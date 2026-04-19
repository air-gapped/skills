# Dell PowerEdge XE reference

Primary source: [Dell PowerEdge XE AI spec sheet (PDF, rev A04, 2026-03)](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe-ai-spec-sheet.pdf).
The spec sheet covers 11 XE models across multiple families.

## Naming disambiguations (these trip people up)

- **XE9780** exists in both **air-cooled (10U, 12× 3200W PSU)** *and* **liquid-cooled
  (XE9780L / XE9780LAP, 3 OU in IR7000)** variants. They are separate SKUs with
  different form factors.
- **XE9680L in Dell's 2026 portfolio is a 4U B200 liquid-cooled node**, NOT a
  liquid-cooled variant of the 6U XE9680 H100/H200 chassis.
- **XE9712 and XE8712** carry **Blackwell Ultra (B300)** + Grace CPU, not B200/GB200.
  XE9712 is a 19" 1 RU sled in IR9048; XE8712 is a 21" ORv3 1 OU sled in IR7044/IR7050.
- **XE9680 accepts five GPU options** in the same chassis: H100, H200, H20 (China SKU),
  AMD MI300X, Intel Gaudi3.
- **XE9780 / XE9780L / XE9785 / XE9785L all carry the HGX B300 NVL8 (270 GB / 1,100 W)
  bin**, not the DGX-bin (288 GB / 1,400 W). See `gpu-specs.md` §2.

## Flagship Blackwell Ultra / NVL-tray models

| Model | GPUs | CPU | Max DRAM | NVMe | Form | PSU | Cooling |
|---|---|---|---|---|---|---|---|
| **XE9712** | 4× B300 + NVLink-C2C coherent | 2× Grace (72c) | 480 GB LPDDR5X + 288 GB HBM3E/GPU | 8× E1.S (61.44 TB) | 1 RU sled in IR9048 (48 RU rack) | 6× 5500W AC in 33 kW shelf (54 VDC) | Air or DLC |
| **XE8712** | 4× B300 | 2× Grace | 480 GB LPDDR5X + 192 GB HBM3E/GPU | 2× E3.S (15.36 TB) | 1 OU sled in IR7044/IR7050 ORv3 | 6× 5500W AC in 33 kW shelf | **DLC only** |
| **XE9780 (air)** | 8× B300 **270 GB 1100 W** SXM6 **or** 8× B200 180 GB 1000 W SXM6 | 2× Intel Xeon 6 (up to 86c) | 32 DIMM (4 TB) | 16× E3.S (245.76 TB) or 10× U.2 (153.6 TB) | 10U — 439.5 × 482.3 × 1044.7 mm; **163.2 kg** | 12× 3200W Titanium 200–240 VAC / 240 VDC | Air (15 GPU fans hot-swap + 5 CPU fans cold-swap) |
| **XE9780L / XE9780LAP** | 8× B300 **270 GB 1100 W** SXM6 (HGX NVL8 bin) | 2× Xeon 6 (L: 86c, LAP: 128c) | L: 4 TB / LAP: 6 TB | 16× E1.S or 8× U.2+2× CEM | 3 OU in IR7000 | 6× 5500W AC in 33 kW shelf | Liquid (CPU+GPU+NVSwitch) |
| **XE9785L** | 8× AMD MI355X **or** 8× B300 **270 GB 1100 W** SXM6 | 2× EPYC 9005 (up to 192c) | 24 DIMM (6 TB) | 16× E1.S or 8× U.2 | 3 OU in IR7000 | 6× 5500W AC in 33 kW shelf | Liquid |

## 10U / 6U / 4U Hopper & Blackwell nodes

| Model | GPUs | CPU | Max DRAM | Form | PSU | Cooling |
|---|---|---|---|---|---|---|
| **XE9785** | 8× MI355X **or** 8× B300 | 2× EPYC 9005 (up to 192c) | 24 DIMM (6 TB) | 10U | 12× 3200W Titanium | Air |
| **XE9680** | 8× H100/H200/H20 SXM5 **or** 8× MI300X OAM **or** 8× Gaudi3 OAM | 2× Xeon Scalable 4th/5th gen (up to 64c) | 32 DIMM (4 TB) | 6U | 2800/3000/3200W Titanium (config-dependent) | Air |
| **XE9680L** | 8× B200 180GB 1000W SXM6 | 2× Xeon Scalable 5th gen (up to 64c) | 32 DIMM (4 TB) | 4U in IR5000 | 3000W Titanium 200–240 VAC | Liquid |
| **XE9685L** | 8× B200 180GB 1000W SXM6 | 2× EPYC 9005 (up to 192c) | 24 DIMM (3 TB) | 4U in IR5000 | 3000W / 2800W | Liquid |
| **XE8640** | 4× H100 SXM5 | 2× Xeon Scalable 4th/5th gen | (shared row) | 4U (482×901 mm) | 3200W / 2800W | Air CPUs + liquid-assisted-air GPUs |
| **XE9640** | 4× H100 or Intel Max 1550 | 2× Xeon Scalable | 4 TB | 2U (87×482×926 mm) | 2800W | Liquid (internal manifold) |

## PCIe training/inference (XE7000 series)

| Model | GPUs | CPU | Max DRAM | Form | PSU | Cooling |
|---|---|---|---|---|---|---|
| **XE7745** | 8× DW-FHFL 600W (e.g. RTX PRO 6000, H200 NVL, H100 NVL, L40S, L4) | 2× EPYC 9005 (up to 192c) | 24 DIMM (3 TB) | 4U | 3200W / 2900W / 2400W | Air |
| **XE7740** | 8× DW-FHFL 600W — includes Gaudi3 600W option | 2× Xeon 6 (up to 144c) | 32 DIMM (4 TB) | 4U | 3200W / 2900W / 2400W | Air |

## Dell Integrated Rack (IR) products

| Rack | For | Notes |
|---|---|---|
| **IR5000** | XE9680L, XE9685L (4U B200 liquid-cooled nodes) | Standard 19" rack with DLC plumbing |
| **IR7000** (44 OU / 50 OU) | XE9780L, XE9780LAP, XE9785L, XE8712 | ORv3 21"; 33 kW power shelf (6× 5500W @ 54 VDC busbar); **up to ~480 kW per rack with DLC** |
| **IR9048** (48 RU) | XE9712 (1 RU sleds) | Standard 19" width; GB300-class Grace+B300 sleds |

## Max-GPU-TDP budgets per box (8-GPU)

| GPU SKU | TDP/GPU | 8-GPU total |
|---|---:|---:|
| H100 / H200 SXM5 | 700 W | 5.6 kW |
| MI300X OAM | 750 W | 6.0 kW |
| Gaudi3 OAM | 900 W | 7.2 kW |
| B200 SXM6 | 1000 W | 8.0 kW |
| B300 SXM6 — HGX NVL8 bin (Dell/SMC/Lenovo) | 1100 W | 8.8 kW |
| B300 SXM — DGX / GB300 Superchip bin | 1400 W | 11.2 kW |
| MI355X OAM | 1400 W | 11.2 kW |

Use these as the *GPU-only* budget when sizing PSU headroom; add ~30–50% for CPU,
memory, NIC, cooling fans.
