# EAGLE-3 and P-EAGLE

Load when picking EAGLE-3 for a production deployment, tuning its k
(num_speculative_tokens), or deciding between EAGLE-3 and P-EAGLE.

## Why EAGLE-3 is the 2026 default model-based method

EAGLE-3 adds auxiliary hidden-state extraction from intermediate layers of the
target. Compared to EAGLE-1 (trained on final hidden state only), the
additional supervision raises AL by ~30% on aligned workloads. Paper:
arXiv 2503.01840.

**The "+32% vs EAGLE-1" number** everyone quotes comes from vLLM PR #25916
(v0.11.1, 2025-11): a **benchmarking bug fix**, not an algorithm change. The
preamble (shared system-prompt tokens) was being double-counted in the harness,
making EAGLE-3 appear only 5% faster. After dedup:
- EAGLE-1 TPOT: 4.32 ms
- EAGLE-3 (broken harness): 4.09 ms (5.6% faster)
- EAGLE-3 (post-fix): 3.25 ms (32.9% faster)
Llama-3.1-8B-Instruct, BS=4, 80 MT-Bench prompts, H100.

**Operator takeaway**: any EAGLE-3 vs EAGLE-1 comparison on vLLM < v0.11.1 is
wrong. Upgrade before benchmarking.

## Target-model allow-list

Hard-coded in `vllm/config/speculative.py:818-833`. Only these target
`model_type`s accept EAGLE-3 (and DFlash):

```
llama, qwen, minicpm, gpt_oss, hunyuan_vl, hunyuan_v1_dense, afmoe,
nemotron_h, deepseek_v2, deepseek_v3, kimi_k2, kimi_k25, minimax_m2, gemma4
```

If the target isn't on this list, EAGLE-3 fails validation at engine
start. Use `draft_model` (any target), `ngram_gpu` (any), or stick with
`eagle` (v1/v2, no aux hidden states, laxer target requirements).

## Checkpoint sources

Stock checkpoints are chat-tuned. Domain mismatch matters.

- `yuhuili/EAGLE3-LLaMA3.1-Instruct-8B` — canonical reference, general chat
- `yuhuili/EAGLE-LLaMA3.1-Instruct-8B` — EAGLE-1 equivalent
- `RedHatAI/*-speculator.eagle3` — vetted by Red Hat for production, same
  architecture family
- Hugging Face `yuhuili/models` and `RedHatAI/speculator-models` collections
- Per-target classes in `vllm/model_executor/models/`:
  `llama_eagle3.py`, `deepseek_eagle3.py`, and auto-wrapped variants for
  other allowed families

For **training your own** EAGLE-3 head — recipe families (Magpie+UltraChat,
Open-PerfectBlend, ShareGPT/UC/PB mix, UltraChat-only, Nemotron, EagleChat),
sample sizes, and target-family guidance — see
`references/training-data-recipes.md`.

## Auto-detection mechanics

vLLM sets `method="eagle3"` automatically if:
1. `"eagle3"` substring appears in the `model` field of `--speculative-config`
   (`config/speculative.py:519`), OR
2. The HF config has `eagle_aux_hidden_state_layer_ids` set

**Gotcha**: mirroring a checkpoint locally and renaming the directory to
drop the `eagle3` substring breaks auto-detection. Either keep the upstream
name or set `method: "eagle3"` explicitly.

Aux-layer IDs live in `eagle_aux_hidden_state_layer_ids` (tuple of ints) in
the drafter's HF config. vLLM reads them via
`v1/worker/gpu/spec_decode/eagle/eagle3_utils.py:35-46`. Cache hashing
(`config/speculative.py:221-229`) includes these IDs.

## Tree vs chain

The EAGLE proposer supports tree speculation via `speculative_token_tree`
(string literal describing branch structure). Chain is the default.

Red Hat's "Fly Eagle(3) Fly" dev blog: "tree decoding underperforms greedy
decoding in most deployment scenarios." The extra verification pass over
multiple tree branches costs more than it saves when acceptance is already
high. Stick with chain unless tree wins have been measured on real traffic.

## num_speculative_tokens tuning

EAGLE-3 vanilla peaks at k=3 on MT-Bench. Above k=3 the AL curve flattens
because acceptance at positions 3+ drops below the verification overhead of
those extra tokens. This is a *vanilla* EAGLE-3 observation — see P-EAGLE
below for the updated recipe.

Start at k=3. Watch `vllm:spec_decode_num_accepted_tokens_per_pos_total` and
raise k only if positions 2 and 3 both show >0.5 acceptance. Lower k if
position 2 is <0.4.

## P-EAGLE (Parallel EAGLE)

vLLM PR #32887 (v0.16.0, 2026-02-05) landed "unified parallel drafting",
which enables P-EAGLE (as well as PARD for draft models and the DFlash
architecture). Source paper + blog: <https://vllm.ai/blog/p-eagle>.

Core idea: predict all k speculative tokens in a single forward pass through
the EAGLE head, rather than sequentially k times. Changes the structure of
the drafter's self-attention but uses the same underlying head weights (so a
plain EAGLE-3 checkpoint can be used in parallel mode with a new recipe).

Amazon's published numbers on 1× B200, GPT-OSS-20B BF16 target, FP8 KV:

- BS=1 (MT-Bench): 1.55× throughput over vanilla EAGLE-3
- BS=1 (SPEED-Bench code): 1.69× over vanilla EAGLE-3
- BS=1 AL K=7: HumanEval 3.94 (P-EAGLE) vs 3.03 (EAGLE-3), +30%
- BS=8 GPT-OSS-120B: P-EAGLE K=3 → 2388 TPS vs EAGLE-3 K=3 → 2234 TPS (+7%)

**K peaks at 7 for P-EAGLE** (vs 3 for vanilla EAGLE-3). The parallel forward
amortises the drafter cost over more tokens so a larger k remains net
positive.

## Canonical invocation

```bash
# EAGLE-3, chain, k=3 — reliable default
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --speculative-config '{"method":"eagle3","model":"yuhuili/EAGLE3-LLaMA3.1-Instruct-8B","num_speculative_tokens":3}'

# P-EAGLE, k=7, on a supported checkpoint
vllm serve openai/gpt-oss-20b \
  --speculative-config '{"method":"eagle3","model":"amazon/GPT-OSS-20B-P-EAGLE","num_speculative_tokens":7,"parallel_drafting":true}'
```

## When EAGLE-3 fails to pay off

Red Hat's EAGLE-3 post is explicit:

> at higher throughputs or batch sizes, we are compute-bound, and speculative
> decoding can provide worse performance.

Concrete causes:

1. **Domain mismatch** — chat-tuned EAGLE-3 on SQL/code/agent traffic, AL
   drops from ~3 to ~2. Solution: domain-adapt the head (continual
   pretraining) or pick a workload-specific checkpoint.
2. **BS >= 32** — verification batch contends with drafter batch, target
   becomes compute-bound, spec-dec loses. Solution: gate spec-dec to the
   low-concurrency tier, or use `disable_by_batch_size`.
3. **Context > 2048** on older stock checkpoints — they were trained at short
   context and extrapolate badly. Check the checkpoint's released sequence
   length before deploying on long context.
4. **Tokenizer mismatch with target** — AL collapses to the rate of shared
   tokens. EAGLE-3 is trained against a specific tokenizer; mixing
   fine-tuned-tokenizer targets with original-tokenizer drafters breaks AL
   quietly.

## Composability

- **LoRA**: supported (v0.11.1+, PR #28318 adds CUDA-graph specialisation)
- **Chunked prefill**: supported (v0.11.1 fix #26263, specifically "padded
  eagle + chunked prefill")
- **Structured outputs**: supported v0.16.0+ (PR #33374)
- **Disaggregated serving**: v0.17.0+ (PR #34529)
- **Pipeline parallel**: v0.17.0+ on MRV2 only (PR #33960, #35029, #35040)
- **Multimodal**: Qwen2.5-VL support in v0.11.1 (#22872); EAGLE-3 multimodal
  embedding support v0.19.0 (#36097)
- **FP8 KV**: supported, specific FlashInfer sparse MLA fix in v0.19
