# Source verification log

Tracks external references cited by this skill and their last-verified dates.
Lift Dim 9 staleness cap by keeping this table current: when adding a new
issue/PR/URL to the skill, probe it and add a row here.

Probe pattern: `gh pr view <N> --repo vllm-project/vllm --json state,mergedAt,title,closedAt,stateReason`

## Last sweep: 2026-08-11 against vLLM **v0.27.0** (prior sweeps 2026-07-21, 2026-05-28, 2026-04-24)

Latest vLLM release at sweep time was v0.27.1 (2026-08-11), a one-change patch
on v0.27.0 touching no chat-template code; every claim below was probed at
**v0.27.0** and is stamped there.

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM PR #27622 | https://github.com/vllm-project/vllm/pull/27622 | 2026-05-28 | MERGED 2025-10-28 | Whitelists HF standard chat-template kwargs (`add_generation_prompt`, `continue_final_message`, `enable_thinking`, etc.) through `**kwargs`. Required for Kimi-K2 fix. Shipped in v0.11.1+. |
| vLLM issue #25401 | https://github.com/vllm-project/vllm/issues/25401 | 2026-08-18 | CLOSED/COMPLETED 2025-10-09 | Mistral `--tokenizer-mode mistral` silently dropping `--chat-template` — **fixed upstream**. Warning-or-error behavior now present in recent vLLM. Verify on your version before assuming silent drop. |
| vLLM issue #28804 | https://github.com/vllm-project/vllm/issues/28804 | 2026-08-18 | CLOSED/NOT_PLANNED 2026-03-23 | DeepSeek V3.1 multi-turn whitespace accumulation. Not accepted upstream as a planned fix. Treat as won't-fix; apply client-side mitigation (strip leading whitespace) rather than expecting a vLLM-side fix. |
| vLLM issue #22578 | https://github.com/vllm-project/vllm/issues/22578 | 2026-08-18 | CLOSED/NOT_PLANNED 2026-01-23 | gpt-oss `/v1/chat/completions` tool calling. Closed as not-planned — `/v1/responses` (Harmony) is the supported path for gpt-oss tool calling and will remain so. |
| vLLM issue #23015 | https://github.com/vllm-project/vllm/issues/23015 | 2026-08-18 | CLOSED/NOT_PLANNED 2026-04-20 | gpt-oss template "appears hard-coded". Closed as not-planned — operator-supplied `--chat-template` is intentionally overridden for gpt-oss when the harmony path is used. Use `/v1/responses`. |
| vLLM issue #39392 | https://github.com/vllm-project/vllm/issues/39392 | 2026-07-21 | **OPEN** | Gemma-4 `<pad>` tokens. **Confirmed still reproducing on `vllm/vllm-openai:v0.25.1-x86_64-cu129-ubuntu2404` on 2026-07-20** — the day before this sweep, so this is a fresh datapoint, not an assumption of continuity. Trigger narrowed by the reporter: **parallel *tool-call* requests**, not concurrency generally; Gemma-4 is otherwise stable under load, and serialising tool calls avoids it. Ampere hardware (RTX 3090, A6000). `--max-num-seqs 1` remains the blunt workaround. |
| vLLM issue #38855 | https://github.com/vllm-project/vllm/issues/38855 | 2026-07-21 | **CLOSED/COMPLETED 2026-06-15 — a real fix, not a stale close** | Passed the freshen-patterns §3.0 check: the closing comments name the remedy ("we published a new vLLM gemma4 container image and the model's chat template was updated on HuggingFace"), so this is a genuine resolution. **But the fix is two-sided**, and that is the operationally important part: it requires *both* the newer vLLM image *and* a re-pulled model whose `chat_template` postdates ~2026-04-10. A vLLM upgrade alone leaves a stale mirrored/air-gapped model snapshot broken. Keep the `skip_special_tokens: false` workaround until both halves are current. |
| vLLM issue #39614 | https://github.com/vllm-project/vllm/issues/39614 | 2026-05-28 | CLOSED/COMPLETED 2026-04-25 | GLM-5.1-FP8 `--chat-template-content-format auto` misroutes tool result — **fixed upstream**. `--chat-template-content-format openai`/`string` workaround only needed on vLLM before the fix. |
| vLLM issue #39611 | https://github.com/vllm-project/vllm/issues/39611 | 2026-05-28 | CLOSED/COMPLETED 2026-04-12 | GLM-5.1-FP8 tool results ignored on `/v1/chat/completions` but work on `/v1/completions` — **fixed upstream**. Tool results now render on `/v1/chat/completions` in patched vLLM. (Previously only listed under not-re-probed; issue is GLM-5.1-FP8, not GLM-4.7.) |

## 2026-08-11 sweep — findings

| Claim | Was | Is (v0.27.0) | Probe |
|---|---|---|---|
| Response field for reasoning | SKILL.md pattern 15: "vLLM settled on `reasoning_content` (#28472)" | **Backwards.** Response field is `reasoning` — `ChatMessage.reasoning` at `chat_completion/protocol.py:71`, `DeltaMessage.reasoning` at `engine/protocol.py:397`. Request side still accepts `reasoning_content` and normalizes it (RFC #27755); the normalizer's own comment calls `reasoning_content` deprecated. This contradicted the sibling `vllm-reasoning-parsers` skill, which was right. | `git show v0.27.0:vllm/entrypoints/openai/chat_completion/protocol.py \| grep -n reasoning` |
| `--reasoning-parser gpt_oss` (flags-matrix.md GPT-OSS recipe) | copy-paste serve command | **Not a registered name.** `grep -c '"gpt_oss"'` on `vllm/reasoning/__init__.py` returns 0 at v0.25.1, v0.26.0 *and* v0.27.0; the registered name is `openai_gptoss`. The command as written fails at startup. | `git show v0.27.0:vllm/reasoning/__init__.py \| grep -c '"gpt_oss"'` |
| `vllm/entrypoints/openai/serving_chat.py:91-182` | cited in Code locations | **File does not exist.** Parser instantiation lives in `vllm/entrypoints/openai/chat_completion/serving.py`. | `git ls-tree v0.27.0 -- vllm/entrypoints/openai/serving_chat.py` (empty) |
| `hf.py` line anchors | `96-145`, `407-435`, `460-505`, error at `477` | `resolve_chat_template()` **257**; `resolve_chat_template_content_format()` **558**; `resolve_chat_template_kwargs()` **633**; `safe_apply_chat_template()` overloads **665-699**, impl to ~728, `ChatTemplateResolutionError` raise at **718**. Line 477 is now unrelated system-message consolidation code. | `git show v0.27.0:vllm/renderers/hf.py` |
| `examples/tool_chat_template_*.jinja` count | "27 files" | **26**, at v0.25.1 *and* v0.27.0 — unchanged, so the 27 was never right. | `git ls-tree --name-only v0.27.0 examples/ \| grep -c tool_chat_template` |
| Bundled fallback families | "~10 … blip-2, chameleon, clip, colpali, deepseek_ocr/ocr2/vl_v2, **fuyu**, minicpmv, paligemma, **qwen**, siglip/siglip2" | **13 model types / 7 jinja files.** `fuyu` **removed** (Fuyu + Persimmon dropped in v0.26.0, #48096) along with `template_fuyu.jinja`; `unlimited-ocr` and `minicpmv4_6` present; **no `qwen` entry at either tag**. | `git show {v0.25.1,v0.27.0}:vllm/transformers_utils/chat_templates/registry.py` |
| "As of transformers v4.44…" error string | quoted in SKILL.md + debugging.md | **Correct and current — deliberately NOT changed.** vLLM still raises this verbatim at v0.27.0 (`hf.py:718`). It names the *transformers release that removed default templates*, not a version requirement. The runtime floor is separately `transformers >= 5.5.3`, `tokenizers >= 0.21.1` (`requirements/common.txt`) — **unchanged from v0.25.1**. A guard note was added so a future pass doesn't "modernize" the quote. | `git grep -n "v4.44" v0.27.0 -- vllm/renderers/hf.py`; `git show v0.27.0:requirements/common.txt` |
| PR #47844 — `continue_final_message` renderer sentinel | not covered | **MERGED 2026-07-08** (v0.26.0). Rust frontend only: previously the value was passed to the chat template and "almost no Hugging Face chat template actually observes this value, so it was a no-op". Now the Rust renderer appends a sentinel to the last message and strips it from the rendered result, porting Transformers-v5 semantics without template awareness. The Rust Harmony renderer explicitly errors: "Harmony renderer does not support continue_final_message". The Python path still just forwards the kwarg. Mutual exclusion with `add_generation_prompt` enforced at `chat_completion/protocol.py:964`. | `gh pr view 47844 -R vllm-project/vllm`; `git grep -n continue_final_message v0.27.0 -- rust/ vllm/renderers/` |

## Not re-probed this sweep (budget exhausted, prior-state assumed)

These refs were cataloged but not re-probed — verify on next sweep. Most are
either (a) historical bug references whose workarounds are baked into the
skill even if the issue is since closed, or (b) model-card discussions that
rarely flip state.

- vLLM #12999, #13978, #14682, #14734, #14884, #15403, #16292, #16463, #16482,
  #16510, #18090, #18141, #18819, #19513, #19545, #20341, #20611, #21711,
  #22403, #22718, #33654, #37909, #39043
- HuggingFace discussions: DeepSeek-R1 #144, gpt-oss-20b #160 / #218,
  gpt-oss-120b #69, Llama-4-Scout #78, Pixtral #22, Mistral-Small-3.1 #49,
  gemma-4-31B #28
- vLLM blog: https://vllm.ai/blog/Kimi-K2-Accuracy (Oct 2025)
- HF blog: https://huggingface.co/blog/qwen-3-chat-template-deep-dive
- discuss.vllm.ai threads: DeepSeek-V3 tool_choice, Llama4-Maverick LangGraph
- MoonshotAI/Kimi-K2 #41 (Kimi-K2 upstream repo)
- ms-swift #5836 (ModelScope downstream harness)

## vLLM source paths cited (subject to code-drift)

These paths are cited inline in SKILL.md with line-number ranges. Line numbers
drift on every vLLM release; treat the range as illustrative, not canonical.
Do **not** re-probe unless a user reports "that line has unrelated code".

- `vllm/renderers/hf.py` — `resolve_chat_template()`, kwarg allowlist
- `vllm/renderers/params.py` — `ChatParams` dataclass
- `vllm/entrypoints/chat_utils.py` — multimodal placeholder injection, ChatTemplateResolutionError
- `vllm/entrypoints/openai/chat_completion/serving.py` — parser instantiation (the old `serving_chat.py` path is gone)
- `vllm/reasoning/__init__.py` — registered reasoning parsers (29 names at v0.27.0)
- `vllm/transformers_utils/chat_templates/registry.py` — bundled fallback lookup
- `examples/tool_chat_template_*.jinja` (26 files)
