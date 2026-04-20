# Disconnected / Air-Gapped Environments Reference

## Table of Contents
- [oc-mirror v2](#oc-mirror-v2)
- [Registry Mirroring](#registry-mirroring)
- [OLM in Disconnected Environments](#olm-in-disconnected-environments)
- [Signature Verification](#signature-verification)
- [Helm Charts in Disconnected Environments](#helm-charts-in-disconnected-environments)
- [GitOps (ArgoCD) Disconnected](#gitops-argocd-disconnected)
- [Tekton Pipelines Disconnected](#tekton-pipelines-disconnected)
- [Container Builds Disconnected](#container-builds-disconnected)
- [Disconnected Upgrades (OSUS)](#disconnected-upgrades-osus)
- [Operational Patterns](#operational-patterns)

---

## oc-mirror v2

GA in OCP 4.18. v1 is deprecated in 4.18 and will be removed in a future release.

### ImageSetConfiguration

API version changed from `mirror.openshift.io/v1alpha2` (v1) to
`mirror.openshift.io/v2alpha1` (v2).

```yaml
kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v2alpha1
mirror:
  platform:
    channels:
    - name: stable-4.18
      minVersion: 4.18.0
      maxVersion: 4.18.5
  operators:
  - catalog: registry.redhat.io/redhat/redhat-operator-index:v4.18
    packages:
    - name: elasticsearch-operator
    - name: cluster-logging
  additionalImages:
  - name: registry.redhat.io/ubi9/ubi-minimal:latest
  helm:
    repositories:
    - name: cosigned
      url: https://sigstore.github.io/helm-charts
    charts:
    - name: cosigned
      version: 0.1.23
```

### Three Workflows

```bash
# Mirror-to-disk (connected host -> tar archive)
oc mirror -c ./isc.yaml file:///path/to/destination --v2

# Disk-to-mirror (tar archive -> disconnected registry)
oc mirror -c ./isc.yaml --from file:///path docker://registry:port --v2

# Mirror-to-mirror (direct, partially disconnected)
oc mirror -c ./isc.yaml --workspace file:///path docker://registry:port --v2
```

### IDMS/ITMS (Replaces ICSP)

v2 generates ImageDigestMirrorSet (IDMS) and ImageTagMirrorSet (ITMS) instead
of ImageContentSourcePolicy (ICSP).

Key improvements over ICSP:
- Covers the entire image set (not just incremental deltas)
- `mirrorSourcePolicy` field: `AllowContactingSource` (fallback) or
  `NeverContactSource` (hard block)
- Correct API group (`config.openshift.io` instead of `operator.openshift.io`)
- Proper kubebuilder validation

**Migration**: `oc adm migrate icsp` converts existing ICSP YAML to IDMS. Both
can coexist, but new deployments should use IDMS/ITMS exclusively.

### Generated Resources

oc-mirror v2 generates these in `<workspace>/working-dir/cluster-resources/`:
- IDMS/ITMS manifests
- CatalogSource / ClusterCatalog manifests
- UpdateService manifests
- Signature ConfigMaps (with `--remove-signatures=false`)

### Gotchas

- **CatalogSource naming**: oc-mirror generates names like
  `cs-redhat-operator-index-v4-18` but many operators hardcode looking for
  `redhat-operators`. Rename the CatalogSource or operators won't resolve.
- **Disable default catalogs first**:
  ```bash
  oc patch OperatorHub cluster --type json \
    -p '[{"op": "add", "path": "/spec/disableAllDefaultSources", "value": true}]'
  ```

### Useful Flags

- `--dry-run` -- preview what will be mirrored
- `--parallel-images` / `--parallel-layers` -- concurrent downloads
- `--since` -- incremental mirroring
- `--strict-archive` -- for size-constrained media
- `--remove-signatures=false` -- preserve signatures for verification

---

## Registry Mirroring

### mirror-registry CLI

Installs a minimal single-node Quay instance as mirror target. Requirements:
- RHEL 8/9, Podman 3.4.2+
- ~12 GB for OCP release images alone
- ~358 GB if including Red Hat Operator images

**Not a production registry** -- no HA, local filesystem storage only.

### Certificate Trust

Extract the registry's TLS cert, add to system trust store, and include in
`install-config.yaml` as `additionalTrustBundle`.

### Quay Bridge Operator

For connecting OpenShift ImageStreams to Quay:
- Synchronizes ImageStreams as Quay repositories
- Auto-rewrites builds to output to Quay
- Auto-imports ImageStream tags post-build

---

## OLM in Disconnected Environments

### OLM v1 (OCP 4.18+)

Uses `ClusterCatalog` (apiVersion: `olm.operatorframework.io/v1`):

```yaml
apiVersion: olm.operatorframework.io/v1
kind: ClusterCatalog
metadata:
  name: redhat-operators
spec:
  source:
    type: Image
    image:
      ref: registry.internal:5000/redhat/redhat-operator-index:v4.18
  updateStrategy:
    registryPoll:
      interval: 15m
```

### OLM v0

Uses `CatalogSource`:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: redhat-operators
  namespace: openshift-marketplace
spec:
  sourceType: grpc
  image: registry.internal:5000/redhat/redhat-operator-index:v4.18
```

### Discovering Available Operators

```bash
oc-mirror list operators \
  --catalog=registry.redhat.io/redhat/redhat-operator-index:v4.19

# Extract channel details from catalog image
opm render registry.internal:5000/redhat/redhat-operator-index:v4.18 | \
  jq 'select(.package == "my-operator")'
```

---

## Signature Verification

### ClusterImagePolicy (GA in OCP 4.21)

```yaml
apiVersion: config.openshift.io/v1alpha1
kind: ClusterImagePolicy
metadata:
  name: my-policy
spec:
  scopes:
  - registry.internal:5000/myns/*
  policy:
    rootOfTrust:
      policyType: PublicKey
      publicKey:
        keyData: <base64-encoded-cosign-public-key>
    signedIdentity:
      matchPolicy: RemapIdentity
      remapIdentity:
        prefix: registry.internal:5000/myns
        signedPrefix: registry.redhat.io/myns
```

### Application Order (Critical)

1. Apply IDMS/ITMS manifests (mirror references)
2. Apply signature ConfigMaps (trust data)
3. Apply ClusterImagePolicies (enforcement)
4. Apply CatalogSource / ClusterCatalog manifests

**If you enable verification without mirrored signatures, the CVO stalls.**

### RemapIdentity

Required to map mirrored registry paths back to original source identities.
Without this, signatures won't validate because the image reference doesn't match
what was signed.

### Coverage Gaps

Only the Red Hat Operators catalog currently provides signatures for all operator
images. Certified and Community catalogs may not have complete signature coverage.

---

## Helm Charts in Disconnected Environments

### OCI Registry (Native Support)

```bash
# Login to internal registry
helm registry login registry.internal:5000

# Push chart
helm push mychart-1.0.0.tgz oci://registry.internal:5000/charts

# Pull chart
helm pull oci://registry.internal:5000/charts/mychart --version 1.0.0

# Install from internal registry
helm install myrelease oci://registry.internal:5000/charts/mychart --version 1.0.0

# Digest-based install (immutable)
helm install myrelease oci://registry.internal:5000/charts/mychart@sha256:abc123
```

### Chart Image Relocation

**charts-syncer** and the **Helm Distribution Tooling (dt) plugin** handle
relocating charts AND their referenced container images across air gaps,
rewriting image references to point at the internal registry.

### oc-mirror v2 for Helm

oc-mirror v2 can mirror Helm charts natively (see ImageSetConfiguration above),
but focuses on chart images referenced in values. For arbitrary charts, use
`helm push`/`helm pull` or charts-syncer.

---

## GitOps (ArgoCD) Disconnected

### OCI-Based GitOps (ArgoCD 3.1+ / GitOps 1.18+)

Store manifests in OCI registry -- eliminates need for a separate Git server:

```bash
# Push manifests
oras push registry.internal/myapp-manifests:v1 ./manifests/

# Create ArgoCD repository secret
kubectl create secret generic myapp-repo \
  --from-literal=type=oci \
  --from-literal=url=oci://registry.internal/myapp-manifests \
  -n openshift-gitops
```

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: openshift-gitops
spec:
  source:
    repoURL: oci://registry.internal/myapp-manifests
    targetRevision: v1
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
```

### TLS Trust for ArgoCD

Patch `argocd-tls-certs-cm` ConfigMap in `openshift-gitops` namespace with the
internal registry's TLS certificate.

### Alternative: Internal Git Server

- **Forgejo** (Gitea hard fork): lightweight, runs on OpenShift, built-in Actions
- **GitLab CE**: heavier but more complete DevOps platform

### Key Insight

GitOps principles don't require Git. Any versioned, immutable store (Git, S3, OCI)
satisfies the requirements. OCI is the most natural fit in disconnected OpenShift
because you already have a registry.

---

## Tekton Pipelines Disconnected

### Tekton Bundles (Replace ClusterTasks)

Mirror task bundles to internal registry:

```bash
skopeo copy \
  docker://gcr.io/tekton-releases/catalog/upstream/git-clone:0.9 \
  docker://registry.internal:5000/tekton/git-clone:0.9
```

Reference in pipelines:

```yaml
taskRef:
  resolver: bundles
  params:
  - name: bundle
    value: registry.internal:5000/tekton/git-clone:0.9
  - name: name
    value: git-clone
  - name: kind
    value: task
  - name: secret
    value: registry-credentials
```

### Bundle Caching

- `always` -- cache all resolved resources
- `auto` -- cache only digest-pulled bundles (default)
- `never` -- disable caching

### Builder/Task Images

Mirror ALL images referenced in pipeline tasks. The Samples Operator is set to
`Removed` status in disconnected installs -- manually mirror S2I builder images
and update ImageStreams.

### Tekton Chains Disconnected

Works in disconnected environments:
- Store attestations in local OCI registry
- Use local cosign key material instead of Fulcio/Rekor
- Configure SLSA provenance storage to internal registry

---

## Container Builds Disconnected

### Key Pattern

**Don't build from scratch in the air gap.** Mirror curated, pre-scanned base
images on a defined cadence. Use multi-stage builds where both builder and runtime
stages reference mirrored images.

### Dockerfile Builds

Every `FROM` image must be available in the mirrored registry. Use ImageStreams
to abstract registry URLs:

```yaml
strategy:
  dockerStrategy:
    from:
      kind: ImageStreamTag
      name: 'ubi9:latest'
```

### Shipwright / Builds for OpenShift

All builder strategy images and base images must be pre-mirrored. Supported
strategies (Buildah, S2I, Buildpacks) all work in disconnected mode with proper
image mirroring.

---

## Disconnected Upgrades (OSUS)

### OpenShift Update Service (Cincinnati)

Runs the Cincinnati graph engine locally.

### Deployment Sequence

1. Mirror release images and graph data with oc-mirror
2. Install Cincinnati operator from mirrored catalog
3. Create ConfigMap with key `updateservice-registry` containing registry CA cert
4. Deploy UpdateService CR (generated by oc-mirror as `updateService.yaml`)
5. Apply release signatures (prevents "update cannot be verified" errors)
6. Patch CVO to use local OSUS:
   ```bash
   oc patch clusterversion version \
     -p '{"spec":{"upstream":"https://osus.apps.cluster.example.com/api/upgrades_info/v1/graph"}}' \
     --type merge
   ```

### Verify Upgrade Paths

```bash
curl -k --silent \
  --header 'Accept:application/json' \
  'https://osus.apps.cluster.example.com/api/upgrades_info/v1/graph?arch=amd64&channel=stable-4.18' | \
  jq '.nodes[] | .version'
```

### Gotchas

- **Certificate trust chain**: `updateservice-registry` ConfigMap key is mandatory.
  Missing it causes OSUS trust failures.
- **Apply signatures BEFORE pointing CVO to OSUS.** Without them, the CVO rejects
  the upgrade payload.
- **Ingress CA** must be added to `user-ca-bundle` and referenced in proxy config.
  All nodes reboot after proxy config changes.

---

## Operational Patterns

### Anti-Pattern: Install Connected, Then Disconnect

Image references, operator subscriptions, and CRDs embed external registry URLs
across hundreds of cluster components. Retrofitting is extremely painful.
**Always install as disconnected from the start.**

### Mirror Factory Pattern

A controlled, connected intermediary environment responsible for:
1. Retrieving artifacts from the internet
2. Scanning and validating
3. Preparing for transfer into the air gap

### Six-Step Operational Cadence

1. **Platform release mirroring** -- mirror OCP releases on schedule
2. **Operator catalog management** -- mirror and curate operator catalogs
3. **Container image promotion** -- promote app images through supply chain
4. **CVE remediation imports** -- import security-fix base images promptly
5. **Upgrade validation** -- test upgrades in connected staging first
6. **Registry maintenance** -- prune old images, manage storage
