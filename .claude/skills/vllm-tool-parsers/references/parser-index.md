# Parser index (one line each + what to grep)

Each entry: `CLI name` → `vllm/tool_parsers/<file>.py` → one non-obvious fact that justifies a skim-read. For anything else, **read the file**.

Rows written `a.py → vllm/parser/b.py` are on the unified engine: `a.py` is a
stub of a few lines and the real logic is in `b.py`. The filename does not tell
you which — `grep -l "registered_adapters import" vllm/tool_parsers/*.py` does.
Verified at v0.27.0.

## JSON-in-sentinels family

| CLI name | File | Non-obvious fact |
|---|---|---|
| `hermes` | `hermes_tool_parser.py` | `adjust_request` sets `skip_special_tokens=False`. Regex has two groups (complete/unclosed). |
| `longcat` | `longcat_tool_parser.py` | Subclasses `hermes`, just renames the tag. |
| `mistral` | `mistral_tool_parser.py` → `vllm/parser/mistral.py` | **Moved onto the unified engine at v0.27.0** ([#48947](https://github.com/vllm-project/vllm/pull/48947)); the `tool_parsers/` file is a ~50-line `MistralParserToolAdapter` subclass. One `MistralParser` now serves *both* `--tool-call-parser mistral` and `--reasoning-parser mistral` and covers pre-v11 (no reasoning) and v11+ (new tool format, optional reasoning). CLI names unchanged. `supports_required_and_named = False` — required/named are routed through the parser's own extraction because Mistral emits `[TOOL_CALLS]name[ARGS]{…}`, not a JSON array. Empty tool-call names are valid on v11+. `adjust_request` bypasses the generic tool_choice→structured-outputs conversion and enforces choice via the mistral-common grammar `mode`. |
| `llama3_json` / `llama4_json` | `llama_tool_parser.py` | Accepts both `arguments` and `parameters` keys. Multi-call separator is `"; "`. |
| `phi4_mini_json` | `phi4mini_tool_parser.py` | `extract_tool_calls_streaming` returns `None` unconditionally — non-streaming only. Sentinel is literal string `functools`. |
| `granite` | `granite_tool_parser.py` | 3.0 uses special token `<\|tool_call\|>`; 3.1 uses string `<tool_call>`. Uses `partial_json_parser`. |
| `granite-20b-fc` | `granite_20b_fc_tool_parser.py` | Back-to-back `<function_call>` tags with no closer. |
| `granite4` | `granite4_tool_parser.py` | `regex` library with `partial=True` — not `re`. |
| `jamba` | `jamba_tool_parser.py` | Hard-fails at init if `<tool_calls>` / `</tool_calls>` not in vocab. |
| `deepseek_v3` / `_v31` | `deepseekv3_tool_parser.py`, `deepseekv31_tool_parser.py` | Sentinels contain U+FF5C `｜` + U+2581 `▁`. NOT ASCII `\|` or `_`. V3 has \`\`\`json fence, V3.1 doesn't. |
| `deepseek_v32` | `deepseekv32_engine_tool_parser.py` → `vllm/parser/deepseek_v32.py` | Uses DSML tokens. Engine path — the `tool_parsers/` file is a stub. |
| `glm45` / `glm47` | `glm47_moe_tool_parser.py` → `vllm/parser/glm47_moe.py` | **Both names are one class** (`Glm47MoeModelToolParser`, an 11-line `Glm47MoeParserToolAdapter` subclass; `structural_tag_model = "glm_4_7"`, `supports_required_and_named = False`). `glm4_moe_tool_parser.py` no longer exists. XML inside `tool_call`, not JSON; needs `tools` for type coercion. |
| `internlm` | `internlm2_tool_parser.py` | **No parallel calls** — second call returns empty delta. |
| `ernie45` | `ernie45_tool_parser.py` | Buffers until `</tool_call>` — not true per-arg streaming. |
| `seed_oss` | `seed_oss_engine_tool_parser.py` → `vllm/parser/seed_oss.py` | Gated on `</seed:think>` having been emitted. XML inner grammar. |
| `hunyuan_a13b` | `hunyuan_a13b_tool_parser.py` | Regex-only, ONE level of nested JSON (TODO at line ~61). |
| `hy_v3` | `hy_v3_tool_parser.py` | Hunyuan V3 parser (newer than `hunyuan_a13b`). Read the file — sentinel grammar + state-machine details live there. |
| `deepseek_v4` | `deepseekv4_engine_tool_parser.py` → `vllm/parser/deepseek_v4.py` | DeepSeek-V4 successor to v3/v31/v32. Same full-width sentinels: `<｜tool▁calls▁begin｜>` (U+FF5C `｜` + U+2581 `▁`), NOT ASCII. |
| `cohere_command3` | `cohere_command_tool_parser.py` (shared) | Command-A / Command-R7B. JSON array between `<\|START_ACTION\|>` / `<\|END_ACTION\|>`; keys are `tool_name` + `parameters` (not `name`/`arguments`). |
| `cohere_command4` | `cohere_command_tool_parser.py` (shared) | Command-A-Reasoning / Command-A-Vision. Same `<\|START_ACTION\|>` grammar as `cohere_command3`. |
| `apertus` | `apertus_tool_parser.py` | JSON array `[{"name","arguments"}]` wrapped in `<tool_calls>` / `</tool_calls>`. Has streaming. |
| `lfm2` | `lfm2_tool_parser.py` | Liquid LFM2. Pythonic `[func(arg=val)]` inside `<\|tool_call_start\|>` / `<\|tool_call_end\|>`. **Streaming not supported** — full responses only. |
| `minicpm5` | `minicpm5xml_tool_parser.py` | XML `<function>` / `<parameter>` tags inside `<\|tool_call_start\|>` / `<\|tool_call_end\|>`. **No `tool_chat_template_minicpm5.jinja` ships** — use the HF default. Carries the `prev_tool_call_arr = [{"arguments": {}}]` plant in three places. |
| `kimi_k3` | `kimi_k3_tool_parser.py` | **New at v0.27.0.** XTML channel format, legacy `ToolParser` shape (not the engine path): `<\|open\|>tools<\|sep\|>` wrapping `<\|open\|>call tool="x" index="1"<\|sep\|>` and per-arg `<\|open\|>argument key="k" type="string"<\|sep\|>`. `type="string"` bodies are RAW (no unescaping); other types are JSON-decoded. Attribute values are `&amp;`/`&quot;`-escaped. Documented limitation: a string value literally containing `<\|close\|>argument<\|sep\|>` is indistinguishable from a real closer. |
| `inkling` | `inkling_tool_parser.py` → `vllm/parser/inkling.py` | **New at v0.27.0.** Self-describing typed blocks, each marker a dedicated special token: `<\|message_model\|>` then one of `<\|content_text\|>` / `<\|content_thinking\|>` / `<\|content_invoke_tool_json\|>` / `<\|content_invoke_tool_text\|>` / `<\|content_tool_error\|>`, closed by `<\|end_message\|>` (or standalone `<\|content_model_end_sampling\|>`). Blocks may repeat in any order. Tool payload is one JSON object whose `name` is lifted out of `args`. [#50403](https://github.com/vllm-project/vllm/pull/50403) made both the Python and Rust parsers buffer **bare text emitted straight after `<\|message_model\|>` with no content-kind marker** and emit it as content at the end marker — while still discarding it when a typed marker proves it was header metadata (e.g. a tool name). `structural_tag_model = None`, `supports_required_and_named = False` — no Inkling grammar is wired up yet, so named/required fall back to auto parsing. |
| `poolside_v1` | `poolside_v1_tool_parser.py` | GLM-4-style grammar (docstring says "GLM-4"): `<tool_call>` with `<arg_key>`/`<arg_value>` tags, NOT JSON-in-tags. Streams string values incrementally (fix for #32829). |

## Pythonic / XML / custom-grammar family

| CLI name | File | Non-obvious fact |
|---|---|---|
| `pythonic` | `pythonic_tool_parser.py` | AST-based. O(n²) streaming (re-parses on every delta). Apostrophe bug in `compute_tool_delta` `'`→`"` substitution. |
| `llama4_pythonic` | `llama4_pythonic_tool_parser.py` | Same as pythonic + optional `<\|python_start\|>…<\|python_end\|>` wrapper. |
| `olmo3` | `olmo3_tool_parser.py` | `<function_calls>\nfn(...)\n</function_calls>` XML-wrapped pythonic. |
| `qwen3_coder` / `qwen3_xml` / `mimo` | `qwen3_engine_tool_parser.py` → `vllm/parser/qwen3.py` | **All three names now resolve to one class**, `Qwen3EngineToolParser` (a thin subclass of `Qwen3ParserToolAdapter` adding `structural_tag_model = "qwen_3_coder"`). The separate `qwen3coder_tool_parser.py` and `qwen3xml_tool_parser.py` files are **deleted** at v0.25.1. Consequence: the old "prefer `qwen3_xml`, its expat streaming is cleaner than `qwen3_coder`'s hand-rolled state machine" advice **no longer has a basis** — same code either way. The #30439 arg-streaming bug (closed 2026-04-10) is likewise moot on the unified implementation. |
| `step3` | `step3_tool_parser.py` | Cursor-based state machine. Full-width `｜` tokens. No object/array coercion. |
| `step3p5` | `step3p5_tool_parser.py` | Uses Python's `xml.parsers.expat.ParserCreate` **directly**. (Previously described here as "reuses the `qwen3_xml` expat engine" — that file no longer exists, and this parser has its own expat usage.) |
| `kimi_k2` | `kimi_k2_tool_parser.py` → `vllm/parser/kimi_k2.py` | On the unified engine path despite the ordinary filename — 20 lines subclassing `KimiK2ParserToolAdapter` (`structural_tag_model = "kimi"`) plus an `adjust_request` override. Tool-call id in stream as `functions.name:0`. |
| ~~`minimax`~~ | *(removed)* | **The bare `minimax` name and `minimax_tool_parser.py` are gone at v0.25.1.** `--tool-call-parser minimax` will fail to resolve. It served MiniMax-M1 with newline-separated JSON objects inside `<tool_calls>` (not an array). Migrate to the model-specific name. |
| `minimax_m2` | `minimax_m2_tool_parser.py` → `vllm/parser/minimax_m2.py` | On the unified engine path despite the ordinary filename — 8 lines subclassing `MinimaxM2ParserToolAdapter` (`structural_tag_model = "minimax"`). `<minimax:tool_call><invoke>` XML. Interleaved thinking. |
| `minimax_m3` | `minimax_m3_tool_parser.py` | MiniMax-M3 — **new at v0.25.1**, own file/class. |
| `xlam` | `xlam_tool_parser.py` | Multi-format accepted (array / `[TOOL_CALLS]` / `<tool_call>` / post-`</think>`). JSON-in-JSON double-wrap footgun. |
| `gemma4` | `gemma4_engine_tool_parser.py` → `vllm/parser/gemma4.py` (helpers in `gemma4_utils.py`) | Bare keys + `<\|"\|>` string delim — NOT JSON. Accumulate-then-reparse-then-diff. |
| `functiongemma` | `functiongemma_tool_parser.py` | Per-value `json.loads` fallback. Multi-token special absorbed via `buffered_delta_text`. |
| `gigachat3` | `gigachat3_tool_parser.py` | Russian model; `<\|function_call\|>` / `<\|role_sep\|>`. |
| `openai` | `gptoss_tool_parser.py` | **Harmony format** — operates on token IDs via `harmony_utils.parse_output_into_messages`. Streaming raises `NotImplementedError`; handled in `chat_completion/serving.py`. At v0.27.0 ([#45560](https://github.com/vllm-project/vllm/pull/45560)) `HarmonyParser.adjust_request` rewrites `json_object`/`json_schema` into a Harmony-aware structural tag that constrains the whole generation, not just the final channel. |

## When to use this index

- Looking up parser → file path to `Read`.
- Confirming whether `--reasoning-parser` pairing is needed (see the `seed_oss`, `minimax_m2`, `ernie45`, `hunyuan_a13b` entries).
- Deciding which parser to copy as a plugin starting point.

**When NOT to use this index**: as a substitute for reading the file. Facts in the "non-obvious fact" column were accurate at skill creation; they may have been fixed, renamed, or the file may have been split. Verify.
