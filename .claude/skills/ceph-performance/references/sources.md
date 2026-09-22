# Sources

Freshened: 2026-09-23 — every row probed at creation.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Ceph OSD options | https://github.com/ceph/ceph/blob/v20.2.4/src/common/options/osd.yaml.in | 2026-09-23 | iops thresholds HDD 500 / SSD 80000; `osd_mclock_max_capacity_iops_ssd` 21500; `osd_mclock_profile` balanced (high_client_ops at v17.2.0–v17.2.6). |
| Ceph global options | https://github.com/ceph/ceph/blob/v20.2.4/src/common/options/global.yaml.in | 2026-09-23 | `bluestore_min_alloc_size_hdd`/`_ssd` 4K; `bluestore_cache_autotune` true; `osd_memory_target_autotune` false; `osd_memory_target` 4G; cgroup ratio 0.8; `ms_{cluster,service,client}_mode` "crc secure". |
| Ceph mgr options | https://github.com/ceph/ceph/blob/v20.2.4/src/common/options/mgr.yaml.in | 2026-09-23 | `mon_target_pg_per_osd` 100. |
| Ceph MDS / RBD options | https://github.com/ceph/ceph/blob/v20.2.4/src/common/options/rbd.yaml.in | 2026-09-23 | `rbd_cache` true, `rbd_cache_policy` writearound, `rbd_readahead_max_bytes` 512K; mds.yaml.in `mds_cache_memory_limit` 4G. |
| Pod memory → target | https://github.com/ceph/ceph/blob/v19.2.6/src/common/config.cc | 2026-09-23 | `POD_MEMORY_REQUEST` 1:1; limit × ratio only as default. |
| mClock config reference | https://docs.ceph.com/en/squid/rados/configuration/mclock-config-ref/ | 2026-09-23 | Bench above threshold → fallback to default capacity, warning, set manually after fio. |
| PG placement / autoscaler | https://docs.ceph.com/en/latest/rados/operations/placement-groups/ | 2026-09-23 | 200 recommended for all but the smallest clusters; >500 costs peering/RAM; bulk; target_size_ratio. |
| Network config reference | https://docs.ceph.com/en/tentacle/rados/configuration/network-config-ref/ | 2026-09-23 | Public-only "functions just fine … especially with 25GE or faster". |
| Rook network providers | https://github.com/rook/rook/blob/v1.20.7/Documentation/CRDs/Cluster/network-providers.md | 2026-09-23 | Host network vs Multus; macvlan "highly recommended", whereabouts "recommended". |
| Rook CephCluster CRD | https://github.com/rook/rook/blob/v1.20.7/Documentation/CRDs/Cluster/ceph-cluster-crd.md | 2026-09-23 | Minimum memory: osd 2048MB, mon 1024MB, mgr 512MB; memory declared → osd_memory_target set to it. |
| Erasure code (Tentacle) | https://docs.ceph.com/en/tentacle/rados/operations/erasure-code/ | 2026-09-23 | `allow_ec_optimizations` irreversible; Jerasure/ISA-L reed_sol_van; stripe_unit 16K general, up to 256K read-heavy, fixed at creation. |
| Tentacle release notes | https://docs.ceph.com/en/latest/releases/tentacle/ | 2026-09-23 | ISA-L default for new EC pools; SeaStore alongside Crimson for testing. |
| Fast EC benchmark | https://ceph.io/en/news/blog/2025/tentacle-fastec-performance-updates/ | 2026-09-23 | 2025-11-20; 2–3× small reads, ≥2× small writes vs Squid, single-node test. |
| Crimson status | https://docs.ceph.com/en/tentacle/dev/crimson/crimson/ | 2026-09-23 | "tech preview stage and is not suitable for production use". |
| ceph-csi rbd-nbd | https://github.com/ceph/ceph-csi/blob/devel/docs/design/proposals/rbd-nbd.md | 2026-09-23 | krbd default; rbd-nbd Alpha, not for production. |
| ceph-csi CephFS mounter | https://github.com/ceph/ceph-csi/blob/devel/internal/cephfs/mounter/volumemounter.go | 2026-09-23 | Kernel mounter first; fuse after. |
| Tentacle EC crash | https://github.com/ceph/ceph.io/issues/1009 | 2026-09-23 | 20.2.0, allow_ec_optimizations on an ec_overwrites pool. |
| ceph-users Tentacle RGW latency | https://lists.ceph.io/hyperkitty/list/ceph-users@ceph.io/ | 2026-09-23 | "Performance issue after tentacle upgrade", 2026-07-09. |
