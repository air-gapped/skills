# Sources

Freshened: 2026-09-22 — every row probed against Open WebUI v0.11.4 (2026-09-21). One long-standing content error corrected: `Qwen3Model`/`Qwen3ForCausalLM` are NOT in vLLM's `_EMBEDDING_MODELS`; Qwen3-Embedding runs through generic `--convert embed` auto-conversion, which happens to be right only because that model wants last-token pooling. TEI shipped v1.9.4 on 2026-09-15, ending the "no release in ~4 months" note. **v0.11.4's bundled-model removal does not reach this skill**: it is scoped to the new opt-in slim image, and the standard image still bakes in `all-MiniLM-L6-v2` with `sentence-transformers` in `requirements.txt`.

Authoritative references underlying this skill. Read these when this skill is wrong.

> **Version note (re-probed 2026-09-15).** Upstream open-webui is now at
> **v0.11.3** (2026-08-31), three patches past v0.11.0. Line numbers below are
> re-resolved against the v0.11.3 tag: `generate_openai_batch_embeddings`
> 677→845 (0.10.2)→862 (0.11.0)→**882**, `get_embedding_function`
> 905→1073 (0.10.2)→1090 (0.11.0)→**1098** (its `asyncio.gather` fan-out at
> **1163**), and the four RAG config keys moved again to **1013 / 1019 / 1027 /
> 1042**. Every default and behaviour re-confirmed unchanged — only positions
> moved, which is the third consecutive release to do so.
> Historically at v0.11.0: `generate_openai_batch_embeddings` 862,
> `get_embedding_function` 1090, `ExternalReranker` class
> at **13** with `predict` at **26** (the previously-cited 14/27 were off by one
> and pointed at `__init__`). Re-resolve by symbol name, never by remembered
> line number — `config.py` was restructured wholesale (not appended to) between
> 0.9.x and 0.10.2, moving keys by ~2000 lines.
>
> **Behaviour re-verified unchanged on 0.11.0:** embed URL auto-append
> (`f'{url}/embeddings'`), payload `{input, model}`, parse
> `data['data'][i]['embedding']`; rerank exact-URL (no append), Cohere body
> `{model, query, documents, top_n}` where `top_n` is always `len(documents)`,
> parse `data['results']` → `relevance_score`, and the silent `return None`
> fallback on both non-2xx and missing-`results`. Env defaults unchanged:
> `RAG_EMBEDDING_BATCH_SIZE` 1 (legacy alias `RAG_EMBEDDING_OPENAI_BATCH_SIZE`
> still honoured, `config.py:1001-1002`), `RAG_EMBEDDING_CONCURRENT_REQUESTS` 0.
> 0.11.0's retrieval churn (+462/−248) is almost entirely in `retrieval/web/`.
> One adjacent change matters: `Knowledges.get_file_metadatas_by_id` became a
> column-only SELECT excluding `File.data` (`models/knowledge.py:684-694`).
>
> **NOT re-probed this pass:** LiteLLM PRs 25395/25698, issue 25388, and the TEI
> v1.9.3 CLI-default line numbers all still carry their 2026-07-21 states.

| Topic | Reference | Last verified | Pinned |
|---|---|---|---|
| Open WebUI embed code | `backend/open_webui/retrieval/utils.py` (`generate_openai_batch_embeddings` line 845; async fan-out in `get_embedding_function` line 1073, `asyncio.gather` line 1138) | 2026-09-15 | re-resolved at open-webui **v0.10.2**; file now 1738 lines |
| Open WebUI rerank code | `backend/open_webui/retrieval/models/external.py` (`ExternalReranker` line 13, `predict` line 26, `requests.post` line 49) | 2026-09-15 | open-webui **v0.10.2**; file barely changed (69 lines) — still synchronous `requests.post`, not httpx |
| Open WebUI RAG config keys | `backend/open_webui/config.py` (RAG_EMBEDDING_BATCH_SIZE line 994, RAG_EMBEDDING_CONCURRENT_REQUESTS line 1000, RAG_RERANKING_ENGINE line 1008, RAG_EXTERNAL_RERANKER_URL line 1023) | 2026-09-15 | open-webui **v0.10.2**. Defaults unchanged: CONCURRENT_REQUESTS still `0`, RERANKING_ENGINE and EXTERNAL_RERANKER_URL still empty strings |
| LiteLLM HF embedding handler | `litellm/llms/huggingface/embedding/transformation.py` (`HuggingFaceEmbeddingConfig` line 38) | 2026-08-18 (paths confirmed on litellm default branch `litellm_internal_staging`, local clone) | litellm commit 934ecdca78 |
| LiteLLM HF rerank handler | `litellm/llms/huggingface/rerank/transformation.py` | 2026-08-18 (paths confirmed on litellm default branch `litellm_internal_staging`, local clone) | litellm commit 934ecdca78 |
| LiteLLM `encoding_format` fix | https://github.com/BerriAI/litellm/pull/25395 — `fix(embedding): omit null encoding_format for openai requests`, MERGED 2026-04-12 | 2026-09-15 | PR 25395 |
| LiteLLM `encoding_format` revert | https://github.com/BerriAI/litellm/pull/25698 — `Revert "fix(embedding): omit null encoding_format..."`, MERGED 2026-04-14 (2 days after the fix) | 2026-09-15 | **revert still stands** |
| LiteLLM `encoding_format` issue | https://github.com/BerriAI/litellm/issues/25388 — `[Bug] LiteLLM sends encoding_format: None causing Gitee AI and SiliconFlow API errors`, CLOSED 2026-04-14 | 2026-09-15 | issue 25388 |
| TEI HTTP routes (`/v1/embeddings`, `/rerank`, `/embed`) | `router/src/http/server.rs` (lines 1109, 287, 566) | 2026-09-15 | TEI **still v1.9.3** (2026-03-23) — no release in ~4 months |
| TEI CLI defaults | `router/src/main.rs` (`max_concurrent_requests` default 512 line 60; `max_client_batch_size` default 32 line 82) | 2026-09-15 | re-resolved at tag **v1.9.3**: both still on lines 60 and 82, exactly as claimed |
| TEI Blackwell image tags (`100-1.9`, `120-1.9`, `121-1.9`) | https://github.com/huggingface/text-embeddings-inference#docker-images — README image-tag table | 2026-08-18 | TEI README @ main — not re-probed 2026-07-21 |
| BGE-Reranker-v2-m3 trained max_length=1024 | https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9 — maintainer Shitao: "max length of this model is 8192, ... we fine-tune this model with a max length of 1024, so we recommend to set max_length=1024" | 2026-08-18 | discussion 9 (HF, not re-probed this pass) |
| Slim image cuts local embedding/reranking models | https://github.com/open-webui/open-webui/commit/cb942bb94c8dc7941336088fb3392e2398ff56c1 — `Dockerfile`, `backend/requirements-slim.txt`, `backend/open_webui/routers/retrieval.py` (`USE_SLIM` guards at lines 155, 192, 540, 966, 1650) | 2026-09-24 | v0.11.4 |
| pgvector multi-KB recall + connection-leak fix | https://github.com/open-webui/open-webui/pull/30142 — `retrieval/vector/dbs/pgvector.py`, adds `PGVECTOR_ITERATIVE_SCAN` (`config.py:744-746`) | 2026-09-24 | v0.11.4 |
| pgvector index-built-too-early fix | https://github.com/open-webui/open-webui/pull/30143 — `retrieval/vector/dbs/pgvector.py` `_index_is_ready`/min_training_rows deferral | 2026-09-24 | v0.11.4 |
| Knowledge folder deletion leaves stale index/blobs | https://github.com/open-webui/open-webui/commit/17dbc6f001aeea25ae1df528cb79bb272eca4a77 — `models/knowledge.py`, `routers/knowledge.py` | 2026-09-24 | v0.11.4 |
| Docling failure/skip now fails the upload | https://github.com/open-webui/open-webui/pull/30107 — `retrieval/loaders/main.py:296-301` | 2026-09-24 | v0.11.4 |
| ftfy no longer partially rewrites extracted text | https://github.com/open-webui/open-webui/commit/1bfa59acb — `retrieval/loaders/main.py`, `ftfy.fix_text(..., unescape_html=False)` | 2026-09-24 | v0.11.4 |
| Duplicate vector-search tracebacks per outage | https://github.com/open-webui/open-webui/pull/29981 | 2026-09-24 | v0.11.4 |
| `RAG_SOURCE_METADATA_KEYS` custom file metadata | https://github.com/open-webui/open-webui/pull/29499 — `backend/open_webui/env.py:375`, `retrieval/utils.py:1367` | 2026-09-24 | v0.11.4 |
| `RAG_METADATA_MAX_VALUE_CHARS` / `ENABLE_KNOWLEDGE_FILE_RETENTION` | https://github.com/open-webui/open-webui/commit/278e97589e71d119b887d5bca9d6ae32912d1dff ; `backend/open_webui/config.py:985`, `env.py:844-846` | 2026-09-24 | v0.11.1 |

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

**The `encoding_format: None` gotcha is still live (checked 2026-09-15).** The
revert (25698) has not been re-reverted and no general fix has merged, so the
per-model `encoding_format` pin this skill recommends remains necessary, not
merely defensive.

**Do not watch #24277 — it is dead.** The stale bot closed it 2026-08-10
(`closed_by: github-actions[bot]`, label `stale`, `merged: false`). It was
never merged, so its closure is not the signal this file said to wait for, and
the pin must not be dropped on the strength of it. There is no known
replacement PR to watch; re-derive one on the next pass rather than inheriting
a dead tell.

Run `/skill-improver freshen open-webui-embeddings` to re-probe these refs and bump `Last verified:` dates.
