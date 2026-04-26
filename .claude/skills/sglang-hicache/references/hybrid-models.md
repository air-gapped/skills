# Hybrid-attention models × HiCache support matrix

The most consequential thing operators evaluating SGLang HiCache vs vLLM caching need to know in 2026.

## Why this matters

The 2026 dense-LLM lineup ships with hybrid attention — alternating sliding-window + full-attention layers (Gemma-4, gpt-oss, Llama-4) OR gated delta-net + attention (Qwen3-Next, Qwen3.5, Qwen3.6, MiniMax-M2). On vLLM, this breaks every tier-extension connector that doesn't subclass `SupportsHMA` (Hybrid Memory Allocator) — see [LMCache #3106](https://github.com/LMCache/LMCache/issues/3106), `vllm-caching` skill backlog. SGLang HiCache started addressing the same problem earlier and is shipping arch-specific support iteratively; the result is a partial matrix that operators must consult before claiming "hicache works".

## Arch detection (where the routing happens)

`python/sglang/srt/managers/scheduler.py:755-870`:

```python
if is_hybrid_ssm:                               # Mamba / SSM family
    cache = HiMambaRadixCache(...)              # if --enable-hierarchical-cache
elif is_hybrid_swa:                             # SWA family (Llama4, GptOss, Gemma4, MiMoV2, Step3p5)
    cache = HiRadixCache(...)                   # FALLS THROUGH (until v0.5.11 SWA support)
    # SWARadixCache branch is unreachable when hicache enabled
else:                                           # MHA / MLA / DSA via NSA
    cache = HiRadixCache(...) or HiMambaRadixCache(...)  # depending on indexer pool
```

Hybrid-SWA detection list (`python/sglang/srt/configs/model_config.py:1503-1515`):
`Llama4ForConditionalGeneration`, `GptOssForCausalLM`, `MiMoV2FlashForCausalLM`, `MiMoV2FlashForCausalLMMTP`, `Step3p5ForCausalLM`, `Step3p5ForCausalLMMTP`, `Gemma4ForCausalLM`, `Gemma4ForConditionalGeneration`.

Hybrid-SSM detection (`scheduler.py:765-769`): models inheriting `Qwen3NextConfig`, `MambaConfig`, gated-delta-net (`gdn`) configs.

## Support matrix — by arch class × backend × release

| Arch class | Examples | L1+L2 only | Mooncake | 3FS | NIXL | aibrix |
|---|---|---|---|---|---|---|
| **MHA / MLA** | Llama-3, DeepSeek-R1, Qwen2.5, Mistral-Large | ✓ all | ✓ all | ✓ all | ✓ all | ✓ all |
| **NSA / DSA** | DeepSeek-V3.2 | ✓ v0.5.9+ | ✓ v0.5.9+ | ✓ v0.5.11 | ✓ v0.5.9+ | partial |
| **Hybrid SSM** (Mamba/GDN) | Qwen3-Next, **Qwen3.5**, Qwen3.6 *(if SSM)*, MiniMax-M2 | partial — needs `--mamba-scheduler-strategy extra_buffer` + `--max-mamba-cache-size N` | ✓ **v0.5.10** (PR #21259) | ✓ **v0.5.11** (PR #23241) | partial | not documented |
| **Hybrid SWA — guarded** | MiMoV2 (#11215), Step3p5, Gemma2, Gemma3, Gemma3n | ✓ (auto `disable_hybrid_swa_memory`) | ✓ | ✓ | ✓ | ✓ |
| **Hybrid SWA — unguarded** | **Llama-4**, **gpt-oss**, **Gemma-4** | ⚠ silent fallthrough — SWA layers treated as full attention | same | same | same | same |
| **Hybrid SWA — proper** | Mistral-class SWA-only | ✗ pre-v0.5.11 | ✗ | ✗ | ✗ | ✗ |
| **DeepSeek V4 UnifiedRadix** | DeepSeek-V4 | open feature | open feature | open feature | open feature | open feature |

Pre-v0.5.11 SWA error message: `ValueError: HiRadixCache only supports MHA, MLA, and NSA (DSA) models` (issue [#23659](https://github.com/sgl-project/sglang/issues/23659)). PR [#23391](https://github.com/sgl-project/sglang/pull/23391) (still **OPEN** as of 2026-04-25) will close #23659 once it merges.

## What "unguarded SWA fallthrough" means in practice

For `Llama4ForConditionalGeneration`, `GptOssForCausalLM`, `Gemma4ForCausalLM` with `--enable-hierarchical-cache`:

1. `is_hybrid_swa` is detected as `True` (model_config.py:1503-1515).
2. Unlike MiMoV2/Step3p5/Gemma3, no server-side guard force-disables hybrid SWA memory (server_args.py:1948-2030).
3. `swa_full_tokens_ratio` keeps its model-config default (e.g. 0.5).
4. `HiRadixCache` doesn't model SWA; it treats SWA layers as full-attention layers in the radix tree.
5. **Effect**: pinned host pool (L2) over-allocates by the SWA ratio (full-len vs window-len), and prefix-cache hits on SWA layers may serve stale/wrong KV when the actual sliding window has scrolled past — quality drift, hard to spot.

**Mitigations**:

1. **Don't enable hicache on those archs** — easiest, lossless option for now.
2. **Pass `--disable-hybrid-swa-memory` explicitly** AND **verify quality** with a held-out eval (e.g. MMLU, GSM8K) before going live. See `test/manual/4-gpu-models/test_qwen35_hicache.py:32` for the verification pattern.
3. **Wait for v0.5.11** — PR #23391 adds proper SWA support to HiRadixCache.

## Tested combinations (CI / benchmark evidence)

| Model | Test file | Coverage |
|---|---|---|
| Qwen/Qwen3.5-27B (Mamba/SSM) | `test/manual/4-gpu-models/test_qwen35_hicache.py:32` | TP=4, file backend, `page_first_direct`, `wait_complete`, `--max-mamba-cache-size 500`, `--mamba-scheduler-strategy extra_buffer`. Verifies GSM8K accuracy with hicache prefetch on, and after `flush_cache` |
| MHA standard | `test/manual/hicache/test_hicache_variants.py:58` | `--hicache-size 100`. MMLU + MGSM thresholds |
| MLA (DeepSeek-distill) | `test_hicache_variants.py:73` | `--hicache-ratio 2`. Per-rank write-back optimisation |
| EAGLE3 + hicache | `test_hicache_variants.py:96` | `--hicache-ratio 1.2 --speculative-algorithm EAGLE3`. accept_length thresholds |
| Small page | `test_hicache_variants.py:118` | `--page-size 32 --hicache-write-policy write_back`. Note: write_back has open bug #19212 |
| Mooncake hybrid bench | PR [#21259](https://github.com/sgl-project/sglang/pull/21259) bench | Qwen3.5-9B: TTFT 714 ms cold → 218 ms warm, throughput 11.6k → 20.9k tok/s |

## Migration story from vLLM/LMCache

If the operator hit the vLLM hybrid wall (LMCache fails to start on Qwen3.5/3.6/Gemma-4, NixlConnector kv_both no auto-discovery, SimpleCPUOffloadConnector TOCTOU race per vLLM #39702), the SGLang options are:

| Coming from | SGLang equivalent | Caveat |
|---|---|---|
| vLLM native CPU offload (`--kv-offloading-size`) on hybrid | `--enable-hierarchical-cache --hicache-ratio 2` (no L3) | Works on hybrid SSM in v0.5.10, hybrid SWA in v0.5.11 |
| LMCache + DRAM tier | Same — L1+L2 only | Hybrid works (Mamba v0.5.10, SWA v0.5.11). Sizing is per-rank not total |
| LMCache + NVMe tier | `--hicache-storage-backend nixl` with NIXL POSIX plugin | NIXL hybrid support depends on plugin |
| NixlConnector 1P1D (P/D disagg) | SGLang PD-disagg + `--hicache-storage-backend mooncake/nixl --disaggregation-decode-enable-offload-kvcache` | PD itself works on hybrid; runtime attach/detach tied to Mooncake bug #23457 |
| MooncakeConnector | `--hicache-storage-backend mooncake` | Native; richer policy controls |

**For Qwen3.5 / Qwen3.6 specifically** (the cases where vLLM v0.19.1 + LMCache 0.4.4 outright crashes):

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3.5-9B \
  --tp 2 \
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

Verify against `test_qwen35_hicache.py` first — that's the only CI-covered path.

## Roadmap

- v0.5.11 (target): SWA support in HiRadixCache (PR #23391 still OPEN as of 2026-04-25), 3FS Mamba/DSA (PR #23241 merged 2026-04-24), hybrid CP (#22996).
- 2026 Q1 SGLang roadmap (issue [#12780](https://github.com/sgl-project/sglang/issues/12780)) explicitly lists "production-level reliability across HiCache" as an open goal — i.e. upstream itself does not yet treat HiCache as production-stable across all parallelism modes.
- DeepSeek V4 UnifiedRadix HiCache (issue [#23639](https://github.com/sgl-project/sglang/issues/23639)) — covers c4/c4_indexer/c128 compressed KV offload; SWA still device-only. Open feature.
- NVIDIA Dynamo + HiCache integration on GB200/GB300 with KVBM — issue [#17130](https://github.com/sgl-project/sglang/issues/17130).
