# MoE tuning + expert parallelism + parallelism decision matrix

Load when: operator is deploying an MoE model, hitting "Using default MoE config. Performance might be sub-optimal!" in logs, choosing between TP / EP / DP / PP, or configuring Wide-EP for DeepSeek / Qwen3-MoE / Kimi-K2.

## Contents

- [`benchmark_moe.py` — fused-MoE kernel autotune](#benchmark_moepy--fused-moe-kernel-autotune) — CLI flags, output filename convention, runtime lookup path
- [DeepEP all-to-all](#deepep-all-to-all) — HT / LL modes, backend selection, NVSHMEM tuning
- [EPLB (Expert Parallel Load Balancer)](#eplb-expert-parallel-load-balancer)
- [Published Wide-EP numbers](#published-wide-ep-numbers) — H200, GB200, LMSYS
- [Parallelism decision matrix](#parallelism-decision-matrix) — activation density, concurrency crossover, MLA rule, DeepSeek-V3.2 warning, supported combos, PP rules
- [Model-specific recipes](#model-specific-recipes) — Llama-4, DeepSeek, Qwen3-Coder, Kimi-K2, Mixtral
- [Common MoE-specific mistakes](#common-moe-specific-mistakes-beyond-skillmds-top-10)

## `benchmark_moe.py` — fused-MoE kernel autotune

**Location:** `benchmarks/kernels/benchmark_moe.py` in the vLLM repo ([code on main](https://github.com/vllm-project/vllm/blob/main/benchmarks/kernels/benchmark_moe.py)).

**What it does:** tunes Triton kernel configurations (block sizes `BLOCK_SIZE_M/N/K`, `GROUP_SIZE_M`, `num_warps`, `num_stages`) for FusedMoE layers across batch sizes 1–4096 and quantization schemes. Auto-extracts MoE shape from HuggingFace config. Uses Ray to parallelize across local GPUs.

**CLI flags:**

| Flag | Default | Purpose |
|---|---|---|
| `--model` | `mistralai/Mixtral-8x7B-Instruct-v0.1` | HF model ID |
| `--tp-size` / `-tp` | 2 | Tensor-parallel degree |
| `--enable-expert-parallel` / `-enable-ep` | off | Activate EP |
| `--dtype` | `auto` | `auto` \| `fp8_w8a8` \| `int8_w8a16` \| `int4_w4a16` |
| `--use-deep-gemm` | off | Use DeepGEMM instead of Triton |
| `--save-dir` | `./` | Output dir for JSON configs |
| `--tune` | off | Tuning phase (else just bench) |
| `--batch-size` | 1..4096 list | Override sweep |
| `--trust-remote-code` | off | Needed for some models |

**Output filename convention** (from `get_config_file_name()`):

```
E=<experts_per_rank>,N=<intermediate/2>,device_name=<GPU>[,dtype=<quant>][,block_shape=<shape>].json
```

Examples: `E=256,N=128,device_name=NVIDIA_B200.json`, `E=8,N=2048,device_name=NVIDIA_H200,dtype=fp8_w8a8.json`, `E=128,N=1024,device_name=AMD_Instinct_MI325X.json`.

- `E` = experts per rank. With EP: `global_E / TP_size`.
- `N` = intermediate size AFTER `silu_and_mul` (= `shard_intermediate_size // 2`).
- `device_name` — spaces replaced with `_`; auto-detected.

**Config contents:** JSON mapping batch size → kernel params:

```json
{
  "1":    {"BLOCK_SIZE_M": 16, "BLOCK_SIZE_N": 32, "BLOCK_SIZE_K": 64,  "GROUP_SIZE_M": 1, "num_warps": 4, "num_stages": 4},
  "8":    {"BLOCK_SIZE_M": 32, "BLOCK_SIZE_N": 64, "BLOCK_SIZE_K": 128, "GROUP_SIZE_M": 1, "num_warps": 8, "num_stages": 3},
  "4096": {"BLOCK_SIZE_M": 128,"BLOCK_SIZE_N": 256,"BLOCK_SIZE_K": 64,  "GROUP_SIZE_M": 8, "num_warps": 8, "num_stages": 3}
}
```

**Runtime lookup** (from `get_moe_configs()`):
1. `VLLM_TUNED_CONFIG_FOLDER` env var (user override)
2. `vllm/model_executor/layers/fused_moe/configs/` (shipped with package)
3. Fallback: generic default + warning → 20–40% throughput loss

**Canonical serve flow after tune:**

```bash
python benchmarks/kernels/benchmark_moe.py \
  --model deepseek-ai/DeepSeek-V3 \
  --tp-size 8 --enable-expert-parallel --dtype fp8_w8a8 \
  --tune --save-dir ./moe_configs

export VLLM_TUNED_CONFIG_FOLDER=./moe_configs

vllm serve deepseek-ai/DeepSeek-V3 \
  --tensor-parallel-size 8 --enable-expert-parallel \
  --enable-eplb --enable-dbo \
  --gpu-memory-utilization 0.85
```

Verify: no `default MoE config` warning in logs.

**Which models need re-tune on new hardware:** DeepSeek-V2/V3/V3.2/R1, Qwen2-MoE / Qwen3-MoE (incl. Qwen3-235B-A22B, Qwen3-Coder-480B-A35B), Mixtral 8x7B/8x22B, Llama-4-Scout (17B-16E), Llama-4-Maverick (17B-128E), Kimi-K2, GLM-4.5/4.6 MoE, Granite-MoE, Jamba, DBRX. Shipped configs cover common combos (H100, H200, A100, MI300X for Mixtral). B200 / B300 / GB200 / MI325X / MI355X / Jetson AGX Thor / RTX 6000 Pro Blackwell almost always need re-tuning ([Jetson AGX Thor thread](https://forums.developer.nvidia.com/t/jetson-agx-thor-vllm-26-02-moe-performance-significantly-below-reference-missing-fused-moe-config/364663), [MissionSquad/vllm-moe-configs](https://github.com/MissionSquad/vllm-moe-configs)).

**Env vars:** `VLLM_MOE_TUNE_CACHE_CLEAR_INTERVAL=50` (clear Triton JIT cache every N iters — OOM prevention on many-expert models).

## DeepEP all-to-all

**What it is:** DeepSeek AI's all-to-all kernel library for MoE dispatch/combine. Two modes:

- **`deepep_high_throughput`** — batched GEMM with unpadded activations. For prefill, long ISL.
- **`deepep_low_latency`** — padded activations to preserve CUDA graphs. For decode.

Repo: [github.com/deepseek-ai/DeepEP](https://github.com/deepseek-ai/DeepEP). vLLM docs: [Expert Parallel Deployment](https://docs.vllm.ai/en/latest/serving/expert_parallel_deployment/).

**Select a backend:**

```bash
export VLLM_ALL2ALL_BACKEND={naive|pplx|deepep_high_throughput|deepep_low_latency}
```

| Backend | Use when | Caveats |
|---|---|---|
| `naive` | default, works everywhere | broadcast + allreduce; slowest |
| `pplx` | Perplexity kernels | **incompatible with microbatching** ([#27513](https://github.com/vllm-project/vllm/issues/27513)) |
| `deepep_high_throughput` | prefill, long ISL | needs compiled `deep_ep` package |
| `deepep_low_latency` | decode, CUDA-graph-compatible | same |

**Known hang:** `dp=2, tp=8, ep=16` with DeepEP on v0.9.2 hangs during warm-up; `naive` works ([#21306](https://github.com/vllm-project/vllm/issues/21306)).

**NVSHMEM + IB tuning** (Azure H100 400 Gb/s IB baseline, from [Microsoft blog](https://techcommunity.microsoft.com/blog/azurehighperformancecomputingblog/achieving-optimal-performance-for-deepseek-expert-parallelism-deepep-on-azure/4414699)):

```bash
export NVSHMEM_IB_ENABLE_IBGDA=1
export NVSHMEM_IBGDA_NIC_HANDLER=gpu
export NVSHMEM_QP_DEPTH=1024
export NVSHMEM_ENABLE_NIC_PE_MAPPING=1
export NVSHMEM_HCA_LIST=mlx5_ib0:1,mlx5_ib1:1,mlx5_ib2:1,mlx5_ib3:1,mlx5_ib4:1,mlx5_ib5:1,mlx5_ib6:1,mlx5_ib7:1
```

Bind 12 cores per process to the matching NUMA node of the HCA. Requires IB with 32/64/128-bit atomics (verify with `ibstat`).

Measured Azure: dispatch FP8 45.9 GB/s RDMA / 149.82 GB/s NVLink; combine 61.34 / 200.22 GB/s.

## EPLB (Expert Parallel Load Balancer)

Distributes hot experts as **redundant replicas** across ranks so traffic balances. PR [#18343](https://github.com/vllm-project/vllm/pull/18343).

```bash
vllm serve <model> --enable-expert-parallel \
  --enable-eplb \
  --eplb-config '{"window_size":1000,"step_interval":3000,"num_redundant_experts":32,"log_balancedness":true}'
```

Recommended **32 redundant experts at scale** — hot experts get replicated across multiple ranks.

## Published Wide-EP numbers

| Setup | Model | Throughput | Source |
|---|---|---|---|
| 96× H100 (12 nodes, PD-disagg) | DeepSeek-V3 prefill | 57,674 tok/s/node @ 1K ISL (EP32) | [LMSYS 2025-05-05](https://www.lmsys.org/blog/2025-05-05-large-scale-ep/) |
| same | decode | 22,282 tok/s/node @ 2K ctx (EP72) | same |
| H200 + CX-7 IB (Coreweave) | DeepSeek-R1 | 2.2k tok/s/GPU (vs ~1.5k baseline) | [vllm.ai/blog/large-scale-serving](https://vllm.ai/blog/large-scale-serving) |
| 8× GB200 decode + 4×(2× GB200) prefill | DeepSeek-R1 | 26.2K TPGS prefill, 10.1K TPGS decode (3-5× H200) | [vllm.ai/blog/dsr1-gb200-part1](https://vllm.ai/blog/dsr1-gb200-part1) |

GB200 numbers used NVFP4 dispatch (4× less comm volume vs FP16), weight-offload v2 over NVLink-C2C, new chunk knobs `VLLM_ENABLE_MOE_DP_CHUNK`, `VLLM_MOE_DP_CHUNK_SIZE`, `VLLM_FUSED_MOE_CHUNK_SIZE`.

## Parallelism decision matrix

### Activation density — the first question for MoE

Activation density = `(experts_per_token / total_routed_experts) × 100%`.

| Model | Density | EP verdict |
|---|---|---|
| Llama-4-Maverick | 0.78% (1/128) | **EP hurts 7-12%** — use TP only |
| Llama-4-Scout | 6.25% (1/16) | EP neutral |
| DeepSeek-R1 / V3 | 3.13% (8/256) | EP wins |
| Qwen3-235B-A22B | 6.25% (8/128) | EP wins big |
| Mixtral 8x22B | 25% (2/8) | EP wins |

Rule: enable `--enable-expert-parallel` only when density > 2%.

### Concurrency crossover (AMD 8× MI300X benchmarks, [MoE playbook](https://rocm.blogs.amd.com/software-tools-optimization/vllm-moe-guide/README.html))

| Concurrency | Winner |
|---|---|
| ≤128 | TP (40-86% higher throughput, lower TTFT) |
| 256-512 | Mixed — benchmark both |
| ≥512 | DP (16-47% higher throughput) |

Example: DeepSeek-R1 at concurrency 1024 → DP=8+EP = 7,114 tok/s vs TP=8+EP = 4,838 tok/s (+47%).

### MLA / MQA rule

Models with **single KV head** (DeepSeek-V2/V3/V3.2/R1, Kimi-K2) can't shard KV cache by head dimension. TP duplicates full KV per rank → 84.5 GB/GPU at TP=8. **Rule: DP-attention + EP-MoE**. Partitions KV to ~0.125 GB/GPU/request.

### DeepSeek-V3.2 FlashMLA-Sparse warning

**Avoid TP=8 on H100/H200/B200/B300.** Only 16 heads per rank, padded to 64 → overhead. **Recipe: `DP=8, EP=8, TP=1`** ([DeepSeek-V3.2 recipe](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-V3_2.html), [vllm.ai/blog/deepseek-v3-2](https://vllm.ai/blog/deepseek-v3-2)).

### Supported combinations

| Combination | Supported | Notes |
|---|---|---|
| TP + PP | Yes | Intra-node TP, cross-node PP |
| TP + EP | Yes | EP requires `TP_SIZE × DP_SIZE > 1` |
| TP + DP | Yes | Replicate + distribute |
| EP + DP | Yes | DP-attn + EP-MoE common pattern |
| TP + PP + EP | Yes | DeepSeek / Qwen3 multi-stage |
| TP + EP + DP | Yes | Full 3D parallelism |

### PP rules

- Intra-node NVLink: prefer TP.
- Cross-node / PCIe-only: PP beats TP.
- Multi-node convention: `tensor_parallel_size = GPUs_per_node`, `pipeline_parallel_size = nodes`.
- L40S / no NVLink: PP over TP even within a single node.

## Model-specific recipes

| Model | Recipe | Source |
|---|---|---|
| Llama-4-Scout | 8× H100: TP=8, up to 1M ctx. 8× H200: up to 3.6M ctx. `VLLM_DISABLE_COMPILE_CACHE=1`, `--override-generation-config='{"attn_temperature_tuning": true}'` | [vLLM Llama-4 blog](https://blog.vllm.ai/2025/04/05/llama4.html) |
| Llama-4-Maverick | 8× H100: ~430K ctx, EP=0. 8× H200: 1M ctx, EP=0 | same |
| DeepSeek-V3 (FP8, 128K) | TP=8 + EP, 96 GPUs for Wide-EP | LMSYS |
| DeepSeek-V3.2 | `DP=8, EP=8, TP=1` — see warning | [recipe](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-V3_2.html) |
| Qwen3-Coder-480B-A35B-FP8 | `--max-model-len 131072 --enable-expert-parallel --data-parallel-size 8` | [recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Coder-480B-A35B.html) |
| Kimi-K2 FP8 128K | Smallest = 16 GPUs (2× 8× H800). TP=16 OR DP+EP=16 OR TP=8+PP=2 | [recipe](https://docs.vllm.ai/projects/recipes/en/latest/moonshotai/Kimi-K2.html) |
| Mixtral-8x7B | TP=2, EP=1 (or TP=1, DP=8) | standard |

## Common MoE-specific mistakes (beyond SKILL.md's top 10)

- **`EP = E / TP` must be integer.** For 256 experts, TP=8 → EP=32 (each rank holds 1 expert) or TP=4, EP=64. Fractional → error at init.
- **EP > E** — cannot split 128 experts across 256 ranks; violates expert placement.
- **Skipping `--enable-eplb` at ≥16 GPUs** — hot-expert imbalance caps throughput; recommend 32 redundant experts at scale.

For general top-10 pitfalls (benchmark_moe.py skip, gpu_memory_utilization cap, Llama-4-Maverick EP, DeepSeek-V3.2 TP=8, DeepGEMM M<128 regression), see SKILL.md.
