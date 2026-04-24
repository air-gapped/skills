---
name: vllm-omni
description: |-
  vLLM-Omni output-side multimodal generation — image (FLUX.1/2, Qwen-Image, GLM-Image, BAGEL, SD3.5, HunyuanImage-3.0), video (Wan2.1/2.2, LTX-2, HunyuanVideo-1.5), TTS (Qwen3-TTS, CosyVoice3, Voxtral-TTS), any-to-any omni (Qwen3-Omni, Qwen2.5-Omni, MiMo-Audio) via `vllm serve --omni`. Stage-based disaggregation (OmniConnector + Mooncake + RDMA), `/v1/images/generations`, async+sync `/v1/videos`, `/v1/audio/speech` with voice-upload, PCM16 WebSocket `/v1/realtime`, Ulysses/Ring SP + CFG-parallel, DiT FP8/INT8/GGUF, CUDA/ROCm/NPU/XPU/MUSA matrix, release pitfalls (v0.19.0rc1 FLUX regression, GLM-Image transformers>=5.0, Qwen3-TTS enforce-eager).
when_to_use: |-
  Trigger on any vLLM deployment producing non-text output (image/video/audio) or any-to-any omni model, or model names ending `-Image`/`-TTS`/`-Omni`/`-Video`. Keywords — `vllm serve --omni`, `vllm-omni`, `/v1/images/generations`, `/v1/videos`, `/v1/audio/speech`, `/v1/audio/voices`, `/v1/realtime`, `async_chunk`, `stage_configs_path`, OmniConnector, MooncakeStore, OmniDiffusionSamplingParams, FlowUniPC, TeaCache, Cache-DiT, Sage/Ring/Ulysses, `--ulysses-degree`, `--ring-degree`, CFG-parallel, Thinker/Talker/Code2Wav, BAGEL, Wan2.2, FLUX.2-klein, DiT FP8/INT8/GGUF, ComfyUI bridge, verl RL. Narrow phrasings — "serve Qwen-Image", "Qwen3-Omni streaming audio", "async video job". Also implicit — "deploy image gen", "TTS endpoint", "video gen pipeline", "audit omni", "deploy-memo for {model}-Image/-TTS/-Video". NOT for embeddings/reranking/STT/OCR (→ `vllm-input-modalities`).
---

# vLLM-Omni — output-side multimodal serving

Target: operators who serve image / video / audio / any-to-any generation models with the vLLM-Omni fork of vLLM. vllm-omni extends upstream vLLM (same CUDA/ROCm/NPU/XPU runtime, same OpenAI-compat API server) to add non-autoregressive DiT models, multi-stage pipeline execution, diffusion schedulers, CFG plumbing, and real-time streaming audio I/O — things upstream vLLM does not ship.

This skill is a **reference**, not a tutorial. SKILL.md holds the mental model, quick-answer router, top pitfalls, and operator cheat sheet. The `references/` files hold endpoint catalogs, supported-model tables, stage-config grammar, and the diffusion/DiT details. Read only the reference file that matches the question.

## The one thing to know before anything else

vllm-omni is **not a fork** — it sits on top of upstream vLLM via `patch.py` (early-import), registers OmniModelConfig, and adds one CLI flag: `--omni`. Adding `--omni` to `vllm serve` routes the server through `vllm_omni.entrypoints`. The architectural claim is to decompose any-to-any models into a **graph of disaggregated stages** (Thinker / Talker / Code2Wav for Qwen3-Omni; AR-encoder / DiT for Qwen-Image) connected via `OmniConnector`, so each stage scales independently. The paper (arXiv:2602.02204) claims up to 91.4% JCT reduction vs an unspecified baseline — treat as an architectural argument, not a deployment benchmark.

Version alignment is strict: vllm-omni major.minor must match upstream vLLM major.minor. **v0.18.0 (2026-03-28) is the current stable**, rebased on vLLM v0.18.0. First stable was v0.14.0 (2026-01-31). **v0.19.0rc1 has a FLUX.1-dev regression (#2730)** — fix merged to `main` 2026-04-24 via PR #2760 but **not yet re-tagged**; pin v0.18.0 in production until the next release ships.

## Quick-answer router

**Serving a specific endpoint** → `references/endpoints.md`
  - `/v1/images/generations`, `/v1/images/edits` (DALL·E-shape)
  - `/v1/videos` (async job) + `/v1/videos/sync` (raw MP4, 1200s timeout)
  - `/v1/audio/speech`, `/v1/audio/voices` (list + upload), `/v1/audio/speech/batch`, `/v1/audio/speech/stream` (WebSocket)
  - `/v1/realtime` (WebSocket PCM16 in/out for Qwen3-Omni)
  - `/v1/chat/completions` with diffusion via `extra_body`

**Picking a model** → `references/models.md`
  - Full supported-architecture → HuggingFace-ID table
  - Per-model platform matrix (CUDA / ROCm / NPU / XPU / MUSA)
  - Known-issue flags per family

**Writing / debugging stage configs** → `references/stage-config.md`
  - OmniModelConfig + StageConfig YAML grammar
  - OmniConnector types (Shared-memory / Mooncake-Store / Mooncake-Transfer-Engine / RDMA / Yuanrong)
  - Pipeline edge validation, entry-point requirement
  - `stage_id`, `model_stage`, `worker_type`, `engine_output_type`, `async_chunk`

**DiT-specific questions** → `references/diffusion.md`
  - Schedulers (FlowUniPC + model-specific)
  - CFG plumbing (dual CFG for Wan2.2, true_cfg_scale for Qwen-Image, cfg_branch_past_key_values)
  - Caches: TeaCache / Cache-DiT / latent cache / noise_pred cache
  - Quantization: FP8 (Flux #1640), INT8 (Z-Image/Qwen-Image #1470), GGUF (#1755) — all per-component via `ComponentQuantizationConfig`
  - Ulysses / Ring sequence parallel, CFG-parallel merged-batch TP

**Qwen3-Omni realtime + Qwen3-TTS** → `references/realtime-tts.md`
  - PCM16 mono @ 16 kHz in / 24 kHz out, OpenAI realtime event shape
  - `async_chunk: false` requirement
  - Qwen3-TTS CustomVoice / VoiceDesign / Base modes, 12 Hz / 25 Hz tokenizers
  - Voice-upload surface (10 MB cap, consent/ref_text/speaker_description required)

## The top operator mistakes this skill exists to prevent

1. **`/v1/realtime` with `async_chunk: true`**. The realtime WebSocket rejects at connection if `async_chunk` is enabled (api_server.py:1208). Use the default stage-config (`vllm_omni/model_executor/stage_configs/qwen3_omni_moe.yaml`) — **not** the `...moe_async_chunk.yaml` variant — for realtime sessions. The async-chunk config is for higher-throughput non-realtime Qwen3-Omni serving.

2. **Qwen3-TTS with CUDA graphs on**. Issue #2866: code2wav stage crashes when `enforce_eager: false`. Always launch Qwen3-TTS with `--enforce-eager --trust-remote-code` until the upstream fix lands. This is a production-blocker that the docs do not yet warn about.

3. **Pinning v0.19.0rc1 instead of v0.18.0**. Issue #2730 reports FLUX.1-dev generates incorrect images in v0.19.0rc1 (T5 text encoder bug). **Fix merged to `main` 2026-04-24 via PR #2760** but no re-tagged release yet, so the rc1 tag artifacts are still broken. rc1 releases are not production targets — stay on v0.18.0 stable for any FLUX deployment until the next RC/stable ships.

4. **GLM-Image on v0.18 without `transformers>=5.0`**. Release notes call this out: GLM-Image requires a manual `pip install 'transformers>=5.0'` before serving. The default wheel pins transformers below 5.0 and GLM-Image silently fails to load.

5. **PCM format on `/v1/realtime`**. Qwen3-Omni realtime hard-expects **16-bit PCM mono @ 16 kHz input**, outputs PCM at 24 kHz. Stereo, 8 kHz, 24-bit, or WAV-with-header inputs produce garbage or silent failures. Use the reference client in `examples/online_serving/qwen3_omni/openai_realtime_client.py` as a template.

6. **Default `guidance_scale=0.0` sentinel**. OmniDiffusionSamplingParams treats `guidance_scale=0.0` as "not provided" — passing `0.5` intending partial CFG gets coerced. To disable CFG, leave the field unset; to enable, pass `> 1.0`.

7. **Prefix caching on a stage that emits latents**. Any stage with `engine_output_type: latent` (thinker stages producing hidden states) must set `enable_prefix_caching: false` in its `engine_args`. Prefix cache reuses token-level blocks, which makes no sense for latent outputs — leaving it on surfaces as intermittent stale responses.

8. **`/v1/videos/sync` for long jobs**. The sync endpoint has a hardcoded `VIDEO_SYNC_TIMEOUT_S` (default ~1200s) and returns 504 past that. Long Wan2.2 / HunyuanVideo-1.5 jobs should use `POST /v1/videos` (async), then poll `GET /v1/videos/{id}` and fetch `/content`.

9. **Orphan processes after a Wan2.2 crash**. Issue #2768: killing one Wan2.2 worker leaves sibling stage processes alive. Wrap launches in a process group + `pkill -9` sweep on failure, or use `systemd`'s `KillMode=control-group`.

10. **Assuming vllm-omni serves text-only models**. If the model has no multimodal output, use stock vLLM — vllm-omni adds overhead for features a text-only model won't exercise, and the community skill explicitly recommends against it. The decision rule: output modality is non-text OR the model name ends `-Omni`/`-Image`/`-TTS`/`-Video` → vllm-omni; otherwise stock vLLM.

## Operator cheat sheet

### Install

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate

# CUDA — pin upstream vLLM to the matching minor:
uv pip install vllm==0.18.0 --torch-backend=auto

# ROCm:
uv pip install vllm==0.18.0+rocm700 \
  --extra-index-url https://wheels.vllm.ai/rocm/0.18.0/rocm700

# Then the omni package (prebuilt wheel OR editable clone):
uv pip install vllm-omni==0.18.0
# OR: git clone https://github.com/vllm-project/vllm-omni && cd vllm-omni && uv pip install -e .
```

Python **3.12 is required** (3.11 is not supported). Docker image: `vllm/vllm-omni:0.18.0`.

### Serving canonical forms

```bash
# Text-to-image (default Z-Image-Turbo quickstart):
vllm serve Tongyi-MAI/Z-Image-Turbo --omni --port 8091

# Qwen-Image with tensor parallelism:
vllm serve Qwen/Qwen-Image --omni --tensor-parallel-size 2 --port 8091

# Qwen3-Omni realtime (default stage config, async_chunk OFF):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  --tensor-parallel-size 2 --gpu-memory-utilization 0.9 --port 8091

# Qwen3-Omni high-throughput non-realtime (async_chunk ON):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  --stage-configs-path vllm_omni/model_executor/stage_configs/qwen3_omni_moe_async_chunk.yaml

# Qwen3-TTS (always eager, always trust-remote-code):
vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --omni \
  --enforce-eager --trust-remote-code --task-type CustomVoice

# Wan2.2 T2V with Ulysses sequence parallel:
vllm serve Wan-AI/Wan2.2-T2V-A14B-Diffusers --omni \
  --ulysses-degree 4 --ulysses-mode strict --port 8091
```

### Common extra flags

| Flag | Purpose |
|---|---|
| `--omni` | Enable vllm-omni entrypoint (load-bearing) |
| `--stage-configs-path` | Override default stage-config YAML |
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
| Current stable | v0.18.0 (2026-03-28, rebased on vLLM v0.18.0) |
| First stable | v0.14.0 (2026-01-31) |
| Minimum Python | 3.12 |
| `/v1/realtime` input | PCM16 mono @ 16 kHz |
| Qwen3-Omni audio output rate | 24 kHz |
| Qwen3-TTS tokenizer rate | 12 Hz or 25 Hz |
| `/v1/videos/sync` timeout | ~1200s (hard) |
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

All claims are cited with file:line, release-note PR refs, or issue IDs. Full anchor list + community channels + third-party plugin catalog in `references/sources.md`. Compiled 2026-04-18 against v0.18.0; last freshened 2026-04-24 (v0.18.0 still stable; refresh again when the next upstream-rebase release ships).
