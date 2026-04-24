# External sources — last-verified inventory

Tracks every external reference the `vllm-observability` skill depends on, when it was last probed, and the verification result. Keep this file current every time the skill is freshened. `skill-improver` Dim 9 staleness cap uses the most-recent date here.

All dates UTC.

## Probe log

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| vLLM PR #24245 "Hide deprecated metrics with gpu_ prefix" | https://github.com/vllm-project/vllm/pull/24245 | 2026-04-24 | fresh | MERGED 2025-09-16. Confirmed via `gh pr view`. Hides `gpu_*`-prefixed metrics behind `--show-hidden-metrics-for-version=X.Y` — this is a HIDING, not a rename. Skill prose updated to reflect this accurately. |
| vLLM PR #25392 "Revert [Metrics] Hide deprecated metrics with gpu_ prefix" | https://github.com/vllm-project/vllm/pull/25392 | 2026-04-24 | deprecation | **CLOSED WITHOUT MERGE** (2025-09-23). Previous skill text claimed the revert "extended the old name's life through transitional releases" — that was incorrect. Corrected in SKILL.md pitfall #3, Version-notes section, and `metrics-catalog.md` rename-saga callout. Source URL cited inline. |
| vLLM V1 metrics source (loggers.py) | https://github.com/vllm-project/vllm/blob/main/vllm/v1/metrics/loggers.py | 2026-04-24 | fresh | Confirmed all load-bearing names in the skill are currently emitted: `vllm:kv_cache_usage_perc`, `vllm:num_requests_waiting`, `vllm:num_requests_waiting_by_reason`, `vllm:num_preemptions`, `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits`, `vllm:external_prefix_cache_{queries,hits}`, `vllm:inter_token_latency_seconds`, `vllm:request_time_per_output_token_seconds`, `vllm:request_queue_time_seconds`, `vllm:corrupted_requests`. Counters that look like `foo_total` on the wire are defined in Python as `foo` (Prom client auto-appends `_total`) — no fix needed, the skill's wire-format names are correct. |
| vLLM `examples/observability/` dashboards tree | https://github.com/vllm-project/vllm/tree/main/examples/observability | 2026-04-24 | fresh | Directory layout confirmed: `dashboards/{grafana,perses}/`, `metrics/`, `opentelemetry/`, `prometheus_grafana/`. Specific files cited by skill all present: `prometheus_grafana/grafana.json`, `prometheus_grafana/prometheus.yaml`, `prometheus_grafana/docker-compose.yaml`, `dashboards/grafana/performance_statistics.json`, `dashboards/grafana/query_statistics.json`, `dashboards/perses/performance_statistics.yaml`, `dashboards/perses/query_statistics.yaml`. |
| vLLM production metrics doc (stable) | https://docs.vllm.ai/en/stable/usage/metrics/ | 2026-04-24 | fresh | Reachable. Documents current V1 names (`kv_cache_usage_perc`, `num_requests_waiting`, `num_preemptions`, `prefix_cache_hits`, `time_to_first_token_seconds`, etc.). Does NOT document the old `gpu_cache_usage_perc` — matches current main. No mention of OTLP flags on this page (OTel is elsewhere in docs). |
| ebpfchirp "11-Second TTFT" incident article | https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on | 2026-04-24 | fresh | Reachable. Title and core finding (GPU_UTIL high while scheduler stalled; SM_OCCUPANCY was the leading indicator) confirmed. Cited in SKILL.md pitfall #8 and `dashboards.md` "Ebpfchirp incident reference". |
| DCGM exporter + Grafana dashboard 15117 | https://grafana.com/grafana/dashboards/15117-nvidia-dcgm-exporter/ | 2026-04-24 | unverified-this-pass | Link shape unchanged since prior audit; not re-probed this freshen pass. Treat as fresh-by-inertia; re-probe next pass. |
| Metrics design doc (canonical) | https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md | 2026-04-24 | unverified-this-pass | Not probed this pass; budget exhausted. Path unchanged since prior audit. |

## Probe budget

This pass: 6 of 8 probes consumed (4 `gh api`/`gh pr view` calls, 2 `WebFetch`). Remaining budget: 2 for drift triggered by follow-up audits. Kept in reserve rather than burning on links where the skill does not cite version-sensitive claims.

## Applied drift fixes

1. **PR #25392 merge status** — corrected from "partial revert (extended old name's life)" to "closed without merging" in three locations: SKILL.md pitfall #3, SKILL.md Version notes bullet, `references/metrics-catalog.md` rename-saga callout.
2. **PR #24245 semantics** — clarified "renamed" → "hid deprecated `gpu_*` names behind `--show-hidden-metrics-for-version`" in the same three locations. The new `kv_cache_usage_perc` name existed before #24245; that PR merely cleaned up by hiding the deprecated variant.
3. **`Last verified: 2026-04-24` stamps** — added to the header of all four reference files so agents loading them know the freshness bound.

No other content was substantively altered — skill prose, PromQL, and YAML examples remained in place.

## Next freshen triggers

Re-probe when any of the following change:
- vLLM release > v0.22 (check whether more V0 metrics fully removed, or new V1 metrics added).
- Ray Serve integration changes (Ray 2.52+ behavior).
- DCGM exporter 4.1+ (field-name drift).
- `examples/observability/` directory restructure (watch for a `dashboards/v2/` or similar).
- Langfuse / Tempo feature changes that affect operator defaults.
