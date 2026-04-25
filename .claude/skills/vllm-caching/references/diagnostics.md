# Diagnostics

Verification and observability recipes. Load when debugging why caching isn't working as expected.

## Is LMCache installed in the container?

Direct check:

```bash
docker run --rm --entrypoint bash <image> -c "pip show lmcache"
```

### Without pulling the image (Docker Hub manifest inspection)

Use the bundled helper script — it queries Docker Hub's manifest API and prints CUDA version, entrypoint, and whether LMCache/NIXL/Mooncake were baked in at build time. Pulls only a few kilobytes, never the layers.

```bash
${CLAUDE_SKILL_DIR}/scripts/inspect-vllm-image.sh v0.19.0-cu130
# or for arm64:
${CLAUDE_SKILL_DIR}/scripts/inspect-vllm-image.sh glm51-cu130 arm64
```

Expected output:

```
image:      vllm/vllm-openai:v0.19.0-cu130 (amd64)
CUDA:       13.0.1
entrypoint: ['vllm', 'serve']
LMCache/NIXL/Mooncake: YES (built with INSTALL_KV_CONNECTORS=true)
```

Safe to run against multi-GB images without filling local storage.

## Is LMCache actually caching?

Tail server logs for these patterns:

```
LMCache INFO: Storing KV cache for N out of N tokens for request <id>
LMCache INFO: Retrieved KV cache for N out of N tokens for request <id>
```

The ratio of retrieved:stored is the hit rate. For coding-agent workloads on a well-sized DRAM tier, expect > 0.7 after warmup.

## GDS sanity check

```bash
sudo modprobe nvidia-fs
lsmod | grep nvidia_fs
/usr/local/cuda/gds/tools/gdscheck -p | head -60
```

`gdscheck -p` enumerates every NVMe and prints GDS compatibility plus reasons for any "Unsupported." Also validates IOMMU, ACS, filesystem, and driver state.

## vLLM's own cache metrics

Exposed on the Prometheus endpoint:

```
vllm:cache_config_info{block_size=...,cpu_offload_gb=...,kv_offloading_size=...,kv_offloading_backend=...}
vllm:kv_cache_usage_perc
vllm:prefix_cache_queries_total                # GPU prefix cache (HBM)
vllm:prefix_cache_hits_total
vllm:external_prefix_cache_queries_total       # offload tier (CPU DRAM via OffloadingConnector)
vllm:external_prefix_cache_hits_total
```

Monitor `prefix_cache_hits_total / prefix_cache_queries_total` — the GPU-level hit rate. The `external_prefix_cache_*` pair is the **offload-tier** counterpart: queries count tokens looked up in the CPU tier; hits count tokens recovered from there. Note that on `cache_config_info`, `num_cpu_blocks="None"` is normal for the native backend even when CPU offload is allocated and active — the label is populated by older offload paths only. Trust the engine startup log + `external_prefix_cache_queries_total` to confirm allocation.

In vLLM 0.20+ the metric prefix dropped the legacy `gpu_` segment — `vllm:gpu_prefix_cache_hits_total` does NOT exist on a fresh install; it's `vllm:prefix_cache_hits_total`. Older grep regexes targeting `^vllm:gpu_prefix_cache` silently return zero; update them when reading post-v0.20 metrics.

## LMCache's own metrics — separate endpoint

LMCache defines **117 `lmcache:*` metric families** (verified 2026-04-25 on v0.4.4-cu13) — request volume, token volume, eviction counts, latency histograms, hit rates, remote-tier ping health, and chunk-statistics. **None of them appear on vLLM's `/metrics`**: they live in the `EngineCore` subprocess's Prometheus REGISTRY, not the API server's. Stock setup hides them entirely.

Enable LMCache's internal API server to expose its own `/metrics`:

```yaml
# in lmcache.yaml
internal_api_server_enabled: True
internal_api_server_port_start: 7000
internal_api_server_host: "0.0.0.0"
```

Worker N exposes `http://<pod>:<port_start + N>/metrics`. With one LMCache worker per pod, that's port 7000.

Add a container port + Service port mirroring 7000 so Prometheus can scrape it. Configure a separate Prometheus job (or a second `prometheus.io/port` annotation) — the vLLM main `/metrics` annotation can't be reused since it points at port 8000.

### Metric families worth scraping

| Family | What it tells you |
|---|---|
| `lmcache:num_{store,retrieve,lookup}_requests_total` | RPS shape per operation type |
| `lmcache:num_{stored,hit,prompt,vllm_hit,lookup,requested}_tokens_total` | Hit-rate calc (`num_hit_tokens / num_lookup_tokens`), throughput |
| `lmcache:num_remote_{read,write}_{requests,bytes}_total` | Cross-instance / remote-backend bandwidth |
| `lmcache:local_cpu_evict_{count,keys_count,failed_count}_total` | DRAM cap pressure, eviction storms |
| `lmcache:forced_unpin_count_total`, `lookup_0_hit_requests_total` | Sizing / hit-rate degradation signals |
| `lmcache:num_slow_retrieval_by_{time,speed}_total`, `get_blocking_failed_count`, `put_failed_count` | SLO regression hooks |
| `lmcache:retrieve_hit_rate`, `lookup_hit_rate`, `request_cache_hit_rate` | Live hit-rate gauges (no need to compute deltas) |
| `lmcache:local_cache_usage`, `remote_cache_usage`, `local_storage_usage` | Tier fill % |
| `lmcache:active_memory_objs_count`, `pinned_memory_objs_count`, `kv_msg_queue_size` | Internal queue/object pressure |
| `lmcache:lmcache_is_healthy` | 0/1 health gauge |
| `lmcache:time_to_{retrieve,store,lookup}` | Per-operation latency histograms |
| `lmcache:retrieve_{process_tokens,broadcast,to_gpu}_time`, `store_{from_gpu,put}_time` | Stage breakdown of retrieve/store path |
| `lmcache:remote_time_to_{get,put,get_sync}`, `remote_backend_batched_get_blocking_time` | Remote-tier latency stages |
| `lmcache:retrieve_speed`, `request_cache_lifespan` | Effective throughput, reuse-window distribution |
| `lmcache:remote_ping_{latency,errors,successes,error_code}` | Connection health to remote URL backends (Mooncake, S3-style stores) |
| `lmcache:periodic_threads_{total,running,active}_count`, `pin_monitor_pinned_objects_count` | Liveness of internal worker threads |
| `lmcache:chunk_statistics_*` | Prefix-reuse analytics; opt in with `enable_chunk_statistics: True` (memory-bloom-filter or file-based strategies) |

Each metric is labelled `model_name`, `served_model_name`, `role`, `worker_id` so multi-instance deployments are queryable.

### vLLM-side metrics that LMCache populates

Visible on the **main vLLM `/metrics`** endpoint (port 8000), populated by LMCacheConnectorV1:

| Metric | Source |
|---|---|
| `vllm:external_prefix_cache_queries_total` | LMCache lookup count (in tokens) |
| `vllm:external_prefix_cache_hits_total` | LMCache hit count (in tokens) |
| `vllm:prompt_tokens_cached_total` | local + external combined |

For most operator dashboards the vLLM-side three are enough; the lmcache-side 117 are for deep diagnosis (eviction storms, latency stage breakdowns, remote-backend ping failures).

## Native offload — confirm it's actually transferring

The native `OffloadingConnector` emits a periodic log line that names the actual GPU↔CPU bytes moved:

```
INFO ... [metrics.py:103] KV Transfer metrics: GPU_to_CPU_total_bytes=1363673088, GPU_to_CPU_total_time=0.20692592173814772
```

Bytes ÷ time = effective transfer bandwidth. Verified on RTX 4060 Ti 16 GB + cu130-nightly = ~6.6 GB/s for the host-pinned path, in line with PCIe Gen4 x8 ceilings on consumer boards. The presence of these lines in pod logs is the simplest "is it really offloading" check — if the line never appears, the connector either wasn't loaded (check `cache_config_info{kv_offloading_backend=...}`) or the workload didn't generate enough KV pressure to trigger eviction to CPU.

A missing line plus `external_prefix_cache_queries_total > 0` and `external_prefix_cache_hits_total = 0` is a different story: the connector IS loaded and IS being consulted, but the workload prefix shape is too varied for the CPU tier to actually score hits. Send the same prefix multiple times (or run a coding-agent-shaped workload) before concluding the tier is broken.

## Verify `--kv-offloading-size` is allocated as expected

The engine startup logs report the actual allocation. Cross-check against `vllm:cache_config_info` — if the value is 1/TP of what was configured, the flag was probably interpreted as per-rank (the SGLang habit). Recheck the configuration.

## Pre-flight checklist for a new offload deploy

Before recommending a config, confirm in this order:

1. `--disable-hybrid-kv-cache-manager` is in the args. If missing, the engine will crash at `KVConnectorFactory.create_connector` with the explicit "does not support HMA" ValueError. Read the previous-container log (`kubectl logs --previous`) on any first-boot crash before changing anything else.
2. `--enable-prefix-caching` is in the args. Without it, prefix reuse is off and offload has nothing to populate.
3. `--max-model-len` is set sensibly (or `auto`). `auto` means vLLM picks the max that fits available KV — useful starting point on small / consumer GPUs. Grep `Auto-fit max_model_len` in startup logs to learn the chosen value.
4. The model architecture is non-hybrid OR is on the verified-with-offload list. Qwen3.5/3.6 hybrid DeltaNet+Attention may fail-to-start on native offload (#36463); test a non-hybrid model first to isolate.
5. `cache_config_info` reports the expected `kv_offloading_backend` and `kv_offloading_size`. If both are missing, the flags didn't take.
