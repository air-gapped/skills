# Gateways serving Chat Completions inbound

How proxies/gateways handle `/v1/chat/completions` as the CLIENT-facing
protocol. Source-examined 2026-07-19 (commits in `sources.md`). For the same
gateways' Anthropic-Messages and Responses front doors, see the messages-api
and responses-api skills — this file is CC-inbound only.

**Key fact**: Superagent Gateway has NO CC inbound — its client protocols
are Anthropic Messages and OpenAI Responses only; CC is its upstream wire
format (see below).

## Contents
- [LiteLLM](#litellm)
- [Bifrost](#bifrost)
- [Superagent Gateway (CC outbound only)](#superagent-gateway)
- [The gateway tax](#the-gateway-tax)

## LiteLLM

Everything funnels through `get_optional_params()` (litellm/utils.py:3760).

- **Param filtering cascade**: params differing from OpenAI defaults are
  checked against `get_supported_openai_params(model, provider)`; unsupported
  ones are dropped silently iff `drop_params` (global or per-request), else
  raise `UnsupportedParamsError` — **as HTTP 500, not 400**
  (utils.py:3861-3864). Escape hatches: `additional_drop_params` (strip
  named/nested params pre-mapping), `allowed_openai_params` (force-pass a
  param the config says is unsupported). `user`, `stream`, `stream_options`,
  `max_retries`, `n==1` always exempt.
- Tool schema mutation happens at the shared layer: `additionalProperties:
  false` is stripped from tool parameter schemas (breaks Vertex/Gemini,
  utils.py:3641-3652).
- **Prefix routing changes the wire body**: `openai/<model>` passes the full
  OpenAI surface; `hosted_vllm/<model>` additionally strips
  `additionalProperties` AND `strict` from tool schemas, converts OpenAI
  `custom` tools to plain function tools, and maps Anthropic-style
  `thinking` → `reasoning_effort` (hosted_vllm/chat/transformation.py).
  Unknown model with no provider match → permissive OpenAI param list.
- **o-series / gpt-5 rewrites** (model-name sniffed): `max_tokens` →
  `max_completion_tokens`; o-series temperature≠1 dropped-or-400 (never
  clamped); gpt-5.1+ allow `logprobs`/`top_p`/`top_logprobs` only when
  `reasoning_effort='none'`; `gpt-5-chat*` excluded from the reasoning path.
  Detection requires the model to be in LiteLLM's model map — unknown
  aliases skip the special-casing.
- **CC → Anthropic outbound**: `stop`→`stop_sequences`; `response_format` →
  native `output_format` or the forced-tool JSON trick; `user` →
  `metadata.user_id` (email-looking values rejected); Claude Code's
  `thinking:{type:"adaptive"}` downgraded to `{type:"enabled",
  budget_tokens}` for pre-4.6 models (budget capped to max_tokens);
  Opus 4.7+/adaptive models accept only temperature=1 (others
  dropped/400). Response: thinking blocks → `message.reasoning_content` +
  non-standard `message.thinking_blocks`. If thinking is enabled but replayed
  assistant messages carry no thinking_blocks, the thinking param is dropped
  for that turn (warning).
- **Tool-call id fabrication**: `call_<uuid>` for Ollama/Gemini/Bedrock/
  GigaChat; deterministic for Cohere (`call_<generation_id>`) and OCI
  (hash); Anthropic `toolu_*` ids passed through (round-trip safe).
- **Streaming = full re-chunking**: every provider stream re-parsed and
  re-emitted as OpenAI chunks (LiteLLM's ids/created/boundaries; role
  injected on first chunk; final chunk normalized empty-delta +
  finish_reason). Usage: the usage chunk is sent only when the client asked
  `include_usage`, but usage is ALWAYS computed and attached to hidden
  params for cost tracking. Provider `reasoning` keys are unified to
  `reasoning_content` (types/utils.py:1293); optional
  `merge_reasoning_content_in_choices` wraps it in `<think>` inside content.
- Mock/fallback: `mock_response` magic strings raise typed exceptions
  (RateLimitError etc.) for client retry testing; router fallbacks can
  transparently re-run a request on another deployment (response `model`
  reflects the fallback).
- The `/v1/messages` and Responses bridges are documented in the
  messages-api / responses-api skills (supported_endpoints,
  use_responses_api_bridge).

## Bifrost

Bifrost's INTERNAL schema is Chat Completions (`BifrostChatRequest/Response`)
— CC inbound is near-native; other protocols convert to it.

- Two front doors: `/v1/chat/completions` (primary) and
  `/openai/v1/chat/completions` (integration; also an Azure-style
  `/openai/deployments/{d}/chat/completions`).
- Model string is the router: `provider/model` split on first `/`
  (`anthropic/claude-…`); non-standard **`fallbacks` accepted in the CC
  request body**; unknown JSON keys ride as `ExtraParams` to the provider.
- Ingress normalization: `max_tokens` → `max_completion_tokens` if absent
  (chat.go:14-16); `max_completion_tokens` **floored to 16**; `user` >64
  chars dropped; tool schemas re-serialized deterministically (prompt-cache
  friendliness).
- **openai→openai is a raw-byte fast path** (zero translation tax); all
  other providers get conversion, and multi-block text content is flattened
  with `\n\n` — CC clients never see content-block arrays.
- Non-OpenAI upstreams: `filterOpenAISpecificParameters` silently strips
  `prediction`, `prompt_cache_key/retention/options`, `verbosity`, `store`,
  `web_search_options`. Fireworks: `prompt_cache_key` renamed
  `prompt_cache_isolation_key`. Vertex Model Garden: `reasoning_effort:
  "none"` dropped.
- CC → Anthropic: required `max_tokens` synthesized when absent;
  temperature XOR top_p (temperature wins); all sampling dropped for
  Opus 4.7+/adaptive models; `response_format` on Vertex/Bedrock Anthropic →
  forced-tool trick (skipped when thinking active).
- Agent mode: with MCP configured, Bifrost may run its own tool-execution
  loop — the client can receive a final answer instead of tool_calls.
- Reverse translation exists (CC internals → Anthropic-protocol clients);
  `reasoning_details` (OpenRouter-style) preserved on messages.

## Superagent Gateway

CC **outbound only** (`ClientProtocol` = AnthropicMessages | OpenAiResponses;
src/error.rs:7). Relevance to CC servers: it is a demanding CC CLIENT —
what it sends upstream is a good tolerance checklist:

- Emits `POST {base}/chat/completions` with: system flattened to one string;
  `tool_result` → `role:"tool"` messages ordered BEFORE same-turn text;
  images from tool_results relayed as a trailing user message.
- **Reasoning dual-write**: replayed assistant thinking is sent as BOTH
  `reasoning_content` AND `reasoning` (translate.rs:170-177) — because Kimi
  K2.7 errors in tool loops if prior reasoning is stripped. Downstream it
  accepts either spelling.
- `max_completion_tokens` used only for a hardcoded model list, else
  `max_tokens`; always forces `stream_options:{include_usage:true}` when
  streaming (it needs the usage chunk to render Anthropic usage events).
- CC responses → Anthropic: `reasoning_content`|`reasoning` → thinking block
  with EMPTY signature; missing tool ids fabricated `toolu_<uuid>`;
  unknown finish_reason → `end_turn`; cache token fields lost.
- count_tokens on OpenAI routes = **chars/4 estimate** (http.rs:664-676).

## The gateway tax

What a CC client loses/gains through each gateway vs hitting the backend
directly:

| Dimension | LiteLLM | Bifrost | Superagent GW |
|---|---|---|---|
| CC inbound | yes (core product) | yes (2 doors) | **no** (Messages/Responses only) |
| Silent param drops | unsupported params under `drop_params`; `additional_drop_params` | OpenAI-only params for non-OpenAI upstreams; `user`>64ch; top_p when temperature set (Anthropic path) | n/a inbound |
| Param rewrites | `max_tokens`→`max_completion_tokens` (o-series/gpt-5); response_format→tool trick; user→metadata | `max_tokens`→`max_completion_tokens` at ingress; floor 16; Anthropic max_tokens synthesized | stop_sequences↔stop; max_tokens name per model |
| Errors on unsupported | **500** UnsupportedParamsError (not 400) unless drop_params | mostly silent filtering | n/a |
| Tool-call ids | fabricated `call_*` for id-less providers | passed through | fabricates `toolu_*` |
| Streaming | full re-chunking + finish_reason normalization | raw passthrough openai→openai, else normalized | synthesizes Anthropic events, fake signature_delta |
| Usage | always computed (hidden if not requested) | forwarded + backfill | chars/4 count_tokens; cache fields lost |
| Reasoning handling | provider `reasoning`→`reasoning_content` unification | `reasoning_details` preserved | dual-write both spellings upstream |
| Extras gained | drop_params, mock_response, fallbacks, cost tracking | in-body fallbacks, MCP agent loop, fast path | protocol translation, hybrid /v1/models |
