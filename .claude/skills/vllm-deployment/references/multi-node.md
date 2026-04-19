# Multi-node — TP/PP across pods on Kubernetes

Single-node TP is covered by the base pod-shape manifest. This reference is for the case where one model doesn't fit on one host: TP spanning two or more nodes, or PP spanning nodes.

## The canonical recipe (April 2026)

**LeaderWorkerSet (LWS) + Ray, driven by vLLM's `multi-node-serving.sh`.**

The "pure headless Service + `parallel-config` + manual rank enumeration" path exists but is not the vLLM-endorsed recipe. LWS is the K8s-native gang-scheduling primitive; Ray is the transport vLLM uses across nodes.

- **LWS project**: https://github.com/kubernetes-sigs/lws — https://lws.sigs.k8s.io/docs/
- **LWS vLLM example (upstream LWS)**: https://github.com/kubernetes-sigs/lws/tree/main/docs/examples/vllm
- **vLLM doc**: https://docs.vllm.ai/en/latest/deployment/frameworks/lws/
- **In-repo bootstrap script**: ``vllm` repo: examples/online_serving/multi-node-serving.sh`
- **Docker-based Ray cluster helper**: ``vllm` repo: examples/online_serving/run_cluster.sh` (reference for what `--shm-size 10.24g --ipc=host --gpus all` should look like)

LWS status as of April 2026: **v0.8.0**, still **pre-GA**. Used in production by llm-d, vllm-production-stack, AIBrix. No v1.0 cut yet — watch [releases](https://github.com/kubernetes-sigs/lws/releases). Pre-1.0 API, but the core `LeaderWorkerSet` CRD has been stable since v0.3.

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
          command: ["bash", "/vllm-workspace/examples/online_serving/multi-node-serving.sh"]
          args: ["leader"]
          env:
            - {name: LWS_LEADER_ADDRESS, valueFrom: {fieldRef: {fieldPath: metadata.annotations['leaderworkerset.sigs.k8s.io/leader-address']}}}
            - {name: VLLM_HOST_IP,       valueFrom: {fieldRef: {fieldPath: status.podIP}}}
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
          command: ["bash", "/vllm-workspace/examples/online_serving/multi-node-serving.sh"]
          args: ["worker"]
          env:
            - {name: LWS_LEADER_ADDRESS, valueFrom: {fieldRef: {fieldPath: metadata.annotations['leaderworkerset.sigs.k8s.io/leader-address']}}}
            - {name: VLLM_HOST_IP,       valueFrom: {fieldRef: {fieldPath: status.podIP}}}
          resources: {limits: {nvidia.com/gpu: "8"}}
          volumeMounts: [{name: dshm, mountPath: /dev/shm}, {name: models, mountPath: /models}]
        volumes:
          - {name: dshm,   emptyDir: {medium: Memory, sizeLimit: 10Gi}}
          - {name: models, persistentVolumeClaim: {claimName: vllm-model-cache}}
```

The leader pod runs `vllm serve` after Ray bootstrap. Workers run Ray only. Expose the leader's port 8000 via a Service (`leaderworkerset.sigs.k8s.io/role: leader` selector).

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

1. **NVIDIA Network Operator** — installs Mellanox OFED drivers, SR-IOV device plugin, Multus CNI. https://docs.nvidia.com/networking/display/kubernetes
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
# Leader pod: Ray sees all workers
kubectl exec -it <leader> -- ray status
# expect num_cpus, num_gpus, num_nodes matching the group size

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
