# External sources — verification log

All external references cited by this skill, probed and timestamped. Use this table to decide when a claim needs re-verification before citing in a response.

**Skill version:** freshened 2026-05-28.
**Verification method:** `gh` CLI (no scraping). Each row lists the probe that was run.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM `vllm/tool_parsers/` directory listing | https://github.com/vllm-project/vllm/tree/main/vllm/tool_parsers | 2026-05-28 | **Fresh.** 40 parser source files (excl. `abstract_tool_parser.py`). 43 registered CLI names in `_TOOL_PARSERS_TO_REGISTER`. Probe: `gh api repos/vllm-project/vllm/contents/vllm/tool_parsers`. |
| vLLM tool-parser registry `__init__.py` | https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/__init__.py | 2026-05-28 | **Fresh.** Contains `_TOOL_PARSERS_TO_REGISTER` + `register_lazy_tool_parsers()`. 43 CLI names: deepseek_v3/v31/v32/**v4 (new)**, **apertus (new)**, **cohere_command3/cohere_command4 (new)**, ernie45, functiongemma, gemma4, gigachat3, glm45/47, granite/granite-20b-fc/granite4, hermes, hunyuan_a13b, hy_v3, internlm, jamba, kimi_k2, **lfm2 (new)**, llama3_json/llama4_json, llama4_pythonic, longcat, **minicpm5 (new, file minicpm5xml)**, minimax/minimax_m2, mistral, olmo3, openai, phi4_mini_json, **poolside_v1 (new)**, pythonic, qwen3_coder, qwen3_xml, mimo (alias→qwen3xml), seed_oss, step3/step3p5, xlam. Probe: `gh api ...contents/vllm/tool_parsers/__init__.py --header 'Accept: application/vnd.github.raw'`. |
| RFC #11522 — Refactor tool parsers | https://github.com/vllm-project/vllm/issues/11522 | 2026-05-28 | **Closed 2025-09-05.** Umbrella RFC for `parse_delta`-based migration; the three follow-on PRs (below) are now merged. SKILL.md text updated accordingly. Probe: `gh issue view 11522 --repo vllm-project/vllm`. |
| PR #38755 — response API streaming migration | https://github.com/vllm-project/vllm/pull/38755 | 2026-04-24 | **Merged 2026-04-08.** `[Parser] Migrate response api streaming to unified parser`. Probe: `gh pr view 38755 --repo vllm-project/vllm`. |
| PR #39728 — Simplify parse_delta | https://github.com/vllm-project/vllm/pull/39728 | 2026-04-24 | **Merged 2026-04-13.** `[Refactor][Parser] Simplify parse_delta`. Probe: `gh pr view 39728 --repo vllm-project/vllm`. |
| PR #39446 — chat-completion auto-tool/reasoning migration | https://github.com/vllm-project/vllm/pull/39446 | 2026-04-24 | **Merged 2026-04-14.** `[Refactor][Parser] Migrate chat completion auto-tool/reasoning/plain streaming to parse_delta`. Probe: `gh pr view 39446 --repo vllm-project/vllm`. |
| Issue #30439 — Qwen3 Coder parser not streaming args | https://github.com/vllm-project/vllm/issues/30439 | 2026-05-28 | **Closed 2026-04-10.** Status now *fixed*; `parser-index.md` text updated to note closure but still flag "verify on your version". Probe: `gh issue view 30439 --repo vllm-project/vllm`. |
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-05-28 | **v0.21.0**, published 2026-05-15. Skill body pins no version by design (read the source on your version). Probe: `gh release view --repo vllm-project/vllm`. |

## Parser-count verification

SKILL.md originally claimed "28+ built-in parsers", then "36+". As of 2026-05-28 the registry exposes **43 CLI names** (40 source files, one alias `mimo`, `llama3_json`/`llama4_json` sharing a class). Description updated to "40+".

## New parsers since last skill update (2026-05-28)

Seven parsers added to the registry since the 2026-04-24 freshen, now characterized in `parser-index.md` and the SKILL.md family table (read the source for full grammar):

- `deepseek_v4` (`DeepSeekV4ToolParser`) — V4 successor to the v3 family; same full-width `<｜tool▁calls▁begin｜>` (U+FF5C + U+2581) sentinels.
- `apertus` (`ApertusToolParser`) — JSON array in `<tool_calls>`/`</tool_calls>`; has streaming.
- `cohere_command3` (`CohereCommand3ToolParser`) — Command-A / Command-R7B; `<|START_ACTION|>` JSON-array grammar, keys `tool_name`/`parameters`.
- `cohere_command4` (`CohereCommand4ToolParser`) — Command-A-Reasoning / Command-A-Vision; same grammar as command3.
- `lfm2` (`LFM2ToolParser`) — Liquid LFM2 pythonic `[func(arg=val)]` in `<|tool_call_start|>`/`<|tool_call_end|>`; non-streaming.
- `minicpm5` (`MiniCPM5XMLToolParser`, file `minicpm5xml_tool_parser.py`) — XML `<function>`/`<parameter>` tags inside `<|tool_call_start|>`/`<|tool_call_end|>`.
- `poolside_v1` (`PoolsideV1ToolParser`) — GLM-4-style `<tool_call>` with `<arg_key>`/`<arg_value>` tags (not JSON-in-tags); incremental string streaming.

`hy_v3` (class `HYV3ToolParser`, added in the prior freshen) is now in the SKILL.md family table as well.

## Re-verification cadence

- Re-probe when a user asks a question that hinges on a claim older than ~90 days.
- Re-probe opportunistically whenever you already have `gh` open on the repo.
- Issues/PRs with `state=OPEN` at probe time should be re-checked first — they change faster than merged PRs.
