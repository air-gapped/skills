---
name: analytical-troubleshooting
description: >-
  Structured live troubleshooting for deviation problems: something worked (or
  should work) and now doesn't, and the cause is unknown. Staged method — quick
  likelihood-weighted tests first, escalating to a comparative IS/IS-NOT
  specification with distinctions-and-changes analysis when quick tests fail or
  the search space is large. Influenced by the problem-analysis tradition of
  Kepner & Tregoe. Works whether the user runs the tests (agent directs, user
  executes) or the agent can test directly.
when_to_use: >-
  Use whenever the user wants to troubleshoot, diagnose, or narrow down an
  unexplained fault — "why does X crash / freeze / fail", "works on A but not
  B", "started failing after...", "never worked right", "intermittent",
  "flaky", "heisenbug", "we've tried everything", "help me find the cause" —
  in hardware, servers, networks, Kubernetes, storage, or software. Also use
  mid-conversation when unstructured guess-and-fix has stalled after a few
  failed attempts. NOT for post-incident reviews or postmortems of
  already-resolved incidents (use understanding-human-error), statistical
  process variation, or choosing between design options.
---

# Analytical Troubleshooting

A staged method for finding the cause of a **deviation**: performance that
used to be acceptable (or should be) no longer is, and nobody knows why.

The core discipline: track what the problem **IS** and, with equal care, what
it plausibly **could be but IS NOT**. A cause that explains only the failures
is a guess; a cause that explains the failures *and* the survivals is a
diagnosis. Most troubleshooting failure — human and model alike — comes from
anchoring on the first plausible cause and collecting only confirming
evidence. This method makes that structurally hard to do.

Why structure instead of intuition: the evidence says procedural scaffolding
(tables, gates, checklists) outperforms both raw expertise and good
intentions. Domain-theory knowledge does not predict troubleshooting success;
maintaining evidence discipline and switching strategies does. Your job is to
be the process leader and bookkeeper. When a human partner is involved, they
are the sensors and hands; deliberately keep the roles that way — a
process-leading non-expert asking sharp questions is a proven pattern
precisely because it resists the expert's urge to assume.

## Hard rules (they exist because models measurably break them)

1. **Never invent evidence.** Every fact in the analysis carries a provenance
   tag: `[observed]` (you or the user directly saw it this session),
   `[reported]` (someone said so), or `[assumed]`. If you didn't get it from
   the world, you may not write it as observed. When a test hasn't run yet,
   its result is unknown — not "probably fine".
2. **No fix before a surviving cause.** Do not propose remediation until at
   least one candidate cause has survived the paper test (Stage 4). Quick
   *diagnostic* actions are always fine; "let's just reinstall/replace/reboot
   and hope" is the failure mode this skill exists to prevent. (Exception:
   genuine safety/stop-the-bleeding containment — say explicitly that it is
   containment, not diagnosis.)
3. **Every planned test names its targets.** Before running or requesting any
   test, state which candidate causes it could *refute*. A test that can only
   confirm your favorite hypothesis is close to worthless; forcing the
   refutation question measurably improves diagnosis.
4. **The spec table is the analysis.** Maintain it continuously and re-emit
   the current table whenever it changes materially or the conversation grows
   long. Long sessions silently lose mid-context evidence; the re-emitted
   table is the antidote. For multi-session work, persist it to a file.
5. **If nothing survives, tighten the spec — not the story.** When every
   candidate fails testing, the specification is missing data. Go get more
   facts. Do not relax your standards until a pet theory passes.

## Stage 0 — Triage

Before analyzing anything, make sure you have *one* analyzable problem.

- **Separate.** "The cluster is broken" is usually several deviations.
  Different symptoms, different objects, different timelines → separate
  analyses. Bundled deviations contaminate each other's evidence; splitting
  them is often the single move that unsticks a stalled investigation.
- **Prioritize** multiple deviations by current impact, urgency, and growth
  potential. Fix the bleeding first, analyze the important.
- **Entry gate.** Full analysis is warranted only if all three hold:
  1. There is a real deviation (a SHOULD vs ACTUAL gap you can state).
  2. The cause is unknown.
  3. Knowing the cause matters for acting well (if a rebuild is cheap and
     acceptable, do that — say so honestly).
- **Route non-deviations elsewhere.** Choosing between options is a decision,
  not a problem. Learning from a resolved incident is a retrospective (hand
  off to `understanding-human-error`). Process variation ("yield wobbles
  2–4%") needs statistical methods. See `references/edge-cases.md` for the
  boundary map.

## Stage 1 — Fast path (earn the right to skip the full method)

Most problems don't deserve the full apparatus. Try to win cheaply first —
but under discipline, with a strict exit.

- **Known-fault check:** does the symptom match a known issue, recent
  advisory, or an error message with a well-documented cause? Search first;
  a recognized problem needs recognition, not analysis.
- **Cheap discriminating tests, ordered by probability ÷ cost.** Prefer the
  test that is most likely to hit, cheapest to run, and — best of all —
  splits the possibility space (a half-split beats ten one-at-a-time checks
  in a chain of components; see `references/test-toolkit.md`).
- **One change per test.** Vary one thing, observe, record. Shotgun changes
  destroy the evidence you'll need in Stage 2.
- **Exit condition (count honestly):** after **~3 failed hypotheses**, or when
  the candidate space is clearly large/opaque, or when any single test is
  expensive, slow, risky, or the fault won't reproduce on demand — stop
  guessing and escalate to Stage 2. Log the failed attempts; they become
  IS-NOT data ("we swapped the PSU and nothing changed" is evidence).

The fast path is a privilege, not a default loop. Unbounded guess-and-swap is
exactly the behavior the exit condition exists to interrupt.

## Stage 2 — Specify

Build the comparative specification. This is the heart of the method.

**Problem statement first:** one object + one deviation, stated factually
("`backup job nightly-pg` exits 137 on 3 of 12 VMs since 07-19" — not "backups
are broken"). Test it: if you can already explain the statement, back up to
the thing you *can't* explain. A brief why-chain on the symptom helps strip
explainable layers before specifying.

**The table.** Four dimensions × IS / IS-NOT, plus what distinguishes them:

| | IS | COULD BE, but IS NOT | Distinctions / Changes |
|---|---|---|---|
| **WHAT** — which object, which deviation | | | |
| **WHERE** — where observed; where on the object | | | |
| **WHEN** — first seen; since then (pattern?); when in lifecycle | | | |
| **EXTENT** — how many objects; how bad; how many per object; trend | | | |

Rules that make the table work:

- **IS-NOT is the closest logical comparison**, not "everything else". The
  sibling VM that *didn't* fail, the identical node that stayed up, the time
  window when it *didn't* happen. The closer the comparison, the sharper the
  boundary around the cause.
- **Ask every cell.** An honestly-empty cell ("N/A" or "unknown — need to
  check") is fine; a skipped cell is a hole your favorite theory will hide in.
  Unknown cells are your data-collection shopping list.
- **Tag provenance** per hard rule 1.
- **Then mine it:** for each IS/IS-NOT pair ask *what is distinctive about
  the IS side?* — and for each distinction, *what changed in, on, or around
  it, and when?* Dated changes that line up with the WHEN row are prime
  cause material.

Full question set, worked example, and table-maintenance guidance:
`references/specification.md`. When facts are in logs, compress them first
(the `lessence` skill pairs well) and transcribe findings into cells with
provenance.

**With a human partner:** request facts one dimension at a time — a focused
question set they can actually answer — never a 20-question dump. You keep
the table; they fetch the facts.

## Stage 3 — Hypothesize

Generate **3–5 candidate causes in parallel**, each stated as a **mechanism**,
not a component: not "the switch", but "switch port MTU dropped below tunnel
overhead, so large packets silently fragment and the session stalls". A
mechanism can be tested; a pointed finger cannot.

Sources, in order:
1. **Knowledge and experience** — cast a wide net from what you and the user
   know of systems like this. Fastest when it works.
2. **Distinctions and changes** — derive causes mechanically from the table
   when brainstorming yields nothing plausible, too much, or only candidates
   that fail Stage 4.

Parallel matters: a single cherished hypothesis is the documented anchor-trap.
Keep a live numbered list (H1..Hn) with status (alive / refuted / verified)
and tag every piece of evidence with the hypotheses it bears on.

**Edge cases change the move** (see `references/edge-cases.md`): if the thing
*never* worked ("Day One" deviation), there is no change to find — hunt
distinctions against a working sibling only. If the decline was gradual,
suspect drift and don't seize the most visible recent change. If the fault is
intermittent, specify occurrences vs. non-occurrences over time.

## Stage 4 — Paper test (kill candidates before spending on tests)

For each candidate, walk the full table: *"If H3 is the cause, how does it
explain each IS — **and** each IS-NOT?"*

- A candidate that requires the IS-NOT side to be false is refuted by
  evidence already in hand. Kill it. This is free — no lab time spent.
- A candidate that fits only with extra assumptions survives *provisionally*;
  write the assumptions down. Rank survivors by assumption load: fewest,
  simplest, most reasonable assumptions first.
- The top survivor is the **most probable cause** — a rank, not a verdict.
  Paper never proves; it only prunes.

If *every* candidate dies: hard rule 5 — the spec is missing a distinction or
a change. Collect more facts; consider whether you're holding two bundled
problems (back to Stage 0).

## Stage 5 — Verify in the world

Confirm the most probable cause with the **safest, surest, cheapest, fastest**
real-world check available:

- **Observe** the mechanism in action (capture the packet, watch the counter,
  catch the OOM kill in the log).
- **Experiment**: swap the suspect component, or better, **reverse the
  suspected change** and watch the problem stop — then, ideally, re-apply it
  and watch the problem return (the strongest evidence there is).
- **Fix and monitor** when direct observation is impossible — apply the fix
  that follows from the mechanism and watch the *specific* symptom, over a
  window long enough to be meaningful (for intermittent faults: several times
  the longest observed gap between occurrences).
- When the evidence is destroyed or unreachable, verify the *assumptions*
  the candidate depends on instead.

Physical/production actions belong to the human partner when one is present;
you specify exactly what to do and what result each outcome would imply,
they execute and report. "If you didn't verify it, it isn't fixed" — a fix
that happens to coincide with recovery, unverified, is how the same incident
returns next month.

Close the loop: state the verified cause, the fix, and update the spec table
one last time showing the cause explaining every row. If the analysis
revealed contributing conditions worth systemic attention, note the handoff
to a proper retrospective — don't do it here.

## Escalation and red flags

- **Escalate to the human** after 3 failed *verification* attempts (not paper
  kills — those are progress), or when the surviving cause implies a design
  problem rather than a fault.
- Red flags that mean *return to the method*, spoken by you or the partner:
  "it's probably just X", "let's try reinstalling everything", "must be a
  <vendor> bug" (without a mechanism), proposing a second fix while the first
  is unverified, an IS-NOT cell contradicting a hypothesis everyone still
  likes, three swaps in a row with no new table entries.
- **Proportionality, restated:** severity does not dictate ceremony. A severe
  problem with an obvious verified cause needs no table; a "minor" recurring
  annoyance that has eaten four debugging sessions deserves the full method.

## References

- `references/specification.md` — full question set per dimension, worked
  example, provenance and table-maintenance discipline. Read when entering
  Stage 2.
- `references/edge-cases.md` — Day One deviations, gradual drift,
  intermittent faults, multi-causal/systemic boundaries, handoff map. Read
  when the standard change-hunt feels wrong.
- `references/test-toolkit.md` — test-selection math (probability ÷ cost),
  half-split, families-of-variation pruning, one-variable discipline, delta
  debugging, best-vs-worst comparison. Read when choosing what to test next.
- `references/evidence.md` — why each mechanism is in the skill, with the
  research behind it. Read when curious or when adapting the method.
