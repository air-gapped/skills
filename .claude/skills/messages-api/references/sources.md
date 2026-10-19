# Sources — messages-api skill

Dated per-URL index. Freshen mode reads and stamps `Last verified:` here.
"Commit examined" per repo is recorded in backend-implementations.md.

Freshened: 2026-09-22 — every row probed. The opencode row's v2 claim was briefly "corrected" this pass on the strength of `gh release list`, which reports v1.18.32 as latest; that was wrong. opencode runs two parallel lines, and the v2 one publishes **git tags and npm `@opencode/cli` but no GitHub Release object**, so the releases API cannot see it. Row now records both lines (v1 1.18.32, v2 2.0.13) and where to look for each.

The pinned versions below are **point-in-time examination snapshots, not latest-version claims** — every upstream here has released since, which is expected and not drift. `llama.cpp` also changed tag scheme, from `bNNNNN` nightly builds to semver.

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
| opencode (anthropic provider) | https://github.com/anomalyco/opencode | 2026-09-22 | v1.18.3 examined; **two live lines — v1 at 1.18.32, v2 at 2.0.13** | 127bdb307 (v1.18.3 tag) — **repo moved `sst/` → `anomalyco/`**; the old URL redirects but is no longer canonical. **v2 ships on a separate channel and is invisible to `gh release list`**: npm `@opencode/cli` (not `opencode-ai`), `https://opencode.ai/v2/install`, brew `anomalyco/tap/opencode-v2`, AUR `opencode-beta`, docs `https://opencode.ai/v2/docs`. Git tags `v2.0.0`–`v2.0.13` and a `2.0` branch exist; **no GitHub Release object does**, so the releases API reports v1.18.32 as latest. Check `…/tags` and the npm dist-tag, not `gh release list`. |
| llama.cpp | https://github.com/ggml-org/llama.cpp | 2026-07-19 | b10068 | 571d0d5 |
| Ollama | https://github.com/ollama/ollama | 2026-07-19 | v0.32.1 | 573386c |
| mistral.rs | https://github.com/EricLBuehler/mistral.rs | 2026-07-19 | v0.9.0 | 0ae0476 |
| Llama Stack / OGX | https://github.com/ogx-ai/ogx | 2026-09-15 | v1.2.1 examined; v1.5.0 `isLatest` on 2026-10-20 | f05b98f — **repo moved and the project renamed**: its README now reads "Llama Stack is now OGX" |
| Lemonade (AMD) | https://github.com/lemonade-sdk/lemonade | 2026-07-19 | v11.0.0 | b09a0e9 |

## 2026-10-20 freshen — claims re-checked at latest tags

| Finding | Source (ref checked) |
|---|---|
| OGX: `gh repo view llamastack/llama-stack` resolves to `ogx-ai/ogx`; passthrough moved into `AnthropicMixin(OpenAIMixin)` used by vllm/ollama/meta/anthropic/deepseek/fireworks adapters; skills/containers routes are `/v1alpha` | ogx-ai/ogx v1.5.0 `src/ogx/providers/utils/inference/anthropic_mixin.py:44,159`; `src/ogx_api/skills/fastapi_routes.py:41` |
| Official stop_reason set is end_turn, max_tokens, stop_sequence, tool_use, pause_turn, refusal, model_context_window_exceeded ("Treat the response as truncated"); refusals carry `stop_details` | https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons ; StopReason type on https://platform.claude.com/docs/en/api/messages |
| Bifrost passthrough requires `IsClaudeCodeRequest(ctx) && isClaudeModel(...)` (same at snapshot 7a1543e85, `anthropic.go:357-358`); raw forwarder `/anthropic_passthrough` | maximhq/bifrost origin/main 4de5eafcc (transports/v2.3.1) `transports/bifrost-http/integrations/anthropic.go:383-431,900`, `passthrough.go:58` |
| LiteLLM handler moved `experimental_pass_through/` → `pass_through/`; native set now in `litellm/utils.py:9021-9100` (adds edenai, bedrock_mantle, JSON-registry providers; vertex_ai/azure_ai/github_copilot gated on "claude" in the model name); Responses bridge skipped when `compaction` is set | BerriAI/litellm v1.106.0 `pass_through/messages/handler.py:499-634` (cascade 531-634), `:550` |
| LiteLLM bridge translates `output_config` (effort→`reasoning_effort`, format→`response_format`) and strips the raw key — already so at b83c60b (`adapters/transformation.py:979-983,1014-1025`); "dropped" was wrong | BerriAI/litellm v1.106.0 `pass_through/adapters/transformation.py:1144-1159,1195-1197`; `pass_through/messages/handler.py:39` `ANTHROPIC_ONLY_REQUEST_KEYS` |
| LiteLLM bridge maps upstream `content_filter`/`refusal` → `refusal` + `stop_details` (absent at b83c60b) | BerriAI/litellm v1.106.0 `litellm/llms/anthropic/pass_through/adapters/transformation.py:1440-1441,1614`; `adapters/streaming_iterator.py:1090` |
| OGX translation path generates `ping`, never emits `stop_sequence`, maps thinking enabled→reasoning_effort by budget (all already true at snapshot f05b98f: `anthropic_translation.py:340,428,432` PingEvent, `:75` _FINISH_TO_STOP_REASON) | ogx-ai/ogx v1.5.0 `src/ogx/providers/utils/inference/anthropic_translation.py:82-87,243,276-288,337,404` |
| mistral.rs v0.9.3+ (#2400, 9e53d6f) replays assistant thinking as `reasoning_content` and reports `cache_read_input_tokens`; v0.9.2 still drops thinking and has no cache fields | EricLBuehler/mistral.rs v0.9.5 `mistralrs-server-core/src/anthropic.rs:395-398,881-896,1112-1120`; v0.9.2 `:746` drops `"thinking"` |
| Lemonade handles `thinking` enabled/disabled→`enable_thinking` (already at snapshot b09a0e9, `anthropic_api.cpp:427-434` — the "No (basic)" cell was wrong); verbatim relay for Anthropic-wire cloud providers (#3223, f174a054) | lemonade-sdk/lemonade v2026.42.1 `src/cpp/server/anthropic_api.cpp:190,281-285,678-685,1155-1174` |
| Signatures: Ollama never emits signature_delta (true at snapshot 573386c too — only an unused struct field); SGLang emits it only when a real signature was captured (same at 99f5a6f46b); llama.cpp sends an empty string | ollama v0.40.6 `anthropic/anthropic.go:272-276,843`; sglang v0.5.22 `anthropic/serving.py:888-896,1271`; llama.cpp b11742 `tools/server/server-task.cpp:910-918` |
| vLLM reports `stop_sequence` since v0.29.0 (#45807, e85dd21497); streaming `message_delta` sets it since v0.30.0 (#55325) | vllm-project/vllm v0.32.0 `serving.py:102-131` `_to_anthropic_stop_reason`, `:1053` |
| vLLM `thinking` param modeled since v0.31.0 (#58613): enabled→`thinking_token_budget`, disabled→reasoning off, adaptive ignored | vllm-project/vllm v0.32.0 `vllm/entrypoints/anthropic/protocol.py:223`, `serving.py:644-649`; first stable tag containing 5a2ed2e7ee = v0.31.0 |

## Live-verification log

| Date | What | Result |
|------|------|--------|
| 2026-07-19 | vLLM v0.25.1 `/v1/messages` raw curl + opencode anthropic provider multi-step tool loop (local deployment, custom Rust tool/reasoning parsers) | PASS; clean token-leakage scan |
| 2026-07-19 | LiteLLM v1.92.0 `/v1/messages` adapter → vLLM (opencode anthropic provider full loop) | PASS; bridges upstream via /v1/chat/completions |
| 2026-07-19 | **Claude Code CLI v2.1.214 → vLLM `/v1/messages` direct** (isolated via CLAUDE_CONFIG_DIR + ANTHROPIC_BASE_URL; 50k-ctx deployment) | PASS: 3-turn tool loop (Bash ls, Read, summary). Required `CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192` — default 32k output reservation + ~18k prompt (system+17 tools) exceeded 50k ctx by exactly 1 token |
| 2026-07-19 | Same, after pod redeployed **with `--enable-prompt-tokens-details`** | Cache fields now populate in the aggregate result usage: warm re-run reported `input_tokens: 304`, `cache_read_input_tokens: 59168` (~99.5% of prompt from prefix cache). Per-turn streamed `message_start` usage still carries null cache fields — only final totals |
