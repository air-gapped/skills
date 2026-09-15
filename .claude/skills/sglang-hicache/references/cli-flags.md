# HiCache CLI flags

All defaults from `python/sglang/srt/server_args.py`. **The normalisation moved:** `_handle_hicache()` no longer exists — as of PR #38047 (merged 2026-09-06, after v0.5.19) the `--hicache-*` field declarations live in `python/sglang/srt/arg_groups/fields/memory.py` and the logic in `python/sglang/srt/arg_groups/hicache_hook.py::handle_hicache()`. Grep the symbol, not a line range; this file's ranges predate the move.

## Master switch

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--enable-hierarchical-cache` | flag | `False` | Required to activate any of the flags below. Mutually exclusive with `--disable-radix-cache` (asserts at `server_args.py:3825`) |
| `--enable-lmcache` | flag | `False` | Use LMCache instead of HiCache. Cannot coexist with `--enable-hierarchical-cache` |

## Sizing

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--hicache-ratio` | float | `2.0` | L2 size = `ratio × L1 size`. **Must be > 1** (host pool must exceed device pool) |
| `--hicache-size` | int | `0` | L2 size in **GB per rank**. When > 0, overrides `--hicache-ratio`. **NOT total** — `--hicache-size 30 --tp 8` allocates 240 GB total |

## Write / IO / layout

| Flag | Type | Default | Valid values |
|---|---|---|---|
| `--hicache-write-policy` | enum | `write_through` | `write_through`, `write_through_selective`, `write_back` |
| `--hicache-io-backend` | enum | `kernel` | `direct`, `kernel`, `kernel_ascend` |
| `--hicache-mem-layout` | enum | `layer_first` | `layer_first`, `page_first`, `page_first_direct`, `page_first_kv_split`, `page_head` |

`page_head` was added in v0.5.6 for heterogeneous TP. `page_first_kv_split` separates K and V tiles for backends that prefer split storage. `page_first_direct` is the only layout that enables zero-copy with `direct` IO.

## Storage backend (L3)

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--hicache-storage-backend` | enum | `None` | `file`, `mooncake`, `hf3fs`, `nixl`, `aibrix`, `eic`, `simm`, `dynamic`. Omit to skip L3. |
| `--hicache-storage-prefetch-policy` | enum | `best_effort` | `best_effort`, `wait_complete`, `timeout`. Production: `timeout` |
| `--hicache-storage-backend-extra-config` | str | `None` | JSON inline OR `@/path/to/file.{json,yaml,toml}` |

`extra_config` keys parsed by `HiRadixCache._parse_storage_backend_extra_config()`:

| Key | Type | What |
|---|---|---|
| `prefetch_threshold` | int | Min L3 prefetch size in tokens. Floored to `page_size` (cache_controller.py:461). Default 256 |
| `prefetch_timeout_base` | float | Constant component of timeout (s) |
| `prefetch_timeout_per_ki_token` | float | Per-1024-token component of timeout. `timeout = base + (tokens / 1024) × per_ki_token` |
| `hicache_storage_pass_prefix_keys` | bool | Pass leading prefix keys to backend (some backends index by full prefix) |
| `tp_lcm_size` | int | Heterogeneous TP — the LCM of TP sizes that share this L3 namespace |
| `master_server_address` | str | Mooncake-only — RDMA master daemon |
| Backend-specific TOML sections | object | NIXL backend TOML, AIBrix `aibrix.kvcache` block, etc. |

## Related flags that interact with HiCache

| Flag | When it matters |
|---|---|
| `--page-size N` | Default 1 (CUDA), 64 (MUSA). Recommended 64 for hicache + L3. DSA forces 64. SSM `no_buffer` forces 1 (incompatible with `trtllm_mha`). SSM `extra_buffer` requires `mamba_track_interval % page_size == 0` |
| `--mem-fraction-static` | Lower (e.g. 0.85) to leave room for the L1 KV pool that L2 will mirror |
| `--disable-radix-cache` | Mutually exclusive with `--enable-hierarchical-cache` — asserts at startup |
| `--disaggregation-decode-enable-offload-kvcache` | Only valid when `--hicache-storage-backend` is set (server_args.py:3836) |
| `--enable-cache-report --enable-metrics` | Required to see per-tier cache-hit metrics |
| `--admin-api-key <KEY>` | Required for `/clear_hicache_storage_backend` and recommended for `/hicache/storage-backend` PUT/DELETE (server_args.py:4890) |
| `--mamba-scheduler-strategy {extra_buffer, no_buffer}` | Required for SSM hybrid models with hicache. `extra_buffer` is the production choice |
| `--max-mamba-cache-size N` | Required for SSM hybrid models with hicache; sizes the Mamba state pool |

## Auto-rewrite normalisation rules — silent flips, watch the boot log

`arg_groups/hicache_hook.py::handle_hicache()` (formerly `server_args.py:_handle_hicache`) enforces compatibility, never errors, just rewrites and logs WARNING. The two rewrite rules are `resolve_layout_io_compatibility()` and `resolve_storage_layout_compatibility()`. If benchmark numbers don't match the recipe, scan the boot log for these.

### Layout × IO compatibility (`_resolve_layout_io_compatibility`, server_args.py:3129-3146)

```
page_first_direct + io=kernel    → io rewritten to direct
page_first        + io=direct    → layout rewritten to page_first_direct
```

Log line: `"switching to {new_layout} layout for {io_backend} io backend"`.

### Storage × layout compatibility (`_resolve_storage_layout_compatibility`, server_args.py:3148-3167)

Mooncake requires `page_first*`. With Mooncake + `layer_first`:

```
io=direct     → layout becomes page_first_direct
io=kernel     → layout becomes page_first
io=otherwise  → layout unchanged (factory may still error)
```

Log: `"switching to {new_layout} layout for {io_backend} io backend"`.

### FA3 decode backend (`server_args.py:3170-3186`)

If FA3 decode kernel is selected (or auto-selected) and `--hicache-io-backend != kernel`:

```
io rewritten to direct  (yes, "direct" — see lines 3170-3181)
```

Log: `"FlashAttention3 decode backend is not compatible with hierarchical cache. Setting hicache_io_backend to vanilla I/O, which may lead to suboptimal performance with small page sizes."`

### Hybrid SWA model handling

**RESOLVED for the three named architectures — re-verified in source 2026-09-15 at tag v0.5.19.**

The routing question is now decided by `is_hybrid_swa_model()` in
`python/sglang/srt/configs/model_config.py`, whose `hybrid_swa_archs` allowlist
**includes all three**: `Llama4ForConditionalGeneration`, `GptOssForCausalLM`
(via `SWA_SINK_ARCHS`, alongside `GraniteSWAForCausalLM` and
`GraniteMoeSWAForCausalLM`) and `Gemma4ForCausalLM` / `Gemma4ForConditionalGeneration`
/ `Gemma4UnifiedForConditionalGeneration`. Also on it: the DeepSeek-V4 family,
MiMo-V2, Step3p5 / Step3p7, Laguna (only when it actually has a sliding window),
Mellum, MuseGlimmer, Inkling and UnlimitedOCR. A model on this list is routed
through `UnifiedRadixCache` with the SWA component, so its sliding-window layers
are cached and evicted as SWA rather than as full attention. PR #27759 made that
the default for hybrid models in v0.5.13, and **v0.5.19 made the unified radix
tree the default for every model, not just hybrid ones**. Do not tell an operator
to pass `--disable-hybrid-swa-memory` or avoid hicache for these three.

**The failure class has not gone away, it has narrowed.** The guard is an
allowlist plus one opt-in escape hatch (`hf_text_config.is_hybrid_swa`). An
architecture that is genuinely SWA but appears in neither returns a plain
`False` — no assertion, no error — and its SWA layers are treated as full
attention exactly as before. That is the shape to check for a new, custom or
vendor-forked architecture, rather than for the three models above.

### Decode-side offload validation

`server_args.py:3825-3843`:

- `--enable-hierarchical-cache + --disable-radix-cache` → assertion error
- `--disaggregation-decode-enable-offload-kvcache` without `--hicache-storage-backend` → assertion error
- (some configurations) → `enable_hierarchical_cache = False` is silently set at server_args.py:3983-3987 if a parallelism mode is incompatible

## Runtime attach/detach HTTP API

For switching the L3 backend without engine restart. Documented in `docs/advanced_features/hicache_storage_runtime_attach_detach.md`.

```http
GET  /hicache/storage-backend                                  → current config
PUT  /hicache/storage-backend                                  → attach / swap
     Body: { "hicache_storage_backend": "...",
             "hicache_storage_backend_extra_config_json": "...",
             "hicache_storage_prefetch_policy": "..." }
DELETE /hicache/storage-backend                                → detach
```

Constraints:

- Engine must pass `is_fully_idle()` — no running, queued, chunked-prefill, PD-bootstrap, or DLLM-staging requests. Returns HTTP 400 otherwise.
- With `dp_size > 1`, success is AND-aggregated across DP ranks. **Partial-success has no automatic rollback** — drain traffic before switching.
- Set `--admin-api-key` for production; without it the endpoints are open.

## Quick verification

After boot, confirm hicache wired up:

```bash
# Boot log should contain:
#   "Hierarchical cache enabled. ratio=2.0 size=0"
#   if storage backend: "Storage backend: mooncake (page_first_direct, direct IO)"
#   if any auto-rewrite: "switching to ... layout for ... io backend"

# Per-tier hit rates via Prometheus:
curl -s http://localhost:30000/metrics | grep -E 'sglang_(num_used_tokens|cache_hit|hicache)'
```

Look for: `sglang_hicache_cpu_hit_count`, `sglang_hicache_storage_hit_count`, `sglang_cache_hit_rate`. Per-tier hit breakdown was added in v0.5.9 (PR #17648).
