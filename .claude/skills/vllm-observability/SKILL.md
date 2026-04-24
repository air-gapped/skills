---
name: vllm-observability
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Observe production vLLM — `/metrics` Prometheus surface (V1 engine), SLO-driven alerting on TTFT/ITL/queue/KV/preemption/aborts/corrupted-logits, shipping Grafana dashboards in `examples/observability/`, OTLP tracing with `--otlp-traces-endpoint` and `--collect-detailed-traces={model,worker,all}`, diagnostic rules to triage from /metrics alone — queue-grows + TPOT-stable means capacity, queue-stable + TPOT-grows means context/model, DCGM `SM_OCCUPANCY` is the real GPU-saturation signal not `GPU_UTIL`. V1 metric names (kv_cache_usage_perc), gpu_→kv_ rename saga (PR #24245 / revert #25392), DCGM-exporter pairing, dashboard-lying pitfalls.
when_to_use: |-
  Trigger on "vllm metrics", "vllm observability", "vllm prometheus", "vllm grafana", "/metrics vllm", "vllm SLO", "TTFT alert", "ITL alert", "kv_cache_usage_perc", "num_requests_waiting", "request_queue_time_seconds", "prefix_cache_hits", "num_preemptions", "spec_decode metrics", "--otlp-traces-endpoint", "--collect-detailed-traces", "vllm tracing", "DCGM vllm", "SM_OCCUPANCY", "vllm KEDA", "vllm incident triage", "vllm goodput", "PromQL vllm". Building a dashboard, SLO burn-rate alerts, pairing vLLM with DCGM, diagnosing slow-TTFT / preemption-storm from /metrics alone. Also implicit — "why is TTFT high", "what should I alert on", "why are preemptions", "vllm is slow", "deploy-memo SLO", "audit observability" — question is from data vLLM already emits.
---

# vLLM observability

Target audience: operators running production vLLM on H100/H200 fleets, usually containerized, usually on Kubernetes, on-call for latency and throughput SLOs.

## Why this matters

`nvidia-smi` can show a perfectly healthy GPU while TTFT is 11 seconds. Raw throughput in `tok/s` can be rising while user-visible P99 TTFT is cratering. Every production incident this skill exists to catch shares one structural problem: aggregate numbers and hardware counters lie, and only the vLLM-internal per-request distributions tell the truth.

Two operator-facing outcomes matter:

1. **Alerting that wakes the right person for the right reason** — TTFT/ITL tail, queue depth, preemption rate, corrupted logits.
2. **Diagnosis from /metrics alone** — a small number of metric patterns distinguish "out of capacity" from "stuck scheduler" from "hot long-context outlier" without SSH'ing to the pod.

## The core diagnostic rule

When something feels slow, read the ratio, not the absolute:

| Queue depth | TPOT / ITL | Most likely cause |
|---|---|---|
| Rising | Stable | **Capacity shortage** — scale out or increase `max-num-seqs` |
| Stable | Rising | **Context / model-side** — long-context request, CUDA graph recompile, prefix-cache miss |
| Rising | Rising | **Compounding** — usually preemption storm; check `num_preemptions` rate |
| Stable | Stable, but TTFT high | **Scheduler stall** — connector (LMCache/NIXL), head-of-line blocking, or engine-core descheduling (ebpf territory) |

This table is the skill's single most valuable line. Everything else is how to read the underlying metrics.

## The metric surface in one paragraph

vLLM exposes a Prometheus text-format endpoint at `/metrics`. All series are prefixed `vllm:` and carry `{model_name, engine}` labels. Metrics fall into queue/scheduler state, KV cache pressure, per-request latency histograms (TTFT/ITL/queue/prefill/decode/e2e), throughput counters, and request outcomes (`finished_reason=stop|length|abort`, plus `corrupted_requests` for NaN-logit page-worthy events).

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

**Do not use `GPU_UTIL` as the saturation signal.** It hits 100% under severe starvation. Use `DCGM_FI_PROF_SM_OCCUPANCY`. Full DCGM pairing catalog and external-dashboard inventory in `references/dashboards.md`.

## Tracing

```bash
vllm serve $MODEL \
  --otlp-traces-endpoint=grpc://otel-collector:4317 \
  --collect-detailed-traces=all   # or: model, or: worker — expensive, use per-incident
```

Without `--collect-detailed-traces`, spans are emitted but the two most useful per-step metrics (`model_forward_time_milliseconds`, `model_execute_time_milliseconds`) are missing. Flag is designed to be enabled *during* an incident, not as baseline — docs explicitly warn about performance impact.

Protocol defaults to gRPC; HTTP/protobuf via `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf`. All OTel packages bundled with vLLM. Full stack choices (Jaeger all-in-one, OTel Collector → Tempo → Grafana, Langfuse), span catalog, and sampling patterns in `references/tracing.md`.

## Critical pitfalls

1. **Alerting on averages.** `sum/count` hides P99 tails that are 10–50× the mean. Every latency alert must go through `histogram_quantile(0.99, …)`.

2. **Forgetting `sum by (le)` before `histogram_quantile`.** Without it, per-instance quantiles mix with fleet quantiles — the most common Grafana mistake in the Prometheus world.

3. **`gpu_cache_usage_perc` vs `kv_cache_usage_perc`.** The new name shipped first; PR #24245 (merged 2025-09-16) then hid the old `gpu_*` counterparts behind `--show-hidden-metrics-for-version=X.Y`. The attempted revert #25392 was **closed without merging** (2025-09-23), so the hiding stuck — current main emits only `kv_cache_usage_perc` by default. Dashboards scraping pre-#24245 tags still see both; greenfield dashboards should use the new name only.

4. **`num_requests_swapped` is deprecated on V1** and always zero. Use `num_preemptions_total` instead. Many copy-pasted dashboards still reference swap.

5. **Multi-pod label collisions.** Every pod emits identical `{model_name, engine}` labels. Without a Prometheus relabel adding `pod`/`replica`, counters sum across pods and hide per-replica pathology.

6. **Cardinality explosion.** Never add `request_id` or the prompt text as a Prometheus label — that path is deliberately absent. Per-request visibility lives in OTLP traces, not metrics.

7. **KEDA threshold too low on `num_requests_waiting`.** Thresholds of 1–2 per replica cause scale thrashing. Production Stack default is 5; OpenShift example is 2. Pair with `cooldownPeriod: 360` — GPU pods take ~10 min to reach ready, reactive scaling fails.

8. **`GPU_UTIL` at 100% ≠ busy GPU.** The ebpfchirp "11-second TTFT" incident is canonical: util pinned high, SM occupancy was 18%, the scheduler was stalled on prefix-cache head-of-line blocking. Watch `SM_OCCUPANCY`.

9. **Ray Serve deployments don't auto-expose `/metrics`.** `RayPrometheusStatLogger` must be wired explicitly, or Ray 2.51+ ingests vLLM metrics through Ray's own endpoint (disable with `log_engine_metrics: False` to avoid double-scraping).

10. **`--collect-detailed-traces` as baseline.** 5–10% overhead. Toggle per-incident; leave unset by default.

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

## Version notes

- V1 engine is default as of late 2025. V0 metrics hidden unless `--show-hidden-metrics-for-version=X.Y`.
- Metric rename saga: `vllm:gpu_cache_usage_perc` → `vllm:kv_cache_usage_perc`. PR #24245 (merged 2025-09-16) hid the deprecated `gpu_*` names behind `--show-hidden-metrics-for-version`; the proposed revert PR #25392 was **closed without merging** (2025-09-23), so the hiding stuck. Current main emits only `kv_cache_usage_perc` by default.
- Deprecated on V1: `num_requests_swapped`, `cpu_cache_usage_perc`, `cpu_prefix_cache_hit_rate`, `time_per_output_token_seconds` (replaced by `inter_token_latency_seconds`), the `model_forward_time_milliseconds` / `model_execute_time_milliseconds` pair (now behind `--collect-detailed-traces`).
- New in V1: `num_requests_waiting_by_reason{reason=capacity|deferred}`, `engine_sleep_state`, `prompt_tokens_by_source{source=local_compute|local_cache_hit|external_kv_transfer}`, per-position spec-decode acceptance counters.

## External references

- Metrics design doc (canonical): https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md
- Metrics source of truth: https://github.com/vllm-project/vllm/tree/main/vllm/v1/metrics
- Example dashboards: https://github.com/vllm-project/vllm/tree/main/examples/observability
- Production metrics docs: https://docs.vllm.ai/en/stable/usage/metrics/
- OTel POC: https://docs.vllm.ai/en/latest/examples/online_serving/opentelemetry/
- Blog — Anatomy of vLLM (defines goodput, scheduler scoring): https://vllm.ai/blog/anatomy-of-vllm
- Blog — Large-Scale Serving (DeepSeek @ 2.2k tok/s/H200): https://blog.vllm.ai/2025/12/17/large-scale-serving.html
- Blog — MorIIO disagg (bimodal-ITL, goodput framing): https://vllm.ai/blog/moriio-kv-connector
- ebpfchirp — 11-Second TTFT on a Healthy Server (canonical incident): https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on
- akrisanov.com — vLLM Metrics in Production (concrete alert set): https://akrisanov.com/vllm-metrics/
- DCGM exporter + Grafana dashboard 15117: https://grafana.com/grafana/dashboards/15117-nvidia-dcgm-exporter/
- Sibling skills: `vllm-caching` (KV tiering), `vllm-benchmarking` (bench + output JSON), `vllm-configuration` (env vars + YAML)
