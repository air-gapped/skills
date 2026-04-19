# OpenShift — the things upstream k8s users don't have to think about

OCP has its own flavor of k8s with stricter security defaults, a different ingress path, a different monitoring stack, and a different installation path for the GPU driver. This reference covers the delta from a clean k8s deploy.

For OpenShift-only teams: also read `references/pod-shape.md`, `references/multi-node.md`, and `references/autoscaling.md` — everything there still applies; this doc is the diff.

## The three things that bite OCP operators first

1. **Arbitrary UID**: the upstream `vllm/vllm-openai` image runs as root. OCP assigns random UIDs per namespace. Root-user image → pod refuses to start under `restricted-v2`.
2. **Route 60-second timeout**: default HAProxy Route cuts streaming responses at 60 s.
3. **`/dev/shm` still 64 MiB**: same as vanilla k8s; use `emptyDir: {medium: Memory}` at `/dev/shm`. See `references/pod-shape.md`.

## RHAIIS — Red Hat AI Inference Server

**RHAIIS is upstream vLLM + Red Hat build, lifecycle, and support — not a fork.** The image is UID-agnostic and runs clean under `restricted-v2`.

- **Product page**: https://www.redhat.com/en/products/ai/inference-server
- **Docs root (3.3)**: https://docs.redhat.com/en/documentation/red_hat_ai_inference_server/3.3
- **Images**: `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.3.0` (+ `-rocm-rhel9`, `-gaudi-rhel9`)
- **vLLM CLI reference**: https://docs.redhat.com/en/documentation/red_hat_ai_inference_server/3.3/html-single/vllm_server_arguments/index
- **Hardware compat matrix**: https://docs.redhat.com/en/documentation/red_hat_ai/3/html-single/supported_product_and_hardware_configurations/index
- **TGIS adapter** (for KServe/TGIS-API compat): https://github.com/opendatahub-io/vllm-tgis-adapter

### RHAIIS ↔ upstream version mapping

| RHAIIS | Upstream vLLM |
|---|---|
| 3.3.0 | v0.13.0 |
| 3.2.3 | v0.12.x (see release notes) |

Pin the exact RHAIIS tag; roll forward with release notes.

## RHOAI — Red Hat OpenShift AI model serving

- **Docs**: https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.23/html/serving_models/
- **Backend**: KServe single-model (KServe Raw Deployments). ModelMesh path is retired for LLM workloads.
- **Bundled ServingRuntime templates**: `vLLM ServingRuntime for KServe` (NVIDIA), `vLLM ROCm`, `vLLM with Gaudi`.
- **Upstream ServingRuntime templates**: https://github.com/opendatahub-io/odh-model-controller
- **Hands-on lab**: https://redhat-ai-services.github.io/etx-llm-optimization-and-inference-leveraging/modules/module-1.3-deploy-rhoai.html

## SCC (Security Context Constraints)

Default OCP policy is `restricted-v2`:

| Image | SCC needed |
|---|---|
| RHAIIS | `restricted-v2` — works out of the box |
| Upstream `vllm/vllm-openai` | `anyuid` (not ideal), or rebuild for non-root |
| Custom vLLM image | Build for arbitrary UID (`chgrp -R 0 /root /tmp && chmod -R g=u /root /tmp`) → `restricted-v2` |

**Do NOT grant `privileged`.** GPU access is via NVIDIA device plugin (resource request), not host device mount. PSA guidance: https://connect.redhat.com/en/blog/important-openshift-changes-pod-security-standards

## The arbitrary-UID rebuild recipe

For custom / upstream `vllm/vllm-openai`:

```dockerfile
FROM vllm/vllm-openai:<pinned-tag>

# Make writable paths UID-agnostic (OCP random UID always has GID 0)
RUN chgrp -R 0 /root /tmp /data 2>/dev/null || true && \
    chmod -R g=u /root /tmp /data 2>/dev/null || true

# Honor $HOME from OCP (random UID has no passwd entry)
ENV HOME=/tmp
ENV HF_HOME=/tmp/.cache/huggingface
```

Known upstream issues:
- https://github.com/vllm-project/vllm/issues/31959 — can't run as non-root
- https://github.com/vllm-project/vllm/issues/15359 — v0.8.1 regression on non-root rebase

OCP guide: https://cookbook.openshift.org/users-and-role-based-access-control/how-can-i-enable-an-image-to-run-as-a-set-user-id.html

## Routes, Gateway API, and service mesh

### Route (default)

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: vllm
  annotations:
    haproxy.router.openshift.io/timeout: 10m          # LOAD-BEARING — streaming
    haproxy.router.openshift.io/timeout-tunnel: 10m
    router.openshift.io/haproxy.health.check.interval: 5s
spec:
  to: {kind: Service, name: vllm}
  port: {targetPort: http}
  tls: {termination: edge}
```

Without the `timeout: 10m` annotation, SSE streaming cuts off at 60 s. This is the single most common OCP-specific failure.

### Gateway API on OCP

| OCP version | Status |
|---|---|
| 4.17 | Dev-preview |
| 4.19+ | **GA** via Ingress Operator |

- Enhancement: https://github.com/openshift/enhancements/blob/master/enhancements/ingress/gateway-api-with-cluster-ingress-operator.md
- OKD docs: https://docs.okd.io/4.20/networking/ingress_load_balancing/configuring_ingress_cluster_traffic/ingress-gateway-api.html

On 4.19+, Gateway API + GAIE is viable. **OSSM v2 (Service Mesh) conflicts with Gateway API — pick one.** OSSM 3.x (Istio ambient) resolves the conflict: https://developers.redhat.com/articles/2025/12/09/integrate-openshift-gateway-api-openshift-service-mesh

## Monitoring

OCP has a built-in Prometheus stack. User-workload monitoring must be enabled separately:

1. **Enable**: https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html/monitoring/enabling-monitoring-for-user-defined-projects
2. Create `PodMonitor` or `ServiceMonitor` in the workload namespace — prom-operator in `openshift-user-workload-monitoring` auto-scrapes.
3. **Label rewrite**: `enforcedNamespaceLabel` rewrites any `namespace` label the pod emits to `exported_namespace`. Don't rely on vLLM's own `namespace` label; use the k8s one.
4. Opt-out a pod with `openshift.io/user-monitoring: "false"`.

Pair with DCGM-exporter (NVIDIA GPU Operator installs it) for hardware-side metrics. See `vllm-observability` skill.

## NVIDIA GPU Operator on OCP

Canonical install: https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/

Order:

1. **Node Feature Discovery (NFD) operator first** — labels nodes with PCI `10de` (NVIDIA).
2. **GPU Operator via OperatorHub** — installs driver, container runtime, device plugin, DCGM exporter, MIG manager.
3. Create a `ClusterPolicy` CR (defaults are usually fine).

Gotcha: GPU Operator's driver DaemonSet conflicts with preinstalled host drivers. **Uninstall host drivers before installing the operator.**

## Disconnected / air-gapped OCP

- **oc-mirror v2** for images + operators: https://docs.redhat.com/en/documentation/openshift_container_platform/4.21/html/disconnected_environments/about-installing-oc-mirror-v2
- **Registry redirection**: ImageDigestMirrorSet (IDMS). ICSP is deprecated.
- **Model weights** three patterns:
  1. PVC + copy pod
  2. **ModelCar** (recommended) — model as OCI image: https://redhat-ai-services.github.io/vllm-showroom/modules/deployment/modelcar/01c-deploy-modelcar.html
  3. ODF / S3 bucket via KServe `storageUri`
- **Worked example**: https://developers.redhat.com/articles/2025/09/15/benchmarking-guidellm-air-gapped-openshift-clusters
- **Overview**: https://developers.redhat.com/articles/2026/03/19/how-operate-openshift-air-gapped-environments

In air-gapped, combine with `HF_HUB_OFFLINE=1`, `HF_ENDPOINT=<internal-mirror>`, `TRANSFORMERS_OFFLINE=1`, `VLLM_NO_USAGE_STATS=1`. See `vllm-configuration` skill.

## OCP-specific pitfalls checklist

1. Upstream image runs as root → SCC failure. Use RHAIIS or rebuild.
2. Route 60 s timeout → SSE dies mid-stream. Annotate.
3. `/dev/shm` 64 MiB default — still needs `emptyDir: {medium: Memory}` same as vanilla k8s.
4. OSSM v2 + Gateway API conflict → pick one, or upgrade to OSSM 3.x.
5. GPU Operator driver DS vs host-installed driver → uninstall host drivers.
6. OCP CoreDNS doesn't resolve `*.cluster.local` exactly like vanilla k8s in some CNI combos — use the full FQDN `.<svc>.<ns>.svc.cluster.local` for multi-node NCCL bootstrap.
7. User-workload monitoring **opt-in** — vLLM `/metrics` won't scrape until enabled in the cluster-monitoring-config.
8. `enforcedNamespaceLabel` rewrites namespace labels — dashboards that filter by `namespace` need `exported_namespace` in OCP.

## Full OCP blog trail (for deeper detail)

- **RHAIIS deep dive**: https://www.redhat.com/en/blog/red-hat-ai-inference-server-technical-deep-dive
- **Lightweight model + RHAIIS**: https://developers.redhat.com/articles/2025/09/12/deploy-lightweight-ai-model-ai-inference-server-containerization
- **Deploy models on RHOAI**: https://developers.redhat.com/articles/2025/09/10/how-deploy-language-models-red-hat-openshift-ai
- **Prod deploy guide**: https://developers.redhat.com/articles/2025/10/06/optimize-and-deploy-llms-production-openshift-ai
- **Bench on k8s**: https://developers.redhat.com/articles/2025/12/24/how-deploy-and-benchmark-vllm-guidellm-kubernetes
- **Prithvi on OCP**: https://developers.redhat.com/articles/2026/03/03/serve-and-benchmark-prithvi-models-vllm-openshift
- **ModelCar pattern**: https://developers.redhat.com/articles/2025/01/30/build-and-deploy-modelcar-container-openshift-ai
- **Wide-EP on OCP + llm-d**: https://developers.redhat.com/articles/2025/09/08/scaling-deepseek-style-moes-vllm-and-llm-d-using-wide-ep
- **KServe + KEDA**: https://developers.redhat.com/articles/2025/09/23/how-set-kserve-autoscaling-vllm-keda
- **SLI autoscaling**: https://developers.redhat.com/articles/2025/11/26/autoscaling-vllm-openshift-ai-model-serving
- **Air-gapped benchmarks**: https://developers.redhat.com/articles/2025/09/15/benchmarking-guidellm-air-gapped-openshift-clusters
