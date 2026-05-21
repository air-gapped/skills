# NVIDIA Transitions Fully Towards Open-Source GPU Kernel Modules

> Retrieved 2026-05-21 from https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/
>
> This is the authoritative source for the claim that open kernel modules are MANDATORY on Blackwell.

## Overview

NVIDIA is transitioning to open-source GPU kernel modules with the R560 driver release. The transition includes dual GPL and MIT licensing for Linux GPU kernel modules, which were initially released in May 2022 with the R515 driver.

## GPU Architecture Support

### Required Open-Source Modules

For cutting-edge platforms, **open-source modules are mandatory**:

- **NVIDIA Grace Hopper**
- **NVIDIA Blackwell**

> "The proprietary drivers are unsupported on these platforms."

### Recommended for Open-Source Migration

For newer GPUs from these architectures, NVIDIA recommends switching to open-source modules:

- Turing
- Ampere
- Ada Lovelace
- Hopper

### Continue Using Proprietary Drivers

For older GPUs from these architectures, open-source modules are incompatible:

- Maxwell
- Pascal
- Volta

### Mixed Deployments

> "For mixed deployments with older and newer GPUs in the same system, continue to use the proprietary driver."

(Not applicable to a pure B300 chassis — all 8 GPUs are Blackwell, so open is unambiguously the choice.)

## New Capabilities

The open-source modules now include:
- Heterogeneous memory management (HMM) support
- Confidential computing
- Coherent memory architectures of Grace platforms
- Performance equivalent to or better than proprietary drivers

## Installation & Migration

### Detection Helper

For uncertainty about GPU compatibility:
```bash
$ nvidia-driver-assistant
```

### Package Manager Commands

**Ubuntu/Debian:**
```bash
$ sudo apt-get install nvidia-open
$ sudo apt-get install nvidia-kernel-source-open
```

**Fedora/RHEL/Kylin:**
```bash
$ sudo dnf module install nvidia-driver:open-dkms
```

**SUSE/openSUSE:**
```bash
$ sudo zypper install nvidia-open
$ sudo zypper install nvidia-open-azure      # Azure kernel
$ sudo zypper install nvidia-open-64k        # 64kb kernel for Grace-Hopper
```

### Runfile Installation

To override driver type via command line:
```bash
$ sh ./cuda_12.6.0_560.22_linux.run --override --kernel-module-type=proprietary
$ sh ./NVIDIA-Linux-x86_64-560.run --kernel-module-type=proprietary
```

## CUDA Toolkit Integration

### CUDA 12.6 Changes

Before CUDA 12.6: Installing the `cuda` metapackage included the proprietary driver 555.

After CUDA 12.6: The default metapackage now includes the open-source driver 560.

Install CUDA Toolkit as usual:
```bash
$ sudo apt-get/dnf/zypper install cuda-toolkit
```

### Package Manager Summary

| Distro | Latest Installation | Specific Release |
|---|---|---|
| Fedora/RHEL/Kylin | `dnf module install nvidia-driver:open-dkms` | `dnf module install nvidia-driver:560-open` |
| openSUSE/SLES | `zypper install nvidia-open{-azure,-64k}` | `zypper install nvidia-open-560{-azure,-64k}` |
| Debian | `apt-get install nvidia-open` | `apt-get install nvidia-open-560` |
| Ubuntu | `apt-get install nvidia-open` | `apt-get install nvidia-open-560` |

## Special Considerations

### Windows Subsystem for Linux (WSL)

> "Windows Subsystem for Linux (WSL) uses the NVIDIA kernel driver from the host Windows operating system. You shouldn't install any driver into this platform specifically. If you are using WSL, no change or action is required."

### Datacenter vs. Consumer GPUs

The initial 2022 release targeted datacenter compute GPUs, with GeForce and Workstation GPUs in alpha. These now have full support in R560.
