# Sources — dated index for `freshen` mode

Authoritative refs cited across this skill, with last-verified dates so
`/skill-improver freshen gpu-host-tuning` can probe staleness.

**Verification methodology.** `Last verified` = fresh probe today (`gh api`
release/commit, `WebFetch` page check). For URLs behind anti-bot walls
(infohub.delltechnologies.com, intel.com download pages,
enterprise-support.nvidia.com SPA) the URL is structurally valid and the
content was confirmed at skill authoring; freshen mode flags these as
`unverifiable` if WebFetch is the only probe surface.

## NVIDIA tooling and docs

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://github.com/NVIDIA/nvbandwidth | host↔device + multinode bandwidth bench | 2026-05-04 | v0.9 | release tag v0.9 (2026-04-08) |
| https://github.com/NVIDIA/nccl-tests | NCCL all-reduce / all-gather perf tests | 2026-05-04 | NCCL_TESTS_VERSION 2.18.3 | latest commit 2026-04-13 |
| https://docs.nvidia.com/dgx/dgx-el10-user-guide/modifying-tuned.html | DGX TuneD profile catalog (a100/h100/h200/h800/b200/b300, base + crashdump) | 2026-05-04 | DGX EL 10 | page last updated 2026-04-13 |
| https://enterprise-support.nvidia.com/s/article/bios-performance-tuning-example | NVIDIA BIOS performance tuning example | 2026-05-04 | — | live; SPA — WebFetch returns CSS error, browser-only |
| https://enterprise-support.nvidia.com/s/article/understanding-bios-configuration-for-performance-tuning | NVIDIA BIOS configuration guide | 2026-05-04 | — | live; SPA — WebFetch returns CSS error, browser-only |

## Distro / OS docs

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-tuning-tuned.html | SLES 15 SP7 — TuneD chapter | 2026-05-04 | SLES 15 SP7 | live |

## Dell PowerEdge XE chassis docs

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://www.delltechnologies.com/asset/en-ca/products/servers/technical-support/poweredge-xe9680-technical-guide.pdf | XE9680 Technical Guide | 2026-05-04 | E90S, 2025-09 | PDF, 5+ MB |
| https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9780-technical-guide.pdf | XE9780 Technical Guide | 2026-05-04 | E125S, 2026-03 | PDF accessible |
| https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe-ai-spec-sheet.pdf | XE AI spec sheet (XE9680/XE9780/XE9785/XE9712 cross-comparison) | 2026-05-04 | — | PDF |
| https://www.dell.com/support/manuals/en-us/poweredge-xe9680/xe9680_ism_pub/ | XE9680 Installation and Service Manual | 2026-05-04 | — | live |
| https://www.dell.com/en-us/shop/ipovw/poweredge-xe9780l | XE9780L product page (liquid variant) | 2026-05-04 | — | live; notes iF Design 2026 award |
| https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/ | 16G BIOS Performance & Workload Tuning Guide | 2026-05-04 | 16G | URL valid; WebFetch returns 403 (anti-bot) |
| https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/detailed-settings-for-intel-bios-profile/ | 16G BIOS Tuning — Intel detailed settings | 2026-05-04 | 16G | URL valid; WebFetch 403 |
| https://infohub.delltechnologies.com/en-us/p/16g-poweredge-platform-bios-characterization-for-hpc-with-intel-sapphire-rapids/ | 16G HPC BIOS characterization (Sapphire Rapids; methodology applies to Granite Rapids) | 2026-05-04 | SPR baseline | URL valid; WebFetch 403 |

## Third-party reviews and tools

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://github.com/wilicc/gpu-burn | gpu-burn stress tool | 2026-05-04 | — | maintenance project; latest commit 2025-11-04 (CUDA 13+ support) |
| https://www.intel.com/content/www/us/en/download/736633/intel-memory-latency-checker-intel-mlc.html | Intel MLC bandwidth/latency tool | 2026-05-04 | MLC v3.x | URL valid; WebFetch 403 (anti-bot) |
| https://www.storagereview.com/review/dell-poweredge-xe9680-the-ultimate-ai-powerhouse | XE9680 third-party review | 2026-05-04 | — | live; published 2024-11-16 |
