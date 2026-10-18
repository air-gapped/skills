# Routing — gateway & LB in front of vLLM fleets

How requests reach the right vLLM pod. Three architectural layers:

1. **Ingress / Route / Gateway** — L7 entry point (TLS, authn).
2. **Inference-aware routing** — prefix-aware, KV-aware, semantic.
3. **Endpoint Picker (EPP)** — picks a specific pod from a pool.

Each layer has multiple implementations. This reference is a pointer map.

## Table of Contents

- [The K8s-standard surface: Gateway API Inference Extension (GAIE)](#the-k8s-standard-surface-gateway-api-inference-extension-gaie)
- [Non-GAIE options (still viable)](#non-gaie-options-still-viable)
- [OpenShift Route (the 60-second gotcha)](#openshift-route-the-60-second-gotcha)
- [Gateway API on OpenShift (version gate)](#gateway-api-on-openshift-version-gate)
- [Istio sidecar caveat for streaming](#istio-sidecar-caveat-for-streaming)
- [Prefix-aware vs KV-aware vs semantic routing](#prefix-aware-vs-kv-aware-vs-semantic-routing)
- [Load balancing across replicas — health & draining](#load-balancing-across-replicas--health--draining)
- [Autoscaler coordination](#autoscaler-coordination)
- [Smoke test — is routing working?](#smoke-test--is-routing-working)
- [Next](#next)

---

## The K8s-standard surface: Gateway API Inference Extension (GAIE)

**GAIE is the SIG-Network standard for LLM routing on K8s.** v1 went GA in September 2025. For new builds, start here.

- **Site**: https://gateway-api-inference-extension.sigs.k8s.io/
- **Repo**: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- **Launch blog**: https://kubernetes.io/blog/2025/06/05/introducing-gateway-api-inference-extension/
- **Spec reference**: https://gateway-api-inference-extension.sigs.k8s.io/reference/spec/

### CRDs (v1.6.x)

| CRD | Group | What it expresses |
|---|---|---|
| `InferencePool` | `inference.networking.k8s.io/v1` | "These pods form a pool"; `spec.endpointPickerRef` (optional from v1.6.0) names the EPP |
| `InferencePoolImport` | `inference.networking.x-k8s.io` (alpha) | Pool exported across clusters |

`InferenceModel` no longer exists — v1.0 replaced it with the alpha `InferenceObjective`, and
v1.6.0 removed `InferenceObjective`, `InferenceModelRewrite` and `EndpointPickerConfig` from
GAIE (moved to llm-d). Delete those objects from manifests targeting GAIE ≥ v1.6. The
full-featured EPP also moved to llm-d; GAIE ships only the conformance `lwepp`.

The **Endpoint Picker (EPP)** is the ext_proc gRPC server that the gateway consults for each request: given a pool, pick the specific endpoint. EPP implementations embed the routing logic — prefix-aware, KV-aware, session-sticky, load-aware.

### GAIE-compatible gateways

| Gateway | URL | Notes |
|---|---|---|
| **llm-d** (bundled) | https://llm-d.ai/ | Ships its own EPP with P/D + KV-aware + SLA scheduling |
| **Agent Router** (formerly Envoy AI Gateway) | https://theagentrouter.ai/ | Full GAIE (v1.6 from v1.2.0) + provider abstraction (Bedrock, Vertex, Anthropic) |
| **kgateway** | https://kgateway.dev/ | Lightweight Envoy Gateway successor |
| **Istio** | https://istio.io/latest/blog/2025/inference-extension-support/ | 1.28+ supports InferencePool; pair when a mesh is already in place |
| **NGINX Gateway Fabric** | https://blog.nginx.org/blog/ngf-supports-gateway-api-inference-extension | NGINX-based GAIE |

### Version gate

Pre-v1 CRDs (`v1alpha1`, `v1alpha2`) will not work with current gateways. Convert to v1.

## Non-GAIE options (still viable)

### vllm-production-stack router

- Repo: https://github.com/vllm-project/production-stack/tree/main/src/vllm_router
- Bundled with the production-stack Helm chart.
- Modes: round-robin, session-sticky, prefix-aware, KV-aware (Q1 2025 roadmap → GA'd), disagg-prefill.
- Non-GAIE; speaks OpenAI API directly. GAIE-compat path exists: https://docs.vllm.ai/projects/production-stack/en/latest/deployment/gateway-inference-extension.html

### vllm-semantic-router

- Site: https://vllm-sr.ai/
- Repo: https://github.com/vllm-project/semantic-router
- Envoy `ext_proc` filter — semantic routing across *different* models by query intent.
- v0.1 Iris launch: https://blog.vllm.ai/2026/01/05/vllm-sr-iris.html
- Orthogonal to prefix-aware routing (which is same-model replicas). Use together when both axes are needed.

### Plain nginx

- vLLM ships a recipe: ``vllm` repo: docs/deployment/nginx.md`
- Round-robin only. Viable for small fleets that don't need inference-aware routing.

## OpenShift Route (the 60-second gotcha)

OpenShift's HAProxy Router has a **60-second default idle timeout** that kills long
SSE streams; fix it with `haproxy.router.openshift.io/timeout: 10m`. Full Route
manifest and the surrounding OCP specifics: `openshift.md` § Routes.

## Gateway API on OpenShift (version gate)

The OCP-version GA table (4.17 dev-preview, 4.19+ GA) and the OSSM-vs-Gateway-API conflict live in `references/openshift.md` §Routes, Gateway API, and service mesh. Before 4.19, stick with Route; from 4.19, Gateway API + GAIE are viable.

## Istio sidecar caveat for streaming

The Envoy sidecar buffers SSE by default. Options:

1. **Disable sidecar on the vLLM pod** (`sidecar.istio.io/inject: "false"`). Simplest.
2. Configure `proxy.istio.io/config: { holdApplicationUntilProxyStarts: true }` and ensure no response-buffering EnvoyFilter is attached. Harder.

When streaming replies appear all-at-once rather than token-by-token, suspect Istio first.

## Prefix-aware vs KV-aware vs semantic routing

| Approach | Goal | Where it lives |
|---|---|---|
| Round-robin / session-sticky | Basic load distribution | Any LB (nginx, GAIE EPP, production-stack router) |
| Prefix-aware | Maximize prefix-cache hit rate | production-stack router, llm-d EPP, GAIE EPP plugins |
| KV-aware | Route to pod whose KV holds the session | llm-d EPP (the big one), AIBrix, production-stack v1 |
| Semantic | Route by query intent / domain | vllm-semantic-router |
| Disagg-prefill | Route prefill to prefill pool, decode to decode pool | llm-d, production-stack, NVIDIA Dynamo |

Prefix-aware alone often beats KV-aware for chat workloads (conversation prefixes repeat). KV-aware shines when sessions persist long enough that KV eviction is the ceiling. Measure.

## Load balancing across replicas — health & draining

- **Readiness probe** (see `references/pod-shape.md`) is what the LB uses to decide readiness. Keep it fast (`/health`) and don't hit `/v1/models` (slower).
- **`--shutdown-timeout N` + `terminationGracePeriodSeconds` ≥ N + 30**: vLLM aborts in-flight streams on SIGTERM unless `--shutdown-timeout` is set (default `0`); the grace period alone drains nothing. Gateways that honour `preStop` can drain cleanly.
- **`lifecycle.preStop`**: sleep 5–10 s to let the LB stop sending before the process dies.

## Autoscaler coordination

The gateway/router publishes queue metrics. KEDA consumes them via Prometheus. On llm-d, KEDA scales on the EPP's metrics; llm-d's WVA is deprecated (v0.10.0).

See `references/autoscaling.md`.

## Smoke test — is routing working?

```bash
# Pool view from GAIE
kubectl get inferencepool,inferencemodel -A

# EPP picking endpoints
kubectl logs -n <ns> -l app=endpoint-picker --tail=100

# Try a prompt against the gateway
curl -fsS $GATEWAY_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-235b", "messages": [{"role":"user","content":"hi"}]}'
```

## Next

- Pick the ecosystem project and routing model: `references/ecosystem.md`
- Scale the fleet: `references/autoscaling.md`
- Cross-pod KV for disagg routing: `references/disagg.md`
