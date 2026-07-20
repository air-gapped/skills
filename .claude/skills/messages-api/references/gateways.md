# Messages API Gateways & Adapters

Gateways that accept Anthropic-format clients and route to arbitrary
backends. Source-examined 2026-07-19 (commits in `sources.md`).

## Contents
- [LiteLLM](#litellm) — 4-step routing cascade, bridge fidelity, thinking seam
- [Bifrost](#bifrost) — prefixed inbound, Responses-schema pivot, Claude passthrough
- [Superagent Gateway](#superagent-gateway) — Messages-pivot translator for Claude Code + Codex

## LiteLLM

Proxy route `POST /v1/messages` (also `/v1/messages/count_tokens`).
Examined at upstream main b83c60b (2026-07-18, newer than v1.92.0 stable);
`/v1/messages` adapter → vLLM live-verified 2026-07-19 on proxy v1.92.0.

**Routing cascade** (`llms/anthropic/experimental_pass_through/messages/handler.py:488-535`):
1. **Native passthrough** — providers with `AnthropicMessagesConfig`:
   anthropic, bedrock (Claude), vertex_ai (Claude), azure_ai, minimax,
   deepseek, tencent, github_copilot.
2. **Per-deployment opt-in passthrough** for OpenAI-compat backends:
   `model_info.supported_endpoints: ["/v1/messages"]` in config.yaml forwards
   the Anthropic body **untranslated** to the backend. Since vLLM/SGLang/
   llama.cpp/Ollama now serve `/v1/messages` natively, this is the
   full-fidelity fleet configuration — no bridge, no thinking-signature loss.
3. **Responses-API bridge** for `custom_llm_provider=="openai"` (opt-out via
   `litellm.use_chat_completions_url_for_anthropic_messages=True`).
4. **Chat-completions bridge** for everything else (`hosted_vllm/` etc.) —
   the default path live-verified against vLLM.

**Bridge fidelity**: tool names truncated to OpenAI's 64-char limit with a
restore mapping; thinking history → `thinking_blocks`; output
reasoning_content → thinking block with **signature: None** — **replaying
synthesized thinking to a real Anthropic backend fails signature validation**.
stop_reason never `stop_sequence`/`refusal`. Streaming synthesizes proper
`event:`+`data:` frames; **never emits `ping`**; single-chunk fake streams
split by `_CombinedChunkSplitter`.

**count_tokens**: provider counting API when available (Anthropic/Google),
else local tokenizer approximation; returns only `{"input_tokens": N}`.

**Quirks**: non-Anthropic `usage.total_tokens` included non-stream (strip via
`litellm.strip_anthropic_total_tokens=True`); `output_config` dropped on the
bridge (avoids 400); `metadata` restricted to `user_id` (use
`litellm_metadata` for LiteLLM's own); tool_use ids sanitized.

## Bifrost

First-class bidirectional Anthropic support (commit 7a1543e85).

- **Inbound**: `POST {prefix}/v1/messages` under `/anthropic` (+ aliases
  `/cursor`, `/litellm`, `/langchain`, `/pydanticai`) — **no bare
  /v1/messages**; Claude Code connects via
  `ANTHROPIC_BASE_URL=http://host:port/anthropic`. Also /v1/complete,
  count_tokens, batches, files.
- Inbound Messages map to Bifrost's internal **Responses schema** (not chat),
  then to any backend; replies converted back with full Anthropic SSE
  synthesis (message_start with `content: []`, thinking_delta,
  input_json_delta, deduped message_delta).
- **Claude-model passthrough fast path**: raw upstream bytes forwarded
  verbatim (renumbering only where strict clients need it) — preserves wire
  fidelity including real thinking signatures.
- stop_reason table: end_turn↔stop, max_tokens↔length, stop_sequence→stop,
  tool_use↔tool_calls, compaction↔compaction; unknown pass through.
- Thinking: enabled|adaptive ↔ Reasoning{Effort,MaxTokens} with
  budget_tokens→effort heuristic; signatures preserved on the Anthropic path.
- Quirks: reasoning-misread heuristics on chat path with thinking enabled;
  unsupported tool calls degrade to text; per-provider capability stripping
  (Bedrock/Vertex/Azure variants).

## Superagent Gateway

superagent-ai/gateway (Rust, single binary, commit d182a5b). Purpose-built
for Claude Code + Codex on any model. **Anthropic Messages is the internal
pivot format** — all 4 translators (anthropic↔chat, responses↔anthropic)
compose the client×provider combos; Responses→OpenAI pivots through Messages.

- Endpoints: `/{anthropic/}v1/messages` (+count_tokens),
  `/{openai/}v1/responses`, `/v1/models` (hybrid objects). No chat serving.
- 14 provider presets + custom `base_url` (`type: anthropic` for
  Anthropic-wire); traffic roles main/subagent/background per client;
  `claude-opus-*`→subagent, `claude-haiku-*`→background glob routing; hidden
  `claude-<name>` "discovery twins" so Claude Code's /model picker lists
  custom models.
- **Tool-loop-safe failover**: retry/fallback only before a 2xx begins;
  mid-stream failure emits SSE `error` (`gateway_upstream_error`), never
  swaps models mid-answer. Non-retryable upstream errors forwarded
  byte-for-byte because Claude Code keys retries off error wording.
- Messages depth: Anthropic upstream = passthrough; OpenAI upstream = full
  SSE synthesis with thinking blocks from `reasoning_content`/`reasoning`,
  closed with **empty signature_delta**; tool ids fabricated `toolu_<uuid>`.
  stop_reason: length→max_tokens, tool_calls→tool_use, else end_turn.
- **Reasoning replay dual-write**: thinking blocks replayed as BOTH
  `reasoning_content` AND `reasoning` on assistant messages — Kimi K2.7
  errors in tool loops if stripped.
- count_tokens: native on Anthropic routes; **chars/4 estimate** on OpenAI
  routes. `previous_response_id` explicitly rejected; no `phase` field on the
  Responses side; reasoning not surfaced to Codex (MVP).
- Ops notes: binds `[::1]` alongside 127.0.0.1 (Node clients); refuses
  non-localhost bind without auth tokens; `.env.local` auto-load.
