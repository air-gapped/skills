# External references — verification audit

Freshened: 2026-09-22 — every row probed; all 34 URLs 200 and every PR placement re-derived from tag ancestry rather than merge dates. Content claims hold; the drift is in source-code line anchors, several of which were already wrong at the v0.27.0 baseline they were stamped against. One real content error found: `SequencePoolingType` is `CLS|LAST|MEAN` and `ALL`/`STEP` belong to a separate `TokenPoolingType` (`vllm/config/pooler.py`), a split that predates this skill's own baseline. New at v0.30.0 and not yet covered: torchcodec `audio_backend` in `--media-io-kwargs` (#51826) and torchaudio as the default resampler (#52598).

**Two placements were wrong**, both the same way: the release published *after* the PR merged while not containing it, because its branch was already cut. That is exactly what makes "merged before X, so it is in X" feel safe. One of the two had reached operator-facing guidance in `stt.md` as a version floor one release too low.

Latest vLLM is now **v0.30.0** (tag date 2026-09-21) — v0.30.0's release
notes were folded into SKILL.md/stt.md/reranking.md on 2026-09-23, see the
row below; rows further down that name an earlier tag are point-in-time and
remain correct for what they assert.

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

## 2026-09-23 release-note fold-in (v0.29.0 → v0.30.0)

Scoped pass: worked the v0.30.0 release notes for items on this skill's
surface (pooling/rerank/STT/OCR), not a full re-verification of every
existing claim (that pass ran 2026-09-22, see the freshen note above).

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.30.0 | <https://github.com/vllm-project/vllm/releases/tag/v0.30.0> | 2026-09-23 | new-feature | Tag date 2026-09-21. All source probes in this pass were made against the `v0.30.0` tag. |
| PR #51826 / #55642 — torchcodec audio backend | <https://github.com/vllm-project/vllm/pull/51826> | 2026-09-23 | new-feature | `AUDIO_BACKENDS = ("auto","soundfile","pyav","torchcodec")` in `vllm/multimodal/media/audio.py`. `auto` tries soundfile, then torchcodec, then pyav. Select via `--media-io-kwargs '{"audio":{"audio_backend":"torchcodec"}}'`. Applied to SKILL.md STT cheat-sheet + v0.30.0 section, stt.md §6. |
| PR #52598 — torchaudio default resampler | <https://github.com/vllm-project/vllm/pull/52598> | 2026-09-23 | deprecation / new-default | `MultiModalDataParser.__init__`'s `audio_resample_method` default is `"torchaudio"` at v0.30.0 (`vllm/multimodal/parse.py:609`), was `"pyav"`. torchaudio is already a standard dependency (`requirements/cuda.txt`, `cpu.txt`, `rocm.txt`, `xpu.txt`). Applied to SKILL.md + stt.md §6. |
| PR #54241 / #54918 — media_io_kwargs in mm cache hash, scoped by modality | <https://github.com/vllm-project/vllm/pull/54241> | 2026-09-23 | **broken / correctness** | Before: `media_io_kwargs` (e.g. `audio_backend`) was not part of the multimodal cache hash and hash kwargs were shared across modalities, so switching backend/kwargs between requests could reuse a stale cached decode. Applied to SKILL.md v0.30.0 section, stt.md §6. |
| PR #56017 — Qwen3 reranker missing-template warning | <https://github.com/vllm-project/vllm/pull/56017> | 2026-09-23 | new-feature (diagnostic) | `CrossEncoderIOProcessor` now `logger.warning`s naming the model id and `qwen3_reranker.jinja` when `is_original_qwen3_reranker=true` and no chat template is configured, instead of failing silently into random-looking scores. Applied to SKILL.md pitfall 5, reranking.md §2. |
| Out of scope for this skill — video-only v0.30.0 items | release notes "Multimodal"/"Correctness"/"Security" bullets | 2026-09-23 | not applicable | Request-controlled video sampling caps for `GLMGAVideoBackend` (#54935) and Qwen-VL (#56729); pruned sliding-window tiles for Gemma 4 video prompts (#53147); empty video URLs with multimodal UUIDs (#54220); base64 video validation (#54323); `VLLM_MM_HASHER_ALGORITHM` removal (#55353, replaced by `MultiModalConfig.mm_hasher_algorithm` / `--mm-hasher-algorithm`, confirmed absent from `vllm/envs.py` at v0.30.0 and present at v0.29.0). None touch pooling/rerank/STT/OCR; the hasher env var belongs to `vllm-configuration`'s catalog. Recorded here so a future pass does not re-research the same "in scope?" question. |

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
| PR #48290 — enable MRV2 for pooling by default | <https://github.com/vllm-project/vllm/pull/48290> | 2026-09-15 | **MERGED 2026-08-19** | Merge `08afae27`. Ancestry in-clone: **not** in v0.28.0, **is** in v0.29.0 — it landed after the v0.28.0 cut and no v0.28.1 was released, so v0.29.0 (2026-09-09) is the first release where pooling defaults to MRV2. Through v0.28.0 the earlier reading holds: `_is_default_v2_model_runner_model` returns False for `runner_type != "generate"` and `VLLM_USE_V2_MODEL_RUNNER` defaults to `None`. |
| MRV2 token-task restriction | v0.27.0 `vllm/v1/worker/gpu/pool/pooling_runner.py:65-78` | 2026-08-11 | new-feature | `_get_enabled_tasks` subtracts `token_embed`/`token_classify` unless `attn_type == "encoder_only"`. Startup error names the escape hatch `VLLM_USE_V2_MODEL_RUNNER=0`. |
| STT entrypoint package moved | v0.27.0 `vllm/entrypoints/speech_to_text/` | 2026-08-11 | **broken (source anchors)** | `vllm/entrypoints/openai/speech_to_text/` returns 404 at v0.27.0. New layout: `base/`, `transcription/`, `translation/`, `realtime/`, `factories.py`. Every anchor in stt.md §2/§11 pointed at the dead path. Applied. |
| PR #48543 — `diarized_json` | <https://github.com/vllm-project/vllm/pull/48543> | 2026-08-11 | new-feature | Merged 2026-07-29, v0.27.0, closes #48443. Transcriptions only (translations unchanged, matching the OpenAI contract). Model-gated, fail-closed parser; `json`/`text`/`verbose_json` paths untouched. Applied to stt.md §2 + roster row. |
| PR #41131 — cumulative STT chunk timestamps | <https://github.com/vllm-project/vllm/pull/41131> | 2026-08-11 | **broken (fixed)** | Merged 2026-07-27, v0.27.0 (tag-ancestry confirmed). **Issue #32588 is still OPEN** — the code shipped but the issue was never closed or linked, so its open state is not evidence the bug survives. `split_audio` searches a 1 s window before the nominal 30 s cut, but offsets assumed an exact 30 s; error accumulated ~1 s/chunk (~5 s over 10 chunks). Text was always right — only timestamps drifted. `TranscriptionSegment.seek` is now `int`. Applied to stt.md §6. |
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
| PR #47729 — MOSS-Transcribe-Diarize | <https://github.com/vllm-project/vllm/pull/47729> | 2026-09-15 | new-feature | Merged 2026-07-08; **first ships in v0.26.0**, not v0.25.0 — the merge commit is not an ancestor of v0.25.0 (published 2026-07-11, three days later). Tag-ancestry verified. `OpenMOSS-Team/MOSS-Transcribe-Diarize` — long-form transcription with timestamped speaker labels; Whisper-style encoder into a Qwen3 causal decoder. First diarizing model in the roster. Added to stt.md. |
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
| PR #39116 — ASR multi-chunk spacing fix | <https://github.com/vllm-project/vllm/pull/39116> | 2026-09-15 | version-drift | Merged 2026-04-09; **ships in v0.20.0 only** — `git tag --contains` on the merge commit. v0.19.1 published 2026-04-18, *after* the merge, and does not contain it: its branch was already cut. The floor here has now been wrong twice in the same direction ("v0.18+", then "≥v0.19.1"), both times by reasoning from dates. Corrected floor: **≥v0.20.0**. |
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
- references/stt.md §6 updated: #39116 is in v0.19.1 + v0.20.0 (not v0.18+). **Superseded 2026-09-15: it is v0.20.0 only — see the row above.**
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
