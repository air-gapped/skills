# Known regressions + vendor quirks

Load when: operator reports perf regression after vLLM upgrade, deploys on AMD/Ascend/XPU, or suspects a vendor-specific bug. Current as of v0.19.0 (April 2026).

## Version regressions

### v0.14.0 → v0.15.1 MiniMax latency regression ([#35048](https://github.com/vllm-project/vllm/issues/35048))

- Model: MiniMax-M2.1 / M2.5
- Median latency **+24%**, P95 TTFT **+73%** (95.9s → 118.9s)
- Throughput 41.7 → 33.6 tok/s per user
- System-wide throughput unchanged — V1 compensates with more concurrent requests at the expense of per-user latency
- **Workaround:** stay on v0.14.0

### v0.13.0 → v0.14.0rc2 GLM-4.7-GPTQ-Int4 MTP regression ([#32547](https://github.com/vllm-project/vllm/issues/32547))

- 96 tps → 87 tps
- Only affects MTP (speculative decoding) path

### v0.9.0.1 → v0.10.0 scheduler regression ([forum](https://discuss.vllm.ai/t/performance-degradation-report-0-9-0-1-vs-0-10-0/1368))

Fixed by enabling `--async-scheduling` in newer versions. If on v0.10+ and seeing throughput drop vs v0.9.0.1, verify async scheduling is actually enabled.

### DeepGEMM M<128 removal → H200 TTFT regression ([#28882](https://github.com/vllm-project/vllm/issues/28882)) — **FIXED 2026-04-21**

Between commits `d83f3f7` and `5a84b76`, the DeepGEMM MoE M<128 restriction was removed. Forces Triton fallback in low-concurrency cases:

- **H200 DeepSeek-R1 EP at concurrency ≤8: 1.5× worse TTFT**
- **Issue closed 2026-04-21** — upgrade to v0.19.1+ or current main; verify the regression is gone for your workload before removing the workaround.
- Legacy workaround (pre-v0.19.1): `VLLM_MOE_USE_DEEP_GEMM=0` + FlashInfer FP8

### v0.19.0rc1 FLUX.1-dev regression ([vllm-omni #2730](https://github.com/vllm-project/vllm-omni/issues/2730))

Not vLLM core but documented here for operators running vllm-omni diffusion: FLUX.1-dev generates incorrect images. Pin v0.18.0. See `vllm-omni` skill.

### Preempt/resume thrashing ([#25538](https://github.com/vllm-project/vllm/issues/25538))

Insufficient token budget at resume triggers immediate re-preemption. Cycles worsen under load. Mitigations: raise `--max-num-batched-tokens`, raise `--swap-space`, or reduce `--max-num-seqs` to reduce competition.

### FULL_AND_PIECEWISE garbage `!!!` output ([#29539](https://github.com/vllm-project/vllm/issues/29539))

Certain config combinations produce nonsense. Workaround: downgrade to `PIECEWISE` via `--compilation-config '{"cudagraph_mode":"PIECEWISE"}'` or `-O1`.

## Vendor quirks

### AMD MI300X

| Issue | Details |
|---|---|
| `VLLM_ROCM_USE_AITER_FP4BMM=True` default crash | MI300X gfx942 has no FP4 hardware. Regression from Jan 15 2026 commit `8c11001`. [#34641](https://github.com/vllm-project/vllm/issues/34641). Set `VLLM_ROCM_USE_AITER_FP4BMM=False` |
| FP8 **slower** than BF16 in steady-state decode | Large MoE (GLM-4.7, MiniMax-M2.1). Counter-intuitive but reproducible. [#31475](https://github.com/vllm-project/vllm/issues/31475) |
| Whisper response inaccurate | [#20069](https://github.com/vllm-project/vllm/issues/20069) |

### AMD MI325X

- Qwen2.5-VL silent 100× slowdown: MIOpen 3D conv "invalid configuration argument". [pytorch #169857](https://github.com/pytorch/pytorch/issues/169857). Need MIOpen patch.

### Huawei Ascend 910B (vllm-ascend)

| Issue | Details |
|---|---|
| Fresh install regression on NPU 910B | [vllm-omni #2898](https://github.com/vllm-project/vllm-omni/issues/2898) |
| 8× 910B serving Qwen3.5-122B-A10B hangs at 8% | running_reqs peaks at ~60 (below configured concurrency), KV drops to 0. [forum](https://discuss.vllm.ai/t/on-8-card-ascend-910b-with-vllm-serving-qwen3-5-122b-a10b-the-client-freezes-at-8-progress-when-running-accuracy-test-as-the-server-stops-receiving-new-requests-after-running-reqs-and-kv-cache-fall-to-0/2538) |
| Async scheduling precision bug on v0.11.0rc2 | [vllm-ascend #4649](https://github.com/vllm-project/vllm-ascend/issues/4649). Disable async-sched on Ascend until fixed |
| HunyuanVideo 1.5 `mindiesd` flash-attn shape | [vllm-omni #2880](https://github.com/vllm-project/vllm-omni/issues/2880) |

### Intel XPU

- torch-xpu 2.6 / ipex-xpu 2.6 oneapi dep conflict — fixed in ipex-xpu 2.7.
- [#28362](https://github.com/vllm-project/vllm/issues/28362): vLLM won't start on Intel 125H Arc.

### FlashInfer backend auto-select bugs

- Hopper FP8 MoE: auto-picks FLASHINFER_CUTLASS when DEEPGEMM would win. [#34249](https://github.com/vllm-project/vllm/issues/34249). Override with `VLLM_USE_DEEP_GEMM=1`.
- NVFP4 MoE on SM120 (RTX PRO 6000 Blackwell): no env-var override for backend choice. [#38971](https://github.com/vllm-project/vllm/issues/38971).
- FlashInfer TRTLLM on SM103 (GB300) hangs on ≥0.6.7. See `vllm-nvidia-hardware` skill. Pin older FlashInfer or use non-TRTLLM backend.

## Published benchmark discrepancies

### SemiAnalysis InferenceMAX / InferenceX

- "tokens-per-MW" metric reported as "generated tokens" but includes processed+generated. [InferenceX #293](https://github.com/SemiAnalysisAI/InferenceX/issues/293).
- Per-GPU disagg throughput comparisons are not apples-to-apples with standard multi-GPU. [#299](https://github.com/SemiAnalysisAI/InferenceX/issues/299).

### Wide-EP throughput numbers

- vLLM Wide-EP H200 blog: 2.2k tok/s/GPU.
- LMSYS EP72 decode on H100: ~22k tok/s/node (= 2.75k tok/s/GPU).
- **Not directly comparable** — different hardware, configs, ISL/OSL mixes.

### async-scheduling default-on timeline

PRs to know:
- [#27614](https://github.com/vllm-project/vllm/issues/27614) — default-on landing
- [#28250](https://github.com/vllm-project/vllm/issues/28250) — follow-up fixes
- [#27679](https://github.com/vllm-project/vllm/issues/27679) — Async Scheduling umbrella tracker (PP, struct-out, spec-dec, MM) — **CLOSED 2025-12-29**, all sub-PRs merged. Verified 2026-04-24.
- [#31679](https://github.com/vllm-project/vllm/issues/31679) — Qwen3-VL + async-sched — **CLOSED 2026-01-07**.

For deployments mixing spec-dec + async-sched with post-upgrade perf drop, verify [#24799](https://github.com/vllm-project/vllm/issues/24799) and [#29821](https://github.com/vllm-project/vllm/issues/29821) fixes landed in the running version.

## Defensive upgrade checklist

Before bumping vLLM version:

1. `git log v<current>..v<target> -- benchmarks/` in the vLLM repo — any new benchmark_moe.py changes?
2. Check release notes for the deployed model family — DeepSeek-V3.2 / Qwen3-MoE / Kimi-K2 / Llama-4 all have fresh-release recipes that may change.
3. Clear `$VLLM_CACHE_ROOT/torch_compile_cache` — stale cache is the single most common upgrade-break.
4. Re-run `auto_tune.sh` for `max_num_seqs × max_num_batched_tokens` — defaults can shift.
5. Run `benchmark_moe.py --tune` if MoE — new kernels may have landed.
6. Verify `/metrics` numbers match pre-upgrade for the same workload before flipping production.
7. Test prefix-cache hit rate hasn't regressed.
8. If on vllm-ascend, pin to last-known-good version.
