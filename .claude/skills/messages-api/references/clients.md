# Messages API Clients (against third-party backends)

## Contents
- [opencode (anthropic provider)](#opencode-anthropic-provider)
- [Claude Code](#claude-code)
- [Ecosystem integrations](#ecosystem-integrations)

## opencode (anthropic provider)

- SDK (v1 line): `@ai-sdk/anthropic`; optional native runtime
  (`packages/llm/src/protocols/anthropic-messages.ts`) behind
  `OPENCODE_EXPERIMENTAL_NATIVE_LLM` (or `OPENCODE_EXPERIMENTAL=true`).
  v2 line (`@opencode/cli`): `@ai-sdk/anthropic` is aliased to its own
  `@opencode/ai` Messages client.
- **Loader is fully static — fails fast, never hangs**: model resolution is
  an in-memory lookup; unknown IDs → `ModelNotFoundError` with fuzzy
  suggestions. (Contrast: the openai provider loader routes through
  `sdk.responses()` discovery and hangs at init on non-catalog model IDs —
  the bug class documented in the responses-api skill.)
- Custom backends: declare under `provider.anthropic.models` with
  `options.baseURL: "http://host/v1"` (SDK appends `/messages`). Always set
  `npm: "@ai-sdk/anthropic"` explicitly: a config-defined model with no `npm`
  and no models.dev entry defaults to `@ai-sdk/openai-compatible`.
- Sends: `anthropic-version: 2023-06-01`, `x-api-key`, always-on
  `anthropic-beta` — v1: interleaved-thinking + fine-grained-tool-streaming;
  v2: interleaved-thinking plus conditional betas (`compact-2026-01-12`,
  `mid-conversation-output-config-2026-07-01`, thinking-binding),
  `cache_control` ephemeral blocks, `thinking` param chosen by a version
  regex on the `claude-*` id: ≥4.7 (and any unparseable `claude-*` id) →
  `adaptive` + `display:"summarized"` + effort; 4.6 → `adaptive` without
  display; older → `enabled` + `budgetTokens`. Always `stream: true`.
- Tolerates: absent thinking signatures, missing cache-usage fields, proxies
  dropping optional event fields. Maps pause_turn/refusal (refusal → session
  error). Never calls count_tokens.
- Retries: session level, **max 5**; 5xx by status, 429 via the retryable
  flag/message match; honors `retry-after-ms` / `retry-after`; otherwise
  2s × 2ⁿ + ≤25% jitter, capped at 30s only when the response had no headers.

## Claude Code

Uses the Messages API natively (its home protocol). Behaviors third-party
servers/gateways specifically accommodate (from their source):

- Injects an `x-anthropic-billing-header` system prefix — vLLM and llama.cpp
  strip/normalize it to preserve prefix caching.
- Keys retry behavior off error message wording — Superagent Gateway
  forwards upstream errors byte-for-byte for this reason.
- /model picker lists models via `/v1/models` — Superagent fabricates
  `claude-<name>` discovery twins for custom models.
- **Gateway contract** (Claude Code's published requirements): serve
  `/v1/messages` (count_tokens optional); forward `anthropic-version` and
  `anthropic-beta` verbatim — never allowlist beta values; do not buffer SSE
  and pass every event incl. `ping`; optional `GET /v1/models?limit=1000`
  feeds the /model picker (3s timeout, no redirects).
- Uses count_tokens when available, else a character-based estimate;
  `ANTHROPIC_BASE_URL` env is the standard redirect knob (origin or /v1
  conventions vary by tool — Lemonade sets origin-only; Bifrost requires the
  `/anthropic` prefix path).

## Ecosystem integrations

- **Ollama**: `ollama launch claude` (cmd/launch/claude.go) configures Claude
  Code against local Ollama; `relax_thinking` set for Claude Code
  compatibility; docs page `anthropic-compatibility.mdx`.
- **Lemonade**: `agent_launcher.cpp` launches Claude Code with
  `ANTHROPIC_BASE_URL` pointed at itself.
- **OGX (Llama Stack)**: integration tests drive the real Claude Code CLI and
  Claude Agent SDK against its `/v1/messages`
  (tests/integration/messages/test_claude_code_cli.py); conformance script
  diffs its OpenAPI against Anthropic's Stainless spec.
- **Superagent Gateway**: purpose-built Claude Code + Codex compatibility
  layer (see `gateways.md`).
