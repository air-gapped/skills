# Hardware reference and sizing math

Concrete numbers for common production platforms. Load when sizing `--kv-offloading-size` or evaluating whether offload will help.

## Sizing math

### Per-token KV memory

Aggregate across all TP ranks:

```
bytes_per_token = 2 × num_layers × num_kv_heads × head_dim × dtype_bytes
```

For a large MoE with GQA at long context, expect roughly 1.5–2.5 MB/token BF16 or 0.75–1.25 MB/token FP8. Verify empirically on a specific model — the `vllm:cache_config_info` metric and engine startup logs report actual bytes.

### Slot math worked example (H200 8× TP=8, 141 GB HBM each = 1128 GB aggregate)

```
Available for KV = gpu_mem_util × 1128 GB − model_weight_bytes
For GLM-5.1-FP8 at TP=8:
  ~1015 GB (at 0.90) − ~355 GB weights ≈ 660 GB KV budget
  At ~2 MB/token BF16 aggregate, 200k-token slot ≈ 400 GB → ~1.6 concurrent slots at max len
```

Adding 1600 GB of DRAM via `--kv-offloading-size 1600` (with 2 TB host RAM, leaving ~400 GB for OS/page cache):

- At 200k max: ~4 additional warm slots held in DRAM
- At 100k avg: ~8 additional warm slots
- With chunk-level prefix dedup (LMCache default 256-token chunks), effective concurrency for agentic workloads is typically 2–4× the raw slot count — the same 100k context persists across agent turns mostly unchanged, so DRAM keeps the context live between tool calls without eviction

## Dell PowerEdge XE9680 with HGX H200

Common production platform for large-model inference:

- 8× H200 SXM5, 141 GB HBM each
- NVLink 900 GB/s bidirectional per GPU via NVSwitch (GPU-to-GPU only; does not accelerate host-to-GPU offload)
- 2× Intel Xeon, 80 PCIe Gen5 lanes per CPU (160 total)
- Each GPU has its own Gen5 x16 uplink to the CPU root complex: **~50 GB/s practical** with pinned memory
- 32 DDR5 DIMMs, 8 channels per socket, DDR5-5600 → **~716 GB/s aggregate host memory bandwidth**
- Up to 4 TB RAM; practical headroom for offload after OS/page cache is ~75–80% of installed
- Up to 16× E3.S or 8× U.2 NVMe bays for disk tier

Offload path on XE9680: CPU DRAM → PCIe Gen5 x16 → GPU HBM, one link per GPU. Aggregate host-to-GPU offload bandwidth = ~400 GB/s (8 × 50), well under the DDR5 ceiling, so DRAM is not the bottleneck.

## HGX H100 8-GPU platforms

Similar topology to H200 but with 80 GB HBM per GPU. Same sizing ratios apply with a smaller KV budget. On standard H100 (not H100 NVL) the per-GPU HBM is 80 GB; on H100 NVL it is 94 GB.

## Load-time estimates

For a 100k-token BF16 context (~20–40 GB aggregate across 8 GPUs):

| Tier | Time | Notes |
|---|---|---|
| DRAM | 100–500 ms | Hot path; PCIe Gen5 x16 per GPU |
| NVMe (Gen4 U.2, buffered) | 5–7 s | L3 overflow tier |
| NVMe (Gen5 with GDS) | 3–4 s | Direct DMA, datacenter GPU only |
| Re-prefill at ~10k tok/s | ~10 s | Baseline to beat |

NVMe beats re-prefill, but DRAM beats NVMe by 20×. Size the DRAM tier to hold the hot working set; treat NVMe as overflow for sessions from "earlier today" that might come back.
