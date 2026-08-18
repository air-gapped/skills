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

## 2026-08-11 freshen (rebaseline v0.25.1 → v0.27.0)

Two minors of drift (v0.26.0 published 2026-07-27, v0.27.0 published
2026-08-10). Unlike the last two passes, this one found a **correctness**
regression rather than a validation tightening — and one long-stale claim the
release notes could never have surfaced, because the change predates the
skill's own previous baseline.

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.27.0 | <https://github.com/vllm-project/vllm/releases/tag/v0.27.0> | 2026-08-11 | new-feature | Published 2026-08-10. **All source probes in this pass were made against the `v0.27.0` tag.** |
| vLLM v0.27.1 (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.27.1> | 2026-08-11 | fresh | Published 2026-08-11 10:47Z, mid-pass. Patch release with exactly one change — "Support quantized DSpark Markov heads" (#50424) — which touches no pooling, rerank, STT or OCR surface, so the v0.27.0 probes above stand. The `v0.27.1` container images were pushed 10:24-10:42Z, *before* the 10:47Z release — image availability, not the PyPI wheel, gates this stack. Not restamped onto individual claims, because it was not probed. |
| vLLM v0.26.0 | <https://github.com/vllm-project/vllm/releases/tag/v0.26.0> | 2026-08-11 | new-feature | Published 2026-07-27. |
| PR #48901 — wrong pooling scores under chunked prefill + `torch.compile` | <https://github.com/vllm-project/vllm/pull/48901> | 2026-08-11 | **broken / correctness** | Merged 2026-07-17, v0.26.0. Fixes #48831. LAST-pooling models (PR names `Qwen/Qwen3-Reranker-0.6B`) returned wrong scores when a query+doc pair was chunk-prefilled, *only* under `torch.compile`. Repro: ~0.83 unchunked → ~0.01–0.36 chunked, varying run-to-run. `--enforce-eager` always correct; offline batch path happened not to chunk. Buffer-lifetime race in the compiled forward — cosine ~0.47 vs eager, no NaN/zeros, so the wrong value is *plausible*. **Invalidates past results, not just future ones.** Applied to SKILL.md pitfall 5 + new baseline section, reranking.md §2, embedding.md §7. |
| `--task` flag absent from the CLI | v0.27.0 `vllm/engine/arg_utils.py`, `vllm/config/model.py`, `docs/models/pooling_models/README.md` | 2026-08-11 | **deprecation → removed** | Source probe, not a release note. No `task` field in `ModelConfig` and no `--task` in `arg_utils.py` at v0.22.0, v0.25.1 **or** v0.27.0; the pooling doc documents only `--runner`/`--convert`. The skill had claimed since v0.20.0 that `--task` "still works with a warning" — that was already stale at its own previous baseline. Applied to SKILL.md mental model + pitfall 1, runner-flags.md §1/§3/§7. |
| `score` / `encode` pooling task names | v0.27.0 `vllm/tasks.py` | 2026-08-11 | **deprecation → removed** | `check_removed_pooling_task` raises `VLLMValidationError` naming the replacement (`classify`; `token_embed`/`token_classify`). Previously described as "deprecated". Applied to runner-flags.md §3/§7. |
| MRV2 pooling series — #49331, #48791, #50293, #50574, #50661 | <https://github.com/vllm-project/vllm/pull/50661> | 2026-08-11 | new-feature | v0.26.0–v0.27.0. #50661 completes encoder-only pooling for every in-tree task. Before it, BGE-M3 **failed to start** on V2 (`get_pooling_task()` ranks `embed&token_classify` first, then the runner rejected it). Applied to runner-flags.md §11. |
| PR #48290 — enable MRV2 for pooling by default | <https://github.com/vllm-project/vllm/pull/48290> | 2026-08-11 | **fresh (still OPEN)** | Not merged. Confirms pooling is *not* on MRV2 by default; corroborated by `VllmConfig._is_default_v2_model_runner_model` returning False for `runner_type != "generate"` in v0.27.0 `vllm/config/vllm.py:637-658`, and `VLLM_USE_V2_MODEL_RUNNER` defaulting to `None` in `vllm/envs.py:279`. The release-note headline "MRV2 expands to non-generative workloads" would otherwise read as a default change. |
| MRV2 token-task restriction | v0.27.0 `vllm/v1/worker/gpu/pool/pooling_runner.py:65-78` | 2026-08-11 | new-feature | `_get_enabled_tasks` subtracts `token_embed`/`token_classify` unless `attn_type == "encoder_only"`. Startup error names the escape hatch `VLLM_USE_V2_MODEL_RUNNER=0`. |
| STT entrypoint package moved | v0.27.0 `vllm/entrypoints/speech_to_text/` | 2026-08-11 | **broken (source anchors)** | `vllm/entrypoints/openai/speech_to_text/` returns 404 at v0.27.0. New layout: `base/`, `transcription/`, `translation/`, `realtime/`, `factories.py`. Every anchor in stt.md §2/§11 pointed at the dead path. Applied. |
| PR #48543 — `diarized_json` | <https://github.com/vllm-project/vllm/pull/48543> | 2026-08-11 | new-feature | Merged 2026-07-29, v0.27.0, closes #48443. Transcriptions only (translations unchanged, matching the OpenAI contract). Model-gated, fail-closed parser; `json`/`text`/`verbose_json` paths untouched. Applied to stt.md §2 + roster row. |
| PR #41131 — cumulative STT chunk timestamps | <https://github.com/vllm-project/vllm/pull/41131> | 2026-08-11 | **broken (fixed)** | Merged 2026-07-27, v0.27.0, fixes #32588. `split_audio` searches a 1 s window before the nominal 30 s cut, but offsets assumed an exact 30 s; error accumulated ~1 s/chunk (~5 s over 10 chunks). Text was always right — only timestamps drifted. `TranscriptionSegment.seek` is now `int`. Applied to stt.md §6. |
| PR #45839 — translation-API sampling params | <https://github.com/vllm-project/vllm/pull/45839> | 2026-08-11 | new-feature | Merged 2026-07-21, v0.27.0. Adds `top_p`, `top_k`, `min_p`, frequency/repetition/presence penalties and `vllm_xargs` to `/v1/audio/translations`; defaults neutral. Applied to stt.md §5. |
| PR #49403 — MOSS-TD max audio duration | <https://github.com/vllm-project/vllm/pull/49403> | 2026-08-11 | **broken (fixed)** | Merged 2026-07-25, v0.27.0. MOSS-TD treated Whisper's 30 s chunk as the whole-item maximum, reporting ~375 `max_tokens_per_mm_item`, so encoder cache fell back to `max_num_batched_tokens` and longer audio was **rejected at request time**. Now sized from MOSS-TD's real 90-minute ceiling (67,500 audio embedding tokens). Applied to stt.md roster row. |
| PR #50688 — jina-embeddings-v5-text-nano | <https://github.com/vllm-project/vllm/pull/50688> | 2026-08-11 | new-feature | Merged 2026-08-03, v0.27.0. Same `JinaEmbeddingsV5Model` architecture, dispatched on `is_decoder`: `-small` = Qwen3 decoder, `-nano` = bidirectional EuroBERT encoder with `EncoderOnlyAttention`. Applied to embedding.md §4. |
| New pooling architectures in v0.26.0 | v0.27.0 `vllm/model_executor/models/registry.py` | 2026-08-11 | new-feature | Confirmed registered: `BertForMaskedLM` (#48463), `RobertaForTokenClassification` / `XLMRobertaForTokenClassification` (#47991); LongCat-Flash-Lite n-gram embedding (#47857) from the release notes. Recorded in embedding.md footer. |
| DeepSeek-OCR recipe constants | v0.27.0 `vllm/model_executor/models/deepseek_ocr.py` | 2026-08-11 | version-drift | `NGramPerReqLogitsProcessor` still present, and `mm_processor_cache_gb` still in `vllm/config/model.py` — all three recipe flags valid. But the class reads `whitelist_token_ids`/`ngram_size`/`window_size` from per-request `extra_args` (lines 140-195); it does not hard-code them, so "enforces" overstated it. GUNDAM sizes are imported constants (`BASE_SIZE`/`IMAGE_SIZE`/`CROP_MODE`) and were not re-read upstream. Applied to ocr.md §3. |

**Ecosystem removals, none on this skill's surface:** TeleChat (#47989),
Persimmon and Fuyu (#48096) in v0.26.0; Plamo2 (#49729) and Ouro (#49786) in
v0.27.0. Also `max_num_partial_prefills` / `max_long_partial_prefills` removed
in v0.27.0 (#49244) — belongs to the scheduler surface, recorded here only
because an image bump surfaces it.

**Still not probed:** HuggingFace model cards, the Red Hat Whisper/RHAIIS blog,
the `docs.vllm.ai` pooling doc tree, and the DeepSeek-OCR recipes page — all
listed under "Non-probed references" below and unchanged in status.

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
| PR #38800 — jina-reranker-v3 | <https://github.com/vllm-project/vllm/pull/38800> | 2026-08-18 | fresh | Merged 2026-04-10; shipped v0.20.0 (Model Support section). |
| PR #38827 — `max_tokens_per_doc` in `/rerank` | <https://github.com/vllm-project/vllm/pull/38827> | 2026-08-18 | fresh | Merged 2026-04-13; shipped v0.20.0 (API section). |
| PR #34539 — Generative Scoring | <https://github.com/vllm-project/vllm/pull/34539> | 2026-08-18 | fresh | Merged 2026-03-31; shipped v0.20.0. Still flagged experimental in skill. |
| PR #39116 — ASR multi-chunk spacing fix | <https://github.com/vllm-project/vllm/pull/39116> | 2026-08-18 | version-drift | Merged 2026-04-09; shipped v0.19.1 + v0.20.0. Skill previously said "v0.18+"; updated to ≥v0.19.1. |
| PR #39592 — async scheduling OFF for pooling | <https://github.com/vllm-project/vllm/pull/39592> | 2026-08-18 | deprecation / new-default | Merged 2026-04-12; shipped v0.20.0. **Breaking** per release notes. Skill now calls this out as a landed default. |
| PR #39530 — `logit_bias/scale` → `logit_mean/sigma` | <https://github.com/vllm-project/vllm/pull/39530> | 2026-08-18 | deprecation | Merged 2026-04-13; shipped v0.20.0. **Breaking** rename; old names still accepted with warning. Skill now describes as landed. |
| Issue #15216 — Whisper OOM on 24 GB | <https://github.com/vllm-project/vllm/issues/15216> | 2026-08-18 | fresh | CLOSED, last updated 2025-10-20; referenced vLLM 0.8.0. Workaround (RedHatAI quants) still valid. |
| vLLM v0.20.0 release notes | <https://github.com/vllm-project/vllm/releases/tag/v0.20.0> | 2026-08-18 | fresh | Authoritative source for this freshen. Confirmed 5 of 6 PRs above plus Jina Embeddings v5 (PR #39575), redundant-sync pooling perf (+3.7%, PR #39113), and the `cprofile`/V0 deprecations. |

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
