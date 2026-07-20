# Chat Completions Backend Implementations (local servers)

How the 7 major local inference servers actually serve
`POST /v1/chat/completions` (+ legacy `/v1/completions`). All findings from
direct source examination of local clones (codegraph-indexed), commits of
2026-07-16..18 — provenance in `sources.md`. CC is the oldest compat surface,
so it has accumulated the MOST per-server divergence and vendor extension of
the three protocols (contrast messages-api / responses-api skills).

## Contents
- [Divergence matrix](#divergence-matrix)
- [vLLM](#vllm) · [SGLang](#sglang) · [llama.cpp](#llamacpp) · [Ollama](#ollama)
- [mistral.rs](#mistralrs) · [Llama Stack / OGX](#llama-stack--ogx) · [Lemonade](#lemonade-amd)

## Divergence matrix

| Behavior | vLLM | SGLang | llama.cpp | Ollama | mistral.rs | OGX (Llama Stack) | Lemonade |
|---|---|---|---|---|---|---|---|
| Commit examined | 9243e0124e | 99f5a6f46b | 571d0d5 | 573386c | 0ae0476 | f05b98f | b09a0e9 |
| Reasoning field out | **`reasoning`** (renames incoming `reasoning_content`→`reasoning`) | `reasoning_content` | `reasoning_content` (`reasoning_format` modes) | **`reasoning`** | `reasoning_content` | provider passthrough | backend's |
| Notable silently-ignored params | `user`; `functions`/`function_call` (extra=allow) | `user`; `functions`/`function_call` | none — unknown keys pass through to native params | **`tool_choice`**, **`max_completion_tokens`**, `logit_bias`, `n`, `parallel_tool_calls`, `user` | `seed`, `stream_options`, `parallel_tool_calls`, `user` | none — unknowns forwarded as `extra_body` | none — verbatim proxy |
| Non-OpenAI finish_reasons | `abort`, `repetition` | `abort` | — (but default is `length`) | — | `canceled`, `generated_image`, `generated_speech` | declares deprecated `function_call` | backend's |
| Named tool_choice finish_reason | `"stop"` (OpenAI-conformant) | `"tool_calls"` | n/a (grammar) | tool_choice ignored | `"tool_calls"` | provider's | backend's |
| parallel_tool_calls:false | post-filter to first call | grammar `maxItems:1` (forced modes) | honored (template probe default) | ignored | ignored | forwarded | forwarded |
| Tool-call arg streaming | incremental | incremental + final flush delta | incremental diffs | **whole blob, one chunk** | **whole blob, one delta** (buffered) | passthrough | passthrough |
| seed | honored, always | **no-op without `--enable-deterministic-inference`** | honored | honored | ignored | forwarded | forwarded |
| json_object semantics | true any-JSON grammar | `{"type":"object"}` schema (no top-level arrays) | empty-schema constraint (+nonstandard inline `schema`) | native `format:"json"` | `{"type":"object"}` schema | provider's | backend's |
| json_schema `strict` | ignored (always fully enforced) | ignored (always enforced) | ignored (always enforced) | ignored | not parsed | forwarded | forwarded |
| cached_tokens in usage | `--enable-prompt-tokens-details` | `--enable-cache-report` | **always** (`prompt_tokens_details.cached_tokens`) | never | never | provider's | backend's |
| stream usage chunk | `include_usage` (+`continuous_usage_stats`) | `include_usage` (server-flippable default) | `include_usage` (default false) | `include_usage` | **always on final chunk** (stream_options ignored) | forwarded; **force-injected when telemetry on** | backend's |
| `data: [DONE]` | yes | yes | yes | yes | yes | **never** | backend's (llama-server: yes) |
| system_fingerprint | config hash, terminal chunk only | never (field absent) | build string (`b6xxx-sha`) | constant `"fp_ollama"` | constant `"local"` | provider's | backend's |
| Error envelope | OpenAI-ish, `code`=int status | OpenAI-ish | `code`=int status, no `param`, extra types | full OpenAI shape (param/code null) | **`{"message"}`**, 422 for validation | OpenAI envelope | mixed: object AND bare-string forms; unknown model→404 |
| Legacy /v1/completions | full prompt forms; `suffix`→400; max_tokens=0 echo-scoring OK | `suffix`/`best_of` silently ignored; max_tokens≤0 rejected | validation is **dead code** (echo/best_of/suffix silently ignored); logprobs use CHAT shape | **string prompt only**; `suffix`=FIM; response never carries logprobs | string prompt only; tools extension; no usage in stream chunks | full surface; anthropic/bedrock providers raise | verbatim proxy |

## vLLM

`vllm/entrypoints/openai/` — split per endpoint: `chat_completion/protocol.py`
+ `serving.py`, `completion/*`, shared `engine/protocol.py`.

- **~30 documented extra params** on CC: `top_k`, `min_p`,
  `repetition_penalty`, `stop_token_ids`, `ignore_eos`, `min_tokens`,
  `prompt_logprobs`, `logprob_token_ids`, `allowed_token_ids`, `bad_words`,
  `echo` (chat echo!), `documents`, `chat_template`(+kwargs),
  `structured_outputs`, `priority`, `request_id`, `return_token_ids`,
  `cache_salt`, `kv_transfer_params`, `vllm_xargs`, `repetition_detection`,
  `thinking_token_budget`, `include_reasoning`. `reasoning_effort` accepts
  `xhigh`/`max` (`max` = DeepSeek-V4 extension); non-`none` values inject
  `enable_thinking` into template kwargs.
- **Reasoning rename**: emits `reasoning`; a before-validator silently
  renames incoming `reasoning_content`→`reasoning`
  (chat_completion/protocol.py:484-509) — responses never contain
  `reasoning_content`. `include_reasoning=false` also suppresses
  logprobs/token-id metadata to avoid leaking reasoning tokens.
- tool_choice: field default `"none"` but validator flips to `"auto"` when
  tools present; `"auto"` needs `--enable-auto-tool-choice` + tool parser;
  `required` is grammar-enforced as a JSON **array** schema; named
  tool_choice constrains to that tool's schema and returns finish_reason
  `"stop"` (serving.py:972-999). Per-tool `strict:true` → xgrammar
  structural-tag constrained calling (registered model types only).
- `parallel_tool_calls=false` only post-filters to the first call
  (tool_calls_utils.py:19-37) — generation is NOT constrained.
- Sampling defaults come from the model's `generation_config.json`, not
  OpenAI defaults — a bare request may not sample at temperature 1.0.
- logit_bias clamped ±100 (OpenAI-conformant); `seed` always honored;
  engine finish_reasons `abort`/`repetition` can surface; `error`→HTTP 500.
- Usage: `prompt_tokens_details.cached_tokens` (+vendor
  `created_cache_tokens`, `multimodal_tokens`) gated by
  `--enable-prompt-tokens-details`. `cache_salt` PARTITIONS the prefix cache
  (isolation key) — not a routing hint like OpenAI's `prompt_cache_key`.
- Streaming: first chunk per choice `{role, content:""}`; minimal deltas
  (`exclude_unset`); `stop_reason` vendor field (stop string/token id) on
  every choice; mid-stream errors as `data: {error...}` then `[DONE]` always.
- Siblings: `/v1/chat/completions/render` (tokenize-only) and `/batch`;
  `model` field optional on single-model servers; ids `chatcmpl-<uuid>`.
- Multimodal: `image_url` + `input_audio` + vendor `audio_url`/`video_url`/
  embeds parts; `image_url.detail` ignored with warning.

## SGLang

`python/sglang/srt/entrypoints/openai/` — `serving_chat.py`, `protocol.py`.

- Extensions: `regex`, `ebnf`, `stop_regex`, `lora_path` (also via
  `"model:adapter"` syntax), `session_params`, `separate_reasoning`,
  `stream_reasoning`, `return_hidden_states`, `input_ids` (bypass chat
  template entirely!), `cache_salt`, `extra_key`, `top_k`, `min_p`,
  DeepSeek-V4 `task`. Accepts a non-OpenAI `reasoning: {effort, enabled}`
  object mapped onto `reasoning_effort` + template kwargs.
- **`json_object` is `json_schema='{"type":"object"}'`** (protocol.py:924) —
  top-level arrays/scalars forbidden, unlike OpenAI json mode.
- **`seed` is a silent no-op unless the server runs
  `--enable-deterministic-inference`** (sampling_batch_info.py:114-129).
- Named tool_choice returns finish_reason **`"tool_calls"`**
  (serving_chat.py:1534-1578) — diverges from OpenAI and vLLM ("stop").
  `parallel_tool_calls=false` enforced in-grammar (`maxItems:1`) for
  forced modes. Tool `parameters` validated as JSON Schema 2020-12 → 400 on
  invalid. On parse failure: raw text returned as content (logged, no error).
- Streaming: `reasoning_content`/`finish_reason`/`matched_stop`/`logprobs`
  keys ALWAYS present (null) in chunk choices — deliberate, so OpenAI-SDK
  attribute access never fails; separate empty-delta finish chunk carrying
  vendor `matched_stop`; unstreamed tool args diff-flushed in a final delta;
  graceful abort surfaces as finish_reason `"abort"`; `content_filter`
  declared but never produced.
- Vendor response fields: `metadata.weight_version` on EVERY response;
  usage carries **top-level `reasoning_tokens`** (OpenAI nests it under
  completion_tokens_details); `prompt_tokens_details.cached_tokens` gated by
  `--enable-cache-report`; optional `sglext` chunk (routed experts / cache
  details) with `choices:[]` before the usage chunk.
- `ToolCall.function.arguments` may be str OR dict in histories.
- No `input_audio` content part (use `audio_url`); no `file` part;
  logit_bias unclamped; completions `text_offset` always -1;
  `logprobs`+`tools`+`stream` is fine here (llama.cpp 400s).
- gpt-oss/harmony models: `reasoning_effort="none"` raises.

## llama.cpp

`tools/server/` — two-layer parse: OAI translation
(`oaicompat_chat_params_parse`, server-common.cpp:905) then a declarative
field schema (server-schema.cpp) evaluated for every completion-type request.

- **Passthrough rule**: after OAI translation, ALL remaining body keys are
  copied verbatim into native params — `mirostat`, `min_p`, `top_k`, `dry_*`,
  `samplers`, `cache_prompt`, `lora`, `n_probs`, `id_slot`, `timings_per_token`
  all work on `/v1/chat/completions`. Unknown keys silently ignored.
- Limits: soft limits clamp silently (top_p→[0,1], temperature→[0,∞) — the
  OpenAI 0..2 range is not enforced); hard limits 400 (`n` = alias of
  `n_cmpl`, capped at server `n_parallel`; max_tokens). `null` param = server
  default (SDK explicit-null safe). `max_completion_tokens` AND `max_tokens`
  both alias `n_predict`.
- **Default finish_reason is `"length"`** — only EOS/stop-word yields
  `"stop"`/`"tool_calls"` (server-task.cpp:486-491).
- logit_bias: accepts OpenAI object AND native array form, **string keys are
  tokenized** (multi-token strings get bias on each token); `false` = −∞ ban.
- Tools require `--jinja`; tools force a (lazy) template-generated grammar;
  user `grammar` + tools → 400; `logprobs`+`tools`+`stream` → 400;
  `top_logprobs` defaults to 20 when `logprobs:true`.
- Streaming: incremental tool-call argument diffs (`common_chat_msg_diff`);
  first chunk `{role:"assistant", content:null}`; separate finish chunk;
  first-error-as-non-stream-JSON (OAI-matching), mid-stream errors as
  `data:{"error":...}`; SSE comment pings (`":"`) on `sse_ping_interval`.
- **Vendor `timings` object** on final response AND last chunk always
  (`cache_n`, `prompt_per_second`, …; per-chunk with `timings_per_token`) —
  strict response validators must tolerate it (and `prompt_progress` chunks
  with `return_progress`).
- Caching: `cache_prompt` defaults TRUE; `usage.prompt_tokens_details.cached_tokens`
  in every usage object — the only local server reporting cached tokens
  unconditionally.
- Reasoning: `reasoning_content` per server-level `--reasoning-format`
  (default deepseek; `none` leaves inline `<think>` in content),
  request-overridable via `reasoning_format` body field; vendor
  `thinking_budget_tokens`, `reasoning_control`, `chat_template_kwargs`.
- Multimodal: `image_url` accepts http(s) (server downloads, 10MB/10s cap),
  data URIs, RAW base64 without prefix, `file://` (with `--media-path`);
  nonstandard `input_video` part.
- Legacy: `/v1/completions` OAI validation is **dead code at HEAD** — old
  echo/best_of/suffix rejections are gone, params silently ignored;
  logprobs come back in the CHAT shape (known TODO); token-array prompts
  fine. FIM lives on `/infill` (native schema, needs FIM vocab tokens;
  `input_prefix`/`input_suffix`/`input_extra` repo context). Also a distinct
  native `/completions` (non-OAI schema) — do not confuse with
  `/v1/completions`.
- Errors: `error.code` is an INT http status; extra types like
  `exceed_context_size_error`. `system_fingerprint` = build string.

## Ollama

`openai/openai.go` shim + `middleware/openai.go` over the native API.

- **Silently dropped** (struct simply lacks the fields):
  **`tool_choice`** (forced tool calls no-op — the single worst CC trap),
  **`max_completion_tokens`** (new-SDK clients get UNBOUNDED generation),
  `logit_bias`, `n`, `parallel_tool_calls`, `user`, `functions`/`function_call`,
  `store`, `metadata`, `prediction`, `audio`, `modalities`, `service_tier`.
- Injects `temperature=1.0`/`top_p=1.0` defaults when absent — overriding
  Modelfile options; no unknown-key passthrough (unlike llama.cpp).
- `reasoning_effort` → native `think` (`low/medium/high/max` pass, `none`→
  false; `minimal` → 400). Reasoning comes back as **`reasoning`** (not
  `reasoning_content` — DeepSeek-convention clients see nothing).
- Streaming: **`role:"assistant"` on every chunk**; **tool-call arguments as
  one whole JSON blob in a single chunk**; thinking+content native chunks
  split into two same-timestamp chunks (logprobs kept on the reasoning one);
  `toolCallSent` flag forces final finish_reason `tool_calls` even on
  length-stop. `/v1/completions` + include_usage: every chunk carries a
  ZERO-usage object (not null), real usage in the final chunk.
- ids are `chatcmpl-<rand 0-999>` — 3-digit random, collision-prone;
  `system_fingerprint` constant `"fp_ollama"`; no cached-token reporting at
  all despite internal prompt caching.
- Multimodal: **http(s) image URLs rejected 400** (base64 data URIs only);
  content parts become SEPARATE native messages (not merged).
- Structured outputs: `json_object`→`format:"json"`, `json_schema`→ raw
  schema passthrough to native grammar; unknown response_format types
  silently ignored. No strict-tools grammar.
- Server tools: uniquely EXECUTES `web_search` server-side (see
  messages-api skill; applies on its Anthropic surface).
- Legacy: `prompt` string-only (issue #5259); `suffix` = FIM (Modelfile
  suffix template — Ollama's whole FIM story); logprobs accepted in request,
  never in response.
- Errors: full OpenAI envelope, `param`/`code` always null.

## mistral.rs

`mistralrs-server-core/src/openai.rs` + `chat_completion.rs`.

- **`messages` accepts a raw STRING** in place of the array
  (`Either<Vec<Message>, String>`) — becomes one user message.
- Silently dropped via serde: `seed`, `stream_options`, `parallel_tool_calls`,
  `user`, `store`, `metadata`, `service_tier`, `prediction`,
  `functions`/`function_call`. `max_completion_tokens` is only a serde ALIAS
  of max_tokens. logit_bias keys must be numeric (`HashMap<u32,f32>`).
- Extensions: `grammar` (regex | json_schema | lark | llguidance), DRY
  sampling quartet, `web_search_options`, `enable_thinking`, `enable_shell`,
  `agent_permission`, `session_id`, `max_tool_rounds`, `files`,
  `truncate_sequence`, `top_k`, `min_p`. Responses-style FLAT function tools
  accepted alongside nested CC form; `tools[].type=web_search` on CC → 400
  ("use web_search_options").
- **Server-side agentic loop ON the CC endpoint** — triggers only when
  `web_search_options` / registered MCP-or-tool-callbacks / `max_tool_rounds`
  / `tool_dispatch_url` / input files are present (otherwise plain CC).
  Executes only the FIRST tool call per round (default 256 rounds); client
  sees ONE final message with aggregated usage + extension fields
  `agentic_tool_calls`, `files`, `session_id`; streaming emits named SSE
  events (`agentic_tool_call_progress`, `agentic_tool_approval_required`,
  `file_produced`). Known bug-shape: streaming + agentic trigger + a
  client-owned tool → tool_calls delta suppressed, stream just ends
  (non-stream path returns them correctly).
- finish_reasons: stop/length/tool_calls + non-standard `canceled`,
  `generated_image`, `generated_speech`; named tool_choice → `tool_calls`.
- Streaming: tool calls buffered and emitted as ONE complete delta per call
  (id `call-<uuid>`, full arguments); `delta.role` on every chunk; usage
  ALWAYS on the final chunk (rides on the finish chunk, no separate usage
  chunk; stream_options ignored); chunk `created` is millis (non-stream is
  seconds); **stream errors are raw non-JSON `data:` lines** before `[DONE]`.
- Errors: `{"message": "..."}` — NOT the OpenAI envelope; validation → 422.
- Legacy: `prompt` String-only; supports best_of/echo/suffix/logprobs(int);
  `tools` as extension; NO response_format; NO usage in stream chunks.

## Llama Stack / OGX

`src/ogx_api/inference/` — router over ~22 REMOTE providers (openai,
anthropic-via-CC-compat, vllm, ollama, gemini, groq, bedrock, together, …);
CC fidelity ≈ the routed provider's.

- Request model `extra="allow"`: unknown params forwarded to the provider as
  OpenAI-SDK `extra_body` — nothing rejected (vLLM `top_k`, `guided_json`
  etc. just work). The ONLY surveyed server still modeling deprecated
  `functions`/`function_call` (models.py:986-988), and it declares
  `function_call` as a possible finish_reason (models.py:638).
- `reasoning_effort` accepts `none..xhigh`; `prompt_cache_key` (≤64 chars)
  modeled. `tool_choice="none"` clears BOTH tool_choice and tools before
  forwarding ("some providers make tool calls even when tool_choice is
  none").
- **Never emits `data: [DONE]`** — clients keying on the sentinel mis-detect
  termination. Mid-stream errors as OpenAI-envelope SSE data events.
- Telemetry force-injects `stream_options.include_usage=true` upstream when
  an OTel span records, and the resulting usage chunk is passed to the
  client — unrequested extra final chunk.
- **Stored completions** (unique among local servers): SQLite(WAL)/Postgres;
  GET list (cursor pagination, model filter) / GET {id} (includes
  `input_messages` — richer than OpenAI) / GET {id}/messages. Stored
  whenever a store is configured — the OpenAI `store` param is NOT
  consulted. Streams re-assembled from deltas for storage.
- Per-provider fixups: anthropic empty tool `parameters:{}` →
  `{"type":"object"}`; vllm `developer`→`system` rewrite.
- Legacy: full OpenAI surface incl. token-array prompts; anthropic/bedrock
  providers raise NotImplementedError.

## Lemonade (AMD)

`src/cpp/server/` — validating/telemetry PROXY, not an implementation: raw
body forwarded to the per-model backend (llama-server, FLM/NPU, OGA, vLLM,
cloud).

- **Quad-prefix routing**: every endpoint under `/api/v0`, `/api/v1`, `/v0`,
  `/v1` — all identical.
- Forwards everything verbatim EXCEPT: strips `:latest` model suffixes;
  converts `enable_thinking:false` / `thinking:false` /
  `thinking:{type:"disabled"}` into a `/no_think\n` prefix on the last user
  message then strips those fields (chat only); extracts non-standard
  `ctx_size` as an auto-load option; collection models get `model` rewritten
  + `x_lemonade_route` injected into the first SSE chunk / response body.
- First request to an unloaded model blocks on download+load (minutes).
- Error shapes INCONSISTENT: OpenAI-ish object for load errors (unknown
  model → **404**), bare-string `{"error":"..."}` for generic 500s, backend
  errors wrapped. Backend watchdog can transparently restart + retry.
- Server-side tool loop only for "collection" models; llama-server's
  `timings` vendor field passes through.
