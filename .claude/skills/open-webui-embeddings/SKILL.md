---
name: open-webui-embeddings
description: |-
  Choose and wire open-weights embedding + reranker models into Open WebUI's RAG pipeline, across TEI, vLLM, OpenRouter or LiteLLM. Covers model selection on current MTEB data (quality, zero-shot contamination, and a FLOPs-based throughput model, since no leaderboard publishes speed), the query/document prefix strings each model needs and the PREFIX_FIELD_NAME mode switch that silently eats them, the exact wire shapes Open WebUI sends (URL auto-append on embed but NOT rerank; strict Cohere rerank shape), per-backend cliffs (LiteLLM encoding_format=null, TEI 422s, vLLM registry gaps and pooling fallbacks, OpenRouter's misreported rerank pricing), and copy-paste config per model.
when_to_use: |-
  Trigger on "open-webui rag", "RAG_OPENAI_API_BASE_URL", "RAG_EXTERNAL_RERANKER_URL", "ExternalReranker", "Cohere rerank shape", "RAG_EMBEDDING_CONCURRENT_REQUESTS", "encoding_format null", "tei docker image hangs"; on model choice: "which embedding model for open-webui", "best reranker", "embeddinggemma", "qwen3-embedding", "qwen3-reranker", "bge-m3", "multilingual-e5", "nemotron embed", "MTEB leaderboard", "embedding throughput"; on prefixes: "RAG_EMBEDDING_QUERY_PREFIX", "RAG_EMBEDDING_PREFIX_FIELD_NAME", "query: passage: prefix", "rag quality dropped after model swap"; and on backends: "vllm embedding serve", "openrouter embeddings", "openrouter rerank". NOT for Open WebUI chat-completion routing, multimodal, or UI/auth; or in-process sentence-transformers embedding.
---

# Open WebUI RAG — embedding + reranking models and backends

Target: operators choosing and wiring open-weights embedding and reranker models into Open WebUI. **Almost every failure mode here degrades quality silently** — right HTTP status, right vector dimension, worse answers — so this skill is built to catch them at config-time rather than by noticing that RAG "feels worse".

**Two layers, kept separate:**

- **Open WebUI's side is backend-agnostic.** `RAG_EMBEDDING_ENGINE=openai`, the `/v1/embeddings` payload, prefix handling, batching and concurrency are identical whether you serve with TEI, vLLM, OpenRouter, or OpenAI itself. That layer is this file plus `references/prefix-models.md`.
- **The serving layer differs per backend** and lives in `references/backends.md` (+ the TEI-specific cliffs in `references/gotchas.md` §2-§6, §9).

Verified against **v0.11.0** source (2026-07-29). The embed and rerank code paths are unchanged from 0.10.2 — 0.11.0's retrieval churn landed almost entirely in `retrieval/web/` (web search), not the embedding core — so every wire shape and env default below still holds. One adjacent 0.11.0 change does affect ingestion verification: see §Verifying ingestion below.

## Start here

| You want to… | Go to |
|---|---|
| Pick an embedder or reranker (quality + speed + price) | `references/model-selection.md` |
| Copy a working config for a specific model | `references/model-selection.md` §Open WebUI config, per model |
| Know which prefix strings a model needs, and why they vanish | `references/prefix-models.md` |
| Serve it on TEI / vLLM / OpenRouter / behind LiteLLM | `references/backends.md` |
| Fix a specific HTTP error | §Triage table below |

**Three findings worth knowing before you choose anything:**

1. **A weak reranker is worse than no reranker.** `bge-reranker-v2-m3` — this skill's former worked example — scores *below* the un-reranked baseline on MTEB-R and MMTEB-R. Prefer `Qwen3-Reranker-0.6B` at identical size and cost.
2. **BGE-M3 is the only prefix-free model in common use.** Every migration off it inherits query/document prefix configuration, and getting that wrong costs quality with no error.
3. **Read MTEB's zero-shot column before its scores.** The current #1 sits at 78% zero-shot — up to 22% of the benchmark may be in its training data.

**Siblings in the `open-webui` plugin.** Setting these values *through the REST
API* rather than the settings UI — and the knowledge/RAG endpoints that ingest
documents — is the **`open-webui-api`** skill. Running more than one Open WebUI
replica, where RAG requests and their WebSocket streams must survive hitting a
different pod, is **`open-webui-valkey-websocket`**.

## The architecture in 30 seconds

Open WebUI terminates two contracts. Anything that speaks both works:

```
Open WebUI ──embed──→  POST {RAG_OPENAI_API_BASE_URL}/embeddings   OpenAI shape
           └─rerank──→ POST {RAG_EXTERNAL_RERANKER_URL}            Cohere shape, strict
```

| Backend | Embed | Rerank |
|---|---|---|
| TEI | direct — serves `/v1/embeddings` natively | ❌ native `/rerank` is `{query, texts}` → 422. **Needs LiteLLM** to translate |
| vLLM | direct — `--runner pooling` | via score API / a shim |
| OpenRouter | direct | direct — its `/api/v1/rerank` is already Cohere-shaped |
| + LiteLLM | proxy: virtual keys, rate limits, logging | proxy + shape translation |

The one hard constraint: **TEI rerank cannot be wired directly.** Its shape is
`{query, texts}` → `[{index, score}]`; Open WebUI demands
`{model, query, documents, top_n}` → `{results: [{index, relevance_score}]}`.
Everything else is a preference. Details in `references/backends.md`.

## Wire shapes (exact)

### Embed — Open WebUI code path

`backend/open_webui/retrieval/utils.py:862` (`generate_openai_batch_embeddings`, v0.11.0):

```http
POST {RAG_OPENAI_API_BASE_URL}/embeddings        ← URL is auto-appended
Authorization: Bearer {RAG_OPENAI_API_KEY}
Content-Type: application/json

{"input": ["text1", "text2", ...], "model": "{RAG_EMBEDDING_MODEL}"}
```

Response parsed as `data["data"][i]["embedding"]` (OpenAI shape).

Async fan-out (`get_embedding_function` at `utils.py:1090`, batching + `asyncio.gather` at `utils.py:1139-1156`, v0.11.0): chunks bundled into batches of `RAG_EMBEDDING_BATCH_SIZE` (default `1`); all batches dispatched concurrently via `asyncio.gather`, wrapped in an `asyncio.Semaphore` only when `RAG_EMBEDDING_CONCURRENT_REQUESTS` is non-zero (default `0` = unlimited). A 100-chunk file at default config fires **100 concurrent single-chunk requests**.

### Rerank — Open WebUI code path

`backend/open_webui/retrieval/models/external.py:13` (`ExternalReranker`, `predict` at line 26; v0.11.0, unchanged since 0.10.2):

```http
POST {RAG_EXTERNAL_RERANKER_URL}                 ← URL is exact, NOT appended
Authorization: Bearer {RAG_EXTERNAL_RERANKER_API_KEY}
Content-Type: application/json

{"model": "{RAG_RERANKING_MODEL}", "query": "...",
 "documents": ["doc1", "doc2", ...], "top_n": <len(documents)>}
```

Response parsed: `data["results"]` sorted by `index`, extracts `relevance_score`. Cohere shape, strict.

Failure handling: `requests.post()` exception or non-2xx → `predict()` returns `None` → retrieval silently downgrades to **un-reranked hybrid order**. No user-visible error in Open WebUI. **Always alert on rerank-side 4xx in TEI/LiteLLM logs.**

## Open WebUI environment variables

| Variable | Mode | Notes |
|---|---|---|
| `RAG_EMBEDDING_ENGINE` | embed | Set to `openai`. Works for OpenAI, LiteLLM, TEI direct, vLLM direct — anything OpenAI-compat. |
| `RAG_OPENAI_API_BASE_URL` | embed | Open WebUI appends `/embeddings`. `http://litellm:4000/v1`, `http://tei:8080/v1`, `http://vllm:8000/v1`, or `https://openrouter.ai/api/v1`. |
| `RAG_OPENAI_API_KEY` | embed | Bearer token. TEI ignores it; LiteLLM and OpenRouter enforce it. |
| `RAG_EMBEDDING_MODEL` | embed | Sent in payload as `model`. Must match the backend's served name exactly — LiteLLM `model_name`, vLLM `--served-model-name`, or the OpenRouter model id. Case-sensitive. |
| `RAG_EMBEDDING_BATCH_SIZE` | embed | Texts per HTTP request. Default `1` — **one round-trip per chunk**, usually the single biggest ingestion bottleneck. `32` is a safe default. Legacy alias `RAG_EMBEDDING_OPENAI_BATCH_SIZE` still honoured (`config.py:1001-1002`). |
| `RAG_EMBEDDING_CONCURRENT_REQUESTS` | embed | Concurrency cap. Default `0` = unlimited (`asyncio.gather` without semaphore). Set to 4-8 so a large upload doesn't burst the backend into 429s. |
| `RAG_EMBEDDING_PREFIX_FIELD_NAME` | embed | **A mode switch, not a value — leave UNSET for `RAG_EMBEDDING_ENGINE=openai`.** Unset = prefix is string-prepended to the text (what vLLM/LiteLLM/TEI need); set = prefix is sent as a separate JSON field, which only Ollama's native API understands. Setting it empty (`""`, or a k8s `name:` with no `value:`) silently disables prefixes. See `references/prefix-models.md`. |
| `RAG_EMBEDDING_QUERY_PREFIX` / `RAG_EMBEDDING_CONTENT_PREFIX` | embed | The query and document label strings. Unused for BGE-M3 (symmetric); **required** for every other mainstream embedder — e5, EmbeddingGemma, Qwen3-Embedding are all asymmetric. Exact per-model strings in `references/prefix-models.md`. Plain `os.getenv` (`config.py:1009-1013`), not PersistentConfig: env-only, invisible in the admin UI, restart to apply. |
| `RAG_RERANKING_ENGINE` | rerank | Set to `external` for Cohere-shape endpoints. |
| `RAG_EXTERNAL_RERANKER_URL` | rerank | **Full URL including path** (no auto-append). `http://litellm:4000/v1/rerank` or `https://openrouter.ai/api/v1/rerank`. |
| `RAG_EXTERNAL_RERANKER_API_KEY` | rerank | Bearer token. |
| `RAG_RERANKING_MODEL` | rerank | Sent in payload as `model`. Match the backend's served name. |
| `RAG_EXTERNAL_RERANKER_TIMEOUT` | rerank | Seconds. Bump for very large `Top_K × Hybrid Search` candidate pools. |

## Triage table

| Symptom | First check | Where |
|---|---|---|
| Embed returns 400 with `encoding_format: expected value` | Add `encoding_format: float` to the LiteLLM litellm_params | `references/gotchas.md` §1 |
| Embed returns 422 with `inputs: data did not match...` | Switch to openai driver — HF driver's task_type detection failed | `references/gotchas.md` §2 |
| Rerank returns 422 with `batch size N > maximum allowed batch size M` | Bump TEI `--max-client-batch-size` | `references/gotchas.md` §3 |
| Rerank returns 404 on `POST /v1` | Open WebUI rerank URL needs full path including `/v1/rerank` | `references/gotchas.md` §7 |
| Open WebUI "Retrieved 1 source" but answer quality dropped | Rerank is silently 4xx — check TEI/LiteLLM logs | `references/gotchas.md` §3 |
| Retrieval quality dropped after an embedding-model swap, no errors anywhere | Asymmetric model needs query/document prefixes, or `PREFIX_FIELD_NAME` is set and eating them | `references/prefix-models.md` |
| TEI pod hangs at "Starting FlashBert model" | Wrong arch image — match GPU compute capability | `references/gotchas.md` §5 |
| TEI returns 429 during knowledge-base upload | Open WebUI concurrency too high; cap `RAG_EMBEDDING_CONCURRENT_REQUESTS` | `references/gotchas.md` §6 |
| Reranker quality degraded since recent config change | `--max-batch-tokens` past trained ceiling lets long inputs through | `references/gotchas.md` §4 |
| `vector_db` directory growing fast | ChromaDB is fine to ~1 GB; past that switch to pgvector halfvec | `references/gotchas.md` §8 |
| Answers got worse after *adding* a reranker | Weak rerankers score below the no-rerank baseline — check the model, not the wiring | `references/model-selection.md` §Rerankers |
| Ingestion is slow regardless of GPU | `RAG_EMBEDDING_BATCH_SIZE` defaults to `1` — one HTTP round-trip per chunk | `references/model-selection.md` §throughput |
| vLLM returns 200 but retrieval is nonsense | Architecture missing from vLLM's `_EMBEDDING_MODELS` → generic last-token pooling fallback | `references/backends.md` §vLLM |
| vLLM 400s on long chunks where TEI was fine | vLLM errors on over-length pooling input; TEI auto-truncates | `references/backends.md` §vLLM |
| OpenRouter rerank returns 200, ordering unchanged | Response shape must be `{results:[{index, relevance_score}]}` or `predict()` returns `None` | `references/backends.md` §OpenRouter |

## Verifying ingestion (changed in 0.11.0)

The obvious way to confirm a knowledge base actually extracted text — list its files and look at the content — **stopped working in 0.11.0**. `Knowledges.get_file_metadatas_by_id` became a column-only `SELECT File.id, File.hash, File.meta, File.created_at, File.updated_at` (`models/knowledge.py:684-694`), deliberately excluding `File.data`, which is where the extracted text lives. Its own docstring says so.

Consequence: `GET /api/v1/knowledge/{id}` and the KB detail view now return file entries with **no extracted content**, so an empty-looking listing no longer distinguishes "extraction failed" from "extraction succeeded, field not selected". To verify extraction actually produced text, fetch the individual file (`GET /api/v1/files/{id}`) rather than reading the collection listing. Knowledge list items gained a `file_count` in exchange.

This is a pure API-shape change — embedding and retrieval quality are unaffected. It matters only for ingestion-verification scripts and health checks.

## Reference index

- **`references/model-selection.md`** — which embedder and which reranker. MTEB scores with the zero-shot contamination column, a FLOPs/MFU throughput model (no leaderboard publishes speed), the reranker table including the below-baseline finding, OpenRouter's free tier with real prices, and a complete copy-paste Open WebUI config block per model. **Load first when choosing or replacing a model.**
- **`references/prefix-models.md`** — symmetric vs asymmetric embedders, exact prefix strings per model, the `PREFIX_FIELD_NAME` mode switch, post-transformer module stacks, and a numerical check that prefixes are really applied. Load whenever the embedder is **not** BGE-M3.
- **`references/backends.md`** — TEI, vLLM, OpenRouter and LiteLLM as peers: which to pick, serving commands, vLLM registry gaps and pooling fallbacks, OpenRouter's API quirks, and how to verify a backend swap numerically.
- **`references/gotchas.md`** — nine gotchas with HTTP error strings, root causes, and fixes. §2-§6 and §9 are TEI-specific; §1 is LiteLLM; §7-§8 are backend-agnostic. Load when the triage table points here.
- **`references/end-to-end-config.md`** — one fully worked TEI + LiteLLM + Open WebUI deployment. Historical worked example (BGE-M3 + BGE-Reranker-v2-m3): correct as a *TEI wiring* reference, but see `model-selection.md` before adopting those two models.
- **`references/performance.md`** — cross-engine numerical-identity check + the measured throughput baseline that calibrates the estimates in `model-selection.md`.
- **`references/sources.md`** — authoritative source files and PR/issue URLs. Load to verify a claim or run `freshen` mode.
