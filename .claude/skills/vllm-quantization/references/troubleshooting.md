# Troubleshooting — symptom → issue → fix

Organised by symptom. Look up the symptom, read the issue, apply the workaround. Many of these are *open* — treat memory as possibly stale; verify on [the issue tracker](https://github.com/vllm-project/vllm/issues).

## Garbage / repetitive output

| Symptom | Model / scenario | Issue | Fix |
|---|---|---|---|
| Repetitive garbage after FP8-block load | Gemma 4 31B | [#39407](https://github.com/vllm-project/vllm/issues/39407) | Use non-block FP8 or static per-tensor |
| FP8 dynamic → gibberish | Gemma 4 (any size) | [#39049](https://github.com/vllm-project/vllm/issues/39049) | Avoid FP8 on Gemma 4, use FP16/BF16 |
| NVFP4 Qwen3-Next → garbage | Any hybrid-attention model | [#40252](https://github.com/vllm-project/vllm/issues/40252) | Audit `quantization_config.ignore` — add all `linear_attn`, `fla`, `mamba` entries |
| FP8 KV MLA multi-turn corruption | DeepSeek V3/V3.2, GLM-4.5/4.6/4.7, Kimi K2 | [#38652](https://github.com/vllm-project/vllm/issues/38652) | **Avoid FP8 KV on MLA multi-turn** — open |
| NVFP4 Marlin NaN/Inf with fp16 | — | Fixed [PR #33972](https://github.com/vllm-project/vllm/pull/33972) | v0.19+ |
| NVFP4 NaN on desktop Blackwell (SM12x) | RTX 5090, RTX 6000 Pro | Fixed [PR #37725](https://github.com/vllm-project/vllm/pull/37725) | v0.19+ |
| BF16 NVFP4 Marlin garbled on non-FP4 GPU | H100, older | [#34694](https://github.com/vllm-project/vllm/issues/34694) | Partial fix [PR #34577](https://github.com/vllm-project/vllm/pull/34577) v0.17; latent cases remain |
| FP8 MLA KV gibberish from scale inconsistency | — | Fixed [PR #37054](https://github.com/vllm-project/vllm/pull/37054) | v0.19 |
| Empty output FP8 + TP=2 Qwen3-8B | Qwen3-8B | [#36583](https://github.com/vllm-project/vllm/issues/36583) | Open |
| GPTQ exclamation-point-only output | Qwen3.5 397B on ROCM | [#37996](https://github.com/vllm-project/vllm/issues/37996) | Open |
| Marlin wrong first Harmony token | GPT-OSS-120B SM121 | [#37030](https://github.com/vllm-project/vllm/issues/37030) | Open; SM121 not production |
| Non-deterministic degenerate output | Dynamic FP8 + LoRA-merged on B200 | [#39662](https://github.com/vllm-project/vllm/issues/39662) | Pin static FP8, or unmerge LoRA |

## Load / init failures

| Symptom | Issue | Fix |
|---|---|---|
| `AttributeError: cannot deserialize quantization_config` | — | Upgrade: `vllm>=0.5.5`, `compressed-tensors>=0.5.0` |
| Unknown quantization method: mxfp4 | Closed [#22276](https://github.com/vllm-project/vllm/issues/22276) | Upgrade vLLM; mxfp4 needs v0.14+ |
| NVFP4 weight missing `_double_scale` key | ModelOpt export on DGX Spark | [#38980](https://github.com/vllm-project/vllm/issues/38980) | Regenerate with ModelOpt ≥ current release |
| Uninitialised `PerTensorScaleParameter` → NaN | Fused-QKV NVFP4 | [#39764](https://github.com/vllm-project/vllm/issues/39764) | Use split-QKV checkpoints |
| `quant_algo MIXED_PRECISION` rejected | NGC vLLM 26.02 + Nemotron-3 NVFP4 | [#37854](https://github.com/vllm-project/vllm/issues/37854) | Use plain NVFP4 config; allow-list gap |
| PTX toolchain error | Kimi-K2.5 compressed-tensors MoE on H200 | [#38619](https://github.com/vllm-project/vllm/issues/38619) | Driver ≥ 575 or rebuild Marlin |
| Gemma 4 MoE NVFP4 `expert_params_mapping` | Gemma 4 | [#38912](https://github.com/vllm-project/vllm/issues/38912) | Open |
| Can't start Qwen3.5-397B NVFP4 on 2×/4× B200 | SM100 | [#38550](https://github.com/vllm-project/vllm/issues/38550) | Use 8× B200 |
| "Waiting for core engine" hang | Mistral Large 3 NVFP4 on 8× B300 | [#34133](https://github.com/vllm-project/vllm/issues/34133) | Open |
| Qwen3.5 AWQ crash with Triton OOM | RTX 5090 | [#36450](https://github.com/vllm-project/vllm/issues/36450) | Workaround: TP=1, manual Triton cache clear |
| Qwen3-14b-AWQ PTX toolchain error v0.16.0 | — | [#36235](https://github.com/vllm-project/vllm/issues/36235) | Upgrade driver |
| MemoryError loading AWQ/GPTQ v0.11.1+ | — | [#29762](https://github.com/vllm-project/vllm/issues/29762) | `parse_safetensors_file_metadata` regression |
| ModelOpt Llama-4 load > 5 min | — | [#31624](https://github.com/vllm-project/vllm/issues/31624) | Open |

## OOM / memory

| Symptom | Issue | Fix |
|---|---|---|
| GPU OOM processing AWQ Marlin with UVA offload | [#21864](https://github.com/vllm-project/vllm/issues/21864) | Disable UVA or load less aggressively |
| Gemma-4-31B-IT-NVFP4 OOM RTX 5090 | [#40291](https://github.com/vllm-project/vllm/issues/40291) | Open — suspect BF16 weights during init |
| Qwen3.5 INT4 memory > FP8 (unexpected) | [#37080](https://github.com/vllm-project/vllm/issues/37080) | Open |
| Gemma 4 31B INT4 KV only 25K tokens at 131K ctx | [#39133](https://github.com/vllm-project/vllm/issues/39133) | Use FP8 KV to fit more |
| Online FP8 drops bias → memory surprises | [#39663](https://github.com/vllm-project/vllm/issues/39663) | Use pre-quantized checkpoint |
| Online FP8 + MoE + TP/EP: single-GPU OOM | Qwen3-Next | [#34129](https://github.com/vllm-project/vllm/issues/34129) | Use pre-quantized checkpoint |

## CUDA errors

| Symptom | Issue | Fix |
|---|---|---|
| CUDA illegal memory access awq_marlin | [#32834](https://github.com/vllm-project/vllm/issues/32834) | Open; try `--enforce-eager` |
| CUDA graph replay triggers Xid 13 | Qwen3-32B-AWQ TP=2 | [#40121](https://github.com/vllm-project/vllm/issues/40121) | `--enforce-eager` |
| CUDA illegal instruction during NVFP4 decode | aarch64 GB10 DGX Spark | [#35519](https://github.com/vllm-project/vllm/issues/35519), [#39761](https://github.com/vllm-project/vllm/issues/39761) | Tracked [#37141](https://github.com/vllm-project/vllm/issues/37141) |
| CUDA illegal memory access GPTQ Marlin | [#36811](https://github.com/vllm-project/vllm/issues/36811) | Open |
| Hang mid-inference FP8 | Qwen3.5-35B-A3B-FP8 | [#36736](https://github.com/vllm-project/vllm/issues/36736) | Open |
| FlashInfer FP8 ScaledMM segfault SM100 | [#39814](https://github.com/vllm-project/vllm/issues/39814) | Pin to CUTLASS backend |

## Kernel / backend not dispatched

| Symptom | Issue | Fix |
|---|---|---|
| `No NvFp4 MoE backend supports the deployment configuration` | RTX 5090 (SM120) | [#35065](https://github.com/vllm-project/vllm/issues/35065) | SM120 gap [#31085](https://github.com/vllm-project/vllm/issues/31085); partial [PR #33417](https://github.com/vllm-project/vllm/pull/33417). Not production. |
| MXFP4 Marlin MoE fails K=N=2880 | GPT-OSS-20B | [#38022](https://github.com/vllm-project/vllm/issues/38022) | Open — not aligned for Marlin thread config |
| GPT-OSS-120b SM120 → kernel not dispatched | RTX Pro 6000 | [#34817](https://github.com/vllm-project/vllm/issues/34817) | SM120 gap |
| GLM-5 MXFP4 sparse MLA decode crash MI355x | [#38924](https://github.com/vllm-project/vllm/issues/38924) | Open |
| Triton MXFP4 MoE device capability `<(11,0)` breaks RDNA3.5 | [#40301](https://github.com/vllm-project/vllm/issues/40301) | Open |
| Misleading FP8 error about CUDA version | [#36805](https://github.com/vllm-project/vllm/issues/36805) | Error refers to wrong thing — check SM capability |
| Gemma 4 MoE 26B-A4B MXFP4 crash | [#39000](https://github.com/vllm-project/vllm/issues/39000) | Open |
| `CompressedTensorsWNA16MarlinMoEMethod` crash actorder=null AWQ MoE | [#35303](https://github.com/vllm-project/vllm/issues/35303) | Open |
| `CutlassW4A8LinearKernel` dim alignment DeepSeek-V3.1 W4AF8 (K=7168, N=2112) | [#33783](https://github.com/vllm-project/vllm/issues/33783) | Dims must be %128==0 |
| FP8 + FlashInfer on Llama-4 B200 | [#32488](https://github.com/vllm-project/vllm/issues/32488), [#32862](https://github.com/vllm-project/vllm/issues/32862) | Open |

## Performance regression

| Symptom | Issue | Fix |
|---|---|---|
| ~23 % output-throughput drop Qwen3.5-397B NVFP4 decode 8× B200 | [#39004](https://github.com/vllm-project/vllm/issues/39004) | Pin to last known-good nightly |
| FP8 speed regression 0.16.0rc2 | [#34377](https://github.com/vllm-project/vllm/issues/34377) | Upgrade |
| W4Afp8 slower than FP8-W8A8 | [#34212](https://github.com/vllm-project/vllm/issues/34212) | Open — format doesn't pay off |
| AWQ-Marlin long-input perf (closed 2026-03-04) | [#27956](https://github.com/vllm-project/vllm/issues/27956) | Upgrade |
| FP8 MoE backend regression Nemotron-3 v0.15.0/0.15.1 | [#34356](https://github.com/vllm-project/vllm/issues/34356) | Upgrade to v0.16+ |

## Quant config / checkpoint semantics

| Symptom | Issue | Fix |
|---|---|---|
| Online FP8 drops bias weights | [#39663](https://github.com/vllm-project/vllm/issues/39663) | Use pre-quantized checkpoint |
| Online FP8 doesn't split MoE across TP/EP | [#34129](https://github.com/vllm-project/vllm/issues/34129) | Use pre-quantized checkpoint |
| fp8_e5m2 KV gate fires on any quantized load | [#39137](https://github.com/vllm-project/vllm/issues/39137) | Patch in discussion |
| MLA casts activations to int32 with Marlin FP8 sm<89 | [#38658](https://github.com/vllm-project/vllm/issues/38658) | Upgrade or switch kernel |
| `runai_safetensors_weights_iterator` non-deterministic → FP8 broken | [#38991](https://github.com/vllm-project/vllm/issues/38991) | Use regular safetensors loader |
| MTP speculative decoding with NVFP4 weight shape mismatch | [#35031](https://github.com/vllm-project/vllm/issues/35031) | Open |

## Concurrent / multi-request

| Symptom | Issue | Fix |
|---|---|---|
| Qwen3.5-122B-A10B-FP8 EngineCore crash on concurrent image requests | [#37602](https://github.com/vllm-project/vllm/issues/37602) | Open |

## Decision pattern for common "my quantized model X is broken" cases

1. **First** — check vLLM version. Most production bugs fix within 2-3 minor releases. If < v0.19, upgrade.
2. **Second** — is the checkpoint from ModelOpt or llm-compressor? If ModelOpt NVFP4, cross-check `quantization_config.ignore` covers all non-linear layers and `_double_scale` keys are present.
3. **Third** — is it MLA + FP8 KV? If yes, avoid until [#38652](https://github.com/vllm-project/vllm/issues/38652) resolved.
4. **Fourth** — is it Gemma 4? If yes, avoid FP8 entirely.
5. **Fifth** — is the GPU SM120/SM121? If yes, expect kernel gaps; try `fp8` only.
6. **Sixth** — if on B300/GB300 and v0.18 or older, upgrade to v0.19+ immediately.
7. **Seventh** — if online-quantized, check bias / MoE gotchas. Switch to pre-quantized.
8. **Eighth** — `--enforce-eager` isolates CUDA-graph bugs from dispatch bugs.

## Useful diagnostics

```bash
# Check effective kernel dispatch
VLLM_LOGGING_LEVEL=DEBUG vllm serve ... 2>&1 | grep -E "(kernel|dispatch|capability)"

# Force specific MoE backend
VLLM_FUSED_MOE_CHUNK_SIZE=...  # tune
VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8=1  # GPT-OSS Blackwell

# Disable CUDA graphs to isolate
--enforce-eager

# Examine config.json quantization_config
python -c 'import json; print(json.dumps(json.load(open("config.json"))["quantization_config"], indent=2))'
```
