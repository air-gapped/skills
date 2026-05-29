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
