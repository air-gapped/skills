# Security Reference

## Table of Contents
- [SecurityContextConstraints (SCC)](#securitycontextconstraints-scc)
- [Pod Security Admission (PSA)](#pod-security-admission-psa)
- [Supply Chain Security](#supply-chain-security)
- [Secret Management](#secret-management)
- [Network Policies](#network-policies)
- [Compliance Operator](#compliance-operator)
- [SELinux and Security Model](#selinux-and-security-model)

---

## SecurityContextConstraints (SCC)

### restricted-v2 (Default Since OCP 4.11)

All authenticated users get `restricted-v2`. Key differences from v1:

| Field | restricted v1 | restricted-v2 |
|-------|--------------|---------------|
| Capabilities dropped | KILL, MKNOD, SETUID, SETGID | ALL |
| allowPrivilegeEscalation | Allowed | false (enforced) |
| seccompProfile | Unset/Unconfined allowed | RuntimeDefault required |
| runAsUser | MustRunAsRange | MustRunAsRange |

**Gotcha**: newly created clusters grant `restricted-v2` (not `restricted`) to all
authenticated users. Upgraded clusters retain both, creating a divergence.

### SCC Selection Priority

1. Highest priority value first
2. Most restrictive wins (among equal priority)
3. Alphabetical name (among equal restrictiveness)

**SCC matching is validation-based, not mutation-based.** A pod's security context
must fit within an SCC's allowed ranges. The SCC system does NOT mutate values.

### Minimum Compliant SecurityContext

Compatible with BOTH PSS restricted AND OpenShift restricted-v2:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
      # Do NOT set runAsUser -- let OpenShift assign
      # readOnlyRootFilesystem: true  # Recommended, not required
```

### Allowed Volume Types (restricted-v2)

configMap, downwardAPI, emptyDir, persistentVolumeClaim, projected, secret.
**No** hostPath, nfs, or other host-mounted volumes.

### Seccomp Profile Under restricted-v2

The `runtime/default` seccomp profile blocks certain syscalls. Workloads that
previously ran unconfined (pre-4.11) may fail silently. Custom seccomp profiles
can be configured if your app requires blocked syscalls.

### Namespace UID Range

Annotation `openshift.io/sa.scc.uid-range: start/length` (e.g., `1000090000/10000`).

**Gotcha**: pre-existing namespace annotations are NOT overwritten. MTC (Migration
Toolkit for Containers) can create overlapping UID ranges between namespaces.

---

## Pod Security Admission (PSA)

### How It Works on OpenShift

OpenShift uses PSA **alongside** SCCs, not instead of them. A pod must pass both.

- **Global enforcement**: `privileged` profile (allows everything)
- **Global warnings/audits**: `restricted` profile
- **Auto-labeling**: a controller labels namespaces with PSA level matching the most
  privileged SCC available to service accounts in that namespace
- `openshift-*` namespaces default to `restricted` enforcement from OCP 4.12

### Per-Namespace Override

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

**Caution**: overriding without understanding SCC interaction can cause pods to be
rejected by PSA even though they pass SCC validation.

---

## Supply Chain Security

### Image Signing (Cosign / Sigstore / RHTAS)

**ClusterImagePolicy** (GA in OCP 4.21):
- Enforces sigstore signature verification cluster-wide
- In 4.21, the default `openshift` ClusterImagePolicy is active by default for
  `quay.io/openshift-release-dev/ocp-release` images
- **Upgrade gotcha**: custom ClusterImagePolicy named `openshift` in OCP 4.20 sets
  `Upgradeable=False` -- remove before upgrading to 4.21

Three verification methods:
1. Fulcio CA + Rekor transparency log (keyless)
2. Cosign public key pairs
3. BYO-PKI with X.509 certificates (GA in 4.21)

**RHTAS** (Red Hat Trusted Artifact Signer): deploys on-prem Sigstore stack
(Fulcio, Rekor, TSA, TUF) via operator. Supports OCP 4.15-4.19.

### SBOM and Attestation

**Tekton Chains** (installed by default with OpenShift Pipelines Operator):
- Automatically snapshots completed TaskRun/PipelineRun
- Generates SLSA provenance (v0.2 or v1.0 format)
- Signs with cosign keys stored as `signing-secrets` in `openshift-pipelines` namespace
- Stores attestations in OCI registry

Task result naming convention is critical:
- `*IMAGE_URL` / `*IMAGE_DIGEST` for output images
- `CHAINS-GIT_URL` / `CHAINS-GIT_COMMIT` for input provenance

### Conforma (Enterprise Contract)

Formerly Enterprise Contract (EC). Uses OPA with Rego rules to validate:
- Container images are signed and attested by known/trusted build systems
- Runs automatically during environment promotion (dev -> staging -> prod)
- Part of RHADS-SSC (Red Hat Advanced Developer Suite - Software Supply Chain)

### RHACS (Advanced Cluster Security / Stackrox)

Architecture: Central + PostgreSQL, Scanner (Trivy-based), Sensor (eBPF DaemonSet),
Admission Controller (ValidatingWebhookConfiguration).

- Only supports Cosign signatures for image verification
- Re-fetches and verifies signatures every 4 hours
- Hundreds of built-in policies (CIS, NIST, CVE detection, runtime analysis)
- For blocking unsigned images: create policy with "Image Signature Verified By",
  set to "Inform and enforce", configure admission controller

### Vulnerability Scanning

- **Quay + Clair**: continuous scanning of every pushed image
- **Container Security Operator**: bridges Quay/Clair metadata into OCP via
  `ImageManifestVuln` objects
- **RHACS Scanner**: Trivy-based, runtime scanning (not just registry-time)
- Scan in CI/CD pipeline (shift-left) AND continuously in registry

---

## Secret Management

### External Secrets Operator (ESO)

GA as day-2 operator for OCP 4.20+. Supports: CyberArk Conjur, HashiCorp Vault,
AWS/GCP/Azure secret managers, IBM Cloud Secrets Manager, AWS SSM.

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-secret
spec:
  refreshInterval: 5m
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: my-k8s-secret
  data:
  - secretKey: password
    remoteRef:
      key: secret/data/myapp
      property: password
```

### Best Practices

- **Volume mounts over env vars**: env vars leak into logs, crash dumps, child processes
- **Dynamic credentials**: use `VaultDynamicSecret` CRs with short TTLs (15m-1h)
- **Never inject dynamic secrets as env vars** -- use volumeMounts so rotations
  are picked up automatically
- **Zero-trust GitOps**: ESO Generator creates GitHub tokens with max 60-minute
  lifespan, auto-rotating
- **etcd encryption**: OpenShift Secrets are NOT encrypted at rest by default --
  they are base64-encoded. Enable etcd encryption for production

### Vault Secrets Operator (VSO)

Red Hat certified, supports OCP 4.12+. Available via OperatorHub or Helm.

---

## Network Policies

### Default-Deny Foundation

Always start with default-deny for both ingress and egress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

Then explicitly allow:
1. Cross-namespace traffic by label
2. Ingress from OpenShift Router
3. Ingress from OpenShift Monitoring
4. Egress for DNS (port 53 to `openshift-dns`)
5. Egress to specific services

### Common Trap: AND vs OR

```yaml
# AND condition (both must match):
from:
- podSelector:
    matchLabels: {app: frontend}
  namespaceSelector:
    matchLabels: {env: prod}

# OR condition (either matches):
from:
- podSelector:
    matchLabels: {app: frontend}
- namespaceSelector:
    matchLabels: {env: prod}
```

Combining `podSelector` and `namespaceSelector` in the same `from` entry creates
AND. Separate entries create OR.

### AdminNetworkPolicy (ANP) -- Tech Preview OCP 4.14+

Cluster-scoped policies that tenant NetworkPolicies cannot override.
Priority order: ANP > NetworkPolicy > BaselineAdminNetworkPolicy (BANP).

Only one BANP named "default" is allowed. Currently v1alpha1.

**Gotcha**: empty namespace selector in ANP matches ALL namespaces including
infrastructure namespaces like kube-system.

### User-Defined Networks (UDN) -- OCP 4.18+

Complete L2/L3 isolation for critical namespaces. Prevents lateral movement.

**Gotcha**: namespace must be labeled with `k8s.ovn.org/primary-user-defined-network`
at creation time -- cannot be added later. UDN pods are isolated from the default
network (most cluster services including internal registry are inaccessible by default).

---

## Compliance Operator

### Supported Profiles (OCP 4.19+)

| Profile | Standard | Variants |
|---------|----------|----------|
| `ocp4-cis` / `ocp4-cis-node` | CIS Benchmark | `ocp4-cis-1-7` (pinned v1.7.0) |
| `ocp4-moderate` / `ocp4-moderate-node` | NIST 800-53 Moderate | `ocp4-moderate-rev-4` (FedRAMP) |
| `ocp4-high` / `ocp4-high-node` | NIST 800-53 High | -- |
| `ocp4-stig` / `ocp4-stig-node` | DISA STIG | `ocp4-stig-v2r3` (pinned) |
| `ocp4-pci-dss` / `ocp4-pci-dss-node` | PCI-DSS | `ocp4-pci-dss-3-2` (v3.2.1) |
| `ocp4-bsi` / `ocp4-bsi-node` | BSI Basic Protection | `ocp4-bsi-2022` (pinned) |
| `ocp4-nerc-cip` / `ocp4-nerc-cip-node` | NERC CIP | -- |

Two scan categories: **platform** (cluster-level) and **node** (RHCOS host-level).
Both must be used together.

**HIPAA** is not a dedicated profile -- use NIST 800-53 Moderate/High as a proxy.
HIPAA workload-level compliance is addressed via RHACS policies.

---

## SELinux and Security Model

OpenShift assigns per-namespace:
- UID range (`openshift.io/sa.scc.uid-range`)
- Supplemental GID range (`openshift.io/sa.scc.supplemental-groups`)
- Unique SELinux MCS label (`openshift.io/sa.scc.mcs`)

Ranges are non-overlapping across namespaces. Even with `anyuid` SCC, pods still
get the namespace's SELinux MCS labels, preventing cross-namespace file access.

The `container_t` SELinux type is assigned to all containers by default, restricting
host resource access regardless of UID.
