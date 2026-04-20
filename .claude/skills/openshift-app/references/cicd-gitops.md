# CI/CD and GitOps Reference

## Table of Contents
- [OpenShift Pipelines (Tekton)](#openshift-pipelines-tekton)
- [Tekton Chains](#tekton-chains)
- [Pipelines-as-Code](#pipelines-as-code)
- [OpenShift GitOps (ArgoCD)](#openshift-gitops-argocd)
- [Shipwright (Builds for OpenShift)](#shipwright-builds-for-openshift)
- [Image Promotion Strategies](#image-promotion-strategies)
- [GitOps Directory Structure](#gitops-directory-structure)
- [BuildConfig (Legacy)](#buildconfig-legacy)

---

## OpenShift Pipelines (Tekton)

### Current Versions

| OCP Version | Pipelines Version | Key Features |
|-------------|------------------|--------------|
| 4.21 | 1.21 | Event-driven pruner GA, Tekton cache GA, per-TaskRun timeout overrides |
| 4.20 | 1.20 | readOnlyRootFilesystem default, `chain` command deprecated |
| 4.18 | 1.17 | Community ClusterTasks removed, use Tekton Resolvers |

### ClusterTasks Removed (Pipelines 1.17)

Community ClusterTasks are no longer shipped. Use Tekton Resolvers instead:

```yaml
taskRef:
  resolver: bundles
  params:
  - name: bundle
    value: gcr.io/tekton-releases/catalog/upstream/git-clone:0.9
  - name: name
    value: git-clone
  - name: kind
    value: task
```

For disconnected environments, mirror bundles to internal registry. See
`references/disconnected.md`.

### Tekton Hub Deprecated (January 2026)

ArtifactHub (CNCF) is the recommended replacement, but is "not fully supported"
with OpenShift Pipelines -- only configuration is supported.

---

## Tekton Chains

Installed by default with OpenShift Pipelines Operator. Automatically:
1. Watches completed TaskRun/PipelineRun
2. Snapshots the results
3. Generates SLSA provenance attestation
4. Signs with cosign keys
5. Stores in configured backend (OCI registry)

### Configuration

Via `chains-config` ConfigMap in `tekton-chains` namespace:
- `artifacts.taskrun.format`: `slsa/v1` (SLSA v0.2) or `slsa/v2alpha4` (SLSA v1.0)
- `artifacts.pipelinerun.format`: same options
- `artifacts.pipelinerun.enable-deep-inspection`: inspect child TaskRuns

### Task Result Naming (Critical)

Tasks must expose results matching these patterns:
- `*IMAGE_URL` / `*IMAGE_DIGEST` -- output image references
- `IMAGES` -- comma/newline-separated entries (alternative)
- `CHAINS-GIT_URL` / `CHAINS-GIT_COMMIT` -- input provenance

### Signing Setup

```bash
cosign generate-key-pair k8s://openshift-pipelines/signing-secrets
```

### Pipelines 1.21 Changes

- Can disable image signing while keeping provenance/attestation signing
- Anti-affinity rules on chains-controller for HA
- Chains StatefulSet ordinals for HA (Tech Preview since 1.19)

---

## Pipelines-as-Code

Joined the Tekton org on March 19, 2026. Stores PipelineRun definitions in
`.tekton/` directory alongside source code.

### Supported Providers

GitHub (App/Webhook), GitLab, Bitbucket Cloud/Data Center, Forgejo.

### Key Features

- **concurrency_limit** in Repository CRD -- controls parallel runs
- **max-keep-runs** annotation -- cleanup old runs
- Auto-cancel superseded runs
- ChatOps: `/test`, `/retest`, `/cancel`
- **pipelinerun_provenance**: fetch pipeline definition from default branch only
  (security feature -- prevents PR authors from modifying the pipeline itself)

---

## OpenShift GitOps (ArgoCD)

### Current Versions

| GitOps Version | ArgoCD Version | Key Features |
|----------------|---------------|--------------|
| 1.20 (Mar 2026) | 3.3 | Agent destination routing GA, NetworkPolicy auto-create, PreDelete hooks |
| 1.19 | 3.1 | Argo CD Agent GA, Image Updater TP, OCI source support |
| 1.18 | 3.1 | OCI registry as application source |
| 1.15 | -- | Multi-source GA, Rollouts HA, traffic management plugins |

### Argo CD Agent (Multi-Cluster)

GA since GitOps 1.19. Pull-based model -- agent initiates all communication.

Architecture: principal (control plane) + agent (managed clusters).
- **Managed mode**: central plane pushes applications
- **Autonomous mode**: workload cluster is source of truth, central plane observes
- Mutual TLS for security
- No firewall changes needed (agent pulls)

### Argo Rollouts

Supported via RolloutManager CRD since GitOps 1.9+. HA support (`.spec.ha`)
and traffic management plugins in 1.15. Console Plugin in 1.20.

### ApplicationSet Generators

Git (directory/file), Cluster, Pull Request (with `titleMatch` filter), Cluster
Decision Resource, List, Matrix, Merge, Plugin.

### Key Recommendations

- Separate repos for source code vs manifests
- Deploy versioned manifests (not HEAD)
- Use annotation tracking (not label tracking -- 63 char limit)
- Never use default AppProject
- Separate ArgoCD instances for cluster-config vs app-deployment

### OCI-Based GitOps (ArgoCD 3.1+)

Store manifests in OCI registry -- eliminates need for separate Git server:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: oci://registry.internal/myapp
    targetRevision: v1
    path: .
```

Push manifests: `oras push registry.internal/myapp:v1 .`

---

## Shipwright (Builds for OpenShift)

### Current Versions

| Builds Version | OCP Version | Key Feature |
|---------------|-------------|-------------|
| 1.7 | 4.21 | BuildConfig-to-Shipwright migration guide |
| 1.6 | 4.20 | Cloud Native Buildpacks GA |
| 1.0 | 4.14 | Initial GA (April 2024) |

### Supported Build Strategies

- **Buildah** (GA) -- Dockerfile-based builds
- **S2I** (GA) -- Source-to-Image within Shipwright framework
- **Cloud Native Buildpacks** (GA since 1.6)
- Community strategies: Kaniko, ko, BuildKit

### Migration from BuildConfig

**Crane** migration tool (Developer Preview, January 2026):
- Converts Docker strategy BuildConfigs to Buildah ClusterBuildStrategy
- Converts Source strategy to S2I ClusterBuildStrategy
- Not yet production-supported

### Build Object Example

```yaml
apiVersion: shipwright.io/v1beta1
kind: Build
metadata:
  name: myapp-build
spec:
  source:
    type: Git
    git:
      url: https://github.com/org/myapp
    contextDir: .
  strategy:
    name: buildah
    kind: ClusterBuildStrategy
  output:
    image: image-registry.openshift-image-registry.svc:5000/myns/myapp:latest
```

### Multi-Arch Builds (OCP 4.17+)

The `multiarch-native-buildah` ClusterBuildStrategy dispatches build jobs to nodes
of each target architecture, then consolidates into a manifest list.

---

## Image Promotion Strategies

### Tag-Based Promotion

```bash
oc tag app-dev/myapp:latest app-staging/myapp:latest
oc tag app-staging/myapp:latest app-prod/myapp:latest
```

### Quay Bridge Operator

Synchronizes OpenShift ImageStreams as Quay repositories, auto-rewrites builds
to output to Quay, auto-imports ImageStream tags post-build.

### Container Security Operator

Bridges Quay/Clair vulnerability metadata into OpenShift. Pipeline can gate on
scan results (fail on high/critical CVEs).

### Argo CD Image Updater

Tech Preview in GitOps 1.19. Automated container image updates in GitOps repos.

---

## GitOps Directory Structure

### Recommended Layout (Polyrepo)

Separate repos for platform config, app config, and app source:

```
# App manifests repo
bootstrap/
  base/
  overlays/default/
cluster-config/         # cluster-level config (identity, scanning)
components/
  applicationsets/
  applications/
  argocdproj/
apps/
  myapp/
    base/
      deployment.yaml
      service.yaml
      kustomization.yaml
    overlays/
      dev/
        kustomization.yaml
      staging/
        kustomization.yaml
      prod/
        kustomization.yaml
```

### Key Principles

- **DRY**: use Kustomize overlays for env deltas, not full manifest copies
- **Branches for features, NOT for environments** (anti-pattern)
- **Kustomize + Helm combo**: Kustomize for overlay-based env management, Helm for
  runtime parameterization

### Three Patterns for Helm + ArgoCD

1. ArgoCD Application pointing at Helm repo (simplest)
2. ArgoCD Application pointing at chart in Git (version-controlled)
3. ArgoCD Application pointing at Kustomize folder that renders Helm chart (most flexible)

### Community Template

`github.com/redhat-cop/gitops-standards-repo-template` provides standard structure
for multi-cluster day-2 configuration.

---

## BuildConfig (Legacy)

Not formally deprecated yet, but Shipwright is the strategic direction. Migration
tooling (Crane) available as Developer Preview.

### When BuildConfig Still Makes Sense

- Existing CI/CD workflows deeply integrated with BuildConfig triggers
- Teams not yet ready to adopt Tekton/Shipwright
- Simple S2I builds where the overhead of Shipwright is not justified

### Migration Path

1. Evaluate Crane migration tool for automated conversion
2. Alternatively, rewrite as Shipwright Build objects manually
3. For complex pipelines, consider Tekton Pipelines instead

### Trusted Artifacts Pattern

From Konflux CI: pass files between Tekton Tasks via OCI registry (ORAS) with
digest tracking to prevent tampering. Replaces PVC-based workspace sharing where
tampering is undetectable. Tasks produce `ARTIFACTS` array result; downstream
tasks reference by digest.
