# Sources — messages-api skill

Dated per-URL index. Freshen mode reads and stamps `Last verified:` here.
"Commit examined" per repo is recorded in backend-implementations.md.

All repo rows were examined by source (local clones of the upstream repos)
on 2026-07-19 at the listed commit.

| Ref | URL | Last verified | Pinned | Commit examined |
|-----|-----|---------------|--------|-----------------|
| Anthropic Messages API spec | https://platform.claude.com/docs/en/api/messages (docs.anthropic.com 301s here) | 2026-07-19 | — | — |
| vLLM (anthropic entrypoint) | https://github.com/vllm-project/vllm | 2026-07-19 | v0.25.1 | 9243e0124e |
| SGLang | https://github.com/sgl-project/sglang | 2026-07-19 | v0.5.15.post1 | 99f5a6f46b |
| LiteLLM | https://github.com/BerriAI/litellm | 2026-07-19 | v1.92.0 (live) / main | b83c60b |
| Bifrost | https://github.com/maximhq/bifrost | 2026-07-19 | — | 7a1543e85 |
| Superagent Gateway | https://github.com/superagent-ai/gateway | 2026-07-19 | — | d182a5b |
| opencode (anthropic provider) | https://github.com/sst/opencode | 2026-07-19 | v1.18.3 | 127bdb307 (v1.18.3 tag) |
| llama.cpp | https://github.com/ggml-org/llama.cpp | 2026-07-19 | b10068 | 571d0d5 |
| Ollama | https://github.com/ollama/ollama | 2026-07-19 | v0.32.1 | 573386c |
| mistral.rs | https://github.com/EricLBuehler/mistral.rs | 2026-07-19 | v0.9.0 | 0ae0476 |
| Llama Stack / OGX | https://github.com/llamastack/llama-stack | 2026-07-19 | v1.2.1 | f05b98f |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-07-19 | v11.0.0 | b09a0e9 |

## Live-verification log

| Date | What | Result |
|------|------|--------|
| 2026-07-19 | vLLM v0.25.1 `/v1/messages` raw curl + opencode anthropic provider multi-step tool loop (local deployment, custom Rust tool/reasoning parsers) | PASS; clean token-leakage scan |
| 2026-07-19 | LiteLLM v1.92.0 `/v1/messages` adapter → vLLM (opencode anthropic provider full loop) | PASS; bridges upstream via /v1/chat/completions |
| 2026-07-19 | **Claude Code CLI v2.1.214 → vLLM `/v1/messages` direct** (isolated via CLAUDE_CONFIG_DIR + ANTHROPIC_BASE_URL; 50k-ctx deployment) | PASS: 3-turn tool loop (Bash ls, Read, summary). Required `CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192` — default 32k output reservation + ~18k prompt (system+17 tools) exceeded 50k ctx by exactly 1 token |
| 2026-07-19 | Same, after pod redeployed **with `--enable-prompt-tokens-details`** | Cache fields now populate in the aggregate result usage: warm re-run reported `input_tokens: 304`, `cache_read_input_tokens: 59168` (~99.5% of prompt from prefix cache). Per-turn streamed `message_start` usage still carries null cache fields — only final totals |
