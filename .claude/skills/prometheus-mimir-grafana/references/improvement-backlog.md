# Improvement Backlog — prometheus-mimir-grafana

Tracks issues attempted but not landed in a single keep/discard iteration, and
changes the metric registered this pass. Append-only audit; not a wishlist.

## Open

- **Trim kpis-frameworks.md §7 dashboard recipes** — Dim 2 / Dim 6 —
  `references/kpis-frameworks.md:322-410`. The recon hypothesis assumed §7
  contained per-recipe PromQL enumerations to collapse into one-line panel
  lists. On read, §7 is *already* in one-line-per-panel form (numbered panel
  names, no inline PromQL). There is no fat to cut without merging the
  numbered lists into comma-joined prose, which would save ~50 lines of a
  474-line **reference** file (under no cap — the 500-line limit applies to
  SKILL.md, which is 189 lines) while degrading scan-readability of the
  differentiated GPU/DCGM, Kafka, and Postgres catalogs (Dim 10 value). Net
  total would not improve. Not applied. Revisit only if the file grows fat
  PromQL blocks later.

- **Reconcile `status` vs `status_code` label naming** — Dim 8 —
  `SKILL.md:89,157` use `status=~"5.."`; `references/agent-workflow.md:47-63`
  use `status_code=~"5.."` for the same concept. This is intentional
  (label name is cluster-dependent; the discovery-first discipline tells the
  agent to confirm the actual label), so a blind find-and-replace would be
  *wrong* — it would assert a label name the skill deliberately leaves open.
  Resolving cleanly needs a one-line standing note ("the 5xx label is
  `status` or `status_code` depending on the exporter — confirm via
  /api/v1/series before filtering") placed once, plus a decision about which
  example form to standardize on. That is an author-judgment edit touching
  three sites in two files; deferred rather than risk introducing a false
  determinism in one atomic step.

## Resolved — 2026-07-21 (freshen)

- **Mimir 3.0 removed read-write-backend deployment mode** — `mimir-api.md` §1
  claimed all three modes still exist. Verified against the Mimir CHANGELOG
  ("[CHANGE] Remove support for the experimental read-write deployment mode",
  #11974/#11975/#12584) and the 3.0.0 release notes. Now states monolithic or
  microservices only, and that a read-write cluster cannot upgrade in place.
- **MQE is the default query engine from Mimir 3.0** — added to `mimir-api.md`
  §1 with the `-querier.query-engine=prometheus` opt-out as the way to tell an
  engine bug from a query bug after an upgrade. Ingest-storage (Kafka)
  architecture noted as available-but-not-assumed (classic still supported).
- **`promql-duration-expr`** (arithmetic in range/offset) added to
  `promql.md` §2 with an assume-it-is-OFF instruction — experimental on both
  Prometheus and Mimir 3.x.
- **`/api/v1/status/self_metrics`** (Prometheus 3.12+) added to the
  `promql.md` §7 status-endpoint list.
- Grafana version framing updated to name 13.1 (2026-07-01) alongside 13.0 GA;
  the `/api` → `/apis` deprecation status is unchanged (13.1 what's-new says
  nothing about the dashboard HTTP API).
- Re-verified, no change: native histograms are NOT behind a feature flag
  (checked the live feature-flags page — the skill's "Prometheus 3.x default"
  claim holds); `info()` IS still experimental behind
  `promql-experimental-functions`; PRW 2.0 still EXPERIMENTAL on Mimir 3.x.
- sources.md: all 32 rows restamped 2026-07-21, rows 33 (Mimir 3.0 release
  notes) and 34 (Prometheus feature flags) added.

## Resolved — 2026-05-28

- Grafana version framing freshened: Grafana 13 (GA 2026-04-17) named as
  current stable with the official `/api`→`/apis` deprecation (notice
  2026-04-20); legacy `/api/dashboards/db` documented as still functional,
  removal deferred. `SKILL.md:112` + `references/grafana-dashboards.md` §1.
  Dim 9 — removed the one-major-version lag the recon flagged.
- PRW 2.0 EXPERIMENTAL status stated explicitly at the Mimir write-path
  endpoint (`references/mimir-api.md` §4), citing the upstream spec banner.
  Dim 5 — closed the description-implied "remote_write" gap.
- Canonical info-metric join deduplicated from 4 full code blocks to 2:
  removed the inline block in `references/agent-workflow.md` §1 Step 6
  (replaced with a prose pointer that keeps the `on(job, instance)`
  correction) and collapsed the `references/promql.md` §4 operator-example
  block to a one-line `group_left` demonstration pointing to §8. Dim 6.
- sources.md re-stamped to 2026-05-28 on the 10 probed rows (1-9, 12) and two
  new rows added: row 31 (Grafana v13 what's-new / `/api` deprecation) and
  row 32 (Prometheus Remote-Write 2.0 EXPERIMENTAL spec). Dim 9 staleness
  clock reset within the no-cap window.
