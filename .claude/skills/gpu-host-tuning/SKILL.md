---
name: gpu-host-tuning
description: Audit AND tune Linux/GPU inference hosts — read-only snapshot of CPU
  power state, C-states, NUMA topology, PCIe link state, GPU settings, kernel
  boot params, sysctl, ulimits, IRQ affinity, container runtime; optional
  pinned-host↔GPU memcpy bench (torch + numactl); plus per-lever cheat-sheets
  to flip settings (governor, EPP, cpuidle, persistence, ECC, hugepages,
  intel_iommu, NCCL env, tuned-adm profiles, BIOS guidance for Dell XE / SMC /
  HPE). Sits beneath any inference framework (vLLM, sglang, TensorRT-LLM) —
  about the host, not the framework. Surfaces configuration gaps that
  bottleneck LMCache CPU-tier throughput, KV offload, NCCL bandwidth,
  prefix-cache rebuild. Triggers on "tune the host", "audit this box",
  "snapshot inference host", "characterize this server", "what's missing on
  bare-metal", "host comparison", "PCIe ground truth", "pinned memcpy
  ceiling", "H2D bandwidth bench", "tuned-adm profile", "C-state mask",
  "governor performance", "BIOS tuning", "is the box tuned", "before/after
  retuning", "GPU host bring-up", "cluster bring-up", "find missing config".
---

# gpu-host-tuning

Host-side tuning + audit for Linux GPU inference servers. Sits *beneath* any
inference framework (vLLM, sglang, TensorRT-LLM, llama.cpp). Three modes:

1. **Audit** — read-only snapshot
2. **Bench** — ground-truth pinned-host↔GPU memcpy ceiling
3. **Tune** — apply individual levers from the cheat-sheet

This file is a pointer map. The actual logic lives in `scripts/` and the
authoritative references in `references/`.

## Quick start

```bash
cd ~/.claude/skills/gpu-host-tuning

# Audit (read-only, ~60s)
./scripts/collect.sh

# Audit + pinned-memcpy bench (needs torch + CUDA, ~5 min)
./scripts/collect.sh --bench
```

The script prompts for the output parent dir on first interactive run and
remembers the choice. Override via `--out <dir>` or `HOST_AUDIT_DIR=<dir>`.
Default snapshot dirname is `gpu-host-tuning-<host>-<UTC>`.

## What the snapshot captures

One file per probe, numbered by section. See
[`references/probe-interpretation.md`](references/probe-interpretation.md)
for the full file-by-file decoder.

| Section | What |
|---|---|
| `00-09` meta | collector version, run timestamp, args |
| `10-19` system + firmware | dmidecode (BIOS, CPU, memory DIMMs), lshw, /sys/class/dmi |
| `20-29` CPU + power + C-states | governor, EPP, intel_pstate / amd_pstate, cpuidle states + disable mask, turbostat 5s residency, microcode, vulnerabilities, thermal zones |
| `30-39` memory + NUMA | numactl -H, /proc/meminfo, THP, numa_balancing, vm tunables, hugepages |
| `40-49` kernel + limits | uname, /etc/os-release, /proc/cmdline, sysctl -a, ulimit, /sys/devices/system/cpu/vulnerabilities, dmesg, IRQ affinity, env vars in vllm processes |
| `50-59` PCIe | lspci tree + verbose, AER counters, link width/speed for every NVIDIA device |
| `60-69` GPU | nvidia-smi -q full, topo -m, nvlink --status, clocks/power/ECC, dmon 5s, dcgmi diag |
| `70-79` network | NICs, IB (ibstat / ibv_devinfo), ethtool ring sizes, RDMA links |
| `80-89` storage | lsblk, NVMe id-ctrl, smartctl, mount flags, io scheduler |
| `90-99` container runtime | containerd version, CDI specs, cgroup v2, kubelet config, RKE2 config |

## Three modes — what each maps to

| Mode | What | Reference |
|---|---|---|
| **Audit** | `./scripts/collect.sh` writes the snapshot directory | `references/probe-interpretation.md` decodes each numbered file |
| **Bench** | `./scripts/collect.sh --bench` adds the pinned-memcpy CSV | `references/session-findings.md` lists baselines per chassis |
| **Tune** | No script — apply individual levers from the cheat-sheet | `references/recommended-tunings.md` (lever-by-lever) and `references/tuned-profiles.md` (apply via `tuned-adm`) |

## When to use which reference

| You want to | Read |
|---|---|
| Apply NVIDIA's stock DGX tunings | [`references/tuned-profiles.md`](references/tuned-profiles.md) |
| Run a proper bring-up flow | [`references/bringup-recipe.md`](references/bringup-recipe.md) |
| Find the lever the audit flagged | [`references/recommended-tunings.md`](references/recommended-tunings.md) |
| Decode an audit output file | [`references/probe-interpretation.md`](references/probe-interpretation.md) |
| Tune a Dell XE9680 (H100/H200, SPR/EMR) | [`references/dell-xe9680.md`](references/dell-xe9680.md) |
| Tune a Dell XE9780 / XE9780L (B200/B300, Granite Rapids) | [`references/dell-xe9780.md`](references/dell-xe9780.md) |
| Understand why cpufreq/cpuidle is empty inside a cloud VM | [`references/virt-and-cloud-quirks.md`](references/virt-and-cloud-quirks.md) |
| See measured baselines from real boxes | [`references/session-findings.md`](references/session-findings.md) |

## Comparing two snapshots

Two snapshots on the same host (e.g., pre-tune and post-tune) can be
compared with `diff -ruN snap_pre/ snap_post/`. For a structured impact
ranking, use `references/probe-interpretation.md` to interpret deltas.

## Companion skills

- [`vllm-nvidia-hardware`](../vllm-nvidia-hardware/) — per-SKU specs (HBM, TDP, NVLink, PCIe gen)
- [`vllm-deployment`](../vllm-deployment/) — K8s manifest authoring, cache mounts, probes
- [`vllm-performance-tuning`](../vllm-performance-tuning/) — vLLM-side knobs (above this skill's layer)
