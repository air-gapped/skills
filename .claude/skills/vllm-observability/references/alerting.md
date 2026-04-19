# Alerting & SLO recipes for vLLM

Load when building Prometheus alert rules, calibrating SLO thresholds, or triaging from `/metrics` during an incident.

## Table of contents
- [The ten signals that matter](#the-ten-signals-that-matter)
- [PromQL templates (copy-paste ready)](#promql-templates-copy-paste-ready)
- [SLO burn-rate alerts](#slo-burn-rate-alerts)
- [Goodput as a derived SLI](#goodput-as-a-derived-sli)
- [Autoscaling signals (KEDA / HPA)](#autoscaling-signals-keda--hpa)
- [Incident triage playbook](#incident-triage-playbook)
- [When metrics lie](#when-metrics-lie)

## The ten signals that matter

Thresholds here are starter values — calibrate against an actual SLO document. Every alert must specify a duration (`for: 10m`) to suppress noise.

| # | What | Why page | Starter threshold |
|---|---|---|---|
| 1 | P99 TTFT | User-visible responsiveness. Never alert on mean — averages hide tails 10–50× | `>3s` interactive, `>10s` batch, sustained 10m |
| 2 | P99 ITL (inter-token latency) | Streaming UX. Bimodal ITL is the leading indicator of disagg-worthy workload | `>200ms` streaming, warn `>80ms` |
| 3 | P99 queue wait | Separates capacity from compute | warn `>2s`, page `>5s` for 10m |
| 4 | KV cache utilization | Above 95% the scheduler preempts | warn `>0.80`, page `>0.95` for 15m |
| 5 | Preemption rate | Preemptions destroy SLO for affected requests | warn any sustained non-zero |
| 6 | Abort fraction | Clients timing out because TTFT blown | warn `>1%`, page `>10%` |
| 7 | Corrupted logits | Silent — request returns garbage, not error | page on **any** increment |
| 8 | Prefix-cache hit-rate drop | Leading indicator of prompt-shape change | warn if WoW drops `>20%` |
| 9 | Queue depth (autoscale trigger) | Autoscaling signal | KEDA: 2–10 per replica |
| 10 | GPU XID errors | Hardware fault, page immediately | page on any increment |

## PromQL templates (copy-paste ready)

### P99 TTFT (fleet-wide, per model)

```promql
histogram_quantile(
  0.99,
  sum by (le, model_name) (
    rate(vllm:time_to_first_token_seconds_bucket[5m])
  )
)
```

Rules of thumb:
- Always `sum by (le, model_name)` before `histogram_quantile` — per-instance quantiles mix poorly with fleet quantiles.
- `[5m]` window smooths scrape noise at 15s intervals. `[1m]` only for ops dashboards where jitter is acceptable.
- Replace `0.99` with `0.95` for fleet-health dashboard; keep `0.99` for pager rules.

### P99 ITL

```promql
histogram_quantile(
  0.99,
  sum by (le, model_name) (
    rate(vllm:inter_token_latency_seconds_bucket[5m])
  )
)
```

### Queue wait P99

```promql
histogram_quantile(
  0.99,
  sum by (le, model_name) (
    rate(vllm:request_queue_time_seconds_bucket[5m])
  )
)
```

### KV utilization (current)

```promql
max by (model_name, pod) (vllm:kv_cache_usage_perc)
```

On mixed-version fleets straddling the rename saga:
```promql
max by (model_name, pod) (vllm:kv_cache_usage_perc or vllm:gpu_cache_usage_perc)
```

### Preemption rate

```promql
rate(vllm:num_preemptions_total[5m])
```

### Abort fraction

```promql
sum(rate(vllm:request_success_total{finished_reason="abort"}[5m]))
/
sum(rate(vllm:request_success_total[5m]))
```

### Corrupted logits

```promql
increase(vllm:corrupted_requests_total[5m]) > 0
```

Set `for: 0s`. Single increment warrants a page.

### Prefix-cache hit rate

```promql
sum(rate(vllm:prefix_cache_hits_total[5m]))
/
sum(rate(vllm:prefix_cache_queries_total[5m]))
```

Week-over-week drop detection:
```promql
(
  (sum(rate(vllm:prefix_cache_hits_total[5m])) / sum(rate(vllm:prefix_cache_queries_total[5m])))
  -
  (sum(rate(vllm:prefix_cache_hits_total[5m] offset 7d)) / sum(rate(vllm:prefix_cache_queries_total[5m] offset 7d)))
) < -0.20
```

### Queue depth (scaling signal)

```promql
max by (model_name) (vllm:num_requests_waiting)
```

Divide by replica count if KEDA expects per-replica:
```promql
max by (model_name) (vllm:num_requests_waiting)
/
count by (model_name) (vllm:num_requests_running)
```

## SLO burn-rate alerts

Multi-window, multi-burn-rate alerts (Google SRE Workbook style). Works unchanged on `time_to_first_token_seconds`.

Define SLI (% of requests under SLO) as a recording rule:
```yaml
- record: slo:vllm_ttft_below_3s:ratio_rate5m
  expr: |
    (
      sum by (model_name) (rate(vllm:time_to_first_token_seconds_bucket{le="2.5"}[5m]))
    ) /
    (
      sum by (model_name) (rate(vllm:time_to_first_token_seconds_count[5m]))
    )
```

Fast-burn alert (2% of monthly budget in 1h):
```yaml
- alert: VllmTTFTFastBurn
  expr: |
    (1 - slo:vllm_ttft_below_3s:ratio_rate5m) > (14.4 * (1 - 0.99))
    and
    (1 - slo:vllm_ttft_below_3s:ratio_rate1h) > (14.4 * (1 - 0.99))
  for: 2m
```

Slow-burn (10% of budget in 24h):
```yaml
- alert: VllmTTFTSlowBurn
  expr: |
    (1 - slo:vllm_ttft_below_3s:ratio_rate6h) > (6 * (1 - 0.99))
    and
    (1 - slo:vllm_ttft_below_3s:ratio_rate24h) > (6 * (1 - 0.99))
  for: 15m
```

The 14.4× / 6× multipliers come from Google SRE's burn-rate tables. Target budget: 99% SLO over 30d.

## Goodput as a derived SLI

vLLM bench defines goodput as "requests completed within an SLO budget." Not natively exposed as a Prometheus metric. Approximation from `/metrics`:

```promql
# Requests/sec completing successfully, scaled down if SLOs red
(
  sum(rate(vllm:request_success_total{finished_reason="stop"}[5m]))
)
*
on() group_left() (
  (histogram_quantile(0.99, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[5m]))) < 3)
  and on()
  (histogram_quantile(0.99, sum by (le) (rate(vllm:inter_token_latency_seconds_bucket[5m]))) < 0.08)
)
```

Truer goodput (per-request SLO check) needs trace-level joining — not available in Prometheus alone.

## Autoscaling signals (KEDA / HPA)

`vllm:num_requests_waiting` is the canonical autoscaler signal. vLLM Production Stack, KServe + KEDA, Red Hat OpenShift examples all use variants.

**KEDA ScaledObject (minimal):**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: vllm-llama70b
spec:
  scaleTargetRef:
    name: vllm-llama70b
  minReplicaCount: 1
  maxReplicaCount: 8
  cooldownPeriod: 360          # 6 min — GPU pods take ~10 min to ready
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        metricName: vllm_queue_depth
        threshold: "5"
        query: max(vllm:num_requests_waiting{model_name="llama-70b"})
```

Threshold calibration:
- `<2` per replica → scale thrashing, pods churn
- `2–5` → Red Hat / OpenShift example default
- `5–10` → Production Stack default
- `>10` → laggy scale-up, risks SLO breach

**Never** use `num_requests_running` alone as trigger — that saturates at `max-num-seqs` even when overloaded. Use waiting for scale decisions, running for capacity-plan analysis.

## Incident triage playbook

Work from the top. Each step should take < 2 min.

### Step 1 — Endpoint up?

```bash
curl -fsS http://$EP/health   # 200 = engine alive; 503 = EngineDeadError
```

`EngineDeadError` = the engine process crashed. Check pod logs (`kubectl logs`), look for OOM, NCCL error, or `AssertionError`. Restart.

### Step 2 — Capacity vs compute?

| Observation | Diagnosis |
|---|---|
| Queue waiting rising, TPOT stable | Capacity — scale out |
| Queue stable, TPOT rising | Compute/context — long-context outlier, CUDA graph rebuild, prefix-miss storm |
| Both rising | Compounding — usually preemption storm, check `num_preemptions_total` rate |
| Both stable, TTFT still high | Scheduler stall (LMCache/NIXL fsync, head-of-line blocking) |

Confirm via PromQL snapshots:
```bash
curl -s http://$EP/metrics | grep -E '^vllm:(num_requests_(waiting|running)|num_preemptions_total|kv_cache_usage_perc) '
```

### Step 3 — KV pressure?

```bash
curl -s http://$EP/metrics | grep -E '^vllm:kv_cache_usage_perc '
```

`>0.95` sustained = about to preempt. Either reduce `max-num-seqs`, add prefix cache, reduce `gpu-memory-utilization` (counterintuitive — frees block alloc headroom), or extend KV to CPU via `--kv-offloading-backend native --kv-offloading-size N`.

### Step 4 — Prefix cache regression?

Compare current hit rate to 7d ago (see PromQL template above). A cliff usually means client prompts changed shape, or the fleet autoscaled and lost warmed blocks.

### Step 5 — GPU-side fault?

If software metrics don't explain it:
- `DCGM_FI_DEV_XID_ERRORS` — any increment = hardware event
- `DCGM_FI_PROF_SM_OCCUPANCY` — if low while `num_requests_running` is high, scheduler stall (ebpf territory)
- `DCGM_FI_DEV_GPU_TEMP` — thermal throttling shows up in ITL tail first
- `DCGM_FI_PROF_NVLINK_RX_BYTES` — TP saturation on MoE wide-EP configs

### Step 6 — If all else looks fine

Enable `--collect-detailed-traces=all` on one replica, reproduce, read trace. The two flags that appear only with detailed traces (`model_forward_time_milliseconds`, `model_execute_time_milliseconds`) tell whether the pain is model-side or scheduler-side.

## When metrics lie

### Averages hide tails

`sum / count` on a latency histogram reports mean. P99 is usually 10–50× mean. Alerts on mean will miss every SLO breach until fleet-wide collapse.

### Per-instance quantiles mixed with fleet quantiles

Without `sum by (le, …)` before `histogram_quantile`, each instance's buckets are quantiled separately and the result is meaningless. Most common Grafana mistake.

### Counters reset on engine restart

`*_total` counters reset to 0. Use `increase()` or `rate()`, never absolute diff across restarts.

### Multi-pod label collision

Every pod emits `{model_name, engine}` identically. Without `pod` or `replica` label added by Prometheus relabel, `sum(...)` hides per-pod pathology and `max(...)` can point at the wrong pod. Relabel at scrape time:
```yaml
metric_relabel_configs:
  - source_labels: [__meta_kubernetes_pod_name]
    target_label: pod
```

### Cardinality blow-up

Never add `request_id` or user prompt as a Prometheus label. The vLLM team deliberately did not expose per-request metrics on Prometheus for this reason. Per-request visibility goes through OTLP traces.

### Histogram bucket coverage

Default TTFT buckets jump `[0.25, 0.5, 0.75, 1.0]`. If SLO is P99 < 250ms, resolution there is weak. Either rewrite the engine (not practical) or rely on trace-level aggregation for sub-bucket precision.

### V0 metric names on V1 dashboards

Copy-pasted dashboards referencing `num_requests_swapped`, `cpu_cache_usage_perc`, or `time_per_output_token_seconds` will show empty panels. Audit and update to V1 names.

### Ray Serve `/metrics` missing

Embedding vLLM in Ray Serve requires explicit `RayPrometheusStatLogger` wiring, or Ray 2.51+ re-exposes via Ray's endpoint. Scraping port 8000 from a Ray-deployed vLLM will 404.

### DP engine metrics summed across replicas

`--api-server-count > 1` puts Prometheus in multiprocess mode. Counters are summed across API server processes; gauges use `mostrecent` mode. Built-in Python metrics (`python_gc_*`, `process_*`) disappear. Design dashboards to tolerate this.

### Sliding-window community-requested stats declined

Issue #22480 asked for request-count-based sliding windows; declined upstream. Implement via `recording_rules` in Prometheus if needed.

### Scrape lag

Metrics update once per scheduler iteration (usually 10–100 ms) and Prometheus scrapes at 15–30s. Sub-minute alerts will have scrape-latency artifacts. Keep `for: 5m` minimum on latency alerts.
