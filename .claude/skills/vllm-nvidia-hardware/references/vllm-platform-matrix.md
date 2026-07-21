# vLLM on NVIDIA — attention backends, quantization, KV connectors, Blackwell readiness

Repo paths below reference the vLLM checkout. Cross-check against the running vLLM
version; the support matrix changes materially between point releases.

## 1. Attention backend × SM compatibility

Backends gate on `DeviceCapability` in `vllm/v1/attention/backends/`:

| Backend | Hopper (sm_90) | Blackwell (sm_100/103) | Notes |
|---|---|---|---|
| `FLASH_ATTN` (FA2/FA3) | ✅ | ✅ | CC ≥ 8.0; FA3 for ViT added v0.11 |
| `FLASH_ATTN_MLA` | ✅ | ❌ | `capability.major == 9` (`flashattn_mla.py:68-69`) |
| `FLASHINFER` | ✅ | ✅ | CC 7.5–12.1; FlashInfer 0.3.1+ default v0.11 |
| `FLASHINFER_MLA` (dense) | ❌ | ✅ | Blackwell-only (`flashinfer_mla.py:65-70`) |
| `FLASHINFER_MLA_SPARSE` (DeepSeek V3.2) | ❌ | ✅ | Blackwell-only; default for FP8 KV cache v0.19 (#37252) |
| `FLASHMLA` (dense & sparse) | ✅ | ✅ | `capability.major in [9, 10]`; disabled on Blackwell in v0.10.2 (#24521), restored |
| `CUTLASS_MLA` | ❌ | ✅ | `sm100_cutlass_mla_decode`; FP8 MLA (#23289, v0.10.2) |
| `TRTLLM attention` | ❌ | ✅ | SM100 and SM103; **SM103 (GB300) previously hung with FlashInfer 0.6.7 (regression vs 0.6.6)** — **fixed 2026-04-07** via flashinfer-ai/flashinfer#2956 (a *revert* of the Blackwell-Ultra optimization that caused the deadlock; closes #2939), shipped in 0.6.7.postN. If stuck on plain 0.6.7, disable TRTLLM on SM103 or upgrade. |
| `TRITON_ATTN` / `FLEX_ATTENTION` / `TREE_ATTN` | ✅ | ✅ | Generic |
| `xformers` | removed v0.11 | removed | V0 deprecation |

## 2. Quantization support

- **FP8** (`fp8.py`): CC ≥ 8.9 (Ada, Hopper, Blackwell). Per-tensor/block/channel
  flavors. Hardware-accelerated FP8 in v0.11 (#24757). FP8 MLA via CUTLASS on SM100
  (#23289).
- **NVFP4 / MXFP4** (`modelopt.py`, `mxfp4.py`): ModelOpt checkpoints native.
  `FLASHINFER_TRTLLM_MXFP4_MXFP8` backend SM100-only. CUTLASS MoE NVFP4 for SM120
  (v0.12, #29242). Default MXFP4 MoE on Blackwell since v0.10.2 (#23008). NVFP4
  dense in v0.11 (#25609).
- **MXFP8**: compressed-tensors MoE + W8A8 online quantization in v0.19 (#35448).
- **QuTLASS**: new quant method added v0.11.1.

## 3. KV connectors (all in `vllm/distributed/kv_transfer/kv_connector/v1/`)

| Connector | Status | Key flag / note |
|---|---|---|
| Native CPU weight offload | Production | `--cpu-offload-gb` |
| Native KV offload | Production | `--kv-offloading-size <GiB>` + `--kv-offloading-backend {native,lmcache}`. **Flag is total across TP ranks** (opposite of SGLang convention) |
| `LMCacheConnector` / `LMCacheMPConnector` | Production | CPU + NVMe + GDS tiering |
| `NixlConnector` | Beta / early-production | UCX/NIXL disagg; heavy dev v0.10.2–v0.19 |
| `MooncakeConnector` | 🧪 Limited | **No pipeline parallelism** (`mooncake_connector.py:704`); heterogeneous TP added v0.19 (#36869) |
| `MultiConnector` | Production | Composition |
| `hf3fs`, `moriio`, `p2p`, `flexkv`, `offloading`, `simple_cpu_offload` | Varies | Specialized transports |

## 4. Speculative decoding — platform angle only

Full method catalogue, config, metrics, and per-method pitfalls: see the
`vllm-speculative-decoding` skill. Hardware-relevant notes only here:

- **Decode is memory-bandwidth-bound** (AI ≈ 1). Spec-dec amortises BW by
  verifying k tokens per target forward — ROI grows the more BW-bound decode
  is. FP4 on Blackwell pushes AI lower still, enlarging spec-dec's upside:
  3–4× routine on B200/B300, typically +30–80% on Hopper.
- **DFlash requires FlashAttention backend** (v0.19 path). Triton/FlashInfer-
  TRTLLM can't serve the non-causal cross-attention head. Affects backend
  selection on SM100/SM103.
- **EAGLE-3 / DFlash target-model allow-list** in
  `config/speculative.py:818-833`: llama, qwen, minicpm, gpt_oss, hunyuan_vl,
  hunyuan_v1_dense, afmoe, nemotron_h, deepseek_v2/v3, kimi_k2/k25,
  minimax_m2, gemma4.
- **BS ≥ 32 regime**: target becomes compute-bound, spec-dec hurts. On
  Blackwell with FP4 weights + FP8 KV this BS shifts down compared to Hopper
  (higher compute-per-BW ratio) — verify the break-even for your hardware.

## 5. Blackwell readiness

- **CUDA 13 support** landed in v0.11 (#24599); v0.12 on PyTorch 2.9.0 / CUDA 12.9;
  v0.19 ships `cu130` wheels.
- **For B300/GB300: CUDA 13 recommended**, `torch_cuda_arch_list='9.0 10.0+PTX'`
  (`docs/getting_started/installation/gpu.cuda.inc.md:372-388`).
- **SM100 (B200)** broadly supported; **SM103 (GB300)** was recognized with known hang
  in TRTLLM/FlashInfer 0.6.7 — **fixed 2026-04-07** via flashinfer-ai/flashinfer#2956,
  which *reverts* the Blackwell-Ultra optimization that introduced the deadlock
  (closes #2939), shipped in 0.6.7.postN. **This is now history for anyone on a
  current vLLM**: v0.22.0 ships FlashInfer 0.6.11.post2, v0.23.0 ships 0.6.12,
  v0.25.0 ships 0.6.13 — all far past the fix. It only bites a deployment that
  pins FlashInfer independently of vLLM. If pinned to plain 0.6.7 without the post
  fix, disable TRTLLM on SM103 (`--attention-config.use_trtllm_attention=0`); 0.6.6
  works, and the FlashInfer default backend on SM103 actually benchmarks faster than
  the old 0.6.6 TRTLLM path (~56 vs ~35 req/s in the upstream repro).
- **SM120 (RTX PRO 6000 desktop Blackwell):** specific CUTLASS optimizations (v0.19
  #37970), NVFP4 NaN fix (#37725).
- **Non-CDMM Grace-Blackwell NUMA handling:** `platforms/cuda.py:677-686` — each
  GPU's HBM is a separate NUMA node with no CPUs.

## 6. Release-note highlights (what shipped for Blackwell)

- **v0.10.2** (Sep 2025) — aarch64 + GB200; FP8 MLA CUTLASS (SM100); MXFP4 fused
  CUTLASS MoE; default MXFP4 MoE on Blackwell; FP8-qkv TRTLLM.
- **v0.11.0** (Oct 2025) — V0 fully removed; CUDA graph FULL_AND_PIECEWISE default;
  NVFP4 dense; FP8 FlashInfer MLA decode; BF16 fused MoE EP (Hopper/Blackwell);
  FlashInfer 0.3.1; CUDA 13; NCCL symmetric memory default.
- **v0.11.1** (Nov 2025) — Batch-invariant torch.compile (DeepGEMM+FlashInfer);
  EAGLE-3 +32% over EAGLE-1 on MT-Bench; QuTLASS; mixed MXFP6-MXFP4; TRTLLM MLA
  prefill accuracy.
- **v0.12.0** (Dec 2025) — GPU Model Runner V2 (experimental); +18.1% throughput
  from batch-invariant BMM; Prefill Context Parallel (PCP) preparatory; NVFP4 MoE
  CUTLASS SM120; TRTLLM MoE NVFP4.
- **v0.19.0** (Apr 2026) — **B300/GB300 (SM 10.3) first-class support**, allreduce
  fusion default, tuned all-reduce communicator (#37755/37756); SM120 CUTLASS
  blockwise FP8 GEMM; FlashInfer sparse MLA default for FP8 KV cache; Gemma 4;
  zero-bubble async + spec decode; general CPU KV offloading for V1 (#37160, #37874,
  #34805).
- **v0.20.0** (Apr 2026, GA 04-27) — **CUDA 13.0 default** (breaking env change),
  PyTorch 2.11, **FlashAttention 4 as default MLA prefill** (SM90+ paged-KV),
  TurboQuant 2-bit KV cache, MXFP4 W4A4 CUTLASS MoE on SM100.
- **v0.22.0** (May 2026) — FlashInfer b12x MoE + FP4 GEMM for **SM120/121**
  (#40082), per-tensor FP8 CUTLASS on SM12.1 (#41215), GDN prefill kernel for
  SM100 (#43273), `head_dim=512` for FlashInfer TRTLLM attention (#38822).
  FlashInfer bumped to **0.6.11.post2** (#41711).
- **v0.23.0** (Jun 2026) — **Triton MoE backend becomes the default on Hopper**
  (#44220) — a default change that silently alters the H100/H200 MoE path, so
  benchmark before and after this version. Also: CUTLASS FP8 scaled-mm padding
  bypass (+20%, #43706), tuned `selective_state_update` for **H200/RTX PRO**
  (#44251), **NUMA auto-binding on DGX B300** (#43270), Marlin MoE on SM 12.x
  (#40923), and **fail-fast on an unsupported NVFP4 KV-cache-dtype arch**
  (#43669) instead of failing obscurely later. FlashInfer **0.6.12** (#44036).
- **v0.24.0** (Jun 2026) — SM90 CUTLASS FP8 mm odd-M via `swap_ab`
  (**180–290% kernel speedup**, #44572), tuned `fused_moe` FP8 for
  Qwen3-Next-80B on H100 (+25%, #44830), native DSA indexer decode on SM100
  (#45322), FP8 MoE re-enabled on **NVIDIA Thor** (#46339). **vLLM stopped
  setting `CUDA_VISIBLE_DEVICES` internally** — use the new `device_ids`
  argument (#45026); ROCm began a deprecation window for the old behaviour
  (#46636).
- **v0.25.0** (Jul 2026) — **PagedAttention removed entirely** (#47361);
  Model Runner V2 default for all dense models (#44443). Blackwell:
  FlashInfer fused all-reduce tuned for **world_size=16 on GB300** (#46392),
  restored NVFP4 swizzled-scale zero-init to recover Blackwell decode
  throughput (#45739), skip cooperative top-K on SM120 (#47164).
  FlashInfer **0.6.13** (#46683).
- **v0.25.1** (2026-07-14) — see the NVFP4 corruption fix below. Patch release,
  and the reason not to sit on v0.25.0.

### ⚠ v0.25.0 corrupts output on some NVFP4 models — fixed in v0.25.1

**PR #48330 (merged 2026-07-12), fixing issue #48324.** The fused FlashInfer
**allreduce + RMSNorm + static-quantization** patterns could match graphs where
the activation and the RMSNorm weight have *different dtypes*. Gemma/Qwen-style
RMSNorm computes `weight.float() + 1.0`, so the effective weight is FP32 while
the residual stream is BF16. Selecting the fused quantized op for that graph
**corrupts the hidden state** and emits repeated tokens — the reported symptom
is a stream of `!!!!!!!!!!!!`.

- **Reproducer named upstream:** `nvidia/Qwen3.6-27B-NVFP4`.
- **Exposure:** NVFP4 model + Gemma/Qwen-style RMSNorm + allreduce fusion
  (which has been *default* since v0.19.0) — i.e. a Blackwell multi-GPU serve.
- **Nature:** silent wrong output, not a crash. No error, no metric moves;
  only the generated text is garbage. Nothing in the logs points at the fusion.
- **Fix:** the `_norm_input_weight_dtype_match` compatibility check is now
  applied to `AllReduceFusedAddRMSNormStaticQuantFP8Pattern` and
  `...NVFP4Pattern`; incompatible graphs fall back to fused allreduce + Gemma
  RMSNorm with `weight_bias=1.0` plus separate quantization. Same-dtype models
  keep the full fusion, so there is no throughput cost for the unaffected case.
- **Action:** on Blackwell + NVFP4, run **≥ v0.25.1**. If pinned to v0.25.0,
  disabling allreduce fusion is the workaround.

### Rubin (R100 / Vera Rubin NVL72) has no vLLM support yet

As of **v0.25.1** there is **no Rubin code path in vLLM**: the issue tracker
returns zero results for "Rubin", and the build scripts target only
`sm_90 / sm_100 / sm_103 / sm_110 / sm_120 / sm_121`. Hardware availability
and engine support are on different clocks — see `references/rubin-roadmap.md`
before assuming a Rubin rack can serve on day one.

**`sm_110` is Thor, not Rubin.** vLLM's own build comments place `sm_110`
in the Blackwell/Thor family alongside `sm_100`/`sm_103`
(`.buildkite/image_build/image_build_arm64.sh`,
`csrc/libtorch_stable/launch_bounds_utils.h`). Don't read a Rubin target into it.

**Thor + CUDA 13 + Triton gotcha.** `ptxas fatal: Value 'sm_110a' is not
defined for option 'gpu-name'` means the ptxas bundled with Triton predates
the device. It surfaces as `EngineDeadError`, which looks like an engine bug
rather than a toolchain mismatch. Fix: point `TRITON_PTXAS_PATH` at the CUDA
toolkit's own ptxas. Documented in `docs/usage/troubleshooting.md`.

## 7. NVL72 handling in vLLM

- No hardcoded 72-GPU logic; NVLink detected generically via NVML p2p
  (`platforms/cuda.py:637-659`).
- Communicator layer has FlashInfer NVLink one-/two-sided all-reduce
  (`fused_moe/prepare_finalize/flashinfer_nvlink_*.py`) and NCCL symmetric memory
  default TP (v0.11 #24532, #25070, +3–4% throughput).
- Scale-out pattern: **large DP/EP engine + NixlConnector/Mooncake for cross-node
  P/D disagg**, not a single 72-way TP. EPLB (Expert Parallel Load Balancer) matured
  v0.11–v0.19; Elastic EP (dynamic scale up/down) in v0.19 (#37131).
- **PCP/DCP (Prefill/Decode Context Parallel)** + **DBO (Dual-Batch Overlap)**
  framework being built out; see `docs/serving/expert_parallel_deployment.md`.

## Sources

[vLLM v0.10.2](https://github.com/vllm-project/vllm/releases/tag/v0.10.2) ·
[vLLM v0.11.0](https://github.com/vllm-project/vllm/releases/tag/v0.11.0) ·
[vLLM v0.11.1](https://github.com/vllm-project/vllm/releases/tag/v0.11.1) ·
[vLLM v0.12.0](https://github.com/vllm-project/vllm/releases/tag/v0.12.0) ·
[vLLM v0.19.0](https://github.com/vllm-project/vllm/releases/tag/v0.19.0) ·
[NVIDIA vLLM release notes 25.09](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/rel-25-09.html).
