# NVIDIA GPU per-SKU reference — Hopper, Blackwell, Blackwell Ultra

All tensor TFLOPs below are **dense, no sparsity** unless noted. NVIDIA marketing often
quotes the sparse figure (2× dense) — always check which column you're reading.

## 1. Hopper (H100 / H200)

| SKU | HBM | HBM gen | HBM BW | FP16 TC | FP8 TC | NVLink BW | PCIe | TDP | Form | FP4 |
|---|---:|---|---:|---:|---:|---|---|---:|---|---|
| H100 SXM5 | 80 GB | HBM3 | 3.35 TB/s | 989 TF | 1,979 TF | NVLink4 / 900 GB/s | Gen5 x16 | 700 W | SXM5 | ❌ |
| H100 PCIe | 80 GB | HBM2e | 2.0 TB/s | 756 TF | 1,513 TF | NVLink4 / 600 GB/s bridge | Gen5 x16 | 300–350 W | PCIe dual-slot | ❌ |
| H100 NVL | 94 GB/card (188/pair) | HBM3 | 3.9 TB/s | 835 TF | 1,671 TF | NVLink4 bridge | Gen5 x16 | 350–400 W | 2× PCIe, bridged | ❌ |
| H200 SXM5 | 141 GB | HBM3E | 4.8 TB/s | 989 TF | 1,979 TF | NVLink4 / 900 GB/s | Gen5 x16 | up to 700 W | SXM5 | ❌ |
| H200 NVL (PCIe) | 141 GB | HBM3E | 4.8 TB/s | 835 TF | 1,671 TF | NVLink4 / 600 GB/s bridge (up to 4-way) | Gen5 x16 | up to 600 W | PCIe dual-slot | ❌ |

**HGX H100/H200 baseboard:** 8× GPUs, 4× 3rd-gen NVSwitches, 900 GB/s per GPU bidir.
HGX H100 aggregate: 640 GB HBM3, 26.8 TB/s. HGX H200: 1,128 GB HBM3E, 38.4 TB/s.

**NVLink aggregate note:** NVIDIA markets 900 GB/s as bidirectional (18 × 50 GB/s
bidi). Half-duplex is 450 GB/s; sources that quote 450 are counting one direction.

**No Hopper NVL72 exists.** The closest Grace-Hopper variant is **GH200 NVL32**
(32 Grace-Hopper superchips). 72-GPU NVLink domains are Blackwell-only.

**FP4 is not supported on Hopper.** Transformer Engine 1 on Hopper supports
FP8/FP16/BF16/TF32/INT8 only.

Primary sources:
[NVIDIA H100 datasheet](https://resources.nvidia.com/en-us-tensor-core/nvidia-tensor-core-gpu-datasheet),
[NVIDIA H200 datasheet](https://nvdam.widen.net/s/nb5zzzsjdf/hpc-datasheet-sc-nvidia-h200-datasheet-nvidia-us),
[Hopper in-depth](https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/).

## 2. Blackwell and Blackwell Ultra — CRITICAL: B300 has two shipping bins

| SKU | Die | HBM | HBM BW | FP16 dense | FP8 dense | **FP4 dense** | NVLink5 BW | TDP | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| B100 | 2 chiplets | 192 GB HBM3E | 8 TB/s | ~1,750 TF | ~3,500 TF | ~7,000 TF | 1.8 TB/s | 700 W | **Effectively cancelled for HGX volume**; replaced by B200A/B102 |
| B200 SXM | 2 chiplets | 180–192 GB HBM3E (SKU-dependent) | 8 TB/s | 2,250 TF | 4,500 TF | 9,000 TF | 1.8 TB/s | 1,000 W | Standard HGX Blackwell |
| **B300 — DGX / GB300 Superchip bin** | 2 chiplets (160 SMs, 208B transistors) | **288 GB HBM3E** (12-Hi) | 8 TB/s | 3,750 TF | 7,500 TF | **15,000 TF** | 1.8 TB/s | **1,400 W** | NVIDIA reference, DGX B300, GB300 Superchip. +67% FP4 vs B200 |
| **B300 — HGX NVL8 SXM6 (OEM bin)** | 2 chiplets | **270 GB HBM3E** | 8 TB/s | ~3,750 TF | ~7,500 TF | ~15,000 TF | 1.8 TB/s | **1,100 W** | Lower-TDP HGX 8-way SKU shipped by Dell (XE9780/XE9780L/XE9785/XE9785L), Supermicro, Lenovo. **18 GB less HBM and 300 W less TDP than the DGX-bin** |

**The bin split matters.** Without it, 8-GPU TDP math is off by 2.4 kW and per-GPU HBM
is off by 18 GB. When the operator refers to B300 in a Dell / Supermicro / Lenovo HGX
box, default to the **270 GB / 1,100 W HGX NVL8** bin. When citing NVIDIA marketing
numbers ("288 GB B300", "15 PFLOPS FP4"), those are the DGX / Superchip bin.

**Compute-format ratio** is 4:2:1 FP4:FP8:FP16 dense — if only one column is cited,
derive the others.

## 3. Blackwell superchips and rack products

| Product | GPUs | CPUs | Aggregate HBM | Agg HBM BW | NVLink domain | Rack power | Cooling | Status |
|---|---:|---:|---:|---:|---|---:|---|---|
| **GB200 Superchip** | 2× B200 | 1× Grace (72-core V2, 480 GB LPDDR5X) | 384 GB HBM3E + 480 GB LPDDR5X | 16 TB/s HBM | 1.8 TB/s/GPU; 900 GB/s NVLink-C2C | ~2.7 kW module | Liquid required | Shipping |
| **GB300 Superchip** | 2× B300 (DGX bin, 288 GB) | 1× Grace | **576 GB HBM3E** + LPDDR5X | 16 TB/s HBM | 1.8 TB/s/GPU | ~3+ kW module | Liquid | 2025 H2 → 2026 |
| **GB200 NVL72** | 72× B200 | 36× Grace | 13.5 TB HBM3E | 576 TB/s | 72 GPUs flat, 130 TB/s all-to-all | **~120 kW/rack** | DLC mandatory | Shipping |
| **GB200 NVL36×2** | 36 + 36 (paired racks) | 18 + 18 | 6.75 TB/rack | 288 TB/s/rack | 72 across pair | ~66 kW/rack | DLC | Shipping |
| **GB300 NVL72** | 72× B300 | 36× Grace | **20.7 TB HBM3E** | 576 TB/s | 72 GPUs, 130 TB/s | **135 kW nom / 155 kW peak** | DLC mandatory | Ramping late-2025/2026 |

**FP4 is a memory-wall mitigation on Blackwell.** Halving weight size vs FP8 is a
direct 2× relief on decode's bandwidth bottleneck. NVIDIA claims ~2× decode throughput
vs FP8 on the same hardware, and up to 15× vs Hopper FP8 at full NVL72 scale (that
15× bundles FP4 + NVL72 + disagg; isolated FP4-vs-FP8 is 1.8–2×).

**NVFP4 vs MXFP4:** both are microscaling FP4. MXFP4 = block size 32, E8M0 scale (open
MX standard); NVFP4 = block size 16, E4M3 scale (finer granularity, better accuracy,
<1% degradation vs BF16 per NVIDIA).

**Transformer Engine 2 (Blackwell)** adds FP4 (NVFP4/MXFP4), FP6, MXFP8, with hardware
per-block scale inside the Tensor Core — no software scaling tax.

Primary sources:
[NVIDIA GB300 NVL72](https://www.nvidia.com/en-us/data-center/gb300-nvl72/),
[Blackwell Ultra datasheet](https://resources.nvidia.com/en-us-blackwell-architecture/blackwell-ultra-datasheet),
[Inside Blackwell Ultra (dev blog)](https://developer.nvidia.com/blog/inside-nvidia-blackwell-ultra-the-chip-powering-the-ai-factory-era/),
[NVFP4 blog](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/),
[SemiAnalysis — Blackwell Perf/TCO](https://semianalysis.com/2024/04/10/nvidia-blackwell-perf-tco-analysis/),
[Tom's — B300 announcement](https://www.tomshardware.com/pc-components/gpus/nvidia-announces-blackwell-ultra-b300-1-5x-faster-than-b200-with-288gb-hbm3e-and-15-pflops-dense-fp4).
