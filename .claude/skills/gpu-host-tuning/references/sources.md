# Sources — dated index for `freshen` mode

Freshened: 2026-09-22 — every row probed; the BaseOS package counts, TuneD profile roster and repomd revision all reproduce exactly. One image tag was superseded: DCGM 3.3.6 → 4.5.2 for ubuntu22.04.

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
| https://github.com/NVIDIA/nvbandwidth | host↔device + multinode bandwidth bench | 2026-09-15 | v0.10.0 | **v0.10.0 (2026-07-21) is latest** — it was published the same day as the previous pass's stamp, so that row was stale within hours of being written. v0.9 (2026-04-08) was previously latest; NVIDIA-recommended replacement for the removed cuda-samples `bandwidthTest` (dropped in cuda-samples v13.0) |
| https://github.com/NVIDIA/nccl-tests | NCCL all-reduce / all-gather perf tests | 2026-09-15 | NCCL_TESTS_VERSION 2.20.0 | **`src/common.h` now defines `NCCL_TESTS_VERSION "2.20.0"`** (HEAD 2026-08-28). **The "no git tags" claim is false: `gh api .../tags` lists v2.20.0, v2.19.7, v2.19.6 and older.** `gh release list` is still empty, which is what the earlier check must have used — tags and GitHub Release objects are different things and the absence of one is not the absence of the other. Historically, HEAD 2026-07-09, no git releases — the version lives in `src/common.h`, bumped 2.19.3→2.19.6 across 2026-07-02..07-09. Build from HEAD; there is nothing to pin to. |
| https://docs.nvidia.com/datacenter/tesla/drivers/latest/supported-drivers-and-cuda-toolkit-versions.html | Supported datacenter driver branches, EOL, max CUDA major | 2026-10-27 | page updated 2026-09-09 | Table: R535 LTSB EOL June 2026 (max CUDA 12), R580 LTSB June 2028, R595 PB March 2027, R610 NFB August 2026 (CUDA 13 for all three). `https://docs.nvidia.com/datacenter/tesla/drivers/releases.json` lists 615 as NFB (615.71.10, 2026-10-19), newest 580 = 580.196.07, 595 = 595.112.07, and no 555 branch at all — the skill's former "550+ baseline; 555+ for Blackwell" named an EOL branch and a non-datacenter one. |
| https://hub.docker.com/r/nvidia/dcgm/tags | DCGM container tag for `dcgmi diag` in `bringup-recipe.md` §2.2 | 2026-10-27 | 4.7.0-ubuntu24.04 | Docker Hub tags API: 4.7.0-ubuntu24.04 / -ubi10 (2026-10-21), 4.6.1-1, 4.6.0-1, 4.5.3-1 on ubuntu24.04/ubi10 only; newest ubuntu22.04 and ubi9 tag is 4.5.2-1 (2026-02-17). Changelog https://docs.nvidia.com/datacenter/dcgm/latest/release-notes/changelog.html: 4.7.0 adds MIG-mode diag, no break to `diag --run N --fail-early`; `-g` is deprecated in favour of `-i`. Open issues since 2026-09 (NVIDIA/DCGM #312–#321) touch health/profiling/exporter, none `diag`. |
| https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html#nccl-nvls-enable | `NCCL_NVLS_ENABLE` semantics and default | 2026-10-27 | NCCL 2.32.3 docs | "(since 2.17) … The default value is 2"; 2 ≡ 1 except 2.27–2.28, which "tried to silently fall back … could result in a hang if the allocation failed on just some of the ranks, so in 2.29 the behavior reverted". Code: `NCCL_PARAM(NvlsEnable, "NVLS_ENABLE", …)` in `src/transport/nvls.cc` is 1 at v2.17.1-1, 2 at v2.18.1-1 and v2.20.3-1 — the skill's former "default 1 since 2.20" matched neither. |
| https://docs.nvidia.com/dgx/dgx-el10-user-guide/modifying-tuned.html | DGX TuneD profile catalog: `dgx-{a100,a800,h100,h200,h800,b200,b300}-performance`, `-crashdump` for all but h800, plus `dgx-base`, `nvidia-base`, `nvidia-x86-64-performance`, `nvidia-crashdump-core`, `nvidia-no-mitigations`, `nvidia-acs-disable` | 2026-10-27 | DGX EL 10 | page last updated 2026-07-15; no `dgx-h800-crashdump`; no GB200/GB300/Rubin/Vera profiles. `dgx-h100-no-mitigations` / `dgx-h100-selective-mitigations` on the page are custom profiles the reader is told to create under `/etc/tuned/`, not shipped ones |
| https://enterprise-support.nvidia.com/s/article/bios-performance-tuning-example | NVIDIA BIOS performance tuning example | 2026-08-18 | — | live; SPA — WebFetch returns CSS error, browser-only |
| https://enterprise-support.nvidia.com/s/article/understanding-bios-configuration-for-performance-tuning | NVIDIA BIOS configuration guide | 2026-08-18 | — | live; SPA — WebFetch returns CSS error, browser-only |

## NVIDIA BaseOS package repos

Apt/dnf repos are public. Directory listings 404; specific Release /
Packages.gz / repomd.xml / individual `.deb` / `.rpm` files all return 200.
Decoded in `nvidia-dgx-config-decoder.md`.

**Count `Packages.gz` entries with `sort -u`.** The index carries one stanza
per *version*, not per package, so a raw `grep -c '^Package:'` inflates the
number. Counts below are unique package names, stanzas in brackets. NVIDIA
pruned jammy between 2026-07-21 and 2026-09-15 (`common` 99 → 86 unique,
`dgx` 35 → 8, noble `dgx` 8 → 3); earlier counts are not drift to restore.

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/Release | Ubuntu 22.04 BaseOS apt index | 2026-10-27 | jammy 2026-07-24 | `Date: Fri, 24 Jul 2026`; components common dcs dgx egx preview c2 |
| https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/common/binary-amd64/Packages.gz | Ubuntu 22.04 `common` package list | 2026-10-27 | — | 86 unique (88). Absent: `nvidia-acs-disable`, `nvidia-relaxed-ordering-gpu`, `nvidia-relaxed-ordering-nvme`, `nv-common-apis` — the decoder's bulk recipe no longer lists them |
| https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/dgx/binary-amd64/Packages.gz | Ubuntu 22.04 `dgx` package list | 2026-10-27 | — | 8 unique (8): dgx-kvm-guest-utils, dgx-repo, dgx-server-grub, dgxstation-a100/a800-ota-update-meta, dgxstation-desktop, dgxstation-grub, dgxstation-ota-update-meta |
| https://repo.download.nvidia.com/baseos/ubuntu/noble/x86_64/dists/noble/Release | Ubuntu 24.04 BaseOS apt index | 2026-10-27 | noble 2026-08-27 | `Date: Thu, 27 Aug 2026`; components common dgx egx preview |
| https://repo.download.nvidia.com/baseos/ubuntu/noble/x86_64/dists/noble/common/binary-amd64/Packages.gz | Ubuntu 24.04 `common` package list | 2026-10-27 | — | 63 unique (65); carries `nvidia-acs-disable`; no `nvidia-relaxed-ordering-*`, no `nv-common-apis` |
| https://repo.download.nvidia.com/baseos/ubuntu/noble/x86_64/dists/noble/dgx/binary-amd64/Packages.gz | Ubuntu 24.04 `dgx` package list | 2026-10-27 | — | 3 unique (12): dgx-a100-ota-update-meta, dgx-kvm-guest-utils, dgx-repo-keys |
| https://repo.download.nvidia.com/baseos/el/10/x86_64/dgx/repodata/repomd.xml | RHEL 10 BaseOS dnf index | 2026-10-27 | EL 10 | repomd `revision` 1762989347 (2025-11-12, unchanged since authoring); primary is `*-primary.xml.zst` (`zstd -dc`, not gunzip); 19 RPMs incl. `nv-common-apis-25.10-1.el.noarch.rpm` (only public source of it) and `nvidia-acs-disable-25.08-1.el.noarch.rpm` |

## Distro / OS docs

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-tuning-tuned.html | SLES 15 SP7 — TuneD chapter | 2026-09-15 | SLES 15 SP7 | live (200). **SP7 is still the newest SLES carrying this chapter.** SLES 16.0 is GA (docs portal live; `documentation.suse.com/sles/` now redirects there) but publishes no System Analysis and Tuning Guide — `16.0/html/SLES-all/cha-tuning-tuned.html` and `book-tuning.html` both 404, and there is no 15-SP8. Do not "upgrade" this citation to a 16.0 URL; it does not exist. |

## Linux kernel

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://github.com/torvalds/linux/blob/master/drivers/cpufreq/amd-pstate.c | amd-pstate mode timeline + server default | 2026-10-27 | v6.13 | Read at tags: base driver v5.17; `amd_pstate_epp_driver` first in v6.3; `AMD_PSTATE_GUIDED` first in v6.4; `X86_AMD_PSTATE_DEFAULT_MODE` (default 3 = active) first in v6.5, but `amd_pstate_init` skips server ACPI PM profiles. Commit 54ab7d7c59c9 ("Switch to amd-pstate by default on some Server platforms") adds the `boot_cpu_data.x86 < 0x1A` exception — absent at v6.12, present at v6.13 and on master. Pre-Zen-5 EPYC servers therefore stay on acpi-cpufreq unless booted with `amd_pstate=`. |

## Dell PowerEdge XE chassis docs

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://www.delltechnologies.com/asset/en-ca/products/servers/technical-support/poweredge-xe9680-technical-guide.pdf | XE9680 Technical Guide | 2026-10-27 | E90S, Rev. A09, July 2025 | PDF, 68 pages; file re-issued 2026-09-07 with the same revision |
| https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9780-technical-guide.pdf | XE9780 Technical Guide | 2026-10-27 | E125S, Rev. A03, August 2026 | PDF, 58 pages; height/depth, 163.2 kg and the B300/B200 GPU options match `dell-xe9780.md` |
| https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe-ai-spec-sheet.pdf | XE AI spec sheet (XE9680/XE9780/XE9785/XE9712 cross-comparison) | 2026-08-18 | — | PDF |
| https://www.dell.com/support/manuals/en-us/poweredge-xe9680/xe9680_ism_pub/ | XE9680 Installation and Service Manual | 2026-08-18 (403 to curl — bot-blocked, verify in browser) | — | live |
| https://www.dell.com/en-us/shop/ipovw/poweredge-xe9780l | XE9780L product page (liquid variant) | 2026-08-18 | — | live; notes iF Design 2026 award |
| https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/ | 16G BIOS Performance & Workload Tuning Guide | 2026-10-27 (gone: browser lands on the Info Hub home page, twice) | 16G | No longer cited in the skill; the guide's subpages still load — cite the Intel-section row below |
| https://infohub.delltechnologies.com/en-us/l/poweredge-bios-performance-and-workload-tuning-guide-for-16g/detailed-settings-for-intel-bios-profile/ | 16G BIOS Tuning — Intel detailed settings | 2026-08-18 | 16G | URL valid; WebFetch 403 |
| https://infohub.delltechnologies.com/en-us/p/16g-poweredge-platform-bios-characterization-for-hpc-with-intel-sapphire-rapids/ | 16G HPC BIOS characterization (Sapphire Rapids; methodology applies to Granite Rapids) | 2026-08-18 | SPR baseline | URL valid; WebFetch 403 |

## Third-party reviews and tools

| URL | Topic | Last verified | Pinned | Notes |
|-----|-------|---------------|--------|-------|
| https://github.com/wilicc/gpu-burn | gpu-burn stress tool | 2026-09-15 | — | maintenance project; HEAD 2026-05-31 (Windows build tidy-up). No releases; CUDA 13+ support landed 2025-11-04 |
| https://www.intel.com/content/www/us/en/download/736633/intel-memory-latency-checker-intel-mlc.html | Intel MLC bandwidth/latency (403 to curl 2026-08-18 — bot-blocked, verify in browser) tool | 2026-08-18 | MLC v3.x | URL valid; WebFetch 403 (anti-bot) |
| https://www.storagereview.com/review/dell-poweredge-xe9680-the-ultimate-ai-powerhouse | XE9680 third-party review | 2026-08-18 | — | live; published 2024-11-16 |
