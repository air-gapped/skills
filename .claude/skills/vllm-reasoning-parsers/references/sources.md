# Sources

Upstream primary references for claims in this skill.

## In-tree code (authoritative)

- `vllm/reasoning/abs_reasoning_parsers.py` — `ReasoningParser` ABC and `ReasoningParserManager` registry. Last verified: 2026-04-24.
- `vllm/reasoning/basic_parsers.py` — `BaseThinkingReasoningParser`. Last verified: 2026-04-24.
- `vllm/reasoning/__init__.py` — `_REASONING_PARSERS_TO_REGISTER` name→class mapping. Verified 22 registered names on `main` (added `hy_v3` since last stamp). Last verified: 2026-04-24.
- `vllm/reasoning/hy_v3_reasoning_parser.py` — `HYV3ReasoningParser` (Hunyuan V3), `<think>`/`</think>` with `reasoning_effort=no_think` → `IdentityReasoningParser` delegation. New since 2026-04 sweep. Last verified: 2026-04-24.
- `vllm/config/reasoning.py` — `ReasoningConfig.initialize_token_ids` (derives reasoning_start/end_token_ids for structured-output backends).
- `vllm/engine/arg_utils.py:552,862` — `--reasoning-parser` / `--reasoning-parser-plugin` CLI argument declaration.
- `vllm/entrypoints/openai/api_server.py:380,477,523–530,544–545` — validation + plugin import on server startup.
- `vllm/entrypoints/openai/chat_completion/serving.py:103,130,240,326–330,595,724–731,825–870,940–955,1365–1373` — per-request instantiation, `prompt_is_reasoning_end_arr` caching, `extract_reasoning_streaming` + `extract_reasoning` call sites, tool-parser content-only contract.
- `vllm/entrypoints/openai/chat_completion/batch_serving.py:264–270` — batch mode parser use.
- `vllm/v1/structured_output/__init__.py:295–334` — xgrammar gating via `is_reasoning_end` / `is_reasoning_end_streaming`.
- Tests in `tests/reasoning/` — canonical contract tests per parser.

## Upstream docs

- https://docs.vllm.ai/en/latest/features/reasoning_outputs/ — official reasoning-outputs guide.
- https://docs.vllm.ai/en/stable/api/vllm/reasoning/ — per-parser API reference (auto-generated).
- https://docs.vllm.ai/en/latest/features/structured_outputs/ — structured output interaction.

## Upstream issues / PRs (linked in pitfalls.md)

- [#19222](https://github.com/vllm-project/vllm/issues/19222) — `deepseek_r1` wrong output with `enable_thinking=False`.
- [#23429](https://github.com/vllm-project/vllm/issues/23429) — DeepSeek-V3.1 mis-routes `thinking: false`. State: CLOSED (fixed 2025-08-24). Last verified: 2026-04-24.
- [#13125](https://github.com/vllm-project/vllm/issues/13125) — DeepSeek-R1-Distill-Qwen-32B missing start `<think>`.
- [HF discussion](https://huggingface.co/deepseek-ai/DeepSeek-R1/discussions/144) — chat template injects `<think>\n`, downstream `reasoning_content` null.
- [Discussion #12708](https://github.com/vllm-project/vllm/discussions/12708) — nested `<think>` tags in DeepSeek-R1 output.
- [#18819](https://github.com/vllm-project/vllm/issues/18819) — Qwen3 broken structured output with `enable_thinking=False`.
- [#17655](https://github.com/vllm-project/vllm/issues/17655) — Qwen3 streaming function-call regression.
- [#19051](https://github.com/vllm-project/vllm/issues/19051) — Qwen3 + reasoning + `tool_choice: required` → 400.
- [#26239](https://github.com/vllm-project/vllm/issues/26239) — Qwen3-VL parser request.
- [#34684](https://github.com/vllm-project/vllm/issues/34684) — Qwen3.5 reasoning leaked into content.
- [#35221](https://github.com/vllm-project/vllm/issues/35221) — `qwen3` parser routes reasoning-only output as content.
- [#39130](https://github.com/vllm-project/vllm/issues/39130) — `gemma4` silently disables xgrammar with `enable_thinking=False`.
- [#31954](https://github.com/vllm-project/vllm/issues/31954) — OLMo3 parser fails to detect `</think>` end → GCD not activated.
- [#17638](https://github.com/vllm-project/vllm/discussions/17638) — structured generation with reasoning parser in offline mode.
- [#32713](https://github.com/vllm-project/vllm/issues/32713) — RFC: unified parser for reasoning + tool calling.
- [#20227](https://github.com/vllm-project/vllm/issues/20227) — how to write a custom reasoning parser (the working answer). State: CLOSED (resolved 2025-10-29). Last verified: 2026-04-24.
- [Magistral discussion](https://huggingface.co/mistralai/Magistral-Small-2506/discussions/17) — Mistral tokenizer-mode requirement.

## OpenAI harmony

- https://cookbook.openai.com/articles/openai-harmony — the spec.
- https://github.com/openai/harmony — renderer / reference impl (vLLM vendors via `openai-harmony` package).

## Freshen sweep log

- 2026-04-24 — Probed `vllm/reasoning/` contents (22 registered names in `__init__.py`, up from 21); added `hy_v3` (HYV3ReasoningParser, `<think>`/`</think>` + reasoning_effort identity delegate) to parser matrix and skill header. Verified issues #20227 and #23429 remain CLOSED. Source: `gh api repos/vllm-project/vllm/contents/vllm/reasoning/__init__.py`.
