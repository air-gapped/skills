# Official Chat Completions + Legacy Completions Spec

The OpenAI-side ground truth, verified 2026-07-19 against developers.openai.com
(platform.openai.com 301s there and 403s scripted fetches; `llms.txt` indexes
and `.md` twins exist for docs pages — Stainless reference method pages have
stub `.md` twins, use the HTML). URL-per-section index in `sources.md`.

Status: **fully supported, not deprecated, but second-choice** — the create
page banners "Starting a new project? We recommend trying Responses". No
sunset date exists.

## Contents
- [Request schema highlights](#request-schema-highlights)
- [Prompt caching (explicit breakpoints)](#prompt-caching)
- [Response and finish_reason](#response-and-finish_reason)
- [Streaming chunk anatomy](#streaming-chunk-anatomy)
- [Stored completions](#stored-completions)
- [Legacy /v1/completions](#legacy-v1completions)
- [Deprecation archaeology](#deprecation-archaeology)
- [What CC does NOT get (Responses-only delta)](#responses-only-delta)

## Request schema highlights

The non-obvious parts of `POST /v1/chat/completions` (full reference: create
page, see sources.md):

- **Roles**: `developer`, `system`, `user`, `assistant`, `tool`, plus
  deprecated `function`. User content parts: `text`, `image_url` (with
  `detail`), `input_audio` (`{data, format: wav|mp3}`), `file`
  (`{file_data|file_id, filename}`).
- **tool_choice has FOUR forms**: `"none"|"auto"|"required"`,
  `{type:"function", function:{name}}`, `{type:"allowed_tools",
  allowed_tools:{mode:"auto"|"required", tools:[...]}}` (subset constraint),
  and `{type:"custom", custom:{name}}`.
- **tools has TWO types**: `function` (with optional `strict`) and `custom` —
  freeform-input tools with optional `format: {type:"grammar",
  grammar:{definition, syntax:"lark"|"regex"}}`. Assistant messages can carry
  `type:"custom"` tool calls with `input` instead of `arguments`.
- **reasoning_effort** enum: `none|minimal|low|medium|high|xhigh|max`.
  Defaults are model-dependent: GPT-5.1+ default `none`, gpt-5.5 default
  `medium`. `max` arrived with GPT-5.6 (2026-07), `xhigh` with GPT-5.2
  (2025-12), `minimal` with GPT-5 (2025-08).
- **moderation** (new 2026-06-04): `{model, policy:{input/output:
  {mode:"score"|"block"}}}` request param; results ride back in a
  `moderation` block on both the completion and chunk objects. Most
  third-party implementations do not know this field exists.
- **verbosity**: `low|medium|high` (GPT-5+). **prediction**: predicted
  outputs (`{type:"content", content}`); rejected prediction tokens ARE
  billed. **web_search_options**: `{search_context_size, user_location}` —
  CC's only built-in tool. **service_tier**: `auto|default|flex|scale|priority`
  (response echoes the tier actually used).
- **store**: enables the stored-completions surface (below); image inputs
  >8MB are dropped from storage. `metadata`: ≤16 pairs, key ≤64 / value ≤512
  chars, filterable in list calls.
- `stop` is "not supported with latest reasoning models"; `max_completion_tokens`
  includes reasoning tokens in its bound.

## Prompt caching

CC gained Anthropic-style explicit caching in the GPT-5.6 era — both APIs,
per the caching guide ("Breakpoints are available in both the Responses API
and Chat Completions API"):

- Request-level `prompt_cache_options: {mode:"implicit"(default)|"explicit",
  ttl:"30m"}` + per-content-block `prompt_cache_breakpoint:
  {mode:"explicit"}` on text/image_url/input_audio/file/refusal parts.
- Implicit mode: 1 implicit + up to latest 3 explicit breakpoints written;
  explicit mode: up to 4 explicit, and NO caching if none set. Max 4 cache
  writes per request. (Doc inconsistency: create page says matching considers
  "latest 80 breakpoints", caching guide says 50.)
- Usage gained `prompt_tokens_details.cache_write_tokens` — cache writes
  billed at 1.25× uncached input on GPT-5.6+.
- `prompt_cache_key` (replaces `user` for cache routing); `prompt_cache_retention`
  is already deprecated in favor of `prompt_cache_options.ttl` (retention
  expressed a MAX lifetime, ttl a MIN — independent semantics).

## Response and finish_reason

- Official finish_reason enum, complete: `stop | length | content_filter |
  tool_calls | function_call` (deprecated). Third-party servers emit values
  outside this set — see the divergence table in
  `backend-implementations.md`.
- `message` fields beyond content: `refusal`, `annotations`
  (`url_citation` spans), `audio` (`{id, data, expires_at, transcript}` —
  id is replayable in later turns), `tool_calls` (function or custom).
- `usage.completion_tokens_details`: `reasoning_tokens`, `audio_tokens`,
  `accepted_prediction_tokens`, `rejected_prediction_tokens`.
  `usage.prompt_tokens_details`: `cached_tokens`, `audio_tokens`,
  `cache_write_tokens`.
- `system_fingerprint` is formally **Deprecated** (as is request `seed`) —
  the determinism story is retired.
- logprobs: `{content, refusal}` arrays of `{token, bytes, logprob,
  top_logprobs}`; `-9999.0` is the outside-top-20 sentinel.

## Streaming chunk anatomy

- Delta assembly rules: `role` on the first chunk only;
  `delta.tool_calls[].index` is the REQUIRED assembly key (id + function.name
  on the first fragment, incremental `arguments` after); final content chunk
  has empty `delta` + `finish_reason`.
- `stream_options.include_usage`: adds one final pre-`[DONE]` chunk with
  `choices: []` and populated `usage`; all other chunks carry `usage: null`;
  interrupted streams may never deliver it.
- `stream_options.include_obfuscation`: **on by default** — an `obfuscation`
  field of random characters is added to delta events to normalize payload
  sizes (side-channel mitigation), yet it does not appear in the published
  chunk schema. Set false to save bandwidth on trusted links.
- Terminal sentinel: `data: [DONE]`. `choices` may be empty (usage chunk) or
  >1 element (n>1).

## Stored completions

Five endpoints over completions created with `store: true`:
`GET /v1/chat/completions` (list; filters: `metadata[key]=value`, `model`,
cursor `after`, `order`), `GET /{id}`, `GET /{id}/messages` (input messages,
with `content_parts`), `POST /{id}` (update — metadata only), `DELETE /{id}`
(returns `object:"chat.completion.deleted"`). Llama Stack/OGX is the only
local implementation of this sub-surface (see backend-implementations.md).

## Legacy /v1/completions

- Documented models: `gpt-3.5-turbo-instruct`, `davinci-002`, `babbage-002` —
  **all shut down 2026-09-28** (with `gpt-3.5-turbo-1106`; replacements
  gpt-5.4-mini/gpt-5-mini). The 2026-10-23 sweep line-items the
  `-completions` endpoint variants of chat models (`gpt-3.5-turbo-completions`,
  `gpt-4-completions`, `gpt-4-turbo-completions`). After October 2026 OpenAI
  serves no first-party model on this endpoint — it survives only as a
  third-party/local surface.
- Param quirks vs chat: `prompt` accepts string | string[] | token int[] |
  token int[][]; **`logprobs` is an INTEGER 0..5** (not bool+top_logprobs);
  `suffix` (insertion) is gpt-3.5-turbo-instruct-only; `echo`; `best_of`
  (server-side best-by-logprob, cannot stream, must exceed `n`); `max_tokens`
  default 16; `seed`/`user` NOT marked deprecated here.
- Response `object:"text_completion"`; logprobs shape is the legacy
  `{tokens, token_logprobs, top_logprobs, text_offset}`; finish_reason has no
  `tool_calls`. Docs note: streamed and non-streamed objects share the same
  shape (unlike chat).
- Local-server fidelity varies widely — see the legacy row in
  `backend-implementations.md` (vLLM 400s on suffix; Ollama is string-prompt
  only but suffix=FIM; llama.cpp's OAI validation is dead code at HEAD).

## Deprecation archaeology

| Deprecated | Replacement | Notes |
|---|---|---|
| `functions` / `function_call` | `tools` / `tool_choice` | Still served; llama-stack is the only local server still modeling them |
| `max_tokens` | `max_completion_tokens` | "not compatible with o-series models"; bound includes reasoning tokens |
| `user` | `safety_identifier` (abuse) + `prompt_cache_key` (cache routing) | reference: "being replaced by" |
| `seed` + response `system_fingerprint` | — | both marked Deprecated; determinism retired |
| `prompt_cache_retention` | `prompt_cache_options.ttl` | retention=max vs ttl=min semantics |
| `function` role messages | `tool` role | |
| Assistants API | Responses + Conversations | shutdown 2026-08-26 |

## Responses-only delta

Features that never reach Chat Completions (changelog-verified): built-in
tools (web search beyond `web_search_options`, file search, computer use,
code interpreter, remote MCP, connectors), Conversations API, compaction
(all three kinds), tool search, hosted shell, apply_patch, Skills, `phase`
field, WebSocket mode, background mode/webhooks, reusable prompts
("not available in Chat Completions", verbatim), **Programmatic Tool
Calling** and pro reasoning mode (GPT-5.6), persisted reasoning, and most
codex-model launches.

CC-only relic: **audio output** — `modalities`/`audio` params and
gpt-audio-1.5 live on Chat Completions. CC also got moderation scores and
explicit prompt caching at parity with Responses.
