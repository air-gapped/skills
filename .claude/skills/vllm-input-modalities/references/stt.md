# Speech-to-text (ASR) — operator reference

Load when the question is about serving Whisper / Voxtral / Qwen3-ASR /
Kimi-Audio, the `/v1/audio/transcriptions` / `/v1/audio/translations`
endpoints, audio chunking, or STT-specific quantisation.

## 1. The mental model

STT runs on the **generate runner**, not pooling. Any model implementing
the `SupportsTranscription` interface gets the two audio endpoints for free;
the model class is otherwise a standard encoder-decoder.

```
--runner generate            # implicit default — don't set it
```

No `--runner transcription` flag. The dispatch is by model type, not flag.

## 2. Endpoints

| Route | Spec | Request body |
|---|---|---|
| `/v1/audio/transcriptions` | OpenAI-compatible | `multipart/form-data` with `file`, `model`, optional `language`, `prompt`, `response_format`, `temperature` |
| `/v1/audio/translations` | OpenAI-compatible (translate to English) | same |

Code:
- `vllm/entrypoints/openai/speech_to_text/api_router.py:52-100`
- `vllm/entrypoints/openai/speech_to_text/serving.py:33-120`
- `vllm/entrypoints/openai/speech_to_text/speech_to_text.py:83` — base

Task types (from `vllm/tasks.py:5-6`):
`GenerationTask = Literal["generate", "transcription", "realtime"]`.

## 3. Supported models

| Family | Model | Class | Notes |
|---|---|---|---|
| Whisper | `openai/whisper-large-v3` | `WhisperForConditionalGeneration` | 1.6 GB checkpoint, but wants ≥32 GB HBM for comfortable batch |
| Whisper | `openai/whisper-large-v3-turbo` | same | ~8× faster decoder than v3; quality near-equal |
| Whisper (RedHatAI) | `whisper-large-v3-turbo-FP8-dynamic` | same | fits 24 GB; validated |
| Whisper (RedHatAI) | `whisper-large-v3-turbo-quantized.w8a8` | same | smaller again |
| Whisper (RedHatAI) | `whisper-large-v3-turbo-quantized.w4a16` | same | smallest, some quality drop |
| Whisper-causal | (internal variant) | `WhisperCausal*` | for causal decoders on Whisper features |
| Voxtral | `mistralai/Voxtral-Mini-3B-2507` | `VoxtralForConditionalGeneration` | Mistral's speech model; Small variant also exists |
| Qwen2-Audio | `Qwen/Qwen2-Audio-*` | `Qwen2AudioForConditionalGeneration` | also does audio understanding |
| Qwen3-Omni | `Qwen/Qwen3-Omni-MoE-Thinker-*` | `Qwen3OmniMoeThinkerForConditionalGeneration` | unified audio+vision |
| Qwen3-ASR | `qwen3_asr_realtime`, `qwen3_asr_forced_aligner` | dedicated ASR variants |
| Ultravox | `fixie-ai/ultravox-v0_*` | `UltravoxModel` | LLaMA 3 + Whisper encoder |
| Kimi-Audio | `moonshotai/Kimi-Audio-7B-Instruct` | `KimiAudioWhisperEncoder` | long-form audio understanding |
| FunASR | `funasr/*` | family | Chinese-first ASR |
| FireRedASR2 | `FireRedASR2-*` | family | Chinese-first ASR, v2 |
| MiniCPM-O | `openbmb/MiniCPM-o-2_6` | `MiniCPMWhisperEncoder` | on-device scale |
| Cohere ASR | `cohere/*` | `CohereASRForCausalLM` | newer addition |
| Gemma 3n | `Gemma3nForConditionalGeneration` | family | multimodal, audio optional |

Model files live under `vllm/model_executor/models/` — grep for
`*audio*.py`, `whisper*.py`, `voxtral*.py`, `ultravox.py`, `funasr*.py`.

## 4. Canonical serve commands

```bash
# Whisper large-v3-turbo (base)
vllm serve openai/whisper-large-v3-turbo

# Red Hat validated quant (fits on 24 GB comfortably, production-tested)
vllm serve RedHatAI/whisper-large-v3-turbo-FP8-dynamic

# Voxtral Mini
vllm serve mistralai/Voxtral-Mini-3B-2507

# Ultravox
vllm serve fixie-ai/ultravox-v0_5-llama-3_1-8b

# Kimi-Audio
vllm serve moonshotai/Kimi-Audio-7B-Instruct --trust-remote-code
```

## 5. Client patterns

```bash
# curl — multipart/form-data is mandatory
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F "file=@meeting.wav" \
  -F "model=openai/whisper-large-v3-turbo" \
  -F "language=en" \
  -F "response_format=json" \
  -F "temperature=0"

# translation (target language = English regardless of source)
curl -X POST http://localhost:8000/v1/audio/translations \
  -F "file=@japanese_audio.mp3" \
  -F "model=openai/whisper-large-v3-turbo"
```

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")

with open("meeting.wav", "rb") as f:
    r = client.audio.transcriptions.create(
        model="openai/whisper-large-v3-turbo",
        file=f,
        language="en",
        temperature=0,
    )
print(r.text)
```

## 6. Audio format handling

Server-side:

1. **Decoding** — librosa-based. WAV / FLAC / MP3 work out of the box.
   MP4 / M4A / WebM decoding support landed in v0.18.
2. **Resampling** — automatic to `SpeechToTextConfig.sample_rate` per model
   (Whisper = 16 kHz, Voxtral = 16 kHz, etc.).
3. **Chunking** — for audio longer than `max_audio_clip_s` (usually 30 s),
   vLLM splits with energy-aware detection at
   `min_energy_split_window_size`. Set `min_energy_split_window_size=None`
   if the model handles its own chunking.

Recent fix: **#39116 (2025-12)** fixed a spacing bug between chunks in
multi-chunk transcription. Pin to v0.18+ for long-form audio.

## 7. Beam search + streaming

- **Beam-search transcription** (offline + online) shipped in v0.18.
  Improves WER on noisy audio at latency cost. Enable via the standard
  `SamplingParams(best_of=..., use_beam_search=True)` plumbing — STT inherits
  it from the generate path.
- **Streaming transcriptions** — long-awaited; check release notes per
  version for streaming support maturity. As of early 2026, offline is
  rock-solid, streaming is still evolving.

## 8. Production path — Red Hat AI Inference Server (RHAIIS)

Red Hat's blog series is the closest thing to a canonical production
deployment guide for vLLM STT. Key artefacts:

- Container: `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.0.0` — hardened
  vLLM distribution.
- Pre-validated quants under `RedHatAI/` namespace on HF.
- Performance target: Whisper-large-v3-turbo-FP8-dynamic delivers real-time
  factor ≫1 on a single L40S.

Source URL: <https://developers.redhat.com/articles/2026/03/06/private-transcription-whisper-red-hat-ai>

## 9. Known sharp edges

1. **Whisper OOM on 24 GB GPU** (issue #15216). The checkpoint is 1.6 GB
   but encoder KV + graph state push total VRAM past 24 GB at even modest
   batch. Fix: use a RedHatAI quant, reduce `--gpu-memory-utilization`, or
   move to a ≥32 GB GPU.
2. **"model doesn't support audio"** — the model file is missing the
   `SupportsTranscription` interface. Check the model's class in
   `vllm/model_executor/models/`; not every "audio" model exposes the STT
   endpoints (some are audio-understanding chat only — use `/v1/chat/completions`).
3. **Non-16 kHz audio** — vLLM resamples, but very low sample rates
   (≤8 kHz phone audio) degrade Whisper quality. Consider a phone-tuned
   model (FunASR has variants) or upsample + de-noise client-side first.
4. **Language hint wrong** — `language="zh"` on an English audio tanks WER.
   Leave blank to let Whisper auto-detect on the first chunk, then pin for
   the rest of the file if using long-form.
5. **`/v1/audio/speech` (TTS)** — **not** currently supported. That's a
   request-output shape nobody in vLLM serves; use a dedicated TTS engine.

## 10. Metrics

STT shares the generate-runner Prometheus metrics:
- `vllm:request_latency_seconds` (request duration)
- `vllm:num_preemptions_total`
- `vllm:generation_tokens_total`
- `vllm:prompt_tokens_total`

Audio-specific metrics (seconds of audio processed, real-time factor) are
not currently surfaced as counters in vLLM itself. For production, wrap
the request client with your own timing instrumentation.

## 11. Source anchors

- `vllm/entrypoints/openai/speech_to_text/api_router.py:52-100` — routes
- `vllm/entrypoints/openai/speech_to_text/serving.py:33-120` — dispatch
- `vllm/entrypoints/openai/speech_to_text/speech_to_text.py:83+` — base
- `vllm/config/speech_to_text.py` — `SpeechToTextConfig` (sample rate,
  chunking params)
- `vllm/tasks.py:5-6` — `GenerationTask`
- `docs/contributing/model/transcription.md` — interface spec for
  `SupportsTranscription`
- Red Hat STT blog: <https://developers.redhat.com/articles/2025/06/10/speech-text-whisper-and-red-hat-ai-inference-server>
