# OpenShift Compatibility Reference

## Table of Contents
- [OpenShift Detection](#openshift-detection)
- [SecurityContextConstraints vs Pod Security Standards](#securitycontextconstraints-vs-pod-security-standards)
- [adaptSecurityContext Pattern](#adaptsecuritycontext-pattern)
- [Route vs Ingress](#route-vs-ingress)
- [Arbitrary UID Handling](#arbitrary-uid-handling)
- [Service Serving Certificates](#service-serving-certificates)
- [Chart Certification](#chart-certification)
- [OpenShift Helm Repository Integration](#openshift-helm-repository-integration)

---

## OpenShift Detection

Detect OpenShift at template time using API capability checks:

```yaml
{{- define "mychart.isOpenshift" -}}
{{- if .Capabilities.APIVersions.Has "security.openshift.io/v1" -}}
{{- true -}}
{{- end -}}
{{- end -}}
```

For Route-specific detection:

```yaml
{{- if .Capabilities.APIVersions.Has "route.openshift.io/v1" }}
```

**Important**: `.Capabilities.APIVersions.Has` works in `helm install`/`upgrade`
AND `helm template`. Do NOT use `lookup` function for detection — it only works
with a live cluster connection.

---

## SecurityContextConstraints vs Pod Security Standards

OpenShift 4.11+ runs BOTH systems in parallel. Workloads must pass both:
1. The PSS level enforced on the namespace
2. An available SCC the service account is authorized to use

### SCCs Introduced in OpenShift 4.11

| SCC | PSS Equivalent | Notes |
|-----|---------------|-------|
| `restricted-v2` | restricted | Default for all users |
| `nonroot-v2` | baseline (nonroot) | |
| `hostnetwork-v2` | host network | |

### Minimum Compliant SecurityContext

This is compatible with BOTH PSS restricted AND OpenShift `restricted-v2`:

```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
    runAsNonRoot: true
  containers:
    - securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
```

**Key difference**: On vanilla Kubernetes, specify `runAsUser: 1001`. On OpenShift,
OMIT `runAsUser`, `runAsGroup`, and `fsGroup` — OpenShift assigns these dynamically
per namespace.

---

## adaptSecurityContext Pattern

The Bitnami approach — auto-detect OpenShift and strip UID/GID fields:

### values.yaml

```yaml
global:
  compatibility:
    openshift:
      adaptSecurityContext: auto  # auto | force | disabled
```

- **`auto`**: Detect OpenShift via `.Capabilities.APIVersions.Has`, strip fields
  only when running on OpenShift
- **`force`**: Always strip UID/GID fields (for testing or manual override)
- **`disabled`**: Never strip (vanilla Kubernetes behavior)

### Helper Template

```yaml
{{- define "mychart.renderSecurityContext" -}}
{{- $adaptedContext := .secContext -}}
{{- $adapt := ((.context.Values.global).compatibility).openshift -}}
{{- if $adapt -}}
  {{- if or (eq $adapt.adaptSecurityContext "force")
            (and (eq $adapt.adaptSecurityContext "auto")
                 (include "mychart.isOpenshift" .context)) -}}
    {{- $adaptedContext = omit $adaptedContext "fsGroup" "runAsUser" "runAsGroup" -}}
    {{- if not .secContext.seLinuxOptions -}}
      {{- $adaptedContext = omit $adaptedContext "seLinuxOptions" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- omit $adaptedContext "enabled" | toYaml -}}
{{- end -}}
```

### Usage in Deployment

```yaml
spec:
  template:
    spec:
      {{- if .Values.podSecurityContext }}
      securityContext:
        {{- include "mychart.renderSecurityContext" (dict "secContext" .Values.podSecurityContext "context" $) | nindent 8 }}
      {{- end }}
      containers:
        - name: {{ .Chart.Name }}
          {{- if .Values.containerSecurityContext }}
          securityContext:
            {{- include "mychart.renderSecurityContext" (dict "secContext" .Values.containerSecurityContext "context" $) | nindent 12 }}
          {{- end }}
```

---

## Route vs Ingress

### Auto-Conversion

OpenShift automatically converts Ingress objects to Routes. The created Route
inherits settings from the Ingress but some features are not supported:

**NOT supported via Ingress-to-Route conversion:**
- Weighted backends for traffic splitting
- Sticky sessions
- Wildcard hosts
- Non-HTTP protocols
- Ingress without explicit hostname

### Conditional Template (Recommended)

Offer both Route and Ingress for maximum flexibility:

```yaml
# values.yaml
ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts: []
  tls: []

route:
  enabled: false      # Only on OpenShift
  host: ""
  path: /
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  annotations: {}
```

### Route Template

```yaml
{{- if .Values.route.enabled }}
{{- if .Capabilities.APIVersions.Has "route.openshift.io/v1" }}
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with .Values.route.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- with .Values.route.host }}
  host: {{ . | quote }}
  {{- end }}
  path: {{ .Values.route.path }}
  port:
    targetPort: http
  to:
    kind: Service
    name: {{ include "mychart.fullname" . }}
    weight: 100
  {{- if .Values.route.tls }}
  tls:
    termination: {{ .Values.route.tls.termination | default "edge" }}
    insecureEdgeTerminationPolicy: {{ .Values.route.tls.insecureEdgeTerminationPolicy | default "Redirect" }}
  {{- end }}
{{- end }}
{{- end }}
```

### Route Annotations on Ingress

When using Ingress auto-conversion, control Route behavior via annotations:

```yaml
annotations:
  route.openshift.io/termination: edge
  route.openshift.io/insecureEdgeTerminationPolicy: Redirect
  haproxy.router.openshift.io/balance: roundrobin
  haproxy.router.openshift.io/timeout: 60s
```

---

## Arbitrary UID Handling

OpenShift assigns each namespace a UID range via annotation
`openshift.io/sa.scc.uid-range=1008050000/10000`. Containers run as the first
UID in that range by default.

### Container Image Requirements

- Containers always run in GID 0 (root group)
- Files/directories must be group-owned by 0 and group-writable
- Images must not assume root or a specific UID

### Dockerfile Pattern

```dockerfile
# Create app directory with correct permissions
RUN mkdir -p /app && chgrp -R 0 /app && chmod -R g=u /app

# For apps that need /etc/passwd entry
RUN chmod g=u /etc/passwd

# Set non-root user (used on vanilla K8s, ignored on OpenShift)
USER 1001

COPY --chown=1001:0 . /app
```

### Entrypoint for /etc/passwd

Some apps require a passwd entry for the running UID:

```bash
#!/bin/sh
if ! whoami &> /dev/null; then
  if [ -w /etc/passwd ]; then
    echo "myuser:x:$(id -u):0:My User:${HOME}:/sbin/nologin" >> /etc/passwd
  fi
fi
exec "$@"
```

---

## Service Serving Certificates

OpenShift can auto-generate TLS certificates for internal service communication.

### Service Annotation

```yaml
{{- if include "mychart.isOpenshift" . }}
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.openshift.io/serving-cert-secret-name: {{ include "mychart.fullname" . }}-tls
```

This creates a TLS Secret named `{{ fullname }}-tls` with a cert for
`<service>.<namespace>.svc`.

### CA Bundle Injection

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  annotations:
    service.beta.openshift.io/inject-cabundle: "true"
```

OpenShift injects the service CA bundle into this ConfigMap automatically.

---

## Chart Certification

Red Hat chart certification uses the `chart-verifier` tool.

### Mandatory Checks

| Check | Description |
|-------|------------|
| `is-helm-v3` | Chart uses apiVersion v2 |
| `has-readme` | README.md exists |
| `contains-test` | helm test pod exists |
| `has-kubeversion` | `kubeVersion` set in Chart.yaml |
| `contains-values-schema` | `values.schema.json` exists |
| `not-contains-crds` | No CRDs in chart (use Operators) |
| `not-contain-csi-objects` | No CSI objects |
| `images-are-certified` | All images are Red Hat certified |
| `helm-lint` | `helm lint` passes |
| `chart-testing` | `ct install` passes (needs OpenShift cluster) |
| `contains-values` | `values.yaml` exists |
| `required-annotations-present` | `charts.openshift.io/name` annotation |

### Required Annotations

```yaml
# Chart.yaml
annotations:
  charts.openshift.io/name: mychart
  charts.openshift.io/provider: MyOrg        # optional
  charts.openshift.io/supportURL: https://... # optional
  charts.openshift.io/archs: x86_64,aarch64  # optional
```

### Key Constraints

- **CRDs not allowed** in certified charts; manage via Operators
- **All container images must be Red Hat certified**
- **values.schema.json is required**
- **DeploymentConfig must not be used** (use Deployment)

---

## OpenShift Helm Repository Integration

### Cluster-Scoped Repository

```yaml
apiVersion: helm.openshift.io/v1beta1
kind: HelmChartRepository
metadata:
  name: my-repo
spec:
  name: My Charts
  connectionConfig:
    url: https://charts.example.com
```

### Namespace-Scoped Repository

```yaml
apiVersion: helm.openshift.io/v1beta1
kind: ProjectHelmChartRepository
metadata:
  name: my-repo
  namespace: my-namespace
spec:
  name: My Charts
  connectionConfig:
    url: https://charts.example.com
```

Charts from registered repositories appear in the OpenShift Developer Catalog.
