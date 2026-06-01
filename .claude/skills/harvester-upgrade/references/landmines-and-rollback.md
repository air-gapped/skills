# Pre-flight gates, landmines, and the no-downgrade rollback reality

## Pre-flight gates (enforced — run before EVERY hop)

Harvester **blocks** an upgrade that fails these. The union of controller-enforced gates + the official
pre-check script `bash pre-check/v1.x/check.sh -v -l log.txt` (harvester/upgrade-helpers, version-aware — run
it on a control-plane node and clear every failure).

| Gate | Condition | Source |
|---|---|---|
| **Free system space** | ≥ **30 GiB** on `/usr/local` **AND** projected post-image-load usage < **85%** (kubelet imageGC). Fix: `crictl rmi --prune`. Override (avoid): `harvesterhci.io/skipGarbageCollectionThresholdCheck`. | controller; check.sh |
| **Cert expiry** | No node cert expiring within **7 days**. Override: `harvesterhci.io/minCertsExpirationInDay`. | controller |
| **Nodes Ready** | All `Ready`, none cordoned/unschedulable. | check.sh |
| **Witness (if any)** | ≤1 witness; must carry `node-role.kubernetes.io/etcd=true:NoExecute`. | check.sh |
| **CAPI healthy** | `clusters.cluster.x-k8s.io/local` = `Provisioned`; machine-count == node-count; all machines `Running`. | check.sh |
| **Longhorn volumes** | No degraded/faulted; attached → `robustness=healthy`; detached multi-replica → live replicas == `numberOfReplicas`; **single-replica volumes flagged** (block drain). | check.sh |
| **No stale volumes** | No volume attached without a running workload. | check.sh |
| **Pods Ready** | No pod `Ready=False` (except `PodCompleted`); rancher-logging healthy (#9644); Fleet bundles `desiredReady`. | check.sh |
| **Backing images** | ≥1 copy (fail if 0; warn if <3) — VMs won't boot post-upgrade otherwise. | check.sh |
| **VM migratability** | Running VMs with CD-ROM/hostDevices fail unless `restoreVM=true`. | check.sh |
| **Housekeeping** | Disable recurring Longhorn snapshot/backup jobs; NTP in sync; only one upgrade at a time. | automatic.md |

## Longhorn — why volume health is the #1 blocker

A node upgrade = cordon + drain, and a drain cannot complete while a Longhorn volume is unhealthy or its
replicas aren't satisfied (the instance-manager PDB blocks eviction: *"removing node PDB is blocked: some
volumes are still attached"*). **Single-replica volumes** are the classic trap — a running single-replica
volume has nowhere to fail over and blocks the drain outright; a detached one risks data loss. Fix-first order:
raise single-replica volumes to ≥2–3 replicas, wait for all `robustness=healthy`, clear stale attachments,
ensure backing images have ≥3 copies, disable Longhorn recurring jobs. A classic stuck point is **"Pre-drained"**
from orphan Longhorn instance-manager engines / a dangling PDB — verify volumes healthy, then delete the
instance-manager PDB (harvester#7366, #8977, longhorn#11605).

## Landmine quick-reference

| Hop | Landmine | Effect | Mitigation | Issue |
|---|---|---|---|---|
| 1.5→1.6 | LiveMigrate storm | all VMs migrate at once | `workloadUpdateMethods: []` before/after | #10349 |
| 1.5→1.6 | Secondary VLAN stripped from mgmt | CP VM net loss | re-add VLAN in `90_custom.yaml`+reboot | #7650 |
| 1.5→1.6 | Guest CP VM IP change | guest etcd broken | MAC DHCP reservations | #8950 |
| 1.5→1.6 | Volume flap post-migration | VM stuck Starting | clear `currentMigrationNodeID` | #8949 |
| 1.6→1.7 | wicked→NM | custom net ignored | edit `harvester.config` pre-upgrade | docs |
| 1.6→1.7 | DHCP client-ID | host IP change, stuck | target latest 1.7 patch / MAC resv | #9260 |
| 1.6→1.7 | Intel NIC rename | host net loss | pin `ifname=NAME:MAC` in grub | #9815 |
| 1.6→1.7 | Fleet pending-upgrade | stuck system service | `helm rollback fleet` | #9738 |
| 1.7→1.8 | virt-handler annotations | no VM migration | delete un-annotated pod | #10447 |
| 1.7→1.8 | RWX storage-net race | stuck Post-draining | re-patch setting + share-mgr | #10532 |
| 1.7→1.8 | CP node won't rejoin | upgrade wedged | no clean fix (open) | #10513 |
| 1.7→1.8 | guest RKE2 1.35 CNI | guest provisioning stuck | RKE2 ≥1.35.4 / Rancher 2.14.1 | #10188 |
| any | single-replica/degraded volume | drain blocked | raise replicas, heal first | check.sh |
| any | orphan Longhorn IM PDB | stuck "Pre-drained" | delete the IM PDB | #7366 |
| any (air-gap, 1.7+) | manual pause/unpause stuck | upgrade halts at 0% | have job logs; lean on structural safety | #10099 |

Issue numbers are point-in-time — re-check status via `gh` before trusting a "fixed in vX" claim (House Rule #2).

## Sequencing risk from an EOL line

- **No specific 1.5 patch floor** — any 1.5.x goes to 1.6.x; v1.5.2 only needed if hit by a listed 1.5.2 bug.
- **RKE1 leftovers strand you** — RKE1 support is removed in 1.6.0 (and gates Rancher 2.12). Inventory and
  retire any RKE1 guest clusters before leaving 1.5 (no in-place RKE1→RKE2 path; replatform).
- **Config-schema traps when leaving an old line:** old `/oem/harvester.config` v1.0 schema and the
  `99_custom.yaml` filename must be migrated before 1.7 (pre-check flags both); confirm **UEFI** boot before 1.8.

## Rollback reality — there is NO downgrade

- **Confirmed:** *"Harvester does not support downgrades"* (`automatic.md`). No host rollback; no resume of a
  failed Phase-4 node upgrade.
- **Backup primitives:**
  - **VM Backup → external Backup Target (NFS/S3)** — the only DR-grade primitive; survives a cluster rebuild
    and can restore into a **new** cluster (set the same backup target; images auto-sync on 1.4.0+).
  - **VM Snapshot → in-cluster (Longhorn)** — fast PITR but does **NOT** survive cluster loss; not DR.
  - Third-party CSI / external storage — their own snapshot/backup.
- **Brick-recovery story:** if a host upgrade fails irrecoverably, the supported answer is rebuild + restore VM
  Backups from NFS/S3 (there is no surfaced host etcd-restore button). **Before starting, back up:** every VM
  via **VM Backup to NFS/S3** (especially the self-managed CP VMs), the cluster config (`/oem/harvester.config`,
  `/oem/90_custom.yaml`, grubenv, NAD/VLAN/network defs, settings CRs), **and a guest-cluster etcd snapshot
  taken inside the guest** (a Harvester rebuild loses the guest VMs).
- **If Phase 4 fails: stop, collect logs, do NOT restart** without SUSE guidance.
</content>
