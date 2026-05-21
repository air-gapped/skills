# NVIDIA Driver Installation Guide — Advanced Options

> Retrieved 2026-05-21 from https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/advanced-options.html

## Switching between Driver Module Flavors

Replace `XXX` with the NVIDIA driver branch number (e.g., 595).

### Ubuntu 22.04/24.04

Switch from proprietary to open:
```bash
# apt install --autoremove --purge nvidia-open nvidia-driver-open
```

Switch from open to proprietary:
```bash
# apt install --autoremove --purge cuda-drivers nvidia-driver
```

> **Skill-author note**: B200/B300 must remain on open. The "switch to proprietary" path documented here is a footgun on Blackwell.

### Red Hat Enterprise Linux 8/9, AlmaLinux 8/9, Rocky Linux 8/9, Oracle Linux 8/9, Amazon Linux 2023, KylinOS 11

```bash
# dnf -y module switch-to nvidia-driver:<stream> --allowerasing
```

### Red Hat Enterprise Linux 10, AlmaLinux 10, Rocky Linux 10, Fedora 43

Switch from proprietary to open:
```bash
# dnf install --allowerasing nvidia-open
```

Switch from open to proprietary:
```bash
# dnf install --allowerasing cuda-drivers
```

For desktop or compute-only installations, switch only the kernel module package:
```bash
# dnf install --allowerasing kmod-nvidia-open-dkms
```

### Azure Linux 3

> "Only the open kernel modules are supported, no switching is possible."

### Debian 12/13

Switch from proprietary to open:
```bash
# apt install --autoremove --purge nvidia-open
```

Switch from open to proprietary:
```bash
# apt install --autoremove --purge cuda-drivers
```

### SUSE Linux Enterprise Server 15/16, OpenSUSE Leap 15/16

Switch from proprietary to open:
```bash
# zypper install --details --force-resolution nvidia-open
```

Switch from open to proprietary:
```bash
# zypper install --details --force-resolution cuda-drivers
```

## Meta Packages

Meta packages contain minimal files but specify multiple dependencies for convenience installation.

| Meta Package | Purpose |
|---|---|
| `nvidia-open` | Installs all NVIDIA Open GPU kernel modules; handles upgrades to next driver version |
| `nvidia-open` (version-locked) | Installs all NVIDIA Open GPU kernel modules; does not upgrade beyond 595.xxx branch |
| `cuda-drivers` | Installs all NVIDIA proprietary kernel modules; handles upgrades to next version |
| `cuda-drivers` (version-locked) | Installs all NVIDIA proprietary kernel modules; does not upgrade beyond 595.xx branch |

## Modularity Profiles

Available on Amazon Linux 2023, KylinOS 10, and Red Hat Enterprise Linux 8/9.

| Stream | Profile | Use Case |
|---|---|---|
| Default | `/default` | Installs all driver packages in a stream |
| NVSwitch Fabric | `/fm` | Installs driver packages plus NVSwitch bootstrapping components (Fabric Manager and NSCQ telemetry) |

Installation examples:
```bash
# dnf module install nvidia-driver:<stream>/default
# dnf module install nvidia-driver:<stream>/fm
```

Install multiple profiles with BASH brace expansion:
```bash
# dnf module install nvidia-driver:latest/{default,fm}
```

> **Skill-author note**: This `/fm` profile shortcut is RHEL-family only. There is no Ubuntu equivalent — on Ubuntu use `nvlink5-<branch>` (or explicit `nvidia-fabricmanager-<branch> + nvlsm + libnvsdm`) per [[recipe]].

## Restrict APT to Look for Specific Architectures

Modify repository entries in `/etc/apt/sources.list` and `/etc/apt/sources.list.d/` to prevent "404 Not Found" errors when foreign architectures are added.

Format:
```
deb [arch=<arch1>,<arch2>] <url>
```

Example restricting to amd64 and i386:
```
deb [arch=amd64,i386] <url>
```

No need to restrict `deb-src` repositories since they don't provide architecture-specific packages.

## APT Repository File not Found

If encountering `E: Failed to fetch file:/var/cuda-repo File not found` on Debian/Ubuntu systems after uninstalling a different driver version:

```bash
# rm -v /var/lib/apt/lists/*cuda* /var/lib/apt/lists/*nvidia*
```

## Verbose Versions when Using APT

Display verbose package version information during installation:

```bash
# apt install --verbose-versions nvidia-open
```
