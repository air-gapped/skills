# Responses API Backend Implementations

All backends listed here serve `/v1/responses`. Most use the same internal
pattern internally: convert Responses API input to Chat Completions, run
inference, convert output back. vLLM and Llama Stack have the deepest
native handling.

**Last refreshed**: 2026-07-19 (provenance: `references/sources.md`).

## Contents
- [Support Matrix](#support-matrix) — feature × backend table
- [vLLM](#vllm-most-mature) · [llama.cpp](#llamacpp-codex-focused) · [mistral.rs](#mistralrs-openresponses-spec-aligned) · [Ollama](#ollama-minimal-stateless) · [LiteLLM](#litellm-translation-layer-100-providers)
- [SGLang](#sglang-moving-again-since-june-2026) · [Llama Stack](#llama-stack-new-reference-tier-impl) · [TensorRT-LLM](#tensorrt-llm-nvidia) · [Bifrost](#bifrost-expanded) · [Lemonade](#lemonade-amd-new)
- [Not (yet) in the matrix](#not-yet-in-the-matrix) — TGI, Triton, MLX-LM, LM Studio, responses.js

## Support Matrix

| Feature | vLLM | llama.cpp | mistral.rs | Ollama | LiteLLM | SGLang | Llama Stack | TensorRT-LLM | Bifrost | Lemonade |
|---------|------|-----------|------------|--------|---------|--------|-------------|--------------|---------|----------|
| Latest version | v0.25.1 | b10068 | v0.9.0 | v0.32.1 | v1.92.0 | v0.5.15.post1 | v1.2.1 | (active) | v2.0.0-pre | v11.0.0 |
| Streaming | Full | Full | Full | Partial | Full | Partial/buggy | Full | Yes | Full | Yes |
| Tool calls (non-stream) | Yes | Yes | Yes | Yes | Yes | Built-in only | Yes | Yes | Yes | Yes |
| Tool calls (stream) | Yes (parallel buggy) | Yes + `--tools` | Yes | ? | Yes | Broken | Yes | Yes | Yes | Yes |
| Reasoning | Yes | Yes | Yes | Yes (via bridge) | Yes | ? | Yes | Yes | Yes | ? |
| `previous_response_id` | Yes (needs `VLLM_ENABLE_RESPONSES_API_STORE=1`) | No (errors) | Yes (in-memory) | No (PR #15404 open) | Yes (spend logs) | Partial (#25881 replay) | Yes (+ compact) | Yes | Yes | ? |
| `background` | Yes | No | Yes (stream-broken) | No | No | No | Yes | PR open | Yes | No |
| `store`/retrieve | Opt-in: `VLLM_ENABLE_RESPONSES_API_STORE=1` env | No | Yes (in-memory, stream-broken) | No | Yes (stream cache) | No | Yes | Yes | Yes | No |
| Compaction (`/compact`) | No | No | No | No | No | No | **Yes** | No | No | No |
| Built-in tools | MCP, web_search, code_interpreter, shell | via `--tools all` | No | No | web_search (param), file_search | Broken | Extensive | Limited | Multi | No |
| `[DONE]` marker | Omitted | Omitted | Sent | ? | Passthrough | ? | Sent | ? | Sent | ? |
| `sequence_number` | -1 placeholder | Omitted | Proper | ? | Monkey-patched | ? | Proper | ? | Proper | ? |
| WebSocket transport | No | No | No | No | Yes (#22559, #22771) | No | No | No | Yes (#1748) | No |

## vLLM (most mature)

**Source**: `vllm/entrypoints/openai/responses/serving.py` (~1700 lines)
**Latest**: v0.25.1 (2026-07-14)

- Full SSE streaming with proper event lifecycle
- **Streaming tool calls landed for non-Harmony models** (Qwen3/3.5, Gemma 4,
  etc.) via PR #29947 (2026-03-12). Previously tool XML leaked into
  `output_text.delta`; the existing `tool_parser_cls` now emits proper
  `response.output_item.added` + `function_call_arguments.delta`.
- MCP tools via `openai_harmony` library for multi-turn loops
- `previous_response_id` + `previous_input_messages` (vLLM extension)
- Background tasks with async processing
- Generic structured outputs for Responses (PR #33709)
- Sampling params: `presence_penalty`, `frequency_penalty` (PR #38613),
  `repetition_penalty`, `seed`, `stop`, `top_k`, `cache_salt`, `priority`,
  `kv_transfer_params` (PR #37424, PD disaggregation)
- Return token IDs (PRs #33212, #33378)
- Alias serialization (PR #38519)
- `truncation` defaults to `"disabled"` (OpenAI defaults to `"auto"`)
- No `[DONE]` marker (live-confirmed still omitted on v0.25.1, 2026-07-19);
  `sequence_number` is now proper monotonic — the `-1` placeholder (#23218)
  is fixed (live-verified v0.25.1)
- **`store: true` is silently ignored unless the server is launched with
  `VLLM_ENABLE_RESPONSES_API_STORE=1`** (env var, no CLI flag) — without it,
  GET retrieval and `previous_response_id` chaining 404 with no warning in
  the server log. The store is in-memory, volatile on restart, and never
  evicts (memory-leak FIXME in `responses/serving.py`). `background=true +
  store=true` errors explicitly, naming the env var. Live-verified v0.25.1,
  2026-07-19.
- `POST /v1/responses/{id}/cancel` endpoint exists (openapi-confirmed v0.25.1)
- **Serves the Anthropic Messages API natively**: `/v1/messages` +
  `/v1/messages/count_tokens` (openapi-confirmed v0.25.1). Anthropic-format
  clients work directly against vLLM — live-verified 2026-07-19 with
  opencode's anthropic provider, multi-step tool calling included.
- **Fixed**: Instructions leak via `previous_response_id` (PR #37727,
  2026-04-13). Prior-response system messages now stripped when chaining.

**Responses API refactor (June 2026):** PR #46030 (2026-06-23) moved parser
state into conversation context; PR #47185 (2026-06-30) refactored Harmony
handling onto `HarmonyParser`. Closed the parallel-tool-call crash **#39584**
(2026-06-19) — upgrade to ≥ v0.25 rather than working around it.

**Open critical bugs:**
- **#36435**: Non-Harmony models still emit tool XML as `output_text.delta`
  when parser flags unset.
- **#38132**: `truncation: "auto"` returns 400 instead of truncating — issue
  still open, but **no longer reproduces on v0.25.1** (live test 2026-07-19
  returned HTTP 200 with `truncation: "auto"` echoed).
- **#39624**: `DELETE /v1/responses/{id}` not implemented (openapi-confirmed
  still absent on v0.25.1 — only GET and POST `/cancel`).
- **#39221**: Tool-calling divergence between Chat Completions and Responses
  when parser flags unset.

## llama.cpp (Codex-focused)

**Source**: `tools/server/server-common.cpp` (`convert_responses_to_chatcmpl`,
~283 lines) + new `tools/server/server-tools.cpp` (~800 lines)
**Latest**: b10068 (2026-07-18, daily builds)

- Thin wrapper: converts request to Chat Completions, runs inference, converts back
- Explicitly built for Codex CLI compatibility
- Proper `event: <type>\ndata: <json>\n\n` SSE format
- Tool calls supported (streaming and non-streaming)
- Reasoning via `<|channel|>analysis` mapping to reasoning_content
- **Built-in tools scaffolding via `--tools all`** (PR #20898, 2026-03-27).
  Adds `GET /tools`. Write-enabled tools require UI permission dialog. Narrows
  the gap vs vLLM.
- Refusal content in Responses API (PR #20285)
- Merging contiguous Responses input items into single assistant message (PR #19773)
- `developer` role mapped to `system` (PR #20215)
- Gemma 4 parser (PRs #21418, #21704, #21760)
- Qwen3-coder + Nemotron Nano 3 parsers (PR #19765)
- `cached_tokens` in oaicompat responses (PR #19361)
- **Quirk**: All `output_item.done` events emitted at end of stream, not inline
- No session support (previous_response_id errors)
- No background mode
- `strict` defaults to `true` for tools
- Mirroring `/v1/responses` to `/responses` (PR #19873)
- **Open bug**: #19173 — cannot cancel stream to stop generation in Responses API

## mistral.rs (OpenResponses spec-aligned)

**Source**: `mistralrs-server-core/src/responses.rs` (~1818 lines)
**Latest**: v0.9.0 (2026-07-07)

- Implements OpenResponses specification (openresponses.org)
- Full session support via in-memory response cache
- GET/DELETE endpoints for stored responses
- POST cancel endpoint for background tasks
- 14 streaming event types with proper sequence numbers
- `reasoning` config: effort (none/low/medium/high/xhigh) + summary (concise/detailed/auto)
- Handles multimodal input (input_image, input_audio, input_file)
- Sends `[DONE]` at end of stream
- **Quirk**: `parallel_tool_calls=false` returns error (only `true` supported)
- In-memory cache only (volatile on restart)
- SSE hang on error event fixed (#1875), stream termination on channel close (#1943)

**Bug status (as of 2026-07-19):**
- **#1944** (inconsistent `output_item.id` across lifecycle events): closed
  2026-07-07, fixed around v0.9.0.
- **#1945 (OPEN)**: `background=true + stream=true` fails with "Unexpected response type".
- **#1946 (OPEN)**: Streaming OpenResponses with `store=true` are not persisted for retrieval.
- **#1918, #1919**: Security concerns around web_search / SSRF in built-in tool
  URL parsing.
- **#1947**: WebSocketTransport MCP drops in-flight responses under concurrency.

## Ollama (minimal, stateless)

**Latest**: v0.32.1 (2026-07-16)

- `/v1/responses` since v0.13.3
- **Stateless only** as of v0.32.1 — no `previous_response_id`
- **PR #15404 (still OPEN as of 2026-07-19)**: implements `previous_response_id`
  with in-memory store (30-min TTL, 1024 entries, LRU, 13 tests). Flip the
  matrix cell when merged.
- **PR #15406 (MERGED 2026-04-07)**: fixes fn call output arrays — unmarshal
  errors when clients send array-form output (text/image content blocks).
- zstd body decompression + codex env vars (PRs #14122, #14827) for Codex compat
- Improved error message for unknown input item types (PR #15424)
- Details otherwise sparse in documentation

## LiteLLM (translation layer, ~100+ providers)

**Source**: `litellm/responses/` (multiple files)
**Latest**: v1.92.0 (2026-07-12)

- Two modes: (1) passthrough for OpenAI/Azure, (2) Chat Completions translation
  for all other providers
- **Live-verified 2026-07-19** (`litellm/litellm:main-stable` = v1.92.0,
  against vLLM v0.25.1): the `hosted_vllm/` provider **forwards `/v1/responses`
  natively upstream** when the backend serves it (no chat-completions
  down-translation); the Anthropic `/v1/messages` adapter bridges via chat
  completions. Full lifecycle event set with correct ordering and sequence
  numbers on the Responses stream, and LiteLLM **adds the `data: [DONE]`
  terminator vLLM omits**. Quirk: emits **data-only SSE** (no `event:` field
  lines) — fine for parsers reading JSON `type`, breaks parsers keyed on the
  SSE `event:` field.
- Bridges ~100+ providers to Responses API format
- Session support via spend-log history reconstruction
- Converts streaming Chat Completions chunks to proper Responses API events
- Splits large argument deltas into 10-char chunks (mimics token-by-token streaming)
- `web_search` tools converted to `web_search_options` parameter
- Sophisticated `tool_choice` normalization (handles Cursor IDE format)
- Bedrock `completion_tokens_details` in Responses (PR #23243)
- Refusal → incomplete status mapping (PRs #25498, #24912)
- GPT-5 temperature validation (PR #24371)

**Feb-Apr 2026 additions:**
- **WebSocket transport** (PRs #22559, #22771, #25437, #25513)
- **`use_responses_api_bridge`** flag for openai/ models with custom api_base
  (PR #24783)
- **`route_all_chat_openai_to_responses`** global flag (PR #24918)
- **Stream cache replay** (PR #24580, 2026-04-07) — streamed Responses persist
  on completion and replay as synthetic SSE, preserving reasoning summaries
- **`reasoning_items` round-trip** (PR #24690) — exposes `message.reasoning_items`
  and accepts them on assistant messages next turn
- **`content_part.added`** for non-OpenAI models (PR #24445, 2026-03-31) —
  materially improves event sequence on Anthropic/Gemini
- **Responses API cache-key allow-list** (PR #25673)
- **Prompt management for Responses** (PR #23999)
- **Anthropic Responses transformation v1** (PR #22087)
- **Codex multi-turn tool-call merge fix** (PR #25618, 2026-04-13) — handles
  Codex CLI's non-standard tool definition format (`id` + `inputSchema.jsonSchema`)
- **Triton embedding cost estimation** (PR #25345)

**Bug status (2026-07-19):**
- **#20975 (OPEN)**: Setup events stripped on Azure passthrough. PR #24445 only
  fixed the non-OpenAI bridge path.
- **#22102**: gpt-5.3-codex skipping `response.output_item.added` (OpenAI-upstream
  quirk, not LiteLLM-specific, but clients see it via LiteLLM). Stale-closed
  2026-06-27 without a confirmed fix — stay resilient.

## SGLang (moving again since June 2026)

**Latest**: v0.5.15.post1 (2026-07-14)

- Has `/v1/responses` endpoint
- **PR #25881 "Fix Responses API request handling" merged 2026-06-12**:
  binds requests to `ResponsesRequest` (FastAPI validation), normalizes
  `input_text`/`input_image` content parts, replays `previous_response_id`
  assistant output as assistant text (skips reasoning/tool/refusal items),
  fixes usage accounting, propagates stop/tool constraints.
- The long-open competing function-tool PRs **#16806 and #20771 were closed
  unmerged the same day** (2026-06-12), superseded by #25881. Custom
  function-tool support on `/v1/responses` — historically broken — needs
  re-verification on ≥ v0.5.15.
- Fixed `default_max_tokens` compute when MTP opened (PR #18932)
- Streaming session race fix (PR #21875)

## Llama Stack (new reference-tier impl)

**Latest**: v1.2.1 (2026-07-14) — crossed 1.0 between Apr and Jul 2026.
**Rebranded "OGX"** (blog 2026-04-28; code moved to `src/ogx*`, repo name
unchanged). Source-examined 2026-07-19 (commit f05b98f): `/v1/responses` now
also served over **WebSocket** (ogx_api/responses/fastapi_routes.py:378-460),
and a full Anthropic Messages surface exists alongside (see the messages-api
skill).

Not in the matrix before 2026-04-17. Now arguably the most spec-complete
Responses implementation after vLLM.

- **`/v1/responses` renamed from `/v1/agents`** (PR #5195, breaking).
- Reasoning output (PR #5206)
- **`POST /v1/responses/compact`** with `context_management` param (PR #5327) —
  Codex-aware server-side compaction, zstd body decompression. Unique to Llama
  Stack among non-OpenAI backends.
- Cancel endpoint for background responses (PR #5268)
- Compacted responses stored for `previous_response_id` chaining (PR #5507)
- Full OpenResponses conformance claim (PR #4999)
- Provider compatibility matrix across providers (PR #5113)
- Integration tests against Azure AI Foundry (#5107), WatsonX (#5120),
  Bedrock (#5254)

## TensorRT-LLM (NVIDIA)

Has `/v1/responses`. PR #9937 merged 2026-01-13 added GET/DELETE
`/v1/responses/{response_id}`. PR #9946 merged 2025-12-15 added docs + examples.
Harmony parser fixes (#12045, #12467).

**Open PRs (Apr 2026):**
- **#10104**: background request support
- **#10030**: benchmark_serving integration
- **#10107**: list input items for any response

## Bifrost (expanded)

**Latest repo release**: ent-v2.0.0-prerelease2-base (2026-07-16) — v2.0 line
in prerelease; HTTP v1.5.0-prerelease3 was current as of 2026-04-15

- Native Responses API support with WebSocket transport (PR #1748)
- Anthropic Responses streaming via `NewSSEScanner` (PR #1904)
- **Native Fireworks Responses** (PR #2518) — previously chat-completions
  fallback. Preserves `previous_response_id`, `max_tool_calls`, `store`.
- Stream error capture (PR #2681)
- Gemini content-block tool outputs in Responses path (PR #2692)
- **ChatGPT OAuth passthrough** (PR #2775) — routes Codex OAuth tokens to
  `chatgpt.com/backend-api/codex/responses`
- OpenAI array-form tool_result flattening (PR #2781)
- `sanitizeResponsesToolsForChatFallback` helper for backends that can't
  handle non-function tools

## Lemonade (AMD, new)

**Latest**: v11.0.0 (2026-07-15) — versioning scheme jumped from 0.x to
date-independent major versions between Apr and Jul 2026

- PR #945 (2026-01-29) enables `/responses` endpoint for llamacpp recipes
- PR #1505 (2026-04-06) implements Lemonade provider for Codex
- Previously returned 422 on Responses calls (PR #402)
- New entrant — limited documentation

## Not (yet) in the matrix

No `/v1/responses` endpoint observed:
- **TGI** (huggingface/text-generation-inference) — no Responses PRs
- **Triton** inference server — no Responses PRs
- **MLX-LM** (Apple) — no Responses activity
- **LM Studio** — no public Responses PRs; may support it behind proprietary
  code

**HuggingFace responses.js** exists but stagnant (last meaningful commit
Aug 2025; GHA pin PR #36 Apr 2026 only).

**HuggingFace Transformers serve**: PR #41353 (2025-10-06) added non-streaming
mode to `/v1/responses` + stream event parity. No activity since pre-Feb 2026.

**Ramalama** (v0.19.0, 2026-04-17): no Responses-specific work; delegates to
llama.cpp backend.

Fireworks AI, Together AI, Groq, Cerebras APIs, OpenRouter proxy, and
HuggingFace Inference Endpoints / Inference Providers: likely offer Responses
behind closed-source gateways. Bifrost's native Fireworks integration suggests
Fireworks exposes it. No OSS probing surface to verify.
