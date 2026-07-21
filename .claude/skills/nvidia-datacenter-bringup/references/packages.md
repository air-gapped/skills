# Package matrix (apt-cache-verified)

Authoritative listing of the apt packages this skill installs. Captured from a clean Ubuntu 24.04 docker container with NVIDIA CUDA repo enabled via `cuda-keyring_1.1-1_all.deb` on 2026-05-21. If the NVIDIA documentation text drifts from this, trust this file.

## TL;DR install on B300

```bash
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

# Branch lock
sudo apt install nvidia-driver-pinning-580

# Driver (open kernel modules — MANDATORY on Blackwell)
sudo apt install nvidia-open-580

# Fabric stack — one meta pulls FM + NVLSM + libnvsdm + libibumad3 + infiniband-diags
sudo apt install nvlink5-580

# Container toolkit (lives in same CUDA repo, no extra mirror needed)
sudo apt install nvidia-container-toolkit
```

Total: four `apt install` invocations. DOCA-Host install happens BEFORE this — see [[recipe]] for the full sequence including DOCA, kernel headers, MOK.

## The branch-suffix cliff (observed 2026-07-21)

**NVIDIA stopped minting branch-suffixed packages partway up the stack.** In the
Ubuntu 24.04 CUDA repo's `Packages` index today:

| Family | Highest `-<branch>` suffixed | Newer branches reachable how |
|---|---|---|
| `nvidia-driver-<b>`, `nvidia-driver-<b>-open`, `nvidia-open-<b>`, `cuda-drivers-<b>`, `nvlink5-<b>` | **580** | unsuffixed `nvidia-driver` / `nvidia-driver-open` / `nvidia-open` / `nvlink5` |
| `nvidia-fabricmanager-<b>`, `cuda-drivers-fabricmanager-<b>`, `libnvidia-nscq-<b>`, `libnvsdm-<b>`, `nvidia-imex-<b>` | **575** | unsuffixed `nvidia-fabricmanager`, `libnvidia-nscq`, … |

Branches **590, 595 and 610** are published — `nvidia-driver`, `nvidia-open`,
`nvlink5` and `nvidia-fabricmanager` all reach `610.43.02-1ubuntu1` — but only
through the **unsuffixed** package names, with the branch encoded in the
*version*. There is no `nvidia-open-610`.

**So `apt install nvidia-open-<branch>` is not a general recipe above 580.**
Pinning above 580 goes through `nvidia-driver-pinning-<branch>` (590/595/610 all
present) or `nvidia-driver-pinning-<version>`, then installing the *unsuffixed*
meta. The 580-based recipes in [[recipe]] and [[hopper-recipe]] remain valid
because 580 is the last branch on the suffixed scheme — that is luck, not design,
and the next branch bump will break them.

Caveat worth carrying: the 2026-05-21 live apt-cache capture recorded suffixed FM
packages up to 595. Today's index has none above 575. Whether those were removed
or never existed is not resolvable from the index alone — what is certain is what
`Packages` says today.

## Package universe summary

| Package | Type | Variants | What it is |
|---|---|---|---|
| `cuda-keyring` | repo bootstrap | `1.1-1_all` | Installs `/usr/share/keyrings/cuda-archive-keyring.gpg` + `/etc/apt/sources.list.d/cuda-*.list` |
| `nvidia-driver-pinning-<branch>` | apt pin file | 570, 575, 580, 590, 595, **610** | Installs an apt-preferences file at priority 1000; allows downgrades |
| `nvidia-driver-pinning-<version>` | apt pin file | 580.126.20, 580.159.03, 590.48.01, 595.71.05, ... | Patch-level pin |
| `nvidia-open` | meta (open, latest) | bare | `Depends: nvidia-driver-open`; conflicts with `cuda-drivers` + `nvidia-driver` |
| `nvidia-open-<branch>` | meta (open, branch-pinned) | 560, 565, 570, 575, 580 | `Depends: nvidia-driver-<branch>-open \| nvidia-driver-<branch>-server-open` |
| `cuda-drivers` | meta (proprietary, latest) | bare | UNSUITABLE for Blackwell |
| `cuda-drivers-<branch>` | meta (proprietary, branch) | various | UNSUITABLE for Blackwell |
| `nvlink5` | meta (latest) | bare | Pulls fabric stack — verify on a real B300 |
| `nvlink5-<branch>` | meta (branch-pinned) | 570, 575, 580 (no 590/595 yet) | Pulls FM + NVLSM + libnvsdm + libibumad3 + infiniband-diags coherent to branch |
| `nvlsm` | binary | floating (calver `2025.10.14-1`) | NVLink Subnet Manager. `Depends: build-essential, libgcc1, libc6, libstdc++6, libibumad3` |
| `libnvsdm` | shared lib | bare + 560/565/570/575 | NVSDM library for telemetry from QM switches |
| `libnvsdm-dev` | dev headers | one | API header + lib |
| `nvidia-fabricmanager-<branch>` | binary | 550–**575 only** | FM service. `Depends: nvidia-kernel-common-<branch>-server`. **No 580/590/595 suffixed build exists** — see the branch-suffix cliff below |
| `cuda-drivers-fabricmanager-<branch>` | meta | 550–**575 only** | Just `Depends: nvidia-fabricmanager-<branch>` — convenience. Same cliff |
| `libnvidia-nscq-<branch>` | shared lib | 550–**575** + bare | NVSwitch Configuration and Query library. Same cliff |
| `nvidia-modprobe` | binary | floating, branch-encoded in version | All driver minors back to 580.82.07 present |
| `nvidia-persistenced` | binary | floating | Persistence daemon |
| `nvidia-container-toolkit` | binary | floating | Container runtime, latest 1.19.1-1 |
| `nvidia-container-toolkit-base` | binary | floating | Base subset (no runtime hooks) |
| `datacenter-gpu-manager-4-{core,cuda11,cuda12,cuda13,cuda-all}` | DCGM v4 | per CUDA major | Pick `cuda13` for current |
| `datacenter-gpu-manager-4-{multinode,proprietary,proprietary-cuda12,proprietary-cuda13}` | DCGM v4 ext | per use case | Multi-node diagnostics and proprietary binaries |
| `datacenter-gpu-manager-exporter` | binary | one | Prometheus exporter |

## Branch lock mechanics

`nvidia-driver-pinning-<branch>` installs an apt-preferences file at priority 1000. Priority 1000 is a special value: it permits *downgrades*, not just blocks upgrades.

```
Package: nvidia-driver-pinning-580
Section: NVIDIA
Provides: nvidia-driver-pinning
Conflicts: nvidia-driver-pinning
Replaces: nvidia-driver-pinning
Description: APT driver pinning file for driver branch 580.
```

Only one `nvidia-driver-pinning-*` can be installed at a time (Conflicts + Provides on the same name).

Switching branches: `sudo apt install nvidia-driver-pinning-590 && sudo apt dist-upgrade --autoremove --purge`. The pinning file change re-prioritises the 590 packages and the dist-upgrade pulls them in.

`apt-mark hold` is known to fight with this mechanism; do **not** combine.

## Open vs proprietary on Blackwell

`nvidia-open-580` Depends:
```
nvidia-driver-580-open | nvidia-driver-580-server-open
```
Conflicts with proprietary siblings (`cuda-drivers-580`, `nvidia-driver-580`, `nvidia-driver-580-server`).

On B300, install `nvidia-open-580` (or 590/595). The proprietary `cuda-drivers-580` will install but the kernel module **does not bind** to Blackwell silicon — `nvidia-smi` reports no GPUs. NVIDIA's open-modules transition blog (2024) makes this explicit: open modules are mandatory on Blackwell and Grace Hopper; proprietary is unsupported.

If proprietary was accidentally installed, switch with:
```bash
sudo apt install --autoremove --purge nvidia-open nvidia-driver-open
```

## `nvlink5-<branch>` dependency tree (apt-cache-verified)

Live `apt-cache show nvlink5-580` output (2026-05-21, CUDA repo Ubuntu 24.04 amd64) gives the exact dependency set:

```
Package: nvlink5-580
Version: 580.159.04-1
Provides: nvlink5-branch
Depends: libnvidia-nscq (>= 580),
         libnvsdm (>= 580),
         nvidia-fabricmanager (>= 580),
         nvidia-imex (>= 580),
         nvidia-dkms-580-open | nvidia-kernel-open-dkms (>= 580),
         libnvidia-compute-580 | nvidia-driver-cuda (>= 580),
         collectx-bringup (>= 1.22.1),
         mft (>= 4.35.0.159),
         mft-oem (>= 4.35.0.159),
         mft-autocomplete (>= 4.35.0.159),
         nvlsm (>= 2025.10.12)
```

Components installed by `nvlink5-580`:
- **Fabric**: `nvidia-fabricmanager`, `nvlsm` (NVLink Subnet Manager — B200/B300 only), `libnvsdm` (telemetry from QM-class switches — B200/B300 only), `libnvidia-nscq` (NSCQ query lib — any NVSwitch generation)
- **IMEX**: `nvidia-imex` (Internode Memory Exchange — facilitates NVLink GPU-to-GPU memory mapping via import/export). **Not Blackwell-specific** — `nvidia-imex-XXX` exists for branches 550, 560, 565, 570, 575, 580, 590, 595 (verified apt-cache 2026-05-21). Useful on any NVLink-fabric chassis including XE9680 (Hopper 8-GPU) and XE8640 (Hopper 4-GPU direct mesh).
- **Firmware tooling**: `collectx-bringup` (Mellanox firmware bring-up — Blackwell CX bridge), `mft` + `mft-oem` + `mft-autocomplete` (Mellanox Firmware Tools — Blackwell ConnectX management)
- **Driver compute side**: `nvidia-dkms-580-open` (kernel modules), `libnvidia-compute-580` (CUDA runtime libs)
- **Transitive**: `libibumad3`, `infiniband-diags` (pulled in by `nvlsm`)

What `nvlink5-580` does **NOT** install:
- `nvidia-utils-580` (no `nvidia-smi`, `nvidia-persistenced`)
- `nvidia-modprobe`
- `xserver-xorg-video-nvidia-*`
- `libnvidia-gl-*`

→ `nvlink5-580` alone is a **compute-only** install. For a full server with `nvidia-smi` and friends, install `nvidia-open-580` (full userland meta) AS WELL. The two metas share kernel-module dependencies (they'll co-resolve to the same `nvidia-dkms-580-open`). See [[recipe]] step 6 + 7.

## NVLSM versioning quirk

`nvlsm` is a **single floating package** (calver, e.g. `2025.10.12-1`), not branch-versioned. The apt-cache description literally says:

> SM is an InfiniBand compliant Subnet Manager (SM).

(Yes, just "SM" — terse.) It depends on `libibumad3` plus build-essential / libc / libgcc / libstdc++. **No dependency on a specific NVIDIA driver branch.**

If the FM User Guide text shows `nvlink5-<branch>` but it's missing from the repo: search a fresh `apt-cache search nvlink5` against the current CUDA repo. Package names occasionally lag the docs.

## What's NOT in Ubuntu archive

These exist ONLY in the NVIDIA CUDA repo (verified via packages.ubuntu.com 404s):
- `nvidia-driver-pinning-*`
- `nvlink5-*`
- `nvlsm`
- `libnvsdm[-XXX]`
- `nvidia-driver-XXX-{open,server-open}` post-595 patches

Ubuntu archive (noble-updates) does carry: `nvidia-driver-XXX-server`, `nvidia-driver-XXX-server-open`, `nvidia-headless-XXX[-server][-open]`, `nvidia-headless-no-dkms-XXX[...]`, `linux-modules-nvidia-XXX[-open]-generic-hwe-24.04` (Canonical-signed precompiled), `nvidia-fabricmanager-XXX`, `cuda-drivers-fabricmanager-XXX`, `libnvidia-nscq-XXX`, `libibumad3`, `infiniband-diags`.

For B300 the single-source CUDA repo path is strictly better than mixed Ubuntu+NVIDIA: simpler version coherence, NVIDIA-pinning available, fresher patches.

## Disambiguating origin at runtime

```bash
# Where did this package come from?
apt-cache policy <pkg>           # Shows the repo URL
apt-cache show <pkg> | grep -E '^(Origin|Maintainer|Section)'

# Ubuntu archive:   Maintainer: Ubuntu Kernel Team <kernel-team@lists.ubuntu.com>
#                   Section: multiverse/libs (or restricted/utils)
#                   Origin: Ubuntu
#
# NVIDIA CUDA repo: Maintainer: cudatools <cudatools@nvidia.com>   (or NVIDIA <cudatools@nvidia.com>)
#                   Section: multiverse/devel  (or NVIDIA)
#                   no Origin field (apt fills from Release file)
```

## Driver patch matrix in the CUDA repo

All these are present (verified live 2026-05-21) — pin any patch level to match a fabricmanager rev:

```
580.82.07 580.95.05 580.105.08 580.126.09 580.126.16 580.126.20 580.159.03 580.159.04
590.44.01 590.48.01
595.45.04 595.58.03 595.71.05
```

The repo never prunes — historical patch versions remain installable. Good for reproducible bring-ups; mirror by patch-version-tuple for immutability.
