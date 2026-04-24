---
name: vllm-input-modalities
description: |-
  vLLM non-chat inference surfaces — text embeddings (`/v1/embeddings`, `/v2/embed`), reranking/scoring (`/rerank`, `/score`), speech-to-text (`/v1/audio/transcriptions`, `/v1/audio/translations`), document OCR via VLMs. Covers 2026 `--runner pooling` (replacing `--task embed`), v0.20 deprecations (`score`→`classify`, multitask pooling, `encode`→`token_embed`+`token_classify`), Matryoshka/MRL, ColBERT/ColPali/ColQwen late-interaction MaxSim, Cohere v2 `/v2/embed`, Jina v3/v4/v5 quirks, cross-encoder score templates, Whisper large-v3-turbo quants, DeepSeek-OCR recipe (NGramPerReqLogitsProcessor, no prefix cache, GUNDAM mode).
when_to_use: |-
  Trigger on any non-chat vLLM endpoint or non-`/v1/chat/completions` model. Covers `--runner pooling`, `--convert embed|classify`, `--pooler-config`, `--hf-overrides is_matryoshka`, CLS/LAST/MEAN/ALL pooling; BGE-M3, Qwen3-Embedding, Jina v3/v4/v5, Qwen3-Reranker, BGE-reranker, mxbai-rerank, ColBERT, ColPali, ColQwen3/3.5, jina-reranker-v3/m0; Whisper, Voxtral, Qwen3-ASR/Omni, Kimi-Audio, Ultravox, FunASR, GLM-ASR; DeepSeek-OCR, dots-OCR, GLM-OCR, Nemotron-Parse. Narrow phrasings — "is --task embed still supported", "which Whisper quant fits 24 GB", "how to serve ColPali". Also implicit — "serve embed model", "deploy Whisper", "embed endpoint for {model}", "rerank endpoint", "OCR pipeline vLLM", "audit embedder", "deploy-memo for embedding", "spec-study embed/rerank/ASR/OCR".
---

# vLLM — embeddings, reranking, speech-to-text, OCR

Target audience: operators who need vLLM's non-chat-completion surfaces. Four
capabilities bundled here because they share operator-facing concepts
(`--runner` flag, pooling configuration, scoring API, multimodal preprocessing)
even though two run on the pooling runner (embedding, reranking) and two run
on the generate runner (STT, OCR).

## The mental model — one flag rules the surface

vLLM decides what a model *does* from the combination of three flags:

```
--runner {auto|generate|pooling|draft}      # what kind of workload
--convert {auto|none|embed|classify}        # adapt a generative LM to a pooler
--pooler-config '{...}'                     # override pool type, dimensions, etc.
```

The pair `(runner, convert)` has replaced the old `--task {generate|embed|
score|classify|reward|...}` flag. The old `--task` is **deprecated** and
still works in current releases, but emits a deprecation warning and is
scheduled for full removal. Canonical today:

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
  --chat-template examples/templates/qwen3_reranker.jinja \
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
    "max_tokens_per_doc": 512,  # added in late 2025
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

**OOM on 24 GB with Whisper** (issue #15216) is a known sharp edge — Whisper
allocates aggressively for its encoder KV, despite the 1.6 GB checkpoint.
Production path is one of the RedHatAI quants above, or raising
`--gpu-memory-utilization` past 0.9 with eager mode if memory is truly tight.

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
  generation degrades. Enforces `whitelist_token_ids={128821,128822}`,
  `ngram_size=30`, `window_size=90`.
- **Disable prefix caching.** OCR per-request inputs don't share prefixes;
  the cache bookkeeping is pure overhead.
- **`--mm-processor-cache-gb 0`** — the multimodal processor cache isn't
  useful for one-off document images.

DeepSeek reports ~2500 tok/s per A100-40 GB, ~200 k pages/day per GPU. Mode
is hard-coded to GUNDAM (base=1024, image=640, crop=True); Tiny/Small/Base/
Large aren't exposed via env vars yet (tracked issue, as of early 2026).

Invocation is still plain `/v1/chat/completions` with image URLs — there is
no dedicated `/ocr` endpoint.

## Top pitfalls

1. **`--task embed` is deprecated, not dead.** It still works in current
   vLLM, with a warning. New deployments should use `--runner pooling`. The
   `score` task is also deprecated; use `--convert classify` on a
   `num_labels==1` model to light up `/score` + `/rerank`.

2. **Pooling runs on PIECEWISE CUDA graphs, not full graphs.** That's
   deliberate (pooling models have variable-shape outputs). Don't force
   `--enforce-eager` for production as older cheat sheets suggest — you lose
   the piecewise graph win without gaining anything.

3. **Jina v4 base checkpoint is not vLLM-compatible.** Use
   `jinaai/jina-embeddings-v4-vllm-retrieval` (pre-merged retrieval adapter).
   Serve with `--pooler-config '{"pooling_type":"ALL"}' --dtype float16` and
   normalize client-side — output is multi-vector per token.

4. **Matryoshka without config.** If a model documents MRL support but
   `config.json` lacks `is_matryoshka` / `matryoshka_dimensions`, the server
   returns 400 for any `dimensions` param. Fix: `--hf-overrides
   '{"is_matryoshka":true}'` at serve time. Don't confuse with BGE-M3, which
   genuinely doesn't support MRL.

5. **Qwen3-Reranker needs a score template AND hf-overrides.** It's an
   instruction-tuned causal LM masquerading as a cross-encoder — vLLM needs
   `classifier_from_token=["no","yes"]` + `is_original_qwen3_reranker=true`
   + `--chat-template qwen3_reranker.jinja`. Skipping any of the three gives
   random-looking scores.

6. **DeepSeek-OCR with prefix caching on.** It doesn't crash — it just
   wastes time and memory. Same for `--mm-processor-cache-gb > 0` for pure
   OCR traffic. Both defaults are wrong for this workload.

7. **Whisper OOM on 24 GB.** Not a bug. Use a Red Hat quant, or accept that
   large-v3 / large-v3-turbo wants ≥32 GB for comfortable batch sizes.

8. **Late-interaction kernel regression sniff test.** ColBERT / ColPali
   throughput jumped ~14% in v0.17–0.19 from MaxSim optimisations. If those
   models feel slow, check `--enable-flash-late-interaction` (default true)
   wasn't disabled by an old config.

## Landed in v0.20.0 (released 2026-04-23) — verify your deployment

The deprecations previously flagged as "scheduled for v0.20" have now shipped.
Callouts from the v0.20.0 release notes (Breaking Changes + API sections):

- **`logit_bias` / `logit_scale` → `logit_mean` / `logit_sigma`** in
  `PoolerConfig` — explicit breaking change, PR #39530. Old names still
  accepted with deprecation warning.
- **Async scheduling default OFF for pooling models** (PR #39592) — explicit
  breaking change. Pooling throughput should be marginally lower but
  stability improves; re-enable case-by-case if you measured a win on v0.19.
- `--task` flag — still accepted with deprecation warning; `--runner` +
  `--convert` is canonical.
- `score` pooling task — replaced by `classify` + `num_labels==1`.
- Pooling **multitask** — pick a task explicitly via `PoolerConfig(task=...)`
  or `--pooler-config.task <task>`; automatic multitasking is gone.
- `encode` task — split into `token_embed` and `token_classify`.
- `normalize` in `PoolingParams` — removed; use `use_activation`.

Two performance wins also landed in v0.20.0 for pooling:

- **#38559** — mean-pooling optimisation via `index_add` (+5.9% on mean-pool models).
- **#39113** — redundant-sync removal for pooling (+3.7% throughput).

Also landed: `jina-reranker-v3` (#38800), **Jina Embeddings v5** (#39575),
`max_tokens_per_doc` in `/rerank` (#38827), **Generative Scoring** (#34539),
ASR multi-chunk spacing fix (#39116).

## Paired skills

- `vllm-configuration` → environment variables, cache paths, telemetry opt-out.
- `vllm-observability` → metrics exposition, Prometheus endpoints.
- `vllm-nvidia-hardware` → SM-level platform support for pooling + FP8 paths.

## Source and refresh policy

- First-party: vLLM docs at
  <https://docs.vllm.ai/en/stable/models/pooling_models/> (README + embed /
  scoring / token_embed / specific_models subpages), and
  `docs/contributing/model/transcription.md` in the repo.
- Production STT canonical reference: Red Hat Developer blog for Whisper +
  RHAIIS (link in `references/stt.md`).
- DeepSeek-OCR canonical reference: vLLM recipes page (link in
  `references/ocr.md`).
- Refresh triggers: any v0.21+ release (further pooling-runner changes), a
  new Jina embeddings major version, or a new native-multimodal reranker
  shipping.
- External-ref audit log: `references/sources.md`.

Last verified: 2026-04-24 (against vLLM v0.20.0 release notes).
