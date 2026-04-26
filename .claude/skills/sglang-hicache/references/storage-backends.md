# L3 storage backends

Pick exactly one (omit `--hicache-storage-backend` for L1+L2 only). Backend factory at `python/sglang/srt/mem_cache/storage/backend_factory.py`.

## Selection summary

| Backend | Production-ready | Hybrid-model support (2026-04-25) | Layout requirement | Key dep |
|---|---|---|---|---|
| `mooncake` | ✓ best-tested 2026 | Mamba/SSM ✓ (v0.5.10), DSA ✓ (v0.5.10), SWA pending v0.5.11 | `page_first` or `page_first_direct` | RDMA NICs + master daemon |
| `hf3fs` | ✓ on DeepSeek operator clusters | Mamba/SSM + DSA pending v0.5.11 (PR #23241) | any | DeepSeek 3FS deployment |
| `nixl` | ✓ for NVIDIA Dynamo / GB200 | depends on NIXL plugin | `page_first` or `page_first_direct` for zero-copy | `nixl-cu12` or `nixl-cu13` |
| `aibrix` | partial (PrisKV not OSS) | not documented | configurable | `aibrix-kvcache` Python lib |
| `eic` | volcengine cloud only | not documented | `page_first` | proprietary |
| `simm` | scitix RDMA shops | not documented | `page_first` or `page_first_direct` | scitix cluster manager |
| `dynamic` | user-supplied | depends on impl | depends | none |
| `lmcache` | replaces hicache, doesn't extend it | depends on LMCache (still broken on hybrid per LMCache #3106) | n/a | `pip install lmcache` |
| `file` | DEV / CI ONLY | yes (any model) | any | none |

## `mooncake`

Best-supported L3 backend in 2026. Only one with shipped hybrid-Mamba support (PR [#21259](https://github.com/sgl-project/sglang/pull/21259) in v0.5.10).

### Install

```bash
pip install mooncake-transfer-engine==0.3.10.post1   # pin to known-good
# RDMA NIC required (mlx5 / RoCE / IB). GPU↔CPU↔NIC topology matters for perf.
```

### Required env / extra-config

```toml
# /etc/sglang/mooncake.toml — pass via --hicache-storage-backend-extra-config "@..."
[mooncake]
master_server_address = "10.0.0.10:50051"
metadata_server       = "etcd://10.0.0.20:2379"  # or "p2p" for embedded mode
global_segment_size   = "32GB"
local_buffer_size     = "4GB"
device                = "auto"                    # or specific HCA/IB device

[mooncake.eviction]
high_watermark_ratio  = 0.9                       # backend handles L3 eviction
low_watermark_ratio   = 0.7

[hicache]
prefetch_threshold              = 1024
prefetch_timeout_base           = 0.05
prefetch_timeout_per_ki_token   = 0.01
tp_lcm_size                     = 8               # if sharing namespace across heterogeneous TP
```

Equivalent env-var fallbacks (used when no extra-config provided): `MOONCAKE_TE_META_DATA_SERVER`, `MOONCAKE_GLOBAL_SEGMENT_SIZE`, `MOONCAKE_DEVICE`, `MOONCAKE_MASTER`.

### Gotchas

- KV tensors are NOT persistent — process exit drops them. For persistence, use 3FS or NIXL+S3.
- Memory fragmentation can fail allocations before reaching 100% usage. Tune `global_segment_size`.
- 0.5.6+ TTFT regression vs 0.5.5 — issue [#16797](https://github.com/sgl-project/sglang/issues/16797), still open across 0.5.6 → 0.5.10. Try `best_effort` prefetch to bypass and isolate.
- Multi-node runtime-attach uses the head node's hostname for all ranks — issue [#23457](https://github.com/sgl-project/sglang/issues/23457). Inject `MOONCAKE_LOCAL_HOSTNAME` per node before launch.
- Layer-first layout is auto-rewritten to `page_first*` (server_args.py:3148-3167). Check boot log.
- DeepSeek-V3.2 PD tool-call empty output — issue [#21176](https://github.com/sgl-project/sglang/issues/21176) (v0.5.9). Pin v0.5.10+.

## `hf3fs`

DeepSeek 3FS distributed filesystem. The LMSYS blog's flagship reference (8× H20-3e + DeepSeek-R1 + 65,536-token context). Hybrid model support landing in v0.5.11 (PR #23241 merged 2026-04-24).

### Install

```bash
# 3FS deployment is operator-managed (helm chart, Mountpoint or usrbio).
# Client lib build for ubuntu24.04 added in PR #15230.
pip install -e "git+https://github.com/sgl-project/sglang.git#subdirectory=sgl-kernel/3fs-client"
mount /mnt/3fs   # via the cluster's mount setup
```

### Recipe

```bash
--hicache-storage-backend hf3fs \
--hicache-mem-layout page_first_direct \
--hicache-io-backend direct \
--hicache-storage-backend-extra-config '{"mount_path": "/mnt/3fs/sglang", "use_usrbio": true}'
```

`use_usrbio: true` selects the fast user-space I/O path. `false` uses POSIX through the mount.

### Gotchas

- Hybrid Mamba/DSA support landing in v0.5.11 only. Pre-v0.5.11 fails with `ValueError: HiRadixCache only supports MHA and MLA yet` on Qwen3-Next / Qwen3.5 / DeepSeek-V3.2.
- `/flush_cache` times out under TP=2 — issue [#20499](https://github.com/sgl-project/sglang/issues/20499).

## `nixl`

NVIDIA NIXL transfer library. Wraps POSIX, 3FS, GDS, GDS_MT, S3-OBJ. Auto-priority `3FS > POSIX > GDS_MT > GDS > OBJ`. Best fit for NVIDIA Dynamo / GB200 / KVBM stacks.

### Install

```bash
pip install nixl-cu12        # or nixl-cu13 for CUDA 13
# requires NIXL >= 0.4
```

For NIXL deep-dive (UCX_TLS, GDS, libfabric, plugin authoring, telemetry, agent API), see the dedicated **`nvidia-nixl`** skill.

### Recipe — config file (recommended for prod)

```bash
--hicache-storage-backend nixl \
--hicache-mem-layout page_first_direct \
--hicache-io-backend direct \
--hicache-storage-backend-extra-config '@/etc/sglang/nixl.toml'
```

```toml
# /etc/sglang/nixl.toml
[nixl]
plugin_priority = ["3FS", "POSIX", "GDS_MT", "GDS", "OBJ"]
storage_dir     = "/mnt/3fs/sglang-nixl"   # for POSIX / 3FS plugins

[nixl.gds]
io_threads = 16
buffer_mb  = 256

[nixl.obj]
endpoint   = "https://s3.example.com"
bucket     = "kv-cache"
region     = "us-east-1"
```

### Recipe — quick env-var path

```bash
SGLANG_HICACHE_NIXL_BACKEND_PLUGIN_TYPE=POSIX \
SGLANG_HICACHE_NIXL_BACKEND_STORAGE_DIR=/var/cache/sglang \
python -m sglang.launch_server ... --hicache-storage-backend nixl
```

### Gotchas

- `page_first_direct` enables zero-copy automatically when the layout matches (hicache_nixl.py:308-319). Without it, NIXL falls back to a buffered path with ~30% throughput hit.
- Use `@config.toml` for prod — flags don't fit on one line.

## `aibrix`

ByteDance AIBrix KVCache offloading framework. Cross-engine reuse with vLLM. PrisKV variant not yet open-source.

### Install

```bash
pip install aibrix-kvcache
# AIBrix Infinistore daemon (deployable via aibrix Helm chart).
```

### Recipe

```bash
--hicache-storage-backend aibrix \
--hicache-storage-backend-extra-config '{"AIBRIX_KV_CACHE_OL_INFINISTORE_ENDPOINT":"infinistore-master:50051"}'
```

Configurable via `AIBRIX_KV_CACHE_OL_*` env vars (see `python/sglang/srt/mem_cache/storage/aibrix_kvcache/README.md`).

## `eic`, `simm`, `dynamic`

- **`eic`** — Elastic Instant Cache (Volcengine). Closed-source SDK. Use only on volcengine cloud.
- **`simm`** — Scitix SiMM (RDMA distributed memory pool). Requires cluster-manager + data-server services (`SIMM_CLUSTER_MANAGER` env var). Added in PR #18016 (v0.5.10rc0).
- **`dynamic`** — User-supplied class via `module_path` + `class_name` extra-config keys. Add `interface_v1: 1` to opt into the zero-copy v1 path:
  ```bash
  --hicache-storage-backend-extra-config '{"module_path":"my_pkg.kv","class_name":"MyKV","interface_v1":1}'
  ```
  Subclass `HiCacheStorage` (`python/sglang/srt/mem_cache/hicache_storage.py:98`).

## `lmcache` — alternative path, not a backend

`--enable-lmcache` swaps `HiRadixCache` for `LMCRadixCache`. Different stack:

- Cannot coexist with `--enable-hierarchical-cache`.
- Inherits LMCache's hybrid-attention bug ([LMCache #3106](https://github.com/LMCache/LMCache/issues/3106)) — broken on Gemma-4 / Qwen3.5 / Qwen3.6 / gpt-oss / Llama-4.
- Useful when standardised on LMCache for vLLM/SGLang sharing OR migrating an LMCache deploy to SGLang piecewise.

## `file` — DEV ONLY

Pure Python, one `.bin` per (key, tp_rank) pair. Per-rank suffix `_{model}_{tp_rank}_{tp_size}` (hicache_storage.py:294-298).

```bash
SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR=/tmp/hicache \
python -m sglang.launch_server ... --hicache-storage-backend file
```

**Issue [#21880](https://github.com/sgl-project/sglang/issues/21880) — extremely slow in containers.** Prefetch path dominates wall-time even with all data warm in CPU. Use this for unit tests and reproducing bugs, never production.
