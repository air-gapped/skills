---
name: helm
description: >-
  Author and maintain Helm charts: create chart, write templates, values.yaml patterns,
  _helpers.tpl, Chart.yaml, values.schema.json, helm-docs, library charts. Helm 4 (SSA,
  WASM, OCI digest). Chart CI/CD (lint, helm-unittest, chart-testing, kubeconform, OCI
  push). OpenShift compatibility (SCCs, Routes, UIDs, adaptSecurityContext). Chart
  security (SecurityContext, RBAC, NetworkPolicy, cosign signing, image digest pinning).
  CRD management, ServiceMonitor templates, HPA, persistence, resource presets.
  NOT for installing or consuming third-party charts.
---

# Helm Charts

Create, test, secure, and publish Helm charts. Covers Helm 4 (November 2025),
OCI distribution, OpenShift compatibility, and production patterns from Bitnami,
Cilium, cert-manager, and ArgoCD.

## Quick Decision Guide

| Task | Go to |
|------|-------|
| Create a new chart from scratch | § Chart Scaffold below |
| Structure values.yaml, helpers, labels | `references/chart-structure.md` |
| Harden security (SecurityContext, RBAC, NetworkPolicy) | `references/security.md` |
| Sign and verify charts (cosign, OCI) | `references/security.md` § Supply Chain |
| Make chart work on OpenShift | `references/openshift.md` |
| Write tests (unittest, ct, kubeconform) | `references/testing-ci.md` § Testing |
| Set up CI/CD (lint, test, release, OCI push) | `references/testing-ci.md` § CI/CD |
| Integrate release-please with Helm charts | `references/testing-ci.md` § Release-Please Integration |
| Add ServiceMonitor, HPA, persistence, extensions | `references/production-patterns.md` |
| Manage CRDs properly | `references/chart-structure.md` § CRDs |
| Multi-chart management (Helmfile) | `references/testing-ci.md` § Helmfile |

## Critical Gotchas

### 1. Helm 4 Is Current (Released November 2025)

Helm 4.0.0 released at KubeCon November 2025. Current: v4.1.3. Key changes:

- **Server-Side Apply** is default for new installations (existing Helm 3 releases
  keep client-side apply on upgrade unless `--server-side` is passed)
- **OCI digest install**: `helm install app oci://registry/chart@sha256:abc...`
- **WASM plugin system** (sandboxed). Post-renderers must be plugin names, not
  arbitrary executables
- **CLI renames**: `--force` -> `--force-replace`, `--atomic` -> `--rollback-on-failure`
  (old names emit deprecation warnings)
- **Multi-document values** files supported (`---` separator)
- **kstatus** replaces `--wait` readiness checks. Annotations:
  `helm.sh/readiness-success`, `helm.sh/readiness-failure`
- **Chart API v2** (Helm 3 charts) works unmodified. v3 format planned but not
  yet available
- **Helm 3 EOL**: bug fixes until July 8, 2026; security until November 11, 2026

### 2. Use `include`, Never `template`

`template` cannot be piped. `include` returns a string that works with `nindent`,
`quote`, etc. Every named template call should use `include`:

```yaml
# Wrong
{{ template "mychart.labels" . }}

# Right
{{- include "mychart.labels" . | nindent 4 }}
```

### 3. Namespace Named Templates to Avoid Collisions

ALL defined template names MUST be prefixed with the chart name. Global template
namespace means unprefixed names collide with subcharts:

```yaml
# Wrong
{{- define "fullname" -}}

# Right
{{- define "mychart.fullname" -}}
```

### 4. Selector Labels Are Immutable

Never include version-based labels in Deployment `matchLabels`. Use only:
- `app.kubernetes.io/name` (chart name)
- `app.kubernetes.io/instance` (release name)

Adding `helm.sh/chart` or `app.kubernetes.io/version` to selectors causes upgrade
failures because `matchLabels` cannot be changed after creation.

### 5. values.yaml: camelCase, Quote Strings, Prefer Maps

- camelCase with lowercase first letter (never `.Release.Name` case for user values)
- Quote all strings: `{{ .Values.foo | quote }}` (prevents YAML type coercion)
- Prefer maps over arrays for `--set` ergonomics
- Large integers can become scientific notation; store as strings if needed

### 6. CRDs in `crds/` Directory Are Never Upgraded

Helm's native `crds/` directory installs CRDs once but never upgrades or deletes
them. Every major chart (cert-manager, Cilium, kube-prometheus-stack) avoids this
by putting CRDs in `templates/` with conditional flags. See
`references/chart-structure.md` § CRDs.

### 7. OCI Is the Primary Distribution Method

OCI registries are the recommended distribution for Helm 4. Bitnami moved to
OCI-only. Push: `helm push chart-0.1.0.tgz oci://ghcr.io/org/charts`. Tags
must match SemVer (no `latest`). SemVer `+` becomes `_` in OCI tags.

### 8. OpenShift: Omit Specific UIDs

OpenShift assigns random UIDs per namespace. Charts that hardcode `runAsUser: 1001`
break under the `restricted-v2` SCC. Use the Bitnami `adaptSecurityContext: auto`
pattern to auto-detect OpenShift and strip UID/GID fields. See
`references/openshift.md`.

### 9. DeploymentConfig Is Dead

Deprecated in OpenShift 4.14. Use standard `apps/v1 Deployment`. Never create
new DeploymentConfigs.

### 10. Default LoadBalancer Services to No NodePort, and Add extraSpec

Kubernetes auto-assigns a NodePort (30000-32767) for LoadBalancer services. This
is almost never wanted — cloud LBs route traffic directly. Default
`allocateLoadBalancerNodePorts: false` in values.yaml. Requires Kubernetes 1.24+.

Additionally, always include `service.extraSpec: {}` — a passthrough map that
renders arbitrary fields into the Service spec via `toYaml`. This prevents
admins from being blocked when they need `externalTrafficPolicy`,
`internalTrafficPolicy`, `loadBalancerClass`, or any future K8s field. See
`references/production-patterns.md` § Service Spec Control.

### 11. Always Provide commonAnnotations and commonLabels

Every chart must include `commonAnnotations: {}` and `commonLabels: {}` at the
top of values.yaml. These apply to **every** resource metadata block — critical
for cost allocation, team ownership, compliance, and tooling that filters by
labels or annotations (Prometheus, ArgoCD, Datadog, etc.). Inject commonLabels
via the labels helper; create a dedicated annotations helper for commonAnnotations.
For resources with their own annotations (Service, Ingress, ServiceAccount),
merge both. See `references/chart-structure.md` § Common Labels and Annotations.

### 12. release-please: Three Traps That Break Chart Publishing

**Trap 1: `release-type` as action input ignores config file.** If you set
`release-type: go` (or any value) in the workflow YAML, the action calls
`Manifest.fromConfig()` which builds config entirely from inputs and
**completely skips** `release-please-config.json`. All advanced config
(`extra-files`, `changelog-sections`, `draft`, etc.) is silently ignored.
Always put `release-type` in the config file, never in the action input.

**Trap 2: String form of `extra-files` strips YAML comments.** The shorthand
`"charts/mychart/Chart.yaml"` runs GenericYaml first, which strips all
comments including `x-release-please-version` annotations. Use the object
form: `{"type": "generic", "path": "charts/mychart/Chart.yaml"}`.

**Trap 3: Missing `changelog-sections` dumps `ci:` into "Breaking Changes".**
Without explicit section config, unrecognized commit types land in a
catch-all "Breaking Changes" section. Always configure `changelog-sections`
with `hidden: true` for non-user-facing types.

See `references/testing-ci.md` § Release-Please Integration for full config.

### 13. Cosign Requires Separate Registry Auth from Helm

`helm registry login ghcr.io` authenticates Helm's OCI client but does NOT
authenticate cosign. If your CI workflow pushes a chart with Helm and then
signs with cosign, you need both:

```yaml
# Helm auth (for helm push)
- uses: docker/login-action@...   # or: helm registry login ghcr.io

# Cosign auth (for cosign sign) — SEPARATE step
- run: cosign login ghcr.io -u ${{ github.actor }} -p ${{ secrets.GITHUB_TOKEN }}
```

Without the cosign login, signing fails with auth errors even though the push
succeeded. See the OCI Push workflow in `references/testing-ci.md`.

### 14. Renovate Is Significantly Better Than Dependabot for Helm

Dependabot added Helm support April 2025 but only handles Chart.yaml dependency
versions. Renovate also updates image tags in values.yaml, auto-bumps chart
versions, supports regex managers, and is self-hostable for air-gapped setups.

## Chart Scaffold

Start with `helm create mychart`, then apply these patterns:

```
mychart/
  .helmignore          # Exclude .git/, .github/, *.key, *.pem, .env
  Chart.yaml           # apiVersion: v2, type: application
  values.yaml          # camelCase, documented properties
  values.schema.json   # JSON Schema for validation
  README.md            # Auto-generate with helm-docs
  charts/              # Dependency charts
  crds/                # Only if CRDs never need upgrading
  templates/
    _helpers.tpl       # Namespaced named templates
    deployment.yaml    # One resource per file
    service.yaml
    serviceaccount.yaml
    ingress.yaml
    networkpolicy.yaml
    hpa.yaml
    pdb.yaml
    NOTES.txt          # Post-install instructions
    tests/
      test-connection.yaml
```

### Minimal Chart.yaml

```yaml
apiVersion: v2
name: mychart
description: A Helm chart for MyApp
type: application
version: 0.1.0
appVersion: "1.0.0"
kubeVersion: ">=1.22.0"
dependencies:
  - name: common
    version: ~2.x
    repository: oci://registry-1.docker.io/bitnamicharts
    tags:
      - bitnami-common
```

Complete starter _helpers.tpl, values.yaml, and other templates are in
`references/chart-structure.md` § Starter Templates. Key values patterns:

- `image.registry`/`repository`/`tag`/`digest` (Bitnami standard, digest overrides tag)
- `serviceAccount.create`/`automount: false` (security: no auto-mounted token)
- `containerSecurityContext` targeting PSS restricted profile
- `global.compatibility.openshift.adaptSecurityContext: auto` for OpenShift

## Reference Files

- **`references/chart-structure.md`** — Starter templates, Chart.yaml, values, helpers, labels, library charts, OCI, deps, schema, helm-docs, CRDs
- **`references/security.md`** — SecurityContext, RBAC, NetworkPolicy, image digests, secrets, cosign signing, Flux/ArgoCD verification
- **`references/openshift.md`** — Detection, SCCs, Routes vs Ingress, arbitrary UIDs, adaptSecurityContext, service certs, certification
- **`references/testing-ci.md`** — Testing pyramid, helm-unittest, ct, kubeconform, security scanning, CI workflows, Helmfile, Renovate
- **`references/production-patterns.md`** — ServiceMonitor, HPA, PDB, persistence, checksums, extension points, multi-component, presets
