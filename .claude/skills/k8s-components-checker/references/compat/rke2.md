# RKE2 — compat (sifted from release_notes)

- **Primary source:** https://github.com/rancher/rke2/releases
- **Secondary sources:** (none — RKE2 does not publish a separate compat-matrix page)
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 1.31
- **Last sifted:** 2026-05-28

Versions tagged `vX.Y.Z+rke2rN`. Compat verdict is k8s-minor-driven (`X.Y`).
Each `## <version>` block below covers the **latest patch of one k8s minor**
in scope (current + prior 2). Patch-level signal collapses into the minor's
block; do not enumerate every `+rke2rN` rebuild.

## 1.36 (latest patch v1.36.1+rke2r1, 2026-05-18)

- **k8s floor:** 1.36 (binds the cluster's k8s minor to 1.36).
- **Breaking:**
  - **Default ingress controller flips from `ingress-nginx` to Traefik for new clusters** (PR #10037). Existing clusters upgrading from 1.35 keep their currently-installed default — no silent flip on upgrade. New installs that need ingress-nginx as default must set it explicitly.
  - **Airgapped image tarball reshuffle:** `rke2-images-core` now bundles Traefik instead of ingress-nginx (PR #10269). The standalone `rke2-images-traefik` tarball is **removed**. Airgapped operators continuing on ingress-nginx must additionally stage the `rke2-images-ingress-nginx` tarball — a 1.35→1.36 airgap upgrade without this step leaves the ingress-nginx pods unable to pull.
- **CRD migrations:** rke2-traefik chart steps 37.4.x → 39.0.7 (Traefik v3.6.16); `rke2-traefik-crd` chart bumps in lockstep. CRDs auto-apply via helm-controller; manual `kubectl apply -f` of older Traefik CRDs is not needed and will conflict.
- **Upgrade ordering:** standard RKE2 in-place upgrade order (servers first, then agents). No ordering against other RKE2 components beyond the airgap-tarball staging above.
- **Deprecations:**
  - **`ingress-nginx` chart frozen** — no further updates, **scheduled for complete removal in v1.37 (community)**. Treat 1.36 as the last minor where ingress-nginx is still shipped for community users.
- **Notable:**
  - New cloud provider flag: `--cloud-provider-name=ovirt` (PR #10315) bundles ovirt CSI on amd64 only (skipped on arm64 per #10341).
  - Packaged: etcd v3.6.7-k3s1, containerd v2.2.3-k3s1, runc v1.4.2, CoreDNS v1.14.3, Traefik v3.6.16, helm-controller v0.17.1.
  - CNI floor: Cilium 1.19.3, Calico 3.32.0, Flannel 0.28.4, Multus 4.2.4.

## 1.35 (latest patch v1.35.5+rke2r1, 2026-05-18)

- **k8s floor:** 1.35.
- **Breaking:** none at the RKE2 layer beyond upstream k8s 1.35 API churn.
- **CRD migrations:** snapshot-controller chart steps 4.0.x → 4.2.x across 1.35 patches (CRD bump from `rke2-snapshot-controller-crd` 4.0.003 → 4.2.003). helm-controller applies in place; no manual conversion needed.
- **Upgrade ordering:** servers before agents; no cross-RKE2-component ordering.
- **Deprecations:** none new at the RKE2 layer in 1.35.
- **Notable:**
  - kine bumped to v0.14.9 (PR #9405). Kine is only on the path for non-etcd datastores (SQLite/PostgreSQL/MySQL) — etcd clusters unaffected.
  - `FlannelBackend` config reverted back in (PR #9420) after a prior removal attempt — config-file consumers that referenced it remain valid in 1.35.
  - Packaged: etcd v3.6.7-k3s1, containerd v2.1.5-k3s1 → v2.2.3-k3s1 across patches, CoreDNS v1.13.1 → v1.14.3, Traefik v3.6.4 → v3.6.16, helm-controller v0.16.17 → v0.17.1.
  - CNI floor at 1.35.0: Cilium 1.18.4, Calico 3.31.2. Latest 1.35.5 ships Cilium 1.19.3, Calico 3.32.0.

## 1.34 (latest patch v1.34.8+rke2r1, 2026-05-18)

- **k8s floor:** 1.34.
- **Breaking:**
  - **`--cloud-config` arg removed from kubelet** (PR #8927). Out-of-tree cloud providers that previously injected a `cloud-config` file via kubelet-arg drop the flag silently — re-route the config to the CCM (cloud-controller-manager) deployment instead. Affects on-prem providers with custom `cloud-config` (e.g. vSphere with non-default zones, custom Harvester wiring); managed-cloud paths unaffected.
- **CRD migrations:** none at the RKE2 layer at 1.34.0; later 1.34 patches pull the same snapshot-controller CRD bump that lands in 1.35.
- **Upgrade ordering:** servers before agents.
- **Deprecations:** none new at the RKE2 layer in 1.34 (see 1.36 for ingress-nginx).
- **Notable:**
  - Packaged at 1.34.1: etcd v3.6.4-k3s3, containerd v2.1.4-k3s2, runc v1.3.1, CoreDNS v1.12.3, helm-controller v0.16.13. By 1.34.8 these advance to etcd v3.6.7-k3s1, containerd v2.2.3-k3s1, runc v1.4.2, CoreDNS v1.14.3, Traefik v3.6.16.
  - CNI floor at 1.34.1: Cilium 1.18.1, Calico 3.30.3. Latest 1.34.8 ships Cilium 1.19.3, Calico 3.32.0 (same as 1.35/1.36).

## 1.33 (latest patch v1.33.12+rke2r1, 2026-05-18)

- **k8s floor:** 1.33.
- **Breaking:**
  - **etcd minor jump 3.5 → 3.6, *within* the 1.33 line.** The 3.6 bump does not
    land at 1.33.0 — it first ships at **v1.33.11+rke2r1** (grounded vs RKE2
    release notes: 1.33.10 packages etcd `v3.5.26-k3s1`, 1.33.11 packages
    `v3.6.7-k3s1`). 1.33.0–1.33.10 stay on etcd 3.5. A 1.32 → 1.33 upgrade that
    targets a patch ≥ .11 crosses the etcd minor; targeting ≤ .10 does not (and
    defers the jump to a later hop). This is the single highest-risk item in the
    1.32 → 1.33 window — see Upgrade ordering.
- **CRD migrations:** snapshot-controller chart steps 4.0.x → 4.2.x within the 1.33 series (CRD bump to `rke2-snapshot-controller-crd` 4.2.003 lands the `VolumeGroupSnapshot v1beta2` CRDs, PR #9905). helm-controller applies in place; consumers of the v1beta1 group-snapshot API must re-cut manifests against v1beta2. rke2-traefik chart steps from the 27.0.x series (Traefik v2) up to 39.0.7 (Traefik v3.6.16) across 1.33 patches — workloads pinned to v1 Middleware/IngressRoute CRDs need to be re-validated against Traefik v3.
- **Upgrade ordering:**
  - Servers before agents.
  - **etcd 3.5 → 3.6 hard prereq:** every etcd member MUST be on **≥ 3.5.26**
    (the zombie-member fix) before *any* member moves to 3.6, or quorum-loss is
    on the table. Convenient anchor: RKE2 1.33.10 ships exactly etcd 3.5.26, so a
    cluster on the last pre-jump patch already meets the floor. Mixed 3.5/3.6 is
    supported transiently (cluster runs at the 3.5 protocol; storage version
    auto-promotes 3.5.0 → 3.6.0 only once **all** members are 3.6) — keep the
    mixed window to hours, not days. Reboot the etcd **leader last** (rebooting it
    forces a re-election = extra churn).
  - **Rollback narrows after convergence:** while still mixed, rollback = reinstall
    the prior RKE2 (etcd 3.5.26) on a node or snapshot-restore; once **all**
    members are 3.6, binary rollback is unsafe (3.6 storage can't be read by 3.5)
    — snapshot-restore / `etcdctl downgrade` only.
- **Deprecations:** none new at the RKE2 layer in 1.33 (see 1.36 for ingress-nginx).
- **Notable:**
  - 1.33 is the last RKE2 minor that ships in lockstep across community and Prime channels before the 1.36 ingress-nginx/Traefik default flip — community users on 1.33 still get ingress-nginx as the shipped default.
  - **Benign restart-storm during a rolling master reboot (do not escalate).** When
    one master's etcd peer drops (drain/reboot) on a 3-node control plane, the
    remaining members run at bare quorum: slow raft agreement, `etcdserver: too
    many requests`, dropped-heartbeat / "overloaded network", leader election.
    This trips rke2-server's etcd health check → systemd restarts rke2-server →
    the load spike can flip a *different* master `NotReady` for ~5 min, which then
    self-heals. Benign (rke2#5614, etcd#16287/#19635) and distinct from the
    zombie-member failure (which ≥ 3.5.26 prevents). **Readiness signal:** the real
    risk is **OOM on low-RAM, swap-off masters** during the convergence load spike
    — size master RAM (or enable swap) before the upgrade and check
    `journalctl -k | grep -i oom` after. Field-validated 2026-05-30 (community
    RKE2 1.32 → 1.33).
  - **Server-version display lag** in a partially-upgraded control plane — see
    `references/cluster-survey.md` Phase 1 (trust per-node `kubectl get nodes`,
    not `kubectl version`).
  - Packaged at 1.33.12: etcd v3.6.7-k3s1, containerd v2.2.3-k3s1, runc v1.4.2, CoreDNS v1.14.3, Traefik v3.6.16, helm-controller v0.17.1. (Within the line: 1.33.0–1.33.10 ship etcd v3.5.x, the latest being v3.5.26-k3s1 at 1.33.10.)
  - CNI floor at 1.33.12: Cilium 1.19.3, Calico 3.32.0, Flannel 0.28.4, Multus 4.2.4 — converged with 1.34/1.35/1.36 latest patches.

## 1.32 (latest community patch v1.32.13+rke2r1, 2026-03-05)

- **k8s floor:** 1.32.
- **Breaking:** none at the RKE2 layer beyond upstream k8s 1.32 API churn. A `+rke2r2` rebuild (2026-05-27) ships May-cycle CVE backports but upstream labels it Prime-only; manually installable from the public tag if the operator chooses, but the registry positions community per house rule #1.
- **CRD migrations:** snapshot-controller chart steps 4.0.x → 4.2.x in the 1.32 series (CRD bump for `VolumeGroupSnapshot v1beta2`, PR #9905) — same break as 1.33. rke2-traefik chart bumps to 39.0.700 (Traefik v3.6.12) within 1.32 patches; existing 1.32.0 clusters on Traefik v2 must reconcile v2→v3 CRD/config differences on upgrade (chart-managed; not in-place CRD conversion).
- **Upgrade ordering:** servers before agents.
- **Deprecations:** none new at the RKE2 layer in 1.32.
- **Notable:**
  - runc bumped to v1.4.1 mid-series (PR #9958). Combined with the containerd v2.2.x bump, hosts with cgroup-v1 fallback hacks (RHEL/CentOS 8-style boot args) should be re-validated.
  - PSA namespace exceptions updated (PR #9931) — workloads relying on the old exception list in `kube-system`/`kube-public` may now hit PSA `restricted` warnings.
  - Packaged at 1.32.13+rke2r2: etcd v3.5.26-k3s1 (still on etcd 3.5 — the 3.6 jump first lands at 1.33.11; the 3.5.26 here already satisfies the ≥3.5.26 prereq for that jump), containerd v2.2.2-k3s1, runc v1.4.1, CoreDNS v1.14.2, Traefik v3.6.12, helm-controller v0.16.17.
  - CNI floor at 1.32.13+rke2r2: Cilium 1.19.1, Calico 3.31.4, Flannel 0.28.2, Multus 4.2.4.

## 1.31 (latest community patch v1.31.14+rke2r1, 2025-11-20; upstream k8s 1.31 EOL Oct 2025)

- **k8s floor:** 1.31.
- **Breaking:** upstream Kubernetes 1.31 reached EOL October 2025 — no further community CVE backports at the k8s layer. A `+rke2r2` rebuild (2026-03-18) exists upstream but is labeled Prime-only; manually installable if needed. Treat 1.31 as a freeze-in-place tier regardless — new deploys SHOULD target 1.32+.
- **CRD migrations:** snapshot-controller stays at the 4.0.x line (`rke2-snapshot-controller-crd` 4.0.003) — the 4.2.x / `VolumeGroupSnapshot v1beta2` jump does **not** backport to 1.31. rke2-traefik is pinned to the 27.0.x chart (Traefik v2.x) for the entire 1.31 series — the v2→v3 break lives in 1.32+.
- **Upgrade ordering:** servers before agents. Cross-minor: 1.31 → 1.32 is the first hop that crosses Traefik v2→v3, the snapshot-controller v1beta1→v1beta2 group-snapshot break (the etcd 3.5→3.6 jump comes later, within the 1.33 line at 1.33.11 — see § 1.33; 1.32 still ships etcd 3.5). Stage tests at each minor; don't skip.
- **Deprecations:** etcd v3.5 in use across the entire 1.31 series; the 3.6 transition does not happen until 1.33. Operators staying on 1.31 should expect no further etcd minor bumps on this branch.
- **Notable:**
  - Packaged at 1.31.14+rke2r2: etcd v3.5.21-k3s1, containerd v2.1.5-k3s1, runc v1.3.3, CoreDNS v1.13.1, helm-controller v0.16.16. Ingress-Nginx version field is **empty** in the published release notes (Prime-only build artifact tagged externally); cross-reference the chart version `rke2-ingress-nginx 4.13.500` rather than the packaged-components table.
  - No Traefik listed under packaged components (chart-only delivery in this minor; expected).
  - CNI floor at 1.31.14+rke2r2: Cilium 1.18.4, Calico 3.31.2, Flannel 0.27.4, Multus 4.2.4. Cilium 1.18.x is the ceiling for 1.31 — the Cilium 1.19 jump tracks with 1.33+.
