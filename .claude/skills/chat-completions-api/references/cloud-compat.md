# Cloud providers' Chat-Completions-compatible endpoints

Documented deviations from the OpenAI CC contract across 10 non-OpenAI cloud
products. All from official vendor docs, fetched 2026-07-19 (URLs in
`sources.md`). The #1 cross-provider trap is the **failure-mode split**:
some providers silently ignore unsupported params, others hard-400 on them —
a portable client must know which is which.

## Contents
- [Gotcha matrix](#gotcha-matrix)
- [Anthropic (OpenAI SDK compatibility layer)](#anthropic-openai-sdk-compatibility-layer)
- [Google Gemini](#google-gemini-beta) · [DeepSeek](#deepseek-cc-is-their-native-api) · [xAI Grok](#xai-grok)
- [Groq](#groq) · [Mistral](#mistral) · [Together / Fireworks](#together--fireworks)
- [OpenRouter](#openrouter-the-normalizer) · [Azure OpenAI](#azure-openai-foundry)

## Gotcha matrix

| Gotcha | Providers |
|---|---|
| Unsupported params **silently ignored** | Anthropic, Gemini, DeepSeek (sampling in thinking mode) |
| Unsupported params **rejected 400** | Groq (`logprobs`, `logit_bias`, `top_logprobs`, `messages[].name`), xAI reasoning models (`presence_penalty`, `frequency_penalty`, `stop`) |
| `n` must be 1 | Anthropic, Groq |
| Temperature range ≠ OpenAI 0..2 | Anthropic (0..1, capped), Groq (0 → 1e-8), Mistral (per-model) |
| tool `strict` not honored | Anthropic (ignored — no schema guarantee) |
| `response_format` ignored entirely | Anthropic |
| Reasoning field name | `reasoning_content` (DeepSeek, xAI CC), `reasoning` (Together, Groq parsed, OpenRouter), inline `<think>` (Groq raw), hidden (Anthropic compat) |
| Reasoning must be passed BACK in tool loops | DeepSeek v4 (with tool calls), OpenRouter (exact block sequence) |
| Silent truncation on context overflow | Fireworks (`context_length_exceeded_behavior: truncate` default) |
| System messages repositioned | Anthropic (all hoisted + `\n`-concatenated to one initial system) |
| CC declared legacy, Responses promoted | xAI, Groq, Azure; OpenAI itself banner-recommends Responses |

## Anthropic (OpenAI SDK compatibility layer)

Base `https://api.anthropic.com/v1/`, Anthropic key, Claude model names.
Positioning verbatim: "primarily intended to test and compare model
capabilities … not considered a long-term or production-ready solution".

- Rule: "Most unsupported fields are silently ignored rather than producing
  errors." Ignored: `response_format` (use native structured outputs!),
  `reasoning_effort`, tool `strict`, `logprobs`, `logit_bias`, `seed`, `n`≠1
  rejected, penalties, `store`, `metadata`, `prediction`, `service_tier`,
  `audio`/`input_audio` (stripped), `image_url.detail`, `messages[].name`.
- `temperature` capped at 1 (Anthropic range). System/developer messages are
  ALL hoisted and concatenated (`\n`) into one initial system message —
  mid-conversation system turns lose position.
- Thinking via `extra_body {"thinking": {...}}` — improves output but the
  trace is NOT returned through CC. No prompt caching through this layer.
- Always-empty response fields: `usage.*_tokens_details`, `refusal`,
  `audio`, `logprobs`, `service_tier`, `system_fingerprint`. Error formats
  match OpenAI but messages differ ("only use … for logging").

## Google Gemini (beta)

Base `https://generativelanguage.googleapis.com/v1beta/openai/`. "Any other
parameters … will be silently ignored."

- `reasoning_effort` → fixed thinking budgets: minimal/low=1,024,
  medium=8,192, high=24,576; `none` disables thinking on 2.5 models only —
  "Reasoning cannot be turned off for Gemini 2.5 Pro or 3 models". Can't
  combine with native `thinking_level`/`thinking_budget`.
- Extensions via `extra_body`: `cached_content`, `thinking_config`
  (incl. include_thoughts), `safety_settings`, image/video params.
- Tools + structured outputs fully supported; audio input actually works
  (unlike Anthropic's layer); `service_tier` accepted (`priority`, `flex`,
  default `standard`). Also: embeddings, image gen, async video (poll
  `/v1/videos/{id}`), Batch.

## DeepSeek (CC is their native API)

Bases: `api.deepseek.com` (OpenAI format), `/anthropic` (Anthropic format),
`/beta` (prefix completion + FIM).

- **`deepseek-chat` / `deepseek-reasoner` names die 2026-07-24**; current:
  `deepseek-v4-flash`, `deepseek-v4-pro`. Thinking defaults ENABLED
  (`extra_body {"thinking":{"type":"enabled"}}` to control); effort default
  high, "automatically max for complex agent requests".
- Originated the `reasoning_content` convention (delta + message level).
- Thinking mode: `temperature`/`top_p`/penalties "will not trigger an error
  but will also have no effect" — silent no-op.
- **Inverted pass-back rule (v4)**: without tool calls, intermediate
  `reasoning_content` need not be resent; **with tool calls it MUST be
  passed back** — clients that strip reasoning break agentic loops.
- Beta: Chat Prefix Completion (last message `role:"assistant"` +
  `prefix:true`, e.g. seed ```` ```python ```` + `stop:["```"]`); FIM on
  `/completions` with `prompt`+`suffix`, max 4K tokens.

## xAI Grok

Base `https://api.x.ai/v1`. "Chat Completions is offered as a legacy
endpoint. New features will come to the Responses API first."

- Reasoning models **400 on** `presence_penalty`, `frequency_penalty`,
  `stop` (the classic n8n integration failure). Reasoning cannot be
  disabled; `reasoning_effort` model-dependent (grok-4.5: low/medium/high;
  grok-4.20-multi-agent uses it to pick agent count).
- CC responses use `reasoning_content` (DeepSeek spelling); raw traces are
  mostly encrypted (Responses-side `reasoning.encrypted_content`).
- Vendor extension — **deferred completions**: POST with `"deferred": true`
  → `{request_id}`; poll `GET /v1/chat/deferred-completion/{id}` (202 while
  pending); result readable **exactly once within 24h**.

## Groq

Base `https://api.groq.com/openai/v1`.

- **400s (not ignores)**: `logprobs`, `logit_bias`, `top_logprobs`,
  `messages[].name`; `n` must be 1. temperature 0 silently becomes 1e-8.
- Reasoning: `reasoning_format` = `parsed` (dedicated `message.reasoning`) |
  `raw` (inline `<think>`) | `hidden`; **`raw` + JSON mode/tools → 400**
  (auto-switches to parsed when unset). `include_reasoning` mutually
  exclusive with reasoning_format. Groq promotes its own Responses API.

## Mistral

Base `api.mistral.ai/v1` — CC-shaped native API, not a strict clone:
**`random_seed`** instead of `seed`; extensions `safe_prompt`,
`prompt_mode:"reasoning"`, `reasoning_effort` (none..xhigh),
`prompt_cache_key` (cached tokens billed at 10%), `prediction`,
`guardrails`. Temperature range is per-model (discover via `/models`).

## Together / Fireworks

- Together (`api.together.ai/v1`): reasoning in **`reasoning`** field;
  `logprobs` in Together's own richer shape; `seed` best-effort; `n` and
  `logit_bias` model-dependent; `service_tier`/`store`/`metadata`/
  `prediction` accepted-but-ignored; no moderations endpoint.
- Fireworks (`api.fireworks.ai/inference/v1`): **silently truncates on
  context overflow by default** (`context_length_exceeded_behavior:
  truncate` lowers max_tokens; set `error` for OpenAI behavior); streaming
  usage ALWAYS on final chunk (no stream_options needed); extensions
  `top_k`, `min_p`, `repetition_penalty`, `mirostat_*`,
  `prompt_truncate_len`, `raw_output`, `echo`, `perf_metrics_in_response`.

## OpenRouter (the normalizer)

Base `openrouter.ai/api/v1`.

- Response carries normalized `finish_reason` PLUS `native_finish_reason`
  (raw provider value); errors normalized `{code, message, metadata}` with
  raw provider error inside; `model` = actual model served.
- **Unified reasoning**: request `reasoning: {effort | max_tokens, exclude,
  enabled}` (effort accepts max..none; Anthropic gets budget percentages —
  max/xhigh=95%, high=80%, medium=50%, low=20%, minimal=10%, min 1024;
  Gemini 3 gets thinkingLevel). Response: `message.reasoning` (plaintext) +
  `message.reasoning_details` (typed blocks).
- **Tool-loop preservation**: pass reasoning back via
  `reasoning`/`reasoning_details`; "the entire sequence of consecutive
  reasoning blocks must match the outputs generated by the model during the
  original request" — critical for Anthropic signed thinking routed through
  OpenRouter.
- Request-level `provider` object controls routing/fallbacks; middle-out
  compression is now a plugin (formerly `transforms:["middle-out"]`).

## Azure OpenAI (Foundry)

- **v1 API (GA Aug 2025)**: base `https://<res>.openai.azure.com/openai/v1/`,
  vanilla `OpenAI()` client, NO `api-version` param, plain
  OPENAI_BASE_URL/OPENAI_API_KEY; Entra ID tokens work through the vanilla
  client. Preview features opt-in via feature headers, not api-versions.
- **`model` field is still the DEPLOYMENT name**, not the model id.
- Legacy dated api-versions silently lack newer params
  (`max_completion_tokens`, `reasoning_effort`, `stream_options`, structured
  outputs each arrived in specific versions). v1 also fronts non-OpenAI
  models (DeepSeek, Grok) speaking v1 CC syntax.
