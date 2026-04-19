# Parser index (one line each + what to grep)

Each entry: `CLI name` → `vllm/tool_parsers/<file>.py` → one non-obvious fact that justifies a skim-read. For anything else, **read the file**.

## JSON-in-sentinels family

| CLI name | File | Non-obvious fact |
|---|---|---|
| `hermes` | `hermes_tool_parser.py` | `adjust_request` sets `skip_special_tokens=False`. Regex has two groups (complete/unclosed). |
| `longcat` | `longcat_tool_parser.py` | Subclasses `hermes`, just renames the tag. |
| `mistral` | `mistral_tool_parser.py` | Dual state machine: pre-v11 uses `ijson.parse_coro`; v≥11 detects via tokenizer version. Contains HACK `prev_tool_call_arr = [{"arguments": {}}]`. |
| `llama3_json` / `llama4_json` | `llama_tool_parser.py` | Accepts both `arguments` and `parameters` keys. Multi-call separator is `"; "`. |
| `phi4_mini_json` | `phi4mini_tool_parser.py` | `extract_tool_calls_streaming` returns `None` unconditionally — non-streaming only. Sentinel is literal string `functools`. |
| `granite` | `granite_tool_parser.py` | 3.0 uses special token `<\|tool_call\|>`; 3.1 uses string `<tool_call>`. Uses `partial_json_parser`. |
| `granite-20b-fc` | `granite_20b_fc_tool_parser.py` | Back-to-back `<function_call>` tags with no closer. |
| `granite4` | `granite4_tool_parser.py` | `regex` library with `partial=True` — not `re`. |
| `jamba` | `jamba_tool_parser.py` | Hard-fails at init if `<tool_calls>` / `</tool_calls>` not in vocab. |
| `deepseek_v3` / `_v31` / `_v32` | `deepseekv3_tool_parser.py` etc. | Sentinels contain U+FF5C `｜` + U+2581 `▁`. NOT ASCII `\|` or `_`. V3 has \`\`\`json fence, V3.1 doesn't, V3.2 uses DSML tokens. |
| `glm45` | `glm4_moe_tool_parser.py` | XML inside tool_call, not JSON. Needs `tools` arg for type coercion. Bypasses guided-JSON in `adjust_request`. |
| `glm47` | `glm47_moe_tool_parser.py` | Subclasses `glm45`; allows zero-arg calls, no-newline-after-name. |
| `internlm` | `internlm2_tool_parser.py` | **No parallel calls** — second call returns empty delta. |
| `ernie45` | `ernie45_tool_parser.py` | Buffers until `</tool_call>` — not true per-arg streaming. |
| `seed_oss` | `seed_oss_tool_parser.py` | Gated on `</seed:think>` having been emitted. XML inner grammar. |
| `hunyuan_a13b` | `hunyuan_a13b_tool_parser.py` | Regex-only, ONE level of nested JSON (TODO at line ~61). |

## Pythonic / XML / custom-grammar family

| CLI name | File | Non-obvious fact |
|---|---|---|
| `pythonic` | `pythonic_tool_parser.py` | AST-based. O(n²) streaming (re-parses on every delta). Apostrophe bug in `compute_tool_delta` `'`→`"` substitution. |
| `llama4_pythonic` | `llama4_pythonic_tool_parser.py` | Same as pythonic + optional `<\|python_start\|>…<\|python_end\|>` wrapper. |
| `olmo3` | `olmo3_tool_parser.py` | `<function_calls>\nfn(...)\n</function_calls>` XML-wrapped pythonic. |
| `qwen3_coder` (`mimo`) | `qwen3coder_tool_parser.py` | `<function=name><parameter=k>` grammar. Hand-rolled state machine. **Historically did not stream args** (issue #30439). |
| `qwen3_xml` (`mimo`) | `qwen3xml_tool_parser.py` | expat-based `StreamingXMLToolCallParser` — cleanest streaming in the tree. |
| `step3` | `step3_tool_parser.py` | Cursor-based state machine. Full-width `｜` tokens. No object/array coercion. |
| `step3p5` | `step3p5_tool_parser.py` | Reuses `qwen3_xml` expat engine. |
| `kimi_k2` | `kimi_k2_tool_parser.py` | Tool-call id in stream as `functions.name:0`. Section overflow guard (1024/8192). |
| `minimax` | `minimax_tool_parser.py` | Newline-separated JSON objects inside `<tool_calls>` — **NOT array**. |
| `minimax_m2` | `minimax_m2_tool_parser.py` | `<minimax:tool_call><invoke>` XML. Interleaved thinking. Schema-priority coercion. |
| `xlam` | `xlam_tool_parser.py` | Multi-format accepted (array / `[TOOL_CALLS]` / `<tool_call>` / post-`</think>`). JSON-in-JSON double-wrap footgun. |
| `gemma4` | `gemma4_tool_parser.py` | Bare keys + `<\|"\|>` string delim — NOT JSON. Accumulate-then-reparse-then-diff. |
| `functiongemma` | `functiongemma_tool_parser.py` | Per-value `json.loads` fallback. Multi-token special absorbed via `buffered_delta_text`. |
| `gigachat3` | `gigachat3_tool_parser.py` | Russian model; `<\|function_call\|>` / `<\|role_sep\|>`. |
| `openai` | `openai_tool_parser.py` | **Harmony format** — operates on token IDs via `harmony_utils.parse_output_into_messages`. Streaming raises `NotImplementedError`; handled in `chat_completion/serving.py`. |

## When to use this index

- Looking up parser → file path to `Read`.
- Confirming whether `--reasoning-parser` pairing is needed (see the `seed_oss`, `minimax_m2`, `ernie45`, `hunyuan_a13b` entries).
- Deciding which parser to copy as a plugin starting point.

**When NOT to use this index**: as a substitute for reading the file. Facts in the "non-obvious fact" column were accurate at skill creation; they may have been fixed, renamed, or the file may have been split. Verify.
