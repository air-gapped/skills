---
name: chat-completions-api
description: Reference for the OpenAI Chat Completions API (/v1/chat/completions) and legacy /v1/completions as the lingua-franca compatibility protocol — the official spec incl. deprecation timeline and Responses-only feature delta, how 7 local servers (vLLM, SGLang, llama.cpp, Ollama, mistral.rs, Llama Stack/OGX, Lemonade) actually implement it, gateways (LiteLLM, Bifrost), 10 cloud providers' CC-compat endpoints (Anthropic, Gemini, DeepSeek, xAI, Groq, OpenRouter, Azure...), the reasoning_content/reasoning field schism, finish_reason divergences, and client wire behavior (opencode, Vercel AI SDK). NOT for the Responses API (responses-api skill) or Anthropic Messages protocol (messages-api skill).
when_to_use: Triggers on /v1/chat/completions or /v1/completions endpoint questions, OpenAI-compatible server or client, chat completions params (tool_choice, response_format, logit_bias, seed, stream_options, reasoning_effort, max_completion_tokens vs max_tokens), reasoning_content vs reasoning fields, finish_reason mapping, SSE chunk / delta assembly / tool-call streaming, structured outputs or json_schema on local servers, legacy completions or FIM/suffix, OpenAI deprecations or model shutdowns, pointing an OpenAI-SDK client at vLLM/SGLang/llama.cpp/Ollama, LiteLLM drop_params, or cloud OpenAI-compat layers (api.deepseek.com, Groq, Gemini openai/, Anthropic OpenAI SDK compat, OpenRouter, Azure v1).
argument-hint: "[topic: spec, backends, gateways, cloud, clients]"
---

# Chat Completions Compatibility Reference

Chat Completions is the lingua franca of LLM serving — and because everyone
has implemented and extended it longest, it carries the MOST undocumented
divergence of the three open protocols. OpenAI keeps it fully supported but
second-choice ("we recommend trying Responses"); xAI, Groq, and Azure
likewise declare it legacy. Legacy `/v1/completions` loses its last
first-party OpenAI models 2026-09-28 and survives as a local/third-party
surface.

**Fleet property: stateless.** Full history resent every turn, like
Messages; no server-side session state to break load-balanced fleets
(contrast responses-api's `previous_response_id`).

**Last refreshed**: 2026-07-19 (source-examined at commits of 2026-07-16..18;
provenance in `references/sources.md`).

## Critical Gotchas

- **The reasoning-field schism**: `reasoning_content` (SGLang, llama.cpp,
  mistral.rs, DeepSeek, xAI) vs `reasoning` (vLLM, Ollama, Together, Groq,
  OpenRouter) vs inline `<think>` — and vLLM silently RENAMES incoming
  `reasoning_content`→`reasoning`. Servers should emit both; clients should
  read both. Full table: `references/backend-implementations.md`.
- **Reasoning must be passed BACK in tool loops** on DeepSeek v4 (with tool
  calls) and OpenRouter (exact block sequence) — clients that strip
  reasoning break agentic loops. `references/cloud-compat.md`.
- **Silent-drop vs hard-400 split**: Ollama silently drops `tool_choice`
  (forced tool calls no-op!) and `max_completion_tokens` (unbounded
  generation); Groq and xAI-reasoning hard-400 on specific params; LiteLLM
  raises UnsupportedParamsError as HTTP **500**. Identify the target's
  failure mode before debugging.
- **finish_reason is not a closed enum**: `abort` (vLLM, SGLang),
  `repetition`, `canceled`/`generated_image` (mistral.rs); llama.cpp
  DEFAULTS to `length`; named tool_choice returns `stop` on vLLM/OpenAI but
  `tool_calls` on SGLang/mistral.rs. Parse tolerantly, key loops on
  `tool_calls`.
- **`seed` is a lottery**: honored (vLLM, llama.cpp), silent no-op unless
  server flag (SGLang `--enable-deterministic-inference`), ignored
  (mistral.rs) — and OpenAI has formally deprecated `seed` AND
  `system_fingerprint`.
- **`json_object` ≠ json mode everywhere**: SGLang and mistral.rs implement
  it as schema `{"type":"object"}` — top-level arrays forbidden.
  `json_schema.strict` is ignored by ALL local servers (always fully
  enforced anyway).
- **Tool-call streaming split**: whole-blob single delta (Ollama,
  mistral.rs) vs incremental argument diffs (vLLM, SGLang, llama.cpp).
  First delta must carry `id`+`function.name` or AI-SDK clients kill the
  stream; loose parsers finalize args the moment they parse as JSON.
- **Cached-token reporting is flag-gated**: vLLM
  `--enable-prompt-tokens-details`, SGLang `--enable-cache-report`;
  llama.cpp reports always; Ollama never. OpenAI CC now has explicit
  caching (`prompt_cache_options` + per-block breakpoints,
  `cache_write_tokens` billed 1.25×): `references/spec.md`.
- **`data: [DONE]` is not universal** — Llama Stack/OGX never sends it; AI
  SDK clients ignore it, official-SDK clients expect it. Send it; don't
  require it.

## Quick Reference

When invoked with a topic argument (`spec`, `backends`, `gateways`, `cloud`,
`clients`), load that reference file first and answer from it. Without an
argument, pick by question shape: official params/deprecations/what-CC-gets
→ spec; which-local-server-does-what → backends; proxy/routing behavior →
gateways; hosted-provider compat → cloud; what-clients-send / parser
tolerance → clients.

- **Spec**: `references/spec.md` — full request/response/chunk schema
  highlights, explicit prompt caching, stored completions, legacy
  /v1/completions + shutdown timeline, deprecation archaeology,
  Responses-only feature delta
- **Backends**: `references/backend-implementations.md` — divergence matrix
  + per-server sections for the 7 local servers
- **Gateways**: `references/gateways.md` — LiteLLM param cascade and prefix
  routing, Bifrost, Superagent (CC outbound only), gateway-tax table
- **Cloud**: `references/cloud-compat.md` — 10 providers' CC-compat
  endpoints and the cross-provider gotcha matrix
- **Clients**: `references/clients.md` — opencode's three CC paths, AI SDK
  parser tolerance, server tolerance checklist
- **Sources**: `references/sources.md` — dated per-URL index with commits
  examined and the live-verification log

Translation between protocols is homed elsewhere: CC↔Messages mapping in
the messages-api skill, CC↔Responses mapping in the responses-api skill.

## Procedures

### Pointing an OpenAI-SDK client at a local backend
1. Base URL `http://host:port/v1` (SDKs append `/chat/completions`); auth
   `Bearer` anything unless the server enforces keys.
2. Check the backend's row in the divergence matrix FIRST — especially
   Ollama (`tool_choice` and `max_completion_tokens` silently dropped) and
   reasoning field naming.
3. For agent clients (opencode etc.): use the openai-COMPATIBLE provider
   path, not the openai provider — the openai path model-id-sniffs
   ("o3-…" gets temperature stripped), drops reasoning fields, and its
   factory default is the Responses API (`references/clients.md`).
4. Reasoning models: confirm how thinking is toggled (`reasoning_effort`
   mapping vs `chat_template_kwargs.enable_thinking` vs vendor `thinking`
   fields) and which field the CoT comes back in.
5. Sanity curl:
   ```bash
   curl -sS http://host:port/v1/chat/completions -H "Content-Type: application/json" \
     -d '{"model":"<name>","max_tokens":32,"messages":[{"role":"user","content":"Say OK."}]}'
   ```
   Expect `object:"chat.completion"`, non-null `choices[0].message.content`,
   `finish_reason` of `stop` OR `length` (llama.cpp defaults to `length`).
   An error body here → check the server's error-envelope row in the matrix
   before parsing (mistral.rs sends `{"message"}`, not `{"error":{...}}`).

### Serving CC through LiteLLM to a fleet
1. Prefix decides fidelity: `openai/<model>` = full surface passthrough;
   `hosted_vllm/<model>` = tool schemas silently edited (strict +
   additionalProperties stripped). Pick deliberately.
2. Set `drop_params: true` (or per-model `additional_drop_params`) —
   otherwise unsupported params surface as HTTP 500 UnsupportedParamsError.
3. Statelessness makes any replica valid — no affinity needed.

### Debugging a CC streaming issue
1. Capture raw SSE:
   ```bash
   curl -sN http://host:port/v1/chat/completions -H "Content-Type: application/json" \
     -d '{"model":"<name>","max_tokens":64,"stream":true,"stream_options":{"include_usage":true},"messages":[{"role":"user","content":"hi"}]}' | head -40
   ```
2. Expect data-only SSE: first chunk `delta.role`, content/tool deltas keyed
   by `index`, finish chunk, optional `choices:[]` usage chunk, `[DONE]`.
3. Check the backend's streaming row in the matrix for known deviations
   (always-present null keys on SGLang, vendor `timings` on llama.cpp,
   role-on-every-chunk + whole-blob tools on Ollama, raw non-JSON error
   lines on mistral.rs, missing [DONE] on OGX).
4. If tool calls vanish client-side: check whether the first delta carried
   `id`+`function.name`, and whether the client requires
   `tool_calls[].index` (`references/clients.md`).
