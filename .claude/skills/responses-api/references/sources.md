# Sources — responses-api skill

Freshened: 2026-09-15 — every row probed.

**Three cited repositories were transferred or renamed** since the last pass. Every old URL still redirects, so none of them would ever have failed a liveness check.

**Three issues flipped open → closed, all `NOT_PLANNED`** — inactivity closures, not fixes. The rows say so explicitly, because a closed state here means the opposite of resolved.

The `Pinned` column records **what was examined, not what is latest**. Every actively developed engine below has released since; that is expected and is not drift.

Dated per-URL index of the external references this skill's claims rest on.
Freshen mode reads and stamps `Last verified:` / `Pinned:` here.

| Ref | URL | Last verified | Pinned |
|-----|-----|---------------|--------|
| OpenAI API changelog | https://developers.openai.com/api/docs/changelog | 2026-07-31 | — |
| OpenAI Responses API reference | https://developers.openai.com/api/reference/resources/responses | 2026-09-15 | path moved; old URL redirects |
| OpenAI ARC-AGI-3 publication (retained reasoning + compaction evidence; "legacy Chat Completions" wording) | https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/ | 2026-07-30 | published 2026-07-29 |
| openai-python SDK (ResponseUsage, ResponseStreamEvent) | https://github.com/openai/openai-python | 2026-07-19 | — |
| OpenResponses spec | https://www.openresponses.org/ | 2026-07-19 | release 2026-04-24 |
| OpenResponses changelog | https://www.openresponses.org/changelog | 2026-07-19 | — |
| vLLM | https://github.com/vllm-project/vllm | 2026-07-31 | v0.26.0 |
| llama.cpp | https://github.com/ggml-org/llama.cpp | 2026-07-31 | b10199 |
| mistral.rs | https://github.com/EricLBuehler/mistral.rs | 2026-07-31 | v0.9.0 |
| Ollama | https://github.com/ollama/ollama | 2026-07-31 | v0.32.5 |
| LiteLLM | https://github.com/BerriAI/litellm | 2026-07-31 | v1.94.0 |
| SGLang | https://github.com/sgl-project/sglang | 2026-07-31 | v0.5.16 |
| Llama Stack / OGX | https://github.com/ogx-ai/ogx | 2026-09-15 | v1.2.2 examined — **repo transferred and project renamed to OGX**; old URL redirects |
| Bifrost | https://github.com/maximhq/bifrost | 2026-07-31 | transports/v1.6.7 (HTTP line; ent-v2.0.0-pre* is the enterprise line) |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-07-31 | v11.5.1 |
| Codex CLI | https://github.com/openai/codex | 2026-07-31 | rust-v0.146.0 |
| TensorRT-LLM | https://github.com/NVIDIA/TensorRT-LLM | 2026-07-31 | v1.2.1 (stable; v1.3.0 in rc only) |
| opencode | https://github.com/anomalyco/opencode | 2026-09-15 | v1.18.10 examined — **repo transferred from `sst/`**; old URL redirects |
| Vercel AI SDK / @ai-sdk/open-responses | https://github.com/vercel/ai | 2026-07-19 | monorepo (per-package tags) |
| Pydantic AI | https://github.com/pydantic/pydantic-ai | 2026-07-31 | v2.21.0 |
| Amazon Strands SDK | https://github.com/strands-agents/harness-sdk | 2026-09-15 | **repo renamed from `sdk-python`**; tags are now plain semver, not per-package — re-check the monorepo assumption before relying on it |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | 2026-07-31 | python-1.12.1 |

Probe notes: `openai.com` blog URLs return 403 to non-browser fetchers
(curl/WebFetch) — re-verify via a real browser session.
`developers.openai.com` docs ARE WebFetch-reachable.

## Tracked issue/PR status (as of 2026-07-31)

| Item | Status |
|------|--------|
| vLLM #39584 (parallel tool-call crash) | closed 2026-06-19 (refactor PRs #46030/#47185); fix live-verified on v0.25.1, 2026-07-19 |
| vLLM #23218 (sequence_number -1) | fixed — live-verified proper numbering on v0.25.1, 2026-07-19 |
| vLLM #38132 (truncation auto 400) | **CLOSED `NOT_PLANNED` 2026-08-11** — an inactivity closure, not a fix; it already no longer reproduced on v0.25.1 (live test 2026-07-19) |
| vLLM #39624 (DELETE endpoint) | **CLOSED `NOT_PLANNED` 2026-08-14** — inactivity closure, so the endpoint is still absent; absence openapi-confirmed on v0.25.1 |
| vLLM #36435 (tool XML leakage) | OPEN (state: reopened; re-probed 2026-09-15). **The upstream repro uses a stock parser** (`--tool-call-parser qwen3_coder`), and the maintainers attribute it to a parser-agnostic `if reasoning_parser: ... elif tool_parser:` branch in `_process_simple_streaming_events` — so it is not custom-parser-specific. Filed against 0.17.0rc1.dev; no comment confirms or denies it on v0.25+. Local run 2026-07-19 did not reproduce it, but used a custom Rust parser. Stale-bot notice 2026-08-05; last human comment 2026-05-04 |
| vLLM store gating | `VLLM_ENABLE_RESPONSES_API_STORE=1` env var, default off, silent ignore — read from `responses/serving.py` @ v0.25.1; env var code-confirmed still present at v0.26.0 (2026-07-31) |
| LiteLLM `/v1/responses/compact` | pure passthrough route since PR #18697 (merged 2026-01-06) — no server-side compaction of its own; code-verified at v1.94.0. (PR #28868's `compact_20260112` polyfill is `context_management`-side; relation to this route unverified) |
| Ollama PR #15404 (previous_response_id) | open (re-probed 2026-07-31) |
| LiteLLM #20975 (Azure passthrough strips setup events) | **CLOSED `NOT_PLANNED` 2026-08-13** by the stale bot — treat as unfixed, not resolved |
| LiteLLM #22102 (codex skips output_item.added) | stale-closed 2026-06-27, unverified |
| SGLang custom tools on `/v1/responses` | **Settled by [#38690](https://github.com/sgl-project/sglang/pull/38690), merged 2026-09-12** (commit `925e684a`). It adds custom-tool support and states the prior behaviour: `_response_tools_to_chat_tools` skipped every non-`function` tool, so a `custom` tool produced no call and `tool_choice="required"` returned HTTP 400. **Main only — no tag contains it; latest release v0.5.19 (2026-09-05).** Earlier attempts #16806 and #20771 were abandoned 2026-06-12 in favour of #25881, which fixed request handling but not this. |
| mistral.rs #1944 | closed 2026-07-07 (~v0.9.0) |
| mistral.rs #1945, #1946 | open (re-probed 2026-07-31) |
| llama.cpp #19173 (stream cancel) | open (re-probed 2026-07-31) |
| vLLM PR #48098 (`parallel_tool_calls=null` crash in Responses `from_request()`) | merged 2026-07-15 (`c0302d94`); **first shipped in v0.26.0** (2026-07-27) — merge commit is not an ancestor of v0.25.1 and is an ancestor of v0.26.0, with no tag between (2026-09-15) |
