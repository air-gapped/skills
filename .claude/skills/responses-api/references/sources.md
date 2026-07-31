# Sources — responses-api skill

Dated per-URL index of the external references this skill's claims rest on.
Freshen mode reads and stamps `Last verified:` / `Pinned:` here.

| Ref | URL | Last verified | Pinned |
|-----|-----|---------------|--------|
| OpenAI API changelog | https://developers.openai.com/api/docs/changelog | 2026-07-31 | — |
| OpenAI Responses API reference | https://developers.openai.com/api/docs/api-reference/responses | 2026-07-31 | — |
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
| Llama Stack | https://github.com/llamastack/llama-stack | 2026-07-31 | v1.2.2 |
| Bifrost | https://github.com/maximhq/bifrost | 2026-07-31 | transports/v1.6.7 (HTTP line; ent-v2.0.0-pre* is the enterprise line) |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-07-31 | v11.5.1 |
| Codex CLI | https://github.com/openai/codex | 2026-07-31 | rust-v0.146.0 |
| TensorRT-LLM | https://github.com/NVIDIA/TensorRT-LLM | 2026-07-31 | v1.2.1 (stable; v1.3.0 in rc only) |
| opencode | https://github.com/sst/opencode | 2026-07-31 | v1.18.10 |
| Vercel AI SDK / @ai-sdk/open-responses | https://github.com/vercel/ai | 2026-07-19 | monorepo (per-package tags) |
| Pydantic AI | https://github.com/pydantic/pydantic-ai | 2026-07-31 | v2.21.0 |
| Amazon Strands SDK | https://github.com/strands-agents/sdk-python | 2026-07-19 | monorepo (per-package tags) |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | 2026-07-31 | python-1.12.1 |

Probe notes: `openai.com` blog URLs return 403 to non-browser fetchers
(curl/WebFetch) — re-verify via a real browser session.
`developers.openai.com` docs ARE WebFetch-reachable.

## Tracked issue/PR status (as of 2026-07-31)

| Item | Status |
|------|--------|
| vLLM #39584 (parallel tool-call crash) | closed 2026-06-19 (refactor PRs #46030/#47185); fix live-verified on v0.25.1, 2026-07-19 |
| vLLM #23218 (sequence_number -1) | fixed — live-verified proper numbering on v0.25.1, 2026-07-19 |
| vLLM #38132 (truncation auto 400) | open, but no longer reproduces on v0.25.1 (live test 2026-07-19) |
| vLLM #39624 (DELETE endpoint) | open; absence openapi-confirmed on v0.25.1 |
| vLLM #36435 (tool XML leakage) | OPEN (state: reopened, re-probed 2026-07-31); not reproduced 2026-07-19 but only tested with a custom rust tool parser, not stock |
| vLLM store gating | `VLLM_ENABLE_RESPONSES_API_STORE=1` env var, default off, silent ignore — read from `responses/serving.py` @ v0.25.1; env var code-confirmed still present at v0.26.0 (2026-07-31) |
| LiteLLM `/v1/responses/compact` | pure passthrough route since PR #18697 (merged 2026-01-06) — no server-side compaction of its own; code-verified at v1.94.0. (PR #28868's `compact_20260112` polyfill is `context_management`-side; relation to this route unverified) |
| Ollama PR #15404 (previous_response_id) | open (re-probed 2026-07-31) |
| LiteLLM #20975 (Azure passthrough strips setup events) | open (re-probed 2026-07-31) |
| LiteLLM #22102 (codex skips output_item.added) | stale-closed 2026-06-27, unverified |
| SGLang #16806 / #20771 | closed unmerged 2026-06-12; superseded by #25881 (merged 2026-06-12); custom function tools still unverified at v0.5.16 |
| mistral.rs #1944 | closed 2026-07-07 (~v0.9.0) |
| mistral.rs #1945, #1946 | open (re-probed 2026-07-31) |
| llama.cpp #19173 (stream cancel) | open (re-probed 2026-07-31) |
| vLLM PR #48098 (`parallel_tool_calls=null` crash in Responses `from_request()`) | merged ~2026-07 (post-v0.25.1 refactor tail); release inclusion unverified |
