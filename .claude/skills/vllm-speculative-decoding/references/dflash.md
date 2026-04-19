# DFlash — block-diffusion parallel drafter

Load when deploying DFlash on Qwen3 / gpt-oss / DeepSeek / Llama / Kimi K2 /
Minimax M2 targets on B200-class hardware, or when the skill has flagged
DFlash as a candidate method.

## Name and provenance

Spelled **DFlash** — capital D, capital F, no hyphen. Stands for "Block
Diffusion for Flash Speculative Decoding." NOT a FlashAttention variant; the
overlapping "Flash" name is coincidental.

- Reference impl: <https://github.com/z-lab/dflash> (authors: z-lab)
- vLLM integration: PR #36847 (2026-03-30, v0.19), +
  speculators-format path in #38300 (2026-04-15, v0.19)

## What it does

Draft tokens are generated in one parallel forward pass via a block-diffusion
adapter. The KV cache is pre-populated with target hidden states; query tokens
(the last sampled target token plus N mask placeholders) cross-attend
non-causally over that context in a single forward.

Conceptually closer to P-EAGLE than to EAGLE-3 — parallel, not sequential. The
head is trained on a block-diffusion objective (DDPM-like), which gives it
stronger parallel-prediction behaviour than a standard EAGLE head.

vLLM plumbing: `vllm/v1/spec_decode/dflash.py:20-250+`. Model definition:
`vllm/model_executor/models/qwen3_dflash.py`.

## Constraints to know before turning it on

1. **`--attention-backend flash_attn` is required.** The non-causal
   cross-attention path is not supported by Triton or FlashInfer-TRTLLM.
   DFlash won't fit if a different backend is pinned for the target.
2. **`parallel_drafting: true` is force-enabled** (`config/speculative.py:576`)
   — can't turn it off. The architecture demands it.
3. **Target-model allow-list**: same as EAGLE-3 (llama, qwen, minicpm,
   gpt_oss, hunyuan_vl, hunyuan_v1_dense, afmoe, nemotron_h, deepseek_v2,
   deepseek_v3, kimi_k2, kimi_k25, minimax_m2, gemma4). See
   `config/speculative.py:818-833`.
4. **Multimodal is untested.** `_raise_if_multimodal` override at line 71
   raises if the target emits MM inputs.
5. Checkpoint must be a DFlash-trained adapter — not a standard EAGLE-3
   checkpoint. Not many of these exist yet; Qwen3-8B is the reference target.

## Published numbers

PR #36847 benchmarks, Qwen3-8B target, 1× B200, `num_speculative_tokens: 15`:

| Workload | BS=1 | BS=8 | BS=32 |
|---|---|---|---|
| GSM8k | **3.51×** | 2.71× | 1.60× |
| HumanEval | **4.63×** | 3.43× | 2.05× |
| MT-Bench | 2.98× | 2.22× | 1.30× |

PR #38300 on magpie dataset, BS=1 with speculators-format checkpoint: mean
AL = 1.77. Solid but not transformative; the BS=1 sprint speedups are where
DFlash shines.

The z-lab paper claims up to 2.5× over EAGLE-3. **Unverified** against vLLM —
no Red Hat / Amazon / Snowflake reproduction in release notes as of April
2026. Benchmark against EAGLE-3 on real traffic before adopting.

## Canonical invocation

```bash
vllm serve Qwen/Qwen3-8B \
  --attention-backend flash_attn \
  --speculative-config '{"method":"dflash","model":"<dflash-checkpoint-path>","num_speculative_tokens":15,"parallel_drafting":true}'
```

`num_speculative_tokens: 15` follows the paper. Drop it to 7-11 on higher
batch sizes; watch the per-position acceptance histogram.

## When DFlash is the wrong choice

- Target not in allow-list → method won't load.
- `--attention-backend` pinned to Triton (common on some Hopper deployments)
  → the cross-attention path is unsupported.
- BS consistently ≥ 32 in production → all spec-dec methods degrade; DFlash
  falls off faster than vanilla EAGLE-3 in the published data.
- Multimodal workload → untested, expect trouble.
- No DFlash adapter exists for the target family → stick with EAGLE-3.

## Operator sanity check

Before adopting, measure:

1. AL on real production traffic (`examples/offline_inference/spec_decode.py`)
2. BS=1, BS=8, BS=32 wall-clock wins vs EAGLE-3 at same k
3. TPOT P99 — DFlash is optimised for BS=1 latency, not high-BS tail

If the BS=8 win is <15% or the P99 TPOT regresses, don't adopt — the extra
deployment risk (new method, small production footprint, one test model) isn't
worth it versus the mature EAGLE-3 path.
