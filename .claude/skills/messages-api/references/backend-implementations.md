# Messages API Backend Implementations

Servers that natively serve `POST /v1/messages`. All findings from direct
source examination of local clones (codegraph-indexed), commits of 2026-07-16
to 2026-07-18. **Every major local inference server now serves the Messages
API natively** — all translate internally to their own chat-completion
pipeline (except OGX, which passes through to Messages-native providers).

**Last refreshed**: 2026-07-19 (provenance: `references/sources.md`).

## Contents
- [Support Matrix](#support-matrix)
- [vLLM](#vllm) · [SGLang](#sglang) · [llama.cpp](#llamacpp) · [Ollama](#ollama)
- [mistral.rs](#mistralrs) · [Llama Stack / OGX](#llama-stack--ogx) · [Lemonade](#lemonade-amd)

## Support Matrix

| Feature | vLLM | SGLang | llama.cpp | Ollama | mistral.rs | OGX (Llama Stack) | Lemonade |
|---|---|---|---|---|---|---|---|
| Commit examined | 9243e0124e | 99f5a6f46b | 571d0d5 | 573386c | 0ae0476 | f05b98f | b09a0e9 |
| `/v1/messages` | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `count_tokens` | Yes (real tokenization) | Yes | Yes | **No** | Yes | Yes | **No** |
| Message Batches | No | No | No | No | No | **Yes (full)** | No |
| `thinking` request param | **Silently ignored** | Yes (adaptive+display; budget unenforced) | Yes (enabled→`thinking_budget_tokens`, default 10000; adaptive ignored) | Yes | Yes | Translated | No (basic) |
| thinking blocks out | Yes (uuid4 fake signature) | Yes | Yes (thinking first, signature_delta) | Yes | Yes (drops input thinking) | Via provider | No |
| `stop_sequence` stop_reason | **Never** | **Never** | Yes (carries matched word) | Yes (other→stop_sequence) | Yes (proper) | Via provider | **Never** (always null) |
| `ping` events | Never | Never (defined unused) | Never | Never | **Yes (keep-alive)** | Forwards on passthrough; doesn't generate | Never |
| Server tools (web_search etc.) | No | Filtered out (400 if tool_choice names one) | No | **Executes web_search + re-invokes** | Maps to agentic options | Via provider | No |
| Claude Code affordance | billing-header strip | — | billing-header strip | `relax_thinking` + launch cmd | container skills → shell refs | CC-CLI integration tests | launcher sets ANTHROPIC_BASE_URL |

## vLLM

`vllm/entrypoints/anthropic/` — `AnthropicServingMessages extends
OpenAIServingChat`; full translation to ChatCompletionRequest and back.
`count_tokens` does **real chat-template tokenization** (adds non-standard
`context_management.original_input_tokens`).

- `thinking` request param **not in the pydantic model — silently ignored**;
  `metadata` accepted but never read; `document` blocks → pydantic 422.
- Output thinking blocks carry **fabricated uuid4 signatures**; input
  `redacted_thinking` accepted-and-dropped.
- Streaming: correct `event:`+`data:` wire format; message_start /
  content_block_* / message_delta / message_stop / error; `ping` defined but
  never emitted. `message_start` id is `chatcmpl-…`, not `msg_…`.
- stop_reason: stop→end_turn, length→max_tokens, tool_calls→tool_use; **no
  stop_sequence mapping** (field always null); unknown→null.
- Strips `x-anthropic-billing-header` system text blocks (Claude Code
  prefix-caching preservation hack); inline system role auto-merged when the
  chat template requires system-first.
- Usage cache fields require `--enable-prompt-tokens-details`.
- Live-verified 2026-07-19 (v0.25.1, local deployment): multi-step tool
  calling via opencode anthropic provider, clean token-leakage scan.

## SGLang

`python/sglang/srt/entrypoints/anthropic/` — `AnthropicServing` over the
chat-completion stack. Protocol models mirror anthropic-sdk-python closely
(incl. Claude 4.7 `adaptive` thinking, `display`, `output_config`
effort/task_budget, `betas`).

- Full Anthropic SSE set incl. thinking_delta + signature_delta.
- stop_reason: stop→end_turn, length→max_tokens, tool_calls→tool_use;
  unmapped→end_turn + WARNING; **never stop_sequence**.
- `thinking.budget_tokens` accepted but NOT enforced; `display:"omitted"`
  still emits reasoning; `betas` no-op; `redacted_thinking` in history → 400.
- Anthropic server tools filtered from forwarded list; `tool_choice` naming
  one → 400. Assistant-side tool_result flattened to text.
- Strong test suite (unit + server + tool-use + vision).
- Note: `sgl-model-gateway` (Rust) does NOT serve /v1/messages — Anthropic is
  upstream-provider-only there.

## llama.cpp

`tools/server/` — routes at server.cpp:242/:259; translate→OpenAI→shared
pipeline→`TASK_RESPONSE_TYPE_ANTHROPIC`.

- Also normalizes the Claude Code `x-anthropic-billing-header` prefix.
- `thinking` request param: `type:"enabled"` maps `budget_tokens` (default
  10000) → `thinking_budget_tokens`; `adaptive` not handled. `metadata.user_id`
  forwarded as `__metadata_user_id` (server-chat.cpp:577-594).
- Full SSE set; thinking block emitted first; signature_delta before closing.
- stop_reason: default max_tokens; natural stop → tool_use if tool calls else
  end_turn; **stop_sequence field carries the matched stop word**.
- 1090-line test file `test_compat_anthropic.py`; documented in server README.

## Ollama

`server/routes.go:1922` → `AnthropicMessagesMiddleware` over native
ChatHandler. Sets `relax_thinking` "to connect to tools like claude code".

- **No count_tokens route.**
- **Actually executes `web_search` server-tool calls** (WebSearchAnthropicWriter
  re-invokes the model) — unique among local backends.
- Full SSE set incl. signature_delta; input tokens estimated for
  message_start.
- stop_reason: tool calls→tool_use, stop→end_turn, length→max_tokens,
  **other non-empty→stop_sequence**.
- Anthropic-typed errors incl. `overloaded_error` (529). Claude Code/Desktop
  launch integration (`cmd/launch/claude.go`);
  `docs/api/anthropic-compatibility.mdx`.

## mistral.rs

`mistralrs-server-core/src/anthropic.rs` — converts to ChatCompletionRequest.

- Rich request surface incl. `container` (skills→shell refs), web_search
  options, many sampling extensions.
- **Input thinking/redacted_thinking/server_tool_use blocks silently
  dropped**; unknown block types → error.
- stop_reason mapping is the most correct of the set (proper stop_sequence).
- Streaming: full set + **keep-alive pings** (only backend emitting ping);
  **tool_use streamed as one complete start/delta/stop triple per call, not
  incremental input_json_delta** — progressive-arg-parsing clients see args
  arrive at once.
- Usage: input/output only — no cache token fields.

## Llama Stack / OGX

**Rebranded "OGX"** (blog 2026-04-28; `src/ogx*`, repo still
llamastack/llama-stack). Deepest Anthropic surface of any backend:
`/v1/messages`, `count_tokens`, **full Message Batches** (create/list/get/
cancel/results), `anthropic-version` response header, Anthropic-format error
bodies.

- Generic path translates via `OpenAIMixin.anthropic_messages`; **providers
  whose backends natively serve /v1/messages get direct passthrough (vLLM,
  meta, ollama)**.
- Conformance: `scripts/anthropic_coverage.py` diffs OGX's OpenAPI against
  Anthropic's Stainless spec; **integration tests drive the real Claude Code
  CLI and Claude Agent SDK**.
- Also serves OpenAI chat/completions, `/v1/responses` (POST+GET+WebSocket),
  files, conversations, skills, containers.

## Lemonade (AMD)

`src/cpp/server/anthropic_api.cpp` — Anthropic→OpenAI chat shim.

- Coverage: model/messages/system/max_tokens/temperature/stream + basic
  tools; unsupported fields ignored **with warnings**; `?beta=true` accepted.
- **No count_tokens.** `/v1/messages` exempt from its quad-prefix rule (bare
  path only).
- Claude Code launcher (`agent_launcher.cpp:116`) sets `ANTHROPIC_BASE_URL`
  origin-only.
