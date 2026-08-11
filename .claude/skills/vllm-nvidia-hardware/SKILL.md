---
name: vllm-nvidia-hardware
description: |-
  NVIDIA AI-hardware + vLLM-platform reference covering Hopper (H100/H200), Blackwell (B100/B200/B300) and Blackwell Ultra, Grace-Blackwell superchips and NVL72 racks (GB200, GB300), Vera Rubin (R100/R300) with VR200 NVL144 and Kyber NVL576, Dell PowerEdge XE family and IR5000/IR7000/IR9048 racks. Per-SKU HBM, FP4/FP8/FP16 TFLOPs, NVLink5, TDP, rack power/cooling (135 kW GB300, 180-220 kW NVL144, 600 kW Kyber), DLC vs RDHx, 800 VDC HVDC. Memory-wall roofline, HBM3E→HBM4 supply 2026. vLLM attention-backend × SM matrix, FP4/FP8 paths, KV connectors, Blackwell gotchas (SM103 TRTLLM hang, 270 vs 288 GB B300 bin split).
when_to_use: |-
  Trigger on NVIDIA-AI hardware sizing, procurement, facility, or vLLM-deployment questions. Triggers — HBM capacity/bandwidth, TDP, NVLink, GB300 NVL72 power/cooling, Vera Rubin timing, Dell PowerEdge XE, IR7000 racks, ORv3 power shelves, DLC flow rate, warm-water 45 °C, 800 VDC HVDC, rack weight, floor load, HBM supply 2026, FlashAttention/FlashInfer/FlashMLA/CUTLASS MLA/TRTLLM per SM, NVFP4, MXFP4, NixlConnector, MooncakeConnector, LMCache, CUDA 13 arch list, SM100/SM103/SM120 gotchas, memory-wall roofline, prefill-vs-decode. Narrow phrasings — "HBM on our XE9780", "wait for Rubin", "which GPU for {model}", "B200 vs H200 choice". Also implicit — "sizing for {model}", "audit hardware", "rack power budget", "can this GPU run {model}", "GPU recommendation", "deploy-memo hardware", "spec-study hardware".
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

5. **Running TRTLLM attention on GB300 with bare FlashInfer 0.6.7.** SM103 (GB300) **hung** with FlashInfer 0.6.7 (regression vs 0.6.6) — **fixed 2026-04-07** via flashinfer-ai/flashinfer#2956 (closes #2939) in 0.6.7.postN. If pinned to plain 0.6.7 without the post fix, disable TRTLLM on SM103 (the FlashInfer default backend is actually faster there). `references/vllm-platform-matrix.md` has this and other Blackwell readiness notes.

## Operator cheat sheet

### Running vLLM on Hopper (H100/H200)
- Default to FP8 weights + FP8 KV cache on H200 for long context.
- Use FlashMLA for DeepSeek models; FlashAttention-3 elsewhere.
- Disagg prefill across nodes needs XDR IB + GPUDirect-RDMA — use CPU/NVMe offload (LMCache) first.
- **No FP4. No NVL72. No 288 GB single-GPU.**

### Running vLLM on Blackwell (B200/B300)
- Switch to FP4 (NVFP4 via ModelOpt checkpoints) — 1.8–2× decode throughput on the same HBM budget.
- NVL72 collapses disagg cost — keep prefill/decode inside one NVLink5 domain; use `NixlConnector`.
- Pin vLLM **≥ v0.19** for first-class B300/GB300 (SM 10.3) support, and
  **≥ v0.25.1 if serving NVFP4**: v0.25.0 and earlier can emit garbage
  (repeated `!!!!!`) from the fused allreduce+RMSNorm+quant path on NVFP4
  models with Gemma/Qwen-style RMSNorm. Silent wrong output, no crash — see
  `references/vllm-platform-matrix.md` §6.
- 270 GB (HGX bin) or 288 GB (DGX bin) HBM per B300 often removes the *need* for KV offload on 70B-scale models. LMCache still earns its keep for 1M+ context and heavy prefix reuse.
- **Upgrading to v0.27.0 is an environment change, not a version bump:** `requirements/cuda.txt` pins `torch==2.13.0` / `torchvision==0.28.0` (#48155, flagged breaking upstream; Triton 3.7.1 rides along with torch rather than being pinned separately), and the image build sets `NCCL_VERSION=2.30.7` — the NCCL floor is what unlocks DeepEPv2 for Wide-EP (#45321). Rebuild the container; don't pip-upgrade in place.

### Buying NVIDIA hardware in 2026
- **GB300 NVL72 is safe for 2026 capacity:** size the row for 135–155 kW, DLC @ 25 °C, 3φ 480 V. Vendors: NVIDIA DGX B300, Dell IR7000 + XE9780L / XE8712 sleds, Supermicro SRS-GB300-NVL72, Lenovo 7DJVCTO2WW, HPE.
- **Greenfield rows should be spec'd for Rubin NVL144:** 180–220 kW, 45 °C W45 warm water, 800 VDC HVDC, new MGX rack. Retrofitting later is expensive.
- **Rubin timing, as of 2026-07-21:** validated racks exist (CoreWeave qualified a Dell-supplied Vera Rubin NVL72 on 2026-05-31), and Jensen Huang said on 2026-07-15 that it is "already in production" — but NVIDIA has given **no customer-delivery date**, only "partner products in 2H 2026". Treat "in production" as a fab statement, not a delivery statement; the signal to plan against is an OEM quoting firm order dates. **vLLM began Rubin enablement in v0.27.0** — `sm_107` is a real build target (#49387) with SM107 NVLink all-reduce (#49647) — but it requires **CUDA ≥ 13.4**, the shipped `vllm/vllm-openai` image is CUDA 13.0.3 with no SM107 cubins, and tracking issue #49735 is still open. Started, not finished. Detail in `references/rubin-roadmap.md`.
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

Refresh when new NVIDIA products launch or when the HBM / rack-power / vLLM backend landscape shifts materially.

**Separate vendor "in production" claims from delivery evidence.** The 2026-07-21
pass found NVIDIA saying Vera Rubin was "already in production" while giving no
customer-delivery date — the two are routinely conflated in coverage. Anchor
timing claims to dated, checkable artifacts (a named customer completing
qualification, an OEM quoting firm order dates), not to executive statements.

**Check the current vLLM patch release for correctness fixes, not just features.**
The same pass found v0.25.0 silently corrupting NVFP4 output, fixed one release
later. A release-note sweep that only reads the feature sections will miss this
class entirely.

**A vLLM release note's "Dependencies" section mixes runtime pins with CI pins —
read the requirements file, not the prose.** The v0.27.0 notes list
"Transformers 5.14.1 (#49223)" among genuine bumps, but that PR touches only
`requirements/test/*`; the runtime floor is `transformers >= 5.5.3` in
`requirements/common.txt` and did not move. Triton 3.7.1 is the same shape — named
in #48155's title, pinned in no runtime requirements file, arriving with torch.
Before writing any dependency into a matrix operators will follow, read it out of
`requirements/{cuda,common,rocm}.txt` at the release tag.

**A "no support yet" finding has a shelf life — re-probe it, don't inherit it.**
The 2026-07-21 pass correctly established that vLLM had no Rubin code path. Three
weeks later `sm_107` was a build target. Negatives about a moving upstream decay
faster than positives; re-run the probe rather than carrying the conclusion.

Last verified: 2026-08-11 — vLLM release line rebaselined v0.25.1 → **v0.27.0**
(2026-08-10) against the v0.27.0 source tree: Rubin `sm_107` enablement, the SM121
kernel-less-build fix, FA4 SM100 capabilities, dependency pins, and every cited
`repo/path:line` pointer in `references/vllm-platform-matrix.md`. The hardware spec
tables (per-GPU HBM/TFLOPs, rack power, Dell SKUs) and the Rubin *shipping-status*
evidence were **not** re-probed this pass and keep their earlier `[LV:]` dates in
`references/sources.md`.
