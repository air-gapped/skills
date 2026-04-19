# Benchmarking methodology

Load when designing a benchmark run — what to measure, how to avoid the mistakes that produce misleading numbers, how to structure A/B comparisons.

## Table of contents
- [Warmup](#warmup)
- [Request-rate sweeps](#request-rate-sweeps)
- [SLO-constrained goodput](#slo-constrained-goodput)
- [Prefix-cache-aware benchmarks](#prefix-cache-aware-benchmarks)
- [Capturing production prompts for replay](#capturing-production-prompts-for-replay)
- [Disaggregated prefill benchmarks](#disaggregated-prefill-benchmarks)
- [Interpreting results](#interpreting-results)

## Warmup

vLLM with `torch.compile`, CUDA graphs, or prefix caching needs warmup. The first 30–60 s of any benchmark hits cold caches. `vllm bench serve` does not auto-warm — operators must.

**Three options:**

1. **Pre-flight the server** before starting the benchmark. Send 20–50 requests, discard. Then launch `vllm bench serve`.
2. **Make `--num-prompts` large enough to amortize.** At ≥500 prompts the startup bump barely affects aggregate percentiles. Still-biased for P99 ITL if the run is short.
3. **Use `--num-warmups N`** (serve subcommand). Pre-loads N requests before measurement starts. Respects `--max-concurrency` during warmup. Defaults to 0 — set it explicitly.

`bench latency` already warms via `--num-iters-warmup 10` by default.

## Request-rate sweeps

The most common mistake: running one `--request-rate inf` test and calling it done. That measures saturation throughput. It does not reveal the latency regime users actually experience.

**The right pattern for a change comparison:**

```bash
for RATE in 1 2 4 8 16 32 inf; do
  vllm bench serve \
    --model <model> --base-url <url> \
    --dataset-name sharegpt --dataset-path /data/sharegpt.json \
    --request-rate $RATE \
    --num-prompts 1000 \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,95,99 \
    --save-result --output-json "sweep-${RATE}.json"
done
```

Plot: x-axis = request rate (or achieved throughput), y-axis = P99 TTFT. The **knee** is the usable operating point. A config that shifts the knee right (more RPS at same P99) is a real win.

**For closed-loop tests:** replace `--request-rate` with `--max-concurrency` at sweep values — this mimics fixed-pool-of-clients load.

`vllm bench sweep` automates this with Pareto-frontier plotting. See `commands.md`.

## SLO-constrained goodput

Raw throughput is not what matters in production. Goodput is — the rate of requests that completed *within their SLO*.

`vllm bench serve --goodput ttft:500 itl:50` tracks what fraction of requests met both budgets (TTFT ≤ 500 ms AND ITL ≤ 50 ms). Use this number for capacity planning: "our SLO budget supports N goodput-compliant RPS at this config."

For auto-tune: `vllm bench sweep` can search for the maximum `--max-concurrency` that keeps goodput above a threshold.

## Prefix-cache-aware benchmarks

`--dataset-name random` defeats prefix caching — uniform random tokens share no structure. A cache-on-vs-off benchmark on random data shows no difference and misleads into "caching doesn't help."

**Correct approach:**

```bash
# Controlled synthetic — known prefix overlap:
vllm bench serve ... \
  --dataset-name prefix_repetition \
  --prefix-repetition-prefix-len 1024 \
  --prefix-repetition-suffix-len 128 \
  --prefix-repetition-num-prefixes 10 \
  --prefix-repetition-output-len 128
```

Or use `custom` with real traffic that has natural prefix locality (system prompts, RAG retrievals, agent tool definitions).

When benchmarking caching wins, watch the Prometheus metric `prefix_cache_hits_total / prefix_cache_queries_total` — this is the hit rate the server actually saw, independent of whatever the benchmark reports.

## Capturing production prompts for replay

The single most valuable benchmark input. Steps:

1. **Log prompts only** (not completions — avoids PII surface). Schema:
   ```json
   {"prompt": "...", "output_tokens": 247}
   ```
2. Capture a **representative window** — 1–3 hours covering expected peak, across weekdays. 5000–20000 prompts is plenty.
3. Write to JSONL (one object per line). Keep the file stable for the lifetime of the benchmark series so A/B results are comparable.
4. Use: `--dataset-name custom --dataset-path prod-replay.jsonl`.

Sanitize aggressively if the data has any chance of containing secrets. Replace customer names, API keys, emails. A regex pass over prompts before writing works fine.

## Disaggregated prefill benchmarks

Disagg prefill (separate prefill/decode instances via NixlConnector or Mooncake) benchmarks differently — end-to-end latency spans a two-hop request path.

Use the recipes at `benchmarks/disagg_benchmarks/` in the vLLM tree. Key differences from single-instance:
- Measure TTFT including the prefill-to-decode KV transfer. This transfer is the new critical path.
- Tune prefill and decode `--max-num-batched-tokens` independently.
- Compare against a single-instance baseline with equivalent total GPU count to know if disagg earned the complexity.

## Interpreting results

**P50 alone lies.** Anyone reporting "median TTFT of 200 ms, our deployment is fast" without P99 is hiding a tail. A common prod failure mode: P50 is great, P99 is 5× worse, and the P99 users churn.

**Token counts are fiction if `--tokenizer` is wrong.** Always check: if tokens/sec looks 30% off from prior runs, first suspect is tokenizer mismatch.

**Don't compare across hardware.** Run A on one box, B on another — impossible to distinguish config delta from hardware/thermal delta. Run both on the same host back-to-back; ideally same session.

**Report everything.** For a change comparison, report: request rate, achieved RPS, P50/P95/P99 for TTFT/TPOT/ITL/E2EL, tokens/sec, goodput at SLO. Omitting any of these invites someone to assume the worst about the hidden number.

**One more time:** warmup. Check that throughput isn't quietly including the cold-cache start. Always.
