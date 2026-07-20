# Responses API <-> Chat Completions Translation Mapping

How to convert between the two formats. Based on LiteLLM's `transformation.py` (2200 lines, Python), Bifrost's `mux.go` (Go, pool-based streaming), and llama.cpp's `convert_responses_to_chatcmpl()` (283 lines, C++).

## Contents
- [Request Translation: Responses -> Chat Completions](#request-translation-responses---chat-completions) — messages, tools, parameters
- [Response Translation: Chat Completions -> Responses](#response-translation-chat-completions---responses) — output, status, usage mapping
- [Streaming Translation: Chat Completions SSE -> Responses API SSE](#streaming-translation-chat-completions-sse---responses-api-sse) — state machine, lost features
- [Critical Implementation Gotchas](#critical-implementation-gotchas) — 17 gotchas proxies must handle

## Request Translation: Responses -> Chat Completions

### Messages

| Responses API input | Chat Completions messages |
|---------------------|--------------------------|
| `instructions: "system prompt"` | `{"role": "system", "content": "system prompt"}` (prepended) |
| `input: "plain text"` | `[{"role": "user", "content": "plain text"}]` |
| `input: [{type: "message", role: "user", content: "hi"}]` | `[{"role": "user", "content": "hi"}]` |
| `input: [{type: "message", role: "assistant", content: [{type: "output_text", text: "hello"}]}]` | `[{"role": "assistant", "content": "hello"}]` |
| `input: [{type: "function_call", call_id: "c1", name: "fn", arguments: "{}"}]` | `[{"role": "assistant", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "fn", "arguments": "{}"}}]}]` |
| `input: [{type: "function_call_output", call_id: "c1", output: "result"}]` | `[{"role": "tool", "tool_call_id": "c1", "content": "result"}]` |
| `input: [{type: "reasoning", summary: [...], encrypted_content: "..."}]` | `[{"role": "assistant", "reasoning_content": "..."}]` (attached to preceding/following assistant message) |

### Tools

| Responses API | Chat Completions |
|---------------|------------------|
| `{"type": "function", "name": "fn", "parameters": {...}, "strict": true}` | `{"type": "function", "function": {"name": "fn", "parameters": {...}, "strict": true}}` |
| `{"type": "web_search_preview", ...}` | No equivalent (strip or convert to web_search_options param) |
| Built-in tools | No equivalent |

Key difference: Responses API tools are **flat** (`name` at top level), Chat Completions **nest** under `function:` wrapper.

Strict defaults: Responses API = `true`, Chat Completions = `false`.

### Other Parameters

| Responses API | Chat Completions |
|---------------|------------------|
| `max_output_tokens` | `max_tokens` (or `max_completion_tokens`) |
| `text.format.type: "json_schema"` | `response_format: {type: "json_schema", json_schema: {...}}` |
| `text.format.type: "json_object"` | `response_format: {type: "json_object"}` |
| `reasoning.effort: "none"..."xhigh"` | `reasoning_effort` (top-level) — Chat Completions supports same values |
| `tool_choice` | Same values, same format |
| `previous_response_id` | No equivalent (must expand to full message history) |
| `conversation` | No equivalent (must expand to full message history) |
| `context_management` / compaction | No equivalent — backend-side or client-side history trimming only |
| `truncation` | No equivalent |
| `store` | No equivalent |
| `background` | No equivalent |
| `include: ["reasoning.encrypted_content"]` | No equivalent — reasoning is discarded in Chat Completions |
| `prompt_cache_key`, `prompt_cache_retention` | Same fields accepted on Chat Completions too (not Responses-specific anymore) |
| `client_metadata` | `user` approximates but is a single string; loses structure |

## Response Translation: Chat Completions -> Responses

### Output mapping

| Chat Completions | Responses API output |
|-----------------|---------------------|
| `choices[0].message.content: "hello"` | `[{type: "message", role: "assistant", content: [{type: "output_text", text: "hello"}]}]` |
| `choices[0].message.tool_calls: [{id, function: {name, arguments}}]` | `[{type: "function_call", call_id: id, name: name, arguments: arguments}]` (one per tool call) |
| `choices[0].message.reasoning_content: "..."` | `[{type: "reasoning", summary: [{type: "summary_text", text: "..."}]}]` (prepended before message) |
| `choices[0].message.refusal: "..."` | `[{type: "message", content: [{type: "refusal", refusal: "..."}]}]` |

### Status mapping

| Chat Completions finish_reason | Responses API status |
|-------------------------------|---------------------|
| `"stop"` | `"completed"` |
| `"tool_calls"` | `"completed"` (with function_call output items) |
| `"length"` | `"incomplete"` (reason: "max_output_tokens") |
| `"content_filter"` | `"incomplete"` (reason: "content_filter") |

### Usage mapping

| Chat Completions | Responses API |
|-----------------|---------------|
| `usage.prompt_tokens` | `usage.input_tokens` |
| `usage.completion_tokens` | `usage.output_tokens` |
| `usage.total_tokens` | `usage.total_tokens` |

## Streaming Translation: Chat Completions SSE -> Responses API SSE

This is the complex part. LiteLLM's `streaming_iterator.py` tracks state to emit proper lifecycle events.

### State machine

1. **First chunk**: Emit `response.created`, `response.in_progress`
2. **First content delta**: Emit `response.output_item.added` (message), `response.content_part.added` (output_text), then `response.output_text.delta`
3. **Subsequent content deltas**: Emit `response.output_text.delta` only
4. **First tool call delta**: Emit `response.output_item.added` (function_call), then `response.function_call_arguments.delta`
5. **Subsequent tool call deltas**: Emit `response.function_call_arguments.delta` only
6. **Tool call complete** (finish_reason or name change): Emit `response.function_call_arguments.done`, `response.output_item.done`
7. **Stream end**: Emit remaining `.done` events, then `response.completed` (with usage)

### What's lost in translation

**Responses API features with no Chat Completions equivalent:**
- `previous_response_id` (server-side state)
- Built-in tools (web_search, file_search, code_interpreter, computer_use)
- `background` mode
- `store` / response retrieval
- `truncation` (server-side context management)
- `include` (optional data inclusion)
- `max_tool_calls` (agentic loop cap)
- `service_tier`
- Lifecycle events (output_item.added, content_part.added, etc.)
- `sequence_number` on events
- Per-item `status` field

**Chat Completions features with no Responses API equivalent:**
- `n` (multiple completions — Responses API returns single output)
- `logit_bias`
- `frequency_penalty` / `presence_penalty` (Bifrost carries through, not in official spec)
- `seed`, `stop`, `suffix`
- `stream_options.include_usage` (Responses always includes usage in `response.completed`)

## Critical Implementation Gotchas

1. **Multiple consecutive function_call items must merge into one assistant message** with multiple `tool_calls` entries. Anthropic rejects separate assistant messages per tool call. LiteLLM PR #25618 (2026-04-13) added a fix for Codex multi-turn tool-call merging.

2. **Reasoning items must be preserved between turns** — dropping them degrades
   model performance (~3% SWE-bench on GPT-5). OpenAI states reasoning items
   from responses with function calls must be passed back via
   `previous_response_id`, `conversation`, or explicitly in the input array.
   With `store: false`, must set `include: ["reasoning.encrypted_content"]` on
   every request or raw reasoning is discarded.

3. **`role: "developer"` maps to `role: "system"`** for Chat Completions backends.

4. **Content type vocabularies differ by role**: `output_text` (assistant output), `input_text` (user input), `text` (Chat Completions). LiteLLM bug #17507 found this mismatch.

5. **Must inject `stream_options: {"include_usage": true}`** on the Chat Completions request so the final chunk includes usage data needed for `response.completed`.

6. **`previous_response_id` / `conversation` requires persistent storage** —
   the proxy must store conversation history indexed by response/conversation
   IDs. Without storage, it's effectively a no-op and may cause errors.

7. **Non-function tools are dropped during fallback** — web_search, file_search, code_interpreter, computer_use, shell, tool_search, mcp have no Chat Completions equivalent. Bifrost's `sanitizeResponsesToolsForChatFallback` skips them.

8. **Strict mode defaults differ** — Responses API defaults `strict: true`, Chat Completions defaults `false`. Must explicitly set when converting.

9. **`phase` field on assistant messages must be preserved verbatim when
   replaying for gpt-5.3-codex and gpt-5.4 models.** Dropping it silently
   re-emits preambles as final answers (opencode #15528). When translating to
   Chat Completions, `phase` has no equivalent — round-tripping a conversation
   via Chat Completions loses this signal.

10. **Breaking (2026-03-25): `ResponseInputMessageItem.type` is REQUIRED.**
    Translators must emit `type` on every message item or requests fail. Also:
    `InputAudio` removed from `ResponseInputContent`.

11. **MCP `authorization` and `headers` are NOT persisted server-side** — must
    be resent every request when reconstructing MCP tool configs from stored
    history.

12. **MCP approval-filter bug**: empty `{never: {tool_names: []}}` silently
    disables ALL approvals — when serializing, use string `"always"` if the
    exempt list is empty (community 1368778, llama-stack #3443).

13. **`compaction` output items are opaque and encrypted** — preserve
    byte-for-byte when chaining; do not attempt to parse or translate. When
    forwarding to Chat Completions backends there is no equivalent; drop the
    item and rely on client-side history trimming instead.

14. **`previous_response_id` vs `conversation`**: they are
    billing-equivalent but have different storage semantics
    (30-day TTL vs unlimited). Translators surfacing history to Chat
    Completions can ignore the distinction — both expand to the same
    `messages[]` array.

15. **`computer_use_preview` → `computer` GA rename (2026-03-05)**: honor both
    spellings on input. openai-python 2.26 moved `ComputerTool` class to
    target the GA; preview moved to `ComputerUsePreview`.

16. **WebSocket transport requires sticky routing**: proxies without
    session-sticky WebSocket routing break multi-turn tool chains because
    `previous_response_id` state is connection-local (CLIProxyAPI #2596).

17. **`include: ["web_search_call.results"]`** (added 2026-04-08): if a client
    sets this, pass through; Chat Completions fallback drops it silently.
