# Improvement backlog — vllm-input-modalities

Tracks issues attempted during skill-improver passes that could not be
resolved in a single atomic keep/discard iteration, plus a log of what each
pass actually changed.

## Open

- **v0.20.0 PR-list redundancy across three files** (Dim 6) —
  `SKILL.md` "Landed in v0.20.0" section vs `references/sources.md`
  derived-updates vs `references/runner-flags.md` §3/§10. The PR-by-PR
  perf/breaking list is stated in all three. Not collapsed: SKILL.md needs
  the breaking-change callouts inline (Completeness/Actionability), the
  reference files are the deep audit trail, and sources.md is the dated
  evidence log — deleting from any one harms a different dimension, so this
  is a deliberate-tension item, not a one-edit win. (carried 2026-05-28)

## Resolved — 2026-08-11 (freshen, rebaseline v0.25.1 → v0.27.0)

- **A pooling *correctness* bug, the pass's headline** — #48901 (v0.26.0).
  LAST-pooling models returned wrong scores whenever chunked prefill split a
  query+doc pair, under `torch.compile` only. The previous two passes both
  found request *validation* tightening; this is the first finding that
  invalidates **results already produced**, so the guidance says re-score,
  not just upgrade. Applied to SKILL.md pitfall 5, `reranking.md` §2 (with
  the `--enforce-eager` A/B diagnostic) and `embedding.md` §7, where the
  skill previously said chunked prefill "works, leave defaults on" without
  a version floor.
- **Caught a claim that was stale before the last pass, not because of it.**
  The skill said `--task` was "deprecated, not dead — still works with a
  warning". Source probes at v0.22.0, v0.25.1 and v0.27.0 all show no `task`
  field in `ModelConfig` and no `--task` in `arg_utils.py`. Release-note
  diffing could never have caught this, because the removal predates the
  skill's own previous baseline. **Method note for future passes:** re-probe
  the load-bearing *negative* claims ("X still works") against source, not
  just the delta between two release bodies. Same class: `score` / `encode`
  pooling task names now raise `VLLMValidationError`.
- **MRV2 pooling documented with the default correctly stated.** The v0.27.0
  release note headline reads as though pooling moved to Model Runner V2. It
  did not: #48290 is still open and
  `_is_default_v2_model_runner_model` returns False for non-`generate`
  runners. Recorded as opt-in, with the token-task/encoder-only restriction
  and the `VLLM_USE_V2_MODEL_RUNNER=0` escape hatch (`runner-flags.md` §11).
  A pass that trusted the headline would have told operators their pooling
  deployments had changed under them.
- **Fixed dead source anchors.** The whole STT entrypoint package moved out
  of `vllm/entrypoints/openai/`; every path in `stt.md` §2/§11 404s at
  v0.27.0. Anchors rot silently — worth a cheap existence check each pass.
- **STT request surface additions** (all v0.27.0): `diarized_json` (#48543),
  cumulative chunk timestamps (#41131 — long-form drift of ~1 s per chunk),
  translation-API sampling params (#45839), MOSS-TD 90-minute audio ceiling
  (#49403, which had been rejecting long audio at request time).
- **Roster additions:** `jina-embeddings-v5-text-nano` (#50688 — same arch,
  EuroBERT *encoder* backbone, which is what makes it MRV2-eligible),
  `BertForMaskedLM`, `Roberta`/`XLMRobertaForTokenClassification`,
  LongCat-Flash-Lite n-gram embedding. All confirmed in `registry.py`.
- **Corrected an overstatement found while re-verifying for the restamp:**
  `NGramPerReqLogitsProcessor` does not "enforce" the whitelist / ngram /
  window values — it reads them from per-request `extra_args`. The recipe
  supplies them, so a client that bypasses the recipe's request shape loads
  the processor unconfigured (`ocr.md` §3).

**Carried forward:** the Open item below (v0.20.0 PR-list redundancy across
three files) is untouched. Note this pass added a second version section to
SKILL.md, which pushes mildly in the same direction — if a future pass wants
to collapse anything, the v0.20.0/v0.21–v0.25 history is the older and
therefore cheaper half to compress.

**Not probed this pass:** HuggingFace model cards, the Red Hat Whisper/RHAIIS
blog, the `docs.vllm.ai` pooling doc tree, and the DeepSeek-OCR recipes page.

## Resolved — 2026-07-21 (freshen, rebaseline v0.21.0 → v0.25.1)

- **Two silent-success → hard-error changes found and documented** (the pass's
  main value). Both landed in v0.24.0 and both turn requests that used to
  return 200 into errors:
  - **#46313** — matryoshka `dimensions` above `hidden_size`. For an MRL model
    with no explicit `matryoshka_dimensions` list, validation checked only
    `dimensions >= 1` and then sliced `[..., :d]`, so an oversized request
    *silently returned a `hidden_size`-length vector*. Applied to SKILL.md
    matryoshka block + `embedding.md` §3, including the operational
    consequence: any index built pre-v0.24 with an oversized value holds
    `hidden_size`-width vectors, so a post-upgrade 400 is pointing at bad data
    upstream, not at a new bug.
  - **#46119** — rerank `top_n=-1` was silently treated as `0` (return all), so
    a client sentinel of `-1` "worked" by accident. Applied to `reranking.md`.
- **Refuted an inviting misreading.** The v0.22.0 release note "truncation side
  for OpenAI endpoints" (#43260) reads as though `/v1/embeddings` gained
  `truncation_side`. The PR body scopes it to `/v1/completions` and
  `/v1/chat/completions` only. SKILL.md now records this as explicitly **not**
  applicable — a negative result worth carrying, since the release-note wording
  will keep inviting the same inference.
- **New capability documented:** #45173 — `/v1/embeddings` now accepts
  message-shaped input and honours `chat_template_kwargs` (v0.24.0). Previously
  rejected at validation; only the top-level messages extension worked. This is
  the supported path for instruction-style embedders (`embedding.md` §1).
- **Roster additions:** Unlimited OCR (#46564 + Triton R-SWA #47102, v0.25.0)
  to `ocr.md` §2; MOSS-Transcribe-Diarize (#47729, v0.25.0) to `stt.md` —
  flagged as the only diarizing entry, which changes the answer to "how do I
  get speaker labels" from "bolt on a separate stage" to "use this model".
- **Confirmed non-events** (recorded so a future pass doesn't re-probe them):
  #42370/#42274 STT entrypoint + test consolidation is an internal refactor
  with no endpoint change; #47071/#47437 pooled-Whisper sliding-window fix is
  KV-memory sizing only; #46762 realtime embeddings is MRv2-internal.
- **Ecosystem removals noted:** PagedAttention deleted in v0.25.0 (#47361),
  Transformers v4 deprecated (#45161), ~11 model families removed across
  v0.24.0/v0.25.0. None on this skill's surface, but recorded because an
  operator bumping the image for an unrelated reason can still be stranded.
- **Refresh-trigger heuristic sharpened.** Two consecutive passes have now found
  the *runner* surface frozen while request validation tightened underneath it.
  The trigger note now says to grep release bodies for
  `pooling|rerank|embedding|matryoshka|top_n`, not just for runner flags —
  the old trigger wording would have missed both #46313 and #46119.

**Carried forward:** the single Open item below (v0.20.0 PR-list redundancy
across three files) is untouched — it is a deliberate-tension item, not a
pending task.

**Not probed this pass:** HuggingFace model cards, the Red Hat Whisper/RHAIIS
blog, and the `docs.vllm.ai` pooling doc tree — all still listed as
"Non-probed references" in `sources.md`.

## Resolved this pass (2026-05-28)

- Qwen3-Reranker three-extras recipe de-duplicated — `SKILL.md` pitfall #5
  now points to the cheat-sheet command above + `references/reranking.md`
  §2 instead of restating the three `--hf-overrides` keys a third time
  (Dim 6 8→9).
- `max_tokens_per_doc` provenance contradiction fixed — "late 2025" →
  "v0.20.0 (PR #38827)" in `SKILL.md` cheat sheet and
  `references/reranking.md` §3, matching sources.md + reranking.md §8
  (Dim 8).
- Async-scheduling-off date contradiction fixed — `references/runner-flags.md`
  §5 "(PR #39592, 2026-01)" → "merged 2026-04-12", matching §3/§10 +
  sources.md (Dim 8).
- `logit_bias/scale` rename provenance contradiction fixed —
  `references/reranking.md` §4 "(late 2025)" → "in v0.20.0 (PR #39530)"
  (Dim 8).
- v0.20.0 release date corrected 2026-04-23 → 2026-04-27 across SKILL.md,
  runner-flags.md §3, reranking.md §8, embedding.md §4, stt.md §6,
  sources.md (Dim 9; gh `published_at` evidence in recon).
- Rebaselined v0.20.0 → v0.21.0 — new SKILL.md "Since v0.20.0 (current
  baseline v0.21.0)" subsection (no runner/convert/pooler breaking change;
  perf-only #41163 AllPool +51%, #41433 sync elimination), footer restamped
  to 2026-05-28, refresh trigger bumped to v0.22+ (Dim 9).
- Qianfan-OCR (#40136) added to `references/ocr.md` §2 roster (v0.21.0
  new OCR architecture) (Dim 5/9).
- All six reference `Last verified` lines restamped 2026-05-28 against
  v0.21.0; new dated freshen section added to `references/sources.md`.
