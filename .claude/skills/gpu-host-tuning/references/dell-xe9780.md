# Dell PowerEdge XE9780 / XE9780L — chassis-specific tuning

Concrete BIOS settings, slot↔CPU map, and known-quirk notes for Dell's
10U air-cooled XE9780 and 3 OU liquid-cooled XE9780L (regulatory model
**E125S**), which carry 8× HGX B300 NVL8 270 GB 1100W SXM6 (or 8× HGX B200
180 GB 1000W SXM6) GPUs on a 6th-gen Intel Xeon (Granite Rapids) platform.

For sibling chassis: see `dell-xe9680.md` (XE9680, 6U air, SPR/EMR + H100/
H200 SXM5), and the family table in `recommended-tunings.md`. The XE9785/
XE9785L carries B300 on AMD EPYC 9005 — different BIOS, similar approach.

---

## Hardware summary

| Subsystem | XE9780 (air, 10U) | XE9780L / XE9780LAP (liquid, 3 OU) |
|---|---|---|
| Chassis | 439.5 × 482.3 × 1044.7 mm; **163.2 kg** | 3 OU sled in IR7000 ORv3 rack |
| CPUs | 2× Intel Xeon 6 (Granite Rapids), up to **86c**, 350W TDP | L: 2× Xeon 6, up to 86c. **LAP: up to 128c** |
| Supported SKUs | 6747P (48c/2.7G), 6767P (64c/2.4G), 6776P (64c/2.3G), 6787P (86c/2.0G) — all 350W, all DDR5-6400 | Same SPR/EMR-class supported list |
| UPI | 4× per socket @ 24 GT/s (vs SPR 16 / EMR 20 GT/s) |
| PCIe per CPU | **192 Gen5 lanes** dual-socket (vs 80 Gen5 on SPR/EMR) |
| DDR5 | **6400 MT/s 1DPC** / 5200 MT/s 2DPC |
| DIMMs | 32 RDIMM, 4 TB (8 TB post-RTS with 256 GB DIMMs) | L: 4 TB; **LAP: 6 TB** |
| GPUs | 8× HGX B300 NVL8 270 GB **1100W SXM6** (Dell HGX bin) **or** 8× HGX B200 180 GB 1000W SXM6 |
| Embedded NICs | 8× ConnectX-8 OSFP integrated on the GPU baseboard (B300 only, 800 Gb/s/port) |
| Storage | 16× E3.S Gen5 NVMe direct from PSB **or** 10× U.2 Gen5 NVMe (post-RTS) | L: 16× E1.S **or** 8× U.2 + 2× CEM |
| PSU | 12× 3200W AC Titanium (200-240 VAC / 240 VDC) | 6× 5500W AC in 33 kW power shelf @ 54 V busbar (IR7000 rack-level) |
| Cooling | 15 hot-swap GPU fans + 5 cold-swap CPU fans | DLC on CPU + GPU + NVSwitch |
| Rack | Standard 19" | **IR7000** ORv3 21" only |

---

## PCIe slot ↔ CPU map (from XE9780 slot priority matrix, Table 14)

The XE9780 has up to 13 PCIe expansion slots plus the OCP slot:

```
Slot 1  (OCP)   → Processor 2
Slot 2  (PCIe)  → Processor 2
Slot 3  (PCIe)  → Processor 2     ← high-power DPU/NIC slot (B300 only — slots 3, 6, 9, 12)
Slot 4  (PCIe)  → Processor 2
Slot 5  (PCIe)  → Processor 2
Slot 6  (PCIe)  → Processor 2     ← high-power DPU/NIC slot
Slot 7  (PCIe)  → Processor 2
Slot 8  (PCIe)  → Processor 1
Slot 9  (PCIe)  → Processor 1     ← high-power DPU/NIC slot
Slot 10 (PCIe)  → Processor 1
Slot 11 (PCIe)  → Processor 1
Slot 12 (PCIe)  → Processor 1     ← high-power DPU/NIC slot
Slot 13 (PCIe)  → Processor 1
```

GPUs occupy logical slot IDs 21-28 (8× SXM6 on the GPU baseboard).

### Two distinct riser/baseboard configurations

| Config | What it is | Slots populatable | When used |
|---|---|---|---|
| **PSBB + B200** | "PCIe Slot Base Board" + 8× B200 SXM6 | All 13 slots usable | B200 deployments — flexible IO |
| **PSRBB + B300** | "PCIe Slot Reduced Base Board" + 8× B300 SXM6 | Only **slots 1, 3, 6, 9, 12** populatable | B300 deployments — thermal/airflow constraints; the rest are blanked |

So with **B300**, you have exactly:
- **1 OCP** slot (slot 1, on Processor 2)
- **4 high-power add-in slots** (3, 6 on Processor 2; 9, 12 on Processor 1)
- Plus the 8× embedded ConnectX-8 OSFP on the GPU baseboard itself

### GPU ↔ CPU NUMA mapping (HGX-8 standard wiring)

The 8× SXM6 baseboard splits into two halves; the XE9780 follows the
universal HGX-8 convention:

```
GPU0–GPU3  →  PCIe Gen5 switches  →  CPU 1  (NUMA node 0)
GPU4–GPU7  →  PCIe Gen5 switches  →  CPU 2  (NUMA node 1)
```

Confirm via `nvidia-smi topo -m`:
- GPU NUMA Affinity column shows `0` for GPU0–3 and `1` for GPU4–7
- All `0` = NUMA disabled in BIOS or virt guest

NVSwitch on the SXM6 baseboard means GPU↔GPU traffic stays at 900 GB/s
(or 1.8 TB/s aggregate via the 5th-gen NVLink rates) regardless of socket;
only CPU↔GPU traffic crosses UPI when "wrong-side."

### NIC placement — match the workload

**With B300 (only 4 add-in slots available, 3/6/9/12)**:

```
Slot 3  → CPU 2 → near GPU4–7 (right half)
Slot 6  → CPU 2 → near GPU4–7 (right half)
Slot 9  → CPU 1 → near GPU0–3 (left half)
Slot 12 → CPU 1 → near GPU0–3 (left half)
```

For balanced GPUDirect RDMA, place **2 NICs per side** here (4 total). The
8× embedded ConnectX-8 OSFP on the baseboard already provides per-GPU
networking — pair each rank with its embedded port via NCCL `NCCL_IB_HCA`.

**With B200 (all 13 slots)**: Per-CPU split is slots 2-7 → CPU 2, slots 8-13
→ CPU 1. Recommended ConnectX-7 priority order from Dell: `4, 8, 7, 11, 2,
10, 5, 13, 6, 9, 3, 12` — alternates sides for symmetric IO.

### High-power DPU/NIC slot caveat

Per Dell: slots 3, 6, 9, 12 are the only ones that can carry **>75W**
SmartNICs/DPUs (BlueField-3, ConnectX-8 add-in, Broadcom 200/400G). Other
slots are 75W max.

---

## BIOS settings — recommended for inference (Granite Rapids)

Reach via iDRAC virtual console or F2 at boot. Path: `System BIOS Settings`.
The 16G PowerEdge BIOS Performance and Workload Tuning Guide is the
authoritative cross-reference.

### System Profile Settings (top-level preset)

```
System Profile         = Performance
Workload Profile       = AI/ML Optimized          (16G BIOS revisions 2.0+ added this preset)
                         OR  HPC Profile  (older or fallback)
```

`Performance` profile overrides all sub-settings to performance-biased
defaults. Use `Custom` only if you need to override individual sub-levers
beyond what `Performance` sets.

### Processor Settings (Granite Rapids specifics)

```
Logical Processor               = Enabled                  # Hyper-Threading on
CPU Power Management            = Maximum Performance
                                  (ranks: Maximum Performance > OS DBPM > System DBPM > Node Manager)
C States                        = Disabled
                                  OR Limited to C1
C1E                             = Disabled
Turbo Boost                     = Enabled
Energy Efficient Turbo          = Disabled
Sub NUMA Cluster (SNC)          = Disabled
                                  OR SNC2  (2 nodes/socket — exposes per-die topology)
                                  OR SNC4  (Granite Rapids new — 4 nodes/socket per CCD;
                                            useful for fine-grained NUMA-locality
                                            workloads, NOT recommended for whole-box NCCL)
Hardware Prefetcher             = Enabled
Adjacent Cache Line Prefetch    = Enabled
DCU Streamer Prefetcher         = Enabled
DCU IP Prefetcher               = Enabled
LLC Prefetch                    = Enabled
X2APIC Mode                     = Enabled
Uncore Frequency Scaling        = Enabled  (or "Maximum")
Intel Speed Select Technology   = Disabled (unless explicitly using ISST profiles)
HWP Native Mode                 = Enabled  (Granite Rapids — CPPC v2 control)
HWP Dynamic Boost               = Enabled  (where exposed)
```

### Memory Settings (DDR5-6400 territory)

```
Memory Operating Mode    = Optimizer Mode
                           (REQUIRED for full DDR5-6400 1DPC bandwidth — ~410 GB/s/socket)
Memory Patrol Scrub      = Disabled
Memory Refresh Rate      = 1x
Memory Frequency         = Maximum Performance
                           (allows Granite Rapids to negotiate DDR5-6400 at 1DPC)
Snoop Mode               = Home Snoop with Directory and Op State (HSDOS)  default
DIMM Self Healing        = Enabled
Memory Bandwidth Boost   = Enabled (when shown — Granite Rapids exposes this)
ADDDC Sparing            = Enabled (correctable error mitigation, near-zero cost)
```

### System Profile sub-pane

```
CPU Power Management                = Maximum Performance
Memory Frequency                    = Maximum Performance
Turbo Boost                         = Enabled
C1E                                 = Disabled
C States                            = Disabled
Energy Efficient Turbo              = Disabled
Monitor/Mwait                       = Enabled            (required for OS C-state control)
Workload Profile                    = AI/ML Optimized
CPU Interconnect Bus Speed          = Maximum Performance  (caps UPI at 24 GT/s)
PCIe ASPM L1 Link Power Management  = Disabled
```

### Integrated Devices

```
SR-IOV Global Enable              = Enabled  (if VFIO passthrough planned)
Memory Mapped I/O above 4GB       = Enabled  (REQUIRED for B300's HBM-mapped BAR)
Memory Mapped I/O Base            = 56T or 64T  (Granite Rapids supports >12T BAR space)
Resizable BAR                     = Enabled  (REQUIRED for B300 full-HBM BAR)
Slot Disablement                  = All slots Enabled (don't accidentally disable any)
Embedded OSFP                     = Enabled  (for B300's integrated 8× CX-8)
```

### Boot Settings

```
Boot Mode                         = UEFI
Secure Boot                       = your call (NVIDIA driver works either way)
```

---

## Common XE9780 quirks worth knowing

| Symptom | Cause | Fix |
|---|---|---|
| Only 4 PCIe slots usable on B300 config | PSRBB layout — slots 2, 4, 5, 7, 8, 10, 11, 13 are blanked by design | Use embedded 8× CX-8 OSFP instead of stacking add-in NICs |
| GPU `Power Limit` reads 1000W on B300 (expecting 1100W) | iDRAC/firmware power-cap may default conservative | `nvidia-smi -pl 1100` after persistence enabled (post-driver-load) |
| `nvidia-smi topo -m` shows `NV18` between every pair (good) — should be 18 NVLink-5 connections per GPU pair | This is correct for HGX B300 NVL8 270G bin (1.8 TB/s aggregate per GPU) | n/a — confirms healthy NVLink mesh |
| `nvidia-smi -q -d ECC` shows Disabled | Some Dell factory images ship with B300 ECC off for benchmarks | `nvidia-smi -e 1` (REBOOT REQUIRED to take effect); do this for production |
| dmidecode shows DDR5-5200 instead of 6400 | 2DPC populated → DDR5 caps at 5200 on Granite Rapids | Move to 1DPC (16 DIMMs/socket) for full 6400; or accept the 19% bandwidth hit |
| One slot reports x8 instead of x16 | Bifurcation set in BIOS (PCIe slot bifurcation) | Confirm `Slot Bifurcation` = `Default x16` for non-bifurcating cards |
| iDRAC reports thermal alarm on Slot 3/6/9/12 | High-power NIC drawing >75W in a "warm aisle" deployment | Verify chassis ambient ≤25 °C; consider DLC variant (XE9780L) for >35 °C inlet rooms |

---

## XE9780 + nvidia-tuned-profiles

`nvidia-tuned-profiles` does NOT yet ship a `dgx-xe9780-performance`-style
profile (it's a Dell chassis, not a DGX). Two approaches:

### Option A — generic Red Hat profile + custom delta

```bash
tuned-adm profile accelerator-performance     # RHEL/SUSE generic GPU profile
# or:
tuned-adm profile latency-performance        # if accelerator-performance isn't present
```

Then layer XE9780-specific kernel cmdline via a one-shot custom profile:

```ini
# /etc/tuned/dell-xe9780-b300/tuned.conf
[main]
summary=Dell XE9780 + 8×B300 SXM6 (Granite Rapids, 1100W TGP)
include=accelerator-performance

[bootloader]
cmdline=iommu=pt default_hugepagesz=1G hugepagesz=1G hugepages=128 init_on_alloc=0 pci=realloc=off pcie_aspm=off intel_iommu=on
# 128 × 1GB = 128 GiB of 1GB hugepages headroom — adjust to expected KV cache size
# pci=realloc=off is required for B300 BAR allocation on some XE9780 BIOS revs

[sysctl]
kernel.numa_balancing=0
vm.swappiness=1
vm.zone_reclaim_mode=0
fs.file-max=10000000
```

### Option B — install `nvidia-tuned-profiles` and use `nvidia-base`

```bash
apt install nvidia-tuned-profiles
tuned-adm profile nvidia-base nvidia-no-mitigations
# nvidia-base sets governor=performance, init_on_alloc=0, ARP/ICMP tuning,
# nvidia-persistenced enabled, nvidia-peermem module loaded
```

Then add the XE9780-specifics on top via your own `dell-xe9780-b300/`
profile that does `include=nvidia-base` and adds the `[bootloader]` block
above.

---

## Per-CPU-bin DDR5 expectations on Granite Rapids

Use these to sanity-check `12_dmidecode_memory.txt` `Configured Memory Speed`:

| Granite Rapids SKU | Cores | Max DDR5 (1DPC) | At 2DPC | TDP |
|---|---|---|---|---|
| 6747P | 48 | 6400 MT/s | 5200 | 330 W |
| 6767P | 64 | 6400 | 5200 | 350 W |
| 6776P | 64 | 6400 | 5200 | 350 W |
| 6787P | 86 | 6400 | 5200 | 350 W |

If `Configured Memory Speed` shows less than the table values, BIOS is
capping or the DIMM SPD/Manufacturer is mismatched.

Aggregate 2-socket memory bandwidth at full-pop (1DPC, 16 DIMMs/socket):
- Granite Rapids 6400 × 8 ch × 2 sock × 8 B = **~819 GB/s** (vs SPR's ~614,
  EMR's ~717)

This 14-33% memory-bandwidth lift is the biggest reason XE9780 outperforms
XE9680 on host-side workloads (KV offload, prefix-cache rebuild, LMCache
CPU tier) at equivalent GPU TGP.

---

## Cooling notes

- **Air XE9780**: 15 hot-swap GPU fans + 5 cold-swap CPU fans. Inlet temp
  >35 °C will throttle B300 GPUs (`nvidia-smi -q -d PERFORMANCE` shows
  `Clocks Throttle Reasons: HW Thermal Slowdown`). For warm-aisle rooms,
  use XE9780L instead.
- **Liquid XE9780L**: DLC on CPUs, GPUs, and NVSwitch — sustained full
  TGP (1100W × 8 = 8.8 kW GPU + 700W CPU + ~500W system = ~10 kW total)
  even at 30 °C ambient.
- **L variant in IR7000 rack**: 33 kW power shelf @ 54V busbar at the rack
  level — the chassis takes 54 VDC busbar in, no per-chassis AC PSU.

---

## XE9780 vs XE9680 differences worth flagging at audit time

When the same operator manages both chassis families, expect deltas on:

| Probe | XE9680 (SPR/EMR) | XE9780 (Granite Rapids) |
|---|---|---|
| `lscpu` Model name | `Intel(R) Xeon(R) Platinum 8480C` etc | `Intel(R) Xeon(R) 6 6787P` etc |
| `lscpu` UPI speed | 16 GT/s (SPR) / 20 GT/s (EMR) | 24 GT/s |
| `dmidecode` DDR5 | 4800 MT/s (SPR) / 5600 MT/s (EMR) | **6400 MT/s** at 1DPC |
| `nvidia-smi -q` GPU model | `H100 / H200` | `B200` or `B300` |
| GPU `Power Limit` | 700 W | 1000 W (B200) or 1100 W (B300) |
| `nvidia-smi nvlink --status` | NVLink-4 (NV18 = 18 links @ 25 GB/s) | NVLink-5 (NV18 = 18 links @ 50 GB/s) |
| GPU PCIe link | Gen5 x16 | Gen5 x16 (same) |
| `lspci` ConnectX | External NIC slots | Embedded 8× CX-8 OSFP on baseboard (B300 only) |

---

## Sources

- Dell PowerEdge XE9780 Technical Guide (E125S, March 2026):
  https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9780-technical-guide.pdf
- Dell PowerEdge XE AI Spec Sheet (XE9680 / XE9780 / XE9785 / XE9712 cross-comparison):
  https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe-ai-spec-sheet.pdf
- Dell PowerEdge BIOS Performance and Workload Tuning Guide for 16G:
  https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/
- Dell PowerEdge BIOS Performance and Workload Tuning Guide for 16G — Intel section:
  https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/detailed-settings-for-intel-bios-profile/
- 16G PowerEdge Platform BIOS Characterization for HPC with Intel Sapphire Rapids
  (analogous methodology applies to Granite Rapids):
  https://infohub.delltechnologies.com/en-us/p/16g-poweredge-platform-bios-characterization-for-hpc-with-intel-sapphire-rapids/
- Dell PowerEdge XE9780L product page (liquid variant):
  https://www.dell.com/en-us/shop/ipovw/poweredge-xe9780l
