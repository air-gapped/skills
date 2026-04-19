# Version gates — v0.14 → v0.19.1

Quantization churns fast enough that cached operator knowledge goes stale
within a release cycle. This table is the ground-truth for "what does vLLM
version N support".

Check actual version: `vllm --version`. Release notes: [github.com/vllm-project/vllm/releases](https://github.com/vllm-project/vllm/releases).

## v0.19.1 — 2026-04-18 (patch)

Transformers v5 upgrade + Gemma 4 fixes.

- [PR #39045](https://github.com/vllm-project/vllm/pull/39045) — Gemma 4: support quantized MoE.

## v0.19.0 — 2026-04-03

**Landmark release for quantization**. Run this on any Blackwell fleet.

Quantization:
- [PR #35448](https://github.com/vllm-project/vllm/pull/35448) — Online MXFP8 quantization (MoE + dense).
- [PR #38815](https://github.com/vllm-project/vllm/pull/38815) — `CompressedTensorsW8A8Mxfp8` linear + MoE.
- [PR #39205](https://github.com/vllm-project/vllm/pull/39205) — MXFP8 into `MxFp8LinearKernel`.
- [PR #32929](https://github.com/vllm-project/vllm/pull/32929) — FP8 WoQ kernel abstraction.
- [PR #38092](https://github.com/vllm-project/vllm/pull/38092) — Marlin FP8 for compressed-tensors fix.
- [PR #34577](https://github.com/vllm-project/vllm/pull/34577) — NVFP4 rescale weight scales (fix BF16 dequant underflow).
- [PR #33972](https://github.com/vllm-project/vllm/pull/33972) — NVFP4 Marlin NaN/Inf fp16 fix.
- [PR #39129](https://github.com/vllm-project/vllm/pull/39129) — NVFP4 into `NvFp4LinearKernel`.
- [PR #38148](https://github.com/vllm-project/vllm/pull/38148) — fix NaN from stale FP4 scale padding.
- [PR #38032](https://github.com/vllm-project/vllm/pull/38032) — QeRL online quant composed with quantized reloading.
- [PR #38219](https://github.com/vllm-project/vllm/pull/38219) — CPU W4A16 compressed-tensors.
- [PR #37207](https://github.com/vllm-project/vllm/pull/37207) — XPU compressed-tensor W4A8.
- [PR #36505](https://github.com/vllm-project/vllm/pull/36505) — ROCm AWQ Marlin.
- [PR #37358](https://github.com/vllm-project/vllm/pull/37358) — MXFP8 + DeepGEMM crash fix.
- [PR #39510](https://github.com/vllm-project/vllm/pull/39510) — TRTLLM GEN NVFP4 MoE for non-512-aligned hidden dims.
- [PR #37463](https://github.com/vllm-project/vllm/pull/37463) — MXFP4 W4A4 CUTLASS MoE SM100.
- [PR #38479](https://github.com/vllm-project/vllm/pull/38479) — **TurboQuant 2-bit KV cache**, 4× capacity.

KV cache:
- [PR #33695](https://github.com/vllm-project/vllm/pull/33695) — skip SWA layers with FP8 KV.
- [PR #37054](https://github.com/vllm-project/vllm/pull/37054) — fix FP8 MLA KV gibberish from scale inconsistency.
- [PR #39418](https://github.com/vllm-project/vllm/pull/39418) — fix KV cache scale handling.
- [PR #39002](https://github.com/vllm-project/vllm/pull/39002) — fix FlashInfer crash with `kv_cache_dtype_skip_layers`.
- [PR #37201](https://github.com/vllm-project/vllm/pull/37201) — `--calculate-kv-scales` **deprecated**.
- [PR #37252](https://github.com/vllm-project/vllm/pull/37252) — FlashInfer sparse MLA default for FP8 KV.

Blackwell / B300:
- [PR #37755](https://github.com/vllm-project/vllm/pull/37755) — B300/GB300 (SM 10.3) allreduce fusion default.
- [PR #37756](https://github.com/vllm-project/vllm/pull/37756) — tuned all-reduce.
- [PR #37970](https://github.com/vllm-project/vllm/pull/37970) — optimized SM120 CUTLASS blockwise FP8 GEMM.
- [PR #37725](https://github.com/vllm-project/vllm/pull/37725) — SM12x arch-suffix fix (NVFP4 NaN on desktop Blackwell).
- [PR #38083](https://github.com/vllm-project/vllm/pull/38083) — **DeepGemm E8M0 accuracy fix for Qwen3.5 FP8 on Blackwell**.
- [PR #38730](https://github.com/vllm-project/vllm/pull/38730) — restrict TRTLLM attention to SM100, fix GB300 hang.
- [PR #38126](https://github.com/vllm-project/vllm/pull/38126) — DGX Spark fix.

GPT-OSS:
- [PR #37205](https://github.com/vllm-project/vllm/pull/37205) — router GEMM kernel.
- [PR #30647](https://github.com/vllm-project/vllm/pull/30647) — eliminate padding with FlashInfer MXFP4/MXFP8 MoE.

Dependencies:
- [PR #36988](https://github.com/vllm-project/vllm/pull/36988) — compressed-tensors → 0.14.0.1.

Removals:
- [PR #32700](https://github.com/vllm-project/vllm/pull/32700) — per-tensor-per-channel FP8 removed.
- [PR #36799](https://github.com/vllm-project/vllm/pull/36799) — Sparse24 integration removed.

## v0.18.1 — 2026-03-31 (patch)

Narrow cherry-picks.

## v0.18.0 — 2026-03-20

**Known issue**: degraded accuracy Qwen3.5 with FP8 KV cache on B200 ([#37618](https://github.com/vllm-project/vllm/issues/37618)). Fixed v0.19.

Quantization:
- [PR #35986](https://github.com/vllm-project/vllm/pull/35986) — ModelOpt MXFP8 MoE.
- [PR #33595](https://github.com/vllm-project/vllm/pull/33595) — MXFP4 MoE routing simulation override.
- [PR #35242](https://github.com/vllm-project/vllm/pull/35242) — FP8 LoRA dense kernel.
- [PR #35316](https://github.com/vllm-project/vllm/pull/35316) — ROCm Quark W4A8 MXFP4/FP8 for LinearLayer.
- [PR #36247](https://github.com/vllm-project/vllm/pull/36247) — compressed-tensors fix for DSR1 on MI300x.
- [PR #34695](https://github.com/vllm-project/vllm/pull/34695) — MLA crash with AWQ/GPTQ fix.
- [PR #35849](https://github.com/vllm-project/vllm/pull/35849) — score layer quantization for reranker.
- [PR #36321](https://github.com/vllm-project/vllm/pull/36321) — GLM-4.1V non-default quant.
- [PR #35656](https://github.com/vllm-project/vllm/pull/35656) — FP8 k_scale/v_scale loading for Qwen3-MoE.
- [PR #34732](https://github.com/vllm-project/vllm/pull/34732) — FA4 for MLA prefill.
- [PR #35891](https://github.com/vllm-project/vllm/pull/35891) — FlashInfer Sparse MLA FP8 KV.
- [PR #36307](https://github.com/vllm-project/vllm/pull/36307) — TRTLLM FP8 MoE modular kernel.
- [PR #34597](https://github.com/vllm-project/vllm/pull/34597) — **FP8 KV in Triton MLA decode**.

## v0.17.0 — 2026-03-07

Quantization:
- [PR #30286](https://github.com/vllm-project/vllm/pull/30286) — quantized LoRA adapters.
- [PR #34281](https://github.com/vllm-project/vllm/pull/34281) — **per-head KV cache scales**.
- [PR #34906](https://github.com/vllm-project/vllm/pull/34906) — FP8 MoE bias for GPT-OSS.
- [PR #34448](https://github.com/vllm-project/vllm/pull/34448) — SM100 MXFP8 blockscaled grouped MM and quant kernels.
- [PR #35047](https://github.com/vllm-project/vllm/pull/35047) — mixed precision for ModelOpt.
- [PR #34243](https://github.com/vllm-project/vllm/pull/34243) — Llama-4 attention quant (int8, fp8).
- [PR #33446](https://github.com/vllm-project/vllm/pull/33446) — Sparse24 compressed-tensors fix.
- [PR #35430](https://github.com/vllm-project/vllm/pull/35430) — KV scale loading fix for MLA.
- [PR #34254](https://github.com/vllm-project/vllm/pull/34254) — **compressed-tensors as ground truth** for quant strategies.
- [PR #34301](https://github.com/vllm-project/vllm/pull/34301) — AMD CK backend for MoE.
- [PR #34157](https://github.com/vllm-project/vllm/pull/34157) — dynamic MXFP4 for DSv2 (ROCm).
- [PR #34688](https://github.com/vllm-project/vllm/pull/34688) — bitsandbytes on ROCm.
- [PR #29008](https://github.com/vllm-project/vllm/pull/29008) — GPT-OSS Quark format.
- [PR #35289](https://github.com/vllm-project/vllm/pull/35289) — Qwen3.5 FP8 weight loading fix.
- [PR #35156](https://github.com/vllm-project/vllm/pull/35156) — mlp.gate not quantizable.
- [PR #34130](https://github.com/vllm-project/vllm/pull/34130) — `int4_w4a16` fused_moe tuning.
- [PR #35053](https://github.com/vllm-project/vllm/pull/35053) — FlashInfer integrate mm_mxfp8 in ModelOpt MXFP8.
- [PR #35658](https://github.com/vllm-project/vllm/pull/35658) — amd-quark package added.

NVIDIA:
- [PR #31195](https://github.com/vllm-project/vllm/pull/31195) — SM100 FMHA FP8 prefill for MLA.
- [PR #34424](https://github.com/vllm-project/vllm/pull/34424) — SM120 FP8 GEMM optimization.
- [PR #34924](https://github.com/vllm-project/vllm/pull/34924) — DeepGEMM swapAB default on SM90.

## v0.16.0 — 2026-02-25 (branch cut 2026-02-08)

Quantization:
- [PR #33280](https://github.com/vllm-project/vllm/pull/33280) — FP8 block quant for `CompressedTensorsW8A16Fp8`.
- [PR #33786](https://github.com/vllm-project/vllm/pull/33786) — ModelOpt MXFP8 for dense.
- [PR #33076](https://github.com/vllm-project/vllm/pull/33076) — NVFP4/FP8 on Turing via emulation.
- [PR #31099](https://github.com/vllm-project/vllm/pull/31099) — TP > 4 for FP4 GEMM.
- [PR #31914](https://github.com/vllm-project/vllm/pull/31914) — FP8 online quant memory fix.
- [PR #33200](https://github.com/vllm-project/vllm/pull/33200) — asymmetric W4A16 (ConchLinear).
- [PR #33932](https://github.com/vllm-project/vllm/pull/33932) — DSv3.2 NVFP4 fix.
- [PR #33879](https://github.com/vllm-project/vllm/pull/33879) — LoRA FP8 fix.
- [PR #32728](https://github.com/vllm-project/vllm/pull/32728) — Falcon-H1 loading fix.
- [PR #33257](https://github.com/vllm-project/vllm/pull/33257) — quantized Mamba TP n_groups=1.
- [PR #33582](https://github.com/vllm-project/vllm/pull/33582), [PR #33727](https://github.com/vllm-project/vllm/pull/33727) — CPU W8A8 fixes.

Hardware:
- [PR #32437](https://github.com/vllm-project/vllm/pull/32437) — SM100 INT4 W4A16 kernel.
- [PR #33967](https://github.com/vllm-project/vllm/pull/33967) — FP8 fusion QK Norm+RoPE on B200.
- [PR #32224](https://github.com/vllm-project/vllm/pull/32224) — CUTLASS FP8 blockwise on SM103a.
- [PR #33637](https://github.com/vllm-project/vllm/pull/33637) — CUTLASS MLA on B200 fix.

Removals:
- [PR #32683](https://github.com/vllm-project/vllm/pull/32683) — BitBlas removed.
- [PR #32688](https://github.com/vllm-project/vllm/pull/32688) — Marlin 24 removed.

## v0.15.1 — 2026-02-04 (patch)

Fix regression [#34356](https://github.com/vllm-project/vllm/issues/34356) — FP8 MoE backend regression on Nemotron-3 (present since 0.15.0).

## v0.15.0 — 2026-01-29

Quantization:
- [PR #32285](https://github.com/vllm-project/vllm/pull/32285) — MXFP4 W4A16 compressed-tensors MoE.
- [PR #32257](https://github.com/vllm-project/vllm/pull/32257) — non-gated MoE quant: Marlin, NVFP4 CUTLASS, FP8, INT8, compressed-tensors.
- [PR #31716](https://github.com/vllm-project/vllm/pull/31716) — Intel Quantization Toolkit integration.
- [PR #30141](https://github.com/vllm-project/vllm/pull/30141) — FP8 KV: per-tensor + per-attention-head via llmcompressor.

Hardware:
- [PR #32615](https://github.com/vllm-project/vllm/pull/32615) — Blackwell defaults: FlashInfer MLA default, TRTLLM default prefill.
- [PR #32520](https://github.com/vllm-project/vllm/pull/32520) — FP4 kernel optimization, +65 % on SM100F via 256-bit loads.

Deprecations:
- [PR #32679](https://github.com/vllm-project/vllm/pull/32679) — DeepSpeedFp8 removed.
- [PR #32697](https://github.com/vllm-project/vllm/pull/32697) — RTN removed.
- [PR #32681](https://github.com/vllm-project/vllm/pull/32681) — HQQ deprecated.

Fix:
- [PR #32361](https://github.com/vllm-project/vllm/pull/32361) — DSv3.1 + DeepGEMM incompatible scale shapes.

## v0.14.1 — 2026-01-24

Security / memory leak patch on top of v0.14.0. No quantization changes.

## v0.14.0

- [PR #37776](https://github.com/vllm-project/vllm/pull/37776) — **online quantization redesign** (`fp8_per_tensor` / `fp8_per_block` / `int8_per_channel_weight_only`).
- [PR #31926](https://github.com/vllm-project/vllm/pull/31926) — MXFP4 W4A16 for compressed-tensors dense.
- [PR #31572](https://github.com/vllm-project/vllm/pull/31572) — activation-quantization fix for compressed-tensors W4A16.

## Cross-release upgrade advice

- **Hopper (H100/H200)** — safe to run any version from v0.16 onwards. v0.19 recommended for DeepGEMM E8M0 fix on Qwen3.5.
- **Blackwell (B200/GB200)** — **v0.19+ only** for production. v0.18 had the Qwen3.5 FP8 KV accuracy regression ([#37618](https://github.com/vllm-project/vllm/issues/37618)).
- **Blackwell Ultra (B300/GB300, SM103)** — **v0.19.1 only**. Earlier versions had TRTLLM-attention hang.
- **SM120 / SM121 (RTX 5090 / DGX Spark)** — not a production target; v0.19 fixes arch-suffix but MoE kernel set still incomplete.
- **MI300X / MI355X** — v0.19+ for ROCm AWQ Marlin and NVFP4 emulation.

## Deprecation watch

Watch for removal in v0.20+:

- `experts_int8` — use `int8_per_channel_weight_only`.
- `fbgemm_fp8` — use `fp8`.
- `fp_quant` — deprecated in `__init__.py:50`.
- `awq` (unfused) — use `awq_marlin`.
- `gptq` (unfused) — use `gptq_marlin`.
- `--calculate-kv-scales` — gone in v0.19.
