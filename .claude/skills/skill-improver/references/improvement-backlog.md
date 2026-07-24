# Improvement Backlog — skill-improver

Carries ceiling/judgment findings across skill-improver runs. Read in Phase 0;
update in Phase 6. See SKILL.md §"Phase 6: Persist the backlog".

## Table of Contents
- [Open](#open) — carried + new ceiling findings, author-judgment items
- [Resolved this pass — 2026-07-24](#resolved-this-pass--2026-07-24-freshen--improve-opus-5-release-day)
- [Resolved this pass — 2026-07-18](#resolved-this-pass--2026-07-18-improve-self-run-mechanics-shakedown)
- [Discards / judged no-ops — 2026-05-28 / 2026-06-09](#discards--judged-no-ops--prior-passes-2026-05-28--2026-06-09)
- [Resolved — 2026-06-09 hotfix](#resolved--2026-06-09-hotfix-training-data-regression-guard)
- [Resolved this pass — 2026-06-09](#resolved-this-pass--2026-06-09-improve--freshen-fable-5-release-day)
- [Resolved — 2026-05-28](#resolved--2026-05-28-improve--freshen-opus-48-learnings)

## Open

- **(new 2026-07-24) Rule-ceiling discards: three rubric-invisible hardenings.**
  All three were applied, cold-scored Δ0 (every affected dim band-internal),
  and reverted per the Phase 4 rule — logged here because each has demonstrated
  operational value and only the author can accept rubric-invisible content:
  - **Line-ceiling gate** (Phase 4, ~7 lines): run `wc -l SKILL.md` before the
    decision rule; >500 is a Dim 2 regression regardless of total. Motivated by
    this run: the freshen additions took SKILL.md 493 → 506 (over the spec
    ceiling) and no rule caught it — only a manual count did.
  - **Freshen recency filter** (`freshen-patterns.md` §F2, ~8 lines): when a
    `Last verified:` stamp is under 7 days old, re-probe only changelogs,
    release tags, pinned commits, and launch pages; leave doc/spec/paper rows
    unprobed AND unrestamped (restamping an unprobed row silently disarms the
    Dim 9 staleness cap). This run followed the rule ad hoc with no text to cite.
  - **Reciprocal drift comment** (`scripts/batch-workflow.js`, 3 lines): a
    header on `blindPrompt()` naming `references/blind-validation.md` as
    canonical. The reference side of that guard was kept (iter 4); the script
    side scored Δ0, so the guard is currently one-directional.

- **(new 2026-07-24) Dim 6/4 discard: symptom → mode dispatch table** in
  §Invocation (13 lines). Net-negative, not rule-ceiling: the table duplicated
  guidance already carried by the Trigger Mode stub ("Use trigger mode when…")
  and Standalone Evaluation step 4, so the Dim 4 gain was cancelled by Dim 6
  redundancy. Do not re-propose as an addition — if mode dispatch is wanted at
  the entry point, it has to *replace* those two passages, which is a
  multi-section rewrite, not one iteration.

- **(new 2026-07-24, Opus 5 final-blind, author decision) Dim 9: skill omits
  two fields from its own Pattern 9.3 checklist.** `effort: xhigh` is the
  defensible one — this is a reasoning-heavy skill whose scoring quality the
  loop depends on, and the platform effort docs recommend `xhigh` as the
  starting point for agentic work — but it raises token spend on every
  invocation, including cheap `score` runs, so it is the operator's call.
  `disable-model-invocation: true` is **not** appropriate despite the checklist:
  proactive model invocation is the point (the whole `trigger` mode exists to
  make it fire), and setting it would remove the description from Claude's
  context entirely. Record the decision here either way so the next blind
  scorer's Dim 9 note can be dismissed with a reason.

- **(new 2026-07-24, final-blind, not attempted — cap reached) Dim 7:
  `scripts/batch-workflow.js` `DEFAULT_BASE` hard-codes the author's repo
  layout.** Overridable, so not a bug; portability nit only. Decide whether the
  script should derive the base from `${CLAUDE_SKILL_DIR}` instead.

- **(carried 2026-06-09, still Open) Dim 2 → 8/9: extract the improve-loop
  phases (Phase 0–5) to a reference.** Re-flagged by the 2026-07-24 final blind
  as the top Dim 2/6 ceiling. SKILL.md is now **379 lines** (was 493 at the
  start of this pass) after extracting Blind Validation and the Phase 6 backlog
  format; the ~150-line improve loop (SKILL.md §"The Improvement Loop") is the
  only workflow still inline and is what holds the file above the 300-line lean
  band. It remains the PRIMARY default mode and must stay visible — burying it
  trades Dim 2 +1 for usability/Dim 4 on every default invocation.
  **Author judgment:** decide whether a thin-dispatcher SKILL.md (loop detail in
  `references/improve-loop.md`) is acceptable. Not a single-iteration mutation.

- **(carried 2026-06-09, still Open) Dim 1 → 9: `philosophy` mode +
  Boris/scaffolding-decay vocabulary absent from `when_to_use`.** "philosophy
  mode", "boris alignment check", "scaffolding decay", "is my skill fighting the
  model's grain" have no trigger phrases (only `argument-hint` + body). Combined
  `description` + `when_to_use` is 1,305/1,536 chars — ~230 chars of headroom.
  Adding triggers blindly is a guess; do it empirically:
  `/skill-improver trigger skill-improver --missed "run a boris check on my skill"
  --missed "check my skill for scaffolding decay"`. Trigger-mode, not score-loop.
  Both 2026-06-09 blind agents and the 2026-07-24 baseline blind also flagged a
  T6-class cross-skill collision — the installed skill-creator plugin claims
  "modify and improve existing skills" territory; the trigger run should include
  sibling-territory negatives for it.

- **(carried 2026-07-18, still Open) Rule-ceiling discard: cold-score-from-disk
  clause.** Adding "read from disk — never from the context-injected copy;
  `${CLAUDE_SKILL_DIR}` appears pre-expanded there and reads as a false
  inconsistency" to Phase 1 §Cold-score discipline moved no dim (all affected
  dims band-internal) yet has demonstrated value: this exact trap caused a
  wrong `discard (noise)` at iter 4 of the 2026-07-18 self-run. Author
  judgment: accept as rubric-invisible operational hardening.

## Resolved — 2026-07-24 (evidence gaps found while running `autoresearch`)

Two defects in this skill surfaced by *using* it, not by scoring it. Both are
cases where the improver could not detect its own errors.

**1. Negative-Transfer Gate added (rubric §, new).** SkillLens's headline number
— skills help in 75% of extractor-target pairs, so **25% are net-harmful**, 47%
in the worst domain — had been sitting in a `sources.md` row since 2026-07-18 and
never reached the rubric or the loop. Nothing here ever asked *is this skill
worse than no skill*. Dim 10's own stated test ("if this skill were deleted,
would Claude produce noticeably worse results?") **is** that question, answered
by intuition — the judgement SkillLens clocked at 46.4%, worse than chance.
Dim 10 is now capped by measured `delta_pass_rate`: 2 if negative, 5 if ≈0,
uncapped if positive, and **8 while unmeasured** (a 9–10 asserts an outcome, not
a reading). Measurement reuses skill-creator's existing
`scripts/aggregate_benchmark.py`, which already computes with_skill vs
without_skill — deliberately not rebuilt here. Also wired into the blind-scorer
prompt so blind runs apply the same cap.

**2. Trigger mode's decision rule was unsound at its own default.** At
`--runs-per-query 3` a query can only score 0/0.33/0.67/1.0, so any query near
the 0.5 threshold is a coin flip and train moves ±1–2 on resampling alone. The
`autoresearch` run demonstrated both failure directions in one session: N=3
manufactured a 0.67 → 0.00 "regression" on the canonical query (6/7 vs 5/7 at
N=7 — pure noise) which cost a full wasted iteration built on a fabricated
proper-noun-placement mechanism, *and* hid a real 1/7 → 6/7 fix behind a tied
pass count. Fixed: probe default 3 → **7**; decision now allows a keep on mean
trigger rate (+≥0.10, no should-NOT regression) when the binary count ties;
guidance to re-measure only disputed queries at high N; T4 row rewritten to say
fractional rates mean *underpowered measurement*, not a mutation problem. The
"mirrors skill-creator" claim was corrected — the methodologies now differ on
this axis and the doc says so.

*Note the shape of both:* this skill warns targets about reward hacking and
noise, and was itself thresholding single-sample noise and scoring utility by
vibes. Running it against a real target found what scoring it never did.

## Resolved this pass — 2026-07-24 (freshen + improve, Opus 5 release day)

Baseline self **83** (post-freshen) / blind **83** → final self **88** / blind
**84**. 5 freshen findings applied, 5 improve keeps, 5 improve discards,
iteration cap reached at 10. No dimension had a 2+ self-vs-blind gap in either
direction at the final check.

**Freshen — Claude Code v2.1.214 → v2.1.219, Opus 5 launch day** (verified via
`gh api` changelog/commits, the Opus 5 launch page, and the live skills doc):
- **Blind-validation model pin moved Fable 5 → Opus 5** (`model: "opus"`,
  `xhigh`). Corrected mid-session after the operator produced the launch
  benchmark table: Opus 5 leads Fable 5 on GDPval knowledge work, BrowseComp
  agentic search, HLE-with-tools, and agentic terminal coding, and carries a
  May-2026 cutoff (vs Jan 2026) that directly reduces false Dim 9 flags on
  freshened claims; Fable 5's wins are sub-1-point coding margins plus legal.
  **Process failure worth remembering:** the first pass of this freshen kept
  the pin on the strength of the docs' "most capable widely released model"
  label and a fetched-page summary, without reading the benchmark rows — a
  vendor tier label is positioning, not measurement. `blind-validation.md`
  §Model selection now states both signals, why the measurements win for this
  task, and that re-pinning requires benchmark rows matching the scoring task.
- `anthropic-skill-design.md`: new frontmatter rows `background` (v2.1.218 —
  `context: fork` skills background by default, `background: false` restores the
  blocking turn and the full tool set) and `arguments`; `disable-model-invocation`
  now notes subagent-preload and scheduled-task blocking (v2.1.196); version rows
  v2.1.215/217/218/219.
- SKILL.md §Batch Mode: fan-out sizing now names all three live caps — 20
  concurrent subagents (v2.1.217), 200 subagents + 200 web searches per session
  (v2.1.212), and the <15-agent medium workflow size guideline (v2.1.219).
- SKILL.md §Standalone Evaluation: new scope boundary — every metric here scores
  the skill's *text*, never its outputs; output-quality evals live in the
  skill-creator plugin loop (`evals/evals.json`, per-case clean-context runs,
  `benchmark.json`, blind A/B), methodology at agentskills.io.
- `sources.md`: new 2026-07-24 pass section; changelog + releases pinned
  v2.1.219; anthropics/skills pinned 1f630fdf (2026-07-22, skill-creator path
  unchanged since 2026-04-20 → Trigger Mode mirroring still accurate); new rows
  for the Opus 5 launch page, the agentskills.io output-quality methodology
  page, and the skill-creator **plugin** install path
  (`anthropics/claude-plugins-official`, the copy the official docs now point at).

**Improve** (rubric hill-climb; self-score column):
- **iter 1 (keep, +2 → 85):** extracted the blind-scorer prompt, model pin,
  parallel-scoring variant, and bias-check table to
  `references/blind-validation.md`, leaving a stub that keeps the two binding
  rules inline. SKILL.md 506 → 421, back under the 500-line spec ceiling.
- **iter 2 (keep, +1 noise-confirmed → 86):** fixed the Boris compensation-language
  probe in `quality-rubric.md` — the `\|` table-cell escapes made the pasted
  command a valid regex that silently matched nothing (verified: escaped form
  exit 1 / 0 matches, corrected form 6 matches). Probe moved below the table
  with the reason stated so it cannot be re-escaped. Closes a carried item.
- **iter 4 (keep, +1 noise-confirmed → 87):** unified the canonical blind prompt
  with `batch-workflow.js` `blindPrompt()` — Dim 9 staleness + spec hard-fail
  caps, `evals/` read step, blind framing — and marked the reference block
  canonical. Closes the two-pass "blind prompts non-comparable" item.
- **iter 6 (keep, simplification → 87):** extracted the Phase 6 backlog format
  (Open/Resolved admission rules, carry-forward, append-only rule) to
  `references/backlog-format.md`. SKILL.md 421 → 379.
- **iter 8 (keep, +1 confirmed → 88):** `scan-skills.sh` now discovers nested
  `.claude/skills/` directories (directory-qualified skills, v2.1.205) that
  `batch --all` silently skipped; tested against a synthetic monorepo and the
  live repo (93 rows, no duplicates). Also removed shipped `__pycache__` /
  `.ruff_cache` cruft.
- **post-cap fixes (Opus 5 re-score of the final artifact):** batch blind
  scorers now carry the same explicit pin as a solo run
  (`model: 'opus'`, `effort: 'xhigh'` in `batch-workflow.js`) — they previously
  inherited the session model, contradicting the binding pin rule and making
  batch and solo blind scores non-comparable; the Batch Mode dynamic-workflow
  label "Fable 5 / Opus 4.8" corrected to "Fable 5 / Opus 5"; TOC added to this
  file (310 lines, a non-optional Phase 0 read, and the only >100-line
  reference without one).
- **post-cap fix (final-blind finding):** `probe-trigger.py` denied `Task` but
  not `Agent` — the canonical name since v2.1.63 — so a probed agent could still
  spawn subagents, breaking the hermetic-probe guarantee the file's own comments
  promise. Both names are now denied.

Discards this pass (anti-re-proposal guards):
- **iter 3:** `discard (noise)` — porting only the Dim 9 cap sentence into the
  blind prompt left the rest of the drift in place; Dim 8 stayed band-internal.
  Re-proposed at full scope as iter 4 → kept.
- **iter 5, 7, 10:** rule-ceiling — line-ceiling gate, freshen recency filter,
  reciprocal drift comment (all moved to Open above).
- **iter 9:** net-negative — symptom → mode dispatch table (moved to Open above).

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
