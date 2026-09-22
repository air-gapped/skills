# Sources

Freshened: 2026-09-23 — every row probed at creation.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Ceph OSD options | https://github.com/ceph/ceph/blob/v19.2.6/src/common/options/osd.yaml.in | 2026-09-23 | Same values at v17.2.8, v18.2.8, v20.2.4: `osd_op_queue` mclock_scheduler, `osd_mclock_profile` balanced, `osd_mclock_override_recovery_settings` false, `osd_max_backfills` 1, `osd_scrub_auto_repair` false, iops thresholds HDD 500 / SSD 80000, `osd_mclock_max_capacity_iops_ssd` 21500, `osd_op_complaint_time` 30. |
| Ceph global options | https://github.com/ceph/ceph/blob/v19.2.6/src/common/options/global.yaml.in | 2026-09-23 | nearfull 0.85, backfillfull 0.9, full 0.95, failsafe 0.97; `osd_memory_target` 4G; `osd_memory_target_cgroup_limit_ratio` 0.8; `bluestore_slow_ops_warn_lifetime` 86400, `_threshold` 1. |
| mClock config reference | https://docs.ceph.com/en/squid/rados/configuration/mclock-config-ref/ | 2026-09-23 | Locked recovery knobs, override flag, capacity fallback when bench exceeds threshold. |
| PG troubleshooting | https://docs.ceph.com/en/latest/rados/troubleshooting/troubleshooting-pg/ | 2026-09-23 | inconsistent, stuck peering, unfound / mark_unfound_lost. No sections for incomplete/unknown/down. |
| PG states | https://docs.ceph.com/en/latest/rados/operations/pg-states/ | 2026-09-23 | Definitions for down, incomplete (restart OSDs; EC: lower min_size), unknown. |
| BLUESTORE_SLOW_OP_ALERT Reef backport | https://github.com/ceph/ceph/pull/59466 | 2026-09-23 | Merged 2024-11-28 into reef. |
| Rook disaster recovery | https://github.com/rook/rook/blob/v1.20.7/Documentation/Troubleshooting/disaster-recovery.md | 2026-09-23 | restore-quorum via plugin; CRD / namespace recovery procedures. |
| Rook OSD management | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Advanced/ceph-osd-mgmt.md | 2026-09-23 | Operator scale-down on host clusters, `kubectl rook-ceph rook purge-osd`, osd-purge Job. |
| Rook CSI common issues | https://github.com/rook/rook/blob/v1.20.7/Documentation/Troubleshooting/ceph-csi-common-issues.md | 2026-09-23 | Node loss: force delete, 8–10 min, blocklist add/rm. |
| kubectl-rook-ceph | https://github.com/rook/kubectl-rook-ceph | 2026-09-23 | v0.9.6 (2026-03-31); command list from README. |
| Rook osd-memory derivation | https://lists.ceph.io/hyperkitty/list/dev@ceph.io/thread/2JVNE27TOJCJFQ76OEOUV3OTDTRRAYZ2/ | 2026-09-23 | Request 1:1, else limit × ratio. |
| Kernel 7.0 mon cold bootstrap | https://github.com/rook/rook/issues/18370 | 2026-09-23 | Closed upstream as Ceph-side; tracker https://tracker.ceph.com/issues/80470. |
| osd lvs hang | https://github.com/rook/rook/issues/18402 | 2026-09-23 | Open. |
| Tentacle EC optimizations crash | https://github.com/ceph/ceph.io/issues/1009 | 2026-09-23 | Website repo; no tracker id linked. |
| 18.2.7 hotfix | https://ceph.io/en/news/blog/2025/v18-2-7-reef-released/ | 2026-09-23 | 18.2.5/18.2.6 BlueStore regression. |
| 20.2.0 read affinity | https://github.com/rook/rook/issues/16839 | 2026-09-23 | Closed. |
| ceph-users field reports | https://lists.ceph.io/hyperkitty/list/ceph-users@ceph.io/ | 2026-09-23 | 2026-07-09 Tentacle RGW latency; 2026-09-11 mon `--mkfs` → PGLog crash; 2026-09-14 1500-OSD mon slow ops. |
