---
name: aiperf
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  NVIDIA AIPerf — vendor-neutral generative-AI inference benchmarking (genai-perf successor). Covers `aiperf profile` with concurrency / request-rate / fixed-schedule trace replay / user-centric / multi-run confidence, 15 endpoint types (chat, completions, embeddings, rankings, responses, image-gen, video-gen, NIM, HF-TGI, template, etc.), 6 custom dataset formats (single_turn, multi_turn, mooncake_trace, bailian_trace, burst_gpt_trace, random_pool), 40+ public datasets, goodput SLOs, GPU + Prometheus telemetry, plot/analyze-trace/synthesize/service subcommands, plugin extensibility, and reasoning-token TTFT/TTFO split.
when_to_use: |-
  Trigger on "aiperf", "ai-dynamo/aiperf", "genai-perf migration", or "benchmark vllm / sglang / trt-llm / dynamo / nim / triton / ollama" — vendor-neutral, prefer over `vllm bench` when target is non-vLLM or trace-driven. Also `aiperf profile / plot / plugins / analyze-trace / synthesize / service`, "mooncake / bailian / burstgpt trace", "sharegpt", "speed-bench", "MMLU / AIME accuracy benchmark", "TTFO / time-to-first-output-token", "reasoning-token TTFT split", "goodput SLO", "DistServe goodput", "fixed-schedule replay", "user-centric rate", "prefill concurrency", "multi-run confidence", "DCGM / pynvml telemetry", "profile_export.jsonl", "NIM embeddings/rankings", "HF TEI rerank", "image / video generation benchmark", "register custom endpoint / dataset plugin". Defer to `vllm-benchmarking` for `vllm bench` workflows.
---

# AIPerf — NVIDIA generative-AI inference benchmarking

Target audience: operators producing defensible latency/throughput/goodput numbers against any OpenAI-compatible inference server (vLLM, SGLang, TensorRT-LLM, NVIDIA Dynamo, NIM, Triton, HF TGI, Ollama), and developers extending AIPerf with custom endpoints, datasets, exporters, or metrics.

## Why this matters

`aiperf` is the open-source successor to `genai-perf`, written by NVIDIA's AI-Dynamo team. It is **the** vendor-neutral way to:

1. **Replay production traces** (Mooncake / Bailian / BurstGPT) at exact timestamps — synthetic load lies about cache reuse and tail behavior.
2. **Measure goodput**, not just throughput — the percentage of requests that meet **all** SLOs simultaneously. A system at 1000 req/s throughput and 28% goodput is mis-provisioned by ~3.5×.
3. **Account for reasoning tokens correctly.** GPT-OSS / DeepSeek-R1 / Qwen3 emit `reasoning_content` before the answer. genai-perf ignored those; aiperf splits **TTFT** (any first token) from **TTFO** (first non-reasoning token). Numbers are not directly comparable across the two tools — see migration notes.
4. **Collect server + GPU telemetry alongside client-side timings** in one run — DCGM / pynvml GPU metrics + Prometheus `/metrics` scrape, all aligned in the same artifact dir.
5. **Extend cleanly** — 25 plugin categories with a YAML manifest + entry-point system. New endpoints, dataset formats, exporters, accuracy graders, plot types all go through the same registry.

If the target is exclusively vLLM and the operator wants the in-tree `vllm bench` toolchain (sweep, latency-only, startup, mm-processor), defer to the `vllm-benchmarking` skill. AIPerf is the right answer when (a) the target is non-vLLM or (b) the workload is trace-driven, multi-modal, multi-server, or needs goodput.

## Versions

- **Stable on PyPI:** v0.7.0 (2026-04-07). `pip install aiperf`.
- **Repo `main`** at https://github.com/ai-dynamo/aiperf: 0.8.0-dev (post-v0.7.0).
- **Python:** ≥3.10. Uses `uvloop` on Linux/macOS, falls back to default asyncio on Windows.
- **Source of truth for flags:** `aiperf profile --help`. CLI options doc is auto-generated via `make generate-cli-docs`. If the doc disagrees with `--help` on a flag spelling, trust `--help`.

## Decision tree — which subcommand

| Question | Subcommand | Why |
|---|---|---|
| "Run a benchmark" | `aiperf profile` | The main command. 99% of tasks. |
| "Plot the result" | `aiperf plot` | Pareto, latency histograms, time-series, side-by-side runs. `--dashboard` for interactive. |
| "What plugins are installed?" | `aiperf plugins [<category> [<name>]]` | Inspect + validate the plugin registry. |
| "Inspect a Mooncake trace before benchmarking" | `aiperf analyze-trace <file.jsonl>` | ISL/OSL distribution + cache-hit-rate stats. Use to size the benchmark. |
| "Make a synthetic trace from a real one" | `aiperf synthesize` | Scale prefix length, speedup ratio, prefix tree count for KV-cache stress. |
| "Run as a single Kubernetes service" | `aiperf service` | One service per pod, ZMQ + FastAPI control. K8s-native deployments. |
| "Validate an artifact dir" | `aiperf validate` | Sanity check that exports are well-formed. |
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
for c in 10 50 100 200 500; do
  aiperf profile \
    --model Qwen/Qwen3-0.6B --url http://endpoint:8000 \
    --endpoint-type chat --streaming \
    --tokenizer Qwen/Qwen3-0.6B \
    --concurrency $c --request-count 1000 \
    --isl 1000 --osl 500 \
    --random-seed 42 \
    --artifact-dir artifacts/pareto-c$c
done
aiperf plot --paths artifacts/pareto-c* --dashboard
```

Same seed, same dataset, back-to-back runs, same hardware. Multi-run confidence (`--num-profile-runs 3 --confidence-level 0.95`) yields CI bands when each run is short enough that re-running 3× is feasible.

## Critical pitfalls

1. **Tokenizer mismatch.** Default tokenizer is whatever HF resolves from `--model`. If the served model and the HF ID differ (custom path, fine-tune, gated repo), every token-count metric is fiction. Always pass `--tokenizer <hf-id>` explicitly. For zero-network use `--tokenizer builtin` (tiktoken `o200k_base`, GPT-4o-class). Set `--tokenizer-trust-remote-code` for tokenizers that ship custom Python (Kimi K2.5, some DeepSeek). Pin via `--tokenizer-revision <sha>` to avoid silent drift on model-card updates.

2. **Reasoning-model TTFT/TTFO/OSL semantics.** AIPerf's TTFT counts reasoning tokens (`reasoning_content` SSE field); genai-perf's TTFT did not. To compare apples-to-apples to historical genai-perf numbers, read **TTFO** (time-to-first-output-token) instead. Same trap on OSL: aiperf OSL = output + reasoning, aiperf `output_token_count` = output only. **Prerequisite:** the server must surface `reasoning_content` as a separate SSE field (vLLM `--reasoning-parser deepseek_r1` / `qwen3` / `gpt_oss` etc.; SGLang `--reasoning-parser deepseek-r1`) — without it, aiperf can't separate streams and TTFO collapses to TTFT, `reasoning_token_count` stays 0. Verify with `curl ... | jq '.choices[0].delta.reasoning_content'` before trusting numbers. See `references/migration-from-genai-perf.md`.

3. **`--request-rate` alone, no concurrency cap.** The benchmark will queue indefinitely on slow servers and the timing manager will fall behind, producing a curve that looks like a system collapse but is really client-side queue buildup. Always pair with a sane `--concurrency` ceiling (e.g. 2–3× expected steady-state inflight).

4. **`--fixed-schedule` with synthetic data.** Fixed-schedule needs timestamped traces (mooncake / bailian / burst_gpt). It is auto-enabled for trace dataset types. Combining it with `--request-rate` or `--user-centric-rate` raises a validation error.

5. **`--isl-block-size` and the Mooncake/server block-size relationship — read this carefully.** Mooncake traces encode `hash_ids` at **512-token granularity by design** — the trace was generated with that block size and the IDs only make sense at 512. Do **not** lower `--isl-block-size` to "match the server" (e.g. 64 for SGLang `--page-size 64`); doing so makes aiperf reconstruct prompts ~8× shorter than the trace intends and corrupts the ISL distribution. What matters is whether **512 is a multiple of the server's block size** — if yes (e.g. SGLang 64 → 512/64=8, vLLM 16 → 512/16=32), each Mooncake block aligns with N server pages and prefix-cache reuse works fine. If the server block size doesn't divide 512, that's the broken case. Run `aiperf analyze-trace --input-file trace.jsonl --block-size 512` to confirm what the trace expects.

6. **Skipping warmup on cold pods.** First N requests hit cold CUDA graphs / torch.compile caches / un-pinned KV pages. Warmup is opt-in: `--warmup-duration 30` or `--warmup-request-count 100`. Multi-run confidence has `--profile-run-disable-warmup-after-first` to amortize.

7. **Ignoring `--use-server-token-count` for OpenAI-compat servers.** When set, AIPerf reads token counts from the server's `usage` field instead of re-tokenizing client-side. Auto-enables `stream_options.include_usage` for streaming. This avoids client/server tokenizer drift entirely. Use this whenever the server is trustworthy. The `--tokenizer` flag is still required (for input-shape generation) but `tokenizer.encode()` is not called for metrics.

8. **`--export-level raw` on a long run.** Writes every request/response payload to disk. Fine for 1k requests, catastrophic for 1M. Default is `records` (per-request metrics, no payloads); only escalate when actually debugging.

9. **CSV export prefix conflict.** `--profile-export-prefix /abs/path/run1` was broken pre-v0.7.0 (PR #801 fixed it). On v0.7.0+ this works; on older builds use a relative prefix and `--artifact-dir`.

10. **Async video generation polling.** `endpoint-type video_generation` polls `/v1/videos/{job_id}` until the job completes. Tune `AIPERF_HTTP_VIDEO_POLL_INTERVAL` (default 0.1 s) — faster polling burns server resources, slower polling inflates request latency. With `--download-video-content`, request latency includes the bytes download.

11. **`--goodput` is per-request, not per-percentile.** The flag asks "is this individual request below the threshold?" and reports `good_request_count / benchmark_duration` as `goodput`. There is no built-in `p99_time_to_first_token:400` syntax. To express "p99 TTFT must be ≤ 400 ms", set `--goodput "time_to_first_token:400"` and check `goodput / request_throughput ≥ 0.99` post-run — that ratio is the fraction of requests meeting all SLOs, which for a single threshold is exactly the "X% under the budget" measure operators usually want. Combine multiple thresholds and the same ratio still works as joint compliance.

## What to read next — and when

| File | Read when... |
|---|---|
| `references/cli.md` | Looking up a specific flag or composing a command. ~350 lines, table-of-contents at top. |
| `references/timing-modes.md` | Picking concurrency vs rate vs fixed-schedule vs user-centric. Compatibility matrix + every validation error message. |
| `references/metrics.md` | Defining what a metric means, its unit, its formula, or which streaming/endpoint types it applies to. Goodput SLO syntax. |
| `references/datasets.md` | Choosing or building an input dataset (synthetic, public, custom JSONL, trace formats). Multi-modal payload shapes. |
| `references/endpoints.md` | Wiring a non-OpenAI inference target (NIM, Cohere, HF TEI, Solido, custom template). |
| `references/output-artifacts.md` | Parsing `profile_export*.{json,jsonl,csv}` programmatically. `MetricRecordInfo` Pydantic schema, correlating inputs to records. |
| `references/plugins.md` | Adding a custom endpoint, dataset loader, exporter, accuracy grader, or plot type. Plugin manifest schema, conflict resolution rules. |
| `references/troubleshooting.md` | A specific error message, a wrong-looking number, or an exporter that produced nothing. |
| `references/migration-from-genai-perf.md` | Porting a genai-perf workflow. Flag mapping + the reasoning-token metric semantics that subtly change the numbers. |
| `references/sources.md` | Verifying or freshening external claims. Per-row `Last verified:` dates. |

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
