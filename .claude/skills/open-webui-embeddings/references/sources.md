# Sources

Authoritative references underlying this skill. Read these when this skill is wrong.

| Topic | Reference | Last verified | Pinned |
|---|---|---|---|
| Open WebUI embed code | `backend/open_webui/retrieval/utils.py` (`generate_openai_batch_embeddings` line 677; async fan-out in `get_embedding_function` line 905, `asyncio.gather` line 963) | 2026-05-01 | open-webui v0.9.2 (commit 8dae237a0) |
| Open WebUI rerank code | `backend/open_webui/retrieval/models/external.py` (`ExternalReranker` line 14, `predict` line 27, `requests.post` line 50) | 2026-05-01 | open-webui v0.9.2 |
| Open WebUI RAG config keys | `backend/open_webui/config.py` (RAG_EMBEDDING_BATCH_SIZE line 2948, RAG_EMBEDDING_CONCURRENT_REQUESTS line 2960, RAG_RERANKING_ENGINE line 2972, RAG_EXTERNAL_RERANKER_URL line 3001) | 2026-05-01 | open-webui v0.9.2 |
| LiteLLM HF embedding handler | `litellm/llms/huggingface/embedding/transformation.py` (`HuggingFaceEmbeddingConfig` line 38) | 2026-05-01 | litellm commit 934ecdca78 |
| LiteLLM HF rerank handler | `litellm/llms/huggingface/rerank/transformation.py` | 2026-05-01 | litellm commit 934ecdca78 |
| LiteLLM `encoding_format` fix | https://github.com/BerriAI/litellm/pull/25395 — `fix(embedding): omit null encoding_format for openai requests`, MERGED 2026-04-12 | 2026-05-01 | |
| LiteLLM `encoding_format` revert | https://github.com/BerriAI/litellm/pull/25698 — `Revert "fix(embedding): omit null encoding_format..."`, MERGED 2026-04-14 (2 days after the fix) | 2026-05-01 | |
| LiteLLM `encoding_format` issue | https://github.com/BerriAI/litellm/issues/25388 — `[Bug] LiteLLM sends encoding_format: None causing Gitee AI and SiliconFlow API errors`, CLOSED 2026-04-14 | 2026-05-01 | |
| TEI HTTP routes (`/v1/embeddings`, `/rerank`, `/embed`) | `router/src/http/server.rs` (lines 1109, 287, 566) | 2026-05-01 | text-embeddings-inference commit 5bc4d88 |
| TEI CLI defaults | `router/src/main.rs` (`max_concurrent_requests` default 512 line 60; `max_client_batch_size` default 32 line 82) | 2026-05-01 | text-embeddings-inference commit 5bc4d88 |
| BGE-Reranker-v2-m3 trained max_length=1024 | https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9 — maintainer Shitao: "max length of this model is 8192, ... we fine-tune this model with a max length of 1024, so we recommend to set max_length=1024" | 2026-05-01 | |

Run `/skill-improver freshen open-webui-embeddings` to re-probe these refs and bump `Last verified:` dates.
