# Rancher — compat (sifted from release_notes)

- **Primary source:** https://github.com/rancher/rancher/releases
- **Secondary sources:** (none — release notes only; SUSE Prime support-matrix pages are Prime-flavored and out of scope)
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 2.11
- **Last sifted:** 2026-06-02
- **Last release-verified (gh):** 2026-06-02 — 2.11 community patch ceiling derived by edition discriminator (see § Community vs Prime). Prior verify (2026-05-30) re-derived 2.12/2.13/2.14 by edition; the earlier 2.12→v2.12.6 / 2.13→v2.13.2 values were wrong — v2.12.6 is a **Prime-only** patch that anti-fabrication grounding rubber-stamped as community.

Community edition only. Community minors land Mar / Jul / Nov; Prime backports ship Apr / Aug / Dec and end-of-line Prime patches are **ignored here**. 18-month community support window from 2.9 onward — 2.11 (Mar 2025) supported through ~Sep 2026, 2.12 (Jul 2025) through ~Jan 2027, 2.13 (Nov 2025) through ~May 2027, 2.14 (Mar 2026) through ~Sep 2027. 2.11 is a common **migration source** minor; its community line ends at v2.11.3 (see §2.11).

**Community vs Prime — how the per-minor ceilings below are derived (do NOT trust `sort -V | tail -1`).** `rancher/rancher` GitHub releases carry **both** editions and the `prerelease` flag does not separate them. Discriminator = release-notes first line: a patch is **Prime-only iff its body redirects to "Please refer to our Prime Documentation …"**; community patches either say "This is a Community version release" or carry inline notes (`# Release vX.Y.Z`) — so test for the Prime marker and treat its **absence** as community (a positive "community version release" grep misses the older inline-notes format). **Pattern:** once a newer community minor ships, the older minor's later patches flip to Prime-only, so an older minor's *top* tag is a Prime patch, not its latest community patch. Full derivation protocol: `references/version-verification.md` § Edition discrimination.

> **2.11-line caveat (the first-line test under-detects — confirm against the self-declaration line).** The 2.11 line uses **two** Prime markers, and the cheap first-line check (`head -1 | grep -i 'prime documentation'`) only catches one. v2.11.9+ use the *redirect* format ("Please refer to our Prime Documentation …") and are caught. But **v2.11.4 – v2.11.8 ship inline `# Release vX.Y.Z` notes** (so their first line looks community) **yet self-declare "This is a Prime version release"** in the description paragraph — the first-line test wrongly passes them as community. Defense: also grep the body for the self-declaration line (`grep -oiE 'This is a (Community|Prime) version release'`) and treat **"Prime version release"** as Prime-only. Observed 2.11 mapping (2026-06-02): v2.11.0 "Community", v2.11.1/v2.11.2 inline-only (community-era, pre-self-declaration format), **v2.11.3 "Community and Prime"** (last community patch), v2.11.4–v2.11.8 "Prime version release", v2.11.9–v2.11.14 Prime-docs redirect. **Community ceiling = v2.11.3** — `sort -V | tail -1` (v2.11.14) and even the first-line discriminator alone (v2.11.8) both overshoot.

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
  - **Google OAuth login broken in 2.14.0**; fixed in 2.14.1 (main issue #54387; v2.14 backport tracked as #54416 — both CLOSED, gh-verified 2026-05-30). If using Google OAuth, skip 2.14.0 GA, install 2.14.1+ directly.
  - `cert-manager` version-check code removed from the Rancher chart — the chart now only supports cert-manager versions compatible with Rancher's own k8s support window. No more compat fallback path.

## 2.13 (latest community: v2.13.3, 2026-02-25 — patches 2.13.4+ are Prime-only)

- **k8s floor:** 1.32 – 1.34 (adds 1.34; removes 1.31 — issues #51252, #51253).
- **Breaking:**
  - **Rancher Provisioning chart auto-replaced by Rancher Turtles** on upgrade (#52254). `rancher-provisioning-capi` is uninstalled, Rancher Turtles is installed. Pre-upgrade backups of any `clusters.provisioning.cattle.io` resources are advisable — they survive the migration but the controller path changes.
  - **OIDC Auth Provider settings may be lost on 2.12.x → 2.13.x upgrade** (#53995). Cleanup of unused OIDC secrets can partially overwrite the AuthConfig and drop endpoints / client IDs. Fix is in **2.14**; on 2.13 itself, back up the OIDC AuthConfig before upgrading.
  - **Rollback 2.13.0 → 2.12.3 via BRO is broken** (backup-restore-operator#844). Workaround: scale Rancher to 0 and uninstall the Webhook chart before restore.
  - **Air-gapped: `capi-controller-manager` may fail to reach Active after the 2.13 upgrade, blocking cluster provisioning** (#52816). Pre-stage the CAPI controller images in the private mirror and watch the pod post-upgrade. (gh-verified 2026-05-30.)
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

## 2.12 (latest community: v2.12.4, 2025-11-24 — patches 2.12.5+ are Prime-only)

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

## 2.11 (latest community: v2.11.3, 2025-06-25 — patches above are Prime-only)

> Edition note: v2.11.3 self-declares **"This is a Community and Prime version release"** (last community 2.11 patch). v2.11.4 – v2.11.8 self-declare **"Prime version release"** despite carrying inline `# Release` notes (the first-line discriminator misreads them as community — see § Community vs Prime, 2.11-line caveat); v2.11.9+ use the Prime-docs redirect. The operator's stated migration source **2.11.3 is community** — confirmed groundable and the highest community 2.11 patch.

- **k8s floor:** 1.30 – 1.32 (adds 1.32 — #47934; removes 1.28/1.29, so the mgmt-cluster floor lifts to 1.30 — #48628). One minor below 2.12's 1.31–1.33, consistent with the file's pattern.
- **Breaking:**
  - **Kubernetes 1.28 / 1.29 dropped** (#48628). Before upgrading *to* 2.11.0 the mgmt (and downstream, out of scope) clusters must already be on **k8s ≥ 1.30**. An operator sitting on 2.11 is therefore on 1.30–1.32; the forward hop to 2.12 then requires reaching **≥ 1.31** (2.12 removes 1.30).
  - **`imperative-api-extension` enabled by default** (#47010) — adds Rancher APIs via the k8s **aggregation layer**. The mgmt cluster MUST have the API Aggregation Layer enabled (RKE2/K3s have it on by default; a non-RKE2 mgmt cluster must verify). This is the 2.11-era origin of the standing "aggregation layer required" constraint carried forward through 2.13/2.14.
  - **Restricted Admin role removed** (#47875). Existing users holding it have those privileges **revoked on upgrade** to 2.11 — re-grant via GlobalRoles before relying on them post-upgrade.
  - **Legacy features removed:** multi-cluster app (and its CLI subcommands), `globaldns` CLI subcommand, legacy Rancher telemetry / data-collection opt-out (#48252, #39525, #12639). UI `v-tooltip` replaced by `v-clean-tooltip` (XSS fix, CVE-2024-52281).
- **CRD migrations:**
  - **Generic imported clusters now use the v3 `cluster.management.cattle.io` object** (#13151). This is the migration that makes the 2.11→2.12 hazard concrete: clusters imported the **pre-2.11 way** by directly instantiating `cluster.provisioning.cattle.io` fail to reconnect after 2.12.0 (#51066, documented in §2.12). On 2.11, re-import any such cluster through the UI / v3 path **before** hopping to 2.12.
  - etcd-snapshot tracking moves to listing `etcdsnapshotfile.k3s.cattle.io` resources instead of CLI/configmap scraping (#44452) — additive, no manual conversion.
  - `GlobalRoleBinding` / `ClusterRoleTemplateBinding` gain status fields + `userPrincipalId` support (#44668, #44663, #47359) — additive.
  - No `tokens.ext.cattle.io` yet — that resource is introduced in **2.13**; 2.11 carries only `tokens.management.cattle.io`.
- **Upgrade ordering (what a 2.11 operator must do):**
  - **Reach k8s ≥ 1.30 before installing 2.11.0**; then reach **≥ 1.31 before hopping to 2.12** (2.12 drops 1.30).
  - **Re-import pre-2.11-style direct-`provisioning.cattle.io` clusters via the v3 path before 2.12** (#51066) — the forward gate.
  - **Sweep RKE1 / RKE-the-binary resources before 2.12** — RKE1 EOL'd 2025-07-31 and 2.12 ships a gating pre-upgrade check that fails the helm upgrade if any RKE1 resource lingers (#48252 announces the EOL in 2.11; the gate lands in 2.12, §2.12). 2.11 still manages RKE1.
  - **Back up the OIDC AuthConfig before the 2.12→2.13 hop** — the generic OIDC provider (enhanced with `GroupSearchEnabled` in 2.11, #48145) can lose settings on 2.12.x→2.13.x (#53995, §2.13). An operator standing up OIDC on 2.11 should record the AuthConfig now.
  - **Helm client floor:** 2.11.0 ships Rancher CLI v2.11.0 / RKE v1.8.1; the Helm-client-≥-3.18 requirement is a **2.12-and-later** gate (for k8s 1.33), not enforced at 2.11. Bumping the Helm client before the 2.12 hop is still advisable.
- **Deprecations:**
  - **RKE1 / RKE-the-binary** — EOL announced for 2.12+ here (#48252); 2.11 is the last minor that manages it.
  - Weave CNI plugin for RKE ≥ 1.27 deprecated (#11322, dashboard).
  - Azure AD Graph API path (Microsoft-deprecated) — migrate to Microsoft Graph before relying on Azure AD auth (#29306).
- **Notable:**
  - **Provisioning is still the classic CAPI stack** — `rancher-provisioning-capi` chart + `embedded-cluster-api` feature flag. The auto-replacement by **Rancher Turtles** does not happen until **2.13** (#52254, §2.13), and embedded CAPI is not removed until **2.14** (#53291). So a 2.11 operator is on the pre-Turtles provisioning controller path; the Turtles migration is a forward concern, not a 2.11 one.
  - **No `ui-sql-cache` / server-side pagination by default** in 2.11 — that ships **enabled-by-default in 2.12** (#48691, §2.12) and brings the ephemeral-disk / DiskPressure sizing concern. Not a 2.11 hazard, but the node-disk audit belongs to the 2.11→2.12 hop.
  - **`AUDIT_LEVEL=0` still means "audit disabled"** on 2.11 — the semantics change (0 = capture metadata) lands in **2.12** (#48941, §2.12). Audit pipelines re-tune on the forward hop, not here.
  - **Rancher CIS Benchmarks (`cis.cattle.io/v1`) still present** on 2.11 — the rename to Rancher Compliance App (`compliance.cattle.io/v1`) and removal of the CIS Operator happen in **2.12** (#50795/#50797, §2.12). Scan history does not migrate across that hop.
  - OCI Helm chart registry for Apps & Marketplace is **experimental** in 2.11 (#29105, #45062).
  - Monitoring chart on `kube-prometheus-stack-66.7.1` (#48992).
