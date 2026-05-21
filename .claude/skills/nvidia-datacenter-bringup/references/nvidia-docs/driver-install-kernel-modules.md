# NVIDIA Driver Installation Guide — Kernel Modules

> Retrieved 2026-05-21 (partial — see live URL for full content) from https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/kernel-modules.html

## Open vs Proprietary Kernel Modules

The NVIDIA Linux GPU driver ships with two kernel module flavors:

**Open-source modules:**

> "These are only for Turing and newer architectures, and this is what you should use if you have one of those architectures."

**Proprietary modules:**

> "This is the flavor that NVIDIA has historically shipped and is required for older GPUs from the Maxwell, Pascal, or Volta architectures."

> **Skill-author note**: this chapter says "should use" for Turing and newer. The stronger claim — that **open modules are MANDATORY on Grace Hopper and Blackwell, and proprietary is unsupported** — comes from NVIDIA's separate transition blog at https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/. See [[open-modules-transition]] for the verbatim text. For B200/B300/B100, use open.

## DKMS vs Precompiled Modules on Ubuntu

The chapter does not differentiate between DKMS and precompiled module options. For Ubuntu 22.04/24.04, it points to:

- `# apt install nvidia-open` (open kernel modules, DKMS-built via `nvidia-dkms-open`)
- `# apt install cuda-drivers` (proprietary, DKMS-built via `nvidia-dkms`)

> **Skill-author note**: Ubuntu's archive provides an additional "precompiled, Canonical-signed" path via `linux-modules-nvidia-XXX[-open]-generic-hwe-24.04`. NVIDIA's CUDA repo only provides the DKMS path. On a Secure Boot host, the Canonical-precompiled path avoids MOK enrollment for the NVIDIA modules — but MOK is still required for DOCA-OFED, so the saving is marginal in practice for B300. See [[secure-boot]].

## Package Names

| Variant | NVIDIA CUDA repo package |
|---|---|
| Open modules (latest) | `nvidia-open` |
| Open modules (branch-specific, ≤ 580) | `nvidia-open-<branch>` e.g. `nvidia-open-580` |
| Proprietary (latest) | `cuda-drivers` |
| Proprietary (branch-specific) | `cuda-drivers-<branch>` |

(Per apt-cache verified 2026-05-21. The branch-specific `nvidia-open-<branch>` form is documented as removed at 590+ but still works because of the pinning mechanism.)
