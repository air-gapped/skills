# NVIDIA Fabric Manager User Guide — relevant chapters

> Offline copy of the chapters most relevant to B200/B300 bring-up on Ubuntu 24.04. Retrieved 2026-05-21 from https://docs.nvidia.com/datacenter/tesla/fabric-manager-user-guide/index.html. For the live full guide, consult that URL or the PDF mirror at https://docs.nvidia.com/datacenter/tesla/pdf/fabric-manager-user-guide.pdf (Release 2.3, May 2025).

## Overview

As deep learning neural networks grow more sophisticated, their computing demands expand exponentially. To address this challenge, applications leverage multi-GPU implementations. NVIDIA NVLink provides direct GPU-to-GPU interconnects that scale multi-GPU input/output in servers. NVIDIA NVSwitch extends this by connecting multiple NVLinks to enable all-to-all GPU communication at full NVLink speed.

This document guides users through setting up Fabric Manager, virtualization models, high-availability modes, and configuration details for NVSwitch-based single-node HGX and DGX systems.

## Terminology

| Abbreviation | Definition |
|---|---|
| FM | Fabric Manager |
| MMIO | Memory Mapped IO |
| VM | Virtual Machine |
| SBR | Secondary Bus Reset |
| DCGM | NVIDIA Data Center GPU Manager |
| NVML | NVIDIA Management Library |
| Service VM | Privileged VM running NVSwitch software stack |
| Access NVLink | GPU-to-NVSwitch connection |
| Trunk NVLink | GPU Baseboard-to-GPU Baseboard connection |
| SMBPBI | NVIDIA SMBus Post-Box Interface |
| vGPU | NVIDIA GRID Virtual GPU |
| MIG | Multi-Instance GPU |
| SR-IOV | Single-Root IO Virtualization |
| PF | Physical Function |
| FC PF | Full Capabilities Physical Function |
| LPF | Limited Physical Function |
| VF | Virtual Function |
| GFID | GPU Function Identification |
| Partition | GPU collection with NVLink P2P communication rights |
| ALI | Autonomous Link Initialization |
| OFED | Open Fabrics Enterprise Distribution Driver |
| MOFED | Mellanox/Nvidia OFED Driver package |
| NVLSM | NVLink Subnet Manager |
| NVSDM | NVLink Switch Device Manager |

## NVSwitch Core Software Stack

### Pre-Fourth Generation NVSwitches

The core software stack consists of an NVSwitch kernel driver and a privileged process called Fabric Manager (FM). The kernel driver manages low-level hardware in response to FM requests. The stack provides in-band and out-of-band monitoring for NVSwitch and GPU errors and status information.

### Fourth Generation NVSwitches

Fourth-generation NVSwitches use a unified architecture spanning NVLink, InfiniBand, and Ethernet switches. A new control plane entity called NVLink Subnet Manager (NVLSM) works with FM. NVLSM configures NVSwitch routing tables, while FM handles GPU-side routing, NVLink configuration, and partition management APIs. FM and NVLSM communicate through an Inter-Process Communication (IPC) interface.

**Note:** DGX B200/B300, NVIDIA HGX B200/B300, and NVIDIA HGX B100 systems use fourth-generation NVSwitches.

## What is Fabric Manager?

FM configures NVSwitch memory fabrics to form one unified memory fabric among participating GPUs and monitors supporting NVLinks. Key tasks include:

- Configuring routing among NVSwitch ports (pre-fourth generation)
- Setting up GPU routing and port mapping
- Coordinating with GPU drivers for GPU initialization
- Monitoring the fabric for NVLink and NVSwitch errors
- On ALI-incapable systems, coordinating NVLink initialization and training

## What is NVLink Subnet Manager?

NVLSM originated from InfiniBand networking and includes logic to program NVSwitches and NVLinks. Primary functions include:

- Discovering NVLink network topology
- Assigning local identifiers (LID) to GPU and NVSwitch NVLink ports
- Calculating and programming switch forwarding tables
- Programming Partition Key (PKEY) for NVLink partitions
- Monitoring NVLink fabric changes

## GPU Baseboard Topologies

### NVIDIA HGX B200/B300 GPU Baseboard

Contains eight B300/B200 GPUs and two fourth-generation NVSwitch ASICs. NVSwitches are not recognized as PCIe devices; instead, they connect through a CX7 Bridge device. Each port exposes one Full Capabilities PF (FC PF) and one Limited PF (LPF), totaling four PFs per baseboard.

**LPF roles:**
- Used by FM and NVLSM for configuration
- Used by telemetry agents (NVIBDM, DCGM)
- FLR reset also resets corresponding NVSwitch device

**FC PF roles:**
- Device administration functions
- NVSwitch resets
- Link enable/disable
- Does not support NVLink control plane or telemetry

Example `lspci` output:

```
05:00.0 Infiniband controller: Mellanox Technologies MT2910 Family [ConnectX-7]
05:00.1 Infiniband controller: Mellanox Technologies MT2910 Family [ConnectX-7]
1b:00.0 3D controller: NVIDIA Corporation Device 29bc
```

(NVIDIA device 29bc is the B300 GPU. The earlier B200 silicon shows different device IDs. B300 SXM6 air-cooled in the user's case has PCI device ID 0x3182 — that's referenced in gpu-operator issue #2231.)

## Getting Started with Fabric Manager

### Basic Components

#### The Fabric Manager Service

FM's core component runs as a UNIX daemon process. The installation package registers it as the `nvidia-fabricmanager` system service. On DGX B200/B300, NVIDIA HGX B200/B300, and NVIDIA HGX B100 systems, FM requires NVLSM. The systemd service file starts both FM and NVLSM processes when applicable.

#### Software Development Kit

FM provides a shared library, C/C++ APIs (SDK), and header files. These interface with the FM service to query/activate/deactivate GPU partitions in shared NVSwitch and vGPU multitenancy modes. SDK components install via a separate development package.

### Supported Platforms

#### Hardware Architectures

- x86_64
- aarch64

#### NVIDIA Server Architectures

- DGX-2 and NVIDIA HGX-2 (V100 GPUs, first-generation NVSwitches)
- DGX A100 and NVIDIA HGX A100 (A100 GPUs, second-generation NVSwitches)
- NVIDIA HGX A800 (A800 GPUs, second-generation NVSwitches)
- DGX H100 and NVIDIA HGX H100 (H100 GPUs, third-generation NVSwitches)
- NVIDIA HGX H800 (H800 GPUs, third-generation NVSwitches)
- DGX H200 and NVIDIA HGX H200 (H200 GPUs, third-generation NVSwitches)
- NVIDIA HGX H20 (H20 GPUs, third-generation NVSwitches)
- **DGX B200/B300 and NVIDIA HGX B200/B300 (B200/B300 GPUs, fourth-generation NVSwitches)**
- NVIDIA HGX B100 (B100 GPUs, fourth-generation NVSwitches)

#### OS Environment

FM supports these Linux distributions:

- RHEL/CentOS 7.x, 8.x, 9.x
- Ubuntu 18.04.x, 20.04.x, 22.04.x, 24.0x

**Kernel requirement note:** DGX B200/B300, NVIDIA HGX B200/B300, and NVIDIA HGX B100 require Linux kernel v5.17 or later. If using older kernels, NVIDIA provides required kernel patches for backporting.

### Other NVIDIA Software Packages

To run FM, systems must include compatible NVIDIA Data Center GPU drivers starting with version R450.

On DGX B200/B300, NVIDIA HGX B200/B300, and NVIDIA HGX B100 systems, an OFED or MOFED driver is required, plus:

```bash
apt-get install libibumad3
apt-get install infiniband-diags
```

**Note:** During initialization, FM checks loaded kernel driver stack version compatibility. If incompatible, the process aborts.

## Installation

### Minimum NVIDIA Driver/Fabric Manager Versions

- NVIDIA HGX-2 and NVIDIA HGX A100: version 450.xx
- NVIDIA HGX H100: version 525.xx
- **NVIDIA HGX B200/B300 and NVIDIA HGX B100: version 570.xx**

### Systems Using Fourth-Generation NVSwitches (B200/B300)

DGX B200/B300, NVIDIA HGX B200/B300, and NVIDIA HGX B100 systems require an additional NVLSM service dependency for proper operation.

**Debian/Ubuntu:**
```bash
sudo apt-get install -V nvidia-open-<driver-branch>
sudo apt-get install -V nvlink5-<driver-branch>
```

Example:
```bash
sudo apt-get install -V nvidia-open-570
sudo apt-get install -V nvlink5-570
```

> **Note from the skill author**: The doc text says `nvlink5-<driver-branch>` but apt-cache (verified 2026-05-21) shows the underlying packages are `nvlsm` (floating calver) plus `libnvsdm` and the fabric manager. The `nvlink5-<branch>` meta exists for 570, 575, 580 — confirmed live. Skill recommends installing the meta when available; explicit packages otherwise.

Additionally, install these required packages on B200/B300/B100 systems:

```bash
sudo apt-get install libibumad3
sudo apt-get install infiniband-diags
```

**Installation note:** The FM systemd service unit file is automatically registered during installation. On HGX systems, manually enable and start the service after installation.

## Initializing NVSwitch and NVLink

NVIDIA GPUs and NVSwitch fabrics function as PCIe endpoints requiring the NVIDIA kernel driver.

**On DGX H100, HGX H100, and later systems** (with ALI support): NVLinks are trained at hardware level without FM intervention. GPUs must register with the fabric for peer-to-peer capability. Failed registration results in loss of NVLink P2P functionality but permits non-P2P use. CUDA initialization begins after GPU fabric registration completes.

### Checking Fabric Registration Status

Query GPU fabric state via NVML APIs or `nvidia-smi`:

**In-progress registration:**
```bash
nvidia-smi -q -i 0 | grep -i -A 2 Fabric
         Fabric
            State                   : In Progress
            Status                  : N/A
```

**Successful registration:**
```bash
nvidia-smi -q -i 0 | grep -i -A 2 Fabric
          Fabric
            State                   : Completed
            Status                  : Success
```

### Service Restart Procedure for H100 and Later Systems

To ensure system coherence when restarting FM or NVLSM on H100/H200/H800 and later platforms:

1. Stop all CUDA applications and GPU services (e.g., DCGM). `nvidia-persistenced` may remain running.
2. Stop the FM service: `sudo systemctl stop nvidia-fabricmanager`
3. Reset GPUs: `sudo nvidia-smi -r`
4. Restart FM: `sudo systemctl start nvidia-fabricmanager`
5. Resume stopped services from step 1
6. Launch CUDA applications

## Additional Steps for NVIDIA HGX B200/B300 Systems

In HGX B200/B300 platforms, NVSwitches do not appear as discrete PCIe devices. They reside behind CX7 bridge devices. The four CX7 device physical functions must be passed to guest VMs. Through these CX7 bridges, FM and NVLSM configure underlying NVSwitches, NVLinks, and GPUs.

### Identifying CX7 Bridge Devices

To differentiate CX7 bridge devices (for NVLink management) from standard CX7 NIC devices:

#### Using Fixed PCIe BDF Assignment

The CX7 bridge device is integrated into the GPU baseboard. With static PCIe resource allocation, the four PF functions remain constant across reboots.

#### Using VPD Information

CX7 bridge devices possess distinct VPD (Vital Product Data) compared to traditional CX7 NICs. Query VPD using:

```bash
lspci -vvs <bdf>
```

or

```bash
vpddecode
```

The LPF (Limited Physical Function) VPD contains a vendor-specific field named `SMDL` with a non-zero value defined as `SW_MNG`. This differentiates management bridge devices.

**On Linux systems,** the FM service's prelaunch script queries CX7 devices for this VPD information and automatically populates FM and NVLSM configuration values (`FM_SM_MGMT_PORT_GUID`).

**For partial pass-through deployments,** additional hypervisor-level configuration is required to identify PF pairs belonging to each CX7 bridge port.

## Managing the Fabric Manager Service

```bash
sudo systemctl start nvidia-fabricmanager
sudo systemctl stop nvidia-fabricmanager
sudo systemctl status nvidia-fabricmanager
sudo systemctl enable nvidia-fabricmanager
sudo systemctl disable nvidia-fabricmanager
sudo journalctl -u nvidia-fabricmanager
```

## Fabric Manager Service File

The FM service unit file contains logic to start FM and NVLSM daemon processes depending on GPU baseboard variants. The installation registers FM using the systemd service unit file.

Modify startup options in: `/lib/systemd/system/nvidia-fabricmanager.service`

The service file invokes the `nv-fabricmanager-start.sh` script (default location: `/usr/bin/nv-fabricmanager-start.sh`) to selectively start FM and NVLSM based on platform.

**Important note:** The systemd and startup scripts assume default installation paths for PID files, binaries, and config files. If these paths are modified, updates must be made to both files and the startup script.

## Fabric Manager Config Options (subset relevant to B300)

Default config location: `/usr/share/nvidia/nvswitch/fabricmanager.cfg`

### Management Port GUID for Control Traffic

```
FM_SM_MGMT_PORT_GUID=<value>
```

U64 bit number queried from CX device allowing FM to communicate with underlying NVSwitches. On HGX B200/B300 systems with discovered CX bridge device for NVLink fabric management, FM service startup script populates this. Command-line argument takes precedence over config option.

**Default:** `FM_SM_MGMT_PORT_GUID=0x0`

### Socket for Fabric Manager and Subnet Manager Communication

```
FM_SM_IPC_INTERFACE=<value>
```

**Supported Values:**
- IPv4: `address:port`
- IPv6: `address:port`
- Unix: `//absolute_path to socket file`

**Default:** `FM_SM_IPC_INTERFACE=/var/run/nvidia-fabricmanager/fm_sm_ipc.socket`

### CUDA Jobs When Fabric Manager Service Stops/Terminates

```
ABORT_CUDA_JOBS_ON_FM_EXIT=<value>
```

**Supported Values:**
- `0` - Don't abort CUDA jobs on FM stop/exit; new job launch fails with `cudaErrorSystemNotReady`
- `1` - Abort all CUDA jobs on FM stop/exit; new job launch fails with `cudaErrorSystemNotReady`

**Default:** `ABORT_CUDA_JOBS_ON_FM_EXIT=1`

**Important note:** Not effective on DGX H100, NVIDIA HGX H100, and **later** NVSwitch-based systems (including B200/B300). Applies only to bare metal and full passthrough virtualization models.

### Setting Log Level

```
LOG_LEVEL=<value>
```

- `0` - All logging disabled
- `1` - CRITICAL and above
- `2` - ERROR and above
- `3` - WARNING and above
- `4` - INFO and above (default)

NVIDIA recommends running FM with INFO-level logging enabled for field issue troubleshooting.

### Setting Log File Location and Name

```
LOG_FILE_NAME=<value>
```

**Default:** `LOG_FILE_NAME=/var/log/fabricmanager.log`
