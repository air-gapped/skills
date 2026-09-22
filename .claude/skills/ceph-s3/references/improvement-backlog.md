# Improvement backlog — ceph-s3

## Open

- **Which Squid point release first accepted AWS SDK trailing CRC32
  checksums.** Not established in this pass; only CRC64NVME (Tentacle-only)
  is sourced. Blocked on: a primary source (tracker or release note) naming
  the release, or a test against a Squid RGW with a current AWS SDK.

## Resolved this pass (2026-09-23)

Created. Blind 84 → 86; A/B comparators 2/3 REGRESSED on the lifecycle
cut, which was reverted (one discard: symptom-to-cause sentences carry
value even when the model knows the defaults). Kept: STS trigger dropped,
single SigV4 revert caveat. Outcome benchmark (9 cases, sonnet): with
skill 100% (and 24/24 on re-run), without 52%.
