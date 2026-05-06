# Repo layout, tool selection, bootstrap

GitOps-repo design choices for an Argo CD v3.3 / v3.4 consumer. Citations
are paths relative to the `argoproj/argo-cd` repo root.

## 1. Separate the config repo from the source-code repo

Rule. App source and Kubernetes manifests live in **different** Git repos.

The five reasons in `docs/user-guide/best_practices.md` lines 3–29:

1. **Code vs config separation** — bumping a replica count should not
   trigger an app CI build.
2. **Cleaner audit log** — the config repo's history *is* the deploy
   history, undiluted by source churn.
3. **Polyrepo applications** — microservices with independent versioning
   ("ELK, Kafka + ZooKeeper") don't belong in one source tree.
4. **Separation of access** — devs push to source, release eng push to
   config; CODEOWNERS scope is natural.
5. **Avoids the CI loop** — CI committing image-tag bumps back to its
   own build repo creates an infinite build → commit → build cycle.
   A separate config repo cuts the loop.

Corollary (`source-hydrator.md` lines 519–527): never co-locate hydrated
manifests next to dry templates — hydrator overwrites mutate developers'
local edits silently.

Pragmatic default: **one config repo per org**, directories per env
(§3), branch protection on `main`, separate from any source repo.

## 2. `targetRevision` immutability — pin to tag or SHA

Rule. Production `targetRevision` and remote bases must be pinned.
`HEAD`/`main` drifts as upstream pushes — manifests change meaning
between Argo CD reconciliations even when *your* repo is unchanged.

`best_practices.md` lines 57–79:

> "When using templating tools like helm or kustomize, it is possible
> for manifests to change their meaning from one day to the next. This
> is typically caused by changes made to an upstream helm repository or
> kustomize base."

```yaml
# BAD — pulls HEAD; meaning drifts silently
resources:
- github.com/argoproj/argo-cd//manifests/cluster-install

# GOOD — pin to tag or SHA
bases:
- github.com/argoproj/argo-cd//manifests/cluster-install?ref=v0.11.1
```

Same in `Application.spec.source.targetRevision`. From
`tracking_strategies.md` lines 31–73:

| Use case            | targetRevision pattern        |
|---------------------|-------------------------------|
| Production          | Commit SHA, or signed tag     |
| Pre-prod (patches)  | `1.2.*` or `>=1.2.0 <1.3.0`   |
| QA (minor releases) | `1.*` or `>=1.0.0 <2.0.0`     |
| Local dev           | `HEAD` / `master`             |

**Ambiguous-ref reconciliation loop** (`tracking_strategies.md` lines
76–98). If `release-1.0` exists as both a branch (commit B) and a tag
(commit A), Argo CD may resolve `targetRevision` inconsistently across
reconciles → permanent sync flap. Fix: fully-qualify refs
(`refs/heads/release-1.0` / `refs/tags/release-1.0`) and never reuse
names between branches and tags.

## 3. Directory-per-env beats branch-per-env

Rule. Use `apps/<env>/...` directories on a single `main` branch.
Branches are reserved for the **Source Hydrator**'s rendered output
(§8), not for the dry source.

`cluster-bootstrapping.md` examples (lines 49–67, 106–116) and the
Git directory generator both presume directories.

Why directory wins for the dry side:

- All envs visible in one PR; cross-env drift in `git diff`.
- Git directory generator natively iterates `apps/prod/*` — no
  per-branch ApplicationSet ceremony.
- `manifest-generate-paths` scopes refresh to the changed env (§4).
- Branch-protection rules apply uniformly to one branch.

Branch-per-env anti-pattern surface area:

- Per-env diffs require cross-branch reviews.
- `git merge dev → prod` becomes a deploy promoter — easy to
  fast-forward unrelated changes.
- One ApplicationSet per branch; Git directory generator can't fan out
  across branches.
- Cherry-pick between envs corrupts history.

## 4. Mono-repo for app manifests — when and how

Right when: small org, single team, one config repo per org. Not right
when: per-team RBAC must be enforced via separate repos, or per-env push
permissions diverge sharply.

What to set on a mono-repo:

```yaml
# Per-Application — scope re-rendering to the changed subtree
metadata:
  annotations:
    argocd.argoproj.io/manifest-generate-paths: '/apps/api;/charts/api'
    argocd.argoproj.io/ignore-resource-updates: "true"   # silence noisy resources
```

`manifest-generate-paths` makes the repo-server skip rendering this
Application when no file under those paths changed. Required at
non-trivial repo sizes — without it, every commit re-renders every app.

v3.3+ supports a shallow-clone repo flag — check `argocd-repo-server`
startup args; reduces wall-clock on first refresh after restart but
disables blame-style log walks.

Mono vs poly trade-offs:

| Aspect                    | Mono-repo                                       | Poly-repo                                          |
|---------------------------|-------------------------------------------------|----------------------------------------------------|
| Cross-env diff in PR      | Trivial (one PR)                                | Hard (per-env PRs)                                 |
| RBAC scoping              | Hard (single branch-protection scope)           | Natural (per-repo permissions)                     |
| Promotion dev → prod      | Move file/path or change tag                    | PR from env-A repo to env-B repo                   |
| Refresh cost              | Whole-repo; mitigate with `manifest-generate-paths` | Per-repo refresh                              |
| ApplicationSet generators | Git directory generator on `apps/<env>/*`       | One ApplicationSet per repoURL                     |
| Bootstrap                 | One root-app pointing at one repo               | One root-app per env or per repo                   |

## 5. App-of-apps vs ApplicationSet — pick the right primitive

Argo's official guidance now recommends **ApplicationSets** over
app-of-apps for app fan-out (`cluster-bootstrapping.md` line 7).
App-of-apps is presented as the *alternative* (line 84+), still
supported but not the v3.x default.

When app-of-apps is still useful:

- **Bootstrap** — root Application points at `argocd/` directory
  containing your AppProjects + ApplicationSets. One imperative
  `argocd app create` and the rest is declarative.
- **Per-cluster meta-config** — small static set of "infra" apps that
  must be ordered with sync waves (cert-manager → external-dns →
  sealed-secrets → workloads).

Minimal "root app" (`cluster-bootstrapping.md` lines 122–142):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io     # cascade delete
spec:
  destination:
    namespace: argocd
    server: https://kubernetes.default.svc
  project: default
  source:
    path: argocd                               # contains AppProjects + AppSets
    repoURL: https://github.com/myorg/config-repo.git
    targetRevision: v1.2.3                     # pin in prod (§2)
  syncPolicy:
    automated:
      prune: true
```

Bootstrap once: `argocd app create root --repo <repo> --path argocd/`.
Bulk-sync children: `argocd app sync -l app.kubernetes.io/instance=root`.

### Pitfalls

**1. Admin-only WARNING** (`cluster-bootstrapping.md` lines 88–95):

> "The ability to create Applications in arbitrary Projects is an
> admin-level capability. Only admins should have push access to the
> parent Application's source repository."

Whoever can push to the root repo can declare an Application in any
Project — including `argocd` (effective admin). Branch-protect the
root path; require admin review on `argocd/**`.

**2. Finalizer cascade ordering** (lines 194–208). Without
`resources-finalizer.argocd.argoproj.io`, deleting the root leaves
children running. With it, deletion cascades parent → children → child
workloads. Catastrophic on accidental delete; pair with a separate
admin-only AppProject and restricted RBAC.

**3. v3.2 deletion semantics change** (lines 210–220). Deletion from
the Applications List and from the Resource Tree now behave
consistently. Non-cascading (orphan) deletion is still available but
explicit. Re-check v3.1 → v3.2 runbooks.

**4. Child-app drift / `RespectIgnoreDifferences`** (lines 222–244).
Without it, the parent reverts user edits to
`/spec/syncPolicy/automated`, the `argocd.argoproj.io/refresh`
annotation, and `/operation`. Fix:

```yaml
spec:
  syncPolicy:
    syncOptions: [RespectIgnoreDifferences=true]
  ignoreDifferences:
  - group: "*"
    kind: Application
    jsonPointers:
    - /spec/syncPolicy/automated
    - /metadata/annotations/argocd.argoproj.io~1refresh
    - /operation
```

## 6. ApplicationSet with Git generator — env-directory layout

Canonical layout. ApplicationSet YAML is in `SKILL.md`; here we cover
the **directory shape**.

```
config-repo/
├── README.md
├── argocd/
│   ├── projects/
│   │   ├── infra.yaml                # AppProject — signatureKeys set
│   │   └── apps.yaml                 # AppProject — workloads
│   ├── appsets/
│   │   ├── dev-apps.yaml             # Git dir generator → apps/dev/*
│   │   ├── stage-apps.yaml           # Git dir generator → apps/stage/*
│   │   ├── prod-apps.yaml            # Git dir generator → apps/prod/*
│   │   └── infra.yaml                # AppSet w/ cluster generator
│   └── root-app.yaml                 # The single root Application
├── apps/
│   ├── dev/{api,frontend,postgres}/
│   ├── stage/...
│   └── prod/...
├── base/{api,frontend,postgres}/     # Kustomize bases
└── charts/shared-lib/                # local Helm charts
```

Each `apps/<env>/<name>/` is one Application — Kustomize
`kustomization.yaml`, Helm `Chart.yaml + values.yaml`, or raw YAML.

New directory = new Application automatically (no PR to add a generator
entry, `Generators-Git.md` lines 83–84):

> "Whenever a new Helm chart/Kustomize YAML/Application/plain
> subdirectory is added to the Git repository, the ApplicationSet
> controller will detect this change and automatically deploy the
> resulting manifests within new Application resources."

### Sibling docs the AppSet should ignore

Drop a `README.md` or `OWNERS` file into `apps/prod/` and the generator
will try to make a `prod-` Application out of it. Two protections:

- `.`-prefixed directories are excluded by default.
- Otherwise use exclude patterns. **Exclude wins over include**
  (`Generators-Git.md` line 130):

```yaml
generators:
- git:
    repoURL: https://github.com/myorg/config-repo.git
    revision: main
    directories:
    - path: apps/prod/*
    - path: apps/prod/_*           # underscore-prefixed = docs / fixtures
      exclude: true
```

Templated `project` is a security boundary
(`Generators-Git.md` lines 5–11): if `project: '{{.path.basename}}'`,
then `mkdir apps/argocd` lets a developer deploy into the privileged
`argocd` project. **Don't template `project`** — pin per ApplicationSet.

## 7. Tool choice — Helm vs Kustomize vs raw vs CMP

Native tools (`config-management-plugins.md` line 4): Helm, Jsonnet,
Kustomize. Plus raw directories.

| Tool       | Best for                                                | Argo-CD-specific gotchas                                                                                                                |
|------------|---------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Raw YAML   | Few static manifests; Operator CRs                      | None. Use `directory.recurse: true` for nested paths.                                                                                   |
| Helm       | Third-party charts (cert-manager, ingress-nginx)        | `helm template` only — Argo doesn't manage Helm state (`docs/user-guide/helm.md` line 6). `lookup`, `randAlphaNum` non-deterministic.   |
| Kustomize  | Your own apps with per-env overlays                     | Pin remote bases with `?ref=<sha>` (§2).                                                                                                |
| CMP        | cdk8s, ytt, jsonnet-libsonnet, vault-injected templates | Significant operational cost; sidecar to repo-server.                                                                                   |

### The umbrella-chart anti-pattern

`docs/user-guide/multiple_sources.md` lines 38–40:

> "**Do not abuse multiple sources** ... this feature is NOT destined
> as a generic way to group different/unrelated applications. ... If
> you find yourself using more than 2-3 items in the sources array
> then you are almost certainly abusing this feature."

The umbrella chart pattern (one Helm chart whose only purpose is 10
sub-charts as `dependencies`) gives:

- One Argo CD Application for the whole stack → no per-service health,
  rollback, or RBAC.
- Tightly-coupled Helm dependencies — bumping one sub-chart needs
  umbrella `Chart.yaml` recompile.
- Hard to debug which sub-resource is out-of-sync.

Right primitive: one Argo CD **Application** per service, grouped by
ApplicationSet or app-of-apps. The Application is the grouping unit.

### Hybrid patterns

**Pattern A: `kustomize.helmCharts` (Kustomize calls Helm).** Native
Kustomize `kustomize build --enable-helm`. Enable globally:

```yaml
# argocd-cm
data:
  kustomize.buildOptions: --enable-helm
```

Or per-app via a CMP. Use when patching a 3rd-party chart that doesn't
expose what you need via values.

**Pattern B: multi-source with `$values` (Helm values from another
repo).** `multiple_sources.md` lines 46–88. Keep upstream chart pristine,
keep values in your config repo:

```yaml
spec:
  sources:
  - repoURL: 'https://prometheus-community.github.io/helm-charts'
    chart: prometheus
    targetRevision: 15.7.1
    helm:
      valueFiles: [$values/charts/prometheus/values.yaml]
  - repoURL: 'https://git.example.com/org/value-files.git'
    targetRevision: dev
    ref: values
```

A source with `ref:` cannot also have `chart:` (line 84). `$values`
resolves to the root of the ref source.

### When to fall back to a CMP

Legitimate use cases (`config-management-plugins.md` lines 4–10): cdk8s,
ytt, jsonnet-libsonnet, inline secret rendering (SOPS+helm), Helm
post-rendering pipelines, per-app `--enable-helm`.

CMP runs as a **sidecar to argocd-repo-server**. argocd-cm plugins were
deprecated v2.4, removed v2.8 — sidecar is the only v3.x path.

Sidecar requirements:

1. Entrypoint `/var/run/argocd/argocd-cmp-server`.
2. Run as user 999.
3. Plugin config at `/home/argocd/cmp-server/config/plugin.yaml`.

Six known CMP gotchas:

1. **Silent prune disaster.** Pipe failure (`kustomize build . | cat`)
   produces empty stdout; if `prune: true`, **Argo deletes all managed
   resources**. Always `set -o pipefail`.
2. **Stdout = valid YAML/JSON only**; logs to stderr.
3. **Manifest-generate vs lock-and-generate timeouts** — 90s
   `ARGOCD_EXEC_TIMEOUT` per generate, 60s repo-server. Raise both for
   slow renders.
4. **`provideGitCreds: true`** hands raw git creds to the plugin;
   trust required.
5. **`preserveFileMode: true`** leaks executable bit out of git;
   trust required.
6. **Errors cached in Redis**; repo-server restart doesn't clear.
   Use "Hard Refresh".

For monorepos, set `argocd.argoproj.io/manifest-generate-paths` so the
CMP re-runs only on relevant subtree changes.

## 8. Source Hydrator — rendered manifests in git

Status: **Alpha** (`source-hydrator.md` line 3). API may change.

Flow: **drySource** (templates on `main`) → hydrate (commit-server
renders) → **syncSource** (rendered YAML on `environments/<env>` branch)
→ cluster.

```yaml
spec:
  sourceHydrator:
    drySource:
      repoURL: https://github.com/myorg/config-repo
      path: helm-guestbook
      targetRevision: HEAD
    syncSource:
      targetBranch: environments/dev
      path: helm-guestbook                  # MUST be non-root
```

`syncSource.path` must be non-root because the hydrator cleans the
path on each run; root would wipe `README.md` and CI configs.

### PR-gated promotion via `hydrateTo`

```yaml
spec:
  sourceHydrator:
    drySource: { ... }
    syncSource:
      targetBranch: environments/dev
      path: helm-guestbook
    hydrateTo:
      targetBranch: environments/dev-next   # hydrator pushes here
```

CI opens PR `environments/dev-next → environments/dev`. **Argo CD does
not create the PR** (line 285) — bring your own bot. Branch-protect
`environments/*` so only the hydrator GitHub App can write.

### Commit traceability

Hydrator writes a JSON `hydrator.metadata` file at the root of every
hydrated commit recording the dry SHA. CI image-bump jobs attach
`Argocd-reference-commit-*` git trailers (RFC 5322 format) so hydrated
commits link back to the source-code commit that triggered the bump.

### Three hard incompatibilities

- **Signature verification** (line 476). Hydrator does not sign its
  pushes. Mutually exclusive with AppProject `signatureKeys`. Pick one.
- **Inline secret injection** (line 502). Helm+SOPS / Argo CD Vault
  Plugin / ESO-rendered values that hydrate plaintext secrets would
  commit them to git. Don't.
- **`manifest-generate-paths`** (line 487). Hydrator ignores it on the
  dry side; you can't use it to scope hydration.

### Determinism rule

`source-hydrator.md` line 510:

> "For a given dry source commit, the hydrator should always produce
> the same hydrated manifests."

Doc-flagged non-deterministic patterns to remove from your charts:
Helm `lookup` (queries the live cluster), Helm `randAlphaNum` /
`randAscii` (RNG), Helm time functions (`now`, `dateInZone`), unpinned
chart deps (`Chart.lock` not committed), unpinned Kustomize remote
bases, CMPs that read non-git state (env, network, files outside the
tar).

## 9. OCI artefacts as source

Argo CD v3 supports `oci://` repoURLs (`docs/user-guide/oci.md`).

```yaml
spec:
  source:
    path: .
    repoURL: oci://registry-1.docker.io/some-user/my-custom-image
    targetRevision: sha256:63dc60481b1b...    # PIN BY DIGEST IN PROD
```

Three spec keys:

- `repoURL: oci://<registry>/<image>` — `oci://` scheme is the marker.
- `targetRevision` — tag **or digest**. Prod = digest. Tags are
  mutable; a registry compromise overwrites them.
- `path` — relative path inside the expanded image. For OCI Helm
  charts (mediaType `vnd.cncf.helm.chart.content.v1.tar+gzip`):
  always `path: .`.

### Single-layer + media-type requirements

Default accepted layer media types:

- `application/vnd.oci.image.layer.v1.tar+gzip`
- `application/vnd.cncf.helm.chart.content.v1.tar+gzip`

Override: `ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES` env on
repo-server. Multi-layer images are rejected — pack as a single layer.

### ORAS push recipe

```bash
oras push <registry>/guestbook:1.2.3 .                       # default mediaType
oras push <registry>/guestbook:1.2.3 \                       # tarball form
  archive.tar.gz:application/vnd.oci.image.layer.v1.tar+gzip
oras push -a "org.opencontainers.image.version=1.2.3" \      # UI annotations
          -a "org.opencontainers.image.source=<repo>" \
          <registry>/guestbook:1.2.3 .
```

### Two credential variants

```bash
# (a) As an OCI repo
argocd repo add oci://registry-1.docker.io/bitnamicharts/nginx \
  --type oci --name stable --username U --password P

# (b) As an OCI Helm repo (no oci:// prefix; --enable-oci)
argocd repo add registry-1.docker.io/bitnamicharts/nginx \
  --type helm --name stable --username U --password P --enable-oci
```

### Signature verification — admission-controller side

```bash
# Cosign keyless
cosign verify \
  --certificate-identity-regexp <signing-workflow-regex> \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-github-workflow-repository "<owner/repo>" \
  <registry>/<image>:<tag>

# SLSA L3 — pin digest first to avoid TOCTOU
IMAGE="<image>@$(crane digest <image>)"
slsa-verifier verify-image "$IMAGE" \
  --source-uri github.com/<owner>/<repo> --source-tag v1.2.3
```

**Argo CD does not auto-verify cosign at sync time.**
`signed-release-assets.md` line 154: verify with admission/policy
controller (cosign Policy Controller, Sigstore, Kyverno verify-images).

## 10. Private repositories

Auth method matrix:

| Method                  | URL form                                       | When to pick                                             |
|-------------------------|------------------------------------------------|----------------------------------------------------------|
| HTTPS + token           | `https://github.com/...` (`.git` for GitLab)   | Simple, ubiquitous. Fine-grained PAT or deploy token.    |
| SSH + private key       | `git@github.com:...` or `ssh://...`            | GHES on non-standard port; Argo holds key.               |
| GitHub App              | `https://github.com/...`                       | **Recommended for orgs.** Per-repo via app installation. |
| OCI registry creds      | `oci://...` or `registry/...` + `--enable-oci` | OCI artefact / OCI Helm sources.                         |
| Azure Workload Identity | `https://...azure.com/...` or ACR              | Azure-native; pod federated identity, no static creds.   |
| Google Cloud Source     | `https://source.developers.google.com/...`    | GCP-native; service-account JSON.                        |
| TLS client cert         | `https://repo.example.com/...`                | mTLS-protected on-prem repo servers.                     |

### GitLab `.git`-suffix gotcha

`private-repositories.md` lines 4–8: GitLab and others 301-redirect
bare URLs to `.git`-suffixed canonical URLs. **Argo CD does not follow
these redirects.** Always include `.git`:

```
https://gitlab.com/myorg/config-repo.git    # works
https://gitlab.com/myorg/config-repo        # 301 → upstream rejects
```

### OpenSSH 8.9 `ssh-rsa` SHA-1 deprecation

Argo CD 2.4+ ships OpenSSH 8.9, which removes `ssh-rsa` SHA-1 from the
default acceptable algorithms. Old git servers using SHA-1 RSA host
keys fail with `no matching host key type found`. Two fixes:

1. **Rotate to ed25519** (preferred): regen server host keys / user
   deploy keys with `ssh-keygen -t ed25519`.
2. **Re-enable in SSH config** if rotation is impossible:

```
Host git.legacy.example.com
  PubkeyAcceptedAlgorithms +ssh-rsa
  HostkeyAlgorithms +ssh-rsa
```

Non-standard SSH ports require `ssh://user@host:port/...`. The
`git@host:repo` form parses port as a path — broken.

### Credential templates — longest-prefix-wins

```bash
argocd repocreds add https://github.com/myorg --username U --password P
argocd repo add https://github.com/myorg/repo-a   # uses template
argocd repo add https://github.com/myorg/repo-b   # uses template
```

URL-prefix match, **longest match wins**. A repo's own credentials
override templates. Declarative form: Secret with
`argocd.argoproj.io/secret-type: repo-creds`.

### TLS / SSH known-hosts

- TLS: `argocd cert add-tls` (prod) or
  `--insecure-skip-server-verification` (dev only). Declarative:
  `argocd-tls-certs-cm` ConfigMap.
- SSH known hosts: `argocd cert add-ssh` from `ssh-keyscan` output.
  Declarative: `argocd-ssh-known-hosts-cm`. **Hashed `known_hosts` not
  accepted by CLI/UI** — declarative ConfigMap only.

### Submodules

Auto-followed. Submodule auth must match the parent repo's. Disable:
`ARGOCD_GIT_MODULES_ENABLED=false`. Don't submodule across credential
domains.

## 11. CI/CD for application manifests

### Reference flow (`docs/user-guide/ci_automation.md` lines 7–55)

```bash
# 1. Build & push image (in source repo CI)
docker build -t mycompany/guestbook:v2.0 . && docker push mycompany/guestbook:v2.0

# 2. Bump manifests in the SEPARATE config repo (TIP line 21)
git clone https://github.com/mycompany/guestbook-config.git && cd guestbook-config
kustomize edit set image mycompany/guestbook:v2.0
git commit -am "Update guestbook to v2.0" && git push

# 3. (Optional) explicit sync if auto-sync is off
argocd app sync guestbook && argocd app wait guestbook
```

Why config-repo not source-repo: §1 reason 5 — CI bumping its own
build repo creates infinite build → commit → build.

### Industry pre-merge layer

The doc covers post-merge sync. Mature shops add a pre-merge gate:

```bash
# Schema validation
helm template . | kubeconform -strict -summary -

# Render PR's "what would be applied" against live cluster
argocd app manifests --revision <PR-sha> myapp
argocd app diff myapp --revision <PR-sha> --refresh

# Policy gates
helm template . | conftest test --policy ./policies -
kyverno apply ./policies --resource ./rendered.yaml
gator test --filename ./rendered.yaml --filename ./constraints/
```

Common policies: no `:latest` tags, all Deployments have resource
limits, no `hostNetwork: true`, required labels.

### Webhook for instant convergence

Default Argo poll: 3 min (apps), 3 min (ApplicationSets). Configure two
webhooks for instant reconcile (no polling):

- API server webhook `/api/webhook` — Application refresh.
  See `docs/operator-manual/webhook.md`.
- ApplicationSet controller — separate `/api/webhook` endpoint.

Both are needed if you use ApplicationSets.

## 12. Resource tracking — annotation vs label vs annotation+label

Configured by `application.resourceTrackingMethod` in `argocd-cm`
(`docs/user-guide/resource_tracking.md`).

### Three modes

- **`annotation`** — *v3.0 default*, recommended. Uses
  `argocd.argoproj.io/tracking-id` only.
- **`annotation+label`** — tracking via annotation; label
  `app.kubernetes.io/instance` written for **informational purposes
  only** (still 63-char truncated). Use when other tools require the
  standard instance label for grouping/dashboards.
- **`label`** — legacy. Uses `app.kubernetes.io/instance` for
  tracking. Subject to the collision below.

### Annotation format

```yaml
metadata:
  annotations:
    argocd.argoproj.io/tracking-id: my-app:apps/Deployment:default/my-deployment
```

Format: `<app>:<group>/<kind>:<ns>/<name>`. The annotation
**self-references** the resource it lives on. Lines 35–38: if it does
not reference the resource it's applied to, Argo CD ignores the
resource for sync status and pruning (lets HNC and similar copy
resources cross-namespace without breaking ownership).

### `app.kubernetes.io/instance` collision when using Helm

Concrete failure under `label` mode: Argo CD App `foo` syncs a Helm
chart that itself sets `app.kubernetes.io/instance: bar` on its
Deployment (release name = `bar`). Argo CD reads the label, sees
`bar`≠`foo`, doesn't recognise the Deployment as managed → out-of-sync
forever. Under `annotation` mode, the tracking-id annotation is
independent and the collision goes away.

### `installationID` — multi-instance Argo CD

Lines 27–34. If two Argo CD instances manage the same cluster:

```yaml
# argocd-cm
data:
  installationID: <unique-id-per-instance>
```

Each managed resource gets `argocd.argoproj.io/installation-id: <id>`.
Without it, the two instances fight over identically-named Applications.

### Custom label key

```yaml
data:
  application.instanceLabelKey: argocd.argoproj.io/instance
```

Argo reads/writes `argocd.argoproj.io/instance` instead of the standard
`app.kubernetes.io/instance`. Helm charts hard-coding the standard
label no longer collide.

### Decision matrix

| Situation                                              | Mode                            |
|--------------------------------------------------------|---------------------------------|
| Greenfield, single Argo CD instance                    | `annotation` (v3.0 default)     |
| Tools/dashboards key off `app.kubernetes.io/instance`  | `annotation+label`              |
| Multiple Argo CD instances on one cluster              | `annotation` + `installationID` |
| Legacy v1.x cluster you can't re-sync                  | `label` (don't migrate live)    |

Switching modes (line 98): re-sync apps to apply. `label`→`annotation`
does not remove existing labels — they linger until resources are
recreated.

## Citation index

All paths relative to `argoproj/argo-cd` repo root:

- `docs/user-guide/best_practices.md` · `cluster-bootstrapping.md`
- `docs/operator-manual/applicationset/Generators-Git.md`
- `docs/operator-manual/{config-management-plugins,signed-release-assets,webhook}.md`
- `docs/user-guide/{source-hydrator,oci,private-repositories}.md`
- `docs/user-guide/{ci_automation,annotations-and-labels,tracking_strategies,resource_tracking}.md`
- `docs/user-guide/{helm,kustomize,multiple_sources,sync-waves,sync-options}.md`
