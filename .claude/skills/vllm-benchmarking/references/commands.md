# `vllm bench` command reference

Load when configuring or debugging a specific bench subcommand. Covers flags, defaults, and gotchas for each of the six subcommands.

## Table of contents
- [`vllm bench serve`](#vllm-bench-serve)
- [`vllm bench throughput`](#vllm-bench-throughput)
- [`vllm bench latency`](#vllm-bench-latency)
- [`vllm bench sweep`](#vllm-bench-sweep)
- [`vllm bench startup`](#vllm-bench-startup)
- [`vllm bench mm-processor`](#vllm-bench-mm-processor)

## `vllm bench serve`

HTTP-level online serving benchmark. The one operators use most.

**Connection:**
- `--base-url <url>` — full URL to the vLLM server. Overrides host/port.
- `--host 127.0.0.1 --port 8000` — fallback when `--base-url` isn't set.
- `--endpoint /v1/completions` — default. Use `/v1/chat/completions` for chat-tuned flows.
- `--backend openai` — default. Other values: `openai-chat`, `vllm`, `vllm-chat`, `openai-embeddings`, `vllm-pooling`, `vllm-rerank`, `openai-audio`, `infinity-embeddings`. **`--endpoint-type` is removed as of v0.11.0 — use `--backend` instead.**
- `--header KEY=VALUE` — arbitrary HTTP headers. Repeatable.
- Auth: `OPENAI_API_KEY` env var auto-injects as Bearer token.

**Load shape:**
- `--num-prompts <N>` — total requests to send. ≥500 for steady-state; ≥2000 for health checks.
- `--request-rate <rps|inf>` — Poisson-arrival rate. `inf` = fire-as-fast-as-possible.
- `--max-concurrency <N>` — cap on in-flight requests. Combine with `--request-rate` for a bounded Poisson; use alone for closed-loop test.
- `--burstiness <float>` — gamma-distribution shape for inter-arrival times. Default 1.0 = Poisson. <1 = bursty spikes, >1 = smoother-than-Poisson.
- `--ramp-up-strategy linear|exponential` + `--ramp-up-start-rps <a>` + `--ramp-up-end-rps <b>` — gradually scale load over the run, useful for finding the breaking point.
- `--num-warmups <N>` — pre-flight requests before measurement. Default 0. Honors `--max-concurrency` during warmup.

**Metrics & output:**
- `--percentile-metrics ttft,tpot,itl,e2el` — which metrics to compute percentiles over. Default `ttft,tpot,itl` for generative; `e2el` only for pooling/embedding.
- `--metric-percentiles 50,90,95,99` — which percentiles. Default is sensible.
- `--goodput KEY:VALUE ...` — SLO budgets in ms (e.g. `ttft:500 itl:50`). Reports fraction of requests meeting all budgets.
- `--save-result --output-json <file>` — dump structured output.
- `--save-detailed` — include per-request records. Large files; use for forensic analysis.

**Dataset selection:** see `datasets.md` for the full catalog. Common: `--dataset-name sharegpt --dataset-path <file>`, `--dataset-name random --random-input-len 1024 --random-output-len 128`, `--dataset-name custom --dataset-path prod-replay.jsonl`.

**Gotcha:** `--max-concurrency` + `--request-rate` together = bounded Poisson. Actual RPS drops below target if server can't keep up. For a fair saturation measurement, use `--request-rate inf` and observe the concurrency that the server achieves.

## `vllm bench throughput`

Offline batch throughput. No HTTP — spins up the engine in-process and submits all prompts at once. Fast iteration for "does this compile flag help."

**Key flags:**
- `--model <name-or-path>` — required; model to load.
- `--num-prompts 1000` — batch size submitted.
- `--dataset-name sharegpt` — default. See `datasets.md`.
- `--input-len`, `--output-len` — force fixed lengths (overrides dataset).
- `--backend vllm` — default. `hf` / `mii` / `vllm-chat` also available.
- `--async-engine` — use the async engine path for measurement.
- `--lora-path <path>` — measure throughput with a LoRA adapter loaded.
- `--disable-detokenize` — skip detokenization cost, isolates raw generate throughput.
- `--output-json <file>` — structured output.

## `vllm bench latency`

Single-batch repeated-measurement latency. Used for kernel-level regression detection.

**Defaults:** `--batch-size 8 --input-len 32 --output-len 128 --num-iters 30 --num-iters-warmup 10`.

**Important gotcha:** **prefix caching is explicitly disabled** in this subcommand to keep latency numbers clean across runs. Do NOT use `latency` to benchmark prefix-cache wins — use `serve` with `--dataset-name prefix_repetition` instead.

**Extra flags:**
- `--profile` — enable PyTorch profiler; writes chrome traces.
- `--disable-detokenize` — as above.

## `vllm bench sweep`

Parameter sweep + SLO-constrained auto-tune. Five sub-modes:

- `sweep serve` — run `bench serve` repeatedly across a parameter grid.
- `sweep serve-workload` — sweep across workload variants (different datasets / lengths).
- `sweep startup` — startup time across configurations.
- `sweep plot` — render results to plots.
- `sweep plot-pareto` — find the Pareto frontier (throughput vs latency).

Typical use: "find the max `--max-concurrency` such that P99 TTFT < 500 ms."

## `vllm bench startup`

Measures time from process launch to first-token-ready. Relevant for cold-start latency in autoscaling / serverless deployments. Takes the full set of engine args normally passed to `vllm serve`.

## `vllm bench mm-processor`

Multimodal preprocessing latency (image/video/audio encoding before decode starts). Dataset-driven. Counts MM tokens per worker separately and aggregates max latency across workers.
