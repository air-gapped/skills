# Rancher — compat (sifted from release_notes)

- **Primary source:** https://github.com/rancher/rancher/releases
- **Secondary sources:** (none — release notes only; SUSE Prime support-matrix pages are Prime-flavored and out of scope)
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 2.12
- **Last sifted:** 2026-05-28

Community edition only. Community minors land Mar / Jul / Nov; Prime backports ship Apr / Aug / Dec and end-of-line Prime patches are **ignored here**. 18-month community support window from 2.9 onward — 2.12 (Jul 2025) supported through ~Jan 2027, 2.13 (Nov 2025) through ~May 2027, 2.14 (Mar 2026) through ~Sep 2027.

The single axis is the **k8s minor that the Rancher management cluster runs on**. Downstream-cluster provisioning (KDM bundling, downstream RKE2/K3s version dropdowns) is **out of scope** — the operator manages downstream clusters by hand. Each `## <version>` block below covers the latest community patch line of one Rancher minor.

## 2.14 (latest community: v2.14.2, 2026-05-28)

- **k8s floor:** 1.33 – 1.35 (adds 1.35; removes 1.32 — issues #52957, #53764).
- **Breaking:**
  - **Embedded Cluster API removed** (#53291). `rancher-provisioning-capi` chart, `embedded-cluster-api` feature flag, and the associated webhooks/controllers are gone. Rancher Turtles becomes the only CAPI integration. Auto-migrates on upgrade *unless* Turtles was previously disabled — re-enable manually or v2prov breaks.
  - **Cluster API bumped to v1beta2 (`cluster-api v1.12.2`, was v1.10.6)** (#52034, #53334). One-way rollback hazard: downgrading to 2.13.x (which carries v1beta1) requires the special rollback procedure documented under `rancher-documentation/v2.14/.../rollbacks`. Skipping it leaves CAPI CRDs in a state 2.13 cannot reconcile.
  - **Backup/Restore rollback from 2.14 → 2.13 needs Rancher resource cleanup on local cluster** before restore — straight BRO restore does not work (rancher/backup-restore-operator#916).
  - Rancher Ingress no longer emits `nginx.ingress.kubernetes.io/proxy-{connect,read,send}-timeout` annotations by default (#53272). Ingress controllers other than `ingress-nginx` (Traefik especially) now get a cleaner Ingress object; operators with a custom proxy that relied on the defaults must set them explicitly.
  - **Upgrade 2.13.2 → 2.14 caused `CrashLoopBackOff`** (#53854). Fix landed in 2.14.0 GA — surveyed clusters upgrading from a 2.13.x earlier than the fix point must pass through a 2.13.3+ first if hit.
- **CRD migrations:**
  - CAPI CRDs flip to `v1beta2` (see Breaking). `clusters.cluster.x-k8s.io` and the rest of the CAPI set get converted; Rancher Turtles handles the conversion if installed, otherwise leftover v1beta1 resources block reconciliation.
  - Continuing migration of `tokens.management.cattle.io` → `tokens.ext.cattle.io` (started 2.13). UI now supports the new resource; legacy tokens still served. Scheduled for complete removal in a later minor.
- **Upgrade ordering:**
  - **Rancher mgmt cluster upgrades BEFORE any downstream-cluster k8s changes** (operator-managed downstream is out of scope here, but the ordering still applies if downstream clusters exist).
  - **cert-manager must be on a chart-supported version BEFORE Rancher 2.14 upgrade** — the Rancher Helm chart removed support and version-check shims for EOL/unsupported cert-manager versions (#52922). Bump cert-manager into the supported window first, or the helm upgrade fails admission.
  - If Turtles was previously disabled, re-enable BEFORE upgrade or v2prov breaks post-upgrade.
- **Deprecations:**
  - **`tokens.management.cattle.io`** — phased removal continues from 2.13.
  - **Cluster API Addon Provider Fleet (CAAPF)** disabled by default in **2.14.1** (turtles#2176); removal in a later release. Migration script provided. Standard Fleet integration unaffected.
  - **CAPRKE2 `v1alpha1` API** marked deprecated (cluster-api-provider-rke2#797).
- **Notable:**
  - **Fleet bumped to v0.15.0, migrated Helm v3 → Helm v4** (fleet#4351). Known issue: drift correction may misbehave with Helm v4 (#4878) — partial fix in 2.14.1, full fix tracked in v0.15.x.
  - Gateway API supported as an install-time network exposure for the Rancher chart itself (#52796) — alternative to Ingress.
  - **Google OAuth login broken in 2.14.0**; fix targeted for 2.14.1 (#54387). If using Google OAuth, skip 2.14.0 GA, install 2.14.1+ directly.
  - `cert-manager` version-check code removed from the Rancher chart — the chart now only supports cert-manager versions compatible with Rancher's own k8s support window. No more compat fallback path.

## 2.13 (latest community: v2.13.2, 2026-01 — patches 2.13.3+ are Prime cadence)

- **k8s floor:** 1.32 – 1.34 (adds 1.34; removes 1.31 — issues #51252, #51253).
- **Breaking:**
  - **Rancher Provisioning chart auto-replaced by Rancher Turtles** on upgrade (#52254). `rancher-provisioning-capi` is uninstalled, Rancher Turtles is installed. Pre-upgrade backups of any `clusters.provisioning.cattle.io` resources are advisable — they survive the migration but the controller path changes.
  - **OIDC Auth Provider settings may be lost on 2.12.x → 2.13.x upgrade** (#53995). Cleanup of unused OIDC secrets can partially overwrite the AuthConfig and drop endpoints / client IDs. Fix is in **2.14**; on 2.13 itself, back up the OIDC AuthConfig before upgrading.
  - **Rollback 2.13.0 → 2.12.3 via BRO is broken** (backup-restore-operator#844). Workaround: scale Rancher to 0 and uninstall the Webhook chart before restore.
- **CRD migrations:**
  - New `tokens.ext.cattle.io` resource introduced (begins the phase-out of `tokens.management.cattle.io`). Both served in parallel.
  - GitHub App auth provider adds a new AuthConfig variant (#50517) — additive, no migration required for existing GitHub auth.
- **Upgrade ordering:**
  - **Rancher mgmt cluster upgrades BEFORE downstream changes.**
  - If Turtles was hand-installed before upgrade, the auto-replacement still runs — ensure no version mismatch by letting the upgrade reconcile, then verify the Turtles chart version matches what 2.13.x ships.
- **Deprecations:**
  - **Kubernetes ≤ 1.31** dropped from downstream provisioning support (out of scope here, but the same cut applies to mgmt cluster's k8s floor).
  - `tokens.management.cattle.io` enters phased deprecation (will remove in a later minor).
- **Notable:**
  - Initial IPv6 support for the mgmt cluster itself (#49689) — mgmt can run on IPv6-only or dual-stack.
  - Mgmt cluster still requires **k8s API Aggregation Layer enabled** (#50400). RKE2/K3s have it on by default — non-RKE2 mgmt clusters must verify.
  - Helm client ≥ 3.18 required (carried from 2.12).

## 2.12 (latest community: v2.12.6, 2026-01 — patches 2.12.7+ are Prime cadence)

- **k8s floor:** 1.31 – 1.33 (adds 1.33; removes 1.30 — issues #48796, #49679).
- **Breaking:**
  - **RKE1 / RKE-the-binary EOL'd 2025-07-31** — Rancher 2.12+ refuses to provision or manage downstream RKE1 clusters, and ships a **pre-upgrade validation check** that fails the helm upgrade if any RKE1 resources remain (#50286). Out-of-scope here for downstream, but the check fires against the mgmt cluster's resource set and will block the Rancher chart upgrade itself if a stale `cluster.management.cattle.io` of kind=RKE1 exists. Delete RKE1 leftovers before upgrade.
  - **Server-Side Pagination (`ui-sql-cache`) enabled by default** (#48691). Introduces an internal SQLite cache stored in the container's ephemeral filesystem on Rancher server pods AND on `cattle-cluster-agent` pods downstream. Rough sizing: ~2× the raw object size, or ~2× etcd snapshot. **A mgmt node tight on ephemeral disk will hit DiskPressure → pod eviction** after upgrade. Audit node ephemeral storage before upgrading.
  - **CRD validation tightening on `dynamicschemas.management.cattle.io` and dynamically generated `*machines.rke-machine.cattle.io` / `*machinetemplates.rke-machine.cattle.io`** (#49402). `null` values disallowed where previously tolerated; `effect`/`key` now required on taints; `timeAdded` must be `date-time` formatted; `cloudCredentialSecretName` capped at 317 chars. Stale machine resources with `null` fields will fail validation on first reconcile post-upgrade.
  - **Imported clusters created by directly instantiating `cluster.provisioning.cattle.io` (pre-2.11 style) fail to reconnect** after upgrade from 2.11.x → 2.12.0 (#51066). Imported clusters created via the UI / `cluster.management.cattle.io` are unaffected.
  - **`AUDIT_LEVEL=0` default behavior changed** (#48941). Pre-2.12 `0` = audit disabled; 2.12+ `0` = request/response metadata captured. New `AUDIT_LOG_ENABLED` knob is the disable switch. Cluster-wide audit pipelines must re-tune retention.
- **CRD migrations:**
  - **`cis.cattle.io/v1` → `compliance.cattle.io/v1`** — Rancher CIS Benchmarks renamed and rebuilt as **Rancher Compliance App** (#50795/#50797). Old CRDs and the CIS Operator are removed; the new Compliance Operator + CRD set takes over. CIS scan history is not migrated.
  - New `tokens.ext.cattle.io` introduced in 2.13 — **not present in 2.12**.
- **Upgrade ordering:**
  - **Pre-upgrade RKE1 resource sweep** (see Breaking) is gating — runs first, fails the helm upgrade if any RKE1 resources linger.
  - **Helm client ≥ 3.18 required** before upgrading the Rancher chart (k8s 1.33 support depends on it). Helm ≤ 3.17 will refuse the upgrade.
  - **cert-manager** still required; chart still ships compat shims for EOL versions in 2.12 (these shims are removed in 2.14).
- **Deprecations:**
  - **Rancher-Istio** deprecated in 2.12.0 — use the SUSE Application Collection Istio build (Prime-gated, so community operators have no Rancher-managed Istio path going forward).
  - **RKE1** (mgmt + downstream) — terminal, EOL.
  - **Rancher CIS Benchmarks** (replaced by Rancher Compliance App).
  - Kubernetes ≤ 1.30 no longer supported.
- **Notable:**
  - Fleet bumped to **v0.13.0**; HelmOps promoted out of experimental and enabled by default. Operators authoring `fleet.yaml` with `helm:` blocks now get production-supported behavior.
  - Image-artifact digest filename layout flattens — `rancher-images-digests-linux-{amd64,arm64}.txt` collapse into `rancher-images-digests-linux.txt`. Air-gapped mirror scripts that grep on the old names break.
  - mgmt cluster requires **k8s API Aggregation Layer** enabled (#50400).
  - ARM64 mgmt cluster officially supported; mixed-architecture clusters still experimental.
