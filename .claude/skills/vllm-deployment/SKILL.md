---
name: vllm-deployment
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Deploy production vLLM on Kubernetes, OpenShift, Docker/Podman. Pod shape (load-bearing `/dev/shm`, cold-load liveness 600s), multi-node LWS + Ray, control plane (llm-d, production-stack, AIBrix, NVIDIA Dynamo, KServe), Gateway API Inference Extension, KEDA autoscaling, disaggregated prefill/decode (Nixl/Mooncake/LMCache/MORI-IO), RHAIIS on OpenShift (SCC, arbitrary UID, Routes 60s, ModelCar, air-gapped).
when_to_use: |-
  Trigger on symptoms (TP>1 segfault, NCCL hang, `/dev/shm` too small, KEDA thrash, disagg P/D can't talk, SSE cuts at 60s OCP, arbitrary-UID SCC fail, Route timeout) and keywords "deploy vllm", "vllm k8s", "vllm helm", "vllm openshift", "rhaiis", "rhoai", "leaderworkerset", "lws", "kserve", "servingruntime", "llm-d", "production-stack", "aibrix", "nvidia dynamo", "gateway api inference extension", "inferencepool", "envoy ai gateway", "keda vllm", "disaggregated prefill", "nixl", "mooncake", "lmcache", "shm size", "sr-iov", "roce", "air gapped vllm", "modelcar". Pod-shape probes, nodeSelector H100/H200/B200/B300, picking llm-d vs production-stack vs AIBrix vs KServe, LWS vs KubeRay, disagg compose. Also implicit — "audit model", "deploy-memo", "manifest", "k8s yaml", "deployment yaml", "pod spec", "serve args", "serve_args", "required_deploy", "check prior manifests", "read prior manifests", "cross-check flags", "flag drift", "how to run {model} in prod", "inference platform for {model}" — authoring/reviewing per-model deploy recipes or K8s manifests that map to vLLM pod shape, LWS, or serving runtime.
---

# vLLM deployment (Kubernetes first, Docker lab, OpenShift sidebar)

Target audience: platform engineers bringing up vLLM on production Kubernetes (H100/H200/B200/B300 fleets), and individual researchers running 1-to-2-node Docker / Podman setups in a lab.

This skill is a **pointer map**. It points to the canonical sources — in the vLLM repo, in docs.vllm.ai, in the ecosystem repos, and to the load-bearing blog posts — rather than paraphrasing them. Paraphrase rots; pointers survive.

## Decision guide — pick the path

| Situation | Go to |
|---|---|
| Single node, 1 container, TP ≤ 8 | `references/docker-lab.md` |
| Single host, 2 containers for PD disagg lab | `references/docker-lab.md` (compose template) + `references/disagg.md` |
| k8s, single model fits 1 pod | `references/pod-shape.md` + in-tree helm chart |
| k8s, model needs multi-node TP/PP | `references/multi-node.md` (LWS + `multi-node-serving.sh`) |
| k8s fleet, router + LMCache + observability bundled | `vllm-production-stack` (Helm) — see `references/ecosystem.md` |
| k8s fleet, disagg P/D + KV-aware + GAIE + SLA scheduler | `llm-d` — see `references/ecosystem.md` |
| k8s fleet, ByteDance-scale multi-tenant LoRA + heterogenous GPU | `AIBrix` — see `references/ecosystem.md` |
| NVIDIA reference stack on prem / EKS / AKS with NIXL | `NVIDIA Dynamo` — see `references/ecosystem.md` |
| OpenShift / RHOAI | `references/openshift.md` + RHAIIS images |
| Routing / load balancing across pods | `references/routing.md` (GAIE, Envoy AI Gateway, Istio, production-stack router, semantic-router) |
| Air-gapped k8s or OCP | `references/openshift.md` §air-gapped + `vllm-configuration` skill for HF mirror |

## The three load-bearing facts

1. **`/dev/shm` is the single most common cause of silent multi-GPU failure on k8s.** On vanilla k8s there is no `--ipc=host`. Without a shared-memory volume, `torch.distributed` segfaults on the first all-reduce of a TP>1 pod. Mount an `emptyDir` with `medium: Memory` and `sizeLimit: 10Gi` at `/dev/shm`. Documented in vLLM's own k8s guide — see ``vllm` repo: docs/deployment/k8s.md:209,289`.
2. **Multi-node vLLM on k8s is Ray-on-LWS, not headless Service.** The `parallel-config` + pure headless-Service path exists but is not the vLLM-endorsed recipe. Use LeaderWorkerSet (`kubernetes-sigs/lws`) as the gang-scheduling primitive and `examples/online_serving/multi-node-serving.sh` (which bootstraps Ray head/worker) as the entrypoint. Since Nov 2025 the `ray symmetric-run` pattern replaces the old head/worker split — see `https://blog.vllm.ai/2025/11/22/ray-symmetric-run.html`.
3. **The upstream `vllm/vllm-openai` image runs as root.** On OpenShift (and any k8s cluster with `restricted-v2` PSA), that is a deploy-time failure. Either rebuild with `chgrp -R 0 /root /tmp && chmod -R g=u /root /tmp`, or use the Red Hat RHAIIS images (`registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.3.0`), which are UID-agnostic by construction.

## Minimum viable pod shape

```yaml
# Deployment essentials — not a complete manifest. Full annotated template in references/pod-shape.md.
spec:
  template:
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:<pinned-tag>          # do NOT use :latest
        args: ["--model", "$(MODEL)", "--tensor-parallel-size", "8",
               "--disable-access-log-for-endpoints", "/health,/metrics,/ping"]
        env:
        - {name: VLLM_HOST_IP, valueFrom: {fieldRef: {fieldPath: status.podIP}}}
        - {name: HF_HOME, value: /models/.cache}      # pre-warmed PVC or ModelCar
        - {name: VLLM_NO_USAGE_STATS, value: "1"}     # disable telemetry
        - {name: VLLM_DO_NOT_TRACK, value: "1"}
        # For multi-NIC nodes (SR-IOV, RDMA, multiple eth):
        # - {name: NCCL_SOCKET_IFNAME, value: "eth0"}
        # - {name: NCCL_IB_HCA,         value: "mlx5_*"}
        ports: [{containerPort: 8000, name: http}]
        readinessProbe: {httpGet: {path: /health, port: http}, periodSeconds: 5,  failureThreshold: 3}
        livenessProbe:  {httpGet: {path: /health, port: http}, periodSeconds: 10, failureThreshold: 3, initialDelaySeconds: 600}
        resources:
          limits: {nvidia.com/gpu: 8}
        volumeMounts:
        - {name: dshm, mountPath: /dev/shm}           # LOAD-BEARING
        - {name: models, mountPath: /models}
      volumes:
      - name: dshm
        emptyDir: {medium: Memory, sizeLimit: 10Gi}   # LOAD-BEARING
      - name: models
        persistentVolumeClaim: {claimName: vllm-model-cache}
      nodeSelector: {nvidia.com/gpu.product: NVIDIA-H200}
```

The `initialDelaySeconds: 600` on the liveness probe is not excessive — cold model loads on a 405B FP8 take 8–12 min. A 30 s default makes the pod liveness-kill before it ever becomes ready. See `VLLM_ENGINE_READY_TIMEOUT_S` (default 600 s) in ``vllm` repo: vllm/envs.py`.

Full annotated manifest (all env vars, all probes, PVC vs ModelCar choice, nodeSelector per SM, RuntimeClass for `nvidia`) in `references/pod-shape.md`.

## Sibling skill boundaries

This skill owns the **pod/container/topology** layer. It does not own:

- **Metrics, alerts, SLO, PromQL, Grafana, OTLP, DCGM pairing** — that is `vllm-observability`. This skill points autoscaling at the metric names; `vllm-observability` owns their semantics and pitfalls.
- **KV cache sizing, LMCache nvme/cpu/gds tiers, offloading backend choice** — that is `vllm-caching`. This skill covers which pod topology supports cross-pod KV transfer; `vllm-caching` covers how to size the tiers.
- **Performance tuning, MoE fused-kernel autotune, TP/EP/DP decision trees, async scheduler, CUDA graph modes** — that is `vllm-performance-tuning`. This skill gets the pod running; that skill makes it fast.
- **Benchmarking methodology, `vllm bench`, request-rate-vs-concurrency semantics, goodput SLO** — that is `vllm-benchmarking`.
- **Env-var and YAML-config semantics, air-gapped HF mirror setup, ModelScope, trust_remote_code** — that is `vllm-configuration`. This skill shows where the env vars go in the pod spec; that one explains what they do.
- **NVIDIA hardware SKU selection, HBM/power/NVLink, Blackwell gotchas per SM** — that is `vllm-nvidia-hardware`.

## Structure of this skill

- **`references/pod-shape.md`** — complete annotated Deployment manifest; env vars catalogue; probes; nodeSelector per SM generation; PVC vs ModelCar trade-off; image tag discipline; `vllm-openai` entrypoint contract.
- **`references/multi-node.md`** — LWS vs KubeRay; `ray symmetric-run`; NCCL on k8s (shm, SR-IOV, RoCE, InfiniBand, `NCCL_SOCKET_IFNAME`/`NCCL_IB_HCA`); the in-repo `multi-node-serving.sh`/`run_cluster.sh`; known issue list.
- **`references/ecosystem.md`** — llm-d, vllm-production-stack, AIBrix, NVIDIA Dynamo, KServe vLLM runtime, vllm-semantic-router, Envoy AI Gateway — what each one is, current version, when to pick.
- **`references/routing.md`** — Gateway API Inference Extension (`InferencePool`, `InferenceModel`, EPP), production-stack router, semantic-router, kgateway/Istio/NGF, OCP Route SSE timeout gotcha.
- **`references/autoscaling.md`** — KEDA on `vllm:num_requests_waiting`, cooldown discipline (`cooldownPeriod: 360`), HPA with custom metrics, scale-to-zero, llm-d WVA.
- **`references/disagg.md`** — cross-pod PD with NixlConnector, Mooncake, LMCache, MORI-IO; Dynamo's relation to vLLM's own connectors; topology recipes.
- **`references/openshift.md`** — RHAIIS, RHOAI ServingRuntime templates, SCC, arbitrary UID, Routes 60 s timeout, NVIDIA GPU Operator on OCP, user-workload monitoring, air-gapped (oc-mirror v2, IDMS, ModelCar).
- **`references/docker-lab.md`** — `docker run` canonical flags, `--shm-size` vs `--ipc=host`, `--gpus`, MIG strings, Podman/podman-compose, rootless friction, 2-node disagg compose template.

## The vLLM in-repo deployment artifacts (cheat sheet)

| Path | What it is |
|---|---|
| `docs/deployment/k8s.md` | Canonical K8s guide |
| `docs/deployment/docker.md` | Canonical Docker run reference |
| `docs/deployment/nginx.md` | Multi-server LB with Nginx |
| `docs/deployment/frameworks/lws.md` | LeaderWorkerSet recipe |
| `docs/deployment/frameworks/helm.md` | Helm chart usage |
| `docs/deployment/frameworks/kserve.md` | KServe runtime |
| `docs/deployment/integrations/{llm-d,production-stack,aibrix,dynamo,kubeRay,kthena,kubeai,kaito,llama-stack,llmaz}.md` | Ecosystem landing pages |
| `examples/online_serving/chart-helm/` | In-tree Helm chart (v0.0.1, experimental) |
| `examples/online_serving/multi-node-serving.sh` | Ray leader/worker bootstrap |
| `examples/online_serving/run_cluster.sh` | Docker-based Ray cluster (`--shm-size 10.24g --ipc=host --gpus all`) |
| `examples/online_serving/disaggregated_serving/` | PD-split proxy demos (XpYd, KV events, Mooncake) |
| `examples/online_serving/disaggregated_prefill.sh` | PD launcher |
| `vllm/envs.py` | Canonical env-var catalogue |
| `vllm/distributed/kv_transfer/` | KV connector implementations (LMCache, Mooncake, MORI-IO, NIXL, P2P-NCCL, HF3FS) |
| `vllm/entrypoints/serve/instrumentator/health.py` | `/health` endpoint (200 healthy, 503 EngineDeadError) |
| `Dockerfile{,.rocm,.cpu,.tpu,.xpu,.nightly_torch,.ppc64le,.s390x}` | Image variants |

All paths relative to vLLM repo root (https://github.com/vllm-project/vllm).

## Operator smoke test — is this pod observable and multi-node-capable?

One-shot smoke test covering all critical checks:

```bash
${CLAUDE_SKILL_DIR}/scripts/deployment-smoke.sh <pod-name> [namespace]
```

The script validates pod health, `/health`, `/v1/models`, `/dev/shm` sizing, `/metrics` surface, NCCL env on multi-GPU pods, usage-stats opt-out, and image-tag discipline. Output is color-coded pass/warn/fail; exits non-zero on critical failure.

Or run ad-hoc:

```bash
kubectl exec -it <pod> -- curl -fsS http://localhost:8000/health
kubectl exec -it <pod> -- curl -fsS http://localhost:8000/v1/models
kubectl exec -it <pod> -- df -h /dev/shm                          # sizeLimit, not 64M default
kubectl exec -it <leader-pod> -- ray status                        # LWS leader
kubectl exec -it <pod> -- env | grep -E '^(NCCL_|GLOO_|VLLM_HOST_IP)'
kubectl exec -it <pod> -- curl -s http://localhost:8000/metrics | grep -c '^vllm:'
```

If any check fails, the corresponding reference file has a diagnostic flow.

## Critical pitfalls (the short list — full treatment in references)

1. **No `/dev/shm` emptyDir.** Silent NCCL segfault on first all-reduce. See `references/pod-shape.md`.
2. **Default liveness probe.** `initialDelaySeconds: 30` vs 8–12 min cold load → pod liveness-kill loop. Fixed at 600 s; tighten only after warm.
3. **`:latest` image tag.** Breaks on every vLLM release. Pin to a version tag and roll forward deliberately.
4. **Root-UID image on OpenShift.** Use RHAIIS images or rebuild. See `references/openshift.md`.
5. **KEDA threshold 1–2 on `num_requests_waiting`.** Thrashing. Use 5–10 per replica and `cooldownPeriod: 360`. See `references/autoscaling.md`.
6. **OCP Route 60 s idle timeout.** Kills long SSE streams. Annotate `haproxy.router.openshift.io/timeout: 10m`.
7. **Missing `NCCL_SOCKET_IFNAME` on multi-NIC hosts.** NCCL picks the wrong interface and hangs on bootstrap. Pin explicitly.
8. **Using the in-tree `chart-helm` (v0.0.1) in production.** It is marked experimental. For production, use vllm-production-stack Helm or llm-d Helm.
9. **Telemetry to `stats.vllm.ai`.** Opt out with `VLLM_NO_USAGE_STATS=1 VLLM_DO_NOT_TRACK=1` — especially in regulated/air-gapped environments.
10. **Assuming Gateway API is GA on every OCP.** It is GA on OCP 4.19+, dev-preview on 4.17. Check the cluster version.

## External references

Canonical entry: https://docs.vllm.ai/en/stable/deployment/ — topic URLs live in the reference files (`references/ecosystem.md`, `references/multi-node.md`, `references/openshift.md`).

Sibling skills: `vllm-observability`, `vllm-caching`, `vllm-performance-tuning`, `vllm-benchmarking`, `vllm-configuration`, `vllm-nvidia-hardware`, `helm`, `openshift-app`.
