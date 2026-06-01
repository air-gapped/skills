---
name: harvester-upgrade
description: >-
  Plan and run a controlled, COMMUNITY-edition Harvester HCI upgrade off an EOL line up to latest stable — the
  no-skip minor ladder (1.5→1.6→1.7→1.8; embedded RKE2/KubeVirt/Longhorn/SLE-Micro ride along), gated at each
  hop on first upgrading the EXTERNAL Rancher + a matching Harvester UI-extension (1.6↔Rancher 2.12, 1.7↔2.13,
  1.8↔2.14). Covers air-gapped version detection, why node-upgrade order is NOT operator-choosable (forced
  serial; the pause knob is v1.7.0+ only) and how to protect VM-hosted control planes anyway via anti-affinity
  spread + N+1 live-migration, making self-managed RKE2 guests Harvester-aware (cloud-provider, CSI,
  qemu-guest-agent), per-hop breaking changes (wicked→NetworkManager, Intel NIC rename, DHCP IP churn), the
  enforced pre-flight health gates, and the no-downgrade backup/rollback reality. Companion to
  k8s-components-checker and rancher-upgrade.
when_to_use: >-
  Use when the user mentions a Harvester upgrade, "upgrade Harvester", Harvester 1.5/1.6/1.7/1.8, Harvester
  stuck on EOL, the Harvester↔Rancher↔RKE2 pairing, the Harvester UI extension, a controlled/staged HCI upgrade,
  live-migrating VMs during a host upgrade, keeping VM-hosted control planes quorate across a host upgrade, or
  making RKE2 guests Harvester-aware (cloud provider, CSI). Also symptom prompts: upgrade stuck / "Pre-drained",
  wicked→NetworkManager, node "Waiting Reboot". NOT for the Rancher-server upgrade (use rancher-upgrade) or the
  single-cluster component verdict (use k8s-components-checker).
---

# harvester-upgrade

Plan, sequence, and de-risk a **community-edition Harvester HCI** upgrade across a real fleet — typically off an
**EOL line** (1.5.x) up to the latest *settled* stable. The hard part is almost never the ISO/UI upgrade click.
It is the **coordination**: Harvester is one bundle whose embedded RKE2, KubeVirt, Longhorn, SLE Micro, and
Rancher pairing all move together, the upgrade controller **picks its own node order**, and the workloads that
matter most — VM-hosted Kubernetes control planes — must stay quorate while each host reboots underneath them.

**Community editions only.** SUSE sells "SUSE Virtualization" (Prime) as a paid *support subscription on the
same bits* — it is **not** a different artifact set, and **patch releases are community-downloadable** (House
Rule #1). Flag Prime-only support claims; never build a plan on them.

## Companion to k8s-components-checker and rancher-upgrade — who owns what

This skill is the Harvester-side upgrade-methodology companion in the same trio (`rancher-upgrade` SKILL.md
explicitly defers Harvester host→guest coordination here). Respect the boundary to avoid drift:

| Question | Skill |
|----------|-------|
| Harvester↔RKE2↔Rancher *pairing numbers*, Node-Driver ranges, per-minor compat | **k8s-components-checker** — `references/compat/harvester.md` is the source of truth. **Cite it; don't restate.** |
| Is a component (Cilium, Rook, …) OK on k8s 1.NN on one cluster? | **k8s-components-checker** (per-cluster verdict) |
| How to upgrade the **Rancher server** itself (the external Rancher's own 2.11→2.14 walk, KDM, CAPI/Turtles) | **rancher-upgrade** |
| How to plan/sequence/execute the **Harvester** upgrade + keep guest control planes alive | **this skill** |

## The load-bearing facts — read these before anything else

1. **No minor skipping, ever.** The only supported path is one minor at a time: `1.5.x → 1.6.x → 1.7.x →
   1.8.x` (each Harvester minor bumps embedded RKE2 exactly one k8s minor; skipping a k8s minor is unsupported
   upstream). Intermediate **patches** within a jump *may* be skipped (`1.5.2 → 1.6.1` directly) — land on each
   minor's latest patch. **Never hand-edit embedded RKE2** — it is locked to the Harvester version.
2. **External Rancher leads every hop.** When Harvester is imported into an external Rancher, each hop is a
   three-step sequence in order: **upgrade Rancher → upgrade the Harvester UI extension → upgrade Harvester.**
   The pairing is required (1.6↔Rancher 2.12, 1.7↔2.13, 1.8↔2.14); a mismatch yields "VM tab missing" /
   unmanageable cluster. The external Rancher's own multi-minor walk is its own gated project — defer to
   `rancher-upgrade`. `references/external-rancher-coupling.md`.
3. **The node-upgrade order is not operator-choosable.** Order is delegated to RKE2/Rancher and forced
   strictly serial (concurrency=1, one-host-at-a-time interlock). The only "pause between nodes" knob
   (`nodeUpgradeOption: manual`) **exists only from v1.7.0+** — unavailable for the 1.5→1.6 and 1.6→1.7 hops.
   So protect VM-hosted control planes **structurally**, not with a button. `references/controlled-flow-and-node-order.md`.
4. **Spreading the control-plane VMs is the real safety mechanism.** Anti-affinity so the etcd VMs land on
   distinct hosts → a one-host-at-a-time upgrade only ever touches **one** member, and quorum holds whether that
   member migrates or is cleanly stopped. **Do not assume a busy etcd VM will live-migrate** — write-heavy VMs
   often *never converge* in pre-copy (Harvester ships auto-converge off and a self-throttling `bandwidthPerMigration:
   0`), so for production etcd plan to take one member down **cleanly** per host and let quorum cover it, rather
   than relying on live migration. `references/guest-rke2-survivability.md`.
5. **There is no downgrade.** A bricked host = rebuild + restore. Back up **VMs to NFS/S3** (not in-cluster
   snapshots) **and** take a **guest-cluster etcd snapshot** before each hop. Volume health (single-replica /
   degraded Longhorn) is the #1 thing that blocks a node drain — heal it first.
   `references/landmines-and-rollback.md`.

## Workflow

### 1. Establish the change set (detect, don't assume)
Read the running versions on the (air-gapped) cluster, then map onto the ladder. Never assume the starting
patch. Commands + version→minor map: `references/version-ladder-and-detection.md`.

### 2. Pick the target — latest *settled* stable, not bleeding-edge
"Latest stable" usually means the newest minor **that has a patch released** and a settled Rancher pair — not a
fresh `.0`. Avoid a first-of-minor release for a controlled upgrade off EOL hardware; landing one minor lower
often also avoids the newest Rancher minor's churn. Ground the actual latest patch of each minor via `gh`
(House Rule #2) and apply look-ahead (House Rule #5). `references/version-ladder-and-detection.md`.

### 3. For each hop: external Rancher → UI-extension → pre-flight → Harvester → verify guests
Each hop is self-contained: upgrade the external Rancher + UI extension to the pair, run the **enforced
pre-flight gates**, then the Harvester upgrade, then verify the guest control planes before the next hop.
Per-hop breaking changes + ordered runbook: `references/per-hop-runbook.md`. Pre-flight gate list: § below.

### 4. Control the flow and keep guests alive
Set up the structural protection (anti-affinity spread, N+1, MAC-pinned IPs, migratable VMs) BEFORE starting;
use the v1.7.0+ pause-map only where available. `references/controlled-flow-and-node-order.md` +
`references/guest-rke2-survivability.md`.

## Pre-flight gates (run before EVERY hop)

Harvester **blocks** an upgrade that fails these. Run the official pre-check (`bash pre-check/v1.x/check.sh -v`
from `harvester/upgrade-helpers`) on a control-plane node and clear every failure. The high-value gates:

- **Free system space** ≥ 30 GiB on `/usr/local` **and** projected post-image-load usage < 85% (kubelet
  imageGC). Fix with `crictl rmi --prune`.
- **All Longhorn volumes `healthy`** — no degraded/faulted, **no single-replica volumes** (they block drain),
  no stale attachments.
- **All nodes Ready** (none cordoned); **CAPI `local` Provisioned**, machine-count == node-count, all `Running`.
- **Certs > 7 days** from expiry; **NTP in sync**; **pods Ready** (rancher-logging healthy, Fleet bundles ok).
- **Back up first** (VM Backup to NFS/S3 + guest etcd snapshot); **disable recurring Longhorn jobs**.

Full gate table with thresholds + sources: `references/landmines-and-rollback.md` § Pre-flight.

## House rules (encode into every plan)

1. **Community editions only.** Patch releases (1.6.1, 1.7.1, …) ARE community — verify against the real
   artifact (public ISO + the official 2-month patch cadence), not a "x.y.0=community / x.y.1+=Prime" myth.
   "Prime" = paid support on identical bits. `references/version-ladder-and-detection.md` § Editions.
2. **Never invent versions; ground or abstain.** The ladder/pairing *mechanics* are this skill's methodology;
   specific latest-patch numbers, GA dates, and "fixed in vX" claims are volatile — state them only if
   cluster-reported, freshly `gh`-grounded (anti-confirmation: enumerate tags, derive per-minor latest, never
   ask "does vX exist"), or marked UNVERIFIED. Run `gh` with valid auth (enumeration exhausts anonymous).
3. **Rancher leads, no minor skips** (both axes; fact 2). Cite `rancher-upgrade` for the Rancher chain — don't
   re-derive it.
4. **Structural safety over the pause button** (facts 3–4): the pause knob is v1.7.0+ and field-flaky, so design
   in anti-affinity spread + serial interlock + MAC-pinned IPs (and N+1 where possible) before the first host.
5. **Look-ahead version targeting.** Recommend the target that also covers the *next* planned hop, not the bare
   immediate minimum — and don't land on a fresh `.0`/a minor at its support ceiling. (Same rule as
   k8s-components-checker House Rule #9 / rancher-upgrade House Rule #4.)
6. **No downgrade — back up before every hop** (fact 5): VM Backup to NFS/S3 (filesystem-consistent via
   qemu-guest-agent) + a guest etcd snapshot; in-cluster VM snapshots are NOT DR.
7. **Cite the real source per claim.** Pairing/Node-Driver numbers → `compat/harvester.md`; Rancher-side →
   `rancher-upgrade`; everything else → the reference file that carries the doc/issue evidence.

## References

- `references/version-ladder-and-detection.md` — the no-skip ladder + component table, the community-vs-Prime
  edition reality (corrected), choosing the target, and air-gapped version-detection commands (Harvester /
  RKE2 / KubeVirt / Longhorn / UI-extension).
- `references/external-rancher-coupling.md` — the Rancher→UI-extension→Harvester order, the required pairing
  table, air-gapped UI-extension install (`ui-plugin-catalog` image map), mismatch failure modes, and how the
  external Rancher's own chain gates the campaign (pointer to `rancher-upgrade`).
- `references/controlled-flow-and-node-order.md` — node order isn't operator-choosable; what the upgrade gates
  on between hosts (Longhorn yes, guest-etcd no); the 3-host physics; the per-version control table (`restoreVM`
  truth, pause-map is 1.7.0+); the guaranteed no-outage pause-map procedure; the **native PDB + VMI-readinessProbe
  gate** for 1.5/1.6 (with the pinning-bypass + must-test caveats); why the 1.8 upgrade-manager is off-limits.
- `references/guest-rke2-survivability.md` — making self-managed RKE2 guests Harvester-aware and survivable:
  anti-affinity spread (the #1 lever), N+1 capacity, live-migration prerequisites, qemu-guest-agent, the
  Harvester cloud-provider (CCM) + CSI standalone install, etcd-during-migration reality, MAC-pinned IPs.
- `references/per-hop-runbook.md` — per-hop (1.5→1.6, 1.6→1.7, 1.7→1.8) breaking changes, manual pre-steps, and
  the ordered runbook (wicked→NetworkManager, Intel NIC rename, DHCP client-ID, secondary-VLAN strip, etc.).
- `references/landmines-and-rollback.md` — the enforced pre-flight gate table, the landmine quick-reference
  (with issue numbers), Longhorn-as-#1-blocker, and the no-downgrade backup/rollback reality.
- `references/sources.md` — primary sources (Harvester docs, release notes, controller source, upgrade-helpers,
  CSI/CCM) with a freshness ledger.
</content>
