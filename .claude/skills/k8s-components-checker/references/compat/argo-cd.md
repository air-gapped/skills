# argo-cd — compat (sifted from published_matrix)

- **Primary source:** https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/
- **Secondary sources:** https://github.com/argoproj/argo-cd/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 3.0
- **Last sifted:** 2026-05-28

Tested-Kubernetes-versions matrix on `stable` lists only v3.2 / v3.3 / v3.4. v3.0 / v3.1 rows pulled from `release-3.0` / `release-3.1` historical docs. **Both v3.0 and v3.1 are EOL upstream** (v3.0 EOL 2026-02-02 at v3.0.23; v3.1 EOL 2026-05-06 at v3.1.16) — encountering either is an automatic ✗ blocker, but the rows are kept for migration-path planning. See companion skill `argo-cd-apps` for application-authoring detail; this file is k8s-compat only.

## 3.4 (latest: v3.4.2, 2026-05-12)

- **k8s floor:** 1.32 – 1.35
- **Breaking:**
  - Resource tracking is **annotation-based by default** (carried over from v3.0; cluster bumps moving from v2.x or v3.0 mid-rollout will re-track resources — operators must run the `argocd admin app generate-spec --resource-tracking-method annotation` migration before flipping).
  - **app-in-any-namespace promoted to Stable** in v3.4 — `application.namespaces` config now production-supported; manifests in tenant namespaces start being authoritative.
  - **Sync impersonation (`destinationServiceAccounts`) promoted to Beta** — behavior is stable but field can still shift; clusters using it must pin to v3.4.x patch line.
- **CRD migrations:** none in this minor; `argoproj.io/v1alpha1` still the only served version.
- **Upgrade ordering:** none against other registry components; Argo CD does not gate RKE2/Rancher upgrades.
- **Deprecations:** none new this minor.
- **Notable:**
  - Source Hydrator still **Alpha** — schema may break in v3.5; do not build long-lived automation on `spec.sourceHydrator`.
  - CMP (Config Management Plugin) sidecar protocol unchanged from v3.3.
  - ApplicationSet generators stable; no new generators in v3.4 (incremental fixes to DuckType, PullRequest, Git only).
  - **CVE-2026-42880 patched** in v3.4.x line as of v3.4.0 GA (fixed in v3.3.8 / v3.2.10 / v3.1.15 for older lines; v3.4 was patched pre-GA). Confirms `IncludeMutationWebhook=true` no longer leaks Secret plaintext.

## 3.3 (latest: v3.3.10, 2026-05-12)

- **k8s floor:** 1.32 – 1.35
- **Breaking:**
  - **3.3.0 + 3.3.1 are broken — skip them.** Forced `kubectl-client-side-apply` → SSA field-manager migration regressed many real apps. Workaround was `ClientSideApplyMigration=false` syncOption. **Fixed in 3.3.2** (2026-02-22). Any survey finding a cluster on 3.3.0 / 3.3.1 must verdict ✗ blocker until bumped to ≥ 3.3.2.
  - When Argo CD manages itself, the self-managing Application requires `ServerSideApply=true` in `syncOptions` — ApplicationSet CRD exceeds the 262 144-byte client-side-apply annotation limit. Without it the meta-app sync fails on upgrade.
  - **CVE-2026-42880** — `ServerSideDiff` + `compare-options: IncludeMutationWebhook=true` annotation leaked plaintext Secret data to anyone with `applications, get`. **Patched 3.3.8** (2026-04-21). Surveyed cluster on 3.3.x must be ≥ 3.3.8 if it handles Secrets at all.
- **CRD migrations:** none.
- **Upgrade ordering:** none against other registry components.
- **Deprecations:** none new this minor.
- **Notable:**
  - **Progressive Sync promoted to Beta** for ApplicationSet (per v3.3.0 docs commit `6cfef6b`).
  - Source Hydrator gained inline parameter support; still Alpha.
  - HPA v2 (`autoscaling/v2`) support added (low signal — `autoscaling/v1` already worked).
  - Server-Side Diff (Stable since v3.2) still **not default** — `IncludeMutationWebhook` opt-in flag is the CVE vector; strip it from every Application.

## 3.2 (latest: v3.2.12, 2026-05-13)

- **k8s floor:** 1.31 – 1.34
- **Breaking:**
  - **CVE-2026-42880 patched** in **v3.2.10** (2026-04-21). Surveyed cluster on 3.2.x must be ≥ 3.2.10 if it handles Secrets.
  - `syncPolicy.automated.enabled=false` semantics fixed in 3.2.x (`#24254`) — pre-fix builds treated the field as no-op and continued auto-syncing. Pre-3.2 manifests relying on this to disable auto-sync silently break on 3.2 if they used a different toggle.
- **CRD migrations:** none.
- **Upgrade ordering:** none against other registry components.
- **Deprecations:**
  - `extensions/v1beta1` shim removed for built-in health checks (`#381`). Apps still referencing those API versions in `ignoreDifferences` or health Lua scripts will misbehave.
- **Notable:**
  - **Server-Side Diff promoted to Stable.** Not default — apps opt in per-Application via `compare-options: ServerSideDiff=true` annotation or globally via `argocd-cmd-params-cm`.
  - **Server-Side Apply migration** logic landed (`#727`) — auto-migrates `kubectl-client-side-apply` fields when ServerSideApply is enabled. This is the same code that regressed in 3.3.0 — 3.2 line is the safe LTS choice if 3.3.x/3.4.x adoption isn't required.
  - ApplicationSet PR generator returns 0 results on repo-not-found rather than failing (`#23447`) — silent behavior change; AppSets relying on hard failure to gate sync need a different signal.

## 3.1 (latest: v3.1.16, 2026-05-05 — **EOL 2026-05-06**)

- **k8s floor:** 1.31 – 1.34
- **EOL.** v3.1.16 release notes carry the upstream EOL banner. No more security or bug patches. Verdict ✗ blocker — must bump to ≥ 3.2.
- **Breaking:**
  - **k8s floor jumped from 1.29 (v3.0) to 1.31.** RKE2 / Rancher clusters that ran v3.0 on k8s 1.29 / 1.30 must bump the kube control plane before installing 3.1.
  - **SSA field-manager migration options added** (`#23337`) — opt-in here; defaults flipped in 3.3.0 and immediately regressed. Pre-stage `ClientSideApplyMigration=false` syncOption on apps that already opted in, so the 3.3 upgrade path is reversible.
  - **`spec.preserveUnknownFields` default ignoreDifference removed** (`#22948`) — Applications that relied on that hidden ignore now show drift on CRDs that still carry the field. Drop the field from CRD specs (it's `false` by default in apiextensions/v1 anyway).
  - **CVE-2026-42880 patched** in **v3.1.15** (2026-04-21). Surveyed cluster on 3.1.x must be ≥ 3.1.15 if it ever handled Secrets — but the whole minor is EOL now, so just bump.
- **CRD migrations:** none.
- **Upgrade ordering:** bump k8s to ≥ 1.31 before installing 3.1 if jumping from 3.0 on 1.29 / 1.30.
- **Deprecations:** none new this minor.
- **Notable:**
  - **OCI native source support promoted to Beta** (`#18646`) — `source.repoURL: oci://...` works without the Helm shim. Pin by digest, not tag.
  - **Apps-in-any-namespace fix for ApplicationSet UI** (`#23601`) — cosmetic, not behavioral.
  - Sync impersonation (`destinationServiceAccounts`) still **Alpha** in 3.1; promoted to Beta in 3.4.
  - Progressive Sync still **Alpha** in 3.1; promoted to Beta in 3.3.
  - Source Hydrator still **Alpha**.

## 3.0 (latest: v3.0.23, 2026-01-22 — **EOL 2026-02-02**)

- **k8s floor:** 1.29 – 1.32
- **EOL.** v3.0.23 release notes carry the upstream EOL banner. Verdict ✗ blocker — must bump.
- **Breaking — the seven v3.0 default flips landed in this minor:**
  1. **Resource tracking is annotation-based by default** (`#22230` — `update compareoptions default values`). Clusters upgrading from 2.x with no prior `argocd admin app generate-spec --resource-tracking-method annotation` migration will re-track every resource and may orphan-prune. Run the migration BEFORE installing 3.0.
  2. **Logs RBAC enforced by default** (`#21678`). Roles without explicit `logs, get` lose pod-log visibility in the UI on upgrade.
  3. **Fine-grained RBAC inheritance disabled by default** (`#19988` / `#20671`). `update` / `delete` no longer cascade to managed resources. Audit AppProject roles before upgrade.
  4. **Default `resource.exclusions` ships with the install** (`#20013` / `#21635`) — Endpoints, EndpointSlice, Lease, *SubjectAccessReview, TokenReview, CSR, CertificateRequest, Kyverno reports, Cilium endpoints, PolicyReports excluded. Apps that relied on tracking any of these go OutOfSync until ignoreDifferences are widened.
  5. **`.status` ignored on all resources by default** (was: only CRDs). Mutation-webhook drift in `.status` no longer surfaces.
  6. **In-cluster destination off by default** (`cluster.inClusterEnabled: "false"`). New apps targeting the local cluster hard-fail until flipped on.
  7. **`spec.preserveUnknownFields: false` on CRDs causes drift.** Drop the field; use `x-kubernetes-preserve-unknown-fields: true` on schemas.
  - **CVE-2026-42880 patched** in **v3.0.22** (2026-01-13). Last security patch before EOL. Any unpatched 3.0.x is double-blocker (EOL + unpatched CVE).
  - **Batch event processing enabled by default** (`#22338`) — perf win, but reorders some controller events; CI smoke tests that race on event timing may flake.
- **CRD migrations:** none in this minor itself, but the 2.x→3.0 jump requires `resources-finalizer.argocd.argoproj.io` finalizer audit (cascade-delete behavior changed with the RBAC inheritance flip).
- **Upgrade ordering:** k8s must be ≥ 1.29 for 3.0; cannot install on 1.28 or older RKE2.
- **Deprecations:** ksonnet support removed (long-deprecated; final removal here). Apps still using `spec.source.ksonnet` fail to sync.
- **Notable:**
  - Source Hydrator GA'd as **Alpha** in 3.0 (`#22485`, `#22753`) — schema unstable.
  - kubectl bundled at 1.32.x (`#21724` / `#22168`); helm at 3.17.0 (`#21722`).
  - Default logging format switched to JSON (`#21656`) — log-scraper regexes built for the legacy text format break on upgrade.
  - Azure workload identity support added for Git/OCI repos and Entra SSO (`#21118`, `#21433`).

---

## Cross-version notes

- **Upstream support window.** Argo CD upstream tests three minors (current + 2 prior). At 2026-05-28: 3.4 (latest), 3.3, 3.2. 3.1 / 3.0 are EOL upstream — verdict ✗ blocker if found.
- **k8s floor stability.** Floor history: 3.0 → 1.29; 3.1 → 1.31 (jumped two); 3.2 → 1.31 (held); 3.3 / 3.4 → 1.32. RKE2 clusters on 1.31 cannot run 3.3+ per the tested matrix; bump RKE2 first or stay on Argo CD 3.2.x. RKE2 on 1.29 / 1.30 is now stuck on EOL Argo CD (v3.0 only) — k8s bump is mandatory before any supported Argo CD.
- **The seven v3.0 default flips** (annotation tracking, `.status` ignored, default `resource.exclusions`, logs-RBAC enforced, no update/delete RBAC inheritance, `preserveUnknownFields: false` causes drift, in-cluster destination off by default) are still in effect across 3.2/3.3/3.4. Any v2.x → v3.x jump in scope must address all seven — defer to `argo-cd-apps` skill `references/version-changes.md` § v3.0.
- **No `ServerSideDiff=true` + `IncludeMutationWebhook=true` combo on unpatched builds.** This is the CVE-2026-42880 trigger. Verdict ✗ blocker if the cluster runs ServerSideDiff and any patched build is not in place.
