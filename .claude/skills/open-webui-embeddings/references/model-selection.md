# Choosing an embedder and a reranker

Load this when picking or replacing a model, not when debugging one. Quality
numbers, throughput estimates, and a complete copy-paste Open WebUI config block
per model — because **every model needs different env vars**, and getting that
wrong degrades retrieval silently.

Leaderboard figures read from <https://mteb-leaderboard.hf.space> on **2026-08-05**.
Re-read before trusting; this list moved substantially in the twelve months prior.

## Embedders — quality

MTEB(Multilingual, v2). `Retr.` is the retrieval task-type average, the column
that matters for RAG. `ZS` is MTEB's zero-shot estimate: the fraction of the
benchmark believed **absent** from that model's training data.

| Model | Params | ZS | Mean(Task) | Retr. | Dim | Ctx |
|---|---|---|---|---|---|---|
| microsoft/harrier-oss-v1-27b | 27B | ⚠️ 78% | 74.27 | 78.27 | — | — |
| tencent/KaLM-Embedding-Gemma3-12B-2511 | 11.8B | ⚠️ 73% | 72.32 | 75.66 | — | — |
| Qwen/Qwen3-Embedding-8B | 7.6B | 99% | 70.58 | 70.88 | 4096 | 32k |
| nvidia/llama-embed-nemotron-8b | 7.5B | 99% | 69.46 | 68.69 | — | — |
| **Qwen/Qwen3-Embedding-4B** | 4.0B | 99% | 69.45 | 69.60 | 2560 | 32k |
| microsoft/harrier-oss-v1-0.6b | 596M | ⚠️ 78% | 69.01 | 70.75 | — | — |
| microsoft/harrier-oss-v1-270m | 268M | ⚠️ 78% | 66.55 | 66.38 | — | — |
| jinaai/jina-embeddings-v5-text-nano | 212M | ⚠️ NA | 65.52 | 63.26 | — | — |
| Qwen/Qwen3-Embedding-0.6B | 596M | 99% | 64.34 | 64.65 | 1024 | 32k |
| intfloat/multilingual-e5-large-instruct | 560M | 99% | 63.22 | 57.11 | 1024 | 512 |
| google/embeddinggemma-300m | 308M | 99% | 61.15 | 62.49 | 768 | 2048 |
| BAAI/bge-m3 | 568M | 98% | 59.55 | 54.59 | 1024 | 8192 |
| intfloat/multilingual-e5-large | 560M | 99% | 58.57 | 53.67 | 1024 | 512 |
| nvidia/Nemotron-3-Embed-1B-BF16 | 1.1B | 95% | **—** | **—** | 2048 | 32k |

**Read `ZS` before `Mean(Task)`.** Harrier tops the board at 78% zero-shot,
meaning up to 22% of the benchmark may be in its training data, and its per-task
rows are dense with ⚠️ markers. Qwen3, EmbeddingGemma and e5 are all 99%. The
most impressive numbers here are the least trustworthy.

**Nemotron-3-Embed has no aggregate score.** It sits at rank #321 with `—`
because it has run only a fraction of the 131 tasks. NVIDIA's own card claims
71.04 on "MMTEB (Retrieval)" and 72.38 on RTEB, but those are self-run at
sequence length 4096 and not comparable to this column. It tops RTEB(beta)
Multilingual — against a 6-model field. Treat as **unproven, not proven-better**.

Also note MTEB ranks by Borda count, not by `Mean(Task)` — rank order and score
order differ. Compare scores, ignore rank.

## Embedders — throughput

Nobody publishes this. MTEB measures quality only (its MODELS page carries
architecture, params, dim, context, release date — no speed). The model cards
don't either; NVIDIA's lists "Throughput and Latency" as metrics and then
publishes neither.

Estimate it instead. Embedding is **pure prefill** — one forward pass, no
autoregressive decode — so FLOPs ≈ 2 × params × tokens. Subtract the vocab
embedding table first; it's a lookup, not a matmul, and it's a large share of
small models.

Calibrated against this skill's own measured baseline (`performance.md`): BGE-M3
at ~150k chars/s ≈ 45k tok/s on ~165 TFLOPS bf16, with ~312M compute params
(568M − 256M vocab table) ⇒ **~17% MFU**. Applied to an H200 (~990 TFLOPS):

| Model | Total | Compute params | ~tok/s | ~chunks/s | vs BGE-M3 |
|---|---|---|---|---|---|
| embeddinggemma-300m | 308M | 107M | 785k | 2,600 | 2.9× faster |
| BAAI/bge-m3 | 568M | 312M | 269k | 900 | 1.0× |
| Nemotron-3-Embed-1B | 1.1B | 830M | 101k | 337 | 2.7× slower |
| Qwen3-Embedding-4B | 4.0B | 3.6B | 23k | 78 | 11.5× slower |
| Qwen3-Embedding-8B | 7.6B | 7.0B | 12k | 40 | 22× slower |

Chunks at Open WebUI's default ~300 tokens (`CHUNK_SIZE=1000` **characters**).
**Estimates, not measurements**, and they flatter small models — tiny models
saturate on per-request overhead long before the GPU is busy, so the real spread
is narrower at the top.

**Split the decision in two:**

- **Query latency — irrelevant.** A query is ~15 tokens. Every model here answers
  in 10–30 ms end-to-end, dominated by HTTP, not compute.
- **Ingestion throughput — where it bites.** 100k chunks on one H200: ~40 s
  (EmbeddingGemma), ~2 min (BGE-M3), ~5 min (Nemotron-1B), ~21 min (Qwen3-4B),
  ~42 min (Qwen3-8B). Even the worst case is a one-time batch job.

Conclusion: **don't let embedding speed drive the choice.** Qwen3-4B's ~12×
throughput penalty buys +15 Mean(Task) for a job you run occasionally.

**Your config matters more than your model.** `RAG_EMBEDDING_BATCH_SIZE` defaults
to `1` — one HTTP round-trip per chunk. At that setting the network path dominates
completely and none of the above is reachable. Setting it to `32` is very likely a
bigger ingestion win than switching models, and it's free.

## Rerankers

Reranking is the **highest-leverage** knob when the embedder is fixed or weak —
and unlike embedding, it sits on the query path, so latency is user-visible.

Qwen's evaluation (their runs, reranking top-100 candidates retrieved by
Qwen3-Embedding-0.6B; the first row is that retriever with **no reranker**):

| Model | Params | MTEB-R | CMTEB-R | MMTEB-R | MLDR | Code | FollowIR |
|---|---|---|---|---|---|---|---|
| *baseline — no reranker* | — | 61.82 | 71.02 | 64.64 | 50.26 | 75.41 | 5.09 |
| jina-multilingual-reranker-v2-base | 0.3B | 58.22 | 63.37 | 63.73 | 39.66 | 58.98 | −0.68 |
| gte-multilingual-reranker-base | 0.3B | 59.51 | 74.08 | 59.44 | 66.33 | 54.18 | −1.64 |
| BAAI/bge-reranker-v2-m3 | 0.6B | 57.03 | 72.16 | 58.36 | 59.51 | 41.38 | −0.01 |
| **Qwen/Qwen3-Reranker-0.6B** | 0.6B | 65.80 | 71.31 | 66.36 | 67.28 | 73.42 | 5.41 |
| **Qwen/Qwen3-Reranker-4B** | 4B | **69.76** | 75.94 | 72.74 | 69.97 | 81.20 | **14.84** |
| Qwen/Qwen3-Reranker-8B | 8B | 69.02 | **77.45** | **72.94** | **70.19** | **81.22** | 8.05 |

⚠️ **A weak reranker is worse than none.** On this protocol
`bge-reranker-v2-m3` scores **57.03 against a 61.82 no-reranker baseline** on
MTEB-R, and 58.36 vs 64.64 on MMTEB-R — it actively reorders good results into
worse ones. `jina-v2-base` does the same. This skill previously used
bge-reranker-v2-m3 as its worked example; treat it as **superseded**.

⚠️ **These are Qwen's numbers for Qwen's models.** A third-party comparison
([aimultiple](https://aimultiple.com/rerankers)) reports the reverse ordering on
an 18-language BEIR-style eval (BGE 67.64 vs Qwen3-0.6B 59.59). The protocols
don't reconcile. Build a 100–500 query golden set from the real corpus and A/B
before committing.

**Default: `Qwen3-Reranker-0.6B`.** Same size and hosting cost as
bge-reranker-v2-m3, Apache 2.0, and it clears the no-reranker baseline. Move to
4B only if ~1s of added query latency is acceptable — its FollowIR 14.84 (vs
5.41) means it genuinely obeys instructions about what "relevant" means.

Reranker latency, same FLOPs model, 50 candidates × ~350 tokens ≈ 17.5k tokens
per search: **0.6B ≈ 90 ms, 4B ≈ 750 ms** per query.

## Open WebUI config, per model

Every block below is complete. `RAG_EMBEDDING_PREFIX_FIELD_NAME` is **absent from
all of them** — that is deliberate and load-bearing (see `prefix-models.md`).

### BAAI/bge-m3 — symmetric, no prefixes

```yaml
- name: RAG_EMBEDDING_ENGINE
  value: "openai"
- name: RAG_OPENAI_API_BASE_URL
  value: "http://litellm:4000/v1"
- name: RAG_EMBEDDING_MODEL
  value: "BAAI/bge-m3"
- name: RAG_EMBEDDING_BATCH_SIZE
  value: "32"
# no prefix vars at all — bge-m3 is the only symmetric model here
```

### google/embeddinggemma-300m — fixed task-vocabulary prefixes

```yaml
- name: RAG_EMBEDDING_ENGINE
  value: "openai"
- name: RAG_OPENAI_API_BASE_URL
  value: "http://litellm:4000/v1"
- name: RAG_EMBEDDING_MODEL
  value: "embeddinggemma"
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "task: search result | query: "     # trailing space required
- name: RAG_EMBEDDING_CONTENT_PREFIX
  value: "title: none | text: "              # trailing space required
- name: RAG_EMBEDDING_BATCH_SIZE
  value: "32"
```

Gated HF repo — the serving pod needs `HF_TOKEN`. Its real output depends on a
768→3072→768 Dense projector in the sentence-transformers wrapper; a backend that
loads only the transformer returns wrong vectors with no error.

### intfloat/multilingual-e5-large — and nvidia/Nemotron-3-Embed-1B (identical strings)

```yaml
- name: RAG_EMBEDDING_ENGINE
  value: "openai"
- name: RAG_OPENAI_API_BASE_URL
  value: "http://litellm:4000/v1"
- name: RAG_EMBEDDING_MODEL
  value: "intfloat/multilingual-e5-large"
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "query: "
- name: RAG_EMBEDDING_CONTENT_PREFIX
  value: "passage: "
- name: RAG_EMBEDDING_BATCH_SIZE
  value: "32"
```

e5's card is emphatic that both prefixes are required *even for non-English text*.
e5-large is 512-token: safe at default chunking, silently truncating if you raise
`CHUNK_SIZE`.

### Qwen/Qwen3-Embedding-* — query-side instruction only

```yaml
- name: RAG_EMBEDDING_ENGINE
  value: "openai"
- name: RAG_OPENAI_API_BASE_URL
  value: "http://litellm:4000/v1"
- name: RAG_EMBEDDING_MODEL
  value: "Qwen/Qwen3-Embedding-4B"
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:"
- name: RAG_EMBEDDING_BATCH_SIZE
  value: "32"
# RAG_EMBEDDING_CONTENT_PREFIX — omit; Qwen3 ships "document": ""
```

Two traps in that one value: **no trailing space** after `Query:` (unlike e5), and
a **real newline** that survives YAML double quotes but *not* single quotes or a
`|` block scalar. Check the rendered manifest if templating through Helm.

The instruction is a tunable — rewrite it for the corpus (in English, even for
non-English content) for a documented 1–5% gain.

### Reranker — Qwen3-Reranker-0.6B

```yaml
- name: RAG_RERANKING_ENGINE
  value: "external"
- name: RAG_EXTERNAL_RERANKER_URL
  value: "http://litellm:4000/v1/rerank"    # full path, no auto-append
- name: RAG_EXTERNAL_RERANKER_API_KEY
  value: "<key>"
- name: RAG_RERANKING_MODEL
  value: "Qwen/Qwen3-Reranker-0.6B"
```

Rerankers take no prefixes — cross-encoders receive the (query, document) pair
directly. None of `prefix-models.md` applies to `RAG_RERANKING_*`.

### Switching models invalidates the index

Vector dimension changes with the model (bge-m3 1024 → EmbeddingGemma 768 →
Nemotron 2048 → Qwen3-4B 2560). Collections are fixed-dimension: drop and
re-ingest every knowledge base. Changing only a *prefix string* also requires
re-ingest — existing vectors were built under the old label.

## Hosted option: OpenRouter

Useful when no GPU is available, or as a zero-setup A/B harness for candidate
models. Prices read from openrouter.ai on **2026-08-05**.

🔒 **Egress warning.** Every chunk ingested and every query is sent to a third
party. Fine for a lab; a data-classification decision anywhere else, and
disqualifying for air-gapped or regulated material.

**Embeddings** — free tier:

| Model | Ctx | Price |
|---|---|---|
| `nvidia/nemotron-3-embed-1b:free` | 32k | **$0** |
| `nvidia/llama-nemotron-embed-vl-1b-v2:free` | 131k | **$0** |

Paid, notable: `qwen/qwen3-embedding-8b` and `baai/bge-m3` and
`intfloat/multilingual-e5-large` at $0.01/M tokens; `qwen/qwen3-embedding-4b` at
$0.02/M.

**Rerank** — only one is free:

| Model | Ctx | Price |
|---|---|---|
| `nvidia/llama-nemotron-rerank-vl-1b-v2:free` | 10k | **$0** |
| `voyageai/rerank-2.5-lite` | 32k | $0.02/M tokens |
| `voyageai/rerank-2.5` | 32k | $0.05/M tokens |
| `cohere/rerank-v3.5` | 4k | $0.001/**search** |
| `cohere/rerank-4-fast` | 33k | $0.002/search |
| `cohere/rerank-4-pro` | 33k | $0.0025/search |

⚠️ **`GET /api/v1/models?output_modalities=rerank` reports
`{"prompt":"0","completion":"0"}` for all six.** That is missing metadata, not six
free models — Cohere is priced per search unit. Read prices off the model page,
not the API.

`llama-nemotron-rerank-vl-1b-v2` is a **vision-language** reranker (actually 1.7B)
built for chart/table RAG. It accepts text-only input, but bench it against
Qwen3-Reranker-0.6B before treating it as a text reranker.

### OpenRouter config — no LiteLLM needed

OpenRouter is itself the shim. Its `POST /api/v1/rerank` takes
`{model, query, documents, top_n}` — exactly the Cohere shape Open WebUI's
`ExternalReranker` sends.

```yaml
- name: RAG_EMBEDDING_ENGINE
  value: "openai"
- name: RAG_OPENAI_API_BASE_URL
  value: "https://openrouter.ai/api/v1"       # /embeddings is auto-appended
- name: RAG_OPENAI_API_KEY
  value: "<openrouter-key>"
- name: RAG_EMBEDDING_MODEL
  value: "nvidia/nemotron-3-embed-1b:free"
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "query: "
- name: RAG_EMBEDDING_CONTENT_PREFIX
  value: "passage: "

- name: RAG_RERANKING_ENGINE
  value: "external"
- name: RAG_EXTERNAL_RERANKER_URL
  value: "https://openrouter.ai/api/v1/rerank"   # full path
- name: RAG_EXTERNAL_RERANKER_API_KEY
  value: "<openrouter-key>"
- name: RAG_RERANKING_MODEL
  value: "nvidia/llama-nemotron-rerank-vl-1b-v2:free"
```

**Unverified:** the rerank *request* shape is confirmed from OpenRouter's SDK docs;
the *response* shape is not documented. Open WebUI requires
`{"results":[{"index":N,"relevance_score":F}]}` exactly. Confirm with one curl
before relying on it — a mismatch makes `predict()` return `None` and retrieval
silently falls back to un-reranked order.

## Picking, in one paragraph

Self-hosted with a GPU: **Qwen3-Embedding-4B + Qwen3-Reranker-0.6B**. Best
quality at 99% zero-shot, both Apache 2.0, both first-class in vLLM, ingestion
cost is a one-time ~20 minutes. Constrained to a small model:
**EmbeddingGemma-300m** beats e5-large decisively, and pairing it with a real
reranker recovers more than the embedder costs. No GPU: OpenRouter's free NVIDIA
pair, subject to the egress warning. Avoid: bge-reranker-v2-m3 (below baseline),
and any harrier number you have not reproduced yourself.

## Sources

| Claim | Source | Verified |
|---|---|---|
| All MTEB(Multilingual, v2) scores, ZS column, Nemotron's `—` aggregate | <https://mteb-leaderboard.hf.space/benchmark/MTEB(Multilingual,%20v2)> | 2026-08-05 |
| RTEB(beta) field size and Nemotron-3-Embed-8B at #1 | <https://mteb-leaderboard.hf.space/benchmark/RTEB(beta)> | 2026-08-05 |
| MTEB publishes no speed metric | leaderboard MODELS page enumerates its own fields | 2026-08-05 |
| Reranker table | `Qwen/Qwen3-Reranker-4B` → `README.md` §Evaluation | 2026-08-05 |
| Nemotron self-reported RTEB / MMTEB-Retrieval | `nvidia/Nemotron-3-Embed-1B-BF16` → `README.md` | 2026-08-05 |
| OpenRouter model lists | `GET https://openrouter.ai/api/v1/models?output_modalities={embeddings,rerank}` | 2026-08-05 |
| OpenRouter real prices | openrouter.ai/models model cards (API pricing metadata is wrong for rerank) | 2026-08-05 |
| OpenRouter rerank request shape | `https://openrouter.ai/docs/client-sdks/python/sdks/rerank/README.md` | 2026-08-05 |
| MFU calibration | this skill's `references/performance.md` BGE-M3 baseline | 2026-08-05 |
