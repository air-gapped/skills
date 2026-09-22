---
name: ceph-troubleshooting
description: >-
  Diagnose and recover an unhealthy Ceph cluster, with Rook-on-Kubernetes
  specifics: slow or stuck recovery/backfill under the mClock scheduler
  (why osd_max_backfills "does nothing"), nearfull/backfillfull/full,
  inconsistent/unfound/incomplete/down PGs, BLUESTORE_SLOW_OP_ALERT vs
  SLOW_OPS, OSD OOM kills from pod memory sizing, mon quorum loss and
  restore-quorum, OSD removal with the kubectl-rook-ceph plugin, stale RBD
  watchers after node loss, and field-reported failure modes on Squid 19.2
  and Tentacle 20.2.
when_to_use: >-
  Use when a Ceph or Rook-Ceph cluster is unhealthy or misbehaving: "ceph
  health detail", "HEALTH_WARN", "HEALTH_ERR", "recovery is slow",
  "backfill stuck", "osd_max_backfills not working", "mclock", "PG
  inconsistent", "pg repair", "unfound objects", "mark_unfound_lost", "PG
  incomplete", "PG down", "PG unknown", "slow ops", "BLUESTORE_SLOW_OP_ALERT",
  "OSD OOMKilled", "osd_memory_target", "nearfull", "backfill_toofull",
  "OSD full", "mon quorum lost", "restore-quorum", "remove an OSD",
  "purge-osd", "kubectl rook-ceph", "RBD image has watchers", "PVC won't
  attach after node died", "blocklist". NOT for planned Rook/Ceph upgrades
  or the AES256K key rotation — that is rook-ceph-best-practices; tuning a
  healthy cluster is ceph-performance; RGW/S3 behaviour is ceph-s3.
argument-hint: "[recovery|pg|osd|mon|csi] (optional focus area)"
---

# ceph-troubleshooting

Defaults below were read from `src/common/options/*.yaml.in` at v18.2.8,
v19.2.6 and v20.2.4 on **2026-09-23**; procedures from docs.ceph.com and
Rook docs at v1.20.7. On a live cluster, `ceph config show osd.N <opt>` beats
any default written here.

## First moves

1. `ceph health detail` — work from the codes, not from `ceph status`.
2. Under Rook, run Ceph commands through the toolbox or
   `kubectl rook-ceph ceph <args>` (plugin v0.9.6, 2026-03-31). If the
   toolbox fails with `handle_auth_bad_method` / errno 13 right after a
   Ceph upgrade, it is a key rotation, not an outage — see
   rook-ceph-best-practices.
3. `AUTH_INSECURE_*` codes on 19.2.6+ / 20.2.4+ belong to the CVE-2025-30156
   rotation (rook-ceph-best-practices), not to this skill.

## Recovery and backfill are slow — mClock

`osd_op_queue` defaults to `mclock_scheduler` on Quincy through Tentacle.
Under mClock, `osd_max_backfills` and `osd_recovery_max_active*` are
**locked**: `ceph config set` reports success and the value is reverted to
the profile's built-in. This is the usual "raised backfills, nothing
changed" report.

| Goal | Do |
|---|---|
| Faster recovery, accept client latency | `ceph config set osd osd_mclock_profile high_recovery_ops` (revert to `balanced` afterwards) |
| Use the classic knobs anyway | `ceph config set osd osd_mclock_override_recovery_settings true`, then set `osd_max_backfills` / `osd_recovery_max_active` |
| Check what is really in force | `ceph config show osd.N osd_max_backfills` (not `ceph config get`) |

Default profile: `balanced` from 17.2.7 on (17.2.0–17.2.6 shipped
`high_client_ops`). Undo both settings when recovery finishes; leaving
`high_recovery_ops` on starves clients.

An OSD whose measured IOPS exceed the sanity threshold (HDD 500, SSD 80 000)
is not trusted by mClock and falls back to the default capacity
(`osd_mclock_max_capacity_iops_ssd` = 21 500). Fast NVMe is routinely
under-driven this way; see ceph-performance.

## Capacity

| Ratio | Default | Effect |
|---|---|---|
| `mon_osd_nearfull_ratio` | 0.85 | `OSD_NEARFULL` warning |
| `mon_osd_backfillfull_ratio` | 0.90 | backfill *into* that OSD stops — PGs show `backfill_toofull` |
| `mon_osd_full_ratio` | 0.95 | cluster stops accepting writes |
| `osd_failsafe_full_ratio` | 0.97 | OSD refuses writes regardless |

Keep nearfull < backfillfull < full < failsafe. To get out of `full`: raise
`ceph osd set-full-ratio` by 0.01–0.02 only long enough to delete data or
add capacity, then set it back. `backfill_toofull` during a rebalance means
the *target* is full — reweight or add OSDs; raising backfillfull only moves
the cliff.

## PG states

| State | Do | Never |
|---|---|---|
| `inconsistent` | `rados list-inconsistent-obj <pgid> --format=json-pretty`, then `ceph pg repair <pgid>`. `osd_scrub_auto_repair` defaults to **false**. | Repair before reading which copy is bad when the error is on the primary. |
| `recovery_unfound` / unfound | `ceph pg <pgid> list_unfound`; bring back every down OSD first; last resort `ceph pg <pgid> mark_unfound_lost revert\|delete` (`revert` does not exist for EC pools; it can roll data back silently). | Mark lost while any OSD that might hold the object can still start. |
| `incomplete` | Start the failed OSDs that held the PG. EC pool short of shards: lower `min_size` temporarily, recover, restore it. | Leave `min_size` lowered. |
| `down` | A replica with needed data is offline: `ceph pg <pgid> query` → `blocked_by`; start those OSDs. | `ceph osd lost` unless the OSD is truly unrecoverable. |
| `unknown` | The mgr has not heard from the PG's OSDs since mgr start. Wait one report interval; if it persists, check mgr and OSD connectivity. | Act on PG data. |
| stuck `peering` | `ceph pg <pgid> query`, start the blocking OSDs. | — |

## Slow ops

- `SLOW_OPS`: client ops older than `osd_op_complaint_time` (30 s).
- `BLUESTORE_SLOW_OP_ALERT`: BlueStore-internal slow ops — count in the last
  `bluestore_slow_ops_warn_lifetime` (86 400 s) ≥
  `bluestore_slow_ops_warn_threshold` (1). Arrived via a Reef backport
  (ceph/ceph#59466, 2024-11-28). Points at the device or its DB/WAL, not the
  network: check `ceph daemon osd.N dump_historic_ops`, device health, and
  BlueFS spillover.
- A warning that clears within 24 h of a one-off stall is this lifetime
  window, not a recurring problem.

## OSD OOM kills under Rook

Rook injects `POD_MEMORY_REQUEST` / `POD_MEMORY_LIMIT`; Ceph uses the
**request 1:1** as `osd_memory_target`, else **limit** ×
`osd_memory_target_cgroup_limit_ratio` (0.8). The 0.8 never applies to the
request. With neither
set, the target is not tied to the pod and OSDs get OOM-killed on busy
nodes. Always set `spec.resources.osd.requests.memory` (and a limit with
headroom) in the CephCluster; verify with
`ceph config show osd.N osd_memory_target`. Ceph's default is 4 GiB.

## Mon quorum lost (Rook)

1. If at least one mon is healthy:
   `kubectl rook-ceph mons restore-quorum <healthy-mon>` — it scales the
   operator down, edits the monmap, and asks for `yes-really-restore`, then
   `continue` before Rook recreates the other mons.
2. Never re-create a mon store (`monmaptool --mkfs`, a fresh mon) to force
   quorum: on 20.2.4 an operator did that during the AES256K rollout and OSDs
   crashed in `PGLog::merge_log` with 278 unfound objects (ceph-users
   2026-09-11).
3. A **new** HA mon quorum that never forms on Linux 7.0 nodes (existing
   quorums unaffected): rook#18370 / tracker 80470. With kube-proxy in IPVS
   mode, check `net.netfilter.nf_conntrack_tcp_be_liberal=1` and
   `net.ipv4.vs.conn_reuse_mode=0`; fixing those alone did not resolve every
   report.

Other disaster procedures (CRDs stuck in Deleting, adopting a cluster into a
new Kubernetes cluster, rebuilding after the Rook namespace was deleted):
Rook `Documentation/Troubleshooting/disaster-recovery.md`.

## Removing an OSD (Rook)

1. Host-based clusters: scale the operator to 0 first, or it re-creates the
   OSD before the disk is wiped. PVC-based: lower the device-set `count`
   instead.
2. `kubectl -n rook-ceph scale deployment rook-ceph-osd-<ID> --replicas=0`,
   `ceph osd down osd.<ID>`.
3. `kubectl rook-ceph rook purge-osd <ID>[,<ID>…] [--force]` (or the
   `osd-purge.yaml` Job).
4. Wipe or replace the disk, then scale the operator back to 1.
5. Confirm `ceph auth ls` has no `osd.<ID>` left — a leftover auth entity
   shows up later as an insecure-key HEALTH_ERR after the AES256K rotation.

`osd`/`osd-prepare` pods hanging on `lvs` while other OSDs on the node are
down: rook#18402 (open).

## PVC will not attach after a node died

1. Force-delete the stuck pod; wait 8–10 min.
2. Still stuck: `ceph osd blocklist add <NODE_IP>` so the volume can move.
3. `rbd status <pool>/<image>` — if the dead client still shows as a watcher,
   the map keeps failing even though it is blocklisted; wait out the watch
   timeout or evict the watcher before retrying.
4. When the node is gone for good: `ceph osd blocklist rm <NODE_IP>`.

Rook's `NetworkFence` CR automates the blocklist step.

## kubectl-rook-ceph commands models tend not to know

`rook purge-osd`, `maintenance start|stop <deployment>` (run a daemon with an
alternate image for debugging), `mons restore-quorum`, `subvolume ls --stale`
/ `subvolume delete`, `cephfs-snap ls --orphaned`, `restore-deleted <CRD>`,
`multus validation run`, `dr health`, `operator restart`, `rook status all`.

## Field reports (2026)

| Report | Source |
|---|---|
| 18.2.8 → 19.2.6 on ~1500 OSDs: every mon restart spiked `mon.X has slow ops` into the tens of thousands; only a manual mon restart cleared it; staging did not reproduce | ceph-users 2026-09-14 |
| 18.2.4 → 20.2.1 on hybrid HDD + NVMe-DB clusters: RGW PUT latency 3–4×, DB-device IOPS near zero; unresolved | ceph-users 2026-07-09 |
| Tentacle 20.2.0: enabling `allow_ec_optimizations` on an EC pool that already had `ec_overwrites` crash-looped OSDs (`interval_set.h:365`) | ceph/ceph.io#1009 (no tracker id) |
| Do not run 18.2.5 / 18.2.6 (BlueStore corruption) or 20.2.0 with CSI read affinity | ceph.io 18.2.7 post; rook#16839 |

## References

- `references/sources.md` — every source with its verification stamp.
- Sibling skills: `rook-ceph-best-practices` (upgrades, key rotation),
  `ceph-performance`, `ceph-s3`.
