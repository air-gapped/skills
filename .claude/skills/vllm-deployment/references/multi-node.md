# Multi-node — TP/PP across pods on Kubernetes

Single-node TP is covered by the base pod-shape manifest. This reference is for the case where one model doesn't fit on one host: TP spanning two or more nodes, or PP spanning nodes.

## Table of Contents

- [The canonical recipe](#the-canonical-recipe)
- [Ray symmetric-run (November 2025 change)](#ray-symmetric-run-november-2025-change)
- [LWS minimum viable manifest](#lws-minimum-viable-manifest)
- [NCCL on Kubernetes — the short list of load-bearing gotchas](#nccl-on-kubernetes--the-short-list-of-load-bearing-gotchas)
- [Known load-bearing GitHub issues](#known-load-bearing-github-issues)
- [RDMA / InfiniBand / RoCE on k8s](#rdma--infiniband--roce-on-k8s)
- [KubeRay as an alternative](#kuberay-as-an-alternative)
- [Pipeline parallelism (PP) vs tensor parallelism (TP) across pods](#pipeline-parallelism-pp-vs-tensor-parallelism-tp-across-pods)
- [Smoke test — did multi-node come up?](#smoke-test--did-multi-node-come-up)
- [Next](#next)

---

## The canonical recipe

**LeaderWorkerSet (LWS), every pod running `vllm serve` with `--nnodes` / `--node-rank` / `--master-addr`** (multiprocessing — upstream's default from v0.24.0, #39400).

Ray on LWS is the alternative, for when `--distributed-executor-backend ray` is wanted. A hand-built headless Service + StatefulSet with manual rank enumeration is not the vLLM-endorsed recipe. LWS injects `LWS_GROUP_SIZE`, `LWS_WORKER_INDEX` and `LWS_LEADER_ADDRESS` into every pod — do not define them.

- **LWS project**: https://github.com/kubernetes-sigs/lws — https://lws.sigs.k8s.io/docs/
- **LWS vLLM example (upstream LWS)**: https://github.com/kubernetes-sigs/lws/tree/main/docs/examples
- **vLLM doc**: https://docs.vllm.ai/en/latest/deployment/frameworks/lws/
- **In-repo Ray bootstrap script**: ``vllm` repo: examples/ray_serving/multi-node-serving.sh`
  — **moved from `examples/online_serving/` at some point before v0.25.1.** The
  old path 404s. Because this path is embedded in the container `command:` of
  LWS manifests, a stale copy does not fail at apply time — it fails when the
  pod starts, as a missing-file error from `bash`. Upstream's own
  `docs/deployment/frameworks/lws.md` uses the new path; match it.
- **Docker-based Ray cluster helper**: ``vllm` repo: examples/ray_serving/run_cluster.sh` (reference for what `--network host --shm-size 10.24g --gpus all` should look like)

LWS status: **v1.0.0** (2026-10-16) — GA; used by llm-d, vllm-production-stack, AIBrix. Upgrading to v1.0.0: a DisaggregatedSet created on v0.9.x must complete one template rollout on v0.10.x/v0.11.x first (v1.0.0 drops slice-less LWS support), and DisaggregatedSet roles without a `rollingUpdateConfiguration` now default to `maxSurge: 0, maxUnavailable: 1`. For crash-looping multi-node groups set `leaderWorkerTemplate.maxGroupRestarts` and `restartBackoff` (v1.0.0) so a bad model config stops recreating the group.

## Ray symmetric-run (November 2025 change)

The Ray launch pattern changed in late 2025. The old head/worker split (`ray start --head` on leader, `ray start --address=` on workers) is still supported but the new **symmetric-run** pattern is the vLLM-endorsed path:

- **Blog post**: https://blog.vllm.ai/2025/11/22/ray-symmetric-run.html
- Every pod runs the same command; Ray self-elects the head.
- Simpler LWS template (no leader/worker command divergence).
- Mitigates several known Ray-on-k8s bootstrap races.

For teams with a working head/worker template from early 2025: migrate to symmetric-run when convenient. Both patterns produce an identical cluster from vLLM's perspective.

## LWS minimum viable manifest

```yaml
apiVersion: leaderworkerset.x-k8s.io/v1
kind: LeaderWorkerSet
metadata: {name: vllm-multinode}
spec:
  replicas: 1                                   # 1 LWS replica = 1 vLLM instance
  leaderWorkerTemplate:
    size: 2                                     # 2 pods total (leader + 1 worker)
    restartPolicy: RecreateGroupOnPodRestart    # if any pod dies, rebuild the whole group
    leaderTemplate:
      spec:
        containers:
        - name: vllm
          image: vllm/vllm-openai:<pinned-tag>
          command: ["sh", "-c"]
          args:
            - >-
              vllm serve <model> --port 8000 --tensor-parallel-size 8
              --pipeline-parallel-size $(LWS_GROUP_SIZE) --nnodes $(LWS_GROUP_SIZE)
              --node-rank $(LWS_WORKER_INDEX) --master-addr $(LWS_LEADER_ADDRESS)
          env:
            - {name: VLLM_HOST_IP, valueFrom: {fieldRef: {fieldPath: status.podIP}}}
            # + all the usual pod-shape envs from references/pod-shape.md
          ports: [{containerPort: 8000, name: http}]
          resources: {limits: {nvidia.com/gpu: "8"}}
          volumeMounts: [{name: dshm, mountPath: /dev/shm}, {name: models, mountPath: /models}]
        volumes:
          - {name: dshm,   emptyDir: {medium: Memory, sizeLimit: 10Gi}}
          - {name: models, persistentVolumeClaim: {claimName: vllm-model-cache}}
    workerTemplate:
      spec:
        containers:
        - name: vllm
          image: vllm/vllm-openai:<pinned-tag>
          command: ["sh", "-c"]
          args:
            - >-
              vllm serve <model> --tensor-parallel-size 8
              --pipeline-parallel-size $(LWS_GROUP_SIZE) --nnodes $(LWS_GROUP_SIZE)
              --node-rank $(LWS_WORKER_INDEX) --master-addr $(LWS_LEADER_ADDRESS) --headless
          env:
            - {name: VLLM_HOST_IP, valueFrom: {fieldRef: {fieldPath: status.podIP}}}
          resources: {limits: {nvidia.com/gpu: "8"}}
          volumeMounts: [{name: dshm, mountPath: /dev/shm}, {name: models, mountPath: /models}]
        volumes:
          - {name: dshm,   emptyDir: {medium: Memory, sizeLimit: 10Gi}}
          - {name: models, persistentVolumeClaim: {claimName: vllm-model-cache}}
```

Every pod runs `vllm serve`; only the leader serves HTTP (workers are `--headless`). Expose the leader's port 8000 via a Service (`leaderworkerset.sigs.k8s.io/role: leader` selector).

**Ray alternative** — swap the two shell commands:

- leader: `bash /vllm-workspace/examples/ray_serving/multi-node-serving.sh leader --ray_cluster_size=$(LWS_GROUP_SIZE); vllm serve <model> --port 8000 --tensor-parallel-size 8 --pipeline-parallel-size 2 --distributed-executor-backend ray`
- worker: `bash /vllm-workspace/examples/ray_serving/multi-node-serving.sh worker --ray_address=$(LWS_LEADER_ADDRESS)`

The script exits 1 without `--ray_cluster_size` (leader) or `--ray_address` (worker), and it only forms the Ray cluster — the leader command must start `vllm serve` itself.

## NCCL on Kubernetes — the short list of load-bearing gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Segfault on first all-reduce (TP>1 pod) | `/dev/shm` too small | `emptyDir: {medium: Memory, sizeLimit: 10Gi}` at `/dev/shm` |
| NCCL bootstrap hangs forever | Wrong interface auto-selected | `NCCL_SOCKET_IFNAME=eth0` (pick the CNI iface) |
| IB cards ignored on SR-IOV node | NCCL defaults to TCP | `NCCL_IB_DISABLE=0 NCCL_IB_HCA=mlx5_*` |
| Cross-pod NCCL stalls 30 s then dies | Hostname resolution | Use full `.<svc>.<ns>.svc.cluster.local`; LWS creates the headless Service automatically |
| ERROR: "WARN Bootstrap : no socket interface found" | No usable iface | Pin `NCCL_SOCKET_IFNAME` or fix CNI |
| First TP=16 run crashes, next one works | FlashInfer / DeepGEMM JIT cache cold | Mount an `emptyDir` at `/root/.cache` so subsequent runs are warm |

**Pin `VLLM_HOST_IP`** on every pod from `status.podIP`. NCCL derives its rank bootstrap address from it when Ray's env is delayed.

## Known load-bearing GitHub issues

- https://github.com/vllm-project/vllm/issues/7466 — NCCL errors multi-GPU K8s (P2P between pods)
- https://github.com/vllm-project/vllm/issues/18831 — `/dev/shm` NCCL shared-memory segment attach fail (the emptyDir fix)
- https://github.com/vllm-project/vllm/issues/4618 — `DistBackendError` NCCL
- https://github.com/vllm-project/vllm/issues/27321 — TP>1 NCCL hang
- https://github.com/vllm-project/vllm/issues/8074 — multi-node on k8s feature tracker
- https://discuss.vllm.ai/t/deploying-multi-node-llm-with-infiband-roce/1344 — SR-IOV via NVIDIA Network Operator, `NCCL_IB_HCA=mlx5`, `NCCL_IB_DISABLE=0`

Dynamo + vLLM + NIXL specifically:
- https://github.com/ai-dynamo/dynamo/issues/3724 — multi-node vLLM `NIXL_ERR_BACKEND`
- https://github.com/ai-dynamo/dynamo/issues/331 — multi-node spec-dec crash

## RDMA / InfiniBand / RoCE on k8s

Three ingredients:

1. **NVIDIA Network Operator** — installs Mellanox OFED drivers, SR-IOV device plugin, Multus CNI. https://docs.nvidia.com/networking/software/cloud-orchestration/index.html
2. **Secondary network via Multus** — annotate the pod with `k8s.v1.cni.cncf.io/networks` pointing at a `NetworkAttachmentDefinition` for the RDMA/SR-IOV fabric.
3. **NCCL env on pods**: `NCCL_IB_HCA=mlx5_*`, `NCCL_IB_DISABLE=0`, `NCCL_IB_GID_INDEX=3` (RoCE v2), `NCCL_SOCKET_IFNAME=<CNI-iface>`.

On AKS/EKS/GKE with managed GPU pools, the operator is preinstalled and `nvidia.com/rdma_ib_roce_gdr` is a resource request. On bare-metal, do all three.

## KubeRay as an alternative

KubeRay (Ray's own k8s operator) is an alternative to LWS. vllm-production-stack has a dedicated recipe:

- https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/pipeline-parallelism-kuberay.html
- https://github.com/ray-project/kuberay

When to pick KubeRay over LWS:
- Already running Ray for data-pipeline work; want a single operator.
- Need Ray Serve's autoscaler and multi-model routing.
- Multi-tenant Ray cluster shared across vLLM + training + batch.

When to stick with LWS:
- Only vLLM, no other Ray workloads.
- Simpler operational surface (LWS is ~1 CRD, KubeRay is several).
- Disagg P/D with llm-d (which natively uses LWS).

## Pipeline parallelism (PP) vs tensor parallelism (TP) across pods

| Axis | Latency cost | Bandwidth requirement | K8s suitability |
|---|---|---|---|
| TP | High (all-reduce every layer) | 100+ GB/s (NVLink domain) | Only within-NVLink-domain pods (one pod, one node, NVSwitch fabric); **NOT across pods** |
| PP | Lower (pipeline bubble) | ~1–10 GB/s (IB/RoCE is fine) | Works across pods/nodes over IB/RoCE |

Practical rule: **use TP within a node, PP across nodes**. A 2-node deployment of a 405B model is typically `TP=8 PP=2` (8 GPUs per node × 2 stages). Don't try to TP across an IB fabric — the all-reduce bandwidth demand will starve.

Exception: NVLink Switch System (NVL72) nodes provide a single NVLink domain across 72 GPUs. There, `TP=16` or higher across pods-on-the-same-NVL-node is viable. This is a Grace-Blackwell-rack-level property, see `vllm-nvidia-hardware` skill.

## Smoke test — did multi-node come up?

```bash
# Multiprocessing: every pod loaded its stage
kubectl logs <leader> | grep -i "Model loading"
kubectl logs <worker> | grep -i "Model loading"

# Ray path only: leader sees all workers (num_nodes = group size)
kubectl exec -it <leader> -- ray status

# NCCL env resolved on every pod
kubectl exec -it <pod> -- env | grep -E '^(NCCL_|VLLM_HOST_IP|GLOO_)'

# Engine responds
kubectl exec -it <leader> -- curl -fsS http://localhost:8000/health

# Model ready for request
kubectl exec -it <leader> -- curl -fsS http://localhost:8000/v1/models
```

## Next

- Single-pod baseline: `references/pod-shape.md`
- Cross-pod KV transfer (disagg): `references/disagg.md`
- Autoscaling a multi-node group: `references/autoscaling.md` (§LWS + KEDA)
