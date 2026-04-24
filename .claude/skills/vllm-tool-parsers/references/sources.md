# External sources — verification log

All external references cited by this skill, probed and timestamped. Use this table to decide when a claim needs re-verification before citing in a response.

**Skill version:** freshened 2026-04-24.
**Verification method:** `gh` CLI (no scraping). Each row lists the probe that was run.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM `vllm/tool_parsers/` directory listing | https://github.com/vllm-project/vllm/tree/main/vllm/tool_parsers | 2026-04-24 | **Fresh.** 34 parser source files (excl. `abstract_tool_parser.py`). 36 registered CLI names in `_TOOL_PARSERS_TO_REGISTER`. Probe: `gh api repos/vllm-project/vllm/contents/vllm/tool_parsers`. |
| vLLM tool-parser registry `__init__.py` | https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/__init__.py | 2026-04-24 | **Fresh.** Contains `_TOOL_PARSERS_TO_REGISTER` + `register_lazy_tool_parsers()`. 36 CLI names: deepseek_v3/v31/v32, ernie45, glm45/47, granite/granite-20b-fc/granite4, hermes, hunyuan_a13b, **hy_v3 (new)**, internlm, jamba, kimi_k2, llama3_json/llama4_json, llama4_pythonic, longcat, mimo (alias→qwen3xml), minimax/minimax_m2, mistral, olmo3, openai, phi4_mini_json, pythonic, qwen3_coder, qwen3_xml, seed_oss, step3/step3p5, xlam, gigachat3, functiongemma, gemma4. Probe: `gh api ...contents/vllm/tool_parsers/__init__.py --header 'Accept: application/vnd.github.raw'`. |
| RFC #11522 — Refactor tool parsers | https://github.com/vllm-project/vllm/issues/11522 | 2026-04-24 | **Closed 2025-09-05.** Umbrella RFC for `parse_delta`-based migration; the three follow-on PRs (below) are now merged. SKILL.md text updated accordingly. Probe: `gh issue view 11522 --repo vllm-project/vllm`. |
| PR #38755 — response API streaming migration | https://github.com/vllm-project/vllm/pull/38755 | 2026-04-24 | **Merged 2026-04-08.** `[Parser] Migrate response api streaming to unified parser`. Probe: `gh pr view 38755 --repo vllm-project/vllm`. |
| PR #39728 — Simplify parse_delta | https://github.com/vllm-project/vllm/pull/39728 | 2026-04-24 | **Merged 2026-04-13.** `[Refactor][Parser] Simplify parse_delta`. Probe: `gh pr view 39728 --repo vllm-project/vllm`. |
| PR #39446 — chat-completion auto-tool/reasoning migration | https://github.com/vllm-project/vllm/pull/39446 | 2026-04-24 | **Merged 2026-04-14.** `[Refactor][Parser] Migrate chat completion auto-tool/reasoning/plain streaming to parse_delta`. Probe: `gh pr view 39446 --repo vllm-project/vllm`. |
| Issue #30439 — Qwen3 Coder parser not streaming args | https://github.com/vllm-project/vllm/issues/30439 | 2026-04-24 | **Closed 2026-04-10.** Status now *fixed*; `parser-index.md` text updated to note closure but still flag "verify on your version". Probe: `gh issue view 30439 --repo vllm-project/vllm`. |

## Parser-count verification

SKILL.md previously claimed "28+ built-in parsers". As of 2026-04-24 the registry exposes **36 CLI names** (34 source files, one alias `mimo`, `llama3_json`/`llama4_json` sharing a class). Description updated to "36+".

## New parser since last skill update

`hy_v3` (class `HYV3ToolParser`) — a newer Hunyuan parser added to the registry. Not yet characterized in `parser-index.md` beyond a pointer; read `vllm/tool_parsers/hy_v3_tool_parser.py` for the actual grammar.

## Re-verification cadence

- Re-probe when a user asks a question that hinges on a claim older than ~90 days.
- Re-probe opportunistically whenever you already have `gh` open on the repo.
- Issues/PRs with `state=OPEN` at probe time should be re-checked first — they change faster than merged PRs.
