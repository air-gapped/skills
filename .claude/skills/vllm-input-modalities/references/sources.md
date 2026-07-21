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

## 2026-07-21 freshen (rebaseline v0.21.0 → v0.25.1)

Four minors of drift. Probed every release body v0.22.0 → v0.25.1 for the
pooling / embedding / rerank / STT / OCR surface, then read the PRs behind
each hit. **The runner surface did not move** — no `--runner` / `--convert` /
`PoolerConfig` change since v0.20.0 — but two request-validation tightenings
in v0.24.0 convert previously-successful requests into errors.

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.25.1 (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.25.1> | 2026-07-21 | new-feature | Published 2026-07-14. New baseline. Patch release, 19-line body, nothing on this skill's surface. |
| vLLM v0.22.0 → v0.25.0 | <https://github.com/vllm-project/vllm/releases> | 2026-07-21 | new-feature | v0.22.0 (2026-05-29), v0.23.0 (2026-06-15), v0.24.0 (2026-06-29), v0.25.0 (2026-07-11). |
| PR #46313 — matryoshka upper bound | <https://github.com/vllm-project/vllm/pull/46313> | 2026-07-21 | **deprecation / breaking** | Merged 2026-06-22, v0.24.0. `PoolingParams._set_default_parameters` checked only `dimensions >= 1` for MRL models lacking an explicit list, then sliced `[..., :d]` — oversized values **silently returned a `hidden_size`-length vector**. Now raises. Mirrors sglang `_validate_for_matryoshka_dim`. Applied to SKILL.md + embedding.md §3. |
| PR #46119 — rerank `top_n` validation | <https://github.com/vllm-project/vllm/pull/46119> | 2026-07-21 | **deprecation / breaking** | Merged 2026-06-22, v0.24.0. `top_n=-1` was silently treated as `0`. `top_n=0` still means "all"; oversized values still accepted. Applied to reranking.md. |
| PR #45173 — `/v1/embeddings` messages + `chat_template_kwargs` | <https://github.com/vllm-project/vllm/pull/45173> | 2026-07-21 | new-feature | Merged 2026-06-15, v0.24.0. Message-shaped input to `/v1/embeddings` was previously **rejected at validation**, and `chat_template_kwargs` never reached the renderer; only the top-level messages extension worked. This is now the supported path for instruction-style embedders. Applied to embedding.md §1. |
| PR #43260 — truncation side | <https://github.com/vllm-project/vllm/pull/43260> | 2026-07-21 | **unverifiable → refuted** | Merged 2026-05-22, v0.22.0. The release note reads "truncation side for OpenAI endpoints", which invites the assumption that `/v1/embeddings` gained `truncation_side`. The PR body scopes it to `/v1/completions` and `/v1/chat/completions` only. Recorded in SKILL.md as explicitly **not** applicable. |
| PR #42370 / #42274 — STT entrypoint + test consolidation | <https://github.com/vllm-project/vllm/pull/42370> | 2026-07-21 | fresh | Merged 2026-05-12 / 2026-05-11, v0.22.0. Internal refactor following #41907. No endpoint or request-body change — `/v1/audio/transcriptions` and `/v1/audio/translations` are untouched. |
| PR #46564 — Unlimited OCR | <https://github.com/vllm-project/vllm/pull/46564> | 2026-07-21 | new-feature | Merged 2026-06-28, v0.25.0. `baidu/Unlimited-OCR`, benchmarked on OmniDocBench; Triton R-SWA backend in #47102. Added to ocr.md §2. |
| PR #47729 — MOSS-Transcribe-Diarize | <https://github.com/vllm-project/vllm/pull/47729> | 2026-07-21 | new-feature | Merged 2026-07-08, v0.25.0. `OpenMOSS-Team/MOSS-Transcribe-Diarize` — long-form transcription with timestamped speaker labels; Whisper-style encoder into a Qwen3 causal decoder. First diarizing model in the roster. Added to stt.md. |
| PR #47071 — pooled Whisper sliding-window KV sizing | <https://github.com/vllm-project/vllm/pull/47071> | 2026-07-21 | fresh (bugfix) | Merged 2026-07-01, v0.25.0. Voxtral Realtime's causal Whisper encoder expressed `SlidingWindowSpec.sliding_window` in encoder-token units while the pool used `block_pool_size` tokens per block, so the KV manager over-reserved encoder blocks by ~`block_pool_size`×. Memory-sizing fix only. |
| PR #46762 — realtime embeddings on MRv2 | <https://github.com/vllm-project/vllm/pull/46762> | 2026-07-21 | new-feature | Merged 2026-06-27, v0.25.0. Realtime models (Voxtral) need embeddings during decode too. |

**Ecosystem removals noted, none on this skill's surface:** PagedAttention
removed entirely in v0.25.0 (#47361); Transformers v4 support deprecated in
v0.24.0 (#45161); model families removed across v0.24.0/v0.25.0 (ERNIE,
Xverse, Dots1, Bamba, Mono-InternVL, Baichuan, Aquila, Grok, Tarsier/Tarsier2,
AyaVision/MusicFlamingo, Mantis). No pooling, rerank, STT or OCR model was
removed — recorded in SKILL.md because an operator bumping the image for an
unrelated reason can still be stranded.

**Still not probed this pass:** the HuggingFace model cards, the Red Hat
Whisper/RHAIIS blog, and the `docs.vllm.ai` pooling doc tree (all listed under
"Non-probed references" below and unchanged in status).

## 2026-05-28 freshen (rebaseline v0.20.0 → v0.21.0)

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.21.0 release notes (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.21.0> | 2026-05-28 | new-feature | Published 2026-05-15. Current baseline. No runner/`--convert`/`PoolerConfig` breaking change vs v0.20.0; pooling deltas perf-only (#41163 AllPool +51%, #41433 GPU↔CPU sync elimination). New OCR arch Qianfan-OCR (#40136). |
| vLLM v0.20.0 release tag (date correction) | <https://github.com/vllm-project/vllm/releases/tag/v0.20.0> | 2026-05-28 | version-drift | `published_at` is 2026-04-27 (not 2026-04-23 as previously stated). Corrected across SKILL.md + 4 reference files. |
| vLLM v0.20.1 / v0.20.2 patch releases | <https://github.com/vllm-project/vllm/releases> | 2026-05-28 | new-feature | v0.20.1 (2026-05-04), v0.20.2 (2026-05-10) — patch releases between v0.20.0 and v0.21.0; no pooling/STT/OCR surface change. |
| PR #41163 — AllPool.forward +51% | <https://github.com/vllm-project/vllm/pull/41163> | 2026-05-28 | new-feature | Pooling perf win, shipped v0.21.0. Token-wise / `ALL` pooling (ColBERT, Jina-v4 multi-vector). |
| PR #41433 — pooling GPU↔CPU sync elimination | <https://github.com/vllm-project/vllm/pull/41433> | 2026-05-28 | new-feature | Pooling perf win, shipped v0.21.0. |
| PR #40136 — Qianfan-OCR | <https://github.com/vllm-project/vllm/pull/40136> | 2026-05-28 | new-feature | New OCR architecture, shipped v0.21.0. Added to ocr.md §2 roster. |

Note: probes for the v0.21.0 rebaseline were performed during the recon
stage of this freshen pass (gh api against vllm-project/vllm releases,
2026-05-28). Internal-contradiction fixes applied this pass
(`max_tokens_per_doc` "late 2025" → v0.20.0/#38827; async-scheduling
"2026-01" → 2026-04-12; logit rename "late 2025" → v0.20.0/#39530) were
verified against the skill's own dated rows below, not online.

## 2026-04-24 freshen (against vLLM v0.20.0 released 2026-04-27)

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
  "Landed in v0.20.0 (released 2026-04-27)" with breaking-change callouts
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
