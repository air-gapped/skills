# Improvement backlog — postgres-operator-best-practices

Carries ceiling findings across skill-improver runs. Append-only history.

## Open

## Unblocked — actionable

- **No trigger-mode measurement yet** (Dim 1, empirical). The description and
  `when_to_use` were written by hand and sized by inspection (1,515/1,536
  chars), never measured. Run
  `/skill-improver trigger postgres-operator-best-practices` for actual
  fire/silence rates. This skill shares much of its trigger space with the
  sibling `postgres-operator-cloudnative-pg-migration`, so the run has to test
  both directions of confusion — this skill firing on migration queries and
  vice versa — not just its own recall.
- **Duplication between SKILL.md and `upgrade-v1-v2.md` is still the lowest
  dimension** (Dim 6). The final blind scorer of the 2026-08-25 pass scored
  Dim 6 **6/10** against a self-score of 8 — the largest self/blind gap in the
  run, and in the generous direction. It named three specific blocks still
  carried in both files: the pins/breaking-defaults table, the "Choosing a
  path" table, and the v2.0.2-viability writeup. Its recommendation is to keep
  each once and have SKILL.md point at the reference.

  Do not act on that recommendation blind. Iteration 8 of the same pass ran the
  experiment on a fourth such block and it came back negative: −4 lines for a
  Dim 5 loss, because SKILL.md is what loads when the skill fires and the
  compressed content answered an advertised symptom. The open question is which
  of the three named blocks are decision-critical on trigger (keep in SKILL.md)
  and which are reference material (move). That needs the eval corpus below to
  settle, not another round of judgement.

- **Dim 2 will not reach 9 without an evidence-backed restructure** (Dim 2).
  The 9–10 band wants SKILL.md under 150 lines; it is 231. This is a mapped
  trade, not a pending chore: iteration 8 of the 2026-08-25 pass measured it.
  Compressing the dropped-in-v2 list to a pointer bought only −4 lines and cost
  Dim 5 a point, because the manifest-field rename mapping is what answers the
  "unknown field errors after a chart bump" symptom the frontmatter advertises.
  Getting under 150 therefore needs a restructure that relocates whole
  responsibilities rather than compressing prose, and it needs a benchmark run
  to show completeness held. Blocked on that measurement, which needs an
  `evals/` corpus this skill does not have.

## Resolved this pass — 2026-08-25 (improve)

Run: 10 iterations (cap reached), 9 keeps, 1 discard. Self-score 75 → 87.
Blind baseline 79.

- iter 1: SKILL.md's v2-defect section reproduced `upgrade-v1-v2.md` at full
  fidelity — compressed to the decision plus the one scope note that changes a
  path choice (Dim 6, 242 → 226).
- iter 2: dropped the "three breaking defaults, restated" table from
  `upgrade-v1-v2.md` — blind-flagged verbatim duplicate, sitting directly below
  its own pins table (Dim 6, 237 → 229).
- iter 3: seven second-person slips → imperative, across SKILL.md and
  `upgrade-v1-v2.md`. Blind's top-ranked defect (Dim 3, 6 → 9). The one
  remaining "you" is inside a quoted release note and stays.
- iter 4: added password rotation, logical backups and connection pooler to
  `operations.md` — all three were advertised in the frontmatter and served
  nowhere. Written from `docs/administrator.md` and `docs/user.md` at tag
  v2.0.2 (Dim 5, 6 → 8; +2 confirmed on a second cold score).
- iter 5: `docker_image` blast-radius passage de-duplicated out of
  `operations.md`, last of the three blind-flagged verbatim pairs (Dim 6).
- iter 6: v1.15.1 staging-point rationale co-located into "Choosing a path" —
  it had been argued twice in SKILL.md across two headings (Dim 8, 8 → 9).
- iter 7: v2 traps recast as a three-item pre-flight checklist; fixed a latent
  count error the restructure exposed (heading read "Two" over three items)
  (Dim 4, 8 → 9).
- iter 9: `sources.md` moved to the one-stamp `Freshened:` contract — all 25
  rows carried the same date. `staleness-report.py` now reads `full` rather
  than 25/25 (Dim 7, 8 → 9).
- iter 10: symptom index added to SKILL.md, routing each frontmatter-advertised
  symptom to the section that answers it (Dim 5, 8 → 9; the one iteration that
  grew SKILL.md, kept on a re-scored confirmation).

Discard — iter 8: compressing the "Also dropped in v2" list to a pointer.
−4 lines gained, Dim 5 lost a point. **The rename mapping
(`init_containers` → `initContainers` and the three others) is load-bearing in
SKILL.md**, because "unknown field errors after a chart bump" is an advertised
symptom and that table is its answer. Do not re-propose compressing it.

Ceiling status: **cap reached, not ceiling mapped.** One discard in one
category is not the 5-across-2 the ceiling claim requires, so the remaining
improvement space is unmeasured rather than known-empty.
