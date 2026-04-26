# HiCache recipes

Concrete commands for the most common production scenarios. Substitute `--model-path` / `--url` / hardware as needed.

## Recipe 1 — Mooncake on H100 RDMA cluster (Qwen3-235B-A22B-Instruct-2507)

The LMSYS blog's headline scenario. 8× H800 + 8× mlx5 RDMA, 760 GB Mooncake pool (30 GB/GPU = 240 GB total).

```bash
# /etc/sglang/mooncake.toml
[mooncake]
master_server_address = "10.0.0.10:50051"
metadata_server       = "p2p"
global_segment_size   = "32GB"
local_buffer_size     = "4GB"
device                = "auto"

[mooncake.eviction]
high_watermark_ratio  = 0.9
low_watermark_ratio   = 0.7

[hicache]
prefetch_threshold              = 1024
prefetch_timeout_base           = 0.05
prefetch_timeout_per_ki_token   = 0.01
```

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-235B-A22B-Instruct-2507 \
  --tp 8 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-size 30 \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --hicache-write-policy write_through \
  --hicache-storage-backend mooncake \
  --hicache-storage-prefetch-policy timeout \
  --hicache-storage-backend-extra-config '@/etc/sglang/mooncake.toml' \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

`--hicache-size 30` is per-rank → 240 GB total across TP=8.

## Recipe 2 — DeepSeek-R1 on 8× H20-3e + 3FS

LMSYS blog's flagship benchmark — 65,536-token context.

```bash
python -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-R1 \
  --tp 8 --port 30000 \
  --reasoning-parser deepseek-r1 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --hicache-write-policy write_through \
  --hicache-storage-backend hf3fs \
  --hicache-storage-prefetch-policy timeout \
  --hicache-storage-backend-extra-config '{"mount_path":"/mnt/3fs/sglang","use_usrbio":true}' \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

## Recipe 3 — Qwen3.5 (hybrid SSM) on Mooncake — vLLM-broken case

The case vLLM v0.19.1 + LMCache 0.4.4 crashes on. SGLang HiCache v0.5.10 with Mooncake handles it.

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3.5-9B \
  --tp 2 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --hicache-write-policy write_through \
  --hicache-storage-backend mooncake \
  --hicache-storage-prefetch-policy timeout \
  --hicache-storage-backend-extra-config '@/etc/sglang/mooncake.toml' \
  --mamba-scheduler-strategy extra_buffer \
  --max-mamba-cache-size 500 \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

## Recipe 4 — NIXL + NVIDIA Dynamo / GB200

```toml
# /etc/sglang/nixl.toml
[nixl]
plugin_priority = ["3FS", "POSIX", "GDS_MT", "GDS"]
storage_dir     = "/mnt/3fs/sglang-nixl"

[nixl.gds]
io_threads = 16
buffer_mb  = 256
```

```bash
python -m sglang.launch_server \
  --model-path meta-llama/Llama-3.1-405B-Instruct \
  --tp 8 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --hicache-write-policy write_through \
  --hicache-storage-backend nixl \
  --hicache-storage-prefetch-policy timeout \
  --hicache-storage-backend-extra-config '@/etc/sglang/nixl.toml' \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

## Recipe 5 — L1 + L2 only, no L3 (single-node start)

The 80% case — host DRAM is a huge tier, no need for distributed L3 unless prefix locality crosses pods.

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-32B-Instruct \
  --tp 4 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-write-policy write_through \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

No `--hicache-storage-backend` flag → L2 only. Default `--hicache-mem-layout layer_first` and `--hicache-io-backend kernel` work fine without zero-copy. Add storage backend when DRAM evictions become noticeable in `sglang_hicache_cpu_eviction_count`.

## Recipe 6 — File backend for dev / CI

NEVER use in prod (issue #21880). Useful for unit tests and reproducing bugs.

```bash
SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR=/tmp/hicache \
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B \
  --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-storage-backend file \
  --hicache-storage-prefetch-policy timeout
```

## Recipe 7 — PD disaggregation + decode-side L3 offload

Prefill pod and decode pod separate; decode pod also offloads its KV to L3.

```bash
# Decode pod
python -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-R1 \
  --tp 8 \
  --disaggregation-mode decode \
  --disaggregation-decode-enable-offload-kvcache \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-storage-backend mooncake \
  --hicache-storage-backend-extra-config '@/etc/sglang/mooncake.toml' \
  --hicache-storage-prefetch-policy timeout \
  --page-size 64 \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

`--disaggregation-decode-enable-offload-kvcache` requires `--hicache-storage-backend` set (server_args.py:3836). The prefill pod has its own caching config — don't have to match.

## Recipe 8 — Runtime attach / detach (no engine restart)

Engine running with no L3 backend; attach Mooncake at runtime.

```bash
# Engine launched with L1+L2 only:
python -m sglang.launch_server \
  --model-path my-model \
  --enable-hierarchical-cache \
  --admin-api-key $ADMIN_KEY \
  --port 30000

# Operator attaches Mooncake on the fly (drain traffic first):
curl -X PUT http://localhost:30000/hicache/storage-backend \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
        "hicache_storage_backend": "mooncake",
        "hicache_storage_backend_extra_config_json": "{\"master_server_address\":\"10.0.0.10:50051\",\"metadata_server\":\"p2p\",\"global_segment_size\":\"32GB\"}",
        "hicache_storage_prefetch_policy": "timeout"
      }'

# Inspect:
curl http://localhost:30000/hicache/storage-backend

# Detach (drain traffic first):
curl -X DELETE http://localhost:30000/hicache/storage-backend \
  -H "Authorization: Bearer $ADMIN_KEY"
```

Returns HTTP 400 if any request is in-flight (`is_fully_idle()` check). Multi-node Mooncake attach is broken on v0.5.10 — issue [#23457](https://github.com/sgl-project/sglang/issues/23457).

## Recipe 9 — Validating that hicache is actually helping

After enabling, verify that hits are landing.

### Pre-/post-metric diff

```bash
curl -s http://endpoint:30000/metrics > /tmp/metrics-pre.txt

# Send N requests with shared prefixes (e.g. via aiperf or vllm bench)
aiperf profile --model my-model --url http://endpoint:30000 \
  --endpoint-type chat --streaming --tokenizer my-model \
  --concurrency 50 --request-count 1000 --isl 8000 --osl 200 \
  --shared-system-prompt-length 1000

curl -s http://endpoint:30000/metrics > /tmp/metrics-post.txt

# Diff cache-hit counters:
diff <(grep -E 'sglang_(cache_hit|hicache)' /tmp/metrics-pre.txt) \
     <(grep -E 'sglang_(cache_hit|hicache)' /tmp/metrics-post.txt)
```

Expect: `sglang_hicache_cpu_hit_count`, `sglang_hicache_storage_hit_count` (if L3 enabled) increase.

### A/B comparison

Run twice on identical traffic, with and without `--enable-hierarchical-cache`. Compare P50/P99 TTFT and end-to-end token throughput. Reuse the `aiperf` skill's `concurrency sweep` recipe to find the throughput-vs-tail-latency knee for each.

## Recipe 10 — KV-event observability

Added in v0.5.9 (PR #17648). Every L1↔L2↔L3 promotion/eviction emits a Prometheus counter.

```bash
python -m sglang.launch_server ... \
  --enable-hierarchical-cache \
  --enable-cache-report --enable-metrics
```

Useful counters:

- `sglang_cache_hit_rate` — overall hit rate (L1 OR L2 OR L3)
- `sglang_hicache_cpu_hit_count` — L2 hits served
- `sglang_hicache_storage_hit_count` — L3 hits served
- `sglang_hicache_cpu_eviction_count` — L2 evictions to free pages already in L3
- `sglang_hicache_prefetch_started_total` / `_completed_total` / `_aborted_total` — L3 prefetch lifecycle (PR #18460)
- `sglang_hicache_kv_event_count` — L2 promotion events (PR #22894, v0.5.11)
