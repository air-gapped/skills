---
name: vllm-tool-parsers
description: vLLM tool-calling operator reference — picking `--tool-call-parser` per model family, writing custom parsers via `--tool-parser-plugin`, and navigating vLLM source + GitHub tracker to debug any specific tool-call question. Pointer map, not source paraphrase. Covers all 28+ built-in parsers (JSON-sentinel, pythonic, XML, harmony grammars), CLI contract (`--enable-auto-tool-choice`, `--reasoning-parser` pairing, chat-template selection), framework contract (`prev_tool_call_arr` + `streamed_args_for_tool` flush invariants, `ToolParser.adjust_request`, `ToolParserManager.register_module`), and diagnostic playbook (isolate template-vs-parser via raw `/v1/completions` + unicodedata codepoint decode).
when_to_use: Any tool-calling / function-calling question against a vLLM deployment — `--tool-call-parser` / `--enable-auto-tool-choice` flag issues, "tool call not firing", duplicate argument chunks, missing `}` at stream end, `finish_reason` stuck on `stop`, any `<tool_call>` / `<|tool_calls_begin|>` / `[TOOL_CALLS]` / `<|python_tag|>` / `<|action_start|>` / `<seed:tool_call>` sentinel in raw content, Claude Code / LangChain / OpenAI-SDK tool failures, pythonic-vs-JSON for Llama, Mistral v11 `[TOOL_CALLS]`, DeepSeek full-width `｜` (U+FF5C) vs ASCII pipe, GLM XML, Qwen3 XML vs Qwen3-Coder tags, Hermes `skip_special_tokens=False`, Jamba vocab check, reasoning + tool ordering. Apply even if parser not named — "my Qwen isn't calling tools" is this skill.
---

# vLLM Tool Parsers — Navigation Map

This skill points to the right source file, template, or GH issue. The source code is authoritative — read it. **Do not paraphrase from this skill when the actual file is available.**

## Where things live

Assume vLLM repo is checked out somewhere accessible (common path in this project: `<home>/projects/github.com/vllm-project/vllm/`). Every reference below is relative to that repo root.

| Target | Read |
|---|---|
| All tool parsers | `vllm/tool_parsers/` (one file per parser) |
| Parser base class + `ToolParserManager` | `vllm/tool_parsers/abstract_tool_parser.py` |
| Shared helpers (`partial_json_loads`, `find_common_prefix`, `make_valid_python`, `partial_tag_overlap`, `compute_tool_delta`, `handle_single_tool`) | `vllm/tool_parsers/utils.py` |
| Built-in parser registry | `vllm/tool_parsers/__init__.py` — `_TOOL_PARSERS_TO_REGISTER` maps CLI name → module → class |
| CLI flag definitions | `vllm/entrypoints/openai/cli_args.py` — grep `tool_call_parser`, `enable_auto_tool_choice`, `tool_parser_plugin` |
| Non-streaming serving invocation | `vllm/entrypoints/openai/chat_completion/serving.py` — grep `extract_tool_calls` |
| Streaming serving loop + tail flush | same file — grep `extract_tool_calls_streaming`, `prev_tool_call_arr` |
| Plugin import wiring | `vllm/entrypoints/openai/api_server.py` — grep `import_tool_parser` |
| Responses API tool handling | `vllm/entrypoints/openai/responses/serving.py` + `vllm/entrypoints/openai/parser/responses_parser.py` |
| Per-parser Jinja chat templates | `examples/tool_chat_template_<family>.jinja` |
| Per-parser tests (executable spec) | `tests/tool_parsers/test_<name>_tool_parser.py` + `tests/tool_parsers/common_tests.py` |
| User-facing docs | `docs/features/tool_calling.md` |

**If the operator's question is "what does parser X do" — read `vllm/tool_parsers/X_tool_parser.py`.** Don't rely on this skill's paraphrase.

## The CLI contract

Two flags, both required together for auto tool choice:

```bash
vllm serve <model> --enable-auto-tool-choice --tool-call-parser <name> [--chat-template <path>]
```

- `--enable-auto-tool-choice` alone → `TypeError: --enable-auto-tool-choice requires --tool-call-parser` (see `cli_args.py`).
- `--tool-call-parser` alone → legal. Parser still runs for `tool_choice="required"` and named, and on Responses API.
- **No `auto` sentinel.** Name a concrete parser.
- `--tool-parser-plugin <path.py>` → third-party file that calls `@ToolParserManager.register_module("name")`.
- `--reasoning-parser` is independent but several tool parsers assume a `</think>` has closed — match them (see "Reasoning pairing" below).
- Chat template often matters. Each parser has a reference Jinja at `examples/tool_chat_template_<family>.jinja`. Wrong template → model never emits the sentinels the parser expects.

## Parser → model family index

Use this to pick the CLI name. **Then read the parser file and the matching Jinja for details** — the wrapping tokens, streaming strategy, and quirks live there, not here.

| `--tool-call-parser` | Model families | Reference template |
|---|---|---|
| `hermes` | Hermes-2/3, Qwen2.5-Instruct, Qwen3-Instruct (text), QwQ | `tool_chat_template_hermes.jinja` |
| `longcat` | LongCat-Flash-Chat | (inherits hermes) |
| `mistral` | Mistral-Instruct (all), Mistral-Large-2506+ (v≥11 format auto-detected) | `tool_chat_template_mistral.jinja` |
| `llama3_json` / `llama4_json` | Llama 3.1/3.2/3.3/4 (JSON flavor) | `tool_chat_template_llama3.1_json.jinja`, `_llama3.2_json.jinja`, `_llama4_json.jinja` |
| `pythonic` | Llama-3.2-{1B,3B}, ToolACE-8B | `tool_chat_template_llama3.2_pythonic.jinja`, `tool_chat_template_toolace.jinja` |
| `llama4_pythonic` | Llama-4 Scout/Maverick | `tool_chat_template_llama4_pythonic.jinja` |
| `olmo3` | Olmo-3-7B/32B | (HF default) |
| `qwen3_coder` (alias `mimo`) | Qwen3-Coder-480B/30B | `tool_chat_template_qwen3coder.jinja` |
| `qwen3_xml` (alias `mimo`) | Qwen3-XML family | (same grammar as qwen3_coder) |
| `deepseek_v3` / `deepseek_v31` / `deepseek_v32` | DeepSeek-V3/R1, V3.1, V3.2 | `tool_chat_template_deepseek_v3.jinja`, `_deepseekv31.jinja` |
| `glm45` / `glm47` | GLM-4.5/4.6, GLM-4.7 | `tool_chat_template_glm4.jinja` |
| `granite` / `granite-20b-fc` / `granite4` | Granite-3.0/3.1, Granite-20B-FC, Granite-4.0 | `tool_chat_template_granite.jinja`, `_granite_20b_fc.jinja` |
| `phi4_mini_json` | Phi-4-mini | `tool_chat_template_phi4_mini.jinja` |
| `jamba` | Jamba-1.5 | (HF default, sentinel must be in vocab) |
| `internlm` | InternLM-2.5 | `tool_chat_template_internlm2_tool.jinja` |
| `kimi_k2` | Kimi-K2 Instruct / Thinking | (HF default) |
| `minimax` / `minimax_m2` | MiniMax-M1 / M2 | `tool_chat_template_minimax_m1.jinja` (M1) |
| `step3` / `step3p5` | Step-3 VL / Step-3.5-Flash | (HF default) |
| `seed_oss` | Seed-OSS | (HF default) |
| `hunyuan_a13b` | Hunyuan-A13B | (HF default) |
| `ernie45` | ERNIE-4.5 thinking | (HF default) |
| `gemma4` / `functiongemma` | Gemma-4-IT / FunctionGemma-270m | `tool_chat_template_gemma4.jinja`, `_functiongemma.jinja` |
| `gigachat3` | GigaChat-3 | (HF default) |
| `xlam` | Salesforce xLAM Llama & Qwen | `tool_chat_template_xlam_llama.jinja`, `_xlam_qwen.jinja` |
| `openai` | gpt-oss-20b/120b (Harmony channels) | (no Jinja — built-in renderer) |

Don't trust this table to be complete — verify with:

```bash
grep -E "^\s+\"" vllm/tool_parsers/__init__.py    # lists registered names
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
  - `prev_tool_call_arr: list[dict]` — serving reads `[i]["arguments"]` at stream end to flush the tail. If empty at end, `finish_reason` becomes `stop` not `tool_calls`.
  - `current_tool_id: int` — starts `-1`, increments per call.
  - `current_tool_name_sent: bool` — flip True once name flushed for current tool.
  - `streamed_args_for_tool: list[str]` — cumulative args already emitted per tool index. **Append on every flush or the tail double-streams.**
- Optional: `adjust_request(request)` — set `skip_special_tokens=False`, inject grammar, etc. `supports_required_and_named: bool = True` — flip False if the output shape breaks guided JSON.
- Return-value contract for streaming: `None` = "consumed, nothing to emit"; `DeltaMessage(content=...)` = pass-through; `DeltaMessage(tool_calls=[DeltaToolCall(...)])` = tool progress.

For the current in-flight `parse_delta` refactor see RFC #11522; align new parsers with the new shape rather than copying older HACKs.

## Reasoning-parser pairing

Several tool parsers gate on a reasoning-end sentinel. Mismatched pair = tool parser sees reasoning text as content, misses sentinels, or emits from inside `<think>`. Table below is a pointer — verify by reading the tool-parser file for the `adjust_request`/`is_reasoning_end` interaction.

| Tool parser | Pair with | Why |
|---|---|---|
| `hermes` (Qwen3 thinking) | `qwen3` | Gates on `</think>` |
| `deepseek_v3` (R1) | `deepseek_r1` | Gates on `</think>` |
| `seed_oss` | `seed_oss` | Gates on `</seed:think>` |
| `hunyuan_a13b` | `hunyuan_a13b` | Excludes `<think>…</think>` region |
| `minimax`, `minimax_m2` | same name | Interleaved thinking / exclusion zone |
| `kimi_k2` | `kimi_k2` | Implicit end via `<\|tool_calls_section_begin\|>` |
| `ernie45` | `ernie45` | Expects `</think>\n\n\n<tool_call>` |
| `mistral` (reasoning variants) | `mistral` | Tokenized reasoning section |

Sibling skill: `vllm-reasoning-parsers` — defer there for reasoning-side questions.

## Diagnostic playbook

When a user reports a broken tool call, work down this list. Each step names where to look.

1. **Both flags set?** Check serve command for `--enable-auto-tool-choice --tool-call-parser <name>`.
2. **Right parser for the model?** Cross-check with the table above AND with `vllm/tool_parsers/__init__.py` registry.
3. **Chat template matches?** Inspect the actual template bytes — don't trust the filename. See step 7.
4. **Reasoning parser paired?** If the model has `<think>` / `</seed:think>` / harmony channels, `--reasoning-parser` must match. Check `vllm/reasoning/` for the registry.
5. **Streaming vs non-streaming?** Grep the parser file: if `extract_tool_calls_streaming` returns `None` unconditionally or raises `NotImplementedError`, streaming isn't supported (e.g. `phi4_mini_json`, `openai`).
6. **`finish_reason` = `stop`?** Then `prev_tool_call_arr` is empty at stream end — parser failed to populate it. Enable vLLM debug logs and trace.
7. **Raw model output vs what parser sees.** Bypass the parser: call `/v1/completions` (no tool parser) with the same prompt. Dump raw bytes:
   ```bash
   curl -sS $VLLM/v1/completions -H 'content-type: application/json' \
     -d '{"model":"...","prompt":"...","max_tokens":200}' \
     | python3 -c "import sys,json,unicodedata; t=json.load(sys.stdin)['choices'][0]['text']; \
         [print(hex(ord(ch)), unicodedata.name(ch,'?'), repr(ch)) for ch in t if ord(ch)>0x7E][:40]"
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

Umbrella RFC to know about: **#11522** — "Refactor tool parsers to eliminate coding errors". Tracks the `parse_delta` refactor (PRs #39446, #39728, #38755). Any new parser work should align with it.

## In-tree HACKs to recognize

Helpful to know what to look for when reading a parser. Grep the codebase for these:

```bash
grep -rn "HACK" vllm/tool_parsers/
grep -rn "TODO" vllm/tool_parsers/
grep -rn "prev_tool_call_arr = \[{\"arguments\": {}}\]" vllm/tool_parsers/
```

The `prev_tool_call_arr = [{"arguments": {}}]` plant is the classic "force finish_reason=tool_calls" workaround. Mistral and all pythonic-family parsers carry it. When writing a new parser, prefer the `parse_delta` shape (RFC #11522).

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
- Closest starting point for most models: `vllm/tool_parsers/pythonic_tool_parser.py` (kwargs Python syntax), `hermes_tool_parser.py` (JSON-in-tags), or `qwen3xml_tool_parser.py` (expat streaming XML).
- Must honor the four state fields above. Read `vllm/tool_parsers/abstract_tool_parser.py` for exact signatures.
- Read `tests/tool_parsers/common_tests.py` — reviewers expect this harness.

Before upstreaming, read `AGENTS.md` at the repo root for the duplicate-work + PR-description policy.

## References in this skill

Compact supplementary maps. Each points back at the source rather than duplicating it.

- `references/parser-index.md` — one-line-per-parser index with file path, wrapping tokens at a glance, and the things unique to that parser that aren't obvious from the filename (e.g. "full-width `｜` U+FF5C sentinels", "non-streaming only", "schema-aware type coercion").
- `references/streaming-pitfalls.md` — the things that bite across parsers: full-width pipes, special-token stripping, empty-args stalls, HACKs, diagnostic flow. Points at `chat_completion/serving.py` for the flush contract.
- `references/custom-parser-plugin.md` — plugin scaffolding checklist with file:line anchors into the base class and the canonical examples.

(Older `references/json-family.md`, `pythonic-xml-family.md`, `known-bugs.md` removed — they duplicated source and rotted. Use `Grep`/`gh search` instead.)
