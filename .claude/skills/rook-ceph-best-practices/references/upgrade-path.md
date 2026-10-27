# Rook upgrade path and release-by-release breaking changes

Enumerated unfiltered from `gh release list --repo rook/rook` (date in `sources.md`).
Read the notes of every crossed hop, not only the target.

## Multi-hop path to the CVE-2025-30156 fix (from rook#18203)

Starting below Rook v1.18:

1. Rook → v1.18.11+
2. Ceph → 19.2.5 (**not** 19.2.6 yet — needs Rook ≥ v1.19.10)
3. Rook → v1.19.10+ (prefer the newest v1.19.x)
4. Ceph → 19.2.6+ (or 20.2.4+ if going to Tentacle) with daemon key rotation
5. Optional: Rook → v1.20.6+ (requires v1.19.5+ and the CSI migration below)

The advisory first named v1.19.9 / v1.20.5 as minimums; a maintainer raised
them to v1.19.10 / v1.20.6. Use the higher floor.

## Release notes that change behaviour

| Release | Date | Breaking / behaviour change |
|---|---|---|
| v1.16.0 | 2024-12-17 | Quincy dropped. CSI network holder pods removed — disable them before the hop. Min K8s 1.27. |
| v1.17.0 | 2025-04-16 | Min K8s 1.28. OBC `additionalConfig` off by default (`ROOK_OBC_ALLOW_ADDITIONAL_CONFIG_FIELDS`). CephObjectStoreUser: undeclared extra S3 credentials are purged. CephBucketTopic Kafka defaults `mechanism=PLAIN`. |
| v1.18.0 | 2025-08-20 | Min K8s 1.29. Helm skew: last 6 minors (3.13+). New-cluster topology validation (duplicate `topology.rook.io/rack` across zones fails; `ROOK_SKIP_OSD_TOPOLOGY_CHECK=true`). ceph-csi-operator becomes the default CSI config path; existing settings auto-converted; rollback `csi.rookUseCsiOperator: false`. Key rotation experimental (Ceph 19.2.3+). |
| v1.19.0 | 2026-01-20 | K8s 1.30–1.35. **Min Ceph 19.2.0 — Reef dropped.** `activeStandby: false` removes the standby MDS Deployment. `rook-ceph-cluster` chart: Ceph image split into repository/tag. External mode no longer auto-creates CSI clients from an admin keyring — use the python script. Experimental NVMe-oF RBD. |
| v1.19.5 | 2026-04-28 | Required floor before v1.20 (Helm upgrade fix). Mon drains prevented more reliably when mons are down. |
| v1.19.9 | 2026-08-19 | AES256K key type support. |
| v1.19.10 | 2026-08-20 | CVE floor for the 1.19 line. `muteHealthWarning`. rook mgr module disable fix. |
| v1.19.11 | 2026-09-02 | ceph-csi 3.16.3 (AES256K). Chart values diff from v1.19.6: only `image.tag` and `csi.cephcsi.tag`. CRD delta: cephx `keyType`, `allowedCiphers`, `muteHealthWarning`. |
| v1.19.12 | 2026-10-14 | RGW waits for every OSD to reach the target Ceph version before rolling (rook#18367). |
| v1.20.0 | 2026-06-02 | K8s 1.31–1.36. **CSI settings removed from Rook**; `ceph-csi-drivers` chart required; chart order rook-ceph → ceph-csi-drivers → rook-ceph-cluster. Unused CRUSH rules deleted after mgr start (`ROOK_DELETE_UNUSED_CRUSH_RULES`). Experimental `CephObjectStoreAccount` (only works on Ceph main images), two-node floating mon. Encrypted host OSDs auto-expand on disk resize. |
| v1.20.5 | 2026-08-19 | AES256K key type support. |
| v1.20.6 | 2026-08-20 | CVE floor for the 1.20 line. Disable-rook-mgr-module recommendation. |
| v1.20.7 | 2026-09-02 | ceph-csi 3.17.1 (AES256K). Mgr module unset properly when disabled. Toolbox restart note in the CVE guide. |
| v1.20.8 | 2026-09-29 | K8s up to 1.37. Same RGW gate as v1.19.12. CephX doc quick-fix image corrected to `v20.2.4-20260818`. |
| v1.20.9 | 2026-10-14 | With `network.connections.encryption.enabled`, mon connections are also forced to `secure` (`ms_mon_*_mode`); a client forcing `crc` to a mon is refused. |
| v1.21.0 | 2026-10-06 | K8s 1.32–1.37. **msgr2 required by default** (kernel clients 5.11+, else `network.connections.requireMsgr2: false`; existing mounts stay on msgr1 until remounted). Helm OCI chart tags drop the `v` prefix (`1.21.0`). New NFS installs must create the `.nfs` CephBlockPool. Rook sets no CSI images: `rook-csi-operator-image-set-configmap` is empty, so custom CSI images must be re-added there. Toolbox reloads keyring/`ceph.conf` after rotation. Umbrella supported once 21.2.0 ships. |
| v1.21.1 | 2026-10-26 | Docs: delete the chart's `ceph-block` StorageClass before upgrading `rook-ceph-cluster` to v1.21 (new immutable CSI secret parameters; PVs unaffected). With no legacy clients, sets `auth_allow_insecure_global_id_reclaim=false` instead of muting the warning. |

## v1.19 → v1.20 checklist

1. Be on v1.19.5+ (prefer latest v1.19.x).
2. Export every CSI setting from `rook-ceph-operator-config` and the
   `rook-ceph` chart values; re-express them as ceph-csi-operator
   `OperatorConfig` / `Driver` CR values.
3. Helm: upgrade `rook-ceph`, then install/upgrade `ceph-csi-drivers`, then
   `rook-ceph-cluster`. Manifest installs: apply the operator.yaml defaults
   for the CSI CRs.
4. Verify `kubectl -n <ns> get deploy | grep ctrlplugin` shows ready
   replicas and the pinned cephcsi image tag (ceph-csi-operator#605).
5. Mount a test PVC before declaring done.

## v1.20 → v1.21 checklist

1. Every node kernel 5.11+, or set `network.connections.requireMsgr2: false`
   (chart: under `cephClusterSpec`) before the hop.
2. Kubernetes 1.32+. Point OCI chart references at the un-prefixed tag.
3. Copy custom CSI images into `rook-csi-operator-image-set-configmap`.
4. Helm: `kubectl delete storageclass ceph-block`, then upgrade
   `rook-ceph` → `ceph-csi-drivers` → `rook-ceph-cluster`.
5. `kubectl -n <ns> get operatorconfig,driver`, then mount a test PVC.

## Ceph image tags

`quay.io/ceph/ceph:vX.Y.Z-YYYYMMDD` is the production tag form; pin its
digest. Major tags (`:v20`) are for test clusters only.
