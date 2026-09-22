# Sources — chat-completions-api skill

Freshened: 2026-09-22 — every row probed; all 38 URLs live. The `seed` and `system_fingerprint` deprecations and the named model retirement dates all reproduce verbatim on the live API reference.

**Five vendor doc URLs were renamed and every one still returns 200 through a redirect** — a liveness sweep can never catch this class, only a check of the final URL can. The rows below are the post-redirect locations.

The repo rows pin commits that were examined, **not latest versions**. Every upstream here has released since and that is not drift; all eleven pinned tags and commits were re-confirmed to still resolve.

Dated per-URL index. Freshen mode reads and stamps `Last verified:` here.
All repo rows examined by source (local clones of the upstream repos) at
the listed commit on 2026-07-19.

| Ref | URL | Last verified | Pinned | Commit examined |
|-----|-----|---------------|--------|-----------------|
| OpenAI ARC-AGI-3 publication ("legacy Chat Completions" wording) | https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/ | 2026-07-30 | published 2026-07-29 | — (openai.com 403s non-browser fetchers; use a real browser) |
| CC create (request/response) | https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create | 2026-09-15 | — | — |
| CC streaming events (full chunk schema; .md twin) | https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events | 2026-09-15 | — | — |
| Stored completions (list/retrieve/update/delete/messages) | https://developers.openai.com/api/reference/chat-completions/overview | 2026-09-15 | — | — |
| Legacy completions create | https://developers.openai.com/api/reference/resources/completions/methods/create | 2026-09-15 | — | — |
| Deprecations (.md twin works) | https://developers.openai.com/api/docs/deprecations | 2026-09-15 | — | — |
| Changelog | https://developers.openai.com/api/docs/changelog | 2026-09-15 | — | — |
| Reasoning guide (effort values) | https://developers.openai.com/api/docs/guides/reasoning | 2026-09-15 | — | — |
| Prompt caching guide (breakpoints, cache_write_tokens) | https://developers.openai.com/api/docs/guides/prompt-caching | 2026-09-15 | — | — |
| vLLM | https://github.com/vllm-project/vllm | 2026-09-15 | v0.25.1 (live-tested) / main | 9243e0124e |
| SGLang | https://github.com/sgl-project/sglang | 2026-09-15 | v0.5.15.post1 | 99f5a6f46b |
| llama.cpp | https://github.com/ggml-org/llama.cpp | 2026-09-15 | b10068 | 571d0d5 |
| Ollama | https://github.com/ollama/ollama | 2026-09-15 | v0.32.1 | 573386c |
| mistral.rs | https://github.com/EricLBuehler/mistral.rs | 2026-09-15 | v0.9.0 | 0ae0476 |
| Llama Stack / OGX | https://github.com/llamastack/llama-stack | 2026-09-15 | v1.2.1 | f05b98f |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-09-15 | v11.0.0 | b09a0e9 |
| LiteLLM | https://github.com/BerriAI/litellm | 2026-09-15 | v1.92.0 (live) / main | b83c60b |
| Bifrost | https://github.com/maximhq/bifrost | 2026-09-15 | — | 7a1543e85 |
| Superagent Gateway | https://github.com/superagent-ai/gateway | 2026-09-15 | — | d182a5b |
| opencode + pinned AI SDK tarballs | https://github.com/sst/opencode | 2026-09-15 | v1.18.3; @ai-sdk/openai@3.0.84, openai-compatible@2.0.41 | 127bdb307 (v1.18.3 tag) |
| Cline (llms SDK provider) | https://github.com/cline/cline | 2026-09-15 | main (gh api) | — |
| Anthropic OpenAI-compat layer | https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk | 2026-09-15 | — | — |
| Gemini OpenAI-compat | https://ai.google.dev/gemini-api/docs/openai | 2026-09-15 | — | — |
| DeepSeek API docs (+thinking/prefix/FIM guides) | https://api-docs.deepseek.com/ | 2026-09-15 | — | — |
| xAI CC (legacy) + deferred completions | https://docs.x.ai/developers/model-capabilities/legacy/chat-completions | 2026-09-15 | — | — |
| Groq OpenAI-compat + reasoning | https://console.groq.com/docs/openai | 2026-09-15 | — | — |
| Mistral API | https://docs.mistral.ai/api/ | 2026-09-15 | — | — |
| Together compat | https://docs.together.ai/docs/inference/openai-compatibility | 2026-09-15 | — | — |
| Fireworks compat | https://docs.fireworks.ai/tools-sdks/openai-compatibility | 2026-09-15 | — | — |
| OpenRouter (overview + reasoning tokens) | https://openrouter.ai/docs/api_reference/overview | 2026-09-15 | — | — |
| Azure v1 API lifecycle | https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle | 2026-09-15 | — | — |

Fetch mechanics: platform.openai.com 403s scripted fetches — use
developers.openai.com; `llms.txt` indexes exist at /api/reference/llms.txt
and /api/docs/llms.txt; docs pages have `.md` twins but Stainless reference
method pages do NOT (the chat/completions `create.md` twin **404s** — it is not a stub;
use the HTML page, or the streaming-events page, whose `.md` twin does serve the full
chunk JSON schema). The legacy `completions/methods/create.md` twin works fine, so the
breakage is per-page, not a rule about Stainless twins.

## Live-verification log

| Date | What | Result |
|------|------|--------|
| 2026-09-15 | opencode (openai-compatible provider) → vLLM v0.25.1 `/v1/chat/completions` direct (local deployment, custom Rust tool/reasoning parsers) — multi-step tool loop in an isolated CI harness | PASS; clean token-leakage scan |
| 2026-09-15 | curl + opencode → LiteLLM v1.92.0 `/v1/chat/completions` → vLLM (hosted_vllm/ and openai/ prefix entries) | PASS both prefixes |
| 2026-09-15 | Prior sample claims re-verified at HEAD: vLLM protocol.py restructure (old openai/protocol.py split per-endpoint — earlier line cites stale); llama.cpp /v1/completions OAI validator confirmed dead code (zero callers); vLLM completions `best_of` field removed entirely | noted in backend-implementations.md |
