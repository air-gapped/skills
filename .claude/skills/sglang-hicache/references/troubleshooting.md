# Troubleshooting

Symptom → diagnosis → fix. Recheck via `gh issue view <N> --repo sgl-project/sglang` before quoting.

## Engine fails to start

### `ValueError: HiRadixCache only supports MHA, MLA, and NSA (DSA) models`

- **Cause**: SWA-class model (Gemma 3-4, Mistral, Llama-4 SWA layers) on v0.5.10 or earlier.
- **Fix**: Disable hicache on this arch. Upgrade path is v0.5.11 once PR [#23391](https://github.com/sgl-project/sglang/pull/23391) merges (still OPEN as of 2026-04-25).

### `AssertionError: enable_hierarchical_cache and disable_radix_cache are mutually exclusive`

- **Cause**: Both flags passed.
- **Fix**: Remove `--disable-radix-cache`. HiCache is itself a radix cache.

### `AssertionError: disaggregation-decode-enable-offload-kvcache is only supported when hicache-storage-backend is provided`

- **Cause**: PD decode-offload requires L3.
- **Fix**: Add `--hicache-storage-backend mooncake` (or another).

### `RuntimeError: hicache_ratio must be > 1`

- **Cause**: `--hicache-ratio 1` or less.
- **Fix**: Use `≥ 2` for production. Host pool must exceed device pool.

### `OOM: failed to allocate pinned host memory`

- **Cause**: `--hicache-size N` is per-rank — `--hicache-size 100 --tp 8` = 800 GB total. Host doesn't have it pinned-available.
- **Fix**: Either reduce `--hicache-size`, ensure `MEMLOCK` ulimit is high (`ulimit -l unlimited` or container caps), or switch to `--hicache-ratio` which auto-sizes from L1.

## Hits look low or hicache "doesn't help"

### Boot log shows auto-rewrite warnings

```
[WARNING] switching to page_first_direct layout for direct io backend
```

- **Cause**: layout × IO compatibility normalisation kicked in.
- **Action**: Not necessarily wrong, but verify it's the intended layout. The warning is the only signal.

### `sglang_cache_hit_rate` stays low

- **Cause options** (in order):
  1. **No prefix locality in workload** — non-agentic, non-RAG traffic has low reuse. `cat ~/sglang.log | grep prefix_cache` will show low matches even before hicache.
  2. **Cold cache** — first N requests pay full prefill cost. Measure steady-state.
  3. **Hicache ratio too small** — `--hicache-ratio 1.2` leaves only ~16% L1 size for prefetched-but-not-yet-used pages. Production: `≥ 2`.
  4. **L3 prefetch policy = best_effort** — returns L1+L2 hit immediately, ignores incomplete L3. Try `timeout` to actually wait for L3.
  5. **Storage backend slow** — Mooncake 0.5.6+ regression (#16797), file backend always slow (#21880). Check `sglang_hicache_storage_get_duration_seconds` histogram.

### TTFT regressed after enabling hicache

- **Cause**: Mooncake 0.5.6+ regression vs 0.5.5 — issue [#16797](https://github.com/sgl-project/sglang/issues/16797). Or `wait_complete` prefetch policy (blocks request until L3 lands).
- **Fix**: Try `--hicache-storage-prefetch-policy best_effort` to bypass L3 wait. If regression persists, it's the Mooncake bug — pin `mooncake-transfer-engine 0.3.10.post1` and consider downgrading to v0.5.5 until fix lands.

## Crashes / IMA at runtime

### `AssertionError: parent does not have child key` in `evict_host`

- **Cause**: Issue [#19212](https://github.com/sgl-project/sglang/issues/19212). Radix tree mutated during heap iteration in `write_back` policy.
- **Fix**: `--hicache-write-policy write_through` (the default). `write_back` is open-bug as of 2026-04-25.

### `RuntimeError: Expected all tensors to be on the same device` in `mamba_pool_host.free`

- **Cause**: Issue [#23429](https://github.com/sgl-project/sglang/issues/23429). Mamba + write_back + `_evict_host_leaf` race on Qwen3.6-35B-A3B-FP8.
- **Fix**: `--hicache-write-policy write_through`. No other workaround.

### Shape-mismatch crash under PP>1 within minutes/hours

- **Cause**: Issue [#22607](https://github.com/sgl-project/sglang/issues/22607). Async prefetch + per-rank LRU diverge.
- **Fix**: `--pp-size 1` until fixes (#22759, #22878) land in v0.5.11.

### Same crash with `Indexer with GLM5 pp2`

- **Cause**: Issue [#20529](https://github.com/sgl-project/sglang/issues/20529). Same root cause as #22607, surfaces around request 700-800.
- **Fix**: Drop to `--pp-size 1` for hicache + DSA stacks.

### `CUDA_EXCEPTION_4: Warp Illegal Instruction` in FlashAttnFwdSm90

- **Cause**: Issue [#19737](https://github.com/sgl-project/sglang/issues/19737). PyPI sgl-kernel 0.3.21 + FA3 + MoE + SXM (Hopper SXM, GB200).
- **Fix**: Install `sgl-kernel` from the GitHub Release artifact (built with `-DCUTLASS_ENABLE_GDC_FOR_SM90`), not PyPI. Or apply 3-line patch from the issue body to `cache_controller.py`.

## Mooncake-specific

### `Connection refused` / `Peer nic not found` after multi-node runtime-attach

- **Cause**: Issue [#23457](https://github.com/sgl-project/sglang/issues/23457). `local_hostname` falls back to `"localhost"` for all ranks; head node value broadcast to workers.
- **Fix**: Inject `MOONCAKE_LOCAL_HOSTNAME=$(hostname)` per node before launch. Use static `--hicache-storage-backend mooncake` startup flag, not runtime attach, until #23457 is fixed.

### `segfault in cache_controller.backup_thread_func` on H20 + GLM-5 DSA

- **Cause**: Issue [#22757](https://github.com/sgl-project/sglang/issues/22757). DSA + Mooncake L3 on specific hardware.
- **Fix**: No clean workaround. Disable hicache on GLM-5 DSA + H20 stack until fix.

## File-backend specific

### TTFT regresses massively despite all data in CPU

- **Cause**: Issue [#21880](https://github.com/sgl-project/sglang/issues/21880). Prefetch path dominates wall-time even with file backend warm.
- **Fix**: Don't use `file` in production. Use `mooncake` / `hf3fs` / `nixl`.

## Validation / debug commands

```bash
# Full boot log scan (use after engine starts)
journalctl -u sglang | grep -iE '(hicache|warning|error)'

# Per-tier hit rates (sample 10s)
for i in {1..10}; do
  curl -s http://localhost:30000/metrics | \
    grep -E 'sglang_(cache_hit_rate|hicache_(cpu|storage)_hit_count)'
  sleep 1
done

# Verify backend wired up
curl http://localhost:30000/hicache/storage-backend
# {"hicache_storage_backend":"mooncake","hicache_storage_backend_extra_config":"...","hicache_storage_prefetch_policy":"timeout"}

# Force-flush all tiers (debug only — drops the cache)
curl -X POST http://localhost:30000/flush_cache \
  -H "Authorization: Bearer $ADMIN_KEY"
```

## When the user says "I migrated from vLLM and hicache numbers are worse"

Common causes in order:

1. **Sizing in wrong units** — vLLM `--kv-offloading-size` is total across TP, SGLang `--hicache-size` is **per rank**. `100 GB → 100 / TP per rank`. See `references/migration-from-vllm-caching.md`.
2. **Reasoning-parser missing** — SGLang reports `output_token_count` differently if `reasoning_content` is folded in. Check whether the comparison was apples-to-apples (e.g. `--reasoning-parser deepseek-r1` for R1 family on both sides).
3. **Page size mismatch** — vLLM default block 16, SGLang default page 1 on CUDA. Recommended 64 for hicache. The first hit rate from a page-size-1 baseline can look worse than vLLM's 16 default until set to 64.
4. **Workload doesn't have prefix locality** — agentic / RAG workloads do; raw chat usually doesn't. Hicache won't help on the latter.
5. **Storage prefetch policy default is `best_effort`** — switch to `timeout` to wait for L3 hits.
