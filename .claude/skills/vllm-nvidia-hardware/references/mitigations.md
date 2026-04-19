# Memory-wall mitigations — matrix by layer and platform

How each technique relieves which bottleneck, and which platform it runs on.
Legend: ✅ supported / 🆕 Blackwell-only / 🧪 experimental / ❌ not supported.

## Model-level

| Mitigation | Hopper | Blackwell | Leverages | Notes |
|---|---|---|---|---|
| **FP8** (E4M3/E5M2) | ✅ | ✅ | HBM BW + compute (2× vs FP16) | Default for DeepSeek-V3, Llama-3.1-405B serving; TE 1 on Hopper, TE 2 on Blackwell |
| **FP4** (NVFP4 / MXFP4) | ❌ | 🆕 ✅ | HBM BW (2× vs FP8) + compute | Shipping in production via TensorRT-LLM mid-2025; in vLLM via ModelOpt checkpoints |
| **Weight-only INT4** (AWQ / GPTQ) | ✅ | ✅ | HBM BW + capacity | Declining relevance on Blackwell because FP4 subsumes it |
| **MLA** (Multi-head Latent Attention) | ✅ | ✅ | KV capacity (~10× shrink) + decode BW | DeepSeek-V2/V3/R1 only; not retrofittable without retrain |
| **GQA** | ✅ | ✅ | Decode BW (4–8× KV head shrink) | Baseline in every model since Llama-2-70B |
| **Sliding-window attention** | ✅ | ✅ | KV capacity (bounded by window) | Hurts long-context retrieval unless paired with a global layer (Gemma-2/3 pattern) |
| **SSM / Mamba / hybrid** | ✅ | ✅ | KV capacity (constant state) + long-context BW | Hybrids winning (Nemotron-H, Granite-4 hybrid, Jamba-1.5); pure-Mamba stalled <70B |

## Serving-level (vLLM-relevant)

| Mitigation | Hopper | Blackwell | Status | Notes |
|---|---|---|---|---|
| **Paged KV cache** | ✅ | ✅ | Production | vLLM's founding contribution (SOSP 2023) |
| **Prefix caching** | ✅ | ✅ | Production, default in vLLM V1 | Wins on multi-turn / RAG / agent loops; neutral on stateless |
| **Chunked prefill** | ✅ | ✅ | Production, default V1 | Required to keep TPOT P99 sane with long prefills |
| **Speculative decoding** | ✅ | ✅✅ | Production | Full method catalogue + config in the `vllm-speculative-decoding` skill. Bigger win on Blackwell: FP4 makes decode more BW-bound so spec-dec ROI is higher |
| **Disaggregated prefill (NixlConnector)** | ✅ | ✅✅ | Beta/early-production | NVL72 collapses the cross-fabric cost; on Hopper needs XDR IB + GPUDirect-RDMA |
| **Disaggregated prefill (MooncakeConnector)** | ✅ | ✅ | 🧪 Limited (no PP) | Used at Moonshot Kimi scale |
| **CPU KV offload (native)** | ✅ | ✅ | Production | `--kv-offloading-size` / `--cpu-offload-gb` |
| **LMCache (CPU + NVMe + GDS)** | ✅ | ✅ | Production | Heaviest deployed option; 3FS/hf3fs connector for distributed KV |
| **FP8 KV cache** | ✅ | ✅ | Production | `--kv-cache-dtype fp8` |
| **FP4 KV cache** | ❌ | 🆕 🧪 | Early-production | Up to 3× TTFT in long-context prefill-heavy |
| **Algorithmic KV eviction** (H2O, StreamingLLM, SnapKV, PyramidKV) | ✅ | ✅ | Research | Correctness on long agentic traces hard to bound |

## System-level

| Mitigation | Hopper | Blackwell | Status | Notes |
|---|---|---|---|---|
| **NVLink4 (900 GB/s)** | ✅ | n/a | Production | 8-GPU island cap |
| **NVLink5 (1.8 TB/s, NVL72 domain)** | ❌ | 🆕 ✅ | Production | Collapses cross-fabric KV transfer into intra-domain |
| **InfiniBand NDR (400 Gb/s)** | ✅ | ✅ | Production | Inter-rack fabric |
| **InfiniBand XDR (800 Gb/s) + GPUDirect-RDMA** | ✅ | ✅ | Shipping 2025 | Minimum for cross-rack disagg |
| **Grace-Hopper / Grace-Blackwell NVLink-C2C (900 GB/s)** | GH200 | GB200/GB300 | Production | Makes CPU offload nearly HBM-equivalent for large-batch reuse |
| **CXL memory tiering** | host-only | host-only | 🧪 research / early pilot | Samsung/SK Hynix modules exist; Meta CMM-B, MS Pond piloting CPU-side; **not for GPU KV in 2026**. NVLink-C2C won this slot instead |
| **800 VDC HVDC rack power** | ❌ | ❌ (GB300=48/54 VDC) | Rubin-era | Arrives with VR200 NVL144 |

## Newly viable or attractive on Blackwell Ultra

- **FP4 as default**, not research — 2× BW relief on decode that Hopper literally can't run.
- **NVL72-scoped disagg** — prefill/decode pool fits one NVLink5 domain; ~20× faster
  KV transfer than cross-fabric IB.
- **288 GB HBM per GPU (B300/GB300 DGX bin; 270 GB on Dell HGX bin)** — a 405B FP4
  model (~200 GB) fits on one GB300 with room for KV; a 70B FP4 at 2M-context fits
  without any offload. Changes the "do I even need offload?" calculus.
- **NVLink-C2C + 270–288 GB HBM** — when offload *is* needed (1M+ context, heavy
  prefix reuse), the Grace side is a genuine fast tier at 900 GB/s, not a slow fallback.
- **Speculative decoding ROI grows** — the more memory-bound decode becomes, the bigger
  the acceptance-rate-amortised win; 3–4× routine on Blackwell. Method-pick guidance
  in `vllm-speculative-decoding`.

Sources:
[DeepSeek-V2 MLA](https://arxiv.org/abs/2405.04434) ·
[DeepSeek-V3](https://arxiv.org/abs/2412.19437) ·
[EAGLE-3](https://arxiv.org/abs/2503.01840) ·
[Mooncake (FAST 2025)](https://arxiv.org/abs/2407.00079) ·
[vLLM paged attention (SOSP 2023)](https://arxiv.org/abs/2309.06180) ·
[AWQ (MLSys 2024)](https://arxiv.org/abs/2306.00978) ·
[NVIDIA NVFP4 blog](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/).
