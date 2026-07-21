# Sources

Upstream primary references for claims in this skill.

## In-tree code (authoritative)

- `vllm/reasoning/abs_reasoning_parsers.py` — `ReasoningParser` ABC and `ReasoningParserManager` registry. 374 lines at v0.25.1. Last verified: 2026-07-21.
- `vllm/reasoning/basic_parsers.py` — `BaseThinkingReasoningParser`. 201 lines at v0.25.1. Last verified: 2026-07-21.
- `vllm/reasoning/__init__.py` — `_REASONING_PARSERS_TO_REGISTER` name→class mapping. **27 registered names at v0.25.1** (up from 25). Two new names: `glm47`, `minimax_m3`. Last verified: 2026-07-21.
- **`vllm/parser/` — new top-level package (NEW at v0.25.1).** One parser class per model (`qwen3.py`, `gemma4.py`, `deepseek_v4.py`, `glm47_moe.py`, `nemotron_v3.py`, `seed_oss.py`, plus `kimi_k2.py`, `minimax_m2.py`, `mistral.py`, `deepseek_v32.py`, `harmony.py`), an `abstract_parser.py` (~35 KB), `parser_manager.py`, `metrics.py`, and an `engine/` subpackage (`parser_engine.py`, `streaming_parser_engine.py`, `incremental_lexer.py`, `token_id_scanner.py`, `events.py`, `adapters.py`, `registered_adapters.py`). Last verified: 2026-07-21.
- **`vllm/parser/engine/registered_adapters.py`** — `make_adapters(XParser)` returns `(XParserReasoningAdapter, XParserToolAdapter)`, so `ReasoningParserManager` and `ToolParserManager` load lazily from **one shared per-model parser**. This is RFC #32713's unified design. Last verified: 2026-07-21.
- **`vllm/reasoning/*_engine_reasoning_parser.py`** — three-line re-export shims (`from vllm.parser.engine.registered_adapters import XParserReasoningAdapter`). Reading one of these for implementation detail finds nothing. Last verified: 2026-07-21.
- `vllm/reasoning/hy_v3_reasoning_parser.py` — `HYV3ReasoningParser` (Hunyuan V3), `<think>`/`</think>` with `reasoning_effort=no_think` → `IdentityReasoningParser` delegation. 143 lines at v0.25.1. Last verified: 2026-07-21.
- `deepseek_v4` — **no longer an alias of `deepseek_v3`.** At v0.25.1 it maps to `deepseek_v4_engine_reasoning_parser` + `DeepSeekV4ParserReasoningAdapter`, backed by its own `vllm/parser/deepseek_v4.py`. Last verified: 2026-07-21.
- `vllm/reasoning/poolside_v1_reasoning_parser.py` — `PoolsideV1ReasoningParser`, subclass of `DeepSeekV3ReasoningParser`; overrides `is_reasoning_end` to scope the backward `</think>` scan to the current assistant turn (`<assistant>` token) so a stray `</think>` in history/few-shot doesn't short-circuit `prompt_is_reasoning_end`. Registered as `poolside_v1`; new since 2026-04 sweep. Last verified: 2026-05-28.
- `vllm/reasoning/cohere_command_reasoning_parser.py` — 571 lines; holds `BaseCohereCommandReasoningParser` plus `CohereCommand3ReasoningParser` (`cohere_command3`) and `CohereCommand4ReasoningParser` (`cohere_command4`). Delimiters are the vocab tokens `<|START_THINKING|>` / `<|END_THINKING|>`, with `<|CHATBOT_TOKEN|>` also resolved. **The two subclasses differ only by a filter profile** — `PyFilterOptions().cmd3()` vs `.cmd4()` for streaming, and the same with `.no_tools()` for unary; neither adds a thinking-disable switch. Last verified: 2026-07-21.
- `glm45` / `holo2` — **diverged at v0.25.1.** `holo2` still maps to `deepseek_v3_reasoning_parser` + `DeepSeekV3ReasoningWithThinkingParser` (default thinking-on). `glm45` moved to `glm47_moe_reasoning_parser` + `Glm47MoeParserReasoningAdapter`, shared with the new `glm47` name. Last verified: 2026-07-21.
- `mimo` — still a registry alias of `qwen3`, but both now map to `qwen3_engine_reasoning_parser` + `Qwen3ParserReasoningAdapter` (logic in `vllm/parser/qwen3.py`). Last verified: 2026-07-21.
- `vllm/entrypoints/openai/chat_completion/protocol.py` — response field is `reasoning` on `ChatMessage.reasoning` / `DeltaMessage.reasoning` (renamed from `reasoning_content`); request side still accepts `reasoning_content` via backward-compat normalization. Last verified: 2026-05-28.
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
- [#23429](https://github.com/vllm-project/vllm/issues/23429) — DeepSeek-V3.1 mis-routes `thinking: false`. State: CLOSED `COMPLETED` 2025-08-24 (a real fix). Last verified: 2026-07-21.
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
- [#32713](https://github.com/vllm-project/vllm/issues/32713) — RFC: unified parser for reasoning + tool calling. **State 2026-07-21: OPEN and stale-bot-marked** ("no activity within 90 days… will be automatically closed") — *while its implementation is already shipping* in `vllm/parser/`. The tracker state says nothing about whether the work landed; read the tree. Last verified: 2026-07-21.
- [#20227](https://github.com/vllm-project/vllm/issues/20227) — how to write a custom reasoning parser. State: CLOSED **`NOT_PLANNED`** 2025-10-29 — closed *without* an upstream change; the value is the last comment, a working CLI-wrapper workaround that registers a parser via `@ReasoningParserManager.register_module` before calling `vllm.entrypoints.cli.main`. That workaround is what this skill documents, so the `NOT_PLANNED` label does not diminish it — but do not read this issue as "vLLM added first-class support". Last verified: 2026-07-21.
- [Magistral discussion](https://huggingface.co/mistralai/Magistral-Small-2506/discussions/17) — Mistral tokenizer-mode requirement.
- [#27755](https://github.com/vllm-project/vllm/issues/27755) — RFC `reasoning_content` → `reasoning` response-field rename; backward-compat kept request-side. Last verified: 2026-05-28.

## OpenAI harmony

- https://cookbook.openai.com/articles/openai-harmony — the spec.
- https://github.com/openai/harmony — renderer / reference impl (vLLM vendors via `openai-harmony` package).

## Freshen sweep log

- 2026-04-24 — Probed `vllm/reasoning/` contents (22 registered names in `__init__.py`, up from 21); added `hy_v3` (HYV3ReasoningParser, `<think>`/`</think>` + reasoning_effort identity delegate) to parser matrix and skill header. Verified issues #20227 and #23429 remain CLOSED. Source: `gh api repos/vllm-project/vllm/contents/vllm/reasoning/__init__.py`.
- 2026-05-28 — Re-probed `vllm/reasoning/__init__.py` (verified line-by-line against the actual `_REASONING_PARSERS_TO_REGISTER` dict): **25** registered names (up from 22). Four new names: `deepseek_v4` (alias of `deepseek_v3` → `DeepSeekV3ReasoningParser`), `poolside_v1` (`PoolsideV1ReasoningParser`, own file, subclass of `DeepSeekV3ReasoningParser`), `cohere_command3` + `cohere_command4` (both in the shared `cohere_command_reasoning_parser.py`). Corrected pre-existing matrix rows against the verified registry: `gemma4` class is `Gemma4ReasoningParser`, `olmo3` class is `Olmo3ReasoningParser`; `glm45`/`holo2` remain bundled as `DeepSeekV3ReasoningWithThinkingParser` and `mimo` remains aliased to `Qwen3ReasoningParser` (NOT separate files — an earlier draft of this sweep wrongly claimed they had been split out; corrected same-session). Reconciled count to 25 across SKILL.md description + matrix intro + this file; added the new matrix rows. Confirmed (via RFC #27755) response field is `ChatMessage.reasoning` with request-side `reasoning_content` backward-compat. Source: `gh api repos/vllm-project/vllm/contents/vllm/reasoning/__init__.py` (raw, line-numbered). NOTE: in-tree code anchors (abs_reasoning_parsers.py, basic_parsers.py, hy_v3) and issue-state rows (#23429, #20227 — both re-confirmed CLOSED via `gh issue view` this session) remain stamped 2026-04-24 — re-verify file:line anchors on the next freshen to clear the Dim 9 staleness cap.

- 2026-07-21 — Re-probed `_REASONING_PARSERS_TO_REGISTER` at tag **v0.25.1**: **27** names (up from 25). Two genuinely new: `glm47`, `minimax_m3`.

  **The bigger finding is structural, not a count.** A refactor has introduced a
  new top-level **`vllm/parser/`** package implementing RFC #32713's unified
  reasoning+tool parser. `make_adapters(XParser)` derives both an
  `XParserReasoningAdapter` and an `XParserToolAdapter` from a single per-model
  class, and the old `vllm/reasoning/*_engine_reasoning_parser.py` files are now
  three-line re-export shims. **8 of the 27 registry names are on this path**:
  `deepseek_v4`, `gemma4`, `glm45`, `glm47`, `mimo`, `nemotron_v3`, `qwen3`,
  `seed_oss`. Their matrix rows named the wrong class *and* the wrong file.

  Two corrections that change behavioural claims, not just paths:
  - **`deepseek_v4` is no longer an alias of `deepseek_v3`.** It now has its own
    `DeepSeekV4Parser`. The matrix said "same file + class, registered under a
    second name" — that is no longer true.
  - **`glm45` and `holo2` have diverged.** They shared a row as
    `DeepSeekV3ReasoningWithThinkingParser` (thinking-default-on). `glm45` moved
    to the adapter path and now shares with the new `glm47`; only `holo2` still
    uses the DeepSeek-V3 thinking variant. Row split.

  The migration is **partial**: `vllm/parser/` also holds `kimi_k2.py`,
  `minimax_m2.py`, `mistral.py`, `deepseek_v32.py` whose *reasoning* registry
  entries still point at legacy files. So the existence of a `vllm/parser/`
  module does not tell you which implementation the reasoning path uses —
  `_REASONING_PARSERS_TO_REGISTER` is the only authority.

  RFC #32713 itself is OPEN and stale-bot-marked while all of the above ships.
  Source: `gh api repos/vllm-project/vllm/contents/{vllm/reasoning/__init__.py,vllm/parser,vllm/parser/engine}?ref=v0.25.1`.
