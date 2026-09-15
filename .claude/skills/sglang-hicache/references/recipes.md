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

The case vLLM v0.19.1 + LMCache 0.4.4 crashes on. SGLang HiCache handles it — Mooncake SSM support since v0.5.10.

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

Returns HTTP 400 if any request is in-flight (`is_fully_idle()` check). Multi-node Mooncake attach used the wrong hostname (issue [#23457](https://github.com/sgl-project/sglang/issues/23457)) — **closed COMPLETED 2026-06-15**. On older builds, inject `MOONCAKE_LOCAL_HOSTNAME` per node or use the static startup flag instead of runtime attach.

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

## Recipe 11 — SiMM (Scitix) L3

Floor **v0.5.11**. Config reaches SGLang two ways, and `--hicache-storage-backend-extra-config` wins whenever it carries `manager_address`:

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-32B-Instruct \
  --tp 4 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-storage-backend simm \
  --hicache-storage-backend-extra-config \
    '{"manager_address":"10.0.0.5:30001","clnt_threadpool_size":10,"enable_profile":false}'
```

File form — used **only** when `manager_address` is absent from extra-config, and the env var is then mandatory (unset raises, it does not fall back to a default path):

```bash
export SGLANG_HICACHE_SIMM_CONFIG_PATH=/etc/sglang/simm.json
# {"manager_address": "10.0.0.5:30001", "clnt_threadpool_size": 10, "enable_profile": false}
```

| Key | Default | Notes |
|---|---|---|
| `manager_address` | none — **required** | `host:port` of the SiMM cluster manager |
| `clnt_threadpool_size` | `10` | |
| `enable_profile` | `false` | |
| `extra_backend_tag` | unset | extra-config only; forwarded to the SiMM data server |

**Do not copy the env vars out of the backend's bundled README.** It documents `DEFAULT_SIMM_CONFIG_PATH_ENV` and `SIMM_CLUSTER_MANAGER` as part of the precedence chain; neither string exists anywhere in SGLang's source, so SGLang never reads them. `SGLANG_HICACHE_SIMM_CONFIG_PATH` is the only env var that works. The `simm` package is a separate install (`github.com/scitix/SiMM`) — absent, the backend raises ImportError at startup.

## Recipe 12 — EIC (Volcengine) L3

Floor **v0.5.3**. YAML only — there is no extra-config path:

```bash
export REMOTE_EIC_YAML=/etc/sglang/remote-eic.yaml   # default if unset: /sgl-workspace/config/remote-eic.yaml
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-32B-Instruct \
  --tp 4 --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-storage-backend eic \
  --hicache-write-policy write_through \
  --hicache-mem-layout page_first
```

```yaml
# /etc/sglang/remote-eic.yaml
remote_url: "eic://10.0.0.7:9000"   # required; the eic:// prefix is stripped to form the endpoint
eic_instance_id: "inst-001"
eic_log_dir: "/var/log/sglang-eic"  # required in practice — see below
eic_thread_num: 1
eic_log_level: 2
eic_trans_type: 3
eic_namespace: ""
enable_kvset_direct: true
enable_kvget_direct: true
enable_kvset_gpu_direct: false      # also requires CUDA available
enable_kvget_gpu_direct: false
enable_gpu_nic_affinity: false
```

Two startup failures read as something other than their cause:

- **Omitting `eic_log_dir` crashes with `TypeError`, not a config error.** It defaults to `None` and is then passed straight to `os.path.exists()`. Set it.
- **Omitting `remote_url` also crashes with `TypeError`.** The guard constructs an `AssertionError` without raising it, so execution continues to the `eic://` prefix strip on `None`. A `TypeError` here means `remote_url` is missing, not malformed.

Set `gpu_nic_affinity_config` / `cpu_nic_affinity_config` (JSON strings) only alongside `enable_gpu_nic_affinity: true` — they are ignored otherwise.

## Recipe 13 — `dynamic`: your own L3 backend

Floor **v0.5.3**. Loads any class subclassing `HiCacheStorage` by import path. All three keys are required; a missing one raises `ValueError` at startup:

```bash
PYTHONPATH=/opt/mybackend \
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-32B-Instruct \
  --port 30000 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-storage-backend dynamic \
  --hicache-storage-backend-extra-config \
    '{"backend_name":"mystore","module_path":"mybackend.store","class_name":"MyHiCacheStore"}'
```

| Key | Meaning |
|---|---|
| `backend_name` | label only — appears in logs, selects nothing |
| `module_path` | import path; must be importable from the server process (`PYTHONPATH`) |
| `class_name` | class in that module, must subclass `HiCacheStorage` |
| `interface_v1` | optional, `0`/`1` — `1` routes through `batch_get_v1` / `batch_set_v1` |

The class is constructed as `MyHiCacheStore(storage_config, kwargs)` — two positional arguments, the second a plain dict. A constructor taking only `storage_config` fails at startup.
