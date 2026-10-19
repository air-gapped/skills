---
name: messages-api
description: Reference for the Anthropic Messages API (/v1/messages) as a third-party compatibility protocol — the 7 inference servers that implement it natively (vLLM, SGLang, llama.cpp, Ollama, mistral.rs, Llama Stack/OGX, Lemonade), gateways that adapt it (LiteLLM, Bifrost, Superagent Gateway), client behavior (Claude Code, opencode anthropic provider), Messages ↔ Chat Completions translation, the thinking-signature seam, stop_reason divergences, and streaming quirks. NOT for official Anthropic API usage (models, pricing, SDK) — that is the claude-api skill.
when_to_use: Triggers on /v1/messages endpoint, count_tokens endpoint, Anthropic-compatible server or backend, serving the Messages API from vLLM/SGLang/llama.cpp/Ollama/mistral.rs, LiteLLM /v1/messages adapter or supported_endpoints passthrough, "point Claude Code at a local model", ANTHROPIC_BASE_URL redirection, opencode anthropic provider, Messages to Chat Completions translation, stop_reason mapping, content blocks, thinking blocks or signatures on third-party backends, anthropic-beta header handling, or Anthropic-protocol gateways (Bifrost, Superagent Gateway). NOT for official Anthropic API questions (pricing, model ids, SDK usage) — use claude-api.
argument-hint: "[topic: backends, gateways, translation, clients]"
---

# Messages API Compatibility Reference

Sibling protocols in the `inference-apis` plugin: **`chat-completions-api`** is
the baseline surface every server implements and the target this one is most
often translated to or from; **`responses-api`** is the third, with the
thinnest backend coverage of the three.

The Anthropic Messages API (`POST /v1/messages`) is now the second open
compatibility surface after Chat Completions: **every major local inference
server serves it natively** (vLLM, SGLang, llama.cpp, Ollama, mistral.rs,
Llama Stack/OGX, Lemonade), and
gateways (LiteLLM, Bifrost, Superagent Gateway) adapt it to everything else.
Claude Code is the driving client; Ollama, Lemonade, and Superagent all ship
Claude Code-specific affordances.

**Fleet property: stateless by protocol.** No `previous_response_id`
equivalent exists — full history is resent every turn, so load-balanced
same-model fleets cannot hit wrong-replica session errors (contrast the
Responses API's server-side state; see the responses-api skill).

## Critical Gotchas

- **The thinking-signature seam**: third-party backends fabricate or omit
  thinking-block signatures. Replaying such thinking to the REAL Anthropic
  API fails signature validation — keep conversations on one side of the
  boundary or strip thinking when crossing. Per-implementation signature
  table: `references/translation-mapping.md`.
- **Never rely on `stop_sequence`**: roughly half the implementations never
  emit it. end_turn/max_tokens/tool_use is the reliable subset;
  pause_turn and model_context_window_exceeded never come from third-party
  backends; refusal only from the LiteLLM bridge (upstream content_filter).
  Divergence table: `references/translation-mapping.md`.
- **`anthropic-beta` headers arrive whether supported or not** — opencode
  always sends interleaved-thinking (v1 adds fine-grained-tool-streaming);
  Claude Code adds beta tool-schema fields (`defer_loading`,
  `eager_input_streaming`). Servers must no-op unknown betas and fields, never
  400. A backend that rejects them (`Unexpected value(s)` on the header,
  `Extra inputs are not permitted`): set
  `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` on the Claude Code side.
- **`thinking` request param**: vLLM before v0.31.0 silently ignores it;
  v0.31.0+ maps `enabled`→thinking budget and `disabled`→reasoning off, but
  still ignores `adaptive` (what current clients send). SGLang accepts
  `budget_tokens` but does not enforce it.
- **`ping` events**: only mistral.rs and OGX's translation path emit them
  locally; Anthropic's real API does — clients must not require pings, proxies must not choke on them.
- **count_tokens is inconsistent**: real tokenization (vLLM) vs approximation
  (LiteLLM, Superagent chars/4) vs absent (Ollama, Lemonade). opencode never
  calls it; Claude Code uses it when present.
- **baseURL convention**: Anthropic SDKs append only `/messages` — configure
  `http://host/v1` (Bifrost is the exception: needs its `/anthropic` prefix).

## Quick Reference

When invoked with a topic argument (`backends`, `gateways`, `translation`,
`clients`), load that reference file first and answer from it. Without an
argument, pick by question shape: which-server-supports-what → backends;
routing/proxy behavior → gateways; wrong output/mapping bugs → translation;
client config → clients.

- **Backends**: `references/backend-implementations.md` — support matrix and
  per-server notes for the 7 native implementations
- **Gateways**: `references/gateways.md` — LiteLLM routing cascade, Bifrost,
  Superagent Gateway
- **Translation**: `references/translation-mapping.md` — field mapping,
  stop_reason divergence table, thinking-signature seam, streaming
  divergences, client-side requirements, Claude Code hacks
- **Clients**: `references/clients.md` — opencode deep-dive, Claude Code
  behaviors, ecosystem launchers
- **Sources**: `references/sources.md` — dated per-URL index with commits
  examined and the live-verification log

## Procedures

### Pointing an Anthropic-format client at a local backend
1. Confirm the backend serves `/v1/messages` (all 7 in the matrix do; check
   `references/backend-implementations.md` for its quirks first).
2. Set the base URL to `http://host:port/v1` (SDK appends `/messages`).
   Sanity-check: `curl -sS http://host:port/v1/messages -H "Content-Type:
   application/json" -H "x-api-key: x" -H "anthropic-version: 2023-06-01"
   -d '{"model":"<name>","max_tokens":32,"messages":[{"role":"user","content":"Say OK."}]}'`
   Expect 200 with `"type":"message"` and a `stop_reason`; 404 means the
   path prefix is wrong.
3. opencode: declare under `provider.anthropic.models` with explicit
   `npm: "@ai-sdk/anthropic"`. Claude Code: `ANTHROPIC_BASE_URL` (origin, no
   /v1 — the client appends it) + `ANTHROPIC_API_KEY`; isolate all state
   non-destructively with `CLAUDE_CONFIG_DIR=<scratch-dir>`; pin
   `ANTHROPIC_DEFAULT_HAIKU_MODEL` (background tasks) to the served model —
   `ANTHROPIC_SMALL_FAST_MODEL` is deprecated.
   **Context budget**: Claude Code's prompt is ~18k tokens (system + 17 tool
   schemas) and for a model id it cannot resolve (any local model name) it
   reserves 32000 output tokens — backends under
   ~52k `max_model_len` reject turn 1. Fix:
   `CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192`.
4. If reasoning models misbehave, check the backend's thinking handling in
   the matrix (param ignored? blocks dropped on input?).
5. Done when the client completes one tool round trip (`tool_use` →
   `tool_result` → `end_turn`) against the backend.

### Serving Messages through LiteLLM to a fleet
1. Add `model_info: {supported_endpoints: ["/v1/messages"]}` to every
   Messages-native deployment: LiteLLM then forwards the Anthropic body
   **untranslated** — full fidelity, no bridge.
2. Without it, `hosted_vllm/` etc. take the chat-completions bridge — expect
   unsigned thinking, no ping, tool-name truncation at 64 chars; see
   `references/gateways.md`.
3. Statelessness makes any replica valid — no affinity needed (unlike
   Responses `previous_response_id`; see responses-api skill).
4. Verify per deployment: the backend's access log shows `POST /v1/messages`
   (passthrough), not `POST /v1/chat/completions` (bridge). Done when every
   Messages-native deployment logs the former.

### Debugging a Messages streaming issue against a third-party backend
1. Capture raw SSE:
   ```bash
   curl -sN http://host:port/v1/messages -H "Content-Type: application/json" \
     -H "x-api-key: x" -H "anthropic-version: 2023-06-01" \
     -d '{"model":"<name>","max_tokens":64,"stream":true,"messages":[{"role":"user","content":"hi"}]}' | head -40
   ```
2. Expect `message_start → content_block_start → *_delta → content_block_stop
   → message_delta (stop_reason+usage) → message_stop`, each as
   `event: X\ndata: {json}`.
3. Check the streaming-divergences section in
   `references/translation-mapping.md` for the backend's known deviations
   (id formats, ping, tool_use triple vs incremental args). Done when every
   deviation in the capture is matched to a listed divergence or recorded as
   a new one with the backend version.
