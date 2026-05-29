# Improvement backlog — vllm-chat-templates

Tracks work attempted-but-not-completed and changes the metric registered.
Append-only; carry open items forward with a `(carried <date>)` marker.

## Open

- **DeepSeek-V3.1 #28804 won't-fix mitigation phrasing could be tightened** (Dim 4/6) —
  SKILL.md pattern #10 + model-families.md DeepSeek bugs row. The whitespace-accumulation
  workaround ("strip leading whitespace on each turn") is stated as guidance but lacks an
  exact client-side snippet. Not applied this pass: adding a snippet is additive content,
  not a one-line atomic edit, and risks Dim 6 regression — defer to an author-driven
  decision on whether the snippet earns its place.

## Resolved this pass

- (2026-05-28) GLM #39614 reclassified OPEN → CLOSED/COMPLETED 2026-04-25 in SKILL.md
  pattern #13, sources.md, and model-families.md GLM bugs table — Dim 9 freshen.
- (2026-05-28) GLM #39611 reclassified to CLOSED/COMPLETED 2026-04-12, mislabel GLM-4.7
  → GLM-5.1 corrected, in SKILL.md patterns #14 + triage table L61 and model-families.md;
  added a dedicated sources.md row and removed it from the not-re-probed bucket — Dim 8 + Dim 9.
- (2026-05-28) Standardized GLM section in model-families.md to note both documented bugs
  are GLM-5.1-FP8 — Dim 8 naming consistency.
- (2026-05-28) Collapsed the redundant per-layer re-definition block under the Triage table
  (5 lines → 1 line) while preserving the "diagnose one at a time" discipline and all three
  layer names — Dim 6 simplification.
- (2026-05-28) Re-stamped re-confirmed sources.md rows (PR #27622, #39392, #38855) and the
  SKILL.md footer to Last verified 2026-05-28; updated sweep header — Dim 9 staleness clock reset.
