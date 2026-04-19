# Pod shape — the minimum viable vLLM Deployment manifest

This is a pointer-map companion to the "Minimum viable pod shape" block in `SKILL.md`. Its job is to explain **why each field is there** and **where the authoritative reference lives**, enabling adaptation to a non-default cluster without cargo-culting.

## The complete annotated template

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm
  labels: {app: vllm}
spec:
  replicas: 1
  strategy:
    type: Recreate          # GPU pods can't overlap on the same node; rolling update will fail on resource pressure
  selector: {matchLabels: {app: vllm}}
  template:
    metadata:
      labels: {app: vllm}
      annotations:
        # Optional: prefer local SSD for model cache
        cluster-autoscaler.kubernetes.io/safe-to-evict: "false"
    spec:
      terminationGracePeriodSeconds: 60   # give in-flight streams a chance to finish
      runtimeClassName: nvidia            # if using nvidia-container-runtime via RuntimeClass
      nodeSelector:
        # Match the SKU; see vllm-nvidia-hardware skill for per-SM guidance
        nvidia.com/gpu.product: NVIDIA-H200         # or NVIDIA-B200, NVIDIA-B300, NVIDIA-H100-80GB-HBM3
      tolerations:
        - {key: nvidia.com/gpu, operator: Exists, effect: NoSchedule}
      containers:
      - name: vllm
        image: vllm/vllm-openai:<pinned-tag>        # NEVER :latest
        imagePullPolicy: IfNotPresent
        command: ["vllm", "serve"]                   # or omit to use image ENTRYPOINT
        args:
          - "$(MODEL)"
          - "--tensor-parallel-size=8"
          - "--served-model-name=$(SERVED_NAME)"
          - "--disable-access-log-for-endpoints=/health,/metrics,/ping"
        env:
          - {name: MODEL,        value: "Qwen/Qwen3-235B-A22B-Instruct"}
          - {name: SERVED_NAME,  value: "qwen3-235b"}
          - {name: VLLM_HOST_IP, valueFrom: {fieldRef: {fieldPath: status.podIP}}}
          - {name: HF_HOME,      value: "/models/.cache"}
          - {name: HUGGING_FACE_HUB_TOKEN, valueFrom: {secretKeyRef: {name: hf-token, key: token, optional: true}}}
          # Telemetry opt-out (especially for air-gapped / regulated)
          - {name: VLLM_NO_USAGE_STATS, value: "1"}
          - {name: VLLM_DO_NOT_TRACK,   value: "1"}
          # Multi-NIC NCCL pinning (see references/multi-node.md)
          # - {name: NCCL_SOCKET_IFNAME, value: "eth0"}
          # - {name: NCCL_IB_HCA,         value: "mlx5_*"}
          # - {name: NCCL_IB_DISABLE,     value: "0"}
        ports:
          - {containerPort: 8000, name: http}
        readinessProbe:
          httpGet: {path: /health, port: http}
          periodSeconds: 5
          failureThreshold: 3
          timeoutSeconds: 2
        livenessProbe:
          httpGet: {path: /health, port: http}
          periodSeconds: 10
          failureThreshold: 3
          initialDelaySeconds: 600              # LOAD-BEARING: matches VLLM_ENGINE_READY_TIMEOUT_S default
          timeoutSeconds: 2
        # startupProbe is the cleaner pattern on k8s 1.20+:
        # startupProbe: {httpGet: {path: /health, port: http}, periodSeconds: 10, failureThreshold: 90}
        resources:
          limits:
            nvidia.com/gpu: "8"
            cpu: "16"
            memory: 256Gi
          requests:
            nvidia.com/gpu: "8"
            cpu: "16"
            memory: 256Gi
        volumeMounts:
          - {name: dshm,   mountPath: /dev/shm}          # LOAD-BEARING
          - {name: models, mountPath: /models}
          - {name: cache,  mountPath: /root/.cache}       # compile cache; avoid repeat JIT on restart
        securityContext:
          allowPrivilegeEscalation: false
          capabilities: {drop: ["ALL"]}
          # NOTE: upstream vllm/vllm-openai image runs as root (UID 0).
          # On OpenShift or restricted-v2 PSA clusters, use RHAIIS or rebuild; see references/openshift.md.
          # runAsNonRoot: true       # enable only with an image that supports it
          # runAsUser: 1000
      volumes:
        - name: dshm
          emptyDir: {medium: Memory, sizeLimit: 10Gi}   # LOAD-BEARING — no k8s `--ipc=host`
        - name: models
          persistentVolumeClaim: {claimName: vllm-model-cache}
        - name: cache
          emptyDir: {sizeLimit: 20Gi}
---
apiVersion: v1
kind: Service
metadata: {name: vllm}
spec:
  type: ClusterIP
  ports: [{port: 8000, targetPort: http, name: http}]
  selector: {app: vllm}
```

## Why each load-bearing field is there

### `/dev/shm` emptyDir (LOAD-BEARING)

Kubernetes has no equivalent of Docker's `--ipc=host`. The in-cluster default `/dev/shm` is a tmpfs of 64 MiB (OpenShift's SCC enforces even smaller on some profiles). `torch.distributed` uses shared memory for the bootstrap + IPC; any TP>1 pod without a real-sized `/dev/shm` will segfault on the first all-reduce. The vLLM docs call this out directly at:

- ``vllm` repo: docs/deployment/k8s.md:209,289`
- ``vllm` repo: docs/getting_started/installation/gpu.cuda.inc.md:207,212,251,263,271-272`
- ``vllm` repo: docs/deployment/nginx.md:95,105`

Size at 2–10 GiB. Backed by host memory (`medium: Memory`), capped at `sizeLimit` so a runaway process can't OOM the node.

### `VLLM_HOST_IP` via `status.podIP` (LOAD-BEARING on multi-node)

On multi-NIC pods, vLLM may auto-select the wrong interface for the engine-core process's gRPC bind. Feeding `status.podIP` guarantees the pod's primary CNI IP. Source: ``vllm` repo: vllm/envs.py:15`. This interacts with `NCCL_SOCKET_IFNAME` — see `references/multi-node.md`.

### Liveness `initialDelaySeconds: 600` (LOAD-BEARING)

Cold model load for large models (405B FP8, DeepSeek-V3, Qwen3-235B) takes 8–12 minutes:

- PVC-backed weights with default storage-class IOPS: 6–15 min
- First run: FlashInfer / DeepGEMM JIT compile (1–3 min), CUDA graph warmup (30–120 s)
- TP>1 NCCL bootstrap (10–30 s)

The default k8s liveness `initialDelaySeconds: 0` + `periodSeconds: 10` + `failureThreshold: 3` kills the pod at 30 s. It never becomes ready. The vLLM env `VLLM_ENGINE_READY_TIMEOUT_S` defaults to 600 s for exactly this reason. Match it.

Cleaner alternative: use `startupProbe` (k8s 1.20+) with `failureThreshold: 90, periodSeconds: 10` (15 min budget), and leave `livenessProbe` at normal settings once it's past startup.

### `--disable-access-log-for-endpoints=/health,/metrics,/ping`

Probes hit `/health` every 5–10 s, Prometheus hits `/metrics` every 15–30 s. Left enabled, the stdout log is 99% probe noise and the real signal drowns. Added in vLLM PR #30011 (`6ee7f18f3` in git log). See `examples/online_serving/chart-helm/values.yaml` for the default list.

### `strategy: Recreate`

GPU pods bind the GPU exclusively. A `RollingUpdate` tries to stand up the new replica before tearing down the old, which either fails on resource pressure or accidentally occupies 2× GPU budget during roll. Use `Recreate` unless spare capacity exists and the overlap is intentional.

### Telemetry opt-out

By default vLLM POSTs anonymous usage stats to `https://stats.vllm.ai` on first start. In regulated / air-gapped clusters this fails visibly (confuses operators) or leaks metadata. Both `VLLM_NO_USAGE_STATS=1` and `VLLM_DO_NOT_TRACK=1` are honoured. Source: ``vllm` repo: vllm/envs.py:35-37`.

## The env-var surface worth tuning

| Var | Default | When to change |
|---|---|---|
| `VLLM_HOST_IP` | auto | Always on multi-node; feed from `status.podIP` |
| `VLLM_PORT` | 8000 | Only on collision with istio-sidecar (15001, 15006) |
| `VLLM_NO_USAGE_STATS` | unset | Always in regulated/air-gapped |
| `VLLM_DO_NOT_TRACK` | unset | Belt-and-braces with `VLLM_NO_USAGE_STATS` |
| `VLLM_ENGINE_READY_TIMEOUT_S` | 600 | Raise if cold load > 10 min (405B FP8 from slow PVC) |
| `VLLM_RPC_TIMEOUT` | 10000 ms | Raise on very slow first-token with heavy structured-output setup |
| `VLLM_NCCL_SO_PATH` | auto | Only for custom NCCL builds |
| `VLLM_USE_RAY_COMPILED_DAG_CHANNEL_TYPE` | `auto` | `nccl` on IB clusters, `shm` on single-node multi-GPU |
| `HF_HOME` | `~/.cache/huggingface` | Point at PVC mount for pre-warmed cache |
| `HF_HUB_OFFLINE` | unset | Set `1` in air-gapped; see `vllm-configuration` skill |
| `HF_ENDPOINT` | HuggingFace | Internal mirror URL in air-gapped |
| `NCCL_SOCKET_IFNAME` | auto | Multi-NIC pods; see `references/multi-node.md` |

Full env-var surface: ``vllm` repo: vllm/envs.py`. Ensure `vllm-configuration` skill is consulted for anything deeper than runtime wiring.

## nodeSelector matrix (per GPU SKU)

The NVIDIA GPU Operator labels every node with `nvidia.com/gpu.product`. Pin pods explicitly so a B200 model doesn't schedule onto an H100:

| GPU | Label |
|---|---|
| H100 80 GB SXM | `NVIDIA-H100-80GB-HBM3` |
| H100 NVL | `NVIDIA-H100-NVL` |
| H200 141 GB | `NVIDIA-H200` |
| B200 180 GB | `NVIDIA-B200` |
| B300 270 GB (HGX) | `NVIDIA-B300` |
| B300 288 GB (DGX/Superchip) | `NVIDIA-B300-HBM3E` (check the cluster's label discovery) |
| GB200 NVL72 Grace+Blackwell | `NVIDIA-GB200` |
| MI300X 192 GB | `AMD-MI300X` |

See `vllm-nvidia-hardware` skill for the B300 SKU split (the HGX 270 GB vs DGX/Superchip 288 GB trap).

## Model weights: PVC vs ModelCar vs in-image

Three patterns:

1. **PVC**: cluster-wide `ReadOnlyMany` PVC populated by a one-shot download Job. Pro: model lives once in the cluster, pods start fast (with prefetch). Con: storage-class IOPS dominates cold-start. Needs RWX storage (NFS, CephFS, ODF).
2. **ModelCar** (Red Hat pattern): model weights shipped as an OCI image; k8s pulls it like any container; weights appear at `/mnt/models`. Pro: same distribution mechanism as the runtime image, signable and attestable. Con: image registry bandwidth. Canonical docs: https://redhat-ai-services.github.io/vllm-showroom/modules/deployment/modelcar/01c-deploy-modelcar.html
3. **In-image**: bake weights into the `vllm/vllm-openai` image. Only viable for small models or tightly-controlled fleets — large images have their own ops headaches.

Air-gapped clusters tend to prefer ModelCar (single distribution path) or PVC populated via `oc-mirror v2` and a pre-seeded registry.

## Startup probe (recommended over long initialDelay)

```yaml
startupProbe:
  httpGet: {path: /health, port: http}
  periodSeconds: 10
  failureThreshold: 90         # 90 * 10 = 15 min budget
livenessProbe:
  httpGet: {path: /health, port: http}
  periodSeconds: 10
  failureThreshold: 3          # once started, quick to catch hangs
readinessProbe:
  httpGet: {path: /health, port: http}
  periodSeconds: 5
  failureThreshold: 3
```

Cleaner than `initialDelaySeconds: 600`. Available since k8s 1.20, stable since 1.20.

## Endpoints the probes see

| Endpoint | Returns | Source |
|---|---|---|
| `/health` | 200 healthy, 503 `EngineDeadError` | `vllm/entrypoints/serve/instrumentator/health.py:22-34` |
| `/v1/models` | Lists served model names | OpenAI-compatible router |
| `/metrics` | Prometheus text (see `vllm-observability` skill) | ditto |
| `/ping` | Alias for `/health` |   |
| `/version` | Build metadata |   |

Don't probe `/v1/models` — it is a router endpoint that requires the engine fully up and tokenizer loaded; `/health` reports the engine state more directly and earlier.

## Image tag discipline

- Never `:latest` — every vLLM release is a breaking change in some dimension.
- Use the SemVer tag (`v0.13.0`) and bump deliberately.
- Pin by digest (`@sha256:...`) for reproducibility + image-signature gate (cosign verify).
- RHAIIS tags are independently versioned; `rhaiis/vllm-cuda-rhel9:3.3.0` corresponds to upstream `v0.13.0`.

## Gotchas not yet covered

- **Istio sidecar + streaming**: the Envoy sidecar buffers SSE by default; streaming replies show up all-at-once. Either disable sidecar on the vLLM pod, or set `proxy.istio.io/config: { ... holdApplicationUntilProxyStarts: true }` and ensure streaming is not buffered.
- **Pod Security Admission**: the upstream image cannot satisfy `restricted-v2` or `nonroot-v2`. Either run under `baseline` profile, use RHAIIS, or rebuild.
- **Termination grace period**: streaming requests need time to finish. 60–120 s is reasonable; shorter truncates user responses.
- **CPU requests**: 16+ is sane for TP=8. Low CPU requests starve the Python engine and show up as mystery TPOT spikes under high concurrency.

## Next

- Multi-node (TP across pods): `references/multi-node.md`
- Autoscaling: `references/autoscaling.md`
- OpenShift-specific adaptations: `references/openshift.md`
- Docker/Podman single-node: `references/docker-lab.md`
