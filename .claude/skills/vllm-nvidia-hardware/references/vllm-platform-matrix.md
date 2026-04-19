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
| `TRTLLM attention` | ❌ | ✅ | SM100 only; **SM103 (GB300) hangs with FlashInfer ≥ 0.6.7** — open (flashinfer-ai/flashinfer#2939) |
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
- **SM100 (B200)** broadly supported; **SM103 (GB300)** recognized with known hang
  in TRTLLM/FlashInfer ≥ 0.6.7. Workaround: avoid TRTLLM on SM103 or pin older
  FlashInfer until flashinfer-ai#2939 is fixed.
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
