# Sources

Freshened: 2026-09-22 — every row probed. GPU Operator is still v26.7.0, but the apt index moved under the file: nvidia-container-toolkit 1.19.1-1 -> 1.20.1-1 and the driver stack 610.43.02-1ubuntu1 -> 615.71.09-2ubuntu1. Two Ubuntu wiki Secure Boot pages now 404 outright — the wiki migrated off MoinMoin and the articles do not exist under any title; annotated inline rather than removed, since documentation.ubuntu.com is the surviving primary source. Dell 403s remain the known Akamai bot-block.

**Three DOCA rows moved host this pass**: `docs.nvidia.com/doca/sdk/...` now permanently redirects to `networking-docs.nvidia.com/doca/archive/3-5-0/...`. The URLs below are the new ones.

**Exception — Dell pages:** several `dell.com` rows answer `curl` with an Akamai block page (and one release-notes asset blocks a real browser too). Those were confirmed through a browser session against the linking driver page; treat a 403 there as a bot block, never as link rot.

Dated index of authoritative URLs the skill draws on. `Last verified:` reflects the date the content was read in full; the loop's freshen pass updates these.

## NVIDIA — Fabric Manager

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/datacenter/tesla/fabric-manager-user-guide/index.html | FM User Guide overview, B200/B300 sections | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/pdf/fabric-manager-user-guide.pdf | PDF mirror (Release 2.3, May 2025) for offline reference | 2026-08-18 | — |

## NVIDIA — Driver Install Guide

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/index.html | Driver guide top-level | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/ubuntu.html | Ubuntu install chapter | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/kernel-modules.html | Open vs proprietary kernel modules | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/advanced-options.html | Switching prop ↔ open, meta-packages | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/compute-only-and-desktop-installation.html | Compute-only (headless) install | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/post-installation-actions.html | Persistence daemon | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/pre-installation-actions.html | Kernel headers, distro check | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/version-locking.html | `nvidia-driver-pinning-XXX` mechanism | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/choose-an-installation-method.html | Network vs local repo guidance | 2026-08-18 | — |

## NVIDIA — DOCA

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://networking-docs.nvidia.com/doca/archive/3-5-0/doca-host-installation-and-upgrade | DOCA-Host install for Ubuntu | 2026-08-18 | — |
| https://networking-docs.nvidia.com/doca/archive/3-5-0/doca-host-installation-and-dkms-management-guide | DOCA DKMS sign-on-build mechanics | 2026-08-18 | — |
| https://networking-docs.nvidia.com/doca/archive/3-5-0 | MLNX_OFED end-of-life, DOCA-OFED forward path | 2026-08-18 | — |
| https://linux.mellanox.com/public/repo/doca/ | DOCA repo root (umbrella GPG key) | 2026-08-18 | — |
| https://linux.mellanox.com/public/repo/doca/public_keys/ | Current split GPG keys (deb + rpm) | 2026-08-18 | rotated 2026-02-24 |
| https://linux.mellanox.com/public/repo/doca/latest-3.2-LTS/ubuntu24.04/x86_64/ | Evidence that `latest-*-LTS/` lags | 2026-08-18 | 2026-10-27: dir dated 2026-03-22, `doca-all` 3.2.2-035000 while 3.2.3 is published — do not mirror it |
| https://linux.mellanox.com/public/repo/doca/3.2.3/ubuntu24.04/x86_64/ | DOCA 3.2.3 LTS (LTS25-U3, June 2026 per the DOCA archive page) Ubuntu 24.04 flat repo — the mirror target | 2026-10-27 | `doca-all` 3.2.3-019000; `Release.gpg` signed by key `DC726C5E41B9CC50` (2026-01-20, the `public_keys/` debian key); per-repo `doca_keyring.gpg` byte-identical to it; umbrella `GPG-KEY-Mellanox.pub` holds only 2013/2014/2018 keys |
| https://developer.nvidia.com/doca-archive | DOCA LTS release calendar | 2026-08-18 | — |

## NVIDIA — CUDA driver repo

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/ | Ubuntu 24.04 amd64 CUDA repo (driver, FM, nvlsm, libnvsdm, nvlink5, container-toolkit) — path note: `ubuntu2404` no dot | 2026-07-21 | 590, 595, 610 and 615 are published (newest `615.71.10-1ubuntu1`; newest 580 `580.196.07-1ubuntu1`; `nvlsm` `2025.12.211-1`; `nvidia-container-toolkit` `1.20.1-1`; re-read 2026-10-27). They ship only via *unsuffixed* package names — branch-suffixed builds stop at 580 (driver side) and 575 (fabric side). See [[packages]] §branch-suffix cliff. Suffixed `nvidia-fabricmanager-<b>` / `cuda-drivers-fabricmanager-<b>` / `libnvidia-nscq-<b>` / `nvidia-imex-<b>` stop at 575 (re-checked 2026-10-27); `nvidia-driver-pinning-580` (`580-1ubuntu3`) pins `src:nvidia-fabricmanager src:libnvidia-nscq src:nvidia-imex src:nvlink5 src:libnvsdm` to `580*`, so Hopper/B300 580 installs use the unsuffixed names. Read `Packages.gz`, **not** the HTML directory listing: the listing does not surface unsuffixed packages' branch versions and reads as though nothing past 580 exists. Branch designations now verified — see the driver-lifecycle row below |
| https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb | Repo keyring + source-list deb | 2026-08-18 | 1.1-1 |
| https://developer.nvidia.com/blog/updating-the-cuda-linux-gpg-repository-key/ | CUDA repo key rotation history (last rotation April 2022) | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/drivers/latest/supported-drivers-and-cuda-toolkit-versions.html | Branch designation + EOL table used in [[recipe]] Step 5 | 2026-10-27 | R535 LTSB EOL June 2026, R580 LTSB June 2028, R595 PB March 2027, R610 NFB August 2026; machine-readable `https://docs.nvidia.com/datacenter/tesla/drivers/releases.json` lists 615 as NFB (615.71.10, 2026-10-19). Lifecycle definitions: `.../drivers/latest/driver-lifecycle.html` |

## NVIDIA — open kernel modules

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/ | "Open modules mandatory on Blackwell + Grace Hopper" statement | 2026-08-18 | — |

## NVIDIA — gpu-operator

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/release-notes.html | Operator release notes | 2026-08-18 | **v26.7.2 is latest** (2026-10-14); v26.7.1 2026-09-23, v26.7.0 2026-08-21. Air-gap image tags in [[gpu-operator]] read from `deployments/gpu-operator/values.yaml` at tag v26.7.2 (local clone, 2026-10-27) |
| https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html | Driver branch + GPU compat matrix | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/install-gpu-operator.html | Pre-installed driver mode helm flags | 2026-08-18 | — |
| https://github.com/NVIDIA/gpu-operator | Upstream source: validator code, helm values.yaml | 2026-08-18 | — |
| https://github.com/NVIDIA/gpu-operator/issues/2231 | B300 PCI 0x3182 validator name table | 2026-08-18 | CLOSED 2026-07-27. The v26.7.0 release notes attribute PR #2625 to it, but that PR only maps `0x318210DE` to the B300X-269C vGPU profile. The validator warning comes from go-nvlib `pkg/nvpci/nvpci.go` (`pciDB.GetDeviceName`) against `vendor/github.com/NVIDIA/go-nvlib/pkg/pciids/default_pci.ids` (dated 2025-07-11, go-nvlib v0.12.0), which has no `3182` entry at v26.3.3, v26.7.2 or `main` (checked 2026-10-27) — the warning persists |
| https://github.com/NVIDIA/gpu-operator/issues/1595 | CLOSED 2025-11-17: FM broken in 570.158.01 | 2026-08-18 | fixed in 570.172.08 |
| https://github.com/NVIDIA/gpu-operator/issues/2463 | CONFIG_MEMORY_HOTPLUG hostPath mount | 2026-07-21 | CLOSED 2026-07-07 by PR #2517 ("Update Memory Hotplug hostvolume to /sys/devices/system", merge `92aceef9`): not in v26.3.3, in v26.7.0+ (`gh api compare`); listed in the 26.7.0 release notes. The skill recommends no workaround |
| https://github.com/NVIDIA/gpu-operator/issues/286 | CLOSED: original cudaErrorSystemNotReady → FM diagnosis | 2026-08-18 | — |
| https://github.com/NVIDIA/gpu-operator/issues/1043 | CLOSED: cuda-validator stuck → install FM | 2026-08-18 | — |
| https://forums.developer.nvidia.com/t/nvidia-fabricmanager-fail-with-ib-umad-module/353369 | Canonical reference for install-order pitfall | 2026-08-18 | — |

## Ubuntu — Secure Boot + DKMS

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://wiki.ubuntu.com/UEFI/SecureBoot **[2026-10-27: 200 again, but a one-line MediaWiki stub that points to the Ubuntu security docs — no content; dropped from [[secure-boot]]]** | (formerly) boot chain, shim + Canonical CA model | 2026-08-18 | — |
| https://wiki.ubuntu.com/UEFI/SecureBoot/DKMS **[2026-10-27: 404 to curl; the browser shows an empty "no text in this page" placeholder — dropped from [[secure-boot]]]** | (formerly) `update-secureboot-policy`, MOK enrollment | 2026-08-18 | — |
| https://documentation.ubuntu.com/security/security-features/platform-protections/secure-boot/ | Canonical security-team SB docs | 2026-08-18 | — |
| https://wiki.debian.org/SecureBoot | lockdown=integrity behaviours, `modinfo` verification | 2026-08-18 | — |
| https://packages.ubuntu.com/noble/shim-signed | shim-signed 1.58+15.8-0ubuntu1 metadata | 2026-08-18 | 24.04 noble |

## Dell — chassis (B300 + Hopper)

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://dl.dell.com/FOLDER14346751M/3/Release-notes.txt | HGX B300 SXM6 air-cooled firmware v1.4.30 release notes | 2026-08-18 | v1.4.30 (2026-03-25) |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=xrg43 | XE9780/XE9785 — Dell driver page for air-cooled B300 firmware | 2026-08-18 (403 to curl — Dell bot-block, verify in browser) | — |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=662gc | Same for partner-cooled B300 variant | 2026-08-18 (403 to curl — Dell bot-block, verify in browser) | — |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=mh92v | XE9680 — HGX H200 141G 8-GPU baseboard firmware | 2026-08-18 (403 to curl — Dell bot-block, verify in browser) | — |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=p9gg2 | XE9680 — PCIe Switch firmware (H100/A100 U.2 NVMe config) | 2026-08-18 (403 to curl — Dell bot-block, verify in browser) | — |
| https://www.dell.com/support/kbdoc/en-ws/000355295/poweredge-xe9680l-and-xe9685l-gpu-firmware-update-may-fail-with-virtual-power-cycle | Virtual power cycle activation failure + `DellOemChassis.ExtendedReset` curl commands. **Scope: XE9680L/XE9685L only** — the title names those two models, not XE9780/XE9785; applying it to B300 SKUs is read-across (see [[dell-firmware]]). Still "a limitation in iDRAC" with no fixed-in version at last update 2026-05-23 | 2026-08-19 (readable — the earlier 403 was curl-specific, not a login wall) | — |
| https://www.dell.com/support/kbdoc/en-us/000377140/ | DUP firmware update failure on B200/B300, `mlxfwmanager` workaround | 2026-08-18 (403 to curl — Dell bot-block, verify in browser) | — |
| https://www.dell.com/support/kbdoc/en-us/000308105/ | XE9680/XE9640/XE8640 — iDRAC Direct USB Port BIOS gotcha | 2026-08-18 (403 to curl — Dell bot-block, verify in browser) | — |
| https://github.com/dell/iDRAC-Redfish-Scripting/blob/master/Redfish%20Python/GetFirmwareInventoryREDFISH.py | Reference for FirmwareInventory Redfish query | 2026-08-18 | — |
| https://docs.nvidia.com/dgx/dgxb300-fw-update-guide/ | NVIDIA-side firmware procedure baseline (DGX equivalent) | 2026-08-18 | — |
| https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe8640-technical-guide.pdf | XE8640 Technical Guide (4× HGX H100 SXM5 confirmation, no NVSwitch) | 2026-08-18 | — |
| https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-580-65-06/index.html | R580 release notes — Hopper subrev 3 VBIOS 96.00.68.00.xx init-failure gate | 2026-08-18 | 580.65.06 |
| https://docs.nvidia.com/datacenter/tesla/hgx-software-guide/index.html | NVIDIA HGX A100 Software User Guide — establishes "HGX 4-GPU has no NVSwitch, FM not required" rule (applies to H100 4-GPU too) | 2026-08-18 | — |

## Ubuntu archive — package presence checks

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://packages.ubuntu.com/search?keywords=nvidia-driver-pinning | Confirms NO `nvidia-driver-pinning-*` in Ubuntu archive | 2026-08-18 | — |
| https://packages.ubuntu.com/search?keywords=nvlink5 | Confirms NO `nvlink5-*` in Ubuntu archive | 2026-08-18 | — |
| https://packages.ubuntu.com/noble-updates/linux-modules-nvidia-595-open-generic-hwe-24.04 | Canonical-signed precompiled 595-open HWE module | 2026-08-18 | kernel ABI 6.17.0-29-generic |

## Live apt-cache reality

Re-probed 2026-07-21 against the repo's `Packages.gz` index (see the branch-suffix correction above). Originally captured 2026-05-21 from a clean `ubuntu:24.04` docker container with the NVIDIA CUDA repo added via `cuda-keyring_1.1-1_all.deb`. The apt-cache output backing the [[packages]] reference is the authoritative source for package names — if NVIDIA's user-guide text drifts from the apt index, trust the apt index. Re-run the inspect script during freshen passes.
