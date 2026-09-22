# Sources

Freshened: 2026-09-23 — every row probed at creation. Rook releases enumerated unfiltered through v1.20.7; Ceph through 19.2.6 / 20.2.4.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Rook releases | https://github.com/rook/rook/releases | 2026-09-23 | v1.16.0 (2024-12-17) … v1.19.11 / v1.20.7 (2026-09-02). Dates from `gh api repos/rook/rook/releases`. |
| Rook CephX key rotation doc | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Advanced/cephx-key-rotation.md | 2026-09-23 | Identical at v1.19.11. Key categories, six health codes, CSI migration/revert, `allowedCiphers` recovery, FIPS 7.2, quick-fix patch with the `v1.20.4-20260818` image typo. |
| Rook Ceph upgrade doc | https://github.com/rook/rook/blob/v1.20.7/Documentation/Upgrade/ceph-upgrade.md | 2026-09-23 | Supported Ceph (19.2.0+, 20.2.1+), 20.2.0 not recommended, HEALTH_ERR refusal at update request, disable rook mgr module, tag forms. |
| Rook upgrade doc | https://github.com/rook/rook/blob/v1.20.7/Documentation/Upgrade/rook-upgrade.md | 2026-09-23 | v1.19.5+ floor before v1.20; chart order rook-ceph → ceph-csi-drivers → rook-ceph-cluster. |
| rook-ceph-cluster chart values | https://github.com/rook/rook/blob/v1.20.7/deploy/charts/rook-ceph-cluster/values.yaml | 2026-09-23 | `mgr.modules: [{name: rook, enabled: false}]` default at v1.19.11 and v1.20.7. |
| Rook CVE advisory | https://github.com/rook/rook/issues/18203 | 2026-09-23 | Open. Multi-hop path; floors raised to v1.19.10 / v1.20.6 in a maintainer comment. |
| Rotation outage / stale toolbox | https://github.com/rook/rook/issues/18240 | 2026-09-23 | Open. Floating `:v20` + IfNotPresent → `Malformed input`; OSD key stuck at generation 1; maintainer: no workarounds, no restarts, collect operator log. |
| CSI RBAC missing after v1.20 | https://github.com/rook/rook/issues/17644 | 2026-09-23 | Closed. Cause: `ceph-csi-drivers` chart not installed. |
| Tentacle mgr crash loop | https://github.com/rook/rook/issues/18124 | 2026-09-23 | Open. Ceph tracker 79106 (fix), 79357 (crash module EIO). |
| mgr OOM after v1.20.1 / 20.2.2 | https://github.com/rook/rook/issues/17786 | 2026-09-23 | Open. Rook-module logging + tracker 77724 refcount leak. |
| Squid→Tentacle RGW/MDS rolled before OSDs | https://github.com/rook/rook/issues/18367 | 2026-09-23 | Closed. Breaks S3 multipart during the window. |
| Kernel 7.0 mon cold-bootstrap | https://github.com/rook/rook/issues/18370 | 2026-09-23 | Closed upstream as a Ceph msgr issue; tracker https://tracker.ceph.com/issues/80470. |
| 20.2.0 read-affinity corruption | https://github.com/rook/rook/issues/16839 | 2026-09-23 | Closed. |
| ceph-csi-operator image fallback | https://github.com/ceph/ceph-csi-operator/issues/605 | 2026-09-23 | Closed. `imageSet.name` not set by `ceph-csi-drivers` chart. |
| Ceph 19.2.6 / 20.2.4 combo release | https://ceph.io/en/news/blog/2026/v20-2-4-v19-2-6-combo-released/ | 2026-09-23 | 2026-08-19. CVE-2025-30156, CVE-2026-39944, CVE-2026-50152, CVE-2026-54330; AES256K; six health codes; multisite `rgw_sigv4_insecure`. |
| Ceph releases index | https://docs.ceph.com/en/latest/releases/ | 2026-09-23 | Reef EOL (18.2.8, 2026-03-20); Squid, Tentacle active. No Umbrella release. |
| Ceph 18.2.7 hotfix | https://ceph.io/en/news/blog/2025/v18-2-7-reef-released/ | 2026-09-23 | 18.2.5/18.2.6 BlueStore regression. |
| Ceph auth config reference | https://docs.ceph.com/en/latest/rados/configuration/auth-config-ref/ | 2026-09-23 | `auth_allowed_ciphers`, `auth_preferred_cipher`, `ceph auth rotate --key-type`. |
| Ceph tags (Umbrella) | https://github.com/ceph/ceph/tags | 2026-09-23 | v21.1.1 → v21.3.0 dev tags, no v21.2.0. |
| Linux libceph AES256K | https://github.com/torvalds/linux/blob/master/net/ceph/crypto.c | 2026-09-23 | `CEPH_CRYPTO_AES256KRB5`; commit "libceph: add support for CEPH_CRYPTO_AES256KRB5" (2025-12-22), Linux 7.0. |
| ceph-users: rotation lockout / mon rebuild | https://lists.ceph.io/hyperkitty/list/ceph-users@ceph.io/ | 2026-09-23 | Threads 2026-08-27 (rotating-key warning persists), 2026-09-11 (mon `--mkfs` → PGLog crash, 278 unfound), 2026-09-14 (1500-OSD mon slow ops on 19.2.6). |
| Tracker 80295 | https://tracker.ceph.com/issues/80295 | 2026-09-23 | "Upgrade 19.2.6 to 20.2.4 changes auth_allowed_ciphers config" (Orchestrator). |
| Tracker 79674 | https://tracker.ceph.com/issues/79674 | 2026-09-23 | SigV4 rejects unsigned Content-Type, breaking presigned PUT; regression in 19.2.6 / 20.2.4. |
| mon_auth_emergency_allowed_ciphers | https://github.com/ceph/ceph/blob/v19.2.6/src/common/options/mon.yaml.in | 2026-09-23 | `type: str`. |
| CVE-2021-20288 (global_id reclaim) | https://docs.ceph.com/en/latest/security/CVE-2021-20288/ | 2026-09-23 | The older AUTH_INSECURE_GLOBAL_ID_RECLAIM* codes the new ones are confused with. |
