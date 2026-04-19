# GB300 NVL72 — vendor landscape and facility prerequisites

Read this when the operator is sizing a purchase, evaluating a data-center site for
GB300 NVL72 deployment, or comparing vendor offerings. Facility prereqs and buy-or-wait
are the hard parts; vendor selection is secondary.

## 1. Vendor SKUs (GB300 NVL72 rack systems)

| Vendor | Product / SKU | Availability | Notes |
|---|---|---|---|
| **NVIDIA** | DGX GB300 (reference design) | H2 2025 hyperscaler; broader 2026 | MGX rack; 21 TB HBM3E; 130 TB/s NVLink |
| **Dell** | PowerEdge XE9712 in **IR7000**; XE9780L for NVL72-equivalent | Shipping — first GB300 rack to CoreWeave July 2025 | IR7000 DLC up to ~480 kW; 54 VDC busbar |
| **Supermicro** | SRS-GB300-NVL72 (48U) | Shipping; "first-to-market" claim | Hybrid-cooled; DLC-2 captures ~98% of heat to liquid |
| **HPE** | "NVIDIA GB300 NVL72 by HPE" (HPE Store 1014890105); Cray variant positioned separately | Quotable 2026 | HPE Store page access-gated |
| **Lenovo** | ThinkSystem GB300 NVL72 — rack **7DJVCTO2WW** (feature C5RK=6-shelf, C5RJ=8-shelf); compute tray **7DLZCTO2WW**; switch tray **7DJYCTO3WW** | Orderable; product guide Mar 2026 | Primary datapoint for facility numbers — Lenovo publishes detailed specs |
| **Supermicro / QCT / Wiwynn / Foxconn (Ingrasys) / Pegatron / Inventec / Aivres** | Branded GB300 NVL72 assemblies | Varies, mostly 2026 | ODM/hyperscaler channel; few public list-price SKUs |

**Pricing:** GB200 NVL72 baseline ~$3M/rack; **GB300 estimates $3.7M–$6.5M** per rack
(analyst range). Cooling BoM alone ~$50k/rack (Tom's Hardware). No vendor lists prices
publicly.

## 2. Facility prerequisites — the buy-or-not checklist

| Spec | GB200 NVL72 | **GB300 NVL72** | Rubin NVL144 (projected) | Rubin Ultra NVL576 Kyber |
|---|---|---|---|---|
| Nominal power | ~120 kW | **135 kW** | 180–220 kW | ~600 kW |
| Peak power | ~132–140 kW | **up to 155 kW** | >220 kW | 600 kW sustained |
| Flow rate | ~80 LPM @ 20–25 °C | **59 LPM @ 25 °C → 177 LPM @ 45 °C** (Lenovo) | not published | not published |
| Inlet water °C | 20–25 °C typical; 45 °C max | **2–50 °C operating range** (Lenovo); 18–45 °C warm-water | **45 °C (W45)** | 45 °C |
| % heat to liquid | ~85–90% | **~90% liquid / 10% air** (DLC-2 up to 98%) | 100% liquid | 100% liquid |
| DLC mandatory? | Yes | **Yes** — GPUs + CPUs + NVSwitch + CX-8 liquid-cooled; RDHx not viable at 135 kW | Yes | Yes |
| Weight (loaded) | ~1,360 kg | **~1,360–1,590 kg** | heavier | heavier |
| Dims | 48U / 600×2294×1068 mm | **48U / 600×2294×1068 mm** (Lenovo) | MGX 48U | Kyber — different form |
| Input supply | 3φ 415/480 V | **200–277 VAC single-phase, 3φ 346–480 VAC WYE**; ORv3 33 kW shelves (6× 5.5 kW PSUs / shelf → 48/54 VDC busbar) | Transitioning to **800 VDC (±400 V) HVDC** | 800 VDC HVDC |
| PSU topology | 4–8× 33 kW shelves | **Up to 8× 33 kW shelves**; Dell=54 VDC; Lenovo=48 VDC | 33 kW shelves in interim; Kyber=HVDC | HVDC |
| Seismic bracing | ISO/TIA Zone-4 kit | Same | Same | Same |

### Key takeaways

- **DLC is mandatory.** No rear-door-heat-exchanger (RDHx) GB300 NVL72 configuration
  exists. Row-level CDU plumbing is on the critical path.
- **Sizing power: use 155 kW headroom, not 135 kW.** Peak-to-nominal is ~15%.
- **Dell vs Lenovo busbar voltage:** Dell IR7000 uses **54 VDC**, Lenovo uses **48 VDC**.
  Both claim ORv3 compliance but the shipped PSU SKUs differ. Confirm with vendor BoM.
- **Floor load:** 1.5 t/rack often triggers slab re-analysis in older DCs; 1500+ kg/m²
  rating expected.
- **Rubin facilities are a different spec** — 800 VDC HVDC, 45 °C water, 180–220 kW
  (NVL144), 600 kW for Kyber/NVL576. Greenfield rows planned in 2026 should be spec'd
  for Rubin, not GB300, to avoid retrofit.

## 3. Scale-out fabric

- **Scale-up inside the rack:** 72 GPUs / one NVLink5 domain / 130 TB/s all-to-all.
- **Scale-out NIC:** ConnectX-8 SuperNIC, **800 Gb/s per GPU → 72 NICs per rack**.
- **Switch:** Quantum-X800 (Q3400, 144×800 G XDR, 4U, <100 ns, 14.4 TFLOPS SHARP).
- **Pod sizing:** public reference architectures commonly describe **8× GB300 NVL72 +
  3× Quantum-X800 racks + 2× in-row CDU** per SuperCluster unit.
- **Fabric BoM:** rough order $600k–$850k networking per NVL72 → **$5–7M per 8-rack
  pod** in optics/cables/switches alone (excl. storage).
- **NVL576 for Blackwell Ultra does not exist.** NVL576 is a **Rubin Ultra Kyber**
  product (2027). Blackwell-Ultra cross-rack today runs over InfiniBand XDR.

## 4. Public deployments

- **CoreWeave:** first GB300 NVL72 (Dell IR7000), July 2025.
- **Microsoft Azure:** GB300 NVL72 blog September 2025 (custom racks, not vanilla SKU).
- **Oracle OCI:** GB200 NVL72 generally available.
- **Crusoe, Lambda, Nebius:** NCP partners with GB200/GB300 capacity.

## 5. Procurement pain points (ranked by observed slippage)

1. **Row power feeds.** 480 V high-density switchgear is the #1 delay.
2. **CDU plumbing.** Vertiv/Schneider in-row CDUs and manifold piping: 6–9-month
   facility work typical.
3. **33 kW PSU shelves.** Lead times 26–40 weeks reported.
4. **HBM allocation.** Gates all GPU ship dates for 2026.
5. **Floor load.** 1.5 t per rack often triggers slab re-analysis in older DCs.

## 6. Buy-or-wait

- **Buy GB300 in H1 2026 if:** you need capacity in 2026; your site can already deliver
  135–155 kW + 25 °C DLC; you accept ~24-month useful life before Rubin-era $/token
  catches up (analysts cite ~10× lower for Rubin).
- **Wait for Rubin if:** the DC is greenfield anyway — spec for **800 VDC, 220 kW,
  45 °C water, HVDC busbars** now. Retrofitting is expensive.
- **Hybrid (common view):** commit to a GB300 pod in H1 2026 for revenue; concurrently
  spec greenfield rows for Rubin NVL144 (H2 2026–2027). See `rubin-roadmap.md`.

## Sources

[Lenovo GB300 NVL72 product guide (lp2357)](https://lenovopress.lenovo.com/lp2357-lenovo-nvidia-gb300-nvl72-rack-scale-ai) ·
[Lenovo GB300 NVL72 datasheet (ds0207)](https://lenovopress.lenovo.com/datasheet/en-us/ds0207-lenovo-nvidia-gb300-nvl72) ·
[NVIDIA GB300 NVL72 product page](https://www.nvidia.com/en-us/data-center/gb300-nvl72/) ·
[NVIDIA DGX B300 datasheet](https://resources.nvidia.com/en-us-dgx-systems/dgx-b200-datasheet) ·
[NVIDIA DGX SuperPOD B300 RA](https://docs.nvidia.com/pdf/dgx-spod-gb300-ra.pdf) ·
[Supermicro SRS-GB300-NVL72](https://www.supermicro.com/en/products/system/gpu/48u/srs-gb300-nvl72) ·
[Dell + CoreWeave first GB300 NVL72 (STH)](https://www.servethehome.com/dell-and-coreweave-show-off-first-nvidia-gb300-nvl72-rack/) ·
[TweakTown — IR7000 480 kW](https://www.tweaktown.com/news/101839/) ·
[Sunbird DCIM — GB300 power](https://www.sunbirddcim.com/blog/how-much-power-does-nvidia-gb300-nvl72-need) ·
[Introl — B300 infra requirements](https://introl.com/blog/nvidia-blackwell-ultra-b300-infrastructure-requirements-2025) ·
[Tom's — $50k cooling BoM](https://www.tomshardware.com/pc-components/cooling/cooling-system-for-a-single-nvidia-blackwell-ultra-nvl72-rack-costs-a-staggering-usd50-000-set-to-increase-to-usd56-000-with-next-generation-nvl144-racks) ·
[DCD — 1 MW racks / 800 VDC](https://www.datacenterdynamics.com/en/news/nvidia-prepares-data-center-industry-for-1mw-racks-and-800-volt-dc-power-architectures/) ·
[CoreWeave GB200 GA](https://www.coreweave.com/news/coreweave-first-cloud-provider-to-announce-general-availability-of-nvidia-gb200-nvl72-instances) ·
[Microsoft Azure GB300 NVL72](https://techcommunity.microsoft.com/blog/azureinfrastructureblog/reimagining-ai-at-scale-nvidia-gb300-nvl72-on-azure/4464556) ·
[Wiwynn GTC 2025](https://www.wiwynn.com/news/wiwynn-showcases-ai-servers-featuring-nvidia-gb300-nvl72-platform-and-liquid-cooling-innovations-at-gtc-2025) ·
[LMSYS/SGLang GB300 benchmarks](https://www.lmsys.org/blog/2026-02-20-gb300-inferencex/).
