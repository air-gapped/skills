# Improvement Backlog — skill-improver

Carries ceiling/judgment findings across skill-improver runs. Read in Phase 0;
update in Phase 6. See SKILL.md §"Phase 6: Persist the backlog".

## Open

- **Dim 2 → 8/9: extract the improve-loop phases (Phase 0–6) to a reference.**
  SKILL.md is at 499 lines (1 under the 500 ceiling, no headroom). The only way
  below the 300-line "lean" band is to relocate the core improve loop, but it is
  the PRIMARY default mode and must stay visible in SKILL.md — burying it trades
  Dim 2 +1 for usability/Dim 4 on every default invocation. **Author judgment:**
  decide whether a thin-dispatcher SKILL.md (loop detail in
  `references/improve-loop.md`) is acceptable. File-set: SKILL.md:60–203 →
  new `references/improve-loop.md` + pointer. Not a single-iteration mutation.

- **Dim 1 → 9: `philosophy` mode + Boris/scaffolding-decay vocabulary absent
  from `when_to_use`.** Triggers cover improve/score/freshen/trigger well, but
  "philosophy mode", "boris alignment check", "scaffolding decay", "is my skill
  fighting the model's grain" have no trigger phrases (only `argument-hint` +
  body). Combined `description`+`when_to_use` is 1,308/1,536 chars — ~228 chars
  of headroom. Adding triggers blindly is a guess; do it empirically:
  `/skill-improver trigger skill-improver --missed "run a boris check on my skill"
  --missed "check my skill for scaffolding decay"`. Trigger-mode, not score-loop.

## Discards this pass (analyzed, not applied)

- **Dim 6: collapse Operating Rules that overlap the loop** ("Prioritize Deletion
  Over Addition" ≈ Phase 2 simplicity criterion; "One File at a Time" ≈ Phase 3
  atomicity). DISCARD — the overlap is deliberate standing-instruction
  reinforcement (survives compaction per `anthropic-skill-design.md` §"Skill
  Content Lifecycle"); deletion trades a marginal Dim-6 cosmetic gain for
  reinforcement loss. Not a ceiling claim — a judged no-op.
- **Dim 2: collapse the freshen/trigger mode-summary stubs into one table**
  (final blind agent's suggestion). DISCARD — the prose stubs carry the
  trigger context the model uses to know the modes exist; a table would compress
  that signal for ~3 lines. Net-negative.

## Resolved this pass — 2026-05-28 (improve + freshen, Opus 4.8 learnings)

Baseline self **81** / blind **84** → final self **89** / blind **90**. 12 kept changes.

**Freshen to Opus 4.8 / Claude Code v2.1.154** (verified via `gh` changelog +
anthropic.com news; Dim 9 6/7 → 10):
- SKILL.md Blind Validation model selection: "Opus 4.6+" → "Opus 4.8
  (`claude-opus-4-8`)".
- `anthropic-skill-design.md`: `effort` field notes Opus 4.8 defaults to `high`
  (`xhigh`/`max` for harder); added `disallowed-tools` frontmatter field
  (v2.1.152); added version-table rows v2.1.152 + v2.1.154.
- `improvement-patterns.md` §9.3: Opus 4.6 → Opus 4.8 effort example.
- `sources.md`: new "Most recent freshen pass: 2026-05-28" section; changelog row
  stamped 2026-05-28 / pinned v2.1.154; new Opus 4.8 news-page row; added a TOC.
- **Dynamic workflows** (the headline Opus 4.8 learning, maps to this skill's
  multi-agent core): notes in Blind Validation (§"Parallel scoring" — fan out N
  scorers, take the median, opt-in guarded) and Batch Mode (parallel baseline
  scoring via the `Workflow` tool).

**Improve** (rubric hill-climb):
- Extracted the Freshen Mode (F0–F6) and Trigger Mode (T0–T7) workflows from
  SKILL.md into `freshen-patterns.md` / `trigger-patterns.md` (one level deep,
  TOC + internal §-refs rewritten). SKILL.md **736 → 499 lines** (under the 500
  ceiling); Boris numbered-line count **70 → 40** (remaining lines are core
  methodology, rubric-exempt — confirmed by blind agent, no Dim 6 cap). Dim 2
  5→8, Dim 6 6→8.
- Converted 5 second-person slips to imperative (Dim 3 9 → 10).
- Reworded the backlog-reference self-contradiction at SKILL.md Phase 6 (Dim 8).
