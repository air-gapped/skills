# The Improvement Loop — Phase Workflow (Phases 0–6)

The full phase workflow for `improve` mode (the default). Extracted verbatim
from `SKILL.md` §"The Improvement Loop"; the stub there carries the three
rules that bind without reading this file. Cross-cutting rules (Operating
Rules, The Skill Outranks Training Data, Blind Validation spawn mechanics)
stay in `SKILL.md` and the references it names.

## Table of Contents

- [Phase 0: Setup](#phase-0-setup)
- [Phase 1: Evaluate (Score the Skill)](#phase-1-evaluate-score-the-skill)
- [Phase 2: Hypothesize (Pick One Improvement)](#phase-2-hypothesize-pick-one-improvement)
- [Phase 3: Mutate (Make the Change)](#phase-3-mutate-make-the-change)
- [Phase 4: Re-evaluate (Score Again)](#phase-4-re-evaluate-score-again)
- [Phase 5: Log and Loop](#phase-5-log-and-loop)
- [Phase 6: Persist the backlog](#phase-6-persist-the-backlog)
- [Phase 7: Land it](#phase-7-land-it)

## Phase 0: Setup

1. Identify the target skill. Accept a path, or run `scripts/scan-skills.sh` (or Glob pattern `**/SKILL.md` under `~/.claude/skills/` and `.claude/skills/`) to list candidates. Do NOT search `~/.claude/plugins/` — those are managed externally.
2. Read `SKILL.md`, then list the directory. Open a `references/`, `scripts/`, `examples/` or `assets/` file when a phase needs it — Phase 1 scoring needs the reference files, Phase 2 needs whichever the hypothesis targets. Reading the whole tree up front costs the loop its own induced-cost cap on a large skill and buys nothing the phases do not ask for.
3. **Read `<skill>/references/improvement-backlog.md` if it exists.** This file carries open issues from prior skill-improver runs — ceiling-hit items that require multi-file restructure or author judgment. Do NOT re-propose items already listed there unless new evidence (e.g. the ceiling is now breakable in one iteration due to earlier structural changes). Items resolved mid-loop get moved to the backlog's "Resolved this pass" section in Phase 6.
4. Read **both** `references/quality-rubric.md` (scoring criteria) **and** `references/improvement-patterns.md` (concrete before/after patterns by dimension) from the skill-improver directory. Both are non-optional — skipping the patterns file means later iterations propose changes that miss documented techniques (Pattern 8.2 terminology standardisation, Pattern 6.1 redundancy removal, Pattern 9.3 frontmatter fields). Feeling unsure what to try next at any phase is a symptom of skipping this read. **Apply the Boris Alignment Check** (rubric §"Boris Alignment Check") on the baseline — two diagnostic patterns (up-front context dumps, model-version compensation) cap Dims 4 and 9; a third, procedural scaffolding, is advisory only — its step-count cap was withdrawn 2026-08-20. Caps surface as cross-cutting structural issues that should be lifted ahead of cosmetic dim improvements of the same magnitude.
5. Establish a baseline score by evaluating the skill against the rubric.
6. Spawn a blind scoring agent on the baseline (see `SKILL.md` §"Blind Validation" and `references/blind-validation.md`). First snapshot the skill: `cp -a <skill-dir> /tmp/<skill-name>-baseline`. Then run the agent in the background while the loop proceeds. **This is non-optional.** The baseline blind agent is the only check on Phase 1's self-score — without it the entire run rests on whatever bias the loop's self-scoring carries. If the runtime cannot spawn agents, run the same prompt manually in a fresh session and paste back the result before entering Phase 2. Do NOT proceed to Phase 6 without both a baseline AND a final blind score on record.
7. Initialize a results log (in-memory or scratch file) with header: `iteration | score | delta | status | description`.
8. Log iteration 0 as `baseline`.

## Phase 1: Evaluate (Score the Skill)

Score the skill on 10 dimensions (each 0–10, summed to 0–100) using the detailed criteria and scoring template in `references/quality-rubric.md` (loaded in Phase 0).

**Cold-score discipline.** When scoring at any phase, read the current file fresh and assign each dimension against the rubric criteria with no reference to prior iteration scores. Do NOT compute the new score by adding deltas to the old. Delta math hides regressions in dimensions not being watched.

## Phase 2: Hypothesize (Pick One Improvement)

Identify the **single lowest-scoring dimension** (or highest-impact if tied). If the
baseline blind agent has returned with flagged dimensions (2+ gap), use the agent's
specific justification text — not just the number — to inform the hypothesis.
Formulate one specific change:

- What to change and why
- Expected score impact
- Complexity cost (lines added/removed, new files)

Consult `references/improvement-patterns.md` for concrete before/after patterns organized by dimension.

**Check the rejected-edit buffer first.** The run log's discard rows (Phase 5
requires them to carry shape + reason) are this run's rejected-edit buffer.
Do NOT re-propose an edit of the same shape against the same section that a
prior iteration discarded — change the dimension, the section, or the
mechanism. The only exemption: a change kept since the discard has plausibly
removed the reason it failed; if claiming that, name the kept iteration and
the removed reason in the hypothesis.

**Factual-claim hypotheses require a probe.** If the change would alter a
version, date, model name, API, flag, or any other external-world claim, run an
online verification BEFORE mutating (see `SKILL.md` Operating Rules §"The
Skill Outranks Training Data") — the claim is likely newer than the model's
knowledge cutoff, and "fixing" it from memory regresses the skill.

**The simplicity criterion (from autoresearch):** A small improvement that adds ugly complexity is not worth it. Removing something and getting equal or better results is a great outcome. A +1 score that adds 20 lines of noise? Skip. A +1 from deleting redundant content? Keep.

**The weakness criterion (Bennett's razor):** When an edit responds to an
observed failure — a blind-agent flag, a missed trigger, an eval miss — write
it no more specifically than the failure *class* forces. Encoding the literal
failing case (the exact query phrase, the one flag name the eval used) is the
strongest possible hypothesis and the least likely to cover the next unseen
case; held-out test splits exist to punish exactly that. Prefer the weakest
rule that still excludes the observed failure. Weak ≠ short: generalisation
probability scales with what a rule permits, not its brevity
(arXiv:2301.12987), so this is a separate axis from the simplicity criterion.

**Format-only hypotheses are low expected value.** SkillLens (arXiv:2605.23899) measured skill format (ordered list vs prose vs checklist vs unordered) as statistically non-significant on every tested target, while changing what the skill *says* was significant on 5/6 — prefer content hypotheses (mechanism + remedy, blacklists, coverage) over reformatting, renaming, or restructuring-for-looks. (The 2026-07-18 self-run confirmed this empirically: all three format/naming iterations discarded at Δ0.)

## Phase 3: Mutate (Make the Change)

Apply exactly one change per iteration, diff minimal. Do NOT bundle multiple
improvements — bundling attributes the score lift to the wrong cause, so the
next loop pivots to the wrong category.

## Phase 4: Re-evaluate (Score Again)

1. Re-score the skill using the same rubric.
2. Compare to previous best score.
3. Run `wc -l SKILL.md` and compare to the count before the change.

**Line-ceiling gate — applies before the decision rule below.** If the file
now exceeds **500 lines** (the agentskills.io / platform best-practices cap,
`quality-rubric.md` §Dim 2) *and* is longer than it was, the change is a Dim 2
regression **regardless of the total score**: DISCARD it, and log
`discard (line ceiling)` with both counts. A change that keeps the file over
500 while removing lines is fine — the gate is about growth past the ceiling,
not about skills already over it (some legitimately are).

The gate exists because the rubric cannot see this. A real miss: freshen
additions took a SKILL.md 493 → 506, past the spec ceiling, and every
dimension stayed band-internal — only a manual count caught it. Length is
also the defect the cost measurements price directly (`quality-rubric.md`
§Boris Alignment Check): stale bulk cost 36% more per ticket at unchanged
accuracy, and scaffolding that fights the model cost 7-11 accuracy points.
Growth past the ceiling is not a tidiness question.

**Decision rule:**
- **Score improved by +2 or more** → KEEP. Log as `keep`. This is the new
  baseline. On every keep: commit (per `SKILL.md` §Git as State Machine), or —
  when commits are not permitted — snapshot the kept file to the scratch
  directory.
  **Anomaly gate (+5 or more):** A single change that lifts the total by +5
  or more is presumed inflated until proven otherwise. Do NOT rationalize the
  deltas. Instead: open the rubric fresh, read the current file as if it were
  new, and score each dimension cold. If the cold total differs from the
  delta-math total by 2 or more in either direction, the cold score wins.
  Most +5 jumps shrink to +3 under cold rescore — that is the finding, not a
  failure of the change. Log both totals in the iteration row.
- **Score improved by exactly +1 (noise zone)** → a bare +1 is inside
  self-scoring noise — cold rescores routinely move a total by ±1–2, so the +1
  may be the scorer, not the change. If the change also simplifies (net lines
  removed), KEEP as `keep (simplification)`. Otherwise cold-score the affected
  dimension(s) fresh; KEEP only if the +1 reproduces, else revert and log as
  `discard (noise)`. Noise discards count toward the ceiling-mapped stop
  condition like any other discard.
- **Score equal, but simpler** → KEEP. Log as `keep (simplification)`.
- **Score equal or worse** → DISCARD. Revert via `git checkout -- <file>` ONLY if every prior keep is committed; with uncommitted keeps, restore the last kept snapshot instead — a whole-file checkout reverts to git HEAD and silently destroys them. (Not git-tracked: undo the edit.) Log as `discard`. The discard row must name WHAT was tried (change shape + target section) and WHY it failed — discard rows are the rejected-edit buffer Phase 2 consults.
- **Change broke something** → REVERT. Log as `crash`. Fix and continue.

## Phase 5: Log and Loop

1. Append result to the log: `iteration | score | delta | status | description`. Use a single declared score column for trend math — pick `self` OR `blind` and stay with it across iterations. Do NOT mix self-scores and blind-scores in the same delta column to make iterations look bigger; if both are tracked, log them as separate columns side by side and compute deltas within each column.
2. Print a one-line status, e.g.: `[iter 3] score: 74 (+2) — keep — moved API docs to references/api.md`.
3. Go to Phase 2 and pick the next improvement.

**Reflect (every 5 iterations):** Categorize all iterations by type (simplification,
style fix, restructuring, content addition, trigger tuning). If the last 5 were all
the same category, force the next hypothesis to be a different category. Print:
`[reflect] N kept from <category>, pivoting to <new category>`

**Stop conditions:**
- Score reaches 90+ AND no dimension is below 7.
- **Ceiling mapped:** 5+ consecutive discards spanning at least 2 different
  improvement categories. This is not failure — it means the skill is near its
  quality ceiling. Report as a positive finding: which categories were tried,
  what the ceiling is, and what would require the author's input to break through.
- **Structural ceiling claim requires evidence.** "Structural ceiling" stops
  require at least 2 logged discards naming the patterns that were attempted
  and why each failed. A run with zero discards has not mapped any ceiling —
  it has stopped early. Reasoning "the next iteration would just be a
  discard" without actually trying it is the
  cheat. Try it.
- User interrupts.
- 10 iterations completed (default cap; user can override).

**What a stop is NOT:**
- Not "+N feels like enough". The metric drives the loop; subjective comfort
  with the gain does not.
- Not "the score is good and I am tired". Read on.
- Not "Dim X is capped, so further improvement is impossible". Other dims
  may still be liftable. Stop only when the rubric criteria for stopping match.

**On stop:** Spawn a final blind scoring agent (see `SKILL.md` §"Blind
Validation"). Print both comparison tables (baseline + final) and the overall
results summary.

## Phase 6: Persist the backlog

Before declaring the run done, update `<skill>/references/improvement-backlog.md`
(create the file if absent). This is non-optional — ceiling findings that exist
only in chat disappear when the session ends.

The two sections and their admission rules — what qualifies as **Open**
(attempted, could not be applied in one iteration; not a wishlist), what
counts as **Resolved this pass** (a mutation the metric registered; not a
placeholder file), the carry-forward marker, and the append-only rule that
preserves prior passes' discard rationales — live in
**`references/backlog-format.md`**. Read it before writing the file.

## Phase 7: Land it

A pass is not done when the score moves. It is done when the work is applied,
verified, committed, and the record updated — in that order, with nothing left
staged for a later session.

**Definition of done.** All five, or the pass is unfinished:

1. Every keep is applied to the real files (not a scratch copy, not a diff).
2. Both blind scores are on record — baseline and final. A run reporting one
   of them has no bias check and its trend is self-scored.
3. Committed through the repo's own hook sequence, with the backlog update in
   the **same** commit. A backlog that lands a commit later describes a state
   that never existed.
4. Anything the pass resolved is **deleted** from Open, not ticked. The diff is
   the record.
5. Every unblocked item the pass surfaced is done, not filed
   (`backlog-format.md` §"The admission test").

**A pass ends with work, not with a report of work.** Findings named only in
the run summary are gone with the session; the same finding written into the
target's files or a commit message survives. If the choice is between one more
paragraph of explanation and one more applied fix, apply the fix.

**Stopping short is a legitimate outcome, but say which kind.** Three endings
look identical in a summary and are not: *ceiling mapped* (5+ discards across
2+ categories — the skill is near its limit), *cap reached* (10 iterations),
and *stopped early* (scope, budget, or an operator interrupt). Only the first
is evidence about the skill. A run with **zero discards has not mapped a
ceiling** — name it as stopped early, in the backlog, so the next pass does not
inherit a false "this skill is done".
