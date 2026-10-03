# Improvement backlog — ceph-s3

## Open

- **Which Squid point release first accepted AWS SDK trailing CRC32
  checksums.** (carried 2026-10-03) Not established; only CRC64NVME
  (Tentacle-only) is sourced. Blocked on: a primary source (tracker or
  release note) naming the release, or a test against a Squid RGW with a
  current AWS SDK. Re-checked 2026-10-03: Squid backports 70736 and 71682
  still New.

## Resolved this pass (2026-10-03)

Blind 81 → 82; comparators 3/3 IMPROVED (slight); outcome (9 cases × 3,
sonnet) final 0.951 / baseline 0.963 / without 0.469 — final vs baseline is
noise (one case-01 run omitted the forwarding mechanism).
Stopped at the 3-iteration cap (1 discard), not a mapped ceiling.
- Kept: `argument-hint` focus areas mapped to sections.
- Kept: §Multisite sync status (behind vs recovery shards, `sync error
  list`, never promote a lagging zone to metadata master).
- Discard: shard-count rule (peak objects / 100 000, prime) plus
  `reshard status` done-check in §Bucket index — Dim 4 +1 cancelled by
  Dim 2 −1 as SKILL.md crossed 150 lines.

## Resolved — 2026-09-23

Created. Blind 84 → 86; A/B comparators 2/3 REGRESSED on the lifecycle
cut, which was reverted (one discard: symptom-to-cause sentences carry
value even when the model knows the defaults). Kept: STS trigger dropped,
single SigV4 revert caveat. Outcome benchmark (9 cases, sonnet): with
skill 100% (and 24/24 on re-run), without 52%.
