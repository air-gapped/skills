# openebs — compat (sifted from release notes)

- **Primary source:** https://openebs.io/docs/releases
- **Secondary sources:** https://github.com/openebs/openebs/releases, https://github.com/openebs/mayastor/releases, https://github.com/openebs/lvm-localpv/releases, https://github.com/openebs/zfs-localpv/releases, https://github.com/openebs/dynamic-localpv-provisioner/releases
- **Truth source type:** `release_notes`
- **Axis type:** `single` (umbrella → k8s; per-engine sub-versioning tracked below the umbrella row)
- **min_tracked_version:** 4.2 (umbrella floor = current + prior 2 minors)
- **Last sifted:** 2026-05-28

OpenEBS ships an **umbrella chart** (`openebs/openebs`) that pins engine sub-charts. Engines also tag and release independently between umbrella drops — so the umbrella version is *not* the only number that matters. Per umbrella minor, the per-engine signal is broken out below.

In-scope community engines as of 4.x: **Replicated PV Mayastor**, **LocalPV-LVM**, **LocalPV-ZFS**, **LocalPV-Hostpath** (dynamic-localpv-provisioner), and **LocalPV-Rawfile** (added in 4.4). **cStor** (`openebs/cstor-operators`) and **Jiva** (`openebs/jiva-operator`) are out of the umbrella from 4.0 onward, last shipped v3.6.0 (Dec 2023), have had no releases since — treat as deprecated / maintenance-only; verdict as out-of-registry-scope if encountered. Charts declare **no `kubeVersion:`** — the docs' "Kubernetes 1.23+" line in every 4.x release is the only stated umbrella floor and has not moved since 4.2; treat it as nominal, not validated. Mayastor release notes carry a "Tested k8s versions" list that is **copy-pasted across releases** (still says 1.23–1.29 in 2.10.0 released Nov 2025) — do not trust as a current upper bound.

## 4.4.0 — 2025-11-21 (umbrella)

Pinned engines: **Mayastor 2.10.0**, **LocalPV-LVM 1.8.0**, **LocalPV-ZFS 2.9.0**, **LocalPV-Hostpath 4.4.0**, **LocalPV-Rawfile 0.12.0**.

- **k8s floor:** docs say 1.23+ (unchanged since 4.2; not validated against newer minors by upstream CI).
- **Breaking:** none called out at umbrella level.
- **CRD migrations:** none called out.
- **Upgrade ordering:** umbrella chart before in-place engine bumps; Mayastor data-plane requires DiskPool drain semantics — see Mayastor 2.10.0 below.
- **Deprecations:** cStor and Jiva remain out of the umbrella (since 4.0). No new deprecations this release.
- **Notable:**
  - "Upgrades to 4.4.0 supported only for: Hostpath, LVM, ZFS, Mayastor (from 3.10.x or below), Rawfile" — cStor/Jiva upgrade path via umbrella explicitly absent.
  - Known issue across umbrella: single-node setups may see ZFS/LVM controller Pod fail to schedule after upgrade (controller manifest changed to a Deployment, affinity rules absent). Workaround: delete the old controller Pod.

### Mayastor 2.10.0 (umbrella 4.4)
- **k8s floor:** stale "Tested k8s versions: 1.23.7, 1.24.14, 1.25.10, 1.29.6-1.1" — same list as 2.9.0. Untrustworthy as upper bound.
- **Breaking:** none.
- **CRD migrations:** none new; existing DiskPool / Volume / Snapshot CRDs unchanged.
- **Upgrade ordering:** check pool/volume status with `kubectl mayastor get pools` and drain replicas off the data-plane node being touched before rolling io-engine Pods.
- **Notable:** DiskPool **capacity expansion** is now supported (requires pool to have been created with sufficient metadata reservation — not retroactively expandable on old pools). Configurable ClusterSize at pool create. Pool cordon. 1GiB hugepages supported. `etcd` chart dep updated to 12.0.14. `udev` kernel monitor replaces older event source — verify host has `systemd-udevd` running. RHEL HA enablement fix.
- **Patches:** v2.9.5 (2026-03-13) and v2.10.x patches post-umbrella. Mayastor patches between umbrella drops are safe to apply standalone.

### LocalPV-LVM 1.8.0 (umbrella 4.4)
- **k8s floor:** no explicit floor in release.
- **Notable:** **Snapshot restore** lands (previously snapshot-only, no restore — was the loudest LVM-LocalPV limitation). ThinPool space reclamation on last-thin-volume delete. Scheduler considers thinpool free space in `SpaceWeighted`. Records thinpool stats in `lvmnode` CR.
- **Patches/forward:** v1.8.1 (2026-02), v1.9.0 (2026-05-21) — adds **VolumeAttributesClass support** + QoS/IOPS profile update (k8s 1.31+ VAC feature). v1.9.0 is **not pinned by umbrella 4.4** — pull standalone if VAC is needed.

### LocalPV-ZFS 2.9.0 (umbrella 4.4)
- **k8s floor:** no explicit floor in release.
- **Notable:** Go bumped to 1.24. Configurable CPU/memory requests/limits via `values.yaml` for `zfs-node` and `zfs-controller`. Removed encryption parameter handling from `buildCloneCreateArgs()` — clones now inherit from parent snapshot only (read-only ZFS property).
- **Host requirement:** ZFS kernel module + matching userspace tools on every node hosting volumes (unchanged across the 4.x line). Mismatched ZFS userspace ↔ kernel version is the classic operator footgun — pin in node image.
- **Patches/forward:** v2.9.1 (2026-02), v2.10.0 (2026-05-19) — Helm `dnsPolicy` configurable, `initContainers` as list (chart shape change — values overrides for `initContainers` must be updated), OCI chart publishing.

### LocalPV-Hostpath 4.4.0 / dynamic-localpv-provisioner (umbrella 4.4)
- **Notable:** mostly observability + chart shape; no compat-affecting change.
- **Forward:** v4.5.0 (2026-05-20) shipped post-umbrella.

### LocalPV-Rawfile 0.12.0 (NEW in umbrella 4.4)
- First appearance in umbrella. VolumeSnapshots, restore-from-snapshot, clone.
- Pre-1.0 — treat as **experimental** in production verdicts.

## 4.3.0 — 2025-06-13 (umbrella)

Pinned engines: **Mayastor 2.9.0**, **LocalPV-LVM 1.7.0**, **LocalPV-ZFS 2.8.0**, **LocalPV-Hostpath 4.3.0**.

- **k8s floor:** docs say 1.23+ (unchanged).
- **Breaking:** **Mayastor volume health semantics changed** — volumes previously reported `Online` may now report `Degraded` (especially unpublished volumes — rebuilds don't run on those). Revert with `agents.core.volumeHealth=false`. **Watch dashboards / alerts that fire on `Degraded`** before upgrading.
- **Breaking (chart shape):** umbrella chart now bundles **Loki + Minio + Alloy by default** (3 Loki replicas, 3 Minio replicas) for support-bundle collection. Adds ~1.5GiB image pull + PVC requirements on first install. Disable with `loki.enabled=false, alloy.enabled=false` or point Loki at filesystem storage instead of Minio.
- **CRD migrations:** none called out.
- **Upgrade ordering:** umbrella plugin (`kubectl openebs`) introduced as the unified upgrade orchestrator — replaces per-engine upgrade plugins. One-step umbrella upgrade.
- **Deprecations:** `Promtail` removed from Mayastor chart (was EOL upstream) — replaced by Alloy.
- **Notable:**
  - Mayastor **at-rest encryption** for DiskPools (user-supplied DEK; no key rotation supported).
  - Mayastor IPv6 support.
  - `kubectl openebs dump system` unifies support-bundle across Hostpath / LVM / ZFS / Mayastor (was Mayastor-only).
  - LocalPV-ZFS CSI spec bumped to v1.11; LocalPV-LVM CSI spec bumped to v1.9 — sidecar image bumps may need imagePullSecret review in air-gapped registries.

### Mayastor 2.9.0 (umbrella 4.3)
- **Breaking:** volume health = true status (see above). `Loki + Minio + Alloy` defaults in chart (mayastor-extensions side too).
- **CRD migrations:** none.
- **Notable:** at-rest encryption; IPv6; `formatOptions` via StorageClass; non-persistent devlinks (`/dev/sdX`) for pool creation now blocked — pools must use `/dev/disk/by-id/...` or similar stable identifiers (this catches operators who copied the old quickstart).
- **Patches:** v2.9.1 (2025-06-23), v2.9.2 (2025-08-27), v2.9.3 (2025-10-10), v2.9.4 (2026-02-24), v2.9.5 (2026-03-13). Patches in the 2.9 line are valid against umbrella 4.3 and can be cherry-picked.

### LocalPV-LVM 1.7.0 (umbrella 4.3)
- **Notable:** `formatOptions` via StorageClass (mkfs flags surfaced); cordoned nodes skipped in scheduling; CSI spec v1.9.

### LocalPV-ZFS 2.8.0 (umbrella 4.3)
- **Notable:** Backup garbage collector for stale/orphaned backups. CSI spec v1.11. SIGTERM/SIGINT handled. `quotatype` backward-compat on restore. `--plugin` flag now only accepts `controller`/`agent` (previously also `node` — **operator scripts passing `--plugin node` break**).

## 4.2.0 — 2025-02-17 (umbrella)

Pinned engines: **Mayastor 2.8.0**, **LocalPV-LVM 1.6.2**, **LocalPV-ZFS 2.7.1**, **LocalPV-Hostpath 4.2.0**. (No Loki/Minio/Alloy yet.)

- **k8s floor:** docs say 1.23+.
- **Breaking:** **Engine compatibility list narrows** — upgrades to 4.2.0 supported only for Hostpath, LVM, ZFS, Mayastor (from 3.10.x or below). **cStor and Jiva are not upgradable via umbrella from 4.2 onward**; operators on cStor/Jiva must either stay on 3.x or migrate data to a supported engine before bumping. This is the load-bearing breaking change of the 4.x line.
- **CRD migrations:** Mayastor `2.7 → 2.8` schema additions for RDMA target sharing (additive, no manual conversion).
- **Upgrade ordering:** umbrella; per-engine plugins still authoritative for upgrade at this version (unified plugin lands in 4.3).
- **Deprecations:** see above re cStor/Jiva.
- **Notable:**
  - Mayastor **NVMe-oF RDMA** target transport (Helm option + RDMA-capable NIC required). Major perf feature for users with RoCE/IB fabrics.
  - Mayastor **CSAL ftl bdev** (SPDK fast-cache).
  - Mayastor detects `nvme-tcp` builtin on Talos.
  - Single-node-setup known issue: ZFS/LVM controller (now a Deployment) may not schedule due to affinity rules — delete old controller Pod to recover.

### Mayastor 2.8.0 (umbrella 4.2)
- **Notable:** RDMA target sharing; CSAL ftl bdev integration; eviction tolerations added to DSP operator + CSI controller for faster failover.

### LocalPV-LVM 1.6.2, LocalPV-ZFS 2.7.1 (umbrella 4.2)
- Patch-level, no compat-affecting change.

## Out-of-umbrella engines (deprecated)

- **cStor** (`openebs/cstor-operators`): last release `v3.6.0` 2023-12-11. Not in 4.x umbrella. CSPC schema unchanged since then. **Verdict pattern:** if detected, mark out-of-registry-scope and recommend migration to LocalPV-LVM or Mayastor, or staying on OpenEBS 3.10.x line (also unmaintained).
- **Jiva** (`openebs/jiva-operator`): last release `v3.6.0` 2023-12-11. Same posture as cStor.

## Known compat hazards across the 4.x line

- **No `kubeVersion:` constraint in any 4.x umbrella chart.** Helm will install on any cluster the chart syntactically renders against. Operators relying on Helm to refuse install on incompatible k8s will not get that signal — verify manually against k8s minor.
- **Mayastor "Tested k8s versions" list in release notes is stale across releases** — present in 2.8/2.9/2.10 with the same 1.23–1.29 range. Do not cite as a current support window.
- **ZFS kernel module ↔ userspace pinning.** Cluster-node OS image must ship matching ZFS kernel + userspace; mismatch silently degrades or fails pool import. Not OpenEBS's fault, but a recurring upgrade footgun.
- **Mayastor hugepages.** Every io-engine node needs hugepages reserved at boot (`vm.nr_hugepages` or kernel cmdline). 1GiB pages supported from 2.10.0. Not auto-configured.
- **`/etc/hosts` / non-persistent devlinks.** Pools created on `/dev/sdX` before 4.3 will not be re-creatable from 4.3+ — keep existing pools but expect any pool re-create to require stable devlinks.
- **etcd dependency.** Mayastor control plane requires an etcd cluster (bundled by default via `bitnami/etcd` chart dep, version `12.0.14` as of umbrella 4.4). Operators substituting external etcd must validate version range.
- **Loki + Minio + Alloy in default chart (4.3+).** ~3 extra Loki + 3 Minio replicas if unblocked. Disable explicitly on small clusters.
- **VolumeAttributesClass (LVM 1.9.0).** Requires k8s 1.31+ and the `VolumeAttributesClass` feature gate. Not yet pinned by any umbrella; standalone bump only.
