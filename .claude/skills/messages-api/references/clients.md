# Messages API Clients (against third-party backends)

## Contents
- [opencode (anthropic provider)](#opencode-anthropic-provider)
- [Claude Code](#claude-code)
- [Ecosystem integrations](#ecosystem-integrations)

## opencode (anthropic provider)

Examined at v1.18.3-era source (2026-07-18).
Live-verified 2026-07-19: full multi-step tool loops against vLLM
`/v1/messages` direct AND via LiteLLM.

- SDK: `@ai-sdk/anthropic` (3.0.82); optional native runtime
  (`@opencode-ai/llm`, `protocols/anthropic-messages.ts`) behind
  `experimentalNativeLlm` flag.
- **Loader is fully static — fails fast, never hangs**: model resolution is
  an in-memory lookup; unknown IDs → `ModelNotFoundError` with fuzzy
  suggestions. (Contrast: the openai provider loader routes through
  `sdk.responses()` discovery and hangs at init on non-catalog model IDs —
  the bug class documented in the responses-api skill.)
- Custom backends: declare under `provider.anthropic.models` with
  `options.baseURL: "http://host/v1"` (SDK appends `/messages`). Caveat: if
  the models.dev catalog is unavailable, the npm fallback flips to
  `@ai-sdk/openai-compatible` — set `npm: "@ai-sdk/anthropic"` explicitly.
- Sends: `anthropic-version: 2023-06-01`, `x-api-key`, always-on
  `anthropic-beta` (interleaved-thinking + fine-grained-tool-streaming),
  `cache_control` ephemeral blocks, `thinking` param (adaptive for
  opus-4.7+/sonnet-5+/fable-5; enabled+budgetTokens for older Claude), always
  `stream: true`.
- Tolerates: absent thinking signatures, missing cache-usage fields, proxies
  dropping optional event fields. Maps pause_turn/refusal (refusal → session
  error). Never calls count_tokens.
- Retries: session-level 429+5xx with retry-after, 2s→30s backoff.

## Claude Code

Uses the Messages API natively (its home protocol). Behaviors third-party
servers/gateways specifically accommodate (from their source):

- Injects an `x-anthropic-billing-header` system prefix — vLLM and llama.cpp
  strip/normalize it to preserve prefix caching.
- Keys retry behavior off error message wording — Superagent Gateway
  forwards upstream errors byte-for-byte for this reason.
- /model picker lists models via `/v1/models` — Superagent fabricates
  `claude-<name>` discovery twins for custom models.
- Uses count_tokens when available; sends `anthropic-beta` headers;
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
