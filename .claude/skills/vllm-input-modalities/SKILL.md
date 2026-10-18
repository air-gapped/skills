---
name: vllm-input-modalities
description: |-
  vLLM non-chat inference surfaces — text embeddings (`/v1/embeddings`, `/v2/embed`), reranking/scoring (`/rerank`, `/score`), speech-to-text (`/v1/audio/transcriptions`, `/v1/audio/translations`), document OCR via VLMs. Covers 2026 `--runner pooling` (replacing `--task embed`), v0.20 deprecations (`score`→`classify`, multitask pooling, `encode`→`token_embed`+`token_classify`), Matryoshka/MRL, ColBERT/ColPali/ColQwen late-interaction MaxSim, Cohere v2 `/v2/embed`, Jina v3/v4/v5 quirks, cross-encoder score templates, Whisper large-v3-turbo quants, DeepSeek-OCR recipe (NGramPerReqLogitsProcessor, no prefix cache, GUNDAM mode).
when_to_use: |-
  Trigger on any non-chat vLLM endpoint or non-`/v1/chat/completions` model. Covers `--runner pooling`, `--convert embed|classify`, `--pooler-config`, `--hf-overrides is_matryoshka`, CLS/LAST/MEAN/ALL pooling; BGE-M3, Qwen3-Embedding, Jina v3/v4/v5, Qwen3-Reranker, BGE-reranker, mxbai-rerank, ColBERT, ColPali, ColQwen3/3.5, jina-reranker-v3/m0; Whisper, Voxtral, Qwen3-ASR/Omni, Kimi-Audio, Ultravox, FunASR, GLM-ASR; DeepSeek-OCR, dots-OCR, GLM-OCR, Nemotron-Parse. Narrow phrasings — "is --task embed still supported", "which Whisper quant fits 24 GB", "how to serve ColPali". Also implicit — "serve embed model", "deploy Whisper", "embed endpoint for {model}", "rerank endpoint", "OCR pipeline vLLM", "audit embedder", "deploy-memo for embedding", "spec-study embed/rerank/ASR/OCR".
---

# vLLM — embeddings, reranking, speech-to-text, OCR

Embedding and reranking run on the pooling runner; STT and OCR run on the
generate runner.

## The mental model — one flag rules the surface

vLLM decides what a model *does* from the combination of three flags:

```
--runner {auto|generate|pooling|draft}      # what kind of workload
--convert {auto|none|embed|classify}        # adapt a generative LM to a pooler
--pooler-config '{...}'                     # override pool type, dimensions, etc.
```

The pair `(runner, convert)` replaced `--task`, which no longer parses
(pitfall 1). Canonical today:

| Workload | Command | Runner | Notes |
|---|---|---|---|
| Chat / completion | `vllm serve <model>` | `generate` (auto) | default |
| Embedding | `vllm serve <model> --runner pooling` | `pooling` | auto-detects CLS/LAST/MEAN from config |
| Embedding from a causal LM | `vllm serve <model> --runner pooling --convert embed` | `pooling` | adapts `*ForCausalLM` checkpoints |
| Classification | `vllm serve <model> --runner pooling --convert classify` | `pooling` | also how `score`/`rerank` comes online |
| Speech-to-text | `vllm serve <model>` | `generate` | works on any `SupportsTranscription` model |
| OCR (VLM generate) | `vllm serve <model>` | `generate` | standard chat-completion + image input |

**Scoring API is automatic.** There is no `--enable-scoring-api`. The
`/score` + `/rerank` endpoints light up whenever the loaded model's
`Pooler.get_supported_tasks()` includes `classify` (with `num_labels==1`),
`embed`, or `token_embed` (late-interaction). Nothing for the operator to
toggle.

## Quick-answer router

| Question class | File |
|---|---|
| "Which pooling type? Matryoshka? `/v2/embed`? BGE-M3, Qwen3, Jina?" | `references/embedding.md` |
| "Cross-encoder vs ColBERT? Qwen3-Reranker? BGE-reranker? Score templates?" | `references/reranking.md` |
| "Whisper-turbo? Voxtral? Qwen3-ASR? Chunking? Quants?" | `references/stt.md` |
| "DeepSeek-OCR recipe? dots-OCR? VLM document parsing?" | `references/ocr.md` |
| "Is `--task embed` gone? What replaces `encode`?" | `references/runner-flags.md` |

`scripts/probe-endpoint.sh` checks a running vLLM whether it exposes
`/v1/embeddings`, `/rerank`, `/v1/audio/transcriptions`, etc., so an operator
can confirm the right endpoints are live before pointing a client at it.

## Operator cheat sheet — the common cases inline

### Embedding

```bash
# Qwen3-Embedding (causal LM, last-token pooling — auto-detected)
vllm serve Qwen/Qwen3-Embedding-0.6B --runner pooling

# BGE-M3 (XLM-Roberta, CLS pooling — native embedding model)
vllm serve BAAI/bge-m3 --runner pooling

# Jina v3 (needs trust-remote-code; only text-matching LoRA is merged)
vllm serve jinaai/jina-embeddings-v3 --runner pooling --trust-remote-code

# Jina v4 — use the pre-merged retrieval variant
vllm serve jinaai/jina-embeddings-v4-vllm-retrieval --runner pooling \
  --pooler-config '{"pooling_type":"ALL"}' --dtype float16
# Normalization happens client-side (vector is multi-vector per token).

# Mean-pool override (Sentence-Transformers config is broken for this model)
vllm serve ssmits/Qwen2-7B-Instruct-embed-base --runner pooling \
  --pooler-config '{"pooling_type":"MEAN"}'
```

Client request format is standard OpenAI: `client.embeddings.create(...)`.

**Matryoshka dimensions.** Gated on `is_matryoshka: true` in the model's
`config.json` (or `matryoshka_dimensions`). If the config is missing it,
force-enable:

```bash
--hf-overrides '{"is_matryoshka": true}'
# or pin specific dimensions:
--hf-overrides '{"matryoshka_dimensions":[256,512,768]}'
```

Request-side: `client.embeddings.create(model=..., input=..., dimensions=512)`.
Passing `dimensions` to a non-MRL model (BGE-M3, older BGE) returns a 400 by
design — not a bug.

**`dimensions` above the model's `hidden_size` is rejected as of v0.24.0**
(#46313). Before that, an MRL model with no explicit `matryoshka_dimensions`
list validated only `dimensions >= 1` and then sliced `[..., :d]` — so an
oversized value **silently returned a `hidden_size`-length vector** instead
of erroring. If a client has been over-asking, it was never getting the
width it requested; upgrading turns that into a visible 400. Pin
the list explicitly via `--hf-overrides` to make the valid set unambiguous.

**`/v2/embed` (Cohere v2 compat)** adds `input_type` prompt prefixing,
`output_dimension` (server-side MRL), `truncate=END|START|NONE`, and
`embedding_types=["float","binary","ubinary","base64"]`. Use it when a client
expects Cohere v2's shape.

### Reranking / scoring

Three serving modes; same endpoints, picked automatically:

```bash
# Cross-encoder (classify, num_labels==1)
vllm serve BAAI/bge-reranker-v2-m3 --runner pooling

# Cross-encoder with instruction-aware score template
vllm serve Qwen/Qwen3-Reranker-0.6B --runner pooling --convert classify \
  --chat-template examples/pooling/score/template/qwen3_reranker.jinja \
  --hf-overrides '{"architectures":["Qwen3ForSequenceClassification"],
                    "classifier_from_token":["no","yes"],
                    "is_original_qwen3_reranker":true}'

# Late-interaction (ColBERT family) — MaxSim over token embeddings
vllm serve jinaai/jina-colbert-v2 --runner pooling --trust-remote-code

# Multimodal reranker (ColPali / ColQwen)
vllm serve vidore/colpali-v1.3-hf --runner pooling
```

Client:

```python
# /rerank (Cohere + Jina compat)
resp = requests.post("http://localhost:8000/rerank", json={
    "query": "what is vLLM",
    "documents": ["text 1", "text 2"],
    "top_n": 3,
    "max_tokens_per_doc": 512,  # added v0.20.0 (PR #38827)
})

# /score (bi-encoder cosine, or cross-encoder logit)
resp = requests.post("http://localhost:8000/score", json={
    "text_1": ["query"],
    "text_2": ["doc A", "doc B"],
})
```

Three `score_type`s served through the same routes:

| Score type | Mechanism | Models |
|---|---|---|
| **cross-encoder** | joint query+doc forward → single logit | BGE-reranker-v2-m3/gemma, Qwen3-Reranker, mxbai-rerank-v2, nvidia/llama-nemotron-rerank |
| **late-interaction** | per-token embeddings + MaxSim | ColBERT, ColModernBERT, jina-colbert-v2, ColPali, ColQwen3/3.5, ColModernVBert |
| **bi-encoder** | cosine over `/embeddings` | any embedding model (auto) |

`jinaai/jina-reranker-v3` is listwise ("last but not late interaction") —
`JinaForRanking`, not MaxSim.

### Speech-to-text

```bash
# Whisper large-v3-turbo (base)
vllm serve openai/whisper-large-v3-turbo

# Red Hat production quants (fit on smaller cards, validated)
vllm serve RedHatAI/whisper-large-v3-turbo-FP8-dynamic
vllm serve RedHatAI/whisper-large-v3-turbo-quantized.w8a8
vllm serve RedHatAI/whisper-large-v3-turbo-quantized.w4a16

# Voxtral (Mistral)
vllm serve mistralai/Voxtral-Mini-3B-2507
```

Client:

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=openai/whisper-large-v3-turbo" \
  -F "language=en"
```

Chunking >30 s audio is server-side (energy-aware split at
`min_energy_split_window_size`). Beam-search transcription arrived in v0.18.

**Audio decode backend (v0.30.0+).** Selectable via
`--media-io-kwargs '{"audio": {"audio_backend": "torchcodec"}}'` —
`soundfile`, `pyav`, or `torchcodec`. `auto` (default) tries **torchcodec
first from v0.32.0** (#58364), then soundfile, then pyav; on v0.30.x–v0.31.x
it was soundfile → torchcodec → pyav (#51826, #55642). Only a missing
backend (or a container soundfile cannot read) falls through — other decode
errors raise. Default resampler switched from
PyAV to torchaudio in the same release (#52598); torchaudio ships in the
standard CUDA/ROCm/CPU/XPU requirement files, no extra install. Details:
`references/stt.md` §6.

**OOM on 24 GB with Whisper** (issue #15216) is a known sharp edge — Whisper
allocates aggressively for its encoder KV, despite the 1.6 GB checkpoint.
Production path is one of the RedHatAI quants above, or raising
`--gpu-memory-utilization` past 0.9 with eager mode if memory is truly tight;
unquantized large-v3 / large-v3-turbo wants ≥32 GB for comfortable batch sizes.

### OCR (DeepSeek-OCR)

Canonical recipe from `docs.vllm.ai/projects/recipes`:

```bash
vllm serve deepseek-ai/DeepSeek-OCR \
  --logits-processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0
```

Three non-obvious flags:
- `NGramPerReqLogitsProcessor` is required — without it, table-token
  generation degrades. Send `whitelist_token_ids={128821,128822}`,
  `ngram_size=30`, `window_size=90` per request in `extra_args` — the
  processor reads them from there (`references/ocr.md` §3).
- **Disable prefix caching.** OCR per-request inputs don't share prefixes;
  the cache bookkeeping is pure overhead.
- **`--mm-processor-cache-gb 0`** — the multimodal processor cache isn't
  useful for one-off document images.

DeepSeek reports ~2500 tok/s per A100-40 GB, ~200 k pages/day per GPU. Mode
is hard-coded to GUNDAM (base=1024, image=640, crop=True); Tiny/Small/Base/
Large are not selectable (still hard-coded at v0.32.0).

Invocation is still plain `/v1/chat/completions` with image URLs — there is
no dedicated `/ocr` endpoint.

## Top pitfalls

1. **`--task embed` is dead, not deprecated.** No `--task` in
   `vllm/engine/arg_utils.py` and no `task` field in `ModelConfig` at v0.32.0 —
   passing it is an unrecognized-argument error. Use `--runner pooling`. The `score`
   and `encode` *pooling task names* are removed too and raise
   `VLLMValidationError` (`vllm/tasks.py`): use `--convert classify` on a
   `num_labels==1` model to light up `/score` + `/rerank`, and
   `token_embed` / `token_classify` in place of `encode`.

2. **Pooling runs on PIECEWISE CUDA graphs, not full graphs.** That's
   deliberate (pooling models have variable-shape outputs). Don't force
   `--enforce-eager` for production as older cheat sheets suggest — you lose
   the piecewise graph win without gaining anything.

3. **Qwen3-Reranker needs a score template AND hf-overrides.** It's an
   instruction-tuned causal LM masquerading as a cross-encoder — skipping
   any of the three extras (see the reranking cheat-sheet command above)
   gives random-looking scores, not errors. Full recipe: `references/reranking.md` §2.
   **Second cause of the same symptom, below v0.26.0:** #48901 — any
   LAST-pooling model returns wrong scores once a query+doc pair is long
   enough to be chunk-prefilled, under `torch.compile` (the default). Rule
   out the version before re-checking the overrides.
   **v0.30.0+ warns at startup** if the original Qwen3 reranker
   (`is_original_qwen3_reranker=true`) is served without a chat template —
   check the logs before assuming silent wrong scores (#56017).

4. **Late-interaction kernel regression sniff test.** ColBERT / ColPali
   throughput jumped ~14% in v0.17–0.19 from MaxSim optimisations. If those
   models feel slow, check `--enable-flash-late-interaction` (default true)
   wasn't disabled by an old config. From v0.32.0 the same flag also gates the
   engine-side flash-maxsim Triton kernel (#40337).

## Version gates — check the running version first

Each row changes what a request returns or whether it is accepted. Release
history and the PRs behind each row: `references/sources.md`.

| Running version | What happens | Action | Detail |
|---|---|---|---|
| below v0.26.0 | LAST-pooling models (Qwen3-Reranker, Qwen3-Embedding) return wrong scores when chunked prefill splits a long query+doc pair under `torch.compile` (the default); `--enforce-eager` is correct | Upgrade; **re-score** rankings produced on long documents | `references/reranking.md` §2 |
| below v0.31.0 | Chunked long-text embeddings (`enable_chunked_processing`) come back non-unit length; a non-truncating `max_tokens_per_doc` still changes scores on Qwen3-Reranker-style models | Upgrade; **re-embed / re-score** affected output | `references/embedding.md` §7, `references/reranking.md` §3 |
| v0.31.0+ | A request carrying `mm_processor_kwargs` or `media_io_kwargs` is rejected unless the server runs `--trust-request-mm-kwargs` (chat and pooling/scoring alike) | Set decode options server-side with `--media-io-kwargs`, or add the flag | `references/stt.md` §6 |
| v0.29.x | `media_io_kwargs` is not part of the multimodal cache hash — requests differing only in it hit each other's cache entries | Do not A/B decode settings with the processor cache on | `references/stt.md` §6 |
| v0.29.0+ | Pooling runs on Model Runner V2 by default | `VLLM_USE_V2_MODEL_RUNNER=0` restores V1 (still accepted at v0.32.0) | `references/runner-flags.md` §11 |
| v0.24.0+ | Rerank `top_n` below 0 is a 400 (`-1` used to mean `0`); `top_n=0` still returns all | Send `0` for "all" | `references/reranking.md` §3 |
| v0.24.0+ | `/v1/embeddings` accepts message-shaped input and `chat_template_kwargs` | Use it for instruction-style embedding prompts | `references/embedding.md` §1 |
| v0.20.0+ | `PoolerConfig` `logit_bias`/`logit_scale` renamed `logit_mean`/`logit_sigma` (old names warn); `normalize` → `use_activation`; no automatic multitask pooling — pick one with `--pooler-config.task`; async scheduling off by default for pooling | Rename keys; set the task explicitly | `references/runner-flags.md` §3 |

## Paired skills

- `vllm-configuration` → environment variables, cache paths, telemetry opt-out.
- `vllm-observability` → metrics exposition, Prometheus endpoints.
- `vllm-nvidia-hardware` → SM-level platform support for pooling + FP8 paths.

## Sources

First-party docs: <https://docs.vllm.ai/en/stable/models/pooling_models/>.
Every citation, its verification date and the refresh triggers:
`references/sources.md`.
