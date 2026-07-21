# Vera Rubin roadmap — buy-or-wait inputs

NVIDIA's successor to Blackwell. First HBM4 silicon; first 800 VDC HVDC racks.
Relevant to any 2026+ purchasing decision: facilities built now should be sized for
Rubin, not Blackwell, to avoid retrofit.

**Naming note (2026-04-24):** NVIDIA's own Developer Blog has settled on
"**Vera Rubin NVL72**" as the product name for the first Rubin rack, and states it
is "in full production, on track to ship in the second half of 2026". This supersedes
the earlier GTC-2025 internal codename **VR200 NVL144** used elsewhere in this
reference. When quoting NVIDIA marketing verbatim, use "Vera Rubin NVL72". When
discussing die-count (144 dies = 72 packages) in engineering context, VR200 NVL144
is still the accurate description.

## Shipping status — checked 2026-07-21, inside the claimed window

The "ships H2 2026" line is now testable rather than forward-looking, and the
honest answer is **silicon exists in a customer rack; general delivery has no
date**. Keep those two facts apart — "in production" is a fab statement, not a
delivery statement.

| Evidence | Date | What it actually establishes |
|---|---|---|
| CoreWeave validated a Vera Rubin NVL72 for production use — rack supplied by **Dell**, passed NVIDIA **L11 diagnostics** and a **147-hour** test suite | arrived **2026-05-31** | Real racks exist and pass qualification. First such validation publicly claimed. |
| Jensen Huang, Tokyo developer event: *"Vera Rubin is already in production. Giant amounts of production incoming."* | **2026-07-15** | NVIDIA denying press reports of a manufacturing delay. No public transcript; no fiscal-quarter or revenue-timing statement accompanied it. |
| NVIDIA guidance | — | Still only "partner products in the second half of 2026". **No customer-delivery date has been given.** |
| First-cohort clouds named in coverage | H2 2026 | AWS, Azure, Google Cloud, Oracle, CoreWeave, Lambda, Nebius, Nscale. OEM channel (Dell, HPE, Lenovo, Supermicro) targeted 2H 2026; broad availability reported as 2027. |
| Reported risk | 2026-07 | A KeyBanc analyst flagged a possible **heat-lid qualification issue with SK hynix memory**. Unconfirmed; treat as rumour, not schedule. |

**Reading it for a buy-or-wait call:** "in production" does not mean partners
have finished rack assembly, cooling, and deployment validation. The signal
worth waiting for is an OEM listing NVL72 systems with **firm order dates** —
that is the first evidence that maps to a delivery you could plan around.

**And the engine is behind the hardware.** As of vLLM **v0.25.1** (2026-07-14)
there is **no Rubin support**: zero "Rubin" hits in the issue tracker, and the
build scripts target only `sm_90 / sm_100 / sm_103 / sm_110 / sm_120 / sm_121`.
`sm_110` is **Thor**, not Rubin — vLLM's own build comments group it with
Blackwell. Anyone sizing a Rubin purchase on vLLM should treat day-one serving
support as unevidenced, not assumed. See `references/vllm-platform-matrix.md`.

## Per-GPU specs

| Product | HBM | BW | FP4 | FP8 | Rack product | Rack power | Status |
|---|---:|---:|---:|---:|---|---:|---|
| **R100 (Rubin)** | 288 GB HBM4 (8 stacks) | ~20 TB/s (CES 2026 revision) | 50 PFLOPS | ~16 PFLOPS | **Vera Rubin NVL72** (aka VR200 NVL144, 144 dies / 72 packages) | **180–220 kW** | **In full production** (NVIDIA, Apr 2026); shipping H2 2026 |
| **R300 (Rubin Ultra)** | **1 TB HBM4E** (16 stacks) | TBD | 100 PFLOPS | TBD | **NVL576 Kyber** | **~600 kW** | H2 2027 |

**Rubin BW revision:** initial GTC March 2025 announcement cited 13 TB/s; NVIDIA
revised at CES 2026 to ~20 TB/s to exceed AMD MI455X. Plan against the higher figure.

## Rack products

- **VR200 NVL144 (MGX rack):** 144 Rubin GPU *dies* (= 72 packages) per rack. NVIDIA
  claims 3.6 EFLOPS FP4 inference / 1.2 EFLOPS FP8 training — **3.3× GB300**.
  75 TB fast memory, 260 TB/s NVLink, 28.8 TB/s CX-9 per rack.
- **Kyber NVL576:** 576 dies (144 quad-die Rubin Ultra packages). 15 EFLOPS FP4 /
  5 EFLOPS FP8 — **14× GB300**. New form factor: cable-free midplane, vertically
  rotated blades (18/chassis), NVL7 switches.

## Infrastructure delta vs GB300 — facilities have to be different

- **+60% rack power** (NVL144 at 180–220 kW vs GB300 at 135 kW).
- **Transition to 800 VDC (±400 V) HVDC** busbars; 33 kW ORv3 shelves (48/54 VDC)
  won't carry over.
- **Warmer water:** 45 °C W45 design vs 20–25 °C typical GB300 operation.
- **New MGX NVL144 mechanicals** — physically different rack spec from GB300's
  NVL72 frame.
- **Kyber is another step change** — 600 kW/rack, liquid-cooled busbar, new blade form.

A facility sized for 135 kW GB300 **will not** host NVL144 without power/cooling upgrades.

## Pricing signals

- Rubin NVL72 racks reportedly up to **$8.8M** (Tom's Hardware, citing analysts) —
  ~2–3× GB300 (~$3.7M–$6.5M).

## Buy-or-wait (Rubin)

- **Buy GB300 NVL72 in H1–Q2 2026 if:** you need capacity in 2026 (Rubin partner
  availability is H2 2026; real volume Q4 2026 / H1 2027); your site can already
  deliver 135–155 kW + 25 °C DLC; you accept a ~24-month useful life before Rubin-era
  $/token catches up (analysts cite ~10× lower for Rubin).
- **Wait for Rubin if:** DC is greenfield anyway — spec for **800 VDC, 220 kW racks,
  45 °C water, HVDC busbars** now. Retrofitting later is expensive.
- **Hybrid play (common SemiAnalysis view):** commit to a GB300 pod in H1 2026 for
  revenue; concurrently spec greenfield rows for Rubin NVL144 (H2 2026–2027).

Sources:
[NVIDIA Vera Rubin Pod](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/),
[SemiAnalysis — Rubin Extreme Co-Design](https://newsletter.semianalysis.com/p/vera-rubin-extreme-co-design-an-evolution),
[SemiAnalysis — GTC 2025 Rubin/Kyber](https://newsletter.semianalysis.com/p/nvidia-gtc-2025-built-for-reasoning-vera-rubin-kyber-cpo-dynamo-inference-jensen-math-feynman),
[The Register — 600 kW racks, 800 VDC](https://www.theregister.com/2025/03/19/nvidia_charts_course_for_600kw/),
[Tom's — Rubin $8.8M](https://www.tomshardware.com/tech-industry/artificial-intelligence/price-of-nvidias-vera-rubin-nvl72-racks-skyrockets-to-as-much-as-usd8-8-million-apiece-but-server-makers-margins-will-be-tight-nvidia-is-moving-closer-to-shipping-entire-full-scale-systems),
[Glenn Lockwood — Kyber architecture](https://www.glennklockwood.com/garden/Kyber),
[DCD — 1 MW racks / 800 VDC](https://www.datacenterdynamics.com/en/news/nvidia-prepares-data-center-industry-for-1mw-racks-and-800-volt-dc-power-architectures/).
