# Quantization formats — per-file deep dive

Every entry: CLI flag, vLLM source file, config class + line, min SM capability,
kernels dispatched to, status, key caveats. Source of truth is
[`vllm/model_executor/layers/quantization/`](https://github.com/vllm-project/vllm/tree/main/vllm/model_executor/layers/quantization).

## Dispatcher

[`vllm/model_executor/layers/quantization/__init__.py:107-184`](https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/layers/quantization/__init__.py) — `get_quantization_config()`. Detection flow in [`vllm/config/model.py:930-1010`](https://github.com/vllm-project/vllm/blob/main/vllm/config/model.py).

Full 29-flag catalog: `awq, fp8, fbgemm_fp8, fp_quant, modelopt, modelopt_fp4, modelopt_mxfp8, modelopt_mixed, gguf, gptq_marlin, awq_marlin, gptq, compressed-tensors, bitsandbytes, experts_int8, quark, moe_wna16, torchao, inc, mxfp4, gpt_oss_mxfp4, mxfp8, cpu_awq, online, fp8_per_tensor, fp8_per_block, int8_per_channel_weight_only`.

## FP8 — `--quantization fp8`

- **File**: `vllm/model_executor/layers/quantization/fp8.py`
- **Config class**: `Fp8Config` (line 96)
- **Min SM**: 75
- **Activation schemes**: `static`, `dynamic`
- **Kernels**: Marlin (`MarlinFP8ScaledMMLinearKernel`), CUTLASS (`cutlass_fp8_supported`), DeepGEMM (`use_deep_gemm`)
- **KV support**: `Fp8KVCacheMethod` (line 203)
- **MoE**: `Fp8MoEMethod` (line 198), `Fp8OnlineMoEMethod` (line 200)
- **Block quant**: `weight_block_size` requires `is_checkpoint_fp8_serialized=True`

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

## AWQ — `--quantization awq`

- **File**: `vllm/model_executor/layers/quantization/awq.py`
- **Config class**: `AWQConfig` (line 26)
- **Min SM**: 60
- **Kernels**: Triton
- Deprecated for production — use `awq_marlin`.

## AWQ-Marlin — `--quantization awq_marlin`

- **File**: `vllm/model_executor/layers/quantization/awq_marlin.py`
- **Config class**: `AWQMarlinConfig` (line 152)
- **Min SM**: 75
- **Kernels**: Marlin
- **Compat check**: `is_awq_marlin_compatible()` (line 153-170)

ROCm AWQ Marlin: [PR #36505](https://github.com/vllm-project/vllm/pull/36505), v0.19.

## GPTQ — `--quantization gptq`

- **File**: `vllm/model_executor/layers/quantization/gptq.py`
- **Config class**: `GPTQConfig` (line 40)
- **Min SM**: 60
- **Kernels**: Triton, Exllamav2
- Consolidated with `gptq_marlin` in [PR #37768](https://github.com/vllm-project/vllm/pull/37768); slow-GEMM removed ([PR #36900](https://github.com/vllm-project/vllm/pull/36900)).

## GPTQ-Marlin — `--quantization gptq_marlin`

- **File**: `vllm/model_executor/layers/quantization/gptq_marlin.py`
- **Config class**: `GPTQMarlinConfig` (line 95)
- **Min SM**: 75
- **Kernels**: Marlin

## MXFP4 — `--quantization mxfp4` / `gpt_oss_mxfp4`

- **File**: `vllm/model_executor/layers/quantization/mxfp4.py`
- **Config class**: `Mxfp4Config` (line 40), `GptOssMxfp4Config` (line 104)
- **Min SM**: 80 (linear fallback), MoE kernel on SM100+
- **Linear NOT implemented** — falls back to unquantized (line 83-88). MoE only via `GptOssMxfp4MoEMethod`.
- **Bfloat16 only** for activations (line 64).

Landmarks: [PR #31926](https://github.com/vllm-project/vllm/pull/31926) (dense W4A16 v0.14), [PR #32285](https://github.com/vllm-project/vllm/pull/32285) (MoE W4A16 v0.15), [PR #37463](https://github.com/vllm-project/vllm/pull/37463) (W4A4 CUTLASS MoE SM100, v0.19).

## MXFP8 — `--quantization mxfp8`

- **File**: `vllm/model_executor/layers/quantization/mxfp8.py`
- **Config class**: `Mxfp8Config` (line 10)
- **Min SM**: 80
- **Kernels**: Marlin
- **Online path**: `Mxfp8OnlineLinearMethod`, `Mxfp8OnlineMoEMethod` (lines 101-109)
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
- **Supported**: W8A8 INT8 (MoE), W4A8 MXFP4/FP8 ([PR #35316](https://github.com/vllm-project/vllm/pull/35316), v0.18)
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

- **File**: `vllm/model_executor/layers/quantization/inc.py`
- **Config class**: `INCConfig` (line 40)
- **Min SM**: 60
- Intel Neural Compressor + AutoRound path.

## bitsandbytes — `--quantization bitsandbytes`

- **File**: `vllm/model_executor/layers/quantization/bitsandbytes.py`
- **Config class**: `BitsAndBytesConfig` (line 28)
- **Min SM**: 70
- Formats: NF4, FP4, FP8
- ROCm support: [PR #34688](https://github.com/vllm-project/vllm/pull/34688), v0.17.

## gguf — `--quantization gguf`

- **File**: `vllm/model_executor/layers/quantization/gguf.py`
- **Config class**: `GGUFConfig` (line 24)
- **Min SM**: 60
- GGML-ecosystem quantized weights. Not a production datacenter path.

## cpu_awq — `--quantization cpu_awq`

- **File**: `vllm/model_executor/layers/quantization/cpu_wna16.py`
- **Config class**: `CPUAWQConfig` (line 25)
- **Capability**: -1 (CPU only)

## online — `--quantization online` (and shortcuts)

- **File**: `vllm/model_executor/layers/quantization/online/base.py`
- **Config class**: `OnlineQuantizationConfig` (line 44)
- **Min SM**: 75
- **Shortcuts**: `fp8_per_tensor`, `fp8_per_block`, `int8_per_channel_weight_only`
- **Config args**: `OnlineQuantizationConfigArgs` with `global_scheme`, `linear_scheme_override`, `moe_scheme_override`, `ignore`
- `OnlineQuantScheme` enum: `FP8_PER_TENSOR`, `FP8_PER_BLOCK`, `INT8_PER_CHANNEL_WEIGHT_ONLY`

RFC: [PR #37776](https://github.com/vllm-project/vllm/pull/37776).

YAML example:

```yaml
global_scheme: fp8_per_tensor
ignore:
  - lm_head
  - embed_tokens
linear_scheme_override: ~
moe_scheme_override: ~
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
