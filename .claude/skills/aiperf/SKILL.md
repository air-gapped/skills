---
name: aiperf
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  NVIDIA AIPerf — vendor-neutral generative-AI inference benchmarking (genai-perf successor). `aiperf profile`: concurrency / request-rate / fixed-schedule trace replay / user-centric / multi-run confidence, 19 endpoint types (chat, completions, embeddings, rankings, responses, messages, audio transcription, image-gen/edit, video-gen, NIM, HF-TGI, raw, template), 13 custom dataset formats (single/multi-turn; mooncake, bailian, burst_gpt, baseten, weka, tracelab traces; random_pool, dag_jsonl, raw_payload, inputs_json, sagemaker_data_capture) plus SPEED-Bench, 40+ public datasets, goodput SLOs, GPU + Prometheus telemetry, plot/analyze/synthesize/kube subcommands, plugins, reasoning TTFT/TTFO split.
when_to_use: |-
  Trigger on "aiperf", "ai-dynamo/aiperf", "genai-perf migration", or "benchmark vllm / sglang / trt-llm / dynamo / nim / triton / ollama" — vendor-neutral, prefer over `vllm bench` when target is non-vLLM or trace-driven. Also `aiperf profile / plot / plugins / analyze-trace / synthesize / service`, "mooncake / bailian / burstgpt trace", "sharegpt", "speed-bench", "MMLU / AIME accuracy benchmark", "TTFO / time-to-first-output-token", "reasoning-token TTFT split", "goodput SLO", "DistServe goodput", "fixed-schedule replay", "user-centric rate", "prefill concurrency", "multi-run confidence", "DCGM / pynvml telemetry", "profile_export.jsonl", "NIM embeddings/rankings", "HF TEI rerank", "image / video generation benchmark", "register custom endpoint / dataset plugin". Defer to `vllm-benchmarking` for `vllm bench` workflows.
---

# AIPerf — NVIDIA generative-AI inference benchmarking

Use for defensible latency / throughput / goodput numbers against any OpenAI-compatible server (vLLM, SGLang, TensorRT-LLM, NVIDIA Dynamo, NIM, Triton, HF TGI, Ollama), and for extending AIPerf with plugins. AIPerf is the `genai-perf` successor; its numbers differ for reasoning models (pitfall 2). For a vLLM-only target driven by the in-tree `vllm bench` toolchain, use the `vllm-benchmarking` skill; use AIPerf when the target is non-vLLM or the workload is trace-driven, multi-modal, multi-server, or needs goodput.

## Version-gated capabilities — check `aiperf --version` before using

| Need | Use | Needs |
|---|---|---|
| Sweep or search instead of a shell loop | List flags (`--concurrency 10,50,100`), `--search-recipe <name>`, YAML `sweep:` / Bayesian search; multi-tier SLO search `--search-sla-tier` | recipes/BO v0.10.0; tiers v0.11.0 |
| Several warmup/profiling phases, or adaptive scaling, in one run | Phases and scale variables in the YAML config | v0.12.0 |
| Accuracy alongside perf | `--accuracy-benchmark` (see `references/cli.md`) | AIME v0.9.0; HellaSwag/BBH/AIME24-25 v0.10.0; MATH-500/GPQA/LCB/GSM8K v0.11.0 |
| Export to MLflow / W&B / OTel | `--mlflow-*`, `--wandb-*`, `--otel-url` + pip extra (`references/cli.md` → External exporters) | MLflow/OTel v0.9.0; W&B v0.11.0 |
| AMD GPU telemetry | `amdsmi` collector | v0.9.0 |
| Latency without the network path | `network_adjusted_*` metrics | v0.11.0 |
| Anthropic Messages API | `--endpoint-type messages` (`/v1/messages`); wire format: `messages-api` skill | v0.12.0 |
| Per-request spec-decode acceptance | vLLM adapter; pair with vLLM `--per-request-spec-decode-metrics` (`vllm-speculative-decoding`) | v0.12.0 |
| Agentic / DAG replay | `exgentic*`, `baseten_trace`, `weka_*`, `dag_jsonl`, `tracelab` (v0.13.0) | v0.12.0 |
| Inspect a run | `aiperf analyze swim-lane` / `turn-messages`; `aiperf chat` for a hand check | v0.12.0 |
| Run inside Kubernetes | `aiperf kube …` (beta) | v0.13.0 |
| Correct ITL when the first chunk bundles tokens | `--per-chunk-usage` (with `--use-server-token-count`; vLLM / TRT-LLM only) | v0.13.0 |
| Reset prefix cache / profile the server per run | `--reset-kv-cache` (`/reset_prefix_cache`), `--server-profiler` (`/start_profile`, `/stop_profile`) | v0.13.0 |
| Production system prompt, `vllm bench`/sglang-style random lengths, cache-bust markers, ASR | `--system-prompt-file`, `--random-range-ratio` + `--random-corpus-style`, `--cache-bust`, `--endpoint-type audio_transcription` | v0.13.0 |

Behaviour changes that make results non-comparable across versions:

- **v0.11.0 warmup fix** — warmup no longer leaks prefix-cache reuse into profiling. Baselines from ≤v0.10.x with warmup on are not comparable; re-run them.
- **v0.13.0 sends `X-Session-Affinity`** (the session's `X-Correlation-ID` value) on every request. A router that honours it pins a session's turns to one replica, so multi-turn results against such a router differ from v0.12.0. Disable: `AIPERF_HTTP_X_SESSION_AFFINITY_FROM_CORRELATION_ID=false`. Router-specific affinity is opt-in: `AIPERF_HTTP_X_DYNAMO_SESSION_ID_FROM_CORRELATION_ID=true` (Dynamo `--router-session-affinity-ttl-secs`), `AIPERF_HTTP_X_SMG_ROUTING_KEY_FROM_CORRELATION_ID=true` (SGLang Model Gateway manual routing).

## Versions

- **Stable on PyPI:** v0.13.0 (2026-09-24), `requires-python >=3.11,<3.14`. `pip install aiperf`. A nightly wheel is published alongside as `aiperf-nightly` (v0.10.0+).
- **Repo `main`** at https://github.com/ai-dynamo/aiperf: post-v0.13.0.
- **Python:** **≥3.11**, <3.14 — the floor moved at v0.12.0 (PR #1107); v0.11.0 and earlier accept 3.10. Pin to v0.11.0 if the runner is stuck on 3.10. Uses `uvloop` on Linux/macOS, falls back to default asyncio on Windows — Windows is a first-class port with blocking CI since v0.11.0 (PR #1007), and Windows-on-ARM install/run was added at v0.12.0 (PR #1068).
- **Source of truth for flags:** `aiperf profile --help`. CLI options doc is auto-generated via `make generate-cli-docs`. If the doc disagrees with `--help` on a flag spelling, trust `--help`.

## Decision tree — which subcommand

| Question | Subcommand | Why |
|---|---|---|
| "Run a benchmark" | `aiperf profile` | The main command. 99% of tasks. |
| "Plot the result" | `aiperf plot` | Pareto, latency histograms, time-series, side-by-side runs. `--dashboard` for interactive. |
| "What plugins are installed?" | `aiperf plugins [<category> [<name>]]` | Inspect + validate the plugin registry. |
| "Inspect a Mooncake trace before benchmarking" | `aiperf analyze-trace <file.jsonl>` | ISL/OSL distribution + cache-hit-rate stats. Use to size the benchmark. |
| "Scale a real trace for KV-cache stress" | `aiperf profile ... --custom-dataset-type mooncake_trace --synthesis-*` | Prefix length / root count / speedup / ISL-OSL caps are `profile` flags, applied in memory at load. `aiperf synthesize` does not take a trace. |
| "Generate a synthetic agentic-coding dataset" | `aiperf synthesize agentic-code [--num-sessions N --output DIR]` | The only `synthesize` target. |
| "Sanity-check an endpoint by hand before a run" | `aiperf chat --model M --url U [--quick "hi"]` | Per-reply TTFT / TPS / latency. Not a benchmark. |
| "Why did this run behave like that?" | `aiperf analyze swim-lane --run-dirs <dir>` / `analyze turn-messages` | Per-session timeline PNG (+ `--html` viewer); per-turn input-message HTML viewer (needs `--export-level raw`). |
| "Start from a YAML config instead of flags" | `aiperf config init --list` → `config init -t <name> -o run.yaml` → `config validate --config-file run.yaml` → `aiperf profile -f run.yaml` | Bundled templates (e.g. `minimal`, `goodput_slo`). |
| "Run the benchmark inside Kubernetes" | `aiperf kube init` (starter config) → `kube profile` / `kube sweep` → `kube results` | v0.13.0+, beta. `kube preflight` / `kube debug` when it fails. `aiperf service` and `aiperf proxy` are pod internals — do not call them directly. |
| "Validate an export file" | `aiperf validate --target <format> --input <file>` | Sanity check that one export file is well-formed. |
| "Combine SPEED-Bench category runs" | `aiperf speed-bench-report` | Per-category → matrix report. |

## The four scheduling modes — pick exactly one

`aiperf profile` schedules requests in one of four mutually exclusive modes. Picking the wrong one is the single most common source of misleading numbers. See `references/timing-modes.md` for the full compatibility matrix and validation errors.

| Goal | Mode | Flag |
|---|---|---|
| Saturation / max throughput within a concurrency cap | **concurrency-only burst** | `--concurrency N` (no rate flag) |
| Controlled request rate, configurable arrivals | **request-rate** | `--request-rate Q` `[--arrival-pattern poisson\|constant\|gamma]` |
| Replay a real trace at exact timestamps | **fixed-schedule** | `--input-file <trace> --custom-dataset-type mooncake_trace --fixed-schedule` |
| Per-user gap-controlled multi-turn (KV-cache TTL testing) | **user-centric-rate** | `--user-centric-rate Q --num-users N --session-turns-mean ≥2` |

A stop condition is required: `--request-count`, `--num-sessions`, or `--benchmark-duration`. Duration mode also reads `--benchmark-grace-period` (default 30s; user-centric defaults to ∞).

## Two methodologies operators actually need

### A — Health check / SLO validation

**Question:** Does this deployment meet the SLO under realistic load?

```bash
aiperf profile \
  --model Qwen/Qwen3-0.6B \
  --url http://endpoint:8000 \
  --endpoint-type chat \
  --streaming \
  --tokenizer Qwen/Qwen3-0.6B \
  --input-file prod-trace.jsonl --custom-dataset-type mooncake_trace --fixed-schedule \
  --goodput "time_to_first_token:250 inter_token_latency:10 request_latency:2000" \
  --warmup-duration 30 \
  --benchmark-duration 600 --benchmark-grace-period 60 \
  --artifact-dir artifacts/health-$(date -Iseconds)
```

The operator reports goodput-req/s and the offending tail percentiles. Goodput=0 with high throughput means the SLO is failing across the board.

### B — A/B comparison / before-after

**Question:** Did config change X help, and at what cost?

Run a **concurrency or request-rate sweep**, not a single point. The knee of the throughput-vs-tail-latency curve is the usable operating point. A change that moves the knee right is a win.

```bash
aiperf profile \
  --model Qwen/Qwen3-0.6B --url http://endpoint:8000 \
  --endpoint-type chat --streaming \
  --tokenizer Qwen/Qwen3-0.6B \
  --concurrency 10,50,100,200,500 --request-count 1000 \
  --isl 1000 --osl 500 \
  --num-dataset-entries 1000 --random-seed 42 \
  --artifact-dir artifacts/pareto
aiperf plot --paths artifacts/pareto --dashboard   # finds every point's run dir recursively
```

A comma-separated `--concurrency` (also `--request-rate`, `--isl`, `--osl`; `--sweep-type grid|zip`) runs the sweep natively and gives each point its own seed (`base + index`) by default — do not write a shell loop with one fixed seed. To answer "highest throughput that still meets the SLA" directly, use a recipe instead of a grid: `--search-recipe max-throughput-ttft-sla --ttft-sla-ms 200` (others: `max-goodput-under-slo`, `concurrency-ramp`, `pareto-sweep`; `aiperf plugins search_recipe` lists them).

Same seed list, same hardware, same tokenizer for config A and config B. **Synthetic prompts are a 100-entry pool by default (`--num-dataset-entries`), reused across requests, and a given `--random-seed` regenerates the identical pool.** Against a prefix-caching server (vLLM APC, SGLang radix) a 1000-request run with the default pool, or a second run with the same seed, is served from cache — TTFT and throughput become cache measurements. So: size `--num-dataset-entries` ≥ requests + warmup, keep a distinct seed per sweep point (the native sweep does; `--parameter-sweep-same-seed` turns it off), and restart the server (or `--reset-kv-cache`, v0.13.0+) before switching config. Multi-run confidence (`--num-profile-runs 3 --confidence-level 0.95`) yields CI bands when each run is short enough that re-running 3× is feasible; its trials share one seed by default, so on a prefix-caching server add `--vary-seed-per-trial` or trials 2..N measure a warm cache.

## Critical pitfalls

1. **Tokenizer mismatch.** Default tokenizer is whatever HF resolves from `--model`. If the served model and the HF ID differ (custom path, fine-tune, gated repo), every token-count metric is fiction. Always pass `--tokenizer <hf-id>` explicitly. For zero-network use `--tokenizer builtin` (tiktoken `o200k_base`, GPT-4o-class). Set `--tokenizer-trust-remote-code` for tokenizers that ship custom Python (Kimi K2.5, some DeepSeek). Pin via `--tokenizer-revision <sha>` to avoid silent drift on model-card updates.

2. **Reasoning-model TTFT/TTFO/OSL semantics.** AIPerf's TTFT counts reasoning tokens (`reasoning_content` SSE field); genai-perf's TTFT did not. To compare apples-to-apples to historical genai-perf numbers, read **TTFO** (time-to-first-output-token) instead. Same trap on OSL: aiperf OSL = output + reasoning, aiperf `output_token_count` = output only. **Prerequisite:** the server must surface `reasoning_content` as a separate SSE field (vLLM `--reasoning-parser deepseek_r1` / `qwen3` / `gpt_oss` etc.; SGLang `--reasoning-parser deepseek-r1`) — without it, aiperf can't separate streams and TTFO collapses to TTFT, `reasoning_token_count` stays 0. Verify with `curl ... | jq '.choices[0].delta.reasoning_content'` before trusting numbers. See `references/migration-from-genai-perf.md`.

3. **`--request-rate` alone, no concurrency cap.** The benchmark will queue indefinitely on slow servers and the timing manager will fall behind, producing a curve that looks like a system collapse but is really client-side queue buildup. Always pair with a sane `--concurrency` ceiling (e.g. 2–3× expected steady-state inflight).

4. **`--fixed-schedule` with synthetic data.** Fixed-schedule needs timestamped traces (mooncake / bailian / burst_gpt). It is auto-enabled for trace dataset types. Combining it with `--request-rate` or `--user-centric-rate` raises a validation error.

5. **`--isl-block-size` = the block size the trace was recorded at — never the server's.** Loader defaults: 512 `mooncake_trace` (the FAST25 trace's `hash_ids` are 512-token blocks), 16 `bailian_trace`; no effect on `baseten_trace`. Do **not** lower it to "match" the server (e.g. 64 for SGLang `--page-size 64`): aiperf then rebuilds every prompt proportionally shorter (~8×) and the prefix structure breaks — symptom: ISL far below the trace, TTFT too good, near-zero cache hits. Server alignment needs only that the server block size divides 512 (vLLM 16, SGLang 64 do). Confirm what the trace expects with `aiperf analyze-trace --input-file trace.jsonl --block-size 512`. Runs made with a lowered block size measured a different workload — discard and re-run; never keep them as a baseline.

6. **Skipping warmup on cold pods.** First N requests hit cold CUDA graphs / torch.compile caches / un-pinned KV pages. Warmup is opt-in: `--warmup-duration 30` or `--warmup-request-count 100`. Multi-run confidence has `--profile-run-disable-warmup-after-first` to amortize.

7. **Ignoring `--use-server-token-count` for OpenAI-compat servers.** When set, AIPerf reads token counts from the server's `usage` field instead of re-tokenizing client-side. Auto-enables `stream_options.include_usage` for streaming. This avoids client/server tokenizer drift entirely. Use this whenever the server is trustworthy. The `--tokenizer` flag is still required (for input-shape generation) but `tokenizer.encode()` is not called for metrics.

8. **`--export-level raw` on a long run.** Writes every request/response payload to disk. Fine for 1k requests, catastrophic for 1M. Default is `records` (per-request metrics, no payloads); only escalate when actually debugging. On v0.13.0 a raw export that takes more than ~20 s ends in exit 1 with `RequiredServiceReaped` although every request completed — the heartbeat watchdog reaps services during export; set `AIPERF_SERVICE_HEARTBEAT_MISSED_THRESHOLD=24`. Exit 0 does not prove the raw file is complete: a record processor force-killed at shutdown truncates it. Check `wc -l profile_export_raw.jsonl` against the request count before recomputing metrics from it.

9. **Async video generation polling.** `endpoint-type video_generation` polls `/v1/videos/{job_id}` until the job completes. Tune `AIPERF_HTTP_VIDEO_POLL_INTERVAL` (default 0.1 s) — faster polling burns server resources, slower polling inflates request latency. With `--download-video-content`, request latency includes the bytes download.

10. **`--goodput` is per-request, not per-percentile.** The flag asks "is this individual request below the threshold?" and reports `good_request_count / benchmark_duration` as `goodput`. There is no built-in `p99_time_to_first_token:400` syntax. To express "p99 TTFT must be ≤ 400 ms", set `--goodput "time_to_first_token:400"` and check `goodput / request_throughput ≥ 0.99` post-run — that ratio is the fraction of requests meeting all SLOs, which for a single threshold is exactly the "X% under the budget" measure operators usually want. Combine multiple thresholds and the same ratio still works as joint compliance.

## Done = every row checked before a number leaves the run

| Check | Evidence in `profile_export_aiperf.json` / the run |
|---|---|
| All requests ran | `request_count` equals the requested count (or sessions × turns); `error_request_count` is 0 or each error is explained. Exit 1 with only `RequiredServiceReaped` on v0.13.0 is pitfall 8, not a failed run |
| The workload is the intended one | mean `input_sequence_length` / `output_sequence_length` match `--isl`/`--osl`, or the trace's `analyze-trace` figures (pitfall 5) |
| Cache state is known | pool ≥ requests, distinct seed per point and trial, server cache reset or restarted between configs (Methodology B) |
| Reasoning split works (reasoning models) | `reasoning_token_count` > 0, TTFO ≠ TTFT (pitfall 2) |
| Run is reproducible | `--tokenizer` explicit and `--tokenizer-revision` pinned; `aiperf --version`, server image and flags recorded beside the artifact dir |
| SLO verdict is per-percentile where the SLO says so | goodput ratio or exported p95/p99 values, not the raw `goodput` number (pitfall 10) |

## What to read next — and when

| File | Read when... |
|---|---|
| `references/cli.md` | Looking up a specific flag or composing a command. Table of contents at top — read the section, not the file. |
| `references/timing-modes.md` | Picking concurrency vs rate vs fixed-schedule vs user-centric. Compatibility matrix + every validation error message. |
| `references/metrics.md` | Defining what a metric means, its unit, its formula, or which streaming/endpoint types it applies to. Goodput SLO syntax. |
| `references/datasets.md` | Choosing or building an input dataset (synthetic, public, custom JSONL, trace formats). Multi-modal payload shapes. |
| `references/endpoints.md` | Wiring a non-OpenAI inference target (NIM, Cohere, HF TEI, Solido, custom template). |
| `references/output-artifacts.md` | Parsing `profile_export*.{json,jsonl,csv}` programmatically. `MetricRecordInfo` Pydantic schema, correlating inputs to records. |
| `references/plugins.md` | Adding a custom endpoint, dataset loader, exporter, accuracy grader, or plot type. Plugin manifest schema, conflict resolution rules. |
| `references/troubleshooting.md` | A specific error message, a wrong-looking number, or an exporter that produced nothing. |
| `references/migration-from-genai-perf.md` | Porting a genai-perf workflow. Flag mapping + the reasoning-token metric semantics that subtly change the numbers. |
| `references/sources.md` | Checking where a version, flag or issue claim comes from, or freshening the skill. The `Freshened:` header stamp dates the last full verification. |

The upstream repo at https://github.com/ai-dynamo/aiperf is the most authoritative reference — `docs/cli-options.md`, `docs/metrics-reference.md`, `docs/environment-variables.md`, and `docs/tutorials/*.md` are all auto-generated or hand-curated from the same code. When this skill disagrees with the repo, trust the repo (and update this skill).

## Quick recipes

### Smoke test a vLLM endpoint

```bash
aiperf profile --model Qwen/Qwen3-0.6B --url http://localhost:8000 \
  --endpoint-type chat --streaming --tokenizer Qwen/Qwen3-0.6B \
  --concurrency 10 --request-count 100 --isl 1000 --osl 500
```

### ShareGPT against an OpenAI-compatible server

```bash
aiperf profile --model my-model --url http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-tokenizer \
  --public-dataset sharegpt --num-sessions 200 --concurrency 50
```

### Mooncake trace replay with goodput

```bash
curl -O https://raw.githubusercontent.com/kvcache-ai/Mooncake/refs/heads/main/FAST25-release/arxiv-trace/mooncake_trace.jsonl
aiperf profile --model my-model --url http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-tokenizer \
  --input-file mooncake_trace.jsonl --custom-dataset-type mooncake_trace --fixed-schedule \
  --goodput "time_to_first_token:400 request_latency:2000"
```

### NIM embeddings benchmark

```bash
aiperf profile --model nvidia/nv-embedqa-e5-v5 --url http://nim:8000 \
  --endpoint-type nim_embeddings --tokenizer intfloat/e5-large-v2 \
  --concurrency 32 --request-count 5000 --prompt-batch-size 16
```

### Custom multi-turn JSONL with shared system prompt

```bash
aiperf profile --model my-model --url http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-tokenizer \
  --input-file conversations.jsonl --custom-dataset-type multi_turn \
  --shared-system-prompt-length 1000 --user-context-prompt-length 200 \
  --num-sessions 50 --concurrency 25
```

### Goodput per concurrency point with multi-run CI

```bash
aiperf profile --model my-model --url http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-tokenizer \
  --concurrency 100 --request-count 2000 --isl 1000 --osl 500 \
  --num-dataset-entries 2000 --vary-seed-per-trial \
  --num-profile-runs 5 --confidence-level 0.95 \
  --profile-run-cooldown-seconds 30 \
  --goodput "time_to_first_token:300 inter_token_latency:8"
```

### MMLU accuracy benchmark

```bash
aiperf profile --model my-model --url http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-tokenizer \
  --accuracy-benchmark mmlu --accuracy-n-shots 5 --accuracy-grader multiple_choice
```

For the full flag catalogue, validation rules, and every endpoint/dataset/metric option, drill into the `references/` files.
