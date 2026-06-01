# Controlling the flow — node order, what the upgrade gates on, and keeping guest control planes quorate

The recurring operator worry: "we can't let the automagic upgrade pick whatever host it wants and reboot it
while our VM-hosted control planes are unstable — and how does it even know the guest control planes are
healthy before continuing?" Short answer: **it doesn't know, and on 1.5/1.6 there is no supported pause.** This
file is the full, source-verified picture and the levers you actually have.

## Contents
1. Node order is not operator-choosable (serial interlock)
2. What the host upgrade gates on between hosts — and what it ignores
3. The 3-host physics: one member down per host is unavoidable
4. Per-version control table (1.5 / 1.6 / 1.7+) — incl. the `restoreVM` truth
5. The guaranteed no-outage procedure (1.7.0+ pause-map)
6. Native best-effort gate via PDB + VMI readinessProbe (1.5/1.6)
7. VM evacuation per node (`restoreVM`, corrected)
8. Monitoring + failure handling; the 1.8 upgrade-manager is off-limits

## 1. Node order is not operator-choosable (serial interlock)
`pkg/controller/master/upgrade/`: `upgradeKubernetes()` rewrites the `fleet-local/local` Cluster with
**`ControlPlaneConcurrency=1` / `WorkerConcurrency=1`** and attaches Harvester pre/post-drain hooks; Rancher's
RKE2 planner picks which node goes next. No sort, no "witness-first," no operator-supplied sequence.
`checkEligibleToDrain` refuses to drain a node while **any other** node is in a state other than
`Succeeded`/`Images preloaded` → **two hosts can never reboot at once.** Per-node states:
`Images preloaded → Pre-draining → Pre-drained → Post-draining → Waiting Reboot → Succeeded`.

## 2. What the host upgrade gates on between hosts — and what it ignores
Verified: the per-host sequence is `pre_drain (wait_longhorn_engines → evacuate VMs) → drain → post_drain (OS
upgrade + reboot) → Succeeded`, then the interlock releases the next host. The **only** between-host gates are:
- **node Ready/Succeeded**, and
- **Longhorn volumes healthy** (`wait_longhorn_engines` waits for `robustness=healthy` before the next host —
  so it won't proceed while the VM disks' replicas are still rebuilding; this protects **data**).

It **never** checks the guest cluster. A grep of the entire upgrade flow for guest/etcd/quorum returns **zero**
hits — Harvester has no awareness of the etcd running inside your VMs. "Are the guest control planes ready?" is
a question it does not ask, on any version.

> **Consequence (the reassuring half):** etcd VM disks live on Longhorn and persist across stop/restart, and the
> next host won't start until Longhorn is healthy. So a member that goes down comes back **with its data** and
> rejoins; quorum **self-heals**. The realistic worst case is a transient guest-API blip (availability), **not
> etcd data loss** — unless you lose Longhorn replicas or force-reset etcd.

## 3. The 3-host physics: one member down per host is unavoidable
On 3 hosts with one etcd member per host, a host reboot has **nowhere to move that member** (pinned, and even
unpinned there is no free anti-affinity target). So **one member down per host is physical and unavoidable.**
That is fine for quorum (2/3 keeps serving — no outage from one member down). Therefore "no outage" reduces to
exactly one requirement: **the down-windows must never overlap** — member-N must be back to quorum *before*
host-N+1 takes member-N+1 down. "No outage" ≡ "no overlap" ≡ **you need a gate between hosts.**

## 4. Per-version control table (incl. the `restoreVM` truth)

| Version | etcd VM during its host | auto-restart after that host | **gate between hosts** |
|---|---|---|---|
| **1.5.x** | stopped (`--shutdown`) | only via the VM's run-state when the host returns (no upgrade-`restoreVM`) | **none** (no pause feature) |
| **1.6.x** | stopped (`--shutdown --upgrade`) | **`restoreVM: true`** → per-host `restore-vm` job restarts it (use `true`!) | **none** (no pause feature) |
| **1.7.x+** | stopped | `restoreVM: true` → restarted per host | **YES — `nodeUpgradeOption: manual` pause-map** |

**`restoreVM` is NOT a gate — and `false` is a footgun for etcd.** Verified: the pre-drain detector *always*
stops non-migratable VMs (`virtctl stop`); `restoreVM` only governs a post-host `restore-vm` job
(`sendRestoreVMJob` → `IsRestoreVM`). `true` = each stopped VM auto-restarts **after its own host** (what you
want). `false` = stopped VMs are **left down** → as the upgrade marches, member1 down, then member2 down → 1/3
→ the exact outage you're avoiding. The upgrade-side `restoreVM` setting **does not exist on 1.5.x** (1.6+ only).
**Set `restoreVM: true`.**

## 5. The guaranteed no-outage procedure (1.7.0+ pause-map)
This is the clean, designed-for-this control — and the reason to prioritize reaching 1.7. Set once in
`upgrade-config`: **`restoreVM: true`** and **`nodeUpgradeOption.strategy.mode: manual`** (pauses every node).
```yaml
# upgrade-config setting (v1.7.0+)
restoreVM: true
nodeUpgradeOption:
  strategy:
    mode: manual          # pauses ALL nodes; or pauseNodes: [hostB, hostC]
```
Then per host: edit the live `Upgrade` CR annotation **`harvesterhci.io/node-upgrade-pause-map`** →
`{"hostA":"unpause"}` to release exactly one host. Harvester stops member-A, upgrades+reboots host-A, restarts
member-A. **You then verify the guest etcd is back to 3/3** (`etcdctl endpoint health` — all healthy, one
leader) → only then unpause the next host. That guarantees no overlap → **zero guest-API outage, operator-gated.**
Field caveat: harvester#10099 (air-gapped pause/unpause once stuck at "Upgrading Node 0%", closed stale) — keep
job logs handy.

## 6. Native best-effort gate via PDB + VMI readinessProbe (1.5/1.6)
On 1.5/1.6 there is no pause feature, but the host drain **does** use the Kubernetes **Eviction API and honors
PodDisruptionBudgets** (verified: `upgrade_controller.go:601-608` sets drain `Enabled=true`, `Force=true` —
which only deletes *bare* pods — and does **not** set `disableEviction`; it also waits on KubeVirt evacuation
PDBs). So a PDB is a real native lever. Make it gate on etcd health:

1. **Spread with pod anti-affinity, NOT a `NodeSelector`.** The pre-drain detector force-stops any VM it deems
   non-migratable — and `GetAllNonLiveMigratableVMINames` flags **`NodeSelector` / `HostDevices` / node-affinity
   / CD-ROM** — *before* the eviction step, so a **pinned VM bypasses the PDB entirely.** Pod anti-affinity keeps
   one-per-host spread without making them non-migratable.
2. **VMI `readinessProbe` → guest etcd health,** so the virt-launcher pod is Ready only when the member serves:
   ```yaml
   # each etcd VM: spec.template.spec
   readinessProbe:
     tcpSocket: { port: 2379 }      # or exec `etcdctl endpoint health` via guest-agent for true quorum
     periodSeconds: 10
     failureThreshold: 3
   ```
3. **PDB `minAvailable: 2`** over the 3 etcd virt-launcher pods (label them `app: guest-etcd` via the VM
   template; KubeVirt propagates the label to the pod):
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata: { name: guest-etcd-quorum, namespace: <vm-ns> }
   spec: { minAvailable: 2, selector: { matchLabels: { app: guest-etcd } } }
   ```
**Effect:** the Eviction API refuses to take down the next etcd VM while only 2 members are Ready → it blocks the
next host's drain until the rebooted member has **rejoined quorum**. Native, version-independent gate.

**Caveats — VALIDATE on a scratch cluster before trusting in prod:**
- On 3 hosts an anti-affinity VM has no migration target, so its eviction ends in KubeVirt **force-shutting** it
  (the member still goes down for *its own* host — expected; the PDB's job is blocking the *next* one).
- Harvester evacuates via a `kubevirt.io/drain` taint + KubeVirt's node-drain controller, which makes its *own*
  evacuation PDBs. Whether your **custom** PDB is consulted on this exact taint-driven, no-target path is the one
  thing not provable from source — test it: run a real upgrade on a 3-host scratch cluster and confirm host-N+1
  **waits** (at "waiting for VM live-migration/shutdown") until member-N's VMI goes Ready. The gate may present
  as the upgrade "stalling" at a host (that's it *working*), not a clean pause.
- This is best-effort; §5's pause-map is the clean control. Use the PDB to de-risk the 1.5→1.6→1.7 hops, then
  switch to the pause-map from 1.7 on.
- The **VMI readinessProbe alone is pure upside** even without the PDB: `kubectl get vmi` then shows each etcd VM
  NotReady until its member is actually healthy — an accurate per-member signal to watch/alert on during any hop.

## 7. VM evacuation per node (`restoreVM`, corrected)
Before a node drains, the pre-drain detector (`vm-live-migrate-detector --shutdown [--upgrade]`):
- **Non-migratable VMs** (`NodeSelector` / PCI-USB `HostDevices` / node-affinity-no-match / CD-ROM) are
  **`virtctl stop`-ped in pre-drain** (bypassing any PDB), then handled by `restoreVM` (§4): `true` = restarted
  after the host; `false` = left stopped (footgun for etcd).
- **Migratable VMs** are left for the drain → evicted → KubeVirt live-migrates them (taint-driven). A busy etcd
  often **won't converge** and a migration with no valid target (3 hosts) is **force-shut** to unblock — see
  `guest-rke2-survivability.md` §5 for the migration-tuning vs clean-shutdown decision.
- **`maintain-mode-strategy` does NOT apply to upgrades.** That label governs only manual *Maintenance Mode*
  (Enable Maintenance Mode on a host); the upgrade path ignores it (verified — the string appears nowhere in the
  upgrade code). Don't rely on it for the rolling upgrade.

## 8. Monitoring, failure handling, and the off-limits 1.8 upgrade-manager
```bash
kubectl -n harvester-system get upgrades -l harvesterhci.io/latestUpgrade=true -o yaml   # .status.nodeStatuses{}
# between hosts, verify the GUEST cluster yourself (Harvester won't):
#   kubectl --kubeconfig <guest> get nodes        # all CP nodes Ready
#   etcdctl endpoint health / member list         # quorum intact, one leader
```
- **Do NOT restart a failed Phase-4 (node) upgrade** unless instructed by SUSE support — there is no clean
  resume of a failed in-binary upgrade. *Pausing* (not failing) is safe and resumable.
- The 1.8 stand-alone **Upgrade Manager** add-on (UpgradePlan CRD) is **experimental, not on the ISO, and does
  not support air-gapped** (harvester#10471), mutually exclusive with the built-in path, with no finer per-node
  control. Air-gapped → always use the **built-in** ISO/UI upgrade, even on 1.8.
</content>
