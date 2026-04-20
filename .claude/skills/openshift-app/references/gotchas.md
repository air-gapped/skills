# Gotchas and Migration Reference

## Table of Contents
- [Version Timeline (OCP 4.14-4.21)](#version-timeline-ocp-414-421)
- [DeploymentConfig Migration](#deploymentconfig-migration)
- [OpenShift SDN to OVN-Kubernetes](#openshift-sdn-to-ovn-kubernetes)
- [restricted to restricted-v2 SCC](#restricted-to-restricted-v2-scc)
- [Logging Stack Migration](#logging-stack-migration)
- [Common "Works on K8s, Fails on OpenShift" Scenarios](#common-works-on-k8s-fails-on-openshift-scenarios)
- [API Deprecations and Removals](#api-deprecations-and-removals)

---

## Version Timeline (OCP 4.14-4.21)

| Version | K8s | Key Breaking Changes / Features |
|---------|-----|--------------------------------|
| **4.14** | 1.27 | cgroup v2 default on fresh installs. OpenShift SDN deprecated. DeploymentConfig deprecated. |
| **4.15** | 1.28 | OVN-Kubernetes required for new installs (SDN still works on upgrades). Builds for OpenShift 1.0 GA. |
| **4.16** | 1.29 | cgroup v1 deprecated. IPTables API deprecated (warning events). SHA-1 certs disabled in ingress. FlowSchema v1beta2 removed. Operator SDK CLI deprecated. OLM v1 Tech Preview. Cluster Samples Operator deprecated. |
| **4.17** | 1.30 | **OpenShift SDN fully removed.** No K8s API removals. |
| **4.18** | 1.31 | **OLM v1 GA.** oc-mirror v2 GA. Builds 1.6 (Buildpacks GA). UDN GA. ESO GA (4.20 operator). |
| **4.19** | 1.32 | **cgroup v1 removed.** RHCOS built as layered image. Image mode for OpenShift GA. Gateway API CRDs ship by default. |
| **4.20** | 1.33 | Pipelines 1.20. GitOps 1.18. In-place VPA beta (k8s 1.33). |
| **4.21** | 1.34 | **ClusterImagePolicy GA** (sigstore verification enforced by default for OCP releases). Pipelines 1.21. GitOps 1.20 (ArgoCD 3.3). RHTAS 1.3. RHADS-SSC 1.8. |

---

## DeploymentConfig Migration

Deprecated since OCP 4.14. Only security/critical fixes. No removal date set.

### Features Without Direct Deployment Equivalent

| DeploymentConfig Feature | Replacement |
|-------------------------|-------------|
| Automatic rollbacks | Argo Rollouts (GitOps 1.9+) or Helm rollbacks |
| ImageStream change triggers | `image.openshift.io/triggers` annotation on Deployment |
| Lifecycle hooks (pre/post) | Resource Hooks in GitOps or Helm Chart Hooks |
| Custom deployment strategies | Deployments have rolling and recreate only; use Argo Rollouts for canary/blue-green |

### ImageStream Triggers on Deployments

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    image.openshift.io/triggers: >-
      [{"from":{"kind":"ImageStreamTag","name":"myapp:latest"},
        "fieldPath":"spec.template.spec.containers[?(@.name==\"myapp\")].image"}]
spec:
  template:
    spec:
      containers:
      - name: myapp
        image: myapp:latest  # Resolved by trigger
```

**Critical**: the ImageStream must have `lookupPolicy.local: true`:
```bash
oc set image-lookup myapp
```
Without this, OpenShift tries to pull from external registries instead of resolving
locally, causing ErrImagePull errors.

---

## OpenShift SDN to OVN-Kubernetes

SDN removed in OCP 4.17. Migration must happen before upgrading past 4.16.

### Breaking Changes

- **IP range conflicts**: OVN reserves `100.64.0.0/16` and `100.88.0.0/16`. Patch
  before migration if these conflict with existing networks.
- **MTU decrease**: 50 bytes smaller due to OVN overlay overhead. Requires interface
  reconfiguration.
- **Two node reboots**: approximately doubles upgrade time.
- **Egress changes**: `EgressNetworkPolicy` auto-converts to `EgressFirewall`.
  HTTP proxy and DNS proxy egress router modes are NOT supported in OVN -- only
  redirect mode works.
- **NetworkPolicy enforcement**: SDN didn't support egress or IPBlock in NetworkPolicy.
  OVN does. Existing policies that couldn't be enforced before now CAN be -- audit
  for unintended enforcement.

### Migration Steps

1. Verify no IP range conflicts with OVN reserved ranges
2. Plan for MTU adjustment
3. Audit egress router pods (convert to redirect mode)
4. Audit NetworkPolicies for egress rules that were previously unenforced
5. Perform migration (requires admin acknowledgment)
6. Verify two-reboot completion

---

## restricted to restricted-v2 SCC

### What Changed

| Aspect | restricted v1 | restricted-v2 |
|--------|--------------|---------------|
| Capabilities | Drop KILL, MKNOD, SETUID, SETGID | Drop ALL |
| allowPrivilegeEscalation | Allowed (true) | false (enforced) |
| seccompProfile | Unset/Unconfined OK | RuntimeDefault required |

### Impact

Workloads that:
- Set `allowPrivilegeEscalation: true` will be rejected
- Require capabilities beyond `NET_BIND_SERVICE` will be rejected
- Don't set seccompProfile will be rejected (if they also don't match the namespace range)

### Divergence Between Fresh Install and Upgrade

- **New clusters (4.11+)**: only `restricted-v2` granted to authenticated users
- **Upgraded clusters**: both `restricted` and `restricted-v2` available
- This means the same manifest may work on an upgraded cluster but fail on a fresh one

---

## Logging Stack Migration

### Logging 6.0 (EFK Completely Removed)

- **Elasticsearch**: removed -- use LokiStack (via Loki Operator)
- **Fluentd**: removed -- use Vector
- **Kibana/Curator**: removed -- use OpenShift console UI plugin
- **Logging 5.9 EOL**: November 2025

### Migration Steps

1. Deploy Loki Operator and create LokiStack
2. Deploy Vector collector alongside existing Fluentd
3. Configure ClusterLogForwarder (observability.openshift.io API group)
4. Run both stacks during log retention window
5. Verify log completeness in LokiStack
6. Remove Elasticsearch/Fluentd deployments

**NOT an in-place upgrade** -- parallel deployment required.

---

## Common "Works on K8s, Fails on OpenShift" Scenarios

### 1. Container Runs as Root

**Symptom**: CrashLoopBackOff, permission denied in logs.
**Cause**: Dockerfile has `USER root` or no USER directive; OpenShift assigns random UID.
**Fix**: `chgrp -R 0 && chmod -R g=u`, set `USER 1001`, leave `runAsUser` empty.

### 2. Privileged Port Binding

**Symptom**: Permission denied binding to port 80/443.
**Cause**: Ports < 1024 require capabilities not available under restricted-v2.
**Fix**: Configure app to listen on 8080/8443. Remap via Service/Route.

### 3. Init Container chown

**Symptom**: Init container fails to fix permissions on volume.
**Cause**: Init containers run as same arbitrary UID under restricted SCC.
**Fix**: Fix permissions in Dockerfile, or use `fsGroup` in pod securityContext.

### 4. Nginx/Apache Default Config

**Symptom**: Crash on startup trying to bind port 80 or write to /var/cache/nginx.
**Fix**: Use unprivileged config (listen 8080), make cache dirs group-writable.

### 5. Hardcoded UID/GID

**Symptom**: `mkdir: cannot create directory: Permission denied`.
**Cause**: App assumes it runs as specific user (e.g., UID 1000).
**Fix**: Remove hardcoded UIDs; use `chgrp -R 0 && chmod -R g=u` pattern.

### 6. Community Helm Chart Defaults

**Symptom**: Chart install fails with SCC errors.
**Fix**: Override with `--set securityContext.runAsUser=null --set securityContext.fsGroup=null`.

### 7. Ingress Annotations Silently Ignored

**Symptom**: Features like rate limiting, proxy timeouts don't work.
**Cause**: nginx/traefik-specific annotations are ignored by OpenShift Router.
**Fix**: Use `haproxy.router.openshift.io/*` annotations or native Route objects.

### 8. Volume Mount Owned by root:root

**Symptom**: App can't write to PVC mount.
**Fix**: Use `fsGroup` in securityContext, or design app to create subdirectories.

### 9. /etc/passwd Lookup Fails

**Symptom**: App crashes with "no such user" for the container UID.
**Fix**: Make `/etc/passwd` group-writable + entrypoint script to append entry.

### 10. Helm chart cannot look up namespace UID range

**Symptom**: Hardcoded UIDs in chart don't match namespace allocation.
**Cause**: `openshift.io/sa.scc.uid-range` annotation can't be read during `helm template`.
**Fix**: Don't hardcode UIDs; use `null` and let OpenShift assign.

---

## API Deprecations and Removals

### OCP 4.16 (K8s 1.29)

- `flowcontrol.apiserver.k8s.io/v1beta2` removed for FlowSchema and
  PriorityLevelConfiguration. Migrate to `v1`.
- Upgrade from 4.15 to 4.16 requires manual administrator acknowledgment.

### OCP 4.17-4.18

No Kubernetes API removals.

### OCP 4.19

OCP 4.19 has API removals (specific list not yet enumerated in public docs at
time of research). Check Red Hat article 6955985 before upgrading.

### Service Serving Certificates

The service CA certificate is valid for 26 months and auto-rotates at 13 months
remaining. If you don't upgrade your cluster during the grace period, manual
certificate refresh may be needed.
