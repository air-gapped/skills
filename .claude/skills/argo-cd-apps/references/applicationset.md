# ApplicationSet reference

Argo CD v3.3 / v3.4 (May 2026). Citations under
`docs/operator-manual/applicationset/` of the `argoproj/argo-cd` repo.

## Contents

- [Generator picker](#generator-picker)
- [Top-level structure](#top-level-structure)
- [Template body](#template-body)
- [Generators](#generators)
- [Progressive Sync (`spec.strategy.rollingSync`)](#progressive-sync-specstrategyrollingsync)
- [Common pitfalls](#common-pitfalls)
- [See also](#see-also)

## Generator picker

| Intent                                            | Generator                  | One-line use                                                  |
|---------------------------------------------------|----------------------------|---------------------------------------------------------------|
| One App per managed cluster                       | `clusters`                 | Filter Argo-CD-known cluster Secrets by labels.               |
| One App per directory in a repo                   | `git` (directories)        | Cluster-add-ons monorepo; `apps/<env>/*` per-env layouts.     |
| One App per JSON/YAML file in a repo              | `git` (files)              | Self-service: devs commit `config.json` to a constrained repo.|
| Static list                                       | `list`                     | Small set of clusters/envs typed inline.                      |
| Cross-product of two generators                   | `matrix`                   | clusters × directories; envs × apps.                          |
| Merge by key                                      | `merge`                    | Base + per-cluster override values.                           |
| One App per repo in a GitHub/GitLab/Bitbucket org | `scmProvider`              | Auto-discover repos by topic/label/path filters.              |
| One App per open PR (preview envs)                | `pullRequest`              | Spin up `preview-<N>` namespaces; tear down on PR close.      |
| Data from a custom CR                             | `clusterDecisionResource`  | OCM / Karmada placement decisions.                            |
| Data from external HTTP service                   | `plugin`                   | RPC to your service when no built-in generator fits.          |

Source list: `Generators.md` lines 9–18.

## Top-level structure

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata: { name: my-appset, namespace: argocd }
spec:
  goTemplate: true                           # ALWAYS — default false uses deprecated fasttemplate
  goTemplateOptions: ["missingkey=error"]    # ALWAYS — fail loud on undefined keys
  generators:
    - list: { ... }
  template:                                  # Application spec with {{...}} substitutions
    metadata: { name: '{{.cluster}}-app' }
    spec:
      project: my-project                    # NEVER template — security boundary
      source: { ... }
      destination: { ... }
  syncPolicy:                                # AppSet ↔ Application reconcile (NOT App ↔ cluster)
    applicationsSync: create-update          # default: sync
    preserveResourcesOnDeletion: false
  strategy: { ... }                          # Progressive Sync — see end
  preservedFields:                           # ONLY annotations + labels — NOT spec fields
    annotations: ['my-custom-annotation']
    labels:      ['my-custom-label']
  ignoreApplicationDifferences:              # arbitrary spec fields — see MergePatch caveat
    - jsonPointers: ['/spec/source/targetRevision']
```

## Template body

### `goTemplate: true` + `missingkey=error` are mandatory

`GoTemplate.md` 39–45. Without `goTemplate`, fasttemplate (deprecated) is
used; without `missingkey=error`, undefined parameter references silently
become empty strings — Application names like `prod-`, garbage URLs.

Migration table (`GoTemplate.md` 200–211):

| fasttemplate                       | goTemplate                                    |
|------------------------------------|------------------------------------------------|
| `{{ cluster }}`                    | `{{ .cluster }}`                               |
| `{{ metadata.labels.my-label }}`   | `{{ index .metadata.labels "my-label" }}`      |
| `{{ path }}`                       | `{{ .path.path }}`                             |
| `{{ path.basename }}`              | `{{ .path.basename }}` (or `{{ base ... }}`)   |
| `{{ path[0] }}`                    | `{{ index .path.segments 0 }}`                 |

Sprig is available except `env`, `expandenv`, `getHostByName`. Plus custom
`normalize`, `slugify`, `toYaml`, `fromYaml`, `fromYamlArray`.

Hard limits (`GoTemplate.md` 52–112): string fields only — booleans/objects
can't be templated. No control flow across YAML fields — each field renders
independently. Templated `project` disables Git signature verification.
Workaround for non-string fields: `templatePatch`.

### Per-generator template overrides

A generator block can carry its own `template:`; merged onto the spec-level
template, overriding per-field.

```yaml
spec:
  generators:
    - list:
        elements:
          - { cluster: dev, url: https://kubernetes.default.svc }
        template:
          spec:
            source: { path: special-dev-path }      # overrides spec-level
  template:
    spec: { source: { repoURL: ..., path: default-path } }
```

Matrix and Merge **silently ignore** per-child `template:` overrides
(`Generators-Matrix.md` 367–375; `Generators-Merge.md` 192–200).

### `templatePatch` for last-mile fixes

`Template.md` 130–201. Use when the static template can't express what you
need — boolean fields, conditional sub-objects, `{{range}}` over a list. The
patch is a Go-templated string rendered then merged onto the template;
requires `goTemplate: true`.

```yaml
spec:
  goTemplate: true
  generators:
    - list:
        elements:
          - { cluster: dev, autoSync: true, prune: true,
              valueFiles: ['values.large.yaml', 'values.debug.yaml'] }
  template:
    metadata: { name: '{{.cluster}}-app' }
    spec:
      project: default
      source: { repoURL: https://github.com/example/manifests.git, targetRevision: HEAD, path: '{{.cluster}}' }
      destination: { server: https://kubernetes.default.svc, namespace: default }
  templatePatch: |
    spec:
      source:
        helm:
          valueFiles:
          {{- range $vf := .valueFiles }}
            - {{ $vf }}
          {{- end }}
    {{- if .autoSync }}
      syncPolicy:
        automated:
          prune: {{ .prune }}
    {{- end }}
```

Caveats: untrusted input + `templatePatch` = injection; pipe through
`toJson`. Empty `spec:` in patch *clears* fields under spec — don't write
empty blocks. `spec.project` is **not** patchable (`Template.md` 196).

### `preservedFields` — annotations + labels only

`Controlling-Resource-Modification.md`. Protects Application annotations and
labels written outside the AppSet (notifications controller, manual UI).

```yaml
spec:
  preservedFields:
    annotations: ['notifications.argoproj.io/subscriptions']
    labels:      ['team']
```

Notifications + refresh annotations are preserved by default. Global
setting via `ARGOCD_APPLICATIONSET_CONTROLLER_GLOBAL_PRESERVED_ANNOTATIONS`
/ `...PRESERVED_LABELS` (lines 328–331). For arbitrary spec fields use
`ignoreApplicationDifferences` (below) — `preservedFields` does NOT cover
them.

### `ignoreApplicationDifferences` — arbitrary spec fields

```yaml
spec:
  ignoreApplicationDifferences:
    - jsonPointers: ['/spec/syncPolicy']     # let users toggle auto-sync via UI
    - name: special-app
      jqPathExpressions: ['.spec.source.helm.values']
```

**MergePatch list-replacement caveat (known issue,
`argoproj/argo-cd#15975`).** When the ignored field is in a list (e.g.
`spec.sources[N].targetRevision`), changes elsewhere in the list cause the
entire list to be replaced — your "ignored" field is reset. Avoid putting
ignore rules on individual list elements when other list elements are
mutable.

### `applicationsSync` policy values

```yaml
spec:
  syncPolicy:
    applicationsSync: create-only       # sync (default) | create-only | create-update | create-delete
    preserveResourcesOnDeletion: true
```

| Value           | CREATE | UPDATE | DELETE |
|-----------------|--------|--------|--------|
| `sync` (default)| yes    | yes    | yes    |
| `create-only`   | yes    | no     | no     |
| `create-update` | yes    | yes    | no     |
| `create-delete` | yes    | no     | yes    |

Controller-level `--policy` flag overrides per-AppSet `applicationsSync`
unless `applicationsetcontroller.enable.policy.override` is set.
`create-only` blocks the **AppSet controller** from modifying/deleting; the
Application controller can still cascade-delete via `ownerReferences` when
the AppSet is deleted. To fully resist, also set
`resources-finalizer.argocd.argoproj.io` on the AppSet AND use
**background** cascading deletion. Foreground bypasses
(`Controlling-Resource-Modification.md` 35).

## Generators

### List

`Generators-List.md`. Hand-typed parameter sets.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - list:
        elements:
          - { cluster: dev,  url: https://k8s-dev.example.com,  env: dev }
          - { cluster: prod, url: https://k8s-prod.example.com, env: prod }
  template:
    metadata: { name: '{{.cluster}}-guestbook' }
    spec:
      project: my-project
      source: { repoURL: https://github.com/example/manifests.git, targetRevision: HEAD, path: 'envs/{{.env}}' }
      destination: { server: '{{.url}}', namespace: guestbook }
```

Parameters: every key in each `elements:` entry. `elementsYaml` form (List
inside Matrix child #2) reads YAML/JSON pulled by a preceding generator and
unfolds it as List elements.

Pitfall: legacy fasttemplate List requires `goTemplate: false` and
`{{cluster}}` (no leading dot). Don't mix syntaxes.

### Cluster

`Generators-Cluster.md`. One App per Argo-CD-known cluster.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - clusters:
        selector:
          matchLabels:
            env: prod
            argocd.argoproj.io/secret-type: cluster   # excludes default in-cluster
        values:
          revision: stable
  template:
    metadata: { name: '{{.nameNormalized}}-guestbook' }
    spec:
      project: prod
      source: { repoURL: https://github.com/example/k8s.git, targetRevision: '{{.values.revision}}', path: guestbook }
      destination: { server: '{{.server}}', namespace: guestbook }
```

Parameters per cluster: `name`, `nameNormalized` (DNS-safe), `server`,
`project`, `metadata.labels.<key>`, `metadata.annotations.<key>`, plus any
keys under `values:`. `flatList: true` produces ONE Application whose
template gets a `.clusters` array of all matching clusters.

Pitfalls: cluster Secrets MUST carry `argocd.argoproj.io/secret-type: cluster`
plus selector labels — without it, Argo CD doesn't recognize the Secret as
cluster credentials. Default in-cluster secret is auto-included unless
filtered on the secret-type label.

### Git (directories)

`Generators-Git.md`. One App per matching subdirectory.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - git:
        repoURL: https://github.com/example/cluster-addons.git
        revision: HEAD
        directories:
          - path: 'addons/*'
          - path: 'addons/legacy-*'
            exclude: true                       # exclude ALWAYS wins over include
        requeueAfterSeconds: 60                 # default 180s
  template:
    metadata: { name: '{{.path.basename}}' }
    spec:
      project: addons
      source: { repoURL: https://github.com/example/cluster-addons.git, targetRevision: HEAD, path: '{{.path.path}}' }
      destination: { server: https://kubernetes.default.svc, namespace: '{{.path.basename}}' }
      syncPolicy: { syncOptions: ['CreateNamespace=true'] }
```

Parameters per directory: `path.path`, `path.basename`,
`path.basenameNormalized`, `path.segments` (array). `pathParamPrefix: myrepo`
namespaces them as `myrepo.path.*`.

Pitfalls: **`path: 'dir/*'` does NOT recurse** — glob is `path.Match`, not
`**`. Two-deep needs `'dir/*/*'`, three-deep `'dir/*/*/*'`. For repo root,
`path: '*'` plus exclusions; `path: ''` matches nothing
(`Generators-Git.md` 173–206). `.`-prefixed dirs excluded by default. New
directory in repo = new Application automatically.

### Git (files)

`Generators-Git.md`. One App per matching file (parsed JSON/YAML).

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - git:
        repoURL: https://github.com/example/cluster-config.git
        revision: HEAD
        files:
          - path: 'cluster-config/**/config.json'
          - path: 'cluster-config/*/dev/config.json'
            exclude: true
  template:
    metadata: { name: '{{.cluster.name}}-guestbook' }
    spec:
      project: default
      source: { repoURL: https://github.com/example/manifests.git, targetRevision: HEAD, path: apps/guestbook }
      destination: { server: '{{.cluster.address}}', namespace: guestbook }
```

Parameters: every flattened JSON/YAML key (e.g. `cluster.name`,
`cluster.address`) plus `path.path`, `path.basename`,
`path.basenameNormalized`, `path.segments`, `path.filename`,
`path.filenameNormalized`. File globs DO recurse with `**` (unlike directory
globs).

Self-service pattern (`Use-Cases.md` 55–108): developers commit constrained
`config.json` files; admins control `project`, cluster, namespace via the
template. Polling default 3 min — set `requeueAfterSeconds: 60` or use the
AppSet webhook (`/api/webhook` on AppSet controller, GitHub + GitLab only).

### Matrix

`Generators-Matrix.md`. Cross-product of exactly two child generators.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - matrix:
        generators:
          - git:
              repoURL: https://github.com/example/addons.git
              revision: HEAD
              directories: [ { path: 'addons/*' } ]
          - clusters:
              selector: { matchLabels: { env: prod } }
  template:
    metadata: { name: '{{.path.basename}}-{{.name}}' }
    spec:
      project: addons
      source: { repoURL: https://github.com/example/addons.git, targetRevision: HEAD, path: '{{.path.path}}' }
      destination: { server: '{{.server}}', namespace: '{{.path.basename}}' }
```

Parameters: union of both children's parameters.

Limits (`Generators-Matrix.md` 355–423): exactly two children; combination
generators (matrix/merge) nestable ONCE only; consuming child must come
after producing child; identical key with conflicting values across children
→ error. **Two Git children require `pathParamPrefix:` on both** to
namespace conflicting `path.*` keys — see pitfall #10.

### Merge

`Generators-Merge.md`. Combine N child generators by `mergeKeys`; later
children override earlier on matching keys.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - merge:
        mergeKeys: [server]
        generators:
          - clusters:
              values: { kafka: 'true', redis: 'false' }                 # base
          - clusters:
              selector: { matchLabels: { use-kafka: 'false' } }
              values: { kafka: 'false' }                                 # per-cluster override
          - list:
              elements:
                - { server: https://prod.example.com, values.redis: 'true' }   # override one
  template:
    metadata: { name: '{{.name}}' }
    spec:
      project: '{{index .metadata.labels "environment"}}'
      source:
        repoURL: https://github.com/example/app.git
        targetRevision: HEAD
        path: app
        helm:
          parameters:
            - { name: kafka, value: '{{.values.kafka}}' }
            - { name: redis, value: '{{.values.redis}}' }
      destination: { server: '{{.server}}', namespace: default }
```

Limits: one generator per array entry; one level of nesting only;
non-matching parameter sets are **discarded** (intersection on unmatched).
**Nested merge keys (e.g. `values.selector`) are unsupported under
`goTemplate: true`** — only top-level keys can be merge keys when
go-templating (`Generators-Merge.md` 214–222). Pre-flatten in your
generators.

### SCMProvider

`Generators-SCM-Provider.md`. Auto-discover repos in
GitHub/GitLab/Gitea/Bitbucket(Server)/AzureDevOps/AWS-CodeCommit org.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - scmProvider:
        cloneProtocol: https
        github:
          organization: my-org
          allBranches: false
          excludeArchivedRepos: true
          tokenRef: { secretName: github-token, key: token }
          # GHE: api: https://ghe.example.com/api/v3
        filters:
          - repositoryMatch: '^myapp-'
            pathsExist: ['Chart.yaml']
            labelMatch: 'argocd-deploy'
  template:
    metadata: { name: '{{.repository}}' }
    spec:
      project: default
      source: { repoURL: '{{.url}}', targetRevision: '{{.branch}}', path: . }
      destination: { server: https://kubernetes.default.svc, namespace: '{{.repository}}' }
```

Parameters: `organization`, `repository`, `url`, `branch`,
`branchNormalized`, `sha`, `short_sha`, `labels` (GitHub topics, GitLab
tags). Filters AND within an entry; OR across entries. Provider keys also
exist for `gitlab`, `gitea`, `bitbucketServer`, `bitbucket`, `azureDevOps`,
`awsCodeCommit`.

Pitfalls: **token Secret must carry
`argocd.argoproj.io/secret-type: scm-creds`** for the AppSet controller to
recognize it. **GHE requires `api: https://ghe.example.com/api/v3`** —
without it, the call hits public github.com. Security: SCM generators
expose Secrets to whoever can author the AppSet; only admins should create
AppSets, and with templated `project`, only admins should be able to create
matching repos in the org.

### PullRequest

`Generators-Pull-Request.md`. One App per open PR — preview environments.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - pullRequest:
        requeueAfterSeconds: 1800             # default 30 min; prefer webhook
        github:
          owner: my-org
          repo: my-app
          tokenRef: { secretName: github-token, key: token }
          # GHE: api: https://ghe.example.com/api/v3
          labels: ['preview']
        filters:
          - branchMatch: '.*-preview$'
          - titleMatch: '^feat:'
        continueOnRepoNotFoundError: false
  template:
    metadata: { name: 'preview-{{.number}}' }
    spec:
      project: preview
      source:
        repoURL: https://github.com/my-org/my-app.git
        targetRevision: '{{.head_sha}}'
        path: deploy
      destination:
        server: https://kubernetes.default.svc
        namespace: 'preview-{{.number}}'
      syncPolicy:
        automated: { prune: true, selfHeal: true }
        syncOptions: ['CreateNamespace=true']
```

Parameters per PR (vary by provider): `number`, `branch`, `branch_slug`,
`target_branch`, `target_branch_slug`, `head_sha`, `head_short_sha`,
`labels`, `author`.

Pitfalls: same `scm-creds` Secret label and `api:` GHE base URL as
SCMProvider. **`continueOnRepoNotFoundError`** is the gnarly bit. Default
`false`: a 404 from the SCM puts the AppSet into a failed state — managed
Apps **may be deleted**. Setting `true` is sometimes correct in matrix
configs where some PR generators are legitimately optional, but: a 404 due
to revoked token will silently *not* delete preview environments, so they
outlive their PRs. Default `false` and let the AppSet fail loudly.

### ClusterDecisionResource

`Generators-Cluster-Decision-Resource.md`. Duck-typed: read a custom
resource that contains a list of cluster-name decisions (Open Cluster
Management `PlacementRule`, Karmada `ResourceBinding`, etc.).

```yaml
spec:
  goTemplate: true
  generators:
    - clusterDecisionResource:
        configMapRef: my-cdr-configmap
        name: my-placement-rule
        # OR labelSelector: { matchLabels: { duck: spotted } }
        requeueAfterSeconds: 60
  template:
    metadata: { name: '{{.clusterName}}-app' }
    spec:
      project: default
      source: { repoURL: https://github.com/example/app.git, targetRevision: HEAD, path: app }
      destination: { server: '{{.clusterName}}', namespace: default }
---
apiVersion: v1
kind: ConfigMap
metadata: { name: my-cdr-configmap, namespace: argocd }
data:
  apiVersion: apps.open-cluster-management.io/v1
  kind: placementrules
  statusListKey: decisions
  matchKey: clusterName
```

Parameters: every key under each item in the `statusListKey` list, accessed
via the `matchKey` field.

### Plugin (generator)

`Generators-Plugin.md`. RPC HTTP service that returns parameter objects.

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - plugin:
        configMapRef: { name: my-plugin-config }
        input:
          parameters:
            project: payments
            envs: ['dev', 'staging']
        values:
          owner: platform-team
        requeueAfterSeconds: 30
  template:
    metadata:
      name: '{{.app_name}}'
      annotations: { owner: '{{.values.owner}}' }
    spec: { project: '{{.project}}', source: { ... }, destination: { ... } }
```

Response shape: `{ output: { parameters: [ {...}, ... ] } }` — list of
arbitrary key maps which the template references.

Pitfalls: **the HTTP service must run somewhere reachable by the AppSet
controller**, with a Secret holding the token referenced by the
`configMapRef` ConfigMap (no direct URL on the generator). Plugin failures
behave like other generator failures — AppSet reconcile fails and managed
Apps don't update. Plan for the plugin's availability to gate App creation.

## Progressive Sync (`spec.strategy.rollingSync`)

`Progressive-Syncs.md`. **Beta** as of v3.3.0 (formal promotion in release
notes). Pre-v3.3 docs labeled it Alpha.

### Still must be enabled at the controller

Beta but not on by default. One of:

```yaml
# argocd-cmd-params-cm
data:
  applicationsetcontroller.enable.progressive.syncs: "true"
```

…or `--enable-progressive-syncs` flag, or env
`ARGOCD_APPLICATIONSET_CONTROLLER_ENABLE_PROGRESSIVE_SYNCS=true`.

### Worked example — dev → qa → prod

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata: { name: guestbook, namespace: argocd }
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - list:
        elements:
          - { cluster: dev,   url: https://1.2.3.4, env: env-dev }
          - { cluster: qa,    url: https://2.4.6.8, env: env-qa }
          - { cluster: prod1, url: https://9.8.7.6, env: env-prod }
          - { cluster: prod2, url: https://9.8.7.7, env: env-prod }
  strategy:
    type: RollingSync
    deletionOrder: Reverse                  # tear down prod before dev on AppSet delete
    rollingSync:
      steps:
        - matchExpressions:
            - { key: envLabel, operator: In, values: ['env-dev'] }
          # maxUpdate omitted ⇒ 100% — all matched at once
        - matchExpressions:
            - { key: envLabel, operator: In, values: ['env-qa'] }
          maxUpdate: 0                      # MANUAL gate — operator Sync via UI/CLI
        - matchExpressions:
            - { key: envLabel, operator: In, values: ['env-prod'] }
          maxUpdate: 10%                    # 10% at a time; floored at 1
  template:
    metadata:
      name: '{{.cluster}}-guestbook'
      labels: { envLabel: '{{.env}}' }      # MUST be on the *Application*, not the AppSet
    spec:
      project: my-project
      source: { repoURL: https://github.com/example/k8s.git, targetRevision: HEAD, path: 'guestbook/{{.cluster}}' }
      destination: { server: '{{.url}}', namespace: guestbook }
```

### Rules

- **`matchExpressions` matches against the *generated Application's*
  labels, not the generator output.** Set them in
  `template.metadata.labels`. Forgetting to template them is the #1
  RollingSync mistake.
- **RollingSync auto-disables auto-sync on managed Applications** even if
  the template asks for `automated: { ... }`. Warnings appear in
  applicationset-controller logs. Sync triggers come from the AppSet
  controller setting `operation` on each Application.
- `maxUpdate: 0` → manual gate; the step never proceeds without operator
  action.
- `maxUpdate: N` → absolute integer.
- `maxUpdate: N%` → fractional, rounds DOWN, **floored at 1** for `>0%`
  so progress is always made (`Progressive-Syncs.md` 86, 208). 10% of 2
  apps = 0.2 → 1, not 0.
- Apps not matching any step are **excluded** from the rolling sync —
  they stay in their pre-update state until manually synced.
- Healthy is the gate — each step waits until *all* matched apps reach
  `Healthy` before proceeding. Argo Rollouts and custom health checks
  participate.
- `deletionOrder: Reverse` (only valid with `type: RollingSync`) deletes
  apps in reverse step order on AppSet teardown; AppSet finalizer is
  auto-added.
- Sync windows on the project DO apply.

## Common pitfalls

1. **`goTemplate: false` (default) silently mishandles nested objects and
   ranges.** `{{.cluster}}` becomes literal text, ranges don't render,
   `index .metadata.labels "x"` is a syntax error. Always set
   `goTemplate: true` (`GoTemplate.md` 39–45).

2. **Templated `project:` is a security boundary issue.** Under
   Git/PR/SCM generators, anyone who can push a directory or open a PR
   can move the Application into a privileged project (`argocd`). Don't
   template `project`; pin a fixed value per AppSet
   (`Generators-Git.md` 5–11).

3. **`path: 'dir/*'` doesn't recurse — use `'dir/*/*'` for two-deep.**
   The glob is `path.Match`, not `**`. For repo root, `path: '*'` plus
   exclusions; `path: ''` matches nothing.

4. **`applyNestedSelectors` was REMOVED in v3.0** — the field is silently
   ignored. Nested selectors (selectors on child generators inside
   Matrix/Merge) are **always applied** as of v3.0.0. Pre-3.0 AppSets
   that relied on `applyNestedSelectors: false` need to remove the
   nested selectors before upgrading
   (`docs/operator-manual/upgrading/2.14-3.0.md` 156–182).

5. **Generator dry-run before applying** — always:

   ```bash
   argocd appset create -f appset.yaml --dry-run
   ```

   Surfaces template errors, missing keys, and the would-be Applications
   without touching cluster state.

6. **ApplicationSet finalizer must be in the template, not the AppSet
   metadata.** `resources-finalizer.argocd.argoproj.io` on the AppSet
   only protects the AppSet itself. To finalize *child Applications* on
   teardown, put the finalizer in `template.metadata.finalizers`. Pair
   with `applicationsSync: create-only` AND background cascading deletion
   for full deletion-resistance — foreground bypasses the protection.

7. **MergePatch list-replacement in `ignoreApplicationDifferences`.** When
   the ignored field is in a list (e.g.
   `spec.sources[N].targetRevision`), changes elsewhere in the list cause
   the entire list to be replaced; the "ignored" field is reset. Known
   issue `argoproj/argo-cd#15975`, unfixed.

8. **Cluster generator: cluster Secrets must have
   `argocd.argoproj.io/secret-type: cluster` and the right labels.**
   Without `secret-type: cluster`, Argo CD doesn't recognize the Secret
   as cluster credentials. Without the matchLabels you select on, the
   generator silently skips. Default in-cluster Secret is auto-included
   unless filtered by the secret-type label.

9. **Missing `goTemplateOptions: ["missingkey=error"]`.** A typo in a
   parameter reference renders as empty. Application gets a name like
   `prod-` (illegal) or destination URL `https://`. Always set it.

10. **Matrix generator with two Git generators needs `pathParamPrefix`.**
    Both children emit `path.path`, `path.basename`, etc. — Matrix errors
    "Identical key with conflicting value" or silently merges values. Set
    `pathParamPrefix:` on both children
    (`Generators-Matrix.md` 257–353):

    ```yaml
    - matrix:
        generators:
          - git: { ..., files: [...], pathParamPrefix: clusters }
          - git: { ..., directories: [...], pathParamPrefix: apps }
    ```

11. **PullRequest generator GHE requires `api: https://ghe.example.com/api/v3`.**
    Without it, the call hits public github.com and silently returns no
    PRs. Same shape applies to SCMProvider's `github:` block.

12. **SCMProvider/PullRequest token Secret label is `scm-creds`** —
    `argocd.argoproj.io/secret-type: scm-creds`. Bare token Secrets are
    not picked up.

13. **Nested merge keys break under `goTemplate: true`** — `mergeKeys:
    [values.selector]` works in fasttemplate; with `goTemplate: true`,
    Merge produces no output. Only top-level keys can be merge keys when
    go-templating (`Generators-Merge.md` 214–222). Pre-flatten.

14. **`continueOnRepoNotFoundError: true` is a footgun.** A 404 due to
    revoked token will silently *not* delete preview environments — they
    outlive their PR. Default `false`; only set `true` in matrix configs
    where some PR generators are legitimately optional.

15. **`preservedFields` only preserves annotations + labels.** Trying to
    put `/spec/syncPolicy` under `preservedFields: labels` does nothing.
    For arbitrary spec fields, use `ignoreApplicationDifferences` (with
    the MergePatch caveat).

## See also

- `docs/operator-manual/applicationset/Generators-Post-Selector.md` —
  post-filter generator output by labels.
- `docs/operator-manual/applicationset/Appset-Any-Namespace.md` — running
  AppSets in non-`argocd` namespaces.
- `docs/operator-manual/applicationset/Security.md` — admin-only AppSets,
  templated-project risk model.
- `docs/operator-manual/applicationset/Use-Cases.md` — cluster add-ons,
  monorepo, self-service.
- `docs/operator-manual/applicationset/Argo-CD-Integration.md` — webhook,
  observability, RBAC.
