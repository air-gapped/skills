---
name: responses-api
description: Reference for the OpenAI Responses API (/v1/responses), OpenResponses open standard, and Codex CLI. Covers the request/response schema, previous_response_id, Conversations API, server-side compaction, WebSocket transport, hosted Shell tool, Skills, tool_search, MCP connectors, prompt caching, phase field, 53 typed streaming events, 10-backend support matrix (vLLM, llama.cpp, mistral.rs, Ollama, LiteLLM, SGLang, Llama Stack, TensorRT-LLM, Bifrost, Lemonade), and Chat Completions translation with 17 gotchas.
when_to_use: Triggers on responses endpoint, output items, InputItem, OutputItem, conversations endpoint, /v1/responses/compact, compaction output item, phase field, tool_search, hosted shell, reasoning.encrypted_content, Codex CLI client_metadata, previous_response_id, conversation field, OpenResponses spec, prompt_cache_key, or migrating off the Assistants API. Also on "implementing Responses API", "proxying OpenAI Responses", "debugging streaming event order", "translating Chat Completions to Responses", or reviewing per-backend Responses quirks.
argument-hint: "[topic: spec, streaming, translation, backends, adoption]"
---

# Responses API Reference

The OpenAI Responses API (`POST /v1/responses`) is the recommended API for
agentic workloads. Launched March 2025. Chat Completions is NOT deprecated,
but superseded for new projects.

Codex CLI dropped Chat Completions in Feb 2026; most major clients (OpenCode, Continue.dev, Cline, Zed, Roo-Code, Vercel AI SDK 5+) now default to Responses. 10 backends serve `/v1/responses` — **Llama Stack is the only non-OpenAI backend with `/v1/responses/compact`**. Full adoption timeline and per-client status in `references/adoption.md`.

**Last refreshed**: 2026-07-19.

## Key Differences from Chat Completions

| Aspect | Chat Completions | Responses API |
|--------|------------------|---------------|
| Input | `messages[]` with `role`+`content` | `input` (string or `InputItem[]`) + `instructions` |
| Output | `choices[0].message` | `output[]` array of typed `OutputItem`s |
| Tool defs | `tools[].function.{name,params}` (nested) | `tools[].{type,name,params}` (flat, `strict:true` default) |
| Tool calls | `message.tool_calls[].function` | Separate `function_call` output items |
| Tool results | `{"role":"tool","tool_call_id":"..."}` message | `{"type":"function_call_output","call_id":"..."}` input item |
| State | Client manages full history | Server via `previous_response_id` OR `conversation` (Conversations API) |
| Streaming | Single delta event, data-only SSE | 53 typed events (HTTP SSE or WebSocket since 2026-02-23) |
| Built-in tools | None | web_search, file_search, code_interpreter, computer (GA 2026-03-05), MCP, image_gen, **shell** (2026-02-10), **tool_search** (2026-03-05) |
| Skills | N/A | Attach via `tools[].environment.skills[]` inside hosted Shell |
| Reasoning | `reasoning_effort` top-level | `reasoning: {effort: "none".."xhigh", generate_summary}` |
| Context mgmt | None | `context_management.compact_threshold` + `compaction` output item, or `POST /v1/responses/compact` |
| Reasoning persistence | Discarded between turns | Kept server-side; pass via `previous_response_id` or `include: ["reasoning.encrypted_content"]` |
| Finish | `finish_reason` string | `response.status` + per-item `status` |
| Prompt caching | `prompt_cache_key` (same) | `prompt_cache_key` + `prompt_cache_retention: "in_memory"/"24h"` |
| Resume dropped stream | No | `GET /v1/responses/{id}?stream=true&starting_after=<seq>` |

## Critical Gotchas

Non-obvious traps with silent failure modes. Full list: `references/translation-mapping.md` (17 gotchas).

- **`phase` field must be preserved verbatim** on assistant messages for gpt-5.3-codex+ and gpt-5.4. Dropping it silently re-emits preambles as final answers (opencode #15528).
- **`reasoning.encrypted_content` required with `store: false`**. Set `include: ["reasoning.encrypted_content"]` every turn or GPT-5 loses ~3% SWE-bench.
- **`ResponseInputMessageItem.type` is REQUIRED** (breaking 2026-03-25). Implicit-type messages fail.
- **Tool defs are flat, not nested**: `{"type":"function","name":"...","parameters":{...}}` — NOT `{"type":"function","function":{"name":...}}` (Chat Completions form).
- **`strict` default flipped**: Responses API = `true`, Chat Completions = `false`. Set explicitly when converting.
- **MCP `{never: {tool_names: []}}` silently disables ALL approvals**. With an empty exempt list, use string `"always"` instead (community 1368778, llama-stack #3443).
- **Compaction output items are opaque encrypted** — preserve byte-for-byte when chaining; drop items preceding the most recent `compaction` when chaining stateless.
- **WebSocket needs session-sticky routing**. `previous_response_id` state is connection-local; without stickiness, multi-turn tool chains break on reconnect (CLIProxyAPI #2596).
- **vLLM silently ignores `store: true`** unless launched with `VLLM_ENABLE_RESPONSES_API_STORE=1` (env var, no CLI flag) — retrieval and `previous_response_id` chaining then 404 with nothing in the server log (live-verified v0.25.1).
- **The vLLM store is per-replica in-memory** (plain dict, no shared/external backend as of v0.25.1) — behind a load balancer, `previous_response_id` chaining 404s (`"Response with id ... not found"`) whenever the next turn lands on a different replica. For fleets: keep clients stateless (full-history replay) or let the gateway own sessions (LiteLLM spend-log reconstruction); never enable per-replica stores without affinity.

## Quick Reference

- **Spec**: `references/spec.md` — full request/response schema, Conversations
  API, Prompt Caching, Transport Modes, Breaking Changes 2026, OpenResponses spec
- **Streaming**: `references/streaming-events.md` — all 53 SSE event types,
  WebSocket transport, resumable streaming, OpenResponses vs OpenAI event
  naming, per-backend quirks
- **Translation**: `references/translation-mapping.md` — Chat Completions <->
  Responses conversion with 17 gotchas
- **Backends**: `references/backend-implementations.md` — 10-column support
  matrix and per-backend notes (including new Llama Stack, TensorRT-LLM,
  Lemonade, Bifrost)
- **Adoption**: `references/adoption.md` — Client adoption, timeline Feb-Jul 2026,
  OpenResponses backer list
- **Sources**: `references/sources.md` — dated per-URL index with `Last verified:`
  stamps and tracked issue/PR statuses; consult before flagging a claim as stale

## Procedures

### Adding Responses API support to a provider
1. Check the backend support matrix in `references/backend-implementations.md`
   — the matrix covers 10 backends as of 2026-07-19.
2. If the backend serves `/v1/responses` natively, a proxy can pass it
   through opaquely.
3. If the backend only serves Chat Completions, translation is needed — see
   `references/translation-mapping.md` for the field mapping and 17 critical
   gotchas.

### Debugging a Responses API streaming issue
1. Capture the raw SSE stream first — event names arrive in the `event:` field:
   ```bash
   curl -sN http://localhost:8000/v1/responses -H "Content-Type: application/json" \
     -d '{"model":"<model>","input":"hi","stream":true}' | head -40
   ```
2. Check the required event ordering in `references/streaming-events.md` —
   `response.created` MUST be first.
3. Verify `response.output_item.added` precedes any deltas for that
   `output_index`. Note: OpenAI gpt-5.3-codex and some backends skip this
   (LiteLLM #22102, stale-closed 2026-06-27 without a confirmed fix).
4. Verify `response.content_part.added` precedes any `output_text.delta` for
   that `content_index`. Azure passthrough via LiteLLM still strips these
   setup events (#20975 still OPEN).
5. Check Known Backend Quirks table in `references/streaming-events.md` for
   per-backend deviations (vLLM omits `[DONE]`, llama.cpp emits all
   `output_item.done` at stream end, mistral.rs has stream+store bugs, etc.).
6. If parallel tool calls crash on vLLM+Qwen3.5 (AssertionError in serving.py):
   fixed by the June 2026 Responses refactor (issue #39584 closed 2026-06-19,
   PRs #46030/#47185) — upgrade to vLLM ≥ v0.25; on older versions switch to
   sequential tool calls.

### Handling stateful conversations
1. Client may pass either `previous_response_id` OR `conversation`
   (Conversations API, IDs like `conv_...`). They are **billing-equivalent**
   but the latter has no 30-day TTL.
2. ZDR tenants auto-enforce `store: false` — use the Conversations API or
   replay the full input client-side.
3. See **Critical Gotchas** above for `phase`, `reasoning.encrypted_content`,
   and `compaction` preservation requirements — all three apply here.

### Understanding a Responses API request/response
1. Load `references/spec.md` for the complete schema — request fields, input
   item types, output item types, tool definitions.
2. Key structural difference: tool defs are flat (not nested under
   `function:`), and `strict` defaults to `true`.
3. Tool calls are separate `function_call` output items (not
   `message.tool_calls`).
4. 2026 additions to know about: `context_management`, `conversation`,
   `prompt_cache_retention`, `client_metadata`, `phase` field on assistant
   messages, `shell` / `tool_search` / GA-renamed `computer` tool types,
   output items `compaction` / `shell_call(+_output)` / `tool_search_call(+_output)`
   / `output_video` / `mcp_approval_request(+_response)`.

### Handling WebSocket transport
1. `wss://api.openai.com/v1/responses` (launched 2026-02-23). Same event model
   as HTTP SSE.
2. Sequential only — one in-flight per socket. 60-minute connection cap.
3. `stream` and `background` flags ignored. See **Critical Gotchas** for the
   session-sticky routing requirement on multi-turn chains.

