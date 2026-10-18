# Qwen3-Omni realtime + Qwen3-TTS serving

Load when serving Qwen3-Omni with `/v1/realtime`, serving Qwen3-TTS via `/v1/audio/speech`, or debugging audio output. Source: `vllm_omni/entrypoints/openai/realtime_connection.py`, `examples/online_serving/qwen3_omni/README.md`, `vllm_omni/entrypoints/openai/serving_speech.py`.

## Qwen3-Omni realtime (`/v1/realtime`)

### Hard constraints

1. **`async_chunk` is allowed on v0.22.0+.** The default `qwen3_omni_moe.yaml` ships `async_chunk: true` and serves `/v1/realtime`; PR #3614 removed the handshake rejection. Only on v0.20.x and older does realtime need a stage config with `async_chunk` off (the server then answers `"unsupported"` at handshake).

2. **Input audio format: PCM16 mono @ 16 kHz**. Anything else (stereo, 8 kHz, 24-bit, WAV-with-header) → garbage or silence. The reference client rejects other rates (`openai_realtime_client.py:60` at v0.30.0).

3. **Output audio rate: 24 kHz** PCM. Concatenate `response.output_audio.delta` events and write a 24 kHz WAV (honour `sample_rate_hz` if an event carries it). Before v0.30.0 the event was `response.audio.delta`.

4. **Turn vs duplex.** Plain `/v1/realtime` on `qwen3_omni_moe.yaml` is turn mode. `?duplex=1` needs a duplex deployment (`qwen3_omni_duplex.yaml`, `session_mode: duplex`); against a turn deployment it returns `unsupported` and closes with 1008.

### Serve command

```bash
# Default deploy YAML: stage 0 on cuda:0, stages 1+2 share cuda:1.
# Do not pass global --gpu-memory-utilization / --tensor-parallel-size —
# they apply to every stage; use --stage-overrides per stage instead.
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni --port 8091
```

Published production numbers (v0.16 release): TTFP reduced 90%, RTF 0.22-0.45 on H100 TP2.

### Protocol — OpenAI realtime shape

Client sends (v0.30.0 reference client):
1. `session.update` — `{"model": "Qwen/Qwen3-Omni-30B-A3B-Instruct"}` (with `--server-vad`: a `session` object carrying `audio.input.format` `{"type":"audio/pcm","rate":16000}` and `turn_detection: server_vad`)
2. `input_audio_buffer.append` — base64-encoded PCM chunk (default 200 ms chunks)
3. `input_audio_buffer.commit` — `"final": true` on the last one; omitted with server VAD
4. `session.close`

Server sends:
- `response.output_audio.delta` — PCM audio chunks at 24 kHz (was `response.audio.delta` before v0.30.0)
- `transcription.delta` — streaming transcript text
- `transcription.done` — final transcript + usage
- `response.output_audio.done` — end of audio (`has_audio` flag)

### Client template (from `examples/online_serving/qwen3_omni/openai_realtime_client.py`)

```bash
python examples/online_serving/qwen3_omni/openai_realtime_client.py \
  --url ws://localhost:8091/v1/realtime \
  --input-wav sample_16k_mono.wav \
  --output-wav output_24k.wav \
  --chunk-ms 200 \
  --send-delay-ms 200
```

CLI args:

| Flag | Purpose |
|---|---|
| `--url` | Full WebSocket URL (include `/v1/realtime`) |
| `--input-wav` | 16-bit PCM mono @ 16 kHz WAV file (required) |
| `--output-wav` | Output WAV path (default `realtime_output.wav`) |
| `--chunk-ms` | Input chunk size ms (default 200) |
| `--send-delay-ms` | Simulated realtime send delay (default 0) |
| `--server-vad` | Let the server detect speech end and commit the turn |
| `--model`, `--output-text` | Model name for `session.update`; transcript output path |
| `--delta-dump-dir` | Save per-delta WAV for debugging |
| `--num-requests`, `--concurrency` | Sequential or parallel sessions |

### Common realtime gotchas

- **Over-generation on incomplete input**: if Thinker runs before input audio is fully committed, it may ramble past the intended end. Cap `max_tokens` in session defaults or server config.
- **Audio gaps (#2562)**: Sporadic silence gaps during streaming. Known issue, tracked; no clean workaround as of v0.18.
- **ASR-only flow**: For `transcription.*` events without TTS output, set `"modalities": ["text"]` in session.update. Saves decoder work.
- **Voice prompt**: to instruct the Talker to use a specific voice, include it in the user text prompt: "Reply with Ethan's voice: ..." — there's no separate session voice field.

## Qwen3-TTS via `/v1/audio/speech`

### Hard constraints

1. **`--trust-remote-code`** required — custom model code lives in the HF repo.
2. **`--task-type`** must match the checkpoint variant: `CustomVoice`, `VoiceDesign`, or `Base`.
3. **`--enforce-eager`** was mandatory on v0.18 (issue #2866: code2wav crashed with CUDA graphs enabled). **#2866 is CLOSED (2026-04-29)** and v0.20.0 adds TTS CUDA-graph capture + shared memory pools (release notes cite #2690/#2758/#2803) — drop `--enforce-eager` on v0.20.0+ to regain throughput.
4. **v0.30.0 default CUDA profile runs experimental Model Runner V2** with event-driven orchestration (#7930, #7088). On a regression, set `model_runner: v1` in the deploy YAML (or `VLLM_OMNI_EVENT_DRIVEN_ORCH` to change orchestration); non-CUDA platforms already use V1.

### Three task types

| Task | HF ID pattern | Behavior |
|---|---|---|
| `CustomVoice` | `Qwen/Qwen3-TTS-*-CustomVoice` | Fixed set of preset voices (`vivian`, `ryan`, `aiden`, ...) |
| `VoiceDesign` | `Qwen/Qwen3-TTS-*-VoiceDesign` | Instruction-guided voice via the request `instructions` field |
| `Base` | `Qwen/Qwen3-TTS-*-Base` | Voice cloning from `ref_audio` sample |

### Serve commands per task type

On v0.18 add `--enforce-eager` to each command (issue #2866); on v0.20.0+ it is no longer required (TTS CUDA-graph capture, release notes #2690/#2758/#2803).

```bash
# CustomVoice (preset voices):
vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --omni \
  --trust-remote-code --task-type CustomVoice \
  --port 8091

# VoiceDesign (instruction-guided):
vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign --omni \
  --trust-remote-code --task-type VoiceDesign \
  --port 8091

# Base (voice cloning):
vllm serve Qwen/Qwen3-TTS-12Hz-0.6B-Base --omni \
  --trust-remote-code --task-type Base \
  --port 8091
```

### Tokenizer frame rates

- 12 Hz (shipped by default): lower bitrate, sufficient for most speech
- 25 Hz (also supported): higher fidelity, roughly 2× decode time

Set via model name (`12Hz` vs `25Hz` in repo name), not a flag.

### Request shapes

```bash
# Basic TTS (CustomVoice)
curl http://localhost:8091/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "input": "Hello from vllm-omni.",
    "voice": "vivian",
    "response_format": "wav",
    "speed": 1.0
  }' --output hello.wav

# Voice cloning (Base)
curl http://localhost:8091/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "input": "This should sound like the reference.",
    "voice": "my_uploaded_voice"
  }' --output clone.wav
```

### Uploading custom voice samples (Base mode)

```bash
curl http://localhost:8091/v1/audio/voices \
  -F "name=jane_narrator" \
  -F "consent=rec-jane-0001" \
  -F "ref_text=Hello, my name is Jane, and this is a voice sample." \
  -F "speaker_description=warm mid-range female voice, narrating" \
  -F "audio_sample=@jane_voice_30s.wav"
```

Required: `name`, `consent` (consent-recording ID), and exactly one of `audio_sample` (≤10 MB) or `speaker_embedding` (JSON float list, 1024-dim for 0.6B, 2048-dim for 1.7B). `ref_text` and `speaker_description` are optional; `ref_text` enables the higher-quality ICL clone. From audio, the embedding is extracted on first use (Base models only). Uploads are process-local — re-upload after every restart, and expect 409 with `--api-server-count` > 1. Metadata comes back in `GET /v1/audio/voices`.

### Streaming TTS

```python
# Python client, PCM streaming:
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8091/v1", api_key="dummy")

with client.audio.speech.with_streaming_response.create(
    model="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    input="Long piece of text...",
    voice="vivian",
    response_format="pcm",
    extra_body={"stream": True, "stream_format": "audio"},  # raw bytes; stream alone = SSE events
) as response:
    with open("out.pcm", "wb") as f:
        for chunk in response.iter_bytes():
            f.write(chunk)
```

v0.16 (#1438) made streaming first-class for Qwen3-TTS. Chunk cadence is per-sentence boundary for `/v1/audio/speech/stream` WebSocket, or per-codec-frame for `stream: true` + `stream_format: "audio"` + `response_format` `pcm`/`wav` on `/v1/audio/speech` (`stream: true` alone sends OpenAI `speech.audio.*` SSE events).

### Batch TTS

`POST /v1/audio/speech/batch` with `BatchSpeechRequest` (array of per-item requests). Returns `{"results": [{"success": bool, "audio_data": base64, "error": str}]}`.

Useful for large synthesis runs that don't require interactive streaming.

## MiMo-Audio — related but different

`XiaomiMiMo/MiMo-Audio-7B-Instruct` ships at RTF ~0.2 (11× baseline per v0.16). It's a general audio generation model — not purely TTS. Served via `/v1/audio/speech` but supports arbitrary-audio prompts.

Known issue: `online_serving mimo_audio` has a bug (#2683). Verify with a simple prompt before trusting batch output.

## Voxtral TTS

`mistralai/Voxtral-4B-TTS-2603` is Mistral's TTS entry. v0.18 addition. Active forum thread: [discuss.vllm.ai/t/2549](https://discuss.vllm.ai/t/issues-with-voxtral-models-and-omni/2549). Validate against the intended workload before committing — deployment maturity is still early.

## Stable-Audio-Open (music / SFX)

`stabilityai/stable-audio-open-1.0` generates music / SFX (not speech). Different endpoint behavior — it produces longer-form audio via diffusion, not AR-codec TTS. Check `docs/serving/` for the exact request shape; the `/v1/audio/speech` TTS shape doesn't carry some of its params (genre, BPM, duration).
