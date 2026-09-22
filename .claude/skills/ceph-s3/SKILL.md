---
name: ceph-s3
description: >-
  Run Ceph RGW as an S3 endpoint under Rook (CephObjectStore,
  CephObjectStoreUser, ObjectBucketClaim, COSI, CephBucketTopic, multisite
  realms/zones). Core knowledge: the 19.2.6 / 20.2.4 RGW security fixes and
  their fallout (SigV4 hardening rejecting presigned PUTs and RGW's own
  multisite forwarding; rgw_sigv4_insecure + rgw_s3_client_max_sig_ver),
  AWS SDK default checksums vs RGW (CRC64NVME only in Tentacle), bucket
  index sharding and large-omap warnings, Tentacle's two-phase reshard, RGW
  accounts (CephObjectStoreAccount, experimental), and Tentacle S3 behaviour
  changes (LastModified truncation, tenant IAM deprecation).
when_to_use: >-
  Use for RGW / S3-on-Ceph work: "radosgw", "RGW", "ceph s3", "CephObjectStore",
  "CephObjectStoreUser", "ObjectBucketClaim", "OBC", "COSI", "bucket
  notifications", "CephBucketTopic", "rgw multisite", "zonegroup", "realm",
  "sync status", "403 AccessDenied after upgrade", "SignatureDoesNotMatch",
  "presigned URL fails", "restic ceph s3 broken", "aws sdk checksum error",
  "x-amz-checksum", "CRC64NVME", "InvalidRequest", "bucket index shards",
  "large omap objects", "reshard", "radosgw-admin", "lifecycle not running",
  "rgw accounts", "IAM on ceph". NOT for generic S3 API usage against
  AWS itself; cluster-wide upgrades and CephX rotation are
  rook-ceph-best-practices; RADOS-level health is ceph-troubleshooting.
argument-hint: "[security|compat|sharding|multisite|rook] (optional focus area)"
---

# ceph-s3

Defaults read from `src/common/options/rgw.yaml.in` at v19.2.6 and v20.2.4;
Rook docs at v1.20.7 and master; tracker and ceph-users as cited. Verified
**2026-09-23**.

## 19.2.6 / 20.2.4 RGW security fixes and their fallout

| CVE | What | Fixed |
|---|---|---|
| CVE-2026-54330 | SigV4 did not check that added `x-amz-*` headers on a presigned request were signed | 19.2.6, 20.2.4 |
| CVE-2026-39944 | STS session-token fields (`is_admin`, account type) could be bit-flipped → RGW admin | 19.2.6, 20.2.4 |
| CVE-2025-30156 | CephX (cluster-wide, not RGW-only) — see rook-ceph-best-practices | 19.2.6, 20.2.4 |

The SigV4 fix breaks two things:

1. **Presigned PUTs from some clients** (restic, PHP SDKs) that send an
   unsigned `Content-Type` — rejected (tracker 79674).
   Workaround: `ceph config set client.rgw rgw_sigv4_insecure true`, until
   19.2.7 / 20.2.5.
2. **RGW multisite forwarding** (non-master zone → master, e.g. bucket
   create): `403 AccessDenied` even with every cluster patched
   (tracker 79698). `rgw_sigv4_insecure` alone does **not** fix it. Set both
   `rgw_sigv4_insecure: "true"` and `rgw_s3_client_max_sig_ver: "2"` in every
   zone **before** upgrading. Under Rook, put them in the CephObjectStore
   `gateway` config or `rook-config-override`.

Both workarounds re-open CVE-2026-54330: scope them to the affected
clients/zones and revert (`"false"` / `"-1"`) once everything runs a fixed
release.

## AWS SDK checksums

AWS SDKs released from early 2025 send checksums on every supported request
by default (`x-amz-checksum-*`, often trailing CRC32/CRC64NVME). RGW learned
CRC64NVME only in **Tentacle 20.2.0** (tracker 70040, ceph/ceph#61878); the
Squid backport (tracker 70736) is still **not shipped**.

On Squid, set the client to send checksums only when required:
`AWS_REQUEST_CHECKSUM_CALCULATION=when_required` and
`AWS_RESPONSE_CHECKSUM_VALIDATION=when_required` (env or SDK config), or
pin the SDK/tool to a version before the change.

## Bucket index and resharding

| Option | Default |
|---|---|
| `rgw_dynamic_resharding` | true |
| `rgw_max_objs_per_shard` | 100 000 |
| `rgw_max_dynamic_shards` | 1999 |
| `osd_deep_scrub_large_omap_object_key_threshold` | 200 000 keys |

- `LARGE_OMAP_OBJECTS` on an index pool = a bucket index shard over the
  key threshold: `radosgw-admin bucket limit check`, then
  `radosgw-admin bucket reshard --bucket <b> --num-shards <n>`. The warning
  clears only after the next deep scrub of that PG.
- Squid: resharding a very large bucket blocks writes for minutes (clients
  see 5xx). Tentacle's two-phase reshard does the heavy copy before
  blocking. On Squid, reshard large buckets in a quiet window or pre-shard
  at creation.
- Multisite: never run `radosgw-admin reshard stale-instances rm` — the
  docs forbid stale-instance cleanup in multisite deployments.

## Lifecycle and GC

- Lifecycle runs only in `rgw_lifecycle_work_time` (default `00:00-06:00`)
  with `rgw_lc_max_worker` 3. "Lifecycle not running" at midday is usually
  the window. Check `radosgw-admin lc list`; `radosgw-admin lc process` runs
  it now.
- Deleted objects' tail data waits `rgw_gc_obj_min_wait` (2 h) before GC;
  pool usage drops late by design. `radosgw-admin gc list --include-all`.
- Never `radosgw-admin bucket rm --bypass-gc` on buckets that received
  S3 CopyObject copies on affected releases: tracker 73348 (silent data
  corruption of shared tail objects; fixed in the dev tree, affected
  19.2.2 per the tracker).

## Tentacle S3 behaviour changes

- `LastModified` is truncated to the second for AWS parity — timestamps on
  existing objects can appear to move backwards after the upgrade; sync
  tools comparing mtimes may re-copy.
- `GetObjectAttributes` is supported.
- Tenant-level IAM APIs (CreateRole, PutRolePolicy, PutUserPolicy) and
  STS Lite / `GetSessionToken` are deprecated in favour of RGW accounts.
- New EC pools default to ISA-L — relevant for EC data pools.
- Squid → Tentacle under Rook: RGW rolls before the OSDs finish, breaking
  multipart uploads in the window (rook#18367) — see
  rook-ceph-best-practices.

## Rook object CRDs

| Need | Use | Status (v1.20.7) |
|---|---|---|
| Bucket for an app | `ObjectBucketClaim` + StorageClass | Stable, documented default |
| Kubernetes-native buckets | COSI (`CephCOSIDriver`, `BucketClaim`) | **Experimental**; the COSI controller repo has moved — take the URL from the current Rook `cosi.md` |
| Users and keys | `CephObjectStoreUser` (`spec.keys` to supply keys) | Stable; since v1.17 undeclared extra keys are purged |
| RGW accounts / IAM | `CephObjectStoreAccount`, `accountRef` on users | **Experimental — only works with `quay.ceph.io/ceph-ci/ceph:main`**, no released Ceph |
| Notifications | `CephBucketTopic` + `CephBucketNotification` | Kafka SASL via `mechanism` + secret refs; topics are owned by their creating user |
| Multisite | `CephObjectRealm` / `ZoneGroup` / `Zone` | Set the SigV4 workaround above before 19.2.6 / 20.2.4 |

## References

- `references/sources.md` — every source with its verification stamp.
- Sibling skills: `rook-ceph-best-practices`, `ceph-troubleshooting`,
  `ceph-performance`.
