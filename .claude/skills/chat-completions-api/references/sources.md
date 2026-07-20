# Sources — chat-completions-api skill

Dated per-URL index. Freshen mode reads and stamps `Last verified:` here.
All repo rows examined by source (local clones of the upstream repos) at
the listed commit on 2026-07-19.

| Ref | URL | Last verified | Pinned | Commit examined |
|-----|-----|---------------|--------|-----------------|
| CC create (request/response) | https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create | 2026-07-19 | — | — |
| CC streaming events (full chunk schema; .md twin) | https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events | 2026-07-19 | — | — |
| Stored completions (list/retrieve/update/delete/messages) | https://developers.openai.com/api/reference/chat-completions/overview | 2026-07-19 | — | — |
| Legacy completions create | https://developers.openai.com/api/reference/resources/completions/methods/create | 2026-07-19 | — | — |
| Deprecations (.md twin works) | https://developers.openai.com/api/docs/deprecations | 2026-07-19 | — | — |
| Changelog | https://developers.openai.com/api/docs/changelog | 2026-07-19 | — | — |
| Reasoning guide (effort values) | https://developers.openai.com/api/docs/guides/reasoning | 2026-07-19 | — | — |
| Prompt caching guide (breakpoints, cache_write_tokens) | https://developers.openai.com/api/docs/guides/prompt-caching | 2026-07-19 | — | — |
| vLLM | https://github.com/vllm-project/vllm | 2026-07-19 | v0.25.1 (live-tested) / main | 9243e0124e |
| SGLang | https://github.com/sgl-project/sglang | 2026-07-19 | v0.5.15.post1 | 99f5a6f46b |
| llama.cpp | https://github.com/ggml-org/llama.cpp | 2026-07-19 | b10068 | 571d0d5 |
| Ollama | https://github.com/ollama/ollama | 2026-07-19 | v0.32.1 | 573386c |
| mistral.rs | https://github.com/EricLBuehler/mistral.rs | 2026-07-19 | v0.9.0 | 0ae0476 |
| Llama Stack / OGX | https://github.com/llamastack/llama-stack | 2026-07-19 | v1.2.1 | f05b98f |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-07-19 | v11.0.0 | b09a0e9 |
| LiteLLM | https://github.com/BerriAI/litellm | 2026-07-19 | v1.92.0 (live) / main | b83c60b |
| Bifrost | https://github.com/maximhq/bifrost | 2026-07-19 | — | 7a1543e85 |
| Superagent Gateway | https://github.com/superagent-ai/gateway | 2026-07-19 | — | d182a5b |
| opencode + pinned AI SDK tarballs | https://github.com/sst/opencode | 2026-07-19 | v1.18.3; @ai-sdk/openai@3.0.84, openai-compatible@2.0.41 | 127bdb307 (v1.18.3 tag) |
| Cline (llms SDK provider) | https://github.com/cline/cline | 2026-07-19 | main (gh api) | — |
| Anthropic OpenAI-compat layer | https://platform.claude.com/docs/en/api/openai-sdk | 2026-07-19 | — | — |
| Gemini OpenAI-compat | https://ai.google.dev/gemini-api/docs/openai | 2026-07-19 | — | — |
| DeepSeek API docs (+thinking/prefix/FIM guides) | https://api-docs.deepseek.com/ | 2026-07-19 | — | — |
| xAI CC (legacy) + deferred completions | https://docs.x.ai/developers/model-capabilities/legacy/chat-completions | 2026-07-19 | — | — |
| Groq OpenAI-compat + reasoning | https://console.groq.com/docs/openai | 2026-07-19 | — | — |
| Mistral API | https://docs.mistral.ai/api/ | 2026-07-19 | — | — |
| Together compat | https://docs.together.ai/docs/openai-api-compatibility | 2026-07-19 | — | — |
| Fireworks compat | https://docs.fireworks.ai/tools-sdks/openai-compatibility | 2026-07-19 | — | — |
| OpenRouter (overview + reasoning tokens) | https://openrouter.ai/docs/api-reference/overview | 2026-07-19 | — | — |
| Azure v1 API lifecycle | https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle | 2026-07-19 | — | — |

Fetch mechanics: platform.openai.com 403s scripted fetches — use
developers.openai.com; `llms.txt` indexes exist at /api/reference/llms.txt
and /api/docs/llms.txt; docs pages have `.md` twins but Stainless reference
method pages have stub twins (use HTML or the streaming-events page, which
embeds the full chunk JSON schema).

## Live-verification log

| Date | What | Result |
|------|------|--------|
| 2026-07-19 | opencode (openai-compatible provider) → vLLM v0.25.1 `/v1/chat/completions` direct (local deployment, custom Rust tool/reasoning parsers) — multi-step tool loop in an isolated CI harness | PASS; clean token-leakage scan |
| 2026-07-19 | curl + opencode → LiteLLM v1.92.0 `/v1/chat/completions` → vLLM (hosted_vllm/ and openai/ prefix entries) | PASS both prefixes |
| 2026-07-19 | Prior sample claims re-verified at HEAD: vLLM protocol.py restructure (old openai/protocol.py split per-endpoint — earlier line cites stale); llama.cpp /v1/completions OAI validator confirmed dead code (zero callers); vLLM completions `best_of` field removed entirely | noted in backend-implementations.md |
