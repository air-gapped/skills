# vLLM Prometheus metrics — full catalog

Last verified: 2026-04-24 (see `references/sources.md`)

Load when looking up what a specific `vllm:*` metric means, its type/labels, or when debugging a dashboard/alert. Reflects V1 engine (default on current main); V0 deltas called out.

Source of truth: `vllm/v1/metrics/loggers.py` (primary), `vllm/v1/metrics/stats.py` (data classes), `vllm/v1/spec_decode/metrics.py` (spec decode), `vllm/v1/metrics/perf.py` (MFU).

## Table of contents
- [Labels on every metric](#labels-on-every-metric)
- [Queue & scheduler state](#queue--scheduler-state)
- [KV cache & memory](#kv-cache--memory)
- [Prefix cache](#prefix-cache)
- [Token throughput](#token-throughput)
- [Request outcomes](#request-outcomes)
- [Latency histograms](#latency-histograms)
- [Per-request count histograms](#per-request-count-histograms)
- [Iteration batch histogram](#iteration-batch-histogram)
- [KV block lifetime (sampled)](#kv-block-lifetime-sampled)
- [LoRA](#lora)
- [Speculative decoding](#speculative-decoding)
- [MFU / performance](#mfu--performance)
- [KV connector / offload](#kv-connector--offload)
- [Bucket boundaries](#bucket-boundaries)
- [V0 vs V1 deltas](#v0-vs-v1-deltas)
- [Code anchors](#code-anchors)

## Labels on every metric

Every `vllm:*` series carries:
- `model_name` — value of `--served-model-name` or the model ID
- `engine` — engine-core instance ID (matters in DP; `0` in single-engine)

Additional labels appear on specific series (`finished_reason`, `reason`, `source`, `sleep_state`, `position`). Callouts below where relevant.

## Queue & scheduler state

| Metric | Type | Unit | Extra labels | Meaning |
|---|---|---|---|---|
| `vllm:num_requests_running` | Gauge | count | — | Requests in active model-execution batches |
| `vllm:num_requests_waiting` | Gauge | count | — | Requests waiting for scheduling capacity (sum of waiting + deferred) |
| `vllm:num_requests_waiting_by_reason` | Gauge | count | `reason={capacity,deferred}` | **V1**. `capacity` = blocked by KV/token limits; `deferred` = transient (LoRA budget, KV transfer, blocked) |
| `vllm:num_preemptions_total` | Counter | count | — | Total scheduler preemptions (evictions). Alert on any sustained rate |
| `vllm:engine_sleep_state` | Gauge | binary | `sleep_state={awake,weights_offloaded,discard_all}` | **V1**. 1 = current state, 0 = other states |

Deprecated on V1: `vllm:num_requests_swapped` (always 0).

## KV cache & memory

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `vllm:kv_cache_usage_perc` | Gauge | fraction [0,1] | KV cache utilization. **Includes prefix-cached blocks.** Computed by scheduler, updated each iteration |
| `vllm:cache_config_info` | Gauge (info) | binary | Static cache config; value always 1. Labels expose `num_gpu_blocks`, `num_cpu_blocks`, `block_size`, etc. |

**Rename saga:** The new name `vllm:kv_cache_usage_perc` landed first; PR #24245 (merged 2025-09-16) then hid the deprecated `gpu_*` counterparts behind `--show-hidden-metrics-for-version=X.Y`. Proposed revert #25392 was **closed without merging** (2025-09-23), so the hiding stuck. **Current main emits only `kv_cache_usage_perc` by default.** On fleets still running pre-#24245 tags, use `or` in PromQL; greenfield deployments can drop the fallback:
```promql
vllm:kv_cache_usage_perc or vllm:gpu_cache_usage_perc
```

## Prefix cache

All counters are **token-weighted**, not block-weighted. A cached 2048-token prompt produces 2048 hits, not N-blocks.

| Metric | Type | Meaning |
|---|---|---|
| `vllm:prefix_cache_queries_total` | Counter | Tokens queried against local prefix cache |
| `vllm:prefix_cache_hits_total` | Counter | Tokens reused from local prefix cache |
| `vllm:external_prefix_cache_queries_total` | Counter | Tokens queried against external KV transfer cache (NIXL, LMCache, Mooncake) |
| `vllm:external_prefix_cache_hits_total` | Counter | Tokens reused from external cache |
| `vllm:mm_cache_queries_total` | Counter | Multimodal cache (images/audio) queries |
| `vllm:mm_cache_hits_total` | Counter | Multimodal cache hits |

**Hit rate** (always compute as rate-over-rate, not absolute):
```promql
rate(vllm:prefix_cache_hits_total[5m]) / rate(vllm:prefix_cache_queries_total[5m])
```

## Token throughput

| Metric | Type | Meaning |
|---|---|---|
| `vllm:prompt_tokens_total` | Counter | Prefill tokens actually **computed** (excludes cached/transferred). Use this for throughput math |
| `vllm:prompt_tokens_by_source` | Counter | **V1**. Split by `source={local_compute,local_cache_hit,external_kv_transfer}` |
| `vllm:prompt_tokens_cached_total` | Counter | Tokens reused from any cache. Complement to `prompt_tokens_total` |
| `vllm:generation_tokens_total` | Counter | Decode tokens generated |

**Invariant:** `prompt_tokens_total + prompt_tokens_cached_total = total prompt tokens processed`. For compute/throughput analysis, use `prompt_tokens_total` alone.

## Request outcomes

| Metric | Type | Extra labels | Meaning |
|---|---|---|---|
| `vllm:request_success_total` | Counter | `finished_reason={stop,length,abort}` | Completed requests per reason |
| `vllm:corrupted_requests_total` | Counter | — | Requests with NaN logits. Only emitted when `VLLM_COMPUTE_NANS_IN_LOGITS=1`. **Page on any increment** |

## Latency histograms

All latency values in **seconds**.

| Metric | Covers | Meaning |
|---|---|---|
| `vllm:time_to_first_token_seconds` | arrival → first token | Includes queue time. User-facing TTFT |
| `vllm:request_queue_time_seconds` | WAITING state duration | Pure queue wait; excludes prefill |
| `vllm:request_prefill_time_seconds` | scheduled → first token | Prefill phase only |
| `vllm:request_decode_time_seconds` | first token → last token | Pure decode |
| `vllm:request_inference_time_seconds` | RUNNING state (prefill + decode) | Includes time during any preemption |
| `vllm:e2e_request_latency_seconds` | arrival → last token | Wall-clock end-to-end |
| `vllm:inter_token_latency_seconds` | per-step decode | Token-to-token. Catches stalls that TPOT averages away |
| `vllm:request_time_per_output_token_seconds` | per-request TPOT (excluding first) | Averaged decode per request |

**Enabling the two detailed-trace-only histograms:**

With `--collect-detailed-traces={model,worker,all}`:
- `vllm:model_forward_time_milliseconds` — forward pass
- `vllm:model_execute_time_milliseconds` — model execution incl. sampling

Expensive; toggle per-incident.

## Per-request count histograms

All in tokens. Bucket pattern: `[1, 2, 5, 10, 20, 50, ...]` up to `max_model_len`.

| Metric | Meaning |
|---|---|
| `vllm:request_prompt_tokens` | Prompt tokens per finished request |
| `vllm:request_generation_tokens` | Generation tokens per finished request |
| `vllm:request_max_num_generation_tokens` | `max_tokens` parameter from client |
| `vllm:request_params_n` | `n` parameter (parallel completions) |
| `vllm:request_params_max_tokens` | `max_tokens` parameter histogram |
| `vllm:request_prefill_kv_computed_tokens` | New KV computed during prefill (excludes cached) |

## Iteration batch histogram

| Metric | Buckets | Meaning |
|---|---|---|
| `vllm:iteration_tokens_total` | `[1,8,16,32,64,128,256,512,1024,2048,4096,8192,16384]` | Total tokens per engine iteration (prefill + decode in same batch). Shows batch composition distribution |

Not useful for per-request latency; use for batch-size tuning.

## KV block lifetime (sampled)

Enable with `--kv-cache-metrics` (sample rate `--kv-cache-metrics-sample`, default 0.01).

| Metric | Buckets | Meaning |
|---|---|---|
| `vllm:kv_block_lifetime_seconds` | `[0.001…1800]` | Alloc → eviction time |
| `vllm:kv_block_idle_before_evict_seconds` | `[0.001…1800]` | Idle time before eviction |
| `vllm:kv_block_reuse_gap_seconds` | `[0.001…1800]` | Gap between consecutive accesses to same block (ring buffer, last N only) |

## LoRA

Enable with `--enable-lora`.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `vllm:lora_requests_info` | Gauge (multiproc_mode=sum) | `max_lora`, `waiting_lora_adapters`, `running_lora_adapters` (comma-separated lists) | LoRA occupancy |

**Caveat:** DP + LoRA produces misleading metrics due to multiprocess aggregation.

## Speculative decoding

Enable with `--speculative-config '{"model":...,"num_speculative_tokens":N}'`.

| Metric | Type | Extra labels | Meaning |
|---|---|---|---|
| `vllm:spec_decode_num_drafts_total` | Counter | — | Draft sequences generated |
| `vllm:spec_decode_num_draft_tokens_total` | Counter | — | Total draft tokens |
| `vllm:spec_decode_num_accepted_tokens_total` | Counter | — | Tokens accepted by verifier |
| `vllm:spec_decode_num_accepted_tokens_per_pos` | Counter vector | `position=0..N-1` | Per-draft-position acceptance |

**Acceptance rate:** `rate(vllm:spec_decode_num_accepted_tokens_total[5m]) / rate(vllm:spec_decode_num_draft_tokens_total[5m])`.
Position 0 is ~100% almost always; drop-off at higher positions tells whether draft compute is being wasted.

## MFU / performance

Enable with `--enable-mfu-metrics`.

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `vllm:estimated_flops_per_gpu_total` | Counter | FLOPs | Cumulative estimated FLOPs |
| `vllm:estimated_read_bytes_per_gpu_total` | Counter | bytes | Cumulative read bytes |
| `vllm:estimated_write_bytes_per_gpu_total` | Counter | bytes | Cumulative write bytes |

**MFU:** `rate(vllm:estimated_flops_per_gpu_total[1m]) / (peak_tflops_for_gpu_and_dtype * 1e12)`.
For H200 bf16 peak ≈ 989 TFLOPs, fp8 ≈ 1979 TFLOPs — consult hardware spec, not firmware claims.

## KV connector / offload

Per-backend (native, LMCache, NIXL, Mooncake). Names stabilizing:

| Metric (approx) | Meaning |
|---|---|
| `vllm:kv_offload_total_bytes` | Cumulative bytes offloaded (CPU or NVMe) |
| `vllm:kv_offload_total_time_seconds` | Histogram of offload operation time |
| `vllm:kv_offload_size_bytes` | Current offload buffer size |
| `vllm:nixl_*` / `vllm:hf3fs_*` | Transfer-backend-specific |

Exact names vary by connector version; grep `/metrics` on a running deployment using the connector to see what the installed version emits.

## Bucket boundaries

TTFT (`time_to_first_token_seconds`):
```
[0.001, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 20.0, 40.0, 80.0, 160.0, 640.0, 2560.0]
```

ITL / TPOT (`inter_token_latency_seconds`, `request_time_per_output_token_seconds`):
```
[0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 20.0, 40.0, 80.0]
```

Request-lifetime (`e2e_request_latency_seconds`, `request_queue_time_seconds`, `request_prefill_time_seconds`, `request_decode_time_seconds`, `request_inference_time_seconds`):
```
[0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 60.0, 120.0, 240.0, 480.0, 960.0, 1920.0, 7680.0]
```

Token-count histograms (`request_prompt_tokens`, `request_generation_tokens`, `request_params_max_tokens`, `request_prefill_kv_computed_tokens`):
```
[1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, ...]   # up to max_model_len
```

KV block residency:
```
[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1200, 1800]
```

**SLO calibration warning:** for a P99 TTFT SLO below 250ms, default buckets have coarse resolution there (next break is 0.5s). Adjust if tighter SLOs matter.

## V0 vs V1 deltas

| V0 name | V1 name / fate |
|---|---|
| `vllm:gpu_cache_usage_perc` | → `vllm:kv_cache_usage_perc` (only new name on current main; see rename saga) |
| `vllm:cpu_cache_usage_perc` | Removed (offload model changed) |
| `vllm:cpu_prefix_cache_hit_rate` | Removed |
| `vllm:num_requests_swapped` | Deprecated, always 0 — use `num_preemptions_total` |
| `vllm:time_in_queue_requests` | Duplicate of `request_queue_time_seconds` — removed |
| `vllm:time_per_output_token_seconds` | → `vllm:inter_token_latency_seconds` + `vllm:request_time_per_output_token_seconds` |
| `vllm:model_forward_time_milliseconds` | Now gated behind `--collect-detailed-traces` |
| `vllm:model_execute_time_milliseconds` | Now gated behind `--collect-detailed-traces` |

V0 metrics are hidden by default on V1. Re-enable during migration with `--show-hidden-metrics-for-version=X.Y`.

## Code anchors

For debugging, jumping into the source is fastest:

- Prometheus setup & metric definitions: `vllm/v1/metrics/loggers.py:404-1057`
- Data classes (SchedulerStats, IterationStats): `vllm/v1/metrics/stats.py:18-200`
- Spec decode counters: `vllm/v1/spec_decode/metrics.py:121-215`
- MFU (perf.py): `vllm/v1/metrics/perf.py:1265-1333`
- Tracing init: `vllm/tracing/__init__.py:66-87`, `vllm/tracing/otel.py:60-124`
- ObservabilityConfig: `vllm/config/observability.py:17-153`
- Programmatic metric reader (`llm.get_metrics()`): `vllm/v1/metrics/reader.py:70-143`
- Canonical design doc: `docs/design/metrics.md`
