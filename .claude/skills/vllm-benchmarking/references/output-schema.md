# `--output-json` schema

Last verified: 2026-09-23 (against `vllm/benchmarks/serve.py` at tag **v0.30.0**).

Load when parsing benchmark output JSON, building dashboards, or diffing A/B runs.

## Top-level fields (always present in `bench serve`)

| Field | Type | Source |
|---|---|---|
| `date` | string | Run timestamp (ISO) |
| `backend` | string | Value of `--backend` |
| `endpoint_type` | string | Same value as `backend`, emitted "for backward compatibility" |
| `label` | string | Value of `--label` if set, else model short name |
| `model_id` | string | `--model` value |
| `tokenizer_id` | string | `--tokenizer` value, defaults to `model_id` |
| `num_prompts` | int | `--num-prompts` |
| `request_rate` | float or string | The requested rate; `"inf"` when unset |
| `burstiness` | float | `--burstiness`, default 1.0 |
| `max_concurrency` | int or null | `--max-concurrency` |

If ramp-up is enabled, adds `ramp_up_strategy`, `ramp_up_start_rps`, `ramp_up_end_rps`.

Custom KV pairs from `--metadata KEY=VALUE` are inlined at the top level.

## Throughput fields (generative models, `BenchmarkMetrics`)

| Field | Unit | Meaning |
|---|---|---|
| `request_throughput` | req/s | Completed requests per wall second |
| `output_throughput` | tok/s | **Decode tokens only** — excludes prefill |
| `total_token_throughput` | tok/s | Input tokens + output tokens over wall time |

Pooling/embedding runs (`EmbedBenchmarkMetrics`) emit `completed`, `failed`, `total_input`, `total_input_sequences`, `request_throughput`, `input_sequence_throughput` (inputs/s), `total_token_throughput`, plus `mean_/median_/std_/p<N>_e2el_ms` (the only percentile metric pooling supports). **v0.30.0+ (#56760):** E2EL for pooling is now measured after the full response body is drained, not when headers arrive — binary (`bytes`) responses were previously never consumed, so their reported latency excluded transfer time and undercounted. A new `bytes_only` encoding format (server returns the embedding as a raw byte stream with no JSON/metadata wrapper) is also now handled — previously every `bytes_only` request failed because it was parsed as JSON.

Also present in `bench serve` output (added since v0.19):
- `request_goodput` — only when `--goodput` is set; otherwise `null`.
- `max_output_tokens_per_s` — peak instantaneous output-token rate observed.
- `max_concurrent_requests` — observed concurrency peak across the run.
- `rtfx` — real-time factor for audio/streaming workloads.
- `start_times` — per-request start timestamps (appears alongside `ttfts`/`itls`).
- `latencies`, `queue_times` (v0.30.0+, #54136) — per-request `list[float]` seconds, present unconditionally (not just under `--save-detailed`) for both generative and pooling results. `latencies[i]` is total request latency; `queue_times[i]` is time spent waiting on the client's `--max-concurrency` semaphore before the request was sent (0.0 when `--max-concurrency` is unset).

## Percentile fields

For each metric in `--percentile-metrics` (default `ttft,tpot,itl`; `e2el` for pooling), the output contains:

```
mean_<metric>_ms
median_<metric>_ms
std_<metric>_ms
p<N>_<metric>_ms    # one per value in --metric-percentiles
```

Example for `--percentile-metrics ttft,tpot --metric-percentiles 50,95,99`:
```
mean_ttft_ms, median_ttft_ms, std_ttft_ms, p50_ttft_ms, p95_ttft_ms, p99_ttft_ms,
mean_tpot_ms, median_tpot_ms, std_tpot_ms, p50_tpot_ms, p95_tpot_ms, p99_tpot_ms
```

Metrics:
- `ttft` — time-to-first-token
- `tpot` — mean time-per-output-token per request
- `itl` — inter-token latency (per-step, finer than tpot)
- `e2el` — end-to-end request latency
- `client_queue_time`, `e2el_including_client_queue` (v0.30.0+, #54136) — client-side semaphore wait, and E2EL plus that wait. Unlike the metrics above these are computed directly from the `queue_times`/`latencies` per-request lists rather than read off the engine's `BenchmarkMetrics`/`EmbedBenchmarkMetrics` object. Both need `--max-concurrency` set; `e2el_including_client_queue` additionally needs `--request-rate` finite. Neither appears unless named explicitly in `--percentile-metrics`.

## Speculative decoding fields (if engine emits them)

Present only when spec decode is active on the server:

```
spec_decode_acceptance_rate              float
spec_decode_acceptance_length            float
spec_decode_num_drafts                   int
spec_decode_draft_tokens                 int
spec_decode_accepted_tokens              int
spec_decode_per_position_acceptance_rates  list[float]
```

Useful for evaluating P-EAGLE / Medusa / MTP configurations.

## `--save-detailed` additions

Adds per-request records (one entry per prompt):

```
input_lens          list[int]
output_lens         list[int]
ttfts               list[float]   # seconds
itls                list[list[float]]  # per-request, per-step
generated_texts     list[str]
errors              list[str]     # empty string = success
```

Large file — use for forensic analysis after a failed run, not for routine reporting.

## Stable vs version-sensitive fields

**Stable across v0.11 → v0.27:**
- `request_throughput`, `output_throughput`, `total_token_throughput`
- `mean_<metric>_ms`, `median_<metric>_ms`, `std_<metric>_ms`, `p<N>_<metric>_ms`
- `num_prompts`, `request_rate`, `max_concurrency`

**Added or renamed in recent versions:**
- `endpoint_type` — **correction (2026-08-11): this field was never removed.** A prior revision of this file claimed it was dropped from the JSON assembly; re-reading `serve.py` at tags v0.21.0, v0.24.0, v0.25.1, v0.26.0 and v0.27.0 shows an unconditional `result_json["endpoint_type"] = args.backend  # for backward compatibility` in every one. Reader code keying off `endpoint_type` still works. Only the **CLI flag** `--endpoint-type` is gone.
- `request_goodput`, `max_output_tokens_per_s`, `max_concurrent_requests`, `rtfx`, `start_times` — present in current assembly (re-verified 2026-08-11 at v0.27.0).
- `probe_completed`, `probe_failed`, `probe_median_e2el_ms`, `probe_p99_e2el_ms`, `probe_max_e2el_ms` — emitted only when `--probe-request-rate` > 0 (v0.27.0, PR #49611). Absent otherwise, including on the same server with probes disabled.
- `rps_change_events` — emitted when ramp-up is used (v0.17+)
- `spec_decode_*` suite — depends on engine spec-decode config
- `latencies`, `queue_times` (v0.30.0+, #54136) — unconditional, both generative and pooling.
- `mean_/median_/std_/p<N>_client_queue_time_ms`, `mean_/median_/std_/p<N>_e2el_including_client_queue_ms` (v0.30.0+, #54136) — only when `--max-concurrency` is set and the metric is named in `--percentile-metrics`; the latter also needs `--request-rate` finite.

**When writing dashboards / CI comparators:** prefer the stable names. Defensively check for presence rather than assuming:

```python
rps = d.get("request_throughput", d.get("requests_per_second", 0))  # old name was requests_per_second pre-v0.10
```

Source of truth: `vllm/benchmarks/serve.py` at v0.30.0 (2425 lines) — `BenchmarkMetrics` dataclass **L327** (`EmbedBenchmarkMetrics` L362), JSON assembly starting at `result_json["date"]` **~L2273**. Line refs drift by hundreds of lines every couple of releases — **resolve by symbol, not by line.**
