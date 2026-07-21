# Improvement backlog — netbox-best-practices

## Resolved — 2026-07-21 (freshen)

**The skill's own refresh trigger did not fire — and that is the finding.**
NetBox is still **4.6.x** (v4.6.5, 2026-07-14) and the chart is still **8.x**
(8.3.37, 2026-07-15). No new minor, no chart major, so every `version-deltas.md`
claim and the v1-token-removal-at-**v5.0** schedule stand unchanged.

- **Version-lookup trap documented.** `netbox-community/netbox-chart` publishes
  **two products into one release stream** — `netbox-<chart>` and
  `netbox-operator-<chart>`. As of 2026-07-21 `isLatest` is
  **`netbox-operator-1.2.128`**, so `gh release view -R
  netbox-community/netbox-chart` returns an *operator* version, not a chart
  version. Recorded the Helm-index query as the correct lookup, since it
  separates the two entries and carries `appVersion`.
  (Fourth distinct shape of this failure found in one freshen run — after
  date-ranked `latest`, RC tags flagged non-prerelease, and parallel-minor
  patching. "How do I find the newest version" is a per-repo question.)
- **`[live]` labels re-scoped, not re-stamped.** They were verified once on
  chart 8.3.14 / v4.6.2 (2026-06-12) and have **not** been re-run; upstream has
  since moved 23 chart patches and 3 NetBox patches. The header now reads
  "observed on 4.6.2" rather than leaving currency implied. Re-running them
  needs the production install, not a public probe — deliberately not faked.
- **Pinned versions annotated** in `SKILL.md`, `helm-chart-gotchas.md` and
  `sources.md` with the upstream delta plus the explicit "no delta invalidated"
  conclusion, so a future reader can tell *checked-and-unchanged* from
  *not-checked*.


## Open

- **HA/replicas/media-persistence coverage** (Dim 5) — netbox-chart replicas >1
  requires RWX media storage (or S3-style media backend); chart issues track
  upgrade-path and securityContext recurrences. Needs researched, verified
  content (chart issues sweep + a live multi-replica test) — not a
  single-iteration mutation. Source candidates: netbox-community/netbox-chart
  issues; deep-research run 2026-06-12 flagged this as its open question.
- **`when_to_use` field split** (Dim 1) — blind scorers (both passes) note
  trigger phrases are stuffed into `description` (866 chars, inside caps).
  Splitting is spec-preferred but cosmetic today; do it next description edit.

## Resolved this pass — 2026-06-12

- sources.md created, all rows stamped 2026-06-12 (Dim 9 cap 6 → 9).
- Token section deduplicated against official netbox-labs:netbox-api-integration,
  then made runnable again per final blind feedback (curl + credential assembly).
- Overbroad description catch-all ("any NetBox deployment/bootstrap/CI
  question") narrowed.
- Second-person occurrences → 0; ToC added to helm-chart-gotchas.md.
- Cross-skill deferral given an internal fallback (version-deltas.md §4.5).
- Scores: self baseline 78 → blind baseline 83 → blind final **91/100**
  (no self-vs-blind dimension gap ≥2 at baseline; final issues all addressed
  or backlogged).
