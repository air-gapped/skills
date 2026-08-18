# External sources — verification log

All external references cited by this skill, probed and timestamped. Use this table to decide when a claim needs re-verification before citing in a response.

**Skill version:** freshened **2026-08-11** against vLLM **v0.27.0** (published 2026-08-10; prior passes 2026-07-21/v0.25.1, 2026-05-28/v0.21.0).
**Verification method:** `gh` CLI plus read-only `git show <tag>:<path>` against a local `vllm-project/vllm` clone. Each row lists the probe that was run.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM `vllm/tool_parsers/` directory listing | https://github.com/vllm-project/vllm/tree/v0.27.0/vllm/tool_parsers | **2026-08-11** | 47 entries at v0.27.0. Delta from v0.25.1 is exactly **two additions**: `inkling_tool_parser.py`, `kimi_k3_tool_parser.py`; no deletions. (v0.25.1 had deleted `qwen3coder_`, `qwen3xml_`, `minimax_tool_parser.py`.) Probe: `git ls-tree --name-only v0.27.0 vllm/tool_parsers/`. |
| vLLM tool-parser registry `__init__.py` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/tool_parsers/__init__.py | **2026-08-11** | `_TOOL_PARSERS_TO_REGISTER` + `register_lazy_tool_parsers()`. **45 CLI names at v0.27.0** (43 at v0.25.1): apertus, cohere_command3, cohere_command4, deepseek_v3, deepseek_v31, deepseek_v32, deepseek_v4, ernie45, functiongemma, gemma4, gigachat3, glm45, glm47, granite, granite-20b-fc, granite4, hermes, hunyuan_a13b, hy_v3, **inkling (new)**, internlm, jamba, kimi_k2, **kimi_k3 (new)**, lfm2, llama3_json, llama4_json, llama4_pythonic, longcat, mimo, minicpm5, minimax_m2, minimax_m3, mistral, olmo3, openai, phi4_mini_json, poolside_v1, pythonic, qwen3_coder, qwen3_xml, seed_oss, step3, step3p5, xlam. The bare `minimax` name is still absent. Probe: `gh api ...contents/vllm/tool_parsers/__init__.py?ref=v0.27.0 --header 'Accept: application/vnd.github.raw'`. |
| PR #48947 — unified engine-based Mistral parser | https://github.com/vllm-project/vllm/pull/48947 | **2026-08-11** | **MERGED 2026-07-30**, ships in v0.27.0. `[PARSER][Mistral] unified engine-based parser for reasoning and tool calls`. **CLI names are unchanged** — `--tool-call-parser mistral` and `--reasoning-parser mistral` still resolve; only the implementation moved to `vllm/parser/mistral.py`. Covers pre-v11 (old tool format, no reasoning) and v11+ (new format, optional reasoning), text- or special-token-based reasoning, mistral-common grammar; empty tool-call names became valid on v11+. Probe: `gh pr view 48947 -R vllm-project/vllm --json title,state,mergedAt,body`. |
| PR #45560 — GPT-OSS strict tool call + constrained decoding for Harmony | https://github.com/vllm-project/vllm/pull/45560 | **2026-08-11** | **MERGED 2026-08-01**, ships in v0.27.0. Rewrites `json_object`/`json_schema` `response_format` into a Harmony-aware `structural_tag` in `HarmonyParser.adjust_request` so constrained decoding governs the entire generation rather than only the final channel; two paths (with/without builtin tools). Also **removed** `GptOssReasoningParser`'s reasoning-end machinery — see the reasoning-parsers skill. Probe: `gh pr view 45560 -R vllm-project/vllm`. |
| PR #50403 — bare Inkling text preserved | https://github.com/vllm-project/vllm/pull/50403 | **2026-08-11** | **MERGED 2026-07-30**. Python *and* Rust Inkling parsers buffer text emitted straight after `<\|message_model\|>` with no content-kind marker, emitting it as assistant content at the end marker, while still discarding it when a typed marker proves it was header metadata (tool name / author). Probe: `gh pr view 50403 -R vllm-project/vllm`. |
| RFC #11522 — Refactor tool parsers | https://github.com/vllm-project/vllm/issues/11522 | 2026-05-28 | **Closed 2025-09-05.** Umbrella RFC for `parse_delta`-based migration; the three follow-on PRs (below) are now merged. SKILL.md text updated accordingly. Probe: `gh issue view 11522 --repo vllm-project/vllm`. |
| PR #38755 — response API streaming migration | https://github.com/vllm-project/vllm/pull/38755 | 2026-08-18 | **Merged 2026-04-08.** `[Parser] Migrate response api streaming to unified parser`. Probe: `gh pr view 38755 --repo vllm-project/vllm`. |
| PR #39728 — Simplify parse_delta | https://github.com/vllm-project/vllm/pull/39728 | 2026-08-18 | **Merged 2026-04-13.** `[Refactor][Parser] Simplify parse_delta`. Probe: `gh pr view 39728 --repo vllm-project/vllm`. |
| PR #39446 — chat-completion auto-tool/reasoning migration | https://github.com/vllm-project/vllm/pull/39446 | 2026-08-18 | **Merged 2026-04-14.** `[Refactor][Parser] Migrate chat completion auto-tool/reasoning/plain streaming to parse_delta`. Probe: `gh pr view 39446 --repo vllm-project/vllm`. |
| Issue #30439 — Qwen3 Coder parser not streaming args | https://github.com/vllm-project/vllm/issues/30439 | 2026-05-28 | **Closed 2026-04-10.** Status now *fixed*; `parser-index.md` text updated to note closure but still flag "verify on your version". Probe: `gh issue view 30439 --repo vllm-project/vllm`. |
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | **2026-08-11** | Latest is **v0.27.1**, published 2026-08-11T10:47Z — a single-change patch on v0.27.0 ("Support quantized DSpark Markov heads", #50424) that touches no parser or chat-template code. **This skill's claims were probed at v0.27.0** (published 2026-08-10) and are deliberately stamped there rather than restamped to a tag that was not probed. The `v0.27.1` **container images** were pushed 10:24-10:42Z, before the release (PyPI still served 0.27.0 — not the delivery vehicle here). Probe: `gh api repos/vllm-project/vllm/releases` + PyPI JSON API. |

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

## 2026-08-11 freshen — registry re-probe at v0.27.0

**43 -> 45 CLI names.** Two additions, no removals: `kimi_k3` (`KimiK3ToolParser`,
legacy `ToolParser` shape, XTML `<|open|>tools<|sep|>` channels) and `inkling`
(`InklingEngineToolParser`, engine path).

**The `*_engine_*` filename convention is not the marker of the engine path —
and never was.** The 2026-07-21 pass listed "7 names / 5 shim files" by matching
filenames. Diffing by *import* instead (`grep -l "registered_adapters import"`)
shows **13 CLI names across 10 files at v0.27.0**, and **11 names were already on
it at v0.25.1** — `glm45`/`glm47` (`glm47_moe_tool_parser.py`), `kimi_k2`
(`kimi_k2_tool_parser.py`) and `minimax_m2` (`minimax_m2_tool_parser.py`) carry
ordinary filenames while being 8-20-line adapter subclasses. That undercount was
a method error, not upstream drift; the parser-index rows for those three said
"read this file" and the file has almost nothing in it.

Genuinely new to the engine path at v0.27.0: **`mistral`** (#48947) and
**`inkling`**.

Full v0.27.0 engine-path set:

| File | CLI name(s) | Logic |
|---|---|---|
| `qwen3_engine_tool_parser.py` | `qwen3_coder`, `qwen3_xml`, `mimo` | `vllm/parser/qwen3.py` |
| `gemma4_engine_tool_parser.py` | `gemma4` | `vllm/parser/gemma4.py` |
| `deepseekv4_engine_tool_parser.py` | `deepseek_v4` | `vllm/parser/deepseek_v4.py` |
| `deepseekv32_engine_tool_parser.py` | `deepseek_v32` | `vllm/parser/deepseek_v32.py` |
| `seed_oss_engine_tool_parser.py` | `seed_oss` | `vllm/parser/seed_oss.py` |
| `glm47_moe_tool_parser.py` | `glm45`, `glm47` | `vllm/parser/glm47_moe.py` |
| `kimi_k2_tool_parser.py` | `kimi_k2` | `vllm/parser/kimi_k2.py` |
| `minimax_m2_tool_parser.py` | `minimax_m2` | `vllm/parser/minimax_m2.py` |
| `mistral_tool_parser.py` | `mistral` | `vllm/parser/mistral.py` — new at v0.27.0 |
| `inkling_tool_parser.py` | `inkling` | `vllm/parser/inkling.py` — new at v0.27.0 |

**Corrections to prior claims:**

1. `glm45` and `glm47` were two rows in `parser-index.md` with `glm47`
   "subclassing" `glm45` from `glm4_moe_tool_parser.py`. **That file does not
   exist**; both names resolve to one 11-line `Glm47MoeModelToolParser`.
2. SKILL.md said the `prev_tool_call_arr = [{"arguments": {}}]` plant is carried
   by "Mistral and all pythonic-family parsers". **Mistral has never carried it**
   — it populates the array properly, at v0.25.1 and v0.27.0 alike. Actual
   carriers (verified `git grep` at v0.27.0): `pythonic`, `llama4_pythonic`,
   `olmo3`, `lfm2`, `minicpm5xml`.
3. Cited-but-nonexistent files corrected in `parser-index.md`:
   `deepseek_v4_tool_parser.py`, `cohere_command3_tool_parser.py`,
   `cohere_command4_tool_parser.py`, `gemma4_tool_parser.py`,
   `openai_tool_parser.py`, `seed_oss_tool_parser.py`, `glm4_moe_tool_parser.py`,
   and `qwen3xml_tool_parser.py` (cited in SKILL.md as a custom-parser starting
   point; replaced with `step3p5_tool_parser.py`, which does use expat directly).
4. Shipped tool templates: **26** at both v0.25.1 and v0.27.0 (unchanged). SKILL.md
   cited `tool_chat_template_deepseek_v3.jinja` (real name has no underscore:
   `_deepseekv3.jinja`) and `tool_chat_template_minicpm5.jinja` (**never
   existed** — `git log --all` on that path returns nothing). Both corrected.

Probes: `git ls-tree --name-only v0.27.0 vllm/tool_parsers/`;
`git show v0.27.0:vllm/tool_parsers/__init__.py`;
`git grep -ln "registered_adapters import" v0.27.0 -- vllm/tool_parsers/`;
`git grep -n 'prev_tool_call_arr = \[{"arguments"' v0.27.0 -- vllm/`;
`gh pr view {48947,45560,50403} -R vllm-project/vllm`.
