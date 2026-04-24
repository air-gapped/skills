# Consolidated source list

Grouped by topic. `foundational` tags mean the source pre-dates 2025 but is still the
canonical reference on its claim.

**Last freshen pass:** 2026-04-24. Rows annotated with `[LV: 2026-04-24]` were probed
in that pass; `[LV: 2026-04-24, drift]` means the probe surfaced a material change that
was applied to the relevant reference file(s). Unannotated rows are inherited from
prior passes (pre-2026-04-24) and have not been re-verified in this pass.

## Fundamentals / HBM / supply / energy

- [arXiv 2512.01644 — Systematic roofline characterization (2025-12)](https://arxiv.org/html/2512.01644v1)
- [arXiv 2402.16363 — LLM Inference Unveiled (foundational)](https://arxiv.org/pdf/2402.16363)
- [Towards Data Science — Prefill/Decode](https://towardsdatascience.com/prefill-is-compute-bound-decode-is-memory-bound-why-your-gpu-shouldnt-do-both/)
- [SemiAnalysis — Memory Wall (2024-09, foundational)](https://semianalysis.com/2024/09/03/the-memory-wall/)
- [SemiAnalysis — HBM rise and roadmap](https://newsletter.semianalysis.com/p/scaling-the-memory-wall-the-rise-and-roadmap-of-hbm)
- [SemiAnalysis — Tensor core evolution Volta→Blackwell](https://newsletter.semianalysis.com/p/nvidia-tensor-core-evolution-from-volta-to-blackwell)
- [NotebookCheck — SK hynix sold out 2026](https://www.notebookcheck.net/SK-hynix-sells-out-its-DRAM-NAND-and-HBM-chip-supply-to-Nvidia-through-2026-as-AI-demand-outpaces-Samsung-and-Micron-s-capacity.1151402.0.html)
- [Astute — HBM market share](https://www.astutegroup.com/news/general/sk-hynix-holds-62-of-hbm-micron-overtakes-samsung-2026-battle-pivots-to-hbm4/)
- [Network World — 2026 memory shortage](https://www.networkworld.com/article/4113772/samsung-warns-of-memory-shortages-driving-industry-wide-price-surge-in-2026)
- [Introl — AI Memory Supercycle](https://introl.com/blog/ai-memory-supercycle-hbm-2026)
- [Future of Computing — Breaking the Memory Wall pt 2](https://news.future-of-computing.com/p/breaking-the-memory-wall-pt-2-a-closer-look-at-hbm-high-bandwidth-memory)
- [NVIDIA HPCA 2017 — Energy-efficient DRAM (foundational)](https://research.nvidia.com/sites/default/files/pubs/2017-02_Architecting-an-Energy-Efficient/chatterjee.hpca2017.pdf)

## NVIDIA hardware

- [H100 datasheet](https://resources.nvidia.com/en-us-tensor-core/nvidia-tensor-core-gpu-datasheet)
- [H200 datasheet](https://nvdam.widen.net/s/nb5zzzsjdf/hpc-datasheet-sc-nvidia-h200-datasheet-nvidia-us)
- [HGX product brief](https://www.nvidia.com/en-us/data-center/hgx/)
- [Hopper in-depth](https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/)
- [AnandTech — H100 NVL](https://www.anandtech.com/show/18781/nvidia-announces-h100-nvl-max-memory-server-card-for-large-language-models)
- [Blackwell architecture page](https://www.nvidia.com/en-us/data-center/technologies/blackwell-architecture/)
- [GB200 NVL72](https://www.nvidia.com/en-us/data-center/gb200-nvl72/)
- [GB300 NVL72](https://www.nvidia.com/en-us/data-center/gb300-nvl72/) **[LV: 2026-04-24]** — page live, status "Available Now"; NVIDIA markets 20 TB HBM (we report 20.7 TB detailed), 130 TB/s NVLink, 576 TB/s aggregate HBM BW. No per-rack power on the page itself.
- [Blackwell Ultra datasheet](https://resources.nvidia.com/en-us-blackwell-architecture/blackwell-ultra-datasheet) **[LV: 2026-04-24, unverifiable]** — URL behind NVIDIA cookie gate; full PDF contents could not be re-read via WebFetch. Content inherited from prior pass; re-verify via a browser session if making sizing calls.
- [DGX B200 datasheet](https://resources.nvidia.com/en-us-dgx-systems/dgx-b200-datasheet)
- [DGX SuperPOD B300 RA](https://docs.nvidia.com/pdf/dgx-spod-gb300-ra.pdf)
- [Inside Blackwell Ultra blog](https://developer.nvidia.com/blog/inside-nvidia-blackwell-ultra-the-chip-powering-the-ai-factory-era/)
- [NVFP4 blog](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/)
- [Quantum-X800 docs](https://docs.nvidia.com/networking/nvidia-quantum-x800-xdr-clusters/index.html)
- [Vera Rubin Pod dev blog](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/) **[LV: 2026-04-24, drift]** — NVIDIA now officially names the first rack product "Vera Rubin NVL72" (not "VR200 NVL144"); blog states it is "in full production, on track to ship in the second half of 2026". Rubin-roadmap reference patched accordingly.
- [SemiAnalysis — Rubin extreme co-design](https://newsletter.semianalysis.com/p/vera-rubin-extreme-co-design-an-evolution)
- [SemiAnalysis — GTC 2025 Rubin/Kyber](https://newsletter.semianalysis.com/p/nvidia-gtc-2025-built-for-reasoning-vera-rubin-kyber-cpo-dynamo-inference-jensen-math-feynman)
- [Glenn Lockwood — Kyber](https://www.glennklockwood.com/garden/Kyber)
- [Tom's — B300 announcement](https://www.tomshardware.com/pc-components/gpus/nvidia-announces-blackwell-ultra-b300-1-5x-faster-than-b200-with-288gb-hbm3e-and-15-pflops-dense-fp4)
- [Tom's — 1400 W B300 TDP](https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidias-next-gen-b300-gpus-have-1400w-tdp-deliver-50-percent-more-ai-horsepower-report)
- [Tom's — Rubin $8.8M](https://www.tomshardware.com/tech-industry/artificial-intelligence/price-of-nvidias-vera-rubin-nvl72-racks-skyrockets-to-as-much-as-usd8-8-million-apiece-but-server-makers-margins-will-be-tight-nvidia-is-moving-closer-to-shipping-entire-full-scale-systems)
- [Tom's — $50k cooling BoM](https://www.tomshardware.com/pc-components/cooling/cooling-system-for-a-single-nvidia-blackwell-ultra-nvl72-rack-costs-a-staggering-usd50-000-set-to-increase-to-usd56-000-with-next-generation-nvl144-racks)
- [Register — 600 kW racks](https://www.theregister.com/2025/03/19/nvidia_charts_course_for_600kw/)
- [DCD — 1 MW racks / 800 VDC](https://www.datacenterdynamics.com/en/news/nvidia-prepares-data-center-industry-for-1mw-racks-and-800-volt-dc-power-architectures/)
- [Wikipedia — Blackwell microarch](https://en.wikipedia.org/wiki/Blackwell_(microarchitecture))
- [TweakTown — B100 cancelled](https://www.tweaktown.com/news/100083/analyst-nvidia-has-effectively-canceled-b100-ai-gpu-over-design-flaw-b200-to-replace-it/index.html)
- [Modal — Decoding Blackwell](https://modal.com/blog/nvidia-blackwell)

## Dell, OEMs, integrated racks

- [Dell PowerEdge XE spec sheet (PDF)](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe-ai-spec-sheet.pdf) **— primary for all Dell specs** **[LV: 2026-04-24, unverifiable]** — URL still live, but WebFetch only retrieved the PDF binary without extractable text on this pass. Rev A04 (2026-03) content inherited; confirm per-SKU availability directly in the PDF if making a purchase call.
- [Dell XE9712 spec sheet](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9712-spec-sheet.pdf)
- [Lenovo GB300 NVL72 product guide lp2357](https://lenovopress.lenovo.com/lp2357-lenovo-nvidia-gb300-nvl72-rack-scale-ai)
- [Lenovo GB300 NVL72 datasheet ds0207](https://lenovopress.lenovo.com/datasheet/en-us/ds0207-lenovo-nvidia-gb300-nvl72)
- [Lenovo HGX B200 180 GB lp2226](https://lenovopress.lenovo.com/lp2226-thinksystem-nvidia-b200-180gb-1000w-gpu)
- [Supermicro GB300 NVL72 product](https://www.supermicro.com/en/products/system/gpu/48u/srs-gb300-nvl72)
- [Supermicro GB200 NVL72 PDF](https://www.supermicro.com/datasheet/datasheet_SuperCluster_GB200_NVL72.pdf)
- [Supermicro GB300 NVL72 PDF](https://www.supermicro.com/datasheet/datasheet_SuperCluster_GB300_NVL72.pdf)
- [HPE Store — GB300 NVL72 by HPE](https://buy.hpe.com/us/en/compute/rack-scale-system/nvidia-nvl-system/nvidia-gb300-nvl72-by-hpe/p/1014890105)
- [Wiwynn GTC 2025](https://www.wiwynn.com/news/wiwynn-showcases-ai-servers-featuring-nvidia-gb300-nvl72-platform-and-liquid-cooling-innovations-at-gtc-2025)
- [STH — first GB300 NVL72](https://www.servethehome.com/dell-and-coreweave-show-off-first-nvidia-gb300-nvl72-rack/)
- [TweakTown — IR7000 480 kW](https://www.tweaktown.com/news/101839/)
- [Sunbird DCIM — GB300 power](https://www.sunbirddcim.com/blog/how-much-power-does-nvidia-gb300-nvl72-need)
- [Introl — B300 infra requirements](https://introl.com/blog/nvidia-blackwell-ultra-b300-infrastructure-requirements-2025)

## Mitigations (algorithms)

- [DeepSeek-V2 MLA](https://arxiv.org/abs/2405.04434)
- [DeepSeek-V3](https://arxiv.org/abs/2412.19437)
- [EAGLE-3](https://arxiv.org/abs/2503.01840)
- [Mooncake (FAST 2025)](https://arxiv.org/abs/2407.00079)
- [vLLM paged attention (SOSP 2023, foundational)](https://arxiv.org/abs/2309.06180)
- [AWQ (MLSys 2024, foundational)](https://arxiv.org/abs/2306.00978)
- [Transformer Engine docs](https://docs.nvidia.com/deeplearning/transformer-engine/user-guide/examples/fp8_primer.html)

## vLLM releases

- [v0.10.2](https://github.com/vllm-project/vllm/releases/tag/v0.10.2)
- [v0.11.0](https://github.com/vllm-project/vllm/releases/tag/v0.11.0)
- [v0.11.1](https://github.com/vllm-project/vllm/releases/tag/v0.11.1)
- [v0.12.0](https://github.com/vllm-project/vllm/releases/tag/v0.12.0)
- [v0.19.0](https://github.com/vllm-project/vllm/releases/tag/v0.19.0) **[LV: 2026-04-24]** — published 2026-04-03. First-class B300/GB300 (SM 10.3); cu130 wheels; FlashInfer sparse MLA default for FP8 KV cache.
- [v0.19.1](https://github.com/vllm-project/vllm/releases/tag/v0.19.1) **[LV: 2026-04-24, new-feature]** — published 2026-04-18. Current **latest stable**. Ships `transformers>=5` compat.
- [v0.20.0](https://github.com/vllm-project/vllm/releases/tag/v0.20.0) **[LV: 2026-04-24, new-feature]** — pre-release 2026-04-23. **CUDA 13.0 default** (breaking env change), PyTorch 2.11, **FlashAttention 4 as default MLA prefill** (SM90+ paged-KV), TurboQuant 2-bit KV cache (4× capacity), MXFP4 W4A4 CUTLASS MoE SM100, TRTLLM GEN NVFP4 MoE non-512-aligned hidden dims, tuned fused_moe config for RTX PRO 6000 Blackwell. Mentioned for planning; platform-matrix recommends pinning v0.19.1 until v0.20.0 leaves pre-release.
- [NVIDIA vLLM release notes 25.09](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/rel-25-09.html)

## Public deployments / benchmarks

- [CoreWeave GB200 NVL72 GA](https://www.coreweave.com/news/coreweave-first-cloud-provider-to-announce-general-availability-of-nvidia-gb200-nvl72-instances)
- [Oracle OCI GB200 NVL72 (DCD)](https://www.datacenterdynamics.com/en/news/nvidia-gb200-nvl72-now-available-via-oracle-cloud/)
- [Microsoft Azure GB300 NVL72](https://techcommunity.microsoft.com/blog/azureinfrastructureblog/reimagining-ai-at-scale-nvidia-gb300-nvl72-on-azure/4464556)
- [LMSYS / SGLang GB300 benchmarks](https://www.lmsys.org/blog/2026-02-20-gb300-inferencex/)
- [TrendForce — GTC 2025 Blackwell/Rubin](https://www.trendforce.com/research/download/RP250319GB)

## Upstream bug trackers

- [flashinfer-ai/flashinfer#2939 — TRTLLM attention hang on GB300 (SM103) with FlashInfer 0.6.7](https://github.com/flashinfer-ai/flashinfer/issues/2939) **[LV: 2026-04-24, drift]** — **Closed 2026-04-07** as fixed via PR #2956 (@PerkzZheng). Fix shipped in a 0.6.7.postN (verify the exact tag before pinning). vllm-platform-matrix reference patched from "open, pin older FlashInfer" to "fixed — upgrade".
