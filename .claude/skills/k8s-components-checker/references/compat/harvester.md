# harvester — compat (sifted from release_notes + per-version wiki matrix)

- **Primary source:** https://github.com/harvester/harvester/wiki (per-version "Harvester vX.Y.Z Compatibility Matrix" pages — only v1.5.0 exists today; 1.6+ matrices live on the SUSE support-matrix site)
- **Secondary sources:** https://github.com/harvester/harvester/releases (the `## Components` table is the canonical bundled-stack signal per release), https://www.suse.com/suse-harvester/support-matrix/all-supported-versions/ (Rancher pairing, EOM/EOL, RKE2 Node Driver range)
- **Truth source type:** `release_notes`
- **Axis type:** `multi` — axis 1 = bundled stack (embedded RKE2, KubeVirt, Longhorn, SLE Micro all move together with the Harvester version); axis 2 = management plane (which Rancher community minor manages this Harvester + the pinned `harvester-ui-extension`)
- **min_tracked_version:** 1.5.0
- **Last sifted:** 2026-05-28

## Community editions and lifecycle (load-bearing — corrected 2026-06-02)

**Patches are community.** Harvester's published lifecycle is a **4-month minor cadence (Apr/Aug/Dec)** plus a
**~2-month patch cadence (best-effort)**, and **every release — minors AND patches (1.5.1, 1.5.2, 1.6.1, 1.7.1, …)
— is a normal community release with a publicly downloadable ISO** (`releases.rancher.com/harvester/<tag>/…`,
HTTP 200, verified). **Prime ("SUSE Virtualization") is a paid SUSE *support subscription* on the same bits** —
NOT a separate artifact set, and NOT a `x.y.0`-community / `x.y.[1..z]`-Prime split. So a community operator can
and should run the **latest patch of each minor**; the community upgrade path is `1.5.x → 1.6.1 → 1.7.1 → …`,
**not `.0`-only**.

> **Correction:** earlier versions of this file claimed `x.y.0`=community / `x.y.[1..z]`=Prime(paid) and that a
> minor's community support ended when "the first Prime patch of the next minor ships." That *mechanism* was
> wrong — verified against the public patch ISOs (HTTP 200), the official lifecycle doc (2-month patch cadence),
> and the patch release notes (no Prime-gating language). The rough staleness dates below survive; the mechanism
> does not.

**Staleness / EOL signal (verdict warns):** a minor is effectively unmaintained once it sits ~2 minors behind
latest (no further community patches). Confirm the exact window against the SUSE support-matrix site at use time;
dates below are approximate and grounded per House Rule #8.

| Harvester minor | Released | Latest community patch | Maintained? (verdict) |
|---|---|---|---|
| 1.8.0 | 2026-04-24 | 1.8.0 (no patch yet) | current — maintained |
| 1.7.0 | 2025-12-23 | 1.7.1 (2026-02-10) | maintained (latest − 1) |
| 1.6.0 | 2025-08-27 | 1.6.1 (2025-10-16) | **stale** — superseded by 1.7/1.8; verdict warns |
| 1.5.0 | 2025-04-25 | 1.5.2 (2025-09-18) | **EOL** — 2 minors behind; verdict warns hard (upgrade 1.5→1.6→1.7, no minor skip; see the `harvester-upgrade` skill) |

## Bundled-stack ↔ Rancher pairing (axis-1 × axis-2 quick lookup)

| Harvester | RKE2 (embedded) | KubeVirt | Longhorn | SLE Micro | Rancher (pair) | harvester-ui-extension |
|---|---|---|---|---|---|---|
| 1.8.0 | v1.35.2+rke2r1 | v1.7.0 | v1.11.1 | 6.2 | v2.14.x | bundled (UI 1.8.0) |
| 1.7.0 | v1.34.2+rke2r1 | v1.6.3 | v1.10.1 | 6.1 | v2.13.x | bundled (UI 1.7.0) |
| 1.6.0 | v1.33.3+rke2r1 | v1.5.2 | v1.9.1 | 5.5 | v2.12.x | bundled (UI 1.6.0) |
| 1.5.0 | v1.32.3+rke2r1 | v1.4.0 | v1.8.1 | 5.5 | v2.11.x | bundled (UI 1.5.0) |

The `harvester-ui-extension` is shipped *inside* the Harvester release for the embedded Rancher; for external Rancher deployments the operator must install the matching `harvester` UI extension version from the SUSE chart repo before importing — using a Rancher that's a minor behind/ahead of the pair above is the #1 cause of "VM tab missing" / "cluster shown but unmanageable" tickets.

## 1.8.0

- **Released:** 2026-04-24
- **Community EOL:** when `1.9.1` ships (est. early 2027)
- **k8s floor (embedded RKE2):** `v1.35.2+rke2r1`. Harvester-CSI/Cloud-Provider supports RKE2 Node Driver `v1.33 – v1.35` for guest clusters (min `≥v1.33.11+rke2r1`, `≥v1.34.7+rke2r1`, `≥v1.35.4+rke2r1`).
- **Bundled stack:** RKE2 `v1.35.2+rke2r1` · KubeVirt `v1.7.0` · Longhorn `v1.11.1` · CDI `v1.62.0` · Kube-OVN `v1.15.4` · SLE Micro `6.2` · embedded Rancher `v2.14.0`.
- **Management plane:** Rancher community **v2.14.x** only. **Upgrade Rancher to v2.14.x *before* upgrading Harvester to 1.8** (SUSE matrix; non-negotiable — Rancher 2.13 cannot drive Harvester 1.8 CRDs).
- **Breaking:**
  - RKE2 minor jump 1.34 → 1.35 (KubeVirt CRD bump v1.6 → v1.7; embedded Rancher 2.13 → 2.14).
  - SLE Micro base bump 6.1 → 6.2.
  - Longhorn v1.10 → v1.11 engine upgrade (Longhorn V2 data engine path matures; storage-network association required for RWX).
  - Upgrade logic decoupled from `harvester` binary into stand-alone `upgrade-manager` (Experimental in 1.8 — affects upgrade troubleshooting workflow).
- **CRD migrations:** `harvesterhci.io` PSA-related additions (Pod Security Admission). `kubevirt.io` CRDs bumped with v1.7. New `BlockDevice` naming convention (drops strict WWN requirement) — pre-1.8 BlockDevice resources auto-migrate but verify post-upgrade.
- **Upgrade ordering:**
  1. Rancher **must** reach v2.14.x first.
  2. Harvester 1.7.x → 1.8.0 in place.
  3. **Do not** bump guest-cluster RKE2 to `v1.35.x` (≤ `v1.35.3`) until Harvester ≥ 1.8.0 — `#10188` causes Calico/Cilium CNI Pending on provisioning. Use `≥v1.35.4+rke2r1`.
- **Deprecations:** `ui-plugin-index` setting removed; replaced by improved `ui-source`. `wicked` network manager fully retired (was migration path in 1.7).
- **Cross-component:** harvester-cloud-provider `v0.2.11`, harvester-csi-driver `v0.1.28`, Terraform provider `v1.8.0`.
- **Notable:** Pod Security Admission (PSA) enforced on system namespaces only (user namespaces remain unenforced — bring-your-own Kyverno/OPA/Kubewarden still works). In-place storage live migration (Longhorn ↔ third-party CSI) lands.

## 1.7.0

- **Released:** 2025-12-23 (community patch 1.7.1 2026-02-10)
- **Maintained:** latest − 1; 1.8 has no patch yet (only `v1.8.1-dev-*`). Latest community patch on this line: 1.7.1.
- **k8s floor (embedded RKE2):** `v1.34.2+rke2r1`. Guest-cluster RKE2 Node Driver: `v1.31`, `v1.32`, `v1.33`, `v1.34`.
- **Bundled stack:** RKE2 `v1.34.2+rke2r1` · KubeVirt `v1.6.3` · Longhorn `v1.10.1` · CDI `v1.62.0` · Kube-OVN `v1.14.10` · SL Micro `6.1` · embedded Rancher `v2.13.0`.
- **Management plane:** Rancher community **v2.13.x**.
- **Breaking:**
  - **`wicked` → NetworkManager** for management-network config. **If the mgmt interface was modified post-install**, manual prep is required pre-upgrade (`/v1.7/upgrade/v1-6-x-to-v1-7-x#migration-from-wicked-to-networkmanager`) — skip this and upgrade hangs at apply-manifest.
  - SLE Micro base bump 5.5 → 6.1.
  - Mandatory `rancher` user password configuration during install (no default password).
  - RKE2 minor jump 1.33 → 1.34; KubeVirt v1.5 → v1.6; Longhorn v1.9 → v1.10.
- **CRD migrations:** `kubevirt.io` v1.5 → v1.6 (NIC hotplug API stabilized). MIG-backed vGPU adds new `pcidevices.devices.harvesterhci.io` shape — verify pre-upgrade if running vGPU.
- **Upgrade ordering:**
  1. Rancher → v2.13.x first.
  2. Harvester 1.6.x → 1.7.0; check `/oem` YAML for hand-edited NetworkManager config (move to `/etc/NetworkManager/`, now a persistent path).
  3. Embedded RKE2 jumps to 1.34 during Harvester upgrade; **do not** pre-bump RKE2 separately.
- **Deprecations:** Harvester upgrade-repo VM deprecated (replaced in 1.8 by stand-alone upgrade-manager).
- **Cross-component:** harvester-csi-driver `v0.1.25` (snapshot support); guest-cluster RKE2 versions that ship this CSI: `v1.31.14+rke2r1`, `v1.32.10+rke2r1`, `v1.33.6+rke2r1`, `v1.34.2+rke2r1`.
- **Notable:** MIG-backed vGPU (A100/H100/H200) lands. NIC hot(un)plug, OVF/OVA import, VM Auto Balance (Descheduler) as experimental add-on. VM VLAN trunk networks.

## 1.6.0

- **Released:** 2025-08-27
- **Staleness:** superseded by 1.7/1.8; latest community patch on this line is 1.6.1 (2025-10-16). Verdict warns; upgrade to 1.7.x (see the `harvester-upgrade` skill).
- **k8s floor (embedded RKE2):** `v1.33.3+rke2r1`. Guest-cluster RKE2 Node Driver: `v1.30`, `v1.31`, `v1.32`, `v1.33`.
- **Bundled stack:** RKE2 `v1.33.3+rke2r1` · KubeVirt `v1.5.2` · Longhorn `v1.9.1` · CDI `v1.62.0` · SLE Micro `5.5` · embedded Rancher `v2.12.0`.
- **Management plane:** Rancher community **v2.12.x**.
- **Breaking:**
  - RKE2 1.32 → 1.33; KubeVirt 1.4 → 1.5; Longhorn 1.8 → 1.9.
  - Kube-OVN packaged as **add-on** (`kubeovn-operator`) — was static install previously; affects networking-upgrade pre-checks.
  - 3rd-party CSI support for guest clusters introduces new harvester-csi-driver paths (RWO).
- **CRD migrations:** `kubevirt.io` v1.4 → v1.5 (CPU/memory hotplug API stable). Longhorn V2 data engine CRDs introduced (V1 engine remains default).
- **Upgrade ordering:**
  1. Rancher → v2.12.x first.
  2. Harvester 1.5.x → 1.6.0.
  3. Upgrading from a 1.5 cluster with the old wicked network manager succeeds, but 1.7 will require the NetworkManager migration — plan for it.
- **Deprecations:** older harvester-cloud-provider paths replaced by `v0.2.10`-line.
- **Cross-component:** harvester-cloud-provider `v0.2.10`, harvester-csi-driver `v0.1.24`.
- **Notable:** CPU/memory hotplug, ISO-upload upgrade flow, live-migration network as separate interface, KubeOVN VPC/subnet GUI. Last community minor on SLE Micro 5.x (1.7+ moves to 6.x).

## 1.5.0

- **Released:** 2025-04-25 (community patches 1.5.1 2025-07-01, 1.5.2 2025-09-18 — both publicly downloadable)
- **EOL:** 2 minors behind (1.7/1.8 shipped); latest community patch on this line is 1.5.2. Verdict warns hard — the only path forward is upgrade 1.5→1.6→1.7 (no minor skip upstream). Use the `harvester-upgrade` skill for the controlled, external-Rancher-gated procedure.
- **k8s floor (embedded RKE2):** `v1.32.3+rke2r1`. Guest-cluster RKE2 Node Driver: `v1.30`, `v1.31`, `v1.32` (per wiki matrix).
- **Bundled stack:** RKE2 `v1.32.3+rke2r1` · KubeVirt `v1.4.0` (SUSE rebuild `1.4.0-150600.5.15.1`) · Longhorn `v1.8.1` · CDI `v1.61.0` (SUSE rebuild `1.61.0-150600.3.12.1`) · SLE Micro `5.5` · embedded Rancher `v2.11.0`. Kube-OVN not yet packaged as add-on (1.6.0 introduced `kubeovn-operator`).
- **Management plane:** Rancher community **v2.11.x**. Upgrade Rancher to v2.11.x **before** upgrading Harvester to 1.5.x (docs: "you must upgrade Rancher _before_ upgrading Harvester"). `harvester-ui-extension` `v1.5.0`.
- **Breaking:**
  - **RKE1 EOL.** Harvester 1.5.0 is the **last release** with any RKE1 awareness; 1.6.0 drops RKE1 entirely. RKE1 guest clusters must be replatformed to RKE2 — **no in-place path** (SUSE KB 000021513). Plan replatforming before any move to 1.6.
  - RKE2 minor jump 1.31 → 1.32; KubeVirt v1.3 → v1.4; Longhorn v1.7 → v1.8 (V2 data engine reaches feature-complete experimental for boot volumes + live migration).
  - 3rd-party CSI provisioning of VM root/data volumes lands (fully supported) — guest-cluster CSI paths reshuffle.
  - Mandatory installer hardware-requirement check (skippable only via `harvester.install.skipchecks=true` kernel param) — old-iron POCs that worked on 1.4 may refuse to install.
  - Full ARM64 GA — add-ons now packaged for arm64; first time ARM-only clusters are production-supported.
- **CRD migrations:** `kubevirt.io` v1.3 → v1.4 (CPU/memory hotplug API stabilizes in v1.5/1.6 — v1.4 is the prep step). Longhorn V2 Data Engine CRDs land as experimental — pre-1.5 V2 volumes remain non-migratable after upgrade (must recreate on new V2 StorageClass).
- **Upgrade ordering:**
  1. Rancher → **v2.11.x first**.
  2. Harvester 1.4.2 / 1.4.3 → 1.5.0 (only `v1.4.2` and `v1.4.3` have documented direct paths; earlier 1.4.x must hop through 1.4.2+).
  3. Network manager is still **`wicked`** at 1.5 — the migration to NetworkManager only happens at 1.7.0. Plan the wicked→NetworkManager migration before any 1.7 upgrade if mgmt-interface was hand-edited post-install.
  4. CVE-2025-1974 mitigation may require re-enabling RKE2 ingress-nginx webhooks post-upgrade.
- **Deprecations:** RKE1 / `rke` provider deprecated (removed in 1.6). Older `harvester-cloud-provider` paths superseded by `v0.2.9`.
- **Cross-component:** harvester-cloud-provider `v0.2.9`, harvester-csi-driver `v0.1.23`, Terraform provider `v0.6.7`, harvester-node-driver `v0.7.1`.
- **Notable:** ARM64 GA; 3rd-party CSI as fully-supported root-volume backend; persistent TPM in VMs; EFI persistent state checkbox; Longhorn V2 boot-volume + live-migration (experimental). Guest OS coverage: SLES 15 SP6, openSUSE Leap 15.6, SLE Micro 6, Ubuntu 24.04. **Per-version wiki compatibility-matrix page exists** (`/wiki/Harvester-v1.5.0-Compatibility-Matrix`) — 1.5 is the *only* version with an in-wiki matrix; 1.6+ moved to the SUSE support-matrix site.

## Ordering rule (general — applies to any Harvester ↔ RKE2 verdict)

**Never bump embedded RKE2 ahead of Harvester.** Embedded RKE2 is locked to the Harvester version; the only supported path is "upgrade Harvester, which carries RKE2 with it." Hand-editing the RKE2 version on a Harvester node will brick the cluster.

Historical reference (still cited in verdicts on legacy 1.1.x/1.2.x clusters that have survived): *"Harvester < 1.2.0 with embedded RKE2 ≥ v1.26.6+rke2r1 breaks; upgrade Harvester first."* Same shape of rule, different versions — the principle is current.

For guest clusters provisioned **through** Harvester (RKE2 Node Driver), follow the Node Driver RKE2 range listed under each Harvester minor above. Guest-cluster RKE2 minor is independent of embedded RKE2 — do not conflate.
