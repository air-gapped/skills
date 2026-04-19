# GEMM backends — DeepGEMM, CUTLASS, and FP8/FP4 paths

Load when picking / debugging the matmul kernel path for a vLLM deployment on
Hopper or Blackwell. Companion to the attention-backend × SM matrix in
`vllm-platform-matrix.md` — same kind of matrix, compute-kernel side.

## Two backends to know

| Backend | SM gate | Strongest on | Quantizations |
|---|---|---|---|
| **DeepGEMM** | SM90 (Hopper), SM100 (Blackwell) | FP8 E4M3, E8M0-scaled FP8, blockwise FP8 | FP8 per-tensor, blockwise FP8, MXFP4 (Blackwell) |
| **CUTLASS** | SM80+ (A100+) | W8A8 INT8, FP8 with scales, Marlin 4-bit, NVFP4 (SM120 blockwise v0.12) | INT8 W8A8, FP8 + scales, Marlin GPTQ/AWQ, NVFP4 |

vLLM auto-selects; manual override via env vars below. Selection happens per
operator (attention QKV, MLP, MoE expert) based on `(SM, dtype, weight shape)`.

## When DeepGEMM pays off

DeepGEMM is a **JIT-compiled, shape-specialised** FP8 GEMM backend. It wins on
Hopper / Blackwell when:

- Model is FP8-quantised (E4M3 activations, E5M2 or E4M3 weights).
- Hidden dim is **divisible by 128** — DeepGEMM assumes this for its tile
  layout. Hidden 4096/5120/6144/8192/12288 all OK; odd hiddens fall back to
  cuBLASLt and give up ~10-20% of the DeepGEMM win.
- `torch_dtype` in the model config is `bfloat16` (not float16). FP16 output
  costs an extra rescale.
- Batch sizes are multiples of 8 for tensor-core alignment. Fragmentation at
  BS=7 or BS=13 is the most common "why is it slow" source.

Performance vs cuBLASLt FP8: typically **+15-35%** on decode matmuls, +5-15%
on prefill matmuls (prefill is already compute-saturated).

## When CUTLASS takes over

- Any non-FP8 quant (INT8 W8A8, Marlin 4-bit, NVFP4, AWQ, GPTQ).
- Hoppers with unaligned hidden dims.
- Blackwell SM120 blockwise FP8 GEMM (v0.12 CUTLASS path, PR #37970).
- Gated MoE experts under MXFP4 on SM100 (v0.10.2 CUTLASS fused MoE default).

CUTLASS kernels are AOT-compiled and selected by a heuristic table. Less
flexible than DeepGEMM's JIT, but no warm-up.

## E8M0 scaling — Hopper-only accuracy knob

`VLLM_USE_DEEP_GEMM_E8M0=1` switches FP8 quantisation scale storage from
FP32 to E8M0 (8-bit exponent, no mantissa). This is *faster* (single-byte
scale per tile) but only lossless for FP8 E4M3. Default off.

Turn on when:

- Model is FP8 E4M3 on H100/H200.
- Throughput > accuracy-bit-for-bit (the scale rounding error is <1 ULP per
  block, typically invisible in generation quality).

Leave off (or default) when:

- FP8 E5M2 weights (the exponent-wide format breaks E8M0 assumptions).
- Accuracy-gated eval pipelines (any scale rounding is a confound).

## JIT cache — the first-request warm-up

DeepGEMM compiles kernels on first encounter of a `(shape, dtype)` pair. On
cold start:

1. First request sees 200-800 ms of extra latency per unseen shape.
2. Compiled kernels serialise to `DG_JIT_CACHE_DIR` (default
   `~/.cache/deep_gemm/`).
3. Subsequent restarts with same model + BS distribution hit the cache
   instantly.

Deployment implications:

- **Mount the cache as a PVC** in Kubernetes — otherwise every pod restart
  pays the warm-up tax.
- **Warm up explicitly**: send a few representative-shape requests before
  flipping traffic to the new replica. See `vllm serve --warmup-requests`.
- **Disk space**: typical cache is 50-200 MB per model. Free-tier PVCs
  (≤1 Gi) work; watch disk pressure in multi-model deployments.

## Alignment check — before deployment

```bash
python -c '
import json, sys
cfg = json.load(open(sys.argv[1]))
h = cfg["hidden_size"]
print(f"hidden_size: {h}")
print(f"128-aligned: {h % 128 == 0}")
print(f"torch_dtype: {cfg.get(\"torch_dtype\", \"unset\")}")
' config.json
```

Non-128 hidden → DeepGEMM won't engage for that model; expect CUTLASS
fallback and a ~15-25% throughput gap vs aligned peers.

## Verification at runtime

Confirm DeepGEMM is active and E8M0 is or isn't on:

```bash
python -c "from vllm.utils.deep_gemm import is_deep_gemm_supported; print(is_deep_gemm_supported())"
python -c "from vllm.utils.deep_gemm import is_deep_gemm_e8m0_used; print(is_deep_gemm_e8m0_used())"
```

Both `True` means the env vars are honoured AND the loaded model is
compatible. `True/False` (supported but E8M0 not used) usually means the
model's FP8 format doesn't support the scale shortcut.

## Env vars

Full catalogue of vLLM env vars including DeepGEMM: see
`vllm-configuration` skill's `references/env-vars.md`, section *Compile /
kernel tuning*. Short summary:

| Variable | Default | Purpose |
|---|---|---|
| `VLLM_USE_DEEP_GEMM` | `1` on Hopper | Enable DeepGEMM kernel path for FP8 matmuls |
| `VLLM_USE_DEEP_GEMM_E8M0` | `0` | Enable E8M0 scale packing (Hopper FP8 E4M3 only) |
| `DG_JIT_CACHE_DIR` | `~/.cache/deep_gemm` | Kernel compile cache — mount as PVC |
| `VLLM_ATTENTION_BACKEND` | auto | `FLASHINFER` / `FLASH_ATTN` / `TRITON` — orthogonal to GEMM backend |

## Troubleshooting

### "DeepGEMM initialization failed"

- Missing package: `pip install deep_gemm` (bundled with CUDA builds since
  v0.11).
- Compute capability < 9.0: older cards (A100 SM80) use CUTLASS; DeepGEMM is
  Hopper+.
- Shared-memory allocation refused: container limit too low. DeepGEMM
  kernels need ≥10 GiB shared memory (`--shm-size=10g` on Docker, or the
  pod spec equivalent).

### "Performance didn't improve after setting VLLM_USE_DEEP_GEMM"

- Check hidden-size alignment (above).
- Check `torch_dtype` is bfloat16.
- Check first-request warm-up — if traffic is BS-varied, JIT cache churns.
  Pre-warm with expected shapes.
- BS not a multiple of 8 — tensor core fragmentation.

### "Compatibility problems — some kernels missing"

- Blackwell SM103 (GB300): some DeepGEMM paths not yet present; falls back
  to CUTLASS. Release-notes watch: v0.19+ improved this.
- Mixed precision (bf16 target + fp8 weights): ensure no FP16 coercion in
  the model config.
- Custom model ops (RoPE variants, novel attention): may need
  `VLLM_DISABLE_COMPILE_CACHE=1` + recompile after upgrade.

## Blackwell specifics (SM100 / SM103 / SM120)

Kernel picture differs from Hopper:

- **SM100 (B200)**: full DeepGEMM coverage; NVFP4 via CUTLASS; MXFP4 fused
  MoE via CUTLASS (default from v0.10.2).
- **SM103 (GB300)**: DeepGEMM partial; TRTLLM backend hangs on FlashInfer
  ≥0.6.7 (see `dell-xe.md` for the known-issue list).
- **SM120 (RTX PRO 6000 desktop)**: CUTLASS blockwise FP8 GEMM (v0.19 PR
  #37970); NVFP4 NaN fix v0.19 (#37725).
- **FP4 KV cache** pairing: FP4-quantised KV cache (early-production) uses
  the same CUTLASS path; throughput gain comes from HBM BW reduction, not
  GEMM speed.

## When GEMM backend choice doesn't matter

- Prefill-dominated workloads under long context — attention backend
  dominates. Optimise `FLASHINFER` / `FLASH_ATTN` / `TRITON` selection
  first.
- MoE-heavy serving with low active-experts-per-token — fused MoE kernel
  choice matters more than GEMM backend for MLP portion.
- Very small models (<3B) at BS<4 — everything is compute-saturated; GEMM
  optimisation returns ~few %.

In all three, `vllm-benchmarking`'s A/B sweep methodology is the right tool
to confirm whether tuning GEMM backend is worth the operator-minute cost.

## References

- DeepGEMM repo: <https://github.com/deepseek-ai/DeepGEMM>
- CUTLASS: <https://github.com/NVIDIA/cutlass>
- vLLM kernel source: `vllm/model_executor/layers/quantization/` (FP8, INT8,
  Marlin, NVFP4, MXFP4 modules)
- Batch-invariant torch.compile + DeepGEMM: v0.11.1 release notes
- SM120 CUTLASS blockwise FP8: v0.19 release notes (PR #37970)
