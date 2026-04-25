# Connector configuration recipes

Detailed recipes for each vLLM KV caching backend. Load when selecting or configuring a specific connector.

## Table of contents
- [Native CPU offload](#native-cpu-offload-single-node-simplest)
- [LMCache with DRAM + NVMe tiers](#lmcache-with-dram--nvme-tiers-single-node-production)
- [LMCache P2P — KV sharing across instances](#lmcache-p2p--kv-sharing-across-instances)
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
  --disable-hybrid-kv-cache-manager \
  --max-model-len 200000 \
  --enable-prefix-caching
```

`--disable-hybrid-kv-cache-manager` is **mandatory** with `OffloadingConnector` — without it the engine fails at startup with `ValueError: Connector OffloadingConnector does not support HMA but HMA is enabled.` See SKILL.md "Critical pitfalls" for the why.

Under the hood: pinned host memory (`cudaHostRegister`-backed mmap), LRU eviction policy by default, ARC also available. Code paths live in `vllm/v1/kv_offload/` with `vllm/v1/kv_offload/cpu/policies/` for eviction strategies.

### Verified small-GPU recipe (consumer card)

Tested 2026-04-25 on RTX 4060 Ti 16 GB SM 8.9 + cu130-nightly + Qwen3-4B BF16, TP=1. Native offload runs cleanly; `KV Transfer metrics: GPU_to_CPU_total_bytes=...` log lines confirm offload tier engaged. See `diagnostics.md` for the verification checklist.

```bash
vllm serve Qwen/Qwen3-4B \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.92 \
  --max-model-len auto \
  --enable-prefix-caching \
  --disable-hybrid-kv-cache-manager \
  --kv-offloading-size 6 \
  --kv-offloading-backend native \
  --block-size 32 \
  --max-num-batched-tokens 4096 \
  --max-num-seqs 16 \
  --load-format fastsafetensors
```

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
    --disable-hybrid-kv-cache-manager \
    --max-model-len 200000 \
    --enable-prefix-caching
```

`--disable-hybrid-kv-cache-manager` is mandatory with the LMCache backend too — same `OffloadingConnector` requirement as native.

Key env vars:
- `LMCACHE_MAX_LOCAL_CPU_SIZE` and `LMCACHE_MAX_LOCAL_DISK_SIZE` are **GiB as floats** (e.g. `5.0`, `1600`)
- `LMCACHE_LOCAL_DISK` takes comma-separated paths in `file:///` URL form
- `LMCACHE_LOCAL_DISK_PATH_SHARDING=by_gpu` (default) shards one path per GPU device id. Match drive count to GPU count when possible; with fewer drives than GPUs, multiple GPUs will contend on a single drive.

Keep `LMCACHE_MAX_LOCAL_CPU_SIZE` and `--kv-offloading-size` consistent. LMCache env vars win on the backend side; inconsistency leads to scheduler miscounting available slots.

Avoid `LMCACHE_LOCAL_CPU=False` (a.k.a. `use_hot=False`) until LMCache #2942 lands — `LocalCPUBackend.allocate()` deadlocks when the staging buffer fills with no eviction path. The default is `True`; do not flip it. Skip the disk tier altogether (#2502) on production paths until the fix is released; DRAM-only is the safer default.

### Pool sizing — don't under-allocate

LMCache's `LocalCPUBackend` allocator stores in fixed-size memory blocks (`chunk_size × layers × 2 × num_kv_heads × head_dim × dtype_bytes`). On Qwen3-4B BF16 with `chunk_size=256` that's **36 MiB per block**. If aggregate prefix footprint fills the pool, you get a warning wall:

```
LMCache WARNING: Failed to allocate memory block of size 37748736 because no memory is available
```

Verified 2026-04-25: `LMCACHE_MAX_LOCAL_CPU_SIZE=6` on an 8-prefix × 6000-token bench (~48 K tokens, ~6.75 GB raw KV) triggered 413 alloc-failures in 60 s. Bumping to `12` eliminated them **and** raised CPU-tier hit rate from 9.4 % → 39.4 % on identical workload.

Sizing rule: `LMCACHE_MAX_LOCAL_CPU_SIZE ≥ 2 × (num_prefixes × prefix_len × kv_bytes_per_token)`. Apply the 2× margin for concurrent-store headroom during burst prefill. Keep `LMCACHE_MAX_LOCAL_CPU_SIZE == --kv-offloading-size` (LMCache wins on the backend, vLLM on the scheduler — mismatch costs the scheduler correctness).

### Running LMCache 0.4.4+ on a CUDA 13 image

As of 2026-04-25 the bundled `lmcache 0.4.3` inside `vllm/vllm-openai:cu130-nightly` is built against CUDA 12 and fails `import lmcache.c_ops` with `libcudart.so.12: cannot open shared object file` on CUDA-13 hosts (LMCache #2843). Workaround at container-start is to `pip install --force-reinstall` the CUDA-13 wheel:

```yaml
command:
  - bash
  - -c
  - |
    set -euo pipefail
    pip install --quiet --upgrade --force-reinstall --no-deps \
      https://github.com/LMCache/LMCache/releases/download/v0.4.4-cu13/lmcache-0.4.4-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
    python3 -c "import lmcache.c_ops; print('lmcache c_ops OK')"
    exec vllm serve "$@"
  - bash
args: [--model, ..., --kv-offloading-backend, lmcache, ...]
```

Match the `cpXYZ` in the wheel to the image's Python (`python3 --version`); current vllm-openai images are `cp312`. Set `PYTHONHASHSEED=0` too — LMCache warns and falls back to a non-stable hash if unset.

### DRAM + local disk tier

Enable a local-disk tier alongside DRAM with `LMCACHE_LOCAL_DISK="file:///<path>"` + `LMCACHE_MAX_LOCAL_DISK_SIZE=<GiB>`. Pre-create and chmod the directory in an init container (LMCache does not `mkdir -p` it):

```yaml
env:
  - {name: LMCACHE_LOCAL_CPU, value: "True"}
  - {name: LMCACHE_MAX_LOCAL_CPU_SIZE, value: "12"}
  - {name: LMCACHE_LOCAL_DISK, value: "file:///models/lmcache-kv"}
  - {name: LMCACHE_MAX_LOCAL_DISK_SIZE, value: "30"}
  - {name: LMCACHE_CHUNK_SIZE, value: "256"}
  - {name: PYTHONHASHSEED, value: "0"}
  - {name: LMCACHE_LOG_LEVEL, value: "ERROR"}  # silences allocator-pressure warnings; see below
```

Keep `LMCACHE_ENABLE_ASYNC_LOADING` unset / `False` until LMCache #2502 is closed. Both backends log `Created backend: LocalCPUBackend (LocalCPUBackend)` and `Created backend: LocalDiskBackend (LocalDiskBackend)` at init; verify in the pod log.

**Steady-state noise — benign.** Once the DRAM pool fills, every eviction cycle emits:

```
LMCache WARNING: Failed to allocate memory block of size 37748736 because no memory is available
```

This is allocator-pressure: `LocalCPUBackend.allocate()` couldn't satisfy immediately → LRU evicts to disk → retries → succeeds. Every request still returns 200 OK, every retrieval still lands. The log chatter is proportional to eviction rate, not failure rate. `LMCACHE_LOG_LEVEL=ERROR` hides it while preserving real errors (source: `lmcache/logging.py` env-var lookup, default `INFO`).

Verified 2026-04-25 on Qwen3-4B + 12 GB DRAM + 30 GB disk at `/models/lmcache-kv` ext4: 128-request 16-prefix × 10 K-token bench → **81.5 % combined external-tier hit rate** (vs 2.1 % for native offload on the same workload, 39.4 % for DRAM-only). 624 chunks written to disk, DRAM-tier reads at 6.2 GB/s, disk-tier reads at 0.7–1.5 GB/s. No crashes, no `ERROR`-level lines — only the benign `WARNING` allocator noise.

## LMCache P2P — KV sharing across instances

Use case: two or more vLLM pods serving the same model discover and retrieve KV chunks from each other over the network (NIXL/UCX transport). First hit on any pod → subsequent hits on all pods. Equivalent to a shared-LRU CPU tier spread across nodes.

> NIXL is the transport layer here; for transport choice / UCX tuning / plugin selection see the **`nvidia-nixl`** skill. This section covers LMCache P2P configuration only.

Verified 2026-04-25 on 2× RTX 4060 Ti + cu130-nightly + Qwen3-4B BF16 + LMCache 0.4.4-cu13. Prime pod-a with a 1002-token prefix; pod-b receives same prefix → **pod-a log `Received P2P batched lookup and get msg`**, pod-b log `Retrieved 768 of 768 required tokens, cost 22.87 ms, throughput 4.61 GB/s`, pod-b external hit rate **76.6 %**.

### Topology

Three pieces: one controller + N vLLM pods with LMCacheConnectorV1 + `kv_role=kv_both`.

```
┌──────────────┐    8300/pull     ┌─────────────┐
│ pod-a        │ ───────────────► │ lmcache-    │
│ LMCache       │                  │ controller  │
│  - admit keys │ ◄─────────────── │             │
│  - peer lookup│    8400/reply    │  registry   │
└──────┬───────┘                  └─────┬───────┘
       │                                │
       │ nixl (ZMQ+UCX)                 │ 8300/8400
       │ init port 8200                 │
       │ lookup port 8201               ▼
       ▼                          ┌─────────────┐
  ┌──────────┐  direct peer       │ pod-b       │
  │ pod-a    │◄────────────────── │ LMCache     │
  │ KV store │                    │ kv_role=both│
  └──────────┘                    └─────────────┘
```

### Required configuration (6 non-obvious settings)

All six must be set. Miss any one → silent 0 %-hit-rate failure with no error logs. Confirmed by live diagnosis on the lab; the LMCache README examples imply these but don't call them out.

| Setting | Default | Required | Why |
|---|---|---|---|
| `enable_p2p: True` | `False` | mandatory | Instantiate P2PBackend in storage manager |
| `transfer_channel: "nixl"` | — | mandatory | Select NIXL/UCX transport |
| `enable_controller: True` + controller pod at `controller_pull_url`/`controller_reply_url` | `False` | mandatory | Controller mediates key-to-peer lookups |
| **`enable_kv_events: True`** | `False` | **mandatory** | Without it pod-a never reports stored chunks via `KVAdmitMsg` → controller has no registry → pod-b's P2P lookup always returns empty `layout_info` |
| **`enable_async_loading: True`** | `False` | **mandatory** | Without it, vLLM's lookup goes through sync `batched_contains` path where `P2PBackend.contains()` unconditionally returns False — P2P is never queried. Async path hits `batched_async_contains` which does contact the controller |
| **`p2p_host` = pod's own IP via `LMCACHE_P2P_HOST` env** | — | **mandatory in K8s** | LMCache uses `p2p_host:p2p_lookup_port` both for ZMQ bind AND for peer advertisement. Binding to a Service FQDN / headless FQDN fails during startup DNS race (`ZMQError: Cannot assign requested address`) because the name resolves to a kube-proxy VIP or to a not-yet-populated EndpointSlice. Pod IP is always a local interface → bind works → advertisement works because K8s pod networking is flat |
| `PYTHONHASHSEED=123` on all pods | — | mandatory | Deterministic hash so both pods compute the same chunk key for the same tokens |

### Minimal K8s example

Per-pod env:

```yaml
env:
  - name: POD_IP
    valueFrom:
      fieldRef:
        fieldPath: status.podIP
  - name: LMCACHE_P2P_HOST
    value: "$(POD_IP)"
  - name: LMCACHE_CONFIG_FILE
    value: /etc/lmcache/lmcache.yaml
  - name: PYTHONHASHSEED
    value: "123"
  - name: UCX_TLS
    value: "tcp"
```

Per-pod LMCache config ConfigMap (instance A; instance B uses different `lmcache_instance_id` + different ports):

```yaml
chunk_size: 256
local_cpu: True
max_local_cpu_size: 5
enable_async_loading: True

enable_p2p: True
# p2p_host set via LMCACHE_P2P_HOST env from downward API
p2p_init_ports: 8200
p2p_lookup_ports: 8201
transfer_channel: "nixl"

enable_controller: True
lmcache_instance_id: "lmcache_instance_a"
controller_pull_url: "lmcache-controller.<ns>.svc.cluster.local:8300"
controller_reply_url: "lmcache-controller.<ns>.svc.cluster.local:8400"
lmcache_worker_ports: 8500
enable_kv_events: True
```

vLLM flag:

```
--kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'
```

Controller pod (CPU-only, same LMCache wheel):

```
lmcache_controller --host 0.0.0.0 --port 9000 \
  --monitor-ports '{"pull": 8300, "reply": 8400}'
```

### Verifying it works

Prime pod-a with a long unique prefix via `/v1/completions`, wait ~3 s for `KVAdmit` to propagate, send the same prefix to pod-b. Expect:

- pod-a log: `LMCache INFO: Received P2P batched lookup and get msg, lookup_id: ...`
- pod-b log: `LMCache INFO: Retrieved N out of N required tokens... throughput: X GB/s`
- pod-b log: `External prefix cache hit rate: >0 %`
- Controller is silent on success (dispatch is unlogged at INFO level).

If you see `LMCache hit tokens: 0, need to load: 0` on pod-b, the 6-setting matrix has a missing piece — check `enable_kv_events` and `enable_async_loading` first.

### Known limitation — NIXL transport only

`transfer_channel: "nixl"` requires NIXL + UCX built into the image. `vllm/vllm-openai:cu130-nightly` and `INSTALL_KV_CONNECTORS=true` images ship it. `UCX_TLS=tcp` disables RDMA for lab hardware without an RDMA NIC.

### Combining P2P with the local-disk tier

Add `local_disk` and `max_local_disk_size` per-instance (distinct paths so the two LMCache instances don't trample each other's metadata) — controller routes by `lmcache_instance_id`, tier is internal to each instance.

```yaml
local_cpu: True
max_local_cpu_size: 5
local_disk: "file:///models/lmcache-kv-a"   # /-b on the other instance
max_local_disk_size: 20
```

Verified 2026-04-25 on the same 2× 4060 Ti lab. Three backends register per pod (`Created backend: LocalCPUBackend`, `P2PBackend`, `LocalDiskBackend`). LMCache writes chunks to both DRAM and NVMe simultaneously (shadow-write pattern; eviction kicks in only at DRAM cap). Disk write bandwidth observed: **932–2188 MB/s sustained** (consistent with PCIe Gen4 NVMe). When pod-b queries the controller for a prefix pod-a stored, the lookup is **tier-agnostic** — controller returns pod-a's instance regardless of whether the chunk is currently in DRAM or NVMe; pod-a's P2P handler reads from whichever tier holds it.

Usage payoff: the DRAM tier is still the hot path for repeated cross-pod hits, but the NVMe tier extends pod-a's effective working set far beyond DRAM cap without losing P2P-serveability. For the same workload, the combined-tier hit rate matches or exceeds DRAM-only.

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

> NIXL itself (the underlying transfer library) is documented in the **`nvidia-nixl`** skill — agent API, all 13 backend plugins (UCX, GDS, Mooncake, libfabric, etc.), telemetry, build paths, ETCD vs side-channel metadata. This section covers vLLM-side wiring only. For transport selection (`UCX_TLS`, `cuda_ipc`), telemetry interpretation, plugin authoring, and the `nixl_agent` Python API → `nvidia-nixl`.

```bash
vllm serve <model> ... \
  --kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_both","kv_buffer_device":"cuda","kv_connector_extra_config":{"backends":["UCX","GDS"]}}'
```

- `kv_role`: `kv_producer` (prefill instance), `kv_consumer` (decode instance), or `kv_both` (symmetric)
- `backends`: `UCX` (default transport, works over Ethernet/IB/RoCE), `GDS` (direct storage). Combine as needed.
- Reference example: `tests/v1/kv_connector/nixl_integration/run_accuracy_test.sh`
- Model/feature compatibility: `docs/features/nixl_connector_compatibility.md`

Bundled in v0.14.0+ images via `nixl-cu12` / `nixl-cu13` (matched to the image's CUDA).

### Verified K8s 1P1D recipe (consumer-lab)

Tested 2026-04-25 on 2× RTX 4060 Ti + cu130-nightly + Qwen3-4B + vLLM v0.19.2rc1. Prefiller pod (GPU 0, `kv_role=kv_producer`) + decoder pod (GPU 1, `kv_role=kv_consumer`) + proxy pod running `tests/v1/kv_connector/nixl_integration/toy_proxy_server.py`. Client request → proxy → prefiller (2-token prefill) → NIXL UCX transfer of KV blocks → decoder (10 tokens decoded) → stream back to client. Round-trip 755 ms. Decoder log: `Transfer plan: TransferTopology(tp_ratio=1, K=8, local_tp=1, remote_tp=1, local_rank=0, remote_block_len=65536)`.

Key env vars per vLLM pod (both prefiller + decoder):

```yaml
env:
  - name: POD_IP
    valueFrom:
      fieldRef:
        fieldPath: status.podIP
  - name: VLLM_NIXL_SIDE_CHANNEL_HOST
    value: "$(POD_IP)"
  - name: VLLM_NIXL_SIDE_CHANNEL_PORT
    value: "5600"
  - name: UCX_TLS
    # cuda_copy is mandatory — without it UCX tags CUDA buffers as host and
    # the prefiller segfaults in nixlUcxSharedThread::run() after prefill.
    # Error signature: "W ucx_utils.cpp:581: memory is detected as host,
    # check that UCX is configured with CUDA support" followed by segfault.
    # sm = shared-mem transport (same-node); tcp = network fallback.
    # No RDMA / NVLink on consumer HW, so omit rc/ud/cuda_ipc.
    value: "cuda_copy,sm,tcp"
  - name: UCX_NET_DEVICES
    value: "all"
```

Per-pod flags:

```
--kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_producer","kv_load_failure_policy":"fail"}'
--enforce-eager   # NIXL + CUDA graphs combination has pending bugs; eager is safer
```

(Decoder: `kv_role=kv_consumer`.)

Services MUST be headless (`clusterIP: None` + `publishNotReadyAddresses: true`) — `VLLM_NIXL_SIDE_CHANNEL_HOST=$(POD_IP)` means the pods advertise pod IPs to each other via the side-channel handshake. Same reasoning as LMCache P2P: binding/advertising via Service VIP breaks because a kube-proxy VIP is not a local interface.

Proxy (toy_proxy_server.py from vLLM repo) runs as a CPU-only pod, ConfigMap-mounted:

```
python3 toy_proxy_server.py \
  --host 0.0.0.0 --port 8192 \
  --prefiller-hosts qwen3-4b-nixl-prefiller.<ns>.svc.cluster.local \
  --prefiller-ports 8000 \
  --decoder-hosts qwen3-4b-nixl-decoder.<ns>.svc.cluster.local \
  --decoder-ports 8000
```

Set `OPENAI_API_KEY=sk-dummy` on the proxy pod (its code reads it for auth headers).

### NIXL gotchas (consumer HW)

1. **UCX must have CUDA memtype in `UCX_TLS`.** `UCX_TLS=tcp` alone segfaults on first transfer because UCX doesn't map CUDA buffers. Use `cuda_copy,sm,tcp`. Image's UCX build includes `libuct_cuda.so` — it IS compiled with CUDA, just not enabled by default.
2. **NIXL warmup race.** First request immediately after pod-ready may fail with `NIXL_ERR_REMOTE_DISCONNECT` on the decoder. Second request onward succeeds. Give the side-channel handshake ~5 s.
3. **Proxy DNS pool cache.** If you restart vLLM pods after proxy has cached httpx connections to old pod IPs, also restart the proxy. httpx `AsyncClient(limits=httpx.Limits(max_connections=None, max_keepalive_connections=None))` doesn't re-resolve on retry.
4. **Both `nixl_cu12` and `nixl_cu13` ship in `cu130-nightly`** — the meta `nixl` wheel `Requires: nixl-cu12`, but `nixl_cu13._bindings` is what gets loaded on CUDA 13 hosts. Both coexist; no action needed.
5. **NIXL pre-v0.20 uses `--enforce-eager`** per upstream docs because NIXL + CUDA graphs has pending interactions. Lose ~20 % throughput vs graphs, but avoid crashes.

### 1P1D vs single-pod — when disaggregation pays off

On the consumer lab (2× 4060 Ti, same-node, `cuda_copy,sm,tcp` transport, `--enforce-eager`) disaggregation is **slower than a monolithic pod on short decode-dominated workloads**. Measured 2026-04-25 with `vllm bench serve --random-input-len 512 --random-output-len 64 --num-prompts 30 --request-rate 3`:

| Metric | 1P1D via proxy | Single-pod (same HW) | Delta |
|---|---|---|---|
| Req throughput | 1.65 req/s | 2.21 req/s | 1P1D **−34 %** |
| Total tok throughput | 965 tok/s | 1291 tok/s | 1P1D **−34 %** |
| Mean TTFT | 3786 ms | 411 ms | 1P1D **9×** worse |
| Median TTFT | 4238 ms | 126 ms | 1P1D 34× worse |
| TPOT | 37.9 ms | 36.8 ms | tied |

Why 1P1D lost on this workload: short prompts mean prefill cost is cheap, so there's no expensive-prefill savings to recover; same-node NIXL transfer (`cuda_copy,sm,tcp`) adds GPU→host memcpy + loopback per request; the prefiller serialises all arrivals through one GPU while the decoder is idle waiting for KV handoff; `--enforce-eager` disables CUDA graphs on both sides.

**1P1D pays off when**: input ≫ output (16 k+ prefill, 100-token decode), prefill latency dominates TTFT, you want the decoder to hit low TPOT without prefill-step interference, *and* you have more than one decode consumer per prefiller (1P2D / 1P4D). On short-prompt decode-dominated traffic with single-node same-fabric transport, a single pod with prefix caching wins. Reserve disaggregation for long-context coding-agent / RAG / research-agent loads and multi-node deployments where the prefill pool can be scaled independently from decode.

### NIXL transfer telemetry caveats + measured numbers

> **For NIXL telemetry internals** (Prometheus + cyclic shared-memory metrics, `NIXL_TELEMETRY_ENABLE`, `nixlbench` benchmarking) → `nvidia-nixl` skill. The notes below are vLLM-side observations only.

**Do not trust `KV Transfer metrics Throughput (MB/s)` at face value.** Two known issues affect the number:

- **vllm-project/vllm#33170 (open)** — telemetry sums per-rank `xfer_time` as if serial, so overlapping transfers (which is the normal concurrent case) are counted as longer-than-reality. With TP>1 it also multiplies per-rank. Effect: reported throughput is **lower than actual** when requests overlap or TP>1.
- **vllm-project/vllm#34054 + PR #36475 (merged 2026-03-09, in v0.19+)** — before this PR, NIXL+UCX silently fell back to host-buffer `cuda_copy` instead of `cuda_ipc` (NVLink) on same-host setups because a spawned thread had no CUDA context, disabling `cuda_ipc`. Post-fix, run with `UCX_PROTO_INFO=y` and grep the decoder log for `ucp.*cuda.*cuda` — `cuda_ipc/cuda` means NVLink is actually being used, otherwise host-staged.

Measured on consumer 2× 4060 Ti same-node K8s pods (`cuda_copy,sm,tcp`, sm unavailable across pods with per-pod emptyDir `/dev/shm`, no NVLink/P2P/RDMA):

| Prompt | MB/transfer | Reported throughput | Notes |
|---|---|---|---|
| 5 tokens | 4.5 MB | 150 MB/s | Latency-bound (72 descriptors × ~13 ms/descriptor) |
| 1562 tokens | 220.5 MB | 240 MB/s | Per-descriptor overhead still dominates |

**Baseline reality check**: raw inter-pod TCP on same node measures **1.6 GB/s** (Python HTTP POST of 100 MB). So UCX/NIXL is leaving ~7× on the table in this config — some of the gap is the broken telemetry, some is per-descriptor overhead.

Reported reference points from upstream (issue #34054 closed 2026-03-09):

| Hardware / transport | Descriptors | Reported throughput | Notes |
|---|---|---|---|
| Same-host 8× H100 GCP VM, pre-#36475 (host-buffer fallback) | 40064 | **1800 MB/s** | NVLink not engaged due to CUDA-context bug |
| Same-host H100 + NVLink, post-#36475 (`cuda_ipc` selected) | — | **>10 GB/s** (expected) | Confirmed via `UCX_PROTO_INFO` log `cuda_ipc/cuda` |

**Why the descriptor count matters.** NIXL emits one descriptor per transformer layer per K or V buffer. Qwen3-4B has 36 layers → 72 descriptors per transfer regardless of prompt length. UCX processes each sequentially with per-message overhead. Models with more layers (e.g. DeepSeek-V3 at 61 layers → 122 descriptors) pay more handshake cost. Larger `--block-size` reduces descriptor count because each layer chunk covers more tokens.

### Raising performance on consumer HW — what works, what doesn't

Tested 2026-04-25 on 2× 4060 Ti same-node K8s pods, Qwen3-4B, 1562-token prefills:

| Config | Descriptors | MB/transfer | Reported throughput | UCX cfg |
|---|---|---|---|---|
| `block_size=32`, per-pod `emptyDir` `/dev/shm` | 72 | 220 | 240 MB/s | `inter-node cfg#2` |
| `block_size=32`, `hostPath: /dev/shm` shared | 108 | 157 | 232 MB/s | **`intra-node cfg#1`** |
| `block_size=128`, `hostPath: /dev/shm` shared | 144 | 324 | 222 MB/s | `intra-node cfg#1` |

**Only the UCX-classification changed meaningfully.** Sharing `/dev/shm` via `hostPath` upgraded `inter-node cfg#2` to `intra-node cfg#1` (confirmed via `UCX_PROTO_INFO=y` log grep for `ucp_context_N <classification> cfg#N`). Raw throughput barely moved. This means UCX transport **is not the bottleneck** at this scale — per-descriptor NIXL dispatch overhead is (~6–10 ms/descriptor, 72–144 descriptors per transfer, dominating the total transfer wall-time). `--block-size` does not reduce the descriptor count in a useful way; NIXL descriptors are keyed by layer × K/V, not by KV block size.

The only thing that meaningfully lifts this ceiling on same-node K8s is getting UCX onto **`cuda_ipc/cuda`** — which requires two GPUs with PCIe P2P enabled (H100 + NVLink / NVSwitch, or MIG-capable datacenter cards). Consumer 4060 Ti driver disables P2P; `cuda_ipc` stays off regardless of `UCX_TLS` setting.

**Summary of fixes in order of verified payoff:**

1. **Run on H100/H200 + NVLink or InfiniBand.** This is what NIXL 1P1D is designed for — `cuda_ipc` selects NVLink; reported throughput jumps to 10 GB/s+ per vllm-project/vllm PR #36475 test data.
2. **Share `/dev/shm` via `hostPath`** even on consumer HW — upgrades UCX to `intra-node cfg`. Minor throughput impact but removes a correctness trap (the `inter-node` TCP path had more handshake overhead and the 6-ms NIXL overhead obscured any gain). Security trade-off: any pod with the hostPath mount can see other pods' shm — acceptable for a lab, not for multi-tenant.
3. **Collapse prefiller + decoder into one pod with two containers** if you just want to demonstrate the protocol at full intra-process speed. Defeats pod-level disaggregation.
4. **Verify `cuda_ipc` is actually selected** via `UCX_PROTO_INFO=y` on H100/H200 — grep decoder log for `ucp_context_0 intra-node cfg#N ... cuda_ipc/cuda`. If you see `cuda_copy` or `host memory to cuda` instead, cuda_ipc is not engaged and you're leaving NVLink on the table (vllm-project/vllm issue #34054 / PR #36475).

NIXL 1P1D on consumer hardware validates **the plumbing** — UCX handshake, side-channel port, proxy round-trip, `kv_transfer_params` threading through prefiller→decoder. It does **not** validate the performance envelope. Don't benchmark PD strategies on consumer HW and extrapolate to H100 — the per-descriptor overhead profile is totally different once `cuda_ipc` engages.

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
