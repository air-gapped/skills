# MTP (Multi-Token Prediction) specifics

Load when configuring MTP on a model that ships native heads (DeepSeek V3/R1,
GLM-4.5/4.6, Qwen3-Next, Qwen3.5, Nemotron-H, MiMo, ERNIE 4.5, EXAONE-MoE,
LongCat-Flash, Pangu-Ultra-MoE, Step-3.5, ...) or when debugging unexpectedly
low acceptance on an MTP-capable target.

## What MTP is and is not

MTP heads are **trained jointly with the base model during pretraining** as
part of the DeepSeek-V3 recipe (arXiv 2412.19437 §2.2). They ship inside the
target checkpoint. No second model to load, no separate VRAM footprint for the
drafter.

This is the structural difference vs EAGLE. EAGLE is a *post-hoc distilled*
drafter trained against a frozen target; MTP is *native* to the target. Both
route through the EAGLE path in vLLM (`SpeculativeConfig.use_eagle()` is True
for `eagle`/`eagle3`/`mtp`/`dflash`/`dspark`), but their failure modes differ:
EAGLE-3 fails on domain mismatch (chat-tuned head on code traffic); MTP
inherits the target's domain coverage.

## Models in vLLM main today

Grep the `MTPModelTypes = Literal[...]` block in `vllm/config/speculative.py`
(line numbers drift). **27 entries at v0.32.0** (26 model types + `mtp`):

| Family | Model types | vLLM model file |
|---|---|---|
| DeepSeek V3 / R1 / V3.2 / V4 | `deepseek_mtp` | `deepseek_mtp.py`, `models/deepseek_v32/*/mtp.py`, `models/deepseek_v4/*/mtp.py` |
| GLM-4.5 / 4.6 MoE, GLM-OCR | `glm4_moe_mtp`, `glm4_moe_lite_mtp`, `glm_ocr_mtp` | `glm4_moe_mtp.py` + variants |
| Qwen3-Next-80B-A3B | `qwen3_next_mtp` | `qwen3_next_mtp.py` |
| Qwen3.5 / Qwen3.5-MoE | `qwen3_5_mtp` | `qwen3_5_mtp.py` |
| MiMo-7B, MiMo v2 | `mimo_mtp`, `mimo_v2_mtp` | `mimo_mtp.py`, `mimo_v2_mtp.py` |
| ERNIE 4.5 | `ernie_mtp` | `ernie_mtp.py` |
| Nemotron-H | `nemotron_h_mtp` | `nemotron_h_mtp.py` |
| EXAONE-MoE, EXAONE 4.5 | `exaone_moe_mtp`, `exaone4_5_mtp` | `exaone_*_mtp.py` |
| LongCat-Flash | `longcat_flash_mtp` | (single layer only) |
| Pangu-Ultra-MoE | `pangu_ultra_moe_mtp` | `openpangu_mtp.py` |
| Step-3.5 | `step3p5_mtp` | `step3p5_mtp.py` |
| Gemma 4 | `gemma4_mtp` | `gemma4_mtp.py` |
| Hunyuan v3 | `hy_v3_mtp` | `hy_v3_mtp.py` |
| Bailing hybrid | `bailing_hybrid_mtp` | `bailing_moe_mtp.py` |
| MiniMax-M3 | `minimax_m3_mtp` | `models/minimax_m3/*/mtp.py` |
| **Kimi K3** (new, v0.26–v0.27) | `kimi_k3_mtp` | `models/kimi_k3/*/mtp.py` |
| **Inkling** (new, v0.26–v0.27) | `inkling_mtp` | `models/inkling/*/mtp.py` |
| dots3-note | `dots3_note_mtp` | arch `Dots3NoteMTPModel` |
| Qwen4-Exp | `qwen4_exp_mtp` | remapped from `qwen4_exp` / `qwen4_exp_text` |
| Bailing hybrid v3 | `bailing_hybrid_v3_mtp` | `bailing_moe_v3_mtp.py` (`BailingMoeV3MTPModel`) |
| Hunyuan v4 | `hy_v4_mtp` | arch `HYV4MTPModel` |
| GLM-5 Next | `glm5_next_mtp` | arch `Glm5NextMTPModel` |

**All of these are deprecated aliases.** Users should set `method: "mtp"`;
vLLM detects the target type and dispatches (PR #25232, v0.11.1).

## `num_speculative_tokens` rules

The target's MTP head has a fixed width: `n_predict` (or
`num_nextn_predict_layers` depending on family — vLLM reads both). DeepSeek-V3
ships `n_predict=1` by default; the V3 paper describes 4 heads but the public
release uses 1. Qwen3-Next ships `n_predict=1`. Nemotron-H varies.

Rule from `config/speculative.py:1489-1501` (v0.32.0): unset defaults to
`n_predict`; a value above `n_predict` must be divisible by it, else
`ValueError: num_speculative_tokens:N must be divisible by n_predict=M`. Above
`n_predict`, vLLM re-runs the MTP layer sequentially. Any value > 1 also logs
(L1377-1385, skipped for `step3p5_mtp` / `inkling_mtp`):

> Enabling num_speculative_tokens > 1 will run multiple times of forward on
> same MTP layer,which may result in lower acceptance rate

Practical implications:

- DeepSeek-V3, `n_predict=1`:
  - `num_speculative_tokens=1` → single native MTP call. Fast, best AL per
    token.
  - `num_speculative_tokens=5` → 5 sequential MTP calls. More tokens per
    forward but acceptance *per position* declines — the second, third, ...
    calls are not what the head was trained to predict.
  - Start at 1. Only raise if AL can be verified to improve.
- Qwen3-Next, `n_predict=1`: same logic.
- Models training multi-head natively (future drops from the DeepSeek recipe):
  set `num_speculative_tokens = n_predict` for best behaviour.

## Known rough edges (April 2026)

**DeepSeek-V3.2 MTP + CUDA graphs** — the old `deepseek_v32_mtp` →
`enforce_eager = True` FIXME is gone (absent at v0.30.0 and v0.32.0). Remove
any `--enforce-eager` a runbook added for it.

**Active MTP bug cluster through v0.19** — release-notes scan shows these all
landed in v0.11.x through v0.19.x:
- #25982 DeepSeek-V3.2 eager fallback (prior fix)
- #25987 Skip MoE NVFP4 for MTP
- #25904 MTP + DeepEP low-latency
- #26361 FlashInfer MTP crash fix
- #27227 FP8 KV scales on MTP (v0.17)
- #25049 DCP + query-length-1 MTP with FA3
- #25109 Piecewise CUDA graphs for EAGLE/MTP head
- #25119 Mamba + MTP KV-cache manager simplification
- #25311 EP/DP + EPLB with MTP
- #28315 IMA-fix for MTP=2 + full-CG
- #34552 Sparse MLA + MTP `num_speculative_tokens > 1`
- #34457 Sparse MLA + MTP + full CUDA graphs
- #35447 Nemotron-H MTP + chunked prefill
- #37803 NemotronH Puzzle + MTP

MTP is still stabilising. Pin to ≥v0.17.0 for Sparse MLA combos, ≥v0.18.0 for
chunked-prefill interaction, ≥v0.19.0 for async + hybrid models + FP32 draft
logits.

## Production signals

SGLang's July 2025 MTP post (<https://www.lmsys.org/blog/2025-07-17-mtp/>)
reports 1.5–2.5× real-workload speedups for DeepSeek MTP. Red Hat's Wide-EP
blog discusses MTP as a key lever for DeepSeek-style MoE scaling. The
DeepSeek-V3 tech report §4.5.2 reports 60–85% token-2 acceptance on their
evaluation mix.

No vLLM-team published benchmark post exists specifically for MTP as of April
2026. Measure yourself with `examples/features/speculative_decoding/spec_decode_offline.py`.

## Canonical invocation

```bash
# DeepSeek V3
vllm serve deepseek-ai/DeepSeek-V3 \
  --tensor-parallel-size 8 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}'

# GLM 4.6 MoE
vllm serve zai-org/GLM-4.6 \
  --tensor-parallel-size 8 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}'

# Qwen3-Next 80B
vllm serve Qwen/Qwen3-Next-80B-A3B-Instruct \
  --tensor-parallel-size 4 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}'
```

Note: `model` field is not set — target model is the drafter.

## What about Kimi K2?

Kimi K2 / K2.5 have no MTP type (no `kimi_k2_mtp` in `MTPModelTypes` at
v0.32.0); **Kimi K3** does (`kimi_k3_mtp`). For K2/K2.5 use EAGLE-3 if a
checkpoint exists and the model class implements `SupportsEagle3`. Verify
before assuming either capability.
