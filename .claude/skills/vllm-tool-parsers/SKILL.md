---
name: vllm-tool-parsers
description: |-
  vLLM tool-calling operator reference — picking `--tool-call-parser` per model family, writing custom parsers via `--tool-parser-plugin`, navigating vLLM source + GitHub tracker to debug any specific tool-call question. Pointer map, not source paraphrase. All 40+ built-in parsers (JSON-sentinel, pythonic, XML, harmony grammars), CLI contract, `prev_tool_call_arr`/`streamed_args_for_tool` flush invariants, diagnostic playbook (isolate template-vs-parser via raw `/v1/completions` + unicodedata codepoint decode).
when_to_use: |-
  Trigger on any tool-calling/function-calling question against a vLLM deployment — `--tool-call-parser`/`--enable-auto-tool-choice` flag issues, "tool call not firing", missing `}` at stream end, `finish_reason` stuck on `stop`, any `<tool_call>`/`<|tool_calls_begin|>`/`[TOOL_CALLS]`/`<|python_tag|>` sentinel in raw content, Claude Code/LangChain/OpenAI-SDK tool failures, pythonic-vs-JSON for Llama, Mistral v11, DeepSeek `｜` (U+FF5C), GLM XML, Qwen3 XML vs Qwen3-Coder, Hermes `skip_special_tokens=False`. Applies even without naming the parser — "my Qwen isn't calling tools" is this skill. Also implicit — "MCP tools not firing", "audit tool parser", "deploy-memo tool calling".
---

# vLLM Tool Parsers — Navigation Map

This skill points to the right source file, template, or GH issue. The source code is authoritative — read it. **Do not paraphrase from this skill when the actual file is available.**

## Where things live

Assume a local [vllm-project/vllm](https://github.com/vllm-project/vllm) checkout is accessible. Every reference below is relative to that repo root.

| Target | Read |
|---|---|
| All tool parsers | `vllm/tool_parsers/` (one file per parser). Not `vllm/entrypoints/openai/tool_parsers/` — removed at v0.14.0; imports from it fail |
| Parser base class + `ToolParserManager` | `vllm/tool_parsers/abstract_tool_parser.py` |
| Shared helpers (`partial_json_loads`, `find_common_prefix`, `make_valid_python`, `partial_tag_overlap`, `compute_tool_delta`, `handle_single_tool`) | `vllm/tool_parsers/utils.py` |
| Built-in parser registry | `vllm/tool_parsers/__init__.py` — `_TOOL_PARSERS_TO_REGISTER` maps CLI name → module → class |
| **Unified parser engine (new)** | `vllm/parser/` — one class per model (`qwen3.py`, `gemma4.py`, `deepseek_v4.py`, `deepseek_v32.py`, `seed_oss.py`, …), `abstract_parser.py`, and `engine/` (`parser_engine.py`, `streaming_parser_engine.py`, `incremental_lexer.py`, `token_id_scanner.py`) |
| **Adapter construction** | `vllm/parser/engine/adapters.py` defines `make_adapters(XParser)` → `(XParserReasoningAdapter, XParserToolAdapter)`; most pairs are built in `vllm/parser/engine/registered_adapters.py`, a few in the model's own `vllm/parser/<model>.py` (`ling3`). The tool side is then subclassed in `vllm/tool_parsers/*.py` to attach `structural_tag_model` |
| CLI flag definitions | `vllm/entrypoints/launchers/cli_args.py` — grep `tool_call_parser`, `enable_auto_tool_choice`, `tool_parser_plugin` |
| Non-streaming serving invocation | `vllm/entrypoints/openai/chat_completion/serving.py` — grep `parser.parse(`; `DelegatingParser` in `vllm/parser/abstract_parser.py` calls the tool parser's `extract_tool_calls` |
| Streaming serving loop | same file — grep `parse_delta`, `tools_streamed` |
| Tail flush of unstreamed args | `vllm/parser/abstract_parser.py` — grep `_append_unstreamed_tool_args`; reads `ToolParser.get_remaining_unstreamed_args()` in `abstract_tool_parser.py` |
| Plugin import wiring | `vllm/entrypoints/launchers/api_server/entry.py` and `vllm/entrypoints/launchers/launcher.py` — grep `import_tool_parser` (`vllm/entrypoints/openai/api_server.py` is a deprecated re-export shim) |
| Responses API tool handling | `vllm/entrypoints/openai/responses/serving.py` + `vllm/entrypoints/openai/responses/utils.py` |
| Per-parser Jinja chat templates | `examples/tool_chat_template_<family>.jinja` |
| Per-parser tests (executable spec) | `tests/tool_parsers/test_<name>_tool_parser.py` + `tests/tool_parsers/common_tests.py` |
| User-facing docs | `docs/features/tool_calling.md` |

**If the operator's question is "what does parser X do" — read `vllm/tool_parsers/X_tool_parser.py`.** Don't rely on this skill's paraphrase.

**Except for the 15 names on the unified-parser path**, where that file is a
stub of a few lines and the logic lives in `vllm/parser/<model>.py`:

| CLI name(s) | Registry class | Real implementation |
|---|---|---|
| `qwen3_coder`, `qwen3_xml`, `mimo` | `Qwen3EngineToolParser` | `vllm/parser/qwen3.py` |
| `gemma4` | `Gemma4EngineToolParser` | `vllm/parser/gemma4.py` |
| `deepseek_v4` | `DeepSeekV4EngineToolParser` | `vllm/parser/deepseek_v4.py` |
| `deepseek_v32` | `DeepSeekV32EngineToolParser` | `vllm/parser/deepseek_v32.py` |
| `seed_oss` | `SeedOssEngineToolParser` | `vllm/parser/seed_oss.py` |
| `glm45`, `glm47` | `Glm47MoeModelToolParser` | `vllm/parser/glm47_moe.py` |
| `kimi_k2` | `KimiK2ToolParser` | `vllm/parser/kimi_k2.py` |
| `minimax_m2` | `MinimaxM2ToolParser` | `vllm/parser/minimax_m2.py` |
| `mistral` | `MistralToolParser` | `vllm/parser/mistral.py` (v0.27.0+; a standalone parser before) |
| `inkling` | `InklingEngineToolParser` | `vllm/parser/inkling.py` (v0.27.0+) |
| `ling3` | `Ling3ToolParser` | `vllm/parser/ling3.py` (v0.29.0+) |
| `deepseek_v41` | `DeepSeekV41EngineToolParser` | `vllm/parser/deepseek_v41.py` (v0.30.0+). Strict (`strict=true`) tool-call parameter schemas are only grammar-constrained if the installed `xgrammar` exposes `builtin_structural_tag.get_deepseek_v4_1_structural_tag`; otherwise the fallback builder constrains tool names/DSML syntax only, not parameter schemas (`vllm/tool_parsers/structural_tag_registry.py`) |

**Four more names are NOT on this path** — `dots` (`DotsToolParser`), `hy_v4` (`HYV4ToolParser`), `muse_glimmer` (`MuseGlimmerToolParser`) and `k2_horizon` (`K2HorizonToolParser`). None imports a `*ParserToolAdapter`, so each is an ordinary standalone tool parser with no paired reasoning adapter. Registry total: **51 names at v0.30.0**.

**`_engine_` in the filename is not the marker.** `glm47_moe_tool_parser.py`,
`kimi_k2_tool_parser.py`, `minimax_m2_tool_parser.py` and `mistral_tool_parser.py`
have ordinary names and are still stubs. The test is whether the file imports
an adapter: `grep -l "ParserToolAdapter" vllm/tool_parsers/*.py` (12 files at v0.30.0;
`ling3_tool_parser.py` imports its adapter from `vllm.parser.ling3`, so grepping
`registered_adapters` misses it).
**Exception**: `cohere_command_tool_parser.py` (`cohere_command3`/`cohere_command4`)
is a stub too but imports no adapter — it's composed by
name-check in `vllm/parser/parser_manager.py` instead, so this grep won't find
it. Its parsing lives in `vllm/parser/cohere_command.py` via the external
`cohere_melody` package — not a vLLM runtime dependency: `pip
install cohere-melody` into the image yourself (CI pins 0.14.0), or the parser
raises `ImportError` at load. (`kimi_k3` goes through the same name-check but its
`tool_parsers/` file is the real implementation, not a stub.)

This is the same refactor described in `vllm-reasoning-parsers` — a single
per-model parser now backs **both** the tool and reasoning adapters. Consequence: a grammar
change to `vllm/parser/qwen3.py` moves tool *and* reasoning behaviour at once —
they are no longer independent surfaces for those models.

## The CLI contract

Two flags, both required together for auto tool choice:

```bash
vllm serve <model> --enable-auto-tool-choice --tool-call-parser <name> [--chat-template <path>]
```

- `--enable-auto-tool-choice` alone → `TypeError: --enable-auto-tool-choice requires --tool-call-parser` (see `cli_args.py`).
- `--tool-call-parser` alone → legal. Parser still runs for `tool_choice="required"` and named, and on Responses API.
- **No `auto` sentinel.** Name a concrete parser.
- `--tool-parser-plugin <path.py>` → third-party file that calls `@ToolParserManager.register_module("name")`. **v0.30.0+**: the value can also be a dotted module name importable from site-packages (e.g. an installed pip package) — `import_plugin()` tries `importlib.import_module(value)` first, falling back to file-path import only on `ModuleNotFoundError` (`vllm/utils/import_utils.py`). Same for `--reasoning-parser-plugin`.
- `--reasoning-parser` is independent but several tool parsers assume a `</think>` has closed — match them (see "Reasoning pairing" below).
- Chat template often matters. Each parser has a reference Jinja at `examples/tool_chat_template_<family>.jinja`. Wrong template → model never emits the sentinels the parser expects.

## Parser → model family index

Use this to pick the CLI name. **Then read the parser file and the matching Jinja for details** — the wrapping tokens, streaming strategy, and quirks live there, not here.

| `--tool-call-parser` | Model families | Reference template |
|---|---|---|
| `hermes` | Hermes-2/3, Qwen2.5-Instruct, Qwen3-Instruct (text), QwQ | `tool_chat_template_hermes.jinja` |
| `longcat` | LongCat-Flash-Chat | (inherits hermes) |
| `mistral` | Mistral-Instruct (all), Mistral-Large-2506+ (v≥11 format auto-detected) | `tool_chat_template_mistral.jinja` (also `_mistral3.jinja`, `_mistral_parallel.jinja`) |
| `llama3_json` / `llama4_json` | Llama 3.1/3.2/3.3/4 (JSON flavor) | `tool_chat_template_llama3.1_json.jinja`, `_llama3.2_json.jinja`, `_llama4_json.jinja` |
| `pythonic` | Llama-3.2-{1B,3B}, ToolACE-8B, Gemma-3 | `tool_chat_template_llama3.2_pythonic.jinja`, `tool_chat_template_toolace.jinja`, `tool_chat_template_gemma3_pythonic.jinja` |
| `llama4_pythonic` | Llama-4 Scout/Maverick | `tool_chat_template_llama4_pythonic.jinja` |
| `olmo3` | Olmo-3-7B/32B | (HF default) |
| `qwen3_coder` / `qwen3_xml` / `mimo` | Qwen3-Coder-480B/30B, Qwen3-XML family | `tool_chat_template_qwen3coder.jinja` — **all three names are one class** (`Qwen3EngineToolParser`) since v0.25.1; before that `qwen3coder_tool_parser.py` and `qwen3xml_tool_parser.py` were separate implementations. **Before v0.25.1, `qwen3_coder` streams all arguments in one final delta** (#30439, closed unfixed — not a flag or template problem): upgrade to ≥ v0.25.1 (unified parser); interim, use non-streaming |
| `deepseek_v3` / `deepseek_v31` / `deepseek_v32` / `deepseek_v4` | DeepSeek-V3/R1, V3.1, V3.2, V4 | `tool_chat_template_deepseekv3.jinja`, `_deepseekv31.jinja`, `_deepseekr1.jinja` |
| `deepseek_v41` | DeepSeek-V4.1-Flash (v0.30.0+; DSML, unified engine) | (HF default) |
| `cohere_command3` / `cohere_command4` | Command-A, Command-R7B (3); Command-A-Reasoning/Vision (4) | `<\|START_ACTION\|>` grammar (HF default) |
| `apertus` | Apertus | `tool_chat_template_apertus.jinja` — vLLM's docs say use it over the HF one (fixes OpenAI-compatibility issues) |
| `lfm2` | LFM2 | (HF default) |
| `minicpm5` | MiniCPM-5 | (HF default — no `tool_chat_template_minicpm5.jinja` ships) |
| `poolside_v1` | Poolside (GLM-4-style grammar) | (HF default) |
| `hy_v3` | Hunyuan V3 (newer than `hunyuan_a13b`) | (HF default) |
| `glm45` / `glm47` | GLM-4.5/4.6, GLM-4.7 | `tool_chat_template_glm4.jinja` |
| `ling3` | Ling 3.0 Flash (v0.29.0+; GLM-4.7 grammar: `Ling3Parser` subclasses `Glm47MoeParser`) | (HF default) |
| `granite` / `granite-20b-fc` / `granite4` | Granite-3.0/3.1, Granite-20B-FC, Granite-4.0 | `tool_chat_template_granite.jinja`, `_granite_20b_fc.jinja` |
| `phi4_mini_json` | Phi-4-mini | `tool_chat_template_phi4_mini.jinja` |
| `jamba` | Jamba-1.5 | (HF default, sentinel must be in vocab) |
| `internlm` | InternLM-2.5 | `tool_chat_template_internlm2_tool.jinja` |
| `kimi_k2` | Kimi-K2 Instruct / Thinking | (HF default) |
| `kimi_k3` | Kimi-K3 (XTML `<\|open\|>tools<\|sep\|>` channels) (v0.27.0+) | (HF default) |
| `inkling` | Inkling (v0.27.0+); typed `<\|content_text\|>`/`<\|content_thinking\|>`/`<\|content_invoke_tool_json\|>` blocks | (HF default) |
| `minimax_m2` / `minimax_m3` | MiniMax-M2 / M3 | **the bare `minimax` name was removed at v0.25.1** — `--tool-call-parser minimax` no longer resolves |
| `step3` / `step3p5` | Step-3 VL / Step-3.5-Flash | (HF default) |
| `dots` | Dots (v0.29.0+); XML `<dots_function_call>` blocks | (HF default) |
| `k2_horizon` | K2 Horizon (v0.30.0+) — `<ifm\|tool_calls>` / `<ifm\|tool_call>` wrappers, JSON or XML (`<ifm\|arg_key>`) bodies; `supports_required_and_named = False` | (HF default) |
| `hy_v4` | Hunyuan V4 / Hy4-preview (v0.29.0+); XML `<arg_key>` / `<arg_value>` pairs | (HF default — no bundled template; the `hunyuan_a13b` one is a different parser) |
| `muse_glimmer` | Muse Glimmer (v0.29.0+); `<\|eom\|>` / `<\|eot\|>` special tokens | `tool_chat_template_muse_glimmer.jinja` |
| `seed_oss` | Seed-OSS | (HF default) |
| `hunyuan_a13b` | Hunyuan-A13B | (HF default per vLLM docs; `tool_chat_template_hunyuan_a13b.jinja` also ships) |
| `ernie45` | ERNIE-4.5 thinking | (HF default) |
| `gemma4` / `functiongemma` | Gemma-4-IT / FunctionGemma-270m | `tool_chat_template_gemma4.jinja`, `_functiongemma.jinja` |
| `gigachat3` | GigaChat-3 | (HF default) |
| `xlam` | Salesforce xLAM Llama & Qwen | `tool_chat_template_xlam_llama.jinja`, `_xlam_qwen.jinja` |
| `openai` | gpt-oss-20b/120b (Harmony channels) | (no Jinja — built-in renderer) |

**gpt-oss/Harmony (v0.27.0+):** `json_object`/`json_schema`
`response_format` is now rewritten into a Harmony-aware `structural_tag` in
`HarmonyParser.adjust_request`, so constrained decoding governs the *whole*
generation instead of only the post-`<|channel|>final<|message|>` region. Without
builtin tools the grammar validates tool name + arguments; with builtin tools it
falls back to "some tool is called" only.

Don't trust this table to be complete — verify with:

```bash
grep -oE '^\s+"[a-z0-9_-]+": \(' vllm/tool_parsers/__init__.py | tr -d ' ":('   # CLI names only (51 at v0.30.0)
ls examples/tool_chat_template_*.jinja            # lists shipped templates
ls vllm/tool_parsers/*_tool_parser.py              # lists source files
```

## Framework contract (mental model)

Worth carrying as mental model, because it's spread across multiple files and easy to miss:

- `ToolParser` subclass implements `extract_tool_calls` (non-streaming, stateless) and `extract_tool_calls_streaming` (stateful, per-delta). See `vllm/tool_parsers/abstract_tool_parser.py`.
- Serving-layer invariants (guaranteed to the streaming method):
  - `current_text == previous_text + delta_text`
  - `current_token_ids == previous_token_ids + delta_token_ids`
  - Deltas may span multiple tokens.
- Four state fields the parser MUST maintain:
  - `prev_tool_call_arr: list[dict]` — at stream end `get_remaining_unstreamed_args()` takes the **last** entry's `"arguments"`, subtracts what `streamed_args_for_tool` already sent, and appends the rest to the final delta's last tool call — only if that final delta carries `tool_calls`.
  - `current_tool_id: int` — starts `-1`, increments per call.
  - `current_tool_name_sent: bool` — flip True once name flushed for current tool.
  - `streamed_args_for_tool: list[str]` — cumulative args already emitted per tool index. **Append on every flush**: if it is not a prefix of the full args, the tail is silently dropped; if it lags, the tail re-sends text already streamed.
- Streaming `finish_reason` is `tool_calls` iff at least one returned `DeltaMessage` carried `tool_calls` (serving's `tools_streamed[i]`) and the request did not name a tool. A parser that only buffers and never emits a `DeltaToolCall` ends on `stop`, whatever `prev_tool_call_arr` holds.
- Optional: `adjust_request(request)` — set `skip_special_tokens=False`, inject grammar, etc. `supports_required_and_named: bool = True` — flip False if the output shape breaks guided JSON.
- Return-value contract for streaming: `None` = "consumed, nothing to emit"; `DeltaMessage(content=...)` = pass-through; `DeltaMessage(tool_calls=[DeltaToolCall(...)])` = tool progress.

Align new parsers with the `parse_delta` shape (RFC #11522 and its merged follow-on PRs #39446, #39728, #38755) rather than copying older HACKs.

## Reasoning-parser pairing

Several tool parsers gate on a reasoning-end sentinel. Mismatched pair = tool parser sees reasoning text as content, misses sentinels, or emits from inside `<think>`. Table below is a pointer — verify by reading the tool-parser file for the `adjust_request`/`is_reasoning_end` interaction.

| Tool parser | Pair with | Why |
|---|---|---|
| `hermes` (Qwen3 thinking) | `qwen3` | Gates on `</think>` |
| `deepseek_v3` (R1) | `deepseek_r1` | Gates on `</think>` |
| `seed_oss` | `seed_oss` | Gates on `</seed:think>` |
| `hunyuan_a13b` | `hunyuan_a13b` | Excludes `<think>…</think>` region |
| `minimax_m2`, `minimax_m3` | same name | Interleaved thinking / exclusion zone |
| `kimi_k2` | `kimi_k2` | Implicit end via `<\|tool_calls_section_begin\|>` |
| `ernie45` | `ernie45` | Expects `</think>\n\n\n<tool_call>` |
| `mistral` (reasoning variants) | `mistral` | Tokenized reasoning section |

Sibling skill: `vllm-reasoning-parsers` — defer there for reasoning-side questions.

## Diagnostic playbook

When a user reports a broken tool call, work down this list. Each step names where to look.

1. **Both flags set?** Check serve command for `--enable-auto-tool-choice --tool-call-parser <name>`.
2. **Right parser for the model?** Cross-check with the table above AND with `vllm/tool_parsers/__init__.py` registry.
3. **Chat template matches?** Inspect the actual template bytes — don't trust the filename. See step 7. Parser and template are a pair: switching `--tool-call-parser` between flavours (`llama4_json` ↔ `llama4_pythonic`, JSON ↔ pythonic) without switching `--chat-template` makes the model emit a shape the parser never matches — calls arrive as plain content. A `--chat-template` value that cannot be opened fails startup (`looks like a file path, but it failed to be opened`) — unless it contains `{`, `}` or a newline, in which case vLLM uses the string itself as the template. A preflight gate checks the path exists.
4. **Reasoning parser paired?** If the model has `<think>` / `</seed:think>` / harmony channels, `--reasoning-parser` must match. Check `vllm/reasoning/` for the registry.
5. **Streaming vs non-streaming?** Grep the parser file: if `extract_tool_calls_streaming` returns `None` unconditionally or raises `NotImplementedError`, streaming isn't supported (e.g. `phi4_mini_json`, `openai`).
6. **`finish_reason` = `stop` when a call was expected?** The parser never returned a `DeltaMessage` with `tool_calls` during the stream (or the request named a tool, where `stop` is correct). Compare with `"stream": false` on the same prompt: tool calls there but not in the stream = a streaming-path bug in that parser.
7. **Raw model output vs what parser sees.** Bypass the parser: call `/v1/completions` (no tool parser) with the chat-rendered prompt — `tokenizer.apply_chat_template(messages, tools=tools, tokenize=False, add_generation_prompt=True)` with the deployed template. Keep `"skip_special_tokens": false`: the default `true` strips special-token sentinels (`<|tool_call|>`, `[TOOL_CALLS]`, …) from `text`, which looks exactly like "model never emitted them". Dump raw text and non-ASCII codepoints:
   ```bash
   curl -sS $VLLM/v1/completions -H 'content-type: application/json' \
     -d '{"model":"...","prompt":"...","max_tokens":200,"skip_special_tokens":false}' \
     | python3 -c "import sys,json,unicodedata; t=json.load(sys.stdin)['choices'][0]['text']; \
         print(repr(t)); [print(hex(ord(ch)), unicodedata.name(ch,'?'), repr(ch)) for ch in t[:2000] if ord(ch)>0x7E]"
   ```
   This distinguishes "model not emitting sentinels" (template/training problem) from "parser not matching sentinels" (parser bug).
8. **vLLM version vs known bugs.** See "Bug archaeology" below.
9. **Custom template?** Diff the deployed Jinja against `examples/tool_chat_template_<family>.jinja`. Character-level. Full-width vs ASCII Unicode gotchas bite here.

## Bug archaeology (don't trust static lists — search)

Tool-parser bugs churn quickly. Teach yourself the pattern:

```bash
# Open bugs affecting a specific parser
gh search issues --repo vllm-project/vllm "<parser-name> tool" --state open \
  --json title,url,state,updatedAt --limit 20

# Recently merged fix PRs
gh search prs --repo vllm-project/vllm "<parser-name>" --state merged \
  --json title,url,mergedAt --limit 20

# Streaming-specific
gh search issues --repo vllm-project/vllm "tool parser streaming <parser-name>" \
  --json title,url,state,updatedAt --limit 20

# Broad sweep if parser name unknown
gh search issues --repo vllm-project/vllm "extract_tool_calls_streaming" --limit 30
```

On finding a referenced issue/PR, read it directly (`gh issue view N --repo vllm-project/vllm --comments`). Never paraphrase from a cached memory — the fix may have landed since.

## In-tree HACKs to recognize

Helpful to know what to look for when reading a parser. Grep the codebase for these:

```bash
grep -rn "HACK" vllm/tool_parsers/
grep -rn "TODO" vllm/tool_parsers/
grep -rn "prev_tool_call_arr = \[{\"arguments\": {}}\]" vllm/tool_parsers/
```

The `prev_tool_call_arr = [{"arguments": {}}]` plant is the old "force finish_reason=tool_calls" workaround; `finish_reason` no longer reads that field, and where it once forced `tool_calls` it produced a call with empty arguments — hiding the failed parse instead of fixing it. Do not copy it into a new parser. At v0.30.0 exactly five parsers carry it: `pythonic`, `llama4_pythonic`, `olmo3`, `lfm2`, `minicpm5xml` — the pythonic family plus the two that reuse its flush shape. (`mistral` does **not**; it populates `prev_tool_call_arr` properly.) When writing a new parser, prefer the `parse_delta` shape (RFC #11522).

## Writing a custom parser

Copy the existing parser closest in format. Don't reinvent.

```bash
# Match the target shape to an existing parser
grep -lE "<your_sentinel>" vllm/tool_parsers/   # sometimes the sentinel itself is in the code
ls vllm/tool_parsers/                            # scan names by format
```

For the skeleton + detailed checklist see `references/custom-parser-plugin.md`. Key points:

- Register with `@ToolParserManager.register_module(["name"])` (decorator path is lazy — plugin loader imports the file).
- Launch: `--tool-parser-plugin /abs/path/file.py --tool-call-parser name`.
- Closest starting point for most models: `vllm/tool_parsers/pythonic_tool_parser.py` (kwargs Python syntax), `hermes_tool_parser.py` (JSON-in-tags), or `step3p5_tool_parser.py` (expat streaming XML — `qwen3xml_tool_parser.py` was deleted in the unified-engine refactor).
- Must honor the four state fields above. Read `vllm/tool_parsers/abstract_tool_parser.py` for exact signatures.
- Read `tests/tool_parsers/common_tests.py` — reviewers expect this harness.

Before upstreaming, read `AGENTS.md` at the repo root for the duplicate-work + PR-description policy.

## References in this skill

Compact supplementary maps. Each points back at the source rather than duplicating it.

- `references/parser-index.md` — one-line-per-parser index with file path, wrapping tokens at a glance, and the things unique to that parser that aren't obvious from the filename (e.g. "full-width `｜` U+FF5C sentinels", "non-streaming only", "schema-aware type coercion").
- `references/streaming-pitfalls.md` — the things that bite across parsers: full-width pipes, special-token stripping, empty-args stalls, HACKs, and the end-of-stream flush contract.
- `references/custom-parser-plugin.md` — plugin scaffolding checklist with file:line anchors into the base class and the canonical examples.
- `references/sources.md` — verification log of the external GitHub issues/PRs/source files cited by this skill, each with a `Last verified` date. Consult before re-citing a claim; re-probe if the entry is stale (>90 days).

---

**Last verified: 2026-09-22** against vLLM **v0.30.0**. See `references/sources.md` for per-reference probe details and timestamps.
