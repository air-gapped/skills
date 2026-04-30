# `smg_*` Prometheus surface

The gateway exposes 40+ Prometheus metrics under the `smg_*` prefix on `--prometheus-host:--prometheus-port` (default `127.0.0.1:29000` — set host to `0.0.0.0` for K8s). Metric prefix was renamed Dec 2025 from `sgl_router_*`.

## What's actually shipped

The README enumerates the catalog. Categories:

### HTTP

- `smg_http_requests_total{method,path,status}` — counter
- `smg_http_request_duration_seconds{method,path}` — histogram

### Router routing decisions

- `smg_router_ttft_seconds{model}` — time to first token, histogram
- `smg_router_tpot_seconds{model}` — time per output token, histogram
- `smg_router_e2e_seconds{model}` — end-to-end request latency
- `smg_router_request_queue_length{model}` — current queued requests
- `smg_worker_selection_total{worker,policy}` — counter, increments per routing decision
- `smg_worker_cb_state{worker}` — gauge: 0=closed, 1=half-open, 2=open
- `smg_worker_health_state{worker}` — gauge: 0=unhealthy, 1=healthy

### Inference

- `smg_inference_requests_total{model,status}` — counter
- `smg_inference_requests_running{model}` — gauge of in-flight per worker
- `smg_inference_input_tokens_total{model}` — counter
- `smg_inference_output_tokens_total{model}` — counter
- `smg_inference_cache_hit_tokens_total{model}` — counter (when worker reports it)

### Discovery

- `smg_discovery_workers_discovered{namespace}` — gauge
- `smg_discovery_workers_added_total{namespace}` — counter
- `smg_discovery_workers_removed_total{namespace}` — counter
- `smg_discovery_probe_failures_total{worker,reason}` — counter

### Retry / circuit breaker

- `smg_retry_attempts_total{worker,outcome}` — counter
- `smg_cb_transitions_total{worker,from,to}` — counter

### MCP

- `smg_mcp_tool_calls_total{tool,status}` — counter

### History DB

- `smg_history_writes_total{backend,status}` — counter

The exact field names and types may shift between gateway versions — verify with `curl http://localhost:29000/metrics | grep -E '^# (TYPE|HELP) smg_'`.

## Useful PromQL recipes

### Per-worker request rate

```promql
sum by (worker) (rate(smg_worker_selection_total[1m]))
```

### TTFT P99 by model

```promql
histogram_quantile(0.99,
  sum by (le, model) (rate(smg_router_ttft_seconds_bucket[5m])))
```

### Cache hit rate (router-side, when worker reports cached tokens)

```promql
sum by (model) (rate(smg_inference_cache_hit_tokens_total[5m])) /
sum by (model) (rate(smg_inference_input_tokens_total[5m]))
```

### Circuit breaker open

```promql
max by (worker) (smg_worker_cb_state) == 2
```

### Discovery flapping

```promql
rate(smg_discovery_workers_added_total[15m]) +
rate(smg_discovery_workers_removed_total[15m]) > 0.05
```

### Queue depth saturation

```promql
smg_router_request_queue_length / on (model) group_left
  scalar(max(smg_router_request_queue_length))   # adjust to your queue-size flag
> 0.8
```

## Joining gateway and worker metrics

The gateway emits `smg_*` and the workers emit `vllm:*` (or `sglang_*`). Join on `model_id` (added via ServiceMonitor relabeling — see `references/kubernetes.md`):

### Gateway-reported request rate vs worker-reported running count

```promql
sum by (model_id) (rate(smg_inference_requests_total{model_id="llama-3-8b"}[1m]))
vs
sum by (model_id) (vllm:num_requests_running{model_id="llama-3-8b"})
```

If gateway-reported rate stays high but worker-reported running drops, requests are queueing in the gateway, not at the workers — you're at gateway capacity. Conversely, gateway rate stable but worker-reported queue growing means the worker is the bottleneck.

### Per-route TTFT split: gateway-side vs vLLM-side

The gateway reports the wall-clock TTFT; vLLM reports its internal scheduler-to-first-token. Difference = network + tokenization + queueing on the gateway:

```promql
histogram_quantile(0.99, sum by (le) (rate(smg_router_ttft_seconds_bucket[5m]))) -
histogram_quantile(0.99, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[5m])))
```

A growing gap means the gateway is adding latency — investigate tokenizer cache hit rate, retry storms, or CPU saturation on the gateway pod.

## Alerts worth shipping

```yaml
groups:
  - name: sgl-model-gateway
    rules:
      - alert: GatewayCircuitBreakerOpen
        expr: max by (worker, model_id) (smg_worker_cb_state) == 2
        for: 2m
        annotations:
          summary: "Gateway has opened CB for {{ $labels.worker }} ({{ $labels.model_id }})"

      - alert: GatewayQueueGrowing
        expr: smg_router_request_queue_length > 0.8 * <queue-size>
        for: 5m
        labels: {severity: warning}

      - alert: GatewayDiscoveryFlapping
        expr: rate(smg_discovery_workers_added_total[15m]) +
              rate(smg_discovery_workers_removed_total[15m]) > 0.1
        for: 10m
        annotations:
          summary: "Discovery is flapping for {{ $labels.namespace }}"

      - alert: GatewayHighRetryRate
        expr: rate(smg_retry_attempts_total{outcome="exhausted"}[5m]) > 0.5
        for: 5m
        labels: {severity: critical}
        annotations:
          summary: "Retries exhausting at >0.5/s — backend saturated or down"

      - alert: GatewayP99TTFTSLOBreach
        expr: histogram_quantile(0.99,
                sum by (le, model_id) (rate(smg_router_ttft_seconds_bucket[5m])))
              > 2.0
        for: 10m
        annotations:
          summary: "TTFT P99 > 2s for {{ $labels.model_id }}"
```

Tune thresholds per your SLOs.

## Grafana dashboards

There is **no upstream Grafana dashboard JSON shipped under the new metric names** as of v0.3.x. You'll need to build your own or rewrite an old `sgl_router_*`-prefixed dashboard.

Suggested rows:

1. **Routing decisions per second** — `smg_worker_selection_total` rate by worker.
2. **TTFT P50/P95/P99** — `smg_router_ttft_seconds` histogram.
3. **Per-worker health & CB** — `smg_worker_health_state` and `smg_worker_cb_state` time-series.
4. **Discovery state** — `smg_discovery_workers_discovered` per namespace.
5. **Retry storms** — `smg_retry_attempts_total{outcome=~"retry|exhausted"}`.
6. **Queue depth** — `smg_router_request_queue_length`.
7. **Cache hit rate** — derived from `smg_inference_cache_hit_tokens_total`.

Dashboard variables: `model_id`, `pod`, `node` (relabeled from K8s metadata via ServiceMonitor — see `references/kubernetes.md`).

## OTel traces

When `--enable-trace` is set with `--otlp-traces-endpoint <host>:<port>`, the gateway emits spans for:

- HTTP request entry/exit
- Worker selection
- Upstream HTTP/gRPC call to worker
- Tokenization
- Retry/CB decisions

Useful for understanding tail-latency in production. Pair with worker-side OTel (vLLM `--otlp-traces-endpoint`) for end-to-end traces.
