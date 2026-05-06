# Argo CD app authoring — troubleshooting reference

Field-medic guide for app authors. Symptom → cause → fix. Argo CD v3.3 / v3.4
(May 2026). Operator-side ops (HA, sharding) out of scope. Cited paths are
relative to `argoproj/argo-cd` repo root, mostly under `docs/`.

---

## 1. `argocd app diff` and `argocd app manifests`

`diff` = "what does Argo think differs **right now**".
`manifests` = "what *would* Argo apply if I synced now".

`docs/user-guide/commands/argocd_app_diff.md`. Exit codes: `0` = no diff,
`1` = diff found, `2` = error. `--diff-exit-code <N>` for CI to distinguish
"diff exists" from "CLI broke". `--exit-code=false` = display-only.

| Flag | Effect |
|------|--------|
| `--refresh` | Re-pull repo before diffing |
| `--hard-refresh` | Re-pull + invalidate cluster-state cache |
| `--server-side-diff` | SSA dry-run (mutating webhooks, default-value drift) |
| `--local <path>` | Diff cluster against local manifests |
| `--server-side-generate` | Send local files to repo-server for rendering parity |
| `--local-include "*.yaml"` | File filter for `--server-side-generate` |
| `--revision <rev>` | Diff a specific git revision (preview a PR) |
| `--ignore-normalizer-jq-execution-timeout 5s` | Bump JQ timeout |

### 1.1 `kustomize build` locally != `argocd app diff`

**Cause:** repo-server runs a different Kustomize/Helm version (pinned in
image), a CMP sidecar (SOPS, injected `commonLabels`), or build-env vars
(`ARGOCD_APP_*`, `KUBE_VERSION`) your local render lacks.

**Fix:** `argocd app diff myapp --local ./overlays/prod --local-repo-root . --server-side-generate`.

### 1.2 `argocd app manifests`

```bash
argocd app manifests myapp                      # rendered from git (default)
argocd app manifests myapp --source live        # live cluster state
argocd app manifests myapp --revision v1.2.3
argocd app manifests myapp --local ./path
```

`--source git` returns **rendered** (post Helm/Kustomize/CMP), not raw
YAML. Preview a candidate: `argocd app diff myapp --revision $SHA`.

### 1.3 Render-mismatch checklist (likelihood order)

1. Kustomize/Helm version skew — `kubectl exec -n argocd deploy/argocd-repo-server -- kustomize version`.
2. CMP plugin — `argocd app get myapp -o yaml | yq '.spec.source.plugin'`.
3. Build-env vars — chart references `ARGOCD_APP_*`.
4. `app.kubernetes.io/instance` collision (§3.7).
5. Multi-source / `ref` source feeding values — only `--server-side-generate` reproduces.

---

## 2. Refresh, hard-refresh, `manifest-generate-paths`

Sources: `operator-manual/reconcile.md`, `user-guide/annotations-and-labels.md`,
`operator-manual/high_availability.md`.

### 2.1 Three cache layers

1. **Repo-server manifest cache** — keyed by repo URL + commit SHA + path + parameters.
2. **Cluster-state cache** — what application-controller thinks is in the cluster.
3. **Application-level reconcile cache** — drives OutOfSync calculation.

### 2.2 Refresh flavors

| Op | Effect | When |
|----|--------|------|
| `--refresh` (or annotation `refresh=normal`) | Re-query git, re-eval sync; manifest cache reused if SHA unchanged | After PR merge — skip the ~3-min jitter wait |
| `--hard-refresh` (or `refresh=hard`) | Invalidate manifest + cluster-state caches; re-render, re-compare | Helm dep bumped at stable SHA; `Manifest generation error (cached)`; cluster state stale |

Lingering `argocd.argoproj.io/refresh` annotation = controller backpressured.

### 2.3 `manifest-generate-paths` — monorepo win

`high_availability.md` 327-440.

**Symptom:** 100-app monorepo, someone touches `apps/foo/`, **every** app
re-renders. Repo-server CPU saturates.

**Cause:** manifest cache key = commit SHA. New commit invalidates cache for
every app pointing at that repo.

**Fix:** declare the paths the app depends on; if untouched, cache reused.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/manifest-generate-paths: .             # relative to spec.source.path
    # ".;../shared"                                           # multiple, semicolon-separated
    # "/apps/guestbook;/shared"                               # absolute from repo root
    # "/shared/*-secret.yaml"                                 # glob (Go filepath.Match)
```

- **v2.11+ works without webhooks.**
- Only helps when multiple apps share one repo.
- External Helm `valueFiles` from a ref source bypass this.
- Webhook path matching: GitHub, GitLab, Gogs only.
- **Trap — too narrow breaks rendering.** Only resources matched by the
  annotation are sent to the CMP server. Wrong glob = silently missing
  resources, not just slower reconciles.

Win metrics: `argocd_webhook_requests_total{repo}`,
`argocd_webhook_store_cache_attempts_total{repo,successful}`.

---

## 3. Top OutOfSync drivers

Sources: `user-guide/diffing.md`, `diff-strategies.md`, `sync-options.md`,
`faq.md`.

### 3.1 Mutating webhook adds fields (Linkerd, Istio, kyverno)

**Symptom:** diff shows fields you didn't author — Istio sidecars,
kyverno-injected labels, operator-patched `imagePullSecrets`. Resync doesn't
help; webhook re-mutates.

**Fix A — `ServerSideDiff=true` (preferred, stable v3.1+).** SSA dry-run, so
mutation isn't drift. Default *excludes* mutation webhooks from diff.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/compare-options: ServerSideDiff=true
```

> **Do not** set `IncludeMutationWebhook=true` post-CVE-2026-42880.

**Fix B — `ignoreDifferences` with `managedFieldsManagers`** when SSA
dry-run is blocked or per-app control needed:

```yaml
spec:
  ignoreDifferences:
    - group: '*'
      kind: '*'
      managedFieldsManagers: [istio-sidecar-injector, kyverno-admission-controller]
```

Caveat (`faq.md` §`field not declared in schema`): static k8s schema can lag
the cluster's; on that error, drop the option, drop SSA, or upgrade.

### 3.2 Server-side defaults rendered into the live object

**Symptom:** wrote `spec.replicas: 3`; live has `spec.strategy.type:
RollingUpdate`, `maxSurge: 25%` — API-server-filled defaults. Legacy 3-way
diff treats them as drift.

**Fix:** `ServerSideDiff=true`. SSA tracks per-field ownership; defaults
owned by `kube-apiserver` are excluded from the controller's diff.

### 3.3 `kubectl` field-manager wars

**Symptom:** someone ran `kubectl edit` / `kubectl apply` directly. Fields
split between `kubectl-client-side-apply` and `argocd-controller`. Resource
flips OutOfSync.

**Fix:** SSA + client-side-apply migration (default).

```yaml
spec:
  syncPolicy:
    syncOptions:
      - ServerSideApply=true
      # ClientSideApplyMigration=true is the default
```

On next sync, ownership transfers to `argocd-controller`. Target a specific
decommissioned manager:
`argocd.argoproj.io/client-side-apply-migration-manager: 'my-old-operator'`.

### 3.4 HPA changes `spec.replicas`

**Symptom:** HPA scales 3→7, git says 3, app OutOfSync. With `selfHeal:
true`, infinite war (§9).

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers: ["/spec/replicas"]
  syncPolicy:
    syncOptions: [RespectIgnoreDifferences=true]
```

Without `RespectIgnoreDifferences=true`, the field is ignored at *diff* time
but re-applied on every sync, briefly stomping HPA. System-wide variant:
`resource.customizations.ignoreDifferences.apps_Deployment` in `argocd-cm`.

### 3.5 cert-manager rewriting Ingress annotations

**Symptom:** `acme.cert-manager.io/http01-edit-in-place` or
`tls[*].secretName` drift back on every refresh.

```yaml
spec:
  ignoreDifferences:
    - group: networking.k8s.io
      kind: Ingress
      managedFieldsManagers: [cert-manager, cert-manager-controller]
```

Per-annotation form:
`jqPathExpressions: ['.metadata.annotations["acme.cert-manager.io/http01-edit-in-place"]']`.

### 3.6 Operator-managed sub-resources (Knative, Crossplane composite)

**Symptom:** you deploy a CR; the operator creates `StatefulSet`/`Service`/
etc. Argo treats them as orphaned or as drift.

**Fix:** don't ship the sub-resources. If you must:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/compare-options: IgnoreExtraneous
```

Combine with `RespectIgnoreDifferences=true` for fields the operator writes
back. `IgnoreExtraneous` affects sync-status only — degraded **health**
still degrades the app.

### 3.7 `app.kubernetes.io/instance` label collision

`faq.md` §"Why Is My App Out Of Sync Even After Syncing?".

**Symptom:** OutOfSync after sync, no obvious diff. Kustomize `commonLabels`
or a Helm chart sets `app.kubernetes.io/instance`.

**Cause:** Argo's default tracking label is the same; auto-injected after
render → live state flickers.

**Fix:** v3.0+ default is annotation-based already. On older clusters set
`application.instanceLabelKey: argocd.argoproj.io/instance` in `argocd-cm`.
Multi-tenant Argo CD installs sharing a cluster: use `installationID` to
scope tracking per-instance. Per docs, "applications will become out of sync
and will need re-syncing" after switching tracking method.

### 3.8 Resource-limit / unit normalization

`faq.md` 187-200. `'1000m'`→`'1'`, `'0.1'`→`'100m'`, `'3072Mi'`→`'3Gi'`,
`8760h`→`8760h0m0s`.

**Fix A:** `ServerSideDiff=true` (cleanest). **Fix B:** declare known-types
for CRDs that re-use core types:

```yaml
# argocd-cm
data:
  resource.customizations.knownTypeFields.argoproj.io_Rollout: |
    - field: spec.template.spec
      type: core/v1/PodSpec
```

First-class types (`Deployment` etc.) are handled automatically.

### 3.9 Status-in-git footgun (operators that set spec from status)

Some teams commit `status:`. Argo diffs status on CRDs by default and
fights forever.

```yaml
# argocd-cm
data:
  resource.compareoptions: |
    ignoreResourceStatusField: crd     # 'crd' (recommended), 'all' (default), 'none'
```

### 3.10 `IncludeMutationWebhook=true` — DO NOT USE

Post-CVE-2026-42880. Default ServerSideDiff already excludes webhook output
— that's the right behavior.

---

## 4. `SyncFailed` / hook failures

Source: `user-guide/sync-waves.md` 41-78.

### 4.1 Read the failure

`argocd app get myapp --show-operation` shows failed resources with kubectl
errors, hooks that ran, phase, exit status. Example:

```
PHASE      | Running
MESSAGE    | waiting for completion of hook batch/Job/ingress-nginx-admission-create
KIND       | batch/v1/Job          STATUS | Running   HOOK | PreSync
MESSAGE    | Pending deletion
```

"Pending deletion" usually = previous Job's pod finalizer didn't release.

### 4.2 The `generateName` + `BeforeHookCreation` Job leak

| Policy | Deletes when |
|--------|--------------|
| `HookSucceeded` | After hook succeeds |
| `HookFailed` | After hook fails |
| `BeforeHookCreation` (default) | Just before next run creates a new one |

**Symptom:** namespace fills with `db-migrate-xxxxx` Jobs over weeks; quotas
blocked.

**Cause:** `metadata.generateName: db-migrate-` + `BeforeHookCreation`. Each
run is a fresh name; the "previous" hook with that name doesn't exist, so
nothing is deleted. Per docs: "It is meant to be used with `/metadata/name`."

**Fix:** fixed `metadata.name` + `BeforeHookCreation`, OR `HookSucceeded`,
OR `ttlSecondsAfterFinished`:

```yaml
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  ttlSecondsAfterFinished: 360
```

"Cleanup-on-success but keep failed for forensics" =
`hook-delete-policy: HookSucceeded`.

### 4.3 PreSync needs the namespace

**Symptom:** PreSync fails with `namespaces "foo" not found` (PreSync runs
*before* Sync, where your Namespace manifest applies).

```yaml
spec:
  destination:
    namespace: my-app
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

Combine with `managedNamespaceMetadata` for labels (PSA enforcement).
If the app *also* contains a `Namespace` manifest of the same name, that
manifest's metadata wins.

### 4.4 `Skip` — make Argo ignore Helm-rendered hooks

A chart you don't control creates a Job that fights Argo's hook semantics
(canonical: ingress-nginx admission Job).

```yaml
ingress-nginx:
  controller:
    admissionWebhooks:
      annotations:
        argocd.argoproj.io/hook: Skip
```

`Skip` = "don't apply this". Helm's own hook machinery still runs.

### 4.5 PreDelete / PostDelete hooks (v3.3+)

PreDelete runs before app deletion (only on `argocd app delete`, not
prune). PostDelete runs after all resources are deleted. Either failing
leaves `DeletionError` on the app CR. Use for: S3/DNS/Vault cleanup, queue
draining, notifications.

---

## 5. `ComparisonError` — six sub-causes

`troubleshooting.md`, `helm.md`, `faq.md`. Status condition meaning
"something blew up while figuring out the desired state" — pre-sync.

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 5.1 | `ssh: handshake failed`, `x509: certificate signed by unknown authority` | Repo unreachable: creds, TLS, host blocked | SSH host key → `argocd-ssh-known-hosts-cm`; TLS → `argocd-tls-certs-cm`; auth → `argocd repo add` rotated |
| 5.2 | `rpc error: code = DeadlineExceeded` | CMP timeout | Operator: bump `argocd-cmd-params-cm`. Author: split app, use `manifest-generate-paths` |
| 5.3 | `helm dep build: chart "foo" version "1.2.3" not found` | `helm dependency update` not run; OCI dep needs creds; version gone | Register repo (`argocd repo add --type helm` or `--enable-oci` + creds); commit `Chart.lock` + `charts/`; pin a version that exists |
| 5.4 | `values file glob "envs/prod/*.yaml" matched no files` | `valueFiles` glob expanded to nothing (`helm.md` 301-323) | `ignoreMissingValueFiles: true` (below) |
| 5.5 | `RUNTIME ERROR: Top-level argument 'env' not provided` | Jsonnet expects TLAs your app spec doesn't supply | Set `directory.jsonnet.tlas` (below) |
| 5.6 | `The order in patch list … doesn't match $setElementOrder list:` (`faq.md` 272-307) | Duplicate keys in a list — usually `env:` arrays with same `name`, different value | Dedupe |

```yaml
# 5.4
source:
  helm:
    valueFiles: [envs/*.yaml]
    ignoreMissingValueFiles: true

# 5.5
source:
  directory:
    jsonnet:
      tlas:
        - { name: env, value: prod }
        - { name: region, value: us-west-2 }
      extVars:
        - { name: someVar, value: someValue }
```

### Diagnostic recipe

```bash
argocd app get myapp -o yaml | yq '.status.conditions'
argocd app get myapp --hard-refresh                                    # bypass cached error
kubectl logs -n argocd deploy/argocd-repo-server --tail=500 | grep myapp
kubectl logs -n argocd deploy/argocd-repo-server -c <plugin> --tail=500
```

---

## 6. App stuck deleting

`app_deletion.md`, `cluster-bootstrapping.md`.

### 6.1 The finalizer

```yaml
metadata:
  finalizers:
    - resources-finalizer.argocd.argoproj.io           # foreground (default)
    # - resources-finalizer.argocd.argoproj.io/background
```

`argocd app delete --cascade` adds it. Controller removes the finalizer
**after the cascade completes**. Foreground waits for cascade before the
app CR disappears; background removes the CR immediately and lets GC clean
up async.

### 6.2 Stuck states

**Symptom:** `kubectl get app myapp -n argocd` shows `deletionTimestamp`,
finalizer still present. Causes:

1. Cascading delete blocked — child has its own k8s finalizer (PVC
   storage-class, cert-manager Certificate, operator CR) and the owning
   controller is gone or stuck.
2. PreDelete hook failing — app stays deleting with `DeletionError`.
3. Cluster unreachable.
4. Repo unreachable (`faq.md`) — Argo can't generate manifests, doesn't
   know what to delete. Use `--cascade=false`.

### 6.3 Diagnose

```bash
kubectl get app myapp -n argocd -o yaml | yq '.metadata.finalizers,.status.conditions'
kubectl get all,pvc,certificates,issuers -A -l app.kubernetes.io/instance=myapp
kubectl logs -n argocd statefulset/argocd-application-controller --tail=200 | grep myapp
```

### 6.4 Manual cleanup

Fix the *child* finalizer first:

```bash
kubectl patch pvc <name> -n <ns> --type=merge -p '{"metadata":{"finalizers":null}}'
```

Or abandon cascade: `argocd app delete myapp --cascade=false`.

> **Only patch the App's finalizer to null AFTER confirming cascade is
> done** — early = leak resources Argo will no longer track.

```bash
kubectl get all,pvc,configmap,secret -A -l app.kubernetes.io/instance=myapp   # confirm empty
kubectl patch app myapp -n argocd --type=merge -p '{"metadata":{"finalizers":null}}'
```

`--cascade=false` is also the "stop managing but keep workloads" pattern.
`--propagation-policy background` for fast cascades when one dependency is
known-stuck.

---

## 7. ApplicationSet not generating expected children

Sources: `applicationset/Controlling-Resource-Modification.md`,
`GoTemplate.md`, `Application-Deletion.md`.

### 7.1 Generator dry-run + inspect

```bash
argocd appset create --dry-run ./appset.yaml -o json | jq -r '.status.resources[].name'
argocd appset generate ./appset.yaml -o yaml          # render apps standalone
argocd appset get my-appset -o yaml | yq '.status'    # generator output + reconcile errors
```

`appset generate` works whether the AppSet exists or not.

### 7.2 `applicationsSync` policy table (v3.x)

| Policy | Create | Update | Delete |
|--------|:------:|:------:|:------:|
| `create-only` | yes | no | no |
| `create-update` | yes | yes | no |
| `create-delete` | yes | no | yes |
| `sync` (default) | yes | yes | yes |

```yaml
spec:
  syncPolicy:
    applicationsSync: create-update
```

Older `policy:` field still works; `applicationsSync` preferred in v3.x.
Controller `--policy` flag overrides per-AppSet unless
`applicationsetcontroller.enable.policy.override: 'true'`.

> **Caveat:** `create-only` / `create-update` do **not** prevent
> `ownerReferences`-driven deletion when the AppSet itself is deleted. Add
> a finalizer + `preserveResourcesOnDeletion: true`:
>
> ```yaml
> metadata:
>   finalizers: [resources-finalizer.argocd.argoproj.io]
> spec:
>   syncPolicy:
>     applicationsSync: create-update
>     preserveResourcesOnDeletion: true
> ```

### 7.3 `preservedFields` — keep author-added annotations

**Symptom:** human added an annotation to a child Application; controller
wipes it on next reconcile.

```yaml
spec:
  preservedFields:
    annotations: ["my-custom-annotation", "deployment.kubernetes.io/revision"]
    labels: ["my-custom-label"]
```

Globally: `ARGOCD_APPLICATIONSET_CONTROLLER_GLOBAL_PRESERVED_ANNOTATIONS` /
`...GLOBAL_PRESERVED_LABELS`. Argo's own refresh/notification annotations
preserved by default.

### 7.4 `goTemplate: true` silent-empty traps

Default = fasttemplate (`{{name}}`). `goTemplate: true` = `text/template`
(`{{ .name }}`). Switching renders silently empty when: missing leading dot;
no `missingkey=error` (undefined → `<no value>`); templating non-string
fields (booleans, lists not supported).

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  template:
    metadata:
      name: 'app-{{ .name }}-{{ cat .branch | slugify 23 }}'
```

`slugify` and `normalize` clean DNS-1123 violations from generator values.

### 7.5 `ignoreApplicationDifferences` MergePatch limitation

**Symptom:** ignore `/spec/syncPolicy.automated` per-app to allow temporary
toggles, but any other AppSet template change replaces the whole `sources`
list and your toggle is lost.

**Cause:** AppSet generates a **MergePatch** — "existing lists are
completely replaced" on any element change.
([argo-cd#15975](https://github.com/argoproj/argo-cd/issues/15975) tracks
StrategicMergePatch.)

**Workaround:** don't put ignored fields in lists. For auto-sync toggle, use
the scalar `spec.syncPolicy.automated.enabled: false`.

---

## 8. Sync waves not advancing

Source: `sync-waves.md` 100-134.

Mental model: PreSync → Sync → PostSync, then `sync-wave` integer (lowest
first), then kind, then name. Apply wave N → **wait for Healthy** → apply
wave N+1. The wait is the trap.

### 8.1 Always-Healthy Lua footgun

**Symptom:** PostSync never runs even after Sync completes; UI shows the
resource Healthy yet next wave doesn't fire — or wave-0 resource is
Progressing forever. Causes:

1. Genuinely unhealthy (StatefulSet unschedulable, ImagePullBackOff).
2. Custom Lua health missing → unknown CRD = Progressing forever.
3. **Lua that always returns Healthy** — wave advances before the operator
   has actually reconciled. Subsequent waves see missing dependencies and
   fail.

```yaml
# WRONG — always-Healthy
resource.customizations.health.foo.io_Bar: |
  hs = {}
  hs.status = "Healthy"
  return hs
```

```lua
-- RIGHT — read .status.conditions
hs = {}
if obj.status ~= nil and obj.status.conditions ~= nil then
  for i, c in ipairs(obj.status.conditions) do
    if c.type == "Ready" and c.status == "True" then
      hs.status = "Healthy"; hs.message = c.message; return hs
    end
  end
end
hs.status = "Progressing"; return hs
```

4. **Ingress** stuck Progressing (`faq.md` 17-46): Contour, older Traefik
   don't populate `status.loadBalancer.ingress`. Fix the controller
   (`publishedService.enabled: true` for Traefik) or relax Lua.
5. **StatefulSet** stuck Progressing — `status.updatedReplicas` not set in
   old k8s. Upgrade or relax health check.
6. **SealedSecret** stuck Progressing — old controller doesn't set status.
   `faq.md` 261-270 ships a ready Lua override.

### 8.2 Pruning order (v3.3+)

> During pruning, wave order is reversed. Higher waves are pruned first.

Wave 5 Deployment goes before wave -1 Namespace on prune. Useful when CRDs
are at low waves and CRs at high — CRs prune first.

---

## 9. Auto-sync looping

Source: `auto_sync.md`.

`selfHeal: true` + a mutating controller = infinite sync. HPA case (§3.4):
HPA scales 3→7, app OutOfSync, self-heal (5s default), Argo scales back to
3, HPA scales up — forever. application-controller CPU climbs.

**Diagnose:**

```bash
argocd app history myapp                        # sync after sync at same SHA = smell
argocd app get myapp --show-operation
kubectl logs -n argocd statefulset/argocd-application-controller --tail=500 \
  | grep -E "(Initiating|Syncing).*myapp"
# "Initiating self-heal sync" repeating every few seconds = the loop.
```

Also grep `argocd_app_sync_total{name="myapp"}` on the Prometheus scrape:
high rate at fixed SHA = self-heal loop.

**Fix A (preferred) — `ignoreDifferences` + `RespectIgnoreDifferences=true`**:

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers: ["/spec/replicas"]
  syncPolicy:
    automated: { selfHeal: true }
    syncOptions: [RespectIgnoreDifferences=true]
```

Self-heal still triggers for *real* drift; HPA wins on replicas.

**Fix B (cruder) — `selfHeal: false`** (or omit). Only enable self-heal when
you know what you're protecting against and have ironed out per-field
exceptions.

**Semantics quick-ref** (`auto_sync.md` 134-148):

- `selfHeal` re-syncs on drift; without it, drift just shows OutOfSync.
- Auto-sync runs only if app is OutOfSync.
- Once per (commit SHA, parameters), unless `selfHeal: true`.
- With `selfHeal`: retry every `--self-heal-timeout-seconds` (5s default).
- Failed (SHA, params) isn't retried unless `retry.refresh: true`.
- **Rollback is disabled** while auto-sync is on.
- `spec.syncPolicy.automated.enabled: false` pauses while preserving
  `prune`/`selfHeal`/`allowEmpty` config.

---

## 10. Performance — author-side knobs

| Annotation / option | Where | What |
|--------------------|-------|------|
| `manifest-generate-paths: <list>` | App annotation | §2.3, monorepo |
| `argocd.argoproj.io/ignore-resource-updates: 'true'` | Untracked resource (CronJob template etc.) | Stop reconciling on noisy sub-object updates (`reconcile.md` 127-178) |
| `ApplyOutOfSyncOnly=true` | App syncOptions | Many-object apps; only OutOfSync resources applied; hooks still run, history recorded (`sync-options.md` 164-194) |
| `argocd.argoproj.io/skip-reconcile: 'true'` (Alpha) | App or cluster Secret | Argo ignores entirely until removed; for incident freezes / debugging. On a cluster Secret skips reconcile for **all** apps targeting that cluster |

```yaml
apiVersion: batch/v1
kind: CronJob
spec:
  jobTemplate:
    metadata:
      annotations: { argocd.argoproj.io/ignore-resource-updates: 'true' }
    spec:
      template:
        metadata:
          annotations: { argocd.argoproj.io/ignore-resource-updates: 'true' }
```

For tracked resources, use
`resource.customizations.ignoreResourceUpdates.<group>_<Kind>` in
`argocd-cm` (operator-side; default on).

---

## 11. "I deleted it from git, why is it still in the cluster"

Sources: `auto_sync.md` 38-75, `sync-options.md` 7-69. Checklist, in order:

1. **`prune` defaults to `false` on `automated`.** `automated: {}` is
   auto-sync *without* prune — intentional safety. Fix:
   `automated: { prune: true }` or `argocd app set myapp --auto-prune`.
   Force the cycle: `argocd app sync myapp --prune`.
2. **App-level `Prune=false`** syncOption disables prune for the whole app.
3. **App-level `Delete=false`** syncOption (v3.3+) — Argo refuses to delete
   the resource on app deletion (e.g. preserve PVCs across re-deploys).
4. **`Prune=confirm` per-resource** blocks until manual confirmation:

   ```yaml
   metadata:
     annotations:
       argocd.argoproj.io/sync-options: Prune=confirm
   ```

   Confirm in UI or
   `kubectl annotate app myapp argocd.argoproj.io/deletion-approved=$(date -Iseconds)`.
5. **Resource-level `Prune=false` overrides app-level prune.** Per docs:
   "setting a Prune sync option on the resource will always override a
   Prune sync policy defined in the Application." Check:
   `kubectl get <kind> <name> -n <ns> -o yaml | yq '.metadata.annotations'`.
6. **Kubernetes finalizer not progressing** on the resource (PVC
   storage-class, cert-manager Certificate, operator CR). Argo issued the
   delete; k8s waits on a controller. Fix the controller, or patch the
   resource finalizer manually.
7. **`allowEmpty: false`** — auto-prune refuses to leave an app with zero
   resources. Set `automated: { prune: true, allowEmpty: true }` only if
   you really want the app to evaporate.

`PruneLast=true` ("drain first"): pruning happens after all other resources
deploy and become healthy. Useful when prune depends on the new resources
being up (removing an old Service after traffic cuts over).

---

## 12. CLI cheat sheet — 15 commands

`docs/user-guide/commands/argocd_app*.md`, `argocd_appset*.md`. Frequency
order:

```bash
# 1. Inspect
argocd app get myapp                            # quick status
argocd app get myapp -o yaml | yq '.status'     # full status
argocd app get myapp --output tree              # resource tree

# 2. Diff
argocd app diff myapp
argocd app diff myapp --server-side-diff        # mutating-webhook clusters
argocd app diff myapp --revision $SHA           # candidate revision

# 3. Manifests
argocd app manifests myapp                      # rendered (default --source git)
argocd app manifests myapp --source live        # live cluster state

# 4. Refresh
argocd app get myapp --refresh                  # re-pull git
argocd app get myapp --hard-refresh             # invalidate caches

# 5. Sync
argocd app sync myapp
argocd app sync myapp --prune
argocd app sync myapp --dry-run
argocd app sync myapp --apply-out-of-sync-only
argocd app sync myapp --resource :Service:web   # selective
argocd app sync myapp --revision $SHA

# 6. Wait
argocd app wait myapp                           # Healthy + Synced
argocd app wait myapp --sync --timeout 600

# 7. List
argocd app list -l team=platform
argocd app list -p my-project -o name

# 8. Operation control
argocd app terminate-op myapp                   # cancel running sync
argocd app rollback myapp <history-id>          # auto-sync must be OFF

# 9. Per-resource
argocd app resources myapp
argocd app delete-resource myapp --kind Deployment --resource-name web

# 10. Logs
argocd app logs myapp --kind Deployment --name web --tail 100 -f

# 11. History
argocd app history myapp

# 12. Imperative patches
argocd app set myapp --sync-policy automated --auto-prune --self-heal
argocd app set myapp --sync-option ServerSideApply=true
argocd app patch myapp --type merge \
  --patch '{"spec":{"syncPolicy":{"automated":null}}}'   # disable auto-sync

# 13. Edit
argocd app edit myapp                           # opens $EDITOR

# 14. Delete
argocd app delete myapp                         # cascade (default)
argocd app delete myapp --cascade=false         # keep workloads, drop CR
argocd app delete myapp --propagation-policy background

# 15. Confirm gates (Delete=confirm / Prune=confirm)
argocd app confirm-deletion myapp

# AppSet
argocd appset get my-appset -o yaml
argocd appset create --dry-run ./appset.yaml -o json
argocd appset generate ./appset.yaml
```

`argocd admin app diff-reconcile-results` compares two reconcile results
offline — handy after upgrading Argo CD.

**Easy-to-forget flags:** `--core` (talk directly to k8s, no argocd-server);
`--port-forward --port-forward-namespace argocd` (no Ingress needed);
`--prompts-enabled` (interactive confirm on destructive); `KUBECTL_EXTERNAL_DIFF=dyff`.

---

## Appendix — Symptom → annotation/syncOption

| Symptom | Annotation / option | Where |
|---------|--------------------|-------|
| Mutating webhook drift | `compare-options: ServerSideDiff=true` | App annotation |
| Default-value drift | `compare-options: ServerSideDiff=true` | App annotation |
| HPA replicas drift | `ignoreDifferences /spec/replicas` + `RespectIgnoreDifferences=true` | App spec + syncOptions |
| `kubectl apply` field-manager war | `ServerSideApply=true` | syncOptions |
| cert-manager Ingress drift | `ignoreDifferences managedFieldsManagers: [cert-manager]` | App spec |
| Operator-managed sub-resource drift | `IgnoreExtraneous` + `RespectIgnoreDifferences=true` | App + syncOptions |
| Resource-limit unit drift | `ServerSideDiff=true` or `knownTypeFields` | App or `argocd-cm` |
| Status-in-git drift | `resource.compareoptions.ignoreResourceStatusField: crd` | `argocd-cm` |
| `instance` label collision | switch tracking method (`installationID`) | `argocd-cm` (v3.0+ default OK) |
| Wave hangs forever | Custom Lua reading `.status.conditions` correctly | `argocd-cm` |
| Self-heal loop | `ignoreDifferences` + `RespectIgnoreDifferences=true` | App spec + syncOptions |
| Monorepo perf | `manifest-generate-paths: <list>` | App annotation |
| Big-app sync slow | `ApplyOutOfSyncOnly=true` | syncOptions |
| Untracked resource churn | `ignore-resource-updates: 'true'` | Resource annotation |
| Hook leak (`generateName`) | Fixed `metadata.name` + `BeforeHookCreation` (or `ttlSecondsAfterFinished`) | Hook resource |
| Hook namespace missing | `CreateNamespace=true` | syncOptions |
| Helm hook collides w/ Argo | `argocd.argoproj.io/hook: Skip` | Resource annotation |
| Cleanup work on app delete | `argocd.argoproj.io/hook: PreDelete` / `PostDelete` | Hook resource |
| AppSet wipes my annotation | `preservedFields.annotations: [...]` | AppSet spec |
| AppSet deletes child apps | `applicationsSync: create-update` (+ finalizer + `preserveResourcesOnDeletion`) | AppSet spec |
| AppSet templating empty | `goTemplate: true` + `goTemplateOptions: ["missingkey=error"]` | AppSet spec |
| Resource won't prune | Remove `argocd.argoproj.io/sync-options: Prune=false` from resource | Resource annotation |
| Empty-app refusal | `automated.allowEmpty: true` | App syncPolicy |
| Critical-resource prune gate | `Prune=confirm` + `argocd.argoproj.io/deletion-approved` | Resource + App annotation |
| Drain-before-prune | `PruneLast=true` | syncOptions |
| Refuse delete on app deletion | `Delete=false` (v3.3+) | syncOptions |
| App stuck deleting | Fix child finalizers, then `--cascade=false` | kubectl + CLI |
| Freeze app during incident | `argocd.argoproj.io/skip-reconcile: 'true'` | App annotation |
