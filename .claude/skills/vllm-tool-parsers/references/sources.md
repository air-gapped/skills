# External sources — verification log

All external references cited by this skill, probed and timestamped. Use this table to decide when a claim needs re-verification before citing in a response.

**Skill version:** freshened **2026-07-21** against vLLM **v0.25.1** (prior pass 2026-05-28 against v0.21.0).
**Verification method:** `gh` CLI (no scraping). Each row lists the probe that was run.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM `vllm/tool_parsers/` directory listing | https://github.com/vllm-project/vllm/tree/v0.25.1/vllm/tool_parsers | 2026-07-21 | **Drift.** 45 entries at v0.25.1. **Three files deleted**: `qwen3coder_tool_parser.py`, `qwen3xml_tool_parser.py`, `minimax_tool_parser.py`. **Five new `*_engine_tool_parser.py` shims**: `qwen3_`, `gemma4_`, `deepseekv4_`, `deepseekv32_`, `seed_oss_`. Probe: `gh api repos/vllm-project/vllm/contents/vllm/tool_parsers?ref=v0.25.1`. |
| vLLM tool-parser registry `__init__.py` | https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/__init__.py | 2026-05-28 | **Fresh.** Contains `_TOOL_PARSERS_TO_REGISTER` + `register_lazy_tool_parsers()`. 43 CLI names: deepseek_v3/v31/v32/**v4 (new)**, **apertus (new)**, **cohere_command3/cohere_command4 (new)**, ernie45, functiongemma, gemma4, gigachat3, glm45/47, granite/granite-20b-fc/granite4, hermes, hunyuan_a13b, hy_v3, internlm, jamba, kimi_k2, **lfm2 (new)**, llama3_json/llama4_json, llama4_pythonic, longcat, **minicpm5 (new, file minicpm5xml)**, minimax/minimax_m2, mistral, olmo3, openai, phi4_mini_json, **poolside_v1 (new)**, pythonic, qwen3_coder, qwen3_xml, mimo (alias→qwen3xml), seed_oss, step3/step3p5, xlam. Probe: `gh api ...contents/vllm/tool_parsers/__init__.py --header 'Accept: application/vnd.github.raw'`. |
| RFC #11522 — Refactor tool parsers | https://github.com/vllm-project/vllm/issues/11522 | 2026-05-28 | **Closed 2025-09-05.** Umbrella RFC for `parse_delta`-based migration; the three follow-on PRs (below) are now merged. SKILL.md text updated accordingly. Probe: `gh issue view 11522 --repo vllm-project/vllm`. |
| PR #38755 — response API streaming migration | https://github.com/vllm-project/vllm/pull/38755 | 2026-04-24 | **Merged 2026-04-08.** `[Parser] Migrate response api streaming to unified parser`. Probe: `gh pr view 38755 --repo vllm-project/vllm`. |
| PR #39728 — Simplify parse_delta | https://github.com/vllm-project/vllm/pull/39728 | 2026-04-24 | **Merged 2026-04-13.** `[Refactor][Parser] Simplify parse_delta`. Probe: `gh pr view 39728 --repo vllm-project/vllm`. |
| PR #39446 — chat-completion auto-tool/reasoning migration | https://github.com/vllm-project/vllm/pull/39446 | 2026-04-24 | **Merged 2026-04-14.** `[Refactor][Parser] Migrate chat completion auto-tool/reasoning/plain streaming to parse_delta`. Probe: `gh pr view 39446 --repo vllm-project/vllm`. |
| Issue #30439 — Qwen3 Coder parser not streaming args | https://github.com/vllm-project/vllm/issues/30439 | 2026-05-28 | **Closed 2026-04-10.** Status now *fixed*; `parser-index.md` text updated to note closure but still flag "verify on your version". Probe: `gh issue view 30439 --repo vllm-project/vllm`. |
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-07-21 | **v0.25.1**, published 2026-07-14. Skill body pins no version by design (read the source on your version) — but note this pass had to name v0.25.1 explicitly, because parser *files* were deleted rather than merely changed. Probe: `gh release view --repo vllm-project/vllm`. |

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

## 2026-07-21 freshen — registry re-probe at v0.25.1

Still **43 CLI names**, so a count-only check would have reported "no change".
The composition moved underneath it.

**Removed — this breaks a working command line:**

- **`minimax`** is gone, along with `minimax_tool_parser.py`.
  `--tool-call-parser minimax` no longer resolves. It served MiniMax-M1
  (newline-separated JSON objects inside `<tool_calls>`, not an array).

**Added:**

- **`minimax_m3`** (`minimax_m3_tool_parser.py`), own file and class.

Net zero on the count — one out, one in. The 2026-05-28 row recorded 43 names
and this pass also finds 43, which is exactly why the *names* have to be diffed
rather than counted.

**Consolidated onto the unified parser engine (7 registry names, 5 shim files):**

| CLI name(s) | Registry class | Real implementation |
|---|---|---|
| `qwen3_coder`, `qwen3_xml`, `mimo` | `Qwen3EngineToolParser` | `vllm/parser/qwen3.py` |
| `gemma4` | `Gemma4EngineToolParser` | `vllm/parser/gemma4.py` |
| `deepseek_v4` | `DeepSeekV4EngineToolParser` | `vllm/parser/deepseek_v4.py` |
| `deepseek_v32` | `DeepSeekV32EngineToolParser` | `vllm/parser/deepseek_v32.py` |
| `seed_oss` | `SeedOssEngineToolParser` | `vllm/parser/seed_oss.py` |

Each shim subclasses the adapter from
`vllm/parser/engine/registered_adapters.py` and attaches a
`structural_tag_model` attribute — e.g.

```python
class Qwen3EngineToolParser(Qwen3ParserToolAdapter):
    structural_tag_model = "qwen_3_coder"
```

**Two guidance claims this invalidates:**

1. `qwen3_coder` vs `qwen3_xml` were documented as materially different
   implementations — a hand-rolled state machine versus an expat-based
   `StreamingXMLToolCallParser` described as "cleanest streaming in the tree" —
   with an implicit recommendation to prefer the latter. **They are now the same
   class.** The choice is a naming detail, not a quality decision, and issue
   #30439 (qwen3_coder not streaming args) is moot on the unified path.
2. `step3p5` was documented as "reuses the `qwen3_xml` expat engine". That file
   no longer exists; `step3p5_tool_parser.py` imports
   `xml.parsers.expat.ParserCreate` directly.

**Cross-skill:** this is the same refactor found in `vllm-reasoning-parsers`
this pass — `make_adapters(XParser)` yields both a reasoning and a tool adapter
from one per-model class, per RFC
[#32713](https://github.com/vllm-project/vllm/issues/32713). The RFC is **OPEN
and stale-bot-marked** while the implementation ships. For the 7 names above,
tool and reasoning behaviour are no longer independent surfaces.

Probe: `gh api repos/vllm-project/vllm/contents/vllm/tool_parsers/__init__.py?ref=v0.25.1`
plus a directory listing of `vllm/tool_parsers` and `vllm/parser`.
