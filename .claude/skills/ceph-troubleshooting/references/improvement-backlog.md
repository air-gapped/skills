# Improvement backlog — ceph-troubleshooting

## Open

- **Trigger collisions with the three sibling Ceph skills.** Blocked on:
  ceph-performance and ceph-s3 existing, so probe-trigger.py can measure
  which skill fires for boundary queries (slow recovery vs tuning, RGW
  errors vs S3 behaviour).

## Resolved this pass (2026-09-23)

Created. Blind 87 → 86 (within scorer noise); A/B comparators 3/3 prefer
final (all margin slight: two sourced correctness fixes vs a capacity-cut
regression, since restored). Outcome benchmark (9 cases, sonnet): with
skill 100%, without 68.5%. Evals 0, 1, 2, 8 do not discriminate — the
model already handles mClock, capacity and EC-incomplete cases; value is
in the Rook-specific procedures. Zero full discards — ceiling not mapped.
