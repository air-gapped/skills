# KV-cache quantization

Separate CLI axis from weight quant. `--kv-cache-dtype` + optional pre-calibrated
scales in the model checkpoint. Source of truth:
[`vllm/config/cache.py:18-34`](https://github.com/vllm-project/vllm/blob/main/vllm/config/cache.py) (dtype enum) and
[`vllm/model_executor/layers/quantization/kv_cache.py`](https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/layers/quantization/kv_cache.py) (loading + scale handling).

## Dtype options

| Dtype | Semantics | Hardware | Scales |
|---|---|---|---|
| `auto` | Match weight dtype | All | — |
| `float16` / `bfloat16` | No quant | All | — |
| `fp8` | Alias for `fp8_e4m3` | SM89+ | Loaded from checkpoint (`k_scale`, `v_scale`) |
| `fp8_e4m3` | Standard E4M3 | SM89+ | Loaded |
| `fp8_e5m2` | IEEE 754 E5M2 (ROCm-oriented) | SM89+ | Loaded |
| `fp8_inc` | Intel path | HPU | — |
| `fp8_ds_mla` | DeepSeek MLA-specific | SM89+ | — |
| `int8_per_token_head` | Dynamic INT8 per (token, head) | FlashInfer / XPU | Computed in-kernel — no checkpoint scales needed |
| `fp8_per_token_head` | Dynamic FP8 per (token, head) | FlashInfer / TRTLLM | Computed in-kernel |
| `turboquant_k8v4` | FP8 K + 4-bit V | SM89+ | Hadamard rotation, no checkpoint scales |
| `turboquant_4bit_nc` | 4-bit K + 4-bit V + NC | SM89+ | Hadamard |
| `turboquant_k3v4_nc` | 3-bit K + 4-bit V + NC | SM89+ | Hadamard |
| `turboquant_3bit_nc` | 3-bit K + 3-bit V + NC | SM89+ | Hadamard |
| `nvfp4` | Roadmap | SM100 | Issue [#32220](https://github.com/vllm-project/vllm/issues/32220) |

## Base method

`BaseKVCacheMethod` (`kv_cache.py:18`) — parameters: `k_scale`, `v_scale`, `q_scale`, `prob_scale`. Loaded from checkpoint or computed.

Extensions:
- `Fp8KVCacheMethod` (`fp8.py:203`) — standard FP8 path.
- `ModelOptFp8KVCacheMethod` (`modelopt.py:120`) — ModelOpt calibrated scales.

Validation: `cache.py:236-254` — ensures backend supports the chosen dtype.

## Calibrating scales (pre-compute)

llm-compressor recipe (tensor-level, stable for MLA):

```python
recipe = QuantizationModifier(
    targets="Linear",
    scheme="FP8_DYNAMIC",
    ignore=["lm_head"],
    kv_cache_scheme={
        "num_bits": 8, "type": "float", "strategy": "tensor",
        "dynamic": False, "symmetric": True,
    },
)
```

512 samples, seq 2048, ~35 min H100 for 70B.

Serve: `vllm serve <model> --kv-cache-dtype fp8`.

## Dynamic (per-token-head) path

New in v0.17 ([PR #34281](https://github.com/vllm-project/vllm/pull/34281)). No checkpoint scales; attention kernel computes per-(token, head) scale at write time.

Rules (`kv_cache.py:57-69`):
- `k_scale` / `v_scale` forced to 1.0.
- Requires FlashInfer or TRTLLM attention backend.
- Not all models supported — check `kv_cache_uses_per_token_head_scales()`.

Pro: no calibration step, no scale drift across domains.
Con: narrower backend support.

## `--calculate-kv-scales` (DEPRECATED v0.19)

Removed by [PR #37201](https://github.com/vllm-project/vllm/pull/37201). Use pre-calibrated scales or per-token-head dynamic path.

## FNUZ adjustment (AMD)

`kv_cache.py:83-84`:

```python
if current_platform.is_fp8_fnuz():
    scale *= 2
```

MI300/MI355X CDNA3/4 required. Handled automatically when platform is detected.

## Attention backend × KV dtype matrix

| Backend | fp8_e4m3 | fp8_e5m2 | int8_per_token_head | nvfp4 | turboquant |
|---|---|---|---|---|---|
| FlashAttention v2 | ✓ | ✓ | ✗ | ✗ | ✗ |
| FlashInfer | ✓ | ✓ | ✓ | ✓ | ✗ |
| FlashInfer Sparse MLA (v0.18+) | ✓ | — | — | — | — |
| TRTLLM (Hopper+) | ✓ | ✓ | ✗ | ✓ | ✗ |
| Triton MLA (v0.18+) | ✓ | — | — | — | — |
| XPU (Intel) | ✓ (incfp8) | ✗ | ✓ | ✗ | ✗ |
| Vanilla (CPU) | ✗ | ✗ | ✗ | ✗ | ✓ |

## Known landmines

1. **FP8 KV on MLA multi-turn → garbage** ([#38652](https://github.com/vllm-project/vllm/issues/38652)) — unresolved. DeepSeek V3/V3.2, GLM-4.5/4.6/4.7, Kimi K2 affected. Avoid.
2. **FP8 KV compile failure SM90 FlashInfer** ([#31843](https://github.com/vllm-project/vllm/issues/31843)) — upgrade FlashInfer to 0.6.6+ (bundled in v0.18+).
3. **`_init_kv_cache_quant` overly broad** ([#39137](https://github.com/vllm-project/vllm/issues/39137)) — fp8_e5m2 gate fires on any quantized checkpoint, blocks legit INT4/NVFP4 loads. Patch in discussion.
4. **Qwen3-MoE k_scale/v_scale load** — fixed in v0.17 ([PR #35656](https://github.com/vllm-project/vllm/pull/35656)).
5. **MLA KV scale inconsistency FP8 → gibberish** — fixed v0.19 ([PR #37054](https://github.com/vllm-project/vllm/pull/37054)).
6. **Skip SWA layers with FP8 KV** — added v0.19 ([PR #33695](https://github.com/vllm-project/vllm/pull/33695)).
7. **FlashInfer crash with `kv_cache_dtype_skip_layers`** — fixed [PR #39002](https://github.com/vllm-project/vllm/pull/39002).
8. **TurboQuant crash on A100 with BF16 + FP8 KV** ([#39992](https://github.com/vllm-project/vllm/issues/39992)) — A100 not a production TurboQuant target.
9. **Per-head FP8 KV experimental for checkpointed scales** — use per-token-head dynamic path instead on MLA.
10. **Qwen3.5 FP8 on B200 degraded-accuracy KV** v0.18 ([#37618](https://github.com/vllm-project/vllm/issues/37618)) — fixed v0.19 ([PR #38083](https://github.com/vllm-project/vllm/pull/38083)).

## Roadmap items (feature requests)

- `nvfp4` KV dtype — [#32220](https://github.com/vllm-project/vllm/issues/32220).
- INT8 KV — [#33480](https://github.com/vllm-project/vllm/issues/33480).
- DCP with FP8 KV — [#32010](https://github.com/vllm-project/vllm/issues/32010).
- Per-head/per-channel FP8 KV generalized — [#32227](https://github.com/vllm-project/vllm/issues/32227).
- Phase-aware KV quant for reasoning — [#39416](https://github.com/vllm-project/vllm/issues/39416) (58 % distortion reduction claim).

## External

- [vLLM docs — Quantized KV Cache](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/)
- [LLM Compressor docs — FP8 W/A/KV](https://docs.vllm.ai/projects/llm-compressor/en/latest/examples/quantization_kv_cache/)
- [NVIDIA — Optimizing Inference for Long Context with NVFP4 KV Cache](https://developer.nvidia.com/blog/optimizing-inference-for-long-context-and-large-batch-sizes-with-nvfp4-kv-cache/)
- [SqueezeBits — vLLM vs TensorRT-LLM KV Quantization](https://blog.squeezebits.com/vllm-vs-tensorrtllm-8-kv-cache-quantization-35079)
