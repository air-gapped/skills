# Sources — vllm-gemma-4-31b

Freshened: 2026-10-18 — every row probed at v0.32.0; both chat templates byte-identical to the last pass. Moved: fact #1 (Gemma 4 backend selection is per-platform, per-layer FA3/FA4 on SM90 + FP8 KV from v0.31.0, not forced Triton), #50477 is not version-gated (gemma4 parser skips grammar for named/`required` since v0.24.0), #50158's acceptance collapse was draft-vocab coverage, Gemma-4 MTP is in stable since v0.21.0, and SM90 WNA16 now prefers Humming over Marlin; #50159 still gates the 0.25.1 ceiling.

External references cited by SKILL.md and `references/*.md`. Each row carries
the upstream URL, classification, last verification date, and pinned version
or git ref where applicable. Re-probe via `/skill-improver freshen vllm-gemma-4-31b`.

## Authoritative model + template sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r01 | https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja | hf-model | 2026-10-18 | sha256:`ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4` (18683 B). **2026-10-18: HELD** — byte-identical again; repo HEAD still `842da379` (2026-07-20, `response_template` added to tokenizer_config.json). Hash chain (evidence of drift rate, not a pin): `94899c0f…` 16934 B 2026-04-30 → `36e3a42e…` 17466 B 2026-05-28 → this, held 2026-08-11, 2026-09-22, 2026-10-18. Google header: *"Published: 2026-07-09 — Fixed tool-calling loops, turn closures, and thinking content-ordering."* Open template PRs on the repo: #137, #140, #147, #148 (all unmerged). |
| r02 | https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit | hf-model | 2026-10-18 | Template still hashes `94899c0f…25bff413` (16934 B), byte-identical to the 2026-04-30 canonical; `diff` vs r01 still exactly **114** lines. HEAD `6f1b616c` (single "Squash history of main" commit, 2026-07-21; sibling `gemma-4-31B-it-qat-AWQ-INT4` HEAD `e0814036`, same squash). Its tokenizer_config.json has no `response_template` (the google base does). Pre-squash history (README-only `Fix Model Size` commit 2026-07-03; template from the 2026-04-30 upload) no longer exists in the repo history. HF 30-day downloads 67,280 on 2026-10-18. |
| r03 | https://huggingface.co/RedHatAI/gemma-4-31B-it-speculator.eagle3 | hf-model | 2026-10-18 | HEAD `28a1c8b4`, `lastModified` 2026-04-14 — untouched. Ships no `chat_template.jinja` (siblings: README, config.json, config.py, model.safetensors). `config.json`: `draft_vocab_size: 32000` — the basis of the non-English acceptance-collapse cause (r14). Vanilla EAGLE3, no P-EAGLE prep tokens. |

## vLLM engine sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r04 | https://github.com/vllm-project/vllm | github | 2026-10-18 | **v0.32.0 latest (2026-10-18)**; v0.31.0 (10-05), v0.30.0 (09-22), v0.29.0 (09-09), v0.28.0 (08-26), v0.27.1 (08-11). v0.31.0/v0.32.0 notes walked for Gemma-4 scope: #53175 (SM90 FP8-KV per-layer FA3/FA4, v0.31.0), #56997 (Humming before Marlin on SM90, v0.32.0), #58604 (`hf` response_template parser — not adopted), #57263 (Gemma4 DSpark adaptive verification — DSpark 31B still blocked by r15). #60156 (Triton FP8 softmax underflow fix) is in the v0.32.0 tag but not its notes. None closes r12/r13. Audit baseline remains v0.20.0; `bench-numbers.md` not re-run. |
| r05 | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/engine/arg_utils.py | github-source | 2026-10-18 | v0.32.0 (blob `ea628467e0b3609014a4a74b1dda49737263a306`, 3223 lines; `def get_batch_defaults` at line 2894). Tiers: `device_memory >= 160*GiB_bytes` → 16384/16384 tokens, 1024 seqs (B200/B300; added by #51726, first in v0.28.0); then `>= 70*GiB_bytes and "a100" not in device_name` → 16384/8192, 1024 — H100 and H200 still share it; then 8192/2048, 256; plus the `is_tpu()` sub-branch. A100 carve-out comment (r10) survives verbatim. |
| r06 | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/v1/spec_decode/llm_base_proposer.py | github-source | 2026-10-18 | v0.32.0 (blob `79be2e8a4d86ec3db9bb5e1d850b31b039a32296`, 1860 lines). Check order: `dflash_config["mask_token_id"]`, `mask_token_id`, `dspark_noise_token_id`, `pard_token`, `ptd_token_id` (lines 364-380); sets `self.parallel_drafting_token_id`, else the five-name `ValueError`. Unchanged since v0.30.0. |

## vLLM issue / PR citations

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r07 | https://github.com/vllm-project/vllm/issues/35467 | github-issue | 2026-10-18 | still OPEN — "non-optimal performance of `linear` for medium batches". Last human comment 2026-06-08 (*"FI impl is ready"*); `stale` label applied 2026-09-09 by the bot, not yet auto-closed. A stale close would not be a fix (§3.0). |
| r08 | https://github.com/vllm-project/vllm/issues/22780 | github-issue | 2026-10-18 | **CLOSED `NOT_PLANNED` 2025-12-14 by the stale bot** (*"automatically closed due to inactivity"*), NOT by a fix. The BnB-4bit concurrency regression is unaddressed upstream, which supports the AWQ-over-BnB recommendation. |
| r09 | https://github.com/vllm-project/vllm/issues/6801 | github-issue | 2026-10-18 | OPEN, labels `RFC` + **`keep-open`** (stale applied 2024-11-08, removed 2024-11-20 when a maintainer pinned it). Will not auto-close. Supports the Pareto-knob framing. |
| r10 | https://github.com/vllm-project/vllm/pull/17885 | github-pr | 2026-10-18 | MERGED 2025-05-11 — "[Perf] Use small max_num_batched_tokens for A100". Its `NOTE(Kuntai)` comment survives verbatim in v0.32.0. |

## Gemma-4 regression tracker (probed 2026-10-18 at v0.32.0)

| Ref | URL | Classification | State on 2026-10-18 | Notes |
|---|---|---|---|---|
| r11 | https://github.com/vllm-project/vllm/issues/49955 | github-issue | **OPEN** | Trailing `<turn|>`. Reproduces with MTP disabled; discriminator is `stream=true` (reporter matrix 2026-07-31); config-sensitive. Root-cause fix **PR #52430** merged 2026-08-18, first stable tag **v0.29.0** (tag ancestry); `chat_kwargs.get("enable_thinking", False)` at `vllm/parser/gemma4.py:425` in v0.32.0. Last comment 2026-08-23 (fix on main, not yet released at that time); no reporter confirmation on a release. #50964 closed unmerged; #50263 OPEN, reporter says it does not fix it. |
| r12 | https://github.com/vllm-project/vllm/issues/50477 | github-issue | **OPEN** | Named / `required` `tool_choice` unenforced: HTTP 200, `finish_reason: "tool_calls"`, prose in `content`, `tool_calls: null`. Mechanism in code: `Gemma4EngineToolParser.supports_required_and_named = False` (`vllm/tool_parsers/gemma4_engine_tool_parser.py:15`, v0.32.0) and its `adjust_request` skips the JSON grammar, so `vllm/parser/abstract_parser.py` treats named/required as `auto`. Introduced by #45795 (first stable tag v0.24.0); identical at v0.25.1, v0.26.0, v0.30.0, v0.32.0 — so 0.25.1 is affected too. 2026-08-15 comment: task-description system prompts trigger the prose fallback, filler text does not. Fix PR #51524 OPEN (REVIEW_REQUIRED, updated 2026-10-12). |
| r13 | https://github.com/vllm-project/vllm/issues/50159 | github-issue | **OPEN** | MRv2 over-reports available KV. Two independent A/B runs localise it to **CUDA-graph capture headroom accounting** — MRv1 reserves ~0.65 GiB vs MRv2 ~0.12 GiB on Gemma-4 31B / 2× RTX 3090; gap ~0 under `--enforce-eager`. **No fix PR.** Related #49224 was closed 2026-08-24 by a maintainer with no linked commit, and a 2026-08-29 comment reports the OOM still occurring after the close — treat as unfixed. #49233 closed unmerged. Opt-out at v0.32.0: `VLLM_USE_V2_MODEL_RUNNER` (`vllm/envs.py`, read in `VllmConfig.use_v2_model_runner`, `vllm/config/vllm.py`). |
| r14 | https://github.com/vllm-project/vllm/issues/50158 | github-issue | **OPEN** | EAGLE embed_tokens sharing decided per-rank. Fix **PR #50280 OPEN**. The reporter's own 2026-08-01 follow-ups: #50280 makes the ranks agree but acceptance stays at 0.454/0.461 per K=3 draft; the collapse is draft-vocab coverage — the eagle3 drafter's `draft_vocab_size = 32000` (r03) covers 95.7% of English but 19.4% of the Russian generated output. |
| r15 | https://github.com/vllm-project/vllm/issues/49475 | github-issue | **OPEN** | `RedHatAI/gemma-4-31B-it-speculator.dspark` still fails to load (repo HEAD `0026c7d1`, 2026-07-21). v0.31.0's Gemma4 DSpark adaptive verification (#57263) does not reference it. |
| r16 | https://github.com/vllm-project/vllm/pull/46837 | github-pr | **MERGED** 2026-07-25 | ViT CUDA graph for Gemma-4; `SupportsEncoderCudaGraph` on `Gemma4ForConditionalGeneration`. First stable tag v0.27.0. |
| r17 | https://github.com/vllm-project/vllm/pull/47216 | github-pr | **MERGED** 2026-07-16 | Gemma4-**12B** DSpark draft model (`deepseek-ai/dspark_gemma4_12b_block7`), first stable tag v0.26.0. Does not unblock r15. |
| r18 | https://github.com/vllm-project/vllm/blob/v0.27.0/examples/tool_chat_template_gemma4.jinja | github-source | 2026-10-18 | Line 180: `{%- set enable_thinking = enable_thinking | default(false) -%}` — same line, same text at v0.32.0. Half of the r11 root cause. |
| r19 | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/parser/gemma4.py | github-source | 2026-10-18 | v0.27.0 line 403: `chat_kwargs.get("enable_thinking", True)` — the pre-fix default. v0.32.0 line 425: `chat_kwargs.get("enable_thinking", False)`; `adjust_initial_state_from_prompt` at line 506; the `(ParserState.TOOL_PREAMBLE, "COLON")` transition (r21) at line 360. |
| r20 | https://github.com/vllm-project/vllm/pull/53147 | github-pr | **MERGED** 2026-08-31, first stable tag v0.30.0 | `[Kernel][Gemma4] Prune Triton sliding-window tiles for multimodal prefixes` (`vllm/v1/attention/ops/triton_unified_attention.py`). Upstream: up to 3-4x E2E / ~4x prefill on a Gemma-4 multimodal workload. Applies to the TRITON_ATTN path, which v0.31.0+ still uses for multimodal-prefix requests (r22). |
| r21 | https://github.com/vllm-project/vllm/pull/53444 | github-pr | **MERGED** 2026-09-15, first stable tag v0.30.0 | `[Bugfix] Handle bare and malformed tool call openers in Gemma4 parser`. Adds the `(TOOL_PREAMBLE, "COLON") -> TOOL_NAME` transition to `gemma4_config()` (`vllm/parser/gemma4.py`). |
| r22 | https://github.com/vllm-project/vllm/pull/53175 | github-pr | **MERGED** 2026-09-24, first stable tag v0.31.0 | Gemma4 FP8-KV FA4 head-dim-512 backend selection. `Gemma4Config.verify_and_update_config` (`vllm/model_executor/models/config.py`, v0.32.0): FA4 available + `max_head_dim <= 512` → on SM90 with FP8 KV logs `Using per-layer FA3/FA4 selection for FP8 KV cache on SM90` (FA3 for 256 causal, FA4 for 512 causal, TRITON_ATTN for mm-prefix via the composite from #56305, v0.30.0); otherwise `Using FA4 for all layers`; FA4 unavailable → `FA4 not available, forcing TRITON_ATTN backend`. PR body: forcing FA4 with FP8 KV on SM90 for the 256 layers corrupts output, hence FA3 there. History: #42175 (unified FA4, first tag v0.24.0), #48666 (FA4 FP8, v0.28.0) reverted by #52987. |
| r23 | https://github.com/vllm-project/vllm/pull/60156 | github-pr | **MERGED** 2026-10-08, in the v0.32.0 tag (not its notes) | `[Bugfix][Attention] Preserve small FP8 softmax weights in Triton attention` — scales `P` before the FP8 cast in `triton_unified_attention.py` so small probabilities no longer underflow to zero with an FP8 KV cache. |
| r24 | https://github.com/vllm-project/vllm/pull/56997 | github-pr | **MERGED** 2026-10-06, first stable tag v0.32.0 | `[Quantization] Prefer Humming before Marlin backends on SM90`. `prioritize_humming()` (`vllm/model_executor/layers/quantization/utils/humming/priority.py`) moves Humming directly ahead of Marlin on compute capability 90; CUDA `_POSSIBLE_KERNELS` order at v0.32.0 is CutlassW4A8, Machete, Marlin, …, Humming before the move. `humming-kernels[cu13]==0.1.17` in `requirements/cuda.txt`. Log line: `Using %s for CompressedTensorsWNA16`. |
| r25 | https://github.com/vllm-project/vllm/pull/41745 | github-pr | **MERGED** 2026-05-06, first stable tag v0.21.0 | `[Spec Decode] Add Gemma4 MTP speculative decoding support` (`vllm/v1/spec_decode/gemma4.py`, `Gemma4Proposer`). MRv2 variant #43241 merged 2026-06-04, first stable tag v0.23.0. Corrects the prior "nightly-only, no stable release" claim, which rested on release-note absence. |

## Notes

**A closed-looking tracker that is entirely open (2026-08-11).** All five
gemma-4 issues this skill cites are OPEN, and all three fix PRs are unmerged.
v0.27.0 shipped the day before this pass and clears none of them, so the version
ceiling extends rather than lifts. The pass's substantive correction was in the
opposite direction from the usual freshen finding: not "this warning is stale,
delete it" but "this warning understates its own scope" — #49955 is not
spec-decode-specific, and the skill said it was.

**Not re-probed this pass (honest gap):** r03 (RedHatAI eagle3 repo), r05/r06
(vLLM source blobs pinned at v0.25.1 — still the skill's supported ceiling, so
re-pinning them at v0.27.0 would misrepresent what the skill recommends running),
and r07–r10. Budget went to the regression tracker, which is what gates the
version recommendation.


**The staleness thesis is no longer inferential (2026-07-21).** The prior two
passes argued "the quant's template is probably stale because canonical keeps
moving." This pass diffed them directly: `cyankiwi`'s file is byte-identical to
the 2026-04-30 canonical and 114 lines behind the current one. That converts the
skill's central recommendation — always `--chat-template` the canonical pull —
from a precaution into a measured defect list (see SKILL.md fact #3).

**How to re-probe r01/r02 next pass** (the whole finding is four commands):

```bash
curl -sSL -o /tmp/g4.jinja  https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja
curl -sSL -o /tmp/cy.jinja  https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit/raw/main/chat_template.jinja
sha256sum /tmp/g4.jinja /tmp/cy.jinja
diff /tmp/g4.jinja /tmp/cy.jinja | grep -c '^[<>]'     # 114 on 2026-07-21
head -7 /tmp/g4.jinja                                  # Google stamps a Published: date in-file
```

That in-file `Published:` header is new and is the cheapest signal available —
read it before hashing anything.

- **Do not treat any r01 hash as a pin.** Three passes, three hashes. The hash
  chain is kept as *evidence of drift rate*, not as a value to match against.
- **`lastModified` on an HF repo does not mean the weights or template moved.**
  r02 reported 2026-07-03 while its template had not been touched since
  2026-04-30 — the commit edited the README. Read
  `/api/models/<repo>/commits/main` titles, not the timestamp.
- **r05/r06 are now re-pinned at v0.25.1** (the honest gap the 2026-05-28 pass
  flagged is closed). Both claims survived five minors; only line numbers and
  the P-EAGLE check *order* moved. Cite symbols, not lines — the line-number
  pins have been re-written twice now for zero semantic change.
- **Still not re-probed:** the EAGLE3 / TRITON_ATTN / spec-config CLI surface
  against 0.21–0.25, and the `bench-numbers.md` measurements, which remain
  v0.20.0 observations. Re-running those needs GPU time, not a probe.
