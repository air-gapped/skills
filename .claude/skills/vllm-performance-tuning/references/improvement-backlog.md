# Improvement backlog — vllm-performance-tuning

## Open

- **PD-disagg connector wiring is thin** (Dim 5) — `references/distributed.md` + SKILL.md router. Nixl/Mooncake/LMCache are named but the actual connector-config recipe (KVTransferConfig fields, proxy wiring) is shallow. Adding it is author-domain content + a multi-section write, not a one-iteration atomic edit; also overlaps `vllm-caching`, so the split needs a deliberate boundary decision.
- **No bundled scripts** (Dim 7, ceiling) — skill points at vLLM's `benchmark_moe.py` / `auto_tune.sh` rather than shipping a wrapper. Scoring this past 7 would require authoring and testing a real bundled script (e.g. a tuned-config-presence checker); cannot be fabricated in one iteration without a tested artifact.
- **#39107 MoE-DP-chunk removal not independently double-fetched** (Dim 9) — `references/moe-and-ep.md` GB200 note + sources.md row. The "removed in v0.20.0" claim rests on the recon's single read of the v0.20.0 release-notes body; the confirmatory `gh` PR-state call was hook-blocked this pass too. Annotation is framed conservatively ("per v0.20.0 release notes") rather than asserted as re-verified. Re-confirm the PR state on the next freshen.

## Resolved this pass

- Converted the 12-step numbered "tuning workflow" (SKILL.md) into a goal-grouped lever list — lifts the Boris strict-workflow cap on Dim 6 (6→8).
- Updated SKILL.md version header from v0.19.1/v0.20.0-prerelease to v0.21.0 stable (2026-05-15); v0.20.x stable since 2026-04-27 — Dim 9.
- Flipped vllm-ascend #4649 from "still disable async-sched" to fixed/closed 2026-03-13 across SKILL.md #7, scheduler-and-compile.md, regressions.md, sources.md — resolves the Dim 8 live/closed contradiction + Dim 9.
- Flipped #34641 (MI300X FP4BMM) from OPEN to closed 2026-05-28 in regressions.md + sources.md; reframed the AITER_FP4BMM=False workaround as legacy-for-pre-fix-builds — Dim 9.
- Annotated GB200 MoE-DP-chunk env vars as removed in v0.20.0 (PR #39107) in moe-and-ep.md; added sources.md row — Dim 9.
- Re-stamped sources.md verified dates and refresh-policy block to 2026-05-28; updated SKILL.md + regressions.md "current as of" stamps — lifts the staleness ceiling on Dim 9.
