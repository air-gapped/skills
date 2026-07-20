# What real agent clients send to /v1/chat/completions

Wire-level behavior of CC clients — the tolerance requirements a third-party
CC server must meet. Source: opencode v1.18.3-era source plus the EXACT pinned
Vercel AI SDK tarballs (`@ai-sdk/openai@3.0.84`,
`@ai-sdk/openai-compatible@2.0.41`, `@ai-sdk/provider-utils@4.0.38`).
Examined 2026-07-19; provenance in `sources.md`.

opencode has THREE distinct CC wire paths:
1. **`@ai-sdk/openai-compatible`** — the default for ALL custom/local
   providers (provider.ts:1216).
2. **`@ai-sdk/openai` chat mode** — only via explicit `.chat()` routing.
   Beware: `createOpenAI()`'s DEFAULT model class is the **Responses API** —
   a plain baseURL override on the openai provider hits `/responses`, not
   `/chat/completions` (the SDK detects the mismatch and suggests `.chat()`
   or openai-compatible).
3. **Native `@opencode-ai/llm`** — hand-written CC protocol, only for
   providerID `openai`/`anthropic`/`opencode*` (the Zen path).

## Contents
- [Request shape differences](#request-shape-differences)
- [Tool schema handling](#tool-schema-handling)
- [Streaming parser tolerance](#streaming-parser-tolerance)
- [Retry and defaults](#retry-and-defaults)
- [Server tolerance checklist](#server-tolerance-checklist)

## Request shape differences

| Aspect | openai-compatible 2.0.41 | openai 3.0.84 chat |
|---|---|---|
| max tokens key | `max_tokens` always | `max_completion_tokens` for (forced-)reasoning models, else `max_tokens` |
| stream_options | `{include_usage:true}` when includeUsage (opencode forces on) | unconditional |
| temperature/top_p | verbatim | **stripped for reasoning models** (model-id sniffed: o1/o3/o4-mini/gpt-5*) |
| system role | `system` | `developer` for reasoning models |
| assistant tool-turn content | `""` (string) | `null` |
| replayed reasoning | `reasoning_content` on assistant msgs | never sent |
| reads reasoning | `reasoning_content` ?? `reasoning` | **neither — silently dropped** |
| chunk `choices[].index` | optional | REQUIRED (validation failure without) |
| `tool_calls[].index` | optional (missing = append) | REQUIRED |
| store / prompt_cache_key | no | opencode sets `store:false` + `prompt_cache_key:<sessionID>` |
| tool `strict` | absent | opencode forces `strict:false` (Codex parity) |
| tool schemas | verbatim | Codex-mirror keyword-whitelist sanitizer |
| parallel_tool_calls | never sent | opt-in (opencode: never) |

The model-id sniffing on the openai path is why local reasoning models
belong on openai-compatible: a local model named "o3-something" would get
its temperature silently deleted, and its `reasoning_content` output
silently discarded.

- **Arbitrary passthrough**: unknown keys under
  `providerOptions[<provider>]` are spread verbatim into the body — opencode
  uses this for `chat_template_args`, `thinking:{...}`, `enable_thinking`.
  Message- and part-level metadata is spread INTO message JSON — e.g.
  `cache_control:{type:"ephemeral"}` on content parts for anthropic-flavored
  models over compat transport. Servers must ignore unknown keys at every
  level.
- Interleaved-reasoning replay: models cataloged with an interleaved field
  (auto-defaulted for custom deepseek models) get `reasoning_content`
  (possibly `""` — deliberately always set) on replayed assistant messages.
- Headers: `Authorization: Bearer` (compat omits it entirely when no key);
  opencode adds `x-session-affinity`/`X-Session-Id` and replaces the SDK
  User-Agent with `opencode/<version> ai-sdk/provider-utils/... runtime/...`
  — don't fingerprint on "ai-sdk/openai-compatible", it's replaced.

## Tool schema handling

- The AI SDK itself never mutates tool schemas — no injected `strict`, no
  `additionalProperties:false`. (`strict` default-true applies only to
  `response_format.json_schema`, which opencode never sends in agent loops —
  factory `supportsStructuredOutputs` defaults false, so JSON output would
  use `json_object`.)
- opencode's openai/azure path: `strict:false` on every tool + a
  Codex-mirror sanitizer that whitelists schema keywords ($ref, enum,
  properties, required, items, additionalProperties, anyOf/oneOf/allOf,
  type, …), drops formats/min/max, converts boolean schemas to
  `{type:"string"}`, forces `properties:{}` on objects.
- opencode's compat path: schemas pass through unmodified except targeted
  fixups (Moonshot `$ref`-sibling stripping, Gemini enum coercions).
- The native path is the only one injecting `additionalProperties:false`
  (plus root-anyOf flattening).
- Other hygiene: tool entries sorted alphabetically; failed tool names
  retried lowercased; mistral/devstral tool-call ids rewritten to exactly
  9 alphanumerics; deepseek models get `reasoning_content:""` appended to
  every assistant message.

## Streaming parser tolerance

Both AI SDK paths ignore `data: [DONE]` (stream close ends the turn) and
validate every data payload; a failed parse becomes an error part.

openai-compatible parser (loose):
- `choices` required but may be `[]`; `delta.role` may be `assistant` on ANY
  chunk (other role values fail the zod enum); unknown keys ignored.
- Reasoning read from `delta.reasoning_content ?? delta.reasoning`.
- Tool calls: missing index = append ("google does not send index"); FIRST
  delta per index MUST carry `id` + `function.name` or the stream dies with
  InvalidResponseDataError; whole-blob arguments work. **Hazard**: arguments
  are finalized the moment the accumulated string parses as valid JSON — a
  server streaming `{}` then more text gets truncated at `{}`.
- finish_reason: stop/length/content_filter kept, function_call|tool_calls →
  tool-calls, anything else/missing → "other". Usage read incl.
  `prompt_tokens_details.cached_tokens`,
  `completion_tokens_details.reasoning_tokens`.

openai chat parser (strict where local servers get sloppy):
- `choices[].index` and `tool_calls[].index` REQUIRED; `tool_calls[].type`
  if present must be `"function"`; **no reasoning fields in the schema at
  all** (silently stripped).
- Pre-scans the stream until first real output; error frames before that are
  thrown as APICallError with status inferred from code/type keywords
  (rate_limit→429, authentication→401, overload→503).
- Reads `annotations`, logprobs, `prompt_tokens_details.cache_write_tokens`.

Native path: reads ONLY `reasoning_content` (not `reasoning`); tool delta
`index` required; args JSON-parsed eagerly at finish — parse failure fails
the stream; `stop` with accumulated tool calls coerced to tool-calls.

## Retry and defaults

- opencode disables the SDK's internal retries (maxRetries 0) and wraps the
  stream with its own **unbounded** policy: retry on 408/409/429/5xx +
  network errors + text-sniffed "rate limit"/"exhausted"/"unavailable";
  honors `retry-after-ms` > `retry-after` (secs or HTTP-date) > exponential
  2s×2 capped 30s. Plain 400s are NOT retried — make validation errors
  precise or clients retry-storm.
- temperature sent ONLY if the model catalog flags the capability (custom
  models default false → no temperature key at all); model-id defaults
  (qwen 0.55, kimi-k2 0.6, gemini/glm 1.0). `maxOutputTokens` =
  min(model limit, 32000) always sent. finish_reason unrecognized →
  "unknown" (tool loops need standard `tool_calls` to continue).
- Default 10s header timeout on the openai provider path; optional
  `chunkTimeout` aborts stalled SSE.

## Server tolerance checklist

Distilled requirements for a third-party CC server to survive real clients:

1. Ignore unknown top-level body keys (`chat_template_args`, `thinking`,
   `enable_thinking`, `store`, `prompt_cache_key`, `reasoning_effort`,
   `verbosity`) AND unknown keys inside messages/parts (`reasoning_content`,
   `cache_control`).
2. Accept both `max_tokens` and `max_completion_tokens`.
3. Honor `stream_options.include_usage` with a final `choices:[]` usage
   chunk.
4. Always include `choices[].index` and `tool_calls[].index` in chunks
   (strict parsers require them; loose ones tolerate). First delta of each
   tool call must carry `id` + `function.name`; never emit argument-only
   deltas before it. `role:"assistant"` on every chunk is harmless; other
   role values break zod enums.
5. Emit reasoning as `reasoning_content` (all opencode paths read it);
   `reasoning` additionally helps AI-SDK-compat and OpenRouter-style
   clients. Best coverage: both (Superagent Gateway dual-writes for this
   reason).
6. Whole-blob tool arguments in one delta are safe for all surveyed parsers.
7. Send `data: [DONE]` anyway — AI SDK ignores it, but official-openai-SDK
   clients (e.g. Cline's classic extension path) expect it.
8. Error bodies `{"error":{message, type?, param?, code?}}`; send
   `retry-after` on 429 — opencode honors it exactly; 5xx/429 are retried
   unbounded, 400 is not.
9. Require nothing beyond `Authorization: Bearer`; tolerate its absence.

Other clients:
- **Cline** (source-verified 2026-07-19 via gh api, repo cline/cline@main):
  the modern `llms` SDK path builds on `@ai-sdk/openai-compatible` with
  `includeUsage: true` — the same loose parser documented above — wrapped in
  a middleware that splits image parts OUT of `role:"tool"` messages into a
  synthetic user message, because the CC wire format cannot carry multimodal
  tool messages (`sdk/packages/llms/src/providers/vendors/openai-compatible.ts`).
  The classic extension path used the official openai SDK
  (`src/core/api/transform/openai-format.ts`); changelog confirms
  `reasoning_content` handling for OpenAI-compatible providers.
- aider (training knowledge, NOT source-verified): routes through LiteLLM —
  its drop rules apply. Codex CLI: partially verified via opencode's
  explicit "Codex parity" mirrors (strict:false + the schema-whitelist
  lowering).
