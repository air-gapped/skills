# Responses API Streaming Events

Source: openai-python SDK `ResponseStreamEvent` union (53 named types as of
2026-07-19), community docs, LiteLLM implementation, OpenAI API reference
through 2026-07-19.

## Contents
- [Wire Format](#wire-format) — SSE protocol with `event:` + `data:` fields
- [Required Ordering](#required-ordering) — `response.created` first, lifecycle constraints
- [Event Categories](#event-categories) — all named event types grouped by function
- [Typical Event Sequences](#typical-event-sequences) — plain text, function call, reasoning+text
- [New Output Item Types (2026)](#new-output-item-types-2026) — compaction, shell, tool_search, video
- [WebSocket Transport](#websocket-transport) — wss endpoint, same event model
- [Resumable Streaming](#resumable-streaming) — starting_after for dropped connections
- [OpenResponses vs OpenAI events](#openresponses-vs-openai-events) — naming and semantic differences
- [Comparison to Chat Completions](#comparison-to-chat-completions-streaming) — side-by-side differences
- [Known Backend Quirks](#known-backend-quirks) — per-backend deviations and bugs

## Wire Format

Each SSE message uses BOTH `event:` and `data:` fields (unlike Chat Completions which is data-only):

```
event: response.output_text.delta
data: {"type":"response.output_text.delta","item_id":"msg_abc","output_index":0,"content_index":0,"delta":"Hello","sequence_number":4}

```

- The `type` field in JSON matches the `event:` field (redundant, can parse either)
- Every event carries `sequence_number: int` (monotonically increasing)
- Stream terminates with `data: [DONE]` (same as Chat Completions)
- Note: some backends (vLLM, llama.cpp) omit `[DONE]`; mistral.rs sends it

## Required Ordering

1. `response.created` **MUST be first** (SDK raises RuntimeError otherwise)
2. `response.in_progress`
3. For each output item:
   - `response.output_item.added` (MUST precede any deltas for that output_index)
   - `response.content_part.added` (MUST precede text deltas for that content_index)
   - Delta events (text, tool args, reasoning)
   - Done events (text done, content_part done, output_item done)
4. Terminal: exactly one of `response.completed` / `response.failed` / `response.incomplete`
5. `data: [DONE]`

**Known bug**: OpenAI's gpt-5.3-codex sometimes skips `response.output_item.added`
and starts with deltas directly (LiteLLM issue #22102, filed 2026-02-25 —
stale-closed 2026-06-27 with no confirmed upstream fix). This is an
OpenAI-upstream stream quirk, not LiteLLM-specific. Proxy must be resilient:
treat first `*.delta` as implicit `output_item.added`.

**Related bug**: LiteLLM #20975 — Azure passthrough strips
`response.created` / `response.in_progress` / `response.output_item.added` /
`response.content_part.added` setup events. PR #24445 fixed the non-OpenAI
bridge path but the Azure passthrough remains broken. Still OPEN.

## Event Categories

### Response Lifecycle (7)
| Event | Key fields | Notes |
|-------|-----------|-------|
| `response.queued` | `response` | Waiting to process |
| `response.created` | `response` | Always first |
| `response.in_progress` | `response` | Processing started |
| `response.completed` | `response` (with `usage`) | **Only source of token counts** |
| `response.failed` | `response` (with `error`) | Terminal |
| `response.incomplete` | `response` (with `incomplete_details.reason`) | Terminal |
| `error` | `code`, `message`, `param` | Error during streaming |

### Output Items (2)
| Event | Key fields |
|-------|-----------|
| `response.output_item.added` | `output_index`, `item` |
| `response.output_item.done` | `output_index`, `item` (finalized) |

### Content Parts (2)
| Event | Key fields |
|-------|-----------|
| `response.content_part.added` | `item_id`, `output_index`, `content_index`, `part` |
| `response.content_part.done` | `item_id`, `output_index`, `content_index`, `part` |

### Text Streaming (3)
| Event | Key fields |
|-------|-----------|
| `response.output_text.delta` | `item_id`, `output_index`, `content_index`, `delta` |
| `response.output_text.done` | `item_id`, `output_index`, `content_index`, `text` (final) |
| `response.output_text.annotation.added` | `annotation` |

### Function Call Arguments (2)
| Event | Key fields | Notes |
|-------|-----------|-------|
| `response.function_call_arguments.delta` | `item_id`, `output_index`, `delta` | Raw JSON fragment. Append, do NOT parse yet |
| `response.function_call_arguments.done` | `item_id`, `output_index`, `name`, `arguments` | Complete. Parse `arguments` as JSON string |

### Refusal (2)
| Event | Key fields |
|-------|-----------|
| `response.refusal.delta` | `item_id`, `output_index`, `content_index`, `delta` |
| `response.refusal.done` | `item_id`, `output_index`, `content_index`, `refusal` |

### Reasoning Summary (4)
| Event | Key fields |
|-------|-----------|
| `response.reasoning_summary_part.added` | `item_id`, `output_index`, `summary_index`, `part` |
| `response.reasoning_summary_text.delta` | `item_id`, `output_index`, `summary_index`, `delta` |
| `response.reasoning_summary_text.done` | `text`, `summary_index` |
| `response.reasoning_summary_part.done` | `part` |

### Reasoning Text (2, OpenResponses extension)
| Event | Key fields |
|-------|-----------|
| `response.reasoning_text.delta` | `item_id`, `output_index`, `content_index`, `delta` |
| `response.reasoning_text.done` | `item_id`, `output_index`, `content_index`, `text` |

### Web Search (3)
| Event | Key fields |
|-------|-----------|
| `response.web_search_call.in_progress` | `output_index`, `item_id` |
| `response.web_search_call.searching` | `output_index`, `item_id` |
| `response.web_search_call.completed` | `output_index`, `item_id` |

### File Search (3)
| Event | Key fields |
|-------|-----------|
| `response.file_search_call.in_progress` | `output_index`, `item_id` |
| `response.file_search_call.searching` | `output_index`, `item_id` |
| `response.file_search_call.completed` | `output_index`, `item_id` |

### Code Interpreter (5)
| Event | Key fields |
|-------|-----------|
| `response.code_interpreter_call.in_progress` | `output_index`, `item_id` |
| `response.code_interpreter_call.interpreting` | `output_index`, `item_id` |
| `response.code_interpreter_call.completed` | `output_index`, `item_id` |
| `response.code_interpreter_call_code.delta` | `delta` |
| `response.code_interpreter_call_code.done` | `code` |

### Image Generation (4)
| Event | Key fields |
|-------|-----------|
| `response.image_generation_call.in_progress` | |
| `response.image_generation_call.generating` | |
| `response.image_generation_call.partial_image` | `partial_image_index`, `b64_json` |
| `response.image_generation_call.completed` | |

### MCP (8)
| Event | Key fields |
|-------|-----------|
| `response.mcp_call_arguments.delta` | `delta` |
| `response.mcp_call_arguments.done` | `arguments` |
| `response.mcp_call.in_progress` | |
| `response.mcp_call.completed` | |
| `response.mcp_call.failed` | |
| `response.mcp_list_tools.in_progress` | |
| `response.mcp_list_tools.completed` | |
| `response.mcp_list_tools.failed` | |

### Custom Tool Call (2)
| Event | Key fields |
|-------|-----------|
| `response.custom_tool_call_input.delta` | `delta` |
| `response.custom_tool_call_input.done` | `input` |

### Audio (4)
| Event | Key fields |
|-------|-----------|
| `response.audio.delta` | `delta` (base64) |
| `response.audio.done` | |
| `response.audio.transcript.delta` | `delta` |
| `response.audio.transcript.done` | |

## Typical Event Sequences

### Plain text response
```
response.created -> response.in_progress ->
output_item.added (message) -> content_part.added (output_text) ->
N x output_text.delta -> output_text.done ->
content_part.done -> output_item.done ->
response.completed (has usage) -> [DONE]
```

### Function call
```
response.created -> response.in_progress ->
output_item.added (function_call) ->
N x function_call_arguments.delta ->
function_call_arguments.done (has name + complete args) ->
output_item.done ->
response.completed -> [DONE]
```

### Reasoning + text
```
response.created -> response.in_progress ->
output_item.added (reasoning) ->
reasoning_summary_part.added -> N x reasoning_summary_text.delta ->
reasoning_summary_text.done -> reasoning_summary_part.done ->
output_item.done (reasoning) ->
output_item.added (message) -> content_part.added ->
N x output_text.delta -> output_text.done ->
content_part.done -> output_item.done ->
response.completed -> [DONE]
```

## New Output Item Types (2026)

The following output item types were added in 2026-02 and 2026-03. They flow
through the existing `response.output_item.{added,done}` envelope — no new
dedicated stream event names were introduced:

| Output item type | Added | Surfaces as |
|------------------|-------|-------------|
| `compaction` | 2026-02-10 | Single encrypted item via `output_item.added`/`done` when `context_management.compact_threshold` crossed. Drop prior items when chaining stateless. |
| `shell_call` + `shell_call_output` | 2026-02-10 | Hosted Shell tool invocation pair. No dedicated delta events — args arrive via `function_call_arguments.*` style flow. |
| `tool_search_call` + `tool_search_output` | 2026-03-05 | Tool search (gpt-5.4+). Resolves deferred function tools. |
| `output_video` | 2026-03-12 | Sora video output. |
| `mcp_approval_request` + `mcp_approval_response` | ongoing | Surfaces when `require_approval` is non-"never". Client replies with `mcp_approval_response` input item. |

**`phase` field on assistant message items** (added 2026-02-24): values
`"commentary"` or `"final_answer"`. Not a streaming event — a field on the
message output item surfaced via `output_item.done`. REQUIRED when replaying
assistant items on gpt-5.3-codex+ or preambles get re-emitted as final answers
(opencode #15528).

## WebSocket Transport

Added 2026-02-23. `wss://api.openai.com/v1/responses`.

- Same event model as HTTP SSE — events arrive as WebSocket text frames rather
  than SSE messages. Parsers that consume `{type: ..., ...}` JSON work unchanged.
- Client sends `response.create` frames (request-initiation) rather than HTTP
  POSTs.
- Optional warm-up: send `{"generate": false}` to establish session state
  without generating.
- 60-minute connection cap. Sequential only (one in-flight per socket).
- `stream` and `background` are ignored.
- Benefit: OpenAI-reported 30-40% faster rollouts on 20+ tool-call loops vs HTTP SSE.
- Connection-local `previous_response_id` state. Proxies MUST session-sticky
  WebSocket routing or multi-turn chains break on reconnect
  (CLIProxyAPI #2596/#2594).

## Resumable Streaming

Added 2026. Resume a dropped SSE stream after reconnect:

```
GET /v1/responses/{id}?stream=true&starting_after=<sequence_number>
```

The server resumes from the sequence after the given number. Persist
`sequence_number` client-side to enable recovery.

## OpenResponses vs OpenAI events

OpenResponses open spec is deliberately minimal — 25 named event types vs
OpenAI's 53 (count from the 2026-01-15 spec; the 2026-04-24 release added
WebSocket transport and the `phase` field but the ~28-event gap remains
tool/MCP/audio/compaction/shell/tool_search — OpenAI-proprietary).

**Named semantic collision — reasoning events:**

| Concept | OpenAI | OpenResponses |
|---------|--------|---------------|
| Natural-language summary streaming | `response.reasoning_summary_text.{delta,done}` | (provider-specific prefix if emitted) |
| Raw reasoning text streaming | `response.reasoning_text.{delta,done}` (optional, opted-in) | `response.reasoning.{delta,done}` |
| Encrypted replay-only payload | `reasoning` item with `encrypted_content` field | same field name |

Proxies translating between open spec and OpenAI must pass provider-prefixed
item/event types through untouched (e.g., `openai:web_search_call`,
`acme:trace_event`).

## Known Backend Quirks

| Backend | Quirk | Status (2026-07-19) |
|---------|-------|---------------------|
| vLLM | Omits `[DONE]` marker | Live-confirmed still omitted on v0.25.1 (2026-07-19) |
| vLLM | `-1` placeholder for `sequence_number` (issue #23218) | **Fixed** — live-verified proper monotonic numbering on v0.25.1 (2026-07-19) |
| vLLM | Item `id` differs between stream lifecycle events and the final `response.completed` output (`msg_...`) | Live-observed on v0.25.1 (2026-07-19) — match items by `output_index`, not `id` |
| vLLM (non-Harmony models) | Leaks tool XML into `output_text.delta` (issue #36435) | Open |
| vLLM | Parallel tool calls crash: AssertionError at `serving.py:1761` on Qwen3.5 (issue #39584) | Closed 2026-06-19 (Responses refactor PRs #46030/#47185); fix live-verified on v0.25.1, 2026-07-19 — two parallel `function_call` items stream cleanly |
| vLLM | `truncation: "auto"` returns 400 instead of truncating (#38132) | Open |
| vLLM | DELETE `/v1/responses/{id}` not implemented (#39624) | Open |
| llama.cpp | Emits all `output_item.done` at stream end, not inline; no session support | Known quirk |
| llama.cpp | Omits `[DONE]` | Known quirk |
| mistral.rs | `parallel_tool_calls=false` returns error | Known quirk |
| mistral.rs | Inconsistent `output_item.id` across lifecycle events (#1944) | Closed 2026-07-07 (fixed around v0.9.0) |
| mistral.rs | `background=true + stream=true` fails "Unexpected response type" (#1945) | Open |
| mistral.rs | `store=true + stream=true` not persisted (#1946) | Open |
| Ollama | No `previous_response_id` (PR #15404 open, not merged) | Open |
| LiteLLM | Setup events stripped on Azure passthrough (#20975) | Open |
| LiteLLM | Splits large argument deltas into 10-char chunks | By design |
| SGLang | Custom function tools broken on `/v1/responses` (#16806, #20771) | Both PRs closed unmerged 2026-06-12; request-handling fix #25881 merged same day — re-verify on ≥ v0.5.15 |
| OpenAI gpt-5.3-codex | Sometimes skips `output_item.added` (LiteLLM #22102) | Stale-closed 2026-06-27, no confirmed fix — stay resilient |

## Comparison to Chat Completions Streaming

| Chat Completions | Responses API |
|-----------------|---------------|
| `data: {"choices":[{"delta":{"content":"Hi"}}]}` | `event: response.output_text.delta\ndata: {"delta":"Hi",...}` |
| `data: {"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"..."}}]}}]}` | `event: response.function_call_arguments.delta\ndata: {"delta":"...",...}` |
| No event field | `event:` field on every SSE message |
| 1 effective event type | 53 distinct typed events |
| No lifecycle events | created, in_progress, completed/failed/incomplete |
| Usage in final chunk (opt-in via stream_options) | Usage always in response.completed |
| `data: [DONE]` | `data: [DONE]` (same) |
