# Install recipe

Full opinionated install sequence for a B300 host on Ubuntu 24.04 LTS. Read [[packages]] for what each package is and why. Read [[secure-boot]] for the MOK detail. Read [[airgap-mirror]] if the host has no internet.

## Step 0 — Dell baseboard firmware (Dell chassis only)

Before any OS-side work. See [[dell-firmware]] for the full procedure including the Redfish AC cycle gotcha. Required firmware floor for B300 SXM6 is `v1.4.30` (March 2026) which fixes the CX-8 MCTP enumeration bug that causes `nvidia-smi` to see no GPUs.

After flash, the activation requires `DellOemChassis.ExtendedReset`, NOT BIOS Full Power Cycle. Verify firmware versions via iDRAC Redfish `FirmwareInventory` before and after.

## Step 1 — OS prep

Fresh Ubuntu 24.04 server install. Then:

```bash
sudo apt update
sudo apt install -y linux-headers-$(uname -r) build-essential dkms

# Blacklist nouveau (NVIDIA driver requires this)
sudo tee /etc/modprobe.d/blacklist-nouveau.conf <<'EOF'
blacklist nouveau
options nouveau modeset=0
EOF
sudo update-initramfs -u
```

Optional but recommended for new Blackwell silicon: switch to HWE kernel. The 24.04 HWE kernel (currently 6.17.x via `linux-image-generic-hwe-24.04`) tracks newer kernels which often have fixes Blackwell needs:

```bash
sudo apt install -y linux-generic-hwe-24.04
sudo reboot
```

## Step 2 — Secure Boot + MOK

Required if Secure Boot is enabled (check with `sudo mokutil --sb-state`). One MOK signs both NVIDIA and DOCA-OFED modules. See [[secure-boot]] for full detail.

```bash
# First-time MOK key generation (creates /var/lib/dkms/mok.key and mok.pub)
sudo update-secureboot-policy --new-key

# Import the public half into the MOK list (interactive: set a one-shot password)
sudo mokutil --import /var/lib/dkms/mok.pub

# Reboot — MokManager prompts for the password to confirm enrollment
sudo reboot

# After reboot, confirm enrollment
sudo mokutil --list-enrolled | grep -i dkms
```

If SB is disabled (`SecureBoot disabled` in `mokutil --sb-state`), skip this step entirely.

## Step 3 — Add the NVIDIA CUDA repo + DOCA repo

### Connected mode

```bash
# CUDA repo (driver, FM, nvlsm, libnvsdm, nvlink5, container-toolkit)
curl -fsSL -O https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb

# DOCA repo (OFED, ib_umad, ConnectX-8 driver)
# Download the latest DOCA host repo deb from https://developer.nvidia.com/doca-downloads
sudo dpkg -i doca-host-*.deb

sudo apt update
```

### Air-gap mode

See [[airgap-mirror]] for the full mirror setup. After mirrors are in place:

```bash
# Trust the keyrings (one belt-and-braces keyring covering both DOCA key tiers)
sudo install -m 0644 cuda-archive-keyring.gpg /usr/share/keyrings/cuda-archive-keyring.gpg
sudo install -m 0644 nvidia-doca.gpg /etc/apt/keyrings/nvidia-doca.gpg

# Point apt at the local mirrors
sudo tee /etc/apt/sources.list.d/nvidia-cuda.sources <<'EOF'
Types: deb
URIs: file:///srv/nvidia-mirror/cuda/ubuntu2404/x86_64
Suites: ./
Signed-By: /usr/share/keyrings/cuda-archive-keyring.gpg
EOF

sudo tee /etc/apt/sources.list.d/nvidia-doca.sources <<'EOF'
Types: deb
URIs: file:///srv/nvidia-mirror/doca/latest-3.2-LTS/ubuntu24.04/x86_64
Suites: ./
Signed-By: /etc/apt/keyrings/nvidia-doca.gpg
EOF

sudo apt update
```

## Step 4 — Install DOCA FIRST

**Order matters.** If DOCA is installed AFTER the NVIDIA driver, `ib_umad` doesn't auto-load at boot and `nvidia-fabricmanager.service` fails. See [[troubleshooting]] for recovery if already broken.

```bash
sudo apt install -y doca-ofed
sudo /etc/init.d/openibd restart

# Confirm ib_umad loaded
lsmod | grep ib_umad
```

`doca-ofed` is the slim profile — OFED stack only, no DPDK / hcoll / sharp / firmware-updater. Use `doca-all` for the full set. The slim profile is sufficient for B300 fabricmanager.

The DOCA install triggers DKMS builds of the CX-8 modules. On a Secure Boot host these are auto-signed by the DKMS MOK and only load after MOK enrollment (Step 2).

## Step 5 — Pin the NVIDIA driver branch

```bash
sudo apt install -y nvidia-driver-pinning-580
```

Pick 580 (LTSB, gpu-operator 26.3.x default), 590, or 595 (latest). For B300 production, 580 LTSB is the conservative choice. See [[packages]] for the full branch matrix.

## Step 6 — Install the driver

```bash
# OPEN kernel modules — MANDATORY for Blackwell
sudo apt install -y nvidia-open-580
```

This pulls `nvidia-driver-580-open` (or `-server-open` depending on resolver), libnvidia-compute, nvidia-dkms-open, nvidia-modprobe, nvidia-persistenced, etc. DKMS builds the modules against the running kernel and signs them with the DKMS MOK.

After install, reboot to load the modules into the kernel:

```bash
sudo reboot

# After reboot
nvidia-smi --query-gpu=name,driver_version --format=csv
# Expect: 8 lines, each B300 with the installed driver version
```

If `nvidia-smi` reports no GPUs at this point, see [[troubleshooting]] § "nvidia-smi sees no GPUs". Likely culprits: baseboard firmware below v1.4.30, proprietary instead of open modules, or MOK not enrolled.

## Step 7 — Install the fabric stack

```bash
# Single meta pulls FM + NVLSM + libnvsdm + libibumad3 + infiniband-diags coherent to branch
sudo apt install -y nvlink5-580
```

If `nvlink5-580` is unavailable in the CUDA-repo snapshot (some patch levels don't ship the meta), fall back to explicit packages:

```bash
sudo apt install -y \
  nvidia-fabricmanager-580 \
  nvlsm \
  libnvsdm \
  libnvidia-nscq-580 \
  libibumad3 \
  infiniband-diags
```

Enable and start:

```bash
sudo systemctl enable --now nvidia-fabricmanager
sudo systemctl enable --now nvidia-nvlsm    # may already be running as a sub-service of FM

# Status check
systemctl status nvidia-fabricmanager
journalctl -u nvidia-fabricmanager -b --no-pager | tail -50
```

FM takes 30–90 s on first boot of an 8-GPU B300 to complete fabric registration. Wait for it.

## Step 8 — Container toolkit

```bash
sudo apt install -y nvidia-container-toolkit
```

The toolkit is in the same NVIDIA CUDA repo (verified 2026-05-21). No need for the separate `nvidia.github.io/libnvidia-container` apt source.

Configure the container runtime — for Docker:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

For containerd (k8s nodes):

```bash
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

## Step 9 — Validate

```bash
# All GPUs present with matching driver
nvidia-smi --query-gpu=name,driver_version --format=csv

# Services active
systemctl is-active nvidia-persistenced nvidia-fabricmanager nvidia-nvlsm

# Required modules loaded
lsmod | grep -E '^nvidia|^nvidia_uvm|^nvidia_peermem|^ib_umad'

# Fabric registration succeeded
nvidia-smi -q -i 0 | grep -A 2 Fabric
# Expect:
#   Fabric
#     State                : Completed
#     Status               : Success

# NVLink links active
nvidia-smi nvlink --status

# CX bridge devices identified (B200/B300 only)
lspci -nn | grep -i mellanox     # several ConnectX-7/8 devices visible
```

If any of these fail, see [[troubleshooting]] for symptom → cause → fix.

## Step 10 — gpu-operator (if running k8s)

Skill scope ends with the host healthy. For gpu-operator helm values for pre-installed driver mode and known issues including B300 #2231, see [[gpu-operator]].

Quick install (pre-installed driver mode, gpu-operator 26.3.x):

```bash
helm install --wait gpu-operator \
  -n gpu-operator --create-namespace \
  nvidia/gpu-operator \
  --version=v26.3.3 \
  --set driver.enabled=false \
  --set toolkit.enabled=false
```

Wait ~2 minutes for the cuda-validator pod to schedule and pass. On a fresh B300, the validator may CrashLoopBackoff for one or two iterations while FM completes fabric registration — that's normal. Sustained crashes past 3 minutes are real failures; see [[troubleshooting]] § "cuda-validator stuck".

## Driver-branch upgrades after first install

```bash
# Switch to a different branch (e.g. 580 → 595)
sudo apt install nvidia-driver-pinning-595
sudo apt dist-upgrade --autoremove --purge
sudo reboot
```

The new pinning package replaces the old; dist-upgrade pulls the matching driver, FM, NVLSM, and toolkit versions. Coherence is automatic because everything traces back through `nvlink5-<branch>` and `cuda-drivers-fabricmanager-<branch>` to the same branch.

## Kernel upgrades

DKMS rebuilds NVIDIA + DOCA-OFED modules automatically when a new kernel is installed, using the enrolled MOK. No manual re-enrollment needed for subsequent kernels — one-time setup only.

To lock the kernel (some sites do this for stability): `sudo apt-mark hold linux-image-generic-hwe-24.04 linux-headers-generic-hwe-24.04`. Trade-off: blocks security patches; gains predictability. Author judgment.
