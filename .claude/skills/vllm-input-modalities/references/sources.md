# External references — verification audit

Log of external citations probed during skill freshen passes. Each row
records when the reference was last verified and its classification:

- **fresh** — still valid, matches claim in skill.
- **version-drift** — reference moved forward but claim still holds with
  minor gloss (e.g. "scheduled" → "landed").
- **deprecation** — replaced by newer API; skill updated to reflect.
- **new-feature** — added since previous freshen; incorporated.
- **broken** — 404 / moved / unreachable; skill updated with replacement
  or "unverifiable" note.
- **unverifiable** — reachable but couldn't confirm the claim.

## 2026-04-24 freshen (against vLLM v0.20.0 released 2026-04-23)

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| PR #38800 — jina-reranker-v3 | <https://github.com/vllm-project/vllm/pull/38800> | 2026-04-24 | fresh | Merged 2026-04-10; shipped v0.20.0 (Model Support section). |
| PR #38827 — `max_tokens_per_doc` in `/rerank` | <https://github.com/vllm-project/vllm/pull/38827> | 2026-04-24 | fresh | Merged 2026-04-13; shipped v0.20.0 (API section). |
| PR #34539 — Generative Scoring | <https://github.com/vllm-project/vllm/pull/34539> | 2026-04-24 | fresh | Merged 2026-03-31; shipped v0.20.0. Still flagged experimental in skill. |
| PR #39116 — ASR multi-chunk spacing fix | <https://github.com/vllm-project/vllm/pull/39116> | 2026-04-24 | version-drift | Merged 2026-04-09; shipped v0.19.1 + v0.20.0. Skill previously said "v0.18+"; updated to ≥v0.19.1. |
| PR #39592 — async scheduling OFF for pooling | <https://github.com/vllm-project/vllm/pull/39592> | 2026-04-24 | deprecation / new-default | Merged 2026-04-12; shipped v0.20.0. **Breaking** per release notes. Skill now calls this out as a landed default. |
| PR #39530 — `logit_bias/scale` → `logit_mean/sigma` | <https://github.com/vllm-project/vllm/pull/39530> | 2026-04-24 | deprecation | Merged 2026-04-13; shipped v0.20.0. **Breaking** rename; old names still accepted with warning. Skill now describes as landed. |
| Issue #15216 — Whisper OOM on 24 GB | <https://github.com/vllm-project/vllm/issues/15216> | 2026-04-24 | fresh | CLOSED, last updated 2025-10-20; referenced vLLM 0.8.0. Workaround (RedHatAI quants) still valid. |
| vLLM v0.20.0 release notes | <https://github.com/vllm-project/vllm/releases/tag/v0.20.0> | 2026-04-24 | fresh | Authoritative source for this freshen. Confirmed 5 of 6 PRs above plus Jina Embeddings v5 (PR #39575), redundant-sync pooling perf (+3.7%, PR #39113), and the `cprofile`/V0 deprecations. |

## Derived updates applied

- SKILL.md "Scheduled deprecations to plan for (v0.20)" → rewritten as
  "Landed in v0.20.0 (released 2026-04-23)" with breaking-change callouts
  and two new perf wins (#38559 mean-pool +5.9%, #39113 redundant-sync
  +3.7%).
- references/runner-flags.md §3 retitled "landed in v0.20.0"; §10 PR
  dates corrected (PRs merged 2026-03 through 2026-04, not 2025-11/12 or
  2026-01/02 as previously labelled). Added #39113.
- references/reranking.md §8 updated with merge dates + breaking-change
  note on #39530.
- references/stt.md §6 updated: #39116 is in v0.19.1 + v0.20.0 (not v0.18+).
- references/embedding.md §4 Jina v5 marked as landed via PR #39575 in
  v0.20.0.
- references/ocr.md: DeepSeek-OCR recipe unchanged; no v0.20.0 landing
  touches this flow.
- scripts/probe-endpoint.sh: unchanged — endpoints and probe semantics
  did not move in v0.20.0.

## Non-probed references (lower-signal, trusted on-file)

These remain unverified in this pass but are unlikely to have drifted:

- Red Hat Whisper + RHAIIS blog (2025-06-10, 2026-03-06 — referenced in stt.md).
- `docs.vllm.ai/projects/recipes` DeepSeek-OCR page (referenced in ocr.md).
- `docs.vllm.ai/en/stable/models/pooling_models/` doc tree.
- HuggingFace model cards (BGE-M3, Jina v3/v4/v5, Qwen3-Embedding, Qwen3-Reranker, ColPali, Whisper-large-v3-turbo, DeepSeek-OCR, RedHatAI quants).

Next freshen triggers: v0.21+ release, new Jina embeddings major, or a
new native-multimodal reranker shipping.
