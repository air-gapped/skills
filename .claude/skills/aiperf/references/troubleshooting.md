# Troubleshooting

Common AIPerf failures, what they mean, and how to fix them.

## "Token counts look wrong"

**Symptom:** ISL or OSL totals diverge from the server's `usage` counts.

**Causes:**
1. Tokenizer mismatch. `--tokenizer` defaults to whatever HF resolves from `--model`. If they differ (custom model path, fine-tune, gated repo), every token count is wrong.
2. Reasoning model — see "TTFT lower than expected" below.

**Fix:**
- Always pass `--tokenizer <hf-id>` explicitly.
- Pin via `--tokenizer-revision <sha>`.
- For tokenizers shipping custom Python (Kimi K2.5, some DeepSeek), add `--tokenizer-trust-remote-code`.
- For server-of-record token counts: `--use-server-token-count`. AIPerf still loads the tokenizer for input shaping but skips client-side `encode()` for metrics.

If `AIPERF_METRICS_USAGE_PCT_DIFF_THRESHOLD` (default 10%) is exceeded, AIPerf logs a warning that client/server counts disagree.

## "TTFT lower than expected"

**Symptom:** TTFT vs a previous genai-perf number is much lower for a reasoning model.

**Cause:** AIPerf TTFT counts the first token of any kind, including `reasoning_content`. genai-perf TTFT counted only the first non-reasoning output token.

**Fix:** Compare AIPerf **TTFO** (`time_to_first_output_token`) to genai-perf TTFT. See `migration-from-genai-perf.md`.

## "Cache hit rate is zero on a Mooncake replay"

**Cause:** `--isl-block-size` doesn't match the server's KV-cache block size. Mooncake hashes by 512-token blocks by default. vLLM's `--block-size` defaults to 16 (some envs), SGLang to 64. Hash IDs in the trace then point to blocks that don't exist server-side.

**Fix:** Pass `--isl-block-size <N>` matching the server's block size. Pre-flight: `aiperf analyze-trace --input-file trace.jsonl` to see what block size the trace expects.

## "No streaming metrics"

**Symptom:** TTFT / ITL / per-user throughput are absent from the export.

**Causes:**
- `--streaming` not passed.
- Endpoint type doesn't stream (embeddings, rankings, image-gen, video-gen).
- Server returned all tokens in one chunk (very small models, very small OSL).

**Fix:** Add `--streaming`. If the endpoint type's metadata says `supports_streaming: false`, those metrics never apply.

## "`--request-rate` curve looks like the system melts"

**Cause:** No concurrency cap. The timing manager keeps issuing credits past the server's capacity; client-side queue grows; per-request latency reflects the queue, not the server.

**Fix:** Always pair `--request-rate` with a sane `--concurrency` ceiling, or use `--user-centric-rate` for per-user gap control.

## "Validation error: `--user-centric-rate requires multi-turn conversations`"

**Cause:** `--session-turns-mean` defaults to 1, which is single-turn. User-centric mode is only meaningful for multi-turn KV-cache testing.

**Fix:** Set `--session-turns-mean ≥ 2`, or use `--request-rate` for single-turn rate-based.

## "Validation error: `--fixed-schedule-* can only be used with --fixed-schedule`"

**Cause:** Passed `--fixed-schedule-start-offset` / `--fixed-schedule-end-offset` / `--fixed-schedule-auto-offset` without `--fixed-schedule`.

**Fix:** Add `--fixed-schedule`, or drop the offset flags. Note: trace dataset types auto-enable `--fixed-schedule`; pass `--no-fixed-schedule` (or omit) for as-fast-as-possible replay.

## "Workers OOM / event-loop warnings"

**Symptoms:** "Event loop blocked" warnings; OOM in workers.

**Causes:**
- Too many workers for the box. `--workers-max` defaults to `int(cpu_count * 0.75) - 1`. On CPU-rich nodes this can exceed memory.
- Long-context payloads — every in-flight request holds the prompt in memory.
- `--export-level raw` on a high-throughput run.

**Fix:**
- Reduce `--workers-max`.
- Reduce `--concurrency` or `--prefill-concurrency` for long-context.
- Drop back to `--export-level records`.
- Tune `AIPERF_WORKER_CPU_UTILIZATION_FACTOR` (default 0.75), `AIPERF_WORKER_MAX_WORKERS_CAP` (default 32).
- Watch `AIPERF_SERVICE_EVENT_LOOP_HEALTH_WARN_THRESHOLD_MS` (default 25 ms) — if breached frequently, the loop is under-provisioned.

## "Macos: `semaphore leak` warning / `None stdio`"

Pre-v0.7.0 issue, fixed in v0.7.0 (PRs #686, #690, #706, #709). Upgrade to v0.7.0+.

## "SSE corrupted / `data` field truncates on a literal newline"

Fixed in v0.7.0 (PR #705). Upgrade to v0.7.0+.

## "Absolute path with `--profile-export-prefix` produces empty files"

Pre-v0.7.0 issue, fixed in v0.7.0 (PR #801). Upgrade or use a relative prefix + `--artifact-dir`.

## "GPU telemetry empty"

**Causes:**
- DCGM exporter not running. AIPerf auto-checks `localhost:9400/metrics` and `:9401/metrics`. Configure via `AIPERF_GPU_DEFAULT_DCGM_ENDPOINTS`.
- DCGM exporter unreachable in time. Bump `AIPERF_GPU_REACHABILITY_TIMEOUT` (default 10 s).
- For direct-query collection, switch to `--gpu-telemetry pynvml` (no exporter required; queries the GPU directly).

## "Server metrics empty"

**Causes:**
- Server doesn't expose `/metrics`. Pass an explicit `--server-metrics http://host:port/metrics`.
- Auth: scrape requires direct access. AIPerf does NOT add `Authorization` headers automatically to metrics scrapes; if the endpoint requires auth, expose unauthenticated `/metrics` or front it with a side-car.
- `AIPERF_HTTP_TRUST_ENV=true` if the metrics URL needs proxy env vars.

## "202 Accepted requests counted as failures"

Pre-v0.7.0. Fixed in v0.7.0 (PR #777) — all 2xx responses now count as success. Upgrade.

## "Error: `--prefill-concurrency requires --streaming to be enabled`"

Self-explanatory. Add `--streaming`.

## "Random pool: paired modalities not preserved"

When `--prompt-batch-size > 1` with `random_pool`, AIPerf samples each modality independently from a flat pool — text and image (or text and audio) within one batch are not paired. If pairing matters, switch to `single_turn` JSONL with explicit per-entry payloads.

## "Convergence early stop never triggers"

**Cause:** `--convergence-threshold` (default 0.10 of CI half-width to mean ratio) too tight for the workload, or `--convergence-metric` is high-variance.

**Fix:** Loosen the threshold (e.g. 0.20), pick a more stable metric (`request_latency` p50 instead of TTFT max), or set a hard cap via `--benchmark-duration`.

## Diagnostic env-var quick set

```bash
export AIPERF_DEV_MODE=true
export AIPERF_DEV_SHOW_INTERNAL_METRICS=true        # dev internals
export AIPERF_DEV_SHOW_EXPERIMENTAL_METRICS=true    # experimental metrics
export AIPERF_LOG_LEVEL=DEBUG
export AIPERF_DEV_DEBUG_SERVICES=TimingManager,WorkerManager
```

`-vv` on the CLI is equivalent to `--log-level TRACE` for everything.

## When the docs disagree with `--help`

`docs/cli-options.md` is auto-generated by `make generate-cli-docs`. Drift can happen if a release ships before the doc is regenerated. Trust `aiperf <subcommand> --help` for flag spelling. File an issue in `ai-dynamo/aiperf` for divergent docs.
