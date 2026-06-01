# Per-hop runbook — breaking changes & manual steps

Each hop: **external Rancher → UI-extension → pre-flight → Harvester → verify guests**
(`external-rancher-coupling.md` + `landmines-and-rollback.md` § Pre-flight). Below is what is *specific* to each
minor jump. Ground exact patch numbers / fix versions via `gh` at run time (House Rule #2).

## Hop 1.5.x → 1.6.x

- **Rancher first → 2.12, UI-ext → 1.6.x.** No OS base bump (SLE Micro stays 5.5).
- **Mass live-migration storm:** KubeVirt 1.4→1.5 with the `LiveMigrate` workloadUpdateMethod migrates **all**
  running VMs at once. Set `workloadUpdateMethods: []` before, restore after (auto-handled only from 1.8.0).
  (v1-5-x-to-v1-6-x.md; harvester#10349)
- **Secondary VLAN interfaces stripped from `mgmt-br`/`mgmt-bo`** — 1.6.0 attaches only required VLANs;
  workloads (and CP VMs!) on a secondary VLAN on the mgmt network lose connectivity. Re-add each VLAN in
  `/oem/90_custom.yaml` and reboot. (harvester#7650)
- **Guest RKE2 stuck "Updating" / etcd broken if a CP VM's IP changes** on reboot (new DHCP lease) — the
  marquee self-managed-guest risk. Prevent with MAC-based DHCP reservations; fix by deleting the bad node +
  restarting the VM. (harvester#8950)
- **Longhorn volume Detaching/Detached flap after live-migration → VM stuck "Starting":** clear
  `status.currentMigrationNodeID` on the volume. (harvester#8949 / longhorn#11479)
- **`90_custom.yaml` sed-truncation → node stuck "Waiting Reboot"** (only if originally installed ≤1.2.1).
  (harvester#9033)
- **No pause control on this hop** — rely on the serial interlock + anti-affinity spread + N+1
  (`controlled-flow-and-node-order.md`).

## Hop 1.6.x → 1.7.x

- **Rancher first → 2.13, UI-ext → 1.7.x.** **OS base bump SLE Micro 5.5 → 6.1.**
- **wicked → NetworkManager migration (the big one).** No 1:1 mapping; NM profiles are regenerated from
  `/oem/harvester.config`. **If you ever hand-edited the mgmt interface (`90_custom.yaml`/ifcfg) or installed
  ≤1.1**, that config is **silently ignored** post-upgrade → broken mgmt networking. Pre-upgrade: edit
  `/oem/harvester.config` to the current schema; if origin ≤1.1, rename `/oem/99_custom.yaml` →
  `/oem/90_custom.yaml`. The pre-check detects both. Recovery: console `nmcli`, or
  `harvester-installer generate-network-config`. (v1-6-x-to-v1-7-x.md)
- **Host IP change from DHCP client-ID difference** (wicked vs NM): nodes stuck "Waiting Reboot". Manual only
  for **1.7.0**; **auto-handled for later 1.7 patches** — a reason to target the latest 1.7 patch. Mitigate with
  MAC reservations. (harvester#9260, #3418)
- **Intel NIC rename** (`i40e`/`ice` driver bump, e.g. `enp6s0f0`→`enp6s0f0np0`) → connectivity lost. Pin names
  via grub `third_party_kernel_args="… ifname=NAME:MAC …"`. Required for 1.7.0 (any NIC) and the first 1.7
  patch (bonded only); automated in a later 1.7 patch — ground the exact fix version. (harvester#9815, #9802)
- **Stuck "Upgrading System Service" (Fleet pending-upgrade):** `helm rollback fleet -n cattle-fleet-system`,
  let Rancher reconcile. Never upgrade from an RC. (harvester#9738, #9680)
- **kube-ovn** addon (if enabled) didn't support upgrades in 1.6 — verify/replan. (harvester#9845, #9533)
- Same live-migration-storm workaround as the prior hop.
- **Still no pause control** (must already be on 1.7+ to use it) — structural protection only.

## Hop 1.7.x → 1.8.0 (optional; defer until a 1.8 patch ships / a real need)

- **Rancher first → 2.14.1+** (not 2.14.0 — Google OAuth broken), **UI-ext → 1.8.x**; the external Rancher
  inherits 2.14's CAPI-v1beta2 one-way boundary + Turtles + Fleet Helm-v4 (defer to `rancher-upgrade`). **OS
  base bump 6.1 → 6.2.**
- **Pause control finally available** (`nodeUpgradeOption`, `controlled-flow-and-node-order.md`) — pause-all →
  unpause-one → verify guest etcd → next. (Mind harvester#10099.)
- **"KubeVirt is not ready" / virt-handler missing annotations** blocks all VM migration → delete the
  un-annotated virt-handler pod. (v1-7-x-to-v1-8-x.md; harvester#10447, OPEN)
- **Stuck Post-draining when Longhorn storage-network-for-RWX is enabled** (`nfs://None/...`). Multi-step patch
  to restore the setting + restart share-manager. (harvester#10532, OPEN)
- **CP node fails to rejoin, upgrade wedged at "Images preloaded"** (kubelet bearer-token / SA-UID mismatch;
  longhorn driver not found) — open, no clean fix; worst case for a self-managed-CP host. (harvester#10513, OPEN)
- **Guest RKE2 1.35 stuck (Calico grabs the VIP)** — fixed in **RKE2 1.35.4 / Rancher 2.14.1**; or set Calico
  `nodeAddressAutodetectionV4: skipInterface: vip.*`. (harvester#10188, fixed)
- **Legacy BIOS boot removed** — confirm nodes boot **UEFI** before 1.8 (future upgrades may need UEFI
  reinstall). Built-in air-gap path only (the upgrade-manager has no air-gap).

## Mechanism note (how the upgrade runs, per version)

- **1.5.x:** in-binary upgrade via a VM-based upgrade-repo.
- **1.6.0:** adds "Upgrade via ISO Upload"; still in-binary.
- **1.7.0+:** Deployment-based upgrade repo (more reliable) **and** the `nodeUpgradeOption` pause feature.
- **1.8.0:** built-in path unchanged; a separate experimental upgrade-manager exists but is **air-gap-unsupported
  and off-limits** (`controlled-flow-and-node-order.md`).

Air-gapped upgrade is the **built-in** path on every minor: stage the ISO/images on an internal HTTP server and
register a `version.yaml` (UI: Advanced → Settings → server-version → Upgrade), then drive it per
`controlled-flow-and-node-order.md`.
</content>
