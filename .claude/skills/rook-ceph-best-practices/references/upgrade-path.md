# Rook upgrade path and release-by-release breaking changes

Enumerated unfiltered from `gh release list --repo rook/rook` on 2026-09-23.
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
| v1.20.0 | 2026-06-02 | K8s 1.31–1.36. **CSI settings removed from Rook**; `ceph-csi-drivers` chart required; chart order rook-ceph → ceph-csi-drivers → rook-ceph-cluster. Unused CRUSH rules deleted after mgr start (`ROOK_DELETE_UNUSED_CRUSH_RULES`). Experimental `CephObjectStoreAccount` (only works on Ceph main images), two-node floating mon. Encrypted host OSDs auto-expand on disk resize. |
| v1.20.5 | 2026-08-19 | AES256K key type support. |
| v1.20.6 | 2026-08-20 | CVE floor for the 1.20 line. Disable-rook-mgr-module recommendation. |
| v1.20.7 | 2026-09-02 | ceph-csi 3.17.1 (AES256K). Mgr module unset properly when disabled. Toolbox restart note in the CVE guide. |

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

## Ceph image tags

`quay.io/ceph/ceph:vX.Y.Z-YYYYMMDD` is the production tag form; pin its
digest. Major tags (`:v20`) are for test clusters only.
