# DiT / diffusion stack

Load when the operator is tuning a diffusion model — CFG weights, schedulers, Ulysses/Ring parallelism, TeaCache/Cache-DiT, quantization, LoRA, ComfyUI integration, or debugging why a DiT deployment is slow. Source: `vllm_omni/diffusion/`, `vllm_omni/inputs/data.py` (OmniDiffusionSamplingParams), `vllm_omni/quantization/factory.py`.

**Contents:** Diffusion request shape · Schedulers · Caching (TeaCache/Cache-DiT) · CFG plumbing · Sequence parallelism · Attention backends · Quantization · LoRA + offload · Frame interpolation · verl RL · ComfyUI bridge · Performance sanity check.

## The shape of a diffusion request

Unlike AR generation, DiT runs a **fixed number of denoising steps** against a latent. So the sampling-params analog is `OmniDiffusionSamplingParams`, defined in `vllm_omni/inputs/data.py:211-460` at v0.32.0 (last class in the module). `None` below means "use the pipeline default":

| Field | Default | Purpose |
|---|---|---|
| `num_inference_steps` | `None` (pipeline default, typically 20-50) | Total denoising steps |
| `guidance_scale` | `None` | CFG scale; set > 1.0 to enable |
| `guidance_scale_2` | `None` | **Dual CFG** high-noise branch (Wan2.2) |
| `guidance_rescale` | 0.0 | Pixel-space rescale after CFG |
| `true_cfg_scale` | `None` | Qwen-Image variant of CFG |
| `seed` | None | Reproducibility |
| `generator_device` | `None` | Device for seeded generator |
| `num_outputs_per_prompt` | 1 | Batch per prompt |
| `height`, `width` | `None` (model default) | Image/frame resolution |
| `num_frames`, `fps` | 1, `None` | Video generation (`num_frames=1` for images; fractional fps allowed) |
| `strength` | `None` | I2I denoising fraction (Z-Image) |
| `negative_prompt` | "" | CFG negative branch |
| `do_classifier_free_guidance` | False | Toggle CFG; set when `guidance_scale>1` + negative prompt exists |
| `latents` | None | Pre-seeded latent input |
| `past_key_values`, `kv_metadata` | None | Incoming KV from prior AR stage |
| `cfg_text_past_key_values`, `cfg_img_past_key_values` | None | CFG companion KV branches |
| `cfg_branch_past_key_values` | `None` | Named multi-branch CFG (e.g. `{"text": tuple, "image": tuple}`) |
| `need_kv_receive` | **True** | Block until KV arrives from upstream |
| `vae_use_slicing`, `vae_use_tiling` | False | VAE memory optimizations |
| `layers` | 4 | Layered image output count (2-10, Qwen-Image-Layered) |

CFG gates on `guidance_scale > 1.0`, so `0.5` disables it as well as `0`.

## Schedulers

Primary: **`FlowUniPCScheduler`** — flow-matching UniPC multistep, used across most DiT models. Source: `vllm_omni/diffusion/models/schedulers/scheduling_flow_unipc_multistep.py`.

Model-specific schedulers live in `vllm_omni/diffusion/models/<model>/schedulers.py`. The stage config picks the scheduler; swap only with compatibility verification — scheduler choice affects the accepted `num_inference_steps` range and `guidance_scale` semantics.

## Caching — non-KV analogs for DiT

DiT has no KV cache (no autoregression). Instead, vllm-omni ships several latent-activation caches that skip redundant DiT forward-passes:

| Cache | Source | What it caches |
|---|---|---|
| **TeaCache** | `vllm_omni/diffusion/cache/teacache/` | Token-level activation similarity threshold (reuse last step) |
| **Cache-DiT** | `vllm_omni/diffusion/cache/cachedit/` | Block-level activations across steps. **Directory renamed from `cache_dit/` (no underscore) by PR #5226, 2026-07-24.** |
| **MagCache** | `vllm_omni/diffusion/cache/magcache/` | Added in the same 2026-07-24 cache refactor |
| **StepCache** | `vllm_omni/diffusion/cache/stepcache/` | Added in the same 2026-07-24 cache refactor |
| **SeaCache** | `vllm_omni/diffusion/cache/seacache/` | New in v0.30.0 (Cosmos3, #6922) |
| Latent cache | `latents` field | Pre-seeded initial latent |
| Noise-pred cache | `noise_pred` field | Output cache for duplicate prompts |

Enable with `--cache-backend tea_cache|cache_dit|mag_cache|sea_cache|step_cache` (default `none`) plus `--cache-config`, or the per-stage `cache_backend` / `cache_config` YAML keys. TeaCache is the most-used — gives 1.5-2× speedup on Wan2.2 / FLUX / Qwen-Image at marginal quality cost.

## CFG plumbing (unique to vllm-omni)

Upstream vLLM has **no** classifier-free guidance support — it's an AR framework and CFG is a DiT thing. vllm-omni adds three CFG variants:

1. **Standard CFG** — pair text prompt with negative prompt; run both through the same DiT; `x_guided = x_neg + guidance_scale * (x_pos - x_neg)`. Controlled by `guidance_scale` + `negative_prompt`.

2. **Dual CFG (Wan2.2)** — second CFG branch at high-noise timesteps. Controlled by `guidance_scale_2` + `boundary_ratio`.

3. **Multi-branch CFG** — DiT accepts KV from multiple AR branches (e.g., `text`, `image` for image edit). Implemented via `cfg_branch_past_key_values` dict and `cfg_kv_collect_func` hook in the stage config.

### Paper's prompt-expand flow

The arXiv paper describes a `prompt_expand_func` that duplicates the input prompt into a positive + negative pair, both run through AR concurrently, OmniConnector carries both KV caches to DiT, where `cfg_kv_collect_func` injects them as `cfg_text_past_key_values`. This means one API request → two AR forward-passes → one merged DiT forward (with CFG-parallel).

**CFG-merged-batch TP**: — both CFG branches run in the same batch on the same TP group, instead of separate forwards. Cuts DiT wall-time by ~35% at the cost of 2× activation memory. Enabled automatically for BAGEL; opt-in for other models via stage config.

## Sequence parallelism for DiT

DiT blocks are compute-heavy. vllm-omni adds three sequence-parallel paths:

| Flag | Purpose |
|---|---|
| `--ulysses-degree N` / `--usp N` | Ulysses SP: shard sequence across N GPUs |
| `--ulysses-mode strict` | Strict divisibility (default) |
| `--ulysses-mode advanced_uaa` | UAA path for uneven shapes (Wan2.2 irregular outputs) |
| `--ring-degree N` | Ring attention: ring-reduce across N GPUs |

Ulysses is usually faster; Ring handles longer sequences with less activation memory. They can be composed: `--ulysses-degree 2 --ring-degree 2` = 4-way SP.

Also available via env vars:

- **Sage Attention** — Triton-fused attention for DiT.
- **Ring Attention** — same as `--ring-degree`.

## Attention backends

Selection is platform + model dependent. Default is **FA3** when the platform supports it (H100+); AMD uses **ROCm AITER Flash Attention**; NPU uses **mindiesd** (shape issues on HunyuanVideo-1.5 #2880).

The backend comes from the model default — normally don't override. To override DiT attention: `--diffusion-attention-backend <NAME>` (e.g. `FLASH_ATTN`, `TORCH_SDPA`) or env `DIFFUSION_ATTENTION_BACKEND`; per-role settings via `--diffusion-attention-config`. This does not touch AR-stage attention, which uses vLLM's own selector. `VLLM_ATTENTION_BACKEND` is not read by the diffusion path.

## Quantization — unified framework

Pass the config as JSON on the CLI:

```bash
vllm serve Qwen/Qwen-Image --omni \
  --diffusion-quantization-config '{"method":"fp8","activation_scheme":"dynamic"}'
```

Per-component routing (`ComponentQuantizationConfig`) is a dict keyed by **layer-name prefix** — longest prefix wins — not by role name: `{"transformer": {"method": "fp8"}, "vae": null}`. It is detected only when at least one value is `null` or a dict carrying `method`; a dict of bare strings (`{"transformer": "fp8"}`) raises `must have a 'method' or 'quant_method' key`.

Supported formats (entry point `build_quant_config()`, `vllm_omni/quantization/factory.py:411` at v0.32.0):

| Format | Targeted at | Source PR |
|---|---|---|
| FP8 | Flux family DiT | v0.16 #1640 |
| INT8 | Z-Image, Qwen-Image DiT | v0.18 #1470 |
| ~~GGUF~~ | **moved out of tree in v0.26.0** — install `vllm-project/vllm-gguf-plugin` | v0.16 #1755, removed by #4769 |
| BitsAndBytes W4 (online) | diffusion transformers | v0.26.0 #5037 |
| Transformer Engine FP8 (online) | FLUX.2-dev Mistral text encoder | v0.26.0 #5136 |
| NVFP4, MXFP4 | via upstream vLLM registry | inherited |
| INC / AutoRound | Intel Neural Compressor path | factory delegate |

Build via factory:

```python
from vllm_omni.quantization.factory import build_quant_config
cfg = build_quant_config({"transformer": {"method": "int8"}, "vae": None})
```

**Multi-stage quant gotcha**: a pre-quantized multi-stage checkpoint (modelopt FP8) stores quant config in per-stage sub-configs. `OmniModelArchConfigConvertor` reads `stage_config_name` to route correctly. For hand-quantized checkpoints, set `hf_config_name` per stage or the wrong stage gets quantized.

## LoRA

DiT LoRA is PEFT-compatible. Pass per-request (`/v1/images/generations` body, or `extra_body.lora` on chat):

```json
{
  "model": "Qwen/Qwen-Image",
  "prompt": "...",
  "lora": {
    "name": "my_style",
    "local_path": "/models/lora/my_style_adapter",
    "scale": 0.8
  }
}
```

`local_path` is a PEFT adapter **directory readable on the server**, not a client path or a bare `.safetensors` name; `name` defaults to the path stem, `scale` to 1.0.

At server start: `--lora-path <adapter-or-file...>` with `--lora-backend peft` (default; `--lora-scale` applies) or `--lora-backend distill`, which fuses few-step LoRA `.safetensors` files into the base weights for the server's lifetime (Wan2.2 MoE: high-noise file first, low-noise second). `--enable-lora --lora-modules` are upstream LLM-adapter flags, not the diffusion path.

Combined with ComfyUI bridge, ComfyUI-saved LoRAs load directly.

## DiT LoRA + Offload

**Layerwise CPU offloading** for DiT — transformer blocks swap to/from CPU between timesteps. Saves ~40% VRAM at ~15% throughput cost. Enable on the CLI:

```bash
vllm serve Wan-AI/Wan2.2-T2V-A14B-Diffusers --omni \
  --diffusion-offload-config '{"mode":"layer","components":["dit"]}'
```

`components` takes `dit`, `text_encoder` or both; `"mode":"module"` is whole-model CPU offload. `--enable-layerwise-offload` and `--enable-cpu-offload` are compatibility aliases.

## Frame interpolation (video post-processing)

RIFE-based temporal upsampling, enabled per-request:

```json
{
  "enable_frame_interpolation": true,
  "frame_interpolation_exp": 2,
  "frame_interpolation_scale": 1.0,
  "frame_interpolation_model_path": "/models/rife-v4"
}
```

`exp=1`→2×, `exp=2`→4×, `exp=3`→8× frame rate.

## verl RL / Flow-GRPO

vllm-omni integrates with verl for E2E RL training on Qwen-Image via Flow-GRPO (#1646, #1593, #2005, #2217). Adds collective RPC support + async batching. Not a serving concern, but worth knowing: the same diffusion engine drives training feedback. For RL weight updates into a running server read `docs/user_guide/weight_transfer.md` (v0.32.0); the trainer side lives in the separate `verl-project/verl-omni` repo. There is no `docs/features/verl.md` at v0.30.0 or v0.32.0.

## ComfyUI bridge

vllm-omni can be the backend for ComfyUI's "Remote DiT" nodes. Boot the vllm-omni server normally, then point ComfyUI at `http://host:8091/v1/images/generations`. The bridge supports video and LoRA.

## Performance sanity check

If DiT latency looks wrong:

1. Check `--ulysses-degree` matches GPU count.
2. Confirm TeaCache or Cache-DiT is enabled (stage-config extras).
3. Check quantization is engaging: grep the startup log for `Building quantization config` (logged for single-method configs).
4. Wan2.2 specifically: `guidance_scale_2` + `boundary_ratio` must both be set or dual-CFG no-ops.
5. Blackwell SM100/SM103 paths: some DiT kernels fall back to CUTLASS.
   **Do not pin `flashinfer<0.6.7`** — unsatisfiable on v0.32.0, which
   inherits vLLM 0.32.0's hard `flashinfer-python==0.7.0.post1` (v0.30.0:
   `0.6.18.post1`). The hang that pin worked around hit **GB300 (SM103) only**
   (GB200 / SM100 never) and vLLM fixed it in tree (PR #38730: SM103 falls
   back from TRTLLM attention to the default FlashInfer backend). A TRTLLM
   attention hang on SM103 today is a new bug — capture it, do not downgrade
   FlashInfer.
