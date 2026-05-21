# NVIDIA Driver Installation Guide — Ubuntu chapter

> Retrieved 2026-05-21 from https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/ubuntu.html

## Preparation

1. Complete the [Pre-installation Actions](pre-installation-actions.html).

2. Install kernel headers and development packages for the current kernel:

```bash
# apt install linux-headers-$(uname -r)
```

3. Choose an installation method: Local Repository Enablement or Network Repository Enablement (amd64/arm64).

## Local Repository Enablement

1. Download the NVIDIA driver repository:

```bash
$ wget https://developer.download.nvidia.com/compute/nvidia-driver/$version/local_installers/nvidia-driver-local-repo-$distro-$version_$arch.deb
```

Replace `$version` with the NVIDIA driver version.

2. Install the local repository:

```bash
# dpkg -i nvidia-driver-local-repo-$distro-$version_$arch.deb
# apt update
```

3. Enroll the ephemeral public GPG key:

```bash
# cp /var/nvidia-driver-local-repo-$distro-$version/nvidia-driver-*-keyring.gpg /usr/share/keyrings/
```

## Network Repository Enablement (amd64)

Install the cuda-keyring package:

```bash
$ wget https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/cuda-keyring_1.1-1_all.deb
# dpkg -i cuda-keyring_1.1-1_all.deb
# apt update
```

**Alternative method** (if cuda-keyring installation fails):

1. Enroll the signing key:

```bash
$ wget https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/cuda-archive-keyring.gpg
# mv cuda-archive-keyring.gpg /usr/share/keyrings/cuda-archive-keyring.gpg
```

2. Enable the network repository:

```bash
# echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/ /" \
    | tee /etc/apt/sources.list.d/cuda-$distro-$arch.list
```

## Network Repository Enablement (arm64)

Install the cuda-keyring package:

```bash
$ wget https://developer.download.nvidia.com/compute/cuda/repos/$distro/sbsa/cuda-keyring_1.1-1_all.deb
# dpkg -i cuda-keyring_1.1-1_all.deb
# apt update
```

**Alternative method** (if cuda-keyring installation fails):

1. Enroll the signing key:

```bash
$ wget https://developer.download.nvidia.com/compute/cuda/repos/$distro/sbsa/cuda-archive-keyring.gpg
# mv cuda-archive-keyring.gpg /usr/share/keyrings/cuda-archive-keyring.gpg
```

2. Enable the network repository:

```bash
# echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/$distro/sbsa/ /" \
    | tee /etc/apt/sources.list.d/cuda-$distro-$arch.list
```

## Selecting a Branch or Specific Driver Version

Pin your system to a specific branch or driver version by installing the appropriate pinning package:

```bash
# apt install nvidia-driver-pinning-<branch>
```

or

```bash
# apt install nvidia-driver-pinning-<version>
```

Install the pinning package before the driver for best results. See [Version locking](version-locking.html) for detailed information.

**Note:** Starting with branch 590, branch designation was removed from Ubuntu package names. Use version locking packages to manage branch and version switching.

> **Skill-author clarification**: "Ubuntu packages" in this note refers to NVIDIA-CUDA-repo Ubuntu packages, NOT Canonical-archive Ubuntu packages. Canonical's archive still uses branch suffixes (`nvidia-driver-595-server-open` etc.). On NVIDIA's CUDA repo, the suffix is dropped at 590+ and `nvidia-driver-pinning-XXX` controls the branch instead.

## Driver Installation

These instructions apply to both local and network installations.

**Open Kernel Modules:**

```bash
# apt install nvidia-open
```

**Proprietary Kernel Modules:**

```bash
# apt install cuda-drivers
```

> **Skill-author clarification**: For Blackwell (B200/B300), only the open kernel modules path is supported. Proprietary `cuda-drivers` will install but not bind. See [[open-modules-transition]].

## Compute-only (Headless) and Desktop-only (no Compute) Installation

Desktop components can be excluded to reduce footprint and dependencies. Excluded components may be added later.

### Compute-only System

**Open Kernel Modules:**

```bash
# apt -V install libnvidia-compute nvidia-dkms-open
```

**Proprietary Kernel Modules:**

```bash
# apt -V install libnvidia-compute nvidia-dkms
```

### Desktop-only System

**Open Kernel Modules:**

```bash
# apt -V install libnvidia-gl nvidia-dkms-open
```

**Proprietary Kernel Modules:**

```bash
# apt -V install libnvidia-gl nvidia-dkms
```

## Reboot the System

```bash
# reboot
```

Complete the [Post-installation Actions](post-installation-actions.html).

## Package Upgrades

When new versions are available, standard package update commands should suffice. If APT pinning is configured, adjust or remove the configuration before upgrading.

Upgrade the driver with:

```bash
# apt dist-upgrade
```

For a more aggressive upgrade that handles held back packages:

```bash
# apt dist-upgrade --autoremove --purge nvidia-open
```

This removes packages with removed dependencies.
