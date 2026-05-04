# Bring-up recipe — pointer-summary

The canonical sequence for taking a GPU host from "wires plugged in" to
"production-ready," distilled from Together.ai's practitioner's guide and
Modal's keep-20K-GPUs-healthy procedures (both 2025).

This file is a navigation map. Run the audit (`scripts/collect.sh`) first;
then the relevant section of this recipe directs you to the exact tool +
command for each step.

---

## Phase 0 — Baseline OS (one-time, by the OEM or your provisioning automation)

- NVIDIA drivers (open module on Hopper+, proprietary on older). Driver
  series 550+ is the 2025/2026 baseline; 555+ for Blackwell.
- OFED / DOCA drivers (Mellanox/NVIDIA Networking). Check version against
  ConnectX firmware. `mlnx_tune` should be on PATH.
- CUDA toolkit (12.4+ for Hopper, 12.8+ for Blackwell, 13.0+ for production
  vLLM 0.20+).
- NCCL (2.20+ for `NCCL_NVLS_ENABLE=1` default on, NVLink-Sharp).
- HPCX stack if doing multi-node IB.
- SLURM or Kubernetes cluster registration.
- Time sync: chronyd or systemd-timesyncd. Drift > 10ms across nodes
  breaks NCCL and GPUDirect Storage.

---

## Phase 1 — Pre-tune audit

```bash
# Run the collector with snapshot only (read-only, safe):
sudo ./scripts/collect.sh
```

Read the snapshot's `INDEX.md` and check the high-impact probes:

| Probe | Acceptable | Action if not |
|---|---|---|
| `22_cpu_freq_governor.txt` | `performance` × all CPUs | `recommended-tunings.md` §A.1 |
| `24_cstates.txt` | C-states deeper than C1 disabled (or PM-QoS = 1) | §A.3 |
| `34_vm_tunables.txt` | `numa_balancing=0`, `swappiness=1` | §C.2, §C.3 |
| `42_cmdline.txt` | `iommu=pt`, hugepages, `mitigations=off` (if policy allows) | §B.1 |
| `44_ulimit_a.txt` | `memlock=unlimited` | §D.1 |
| `60_nvsmi_full.txt` | Persistence Enabled, ECC Enabled (prod), TGP power limit | §F |
| `93_cdi_listing.txt` | CDI specs present | §I.1 |

If `tuned` + `nvidia-tuned-profiles` is available, **apply the profile FIRST**
— it covers most of the above in one step:

```bash
tuned-adm profile dgx-h200-performance        # or your platform variant
tuned-adm verify                              # confirm the profile took
```

Then re-audit. The remaining gaps are chassis-specific or workload-specific.

---

## Phase 2 — Validate hardware basics (~5 min)

### 2.1 Count + sanity

```bash
# GPU count matches box spec (catches "fell off the bus"):
nvidia-smi -L | wc -l       # should equal expected GPU count

# All GPUs reach driver-side health-check:
nvidia-smi --query-gpu=index,name,uuid,persistence_mode,ecc.mode.current,power.management,power.draw,temperature.gpu --format=csv
```

### 2.2 DCGM diagnostic — the standard health gate

```bash
# Level 1: ~30 sec, basic sanity (PCIe, GPU memory, basic compute)
dcgmi diag --run 1

# Level 2: ~5 min, runs CUBLAS/CUFFT/Targeted stress (Modal does this weekly)
dcgmi diag --run 2 --fail-early

# Level 3: ~30 min, deep stress (Together.ai does this on bring-up)
dcgmi diag --run 3 --fail-early

# Level 4: ~1 hour. NEVER at boot. Quarterly maintenance windows only.
# dcgmi diag --run 4
```

In a container:

```bash
apptainer pull docker://nvidia/dcgm:3.3.6-1-ubuntu22.04
apptainer exec --nv dcgm_3.3.6-1-ubuntu22.04.sif /usr/bin/dcgmi diag --run 3 --fail-early
```

---

## Phase 3 — Bandwidth ground truth

### 3.1 Pinned-host ↔ GPU memcpy (this skill's bench)

```bash
# Run inside the container or venv that has torch:
sudo ./scripts/collect.sh --bench
```

Compare the resulting `bench_pinned_memcpy.csv` with `session-findings.md`:
- H100 80GB SXM5: ~50 GB/s H2D ceiling
- H200 141GB SXM5: ~57 GB/s H2D ceiling (measured Verda 2026)
- B200 SXM6: ~85 GB/s H2D ceiling (PCIe Gen5 x16 ~95% efficiency)
- L40S / RTX PRO 6000: ~25-28 GB/s H2D ceiling (PCIe Gen4 x16)

If you're at <80% of expected → see `recommended-tunings.md` and confirm
PCIe link is trained at full speed/width (`nvidia-smi -q -d POWER` and
`51_lspci_full.txt` LnkSta).

### 3.2 NVIDIA `nvbandwidth`

The official tool. Measures every memcpy pattern (CE / SM, host↔device,
device↔device, multinode).

```bash
git clone https://github.com/NVIDIA/nvbandwidth
cd nvbandwidth && cmake -B build && cmake --build build -j
./build/nvbandwidth                         # all tests
./build/nvbandwidth -t host_to_device_memcpy_ce
./build/nvbandwidth -t device_to_device_memcpy_write_ce
./build/nvbandwidth -t multinode_device_to_device_memcpy_write_ce
```

Expected GPU↔GPU on H100 fully-NVLink-connected: **~389 GB/s** per pair
(Together.ai's measured number).

### 3.3 NCCL all-reduce single-node

```bash
git clone https://github.com/NVIDIA/nccl-tests
cd nccl-tests && make MPI=0 -j

./build/all_reduce_perf -b 64M -e 8G -f 2 -g 8
# -g 8 = 8 GPUs, -b/-e/-f = size sweep min/max/factor
```

Expected on H200 8× single-node: ~480 GB/s busbw at large sizes (per
Cisco/NVIDIA MLPerf submissions).

### 3.4 NCCL all-reduce multi-node (IB)

```bash
mpirun --allow-run-as-root -np 16 -H node1:8,node2:8 \
    --mca btl_tcp_if_exclude lo,docker0 \
    -x NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3 \
    -x NCCL_DEBUG=INFO \
    ./build/all_reduce_perf -b 64M -e 8G -f 2 -g 1
```

Target **92% of theoretical** (per Together.ai): ~370 GB/s on 400 Gbps fabric.

### 3.5 IB raw (point-to-point)

```bash
# Server side:
ib_write_bw -d mlx5_0
# Client side:
ib_write_bw -d mlx5_0 <server-ip>
```

Expected near line rate (e.g., 47-48 GB/s on 400Gbps NDR per direction).

### 3.6 Storage (`fio`)

```bash
fio --name=randread --rw=randread --bs=128k --numjobs=8 --iodepth=32 \
    --runtime=30 --time_based --filename=/var/lib/vllm-cache/.test \
    --direct=1 --ioengine=libaio
```

Target depends on storage tier. NVMe SSD: 5+ GB/s. NFS/CIFS: depends on net.

---

## Phase 4 — Stability under load

### 4.1 GPU-Burn / GPU-Fryer

```bash
git clone https://github.com/wilicc/gpu-burn
cd gpu-burn && make
./gpu_burn 60                   # 60-second run, looks for memory errors
./gpu_burn -d 600               # 10-min for thorough thermal soak
```

Or via container:
```bash
apptainer pull docker://oguzpastirmaci/gpu-burn:latest
apptainer exec --nv gpu-burn_latest.sif /app/gpu_burn 60
```

Watch for "GPU N: ECC errors!" in output. Memory errors under load are
fatal — return the GPU.

Hugging Face's `gpu-fryer` is an alternative — single-binary, similar idea.

### 4.2 Modal's thermal threshold table

| Temp | Action |
|---|---|
| < 70 °C | Fine |
| 70-80 °C | Within spec |
| 80-88 °C | Watch — could be ambient or fan failure |
| 88-90 °C | **Flag for investigation** |
| > 90 °C | Broken — replace |

H100/H200 max operating temp is 88 °C; Blackwell B100/B200 is 90 °C; B300 air
is 95 °C, B300 DLC ~75 °C max.

---

## Phase 5 — Reference workload

### 5.1 Together.ai's recommendation: Llama-3 8B FSDP across 16 nodes

A real training run, ~30 min, exercises all the layers: CUDA, NCCL, IB,
storage, kernel scheduling. Watch for:
- Throughput (tokens/second per GPU)
- Model FLOPS utilization (target 50%+ for H100, 40%+ for H200 due to BW headroom)
- GPU usage % (should be >85%)
- Network latency (NCCL p99)

### 5.2 vLLM equivalent for inference hosts

```bash
docker run -d --gpus all --ipc=host --name vllm-test \
    -e LMCACHE_LOCAL_CPU=True \
    -e LMCACHE_MAX_LOCAL_CPU_SIZE=100 \
    vllm/vllm-openai:latest \
    --model meta-llama/Llama-3-70B-Instruct \
    --tensor-parallel-size 4 \
    --max-model-len 8192

# After startup:
docker exec vllm-test vllm bench serve \
    --backend openai --base-url http://localhost:8000 \
    --model meta-llama/Llama-3-70B-Instruct \
    --dataset-name prefix_repetition --num-prompts 200 --max-concurrency 16
```

Compare TTFT P99, output tok/s, and Prometheus `vllm:cache_hit_rate` to
known-good baselines.

---

## Phase 6 — Drift detection (continuous)

### 6.1 Continuous low-impact health-check (Modal model)

Every 30s on each node:

```bash
# Wrap in a systemd timer or DaemonSet:
nvidia-smi --query-gpu=index,temperature.gpu,power.draw,clocks_throttle_reasons.active,ecc.errors.uncorrected.aggregate.total --format=csv
dmesg --since "1 minute ago" | grep -iE "xid|nvrm|aer|throttl"
```

Alert on:
- Temp > 88 °C
- Any uncorrectable ECC delta
- Any new Xid in dmesg (Xid 79 = GPU fell off bus, Xid 31 = MMU fault, etc.)
- Sync-boost violations
- Hardware throttle reasons

### 6.2 Periodic deep check (weekly)

```bash
# Tier 1: rerun the audit, diff against last week's
sudo ./scripts/collect.sh
# diff -ruN gpu-host-tuning-<host>-<prev-UTC>/ gpu-host-tuning-<host>-<new-UTC>/

# Tier 2: dcgmi level-2
dcgmi diag --run 2

# Tier 3: NCCL all-reduce
./build/all_reduce_perf -b 1G -e 8G -f 2 -g 8
```

### 6.3 Per-Xid-code action

NVIDIA documents Xid codes — common ones:
- **Xid 13**: graphics engine exception. Often transient under heavy compute. > 5/day → investigate.
- **Xid 31**: MMU fault. App bug or hardware. > 2/day → drain node.
- **Xid 43**: stopped processing. App-level OOM or driver-level issue.
- **Xid 45**: preemption. Normal during checkpointing.
- **Xid 79**: GPU fell off bus. **Drain immediately** — usually PCIe link or thermal.
- **Xid 94**: Contained ECC error. Memory page retired automatically; > 50 retired pages = replace.

---

## Phase 7 — Tear-up checklist (single-page, no commentary)

```
[ ] Drivers + CUDA + NCCL + OFED installed; `nvidia-smi` shows expected GPU count
[ ] tuned-adm profile dgx-<platform>-performance applied; tuned-adm verify clean
[ ] /proc/cmdline has: iommu=pt, default_hugepagesz=1G, mitigations=off (if policy)
[ ] Persistence mode ON (nvidia-persistenced.service enabled)
[ ] ECC enabled (nvidia-smi -q -d ECC)
[ ] Power limit at TGP (nvidia-smi -pl <max>)
[ ] memlock = unlimited (limits.d + container ulimits)
[ ] swap off (`swapoff -a` + fstab clean)
[ ] kernel.numa_balancing = 0
[ ] vm.swappiness = 1
[ ] CDI generated (nvidia-ctk cdi generate)
[ ] containerd runtime configured for CDI
[ ] kubelet CPU/topology/memory managers static (if K8s)
[ ] dcgmi diag --run 2 passes
[ ] gpu-burn 60s passes (no ECC errors)
[ ] nvbandwidth shows ≥80% of expected H2D / D2D
[ ] nccl-tests all_reduce_perf within 10% of expected single-node bw
[ ] (multinode) IB ports up, ib_write_bw at line rate
[ ] Reference workload completes (Llama-3 8B / 70B for ~10 min)
[ ] Audit re-run, snapshot saved as the post-tune baseline
```

The post-tune baseline becomes the diff target for monthly drift checks.
