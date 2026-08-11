# External sources — last-verified inventory

Tracks every external reference the `vllm-observability` skill depends on, when it was last probed, and the verification result. Keep this file current every time the skill is freshened. `skill-improver` Dim 9 staleness cap uses the most-recent date here.

All dates UTC.

## Probe log

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| vLLM PR #24245 "Hide deprecated metrics with gpu_ prefix" | https://github.com/vllm-project/vllm/pull/24245 | 2026-05-28 | fresh | Re-confirmed `gh pr view`: state=MERGED, mergedAt=2025-09-16. Hides `gpu_*`-prefixed metrics behind `--show-hidden-metrics-for-version=X.Y` — a HIDING, not a rename. Terminal state. |
| vLLM PR #25392 "Revert [Metrics] Hide deprecated metrics with gpu_ prefix" | https://github.com/vllm-project/vllm/pull/25392 | 2026-05-28 | deprecation | Re-confirmed `gh pr view`: state=CLOSED, mergedAt=null, closedAt=2025-09-23. Revert never merged, so the hiding stuck. Terminal state. |
| vLLM V1 metrics source (loggers.py) | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/v1/metrics/loggers.py | 2026-07-21 | fresh | Re-probed at **tag v0.25.1** (1365 lines, was 1359 on main at the 2026-05-28 pass). Extracted every `name="vllm:..."` declaration and diffed against this skill's catalog: **no catalogued name removed or renamed**; `gpu_cache_usage_perc` still 0 occurrences. Emitted set: `corrupted_requests`, `e2e_request_latency_seconds`, `engine_sleep_state`, `external_prefix_cache_{hits,queries}`, `generation_tokens`, `inter_token_latency_seconds`, `iteration_tokens_total`, `kv_block_{idle_before_evict,lifetime,reuse_gap}_seconds`, `kv_cache_usage_perc`, `lora_requests_info`, `mm_cache_{hits,queries}`, `num_preemptions`, `num_requests_{running,waiting}`, `num_requests_waiting_by_reason`, `prefix_cache_{hits,queries}`, `prompt_tokens`, `prompt_tokens_by_source`, `prompt_tokens_cached`, `request_decode_time_seconds`, `request_generation_tokens`, `request_inference_time_seconds`, `request_max_num_generation_tokens`, `request_params_{max_tokens,n}`, `request_prefill_kv_computed_tokens`, `request_prefill_time_seconds`, `request_prompt_tokens`, `request_queue_time_seconds`, `request_success`, `request_time_per_output_token_seconds`, `time_to_first_token_seconds`. |
| _(superseded row — loggers.py on main)_ | https://github.com/vllm-project/vllm/blob/main/vllm/v1/metrics/loggers.py | 2026-05-28 | fresh | Re-probed `gh api contents` on main (1359 lines): all load-bearing names emitted — `vllm:kv_cache_usage_perc`, `vllm:num_requests_waiting`, `vllm:num_requests_waiting_by_reason`, `vllm:num_preemptions`, `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits`, `vllm:external_prefix_cache_{queries,hits}`, `vllm:inter_token_latency_seconds`, `vllm:request_time_per_output_token_seconds`, `vllm:request_queue_time_seconds`, `vllm:corrupted_requests`. `gpu_cache_usage_perc` NOT emitted (0 occurrences). Counters defined bare in Python (`foo`); Prom client appends `_total` on the wire — skill's wire-format names are correct. |
| vLLM `examples/observability/` dashboards tree | https://github.com/vllm-project/vllm/tree/main/examples/observability | 2026-05-28 | fresh | Re-probed `gh api contents`: top level `dashboards/`, `metrics/`, `opentelemetry/`, `prometheus_grafana/`. `dashboards/grafana/` = `performance_statistics.json` + `query_statistics.json` (+ README). All files cited by skill present. |
| vLLM production metrics doc (stable) | https://docs.vllm.ai/en/stable/usage/metrics/ | 2026-08-11 | fresh / **new names harvested** | HTTP 200. Re-scraped the `vllm:*` names: documents current V1 names and still does NOT document `gpu_cache_usage_perc`. **New this pass:** the page carries concrete NIXL-connector series — `vllm:nixl_bytes_transferred`, `nixl_xfer_time_seconds`, `nixl_post_time_seconds`, `nixl_num_descriptors`, `nixl_num_failed_transfers`, `nixl_num_failed_notifications`, `nixl_num_kv_expired_reqs` — which replaced the catalog's `vllm:nixl_*` wildcard. Also confirms `vllm:estimated_{flops,read_bytes,write_bytes}_per_gpu_total`. |
| ebpfchirp "11-Second TTFT" incident article | https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on | 2026-08-11 | fresh | HTTP 200 (`curl -L`). URL still resolves; cited in SKILL.md pitfall #8 and `dashboards.md` "Ebpfchirp incident reference". |
| DCGM exporter + Grafana dashboard 15117 | https://grafana.com/grafana/dashboards/15117-nvidia-dcgm-exporter/ | 2026-08-11 | fresh | HTTP 200 (`curl -L`). Carried at 2026-04-24 through two passes; finally re-probed. |
| Metrics design doc (canonical) | https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md | 2026-08-11 | fresh | Fetched raw at **v0.27.0** (702 lines). Mentions `kv_cache_usage_perc`; `gpu_cache_usage_perc` appears **0 times** — independently corroborates the rename-saga conclusion from a second source. |
| vLLM V1 metrics source (loggers.py) @ v0.27.0 | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/v1/metrics/loggers.py | 2026-08-11 | fresh | Re-probed at **tag v0.27.0** (1402 lines, was 1365 at v0.25.1). Extracted every `name="vllm:..."` declaration and diffed against the v0.25.1 set recorded above: **identical — 37 names, none added, none removed, none renamed**; `gpu_cache_usage_perc` still 0 occurrences. The file grew 37 lines without changing its metric surface. |
| KV-offload metric names (3 source files) | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/distributed/kv_transfer/kv_connector/v1/offloading/metrics.py | 2026-08-11 | **broken → corrected** | The catalog's "approx" offload names were **wrong**: actual deprecated names are `vllm:kv_offload_total_time` (catalog said `…_total_time_seconds`) and `vllm:kv_offload_size` (catalog said `…_size_bytes`). Read the real set from `offloading/metrics.py`, `vllm/v1/kv_offload/cpu/common.py` and `vllm/v1/kv_offload/tiering/base.py` at v0.27.0. Current surface is a direction-split `kv_offload_{load,store}_{bytes,time,size}` plus `lookup_{sync,async}_delay_seconds` and `allocation_failure`; the three legacy `total_*`/`size` names are deprecated, carry a `transfer_type` label, and are only observed when the spec is a `CPUOffloadingSpec`. |

## Probe budget

This pass: 6 of 8 probes consumed (4 `gh api`/`gh pr view` calls, 2 `WebFetch`). Remaining budget: 2 for drift triggered by follow-up audits. Kept in reserve rather than burning on links where the skill does not cite version-sensitive claims.

## Applied drift fixes

1. **PR #25392 merge status** — corrected from "partial revert (extended old name's life)" to "closed without merging" in three locations: SKILL.md pitfall #3, SKILL.md Version notes bullet, `references/metrics-catalog.md` rename-saga callout.
2. **PR #24245 semantics** — clarified "renamed" → "hid deprecated `gpu_*` names behind `--show-hidden-metrics-for-version`" in the same three locations. The new `kv_cache_usage_perc` name existed before #24245; that PR merely cleaned up by hiding the deprecated variant.
3. **`Last verified: 2026-04-24` stamps** — added to the header of all four reference files so agents loading them know the freshness bound.

No other content was substantively altered — skill prose, PromQL, and YAML examples remained in place.

## 2026-07-21 freshen — new metrics found (v0.24.0 / v0.25.0)

The 2026-05-28 trigger ("re-probe when vLLM release > v0.22") fired: latest is
now **v0.25.1** (2026-07-14). Four additions, two of which mean previously
collected data was wrong rather than merely incomplete.

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| PR #42206 — group-aware KV capacity in `cache_config_info` | https://github.com/vllm-project/vllm/pull/42206 | 2026-07-21 | new-feature / **corrects prior dashboards** | Merged 2026-06-12, v0.24.0. Fixes the Prometheus-vs-startup-log discrepancy in issue #42024. Adds labels `kv_cache_size_tokens` and `kv_cache_max_concurrency`, both per-DP-engine and group-aware. Upstream states plainly that `num_gpu_blocks * block_size` "can be wrong for hybrid models where requests occupy multiple KV cache groups" — i.e. any dashboard deriving capacity that way has been overstating it. Applied to `metrics-catalog.md` § KV cache. |
| PR #39457 — `MLAAttentionMetrics` for DeepSeek MFU | https://github.com/vllm-project/vllm/pull/39457 | 2026-07-21 | new-feature / **invalidates prior MFU on MLA** | Merged 2026-06-12, v0.24.0. The old `AttentionMetrics` assumed MHA/GQA with a `2 * num_kv_heads * head_dim` KV footprint; MLA stores one compressed `(kv_lora_rank + qk_rope_head_dim)` vector. For DeepSeek-V3 that is **576 vs 32,768 bytes per token per layer** — a ~57× bandwidth overestimate. MFU collected from a DeepSeek deployment on < v0.24.0 is unusable. Applied to `metrics-catalog.md` § MFU. |
| PR #44448 — `vllm:tool_call_parser_invocations_total` | https://github.com/vllm-project/vllm/pull/44448 | 2026-07-21 | new-feature | Merged 2026-06-10, v0.24.0. Counter recorded in `DelegatingParser`, labelled by `mode` (streaming/non-streaming), `outcome` (tool call / no tool call), and request type. Rollout-regression signal for tool calling. **Upstream-stated limit: non-harmony path only** — harmony does not route through `DelegatingParser`. New `metrics-catalog.md` § Tool-call parsing. |
| PR #46768 — per-request `metrics` field on Chat/Completions responses | https://github.com/vllm-project/vllm/pull/46768 | 2026-07-21 | new-feature | Merged 2026-07-07, v0.25.0. RFE #40076 (billing, SLAs, experimentation, debugging). Fields: `time_to_first_token_ms`, `generation_time_ms`, `queue_time_ms`, `mean_itl_ms`, `tokens_per_second`. **Double-gated** by `--enable-per-request-metrics` *and* the `include_metrics` request parameter; suppressed when single-stream attribution isn't meaningful (`n > 1`, multi-prompt). New `metrics-catalog.md` section — this is response-body data, not Prometheus. |

Also noted, not applied (KV-connector metric names remain "stabilizing" in the
catalog and none of these change a documented name): offloading-manager stats
(#35669) and labeled/CPU-usage metrics (#45957, #45737) in v0.24.0, KV tiering
metric plumbing (#45959) in v0.25.0, Mooncake operation metrics (#43392) in
v0.22.0.

## 2026-08-11 freshen — the catalog's own names were the finding

The 2026-07-21 trigger fired twice over: **v0.26.0** (2026-07-27) and **v0.27.0**
(2026-08-10). The prescribed `loggers.py` name diff ran first and came back
clean — 37 names, identical to v0.25.1. That is a real result, but it also means
the cheap mechanical check had reached the end of what it can catch, because the
metric churn in these two releases happened **outside `loggers.py`**, in the KV
offload namespace.

Going there found the pass's only `broken` classification, and it was
self-inflicted: the § KV connector / offload table had been published with names
marked "(approx)", and **two of the three were misspelled** —
`vllm:kv_offload_total_time_seconds` and `vllm:kv_offload_size_bytes` do not
exist and never did; the real names are `vllm:kv_offload_total_time` and
`vllm:kv_offload_size`. An "(approx)" hedge on a metric name is not a hedge — a
PromQL query built on it returns no data, silently. All three are now deprecated
anyway, superseded by a direction-split load/store set.

**Process lesson for the next pass:** a metric catalog can be simultaneously
"verified against the source" and wrong, if the verification only covers the file
the previous pass happened to check. Diff `loggers.py` *and* enumerate the metric
name constants under `vllm/v1/kv_offload/` and
`vllm/distributed/kv_transfer/kv_connector/v1/offloading/`.

Also cleared: the four non-GitHub rows that had been carried unprobed since
2026-04-24 through two passes. All four return HTTP 200, and the docs.vllm.ai
page turned out to carry the concrete NIXL series that replaced another wildcard
in the catalog — the deferred probe was hiding a content improvement, not just a
staleness risk.

## Next freshen triggers

Re-probe when any of the following change:
- vLLM release > v0.27.1 (current latest, 2026-08-11; this pass probed the v0.27.0 tree — v0.27.1 is a one-change patch touching only `vllm/model_executor/models/qwen3_dspark.py`, no metric surface). Run the loggers.py name diff **and** the kv_offload constant sweep — the diff alone was clean across two minors that did change the offload surface.
- Ray Serve integration changes (Ray 2.52+ behavior).
- DCGM exporter 4.1+ (field-name drift).
- `examples/observability/` directory restructure (watch for a `dashboards/v2/` or similar).
- Langfuse / Tempo feature changes that affect operator defaults.
