# prereqs-and-ordering.md — prerequisites, cross-cluster ordering, backup & rollback

**Grounded via `gh` + ranchermanager docs + docs.rke2.io: 2026-05-30; BRO versions + restore-quirk
issue states re-verified 2026-07-25 (#844 still OPEN, last activity 2026-06-22; #916 CLOSED with a
maintainer-confirmed remedy, not a stale-bot close).** The cert-manager windows and Helm floor were
**not** re-derived this pass — re-ground them at use time (House Rule #3). The mgmt-cluster k8s window per Rancher minor is **not** restated here
— cite `k8s-components-checker/references/compat/rancher.md`.

**Contents:** [Pre-flight: Rancher-proxied kubeconfig](#pre-flight-is-the-kubeconfig-rancher-proxied-resolve-before-any-step--field-validated-2026-05-30)
· [Upgrade path rule](#upgrade-path-rule) · [Per-step prerequisites](#per-step-prerequisites-gate-every-minor-step-on-these)
(cert-manager · Helm floor · agg layer · RKE1 sweep) · [Cross-cluster ordering](#cross-cluster-ordering-the-load-bearing-rule)
· [Backup & rollback](#backup--rollback--backup-restore-operator-bro--etcd-snapshot)

## Pre-flight: is the kubeconfig Rancher-proxied? (resolve BEFORE any step — field-validated 2026-05-30)

The single most dangerous omission. An operator's day-to-day kubeconfig often reaches the management
cluster **through Rancher's own proxy** — `server` URL like `https://<rancher-host>/k8s/clusters/local`,
auth = a short-lived **Rancher/OIDC-minted token**. Running `helm upgrade` of the `rancher` release
**restarts the very pods serving that proxy**, severing the API connection mid-apply. Worse: if the
token has expired, re-minting it can depend on the OIDC path that a Step-1 regression (#53995) may
break → lockout (break-glass = the local-admin password).

```bash
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
# server contains "/k8s/clusters/"  → Rancher-PROXIED. Do NOT upgrade through it.
```

**Mitigation — run the entire upgrade through a Rancher-INDEPENDENT kubeconfig** that talks straight
to the apiserver:
- RKE2: `/etc/rancher/rke2/rke2.yaml` off a control-plane node (RKE1/K3s have equivalents).
- Rewrite its `server:` to a control-plane **LB hostname that is a cert SAN** — a bare node mgmt IP
  usually is *not* a SAN and TLS fails. The embedded admin **client cert** has a multi-year TTL and
  does not depend on Rancher/OIDC, so it survives a broken auth path.
- Guard it: refuse any upgrade/uninstall against a context whose name or `server` contains
  `rancher` / `/k8s/clusters/`.

## Upgrade path rule

Supported path between minors: **latest COMMUNITY patch of the current minor → latest COMMUNITY patch
of the next minor, one minor at a time.** No minor skipping (2.11→2.12→2.13→2.14, never 2.11→2.14).
Intra-minor patch jumps are fine and expected (land on the community ceiling *before* stepping).

⛔ **"Latest patch" ≠ newest tag.** For every minor except the current one, the newest tag is a
**Prime-only** patch the community cannot install — grounded 2026-07-25, the community ceilings are
**2.11.3 / 2.12.3 / 2.13.3 / 2.14.3**, while the newest tags are 2.11.15 / 2.12.11 / 2.13.7 / 2.14.3.
Deriving a rung with `sort -V | tail -1` produces an uninstallable target. Derive each ceiling
edition-aware — see `lifecycle.md` § Latest patch per minor and § Grounding.

## Per-step prerequisites (gate every minor step on these)

- **cert-manager.** Needed only for Rancher-generated (self-signed) certs — the
  `ingress.tls.source=secret` path doesn't use it. **At 2.14 the Rancher chart REMOVED the
  cert-manager version-check / compat shims** (rancher/rancher#52922) — an out-of-window cert-manager
  now fails admission, so bump it into the supported window *before* the 2.14 helm upgrade. Grounded
  supported pair for the 2.14 era: **cert-manager 1.18 or 1.19** (#52922). For 2.11/2.12/2.13, derive
  the range by intersecting the Rancher minor's k8s window (`compat/rancher.md`) with cert-manager's
  own k8s windows (`k8s-components-checker/references/compat/cert-manager.md`) — cert-manager must
  cover the Rancher minor's **full** k8s window. Derived 2026-05-30 (both windows gh-grounded, not a
  vendor pin): **2.11 (k8s 1.30–1.32) → cert-manager 1.17–1.18; 2.12 (1.31–1.33) → 1.18–1.19;
  2.13 (1.32–1.34) → 1.19–1.20**. Re-confirm against the target minor's release-notes prerequisites
  at use time.
- **Helm client floor.** **≥ 3.18 from Rancher 2.12 onward** (verbatim docs; tied to k8s 1.33
  support); 2.13/2.14 inherit it. 2.11 ≈ 3.17 (3.18 recommended). `helm version --short`.
- **API aggregation layer** enabled on the mgmt cluster (rancher/rancher#50400) — RKE2/K3s enable it
  by default; only non-RKE2/K3s mgmt clusters need to verify.
- **RKE1 EOL sweep (bites going INTO 2.12).** RKE1 reached EOL 2025-07-31; Rancher **2.12.0+ ships a
  gating pre-upgrade validation that BLOCKS the helm upgrade if any RKE1 resources remain**
  (rancher/rancher#50286). Clean RKE1 leftovers (delete RKE1 `cluster.management.cattle.io` + their
  dependents) **while Rancher is still live** — don't discover this mid-upgrade. If the upgrade
  fails, it prints the blocking resource IDs; remove finalizers + delete them, then retry.

## Cross-cluster ordering (the load-bearing rule)

**Management Rancher upgrades BEFORE any downstream k8s *minor* bump** — introducing a downstream
minor requires the new Rancher's KDM (`kdm-downstream-matrix.md`). But also: **lift any *trailing*
downstream cluster into the target Rancher's KDM window before the host upgrade**, or it loses
manageability afterward. The full interleave:

1. Pre-flight + backup (below).
2. Lift trailing downstreams into the target Rancher's window (still on the old Rancher).
3. Upgrade the management Rancher (one minor step).
4. New KDM unlocks the next downstream minor → bump downstreams that need it.
5. Repeat per minor step.

## Backup & rollback — backup-restore-operator (BRO) + etcd snapshot

Two layers, both taken **before every step**:

> **BRO may not be installed** (field-validated 2026-05-30) — many community installs never deployed
> `rancher-backup` (no `rancher-backup` release, no `resources.cattle.io` CRDs, no storage location).
> **Do not block the upgrade on it.** The RKE2 etcd snapshot below is the real rollback floor; if BRO
> is absent, substitute targeted `kubectl get -o yaml` exports of the state that matters — the
> Rancher/Fleet app objects and the **OIDC/auth AuthConfig + its secrets** — and proceed.

- **BRO** (`rancher/backup-restore-operator`) backs up Rancher *application* state (CRDs, settings,
  cluster objects). Pair the BRO chart to the Rancher minor by the chart's
  `catalog.cattle.io/rancher-version` annotation — **not** the chart-version prefix. Grounded
  pairing (2026-05-30): 2.11→chart `106.x+up7.0.x`, 2.12→`107.x+up8.1.x`, 2.13→`108.x+up9.0.x`,
  2.14→`109.x+up10.0.x` (latest BRO app **v10.0.7**, 2026-06-23 — grounded 2026-07-25). Re-ground via
  `gh api 'repos/rancher/backup-restore-operator/releases?per_page=50'`. The operator auto-scales
  the Rancher deployment to 0 during a restore (no manual scale-down needed).
- **RKE2 etcd snapshot of the management cluster** is the *real* rollback floor — it recovers from a
  failed CRD migration / CAPI bump that BRO can't. Take an on-demand snapshot immediately before the
  helm upgrade:
  ```bash
  rke2 etcd-snapshot save                       # → ${data-dir}/db/snapshots, on-demand-<node>-<ts>
  # air-gap: ship to internal MinIO/S3
  rke2 etcd-snapshot save --etcd-s3 --etcd-s3-bucket=<b> --etcd-s3-access-key=<k> --etcd-s3-secret-key=<s>
  # restore: rke2 server --cluster-reset --cluster-reset-restore-path=<PATH> ; then systemctl start rke2-server
  ```
  Scheduled snapshots default on (cron `0 */12 * * *`, retention 5).

**Per-minor restore quirks (grounded):**
- **2.13.0 → 2.12.3 BRO restore never completes** (backup-restore-operator#844, OPEN) — admission
  webhook rejects restoring globalrole-owned ClusterRoles (immutable `gr-owner` label). Mitigation:
  delete the Rancher webhook configs before restore — `kubectl delete
  mutatingwebhookconfigurations rancher.cattle.io` and `... validatingwebhookconfigurations
  rancher.cattle.io` (Rancher recreates them on startup).
- **2.14 → 2.13 is a one-way boundary** because of the CAPI `v1beta1→v1beta2` bump (see
  `capi-turtles-fleet.md`): restoring a 2.13 backup after 2.14 fails because v1beta2 CRs block
  dropping the v1beta2 CRD version. The dedicated BRO issue (#916) is CLOSED — but **closed with a
  workaround, not a fix** (verified 2026-07-25 by reading the closing comment, per the
  closed-≠-fixed rule). The maintainer's verbatim resolution: *"a simple rollback may fail, so the
  best way forward is to use the `cleanup.sh` script… For the restore to work, all resources created
  by Rancher must be removed beforehand… the restore will behave like a cluster migration instead of
  an in-place rollback."* Script + procedure: ranchermanager docs § *Rollbacks → Alternative steps
  for special scenarios*
  (https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster/rollbacks).
  **Plan accordingly: a post-2.14 BRO rollback is a rebuild-and-restore, not an undo.** The RKE2 etcd
  snapshot remains the only true in-place rollback across this boundary — always snapshot before the
  2.13→2.14 step.
