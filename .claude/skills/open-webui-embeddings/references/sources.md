# Sources

Freshened: 2026-10-27 — every row probed against Open WebUI v0.12.4, TEI v1.9.4, LiteLLM v1.106.4 and vLLM v0.32.0.

Authoritative references underlying this skill. Read these when this skill is wrong.

> **Version note.** Line numbers below are resolved at open-webui **v0.12.4**
> (2026-10-25). They have moved on every release since 0.9.x — re-resolve by
> symbol name, never by remembered line number. Behaviour re-read at v0.12.4 and
> unchanged: embed URL auto-append (`f'{url}/embeddings'`), payload
> `{input, model}`, parse `data['data'][i]['embedding']`; rerank exact-URL,
> Cohere body `{model, query, documents, top_n=len(documents)}`, parse
> `data['results']` → `relevance_score`, `return None` on non-2xx and on missing
> `results`. Env defaults unchanged: `RAG_EMBEDDING_BATCH_SIZE` 1 (legacy alias
> `RAG_EMBEDDING_OPENAI_BATCH_SIZE`), `RAG_EMBEDDING_CONCURRENT_REQUESTS` 0,
> reranker keys empty strings. `PersistentConfig` no longer exists (absent at
> v0.11.4 and v0.12.4); persisted settings are the `DEFAULT_CONFIG` dict, seeded
> into the DB by `Config.seed_defaults` (insert-if-missing).

| Topic | Reference | Last verified | Pinned |
|---|---|---|---|
| Open WebUI embed code | `backend/open_webui/retrieval/utils.py` (`generate_openai_batch_embeddings` line 891, async `agenerate_openai_batch_embeddings` line 921; `get_embedding_function` line 1107, semaphore line 1164, `asyncio.gather` line 1173; mode-A prepend in `generate_embeddings` line 1212) | 2026-10-27 | open-webui **v0.12.4**; file 1882 lines |
| Open WebUI rerank code | `backend/open_webui/retrieval/models/external.py` (`ExternalReranker` line 13, `predict` line 26, `requests.post` line 49) | 2026-10-27 | open-webui **v0.12.4**; 69 lines, still synchronous `requests.post` |
| Open WebUI RAG config keys | `backend/open_webui/config.py` (RAG_EMBEDDING_BATCH_SIZE line 1026, RAG_EMBEDDING_CONCURRENT_REQUESTS line 1032, prefix trio lines 1034-1038, RAG_RERANKING_ENGINE line 1040, RAG_EXTERNAL_RERANKER_URL line 1055; `DEFAULT_CONFIG` line 2917) | 2026-10-27 | open-webui **v0.12.4**. Defaults unchanged |
| LiteLLM HF embedding handler | `litellm/llms/huggingface/embedding/transformation.py` (`HuggingFaceEmbeddingConfig` line 50) | 2026-10-27 (default branch is now `main`) | litellm `main`; latest release v1.106.4 |
| LiteLLM HF rerank handler | `litellm/llms/huggingface/rerank/transformation.py` (`HuggingFaceRerankConfig` line 53, maps documents → `texts`) | 2026-10-27 (default branch `main`) | litellm `main` |
| LiteLLM `encoding_format` fix | https://github.com/BerriAI/litellm/pull/25395 — `fix(embedding): omit null encoding_format for openai requests`, MERGED 2026-04-12 | 2026-09-15 | PR 25395 |
| LiteLLM `encoding_format` revert | https://github.com/BerriAI/litellm/pull/25698 — `Revert "fix(embedding): omit null encoding_format..."`, MERGED 2026-04-14 (2 days after the fix) | 2026-09-15 | **revert still stands** |
| LiteLLM `encoding_format` issue | https://github.com/BerriAI/litellm/issues/25388 — `[Bug] LiteLLM sends encoding_format: None causing Gitee AI and SiliconFlow API errors`, CLOSED 2026-04-14 | 2026-09-15 | issue 25388 |
| LiteLLM `encoding_format` default → float | https://github.com/BerriAI/litellm/pull/26976 — `feat(embedding): default OpenAI-path encoding_format to float`, MERGED 2026-05-01 (merge `0b87bdff`). Ancestry: in v1.85.0 and v1.94.0, absent from v1.84.0/v1.84.1. Resolution order request/`litellm_params` → `LITELLM_DEFAULT_EMBEDDING_ENCODING_FORMAT` → `float` | 2026-10-27 | first release v1.85.0 |
| LiteLLM `encoding_format` omitted when unset | https://github.com/BerriAI/litellm/pull/38774 — `fix(embeddings): omit encoding_format when the client omits it on OpenAI-compatible calls`, MERGED 2026-09-01 (merge `6661e915`); in v1.101.0, absent from v1.100.0. Code at v1.106.4: `litellm/main.py` pops `encoding_format` when the resolved value is None/`"none"` | 2026-10-27 | first release v1.101.0 |
| TEI HTTP routes (`/v1/embeddings`, `/rerank`, `/embed`) | `router/src/http/server.rs` (lines 1107, 285, 564) | 2026-10-27 | TEI **v1.9.4** (2026-09-15, isLatest; the only release since v1.9.3) |
| TEI CLI defaults | `router/src/main.rs` (`max_concurrent_requests` default 512 line 60; `max_client_batch_size` default 32 line 82) | 2026-10-27 | re-resolved at tag **v1.9.4**: unchanged |
| TEI `cuda-` image arch dispatch | `cuda-all-entrypoint.sh` @ v1.9.4: 75→router-75, 80–89→router-80, 90→router-90, 100→router-100, 120→router-120, else `cuda compute cap N is not supported` + exit 1 | 2026-10-27 | v1.9.4 |
| TEI image tags (`turing-1.9` exp., `1.9` for A100, `86-1.9`, `89-1.9`, `hopper-1.9`, `100/120/121-1.9` exp.) | https://github.com/huggingface/text-embeddings-inference#docker-images — README image-tag table | 2026-10-27 | TEI README @ main |
| BGE-Reranker-v2-m3 trained max_length=1024 | https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9 — maintainer Shitao: "max length of this model is 8192, ... we fine-tune this model with a max length of 1024, so we recommend to set max_length=1024" | 2026-08-18 | discussion 9 (HF, not re-probed this pass) |
| Slim image cuts local embedding/reranking models | https://github.com/open-webui/open-webui/commit/cb942bb94c8dc7941336088fb3392e2398ff56c1 — `Dockerfile`, `backend/requirements-slim.txt`, `backend/open_webui/routers/retrieval.py` (`USE_SLIM` guards at v0.12.4 lines 153, 190, 511, 939, 1289) | 2026-10-27 | first release v0.11.4 |
| pgvector multi-KB recall + connection-leak fix | https://github.com/open-webui/open-webui/pull/30142 — `retrieval/vector/dbs/pgvector.py`, adds `PGVECTOR_ITERATIVE_SCAN` (`config.py:744-746`) | 2026-09-24 | v0.11.4 |
| pgvector index-built-too-early fix | https://github.com/open-webui/open-webui/pull/30143 — `retrieval/vector/dbs/pgvector.py` `_index_is_ready`/min_training_rows deferral | 2026-09-24 | v0.11.4 |
| Knowledge folder deletion leaves stale index/blobs | https://github.com/open-webui/open-webui/commit/17dbc6f001aeea25ae1df528cb79bb272eca4a77 — `models/knowledge.py`, `routers/knowledge.py` | 2026-09-24 | v0.11.4 |
| Docling failure/skip now fails the upload | https://github.com/open-webui/open-webui/pull/30107 — `retrieval/loaders/main.py:296-301` | 2026-09-24 | v0.11.4 |
| ftfy no longer partially rewrites extracted text | https://github.com/open-webui/open-webui/commit/1bfa59acb — `retrieval/loaders/main.py`, `ftfy.fix_text(..., unescape_html=False)` | 2026-09-24 | v0.11.4 |
| Duplicate vector-search tracebacks per outage | https://github.com/open-webui/open-webui/pull/29981 | 2026-09-24 | v0.11.4 |
| `RAG_SOURCE_METADATA_KEYS` custom file metadata | https://github.com/open-webui/open-webui/pull/29499 — `backend/open_webui/env.py:375`, `retrieval/utils.py:1367` | 2026-09-24 | v0.11.4 |
| `RAG_METADATA_MAX_VALUE_CHARS` / `ENABLE_KNOWLEDGE_FILE_RETENTION` | https://github.com/open-webui/open-webui/commit/278e97589e71d119b887d5bca9d6ae32912d1dff ; `backend/open_webui/config.py:985`, `env.py:844-846` | 2026-09-24 | v0.11.1 |
| Rerank calls carry user-info headers | https://github.com/open-webui/open-webui/pull/32061 — `fix: reranker gets no user info headers in chat and knowledge search`, MERGED 2026-10-08 (merge `c04c7ddae0`, contained in v0.12.0 by ancestry); fixes issue #32060 | 2026-10-27 | v0.12.0 |
| Memory reindex honours concurrency cap + batch size | https://github.com/open-webui/open-webui/pull/32420 — `fix: memory reindex ignores the Embedding Concurrent Requests limit`, MERGED 2026-10-14; v0.12.2 notes: "where it sent one request per memory at once and rate-limited providers failed most of them with 429 errors" | 2026-10-27 | v0.12.2 |
| Dev-only `/api/v1/retrieval/ef/{text}` route removed | https://github.com/open-webui/open-webui/pull/32869 — `refactor: remove unused development route`, MERGED 2026-10-21 (merge `d1e31cbb81`). Route present at v0.12.3 (`routers/retrieval.py:2993-2995`, under `if ENV == 'dev'`), absent at v0.12.4 | 2026-10-27 | v0.12.4 |
| RAG env vars are first-boot seeds, DB wins after | open-webui v0.12.4 `config.py` `DEFAULT_CONFIG` (line 2917; `rag.embedding_*`, `rag.reranking_*`, `rag.external_reranker_*`, `rag.openai.*` at 3009-3031) → `models/config.py` `Config.seed_defaults` ("Insert keys that don't yet exist in the DB... Existing DB values take precedence", line 248) and `Config.get` (DB unless `persistent_enabled_for` is false, line 143); `routers/retrieval.py:563` passes `config['rag.embedding_batch_size']` to `get_embedding_function`; `ENABLE_PERSISTENT_CONFIG` at `config.py:3352` | 2026-10-27 | v0.12.4 |

**This file covers the open-webui / LiteLLM / TEI code and issue trail only.**
Two other reference files carry their own dated Sources tables, because they cite
a different class of fact on a different clock:

- **`references/prefix-models.md`** — `config_sentence_transformers.json` prompt
  strings, model-card FAQs, and the open-webui prefix-dispatch call sites.
- **`references/model-selection.md`** — MTEB leaderboard figures, reranker
  evaluation tables, OpenRouter catalogue and pricing, vLLM registry state.

Re-probe those there. The leaderboard and OpenRouter entries in particular are the
fastest-moving claims in the skill — MTEB shipped releases daily around
2026-08-05, and the multilingual top-10 turned over substantially in the preceding
year. Anything sourced to a leaderboard should be treated as stale after ~3 months.

**The `encoding_format: None` gotcha is fixed upstream from LiteLLM v1.85.0** (PR 26976),
and from v1.101.0 the field is omitted entirely (PR 38774). PR 24277 was stale-closed
unmerged on 2026-08-10 and is not the fix; issue 25388 was closed by the reverted
25395 and is not evidence of a fix either. The per-model pin stays in the skill as a
harmless workaround for releases below v1.85.0.

Run `/skill-improver freshen open-webui-embeddings` to re-probe these refs and rewrite the `Freshened:` stamp.
