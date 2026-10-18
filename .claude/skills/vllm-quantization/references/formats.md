# Quantization formats — per-file deep dive

Every entry: CLI flag, vLLM source file, config class + line, min SM capability,
kernels dispatched to, status, key caveats. Source of truth is
[`vllm/model_executor/layers/quantization/`](https://github.com/vllm-project/vllm/tree/main/vllm/model_executor/layers/quantization).

## Table of Contents

- [Dispatcher](#dispatcher)
- [FP8 — `--quantization fp8`](#fp8----quantization-fp8)
- [ModelOpt FP8 — `--quantization modelopt`](#modelopt-fp8----quantization-modelopt)
- [ModelOpt NVFP4 — `--quantization modelopt_fp4`](#modelopt-nvfp4----quantization-modelopt_fp4)
- [ModelOpt MXFP8 — `--quantization modelopt_mxfp8`](#modelopt-mxfp8----quantization-modelopt_mxfp8)
- [ModelOpt mixed — `--quantization modelopt_mixed`](#modelopt-mixed----quantization-modelopt_mixed)
- [compressed-tensors — `--quantization compressed-tensors`](#compressed-tensors----quantization-compressed-tensors)
- [AWQ — `--quantization awq` / `awq_marlin` / `auto_awq`](#awq----quantization-awq--awq_marlin--auto_awq)
- [GPTQ — `--quantization gptq` / `gptq_marlin` / `auto_gptq`](#gptq----quantization-gptq--gptq_marlin--auto_gptq)
- [MXFP4 — `--quantization mxfp4` / `gpt_oss_mxfp4`](#mxfp4----quantization-mxfp4--gpt_oss_mxfp4)
- [MXFP8 — `--quantization mxfp8`](#mxfp8----quantization-mxfp8)
- [FBGEMM FP8 — `--quantization fbgemm_fp8` (DEPRECATED)](#fbgemm-fp8----quantization-fbgemm_fp8-deprecated)
- [FP_Quant — `--quantization fp_quant` (DEPRECATED)](#fp_quant----quantization-fp_quant-deprecated)
- [Quark — `--quantization quark`](#quark----quantization-quark)
- [experts_int8 / `int8_per_channel_weight_only` (online)](#experts_int8--int8_per_channel_weight_only-online)
- [moe_wna16 — `--quantization moe_wna16`](#moe_wna16----quantization-moe_wna16)
- [torchao — `--quantization torchao`](#torchao----quantization-torchao)
- [inc / auto-round — `--quantization inc` / `--quantization auto-round`](#inc--auto-round----quantization-inc----quantization-auto-round)
- [bitsandbytes — moved out-of-tree (plugin)](#bitsandbytes--moved-out-of-tree-plugin)
- [gguf — moved out-of-tree (plugin)](#gguf--moved-out-of-tree-plugin)
- [cpu_awq — removed, folded into `awq_marlin`](#cpu_awq--removed-folded-into-awq_marlin)
- [online — `--quantization online` (and shortcuts)](#online----quantization-online-and-shortcuts)
- [TurboQuant (KV-only)](#turboquant-kv-only)
- [Example config-JSON shapes](#example-config-json-shapes)
- [Config-filename table per method](#config-filename-table-per-method)

---

## Dispatcher

[`vllm/model_executor/layers/quantization/__init__.py`](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/model_executor/layers/quantization/__init__.py) — grep `QuantizationMethods = Literal` for the flag list and `def get_quantization_config` for the dispatch table (line ranges drift every minor). Detection flow in [`vllm/config/model.py`](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/model.py), `override_quantization_method()`.

Full 30-flag catalog **verified against v0.32.0** (unchanged since v0.28.0 dropped `bitsandbytes`): `awq, auto_awq, fp8, fbgemm_fp8, fp_quant, modelopt, modelopt_fp4, modelopt_mxfp8, modelopt_mixed, auto_gptq, gptq, gptq_marlin, awq_marlin, humming, compressed-tensors, experts_int8, quark, moe_wna16, torchao, inc, mxfp4, gpt_oss_mxfp4, deepseek_v4_fp8, online, fp8_per_tensor, fp8_per_block, fp8_per_channel, int8_per_channel_weight_only, nvfp4_per_token, mxfp8`.

`DEPRECATED_QUANTIZATION_METHODS` (same file) is exactly `["fbgemm_fp8", "fp_quant"]`. **`gguf` and `cpu_awq` are no longer in the list** — see their sections below.

## FP8 — `--quantization fp8`

- **File**: `vllm/model_executor/layers/quantization/fp8.py`
- **Config class**: `Fp8Config` (line 92 at v0.32.0)
- **Min SM**: 75
- **Activation schemes**: `static`, `dynamic`
- **Kernels**: Marlin (`MarlinFP8ScaledMMLinearKernel`), CUTLASS (`cutlass_fp8_supported`), DeepGEMM (`use_deep_gemm`)
- **KV support**: `Fp8KVCacheMethod` (class line 850)
- **MoE**: `Fp8MoEMethod` (class line 464)
- **Pre-quantized checkpoints only from v0.31.0** ([PR #53585](https://github.com/vllm-project/vllm/pull/53585)): `Fp8Config(is_checkpoint_fp8_serialized=False)` raises *"The `fp8` quantization method no longer supports online quantization"*; with no quant config in the checkpoint, `--quantization fp8` logs a deprecation warning and loads through the `fp8_per_tensor` online shorthand.

Key config fields: `is_checkpoint_fp8_serialized`, `activation_scheme`, `ignored_layers`, `weight_block_size`.

## ModelOpt FP8 — `--quantization modelopt`

- **File**: `vllm/model_executor/layers/quantization/modelopt.py`
- **Config class**: `ModelOptFp8Config` (line 362)
- **Min SM**: 89
- **Quant algo**: `FP8` from checkpoint (line 105)
- **Kernels**: Marlin, CUTLASS FP8, FlashInfer (lines 1799-1924)
- **Base class**: `ModelOptQuantConfigBase` (line 129), wildcard `exclude_modules` (fnmatch line 174), auto-skip `vision_tower` (line 197)

## ModelOpt NVFP4 — `--quantization modelopt_fp4`

- **Config class**: `ModelOptNvFp4Config` (line 1000)
- **Min SM**: 75 (emulated), 100 native
- **Kernels**: CUTLASS (Qutlass, line 1091), TRTLLM, FlashInfer CuteDSL, Machete
- **KV support**: `ModelOptFp8KVCacheMethod` (line 120) — FP8 KV, not NVFP4 KV yet
- **Backend selection**: `select_nvfp4_moe_backend` in [`vllm/model_executor/layers/fused_moe/oracle/nvfp4.py`](https://github.com/vllm-project/vllm/tree/main/vllm/model_executor/layers/fused_moe/oracle)

Recent landmarks: [PR #35733](https://github.com/vllm-project/vllm/pull/35733) (NVFP4 on AMD MI300 / Hopper via emulation, v0.19), [PR #37725](https://github.com/vllm-project/vllm/pull/37725) (SM12x arch-suffix fix), [PR #39510](https://github.com/vllm-project/vllm/pull/39510) (TRTLLM NVFP4 MoE for non-512-aligned hidden dims).

## ModelOpt MXFP8 — `--quantization modelopt_mxfp8`

- **Config class**: `ModelOptMxFp8Config` (line 1492)
- **Min SM**: 89
- **Quant algo**: `MXFP8`
- **Kernels**: Marlin (via `get_marlin_input_dtype`), FlashInfer
- **MoE backend**: `select_mxfp8_moe_backend`

## ModelOpt mixed — `--quantization modelopt_mixed`

- **Config class**: `ModelOptMixedPrecisionConfig` (line 2021)
- **Min SM**: 89
- Mixed FP8 / FP16 per layer. Added [PR #35047](https://github.com/vllm-project/vllm/pull/35047), v0.17.

## compressed-tensors — `--quantization compressed-tensors`

- **File**: `vllm/model_executor/layers/quantization/compressed_tensors/compressed_tensors.py`
- **Config class**: `CompressedTensorsConfig` (line 80)
- **Schemes** in `compressed_tensors/schemes/`:

| Scheme file | SM | Kernels |
|---|---|---|
| `compressed_tensors_w8a8_fp8.py` | 89 | CUTLASS, Marlin, DeepGEMM |
| `compressed_tensors_w8a16_fp8.py` | 75 | Marlin |
| `compressed_tensors_w8a8_int8.py` | 75 | CUTLASS INT8, Triton (AMD asymmetric) |
| `compressed_tensors_w4a16_nvfp4.py` | 75 | CUTLASS (Qutlass), TRTLLM |
| `compressed_tensors_w4a4_nvfp4.py` | 75 | CUTLASS (Qutlass) |
| `compressed_tensors_w4a16_mxfp4.py` | 80 | Marlin |
| `compressed_tensors_w8a8_mxfp8.py` | 80 | Marlin, FlashInfer |
| `compressed_tensors_wNa16.py` | varies | per bits |
| `compressed_tensors_24.py` | varies | Triton, CUTLASS |

New in v0.19: `CompressedTensorsW8A8Mxfp8` ([PR #38815](https://github.com/vllm-project/vllm/pull/38815)). Ground-truth for quant-strategy decisions since [PR #34254](https://github.com/vllm-project/vllm/pull/34254) (v0.16).

Transform layer: `compressed_tensors/transform/linear.py` (torch::compile shape transforms).

### compressed-tensors schema

Spec: [`quant_scheme.py`](https://github.com/neuralmagic/compressed-tensors/blob/main/src/compressed_tensors/quantization/quant_scheme.py).

Top-level `quantization_config` fields in HF `config.json`:

- `quant_method`: `compressed-tensors`
- `format`: `dense`, `float-quantized`, `int-quantized`, `pack-quantized`, `naive-quantized`, `marlin-24`, `nvfp4-pack-quantized`, `mxfp4-pack-quantized`
- `config_groups`: dict of `QuantizationScheme`
  - `targets: list[str]` (e.g. `Linear`, `re:.*mlp.*`)
  - `weights: QuantizationArgs | None`
  - `input_activations: QuantizationArgs | None`
  - `output_activations: QuantizationArgs | None`
- `ignore: list[str]` — **audit this carefully for hybrid-attention models** (issue #40252)
- `kv_cache_scheme: QuantizationArgs | None`
- `quantization_status`: `initialized` | `calibration` | `frozen` | `compressed`

`QuantizationArgs` fields: `num_bits`, `type` (INT/FLOAT), `strategy` (TENSOR, CHANNEL, GROUP, TENSOR_GROUP, TOKEN, ATTN_HEAD, BLOCK), `symmetric`, `group_size` (16 for NVFP4, 32 for MXFP4, 128 for W4A16), `actorder`, `dynamic`, `observer`, `scale_dtype`, `zp_dtype`, `block_structure` (`[128, 128]` for FP8_BLOCK).

Preset schemes: `UNQUANTIZED`, `W8A16`, `W4A16`, `W4A16_ASYM`, `W8A8`, `INT8`, `W4A8`, `W4AFP8`, `FP8`, `FP8_DYNAMIC`, `FP8_BLOCK`, `NVFP4A16`, `NVFP4`, `MXFP4A16`, `MXFP4`, `MXFP8A16`, `MXFP8`.

## AWQ — `--quantization awq` / `awq_marlin` / `auto_awq`

- **File**: `vllm/model_executor/layers/quantization/auto_awq.py` — all three values map to `AutoAWQConfig` (line 174 at v0.32.0); the old `awq.py` / `awq_marlin.py` split is gone.
- **Min SM**: 75
- **Kernels**: Marlin on CUDA when `check_marlin_supported()` passes (not under `VLLM_BATCH_INVARIANT`), Triton otherwise; CPU/XPU take the Marlin method's mixed-precision kernel picker. The flag value does not select the kernel.
- 4-bit only through this config (8-bit AWQ errors with a pointer to the Marlin backend).

ROCm AWQ Marlin: [PR #36505](https://github.com/vllm-project/vllm/pull/36505), v0.19.

## GPTQ — `--quantization gptq` / `gptq_marlin` / `auto_gptq`

- **File**: `vllm/model_executor/layers/quantization/auto_gptq.py` — all three values map to `AutoGPTQConfig` (line 95 at v0.32.0).
- **Min SM**: 60
- **Kernels**: Marlin (linear and MoE).
- Consolidated in [PR #37768](https://github.com/vllm-project/vllm/pull/37768); slow-GEMM removed ([PR #36900](https://github.com/vllm-project/vllm/pull/36900)); group/dynamic activation ordering (`g_idx`) removed in v0.30.0 ([PR #54809](https://github.com/vllm-project/vllm/pull/54809)).

## MXFP4 — `--quantization mxfp4` / `gpt_oss_mxfp4`

- **File**: `vllm/model_executor/layers/quantization/mxfp4.py`
- **Config class**: `Mxfp4Config` (line 40), `GptOssMxfp4Config` (line 104)
- **Min SM**: 80 (linear fallback), MoE kernel on SM100+
- **Linear NOT implemented** — falls back to unquantized (line 83-88). MoE only via `GptOssMxfp4MoEMethod`.
- **Bfloat16 only** for activations (line 64).

Landmarks: [PR #31926](https://github.com/vllm-project/vllm/pull/31926) (dense W4A16 v0.14), [PR #32285](https://github.com/vllm-project/vllm/pull/32285) (MoE W4A16 v0.15), [PR #37463](https://github.com/vllm-project/vllm/pull/37463) (W4A4 CUTLASS MoE SM100, v0.19).

## MXFP8 — `--quantization mxfp8`

- **Dual role**: an online shorthand (`_ONLINE_SHORTHANDS`) *and* the checkpoint `quant_method: "mxfp8"` some exports carry, which loads through `ModelOptMxFp8Config` (`modelopt.py`). There is no `mxfp8.py`.
- **Min SM**: 80
- **Kernels**: Marlin, Humming (preferred on SM90 from v0.32.0), FlashInfer `mm_mxfp8` on SM100
- Block params: `MXFP8_BLOCK_SIZE`, `MXFP8_SCALE_DTYPE`, `MXFP8_VALUE_DTYPE` in `utils/mxfp8_utils`.

Landmarks: [PR #35448](https://github.com/vllm-project/vllm/pull/35448) (online v0.19), [PR #39205](https://github.com/vllm-project/vllm/pull/39205) (`MxFp8LinearKernel`).

## FBGEMM FP8 — `--quantization fbgemm_fp8` (DEPRECATED)

- **File**: `vllm/model_executor/layers/quantization/fbgemm_fp8.py`
- **Config class**: `FBGEMMFp8Config` (line 31)
- **Min SM**: 80
- Deprecated in `__init__.py:49`. Use `fp8` instead.

## FP_Quant — `--quantization fp_quant` (DEPRECATED)

- **File**: `vllm/model_executor/layers/quantization/fp_quant.py`
- **Config class**: `FPQuantConfig` (line 21)
- **Min SM**: 100
- Deprecated in `__init__.py:50`.

## Quark — `--quantization quark`

- **File**: `vllm/model_executor/layers/quantization/quark/quark.py`
- **Config class**: `QuarkConfig`
- **Supported**: W8A8 INT8 (MoE), W4A8 MXFP4/FP8 ([PR #35316](https://github.com/vllm-project/vllm/pull/35316), v0.18), native W4A16 INT4/UINT4 exports ([PR #48606](https://github.com/vllm-project/vllm/pull/48606), v0.31.0)
- **v0.31.0 removed Quark's silent online MXFP4 quantization** ([PR #51800](https://github.com/vllm-project/vllm/pull/51800)) — request online MXFP4 through `--quantization-config` instead.
- AMD's quantizer. Docs: [vllm.ai/.../quark](https://docs.vllm.ai/en/stable/features/quantization/quark/).

## experts_int8 / `int8_per_channel_weight_only` (online)

- **File**: `vllm/model_executor/layers/quantization/experts_int8.py`
- **Config class**: `ExpertsInt8Config` (line 20)
- **Min SM**: 80
- **Online MoE method**: `Int8OnlineMoEMethod` (line 57)
- Consolidated with online FP8 in [PR #38463](https://github.com/vllm-project/vllm/pull/38463). Use `--quantization int8_per_channel_weight_only` for new deployments.

## moe_wna16 — `--quantization moe_wna16`

- **File**: `vllm/model_executor/layers/quantization/moe_wna16.py`
- **Config class**: `MoeWNA16Config` (line 37)
- **Min SM**: 70
- **Linear method values**: `gptq`, `awq`, `awq_marlin`
- Marlin dispatch conditional on `is_gptq_marlin_compatible` / `is_awq_marlin_compatible`.

Fields: `linear_quant_method`, `weight_bits`, `group_size`, `has_zp`, `lm_head_quantized`, `modules_to_not_convert`.

## torchao — `--quantization torchao`

- **File**: `vllm/model_executor/layers/quantization/torchao.py`
- **Config class**: `TorchAOConfig` (line 30)
- **Min SM**: 75
- Accepts PyTorch composable configs: `Float8WeightOnlyConfig`, `Int8WeightOnlyConfig`, etc.

## inc / auto-round — `--quantization inc` / `--quantization auto-round`

- **File**: `vllm/model_executor/layers/quantization/inc/inc.py` (moved into an
  `inc/` package)
- **Config class**: `INCConfig`
- **Min SM**: 60
- Intel Neural Compressor, including AutoRound-packed checkpoints
  (`auto_round:auto_gptq` / `auto_round:auto_awq` / `auto_round:fp8` /
  `auto_round:llm_compressor`). `auto-round` is not its own `--quantization`
  value — it is a packing format loaded through `inc`.
- **v0.30.0** added CUDA support for AutoRound's 2/3/5/6/7-bit widths: CUDA's
  Marlin/GPTQ/AWQ kernels only cover 4/8-bit, so these widths now dispatch to
  the Humming kernel instead of erroring
  ([#52890](https://github.com/vllm-project/vllm/pull/52890)).

## bitsandbytes — moved out-of-tree (plugin)

`bitsandbytes.py` left the tree in v0.28.0 (#43529) and `bitsandbytes` is not in
`QuantizationMethods`. Install [`vllm-bnb-plugin`](https://github.com/vllm-project/vllm-bnb-plugin)
(`uv pip install vllm-bnb-plugin`, `docs/features/quantization/bnb.md`); it
handles both in-flight quantization and pre-quantized NF4/FP4 checkpoints.

## gguf — moved out-of-tree (plugin)

`vllm/model_executor/layers/quantization/gguf.py` **no longer exists** at v0.27.0
and `gguf` is not in `QuantizationMethods`. GGUF support migrated to the
out-of-tree [`vllm-gguf-plugin`](https://github.com/vllm-project/vllm-gguf-plugin)
(`docs/features/quantization/gguf.md`, v0.27.0).

```bash
uv pip install vllm-gguf-plugin
vllm serve unsloth/Qwen3-0.6B-GGUF:Q4_K_M --tokenizer Qwen/Qwen3-0.6B
```

Load by `repo_id:quant_type` or a local `.gguf` path. Upstream still labels it
"highly experimental and under-optimized"; always pass the **base model's**
tokenizer — GGUF tokenizer conversion is slow and unstable on large vocabs. Not
a production datacenter path.

## cpu_awq — removed, folded into `awq_marlin`

[PR #43841](https://github.com/vllm-project/vllm/pull/43841) (merged 2026-05-28)
migrated `cpu_awq` into `awq_marlin`. The flag value and
`quantization/cpu_wna16.py` are gone at v0.27.0 — use `--quantization awq_marlin`
on CPU.

## online — `--quantization online` (and shortcuts)

- **File**: `vllm/model_executor/layers/quantization/online/base.py`
- **Config class**: `OnlineQuantizationConfig` (line 44)
- **Min SM**: 75
- **Shortcuts** (`_ONLINE_SHORTHANDS`, `vllm/config/quantization.py`): `fp8_per_tensor`, `fp8_per_block`, `fp8_per_channel`, `int8_per_channel_weight_only`, `nvfp4_per_token`, `mxfp8`
- **Config args**: `QuantizationConfigArgs` in `vllm/config/quantization.py` — fields are `linear`, `moe` (each a `QuantSpec` with `weight` / `activation`), `ignore`, and (v0.30.0+) `targets` (`{pattern: shorthand}`, mutually exclusive with `linear`/`moe`). Weight/activation names come from `QUANT_KEY_NAMES` in the same file (`fp8_per_tensor_static`, `fp8_per_tensor_dynamic`, `fp8_per_token`, `fp8_per_channel_static`, `fp8_per_block_static`, `fp8_per_block_dynamic`, `mxfp8`, `mxfp4`, `nvfp4_per_token`, `int8_per_channel_static`, `int4_per_group_32` — the last is the gfx942 load-time MXFP4-to-int4 path).
- **Re-quantization (v0.32.0)**: an online target can re-quantize a checkpoint-quantized linear layer (dequantize, then quantize); only serialized ModelOpt MXFP8 linears are a supported source, other pairs raise ([PR #55684](https://github.com/vllm-project/vllm/pull/55684)).
- Passed via **`--quantization-config`** (JSON or dotted keys). There is no `--quantization-config-file` flag, no `global_scheme` / `linear_scheme_override` / `moe_scheme_override` keys, and no `OnlineQuantScheme` enum — that was the pre-v0.25 shape.
- XPU: non-block FP8 scaled-mm linear defaults to W8A16; `--linear-backend xpu` forces W8A8, `--linear-backend xpu_woq` pins weight-only.

RFC: [PR #37776](https://github.com/vllm-project/vllm/pull/37776). Schema doc: `docs/features/quantization/online.md`.

Advanced-config example:

```yaml
quantization_config:
  linear:
    weight: fp8_per_tensor_static
    activation: fp8_per_token
  moe:
    weight: fp8_per_block_static
  ignore:
    - lm_head
    - embed_tokens
```

## TurboQuant (KV-only)

- **File**: `vllm/model_executor/layers/quantization/turboquant/config.py`
- **Dtypes**: `turboquant_k8v4`, `turboquant_4bit_nc`, `turboquant_k3v4_nc`, `turboquant_3bit_nc`
- **Method**: Hadamard rotation + Lloyd-Max (keys) + uniform (values)
- **Presets**:

| Preset | What | Compression | PPL cost |
|---|---|---|---|
| `turboquant_k8v4` | FP8 K + 4-bit V | 2.6× | +1.17 % |
| `turboquant_4bit_nc` | 4-bit MSE K + 4-bit V + NC | 3.8× | +2.71 % |
| `turboquant_k3v4_nc` | 3-bit MSE K + 4-bit V + NC | ~3.5× | +10.63 % |
| `turboquant_3bit_nc` | 3-bit K + 3-bit V + NC | 4.9× | +20.59 % |

Landed v0.19 ([PR #38479](https://github.com/vllm-project/vllm/pull/38479)). KV-only — pair with separate weight quant.

## Example config-JSON shapes

### compressed-tensors FP8 W8A8

```json
{
  "quantization_config": {
    "format": "compressed-tensors",
    "quantization": [{
      "type": "quantization",
      "strategy": "tensor",
      "targets": ["linear_*"],
      "weights": {"num_bits": 8, "type": "float", "symmetric": true, "strategy": "tensor"},
      "input_activations": null,
      "output_activations": {"num_bits": 8, "type": "float", "symmetric": true, "strategy": "tensor"}
    }]
  }
}
```

### ModelOpt NVFP4

```json
{
  "quant_method": "NVFP4",
  "exclude_modules": ["lm_head"],
  "global_sf": true
}
```

### ModelOpt FP8

```json
{
  "quant_method": "FP8",
  "activation_scheme": "static",
  "weight_block_size": null,
  "exclude_modules": []
}
```

### AWQ

```json
{
  "quant_method": "awq",
  "zero_point": true,
  "group_size": 128,
  "bits": 4,
  "version": "GEMM"
}
```

### GPTQ

```json
{
  "quant_method": "gptq",
  "bits": 4,
  "group_size": 128,
  "sym": true,
  "desc_act": false
}
```

### MXFP4 (GPT-OSS)

```json
{
  "quant_method": "mxfp4",
  "model_type": "gpt_oss"
}
```

## Config-filename table per method

| Method | Config filenames loaded |
|---|---|
| awq, gptq, gptq_marlin, awq_marlin, moe_wna16 | `quantize_config.json` |
| compressed-tensors | (embedded in `config.json.quantization_config`) |
| modelopt, modelopt_fp4, modelopt_mxfp8, modelopt_mixed | (embedded in `config.json.quantization_config` or `hf_quant_config.json`) |
| fp8 | — (detected from checkpoint + `quant_method`) |
| mxfp4 | — |

Override registration: `@classmethod get_config_filenames()` in `base_config.py:100-102`.
