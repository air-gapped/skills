# Making self-managed RKE2 guests Harvester-aware & survivable

For clusters where the RKE2 **control-plane/etcd nodes run as Harvester VMs** (workers may be bare-metal off
Harvester) and are **self-managed** (not Rancher-provisioned). Ordered by impact for surviving the rolling host
upgrade.

## 1. Anti-affinity spread of the CP/etcd VMs — the #1 lever

Spread the 3 etcd VMs across **3 distinct Harvester hosts** so a one-host-at-a-time upgrade only ever touches
**one** etcd member → the other two keep quorum no matter what happens to the third.
- Rancher-provisioned guests get this automatically (topologySpreadConstraints, harvester#2316/#2323).
  **Self-managed clusters must set it by hand.**
- UI: VM → **"VM Scheduling"** tab (workload/pod anti-affinity on VM labels), *not* "Node Scheduling". On the CR
  it lands under `spec.template.spec.affinity.podAntiAffinity`. Give the CP VMs a shared label and use
  `topologyKey: kubernetes.io/hostname`.
- **Strict (required) anti-affinity trap:** if it can't be satisfied, the VM becomes **non-migratable**, and in
  pre-drain Harvester will **force-shut** it. With **3 hosts + 3 CP VMs + required anti-affinity**, the draining
  host's CP VM has nowhere to migrate → it is force-shut for that host's window (~10–15 min) — still only one
  member, so quorum holds. With **N+1 hosts (4+)** that VM **live-migrates** → **zero** etcd downtime.
  **Recommend N+1 for zero member downtime.**
- **VLAN auto-affinity trap:** attaching a VM to a VLAN-backed network auto-injects `requiredDuringScheduling`
  nodeAffinity for `network.harvesterhci.io/<clusternetwork>` (and the webhook reverts manual edits). If that
  network doesn't span all hosts, the VM becomes non-migratable. Keep CP VMs on **`mgmt`** (no affinity, all
  nodes) or ensure the VLAN network-config spans every host.

## 2. Live-migration prerequisites for the CP VMs

A VM is migratable iff another schedulable host satisfies its rules with free CPU/mem and all volumes/devices
can be rebuilt on the target. Make CP VMs migratable:
- **No PCI/SR-IOV/vGPU passthrough**; no CPU-pinning only one node satisfies.
- **Volumes on Longhorn (shared)**, not local/host-path.
- **No node-selector/affinity matching only one host** (see VLAN trap).
- Verify: `kubectl get vmi <vm> -o jsonpath='{.status.conditions}'` → `LiveMigratable: True`; or the UI **⋮ →
  Migrate** action is enabled; in-flight migrations track as `kubectl get vmim`.
- Pre-check before every hop: `bash pre-check/v1.x/check.sh` (harvester/upgrade-helpers) flags running VMs with
  CD-ROM/hostDevices (re-run until clean — it reports only the first violator, harvester#9367).

## 3. qemu-guest-agent (install in every VM)

A guest-OS daemon (not a Harvester component). Gives graceful ACPI shutdown, IP/secondary-NIC reporting, and
**filesystem freeze/thaw** so VM backups are **filesystem-consistent** (via KubeVirt `virt-freezer`). It does
**not** gate live migration (migration is a hypervisor memory copy) — install it anyway; it's harmless and
high-value for graceful shutdown of non-migratable VMs and for consistent pre-upgrade backups.
```yaml
#cloud-config
package_update: true
packages: [qemu-guest-agent]
runcmd: [[systemctl, enable, '--now', qemu-guest-agent.service]]
```
Air-gap: bake into the image or point cloud-init at an internal mirror. cloud-init runs once — to add to a
running VM: `cloud-init clean --logs --reboot`. Verify connected:
`kubectl get vmi <n> -o jsonpath='{.status.interfaces[0].infoSource}'` contains `guest-agent`.

## 4. Harvester Cloud Provider (CCM) + CSI driver — the "awareness" the operator asked about

Both install **standalone via Helm** for a hand-rolled (non-Rancher) cluster, using a cloud-config token minted
from Harvester — no Rancher required.
- **CCM** (`docs/rancher/cloud-provider.md`): gives the guest **LoadBalancer Services** (Harvester-side LB with
  DHCP/IP-Pool/Share-IP IPAM) + node lifecycle. Generate the token with `generate_addon.sh <sa> <namespace>`
  against the Harvester kubeconfig (VIP) → creates a SA + `harvesterhci.io:cloudprovider` rolebinding in the VM
  namespace and emits a cloud-config; set kubelet `--cloud-provider=external` and
  `helm install harvester-cloud-provider` (chart from `charts.harvesterhci.io`, pass `global.cattle.clusterName`).
  DHCP-mode LB needs the **`macvlan` kernel module** inside the VM (absent from *minimal* SLE cloud images —
  install `kernel-default`; harvester#6418).
- **CSI** (`docs/rancher/csi-driver.md`): gives the guest **PVCs backed by Harvester/Longhorn volumes**
  hot-plugged as real block devices (native perf). Token via `generate_addon_csi.sh <sa> <namespace> RKE2`;
  needs the snapshot controller/CRDs present (RKE2 bundles `rke2-snapshot-controller`). RWO native; RWX needs a
  storage-network NIC + NFS client in the guest.
- **Guest RKE2 must stay in the Harvester minor's Node-Driver range** (`compat/harvester.md`): 1.6 = v1.30–1.33
  (CSI 0.1.24), 1.7 = v1.31–1.34 (CSI 0.1.25), 1.8 = v1.33–1.35 (CSI 0.1.28; floors ≥1.33.11/≥1.34.7/≥1.35.4).
  **Avoid guest RKE2 ≤1.35.3 until Harvester ≥1.8 (harvester#10188).** Ground exact versions per `compat`.

## 5. Live-migrating busy etcd / control-plane VMs — the realistic picture

**Correction to a common myth: live migration is NOT reliably "sub-second, defaults are fine" for a busy etcd
VM.** That holds only for idle/low-churn VMs. A write-heavy etcd member is the *worst case* for KubeVirt
pre-copy live migration and on a real production cluster it frequently **never completes** — the documented,
reproducible failure (kubevirt#3504; harvester#4375/#5756/#8731).

**Why it stalls — the dirty-page race.** KubeVirt migration is pre-copy: RAM copies to the target while the VM
keeps running and keeps dirtying pages. If the guest dirties faster than the stream copies, the remaining set
never shrinks → never converges. etcd (constant Raft appends + fsync, large mutated page cache) dirties fast and
loses the race.

**Why Harvester defaults make it worse (verified 1.5.x/1.6.x):**
- 1.5.x/1.6.x ship **no MigrationConfiguration at all** (the chart block is commented out) → raw KubeVirt v1.4
  defaults: `allowAutoConverge: false`, `allowPostCopy: false`, `bandwidthPerMigration: 0`,
  `completionTimeoutPerGiB: 150`, `progressTimeout: 150` (confirmed vs a real support bundle, harvester#9144 —
  the docs' "800s/GiB / 64Mi" are stale).
- **`bandwidthPerMigration: 0` is a self-throttle trap, not "unlimited."** With 0, KubeVirt never calls
  libvirt's set-max-speed, so QEMU uses a *conservative internal* rate and does NOT saturate your 25 GbE
  (harvester#10482) → a busy etcd out-dirties the copy.
- **auto-converge off** → nothing throttles the guest to let pre-copy win.
- **The `mgmt` bond defaults to active-backup** → only **one** 25 GbE link is usable (not 50), and migration
  shares mgmt with etcd peer/client + storage + API traffic.
- **No circuit breaker:** on 1.5.x the upgrade/maintenance pre-drain is a bare infinite wait
  (`wait_vms_out_or_shutdown`) — a non-converging migration **hangs indefinitely** (the "never completed"
  symptom, harvester#5756/#8731). The evacuation loop still has no retry limit on 1.8 (harvester#10698,
  maintainer-confirmed 2026-06-01).

### A) Make migration converge (if you insist on live-migrating etcd)
- **auto-converge** (`allowAutoConverge: true`) — the most effective pre-copy knob; progressively throttles
  guest vCPU to drop the dirty rate. **Tradeoff for etcd:** throttling slows its fsync/apply loop → can miss
  Raft heartbeats → brief leader election on *that* member (tolerable only because quorum covers one member).
- **Set an explicit `bandwidthPerMigration`** (e.g. `4Gi`–`5Gi`) so QEMU uses the link instead of self-throttling.
- **Dedicate a migration network** — highest-leverage structural fix. Harvester's `vm-migration-network` setting
  puts migration on its own NAD/VLAN off `mgmt` (docs warn explicitly *not* to leave it on mgmt). Also check the
  bond: active-backup = 25 G; LACP (switch-side) ≈ 50 G.
- **Raise `progressTimeout`** (e.g. 300–600) so a transient stall on a contended link doesn't abort an
  otherwise-progressing migration.
- **Where to set it:** on **1.7.0+** use the supported Harvester `kubevirt-migration` Setting
  (`kubectl edit setting.harvesterhci.io kubevirt-migration`) — editing the KubeVirt CR directly is reconciled
  back. On **1.5.x/1.6.x** there is **no supported in-product knob**; use a KubeVirt **`MigrationPolicy`** CRD
  scoped to the etcd VMs (works, not reconciled away) or accept defaults and use path (B).
- **Never `allowPostCopy: true` for etcd.** Post-copy "guarantees completion" by running the VM on the target
  and faulting pages back — but a network blip mid-post-copy **crashes the VM with no recovery** (kubevirt#15924,
  open). For a Raft voter that's a data/quorum risk, not just downtime. Scope it to non-etcd VMs only, if at all.

### B) Don't live-migrate etcd — take one member down cleanly (recommended for busy prod etcd)
The protection for etcd is **Raft quorum + anti-affinity**, not live migration. A 3-member cluster tolerates one
member down, so drop **one** control-plane VM cleanly per host and let quorum cover it. **Two different
contexts, two different mechanisms** (don't conflate them):

- **Manual host maintenance** (you click *Enable Maintenance Mode* on a host): label the etcd VMs
  `harvesterhci.io/maintain-mode-strategy: Shutdown` (or `ShutdownAndRestartAfterDisable`) → Maintenance Mode
  **powers the member off** instead of live-migrating it. Confirm distinct hosts (§1), drain the *guest* node,
  do the host work, power back on, **verify quorum rejoin** (`etcdctl endpoint health` — all healthy, one
  leader) **before** the next host. (Caveat: with only 2 CP nodes Harvester refuses Maintenance Mode — get to 3.)
- **The rolling UPGRADE** ignores `maintain-mode-strategy` entirely (verified — it's a Maintenance-Mode-only
  label). During an upgrade, control comes from the **gate**, not this label: the **PDB + VMI-readinessProbe**
  native gate on 1.5/1.6, or the **`nodeUpgradeOption` pause-map** on 1.7+. See
  `controlled-flow-and-node-order.md` §4–6 — that is where the upgrade-time "one member at a time, verified
  rejoin between hosts" guarantee lives.

### Bottom line (busy prod etcd, 2×25 G)
"Just live-migrate, defaults are fine" is wrong here. Rank: (1) clean one-member-at-a-time shutdown via quorum
(path B); (2) dedicate the migration network + make the bond LACP not active-backup (helps *all* VMs); (3) if you
must migrate etcd, a `MigrationPolicy` with auto-converge + explicit bandwidth (accept brief Raft churn);
(4) scale etcd to 5 + low-write windows; (5) **never** post-copy for etcd. Migrate one member at a time
regardless (concurrent live migration is still open, harvester#10425).

## 6. Other safety levers

- **Pin VM IPs** (MAC-based DHCP reservations or static) — a CP VM that gets a new lease on reboot breaks guest
  etcd (harvester#8950); this is the most common self-managed-guest upgrade failure.
- **runStrategy `Always`** on CP VMs so a force-shut member auto-restarts after the host reboots.
- **VM Backup (to NFS/S3) of each CP VM** before the campaign (filesystem-consistent with qemu-ga) + a
  **guest-cluster etcd snapshot** taken inside the guest.
- Optional **virtual-machine-auto-balance** add-on (experimental, ≥1.7.0) to re-spread CP VMs onto 3 hosts
  after an upgrade collapses them — enable deliberately (it live-migrates VMs).
- **A PDB CAN gate the upgrade** — the host drain is eviction-based and honors PodDisruptionBudgets. A PDB
  (`minAvailable: 2`) over the etcd virt-launcher pods + a VMI readinessProbe tied to etcd health is a native
  best-effort gate on 1.5/1.6, **but only if the VMs ride the eviction path** (pod anti-affinity, *not*
  `NodeSelector` pinning — pinned VMs are force-stopped pre-eviction). Full design + must-test caveats:
  `controlled-flow-and-node-order.md` §6. (The Harvester *witness* node protects Harvester's own etcd, not the
  guest's.)
</content>
