---
name: vllm-nvidia-hardware
description: |-
  NVIDIA AI-hardware + vLLM-platform reference covering Hopper (H100/H200), Blackwell (B100/B200/B300) and Blackwell Ultra, Grace-Blackwell superchips and NVL72 racks (GB200, GB300), Vera Rubin (R100/R300) with VR200 NVL144 and Kyber NVL576, Dell PowerEdge XE family and IR5000/IR7000/IR9048 racks. Per-SKU HBM, FP4/FP8/FP16 TFLOPs, NVLink5, TDP, rack power/cooling (135 kW GB300, 180-220 kW NVL144, 600 kW Kyber), DLC vs RDHx, 800 VDC HVDC. Memory-wall roofline, HBM3E→HBM4 supply 2026. vLLM attention-backend × SM matrix, FP4/FP8 paths, KV connectors, Blackwell gotchas (SM103 TRTLLM hang, 270 vs 279 GB B300 bin split).
when_to_use: |-
  Trigger on NVIDIA-AI hardware sizing, procurement, facility, or vLLM-deployment questions. Triggers — HBM capacity/bandwidth, TDP, NVLink, GB300 NVL72 power/cooling, Vera Rubin timing, Dell PowerEdge XE, IR7000 racks, ORv3 power shelves, DLC flow rate, warm-water 45 °C, 800 VDC HVDC, rack weight, floor load, HBM supply 2026, FlashAttention/FlashInfer/FlashMLA/CUTLASS MLA/TRTLLM per SM, NVFP4, MXFP4, NixlConnector, MooncakeConnector, LMCache, CUDA 13 arch list, SM100/SM103/SM120 gotchas, memory-wall roofline, prefill-vs-decode. Narrow phrasings — "HBM on our XE9780", "wait for Rubin", "which GPU for {model}", "B200 vs H200 choice". Also implicit — "sizing for {model}", "audit GPU hardware for a vLLM deploy", "rack power budget", "can this GPU run {model}", "GPU recommendation", "deploy-memo hardware", "spec-study hardware".
---

# vLLM on NVIDIA hardware — Hopper through Rubin

Answer from the shortcuts below; for full tables, read the one reference file the router names for the question.

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

1. **Conflating the two B300 bins.** NVIDIA ships B300 in two bins: **DGX / GB300 Superchip = 279 GB HBM3E / 8 TB/s / 1,400 W** (launch coverage says 288 GB; size against the datasheet's 279), and **HGX B300 NVL8 SXM6 (OEM baseboards) = 270 GB / 7.7 TB/s / 1,100 W**. Dell PowerEdge XE9780/XE9780L/XE9780LAP/XE9785/XE9785L all carry the **HGX NVL8 bin** (270 GB / 1,100 W). Getting this wrong puts the 8-GPU TDP budget off by 2.4 kW and the per-GPU HBM off by 9 GB. `references/gpu-specs.md` §2 has both rows.

2. **Assuming B300 is HBM4.** It isn't. B300 uses HBM3E (12-Hi stacks, 279 GB at the top bin). HBM4 first ships in **Vera Rubin R100** (H2 2026) with ~20 TB/s per GPU. This matters for roadmap planning.

3. **Assuming GB300 NVL72 can use rear-door heat exchangers.** It can't — at 135 kW nominal / 155 kW peak per rack, direct liquid cooling is mandatory on GPUs + CPUs + NVSwitch + CX-8 NICs. Facility work (row-level CDU, 3φ 480V feeds, 1500 kg/m² floor) routinely takes 6–9 months. See `references/nvl72-procurement.md`.

4. **Confusing Dell's "XE9780 (air)" with "XE9780L (liquid)".** They are separate SKUs in the same spec sheet. Also note that **XE9680L in Dell's 2026 portfolio is a 4U B200 liquid-cooled node**, not a liquid-cooled variant of the 6U XE9680 H100/H200 chassis. `references/dell-xe.md` has the name disambiguation.

5. **Running TRTLLM attention on GB300 with FlashInfer pinned to 0.6.7 / 0.6.7.post1 independently of vLLM.** SM103 hangs there (regression vs 0.6.6, flashinfer-ai/flashinfer#2939); fixed in **0.6.7.post2** (#2956). vLLM's own pins are far past it, so this bites only on a separate FlashInfer pin: upgrade it, or disable TRTLLM on SM103 (the FlashInfer default backend is faster there). `references/vllm-platform-matrix.md` §5 has this and other Blackwell readiness notes.

## Operator cheat sheet

### Running vLLM on Hopper (H100/H200)
- Default to FP8 weights + FP8 KV cache on H200 for long context.
- Use FlashMLA for DeepSeek models; FlashAttention-3 elsewhere.
- Disagg prefill across nodes needs XDR IB + GPUDirect-RDMA — use CPU/NVMe offload (LMCache) first.
- **No FP4 compute (NVFP4 KV cache only, v0.32.0+ with FA2). No NVL72. No 270+ GB single-GPU.**

### Running vLLM on Blackwell (B200/B300)
- Switch to FP4 (NVFP4 via ModelOpt checkpoints) — 1.8–2× decode throughput on the same HBM budget.
- NVL72 collapses disagg cost — keep prefill/decode inside one NVLink5 domain; use `NixlConnector`.
- Minimum vLLM by workload — the two NVFP4 rows fail silently (wrong text, no crash):

  | Workload | Floor | Below the floor |
  |---|---|---|
  | B300/GB300 (SM 10.3) | v0.19 | no first-class SM103 support |
  | NVFP4, multi-GPU, Gemma/Qwen-style RMSNorm | v0.25.1 | repeated `!!!!!` from the fused allreduce+RMSNorm+quant path |
  | NVFP4/MXFP4 MoE + expert parallelism, CUTLASS MoE backend | v0.32.0 | `expert_map` ignored, wrong local experts, ~0% GSM8K (#59042) |

- 270 GB (HGX bin) or 279 GB (DGX bin) HBM per B300 often removes the *need* for KV offload on 70B-scale models. LMCache still earns its keep for 1M+ context and heavy prefix reuse.
- **Crossing v0.27.0 or v0.32.0 is an environment change:** torch, NCCL, Python,
  GCC and transformers floors moved — rebuild the container, never pip-upgrade in
  place. Floors per release: `references/vllm-platform-matrix.md` §6.
- **On v0.32.0+ pip installs, run `vllm download-kernels` after every install or
  upgrade** (#58765): `flashinfer-cubin` is no longer a dependency, so without it
  startup JIT-compiles for minutes on Blackwell, and a mismatched kernel set makes
  FlashInfer refuse to import. The `vllm/vllm-openai` image does it at build.

### Buying NVIDIA hardware in 2026
- **GB300 NVL72 is safe for 2026 capacity:** size the row for 135–155 kW, DLC @ 25 °C, 3φ 480 V. Vendors: NVIDIA DGX B300, Dell IR7000 + XE9780L / XE8712 sleds, Supermicro SRS-GB300-NVL72, Lenovo 7DJVCTO2WW, HPE.
- **Greenfield rows should be spec'd for Rubin NVL144:** 180–220 kW, 45 °C W45 warm water, 800 VDC HVDC, new MGX rack. Retrofitting later is expensive.
- **Rubin timing (2026-10-18):** first customer in production (CoreWeave, 2026-09-30);
  NVIDIA states no GA or delivery date — plan purchases against an OEM quoting firm
  order dates. vLLM `sm_107` is preview-only: CUDA ≥ 13.4, `cu134-nightly` images,
  tracking issue #49735 open. Dated evidence and the build recipe: `references/rubin-roadmap.md`.
- **Expect HBM allocation and PSU rectifier shelf lead times to dominate schedule risk.** SK hynix / Micron / Samsung HBM sold out through CY26.

### Key numbers to memorize
| Metric | Value |
|---|---|
| GB300 NVL72 aggregate HBM | 20.1 TB HBM3E (72 × 279 GB; NVIDIA: "> 20 TB") |
| GB300 NVL72 aggregate HBM BW | ~576 TB/s |
| GB300 NVL72 NVLink domain | 72 GPUs flat, 130 TB/s |
| H200 SXM5 | 141 GB HBM3E / 4.8 TB/s / 700 W |
| Rubin R100 (H2 2026) | ~288 GB HBM4 / ~20 TB/s |
| Rubin Ultra Kyber NVL576 rack | 600 kW |

## Paired skill

Configuring tiered KV (`--kv-offloading-size`, LMCache, NixlConnector, MooncakeConnector) for the hardware chosen here: load `vllm-caching` alongside.

## Before stating a version, pin or status

- **Read dependency pins from `requirements/{cuda,common,rocm}.txt` at the release
  tag, never from release-note prose** — the notes' "Dependencies" section mixes CI
  pins (`requirements/test/*`) with runtime pins.
- **Read the bug-fix sections of the current patch release, not only features** —
  silent-corruption fixes (wrong text, no crash) land there.
- **Anchor shipping claims to dated, checkable artifacts** — a named customer in
  production, an OEM quoting firm order dates — never to "in production" statements,
  which describe fab output, not delivery.
- **Re-probe every "not supported yet" before repeating it** — negatives about a
  moving upstream decay fastest.
- Prefer NVIDIA first-party datasheets, then OEM datasheets (Dell/Lenovo/Supermicro),
  SemiAnalysis, then news; where sources disagree, report the range with each citation.
  Sources and the verification stamp: `references/sources.md`.
