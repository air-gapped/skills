# Session findings — measured baselines

Concrete numbers from real boxes audited with this skill. New runs append
here. Use as a ground-truth cross-check when interpreting the bench harness
output on a new box.

---

## H200 SXM5 — pinned-host ↔ GPU memcpy

### Verda 8H200.141S.176V (FIN-03, on-demand, 2026-05-04)

Underlying chassis CPU: **AMD EPYC 9654** (Genoa, Zen 4) — exposed to QEMU
guest as 176 single-core sockets in 1 NUMA node.
Image: `ubuntu-24.04-cuda-12.8-open-docker`.
torch 2.11.0+cu128, Python 3.12.

```
Per-GPU 1024 MB pinned-memcpy throughput (n=16 measurements: 8 GPUs × 2 tags):

  H2D mean: 57.28 GB/s   (range 56.58 – 57.39, spread <1.5%)
  D2H mean: 53.62 GB/s   (range 53.61 – 53.64, spread <0.06%)

PCIe Gen5 x16 theoretical raw: ~63 GB/s
H2D at 91% of theoretical, D2H at 85% — textbook efficiency.

Smaller sizes (size-overhead-bound, NOT memory-bound):
  16 MB H2D: 36-48 GB/s (high variance, launch overhead dominates)
  64 MB H2D: 39-49 GB/s
  256 MB H2D: 55-57 GB/s (steady state begins)
  1024 MB H2D: 57.3 GB/s (full saturation)
```

LMCache chunk-size band (~85 MB for K2.6 MLA at TP=8): **42-46 GB/s** (the
realistic working ceiling for KV offload, not the 57 GB/s asymptote).

membind=0 and interleave=all give **identical** results on this box because
QEMU exposes only 1 NUMA node — the cross-NUMA penalty is hidden by virt.

### Reference: same chassis K2.6 + LMCache run (2026-05-03)

Cold-pass LMCache CPU-tier *store* throughput per rank, measured from worker
logs (`Stored ... throughput: ... GB/s` lines):

```
n = 202 store events
min  1.79 GB/s
max  2.45 GB/s
mean 2.32 GB/s     ← LMCache utilization at the time
```

**LMCache hardware utilization: 2.32 / 57.28 = ~4.05% of the per-GPU
pinned-memcpy ceiling**, or ~5% of the chunk-size-realistic 42-46 GB/s
ceiling. The bottleneck is in LMCache's per-iteration alloc/dealloc + layer
serialization, not the host hardware.

---

## RTX PRO 6000 (Blackwell Server Edition) — pinned-host ↔ GPU

### Verda 2RTXPRO6000.60V (FIN-03, spot, 2026-05-04)

Single NUMA node visible to guest; underlying CPU not directly identified
(virt-flattened). PCIe Gen5 x16 capable but not stress-tested deep.

The pinned-memcpy bench was not run on this SKU during validation (script
verified end-to-end without `--bench` to avoid OOM risk on the 1.4 GB-free
node). For the hardware-only validation + 7-second snapshot pass: see
`~/host-snapshots/verda-h200-20260504/...` directory tree
references; for full RTX PRO 6000 baselines, run the bench on a fresh
spot instance.

---

## EPYC 7551 (Naples, Zen 1, 2017) home server — PCIe Gen3 x8 ceiling

### Bare-metal home box (epyc, 2026-05-04)

Single-socket EPYC 7551 (32c/64t), 256 GB DDR4, 4 NUMA nodes (Naples MCM,
4-die per socket, NPS=4 effectively). 2× RTX 4060 Ti.

Kernel 6.17.0-20-generic Ubuntu 24.04. acpi-cpufreq + schedutil governor.
3 cpuidle states only: POLL, C1 (1µs), C2 (400µs) — all enabled. Boost
enabled. Pkg power 83 W idle on 250 W TDP. C2 cumulative residency since boot
= 1.3 × 10¹² µs (deeply idle most of the time).

Bench results (n=80, all 4 NUMA bindings + interleave, sizes 16/64/256/1024 MB):

```
Per-GPU 1024 MB pinned-memcpy throughput:

  H2D mean: 6.71 GB/s   (range 6.69 – 6.71, spread 0.03 GB/s ≈ 0.4%)
  D2H mean: 6.59 GB/s   (range 6.58 – 6.59, spread <0.02 GB/s)

PCIe Gen3 x8 theoretical raw: ~7.88 GB/s
H2D at 85% efficiency — textbook for Gen3 x8.

Variance across all 5 NUMA bindings: <0.6% — the link is saturated long
before DRAM bandwidth becomes the bottleneck.
```

**Why the same number across all NUMA bindings**:
- Naples 7551 is PCIe Gen 3 only (Zen 1, 2017).
- Gen3 x8 saturates at ~6.7 GB/s effective.
- DRAM bandwidth (~170 GB/s aggregate across 4 nodes, even cross-die ~100 GB/s)
  is 25× the PCIe ceiling — DRAM cannot be the bottleneck at this transfer
  rate.
- → NUMA placement of the pinned buffer doesn't affect throughput on PCIe
  Gen3 hardware.

This is the **opposite** of an H200/B200 box where the link can sink 50+ GB/s
and DRAM (especially cross-NUMA) becomes the next ceiling. Our H200 finding
that "membind = interleave because virt is flat" is also a different reason
for the same observation — but in that case the hypothesis is "would have
shown delta if NUMA were exposed."

---

## Per-chassis expected H2D ceilings (rough estimates from spec'd PCIe gen)

To use as a quick sanity check when running the bench on a new box:

| Chassis / GPU | PCIe gen × width | Theoretical raw | Expected effective (~85-91%) |
|---|---|---:|---:|
| HGX H100 SXM5 (any chassis) | Gen5 x16 | 63 GB/s | **50-57 GB/s** |
| HGX H200 SXM5 (any chassis) | Gen5 x16 | 63 GB/s | **50-57 GB/s** |
| HGX B200 SXM6 (any chassis) | Gen5 x16 | 63 GB/s | **50-57 GB/s** (same link, same expectation) |
| HGX B300 SXM6 NVL8 bin | Gen5 x16 | 63 GB/s | **50-57 GB/s** |
| H100 NVL PCIe | Gen5 x16 | 63 GB/s | 50-57 GB/s |
| L40S | Gen4 x16 | 31 GB/s | **25-28 GB/s** |
| RTX 4060 Ti / 4070 / 4080 | Gen4 x8 (laptops/cheap) — Gen4 x16 (full) | 16 GB/s / 31 GB/s | 13-14 GB/s / 25-28 GB/s |
| RTX 4060 Ti on PCIe Gen3 host (legacy) | Gen3 x8 (negotiated down) | 7.88 GB/s | **6.5-6.7 GB/s** |
| A100 SXM4 | Gen4 x16 | 31 GB/s | 25-28 GB/s |
| A100 PCIe | Gen4 x16 | 31 GB/s | 25-28 GB/s |

**If your H2D is 80%+ of expected** → no host-side bottleneck. If <70% →
audit `recommended-tunings.md` §A (CPU power), §B (boot args), §F (NVIDIA
state), §K (BIOS).

---

## Future runs — what to capture

When auditing a new box, save the snapshot tarball and append a section
here with:

1. Chassis + CPU + GPU SKU
2. Underlying virt vs bare-metal
3. Kernel + driver + CUDA versions
4. tuned profile (if any) active at audit time
5. Bench results: 1024 MB H2D and D2H mean, range; smaller-size
   approximation
6. Any unexpected probe values flagged in INDEX.md

This file is the trend-detection corpus. Multiple data points on the same
chassis SKU let us build "expected baseline" tables instead of relying on
back-of-envelope theoretical numbers.
