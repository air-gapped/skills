# Migrating from vLLM caching to SGLang HiCache

For operators with a vLLM/LMCache deploy hitting the 2026 hybrid-attention wall.

## When to consider migrating

The trigger is a hybrid-attention model — Gemma-4, Qwen3.5/3.6, gpt-oss, Llama-4 — where vLLM v0.19.1 + LMCache 0.4.4 fails to offload KV beyond HBM. Symptoms (verified 2026-04-25 on Verda 2× H100 SXM5 80GB serving Qwen/Qwen3.6-27B-FP8):

- LMCacheConnectorV1 startup `ValueError: Hybrid KV cache manager is disabled but failed to convert KV cache specs to one unified type` — [LMCache #3106](https://github.com/LMCache/LMCache/issues/3106).
- SimpleCPUOffloadConnector boots but `AssertionError: External KV connector is not verified yet` on first long-context request — [vLLM #39702](https://github.com/vllm-project/vllm/issues/39702).
- NixlConnector kv_role=kv_both serves chat correctly but `vllm:nixl_xfer_time_seconds_count = 0` after a same-prefix request to peer — no auto-discovery in symmetric mode (designed for proxy-orchestrated 1P1D).
- Native `--kv-offloading-size` fails-to-start on Qwen3.5 family per [vLLM #36463](https://github.com/vllm-project/vllm/issues/36463).

For non-hybrid models (Llama-3, DeepSeek-R1, Qwen2.5, Mistral), vLLM caching works — don't migrate just to migrate.

## Sizing math — the most common bug

| vLLM | SGLang HiCache | Direction |
|---|---|---|
| `--kv-offloading-size N` | `--hicache-size N` × `1/TP` per rank, OR `--hicache-ratio R` | **vLLM total → SGLang per-rank** — divide by TP |
| `--cpu-offload-gb N` (per GPU) | `--hicache-size N` per rank | **vLLM per-GPU → SGLang per-rank** — same units |
| `LMCACHE_MAX_LOCAL_CPU_SIZE` (per rank) | `--hicache-size` | per-rank in both — same units |

**Worked example.** vLLM had `--kv-offloading-size 1600 --tp 8` (1600 GB total = 200 GB/rank). On SGLang: `--hicache-size 200 --tp 8` (200 GB/rank = 1600 GB total). NOT `--hicache-size 1600`.

This is one of two places SGLang's convention is different from vLLM (the other being page-size default 1 on CUDA vs vLLM's block-size 16).

## Connector / backend mapping

| vLLM | SGLang HiCache equivalent | Notes |
|---|---|---|
| Native CPU offload (`--kv-offloading-size`) | `--enable-hierarchical-cache --hicache-ratio 2` | SGLang's L1+L2 path. No L3 needed for single-node start |
| `--kv-offloading-backend lmcache` | `--enable-hierarchical-cache --hicache-storage-backend file/dynamic` | LMCache itself can also be wired as `--enable-lmcache` (see below) |
| LMCache + `LMCACHE_LOCAL_DISK` (NVMe) | `--hicache-storage-backend nixl` w/ NIXL POSIX plugin | NIXL hybrid support depends on plugin |
| MooncakeConnector | `--hicache-storage-backend mooncake` | SGLang has richer policy controls |
| NixlConnector kv_both | not a direct equivalent | SGLang doesn't ship symmetric P2P for prefix sharing |
| NixlConnector 1P1D | `--disaggregation-mode prefill` / `decode` + `--hicache-storage-backend nixl` | SGLang PD-disagg natively supported |
| MultiConnector composition | not directly — pick one L3 | SGLang assumes one L3 per engine; use `--enable-lmcache` if mixing with vLLM |

## Side-by-side: vLLM CPU offload → SGLang L1+L2

**vLLM (broken on hybrid):**

```bash
vllm serve Qwen/Qwen3.5-9B \
  --tensor-parallel-size 2 \
  --kv-offloading-backend native \
  --kv-offloading-size 200 \
  --disable-hybrid-kv-cache-manager \
  --enable-prefix-caching
```

**SGLang HiCache (works on hybrid SSM, v0.5.10):**

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3.5-9B \
  --tp 2 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-size 100 \
  --hicache-write-policy write_through \
  --mamba-scheduler-strategy extra_buffer \
  --max-mamba-cache-size 500 \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

`--hicache-size 100` per-rank × tp=2 = 200 GB total — matches vLLM's 200 GB total.

## Side-by-side: vLLM Mooncake → SGLang Mooncake

**vLLM:**

```bash
vllm serve my-model \
  --tensor-parallel-size 8 \
  --kv-transfer-config '{
     "kv_connector":"MooncakeConnector",
     "kv_role":"kv_both",
     "kv_buffer_size":"32GB"
   }'
```

**SGLang:**

```bash
python -m sglang.launch_server \
  --model-path my-model \
  --tp 8 \
  --enable-hierarchical-cache \
  --hicache-storage-backend mooncake \
  --hicache-storage-backend-extra-config '@/etc/sglang/mooncake.toml' \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --hicache-storage-prefetch-policy timeout
```

Where the TOML has `master_server_address`, `metadata_server`, `global_segment_size`, `eviction_high_watermark_ratio`, etc. See `references/storage-backends.md`.

## Write-policy mapping

| vLLM (LMCache) | SGLang | Behaviour |
|---|---|---|
| `LMCACHE_USE_HOT=true` (default) | `--hicache-write-policy write_through` (default) | Always backup |
| `LMCACHE_USE_HOT=false` | n/a — skip | LMCache `use_hot=False` is bugged ([LMCache #2942](https://github.com/LMCache/LMCache/issues/2942)) |
| `LMCACHE_LAZY_BACKUP=true` | `--hicache-write-policy write_through_selective` | Subset of pages |
| n/a | `--hicache-write-policy write_back` | **Avoid** — issue [#19212](https://github.com/sgl-project/sglang/issues/19212) |

## Prometheus metric mapping

| vLLM | SGLang |
|---|---|
| `vllm:prefix_cache_hits_total` | `sglang_cache_hit_rate` (gauge) — multiply by request count for rate-style |
| `vllm:external_prefix_cache_hits_total` | `sglang_hicache_cpu_hit_count` (L2) and `sglang_hicache_storage_hit_count` (L3) |
| `vllm:nixl_xfer_time_seconds_count` | `sglang_hicache_storage_get_duration_seconds_count` |
| `vllm:cache_config_info` | check via `/hicache/storage-backend` admin endpoint |

## Things SGLang HiCache does that vLLM doesn't

1. **Per-tier prefetch policy** — `best_effort` / `wait_complete` / `timeout`. vLLM has no equivalent — its connectors are all best-effort.
2. **Runtime attach/detach of L3 backend without restart** — HTTP admin endpoints. vLLM requires engine restart.
3. **Mamba/SSM state offload** — `HiMambaRadixCache` ships, vLLM `LMCache` is broken on hybrid SSM (#3106).
4. **Per-rank L2 sizing without HMA conflicts** — no `--disable-hybrid-kv-cache-manager` equivalent needed; HiCache is the scheduler.
5. **NIXL config-file path** — `@config.toml` for complex deployments. vLLM's `--kv-transfer-config` is JSON-on-CLI only.

## Things vLLM does that SGLang HiCache doesn't

1. **MultiConnector composition** — vLLM can mix NixlConnector + OffloadingConnector. SGLang assumes one L3.
2. **`--cpu-offload-gb` for model weights** — vLLM weight-offload is separate from KV-offload. SGLang has no direct equivalent (use TP/PP scaling).
3. **NVIDIA Dynamo native control plane** — vLLM is the reference deploy for Dynamo today; SGLang+Dynamo is on the 2026 roadmap (issue [#17130](https://github.com/sgl-project/sglang/issues/17130)).

## Known gotchas during migration

1. **Page size default differs**. vLLM: 16. SGLang: 1 on CUDA, 64 on MUSA. Set `--page-size 64` explicitly to match production hicache recipe.
2. **Reasoning-parser flag must match.** vLLM `--reasoning-parser deepseek_r1` ↔ SGLang `--reasoning-parser deepseek-r1` (note hyphen). aiperf TTFT/TTFO splits depend on this.
3. **Sizing in wrong units** is the #1 OOM source. See "Sizing math" above.
4. **PP > 1 doesn't work** with SGLang HiCache (issue #22607). vLLM works with PP. If migrating from vLLM `pipeline-parallel-size > 1`, drop to `--pp-size 1` until v0.5.11.
5. **`write_back` policy is bugged** — stay on `write_through` even if vLLM's LMCache was using lazy.

## Decision tree for the migrating operator

```
Is the model hybrid-attention (Gemma-4, Qwen3.5/3.6, gpt-oss, Llama-4)?
├── No → vLLM caching works; don't migrate just to migrate
└── Yes
    ├── Hybrid SSM (Qwen3-Next/3.5/3.6, MiniMax-M2)?
    │   └── SGLang v0.5.10 + Mooncake L3 ✓
    ├── Hybrid SWA (Gemma-4, gpt-oss, Llama-4)?
    │   └── Wait for SGLang v0.5.11 (PR #23391) OR
    │       run with explicit --disable-hybrid-swa-memory + verify quality
    └── DSA (DeepSeek-V3.2)?
        └── SGLang v0.5.10 + Mooncake L3 ✓ (3FS in v0.5.11)
```
