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
vllm:cache_config_info{block_size=...,cpu_offload_gb=...,kv_offloading_size=...,...}
vllm:kv_cache_usage_perc
vllm:prefix_cache_queries_total
vllm:prefix_cache_hits_total
```

Monitor `prefix_cache_hits_total / prefix_cache_queries_total` — the GPU-level hit rate. With offload on, re-loads from DRAM/NVMe count as hits.

## Verify `--kv-offloading-size` is allocated as expected

The engine startup logs report the actual allocation. Cross-check against `vllm:cache_config_info` — if the value is 1/TP of what was configured, the flag was probably interpreted as per-rank (the SGLang habit). Recheck the configuration.
