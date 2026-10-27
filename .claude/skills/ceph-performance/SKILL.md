---
name: ceph-performance
description: >-
  Tune and benchmark a healthy Ceph cluster, with Rook-on-Kubernetes
  specifics: mClock profiles and the NVMe capacity-fallback trap
  (osd_mclock_max_capacity_iops), osd_memory_target from pod requests,
  BlueStore allocation and cache defaults, PG autoscaler targets
  (mon_target_pg_per_osd, bulk, target_size_ratio), public/cluster network
  and Multus choices, msgr2 modes, Tentacle Fast EC (allow_ec_optimizations,
  stripe_unit), krbd vs rbd-nbd in ceph-csi, librbd cache, and benchmark
  method (rados bench, rbd bench, fio). Squid 19.2 and Tentacle 20.2.
when_to_use: >-
  Use when making a working Ceph cluster faster or sizing one: "ceph
  performance", "tune ceph", "mclock profile", "osd_mclock_max_capacity_iops",
  "NVMe OSD slow", "IOPS lower than expected", "osd_memory_target", "OSD
  memory sizing rook", "bluestore_min_alloc_size", "pg autoscaler",
  "mon_target_pg_per_osd", "how many PGs", "bulk pool", "cluster network",
  "public network", "multus ceph", "host network rook", "msgr2 secure mode
  overhead", "erasure coding performance", "allow_ec_optimizations", "fast
  EC", "stripe_unit", "crimson", "seastore", "krbd vs rbd-nbd", "rbd cache",
  "rados bench", "fio rbd", "benchmark ceph". NOT for a degraded or
  erroring cluster (slow recovery, slow ops, full OSDs) — that is
  ceph-troubleshooting; upgrades are rook-ceph-best-practices; RGW/S3
  behaviour is ceph-s3.
argument-hint: "[mclock|memory|pg|network|ec|client|bench] (optional focus area)"
---

# ceph-performance

Defaults below hold at Ceph v19.2.7 and v20.2.4
(`src/common/options/*.yaml.in`) and Rook v1.21.1; sources in
`references/sources.md`.
Measure before and after every change; `ceph config show osd.N <opt>` is
the value actually in force.

## mClock: the NVMe capacity trap

mClock sizes every reservation from each OSD's measured IOPS capacity. At
OSD start an `osd bench` sets `osd_mclock_max_capacity_iops_{hdd,ssd}`.
If the result exceeds the sanity threshold — **500 (HDD), 80 000 (SSD)** —
it is discarded and the OSD falls back to the default capacity
(**21 500** SSD) with a cluster-log warning. Modern NVMe routinely exceeds
80 000, so mClock under-drives it.

1. `ceph config show osd.N osd_mclock_max_capacity_iops_ssd` on every OSD;
   `21500` means the fallback hit.
2. Measure the device with fio at 4 KiB random write, then
   `ceph config set osd.N osd_mclock_max_capacity_iops_ssd <iops>`.
3. Re-check after replacing a device — the value is per OSD.

Profiles: `balanced` is the default from 17.2.7 and in Reef, Squid and
Tentacle (17.2.0–17.2.6 shipped `high_client_ops`). Use `high_client_ops`
for latency-sensitive steady state, `high_recovery_ops` only for a
maintenance window.

## Memory

- Under Rook, Ceph sets `osd_memory_target` = min(`POD_MEMORY_REQUEST`,
  limit × `osd_memory_target_cgroup_limit_ratio` (0.8)); with only a
  limit, target = limit × 0.8. Set requests and limits explicitly on
  `spec.resources.osd` with limit ≥ request ÷ 0.8 (1.25×) — a tighter
  limit pulls the target below the request. The target is a cache-trim
  goal, not a cap, so the limit needs that headroom anyway. Confirm with
  `ceph config show osd.N osd_memory_target` after the pods restart.
- Rook's own minimums (warns below): osd 2048 MB, mon 1024 MB, mgr 512 MB.
  4 GiB+ per OSD is the Ceph default target; NVMe OSDs benefit from more.
- `bluestore_cache_autotune` is on by default; `osd_memory_target_autotune`
  (cephadm) is off and irrelevant under Rook.
- `mds_cache_memory_limit` defaults to 4 GiB; the MDS uses more than this —
  size its pod limit well above it.

## BlueStore allocation and WAL

`bluestore_min_alloc_size_hdd` and `_ssd` are both **4 KiB**. The "64 KiB
on HDD" advice is obsolete. The value is baked in at OSD creation; changing
it needs the OSD redeployed.

Tentacle turns on `bluefs_wal_envelope_mode` (default true; absent in
Squid). It cuts RocksDB-WAL `fdatasync` calls by about half, so
DB/WAL-device IOPS fall after the upgrade. Expected — do not chase that
drop as a fault.

## PG autoscaler

| Knob | Default | Guidance |
|---|---|---|
| `mon_target_pg_per_osd` (mgr option) | 100 | Docs recommend **200** for all but the smallest clusters; above 500 costs peering and RAM |
| pool `bulk` flag | false | Set on pools that will hold most of the data so they start with a full PG count instead of growing |
| `target_size_ratio` | unset | Set on each large pool; otherwise the autoscaler sizes from current usage only |
| `pg_num_min` / `pg_num_max` | unset | Bound pools the autoscaler keeps shrinking |

## Network

- A separate cluster network is **optional**: current docs say public-only
  "functions just fine … especially with 25GE or faster"; add one for high
  client traffic or ≤10 GE links.
- Rook: host networking removes pod-network latency but gives no isolation;
  Multus gives isolation — use CNI `macvlan` with `whereabouts` IPAM (the
  documented path). Validate with `kubectl rook-ceph multus validation run`.
- msgr2 mode defaults are `crc secure` for cluster, service and client:
  CRC is used unless a peer requires secure. Forcing `secure` everywhere
  encrypts all traffic and costs CPU/throughput — benchmark before and after.

## Erasure coding (Tentacle)

- New pools default to the **ISA-L** plugin (Jerasure before); existing
  pools keep their plugin on upgrade.
- Fast EC: `ceph osd pool set <pool> allow_ec_optimizations true` — partial
  reads/writes, parity-delta writes; 2–3× small-I/O gains in Ceph's own
  benchmark. **Irreversible** for the pool. Works with Jerasure and ISA-L
  `reed_sol_van`.
- `stripe_unit` is fixed at pool creation: 16 KiB for general workloads,
  up to 256 KiB for read-heavy; the old 4 KiB default gains less. Create a
  new pool rather than flipping the flag on an old 4 KiB one.
- Enable it only where `(stripe_width / k) % 4096 == 0` (read both from
  `ceph osd pool ls detail` and the EC profile). On 20.2.0 a non-4 KiB-
  aligned chunk size crash-loops every OSD serving the pool
  (`interval_set.h:365`) with no way back; 20.2.1+ refuses the flag on
  such pools. Upgrade to ≥ 20.2.1 first.
- Replicated size 3 still outperforms EC; EC wins on cost per byte.

## Crimson / SeaStore

Tentacle docs: "tech preview stage and is not suitable for production use".
Do not recommend it for production.

## Clients (ceph-csi)

- RBD PVCs use **krbd** by default. `mounter: rbd-nbd` is Alpha, not for
  production. CephFS uses the kernel client by default, ceph-fuse on request.
- librbd cache settings (`rbd_cache` true, `rbd_cache_policy`
  `writearound`, `rbd_readahead_max_bytes` 512 KiB) apply to librbd and
  rbd-nbd only — they do nothing for krbd PVCs. The same holds for librbd
  `rbd_qos_*` limits.
- Per-PVC IOPS/bandwidth caps on krbd (noisy neighbour): Rook ≥ 1.21,
  Kubernetes ≥ 1.34, cgroup v2, kernel ≥ 5.8. Create a
  `VolumeAttributesClass` with `maxReadIops`/`maxWriteIops`/`maxReadBps`/
  `maxWriteBps` and set it as the PVC's `volumeAttributesClassName`. The
  StorageClass needs the `controller-modify-secret-*` and
  `node-publish-secret-*` parameters; recreate it if they are missing.

## Benchmarking

| Layer | Tool | Watch |
|---|---|---|
| RADOS | `rados bench -p <pool> 60 write --no-cleanup`, then `seq` / `rand`, then `rados -p <pool> cleanup` | Without `--no-cleanup` the read phases have nothing to read |
| RBD | `rbd bench --io-type write --io-size 4K --io-pattern rand` | Bypasses the kernel; not what a krbd PVC sees |
| PVC path | fio inside a pod on the PVC (`--direct=1`) | Matches krbd + filesystem, the real client path |
| Cluster-wide | CBT (`ceph/cbt`) | Repeatable multi-client runs |

Run several clients in parallel — one client cannot saturate a cluster —
and use a dataset larger than the OSD caches.

## Field reports

| Report | Source |
|---|---|
| 18.2.4 → 20.2.1, RGW on 2-zone multisite, hybrid HDD + NVMe-DB, 9 clusters: PUT latency 3–4×, GET and HEAD worse (HEAD ~5×). 20.2.3 does not fix it; re-indexing or re-creating the bucket restores latency for about a week. Unresolved. Unconfirmed on-list suspect: the GET/HEAD replication-status check reading the bucket bilog — test with `ceph tell osd.N compact` on the index-pool OSDs and watch `radosgw-admin bilog list --bucket=<b>` grow | ceph-users, 2026-07-09 to 2026-09-24 |

## References

- `references/sources.md` — every source with its verification stamp.
- Sibling skills: `ceph-troubleshooting`, `rook-ceph-best-practices`,
  `ceph-s3`.
