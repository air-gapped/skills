# Sources — responses-api skill

Dated per-URL index of the external references this skill's claims rest on.
Freshen mode reads and stamps `Last verified:` / `Pinned:` here.

| Ref | URL | Last verified | Pinned |
|-----|-----|---------------|--------|
| OpenAI API changelog | https://developers.openai.com/api/docs/changelog | 2026-07-19 | — |
| OpenAI Responses API reference | https://developers.openai.com/api/docs/api-reference/responses | 2026-07-19 | — |
| openai-python SDK (ResponseUsage, ResponseStreamEvent) | https://github.com/openai/openai-python | 2026-07-19 | — |
| OpenResponses spec | https://www.openresponses.org/ | 2026-07-19 | release 2026-04-24 |
| OpenResponses changelog | https://www.openresponses.org/changelog | 2026-07-19 | — |
| vLLM | https://github.com/vllm-project/vllm | 2026-07-19 | v0.25.1 |
| llama.cpp | https://github.com/ggml-org/llama.cpp | 2026-07-19 | b10068 |
| mistral.rs | https://github.com/EricLBuehler/mistral.rs | 2026-07-19 | v0.9.0 |
| Ollama | https://github.com/ollama/ollama | 2026-07-19 | v0.32.1 |
| LiteLLM | https://github.com/BerriAI/litellm | 2026-07-19 | v1.92.0 |
| SGLang | https://github.com/sgl-project/sglang | 2026-07-19 | v0.5.15.post1 |
| Llama Stack | https://github.com/llamastack/llama-stack | 2026-07-19 | v1.2.1 |
| Bifrost | https://github.com/maximhq/bifrost | 2026-07-19 | ent-v2.0.0-prerelease2-base |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-07-19 | v11.0.0 |
| Codex CLI | https://github.com/openai/codex | 2026-07-19 | rust-v0.144.6 |
| TensorRT-LLM | https://github.com/NVIDIA/TensorRT-LLM | 2026-07-19 | v1.2.1 |
| opencode | https://github.com/sst/opencode | 2026-07-19 | v1.18.3 |
| Vercel AI SDK / @ai-sdk/open-responses | https://github.com/vercel/ai | 2026-07-19 | monorepo (per-package tags) |
| Pydantic AI | https://github.com/pydantic/pydantic-ai | 2026-07-19 | v2.13.0 |
| Amazon Strands SDK | https://github.com/strands-agents/sdk-python | 2026-07-19 | monorepo (per-package tags) |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | 2026-07-19 | python-1.11.0 |

## Tracked issue/PR status (as of 2026-07-19)

| Item | Status |
|------|--------|
| vLLM #39584 (parallel tool-call crash) | closed 2026-06-19 (refactor PRs #46030/#47185); fix live-verified on v0.25.1, 2026-07-19 |
| vLLM #23218 (sequence_number -1) | fixed — live-verified proper numbering on v0.25.1, 2026-07-19 |
| vLLM #38132 (truncation auto 400) | open, but no longer reproduces on v0.25.1 (live test 2026-07-19) |
| vLLM #39624 (DELETE endpoint) | open; absence openapi-confirmed on v0.25.1 |
| vLLM #36435 (tool XML leakage) | open; not reproduced 2026-07-19 but only tested with a custom rust tool parser, not stock |
| vLLM store gating | `VLLM_ENABLE_RESPONSES_API_STORE=1` env var, default off, silent ignore — read from `responses/serving.py` @ v0.25.1 |
| Ollama PR #15404 (previous_response_id) | open |
| LiteLLM #20975 (Azure passthrough strips setup events) | open |
| LiteLLM #22102 (codex skips output_item.added) | stale-closed 2026-06-27, unverified |
| SGLang #16806 / #20771 | closed unmerged 2026-06-12; superseded by #25881 (merged 2026-06-12) |
| mistral.rs #1944 | closed 2026-07-07 (~v0.9.0) |
| mistral.rs #1945, #1946 | open |
| llama.cpp #19173 (stream cancel) | open |
