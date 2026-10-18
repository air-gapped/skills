# vllm-omni endpoint catalog

Load when operator asks about a specific API endpoint's shape, streaming, auth, or payload fields. Source: `vllm_omni/entrypoints/openai/api_server.py`, `vllm_omni/entrypoints/openai/protocol/*.py`, `docs/serving/*.md`, and the reference clients in `examples/online_serving/`.

**Contents:** Endpoint map · `/v1/images/generations` · `/v1/images/edits` · `/v1/audio/speech` · `/v1/audio/voices` · `/v1/audio/speech/stream` · `/v1/videos` (async vs sync) · `/v1/realtime` · `/v1/chat/completions` with diffusion.

## Endpoint map (paths and field tables verified at v0.30.0)

Also registered at v0.30.0, not detailed here: `/v1/audio/generate` (POST),
`/v1/realtime/video` and `/v1/video/chat/stream` (WebSocket), `/v1/omni/sleep` /
`/v1/omni/wakeup` (POST), RL rollout `/v1/realtime/sessions…` (POST/GET).

| Path | Method | Purpose |
|---|---|---|
| `/v1/chat/completions` | POST | Multimodal chat + omni; diffusion via `extra_body` |
| `/v1/images/generations` | POST | DALL·E-shape text-to-image |
| `/v1/images/edits` | POST | DALL·E-shape image edit (multipart) |
| `/v1/audio/speech` | POST | OpenAI-shape TTS (WAV/PCM/FLAC/MP3/OPUS) |
| `/v1/audio/speech/batch` | POST | Batched TTS |
| `/v1/audio/speech/stream` | WebSocket | Streaming TTS (text in → audio-per-sentence out) |
| `/v1/audio/voices` | GET | List speakers (built-in + uploaded) |
| `/v1/audio/voices` | POST | Upload custom voice (multipart: audio ≤10 MB or a speaker embedding) |
| `/v1/videos` | POST | **Async** video job (returns job metadata) |
| `/v1/videos/sync` | POST | **Sync** video (raw MP4 bytes; 600 s default timeout) |
| `/v1/videos` | GET | List video jobs (query: `after`, `limit`, `order`) |
| `/v1/videos/{id}` | GET | Job metadata |
| `/v1/videos/{id}/content` | GET | Raw MP4 bytes |
| `/v1/videos/{id}` | DELETE | Delete job + artifacts |
| `/v1/realtime` | WebSocket | PCM16 realtime (Qwen3-Omni turn mode) |
| `/v1/realtime?duplex=1`, `/v1/duplex` | WebSocket | Full-duplex session (duplex deployments only; `/v1/duplex` is an alias) |
| `/health` | GET | `{"status":"healthy"}`; 503 `unhealthy` when no engine |
| `/v1/models` | GET | List loaded models (diffusion too, since v0.14 #454) |

## `/v1/images/generations`

DALL·E-compatible (`ImageGenerationRequest`, `protocol/images.py`). `response_format`: `b64_json` (default) or `file` (raw image bytes; a zip when `n > 1`); `url` is declared but not implemented. `size` is `"WIDTHxHEIGHT"` — Qwen-Image respects bucket sizes (640/1024/1536). A `model` that differs from the served model returns **400 "Model mismatch"**.

```bash
curl http://localhost:8091/v1/images/generations \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen-Image",
    "prompt": "a photo of a sea otter on a surfboard",
    "n": 1,
    "size": "1024x1024",
    "num_inference_steps": 30,
    "guidance_scale": 4.0,
    "true_cfg_scale": 1.0,
    "seed": 42,
    "negative_prompt": "blurry, low quality"
  }'
```

Non-OpenAI extensions:

| Field | Type | Purpose |
|---|---|---|
| `negative_prompt` | string | CFG negative branch |
| `num_inference_steps` | int 1-200 | Diffusion steps; omitted = model default |
| `guidance_scale` | float 0-20 | CFG scale (>1.0 to enable). v0.26.0+: omitted = model default, `0` = off. Below v0.26.0 `0` was the "not provided" sentinel — omit the field instead |
| `true_cfg_scale` | float 0-20 | Qwen-Image variant; ignored by models without it |
| `flow_shift` | float | Scheduler sigma shift (flow-matching models) |
| `seed` | int64 | Reproducibility |
| `generator_device` | `"cpu"` / `"cuda"` | Seeded generator device; default is the runner's device |
| `system_prompt`, `use_system_prompt` | str, str | `use_system_prompt` ∈ `dynamic`, `en_vanilla`, `en_recaption`, `en_think_recaption`, `en_unified`, `custom` (`custom` reads `system_prompt`); any other value → 422 |
| `bot_task` | str | Model-specific task mode, e.g. `cot` |
| `lora` | dict | Per-request LoRA adapter spec |
| `vae_use_slicing`, `vae_use_tiling` | bool | VAE memory optimizations |
| `layers` | int 2-10 | Layered image models |
| `output_format`, `output_compression` | `png`/`jpeg`/`webp`, 0-100 | Encoding; compression is quality for jpeg/webp, speed-vs-size for png (100 = fastest) |
| `extra_params` | dict | Passed to the model's `extra_args` |
| `return_stage_metrics` | bool | Per-request metrics in the response `metrics` field |

Response: `{"created": <ts>, "data": [{"b64_json": "...", "revised_prompt": null}], "output_format", "size"}`, plus `cot_output` for CoT-enabled edit models.

**Gotcha**: Python OpenAI SDK doesn't have fields for the non-OpenAI extras. Use curl, or pass them through the SDK's `extra_body` (if translating to `/v1/chat/completions` with diffusion).

## `/v1/images/edits`

Multipart/form-data. Input image(s) as `image` / `image[]` files or `url` / `url[]` strings; extensions `mask_image`, `reference_image`, `strength`, `guidance_scale_2`, `resolution` (layered models), plus the diffusion fields above. `stream=true` emits `image.edit.chunk` events (`ar_delta` text from the AR stage, then `image`). Same 400 on model mismatch.

## `/v1/audio/speech`

OpenAI TTS shape + Qwen3-TTS extensions (`OpenAICreateSpeechRequest`, `protocol/audio.py`).

```bash
curl http://localhost:8091/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "input": "Hello from vllm-omni.",
    "voice": "vivian",
    "response_format": "wav",
    "speed": 1.0
  }' --output out.wav
```

Fields:

| Field | Type | Purpose |
|---|---|---|
| `model` | string | TTS model name |
| `input` | string | Text to synthesize |
| `voice` / `speaker` | string, or `{"id": ...}` | Speaker name; Qwen3-TTS CustomVoice presets are `vivian`, `ryan`, `aiden`, … |
| `instructions` | string | Style/emotion (Qwen3-TTS `instruct`) |
| `response_format` | `wav` / `pcm` / `flac` / `mp3` / `opus` | Default **`wav`**. `aac` is not accepted |
| `sample_rate` | int > 0 | Resample output; omitted = model native rate |
| `speed` | 0.25-4.0 | Speech rate, default 1.0 |
| `stream`, `stream_format` | bool, `sse` / `audio` | `stream=true` alone → OpenAI `speech.audio.*` SSE events; add `stream_format="audio"` for raw bytes. HTTP streaming needs `response_format` `pcm` or `wav` |
| `task_type` | `CustomVoice` / `VoiceDesign` / `Base` | Qwen3-TTS mode |
| `language` | string | e.g. `English`, `Chinese`, `Auto` |
| `ref_audio`, `ref_text` | URL / base64 / file URI, string | Voice cloning (`Base`) |
| `speaker_embedding`, `x_vector_only_mode` | float list, bool | Precomputed embedding (1024-dim for 0.6B, 2048-dim for 1.7B); excludes `ref_audio` |
| `ref_audio_2`, `ambient_sound`, `duration_seconds` | | MOSS-TTSD second speaker / MOSS-SoundEffect |
| `max_new_tokens`, `seed` | int | Generation cap, determinism |
| `initial_codec_chunk_frames`, `non_streaming_mode` | int, bool | First-chunk size override; Qwen3-TTS prompt-construction mode (not HTTP streaming) |
| `word_timestamps` | bool | Per-word timings in the `X-Word-Timestamps` header (non-streaming) |
| `extra_params` | dict | Passed to the model's `extra_args` |

No `temperature` / `top_p` / `top_k` / `codec_*` fields exist; pydantic drops unknown keys silently, so sending them changes nothing. Output sample rate per model: Qwen3-TTS produces 24 kHz audio; tokenizer frame rate is 12 Hz or 25 Hz (set via model name, not param).

`/v1/audio/speech/batch` takes `{"items": [...]}` with the same per-item fields (request-level values are defaults) and returns `{"results": [{"index", "status", "audio_data"}], "succeeded", "failed"}`.

## `/v1/audio/voices`

**GET** → `{"voices": [str], "uploaded_voices": [{"name", "consent", "created_at", "file_size", "mime_type", "embedding_source", "embedding_dim", "ref_text"?, "speaker_description"?}]}`

**POST** (multipart): upload a custom voice. Required: `name`, `consent` (a consent-recording ID), and exactly one of `audio_sample` (file, 10 MB cap) or `speaker_embedding` (JSON float list). Optional: `ref_text` (enables higher-quality ICL cloning), `speaker_description`. Both or neither of `audio_sample`/`speaker_embedding` → 400.

```bash
curl http://localhost:8091/v1/audio/voices \
  -F "name=my_voice" \
  -F "consent=rec-0001" \
  -F "ref_text=hello this is my voice sample" \
  -F "audio_sample=@voice.wav"
```

Uploaded voices are process-local: with `--api-server-count` > 1 the upload returns **409**.

## `/v1/audio/speech/stream` (WebSocket)

Not OpenAI-compatible. Client sends text messages incrementally; server splits at sentence boundaries and returns per-sentence audio chunks. Implementation: `vllm_omni/entrypoints/openai/serving_speech_stream.py`.

## `/v1/videos` (async) vs `/v1/videos/sync`

**Use async** (`POST /v1/videos`) for anything likely > 1 min. Async jobs live in process-local state: every `/v1/videos` job route returns **409** with `--api-server-count` > 1 — run one API worker, or use `/v1/videos/sync`. Sync waits `VIDEO_SYNC_TIMEOUT_S` — 600 s default, `VLLM_OMNI_VIDEO_SYNC_TIMEOUT` overrides it (v0.24.0+) — and returns 504 past that.

### Async (recommended)

```bash
# Kick off job:
curl -X POST http://localhost:8091/v1/videos \
  -F "model=Wan-AI/Wan2.2-T2V-A14B-Diffusers" \
  -F "prompt=a cat chasing a laser pointer" \
  -F "num_frames=81" -F "fps=16" -F "width=832" -F "height=480" \
  -F "guidance_scale=5.0" -F "num_inference_steps=30"
# → {"id": "video_abc123", "object": "video", "status": "queued", "progress": 0, ...}

# Poll until status is "completed" or "failed" (states: queued | in_progress | completed | failed):
curl http://localhost:8091/v1/videos/video_abc123

# Fetch when done:
curl http://localhost:8091/v1/videos/video_abc123/content --output out.mp4
```

### Sync (benchmarking only)

Same form data but `/v1/videos/sync` — returns raw `video/mp4` with metadata headers:

| Header | Meaning |
|---|---|
| `X-Request-Id` | Request ID |
| `X-Model` | Model served |
| `X-Inference-Time-S` | Total seconds |
| `X-Stage-Durations` | Per-stage JSON |
| `X-Peak-Memory-MB` | Peak VRAM |

Video request fields beyond OpenAI's `prompt` / `seconds` / `size` (`VideoGenerationRequest`, `protocol/videos.py`):

| Field | Purpose |
|---|---|
| `num_frames`, `fps`, `width`, `height` | Output length/rate/resolution (also accepted nested under `video_params`) |
| `image_reference`, `video_reference`, `audio_reference` | `{file_id}` or `{image_url|video_url|audio_url}`, single or list (I2V, V2V, S2V) |
| `negative_prompt`, `num_inference_steps`, `seed` | As for images |
| `guidance_scale`, `guidance_scale_2` | Dual CFG (Wan2.2: `guidance_scale_2` for high-noise branch) |
| `true_cfg_scale`, `boundary_ratio`, `flow_shift` | Qwen-style CFG, Wan2.2 boundary timing, scheduler shift |
| `quality` | `lossless` or `high`; anything else → 422 |
| `generate_sound`, `sound_duration` | Model-generated audio track (sound-capable models) |
| `aspect_ratio`, `short_edge`, `num_outputs_per_prompt` (1-10), `start_time_seconds` | MiniMax H3 |
| `enable_frame_interpolation` | RIFE post-processing |
| `frame_interpolation_exp` | `1` / `2` / `3` → 2× / 4× / 8× temporal |
| `frame_interpolation_scale`, `frame_interpolation_model_path` | RIFE config |
| `lora`, `extra_params`, `return_stage_metrics` | As for images |

A `model` that differs from the served model returns **400 "Model mismatch"** on video requests too (#2805).

## `/v1/realtime` (WebSocket, Qwen3-Omni)

Full recipe in `references/realtime-tts.md`. On v0.22.0+ the default `qwen3_omni_moe.yaml` (`async_chunk: true`) serves realtime; only v0.20.x and older reject realtime under `async_chunk`. Since v0.30.0 audio arrives as `response.output_audio.delta` (formerly `response.audio.delta`).

## `/v1/chat/completions` with diffusion via `extra_body`

```python
# Python SDK:
resp = client.chat.completions.create(
    model="Qwen/Qwen-Image",
    messages=[{"role": "user", "content": "draw a cat"}],
    extra_body={
        "modalities": ["text", "image"],
        "guidance_scale": 4.0,
        "num_inference_steps": 30,
    },
)
```

A `WARNING: fields were present in the request but ignored` log line is **harmless and expected** — the SDK's OpenAI schema doesn't know about these fields.

Qwen3-Omni output modality control: `"modalities": ["text"]` / `["audio"]` / `["text","audio"]`.
