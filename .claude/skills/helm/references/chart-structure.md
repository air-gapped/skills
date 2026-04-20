# Helm Chart Structure Reference

## Table of Contents
- [Starter Templates](#starter-templates)
- [Chart.yaml Schema](#chartyaml-schema)
- [Directory Layout](#directory-layout)
- [values.yaml Conventions](#valuesyaml-conventions)
- [_helpers.tpl Patterns](#helperstpl-patterns)
- [Standard Labels](#standard-labels)
- [Library Charts](#library-charts)
- [OCI Distribution](#oci-distribution)
- [Subchart Dependencies](#subchart-dependencies)
- [values.schema.json](#valuesschemajson)
- [helm-docs](#helm-docs)
- [CRD Management](#crd-management)
- [.helmignore](#helmignore)

---

## Starter Templates

Complete starter files for a new chart. Copy and customize.

### Minimal _helpers.tpl

```yaml
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "mychart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "mychart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "mychart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mychart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

### Minimal values.yaml

```yaml
commonAnnotations: {}   # Applied to every resource metadata
commonLabels: {}        # Applied to every resource metadata

replicaCount: 1

image:
  registry: docker.io
  repository: myorg/myapp
  tag: ""             # Defaults to Chart.appVersion
  digest: ""          # SHA256 overrides tag when set
  pullPolicy: IfNotPresent

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  automount: false    # Security: don't mount token unless needed
  annotations: {}
  name: ""

rbac:
  create: true

podSecurityContext:
  fsGroup: 1001
  fsGroupChangePolicy: OnRootMismatch

containerSecurityContext:
  runAsUser: 1001
  runAsGroup: 1001
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault

service:
  type: ClusterIP
  port: 80
  nodePort: ""                        # Pin a specific NodePort (NodePort/LoadBalancer only)
  allocateLoadBalancerNodePorts: false # Suppress auto-assigned NodePorts on LoadBalancer (K8s 1.24+)
  annotations: {}
  extraSpec: {}                       # Passthrough for any Service spec field (see production-patterns.md)

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
    - host: chart-example.local
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls: []

resources: {}

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

nodeSelector: {}
tolerations: []
affinity: {}

networkPolicy:
  enabled: false

metrics:
  enabled: false
  serviceMonitor:
    enabled: false
    interval: "30s"
    additionalLabels: {}

# OpenShift compatibility
global:
  compatibility:
    openshift:
      adaptSecurityContext: auto  # auto | force | disabled
```

---

## Chart.yaml Schema

`apiVersion: v2` required for Helm 3+ (still current for Helm 4; v3 coming later).

### Required Fields

| Field | Description |
|-------|------------|
| `apiVersion` | `v2` |
| `name` | Lowercase letters and numbers, dashes allowed. No uppercase, underscores, dots. |
| `version` | SemVer 2. Chart version (independent of appVersion). |

### Optional Fields

| Field | Description |
|-------|------------|
| `appVersion` | Application version. Independent of chart version. Quote it. |
| `description` | Single-sentence chart description. |
| `type` | `application` (default, installable) or `library` (not installable). |
| `kubeVersion` | SemVer constraint (e.g., `>=1.22.0`). Checked at install time. |
| `keywords` | List for Artifact Hub search. |
| `home` | Project homepage URL. |
| `sources` | List of source code URLs. |
| `maintainers` | List of `{name, email, url}`. |
| `icon` | SVG or PNG URL for Artifact Hub. |
| `deprecated` | Boolean. |
| `dependencies` | See § Subchart Dependencies. |
| `annotations` | Free-form metadata. Artifact Hub uses specific keys. |

SemVer `+` converts to `_` in Kubernetes labels and OCI tags.

---

## Directory Layout

```
mychart/
  .helmignore              # Patterns to exclude from packaging
  Chart.yaml               # Chart metadata
  Chart.lock               # Locked dependency versions (commit this)
  values.yaml              # Default configuration
  values.schema.json       # JSON Schema for values validation
  README.md                # Auto-generate with helm-docs
  README.md.gotmpl         # Optional helm-docs template
  LICENSE                  # Chart license
  charts/                  # Dependency chart archives
  crds/                    # CRDs (installed once, never upgraded)
  templates/
    _helpers.tpl           # Named template partials (no manifest output)
    deployment.yaml        # One resource per file
    service.yaml
    serviceaccount.yaml
    configmap.yaml
    secret.yaml
    ingress.yaml
    networkpolicy.yaml
    hpa.yaml
    pdb.yaml
    NOTES.txt              # Post-install instructions (Go template)
    tests/
      test-connection.yaml # helm test pods
```

Conventions:
- Files prefixed with `_` produce no manifest output
- Use `.yaml` for manifests, `.tpl` for helpers
- One resource per file, named for the resource kind
- Filenames use dashed-lowercase, not camelCase
- Two-space indentation, never tabs

---

## values.yaml Conventions

### Naming

- **camelCase** with lowercase first letter
- Never initial capitals (conflicts with Helm built-ins like `.Release.Name`)
- No hyphens in value names

### Structure

Prefer flat over nested. Nested requires existence checks at every level:

```yaml
# Flat — simpler, works with --set directly
serverPort: 8080
serverHost: "0.0.0.0"

# Nested — use only when many related variables exist
server:
  port: 8080
  host: "0.0.0.0"
```

Prefer maps over arrays for `--set` ergonomics:

```yaml
# Map — easy to override one entry
servers:
  foo:
    port: 80
  bar:
    port: 443

# Array — awkward with --set (servers[0].port=80)
servers:
  - name: foo
    port: 80
```

### Type Safety

- Quote all strings: `{{ .Values.foo | quote }}`
- Large integers may become scientific notation; store as strings and convert:
  `{{ int .Values.bigNumber }}`
- Use `required` for mandatory values: `{{ required "image.tag is required" .Values.image.tag }}`
- Use `fail` for conditional validation: `{{ if condition }}{{ fail "message" }}{{ end }}`

### Documentation

Document every property with a comment starting with the parameter name:

```yaml
# -- Number of replicas for the main deployment
replicaCount: 1

# -- Image configuration
image:
  # -- Container image registry
  registry: docker.io
  # -- Container image repository
  repository: myorg/myapp
  # -- Container image tag (defaults to Chart.appVersion)
  tag: ""
  # -- Image digest (overrides tag when set)
  # @default -- ""
  digest: ""
```

### Do NOT

- Hardcode namespaces — use `{{ .Release.Namespace }}`
- Put secrets in values.yaml committed to git
- Use `latest`/`head`/`canary` image tags

---

## _helpers.tpl Patterns

### Standard Helpers

Every chart needs these five. All names prefixed with chart name:

1. **`mychart.name`** — Chart name with optional override, truncated to 63 chars
2. **`mychart.fullname`** — Release + chart name combo, truncated to 63 chars (DNS limit)
3. **`mychart.chart`** — Chart name + version for `helm.sh/chart` label
4. **`mychart.labels`** — All standard labels
5. **`mychart.selectorLabels`** — Only immutable selector labels

### Advanced Helpers

```yaml
{{/* Image string from registry/repository/tag/digest */}}
{{- define "mychart.image" -}}
{{- if .Values.image.digest }}
{{- printf "%s/%s@%s" .Values.image.registry .Values.image.repository .Values.image.digest }}
{{- else }}
{{- printf "%s/%s:%s" .Values.image.registry .Values.image.repository (default .Chart.AppVersion .Values.image.tag) }}
{{- end }}
{{- end }}
```

### Rules

- Always use `include` (not `template`) — `include` returns a string that can be piped
- Use `{{- }}` whitespace chomping to minimize blank lines
- Template comments `{{- /* comment */ -}}` stay hidden. YAML `#` comments are
  visible in `--debug` output
- Do not place YAML `#` comments on lines with `required` function

---

## Standard Labels

### Full Label Set (all resources)

```yaml
labels:
  app.kubernetes.io/name: {{ include "mychart.name" . }}
  app.kubernetes.io/instance: {{ .Release.Name }}
  app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
  app.kubernetes.io/component: frontend          # optional
  app.kubernetes.io/part-of: my-platform         # optional
  helm.sh/chart: {{ include "mychart.chart" . }}
  app.kubernetes.io/managed-by: {{ .Release.Service }}
```

### Selector Labels (Deployment matchLabels)

Only stable, immutable fields:

```yaml
matchLabels:
  app.kubernetes.io/name: {{ include "mychart.name" . }}
  app.kubernetes.io/instance: {{ .Release.Name }}
```

Never include version or chart in selectors.

### Common Labels and Annotations (all resources)

Provide `commonLabels` and `commonAnnotations` in values.yaml so admins can tag
every resource in one place — critical for cost allocation, team ownership,
compliance, and tooling that filters by annotation (Prometheus, ArgoCD, etc.).

```yaml
# values.yaml
commonAnnotations: {}
commonLabels: {}
```

Inject `commonLabels` into the standard labels helper so they appear on every
resource automatically:

```yaml
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}
```

Create a separate `mychart.annotations` helper for `commonAnnotations`:

```yaml
{{- define "mychart.annotations" -}}
{{- with .Values.commonAnnotations }}
{{- toYaml . }}
{{- end }}
{{- end }}
```

Use it in every resource metadata block:

```yaml
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with (include "mychart.annotations" .) }}
  annotations:
    {{- . | nindent 4 }}
  {{- end }}
```

For resources with their own annotations (Service, Ingress, ServiceAccount),
merge common and resource-specific:

```yaml
  {{- $ann := include "mychart.annotations" . }}
  {{- if or $ann .Values.service.annotations }}
  annotations:
    {{- with $ann }}
    {{- . | nindent 4 }}
    {{- end }}
    {{- with .Values.service.annotations }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
  {{- end }}
```

---

## Library Charts

Set `type: library` in Chart.yaml. Cannot be installed directly.

All templates must be in `_*.tpl` or `_*.yaml` files. Provide named templates
that consuming charts call via `include`.

```yaml
# Consumer's Chart.yaml
dependencies:
  - name: common
    version: ~2.x
    repository: oci://registry-1.docker.io/bitnamicharts
```

Library charts share the parent's `.Values` and `.Files` scope.

**Bitnami Common Chart** (v2.38.0+) is the canonical example. Key helpers:
`common.names.fullname`, `common.labels.standard`, `common.labels.matchLabels`,
`common.images.image`, `common.resources.preset`, `common.tplvalues.render`,
`common.capabilities.deployment.apiVersion`, `common.compatibility.renderSecurityContext`.

---

## OCI Distribution

OCI is the recommended distribution method for Helm 4.

### Push

```bash
helm package ./mychart
helm push mychart-0.1.0.tgz oci://ghcr.io/myorg/charts
```

### Pull / Install

```bash
helm pull oci://ghcr.io/myorg/charts/mychart --version 0.1.0
helm install myrelease oci://ghcr.io/myorg/charts/mychart --version 0.1.0

# Helm 4: install by digest (immutable)
helm install myrelease oci://ghcr.io/myorg/charts/mychart@sha256:abc123...
```

### Authentication

```bash
echo "$TOKEN" | helm registry login ghcr.io -u USERNAME --password-stdin
```

### Notes

- Tags must match SemVer (no `latest` tag)
- SemVer `+` becomes `_` in OCI tags
- `.prov` files pushed as extra OCI manifest layer automatically if present
- Dependencies can reference OCI repos: `repository: "oci://ghcr.io/org/charts"`
- OCI has no search/list protocol; use Artifact Hub for discovery

---

## Subchart Dependencies

Declared in Chart.yaml `dependencies:` section.

### Version Ranges

Use semver ranges, not exact pins. `Chart.lock` records exact resolved versions.

```yaml
dependencies:
  - name: postgresql
    version: ~12.x          # >=12.0.0, <13.0.0
    repository: oci://registry-1.docker.io/bitnamicharts
    condition: postgresql.enabled
    tags:
      - database
```

- **`condition`**: Boolean value path to enable/disable. Defaults to true.
- **`tags`**: Group related optional dependencies for unified toggling.
- Conditions override tags. First condition path that exists wins.
- `global:` values are automatically available to all subcharts.
- Run `helm dependency update` after changing dependencies.
- Commit `Chart.lock` for reproducible builds.

---

## values.schema.json

Must be named `values.schema.json` alongside `values.yaml`. Validated during
`helm install`, `upgrade`, `lint`, and `template`.

### Generation Tools

- **`dadav/helm-schema`** (v0.23.0) — Generates from `@schema` annotations in
  values.yaml. Supports JSON Schema Draft 7. Has pre-commit hook. GPG-signed
  releases for Helm 4 plugin verification.
- **`losisin/helm-values-schema-json`** — Helm plugin. Supports multiple drafts
  (4/6/7/2019/2020).

### Annotation Syntax (dadav/helm-schema)

```yaml
# @schema
# type: integer
# minimum: 1
# maximum: 100
# @schema
replicaCount: 1

# @schema
# type: string
# enum: ["ClusterIP", "NodePort", "LoadBalancer"]
# @schema
serviceType: ClusterIP
```

### Validation Patterns

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": "^[a-z0-9/._-]+$"
        },
        "tag": { "type": "string" }
      }
    },
    "service": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["ClusterIP", "NodePort", "LoadBalancer"]
        }
      }
    }
  }
}
```

`required` alone doesn't ensure non-empty strings. Add `pattern` regex for that.

### IDE Integration

Add to values.yaml first line for VS Code autocomplete:
```yaml
# yaml-language-server: $schema=values.schema.json
```

---

## helm-docs

Auto-generates README.md from values.yaml comments and Chart.yaml metadata.

### Comment Syntax

```yaml
# -- Number of replicas
replicaCount: 1

# -- Image configuration
image:
  # -- Image registry
  registry: docker.io
  # -- Image tag
  # @default -- Chart.appVersion
  tag: ""
  # @ignored — excluded from docs
  internalField: true
```

- `# --` prefix marks a field for documentation
- `@default -- text` overrides the displayed default value
- `@ignored` excludes the field from generated docs
- Leaf nodes auto-appear. Non-empty collections only appear with description comments.

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/norwoodj/helm-docs
    rev: v1.14.2
    hooks:
      - id: helm-docs
        args: [--chart-search-root=charts]
```

### Custom Template

Create `README.md.gotmpl` in chart root for custom layout. Available sub-templates:
`chart.header`, `chart.valuesSection`, `chart.valuesTableMd`,
`chart.requirementsSection`, `chart.maintainersSection`, `chart.sourcesSection`.

---

## CRD Management

### Why Not `crds/` Directory

Helm's native `crds/` directory installs CRDs once but **never upgrades or deletes**
them. Not templated (no conditional logic). `--dry-run` doesn't work with CRDs.

Every major chart avoids it. Three approaches used in production:

### Approach 1: Templates with Conditional Flags (cert-manager)

```yaml
# values.yaml
crds:
  enabled: false    # User must explicitly opt in
  keep: true        # Prevent Helm from deleting CRDs on uninstall

# templates/crds.yaml
{{- if .Values.crds.enabled }}
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: certificates.cert-manager.io
  annotations:
    {{- if .Values.crds.keep }}
    "helm.sh/resource-policy": keep
    {{- end }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec: ...
{{- end }}
```

### Approach 2: Separate CRD Chart (kube-prometheus-stack)

Separate `prometheus-operator-crds` sub-chart dependency. CRD updates trigger
major version bumps. Cluster operators manage CRDs independently.

### Approach 3: CRDs Inline (Cilium)

CRDs included directly in chart templates. Simple but tightly couples CRD lifecycle
to chart releases.

**Recommendation**: Approach 1 for most charts. Approach 2 for complex CRD sets
shared across multiple charts.

---

## .helmignore

Must exclude development and sensitive files from chart packages:

```
# VCS
.git/
.github/
.gitignore

# IDE/OS
.DS_Store
.idea/
.vscode/
*.swp
*.tmp

# CI
.gitlab-ci.yml
Jenkinsfile
Makefile

# Security
.env
*secret*
*.key
*.pem
*.crt

# Development
*.md.gotmpl
ci/
```

Notes:
- `**` glob syntax is NOT supported (uses Go's `filepath.Match`)
- Always inspect packaged charts before publishing: `tar tzf mychart-0.1.0.tgz`
