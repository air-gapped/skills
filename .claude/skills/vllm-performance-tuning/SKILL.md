---
name: vllm-performance-tuning
description: |-
  vLLM performance-tuning operator reference — tuning workflow (baseline → bottleneck → knob → re-bench), fused-MoE kernel autotune (`benchmark_moe.py` generates `E=N,N=M,device_name=X.json` configs), DeepEP all-to-all + expert parallelism + EPLB, CUDA graph modes (FULL_AND_PIECEWISE default), torch.compile AOT + compile cache, scheduler knobs (`--max-num-batched-tokens`, `--max-num-seqs`, `--async-scheduling`), TP/EP/DP/PP decision tree, NCCL/DCGM on H100/H200/B200/GB200, PD disaggregation (Nixl/Mooncake/LMCache), known regressions + vendor quirks (v0.14→0.15.1 MiniMax, MI300X FP8<BF16, DeepGEMM M<128 TTFT).
when_to_use: |-
  Trigger on vLLM perf tuning, throughput/latency/goodput optimization, MoE deployment on new hardware, bringing up new GPU SKU (B200/B300/GB200/MI325X/Jetson Thor/RTX Pro Blackwell). Keywords — `benchmark_moe.py`, `VLLM_TUNED_CONFIG_FOLDER`, `VLLM_ALL2ALL_BACKEND`, `VLLM_USE_DEEP_GEMM`, `VLLM_USE_AOT_COMPILE`, `VLLM_ENABLE_MOE_DP_CHUNK`, DeepEP, DeepGEMM, EPLB, `--enable-expert-parallel`, `--enable-eplb`, `--enable-dbo`, `--cudagraph-capture-sizes` (formerly `--cuda-graph-sizes`), `--performance-mode`, `--watermark`, Wide-EP, MLA, PD disagg. Narrow — "tune MoE for B200", "TP vs EP for MoE", "MoE slow", "async scheduling broke latency". Also implicit — "vllm is slow", "why low TPS", "throughput too low", "TTFT too high", "tune model X", "perf regression after upgrade", "audit perf", "deploy-memo perf targets". NOT for measuring (→ `vllm-benchmarking`). NOT for KV cache (→ `vllm-caching`).
---

# vLLM performance tuning

Target: operators deploying models on new hardware, chasing throughput / latency / goodput SLOs, or diagnosing perf regressions. Verified against **v0.32.0** (2026-10-18), the latest stable.

Companion skills: `vllm-benchmarking` (measure), `vllm-caching` (KV), `vllm-nvidia-hardware` (GPU/GEMM), `vllm-configuration` (env vars), `vllm-observability` (metrics).

## Tuning levers (apply by goal, not in fixed order)

**Always first — characterize the workload.** ISL / OSL / req/s / concurrency / SLO (P95 TTFT, P95 TPOT, P95 ITL). "Goodput" = tok/s/GPU **under SLO**, not raw tok/s. Everything below is keyed off these numbers.

**Parallelism + MoE kernels (biggest single wins):**
- **Pick parallelism** (see `references/moe-and-ep.md`) — model-fits-1-GPU → TP=1 + replicas (DP); MoE MLA (DeepSeek/Kimi-K2) → DP-attn + EP; multi-node → TP intra + PP inter OR Wide-EP.
- **MoE on a new SKU → run `benchmark_moe.py --tune`** — generates `E=*,N=*,device_name=*.json` configs. Without tuned configs vLLM logs "Using default MoE config. Performance might be sub-optimal!" = 20-40% throughput loss.
- **Wide-EP** (`--enable-expert-parallel --enable-eplb --enable-dbo`) for DeepSeek/Qwen3/Kimi-K2 at ≥16 GPUs.

**Throughput / batching:**
- **`auto_tune.sh`** (`benchmarks/auto_tune/`) sweeps `max_num_seqs × max_num_batched_tokens`.
- **`--gpu-memory-utilization`** — raise from 0.90 toward 0.95 until steady OOM margin, then back off. MoE: cap at 0.85 (all-to-all buffers not in accounting).
- **Chunked prefill (on by default where supported)** — raise `--max-num-batched-tokens` if TTFT > SLO; lower if ITL > SLO. The default is gated on **both** device memory and entrypoint (`vllm/engine/arg_utils.py`, v0.32.0):

  | Device | `vllm serve` (OpenAI API) | Offline `LLM(...)` |
  |---|---|---|
  | ≥160 GiB (B200/B300) | 16384 / seqs 1024 | 16384 / seqs 1024 |
  | ≥70 GiB non-A100 (H100/H200) | **8192** / seqs 1024 | 16384 / seqs 1024 |
  | everything else, incl. A100 | 2048 / seqs 256 | 8192 / seqs 256 |

  **On H100/H200 the `vllm serve` default is still 8192.** v0.28.0's "raised from 8192 to 16384" note (#51726) applies only to the offline path and the new ≥160 GiB tier. TPU chips have their own smaller table (V6E 1024, V5E 512, V5P lower still, on the serving path).
- **`--performance-mode {balanced,interactivity,throughput}`** — one flag for the whole posture; try it before hand-tuning the batching pair.

**Latency / graph + compile:**
- **CUDA graphs** — keep `FULL_AND_PIECEWISE` (default); the flag is now `--cudagraph-capture-sizes` / `--max-cudagraph-capture-size`, and the generated cap already tracks `min(max_num_seqs × (1+spec_tokens) × 2, ceiling)` — ceiling **1024 on SM100 (B200/B300/GB200)**, 512 elsewhere.
- **`--async-scheduling`** — auto-on unless: pooling model, a spec method other than EAGLE/MTP/draft-model/GPU n-gram/DSpark/DFlash, `disable_padded_drafter_batch`, PP>1 on Model Runner V1, or an executor without support.
- **Compile cache** — pre-bake `$VLLM_CACHE_ROOT/torch_compile_cache` on a representative pod; mount as PVC / bake into OCI layer.

**Distributed (last resort, only when the lever above is exhausted):**
- **NCCL** — on well-configured clouds do nothing. Bare-metal IB: `NCCL_IB_HCA`, `NCCL_IB_GID_INDEX`, `NCCL_NET_GDR_LEVEL`. Never `NCCL_CUMEM_ENABLE=0` on GB200.
- **PD disagg** — reach for only after the above are exhausted and prefill interference is the actual bottleneck.

## Triage tree ("why is it slow")

From Red Hat's 5-step triage ([2026-03-09](https://developers.redhat.com/articles/2026/03/09/5-steps-triage-vllm-performance)):

| Symptom | Look at | Common cause |
|---|---|---|
| TTFT high, queue empty | compute-bound prefill | chunked-prefill budget too low, no prefix cache, bad parallelism |
| TTFT high, queue growing | capacity | raise replicas, raise `max_num_seqs`, check preemption rate |
| TPOT high, TTFT fine | decode-bound | MoE kernel not tuned, wrong attention backend, async sched off |
| ITL spikes | CUDA-graph miss | batch sizes fall outside captured buckets |
| Preemptions climbing | KV thrashing | raise `--watermark`, lower `--max-num-seqs`, or add replicas (`--swap-space` is gone — V1 always recomputes) |
| `num_running` < configured concurrency | scheduler stall | check async-sched blockers, multimodal path, structured output |

**DCGM signals** (not `GPU_UTIL`): `DCGM_FI_PROF_SM_OCCUPANCY`, `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE`. Low tensor-core active on a GEMM-bound workload = memory-bound.

## Quick-answer router

**MoE tuning + expert parallelism + DeepEP + EPLB + parallelism decision matrix** → `references/moe-and-ep.md`

**Scheduler knobs + CUDA graphs + torch.compile + compile cache** → `references/scheduler-and-compile.md`

**NCCL / InfiniBand / DCGM + PD disaggregation (Nixl/Mooncake/LMCache)** → `references/distributed.md`

**Known regressions + vendor quirks (AMD / Ascend / XPU) + per-minor execution-path changes + upgrade checklist** → `references/regressions.md`

**Full citation anchors** → `references/sources.md`

## Top 10 operator mistakes this skill exists to prevent

1. **Not running `benchmark_moe.py` on a new GPU SKU.** Shipped configs cover common combos (H100, H200, A100, MI300X for Mixtral). B200 / B300 / GB200 / MI325X / Jetson Thor / RTX Pro Blackwell almost always need re-tuning. Symptom: `Using default MoE config. Performance might be sub-optimal!` in logs. Fix: `python benchmarks/kernels/benchmark_moe.py --model <moe-model> --tp-size <N> --enable-expert-parallel --tune --save-dir ./configs`, then `export VLLM_TUNED_CONFIG_FOLDER=./configs`. Expected: 20-40% throughput recovery.

2. **`gpu_memory_utilization=0.95` on MoE.** All-to-all staging buffers (DeepEP, NVSHMEM) aren't in the memory accountant. OOM at high concurrency. Fix: cap at 0.85 for MoE, 0.92 for dense.

3. **TP not divisible by head count.** Model has 32 heads, TP=7 → shape mismatch. Rule: `num_heads % TP == 0` AND `hidden_size % TP == 0`.

4. **DeepSeek-V3.2 at TP=8 on H100/H200/B200/B300.** FlashMLA-Sparse only uses 16 heads per rank, padded to 64 → overhead. Fix: `DP=8, EP=8, TP=1`. ([DeepSeek-V3.2 recipe](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-V3_2.html))

5. **Llama-4-Maverick with `--enable-expert-parallel`.** Activation density 0.78% (1/128) — AllToAll overhead exceeds parallelism win. **EP hurts 7-12%** vs TP-only for Maverick. DeepSeek-R1 (3.13%) and Qwen3-235B (6.25%) benefit from EP. Rule: only enable EP when `(experts_per_token / total_experts) > 2%`.

6. **MLA model with TP=8.** Single KV head, TP duplicates ~84.5 GB KV cache per rank. Fix: DP-attention + EP-MoE splits KV to ~0.125 GB/GPU/request.

7. **`--async-scheduling` with unsupported path.** Structured outputs (fixed #26866), spec-dec (#24799 fixed), PP/struct-out/spec-dec/MM umbrella tracker #27679 closed 2025-12-29 — all sub-PRs merged. Remaining hard limit: Model Runner V1 + PP>1 auto-disables it, and forcing it on there with structured output is rejected at startup (v0.31.0+). The vllm-ascend v0.11.0rc2 precision bug (#4649) is fixed — **closed 2026-03-13**; upgrade rather than disabling async-sched. Symptom: stall, latency regression, or precision loss. Fix: upgrade; disable only after reproducing the issue on the running version.

8. **Shipping `VLLM_MOE_USE_DEEP_GEMM=1` blindly on H200.** Between `d83f3f7` and `5a84b76` the DeepGEMM MoE M<128 restriction was removed; H200 DeepSeek-R1 EP at concurrency ≤8 regressed 1.5× TTFT. **[#28882](https://github.com/vllm-project/vllm/issues/28882) was bot-closed 2026-04-21 with no fix** — treat it as open. Keep `VLLM_MOE_USE_DEEP_GEMM=0` + FlashInfer FP8 for low-concurrency decode; drop the override only after measuring TTFT at concurrency ≤8 on the running build.

9. **Skipping compile cache on K8s.** First-pod torch.compile = 5-15 min on large models. Fix: pre-bake `$VLLM_CACHE_ROOT/torch_compile_cache` on one pod, mount as PVC / OCI layer. Llama-4 specifically needs `VLLM_DISABLE_COMPILE_CACHE=1` — stale-cache bug.

10. **`NCCL_CUMEM_ENABLE=0` on GB200.** Disables multi-node NVLink, forces TCP/IB fallback. Nvidia's rule: **"users should not need to tune NCCL environment variables"** on modern clouds. GB200 set `NCCL_NET_GDR_C2C=1`. PR [#16992](https://github.com/vllm-project/vllm/pull/16992) fixed vLLM's defaults.

## Operator cheat sheet

### MoE tune on new hardware (canonical recipe)

```bash
# Step 1 — run the tuner (uses Ray to parallelize across local GPUs)
python benchmarks/kernels/benchmark_moe.py \
  --model deepseek-ai/DeepSeek-V3 \
  --tp-size 8 --enable-expert-parallel --dtype fp8_w8a8 \
  --tune --save-dir ./moe_configs

# Step 2 — point vLLM at the configs
export VLLM_TUNED_CONFIG_FOLDER=./moe_configs

# Step 3 — serve + verify no "default MoE config" warning in logs
vllm serve deepseek-ai/DeepSeek-V3 --tensor-parallel-size 8 \
  --enable-expert-parallel --enable-eplb --enable-dbo \
  --gpu-memory-utilization 0.85
```

### Parallelism first-pick table

| Model family | Small-scale | Large-scale (≥16 GPUs) |
|---|---|---|
| Dense (Llama, Qwen3-dense) | TP=N, DP=replicas | TP=8 intra-node + PP=nodes OR TP=8 + DP=N |
| MoE non-MLA (Mixtral, Qwen3-MoE) | TP=N, EP off | TP + EP: EP = E / TP |
| MoE MLA (DeepSeek-V3/R1, Kimi-K2) | DP=N + EP | Wide-EP: DP-attn + EP-MoE, `--enable-eplb` |
| Llama-4-Maverick (0.78% density) | TP only | TP only (EP hurts) |
| DeepSeek-V3.2 (FlashMLA-Sparse) | DP=8, EP=8, TP=1 | same |

Concurrency crossover (8× MI300X benchmarks): ≤128 concurrent → TP wins, ≥512 → DP wins, 256-512 mixed. ([AMD MoE playbook](https://rocm.blogs.amd.com/software-tools-optimization/vllm-moe-guide/README.html))

### Scheduler first-pass by workload

| Scenario | `max_num_batched_tokens` | `max_num_seqs` | Other |
|---|---|---|---|
| Throughput-heavy (batch decode) | 4096-16384 | 256-512 | async sched on |
| Latency-heavy (chat) | 1024-2048 | 64-128 | async sched on, `--stream-interval 1` |
| Long-context RAG | 8192-16384 | 32-64 | `--enable-prefix-caching`, `--long-prefill-token-threshold` |
| Wide-EP DeepSeek | 8192 | 256 | `--enable-expert-parallel --enable-eplb --enable-dbo`, `FULL_AND_PIECEWISE` |

### Compile-level shorthand

| Flag | Effect |
|---|---|
| `-O0` | No compile, no CUDA graphs. `--enforce-eager` = `-O0` **plus no JIT kernel warmup** (v0.31.0+, unless fault tolerance is on) |
| `-O1` | Simple compile + PIECEWISE graphs |
| **`-O2`** | **default** — full compile + `FULL_AND_PIECEWISE` + fusions (AllReduce+RMSNorm +15%, Attention+Quant FP8 +7%; the compile-pass SP+Async-TP is gone in v0.32.0) |
| `-O3` | reserved (currently = `-O2`) |

### Upgrading across v0.22.0 → v0.32.0

Re-benchmark after crossing any minor in this range; do not compare against numbers taken before it. Per-minor execution-path changes and the config keys that now fail validation → `references/regressions.md` §"Execution-path changes by minor".

## Source policy

Citations and refresh triggers: `references/sources.md`. Two standing rules when checking any claim here against a live build:

- **A `CLOSED` issue is unfixed until its closing comment names a fix PR.** Several regressions this skill tracks were closed `NOT_PLANNED` by the inactivity bot; their workarounds still apply.
- **A flag named here may no longer exist on a newer tag.** Grep `vllm/config/*.py` and `vllm/engine/arg_utils.py` at the running tag before putting it in serve args; a removed flag is a startup failure.
