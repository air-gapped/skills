---
name: vllm-omni
description: |-
  vLLM-Omni output-side multimodal generation — image (FLUX.1/2, Qwen-Image, GLM-Image, BAGEL, SD3.5, HunyuanImage-3.0), video (Wan2.1/2.2, LTX-2, HunyuanVideo-1.5), TTS (Qwen3-TTS, CosyVoice3, Voxtral-TTS), any-to-any omni (Qwen3-Omni, Qwen2.5-Omni, MiMo-Audio) via `vllm serve --omni`. Stage-based disaggregation (OmniConnector + Mooncake + RDMA), `/v1/images/generations`, async+sync `/v1/videos`, `/v1/audio/speech` with voice-upload, PCM16 WebSocket `/v1/realtime`, Ulysses/Ring SP + CFG-parallel, DiT FP8/INT8/GGUF, CUDA/ROCm/NPU/XPU/MUSA matrix, release pitfalls (v0.19.0rc1 FLUX regression, GLM-Image transformers>=5.0, Qwen3-TTS enforce-eager).
when_to_use: |-
  Trigger on any vLLM deployment producing non-text output (image/video/audio) or any-to-any omni model, or model names ending `-Image`/`-TTS`/`-Omni`/`-Video`. Keywords — `vllm serve --omni`, `vllm-omni`, `/v1/images/generations`, `/v1/videos`, `/v1/audio/speech`, `/v1/audio/voices`, `/v1/realtime`, `async_chunk`, `stage_configs_path`, OmniConnector, MooncakeStore, OmniDiffusionSamplingParams, FlowUniPC, TeaCache, Cache-DiT, Sage/Ring/Ulysses, `--ulysses-degree`, `--ring-degree`, Thinker/Talker/Code2Wav, BAGEL, Wan2.2, FLUX.2-klein, ComfyUI bridge, verl RL. Narrow phrasings — "serve Qwen-Image", "Qwen3-Omni streaming audio", "async video job". Also implicit — "deploy image gen", "TTS endpoint", "video gen pipeline", "audit omni", "deploy-memo for {model}-Image/-TTS/-Video". NOT for embeddings/reranking/STT/OCR (→ `vllm-input-modalities`).
---

# vLLM-Omni — output-side multimodal serving

Target: operators who serve image / video / audio / any-to-any generation models with vLLM-Omni, a plugin layer on upstream vLLM. vllm-omni extends upstream vLLM (same CUDA/ROCm/NPU/XPU runtime, same OpenAI-compat API server) to add non-autoregressive DiT models, multi-stage pipeline execution, diffusion schedulers, CFG plumbing, and real-time streaming audio I/O — things upstream vLLM does not ship.

This skill is a **reference**, not a tutorial. SKILL.md holds the mental model, quick-answer router, top pitfalls, and operator cheat sheet. The `references/` files hold endpoint catalogs, supported-model tables, stage-config grammar, and the diffusion/DiT details. Read only the reference file that matches the question.

## How it plugs into vLLM

vllm-omni layers on upstream vLLM: upstream's own CLI hands `vllm serve <model> --omni` to `vllm_omni.entrypoints.cli.main` (exit 1 with "--omni flag requires a valid instance of vllm-omni" when the package is missing), and omni model registrations reach worker subprocesses through the `vllm.general_plugins` entry point. Importing `vllm_omni` runs `vllm_omni/patch.py`, which replaces vLLM classes (`EngineCoreRequest`, `EngineCoreOutput`, `TokensPrompt`, `Request`, …) with Omni subclasses in every loaded module — so a vLLM/omni minor mismatch breaks at import, and `import vllm_omni` does not belong in a process meant to stay stock vLLM. Any-to-any models run as a **graph of disaggregated stages** (Thinker / Talker / Code2Wav for Qwen3-Omni; AR-encoder / DiT for Qwen-Image) joined by `OmniConnector`, so each stage is configured and scaled on its own (`references/stage-config.md`).

## Version pins — check before installing anything

| Rule | Action |
|---|---|
| omni major.minor must equal vLLM major.minor (`vllm_omni/version.py` warns on mismatch) | Install omni **v0.32.0** (current stable) with vLLM **0.32.0** |
| vLLM **0.33.0** is the newest vLLM release, so an unpinned `pip install vllm` resolves to it (PyTorch 2.14.0); omni's only build for it is the pre-release v0.33.0rc1 | Always write `vllm==0.32.0` beside `vllm-omni==0.32.0`. Do not deploy v0.33.0rc1 as current |
| transformers ranges are disjoint across omni minors: v0.30.0 pins `>= 5.13.0, < 5.15`, v0.32.0 pins `>= 5.16.1, < 5.20.0` (same as vLLM 0.32.0) | Upgrade omni and vLLM together, in a fresh venv/image. Never put omni v0.30.0 in a vLLM 0.32.0 env or the reverse |
| v0.32.0 requires Python `>=3.11,<3.14` (v0.30.0 accepted 3.10) | Use 3.12; rebuild 3.10 envs before upgrading |
| Odd omni minors (v0.21 … v0.33) exist only as `rc1` | Check `prerelease` before pinning a minor; a missing stable is not a withdrawn one |
| Docker `vllm/vllm-omni:latest` follows the newest image, and has pointed at rc builds (v0.29.0rc1, v0.31.0rc1; today v0.32.0) | Pin `vllm/vllm-omni:v0.32.0` (`-x86_64` / `-aarch64` variants) in every manifest |
| ROCm images live in `vllm/vllm-omni-rocm`, newest stable **v0.30.0** (no v0.32.0 tag, no `latest`) | On ROCm deploy the v0.30.0 pair; the 0.32.0 ROCm wheel is unvalidated (Install below) |
| A tag is not a wheel and not an image | Check GitHub releases, PyPI and both Docker repos before quoting a version |

Release-by-release history and channel evidence: `references/sources.md` §Releases.

## Quick-answer router

**Serving a specific endpoint** → `references/endpoints.md`
  - `/v1/images/generations`, `/v1/images/edits` (DALL·E-shape)
  - `/v1/videos` (async job) + `/v1/videos/sync` (raw MP4, 600s default timeout)
  - `/v1/audio/speech`, `/v1/audio/voices` (list + upload), `/v1/audio/speech/batch`, `/v1/audio/speech/stream` (WebSocket)
  - `/v1/realtime` (WebSocket PCM16 in/out for Qwen3-Omni; `?duplex=1` / `/v1/duplex` for duplex deployments)
  - `/v1/chat/completions` with diffusion via `extra_body`

**Picking a model** → `references/models.md`
  - Full supported-architecture → HuggingFace-ID table
  - Per-model platform matrix (CUDA / ROCm / NPU / XPU), synced with upstream at v0.32.0
  - Known-issue flags per family, including the pre-v0.20 FLUX / GLM-Image / Qwen3-TTS `--enforce-eager` pitfalls (all fixed on v0.20.0+)

**Writing / debugging stage configs** → `references/stage-config.md`
  - OmniModelConfig + StageConfig YAML grammar
  - OmniConnector types (Shared-memory / Mooncake-Store / Mooncake-Transfer-Engine / MORI / NIXL / Yuanrong)
  - Pipeline edge validation, entry-point requirement
  - `stage_id`, `model_stage`, `worker_type`, `engine_output_type`, `async_chunk`

**DiT-specific questions** → `references/diffusion.md`
  - Schedulers (FlowUniPC + model-specific)
  - CFG plumbing (dual CFG for Wan2.2, true_cfg_scale for Qwen-Image, cfg_branch_past_key_values)
  - Caches: TeaCache / Cache-DiT / latent cache / noise_pred cache
  - Quantization: FP8 (Flux #1640), INT8 (Z-Image/Qwen-Image #1470) per-component via `ComponentQuantizationConfig`; **GGUF moved out of tree in v0.26.0** (#4769) to `vllm-project/vllm-gguf-plugin`
  - Ulysses / Ring sequence parallel, CFG-parallel merged-batch TP

**Full-duplex realtime** — unified engine-owned duplex framework in v0.30.0 (#7413); MiniCPM-o 4.5, PersonaPlex, Qwen3-Omni (`qwen3_omni_duplex.yaml`)
  - `/v1/realtime?duplex=1`; `/v1/duplex` is an alias of it. Needs a duplex plugin and a deploy YAML with `session_mode: duplex` — the default `qwen3_omni_moe.yaml` is a turn deployment
  - **v0.30.0 client contract break:** `native_duplex` and the experimental client params are gone; use `auto_response` (the `full_duplex` alias was removed). Update clients written against v0.26–v0.28
  - Streaming audio in/out with cancel, barge-in, playback-aware session state, session resume. `docs/serving/realtime_duplex_api.md` is the wire contract

**Qwen3-Omni realtime + Qwen3-TTS** → `references/realtime-tts.md`
  - Turn-mode wire contract per version: v0.32.0 takes PCM16 mono 24 kHz and needs `response.create`; v0.30.0 takes 16 kHz and emits `transcription.*`
  - `async_chunk` no longer blocks realtime (v0.22.0+)
  - Qwen3-TTS CustomVoice / VoiceDesign / Base modes, 12 Hz / 25 Hz tokenizers
  - Voice-upload surface (`name` + `consent` + audio ≤10 MB or a speaker embedding; persisted under `SPEAKER_SAMPLES_DIR`)

## The top operator mistakes this skill exists to prevent

- **Old realtime advice: "turn `async_chunk` off for `/v1/realtime`"**. True only on **v0.20.x and older**, where the WebSocket rejected at connection when `async_chunk` was on. PR #3614 (v0.22.0) removed that gate and added streaming audio input under async-chunk. On v0.22.0+ realtime works with the default `vllm_omni/deploy/qwen3_omni_moe.yaml`, which ships `async_chunk: true`; `--no-async-chunk` / `--async-chunk` override the YAML (v0.28.0+). `qwen3_omni_moe_async_chunk.yaml` no longer exists — do not look for it.

- **Realtime client written for another server version**. v0.32.0 rewrote turn-mode `/v1/realtime` on the OpenAI Realtime GA event set (#8339). A client that worked on v0.30.0 hangs on v0.32.0, and the reverse writes silence:

  | | v0.30.0 | v0.32.0 |
  |---|---|---|
  | Input | PCM16 mono 16 kHz | PCM16 mono **24 kHz** |
  | Start a reply | `input_audio_buffer.commit` | `input_audio_buffer.commit`, then **`response.create`** |
  | Audio event | `response.output_audio.delta`, base64 in `audio` | `response.output_audio.delta`, base64 in **`delta`** |
  | Transcript | `transcription.delta` / `.done` | `response.output_audio_transcript.delta` / `.done` |
  | Turn end | `response.output_audio.done` | `response.done` |

  Before v0.30.0 the audio events were `response.audio.delta` / `.done` (#7339). Server VAD, tools and limits: `references/realtime-tts.md`.

- **v0.30.0 config removals that fail at load.** `diffusion_batch_size` is gone — use `max_num_seqs` (#6484). Unknown diffusion config fields now raise with the field name and stage id instead of being silently dropped (#5172) — a stale or misspelled key that used to be ignored now stops the server. First-party Dynin-Omni and dots.tts support was removed (#7655).

- **v0.32.0 changes that fail at startup.** An LLM stage's `engine_output_type` must be exactly `text`, `image`, `audio`, `latent` or `token_ids`, joined by `+` or `,` (#7843); a legacy alias, case variant or padded value raises `Unknown modality` when the output processor initialises. First-party HiDream-I1-Full (`HiDreamImagePipeline`) is gone from the registry (#9065). Python 3.10 is no longer accepted.

- **PCM format on `/v1/realtime`**. Send headerless **16-bit PCM mono** at the rate the server version expects (24 kHz on v0.32.0, 16 kHz through v0.30.0); output is 24 kHz PCM16. Stereo, the wrong rate, 24-bit, or WAV-with-header inputs produce garbage or silence. Client templates: v0.32.0 `examples/online_serving/realtime_web` (`--profile qwen3-turn`); through v0.30.0 `examples/online_serving/qwen3_omni/openai_realtime_client.py` (removed at v0.32.0).

- **`guidance_scale=0` silently enabled CFG below v0.26.0**. `0.0` was the "unset" sentinel in `OmniDiffusionSamplingParams`, so an explicit `0` was replaced by the pipeline default (HunyuanImage-3.0: `5.0`, CFG on) — every pipeline, not one model. Fixed in v0.26.0 (#4999). On older builds omit the field instead of sending `0`. CFG still gates on `guidance_scale > 1.0`, so `0.5` disables it on every version.

- **Prefix caching on a stage that emits latents**. Any stage with `engine_output_type: latent` (thinker stages producing hidden states) must set `enable_prefix_caching: false` on that stage (a flat per-stage key in the deploy YAML; the shipped Qwen3-Omni YAML sets it on every stage). Prefix cache reuses token-level blocks, which makes no sense for latent outputs — leaving it on surfaces as intermittent stale responses.

- **`/v1/videos/sync` for long jobs**. The sync endpoint times out at `VIDEO_SYNC_TIMEOUT_S` — **600 s** by default, overridable with `VLLM_OMNI_VIDEO_SYNC_TIMEOUT` (v0.24.0+; a fixed 600 s before that) — and returns 504 past it. Long Wan2.2 / HunyuanVideo-1.5 jobs should use `POST /v1/videos` (async), then poll `GET /v1/videos/{id}` and fetch `/content`.

- **Orphan processes after a Wan2.2 crash** (#2768). Killing one worker leaves sibling stage processes alive. Launch in a process group and `kill -- -<PGID>` on failure, or run under `systemd` with `KillMode=control-group`. Keep this on current builds: the issue closed without a fix PR, after a fresh reproduction.

- **Two v0.26.0 breaking changes that rename or remove things you may be using.** (1) **LTX pipeline registry names changed** (#5148): `LTX2Pipeline` is now the single one-stage entry for LTX-2 *and* LTX-2.3, T2V *and* I2V — checkpoint metadata picks the version, `image=` picks I2V. `LTX2ImageToVideoPipeline`, `LTX23Pipeline` and `LTX23ImageToVideoPipeline` were removed. On v0.32.0 the supported list names `LTX2TwoStagePipeline`, `LTX2DistilledOneStagePipeline`, `LTX2DistilledTwoStagePipeline` and `LTX2TextToAudioPipeline` (`LTX2DistilledPipeline` is still registered); the distilled rows cover LTX-2.3 and LTX-2.5 only, since `rootonchair/LTX-2-19b-distilled` was removed (#9065). Expect higher compute too: the official guidance recipe runs up to four transformer passes per denoise step (cond / uncond / STG perturbation / cross-modality). (2) **GGUF diffusion support moved out of tree** (#4769) to `vllm-project/vllm-gguf-plugin` — a GGUF DiT deployment now needs that plugin installed, and the in-core path is gone.

- **Assuming vllm-omni serves text-only models**. If the model has no multimodal output, use stock vLLM — vllm-omni adds overhead for features a text-only model won't exercise, and the community skill explicitly recommends against it. The decision rule: output modality is non-text OR the model name ends `-Omni`/`-Image`/`-TTS`/`-Video` → vllm-omni; otherwise stock vLLM.

## Operator cheat sheet

### Install

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate

# CUDA 13.0 — vLLM and omni on the same minor (needs a CUDA 13 driver):
uv pip install "vllm==0.32.0" "vllm-omni==0.32.0" --torch-backend=cu130
# OR editable: git clone -b v0.32.0 https://github.com/vllm-project/vllm-omni && cd vllm-omni && uv pip install -e .

# ROCm — validated prebuilt pair is still 0.30.0 (vLLM wheel is cp312-only):
uv pip install vllm==0.30.0+rocm723 \
  --extra-index-url https://wheels.vllm.ai/rocm/0.30.0/rocm723
uv pip install vllm-omni==0.30.0
```

Resulting CUDA stack (vLLM v0.32.0 `requirements/cuda.txt` + omni `requirements/common.txt`): PyTorch 2.13.0, FlashInfer 0.7.0.post1, torchvision 0.28.0, `transformers >= 5.16.1, < 5.20.0`, `diffusers==0.40.0`. Keep transformers inside the range of the omni version installed. Python 3.11–3.13 is declared; use 3.12 (quickstart default, and the ROCm wheel is cp312-only). A `vllm==0.32.0+rocm723` wheel exists at `https://wheels.vllm.ai/rocm/0.32.0/rocm723`, but upstream's install guide marks it unverified against the v0.32.0 source pin and there is no v0.32.0 ROCm image — treat ROCm on v0.32.0 as a test build. Docker model tags (`minimax-h3`, `qwen-image21`, `cosmos3`, …) and `nightly*` tags are not releases.

### Serving canonical forms

```bash
# Text-to-image (default Z-Image-Turbo quickstart):
vllm serve Tongyi-MAI/Z-Image-Turbo --omni --port 8091

# Qwen-Image with tensor parallelism:
vllm serve Qwen/Qwen-Image --omni --tensor-parallel-size 2 --port 8091

# Qwen3-Omni (registry loads vllm_omni/deploy/qwen3_omni_moe.yaml: stage 0 on
# cuda:0, stages 1+2 share cuda:1, async_chunk ON; serves chat + /v1/realtime).
# No global --gpu-memory-utilization: it applies to every stage and
# oversubscribes the shared GPU — tune per stage with --stage-overrides.
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni --port 8091

# Same, with chunk-level stage overlap off (overrides the YAML):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni --port 8091 --no-async-chunk

# Qwen3-TTS (--trust-remote-code required; no --enforce-eager, CUDA graphs work):
vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --omni \
  --trust-remote-code --task-type CustomVoice

# Wan2.2 T2V with Ulysses sequence parallel:
vllm serve Wan-AI/Wan2.2-T2V-A14B-Diffusers --omni \
  --ulysses-degree 4 --ulysses-mode strict --port 8091
```

### Common extra flags

| Flag | Purpose |
|---|---|
| `--omni` | Enable vllm-omni entrypoint (load-bearing) |
| `--deploy-config` | Stage-config YAML. **`--stage-configs-path` and the legacy `stage_args` loader were REMOVED at v0.28.0** — with them went `vllm_omni/deploy/qwen3_omni_moe_async_chunk.yaml`. Use `--deploy-config` plus the `--async-chunk` / `--no-async-chunk` override. |
| `--stage-overrides` | Per-stage JSON, e.g. `'{"0": {"gpu_memory_utilization": 0.8}}'` — use instead of global engine flags on multi-stage models |
| `--task-type` | Qwen3-TTS: `CustomVoice` \| `VoiceDesign` \| `Base` |
| `--ulysses-degree` / `--usp` | Ulysses sequence parallelism for DiT |
| `--ulysses-mode` | `strict` (divisibility) \| `advanced_uaa` (uneven shapes) |
| `--ring-degree` | Ring-based parallelism |
| `--num-gpus` | GPUs allocated to diffusion pipeline |
| `--omni-master-address` / `-oma` | Orchestrator hostname (multi-node) |
| `--omni-master-port` / `-omp` | Orchestrator port |
| `--stage-id` | Single-stage mode (requires master address) |
| `--worker-backend` | `multi_process` \| `ray` |
| `--model-class-name` | Override diffusion pipeline class |

### Key numbers to memorize

| Metric | Value |
|---|---|
| `/v1/realtime` input | PCM16 mono @ 24 kHz on v0.32.0; 16 kHz through v0.30.0 |
| Qwen3-Omni audio output rate | 24 kHz |
| Qwen3-TTS tokenizer rate | 12 Hz or 25 Hz |
| `/v1/videos/sync` timeout | 600 s default; `VLLM_OMNI_VIDEO_SYNC_TIMEOUT` overrides (v0.24.0+) |
| Voice upload size cap | 10 MB |
| Paper claim | up to 91.4% JCT reduction vs "baseline" (unspecified) |
| Qwen3-TTS published RTF (v0.16) | 0.22–0.45 |
| MiMo-Audio published RTF (v0.16) | ~0.2 (11× baseline) |

## Paired skills

- **`vllm-input-modalities`** — the complement: text embeddings, reranking, STT (Whisper/Voxtral-STT/Qwen3-ASR), OCR (DeepSeek-OCR). Trigger together when the deployment does both input and output non-text modalities.
- **`vllm-nvidia-hardware`** — for sizing GB300/NVL72/Rubin capacity for diffusion + CFG-parallel + Ulysses footprints.
- **`vllm-caching`** — OmniConnector borrows Mooncake from upstream vLLM; the caching skill has the connector-config surface.
- **`vllm-observability`** — vllm-omni inherits upstream `/metrics`; profiler hooks (`OmniTorchProfilerWrapper`) add stage_id + rank awareness to trace files.

## Source policy

All claims are cited with file:line, release-note PR refs, or issue IDs. Full anchor list, version history, community channels and third-party plugin catalog in `references/sources.md`.

`references/models.md` mirrors upstream's list at v0.32.0 only — on any other tag, read `docs/models/supported_models.md` at that tag before calling a model unsupported.
