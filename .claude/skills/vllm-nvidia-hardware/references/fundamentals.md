# Memory-wall fundamentals (late 2025 / 2026)

Read this when the operator is asking *why* — why FP4 matters, why NVL72 matters, why HBM supply is a constraint. The per-SKU numbers in `gpu-specs.md` only mean what they mean once you understand the roofline.

## 1. Roofline — prefill is compute-bound, decode is memory-bound

LLM inference runs two fundamentally different phases:

| Phase | Arithmetic intensity (AI) | Bound by | Comment |
|---|---|---|---|
| **Prefill** | Tens to hundreds of FLOPs/byte (GEMMs on full attention) | Compute | Sits above the ridge point on modern GPUs |
| **Decode** (batch 1) | ~1 FLOP/byte — weights read once per token with tiny reuse | **HBM bandwidth** | Sits ~100× below the ridge; compute idle 95%+ of the time |

A recent empirical roofline study measures AI dropping ~5× from prefill to decode on
modern GPUs, with FFN GEMMs being the dominant shifting kernel
([arXiv 2512.01644](https://arxiv.org/html/2512.01644v1), 2025-12). At H100 SXM5's
495 TFLOPS FP16 / 3.35 TB/s, the ridge sits at ~148 FLOPs/byte — decode's AI≈1 is
nowhere near it. See also the practitioner framing in
[Towards Data Science — "Prefill is compute-bound, decode is memory-bound"](https://towardsdatascience.com/prefill-is-compute-bound-decode-is-memory-bound-why-your-gpu-shouldnt-do-both/).

The practical consequence: larger-batch serving amortizes weight reads over more decode
steps, raising effective AI; but single-stream latency is always memory-bound on any
modern GPU.

## 2. The bandwidth-vs-FLOPs gap keeps widening

Across Volta → Ampere → Hopper → Blackwell:

| Gen | Dense FP16 tensor TFLOPs | HBM BW (TB/s) | FLOPs/byte to saturate |
|---|---:|---:|---:|
| V100 (2017) | 125 | 0.9 | 139 |
| A100 (2020) | 312 | 2.0 | 156 |
| H100 (2022) | 989 | 3.35 | 295 |
| H200 (2024) | 989 | 4.8 | 206 |
| B200 (2024–25) | 2,250 | 8.0 | 281 |
| B300 / Blackwell Ultra (2025) | 3,750 | 8.0 | 469 |
| Rubin R100 (2026 projected) | ~8,000 (est.) | ~20 | ~400 |

Compute grew ~18× from V100→B200 while bandwidth grew ~9× — the **compute:bandwidth
ratio roughly doubled**, pushing the memory wall further into the workloads we run.
Blackwell Ultra's higher FP16 TFLOPs (vs B200) comes with the same 8 TB/s HBM BW, so
the ratio worsens again — which is precisely why **FP4 becomes structurally important
on B300**: halving weight bytes buys a direct 2× relief on the memory-bound decode
path.

Sources:
[SemiAnalysis — NVIDIA Tensor Core Evolution](https://newsletter.semianalysis.com/p/nvidia-tensor-core-evolution-from-volta-to-blackwell),
[SemiAnalysis — The Memory Wall (foundational)](https://semianalysis.com/2024/09/03/the-memory-wall/).

## 3. HBM generations and roadmap

| HBM gen | Per-stack BW | Per-stack capacity | Ships in |
|---|---:|---:|---|
| HBM2e | ~0.46 TB/s | 16 GB | A100, H100 PCIe |
| HBM3 | ~0.8 TB/s | up to 24 GB (8-Hi) | H100 SXM5 |
| HBM3E (8-Hi) | ~1.2 TB/s | 24 GB | H200, B200 |
| HBM3E (12-Hi) | ~1.2 TB/s | 36 GB | **B300 / GB300** |
| HBM4 | 2.0–2.8 TB/s (JEDEC JESD270-4) | 32–48 GB | **Rubin R100** (H2 2026) |
| HBM4E | up to ~3.3 TB/s | up to 64 GB | **Rubin Ultra R300** (2027) |

HBM4 **doubles the per-stack interface from 1024-bit to 2048-bit** — the structural
jump that lets bandwidth roughly keep pace with Rubin's compute uplift without driving
per-pin clocks higher. **B300 is HBM3E, not HBM4** — a common misread.

[SemiAnalysis — Scaling the Memory Wall: Rise and Roadmap of HBM](https://newsletter.semianalysis.com/p/scaling-the-memory-wall-the-rise-and-roadmap-of-hbm).

## 4. HBM supply situation 2026 — it's a constraint

- **Sold out through 2026.** SK hynix, Micron, and Samsung have contractually allocated
  their HBM output through CY26 per Q3 2025 earnings calls
  ([NotebookCheck, 2025](https://www.notebookcheck.net/SK-hynix-sells-out-its-DRAM-NAND-and-HBM-chip-supply-to-Nvidia-through-2026-as-AI-demand-outpaces-Samsung-and-Micron-s-capacity.1151402.0.html)).
- **Market share Q2 2025:** SK hynix 62%, Micron 21%, Samsung 17% — Micron has overtaken
  Samsung. Samsung is adding ~50% HBM capacity in 2026
  ([Astute Group](https://www.astutegroup.com/news/general/sk-hynix-holds-62-of-hbm-micron-overtakes-samsung-2026-battle-pivots-to-hbm4/)).
- **DRAM/HBM price surge** flagged by Samsung for 2026
  ([Network World, 2025-12](https://www.networkworld.com/article/4113772/samsung-warns-of-memory-shortages-driving-industry-wide-price-surge-in-2026)).
- **Operator implication:** HBM is the binding constraint on Blackwell delivery. Lead
  times on 33 kW PSU shelves and liquid-cooling plumbing compound this — see
  `nvl72-procurement.md`.

## 5. Energy economics — data movement dominates

Horowitz's canonical numbers (still cited — **foundational**):

| Operation | Energy |
|---|---:|
| FP32 add | 0.9 pJ |
| FP32 multiply | 3–4 pJ |
| 32-bit SRAM read | ~5 pJ |
| 32-bit HBM access | ~640 pJ |

HBM is **~100–200× more energy per bit than an arithmetic operation**; cross-server
InfiniBand is another ~10× on top of HBM. Modern HBM3/3E is in the low single-digit
pJ/bit range; PCIe and NVLink data movement is ~8 pJ/bit
([Future of Computing](https://news.future-of-computing.com/p/breaking-the-memory-wall-pt-2-a-closer-look-at-hbm-high-bandwidth-memory),
[NVIDIA HPCA 2017](https://research.nvidia.com/sites/default/files/pubs/2017-02_Architecting-an-Energy-Efficient/chatterjee.hpca2017.pdf)).

Why it matters: at rack scale (135 kW GB300 NVL72), every watt spent moving bits
between GPUs is a watt not spent on compute. This is the thesis behind NVLink5 /
NVL72 and ultimately NVLink-C2C + HVDC in Rubin.
