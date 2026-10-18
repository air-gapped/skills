---
name: vllm-quantization
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  vLLM datacenter-GPU quantization — picking, configuring, troubleshooting NVFP4, FP8, MXFP4, MXFP8, AWQ, GPTQ, INT8, compressed-tensors, modelopt, quark on H100/H200/B200/B300/GB200/GB300; every `--quantization` flag value, KV-cache dtypes (fp8_e4m3, nvfp4, per-token-head, turboquant), MoE backend selection (CUTLASS, TRTLLM, FlashInfer, DeepGEMM, Marlin, Qutlass), producing checkpoints with llm-compressor and NVIDIA ModelOpt (NVFP4_DEFAULT_CFG, FP8_DEFAULT_CFG, W4A16, SmoothQuant+GPTQ), online quantization (`fp8_per_tensor`, `fp8_per_block`, `nvfp4_per_token`), training EAGLE-3/dflash drafters on BF16 targets before PTQ, version gates per vLLM release (v0.14 → v0.32).
when_to_use: |-
  Trigger on `--quantization`, `--kv-cache-dtype`, W8A8, W4A4, torchao, bitsandbytes, gguf, Machete, `hf_quant_config.json`, `kv_cache_scheme`. Symptoms — "garbage after FP8", "NVFP4 NaN", "FP8 KV multi-turn corruption", "MoE kernel not dispatched on SM120", "illegal memory access awq_marlin", "online FP8 quality drop", "modelopt checkpoint won't load". Decisions — NVFP4 vs FP8 on H200 vs B200, quantizing EAGLE-3/dflash drafters, generating a checkpoint vLLM can load. Also implicit — "quantize {model}", "pick quant for {model}", "audit quantization", "deploy-memo quant", "which quant fits {GPU}", "spec-study quantization".
---

# vLLM quantization — operator skill

Registries, counts and flag values below are re-derived from the **v0.32.0**
tree (2026-10-18); verification dates and citations live in
`references/sources.md`.

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
For the eval itself use the `vllm-benchmarking` skill (vLLM's own harness,
serving-side accuracy + latency) or `aiperf` (vendor-neutral, trace replay and
accuracy benchmarks against any OpenAI-compatible endpoint).

## Format selection — pick once per hardware

| GPU | Weight format recommendation | KV cache | Why |
|---|---|---|---|
| H100 / H200 (SM90) | `fp8` (compressed-tensors) or `modelopt` | `fp8_e4m3` | FP8 native Tensor Cores, CUTLASS/Marlin/DeepGEMM all mature |
| H100 / H200, accuracy-critical | `awq_marlin` / `gptq_marlin` (W4A16) | `fp8_e4m3` | Weight-only INT4 with per-group scales — best accuracy at 4-bit |
| H100 / H200, long-context MoE | `fp8` + DeepGEMM block | `fp8_e4m3` | Block FP8 MoE uses DeepGEMM path, lower activation-scale cost |
| B200 / B300 (SM100 / SM103) | `modelopt_fp4` or compressed-tensors NVFP4 | `fp8_e4m3`, or `nvfp4` (shipped v0.25.0, #42890) | Blackwell has native FP4 Tensor Cores — NVFP4 wins on both memory AND compute |
| B200 / B300, GPT-OSS | `mxfp4` / `gpt_oss_mxfp4` + `VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8=1` | `fp8_e4m3` | Only vendor-supplied format GPT-OSS ships |
| B200 / B300, lower accuracy risk | `modelopt_mxfp8` or online `fp8_per_block` | `fp8_e4m3` | MXFP8 MoE has the newest kernel set (v0.19), better on shapes NVFP4 struggles with |
| GB10 / DGX Spark (SM121) | `fp8` only (NVFP4/MXFP4 kernels brittle on SM121) | `fp8_e4m3` | See #39761 / #37030 / #34817 — desktop-Blackwell quant kernels are not production ready |
| MI300X / MI355X (ROCm, gfx942/gfx950) | `quark` (AMD) — W4A8 MXFP4/FP8 | `fp8_e4m3` (FNUZ-adjusted) | MI300 needs FNUZ scale adjustment; AMD Quark is the validated path |
| CPU | `awq_marlin` (W4A16; `cpu_awq` is gone) or `torchao` | — | Intel path for laptop / dev |

**Cross-hardware rule of thumb:** produce one `NVFP4` checkpoint per model. It
loads on Blackwell natively and on Hopper via emulation ([PR #35733](https://github.com/vllm-project/vllm/pull/35733), v0.19). A separate `fp8` checkpoint is still worth keeping for older Hopper nodes where the
NVFP4 emulation path is slower.

## The `--quantization` flag values (30 at v0.32.0)

Ground truth is the `QuantizationMethods = Literal[...]` block in [`vllm/model_executor/layers/quantization/__init__.py`](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/model_executor/layers/quantization/__init__.py) (`get_quantization_config()` dispatches below it) — grep the symbol, not a line range. Full catalog with file paths, min-capability, kernel map, and notes: `references/formats.md`.

**Production formats (keep in head):**

| Flag | Min SM | Use for |
|---|---|---|
| `fp8` | 89 | Pre-quantized FP8 W8A8 checkpoint — the Hopper default. **v0.31.0+: no longer an online quantizer** ([#53585](https://github.com/vllm-project/vllm/pull/53585)) — on a BF16 checkpoint it warns and redirects to `fp8_per_tensor`; pass `fp8_per_tensor` explicitly |
| `modelopt` | 89 | ModelOpt-exported FP8 (TRT-LLM ecosystem) |
| `modelopt_fp4` | 75 (emulated), 100 (native) | ModelOpt NVFP4 — the Blackwell default |
| `modelopt_mxfp8` | 89 | ModelOpt MXFP8 (MoE + dense) |
| `modelopt_mixed` | 89 | Mixed-precision per-layer checkpoints |
| `compressed-tensors` | varies per scheme | neuralmagic / Red Hat / llm-compressor output |
| `awq_marlin` | 75 | AWQ W4A16 — accuracy-critical INT4 |
| `gptq_marlin` | 75 | GPTQ W4A16 — classic INT4. **v0.30.0 removed group/dynamic activation ordering** ([#54809](https://github.com/vllm-project/vllm/pull/54809)): `g_idx` is ignored and the Marlin/GPTQ/CPU/RDNA3 kernels for it are gone. A checkpoint relying on act-order loses that accuracy recovery silently — prefer `awq_marlin` or `compressed-tensors` there. |
| `mxfp4` / `gpt_oss_mxfp4` | 80 (MoE only on 100) | GPT-OSS ships this |
| `mxfp8` | 80 | Online MXFP8 (v0.19+) |
| `quark` | varies | AMD ROCm path |
| `fp8_per_tensor` / `fp8_per_block` / `int8_per_channel_weight_only` / `online` | 75 | **Online** quantization from BF16 checkpoint — no pre-quant step |

**Deprecated / legacy / narrow:** `fbgemm_fp8` and `fp_quant` are the only two in vLLM's own `DEPRECATED_QUANTIZATION_METHODS` list. `awq` / `awq_marlin` / `auto_awq` all resolve to `AutoAWQConfig` and `gptq` / `gptq_marlin` / `auto_gptq` to `AutoGPTQConfig`: the flag name does not pick the kernel (Marlin on CUDA when the shape allows, else Triton; pin with `--linear-backend`). Also avoid for new work: `experts_int8` (use `int8_per_channel_weight_only`), `moe_wna16`, `inc` (Intel Neural Compressor / AutoRound packing — no longer Intel-only compute: v0.30.0 added CUDA support for AutoRound's 2/3/5/6/7-bit widths via a Humming-kernel fallback, #52890), `torchao`.

**`bitsandbytes` left the tree in v0.28.0** (#43529, listed under Breaking
Changes). It is now the out-of-tree `vllm-bnb-plugin`, so on v0.28.0+ an
existing `--quantization bitsandbytes` deployment needs
`uv pip install vllm-bnb-plugin` rather than a flag change. This is the same shape as `gguf`
moving to `vllm-gguf-plugin` — check the plugin before assuming the flag still
resolves.

**`VLLM_TEST_FORCE_FP8_MARLIN` was removed in v0.29.0** (#52182), superseded
by `--linear-backend` / `--moe-backend`. `VLLM_ROCM_USE_AITER_FP4_ASM_GEMM`
was removed in v0.29.0 (#53141) and **restored in v0.31.0, default off**
(#57055) — set it to `1` to opt back into the AITER W4A4 ASM GEMM. v0.28.0 also
removed the deprecated `calculate_kv_scales` runtime KV-scale calculation
(#49389) and `override_attention_dtype` (#48684).

**v0.30.0 removed the `use_fp4_indexer_cache` alias** (#55353): set
`indexer_kv_dtype` directly on `AttentionConfig` for the DSA sparse-attention
indexer K cache (values `auto` / `bf16` / `fp8` / `mxfp4` / `nvfp4`) —
`use_fp4_indexer_cache = True` used to map to `mxfp4`. The field is gone from
`AttentionConfig`, not just ignored — a config that still sets it is no
longer accepted.

**Gone from the in-tree flag list — do not offer them:**

- `gguf` — **migrated out-of-tree** to [`vllm-gguf-plugin`](https://github.com/vllm-project/vllm-gguf-plugin). `pip install vllm-gguf-plugin` first, then `vllm serve <repo>:Q4_K_M --tokenizer <base-model>`. Still experimental; not a datacenter path.
- `cpu_awq` — **folded into `awq_marlin`** ([PR #43841](https://github.com/vllm-project/vllm/pull/43841), merged 2026-05-28). Use `awq_marlin` on CPU.

**Newer values not in older skill copies:** `humming` (Humming mixed-precision, also a `--linear-backend` / `--moe-backend` value), `deepseek_v4_fp8` (DeepSeek-V4 checkpoint config), `fp8_per_channel` and `nvfp4_per_token` (online shorthands; `nvfp4_per_token` added v0.26.0, [#48538](https://github.com/vllm-project/vllm/pull/48538)).

## KV-cache dtypes (19 at v0.32.0)

Single dispatch: [`vllm/config/cache.py`](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/cache.py) — grep the `CacheDType = Literal[...]` block, not a line range; it has grown every minor.

- `auto` — match model weight dtype, except where the model overrides it: DeepSeek-V3.2 and (v0.32.0+, SM100 only) GLM-5.x `GlmMoeDsaForCausalLM` resolve `auto` to FP8. `float16` / `bfloat16` — pin an explicit unquantized KV dtype; set `bfloat16` to opt out of those defaults.
- `fp8`, `fp8_e4m3`, `fp8_e5m2` — the production path. **E4M3 is default**; E5M2 only for ROCm-specific setups.
- `fp8_inc` (Intel), `fp8_ds_mla` (DeepSeek MLA variant), `nvfp4_ds_mla` (sparse-MLA NVFP4 NoPE + FP8 RoPE, SM100 only).
- `ultraquant_4bit` — ROCm-only 4-bit KV (FP4 E2M1 + UE8M0 per-32 scales, Hadamard-rotated K), ~2× FP8 density (v0.32.0).
- `int4_per_token_head`, `int8_per_token_head`, `fp8_per_token_head` — dynamic per-(token,head) scales computed in-kernel. **No checkpoint scales needed.** Added in [PR #34281](https://github.com/vllm-project/vllm/pull/34281), v0.17.
- `turboquant_k8v4`, `turboquant_4bit_nc`, `turboquant_k3v4_nc`, `turboquant_3bit_nc` — Hadamard-rotated 2-4 bit KV (v0.19, [PR #38479](https://github.com/vllm-project/vllm/pull/38479)).
- `nvfp4` — **shipped, not roadmap.** [#32220](https://github.com/vllm-project/vllm/issues/32220) closed `COMPLETED` 2026-05-04; v0.25.0 landed NVFP4 KV with skip-layers sliding window ([#42890](https://github.com/vllm-project/vllm/pull/42890)). FlashInfer-only: SM100 through TRTLLM; **v0.32.0 added SM80/SM90/SM12x** through the FA2 path (not at head size 64, not with attention sinks). `nvfp4_4over6` (4-over-6 scale selection) stays SM100-only. See `references/kv-cache.md`.

`--calculate-kv-scales` was **deprecated in v0.19** ([PR #37201](https://github.com/vllm-project/vllm/pull/37201)). Use pre-calibrated scales (LLM Compressor produces them) or let per-token-head scales be computed dynamically.

## Producing a checkpoint

vLLM doesn't quantize — a separate tool does, then vLLM loads the result.
Two production paths exist:

1. **[llm-compressor](https://github.com/vllm-project/llm-compressor)** (vLLM-project) — outputs compressed-tensors format. Preferred for the open ecosystem. Covered in `references/llm-compressor.md`.
2. **[NVIDIA ModelOpt](https://github.com/NVIDIA/Model-Optimizer)** — outputs ModelOpt HF format, also consumable by TRT-LLM and SGLang. Preferred for NVFP4 on Blackwell. Covered in `references/modelopt.md`.

**Quick picker:**

- **FP8 Hopper, no calibration wanted** → llm-compressor `FP8_DYNAMIC` (data-free, ~15 min for a 70B on H100).
- **W4A16 INT4 (AWQ or GPTQ) with best accuracy** → llm-compressor, `AWQModifier` or `GPTQModifier` with 256–512 ultrachat samples.
- **NVFP4 on Blackwell** → ModelOpt `NVFP4_DEFAULT_CFG` or llm-compressor `NVFP4A16` / `NVFP4` scheme (v0.10+; current release **0.14.0**, and note the project ships parallel maintenance lines — see `references/llm-compressor.md`).
- **MXFP4 MoE for GPT-OSS-style models** → use the vendor checkpoint as-is, or ModelOpt MXFP4.
- **KV cache FP8 scales for MLA** → llm-compressor `kv_cache_scheme` block with `strategy: tensor` (per-tensor is stable; per-head is still the experimental path).

Both tools output a HF directory vLLM serves with `--quantization compressed-tensors` (llm-compressor) or `--quantization modelopt` / `--quantization modelopt_fp4` (ModelOpt).

## Speculative decoding drafters

**llm-compressor does not train drafters.** ModelOpt does:
`modelopt/torch/speculative/{eagle,dflash,medusa,plugins}/`, examples in
`examples/speculative_decoding/`. Recipes: `modelopt_recipes/general/speculative_decoding/{eagle3,dflash}.yaml`.

**Train the drafter against the BF16 base, never the quantized checkpoint.**
ModelOpt recipes are BF16-target only; an NVFP4 target is untested (the base
runs under `torch.no_grad()`) — treat it as unsupported. An existing
NVFP4/FP8 checkpoint of that same base is kept and served as-is — spec-dec
never requires re-quantizing or discarding it. Verdict on "you can't train
speculators on a quantized model, so re-quantize everything": the first half
is right, the second is wrong. The order is:

```
1. Train drafter on the BF16 base (ModelOpt, ~4-12h on 8×H100)
2. Export drafter HF dir          (scripts/export_hf_checkpoint.py)
3. PTQ target from that BF16 base (ModelOpt or llm-compressor) — skip if a
   quantized checkpoint of that same base already exists
4. (Optional) PTQ drafter too     (small, minimal accuracy cost)
5. Serve both in vLLM:
   vllm serve <nvfp4-target> --quantization modelopt_fp4 \
     --speculative-config '{"method":"dflash","model":"<drafter-dir>","num_speculative_tokens":7}'
   # EAGLE-3: '{"method":"eagle3","model":"<drafter-dir>"}'
```

**Pick the drafter — state the pick, don't leave it to the user:**

| Target | Pick | Reason |
|---|---|---|
| Dense Qwen3 / Qwen3.5 (ModelOpt-validated), online training | **dflash** | ModelOpt ships a Qwen3-8B dflash example; its vLLM results reach acceptance length 3.0–5.1 per MT-Bench category at block size 8 (2.8× at TP=8 on H100) vs EAGLE-3's typical 2.5–3.5 at k=3 |
| MoE (Qwen3-MoE), MLA (DeepSeek-V3, Kimi-K2), offline hidden-state training, or any family without a validated dflash recipe | **EAGLE-3** | ModelOpt dflash has no MoE draft, no MLA KV injection, no offline training |
| Checkpoint ships MTP heads | **mtp** | no training needed |

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

# Fine-grained: per-layer-kind override via --quantization-config (JSON or dotted keys)
vllm serve meta-llama/Llama-3.1-70B \
  --quantization fp8_per_tensor \
  --quantization-config '{"moe":{"activation":"mxfp8"},"ignore":["lm_head"]}'
```

The advanced schema is `{linear: {weight, activation}, moe: {weight, activation},
ignore: [...]}`; `linear` / `moe` also accept a bare shorthand string. Names come
from `QUANT_KEY_NAMES` in `vllm/config/quantization.py`. There is no
`--quantization-config-file` flag and no `global_scheme` key.

**v0.30.0 added `targets`** for per-layer online overrides — a dict of
`{pattern: shorthand}` (exact name, `re:`-prefixed regex, or fnmatch, mapping
to `fp8_per_tensor` / `fp8_per_block` / `fp8_per_channel` / `mxfp8` /
`int8_per_channel_weight_only` / `nvfp4_per_token`), mutually exclusive with
`linear`/`moe`. A layer matching no pattern keeps its checkpoint dtype
([#51285](https://github.com/vllm-project/vllm/pull/51285)):

```bash
vllm serve Qwen/Qwen3.5-35B-A3B --quantization online \
  --quantization-config '{"targets":{"model.layers.0.self_attn.o_proj":"fp8_per_tensor","*mlp.experts*":"mxfp4"}}'
```

**v0.30.0 also let online quantization target the unquantized layers of an
already partially pre-quantized checkpoint**, regardless of its own
`quant_method` (modelopt, compressed-tensors, quark) — the checkpoint's own
method still owns its already-quantized layers
([#51392](https://github.com/vllm-project/vllm/pull/51392)):

```bash
# Adds MXFP8 to the dense linear layers of a Quark checkpoint that only
# ships quantized MoE experts.
vllm serve amd/Qwen3.5-35B-A3B-MXFP4 --quantization-config.linear mxfp8
```

**v0.32.0 can re-quantize already-quantized linear layers** at load time
(dequantize, then apply the online target) — linear only, and only from a
serialized ModelOpt MXFP8 source; other pairs raise
([#55684](https://github.com/vllm-project/vllm/pull/55684)):
`vllm serve <mxfp8-ckpt> --quantization-config.linear fp8_per_channel`.
Checkpoint exclusions are not honored here — exclude via `targets` / `ignore`.

v0.31.0 removed Quark's silent online MXFP4 quantization
([#51800](https://github.com/vllm-project/vllm/pull/51800)): request it through
`--quantization-config` instead.

**Known gotchas** — [#34129](https://github.com/vllm-project/vllm/issues/34129) (doesn't split MoE across EP, closed `NOT_PLANNED` — won't-fix), [#19020](https://github.com/vllm-project/vllm/issues/19020) / [#32029](https://github.com/vllm-project/vllm/issues/32029) / [#32412](https://github.com/vllm-project/vllm/issues/32412) (multiple active RFCs). Dropped bias weights ([#39663](https://github.com/vllm-project/vllm/issues/39663)) is **fixed in v0.21.0** (PR #41424) — below it, a bias-ed target needs a pre-quantized checkpoint; at or above it, never name bias loss as the cause of an online-FP8 quality drop. For MoE models, still prefer a pre-quantized checkpoint.

**Online FP8 quality drop that switching granularity or `ignore` does not move:** granularity is not the cause (FP8 W8A8 on a dense model is near-lossless). Stop tuning online flags. A/B the online run against an offline FP8 checkpoint of the same model, same eval and TP — the publisher's `-FP8` build or llm-compressor `FP8_DYNAMIC` (data-free, minutes) — and serve the offline checkpoint if it recovers.

## The operator-pain-point shortlist

Internalize these before debugging accuracy / throughput regressions:

1. **`--kv-cache-dtype fp8` on MLA models → garbage on multi-turn** ([#38652](https://github.com/vllm-project/vllm/issues/38652)) — **fixed in v0.19.0** (PR #37054, KV-scale inconsistency in FP8 MLA). On v0.19.0+ do not exclude FP8 KV for DeepSeek / GLM / Kimi; measure it. See `references/kv-cache.md` items 1 and 5.
2. **Gemma 4 FP8-block → logit saturation / repetitive garbage** ([#39407](https://github.com/vllm-project/vllm/issues/39407), [#39049](https://github.com/vllm-project/vllm/issues/39049)). Use non-block FP8 or FP16. Both issues and the fix PR (#40391) were stale-closed unfixed — closed is not fixed here.
3. **NVFP4 on Qwen3-Next / hybrid-attention models** silently corrupted output when `quantization_config.ignore` missed `linear_attn` layers ([#40252](https://github.com/vllm-project/vllm/issues/40252), fixed + closed 2026-04-20). The underlying pattern still applies to any new hybrid-attention model: always audit the `ignore` list when quantizing non-standard architectures.
4. **Dynamic FP8 + LoRA-merged model on B200 → non-deterministic degenerate output** ([#39662](https://github.com/vllm-project/vllm/issues/39662)). Pin static FP8.
5. **SM120 (RTX 5090, 6000 Pro) is not a datacenter NVFP4 MoE target** ([#35065](https://github.com/vllm-project/vllm/issues/35065), [#31085](https://github.com/vllm-project/vllm/issues/31085)) — full kernel set is SM100 / SM103 only. Desktop Blackwell is production only for `fp8`.
6. **CUTLASS NVFP4 / MXFP4 MoE under expert parallelism → silently wrong output** before v0.32.0: the CUTLASS FP4 MoE path ignored the EP `expert_map` ([#59042](https://github.com/vllm-project/vllm/pull/59042)). Upgrade to v0.32.0; on older releases with `--enable-expert-parallel`, pin a non-CUTLASS `--moe-backend`.

The hardware-/version-gated traps (B300 TRTLLM hang, ModelOpt-vs-compressed-tensors export drift, MXFP4-linear-falls-back-to-BF16, A100 TurboQuant crash, Qwen3.5 v0.18 KV regression, MXFP8+DeepGEMM pre-v0.19 crash) live in the full triage playbook with symptoms → PR → workaround: `references/troubleshooting.md`.

## Version gates an upgrade acts on

Before any upgrade, read every hop between the installed and target release in
`references/version-gates.md`. Gates not covered elsewhere in this file:

| Gate | Action |
|---|---|
| v0.32.0+ on SM90 | `auto` picks Humming over Marlin for linear and MoE (#56997). Pin `--linear-backend marlin` / `--moe-backend marlin` to A/B a throughput change |
| v0.32.0+ MXFP4 W4A4 checkpoint, no W4A4 MoE kernel | falls back to W4A16 with a warning (#60079) — grep the load log before benchmarking |
| v0.27.0+ | PyTorch 2.13.0 / Triton 3.7.1 / Transformers 5.14.1 (#48155, #49223) — rebuild any custom kernel or plugin image |
| ≤ v0.25.0, NVFP4 multi-GPU, Gemma/Qwen-style RMSNorm | fused allreduce+RMSNorm+quant corrupts output (#48330) — run v0.25.1+ |

## What to read next

- `references/formats.md` — per-format deep dive: kernels, config JSON shapes, min-capability, known caveats.
- `references/llm-compressor.md` — recipe cookbook: FP8_DYNAMIC / W4A16 / AWQ / NVFP4A16 / KV-cache FP8 / model-free PTQ commands with exact calibration budgets and output layouts.
- `references/modelopt.md` — ModelOpt PTQ (`hf_ptq.py`) + speculative-decoding training (EAGLE-3, dflash, MTP constraints) + vLLM loader compatibility.
- `references/kernels.md` — kernel × format × SM dispatch map (Marlin / CUTLASS / DeepGEMM / FlashInfer / TRTLLM / Qutlass / Machete / Triton / Exllamav2).
- `references/kv-cache.md` — KV-cache quantization: dtypes, per-token-head scales, attention-backend compatibility, calibration.
- `references/troubleshooting.md` — symptom → known-issue → fix playbook.
- `references/version-gates.md` — release-by-release quantization changes, v0.14 → v0.32.

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
