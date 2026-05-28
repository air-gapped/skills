# rook — compat (sifted from release_notes)

- **Primary source:** https://github.com/rook/rook/releases
- **Secondary sources:** https://rook.io/docs/rook/latest-release/, per-tag `Documentation/Upgrade/rook-upgrade.md` + `Documentation/Upgrade/ceph-upgrade.md`
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 1.17
- **Last sifted:** 2026-05-28

## 1.19 (latest: 1.19.6, 2026-05-27)

- **k8s floor:** 1.30 – 1.35
- **Breaking:**
  - K8s minimum bumped to v1.30 (was v1.29 in 1.18).
  - Minimum Ceph is now **v19.2.0** — Reef v18 is dropped. Clusters on Ceph v18 MUST upgrade Ceph to v19.2.0+ BEFORE upgrading Rook to 1.19.
  - `CephFilesystem.activeStandby=false` now scales down the standby MDS deployment entirely (previously kept the daemon running with cache disabled).
  - In external mode, providing a Ceph admin keyring no longer auto-creates CSI Ceph clients — must use the external Python script.
  - Helm: `rook-ceph-cluster` chart relocates Ceph image config. Remove the `cephVersion` block from `cephClusterSpec` and apply the new top-level `cephImage: {repository, tag}` instead — values.yaml drift will conflict.
- **CRD migrations:** `CephFilesystem.activeStandby` semantics change (above); no CRD schema-version bumps.
- **Upgrade ordering:**
  - Ceph v18 → v19.2.0+ BEFORE Rook 1.18 → 1.19. Skipping this strands the cluster.
  - Rook operator before CephCluster (always).
  - Helm: upgrade `rook-ceph` chart before `rook-ceph-cluster`.
- **Deprecations:** Rook-direct CSI settings deprecated — CSI operator is required (was default-but-overridable in 1.18). `ROOK_USE_CSI_OPERATOR: false` escape hatch is gone.
- **Cross-component (Ceph):** **Ceph Squid v19.2.0+ and Ceph Tentacle v20.2.1+.** Tentacle v20.2.0 is NOT recommended — data-corruption risk when `csi.readAffinity.enabled: true`; Rook auto-disables read affinity internally on v20.2.0 as a mitigation. Reef v18 is dropped entirely.
- **Notable:**
  - Ceph CSI v3.16 bundled (NVMe-oF CSI driver, improved RBD/CephFS fencing, block volume stats, configurable block encryption cipher).
  - Experimental: NVMe-oF for RBD volumes (NVMe/TCP exposure inside + outside cluster).
  - Experimental: concurrent CephCluster reconciles via `ROOK_RECONCILE_CONCURRENT_CLUSTERS > 1`.

## 1.18 (latest: 1.18.11, 2026-05-27)

- **k8s floor:** 1.29 – 1.34
- **Breaking:**
  - K8s minimum bumped to v1.29.
  - Ceph CSI operator becomes default — `csi.rookUseCsiOperator: true` (Helm) / `ROOK_USE_CSI_OPERATOR: true` (operator.yaml). Rook auto-converts existing Rook CSI settings to new CSI operator CRs during 1.18.x. Escape hatch: set to `false`.
  - New install requires `csi-operator.yaml` manifest at deploy time.
  - Helm `rook-ceph-cluster`: two new immutable storage-class properties (`controller-publish-secret-name`, `controller-publish-secret-namespace`) — Helm upgrade FAILS unless either the existing StorageClasses are deleted first OR the new params are stripped from values.yaml pre-upgrade (PR #16442).
  - Node topology validation on new CephCluster creation — duplicated topology labels (e.g. `topology.rook.io/rack` across zones) cause cluster creation to fail. Existing clusters: warning only. Bypass: `ROOK_SKIP_OSD_TOPOLOGY_CHECK=true` in `rook-ceph-operator-config` ConfigMap.
  - Helm 3.13+ required (was "latest only"); now supports six most recent minor versions.
- **CRD migrations:** New CSI operator CRs introduced: `cephconnections.csi.ceph.io`, `drivers.csi.ceph.io`, `operatorconfigs.csi.ceph.io`, `clientprofiles.csi.ceph.io`, `clientprofilemappings.csi.ceph.io`. Rook reconciles into these from legacy settings automatically.
- **Upgrade ordering:**
  - StorageClass cleanup BEFORE `rook-ceph-cluster` Helm upgrade (see breaking).
  - Rook operator before CephCluster.
- **Deprecations:** Rook-direct CSI configuration to be removed in 1.19 (announced here, executed there).
- **Cross-component (Ceph):** **Ceph Reef v18.2.0+, Squid v19.2.0+, Tentacle v20.2.0+.** Tentacle v20.2.0 carries the same read-affinity corruption warning as in 1.19 — prefer v20.2.1 once available. Reef v18 still supported here (last Rook minor to do so).
- **Notable:**
  - Ceph CSI v3.15 bundled.
  - Experimental: CephX key rotation (requires Ceph v19.2.3+; admin and mon keys not yet rotatable).
  - Tentacle v20 support landed mid-cycle ("as soon as released" at 1.18.0 GA).

## 1.17 (latest: 1.17.9, 2025-11-13)

- **k8s floor:** 1.28 – 1.33
- **Breaking:**
  - K8s minimum bumped to v1.28.
  - `CephObjectStoreUser`: no more out-of-band multi-credential on the underlying S3 user — Rook purges undeclared credentials. Migration: adopt the new first-class credential-management CRD fields (#15359).
  - OBC additional-config fields locked off by default — operator must set `ROOK_OBC_ALLOW_ADDITIONAL_CONFIG_FIELDS=true` to restore the 1.16 self-serve OBC behavior (#15376).
  - `CephBucketTopic` Kafka notifications default to `auth_mechanism=PLAIN`; setting `&mechanism=...` via `opaqueData` no longer works — must reconfigure `CephBucketTopic` resources (#15554, #15711).
- **CRD migrations:** `CephObjectStoreUser` gains first-class credential-management fields (additive but behaviorally breaking).
- **Upgrade ordering:** Rook operator before CephCluster (standard).
- **Deprecations:** none net-new at the operator level (CSI operator transition is announced in 1.18, not here).
- **Cross-component (Ceph):** **Ceph Reef v18.2.0+ and Squid v19.2.0+.** Tentacle not yet supported in this minor.
- **Notable:**
  - Ceph CSI v3.14 bundled.
  - External mons (experimental) — for two-DC clusters where an arbiter K8s node isn't available.
  - DNS resolution for mons via `rook-ceph-active-mons.<ns>.svc.cluster.local` — clients outside K8s can resolve mon endpoints dynamically (live-migration friendly).
  - Node-specific `ceph.conf` overrides via per-node ConfigMap.
