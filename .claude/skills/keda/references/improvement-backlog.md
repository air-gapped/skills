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

## Resolved — 2026-07-21 (freshen)

- **KEDA release moved 2.19.0 → 2.20.1** — `operations.md` install pin bumped;
  k8s N-2 window updated to 2.20 → v1.33–v1.35; sources.md rows restamped.
  Source: https://github.com/kedacore/keda/releases/tag/v2.20.1
- **2.20 `events.k8s.io` upgrade trap** added to `operations.md` Upgrades —
  restricted RBAC needs `create`/`patch` on `events.k8s.io/events` before the
  upgrade or event recording breaks (PR #7781).
- **2.20 CRD validation markers** noted in the CRD-changes bullet — previously
  accepted ScaledObjects (e.g. names > 63 chars) can now fail admission.
- **`scalingModifiers` fallback** — the "does not fire correctly" caveat in
  `patterns.md` now names 2.20's `fallback.behavior: scalingModifiers` plus the
  `??` metric-chaining formula. Source: kedacore/keda PR #7790 (merged 2026-05-29).
- **HTTP Add-on v0.14.0 → v0.15.0** — HTTP/2 + gRPC (`appProtocol:
  kubernetes.io/h2c`, `KEDA_HTTP_FORCE_HTTP2` removed) and
  `coldStart.placeholder` documented in `patterns.md`; the stale "README says
  not recommended for production" claim corrected in both `patterns.md` and
  SKILL.md — README now says beta-but-stable with a v1.0 planned.
- **OTel Helm value name** (carried from the prior pass) — closed. Probed the
  live chart `values.yaml`: correct keys are `opentelemetry.operator.enabled`
  and `opentelemetry.collector.uri`; the skill's `operator.otelScraping.enabled`
  did not exist.
- **New 2.20 scalers** `opensearch` + `elastic-forecast` added to the
  `scalers.md` catalog and decision tree; InfluxDB `authToken`-in-metadata
  removal noted.

## Resolved — prior pass

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
