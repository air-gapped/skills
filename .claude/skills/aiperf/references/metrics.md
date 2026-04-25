# AIPerf Metrics Reference

All metrics aiperf produces, grouped by category. Units in parentheses. Source: `docs/metrics-reference.md` in the local checkout. The same tags are used in `--goodput "tag:value tag:value"` SLO syntax.

## Table of Contents

- [Streaming latency](#streaming-latency)
- [Token counts](#token-counts)
- [Throughput](#throughput)
- [Goodput](#goodput)
- [Errors](#errors)
- [General](#general)
- [Image / video](#image--video)
- [API usage (server-reported)](#api-usage-server-reported)
- [HTTP trace](#http-trace)
- [Multi-run aggregate stats](#multi-run-aggregate-stats)
- [Metric flags](#metric-flags)
- [Goodput SLO syntax](#goodput-slo-syntax)

## Streaming latency

These metrics require `--streaming` and an SSE-capable endpoint.

| Tag | Definition | Unit |
|---|---|---|
| `time_to_first_token` (TTFT) | First response chunk including reasoning tokens. | ms |
| `time_to_second_token` (TTST) | Gap between chunk 1 and chunk 2. | ms |
| `time_to_first_output_token` (TTFO) | First **non-reasoning** output token. Equivalent to genai-perf TTFT for reasoning models. | ms |
| `inter_token_latency` (ITL) | Mean time between successive output tokens (excludes TTFT). | ms |
| `inter_chunk_latency` (ICL) | Distribution of inter-chunk gaps (per-request list). | ms |
| `output_token_throughput_per_user` | `1 / ITL`. | tokens/sec/user |
| `prefill_throughput_per_user` | `ISL / TTFT`. | tokens/sec/user |

For non-reasoning models TTFT == TTFO. For reasoning models (DeepSeek-R1, Qwen3 with thinking, GPT-OSS-class), TTFT < TTFO.

## Token counts

| Tag | Definition | Unit |
|---|---|---|
| `output_token_count` | Non-reasoning completion tokens. (genai-perf OSL equivalent.) | tokens |
| `output_sequence_length` (OSL) | All completion tokens (output + reasoning). | tokens |
| `input_sequence_length` (ISL) | Prompt tokens. | tokens |
| `reasoning_token_count` | Tokens emitted in `reasoning_content`. | tokens |
| `total_output_tokens` | Sum of `output_token_count` across all requests. | tokens |
| `total_output_sequence_length` | Sum of OSL. | tokens |
| `total_input_sequence_length` | Sum of ISL. | tokens |

## Throughput

| Tag | Definition | Unit |
|---|---|---|
| `output_token_throughput` | `total_OSL / benchmark_duration`. | tokens/sec |
| `e2e_output_token_throughput` | `OSL / request_latency`, per request, then aggregated. | tokens/sec |
| `total_token_throughput` | `(total_ISL + total_OSL) / benchmark_duration`. | tokens/sec |
| `request_throughput` | `request_count / benchmark_duration`. | requests/sec |

## Goodput

Goodput = the fraction of requests that meet **all** specified SLOs simultaneously. Throughput says capacity; goodput says how much of that capacity delivers acceptable UX.

| Tag | Definition | Unit |
|---|---|---|
| `good_request_count` | Requests meeting every `--goodput` constraint. | requests |
| `goodput` | `good_request_count / benchmark_duration`. | requests/sec |

## Errors

| Tag | Definition | Unit |
|---|---|---|
| `error_request_count` | Failed requests. | requests |
| `error_input_sequence_length` | ISL of failed requests. | tokens |

## General

| Tag | Definition | Unit |
|---|---|---|
| `request_latency` | Full HTTP-level request → last-response time. | ms |
| `request_count` | Total successful requests. | requests |
| `min_request_timestamp`, `max_response_timestamp` | First / last wall-clock event. | ns |
| `benchmark_duration` | Wall-clock benchmark span. | sec |

## Image / video

| Tag | Definition | Unit |
|---|---|---|
| `number_of_images` | Images per request. | count |
| `image_throughput` | Images / latency. | images/sec |
| `image_latency` | Latency / images. | ms/image |
| `video_inference_time` | Server-reported GPU generation time. | sec |
| `video_peak_memory` | Server-reported peak GPU memory. | MB |

## API usage (server-reported)

When the server populates the OpenAI `usage` field (chat, completions, responses), aiperf records it alongside client-side counts. Useful for client/server tokenizer divergence diagnostics.

| Tag | Definition |
|---|---|
| `usage_prompt_tokens` | Server-reported prompt tokens. |
| `usage_completion_tokens` | Server-reported completion tokens. |
| `usage_total_tokens` | Server-reported total. |
| `usage_reasoning_tokens` | Server-reported reasoning tokens (O1/O3-style models). |

Discrepancy thresholds (env vars):

- `AIPERF_METRICS_USAGE_PCT_DIFF_THRESHOLD` (default 10%) — flag client-vs-server prompt token mismatch.
- `AIPERF_METRICS_OSL_MISMATCH_PCT_THRESHOLD` (default 5%), `AIPERF_METRICS_OSL_MISMATCH_MAX_TOKEN_THRESHOLD` (default 50 tokens) — flag requested-vs-actual OSL mismatch.

## HTTP trace

Available with `--export-http-trace`. k6/HAR-style timings.

| Tag | Definition |
|---|---|
| `http_req_blocked` | Connection-pool wait |
| `http_req_dns_lookup` | DNS |
| `http_req_connecting` | TCP/TLS handshake |
| `http_req_sending` | Request transmission |
| `http_req_waiting` | TTFB (time to first byte) |
| `http_req_receiving` | Response download |
| `http_req_duration` | sending + waiting + receiving |
| `http_req_total` | Full cycle including connection overhead |
| `http_req_data_sent`, `http_req_data_received` | Bytes |
| `http_req_connection_reused` | 1 / 0 |
| `http_req_chunks_sent`, `http_req_chunks_received` | Transport-level chunk counts |

## Multi-run aggregate stats

Generated when `--num-profile-runs > 1`. Exported to `aggregate/profile_export_aiperf_aggregate.{csv,json}`.

| Field | Definition |
|---|---|
| `mean`, `std`, `min`, `max` | Summary stats across runs |
| `cv` | Coefficient of variation (`std/mean`) |
| `se` | Standard error |
| `ci_low`, `ci_high` | Confidence interval bounds |
| `t_critical` | Student-t critical value at the configured `--confidence-level` |

## Metric flags

Internal markers that affect display / availability:

| Flag | Meaning |
|---|---|
| `STREAMING_ONLY` | Requires `--streaming` and SSE multi-chunk responses. |
| `PRODUCES_TOKENS_ONLY` | Only meaningful for endpoints whose responses are tokens (chat / completions / responses / hf-generate). |
| `NO_CONSOLE` | Hidden from terminal display; appears in exports only. |
| `LARGER_IS_BETTER` | Throughput-style; aggregation order. |
| `GOODPUT` | Requires SLOs to be configured. |
| `HTTP_TRACE_ONLY` | Requires `--export-http-trace`. |
| `SUPPORTS_REASONING` | Distinguishes reasoning vs non-reasoning behavior. |
| `INTERNAL` | Hidden unless `AIPERF_DEV_SHOW_INTERNAL_METRICS=true`. |
| `EXPERIMENTAL` | Requires `AIPERF_DEV_MODE=true && AIPERF_DEV_SHOW_EXPERIMENTAL_METRICS=true`. |

## Goodput SLO syntax

```
--goodput "tag1:value1 tag2:value2 ..."
```

- Whitespace-separated.
- `tag` is the metric tag (above). Only metrics applicable to the configured endpoint count.
- `value` is in the metric's display unit (ms for latency, tokens/sec for throughput-per-user). Falls back to base unit if no display unit.

Examples:

```
--goodput "time_to_first_token:250"                                # TTFT ≤ 250 ms
--goodput "time_to_first_token:250 inter_token_latency:10"          # both
--goodput "time_to_first_output_token:300 request_latency:2000"     # reasoning-aware
--goodput "output_token_throughput_per_user:600"                    # per-user TPS ≥ 600
```

A request must meet **all** SLO criteria to count toward `good_request_count`. Reference: [DistServe paper](https://arxiv.org/pdf/2401.09670), [Hao-AI blog](https://hao-ai-lab.github.io/blogs/distserve).

### Mapping percentile SLOs to per-request goodput

`--goodput` evaluates each request against thresholds — there is no `p99_time_to_first_token:400` syntax. To express a percentile SLA:

| Operator framing | aiperf interpretation |
|---|---|
| "p99 TTFT ≤ 400 ms" | `--goodput "time_to_first_token:400"`, post-run check `goodput / request_throughput ≥ 0.99` |
| "p95 TTFT ≤ 300 ms AND p99 latency ≤ 2 s" | `--goodput "time_to_first_token:300 request_latency:2000"`, check ratio ≥ 0.95 |
| "every request must meet SLOs" | `--goodput "..."`, check ratio == 1.0 |

The ratio `good_request_count / request_count` is the exact share of requests meeting all configured thresholds — that's the percentile floor. Reasoning models: use `time_to_first_output_token` not `time_to_first_token` so the SLO measures user-visible latency.
