# Packaging Formats Reference

## Table of Contents
- [Helm on OpenShift](#helm-on-openshift)
- [OLM v1 ClusterExtensions](#olm-v1-clusterextensions)
- [OLM v0 (Legacy)](#olm-v0-legacy)
- [Kustomize on OpenShift](#kustomize-on-openshift)
- [Helm + Kustomize Hybrid](#helm--kustomize-hybrid)
- [Certified Helm Charts](#certified-helm-charts)
- [Certified Operators](#certified-operators)
- [OpenShift Templates (Legacy)](#openshift-templates-legacy)

---

## Helm on OpenShift

### Version Status (2026)

- **Helm 4.0.0** released November 12, 2025 (Server-Side Apply default)
- **The web terminal ships Helm 3**: v3.17.1 on 4.19-4.21, v3.20.2 on 4.22 (Web Terminal Operator 1.17)
- **Argo CD 3.5+ renders with Helm 4** (upstream pins 4.2.1 on 3.5.x, 4.3.1 on the 3.6 RCs; 3.3.x and 3.4.x pin 3.19.4). **OpenShift GitOps 1.22 ships Argo CD 3.5.3 with Helm 4.2.4**; GitOps 1.21 and 1.20 ship Helm 3.19.4. Upgrading Argo CD 3.4 → 3.5 can change rendered manifests through Helm 4's null-coalescing change with no chart edit (argo-cd#29068, open) — diff a render across the bump
- **Helm 3 EOL**: v3.22 (2026-09-10) was the final feature release; security patches only until **2027-02-10**, then no further Helm 3 releases. Migrate charts and pipelines to Helm 4 before that date
- **Test charts under both Helm 3 and Helm 4**: the web terminal and `oc`-side tooling render with Helm 3, GitOps 1.22+ with Helm 4

### OpenShift Detection

```yaml
{{- define "mychart.isOpenshift" -}}
{{- if .Capabilities.APIVersions.Has "security.openshift.io/v1" -}}true{{- end -}}
{{- end -}}
```

For Route-specific:
```yaml
{{- if .Capabilities.APIVersions.Has "route.openshift.io/v1" }}
```

**Important**: `.Capabilities.APIVersions.Has` works in `helm install`/`upgrade`
AND `helm template`. Do NOT use `lookup` for detection -- it only works with
a live cluster connection.

### SCC-Compatible Values

Community charts that assume root or hardcoded UIDs fail on OpenShift. Override:

```yaml
# values-openshift.yaml
podSecurityContext:
  runAsUser: null    # Let OpenShift assign
  fsGroup: null      # Let OpenShift assign
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault

containerSecurityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  readOnlyRootFilesystem: true  # Recommended, not required by restricted-v2
```

### Route vs Ingress in Charts

Controller-specific Ingress annotations (e.g., `nginx.ingress.kubernetes.io/*`)
are **silently ignored** by the OpenShift Router. Only OpenShift-aware annotations
are honored:
- `route.openshift.io/termination`
- `haproxy.router.openshift.io/balance`
- `haproxy.router.openshift.io/timeout`

An Ingress without a hostname will NOT create a Route.

Ingress-to-Route conversion supports only **edge TLS** termination.
Passthrough and re-encrypt require native Route objects.
Wildcard hosts (`*.example.com`) are Route-only.

### Conditional Route/Ingress Template

```yaml
{{- if .Capabilities.APIVersions.Has "route.openshift.io/v1" }}
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  to:
    kind: Service
    name: {{ include "mychart.fullname" . }}
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
{{- else }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  rules:
  - host: {{ .Values.ingress.host }}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {{ include "mychart.fullname" . }}
            port:
              name: http
{{- end }}
```

### TLS Gotcha

If using OpenShift Routes with edge TLS termination, TLS in the Ingress spec must
be deactivated to avoid double termination.

### Helm Chart Repo

`charts.openshift.io` is configured by default since OCP 4.8.

---

## OLM v1 ClusterExtensions

GA in OpenShift 4.18. Coexists with OLM v0 (no forced migration).

### Key Changes from OLM v0

| Aspect | OLM v0 | OLM v1 |
|--------|--------|--------|
| API | Subscription + OperatorGroup | ClusterExtension |
| Scope | Namespace or cluster | Cluster only (AllNamespaces) |
| RBAC | Automatic (OLM ran as cluster-admin) | User-provided ServiceAccount |
| Catalog API | CatalogSource (CRD-based) | ClusterCatalog (REST API via catalogd) |
| Bundle handling | Directly applied | Converted to Helm charts internally |
| Permission model | Escalated | Least privilege (halt-and-wait on insufficient RBAC) |

### ClusterExtension Example

```yaml
apiVersion: olm.operatorframework.io/v1
kind: ClusterExtension
metadata:
  name: my-operator
spec:
  namespace: my-operator-system
  serviceAccount:
    name: my-operator-installer
  source:
    sourceType: Catalog
    catalog:
      packageName: my-operator
      channels:
      - name: stable
      version: "~3.12"       # semver range
  install:
    preflight:
      crdUpgradeSafety:
        enforcement: None     # or Strict
```

### RBAC Setup (Required Before Install)

OLM v1 does NOT manage RBAC. You must create ServiceAccount + roles + bindings.
The RBAC PreAuthorizer validates permissions before installation. On failure,
the ClusterExtension status shows the specific missing permissions.

Reference RBAC pattern (from operator-controller samples for ArgoCD):

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-operator-installer
  namespace: my-operator-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: my-operator-installer
rules:
# OLM finalizer management
- apiGroups: [olm.operatorframework.io]
  resources: [clusterextensions/finalizers]
  verbs: [update]
# Only with the experimental Boxcutter runtime (ClusterObjectSet revisions)
- apiGroups: [olm.operatorframework.io]
  resources: [clusterobjectsets, clusterobjectsets/finalizers]
  verbs: ["*"]
# Operator's own CRDs
- apiGroups: [my-operator.example.com]
  resources: ["*"]
  verbs: ["*"]
# Common resources the operator needs
- apiGroups: [""]
  resources: [configmaps, secrets, services, serviceaccounts]
  verbs: ["*"]
- apiGroups: [apps]
  resources: [deployments]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: my-operator-installer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: my-operator-installer
subjects:
- kind: ServiceAccount
  name: my-operator-installer
  namespace: my-operator-system
```

### Discovering Required Permissions

No easy method exists. Options:
1. Inspect the CSV's `spec.install.spec.permissions[]` and `spec.install.spec.clusterPermissions[]`
2. Use `grpcurl` against the catalog GRPC API
3. Start with broad permissions, then narrow using the "halt and wait" error messages
4. Use the community `vp-rbac` Helm chart from Validated Patterns

### End-User API Access

OLM v1 does not grant users access to operator CRDs. Create three role tiers:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: my-operator-view
  labels:
    rbac.authorization.k8s.io/aggregate-to-view: "true"
rules:
- apiGroups: [my-operator.example.com]
  resources: ["*"]
  verbs: [get, list, watch]
---
# Similar for edit (add create/update/patch/delete) and admin (add wildcard)
```

### Predefined Catalogs

| Catalog | Priority | Content |
|---------|----------|---------|
| openshift-redhat-operators | -100 | Red Hat operators |
| openshift-certified-operators | -200 | Partner certified |
| openshift-redhat-marketplace | -300 | Marketplace |
| openshift-community-operators | -400 | Community |

All poll every 10 minutes by default.

### Version Management

- Semver ranges: `~3.12` (>=3.12.0, <3.13.0), `>=3.10, <4.0`
- Manual downgrade: `upgradeConstraintPolicy: SelfCertified`

---

## OLM v0 (Legacy)

Still fully supported for the entire OCP 4 lifecycle. No removal date announced.

### Key Gotcha

**Automatic approval strategy** means OLM upgrades operators without human
intervention. Use `Manual` approval in production namespaces.

If a new CSV fails to reach Succeeded state, both old and new CSVs persist.
Manual intervention required to clean up failed InstallPlans.

---

## Kustomize on OpenShift

Built into both `kubectl` and `oc` CLIs.

### Standard Directory Layout

```
app/
  base/
    deployment.yaml
    service.yaml
    kustomization.yaml
  overlays/
    dev/
      kustomization.yaml
      patch-replicas.yaml
    staging/
      kustomization.yaml
    prod/
      kustomization.yaml
      patch-resources.yaml
```

### OpenShift CRDs

For OpenShift custom resources (Routes, SCCs), you must provide the OpenAPI schema
to Kustomize for strategic merge patching to work correctly on CRD fields.

### Key Limitation

`oc apply -k` and `kubectl apply -k` do **NOT** support the `--enable-helm` flag.
This only works with `kustomize build . --enable-helm` or via ArgoCD with
`kustomizeBuildOptions: "--enable-helm"`.

---

## Helm + Kustomize Hybrid

The dominant pattern for OpenShift GitOps:

```yaml
# kustomization.yaml
helmCharts:
- name: myapp
  repo: https://charts.example.com
  version: 1.0.0
  releaseName: myapp
  valuesFile: values.yaml
  namespace: myapp

patches:
- target:
    kind: Deployment
    name: myapp
  patch: |-
    - op: add
      path: /spec/template/spec/containers/0/resources/limits/cpu
      value: "2"
```

In ArgoCD, enable with:
```yaml
spec:
  source:
    kustomize:
      buildOptions: "--enable-helm"
```

---

## Certified Helm Charts

### chart-verifier Mandatory Checks

For partner/RedHat profiles:
- `is-helm-v3` -- chart is Helm v3
- `has-readme` -- README.md present
- `contains-test` -- test templates exist
- `has-kubeversion` -- kubeVersion set in Chart.yaml
- `contains-values-schema` -- values.schema.json present
- `not-contains-crds` -- no CRDs in chart (use operator for CRDs)
- `not-contain-csi-objects` -- no CSI objects
- `images-are-certified` -- all referenced images are Red Hat certified
- `helm-lint` -- passes `helm lint`
- `chart-testing` -- passes `helm test`
- `contains-values` -- values.yaml present
- `required-annotations-present` -- `charts.openshift.io/name` annotation
- `signature-is-valid` -- valid chart signature

### Distribution Methods

1. Publish in Red Hat's Helm chart repository
2. Publish in your own repo with report-only submission
3. Submit both chart and report

---

## Certified Operators

### Capability Maturity Levels

| Level | Name | Helm | Ansible | Go |
|-------|------|------|---------|-----|
| L1 | Basic Install | Yes | Yes | Yes |
| L2 | Seamless Upgrades | Yes | Yes | Yes |
| L3 | Full Lifecycle | No | Yes | Yes |
| L4 | Deep Insights | No | Yes | Yes |
| L5 | Auto Pilot | No | Yes | Yes |

**Hybrid Helm Operator** (Operator SDK) combines Helm charts with Go APIs to
overcome the L2 ceiling. Available since OCP 4.10+.

### Image Pre-Certification

All container images referenced in an Operator Bundle must already be certified
and published in the Red Hat Ecosystem Catalog **before** operator certification.

---

## OpenShift Templates (Legacy)

- Template Service Broker: deprecated OCP 4.2, removed OCP 4.4
- `oc process` and `oc new-app --template` still work in OCP 4.18+
- NOT formally deprecated as a feature but "no longer recommended"
- Not portable to vanilla Kubernetes -- the primary reason to avoid
- Multiple Red Hat products have deprecated their templates in favor of Operators
