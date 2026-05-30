---
name: rancher-upgrade
description: >-
  Plan and sequence COMMUNITY-edition Rancher upgrades across air-gapped multi-cluster fleets — a
  management/"hosting" Rancher cluster plus the downstream RKE2/K3s clusters it provisions. Covers the community
  release model (2.11→2.14, community-vs-Prime cadence, EOL), the Kontainer Driver Metadata (KDM) downstream-
  Kubernetes support matrix that decides which downstream k8s minors each Rancher version can manage (and the
  stranding risk when a host-Rancher bump outruns its sub-clusters), cross-cluster upgrade ordering, the
  embedded-CAPI→Rancher-Turtles migration, Fleet coupling, cert-manager/Helm/backup prerequisites, backup-
  restore-operator + etcd rollback, and the air-gapped upgrade procedure (which images/charts/KDM to mirror).
  Community editions only; Prime-gated content is flagged and excluded. Companion to k8s-components-checker,
  which owns the management-cluster k8s compatibility verdict; this skill owns the upgrade methodology and
  downstream coordination.
when_to_use: >-
  Use whenever the user mentions "rancher upgrade", "upgrade Rancher", "Rancher 2.X to 2.Y", "KDM", "which k8s
  can my Rancher manage", "downstream cluster stranded", "Rancher Turtles migration", "embedded cluster-api
  removed", "Fleet Helm v4", "Rancher air-gap upgrade", or "rancher-backup / cert-manager prerequisite" — or
  plans an upgrade of a Rancher management cluster and the downstream clusters under it, even without naming KDM
  or Turtles. NOT for Harvester or the single-cluster component-compat verdict (use k8s-components-checker).
---

# rancher-upgrade

Plan, sequence, and de-risk a **community-edition Rancher** upgrade across a real fleet: a
management ("hosting") cluster and the downstream RKE2/K3s clusters it provisions. The hard part
of a Rancher upgrade is almost never the `helm upgrade` itself — it's the **cross-cluster
coordination**: a management-cluster Rancher bump silently changes which downstream Kubernetes
versions the fleet can run, and getting the order wrong strands sub-clusters or forces a rebuild.

**Community editions only.** SUSE Rancher Prime backports, Prime-only patches, and Prime support
matrices are out of scope — flag them when they appear, never build a plan on them. House Rule #1.

## Companion to k8s-components-checker — who owns what

This skill is the upgrade-methodology companion to `k8s-components-checker` (same repo), mirroring
the `argo-cd-apps ↔ compat/argo-cd.md` split. The boundary is load-bearing — respect it to avoid
drift:

| Question | Skill |
|----------|-------|
| "Is Rancher version X compatible with the **management cluster's** k8s minor?" | **k8s-components-checker** — `references/compat/rancher.md` is the single source of truth for the mgmt-cluster k8s window per Rancher minor. **Cite it; never restate those numbers here.** |
| "Is component Y (Cilium, Rook, …) OK on k8s 1.NN on one cluster?" | **k8s-components-checker** (per-cluster verdict) |
| "How do I plan/sequence a Rancher version upgrade, and what happens to my **downstream** clusters?" | **this skill** |
| "Which downstream RKE2/K3s k8s minors can Rancher 2.X manage?" (KDM) | **this skill** |
| Harvester host→guest upgrade coordination | **neither yet** — a separate `harvester-upgrade` skill (planned). Cross-reference only. |

## The mental model — two coupled axes

A Rancher fleet upgrade moves on two axes that are **decoupled but ordered**:

1. **Management-cluster axis** — the k8s minor the Rancher server itself runs on, and the Rancher
   version. (k8s window → cite `compat/rancher.md`.)
2. **Downstream axis** — which RKE2/K3s k8s minors Rancher can *provision and manage*, governed by
   **Kontainer Driver Metadata (KDM)**, NOT by the management cluster's own k8s version.

The rule that ties them: **introducing a downstream k8s *minor* requires upgrading Rancher first;
downstream *patch* upgrades do not.** So the management Rancher always moves before any downstream
minor bump — and a trailing downstream cluster can fall out of support when the host Rancher rolls
forward. This is the single most common way a fleet upgrade goes wrong. See
`references/kdm-downstream-matrix.md`.

## Workflow

### 1. Establish the change set and the fleet shape

- **Versions:** current Rancher minor+patch, target Rancher minor. Get this from the cluster
  (`helm list -A -n cattle-system | grep rancher`), not from memory.
- **Fleet shape:** does this Rancher actually provision downstream clusters?
  `kubectl get clusters.cluster.x-k8s.io -A` (populated = real fleet; empty = standalone mgmt
  cluster — the CAPI/Turtles migration is then a near-non-event). `kubectl get
  clusters.provisioning.cattle.io -A` — any row whose name ≠ `local` is a downstream cluster.
- **Air-gap?** If the registry is internal-mirror-only, the air-gap procedure (what to mirror)
  applies — `references/air-gap-procedure.md`.

### 2. Compute the upgrade path (no minor skipping)

The only supported path between minors is **latest-patch-of-current-minor → latest-patch-of-next-
minor, one minor at a time** (2.11→2.12→2.13→2.14; never 2.11→2.14). Intra-minor patch jumps are
fine. Ground the actual latest patch of each minor via `gh` (House Rule #8 below) — don't assert a
patch from memory.

### 3. For each minor step, run the pre-flight → upgrade → post-flight runbook

The per-minor breaking changes and the ordered runbook live in `references/per-minor-runbook.md`.
Prerequisites common to every step (cert-manager window, Helm floor, mandatory backup, RKE1 sweep,
API aggregation layer) and the cross-cluster ordering + rollback floor are in
`references/prereqs-and-ordering.md`.

### 4. Coordinate the downstream clusters

Before bumping the host Rancher, check every downstream cluster's k8s minor against the **target**
Rancher's KDM window (`references/kdm-downstream-matrix.md`). Lift any *trailing* downstream into
the new window **first**, or it loses manageability after the host upgrade. After the host upgrade
(which ships a new KDM branch), the newly-unlocked downstream minors become selectable — bump
downstreams then.

### 5. Produce the plan

Emit an ordered plan: per-minor-step pre-flight gates, the upgrade command (air-gap variant if
applicable), post-flight verification, and the downstream-coordination steps interleaved at the
right points. Cite the reference + grounded version for every specific claim. Recognizable shape:

```
<cluster/fleet> — Rancher <current> → <target>   (path: <minor steps, no skips>)

prerequisites  - cert-manager <window> · Helm <floor> · RKE1 sweep · BRO backup + etcd snapshot
downstream     - <cluster>: k8s <ver> — <in target's KDM window | lift to ≥X BEFORE host upgrade>
                 source: references/kdm-downstream-matrix.md
per step (×N)  1. pre-flight gates  2. upgrade mgmt Rancher  3. post-flight  4. bump downstream
blockers       - <one-way rollback / known regression / Prime-gated path>  source: references/<file>.md
```

Every cited version is cluster-reported or freshly `gh`-grounded (House Rule #3), never from memory;
target versions follow look-ahead (House Rule #4).

## House rules (encode into every plan)

1. **Community editions only.** Flag Prime-gated versions/patches/features; never plan on them.
   The reliable community-vs-Prime signal is the GitHub release-notes first line — see
   `references/lifecycle.md`.
2. **Cite, don't restate, the mgmt-cluster k8s window.** That lives in
   `k8s-components-checker/references/compat/rancher.md`. Pointing at it keeps the two skills from
   drifting.
3. **Never invent versions; ground or abstain (House Rule #8 lineage).** k8s *windows* and KDM
   *mechanics* are methodology the skill states. Specific release/patch *numbers* — "latest 2.13
   patch", "Turtles version on 2.14", "BRO chart for 2.12" — are volatile and the #1 fabrication
   risk. State a specific version only if it is cluster-reported, freshly grounded via `gh`, or
   explicitly marked `UNVERIFIED`. Grounding method (anti-confirmation): anchor on
   `gh api repos/rancher/rancher/releases/latest`, enumerate-and-derive the real latest patch,
   **never** ask "does vX.Y.Z exist?" (existence/list queries get rubber-stamped). `gh` must be run
   with **valid auth** from the operator's workstation — anonymous is 60 requests/hour and exhausts
   almost immediately on an enumeration sweep (`gh auth status` first). Repo map + protocol:
   `references/lifecycle.md` § Grounding.
4. **Look-ahead version targeting.** When recommending any target version, pick the one that covers
   the operator's *next* planned hop too, not the bare immediate minimum — a version sitting at its
   own support ceiling forces an avoidable second upgrade. (Same rule as k8s-components-checker
   House Rule #9.)
5. **Management Rancher upgrades BEFORE downstream k8s minor bumps**, always. And **no minor
   skipping** on the Rancher axis. Violating either is the classic fleet-stranding / rebuild path.
6. **Back up before every step.** A backup-restore-operator backup *and* an RKE2 etcd snapshot of
   the management cluster — rollback across the 2.14 CAPI-v1beta2 boundary is one-way without them.
   See `references/prereqs-and-ordering.md` § Backup & rollback.

## Decision guide

| Task | Read |
|------|------|
| Community vs Prime, cadence, EOL, latest-patch grounding, `gh` repo map | `references/lifecycle.md` |
| Which downstream k8s a Rancher minor can manage; stranding; air-gap KDM mirror | `references/kdm-downstream-matrix.md` |
| cert-manager / Helm / backup prereqs, cross-cluster ordering, etcd rollback | `references/prereqs-and-ordering.md` |
| embedded-CAPI→Turtles migration, CAPRKE2/CAAPF, Fleet per-minor + Helm v4 | `references/capi-turtles-fleet.md` |
| Air-gapped upgrade: what to mirror, `helm upgrade` flags, downstream RKE2 SUC | `references/air-gap-procedure.md` |
| Per-minor (2.11→2.14) breaking changes + ordered pre/upgrade/post runbook | `references/per-minor-runbook.md` |

All version specifics in the references were grounded via `gh` on the date stamped in each file.
Re-ground at use time per House Rule #8 — releases move.
