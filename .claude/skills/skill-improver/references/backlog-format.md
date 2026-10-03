# Backlog Format — What Goes in improvement-backlog.md

Section shapes and admission rules for `<skill>/references/improvement-backlog.md`
(the target skill's own file, not skill-improver's), written in Phase 6 of the improve loop
(`improve-loop.md` §"Phase 6: Persist the backlog"). Load when writing or rewriting a target skill's backlog.

## Table of Contents
- [Open](#open) — attempted-but-unapplied issues
- [Resolved this pass](#resolved-this-pass) — what the metric registered
- [File shape and carry-forward](#file-shape-and-carry-forward)

## Open

List every issue the loop **actually attempted** as a hypothesis and could NOT apply in a single
iteration (multi-file restructure, author-only domain content, flagged-for-review findings from
freshen, rule-ceiling discards). Each entry:
- one-line title
- dimension number affected (e.g. "Dim 2" or "Dim 6/8")
- file:line pointer OR the exact file-set that would need to change
- why skill-improver couldn't apply it in one iteration (e.g. "9-file split",
  "requires author-authored error-handling content", "breaks self-consistency without restructure")
- enough context to act without re-running the baseline scoring

**Open is NOT a wishlist.** Do not add hypothetical-future-risk items ("description is 8 chars
from cap"; "this keyword could become ambiguous if X"). Admit only a mutation the loop proposed,
attempted or planned this iteration and could not apply. Never tried, or would surface naturally in
tomorrow's edits: leave it out.

### The admission test: name the absent thing

Before writing ANY Open entry, answer in one clause: **what, specifically, that is not here right
now, prevents doing this?** Valid: a missing thing — an operator ruling, a credential, an unreleased
upstream version, a live system to test against, a measurement run nobody can do this pass.
Invalid: "larger than one iteration", "a lot of edits", "didn't fit the rule I was applying", "ran
out of scope" — these describe effort, not a blocker.

**Honest answer "nothing, it is just work": do it in this pass, before the pass ends.** Mechanical
volume is not a reason to defer; the one-change-per-iteration rule keeps score movement
attributable, not a cap on how much a pass may fix.

**A pass may not end having ADDED an unblocked item.** Renaming the section, qualifying it
("available to the next pass", "not a blocker"), or filing it under another heading changes
nothing. Actionable by the next person with no new information means actionable now.

### Drain duty

Phase 0 reads Open to check whether anything there has become unblocked, not only to avoid
re-proposing. When the named absent thing has arrived (release shipped, ruling came, measurement
exists), that item is this pass's work, ahead of a fresh hypothesis of equal size. Delete it from
Open when done; the diff is the record. Never tick it in place.

## Resolved this pass

One-line audit of what was fixed. Move items from Open to Resolved if a prior backlog listed them
and this run closed them. Evidence, numbers, iteration tables and how a fix was found go in the
commit body, not here.

| Kind | Length |
|---|---|
| Fixed item | one line |
| Pass summary | one line — date, blind baseline → final, comparator verdict, commit |
| Discard ("tried X, rejected because Y") | in full — it is the re-proposal guard |

Shape to copy:

```markdown
## Resolved this pass (2026-09-23)

Blind 84 → 86; comparators 2/3 REGRESSED on the lifecycle cut → reverted.
- Discard: cutting symptom-to-cause sentences — they carry value even when the
  model knows the defaults.
- Kept: STS trigger dropped; single SigV4 revert caveat.
```

**"Resolved" means** the iteration applied a real mutation the metric registered. A placeholder file
(e.g., empty `sources.md` with no `Last verified:` dates) does NOT resolve a Dim 9 staleness cap.
Log such cases as Open with action "run freshen mode".

## File shape and carry-forward

Plain markdown; `## Open` and `## Resolved this pass` as top-level sections. Keep the shape uniform
across runs so loops can diff.

Existing backlog with items skill-improver chose not to fix this run: carry them into the new
"Open" section with a `(carried YYYY-MM-DD)` marker.

**Append-only history.** When rewriting, never drop prior passes' "Resolved" sections or discard
rationales; keep them as dated `## Resolved — YYYY-MM-DD` sections below the current pass. Loops
read the live file, not git history, and a loop that can't see "tried X, judged net-negative"
re-proposes X.

Zero ceiling findings (converged cleanly at ≥90/100): still update the file — empty "Open" and
record the final score under "Resolved this pass".
