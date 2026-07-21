# Sources

Authoritative references underlying this skill. Read these when this skill is wrong.

> **Version note (re-probed 2026-07-21).** Upstream open-webui has moved
> **v0.9.5 → v0.10.2** (2026-07-01; v0.9.6, v0.10.0, v0.10.1 in between), and the
> line numbers below have been **re-resolved against the v0.10.2 tag** rather than
> carried forward. They drifted a long way — `generate_openai_batch_embeddings`
> 677→845, `get_embedding_function` 905→1073, and every `config.py` key moved by
> roughly *two thousand* lines (2948→994 etc.), which means `config.py` was
> restructured, not merely appended to. Re-resolve by symbol name, never by
> remembered line number. LiteLLM PRs 25395/25698 and issue 25388 re-confirmed in
> the same states; TEI is unchanged at v1.9.3 with its two CLI defaults still on
> lines 60 and 82.

| Topic | Reference | Last verified | Pinned |
|---|---|---|---|
| Open WebUI embed code | `backend/open_webui/retrieval/utils.py` (`generate_openai_batch_embeddings` line 845; async fan-out in `get_embedding_function` line 1073, `asyncio.gather` line 1138) | 2026-07-21 | re-resolved at open-webui **v0.10.2**; file now 1738 lines |
| Open WebUI rerank code | `backend/open_webui/retrieval/models/external.py` (`ExternalReranker` line 13, `predict` line 26, `requests.post` line 49) | 2026-07-21 | open-webui **v0.10.2**; file barely changed (69 lines) — still synchronous `requests.post`, not httpx |
| Open WebUI RAG config keys | `backend/open_webui/config.py` (RAG_EMBEDDING_BATCH_SIZE line 994, RAG_EMBEDDING_CONCURRENT_REQUESTS line 1000, RAG_RERANKING_ENGINE line 1008, RAG_EXTERNAL_RERANKER_URL line 1023) | 2026-07-21 | open-webui **v0.10.2**. Defaults unchanged: CONCURRENT_REQUESTS still `0`, RERANKING_ENGINE and EXTERNAL_RERANKER_URL still empty strings |
| LiteLLM HF embedding handler | `litellm/llms/huggingface/embedding/transformation.py` (`HuggingFaceEmbeddingConfig` line 38) | 2026-05-28 | litellm commit 934ecdca78 |
| LiteLLM HF rerank handler | `litellm/llms/huggingface/rerank/transformation.py` | 2026-05-28 | litellm commit 934ecdca78 |
| LiteLLM `encoding_format` fix | https://github.com/BerriAI/litellm/pull/25395 — `fix(embedding): omit null encoding_format for openai requests`, MERGED 2026-04-12 | 2026-07-21 | PR 25395 |
| LiteLLM `encoding_format` revert | https://github.com/BerriAI/litellm/pull/25698 — `Revert "fix(embedding): omit null encoding_format..."`, MERGED 2026-04-14 (2 days after the fix) | 2026-07-21 | **revert still stands** |
| LiteLLM `encoding_format` issue | https://github.com/BerriAI/litellm/issues/25388 — `[Bug] LiteLLM sends encoding_format: None causing Gitee AI and SiliconFlow API errors`, CLOSED 2026-04-14 | 2026-07-21 | issue 25388 |
| TEI HTTP routes (`/v1/embeddings`, `/rerank`, `/embed`) | `router/src/http/server.rs` (lines 1109, 287, 566) | 2026-07-21 | TEI **still v1.9.3** (2026-03-23) — no release in ~4 months |
| TEI CLI defaults | `router/src/main.rs` (`max_concurrent_requests` default 512 line 60; `max_client_batch_size` default 32 line 82) | 2026-07-21 | re-resolved at tag **v1.9.3**: both still on lines 60 and 82, exactly as claimed |
| TEI Blackwell image tags (`100-1.9`, `120-1.9`, `121-1.9`) | https://github.com/huggingface/text-embeddings-inference#docker-images — README image-tag table | 2026-05-28 | TEI README @ main — not re-probed 2026-07-21 |
| BGE-Reranker-v2-m3 trained max_length=1024 | https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9 — maintainer Shitao: "max length of this model is 8192, ... we fine-tune this model with a max length of 1024, so we recommend to set max_length=1024" | 2026-05-01 | discussion 9 (HF, not re-probed this pass) |

**The `encoding_format: None` gotcha is still live (checked 2026-07-21).** The
revert (25698) has not been re-reverted and no general fix has merged. PR
**#24277** — `fix(openai): filter None values from embedding optional_params` —
is **still open**, so the per-model `encoding_format` pin this skill recommends
remains necessary, not merely defensive. Watch #24277 as the tell for when it
can be dropped.

Run `/skill-improver freshen open-webui-embeddings` to re-probe these refs and bump `Last verified:` dates.
