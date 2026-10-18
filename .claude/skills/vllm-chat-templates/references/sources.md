# Source verification log

Freshened: 2026-10-18 — every row probed at v0.32.0 (issue/PR states via one GraphQL batch, HF discussions via the Hub API, URLs curled, paths/symbols/line anchors at the v0.32.0 tag). Moved: `chat_utils.py` relocated to `vllm/renderers/`, `offline_utils.py` to `entrypoints/common/offline.py`; transformers pin now `>= 5.16.1, < 5.20.0`; fallback registry 14 model types; `assistant_tokens_mask` removed; chat-template render timeout added; `oss-harmony` embeds the gpt-oss vocab; pre-existing broken `--disable-log-requests`, `gpt_oss` and `minimax_m1` references corrected.

Tracks external references cited by this skill and their last-verified dates.
Lift Dim 9 staleness cap by keeping this table current: when adding a new
issue/PR/URL to the skill, probe it and add a row here.

Probe pattern: `gh pr view <N> --repo vllm-project/vllm --json state,mergedAt,title,closedAt,stateReason`

## 2026-10-18 — v0.31.0 / v0.32.0 freshen

Probed against `v0.30.0..v0.32.0` and the `v0.32.0` tag tree (local clone, read via refs only).

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM PR #50300 | https://github.com/vllm-project/vllm/pull/50300 | 2026-10-18 | MERGED 2026-09-30, first in v0.32.0 (not in v0.31.0) | Python: `_render_with_timeout()` (`vllm/renderers/hf.py:992`), `VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT` default `30` (`vllm/envs.py:816`), `<= 0` disables; Responses API `validate_chat_template()` gate (`responses/serving.py:340`). Rust: `DEFAULT_TEMPLATE_FUEL = 500_000` (`rust/src/chat/src/renderer/hf/template.rs:35`). The PR body and v0.32.0 notes also promise static AST validation — **absent from the tag** (no validator in `hf.py`). The GHSA id they cite, GHSA-4hhp-h66f-j5j7, resolves via the advisories API to an unrelated published SSRF advisory (MiMoV2Omni, CVE-2026-73560), so the skill cites the PR only. |
| vLLM PR #57520 | https://github.com/vllm-project/vllm/pull/57520 | 2026-10-18 | MERGED 2026-09-18, in v0.31.0 | Removes `return_assistant_tokens_mask` on `/render` and the `assistant_tokens_mask` field. |
| vLLM PR #60522 | https://github.com/vllm-project/vllm/pull/60522 | 2026-10-18 | first in v0.32.0 (commit `c1692c85f1`) | `vllm/entrypoints/chat_utils.py` → `vllm/renderers/chat_utils.py`. Anchors at v0.32.0 (2333 lines): `ChatTemplateResolutionError` 90, placeholder map 99-101, `validate_chat_template()` 1457, `_get_full_multimodal_text_prompt()` 1569, empty-`tool_calls` drop 2165-2167. |
| vLLM PRs #57387 / #59614 / #59796 | https://github.com/vllm-project/vllm/pull/59614 | 2026-10-18 | all MERGED | `requirements/common.txt`: v0.30.0 `transformers >= 5.10.4`; v0.31.0 `>= 5.10.4, < 5.18.0`; v0.32.0 `>= 5.16.1, < 5.20.0`, `tokenizers >= 0.23.2` (was `>= 0.21.1` through v0.31.0). v0.27.0/v0.28.0 `>= 5.5.3`, v0.29.0 `>= 5.10.4` re-read. |
| vLLM PR #55128 | https://github.com/vllm-project/vllm/pull/55128 | 2026-10-18 | MERGED 2026-09-27, in v0.31.0 | `oss-harmony >= 0.0.11` replaces `openai-harmony`; same `openai_harmony` import, vocab embedded so no `TIKTOKEN_ENCODINGS_BASE` download. PR notes `gpt-oss` on PyPI still depends on `openai-harmony`, which overwrites the module if co-installed. |
| vLLM PR #45993 | https://github.com/vllm-project/vllm/pull/45993 | 2026-10-18 | commit `d14e551a53`, first in v0.24.0 | Deleted `examples/tool_chat_template_minimax_m1.jinja`. Tool-template set at v0.30.0 and v0.32.0: 27 files, identical (`git ls-tree`); `apertus` added v0.22.0 (#41154), `muse_glimmer` v0.28.0 (#51655). |
| vLLM PR #35723 | https://github.com/vllm-project/vllm/pull/35723 | 2026-10-18 | commit `792a74b973`, first in v0.17.0 | Removed `--disable-log-requests`; `--enable-log-requests` (BooleanOptionalAction) logs prompts at DEBUG (`vllm/engine/arg_utils.py:3206`). `--log-level` exists from v0.31.0 (#57205), absent at v0.30.0. |
| vLLM PR #35024 | https://github.com/vllm-project/vllm/pull/35024 | 2026-10-18 | commit `2676ab1e0b`, first in v0.22.0 | Removed `vllm.transformers_utils.tokenizer.get_tokenizer`; current import `vllm.tokenizers.get_tokenizer` (`vllm/tokenizers/registry.py:196`). |
| vLLM PR #13025 | https://github.com/vllm-project/vllm/pull/13025 | 2026-10-18 | commit `fc6485d277` 2025-02-11, first in v0.7.3 (not v0.7.2) | Closes #12999 (reporter on v0.7.2, R1-Distill output carries only `</think>`). `deepseek_r1` parser assumes reasoning starts at output position 0 when `<think>` is absent; still in `BaseThinkingReasoningParser.extract_reasoning` (`vllm/reasoning/basic_parsers.py:168-176`) and the R1 streaming override at v0.14.0 and v0.32.0. |
| Fallback registry | `vllm/transformers_utils/chat_templates/registry.py` | 2026-10-18 | v0.32.0 | 14 model types, lines 25-40; `unlimited_ocr` (#61590) and `minicpmv4_7` (#58674) added since v0.30.0; 7 `.jinja` files unchanged. |
| `hf.py` anchors | `vllm/renderers/hf.py` | 2026-10-18 | v0.32.0, 1389 lines | `resolve_chat_template` 265, `resolve_chat_template_content_format` 632, `_resolve_chat_template_kwargs` 680, `_get_hf_base_chat_template_params` 695, `resolve_chat_template_kwargs` 715 (reserved 723, filter 742-743), `safe_apply_chat_template` 759-842 (raise 797). |
| Response fields | `vllm/entrypoints/openai/chat_completion/protocol.py` | 2026-10-18 | v0.32.0 | `ChatMessage.reasoning` :79; `DeltaMessage.reasoning` moved to `vllm/entrypoints/generate/base/protocol.py:359`; `continue_final_message`/`add_generation_prompt` exclusion :1026. Reasoning parser registry: 38 names, `openai_gptoss` present, `gpt_oss` absent. |
| vLLM PR #38579 | https://github.com/vllm-project/vllm/pull/38579 | 2026-10-18 | MERGED 2026-04-19, first in v0.20.0 | Named as the fix in #33654 (Kimi-K2.5 empty content). |
| vLLM PR #18879 | https://github.com/vllm-project/vllm/pull/18879 | 2026-10-18 | MERGED 2025-05-31, first in v0.9.1 | Fix for #18819, reporter-confirmed on v0.9.1. |

Not applied (out of scope — output parsing or pooling): `--tool-call-parser hf` / `--reasoning-parser hf` reading `response_template` (#58604, #58602, #59005; `vllm-tool-parsers` / `vllm-reasoning-parsers`); Rust `qwen3_xml` now an alias of `qwen3_coder` plus new `qwen3_json` (#60136; `vllm-tool-parsers`); tool-parser compatibility check at startup (#59749); `zerank2.jinja` reranker score template (#60415); `mm_payload` / `return_mm_kwargs` deprecation on render (#61427); `tokenizer_mode="slow"` removed (#58545 — the skill never recommends it).

## 2026-09-23 — v0.30.0 release-note items added

Not a full sweep; these are new citations pulled from the v0.30.0 release notes and probed against the `v0.29.0..v0.30.0` commit range and the `v0.30.0` tag tree.

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM PR #53824 | https://github.com/vllm-project/vllm/pull/53824 | 2026-09-23 | MERGED 2026-09-10 | `_detect_content_format()` (`vllm/renderers/hf.py`) now traces macro parameters back to `message['content']`; previously macro-wrapped content mis-detected as `string`. |
| vLLM PR #55288 | https://github.com/vllm-project/vllm/pull/55288 | 2026-09-23 | MERGED 2026-09-04 | Fixes double BOS in `LLM.chat()` for multimodal models; `_preprocess_chat()` (`vllm/entrypoints/offline_utils.py`) now defaults `add_special_tokens=False`, matching the online `ChatCompletionRequest` default. |
| vLLM PR #56017 | https://github.com/vllm-project/vllm/pull/56017 | 2026-09-23 | MERGED 2026-09-11 | Warns when serving an original Qwen3/Qwen3-VL reranker without `--chat-template`; names `examples/pooling/score/template/qwen3_reranker.jinja` / `qwen3_vl_reranker.jinja` (`vllm/entrypoints/pooling/scoring/io_processor.py`). |
| vLLM PR #56378 | https://github.com/vllm-project/vllm/pull/56378 | 2026-09-23 | MERGED 2026-09-12 | Rust frontend now parses `{% generation %}` blocks (`rust/src/chat/src/renderer/hf/generation.rs`), needed for `return_assistant_tokens_mask` on templates using that convention. |

Not applied (cap): vLLM PR #53762 (packaging-only — bundled fallback `.jinja` files added to `setup.py` `package_data`; no operator-facing flag/config change) and vLLM PR #54539 / #54692 (`assistant_tokens_mask` and token-offset truncation alignment on the `/v1/chat/completions/render` endpoint — training-data-generation path, outside this skill's prompt-rendering-for-serving scope).

## Last sweep: 2026-08-11 against vLLM **v0.27.0** (prior sweeps 2026-07-21, 2026-05-28, 2026-04-24)

Latest vLLM release at sweep time was v0.27.1 (2026-08-11), a one-change patch
on v0.27.0 touching no chat-template code; every claim below was probed at
**v0.27.0** and is stamped there.

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM PR #27622 | https://github.com/vllm-project/vllm/pull/27622 | 2026-05-28 | MERGED 2025-10-28 | Whitelists HF standard chat-template kwargs (`add_generation_prompt`, `continue_final_message`, `enable_thinking`, etc.) through `**kwargs`. Required for Kimi-K2 fix. Shipped in v0.11.1+. |
| vLLM issue #25401 | https://github.com/vllm-project/vllm/issues/25401 | 2026-09-15 | CLOSED/COMPLETED 2025-10-09 | Mistral `--tokenizer-mode mistral` silently dropping `--chat-template` — **fixed upstream**. Warning-or-error behavior now present in recent vLLM. Verify on your version before assuming silent drop. |
| vLLM issue #28804 | https://github.com/vllm-project/vllm/issues/28804 | 2026-09-15 | CLOSED/NOT_PLANNED 2026-03-23 | DeepSeek V3.1 multi-turn whitespace accumulation. Not accepted upstream as a planned fix. Treat as won't-fix; apply client-side mitigation (strip leading whitespace) rather than expecting a vLLM-side fix. |
| vLLM issue #22578 | https://github.com/vllm-project/vllm/issues/22578 | 2026-09-15 | CLOSED/NOT_PLANNED 2026-01-23 | gpt-oss `/v1/chat/completions` tool calling. Closed as not-planned — `/v1/responses` (Harmony) is the supported path for gpt-oss tool calling and will remain so. |
| vLLM issue #23015 | https://github.com/vllm-project/vllm/issues/23015 | 2026-09-15 | CLOSED/NOT_PLANNED 2026-04-20 | gpt-oss template "appears hard-coded". Closed as not-planned — operator-supplied `--chat-template` is intentionally overridden for gpt-oss when the harmony path is used. Use `/v1/responses`. |
| vLLM issue #39392 | https://github.com/vllm-project/vllm/issues/39392 | 2026-10-18 | **OPEN** — no activity since 2026-07-20, no linked fix in v0.31.0/v0.32.0 notes | Gemma-4 `<pad>` tokens. **Confirmed still reproducing on `vllm/vllm-openai:v0.25.1-x86_64-cu129-ubuntu2404` on 2026-07-20** — the day before this sweep, so this is a fresh datapoint, not an assumption of continuity. Trigger narrowed by the reporter: **parallel *tool-call* requests**, not concurrency generally; Gemma-4 is otherwise stable under load, and serialising tool calls avoids it. Ampere hardware (RTX 3090, A6000). `--max-num-seqs 1` remains the blunt workaround. |
| vLLM issue #38855 | https://github.com/vllm-project/vllm/issues/38855 | 2026-09-15 | **CLOSED/COMPLETED 2026-06-15 — a real fix, not a stale close** | Passed the freshen-patterns §3.0 check: the closing comments name the remedy ("we published a new vLLM gemma4 container image and the model's chat template was updated on HuggingFace"), so this is a genuine resolution. **But the fix is two-sided**, and that is the operationally important part: it requires *both* the newer vLLM image *and* a re-pulled model whose `chat_template` postdates ~2026-04-10. A vLLM upgrade alone leaves a stale mirrored/air-gapped model snapshot broken. Keep the `skip_special_tokens: false` workaround until both halves are current. |
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

## Cataloged refs — states probed 2026-10-18

vLLM (GraphQL batch): CLOSED/COMPLETED #12999, #14682, #14734, #14884, #16292, #16510, #18819 (fixed v0.9.1, #18879), #19545, #20341, #22403, #27755, #28472, #9059, #33654 (fixed by #38579), #39043 (maintainer: resolved on v0.24.0+); CLOSED/NOT_PLANNED stale-bot, no fix — #13978, #15403, #16482, #18090, #18141, #19513, #20611, #21711, #22718. **#37909** CLOSED/COMPLETED 2026-06-25 by the reporter ("lost track"), its fix PR #38100 closed unmerged — treat as unfixed; the skill's "omit or use `low`" stands. MERGED: #16463, #25794, #27565. Discussion #12708 live.

HF Hub API: DeepSeek-R1 #144 closed; gemma-4-31B-it #28 open; Llama-4-Scout #78 merged PR; Mistral-Small-3.1 #49 closed; pixtral-12b #22 open (repo now `mistral-experimental/pixtral-12b`, old URL redirects); gpt-oss-120b #69, gpt-oss-20b #160 / #218 open.

Other: modelscope/ms-swift #5836 OPEN; MoonshotAI/Kimi-K2 #41 OPEN; vLLM blog Kimi-K2-Accuracy 200 (redirects to `/blog/2025-10-28-kimi-k2-accuracy`); HF blog qwen-3-chat-template-deep-dive 200; both discuss.vllm.ai threads 200; docs.vllm.ai tool_calling 200.

## vLLM source paths cited (v0.32.0)

- `vllm/renderers/hf.py` — `resolve_chat_template()`, kwarg allowlist, render timeout
- `vllm/renderers/params.py` — `ChatParams` dataclass
- `vllm/renderers/chat_utils.py` — multimodal placeholder injection, `ChatTemplateResolutionError` (was `vllm/entrypoints/chat_utils.py` through v0.31.0)
- `vllm/entrypoints/openai/chat_completion/serving.py` — parser instantiation (the old `serving_chat.py` path is gone)
- `vllm/entrypoints/common/offline.py` — `LLM._preprocess_chat()` (was `vllm/entrypoints/offline_utils.py` at v0.30.0)
- `vllm/reasoning/__init__.py` — registered reasoning parsers (38 names)
- `vllm/transformers_utils/chat_templates/registry.py` — bundled fallback lookup
- `examples/tool_chat_template_*.jinja` (27 files)
