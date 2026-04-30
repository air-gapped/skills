# Gemma 4 31B AWQ — full benchmark table from 2026-04-30 Verda audit

Hardware: Verda 2× H100 80GB SXM5 (NVLink), single VM
Engine: vLLM 0.20.0, kv-cache-dtype fp8, EAGLE3 k=3 chain spec-dec
Model: cyankiwi/gemma-4-31B-it-AWQ-4bit
Chat template: canonical Google `gemma-4-31B-it/chat_template.jinja` (sha256 `94899c0f9...`)
Bench tool: `vllm bench serve --backend openai-chat`, deterministic (--temperature 0.0 --seed 42)
All numbers measured with `--num-warmups 5` (or 3 for long-context to save time).

## Phase 1 — TP=1 max_num_seqs sweep at fixed config

Workload: random 4096 in / 512 out, num_prompts=400.
Fixed: max_model_len=32768, max_num_batched_tokens=8192, util=0.85
(except 128/256 rows which used util=0.90 to allow more KV).

| max_num_seqs | bench c | tok/s out | tok/s total | TPOT mean (ms) | TTFT mean (s) | Peak in-flight | Acceptance |
|---|---|---|---|---|---|---|---|
| 32 | 32 | 397.95 | 3591.97 | 74.20 | 2.9 | 38 | 42.76% |
| 48 | 48 | 399.63 | 3607.14 | 109.57 | 4.8 | 52 | 43.02% |
| **64** | **80** | **408.65** | **3688.50** | **141.44** | 25.9 | (cap=64) | 43.40% |
| 128 | 128 | 397.41 | 3587.04 | 168.74 | 70.5 | 131 | 43.11% |
| 256 | 256 | 400.26 | 3612.83 | 165.04 | 181.8 | 261 | 42.54% |

**Observations**: peak at max_num_seqs=64 + c=80. Throughput unimodal.
Above 64, more concurrency just queues — TTFT explodes (2.9s →
181.8s) but tok/s is flat. This is the HBM-bandwidth-bound knee for
H100.

## Phase 2 — TP=2 short-context concurrency sweep (LIGHT config)

Workload: random 4096 in / 512 out, num_prompts=400.
Config: TP=2, max_model_len=32768, util=0.85, max_num_seqs=64,
max_num_batched_tokens=8192.

| bench c | tok/s out | tok/s total | TPOT mean (ms) | TTFT mean (s) | Peak in-flight |
|---|---|---|---|---|---|
| 128 | 741.18 | 6689.96 | 78.02 | 42.6 | 133 |
| 192 | 745.01 | 6724.53 | 77.69 | 74.5 | 197 |

**TP=2 plateau at c=128** matching the bandwidth doubling story
(weights split across 2 cards = effective bandwidth doubles). Adding
more concurrency past 128 just queues.

## Phase 2 — TP=2 short-context PUSH config

Same workload, config: TP=2, max_model_len=**262144**, util=**0.94**,
max_num_seqs=**256**, max_num_batched_tokens=**16384**.

| bench c | tok/s out | TPOT mean (ms) | TTFT mean (s) | Peak in-flight |
|---|---|---|---|---|
| 128 | 728.98 | 143.88 | 13.5 | 138 |
| 192 | 734.82 | 198.24 | 27.7 | 200 |
| 256 | 729.67 | 200.20 | 64.4 | 265 |

**PUSH costs ~2% throughput vs LIGHT** at short context (728 vs 741) and
**doubles TPOT** (143 vs 78 ms). Larger max_model_len + max_num_seqs
=  larger cudagraph buffers + more block-table overhead per step.
TTFT actually IMPROVED at PUSH because bigger maxSeqs admits requests
faster. **PUSH is for long-context capability, not for short-context
peak throughput.**

## Phase 2 — TP=2 long-context PUSH

Workload: random **16384 in / 1024 out**, num_prompts=100.

| bench c | tok/s out | tok/s total | TPOT (ms) | TTFT (s) | Peak in-flight |
|---|---|---|---|---|---|
| 14 | 203.36 | 3459.85 | 61.6 | 5.4 | 16 |
| 32 | 255.80 | 4351.93 | 100.7 | 17 | 36 |
| 64 | 278.54 | 4738.79 | 154 | 58 | 67 |
| 96 | 274.64 | 4672.50 | 195 | 125 | 97 |
| **128** | **284.02** | **4832.08** | **193** | **137** | **100** ← cap |
| 192 | 271.54 | 4619.77 | 194 | 137 | **100** ← same cap |

**Long-context engine self-caps at ~100 in-flight** — chunked-prefill
scheduler's effective KV ceiling. KV is 244K tokens; 244K ÷ 24K (avg
fully-decoded ctx) ≈ 10 fully-decoded slots, but chunked prefill admits
many partial-prefill sequences. Past c=128, TTFT plateaus and
throughput drops 4-5%.

## Phase 3 — TP=1 long-context PUSH (per-H100)

Workload: random 16384 in / 1024 out, num_prompts=100.
Config: TP=1, max_model_len=262144, util=0.94, max_num_seqs=256,
max_num_batched_tokens=16384.

| bench c | tok/s out | tok/s total | TPOT (ms) | TTFT (s) | Peak in-flight |
|---|---|---|---|---|---|
| 64 (per H100) | 143.46 | 2440.66 | 199 | 200 | 67 |
| 128 (per H100) | 142.34 | 2421.64 | 201 | 319 | 100 |

**TP=1 per-H100 KV is only 102K tokens** (vs TP=2's 244K aggregate).
At 17K per request, max parallel = 6. Two TP=1 instances aggregate to
~286 tok/s, basically tied with TP=2's 284 — but TTFT is **2-3× worse**
on TP=1 (200-319s vs 58-137s).

## Cross-config aggregate comparison

| Workload | 2× TP=1 LIGHT (one per H100) | 1× TP=2 LIGHT | 2× TP=1 PUSH | 1× TP=2 PUSH |
|---|---|---|---|---|
| Short ctx (4K/512) tok/s out | 816 (2×408) | 745 | (likely worse — PUSH costs 2%) | 729 |
| Long ctx (16K/1K) tok/s out | (TP=1 LIGHT can't fit, ml=32K) | (TP=1 LIGHT can't fit) | ~286 | 284 |
| Long ctx max doc | 32K | 32K | ~100K (KV-bound per card) | **256K** |

## Cross-config TPOT and TTFT comparison

Long-context (16K/1K) at peak concurrency:

| Config | TPOT mean (ms) | TTFT mean (s) | Peak in-flight |
|---|---|---|---|
| TP=1 PUSH per H100 | 199-201 | 200-319 | 67-100 |
| TP=2 PUSH | 154-193 | 58-137 | 67-100 |

**TP=2 wins on TTFT by 2-3×** — for document summarization where
users wait for first token, this is a UX-defining difference. TPOT
is similar (~5-15% TP=2 advantage at high concurrency).

## Stock vs preflight parser comparison (separate run)

Same hardware, same model, same chat_template, same EAGLE3.
Workload: MT-Bench (philschmid/mt-bench), c=20, N=80, --num-warmups 5.

| Run | Config | Stock tok/s | Stock TPOT mean / P99 | Preflight tok/s | Preflight TPOT mean / P99 |
|---|---|---|---|---|---|
| R1 | Parallel, no warmup | 1254.19 | 13.55 / 21.28 | 1263.51 | 13.52 / 18.87 |
| R2 | Parallel, 5 warmup | 1378.11 | 12.63 / 21.02 | 1382.12 | 12.61 / 19.43 |
| R3 | Serial GPU 0 only | 1382.47 | 12.83 / 23.67 | 1341.23 | 13.06 / 21.60 |

**Mean throughput identical within noise** (≤1%). **P99 TPOT consistently
~8-11% lower for preflight** in 3 of 3 runs (Rust avoids GIL pauses).
Median TPOT identical. On real chat data, both stock and preflight
hit acceptance ~50%, AL ~2.5.

Memos: `comparison-memo.2026-04-30.md` for the full stock-vs-preflight
write-up.

## Notes on bench methodology

1. **`--num-warmups 5` matters** — adds ~9% throughput (1254 → 1378 in R1
   vs R2 above) and ~25% lower TTFT by hitting cudagraphs.
2. **Acceptance on random tokens is meaningless** — EAGLE3 drafter has
   nothing to predict. Use real-text bench for realistic acceptance
   numbers (~50-72% on MT-Bench, ~80-92% claimed by paper on aligned chat).
3. **GPU-side variance is real** — same H100 SXM5 cards in the same
   chassis differ by ~3% throughput silicon/thermal variance. Always
   pin to the same GPU when comparing parser flavors.
4. **vllm bench has built-in MT-Bench/sharegpt support** via
   `--dataset-name hf --dataset-path philschmid/mt-bench --hf-split train`
   but requires `pip install datasets` in the container (not in the
   stock image). Run `uv pip install --system --quiet datasets` once
   per container before benching real text.
