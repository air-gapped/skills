---
name: argo-cd-apps
description: >-
  Author and maintain Argo CD `Application` and `ApplicationSet` manifests as a
  GitOps consumer (publisher), targeting Argo CD v3.4 / v3.5 (Sept 2026). Covers
  source types (Helm, Kustomize, OCI, multi-source, plugin), sync policies +
  options + waves + hooks, ApplicationSet generators (List, Cluster, Git, Matrix,
  Merge, SCMProvider, PullRequest, Plugin, ClusterDecisionResource), Progressive
  Sync (Beta), Source Hydrator (Beta since v3.5), AppProjects, RBAC, sync
  impersonation (`destinationServiceAccounts`), GPG/cosign signature
  verification, GitOps repo layout (mono vs poly, app-of-apps vs ApplicationSet
  — Argo recommends ApplicationSet first), troubleshooting drift / OutOfSync /
  sync loops / stuck-deletion / hook failures, and v3.0→v3.5 changes (annotation
  tracking default, SSA-migration regression, CVE-2026-42880 Secret leak).
  NOT for installing or operating the Argo CD control plane (HA, Dex,
  repo-server tuning, UI customization).
when_to_use: >-
  Use whenever the user mentions Argo CD, ArgoCD, GitOps, Application CR,
  ApplicationSet, app-of-apps, sync policy, sync wave, AppProject, GitOps repo,
  publishing apps to Kubernetes via Argo, or migrating from Flux to Argo CD —
  even if they don't say "Argo CD" explicitly.
---

# Argo CD application authoring

For developers and platform teams who **publish** Argo CD `Application` and
`ApplicationSet` manifests in git. **v3.5 shipped** (v3.5.0 on 2026-08-04;
latest **v3.5.3**, 2026-09-14) and the v3.4 line continues in parallel (latest
**v3.4.9**, also 2026-09-14). Note there is no `v3.4.0` tag — that line's first
stable release is **v3.4.1**, as its own notes say.

**Before upgrading to 3.5, read these three.** All verified 2026-09-15:

- **A Secret data-loss regression is open.** `RespectIgnoreDifferences=true`
  plus a key-level `ignoreDifferences` rule on a Secret that renders
  `stringData` now drops the **entire `data` map** on sync
  ([#29644](https://github.com/argoproj/argo-cd/issues/29644), OPEN, filed
  2026-09-09). It is a regression from #27136, cherry-picked into both the 3.4
  and 3.5 lines, and the reporter has a unit test passing on v3.4.4 and failing
  on v3.5.2. Self-heal then re-applies the key-less manifest forever. If you
  ignore individual Secret keys, check this before you sync.
- **Helm 4 can change your rendered manifests with no chart or values edit.**
  v3.5.0 bundles Helm 4.2.x, whose null/nil coalescing differs, so a chart may
  start emitting explicit `null` fields
  ([#29068](https://github.com/argoproj/argo-cd/issues/29068)). Diff a render
  across the bump rather than assuming parity.
- **Plain-HTTP OCI registries need an explicit flag** under Helm 4:
  `--insecure-oci-force-http`, or `insecureOCIForceHttp: "true"` on the repo
  secret. Documented limitation: combining it with
  `--insecure-skip-server-verification` makes Helm 4 silently drop
  `--plain-http`, with no workaround when both are legitimately required. Cited file paths in references/ are relative to a local clone
of `argoproj/argo-cd` (e.g. `docs/user-guide/best_practices.md`). Without
a local clone, fetch the same content via `gh api repos/argoproj/argo-cd/contents/<path>`
or read https://github.com/argoproj/argo-cd at the matching path.

## Quick decision guide

| Task | Go to |
|------|-------|
| Write a new `Application` from scratch | § Canonical Application below |
| Pick `source` vs `sources` (multi-source); choose Helm/Kustomize/OCI | `references/application.md` |
| Write an `ApplicationSet` (any generator) | § Canonical ApplicationSet + `references/applicationset.md` |
| Pick the right ApplicationSet generator | `references/applicationset.md` § Generator Picker |
| Set sync policy / `syncOptions` / retry / `selfHeal` | § Sync policy below + `references/sync.md` |
| Add sync waves / hooks / health checks | `references/sync.md` § Waves, Hooks, Health |
| Stop drift fights (HPA, webhooks, kubectl edits) | `references/troubleshooting.md` § OutOfSync drivers |
| Lay out the GitOps repo (mono vs poly, app-of-apps) | `references/repo-layout.md` |
| Write/audit an `AppProject` for multi-tenancy | `references/projects-rbac.md` § AppProject |
| Configure sync impersonation (per-app SA) | `references/projects-rbac.md` § Impersonation |
| Verify signed commits / OCI artefacts | `references/projects-rbac.md` § Signature verification |
| App stuck deleting / `ComparisonError` / `SyncFailed` | `references/troubleshooting.md` |
| Upgrading 3.x → 3.y, deprecations, "what to drop" | `references/version-changes.md` |

## Critical gotchas (May 2026)

### 1. ServerSideDiff leaks Secrets — two CVEs, and the first fix was incomplete

**Floor: v3.4.2 / v3.3.10 / v3.2.12.** Anything at or below v3.4.1 / v3.3.9 /
v3.2.11 is exposed. Verified 2026-09-15.

| CVE | Published | Affected | Fixed in | Trigger |
|-----|-----------|----------|----------|---------|
| CVE-2026-42880 (**critical**) | 2026-05-01 | 3.2.0 – 3.3.8 | 3.3.9 / 3.2.11 | `ServerSideDiff` + the `IncludeMutationWebhook=true` compare-option |
| CVE-2026-45737 (medium) | 2026-05-13 | 3.2.0 – 3.2.11, **3.3.9**, **3.4.1** | **3.4.2 / 3.3.10 / 3.2.12** | `argocd app diff --server-side-diff` — **no annotation needed** |

**The trap: 3.3.9 and 3.2.11 are the remediation for the first CVE and are
inside the second.** The advisory says so outright — "the original fix for
GHSA-3v3m-wc6v-x4x3 is incomplete". Upgrading to the number the critical
advisory names lands on a vulnerable build.

The second is not a narrower rerun of the first. It needs **no compare-option**:
the fix masked top-level Secret data but not the copy embedded in
`kubectl.kubernetes.io/last-applied-configuration`, which any Secret previously
written by *client-side* apply still carries. Server-side dry-run returns that
annotation on `predictedLive`, and the masking only rewrote `live`. So a cluster
that never set `IncludeMutationWebhook=true` is still exposed, and anyone who
can run `argocd app diff --server-side-diff` sees the values.

**Therefore stripping the annotation is not a mitigation for the second CVE** —
it only closes the first. Below the floor, the containment is to restrict who
holds `applications, get` and who can run `app diff`, and to re-apply affected
Secrets server-side so the annotation stops carrying plaintext. Strip
`IncludeMutationWebhook=true` anyway and block it in CI with
`kubeconform`/conftest; it is a footgun independent of patch level.

**Bundled checker — `scripts/check-serversidediff-exposure.py`.** Runs both
checks, because neither alone decides it:

```bash
python3 scripts/check-serversidediff-exposure.py ./apps --version 3.4.1
python3 scripts/check-serversidediff-exposure.py --selfcheck   # verifies the floors
```

It scans manifests as **text**, not parsed YAML, so the annotation is caught
inside Helm templates, kustomize patches and ApplicationSet `template:` blocks —
none of which parse standalone. Exit 1 on any exposure, so it drops into CI as
is. A clean manifest scan with no `--version` prints a warning rather than a
pass, because it proves nothing about the annotation-free CVE.

Also on this line: **CVE-2026-45738** (high, 2026-05-13) — stored XSS in
application **link annotations**, escalating a developer who can edit an
Application to admin. Affects `< 3.0.0` only, so any 3.x is clear; it matters
when advising anyone still on 2.x.

### 2. Argo CD v3.0 flipped seven defaults — don't write apps as if on v2

In May 2026 assume v3.x semantics:

- **Resource tracking is annotation-based by default**, not labels. Don't add
  `app.kubernetes.io/instance` overrides expecting them to track ownership.
- **`.status` is ignored on all resources by default** (was: only CRDs).
  ServerSideDiff respects this; mutation-webhook drift in `.status` no longer
  shows up as OutOfSync.
- **Default `resource.exclusions` ships with the install** (Endpoints,
  EndpointSlice, Lease, *SubjectAccessReview, TokenReview, CSR,
  CertificateRequest, Kyverno reports, Cilium endpoints, PolicyReports).
- **Logs RBAC is enforced**: roles need explicit `logs, get` to view pod logs.
- **`update`/`delete` RBAC no longer inherits to managed resources.**
- **`spec.preserveUnknownFields: false` on CRDs causes drift now** — drop the
  field; use `x-kubernetes-preserve-unknown-fields: true` on schemas.
- **In-cluster destination disabled (`cluster.inClusterEnabled: "false"`) hard-blocks new apps** to that cluster.

Full list with PRs: `references/version-changes.md` § v3.0.

### 3. Skip Argo CD 3.3.0 and 3.3.1 — SSA migration regression

3.3.0 forced the `kubectl-client-side-apply` → SSA field-manager rewrite, broke
many real apps, and required `ClientSideApplyMigration=false` as a temp
workaround. **3.3.2 fixed it** (2026-02). Operators should be on 3.3.2+ before
publishing on this cluster.

When Argo CD manages itself, the meta-Application needs
`ServerSideApply=true` in `syncOptions` because the ApplicationSet CRD
exceeds the 262 144-byte client-side-apply annotation limit.

### 4. Source Hydrator reached **Beta** in v3.5 — still not GA

Alpha through v3.4, promoted to Beta in v3.5.0. Beta is not a stability
guarantee: `spec.sourceHydrator` remains on the feature-maturity table's
unstable list, so treat long-lived automation against it as something you may
have to migrate.

**Manifest signing changed hands in v3.5.** The GnuPG path — `.spec.signatureKeys`
on `AppProject`, plus `argocd proj add-signature-key` / `remove-signature-key` —
is deprecated in favour of the new **Source Integrity** subsystem, and v3.5.0
added opt-in dry-source integrity verification for the hydrator (Alpha, #19302).
Argo CD still ships no first-class cosign integration.

### 5. The default `AppProject` is a footgun in any multi-tenant cluster

`default` permits **every** repo, **every** destination, **every** cluster-scoped
resource. Production app authors should never set `spec.project: default`. Make
a project-per-team or project-per-environment, set `sourceRepos`, `destinations`,
`clusterResourceWhitelist`, `signatureKeys`. See `references/projects-rbac.md`.

### 6. Templated `project:` in ApplicationSet bypasses tenancy

`spec.template.spec.project: "{{path.basename}}"` lets an attacker who controls
the source git path elevate to any project they can name. Hard-code the project
in the ApplicationSet template. Argo CD warns about this in
`docs/operator-manual/applicationset/Generators-Git.md` lines 5-11.

### 7. ApplicationSets are recommended over app-of-apps

The official guidance — `docs/operator-manual/cluster-bootstrapping.md` line 7
— is now ApplicationSet first. App-of-apps still works for the bootstrap
(root → ApplicationSets), but for app fan-out, prefer an ApplicationSet with a
Git directory generator over a parent Application that points at child
Applications.

## v3.4 → v3.5 breaking changes (upgrade guide, verified 2026-09-15)

Beyond the three hazards at the top, the official 3.4→3.5 upgrade guide lists:

| Change | What it breaks |
|---|---|
| **GnuPG replaced by Source Integrity** | `.spec.signatureKeys` on `AppProject` and `argocd proj add-signature-key` / `remove-signature-key` are deprecated in favour of `sourceIntegrity`. |
| **Impersonation now covers all API-server actions** | Previously sync-only. Viewing logs, deleting resources and running resource actions now impersonate too, so the service account's RBAC must cover them or those actions start failing. |
| **gRPC `EventList` type changed** | `ListResourceEvents` (Application, ApplicationSet) and `ListEvents` (Project) return Argo CD's own type, not the Kubernetes one. Regenerate custom gRPC clients. REST/JSON is unaffected. |
| **React 19 in the UI** | UI extensions must be rebuilt to externalize `react/jsx-runtime`, or fail with `Extension <name>.js failed to load: TypeError: Cannot read properties of undefined`. |
| `--repo-server-strict-tls` deprecated | Use `--repo-server-ca-cert-path`. Repo-server also gains opt-in mTLS via an `argocd-repo-server-mtls` Secret. |

**From v3.4.1, an ApplicationSet change that is easy to miss.** Helm 3.19.0
changed how the cluster version is interpreted, so Cluster Generators that
select on Kubernetes version and use `argocd.argoproj.io/auto-label-cluster-info`
must move to **`argocd.argoproj.io/kubernetes-version`** in
`vMajor.Minor.Patch` form, not the old `Major.Minor`.

**Feature maturity — none of these is GA.** Source Hydrator went Alpha → **Beta**
in v3.5.0, sync impersonation went → **Beta** in v3.5.0, and Progressive Sync
has been **Beta since v3.3.0** (not v3.4, which the docs corrected). The
v3.5.0 dry-source signature verification under the hydrator is **Alpha**.
ApplicationSet in any namespace is now **stable**. OCI sources are absent from
the maturity table entirely, which is the closest thing to unqualified status
they have.

**Two more post-3.5 regressions worth knowing**, both open: `valueFiles` glob
patterns such as `*.yaml` stopped matching
([#29069](https://github.com/argoproj/argo-cd/issues/29069)) in the same release
that advertised wildcard support, and an `oci://` source combined with the
`argocd.argoproj.io/manifest-generate-paths` annotation flaps the Application to
Unknown every reconcile with `unsupported scheme "oci"`
([#29058](https://github.com/argoproj/argo-cd/issues/29058)).

## Canonical Application

Smallest sensible production Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payments-api
  namespace: argocd                         # default; with app-in-any-namespace can live in tenant ns
  finalizers:
    - resources-finalizer.argocd.argoproj.io  # cascade delete child resources when App is deleted
spec:
  project: team-payments                    # NEVER `default` in production
  source:
    repoURL: https://github.com/example/config-repo.git
    targetRevision: main                    # pin to a tag or SHA in production
    path: apps/prod/payments-api
    helm:                                   # or `kustomize:`, `directory:`, `plugin:`
      releaseName: payments-api
      valueFiles:
        - values.yaml
        - values-prod.yaml
  destination:
    name: prod-eu-1                         # XOR with `server:` — prefer `name` (stable)
    namespace: payments-api
  syncPolicy:
    automated:
      enabled: true                         # v3.x: use this, not "delete the automated block"
      prune: true                           # default false; without this, deleted resources stay
      selfHeal: true                        # only if no controllers mutate the spec
      allowEmpty: false                     # never prune everything if the app is empty
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true                # required for self-managed Argo CD; recommended otherwise
      - ApplyOutOfSyncOnly=true             # huge win on apps with many objects
      - RespectIgnoreDifferences=true       # makes ignoreDifferences actually skip the field on apply
      - PrunePropagationPolicy=foreground
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas                    # HPA-managed; without this the controller sync-loops
  revisionHistoryLimit: 5
  info:
    - name: Runbook
      value: https://wiki.example.com/payments-api
```

The single most important field for production hygiene: `targetRevision` —
**pin to a SHA or tag**, not `HEAD` / `main`. Floating revisions cause
non-deterministic syncs and break audit. Argo's own `best_practices.md` makes
this explicit (`docs/user-guide/best_practices.md` lines 57-79).

## Canonical ApplicationSet

One Application per directory under `apps/<env>/` in the config repo:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: prod-apps
  namespace: argocd
spec:
  goTemplate: true                          # ALWAYS set; default is the legacy fasttemplate
  goTemplateOptions:
    - missingkey=error                      # fail-fast on typos in template paths
  generators:
    - git:
        repoURL: https://github.com/example/config-repo.git
        revision: main
        directories:
          - path: apps/prod/*               # one Application per matching subdir
  template:
    metadata:
      name: '{{ .path.basename }}'          # e.g. "payments-api"
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      project: team-platform                # HARD-CODED — do not template (security)
      source:
        repoURL: https://github.com/example/config-repo.git
        targetRevision: '{{ .metadata.commitSHA }}'  # available with Git generator + values
        path: '{{ .path.path }}'
      destination:
        name: prod-eu-1
        namespace: '{{ .path.basename }}'
      syncPolicy:
        automated:
          enabled: true
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - ServerSideApply=true
          - ApplyOutOfSyncOnly=true
  syncPolicy:
    preserveResourcesOnDeletion: false      # delete generated Applications on AppSet deletion
    applicationsSync: sync                  # create+update+delete (was named `policy:` in older docs)
```

Hard rules:

1. **`goTemplate: true` always.** The default is `false` (legacy fasttemplate),
   which silently mishandles nested objects, ranges, and `if`. The new pattern
   uses Go templates with `.path.basename`, `.path.path`, `.cluster.name`, etc.
2. **`goTemplateOptions: ["missingkey=error"]` always.** Without it, typos in
   template paths render as the empty string and the bug ships.
3. **`project:` is hard-coded, never templated.** Templated project lets a git
   PR author change `spec.template.spec.project` to a privileged project.
4. **`finalizers:` go in the template, not the AppSet itself.** Adding the
   finalizer to the AppSet metadata won't propagate to children.
5. **`applicationsSync: sync`** is what most teams want. `create-only` /
   `create-update` / `create-delete` are escape hatches for migrations.
6. **For Git directory generators, `path: <dir>/*`** matches one level.
   `<dir>/**` doesn't recurse — use `<dir>/*/*` for two-deep, etc.

ApplicationSet generator picker, all generator schemas, Progressive Sync (Beta
in v3.3), and the `preservedFields` / `templatePatch` knobs live in
`references/applicationset.md`.

## Sync policy decision shortcut

Default policy for a typical workload:

- `automated.enabled: true`, `prune: true`, `selfHeal: true` when no controller
  mutates the spec. When one does (HPA, cert-manager, sidecar injectors),
  keep `selfHeal: false` OR add precise `ignoreDifferences` and
  `RespectIgnoreDifferences=true`.
- `syncOptions` to set on every app:
  `CreateNamespace=true`, `ServerSideApply=true`, `ApplyOutOfSyncOnly=true`,
  `RespectIgnoreDifferences=true`. `PrunePropagationPolicy=foreground` for
  synchronous child-cleanup pruning; `background` for fast pruning.
- `retry` defaults are fine; raise `limit` to 10 only for apps with PreSync
  hooks that legitimately flake (DB migrations on shared infra).
- For apps with destructive operations (delete Namespaces, PVCs):
  `Prune=confirm` and/or `Delete=confirm` (v3.3+) — UI prompts before the op.

For the full `syncOptions` table, sync waves, hooks, health checks, and the
diff strategy reference (Server-Side Diff is **Stable since v3.2** but **not
default**), see `references/sync.md`.

## CLI quick reference for app authors

The 12 most-used commands:

```bash
# Inspect what's in git vs the live cluster
argocd app diff <name>                    # Argo's view of git vs live
argocd app diff <name> --server-side-generate  # render via repo-server, like a sync would

# Force the controller to re-fetch the source
argocd app get <name> --refresh           # re-evaluate sync status (uses cache)
argocd app get <name> --hard-refresh      # bust the manifest cache; rare, slow

# See what Argo CD WOULD apply
argocd app manifests <name>               # rendered manifests from git
argocd app manifests <name> --source live # what's actually live

# Sync controls
argocd app sync <name>                    # full sync
argocd app sync <name> --resource <gk>:<name>          # selective sync (skips hooks, no history)
argocd app sync <name> --prune --dry-run  # preview a prune

# Termination & deletion
argocd app terminate-op <name>            # cancel an in-progress sync
argocd app delete <name> --cascade        # delete app + its managed resources
argocd app delete <name> --no-cascade     # delete app, leave resources

# ApplicationSets
argocd appset get <name>                  # show generated children
argocd appset create -f appset.yaml --dry-run  # preview before applying
```

The `--core` mode (no API server, talk straight to k8s) is useful for CI:
`argocd --core app diff <name>` skips the gRPC server entirely. Set
`KUBECTL_EXTERNAL_DIFF=delta` for nicer output.

## Annotations cheat sheet

The `argocd.argoproj.io/*` annotations app authors use most:

| Annotation | On | Effect |
|------------|----|--------|
| `sync-wave: "<int>"` | any resource | order: lower runs first; default 0; negatives run before 0 |
| `hook: PreSync\|Sync\|PostSync\|SyncFail\|Skip\|PreDelete\|PostDelete` | Job/Pod/etc. | run as a hook in that phase |
| `hook-delete-policy: HookSucceeded\|HookFailed\|BeforeHookCreation` | hook resource | when to GC the hook |
| `sync-options: <opt>=<val>,<opt>=<val>` | any resource | per-resource override of `syncPolicy.syncOptions` |
| `compare-options: IgnoreExtraneous` | any resource | hide extraneous resources from diff |
| `compare-options: IncludeMutationWebhook=true` | any resource | **DO NOT USE** below v3.4.2 / v3.3.10 / v3.2.12 — see §1; note the second CVE needs no annotation |
| `manifest-generate-paths: ".;../base"` | Application | only re-render if these git paths change (huge perf win) |
| `refresh: "hard"` | Application | trigger one hard-refresh (Argo deletes the annotation after) |
| `skip-reconcile: "true"` | Application | freeze reconcile (Alpha; intended for OCM) |

Full table including `tracking-id`, `sync-statuses`, finalizer variants:
`references/sync.md` § Annotations.

## Reference files — when to load

| File | Read when |
|------|-----------|
| `references/application.md` | Authoring a non-trivial Application: source types (Helm/Kustomize/directory/jsonnet/OCI/plugin), multi-source `$values` pattern, finalizers, Source Hydrator, OCI digest pinning |
| `references/applicationset.md` | Any ApplicationSet authoring: all 9 generators with examples, Progressive Sync (Beta v3.3), `templatePatch`, `preservedFields`, `ignoreApplicationDifferences`, `applicationsSync`, the `goTemplate` gotcha tree |
| `references/sync.md` | Anything sync- or drift-related: every `syncOption` with default + flip-reason, sync waves + phase ordering + kind-order, all 7 hook types, all 3 delete policies, Lua health checks, diff strategies, selective sync, sync windows |
| `references/repo-layout.md` | Designing or restructuring a GitOps repo: config-repo separation, directory-per-env vs branch-per-env, app-of-apps vs ApplicationSet, tool choice + umbrella-chart anti-pattern, Source Hydrator, OCI sources, private repos + OpenSSH 8.9 ssh-rsa gotcha |
| `references/projects-rbac.md` | Multi-tenancy, security, or supply-chain: every `AppProject` field, app/appset-in-any-namespace (Stable v3.4), sync impersonation (Beta v3.4), GPG signature verification, secrets hygiene (ESO/SealedSecrets/SOPS/CSI), trusted vs untrusted repos |
| `references/troubleshooting.md` | Anything broken: OutOfSync drivers (HPA, webhooks, field-manager wars, etc.), SyncFailed/hook leaks, ComparisonError, stuck deletion, ApplicationSet generation issues, auto-sync looping, performance, "deleted from git but still there" checklist |
| `references/version-changes.md` | Upgrading 3.x→3.y or auditing old manifests: per-minor highlights v3.0→v3.4, breaking changes, maturity table, CVEs, 22 "things to drop now" patterns |
| `references/sources.md` | Verifying citation freshness: dated index of every URL/repo/spec used to build this skill |

## Adjacent skills

- **`helm`** for chart authoring questions (Helm 4 SSA, OCI digest install,
  values, helpers). This skill assumes Helm chart authoring competence.
- **`kubefwd`** for accessing Argo CD UI / repo-server services from a
  laptop without one-port-at-a-time `kubectl port-forward`.
- **`gh-cli`** for fetching release notes, PRs, security advisories from the
  argo-cd repo (canonical changelog — `CHANGELOG.md` in the repo is stale
  back to 2022).
