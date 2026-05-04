# tuned-adm profiles for inference hosts — pointer + templates

NVIDIA ships an authoritative `nvidia-tuned-profiles` package with per-DGX
profiles. Use it where you can; write a custom profile for non-DGX hardware.

---

## NVIDIA stock profiles (DGX-class hardware)

Available via the `nvidia-tuned-profiles` package on RHEL/SLES/Ubuntu (DGX
OS or installable from NVIDIA's repos). Verified profile names (DGX OS 6+
and DGX EL 10):

```
dgx-a100-performance       # DGX A100, 8× A100 SXM4
dgx-a800-performance       # DGX A800 China SKU
dgx-h100-performance       # DGX H100, 8× H100 SXM5
dgx-h200-performance       # DGX H200, 8× H200 SXM5  ← what NVIDIA's MLPerf H200 SUTs use
dgx-h800-performance       # DGX H800 China SKU
dgx-b200-performance       # DGX B200, 8× B200 SXM6
dgx-b300-performance       # DGX B300, 8× B300 SXM6 (DGX bin = 1400W TGP)

# Plus crashdump variants for each, e.g. dgx-h100-crashdump
```

### Composition

Each platform profile inherits two base profiles:

- **`nvidia-base`** — sets governor=performance, `init_on_alloc=0` kernel arg,
  `nvidia-persistenced` enabled, ARP/ICMP tuning, `nvidia-peermem` module
- **`dgx-base`** — adds `iommu=pt`, serial console (`console=ttyS0,115200n8`),
  `pci=realloc=off` (large GPU BAR support)

### Activation

```bash
# Install + enable:
apt install tuned tuned-utils nvidia-tuned-profiles    # Ubuntu
dnf install tuned tuned-utils nvidia-tuned-profiles    # RHEL/SLES
systemctl enable --now tuned

# List + activate:
tuned-adm list
tuned-adm profile dgx-h200-performance

# Verify the profile is fully applied (drift check):
tuned-adm verify
# This prints a list of any settings that have drifted from the profile's
# expectations. Run it after any reboot or manual sysctl change to confirm
# nothing has overridden the profile.

# Combine multiple profiles:
tuned-adm profile dgx-h200-performance nvidia-no-mitigations
# (Profiles merge in order; later overrides earlier.)

# Show what the active profile is doing:
tuned-adm active
tuned-adm profile_info dgx-h200-performance
```

### Storage

- System-shipped profiles: `/usr/lib/tuned/profiles/<name>/tuned.conf`
- Custom + overrides: `/etc/tuned/<name>/tuned.conf` (preserved across `dnf`/`apt` updates)

### Useful add-ons

- **`nvidia-no-mitigations`** — small profile that adds `mitigations=off` to
  cmdline. Stack onto a platform profile.
- **`accelerator-performance`** — Red Hat's generic GPU profile. Less
  specific than dgx-* but useful if `nvidia-tuned-profiles` isn't available
  (Ubuntu without NVIDIA repos).
- **`latency-performance`** — Red Hat's classic low-latency profile.
  Disables ondemand, sets governor=performance, raises priorities. Good
  starting point for non-DGX inference hosts.

---

## Custom profile templates (non-DGX hardware)

When `nvidia-tuned-profiles` is unavailable, or for chassis NVIDIA doesn't
ship a profile for (Dell XE9680, Supermicro AS-8125GS, HPE Apollo 6500 ML270,
Lenovo SR675 V3, custom whitebox), write your own profile that inherits
`nvidia-base` and adds chassis specifics.

### Template — `/etc/tuned/inference-h200/tuned.conf`

```ini
[main]
summary=Inference host with 8× H200 SXM5 — chassis-agnostic
include=throughput-performance

[bootloader]
cmdline=iommu=pt
cmdline_iommu_amd=amd_iommu=on
cmdline_hugepages=default_hugepagesz=1G hugepagesz=1G hugepages=64
cmdline_lowlatency=processor.max_cstate=1 intel_idle.max_cstate=0
cmdline_pci=pci=realloc=off pcie_aspm=off
cmdline_init=init_on_alloc=0
cmdline_serial=console=tty0 console=ttyS0,115200n8

[sysctl]
kernel.numa_balancing=0
vm.swappiness=1
vm.zone_reclaim_mode=0
vm.max_map_count=1048576
vm.overcommit_memory=1
fs.file-max=10000000
fs.nr_open=10000000
net.core.rmem_max=536870912
net.core.wmem_max=536870912
net.ipv4.tcp_rmem=4096 87380 268435456
net.ipv4.tcp_wmem=4096 65536 268435456
net.ipv4.tcp_congestion_control=bbr
net.core.netdev_max_backlog=250000

[vm]
transparent_hugepages=madvise

[cpu]
governor=performance
energy_perf_bias=performance
min_perf_pct=100
force_latency=1     # caps PM-QoS latency at 1µs → C-states deeper than C1 disabled

[disk]
elevator=none       # NVMe queue is internal; kernel scheduler is overhead

[script]
script=apply.sh
```

### Optional `apply.sh` for runtime fixes the [sysctl]/[cpu]/[bootloader] sections can't express

```bash
#!/usr/bin/env bash
# Tuned variable expansion: $1 = "start" or "stop"
[[ "$1" == "start" ]] || exit 0

# nvidia-smi-side state — only valid when nvidia driver is loaded
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    nvidia-smi -pm 1                               # persistence mode
    # Lock GPU clocks at max for thermally-stable hosts
    # nvidia-smi -lgc <max_mhz>
fi

# Disable irqbalance
systemctl disable --now irqbalance 2>/dev/null

# Set ulimits for the inference user (limits.d preferred over here):
# ulimit -l unlimited; ulimit -n 1048576
```

### Activation

```bash
mkdir -p /etc/tuned/inference-h200
# Copy tuned.conf and apply.sh into place.
chmod +x /etc/tuned/inference-h200/apply.sh
tuned-adm profile inference-h200
tuned-adm verify
reboot          # for [bootloader] changes to take effect
```

---

## Per-vendor profile starting points

Snippet differences from the generic template above. Only the deltas:

### Dell PowerEdge XE9680 / XE9785 / XE9785L

```ini
# /etc/tuned/dell-xe96xx/tuned.conf
[main]
summary=Dell PowerEdge XE96xx (XE9680 H100/H200, XE9785 B300, XE9785L)
include=inference-h200

[bootloader]
# Dell BIOS often defaults `mlx5` to `roce_mode=2` which is right.
# Add the relevant Dell-recommended cmdline args:
cmdline_dell=transparent_hugepage=never  # only if you cannot set madvise via sysctl
                                         # (Dell HPC tuning historically prefers `never`,
                                         # 2025 inference best practice is `madvise`)
```

Pair this with the BIOS settings in `dell-xe9680.md`.

### Supermicro AS-8125GS-TNHR / SYS-821GE-TNHR

Supermicro doesn't ship a tuned profile. Use the generic template; their
"Maximum Performance" BIOS preset is similar to Dell's "Performance" system
profile.

### HPE Apollo 6500 Gen11 / ProLiant XL645d

HPE has a `hpe-server-performance` tuned profile in some PSP releases. If
absent, use the generic. HPE iLO has a "OS Control" power mode (recommended
for tuned to work) vs "Static High" (BIOS-only).

### AMD-CPU + NVIDIA-GPU boxes (Genoa/Bergamo + H100/H200)

```ini
# Add to bootloader:
cmdline_amd=amd_iommu=on
# AMD's `amd-pstate-epp` (kernel 6.5+) handles governor + EPP correctly.
# No need to override [cpu] beyond the generic; Genoa+ supports HWP-equivalent.
```

NPS (NUMA per Socket) setting is in BIOS, not the kernel — see
`recommended-tunings.md` §K.

### Grace-Hopper / Grace-Blackwell (GH200 / GB200 / GB300)

NVIDIA ships **`nvidia-grace-performance`** for these; auto-detected. Combine
with `dgx-h200-performance` doesn't apply — Grace is a different boot chain
(no x86 BIOS, EDK II + arm64 cmdline).

---

## Troubleshooting `tuned-adm verify`

When `tuned-adm verify` reports drift, the message points at the file +
expected vs current. Common causes:

| Drift | Cause | Fix |
|---|---|---|
| `governor != performance` | Some service (often `power-profiles-daemon`) is overriding | `systemctl mask power-profiles-daemon` |
| `transparent_hugepage != madvise` | Distro post-install hook | Hard-set in `[vm]` section, also `/etc/default/grub` cmdline |
| `pcie_aspm != off` | Kernel cmdline ignored | Confirm `pcie_aspm` arg in `/proc/cmdline`; UEFI may force-override — disable in BIOS |
| Per-CPU `pm_qos_resume_latency_us != 1` | Other service writes to it | Check `systemd-rfkill` and any `tuned-ppd` package; mask offenders |
| `kernel.numa_balancing != 0` | systemd unit re-enabling on boot | `systemctl mask systemd-numa-balance.service` if present |

---

## Sources

- NVIDIA DGX Software for RHEL 10 — Managing and Customizing TuneD Profiles:
  https://docs.nvidia.com/dgx/dgx-el10-user-guide/modifying-tuned.html
- NVIDIA — BIOS Performance Tuning Example:
  https://enterprise-support.nvidia.com/s/article/bios-performance-tuning-example
- NVIDIA — Understanding BIOS Configuration for Performance Tuning:
  https://enterprise-support.nvidia.com/s/article/understanding-bios-configuration-for-performance-tuning
- Red Hat — TuneD documentation: `man tuned-adm`, `man tuned.conf`
- SUSE — Adaptive and dynamic tuning using TuneD (SLES 15 SP7):
  https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-tuning-tuned.html
