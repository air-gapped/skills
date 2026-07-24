# Improvement backlog — postgres-operator-cloudnative-pg-migration

Carries ceiling findings across skill-improver runs. Append-only history.

## Open

- **SKILL.md <150 lines for Dim 2 = 10** (Dim 2). SKILL.md sits at ~192
  lines; the 9→10 step requires compressing the walls/paths/HA sections
  in one pass — a multi-section restructure that risks the scan-layer
  completeness (Dim 5) and was judged not single-iteration-safe on
  2026-07-24. Only worth attempting with a fresh benchmark run to prove
  no regression.
- **Trigger mode not yet run** (Dim 1, empirical). Description was
  tuned to fit the 1,536-char listing cap by inspection only; run
  `/skill-improver trigger postgres-operator-cloudnative-pg-migration`
  to measure actual fire/silence rates (house rule: Haiku screens, Opus
  confirms; never strip when_to_use).
- **Freshen after CNPG 1.31.0** (~2026-09-29) (Dim 9). Volatile facts
  flagged in sources.md §"Volatile facts": in-tree barman removal
  (slipped 4×), plugin↔CNPG minor pairing, Zalando release state, CNCF
  incubation cncf/toc#1961, open-bug states (#3788, #8902, #652, HA
  set). Run freshen mode when 1.31.0 lands.

## Resolved this pass — 2026-07-24

Run: 8 iterations, self-score 83 → 91; blind baseline 87, blind final 87
(final blind ran before iters 7–8, whose fixes implement its own top
findings — its Dim 3: 8 and Dim 8: 8 predate those fixes).

- iter 1: frontmatter 1,834 → 1,521 chars — symptom triggers + NOT
  clause now inside the 1,536 listing cap (Dim 1, +2).
- iter 2: SKILL.md second-person → imperative, 2 spots (Dim 3).
- iter 3: sources.md operand-majors row disambiguated (image repo
  *builds* 13–18, CNPG *supports* 14–18) — blind-flagged mismatch (Dim 8/9).
- iter 4: TOCs added to all five >100-line references (Dim 2/7).
- iter 5: backup-chain wall-recap deduplicated, −2 lines (Dim 6).
- iter 6: duplicate rolling-restart entry removed from quick index (Dim 6).
- iter 7: path-chooser PG-floor contradiction fixed — Path A valid from
  source PG ≥10; PG≤13 routes to A or B, not B only (final-blind flag, Dim 8).
- iter 8: 4 second-person slips in references fixed (final-blind flag, Dim 3).

Discards: none — every hypothesis derived from a rubric criterion or a
blind-agent finding and landed. Ceiling not mapped by discard evidence;
the run stopped on the 90+/no-dim-below-7 condition (self 91).
