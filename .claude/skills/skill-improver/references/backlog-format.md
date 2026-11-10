# Backlog Format — What Goes in improvement-backlog.md

Section shapes and admission rules for `<skill>/references/improvement-backlog.md`
(the target skill's own file, not skill-improver's), written in Phase 6 of the improve loop
(`improve-loop.md` §"Phase 6: Persist the backlog"). Load when writing or rewriting a target skill's backlog.

## Table of Contents
- [Open](#open) — only what no agent in the session can obtain
- [Resolved this pass](#resolved-this-pass) — what the metric registered
- [File shape and carry-forward](#file-shape-and-carry-forward)

## Open

One entry per thing **no agent in this session can obtain**. Nothing else is filed.

| Valid blocker | The entry names |
|---|---|
| an upstream version not yet released | the version, and where its release will show |
| hardware or an endpoint that was probed and is not reachable | the probe that ran and what it returned |
| a credential | which one, and the call that needs it |
| a real-money purchase | what, and its price |
| usage above the spend ceiling | the measurement, its computed cost (calls × rate, or agents × model), and what its result would change |

Each entry: one-line title · dimension affected ("Dim 2", "Dim 6/8") · file:line or the file set
that would change · the blocker · the command or purchase that unblocks it · enough context to act
without re-running the baseline scoring.

### The spend ceiling

A measurement nobody asked for runs unprompted only when its computed cost is at most **$5 at list
rates** (about 100 probe calls, or one Sonnet worker). Above that it is filed with its price, and the
user decides. Compute the cost before deciding, never after: queries × runs × measurements, or
agents × expected turns. A measurement the user asked for runs at whatever budget they set.

### The admission test: name the absent thing

**Before filing, write the command or purchase that would unblock it. If that command can run now,
run it instead.**

Never filed — do the right-hand column in this pass:

| Claimed blocker | Do this instead |
|---|---|
| "needs an operator decision / ruling" | decide with the best default, apply it, record the choice and its reason under `## Decided` |
| "single reporter", "unconfirmed", "needs a second source" | read the cited code at the release tag. Confirmed in code: write it into the skill text, marked as an unconfirmed upstream report. File only a claim that reading cannot settle, naming the runtime fact that is missing |
| "no fix PR" | run the three probes in `freshen-patterns.md` §3.0a first |
| usage cost at or under the spend ceiling | state the spend and run it |
| "large", "tedious", "out of this pass's scope", "more than one iteration" | do it; the one-change rule keeps score movement attributable, it is not a cap on how much a pass fixes |
| "a live endpoint / real hardware / a test instance", not yet probed | probe the operator's environment: forwarded services and hosts entries, the device inventory, what monitoring already scrapes. Reachable: run the test |
| "live-verify CLI subcommand X" | read X's source at the pinned tag; a thin wrapper (one API call, no branch on instance state) is settled by the code |
| a hypothetical future risk, or a change never attempted | leave it out |

**A pass may not end having ADDED an unblocked item.** Renaming the section, qualifying it
("available to the next pass", "not a blocker"), or filing it under another heading changes
nothing. Actionable by the next person with no new information means actionable now.

### Drain duty

Phase 0 reads Open to check whether anything there has become unblocked, not only to avoid
re-proposing. When the named absent thing has arrived (release shipped, endpoint reachable, credential
issued, purchase made), that item is this pass's work, ahead of a fresh hypothesis of equal size. Delete it from
Open when done; the diff is the record. Never tick it in place.

## Resolved this pass

One-line audit of what was fixed. Move items from Open to Resolved if a prior backlog listed them
and this run closed them. Evidence, numbers, iteration tables and how a fix was found go in the
commit body, not here.

| Kind | Length |
|---|---|
| Fixed item | one line |
| Pass summary | one line — date, blind baseline → final, comparator verdict, commit |
| Kept iteration that made two changes | one line that says so — its score delta belongs to neither change (`confounded`), so the next pass re-tests each alone |
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
Run `freshen` instead; it is not an Open item.

## File shape and carry-forward

Plain markdown; `## Open` and `## Resolved this pass` as top-level sections, plus `## Decided` for
choices the pass made instead of filing (one line each: decision, reason, re-open condition).
Keep the shape uniform across runs so loops can diff.

An existing Open item whose blocker is still absent is carried with a `(carried YYYY-MM-DD)`
marker. One that fails the admission test is done, moved to `## Decided`, or deleted — never carried.

**Keep the discards, drop the diary.** A discard rationale ("tried X, judged net-negative because
Y") stays, under `## Discard guards`: a loop that cannot see it re-proposes X. What a past pass
resolved is in git; delete those sections when rewriting the file.

Zero ceiling findings (converged cleanly at ≥90/100): still update the file — empty "Open" and
record the final score under "Resolved this pass".
