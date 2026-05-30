# capi-turtles-fleet.md — provisioning v2 (CAPI→Turtles) and Fleet across 2.11→2.14

**Grounded via per-`release-v2.X`-branch `gh` inspection of `rancher/charts` + release notes:
2026-05-30.** Re-ground specific chart/app versions at use time.

## Embedded CAPI → Rancher Turtles timeline (definitive — from live chart branches)

| Rancher | embedded CAPI (`rancher-provisioning-capi` chart) | Rancher Turtles | CAPI contract |
|---------|---------------------------------------------------|-----------------|---------------|
| 2.11 | present (`…+up0.7.0`) | **absent** | embedded |
| 2.12 | present (`…+up0.8.0`) | **absent** | embedded |
| 2.13 | present (`…+up0.9.0`) | **introduced — Turtles v0.25.x** | v1.10.6 / **v1beta1** |
| 2.14 | **REMOVED** (chart 404 on `release-v2.14`, rancher/rancher#53291) | **only path — Turtles v0.26.x** | v1.12.x / **v1beta2** |

So: embedded CAPI through **2.12**; **2.13** runs both (Turtles v0.25 introduced alongside);
**2.14** removes embedded CAPI entirely and runs Turtles **v0.26** with CAPI **v1beta2**. (Turtles
v0.26.0 ≈ 2.14.0 GA; latest v0.26.2.) The `rancher-provisioning-capi` chart being **404 on the
release-v2.14 branch** is the hard confirmation embedded CAPI is gone at 2.14.

## What this means at the 2.14 upgrade — and the real-vs-non-event test

- **Auto-migration:** the 2.13→2.14 upgrade migrates provisioning to Turtles automatically. A
  **startup warning fires if Turtles was previously disabled** → re-enable it first or v2prov
  (downstream provisioning) breaks. Pre-2.13 you no longer need to manually disable
  `embedded-cluster-api` / pre-clean webhooks (the docs dropped that step).
- **Is the migration a real event or a near-non-event?** Depends entirely on whether this Rancher
  actually provisions downstream clusters:
  ```bash
  kubectl get clusters.cluster.x-k8s.io -A          # populated → REAL migration (v1beta2 conversion + rollback hazard live)
  kubectl get clusters.provisioning.cattle.io -A    # any row name ≠ "local" → a downstream cluster
  kubectl get machines.cluster.x-k8s.io -A          # populated → CAPI is actually driving machines
  ```
  Empty `clusters.cluster.x-k8s.io` = standalone mgmt cluster: the chart/CRDs exist but there's
  nothing to convert, Turtles installs but manages nothing, and the v1beta2 rollback hazard is
  effectively absent. Don't over-weight the Turtles caveat for a standalone mgmt cluster.
- **One-way rollback hazard:** v1beta2 is a one-way contract — restoring a 2.13 backup after 2.14
  fails because v1beta2 CRs block dropping the v1beta2 CRD version. RKE2 etcd snapshot is the
  reliable rollback (see `prereqs-and-ordering.md`).
- **CAPRKE2 `v1alpha1` deprecated** (cluster-api-provider-rke2#797, CLOSED — "lack of usage in last
  2 years"); removal minor not yet committed. **CAAPF (Cluster API Addon Provider Fleet) disabled by
  default at 2.14.1** (turtles#2176) — if you provisioned CAPI clusters via CAAPF, set
  `features.use-caapf.enabled: true` before upgrading; standard (non-CAAPF) Fleet is unaffected.

## Fleet per Rancher minor (grounded live from `release-v2.X` branches)

| Rancher | Fleet app version |
|---------|-------------------|
| 2.11 | **0.12.x** |
| 2.12 | **0.13.x** |
| 2.13 | **0.14.x** |
| 2.14 | **0.15.x** |

> Note: an earlier doc-only pass mis-derived this as "off by one" from a stale clone. The live
> release branches confirm the mapping above (and confirm the k8s-components-checker
> `compat/rancher.md` entries "Fleet 0.13 @ 2.12" and "0.15 @ 2.14" are CORRECT). Trust live
> `gh api repos/rancher/charts/contents/assets/fleet?ref=release-v2.X` over any cached/clone value.

- **Fleet Helm v3 → v4 at v0.15.0 / Rancher 2.14.** Because v0.15.0 also adopts Server-Side Apply,
  **drift correction can misbehave** — issue #4878, **fixed in Rancher 2.14.1**; interim workaround
  `correctDrift.force=true`. If GitOps/Fleet drift correction is in use, target **2.14.1+**, not the
  2.14.0 GA.
- HelmOps was promoted out of experimental (default-on) at Fleet 0.13.x / Rancher 2.12.
