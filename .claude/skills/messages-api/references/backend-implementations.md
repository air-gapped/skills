# Messages API Backend Implementations

Servers that natively serve `POST /v1/messages`. Findings from source
examination at the commits in the matrix's first row, re-checked at each
project's latest tag; behaviour that changed between them carries an inline
version gate. **Every major local inference server now serves the Messages
API natively** — all translate internally to their own chat-completion
pipeline (except OGX, which passes through to Messages-native providers).

## Contents
- [Support Matrix](#support-matrix)
- [vLLM](#vllm) · [SGLang](#sglang) · [llama.cpp](#llamacpp) · [Ollama](#ollama)
- [mistral.rs](#mistralrs) · [Llama Stack / OGX](#llama-stack--ogx) · [Lemonade](#lemonade-amd)

## Support Matrix

| Feature | vLLM | SGLang | llama.cpp | Ollama | mistral.rs | OGX (Llama Stack) | Lemonade |
|---|---|---|---|---|---|---|---|
| Commit examined | 9243e0124e | 99f5a6f46b | 571d0d5 | 573386c | 0ae0476 | f05b98f | b09a0e9 |
| Re-checked at | v0.32.0 | v0.5.22 | b11742 | v0.40.6 | v0.9.5 | v1.5.0 | v2026.42.1 |
| `/v1/messages` | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `count_tokens` | Yes (real tokenization) | Yes | Yes | **No** | Yes | Yes | **No** |
| Message Batches | No | No | No | No | No | **Yes (full)** | No |
| `thinking` request param | v0.31.0+: enabled→`thinking_token_budget`, disabled→reasoning off, adaptive ignored; earlier: **silently ignored** | Yes (adaptive+display; budget unenforced) | Yes (enabled→`thinking_budget_tokens`, default 10000; adaptive ignored) | Yes | Yes | Passthrough: native; translation: enabled→`reasoning_effort` by budget, adaptive→none, errors on non-reasoning models | enabled/disabled→`enable_thinking`; other types warned + ignored |
| thinking blocks out | Yes (uuid4 fake signature) | Yes (unsigned) | Yes (thinking first, empty signature_delta) | Yes (no signature_delta) | Yes (v0.9.3+ replays assistant thinking; earlier drops it) | Passthrough: provider's; translation: empty signature | No (shim); verbatim on cloud relay |
| `stop_sequence` stop_reason | v0.29.0+: Yes (carries matched string); earlier **never** | **Never** | Yes (carries matched word) | Yes (other→stop_sequence) | Yes (proper) | Passthrough only; translation never | **Never** (always null) |
| `ping` events | Never | Never (defined unused) | Never | Never | **Yes (keep-alive)** | Forwards on passthrough; **generates** on translation | Never |
| Server tools (web_search etc.) | No | Filtered out (400 if tool_choice names one) | No | **Executes web_search + re-invokes** | Maps to agentic options | Via provider | No |
| Claude Code affordance | billing-header strip | — | billing-header strip | `relax_thinking` + launch cmd | container skills → shell refs | CC-CLI integration tests | launcher sets ANTHROPIC_BASE_URL |

## vLLM

`vllm/entrypoints/anthropic/` — `AnthropicServingMessages extends
OpenAIServingChat`; full translation to ChatCompletionRequest and back.
`count_tokens` does **real chat-template tokenization** (adds non-standard
`context_management.original_input_tokens`).

- `thinking` request param: **silently ignored before v0.31.0** (not in the
  pydantic model). v0.31.0+: `enabled` → `thinking_token_budget` (rejects
  `budget_tokens >= max_tokens`), `disabled` → reasoning off, `adaptive`
  accepted and ignored, `display` ignored; count_tokens applies `thinking` and
  `output_config` too.
- `metadata` accepted but never read; `document` blocks → pydantic 422;
  `tool_reference` / `tool_addition` / `tool_removal` blocks accepted.
- Output thinking blocks carry **fabricated uuid4 signatures**; input
  `redacted_thinking` accepted-and-dropped.
- Streaming: correct `event:`+`data:` wire format; message_start /
  content_block_* / message_delta / message_stop / error; `ping` defined but
  never emitted. `message_start` id is `chatcmpl-…`, not `msg_…`.
- stop_reason: stop→end_turn, length→max_tokens, tool_calls→tool_use (named
  `tool_choice` calls too); unknown→null. `stop_sequence` emitted with the
  matched string since v0.29.0 (streaming `message_delta` since v0.30.0);
  **never before v0.29.0** (field always null).
- Strips `x-anthropic-billing-header` system text blocks (Claude Code
  prefix-caching preservation hack); inline system role auto-merged when the
  chat template requires system-first.
- Usage cache fields require `--enable-prompt-tokens-details` and arrive only
  in `message_delta`; `message_start` omits them and counts the whole prompt
  as `input_tokens`.

## SGLang

`python/sglang/srt/entrypoints/anthropic/` — `AnthropicServing` over the
chat-completion stack. Protocol models mirror anthropic-sdk-python closely
(incl. Claude 4.7 `adaptive` thinking, `display`, `output_config`
effort/task_budget, `betas`).

- Full Anthropic SSE set incl. thinking_delta; signature_delta only when the
  backend supplies a real signature — local models never do, so thinking is
  unsigned.
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
- Full SSE set; thinking block emitted first; empty-string signature_delta
  before closing.
- stop_reason: default max_tokens; natural stop → tool_use if tool calls else
  end_turn; **stop_sequence field carries the matched stop word**.
- 1090-line test file `test_compat_anthropic.py`; documented in server README.

## Ollama

`server/routes.go:1922` → `AnthropicMessagesMiddleware` over native
ChatHandler. Sets `relax_thinking` "to connect to tools like claude code".

- **No count_tokens route.**
- **Actually executes `web_search` server-tool calls** (WebSearchAnthropicWriter
  re-invokes the model) — unique among local backends.
- SSE set has thinking_delta but **no signature_delta** (thinking unsigned);
  input tokens estimated for
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
- Input blocks: v0.9.3+ replays assistant `thinking` as `reasoning_content`;
  `redacted_thinking`, `server_tool_use`, and thinking/tool-result blocks on
  user turns are **silently dropped** (before v0.9.3 all input thinking was
  dropped); unknown block types → error.
- stop_reason mapping is the most correct of the set (proper stop_sequence).
- Streaming: full set + **keep-alive pings** (only backend emitting ping);
  **tool_use streamed as one complete start/delta/stop triple per call, not
  incremental input_json_delta** — progressive-arg-parsing clients see args
  arrive at once.
- Usage: v0.9.3+ reports `cache_read_input_tokens` (from cached prompt
  tokens) and `cache_creation_input_tokens` hardcoded 0; earlier input/output
  only.

## Llama Stack / OGX

**Rebranded "OGX"** (`src/ogx*`; repo `ogx-ai/ogx` — `llamastack/llama-stack`
redirects there). Deepest Anthropic surface of any backend:
`/v1/messages`, `count_tokens`, **full Message Batches** (create/list/get/
cancel/results), `anthropic-version` response header, Anthropic-format error
bodies.

- Generic path translates via `OpenAIMixin.anthropic_messages`; **providers
  whose backends natively serve /v1/messages get direct passthrough** via
  `AnthropicMixin` (vllm, ollama, meta, anthropic, deepseek, fireworks) —
  the only path that keeps extended thinking, cache_control and tool search.
  On deepseek/fireworks count_tokens falls back to a `max_tokens=1` call.
- Translation path: `thinking.enabled` → `reasoning_effort` (budget ≤2048
  low, ≤8192 medium, else high), `adaptive` → no effort, any thinking on a
  non-reasoning model → error; reasoning returned as a leading thinking block
  with empty signature; stop→end_turn, content_filter→end_turn, **never
  stop_sequence**; emits `ping` after message_start and every block stop.
- Conformance: `scripts/anthropic_coverage.py` diffs OGX's OpenAPI against
  Anthropic's Stainless spec; **integration tests drive the real Claude Code
  CLI and Claude Agent SDK**.
- Also serves OpenAI chat/completions, `/v1/responses` (POST+GET+WebSocket),
  files, conversations; skills and containers under `/v1alpha`.

## Lemonade (AMD)

`src/cpp/server/anthropic_api.cpp` — Anthropic→OpenAI chat shim for local
models; **Anthropic-wire cloud providers are relayed verbatim** (thinking
blocks, tool use, cache_control preserved).

- Coverage: model/messages/system/max_tokens/temperature/stream, tools +
  `tool_choice`, `stop_sequences`, images, `tool_result`,
  `output_config.format`; unsupported fields ignored **with warnings**
  (`X-Lemonade-Warning` header); `?beta=true` accepted.
- `thinking`: `enabled`/`disabled` → `enable_thinking` true/false; any other
  type (incl. `adaptive`) warned and ignored. The shim emits no thinking
  blocks and `stop_sequence` is always null.
- **No count_tokens.** `/v1/messages` exempt from its quad-prefix rule (bare
  path only).
- Claude Code launcher (`agent_launcher.cpp`) sets `ANTHROPIC_BASE_URL`
  origin-only.
