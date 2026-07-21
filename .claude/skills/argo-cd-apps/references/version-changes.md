# Argo CD v3.0 → v3.4: Version-change reference for App authors

## Currency note (verified 2026-07-21)

- **Latest stable:** **v3.4.5** (2026-07-09). v3.4 reached GA in early May 2026
  (v3.4.0 on 2026-05-06); v3.4.4 landed 2026-06-18.
- **Maintenance lines:** v3.3.x (latest **v3.3.12**, 2026-06-18), v3.2.x
  (v3.2.12, 2026-05-13), v3.1.x (v3.1.16, 2026-05-05).
- **v3.5 is in release-candidate:** **v3.5.0-rc1** (2026-06-16),
  **v3.5.0-rc2** (2026-07-01). Not GA. See the v3.5 section below — it carries
  a Helm v4 breaking change that needs planning before the hop, not after.
- **Enumerate the release list; don't read `releases/latest`.** GitHub marks
  latest by recency, so a patch on an older line can outrank a newer minor.
  Use `gh release list -R argoproj/argo-cd --limit 25` and reason per line.
- **The repo's `CHANGELOG.md` is stale** — last entry is v2.4.8 (July 2022).
  Canonical changelog is the GitHub release-note set. Use
  `gh release view <tag> --repo argoproj/argo-cd` and the per-version
  `docs/operator-manual/upgrading/<from>-<to>.md` files.
- Local clone at `~/projects/github.com/argoproj/argo-cd/` (last commit
  `4d02fc2f5` on 2026-05-05, branch `main`, `VERSION=3.5.0`) is freshest;
  see "Note on conflicting sources" at the bottom.
- Release timing: v3.0.0 (2025-05-06), v3.1.0 (mid-summer 2025),
  v3.2.0 (2025-11-04), v3.3.0 (2026-02-02), v3.4.0-rc1 (2026-03-16).

For the standard list of "things that bite app authors", see SKILL.md
§ Critical gotchas — this file does not duplicate it.

---

## v3.0 (2025-05-06) — "Small But Mighty" (defaults flip)

The binary changed less than the defaults did. Read
`docs/operator-manual/upgrading/2.14-3.0.md` end-to-end before upgrading.

### Headline features for app authors

- **Annotation-based resource tracking is default**
  ([#20671](https://github.com/argoproj/argo-cd/pull/20671)). Greenfield:
  nothing. Existing apps: next sync rewrites labels to annotations; for
  any `ApplyOutOfSyncOnly=true` apps, **explicitly sync** post-upgrade or
  risk orphans. Opt-out via `application.resourceTrackingMethod: label`.
- **Default `resource.exclusions` ships with install**
  ([#21635](https://github.com/argoproj/argo-cd/pull/21635)): excludes
  `Endpoints`, `EndpointSlice`, `Lease`, `*SubjectAccessReview`,
  `TokenReview`, `CertificateSigningRequest`, `CertificateRequest`,
  Kyverno reports, Cilium endpoints, `PolicyReport`/`ClusterPolicyReport`.
  Override in `argocd-cm` if any are load-bearing.
- **Default `resource.customizations.ignoreResourceUpdates` ships.**
  Status-only churn ignored. If your CR's `.status` *is* desired state,
  set `ignoreDifferencesOnResourceUpdates: false`.
- **Health no longer persisted in Application CR by default**
  ([#21532](https://github.com/argoproj/argo-cd/pull/21532)). Per-resource
  health moves to redis. `argocd app list -o json` no longer returns
  individual resource health — use `argocd app get <name>`. Fix tooling
  scraping `.status.resources[].health` from the CR.
- **Empty-string env vars now reach CMPs**
  ([#22096](https://github.com/argoproj/argo-cd/pull/22096)). Switch
  `[ -n "$VAR" ]` checks to `[ -z "${VAR:-}" ]`.
- **Source Hydrator first-class CRD field handling**
  ([#22485](https://github.com/argoproj/argo-cd/pull/22485)). Hydrator
  still **Alpha**.
- **OCI source — Alpha** (promoted in 3.1).
- **Sync-window `AND` operator for matches**
  ([#16846](https://github.com/argoproj/argo-cd/pull/16846)) — opt-in.
- **Build-env `ARGOCD_APP_PROJECT_NAME`**
  ([#21586](https://github.com/argoproj/argo-cd/pull/21586)).
- **`argocd-source.yaml` Kustomize "ignore missing components"**
  ([#21674](https://github.com/argoproj/argo-cd/pull/21674)).
- **Bundled:** Helm 3.17.1, Kustomize 5.6.x, kubectl 1.32.1.

### Breaking changes / deprecations

- **Fine-grained RBAC no longer inherits to sub-resources**
  ([#20671](https://github.com/argoproj/argo-cd/pull/20671)). `update` /
  `delete` on Application no longer auto-grant `update/*` / `delete/*`
  on managed resources. Add explicit policies, or set
  `server.rbac.disableApplicationFineGrainedRBACInheritance: false`.
- **Logs RBAC enforced; `server.rbac.log.enforce.enable` removed**
  ([#21678](https://github.com/argoproj/argo-cd/pull/21678)). Add
  `logs, get` to roles needing pod-log access.
- **Legacy `argocd-cm` repo config removed.** Repos must be Secrets.
- **ApplicationSet `spec.applyNestedSelectors` ignored** — nested
  selectors always apply. Strip the field.
- **Dex SSO subject changes from `sub` → `federated_claims.user_id`**
  ([#21726](https://github.com/argoproj/argo-cd/pull/21726)). Update
  `policy.csv`.
- **`spec.preserveUnknownFields: false` on CRD now causes drift** —
  drop the field or add an `ignoreDifferences` for it.
- **`resource.compareoptions` defaults flipped**
  ([#22230](https://github.com/argoproj/argo-cd/pull/22230)):
  `ignoreResourceStatusField` `crd` → `all`;
  `ignoreDifferencesOnResourceUpdates` now `true`.
- **Removed metrics:** `argocd_app_sync_status`, `argocd_app_health_status`,
  `argocd_app_created_time`. Use labels on `argocd_app_info`.
- **`cluster.inClusterEnabled: "false"` now hard-blocks new in-cluster apps.**
- **Sanitised project API response**
  ([GHSA-786q-9hcg-v9ff](https://github.com/argoproj/argo-cd/security/advisories/GHSA-786q-9hcg-v9ff))
  — drops project-scoped repo / cluster credentials.
- **Helm 3.17.1 `null` semantics changed.** `null` in `values.yaml` now
  overrides upstream non-table values. Strip stray `null:` from subcharts.

### Maturity changes

- **Source Hydrator** — Alpha (introduced v2.14, documented in 3.0).
- **Service Account Impersonation** — still Beta.
- **AppSet Progressive Syncs** — still Beta (formal Beta in 3.3).

---

## v3.1 (mid-summer 2025) — polish

Read `docs/operator-manual/upgrading/3.0-3.1.md`.

### Headline features for app authors

- **Parameterised resource actions**
  ([#20097](https://github.com/argoproj/argo-cd/pull/20097)). Custom
  actions take typed parameters; Lua actions get a `params` table. Ship
  "scale to N" instead of fixed pairs.
- **OCI source — Beta** ([#18646](https://github.com/argoproj/argo-cd/pull/18646)).
  `repoURL: oci://...` for Helm OCI charts and arbitrary manifest bundles
  (`argocd repo add --type oci`). Point Apps at GHCR/ECR/GAR for both.
- **CLI plugin support** ([#20074](https://github.com/argoproj/argo-cd/pull/20074),
  [#23385](https://github.com/argoproj/argo-cd/pull/23385) `argocd whoami`).
  `argocd <plugin>` dispatches to `argocd-<plugin>` on `$PATH`.
- **Progressive Syncs UI** ([#22781](https://github.com/argoproj/argo-cd/pull/22781)).
- **App-level `SkipDryRunOnMissingResource`**
  ([#22679](https://github.com/argoproj/argo-cd/pull/22679)) — set on
  the Application directly, not just AppProject.
- **`syncPolicy.automated.enabled`**
  ([#21999](https://github.com/argoproj/argo-cd/pull/21999),
  [#22440](https://github.com/argoproj/argo-cd/pull/22440)) — toggle
  auto-sync without removing the `automated:` block.
- **SSA field-manager migration controls**
  ([#23337](https://github.com/argoproj/argo-cd/pull/23337)).
- **Bitbucket Cloud PR generator: `targetBranch` filter**
  ([#22402](https://github.com/argoproj/argo-cd/pull/22402)).
- **Git File generator: file-exclude support**
  ([#22734](https://github.com/argoproj/argo-cd/pull/22734)).
- **AppSet Git generators: `repository_id`**
  ([#22416](https://github.com/argoproj/argo-cd/pull/22416)).
- **Gitea PR-generator: PR label filtering**
  ([#21148](https://github.com/argoproj/argo-cd/pull/21148)).
- **Numaplane force-promote action**
  ([#22141](https://github.com/argoproj/argo-cd/pull/22141)).
- **PR/SCM generator 401 handling without `tokenRef`**
  ([#22744](https://github.com/argoproj/argo-cd/pull/22744)).
- **Bundled:** Kustomize 5.7.0, Helm 3.18.4.
- **Health checks added:** SpinKube `SpinApp`, OpenTelemetryCollector,
  Logstash, Kyverno `Policy`, projectcontour `HTTPProxy`, Grafana CRDs,
  CloudNativePG `Cluster`, Gateway API
  (`Gateway`, `HTTPRoute`, `GRPCRoute`), RabbitMQ topology CRDs.

### Breaking changes / deprecations

- **`/api/v1/applications/{name}/resource/actions` deprecated** — use
  `/resource/actions/v2`. Parameters move from query string to JSON POST
  body, plus `resourceActionParameters`.
- **OIDC PKCE flow now server-side, not UI.** Add
  `https://<argocd>/auth/callback` to your IdP's redirect URIs.
- **API `--staticassets` blocks symlinks pointing outside the directory**
  ([#22936](https://github.com/argoproj/argo-cd/pull/22936)).

### Maturity changes

- **OCI source: Alpha → Beta** ([#18646](https://github.com/argoproj/argo-cd/pull/18646)).
- **Proxy Extensions: → Beta** ([#22361](https://github.com/argoproj/argo-cd/pull/22361)).

---

## v3.2 (2025-11-04) — ApplicationSet sharpening + multi-source overrides

Read `docs/operator-manual/upgrading/3.1-3.2.md`.

### Headline features for app authors

- **Server-Side Diff CLI** ([#23978](https://github.com/argoproj/argo-cd/pull/23978)).
  `argocd app diff --server-side-diff` works via CLI. Re-enable SSD if
  you'd disabled it for CLI gaps.
- **`get-resource` CLI** ([#23609](https://github.com/argoproj/argo-cd/pull/23609)).
  `argocd app get-resource <app> --kind X --name Y` — live cluster state
  without `kubectl` access.
- **Newer revision permitted on retry of failed sync**
  ([#23038](https://github.com/argoproj/argo-cd/pull/23038)). Auto-sync
  no longer pins to the failed commit.
- **CronJob health checks** ([#23991](https://github.com/argoproj/argo-cd/pull/23991))
  — see breaking change.
- **Hydrator: commit-message templating, credential templating, parallel
  repo-server calls, `.gitattributes` injection** —
  [#24204](https://github.com/argoproj/argo-cd/pull/24204),
  [#23999](https://github.com/argoproj/argo-cd/pull/23999),
  [#23725](https://github.com/argoproj/argo-cd/pull/23725),
  [#24451](https://github.com/argoproj/argo-cd/pull/24451).
- **PR generator: title-matching filter**
  ([#23569](https://github.com/argoproj/argo-cd/pull/23569)).
- **Authenticated `userId` header to UI extensions**
  ([#24356](https://github.com/argoproj/argo-cd/pull/24356)).
- **OTel trace context propagation for HTTP**
  ([#23029](https://github.com/argoproj/argo-cd/pull/23029)).
- **AppSet PR generator returns 0 on repo-not-found instead of failing**
  ([#23447](https://github.com/argoproj/argo-cd/pull/23447)). If you
  used PR-generator failure as a "did the repo move?" canary, switch to
  an explicit ListEntries-equivalent check.
- **Preserve non-hydrated files during hydration**
  ([#24129](https://github.com/argoproj/argo-cd/pull/24129)). Pairs with
  the 3.3 "no automatic path cleaning" change.
- **Read argocd password from stdin**
  ([#23520](https://github.com/argoproj/argo-cd/pull/23520)) for CI.
- **Health checks added:** GitOps Promoter
  (`ArgoCDCommitStatus`, `ChangeTransferPolicy`, `CommitStatus`,
  `PromotionStrategy`, `PullRequest`), Coralogix `Alert` /
  `RecordingRuleGroupSet`, projectcontour `ExtensionService`,
  ClickHouse / ClickHouseKeeper, 16 3scale CRDs
  ([#24326](https://github.com/argoproj/argo-cd/pull/24326)),
  CronJob, DatadogMetric.

### Breaking changes / deprecations

- **Hydrator paths must be non-root.** `path: ""` / `path: "."` rejected.
  Old hydrators wiped repo-root files; v3.2 rejects this. **Manually
  clean stale root-level `manifest.yaml` from earlier versions.**
- **`kustomizeOptions.binaryPath` deprecated in repo-server gRPC.**
  Use `kustomizeOptions.versions`.
- **CronJob health may flip Apps to `Degraded`.**
  - Last run failed → App `Degraded`.
  - Active job present → App jumps Healthy→Degraded→Healthy each cycle
    (CronJob status doesn't separate "last completed" from "current").
  - Suspended CronJobs `Healthy` by default; override via
    `resource.customizations.health.batch_CronJob`.
  - Annotate noisy ones with
    `argocd.argoproj.io/ignore-healthcheck: "true"`.
- **`.argocd-source.yaml` now respects `kustomize.version`.** Per-env
  override can pin Kustomize. **Audit** files that *accidentally* set
  this — they now actually take effect.
- **ApplicationSet `status.resources` capped at 5000 entries by default**
  ([#24711](https://github.com/argoproj/argo-cd/pull/24711)). Override
  via `applicationsetcontroller.status.max.resources.count`.
- **3.2.0 has repo-server lock contention on monorepos** — fixed in
  3.2.1+ ([#25127](https://github.com/argoproj/argo-cd/pull/25127)).
  Don't run 3.2.0 on monorepos.

### Maturity changes

- **Server-Side Diff: Beta → Stable / GA**
  ([#24138](https://github.com/argoproj/argo-cd/pull/24138)). Default to
  `controller.diff.server.side: "true"`.
- **OCI source remains Beta** through 3.2.

---

## v3.3 (2026-02-02) — lifecycle hooks + RBAC granularity

Read `docs/operator-manual/upgrading/3.2-3.3.md` carefully — SSA
migration is non-trivial.

### Headline features for app authors

- **PreDelete hooks** ([#22288](https://github.com/argoproj/argo-cd/pull/22288)).
  Completes lifecycle: PreSync / Sync / PostSync / SyncFail / **PreDelete**.
  Annotate Job with `argocd.argoproj.io/hook: PreDelete`. Migrate
  deletion-side finalisers from external operators / manual `kubectl
  delete` rituals into PreDelete Jobs.
- **`Prune` and `Delete` as application-level sync options**
  ([#23370](https://github.com/argoproj/argo-cd/pull/23370)):
  ```yaml
  spec:
    syncPolicy:
      syncOptions:
        - Prune=false
        - PruneLast=true
        - Delete=false
  ```
- **Resources pruned in reverse sync-wave order** (gitops-engine
  [#538](https://github.com/argoproj/gitops-engine/pull/538)). Wave 0
  syncs first, prunes last. Audit forward-only ordering tunings.
- **Prune / Delete `=confirm` deletion protection** (gitops-engine
  [#630](https://github.com/argoproj/gitops-engine/pull/630)).
  `argocd.argoproj.io/sync-options: Prune=confirm` (or `Delete=confirm`)
  requires explicit UI / CLI confirmation.
- **Cluster-resource RBAC narrowed by name**
  ([#24674](https://github.com/argoproj/argo-cd/pull/24674)).
  `clusterResourceWhitelist` can restrict by `name:`. Scope to specific
  CRD instead of blanket `apiextensions.k8s.io/CustomResourceDefinition`.
- **OIDC background token refresh**
  ([#23727](https://github.com/argoproj/argo-cd/pull/23727)). New
  `refreshTokenThreshold` configurable.
- **Inline parameters in Source Hydrator**
  ([#24277](https://github.com/argoproj/argo-cd/pull/24277)).
- **Hydrator: don't push commits if manifests don't change**
  ([#25056](https://github.com/argoproj/argo-cd/pull/25056)) — see
  breaking change for git-notes flip.
- **Shallow clone option for repositories**
  ([#24931](https://github.com/argoproj/argo-cd/pull/24931)). Per-repo
  `shallow: true`. Big speedup on monorepos.
- **Auto-migration of `kubectl-client-side-apply` field manager → SSA**
  (gitops-engine [#727](https://github.com/argoproj/gitops-engine/pull/727)).
- **Cross-namespace hierarchy traversal cluster-scoped → namespaced
  children** ([#24847](https://github.com/argoproj/argo-cd/pull/24847)).
  Fixes `argocd app resources` truncation when an operator creates child
  Deployments in a different namespace.
- **Custom labels on `CreateNamespace` SyncOption namespaces**
  (gitops-engine [#443](https://github.com/argoproj/gitops-engine/pull/443)).
- **HPA v2 (`autoscaling/v2`) support** (gitops-engine
  [#411](https://github.com/argoproj/gitops-engine/pull/411)).
- **Sync to a different revision now requires `override` privilege**
  ([#22858](https://github.com/argoproj/argo-cd/pull/22858)). Roles with
  `sync` on Applications also need `override` on the project.
- **KEDA: pause action for `ScaledObject` / `ScaledJob`**
  ([#25301](https://github.com/argoproj/argo-cd/pull/25301)) and
  `ScaledJob` health ([#25106](https://github.com/argoproj/argo-cd/pull/25106)).
- **PullRequest merge action**
  ([#24823](https://github.com/argoproj/argo-cd/pull/24823)) for GitOps
  Promoter.
- **`ApplyOutOfSyncOnly=true` honoured for cluster-scoped resources**
  (gitops-engine [#765](https://github.com/argoproj/gitops-engine/pull/765))
  — was silently broken.
- **Bundled:** Helm 3.19.2, Kustomize 5.8.0. Helm 2.x unsupported.
- **Health checks added:** Ceph CRDs, ObjectBucketClaim, KEDA `ScaledJob`,
  SAP `ServiceBinding`/`ServiceInstance`, GCP Config Connector,
  grafana-org-operator.

### Breaking changes / deprecations

- **ApplicationSet CRD now exceeds 262 144-byte client-side-apply
  annotation limit.** Upgrade with `kubectl apply --server-side
  --force-conflicts` (or set `ServerSideApply=true` syncOption on the
  meta-Application). 3.3.0 / 3.3.1 had a regression needing
  `ClientSideApplyMigration=false` — fixed in 3.3.2. **Use 3.3.2+, not
  3.3.0.**
- **Source Hydrator state moves from "commit per DRY commit" to git-notes**
  ([#25056](https://github.com/argoproj/argo-cd/pull/25056)). The
  `hydrator.metadata.drySha` field is replaced by a git note. Any "any
  new hydrated commit" trigger should switch to watching the git-notes
  namespace, or watch only commits that mutate `manifest.yaml`. Far
  fewer hydrated commits will exist.
- **Hydrator no longer cleans the application path before writing.**
  Previously it deleted everything in path then re-wrote; now writes
  only files it owns. Clean stale files once, by hand. Long-term: keep
  output in a dedicated subdirectory.
- **`ARGOCD_K8S_SERVER_SIDE_TIMEOUT` splits from `ARGOCD_K8S_TCP_TIMEOUT`.**
- **`--self-heal-backoff-cooldown-seconds` flag deprecated** on the
  application-controller.
- **Anonymous Settings API call no longer returns `resourceOverrides`.**
- **Helm 2.x dropped** — won't work even via `helm.binaryPath`.

### Maturity changes

- **AppSet Progressive Syncs: → Beta (formal)**
  ([#25122](https://github.com/argoproj/argo-cd/pull/25122)). Still gated
  by `applicationsetcontroller.enable.progressive.syncs: "true"`.
- **OCI source: still Beta** (no formal GA).
- **Source Hydrator: still Alpha**.
- **Service Account Impersonation: still Beta** (formal Beta in 3.4).

---

## v3.4 (GA — v3.4.0 2026-05-06, latest v3.4.3 2026-05-28) — defaults sharpening + impersonation extension

Read `docs/operator-manual/upgrading/3.3-3.4.md` and `3.4-3.5.md`.

### Headline features for app authors

- **Cluster-version format: `vMajor.Minor.Patch`** (was `Major.Minor`),
  backported to 3.3.3. If your AppSet Cluster generator filters on
  `argocd.argoproj.io/auto-label-cluster-info` for k8s version, switch
  to `argocd.argoproj.io/kubernetes-version` and `vMajor.Minor.Patch`.
  CMP env var `$KUBE_VERSION` is unchanged (still `Major.Minor.Patch`
  without the `v`).
- **AppSet UI: Watch API + status integration**
  ([#26409](https://github.com/argoproj/argo-cd/pull/26409),
  [#26490](https://github.com/argoproj/argo-cd/pull/26490),
  [#25753](https://github.com/argoproj/argo-cd/pull/25753),
  [#25837](https://github.com/argoproj/argo-cd/pull/25837),
  [#26262](https://github.com/argoproj/argo-cd/pull/26262)).
  ApplicationSets get a real list view, slide-out summary, tree view,
  filter chips. Stop managing AppSets via CLI only.
- **AppSet `Health` field in status**
  ([#25753](https://github.com/argoproj/argo-cd/pull/25753)).
- **Annotation to pause reconciliation for a specific cluster**
  ([#26442](https://github.com/argoproj/argo-cd/pull/26442)). Set
  `argocd.argoproj.io/pause-reconcile: "true"` on a cluster Secret.
- **Configurable hydrator commit Author Name / Email**
  ([#25746](https://github.com/argoproj/argo-cd/pull/25746)).
- **GitHub App auth without `installationId`**
  ([#25374](https://github.com/argoproj/argo-cd/pull/25374)).
- **Annotation filtering on Applications-list UI**
  ([#25590](https://github.com/argoproj/argo-cd/pull/25590)).
- **Custom UI icons** ([#20864](https://github.com/argoproj/argo-cd/pull/20864)).
- **Prune / Delete UI confirm flows.**
- **AppSet listResourceEvents API**
  ([#25537](https://github.com/argoproj/argo-cd/pull/25537)).
- **`automated.enabled: false` actually disables auto-sync now**
  ([#26763](https://github.com/argoproj/argo-cd/pull/26763)) — fixes a
  3.1-introduced leak.
- **`refresh paths from drySource` for hydration-enabled apps**
  ([#25516](https://github.com/argoproj/argo-cd/pull/25516)).
- **Health checks added:** nmstate `NodeNetworkConfigurationPolicy`
  ([#26507](https://github.com/argoproj/argo-cd/pull/26507)).
- **OCI metrics** ([#25493](https://github.com/argoproj/argo-cd/pull/25493)).
- **Bundled:** Dex 2.45.0 (`ContinueOnConnectorFailure` on by default;
  disable via `dexserver.connector.failure.continue: "false"`).

### Breaking changes / deprecations

- **Application "Missing" health is now reserved for "all resources missing"**
  (e.g. before first sync). Previously a single missing resource could
  mark the App `Missing` (inconsistently). Individual missing resources
  now reflect via `OutOfSync`. Change automation that detects "some
  resources got deleted by mistake" via `health.status == Missing` to
  poll `sync.status == OutOfSync` + per-resource health introspection.
- **Cluster version format flip to `vMajor.Minor.Patch`** — see Headline.
  Cluster generators with hard-coded `1.32` style filters need updating
  to `v1.32.X` semver matching.
- **`go-oidc` v3.17.0** reorders verification to `signature → claims`.
  A token both *expired* and *signed by a rotated-out JWKS key* now
  redirects to login (manual SSO restart). Mitigated by IdPs publishing
  previous keys for grace period > token lifetime.
- **OpenTelemetry SDK upgrade** to 1.42.0 with semantic conventions
  v1.40.0 — audit OTEL dashboards.

### Maturity changes

- **Service Account Impersonation: → Beta (formal)**
  ([#27576](https://github.com/argoproj/argo-cd/pull/27576), doc commit
  `3c233ccda` 2026-05-01). The `app-sync-using-impersonation.md`
  "experimental" warning is gone. Adopt
  `spec.destinationServiceAccounts` without expecting schema breakage in 3.5.
- **ApplicationSet in any namespace: Beta → Stable**
  ([#27353](https://github.com/argoproj/argo-cd/pull/27353), doc commit
  `04fa70c4a` 2026-04-16). Multi-tenant deployments where each tenant
  owns their AppSet namespace are first-class.
- **Source Hydrator: still Alpha**. Schema can still break in 3.5.
- **Impersonation extends to server operations** (logs, delete, list
  events, exec custom resource actions) per
  [#26898](https://github.com/argoproj/argo-cd/pull/26898) merged
  2026-04-02 (well before 3.4-rc1 → likely in 3.4 itself, despite
  `3.4-3.5.md` placement). If you enable impersonation, the
  `destinationServiceAccounts` SA needs `get`/`list` on `pods`,
  `pods/log`, `events`, plus `delete`/`patch`/`create` for UI actions.
  Missing perms = 403, not silent fallbacks.

---

## v3.5 (RC as of 2026-07-21 — rc1 2026-06-16, rc2 2026-07-01) — Helm v4, React 19

**Not GA.** Sourced from `docs/operator-manual/upgrading/3.4-3.5.md` read at tag
**v3.5.0-rc2** — a real release artifact, not `main`. Content can still change
before GA; re-read the doc at the GA tag.

### Breaking: Helm upgraded to 4.2.0 — plain-HTTP OCI registries need explicit flags

The single change most likely to break an existing install, and it bites
on-prem / air-gapped setups hardest because those are where plain-HTTP OCI
registries live. Helm v4's OCI implementation requires `--plain-http` explicitly
when the registry doesn't speak TLS.

1. **Existing plain-HTTP OCI repos** need the flag:
   `argocd repo add ... --insecure-oci-force-http --upsert` (CLI 3.5), or in the
   Secret:
   ```yaml
   stringData:
     insecureOCIForceHttp: "true"
   ```
2. **OCI *dependency* repos must now be registered explicitly.** If a chart has
   `dependencies:` with `repository: oci://...` on a plain-HTTP registry, that
   dependency repo must be added to Argo CD with the same flag. **Under Helm v3
   this worked transparently with no registration at all** — so a chart that has
   been building for years can start failing with nothing in the app changed.
3. **Known limitation with no workaround.** Setting *both*
   `--insecure-skip-server-verification` (→ Helm `--insecure-skip-tls-verify`)
   and `--insecure-oci-force-http` (→ Helm `--plain-http`) makes Helm v4
   **silently drop `--plain-http`** — TLS-skip takes internal precedence. The
   failure is `http: server gave HTTP response to HTTPS client`. Affects
   `type=helm` repos with `--enable-oci`, and `type=oci` + `type=helm`
   dependency chains. Upstream states there is no workaround when both are
   legitimately needed in the same chain.
4. **`spec.source.helm.version: v3` is now ignored** — Argo CD renders with
   Helm v4 only. The field can be left in place; it just does nothing.

See the `helm` skill for Helm 4 chart-authoring implications.

### Breaking: UI extensions must externalize `react/jsx-runtime`

The UI moved React 16 → 19. Extensions built against an older Argo CD UI fail
to load with `Extension <name>.js failed to load: TypeError: Cannot read
properties of undefined (reading '<prop>')`. Remediation guide:
`docs/operator-manual/upgrading/ui-extensions-react-19-upgrading.md`. No action
if you install no UI extensions.

### Breaking: event-listing gRPC methods return an Argo CD `EventList`

`ListResourceEvents` (Application, ApplicationSet) and `ProjectService/ListEvents`
change response type from `k8s.io.api.core.v1.EventList` to an Argo CD-defined
type. **gRPC clients must be regenerated alongside the 3.5 server** — grpc-web
is *not* a compatibility shim. The **argocd CLI is not affected** (it doesn't
use these APIs), and **REST paths and JSON bodies are unchanged**, so the UI and
REST integrations are fine. Generated OpenAPI clients see a schema-level break
(`eventsEventList` replaces `io.k8s.api.core.v1.EventList`).

### Behavioural: impersonation extends to all server operations

Previously sync-only. Now every API-server operation uses the impersonated
service account from `destinationServiceAccounts` — so those accounts need
broader RBAC than before:

| Operation | Required verbs |
|---|---|
| Get resource | `get` |
| Patch resource | `get`, `patch` |
| Delete resource | `delete` |
| List resource events | `list` on `events` (core/v1) |
| View pod logs | `get` on `pods` and `pods/log` |
| Run resource action | `get`, `create`, `patch` |

Custom resource actions may need more. No action if impersonation is off.

### Behavioural: SSH `known_hosts` now sourced from the ConfigMap for credential-less repos

`go-git` moved to v5.19.x, which tightens host-key verification. Argo CD now
builds SSH auth itself for repos **without** configured credentials and wires
the host-key callback to `argocd-ssh-known-hosts-cm` — previously go-git's
default builder read `~/.ssh/known_hosts` inside the repo-server container.
**If a custom repo-server image baked in or mounted a `~/.ssh/known_hosts`, move
those keys into `argocd-ssh-known-hosts-cm`** or expect
`knownhosts: key mismatch`. No action for HTTPS repos or SSH repos that do have
credentials configured.

---

## Cross-cutting maturity table (May 2026, post-3.3 / pre-3.4-GA)

Authoritative source: `docs/operator-manual/feature-maturity.md` plus
git-history promotion commits.

| Feature | Status (3.0) | Status (3.4) | Triggered by |
|---|---|---|---|
| AppSet Progressive Syncs | Beta (informal) | Beta (formal, since 3.3) | [#25122](https://github.com/argoproj/argo-cd/pull/25122) |
| Proxy Extensions | Alpha | Beta (since 3.1) | [#22361](https://github.com/argoproj/argo-cd/pull/22361) |
| Skip Application Reconcile | Alpha | Alpha | unchanged |
| Cluster Sharding (round-robin) | Alpha | Alpha | unchanged |
| Dynamic Cluster Distribution | Alpha | Alpha | unchanged |
| Cluster Sharding (consistent-hashing) | Alpha | Alpha | unchanged |
| Service Account Impersonation | Beta (informal since 2.13) | Beta (formal in 3.4) | [#27576](https://github.com/argoproj/argo-cd/pull/27576) |
| Source Hydrator | Alpha | Alpha | unchanged |
| Server-Side Diff | Beta | **Stable** (3.2) | [#24138](https://github.com/argoproj/argo-cd/pull/24138) |
| OCI source | Alpha | Beta (since 3.1) | [#18646](https://github.com/argoproj/argo-cd/pull/18646) |
| ApplicationSet in any namespace | Beta | **Stable** (3.4) | [#27353](https://github.com/argoproj/argo-cd/pull/27353) |
| AppSet generators (List, Cluster, Git, Matrix, Merge, SCM Provider, Pull Request, Plugin) | Stable | Stable | n/a |
| Multi-source Applications | Stable (since 2.6) | Stable | n/a |
| App-in-any-namespace | Stable | Stable | n/a |

No feature was demoted in 3.0 → 3.4.

---

## CVE callouts (app-author-relevant)

- **CVE-2026-42880** (critical, advisory published 2026-05-01). `ServerSideDiff`
  combined with `IncludeMutationWebhook=true` leaks Secrets in the rendered diff.
  **Patched in v3.3.9 / v3.2.11** (GHSA-3v3m-wc6v-x4x3). Upgrade before enabling
  SSD with mutation-webhook inclusion.
- **CVE-2026-45737** (medium, advisory published 2026-05-13,
  GHSA-rg3g-4rw9-gqrp). Further `ServerSideDiff` Kubernetes-Secret extraction
  via sensitive annotations — same exposure class as CVE-2026-42880. Confirm
  the running build post-dates the 2026-05-13 batch before relying on SSD
  near Secret-bearing resources.
- **CVE-2026-45738** (high, advisory published 2026-05-13,
  GHSA-h98r-wv3h-fr38). Stored XSS via application link annotations
  (the `info[].value` / link annotations rendered in the UI) enables a
  developer who can edit Application annotations to escalate to admin.
  Treat user-settable Application annotations as an untrusted UI-injection
  surface; upgrade past the 2026-05-13 batch.
- **CVE-2025-55190** (critical, Sept 2025). Project API tokens leak
  repo credentials. Sanitised project API response is the fix
  ([GHSA-786q-9hcg-v9ff](https://github.com/argoproj/argo-cd/security/advisories/GHSA-786q-9hcg-v9ff)).
- **CVE-2024-31990** (apps-in-any-namespace boundary bypass). Pre-3.0
  boundary checks could be bypassed via crafted Application names.
  Fixed via project-namespace allowlist tightening.

Supply-chain context (operator-side, mention in audits):

- **CVE-2024-31989** — redis weak crypto in older Argo CD bundles.
- **CVE-2022-24904 / CVE-2023-40026 / CVE-2022-31036** — repo-server
  path traversal class. Fixed in 2.x; relevant only for ancient installs.

---

## Things to drop now (May 2026)

Idiomatic in 2.x or early 3.x, but obsolete or actively bad in 3.4.

1. **Label-based resource tracking.** Don't set
   `application.resourceTrackingMethod: label` on fresh installs.
   Migrate old installs by performing one explicit sync per app post-3.0.
2. **Repos in `argocd-cm` ConfigMap.** Removed in 3.0 — must be Secrets:
   `kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=repository`.
3. **Relying on `update` / `delete` RBAC inheriting to managed resources.**
   3.0 disabled by default. Add explicit `update/*` / `delete/*` policies.
4. **Old `/resource/actions` endpoint.** Migrate to
   `/resource/actions/v2`. CLI 3.1+ does it automatically.
5. **Hydrator path = repo root (`""` / `"."`).** Rejected in 3.2.
6. **Custom CronJob health overrides assuming CronJobs always show
   Healthy.** 3.2's health is more accurate but chatty; accept defaults,
   set `argocd.argoproj.io/ignore-healthcheck: "true"`, or override via
   `resource.customizations.health`.
7. **`spec.preserveUnknownFields: false` on CRDs.** Drop the field —
   deprecated in CRD v1 in favour of
   `x-kubernetes-preserve-unknown-fields: true` on schemas.
8. **Manually constructing tracking *labels***. Use the **annotation**
   `argocd.argoproj.io/tracking-id: <app>:<group>/<kind>:<ns>/<name>`.
   Still officially unsupported — prefer GitOps.
9. **`server.rbac.log.enforce.enable` config key.** Removed in 3.0.
   Grant `logs, get` explicitly. Remove the stale key.
10. **Helm 2.x in any form.** 3.3 dropped support entirely.
11. **`kustomizeOptions.binaryPath` in repo-server gRPC clients.** 3.2
    deprecated; use `kustomizeOptions.versions`.
12. **Polling for hydrated commits as deploy trigger.** 3.3 skips
    commits when manifests don't change. Watch the git-notes namespace
    or `manifest.yaml` content changes.
13. **Hydrator paths mixing README / CI files with output.** 3.3 stopped
    auto-clean. Output in a dedicated subdirectory; siblings for docs/CI.
14. **Querying `.status.resources[].health` from the Application CR.**
    3.0 moved per-resource health to redis. Use `argocd app get` / API.
15. **`argocd app list -o json | jq '.[].status.resources[].health'`.**
    Field isn't populated by the list API in 3.0+.
16. **Cluster generator filtering on `Major.Minor` cluster version.**
    3.4 flips to `vMajor.Minor.Patch`. Use
    `argocd.argoproj.io/kubernetes-version` and semver matching.
17. **Depending on `Missing` health for "deleted out-of-band" detection.**
    3.4 reserves `Missing` for "all resources missing". Switch to
    `sync.status == OutOfSync` + per-resource health introspection.
18. **AppSet `applyNestedSelectors: false`.** 3.0 ignores the field —
    no-op now.
19. **Argo CD 3.3.0 / 3.3.1.** SSA-migration regression. Skip to 3.3.2+.
20. **Argo CD 3.2.0 on monorepos.** Repo-server lock contention bug
    ([#25127](https://github.com/argoproj/argo-cd/pull/25127)); use 3.2.1+.
21. **`--self-heal-backoff-cooldown-seconds` controller flag.**
    Deprecated in 3.3, will be removed.
22. **Old PKCE redirect URI (`/pkce/verify` or UI-side callback).** 3.1
    moved PKCE to the server; update IdP redirect URIs to include
    `/auth/callback`.

---

## Quick reference: PRs you'll cite most often

For pasting into team docs:

- `feat: oci support (Beta)` — Argo CD [#18646](https://github.com/argoproj/argo-cd/pull/18646), v3.1.
- `feat!: disable fine-grained inheritance by default` — [#19988 / #20671](https://github.com/argoproj/argo-cd/pull/20671), v3.0.
- `feat!: Logs rbac enforce by default` — [#21678](https://github.com/argoproj/argo-cd/pull/21678), v3.0.
- `feat(config)!: exclude known interim resources by default` — [#20013 / #21635](https://github.com/argoproj/argo-cd/pull/21635), v3.0.
- `feat!: update compareoptions default values` — [#22230](https://github.com/argoproj/argo-cd/pull/22230), v3.0.
- `feat: PreDelete hooks support` — [#22288](https://github.com/argoproj/argo-cd/pull/22288), v3.3.
- `feat: add Prune and Delete as application level sync option` — [#23370](https://github.com/argoproj/argo-cd/pull/23370), v3.3.
- `feat: allow limiting clusterResourceWhitelist by resource name` — [#24674](https://github.com/argoproj/argo-cd/pull/24674), v3.3.
- `feat: application resource deletion protection` — gitops-engine [#630](https://github.com/argoproj/gitops-engine/pull/630), v3.3.
- `feat: Implement Server-Side Diffs` — gitops-engine [#522](https://github.com/argoproj/gitops-engine/pull/522), v3.3 (via gitops-engine merge).
- `feat: parametrized actions to scale workloads` — [#20097](https://github.com/argoproj/argo-cd/pull/20097), v3.1.
- `feat: Enable SkipDryRunOnMissingResource sync option on Application level` — [#22679](https://github.com/argoproj/argo-cd/pull/22679), v3.1.
- `feat: add enable field for automatedSync` — [#21999](https://github.com/argoproj/argo-cd/pull/21999), v3.1.
- `feat: add ability to use shallow clone for repositories` — [#24931](https://github.com/argoproj/argo-cd/pull/24931), v3.3.
- `feat: use impersonation for server operations` — [#26898](https://github.com/argoproj/argo-cd/pull/26898), v3.4.
- `feat: ApplicationSet watch API` — [#26409](https://github.com/argoproj/argo-cd/pull/26409), v3.4.
- `feat(hydrator): don't push commits if manifests don't change` — [#25056](https://github.com/argoproj/argo-cd/pull/25056), v3.3.
- `docs: Promote ApplicationSet in any namespace to stable` — [#27353](https://github.com/argoproj/argo-cd/pull/27353), v3.4.
- `docs(impersonation): promote feature to beta` — [#27576](https://github.com/argoproj/argo-cd/pull/27576), v3.4.
- `docs: promote ApplicationSet's Progressive Sync to beta` — [#25122](https://github.com/argoproj/argo-cd/pull/25122), v3.3.
- `docs: promote server-side diff stable` — [#24138](https://github.com/argoproj/argo-cd/pull/24138), v3.2.

---

## Note on conflicting sources

- ~~The **`3.4-3.5.md` upgrade doc** says impersonation extends to server
  operations *between* 3.4 and 3.5 … Treat as 3.4 unless GA notes say
  otherwise.~~ **RESOLVED 2026-07-21 — it is a 3.5 change.** Checked both
  shipped docs rather than inferring from PR dates: `3.3-3.4.md` at tag
  **v3.4.5** does not mention impersonation *at all*, while `3.4-3.5.md` at
  **v3.5.0-rc2** documents it with a full RBAC-verb table. The GA notes did
  "say otherwise" by staying silent. Note also the prior arithmetic was off —
  PR #26898 landed 2026-04-02, which is *after* v3.4.0-rc1 (2026-03-16), not
  four weeks before it.
- **`feature-maturity.md` lists Source Hydrator as Alpha.** Despite
  heavy 3.2/3.3/3.4 feature work, no Beta promotion. Plan as Alpha.
- **`CHANGELOG.md` in the repo root is stale** (last entry v2.4.8, July
  2022). Use release notes via `gh release view` and per-version
  upgrade docs.
- `argo-cd.readthedocs.io` may lag the local clone by hours-to-days.
  The local clone (last commit 2026-05-05) is the freshest source for
  v3.4 details. When `master`-branch docs disagree with v3.3.9 release
  docs, default to the local clone unless you're explicitly on stable.
