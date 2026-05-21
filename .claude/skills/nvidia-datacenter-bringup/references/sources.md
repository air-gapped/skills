# Sources

Dated index of authoritative URLs the skill draws on. `Last verified:` reflects the date the content was read in full; the loop's freshen pass updates these.

## NVIDIA — Fabric Manager

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/datacenter/tesla/fabric-manager-user-guide/index.html | FM User Guide overview, B200/B300 sections | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/pdf/fabric-manager-user-guide.pdf | PDF mirror (Release 2.3, May 2025) for offline reference | 2026-05-21 | — |

## NVIDIA — Driver Install Guide

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/index.html | Driver guide top-level | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/ubuntu.html | Ubuntu install chapter | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/kernel-modules.html | Open vs proprietary kernel modules | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/advanced-options.html | Switching prop ↔ open, meta-packages | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/compute-only-and-desktop-installation.html | Compute-only (headless) install | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/post-installation-actions.html | Persistence daemon | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/pre-installation-actions.html | Kernel headers, distro check | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/version-locking.html | `nvidia-driver-pinning-XXX` mechanism | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/choose-an-installation-method.html | Network vs local repo guidance | 2026-05-21 | — |

## NVIDIA — DOCA

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/doca/sdk/doca-host-installation-and-upgrade/index.html | DOCA-Host install for Ubuntu | 2026-05-21 | — |
| https://docs.nvidia.com/doca/sdk/doca-host-installation-and-dkms-management-guide/index.html | DOCA DKMS sign-on-build mechanics | 2026-05-21 | — |
| https://docs.nvidia.com/doca/sdk/MLNX_OFED-to-DOCA-OFED-Transition-Guide/index.html | MLNX_OFED end-of-life, DOCA-OFED forward path | 2026-05-21 | — |
| https://linux.mellanox.com/public/repo/doca/ | DOCA repo root (umbrella GPG key) | 2026-05-21 | — |
| https://linux.mellanox.com/public/repo/doca/public_keys/ | Current split GPG keys (deb + rpm) | 2026-05-21 | rotated 2026-02-24 |
| https://linux.mellanox.com/public/repo/doca/latest-3.2-LTS/ubuntu24.04/x86_64/ | DOCA 3.2 LTS Ubuntu 24.04 flat repo | 2026-05-21 | LTS line — path note: `ubuntu24.04` with dot |
| https://developer.nvidia.com/doca-archive | DOCA LTS release calendar | 2026-05-21 | — |

## NVIDIA — CUDA driver repo

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/ | Ubuntu 24.04 amd64 CUDA repo (driver, FM, nvlsm, libnvsdm, nvlink5, container-toolkit) — path note: `ubuntu2404` no dot | 2026-05-21 | — |
| https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb | Repo keyring + source-list deb | 2026-05-21 | 1.1-1 |
| https://developer.nvidia.com/blog/updating-the-cuda-linux-gpg-repository-key/ | CUDA repo key rotation history (last rotation April 2022) | 2026-05-21 | — |

## NVIDIA — open kernel modules

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/ | "Open modules mandatory on Blackwell + Grace Hopper" statement | 2026-05-21 | — |

## NVIDIA — gpu-operator

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/release-notes.html | Operator release notes (26.3.0, 26.3.1) | 2026-05-21 | 26.3.1 latest |
| https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html | Driver branch + GPU compat matrix | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/install-gpu-operator.html | Pre-installed driver mode helm flags | 2026-05-21 | — |
| https://github.com/NVIDIA/gpu-operator | Upstream source: validator code, helm values.yaml | 2026-05-21 | — |
| https://github.com/NVIDIA/gpu-operator/issues/2231 | OPEN: B300 PCI 0x3182 validator name table | 2026-05-21 | open as of 2026-05-18 |
| https://github.com/NVIDIA/gpu-operator/issues/1595 | CLOSED 2025-11-17: FM broken in 570.158.01 | 2026-05-21 | fixed in 570.172.08 |
| https://github.com/NVIDIA/gpu-operator/issues/2463 | OPEN 2026-05-14: CONFIG_MEMORY_HOTPLUG hostPath mount | 2026-05-21 | open |
| https://github.com/NVIDIA/gpu-operator/issues/286 | CLOSED: original cudaErrorSystemNotReady → FM diagnosis | 2026-05-21 | — |
| https://github.com/NVIDIA/gpu-operator/issues/1043 | CLOSED: cuda-validator stuck → install FM | 2026-05-21 | — |
| https://forums.developer.nvidia.com/t/nvidia-fabricmanager-fail-with-ib-umad-module/353369 | Canonical reference for install-order pitfall | 2026-05-21 | — |

## Ubuntu — Secure Boot + DKMS

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://wiki.ubuntu.com/UEFI/SecureBoot | Boot chain, shim + Canonical CA model | 2026-05-21 | — |
| https://wiki.ubuntu.com/UEFI/SecureBoot/DKMS | `update-secureboot-policy`, MOK enrollment | 2026-05-21 | — |
| https://documentation.ubuntu.com/security/security-features/platform-protections/secure-boot/ | Canonical security-team SB docs | 2026-05-21 | — |
| https://wiki.debian.org/SecureBoot | lockdown=integrity behaviours, `modinfo` verification | 2026-05-21 | — |
| https://packages.ubuntu.com/noble/shim-signed | shim-signed 1.58+15.8-0ubuntu1 metadata | 2026-05-21 | 24.04 noble |

## Dell — chassis (B300 + Hopper)

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://dl.dell.com/FOLDER14346751M/3/Release-notes.txt | HGX B300 SXM6 air-cooled firmware v1.4.30 release notes | 2026-05-21 | v1.4.30 (2026-03-25) |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=xrg43 | XE9780/XE9785 — Dell driver page for air-cooled B300 firmware | 2026-05-21 | — |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=662gc | Same for partner-cooled B300 variant | 2026-05-21 | — |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=mh92v | XE9680 — HGX H200 141G 8-GPU baseboard firmware | 2026-05-21 | — |
| https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=p9gg2 | XE9680 — PCIe Switch firmware (H100/A100 U.2 NVMe config) | 2026-05-21 | — |
| https://www.dell.com/support/kbdoc/en-us/000355295/ | Virtual power cycle activation failure + `DellOemChassis.ExtendedReset` curl commands | 2026-05-21 | — |
| https://www.dell.com/support/kbdoc/en-us/000377140/ | DUP firmware update failure on B200/B300, `mlxfwmanager` workaround | 2026-05-21 | — |
| https://www.dell.com/support/kbdoc/en-us/000308105/ | XE9680/XE9640/XE8640 — iDRAC Direct USB Port BIOS gotcha | 2026-05-21 | — |
| https://github.com/dell/iDRAC-Redfish-Scripting/blob/master/Redfish%20Python/GetFirmwareInventoryREDFISH.py | Reference for FirmwareInventory Redfish query | 2026-05-21 | — |
| https://docs.nvidia.com/dgx/dgxb300-fw-update-guide/ | NVIDIA-side firmware procedure baseline (DGX equivalent) | 2026-05-21 | — |
| https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe8640-technical-guide.pdf | XE8640 Technical Guide (4× HGX H100 SXM5 confirmation, no NVSwitch) | 2026-05-21 | — |
| https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-580-65-06/index.html | R580 release notes — Hopper subrev 3 VBIOS 96.00.68.00.xx init-failure gate | 2026-05-21 | 580.65.06 |
| https://docs.nvidia.com/datacenter/tesla/hgx-software-guide/index.html | NVIDIA HGX A100 Software User Guide — establishes "HGX 4-GPU has no NVSwitch, FM not required" rule (applies to H100 4-GPU too) | 2026-05-21 | — |

## Ubuntu archive — package presence checks

| URL | Purpose | Last verified | Pinned |
|---|---|---|---|
| https://packages.ubuntu.com/search?keywords=nvidia-driver-pinning | Confirms NO `nvidia-driver-pinning-*` in Ubuntu archive | 2026-05-21 | — |
| https://packages.ubuntu.com/search?keywords=nvlink5 | Confirms NO `nvlink5-*` in Ubuntu archive | 2026-05-21 | — |
| https://packages.ubuntu.com/noble-updates/linux-modules-nvidia-595-open-generic-hwe-24.04 | Canonical-signed precompiled 595-open HWE module | 2026-05-21 | kernel ABI 6.17.0-29-generic |

## Live apt-cache reality

Captured 2026-05-21 from a clean `ubuntu:24.04` docker container with the NVIDIA CUDA repo added via `cuda-keyring_1.1-1_all.deb`. The apt-cache output backing the [[packages]] reference is the authoritative source for package names — if NVIDIA's user-guide text drifts from the apt index, trust the apt index. Re-run the inspect script during freshen passes.
