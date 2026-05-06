# `Application` CR — author reference

Scope: every field of `argoproj.io/v1alpha1/Application` that authors touch.
ApplicationSet lives in `references/applicationset.md`. Sync deep-dive lives in
`references/sync.md`. Canonical full example lives in SKILL.md § Canonical
Application — not repeated here.

Path citations are relative to the `argoproj/argo-cd` repo root. Canonical
spec is `docs/operator-manual/application.yaml` (rendered into
`docs/user-guide/application-specification.md`).

---

## 1. `metadata`

### 1.1 `name`, `namespace`

**Rule.** Apps live in the `argocd` namespace by default. Other namespaces
work only if the operator added them to `application.namespaces` in
`argocd-cmd-params-cm`. Default install: only `argocd` — Apps elsewhere are
silently ignored. See `docs/operator-manual/applicationset/Appset-Any-Namespace.md`.

```yaml
metadata:
  name: payments-api
  namespace: argocd
```

### 1.2 Finalizers — three variants

**Rule.** Without a finalizer, deleting the App orphans its workloads.
`resources-finalizer.argocd.argoproj.io` enables cascading delete.

```yaml
metadata:
  finalizers:
    # (a) bare = foreground cascade. App stays Terminating until child
    # resources finish deleting. Safest. UI default for "delete with cascade".
    - resources-finalizer.argocd.argoproj.io
    # (b) /foreground — explicit form of (a). Same semantics.
    # - resources-finalizer.argocd.argoproj.io/foreground
    # (c) /background — App disappears immediately; resources deleted async.
    # Faster. Use for short-lived preview envs.
    # - resources-finalizer.argocd.argoproj.io/background
```

No finalizer = orphan-on-delete (equivalent to
`argocd app delete --cascade=false`). v3.2+ exposes Foreground / Background /
Non-Cascading consistently across App List and Resource Tree
(`docs/user-guide/app_deletion.md` 41–177).

---

## 2. `spec.project`

**Rule.** Always set `project` explicitly. Never rely on `default` in prod.
`default` permits every cluster, resource type, and repoURL — a
privilege-escalation vector when ApplicationSets template this field
(`docs/operator-manual/applicationset/Generators-Git.md` 5–11).

```yaml
spec:
  project: platform-prod   # must be a pre-existing AppProject in argocd ns
```

---

## 3. `spec.source` (single-source) — the union

**Rule.** `source` is a discriminated union. Argo picks the manifest tool by
what's present: `source.helm`, `source.kustomize`, `source.directory`,
`source.plugin`, or by `source.chart` being set, or by `repoURL` having
`oci://` prefix. Only one tool block per source is meaningful.

Common fields (`application.yaml` 21–27):

| Field | Meaning |
|-------|---------|
| `repoURL` | git URL, Helm repo URL, or `oci://...` URL. |
| `targetRevision` | branch / tag / commit SHA / OCI digest / Helm chart version (semver constraints OK for Helm). |
| `path` | path within repo. **Meaningless for Helm-repo charts; must be `.` for OCI.** |
| `chart` | Helm chart name. **Only** when `repoURL` is a Helm repo. Setting `chart` AND `path` is misconfiguration. |

---

## 4. `spec.destination`

**Rule.** Set exactly one of `server:` (cluster API URL) **or** `name:`
(cluster Secret name). Never both. `namespace:` only applies to namespace-scoped
resources whose manifest doesn't already set `metadata.namespace`.

```yaml
spec:
  destination:
    name: prod-eu-1            # OR server: https://...
    namespace: payments
```

In-cluster URL is `https://kubernetes.default.svc`. For multi-cluster GitOps
prefer `name:` so the API URL doesn't bake into manifests.

---

## 5. `spec.syncPolicy` (minimal)

**Rule.** Three independent knobs: `automated`, `syncOptions`, `retry`. Full
catalogue in `references/sync.md`. Minimal example:

```yaml
spec:
  syncPolicy:
    automated:
      enabled: true        # default true; set false to PAUSE without removing block
      prune: true          # default false — orphans deleted resources without it
      selfHeal: true       # default false — re-sync on out-of-band drift
      allowEmpty: false    # default false — refuse to prune to 0 resources
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
      - RespectIgnoreDifferences=true
    retry:
      limit: 5
      backoff: { duration: 5s, factor: 2, maxDuration: 3m }
```

`automated.enabled: false` is **not** equivalent to deleting the `automated`
block — the "pause" semantic only works while the field exists, so
`ignoreApplicationDifferences` on `/spec/syncPolicy/automated/enabled`
round-trips cleanly.

---

## 6. `spec.ignoreDifferences`

**Rule.** Skip drift detection on JSON paths or on fields owned by named field
managers. **Only affects diff display unless `RespectIgnoreDifferences=true`
is in `syncOptions`** — otherwise Argo still applies the field every sync,
re-creating the drift.

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers: [/spec/replicas]      # HPA-managed
    - kind: ConfigMap
      name: my-app                         # narrow by name+namespace
      namespace: prod
      jqPathExpressions: ['.data["config.yaml"]']
    - group: "*"
      kind: "*"
      managedFieldsManagers: [kube-controller-manager]
```

Slashes inside JSON keys must be encoded as `~1` in `jsonPointers`
(`docs/user-guide/diffing.md` 73–81).

---

## 7. `spec.revisionHistoryLimit`

**Rule.** Default 10. Set lower (e.g. 3) for high-churn apps to reduce CR
storage. Set 0 if rollbacks aren't needed. Don't increase above 10
(`application.yaml` 281–285 explicitly warns).

```yaml
spec:
  revisionHistoryLimit: 5
```

---

## 8. `spec.info`

**Rule.** Free-form key/value links shown in the App "Details" tab. Use it for
runbooks, dashboards, on-call channels.

```yaml
spec:
  info:
    - { name: Runbook,   value: 'https://wiki.example.com/runbooks/payments' }
    - { name: Dashboard, value: 'https://grafana.example.com/d/abc123' }
```

---

## 9. Source types

One minimal YAML per type. Comparison table at end.

### 9.1 Directory

Plain manifests, no templating. Triggered by `*.yaml`/`*.yml`/`*.json` in
`path`. (`docs/user-guide/directory.md`.)

```yaml
spec:
  source:
    repoURL: https://github.com/example/manifests.git
    targetRevision: HEAD
    path: deploy/prod
    directory:
      recurse: true
      include: '{*.yaml,*.yml}'         # multi-pattern: wrap in {}
      exclude: '{config.json,env-usw2/*}'
```

- `recurse: false` (default) loads only files at root of `path`.
- `exclude` always wins over `include`.
- Files marked `# +argocd:skip-file-rendering` are ignored — useful for
  `values.yaml` files coexisting with manifests.
- Directory apps **fail** if Helm/Kustomize/Jsonnet markers are present in
  `path`; no auto-fallback (`directory.md` 46–47).

### 9.2 Helm — three flavours

`docs/user-guide/helm.md`. Value precedence (low → high):
`valueFiles → values → valuesObject → parameters` (helm.md 398–408). Within
multiple `valueFiles`, the **last** file wins.

#### (a) Helm chart from a Helm repo

```yaml
spec:
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: prometheus              # chart name (NOT a path)
    targetRevision: 25.20.0        # chart VERSION
    helm:
      releaseName: prom            # explicit; see §10.5
      valueFiles: ['values-prod.yaml', 'envs/*.yaml']
      ignoreMissingValueFiles: true
      valuesObject: { replicaCount: 3 }            # preferred over `values:` string
      parameters:                                  # --set-style; HIGHEST precedence
        - { name: image.tag, value: '1.27.0' }
        - { name: existingSecret, value: my-secret, forceString: true }
```

#### (b) Helm chart from OCI

```yaml
spec:
  source:
    repoURL: oci://registry-1.docker.io/bitnamicharts/nginx   # oci:// prefix
    targetRevision: 18.0.0          # tag OR sha256:... digest (prefer digest)
    path: .                         # ALWAYS '.' for OCI Helm
    helm:
      valuesObject: { replicaCount: 2 }
```

Alt form (no `oci://`, repo configured with `--type helm --enable-oci`): omit
`oci://`, set `chart:`, no `path:`.

#### (c) Helm chart from git

```yaml
spec:
  source:
    repoURL: https://github.com/example/charts.git
    targetRevision: main
    path: charts/payments           # dir containing Chart.yaml
    helm:
      releaseName: payments
      valueFiles: ['values-prod.yaml']
```

Glob expansion uses `doublestar`; files sort lexically with later overriding
earlier (use `00-`, `10-`, `20-` prefixes if precedence matters). No-match
raises `ComparisonError` unless `ignoreMissingValueFiles: true`.

Helm gotchas:
- `randAlphaNum`-using charts are permanently OutOfSync — value re-renders
  every comparison. Pin via `parameters` or `argocd app set -p`.
- Helm hooks remap to Argo CD hooks via annotation. **If you define ANY Argo CD
  hooks, all Helm hooks are ignored** (helm.md 528).
- `install` and `upgrade` hooks both run on every sync — Argo doesn't track
  install state.
- Overriding `releaseName` breaks selectors keyed on
  `app.kubernetes.io/instance` — Argo overwrites that label with the App name.
  Workaround: change `application.instanceLabelKey` in `argocd-cm`.

### 9.3 Kustomize

Triggered by `kustomization.yaml` at `path`. (`docs/user-guide/kustomize.md`.)

```yaml
spec:
  source:
    repoURL: https://github.com/example/configs.git
    targetRevision: HEAD
    path: overlays/prod
    kustomize:
      namePrefix: prod-
      commonLabels: { team: platform }
      commonAnnotationsEnvsubst: true       # required for ${...} substitution
      commonAnnotations: { owner: '${ARGOCD_APP_NAME}' }
      images: ['my-app=registry.example.com/my-app:v2.3.1']
      replicas: [{ name: my-app-deployment, count: 4 }]
      components: [../component]            # path relative to source.path
      ignoreMissingComponents: true
      patches:
        - target: { kind: Deployment, name: my-app }
          patch: |-
            - op: replace
              path: /spec/template/spec/containers/0/image
              value: registry.example.com/my-app:v2.3.1
      namespace: custom-ns                  # OVERRIDES destination.namespace
```

- `kustomize.namespace` overrides `destination.namespace` for kustomize-set
  fields only (`kustomize.md` 289–296).
- Inline `patches` interpolate ApplicationSet generator parameters
  (`{{.name}}`).
- Helm-inside-Kustomize requires `--enable-helm` in `kustomize.buildOptions`
  of `argocd-cm` — operator-level, not per-App.
- Private remote bases inherit only the App's repo credentials; cannot use
  separate creds for other private repos.

### 9.4 Jsonnet (sub-mode of directory)

(`docs/user-guide/jsonnet.md`.)

```yaml
spec:
  source:
    repoURL: https://github.com/example/jsonnet-app.git
    path: environments/prod
    directory:
      jsonnet:
        extVars:
          - { name: app, value: $ARGOCD_APP_NAME }      # build-env vars OK
          - { name: replicas, value: "3", code: true }  # code:true → parse as Jsonnet
        tlas:
          - { name: ns, value: $ARGOCD_APP_NAMESPACE }
        libs: [vendor]                                  # repo-relative
```

`code: true` matters: without it the value is a Jsonnet string; with it the
value is parsed (`"true"` → boolean, `"[1,2,3]"` → array). TLAs are top-level
arguments to the entrypoint; extVars are global.

### 9.5 OCI bundle (non-Helm)

(`docs/user-guide/oci.md`.)

```yaml
spec:
  source:
    repoURL: oci://ghcr.io/my-org/manifests-bundle
    targetRevision: sha256:7b3e...   # digest preferred; tags can be moved
    path: .                          # always '.' for OCI
```

- Single-layer media-type `application/vnd.oci.image.layer.v1.tar+gzip` (or
  the helm content type). Custom types via
  `ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES` env on `argocd-repo-server`.
- OCI annotations (`org.opencontainers.image.title`, `.description`,
  `.version`, `.revision`, `.url`, `.source`, `.authors`, `.created`) surface
  in the UI.

### 9.6 Plugin (CMP)

cdk8s, tanka, terragrunt, kpt, custom templating.
(`docs/operator-manual/config-management-plugins.md`.)

```yaml
spec:
  source:
    repoURL: https://github.com/example/cdk8s-app.git
    targetRevision: HEAD
    path: app
    plugin:
      name: cdk8s-v1.0          # <plugin-name>-<plugin-version>; omit if discovery matches
      env: [{ name: STAGE, value: prod }]
      parameters:               # CMP plugin parameters (since v2.5)
        - { name: cdk8s-app, string: payments }
        - { name: extra-args, array: ['--debug'] }
        - { name: feature-flags, map: { ingress: 'true', tls: 'false' } }
```

- If `discover:` matches the repo, omit `plugin.name`.
- If the `ConfigManagementPlugin` declares `version:`, `plugin.name` MUST be
  `<name>-<version>` exactly. Mismatch → "no plugin found".
- CMPs run in the repo-server sidecar; `generate` must emit valid YAML/JSON
  on stdout.
- Plugins with non-deterministic output (random IDs, time-based templating,
  external lookups) are **incompatible with Source Hydrator** (§11).

### 9.7 Comparison table

| Type | Trigger | Pick when… |
|------|---------|-----------|
| directory | YAML/JSON files in `path` | plain manifests, no templating, dev/test |
| Helm | `Chart.yaml` at `path` OR `chart:` set | upstream/in-house charts; values-driven config |
| Kustomize | `kustomization.yaml` at `path` | overlay/patch a base; per-cluster patches via AppSet |
| Jsonnet | `*.jsonnet` under `path` | programmatic generation, libraries, env matrices |
| OCI | `oci://` prefix on `repoURL` | manifests/charts in an OCI registry, digest-pinned |
| Plugin (CMP) | `source.plugin` set or repo matches discovery | cdk8s, tanka, terragrunt, anything else |

---

## 10. Multi-source apps (`spec.sources`)

Source: `docs/user-guide/multiple_sources.md`. **Setting `sources` makes Argo
ignore `source` (singular)** — don't populate both (multiple_sources.md 9–10).

### 10.1 When to use

**Rule.** Use `spec.sources` for: combining an upstream Helm chart with
**values from a separate git repo**, OR overlaying an in-house manifest patch
on an external source. NOT for bundling unrelated apps — use App-of-Apps or
ApplicationSet for that. The doc literally says: *"If you find yourself using
more than 2-3 items in the `sources` array then you are almost certainly
abusing this feature."*

### 10.2 The `$values` ref-source pattern

**Rule.** Mark the values-bearing source with `ref: <name>`, then reference it
from the chart source's `valueFiles` as `$<name>/path/to/values.yaml`. The
`$ref` token MUST be the prefix of the value-file path (multiple_sources.md
76–79).

```yaml
spec:
  project: default
  destination: { server: https://kubernetes.default.svc, namespace: monitoring }
  sources:
    - repoURL: https://prometheus-community.github.io/helm-charts
      chart: prometheus
      targetRevision: 25.20.0
      helm:
        releaseName: prom-prod                # explicit; see §10.5
        valueFiles:
          - $values/charts/prometheus/values.yaml   # $values → ref-source root
    - repoURL: https://git.example.com/org/value-files.git
      targetRevision: dev
      ref: values
      # No `path:` — this source contributes ONLY values, no manifests.
```

Constraints (multiple_sources.md 84–88):
- A `ref:` source CANNOT also have `chart:` set.
- `$values` always resolves to ref-source ROOT, regardless of `path`. Use
  repo-relative paths in `valueFiles`.
- Setting `path:` on a `ref:` source makes Argo ALSO generate manifests from
  that path → duplicate manifests. Leave `path:` unset for pure-values sources.

### 10.3 Source ordering

**Rule.** Sources processed in declared order. **Later sources override
earlier on value resolution.** List base values first, overrides after.

### 10.4 Same-resource collisions

**Rule.** When two sources produce the same `(group, kind, name, namespace)`,
the **last source wins** and Argo emits `RepeatedResourceWarning`. Useful for
overriding a chart-rendered resource with a hand-written one
(multiple_sources.md 42–44).

### 10.5 Helm release-name collision pitfall

**Rule.** When two sources both render Helm and both default `releaseName` to
the App name, generated `app.kubernetes.io/instance` labels collide on every
shared resource → `RepeatedResourceWarning` everywhere. **Always set explicit
`helm.releaseName` per source** when multi-sourcing two charts.

```yaml
sources:
  - repoURL: https://charts.example.com
    chart: redis
    targetRevision: 19.0.0
    helm: { releaseName: payments-redis }     # explicit, NOT app name
  - repoURL: https://charts.example.com
    chart: postgresql
    targetRevision: 15.0.0
    helm: { releaseName: payments-postgres }  # explicit
```

---

## 11. `spec.sourceHydrator` — Alpha

**STATUS: Alpha as of v3.3.x.** Disabled by default. Enable via
`argocd-cmd-params-cm` `hydrator.enabled: "true"` (requires "commit server"
component) or use `*-install-with-hydrator.yaml` install manifests.
Source: `docs/user-guide/source-hydrator.md`.

For each Application, Argo CD renders the dry source and **commits the
hydrated manifests to a different branch of git** (the "wet" branch). The App
syncs from the wet branch. PRs from wet branch into `syncSource` branch gate
promotion. Solves audit ("what was actually applied"), PR-gated promotion,
branch-protection as ground truth.

### 11.1 Minimal + PR-gated forms

```yaml
spec:
  sourceHydrator:
    drySource:
      repoURL: https://github.com/my-org/my-app.git
      path: helm-app                          # un-rendered source
      targetRevision: HEAD
      helm:
        valueFiles: ['values-prod.yaml']
        parameters: [{ name: image.tag, value: v1.2.3 }]
        releaseName: my-app
    syncSource:
      targetBranch: environments/prod         # what Argo SYNCS from
      path: my-app-hydrated                   # MUST be non-root dir
    # Optional: PR-gated promotion. Hydrator pushes to prod-next; CI or a
    # human opens PR prod-next→prod; merge triggers the sync. Argo does NOT
    # create the PR itself.
    hydrateTo:
      targetBranch: environments/prod-next    # what hydrator PUSHES to
```

### 11.2 Repository secret label split

```yaml
labels: { argocd.argoproj.io/secret-type: repository }        # READ dry source
labels: { argocd.argoproj.io/secret-type: repository-write }  # WRITE hydrated
```

Both can use any auth method (PAT, SSH, GitHub App). Project-scoped repository
secrets only work if **all Apps writing to the same repo+branch are in the
same project**. Cross-project hydration to one repo requires a global write
secret (source-hydrator.md 128–139, 480–484).

### 11.3 Commit trailers (back-link to dry source)

```bash
git commit -m "Bump image to v1.2.3" \
  --trailer "Argocd-reference-commit-sha: $(git rev-parse HEAD)" \
  --trailer "Argocd-reference-commit-author: Author <author@example.com>" \
  --trailer "Argocd-reference-commit-subject: $(git show -s --format='%s')" \
  --trailer "Argocd-reference-commit-repourl: $(git remote get-url origin)" \
  --trailer "Argocd-reference-commit-date: $(git show -s --format='%aI')"
```

Trailers surface in `hydrator.metadata` JSON at the root of each hydrated
commit. Customise wet-commit message via `sourceHydrator.commitMessageTemplate`
in `argocd-cm` (Sprig + Go text/template).

### 11.4 Do NOT use the hydrator when

- Secrets injected at render time (Argo Vault Plugin, Helm SOPS) — rendered
  secrets would be committed to git. Use a destination-cluster secrets
  operator instead.
- Rendering is non-deterministic (`randAlphaNum`, `lookup`, unpinned chart
  deps, unpinned remote Kustomize bases, plugin reads of external state) —
  every reconcile produces a new commit forever.
- DRY-source signature verification needed — not currently supported. Hydrator
  commits are also not signed by Argo.
- You depend on `manifest-generate-paths` annotations — incompatible.

### 11.5 Best-practice rules

- `syncSource.path` MUST be non-root (source-hydrator.md 115–117). Hydrator
  cleans the configured path before writing — root would wipe CI / READMEs.
- Argo CD must be the ONLY writer to the wet branch. Enable branch protection.
- Hydration triggers only on new dry-source commits. Adding/removing Apps
  doesn't kick a run — push an empty commit if needed.
- Changing `syncSource.path` leaves the old dir orphaned. Same on App delete.

---

## 12. Common authoring gotchas

1. **Missing `targetRevision`.** Defaults to empty / "HEAD" depending on
   context; for Helm the resolved version is non-deterministic. For prod, pin
   to a commit SHA, semver tag, or OCI digest — not a moving branch.

2. **`path: '.'` edge cases.** Required for OCI sources. Valid for repo-root
   manifests, but with `directory.recurse: true` it walks the entire repo.
   `path` set on a Helm-repo source is silently ignored (`application.yaml` 24).

3. **`chart:` vs `path:` mistake.** Setting both is misconfiguration. Use
   `chart:` only when `repoURL` is a Helm repo (or OCI Helm repo configured
   with `--type helm --enable-oci`). Use `path:` for git-hosted charts.

4. **Helm release-name collisions in multi-source.** Two helm sources both
   defaulting `releaseName` to the App name → `RepeatedResourceWarning` on
   every shared resource. Set `helm.releaseName` explicitly per source (§10.5).

5. **Multi-source `$ref` quirks.** Setting `path:` on a `ref:` source makes
   Argo ALSO generate manifests from that path. Leave `path:` unset on
   pure-values sources. `$values` always resolves to the ref-source root
   regardless of `path`.

6. **OCI digest pinning.** Tags are mutable; digests are not. Prefer
   `targetRevision: sha256:...` for supply-chain integrity. The repo-server
   caches by revision, so digest pinning makes caching deterministic too.

7. **ServerSideApply migration on v3.3.0+.** Self-managed Argo CD apps fail
   sync with `Failed to perform client-side apply migration` after upgrade.
   Add `ServerSideApply=true` to `syncOptions` on the App that manages Argo
   CD itself. Temporary workaround: also `ClientSideApplyMigration=false`
   until `argoproj/argo-cd#26279` is fixed.

8. **`ignoreDifferences` without `RespectIgnoreDifferences=true`.** Diff says
   "synced" but Argo still applies the ignored field every sync, immediately
   re-creating drift. Add `syncOptions: [RespectIgnoreDifferences=true]`
   (`application.yaml` 239).

9. **Auto-sync `enabled: false` vs deleting `automated:`.** `enabled: false`
   keeps the field present so `ignoreApplicationDifferences` on
   `/spec/syncPolicy/automated/enabled` round-trips cleanly. Removing the
   block entirely round-trips badly when AppSets are involved.

10. **Namespace metadata via `managedNamespaceMetadata`.** No-op without
    `CreateNamespace=true` (`application.yaml` 243). Used for PSA labels,
    ownership annotations, NetworkPolicy selectors — Argo reconciles on each
    sync:

    ```yaml
    spec:
      syncPolicy:
        syncOptions: [CreateNamespace=true]
        managedNamespaceMetadata:
          labels:
            team: platform
            pod-security.kubernetes.io/enforce: baseline
          annotations: { owner: platform-team@example.com }
    ```

11. **Apps in non-`argocd` namespace.** Default install: only `argocd` ns
    works. Other namespaces need `application.namespaces` allowlist in
    `argocd-cmd-params-cm`. Without it, Apps in other namespaces are silently
    ignored.

12. **Forgetting `resources-finalizer.argocd.argoproj.io`.** Deleting the
    Application orphans its workloads. Add the bare finalizer for foreground
    cascade, or `/background` for fast async cleanup (§1.2).

13. **`destination` with both `server:` and `name:`.** Ambiguous — one or the
    other, never both. Prefer `name:` for multi-cluster GitOps.

14. **`revisionHistoryLimit` over 10.** Explicit warning in `application.yaml`
    281–285. Stick to default 10 or lower.

15. **`spec.project` left as `default` in prod.** Permits every cluster, every
    resource type. Privilege-escalation vector under templated AppSets. Always
    set an explicit `AppProject`.
