# Improvement backlog — vllm-performance-tuning

## Open

- **PD-disagg connector wiring is thin** (Dim 5) — `references/distributed.md` + SKILL.md router. Nixl/Mooncake/LMCache are named but the actual connector-config recipe (KVTransferConfig fields, proxy wiring) is shallow. Adding it is author-domain content + a multi-section write, not a one-iteration atomic edit; also overlaps `vllm-caching`, so the split needs a deliberate boundary decision.
- **No bundled scripts** (Dim 7, ceiling) — skill points at vLLM's `benchmark_moe.py` / `auto_tune.sh` rather than shipping a wrapper. Scoring this past 7 would require authoring and testing a real bundled script (e.g. a tuned-config-presence checker); cannot be fabricated in one iteration without a tested artifact.

## Resolved — 2026-08-11 (freshen, v0.25.1 -> v0.27.0)

**The pass's central finding is about method, not content: three prior freshens
verified the issue tracker and never verified the flag surface.** Probing
`vllm/config/*.py` + `vllm/engine/arg_utils.py` at the tag — which no earlier pass
had done — turned up four dead flags and one rename, two of them removed **eleven
and five months** before this pass and therefore invisible to any release-note
scan of the current window. A removed flag is a hard startup failure, strictly
worse than a stale issue state.

- **`--max-num-partial-prefills` / `--max-long-partial-prefills` removed in
  v0.27.0** (PR #49244). The PR's own framing is the useful part: these were V0
  fields "explicitly rejected by the V1 enablement oracle… dead config that can
  only ever raise `UnsupportedFeatureError`". Same documented-but-dead shape as
  `VLLM_RPC_TIMEOUT` in the sibling `vllm-configuration` skill.
- **`--preemption-mode` (PR #25334, 2025-09-21) and `--swap-space` (PR #36216,
  2026-03-07) removed — and the skill's preemption section was built on them.**
  "Raise `--swap-space` to absorb bursts" was mitigation #1 for KV thrashing in
  `scheduler-and-compile.md`, was repeated in SKILL.md's triage tree, in the Red
  Hat triage step 3, and in `regressions.md` under #25538. It was a no-op even
  before removal: V1 hardcodes `num_cpu_blocks = 0`. Rewrote the section around
  the knobs that actually exist — `--watermark` (KV headroom at admission) and
  `--scheduler-reserve-full-isl` (admit only if the whole ISL fits, on by
  default), which is precisely the over-admission that produced the thrash
  reports.
- **`--cuda-graph-sizes` renamed `--cudagraph-capture-sizes`.** Absent from the
  tree at v0.25.1 *and* v0.27.0, and a repo-wide code search for the old symbol
  returns nothing — so the skill had been shipping an unparseable flag for at
  least two minors. Fixed in the frontmatter (old spelling kept as a trigger),
  SKILL.md, `distributed.md`, and three places in `scheduler-and-compile.md`.
- **The two batching defaults are device-gated, and the skill stated a
  constant.** `vllm serve` on a ≥70 GiB non-A100 GPU defaults to
  `max_num_batched_tokens=8192, max_num_seqs=1024`; the familiar 2048/256 from
  PR #10544 is the small-GPU branch. On the H100/H200/B200 hardware this skill
  targets, every tuning plan anchored to 2048/256 started 4× below reality.
- **New levers added:** `--performance-mode {balanced,interactivity,throughput}`
  — a single flag for the posture the "scheduler first-pass by workload" table
  was hand-assembling — plus the note that `throughput` doubles only *defaulted*
  batching values, and per-request `stream_interval` (#49754).
- **Compile section corrected in a way that changes behaviour, not just wording:**
  both AOT vars have *computed* defaults that resolve **on** under the v0.27.0
  torch 2.13.0 pin (#48155), so they are opt-out. The consequence worth naming is
  the coupling — `VLLM_DISABLE_COMPILE_CACHE=1`, the documented Llama-4
  workaround sitting one row above, also disables AOT compile and with it the
  mega-artifact. Also: first-request JIT stalls are gone (#47451, #49903), so a
  pre-v0.27.0 TTFT baseline that swallowed one is not comparable.
- **Added step 0 to the defensive upgrade checklist:** diff the flag surface
  between tags before upgrading. That is the check whose absence caused this
  pass's findings.

**Deliberately kept:** `--cuda-graph-sizes` remains in the frontmatter beside the
new spelling — same policy as `VLLM_ENABLE_MOE_DP_CHUNK`; it is a *trigger*, so an
operator searching the dead name should land here and be told the new one.

**Not attempted:** the issue tracker was not re-probed this pass (budget went to
the flag surface). #35048, #32547, #19579, #31475 and #25538 all carry 2026-07-21
states, and `regressions.md` now says so at the top rather than implying currency.
`FusedMoE` → `FusedMoEFactory` (#44941) verified but not applied — the skill's
only mention is generic prose, and no operator-facing flag changed.

**Tag discipline:** v0.27.1 shipped mid-pass (2026-08-11) with one change
(#50424, quantized DSpark Markov heads). Claims stay stamped **v0.27.0** because
that is the tag actually read; only the "latest stable" line names v0.27.1.

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
