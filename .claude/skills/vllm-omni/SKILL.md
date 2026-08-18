---
name: vllm-omni
description: |-
  vLLM-Omni output-side multimodal generation — image (FLUX.1/2, Qwen-Image, GLM-Image, BAGEL, SD3.5, HunyuanImage-3.0), video (Wan2.1/2.2, LTX-2, HunyuanVideo-1.5), TTS (Qwen3-TTS, CosyVoice3, Voxtral-TTS), any-to-any omni (Qwen3-Omni, Qwen2.5-Omni, MiMo-Audio) via `vllm serve --omni`. Stage-based disaggregation (OmniConnector + Mooncake + RDMA), `/v1/images/generations`, async+sync `/v1/videos`, `/v1/audio/speech` with voice-upload, PCM16 WebSocket `/v1/realtime`, Ulysses/Ring SP + CFG-parallel, DiT FP8/INT8/GGUF, CUDA/ROCm/NPU/XPU/MUSA matrix, release pitfalls (v0.19.0rc1 FLUX regression, GLM-Image transformers>=5.0, Qwen3-TTS enforce-eager).
when_to_use: |-
  Trigger on any vLLM deployment producing non-text output (image/video/audio) or any-to-any omni model, or model names ending `-Image`/`-TTS`/`-Omni`/`-Video`. Keywords — `vllm serve --omni`, `vllm-omni`, `/v1/images/generations`, `/v1/videos`, `/v1/audio/speech`, `/v1/audio/voices`, `/v1/realtime`, `async_chunk`, `stage_configs_path`, OmniConnector, MooncakeStore, OmniDiffusionSamplingParams, FlowUniPC, TeaCache, Cache-DiT, Sage/Ring/Ulysses, `--ulysses-degree`, `--ring-degree`, Thinker/Talker/Code2Wav, BAGEL, Wan2.2, FLUX.2-klein, ComfyUI bridge, verl RL. Narrow phrasings — "serve Qwen-Image", "Qwen3-Omni streaming audio", "async video job". Also implicit — "deploy image gen", "TTS endpoint", "video gen pipeline", "audit omni", "deploy-memo for {model}-Image/-TTS/-Video". NOT for embeddings/reranking/STT/OCR (→ `vllm-input-modalities`).
---

# vLLM-Omni — output-side multimodal serving

Target: operators who serve image / video / audio / any-to-any generation models with the vLLM-Omni fork of vLLM. vllm-omni extends upstream vLLM (same CUDA/ROCm/NPU/XPU runtime, same OpenAI-compat API server) to add non-autoregressive DiT models, multi-stage pipeline execution, diffusion schedulers, CFG plumbing, and real-time streaming audio I/O — things upstream vLLM does not ship.

This skill is a **reference**, not a tutorial. SKILL.md holds the mental model, quick-answer router, top pitfalls, and operator cheat sheet. The `references/` files hold endpoint catalogs, supported-model tables, stage-config grammar, and the diffusion/DiT details. Read only the reference file that matches the question.

## The one thing to know before anything else

vllm-omni is **not a fork** — it layers on top of upstream vLLM, registers OmniModelConfig, and adds one CLI flag: `--omni`. Adding `--omni` to `vllm serve` routes the server through `vllm_omni.entrypoints`. As of v0.20.0 the old vLLM entrypoint-hijack / `patch.py` early-import mechanism was **removed** — the v0.20.0 release notes state "removal of the old vLLM entrypoint hijack, and runtime changes needed for the 0.20.0 integration path (#3232, #3082, #3352, #3393, #2306)". The omni runtime is rebased onto upstream vLLM rather than monkey-patching it — v0.20.0 via PR #3232, then forward through the v0.21/v0.22 rebases (#3530, #3891) and the v0.23.0/v0.24.0 rebases (#4286, #4709). The architectural claim is to decompose any-to-any models into a **graph of disaggregated stages** (Thinker / Talker / Code2Wav for Qwen3-Omni; AR-encoder / DiT for Qwen-Image) connected via `OmniConnector`, so each stage scales independently. The paper (arXiv:2602.02204) claims up to 91.4% JCT reduction vs an unspecified baseline — treat as an architectural argument, not a deployment benchmark.

Version alignment is strict: vllm-omni major.minor must match upstream vLLM major.minor. **v0.26.0 (2026-08-03) is the current stable**, rebased on upstream vLLM 0.26.0 (#5443); first stable was v0.14.0 (2026-01-31). The v0.19.0rc1 FLUX.1-dev regression (#2730) is **fixed in v0.20.0 stable** (PR #2760) — no version pin needed anymore.

**Not every minor gets a stable.** v0.21.0, v0.23.0 and v0.25.0 exist only as
`rc1` — the stable line went v0.20.0 → v0.22.0 → v0.24.0 → v0.24.1 → v0.26.0.
Don't infer a missing release is a withdrawn one.

### The v0.24.1 channel mismatch is resolved — but keep checking channels

Verified 2026-08-11. All three channels now agree on **v0.26.0**:

| Channel | Newest | Checked |
|---|---|---|
| GitHub releases | **v0.26.0** (2026-08-03), marked Latest | `gh release list` |
| PyPI | **0.26.0** (2026-08-03) | `pypi.org/pypi/vllm-omni/json` |
| Docker Hub | **v0.26.0** (2026-08-03); `latest` matches no versioned tag — it tracks the unversioned `vtest-nightly` build | Docker Hub v2 tags API |

The 2026-07-21 finding — v0.24.1 existing as a GitHub tag with no wheel and no
image — is now **moot, not fixed**: v0.24.1 was never uploaded to PyPI, but
v0.26.0 supersedes it everywhere, and the Qwen-Image fix it carried (#5017,
issue #4964) is in v0.26.0 by descent. Nobody needs the `git+…@v0.24.1` install
form any more.

Two things carry forward. First, **`latest` on Docker Hub is not a released
version**: as of 2026-08-18 its digests match no versioned tag at all — it
tracks the unversioned `vtest-nightly` build. Pin the exact tag. Second, the underlying
lesson stands — a tag is not a wheel — so check all three channels before
quoting a version, rather than assuming this pass's parity is permanent.

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
  - Quantization: FP8 (Flux #1640), INT8 (Z-Image/Qwen-Image #1470) per-component via `ComponentQuantizationConfig`; **GGUF moved out of tree in v0.26.0** (#4769) to `vllm-project/vllm-gguf-plugin`
  - Ulysses / Ring sequence parallel, CFG-parallel merged-batch TP

**Full-duplex realtime (experimental, v0.26.0)** — MiniCPM-o 4.5 only
  - Native `/v1/duplex` plus a Realtime-compatible `/v1/realtime?duplex=1` (#3907)
  - Streaming audio in/out with cancel, barge-in, overlap policy, playback-aware session state
  - Explicitly a **preview**: no persistent KV leases, no multi-session/multi-replica admission or recovery, no byte-for-byte OpenAI Realtime compatibility. Don't plan production capacity on it.

**Qwen3-Omni realtime + Qwen3-TTS** → `references/realtime-tts.md`
  - PCM16 mono @ 16 kHz in / 24 kHz out, OpenAI realtime event shape
  - `async_chunk: false` requirement
  - Qwen3-TTS CustomVoice / VoiceDesign / Base modes, 12 Hz / 25 Hz tokenizers
  - Voice-upload surface (10 MB cap, consent/ref_text/speaker_description required)

## The top operator mistakes this skill exists to prevent

- **`/v1/realtime` with `async_chunk: true`**. The realtime WebSocket rejects at connection if `async_chunk` is enabled (api_server.py:1208). Use the default stage-config (`vllm_omni/deploy/qwen3_omni_moe.yaml`) — **not** the `...moe_async_chunk.yaml` variant — for realtime sessions. The async-chunk config is for higher-throughput non-realtime Qwen3-Omni serving.

- **Qwen3-TTS with CUDA graphs on (v0.18 only)**. Issue #2866: on v0.18 the code2wav stage crashed when `enforce_eager: false`, so `--enforce-eager` was mandatory. **#2866 is CLOSED (2026-04-29)** and v0.20.0 ships TTS CUDA-graph capture + shared memory pools (release notes cite #2690/#2758/#2803), lifting the requirement. On v0.20.0+ keep `--trust-remote-code` but `--enforce-eager` is no longer forced — drop it to regain CUDA-graph throughput, and re-test latency.

- **Running the v0.19.0rc1 FLUX artifacts**. Issue #2730: FLUX.1-dev generated incorrect images in v0.19.0rc1 (T5 text-encoder bug). **Fixed in v0.20.0 stable** (PR #2760, merged 2026-04-24). The v0.19.0rc1 tag artifacts are still broken, so do not deploy that specific tag — use v0.20.0+ for any FLUX deployment.

- **GLM-Image on v0.18 without `transformers>=5.0`** — historical only, resolved. On v0.18 GLM-Image needed a manual `pip install 'transformers>=5.0'` because the wheel pinned transformers below 5.0 and the model silently failed to load. v0.20.0 shipped Transformers 5.x compat fixes, and **v0.26.0's own `requirements/common.txt` floors transformers at `>= 5.5.3`** (kept deliberately aligned with the upstream vLLM constraint). No manual upgrade on any current build.

- **PCM format on `/v1/realtime`**. Qwen3-Omni realtime hard-expects **16-bit PCM mono @ 16 kHz input**, outputs PCM at 24 kHz. Stereo, 8 kHz, 24-bit, or WAV-with-header inputs produce garbage or silent failures. Use the reference client in `examples/online_serving/qwen3_omni/openai_realtime_client.py` as a template.

- **`guidance_scale=0` was silently ignored below v0.26.0**. `OmniDiffusionSamplingParams.guidance_scale` used `0.0` as its "unset" default, so an explicit `0` could not be distinguished from an omitted value and the pipeline's own default was substituted instead — HunyuanImage-3.0's `5.0`, for example, which *enables* CFG. Not model-specific: the collision was in the shared input layer, so every pipeline that substitutes a default was affected. **Fixed in v0.26.0** (#4999, fixes #4998) by making `None` the sentinel and testing presence by identity. On v0.26.0+ `guidance_scale=0` means what it says. On older builds, omit the field to disable CFG rather than sending `0`. The CFG gate is still `guidance_scale > 1.0`, so a value like `0.5` disables CFG on every version.

- **Prefix caching on a stage that emits latents**. Any stage with `engine_output_type: latent` (thinker stages producing hidden states) must set `enable_prefix_caching: false` in its `engine_args`. Prefix cache reuses token-level blocks, which makes no sense for latent outputs — leaving it on surfaces as intermittent stale responses.

- **`/v1/videos/sync` for long jobs**. The sync endpoint has a hardcoded `VIDEO_SYNC_TIMEOUT_S` (default ~1200s) and returns 504 past that. Long Wan2.2 / HunyuanVideo-1.5 jobs should use `POST /v1/videos` (async), then poll `GET /v1/videos/{id}` and fetch `/content`.

- **Orphan processes after a Wan2.2 crash**. Issue #2768: killing one Wan2.2 worker leaves sibling stage processes alive. Wrap launches in a process group + `pkill -9` sweep on failure, or use `systemd`'s `KillMode=control-group`. **#2768 now reads CLOSED/COMPLETED (2026-05-16) but keep the mitigation** — the last comment on the thread (2026-05-12, four days before closure) is a *fresh reproduction* by a different reporter, with no fix PR referenced. Treat the closure as bookkeeping, not as a fix.

- **Two v0.26.0 breaking changes that rename or remove things you may be using.** (1) **LTX pipeline registry names changed** (#5148): `LTX2Pipeline` is now the single one-stage entry for LTX-2 *and* LTX-2.3, T2V *and* I2V — checkpoint metadata picks the version, `image=` picks I2V. `LTX2ImageToVideoPipeline`, `LTX23Pipeline` and `LTX23ImageToVideoPipeline` were removed; the distilled two-stage path is now `LTX2DistilledPipeline`. Expect higher compute too: the official guidance recipe runs up to four transformer passes per denoise step (cond / uncond / STG perturbation / cross-modality). (2) **GGUF diffusion support moved out of tree** (#4769) to `vllm-project/vllm-gguf-plugin` — a GGUF DiT deployment now needs that plugin installed, and the in-core path is gone.

- **Qwen3-TTS `max_model_len` validation error**. Issue #2595 (closed 2026-04-28): serving fails when `max_model_len` exceeds the derived maximum. The recorded workaround is `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (see PR #2508). The thread closed on that workaround rather than on a root-cause fix, so expect it to still be needed.

- **Assuming vllm-omni serves text-only models**. If the model has no multimodal output, use stock vLLM — vllm-omni adds overhead for features a text-only model won't exercise, and the community skill explicitly recommends against it. The decision rule: output modality is non-text OR the model name ends `-Omni`/`-Image`/`-TTS`/`-Video` → vllm-omni; otherwise stock vLLM.

## Operator cheat sheet

### Install

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate

# CUDA — pin upstream vLLM to the matching minor:
uv pip install vllm==0.26.0 --torch-backend=auto

# ROCm — note the index moved to rocm723:
uv pip install vllm==0.26.0+rocm723 \
  --extra-index-url https://wheels.vllm.ai/rocm/0.26.0/rocm723

# Then the omni package (prebuilt wheel OR editable clone):
uv pip install vllm-omni==0.26.0
# OR: git clone https://github.com/vllm-project/vllm-omni && cd vllm-omni && uv pip install -e .
```

**Do not reach for upstream vLLM 0.27.x here.** vllm-omni v0.26.0 is rebased on
vLLM **0.26.0** and the minor must match, so this stack is on **PyTorch 2.11.0
and FlashInfer 0.6.14** (vLLM v0.26.0 `requirements/cuda.txt`) — not the 2.13.0
/ 0.6.16 pair that upstream v0.27.0 moved to. Transformers floor is
`>= 5.5.3`, kept deliberately aligned with upstream (vllm-omni
`requirements/common.txt`), alongside `diffusers==0.38.0`.

Python **3.12 is required** (3.11 is not supported). Docker image:
`vllm/vllm-omni:v0.26.0` (`-x86_64` / `-aarch64` variants published per tag);
ROCm images live in a **separate** repo, `vllm/vllm-omni-rocm:v0.26.0`. Pin the
exact tag: `latest` tracks an unversioned nightly, not a release. Model-specific
builds also appear on the tag list (`cosmos3`, `minimax-h3`, `minimax-h3-cu129`)
— those are not releases.

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
  --stage-configs-path vllm_omni/deploy/qwen3_omni_moe_async_chunk.yaml

# Qwen3-TTS (trust-remote-code; --enforce-eager only required on v0.18, lifted by TTS CUDA-graph capture in v0.20.0+):
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
| Current stable, all channels | **v0.26.0** (2026-08-03), rebased on vLLM 0.26.0 (#5443) |
| Docker `latest` resolves to | the unversioned `vtest-nightly` build — matches no release, pin the exact tag |
| Latest pre-release | v0.26.0rc1 (2026-07-28) |
| Stables in the line | v0.14.0, v0.16.0, v0.18.0, v0.20.0, v0.22.0, v0.24.0, v0.24.1, v0.26.0 (v0.21/v0.23/v0.25 are rc1-only) |
| First stable | v0.14.0 (2026-01-31) |
| Minimum Python | 3.12 |
| Runtime pins (via vLLM 0.26.0) | PyTorch 2.11.0, FlashInfer 0.6.14, transformers >= 5.5.3, diffusers 0.38.0 |
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

All claims are cited with file:line, release-note PR refs, or issue IDs. Full anchor list + community channels + third-party plugin catalog in `references/sources.md`. Compiled 2026-04-18 against v0.18.0; freshened 2026-05-28 (v0.20.0) and 2026-07-21 (v0.24.0/v0.24.1, channel mismatch, six issue closures re-classified). **Last freshened 2026-08-11** — rebased to v0.26.0, recorded its two breaking changes (LTX registry renames, GGUF out of tree), and closed the long-open `guidance_scale=0` and GLM-Image `transformers` questions against source.

**Known gap, now larger:** the model roster in `references/models.md` has not been re-synced against `docs/models/supported_models.md` since 2026-04-18 — five minors. On top of the v0.22.0/v0.24.0 additions (Cosmos3, DreamZero, Higgs Audio V3, IndexTTS2, Step-Audio2, SDXL, GR00T-N1.7, MiniCPM-o 4.5), v0.26.0 adds MiniMax H3 (joint video+audio), Krea 2, Boogu Image 0.1, Nemotron Audex, LingBot Video, MammothModa2-Dev, Cosmos3 Edge/Distilled and MOSS-TTS-Local v1.5. Treat that file as a floor, not a complete list.
