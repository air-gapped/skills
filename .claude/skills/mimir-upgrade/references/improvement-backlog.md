# Improvement backlog — mimir-upgrade

Work-not-done log across skill-improver runs. Append-only history; not a wishlist.

## Open

### Nothing in this skill has been field-validated (Dim 9 / integrity)

- **What:** every procedure is either upstream-grounded from docs/source or reasoned from chart templates. No
  lab cluster existed at authoring time (prod is air-gapped; the lab Mimir install was decommissioned as too
  large to run continuously).
- **Why it could not be closed:** requires a cluster. Not fixable by reading.
- **Highest-value validations, in order,** if a lab is ever available:
  1. That `classic-architecture.yaml` produces a *working* 6.x cluster, not merely a clean render — specifically
     that a live Mimir accepts `ingest_storage.kafka.address: null` through its `Validate()` path. The decode
     was proven against Mimir's YAML library; the validate path was not.
  2. That an in-place 5.7.0 → 6.x classic upgrade preserves ingestion across the ingester roll.
  3. That the nginx→gateway `nameOverride` migration genuinely preserves client connectivity end to end.
- **Do NOT** silently upgrade `[RFC]` tags to `[UG]` on the strength of "it looks right". The tag distinction is
  the skill's integrity.

### Fleet-facts interview answers are unknown (Dim 4)

- **What:** Step 0 asks five questions the skill cannot answer for itself. Until a real fleet answers them, the
  runbook necessarily hedges — most visibly around nginx-vs-gateway (§3 of `per-hop-runbook.md`), where the
  entire hop-2 risk profile depends on the answer.
- **Why not closed:** requires cluster access the author did not have.
- **Next pass:** if the operator supplies answers, consider a worked example section pinned to that fleet's real
  shape — but keep the generic interview, since the skill outlives one fleet.

### MQE differencing rig is assembled, not documented (Dim 5)

- **What:** `verification.md` §7 describes a query-tee rig built from documented primitives (query-tee flags +
  an engine-pinned second query path). Upstream describes having done this in staging but **publishes no
  procedure**.
- **Why not closed:** there is no upstream runbook to cite, and no lab to test the rig in. Tagged `[RFC]`
  accordingly.
- **Next pass:** re-probe for an upstream query-tee runbook; if one appears, replace the reconstruction and
  re-tag.

### Kafka sizing has no upstream guidance (Dim 5)

- **What:** `architecture-decision.md` §6 extrapolates from a single community datapoint (~2 GB/day per 1k
  samples/s at 24 h retention) because upstream publishes none — tracked in grafana/mimir#12012 and #14008, both
  open.
- **Why not closed:** the guidance does not exist yet.
- **Next pass:** check whether #14008 landed capacity-planning docs for ingest storage; if so, replace the
  extrapolation with the real numbers.

### Chart 6.1.x may supersede 6.1.0 (Dim 9)

- **What:** the ladder terminates at 6.1.0 / app 3.1.2, but app 3.1.3 exists upstream and a 6.1.x patch chart may
  land.
- **Why not closed:** correct at authoring time; this is a freshen concern, not a defect.
- **Next pass:** re-derive the terminal hop from `k8s-components-checker` → `compat/mimir.md` rather than
  updating numbers here. This skill deliberately holds no version matrix.

## Resolved — 2026-07-21 (initial authoring)

Built from a six-agent autoresearch pass. Notable corrections that the research forced into the skill, all of
which contradicted the starting assumptions:

- **Classic architecture is supported, shipped, and CI-tested** — the premise that the override was
  undocumented was wrong. The chart ships `classic-architecture.yaml`; the migration guide has a dedicated
  section; upstream regression-tests it with golden manifests.
- **MQE became the querier default at 2.17, not 3.0** — moving the read-path risk to hop 1 and changing the
  recommended sequencing (pin the engine through 5.8.0, flip separately).
- **The `kubectl rollout restart` prohibition is folklore** — no upstream document states it, and the
  "it errors on `OnDelete`" variant is disproven by kubectl source. The real mechanism is defused by the
  chart's `unregister_on_shutdown: false` pin; the genuinely dangerous case is single-zone.
- **Four chart-CHANGELOG claims are wrong** (querier `max_concurrent`, GEM port 8080, Helm v4, rollout-operator
  version) — recorded in `per-hop-runbook.md` §7 with the tarball evidence, since a future reader will hit the
  same changelog.
- **The nginx→gateway break is community-specific**, which is why it is under-reported: enterprise fleets
  already ran `gateway` and never saw it.
