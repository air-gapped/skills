# LMCache MP — L2 storage adapters

L1 (CPU DRAM) is the always-on tier. L2 is **optional persistence** — adapters configured via `--l2-adapter` JSON. Keys flow L1 → L2 via `StoreController` (async) and L2 → L1 via `PrefetchController` on miss.

You can stack multiple `--l2-adapter` flags for a cascade (e.g. fast SSD + larger NVMe). Adapters are queried in declaration order.

## Adapter types

### `nixl_store` — pre-allocated NIXL backend (production default)

Uses NIXL (NVIDIA Interconnect Library) for high-performance storage I/O. Backends:

| Backend | Description |
|---|---|
| `POSIX` | Standard POSIX file I/O. Any filesystem. No direct I/O. |
| `GDS` | NVIDIA GPU Direct Storage. Direct GPU↔storage transfers bypass CPU. **Requires NVMe SSDs with GDS support.** |
| `GDS_MT` | Multi-threaded GDS variant for higher throughput. |
| `HF3FS` | Distributed/networked filesystem. |
| `OBJ` | Object store. No `file_path` required. |

Config examples:

```bash
# POSIX
--l2-adapter '{"type":"nixl_store","backend":"POSIX",
               "backend_params":{"file_path":"/data/lmcache/l2","use_direct_io":"false"},
               "pool_size":64}'

# GDS (requires GDS-capable NVMe)
--l2-adapter '{"type":"nixl_store","backend":"GDS",
               "backend_params":{"file_path":"/data/nvme/lmcache","use_direct_io":"true"},
               "pool_size":128}'
```

`pool_size` is the number of pre-allocated storage descriptors. Tune up for higher concurrency.

### `nixl_store_dynamic` — persist + recover

Same backends, but opens/closes files per operation rather than pre-allocating. Two big differences from `nixl_store`:

- **Persist/recover** — cached KV survives LMCache server restarts (`persist_enabled` defaults to `true`).
- **No fd limits** — files open and close per transfer, so cache can grow beyond OS open-fd limits.

Object backend (`OBJ`) is **NOT** supported in dynamic mode.

```bash
# Dynamic POSIX with eviction
--l2-adapter '{"type":"nixl_store_dynamic","backend":"POSIX",
               "backend_params":{"file_path":"/data/lmcache/l2",
                                 "use_direct_io":"false",
                                 "max_capacity_gb":"50"},
               "eviction":{"eviction_policy":"LRU",
                           "trigger_watermark":0.9,
                           "eviction_ratio":0.1}}'
```

`max_capacity_gb` is **required** when using dynamic mode — the eviction controller needs it to compute usage. The adapter rejects stores when the limit is reached.

On startup, the in-memory index is empty. Lookups miss → fall through to disk → if the deterministic file exists, treated as a hit and the in-memory index populates lazily.

### `fs` — pure file-system adapter (no NIXL needed)

Uses `aiofiles` for async I/O. Each KV object is one `.data` file, name encoding the full ObjectKey. Works on any POSIX filesystem.

```bash
--l2-adapter '{"type":"fs","base_path":"/data/lmcache/l2"}'

# With temp-dir for atomic writes
--l2-adapter '{"type":"fs","base_path":"/data/lmcache/l2","relative_tmp_dir":".tmp"}'

# With O_DIRECT bypass of page cache
--l2-adapter '{"type":"fs","base_path":"/data/lmcache/l2","use_odirect":true}'
```

Use this when:
- You don't have NIXL installed (e.g. arm64 image where NIXL build is finicky).
- You're testing without real storage hardware.
- You want a simple debugging adapter.

**Limitations**: `delete` and `get_usage` are no-ops, so eviction is not supported. Don't use as the only adapter under sustained load.

### `mooncake_store` — Mooncake native connector (RDMA-capable)

L2 backed by the native C++ Mooncake Store connector. Useful for RDMA-grade distributed KV cache.

**Build requirement**: not built by default. Set `BUILD_MOONCAKE=1`:

```bash
BUILD_MOONCAKE=1 pip install -e . --verbose

# If headers aren't in /usr/local/include:
BUILD_MOONCAKE=1 \
  MOONCAKE_INCLUDE_DIR=/path/to/mooncake/include \
  MOONCAKE_LIB_DIR=/path/to/mooncake/lib \
  pip install -e . --verbose
```

Config example (TCP):

```bash
--l2-adapter '{
  "type":"mooncake_store",
  "num_workers":4,
  "local_hostname":"node01",
  "metadata_server":"http://localhost:8080/metadata",
  "master_server_address":"localhost:50051",
  "protocol":"tcp",
  "local_buffer_size":"3221225472",
  "global_segment_size":"3221225472"
}'
```

RDMA notes:
- `protocol:"rdma"` requires a valid LMCache L1 memory descriptor. Set `--no-l1-use-lazy` so L1 buffer is fully allocated before Mooncake registers it.
- `protocol:"tcp"` does not require L1 preregistration.
- If RDMA init fails, verify L1 memory is enabled and the descriptor has non-zero pointer + size.

**Limitation**: Mooncake adapter does not support eviction (it's a native connector adapter).

For full Mooncake setup (master service, metadata server), see https://github.com/kvcache-ai/Mooncake.

### `s3` — S3-compatible object store

Stores KV objects as S3 objects via AWS Common Runtime (CRT). Works with AWS S3, S3 Express One Zone, MinIO, Ceph RGW, etc.

```bash
# AWS S3 with default credentials
--l2-adapter '{"type":"s3","s3_endpoint":"s3://my-bucket","s3_region":"us-west-2"}'

# Local MinIO over plain HTTP
--l2-adapter '{"type":"s3","s3_endpoint":"minio.local:9000","s3_region":"us-east-1",
               "disable_tls":true,
               "aws_access_key_id":"minio","aws_secret_access_key":"minio123"}'
```

Eviction supported via `max_capacity_gb` (default 0 = aggregate eviction disabled).

### `mock` — for testing

```bash
--l2-adapter '{"type":"mock","max_size_gb":256,"mock_bandwidth_gb":10}'
```

## Cascade: multiple L2 adapters

Repeat `--l2-adapter` for cascade. `StoreController` pushes to **all** configured adapters; `PrefetchController` queries them **in order**.

```bash
# Fast SSD (POSIX) + large NVMe (GDS)
--l2-adapter '{"type":"nixl_store","backend":"POSIX",
               "backend_params":{"file_path":"/data/ssd/l2","use_direct_io":"false"},
               "pool_size":64}' \
--l2-adapter '{"type":"nixl_store","backend":"GDS",
               "backend_params":{"file_path":"/data/nvme/l2","use_direct_io":"true"},
               "pool_size":128}'
```

## Store and prefetch policies

```bash
--l2-store-policy default      # store all keys to all adapters; never delete from L1
--l2-store-policy skip_l1      # store all keys to all adapters; immediately delete from L1
                               # (pair with --eviction-policy noop to skip LRU overhead)

--l2-prefetch-policy default   # first (lowest-indexed) adapter that has the key wins;
                               # prefetched keys are temporary (deleted after read)
--l2-prefetch-policy retain    # same load plan as default; prefetched keys retained in L1
                               # (good for shared system-prompt chunks)
```

`--l2-prefetch-max-in-flight 8` (default) caps concurrent prefetch ops. Higher = more L2→L1 throughput, more L1 memory pressure.

## Buffer-only mode (L1 is just a write buffer)

```bash
--eviction-policy noop \
--l2-store-policy skip_l1 \
--l2-prefetch-policy default
```

L1 holds keys only long enough to write them to L2, then evicts immediately. Saves CPU/memory but loses L1's hot-cache benefit.

## Eviction

L1 eviction (CLI):

```bash
--eviction-policy LRU \
--eviction-trigger-watermark 0.8 \
--eviction-ratio 0.2
```

L2 eviction is **per-adapter**. Add an `"eviction"` sub-object to the adapter's `--l2-adapter` JSON:

```bash
--l2-adapter '{
  "type":"nixl_store",
  "backend":"POSIX",
  "backend_params":{"file_path":"/data/lmcache/l2","use_direct_io":"false"},
  "pool_size":128,
  "eviction":{"eviction_policy":"LRU","trigger_watermark":0.8,"eviction_ratio":0.2}
}'
```

L2 eviction support per adapter type:

| Adapter | L2 eviction |
|---|---|
| `nixl_store` | Full. `delete` frees pool slots; pinned keys skipped, retried next cycle. |
| `nixl_store_dynamic` | Full. `delete` removes data files; `get_usage` is byte-based. |
| `mock` | Full. |
| `s3` | Yes if `max_capacity_gb > 0`. `delete` removes objects from bucket. |
| `mooncake_store` | **No**. |
| `fs` | **No** (`delete` and `get_usage` are no-ops). |

## Verifying L2 is active

`LMCACHE_LOG_LEVEL=DEBUG` in the LMCache server env. Look for:

```
LMCache DEBUG: Submitted store task ...
LMCache DEBUG: L2 store task N completed ...
LMCache DEBUG: Prefetch request submitted: X total keys, Y L1 prefix hits, Z remaining for L2
```

If you don't see L2 activity, your L1 is large enough that nothing has been evicted yet (good — bigger L1 means fewer L2 round-trips). To force activity, deliberately exceed L1 capacity in a benchmark; see `vllm-caching` for the `vllm bench serve --dataset-name prefix_repetition` recipe.
