# kyverno — compat (sifted from published_matrix + release_notes)

- **Primary source:** https://kyverno.io/docs/installation/releases/
- **Secondary sources:** https://github.com/kyverno/kyverno/releases, `charts/kyverno/Chart.yaml` (per release tag), https://kyverno.io/docs/installation/upgrading/
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 1.16
- **Last sifted:** 2026-05-28

Docs publish only the **current minor's** support window — historical floors recovered from git history of the install page (pre-Astro path `content/en/docs/installation/_index.md`, commit `bcd1f63`). The chart's `kubeVersion: ">=1.25.0-0"` is permissive and **not authoritative**; the docs matrix below is the contract. Helm `kyverno-policies` chart (Pod Security Standards) is versioned separately and not on the matrix — pin to the same minor as the main chart.

Community patch window is ~3 months per minor. When `x.(y+1)` ships, `x.y` is EOL. As of 2026-05-28: **1.18 supported**, 1.17 / 1.16 are EOL upstream.

## 1.18.0 (2026-04-29)

- **k8s floor:** 1.33 – 1.35
- **Breaking:** none flagged. Metric `kyverno_policy_results` had an accidental breaking change in main during the cycle that was reverted before GA (#14471) — no operator action.
- **CRD migrations:** ship in `install.yaml` as separate files under `policies.kyverno.io/` (deletingpolicies, generatingpolicies, imagevalidatingpolicies, mutatingpolicies, validatingpolicies + all five `namespaced*` variants) and `kyverno.io/` (cleanuppolicies, clustercleanuppolicies, clusterpolicies, globalcontextentries, policies, policyexceptions, updaterequests). When using Helm, install the standalone **`kyverno-crds`** chart first, then `kyverno`, then `kyverno-policies` — split landed in 1.16 (#13988) precisely so GitOps tools can order CRDs before the controller release.
- **Upgrade ordering:** CRDs chart → main chart → policies chart. YAML-manifest path: **direct upgrade not supported** — uninstall using the same-tag manifest, then reinstall.
- **Deprecations:** none flagged in this release. The removal of `kubectl` from the webhook cleanup binary (#15067, #15132) is image-internal, not user-facing.
- **Notable:**
  - HTTP context loading enforces a configurable **blocklist** (`FLAG_HTTP_BLOCKLIST`) + scoped token authz — review policies that perform external HTTP calls.
  - `imageRegistryCredentials` now accepts namespaced secrets + pod-level `imagePullSecrets`.
  - Helm chart is now PSS-compliant (#15208); previous custom `securityContext` overrides may now conflict.
  - Helm chart removes finalizers + uninstall workarounds (#15260) — clean uninstall behavior changed.
  - Admission-controller HPA supports memory-utilization scaling (#15303).
  - `/metrics` endpoint supports TLS (#14232).
  - CLI: `kyverno apply` / `kyverno test` extended to cleanup policies, HTTP/Envoy authz policies, mutateExisting MPOLs.

## 1.17.0 (2026-02-02)

- **k8s floor:** 1.32 – 1.35
- **Breaking:** none at the API level. Note `release-1.17` is **EOL** as of 1.18 GA (2026-04-29) — community patches stopped at 1.17.2 (2026-04-23).
- **CRD migrations:** adds **`NamespacedValidatingPolicy`**, **`NamespacedImageValidatingPolicy`**, **`NamespacedMutatingPolicy`**, **`NamespacedDeletingPolicy`**, **`NamespacedGeneratingPolicy`** — five new namespaced CRDs in the `policies.kyverno.io` group. The 1.16 CRDs chart (`kyverno-crds`) must be upgraded **before** the main chart so the new types resolve.
- **Upgrade ordering:** CRDs chart → main chart. Skipping minors: read 1.16 notes (RBAC + standalone CRDs chart).
- **Deprecations:** **v1alpha1** marked unserved for `UpdateRequest` (#14145); `v1beta1` is the new served version for `ValidatingPolicy`, `ImageValidatingPolicy`, `MutatingPolicy`, `GeneratingPolicy`, `DeletingPolicy`, `PolicyException`. `v2beta1` is served for `GlobalContextEntry`. Existing v1alpha1 resources auto-convert via the webhook conversion strategy, but new manifests should target the bumped versions.
- **Notable:**
  - Pod Security Standards subrule (`podSecurity`) now tracks **k8s v1.30 – v1.32** PSS profile mapping (#14255). Older PSS-restricted profiles map to the corresponding k8s minor; if the cluster runs k8s 1.33+, the latest mapping is fine.
  - CEL libraries: `quantity`, `resource.Get`/`resource.List`, `semver`. `params` supported in VAP/MAP CLI mode.
  - Performance: lazy dynamic watcher hash updates, restmapper optimization, histogram min/max tracking disabled by default.

## 1.16.0 (2025-11-10)

- **k8s floor:** 1.31 – 1.34
- **Breaking:** **deprecated webhook removed** (#13273) — clusters that pinned to the old webhook path will fail health checks until upgraded.
- **CRD migrations:** the **CEL-based policy CRDs** introduced as v1alpha1 — `ValidatingPolicy`, `ImageValidatingPolicy`, `MutatingPolicy`, `GeneratingPolicy`, `DeletingPolicy`, `CleanupPolicy` — graduate to **`v1beta1`** as their primary served version. `PolicyException` bumped to v1beta1; `GlobalContextEntry` bumped to v2beta1. Existing v1alpha1 manifests are auto-converted on apply. New chart split: **`kyverno-crds`** standalone Helm chart (#13988) so CRDs install in their own release, ahead of the controller. Affected CRDs (carried by the migration job): `cleanuppolicies.kyverno.io`, `clustercleanuppolicies.kyverno.io`, `clusterpolicies.kyverno.io`, `globalcontextentries.kyverno.io`, `policies.kyverno.io`, `policyexceptions.kyverno.io`, `updaterequests.kyverno.io`.
- **Upgrade ordering:** **CRDs first**, controller second. From 1.15 → 1.16 with Helm: install `kyverno-crds` chart, then upgrade `kyverno` chart. YAML-manifest path: uninstall using the prior tag's `install.yaml`, then `kubectl create -f` the 1.16 tag's `install.yaml` (direct YAML upgrade still unsupported, per upstream docs).
- **Deprecations:** old v1alpha1 served versions for the CEL policy CRDs deprecated in favor of v1beta1 (still served, but new resources should use v1beta1). `v1alpha1` of `UpdateRequest` will be marked unserved in 1.17.
- **Notable:**
  - **k8s libraries bumped to 1.34** internally (#14191) — first minor that can run on a 1.34 control plane.
  - CEL `matchConditions` support, label-selector in `resource.List`, `params` in VAP/MAP, CLI completion command.
  - `bind` ClusterRole added to background controller default RBAC (#14278) — RBAC drift if previously stripped.
  - Helm: standalone CRDs chart (#13988), template-value globalization (#14144), unused hook cleanup, shorter hook names.
  - VAP/MAP reporting flipped from opt-out to **opt-in** (#14353) during the 1.16 cycle — verify before relying on auto-emitted reports.

---

## Cross-cutting CRD-migration gotcha

Kyverno 1.13 (out of registry scope but referenced by the upstream upgrade doc) was the last hard break — it dropped wildcard view perms and removed `register: "*"` default exceptions. Any cluster still on `< 1.13` cannot upgrade to 1.16+ via Helm without the v2→v3 chart migration. Within 1.16–1.18, the load-bearing CRD-ordering pattern is: **always upgrade the standalone `kyverno-crds` chart before the main `kyverno` chart**, and never bump the controller image tag in-place without re-applying CRDs from the matching release tag. Skipping a minor (e.g. 1.15 → 1.18 in one step) is not supported via YAML; via Helm, read every intervening release's notes — Kyverno does not gate the upgrade path in the chart itself.

## kyverno-cli compatibility

The `kyverno` CLI version should match the cluster's controller minor. Cross-version CLI use (e.g. running 1.16 CLI against a 1.18 cluster) works for basic `apply` / `test` but the CLI cannot evaluate newer policy types (e.g. NamespacedMutatingPolicy on 1.16 CLI). When CI lints policies that target a 1.18 cluster, pin the CLI to ≥ 1.18.
