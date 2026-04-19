# vllm-omni supported models

Load when operator asks "what's supported" / "is model X supported" / "which platform for model Y". Source: [`docs/models/supported_models.md`](https://github.com/vllm-project/vllm-omni/blob/main/docs/models/supported_models.md), code in `vllm_omni/model_executor/`. Current as of v0.18.0 (2026-03-28).

## Any-to-any omni models

| Architecture | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|:-:|:-:|:-:|:-:|---|
| `Qwen3OmniMoeForConditionalGeneration` | `Qwen/Qwen3-Omni-30B-A3B-Instruct` | Y | Y | Y | Y | 30B MoE (~3B active). Thinker/Talker/Code2Wav stages. TP2 on H100 production. Realtime via `/v1/realtime` (requires `async_chunk: false`). Audio gaps issue #2562. |
| `Qwen2_5OmniForConditionalGeneration` | `Qwen/Qwen2.5-Omni-7B`, `-3B` | Y | Y | Y | Y | Predecessor family, no realtime streaming path. |
| `MiMoAudioForConditionalGeneration` | `XiaomiMiMo/MiMo-Audio-7B-Instruct` | Y | Y | | | Production RTF ~0.2 per v0.16 notes. Issue #2683 (serving bug). Wrong attention backend → noise. |
| `MammothModa2ForConditionalGeneration` | `bytedance-research/MammothModa2-Preview` | Y | Y | | | Preview model. |
| `FishSpeechSlowARForConditionalGeneration` | `fishaudio/s2-pro` | Y | Y | | | v0.18. |
| `DyninOmniForConditionalGeneration` | `snu-aidas/Dynin-Omni` | Y | | | | CUDA-only. |
| `MingFlashOmniForConditionalGeneration` | Ming Flash Omni family | Y | Y | | | |
| `DreamIDOmniPipeline` | `XuGuo699/DreamID-Omni` | Y | Y | | | |

## Diffusion image generation

| Architecture | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|:-:|:-:|:-:|:-:|---|
| `QwenImagePipeline` | `Qwen/Qwen-Image`, `Qwen/Qwen-Image-2512` | Y | Y | Y | Y | GGUF adapter v0.16 (#1755), INT8 v0.18 (#1470). Bucket sizes: 640/1024/1536. |
| `QwenImageEditPipeline` | `Qwen/Qwen-Image-Edit` | Y | Y | Y | Y | Image-to-image edit. |
| `QwenImageEditPlusPipeline` | `Qwen/Qwen-Image-Edit-2509`, `-2511` | Y | Y | Y | Y | |
| `QwenImageLayeredPipeline` | `Qwen/Qwen-Image-Layered` | Y | Y | Y | Y | `layers` param 3-10. |
| `FluxPipeline` | `black-forest-labs/FLUX.1-dev`, `FLUX.1-schnell` | Y | Y | | Y | **v0.19.0rc1 FLUX.1-dev regression (#2730) — pin v0.18.0.** |
| `FluxKontextPipeline` | `black-forest-labs/FLUX.1-Kontext-dev` | Y | Y | | | |
| `Flux2Pipeline` | `black-forest-labs/FLUX.2-dev` | Y | Y | | | FP8 path v0.16 (#1640). |
| `Flux2KleinPipeline` | `black-forest-labs/FLUX.2-klein-{4B,9B}` | Y | Y | Y | Y | v0.14. |
| `GlmImagePipeline` | `zai-org/GLM-Image` | Y | Y | | | **Requires `transformers>=5.0` manual upgrade on v0.18.** |
| `ZImagePipeline` | `Tongyi-MAI/Z-Image-Turbo` | Y | Y | Y | Y | Quickstart default. Smallest footprint. INT8 supported. |
| `HunyuanImage3ForCausalMM` | `tencent/HunyuanImage-3.0`, `-Instruct` | Y | Y | Y | Y | v0.18. |
| `LongcatImagePipeline` | `meituan-longcat/LongCat-Image` | Y | Y | Y | Y | |
| `LongCatImageEditPipeline` | `meituan-longcat/LongCat-Image-Edit` | Y | Y | Y | Y | |
| `StableDiffusion3Pipeline` | `stabilityai/stable-diffusion-3.5-medium` | Y | Y | | Y | |
| `OvisImagePipeline` | `OvisAI/Ovis-Image` | Y | Y | | Y | |
| `OmniGen2Pipeline` | `OmniGen2/OmniGen2` | Y | Y | | Y | |
| `BagelForConditionalGeneration` | `ByteDance-Seed/BAGEL-7B-MoT` | Y | Y | | Y | **DiT-only** (not full MoT). v0.14 stage-based layout. YAML/docs field mismatch #2635. |
| `NextStep11Pipeline` | `stepfun-ai/NextStep-1.1` | Y | Y | | Y | |

## Diffusion video generation

| Architecture | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|:-:|:-:|:-:|:-:|---|
| `WanPipeline` | `Wan-AI/Wan2.1-T2V-{1.3B,14B}-Diffusers`, `Wan-AI/Wan2.2-T2V-A14B-Diffusers`, `Wan-AI/Wan2.2-TI2V-5B-Diffusers` | Y | Y | Y | Y | T2V. v0.16 ships OpenAI `/v1/videos` endpoint. Orphan procs on crash #2768. |
| `WanImageToVideoPipeline` | `Wan-AI/Wan2.2-I2V-A14B-Diffusers` | Y | Y | Y | Y | I2V. |
| `Wan22VACEPipeline` | `Wan-AI/Wan2.1-VACE-{1.3B,14B}-diffusers` | Y | Y | Y | Y | VACE control variant. |
| `LTX2Pipeline` | `Lightricks/LTX-2`, `rootonchair/LTX-2-19b-distilled` | Y | Y | | | T2V. |
| `LTX2ImageToVideoPipeline` | `Lightricks/LTX-2` | Y | Y | | | I2V. |
| `LTX2TwoStagesPipeline` / `LTX2ImageToVideoTwoStagesPipeline` | `rootonchair/LTX-2-19b-distilled` | Y | Y | | | Distilled two-stage variants. |
| `HeliosPipeline`, `HeliosPyramidPipeline` | `BestWishYsh/Helios-{Base,Mid,Distilled}` | Y | Y | Y | | |
| `MagiHumanPipeline` | `SII-GAIR/daVinci-MagiHuman-Base-1080p` | Y | Y | | | |
| `HunyuanVideo15Pipeline` | `hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-{480p,720p}_t2v` | Y | Y | | | T2V. Flash-attn shape issue on NPU mindiesd #2880. |
| `HunyuanVideo15ImageToVideoPipeline` | `hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-{480p,720p}_i2v` | Y | Y | | | I2V. |

## TTS and audio output

| Architecture | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|:-:|:-:|:-:|:-:|---|
| `Qwen3TTSForConditionalGeneration` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | Y | Y | Y | Y | `--task-type CustomVoice`. Preset voices. |
| `Qwen3TTSForConditionalGeneration` | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | Y | Y | Y | Y | `--task-type VoiceDesign`. Instruction-guided voice. |
| `Qwen3TTSForConditionalGeneration` | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | Y | Y | Y | Y | `--task-type Base`. Voice cloning with `ref_audio`. |
| | | | | | | **All Qwen3-TTS: `--enforce-eager --trust-remote-code`** (issue #2866). RTF 0.22-0.45 per v0.16 notes. Output 24 kHz. |
| `CosyVoice3Model` | `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` | Y | Y | | | v0.18. |
| `VoxtralTTSForConditionalGeneration` | `mistralai/Voxtral-4B-TTS-2603` | Y | Y | | | Forum thread [#2549](https://discuss.vllm.ai/t/issues-with-voxtral-models-and-omni/2549). |
| `StableAudioPipeline` | `stabilityai/stable-audio-open-1.0` | Y | Y | | Y | T2A. v0.14 (#331). |

## Platform legend

- **CUDA** — NVIDIA H100/A100/H200/Blackwell.
- **ROCm** — AMD MI300 family. `vllm==X.X.X+rocm700` wheel index.
- **NPU** — Huawei Ascend 910B. Fresh-install regression on main for some models #2898.
- **XPU** — Intel Arc / Ponte Vecchio. Backend: XCCL / oneccl_bindings_for_pytorch.
- **MUSA** — Tencent GPU (not shown in this table). Auto-detected via `torchada`.

## Model-picker heuristics

| Operator goal | Recommended model |
|---|---|
| Smallest image-gen footprint | `Tongyi-MAI/Z-Image-Turbo` (quickstart default) |
| Best-quality open text-to-image | `black-forest-labs/FLUX.2-dev` (FP8) or `Qwen/Qwen-Image` (GGUF) |
| Image edit / inpaint | Qwen-Image-Edit-2511 or FLUX.1-Kontext-dev |
| Short video (5-15s) | Wan2.2-T2V-A14B (A14B MoE) or LTX-2-distilled |
| Long video / talking head | MagiHuman, HunyuanVideo-1.5 |
| Full any-to-any with audio | Qwen3-Omni-30B-A3B-Instruct |
| TTS with custom voice upload | Qwen3-TTS-12Hz-0.6B-Base (cloning mode) |
| Cheap TTS | Fun-CosyVoice3-0.5B |
| Text-to-audio (music / SFX) | Stable-Audio-Open-1.0 |

## Pending / RFC model additions

From open issues (2026-04):

- VoxCPM2 (#2594), Ovi 1.1 (#2593), LongCat-AudioDiT (#2462), VibeVoice (#2319), AudioX (#2003), OmniWeaving (#2664), 3D World Models / VGGT (#2727), Wan2.2-S2V-14B (#2612).

If a model is not in the tables above, check `gh api /repos/vllm-project/vllm-omni/contents/vllm_omni/model_executor/models` and the open issues before concluding unsupported.

## Community skill catalog

[`hsliuustc0106/vllm-omni-skills`](https://github.com/hsliuustc0106/vllm-omni-skills) — 22-skill Claude/Cursor plugin catalog. Useful for "how do I do X with model Y" recipes the official docs don't have yet. Third-party; not an official project artifact.
