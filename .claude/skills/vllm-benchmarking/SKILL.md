---
name: vllm-benchmarking
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  Run production vLLM benchmarks — `vllm bench` (serve, throughput, latency, sweep, startup, mm-processor), request-rate vs max-concurrency semantics, TTFT/TPOT/ITL/E2EL percentiles, goodput SLO measurement, prefix-cache workloads, air-gapped operation (HF_ENDPOINT, ModelScope, hf-mirror, offline cache). Methodology split — SLO health checks vs A/B change sweeps — plus pitfalls that produce misleading numbers (no warmup, wrong tokenizer, random-as-prod, `--request-rate inf` alone).
when_to_use: |-
  Trigger on "vllm bench", "benchmark vllm", "load test vllm", "measure TTFT", "measure TPOT", "ITL", "P99 latency", "throughput test", "request rate sweep", "max-concurrency", "goodput", "bench serve", "bench throughput", "bench latency", "SLO test", "sharegpt dataset", "sonnet dataset", "burstgpt", "vllm perf numbers", "does this deploy get faster", "compare two vllm configs", "tune request rate", "prove SLO", "prefix cache benchmark", "disagg benchmark". Also air-gapped benchmarking (HF_ENDPOINT, hf-mirror, ModelScope, HF_HUB_OFFLINE, pre-seeded cache). Also implicit contexts — "bench model X", "perf numbers for {model}", "audit benchmark", "can {model} hit TTFT Y", "deploy-memo perf", "spec-study performance" — any time producing defensible numbers or comparing two deployments.
---

# vLLM benchmarking

Target audience: operators producing defensible latency/throughput numbers against production or pre-production vLLM deployments, on datacenter GPUs, often in containerized or air-gapped environments.

## Why this matters

Bad benchmarks are worse than no benchmarks — they drive the wrong decisions with false confidence. The three common failure modes:

1. **Wrong methodology.** `--request-rate inf` answers "saturation throughput," not "TTFT my users see." Mixing those up leads to buying GPUs to solve a latency problem, or shipping a latency regression because total throughput looked fine.
2. **Wrong workload.** `--dataset-name random` has zero prefix structure. Real coding-agent or RAG traffic has heavy prefix reuse. Benchmarking caching wins on random produces numbers that don't survive contact with prod.
3. **No warmup / wrong tokenizer.** First N requests hit cold CUDA graphs. Token counts are fiction unless `--tokenizer` matches the served model exactly.

The cost of getting this right is small; the cost of getting it wrong is buying the wrong hardware.

## Decision tree — which subcommand

| Question | Command | Why |
|---|---|---|
| "Saturation throughput of this offline batch" | `vllm bench throughput` | Submits N prompts at once, measures tok/s. No server. |
| "Single-batch generation latency" | `vllm bench latency` | Fixed batch size, repeated N times. Warmup included. Good for kernel-level regression. |
| "Production serving performance" | `vllm bench serve` | HTTP-level, Poisson arrivals, percentile metrics, honors concurrency caps. Use this for serving. |
| "Find best config under SLO" | `vllm bench sweep` | Parameter sweep + auto-tune. Finds max throughput subject to P99 < X ms. |
| "Cold-start / container boot latency" | `vllm bench startup` | Time from process launch to first-token-ready. |
| "Multimodal processor overhead" | `vllm bench mm-processor` | Image/video preprocessing cost before decode. |

Most production questions route to `vllm bench serve`. Reach for the others only when the question is specifically kernel-level (latency), offline-batch (throughput), or SLO auto-tuning (sweep).

## The two methodologies operators actually need

### Methodology A: health check / SLO validation

**Question:** "Does my running deployment meet the latency SLO under realistic load?"

- Fixed `--max-concurrency` matching the production in-flight ceiling (NOT `--request-rate`).
- Realistic input/output length distribution — ideally replayed from production logs via `--dataset-name custom` with a JSONL file.
- Sustained 10+ minute run to cover warmup + steady state.
- Report: P50/P95/P99 TTFT, P95/P99 ITL, throughput (tok/s, req/s).
- Compare against the SLO. Pass/fail.

```bash
vllm bench serve \
  --model <served-model> \
  --base-url http://<endpoint> \
  --dataset-name custom \
  --dataset-path /data/captured-prod-prompts.jsonl \
  --max-concurrency 32 \
  --num-prompts 2000 \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,95,99 \
  --save-result --output-json health-check.json
```

### Methodology B: change comparison / A/B

**Question:** "Does config change X make it faster, and at what cost?"

- **Request-rate sweep**, not a single rate: e.g. 1, 2, 4, 8, 16, 32, inf req/s.
- Plot throughput vs P99 latency — the **knee of the curve is the usable operating point**. A config that shifts the knee right is a win.
- Same seeds, same `--num-prompts` (≥500), same dataset on both sides.
- Run A and B back-to-back on the same hardware in the same session to avoid thermal/neighbor noise.

See `scripts/bench-sweep.sh` for a parametrized sweep runner that emits one JSON file per rate for plotting.

## Critical pitfalls

1. **No warmup.** First 30–60 s hit cold CUDA graphs / torch.compile caches. `vllm bench serve` does not auto-warm (as of v0.19) — pre-flight the server with a few requests, or set `--num-prompts` large enough (≥500) to amortize. `latency` does warm up via `--num-iters-warmup` (default 10).
2. **Wrong tokenizer.** `--tokenizer` defaults to `--model`, but if they differ (e.g., served via a local path while benching with a HF ID), every token count in the output is fiction. Always specify explicitly.
3. **`--dataset-name random` as a proxy for production traffic.** Random has zero prefix structure, overstates prefill work, understates prefix-cache hit rate, makes chunked prefill look worse than reality. For anything involving caching claims, use `custom` with a real-traffic JSONL, or `prefix_repetition` for synthetic prefix-heavy tests.
4. **`--request-rate inf` alone.** Measures saturation throughput, not the latency regime users experience. Always include a concurrency sweep for serving comparisons.
5. **`--endpoint-type` is removed.** Deprecated in v0.11.0, now gone. Use `--backend`. Current full value set (docs.vllm.ai, verified 2026-04-24): `openai`, `openai-chat`, `openai-audio`, `openai-embeddings`, `openai-embeddings-chat`, `openai-embeddings-clip`, `openai-embeddings-vlm2vec`, `vllm`, `vllm-chat`, `vllm-pooling`, `vllm-rerank`, `infinity-embeddings`, `infinity-embeddings-clip`.
6. **Conflating tok/s with req/s.** High total-tokens/sec can coexist with terrible TTFT. Always report both plus P99 ITL.
7. **Noisy neighbor.** Shared GPU, unrelated container load, MIG partition changes mid-run — check `nvidia-smi dmon` for unrelated activity before trusting numbers.
8. **`latency` subcommand disables prefix caching by default** (to keep numbers clean). If benchmarking prefix-cache behavior, use `serve` with the `prefix_repetition` dataset.

For the full flag reference for each subcommand, see `references/commands.md`. For the dataset catalog and when to use each, see `references/datasets.md`.

## Air-gapped environments

Operators who can't reach `huggingface.co` have three working patterns:

1. **Reroute to a mirror** — set `HF_ENDPOINT=https://hf-mirror.com` (or an internal reverse-proxy URL). `huggingface_hub` treats it transparently.
2. **ModelScope** — set `VLLM_USE_MODELSCOPE=True` plus `trust_remote_code=True`. Historical gap: LoRA adapter loading through ModelScope (vLLM issue #32841, closed 2026-01-23). Re-verify on your vLLM version before relying on LoRA-via-ModelScope; issue closure without a linked PR means status is unclear — test first.
3. **Fully offline with pre-seeded cache** — `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1`, `HF_HOME` pointing at a pre-populated directory (NFS, PVC, or JuiceFS/S3).

For benchmark datasets specifically: `sonnet` is **in-tree** at `vllm/benchmarks/sonnet.txt` — never downloads. `random` is synthetic — never downloads. `sharegpt` must be pre-staged: `wget` the JSON on a connected host, `rsync` into the enclave, point `--dataset-path` at it.

For the full air-gapped recipe (HF proxy setup, gated model tokens, MinIO-as-HF-cache, transformer cache warming), see `references/air-gapped.md`.

## Measuring the outcomes that matter

Default metrics (`--percentile-metrics ttft,tpot,itl,e2el`):

- **TTFT** — time-to-first-token. User-facing responsiveness. Dominated by prefill.
- **TPOT** — time-per-output-token (averaged across decode). Steady-state perceived speed.
- **ITL** — inter-token latency (per-step). Catches stalls that TPOT averages away.
- **E2EL** — end-to-end request latency. Only one that matters for pooling/embedding models.

Reporting guideline: **always P50 and P99 together**. Either in isolation is misleading. Add P95 if ITL has a long tail.

**Goodput SLO** — `--goodput KEY:VALUE` (milliseconds) tracks requests that completed within an SLO budget. Example: `--goodput ttft:500 itl:50`. Goodput is what actually matters in production; raw throughput that violates SLO is useless.

For methodology detail (warmup protocols, sweep design, SLO-constrained auto-tune, how to capture real-traffic prompts for replay), see `references/methodology.md`.

## When numbers look wrong or a run crashes

See `references/troubleshooting.md` for the failure modes: tokenizer mismatch (numbers off 20–40%), cold-cache contamination (suspiciously fast), air-gapped hang (incomplete `HF_HUB_OFFLINE` setup), goodput=0 (unit error), noisy-neighbor ITL variance, and the full "what to include in a bug report" checklist.

## Parsing the output JSON

See `references/output-schema.md` for the field layout in `--output-json` — top-level fields (`request_throughput`, `output_throughput`, `total_token_throughput`), the `mean_/median_/std_/p<N>_<metric>_ms` pattern, speculative decoding fields, and which names are stable across versions vs renamed.

## External references

- vLLM bench CLI docs: https://docs.vllm.ai/en/latest/benchmarking/cli/
- `vllm bench serve` reference: https://docs.vllm.ai/en/stable/cli/bench/serve/
- Performance dashboard (nightly reference numbers): https://docs.vllm.ai/en/latest/benchmarking/dashboard/
- In-tree benchmarks dir: https://github.com/vllm-project/vllm/tree/main/benchmarks
- Air-gapped discussion thread: https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916
- vLLM env vars (including `VLLM_USE_MODELSCOPE`): https://docs.vllm.ai/en/stable/configuration/env_vars/
- Blog: Anatomy of a High-Throughput LLM Inference System (2025-09-05): https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html
- Blog: Large Scale Serving — DeepSeek @ 2.2k tok/s/H200 (2025-12-17): https://blog.vllm.ai/2025/12/17/large-scale-serving.html
