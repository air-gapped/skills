# Edge Cases and Boundaries

The standard method assumes a deviation caused by a discrete change acting
through a distinction. Four situations break that assumption; each has its
own move. Recognizing which one you're in is most of the battle.

## Day One deviations — it never worked

"That unit was never any good from the day it came online." ACTUAL has been
below SHOULD since the start, often as a *degree* shortfall (the twin server
that runs 30% slower, the link that never hits line rate).

**The move:** there is no change to find, so the change-hunt is wasted
effort. The search lives *entirely in distinctions*: line the broken thing up
against a working sibling and enumerate every difference, however trivial —
slot population, firmware, cable path, BIOS defaults, build order, who
racked it. Assume the "identical" twin is not identical; the analysis exists
to find where. If no sibling exists, the comparison is against the design
spec itself, checked assumption by assumption.

Pitfall: teams burn days asking "what changed?" about a system where nothing
ever changed — it was born this way. The WHEN row tells you early: if "first
observed" ≈ "first commissioned", switch modes.

## Gradual drift — it faded, not broke

Problems that arrive "like fog": throughput sagging over months, error rates
creeping. There is no sharp onset, and that creates a specific trap: people
seize the most *visible* recent change (the new hire, the last deploy) because
a fuzzy WHEN can't acquit anyone.

**The moves:**
- Plot the trend and estimate onset from data, not memory; a gradual curve
  often has a knee that memory smoothed over.
- Lean on WHERE/EXTENT comparisons instead of WHEN: what is distinctive about
  the affected instance vs. unaffected peers *right now*?
- For candidate causes, verify by **timeline correlation**: when did the
  metric start moving, when did the suspected condition start, what lag would
  the mechanism predict, and does the observed lag match?
- Consider slow-accumulation mechanisms explicitly: leaks, fragmentation,
  filling disks, cert/token aging, thermal dust, database bloat — causes that
  *are* changes, just continuous ones.

## Intermittent faults — it comes and goes

The hardest class: cheap-test loops fail (can't reproduce on demand) and
naive specification fails (the fault hides between observations).

**The moves:**
- Specify **occurrences vs. non-occurrences** — the IS-NOT is the quiet
  periods. What is different about the minutes/requests/temperatures when it
  fires vs. when it doesn't? Bin the events and hunt the pattern (load,
  time-of-day, concurrency, temperature, specific input shapes).
- **Instrument first, then wait.** Since you can't summon the fault, arrange
  to capture it in flight: extra logging around the suspected path, packet
  capture on a ring buffer, `ftrace`/counters, a camera on the LED. The
  investment decision is one instrumented occurrence vs. N more anecdotes —
  anecdotes lose.
- **Never trust a quiet interval as proof of fix.** Verification requires
  silence over several times the longest previously-observed gap between
  occurrences — state the window explicitly before declaring victory.
- Component swaps are weak evidence here (the fault may just be dormant);
  reversal-and-recurrence is correspondingly strong.

## Multi-causal and systemic problems — the model itself is wrong

Some failures have no single dominant cause: multiple necessary contributors,
emergent interactions, organizational drift. Signs you're there:

- Every single-cause candidate keeps failing the paper test even after the
  spec is tightened twice.
- The "cause" list keeps growing conditions ("only under load AND after
  failover AND when the cache is cold") — that conjunction may *be* the
  answer: several contributors, jointly sufficient.
- The deviation is in human/process performance, or the incident is over and
  the goal is learning, not repair.

**The moves:** for live repair, it is legitimate to fix the most tractable
contributor and verify the symptom stops — say clearly that you removed *a*
necessary contributor, not *the* root cause. For understanding and
prevention, stop cause-hunting and hand off: systemic analysis
(`understanding-human-error` for the blame-free investigation frame) is a
different activity with different rules. Cause-hunting language is a fine
tool at the console and a poor one in the retrospective.

## Boundary map — when this skill is the wrong tool

| Situation | Better frame |
|---|---|
| Incident resolved; team wants lessons | Retrospective / `understanding-human-error` |
| Output wobbles statistically, no discrete failure | SPC / designed experiments (variation problem) |
| Choosing between options, nothing is broken | Decision analysis: objectives, must/want, risks |
| Protecting an upcoming change from failure | Pre-mortem: what could go wrong, prevention + contingency triggers |
| Requirement was never defined ("is this slow?") | Define SHOULD first — without a standard there is no deviation |
| Code bug with cheap perfect reproduction | Just bisect/debug; the spec table adds ceremony (its ideas — one change at a time, refute don't confirm — still apply) |
