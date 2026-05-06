# Projects, RBAC, multi-tenancy boundaries

App-author view of the security envelope around every `Application`: the `AppProject` CR, RBAC, app/appset-in-any-namespace, sync impersonation, signature verification, secrets hygiene, and supply chain. Targets Argo CD v3.3.9 stable, with v3.4 deltas called out.

Sources (paths relative to `argoproj/argo-cd` repo root): `docs/operator-manual/{project-specification.md, project.yaml, app-any-namespace.md, app-sync-using-impersonation.md, rbac.md, secret-management.md, security.md}`, `docs/user-guide/{projects.md, gpg-verification.md, kustomize.md, sync_windows.md, orphaned-resources.md}`.

---

## 1. AppProject CR — every field

An `AppProject` is the trust envelope for a set of `Application`s. It declares what those Applications can source from, deploy to, deploy as, and sync when. Violations make the controller refuse reconciliation.

### 1.1 `metadata.namespace` and finalizer

**Rule.** Every `AppProject` lives in the Argo CD control-plane namespace (typically `argocd`); you cannot put projects in tenant namespaces. `metadata.name` is what `Application.spec.project` references. Always set the resources finalizer.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-alpha
  namespace: argocd
  finalizers: [resources-finalizer.argocd.argoproj.io]
```

**Why.** Without the finalizer, deleting a project while child `Application`s still reference it leaves them orphaned. With it, delete blocks until the last referrer is gone.

### 1.2 `sourceRepos`

**Rule.** Glob list of repo URLs Applications in this project may source from. Supports `!repo` negation. A source is allowed iff at least one allow matches AND no deny matches; `!*` is invalid (`docs/user-guide/projects.md` lines 83-88).

```yaml
spec:
  sourceRepos:
    - 'https://github.com/team-alpha/*'
    - '!https://github.com/team-alpha/secret-repo'   # deny wins
```

**Transitive reference caveat.** `sourceRepos` only restricts the **initial** clone. Helm chart `dependencies:` and Kustomize remote bases are followed transitively and are **not** subject to the allow-list (`docs/operator-manual/security.md` lines 65-88; §10). If your app pulls a chart from a museum you don't own, the second-hop fetch is unconstrained.

### 1.3 `destinations`

**Rule.** List of `(server | name | namespace)` triples (any combination, all glob-able). Both cluster and namespace are constrained. Same allow + no-deny semantics as `sourceRepos`.

```yaml
spec:
  destinations:
    - { namespace: 'team-alpha-*', server: https://kubernetes.default.svc, name: in-cluster }
    - { namespace: '!kube-system', server: '*' }     # forbid even if allowed above
```

**Why both `server` and `name`?** Some clusters in `argocd-cm` are referenced by URL (`server`), others by registered name (`name`). When both fields are set on a destination entry, **both must match**. Day-one footgun — see §9. Negation is the only safe way to express "any namespace except `kube-system`".

### 1.4 `clusterResourceWhitelist` / `clusterResourceBlacklist`

**Rule.** Cluster-scoped resources are **deny-by-default** (whitelist). If a cluster Kind isn't listed, project apps can't create it.

```yaml
spec:
  clusterResourceWhitelist:
    - { group: '', kind: Namespace, name: 'team-alpha-*' }   # name optional, glob (v3.3+)
    - { group: 'rbac.authorization.k8s.io', kind: ClusterRole }
  clusterResourceBlacklist:
    - { group: '', kind: Namespace, name: 'kube-*' }         # deny even if whitelisted
```

**v3.3 new (#24674).** The `name:` field on `clusterResourceWhitelist`/`Blacklist` lets you scope by *name pattern* in addition to `group`/`kind`. A team that owns a name-prefix can create their own namespaces / CRDs / ClusterRoles without touching anyone else's.

### 1.5 `namespaceResourceWhitelist` / `namespaceResourceBlacklist`

**Rule.** Namespaced resources are **allow-by-default** (blacklist). If you also set a whitelist, the union "in whitelist AND not in blacklist" is what's permitted.

```yaml
spec:
  namespaceResourceBlacklist:
    - { group: '',                          kind: ResourceQuota }
    - { group: '',                          kind: LimitRange }
    - { group: 'networking.k8s.io',         kind: NetworkPolicy }
    - { group: '',                          kind: Secret }       # force ESO/SealedSecrets — §8
    - { group: 'rbac.authorization.k8s.io', kind: RoleBinding }  # if platform manages identity
```

**Why.** Common multi-tenant pattern: tenants ship `Deployment`, `Service`, `ConfigMap`; platform manages `RoleBinding`, `ClusterRoleBinding`, `NetworkPolicy`, `ResourceQuota`, `ServiceAccount`. If an app author can ship `RoleBinding` `cluster-admin → their SA`, every other project control evaporates.

**Inverse use.** Blacklisting `Secret` here forces every secret through `ExternalSecret`/`SealedSecret`/CSI — tenants *cannot* commit plaintext even by accident.

### 1.6 `roles` (jwtTokens, policies, groups)

Project-scoped RBAC: list of Casbin policies + OIDC groups bound to each role + issued JWT tokens for CI. Brief here; full RBAC in §6.

```yaml
spec:
  roles:
    - name: read-only
      policies:
        - p, proj:team-alpha:read-only, applications, get, team-alpha/*, allow
      groups: [acme-org:team-alpha-developers]
    - name: ci-syncer
      policies:
        - p, proj:team-alpha:ci-syncer, applications, sync, team-alpha/*, allow
        - p, proj:team-alpha:ci-syncer, applications, get,  team-alpha/*, allow
      jwtTokens:
        - iat: 1714902000   # populated by `argocd proj role create-token`
```

**Footgun.** Policy subject must be exactly `proj:<project-name>:<role-name>`, or it's silently ineffective (`projects.md` line 202).

### 1.7 `signatureKeys`

**Rule.** List of GnuPG key IDs that **must** have signed a target commit before the controller will sync. Project granularity — no per-Application override. Full coverage in §7.

```yaml
spec:
  signatureKeys:
    - keyID: 4AEE18F83AFDEB23   # 40-char fingerprint
```

**Pair with tight `sourceRepos`.** Otherwise an attacker who can write any allowed repo dodges enforcement by pointing the Application at a repo where they control signing.

### 1.8 `syncWindows`

Time-windowed allow/deny rules; composite key `(kind, schedule, duration, applications|namespaces|clusters)`. Brief — deep coverage in `references/sync.md`. As a security control, `manualSync: false` makes a true freeze (CI cannot push through); `syncOverrun: true` lets in-flight syncs finish through the boundary.

```yaml
spec:
  syncWindows:
    - { kind: deny, schedule: '0 22 * * 5', duration: 60h,
        applications: ['prod-*'], manualSync: false,
        timeZone: UTC, syncOverrun: true }
```

### 1.9 `orphanedResources`

**Rule.** Detects namespaced resources in destination namespaces that aren't tracked by any Argo CD Application. Useful for catching drift.

```yaml
spec:
  orphanedResources:
    warn: true
    ignore:
      - { kind: ConfigMap, name: kube-root-ca.crt }
      - { kind: Secret,    name: '*-token-*' }
```

K8s-injected resources (`kube-root-ca.crt`, default `ServiceAccount`, `kubernetes` Service in `default`, SA token Secrets) are never flagged. Performance hit if namespaces are busy with non-Argo-managed resources.

### 1.10 `permitOnlyProjectScopedClusters`

**Rule.** Restricts the project to clusters registered *as project-scoped* — cluster Secret labelled `argocd.argoproj.io/secret-type: cluster` AND with `stringData.project: <name>`.

```yaml
spec:
  permitOnlyProjectScopedClusters: true
```

**Why.** Closes the `destinations: { server: '*' }` escape hatch. Without it, a tenant whose project's `destinations` covers `server: '*'` can target any cluster the controller knows about — including clusters owned by other teams.

### 1.11 `sourceNamespaces`

**Rule.** K8s namespaces in which `Application` resources for this project may **reside**. Empty (default) = only the control-plane namespace. See §3.

```yaml
spec:
  sourceNamespaces: [team-alpha-apps, team-alpha-staging]
```

### 1.12 `destinationServiceAccounts`

The impersonation map (§5):

```yaml
spec:
  destinationServiceAccounts:
    - { server: https://kubernetes.default.svc, namespace: team-alpha-prod,
        defaultServiceAccount: team-alpha-deployer }
    - { server: https://kubernetes.default.svc, namespace: 'team-alpha-*',
        defaultServiceAccount: team-alpha-fallback-deployer }
```

---

## 2. The `default` project is dangerous

The auto-created `default` project ships fully open: `sourceRepos: ['*']`, `destinations: ['*'/'*']`, `clusterResourceWhitelist: ['*'/'*']`. Any `Application` with no explicit `spec.project` lands there. The only thing stopping abuse is whatever Argo CD RBAC and Kubernetes RBAC the controller's SA has — usually nothing useful in a multi-tenant cluster.

**Rule 1.** First action on a new install: neuter `default`.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata: { name: default, namespace: argocd }
spec:
  sourceRepos:      []
  sourceNamespaces: []
  destinations:     []
  namespaceResourceBlacklist:
    - { group: '*', kind: '*' }
```

After applying, any `Application` targeting `default` is denied sync until moved to a real project.

**Rule 2.** One project per **team-environment** pair, not "per team" (`team-alpha-dev` could deploy to `team-alpha-prod`) and not "per app" (admin overhead explodes). Sweet spot: `team-alpha-dev`, `team-alpha-staging`, `team-alpha-prod` — progressively tighter `destinations`, `signatureKeys`, `syncWindows`.

**Tight production project.**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-alpha-prod
  namespace: argocd
  finalizers: [resources-finalizer.argocd.argoproj.io]
spec:
  description: Team Alpha — production
  sourceRepos: ['https://github.com/team-alpha/prod-manifests']
  sourceNamespaces: [team-alpha-apps]
  destinations:
    - { server: https://team-alpha-prod.k8s.example.com, namespace: 'team-alpha-*' }
    - { name:   team-alpha-prod,                          namespace: 'team-alpha-*' }
  permitOnlyProjectScopedClusters: true
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
    - { group: '',                          kind: Secret }
    - { group: '',                          kind: ResourceQuota }
    - { group: '',                          kind: LimitRange }
    - { group: 'rbac.authorization.k8s.io', kind: RoleBinding }
    - { group: 'rbac.authorization.k8s.io', kind: ClusterRoleBinding }
    - { group: 'networking.k8s.io',         kind: NetworkPolicy }
  signatureKeys: [{ keyID: 4AEE18F83AFDEB23 }]
  destinationServiceAccounts:
    - { server: https://team-alpha-prod.k8s.example.com,
        namespace: 'team-alpha-*',
        defaultServiceAccount: team-alpha-deployer }
  syncWindows:
    - { kind: deny, schedule: '0 22 * * 5', duration: 60h,
        applications: ['*'], manualSync: false, timeZone: UTC }
```

---

## 3. Applications in any namespace (Stable)

Source: `docs/operator-manual/app-any-namespace.md`.

Pre-v2.5, all `Application`s had to live in `argocd`. Anyone with K8s `create` on `argocd` is effectively an Argo CD admin. **Fix**: two prerequisites both required:

1. **Platform-admin gate** — controller and server started with `--application-namespaces=<glob,...>`, or `application.namespaces` set in `argocd-cmd-params-cm`. Globs work (`team-*`, `*-tenant-a`, `*` for all).
2. **Project-owner gate** — the AppProject's `.spec.sourceNamespaces` includes the Application's namespace.

```yaml
# argocd-cmd-params-cm — platform admin
data:
  application.namespaces: 'team-alpha-apps, *-tenant-a'
---
# AppProject — project owner
spec:
  sourceNamespaces: [team-alpha-apps]   # MUST also be in application.namespaces above
```

**RBAC `<object>` shift.** With apps-in-any-namespace, the `<object>` for `applications`/`logs` resources changes from `<project>/<app>` to `<project>/<namespace>/<app>`. Apps in `argocd` keep the 2-segment form. Never grant access to `argocd` via `sourceNamespaces` — apps there can't be properly restricted (`app-any-namespace.md` line 145).

**Other knobs.** Resource-tracking method must be `annotation` or `annotation+label` (composite names overflow the 63-char K8s label limit). The default `argocd-server` ClusterRole doesn't reach outside `argocd` — apply `examples/k8s-rbac/argocd-server-applications/`. Notifications controller needs the same.

**CVE-2024-31990 angle.** Pre-patch, the API server didn't enforce `sourceNamespaces` on project switching: a user could create an app in their permitted namespace then `kubectl edit` `.spec.project` to escalate into a more-privileged project. The two-gate boundary above is what the patch enforces. Patched v2.10.7 / v2.9.12 / v2.8.16; v3.x clean from day 1.

---

## 4. ApplicationSets in any namespace (Stable in v3.4)

Same shape as §3, for `ApplicationSet`. **Stable in v3.4** (#27353). Two gates:

1. `--applicationset-namespaces=<glob,...>` (or `applicationsetcontroller.namespaces` in `argocd-cmd-params-cm`).
2. The project allows the templated Applications via `sourceNamespaces`.

The `ApplicationSet` CR goes in a tenant namespace; the generated `Application`s land where the templated `metadata.namespace` points (which must satisfy §3's two gates).

---

## 5. Sync impersonation (`destinationServiceAccounts`)

Source: `docs/operator-manual/app-sync-using-impersonation.md`.

**Maturity.** v3.3.9: **Alpha** (since v2.13). v3.4: **Beta** — formally graduated by #27576 / commit `3c233ccda` (2026-05-01). v3.4 also extends impersonation to **server operations** (`logs`, `exec`, custom resource actions) per #26898.

**Problem.** By default the controller's own SA applies all manifests, so it needs the union of every Application's permissions — typically `cluster-admin`. A malicious tenant who can mutate a `RoleBinding` escalates to that level.

**Fix.** Per-`(cluster, namespace)` ServiceAccount on the destination cluster. K8s RBAC enforced by kube-apiserver becomes the actual blast-radius gate.

**Wiring.**

```yaml
# argocd-cm — global on/off, no per-app/per-project opt-in
data:
  application.sync.impersonation.enabled: 'true'
---
# AppProject — per-project mapping
spec:
  destinationServiceAccounts:
    - { server: https://kubernetes.default.svc, namespace: team-alpha-prod,
        defaultServiceAccount: team-alpha-deployer }
    - { server: https://kubernetes.default.svc, namespace: 'team-alpha-*',
        defaultServiceAccount: team-alpha-fallback-deployer }
    - { server: https://kubernetes.default.svc, namespace: '*',
        defaultServiceAccount: default }     # catch-all — list LAST
```

The controller iterates the list **in order** and uses the first match. **No match → sync fails** — always include a sane catch-all last. Cross-namespace SA: `defaultServiceAccount: tenant-meta-ns:team-alpha-deployer`; bare name = SA in destination namespace.

**v3.4 server-side scope.** The impersonated SA also serves `argocd app logs`, `argocd app exec`, and Resource Action calls. The SA needs `get`/`list` on `pods`, `pods/log`, `events`, plus action permissions for any `actions/<group>/<kind>/<verb>` exposed.

**`destinationServiceAccounts` is keyed by `server` only — not `name`.** Known gap. If you use impersonation, **standardise on `server`** for both `destinations:` and `destinationServiceAccounts:` so matching stays predictable.

**Multi-tenant onboarding.** Platform admin creates: tenant namespace, `ServiceAccount` in it, `Role` granting only the Kinds the team may ship (Deployment, Service, ConfigMap — *not* Roles, RoleBindings, ResourceQuotas), `RoleBinding`, then the AppProject with matching `destinations` + `destinationServiceAccounts` + `sourceNamespaces`. Argo CD's blast radius is then bounded by the destination Role.

**Caveats.** Global on/off (can't enable per-project). Lifecycle covers sync (create/update/prune), the Application finalizer's deletion path, and (v3.4+) UI/CLI server actions. Don't grant the destination SA `cluster-admin` "just in case" — defeats the feature.

---

## 6. RBAC for app authors (brief)

Source: `docs/operator-manual/rbac.md`.

**Two layers.** Global (`argocd-rbac-cm`, admin) and project-scoped (the `roles:` block on each AppProject, project owner). Project-scoped policies must be subject-prefixed `proj:<project>:<role>` and policy `<object>` must be `<project>/...`.

**Casbin policy syntax.**

```
p, <role/user/group>, <resource>, <action>, <object>, <effect>
g, <user/group>, <role>
```

Resources app authors touch: `applications`, `applicationsets`, `logs`, `exec`, `repositories`, `clusters`, `gpgkeys`. Application object format is `<project>/<app>` without apps-in-any-namespace, `<project>/<namespace>/<app>` with it.

### 6.1 v3.0 sub-resource inheritance breaking change

Pre-v3.0, `applications, update` on `default/foo` granted update on the Application **and** every resource it managed. **v3.0+: no longer inherits by default.** Use the explicit form:

```
p, alice, applications, update/<group>/<kind>/<ns>/<name>, default/foo, allow
```

Restore old behaviour with `server.rbac.disableApplicationFineGrainedRBACInheritance: false` in `argocd-cm` (`docs/operator-manual/upgrading/2.14-3.0.md`).

### 6.2 Logs RBAC enforced

`applications, get` no longer implies log access. Logs need an explicit policy:

```
p, my-team, logs, get, team-alpha/*, allow
```

### 6.3 JWT tokens for CI

```bash
argocd proj role create-token <PROJ> <ROLE> -e 90d
```

Tokens are never persisted (only `iat` is stored on the project); revoke with `argocd proj role delete-token <PROJ> <ROLE> <iat>`. Cannot escape the project's policy lattice.

### 6.4 Glob-matching trap

```
p, role:tester, applications, action/extensions/*, default/*, allow
```

…matches `action/extensions/DaemonSet/test` because `/` is **not** a separator inside a glob token (`rbac.md` line 135-144). Be explicit — use four slashes for sub-resource patterns.

---

## 7. Signature verification (GnuPG)

Source: `docs/user-guide/gpg-verification.md`.

**Control.** AppProject's `.spec.signatureKeys` list. Non-empty list → sync requires the target Git revision to be signed by one of those keys. Project granularity.

**Keyring.** Public keys in cluster-wide `argocd-gpg-keys-cm` ConfigMap (key ID → ASCII-armored block). Manage via `argocd gpg add|list|get|rm` or declaratively. RBAC resource is `gpgkeys`.

**Verification target rules** (lines 39-52):

- `targetRevision` resolves to a **commit** (branch, `HEAD`, SHA) → the **commit** must be signed.
- `targetRevision` resolves to a **lightweight tag** → same as commit.
- `targetRevision` resolves to an **annotated tag** (`git tag -s`) → the **tag object** must be signed (the tag, not necessarily the commit it points at).

**Bypass conditions.**

- `signatureKeys` empty (the default) → no enforcement.
- `ARGOCD_GPG_ENABLED=false` env on Argo CD pods → global kill switch.
- **Helm repos**: GnuPG verification covers Git only. Helm chart provenance is **out of scope** (line 23).
- `argocd app sync --local` is **blocked** when enforcement is on (line 67).

**No first-class cosign integration as of v3.3.9.** For OCI / cosign artefact verification, run a separate destination-cluster verifier (Kyverno, sigstore-policy-controller). Alternative: source-hydrator pattern where CI signs rendered manifests with GnuPG and Argo CD verifies the standard way.

**Trust model caveat.** All keys in the keyring are trusted equally — no web-of-trust. Treat key import as sensitive; restrict `gpgkeys, create` to platform admins.

---

## 8. Secrets — what NOT to do

Source: `docs/operator-manual/secret-management.md`.

**Strong rule.** Don't commit raw `Secret`. Don't render secrets via a manifest-generation plugin. Use a **destination-cluster** secret operator.

**Why.** The repo-server caches generated manifests in **Redis in plaintext**. Anything Argo CD's manifest-generation step sees, Redis sees. Two recent criticals exploit exactly this surface:

- **CVE-2026-42880** (May 2026, critical). `ServerSideDiff` + `IncludeMutationWebhook=true` annotation leaks unmasked Secret data via the project API to any auth user with `applications, get` (which everyone has by default). Patched **v3.3.8 / v3.2.10 / v3.1.15** — upgrade past those if you handle secrets.
- **CVE-2025-55190** (Sept 2025, critical). Project API token with basic project RBAC could pull repository credentials from `/api/v1/projects/{p}/detailed`. Patched late-Sep 2025.

UX bonus: secret rotation decouples from app-sync, so you can't accidentally rotate via an unrelated release.

**Recommended patterns** (`secret-management.md` lines 11-28):

- **External Secrets Operator** (canonical). `ExternalSecret` → `SecretStore` (AWS SM, Vault, GCP, Azure KV, …). Operator pulls plaintext at runtime and writes a normal `Secret`.
- **Sealed Secrets**. Per-cluster public-key encryption. `kubeseal` locally → commit `SealedSecret` → controller decrypts in-cluster.
- **SOPS via plugin**. **The doc strongly cautions against** (line 35): secrets pass through repo-server → Redis. If you must, run Argo CD on a dedicated cluster with NetworkPolicies.
- **Kubernetes Secrets Store CSI Driver**. Mounts cloud-secret-manager values directly into Pods as files. No `Secret` resource exists.
- **Vault Secrets Operator**. Hashicorp first-party; same shape as ESO but Vault-only.

**App-author rule.** Commit a *reference* to a secret store (`ExternalSecret` / `SealedSecret` / etc.), never a raw `Secret`. Base64 is encoding, not encryption.

**Project-policy lever.** Blacklist `Secret` Kind in `namespaceResourceBlacklist`. Tenants then *cannot* commit plaintext even by accident.

---

## 9. `destination.name` vs `destination.server`

Both fields identify the target cluster. Day-one footgun.

- **`server`** — the API URL (`https://kubernetes.default.svc`, `https://team-alpha-prod.k8s.example.com:6443`). The auto-registered in-cluster destination is `https://kubernetes.default.svc`.
- **`name`** — the registered name from `argocd cluster add` / cluster Secret (`in-cluster`, `team-alpha-prod`).

**Rules.**

- Set **exactly one** of `server` or `name` on an `Application`. Both-set + disagree fails validation; both-set + match is redundant.
- **Use `name` when you can.** Names are stable across cluster migrations; URLs aren't. `name`-keyed Applications survive control-plane endpoint changes (LB rename, DNS migration) with just a Secret update; `server`-keyed apps break.

**ApplicationSet cluster-generator caveat.** The cluster generator emits **both** `server` and `name` into the templated Application. If your template uses `{{server}}` and the project's `destinations:` only lists `name`, sync hits a project-permission denial. Fix: list **both** forms in `destinations:`.

```yaml
spec:
  destinations:
    - { server: 'https://team-alpha-prod.k8s.example.com', namespace: team-alpha-prod }
    - { name:   'team-alpha-prod',                          namespace: team-alpha-prod }
```

§5's `destinationServiceAccounts` is keyed by `server` only — keep that aligned.

---

## 10. Trusted vs untrusted repos — supply chain

Sources: `docs/operator-manual/security.md` lines 43-89, `docs/user-guide/kustomize.md` lines 175-300.

**Repo-server is the exposure surface.** `argocd-repo-server` clones your repos and **executes their content** — `helm template`, `kustomize build`, `jsonnet`, plugins. A malicious commit can attempt out-of-tree file reads, RCE via plugins, or pull additional unaudited repos via Helm `dependencies:` / Kustomize remote bases. The `sourceRepos` allow-list only gates the **initial** clone (§1.2).

**Rules.**

1. **Pin everything.** Helm `dependencies:` → digest, not floating version. Application `targetRevision` → SHA + `signatureKeys`, not `HEAD`.
2. **No charts from museums you don't own.** A public Helm/OCI registry can publish a poisoned chart at any time; your Argo CD reconciles it next sync.
3. **`kustomize.buildOptions: --enable-alpha-plugins` is dangerous.** Lets Kustomize invoke arbitrary external binaries from the repo-server pod. Attacker who can write a trusted repo gets RCE on `argocd-repo-server`. Don't enable; if you must, run Argo CD on a dedicated cluster.
4. **`kustomize.buildOptions: --load-restrictor LoadRestrictionsNone` weakens path-traversal defence.** History of path-traversal CVEs: **CVE-2022-24904**, **CVE-2023-40026**, **CVE-2022-31036** — all "out-of-bound files leaked from repo-server". Don't add unless needed for one specific trusted app.
5. **`kustomize.buildOptions: --enable-helm`** lets Kustomize render embedded Helm charts at build. Chart-trust concerns now apply through Kustomize too.
6. **CMPs + secret injection put plaintext in Redis.** If you must run `argocd-vault-plugin` or similar, NetworkPolicy-isolate repo-server and Redis. Accept that Redis compromise = secrets compromise.
7. **Disable tools you don't use.** `docs/user-guide/tool_detection.md` covers tool detection. Pure-Kustomize shop? Disable Helm rendering. Smaller blast radius.

---

## Pre-publish checklist for an app author

1. `spec.project` set explicitly (not the neutered `default`).
2. `repoURL` covered by the project's `sourceRepos`.
3. `(server|name, namespace)` covered by `destinations`, `permitOnlyProjectScopedClusters` honoured.
4. Cluster-scoped Kinds in `clusterResourceWhitelist`. No raw `Secret` / `RoleBinding`.
5. Commits or annotated tags signed by a key in `argocd-gpg-keys-cm` if the project enforces `signatureKeys`.
6. If app lives outside `argocd`, namespace in **both** `application.namespaces` and the project's `sourceNamespaces`.
7. If impersonation is on, destination matches a `destinationServiceAccounts` entry, and the SA has K8s RBAC for every Kind shipped.
8. No active `kind: deny` syncWindow blocking the deploy (`argocd app get <app>` shows windows).
