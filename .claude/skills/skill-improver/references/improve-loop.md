# The Improvement Loop — Phase Workflow (Phases 0–7)

Full phase workflow for `improve` mode (the default). Cross-cutting rules (rules for every mode, blind validation spawn mechanics) stay in `SKILL.md`.

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

1. Identify the target skill. Accept a path, or run `scripts/scan-skills.sh` (or Glob `**/SKILL.md` under `~/.claude/skills/` and `.claude/skills/`). Do NOT search `~/.claude/plugins/` — managed externally.
2. Read `SKILL.md`, then list the directory. Open a `references/`, `scripts/`, `examples/` or `assets/` file only when a phase needs it (Phase 1 needs the reference files, Phase 2 whichever the hypothesis targets). Do not read the whole tree up front.
3. **Read `<skill>/references/improvement-backlog.md` if it exists.** It carries open ceiling-hit items from prior runs. Do NOT re-propose a listed item unless new evidence shows the ceiling is now breakable in one iteration. Items resolved mid-loop move to the backlog's "Resolved this pass" section in Phase 6.
4. Read **both** `references/quality-rubric.md` and `references/improvement-patterns.md` from the skill-improver directory. Both are mandatory; skipping the patterns file misses documented techniques (Pattern 8.2 terminology standardisation, Pattern 6.1 redundancy removal, Pattern 9.3 frontmatter fields). Feeling unsure what to try next is a symptom of skipping this read. **Apply the Boris Alignment Check** (rubric §"Boris Alignment Check") to the baseline: up-front context dumps and model-version compensation cap Dims 4 and 9; procedural scaffolding is advisory only (no cap). Lift caps ahead of cosmetic dim improvements of the same magnitude.
5. Establish a baseline score against the rubric. **Run `python3 ${CLAUDE_SKILL_DIR}/scripts/eval-evidence.py <skill-dir>` first** and take Dim 10's cap from it; do not judge it yourself. It also reports case count and noise floor. A new skill usually has **no** eval set (cap 8, correct, nothing to fix); one with 3 cases resolves nothing under 0.33 and is worse than none. State which of the two it is in the baseline; when the corpus is thin, name `scripts/grow-evals.py` as the fix. Applies on every scoring run.
6. Spawn a blind scoring agent on the baseline (`SKILL.md` §"Blind Validation", `references/blind-validation.md`). First record the baseline commit, `BASE=$(git rev-parse HEAD)` (the `<baseline-ref>` for the A/B comparator and `outcome --against`), then snapshot: `SNAP=$(mktemp -d -t <skill-name>-baseline.XXXX) && cp -a <skill-dir>/. "$SNAP"`. Run the agent in the background while the loop proceeds. **Mandatory** — it is the only check on Phase 1's self-score. If the runtime cannot spawn agents, run the same prompt in a fresh session and paste the result back before Phase 2. Do NOT proceed to Phase 6 without both a baseline AND a final blind score on record.
7. Initialize a results log (in-memory or scratch file), header: `iteration | score | delta | status | description`.
8. Log iteration 0 as `baseline`.

## Phase 1: Evaluate (Score the Skill)

Score 10 dimensions (each 0–10, summed to 0–100) using the criteria and template in `references/quality-rubric.md`.

**Cold-score discipline.** At every scoring, read the current file fresh from disk — never the context-injected copy of a loaded skill (`${CLAUDE_SKILL_DIR}` appears pre-expanded there and reads as a false inconsistency). Assign each dimension against the rubric with no reference to prior scores. Do NOT compute the new score by adding deltas to the old.

## Phase 2: Hypothesize (Pick One Improvement)

Identify the **single lowest-scoring dimension** (highest-impact if tied). If the baseline blind agent flagged dimensions (2+ gap), use its justification text, not just the number. Formulate one change:

- What to change and why
- Expected score impact
- Complexity cost (lines added/removed, new files)

Consult `references/improvement-patterns.md` for before/after patterns by dimension.

**Check the rejected-edit buffer first.** The run log's discard rows (Phase 5) are this run's rejected-edit buffer. Do NOT re-propose an edit of the same shape against the same section that a prior iteration discarded — change the dimension, section, or mechanism. Exemption: a change kept since the discard has plausibly removed the reason it failed; then name the kept iteration and the removed reason in the hypothesis.

**Factual-claim hypotheses require a probe.** If the change alters a version, date, model name, API, flag, or other external-world claim, verify online BEFORE mutating (`SKILL.md` §"Rules for every mode" (the skill outranks training data)). Never "fix" such a claim from memory.

**The simplicity criterion:** a small improvement that adds ugly complexity is not worth it. Removing something for equal or better results is a great outcome. +1 that adds 20 lines of noise: skip. +1 from deleting redundant content: keep.

**The weakness criterion (Bennett's razor):** when an edit responds to an observed failure (blind-agent flag, missed trigger, eval miss), write it no more specifically than the failure *class* forces. Do not encode the literal failing case (the exact query phrase, the one flag name the eval used). Prefer the weakest rule that still excludes the observed failure. Weak ≠ short; this is a separate axis from the simplicity criterion.

**Format-only hypotheses are low expected value.** Skill format (ordered list vs prose vs checklist) is non-significant; changing what the skill *says* is significant. Prefer content hypotheses (mechanism + remedy, blacklists, coverage) over reformatting, renaming, or restructuring-for-looks.

## Phase 3: Mutate (Make the Change)

Apply exactly one change per iteration, diff minimal. Do NOT bundle improvements — bundling attributes the lift to the wrong cause.

## Phase 4: Re-evaluate (Score Again)

1. Re-score using the same rubric.
2. Compare to the previous best score.
3. Run `wc -l SKILL.md` and compare to the count before the change.

**Line-ceiling gate — applies before the decision rule.** If the file now exceeds **500 lines** (`quality-rubric.md` §Dim 2) *and* is longer than before, the change is a Dim 2 regression **regardless of total score**: DISCARD and log `discard (line ceiling)` with both counts. A change that keeps the file over 500 while removing lines is fine.

**Decision rule:**
- **Score improved by +3 or more** → KEEP, log `keep`; this is the new baseline. On every keep: commit (`SKILL.md` §"Rules for every mode"), or, when commits are not permitted, snapshot the kept file to scratch.
  **Anomaly gate (+5 or more):** presumed inflated. Do NOT rationalize the deltas. Open the rubric fresh, read the file as if new, score each dimension cold. If the cold total differs from the delta-math total by 2 or more either way, the cold score wins. Log both totals in the iteration row.
- **Score improved by exactly +2 (undecided)** → inside the scorer's noise (`blind-validation.md` §Measured scorer behaviour). KEEP if the change also simplifies (net lines removed), fixes a verifiable defect (defined below), or a second full cold score also lands +2 or more; otherwise revert, log `discard (noise)`.
- **Score improved by exactly +1 (noise zone)** → if the change also simplifies (net lines removed), KEEP as `keep (simplification)`; if it fixes a verifiable defect, KEEP as `keep (defect)`. Otherwise cold-score the affected dimension(s) fresh; KEEP only if the +1 reproduces, else revert, log `discard (noise)`. Noise discards count toward the ceiling-mapped stop condition.
- **Score equal, but simpler** → KEEP, log `keep (simplification)`.
- **Score equal, but fixes a verifiable defect** → KEEP, log `keep (defect)`. Verifiable = checkable without judgement: a mode or command with no dispatch, a reference to a section or script that does not exist, a rule whose scope provably misses a case that already caused a wrong decision. A wording or emphasis preference is not a defect — discard.
- **Score equal or worse** → DISCARD. Revert via `git checkout -- <file>` ONLY if every prior keep is committed; with uncommitted keeps, restore the last kept snapshot (a whole-file checkout reverts to git HEAD and destroys them). Not git-tracked: undo the edit. Log `discard`. The discard row must name WHAT was tried (change shape + target section) and WHY it failed.
- **Change broke something** → REVERT, log `crash`, fix and continue.

## Phase 5: Log and Loop

1. Append to the log: `iteration | score | delta | status | description`. Pick ONE declared score column (`self` OR `blind`) for trend math and keep it across iterations. Never mix self- and blind-scores in one delta column; if both are tracked, log separate columns and compute deltas within each.
2. Print a one-line status, e.g. `[iter 3] score: 74 (+2) — keep — moved API docs to references/api.md`.
3. Go to Phase 2.

**Reflect (every 5 iterations):** categorize all iterations by type (simplification, style fix, restructuring, content addition, trigger tuning). If the last 5 were one category, force the next hypothesis into a different one. Print: `[reflect] N kept from <category>, pivoting to <new category>`

**Stop conditions:**
- Score reaches 90+ AND no dimension is below 7.
- **Ceiling mapped:** 5+ consecutive discards spanning at least 2 different improvement categories, **and** one widened pass has been tried since the last keep. Report as a positive finding: categories tried, what the ceiling is, what would need the author's input to break through.

  **Widen before declaring the ceiling.** On hitting the discard run, do one pass that generates 3-4 candidate edits across *different* dimensions, compares them against each other and the discard rows, and applies the most promising one. If that pass also discards, the ceiling claim is earned. Then return to one-at-a-time.
- **Structural ceiling claim requires evidence.** It requires at least 2 logged discards naming the patterns attempted and why each failed. A run with zero discards has not mapped a ceiling — it stopped early. Do not reason "the next iteration would just be a discard"; try it.
- User interrupts.
- 10 iterations completed (default cap; user can override).

**What a stop is NOT:**
- Not "+N feels like enough" — the metric drives the loop.
- Not "the score is good and I am tired" — read on.
- Not "Dim X is capped, so further improvement is impossible" — other dims may still be liftable.

**On stop:** spawn a final blind scoring agent (`SKILL.md` §"Blind Validation"). Print both comparison tables (baseline + final) and the overall results summary.

Then run the **A/B comparator** — it, not the score delta, decides whether the pass stands. Follow **`references/blind-validation.md`** §"The A/B comparator" step for step (a bare `git archive` pair is not blind). Report the verdict alongside the totals; never report a lift the comparator did not confirm. On `REGRESSED` (outranks a positive delta), revert the iteration its `reasons` identify and re-run this step.

## Phase 6: Persist the backlog

Before declaring the run done, update `<skill>/references/improvement-backlog.md` (create if absent). Mandatory — findings left only in chat are lost.

Admission rules for **Open** (attempted, could not be applied in one iteration; not a wishlist) and **Resolved this pass** (a mutation the metric registered; not a placeholder file), the carry-forward marker, and the append-only rule live in **`references/backlog-format.md`**. Read it before writing the file.

## Phase 7: Land it

A pass is done only when the work is applied, verified, committed, and the record updated, in that order, with nothing left staged for a later session.

**Definition of done.** All of these, or the pass is unfinished:

1. Every keep is applied to the real files (not a scratch copy or diff).
2. Both blind scores are on record — baseline and final — and the A/B comparator verdict.
3. Committed through the repo's own hook sequence, with the backlog update in the **same** commit.
4. Anything the pass resolved is **deleted** from Open, not ticked.
5. Every unblocked item the pass surfaced is done, not filed (`backlog-format.md` §"The admission test"). Items still open when the iteration cap hits are applied after the loop, outside the score accounting, before landing.
6. When the target skill has `evals/evals.json`: an `outcome` run (`scripts/outcome-eval.py <skill-dir> --against <baseline-ref>`) has been made. If the pass proved an assertion stale (verified against the primary source), correct the assertion first — both versions are graded against the same current `evals.json`, so a stale assertion scores the fix as a loss. A fix made after the outcome run is checked by re-running only the affected cases (`--case`); `benchmark.plugin-eval.json` keeps the last full run, and the case re-run goes in the backlog entry.

**A pass ends with work, not a report of work.** Put findings in the target's files or a commit message, not only the run summary. Prefer one more applied fix over one more paragraph of explanation.

**Name the kind of stop:** *ceiling mapped* (Phase 5 stop conditions), *cap reached* (10 iterations), or *stopped early* (scope, budget, operator interrupt). Only the first is evidence about the skill. A run with **zero discards has not mapped a ceiling** — record it in the backlog as stopped early.
