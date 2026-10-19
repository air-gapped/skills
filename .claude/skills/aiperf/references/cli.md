# AIPerf CLI Reference

Comprehensive reference for `aiperf` subcommands and `aiperf profile` flags. Aiperf v0.13.0 (stable). Trust `aiperf <subcommand> --help` if anything here disagrees.

## Table of Contents

- [Subcommands](#subcommands)
- [profile — endpoint](#profile--endpoint)
- [profile — input / dataset](#profile--input--dataset)
- [profile — load generator](#profile--load-generator)
- [profile — warmup](#profile--warmup)
- [profile — request cancellation](#profile--request-cancellation)
- [profile — multimodal (audio / image / video)](#profile--multimodal-audio--image--video)
- [profile — prompt / ISL / OSL](#profile--prompt--isl--osl)
- [profile — prefix / system / context](#profile--prefix--system--context)
- [profile — multi-turn / conversation](#profile--multi-turn--conversation)
- [profile — output / exporters](#profile--output--exporters)
- [profile — tokenizer](#profile--tokenizer)
- [profile — multi-run confidence](#profile--multi-run-confidence)
- [profile — accuracy benchmarking](#profile--accuracy-benchmarking)
- [profile — telemetry & server-metrics](#profile--telemetry--server-metrics)
- [profile — service / ZMQ / workers / logging](#profile--service--zmq--workers--logging)
- [analyze-trace](#analyze-trace)
- [plot](#plot)
- [plugins](#plugins)
- [synthesize / validate / speed-bench-report](#synthesize--validate--speed-bench-report)

## Subcommands

| Subcommand | Purpose |
|---|---|
| `aiperf profile` | Run a benchmark. The main command. `-f run.yaml` runs a YAML config. |
| `aiperf analyze-trace --input-file <file.jsonl>` | Stats on a Mooncake trace (ISL/OSL distributions, cache-hit rates, block-size). |
| `aiperf analyze swim-lane --run-dirs <dir>` | Per-session swim-lane PNG with the concurrency curve; `--html` adds an interactive viewer. |
| `aiperf analyze turn-messages --run-dirs <dir>` | HTML viewer of per-turn input messages. Needs a run made with `--export-level raw`. |
| `aiperf chat --model M --url U` | Interactive chat with per-reply TTFT / TPS / latency. `--quick "<msg>"` = one request; `--no-history` = stateless turns. Sanity check, not a benchmark. |
| `aiperf config init / expand / validate` | Bundled YAML templates (`init --list`, `init -t <name> -o run.yaml`), expand a sweep config, validate a config through the `profile` pipeline (exit 1 on fatal errors). |
| `aiperf kube <init\|validate\|preflight\|profile\|sweep\|attach\|logs\|results\|list\|show\|debug\|dashboard\|cancel\|delete\|cleanup\|shutdown\|generate>` | v0.13.0+, beta. Run benchmarks as Kubernetes jobs through the AIPerf operator. `kube preflight` checks the cluster; `kube results` downloads artifacts. |
| `aiperf plot` | Generate plots (latency dist, throughput, Pareto, time-series, comparison) from one or more artifact dirs; `--dashboard` launches an interactive Dash app. |
| `aiperf plugins [<category> [<name>]]` | List installed plugin packages, browse categories, inspect an entry, `--validate` against import. |
| `aiperf synthesize agentic-code` | Generate a synthetic agentic-coding session dataset. Trace scaling is NOT here — it is `aiperf profile --synthesis-*`. |
| `aiperf validate --target <format> --input <file>` | Validate one export file. |
| `aiperf speed-bench-report --paths <dirs>` | Combine per-category SPEED-Bench artifact dirs into a single matrix report. |
| `aiperf service`, `aiperf proxy` | Pod internals of the Kubernetes path. Do not call directly; single-node runs use `aiperf profile`. |
| `aiperf --install-completion [--shell {bash,zsh,fish}]` | Install shell completion. |

## profile — endpoint

| Flag | Type | Default | Notes |
|---|---|---|---|
| `-m`, `--model-names`, `--model` | list | **required** | Comma-separated or repeat. With multiple, `--model-selection-strategy {round_robin,random}`. |
| `--endpoint-type` | enum | `chat` | 19 values: `chat`, `chat_embeddings`, `completions`, `responses`, `messages`, `audio_transcription`, `embeddings`, `nim_embeddings`, `cohere_rankings`, `hf_tei_rankings`, `nim_rankings`, `image_retrieval`, `image_generation`, `image_edit`, `video_generation`, `huggingface_generate`, `solido_rag`, `raw`, `template`. See `endpoints.md`. |
| `--custom-endpoint`, `--endpoint` | str | `/v1/...` | Override the default API path (e.g. `/my-api/chat`). |
| `-u`, `--url` | list | `localhost:8000` | One or more base URLs. Multiple URLs enable load balancing (`--url-strategy round_robin`). |
| `--streaming` | flag | off | Enable SSE streaming. Required for TTFT/ITL/ICL metrics. Auto-disabled on non-streaming endpoints. |
| `--api-key` | str | none | `Authorization: Bearer <key>`. v0.7.0 added centralized credential redaction in logs. |
| `--request-timeout-seconds` | float | 21600 | 6 h default. |
| `--transport`, `--transport-type` | enum | auto | Currently only `http` (aiohttp). |
| `--use-legacy-max-tokens` | flag | off | Use `max_tokens` instead of `max_completion_tokens`. For older OpenAI-compat servers. |
| `--use-server-token-count` | flag | off | Trust server's `usage` field instead of client tokenizing. Auto-sets `stream_options.include_usage=true`. |
| `--per-chunk-usage` | flag | off | v0.13.0+. Sets `stream_options.continuous_usage_stats` so ITL subtracts the real first-chunk token count. Use when the server bundles tokens into the first chunk (e.g. TRT-LLM `stream-interval`). Requires `chat`, `--streaming` and `--use-server-token-count`; vLLM / TRT-LLM accept it, strict OpenAI rejects it. |
| `--reset-kv-cache` | flag | off | v0.13.0+. POST a KV-cache reset once per cell. `--reset-kv-cache-path` (default `/reset_prefix_cache`), `--reset-kv-cache-timeout-seconds`. |
| `--server-profiler` | flag | off | v0.13.0+. Start/stop the server profiler around profiling phases. `--server-profiler-start-path` (default `/start_profile`), `--server-profiler-stop-path` (default `/stop_profile`). |
| `--session-header` | str | `X-Correlation-ID` | Renames the per-session correlation header. v0.13.0+ also sends `X-Session-Affinity` with the same value by default (see SKILL.md). |
| `--connection-reuse-strategy` | enum | `pooled` | `pooled` / `never` / `sticky-user-sessions` (last keeps a user's connection across turns — enables sticky LB). |
| `--download-video-content` | flag | off | For `video_generation`: download bytes after job completes; latency includes download time. |
| `--request-content-type` | enum | `application/json` | `multipart/form-data` for vLLM video-gen. |

## profile — input / dataset

| Flag | Notes |
|---|---|
| `--input-file <path>` | File or directory; required with `--custom-dataset-type`. |
| `--custom-dataset-type` | 13 formats: `single_turn`, `multi_turn`, `mooncake_trace`, `bailian_trace`, `burst_gpt_trace`, `baseten_trace`, `weka_trace`, `tracelab`, `random_pool`, `dag_jsonl`, `raw_payload`, `inputs_json`, `sagemaker_data_capture` — plus the `speed_bench_*` family. See `datasets.md`. |
| `--public-dataset` | 42 values: `sharegpt`, `aimo*`, vision (`mmstar`, `mmvu`, `vision_arena`, `llava_onevision`), coding (`instruct_coder`, `spec_bench`, `blazedit_*`), `spec_al_*`, speech (`librispeech`, `voxpopuli`, `gigaspeech`, `ami`, `spgispeech`), agentic (`exgentic`, `exgentic_v2`, `weka_hf`, `semianalysis_cc_traces_weka*`). `speed_bench_*` is NOT a public dataset — it is a `--custom-dataset-type` value. Mutually exclusive with `--custom-dataset-type`. |
| `--hf-subset <name>` | Override the HF subset for HF-backed loaders (e.g. `sharegpt4o`). |
| `--dataset-sampling-strategy` | `sequential` / `random` / `shuffle`. Default depends on dataset; not compatible with `--fixed-schedule`. |
| `--fixed-schedule` | Replay timestamps from dataset metadata. Auto-enabled for trace types. |
| `--fixed-schedule-auto-offset` | Shift first timestamp to 0. Mutually exclusive with `--fixed-schedule-start-offset`. |
| `--fixed-schedule-start-offset <ms>` | Skip requests before this offset (ms). |
| `--fixed-schedule-end-offset <ms>` | Stop at this offset. Must be ≥ start. |
| `--random-seed <int>` | Reproducibility seed for synthetic generation, sampling, delays. |
| `--extra-inputs key:value` | Merged into every payload. Repeat or pass JSON: `--extra-inputs temperature:0.7 top_p:0.9` or `--extra-inputs '{"temperature":0.7}'`. |
| `-H`, `--header Header:Value` | Custom HTTP header. Repeat. JSON form also accepted. |
| `--goodput "tag:val tag:val"` | SLO constraints. Tag = metric tag, value in display unit. E.g. `"time_to_first_token:250 inter_token_latency:10 request_latency:2000"`. Goodput = req/s meeting **all** constraints. See [DistServe](https://arxiv.org/pdf/2401.09670). |

## profile — load generator

See `timing-modes.md` for the full compatibility matrix. Pick exactly one scheduling mode; otherwise rules:

- `--concurrency` only → burst mode (as fast as possible, capped).
- `--request-rate` → rate-based (with optional `--arrival-pattern`).
- `--fixed-schedule` → trace replay.
- `--user-centric-rate --num-users` → per-user gap.

| Flag | Notes |
|---|---|
| `--concurrency <int>` | Max in-flight sessions. With rate or fixed-schedule it's a ceiling; alone it's the driver. |
| `--prefill-concurrency <int>` | Max in-flight prefill stage. Requires `--streaming`; must be ≤ `--concurrency`. Memory-safe long-context benchmarking. |
| `--concurrency-ramp-duration <sec>` | Linear ramp from 1 → target. |
| `--prefill-concurrency-ramp-duration <sec>` | Same for prefill. Requires `--streaming`. |
| `--request-rate <qps>` | Target requests per second. |
| `--request-rate-ramp-duration <sec>` | Ramp from a proportional minimum to target. Errors with `--fixed-schedule` or `--user-centric-rate`. |
| `--arrival-pattern` | `constant`, `poisson` (default with `--request-rate`), `gamma`, `concurrency_burst` (auto when no rate). |
| `--arrival-smoothness <float>` | Gamma shape: `<1` bursty, `=1` Poisson, `>1` smooth. Only with `--arrival-pattern gamma`. |
| `--user-centric-rate <qps>` | Per-user QPS. Each user's turn-gap = `num_users / qps`. Requires `--num-users`, `--session-turns-mean ≥2`. |
| `--num-users <int>` | Active concurrent users (user-centric mode only). |
| `--request-count <int>` | Stop after N requests. Mutex with `--num-sessions`. |
| `--num-sessions`, `--conversation-num <int>` | Stop after N sessions. |
| `--benchmark-duration <sec>` | Stop after wall-clock seconds. |
| `--benchmark-grace-period <sec\|inf>` | Wait for in-flight after duration. Default 30 (∞ for user-centric duration mode). |
| `--convergence-metric <tag>` | Adaptive stopping target metric (e.g. `time_to_first_token`). |
| `--convergence-stat <name>` | `avg`, `p50`, `p90`, `p95`, `p99`, `min`, `max`. |
| `--convergence-threshold <float>` | CI half-width / mean fraction. Default 0.10. |
| `--convergence-mode` | `ci_width`, `cv`, `distribution`. |

## profile — warmup

Independent of main scheduling. Falls back to main values if the warmup-prefixed flag is omitted.

| Flag | Notes |
|---|---|
| `--warmup-request-count <int>` | Stop warmup at N requests. Mutex with `--num-warmup-sessions`. |
| `--warmup-duration <sec>` | Stop warmup after wall-clock seconds. |
| `--num-warmup-sessions <int>` | Stop warmup at N sessions. |
| `--warmup-concurrency <int>` | Defaults to `--concurrency`. |
| `--warmup-prefill-concurrency <int>` | Requires `--streaming`. |
| `--warmup-request-rate <qps>` | |
| `--warmup-arrival-pattern` | |
| `--warmup-grace-period <sec\|inf>` | Default ∞. |
| `--warmup-*-ramp-duration` | Per-knob ramp. |

## profile — request cancellation

| Flag | Notes |
|---|---|
| `--request-cancellation-rate <0–100>` | % of requests to cancel mid-flight. |
| `--request-cancellation-delay <sec>` | Wait before cancelling. Requires `--request-cancellation-rate`. |

Cancelled requests carry `was_cancelled: true` and `cancellation_time_ns` in `profile_export.jsonl`. Error type `RequestCancellationError`, code 499.

## profile — multimodal (audio / image / video)

Audio:

| Flag | Notes |
|---|---|
| `--audio-batch-size <int>` | Per-request audio inputs. |
| `--audio-length-mean <sec>`, `--audio-length-stddev` | Synthetic audio duration distribution. |
| `--audio-format` | `wav` or `mp3`. |
| `--audio-depths` | List: 8 / 16 / 24 / 32. |
| `--audio-sample-rates` | List in kHz. |
| `--audio-num-channels` | 1 (mono) / 2 (stereo). |

Image:

| Flag | Notes |
|---|---|
| `--image-batch-size <int>` | Per-request images. |
| `--image-width-mean`, `--image-width-stddev`, `--image-height-mean`, `--image-height-stddev` | Distribution. |
| `--image-format` | `png`, `jpeg`, `random`. |

Video:

| Flag | Notes |
|---|---|
| `--video-batch-size <int>` | Per-request videos. |
| `--video-duration <sec>` | |
| `--video-fps`, `--video-width`, `--video-height` | |
| `--video-format` | `webm` (default) / `mp4`. |
| `--video-codec` | `libvpx-vp9` default. |

## profile — prompt / ISL / OSL

| Flag | Notes |
|---|---|
| `--isl`, `--prompt-input-tokens-mean <int>` | Mean input tokens. Default 550. |
| `--isl-stddev`, `--prompt-input-tokens-stddev <int>` | Stddev. |
| `--isl-block-size`, `--prompt-input-tokens-block-size <int>` | KV-cache block size. Mooncake default 512. Mooncake `hash_ids` are encoded at 512-token granularity by design — keep 512; verify the server's block size divides 512 (see SKILL.md pitfall 5). |
| `--osl`, `--prompt-output-tokens-mean <int>` | Mean output tokens (target). |
| `--osl-stddev`, `--prompt-output-tokens-stddev <int>` | Stddev. |
| `-b`, `--prompt-batch-size <int>` | Batch inputs per request (embeddings/rankings). |
| `--random-range-ratio <float\|json>` | v0.13.0+. Sample ISL/OSL uniformly in a window around `--isl`/`--osl` (both required). `--random-corpus-style vllm` (default; `[mean*(1-r), mean*(1+r)]`, matches `vllm bench serve`) or `sglang` (`[mean*r, mean]`). Mutually exclusive with `--seq-dist`. |
| `--seq-dist`, `--sequence-distribution "ISL,OSL:WEIGHT;ISL,OSL:WEIGHT"` | Mixed ISL/OSL distribution, e.g. `256,128:25;512,256:50;1024,512:25`. |

## profile — prefix / system / context

| Flag | Notes |
|---|---|
| `--num-prefix-prompts <int>` | Distinct prefix prompts (KV-cache reuse testing). |
| `--prefix-prompt-length <int>` | Tokens per prefix. |
| `--shared-system-prompt-length <int>` | Tokens in a shared system prompt across all sessions. Cache-friendly. |
| `--user-context-prompt-length <int>` | Per-session unique padding (cache-hostile). |
| `--system-prompt <text>` / `--system-prompt-file <path>` | v0.13.0+. Verbatim system prompt on every conversation (prepended to a dataset's own system message). Tokens are additive to `--isl`. Use the file form for real production prompts. Mutually exclusive with each other, `--shared-system-prompt-length` and `--num-prefix-prompts`. |
| `--cache-bust <target>` | `none` (default); `system_prefix` / `system_suffix` / `first_turn_prefix` / `first_turn_suffix` inject a per-trajectory unique marker (warmup KV work still transfers to profiling, no cross-trajectory sharing); `warmup_isolation_system` / `warmup_isolation_first_turn` mark warmup only. All structured workloads since v0.13.0. Not with agentic replay. |

## profile — multi-turn / conversation

| Flag | Notes |
|---|---|
| `--conversation-num`, `--num-sessions <int>` | Sessions to run. |
| `--num-dataset-entries <int>` | Unique prompts in the pool. **Default 100**, reused across requests; the same `--random-seed` regenerates the same pool. Set ≥ requests + warmup on prefix-caching servers or repeats are served from cache. |
| `--conversation-turn-mean <int>` | Turns per conversation. Default 1. User-centric requires ≥2. |
| `--conversation-turn-stddev <int>` | |
| `--conversation-turn-delay-mean <ms>` | Inter-turn delay. |
| `--conversation-turn-delay-stddev <ms>` | |
| `--conversation-turn-delay-ratio <float>` | Multiplier on the mean. |

## profile — output / exporters

| Flag | Notes |
|---|---|
| `--artifact-dir <path>` | Output dir. Default `artifacts`. |
| `--profile-export-prefix <str>` | File-name prefix. v0.7.0 fixed absolute-path support (PR #801). |
| `--export-level` | `summary` (csv+json) / `records` (default; adds `.jsonl`) / `raw` (adds `_raw.jsonl` with full payloads). |
| `--slice-duration <sec>` | Time-windowed metrics. Generates `*_timeslices.{csv,json}`. |
| `--export-http-trace` | Include HTTP trace timings in the export. |
| `--show-trace-timing` | Print HTTP timing breakdown to console. |

External exporters — each needs its extra: `pip install "aiperf[mlflow]"` / `"aiperf[wandb]"` / `"aiperf[otel]"`.

| Flag | Notes |
|---|---|
| `--mlflow-tracking-uri <uri>` | Enables MLflow upload of the run's results. |
| `--mlflow-experiment <name>`, `--mlflow-run-name <name>` | Experiment and run name. |
| `--mlflow-tag key:value` | Repeatable run tags (e.g. `--mlflow-tag revision:<sha>`). |
| `--mlflow-parent-run-id <id>` | Nest the run under a parent run. |
| `--mlflow-artifact-glob <glob>` | Override which artifact files are uploaded. |
| `--wandb-project <name>` | Enables W&B export. `--wandb-entity`, `--wandb-run-name`, `--wandb-tag`. |
| `--otel-url <otlp-http-url>` | Live OTLP/HTTP streaming. `--stream metrics\|timing\|default`, `--otel-resource-attributes key=value`. |

`aiperf plot --paths <run> --mlflow-upload` attaches the plots to the MLflow run recorded in `mlflow_export.json`.

## profile — tokenizer

| Flag | Notes |
|---|---|
| `--tokenizer <id\|path\|builtin>` | HF id, local path, or `builtin` (tiktoken `o200k_base`, no network). |
| `--tokenizer-revision <branch\|tag\|sha>` | Default `main`. Pin for reproducibility. |
| `--tokenizer-trust-remote-code` | Required for tokenizers shipping custom Python (Kimi K2.5 etc.). v0.7.0 fixed `parallel_decode` honoring this for Kimi (PR #744). |

## profile — multi-run confidence

| Flag | Notes |
|---|---|
| `--num-profile-runs <1–10>` | Repeat profile N times for CI bands. Default 1. |
| `--profile-run-cooldown-seconds <sec>` | Cooldown between runs. |
| `--confidence-level <float>` | Default 0.95. |
| `--profile-run-disable-warmup-after-first` | Skip warmup on runs 2–N. |
| `--set-consistent-seed` | Default on: sets seed 42 when none given, so every trial replays identical prompts. |
| `--vary-seed-per-trial` | Distinct seed per trial. Use on prefix-caching servers, where identical trials 2..N hit a warm cache. |

Outputs: `aggregate/profile_export_aiperf_aggregate.{csv,json}` with mean, std, cv, se, ci_low, ci_high, t_critical.

## profile — accuracy benchmarking

| Flag | Notes |
|---|---|
| `--accuracy-benchmark` | `mmlu` / `aime` / `aime24` / `aime25` / `hellaswag` / `bigbench` / `gpqa_diamond` / `math_500` / `lcb_codegeneration`. |
| `--accuracy-tasks <list>` | Subtask filter. |
| `--accuracy-n-shots <0–8>` | Few-shot examples. |
| `--accuracy-enable-cot` | Chain-of-thought prompting. |
| `--accuracy-grader` | `exact_match` / `math` / `multiple_choice` / `code_execution`. |
| `--accuracy-system-prompt <str>` | Override default. |
| `--accuracy-verbose` | Detailed grading output. |

## profile — telemetry & server-metrics

| Flag | Notes |
|---|---|
| `--gpu-telemetry [pynvml\|dashboard\|<URL>]` | Collect GPU metrics. `pynvml` queries the GPU directly (no exporter); `dashboard` or a URL scrapes DCGM Prometheus. Auto-discovers DCGM endpoints `localhost:{9400,9401}/metrics`. |
| `--no-gpu-telemetry` | Disable. |
| `--server-metrics [URLs...]` | Prometheus endpoints to scrape. Auto-enabled; defaults to `<--url>/metrics`. |
| `--no-server-metrics` | Disable. |
| `--server-metrics-formats` | List of `json`, `csv` (default), `jsonl`, `parquet`. |

## profile — service / ZMQ / workers / logging

| Flag | Notes |
|---|---|
| `--zmq-host` | Default `127.0.0.1`. |
| `--zmq-ipc-path <dir>` | IPC socket directory. |
| `--workers-max <int>` | Cap. Default formula: `max(1, min(int(cpu_count * 0.75) - 1, AIPERF_WORKER_MAX_WORKERS_CAP))`. Default cap 32. |
| `--log-level` | `TRACE`, `DEBUG`, `INFO` (default), `NOTICE`, `WARNING`, `SUCCESS`, `ERROR`, `CRITICAL`. |
| `-v`, `--verbose` | = `--log-level DEBUG`. |
| `-vv`, `--extra-verbose` | = `--log-level TRACE`. |

## analyze-trace

```
aiperf analyze-trace --input-file <trace.jsonl> [--block-size 512] [--output-file analysis.json]
```

Reports ISL/OSL distribution, request-rate histogram, and KV-cache block-reuse statistics for a Mooncake-format trace. Pre-flight check before benchmarking — surfaces the trace's natural concurrency, hit-rate ceiling, and whether the model's context window can absorb the tail.

## plot

```
aiperf plot [--paths DIR ...] [--dashboard] [--port 8050] [--theme dark|light] [--output OUT]
```

Plot types: latency distribution histograms, throughput curves, Pareto (TPS/GPU vs TPS/User), time-series, request-level scatter, side-by-side multi-run comparison. `--dashboard` runs an interactive Dash server (default port 8050). `plot` finds runs by the default export filenames only — a run made with `--profile-export-prefix` / `--profile-export-file` is not detected. PNG export needs Chrome or Chromium installed.

## plugins

```
aiperf plugins                        # installed packages, versions, plugin counts
aiperf plugins --all                  # every category × plugins
aiperf plugins endpoint               # all endpoints with descriptions
aiperf plugins endpoint chat          # details: class path, package, metadata
aiperf plugins --validate             # validate class paths and existence
```

See `plugins.md` for authoring custom plugins.

## synthesize / validate / speed-bench-report

```
# Trace scaling is a profile-time transform (in memory, before the run):
aiperf profile ... \
  --input-file mooncake_trace.jsonl --custom-dataset-type mooncake_trace \
  --synthesis-speedup-ratio 2.0 \
  --synthesis-prefix-len-multiplier 1.5 \
  --synthesis-prefix-root-multiplier 4 \
  --synthesis-prompt-len-multiplier 1.0 \
  --synthesis-max-isl 32000 --synthesis-max-osl 2000

aiperf synthesize agentic-code --num-sessions 1000 --output out/ [--seed 42 --max-isl N --max-osl N]

aiperf validate --target <format> --input <export-file>

aiperf speed-bench-report --paths artifacts/ [--metric accept_rate] [--output report] [--format ...]
```
