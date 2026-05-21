# NVIDIA DOCA Host Installation and Upgrade — Ubuntu 24.04

> Retrieved 2026-05-21 from https://docs.nvidia.com/doca/sdk/doca-host-installation-and-upgrade/index.html

## Prerequisites

Before installation, ensure:

- **Kernel headers** matching your running kernel version are installed
  - Verify via: `ls -la /lib/modules/$(uname -r)/build`
- **GCC version** must match the one used to build your kernel
- **DKMS ≥ 3.2** installed as a package

## Complete Uninstallation

If upgrading from DOCA-Host < 2.6.0, perform full uninstallation first:

```bash
for f in $( dpkg --list | grep -E 'doca|flexio|dpa-gdbserver|dpa-stats|dpa-resource-mgmt|dpaeumgmt|dpdk-community' | awk '{print $2}' ); do
  echo $f
  sudo apt remove --purge $f -y
done

sudo /usr/sbin/ofed_uninstall.sh --force
sudo apt-get autoremove
```

## Installation Steps

### 1. Add DOCA Repository

Download the DOCA host repository package from the [NVIDIA DOCA Downloads](https://developer.nvidia.com/doca-downloads) page for Ubuntu 24.04.

```bash
sudo dpkg -i doca-repo-ubuntu2404-*.deb
```

> **Skill-author note**: For air-gapped sites, mirror the DOCA repo directly from `https://linux.mellanox.com/public/repo/doca/latest-3.2-LTS/ubuntu24.04/x86_64/` (note: `ubuntu24.04` with dot) — the `doca-repo-ubuntu2404-*.deb` package just installs a sources.list pointing at that URL anyway. See [[airgap-mirror]].

### 2. Update Package Lists

```bash
sudo apt-get update
```

### 3. Install DOCA Profile

Install your preferred profile. For comprehensive DOCA support:

```bash
sudo apt install -y doca-all
```

Alternative profiles (choose one):
- `doca-host` – base host support
- `doca-ofed` – OFED stack support **← recommended for B300 fabricmanager**
- `doca-libvma` – VMA acceleration library
- `doca-libxlio` – XLIO acceleration library

### 4. Update Firmware

```bash
sudo apt install -y mlnx-fw-updater
```

> **Skill-author note**: For B300 in a Dell chassis, baseboard firmware is updated via iDRAC (see [[dell-firmware]]). `mlnx-fw-updater` is for the CX-8 NICs separately, not the GPU baseboard.

### 5. Load Drivers

```bash
sudo /etc/init.d/openibd restart
```

### 6. Initialize MST

```bash
sudo mst restart
```

## Secure Boot Configuration

For secure-boot-enabled systems, enroll DKMS-generated kernel module signing keys:

```bash
sudo mokutil --import /var/lib/dkms/mok.pub
```

Follow the prompts to create and confirm an enrollment password. Reboot the system and complete key enrollment via the MOK utility during boot.

> **Skill-author note**: The same MOK signs both DOCA-OFED and NVIDIA modules. Enroll once. See [[secure-boot]] for the full procedure.

## Upgrading Existing Installation

### From DOCA 2.6.0 or Later

```bash
sudo apt install doca-all
```

Or upgrade a specific profile:

```bash
sudo apt upgrade doca-ofed
```

Before upgrading `mlnx-fw-updater`, restart MST:

```bash
sudo mst restart
sudo apt upgrade mlnx-fw-updater
```

## Storage Installation

### NVMe and NFS-RDMA

Search for packages:

```bash
apt search mlnx-nvme
apt search mlnx-nfsrdma
```

Install by full package name:

```bash
sudo apt install mlnx-nvme-dkms
sudo apt install mlnx-nfsrdma-dkms
```

## VMA Installation

Install VMA with all required dependencies:

```bash
sudo apt install -y doca-libvma
```

Refer to [VMA documentation](https://docs.nvidia.com/networking/software/accelerator-software/index.html#vma) for system requirements.

## XLIO Installation

Install XLIO with all required dependencies:

```bash
sudo apt install -y doca-libxlio
```

Refer to [XLIO documentation](https://docs.nvidia.com/networking/software/accelerator-software/index.html#xlio) for system requirements.

## Kernel Module Rebuilding (Advanced)

For non-standard kernel versions, rebuild kernel modules:

```bash
sudo apt install -y doca-extra
sudo /opt/mellanox/doca/tools/doca-kernel-support
```

With module signing:

```bash
MODULE_SIGN_PUB_KEY=/path/to/pub_key.der \
MODULE_SIGN_PRIV_KEY=/path/to/priv_key.priv \
WITH_MOD_SIGN=1 \
/opt/mellanox/doca/tools/doca-kernel-support
```

Install the generated repository package:

```bash
sudo dpkg -i /tmp/DOCA.*/doca-kernel-repo-*.deb
sudo apt update
sudo apt install doca-ofed
```

## Verify Installation

Retrieve installed package versions:

```bash
/opt/mellanox/doca/tools/doca-info
```

If UEFI/ATF versions show "N/A" with BlueField version ≥ 2.7.0:

```bash
sudo /etc/init.d/openibd restart
```

## Package Signing

RPM packages are GPG-signed. Debian packages are verified automatically during `apt-get update`.

## Proprietary Packages

The following closed-source packages are not installed by default and require manual installation from RPM/DEB files:

- Clusterkit
- DPCP
- hcoll
- sharp
- ibutils2
- opensm
