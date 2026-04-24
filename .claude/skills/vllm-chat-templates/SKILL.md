---
name: vllm-chat-templates
description: |-
  vLLM chat-template (prompt-side Jinja) operator reference. Template resolution precedence (`--chat-template` → AutoProcessor → tokenizer default → bundled fallback), `chat_template_kwargs` allowlist silently dropping `add_generation_prompt`/`enable_thinking`/custom kwargs (PR 27622 fix), 27 shipped `tool_chat_template_*.jinja` files, known template-layer bugs for Qwen3/Qwen3-Coder, DeepSeek-R1/V3/V3.1/V3.2, GPT-OSS, Kimi-K2, Llama-4, Mistral (HF vs mistral mode), Gemma-3/4, Phi-4, GLM. Prompt side only — output parsing lives in sibling skills.
when_to_use: |-
  Trigger on "chat template broken", "chat template no effect", "--chat-template ignored", "jinja template error vllm", "apply_chat_template error", "ChatTemplateResolutionError", "tool_chat_template", "which tool_chat_template", "chat_template_kwargs not respected", "add_generation_prompt dropped", "enable_thinking ignored", "continue_final_message", "--chat-template-content-format auto", "tokenizer-mode mistral silent", "harmony format gpt-oss template", "template resolution order", "AutoProcessor chat template skipped when tools", "prompt doesn't match model card", "/v1/chat/completions vs /v1/responses template". TGI/SGLang/TensorRT-LLM-to-vLLM migration where Jinja differs. Also implicit — "audit chat template for {model}", "deploy-memo prompt format", "why does model emit wrong prompt", "jinja check". NOT for output parsing (→ `vllm-reasoning-parsers` / `vllm-tool-parsers`), NOT for KV caching (→ `vllm-caching`).
---

# vLLM chat templates — operator triage

Target audience: operators deploying vLLM in production. Assumes OpenAI-API-compatible frontend (`/v1/chat/completions` or `/v1/responses`), multi-GPU, mid-2024 through 2026 model families.

## Scope — three sibling skills, three layers

Chat-template bugs span three layers. This skill owns the **prompt-rendering** layer; route to a sibling when the problem is output-side.

| Layer | Direction | Skill | What it covers |
|---|---|---|---|
| **Chat template (Jinja)** | messages → prompt string | **this skill** | template precedence, `--chat-template`, `chat_template_kwargs`, `examples/tool_chat_template_*.jinja`, bundled fallbacks |
| **Reasoning parser** | model output → `reasoning_content` + `content` | `vllm-reasoning-parsers` | `--reasoning-parser`, `extract_reasoning`, `is_reasoning_end`, `<think>` splitting |
| **Tool parser** | model output → `tool_calls[]` | `vllm-tool-parsers` | `--tool-call-parser`, streaming state machines, partial-JSON parsing |

When in doubt: if the operator complains about what the **server receives**, it's this skill; if about what the **client receives**, it's one of the parser skills. Template and parser bugs often present the same symptom ("reasoning_content is null"), so all three skills name each other in diagnostics. This file stays on the Jinja side.

## Why this matters

Chat templates are the **Jinja layer between structured messages and the raw prompt string the model sees**. Tool-calling and reasoning models are extremely sensitive to this layer — a one-character whitespace difference in a template can send tool-call success rate from 99% to 0%, silently.

The hardest class of bug in vLLM deployments is **template silent failure**: the server starts, requests return 200s, but the model emits garbled tool calls, or `reasoning_content` is `null`, or `enable_thinking=false` has no effect. No exception, no log line, just wrong outputs. Operators often chase parser bugs when the real fix is a template override (or vice versa — override a template when the real fix is a parser flag).

This skill's job: given a symptom, identify whether it's a template, a parser, a kwarg, or an API-endpoint issue, and point at the known fix.

## Template resolution precedence (memorize this)

vLLM picks a chat template in this order. First hit wins. Source: `vllm/renderers/hf.py:96-145` (`resolve_chat_template()`).

1. **`--chat-template <path-or-name>` CLI flag** — highest. Path to a `.jinja` file, literal Jinja string, or a named template (`"tool_use"`) that the tokenizer knows.
2. **AutoProcessor chat template** — only consulted when the request has `tools=None`. Multimodal models often expose their template via the processor, not the tokenizer. Source: `hf.py:110-116`.
3. **AutoTokenizer `chat_template`** — the one shipped in `tokenizer_config.json`. Source: `hf.py:119-126`.
4. **Bundled fallback in `vllm/transformers_utils/chat_templates/`** — vLLM ships defaults for ~10 vision/OCR model families (blip-2, chameleon, clip, colpali, deepseek_ocr/ocr2/vl_v2, fuyu, minicpmv, paligemma, qwen, siglip/siglip2). Source: `registry.py:64-75`.

If none resolves, **`ChatTemplateResolutionError`** raised at `hf.py:477` with: *"As of transformers v4.44, default chat template is no longer allowed, so you must provide a chat template if the tokenizer does not define one."*

### Consequences operators miss

- **Passing `--chat-template` does NOT override the tokenizer's template if the path is invalid** — vLLM raises *"The supplied chat template ... appears path-like, but doesn't exist!"* (`chat_utils.py:1105-1109`). Check `ls` first.
- **Tool-calling disables the AutoProcessor step.** If a multimodal model has a processor template but the request has `tools`, vLLM skips it and falls through to tokenizer. This is *intentional* — tool templates must be explicit.
- **`--tokenizer-mode mistral` silently ignores `--chat-template`.** Warning only; see Mistral section in `references/model-families.md`. Issue vllm-project/vllm#25401 — closed as COMPLETED 2025-10-09. Behavior is at least louder in current vLLM; verify on your version before assuming silent-drop. Verified 2026-04-24.
- **Some templates (e.g. gpt-oss) appear hard-coded** — operator-supplied `--chat-template` has no effect (vllm-project/vllm#23015, closed NOT_PLANNED 2026-04-20). Intentional: gpt-oss goes through the Harmony path via `/v1/responses`; `--chat-template` is not the intended escape hatch. Verified 2026-04-24.

## Triage: symptom → suspect

Use this table first. Load `references/model-families.md` for the specific model bug + flags.

| Symptom | First suspect | Second suspect |
|---|---|---|
| `reasoning_content` is `null` or missing from response | `--reasoning-parser` flag missing/wrong | Template strips opening `<think>` before model generates it (DeepSeek-R1) |
| `tool_calls` empty array `[]` but model emitted text | `--tool-call-parser` wrong for model family | `tool_choice="auto"` (try `"required"` or a named tool) |
| Tool calls have malformed JSON / `arguments` empty | Wrong tool-call parser (Hermes vs pythonic vs XML vs model-specific) | Template doesn't inject `tools` correctly |
| `enable_thinking=False` has no effect | Kwarg dropped by vLLM allowlist (need PR #27622 or ≥v0.11.1) | Downstream harness not forwarding `chat_template_kwargs` |
| Tool calling works on `/v1/completions` but not `/v1/chat/completions` | Chat template doesn't render tool result (e.g. GLM-5.1 #39611) | Endpoint-specific parser path |
| Prompt in server log doesn't match model card | Wrong template resolving — check precedence order above | `--chat-template` pointing at file that doesn't exist (silent for some tokenizer modes) |
| `<think>` content leaks into final output | `--reasoning-parser` missing | `skip_special_tokens=true` stripping control tokens before parser (#38855) |
| Garbled prompt with repeated `<image>` placeholders | Template has placeholder AND multimodal parser adds one | `interleave_strings` mismatch — see `chat_utils.py:1186-1241` |
| `IndexError` / Jinja exception on multi-turn tool calls | Tool-call ID format regex too strict (Kimi-K2, Mistral) | Historical `tool_calls=[]` in assistant msg crashes template (Llama #13978) |
| Server starts, first request works, subsequent requests fail | State-ful template bug: leading whitespace accumulating (DeepSeek V3.1 #28804) | Concurrent-request regression (Gemma-4 `<pad>` tokens #39392) |
| "this model is reasoning but reasoning_effort=none" | gpt-oss #37909 — `"none"` not honored | Wrong reasoning parser |
| Works on SGLang / TGI, broken on vLLM | vLLM applies template differently (HF precedence + kwarg allowlist) | Check `--tokenizer-mode` differences |

Three orthogonal layers — diagnose one at a time, don't change multiple at once:

- **Template layer**: Jinja file that turns messages → prompt string.
- **Parser layer** (output): `--tool-call-parser`, `--reasoning-parser` — extract structured fields from model output.
- **Kwarg layer**: `chat_template_kwargs` forwarded to `apply_chat_template`.

## The flag matrix (common case)

Per-family flag matrix lives in `references/flags-matrix.md`. Quick cheat-sheet for the production-critical ones:

| Model family | `--chat-template` | `--tool-call-parser` | `--reasoning-parser` |
|---|---|---|---|
| Qwen3 dense / MoE | tokenizer default | `hermes` | `qwen3` |
| Qwen3-Coder | tokenizer default | `qwen3_xml` | — |
| DeepSeek-R1 | `examples/tool_chat_template_deepseekr1.jinja` | `deepseek_v3` | `deepseek_r1` |
| DeepSeek-V3-0324 | `examples/tool_chat_template_deepseekv3.jinja` | `deepseek_v3` | — |
| DeepSeek-V3.1 | `examples/tool_chat_template_deepseekv31.jinja` | `deepseek_v31` | `deepseek_r1` |
| DeepSeek-V3.2 | (uses `--tokenizer-mode deepseek_v32`) | `deepseek_v32` | `deepseek_r1` |
| GPT-OSS 20B/120B | prefer `/v1/responses` endpoint | `openai` (broken on chat-completions #22578) | harmony-native |
| Kimi-K2 | tokenizer default (post-fix commit) | `kimi_k2` | `kimi_k2` |
| Llama-4 Maverick/Scout | `examples/tool_chat_template_llama4_pythonic.jinja` | `llama4_pythonic` | — |
| Mistral (HF format) | `examples/tool_chat_template_mistral_parallel.jinja` | `mistral` | — |
| Mistral (`mistral` tokenizer-mode) | **ignored** (don't set) | `mistral` | — |
| Gemma-3 | `examples/tool_chat_template_gemma3_pythonic.jinja` | `pythonic` | — |
| Gemma-4 | `examples/tool_chat_template_gemma4.jinja` | `gemma4` (flaky concurrent) | `gemma4` |
| Phi-4-mini | `examples/tool_chat_template_phi4_mini.jinja` | `llama3_json` | — |
| Phi-4-reasoning | tokenizer default | — | **not** `deepseek_r1` (#18141) |
| Hermes / Hunyuan / Granite / Toolace / XLAM | `examples/tool_chat_template_<name>.jinja` | `hermes`/matching | — |

Commit-gated models (Kimi-K2) require minimum HF revision — check `references/model-families.md` before recommending.

## Top 15 patterns that silently break production

Consult this list for any "broken chat template" symptom. Most reports reduce to one of these.

1. **Chat template silently ignored.** Mistral in `--tokenizer-mode mistral` (#25401), reportedly gpt-oss (#23015). Warning-only. Symptom: edit template, nothing changes. Fix: switch to HF tokenizer mode, or accept that the built-in Mistral template is canonical.

2. **`skip_special_tokens=true` strips control tokens before reasoning parser.** Gemma-4 (#38855), Qwen3 reasoning, gpt-oss harmony. Fix: `extra_body={"skip_special_tokens": false}` per request.

3. **`<think>` opening tag prepended to prompt → never appears in output → `reasoning_content=null`.** DeepSeek-R1 (HF #144, vLLM #12999). Template forces thinking by inserting `<think>\n` in the prefill; parser sees only `</think>`. Fix: post-process prepend `<think>`, or use patched template.

4. **Empty string `''` wrapped to `[{'type':'text','text':''}]`.** Broke Kimi-K2 templates expecting strings. Any template that doesn't type-check `message.content` is at risk. Fix: updated chat template or vLLM version.

5. **Tool-call ID regex mismatch.** Mistral requires 9 digits; Kimi-K2 required `functions.X:idx` exactly. vLLM generates longer IDs → `IndexError` → all tool calls silently dropped. Fix: Kimi-K2 fixed in PR #27565; Mistral template truncates to last 9 digits.

6. **`add_generation_prompt` dropped by kwarg allowlist.** PR #25794 restricted `**kwargs` forwarding for security; tokenizers relying on non-standard params broke. Fix: PR #27622 whitelists standard HF params — requires vLLM ≥ v0.11.1.

7. **Jinja template from disk triggers `_try_extract_ast()` exception.** #14884: `\n` escape sequences double-converted when shell-interpolated. Fix: pass the file path, not the contents; don't shell-escape.

8. **`tool_calls=[]` in historical assistant message crashes template.** #13978 (Llama). Templates assume nonempty if present. vLLM now drops empty tool_calls (`chat_utils.py:1586-1589`).

9. **`tool_choice="auto"` vs `"required"` divergence.** `auto` = free-form generation + regex parse (schema-free, brittle). `required`/named = structured-outputs FSM (schema-valid). Many "tool calling is broken" reports vanish when switching to `required`.

10. **Multi-turn whitespace accumulation.** DeepSeek V3.1 (#28804, closed NOT_PLANNED 2026-03-23) — leading whitespace grows each turn. Look for this when assistant replies get progressively indented. Upstream not planning a fix; apply client-side mitigation (strip leading whitespace on each turn) or use `deepseek_v31` parser commits post-issue report. Verified 2026-04-24.

11. **`reasoning_effort="none"` silently breaks output.** gpt-oss #37909. Fix: omit or use `"low"`.

12. **Concurrent requests → `<pad>` tokens.** Gemma-4 #39392. Not reproducible sequentially. Fix: version bump; interim workaround `--max-num-seqs 1`.

13. **`--chat-template-content-format auto` misroutes tool results.** GLM-5.1 #39614: tool result as `{"type":"text","text":"..."}` hits an "else" branch in a template checking `.name` → renders `<tools></tools>` instead of result.

14. **`/v1/chat/completions` vs `/v1/responses` divergence.** gpt-oss tool calling works only on `/v1/responses` (#22578). GLM-4.7 (#39611) tool results ignored on chat-completions but work on completions.

15. **API field name mismatch.** `reasoning` (vLLM older) vs `reasoning_content` (DeepSeek/OpenAI-style). Clients that hard-code one break on version bump. vLLM settled on `reasoning_content` (#28472).

## What `chat_template_kwargs` accepts

Threaded as `extra_body={"chat_template_kwargs": {...}}` in OpenAI client. Source: `vllm/renderers/params.py:70-125`, `hf.py:407-435`.

- **Any Jinja variable** referenced in the resolved template — detected via AST parse at `hf.py:429`.
- **HF `apply_chat_template` params** auto-detected from tokenizer signature (`hf.py:387-404`).
  - `add_generation_prompt` (bool)
  - `continue_final_message` (bool) — mutually exclusive with `add_generation_prompt=True`
  - `documents` (list of `{title, contents}`) for RAG templates
  - `enable_thinking` (Qwen3 and some others)
- **Reserved (will raise `ValueError`):** `chat_template`, `tokenize` (`hf.py:416-421`).
- **Unknown kwargs silently filtered** (`hf.py:434-435`) — if `enable_thinking` doesn't appear in the detected Jinja vars, it's dropped without warning. This is a confusing failure mode: operator sets it, sees no effect, can't find an error.

Merging: server defaults (serving.py:111) ← request kwargs (params.py:28-40) — request wins.

## Reasoning parser vs chat template (they're confused a lot)

- **Chat template** (this skill) controls the *prompt* — where `<think>` tags go going *in* to the model, and how tool definitions get rendered.
- **Reasoning parser** (`vllm-reasoning-parsers`) extracts `<think>` content from *output* into `reasoning_content`. Template-side causes of null `reasoning_content` are pattern #3 above (opening `<think>` prepended in prefill); all other root causes live in the parser skill.
- **Tool-call parser** (`vllm-tool-parsers`) extracts `tool_calls[]` from *output*. Template-side causes of empty `tool_calls` are wrong tool template or `tool_choice="auto"` vs `"required"` (pattern #9); parser-selection and streaming state-machine debugging live in that skill.

Raw-output capture (`--disable-log-requests=False` + no `--tool-call-parser`/`--reasoning-parser`) determines which layer is at fault: if the model emits the expected tags/JSON, the prompt is fine and the problem is parser-side; if not, the template is misrendering.

## Multimodal template notes

Models use model-specific placeholders (`<image>`, `<|image_start|>`, etc.) — vLLM's internal placeholder is `<##IMAGE##>` / `<##AUDIO##>` / `<##VIDEO##>` (`chat_utils.py:96-100`).

- If request has images but template has no placeholder, vLLM **prepends** them to final prompt (`chat_utils.py:1233-1240`). Some models tolerate this; others produce garbage.
- If template has more placeholders than media items: `ValueError: "Found more '<image>' placeholders in input prompt than actual multimodal data items."` (`chat_utils.py:1226-1229`).
- `interleave_strings=True` (via `multimodal_config.interleave_mm_strings`) enables in-order substitution; default is prepend-all.

For Pixtral, Mistral-Small-3.1 multimodal, and other MM-tool-calling combinations, see `references/model-families.md`.

## When nothing works — full debugging workflow

Load `references/debugging.md`. The short version:

1. **Log the actual prompt.** `--disable-log-requests=False` + log level DEBUG. Compare against model card example. If they differ, template is wrong.
2. **Bypass vLLM.** Load the same tokenizer in a Python REPL, call `tokenizer.apply_chat_template(messages, add_generation_prompt=True)`, compare. If same bad output, template is wrong. If different, vLLM's kwarg forwarding is eating something.
3. **Capture raw model output.** Set `--tool-call-parser` to none, read what the model actually emits. Then work backward to pick the right parser.
4. **Pin versions.** Record `vllm --version`, `transformers.__version__`, model revision SHA. Many template bugs track a specific `tokenizer_config.json` commit — mention in bug reports.

## Code locations (for reading vLLM source)

- `vllm/entrypoints/chat_utils.py` — message parsing, multimodal placeholder injection, `ChatTemplateResolutionError`.
- `vllm/renderers/hf.py:96-145` — `resolve_chat_template()` precedence.
- `vllm/renderers/hf.py:460-505` — `safe_apply_chat_template()` + error surface.
- `vllm/renderers/hf.py:407-435` — `resolve_chat_template_kwargs()` allowlist.
- `vllm/renderers/params.py:70-125` — `ChatParams` dataclass.
- `vllm/reasoning/__init__.py:22-103` — registered reasoning parsers.
- `vllm/transformers_utils/chat_templates/registry.py:64-75` — bundled fallback lookup.
- `vllm/entrypoints/openai/serving_chat.py:91-182` — parser instantiation at server init.
- `examples/tool_chat_template_*.jinja` (27 files) — ready-made tool templates per model family.

## Per-family deep-dive

When the operator names a model family, load `references/model-families.md` — it has per-family flag recipes, minimum commit SHAs, known bugs with issue numbers, and recovery strategies.

## Further reference material

- `references/model-families.md` — Qwen3, DeepSeek, GPT-OSS, Kimi-K2, Llama-4, Mistral, Gemma, Phi-4, GLM, Hermes/Granite/Hunyuan — with inline issue URLs.
- `references/debugging.md` — stepwise debugging workflow + full error-message catalog.
- `references/flags-matrix.md` — quick CLI-flag lookup per model.
- `references/sources.md` — verification log for external URLs/issues/PRs cited in this skill, with `Last verified` dates.

Last verified: 2026-04-24 (see `references/sources.md` for per-ref status).
