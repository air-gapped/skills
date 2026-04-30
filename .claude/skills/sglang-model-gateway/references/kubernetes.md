# Kubernetes deployment — sgl-model-gateway

Deep-dive on K8s manifests, RBAC, label selectors, probes, ServiceMonitor, and HA for the gateway. Pairs with the YAML in `assets/`.

## The pattern: one Deployment+RBAC per model

The shape that works in production (and matches the user's `k8s-homelab/`) is **one Deployment + Service + ServiceAccount + Role + RoleBinding + ServiceMonitor + PDB per model**, keyed by a `model_id` label. Reasons:

- Per-model RBAC bounds the gateway's pod-watching to the namespace it cares about.
- Per-model PDB protects the gateway during node drains without affecting other models.
- Per-model HPA (or KEDA) lets you scale the inference fleet for one model without ripple.
- The `model_id` label is the discriminator everywhere — Service selector, gateway `--selector`, ServiceMonitor relabeling, dashboard variables.

The alternative (one big multi-model gateway via `--enable-igw`) is documented in upstream docs but seen rarely in production.

## Service discovery: how it actually works

From `sgl-model-gateway/src/service_discovery.rs`:

```rust
pub struct ServiceDiscoveryConfig {
    pub selector: HashMap<String, String>,         // regular workers
    pub prefill_selector: HashMap<String, String>, // PD mode
    pub decode_selector: HashMap<String, String>,  // PD mode
    pub router_selector: HashMap<String, String>,  // mesh
    pub bootstrap_port_annotation: String,         // sglang.ai/bootstrap-port
    pub router_mesh_port_annotation: String,       // sglang.ai/ha-port
    ...
}
```

The gateway uses `kube` + `k8s-openapi` to **`watch` Pods directly** — *not* Endpoints, *not* Services. It filters Pods by label selector with **AND semantics** across all selector keys (all must match), then probes each Pod's IP at `--service-discovery-port` for metadata via `/server_info` + `/model_info`.

Implications:

- Selecting a Pod via `--selector model_id=foo` works regardless of whether the Pod is in any Service. Endpoints state and Service state are not consulted.
- The probe **must** succeed for the Pod to register as a worker. SGLang workers expose `/server_info`; vLLM workers don't (use `--worker-urls` for vLLM).
- AND semantics: `--selector app=worker --selector model_id=foo` requires *both* labels.

## Required RBAC

Minimum permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sglang-gateway
  namespace: sglang
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

The user's `k8s-homelab` adds `endpoints` and `services` defensively (gateway code may eventually consult them, but as of v0.3.x it does not):

```yaml
rules:
  - apiGroups: [""]
    resources: ["pods", "endpoints", "services"]
    verbs: ["get", "list", "watch"]
```

For **cluster-wide** discovery (gateway in one namespace, workers in others), use `ClusterRole` + `ClusterRoleBinding`. For per-namespace discovery, `Role` + `RoleBinding` + `--service-discovery-namespace <ns>`. The latter is least-privilege.

## CLI flags for K8s

| Flag | Default | Notes |
|---|---|---|
| `--service-discovery` | `false` | Master switch. |
| `--selector key=value` | empty | Repeatable. AND-combined. |
| `--service-discovery-port` | `80` | The port the gateway probes on each Pod IP. **Must match the worker's container port** — set this explicitly to your worker's port (e.g. `30000` for SGLang, `8000` for vLLM). |
| `--service-discovery-namespace` | `default` | Namespace to watch. Single namespace per gateway. |
| `--prefill-selector`, `--decode-selector` | empty | PD mode only. |
| `--router-selector` | empty | Multi-gateway mesh mode. |
| `--bootstrap-port-annotation` | `sglang.ai/bootstrap-port` | Pod annotation read for PD bootstrap port. |
| `--router-mesh-port-annotation` | `sglang.ai/ha-port` | Pod annotation read for mesh port. |

## Multi-port-per-pod limitation

`sgl-project/sglang#20184` (open as of March 2026): service discovery **only watches a single `--service-discovery-port` per gateway**. Operators running B300-style nodes with two decode workers per Pod (e.g. ports 12121 + 12122) cannot register both via the same gateway+selector. Workaround: split into two Pods, one port each, and use a label to discriminate. Or run two gateways with different `--service-discovery-port` values.

## Labels you should put on workers

Convention used in the user's homelab (and the recommended pattern):

```yaml
metadata:
  labels:
    app.kubernetes.io/name: sglang-worker        # or vllm-worker
    app.kubernetes.io/component: inference
    model_id: gemma-3-4b                          # the discriminator
    model-version: 2026-04-25                     # for blue/green
```

Gateway selects on `model_id=gemma-3-4b`. The other labels are for observability and Service routing. **`model_id` value must be stable across replicas** of the same model.

## Probes that work

### HTTP gateway

```yaml
livenessProbe:
  httpGet: {path: /health, port: http}
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
readinessProbe:
  httpGet: {path: /health, port: http}
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
```

Gateway startup is fast (Rust binary, no model loading), so 10-30s initial delays are sufficient.

### gRPC gateway

For gRPC probes, Kubernetes requires **numeric port numbers**, not named ports — this is a `kubelet` API constraint:

```yaml
readinessProbe:
  grpc:
    port: 8080            # numeric, NOT "http"
  initialDelaySeconds: 10
  periodSeconds: 5
```

If you use a named port, kubelet rejects the probe at admission. The user's homelab README captures this gotcha for SGLang gRPC mode.

## Worker probes

vLLM and SGLang both expose `/health`. Critically, vLLM's FastAPI app only binds **after** engine init, so:

- Connection refused → still booting (probe failure is correct).
- `200` OK → ready (live AND ready, single endpoint).
- `503` → engine crashed.

Configure `failureThreshold * periodSeconds > cold-load time`. For 8B models on a single GPU, ~2-5 min cold load. For 70B+ models, 8-12 min. SGLang worker example (homelab):

```yaml
livenessProbe:
  httpGet: {path: /health, port: http}
  initialDelaySeconds: 300         # 5 min — well past first /health-able state
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
readinessProbe:
  httpGet: {path: /health, port: http}
  initialDelaySeconds: 120
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

## ServiceMonitor with relabelings

If using Prometheus Operator, the ServiceMonitor needs to surface `model_id`, `pod`, and `node` so dashboards can group by them. Pattern:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: sglang-gateway
  namespace: sglang
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: sglang-gateway
  endpoints:
    - port: metrics
      interval: 15s
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_label_model_id]
          targetLabel: model_id
        - sourceLabels: [__meta_kubernetes_pod_name]
          targetLabel: pod
        - sourceLabels: [__meta_kubernetes_pod_node_name]
          targetLabel: node
```

Apply the same relabeling to the worker ServiceMonitor so vLLM-side `vllm:*` metrics and gateway-side `smg_*` metrics carry the same `model_id` for joined queries.

## Service shape

Two flavors:

```yaml
# 1. Standard ClusterIP — clients hit one IP, Service load-balances among gateway replicas
apiVersion: v1
kind: Service
metadata:
  name: gateway
spec:
  type: ClusterIP
  ports:
    - {name: http,    port: 8080, targetPort: http}
    - {name: metrics, port: 29000, targetPort: metrics}
  selector: {app.kubernetes.io/name: sglang-gateway, model_id: gemma-3-4b}

# 2. Headless — only useful if a sidecar wants to enumerate Pod IPs directly;
# rare for the gateway itself.
spec:
  type: ClusterIP
  clusterIP: None
```

ClusterIP for the gateway. Headless is for the *worker* Service when the gateway uses Pod-IP-direct addressing (which it does via service discovery).

## HA: multiple gateway replicas

Each gateway replica owns an independent radix tree (cache-aware policy). Running 2+ replicas behind a Service:

- HTTP traffic round-robins among gateway replicas (default Service behaviour).
- Each gateway sees only its own request stream → its radix tree reflects its own routing decisions.
- Two same-prefix requests landing on different gateways may pick different workers → cache miss.
- Documented penalty: **10-20% cache hit reduction**.

To mitigate:
- **Session affinity** at the Service level (`sessionAffinity: ClientIP`) — clients pin to a gateway, so the same prefix lands on the same gateway → same routing decision.
- Or run **a single gateway replica with PodDisruptionBudget + fast restarts** — accept brief unavailability during restarts.

```yaml
apiVersion: v1
kind: Service
spec:
  type: ClusterIP
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800   # 3 hours
```

This is fine for chat workloads where one user hits one gateway repeatedly. For uniform-load batch traffic, ClientIP affinity creates hot spots — disable it.

## PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: gateway
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: sglang-gateway
      model_id: gemma-3-4b
```

For a 1-replica gateway, set `minAvailable: 0` and accept brief unavailability during node drains. For 2+, `maxUnavailable: 1` keeps at least one available.

## Resource requests/limits

The gateway is light — a few hundred MB of RAM, low CPU. Real numbers from the homelab:

```yaml
resources:
  requests: {memory: "768Mi", cpu: "100m"}
  limits:   {memory: "1Gi",   cpu: "500m"}
```

For high-throughput deployments (>5k req/s), bump to 2 vCPUs and 4 GiB. The gateway is mostly waiting on workers, so CPU saturation is rare except during heavy tokenization.

## Image and tag selection

```yaml
image: lmsysorg/sgl-model-gateway:v0.3.1   # pin a specific gateway tag
```

Don't use `:latest`. The image is the canonical artifact for the renamed crate; it tracks `gateway-vX.Y.Z` release tags.

## Network policy

If your cluster runs NetworkPolicy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gateway-allow
spec:
  podSelector:
    matchLabels: {app.kubernetes.io/name: sglang-gateway}
  policyTypes: [Ingress, Egress]
  ingress:
    - {from: [{namespaceSelector: {matchLabels: {ingress: allowed}}}], ports: [{port: 8080}]}
    - {from: [{namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: monitoring}}}], ports: [{port: 29000}]}
  egress:
    - {to: [{podSelector: {matchLabels: {app.kubernetes.io/name: sglang-worker}}}]}  # to workers
    - {ports: [{port: 53, protocol: UDP}, {port: 53, protocol: TCP}]}                 # DNS
    - {to: [{namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: kube-system}}}], ports: [{port: 6443}]}  # kube-apiserver for service discovery
```

The kube-apiserver egress is essential — service discovery does `watch Pods` against the API server.

## What the upstream repo does NOT ship

- **No Helm chart** for the gateway.
- **No Kustomize base** for the gateway (only worker-only `docker/k8s-sglang-distributed-sts.yaml` and `docker/k8s-sglang-service.yaml` for distributed inference).
- **No example ServingRuntime / KServe / Inference Gateway integration**.

The user's `k8s-homelab/` is the closest production-shaped reference visible. Treat upstream as having a manifest gap and roll your own (or use the assets in this skill).
