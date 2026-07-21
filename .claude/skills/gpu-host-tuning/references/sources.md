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
| https://github.com/NVIDIA/nvbandwidth | host↔device + multinode bandwidth bench | 2026-07-21 | v0.9 | v0.9 (2026-04-08) still latest; NVIDIA-recommended replacement for the removed cuda-samples `bandwidthTest` (dropped in cuda-samples v13.0) |
| https://github.com/NVIDIA/nccl-tests | NCCL all-reduce / all-gather perf tests | 2026-07-21 | NCCL_TESTS_VERSION 2.19.6 | HEAD 2026-07-09. No git tags/releases — the version lives in `src/common.h`, bumped 2.19.3→2.19.6 across 2026-07-02..07-09. Build from HEAD; there is nothing to pin to. |
| https://docs.nvidia.com/dgx/dgx-el10-user-guide/modifying-tuned.html | DGX TuneD profile catalog (a100/a800/h100/h200/h800/b200/b300 `-performance` + `-crashdump`, plus `dgx-base`, `nvidia-base`, `nvidia-x86-64-performance`, `nvidia-crashdump-core`, `nvidia-no-mitigations`, `nvidia-acs-disable`) | 2026-07-21 | DGX EL 10 | page last updated 2026-07-15; profile roster unchanged vs the 2026-05 probe — no Rubin/Vera entries yet |
| https://enterprise-support.nvidia.com/s/article/bios-performance-tuning-example | NVIDIA BIOS performance tuning example | 2026-05-04 | — | live; SPA — WebFetch returns CSS error, browser-only |
| https://enterprise-support.nvidia.com/s/article/understanding-bios-configuration-for-performance-tuning | NVIDIA BIOS configuration guide | 2026-05-04 | — | live; SPA — WebFetch returns CSS error, browser-only |

## NVIDIA BaseOS package repos

Discovered + verified 2026-05-05 while extracting per-package settings.
Apt/dnf repos are public. Directory listings 404; specific Release /
Packages.gz / repomd.xml / individual `.deb` / `.rpm` files all
return 200. Decoded in `nvidia-dgx-config-decoder.md`.

Re-probed 2026-07-21: every row below still resolves and every count still
holds. **Count `Packages.gz` entries with `sort -u`.** The index carries one
stanza per *version*, not per package, so a raw `grep -c '^Package:'` inflates
the number — noble `dgx` returns 33 stanzas for the same 8 metapackages
(`dgx-repo` alone appears 11 times). The `dgx`-component counts below are
unique package names; jammy `common` is quoted as 106 stanzas / 99 unique. A
future freshen that "corrects" 8 → 33 has miscounted, not found drift.

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/Release | Ubuntu 22.04 BaseOS apt index | 2026-07-21 | jammy 2026-04-03 | 5 components: common (106 pkgs), dgx (35), dcs, egx, preview, c2 |
| https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/common/binary-amd64/Packages.gz | Ubuntu 22.04 `common` package list | 2026-07-21 | — | 106 stanzas / 99 unique settings packages (`nv-*`, `nvidia-*`) |
| https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/dgx/binary-amd64/Packages.gz | Ubuntu 22.04 `dgx` package list | 2026-07-21 | — | 35 metapackages, all unique (a100/a800/dgx1/dgx2/station only — no h100+ here) |
| https://repo.download.nvidia.com/baseos/ubuntu/noble/x86_64/dists/noble/dgx/binary-amd64/Packages.gz | Ubuntu 24.04 `dgx` package list | 2026-07-21 | — | 8 unique metapackages, 33 stanzas (thin — Hopper+ metapackages STILL gated as of 2026-07; noble `Release` dated 2026-03-19, components common/dgx/egx/preview) |
| https://repo.download.nvidia.com/baseos/el/10/x86_64/dgx/repodata/repomd.xml | RHEL 10 BaseOS dnf index | 2026-07-21 | EL 10 | 19 RPMs incl. `nv-common-apis-25.10-1.el.noarch.rpm`; repomd `revision` still 1762989347 (2025-11-12) — unchanged since authoring |

## Distro / OS docs

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-tuning-tuned.html | SLES 15 SP7 — TuneD chapter | 2026-07-21 | SLES 15 SP7 | live (200). **SP7 is still the newest SLES carrying this chapter.** SLES 16.0 is GA (docs portal live; `documentation.suse.com/sles/` now redirects there) but publishes no System Analysis and Tuning Guide — `16.0/html/SLES-all/cha-tuning-tuned.html` and `book-tuning.html` both 404, and there is no 15-SP8. Do not "upgrade" this citation to a 16.0 URL; it does not exist. |

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
| https://github.com/wilicc/gpu-burn | gpu-burn stress tool | 2026-07-21 | — | maintenance project; HEAD 2026-05-31 (Windows build tidy-up). No releases; CUDA 13+ support landed 2025-11-04 |
| https://www.intel.com/content/www/us/en/download/736633/intel-memory-latency-checker-intel-mlc.html | Intel MLC bandwidth/latency tool | 2026-05-04 | MLC v3.x | URL valid; WebFetch 403 (anti-bot) |
| https://www.storagereview.com/review/dell-poweredge-xe9680-the-ultimate-ai-powerhouse | XE9680 third-party review | 2026-05-04 | — | live; published 2024-11-16 |
