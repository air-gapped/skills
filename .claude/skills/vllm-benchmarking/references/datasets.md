# Dataset catalog for `vllm bench`

Load when picking `--dataset-name` for a specific test. What each tests, when to reach for it, and whether it hits the network.

**Module moved (2026-07-21).** The dataset registry is no longer
`vllm/benchmarks/datasets.py` — it is now a package,
`vllm/benchmarks/datasets/datasets.py` (~4,800 lines), alongside `utils.py` and
`create_txt_slices_dataset.py`. Any tooling or citation pointing at the old flat
path will 404.

**Names newly observed in the v0.25.1 tree** and not previously catalogued here:
`bfcl` (tool-calling, PR #42457), `random-mm`, `random-rerank`, `timed_trace`.
This is what was seen in-tree, not a claim of completeness — the rendered docs
table remains the authority for the supported set.

## In-tree, no network required

- **`random`** — synthetic uniform tokens. Flags: `--random-input-len`, `--random-output-len`, `--random-num-prompts`. Use for: isolating engine throughput from prefix effects. **Avoid for: caching claims** — zero prefix structure makes cached workloads look flat.
- **`sonnet`** — synthetic from Claude prompt patterns. Ships at `vllm/benchmarks/sonnet.txt`. Flags: `--sonnet-input-len`, `--sonnet-output-len`. **Marked deprecated in docs.vllm.ai/en/latest/benchmarking/cli/ as of 2026-04-24** — still works but will be removed. For new benchmarks prefer `random` (engine isolation), `prefix_repetition` (caching), or `custom` (prod replay). Use `sonnet` only to reproduce older baseline runs.
- **`prefix_repetition`** — synthetic with shared prefix across prompts. Flags: `--prefix-repetition-prefix-len`, `--prefix-repetition-suffix-len`, `--prefix-repetition-num-prefixes`, `--prefix-repetition-output-len`. **Use this** to benchmark prefix-cache hit rate and DRAM/NVMe offload wins.
- **`spec_bench`** — Spec-Bench, the dataset for **speculative-decoding** benchmarking (in docs dataset table, verified 2026-05-28). Use when measuring EAGLE / Medusa / MTP draft-acceptance behavior; pair with the `spec_decode_*` output fields in `output-schema.md`. Sourced from `raw.githubusercontent.com/hemingkx/Spec-Bench/.../question.jsonl` — stage the JSONL for air-gapped.
- **`speed_bench`** — SPEED-Bench, a unified speculative-decoding workload from NeMo-Skills (in docs dataset table, verified 2026-05-28). Same use case as `spec_bench`; prepared via the NeMo-Skills `speed-bench/prepare.py` script — stage the output for air-gapped.
- **`random-mm`** — multimodal synthetic. Flags: `--random-mm-num-images`, `--random-mm-num-video-frames`. For vision/audio model serving.
- **`random-rerank`** — reranking workload. Flags: `--random-rerank-input-len`, `--random-rerank-output-len`.

## External file-based

- **`sharegpt`** — real conversational data (ShareGPT dump). Use for: "realistic average prompt" when prod replay isn't available. Requires `--dataset-path` pointing at a JSON file. **Air-gapped:** pre-download `ShareGPT_V3_unfiltered_cleaned_split.json` on a connected host, rsync into the enclave.
- **`burstgpt`** — variable-length distributions mimicking real burst patterns. Flags: `--burstgpt-input-len`, `--burstgpt-output-len`.
- **`custom`** — arbitrary JSONL file. One prompt per line with `{"prompt": "..."}` schema, optional `"output_tokens"` field. **Best for production A/B** — capture real prod prompts, replay them. If `--output-len` is unset or `-1`, the `output_tokens` field per row is mandatory.
- **`custom_audio`** / **`custom_image`** — multimodal variants of `custom` (in docs dataset table, verified 2026-05-28). Local JSONL referencing audio/image inputs (`audio_data.jsonl` / `image_data.jsonl`). Use to replay real multimodal prod traffic against ASR / VLM endpoints; always local, no network.

## HuggingFace datasets (`hf`)

- `--dataset-name hf --hf-subset <subset> --hf-split <split>` loads a HF dataset. Supported templates include: Conversation, MultiModalConversation, VisionArena, MMVU, InstructCoder, AIMODataset, TxtSlices, ASRDataset.
- Requires network access OR a pre-seeded HF cache. See `air-gapped.md` for seeding.

## Picking a dataset for a given question

| Question | Dataset | Why |
|---|---|---|
| "Engine throughput regression?" | `random` | Isolates engine from prefix effects |
| "Does prefix caching help?" | `prefix_repetition` | Controlled prefix overlap, measurable hit rate |
| "Does change X help prod traffic?" | `custom` (replay) | Only prod-shaped data gives trustworthy A/B |
| "Rough serving baseline" | `sonnet` or `sharegpt` | Natural structure, no prod data needed |
| "Burst load handling" | `burstgpt` | Variable lengths match real spiky traffic |
| "VLM performance" | `random-mm` or HF VisionArena | Exercises MM preprocessor + decode |
| "Cold-start / single-request" | `random` with `--num-prompts 1` | Isolates latency from queueing |

## Capturing production prompts for `custom` replay

Log prompts (not completions — no PII concerns) for a representative window, emit JSONL:

```python
# pseudo-code for a logger tap
import json
with open("prod-replay.jsonl", "a") as f:
    f.write(json.dumps({"prompt": request.prompt, "output_tokens": response.completion_token_count}) + "\n")
```

Then: `vllm bench serve ... --dataset-name custom --dataset-path prod-replay.jsonl`.

This is the single most important thing an operator can do for trustworthy benchmarking — everything else is a proxy for this.
