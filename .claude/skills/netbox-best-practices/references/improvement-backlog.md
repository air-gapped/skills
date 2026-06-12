# Improvement backlog — netbox-best-practices

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
