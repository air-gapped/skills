# HiCache architecture

Three-tier hierarchical KV prefix cache addressed through one radix tree.

## Tiers

| Tier | Substrate | Scope | Class |
|---|---|---|---|
| **L1** | GPU HBM (per-rank) | private to engine | regular `MHATokenToKVPool` / `MLATokenToKVPool` |
| **L2** | pinned CPU DRAM (per-rank) | private to engine | `MHATokenToKVPoolHost` / `MLATokenToKVPoolHost` (`memory_pool_host.py`) |
| **L3** | distributed / disk | optionally **shared cross-cluster** | `HiCacheStorage` ABC + concrete backend |

Sized via `--hicache-ratio` (L2 = ratio × L1) **or** `--hicache-size <GB>` per rank.

## Core classes

`python/sglang/srt/mem_cache/`:

- **`RadixCache`** (radix_cache.py) — base prefix tree (RadixAttention).
- **`HiRadixCache(RadixCache)`** (hiradix_cache.py:66) — adds host pool + L3 backend, owns the controller and per-request prefetch tracking. The "HiRadixTree" of the design doc is implemented here as RadixCache + extra `host_value` / `hash_value` fields on each `TreeNode`.
- **`HiMambaRadixCache(MambaRadixCache)`** (hi_mamba_radix_cache.py:88) — hicache variant for hybrid Mamba/SSM models (Qwen3-Next, Qwen3.5, MiniMax-M2 family). Uses `HybridLinearKVPool` + `HybridReqToTokenPool`. Selected at scheduler.py:835-842 when `is_hybrid_ssm` is true.
- **`HiCacheController`** (managers/cache_controller.py:247) — owns L1↔L2 transfer streams (`write_stream`, `load_stream`) and the L2↔L3 prefetch + backup daemon threads (cache_controller.py:348-362). Holds the `StorageBackendFactory`.
- **`HybridCacheController(HiCacheController)`** (mem_cache/hybrid_cache/hybrid_cache_controller.py:149) — extends controller for SSM + DSA (NSA indexer) pools. Adds Mamba state offload entries.
- **`HiCacheStorage(ABC)`** (hicache_storage.py:98) — the L3 contract: `get / set / exists / batch_*` plus zero-copy `batch_get_v1 / batch_set_v1 / batch_get_v2 / batch_set_v2` using `PoolTransfer` (hicache_storage.py:62-95) for KV + extras (Mamba SSM, DSA indexer).

Note: there is **no class literally named `HiRadixTree`** despite the design doc's terminology — search for `HiRadixCache` instead.

## Write paths

### L1 → L2 (host backup)

```
HiRadixCache.write_backup() (hiradix_cache.py:653)
  → HiCacheController.write()                              # enqueue CacheOperation
  → start_writing()                                        # CUDA events on write_stream
  → mem_pool_host.backup_from_device_all_layer()           # cache_controller.py:681-709
```

Async, event-acked. Triggered by L1 eviction (LRU `radix_eviction_policy`).

### L2 → L3 (storage backup)

```
HiRadixCache.write_backup_storage()  (hiradix_cache.py:688)
  → HiCacheController.write_storage()
  → background backup_thread: storage_backend.batch_set_*
```

Always async; daemon thread. Triggered by L2 eviction OR (in `write_through` mode) immediately after L1→L2.

### Write policies

`--hicache-write-policy`:

| Value | What happens on every L1 eviction |
|---|---|
| `write_through` (default) | Always backs up to L2 AND queues for L3. Highest hit rate, highest write bandwidth. |
| `write_through_selective` | Backs up only "promising" prefixes (heuristic on access count). Reduces write bandwidth at the cost of cold-set hits. |
| `write_back` | Defers backup until L1 must evict; only writes pages about to be lost. **OPEN BUG #19212 — crashes under load**. Avoid until fixed. |

## Read paths

### Storage → L2 prefetch

```
prefetch_thread (daemon)
  → poll prefetch_queue
  → storage_backend.batch_exists*   # check what's in L3
  → storage_backend.batch_get*      # async pull
```

Termination governed by `--hicache-storage-prefetch-policy`:

| Value | Behaviour |
|---|---|
| `best_effort` (default) | Issues prefetch requests, returns the L1+L2 hit immediately, ignores incomplete L3 hits for the current request |
| `wait_complete` | Blocks the request until all prefetched L3 pages land. Highest hit rate, worst tail TTFT |
| `timeout` | Waits up to `prefetch_timeout_base + page_count * prefetch_timeout_per_page`. **Recommended for production SLOs** |

`prefetch_timeout_per_page = page_size / 1024 * prefetch_timeout_per_ki_token` (hiradix_cache.py:211-213). Set both keys via `--hicache-storage-backend-extra-config`.

For TP > 1, `prefetch_tp_group` is a separate `gloo` group (cache_controller.py:478). HiCache uses `all_reduce(op=min)` to enforce the same hit length on every rank — the slowest rank's hit count wins, otherwise prefill batches get out-of-sync KV layouts (hicache_design.md:79-81).

### L2 → L1 (compute-transfer overlap)

```
HiCacheController.start_loading()
  → per-layer copy on load_stream
  → LayerLoadingEvent ring (cache_controller.py:51-97)
  ⇒ prefill compute layer N | load layer N+1 in parallel
```

This overlap is what makes the L2 hit a multi-second-saver instead of a wash. With `--hicache-io-backend kernel` (default), the per-layer copies run a CUDA kernel that explicitly co-issues with prefill. With `direct`, regular `cudaMemcpyAsync` is used — required for FA3 and Mooncake `direct` IO.

## Eviction

| Tier | Policy | Notes |
|---|---|---|
| **L1** | `--radix-eviction-policy` (LRU default) | Either triggers L2 backup (`write_through`) or just frees if already backed up |
| **L2** | "free pages whose contents are already replicated to L3" (cache_controller.py:795-799) | Only supported policy: `evict_host(host_indices, backup_only=True)` |
| **L3** | **delegated to backend** | Mooncake's `eviction_high_watermark_ratio`, 3FS's quotas, etc. HiCache does not evict L3 itself |

`prefetch_threshold` (default 256 tokens, hicache_design.md:46) is silently floored to `page_size` (cache_controller.py:461). The L2 capacity used for prefetch is `0.8 × (mem_pool_host.size − mem_pool_device.size)` (cache_controller.py:462-463). With `--hicache-ratio 1.2` only ~16% of L1 size is available for prefetched-but-not-yet-used pages — enough for spec-decode but chokes under multi-turn. Use ratio ≥ 2 in production.

## TP / PP / DP layout

| Parallelism | HiCache behaviour |
|---|---|
| TP > 1 | Per-rank L1 + L2 + L3 namespace. `prefetch_tp_group` synchronises hit length. Mooncake / 3FS / NIXL backends use `tp_lcm_size` extra-config key for heterogeneous TP support |
| PP > 1 | **Broken** — issue [#22607](https://github.com/sgl-project/sglang/issues/22607). Async prefetch + per-rank scheduler diverge under wall-clock LRU; host-tree shape mismatch crash |
| DP > 1 | Per-DP-rank state. Runtime attach/detach is AND-aggregated across DP ranks; partial-success has no automatic rollback (hicache_storage_runtime_attach_detach.md:50-65) |
| MLA models | Write-back optimisation: only **one** rank writes (LMSYS blog), since MLA KV is identical across TP ranks. MHA / GQA must split per-rank |
| MoE | Each routed expert's KV slice goes through the same path. PR [#19737](https://github.com/sgl-project/sglang/issues/19737) IMA on FA3 + MoE + SXM is unrelated to HiCache itself but breaks HiCache by extension |

## Key file paths

- `python/sglang/srt/mem_cache/hicache_storage.py` — `HiCacheStorage` ABC, `PoolTransfer`, `HiCacheFile`
- `python/sglang/srt/mem_cache/hiradix_cache.py` — `HiRadixCache`
- `python/sglang/srt/mem_cache/hi_mamba_radix_cache.py` — `HiMambaRadixCache`
- `python/sglang/srt/mem_cache/memory_pool_host.py` — host pool implementations
- `python/sglang/srt/mem_cache/hybrid_cache/hybrid_cache_controller.py` — `HybridCacheController`
- `python/sglang/srt/mem_cache/storage/backend_factory.py` — `StorageBackendFactory`
- `python/sglang/srt/managers/cache_controller.py` — `HiCacheController` + transfer streams + daemon threads
- `python/sglang/srt/managers/scheduler.py:755-890` — radix-cache class selection (which radix tree gets instantiated)
- `python/sglang/srt/server_args.py:5635-5733` — flag definitions
- `python/sglang/srt/server_args.py:3100-3200` — `_handle_hicache` normalisation
- `docs/advanced_features/hicache_design.md` — official design doc (read alongside this file)
