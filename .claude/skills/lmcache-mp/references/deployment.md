# LMCache MP — deployment recipes

## Docker

### Server only

```bash
docker run --runtime nvidia --gpus all \
    --network host --ipc host \
    lmcache/standalone:nightly \
    /opt/venv/bin/lmcache server \
    --l1-size-gb 60 --eviction-policy LRU --max-workers 4 --port 6555
```

Expected log line:

```
LMCache INFO: LMCache cache server is running...
```

Default ZMQ port: **5555**. Default HTTP frontend port (when using `lmcache server` rather than `python3 -m lmcache.v1.multiprocess.server`): **8080**.

### vLLM client

```bash
docker run --runtime nvidia --gpus all \
    --network host --ipc host \
    lmcache/vllm-openai:latest-nightly \
    Qwen/Qwen3-14B \
    --no-enable-prefix-caching \
    --disable-hybrid-kv-cache-manager \
    --kv-transfer-config '{"kv_connector":"LMCacheMPConnector",
                           "kv_role":"kv_both",
                           "kv_connector_extra_config":{"lmcache.mp.port":6555}}'
```

vLLM-side success line:

```
LMCache INFO: Registering kv caches!
```

LMCache-side success line:

```
LMCache INFO: Registered KV cache for GPU ID <pid> with 40 layers
```

### Remote LMCache server

If LMCache is on a different host than vLLM (NUMA-isolated, dedicated cache box, etc.), pass both host and port via `kv_connector_extra_config`:

```json
{"kv_connector":"LMCacheMPConnector",
 "kv_role":"kv_both",
 "kv_connector_extra_config":{"lmcache.mp.host":"10.0.0.1","lmcache.mp.port":6555}}
```

## Kubernetes — DaemonSet + Deployment pattern

This is the canonical production shape. One LMCache server **per node** (DaemonSet), shared by N vLLM pods on that node (Deployment).

### LMCache DaemonSet

Adapted from `LMCache/LMCache/examples/multi_process/lmcache-daemonset.yaml`:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: lmcache-server
  namespace: multi-process
spec:
  selector:
    matchLabels:
      app: lmcache-server
  template:
    metadata:
      labels:
        app: lmcache-server
    spec:
      hostNetwork: true            # vLLM pods discover via status.hostIP
      nodeSelector:
        nvidia.com/gpu.present: "true"   # don't schedule on CPU-only nodes
      volumes:
        - name: dev-shm
          hostPath: { path: /dev/shm, type: Directory }
      containers:
        - name: lmcache-server
          image: lmcache/standalone:nightly
          command:
            - /opt/venv/bin/python3
            - -m
            - lmcache.v1.multiprocess.server
            - --host
            - "0.0.0.0"
            - --port
            - "6555"
            - --l1-size-gb
            - "60"
            - --eviction-policy
            - LRU
            - --max-workers
            - "4"
          volumeMounts:
            - { name: dev-shm, mountPath: /dev/shm }
          resources:
            requests:
              memory: "65Gi"        # l1-size-gb + ~5GB Python/server overhead
              cpu: "4"
            limits:
              memory: "120Gi"
              cpu: "8"
          env:
            - { name: LMCACHE_LOG_LEVEL, value: "DEBUG" }
```

### vLLM Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-deployment
  namespace: multi-process
spec:
  replicas: 1
  selector: { matchLabels: { app: vllm-deployment } }
  template:
    metadata: { labels: { app: vllm-deployment } }
    spec:
      volumes:
        - name: dshm
          hostPath: { path: /dev/shm, type: Directory }
      containers:
        - name: vllm
          image: lmcache/vllm-openai:latest-nightly
          volumeMounts:
            - { name: dshm, mountPath: /dev/shm }
          command:
            - /bin/bash
            - -c
            - |
              vllm serve Qwen/Qwen3-14B \
                --host 0.0.0.0 --port 8000 \
                --no-enable-prefix-caching \
                --disable-hybrid-kv-cache-manager \
                --max-model-len 32768 \
                --gpu-memory-utilization 0.85 \
                --tensor-parallel-size 4 \
                --kv-transfer-config "{\"kv_connector\":\"LMCacheMPConnector\", \"kv_role\":\"kv_both\", \"kv_connector_extra_config\": {\"lmcache.mp.host\": \"tcp://${HOST_IP}\", \"lmcache.mp.port\": 6555}}"
          env:
            - name: HOST_IP
              valueFrom: { fieldRef: { fieldPath: status.hostIP } }
            - { name: PYTHONHASHSEED, value: "0" }
            - { name: PROMETHEUS_MULTIPROC_DIR, value: "/tmp" }
          resources:
            requests: { nvidia.com/gpu: "4" }
            limits:   { nvidia.com/gpu: "4" }
          startupProbe:
            failureThreshold: 60
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 30
            periodSeconds: 10
```

### Why each piece matters

- **`hostNetwork: true` on the DaemonSet** — vLLM pods reach LMCache via `status.hostIP` (host's IP). Without `hostNetwork`, the LMCache port isn't exposed on the host's IP and sibling pods can't reach it.
- **`/dev/shm` mounted from host on both** — CUDA IPC shared-memory transfers require both ends to share the same `/dev/shm` namespace.
- **GPU NOT requested in DaemonSet** — LMCache server doesn't run inference. The NVIDIA container runtime grants the implicit access needed for IPC. Requesting GPUs there steals them from the vLLM pods.
- **`PYTHONHASHSEED=0` on vLLM** — makes prefix hash computation deterministic across pod restarts so cached prefixes survive.
- **`PROMETHEUS_MULTIPROC_DIR=/tmp`** — required for vLLM's multi-process Prometheus metrics.

### Health check via HTTP server variant

If you use `lmcache server` (not `python3 -m lmcache.v1.multiprocess.server`), you also get a FastAPI HTTP frontend on port 8080 with `/api/healthcheck`. Wire it into K8s probes:

```yaml
livenessProbe:
  httpGet: { path: /api/healthcheck, port: 8080 }
  initialDelaySeconds: 10
  periodSeconds: 30
readinessProbe:
  httpGet: { path: /api/healthcheck, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 10
```

Note the LMCache DaemonSet example uses the legacy `python3 -m lmcache.v1.multiprocess.server` entrypoint (no HTTP frontend). Switch to `lmcache server` to get health checks. The MP docs explicitly call this out: "Recommended. ZMQ + FastAPI HTTP frontend (adds /api/healthcheck for K8s probes…)".

### Monitoring

Prometheus scraping on port 9090 by default. Add a `ServiceMonitor` or pod scrape annotation against the DaemonSet pods. Metrics surface includes L1 cache hits/misses, eviction rates, L2 throughput (added in PR #3098, 2026-04-25), and KV-format / GPU registration events.

## Production tuning checklist

- **`--l1-size-gb`**: aim for 60–80% of free node memory after vLLM weight + activations + OS. Bigger L1 = fewer L2 round-trips.
- **`--max-workers`**: at least the number of vLLM instances sharing the cache server, so each instance has its own GPU thread. Override the GPU pool independently with `--max-gpu-workers`; CPU pool with `--max-cpu-workers`.
- **`--eviction-trigger-watermark` / `--eviction-ratio`**: lower watermark or higher ratio if you observe stutter under sustained load.
- **`LMCACHE_LOG_LEVEL=DEBUG`** during initial setup to verify L2 store/load activity. Switch to `INFO` for production.

## Cleanup

```bash
kubectl delete -f vllm-deployment.yaml
kubectl delete -f lmcache-daemonset.yaml
kubectl delete namespace multi-process
```
