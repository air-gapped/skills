# vllm-omni supported models

Load when operator asks "what's supported" / "is model X supported" / "which platform for model Y".

**Contents:** sync rule · Any-to-any omni · Image · Video · TTS and audio · World models and VLA · Platform legend · Model-picker heuristics · Pending additions · Community skill catalog.

> **Synced row-for-row with `docs/models/supported_models.md` at tag v0.30.0** (93 rows),
> platform columns included. Upstream's own caveat applies: for rows with an
> audited recipe, the checkmarks are only the hardware that recipe documents, so
> an empty cell means "not listed", not "fails". For any other tag, read the
> document at that tag before calling a model unsupported:
> `gh api -H 'Accept: application/vnd.github.raw' 'repos/vllm-project/vllm-omni/contents/docs/models/supported_models.md?ref=<tag>'`
>
> **Removed — a deploy naming these fails to resolve:** DreamID-Omni,
> MagiHuman, SoulX-Singer and AudioX (v0.28.0); Dynin-Omni and dots.tts
> (v0.30.0, #7655).
>
> **Not in the supported list even where a deploy YAML ships:** Step-Audio2,
> Aura and Nemotron Audex (`aura_omni.yaml`, `audex_*.yaml`). A release note
> saying a model was "added or improved" is not presence in the list. Treat them
> as unsupported.
>
> **Code present, no list row at v0.30.0:** PersonaPlex (duplex, see SKILL.md),
> Nemotron VoiceChat, JoyAI-VL interaction (`vllm_omni/model_executor/models/`).
> Read the release notes and the example under `examples/online_serving/` before
> relying on one.

## Any-to-any omni and audio-chat models

| Architecture | Model | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|---|:-:|:-:|:-:|:-:|---|
| `Qwen3OmniMoeForConditionalGeneration` | Qwen3-Omni | `Qwen/Qwen3-Omni-30B-A3B-Instruct` | Y |  |  |  | Thinker/Talker/Code2Wav. Default deploy 2 GPUs (stage 0 on cuda:0, stages 1+2 on cuda:1). `/v1/realtime` with the default `async_chunk: true`; duplex via `qwen3_omni_duplex.yaml`. |
| `Qwen2_5OmniForConditionalGeneration` | Qwen2.5-Omni | `Qwen/Qwen2.5-Omni-7B`, `Qwen/Qwen2.5-Omni-3B` | Y | Y | Y | Y | No realtime streaming path. |
| `MingFlashOmniForConditionalGeneration` + `MingImagePipeline` | Ming-flash-omni-2.0 (omni-speech + imagegen<sup>1</sup>) | `Jonathan1909/Ming-flash-omni-2.0` | Y |  |  |  |  |
| `MammothModa2ForConditionalGeneration` | MammothModa2-Preview | `bytedance-research/MammothModa2-Preview` | Y | Y |  |  | Preview model. |
| `MammothModa2ForConditionalGeneration` | MammothModa2-Dev (AR-only image understanding) | `bytedance-research/MammothModa2-Dev` | Y |  |  |  |  |
| `MiMoAudioModel` | MiMo-Audio-7B-Instruct | `XiaomiMiMo/MiMo-Audio-7B-Instruct` | Y | Y |  |  | RTF ~0.2 (v0.16 notes). Wrong attention backend → noise output. #2683 root-caused in `stage_input_processors/mimo_audio.py`, fix unconfirmed. |
| `CovoAudioForConditionalGeneration` | Covo-Audio-Chat | `tencent/Covo-Audio-Chat` | Y |  |  |  |  |
| `MiniCPMO45OmniForConditionalGeneration` | MiniCPM-o 4.5 | `openbmb/MiniCPM-o-4_5` | Y |  | Y |  |  |

## Image generation, editing and unified models

| Architecture | Model | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|---|:-:|:-:|:-:|:-:|---|
| `BagelForConditionalGeneration` | BAGEL (DiT-only) | `ByteDance-Seed/BAGEL-7B-MoT` | Y | Y |  | Y | Not full MoT. `tensor_parallel_size` is not a diffusion config field (#2635); unknown fields raise on v0.30.0 (#5172). |
| `HunyuanImage3ForCausalMM` | HunyuanImage3.0 (DiT-only) | `tencent/HunyuanImage-3.0`, `tencent/HunyuanImage-3.0-Instruct` | Y | Y | Y | Y |  |
| `QwenImagePipeline` | Qwen-Image | `Qwen/Qwen-Image` | Y |  |  | Y | INT8 (#1470). GGUF needs `vllm-gguf-plugin`. Bucket sizes 640/1024/1536. |
| `QwenImagePipeline` | Qwen-Image-2512 | `Qwen/Qwen-Image-2512` | Y |  |  | Y |  |
| `QwenImageEditPipeline` | Qwen-Image-Edit | `Qwen/Qwen-Image-Edit` | Y | Y | Y | Y |  |
| `QwenImageEditPlusPipeline` | Qwen-Image-Edit-2509 | `Qwen/Qwen-Image-Edit-2509` | Y | Y | Y | Y |  |
| `QwenImageLayeredPipeline` | Qwen-Image-Layered | `Qwen/Qwen-Image-Layered` | Y | Y | Y | Y | `layers` param 3–10. |
| `QwenImageEditPlusPipeline` | Qwen-Image-Edit-2511 | `Qwen/Qwen-Image-Edit-2511` | Y | Y | Y | Y |  |
| `GlmImagePipeline` | GLM-Image | `zai-org/GLM-Image` | Y | Y |  |  | Current pins cover its transformers needs; do not hand-upgrade transformers past 5.14.x. |
| `ZImagePipeline` | Z-Image | `Tongyi-MAI/Z-Image-Turbo` | Y | Y | Y | Y | Quickstart default; smallest footprint. INT8 supported. |
| `Krea2Pipeline` | Krea 2 (Raw + Turbo) | `krea/Krea-2-Raw`, `krea/Krea-2-Turbo` | Y |  |  | Y |  |
| `OvisImagePipeline` | Ovis-Image | `OvisAI/Ovis-Image` | Y | Y |  | Y |  |
| `LongcatImagePipeline` | LongCat-Image | `meituan-longcat/LongCat-Image` | Y | Y | Y | Y |  |
| `LongCatImageEditPipeline` | LongCat-Image-Edit | `meituan-longcat/LongCat-Image-Edit` | Y | Y | Y | Y |  |
| `BooguImagePipeline` | Boogu-Image | `Boogu/Boogu-Image-0.1-Base`, `Boogu/Boogu-Image-0.1-Edit`, `Boogu/Boogu-Image-0.1-Edit-Turbo` | Y |  |  | Y |  |
| `BooguImageTurboPipeline` | Boogu-Image Turbo distilled T2I | `Boogu/Boogu-Image-0.1-Turbo` | Y |  |  |  |  |
| `StableDiffusionXLPipeline` | Stable-Diffusion-XL | `stabilityai/stable-diffusion-xl-base-1.0` | Y | Y | Y | Y |  |
| `StableDiffusion3Pipeline` | Stable-Diffusion-3 | `stabilityai/stable-diffusion-3.5-medium` | Y | Y |  | Y |  |
| `Flux2KleinPipeline` | FLUX.2-klein | `black-forest-labs/FLUX.2-klein-4B`, `black-forest-labs/FLUX.2-klein-9B` | Y | Y | Y | Y |  |
| `FluxKontextPipeline` | FLUX.1-Kontext-dev | `black-forest-labs/FLUX.1-Kontext-dev` | Y | Y |  |  |  |
| `FluxPipeline` | FLUX.1-dev | `black-forest-labs/FLUX.1-dev` | Y | Y |  | Y | Do not deploy the v0.19.0rc1 tag (T5 regression #2730, fixed v0.20.0). |
| `FluxPipeline` | FLUX.1-schnell | `black-forest-labs/FLUX.1-schnell` | Y | Y |  | Y |  |
| `OmniGen2Pipeline` | OmniGen2 | `OmniGen2/OmniGen2` | Y | Y |  | Y |  |
| `NextStep11Pipeline` | NextStep-1.1 | `stepfun-ai/NextStep-1.1` | Y | Y |  | Y |  |
| `Flux2Pipeline` | FLUX.2-dev | `black-forest-labs/FLUX.2-dev` | Y | Y |  |  | FP8 path (#1640). |
| `SenseNovaU1Pipeline` | SenseNova-U1 (DiT-only), SenseNova-U1.5 | `SenseNova/SenseNova-U1-8B-MoT`, `sensenova/SenseNova-U1.5-8B-MoT` | Y |  |  |  |  |
| `LancePipeline` | Lance | `bytedance-research/Lance` | Y |  |  |  |  |
| `ErnieImagePipeline` | ERNIE-Image | `baidu/ERNIE-Image`, `baidu/ERNIE-Image-Turbo` | Y | Y | Y | Y |  |
| `HiDreamImagePipeline` | HiDream-I1-Full | `HiDream-ai/HiDream-I1-Full` | Y | Y |  |  |  |
| `HiDreamO1ImagePipeline` | HiDream-O1-Image | `HiDream-ai/HiDream-O1-Image` | Y |  |  |  |  |
| `AnimaPipeline` | Anima | `circlestone-labs/Anima` | Y | Y |  |  |  |

## Video generation

| Architecture | Model | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|---|:-:|:-:|:-:|:-:|---|
| `WanPipeline` | Wan2.1-T2V, Wan2.2-T2V, Wan2.2-TI2V | `Wan-AI/Wan2.1-T2V-1.3B-Diffusers`, `Wan-AI/Wan2.1-T2V-14B-Diffusers`, `Wan-AI/Wan2.2-T2V-A14B-Diffusers`, `Wan-AI/Wan2.2-TI2V-5B-Diffusers` | Y | Y | Y | Y | Orphan stage processes on crash (#2768) — launch in a process group. |
| `WanImageToVideoPipeline` | Wan2.2-I2V | `Wan-AI/Wan2.2-I2V-A14B-Diffusers` | Y | Y | Y | Y |  |
| `Wan22S2VPipeline` | Wan2.2-S2V | `Wan-AI/Wan2.2-S2V-14B` | Y | Y | Y | Y |  |
| `Wan22VACEPipeline` | Wan2.1-VACE | `Wan-AI/Wan2.1-VACE-1.3B-diffusers`, `Wan-AI/Wan2.1-VACE-14B-diffusers` | Y | Y | Y | Y |  |
| `Wan22VACEPipeline` | Wan2.2-VACE | `Pyros13/Wan2.2-VACE-Fun-A14B-Diffusers` | Y |  |  | Y |  |
| `LTX2Pipeline` | LTX-2 / LTX-2.3 one-stage T2V and I2V | `Lightricks/LTX-2`, `diffusers/LTX-2.3-Diffusers` | Y | Y |  |  | Single one-stage entry since v0.26.0 (#5148): checkpoint metadata picks LTX-2 vs 2.3, `image=` picks I2V. |
| `LTX2TwoStagePipeline` | LTX-2 / LTX-2.3 ordinary two-stage T2V and I2V | `Lightricks/LTX-2`, `diffusers/LTX-2.3-Diffusers` + matching Lightricks LoRA and upsampler | Y | Y |  |  |  |
| `LTX2DistilledOneStagePipeline` | LTX-2 / LTX-2.3 merged-distilled one-stage T2V and I2V | `rootonchair/LTX-2-19b-distilled`, `diffusers/LTX-2.3-Distilled-Diffusers` | Y | Y |  |  | `LTX2DistilledPipeline` (v0.26.0 name) is still registered. |
| `LTX2DistilledTwoStagePipeline` | LTX-2 / LTX-2.3 merged-distilled two-stage T2V and I2V | `rootonchair/LTX-2-19b-distilled`, `diffusers/LTX-2.3-Distilled-Diffusers` + matching Lightricks upsampler | Y | Y |  |  |  |
| `LTX2Pipeline` | LTX-2.5 Full/SFT one-stage T2V and I2V | `Lightricks/LTX-2.5-Diffusers` | Y |  |  |  |  |
| `LTX2TwoStagePipeline` | LTX-2.5 Full/SFT two-stage T2V and I2V | `Lightricks/LTX-2.5-Diffusers` + `Lightricks/LTX-2.5` LoRA | Y |  |  |  |  |
| `LTX2DistilledOneStagePipeline` | LTX-2.5 merged-distilled one-stage T2V and I2V | `Lightricks/LTX-2.5-Diffusers` | Y |  |  |  |  |
| `LTX2DistilledTwoStagePipeline` | LTX-2.5 merged-distilled two-stage T2V and I2V | `Lightricks/LTX-2.5-Diffusers` | Y |  |  |  |  |
| `LTX2T2VDMD2Pipeline` / `LTX2I2VDMD2Pipeline` | LTX-2 DMD2 | — | | | | | In `vllm_omni/diffusion/registry.py` at v0.30.0, not in the supported list. |
| ~~`LTX2ImageToVideoPipeline`~~, ~~`LTX23Pipeline`~~, ~~`LTX23ImageToVideoPipeline`~~, ~~`LTX2TwoStagesPipeline`~~, ~~`LTX2ImageToVideoTwoStagesPipeline`~~ | — | — | | | | | **Removed in v0.26.0** (#5148). A stage config naming any of these fails to resolve. |
| `LingBotVideoPipeline` | LingBot-Video dense and MoE T2I, T2V, TI2V | `robbyant/lingbot-video-dense-1.3b`, `robbyant/lingbot-video-moe-30b-a3b` | Y |  |  |  |  |
| `SanaVideoPipeline` | SANA-Video-2B T2V (native 480p/720p; Diffusers adapter validated at both resolutions) | `Efficient-Large-Model/SANA-Video_2B_480p_diffusers`, `Efficient-Large-Model/SANA-Video_2B_720p_diffusers` | Y |  |  |  |  |
| `SanaImageToVideoPipeline` | SANA-Video-2B I2V (native and Diffusers adapter validated at 480p/720p) | `Efficient-Large-Model/SANA-Video_2B_480p_diffusers`, `Efficient-Large-Model/SANA-Video_2B_720p_diffusers` | Y |  |  |  |  |
| `MiniMaxH3Pipeline` | MiniMax H3 T2VA, first/last-keyframe FL2VA, and mixed-reference Ref2VA | `MiniMaxAI/MiniMax-H3` | Y | Y |  |  | Joint video+audio via `/v1/videos`. AMD validated on gfx942/gfx950 in BF16 with the AITER `FLASH_ATTN` diffusion backend only. |
| `Magi2Pipeline` | MAGI-2 native Preview-stage T2VA and I2VA (272p/540p) | `sand-ai/MAGI-2-preview` | Y |  |  |  |  |
| `HeliosPipeline`, `HeliosPyramidPipeline` | Helios | `BestWishYsh/Helios-Base`, `BestWishYsh/Helios-Mid`, `BestWishYsh/Helios-Distilled` | Y | Y | Y |  |  |
| `LongCatVideoAvatarPipeline` | LongCat-Video-Avatar-1.5 A2V/AI2V (native single-speaker and multi-speaker AI2V/AVC) | `meituan-longcat/LongCat-Video-Avatar-1.5` | Y |  |  |  |  |
| `HunyuanVideo15Pipeline` | HunyuanVideo-1.5-T2V | `hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-480p_t2v`, `hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-720p_t2v` | Y | Y |  |  | NPU mindiesd flash-attn shape issue #2880 (fix unconfirmed). |
| `HunyuanVideo15ImageToVideoPipeline` | HunyuanVideo-1.5-I2V | `hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-480p_i2v`, `hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-720p_i2v` | Y | Y |  |  |  |

## TTS, speech and audio output

| Architecture | Model | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|---|:-:|:-:|:-:|:-:|---|
| `CosyVoice3Model` | CosyVoice3 | `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` | Y | Y |  | Y |  |
| `AuKForConditionalGeneration` | AuK / AuK-Flash (instruction-driven speech generation and editing) | `tencent/AuK`, `tencent/AuK-Flash` (with `Qwen/Qwen2.5-Omni-3B`; assemble with `tools/prepare_auk_checkpoint.py`) | Y |  |  |  |  |
| `OmniVoiceModel` | OmniVoice | `k2-fsa/OmniVoice` | Y |  |  | Y |  |
| `VoxCPM2TalkerForConditionalGeneration` | VoxCPM2 | `openbmb/VoxCPM2` | Y |  |  | Y |  |
| `BreezeForConditionalGeneration` | Breeze-TTS-2 (voice design, voice clone, voice direction, CFG) | `BreezeBlue/Breeze-TTS-2` | Y |  |  |  |  |
| `StableAudioPipeline` | Stable-Audio-Open | `stabilityai/stable-audio-open-1.0` | Y | Y |  | Y | Text-to-audio. |
| `MiniMaxMusic3ForConditionalGeneration` | MiniMax Music 3 (text-to-music) | `MiniMaxAI/MiniMax-Music3` | Y |  |  |  |  |
| `Qwen3TTSForConditionalGeneration` | Qwen3-TTS-12Hz-1.7B-CustomVoice | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | Y |  |  | Y | `--task-type CustomVoice`, preset voices. All Qwen3-TTS: `--trust-remote-code`, 24 kHz out, RTF 0.22–0.45 (v0.16 notes). Streaming audio gaps #2562 closed for inactivity, not fixed. |
| `Qwen3TTSForConditionalGeneration` | Qwen3-TTS-12Hz-1.7B-VoiceDesign | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | Y | Y | Y | Y | `--task-type VoiceDesign`, instruction-guided voice. |
| `Qwen3TTSForConditionalGeneration` | Qwen3-TTS-12Hz-1.7B-Base | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | Y | Y | Y | Y | `--task-type Base`, cloning with `ref_audio`. `Qwen/Qwen3-TTS-12Hz-0.6B-Base` uses the same architecture but is not in the upstream list. |
| `MingTTSForConditionalGeneration` | Ming-omni-tts dense 0.5B | `inclusionAI/Ming-omni-tts-0.5B` | Y |  |  | Y |  |
| `GLMTTSForConditionalGeneration` | GLM-TTS | `zai-org/GLM-TTS` | Y |  |  |  |  |
| `MossTTSNanoForCausalLM` | MOSS-TTS-Nano | `OpenMOSS-Team/MOSS-TTS-Nano` | Y |  | Y |  |  |
| `MossTTSDelayModel` | MOSS-TTS, MOSS-TTSD, MOSS-SoundEffect, MOSS-VoiceGenerator | `OpenMOSS-Team/MOSS-VoiceGenerator` | Y |  |  |  |  |
| `MossTTSRealtime` | MOSS-TTS-Realtime | `OpenMOSS-Team/MOSS-TTS-Realtime` | Y |  |  |  |  |
| `HiggsAudioV2ForConditionalGeneration` | Higgs-Audio v2 | `bosonai/higgs-audio-v2-generation-3B-base` | Y |  |  |  |  |
| `HiggsMultimodalQwen3ForConditionalGeneration` | Higgs-Audio v3 (TTS) | `bosonai/higgs-audio-v3-tts-4b` | Y |  |  |  |  |
| `IndexTTS2TalkerForConditionalGeneration` | IndexTTS-2 | `IndexTeam/IndexTTS-2` | Y |  |  |  |  |
| `IndexTTS25TalkerForConditionalGeneration` | IndexTTS-2.5 | native `checkpoints/` bundle | Y |  |  |  |  |
| `MiMoV2ASRForCausalLM` | MiMo-V2.5-ASR | `XiaomiMiMo/MiMo-V2.5-ASR` | Y | Y |  |  | Speech in, text out — the one ASR row in the list. |
| `FishSpeechSlowARForConditionalGeneration` | Fish Speech S2 Pro | `fishaudio/s2-pro` | Y | Y |  | Y |  |
| `Audio8TTSSlowARForConditionalGeneration` | Audio8 TTS Preview | `Audio8/Audio8-TTS-Preview-0.6b` | Y |  |  |  |  |
| `VoxtralTTSForConditionalGeneration` | Voxtral TTS | `mistralai/Voxtral-4B-TTS-2603` | Y | Y |  |  | Forum thread [#2549](https://discuss.vllm.ai/t/issues-with-voxtral-models-and-omni/2549). |
| `GepardTalkerForConditionalGeneration` | Gepard-1.0 | `nineninesix/gepard-1.0` | Y |  |  | Y |  |

## World models and robot policies (VLA)

| Architecture | Model | HuggingFace ID | CUDA | ROCm | NPU | XPU | Notes |
|---|---|---|:-:|:-:|:-:|:-:|---|
| `InternVLAA1Pipeline` | InternVLA-A1 | `InternRobotics/InternVLA-A1-3B` | Y | Y |  |  |  |
| `Gr00tN1d7Pipeline` | GR00T N1.7 | `nvidia/GR00T-N1.7-3B` | Y |  |  |  |  |
| `LingBotWorldCausalDMDPipeline` | LingBot-World 2.0 v1 (experimental) | `robbyant/lingbot-world-v2-14b-causal-fast-diffusers` | exp |  |  |  | CUDA experimental only. |
| `Cosmos3OmniDiffusersPipeline` | Cosmos3 T2I, T2V, I2V, V2V, T2V with sound, action policy | `nvidia/Cosmos3-Nano`, `nvidia/Cosmos3-Super` | Y | Y | Y | Y |  |
| `SanaWmPipeline` | SANA-WM | `BBBBruce/SANA-WM_bidirectional-stage1-diffusers` | Y |  |  |  |  |
| `DreamZeroPipeline` | DreamZero-DROID | `GEAR-Dreams/DreamZero-DROID` | Y | Y | Y | Y |  |
| `Pi0Pipeline` | π0 (Pi-Zero) VLA | `lerobot/pi0_base` | Y |  |  |  |  |
| `Pi05Pipeline` | π0.5 VLA | `lerobot/pi05_base` | Y |  |  |  |  |

## Platform legend

- **CUDA** — NVIDIA H100/A100/H200/Blackwell.
- **ROCm** — AMD MI300 family. Wheel index is version-specific and moves: v0.30.0 uses `vllm==0.30.0+rocm723` from `https://wheels.vllm.ai/rocm/0.30.0/rocm723` (cp312 only; v0.24.0 used `rocm700`). Images live in the separate `vllm/vllm-omni-rocm` repo, which tops out at v0.28.0.
- **NPU** — Huawei Ascend 910B. Set `--dtype`, `--max-model-len`, `--served-model-name` in the stage YAML, not on the CLI: multi-stage deploys do not pass them through (#2898).
- **XPU** — Intel Arc / Ponte Vecchio. Backend: XCCL / oneccl_bindings_for_pytorch.
- **MUSA** — detected by `torchada.is_musa_platform()` (`vllm_omni/platforms/__init__.py`); upstream's list has no MUSA column, so no row claims it.

## Model-picker heuristics

| Operator goal | Recommended model |
|---|---|
| Smallest image-gen footprint | `Tongyi-MAI/Z-Image-Turbo` (quickstart default) |
| Best-quality open text-to-image | `black-forest-labs/FLUX.2-dev` (FP8) or `Qwen/Qwen-Image` (GGUF needs `vllm-gguf-plugin` on v0.26.0+) |
| Image edit / inpaint | Qwen-Image-Edit-2511 or FLUX.1-Kontext-dev |
| Short video (5-15s) | Wan2.2-T2V-A14B (A14B MoE) or LTX-2-distilled |
| Long video / talking head | HunyuanVideo-1.5, Wan2.2-S2V (speech-to-video) |
| Full any-to-any with audio | Qwen3-Omni-30B-A3B-Instruct |
| TTS with custom voice upload | Qwen3-TTS-12Hz-1.7B-Base (cloning mode) |
| Cheap TTS | Fun-CosyVoice3-0.5B |
| Text-to-audio (music / SFX) | Stable-Audio-Open-1.0 |

## Pending / RFC model additions

From open issues (2026-04):

- Ovi 1.1 (#2593), LongCat-AudioDiT (#2462), VibeVoice (#2319), OmniWeaving (#2664), 3D World Models / VGGT (#2727) — all absent from the v0.30.0 supported list.
- Landed since: VoxCPM2 and Wan2.2-S2V-14B are in the v0.30.0 list (the S2V issue #2612 still reads open). AudioX shipped and was removed again at v0.28.0.

If a model is not in the tables above, check `gh api /repos/vllm-project/vllm-omni/contents/vllm_omni/model_executor/models` and the open issues before concluding unsupported.

## Community skill catalog

[`hsliuustc0106/vllm-omni-skills`](https://github.com/hsliuustc0106/vllm-omni-skills) — 22-skill Claude/Cursor plugin catalog. Useful for "how do I do X with model Y" recipes the official docs don't have yet. Third-party; not an official project artifact.
