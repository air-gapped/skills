# Backlog Format — What Goes in improvement-backlog.md

The section shapes and admission rules for `<skill>/references/improvement-backlog.md`,
written in Phase 6 of the improve loop (`SKILL.md` §"Phase 6: Persist the backlog").
Load when writing or rewriting a target skill's backlog.

## Table of Contents
- [Open](#open) — attempted-but-unapplied issues
- [Resolved this pass](#resolved-this-pass) — what the metric registered
- [File shape and carry-forward](#file-shape-and-carry-forward)

## Open

Every issue the loop **actually attempted** as a hypothesis and
could NOT apply in a single iteration (multi-file restructure, author-only
domain content, flagged-for-review findings from freshen, or rule-ceiling
discards). For each entry:
- one-line title
- dimension number it affects (e.g. "Dim 2" or "Dim 6/8")
- specific file:line pointer OR the exact file-set that would need to change
- why skill-improver couldn't apply it in one iteration (e.g. "9-file split",
  "requires author-authored error-handling content", "breaks
  self-consistency without restructure")
- enough context to act on without re-running the baseline scoring

**Open is NOT a wishlist.** Hypothetical-future-risk items ("description is
8 chars from cap, might overflow someday"; "this trigger keyword could
become ambiguous if X happens") do NOT belong in Open. The bar is: the loop
proposed this iteration, attempted or planned the mutation, and the
mutation could not be applied. If it was never tried, leave it out. If
tomorrow's edits would naturally surface it, leave it out. Open is a
work-not-done log, not a worry list.

## Resolved this pass

One-line audit of what was fixed. Move items from
"Open" to "Resolved" if a prior backlog listed them and this run closed them.

**What "Resolved" means:** the iteration applied a real mutation that the
metric registered. Creating a placeholder file (e.g., empty `sources.md`
with no `Last verified:` dates) does NOT resolve a Dim 9 staleness cap —
the cap stays. Log such cases as Open with action "run freshen mode", not
Resolved. Hand-waving that "the structure now exists" is theater.

## File shape and carry-forward

Format: plain markdown, `## Open` and `## Resolved this pass` as top-level
sections, in the target skill's own `references/improvement-backlog.md` (not
skill-improver's). Keep the shape uniform across runs so future loops can diff.

If the backlog already exists with items skill-improver chose not to fix this
run, carry them forward into the new "Open" section with a `(carried YYYY-MM-DD)`
marker so staleness is visible.

**The backlog is append-only history, not a status page.** When rewriting it,
never drop prior passes' "Resolved" sections or discard rationales — keep them
as dated `## Resolved — YYYY-MM-DD` sections below the current pass. Discard
rationales are anti-re-proposal guards: a future loop that can't see "tried X,
judged net-negative" will re-propose X. Git keeps the bytes, but loops read the
live file, not git history.

If the run produced zero ceiling findings (converged cleanly at ≥90/100),
still update the file — strip "Open" to empty and record the final score under
"Resolved this pass" so the file remains a truthful record.
