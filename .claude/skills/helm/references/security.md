# Helm Chart Security Reference

## Table of Contents
- [SecurityContext Defaults](#securitycontext-defaults)
- [RBAC Templates](#rbac-templates)
- [NetworkPolicy Templates](#networkpolicy-templates)
- [Image Digest Pinning](#image-digest-pinning)
- [Secret Management](#secret-management)
- [Supply Chain Security](#supply-chain-security)
- [Artifact Hub](#artifact-hub)

---

## SecurityContext Defaults

Target the **Pod Security Standards "restricted" profile** — the strictest PSS level,
also compatible with OpenShift's `restricted-v2` SCC.

### Container SecurityContext

```yaml
# values.yaml
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
```

### Pod SecurityContext

```yaml
podSecurityContext:
  fsGroup: 1001
  fsGroupChangePolicy: OnRootMismatch   # Faster than Always for large volumes
  runAsNonRoot: true
```

### Read-Only Root Filesystem

Apps needing write access should use `emptyDir` volumes rather than disabling
`readOnlyRootFilesystem`:

```yaml
volumes:
  - name: tmp
    emptyDir: {}
volumeMounts:
  - name: tmp
    mountPath: /tmp
```

### Pod Security Standards Namespace Labels

For clusters with PSS enforcement:

```yaml
pod-security.kubernetes.io/enforce: restricted
pod-security.kubernetes.io/warn: restricted
pod-security.kubernetes.io/audit: restricted
```

### OpenShift Adaptation

On OpenShift, hardcoded `runAsUser`/`runAsGroup`/`fsGroup` conflict with the
`restricted-v2` SCC which assigns random UIDs. Use the Bitnami
`adaptSecurityContext: auto` pattern — see `openshift.md` for details.

---

## RBAC Templates

### values.yaml Structure

Separate `rbac` and `serviceAccount` keys (not nested):

```yaml
rbac:
  create: true
  # rules: []   # Optional: additional custom rules

serviceAccount:
  create: true
  name: ""              # Defaults to fullname
  automount: false      # Security: don't mount token unless needed
  annotations: {}
```

### ServiceAccount Template

```yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "mychart.serviceAccountName" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
automountServiceAccountToken: {{ .Values.serviceAccount.automount }}
{{- end }}
```

### Role/RoleBinding Template

```yaml
{{- if .Values.rbac.create -}}
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]
  {{- with .Values.rbac.rules }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: {{ include "mychart.fullname" . }}
subjects:
  - kind: ServiceAccount
    name: {{ include "mychart.serviceAccountName" . }}
    namespace: {{ .Release.Namespace }}
{{- end }}
```

**Never grant `verbs: ["*"]` on secrets.** Enumerate specific verbs needed.

---

## NetworkPolicy Templates

### values.yaml

```yaml
networkPolicy:
  enabled: false          # Enable when CNI supports it
  allowSameNamespace: true
  additionalIngress: []
  additionalEgress: []
```

### Template

```yaml
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        {{- if .Values.networkPolicy.allowSameNamespace }}
        - podSelector: {}
        {{- end }}
      ports:
        - protocol: TCP
          port: {{ .Values.service.port }}
    {{- with .Values.networkPolicy.additionalIngress }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
  egress:
    - to: []     # Allow DNS
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    {{- with .Values.networkPolicy.additionalEgress }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
{{- end }}
```

---

## Image Digest Pinning

### values.yaml Pattern (Bitnami Standard)

```yaml
image:
  registry: docker.io
  repository: myorg/myapp
  tag: "1.0.0"
  digest: ""              # sha256:... overrides tag when set
  pullPolicy: IfNotPresent

# Global overrides cascade to all sub-charts
global:
  imageRegistry: ""
  imagePullSecrets: []
```

### Image Helper Template

```yaml
{{- define "mychart.image" -}}
{{- $registry := default .Values.image.registry .Values.global.imageRegistry -}}
{{- if .Values.image.digest -}}
{{- printf "%s/%s@%s" $registry .Values.image.repository .Values.image.digest -}}
{{- else -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s/%s:%s" $registry .Values.image.repository $tag -}}
{{- end -}}
{{- end -}}
```

Usage: `image: {{ include "mychart.image" . }}`

---

## Secret Management

Three approaches ranked by maturity:

### 1. External Secrets Operator (Recommended)

Vault-backed, cloud IAM, continuous sync. Best for multi-cloud.

```yaml
# templates/external-secret.yaml
{{- if .Values.externalSecret.enabled }}
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: {{ .Values.externalSecret.secretStoreName }}
    kind: ClusterSecretStore
  target:
    name: {{ include "mychart.fullname" . }}
  data:
    {{- range .Values.externalSecret.data }}
    - secretKey: {{ .secretKey }}
      remoteRef:
        key: {{ .remoteKey }}
    {{- end }}
{{- end }}
```

### 2. helm-secrets + SOPS

Encrypt-in-Git workflow. SOPS donated to CNCF; age encryption preferred over PGP.

```bash
# Encrypt
sops -e -i secrets.yaml

# Use with Helm
helm secrets upgrade myrelease ./mychart -f secrets.yaml
```

### 3. Sealed Secrets

Encrypt into SealedSecret CRs decryptable only by in-cluster controller. Good
for GitOps.

### Rules

- Never commit plaintext secrets to values.yaml
- `.gitignore` all `.dec` files
- Implement automated secret scanning in CI
- Rotate secrets on a cadence (critical: 30d, high: 60d, others: 90d)

---

## Supply Chain Security

### Cosign OCI Signing (Modern Approach)

#### Key-Based

```bash
# Sign (always use digest, not tag)
cosign sign --key cosign.key "ghcr.io/myorg/charts/mychart@${DIGEST}"

# Verify
cosign verify --key cosign.pub "ghcr.io/myorg/charts/mychart@${DIGEST}"
```

#### Keyless (OIDC/Sigstore) — Preferred for CI

```bash
# Sign (GitHub Actions — always use digest, not tag)
cosign sign -y "ghcr.io/myorg/charts/mychart@${DIGEST}"

# Verify
cosign verify "ghcr.io/myorg/charts/mychart@${DIGEST}" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  --certificate-identity "https://github.com/myorg/myrepo/.github/workflows/release.yaml@refs/heads/main"
```

GitHub Actions requires `permissions: id-token: write` for keyless signing.

**CRITICAL: Always sign by digest, never by tag.** Tags are mutable — signing
a tag means someone can push a different artifact to the same tag after signing.
Capture the digest from `helm push` output:

```bash
OUTPUT=$(helm push "$PACKAGE" oci://ghcr.io/myorg/charts 2>&1)
DIGEST=$(echo "$OUTPUT" | grep -oP 'sha256:[a-f0-9]+')
cosign sign -y "ghcr.io/myorg/charts/mychart@${DIGEST}"
```

**OCI SemVer gotcha**: OCI tags cannot contain `+`. Helm converts `+` to `_` on
push, but cosign doesn't — use the underscore form when verifying.

### Legacy Helm Provenance (.prov)

GnuPG-based. The `.prov` file contains Chart.yaml content, SHA-256 checksums,
and an OpenPGP signature. Not yet updated for Helm 4.

```bash
helm package --sign --key 'Key Name' --keyring path/to/keyring.secret mychart
helm verify mychart-0.1.0.tgz
helm install --verify mychart-0.1.0.tgz
```

### Flux Verification

Flux natively verifies cosign signatures on Helm OCI charts:

```yaml
# Key-based
spec:
  verify:
    provider: cosign
    secretRef:
      name: cosign-public-keys

# Keyless (OIDC matching)
spec:
  verify:
    provider: cosign
    matchOIDCIdentity:
      - issuer: "^https://token.actions.githubusercontent.com$"
        subject: "^https://github.com/myorg/myrepo.*$"
```

### ArgoCD Limitation

ArgoCD 3.1 introduced native OCI support but does **not** yet have built-in cosign
signature verification (open issue #22609). Flux is ahead here.

### Chart Dependency Pinning

Use semver ranges in Chart.yaml for flexibility, commit `Chart.lock` for exact
reproducibility:

```bash
helm dependency update    # Resolves ranges, writes Chart.lock
helm dependency build     # Reconstructs from Chart.lock
```

---

## Artifact Hub

### Verified Publisher Badge

Automated via `artifacthub-repo.yml` at repo root:

```yaml
repositoryID: <uuid-from-artifact-hub>
owners:
  - name: myorg
    email: helm@myorg.com
```

### Security Annotations in Chart.yaml

```yaml
annotations:
  artifacthub.io/containsSecurityUpdates: "true"
  artifacthub.io/signKey: |
    fingerprint: C874011F0AB405110D02105534365D9472D7468F
    url: https://myorg.com/pgp-key.asc
  artifacthub.io/images: |
    - name: myapp
      image: docker.io/myorg/myapp:1.0.0
      whitelisted: false
  artifacthub.io/license: Apache-2.0
```

Trivy scans container images listed in `artifacthub.io/images` daily for the
latest version.
