# Ecosystem — the K8s projects around vLLM

A pointer map to the control-plane and data-plane projects that deploy, route, autoscale, and coordinate vLLM on Kubernetes. For each: canonical URL, what it does, when to pick it, and the single biggest differentiator from its siblings.

## Decision matrix

| Goal | Pick | Why |
|---|---|---|
| Minimum K8s primitive, multi-node TP/PP, no opinionated control plane | **LWS** | Apache-2.0 sig-apps primitive; every other project uses it under the hood |
| Reference stack = router + vLLM + LMCache + observability, one `helm install` | **vllm-production-stack** | Opinionated monorepo; UC Berkeley LMCache + vLLM |
| Disagg P/D + Wide-EP + GAIE + SLA-aware scheduler | **llm-d** | K8s-native distributed orchestrator; CNCF sandbox (Mar 2026) |
| Multi-tenant LoRA fan-out, heterogeneous-GPU fleet, StormService CRD | **AIBrix** | ByteDance-scale control plane; vLLM + SGLang multi-engine |
| NVIDIA reference stack with NIXL, cross-engine (vLLM + SGLang + TRT-LLM) | **NVIDIA Dynamo** | NVIDIA-backed, disagg-native, NIXL data plane |
| Declarative `InferenceService` CR; ML-ops surface (transformers, explainers) | **KServe vLLM runtime** | LF AI & Data; predictor/transformer/explainer story |
| Router in front of a fleet of same-model replicas (prefix-aware) | **production-stack router** | Ships with production-stack |
| Router in front of many-model fleet (route by intent/domain) | **vllm-semantic-router** | Envoy ext_proc + Milvus embeddings |
| K8s-standard routing CRD (InferencePool + InferenceModel) | **Gateway API Inference Extension (GAIE)** | SIG-Network, GA Sept 2025 |
| GAIE implementation with provider-abstraction (Bedrock/Vertex/Anthropic) | **Envoy AI Gateway** | Multi-provider BYOK + cost metering |
| OpenShift-supported, Red Hat-built vLLM | **RHAIIS** (see `references/openshift.md`) | Upstream vLLM + RH lifecycle + SCC-friendly image |

## Projects in detail

### LeaderWorkerSet (LWS)

- **Repo / site**: https://github.com/kubernetes-sigs/lws · https://lws.sigs.k8s.io/docs/
- **Version (Apr 2026)**: v0.8.0 (pre-GA; no v1.0 cut yet)
- **Maintainer / license**: Kubernetes SIG-Apps · Apache-2.0
- **Role**: K8s primitive for "group of pods as a unit of replication". The gang-scheduling piece of every multi-node vLLM deploy.
- **vLLM integration**: https://github.com/kubernetes-sigs/lws/tree/main/docs/examples/vllm — wraps `examples/online_serving/multi-node-serving.sh`
- **Pick when**: The minimum primitive is wanted without an opinionated control plane, or to understand what the fancier projects do under the hood.
- **Known limitation**: No native gang-scheduling ([issue #167](https://github.com/kubernetes-sigs/lws/issues/167)) — pair with Kueue or Volcano if strict gang-scheduling matters.

### vllm-production-stack (UC Berkeley + UChicago)

- **Repo**: https://github.com/vllm-project/production-stack · docs: https://docs.vllm.ai/projects/production-stack/
- **Helm chart**: https://github.com/vllm-project/production-stack/tree/main/helm · values: https://github.com/vllm-project/production-stack/blob/main/helm/values.yaml
- **Maintainer / license**: UC Berkeley Sky Lab + UChicago LMCache + vLLM · Apache-2.0
- **Role**: Reference "stack" — router + N vLLM engines + LMCache tiered KV + observability, packaged as one Helm release.
- **Router modes**: round-robin, session-sticky, prefix-aware, KV-aware, disagg-prefill
- **Pick when**: Single team, opinionated monorepo, LMCache + router + vLLM triad bundled.
- **Supersedes**: Many ad-hoc vLLM Helm charts from 2024.
- **Load-bearing blog posts**:
  - https://blog.vllm.ai/2025/01/21/stack-release.html — launch
  - https://blog.lmcache.ai/en/2025/01/21/high-performance-and-easy-deployment-of-vllm-in-k8s-with-vllm-production-stack/
  - https://blog.lmcache.ai/en/2025/02/20/deploying-llms-in-clusters-2-running-vllm-production-stack-on-aws-eks-and-gcp-gke/
  - https://blog.lmcache.ai/en/2025/03/06/open-source-llm-inference-cluster-performing-10x-faster-than-sota-oss-solution/ (disputed comparison vs AIBrix)

### llm-d

- **Repo / site**: https://github.com/llm-d/llm-d · https://llm-d.ai/
- **Version (Apr 2026)**: v0.5.1 (Mar 2026)
- **Maintainer / license**: Red Hat + Google Cloud + IBM + NVIDIA + CoreWeave · Apache-2.0
- **CNCF status**: Sandbox as of Mar 2026 (https://www.cncf.io/blog/2026/03/24/welcome-llm-d-to-the-cncf-evolving-kubernetes-into-sota-ai-infrastructure/)
- **Role**: K8s-native distributed vLLM orchestrator. Inference scheduler (P/D-aware, KV-aware, SLA-aware, load-aware). "The orchestrator to vLLM's engine."
- **Architecture**: https://llm-d.ai/docs/architecture
- **Current shape**: Helm chart (https://github.com/llm-d-incubation/llm-d-modelservice). The old CRD-operator `llm-d/llm-d-model-service` is **deprecated** (consolidation mid-2025).
- **Deployer**: https://github.com/llm-d/llm-d-deployer
- **GAIE integration**: Native. Uses upstream `InferencePool` + `InferenceModel`, plugs its Endpoint Picker (EPP) into Envoy/Istio/kgateway.
- **Pick when**: Disagg P/D is first-class; KV-aware routing, HA, and GAIE-native gateway needed without assembling three projects.
- **Key blog posts**:
  - https://llm-d.ai/blog/llm-d-press-release — launch (May 2025)
  - https://llm-d.ai/blog/llm-d-v0.3-expanded-hardware-faster-perf-and-igw-ga — IGW GA, prefix scorers, WVA autoscaler, scale-to-zero
  - https://developers.redhat.com/articles/2025/05/20/llm-d-kubernetes-native-distributed-inferencing
  - https://developers.redhat.com/articles/2025/09/08/scaling-deepseek-style-moes-vllm-and-llm-d-using-wide-ep
  - https://developers.redhat.com/articles/2025/10/07/master-kv-cache-aware-routing-llm-d-efficient-ai-inference
  - https://www.redhat.com/en/blog/demystifying-llm-d-and-vllm-race-production

### AIBrix

- **Repo**: https://github.com/vllm-project/aibrix
- **Version (Apr 2026)**: v0.4.x (Aug 2025 base)
- **Paper**: https://arxiv.org/abs/2504.03648
- **Maintainer / license**: ByteDance-originated, now under vLLM org · Apache-2.0
- **Role**: Full cloud-native control plane. High-density LoRA, StormService CRD, distributed KV cache, P/D disagg (v0.4), heterogeneous-GPU scheduling.
- **Pick when**: ByteDance-scale multi-tenancy (LoRA fan-out), multi-engine fleet (vLLM + SGLang), heterogeneous-GPU.
- **Launch post**: https://blog.vllm.ai/2025/02/21/aibrix-release.html
- **v0.4 release**: https://aibrix.github.io/posts/2025-08-04-v0.4.0-release/
- **KubeCon talks**: KubeCon NA 2025 keynote "AIBrix: K8s-native GenAI Inference Infrastructure"; KubeCon EU 2025 with Google on LLM-aware LB

### NVIDIA Dynamo

- **Repo**: https://github.com/ai-dynamo/dynamo · NIXL: https://github.com/ai-dynamo/nixl
- **Version (Apr 2026)**: v1.x (2025–2026)
- **Maintainer / license**: NVIDIA · Apache-2.0
- **Role**: Disagg-native serving framework; backend-agnostic (vLLM, SGLang, TRT-LLM). Dynamo = orchestrator + NIXL data plane; vLLM consumes NIXL via its own `NixlConnector`.
- **Relation to vLLM's native Nixl/Mooncake**: Dynamo drives Nixl; vLLM exposes the connector. They're complementary layers, not competitors. Mooncake is a parallel alternative (KV-store-first).
- **Pick when**: NVIDIA's reference disagg stack is wanted with tight NIXL integration across all three engines.
- **Launch**: https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/
- **Integration with llm-d**: https://developer.nvidia.com/blog/nvidia-dynamo-accelerates-llm-d-community-initiatives-for-advancing-large-scale-distributed-inference/
- **EKS blueprint**: https://awslabs.github.io/ai-on-eks/docs/blueprints/inference/GPUs/nvidia-dynamo
- **AKS blueprint**: https://blog.aks.azure.com/2025/10/24/dynamo-on-aks
- **GCP recipe**: https://cloud.google.com/blog/products/compute/ai-inference-recipe-using-nvidia-dynamo-with-ai-hypercomputer

### KServe vLLM runtime

- **Docs**: https://kserve.github.io/website/docs/ · https://docs.vllm.ai/en/stable/deployment/integrations/kserve/
- **0.15 GenAI release**: https://www.cncf.io/blog/2025/06/18/announcing-kserve-v0-15-advancing-generative-ai-model-serving/
- **Maintainer / license**: LF AI & Data · Apache-2.0
- **Role**: Declarative `InferenceService` CRD with vLLM as a pre-bundled `ClusterServingRuntime`; HuggingFace + safetensors.
- **Autoscaling**: Knative KPA (legacy) or KEDA on Prometheus metrics. Preferred = KEDA on `vllm:num_requests_waiting`.
- **Pick when**: KServe / OpenShift AI already in place; the predictor/transformer/explainer surface on top of vLLM is wanted.
- **Limitation**: Weakest story for disagg P/D; no native KV-aware routing.
- **Autoscaling posts**:
  - https://developers.redhat.com/articles/2025/09/23/how-set-kserve-autoscaling-vllm-keda
  - https://developers.redhat.com/articles/2025/11/26/autoscaling-vllm-openshift-ai-model-serving

### Gateway API Inference Extension (GAIE)

- **Site**: https://gateway-api-inference-extension.sigs.k8s.io/
- **Repo**: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- **Status (Apr 2026)**: v1 CRDs **GA** (Sept 2025); Gateway API 1.4 (Nov 2025) includes IGW integration
- **Maintainer / license**: K8s SIG-Network · Apache-2.0
- **CRDs**: `InferencePool` (platform — pods on shared GPU nodes) + `InferenceModel` (ML owner — public model name → pool). Endpoint Picker (EPP) is the ext_proc gRPC server that picks the endpoint.
- **Implementers**: llm-d, Envoy AI Gateway, kgateway, Istio 1.28+, NGINX Gateway Fabric
- **Pick when**: K8s-standard routing CRDs are wanted that multiple gateways (Envoy / kgateway / Istio) can implement. Future-proof.
- **Intro**: https://kubernetes.io/blog/2025/06/05/introducing-gateway-api-inference-extension/
- **CNCF deep dive**: https://www.cncf.io/blog/2025/04/21/deep-dive-into-the-gateway-api-inference-extension/
- **Istio support**: https://istio.io/latest/blog/2025/inference-extension-support/
- **NGF support**: https://blog.nginx.org/blog/ngf-supports-gateway-api-inference-extension

### Envoy AI Gateway

- **Site**: https://aigateway.envoyproxy.io/
- **Repo**: https://github.com/envoyproxy/ai-gateway
- **Version**: v0.3.x (from 2025)
- **Maintainer / license**: Envoy Foundation · Apache-2.0
- **Role**: GAIE implementation built on Envoy Gateway. Adds provider-abstraction (Bedrock, Vertex, Anthropic) and token-based cost metering on top of `InferencePool`.
- **Pick when**: Multi-provider BYOK gateway + GAIE in one. Alternative to kgateway/Istio for the GAIE layer.

### vllm-semantic-router

- **Site**: https://vllm-semantic-router.com/
- **Repo**: https://github.com/vllm-project/semantic-router
- **Version**: v0.1 "Iris" (Jan 2026)
- **Launch**: https://blog.vllm.ai/2026/01/05/vllm-sr-iris.html
- **Role**: Envoy `ext_proc` that does **semantic** routing (mixture-of-models across different models by query domain/intent). Ships with Milvus integration.
- **Pick when**: Multi-model fleet routing `general` → small model, `code`/`math` → large model.
- **Orthogonal to**: Prefix-aware routing (same-model replicas) — use production-stack router or GAIE EPP for that.

## Ray Serve

Not strictly a K8s project, but Ray Serve on KubeRay is a sibling deployment path.

- **Repo**: https://github.com/ray-project/ray
- **K8s operator**: https://github.com/ray-project/kuberay
- **Example**: ``vllm` repo: examples/online_serving/ray_serve_deepseek.py`
- **Pick when**: Multi-tenant Ray cluster shared across vLLM + training + batch.
- **Metrics caveat**: Ray Serve doesn't auto-expose vLLM `/metrics`. Wire `RayPrometheusStatLogger` explicitly or use Ray 2.51+ ingestion. See `vllm-observability` skill §Ray.

## Load-bearing comparisons to read

- **Red Hat — Demystifying llm-d and vLLM**: https://www.redhat.com/en/blog/demystifying-llm-d-and-vllm-race-production
- **Red Hat — Why vLLM is the best choice**: https://developers.redhat.com/articles/2025/10/30/why-vllm-best-choice-ai-inference-today
- **MarkTechPost — Top 6 inference runtimes 2025**: https://www.marktechpost.com/2025/11/07/comparing-the-top-6-inference-runtimes-for-llm-serving-in-2025/
- **LMCache — 10x faster than SOTA OSS** (production-stack vs AIBrix): https://blog.lmcache.ai/en/2025/03/06/open-source-llm-inference-cluster-performing-10x-faster-than-sota-oss-solution/
- **KubeCon NA 2025 — Future of llm-d and vLLM (James Harmison, Red Hat)**: https://www.youtube.com/watch?v=1sejSbvXKl8
- **PyTorch Conference 2025 vLLM hub**: https://github.com/vllm-project/vLLM-in-PyTorch-Conference-2025

## Consolidation / breaking-change notes

1. **llm-d**: `llm-d-model-service` operator **deprecated**; functionality moved to `llm-d-incubation/llm-d-modelservice` Helm chart (mid-2025).
2. **LWS**: still pre-1.0 (v0.8.0) despite broad adoption — no API-stability promise yet; watch for v1.0.
3. **Dynamo**: `vllm-runtime` container is versioned independently of vLLM upstream; pin carefully.
4. **GAIE**: v1 CRD spec is GA; pre-v1 (`v1alpha1`, `v1alpha2`) manifests will break.
5. **AIBrix**: v0.4 (Aug 2025) introduced KVCache v1 connector + KV event sync — older v0.2 deploys need migration.
6. **KServe**: ModelMesh path deprecated for LLM workloads; use the single-model (KServe Raw Deployments) path.
