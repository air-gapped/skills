# `--output-json` schema

Load when parsing benchmark output JSON, building dashboards, or diffing A/B runs. Field names confirmed against `vllm/benchmarks/serve.py` in v0.19.x.

## Top-level fields (always present in `bench serve`)

| Field | Type | Source |
|---|---|---|
| `date` | string | Run timestamp (ISO) |
| `backend` | string | Value of `--backend` |
| `endpoint_type` | string | Mirror of `backend` — kept for backward compat (reader code may still look for this) |
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

Pooling/embedding runs (`EmbedBenchmarkMetrics`) emit only `request_throughput` and `total_token_throughput`.

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

**Stable across v0.11 → v0.19:**
- `request_throughput`, `output_throughput`, `total_token_throughput`
- `mean_<metric>_ms`, `median_<metric>_ms`, `std_<metric>_ms`, `p<N>_<metric>_ms`
- `num_prompts`, `request_rate`, `max_concurrency`

**Added or renamed in recent versions:**
- `endpoint_type` kept as alias after `--endpoint-type` flag removal (v0.11)
- `rps_change_events` — emitted when ramp-up is used (v0.17+)
- `spec_decode_*` suite — depends on engine spec-decode config

**When writing dashboards / CI comparators:** prefer the stable names. Defensively check for presence rather than assuming:

```python
rps = d.get("request_throughput", d.get("requests_per_second", 0))  # old name was requests_per_second pre-v0.10
```

Source of truth: `vllm/benchmarks/serve.py:171-215` (dataclass) and `vllm/benchmarks/serve.py:982-1067` (JSON assembly).
