---
name: vllm-gemma-4-31b
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Operating-point reference for serving Gemma 4 31B on vLLM — TP sizing, max_model_len, max_num_seqs, gpu_memory_utilization, kv_cache_dtype, EAGLE3 spec-dec, chat_template choice.
when_to_use: |-
  When the user mentions Gemma 4 31B in the context of vLLM deployment, tuning, or performance.
---

# Gemma 4 31B on vLLM — operating-point reference

For platform engineers deploying `google/gemma-4-31B-it` (BF16, FP8) or its
community quants (e.g. `cyankiwi/gemma-4-31B-it-AWQ-4bit`,
`RedHatAI/*-Gemma-4-31B-*`) on vLLM 0.20+. Pulls together measurements
from a Verda 2× H100 SXM5 80GB audit on 2026-04-30 and the upstream
constraints that shape the answer.

## Three load-bearing facts

1. **Gemma 4 has heterogeneous head_dim (256 dense / 512 attention)**, which
   forces vLLM to use `TRITON_ATTN` backend, not FLASH_ATTN. This is
   automatic — vLLM logs `Gemma4 model has heterogeneous head dimensions
   (head_dim=256, global_head_dim=512). Forcing TRITON_ATTN backend to
   prevent mixed-backend numerical divergence`. Don't try to override
   with `--attention-backend FLASH_ATTN` — vLLM rejects it (`kv_cache_dtype
   not supported`, `partial multimodal token full attention not supported`).
2. **Throughput plateaus at batch=64 on H100, batch=128 on H200.** This is
   *not* a hardcoded vLLM cap — it's HBM-bandwidth-bound saturation. H100
   SXM5 has ~3.35 TB/s HBM3, H200 has ~4.8 TB/s HBM3e (~43% more). The
   bandwidth ratio approximately matches the batch ratio. See
   `references/hbm-saturation.md` for the source-code investigation
   (vllm/engine/arg_utils.py:2207-2288 is the only hardware-aware default
   in the engine; H100 and H200 take the *same* code path). **Don't set
   `max_num_seqs` above the bandwidth knee** — it just inflates TPOT and
   TTFT without moving throughput.
3. **The stock chat_template shipped with cyankiwi/RedHatAI quants is
   stale** until they re-pull from `google/gemma-4-31B-it`. The 2026-04-28
   Google upstream patch removed the `<|channel>thought\n<channel|>`
   injection in non-thinking mode, fixed the `format_parameters` macro
   filter, and added multimodal-system-message support. Always pull
   `huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja`
   directly and pass via `--chat-template`. SHA256 of the 2026-04-30
   pull: `94899c0f917d93f6fe81c95744d1e8ddab2d21d39228d2e4aec1fb2a25bff413`.

## Decision guide — which TP for which workload

| Prod traffic shape | Deploy | Why |
|---|---|---|
| Short chat (≤4K input), many concurrent users | **2× TP=1 LIGHT**, one per H100 | 408 tok/s/H100 × 2 = 816 tok/s aggregate vs TP=2's 745 (per-H100 TP=2 has ~9% TP communication overhead) |
| Long context (≥16K input), document summarization, RAG | **1× TP=2 PUSH** | Same long-ctx aggregate throughput (~284 tok/s) but **2-3× faster TTFT** (58-137s vs 200-319s), single endpoint, can serve documents up to 256K. **TP=1 cannot serve docs >100K** at all (per-card KV is only ~102K) |
| Mixed (chat + occasional long doc) | **1× TP=2 PUSH** | Versatile; small short-ctx penalty (~10%) acceptable for long-doc capability |
| Per-H100 cost-efficiency only | **TP=1 LIGHT** | Best $/tok at short context |
| Latency-sensitive single-user | **TP=2** | Always lower TPOT (78–193 ms vs 141–201 ms) |

## Operating-point recipes — copy-paste ready

### LIGHT — short-mostly chat, max throughput per H100

Run **2 replicas** on a 2-H100 box, one pinned per GPU via
`--gpus device=N`. Two endpoints (port 8000 + 8001 for example).

```bash
vllm serve cyankiwi/gemma-4-31B-it-AWQ-4bit \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 64 \
  --max-num-batched-tokens 8192 \
  --kv-cache-dtype fp8 \
  --chat-template /path/to/google-31b-chat-template.jinja \
  --trust-request-chat-template \
  --enable-auto-tool-choice \
  --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --speculative-config '{"method":"eagle3","model":"RedHatAI/gemma-4-31B-it-speculator.eagle3","num_speculative_tokens":3}' \
  --no-scheduler-reserve-full-isl
```

Headline numbers per H100 (random 4K input / 512 output, EAGLE3 acceptance ~43%
on random — would be 50–80% on real chat):
- **408 tok/s output** (3688 tok/s total)
- **TPOT mean 141 ms** at concurrency 64-80
- KV cache size: ~85K tokens at fp8

### PUSH — long-context RAG / document summarization

Run **1 replica** spanning both H100s. Single endpoint. Accepts any
prompt up to the architectural max (262144 tokens).

```bash
vllm serve cyankiwi/gemma-4-31B-it-AWQ-4bit \
  --tensor-parallel-size 2 \
  --max-model-len 262144 \
  --gpu-memory-utilization 0.94 \
  --max-num-seqs 256 \
  --max-num-batched-tokens 16384 \
  --kv-cache-dtype fp8 \
  --chat-template /path/to/google-31b-chat-template.jinja \
  --trust-request-chat-template \
  --enable-auto-tool-choice \
  --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --speculative-config '{"method":"eagle3","model":"RedHatAI/gemma-4-31B-it-speculator.eagle3","num_speculative_tokens":3}' \
  --no-scheduler-reserve-full-isl
```

**Why these specific values:**

- `gpu-memory-utilization 0.94` — measured cliff. **0.95+ runtime-OOMs**
  during cudagraph capture for the 35 default capture sizes × max_num_seqs=256.
  0.94 leaves ~1.8 GB headroom per card.
- `max-model-len 262144` — Gemma 4 architectural max (`text_config.max_position_embeddings`).
  Engine reports `Maximum concurrency for 262,144 tokens per request: 6.11x`
  meaning ~6 simultaneous full-context requests fit. Real prod will see
  more concurrency since few prompts hit the full max.
- `max-num-seqs 256` — past the HBM-bandwidth knee (~128 on H100 effective
  for TP=2), but the chunked-prefill scheduler caps actual in-flight at
  ~100 anyway. Keep this high; it's headroom, not a binding constraint.

Headline numbers (TP=2 PUSH):
- Short ctx (4K/512): **745 tok/s output, ~78 ms TPOT** (vs LIGHT's 741 — basically tied)
- Long ctx (16K/1K): **284 tok/s output @ c=128, ~193 ms TPOT, ~137s TTFT**
- KV cache: 244K tokens at fp8 / 0.94 util
- Saturation point: c=128 (engine self-caps in-flight at ~100)

## Why gemma-4-31B-AWQ behaves differently than gemma-3-27B-fp8

An existing prod running gemma-3-27B-fp8 may favour TP=2 over TP=1 or
TP=4 on H100/H200 — that experience is correct for that model. Gemma 4
31B AWQ-4bit shows a different curve (TP=1 wins on short-ctx per-H100
efficiency). Likely reasons:

1. **AWQ-4bit weights are smaller than fp8** (4 bits vs 8 bits, ~16 GB vs
   ~27 GB). Less benefit from TP weight-splitting since weights already
   fit comfortably on one H100 with KV headroom.
2. **TRITON_ATTN backend has different TP scaling than FLASH_ATTN**.
   gemma-3 uses FLASH_ATTN (homogeneous head_dim); Gemma 4 forces
   TRITON_ATTN — different per-rank communication characteristics.
3. **EAGLE3 spec-dec compute scales asymmetrically with TP**. The drafter
   weights are also sharded across TP ranks; for a small drafter (4.5 GB
   BF16 split across 2 cards) the per-rank compute is small, but the
   draft-verify cycle adds extra all-reduces that hurt at TP=2.
4. **31B vs 27B**: 31B has more layers + hidden dim → larger weight
   bytes per token; HBM bandwidth saturation knee shifts with weight
   size.

## Pitfalls — things that have already burned a deploy once

### `--max-model-len 262144` will refuse to boot if KV doesn't fit

vLLM enforces `KV_cache_size ≥ max_model_len ÷ engine_concurrency_factor`
at startup. When the util/maxSeqs/spec-dec config leaves insufficient
KV, the engine errors with the **estimated maximum**. Take that number
minus 5% margin to avoid cliff-edge boot variance from CUDA fragmentation.
Worked example: on Verda 2× H100, vLLM said 65120 was the ceiling at
TP=1 + util=0.94 + EAGLE3; first boot at 65120 failed (KV=2.44 GiB needed
2.47), second boot succeeded by coincidence. Drop to ≤ 60000 for
reproducible boots.

### One restart = fail, not "let it retry"

Boot succeeding on retry is CUDA-fragmentation luck, not a fix. Treat
restart-1 as a config failure and drop the offending knob (max_model_len,
util, max_num_seqs). The cliff-edge boot at the previous pitfall is
exactly this scenario.

### `parallel_drafting:true` (P-EAGLE) needs a **prepared** checkpoint

`RedHatAI/gemma-4-31B-it-speculator.eagle3` is *vanilla* EAGLE3, no
P-EAGLE prep tokens. `vllm/v1/spec_decode/llm_base_proposer.py:341`
requires `pard_token` / `ptd_token_id` / `dflash_config.mask_token_id`
in the draft `config.json`. Don't pass `parallel_drafting:true` with
the vanilla checkpoint — engine init will fail.

### DFlash speculator unsupported on sm_89 (RTX 4060 Ti / Ada)

DFlash needs non-causal attention. Only `flash_attn` and
`flex_attention` declare `supports_non_causal=True` on CUDA. On Ada,
`flash_attn` is blocked by fp8 KV + multimodal; `flex_attention` is
PyTorch fallback (no Ada kernel). vLLM skill scopes DFlash to "B200
class". Use EAGLE3 instead.

### Spec-dec acceptance on random tokens is meaningless

EAGLE3 acceptance is ~22-44% on random (vs ~50-72% on MT-Bench, ~80-92%
claimed on aligned chat). When benchmarking, use a real-text dataset
(MT-Bench, ShareGPT, NuminaMath) for realistic acceptance numbers.
Random benchmarks give worst-case lower bound.

### gpu-memory-utilization=0.97 OOM on cudagraph capture

Reproducible failure on TP=2 H100 with `max-num-seqs 256
max-num-batched-tokens 16384`: cudagraph capture for the 35 default
sizes ([1,2,4,8,...,256]) needs ~336 MiB and OOMs at 0.97. Stay at 0.94.

### Multimodal at high util OOMs at runtime

util=0.94 on the 16 GB lab cards (RTX 4060 Ti) caused runtime CUDA OOM
on the first multimodal request — image batch all_gather needed 394 MiB,
only 337 MiB free. On 80 GB H100 with TP=2, util=0.94 is fine for text;
for multimodal traffic specifically, drop to 0.92 or 0.90.

## Stock vs preflight parser plugin

The 2026-04-30 audit measured stock vLLM 0.20.0 + the new Google
chat_template against the preflight Rust parser plugin head-to-head on
H100. Result:

- **Correctness**: stock + new chat_template now passes everything
  preflight passes (`xgrammar_schema_enforce`, `image_token_in_output`,
  all 6 parser-suite + 9 multimodal-battery lanes).
- **Throughput**: identical at noise floor (<1% delta).
- **TPOT mean**: identical.
- **TPOT P99**: preflight ~8-11% lower in 3 of 3 runs (Rust avoids
  Python GIL/GC pauses) — small but consistent.

For a fresh deploy with the new chat_template, stock parsers are fine.
Preflight's value narrows to P99 tail latency + insurance against
future stock regressions. Full memo:
`findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/verda-stock-vs-preflight/comparison-memo.2026-04-30.md`.

## What was NOT measured

The following questions need a follow-up bench:

1. **`num_speculative_tokens=2` vs 3 on real-text**. At higher real
   acceptance (50-80%) k=3 may pay off but at low acceptance k=2 might
   win. Untested on Gemma 4.
2. **No-spec-dec baseline**. Operator brief was EAGLE3-only; if real
   acceptance drops below ~30% on prod traffic, no-spec might be
   competitive on aggregate throughput at high concurrency.
3. **AWQ-Marlin kernel** vs vanilla AWQ. Marlin is faster mid-batch on
   H100; cyankiwi quant uses compressed-tensors format which dispatches
   to Marlin automatically when available, but worth confirming via the
   `[compressed_tensors_wNa16] Using MarlinLinearKernel` log line.
4. **TP=4 hypothetical**. Would need a 4-H100 SKU. The bandwidth-bound
   knee should shift again, but TP communication overhead grows
   non-linearly past TP=2.
5. **Real-text long-context**. The 16K/1K random benchmark is
   conservative; ShareGPT-long or NuminaMath would give more realistic
   acceptance + throughput.

## References

- `references/hbm-saturation.md` — vLLM source-code investigation, GH issues, the bandwidth-bound saturation explanation
- `references/bench-numbers.md` — full benchmark table from the 2026-04-30 Verda audit, all 12+ data points
- `references/sources.md` — dated index of upstream URLs (HF model + chat_template, vLLM source paths, GH issues / PRs) with `Last verified:` and `Pinned:` markers

## Reproduction artifacts

The benchmark logs + memos referenced in this skill live in the
`model-preflight` repo at:

```
findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/
├── verda-tp1-tp2-search/
│   ├── max-perf-tp1-vs-tp2-memo.2026-04-30.md
│   ├── tp1-stock-eagle3-max-perf.md
│   └── p{1,2,3}-*.log              # raw bench output
├── verda-stock-vs-preflight/
│   ├── comparison-memo.2026-04-30.md
│   └── parser-suite-{stock,preflight}.jsonl
└── eagle3-sweep/
    └── deploy-memo.2026-04-29.md
```
