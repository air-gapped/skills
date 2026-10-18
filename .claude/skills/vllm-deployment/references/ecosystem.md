# Ecosystem — the K8s projects around vLLM

A pointer map to the control-plane and data-plane projects that deploy, route, autoscale, and coordinate vLLM on Kubernetes. For each: canonical URL, what it does, when to pick it, and the single biggest differentiator from its siblings.

## Table of Contents

- [Decision matrix](#decision-matrix)
- [Projects in detail](#projects-in-detail)
- [Ray Serve](#ray-serve)
- [Load-bearing comparisons to read](#load-bearing-comparisons-to-read)
- [Consolidation / breaking-change notes](#consolidation--breaking-change-notes)

---

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
| K8s-standard routing CRD (`InferencePool`) | **Gateway API Inference Extension (GAIE)** | SIG-Network, GA Sept 2025 |
| GAIE implementation with provider-abstraction (Bedrock/Vertex/Anthropic) | **Agent Router** (formerly Envoy AI Gateway) | Multi-provider BYOK + cost metering |
| OpenShift-supported, Red Hat-built vLLM | **RHAIIS** (see `references/openshift.md`) | Upstream vLLM + RH lifecycle + SCC-friendly image |

## Projects in detail

### LeaderWorkerSet (LWS)

- **Repo / site**: https://github.com/kubernetes-sigs/lws · https://lws.sigs.k8s.io/docs/
- **Version**: **v1.0.0** (2026-10-16) — **GA**; controller config API graduates to `config.lws.x-k8s.io/v1`. Upgrade hazard: a DisaggregatedSet created on v0.9.x must roll out once on v0.10.x/v0.11.x before v1.0.0 — see `references/multi-node.md`
- **Maintainer / license**: Kubernetes SIG-Apps · Apache-2.0
- **Role**: K8s primitive for "group of pods as a unit of replication". The gang-scheduling piece of every multi-node vLLM deploy.
- **vLLM integration**: https://github.com/kubernetes-sigs/lws/tree/main/docs/examples — wraps `examples/ray_serving/multi-node-serving.sh`
- **Pick when**: The minimum primitive is wanted without an opinionated control plane, or to understand what the fancier projects do under the hood.
- **Gang scheduling**: native support is **alpha and opt-in** (KEP-666, `WorkloadAwareScheduling` gate; needs the Kubernetes 1.37 Workload/PodGroup APIs with `GenericWorkload` enabled). Otherwise pair with Kueue or Volcano if strict gang-scheduling matters.

### vllm-production-stack (UC Berkeley + UChicago)

- **Repo**: https://github.com/vllm-project/production-stack · docs: https://docs.vllm.ai/projects/production-stack/
- **Helm chart version**: **vllm-stack-0.1.13** (2026-09-29) — adds `pvcExistingClaimName` for an externally managed PVC and `shmSize` on the operator's `VLLMRuntime`; the inference gateway path moved from kgateway to agentgateway
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
- **Version**: **v0.10.0** (2026-09-29) — base image `vllm/vllm-openai:v0.30.0`, GAIE CRDs still **v1.5.0**, LWS 0.11.0. `ghcr.io/llm-d/llm-d-cuda` is **deprecated in favour of `docker.io/vllm/vllm-openai`**; WVA deprecated (KEDA on EPP metrics instead — `references/autoscaling.md`); `llm-d-kv-cache` merged into `llm-d-router`. Release notes carry a per-component version table — read it rather than assuming the umbrella tag applies to every sub-component
- **Maintainer / license**: Red Hat + Google Cloud + IBM + NVIDIA + CoreWeave · Apache-2.0
- **CNCF status**: Sandbox as of Mar 2026 (https://www.cncf.io/blog/2026/03/24/welcome-llm-d-to-the-cncf-evolving-kubernetes-into-sota-ai-infrastructure/)
- **Role**: K8s-native distributed vLLM orchestrator. Inference scheduler (P/D-aware, KV-aware, SLA-aware, load-aware). "The orchestrator to vLLM's engine."
- **Architecture**: https://llm-d.ai/docs/architecture
- **Current shape**: Helm chart (https://github.com/llm-d-incubation/llm-d-modelservice). The old CRD-operator `llm-d/llm-d-model-service` is **deprecated** (consolidation mid-2025).
- **Deployer**: https://github.com/llm-d/llm-d-deployer
- **GAIE integration**: Native. Uses upstream `InferencePool`; the full-featured Endpoint Picker (EPP) now lives in llm-d (moved from GAIE in v1.6.0) and plugs into Envoy/Istio/kgateway.
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
- **Version**: **v0.8.0** (2026-10-13) — adds experimental ModelClaim (several models sharing GPU runtimes) and ModelWarmup (node image preload), StormService multi-node rollout/scale-in fixes
- **Paper**: https://arxiv.org/abs/2504.03648
- **Maintainer / license**: ByteDance-originated, now under vLLM org · Apache-2.0
- **Role**: Full cloud-native control plane. High-density LoRA, StormService CRD, distributed KV cache, P/D disagg (v0.4), heterogeneous-GPU scheduling.
- **Pick when**: ByteDance-scale multi-tenancy (LoRA fan-out), multi-engine fleet (vLLM + SGLang), heterogeneous-GPU.
- **Launch post**: https://blog.vllm.ai/2025/02/21/aibrix-release.html
- **v0.4 release**: https://aibrix.github.io/posts/2025-08-04-v0.4.0-release/
- **KubeCon talks**: KubeCon NA 2025 keynote "AIBrix: K8s-native GenAI Inference Infrastructure"; KubeCon EU 2025 with Google on LLM-aware LB

### NVIDIA Dynamo

- **Repo**: https://github.com/ai-dynamo/dynamo · NIXL: https://github.com/ai-dynamo/nixl
- **Version**: **v1.5.1** (2026-10-07) is the newest *stable*, via v1.5.0 (2026-09-21); bundles **vLLM v0.28.0**. v1.5.0: `nvidia.com/v1beta1` is the CRD storage version, the Go EPP is removed (Rust EPP in the Frontend image, `eppConfig` deprecated), `DynamoCheckpoint` CRD replaced by the standalone Snapshot operator's `PodSnapshot`, KVBM deprecated (removal targeted v1.7.0). v1.5.1: workers fetching media through an HTTP proxy need `DYN_MM_TRUST_EGRESS_PROXY=1`. **Do not sort this repo's tags by date**: it publishes model-specific dev prereleases (`v1.6.0-glm-5.3-flash-dev.1`, `v1.5.0-kimi-k3-post.1`, …) newer by date and higher by version than the stable while flagged `prerelease`. Filter on `isPrerelease=false`
- **Maintainer / license**: NVIDIA · Apache-2.0
- **Role**: Disagg-native serving framework; backend-agnostic (vLLM, SGLang, TRT-LLM). Dynamo = orchestrator + NIXL data plane; vLLM consumes NIXL via its own `NixlConnector`.
- **Relation to vLLM's native Nixl/Mooncake**: Dynamo drives Nixl; vLLM exposes the connector. They're complementary layers, not competitors. Mooncake is a parallel alternative (KV-store-first).
- **Pick when**: NVIDIA's reference disagg stack is wanted with tight NIXL integration across all three engines.
- **Launch**: https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/
- **Integration with llm-d**: https://developer.nvidia.com/blog/nvidia-dynamo-accelerates-llm-d-community-initiatives-for-advancing-large-scale-distributed-inference/
- **EKS blueprint**: https://awslabs.github.io/ai-on-eks/docs/blueprints/inference/framework-guides/GPUs/nvidia-dynamo
- **AKS blueprint**: https://blog.aks.azure.com/2025/10/24/dynamo-on-aks
- **GCP recipe**: https://cloud.google.com/blog/products/compute/ai-inference-recipe-using-nvidia-dynamo-with-ai-hypercomputer

### KServe vLLM runtime

- **Docs**: https://kserve.github.io/website/docs/intro · https://docs.vllm.ai/en/stable/deployment/integrations/kserve/
- **Version**: **v0.21.0** (2026-09-25); `LLMInferenceService` samples moved from `v1alpha1` to `v1alpha2`
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
- **Status**: v1 `InferencePool` **GA** (Sept 2025); latest **v1.6.2** (2026-09-17). v1.6.0 moved the full EPP, Body-Based Routing and the latency predictor to llm-d, removed the alpha `InferenceObjective` / `InferenceModelRewrite` / `EndpointPickerConfig`, and made `InferencePool.spec.endpointPickerRef` optional. llm-d v0.10.0 still pins GAIE v1.5.0 CRDs — check both sides before mixing versions
- **Maintainer / license**: K8s SIG-Network · Apache-2.0
- **CRDs**: `InferencePool` (v1) + alpha `InferencePoolImport`. `InferenceModel` is gone (v1.0). Endpoint Picker (EPP) is the ext_proc gRPC server that picks the endpoint; GAIE itself now ships only the conformance `lwepp`.
- **Implementers**: llm-d, Agent Router (formerly Envoy AI Gateway), kgateway, Istio 1.28+, NGINX Gateway Fabric
- **Pick when**: K8s-standard routing CRDs are wanted that multiple gateways (Envoy / kgateway / Istio) can implement. Future-proof.
- **Intro**: https://kubernetes.io/blog/2025/06/05/introducing-gateway-api-inference-extension/
- **CNCF deep dive**: https://www.cncf.io/blog/2025/04/21/deep-dive-into-the-gateway-api-inference-extension/
- **Istio support**: https://istio.io/latest/blog/2025/inference-extension-support/
- **NGF support**: https://blog.nginx.org/blog/ngf-supports-gateway-api-inference-extension

### Agent Router (formerly Envoy AI Gateway)

- **Site**: https://theagentrouter.ai/ (old `aigateway.envoyproxy.io` redirects)
- **Repo**: https://github.com/theagentrouter/agent-router — **renamed and moved owner from `envoyproxy/ai-gateway`**; the old URL still 200s by redirect. The API group (`aigateway.envoyproxy.io`), CRDs, Helm charts, images and `aigw` CLI keep their old names.
- **Version**: **v1.2.0** (2026-10-07) — first release under the new name; moves to Envoy Gateway v1.9.2, Gateway API v1.6 and **GAIE v1.6** (an `InferencePool` without `endpointPickerRef` is reported `Accepted=False`); security fixes change behaviour — read its breaking changes before upgrading. v1.1.0 turned on a restricted `securityContext` with non-root UID 65532 by default, which breaks custom controller images that cannot run as that UID. The core API (`AIGatewayRoute`, `AIServiceBackend`, `BackendSecurityPolicy`, `GatewayConfig`, `MCPRoute`) is stable for 1.x but still served at **`v1beta1`** — keep `v1beta1` in manifests
- **Maintainer / license**: Envoy Foundation · Apache-2.0
- **Role**: GAIE implementation built on Envoy Gateway. Adds provider-abstraction (Bedrock, Vertex, Anthropic) and token-based cost metering on top of `InferencePool`.
- **Pick when**: Multi-provider BYOK gateway + GAIE in one. Alternative to kgateway/Istio for the GAIE layer.

### vllm-semantic-router

- **Site**: https://vllm-sr.ai/
- **Repo**: https://github.com/vllm-project/semantic-router
- **Version**: **v0.4.0** "Hermes" (2026-09-27); `pip install vllm-sr==0.4.0`
- **Launch**: https://blog.vllm.ai/2026/01/05/vllm-sr-iris.html
- **Role**: Envoy `ext_proc` that does **semantic** routing (mixture-of-models across different models by query domain/intent). Ships with Milvus integration.
- **Pick when**: Multi-model fleet routing `general` → small model, `code`/`math` → large model.
- **Orthogonal to**: Prefix-aware routing (same-model replicas) — use production-stack router or GAIE EPP for that.

## Ray Serve

Not strictly a K8s project, but Ray Serve on KubeRay is a sibling deployment path.

- **Repo**: https://github.com/ray-project/ray
- **K8s operator**: https://github.com/ray-project/kuberay
- **Example**: ``vllm` repo: examples/ray_serving/ray_serve_deepseek.py`
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
2. **LWS**: **v1.0.0 GA** (2026-10-16). v1.0.0 drops slice-less LWS for DisaggregatedSets created on v0.9.x — roll those once on v0.10.x/v0.11.x before upgrading.
3. **Dynamo**: `vllm-runtime` container is versioned independently of vLLM upstream (v1.5.x bundles vLLM v0.28.0); pin carefully. v1.5.0 removed the `DynamoCheckpoint` CRD and the Go EPP.
4. **GAIE**: v1 `InferencePool` is GA; pre-v1 (`v1alpha1`, `v1alpha2`) manifests break, and v1.6.0 removed the alpha `InferenceObjective`/`InferenceModelRewrite`/`EndpointPickerConfig`.
5. **AIBrix**: v0.4 (Aug 2025) introduced KVCache v1 connector + KV event sync — older v0.2 deploys need migration.
6. **KServe**: ModelMesh path deprecated for LLM workloads; use the single-model (KServe Raw Deployments) path.
