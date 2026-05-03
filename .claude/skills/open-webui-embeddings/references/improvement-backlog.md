# Improvement backlog

Carries open quality findings across `/skill-improver` runs. Items here are ceiling-hit issues that either require multi-file restructure, mode switching, or author judgment — not single-iteration `improve` mutations.

## Open

(none)

## Resolved this pass

2026-05-01 — Freshen pass (pass 3). All 11 sources verified against fresh local clones (open-webui v0.9.2, litellm @934ecdca78, text-embeddings-inference @5bc4d88) plus `gh` CLI for PR/issue state plus WebFetch for HF discussion.

- **Dim 9 cap lifted: 6 → 9–10** — `references/sources.md` now carries `Last verified: 2026-05-01` and `Pinned: <version-or-commit>` on every row. Per rubric staleness rule, Dim 9 is no longer capped.
- **Open WebUI line numbers updated** (single version-drift finding, multi-site fix):
  - `SKILL.md:32` — `utils.py:560-639` → `utils.py:677` (`generate_openai_batch_embeddings`)
  - `SKILL.md:44` — `utils.py:858-913` → `utils.py:905` + `asyncio.gather` at `utils.py:963` (stabilised by adding the function name `get_embedding_function`, which resists future drift better than line ranges alone)
  - `SKILL.md:48` — `external.py:38-79` → `external.py:14` (`ExternalReranker`, `predict` at line 27)
  - `gotchas.md:117` — `utils.py:584` → `utils.py:698`; `external.py:49` → `external.py:50`
- **Verified fresh, no content change needed:**
  - LiteLLM PR #25395 (encoding_format fix, MERGED 2026-04-12) — title and merge date confirmed via `gh pr view`
  - LiteLLM PR #25698 (revert, MERGED 2026-04-14) — confirmed; the "2 days later" claim in the skill is accurate (4-12 → 4-14)
  - LiteLLM Issue #25388 (CLOSED 2026-04-14) — title confirms the GiteeAI/SiliconFlow co-impact
  - LiteLLM HF embedding/rerank `transformation.py` files exist at the documented paths
  - TEI `--max-client-batch-size=32` and `--max-concurrent-requests=512` defaults confirmed in `router/src/main.rs`
  - TEI routes `/v1/embeddings`, `/rerank`, `/embed` all present in `router/src/http/server.rs`
  - HF disc #9 (BAAI/bge-reranker-v2-m3) — maintainer Shitao confirms "max length 8192, fine-tuned at 1024, recommend max_length=1024" — exactly as the skill claims
- **`Pinned:` versions/commits added** to every source-tree ref so future freshens can compute drift since this pass.

Pass 1 (2026-05-01, single-iter restructure) and Pass 2 (2026-05-01, 5-iter improve loop, blind 90/100) — see git history if tracked.
