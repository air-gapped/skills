---
name: vllm-quantization
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: vLLM datacenter-GPU quantization operator reference — picking, configuring, troubleshooting NVFP4, FP8, MXFP4, MXFP8, AWQ, GPTQ, INT8, compressed-tensors, modelopt, and quark on H100, H200, B200, B300, GB200, GB300. Covers the 29 `--quantization` flag values, KV-cache dtypes (fp8_e4m3, nvfp4, per-token-head, turboquant), MoE backend selection (CUTLASS, TRTLLM, FlashInfer, DeepGEMM, Marlin, Qutlass), producing checkpoints with llm-compressor and NVIDIA ModelOpt (NVFP4_DEFAULT_CFG, FP8_DEFAULT_CFG, W4A16, SmoothQuant+GPTQ), online quantization (`fp8_per_tensor`, `fp8_per_block`), training EAGLE-3 / dflash drafters on BF16 targets before PTQ, and version-gates per vLLM release (v0.14 → v0.19.1).
when_to_use: Trigger on `--quantization`, `--kv-cache-dtype`, NVFP4, MXFP4, MXFP8, FP8, W4A16, W8A8, W4A4, AWQ, GPTQ, SmoothQuant, modelopt, compressed-tensors, quark, torchao, bitsandbytes, gguf, TurboQuant, CUTLASS, Marlin, FlashInfer, TRTLLM, DeepGEMM, Qutlass, Machete, `hf_quant_config.json`, `kv_cache_scheme`, `NVFP4_DEFAULT_CFG`, `FP8_DEFAULT_CFG`, llm-compressor, ModelOpt. Also symptoms "garbage after FP8", "NVFP4 NaN", "FP8 KV multi-turn corruption", "MoE kernel not dispatched on SM120", "illegal memory access awq_marlin", "online FP8 drops bias", "modelopt checkpoint won't load", and decisions between NVFP4 vs FP8 on H200 vs B200, quantizing EAGLE-3 / dflash drafters, and generating a checkpoint vLLM can load.
---

# vLLM quantization — operator skill

For production vLLM operators on **H100 / H200 / B200 / B300 / GB200 / GB300** fleets
deciding which quantization format fits a given target model, producing a
checkpoint vLLM will actually load, wiring the right KV-cache dtype, diagnosing
accuracy or throughput regressions after an upgrade, and composing quantization
with speculative decoding / LoRA / MoE.

Pointer-map format: this SKILL.md picks the format and CLI; the files in
`references/` hold the per-format deep dives, exact source pointers, and
troubleshooting cards. Follow the link, don't paraphrase from memory — the
quantization layer moves faster than any other subsystem in vLLM (six formats
landed in v0.19 alone).

## When quantization wins, when it doesn't

Quantization trades weight precision for memory + compute:

- **KV-capacity bound** (long context, high concurrency) — FP8 or NVFP4 **KV
  cache** gives a 2×/4× KV-capacity multiplier; weight format matters much
  less than getting `--kv-cache-dtype` right. Measure `kv_cache_usage_perc`.
- **Memory-bandwidth bound** (small batch, decode-heavy, 70B+ on < 8 GPUs) —
  weight quantization (NVFP4 / FP8 / W4A16) reduces HBM traffic per token,
  giving 1.5–3× decode throughput on a well-matched target+kernel.
- **Compute bound** (prefill, large batch, small model) — quantization may
  not help; Blackwell FP4 Tensor Cores are the first architecture where
  W4A4 actually beats FP8 in compute-bound regimes. On Hopper, W4A16 is
  memory-only — MMA still runs FP16.
- **Multi-node EP / disaggregated serving** — NVFP4 reduces all-to-all by 4×
  vs BF16. DeepSeek-R1 / V3.2 on GB200/GB300 gets most of its throughput
  from NVFP4 over the fabric, not from per-GPU compute (see vLLM WideEP blog).

**Quantized models are not equivalent to the BF16 original.** Always eval on
actual traffic. Stock NVFP4 checkpoints recover ~99 % at 70B+, ~95–98 % at
7B–14B (Red Hat / NVIDIA numbers). Code / math / agentic workloads hit harder.

## Format selection — pick once per hardware

| GPU | Weight format recommendation | KV cache | Why |
|---|---|---|---|
| H100 / H200 (SM90) | `fp8` (compressed-tensors) or `modelopt` | `fp8_e4m3` | FP8 native Tensor Cores, CUTLASS/Marlin/DeepGEMM all mature |
| H100 / H200, accuracy-critical | `awq_marlin` / `gptq_marlin` (W4A16) | `fp8_e4m3` | Weight-only INT4 with per-group scales — best accuracy at 4-bit |
| H100 / H200, long-context MoE | `fp8` + DeepGEMM block | `fp8_e4m3` | Block FP8 MoE uses DeepGEMM path, lower activation-scale cost |
| B200 / B300 (SM100 / SM103) | `modelopt_fp4` or compressed-tensors NVFP4 | `fp8_e4m3` (NVFP4 KV roadmap #32220) | Blackwell has native FP4 Tensor Cores — NVFP4 wins on both memory AND compute |
| B200 / B300, GPT-OSS | `mxfp4` / `gpt_oss_mxfp4` + `VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8=1` | `fp8_e4m3` | Only vendor-supplied format GPT-OSS ships |
| B200 / B300, lower accuracy risk | `modelopt_mxfp8` or online `fp8_per_block` | `fp8_e4m3` | MXFP8 MoE has the newest kernel set (v0.19), better on shapes NVFP4 struggles with |
| GB10 / DGX Spark (SM121) | `fp8` only (NVFP4/MXFP4 kernels brittle on SM121) | `fp8_e4m3` | See #39761 / #37030 / #34817 — desktop-Blackwell quant kernels are not production ready |
| MI300X / MI355X (ROCm, gfx942/gfx950) | `quark` (AMD) — W4A8 MXFP4/FP8 | `fp8_e4m3` (FNUZ-adjusted) | MI300 needs FNUZ scale adjustment; AMD Quark is the validated path |
| CPU | `cpu_awq` (W4A16) or `torchao` | — | Intel path for laptop / dev |

**Cross-hardware rule of thumb:** produce one `NVFP4` checkpoint per model. It
loads on Blackwell natively and on Hopper via emulation ([PR #35733](https://github.com/vllm-project/vllm/pull/35733), v0.19). A separate `fp8` checkpoint is still worth keeping for older Hopper nodes where the
NVFP4 emulation path is slower.

## The `--quantization` flag values (all 29)

Single dispatch point: [`vllm/model_executor/layers/quantization/__init__.py:107-184`](https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/layers/quantization/__init__.py). Full catalog with file paths, min-capability, kernel map, and notes: `references/formats.md`.

**Production formats (keep in head):**

| Flag | Min SM | Use for |
|---|---|---|
| `fp8` | 89 | Compressed-tensors FP8 W8A8 — the Hopper default |
| `modelopt` | 89 | ModelOpt-exported FP8 (TRT-LLM ecosystem) |
| `modelopt_fp4` | 75 (emulated), 100 (native) | ModelOpt NVFP4 — the Blackwell default |
| `modelopt_mxfp8` | 89 | ModelOpt MXFP8 (MoE + dense) |
| `modelopt_mixed` | 89 | Mixed-precision per-layer checkpoints |
| `compressed-tensors` | varies per scheme | neuralmagic / Red Hat / llm-compressor output |
| `awq_marlin` | 75 | AWQ W4A16 — accuracy-critical INT4 |
| `gptq_marlin` | 75 | GPTQ W4A16 — classic INT4 |
| `mxfp4` / `gpt_oss_mxfp4` | 80 (MoE only on 100) | GPT-OSS ships this |
| `mxfp8` | 80 | Online MXFP8 (v0.19+) |
| `quark` | varies | AMD ROCm path |
| `fp8_per_tensor` / `fp8_per_block` / `int8_per_channel_weight_only` / `online` | 75 | **Online** quantization from BF16 checkpoint — no pre-quant step |

**Deprecated / legacy / narrow:** `awq` (unfused Triton — use `awq_marlin`), `gptq` (unfused — use `gptq_marlin`), `fbgemm_fp8`, `fp_quant`, `experts_int8` (use `int8_per_channel_weight_only`), `moe_wna16`, `bitsandbytes`, `gguf`, `inc` / `auto-round` (Intel), `torchao`, `cpu_awq`.

## KV-cache dtypes (all 11)

Single dispatch: [`vllm/config/cache.py:18-34`](https://github.com/vllm-project/vllm/blob/main/vllm/config/cache.py).

- `auto` — match model weight dtype.
- `fp8`, `fp8_e4m3`, `fp8_e5m2` — the production path. **E4M3 is default**; E5M2 only for ROCm-specific setups.
- `fp8_inc` (Intel), `fp8_ds_mla` (DeepSeek MLA variant).
- `int8_per_token_head`, `fp8_per_token_head` — dynamic per-(token,head) scales computed in-kernel. **No checkpoint scales needed.** Added in [PR #34281](https://github.com/vllm-project/vllm/pull/34281), v0.17.
- `turboquant_k8v4`, `turboquant_4bit_nc`, `turboquant_k3v4_nc`, `turboquant_3bit_nc` — Hadamard-rotated 2-4 bit KV (v0.19, [PR #38479](https://github.com/vllm-project/vllm/pull/38479)).
- `nvfp4` — roadmap, gated on [#32220](https://github.com/vllm-project/vllm/issues/32220).

`--calculate-kv-scales` was **deprecated in v0.19** ([PR #37201](https://github.com/vllm-project/vllm/pull/37201)). Use pre-calibrated scales (LLM Compressor produces them) or let per-token-head scales be computed dynamically.

## Producing a checkpoint

vLLM doesn't quantize — a separate tool does, then vLLM loads the result.
Two production paths exist:

1. **[llm-compressor](https://github.com/vllm-project/llm-compressor)** (vLLM-project) — outputs compressed-tensors format. Preferred for the open ecosystem. Covered in `references/llm-compressor.md`.
2. **[NVIDIA ModelOpt](https://github.com/NVIDIA/TensorRT-Model-Optimizer)** — outputs ModelOpt HF format, also consumable by TRT-LLM and SGLang. Preferred for NVFP4 on Blackwell. Covered in `references/modelopt.md`.

**Quick picker:**

- **FP8 Hopper, no calibration wanted** → llm-compressor `FP8_DYNAMIC` (data-free, ~15 min for a 70B on H100).
- **W4A16 INT4 (AWQ or GPTQ) with best accuracy** → llm-compressor, `AWQModifier` or `GPTQModifier` with 256–512 ultrachat samples.
- **NVFP4 on Blackwell** → ModelOpt `NVFP4_DEFAULT_CFG` or llm-compressor `NVFP4A16` / `NVFP4` scheme (v0.10+).
- **MXFP4 MoE for GPT-OSS-style models** → use the vendor checkpoint as-is, or ModelOpt MXFP4.
- **KV cache FP8 scales for MLA** → llm-compressor `kv_cache_scheme` block with `strategy: tensor` (per-tensor is stable; per-head is experimental — see [#38652](https://github.com/vllm-project/vllm/issues/38652) before enabling on MLA multi-turn).

Both tools output a HF directory vLLM serves with `--quantization compressed-tensors` (llm-compressor) or `--quantization modelopt` / `--quantization modelopt_fp4` (ModelOpt).

## Speculative decoding drafters

**llm-compressor does not train drafters.** ModelOpt does:
`modelopt/torch/speculative/{eagle,dflash,medusa,plugins}/`, examples in
`examples/speculative_decoding/`. Recipes: `modelopt_recipes/general/speculative_decoding/{eagle3,dflash}.yaml`.

**Critical constraint:** ModelOpt recipes assume **BF16 target** — not
validated with an already-NVFP4 target (base wrapped in `torch.no_grad()`,
so quantized target is theoretically workable but unvalidated). The order is:

```
1. Train drafter on BF16 target   (ModelOpt, ~4-12h on 8×H100)
2. Export drafter HF dir          (scripts/export_hf_checkpoint.py)
3. PTQ target to NVFP4 or FP8     (ModelOpt or llm-compressor)
4. (Optional) PTQ drafter too     (small, minimal accuracy cost)
5. Serve both in vLLM             (--quantization modelopt_fp4 --speculative-config '{...}')
```

Medusa / MTP cannot be trained post-hoc — MTP heads are part of the
pretraining (DeepSeek V3, Qwen3-Next, GLM-4.5 MoE, etc.). Full details +
exact commands: `references/modelopt.md` § speculative-decoding.

For spec-dec runtime tuning (acceptance rate metrics, method selection
per target family, chunked-prefill composability) use the separate
`vllm-speculative-decoding` skill — don't duplicate here.

## Online quantization

Introduced by the v0.14 redesign ([PR #37776](https://github.com/vllm-project/vllm/pull/37776)). Quantizes a BF16 checkpoint **at load time**, no pre-quantization step. Trade-off: peak load memory is BF16 size.

```bash
# Per-tensor FP8 (static scales, simplest)
vllm serve meta-llama/Llama-3.1-70B --quantization fp8_per_tensor

# Per-block FP8 (dynamic per-token activation scales)
vllm serve meta-llama/Llama-3.1-70B --quantization fp8_per_block

# Weight-only INT8
vllm serve meta-llama/Llama-3.1-70B --quantization int8_per_channel_weight_only

# YAML-configured
vllm serve meta-llama/Llama-3.1-70B \
  --quantization online \
  --quantization-config-file online.yaml
```

**Known gotchas** — see [#39663](https://github.com/vllm-project/vllm/issues/39663) (drops bias weights), [#34129](https://github.com/vllm-project/vllm/issues/34129) (doesn't split MoE across EP), [#19020](https://github.com/vllm-project/vllm/issues/19020) / [#32029](https://github.com/vllm-project/vllm/issues/32029) / [#32412](https://github.com/vllm-project/vllm/issues/32412) (multiple active RFCs). For any bias-ed or MoE model, prefer a pre-quantized checkpoint.

## The operator-pain-point shortlist

Internalize these before debugging accuracy / throughput regressions:

1. **`--kv-cache-dtype fp8` on MLA models → garbage on multi-turn** ([#38652](https://github.com/vllm-project/vllm/issues/38652)). Unresolved. Avoid on DeepSeek, GLM-4.5/4.6/4.7, Kimi K2 until FP8-KV MLA follow-ups land.
2. **Gemma 4 FP8-block → logit saturation / repetitive garbage** ([#39407](https://github.com/vllm-project/vllm/issues/39407), [#39049](https://github.com/vllm-project/vllm/issues/39049)). Use non-block FP8 or FP16.
3. **NVFP4 on Qwen3-Next / hybrid-attention models** silently corrupts output when `quantization_config.ignore` misses `linear_attn` layers ([#40252](https://github.com/vllm-project/vllm/issues/40252)). Always audit the `ignore` list.
4. **Online FP8 drops bias weights** ([#39663](https://github.com/vllm-project/vllm/issues/39663)). Any bias-ed target → use pre-quantized checkpoint.
5. **Dynamic FP8 + LoRA-merged model on B200 → non-deterministic degenerate output** ([#39662](https://github.com/vllm-project/vllm/issues/39662)). Pin static FP8.
6. **SM120 (RTX 5090, 6000 Pro) is not a datacenter NVFP4 MoE target** ([#35065](https://github.com/vllm-project/vllm/issues/35065), [#31085](https://github.com/vllm-project/vllm/issues/31085)) — full kernel set is SM100 / SM103 only. Desktop Blackwell is production only for `fp8`.
7. **B300 / GB300 (SM103) TRTLLM-attention hang** before v0.19 (fixed by [PR #38730](https://github.com/vllm-project/vllm/pull/38730)). Run v0.19.1+ on GB300.
8. **ModelOpt NVFP4 exports drift from compressed-tensors** (missing `_double_scale`, fused-QKV scale corruption) — [#38980](https://github.com/vllm-project/vllm/issues/38980), [#39764](https://github.com/vllm-project/vllm/issues/39764). Prefer split-QKV checkpoints; validate `ignore` list.
9. **MXFP4 linear not implemented** — MXFP4 is MoE-only in vLLM right now ([`vllm/model_executor/layers/quantization/mxfp4.py:83-88`](https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/layers/quantization/mxfp4.py)). Linear layers fall back to BF16.
10. **TurboQuant attention crashes on A100 when BF16 models use FP8 KV** ([#39992](https://github.com/vllm-project/vllm/issues/39992)). A100 is not a production TurboQuant target.
11. **Qwen3.5 FP8 on B200 degraded-accuracy KV-cache** in v0.18 ([#37618](https://github.com/vllm-project/vllm/issues/37618)). Upgrade to v0.19+.
12. **MXFP8 + DeepGEMM crash** before v0.19 ([PR #37358](https://github.com/vllm-project/vllm/pull/37358)).

Full triage playbook with symptoms → PR → workaround: `references/troubleshooting.md`.

## Version-gate highlights

Full matrix in `references/version-gates.md`. Load-bearing ones:

- **v0.19** — online MXFP8, `CompressedTensorsW8A8Mxfp8`, ROCm AWQ Marlin, TurboQuant KV, DeepGemm E8M0 fix for Qwen3.5 FP8 on Blackwell, `--calculate-kv-scales` deprecation, Gemma 4 quantized MoE, B300 / GB300 fixes.
- **v0.18** — FP8 KV in Triton MLA decode, FlashInfer Sparse MLA FP8, ModelOpt MXFP8 MoE, AMD Quark W4A8 MXFP4/FP8, MLA crash with AWQ/GPTQ fix.
- **v0.17** — per-head KV scales, SM100 MXFP8 kernels, compressed-tensors as ground-truth, ModelOpt mixed precision, Llama-4 attention quant.
- **v0.16** — NVFP4/FP8 on Turing via emulation, TP>4 for FP4 GEMM, ModelOpt MXFP8 dense.
- **v0.15** — MXFP4 W4A16 for compressed-tensors MoE, FP4 kernel optimization (+65 % on SM100F via 256-bit loads).
- **v0.14** — Online quantization redesign, MXFP4 W4A16 for dense.

## What to read next

- `references/formats.md` — per-format deep dive: kernels, config JSON shapes, min-capability, known caveats.
- `references/llm-compressor.md` — recipe cookbook: FP8_DYNAMIC / W4A16 / AWQ / NVFP4A16 / KV-cache FP8 / model-free PTQ commands with exact calibration budgets and output layouts.
- `references/modelopt.md` — ModelOpt PTQ (`hf_ptq.py`) + speculative-decoding training (EAGLE-3, dflash, MTP constraints) + vLLM loader compatibility.
- `references/kernels.md` — kernel × format × SM dispatch map (Marlin / CUTLASS / DeepGEMM / FlashInfer / TRTLLM / Qutlass / Machete / Triton / Exllamav2).
- `references/kv-cache.md` — KV-cache quantization: dtypes, per-token-head scales, attention-backend compatibility, calibration.
- `references/troubleshooting.md` — symptom → known-issue → fix playbook.
- `references/version-gates.md` — release-by-release quantization changes, v0.14 → v0.19.1.

## External references

Load source, not paraphrase:

- vLLM docs: [FP8 W8A8](https://docs.vllm.ai/en/latest/features/quantization/fp8/), [Quantized KV Cache](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/), [AMD Quark](https://docs.vllm.ai/en/stable/features/quantization/quark/).
- vLLM recipes: [index](https://docs.vllm.ai/projects/recipes/en/latest/index.html).
- llm-compressor docs: [index](https://docs.vllm.ai/projects/llm-compressor/en/latest/), [NVFP4 W4A4](https://docs.vllm.ai/projects/llm-compressor/en/latest/examples/quantization_w4a4_fp4/), [Qwen3.5 NVFP4 MoE](https://docs.vllm.ai/projects/llm-compressor/en/latest/key-models/qwen3.5/nvfp4-moe-example/).
- compressed-tensors spec: [`quant_scheme.py`](https://github.com/neuralmagic/compressed-tensors/blob/main/src/compressed_tensors/quantization/quant_scheme.py), [overview](https://deepwiki.com/neuralmagic/compressed-tensors/1-overview).
- NVIDIA: [Introducing NVFP4](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/), [NVFP4 KV cache](https://developer.nvidia.com/blog/optimizing-inference-for-long-context-and-large-batch-sizes-with-nvfp4-kv-cache/), [MoE perf leaps on Blackwell](https://developer.nvidia.com/blog/delivering-massive-performance-leaps-for-mixture-of-experts-inference-on-nvidia-blackwell/).
- Red Hat: [Accelerating LLMs with NVFP4](https://developers.redhat.com/articles/2026/02/04/accelerating-large-language-models-nvfp4-quantization), [LLM Compressor 0.9](https://developers.redhat.com/articles/2026/01/16/llm-compressor-090-attention-quantization-mxfp4-support-and-more), [vLLM FP8 foundational](https://developers.redhat.com/articles/2024/07/15/vllm-brings-fp8-inference-open-source-community).
- vLLM blog: [GPT-OSS on Blackwell](https://blog.vllm.ai/2026/02/01/gpt-oss-optimizations.html), [DeepSeek-R1 WideEP on GB200](https://blog.vllm.ai/2026/02/03/dsr1-gb200-part1.html), [DeepSeek-V3.2 on GB300](https://blog.vllm.ai/2026/02/13/gb300-deepseek.html).
- AMD: [FP8 with Quark for vLLM](https://rocm.docs.amd.com/projects/ai-developer-hub/en/latest/notebooks/gpu_dev_optimize/fp8_quantization_quark_vllm.html), [MXFP4 Llama3.3 with Quark](https://rocm.docs.amd.com/projects/ai-developer-hub/en/latest/notebooks/gpu_dev_optimize/mxfp4_quantization_quark_vllm.html).

When in doubt, read the vLLM source — [`vllm/model_executor/layers/quantization/`](https://github.com/vllm-project/vllm/tree/main/vllm/model_executor/layers/quantization/) is the ground truth, and the quantization layer churns fast enough that cached knowledge rots inside a release cycle.
