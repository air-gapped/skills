# Qwen3-Omni realtime + Qwen3-TTS serving

Load when serving Qwen3-Omni with `/v1/realtime`, serving Qwen3-TTS via `/v1/audio/speech`, or debugging audio output. Source: `vllm_omni/entrypoints/openai/realtime_connection.py`, `examples/online_serving/qwen3_omni/README.md`, `vllm_omni/entrypoints/openai/serving_speech.py`.

## Qwen3-Omni realtime (`/v1/realtime`)

### Hard constraints

1. **`async_chunk: false`** in the stage config. Default `qwen3_omni_moe.yaml` has this right; **never** pass `--stage-configs-path qwen3_omni_moe_async_chunk.yaml` for realtime. The server rejects at WebSocket handshake (api_server.py:1208) with `"unsupported"` code.

2. **Input audio format: PCM16 mono @ 16 kHz**. Anything else (stereo, 8 kHz, 24-bit, WAV-with-header) → garbage or silence. Hardcoded in `openai_realtime_client.py:43`.

3. **Output audio rate: 24 kHz** PCM. Concatenate `response.audio.delta` events and write a 24 kHz WAV.

### Serve command

```bash
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.9 \
  --trust-remote-code \
  --port 8091
```

Published production numbers (v0.16 release): TTFP reduced 90%, RTF 0.22-0.45 on H100 TP2.

### Protocol — OpenAI realtime shape

Client sends:
1. `session.update` — `{"model": "Qwen/Qwen3-Omni-30B-A3B-Instruct"}`
2. `input_audio_buffer.append` — base64-encoded PCM chunk (default 200 ms chunks)
3. `input_audio_buffer.commit` — signals input complete

Server sends:
- `response.audio.delta` — PCM audio chunks at 24 kHz
- `transcription.delta` — streaming ASR transcription text
- `transcription.final` — final transcription
- `response.audio.done` — end-of-utterance

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
| `--send-delay-ms` | Simulated realtime send delay |
| `--delta-dump-dir` | Save per-delta WAV for debugging |
| `--num-requests`, `--concurrency` | Sequential or parallel sessions |

### Common realtime gotchas

- **Over-generation on incomplete input**: if Thinker runs before input audio is fully committed, it may ramble past the intended end. Cap `max_tokens` in session defaults or server config.
- **Audio gaps (#2562)**: Sporadic silence gaps during streaming. Known issue, tracked; no clean workaround as of v0.18.
- **ASR-only flow**: For `transcription.*` events without TTS output, set `"modalities": ["text"]` in session.update. Saves decoder work.
- **Voice prompt**: to instruct the Talker to use a specific voice, include it in the user text prompt: "Reply with Ethan's voice: ..." — there's no separate session voice field.

## Qwen3-TTS via `/v1/audio/speech`

### Hard constraints

1. **`--enforce-eager`** is mandatory (issue #2866): code2wav stage crashes with CUDA graphs enabled.
2. **`--trust-remote-code`** required — custom model code lives in the HF repo.
3. **`--task-type`** must match the checkpoint variant: `CustomVoice`, `VoiceDesign`, or `Base`.

### Three task types

| Task | HF ID pattern | Behavior |
|---|---|---|
| `CustomVoice` | `Qwen/Qwen3-TTS-*-CustomVoice` | Fixed set of preset voices (ethan, chelsie, aiden, ...) |
| `VoiceDesign` | `Qwen/Qwen3-TTS-*-VoiceDesign` | Instruction-guided voice via `speaker_description` |
| `Base` | `Qwen/Qwen3-TTS-*-Base` | Voice cloning from `ref_audio` sample |

### Serve commands per task type

```bash
# CustomVoice (preset voices):
vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --omni \
  --enforce-eager --trust-remote-code --task-type CustomVoice \
  --port 8091

# VoiceDesign (instruction-guided):
vllm serve Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign --omni \
  --enforce-eager --trust-remote-code --task-type VoiceDesign \
  --port 8091

# Base (voice cloning):
vllm serve Qwen/Qwen3-TTS-12Hz-0.6B-Base --omni \
  --enforce-eager --trust-remote-code --task-type Base \
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
    "voice": "ethan",
    "response_format": "wav",
    "speed": 1.0,
    "temperature": 0.7
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
  -F "consent=true" \
  -F "ref_text=Hello, my name is Jane, and this is a voice sample." \
  -F "speaker_description=warm mid-range female voice, narrating" \
  -F "audio_sample=@jane_voice_30s.wav"
```

10 MB cap on `audio_sample`. Server computes a speaker embedding on upload — persist this across re-deploys. Metadata (consent, ref_text, speaker_description, embedding_dim, created_at, file_size, mime_type) is returned in `/v1/audio/voices` GET.

### Streaming TTS

```python
# Python client, PCM streaming:
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8091/v1", api_key="dummy")

with client.audio.speech.with_streaming_response.create(
    model="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    input="Long piece of text...",
    voice="ethan",
    response_format="pcm",
) as response:
    with open("out.pcm", "wb") as f:
        for chunk in response.iter_bytes():
            f.write(chunk)
```

v0.16 (#1438) made streaming first-class for Qwen3-TTS. Chunk cadence is per-sentence boundary for `/v1/audio/speech/stream` WebSocket, or per-codec-frame for `stream: true` + `response_format: pcm` on `/v1/audio/speech`.

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
