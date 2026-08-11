# Sources — vllm-gemma-4-31b

External references cited by SKILL.md and `references/*.md`. Each row carries
the upstream URL, classification, last verification date, and pinned version
or git ref where applicable. Re-probe via `/skill-improver freshen vllm-gemma-4-31b`.

## Authoritative model + template sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r01 | https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja | hf-model | 2026-08-11 | sha256:`ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4` (18683 B; **DRIFTED AGAIN** — third distinct hash in three passes: `94899c0f…` 16934 B 2026-04-30 → `36e3a42e…` 17466 B 2026-05-28 → this. **2026-08-11: HELD** — re-pulled, byte-identical, same 18683 B. First pass in four with no drift; do not read this as the chain having stopped, read it as one interval). Now carries a Google header comment: *"Published: 2026-07-09 — Fixed tool-calling loops, turn closures, and thinking content-ordering."* |
| r02 | https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit | hf-model | 2026-08-11 | Repo `lastModified` 2026-07-03, but that commit is *"Fix Model Size: 38.94 GB -> 20.90 GB"* (README only). Its `chat_template.jinja` hashes `94899c0f…25bff413` — **byte-identical to the 2026-04-30 canonical**, last touched by the 2026-04-30 `Upload folder using huggingface_hub` commit. 114 lines behind canonical (re-diffed 2026-08-11: still exactly 114). 951,914 downloads. |
| r03 | https://huggingface.co/RedHatAI/gemma-4-31B-it-speculator.eagle3 | hf-model | 2026-07-21 | `lastModified` 2026-04-14 — untouched since the original audit. Ships no `chat_template.jinja` at all (siblings: README, config.json, config.py, model.safetensors), so the staleness finding in r02 does not apply to it. Vanilla EAGLE3, still no P-EAGLE prep tokens. |

## vLLM engine sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r04 | https://github.com/vllm-project/vllm | github | 2026-08-11 | **v0.27.1 latest (2026-08-11)** — a one-change patch on v0.27.0 ("Support quantized DSpark Markov heads", #50424). **Checked for Gemma relevance: none** — the PR touches exactly one file, `vllm/model_executor/models/qwen3_dspark.py`, and is scoped to `Qwen3DSparkModel`. Then v0.27.0 (08-10), v0.26.0 (07-27), v0.25.1 (07-14), v0.25.0 (07-11), v0.24.0 (06-29). Skill's "0.20+" floor still valid, but the **audit baseline v0.20.0 is now seven minors old** — the measured numbers in `bench-numbers.md` have not been re-run past 0.20.0 and are labelled as such in that file and in SKILL.md. Note the skill's *ceiling* (0.25.1) is now two minors below latest, deliberately: see the three open regressions in r11–r13. |
| r05 | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/engine/arg_utils.py | github-source | 2026-07-21 | v0.25.1 (blob sha `c7a9335bbeb0535d87a93e407fb874c3d2efb65b`). `get_batch_defaults` now at lines **2397-2478** (was 2207-2288 at v0.20.0). GPU branch logic **unchanged**: `device_memory >= 70*GiB_bytes and "a100" not in device_name` → 16384/8192 tokens, 1024 seqs; H100 and H200 still share it. New since v0.20.0: a `current_platform.is_tpu()` sub-branch (V6E/V5E) inside the same function — so "only hardware-aware default" now means *only function*, not *only branch*. |
| r06 | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/v1/spec_decode/llm_base_proposer.py | github-source | 2026-07-21 | v0.25.1 (blob sha `756c5f3b3717204f45744a3d57fa8dc6d188d54c`). P-EAGLE requirement intact at lines 352-366 (was 341), but the **check order reversed**: `dflash_config["mask_token_id"]` is now tried *first*, then `pard_token`, then `ptd_token_id`. Sets `self.parallel_drafting_token_id`; raises the three-name `ValueError` otherwise. |

## vLLM issue / PR citations

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r07 | https://github.com/vllm-project/vllm/issues/35467 | github-issue | 2026-07-21 | still OPEN — "non-optimal performance of `linear` for medium batches" (B200 numerical proof of HBM-bandwidth-bound saturation). Latest comment: *"FI impl is ready. Have to check current state"* — a fix is in flight, so re-probe next pass. |
| r08 | https://github.com/vllm-project/vllm/issues/22780 | github-issue | 2026-07-21 | **CLOSED `NOT_PLANNED` 2025-12-14 by the stale bot** (*"automatically closed due to inactivity"*), NOT by a fix. The prior "closed" note read as resolved; it is not. The BnB-4bit concurrency regression is unaddressed upstream, which *strengthens* this skill's AWQ-over-BnB recommendation. See skill-improver `freshen-patterns.md` §3.0. |
| r09 | https://github.com/vllm-project/vllm/issues/6801 | github-issue | 2026-07-21 | OPEN but **stale-bot-marked** — "automatically marked as stale… will be closed if no further activity within 30 days." Expect it CLOSED/`NOT_PLANNED` by the next pass; that will mean abandonment, not delivery. The Pareto-knob framing it supports stands on its own. |
| r10 | https://github.com/vllm-project/vllm/pull/17885 | github-pr | 2026-07-21 | MERGED 2025-05-11 — "[Perf] Use small max_num_batched_tokens for A100". Still the origin of the A100 carve-out; its `NOTE(Kuntai)` comment survives verbatim in v0.25.1. |

## Gemma-4 regression tracker (probed 2026-08-11)

| Ref | URL | Classification | State on 2026-08-11 | Notes |
|---|---|---|---|---|
| r11 | https://github.com/vllm-project/vllm/issues/49955 | github-issue | **OPEN** | Trailing `<turn|>`. **The skill's prior "not reproducible without spec-decode" was wrong** — the same reporter's 2026-07-31 matrix reproduces on 0.26.0 with MTP fully disabled, and finds the real discriminator is `stream=true`. A contributor could not reproduce at all on 0.26.0 without spec-decode, so it is config-sensitive. Fix PR #50964 (align `enable_thinking` default) OPEN; #50263 OPEN and confirmed by the reporter *not* to fix it. |
| r12 | https://github.com/vllm-project/vllm/issues/50477 | github-issue | **OPEN** | Named forced `tool_choice` ignored. Second reporter (2026-08-05) extends it to `tool_choice: "required"` on 0.26.0: HTTP 200, `finish_reason: "tool_calls"`, prose in `content`, `tool_calls: null`. Fix PR #51524 OPEN. |
| r13 | https://github.com/vllm-project/vllm/issues/50159 | github-issue | **OPEN** | MRv2 over-reports available KV. Two independent A/B runs (Qwen2.5-0.5B on RTX PRO 6000; Gemma-4 31B on 2× RTX 3090) localise it to **CUDA-graph capture headroom accounting**, not KV capacity — MRv1 reserves ~0.65 GiB vs MRv2 ~0.12 GiB on the large rig, and the gap collapses to ~0 under `--enforce-eager`. Related: #49224, draft #49233 (on hold). **No fix PR.** |
| r14 | https://github.com/vllm-project/vllm/issues/50158 | github-issue | **OPEN** | EAGLE embed_tokens sharing decided per-rank. Unchanged; the skill's acceptance-rate check after every engine upgrade stands. |
| r15 | https://github.com/vllm-project/vllm/issues/49475 | github-issue | **OPEN** | `RedHatAI/gemma-4-31B-it-speculator.dspark` still fails to load. |
| r16 | https://github.com/vllm-project/vllm/pull/46837 | github-pr | **MERGED** 2026-07-25 | ViT CUDA graph for Gemma-4; `SupportsEncoderCudaGraph` on `Gemma4ForConditionalGeneration`, static gather replaces the pooler's dynamic slicing. Listed in the **v0.27.0** release notes. The only gemma-4 gain in 0.27.0. |
| r17 | https://github.com/vllm-project/vllm/pull/47216 | github-pr | **MERGED** 2026-07-16 | Gemma4-**12B** DSpark draft model (`deepseek-ai/dspark_gemma4_12b_block7`), shipped in v0.26.0. Different size and checkpoint from the 31B path — does not unblock r15. |
| r18 | https://github.com/vllm-project/vllm/blob/v0.27.0/examples/tool_chat_template_gemma4.jinja | github-source | verified | Line 180: `{%- set enable_thinking = enable_thinking | default(false) -%}`. Half of the r11 root cause. |
| r19 | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/parser/gemma4.py | github-source | verified | Line 403: `self._thinking_enabled = chat_kwargs.get("enable_thinking", True)`. The other half — defaults disagree, so an unspecified `enable_thinking` puts template and parser in opposite states. |

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
