# NIXL Plugins — Per-Backend Reference

13 plugins ship in v1.0.1. This file provides the cross-cutting matrix + per-plugin entry. Always cross-check the plugin's own `src/plugins/<name>/README.md` for the latest deps and params; this file paraphrases.

## Table of Contents
- [Plugin matrix](#plugin-matrix)
- [Network plugins](#network-plugins)
  - [UCX](#ucx)
  - [libfabric](#libfabric)
  - [mooncake \[Preview\]](#mooncake-preview)
  - [uccl \[Preview\]](#uccl-preview)
  - [gpunetio (DOCA GPUNetIO)](#gpunetio-doca-gpunetio)
- [Storage plugins](#storage-plugins)
  - [cuda_gds (NVIDIA GPUDirect Storage)](#cuda_gds-nvidia-gpudirect-storage)
  - [gds_mt (multi-threaded GDS)](#gds_mt-multi-threaded-gds)
  - [posix](#posix)
  - [hf3fs (DeepSeek 3FS)](#hf3fs-deepseek-3fs)
  - [obj (S3)](#obj-s3)
  - [azure_blob](#azure_blob)
  - [gusli](#gusli)
- [Telemetry plugins](#telemetry-plugins)

## Plugin matrix

| Plugin | Class | supportsLocal | supportsRemote | supportsNotif | Memory types | External deps | Status |
|---|---|---|---|---|---|---|---|
| **UCX** | network | yes | yes | yes | DRAM, VRAM | UCX 1.20.x, optional GDRCopy, CUDA | stable, default |
| **libfabric** | network | partial | yes | yes | DRAM, VRAM | libfabric ≥1.21.0, hwloc 2.10+, libnuma | stable; thread-safe in v1.0.1 |
| **mooncake** | network | yes | yes | yes | DRAM, VRAM | Mooncake (BUILD_SHARED_LIBS=ON) | preview; own metadata path |
| **uccl** | network | no (yet) | yes | yes | DRAM, VRAM | UCCL P2P engine, RDMA NIC | preview; intra-node WIP |
| **gpunetio** | network | no | yes | yes | DRAM, VRAM | DOCA GPUNetIO, gdrcopy | stable; single-NIC + single-GPU |
| **cuda_gds** | storage | yes | no | no | VRAM, FILE | cuFile (CUDA Toolkit 12.8+) | stable |
| **gds_mt** | storage | yes | no | no | VRAM, FILE | cuFile + thread pool | stable |
| **posix** | storage | yes | no | no | DRAM, FILE | libaio (default) or liburing | stable |
| **hf3fs** | storage | yes | no | no | DRAM, FILE | hf3fs_usrbio.so, libhf3fs_api_shared.so | stable |
| **obj** | storage | yes | no | no | DRAM, OBJ | aws-sdk-cpp 1.11.x (s3 + s3-crt), optional cuobjclient-13.1 | stable |
| **azure_blob** | storage | yes | no | no | DRAM, OBJ | azure-sdk-for-cpp (storage-blobs + identity) | stable |
| **gusli** | storage | yes | no | no | DRAM, BLOCK | libgusli_clnt.so | stable |
| **telemetry** | telemetry | n/a | n/a | n/a | n/a | static (cyclic) or Prometheus exposer (dynamic) | stable; Prometheus is beta |

"supportsLocal=partial" for libfabric: works for cross-process loopback on the same node but not as a substitute for in-process memory copy.

## Network plugins

### UCX

**Default backend.** High-perf network library covering RDMA (IB, RoCE), TCP, shared mem, NVLink.

```python
agent.create_backend("UCX", {"num_threads": "4"})
```

Common env vars (UCX-level, not NIXL-specific):
- `UCX_TLS=cuda_copy,sm,tcp` — transports to allow. **`tcp` alone is the #1 source of segfaults in vLLM-NIXL deploys** if the GPU is reachable but cuda_copy isn't enabled.
- `UCX_NET_DEVICES=mlx5_0:1` — restrict NICs.
- `UCX_LOG_LEVEL=info|debug|trace` — for debugging.
- `UCX_RNDV_THRESH` — rendezvous threshold; tune for KV-cache block sizes.

**Recent fixes:**
- v1.0.1 PR #1565: improved progress + notif handling.
- v1.0.1 PR #1573: removed indirection for hot path.
- v1.0.1 PR #1527: EFA-specific config gated to EFA only — pre-1.0.1 EFA defaults could degrade non-EFA setups.
- v1.0.1 PR #1568: thread-safety in tests.

GDRCopy is recommended for max GPU↔NIC throughput but UCX/NIXL work without it. v1.0.1 builds disable gdrcopy in the bundled UCX (PR #1436) to avoid linkage conflicts; build your own UCX with gdrcopy if you need it.

### libfabric

OpenFabrics Interfaces (OFI). The go-to choice for **AWS EFA** (validated). Other libfabric providers (cxi, verbs, tcp) work but aren't validated.

```python
agent.create_backend("LIBFABRIC", {})
```

**Capabilities** (from plugin README):
- Multi-Rail RDMA — auto-discovers multiple NICs for additive bandwidth.
- GPU Direct (GDR) — required for VRAM transfers.
- Topology-aware GPU↔EFA + NUMA↔EFA mapping via hwloc.
- Async pre-allocated request pools.

**v1.0.1 fixes:**
- PR #1482, #1433: notification override on transfer-handle repost — pre-1.0.1, reposted transfers always used the original notif from prep time. Critical for multi-step KV-transfer protocols.
- PR #1483, #1457: endpoint thread-safety mutexes (FI_THREAD_COMPLETION).
- PR #1510, #1495: active-rail tracking + multi-rank stats.
- PR #1506: multi-GPU memory registration.
- PR #1462: log-level cleanups.

**Build flags:**
```bash
meson setup build -Dlibfabric_path=/path/to/libfabric
```

### mooncake [Preview]

KV-cache-centric transfer engine from Mooncake project. Multi-protocol (TCP/RDMA/CXL/NVMe-oF).

```cpp
nixlAgentConfig cfg;
cfg.useProgThread = false;        // mooncake doesn't support progress thread
agent.createBackend("MOONCAKE", params);
```

**Caveats:**
1. Progress thread NOT supported.
2. Mooncake has its own metadata exchange that bypasses NIXL's. **Don't compose with NIXL ETCD/side-channel flows** for mooncake-only paths.
3. `kMaxRequestCount = 1024` — sum of release requests per `prepXfer`-allocated handle.
4. Notify feature requires latest Mooncake `main` branch; release tags lag.

**Build:** Mooncake must be installed first with `-DBUILD_SHARED_LIBS=ON`. Then build NIXL with `disable_mooncake_backend=false`. Memory-aware parallel ninja build for Mooncake itself in v1.0.1 (#1485).

### uccl [Preview]

Software-transport over RDMA. Designed for heterogeneous GPUs/NICs.

```python
config = nixl_agent_config(backends=["UCCL"])
agent = nixl_agent("agent-name", config)
```

**Today:** internode only. Intra-node and progress thread on the roadmap. Auto-discovers NIC by PCIe distance during memory registration.

vLLM has a UCCL-based NIXL connector path: see vLLM commit `e731733d30d0aed3252dc60427927768bfc0ca73`.

### gpunetio (DOCA GPUNetIO)

GPU-driven RDMA via NVIDIA DOCA. RDMA Read/Write are launched from a CUDA kernel, not the CPU. Best for pipelines where data processing and transfer can be co-scheduled on the GPU.

```python
agent.create_backend("GPUNETIO", {
    "network_devices": "mlx5_0",
    "oob_interface": "ens9f0",       # optional, not needed for IB-mode NICs
    "gpu_devices": "0",
    "cuda_streams": "8",
})
```

**Two modes:**
- **Stream attached**: caller passes `extra_params.customParam` = CUDA stream pointer at `createXferRequest` time. The kernel runs on that stream — line up with the user's pipeline.
- **Stream pool**: backend uses an internal pool of streams (`cuda_streams` size). Better for CPU-driven workflows that just want async network ops.

**Limits:** 1 NIC + 1 GPU per backend instance. To use 2 NICs, instantiate 2 backends. VRAM-only effective; the kernel can't read DRAM.

Tested via NIXLBench:

```bash
LD_LIBRARY_PATH+=:/path/to/gdrcopy/src:/opt/mellanox/doca \
NIXL_PLUGIN_DIR=/path/to/nixl/lib/x86_64-linux-gnu/plugins \
CUDA_MODULE_LOADING=EAGER \
./nixlbench --etcd-endpoints http://etcd:2379 \
  --backend=GPUNETIO --initiator_seg_type=VRAM --target_seg_type=DRAM \
  --runtime_type=ETCD --gpunetio_device_list=0 --device_list=mlx5_0 \
  --start_batch_size=512 --max_batch_size=512 --total_buffer_size=34359738368
```

## Storage plugins

### cuda_gds (NVIDIA GPUDirect Storage)

GPU-direct storage I/O via cuFile. Single-thread submission. For multi-thread, use `gds_mt`.

**cufile.json — load-bearing config.** Without `allow_compat_mode=true`, cuFile fails on filesystems that don't support GDS natively. NVIDIA-recommended overrides for NIXL:

```json
{
  "properties": {
    "allow_compat_mode": true,
    "max_direct_io_size_kb": 16384,
    "max_device_cache_size_kb": 2097152,
    "per_buffer_cache_size_kb": 16384
  }
}
```

```bash
export CUFILE_ENV_PATH_JSON="/path/to/cufile.json"
```

`max_device_cache_size_kb / per_buffer_cache_size_kb >= io_batchsize` is the sizing constraint.

### gds_mt (multi-threaded GDS)

```python
agent.create_backend("GDS_MT", {"thread_count": "8"})
```

Same cuFile-level config as `cuda_gds`. Use for high-IOPS / many-small-files workloads where single-thread submission is the bottleneck.

### posix

POSIX file I/O. Default backend = libaio; opt-in liburing.

```python
agent.create_backend("POSIX", {"use_uring": "true"})
```

**Docker caveat.** `io_uring` syscalls are blocked by Docker's default seccomp profile. Add a custom seccomp JSON or run the container with `--security-opt seccomp=unconfined` (don't do this in production).

**v1.0.1 PR #1562**: dangling pointer fix.

### hf3fs (DeepSeek 3FS)

```cpp
nixl_b_params_t params;
params["mem_config"] = "auto";   // "dram" / "dram_zc" / "auto"
agent.createBackend("HF3FS", params, hf3fs);
```

**`mem_config` semantics:**
- `dram_zc` (zero-copy): `mmap()` user memory directly into 3FS backend. Requires page-aligned addr + size = multiple of page size. Fails loud on bad alignment — use this in tests.
- `dram`: never zero-copy; always use a 3FS-allocated shared buffer with copy.
- `auto` (default): try zero-copy, fall back to copy on failure.

Install 3FS: `https://github.com/deepseek-ai/3FS/`. Headers in `/usr/include/hf3fs/`, libs `hf3fs_usrbio.so` + `libhf3fs_api_shared.so` in `/usr/lib/`.

### obj (S3)

S3 (or S3-compatible) backend. Dual-client architecture:
- `awsS3Client` — standard SDK, for small objects.
- `awsS3CrtClient` — AWS Common Runtime, multipart + connection pooling, for large objects.
- Optional `cuobjclient-13.1` — GPU-direct accelerated S3 ("S3 Accelerated Engines"). If present, used automatically; if not, transparent fallback to standard S3 + S3 CRT.

```python
agent.create_backend("OBJ", {
    "endpoint_override": "https://s3.us-west-2.amazonaws.com",
    "bucket": "my-kv-cache",
    # crtMinLimit: object size threshold for CRT vs std client
    "crtMinLimit": "16777216",
})
```

**Build deps:**
```bash
git clone --recurse-submodules https://github.com/aws/aws-sdk-cpp.git --branch 1.11.581
cmake .. -DBUILD_ONLY="s3;s3-crt" -DCMAKE_INSTALL_PREFIX=/usr/local
make -j install
```

### azure_blob

Azure Blob equivalent of `obj`.

```bash
git clone --depth 1 https://github.com/Azure/azure-sdk-for-cpp.git --branch azure-storage-blobs_12.15.0
cmake .. -DBUILD_SHARED_LIBS=ON -DDISABLE_AMQP=ON -DDISABLE_AZURE_CORE_OPENTELEMETRY=ON \
  -DAZURE_SDK_DISABLE_AUTO_VCPKG=1
cmake --build . --target azure-storage-blobs azure-identity
```

Backend params via `nixl_b_params_t` map, env vars also supported (params take precedence). Read `src/plugins/azure_blob/README.md` for the full param list.

### gusli

User-space block storage client. Communicates with a GUSLI server via:
1. **Local shared memory** (recommended) — server integrated into SPDK / NVMeshUM / etc.; bypasses kernel.
2. **Networked** (`device_type=N`) — remote GUSLI server.
3. **Direct** — local block devices via kernel APIs (fallback, not for production).

```cpp
nixl_b_params_t params = gen_gusli_plugin_params(agent);
nixlBackendH* gusli_ptr = nullptr;
agent.createBackend("GUSLI", params, gusli_ptr);
```

Config file built via GUSLI client API:

```cpp
gusli::client_config_file conf(1);
using gsc = gusli::bdev_config_params;
conf.bdev_add(gsc(__stringify(UUID_LOCAL_FILE_0), gsc::bdev_type::DEV_FS_FILE,
                   "./store0.bin", "sec=0x03", 0, gsc::connect_how::SHARED_RW));
params["config_file"] = conf.get();
```

Build GUSLI: `make all BUILD_RELEASE=1 BUILD_FOR_UNITEST=0 ALLOW_USE_URING=0`. Install before NIXL.

## Telemetry plugins

### Cyclic shared-memory buffer (built-in, static)

Always available. Enable via env var:

```bash
export NIXL_TELEMETRY_ENABLE=1
export NIXL_TELEMETRY_DIR=/tmp/nixl-telemetry
export NIXL_TELEMETRY_BUFFER_SIZE=4096
export NIXL_TELEMETRY_RUN_INTERVAL=100
```

Outputs one shared-memory file per agent (named after agent name). Read with:

```bash
./builddir/examples/cpp/telemetry_reader /tmp/nixl-telemetry/agent_name
python3 examples/python/telemetry_reader.py --telemetry_path /tmp/nixl-telemetry/agent_name
```

Producer appends events under a mutex; consumer reads in ring-insertion order. **Silent loss possible** under sustained overflow — bump `NIXL_TELEMETRY_BUFFER_SIZE` if events drop.

### Prometheus exporter (dynamic, beta)

Loaded as a dynamic plugin:

```bash
export NIXL_TELEMETRY_ENABLE=1
export NIXL_TELEMETRY_EXPORTER=prometheus
# Plugin-specific config in src/plugins/telemetry/prometheus/README.md
```

Exposer is shared across all agents in the same process (PR #1470). Beta status as of v1.0.1.

### Custom exporter

Author guide: `src/plugins/telemetry/README.md`. Implement the `Exporter` interface, build as a `.so`, drop in `NIXL_PLUGIN_DIR`, point `NIXL_TELEMETRY_EXPORTER` at it.
