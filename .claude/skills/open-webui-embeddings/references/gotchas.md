# Gotchas catalog

Each gotcha is independent — load this file when the triage table in SKILL.md points here for a specific symptom.

## 1. LiteLLM injects `encoding_format: null` → TEI 400

```
HTTP 400: "Failed to parse the request body as JSON:
encoding_format: expected value at line 1 column 57"
```

LiteLLM's openai driver serialises `encoding_format=None` as JSON `null` whenever the caller (Open WebUI) does not set the field. TEI's strict JSON parser rejects null on enum fields.

**Fix:** pin `encoding_format: float` in the model's `litellm_params`:

```yaml
- model_name: BAAI/bge-m3
  litellm_params:
    model: openai/BAAI/bge-m3
    api_base: http://tei:8080/v1
    api_key: dummy
    encoding_format: float       # ← stops LiteLLM from sending null
```

**History:** LiteLLM PR #25395 fixed this on 2026-04-12 by omitting null `encoding_format` from upstream requests; PR #25698 reverted it 2 days later — forcing `"float"` for everyone broke other providers. Issue #25388 reads "closed" but the bug behaves identically in the latest LiteLLM. The per-model pin is durable, version-independent.

**Also affects:** GiteeAI, SiliconFlow, any provider with strict JSON validation on OpenAI fields.

## 2. LiteLLM HF driver task_type misdetection → TEI 422

Symptom (with `model: huggingface/BAAI/bge-m3` for embedding):

```
HTTP 422: "Failed to deserialize the JSON body into the target type:
inputs: data did not match any variant of untagged enum Input"
```

The HF embedding handler queries `<api_base>/api/models/<model>` to discover `pipeline_tag`. The query 404s against a TEI endpoint; the handler defaults wrongly (often `sentence-similarity`) and sends the wrapped shape `{"inputs": {"source_sentence": ..., "sentences": [...]}}`, which TEI's `/embed` route rejects.

**Fix:** do not use the HF driver for embedding. Use the openai driver against TEI's `/v1/embeddings`:

```yaml
litellm_params:
  model: openai/BAAI/bge-m3      # NOT huggingface/...
  api_base: http://tei:8080/v1   # /v1 for OpenAI-compat
  encoding_format: float
```

The HF driver is the **right** choice for **rerank** — it sees `mode: rerank` in `model_info`, uses the rerank-specific transformation, and translates Cohere shape correctly to TEI native.

## 3. TEI `--max-client-batch-size` rejects hybrid-search rerank

```
HTTP 422: {"error": "batch size 91 > maximum allowed batch size 64",
           "error_type": "Validation"}
```

Open WebUI hybrid search merges BM25 top-K + dense top-K (deduplicated). With low overlap, the union approaches `2 × Top_K`. Open WebUI sends ALL candidates to the reranker in one request. TEI's `--max-client-batch-size` (default 32) caps client-supplied batch size.

**Fix:** bump TEI manifest to cover the worst case:

```yaml
args:
  - --max-client-batch-size=128       # cover 2 × Top_K=50 + headroom
```

Latency impact: 128-doc rerank request ≈ N forward passes (bounded by `--max-batch-tokens`). For BGE-Reranker-v2-m3 at typical query+doc lengths and `--max-batch-tokens=1024`, ~25-30 forwards × 13 ms ≈ 350-400 ms inference, plus tokenization + queue. ~1-2 s wall time per rerank under typical load — acceptable for chat.

The Open WebUI `ExternalReranker.predict()` swallows the 422 and returns `None`. Retrieval silently falls back to un-reranked hybrid order. **Failure is invisible to users.**

## 4. TEI `--max-batch-tokens` IS the auto-truncate boundary

With `--auto-truncate=true`, individual inputs are truncated at `min(model_native_max, --max-batch-tokens)`. So `--max-batch-tokens=1024` on a model with native 8192 max → all inputs truncated at 1024.

This matters for the **reranker** (BGE-Reranker-v2-m3 was trained at `max_length=1024` per HF disc #9; technical max 8192). Setting `--max-batch-tokens=1024` enforces the trained ceiling — bumping past 1024 lets untrained-length inputs through and degrades quality.

For **BGE-M3** (trained at full XLM-R 8192), `--max-batch-tokens=32768` (or higher) only constrains pack budget, not per-input length — the model's 8192 native max binds first. Pack-budget bumps do not hurt quality for the embedder.

To relax the reranker batch budget for throughput, raise `--max-concurrent-requests=1024` (queue admission) and `--max-client-batch-size=128` (per-client cap) — leave `--max-batch-tokens=1024` to preserve quality.

## 5. TEI Docker image arch matching

Generic `text-embeddings-inference:cuda-1.9.x` is `text-embeddings-router-80` — compiled for SM 8.0 (Ampere). On non-native compute capabilities, Candle's FlashBert JIT-compiles kernels at runtime, which can hang silently for >10 minutes (eventually liveness-killed).

| GPU family | Compute capability | TEI image tag |
|---|---|---|
| Pascal (1050 Ti, 1080 Ti) | 6.1 | none — build from source with `CUDA_COMPUTE_CAP=61` |
| Turing (T4, 2080 Ti, 16xx) | 7.5 | `turing-1.9.x` |
| Ampere datacenter (A100) | 8.0 | `cuda-1.9.x` (default) |
| Ampere consumer (A10, RTX 30xx) | 8.6 | `86-1.9.x` |
| Ada Lovelace (RTX 40xx) | 8.9 | `89-1.9.x` |
| Hopper (H100/H200) | 9.0 | `hopper-1.9.x` |
| Blackwell (B100/B200/RTX 50xx) | 10.0+ | check current TEI release tags |

If the image tag does not match the GPU, expect either silent hang at warmup OR much slower throughput from FlashAttention disabled. FlashBert requires compute capability ≥ 7.5 — Pascal cannot use it at all and falls back to slower kernels.

## 6. Open WebUI concurrent fan-out can overwhelm TEI

A 100-chunk knowledge-base file at default Open WebUI config (`RAG_EMBEDDING_CONCURRENT_REQUESTS=0` = unlimited, `RAG_EMBEDDING_BATCH_SIZE=1`) fires 100 concurrent embed requests via `asyncio.gather`. TEI's `--max-concurrent-requests` (default 512) is the queue cap; beyond which requests get HTTP 429.

**Fix (Open WebUI side, preferred):** bound the fan-out:

```
RAG_EMBEDDING_CONCURRENT_REQUESTS=4
RAG_EMBEDDING_BATCH_SIZE=32
```

Small concurrency × bigger batches reduces request count 32× while keeping pipelining healthy. TEI's batching fuses adjacent requests anyway — bigger client batches do not hurt internal throughput.

**Fix (TEI side, defensive):** raise the queue cap:

```yaml
args:
  - --max-concurrent-requests=1024
```

## 7. `RAG_EXTERNAL_RERANKER_URL` is exact-URL, not auto-append

The embed URL auto-appends `/embeddings` (`utils.py:698`). The rerank URL does NOT (`external.py:50`: `requests.post(f'{self.url}', ...)`). Mirror the embed convention and the request 404s.

```
RAG_OPENAI_API_BASE_URL=http://litellm:4000/v1            # → POSTs to /v1/embeddings
RAG_EXTERNAL_RERANKER_URL=http://litellm:4000/v1/rerank   # ← MUST include /v1/rerank
```

## 8. ChromaDB vector_db storage growth

Open WebUI's default vector backend is ChromaDB (SQLite). Growth math for BGE-M3 embeddings (1024-dim fp32) at Open WebUI defaults (chunk_size=512, overlap=64):

```
Per chunk:  ~4 KB embedding + ~3-4 KB HNSW index + ~1 KB chunk text + metadata
            ≈ 10-12 KB total
≈ 1.4 × source PDF size, indexed.
```

For a 9 MB source PDF (~600 chunks): ~13 MB in `/data/vector_db`. Acceptable up to a few hundred MB. Past 1 GB consider switching to pgvector with `halfvec` (50% storage reduction) via `VECTOR_DB=pgvector`. Past 10 GB, evaluate a dedicated vector DB.

## 9. LiteLLM model_list — do not request features TEI does not honour

Common mistake: copying full OpenAI embedding entries (`encoding_format`, `dimensions`, etc.) for TEI-backed models. TEI does not honour OpenAI's `dimensions` parameter (no Matryoshka support in BGE-M3). Stick to the minimum-viable spec.

```yaml
- model_name: BAAI/bge-m3
  litellm_params:
    model: openai/BAAI/bge-m3
    api_base: http://tei:8080/v1
    api_key: dummy
    encoding_format: float       # ← only the load-bearing field
  model_info:
    max_input_tokens: 8192
    output_vector_size: 1024
    mode: embedding
```
