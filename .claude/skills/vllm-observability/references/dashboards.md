# vLLM dashboards & GPU-side pairing

Last verified: 2026-04-24 (see `references/sources.md`)

Load when choosing a dashboard to ship, adapting an upstream one, or deciding what GPU-hardware metrics to surface alongside vLLM's own.

## Shipping dashboards in the vLLM repo

Location: `examples/observability/` (path moved from the deprecated `examples/production_monitoring/`).

### `prometheus_grafana/`

Ready-to-run minimal stack: Grafana + Prometheus via docker-compose, one dashboard.

- `grafana.json` — **12-panel all-in-one** dashboard. Panels:
  - E2E request latency (P50/P90/P95/P99 via `histogram_quantile`)
  - Token throughput (prompt + generation rate)
  - Inter-token latency (P50/P90/P95/P99)
  - Scheduler state (running + waiting over time)
  - TTFT (P50/P90/P95/P99)
  - KV cache utilization
  - Request prompt-length heatmap
  - Request generation-length heatmap
  - Finish-reason breakdown (`request_success_total{finished_reason}`)
  - Queue time
  - Prefill + decode time
  - Max-generation-tokens per sequence group
- `prometheus.yaml` — 5s scrape interval, 30s evaluation, target `host.docker.internal:8000`
- `docker-compose.yaml` — `prom/prometheus:latest` + `grafana/grafana:latest`; no DCGM, no cAdvisor, no node-exporter

Import directly into existing Grafana via **Dashboards → New → Import → Upload JSON**.

### `dashboards/grafana/`

Two newer, more specialized dashboards:

- `performance_statistics.json` — **20-panel SRE dashboard**:
  - E2E latency stats P50/P90/P99 + over-time rows
  - TTFT stats + TTFT percentile-over-time
  - ITL stats + percentile-over-time
  - Tokens-per-second streams (prompt, generation, iteration tokens)

- `query_statistics.json` — **18-panel product dashboard**:
  - Successful-request volume over time
  - P50/P90/P99 latency summary stats
  - Input token size distribution + percentiles
  - Output token size distribution + percentiles

### `dashboards/perses/`

Same two dashboards as above but in Perses YAML format. For operators using Perses instead of Grafana.

### `opentelemetry/`

OTLP proof-of-concept: Jaeger all-in-one via docker-compose, dummy client script, example `--otlp-traces-endpoint` wiring. See `tracing.md` for the full stack.

### `metrics/offline.py`

Shows `llm.get_metrics()` for notebook/benchmark contexts without HTTP. Useful for capture-and-compare in CI.

## vLLM Production Stack dashboard

Source: `github.com/vllm-project/production-stack/helm/charts/vllm/dashboards/vllm-dashboard.json` + optional `lmcache-dashboard-cm.yaml`.

Deployed as ConfigMaps picked up by kube-prometheus-stack sidecar when the Helm values enable `grafanaDashboards.enabled: true`.

Four-row layout:
1. **System Overview** — healthy pod count, router QPS, P99 latencies
2. **QoS** — per-model TTFT/ITL, abort fraction
3. **Engine Load** — per-engine running/waiting, KV utilization, preemption rate
4. **Resource Usage** — router pod CPU/mem/disk, node-level if exporters wired

Uniquely surfaces **router-level metrics** that don't exist on a pure vLLM-serve deployment:
- `vllm:current_qps` — router-level QPS; **absent** on standalone vLLM
- `healthy_pods_total` — backend liveness count

**Enable via Helm values:**
```yaml
servingEngineSpec:
  serviceMonitor:
    enabled: true
routerSpec:
  serviceMonitor:
    enabled: true
grafanaDashboards:
  enabled: true
```

## Ray Serve LLM integration

Ray 2.51+ auto-exposes vLLM engine metrics through Ray's metrics endpoint (port 8080 typically). Pre-built Grafana dashboards ship with Ray.

- Disable double-scraping with `log_engine_metrics: False` on the deployment if Prometheus already scrapes Ray.
- Ray dashboard (web UI :8265) is best for actor placement in multi-node TP. Doesn't duplicate vLLM metrics but surfaces:
  - `ray_serve_num_router_requests`
  - `ray_serve_deployment_replica_healthy`
  - Per-actor GPU-process uptime

## Cloud-provider integrations

| Provider | Integration |
|---|---|
| **Azure AKS AI Toolchain Operator (KAITO)** | Pre-wired to import `grafana.json` into Azure Managed Grafana. ServiceMonitor YAML documented, 30s scrape interval. |
| **Google Cloud Managed Prometheus** | First-party vLLM exporter page with PodMonitoring CR template. |
| **NVIDIA Dynamo** | Documents vLLM metrics as part of its backend. Secondary reference for semantics. |
| **KServe** | No built-in dashboard; integration surface is `serving.kserve.io/enable-prometheus-scraping: "true"` annotation. KEDA uses `num_requests_running` or `num_requests_waiting`. |
| **Langfuse** | OTLP-based; captures token counts and latency spans, **not** prompts/completions. |

## Community / commercial

- **Grafana Labs dashboard 23991 ("vLLM")** — generic import starting template. No authoritative authorship.
- **akrisanov.com "vLLM Metrics in Production"** — concrete alert set + operator's mental model.
- **glukhov.org "Monitoring LLM Inference"** — side-by-side dashboard structure comparing TGI, vLLM, llama.cpp.

## vLLM Performance Dashboard (release-engineering, not ops)

`https://hud.pytorch.org/benchmark/llms?repoName=vllm-project/vllm` — nightly performance dashboard triggered every 4 hours by a PyTorch CI workflow. Runs on every PR tagged `perf-benchmarks + ready`.

Nightly comparisons: vLLM vs TGI vs TRT-LLM vs LMDeploy. Useful for operators only as a pre-upgrade sanity check ("is this release regressing on the workload shape I care about?"). Not for live production monitoring.

## DCGM pairing — minimum viable GPU-side metrics

vLLM's metrics say nothing about the hardware. Every production deployment needs DCGM exporter stacked alongside. Minimum set:

| DCGM metric | Why it matters | Pair with |
|---|---|---|
| `DCGM_FI_DEV_GPU_UTIL` | % time GPU is busy. **Coarse, can lie.** Can hit 100% under starvation | `num_requests_running` — if GPU_UTIL high but running drops, scheduler stuck |
| `DCGM_FI_PROF_SM_OCCUPANCY` | **The real saturation signal** — resident warps / max | `iteration_tokens_total` histogram. If occupancy low while throughput OK, prefill-heavy; if occupancy low and throughput bad, stall |
| `DCGM_FI_DEV_FB_USED` / `FB_FREE` | Framebuffer bytes used/free | `kv_cache_usage_perc`. Should track. Divergence = non-KV allocation (compile cache, CUDA graphs) |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | HBM bandwidth saturation | ITL tail. Decode is BW-bound — this metric is the ITL-regression leading indicator |
| `DCGM_FI_DEV_GPU_TEMP` + `DCGM_FI_DEV_POWER_USAGE` | Temp + power | Thermal throttling appears in ITL tail fluctuation before anywhere else |
| `DCGM_FI_PROF_NVLINK_RX_BYTES` / `TX_BYTES` | NVLink traffic | Multi-GPU TP — saturates before compute on MoE wide-EP |
| `DCGM_FI_DEV_XID_ERRORS` | XID fault counter | **Page on any increment** — usually first sign of a dying GPU |

### Deploy DCGM exporter

Kubernetes: `nvidia-dcgm-exporter` Helm chart, or the NVIDIA GPU Operator (bundled).

Compose:
```yaml
dcgm-exporter:
  image: nvcr.io/nvidia/k8s/dcgm-exporter:4.0.0-4.0.0-ubuntu22.04
  runtime: nvidia
  environment:
    DCGM_EXPORTER_INTERVAL: "30000"   # milliseconds — 30s. NOT 30 (that's 30ms, fills TSDB fast)
  ports:
    - "9400:9400"
```

### Pairing dashboards

- **Grafana dashboard 15117** (NVIDIA DCGM Exporter) — canonical GPU dashboard. Pairs cleanly side-by-side with vLLM's `grafana.json`.
- **Grafana dashboard 12239** — alternative with more per-metric detail.

### Ebpfchirp incident reference

The canonical "dashboard lied" case study: 11-second TTFT on a vLLM server where:
- `nvidia-smi GPU_UTIL` = 100% (looked healthy)
- `SM_OCCUPANCY` = 18% (actual sign of starvation)
- Root cause: engine-core CPU descheduling during prefix-cache head-of-line blocking
- Detection required: eBPF tracing of scheduler thread

Dashboard takeaway: **include SM_OCCUPANCY on the same row as `num_requests_running`**. When running stays high while SM occupancy drops, that's starvation in real time. URL: https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on.

## Common dashboard structural mistakes

1. **No `model_name` variable** — multi-tenant dashboards without a template variable mix all models into one percentile, producing meaningless P99s.
2. **No `pod` variable** — without Prometheus relabel adding pod label, aggregates hide per-pod pathology.
3. **Using `[1m]` windows with 5s scrape** — produces stat noise on percentile panels. Use `[5m]` minimum.
4. **Hard-coding Prometheus UID** in dashboards instead of using `${DS_PROMETHEUS}` template — imports fail or bind to wrong datasource.
5. **Panel units mismatched to metric units** — vLLM histograms are in seconds; panels often default to milliseconds, showing 3000 instead of 3.
6. **No legend cardinality cap** — `{instance, model_name, engine, pod}` cross-product produces Grafana-browser-hangs on legend rendering above ~50 series. Set `Legend: Hide` or aggregate harder in the query.
7. **Alert thresholds in Grafana instead of Prometheus** — Grafana alerts require the browser/server to be up. Alertmanager rules in Prometheus survive Grafana outages.

## Import workflow (Grafana)

```bash
# 1. Copy the JSON
curl -sO https://raw.githubusercontent.com/vllm-project/vllm/main/examples/observability/prometheus_grafana/grafana.json

# 2. In Grafana UI
#    Dashboards → New → Import → Upload JSON → pick Prometheus datasource → Import

# 3. Customize
#    - Add `model_name` template variable: Variables → New → Prometheus → label_values(vllm:num_requests_running, model_name)
#    - Add `pod` template variable if relabel configured
#    - Adjust panel units (ms vs s) if SLO targets sub-second
```

## References

- vLLM examples/observability: https://github.com/vllm-project/vllm/tree/main/examples/observability
- Metrics design doc: https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md
- Production Stack: https://github.com/vllm-project/production-stack
- Production Stack dashboards (DeepWiki): https://deepwiki.com/vllm-project/production-stack/7.2-grafana-dashboards
- Azure KAITO monitoring: https://learn.microsoft.com/en-us/azure/aks/ai-toolchain-operator-monitoring
- GCP managed Prometheus vLLM exporter: https://cloud.google.com/stackdriver/docs/managed-prometheus/exporters/vllm
- Red Hat KServe + KEDA: https://developers.redhat.com/articles/2025/09/23/how-set-kserve-autoscaling-vllm-keda
- DCGM exporter: https://github.com/NVIDIA/dcgm-exporter
- Grafana DCGM dashboard: https://grafana.com/grafana/dashboards/15117-nvidia-dcgm-exporter/
- Ebpfchirp 11s TTFT incident: https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on
