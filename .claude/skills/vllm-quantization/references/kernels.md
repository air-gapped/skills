# Kernel × format × SM dispatch

Who actually runs the matmul. Each kernel dispatches from a different file; the
dispatch selection is the #1 reason for surprise regressions when switching
vLLM versions.

## Table of Contents

- [Kernel registry files](#kernel-registry-files)
- [Dispatch table (linear GEMM)](#dispatch-table-linear-gemm)
- [Overriding the dispatch — `--linear-backend` / `--moe-backend`](#overriding-the-dispatch----linear-backend----moe-backend)
- [MoE backend oracles](#moe-backend-oracles)
- [Blackwell-specific dispatch](#blackwell-specific-dispatch)
- [AMD / ROCm](#amd--rocm)
- [Hopper-specific notes](#hopper-specific-notes)
- [Marlin input dtype selection](#marlin-input-dtype-selection)
- [Sanity checks at load time](#sanity-checks-at-load-time)

---

## Kernel registry files

- Linear kernels: `vllm/model_executor/kernels/linear/{scaled_mm,nvfp4,mxfp4,mxfp8,mixed_precision}/`; the per-platform priority lists (`_POSSIBLE_KERNELS`, `_POSSIBLE_NVFP4_KERNELS`) are in `kernels/linear/__init__.py`
- W8A8 utils: `vllm/model_executor/layers/quantization/utils/w8a8_utils.py`
- DeepGEMM wrapper: `vllm/utils/deep_gemm.py`
- FlashInfer wrapper: `vllm/utils/flashinfer.py`
- MoE oracle: `vllm/model_executor/layers/fused_moe/oracle/{fp8,nvfp4,mxfp8}.py` — picks MoE backend per format.

## Dispatch table (linear GEMM)

| Format | Kernel class | Min SM | File |
|---|---|---|---|
| FP8 W8A8 | `MarlinFP8ScaledMMLinearKernel` | 75 | scaled_mm.py |
| FP8 W8A8 | CUTLASS via `cutlass_fp8_supported()` | 89 | w8a8_utils.py |
| FP8 block | CUTLASS via `cutlass_block_fp8_supported()` | 89 | w8a8_utils.py |
| FP8 block | DeepGEMM via `is_deep_gemm_supported()` | 80 | deep_gemm.py |
| FP8 (FlashInfer) | `FlashInferFP8ScaledMMLinearKernel` | 100 | flashinfer.py — **segfault-prone on SM100** ([#39814](https://github.com/vllm-project/vllm/issues/39814)) |
| INT8 W8A8 | CUTLASS INT8 | 75 | compressed_tensors_w8a8_int8.py |
| INT8 W8A8 (AMD asym) | `TritonInt8ScaledMMLinearKernel` | — | [PR #38501](https://github.com/vllm-project/vllm/pull/38501) |
| INT4 AWQ | `TritonInt4Kernel` | 60 | awq.py |
| INT4 AWQ-Marlin | Marlin | 75 | awq_marlin.py |
| INT4 GPTQ | `TritonInt8ScaledMMLinearKernel` | 60 | gptq.py |
| INT4 GPTQ | Exllamav2 | 60 | gptq.py |
| INT4 GPTQ-Marlin | Marlin | 75 | gptq_marlin.py |
| INT4 W4A8 | `CutlassW4A8LinearKernel` | 89 | — **dim alignment bug** ([#33783](https://github.com/vllm-project/vllm/issues/33783)) |
| NVFP4 | CUTLASS (Qutlass) | 75 (emulated) / 100 | modelopt.py:1091 |
| NVFP4 | TRTLLM GEN | 100 | modelopt.py:1799-1924 |
| NVFP4 | FlashInfer CuteDSL | 100 | [PR #38251](https://github.com/vllm-project/vllm/pull/38251) |
| NVFP4 | `NvFp4LinearKernel` (refactored) | — | [PR #39129](https://github.com/vllm-project/vllm/pull/39129) |
| NVFP4 | Machete | 100 | experimental |
| MXFP4 | Marlin | 80 | compressed_tensors_w4a16_mxfp4.py |
| MXFP4 MoE | CUTLASS MoE | 100 | [PR #37463](https://github.com/vllm-project/vllm/pull/37463) |
| MXFP8 | Marlin | 80 | mxfp8.py |
| MXFP8 | FlashInfer mm_mxfp8 | 100 | [PR #35053](https://github.com/vllm-project/vllm/pull/35053) |
| MXFP8 | `MxFp8LinearKernel` (refactored) | — | [PR #39205](https://github.com/vllm-project/vllm/pull/39205) |

## Overriding the dispatch — `--linear-backend` / `--moe-backend`

Both are first-class CLI flags; the authoritative value lists are the
`LinearBackend` and `MoEBackend` `Literal`s in
[`vllm/config/kernel.py`](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/kernel.py)
(21 linear / 23 MoE values at v0.32.0).

- `--linear-backend`: `auto` (default), `cutlass`, `flashinfer_cutlass`,
  `flashinfer_cutedsl`, `flashinfer_trtllm`, `flashinfer_cudnn`, `flashinfer_b12x`,
  `b12x`, `marlin`, `humming`, `triton`, `deep_gemm`, `torch`, `aiter`, `machete`,
  `fbgemm`, `conch`, `exllama`, `emulation`, `xpu`, `xpu_woq`.
- `--moe-backend`: `auto`, `triton`, `batched_triton`, `deep_gemm`,
  `deep_gemm_mega_moe`, `cutlass`, `flashinfer_trtllm`, `flashinfer_cutlass`,
  `flashinfer_cutedsl`, `flashinfer_moe_ep_cutedsl`, `flashinfer_b12x`, `b12x`,
  `flashinfer_moe_ep_mega_deep_gemm`, `marlin`, `humming`, `triton_unfused`,
  `aiter`, `aiter_mega_moe`, `aiter_triton_mxfp4_bf16`, `flydsl`, `hpc`,
  `emulation`, `rdna3`. v0.32.0 renamed `flashinfer_moe_ep_mega_cutedsl` to
  `flashinfer_moe_ep_cutedsl` (the old value no longer parses) and added
  `aiter_mega_moe` (ROCm DeepSeek-V4 MegaMoE).

**Gotcha:** `ModelOptNvFp4W4A16LinearMethod` **hardcoded Marlin and silently
ignored `--linear-backend`** until [PR #50273](https://github.com/vllm-project/vllm/pull/50273)
(merged 2026-07-30, v0.27.0). On v0.26.0 and earlier, setting a backend for a
ModelOpt W4A16 checkpoint is a no-op — verify the kernel actually changed rather
than trusting the flag. `auto` resolved to Marlin post-fix on v0.27.x-v0.29.x;
the PR only added the plumbing. **This flipped at v0.30.0**: FlashInfer CuTeDSL
NVFP4 W4A16 is now the default over Marlin on SM100/103
([#53014](https://github.com/vllm-project/vllm/pull/53014)).

**v0.30.0** added `linear_backend_per_quant` — a `KernelConfig` field for
mixed-precision checkpoints that use more than one linear quantization
scheme, set via `--kernel-config`:

```bash
vllm serve <model> --linear-backend cutlass \
  --kernel-config '{"linear_backend_per_quant":{"nvfp4_w4a16":"humming"}}'
```

Per-scheme overrides take precedence over `--linear-backend`; a scheme with
no entry keeps using the global setting, including `auto`
([#51204](https://github.com/vllm-project/vllm/pull/51204)).

## MoE backend oracles

Each format has a selector function in `fused_moe/oracle/`:

- `select_fp8_moe_backend()` — returns enum value (CUTLASS, TRTLLM, FLASHINFER_CUTEDSL, DEEPGEMM, MARLIN).
- `select_nvfp4_moe_backend()` — CUTLASS / TRTLLM / FLASHINFER_CUTEDSL / MACHETE.
- `select_mxfp8_moe_backend()` — CUTLASS / TRTLLM / FLASHINFER / MARLIN.

Selection is platform-dependent; Blackwell prefers TRTLLM + FlashInfer CuteDSL, Hopper prefers CUTLASS + DeepGEMM block.

**v0.32.0 MXFP4 MoE oracle** gained a CUTLASS W4A4 backend and a BF16-activation
fallback ([#60079](https://github.com/vllm-project/vllm/pull/60079)): an MXFP4
W4A4 checkpoint with no W4A4 kernel for the deployment now loads as W4A16 and
logs `No Mxfp4 MoE backend supports activation=... Falling back to '<backend>'
with BF16 activations.` Grep for it before benchmarking W4A4.

## Blackwell-specific dispatch

- **SM100** (B100/B200/GB200) — FP4 Tensor Cores; TRTLLM + FlashInfer CuteDSL preferred. `ENABLE_NVFP4_SM100` gate controls `mxfp4_experts_quant` bindings ([PR #40191](https://github.com/vllm-project/vllm/pull/40191)).
- **SM103** (B300/GB300, Blackwell Ultra) — TRTLLM attention had hang bug fixed in [PR #38730](https://github.com/vllm-project/vllm/pull/38730) (v0.19). Run v0.19.1+ on GB300.
- **SM120** (RTX 5090, RTX 6000 Pro) — *desktop* Blackwell. NVFP4 MoE kernel set NOT complete. Issues: [#35065](https://github.com/vllm-project/vllm/issues/35065), [#31085](https://github.com/vllm-project/vllm/issues/31085). Partial path via [PR #33417](https://github.com/vllm-project/vllm/pull/33417). [PR #37725](https://github.com/vllm-project/vllm/pull/37725) preserves arch suffix. v0.29.0+ ships the optional `b12x` backend for SM120/121 (`uv pip install "vllm[b12x]"`, `--linear-backend b12x --moe-backend b12x`): NVFP4/MXFP4 MoE with tensor parallelism only — no expert parallelism or expert maps; v0.32.0 added ModelOpt IQ2_XS / IQ2_XXS / Q8_0 block codecs ([#59604](https://github.com/vllm-project/vllm/pull/59604)). **Not a datacenter production target.**
- **SM121** (DGX Spark, GB10) — similar kernel gaps: [#39761](https://github.com/vllm-project/vllm/issues/39761), [#37030](https://github.com/vllm-project/vllm/issues/37030).
- **v0.30.0**: on SM120/121, W4A4 NVFP4 linear kernels are now preferred over
  the weight-only (W4A16) FlashInfer CuteDSL kernel when a checkpoint supports
  both — `FlashInferCuteDslNvFp4W4A16LinearKernel` moved from a preferred to a
  fallback position in `_POSSIBLE_NVFP4_KERNELS`
  ([#55170](https://github.com/vllm-project/vllm/pull/55170)). A W4A4-capable
  checkpoint on desktop Blackwell now gets real W4A4 compute instead of a
  silent weight-only downgrade.

## AMD / ROCm

- **FNUZ format** — MI300 requires FP8 FNUZ. `normalize_e4m3fn_to_e4m3fnuz()` in w8a8_utils.py (line 72). Scale adjustment `*= 2` in `kv_cache.py:84`. `current_platform.is_fp8_fnuz()` guard.
- **AWQ Marlin on ROCm** — landed v0.19 ([PR #36505](https://github.com/vllm-project/vllm/pull/36505)).
- **wvSplitK skinny GEMM** for RDNA4/gfx1x AWQ ([PR #34709](https://github.com/vllm-project/vllm/pull/34709)).
- **NVFP4 via emulation on MI300/MI355X** — [PR #35733](https://github.com/vllm-project/vllm/pull/35733) (v0.19).

## Hopper-specific notes

- **DeepGEMM** (`is_deep_gemm_supported`) — preferred for FP8 block MoE. SM80+ with FP8 native ops. Fused output quant in [PR #36518](https://github.com/vllm-project/vllm/pull/36518). E8M0 accuracy fix for Qwen3.5 FP8 on Blackwell: [PR #38083](https://github.com/vllm-project/vllm/pull/38083).
- **swapAB default on SM90** — [PR #34924](https://github.com/vllm-project/vllm/pull/34924) (v0.17).
- **Humming outranks Marlin on SM90 (v0.32.0)** — `prioritize_humming()` moves Humming directly ahead of Marlin in the linear lists and the FP8 / NVFP4 / MXFP4 / MXFP8 / INT-WNA16 MoE oracles, SM90 only ([#56997](https://github.com/vllm-project/vllm/pull/56997)). After upgrading, a Hopper deployment that resolved to Marlin under `auto` now runs Humming; pin `--linear-backend marlin` / `--moe-backend marlin` to A/B a throughput or accuracy shift.
- **CUTLASS FP8 blockwise on SM103a** — [PR #32224](https://github.com/vllm-project/vllm/pull/32224).

## Marlin input dtype selection

`get_marlin_input_dtype()`:
- `modelopt.py:68` — selects marlin input for ModelOpt NVFP4 / MXFP8.
- `fp8.py:57` — selects for FP8.
- `fp8.py:384-391` — `use_marlin` gate for dispatch.

## Sanity checks at load time

```python
# kv_cache.py
kv_cache_uses_per_token_head_scales()    # line 60 — dynamic per-(token, head)
# fp8.py
Fp8Config.get_min_capability()           # line 144 — SM75
# modelopt.py
ModelOptNvFp4Config.get_min_capability() # line 1028 — SM75 emulated
```

Validation lives in `ModelConfig.override_quantization_method()` per config class (model.py:968-987).
