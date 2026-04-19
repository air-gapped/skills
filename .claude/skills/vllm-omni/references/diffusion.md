# DiT / diffusion stack

Load when the operator is tuning a diffusion model — CFG weights, schedulers, Ulysses/Ring parallelism, TeaCache/Cache-DiT, quantization, LoRA, ComfyUI integration, or debugging why a DiT deployment is slow. Source: `vllm_omni/diffusion/`, `vllm_omni/inputs/data.py` (OmniDiffusionSamplingParams), `vllm_omni/quantization/factory.py`.

## The shape of a diffusion request

Unlike AR generation, DiT runs a **fixed number of denoising steps** against a latent. So the sampling-params analog is `OmniDiffusionSamplingParams`, defined in `vllm_omni/inputs/data.py:174-300`:

| Field | Default | Purpose |
|---|---|---|
| `num_inference_steps` | model-specific (20-50) | Total denoising steps |
| `guidance_scale` | 0.0 (sentinel "unset") | CFG scale; set > 1.0 to enable |
| `guidance_scale_2` | 0.0 | **Dual CFG** high-noise branch (Wan2.2) |
| `guidance_rescale` | 0.0 | Pixel-space rescale after CFG |
| `true_cfg_scale` | 1.0 | Qwen-Image variant of CFG |
| `seed` | None | Reproducibility |
| `generator_device` | `"cuda"` | Device for seeded generator |
| `num_outputs_per_prompt` | 1 | Batch per prompt |
| `height`, `width` | model-default | Image/frame resolution |
| `num_frames`, `fps` | n/a for images | Video generation |
| `strength` | 1.0 | I2I denoising fraction (Z-Image) |
| `negative_prompt` | "" | CFG negative branch |
| `do_classifier_free_guidance` | auto | Toggle CFG; auto-true when `guidance_scale>1` + negative prompt exists |
| `latents` | None | Pre-seeded latent input |
| `past_key_values`, `kv_metadata` | None | Incoming KV from prior AR stage |
| `cfg_text_past_key_values`, `cfg_img_past_key_values` | None | CFG companion KV branches |
| `cfg_branch_past_key_values` | dict | Named multi-branch CFG (e.g. `{"text": tuple, "image": tuple}`) |
| `need_kv_receive` | False | Block until KV arrives from upstream |
| `vae_use_slicing`, `vae_use_tiling` | False | VAE memory optimizations |
| `layers` | None | Layered image output count (3-10, Qwen-Image-Layered) |

**Sentinel gotcha**: `guidance_scale=0.0` is treated as "not provided". Passing `0.5` is coerced to 1.0 (CFG disabled). To intentionally disable CFG, leave unset; to enable, pass > 1.0.

## Schedulers

Primary: **`FlowUniPCScheduler`** — flow-matching UniPC multistep, used across most DiT models. Source: `vllm_omni/diffusion/models/schedulers/scheduling_flow_unipc_multistep.py`.

Model-specific schedulers live in `vllm_omni/diffusion/models/<model>/schedulers.py`. The stage config picks the scheduler; swap only with compatibility verification — scheduler choice affects the accepted `num_inference_steps` range and `guidance_scale` semantics.

## Caching — non-KV analogs for DiT

DiT has no KV cache (no autoregression). Instead, vllm-omni ships several latent-activation caches that skip redundant DiT forward-passes:

| Cache | Source | What it caches |
|---|---|---|
| **TeaCache** | `vllm_omni/diffusion/cache/teacache/` | Token-level activation similarity threshold (reuse last step) |
| **Cache-DiT** | `vllm_omni/diffusion/cache/cache_dit/` | Block-level activations across steps |
| Latent cache | `latents` field | Pre-seeded initial latent |
| Noise-pred cache | `noise_pred` field | Output cache for duplicate prompts |

Enable via stage-config extras or per-request `OmniDiffusionSamplingParams`. TeaCache is the most-used — gives 1.5-2× speedup on Wan2.2 / FLUX / Qwen-Image at marginal quality cost.

## CFG plumbing (unique to vllm-omni)

Upstream vLLM has **no** classifier-free guidance support — it's an AR framework and CFG is a DiT thing. vllm-omni adds three CFG variants:

1. **Standard CFG** — pair text prompt with negative prompt; run both through the same DiT; `x_guided = x_neg + guidance_scale * (x_pos - x_neg)`. Controlled by `guidance_scale` + `negative_prompt`.

2. **Dual CFG (Wan2.2)** — second CFG branch at high-noise timesteps. Controlled by `guidance_scale_2` + `boundary_ratio`.

3. **Multi-branch CFG** — DiT accepts KV from multiple AR branches (e.g., `text`, `image` for image edit). Implemented via `cfg_branch_past_key_values` dict and `cfg_kv_collect_func` hook in the stage config.

### Paper's prompt-expand flow

The arXiv paper describes a `prompt_expand_func` that duplicates the input prompt into a positive + negative pair, both run through AR concurrently, OmniConnector carries both KV caches to DiT, where `cfg_kv_collect_func` injects them as `cfg_text_past_key_values`. This means one API request → two AR forward-passes → one merged DiT forward (with CFG-parallel v0.16 #1293).

v0.16 added **CFG-merged-batch TP** — both CFG branches run in the same batch on the same TP group, instead of separate forwards. Cuts DiT wall-time by ~35% at the cost of 2× activation memory. Enabled automatically for BAGEL; opt-in for other models via stage config.

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

- **Sage Attention** (v0.12 #243) — Triton-fused attention for DiT.
- **Ring Attention** (v0.12 #273) — same as `--ring-degree`.

## Attention backends

Selection is platform + model dependent. v0.14 defaults to **FA3** when the platform supports it (H100+); v0.14 added **ROCm AITER Flash Attention** (#941) for AMD; NPU uses **mindiesd** (shape issues on HunyuanVideo-1.5 #2880).

The backend is set in stage config or model default — normally don't override. To override: `VLLM_ATTENTION_BACKEND=FLASH_ATTN|FLASHINFER|TRITON`.

## Quantization — unified framework (v0.18 #1764)

Per-component quant via `ComponentQuantizationConfig`. The DiT and text encoder can use different methods:

```yaml
engine_args:
  quantization_config:
    dit: "int8"          # DiT UNet weights INT8
    text_encoder: "fp8"   # Text encoder FP8
    vae: "none"           # VAE stays full precision
    default: "int8"       # Anything else
```

Supported formats (factory `vllm_omni/quantization/factory.py:138-178`):

| Format | Targeted at | Source PR |
|---|---|---|
| FP8 | Flux family DiT | v0.16 #1640 |
| INT8 | Z-Image, Qwen-Image DiT | v0.18 #1470 |
| GGUF | Qwen-Image DiT (llama.cpp-compatible) | v0.16 #1755 |
| NVFP4, MXFP4 | via upstream vLLM registry | inherited |
| INC / AutoRound | Intel Neural Compressor path | factory delegate |

Build via factory:

```python
from vllm_omni.quantization.factory import build_quant_config
cfg = build_quant_config({"dit": "int8", "text_encoder": "fp8"})
```

**Multi-stage quant gotcha**: a pre-quantized multi-stage checkpoint (modelopt FP8) stores quant config in per-stage sub-configs. `OmniModelArchConfigConvertor` reads `stage_config_name` to route correctly. For hand-quantized checkpoints, set `hf_config_name` per stage or the wrong stage gets quantized.

## LoRA

DiT LoRA (PEFT-compatible) landed v0.14 #758. Pass per-request:

```json
{
  "model": "Qwen/Qwen-Image",
  "prompt": "...",
  "lora": {
    "adapter": "my_style_lora.safetensors",
    "weight": 0.8
  }
}
```

Or load at server-start via `--enable-lora --lora-modules <name>=<path>`.

Combined with ComfyUI bridge (v0.18 #1596), ComfyUI-saved LoRAs load directly.

## DiT LoRA + Offload

v0.14 #858 added **layerwise CPU offloading** for DiT — transformer blocks swap to/from CPU between timesteps. Saves ~40% VRAM at ~15% throughput cost. Configured per-stage:

```yaml
engine_args:
  layerwise_cpu_offload: true
```

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

## verl RL / Flow-GRPO (v0.18)

vllm-omni integrates with verl for E2E RL training on Qwen-Image via Flow-GRPO (#1646, #1593, #2005, #2217). Adds collective RPC support + async batching. Not a serving concern, but worth knowing: the same diffusion engine drives training feedback. For Flow-GRPO setups, cross-reference `docs/features/verl.md`.

## ComfyUI bridge (v0.16 #1113)

vllm-omni can be the backend for ComfyUI's "Remote DiT" nodes. Boot the vllm-omni server normally, then point ComfyUI at `http://host:8091/v1/images/generations`. v0.18 #1596 added video + LoRA support to the bridge.

## Performance sanity check

If DiT latency looks wrong:

1. Check `--ulysses-degree` matches GPU count.
2. Confirm TeaCache or Cache-DiT is enabled (stage-config extras).
3. Check quantization is engaging: `python -c "from vllm_omni.quantization.factory import ...; print(built_config)"`.
4. Wan2.2 specifically: `guidance_scale_2` + `boundary_ratio` must both be set or dual-CFG no-ops.
5. Blackwell SM100/SM103 paths: some DiT kernels fall back to CUTLASS; pin `flashinfer<0.6.7` if TRTLLM attention hangs (borrowed from upstream vLLM bug).
