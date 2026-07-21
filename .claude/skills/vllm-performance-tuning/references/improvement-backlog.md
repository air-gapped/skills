# Improvement backlog — vllm-performance-tuning

## Open

- **PD-disagg connector wiring is thin** (Dim 5) — `references/distributed.md` + SKILL.md router. Nixl/Mooncake/LMCache are named but the actual connector-config recipe (KVTransferConfig fields, proxy wiring) is shallow. Adding it is author-domain content + a multi-section write, not a one-iteration atomic edit; also overlaps `vllm-caching`, so the split needs a deliberate boundary decision.
- **No bundled scripts** (Dim 7, ceiling) — skill points at vLLM's `benchmark_moe.py` / `auto_tune.sh` rather than shipping a wrapper. Scoring this past 7 would require authoring and testing a real bundled script (e.g. a tuned-config-presence checker); cannot be fabricated in one iteration without a tested artifact.

## Resolved — 2026-07-21 (freshen, v0.21.0 -> v0.25.1)

- **Closed the twice-blocked #39107 backlog item.** The confirmatory `gh` call
  had been hook-blocked on two consecutive passes, so the claim rested on a
  single read of release-note prose. Probed directly: PR #39107 "[MoE Refactor]
  Remove MoE DP chunking" is **MERGED 2026-04-14**, and its stated purpose names
  the replacement — *"Use `max_num_batched_tokens` as default for
  `max_num_tokens` in `FusedMoEConfig`."* Grepping `vllm/envs.py` at v0.25.1
  found **zero** hits for all three chunk vars, including
  `VLLM_FUSED_MOE_CHUNK_SIZE`, which the prior annotation had **not** flagged as
  removed. So the finding was one env var larger than recorded, and there is now
  a named replacement knob instead of just a deletion notice.
- **The `!!!` symptom has two distinct root causes — the pass's most useful
  correction.** `references/regressions.md` documented #29539 (CUDA-graph NaN
  under `FULL_AND_PIECEWISE`, genuinely fixed 2026-01-07) as *the* `!!!` bug.
  A second, unrelated defect produces the identical symptom: #48324 / PR #48330,
  the fused allreduce+RMSNorm+static-quant path matching a mixed-dtype graph on
  NVFP4 models, fixed only in **v0.25.1**. An operator matching on the symptom
  would conclude "fixed in January" and stop. Rewrote the section as a
  two-row cause table with a triage order, cross-linked to
  `vllm-nvidia-hardware`.
- **§3.0 sweep changed the meaning of three tracked issues.** #31475 (MI300X FP8
  slower than BF16) and #25538 (preempt/resume thrashing) both now read `CLOSED`
  — both closed `NOT_PLANNED` **by the inactivity bot**, neither fixed. The
  prior pass's refresh policy listed #31475 as "still-open", so a state-only
  re-probe would have flipped it to resolved and silently deleted a live AMD
  hazard. #35048 is stale-marked and heading the same way. Conversely #38971
  closed with a genuinely useful *answer* — `--moe-backend` is the flag that
  request was asking for — which is now recorded as guidance rather than as a
  known limitation, and #30758 closed as a tracker wind-down with follow-up
  "deferred indefinitely", not as completed work.
- **Added a "what changed under you, v0.22.0 → v0.25.1" section** to SKILL.md,
  scoped to changes that move the baseline a re-tune is measured against:
  Model Runner V2 becoming the default in three steps (Qwen3 → +Llama/Mistral
  #43458 → all dense #44443), DeepEP v2 (#41183), async EPLB on by default
  (#43219) plus NCCL-EPLB now *rejected* alongside it (#44978), sequence
  parallelism no longer requiring DP (#47070), `CUDA_VISIBLE_DEVICES` no longer
  set internally (#45026), PagedAttention removed (#47361), and the Transformers
  backend reaching native-vLLM speed (#47187) — which undercuts the reflex to
  always port to a native implementation.
- **Restamped** SKILL.md, `regressions.md`, and `sources.md` to v0.25.1 /
  2026-07-21, and rewrote the refresh policy around closure *reason* rather than
  closure state.

**Deliberately kept:** `VLLM_ENABLE_MOE_DP_CHUNK` stays in the frontmatter
`when_to_use` keyword list even though the var is gone. It is a *trigger*, not a
claim — an operator searching for it should land here and be told it is retired.

**Not attempted:** Wide-EP GB200 Part II (still Part I only; not re-probed),
#32547 and #19579 (not re-probed), and the two structural Open items below.

## Resolved this pass (2026-05-28)

- Converted the 12-step numbered "tuning workflow" (SKILL.md) into a goal-grouped lever list — lifts the Boris strict-workflow cap on Dim 6 (6→8).
- Updated SKILL.md version header from v0.19.1/v0.20.0-prerelease to v0.21.0 stable (2026-05-15); v0.20.x stable since 2026-04-27 — Dim 9.
- Flipped vllm-ascend #4649 from "still disable async-sched" to fixed/closed 2026-03-13 across SKILL.md #7, scheduler-and-compile.md, regressions.md, sources.md — resolves the Dim 8 live/closed contradiction + Dim 9.
- Flipped #34641 (MI300X FP4BMM) from OPEN to closed 2026-05-28 in regressions.md + sources.md; reframed the AITER_FP4BMM=False workaround as legacy-for-pre-fix-builds — Dim 9.
- Annotated GB200 MoE-DP-chunk env vars as removed in v0.20.0 (PR #39107) in moe-and-ep.md; added sources.md row — Dim 9.
- Re-stamped sources.md verified dates and refresh-policy block to 2026-05-28; updated SKILL.md + regressions.md "current as of" stamps — lifts the staleness ceiling on Dim 9.
