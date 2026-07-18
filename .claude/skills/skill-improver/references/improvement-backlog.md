# Improvement Backlog — skill-improver

Carries ceiling/judgment findings across skill-improver runs. Read in Phase 0;
update in Phase 6. See SKILL.md §"Phase 6: Persist the backlog".

## Open

- **(new 2026-07-18) Dim 8: blind-scorer prompt drift between SKILL.md and
  batch-workflow.js.** Final-blind finding (self 10 vs blind 8 — flag accepted):
  `scripts/batch-workflow.js` blindPrompt instructs Boris caps, the Dim 9
  staleness cap, and spec hard-fail checks; SKILL.md §"Blind Validation" prompt
  omits all three, so solo-run and batch-run blind scores are non-comparable.
  Not attempted this run (iteration cap reached at the flag). Two-file
  unification; author should decide the canonical prompt (likely: port the
  three cap instructions into the SKILL.md prompt).

- **(new 2026-07-18) Dim 7: quality-rubric.md:323 Boris detection `rg` breaks
  on copy-paste.** Final-blind finding: the markdown-table cell escapes `\|`
  read as literal-pipe regex escapes from raw source; the working form exists
  at freshen-patterns.md:311. Single-iteration fix for the next run: align the
  rubric command with the freshen-patterns form (verify by executing both).

- **(new 2026-07-18) Rule-ceiling discard: cold-score-from-disk clause
  (iter 6).** Adding "read from disk — never from the context-injected copy;
  `${CLAUDE_SKILL_DIR}` appears pre-expanded there and reads as a false
  inconsistency" to Phase 1 §Cold-score discipline moved no dim (all affected
  dims band-internal) yet has demonstrated value: this exact trap caused a
  wrong `discard (noise)` at iter 4 of the 2026-07-18 self-run. Author
  judgment: accept as rubric-invisible operational hardening.

- **(new 2026-07-18) Dim 9 staleness horizon: sources.md rows stamped
  2026-05-01 cross the 90-day cap ~2026-07-30.** Both blind agents flagged it.
  Action: run `freshen skill-improver` before the end of July; score-loop
  mutations cannot resolve this.

- **(carried 2026-06-09) Dim 2 → 8/9: extract the improve-loop phases (Phase 0–6)
  to a reference.** SKILL.md is now 427 lines after the Philosophy Mode extraction;
  the improve loop (~144 lines, SKILL.md §"The Improvement Loop") is the only
  workflow still inline. Both 2026-06-09 blind agents re-flagged it as the top
  Dim 2 issue. It remains the PRIMARY default mode and must stay visible —
  burying it trades Dim 2 +1 for usability/Dim 4 on every default invocation.
  **Author judgment:** decide whether a thin-dispatcher SKILL.md (loop detail in
  `references/improve-loop.md`) is acceptable. Not a single-iteration mutation.

- **(carried 2026-06-09) Dim 1 → 9: `philosophy` mode + Boris/scaffolding-decay
  vocabulary absent from `when_to_use`.** "philosophy mode", "boris alignment
  check", "scaffolding decay", "is my skill fighting the model's grain" have no
  trigger phrases (only `argument-hint` + body). Combined `description` +
  `when_to_use` is 1,304/1,536 chars — ~230 chars of headroom. Adding triggers
  blindly is a guess; do it empirically:
  `/skill-improver trigger skill-improver --missed "run a boris check on my skill"
  --missed "check my skill for scaffolding decay"`. Trigger-mode, not score-loop.
  **New evidence 2026-06-09:** both blind agents also flagged a T6-class
  cross-skill collision — the installed skill-creator plugin claims "modify and
  improve existing skills" territory; the trigger run should include
  sibling-territory negatives for it.

## Resolved this pass — 2026-07-18 (improve, self-run: mechanics shakedown)

Baseline self **83** / blind **85** → final self **85** (Dim 8 flag accepted →
effective ~83–84) / blind **83**. 4 kept, 6 discarded, cap reached at 10.
First live exercise of the rejected-edit buffer and +1 noise floor (added
2026-07-18, commit 98bf0af); every decision-rule path fired at least once.

- **iter 1 (keep, +1 noise-confirmed):** decision rule partitioned by delta
  (+2+/+1/Δ0/worse/crash) — removed the header-contradicts-body nesting the
  98bf0af noise floor shipped with.
- **iter 2 (keep, simplification):** trimmed the rhetorical tail from the
  Phase 4 discard bullet.
- **iter 5 (keep, +1 noise-confirmed):** flattened the philosophy-patterns P0
  A→B chain by naming the three check-section anchors in the SKILL.md
  Philosophy stub (anchors verified on disk). Baseline-blind Dim 8 nit closed.
- **iter 7 (keep, +1 noise-confirmed):** snapshot-aware keep/discard state
  handling — commit each keep, or snapshot when commits are not permitted;
  discard-revert restores the last kept snapshot instead of `git checkout`
  (which reverts to HEAD and silently destroys uncommitted keeps — this
  exact data loss occurred at iter 4 of this run and was recovered from
  scratchpad snapshots).

Discards this pass (anti-re-proposal guards):
- **iter 3:** `discard (noise)`-status example row in rubric §Results Log
  Format — Dim 8 pinned by the then-open P0 chain; pure addition.
- **iter 4:** `discard (noise)` — P0-chain flatten +1 failed cold rescore
  against a *false* blocker (see incident below); re-proposed and kept as
  iter 5 under the buffer's new-evidence exemption.
- **iter 6:** rule-ceiling — cold-score-from-disk clause (moved to Open).
- **iter 8:** "run log"→"results log" rename — single co-referential
  occurrence, below rubric granularity; Δ0, no line reduction.
- **iter 9:** mode-name tags on section headings (`score`, `improve`) —
  band-internal on all affected dims; Δ0.
- **iter 10:** Phase 0 baseline-snapshot location `/tmp` → scratch dir —
  cosmetic seam, not behavioral; replaced a concrete path with a placeholder.

Process incidents (self-run lessons, both recoverable):
- **Context-vs-disk trap:** when the target skill is the currently-invoked
  one, the context-injected SKILL.md has `${CLAUDE_SKILL_DIR}` pre-expanded;
  scoring against it produced a phantom "hardcoded path" inconsistency and a
  wrong discard (iter 4). Always score against the on-disk file.
- **Revert footgun:** `git checkout -- <file>` on discard (iter 4) wiped
  uncommitted keeps 1–2; recovered from per-keep scratchpad snapshots and
  fixed structurally in iter 7.

## Discards / judged no-ops — prior passes (2026-05-28 / 2026-06-09)

- **(carried 2026-05-28) Dim 2: collapse the freshen/trigger mode-summary stubs
  into one table** (a final blind agent's suggestion). DISCARD — the prose stubs
  carry the trigger context the model uses to know the modes exist; a table
  would compress that signal for ~3 lines. Net-negative. Applies equally to the
  philosophy stub added 2026-06-09.
- **Dim 6: trim ~20–30 lines of deliberate reinforcement** ("Operating Rules"
  restating phase rules; "What a stop is NOT"; "Open is NOT a wishlist"). Blind
  agents scored Dim 6 at 6–7 citing this density both passes. The 2026-05-28 run
  analyzed the deletion and DISCARDED it: the overlap is standing-instruction
  reinforcement that survives compaction (`anthropic-skill-design.md` §"Skill
  Content Lifecycle"). Author decision stands; re-evaluate only if a future
  blind agent shows the redundancy causing *behavioral* errors, not just
  rubric-cosmetic cost.

## Resolved — 2026-06-09 (hotfix: training-data regression guard)

**User-reported incident:** an `improve` run on `rust-expert` mutated factual
claims from training-data memory, regressing content the skill had been
freshened to AFTER the model's knowledge cutoff. Root cause: only `freshen`
mode was required to go online — `improve` hypotheses and blind-scorer
findings could alter external-world claims (versions, dates, model names,
flags, SHAs) from the model's stale prior, and nothing treated a
version-downgrade as the alarm signal it is.

**Fix (4 files, every point where a mutation or score can originate):**
- SKILL.md: new Operating Rule §"The Skill Outranks Training Data" (never
  mutate external-world claims from memory; downgrade = mandatory online
  probe; binds blind scorers); Phase 2 "Factual-claim hypotheses require a
  probe"; blind-agent prompt Dim 9 guard.
- quality-rubric.md Dim 9 check method: verification = online probes / local
  execution / sources.md stamps, never scorer memory; recent stamp outranks
  the prior.
- improvement-patterns.md: Dim 9 guard banner; Patterns 9.1/9.2 now require
  cited online probes and forbid memory-based "corrections".
- scripts/batch-workflow.js: recon STEP 3 (no memory-based Dim 9 docking),
  STEP 4 (factual-claim hypotheses only from STEP 5 probes), apply
  WORKSTREAM A rule (freshen evidence required, downgrades presumed stale),
  blindPrompt Dim 9 guard.

## Resolved this pass — 2026-06-09 (improve + freshen, Fable 5 release day)

Baseline self **84** / blind **82** → final self **88** / blind re-run after
post-flag fixes (see below). 13 kept changes, 0 discards (iteration cap reached;
no ceiling claim made).

**Freshen — Fable 5 / Claude Code v2.1.155–170** (verified via `gh` changelog +
https://www.anthropic.com/news/claude-fable-5-mythos-5):
- SKILL.md Blind Validation model pin: Opus 4.8 → **Fable 5** (`claude-fable-5`,
  Mythos-class tier above Opus, v2.1.170, 2026-06-09); `model: "opus"` →
  `model: "fable"` in the Agent-call instruction (tail fixed after the final
  blind agent caught the incomplete first edit).
- Dynamic-workflow opt-in language: trigger keyword `workflow` → `ultracode`
  (renamed v2.1.160) in both Workflow sections; "agents inherit Opus" → "the
  session model"; batch-workflow.js comment likewise.
- `anthropic-skill-design.md`: effort row (`xhigh` = Fable 5 + Opus 4.8/4.7);
  version-table rows v2.1.157/160/163/169/170; Key Settings rows
  `disableBundledSkills` + `CLAUDE_CODE_SAFE_MODE`.
- `improvement-patterns.md` §9.3: effort example → Fable 5 / Opus 4.8.
- `sources.md`: new 2026-06-09 pass section; changelog pinned v2.1.170; Fable 5
  news row; anthropics/skills re-pinned c30d329f (2026-06-07, skill-creator
  unchanged); agentskills spec re-pinned 5d4c1fda (2026-05-20 name-field docs
  clarification — matches rubric, no drift).

**Improve** (rubric hill-climb + blind-agent findings):
- Fixed broken `rg -nE`/`rg -inE` detection commands in quality-rubric.md §Boris
  and freshen-patterns.md §4b — in ripgrep `-E` is `--encoding`, so the
  documented Boris probes errored as written (verified live, corrected forms
  tested). Dim 7.
- Rewrote the broken awk section-length detector in freshen-patterns.md §4b
  (first rule's `next` made the print rule unreachable — probe #3 silently
  output nothing); new one-liner tested. Dim 7 (final-blind finding).
- Extracted Philosophy Mode (P0–P4, batch, anti-patterns) to
  `references/philosophy-patterns.md` with stub + pointer — SKILL.md 497→427
  lines, all five non-default modes now uniformly extracted. Dim 2 6→7
  (baseline-blind top issue).
- Fixed "Phase 0 step 4" → "step 5" off-by-one in Blind Validation §When to Run.
  Dim 8 (baseline-blind finding).
- Resolved the rubric/trigger-patterns voice contradiction: rubric Dim 1 failure
  example now distinguishes true second person ("You can use this...") from
  acceptable imperative ("Use this skill when..." — the form Anthropic's own
  skill-creator optimizer emits). Dim 8 (baseline-blind finding).
- Batch sub-mode list now includes `philosophy` (was freshen/improve/trigger
  only, contradicting the mode's own batch section). Dim 8 (final-blind finding).
- Converted 5 second-person slips in trigger-patterns.md to imperative (Boris
  quote and intentional examples untouched). Dim 3.

## Resolved — 2026-05-28 (improve + freshen, Opus 4.8 learnings)

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

*(2026-05-28 record restored 2026-06-09 — dropped in that day's backlog rewrite;
prior-pass history stays in the live file so future loops inherit it without
digging through git.)*
