# vLLM Prometheus metrics — full catalog

Last verified: 2026-08-11 against vLLM **v0.27.0** (see `references/sources.md`). Every metric name in this file was diffed against the `name="vllm:..."` declarations in `vllm/v1/metrics/loggers.py` at that tag — **the emitted set is identical to v0.25.1**: no name removed, none renamed, `gpu_cache_usage_perc` still absent by default (0 occurrences). Additions from v0.24.0/v0.25.0 remain folded in: `vllm:tool_call_parser_invocations_total`, the group-aware `cache_config_info` labels, `MLAAttentionMetrics`, and the per-request response-body `metrics` field. **The § KV connector / offload names were corrected on 2026-08-11** — they had been approximations, and two of the three were misspelled; they are now read from the v0.27.0 source.

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
- [Tool-call parsing](#tool-call-parsing)
- [Per-request timing in the response body (not Prometheus)](#per-request-timing-in-the-response-body-not-prometheus)
- [Speculative decoding](#speculative-decoding)
- [MFU / performance](#mfu--performance)
- [Observability switches that never reach /metrics](#observability-switches-that-never-reach-metrics)
- [Rust frontend](#rust-frontend)
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
| `vllm:request_num_preemptions` | Histogram | count | — | Per-request preemption count, buckets 1,2,3,4,5,10,20. **New in v0.30.0** ([#49984](https://github.com/vllm-project/vllm/pull/49984)) — use it to tell "a few requests preempted repeatedly" from "many preempted once", which the counter above cannot |
| `vllm:engine_sleep_state` | Gauge | binary | `sleep_state={awake,weights_offloaded,discard_all}` | **V1**. 1 = current state, 0 = other states |

Deprecated on V1: `vllm:num_requests_swapped` (always 0).

## KV cache & memory

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `vllm:kv_cache_usage_perc` | Gauge | fraction [0,1] | KV cache utilization. **Includes prefix-cached blocks.** Computed by scheduler, updated each iteration |
| `vllm:cache_config_info` | Gauge (info) | binary | Static cache config; value always 1. Labels expose `num_gpu_blocks`, `num_cpu_blocks`, `block_size`, and — since v0.24.0 — `kv_cache_size_tokens` and `kv_cache_max_concurrency` |

**Don't compute KV capacity as `num_gpu_blocks * block_size` — it is wrong on
hybrid models.** vLLM's startup log has always reported the correct
*group-aware* capacity, but Prometheus did not expose a matching figure, so
dashboards derived it from the block labels and silently disagreed with the
log (issue #42024). PR #42206 (merged 2026-06-12, **v0.24.0**) closes the gap
by adding two labels computed the same way the startup log computes them:

| Label | Meaning |
|---|---|
| `kv_cache_size_tokens` | Per-DP-engine KV cache capacity in tokens, group-aware |
| `kv_cache_max_concurrency` | Per-DP-engine max concurrency at `max_model_len` tokens |

On a hybrid model a request can occupy blocks in **multiple KV cache groups**,
so the naive product overstates capacity. Prefer the labels; keep the product
only as a fallback for pre-v0.24.0 engines, and expect the two to disagree
there rather than assuming one is a bug.

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

## Tool-call parsing

| Metric | Type | Extra labels | Meaning |
|---|---|---|---|
| `vllm:tool_call_parser_invocations_total` | Counter | `mode={streaming,non-streaming}`, `outcome={tool call, no tool call}`, request type (`ChatCompletionRequest` \| `ResponsesRequest`) | How often the tool parser ran and whether it produced a tool call |

Added by PR #44448 (merged 2026-06-10, **v0.24.0**), recorded in
`DelegatingParser`. The point of it is rollout safety: a model or template
change that quietly stops emitting parseable tool calls shows up here as the
`outcome` ratio collapsing, while request-level metrics stay flat and healthy.

```promql
# fraction of parser invocations that produced no tool call
sum(rate(vllm:tool_call_parser_invocations_total{outcome!="tool call"}[5m]))
  / sum(rate(vllm:tool_call_parser_invocations_total[5m]))
```

**Coverage limit stated upstream:** the **non-harmony path only** — harmony
does not go through `DelegatingParser`, so a harmony deployment sees no
increments and the ratio above is not a valid health signal there.

## Per-request timing in the response body (not Prometheus)

PR #46768 (merged 2026-07-07, **v0.25.0**) adds a top-level `metrics` field to
Chat/Completions responses, streaming and non-streaming:
`time_to_first_token_ms`, `generation_time_ms`, `queue_time_ms`, `mean_itl_ms`,
`tokens_per_second`. Motivating use cases in the RFE (#40076) are billing,
SLAs, experimentation, and debugging — cases where per-request attribution
matters and a Prometheus histogram cannot help.

**Double-gated**, so it is off unless deliberately turned on at both levels:

1. server flag `--enable-per-request-metrics`
2. request body parameter `include_metrics`

**Suppressed when attribution to a single generation stream isn't meaningful**
— e.g. `n > 1` or multi-prompt requests. Absent fields there are by design;
don't treat a missing `metrics` block as a bug before checking request shape.

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

**MFU on MLA models was wrong before v0.24.0.** The estimator's
`AttentionMetrics` assumed MHA/GQA — separate K/V projections and a KV cache
sized `2 * num_kv_heads * head_dim` per token per layer. MLA (DeepSeek-V2/V3/R1)
stores a single compressed `(kv_lora_rank + qk_rope_head_dim)` vector instead:
for DeepSeek-V3 that is **576 bytes per token per layer versus 32,768** under
the GQA assumption — a ~57× overestimate of KV bandwidth. PR #39457 (merged
2026-06-12, **v0.24.0**) adds `MLAAttentionMetrics` to model it correctly.
Treat any MFU or bandwidth figure collected from a DeepSeek deployment on
**< v0.24.0** as unusable, not merely imprecise.

**MFU/MBU on sliding-window and hybrid-attention models was overestimated
before v0.30.0.** The estimator summed `num_tokens * context_len` using the
full, unclamped context length for every layer, including SWA layers that
only ever attend to the last `sliding_window` tokens — inflating
`attn_qk`/`attn_av` FLOPs and KV read/write bytes on long-context requests for
Mistral, Qwen2.5, Gemma 2/3n, Llama 4, and hybrid Mamba models. PR #55624
(merged 2026-09-14, **v0.30.0**) clamps per-layer context length to
`sliding_window` via a new `num_swa_layers` split in `AttentionMetrics`.
Discard MFU/MBU history from SWA/hybrid deployments on **< v0.30.0** for
long-context workloads — short-context traffic was unaffected, since the
clamp only changes anything once `context_len > sliding_window`.

## Observability switches that never reach `/metrics`

`ObservabilityConfig` carries several operator-visible switches whose output is
**log-only**. Turning one on and then grepping `/metrics` for it is a wasted
half-hour, so the first column below is the one that matters. All are read from
`vllm/config/observability.py` and exposed as CLI flags in
`vllm/engine/arg_utils.py` (verified at upstream `main`, 2026-09-15).

| Flag | Output | What it gives you |
|---|---|---|
| `--cudagraph-metrics` | **log only** | Padded/unpadded token counts, runtime cudagraph dispatch modes, and their observed frequencies, at every logging interval |
| `--enable-layerwise-nvtx-tracing` | **NVTX ranges** | Per-layer/module ranges annotated with input/output shapes, for Nsight. **Does not work with CUDA graphs enabled** — a real constraint, not a caveat |
| `--enable-logging-iteration-details` | **log only** | Per-iteration context/generation request and token counts, plus elapsed CPU time |
| `--jit-monitor-mode` (`warn`\|`error`) | **log only** | How to handle post-warmup JIT compilation events. `error` turns a late recompile into a failure instead of a line nobody reads |
| `--jit-monitor-verbose` | **log only** | Every monitored JIT compile with runtime detail. Emits many logs and adds overhead — debugging only |

`--enable-mfu-metrics` is the exception in this family: it **does** produce
Prometheus series (see § MFU / performance above).

**`enable_mm_processor_stats` is not a CLI flag.** It collects multimodal
processor timings and its own docstring says it is for internal use, e.g.
benchmarks. If a config-file or env approach appears to set it, that is not a
supported operator surface.

## Rust frontend

Engine-core metrics registered by the Rust frontend (`vllm serve --grpc`, the
render/derender path) reuse the **same `vllm:`-prefixed names** as the Python
engine — `vllm:num_requests_running`, `vllm:kv_cache_usage_perc`,
`vllm:iteration_tokens_total`, and (as of **v0.30.0**,
[#52755](https://github.com/vllm-project/vllm/pull/52755)) the Mooncake/NIXL
KV-connector histograms `vllm:mooncake_store_operation_time_seconds` and
`vllm:nixl_xfer_time_seconds` — so the PromQL in this catalog applies
unchanged regardless of frontend. `vllm:iteration_tokens_total` on the Rust
frontend is new in v0.30.0 too
([#56990](https://github.com/vllm-project/vllm/pull/56990)); before that PR it
only existed on the Python engine.

HTTP-layer metrics (`http_requests_total`, `http_request_duration_seconds`)
are **not** `vllm:`-prefixed and mirror `PrometheusFastApiInstrumentator`
naming. Their `method` label is bounded to known HTTP verbs plus `other`
since v0.30.0 ([#56058](https://github.com/vllm-project/vllm/pull/56058),
a security fix); before it, an arbitrary request method string on the wire
became the label value directly — the same unbounded-cardinality failure
mode as pitfall 6 above, just on the Rust frontend's own metric family.

**Why this matters beyond the flags themselves:** "vLLM has a metric for X" and
"vLLM can tell you X" are different claims. Three of the five above answer real
operator questions — is the cudagraph dispatch doing what I configured, is
something recompiling after warmup — and none of them will ever appear on a
dashboard. Reach for the logs, or for `--jit-monitor-mode error` to turn a
silent regression into a loud one.

## KV connector / offload

**These names were guessed in earlier revisions of this catalog and two of the
three were wrong.** The set below is read verbatim from the v0.27.0 tree —
`vllm/distributed/kv_transfer/kv_connector/v1/offloading/metrics.py`,
`vllm/v1/kv_offload/cpu/common.py`, `vllm/v1/kv_offload/tiering/base.py`.

Transfer metrics are **split by direction**, not aggregated (declared names; the
Prometheus client appends `_total` to counters on the wire, as elsewhere in this
catalog):

| Metric | Type | Meaning |
|---|---|---|
| `vllm:kv_offload_load_bytes` | Counter | Bytes loaded back from the offload tier (CPU→GPU) |
| `vllm:kv_offload_store_bytes` | Counter | Bytes stored to the offload tier (GPU→CPU) |
| `vllm:kv_offload_load_time` | Counter | Cumulative time in load operations |
| `vllm:kv_offload_store_time` | Counter | Cumulative time in store operations |
| `vllm:kv_offload_load_size` | Histogram | Load operation size, in bytes |
| `vllm:kv_offload_store_size` | Histogram | Store operation size, in bytes |
| `vllm:kv_offload_lookup_sync_delay_seconds` | Histogram | Time inside a single offload lookup call |
| `vllm:kv_offload_lookup_async_delay_seconds` | Histogram | Time from a request's lookup first deferring until it resolves |
| `vllm:kv_offload_allocation_failure` | Counter | Store allocation attempts that failed |

CPU-tier gauges (`CPUOffloadingMetrics`) — the read/write split arrived in
**v0.26.0 (#47666)** and is the one worth alerting on, because it separates
back-pressure on the write path from stall on the read path:

| Metric | Type | Meaning |
|---|---|---|
| `vllm:kv_offload_cpu_cache_usage_perc` | Gauge | CPU cache space pinned by any in-flight transfer. **Equals write + read** |
| `vllm:kv_offload_cpu_cache_write_usage_perc` | Gauge | Fraction pinned by in-flight stores (GPU→CPU) not yet complete |
| `vllm:kv_offload_cpu_cache_read_usage_perc` | Gauge | Fraction pinned by in-flight loads (CPU→GPU) not yet complete |
| `vllm:kv_offload_cpu_allocation_size` | — | CPU-tier allocation size |
| `vllm:kv_offload_stores_skipped` | Counter | Stores skipped |

Tiering metrics (`TieringOffloadingMetrics`), added by **v0.26.0 (#47679)** —
note these are a *different* pair from the connector-level lookup delays above:

| Metric | Meaning |
|---|---|
| `vllm:kv_offload_tiering_lookup_sync_delay_seconds` | Cost of a single secondary-tier lookup call |
| `vllm:kv_offload_tiering_lookup_async_delay_seconds` | Total time a request's lookup stays deferred across a tier promotion — first RETRY until resolved (or the request finishes unresolved) |
| `vllm:kv_offload_tiering_read_bytes` / `_read_time` | Bytes read from, and time spent reading from, the secondary tier |
| `vllm:kv_offload_tiering_write_bytes` / `_write_time` | Same for writes to the secondary tier |
| `vllm:kv_offload_tiering_chunk_queries` / `_chunk_hits` | Secondary-tier chunk lookups and hits — the tier's own hit rate, distinct from the engine's prefix-cache hit rate. **Renamed from `block_queries`/`block_hits`** |
| `vllm:kv_offload_tiering_primary_read_usage_perc` / `_primary_write_usage_perc` | Occupancy of the primary tier's read and write paths |
| `vllm:kv_offload_tiering_active_promotion_jobs` / `_active_cascade_jobs` | In-flight promotion and cascade jobs |
| `vllm:kv_offload_tiering_promotion_job_failures` / `_cascade_job_failures` / `_promotion_allocation_failures` | Failure counters — watch these first when tiering silently stops helping |

**The 13 names above ship from v0.28.0 and do not exist before it.** Counted in `vllm/v1/kv_offload/tiering/base.py`: 2 names at v0.27.0, 15 at v0.28.0. On v0.27.x only the two `lookup_*_delay_seconds` metrics exist, so a dashboard built from this table will render empty panels there.

**Three legacy names are deprecated, and the two this catalog previously
published were misspelled.** Actual deprecated names are
`vllm:kv_offload_total_bytes`, **`vllm:kv_offload_total_time`** (not
`…_total_time_seconds`) and **`vllm:kv_offload_size`** (not `…_size_bytes`).
They carry a `transfer_type` label instead of splitting into separate series,
and they are **only observed when the offloading spec is a `CPUOffloadingSpec`**
(`_observe_deprecated_metrics = issubclass(spec_cls, CPUOffloadingSpec)`) — on
any other spec they are registered but never incremented, so a dashboard built
on them goes flat rather than erroring. Migrate to the load/store split.

**NIXL connector series are documented upstream** and no longer need guessing
(https://docs.vllm.ai/en/stable/usage/metrics/, probed 2026-08-11):
`vllm:nixl_bytes_transferred`, `vllm:nixl_xfer_time_seconds`,
`vllm:nixl_post_time_seconds`, `vllm:nixl_num_descriptors`,
`vllm:nixl_num_failed_transfers`, `vllm:nixl_num_failed_notifications`,
`vllm:nixl_num_kv_expired_reqs`. The two failure counters and the expired-request
counter are the alertable ones on a disaggregated deployment.

**HiSparse connector counters**, new in **v0.30.0**
([#56061](https://github.com/vllm-project/vllm/pull/56061)), only emit when
`HiSparseConnector` is the configured KV connector — the host-resident
sparse-MLA decode tier introduced this release:

| Metric | Type | Meaning |
|---|---|---|
| `vllm:hisparse_cache_hits_total` | Counter | Device hot-buffer hits |
| `vllm:hisparse_cache_misses_total` | Counter | Device hot-buffer misses |
| `vllm:hisparse_host_to_device_bytes_total` | Counter | Bytes moved from host KV storage into hot buffers |

Other backends (`vllm:hf3fs_*`, LMCache, Mooncake) remain
connector-version-dependent — grep `/metrics` on a running deployment to see what
the installed connector actually emits.

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
