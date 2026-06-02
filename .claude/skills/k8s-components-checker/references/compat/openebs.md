# openebs — compat (LocalPV-LVM only; sifted from release notes)

- **Primary source:** https://github.com/openebs/lvm-localpv/releases
- **Secondary sources:** https://openebs.io/docs/releases (umbrella context), https://github.com/openebs/openebs/releases (umbrella → LVM pin map)
- **Truth source type:** `release_notes`
- **Axis type:** `single` (LocalPV-LVM version → k8s)
- **min_tracked_version:** 1.5 (LocalPV-LVM; floor = the engine version umbrella 4.0.1 pins — the operator's migration source)
- **Last sifted:** 2026-06-02
- **Last release-verified:** 2026-06-02

**Scope: LocalPV-LVM only.** The operator runs OpenEBS *only* via the **LocalPV-LVM**
engine, so this file tracks LocalPV-LVM (`openebs/lvm-localpv`) and nothing else.
Mayastor, LocalPV-ZFS, LocalPV-Hostpath, LocalPV-Rawfile, and the deprecated
cStor/Jiva are **intentionally out of registry scope** (dropped 2026-06-02). If a
survey detects any of those engines (Mayastor `DiskPool`/`openebs.io` CRs, ZFS
`zfsvolumes`, cStor `cstorpoolclusters`, Jiva, Hostpath `localpv-provisioner`),
report it as an **untracked component → abstain**; do not verdict it from this file.

LocalPV-LVM installs **standalone** (the `lvm-localpv` Helm chart / OCI chart from
1.7.0+) *or* as a pinned sub-chart of the OpenEBS umbrella. Detect the installed
engine version from the `lvm-localpv` chart version, the
`openebs-lvm-localpv-node` DaemonSet image tag, or the `local.openebs.io` CRDs —
**not** the umbrella version. The umbrella version is context only:

| OpenEBS umbrella | pins LocalPV-LVM |
|---|---|
| 4.4.x | 1.8.0 |
| 4.3.x | 1.7.0 |
| 4.2.x / 4.1.3 | 1.6.2 |
| 4.0.x / 4.1.0 | 1.5.1 |

(Grounded from umbrella `charts/Chart.yaml` `dependencies:` at tags v4.0.1 … v4.4.0;
LVM release tags + dates from `openebs/lvm-localpv`, no-candidate enumeration.)

## 1.8.0 — 2025-11-18  (pinned by umbrella 4.4)

- **k8s floor:** chart declares **no `kubeVersion:`** — installs on any minor; the
  docs' nominal "Kubernetes 1.23+" is the only stated floor and is not CI-validated
  against newer minors. Verify the target minor manually.
- **Breaking:** none.
- **CRD migrations:** none (`lvmvolumes` / `lvmnodes` / `lvmsnapshots.local.openebs.io`
  unchanged).
- **Notable:**
  - **Snapshot *restore* lands** — before 1.8.0 LocalPV-LVM was snapshot-only with **no
    restore** (the loudest LVM limitation). Relevant when migrating off a pre-1.8 line:
    restore-from-snapshot is unavailable until the engine reaches 1.8.0.
  - ThinPool space reclamation on last-thin-volume delete; scheduler now considers
    thinpool free space (`SpaceWeighted`); records thinpool stats in the `lvmnode` CR.
- **Patches / forward (standalone — NOT yet umbrella-pinned):** **1.8.1** (2026-02-04,
  bug-fix); **1.9.0** (2026-05-21) adds **VolumeAttributesClass support** + a QoS/IOPS
  profile update — **requires k8s ≥ 1.31** and the `VolumeAttributesClass` feature gate.
  Pull 1.9.0 standalone if VAC is needed; no umbrella pins it yet.

## 1.7.0 — 2025-06-03  (pinned by umbrella 4.3)

- **k8s floor:** no `kubeVersion:` constraint (see 1.8.0).
- **Breaking:** none.
- **Notable:**
  - `formatOptions` via StorageClass — mkfs flags surfaced to the StorageClass.
  - Cordoned nodes are skipped during volume scheduling.
  - CSI sidecar / external-provisioner images bumped — in air-gapped registries,
    re-mirror the new sidecar images and review `imagePullSecrets` before the bump.

## 1.6.2 — 2024-09-19  (pinned by umbrella 4.1.3 / 4.2)

- **k8s floor:** no `kubeVersion:` constraint.
- **Breaking:** none.
- **Notable:** maintenance line over 1.6.0 (2024-07-05); no compat-affecting change
  versus 1.5.x beyond bug fixes. Safe in-place bump from 1.5.1.

## 1.5.1 — 2024-04-16  (pinned by umbrella 4.0 / 4.0.1 / 4.1.0 — operator's floor)

- **k8s floor:** no `kubeVersion:` constraint.
- **Breaking:** none.
- **CRD migrations:** none.
- **Upgrade ordering / migration (1.5.1 is the migration SOURCE):**
  - The engine version the **first** OpenEBS umbrella (v4.0.0 / v4.0.1) ships, and the
    operator's stated baseline. Snapshot support here is **snapshot-only — no restore**
    until 1.8.0.
  - Forward path (in-place, one umbrella minor at a time): umbrella 4.0/4.1 (LVM 1.5.1)
    → 4.2 (LVM 1.6.2) → 4.3 (LVM 1.7.0 — unified `kubectl openebs` upgrade plugin
    arrives; CSI sidecar bumps) → 4.4 (LVM 1.8.0 — snapshot restore). Standalone LVM
    can also be bumped directly via the `lvm-localpv` chart, independent of the umbrella.
  - **Single-node trap:** the LVM controller is a **Deployment** in the 4.x line; on
    single-node setups its Pod may fail to schedule after an upgrade (affinity rules).
    Workaround: delete the old controller Pod so it reschedules.

## LocalPV-LVM compat hazards (apply across the tracked line)

- **No `kubeVersion:` in the LVM chart.** Helm installs on any minor it renders
  against; it will not refuse an incompatible k8s. Verify the minor manually.
- **Node host prerequisite.** Every node hosting LVM volumes needs the **LVM2
  userspace** (`lvm2`) installed and a **Volume Group pre-created**; the StorageClass
  references that VG by name. The `openebs-lvm-localpv-node` DaemonSet provisions
  *within* an existing VG — it does not create the VG. Bake `lvm2` + the VG into the
  node image; a node missing either silently fails to provision LVM volumes.
- **VolumeAttributesClass (LVM 1.9.0).** Requires k8s **1.31+** and the
  `VolumeAttributesClass` feature gate. Not pinned by any umbrella — standalone bump only.
- **Single-node controller scheduling.** Controller-as-Deployment affinity can block
  the controller Pod on single-node clusters after an upgrade — delete the old Pod.
