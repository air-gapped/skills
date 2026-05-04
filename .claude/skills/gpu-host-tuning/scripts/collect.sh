#!/usr/bin/env bash
# gpu-host-tuning collector — read-only audit of an inference host.
# No installs, no privileged writes, safe on a production box.
#
# USAGE
#   ./collect.sh                            # snapshot only, ~60s
#   ./collect.sh --bench                    # + pinned-memcpy harness, ~5 min (needs torch)
#   ./collect.sh --bench --mlc              # + Intel MLC bandwidth/latency matrix
#   ./collect.sh --out <dir>                # explicit output dir
#   ./collect.sh --no-prompt                # skip the interactive output-dir prompt
#                                           #   (use $PWD or $HOST_AUDIT_DIR or last choice)
#
# OUTPUT
#   <chosen-dir>/gpu-host-tuning-<host>-<UTC>/    one file per probe + ERRORS.log + INDEX.md
#   <chosen-dir>/gpu-host-tuning-<host>-<UTC>.tar.zst
#
# Last-used parent dir is persisted to ~/.config/gpu-host-tuning/last_outdir
#
# FILE-NAME CATEGORIES (numeric prefix = section)
#   00-09  meta             (collector version, timestamps, host id)
#   10-19  system + firmware (dmidecode, lshw, /sys/class/dmi)
#   20-29  CPU + power + C-states + thermal
#   30-39  memory + NUMA + THP + numa_balancing
#   40-49  kernel, boot cmdline, sysctl, ulimits, vulnerabilities, dmesg, IRQ aff, env vars
#   50-59  PCIe topology, link width/speed, ASPM, AER
#   60-69  GPU (nvidia-smi -q, topo, nvlink, clocks, ECC, throttle reasons)
#   70-79  network (NICs, IB, RDMA, ethtool)
#   80-89  storage (block devices, NVMe, mounts, schedulers)
#   90-99  container runtime + kubelet (containerd, runc, CDI, RKE2)
#   bench_* micro-benchmarks (CSV + log)

set -u
shopt -s nullglob

DO_BENCH=0
DO_MLC=0
NO_PROMPT=0
EXPLICIT_OUT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bench) DO_BENCH=1; shift ;;
        --mlc)   DO_MLC=1; shift ;;
        --no-prompt) NO_PROMPT=1; shift ;;
        --out) EXPLICIT_OUT="$2"; shift 2 ;;
        --out=*) EXPLICIT_OUT="${1#*=}"; shift ;;
        -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

HOST="$(hostname -s 2>/dev/null || echo unknown)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
HERE="$(cd "$(dirname "$0")" && pwd)"
SNAP_NAME="gpu-host-tuning-${HOST}-${TS}"

# --- choose the parent directory the snapshot dir will live in ---
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/gpu-host-tuning"
LAST_FILE="$CFG_DIR/last_outdir"
DEFAULT_PARENT=""
if [[ -n "$EXPLICIT_OUT" ]]; then
    DEFAULT_PARENT="$EXPLICIT_OUT"
elif [[ -n "${HOST_AUDIT_DIR:-}" ]]; then
    DEFAULT_PARENT="$HOST_AUDIT_DIR"
elif [[ -r "$LAST_FILE" ]]; then
    DEFAULT_PARENT="$(cat "$LAST_FILE")"
else
    DEFAULT_PARENT="$PWD"
fi

# Interactive prompt unless --no-prompt or non-tty
if [[ $NO_PROMPT -eq 0 && -z "$EXPLICIT_OUT" && -t 0 && -t 1 ]]; then
    printf 'Output parent directory [%s]: ' "$DEFAULT_PARENT" >&2
    read -r answer
    [[ -n "$answer" ]] && DEFAULT_PARENT="$answer"
fi

mkdir -p "$CFG_DIR" 2>/dev/null && echo "$DEFAULT_PARENT" >"$LAST_FILE" 2>/dev/null

OUT="$DEFAULT_PARENT/$SNAP_NAME"
ERR="$OUT/ERRORS.log"
INDEX="$OUT/INDEX.md"
mkdir -p "$OUT"
: >"$ERR"
echo "writing snapshot to $OUT" >&2

# ------ helpers ------
need_root_warn=0
maybe_sudo() {
    if [[ $EUID -eq 0 ]]; then "$@"
    elif command -v sudo >/dev/null && sudo -n true 2>/dev/null; then sudo "$@"
    else need_root_warn=1; "$@"
    fi
}
cap() {  # cap <out_relpath> -- <cmd...>
    local rel="$1"; shift
    [[ "$1" == "--" ]] && shift
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "[$rel] SKIPPED (missing tool: $1)" >>"$ERR"
        return
    fi
    "$@" >"$OUT/$rel" 2>>"$ERR" || echo "[$rel] FAILED rc=$?: $*" >>"$ERR"
}
cap_root() {  # cap_root <out_relpath> -- <cmd...>
    local rel="$1"; shift
    [[ "$1" == "--" ]] && shift
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "[$rel] SKIPPED (missing tool: $1)" >>"$ERR"; return
    fi
    maybe_sudo "$@" >"$OUT/$rel" 2>>"$ERR" || echo "[$rel] FAILED rc=$?: $*" >>"$ERR"
}
read_glob() {  # read_glob <out_relpath> <pattern> [head_lines]
    local rel="$1" pat="$2" head="${3:-0}"
    {
        # shellcheck disable=SC2086  # pattern intentionally unquoted for glob expansion
        for f in $pat; do
            [[ -r "$f" ]] || continue
            printf -- '--- %s\n' "$f"
            if [[ "$head" -gt 0 ]]; then head -c "$head" "$f"; echo
            else cat "$f"; fi
        done
    } >"$OUT/$rel" 2>>"$ERR"
}

# ============================================================
# 00 — meta
# ============================================================
{
    echo "collector_version=1"
    echo "collected_at_utc=$TS"
    echo "host=$HOST"
    echo "uname=$(uname -a)"
    echo "id=$(id)"
    echo "args=$*"
    echo "do_bench=$DO_BENCH"
    echo "do_mlc=$DO_MLC"
} >"$OUT/00_meta.txt"

# ============================================================
# 10 — system identity / firmware (DMI / SMBIOS, lshw)
# ============================================================
# dmidecode -t accepts only one keyword at a time
{
    for kw in bios system baseboard chassis; do
        echo "=== $kw ==="
        maybe_sudo dmidecode -t "$kw" 2>/dev/null
    done
} >"$OUT/10_dmidecode_system.txt" 2>>"$ERR"
cap_root 11_dmidecode_processor.txt -- dmidecode -t processor
cap_root 12_dmidecode_memory.txt    -- dmidecode -t memory
# Walk /sys/class/dmi/id/ but skip directories (subsystem/, power/)
{
    for f in /sys/class/dmi/id/*; do
        [[ -f "$f" && -r "$f" ]] || continue
        printf -- '--- %s\n' "$f"
        head -c 4096 "$f" 2>/dev/null; echo
    done
} >"$OUT/13_dmi_id.txt" 2>>"$ERR"
cap 14_lshw_short.txt               -- lshw -short
cap 15_lscpu.txt                    -- lscpu
cap 16_hostnamectl.txt              -- hostnamectl

# ============================================================
# 20 — CPU + POWER + C-STATES   (the one we care about)
# ============================================================
# /proc/cpuinfo (full first-CPU stanza for flags + microcode + family/model)
# shellcheck disable=SC2129  # different stdout targets per redirect
{ awk '/^$/{exit} {print}' /proc/cpuinfo; } >"$OUT/20_cpuinfo_first.txt" 2>>"$ERR"
{ grep -c '^processor' /proc/cpuinfo; } >"$OUT/21_cpuinfo_count.txt" 2>>"$ERR"

# --- governor / frequency (one line per distinct value, with count) ---
{
    if [[ -z "$(echo /sys/devices/system/cpu/cpu0/cpufreq/*)" ]]; then
        echo "# WARNING: /sys/devices/system/cpu/cpu*/cpufreq/ is empty — cpufreq sysfs not exposed."
        echo "# Common cause: virtualized guest where the hypervisor hides power-state controls."
        echo "# In that case CPU power management is the host's responsibility, not ours."
        echo
    fi
    echo "# scaling_driver:"
    cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_driver 2>/dev/null | sort | uniq -c
    echo
    echo "# scaling_governor:"
    cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c
    echo
    echo "# energy_performance_preference (intel_pstate EPP):"
    cat /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference 2>/dev/null | sort | uniq -c
    echo
    echo "# energy_performance_available_preferences (per-CPU):"
    cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_available_preferences 2>/dev/null
    echo
    echo "# scaling_min_freq / scaling_max_freq / cpuinfo_max_freq (kHz, distinct values):"
    cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq 2>/dev/null | sort -u | sed 's/^/  min /'
    cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq 2>/dev/null | sort -u | sed 's/^/  max /'
    cat /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq 2>/dev/null | sort -u | sed 's/^/  hwmax /'
} >"$OUT/22_cpu_freq_governor.txt" 2>>"$ERR"

# --- pstate global state — Intel (intel_pstate) AND AMD (amd_pstate) ---
{
    intel_dir=/sys/devices/system/cpu/intel_pstate
    amd_dir=/sys/devices/system/cpu/amd_pstate
    if [[ -d "$intel_dir" ]]; then
        echo "# intel_pstate:"
        for f in $intel_dir/{status,no_turbo,min_perf_pct,max_perf_pct,hwp_dynamic_boost,turbo_pct,num_pstates}; do
            [[ -r "$f" ]] || continue
            printf '  %s = ' "$f"; cat "$f"
        done
    else
        echo "# intel_pstate: not present"
    fi
    echo
    if [[ -d "$amd_dir" ]]; then
        echo "# amd_pstate:"
        for f in $amd_dir/{status,prefcore}; do
            [[ -r "$f" ]] || continue
            printf '  %s = ' "$f"; cat "$f"
        done
        # Per-CPU EPP for amd-pstate-epp driver
        echo "  # amd_pstate EPP (energy_performance_preference) distribution:"
        cat /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference 2>/dev/null \
            | sort | uniq -c | sed 's/^/    /'
    else
        echo "# amd_pstate: not present"
    fi
    echo
    echo "# acpi-cpufreq boost (legacy; absent if pstate driver in use):"
    [[ -r /sys/devices/system/cpu/cpufreq/boost ]] && cat /sys/devices/system/cpu/cpufreq/boost \
        || echo "  not present"
} >"$OUT/23_pstate.txt" 2>>"$ERR"

# --- C-state inventory (per state, NOT per CPU — they're all identical) ---
{
    if [[ ! -d /sys/devices/system/cpu/cpu0/cpuidle/state0 ]]; then
        echo "# WARNING: /sys/devices/system/cpu/cpu0/cpuidle/state* missing — cpuidle"
        echo "# states not exposed. Common in virtualized guests where the hypervisor"
        echo "# manages host C-states. The kernel-module knobs below describe the GUEST"
        echo "# kernel limits but do not constrain the underlying host."
        echo
    fi
    echo "# Per-state details (from cpu0):"
    for s in /sys/devices/system/cpu/cpu0/cpuidle/state*; do
        [[ -d "$s" ]] || continue
        printf '%-8s name=%s  desc=%s  latency=%sus  residency=%sus  disable=%s\n' \
            "${s##*/}" \
            "$(cat "$s/name" 2>/dev/null)" \
            "$(cat "$s/desc" 2>/dev/null)" \
            "$(cat "$s/latency" 2>/dev/null)" \
            "$(cat "$s/residency" 2>/dev/null)" \
            "$(cat "$s/disable" 2>/dev/null)"
    done
    echo
    echo "# Disabled-state distribution across ALL cpus (per state):"
    for s in /sys/devices/system/cpu/cpu0/cpuidle/state*; do
        n="${s##*/}"
        echo -n "  $n "
        cat /sys/devices/system/cpu/cpu*/cpuidle/"$n"/disable 2>/dev/null | sort | uniq -c | tr '\n' ' '
        echo
    done
    echo
    echo "# Kernel-module knobs:"
    for f in /sys/module/intel_idle/parameters/* /sys/module/processor/parameters/* /sys/module/cpuidle/parameters/*; do
        [[ -r "$f" ]] || continue
        printf '%s = ' "$f"; cat "$f"
    done
    echo
    echo "# Per-CPU PM-QoS resume latency (us, distinct values):"
    cat /sys/devices/system/cpu/cpu*/power/pm_qos_resume_latency_us 2>/dev/null | sort | uniq -c
    echo
    echo "# Cumulative per-state usage (cpu0) and total time (us) — fallback for"
    echo "# when turbostat can't read MSRs. Useful as a residency proxy."
    for s in /sys/devices/system/cpu/cpu0/cpuidle/state*; do
        [[ -d "$s" ]] || continue
        printf '  %-8s name=%s  usage=%s  time=%sus\n' \
            "${s##*/}" \
            "$(cat "$s/name" 2>/dev/null)" \
            "$(cat "$s/usage" 2>/dev/null)" \
            "$(cat "$s/time" 2>/dev/null)"
    done
} >"$OUT/24_cstates.txt" 2>>"$ERR"

# --- cpupower outputs (works without root for read; nicer formatting) ---
cap 25_cpupower_freq.txt -- cpupower frequency-info
cap 26_cpupower_idle.txt -- cpupower idle-info

# --- turbostat: live snapshot of busy% + C-state residency + pkg power.
#     Note: turbostat writes its DATA to stderr by default, so we 2>&1 it
#     into the output file. If it fails (e.g. MSR I/O error in a guest),
#     the failure message lands in the same file, making it self-diagnosing.
if command -v turbostat >/dev/null 2>&1; then
    maybe_sudo turbostat --quiet --interval 1 --num_iterations 5 \
        sleep 5 >"$OUT/27_turbostat_5s.txt" 2>&1 \
        || echo "[27_turbostat_5s.txt] turbostat exit non-zero — see file for details" >>"$ERR"
else
    echo "[27_turbostat_5s.txt] SKIPPED (turbostat not installed; install kernel-tools or linux-tools-common)" >>"$ERR"
fi

# --- microcode + Spectre/Meltdown mitigation cost ---
read_glob 28_vulnerabilities.txt "/sys/devices/system/cpu/vulnerabilities/*"
cap 29_microcode_dmesg.txt -- bash -c 'dmesg 2>/dev/null | grep -iE "microcode|smpboot|tsc:|cpu0:" | head -200'

# --- thermal zones (CPU + chassis) — catches throttle origins beyond the GPU ---
{
    for z in /sys/class/thermal/thermal_zone*; do
        [[ -d "$z" ]] || continue
        printf '%s  type=%s  temp=%s mC  policy=%s\n' \
            "${z##*/}" \
            "$(cat "$z/type" 2>/dev/null)" \
            "$(cat "$z/temp" 2>/dev/null)" \
            "$(cat "$z/policy" 2>/dev/null)"
    done
} >"$OUT/2A_thermal.txt" 2>>"$ERR"

# ============================================================
# 30 — memory + NUMA
# ============================================================
cap 30_numactl_H.txt    -- numactl --hardware
cap 31_meminfo.txt      -- cat /proc/meminfo
cap 32_zoneinfo.txt     -- bash -c 'head -200 /proc/zoneinfo'
read_glob 33_thp.txt    "/sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag /sys/kernel/mm/transparent_hugepage/khugepaged/defrag"
{
    echo "# /proc/sys/kernel/numa_balancing = $(cat /proc/sys/kernel/numa_balancing 2>/dev/null)"
    echo "# /proc/sys/vm/swappiness         = $(cat /proc/sys/vm/swappiness 2>/dev/null)"
    echo "# /proc/sys/vm/zone_reclaim_mode  = $(cat /proc/sys/vm/zone_reclaim_mode 2>/dev/null)"
    echo "# /proc/sys/vm/overcommit_memory  = $(cat /proc/sys/vm/overcommit_memory 2>/dev/null)"
    echo "# /proc/sys/vm/max_map_count      = $(cat /proc/sys/vm/max_map_count 2>/dev/null)"
    echo "# /proc/sys/vm/nr_hugepages       = $(cat /proc/sys/vm/nr_hugepages 2>/dev/null)"
    echo "# /proc/sys/vm/nr_overcommit_hugepages = $(cat /proc/sys/vm/nr_overcommit_hugepages 2>/dev/null)"
    echo
    echo "# 1GB hugepages (if any):"
    for d in /sys/devices/system/node/node*/hugepages/hugepages-*; do
        [[ -d "$d" ]] && printf '%s nr=%s free=%s\n' "$d" \
            "$(cat "$d"/nr_hugepages 2>/dev/null)" \
            "$(cat "$d"/free_hugepages 2>/dev/null)"
    done
} >"$OUT/34_vm_tunables.txt" 2>>"$ERR"

# ============================================================
# 40 — kernel, boot cmdline, sysctl, ulimits
# ============================================================
cap 40_uname.txt        -- uname -a
cap 41_os_release.txt   -- cat /etc/os-release
cap 42_cmdline.txt      -- cat /proc/cmdline
# sysctl -a writes "permission denied" warnings for unprivileged keys to
# stderr — those are not real errors. Filter them out of ERR.
{
    sysctl -a 2> >(grep -v 'permission denied' >&2)
} >"$OUT/43_sysctl_all.txt" 2>>"$ERR"
cap 44_ulimit_a.txt     -- bash -c 'ulimit -a -S; echo "--- HARD ---"; ulimit -a -H'
read_glob 45_security_limits.txt "/etc/security/limits.conf /etc/security/limits.d/*"
cap 46_dmesg_first.txt  -- bash -c 'dmesg 2>/dev/null | head -200'
cap 47_dmesg_pcie.txt   -- bash -c 'dmesg 2>/dev/null | grep -iE "pcie|pci |aer|iommu|nvidia|nvme" | head -300'
cap 48_loaded_modules.txt -- lsmod

# --- IRQ affinity summary (HPC tuning often pins NIC/NVMe IRQs off the inference cores) ---
{
    echo "# Top 30 IRQs by event count + their smp_affinity_list:"
    if [[ -r /proc/interrupts ]]; then
        awk 'NR==1 {print "IRQ\tTOTAL\tNAME"} NR>1 {
            sum=0; for (i=2;i<=NF-2;i++) sum+=$i;
            name=$NF; for (i=NF-1;i>NF-3;i--) name=$i" "name;
            irq=$1; sub(/:/,"",irq);
            if (irq ~ /^[0-9]+$/) print irq"\t"sum"\t"name
        }' /proc/interrupts | sort -k2 -n -r | head -30 | while read -r irq tot name; do
            aff=$(cat /proc/irq/"$irq"/smp_affinity_list 2>/dev/null)
            printf 'irq=%-4s  total=%-12s  affinity=%-20s  name=%s\n' "$irq" "$tot" "$aff" "$name"
        done
    fi
    echo
    echo "# default_smp_affinity = $(cat /proc/irq/default_smp_affinity 2>/dev/null)"
    echo "# irqbalance status:"
    systemctl is-active irqbalance 2>/dev/null
    systemctl status irqbalance 2>/dev/null | head -5
} >"$OUT/49_irq_affinity.txt" 2>>"$ERR"

# --- relevant environment variables (NCCL/CUDA/OMP/torch) — present iff a serving process is up ---
{
    echo "# Env vars in PID 1 / current process / any vllm process:"
    for src in /proc/1/environ /proc/self/environ; do
        [[ -r "$src" ]] || continue
        echo "=== $src ==="
        tr '\0' '\n' <"$src" 2>/dev/null \
            | grep -E '^(NCCL|UCX|CUDA|TORCH|OMP|MKL|HF_|VLLM|LMCACHE|PYTHON|HUGGING|LD_LIBRARY_PATH|PATH)' \
            | sort
    done
    for pid in $(pgrep -f vllm 2>/dev/null); do
        [[ -r /proc/$pid/environ ]] || continue
        echo "=== /proc/$pid/environ (vllm) ==="
        tr '\0' '\n' </proc/"$pid"/environ 2>/dev/null \
            | grep -E '^(NCCL|UCX|CUDA|TORCH|OMP|MKL|HF_|VLLM|LMCACHE)' \
            | sort
    done
} >"$OUT/4A_env_vars.txt" 2>>"$ERR"

# ============================================================
# 50 — PCIe
# ============================================================
cap 50_lspci_tree.txt    -- lspci -tv
cap_root 51_lspci_full.txt -- lspci -vvv -nn
cap 52_lspci_nvidia.txt  -- bash -c 'lspci -d 10de: -vvv -nn 2>/dev/null'
# shellcheck disable=SC2016  # vars expand inside the spawned bash, not in parent
cap 53_lspci_aer.txt     -- bash -c 'for d in /sys/bus/pci/devices/*; do for f in $d/aer_*; do [[ -r "$f" ]] && echo "=== ${f#/sys/bus/pci/devices/} ===" && cat "$f"; done; done'

# ============================================================
# 60 — GPU
# ============================================================
cap 60_nvsmi_full.txt    -- nvidia-smi -q
cap 61_nvsmi_topo.txt    -- nvidia-smi topo -m
cap 62_nvsmi_nvlink.txt  -- nvidia-smi nvlink --status
cap 63_nvsmi_clocks.txt  -- nvidia-smi -q -d POWER,CLOCK,PERFORMANCE,SUPPORTED_CLOCKS,TEMPERATURE
cap 64_nvsmi_pcie.txt    -- nvidia-smi -q -d MEMORY,UTILIZATION,ECC
cap 65_nvsmi_short.txt   -- nvidia-smi
cap 66_nvsmi_dmon_5s.txt -- bash -c 'nvidia-smi dmon -c 5 -s pucvmet 2>/dev/null'
cap 67_dcgmi_diag.txt    -- bash -c 'dcgmi diag -r 1 2>/dev/null || echo "dcgmi not available"'

# ============================================================
# 70 — network
# ============================================================
cap 70_ip_link.txt    -- ip -s link
cap 71_ip_addr.txt    -- ip -br addr
{
    for ifc in /sys/class/net/*; do
        n="${ifc##*/}"
        [[ "$n" == "lo" ]] && continue
        echo "=== $n ==="
        ethtool -i "$n" 2>/dev/null
        ethtool -g "$n" 2>/dev/null | head -20
        echo
    done
} >"$OUT/72_ethtool.txt" 2>>"$ERR"
cap 73_ibstat.txt      -- ibstat
cap 74_ibv_devinfo.txt -- ibv_devinfo -v
cap 75_rdma_link.txt   -- rdma link

# ============================================================
# 80 — storage
# ============================================================
cap 80_lsblk.txt       -- lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,UUID
cap 81_findmnt.txt     -- findmnt -t ext4,xfs,zfs,btrfs,nfs,nfs4,cifs,overlay
cap 82_nvme_list.txt   -- nvme list
# shellcheck disable=SC2016  # vars expand inside the spawned bash, not in parent
cap_root 83_nvme_id.txt -- bash -c 'for d in /dev/nvme?n1; do [[ -e "$d" ]] || continue; echo "=== $d ==="; nvme id-ctrl "$d" 2>/dev/null | head -50; done'
# shellcheck disable=SC2016
cap_root 84_smartctl.txt -- bash -c 'for d in /dev/nvme?n1 /dev/sd?; do [[ -e "$d" ]] || continue; echo "=== $d ==="; smartctl -i -A "$d" 2>/dev/null | head -40; done'
# shellcheck disable=SC2016
cap 85_io_scheduler.txt -- bash -c 'for q in /sys/block/*/queue/scheduler; do echo "$q = $(cat "$q" 2>/dev/null)"; done'

# ============================================================
# 90 — container runtime
# ============================================================
cap 90_containerd_ver.txt -- containerd --version
cap 91_runc_ver.txt       -- runc --version
cap 92_nvidia_ctk_ver.txt -- nvidia-ctk --version
cap 93_cdi_listing.txt    -- bash -c 'ls -la /var/run/cdi/ /etc/cdi/ 2>/dev/null || echo "no CDI dirs"; true'
cap 94_cgroup_version.txt -- bash -c 'stat -fc %T /sys/fs/cgroup/'
cap 95_kubelet_config.txt -- bash -c 'cat /var/lib/rancher/rke2/agent/kubelet.yaml 2>/dev/null || cat /var/lib/kubelet/config.yaml 2>/dev/null || echo "no kubelet config found"'
cap 96_rke2_config.txt    -- bash -c 'cat /etc/rancher/rke2/config.yaml 2>/dev/null || echo "no rke2 config"'
cap 97_docker_info.txt    -- docker info

# ============================================================
# bench — micro-benchmarks (only if --bench)
# ============================================================
if [[ $DO_BENCH -eq 1 ]]; then
    # nvbandwidth: pinned-host <-> GPU + GPU<->GPU
    if command -v nvbandwidth >/dev/null 2>&1; then
        cap bench_nvbandwidth_h2d.txt -- nvbandwidth -t host_to_device_memcpy_ce
        cap bench_nvbandwidth_d2h.txt -- nvbandwidth -t device_to_host_memcpy_ce
        cap bench_nvbandwidth_d2d.txt -- nvbandwidth -t device_to_device_memcpy_ce
        cap bench_nvbandwidth_all.txt -- nvbandwidth
    else
        echo "[bench_nvbandwidth] SKIPPED (nvbandwidth not on PATH; install: https://github.com/NVIDIA/nvbandwidth)" >>"$ERR"
    fi

    # custom pinned-memcpy harness — replicates LMCache offload path under
    # several NUMA bindings so we can see the local-vs-remote-vs-interleave
    # delta on this exact box. This is the LMCache CPU-tier ground truth.
    if [[ -r "$HERE/bench_pinned_memcpy.py" ]] && command -v python3 >/dev/null 2>&1; then
        if ! python3 -c 'import torch; assert torch.cuda.is_available()' 2>>"$ERR"; then
            echo "[bench_pinned_memcpy] SKIPPED (torch + CUDA not available in this python; run inside vllm container)" >>"$ERR"
        else
            log="$OUT/bench_pinned_memcpy.log"
            csv="$OUT/bench_pinned_memcpy.csv"
            : >"$log"
            nodes=$(numactl --hardware 2>/dev/null | awk '/^node [0-9]+ size:/{print $2}')
            if [[ -z "$nodes" ]] || ! command -v numactl >/dev/null 2>&1; then
                echo "=== no NUMA / numactl missing — single run ===" >>"$log"
                python3 "$HERE/bench_pinned_memcpy.py" --csv "$csv" \
                    --tag default --all-gpus >>"$log" 2>>"$ERR"
            else
                # one run per membind=N (membind+cpunodebind = local-style)
                for node in $nodes; do
                    echo "=== membind=$node cpunodebind=$node ===" >>"$log"
                    numactl --membind="$node" --cpunodebind="$node" \
                        python3 "$HERE/bench_pinned_memcpy.py" --csv "$csv" \
                        --tag "membind${node}" --all-gpus >>"$log" 2>>"$ERR" \
                        || echo "[bench_pinned_memcpy membind=$node] FAILED" >>"$ERR"
                done
                # one run with interleave=all (the de-facto LMCache today, when wrapped)
                echo "=== interleave=all ===" >>"$log"
                numactl --interleave=all \
                    python3 "$HERE/bench_pinned_memcpy.py" --csv "$csv" \
                    --tag interleave --all-gpus >>"$log" 2>>"$ERR" \
                    || echo "[bench_pinned_memcpy interleave] FAILED" >>"$ERR"
            fi
        fi
    else
        echo "[bench_pinned_memcpy] SKIPPED (harness not found at $HERE/bench_pinned_memcpy.py)" >>"$ERR"
    fi
fi

if [[ $DO_MLC -eq 1 ]]; then
    if command -v mlc >/dev/null 2>&1; then
        cap_root bench_mlc_bandwidth.txt -- mlc --bandwidth_matrix
        cap_root bench_mlc_latency.txt   -- mlc --latency_matrix
    else
        echo "[bench_mlc] SKIPPED (mlc not on PATH; download Intel MLC at https://www.intel.com/content/www/us/en/download/736633/intel-memory-latency-checker-intel-mlc.html)" >>"$ERR"
    fi
fi

# ============================================================
# Index + tarball
# ============================================================
{
    echo "# gpu-host-tuning snapshot — $SNAP_NAME"
    echo
    echo "Generated: $TS  host=$HOST  do_bench=$DO_BENCH  do_mlc=$DO_MLC"
    echo
    if [[ $need_root_warn -eq 1 ]]; then
        echo "**Note**: not root and no passwordless sudo — some probes (dmidecode,"
        echo "full lspci, turbostat, smartctl) ran without privileges and may be"
        echo "partial. See ERRORS.log. Re-run with sudo for full coverage."
        echo
    fi
    echo "## How to interpret"
    echo
    echo "See \`references/probe-interpretation.md\` in the gpu-host-tuning skill"
    echo "for what an OK vs surprising value looks like in each numbered file."
    echo "See \`references/recommended-tunings.md\` for the lever-by-lever fixes."
    echo
    echo "## Files"
    (cd "$OUT" && for f in *; do [[ "$f" == "INDEX.md" ]] && continue; echo "$f"; done | sort) | sed 's/^/  - /'
} >"$INDEX"

if command -v zstd >/dev/null 2>&1; then
    tar -C "$(dirname "$OUT")" -cf - "$(basename "$OUT")" | zstd -19 -T0 -q -o "${OUT}.tar.zst"
    echo "wrote ${OUT}.tar.zst ($(du -h "${OUT}.tar.zst" | cut -f1))"
else
    tar -C "$(dirname "$OUT")" -czf "${OUT}.tar.gz" "$(basename "$OUT")"
    echo "wrote ${OUT}.tar.gz ($(du -h "${OUT}.tar.gz" | cut -f1))"
fi

errcount=$(wc -l <"$ERR")
echo "snapshot dir : $OUT"
echo "errors logged: $errcount lines (see $ERR)"
