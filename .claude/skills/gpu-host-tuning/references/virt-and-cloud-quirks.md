# Virt and cloud quirks — what hypervisors hide from inside the guest

When the audit runs inside a virtualized GPU instance (Verda, Lambda Cloud,
RunPod, Vast.ai, AWS, GCP, Azure, Oracle), several probes are blind by
design. The collector flags these explicitly with WARNING blocks; this file
explains what's lost and why.

Use this when interpreting cloud snapshots and diffing them against
bare-metal — many "differences" are virt artifacts, not real config gaps.

---

## What's universally hidden in QEMU/KVM/Hyper-V GPU guests (verified on Verda 2026)

### CPU power state surface — entirely empty

- `/sys/devices/system/cpu/cpu*/cpufreq/` directory empty
  → `22_cpu_freq_governor.txt` shows the WARNING block
- `/sys/devices/system/cpu/intel_pstate/` and `/amd_pstate/` absent
  → `23_pstate.txt` shows "intel_pstate: not present / amd_pstate: not present"
- `/sys/devices/system/cpu/cpu0/cpuidle/state*/` absent
  → `24_cstates.txt` shows the cpuidle WARNING
- `turbostat` returns "msr offset 0xe8 read failed: Input/output error"
  → `27_turbostat_5s.txt` is empty/error
- `cpupower` reports no driver, no available governors

**Why**: QEMU does not expose MSRs or the full cpufreq sysfs by default;
the host OS owns CPU power management. Guest cannot see or change governor.

**Implication for diff**: a Verda VM and a bare-metal box CANNOT be diffed on
power state. The bare-metal snapshot is the only place where governor /
EPP / C-state mask is visible. Diff focuses on everything else.

### NUMA topology — flattened

QEMU presents the CPUs as either:
- One big NUMA node (Verda's choice — `available: 1 nodes (0)`), or
- N "single-core sockets" in node 0 (which is what `lscpu` shows: `Socket(s):
  176, Core(s) per socket: 1, Thread(s) per core: 1`)

**Implication**: from inside the guest, `numactl --membind=0` is the only
node available. Cross-NUMA penalty experiments only work on the host or on
guests with explicit NUMA topology passed through (uncommon). Verda's 8H200
guest has 1 NUMA node — same as 2RTXPRO6000 — even though the underlying
chassis is 2-socket.

### BIOS / firmware identity

`dmidecode` shows BIOS Vendor as `EFI Development Kit II / OVMF` or just
`QEMU`, BIOS version typically `0.0.0`, with characteristic line `System is
a virtual machine`. No real Dell/SMC/HPE service tag.

**Implication**: cannot audit BIOS settings from inside a cloud VM. Cloud
provider's tuning is whatever they applied at the host layer. Take their
benchmarks as the ceiling and assume their tuning is good (mostly true for
specialized AI clouds; less true for general clouds).

### MSR access

Blocked. Affects:
- `turbostat` (needs MSRs for residency counters)
- `rdmsr` / `wrmsr` tools
- AMD Spec/Aldebaran-specific microbenches
- Hardware perf counters (see "perf" below)

### Hardware perf counters

`perf stat ...` returns most counters as `<not supported>`. Some clouds
expose limited per-vCPU counters; most don't. Profile-based tuning is
limited to wall-clock measurements + nvidia-smi metrics.

### DMI mostly empty

Directories like `/sys/class/dmi/id/board_serial` are stubs. Memory DIMM
info from `dmidecode -t memory` is fabricated by QEMU SMBIOS code — no
real DIMM speeds, no real channel layout.

---

## What IS visible (and useful) in cloud GPU guests

### Linux kernel state

Same as bare-metal:
- `/proc/cmdline` (the GUEST kernel cmdline — settable via cloud-init)
- `sysctl` values (settable normally)
- `ulimit` (settable normally)
- `/etc/security/limits.d/`
- THP, numa_balancing, swappiness, etc.

→ tuning here is the cloud user's responsibility, no virt limit.

### NVIDIA driver / GPU state

Almost identically visible:
- `nvidia-smi -q` full
- `nvidia-smi topo -m` (but flat — see above)
- Persistence Mode, ECC Mode, Power Limit, MIG Mode, clocks
- NVLink status (full per-link)
- PCIe link gen/width (the link from guest's PCIe domain to passthrough GPU)

### PCIe (within the guest's view)

`lspci -vvv` works — but the topology is QEMU's pcie root hierarchy, not
the host's. NVMe drives, virtio devices, and the passed-through GPU all
look like pcie devices on a virtual bus. Real PCIe link gen/width to the
GPU is correctly reported (it's the actual passthrough link).

### Container runtime

Identical to bare-metal — containerd, runc, nvidia-ctk all work normally.

---

## Per-cloud notes

### Verda (DataCrunch FIN-03)

- 8H200.141S.176V SKU = 8× H200 + 176 vCPU + 1450 GB RAM, 1 NUMA node visible
- 2RTXPRO6000.60V = 2× RTX PRO 6000 + 60 vCPU + 180 GB RAM, 1 NUMA node
- Image `ubuntu-24.04-cuda-12.8-open-docker` ships pip absent (stripped from
  python3 packages); use `apt install python3-pip` after first boot, OR
  bootstrap via the existing Docker + the vllm-openai container
- BIOS Vendor: `EFI Development Kit II / OVMF`, version `0.0.0`
- Underlying CPU on 8H200: AMD EPYC 9654 (Genoa, Zen 4), exposed as 176
  single-core sockets to QEMU
- ECC Mode on H200s: **Disabled** by default (gain ~6-12% HBM bandwidth)
- Persistence Mode: Enabled
- Cold boot to SSH-ready: ~1-3 min provisioning, then ~30s for SSHd
- `apt-get` may be locked by cloud-init / unattended-upgrades for the first
  few minutes after boot — wait for `fuser /var/lib/dpkg/lock` to return empty

### AWS p5/p5e (H100 / H200)

- NUMA usually visible: 2 nodes per p5 instance (matches the underlying
  Sapphire Rapids 2-socket EC2 host)
- Nitro hypervisor exposes more CPU info than QEMU/KVM — turbostat partial
- ECC: typically Enabled
- Recommended TuneD profile: `accelerator-performance` (RHEL/Amazon Linux)
- ENA NIC ring sizes default 4096 (good)

### GCP a3-megagpu / a3-edgeasync

- Custom hypervisor; GPU passthrough via gVNIC
- 1-2 NUMA nodes visible depending on size
- Persistence Mode: enabled in image
- 2025+ images include nvidia-tuned-profiles

### Lambda Labs / RunPod / Vast.ai

- Mix of bare-metal and virtualized; check `dmidecode` to tell.
- Pricing usually below AWS, but tuning can be inconsistent — always re-run
  the audit after `verda`-equivalent VM provisioning.

---

## Diff strategy: bare-metal vs cloud guest

When comparing a bare-metal snapshot to a cloud-VM snapshot, partition the
findings into three buckets:

1. **Genuine config deltas** (actionable on the bare-metal side):
   - kernel cmdline differences
   - sysctl values
   - ulimits
   - tuned profile applied vs not
   - NVIDIA driver state (persistence, ECC, power limit, clocks)
   - container runtime config

2. **Virt artifacts** (expect them, don't act):
   - `22_cpu_freq_governor.txt` empty in cloud, populated bare-metal
   - `24_cstates.txt` empty in cloud
   - `27_turbostat_5s.txt` failed in cloud
   - `numactl -H` 1 node in cloud, N nodes bare-metal
   - `dmidecode` BIOS Vendor differs (QEMU/OVMF vs Dell/SMC/HPE)
   - `BIOS Model name` `pc-q35-N.M` in cloud vs real chassis bare-metal

3. **Topology differences worth understanding**:
   - PCIe link gen/width (cloud may have host-side PCIe limits)
   - NIC firmware version
   - GPU UUID + VBIOS revision (different boards may have different VBIOS
     even within the same provider)

When you have a snapshot from a cloud GPU VM and want to compare it against
a bare-metal snapshot, partition deltas into the three buckets above before
acting on any of them. Bucket 2 entries are virt artifacts and should be
ignored; Bucket 1 is the actionable list.
