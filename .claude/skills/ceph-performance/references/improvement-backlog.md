# Improvement backlog — ceph-performance

## Open

## Resolved this pass (2026-09-23)

Created. Blind 88 → 85 on the cut version; A/B comparators 3/3 REGRESSED,
all naming the benchmarking cut, which was reverted (one discard — ceiling
partly mapped: non-discriminating evals do not make runnable commands
redundant). Kept: osd_memory_target verification step. Outcome benchmark
(9 cases, sonnet): with skill 96% → 100% on re-run, without 59%.
