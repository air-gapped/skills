# Probe interpretation — what each audit file means

For each file produced by `scripts/collect.sh`: what it shows, what an OK
value looks like, what's surprising, and which lever in `recommended-tunings.md`
fixes it.

---

## 00-09 — Meta

### `00_meta.txt`
Collector version, run timestamp, host, args. Used for diff-ing two snapshots
(skip these lines when comparing).

---

## 10-19 — System + firmware

### `10_dmidecode_system.txt`
BIOS / Baseboard / Chassis. Look for:
- **`BIOS Vendor`** — `Dell Inc.`, `Supermicro`, `American Megatrends`, `HPE`.
  `EFI Development Kit II / OVMF` or `QEMU` = virtualized guest (see
  `virt-and-cloud-quirks.md`).
- **`BIOS Version`** + `Release Date` — older than 6 months may lack microcode
  for current Spectre/Meltdown / RAS fixes.
- **`Family`** + `Product Name` — chassis SKU. Cross-reference with vendor
  tuning guide (e.g. `dell-xe9680.md`).

### `11_dmidecode_processor.txt`
Per-socket CPU info. Confirm:
- Socket count matches vendor chassis spec (XE9680 = 2 sockets, single-socket
  Naples-class home box = 1 socket).
- Stepping + microcode revision are current.
- TDP under "Max Speed" / "External Clock" sanity-checks the part number
  (e.g., 8480C = 350W TDP).

### `12_dmidecode_memory.txt`
Per-DIMM info. **The biggest source of "why is bandwidth low" findings.**
- Look at every Locator (CPU0_DIMM_A1 … H2 etc).
- **`Size`** — full population vs sparse. SPR/EMR full = 16 DIMMs/socket = 32
  DIMMs/system. Sparse = 8 DIMMs/socket = ~50% bandwidth.
- **`Configured Memory Speed`** — 4800 MT/s (SPR), 5600 MT/s (EMR), 6400 MT/s
  (Granite Rapids). Configured *below* `Speed` (max) means BIOS or 2DPC limit.
- **`Manufacturer` / `Part Number`** — mixed parts on the same channel can
  cause IF/UPI links to negotiate down.

### `13_dmi_id.txt`
`/sys/class/dmi/id/*` flat dump. Same info as dmidecode, but accessible
without root. Convenient for grep.

### `14_lshw_short.txt`, `15_lscpu.txt`, `16_hostnamectl.txt`
Tree views. `lscpu` is the fastest way to confirm:
- `BIOS Model name:` showing `pc-q35-N.M CPU` ⇒ QEMU guest
- `Socket(s)` × `Core(s) per socket` × `Thread(s) per core` = total CPUs
- `NUMA node(s)` ≠ 1 means real NUMA visible

---

## 20-29 — CPU + power + C-states + thermal

### `20_cpuinfo_first.txt`
First-stanza of `/proc/cpuinfo`. Check **`flags`** for:
- `pdpe1gb` — 1GB hugepage support (should be present on all server CPUs)
- `avx512f`, `avx512_bf16`, `avx512_vnni` — AI-relevant SIMD (SPR/Genoa+)
- `amx_bf16`, `amx_int8`, `amx_tile` — Sapphire/Emerald Rapids AMX accelerators
- `ibrs_enhanced` — hardware Spectre v2 mitigation (cheaper than software IBRS)
- `pku` / `ospke` — protection keys (memory isolation, sometimes used by
  pinned-memory frameworks)

### `22_cpu_freq_governor.txt`
Output is empty + `WARNING: cpufreq sysfs not exposed` ⇒ virtualized guest.
On bare metal, expect:
- **`scaling_driver`**: `intel_pstate` (Intel HWP-capable), `amd-pstate-epp`
  (Genoa+ Linux 6.5+), `acpi-cpufreq` (older AMD or Intel without HWP)
- **`scaling_governor`**: `performance` ✓ — fix per `recommended-tunings.md` §A.1
  if `schedutil` / `powersave` / `ondemand`
- **EPP**: `performance` ✓ — fix per §A.2 if `balance_performance` / `default`
  / `power`
- **min/max/hwmax**: max should equal hwmax. If max < hwmax, governor is
  capped (look in `23_pstate.txt` for `max_perf_pct`).

### `23_pstate.txt`
- `intel_pstate.status = active` (HWP) or `passive` (legacy P-state). `active`
  is correct for SPR/EMR/Granite.
- `intel_pstate.no_turbo = 0` ✓
- `hwp_dynamic_boost = 1` (when supported)
- `amd_pstate.status = active` or `guided` (kernel 6.3+); `passive` is the old
  behavior, equivalent to acpi-cpufreq
- Old hardware: `acpi-cpufreq boost = 1`

### `24_cstates.txt`
**Critical for latency.** Look for:
- Per-state list: `state0 POLL (0µs)`, `state1 C1 (1-2µs)`,
  `state2 C1E or C2 (10-400µs)`, `state3 C6 (>100µs on Intel)`.
- Disable distribution: `state2  64 0` means "across all 64 CPUs, disable=0
  (i.e. enabled)". You want all states deeper than C1 to show `64 1` (i.e.
  disabled) on a latency-tuned host.
- `pm_qos_resume_latency_us` distinct values: `0` = unconstrained (deep
  C-states allowed), `1`/`2` = limit to C1 only.

Fix per `recommended-tunings.md` §A.3.

### `25_cpupower_freq.txt`, `26_cpupower_idle.txt`
Pretty-printed cpupower output. Sanity-check governor + per-state info match
sysfs.

### `27_turbostat_5s.txt`
5-second snapshot of busy% + C-state residency + package power. **Empty file
or "msr offset 0xe8 read failed" = virtualized guest** (MSRs blocked).
On bare metal, look for:
- **`Bzy_MHz`** column: should hover near max-Turbo when CPUs are busy. Falling
  to base clock under load = thermal throttling or governor mis-set.
- **`POLL%` / `C1%` / `C2%`** columns: residency in each state. If `C2%` is
  high (>50%) on idle cores, deep states are doing what they should. On a
  *latency-locked* host, you want everything in C1 or POLL.
- **`PkgWatt`**: package power. Compare against TDP — idle of ~30% TDP is
  normal for SPR/Genoa server parts.
- **`CorWatt` per core**: anomaly if one core is way hotter — possibly a
  pinned process keeping it busy, or a hardware fault.

### `28_vulnerabilities.txt`
Per-vulnerability mitigation status from `/sys/devices/system/cpu/vulnerabilities/`.
- `Mitigation: ...` → mitigation active (perf cost varies, 0-15%)
- `Vulnerable` → not mitigated (microcode missing, or `mitigations=off` in cmdline)
- `Not affected` → hardware is immune

### `29_microcode_dmesg.txt`
Microcode version + early boot. `microcode: updated to revision 0x...` is
fine. `microcode: ucode loading not allowed` = blocked by `dis_ucode_ldr`
or filesystem issue.

### `2A_thermal.txt`
Thermal zones. Pkg temp > 80 °C under idle = cooling problem. CPU pkg crit
threshold typically 95-105 °C; you want >20 °C margin under load.

---

## 30-39 — Memory + NUMA

### `30_numactl_H.txt`
- **`available: N nodes`** — real NUMA layout. 1 node on a 2-socket box ⇒
  virt flattening (see `virt-and-cloud-quirks.md`) or BIOS has SNC disabled.
- **per-node CPU lists** — should be contiguous + match
  `nvidia-smi topo -m` GPU NUMA affinities.
- **per-node free** — Linux's free counter; **NOT MemAvailable**. Page cache
  shows as "used" here. Use `31_meminfo.txt` for the real picture.
- **`node distances` matrix**: `10` for self, `12-21` for cross-node,
  `>21` for cross-CCD-but-same-socket (Naples) or chiplet-aware distances.

### `31_meminfo.txt`
The authoritative memory state:
- **`MemAvailable`** = the real "headroom for new allocations" number
- **`Buffers + Cached`** = page cache (reclaimable)
- **`AnonPages`** = real RSS in use by processes
- **`HugePages_Total / HugePages_Free`** = explicit hugepages
- **`Hugetlb`** = total hugepage memory (KB)
- **`SwapTotal`** = should be `0` ✓ (per `recommended-tunings.md` §C.3)

### `33_thp.txt`
- `enabled = madvise` ✓ (kernel 6.x default, correct for inference)
- `enabled = always` → fix to `madvise` (avoids khugepaged stalls)
- `enabled = never` → fix to `madvise` (loses hugepage benefit)
- `defrag = defer` or `defer+madvise` ✓ (don't stall syscalls on fragmented memory)
- `defrag = always` → too aggressive

### `34_vm_tunables.txt`
- `numa_balancing = 0` ✓ (per §C.2)
- `swappiness = 1` ✓ (per §C.3)
- `zone_reclaim_mode = 0` ✓ (per §C.4)
- `nr_hugepages` matches what you allocated at boot
- Per-node 1GB hugepages: `nr=N free=M`

---

## 40-49 — Kernel, boot, sysctl, ulimits, IRQ, env

### `42_cmdline.txt`
Full kernel boot args. Cross-reference with `recommended-tunings.md` §B.1:
- Missing `mitigations=off` → 5-15% perf tax remains
- Missing `iommu=pt` → DMA translation overhead
- Missing `default_hugepagesz=1G hugepages=N` → no 1GB hugepages
- Missing `init_on_alloc=0` → small alloc tax
- Missing `pcie_aspm=off` → potential PCIe L1 exit-latency hits

### `43_sysctl_all.txt`
Full sysctl dump. `grep` for the keys in §C.1-C.6. Particularly:
- `kernel.numa_balancing`
- `vm.swappiness`, `vm.zone_reclaim_mode`, `vm.max_map_count`
- `net.core.rmem_max`, `net.core.wmem_max` (need ~512MB for fast networks)
- `net.ipv4.tcp_congestion_control` (`bbr` or `cubic`)
- `fs.file-max`, `fs.nr_open`

### `44_ulimit_a.txt`
- **`max locked memory  (kbytes, -l)`** must be `unlimited` ✓ for LMCache /
  pinned alloc to work without silent fallback.
- `open files (-n)` should be 1M+ for high-concurrency vLLM.
- `stack size (-s)` = `8192` (default) is fine.

### `45_security_limits.txt`
Persistent ulimits. Should match §D.1 — `99-inference.conf` (or similar)
setting memlock/nofile to unlimited.

### `46_dmesg_first.txt`
First 200 lines of dmesg — early boot. Look for:
- `microcode: updated`
- `IOMMU: ... initialized`
- `nvme*: queue depth`
- `mlx5_core: ... firmware version`

### `47_dmesg_pcie.txt`
PCIe + NUMA + IOMMU + nvidia + nvme dmesg matches. Look for:
- `pcieport ...: Bus number ... not enough` ⇒ resource exhaustion
- `AER: ...` ⇒ correctable/fatal PCIe errors
- `nvidia 0000:..: BAR 1: ... not within available BAR space` ⇒ Above4G
  decoding off in BIOS

### `48_loaded_modules.txt`
- `nvidia` module loaded
- `nvidia_uvm` for unified memory
- `nvidia_peermem` (or `nvidia-peermem`) for GPUDirect RDMA — required for
  Mellanox + NVIDIA P2P
- `mlx5_core`, `mlx5_ib`, `ib_uverbs` for RDMA stack

### `49_irq_affinity.txt`
Top 30 IRQs by event count + their `smp_affinity_list`. Look for:
- Network IRQs (mlx5_async, virtio2-req, ena*) — should NOT be on the
  cores you intend to use for inference workers.
- `irqbalance` running (`systemctl is-active irqbalance` line) — usually
  best to disable on inference hosts in favor of manual pinning.

### `4A_env_vars.txt`
Captures NCCL/CUDA/HF/VLLM/LMCACHE env vars from PID 1 + any running
vllm process. Cross-reference with `recommended-tunings.md` §G.

---

## 50-59 — PCIe

### `50_lspci_tree.txt`
Tree view (`lspci -tv`). Useful to see physical topology — which root ports
hold which devices.

### `51_lspci_full.txt`
**The big one.** Full `lspci -vvv -nn`. For each NVIDIA + NIC device:
- **`LnkCap`** — what the device supports (e.g. `Speed 32GT/s, Width x16`
  for PCIe Gen5 x16)
- **`LnkSta`** — what the link is currently trained at. **Compare to LnkCap**.
  - `(downgraded)` annotation = link below capability — under load it may retrain
  - `Speed 2.5GT/s` = Gen 1 (idle ASPM-like state on most modern chassis)
  - `Speed 8GT/s` = Gen 3
  - `Speed 16GT/s` = Gen 4
  - `Speed 32GT/s` = Gen 5
- **`MaxPayload`** — typically 256 or 512. Higher is better for bulk DMA.
- **`MaxReadReq`** — typically 512 or 4096. NICs often want 4096.
- **`ASPM`** — `Disabled` ✓ (per §B.1 `pcie_aspm=off`)

### `52_lspci_nvidia.txt`
NVIDIA-only filter — same data as 51 but easier to grep.

### `53_lspci_aer.txt`
PCIe Advanced Error Reporting counters. **Any non-zero counter is a
finding**:
- `aer_dev_correctable` non-zero = link errors being corrected (often
  cabling / connector issues, sometimes BIOS firmware bugs)
- `aer_dev_fatal` non-zero = at-the-edge of failure

---

## 60-69 — GPU

### `60_nvsmi_full.txt`
`nvidia-smi -q` complete dump. The treasure-trove. Per-GPU look for:
- **`Persistence Mode`**: `Enabled` ✓ (per §F.1)
- **`Power Limit > Default Power Limit`**: leave at TGP unless explicitly de-rated
- **`ECC Mode > Current`**: `Enabled` (production) or `Disabled` (cloud
  cost-optimized — gain ~6-12% HBM BW at the cost of error visibility)
- **`MIG Mode > Current`**: `Disabled` (whole-GPU inference)
- **`PCIe Generation > Current` / `Link Width > Current`**: at idle these
  may show `1` / `8x` (downgrade). Re-check under load.
- **`Clocks Throttle Reasons > ...`**: `Not Active` for everything ✓.
  `HW Slowdown` / `HW Thermal Slowdown` / `SW Power Cap` = problem.
- **`Temperature > GPU Current Temp`**: degradation starts mid-70s, >88 °C
  flag, >90 °C broken (per Modal's threshold in `bringup-recipe.md`).
- **`ECC Errors > Volatile / Aggregate`**: any uncorrectable errors are
  fatal. Correctable counts > 1000/day on HBM is the canary for failing GPU.
- **`Xid` errors in dmesg related to this GPU** — see `47_dmesg_pcie.txt`.

### `61_nvsmi_topo.txt`
GPU↔GPU connectivity matrix + CPU + NUMA affinity. On H200 8× expect:
- All pairs `NV18` (18 NVLink connections each, 4th-gen NVLink mesh)
- Two NUMA columns showing `0` for GPU0-3 and `1` for GPU4-7 (correct
  socket affinity). All `0` = NUMA flattened (virt) or BIOS issue.

### `62_nvsmi_nvlink.txt`
Per-link status. Each H200 has 18 links @ 25 GB/s. All should show "Active".
Inactive links = hardware fault on baseboard.

### `63_nvsmi_clocks.txt`
Power, clocks, performance state, supported clock list. `P0` = max perf
state. If `P2` or `P8` under steady load = power-cap/throttle.

### `66_nvsmi_dmon_5s.txt`
5-second device-monitor sample. Columns:
- `pwr` (W), `gtemp` (°C), `mtemp`, `sm` (%), `mem` (%), `enc`, `dec`, `mclk`,
  `pclk`, `pviol` (power viol since last reset), `tviol` (thermal viol).

### `67_dcgmi_diag.txt`
DCGM level-1 diagnostic. Should show "Pass" for everything. Run
`dcgmi diag --run 3 --fail-early` for deeper checks (see
`bringup-recipe.md`).

---

## 70-79 — Network

### `70_ip_link.txt`, `71_ip_addr.txt`
Interface status, RX/TX counters. Look for `dropped` or `errors` non-zero.

### `72_ethtool.txt`
Per-interface driver, firmware, ring sizes. Per `recommended-tunings.md` §L:
- Ring sizes typically 4096 RX / 4096 TX for max throughput.
- Driver should be `mlx5_core` for ConnectX, `nvidia` for BlueField.

### `73_ibstat.txt`, `74_ibv_devinfo.txt`
IB / RDMA per-HCA. Each port:
- `State: Active` ✓
- `Physical state: LinkUp` ✓
- `Rate: 200 Gb/sec (4X HDR)` or `400 Gb/sec (4X NDR)` for IB; check vs
  switch capability.
- `Link layer: InfiniBand` or `Ethernet` (RoCE)

### `75_rdma_link.txt`
Newer RDMA tooling — same info as ibstat in modern format.

---

## 80-89 — Storage

### `80_lsblk.txt`, `81_findmnt.txt`
Block devices + mounts. Confirm weights cache mount has `noatime`.

### `82_nvme_list.txt`, `83_nvme_id.txt`
NVMe device list + per-controller info. Look for:
- Firmware revision
- Namespace 1 capacity
- LBA Format size (4096 ✓ for modern NVMe)

### `84_smartctl.txt`
SMART health + recent error counters. Look for:
- `Percentage Used` near 100 = wearing out
- `Media and Data Integrity Errors` non-zero = pending failure
- `Temperature` > 70 °C sustained = cooling issue

### `85_io_scheduler.txt`
Per-device scheduler. `none` ✓ for NVMe (per §H.1). `mq-deadline` /
`bfq` = override needed.

---

## 90-99 — Container runtime

### `90_containerd_ver.txt`
2.0+ recommended for CDI default + NRI GA.

### `93_cdi_listing.txt`
`/var/run/cdi/` and `/etc/cdi/`. NVIDIA CDI spec from
`nvidia-ctk cdi generate`. Empty = CDI not configured (per §I.1).

### `94_cgroup_version.txt`
`cgroup2fs` ✓. `tmpfs` = cgroup v1, switch via kernel cmdline
`systemd.unified_cgroup_hierarchy=1`.

### `95_kubelet_config.txt`, `96_rke2_config.txt`
Kubelet + RKE2 server config. Confirm CPU/topology/memory managers per §I.3.

### `97_docker_info.txt`
Docker version + storage driver if docker (not containerd) is what's running.

---

## Comparing two snapshots

`diff -ruN snapA/ snapB/` works for ~80% of probes but is noisy in places.
The lists below show which probes always change run-to-run (filter them
out) vs which are signal (any diff is a finding).

Probes where line-by-line diff is misleading (skip or filter):
- `00_meta.txt` — timestamps always differ
- `27_turbostat_5s.txt` — sampled live values differ run-to-run
- `30_numactl_H.txt` `node free` columns — per-run dynamic
- `66_nvsmi_dmon_5s.txt` — sampled live values
- `46_dmesg_first.txt` / `47_dmesg_pcie.txt` — boot-time entries vs not
- `49_irq_affinity.txt` `total=N` columns — counters

Probes where any diff is a finding:
- `42_cmdline.txt` — kernel boot args
- `43_sysctl_all.txt` — sysctl values
- `13_dmi_id.txt` — chassis identity
- `45_security_limits.txt` — ulimits
- `60_nvsmi_full.txt` — driver/persistence/ECC/MIG/clocks/throttle reasons
