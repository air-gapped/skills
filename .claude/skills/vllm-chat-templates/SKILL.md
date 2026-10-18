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

vLLM picks a chat template in this order. First hit wins. Source: `resolve_chat_template()` in `vllm/renderers/hf.py`.

1. **`--chat-template <path-or-name>` CLI flag** — highest. Path to a `.jinja` file, literal Jinja string, or a named template (`"tool_use"`) that the tokenizer knows.
2. **AutoProcessor chat template** — only consulted when the request has `tools=None`. Multimodal models often expose their template via the processor, not the tokenizer.
3. **AutoTokenizer `chat_template`** — the one shipped in `tokenizer_config.json`.
4. **Bundled fallback in `vllm/transformers_utils/chat_templates/`** — at v0.32.0, **14 model types** mapping onto 7 shipped `.jinja` files: blip-2, clip, colpali, deepseek_ocr, deepseek_ocr2, unlimited-ocr, unlimited_ocr, deepseek_vl_v2, minicpmv, minicpmv4_6, minicpmv4_7, paligemma, siglip, siglip2. No `fuyu` (model dropped in v0.26.0) and no `qwen`/Qwen-VL entry — a Qwen checkpoint with its template stripped has no fallback. Source: `_MODEL_TYPE_TO_CHAT_TEMPLATE_FALLBACK` in `chat_templates/registry.py`.

If none resolves, **`ChatTemplateResolutionError`** raised by `safe_apply_chat_template()` with: *"As of transformers v4.44, default chat template is no longer allowed, so you must provide a chat template if the tokenizer does not define one."*

> **Do not "modernize" that v4.44** — it is vLLM's verbatim error string, not a version requirement. The real `transformers` pin and the template-name security floor (below v0.32.0, pin `transformers` explicitly): `references/debugging.md` § Step 4.

### Consequences operators miss

- **Passing `--chat-template` does NOT override the tokenizer's template if the path is invalid** — vLLM raises *"The supplied chat template ... appears path-like, but doesn't exist! Tried: <path> and <built-in dir>/<path>"* (`validate_chat_template()` in `vllm/renderers/chat_utils.py`; `vllm/entrypoints/chat_utils.py` before v0.32.0). A bare name is also looked up in the bundled `chat_templates/` dir. **A value containing `{`, `}` or a newline skips that check** and, if it does not open, is used as literal Jinja (`_load_chat_template()`) — a mangled Helm/env-interpolated value renders silently. `examples/…` resolves against the process cwd: `vllm/vllm-openai` has it at `/vllm-workspace/examples` (its WORKDIR); the `-nonroot` image's WORKDIR is `/home/vllm`; pip wheels ship no `examples/`. **Every launch recipe that passes `--chat-template` must tell the operator to `ls` the path inside the serving container** and to confirm the logged prompt matches that file.
- **Tool-calling disables the AutoProcessor step.** If a multimodal model has a processor template but the request has `tools`, vLLM skips it and falls through to tokenizer. This is *intentional* — tool templates must be explicit. Without `--chat-template`, image-only and image+tools requests to the same model render with **two different templates** — a smoke test must cover both shapes; an explicit `--chat-template` pins one template for both.
- **v0.32.0+ bounds template rendering** (#50300; no static template validation shipped despite the release note). Python online renderer: `TimeoutError: Chat template rendering timed out after 30.0s` — raise `VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT` (seconds, default 30; `<= 0` disables) for a legitimately huge prompt. Rust frontend: fixed MiniJinja fuel budget (500,000 instructions), no knob. `/v1/responses` now refuses `chat_template` inside `chat_template_kwargs` unless `--trust-request-chat-template` is set, as chat-completions already did.

## Triage: symptom → suspect

Use this table first. Load `references/model-families.md` for the specific model bug + flags.

| Symptom | First suspect | Second suspect |
|---|---|---|
| `reasoning_content` is `null` or missing from response | `--reasoning-parser` flag missing/wrong, or client reads `reasoning_content` off a response that names it `reasoning` (pattern #15) | Template prefills `<think>` (DeepSeek-R1) — a cause only on vLLM ≤ v0.7.2 (pattern #3) |
| `tool_calls` empty array `[]` but model emitted text | `--tool-call-parser` wrong for model family | `tool_choice="auto"` (try `"required"` or a named tool) |
| Tool calls have malformed JSON / `arguments` empty | Wrong tool-call parser (Hermes vs pythonic vs XML vs model-specific) | Template doesn't inject `tools` correctly |
| `enable_thinking=False` has no effect | Kwarg dropped by vLLM allowlist (need PR #27622 or ≥v0.11.1) | Downstream harness not forwarding `chat_template_kwargs` |
| Tool calling works on `/v1/completions` but not `/v1/chat/completions` | Chat template doesn't render tool result (GLM-5.1 #39611, fixed 2026-04-12) | Endpoint-specific parser path |
| Prompt in server log doesn't match model card | Wrong template resolving — check precedence order above | `--chat-template` pointing at file that doesn't exist (silent for some tokenizer modes) |
| `<think>` content leaks into final output | `--reasoning-parser` missing | `skip_special_tokens=true` stripping control tokens before parser (#38855) |
| Garbled prompt with repeated `<image>` placeholders | Template has placeholder AND multimodal parser adds one | `interleave_strings` mismatch — see `_get_full_multimodal_text_prompt()` in `renderers/chat_utils.py` |
| `IndexError` / Jinja exception on multi-turn tool calls | Tool-call ID format regex too strict (Kimi-K2, Mistral) | Historical `tool_calls=[]` in assistant msg crashes template (Llama #13978) |
| Server starts, first request works, subsequent requests fail | State-ful template bug: leading whitespace accumulating (DeepSeek V3.1 #28804) | Concurrent-request regression (Gemma-4 `<pad>` tokens #39392) |
| "this model is reasoning but reasoning_effort=none" | gpt-oss #37909 — `"none"` not honored | Wrong reasoning parser |
| Works on SGLang / TGI, broken on vLLM | vLLM applies template differently (HF precedence + kwarg allowlist) | Check `--tokenizer-mode` differences |

Template, parser (output), and kwarg (`chat_template_kwargs`) are orthogonal layers — diagnose one at a time, don't change multiple at once.

## The flag matrix (common case)

Per-family flag matrix lives in `references/flags-matrix.md`. Quick cheat-sheet for the production-critical ones:

| Model family | `--chat-template` | `--tool-call-parser` | `--reasoning-parser` |
|---|---|---|---|
| Qwen3 dense / MoE | tokenizer default | `hermes` | `qwen3` |
| Qwen3-Coder (480B-A35B, 30B-A3B) | `examples/tool_chat_template_qwen3coder.jinja` | `qwen3_xml` — **not** `hermes`: emits XML `<function=…><parameter=…>`, hermes drops it → `tool_calls=[]` | — |
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

## Top 16 patterns that silently break production

Consult this list for any "broken chat template" symptom. Most reports reduce to one of these.

1. **Chat template silently ignored.** `--tokenizer-mode mistral` ignores `--chat-template` with a warning only (#25401); gpt-oss ignores it by design (#23015). Symptom: edit template, nothing changes. Fix: Mistral → HF tokenizer mode, or accept the built-in Mistral template as canonical; gpt-oss → `/v1/responses`.

2. **`skip_special_tokens=true` strips control tokens before the reasoning parser.** Qwen3 reasoning, gpt-oss harmony. Fix: `extra_body={"skip_special_tokens": false}` per request. Gemma-4 (#38855) also needs a re-pulled HF template, not only a vLLM upgrade — §Gemma-4 in `model-families.md`.

3. **`<think>` prefilled by the template → output carries only `</think>`.** DeepSeek-R1 / R1-Distill templates end the generation prompt with `<think>\n` (HF #144). This nulled `reasoning_content` only on vLLM ≤ v0.7.2 (#12999). **Since v0.7.3 (#13025) the `deepseek_r1` parser (and every `BaseThinkingReasoningParser`) treats all text before `</think>` as reasoning when `<think>` is absent**, so on current vLLM the prefill never empties the reasoning field. Reasoning null **and** chain-of-thought inside `content` on ≥ v0.7.3 means the parser did not split that response: confirm `--reasoning-parser` reached the server (startup log, wrapper/Helm args), capture raw output (debugging step 3), then work in `vllm-reasoning-parsers`. Do not swap `--chat-template` for this — the parser already tolerates the prefill either way. Only on ≤ v0.7.2: upgrade, or prepend `<think>` client-side before parsing.

4. **Empty string `''` wrapped to `[{'type':'text','text':''}]`.** Broke Kimi-K2 templates expecting strings. Any template that doesn't type-check `message.content` is at risk. Fix: updated chat template or vLLM version.

5. **Tool-call ID regex mismatch.** Mistral requires 9 digits; Kimi-K2 required `functions.X:idx` exactly. vLLM generates longer IDs → `IndexError` → all tool calls silently dropped. Fix: Kimi-K2 fixed in PR #27565; Mistral template truncates to last 9 digits.

6. **`add_generation_prompt` dropped by kwarg allowlist.** PR #25794 restricted `**kwargs` forwarding for security; tokenizers relying on non-standard params broke. Fix: PR #27622 whitelists standard HF params — requires vLLM ≥ v0.11.1.

7. **Jinja template from disk triggers `_try_extract_ast()` exception.** #14884: `\n` escape sequences double-converted when shell-interpolated. Fix: pass the file path, not the contents; don't shell-escape.

8. **`tool_calls=[]` in historical assistant message crashes template.** #13978 (Llama). Templates assume nonempty if present. vLLM now drops empty `tool_calls` before rendering (`vllm/renderers/chat_utils.py`).

9. **`tool_choice="auto"` vs `"required"` divergence.** `auto` = free-form generation + regex parse (schema-free, brittle). `required`/named = structured-outputs FSM (schema-valid). Many "tool calling is broken" reports vanish when switching to `required`.

10. **Multi-turn whitespace accumulation.** DeepSeek V3.1 (#28804, won't fix): leading whitespace grows each turn, so assistant replies get progressively indented. Fix: strip leading whitespace from each assistant turn client-side.

11. **`reasoning_effort="none"` silently breaks output.** gpt-oss #37909. Fix: omit or use `"low"`.

12. **Parallel *tool-call* requests → `<pad>` tokens.** Gemma-4 #39392, open at v0.32.0 — no version bump fixes it. Plain load is stable; the trigger is parallel tool-call requests. Fix: serialise the tool-calling path; `--max-num-seqs 1` only as a last resort (it throttles the whole server).

13. **`--chat-template-content-format auto` misroutes tool results.** A template that branches on `.name` sends a `{"type":"text",...}` tool result to its else branch and renders `<tools></tools>` instead of the result (GLM-5.1 #39614, fixed upstream). Fix: upgrade, or pass `--chat-template-content-format openai`/`string`.

14. **`/v1/chat/completions` vs `/v1/responses` divergence.** gpt-oss tool calling works only on `/v1/responses` (#22578, permanent). Tool results ignored on chat-completions but honoured on `/v1/completions` → the template drops the tool-result message (GLM-5.1 #39611, fixed upstream).

15. **API field name mismatch.** The **response** field on current vLLM is `reasoning`, *not* `reasoning_content` — at v0.32.0: `ChatMessage.reasoning` (`chat_completion/protocol.py`), `DeltaMessage.reasoning` (`generate/base/protocol.py`). The **request** side still accepts `reasoning_content` and normalizes it (RFC #27755). A client reading `reasoning_content` off a response sees `null` every time even when the parser ran perfectly — this looks exactly like a parser failure. Check with `jq '.choices[0].message | keys'` before debugging parsers.

16. **Content-format auto-detection misses macro-only templates.** `_detect_content_format()` (`vllm/renderers/hf.py`) looks for a `for item in message['content']` loop; before v0.30.0 (#53824) a template that reaches `message.content` only through a macro parameter was detected as `string`, silently flattening multimodal content. Fix: v0.30.0+, or pass `--chat-template-content-format openai`.


## What `chat_template_kwargs` accepts

Threaded as `extra_body={"chat_template_kwargs": {...}}` in OpenAI client. Source: `ChatParams` (`vllm/renderers/params.py`), `resolve_chat_template_kwargs()` (`hf.py`).

- **Any Jinja variable** referenced in the resolved template — detected via AST parse (`_resolve_chat_template_kwargs()`).
- **HF `apply_chat_template` params** auto-detected from the tokenizer signature plus HF's base `apply_chat_template` signature (`_get_hf_base_chat_template_params()`).
  - `add_generation_prompt` (bool)
  - `continue_final_message` (bool) — mutually exclusive with `add_generation_prompt=True` (enforced in `chat_completion/protocol.py`). **Frontend-dependent:** almost no HF chat template actually reads this variable, so on the Python renderer it is close to a no-op. The **Rust frontend** implements Transformers-v5 semantics properly ([#47844](https://github.com/vllm-project/vllm/pull/47844), v0.26.0) — it appends a sentinel to the last message and strips it from the rendered output, so the template never needs to know. The Rust Harmony renderer rejects it outright ("Harmony renderer does not support continue_final_message"). If it silently does nothing, check which frontend serves the request before editing the template. **v0.30.0+:** the Rust frontend also parses `{% generation %}...{% endgeneration %}` blocks (`rust/src/chat/src/renderer/hf/generation.rs`, #56378), rendering only their text — templates that mark assistant spans this way no longer fail there. `return_assistant_tokens_mask` on `/render` and the `assistant_tokens_mask` response field were **removed in v0.31.0** (#57520); do not send them.
  - `documents` (list of `{title, contents}`) for RAG templates
  - `enable_thinking` (Qwen3 and some others)
- **Reserved (will raise `ValueError`):** `chat_template`, `tokenize`.
- **Unknown kwargs silently filtered** — if `enable_thinking` doesn't appear in the detected Jinja vars, it is dropped with no warning and no error. Confirm the kwarg reached the template: `references/debugging.md` § Verifying the kwarg actually reached the template.

Merging: server defaults (`--default-chat-template-kwargs`) ← request kwargs via `ChatParams.with_defaults()` / `merge_kwargs()` — request wins.

## Reasoning parser vs chat template (they're confused a lot)

- **Chat template** (this skill) controls the *prompt* — where `<think>` tags go going *in* to the model, and how tool definitions get rendered.
- **Reasoning parser** (`vllm-reasoning-parsers`) extracts `<think>` content from *output* into `reasoning_content`. On vLLM ≥ v0.7.3 no template prefill nulls `reasoning_content` (pattern #3); every current root cause lives in the parser skill.
- **Tool-call parser** (`vllm-tool-parsers`) extracts `tool_calls[]` from *output*. Template-side causes of empty `tool_calls` are wrong tool template or `tool_choice="auto"` vs `"required"` (pattern #9); parser-selection and streaming state-machine debugging live in that skill.

Raw-output capture (`--enable-log-requests` + no `--tool-call-parser`/`--reasoning-parser`) determines which layer is at fault: if the model emits the expected tags/JSON, the prompt is fine and the problem is parser-side; if not, the template is misrendering.

## Multimodal template notes

Models use model-specific placeholders (`<image>`, `<|image_start|>`, etc.) — vLLM's internal placeholder is `<##IMAGE##>` / `<##AUDIO##>` / `<##VIDEO##>` (`renderers/chat_utils.py`).

- If request has images but template has no placeholder, vLLM **prepends** them to final prompt (`_get_full_multimodal_text_prompt()`). Some models tolerate this; others produce garbage.
- If template has more placeholders than media items: `ValueError: "Found more '<image>' placeholders in input prompt than actual multimodal data items."`
- `interleave_strings=True` (via `multimodal_config.interleave_mm_strings`) enables in-order substitution; default is prepend-all.
- **Double BOS in offline `LLM.chat()` for multimodal models — fixed v0.30.0 (#55288).** The multimodal processor's tokenization default is `add_special_tokens=True`; a template that emits `{{ bos_token }}` (Gemma-3, bundled `deepseek_vl2`/`deepseek_ocr` templates) then got a second BOS from the tokenizer. `LLM._preprocess_chat()` (`vllm/entrypoints/common/offline.py` at v0.32.0; `offline_utils.py` at v0.30.0) now defaults `add_special_tokens=False` for chat, matching `ChatCompletionRequest` on the online server; pass `tokenization_kwargs={"add_special_tokens": True}` to opt back in. `LLM.generate()` on raw prompts is unaffected — the processor default still applies there.

For Pixtral, Mistral-Small-3.1 multimodal, and other MM-tool-calling combinations, see `references/model-families.md`.

## When nothing works — full debugging workflow

Load `references/debugging.md`. The short version:

1. **Log the actual prompt.** `--enable-log-requests` + `VLLM_LOGGING_LEVEL=DEBUG` (or `--log-level DEBUG`, v0.31.0+); prompts are logged only at DEBUG. `--disable-log-requests` was removed in v0.17.0 and fails to parse. Compare against model card example. If they differ, template is wrong.
2. **Bypass vLLM.** Load the same tokenizer in a Python REPL, call `tokenizer.apply_chat_template(messages, add_generation_prompt=True)`, compare. If same bad output, template is wrong. If different, vLLM's kwarg forwarding is eating something.
3. **Capture raw model output.** Set `--tool-call-parser` to none, read what the model actually emits. Then work backward to pick the right parser.
4. **Pin versions.** Record `vllm --version`, `transformers.__version__`, model revision SHA. Many template bugs track a specific `tokenizer_config.json` commit — mention in bug reports.

## Code locations (for reading vLLM source)

Grep the symbol; line anchors per release are in `references/sources.md`.

- `vllm/renderers/chat_utils.py` — message parsing, multimodal placeholder injection, `ChatTemplateResolutionError`, `validate_chat_template()`. **Moved from `vllm/entrypoints/chat_utils.py` in v0.32.0** (#60522).
- `vllm/renderers/hf.py` — `resolve_chat_template()` (precedence), `safe_apply_chat_template()` (error surface), `resolve_chat_template_kwargs()` (allowlist), `resolve_chat_template_content_format()`, `_render_with_timeout()` (`VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT`).
- `vllm/renderers/params.py` — `ChatParams` dataclass.
- `vllm/reasoning/__init__.py` — registered reasoning parsers (38 names at v0.32.0).
- `vllm/transformers_utils/chat_templates/registry.py` — `_MODEL_TYPE_TO_CHAT_TEMPLATE_FALLBACK`, `get_chat_template_fallback_path()`.
- `vllm/entrypoints/openai/chat_completion/serving.py` — parser instantiation (`serving_chat.py` no longer exists).
- `examples/tool_chat_template_*.jinja` (**27** files at v0.30.0–v0.32.0) — ready-made tool templates per model family.

## Per-family deep-dive

When the operator names a model family, load `references/model-families.md` — it has per-family flag recipes, minimum commit SHAs, known bugs with issue numbers, and recovery strategies.

## Further reference material

- `references/model-families.md` — Qwen3, DeepSeek, GPT-OSS, Kimi-K2, Llama-4, Mistral, Gemma, Phi-4, GLM, Hermes/Granite/Hunyuan — with inline issue URLs.
- `references/debugging.md` — stepwise debugging workflow + full error-message catalog.
- `references/flags-matrix.md` — quick CLI-flag lookup per model.
- `references/sources.md` — verification log for external URLs/issues/PRs cited in this skill, with `Last verified` dates.

Last verified: 2026-10-18 against vLLM **v0.32.0** (see `references/sources.md` for per-ref status).
