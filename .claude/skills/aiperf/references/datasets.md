# Datasets — Synthetic, Public, Custom JSONL, Trace

Three input modes: synthetic generation (default), `--public-dataset <name>`, or `--custom-dataset-type <type> --input-file <path>`. Public and custom are mutually exclusive.

## Synthetic (default)

When neither `--public-dataset` nor `--custom-dataset-type` is set, AIPerf generates synthetic prompts from a Shakespeare corpus, sampled to match `--isl-mean ± --isl-stddev`. Output length is requested via `--osl-mean ± --osl-stddev`.

Multimodal:

- Audio: random noise (WAV/MP3) at `--audio-format`, `--audio-sample-rates`, `--audio-depths`, `--audio-num-channels`. Duration ~ N(`--audio-length-mean`, `--audio-length-stddev`).
- Image: randomly resized PNG/JPEG (or `random`). Dimensions ~ N(`--image-{width,height}-{mean,stddev}`).
- Video: procedural (moving shapes / grid clock / noise). `--video-format`, `--video-codec`, `--video-fps`, `--video-{width,height}`, `--video-duration`.

## Public datasets

`--public-dataset <name>` downloads from HuggingFace (or built-in registry) and parses automatically. `--hf-subset` overrides the HF subset for HF-backed loaders.

| Group | Names |
|---|---|
| Conversational | `sharegpt` |
| Math | `aimo`, `aimo_aime`, `aimo_numina_cot`, `aimo_numina_1_5` |
| Vision | `mmstar`, `mmvu`, `vision_arena`, `llava_onevision` |
| Coding | `instruct_coder`, `spec_bench`, `blazedit_5k`, `blazedit_10k` |
| SPEED-Bench by category | `speed_bench_qualitative`, `…_coding`, `…_humanities`, `…_math`, `…_multilingual`, `…_qa`, `…_rag`, `…_reasoning`, `…_roleplay`, `…_stem`, `…_summarization`, `…_writing` |
| SPEED-Bench by length | `speed_bench_throughput_{1k,2k,8k,16k,32k}[_low_entropy\|_mixed\|_high_entropy]` |

`aiperf plugins public_dataset_loader` lists what's installed (the registry is plugin-driven since v0.7.0 — see `plugins.md`).

## Custom JSONL formats

Pass `--custom-dataset-type <type> --input-file <file-or-dir>`. AIPerf reads each line and translates to the wire format for the configured `--endpoint-type`.

### `single_turn`

One exchange per line. Format change vs genai-perf: `payload` (singular) → `payloads` (array).

```jsonl
{"session_id": "1", "payloads": [{"text": "What is the capital of France?"}]}
{"session_id": "2", "payloads": [{"text": "Explain mitosis briefly."}]}
```

Per-request `output_length` override (added in PR #830, v0.7.0+ / v0.8.0):

```jsonl
{"session_id": "1", "payloads": [{"text": "...", "output_length": 256}]}
```

### `multi_turn`

Each `payloads` entry is one turn. AIPerf preserves order within a session; turn N+1 is sent only after turn N completes. Combine with `--shared-system-prompt-length` and `--user-context-prompt-length` for KV-cache benchmarking.

```jsonl
{"session_id": "abc", "payloads": [
  {"text": "Hi, I have a question about my account."},
  {"text": "What's my balance?"},
  {"text": "Transfer $100 to savings."}
]}
```

### `mooncake_trace`

Privacy-preserving production trace from [kvcache-ai/Mooncake](https://github.com/kvcache-ai/Mooncake). Each line is a timestamped request with hashed input blocks for cache-reuse analysis without leaking content.

```jsonl
{"timestamp": 0, "input_length": 8000, "output_length": 200, "hash_ids": [46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61]}
{"timestamp": 1500, "input_length": 8500, "output_length": 180, "hash_ids": [46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62]}
```

`hash_ids` are 512-token blocks by default — pass `--isl-block-size <N>` to match the server's KV-cache block size. v0.7.0 added a `messages` variant for explicit conversation context. Trigger with `--fixed-schedule` to replay at original timestamps; omit for as-fast-as-possible capacity testing. Pre-flight: `aiperf analyze-trace --input-file mooncake_trace.jsonl`.

Demo trace:

```bash
curl -O https://raw.githubusercontent.com/kvcache-ai/Mooncake/refs/heads/main/FAST25-release/arxiv-trace/mooncake_trace.jsonl
```

### `bailian_trace`

Alibaba Bailian production trace. v0.7.0 added support (PR #723). Same family as Mooncake but the Bailian-side schema; use the dedicated loader because field names and timestamp resolution differ.

### `burst_gpt_trace`

[BurstGPT](https://arxiv.org/abs/2401.17286) production trace. Captures bursty, real conversational LLM service traffic. Added v0.7.0 (PR #786).

### `random_pool`

Directory of plain text files. AIPerf samples randomly per batch. v0.7.0 added per-batch-size support and single-line JSONL (PR #745). When `--prompt-batch-size > 1`, each modality is sampled independently from a flat pool — paired modalities are not preserved. Use `single_turn` if pairing matters.

```
prompts/
├── prompt-001.txt
├── prompt-002.txt
├── ...
```

When using `random_pool`, `--conversation-num` defaults to 100 if not specified.

## `--input-file` is the single switch

Same flag for all custom types — the parser is selected by `--custom-dataset-type`. Files for `single_turn` / `multi_turn` / `mooncake_trace` / `bailian_trace` / `burst_gpt_trace` are JSONL; `random_pool` accepts a directory or a JSONL with one prompt per line.

## Sampling

`--dataset-sampling-strategy` controls iteration order:

- `sequential` — wraps after end. Default for traces.
- `random` — sample with replacement.
- `shuffle` — shuffle once, exhaust, re-shuffle.

Not compatible with `--fixed-schedule` (timestamps drive order).

## Synthesizing scaled traces

`aiperf synthesize` builds a synthetic trace by scaling an existing one — useful for stress-testing prefix caches at controlled scale.

```bash
aiperf synthesize \
  --input-file mooncake_trace.jsonl --custom-dataset-type mooncake_trace \
  --synthesis-speedup-ratio 2.0 \
  --synthesis-prefix-len-multiplier 1.5 \
  --synthesis-prefix-root-multiplier 4 \
  --synthesis-prompt-len-multiplier 1.0 \
  --synthesis-max-isl 32000 --synthesis-max-osl 2000
```

| Knob | Effect |
|---|---|
| `--synthesis-speedup-ratio` | Compress the timeline (e.g. 2.0 = 2× faster replay). |
| `--synthesis-prefix-len-multiplier` | Scale shared-prefix block counts. |
| `--synthesis-prefix-root-multiplier` | Distribute traces across N independent prefix trees. |
| `--synthesis-prompt-len-multiplier` | Scale unique prompt lengths. |
| `--synthesis-max-isl` | Filter out traces beyond this ISL. |
| `--synthesis-max-osl` | Cap output length on traces beyond this OSL. |
