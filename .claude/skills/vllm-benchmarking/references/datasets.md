# Dataset catalog for `vllm bench`

Load when picking `--dataset-name` for a specific test. What each tests, when to reach for it, and whether it hits the network.

## In-tree, no network required

- **`random`** — synthetic uniform tokens. Flags: `--random-input-len`, `--random-output-len`, `--random-num-prompts`. Use for: isolating engine throughput from prefix effects. **Avoid for: caching claims** — zero prefix structure makes cached workloads look flat.
- **`sonnet`** — synthetic from Claude prompt patterns. Ships at `vllm/benchmarks/sonnet.txt`. Flags: `--sonnet-input-len`, `--sonnet-output-len`. Use for: reproducible general-purpose load with natural-language structure.
- **`prefix_repetition`** — synthetic with shared prefix across prompts. Flags: `--prefix-repetition-prefix-len`, `--prefix-repetition-suffix-len`, `--prefix-repetition-num-prefixes`, `--prefix-repetition-output-len`. **Use this** to benchmark prefix-cache hit rate and DRAM/NVMe offload wins.
- **`random-mm`** — multimodal synthetic. Flags: `--random-mm-num-images`, `--random-mm-num-video-frames`. For vision/audio model serving.
- **`random-rerank`** — reranking workload. Flags: `--random-rerank-input-len`, `--random-rerank-output-len`.

## External file-based

- **`sharegpt`** — real conversational data (ShareGPT dump). Use for: "realistic average prompt" when prod replay isn't available. Requires `--dataset-path` pointing at a JSON file. **Air-gapped:** pre-download `ShareGPT_V3_unfiltered_cleaned_split.json` on a connected host, rsync into the enclave.
- **`burstgpt`** — variable-length distributions mimicking real burst patterns. Flags: `--burstgpt-input-len`, `--burstgpt-output-len`.
- **`custom`** — arbitrary JSONL file. One prompt per line with `{"prompt": "..."}` schema, optional `"output_tokens"` field. **Best for production A/B** — capture real prod prompts, replay them. If `--output-len` is unset or `-1`, the `output_tokens` field per row is mandatory.

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
