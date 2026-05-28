# Improvement backlog — keda

## Open

- **Full three-file max-of consolidation** — Dim 6 — SKILL.md gotcha #4 +
  `references/crds.md` (multi-trigger semantics) + `references/patterns.md`
  ("Default: max of triggers"). This pass collapsed the crds.md restatement to
  a one-line pointer to patterns.md. The remaining two are NOT pure duplication:
  SKILL.md gotcha #4 is the gotcha-summary surface and patterns.md is the
  canonical depth (intro paragraph that the scalingModifiers section builds on).
  Removing either in one atomic step orphans its section's context, so deeper
  consolidation could not be applied without a multi-step rewrite that re-flows
  the patterns.md scalingModifiers lead-in.

- **OTel Helm value name unverified** — Dim 9 — `references/operations.md` L322
  (`operator.otelScraping.enabled=true`). Recon classified this `unverifiable`
  within the probe budget; the skill already hedges with "check chart version".
  Not applied: confirming the exact current Helm value name requires a chart
  values probe that was out of scope this pass. Re-check against the live
  `kedacore/keda` chart `values.yaml` on the next freshen.

## Resolved this pass

- Replaced nonexistent `v2.20.0` install-manifest URLs with a pinned
  `KEDA_VERSION=2.19.0` variable reused in both URLs (`operations.md`) — fixes a
  verified-stale 404 (Dim 9) and removes the install-vs-CVE-prose version
  self-inconsistency (Dim 8).
- Created `references/sources.md` with 10 verified rows stamped 2026-05-28 —
  lifts the Dim 9 staleness cap (was capped at 6 for absent sources.md).
- Added a `references/sources.md` pointer to SKILL.md's reference list (Dim 2/8).
- Trimmed `references/scalers.md` from 503 to 498 lines (cut redundant
  cross-reference boilerplate; folded the legacy-`kafka` note into the
  apache-kafka gotchas) — brings the last over-limit reference file under the
  500-line guidance (Dim 2).
- Collapsed the `references/crds.md` multi-trigger restatement to a pointer to
  `references/patterns.md` (Dim 6).
- Added jq-first / python3-fallback parsing to
  `scripts/debug-scaledobject.sh` via `metric_names()` and `trigger_count()`
  helpers — removes the hard python3 dependency (Dim 7).
