# argo-cd — compat (sifted from published_matrix)

- **Primary source:** https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/
- **Secondary sources:** https://github.com/argoproj/argo-cd/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 3.0
- **Last sifted:** 2026-11-25 — `gh release list`, repo security advisories, `tested-kubernetes-versions.md` at v3.6.3 / v3.5.9 / v3.4.15 / v3.3.19, upgrade docs 3.4→3.5 and 3.5→3.6, v3.3.19 / v3.6.0 / v3.6.3 release notes.
- **Last release-verified (gh):** 2026-11-25 — releases and security advisories of 3.3–3.6 enumerated; ceilings v3.6.3 / v3.5.9 / v3.4.15 / v3.3.19 (final).
- **2026-09-15 RETRACTION of the 2026-05-30 "operator correction".** That note claimed the 3.2
  line ended at **v3.2.6**, that it never received the CVE-2026-42880 backport, and that
  `v3.2.10` / `v3.2.12` **do not exist**. All three are false. The 3.2 line runs to **v3.2.12**
  (2026-05-13) and v3.2.7–v3.2.12 are all real published stable releases; the CVE fixes landed
  in **v3.2.11** and **v3.2.12**. The correction deleted accurate data and replaced it with a
  verdict — *a 3.2.x cluster is permanently exposed, bump to 3.4* — that was wrong on both the
  exposure and the destination. **A "correction" that removes releases is the shape to distrust:
  enumerate the tags before deleting one.**
- **The real reason to leave 3.2 is EOL, not CVE exposure**, and it is derivable rather than
  looked up: **Argo CD supports exactly the newest three minors, and minor N reaches EOL on the
  day minor N+3 GAs.** Three independent confirmations — 3.0 EOL 2026-02-02 = v3.3.0 GA; 3.1 EOL
  2026-05-06 = v3.4.1 GA; 3.2 EOL 2026-08-04 = v3.5.0 GA, stated in v3.2.12's own release notes
  ("final release of the 3.2 release series … upgrade to a supported version (v3.3, v3.4, or
  v3.5)"). Minors land ~every 3 months. **3.3 reached EOL 2026-11-03 = v3.6.0 GA** (v3.3.19, the final 3.3 release, carries the banner naming v3.4.13 / v3.5.7 / v3.6.0). **3.4 EOLs when 3.7 GAs** — not announced; the ~3-month cadence puts it near 2027-02.
- **Advisory floor (2026-11-24): v3.6.3 / v3.5.9 / v3.4.15. 3.3 has no fixed release** — the 2026-11-24 advisories
  (four HIGH: unauthenticated request crashes the API server GHSA-w7rw-fg89-2cjf, Helm chart home-link stored XSS
  GHSA-rxm8-qc6h-3c8h, repository-create upsert overwrite GHSA-mfgm-4p7x-3ccr, ApplicationSet delete API ignoring allowed
  namespaces GHSA-rvmf-gjc9-wjgq; plus three MODERATE) list every `>= 3.0.0, < 3.4.15` build as affected, so **v3.3.19 is exposed
  and unpatchable** — verdict ✗ on EOL plus open HIGHs. Surveyed versions below the floor of their line verdict ✗.
  Earlier floors, all subsumed: 2026-10-07 batch (four critical — two Kustomize command-execution paths in the repo-server,
  a Jsonnet import file read, PreDelete/PostDelete hooks bypassing AppProject restrictions) fixed in 3.5.4 / 3.4.10 / 3.3.15;
  2026-11-20 batch: tar-symlink write outside the extraction directory GHSA-rq7v-q562-vwcq (3.5.5 / 3.4.11 / 3.3.16) and
  ApplicationSet cluster generator leaking cluster credentials via `last-applied-configuration` GHSA-hr74-g9pw-j38m
  (3.5.7 / 3.4.13 / 3.3.19 / 3.6.0). 3.2 and older get no patch.
- **`helm.releaseName` is now validated** (v3.6.3 / v3.5.9 / v3.4.15, GHSA-v2hj-322q-6cg4): passed to Helm literally, must be a valid Helm
  release name (lowercase letters, digits, `-`, `.`; start and end alphanumeric; ≤ 53 chars). An Application whose name used
  template syntax or is invalid **fails manifest generation** after the patch — audit `spec.source.helm.releaseName` and
  `.argocd-source.yaml` before landing the floor.

Tested-Kubernetes-versions matrix at v3.6.3 lists only v3.4 / v3.5 / v3.6 (v3.3.19 lists 3.1–3.3, v3.4.15 lists 3.2–3.4). v3.0 / v3.1 rows pulled from `release-3.0` / `release-3.1` historical docs. **Both v3.0 and v3.1 are EOL upstream** (v3.0 EOL 2026-02-02 at v3.0.23; v3.1 EOL 2026-05-06 at v3.1.16) — encountering either is an automatic ✗ blocker, but the rows are kept for migration-path planning. See companion skill `argo-cd-apps` for application-authoring detail; this file is k8s-compat only.

## 3.6 (GA 2026-11-03, latest: v3.6.3, 2026-11-24 — current minor)

- **Security floor:** v3.6.3 (2026-11-24 advisories — header). v3.6.0 carries the 2026-11-20 fixes; release candidates rc1 / rc2 are affected by earlier advisories (rc1: 2026-10-07 batch; rc1 + rc2: tar-symlink) — never run an RC.
- **k8s floor:** 1.34 – 1.37 (tested-versions matrix at v3.6.3) — a 3.6 bump drops k8s 1.33.
- Its GA put 3.3 out of support (EOL rule in the header).
- **Breaking (3.5 → 3.6 upgrade doc):**
  - **`ServerSideApply=true` now implies Server-Side Diff** — Applications with the sync option compute diffs by an SSA dry-run against the kube-apiserver (the Structured-Merge Diff strategy is removed); expect extra apiserver load and webhooks now take part in the diff stage. Opt out per Application with `argocd.argoproj.io/compare-options: ServerSideDiff=false`.
  - **OpenTelemetry:** repo-server env `ARGOCD_REPO_OTLP_HEADERS` renamed `ARGOCD_REPO_SERVER_OTLP_HEADERS` (old name no longer read); `otlp.insecure` now alone decides plaintext vs TLS (with `"true"`, `OTEL_EXPORTER_OTLP_CERTIFICATE` no longer switches to TLS); the sampler is parent-based, so an inbound not-sampled `traceparent` is honored; `otelgrpc` / `otelhttp` v0.70.0 changes span attribute names (`server.address` is the dial target, not the peer IP).
  - `argocd app diff --local --server-side-generate` default `--local-include` gains `*.tpl` and `Chart.lock`; a custom `--local-include` replaces the defaults entirely.
  - Progressive Sync: before stepping, the ApplicationSet controller annotates all owned Applications for refresh and waits — slower step progression with many Applications.
  - GitOps Promoter `PromotionStrategy` / `ChangeTransferPolicy` report `Healthy` (was `Progressing`) while a promotion is in flight.
- **CRD migrations:** none (API change: ephemeral `configHash` on `Cluster`).

## 3.5 (GA 2026-08-04, latest: v3.5.9, 2026-11-24 — supported, previous minor)

- **Security floor:** v3.5.9 (2026-11-24 advisories — header).
- **k8s floor:** 1.33 – 1.36 (tested-versions matrix at v3.5.9; unchanged).
- **v3.5.0 is affected by GHSA-jj8j-82j2-7ph7** (medium, 2026-11-20: Secret masking skipped when `last-applied-configuration` is not valid JSON — an incomplete fix of CVE-2026-45737); fixed in **3.5.1** (3.4.7, 3.3.14). The first two ServerSideDiff Secret-leak CVEs (CVE-2026-42880, CVE-2026-45737) are below this line (floors 3.4.2 / 3.3.10 / 3.2.12).
- **Breaking (3.4 → 3.5 upgrade doc):**
  - **Helm upgraded to 4.x** (4.2.1 at v3.5.9) and `spec.source.helm.version: v3` is ignored — Helm 4 only. Plain-HTTP OCI registries (including OCI chart *dependencies*) must be registered with `--insecure-oci-force-http` (or `insecureOCIForceHttp: "true"` in the repo Secret); combining it with `--insecure-skip-server-verification` on the same chain silently drops `--plain-http` and fails with no workaround.
  - **UI moved to React 19** — UI extensions must be rebuilt to externalize `react/jsx-runtime` or fail to load.
  - Event-listing gRPC methods (`ListResourceEvents` x2, `ProjectService/ListEvents`) return an Argo CD `EventList` type — regenerate gRPC and OpenAPI-generated clients; REST/JSON and the CLI are unaffected.
  - **Sync impersonation now applies to all API server operations** (logs, events, delete, patch, resource actions), not only sync — `destinationServiceAccounts` accounts need the matching RBAC verbs.
  - Repositories without configured credentials now use `argocd-ssh-known-hosts-cm` for SSH host keys (a baked-in `~/.ssh/known_hosts` in the repo-server is no longer read).
  - GnuPG verification replaced by Source Integrity; `AppProject.spec.signatureKeys` deprecated (legacy config still works with a warning).
- Its GA date is what put 3.2 out of support — see the EOL rule in the header.

## 3.4 (latest: v3.4.15, 2026-11-24 — supported, oldest supported minor)

- **Security floor:** v3.4.15 (2026-11-24 advisories — header). Also fixes GHSA-jj8j-82j2-7ph7 at 3.4.7 (see § 3.5).
- **Helm release names are validated from v3.4.15** (header) — the first patch in this line that can fail manifest generation for an Application with an invalid `releaseName`.
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
  - **ServerSideDiff Secret leak — the 3.4 floor is v3.4.2, NOT the line's first release.**
    CVE-2026-42880 (critical) was patched before this line shipped, but its fix was incomplete
    and **CVE-2026-45737 lists v3.4.1 as affected**; v3.4.2 (2026-05-12) carries the real fix.
    **There is no v3.4.0 release** (the tag exists, no release was published) — the line starts
    at v3.4.1, so "≥ 3.4.0" is not a usable floor. Per-line floors: **3.4.2 / 3.3.10 / 3.2.12**. The second CVE needs no
    `IncludeMutationWebhook=true` annotation — it fires on `argocd app diff
    --server-side-diff` — so stripping the annotation does not substitute for the patch.

## 3.3 (final release v3.3.19, 2026-11-02 — **EOL 2026-11-03**)

- **EOL — verdict ✗ blocker.** v3.3.19 is the final 3.3 release; its notes carry the end-of-life banner naming v3.4.13 / v3.5.7 / v3.6.0 as the supported destinations. The 2026-11-24 advisories (header) have **no 3.3 fix** — v3.3.19 is the best 3.3 can be and is still exposed. Destination: **3.5 or 3.6** (3.4 is the smaller hop but is the next to expire).
- **Security floor (for a cluster that cannot move yet): v3.3.19** — carries the 2026-10-07 and 2026-11-20 fixes; the 2026-11-24 HIGHs stay open.
- **k8s floor:** 1.32 – 1.35
- **Breaking:**
  - **3.3.0 + 3.3.1 are broken — skip them.** Forced `kubectl-client-side-apply` → SSA field-manager migration regressed many real apps. Workaround was `ClientSideApplyMigration=false` syncOption. **Fixed in 3.3.2** (2026-02-22). Any survey finding a cluster on 3.3.0 / 3.3.1 must verdict ✗ blocker until bumped to ≥ 3.3.2. (Moot for a destination — 3.3 is EOL.)
  - When Argo CD manages itself, the self-managing Application requires `ServerSideApply=true` in `syncOptions` — ApplicationSet CRD exceeds the 262 144-byte client-side-apply annotation limit. Without it the meta-app sync fails on upgrade.
  - **ServerSideDiff Secret leak — floor is v3.3.10, and the old `3.3.8` here was wrong in the
    unsafe direction.** CVE-2026-42880's affected range is `3.2.0 - 3.3.8`, so **3.3.8 is
    affected**, not patched; v3.3.9 carried that fix. That fix was then incomplete and
    CVE-2026-45737 lists **v3.3.9** as affected too, so the floor is **v3.3.10** (2026-05-12).
    Surveyed 3.3.x handling Secrets must be ≥ 3.3.10.
- **CRD migrations:** none.
- **Upgrade ordering:** none against other registry components.
- **Deprecations:** none new this minor.
- **Notable:**
  - **Progressive Sync promoted to Beta** for ApplicationSet (per v3.3.0 docs commit `6cfef6b`).
  - Source Hydrator gained inline parameter support; still Alpha.
  - HPA v2 (`autoscaling/v2`) support added (low signal — `autoscaling/v1` already worked).
  - Server-Side Diff (Stable since v3.2) still **not default** — `IncludeMutationWebhook` opt-in flag is the CVE vector; strip it from every Application.

## 3.2 (final release v3.2.12, 2026-05-13 — line EOL 2026-08-04)

- **k8s floor:** 1.31 – 1.34
- **Breaking:**
  - **EOL 2026-08-04 — verdict ✗ blocker, but for support, not exposure.** v3.2.12 is the final
    3.2 release and its notes carry the end-of-life banner naming v3.3, v3.4 and v3.5 as the
    supported destinations. No further security updates will ship for this line, so the next
    advisory against it has no patch — that, not a present hole, is the reason to move.
  - **Both ServerSideDiff CVEs WERE patched here**, contrary to the retracted note: v3.2.11
    (2026-04-30) for CVE-2026-42880 and **v3.2.12** (2026-05-13) for CVE-2026-45737. A 3.2
    cluster already on **v3.2.12** is not exposed to either and can be scheduled rather than
    treated as an incident — which is the practical difference the wrong note erased.
  - **Destination: 3.5 (or 3.4), not "3.4.x" as a fixed answer.** 3.3 went EOL 2026-11-03
    (3.6 GA), so 3.3 is not a destination. Apply House Rule #9 look-ahead: 3.4 EOLs when 3.7 GAs (~2027-02 by cadence).
  - `syncPolicy.automated.enabled=false` semantics fixed in 3.2.x (`#24254`) — pre-fix builds treated the field as no-op and continued auto-syncing. Pre-3.2 manifests relying on this to disable auto-sync silently break on 3.2 if they used a different toggle.
- **CRD migrations:** none.
- **Upgrade ordering:** none against other registry components.
- **Deprecations:**
  - `extensions/v1beta1` shim removed for built-in health checks (`#381`). Apps still referencing those API versions in `ignoreDifferences` or health Lua scripts will misbehave.
- **Notable:**
  - **Server-Side Diff promoted to Stable.** Not default — apps opt in per-Application via `compare-options: ServerSideDiff=true` annotation or globally via `argocd-cmd-params-cm`.
  - **Server-Side Apply migration** logic landed (`#727`) — auto-migrates `kubectl-client-side-apply` fields when ServerSideApply is enabled. This is the same code that regressed in 3.3.0. **Do NOT treat 3.2 as the "safe LTS" landing zone** — it went EOL 2026-08-04 at v3.2.12 and receives no further security updates. Land on **3.5** or **3.6**; 3.4 is the smaller hop but expires next; 3.3 is EOL (2026-11-03).
  - ApplicationSet PR generator returns 0 results on repo-not-found rather than failing (`#23447`) — silent behavior change; AppSets relying on hard failure to gate sync need a different signal.

## 3.1 (latest: v3.1.16, 2026-05-05 — **EOL 2026-05-06**)

- **k8s floor:** 1.31 – 1.34
- **EOL.** v3.1.16 release notes carry the upstream EOL banner. No more security or bug patches. Verdict ✗ blocker — must bump to a supported minor — **3.5, or 3.4 if a smaller hop is needed**. Do not land on 3.2: it went EOL 2026-08-04 (see § 3.2). Note its EOL date is exactly v3.4.1's GA date, the N+3 rule in the header.
- **Breaking:**
  - **k8s floor jumped from 1.29 (v3.0) to 1.31.** RKE2 / Rancher clusters that ran v3.0 on k8s 1.29 / 1.30 must bump the kube control plane before installing 3.1.
  - **SSA field-manager migration options added** (`#23337`) — opt-in here; defaults flipped in 3.3.0 and immediately regressed. Pre-stage `ClientSideApplyMigration=false` syncOption on apps that already opted in, so the 3.3 upgrade path is reversible.
  - **`spec.preserveUnknownFields` default ignoreDifference removed** (`#22948`) — Applications that relied on that hidden ignore now show drift on CRDs that still carry the field. Drop the field from CRD specs (it's `false` by default in apiextensions/v1 anyway).
  - **CVE-2026-42880 does not affect this minor — do not record a 3.1 floor for it.** The advisory's
    ranges are `>= 3.2.0, < 3.2.11` and `>= 3.3.0, < 3.3.9` only. 3.1 was still supported when it
    published (2026-05-01) and was not listed, and v3.1.15 carries no security banner. The blocker
    on 3.1 is EOL, nothing else.
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
  - **CVE-2026-42880 does not affect this minor either** (see § 3.1). v3.0.22 shipped 2026-01-13,
    three months before the fix releases of 2026-04-30 — a patch cannot predate the fix it claims.
    3.0.x is a blocker on EOL alone.
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

- **Upstream support window.** Argo CD upstream tests three minors (current + 2 prior). At 2026-11-25: 3.6 (latest), 3.5, 3.4. 3.3 (EOL 2026-11-03), 3.2, 3.1 and 3.0 are EOL upstream — verdict ✗ blocker if found.
- **k8s floor stability.** Floor history: 3.0 → 1.29; 3.1 → 1.31 (jumped two); 3.2 → 1.31 (held); 3.3 / 3.4 → 1.32; 3.5 → 1.33; 3.6 → 1.34 (one minor per release again). RKE2 clusters on 1.31 cannot run 3.3+, on 1.32 cannot run 3.5+, on 1.33 cannot run 3.6, per the tested matrix; the ceiling moves too (3.6 tests 1.37). Argo CD 3.2 is fully patched against both ServerSideDiff CVEs at v3.2.12, so this is a **support** problem rather than an exposure one — but the line is EOL as of 2026-08-04, so the move is still **bump RKE2 to ≥ 1.32, then land on a supported minor**, not park on 3.2.x. The distinction changes the urgency, not the destination. RKE2 on 1.29 / 1.30 is stuck on EOL Argo CD (v3.0 only) — k8s bump is mandatory before any supported Argo CD.
- **The seven v3.0 default flips** (annotation tracking, `.status` ignored, default `resource.exclusions`, logs-RBAC enforced, no update/delete RBAC inheritance, `preserveUnknownFields: false` causes drift, in-cluster destination off by default) are still in effect across 3.2–3.6. Any v2.x → v3.x jump in scope must address all seven — defer to `argo-cd-apps` skill `references/version-changes.md` § v3.0.
- **No `ServerSideDiff=true` + `IncludeMutationWebhook=true` combo on unpatched builds.** This is the CVE-2026-42880 trigger. Verdict ✗ blocker if the cluster runs ServerSideDiff and any patched build is not in place.
