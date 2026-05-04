# Recommended tunings — 2025/2026 lever cheat-sheet

Every lever the audit might flag, with the **exact command** to apply it, the
rationale, and the tradeoff. Indexed by audit-file number. Verify each against
the actual probe output before applying — context matters.

## Sections

- §A — CPU power (governor, EPP, C-states, turbo, HWP, HT)
- §B — Kernel boot params (cmdline + avoid list)
- §C — Runtime kernel state (THP, numa_balancing, swap, zone_reclaim, max_map_count, fs.file-max)
- §D — ulimits / locked memory (memlock, nofile, container ulimits)
- §E — IRQ affinity (irqbalance, NCCL-aware NIC pinning)
- §F — NVIDIA driver state (persistence, power limit, clocks, ECC, MIG, compute mode)
- §G — NCCL environment (single-node + multi-node IB)
- §H — Storage (NVMe scheduler, mount options, fs choice)
- §I — Container runtime (CDI, cgroup v2, kubelet config)
- §J — tuned-adm (DGX profiles + custom non-DGX templates)
- §K — BIOS levers (Dell/SMC/HPE recommended settings)
- §L — Mellanox / NVIDIA networking (mlnx_tune, MTU, ring sizes, TCP buffers)
- *Order of operations* — boot-time → tuned → per-lever → driver → container

**Default policy for inference hosts**: maximize bandwidth + minimize latency
+ minimize jitter, even at the cost of idle power and a few % security
mitigation overhead. These choices align with NVIDIA's `nvidia-tuned-profiles`,
Dell's "Performance" system profile, and the MLPerf submission settings.

---

## A. CPU power (audit files `22_cpu_freq_governor.txt`, `23_pstate.txt`, `24_cstates.txt`, `27_turbostat_5s.txt`)

### A.1 Governor → `performance`

```bash
# Set on every core, persistent via cpupower:
cpupower frequency-set -g performance
# Or directly to sysfs (use this when cpupower is missing):
for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance >"$c"
done
# Persist via systemd: enable cpupower.service or write a oneshot unit.
```

**When**: governor is `schedutil`, `powersave`, `ondemand`, or `conservative`.
On 2025+ Ubuntu desktop builds, `schedutil` is default and is too aggressive
about clocking down idle cores — adds ~5-30% latency to bursty inference.

**Tradeoff**: ~10-30 W extra idle power per socket. Not measurable on
inference-host bills.

### A.2 Intel EPP / amd-pstate EPP → `performance`

```bash
# Intel CPUs (HWP-capable: Skylake+ and all Xeon Scalable):
for f in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
    echo performance >"$f"
done

# AMD (EPYC Rome+, Ryzen 5000+ — `amd_pstate` driver in `active` or `guided` mode):
echo active >/sys/devices/system/cpu/amd_pstate/status   # if currently passive
for f in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
    echo performance >"$f"
done
```

**When**: EPP currently `balance_performance` (default), `default`, `power`, or
`balance_power`. EPP is a hint to HWP/CPPC about power-vs-perf bias *within*
the governor's frequency choice.

**Tradeoff**: same as governor — slightly higher idle power. On AMD, `guided`
EPP mode (kernel 6.3+) is a useful compromise for boxes that idle heavily; for
production inference, `active` + `performance` is the standard.

### A.3 Disable C-states deeper than C1

```bash
# Per-CPU PM-QoS — works on both Intel and AMD, no reboot:
for f in /sys/devices/system/cpu/cpu*/power/pm_qos_resume_latency_us; do
    echo 1 >"$f"   # cap exit latency at 1 µs → kernel won't pick C2/C6
done

# Or via cpupower (older kernels):
cpupower idle-set --disable-by-latency 1

# Or boot-permanent:
# kernel cmdline: processor.max_cstate=1 intel_idle.max_cstate=0
# (Intel — disables intel_idle and forces ACPI C1 only)
# kernel cmdline: idle=poll
# (extreme — never enters any idle state, ~5-10% extra power, lowest jitter)
```

**When**: `24_cstates.txt` shows C2 / C6 / C7 with latency > 50 µs **and**
`disable=0` for those states across many cores. C2 (400 µs exit latency on
Naples, 133 µs on SPR) adds wakeup jitter that shows up in TTFT P99.

**Tradeoff**: 50-100 W more idle power per socket. For latency-sensitive
inference (TTFT P99 SLA), worth it. For throughput-only batch workloads, leave
deep C-states enabled.

### A.4 Turbo / boost → enabled

```bash
# Intel (intel_pstate):
echo 0 >/sys/devices/system/cpu/intel_pstate/no_turbo

# AMD or legacy acpi-cpufreq:
echo 1 >/sys/devices/system/cpu/cpufreq/boost
```

**When**: `23_pstate.txt` shows `no_turbo = 1` or `boost = 0`. Turbo is
universally desirable for inference — single-thread bursts (prefill bound on
sequence prep) benefit hugely.

**Tradeoff**: very rarely worth disabling. Some MLPerf submissions disable it
for **reproducibility**, not for performance.

### A.5 HWP Dynamic Boost (Intel SPR/EMR)

```bash
echo 1 >/sys/devices/system/cpu/intel_pstate/hwp_dynamic_boost
```

**When**: file exists and shows 0. Enables short-burst over-Turbo on demand.

### A.6 Hyper-Threading — leave enabled

NVIDIA's MLPerf H200 SUTs run with HT on. Disable HT only when explicitly
profiling `cores=64` cgroup pinning with a measured regression.

---

## B. Kernel boot params (require reboot — `42_cmdline.txt`)

Edit `/etc/default/grub` `GRUB_CMDLINE_LINUX_DEFAULT=`, then `update-grub`
(Debian/Ubuntu) or `grub2-mkconfig -o /boot/grub2/grub.cfg` (RHEL/SUSE),
then reboot.

### B.1 Recommended set for an NVIDIA inference host (2025/2026)

```
mitigations=off                  # 5-15% Spectre/L1TF mitigation tax — only off if your security posture allows
intel_iommu=on iommu=pt          # passthrough mode — DMA without IOMMU translation overhead
                                 # (AMD: amd_iommu=on iommu=pt)
default_hugepagesz=1G hugepagesz=1G hugepages=N    # N depends on workload; 16-64 typical for KV cache
transparent_hugepage=madvise     # 6.x default; explicit-via-madvise() rather than always (avoids khugepaged stalls)
init_on_alloc=0                  # NVIDIA recommends — saves 1-3% on alloc
pcie_aspm=off                    # disable PCIe ASPM L0s/L1 — small static power cost, no L1-exit latency hits
nmi_watchdog=0                   # not actionable on most servers, frees a perf counter
nosoftlockup                     # avoid soft-lockup warnings under heavy compute
audit=0                          # if you don't need kernel auditing — saves ~1% syscall overhead
console=tty0 console=ttyS0,115200n8   # serial console for IPMI/iDRAC SoL debugging
pci=realloc=off                  # NVIDIA — needed for large GPU BAR allocation on some chassis
```

**For latency-critical / RT-ish (rare)**: also add
`isolcpus=<cpus> nohz_full=<cpus> rcu_nocbs=<cpus>` to dedicate cores to NCCL
workers. Pick cores from one NUMA node (the one nearest your GPUs in
`nvidia-smi topo -m`).

### B.2 Avoid (on 2025+ kernels)

- `clocksource=tsc` — kernel auto-selects on modern hardware; only force if dmesg shows tsc instability
- `numa=fake=N` — solves nothing on real NUMA, breaks memory accounting
- `selinux=0 / apparmor=0` — security regression with no measurable inference perf impact
- `ipv6.disable=1` — broke many inference frameworks that bind to `::1`

---

## C. Runtime kernel state (audit files `33_thp.txt`, `34_vm_tunables.txt`, `43_sysctl_all.txt`)

### C.1 THP

```bash
echo madvise >/sys/kernel/mm/transparent_hugepage/enabled    # explicit-via-madvise
echo defer  >/sys/kernel/mm/transparent_hugepage/defrag      # don't stall on alloc
```

**When**: `enabled = always` (causes khugepaged stalls under memory pressure)
or `enabled = never` (loses most of THP's benefit). 6.x default is `madvise`,
which is correct.

### C.2 numa_balancing → off

```bash
echo 0 >/proc/sys/kernel/numa_balancing
# Or via sysctl: sysctl -w kernel.numa_balancing=0
```

**When**: shows `1`. Auto-balancing migrates pages mid-flight, which causes
unpredictable latency spikes on inference workloads with stable working sets.
NCCL all-reduce P99 latency improves visibly with this off.

### C.3 swap → off / swappiness=1

```bash
swapoff -a   # immediate, no reboot
# Persist by removing/commenting swap entries from /etc/fstab
sysctl -w vm.swappiness=1
```

**When**: any swap is configured. Inference hosts must not swap — pinned
memory + swap = OOM kill cascade.

### C.4 zone_reclaim_mode → 0

```bash
sysctl -w vm.zone_reclaim_mode=0
```

**When**: shows non-zero (was default on some older RHEL). Forces
cross-NUMA-node reclaim before swapping; on inference boxes with steady-state
working sets this fights against numactl interleave.

### C.5 vm.max_map_count → high

```bash
sysctl -w vm.max_map_count=1048576
```

**When**: shows the 65530 default. Triton, vLLM with large MoE, and pytorch
distributed all need many mappings. K8s requires this for some CSI drivers.

### C.6 file descriptors

```bash
sysctl -w fs.file-max=10000000
sysctl -w fs.nr_open=10000000
```

**When**: defaults are low (1M). vLLM with high concurrency + LMCache + many
HF-cache files exhaust the default.

---

## D. ulimits / locked memory (audit files `44_ulimit_a.txt`, `45_security_limits.txt`)

### D.1 memlock → unlimited

```bash
# /etc/security/limits.d/99-inference.conf:
*    soft    memlock     unlimited
*    hard    memlock     unlimited
*    soft    nofile      1048576
*    hard    nofile      1048576
*    soft    stack       unlimited
*    hard    stack       unlimited
```

**When**: `ulimit -l` shows anything other than `unlimited` (default is
`64 KB`!). LMCache pinned-host buffer alloc fails → silently falls back to
non-pinned → 5-10× slower.

### D.2 Container ulimits

For docker/podman: `--ulimit memlock=-1 --ulimit stack=-1`.
For containerd default: edit `/etc/containerd/config.toml`,
`[plugins."io.containerd.runtime.v2.task".options] LimitMEMLOCK = "infinity"`.
For Kubernetes pods: add `securityContext.capabilities.add: ["IPC_LOCK"]`.

---

## E. IRQ affinity (audit file `49_irq_affinity.txt`)

### E.1 Disable irqbalance, pin manually

```bash
systemctl disable --now irqbalance
# Pin NIC IRQs off the inference cores. Example: pin all NIC TX/RX queues to core 0:
for i in $(awk '/mlx5_async/{print $1}' /proc/interrupts | sed 's/://'); do
    echo 0 >/proc/irq/$i/smp_affinity_list
done
```

**When**: `49_irq_affinity.txt` shows NIC IRQs spread across the cores you
plan to use for inference workers. Keep IRQs on housekeeping cores.

**Note**: NVIDIA DGX images set this via `tuned-adm profile dgx-h200-performance`
which includes `nvidia-base` (sets ARP/NIC tunings + relevant pinning hints).

### E.2 NCCL aware: pin NIC IRQs near the GPUs they serve

For multi-NIC boxes, use `nvidia-smi topo -m` to map each GPU to its near NIC,
then pin IRQs of that NIC to cores on the GPU's NUMA node.

---

## F. NVIDIA driver state (audit files `60_nvsmi_full.txt`, `63_nvsmi_clocks.txt`)

### F.1 Persistence Mode → ON

```bash
nvidia-smi -pm 1
# Persistent across reboot via systemd:
systemctl enable --now nvidia-persistenced
```

**When**: `60_nvsmi_full.txt` shows `Persistence Mode: Disabled`. Without this,
the driver tears down between CUDA contexts → 1-2s cold-start every time.

### F.2 Power limit → at TGP

```bash
nvidia-smi -pl 700    # H100/H200 SXM5 = 700 W
nvidia-smi -pl 1000   # B200 SXM6
nvidia-smi -pl 1100   # B300 SXM6 (Dell HGX NVL8 bin)
nvidia-smi -pl 600    # H100 NVL PCIe / RTX PRO 6000
```

**When**: `Power Limit` is below the GPU's TGP. Some chassis ship with
de-rated power limits for thermal headroom — re-set when cooling supports the
full TGP.

### F.3 Lock GPU & memory clocks

```bash
# Find the max:
nvidia-smi -q -d SUPPORTED_CLOCKS | head -40
# Lock SM and memory clocks (use the max from above):
nvidia-smi -lgc <max_gpu_mhz>
nvidia-smi -lmc <max_mem_mhz>
# Reset to auto:
nvidia-smi -rgc
nvidia-smi -rmc
```

**When**: workload is throughput-stable and zero clock-jitter on generation
latency is required. **Don't lock clocks for thermally-marginal cooling** — the
GPU will throttle harder than auto-management would.

### F.4 ECC — leave Enabled (production)

```bash
# Check:
nvidia-smi -q -d ECC
# Toggle (REQUIRES REBOOT to take effect):
nvidia-smi -e 1     # enable
nvidia-smi -e 0     # disable
```

**When**: production hosts → Enabled. Cloud GPUs sometimes ship Disabled for
6-12% extra HBM bandwidth — note this when comparing cloud to bare-metal.

### F.5 MIG — disabled for whole-GPU inference

```bash
nvidia-smi -mig 0    # disables MIG mode (REQUIRES no active CUDA contexts)
```

### F.6 Compute mode → DEFAULT

```bash
nvidia-smi -c DEFAULT    # multi-process; the only sane choice for vLLM/sglang
```

---

## G. NCCL environment (audit file `4A_env_vars.txt`)

These belong on the *workload* (vLLM pod, training job), not the host. But
they're often set per-host via systemd EnvironmentFile or via the K8s pod
spec. The audit captures whatever's in the running vllm process.

### G.1 Recommended baseline for H200 8× single-node

```bash
NCCL_P2P_LEVEL=NVL                # force NVLink-only P2P
NCCL_NVLS_ENABLE=1                # NVLink-Sharp on Hopper (default 1 since NCCL 2.20)
NCCL_MIN_NCHANNELS=4              # baseline for full NVLink mesh utilization
NCCL_DEBUG=WARN                   # change to INFO once for first run, then back
NCCL_SOCKET_IFNAME=^docker,lo     # avoid bridges
CUDA_DEVICE_MAX_CONNECTIONS=1     # Hopper: predictable launch ordering
CUDA_DEVICE_ORDER=PCI_BUS_ID      # consistent device numbering across reboots
```

### G.2 Multi-node IB additions

```bash
NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3   # adjust to your HCAs (ibstat)
NCCL_IB_GID_INDEX=3               # RoCE v2
NCCL_IB_TC=106                    # DSCP traffic-class for QoS
NCCL_IB_SL=3                      # service level
NCCL_CROSS_NIC=1                  # enable per-rail NIC selection
NCCL_IB_TIMEOUT=22                # higher than default for cross-AZ
NCCL_IB_RETRY_CNT=7
```

---

## H. Storage (audit files `85_io_scheduler.txt`, `82_nvme_list.txt`)

### H.1 NVMe scheduler → none

```bash
for q in /sys/block/nvme*n1/queue/scheduler; do
    echo none >"$q"
done
```

**When**: shows `mq-deadline` or `bfq` as active. NVMe firmware queue is
itself an mq scheduler — the kernel one is redundant overhead.

### H.2 Mount with `noatime` for the weights cache

```
# /etc/fstab
UUID=...  /var/lib/vllm-cache  ext4  defaults,noatime  0  0
```

### H.3 NVMe provisioning

For weight stores: prefer ext4 or XFS, NOT btrfs/zfs (CoW + checksum overhead
hurts large-sequential reads). Use `mkfs.ext4 -E lazy_itable_init=0
-O ^has_journal` for max throughput on read-heavy stores (no journal — only
safe for rebuildable caches).

---

## I. Container runtime (audit files `90_containerd_ver.txt`, `93_cdi_listing.txt`)

### I.1 Use CDI on containerd 2.0+

```bash
nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml
nvidia-ctk runtime configure --runtime=containerd --cdi.enabled=true
systemctl restart containerd
```

**When**: `93_cdi_listing.txt` shows no CDI specs. CDI is the GA-since-1.7
mechanism that gives the kubelet topology manager structured device info.
Without it, GPUs are opaque resources and topology hints degrade.

### I.2 cgroup v2 (default on kernel 5.x+ / Ubuntu 22.04+)

`94_cgroup_version.txt` should show `cgroup2fs`. If it shows `tmpfs`, the host
is on v1 — switch via `systemd.unified_cgroup_hierarchy=1` in kernel cmdline. K8s
1.25+ requires v2 for memory QoS.

### I.3 Kubelet config (RKE2)

`/etc/rancher/rke2/config.yaml`:

```yaml
kubelet-arg:
  - "cpu-manager-policy=static"
  - "topology-manager-policy=best-effort"
  - "topology-manager-scope=container"
  - "memory-manager-policy=Static"
  - "reserved-memory=0:memory=4Gi;1:memory=4Gi"
  - "kube-reserved=cpu=4,memory=8Gi"
  - "system-reserved=cpu=4,memory=8Gi"
  - "feature-gates=MemoryQoS=true"
```

**When**: `95_kubelet_config.txt` lacks any of the three managers as `static`.
For 8-GPU pods spanning both sockets: `topology-manager-policy=best-effort`
(not `restricted` — that would refuse admission).

---

## J. tuned-adm (preferred shortcut on RHEL/SLES/Ubuntu)

If `tuned` is installed and `nvidia-tuned-profiles` package is available,
this is the fastest path:

```bash
apt install tuned tuned-utils nvidia-tuned-profiles    # Ubuntu
dnf install tuned tuned-utils nvidia-tuned-profiles    # RHEL/SLES

systemctl enable --now tuned

# Pick the right profile for your platform:
tuned-adm profile dgx-h200-performance               # 8× H200 SXM5
tuned-adm profile dgx-b200-performance               # 8× B200 SXM6
tuned-adm profile dgx-b300-performance               # 8× B300 SXM6 DGX bin

# Combine with mitigations off (production with tight security perimeter):
tuned-adm profile dgx-h200-performance nvidia-no-mitigations

# Drift check:
tuned-adm verify
# This is the audit's drift-check equivalent — re-run anytime to confirm
# nothing has overridden the profile.

# Active profile + sources:
tuned-adm active
ls /etc/tuned/<profile>/   # custom overrides go here, persist across updates
```

For non-DGX hardware (Dell XE9680, Supermicro AS-8125, HPE Apollo 6500 ML270),
**create a custom profile** that inherits `nvidia-base` and adds chassis
specifics:

```ini
# /etc/tuned/dell-xe9680-h200/tuned.conf
[main]
summary=Dell XE9680 H200 8x — chassis-specific tuning
include=nvidia-base

[bootloader]
cmdline=iommu=pt processor.max_cstate=1 intel_idle.max_cstate=0 default_hugepagesz=1G hugepagesz=1G hugepages=64

[sysctl]
kernel.numa_balancing=0
vm.swappiness=1

[script]
script=apply.sh
```

See `references/tuned-profiles.md` for full templates.

---

## K. BIOS levers (require reboot, often via BMC — see `references/dell-xe9680.md`)

| Lever | Recommended | Why |
|---|---|---|
| System Profile | `Performance` (Dell) / `Maximum Performance` | Locks all sub-levers to the perf-biased default |
| Workload Profile | `AI/ML Optimized` if available | Vendor preset for accelerator workloads |
| C-States | Disabled, or limit to C1 | Same reasoning as A.3 — at the firmware layer this time |
| C1E | Disabled | Cluster-wide low-power state, adds wakeup jitter |
| Turbo Boost | Enabled | A.4 |
| Hyper-Threading | Enabled | NVIDIA MLPerf default |
| Sub-NUMA Clustering (SNC) | Disabled, or `SNC2` for explicit per-CCD topology | SPR `SNC2` exposes 4 NUMA nodes per dual-socket box. Off (Hemisphere mode) keeps 2 nodes — simpler for inference where NCCL spans both sockets |
| DDIO | Enabled (Intel default) | Direct cache placement for IB RDMA |
| Memory Operating Mode | Optimizer / Independent | Max bandwidth, vs Mirror/Sparing/Lockstep |
| Memory Patrol Scrub | Disabled | Lowers idle DDR5 traffic; tradeoff: less ECC error visibility (still corrected, just not reported until accessed) |
| Memory Refresh Rate | 1× (not 2×) | 2× halves bandwidth in extreme-temp scenarios — usually unneeded |
| Energy Efficient Turbo | Disabled | Caps Turbo at lower freq to save power |
| Hardware Prefetcher / DCU IP / DCU Streamer / LLC Prefetch | All Enabled (default) | Memory streaming wins outweigh L2/L3 contention |
| PCIe ASPM | Disabled | A.4 — same as kernel `pcie_aspm=off` |
| X2APIC | Enabled | Required for >256 logical CPUs and modern interrupt remapping |
| Above 4G Decoding | Enabled | Needed for large GPU BARs |
| Resizable BAR | Enabled | Required for full HBM-mapped access on Hopper/Blackwell |
| IOMMU | Enabled | Pairs with `iommu=pt` kernel arg |
| AMD: NPS | `NPS4` (Genoa) or `NPS2` | Per-CCD NUMA exposure for tighter memory locality |
| AMD: GMI / xGMI Speed | `Auto` or max manual | Inter-CCD link bandwidth |

See `references/dell-xe9680.md` for the slot-to-CPU map and exact menu paths
on Dell BIOS revisions 1.x through 2.x.

---

## L. Mellanox / NVIDIA networking (audit files `73_ibstat.txt`, `72_ethtool.txt`)

### L.1 mlnx_tune

```bash
mlnx_tune -p HIGH_THROUGHPUT     # set whole-system NIC profile
# Other profiles: HIGH_THROUGHPUT_AGGRESSIVE, LOW_LATENCY, HIGH_THROUGHPUT_SHORT_LIVED_TCP
```

`mlnx_tune` is what NVIDIA Networking ships for tuning ConnectX-6/7 +
BlueField — it sets governor, ring sizes, ASPM, IRQ affinity, MTU, ConnectX
firmware queues, and a few sysctls in one shot. Always re-run after a kernel
upgrade.

### L.2 Jumbo MTU (IB and high-speed Ethernet)

```bash
ip link set dev mlx5_0 mtu 9000      # IB devices
ip link set dev eth0   mtu 9000      # Ethernet — both sides of the link must agree
```

### L.3 Ring sizes

```bash
ethtool -G mlx5_0 rx 4096 tx 4096
```

### L.4 TCP buffers (large network buffers for high-BDP)

```bash
sysctl -w net.core.rmem_max=536870912     # ~512 MB
sysctl -w net.core.wmem_max=536870912
sysctl -w net.ipv4.tcp_rmem='4096 87380 268435456'
sysctl -w net.ipv4.tcp_wmem='4096 65536 268435456'
sysctl -w net.ipv4.tcp_congestion_control=bbr   # 2025+ kernels
```

---

## Order of operations when applying

1. **Boot-time first** (require reboot): kernel cmdline + BIOS levers. Plan one reboot.
2. **tuned-adm profile** (handles A, B, E, plus a few in C and L if `nvidia-base` covers them).
3. **Per-lever runtime fixes** for anything tuned didn't catch (audit-driven).
4. **NVIDIA driver state** (F): persistence, power limit, ECC.
5. **Container runtime + kubelet** (I): only after the host is otherwise tuned.
6. **Re-run audit + bench**: confirm the levers stuck and the H2D/D2H ceiling
   moved closer to the theoretical max for the chassis (see
   `references/session-findings.md` baselines).
