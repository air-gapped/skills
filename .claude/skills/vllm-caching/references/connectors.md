# Connector configuration recipes

Detailed recipes for each vLLM KV caching backend. Load when selecting or configuring a specific connector.

## Table of contents
- [Native CPU offload](#native-cpu-offload-single-node-simplest)
- [LMCache with DRAM + NVMe tiers](#lmcache-with-dram--nvme-tiers-single-node-production)
- [GDS (GPUDirect Storage) for NVMe direct-DMA](#gds-gpudirect-storage-for-nvme-direct-dma)
- [NixlConnector — disaggregated prefill](#nixlconnector-disaggregated-prefill)
- [MooncakeConnector — RDMA-backed disaggregated prefill](#mooncakeconnector-rdma-backed-disaggregated-prefill)
- [MultiConnector — compose backends](#multiconnector-compose-backends)

## Native CPU offload (single node, simplest)

Zero extra dependencies. Included since v0.11.1. Start here unless there is a concrete reason to add complexity.

```bash
vllm serve <model> \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90 \
  --kv-offloading-size 1600 \
  --kv-offloading-backend native \
  --max-model-len 200000 \
  --enable-prefix-caching
```

Under the hood: pinned host memory (`cudaHostRegister`-backed mmap), LRU eviction policy by default, ARC also available. Code paths live in `vllm/v1/kv_offload/` with `vllm/v1/kv_offload/cpu/policies/` for eviction strategies.

## LMCache with DRAM + NVMe tiers (single node, production)

Use when an NVMe tier is needed in addition to DRAM. Assumes v0.14.0+ image with LMCache bundled, or `pip install lmcache>=0.3.9` at container start.

```bash
docker run ... \
  -e LMCACHE_USE_EXPERIMENTAL=True \
  -e LMCACHE_CHUNK_SIZE=256 \
  -e LMCACHE_LOCAL_CPU=True \
  -e LMCACHE_MAX_LOCAL_CPU_SIZE=1600 \
  -e LMCACHE_LOCAL_DISK="file:///mnt/nvme0/lm,file:///mnt/nvme1/lm,file:///mnt/nvme2/lm,file:///mnt/nvme3/lm" \
  -e LMCACHE_MAX_LOCAL_DISK_SIZE=4000 \
  -e LMCACHE_LOCAL_DISK_PATH_SHARDING=by_gpu \
  vllm/vllm-openai:v0.19.0-cu130 \
    <model> \
    --tensor-parallel-size 8 \
    --gpu-memory-utilization 0.90 \
    --kv-offloading-size 1600 \
    --kv-offloading-backend lmcache \
    --max-model-len 200000 \
    --enable-prefix-caching
```

Key env vars:
- `LMCACHE_MAX_LOCAL_CPU_SIZE` and `LMCACHE_MAX_LOCAL_DISK_SIZE` are **GiB as floats** (e.g. `5.0`, `1600`)
- `LMCACHE_LOCAL_DISK` takes comma-separated paths in `file:///` URL form
- `LMCACHE_LOCAL_DISK_PATH_SHARDING=by_gpu` (default) shards one path per GPU device id. Match drive count to GPU count when possible; with fewer drives than GPUs, multiple GPUs will contend on a single drive.

Keep `LMCACHE_MAX_LOCAL_CPU_SIZE` and `--kv-offloading-size` consistent. LMCache env vars win on the backend side; inconsistency leads to scheduler miscounting available slots.

## GDS (GPUDirect Storage) for NVMe direct-DMA

Datacenter GPUs only (H100/H200/A100/L40+). Consumer GeForce silently falls back to CPU-staging compat mode — cuFile API works but without performance benefit. Skip GDS on non-datacenter hardware.

### Host prerequisites

`nvidia-gds` lives in NVIDIA's CUDA apt repo, not in Ubuntu main/universe. Add the cuda-keyring first:

```bash
. /etc/os-release && UB=${VERSION_ID//./}
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu${UB}/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb && sudo apt-get update
sudo apt-get install nvidia-gds  # or nvidia-gds-13-0 pinned to CUDA major.minor
```

The metapackage pulls in `libcufile0`, `gds-tools`, and `nvidia-fs`.

### Additional requirements

- **Open NVIDIA kernel modules.** Required from nvidia-fs 2.17.5+. On bare metal, install the `-open` driver variant. On Kubernetes, GPU Operator handles it:
  ```bash
  helm install ... nvidia/gpu-operator \
    --set gds.enabled=true \
    --set driver.kernelModuleType=open
  ```
  (NVIDIA renamed the Helm value — older `driver.useOpenKernelModules=true` is no longer current. Verified 2026-04-24 against `docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-operator-rdma.html`.)
- **Secure Boot DISABLED.** Check with `mokutil --sb-state`. Dell PowerEdge ships with Secure Boot on by default — toggle in BMC/UEFI.
- **cuFile-compatible filesystem.** Ext4 or xfs, no dm-crypt / LUKS / LVM in the DMA path. Hardware RAID also blocks it — plain block devices or JBOD only.
- **MLNX_OFED / DOCA-OFED is NOT needed** for local U.2 / E3.S NVMe. Only required for GDS-over-RDMA (remote NVMe).

### Enable in LMCache

```bash
-e LMCACHE_GDS_PATH="/mnt/nvme0/lmcache,/mnt/nvme1/lmcache,..."
-e LMCACHE_CUFILE_BUFFER_SIZE=<bytes>
```

### Verification

```bash
sudo modprobe nvidia-fs
/usr/local/cuda/gds/tools/gdscheck -p
```

`gdscheck -p` enumerates every NVMe and prints GDS compatibility plus reasons for any "Unsupported." Validates IOMMU, ACS, filesystem, and driver state.

## NixlConnector — disaggregated prefill

Separates prefill and decode into distinct vLLM instances; the connector handles async KV transfer. Tunes TTFT (prefill instance parallelism) and ITL (decode instance parallelism) independently. Does NOT improve throughput on its own — it shapes latency.

```bash
vllm serve <model> ... \
  --kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_both","kv_buffer_device":"cuda","kv_connector_extra_config":{"backends":["UCX","GDS"]}}'
```

- `kv_role`: `kv_producer` (prefill instance), `kv_consumer` (decode instance), or `kv_both` (symmetric)
- `backends`: `UCX` (default transport, works over Ethernet/IB/RoCE), `GDS` (direct storage). Combine as needed.
- Reference example: `tests/v1/kv_connector/nixl_integration/run_accuracy_test.sh`
- Model/feature compatibility: `docs/features/nixl_connector_compatibility.md`

Bundled in v0.14.0+ images via `nixl-cu12` / `nixl-cu13` (matched to the image's CUDA).

## MooncakeConnector — RDMA-backed disaggregated prefill

High-performance RDMA KV transfer between prefill and decode pods using `mooncake-transfer-engine`. Choose over NIXL when:

- A dedicated RDMA fabric is available (InfiniBand / RoCE v2)
- Predictable, ultra-low-latency KV handoff is required at scale
- Mooncake-based KV store infrastructure is already deployed

Example: `examples/online_serving/disaggregated_serving/mooncake_connector/run_mooncake_connector.sh`
Docs: `docs/features/mooncake_connector_usage.md`

Bundled in v0.14.0+ images via `mooncake-transfer-engine >= 0.3.8`.

## MultiConnector — compose backends

Stacks connectors in priority order. Common pattern: NIXL for inter-node prefill handoff + local CPU overflow on each decode pod.

```bash
--kv-transfer-config '{
  "kv_connector":"MultiConnector",
  "kv_role":"kv_both",
  "kv_connector_extra_config":{
    "connectors":[
      {"kv_connector":"NixlConnector","kv_role":"kv_both"},
      {"kv_connector":"OffloadingConnector","kv_role":"kv_both",
       "kv_connector_extra_config":{"block_size":64,"cpu_bytes_to_use":1000000000}}
    ]
  }
}'
```

Order matters — the first connector that can satisfy a lookup wins. Put the fastest tier first.
