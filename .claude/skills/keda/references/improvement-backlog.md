# Improvement backlog — keda

## Accepted duplicates — do not "fix"

`context-optimization-check` flags these two as DUPLICATE on every run. Both
were read on 2026-08-21 and kept deliberately; leave them alone.

- **SKILL.md 3-step fast path vs `troubleshooting.md` step 1-3.** The body
  carries only the three checks that cover 90% of cases so a stuck-ScaledObject
  question is answered without a file read. The reference carries all six as a
  runnable sequence.
- **`operations.md` "Probing the external metrics API" vs `troubleshooting.md`
  steps 4-5.** The probe is run top-to-bottom; replacing two of its steps with a
  pointer breaks the sequence. `operations.md` is the reference for the
  `s<index>-<type>-<hash>` metric-name scheme, which the probe links to.

## Open

## Unblocked — actionable

## Decided — do not re-propose

- **Do not consolidate the max-of semantics further.** The entry already conceded
  the remaining two statements are not duplicates: SKILL.md gotcha #4 is the
  gotcha-summary surface and `patterns.md` § "Default: max of triggers" is the
  canonical depth the `scalingModifiers` section builds on. That is the shape
  skill-improver's rubric names INTENTIONAL_DETAIL and requires to be kept — an
  overview in the body developed in `references/` *is* progressive disclosure, and
  the fleet measurement behind that rule found 83% of similar-looking content
  correct as written. Gotcha #4 already points at `patterns.md`, so the two are
  linked rather than merely repeated.
- **The third statement is not a duplicate either.** The Prometheus + CPU recipe
  states the max-of rule immediately above its manifest. A recipe read on its own
  needs it there, and the gotcha it would otherwise depend on sits 180 lines later.
- What the earlier pass did do — collapsing the `crds.md` restatement to a pointer
  — was the part that was genuine duplication. Nothing is left that can be removed
  without orphaning the context around it.

## Resolved — 2026-09-15 (freshen to v2.20.2)

- **Two things must happen before a v2.20 upgrade, and the skill named neither.**
  v2.20.0 moved event recording to the **`events.k8s.io`** API group, so a
  custom or restricted RBAC role needs `create`/`patch` there **before** the
  upgrade or events stop being recorded. v2.20.2 then had to restore the core
  `""` group as well (#7922) because client-go's legacy broadcaster still uses
  it — a hand-rolled Role wants both, which is not obvious from either release
  note alone.
- **Four deprecated scaler fields were removed in v2.20.0**, so an existing
  manifest can break: GCP PubSub `subscriptionSize`, Huawei Cloudeye
  `minMetricValue`, InfluxDB `authToken` in `triggerMetadata`, and the IBM MQ
  `tls` setting. Recorded with replacements.
- **Security:** GHSA-6w3m-4hhp-775q (medium, 2026-06-01), connection-string
  parameter injection in the **PostgreSQL scaler**, affects ≤ 2.19.x, patched in
  2.20.
- **Kubernetes support is a tested N-2 window, not a floor** — v2.20 covers
  1.33–1.35. Stating it as a floor would overclaim; 1.36 was not in the matrix
  at this check.
- **Three open defects recorded**, the first of which is the one most likely to
  be mistaken for a target-side fault: `TriggerAuthentication` resolves auth
  params once at scaler build time and never re-reads them, so a **rotated
  Secret produces silent 401s** until the ScaledObject is recreated (#7906).
  Also stuck finalizers wedging namespace teardown (#7950) and a
  CloudEventSource deadlock that keeps passing its liveness probe (#8039).

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
