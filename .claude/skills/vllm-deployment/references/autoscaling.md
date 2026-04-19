# Autoscaling — KEDA, HPA, and llm-d WVA

GPU pods are expensive and slow to start. Autoscaling a vLLM fleet is more about **cooldown discipline** than reactive scaling — scale signals that are too sensitive cause thrashing, and pods that take 10 minutes to cold-start punish reactive scaling anyway.

## The signal to scale on

**`vllm:num_requests_waiting`** is the canonical GPU-backpressure metric. It measures requests queued in the vLLM scheduler — not CPU or memory, which for LLM inference do not correlate with load.

- Exported at `/metrics` — see `vllm-observability` skill for the metric catalogue.
- Units: integer count of queued requests per engine.
- Labels: `{model_name, engine}`.

Secondary signals:

| Metric | When to use |
|---|---|
| `vllm:kv_cache_usage_perc` | Pre-emption risk (scale out before it hits 0.95) |
| `vllm:time_to_first_token_seconds` (P99) | SLO-driven scaling |
| `vllm:num_requests_running` | Current active batch — informational |

## KEDA — the recommended autoscaler

KEDA treats GPU pods as first-class. It scales based on external metrics (Prometheus, custom), supports scale-to-zero, and provides `cooldownPeriod` for slow-start workloads.

- **Site**: https://keda.sh/
- **Prometheus scaler**: https://keda.sh/docs/latest/scalers/prometheus/

### Canonical ScaledObject

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: {name: vllm}
spec:
  scaleTargetRef: {name: vllm, kind: Deployment}
  minReplicaCount: 1                    # raise to 2+ when cold-start windows are unacceptable
  maxReplicaCount: 8
  cooldownPeriod: 360                   # LOAD-BEARING — 6 min. GPU pods take ~10 min to become ready; reactive scaling fails
  pollingInterval: 30
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        metricName: vllm_waiting
        threshold: "5"                   # waiting requests per replica — 5–10 is the sane band
        query: |
          sum(vllm:num_requests_waiting{model_name="qwen3-235b"})
```

### The thresholds that matter

| Threshold | Behavior |
|---|---|
| 1–2 | **Thrash city.** Every short burst triggers a scale. Pods cold-start, the burst ends, they scale down, the next burst retriggers. Avoid. |
| 5–10 per replica | Production Stack default is 5. OpenShift AI example is 2 (also on the edge of thrashing). **Pick 5 or higher.** |
| 20+ | Too conservative; SLO suffers during scale-up window. |

### `cooldownPeriod` discipline

GPU pods take 8–12 minutes to become ready (PVC pull + JIT + CUDA graphs). A reactive scaler with `cooldownPeriod: 60` will:

1. See queue high → add pod.
2. Queue starts dropping (existing pods absorb it).
3. New pod still 8 min from ready.
4. Scaler sees queue OK → kills the still-starting pod.
5. Queue spikes again → starts another 8-min cold start.

**Set `cooldownPeriod: 360` or higher.** Let scale-up commit to its decision long enough for the new pod to actually arrive.

### Scale-to-zero caveats

- Cold-start = 8–12 min. Traffic with > 12-min gaps benefits from scale-to-zero.
- Interactive / always-on workloads: **do not scale to zero.** Keep `minReplicaCount: 1`.
- Batch / evening jobs: scale-to-zero is fine.

## HPA with custom metrics (alternative)

When KEDA is unavailable, HPA via Prometheus Adapter works. More setup:

1. Deploy Prometheus Adapter with a rule mapping `vllm:num_requests_waiting` to a K8s custom metric.
2. HPA references the custom metric.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: vllm}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: vllm}
  minReplicas: 1
  maxReplicas: 8
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 360       # same cooldown discipline as KEDA
  metrics:
    - type: Pods
      pods:
        metric: {name: vllm_num_requests_waiting}
        target: {type: AverageValue, averageValue: "5"}
```

**Prefer KEDA** unless there is org-wide standardization on HPA. KEDA's cooldown semantics and scale-to-zero are worth the extra operator.

## llm-d Workload Variance Autoscaler (WVA)

llm-d v0.3 introduced WVA — inference-specific autoscaling that replaces generic HPA/KEDA:

- **Announcement**: https://llm-d.ai/blog/llm-d-v0.3-expanded-hardware-faster-perf-and-igw-ga
- Aware of disagg topology (scales prefill and decode pools independently).
- SLA-driven (scale on P99 TTFT SLO rather than queue depth).
- Scale-to-zero native, with pre-warming.

On llm-d, use WVA. Otherwise stick with KEDA.

## KServe / OpenShift AI autoscaling

KServe's legacy autoscaler was Knative KPA (request-count-based). **For vLLM, use KEDA instead.** Red Hat's own docs now recommend KEDA:

- https://developers.redhat.com/articles/2025/09/23/how-set-kserve-autoscaling-vllm-keda — KEDA on vLLM/KServe
- https://developers.redhat.com/articles/2025/11/26/autoscaling-vllm-openshift-ai-model-serving — SLI-driven autoscaling, current reference as of late 2025

RHOAI 2.23 ships with KEDA integration out of the box.

## Multi-node scale (LWS + autoscaler)

LWS scales `replicas` as whole groups (leader + workers). KEDA `scaleTargetRef` points at the `LeaderWorkerSet` object. Cooldowns apply to group spin-up — which is slower than single-pod (every pod in the group must become ready).

```yaml
scaleTargetRef:
  apiVersion: leaderworkerset.x-k8s.io/v1
  kind: LeaderWorkerSet
  name: vllm-multinode
```

Raise `cooldownPeriod` to 600–900 for multi-node.

## Scale-down gotcha: draining streams

Reducing replicas triggers pod termination. In-flight streams die unless:

1. `terminationGracePeriodSeconds: 60+` on the pod.
2. `lifecycle.preStop: exec: ["sleep", "10"]` gives the LB time to stop sending new requests.
3. Gateway/router is aware of termination and stops selecting the pod immediately (GAIE EPP, production-stack router, llm-d EPP all do this).

Plain nginx round-robin will happily send new requests to a pod mid-termination. On nginx, pair with a longer grace period and accept some truncated streams, or upgrade the router.

## SLO-driven autoscaling (advanced)

Instead of queue depth, trigger on P99 TTFT vs SLO:

```yaml
triggers:
  - type: prometheus
    metadata:
      query: |
        histogram_quantile(0.99,
          sum by (le, model_name) (
            rate(vllm:time_to_first_token_seconds_bucket{model_name="qwen3-235b"}[5m])
          )
        )
      threshold: "3"          # seconds — scale when P99 TTFT exceeds SLO
```

Pro: directly aligned with user experience. Con: TTFT is noisier than queue depth; needs longer windows.

## Smoke test — is autoscaling wired?

```bash
# KEDA picked up the ScaledObject
kubectl get scaledobject -A

# The HPA KEDA created is healthy
kubectl get hpa -A -l scaledobject.keda.sh/name=vllm

# Prometheus query returns data
curl -s http://prometheus.monitoring:9090/api/v1/query?query=vllm:num_requests_waiting

# Force load, watch replicas grow
kubectl get deploy vllm -w
```

## Reference posts

- **Production Stack KEDA tutorial**: https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/autoscaling-keda.html
- **Red Hat — KEDA + KServe autoscaling**: https://developers.redhat.com/articles/2025/09/23/how-set-kserve-autoscaling-vllm-keda
- **Red Hat — Autoscaling RHOAI RawDeployments**: https://developers.redhat.com/articles/2025/10/02/autoscaling-vllm-openshift-ai
- **Red Hat — SLI-driven autoscaling**: https://developers.redhat.com/articles/2025/11/26/autoscaling-vllm-openshift-ai-model-serving
- **llm-d v0.3 WVA**: https://llm-d.ai/blog/llm-d-v0.3-expanded-hardware-faster-perf-and-igw-ga
