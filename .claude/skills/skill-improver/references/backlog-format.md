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

### The admission test: name the absent thing

Before writing ANY Open entry, answer in one clause: **what, specifically,
that is not here right now, prevents doing this?** A valid answer names a
missing thing — an operator ruling, a credential, an unreleased upstream
version, a live system to test against, a measurement run nobody can do in
this pass. "Larger than one iteration", "a lot of edits", "didn't fit the
rule I was applying", "ran out of scope" are NOT answers. They describe
effort, and effort is not a blocker.

**If the honest answer is "nothing, it is just work" — do it, in this pass,
before the pass ends.** Mechanical volume is not a reason to defer; the
one-change-per-iteration rule exists so score movement stays attributable,
not to cap how much a pass may fix.

**A pass may not end having ADDED an unblocked item.** Renaming the section,
qualifying it ("available to the next pass", "not a blocker"), or filing it
under a different heading does not change what it is. If the item would be
actionable by the next person with no new information, it is actionable now.

### Drain duty

Phase 0 reads Open. That read is not just to avoid re-proposing — **it is to
check whether anything there has become unblocked.** When the named absent
thing has arrived (the release shipped, the ruling came, the measurement
exists), that item is this pass's work, ahead of a fresh hypothesis of equal
size. Delete it from Open when done; the diff is the record. Ticking it in
place is how a list grows without ever shrinking.

**Why this is enforced rather than advised.** Open counts across the fleet do
not fall — they sit flat or rise across successive passes, and "Resolved this
pass" becomes a changelog of whatever that session happened to do rather than
the Open list being worked off. This skill's own target proved the cost:
`netbox-best-practices` carried a `when_to_use` split from 2026-06-12
described as "spec-preferred but cosmetic today; do it next description
edit". Nothing was absent — it was a two-minute frontmatter edit. It sat for
69 days while `description` grew from 866 to 1,070 chars, crossed the
1,024-char spec hard max, and hard-capped Dim 9 at 3. A deferred cosmetic item
became the skill's single worst dimension by doing nothing at all.

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
