# Serving backends — TEI, vLLM, OpenRouter, LiteLLM

Open WebUI speaks OpenAI-shape `/v1/embeddings` and Cohere-shape `/rerank`. Any
backend that terminates both works. This file is the per-backend serving layer;
model choice is `model-selection.md`, prefix wiring is `prefix-models.md`.

**The Open WebUI side never changes.** `RAG_EMBEDDING_ENGINE=openai`, the payload
`{"input": [...], "model": "..."}`, prefix handling, batching and concurrency are
identical across all four. Only the URL, the auth, and the failure modes differ.

## Which backend

| | TEI | vLLM | OpenRouter | + LiteLLM |
|---|---|---|---|---|
| Model coverage | BERT/XLM-R encoders | almost anything | fixed catalogue | n/a (proxy) |
| Native rerank | yes, wrong shape | via score API | **yes, Cohere shape** | translates |
| Needs a GPU | yes | yes | no | no |
| Data leaves network | no | no | **yes** | no |
| Best for | classic encoders | modern LLM-based embedders | no-GPU, quick A/B | auth + multi-backend |

Rule of thumb: **BGE-M3 / e5 / classic encoders → TEI. Qwen3-Embedding,
EmbeddingGemma, Nemotron → vLLM. No GPU → OpenRouter.** Add LiteLLM in front when
you need virtual keys, per-model rate limits, request logging, or a
Cohere↔non-Cohere rerank translation.

## TEI

Mature for BERT-family encoders, and the only backend here that auto-truncates
over-length input instead of erroring.

```
Open WebUI → LiteLLM → TEI
             └ embed:  openai-driver → /v1/embeddings
             └ rerank: huggingface-driver → /rerank (Cohere↔TEI translation)
```

**Embed can skip LiteLLM** — TEI serves `/v1/embeddings` natively, so
`RAG_OPENAI_API_BASE_URL: http://tei:8080/v1` works directly.

**Rerank cannot.** TEI's native `/rerank` is `{query, texts}` → `[{index, score}]`.
Open WebUI sends Cohere `{model, query, documents, top_n}` and demands
`{results: [{index, relevance_score}]}`. Direct wiring fails **HTTP 422**.
LiteLLM's HuggingFace rerank handler is the translator.

All TEI-specific cliffs — client batch size, `--max-batch-tokens` as the truncate
boundary, arch-matched Docker images, 429s under fan-out — are `gotchas.md`
§2–§6 and §9. A complete working TEI+LiteLLM deployment is `end-to-end-config.md`.

## vLLM

Required for modern LLM-derived embedders (Qwen3, Gemma3, Mistral-derived), which
TEI does not implement.

```bash
vllm serve <model> \
  --runner pooling \
  --served-model-name <short-name> \
  --gpu-memory-utilization 0.08 \   # else it reserves the whole card for KV cache
  --max-num-seqs 256 \
  --max-num-batched-tokens 32768
```

`--gpu-memory-utilization` is the one people miss: vLLM defaults to ~90% of the
GPU for a KV cache that a pooling model barely uses. On a shared card that
starves everything else.

**Check the model is registered, not merely loadable.** vLLM's embedding registry
(`vllm/model_executor/models/registry.py`, `_EMBEDDING_MODELS`) has explicit
entries for `Qwen3Model`, `Gemma3TextModel`, `BgeM3EmbeddingModel`,
`XLMRobertaModel`, `LlamaBidirectionalModel` and others. An architecture that is
**absent** falls through to generic auto-conversion, which defaults to last-token
pooling — wrong for any mean-pooled model, and wrong silently.

Known cases as of 2026-08-05:

- `Gemma3TextModel` (EmbeddingGemma) — registered, with a dedicated config class
  that reads `use_bidirectional_attention` into `is_causal`, and its ST Dense
  projector implemented and tested. Works out of the box.
- `Ministral3Model` (Nemotron-3-Embed) — **absent from the registry entirely**.
  NVIDIA validates `vllm serve` on v0.20.0–v0.24.0 and `/v2/embed` on v0.25.0;
  latest release is v0.26.0. vLLM issue
  [#48621](https://github.com/vllm-project/vllm/issues/48621) (YaRN scaling, still
  open) is why the card says not to remove `apply_yarn_scaling` from `config.json`.
  Pin a validated version and verify numerically.
- NVIDIA embedding models generally — issue
  [#41390](https://github.com/vllm-project/vllm/issues/41390) reports vLLM being
  **slower than plain HF Transformers** for batch-32 offline pooling, post
  `torch.compile`. Still open.

**vLLM errors on over-length pooling input; TEI truncates.** Open WebUI turns that
error into a `None` and a failed ingest. Either keep `CHUNK_SIZE` well inside the
model's window (the default 1000 characters ≈ 300 tokens is safe everywhere), or
have the caller send `truncate_prompt_tokens` / `truncation_side`, which vLLM's
pooling protocol accepts.

vLLM also exposes `/v2/embed` (Cohere Embed shape) alongside `/v1/embeddings`.
Open WebUI wants the latter.

## OpenRouter

No GPU, no proxy — it terminates both APIs itself. Best used as a zero-setup A/B
harness for candidate models, or when there is no hardware at all.

🔒 Every ingested chunk and every query is sent to a third party. A
data-classification decision outside a lab, and disqualifying for air-gapped or
regulated material.

- Embeddings: `POST https://openrouter.ai/api/v1/embeddings` — OpenAI shape, so
  `RAG_OPENAI_API_BASE_URL: https://openrouter.ai/api/v1` (Open WebUI appends
  `/embeddings`).
- Rerank: `POST https://openrouter.ai/api/v1/rerank` — takes
  `{model, query, documents, top_n}`, the exact Cohere shape Open WebUI sends. Set
  `RAG_EXTERNAL_RERANKER_URL` to the full path; there is no auto-append.

Free models, current pricing, and the full config block are in
`model-selection.md` §"Hosted option: OpenRouter". Two cautions repeated here
because they cost real time: the models API **misreports rerank pricing as zero**
for all six models, and the rerank **response** shape is undocumented — verify it
returns `{"results":[{"index":N,"relevance_score":F}]}` before trusting it.

## LiteLLM

Not a backend — a proxy in front of one. Add it for virtual-key auth, per-model
rate limits, request logging, caching, or rerank-shape translation. It is
**mandatory** only for TEI rerank.

```yaml
model_list:
  - model_name: BAAI/bge-m3                 # ← must match RAG_EMBEDDING_MODEL exactly
    litellm_params:
      model: openai/BAAI/bge-m3             # openai driver, NOT huggingface
      api_base: http://tei:8080/v1
      api_key: dummy
      encoding_format: float                # stops LiteLLM sending null
```

Two recurring traps, both in `gotchas.md`: LiteLLM serialises an unset
`encoding_format` as JSON `null`, which strict parsers reject (§1); and its
HuggingFace *embedding* driver misdetects `task_type` against a TEI endpoint and
sends a wrapped payload TEI rejects with 422 (§2). Use the `openai` driver for
embed and the `huggingface` driver only for rerank.

`model_name` is what Open WebUI must send in `RAG_EMBEDDING_MODEL` /
`RAG_RERANKING_MODEL` — case-sensitive, exact.

## Verifying any backend swap

Embedding is deterministic, so a numerical check settles it:

1. Same text through old and new backend → vectors should match within fp16 noise
   (~1e-5). A mismatch means different pooling, dtype, or a skipped
   sentence-transformers module.
2. Compare against the model card's own published reference scores where they
   exist — that catches a missing Dense projector, which a same-dimension wrong
   vector will not.
3. Confirm prefixes survive the new path using the `ENV=dev`
   `/api/v1/retrieval/ef/{text}` recipe in `prefix-models.md` §Verifying.

Step 2 is the one people skip, and it is the only one that catches "returns 200,
right shape, wrong numbers".
