---
name: open-webui-embeddings
description: |-
  Wire HuggingFace embedding + reranker models (BGE-M3, BGE-Reranker-v2-m3, etc.) into Open WebUI's RAG pipeline via LiteLLM as a proxy in front of HuggingFace Text Embeddings Inference (TEI). Covers the exact wire shapes Open WebUI sends (URL auto-append on embed but NOT rerank; payload + response shapes for both modes), the LiteLLM ↔ TEI gotchas (encoding_format=null trap, HF-driver task_type misdetection, openai-driver vs huggingface-driver tradeoffs), TEI configuration cliffs (max-client-batch-size 422 under hybrid search, max-batch-tokens AS the auto-truncate boundary, arch-specific Docker images), and the end-to-end production-grade config. BGE-M3 and BGE-Reranker-v2-m3 are the worked examples; the patterns generalise to any TEI-served encoder.
when_to_use: |-
  Trigger on "open-webui rag", "RAG_OPENAI_API_BASE_URL", "RAG_EXTERNAL_RERANKER_URL", "ExternalReranker", "litellm tei rerank", "litellm huggingface embedding", "encoding_format null", "TEI 400 encoding_format", "TEI 422 batch size", "BGE-M3 deployment", "BGE-Reranker-v2-m3", "open-webui embedding 400", "open-webui rerank 404", "Cohere rerank shape", "/v1/rerank vs /rerank", "hybrid search rerank too large", "tei docker image hangs", "max-batch-tokens trained ceiling", "knowledge base upload slow", "RAG_EMBEDDING_CONCURRENT_REQUESTS", "RAG_EMBEDDING_BATCH_SIZE", "TEI auto-truncate", "openwebui ChromaDB vector_db". NOT for Open WebUI's chat-completion routing, multimodal, or UI; or non-TEI embedding backends (sentence-transformers in-process, Ollama embeddings).
---

# Open WebUI embeddings + reranking — operator reference

Target: operators wiring Open WebUI's RAG pipeline to HuggingFace Text Embeddings Inference (TEI) via LiteLLM. Three hops, each with its own wire-shape quirks. Most failure modes silently degrade to "answer quality dropped" rather than visible errors — this skill is a triage for catching them at config-time.

## The architecture in 30 seconds

```
Open WebUI → LiteLLM proxy → TEI (GPU)
            └ embed: openai-driver → /v1/embeddings
            └ rerank: huggingface-driver → /rerank (Cohere↔TEI translation)
```

Why proxy through LiteLLM rather than point Open WebUI at TEI directly?

- **Embed:** TEI exposes `/v1/embeddings` natively (OpenAI-compat) — direct path works. LiteLLM adds: virtual-key auth, per-model rate limits, request logging, optional caching.
- **Rerank:** TEI's native `/rerank` is `{query, texts}` → `[{index, score}]`. Open WebUI's `ExternalReranker` sends Cohere shape `{query, documents, top_n}` → `{results: [{index, relevance_score}]}`. **Direct path fails with HTTP 422** — wire shapes do not match. LiteLLM's HuggingFace rerank handler translates between the two.

Skipping LiteLLM is therefore feasible only for embed; rerank requires either LiteLLM (or another Cohere↔TEI shim) unless Open WebUI itself is patched.

## Wire shapes (exact)

### Embed — Open WebUI code path

`backend/open_webui/retrieval/utils.py:677` (`generate_openai_batch_embeddings`):

```http
POST {RAG_OPENAI_API_BASE_URL}/embeddings        ← URL is auto-appended
Authorization: Bearer {RAG_OPENAI_API_KEY}
Content-Type: application/json

{"input": ["text1", "text2", ...], "model": "{RAG_EMBEDDING_MODEL}"}
```

Response parsed as `data["data"][i]["embedding"]` (OpenAI shape).

Async fan-out (`utils.py:905`, `get_embedding_function` → `asyncio.gather` at `utils.py:963`): chunks bundled into batches of `RAG_EMBEDDING_BATCH_SIZE` (default `1`); all batches dispatched concurrently via `asyncio.gather` with optional semaphore from `RAG_EMBEDDING_CONCURRENT_REQUESTS` (default `0` = unlimited). A 100-chunk file at default config fires **100 concurrent single-chunk requests**.

### Rerank — Open WebUI code path

`backend/open_webui/retrieval/models/external.py:14` (`ExternalReranker`, `predict` at line 27):

```http
POST {RAG_EXTERNAL_RERANKER_URL}                 ← URL is exact, NOT appended
Authorization: Bearer {RAG_EXTERNAL_RERANKER_API_KEY}
Content-Type: application/json

{"model": "{RAG_RERANKING_MODEL}", "query": "...",
 "documents": ["doc1", "doc2", ...], "top_n": N}
```

Response parsed: `data["results"]` sorted by `index`, extracts `relevance_score`. Cohere shape, strict.

Failure handling: `requests.post()` exception or non-2xx → `predict()` returns `None` → retrieval silently downgrades to **un-reranked hybrid order**. No user-visible error in Open WebUI. **Always alert on rerank-side 4xx in TEI/LiteLLM logs.**

## Open WebUI environment variables

| Variable | Mode | Notes |
|---|---|---|
| `RAG_EMBEDDING_ENGINE` | embed | Set to `openai`. Works for OpenAI, LiteLLM, TEI direct, vLLM direct — anything OpenAI-compat. |
| `RAG_OPENAI_API_BASE_URL` | embed | Open WebUI appends `/embeddings`. Set to `http://litellm:4000/v1` (proxy) or `http://tei:8080/v1` (direct). |
| `RAG_OPENAI_API_KEY` | embed | Bearer token. TEI ignores; LiteLLM enforces virtual key. |
| `RAG_EMBEDDING_MODEL` | embed | Sent in payload as `model`. Must match LiteLLM's `model_name` exactly (case-sensitive, full HF path). |
| `RAG_EMBEDDING_BATCH_SIZE` | embed | Texts per HTTP request. Default `1`. Bumping to `32` reduces per-request overhead during indexing. |
| `RAG_EMBEDDING_CONCURRENT_REQUESTS` | embed | Concurrency cap. Default `0` = unlimited (`asyncio.gather` without semaphore). Set to a bounded number (4-8) to avoid bursting TEI. |
| `RAG_EMBEDDING_PREFIX_FIELD_NAME` | embed | Extra field name for prefix-needing models (e.g. `prompt` for EmbeddingGemma). Leave unset for BGE-M3 — its query/passage symmetry is built into the model. |
| `RAG_EMBEDDING_QUERY_PREFIX` / `RAG_EMBEDDING_CONTENT_PREFIX` | embed | Prefix strings (paired with the field name above). Unused for BGE-M3. |
| `RAG_RERANKING_ENGINE` | rerank | Set to `external` for Cohere-shape endpoints. |
| `RAG_EXTERNAL_RERANKER_URL` | rerank | **Full URL including path** (no auto-append). E.g. `http://litellm:4000/v1/rerank`. |
| `RAG_EXTERNAL_RERANKER_API_KEY` | rerank | Bearer token. |
| `RAG_RERANKING_MODEL` | rerank | Sent in payload as `model`. Match LiteLLM's `model_name`. |
| `RAG_EXTERNAL_RERANKER_TIMEOUT` | rerank | Seconds. Bump for very large `Top_K × Hybrid Search` candidate pools. |

## Triage table

| Symptom | First check | Where |
|---|---|---|
| Embed returns 400 with `encoding_format: expected value` | Add `encoding_format: float` to the LiteLLM litellm_params | `references/gotchas.md` §1 |
| Embed returns 422 with `inputs: data did not match...` | Switch to openai driver — HF driver's task_type detection failed | `references/gotchas.md` §2 |
| Rerank returns 422 with `batch size N > maximum allowed batch size M` | Bump TEI `--max-client-batch-size` | `references/gotchas.md` §3 |
| Rerank returns 404 on `POST /v1` | Open WebUI rerank URL needs full path including `/v1/rerank` | `references/gotchas.md` §7 |
| Open WebUI "Retrieved 1 source" but answer quality dropped | Rerank is silently 4xx — check TEI/LiteLLM logs | `references/gotchas.md` §3 |
| TEI pod hangs at "Starting FlashBert model" | Wrong arch image — match GPU compute capability | `references/gotchas.md` §5 |
| TEI returns 429 during knowledge-base upload | Open WebUI concurrency too high; cap `RAG_EMBEDDING_CONCURRENT_REQUESTS` | `references/gotchas.md` §6 |
| Reranker quality degraded since recent config change | `--max-batch-tokens` past trained ceiling lets long inputs through | `references/gotchas.md` §4 |
| `vector_db` directory growing fast | ChromaDB is fine to ~1 GB; past that switch to pgvector halfvec | `references/gotchas.md` §8 |

## Reference index

- **`references/gotchas.md`** — nine gotchas with HTTP error strings, root causes, and fixes. Load when triage table points here.
- **`references/end-to-end-config.md`** — full working LiteLLM + Open WebUI + TEI config (BGE-M3 + BGE-Reranker-v2-m3 worked example). Load when bootstrapping a new deployment.
- **`references/performance.md`** — quality verification (cross-engine numerical-identity check) + throughput baseline. Load for sizing or post-deployment health checks.
- **`references/sources.md`** — authoritative source files and PR/issue URLs underlying every claim. Load to verify a specific claim or run `freshen` mode.
