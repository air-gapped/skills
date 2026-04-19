---
name: vllm-nvidia-hardware
description: NVIDIA AI-hardware + vLLM-platform reference covering Hopper (H100/H200), Blackwell (B100/B200/B300) and Blackwell Ultra, Grace-Blackwell superchips and NVL72 racks (GB200, GB300), Vera Rubin (R100/R300) with VR200 NVL144 and Kyber NVL576, Dell PowerEdge XE family (XE8640/9640/9680/9680L/9685L/9780/9780L/9785L/9712/8712/7740/7745), and Dell IR5000/IR7000/IR9048 racks. Per-SKU HBM, FP4/FP8/FP16 TFLOPs, NVLink5, TDP. Rack power/cooling (135 kW GB300, 180–220 kW NVL144, 600 kW Kyber), DLC vs RDHx, 800 VDC HVDC roadmap. Memory-wall roofline reasoning (AI≈1 decode, BW-vs-FLOPs gap, HBM3E→HBM4, HBM supply 2026). vLLM attention-backend × SM matrix, FP4 (NVFP4/MXFP4) and FP8 paths, KV connectors (Nixl, Mooncake, LMCache), Blackwell gotchas (SM103 TRTLLM hang, 270 vs 288 GB B300 bin split).
when_to_use: Use this skill for any NVIDIA-AI hardware sizing, procurement, facility, or vLLM-deployment question. Triggers include HBM capacity/bandwidth, TDP, NVLink, GB300 NVL72 power/cooling, Vera Rubin timing, Dell PowerEdge XE, IR7000 racks, ORv3 power shelves, DLC flow rate, warm-water 45 °C, 800 VDC HVDC, rack weight, floor load, HBM supply 2026, FlashAttention/FlashInfer/FlashMLA/CUTLASS MLA/TRTLLM per SM, NVFP4, MXFP4, NixlConnector, MooncakeConnector, LMCache, CUDA 13 arch list, SM100/SM103/SM120 gotchas, memory-wall roofline, prefill-vs-decode. Apply even when phrased narrowly (e.g. "HBM on our XE9780", "wait for Rubin"); bin split, platform gotchas, and facility constraints matter.
---

# vLLM on NVIDIA hardware — Hopper through Rubin

Target audience: operators who run vLLM on NVIDIA datacenter GPUs, sizing from single H100 nodes up to GB300 NVL72 racks, and evaluating Vera Rubin for 2026–2027 purchases.

This skill is a **reference**, not a walkthrough — most of the content is SKU tables, facility prerequisites, and platform compatibility matrices. The SKILL.md body holds the quick-answer shortcuts; the `references/` directory has the full tables. Read the reference file that matches the question.

## The one thing to know before anything else

LLM inference has two phases with radically different bottlenecks:

- **Prefill** is compute-bound (GEMMs, AI ≫ ridge point) — more FLOPs help.
- **Decode** is memory-bandwidth-bound (AI ≈ 1, 100× below the ridge) — more HBM bandwidth helps, more FLOPs don't.

Every hardware decision — FP4 vs FP8, B300's higher FLOPs with the same 8 TB/s, NVL72's domain collapse, Rubin's HBM4 jump to ~20 TB/s — is about relieving the memory wall on decode while keeping prefill healthy. Read `references/fundamentals.md` for the roofline math and the HBM roadmap context that makes the rest of the tables meaningful.

## Quick-answer router

**Hardware specs** ("what's the HBM on X?", "TDP of Y?")
- NVIDIA GPU SKUs (Hopper, Blackwell, Blackwell Ultra) → `references/gpu-specs.md`
- Vera Rubin roadmap (R100, Rubin Ultra, NVL144, Kyber NVL576) → `references/rubin-roadmap.md`
- Dell PowerEdge XE servers → `references/dell-xe.md`
- GB300 NVL72 vendor landscape + facility prereqs → `references/nvl72-procurement.md`

**Memory-wall reasoning** ("why does FP4 help?", "why NVL72?")
- Fundamentals (roofline, BW/FLOPs gap, HBM roadmap, supply, energy) → `references/fundamentals.md`
- Mitigations × platform matrix (what works on Hopper vs Blackwell) → `references/mitigations.md`

**vLLM on NVIDIA** ("what backend on SM100?", "FlashMLA on Blackwell?")
- Attention backend × SM matrix, quant, KV connectors, known gotchas, release-note highlights → `references/vllm-platform-matrix.md`
- GEMM backends (DeepGEMM vs CUTLASS, FP8 alignment, E8M0 scaling, JIT cache) → `references/gemm-backends.md`

## The five most common operator mistakes this skill exists to prevent

1. **Conflating the two B300 bins.** NVIDIA ships B300 in two bins: **DGX / GB300 Superchip = 288 GB HBM3E / 1,400 W**, and **HGX B300 NVL8 SXM6 (OEM baseboards) = 270 GB / 1,100 W**. Dell PowerEdge XE9780/XE9780L/XE9780LAP/XE9785/XE9785L all carry the **HGX NVL8 bin** (270 GB / 1,100 W). Getting this wrong puts the 8-GPU TDP budget off by 2.4 kW and the per-GPU HBM off by 18 GB. `references/gpu-specs.md` §2.2 has both rows.

2. **Assuming B300 is HBM4.** It isn't. B300 uses HBM3E (12-Hi stacks, 288 GB at the top bin). HBM4 first ships in **Vera Rubin R100** (H2 2026) with ~20 TB/s per GPU. This matters for roadmap planning.

3. **Assuming GB300 NVL72 can use rear-door heat exchangers.** It can't — at 135 kW nominal / 155 kW peak per rack, direct liquid cooling is mandatory on GPUs + CPUs + NVSwitch + CX-8 NICs. Facility work (row-level CDU, 3φ 480V feeds, 1500 kg/m² floor) routinely takes 6–9 months. See `references/nvl72-procurement.md`.

4. **Confusing Dell's "XE9780 (air)" with "XE9780L (liquid)".** They are separate SKUs in the same spec sheet. Also note that **XE9680L in Dell's 2026 portfolio is a 4U B200 liquid-cooled node**, not a liquid-cooled variant of the 6U XE9680 H100/H200 chassis. `references/dell-xe.md` has the name disambiguation.

5. **Running TRTLLM attention on GB300 with recent FlashInfer.** SM103 (GB300) **hangs** with FlashInfer ≥ 0.6.7 — upstream bug (flashinfer-ai/flashinfer#2939). Workaround: use non-TRTLLM backend on SM103 or pin an older FlashInfer until fixed. `references/vllm-platform-matrix.md` has this and other Blackwell readiness notes.

## Operator cheat sheet

### Running vLLM on Hopper (H100/H200)
- Default to FP8 weights + FP8 KV cache on H200 for long context.
- Use FlashMLA for DeepSeek models; FlashAttention-3 elsewhere.
- Disagg prefill across nodes needs XDR IB + GPUDirect-RDMA — use CPU/NVMe offload (LMCache) first.
- **No FP4. No NVL72. No 288 GB single-GPU.**

### Running vLLM on Blackwell (B200/B300)
- Switch to FP4 (NVFP4 via ModelOpt checkpoints) — 1.8–2× decode throughput on the same HBM budget.
- NVL72 collapses disagg cost — keep prefill/decode inside one NVLink5 domain; use `NixlConnector`.
- Pin vLLM **≥ v0.19** for first-class B300/GB300 (SM 10.3) support.
- 270 GB (HGX bin) or 288 GB (DGX bin) HBM per B300 often removes the *need* for KV offload on 70B-scale models. LMCache still earns its keep for 1M+ context and heavy prefix reuse.

### Buying NVIDIA hardware in 2026
- **GB300 NVL72 is safe for 2026 capacity:** size the row for 135–155 kW, DLC @ 25 °C, 3φ 480 V. Vendors: NVIDIA DGX B300, Dell IR7000 + XE9780L / XE8712 sleds, Supermicro SRS-GB300-NVL72, Lenovo 7DJVCTO2WW, HPE.
- **Greenfield rows should be spec'd for Rubin NVL144:** 180–220 kW, 45 °C W45 warm water, 800 VDC HVDC, new MGX rack. Retrofitting later is expensive.
- **Expect HBM allocation and PSU rectifier shelf lead times to dominate schedule risk.** SK hynix / Micron / Samsung HBM sold out through CY26.

### Key numbers to memorize
| Metric | Value |
|---|---|
| GB300 NVL72 rack power | 135 kW nominal / 155 kW peak |
| GB300 NVL72 aggregate HBM | 20.7 TB HBM3E |
| GB300 NVL72 aggregate HBM BW | ~576 TB/s |
| GB300 NVL72 NVLink domain | 72 GPUs flat, 130 TB/s |
| B300 (HGX NVL8, Dell fleet) | 270 GB / 1,100 W |
| B300 (DGX / GB300 Superchip) | 288 GB / 1,400 W |
| H200 SXM5 | 141 GB HBM3E / 4.8 TB/s / 700 W |
| Rubin R100 (H2 2026) | ~288 GB HBM4 / ~20 TB/s |
| Rubin NVL144 rack power | 180–220 kW (800 VDC HVDC) |
| Rubin Ultra Kyber NVL576 rack | 600 kW |

## Paired reference

If this skill helps with *why* a hardware choice matters for KV-cache sizing, the companion skill `vllm-caching` covers *how* to configure tiered KV (`--kv-offloading-size`, LMCache, NixlConnector, MooncakeConnector). Both skills should trigger together on combined "we're buying GB300 and need to size LMCache" style questions.

## Source and refresh policy

All claims in the references are sourced inline — **prefer NVIDIA first-party datasheets, SemiAnalysis, Dell/Lenovo/Supermicro OEM datasheets**, then reputable news. When numbers disagree across sources, the references report the range with each citation. The full consolidated source list is in `references/sources.md`.

This skill was compiled from `MEMORY_WALL_DEEP.md` (late-2025/early-2026 research pass); refresh when new NVIDIA products launch or when HBM / rack-power / vLLM backend landscape shifts materially.
