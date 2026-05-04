# Dell PowerEdge XE9680 — chassis-specific tuning

Concrete BIOS settings, slot↔CPU map, and known-quirk notes for the Dell
XE9680 6U chassis with 8× H100/H200/H800 SXM5 GPUs. Distilled from Dell's
PowerEdge BIOS Performance and Workload Tuning Guide for 16G plus the 2025-09
Technical Guide (E90S regulatory model).

For sibling chassis: XE9680L (4U B200 liquid), XE9785 (10U B300 air),
XE9785L (3 OU B300 liquid), XE9780/XE9780L (10U / 3 OU B300 air/liquid),
XE9712 (1 RU GB300 sled). The PCIe layout differs; see vendor docs.

---

## Hardware summary

| Subsystem | XE9680 |
|---|---|
| Form factor | 6U air-cooled |
| GPUs | 8× HGX H100/H200/H800 SXM5 (700 W each, NVLink mesh via NVSwitch) |
| GPU options | NVIDIA HGX A100/H100/H200/H20, AMD MI300X OAM, Intel Gaudi3 OAM |
| CPUs | 2× Intel Xeon Scalable, **either** 4th gen Sapphire Rapids (≤56c, DDR5-4800) **or** 5th gen Emerald Rapids (≤64c, DDR5-5600) |
| PCIe per CPU | 80× Gen5 lanes integrated |
| UPI | 4× per socket @ 16 GT/s (SPR) or 20 GT/s (EMR) |
| DIMMs | 32 total (16/socket × 8 channels × 2 DPC) |
| Max memory | 4 TB |
| PCIe expansion | 10× Gen5 x16 slots (8 on PSB, 2 on PBB) |

---

## PCIe slot ↔ CPU map (from Dell's PCIe slot mechanical compatibility matrix)

```
Slot 31 (PBB) → Processor 2     [SmartNIC/DPU; high-power supported]
Slot 32 (RS4) → Processor 2
Slot 33 (RS4) → Processor 2     [blocked when Gaudi3 GPUs installed]
Slot 34 (RS3) → Processor 2
Slot 35 (RS3) → Processor 2
Slot 36 (RS2) → Processor 1
Slot 37 (RS2) → Processor 1
Slot 38 (RS1) → Processor 1     [blocked when Gaudi3 GPUs installed]
Slot 39 (RS1) → Processor 1
Slot 40 (PBB) → Processor 1     [SmartNIC/DPU; high-power supported]
```

PSB = PCIe Switch Board; PBB = PCIe Base Board.

### GPU ↔ CPU NUMA mapping (HGX-8 standard wiring)

The 8× SXM5 baseboard splits into two halves; the XE9680 follows the
universal HGX-8 convention:

```
GPU0–GPU3  →  2 PCIe Gen5 switches  →  CPU 0  (NUMA node 0)
GPU4–GPU7  →  2 PCIe Gen5 switches  →  CPU 1  (NUMA node 1)
```

Confirm via `nvidia-smi topo -m`:
- GPU NUMA Affinity column should show `0` for GPU0–3 and `1` for GPU4–7
- All `0` = NUMA disabled in BIOS (`Sub-NUMA Clustering = Disabled` AND
  `NUMA = Disabled`) OR you're inside a virt guest.
- `N/A` for all = numa subsystem not enabled in kernel (rare on 24.04+).

NVSwitch mesh on the baseboard means GPU-to-GPU traffic stays at 900 GB/s
regardless of socket; only CPU↔GPU traffic crosses UPI when "wrong-side."

### NIC placement — match the workload

For a 4-NIC config doing GPUDirect RDMA to all 8 GPUs:
- Slots 38, 39 → Processor 1 → near GPUs 0-3 (place 2 NICs here for the
  "left" half)
- Slots 31, 32 → Processor 2 → near GPUs 4-7 (place 2 NICs here for the
  "right" half)

Set NCCL `NCCL_IB_HCA` ordering to match this physical layout so each rank
uses its near NIC.

---

## BIOS settings — recommended for inference

Reach via iDRAC virtual console or F2 at boot. Path: `System BIOS Settings`.

### System Profile Settings (top-level preset)

```
System Profile         = Performance
Workload Profile       = AI/ML Optimized          (when shown — XE9680 BIOS 2.0+)
                         OR  HPC Profile  (older BIOS)
```

`Performance` overrides all sub-settings to performance-biased defaults.
`Custom` if you want to override individual sub-levers.

### Processor Settings

```
Logical Processor      = Enabled                  # Hyper-Threading on
CPU Power Management   = Maximum Performance
                          (alternates: OS DBPM, System DBPM, Node Manager)
C States               = Disabled
                          OR Limited to C1  (preserves some idle savings, safe for inference)
C1E                    = Disabled
Turbo Boost            = Enabled
Energy Efficient Turbo = Disabled
Sub NUMA Cluster (SNC) = Disabled
                          (or SNC2 = "Hemisphere mode" with 2 NUMA nodes per socket;
                          inference workloads spanning all 8 GPUs simpler with SNC off)
Hardware Prefetcher    = Enabled
Adjacent Cache Line Prefetch = Enabled
DCU Streamer Prefetcher = Enabled
DCU IP Prefetcher      = Enabled
LLC Prefetch           = Enabled
X2APIC Mode            = Enabled
Uncore Frequency Scaling = Enabled
                          OR  Maximum  (locks uncore at peak — adds power, lowers latency variability)
```

### Memory Settings

```
Memory Operating Mode  = Optimizer Mode           (max bandwidth — vs Mirror/Sparing)
Memory Patrol Scrub    = Disabled                 (lowers DDR5 idle traffic)
                          (downside: slow background ECC scrub disabled — uncorrectable
                          errors revealed only at access. Production tradeoff.)
Memory Refresh Rate    = 1x                       (2x halves bandwidth, only needed at extreme temps)
Snoop Mode             = Home Snoop with Directory and Op State (HSDOS)
                          OR  Home Directory Snoop with OS (HDOS)
Memory Frequency       = Maximum Performance
                          (allows full DDR5-4800/5600 — auto sometimes caps for stability)
DIMM Self Healing      = Enabled                  (post-package repair, rare events)
```

### System Profile Settings (sub-pane)

```
CPU Power Management        = Maximum Performance
Memory Frequency            = Maximum Performance
Turbo Boost                 = Enabled
C1E                         = Disabled
C States                    = Disabled
Energy Efficient Turbo      = Disabled
Monitor/Mwait               = Enabled            (required for OS C-state control)
Workload Profile            = AI/ML / HPC
CPU Interconnect Bus Speed  = Maximum Performance
PCIe ASPM L1 Link Power Management = Disabled
```

### Integrated Devices

```
SR-IOV Global Enable        = Enabled  (if you'll use VFIO passthrough)
Memory Mapped I/O above 4GB = Enabled  (REQUIRED for GPU BAR allocation)
                                       Note: Resizable BAR may need a separate toggle
Slot Disablement            = Slots 31-40 Enabled  (don't accidentally disable any)
```

### Boot Settings

```
Boot Mode                   = UEFI                # required for >2TB drives
Secure Boot                 = your call (NVIDIA driver works either way)
```

---

## Common XE9680 quirks observed in the field

| Symptom | Cause | Fix |
|---|---|---|
| GPU `Power Limit` shows 600W instead of 700W | `Processor Settings → CPU Power Cap` is on | Disable, or raise to per-GPU limit |
| `nvidia-smi topo -m` all NUMA = N/A | `Memory NUMA = Disabled` in BIOS | Enable; reboot |
| One GPU LnkSta = Gen4 x16, others Gen5 x16 | Cabling on the SXM5 board, or the NVSwitch detected one side as Gen4 | Reseat baseboard cables; cold-boot (not warm reset) |
| Slot 33 / 38 unusable | XE9680-Gaudi3 thermal-airflow blocking | Replace with H200 GPUs OR accept 8-slot config |
| dmidecode shows DDR5-4800 with EMR Xeon | EMR + 1DPC supports DDR5-5600; 2DPC drops to 4800 | Verify: 16 DIMMs/socket = 1DPC. If 32 DIMMs/socket = 2DPC and that's the cap. |
| iDRAC reports correctable ECC errors steadily | Patrol Scrub finding accumulated bit-flips | Watch trend; > 100/day = replace DIMM identified by error log |

---

## XE9680 + nvidia-tuned-profiles

`nvidia-tuned-profiles` ships profiles for DGX, not XE9680. Either:

a) Install on the box and use `accelerator-performance` (Red Hat generic
   GPU profile), then layer your own custom profile.

b) Author `/etc/tuned/dell-xe9680-h200/tuned.conf` per the template in
   `tuned-profiles.md`, including:
   ```ini
   [main]
   summary=Dell XE9680 + 8×H200 SXM5
   include=throughput-performance

   [bootloader]
   cmdline=iommu=pt default_hugepagesz=1G hugepagesz=1G hugepages=64 init_on_alloc=0 pci=realloc=off pcie_aspm=off
   # XE9680 BIOS sometimes presents pcie root ports differently than DGX —
   # the pci=realloc=off arg is genuinely useful here per NVIDIA recommendation.
   ```

The audit's `42_cmdline.txt` after applying should show all the cmdline args.

---

## Per-CPU-bin DDR5 expectations

Use these to sanity-check `12_dmidecode_memory.txt` `Configured Memory Speed`:

| Xeon SKU | Generation | Max DDR5 (1DPC) | At 2DPC |
|---|---|---|---|
| 8480C | Sapphire Rapids (4th) | 4800 MT/s | 4400 MT/s |
| 8470 | SPR | 4800 | 4400 |
| 8462Y+ | SPR | 4800 | 4400 |
| 8580 / 8580+ | Emerald Rapids (5th) | 5600 | 4800 |
| 8570 | EMR | 5600 | 4800 |
| 6526Y / 6530 / 6540Y | EMR | 5200 | 4400 |

If you see less, BIOS is capping or DIMM SPD/Manufacturer mismatch. Aggregate
2-socket memory bandwidth at full-pop:

- SPR 4800 × 8 ch × 2 sock × 8 B = ~614 GB/s
- EMR 5600 × 8 ch × 2 sock × 8 B = ~717 GB/s

This is the host-side ceiling that LMCache CPU-tier writes share with all
8 GPUs concurrently.

---

## Cooling notes

- Air-cooled XE9680 has 15 hot-swap GPU fans + 5 cold-swap CPU fans.
- Inlet temp >35 °C will cause GPU clocks to throttle — `nvidia-smi -q -d
  PERFORMANCE` shows `Clocks Throttle Reasons` `HW Thermal Slowdown`.
- Watch `2A_thermal.txt` zones; pkg temp >85 °C under load = cooling
  issue (chassis full of dust, fan FRU failed, or rack hot aisle issue).
- For Dell rooms running 95 °F (35 °C) inlet by design, consider XE9680L
  (4U liquid) — same 8× B200 SXM6 budget but DLC keeps GPU consistent
  under heavy load.

---

## Sources

- Dell PowerEdge XE9680 Technical Guide (E90S, Sept 2025):
  https://www.delltechnologies.com/asset/en-ca/products/servers/technical-support/poweredge-xe9680-technical-guide.pdf
- Dell PowerEdge BIOS Performance and Workload Tuning Guide for 16G:
  https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/
- Dell PowerEdge XE9680 Installation and Service Manual:
  https://www.dell.com/support/manuals/en-us/poweredge-xe9680/xe9680_ism_pub/
- StorageReview — Dell PowerEdge XE9680: The Ultimate AI Powerhouse:
  https://www.storagereview.com/review/dell-poweredge-xe9680-the-ultimate-ai-powerhouse
