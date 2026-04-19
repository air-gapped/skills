# vllm-omni endpoint catalog

Load when operator asks about a specific API endpoint's shape, streaming, auth, or payload fields. Source: `vllm_omni/entrypoints/openai/api_server.py`, `vllm_omni/entrypoints/openai/protocol/*.py`, `docs/serving/*.md`, and the reference clients in `examples/online_serving/`.

## Endpoint map (v0.18.0)

| Path | Method | Purpose |
|---|---|---|
| `/v1/chat/completions` | POST | Multimodal chat + omni; diffusion via `extra_body` |
| `/v1/images/generations` | POST | DALL·E-shape text-to-image |
| `/v1/images/edits` | POST | DALL·E-shape image edit (multipart) |
| `/v1/audio/speech` | POST | OpenAI-shape TTS (WAV/MP3/PCM/FLAC/AAC/OPUS) |
| `/v1/audio/speech/batch` | POST | Batched TTS |
| `/v1/audio/speech/stream` | WebSocket | Streaming TTS (text in → audio-per-sentence out) |
| `/v1/audio/voices` | GET | List speakers (built-in + uploaded) |
| `/v1/audio/voices` | POST | Upload custom voice (multipart, 10 MB cap) |
| `/v1/videos` | POST | **Async** video job (returns job metadata) |
| `/v1/videos/sync` | POST | **Sync** video (raw MP4 bytes; ~1200s timeout) |
| `/v1/videos` | GET | List video jobs (query: `after`, `limit`, `order`) |
| `/v1/videos/{id}` | GET | Job metadata |
| `/v1/videos/{id}/content` | GET | Raw MP4 bytes |
| `/v1/videos/{id}` | DELETE | Delete job + artifacts |
| `/v1/realtime` | WebSocket | PCM16 realtime (Qwen3-Omni only) |
| `/health` | GET | `{"status":"ok"}` |
| `/v1/models` | GET | List loaded models (diffusion too, since v0.14 #454) |

## `/v1/images/generations`

DALL·E-compatible. **`response_format` is always `b64_json`** (no URL hosting). `size` is `"WIDTHxHEIGHT"` — Qwen-Image respects bucket sizes (640/1024/1536).

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
| `num_inference_steps` | int 1-200 | Diffusion steps |
| `guidance_scale` | float 0-20 | CFG scale (>1.0 to enable; **0.0 is sentinel "not provided"**) |
| `true_cfg_scale` | float | Qwen-Image variant |
| `seed` | int | Reproducibility |
| `generator_device` | `"cpu"\|"cuda"` | Seeded generator device |
| `system_prompt`, `use_system_prompt` | str, bool | Qwen-Image system prompting |
| `lora` | dict | Per-request LoRA adapter spec |
| `vae_use_slicing`, `vae_use_tiling` | bool | VAE memory optimizations |
| `layers` | int 3-10 | Layered image models |

Response: `{"created": <ts>, "data": [{"b64_json": "...", "revised_prompt": null}]}`.

**Gotcha**: Python OpenAI SDK doesn't have fields for the non-OpenAI extras. Use curl, or pass them through the SDK's `extra_body` (if translating to `/v1/chat/completions` with diffusion).

## `/v1/images/edits`

Multipart/form-data. Extensions: `url`, `reference_image`, `mask_image` fields.

## `/v1/audio/speech`

OpenAI TTS shape + Qwen3-TTS extensions.

```bash
curl http://localhost:8091/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "input": "Hello from vllm-omni.",
    "voice": "ethan",
    "response_format": "wav",
    "speed": 1.0
  }' --output out.wav
```

Fields:

| Field | Type | Purpose |
|---|---|---|
| `model` | string | TTS model name |
| `input` | string | Text to synthesize |
| `voice` / `speaker` | string | Speaker/voice name (e.g. `ethan`, `chelsie`, `aiden`) |
| `response_format` | `wav`/`mp3`/`flac`/`pcm`/`aac`/`opus` | Output format (default mp3) |
| `speed` | 0.25-4.0 | Speech rate |
| `temperature` | 0-2 | Omni-specific sampling |
| `top_p`, `top_k` | | Omni-specific |
| `codec_bitrate`, `codec_sample_rate` | | Audio quality |
| `stream` | bool | Server-sent streaming (when `response_format=pcm`) |

Output sample rate per model: Qwen3-TTS produces 24 kHz audio; tokenizer frame rate is 12 Hz or 25 Hz (set via model name, not param).

## `/v1/audio/voices`

**GET** → `{"voices": [str], "uploaded_voices": [{"name", "consent", "ref_text", "speaker_description", "embedding_source", "embedding_dim", "created_at", "file_size", "mime_type"}]}`

**POST** (multipart): upload custom voice sample.

```bash
curl http://localhost:8091/v1/audio/voices \
  -F "name=my_voice" \
  -F "consent=true" \
  -F "ref_text=hello this is my voice sample" \
  -F "speaker_description=warm female narrator" \
  -F "audio_sample=@voice.wav"
```

Constraints: 10 MB cap on audio_sample. Missing `name`/`consent`/`ref_text`/`speaker_description` → 400.

## `/v1/audio/speech/stream` (WebSocket)

Not OpenAI-compatible. Client sends text messages incrementally; server splits at sentence boundaries and returns per-sentence audio chunks. Implementation: `vllm_omni/entrypoints/openai/serving_speech_stream.py`.

## `/v1/videos` (async) vs `/v1/videos/sync`

**Use async** (`POST /v1/videos`) for anything likely > 1 min. Sync has `VIDEO_SYNC_TIMEOUT_S` (~1200s hardcoded) and returns 504 past that.

### Async (recommended)

```bash
# Kick off job:
curl -X POST http://localhost:8091/v1/videos \
  -F "model=Wan-AI/Wan2.2-T2V-A14B-Diffusers" \
  -F "prompt=a cat chasing a laser pointer" \
  -F "num_frames=81" -F "fps=16" -F "width=832" -F "height=480" \
  -F "guidance_scale=5.0" -F "num_inference_steps=30"
# → {"id": "video_abc123", "status": "queued", ...}

# Poll:
curl http://localhost:8091/v1/videos/video_abc123
# → {"status": "completed" | "running" | "failed", ...}

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

Non-OpenAI video extensions:

| Field | Purpose |
|---|---|
| `num_frames`, `fps` | Output length/rate |
| `width`, `height` | Resolution |
| `guidance_scale`, `guidance_scale_2` | Dual CFG (Wan2.2: `guidance_scale_2` for high-noise branch) |
| `boundary_ratio` | Wan2.2 boundary timing |
| `flow_shift` | Scheduler param |
| `enable_frame_interpolation` | RIFE post-processing |
| `frame_interpolation_exp` | `1` / `2` / `3` → 2× / 4× / 8× temporal |
| `frame_interpolation_scale`, `frame_interpolation_model_path` | RIFE config |

**Gotcha** (#2804): diffusion endpoints accept model mismatch silently — the URL's `model` field is pass-through without validation. Add a gateway check where validation matters.

## `/v1/realtime` (WebSocket, Qwen3-Omni)

Full recipe in `references/realtime-tts.md`. Key constraint: **server must be started with `async_chunk: false`** — the default `qwen3_omni_moe.yaml` stage config is correct; do not use `qwen3_omni_moe_async_chunk.yaml` for realtime.

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
