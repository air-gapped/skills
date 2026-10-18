---
name: vllm-observability
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Observe production vLLM from the data it already emits — the V1 `/metrics` Prometheus surface, SLO alerts on TTFT/ITL/queue/KV/preemption/aborts/corrupted logits, the shipped Grafana dashboards, OTLP tracing (`--otlp-traces-endpoint`, `--collect-detailed-traces`), DCGM pairing (`SM_OCCUPANCY`, not `GPU_UTIL`), metric renames across upgrades, and triage of slow-TTFT or preemption storms from /metrics alone. Use when building, auditing or fixing vLLM dashboards and alerts, wiring vLLM tracing, or diagnosing a vLLM latency incident from metrics.
when_to_use: |-
  Trigger on "vllm metrics", "vllm observability", "vllm prometheus", "vllm grafana", "/metrics vllm", "vllm SLO", "TTFT alert", "ITL alert", "kv_cache_usage_perc", "gpu_cache_usage_perc", "num_requests_waiting", "request_queue_time_seconds", "prefix_cache_hits", "num_preemptions", "spec_decode metrics", "admission_rejections", "--otlp-traces-endpoint", "--collect-detailed-traces", "vllm tracing", "DCGM vllm", "SM_OCCUPANCY", "vllm KEDA", "vllm incident triage", "vllm goodput", "PromQL vllm", "dashboard empty after vllm upgrade". Also implicit when a vLLM deployment is in context — "why is TTFT high", "what should I alert on", "why are preemptions", "vllm is slow", "audit observability", "deploy-memo SLO". Not for load-testing (vllm-benchmarking) or knob tuning (vllm-performance-tuning).
---

# vLLM observability

Target audience: operators running production vLLM on H100/H200 fleets, usually containerized, usually on Kubernetes, on-call for latency and throughput SLOs.

## The core diagnostic rule

When something feels slow, read the ratio, not the absolute:

| Queue depth | TPOT / ITL | Most likely cause |
|---|---|---|
| Rising | Stable | **Capacity shortage** — scale out or increase `max-num-seqs` |
| Stable | Rising | **Context / model-side** — long-context request, CUDA graph recompile, prefix-cache miss |
| Rising | Rising | **Compounding** — usually preemption storm; check `num_preemptions` rate |
| Stable | Stable, but TTFT high | **Scheduler stall** — connector (LMCache/NIXL), head-of-line blocking, or engine-core descheduling (ebpf territory) |

## The metric surface in one paragraph

vLLM exposes a Prometheus text-format endpoint at `/metrics`. All series are prefixed `vllm:`; engine series carry `{model_name, engine}` labels (frontend-side exceptions listed in the catalog). Metrics fall into queue/scheduler state, KV cache pressure, per-request latency histograms (TTFT/ITL/queue/prefill/decode/e2e), throughput counters, and request outcomes (`finished_reason=stop|length|abort`, plus `corrupted_requests` for NaN-logit page-worthy events).

Full catalog with types, buckets, labels, and emission file:line anchors in `references/metrics-catalog.md`. The catalog is V1-first with V0 deltas noted.

## Top signals to alert on

| # | Signal | PromQL sketch | Starter threshold |
|---|---|---|---|
| 1 | **P99 TTFT** | `histogram_quantile(0.99, sum by (le, model_name) (rate(vllm:time_to_first_token_seconds_bucket[5m])))` | Page `> 3s` interactive, `> 10s` batch |
| 2 | **P99 ITL** | same pattern on `vllm:inter_token_latency_seconds_bucket` | Page `> 200ms` streaming |
| 3 | **Queue wait P99** | `vllm:request_queue_time_seconds_bucket` | Page `> 5s` sustained 10m |
| 4 | **KV utilization** | `vllm:kv_cache_usage_perc` | Warn `> 0.80`, page `> 0.95` sustained 15m |
| 5 | **Preemption rate** | `rate(vllm:num_preemptions_total[5m])` | Warn any sustained non-zero |
| 6 | **Abort fraction** | `rate(vllm:request_success_total{finished_reason="abort"}[5m]) / rate(vllm:request_success_total[5m])` | Warn `> 1%`, page `> 10%` |
| 7 | **Corrupted logits** | `increase(vllm:corrupted_requests_total[5m])` | Page on **any** > 0 |
| 8 | **Prefix-cache hit rate** | `rate(vllm:prefix_cache_hits_total[5m]) / rate(vllm:prefix_cache_queries_total[5m])` | Warn if WoW drops > 20% |
| 9 | **Queue depth (for autoscaling)** | `vllm:num_requests_waiting` | KEDA trigger at 2–10 per replica |
| 10 | **XID errors (DCGM side)** | `DCGM_FI_DEV_XID_ERRORS` | Page on any increment |

Full PromQL with multi-window burn-rate templates, SLO calibration notes, and goodput approximation in `references/alerting.md`.

## Dashboards and stacks

The repo ships three operator-ready Grafana dashboards at `examples/observability/`:

- `prometheus_grafana/grafana.json` — 12-panel all-in-one (E2E, TTFT, ITL, KV usage, scheduler, throughput, finish-reason, queue/prefill/decode times, token-length heatmaps)
- `dashboards/grafana/performance_statistics.json` — 20-panel SRE dashboard (latency P50/P90/P99 over time, TPS streams)
- `dashboards/grafana/query_statistics.json` — 18-panel product dashboard (per-model volume, token-size distributions)

Plus a working `docker-compose.yaml` + `prometheus.yaml` for local trials. Perses YAML equivalents in `dashboards/perses/`. Pair with DCGM exporter (Grafana dashboard 15117) for hardware-side metrics.

Full DCGM pairing catalog and external-dashboard inventory in `references/dashboards.md`.

## Tracing

```bash
vllm serve $MODEL \
  --otlp-traces-endpoint=grpc://otel-collector:4317 \
  --collect-detailed-traces=all   # or: model, or: worker
```

`--collect-detailed-traces`:

- **Unlocks** `model_forward_time_milliseconds` and `model_execute_time_milliseconds`; without it spans are emitted but these two per-step metrics are missing.
- **Costs 5–10% throughput.** Enable on one replica during an incident; leave unset as baseline.
- **Combine modules space-separated** (`--collect-detailed-traces model worker`); the comma form `model,worker` fails startup since v0.31.0.

Protocol defaults to gRPC; HTTP/protobuf via `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf`. All OTel packages bundled with vLLM. Full stack choices (Jaeger all-in-one, OTel Collector → Tempo → Grafana, Langfuse), span catalog, and sampling patterns in `references/tracing.md`.

## Critical pitfalls

1. **Alerting on averages.** `sum/count` hides P99 tails that are 10–50× the mean. Every latency alert must go through `histogram_quantile(0.99, …)`.

2. **Forgetting `sum by (le)` before `histogram_quantile`.** Without it, per-instance quantiles mix with fleet quantiles — the most common Grafana mistake in the Prometheus world.

3. **`gpu_cache_usage_perc` no longer exists.** It sat behind `--show-hidden-metrics-for-version=X.Y` on v0.11.x and is gone from the source from v0.12.0, so no flag restores it. Query `vllm:kv_cache_usage_perc`; only fleets still running ≤ v0.11.x need `vllm:kv_cache_usage_perc or vllm:gpu_cache_usage_perc`. PR history in `references/metrics-catalog.md` § KV cache & memory.

4. **`num_requests_swapped` is deprecated on V1** and always zero. Use `num_preemptions_total` instead. Many copy-pasted dashboards still reference swap.

5. **Multi-pod label collisions.** Every pod emits identical `{model_name, engine}` labels. Without a Prometheus relabel adding `pod`/`replica`, counters sum across pods and hide per-replica pathology.

6. **Cardinality explosion.** Never add `request_id` or the prompt text as a Prometheus label — that path is deliberately absent. Per-request visibility lives in OTLP traces, not metrics.

7. **KEDA threshold too low on `num_requests_waiting`.** Thresholds of 1–2 per replica cause scale thrashing. Production Stack default is 5; OpenShift example is 2. Pair with `cooldownPeriod: 360` — GPU pods take ~10 min to reach ready, reactive scaling fails.

8. **`GPU_UTIL` is not a saturation signal.** It reads 100% while the GPU starves — in the ebpfchirp 11-second-TTFT incident util was pinned, SM occupancy was 18%, and the scheduler was stalled on prefix-cache head-of-line blocking. Use `DCGM_FI_PROF_SM_OCCUPANCY`.

9. **Ray Serve deployments don't auto-expose `/metrics`.** `RayPrometheusStatLogger` must be wired explicitly, or Ray 2.51+ ingests vLLM metrics through Ray's own endpoint (disable with `log_engine_metrics: False` to avoid double-scraping).

Full troubleshooting matrix (dashboard-empty, metric-gone-after-upgrade, P99 NaN, histogram buckets miscalibrated for SLO) in `references/alerting.md` under the "When metrics lie" section.

## Verify a deployment can be observed

```bash
# Basic reachability
curl -fsS http://<endpoint>/health
curl -fsS http://<endpoint>/metrics | head -30
# Confirm the load-bearing series exist
curl -s http://<endpoint>/metrics | grep -E '^vllm:(kv_cache_usage_perc|num_requests_(waiting|running)|time_to_first_token|request_success|num_preemptions|prefix_cache_(hits|queries))'
```

`${CLAUDE_SKILL_DIR}/scripts/metrics-smoke.sh` runs the full smoke check against a deployment: confirms endpoints, greps load-bearing series, warns on deprecated metric names, cross-checks DCGM availability if configured. Output is color-coded pass/warn/fail.

**An observability audit is done when all three hold:**

1. `metrics-smoke.sh` exits 0, or every WARN it prints is explained in the report.
2. Every row of [Top signals](#top-signals-to-alert-on) has an alert rule or a written waiver.
3. Every `vllm:*` name the dashboards and rules query exists on the live endpoint. Send one request first, then run:

```bash
names() { grep -oE 'vllm:[a-z0-9_]+' | sed -E 's/_(bucket|sum|count|created)$//' | sort -u; }
grep -rh 'vllm:' <dashboards-and-rules-dir> | names > want.txt
curl -s http://<endpoint>/metrics | grep '^vllm:' | names > have.txt
comm -23 want.txt have.txt   # each line left: renamed, removed, or feature-gated per metrics-catalog.md
```

## Upgrade traps

Every name, label and release gate below is in `references/metrics-catalog.md`; its § V0 vs V1 deltas maps each deprecated name to its replacement.

| Trap | Action |
|---|---|
| v0.28.0 renamed `vllm:kv_offload_tiering_block_{queries,hits}` → `…_chunk_{queries,hits}`; on v0.28.x–v0.29.x the constants kept their `BLOCK_*` names, so a source grep finds no rename | Rewrite dashboards and alerts on the old names — they go silently empty |
| `vllm:kv_offload_total_*` deprecated, observed only under `CPUOffloadingSpec` | Switch to the direction-split `kv_offload_{load,store}_*` set |
| v0.31.0+: `nixl_num_failed_transfers` already includes notification failures | Never add `nixl_num_failed_notifications` to it |
| v0.32.0+: `vllm:admission_rejections_total{reason}` counts frontend load shedding, which never reaches `num_requests_waiting` | Alert on any sustained rate |
| KV capacity as `num_gpu_blocks * block_size` overstates hybrid models | On v0.24.0+ read `kv_cache_size_tokens` from `vllm:cache_config_info` |
| MFU on MLA models (DeepSeek-V2/V3/R1) before v0.24.0 overestimated KV bandwidth ~57× | Discard that MFU history |

## External references

- Metrics design doc (canonical): https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md
- Metrics source of truth: https://github.com/vllm-project/vllm/tree/main/vllm/v1/metrics
- Example dashboards: https://github.com/vllm-project/vllm/tree/main/examples/observability
- Production metrics docs: https://docs.vllm.ai/en/stable/usage/metrics/
- OTel POC: https://docs.vllm.ai/en/stable/examples/observability/opentelemetry.html
- Blog — Anatomy of vLLM (defines goodput, scheduler scoring): https://vllm.ai/blog/anatomy-of-vllm
- Blog — Large-Scale Serving (DeepSeek @ 2.2k tok/s/H200): https://blog.vllm.ai/2025/12/17/large-scale-serving.html
- Blog — MorIIO disagg (bimodal-ITL, goodput framing): https://vllm.ai/blog/moriio-kv-connector
- ebpfchirp — 11-Second TTFT on a Healthy Server (canonical incident): https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on
- akrisanov.com — vLLM Metrics in Production (concrete alert set): https://akrisanov.com/vllm-metrics/
- DCGM exporter + Grafana dashboard 15117: https://grafana.com/grafana/dashboards/15117-nvidia-dcgm-exporter/
- Sibling skills: `vllm-caching` (KV tiering), `vllm-benchmarking` (bench + output JSON), `vllm-configuration` (env vars + YAML)
