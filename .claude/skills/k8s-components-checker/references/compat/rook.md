# rook — compat (sifted from release_notes)

- **Primary source:** https://github.com/rook/rook/releases
- **Secondary sources:** https://rook.io/docs/rook/latest-release/, per-tag `Documentation/Upgrade/rook-upgrade.md` + `Documentation/Upgrade/ceph-upgrade.md`
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 1.17
- **Last sifted:** 2026-07-21

## Node drain / reboot during a k8s/RKE2 upgrade (cross-version)

Not version-specific, but the dominant Rook-Ceph hazard during a rolling k8s/RKE2
upgrade — feed it into the verdict's action-plan ordering whenever Rook-Ceph is
detected. OSD / mon / mgr daemons commonly co-locate on **control-plane *and*
worker** nodes, so **every** node drain in a rolling upgrade touches Ceph.

- **Gate each drain on cluster health:** `CephCluster status.ceph.health ==
  HEALTH_OK` before draining; after draining, wait for the node's `csi.ceph` mounts
  in `/proc/mounts` to clear before rebooting.
- **Rebooting an OSD node opens a degraded/backfill window** — the *post*-reboot
  HEALTH_OK gate must wait for recovery to complete (minutes), not merely for the
  OSD pod to return to Running.
- **Trap — do NOT gate on Rook PodDisruptionBudgets by name.** Rook creates and
  deletes PDBs **dynamically** during drains (notably per-failure-domain
  `rook-ceph-osd` PDBs), so a fixed-name check (e.g. `k8s_info … failed_when
  resources == 0`) breaks intermittently. Gate on **CephCluster health + CSI
  unmount** instead.
- **In-place RKE2 cutover (service-restart, no drain) is far gentler than a drain/reboot.** A version
  cutover that only restarts `rke2-server`/`-agent` (no cordon, no drain, no reboot) briefly bounces
  just the OSD/mon/mgr daemons **co-located on that node** — no eviction, no backfill window. Still
  confirm `HEALTH_OK` + all OSDs up/in + pgs `active+clean` before the next node, but the drain-gating
  above applies only when you actually drain/reboot (i.e. for an OS-level reason). Field-validated
  2026-05-31 (RKE2 1.33 → 1.34, service-restart cutover, no drain).
- Field-validated 2026-05-30 (community RKE2 1.32 → 1.33, OSDs on shared
  master/worker nodes).

## Operator upgrade (cross-version) — reconcile signal, timing, benign noise

Bumping the **Rook operator** (the helm release) is distinct from a k8s/node
upgrade: the operator pod rolls, then Rook reconciles the running Ceph daemons
**in place** — mons → mgr → OSDs → RGW/MDS, one failure domain at a time. **No node
drain, no reboot.** During an OSD's restart the operator creates a temporary
blocking PDB (`maxUnavailable=0`) and sets `noout` per host — **correct
orchestration, not an error** (it greps as "Failure Domain" / "Draining"). OSD
restarts cause brief PG peering/`degraded` blips that self-heal as each OSD returns
— not backfill. A single-minor operator hop reconciles in **~5 min** (field:
1.18 → 1.19, 3 mon / 2 mgr / 4 OSD / 2 RGW).

**Reconcile signal — the `rook-version` label is on the daemon DEPLOYMENTS, not the
pods.** Watch convergence with:
```bash
kubectl -n rook-ceph get deploy -l 'app in (rook-ceph-mon,rook-ceph-mgr,rook-ceph-osd,rook-ceph-rgw,rook-ceph-mds)' -L rook-version
```
Done = every daemon deployment shows the new version **and** `ceph -s` is
`HEALTH_OK` with no pending pods.

**Verify on settled state — the CephCluster CR status LAGS.** `ceph -s` (toolbox) is
ground truth and settles first; the CephCluster CR `.status.ceph.health` is
refreshed on the mgr's periodic poll and can show a stale `HEALTH_WARN` for ~30–60 s
after `ceph -s` is already OK. Poll the CR field until it agrees before declaring
done — don't correct from the unsettled snapshot.

**`kubectl diff` vs Rook's CRDs can hit `metadata.annotations: Too long`.** Rook
ships CRDs as chart templates; the rendered manifest is ~3 MB, which can exceed
kubectl's client-side last-applied-annotation limit on the big CRDs. Fallbacks: a
text diff of the prev-vs-current rendered templates (never touches the API), or
`kubectl diff --server-side`. `helm upgrade` itself is unaffected — Helm keeps
release state in a Secret, not in annotations.

**Air-gap image list = UNION of two sources.** `helm template` renders only 2 images
(the operator + ceph-csi-operator). The CSI **sidecars** (provisioner, attacher,
resizer, snapshotter, registrar, csiaddons, cephcsi) appear ONLY as
`repository:`/`tag:` pairs under `csi:` in the values — the operator injects them
into the CSI driver pods at runtime, so they never appear in the rendered template.
Mirror the union of both. (Direct-pull clusters skip this.)

**Benign post-upgrade noise — do NOT chase these.** A full event + per-pod log sweep
after a clean operator hop typically surfaces only:
- *Transient (upgrade window, self-heals):* operator `disruption: failed to get OSD
  status … exit status 1` (OSD mid-restart); ceph-csi-controller `the object has been
  modified; please apply your changes to the latest version` (operator + CSI operator
  both write the CSI driver Deployment/DaemonSet — optimistic-concurrency requeue,
  converges in seconds); rgw `handle_error … err (110) Connection timed out` (rados
  watches drop while OSDs bounce, then re-watch); OSD `Startup probe failed: ceph
  daemon health check failed`; `HEALTH_WARN: N chassis/rack/zone down` = CRUSH
  reporting the single down OSD across every bucket type; `Degraded data redundancy …
  pgs degraded` (recovers per OSD).
- *Pre-existing cosmetic (present pre-upgrade too):* mgr scipy/NumPy sub-interpreter
  `UserWarning`, `[restful WARNING] server not running: no certificate configured`,
  `unable to list storage classes: 'storageClassDeviceSets'` (orchestrator querying
  for PVC-backed OSDs on a host-based cluster); osd `bdev … ioctl(F_SET_FILE_RW_HINT)
  … failed: (22)` (benign BlueStore write-hint) + RocksDB option dumps (`Options.*`
  key names, not errors).

Field-validated 2026-05-31 (community Rook 1.18.8 → 1.19.6, operator-only, RBD + RGW,
no CephFS).

## 1.20 (latest: 1.20.2, 2026-07-07)

- **k8s floor:** **1.31 – 1.36** (stated in the 1.20.0 release notes).
- **Breaking:**
  - **The Ceph CSI operator is now REQUIRED.** CSI settings are removed from the
    `rook-ceph-operator-config` ConfigMap and from the `rook-ceph` Helm chart.
    Existing clusters keep working with the settings Rook already applied, but
    **further CSI changes must go through the Ceph-CSI `OperatorConfig` and
    `Driver` CRs** — editing the old ConfigMap keys silently does nothing.
    New installs must configure those CRs up front; Helm users get them via the
    separate `ceph-csi-drivers` chart (custom CSI *images* stay in `rook-ceph`
    chart values). This completes the deprecation started in 1.19.
  - Unused CRUSH rules are now **deleted by default** after the Ceph mgr starts.
    Set `ROOK_DELETE_UNUSED_CRUSH_RULES=false` in the operator config to keep
    hand-made rules that are not currently referenced by a pool.
- **CRD migrations:** none. New CRD `CephObjectStoreAccount` (experimental) plus
  an `accountRef` field on `CephObjectStoreUser`.
- **Upgrade ordering:** unchanged — Rook operator before CephCluster; Helm
  `rook-ceph` chart before `rook-ceph-cluster`. Follow the per-tag upgrade guide.
- **Notable:**
  - `ROOK_RECONCILE_CONCURRENT_CLUSTERS` (concurrent CephCluster reconciles) is
    now **stable**, was experimental in 1.19.
  - OSD resize now auto-expands encrypted host-based OSDs (`encryptedDevice: true`).
  - Pod containers reconciled by name rather than declaration order — defensive
    against mutating webhooks reordering them.
  - Experimental: two-node clusters with a "floating" mon that migrates when one
    node is down; SSE-S3 via Vault Agent auth.
- **Not yet field-validated** — the 1.19 entry below carries the operator's live
  upgrade notes; 1.20 is release-note-grounded only.

## 1.19 (latest: 1.19.7, 2026-06-16)

- **k8s floor:** 1.30 – 1.35
- **Breaking:**
  - K8s minimum bumped to v1.30 (was v1.29 in 1.18).
  - Minimum Ceph is now **v19.2.0** — Reef v18 is dropped. Clusters on Ceph v18 MUST upgrade Ceph to v19.2.0+ BEFORE upgrading Rook to 1.19.
  - **`CephFilesystem.activeStandby` now controls MDS pod count — and it defaults to `false` when omitted.** Rook deploys `activeCount` MDS pods when the field is false/unset, `activeCount × 2` (active + warm standby-replay) when true. In ≤1.18 a `false`/omitted value still left passive standby pods running; **1.19 scales those standby deployments to zero.** Trap: the field is a plain `bool` with `omitempty` (zero value `false`), so a CephFilesystem that never set `activeStandby` **silently loses its standby MDS on upgrade** — `activeCount: 1` goes from 1 active + 1 standby to **1 active, none**, and an MDS pod death then stalls metadata I/O for all clients until it restarts (no warm failover). No data risk (daemon redundancy only). **Fix: set `activeStandby: true` explicitly before the 1.18 → 1.19 bump** (recommended prod posture; costs one extra MDS pod per active rank). The in-tree field comment ("if false, standbys will still be available") is stale — trust the replica logic, not the doc-comment. Field-grounded vs released v1.19.6 (`pkg/operator/ceph/file/mds/mds.go`), 2026-05-31.
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

## 1.18 (latest: 1.18.11, 2026-05-27 — out of the current + prior 2 window as of 1.20; retained for in-flight 1.18 → 1.19 upgrades)

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
