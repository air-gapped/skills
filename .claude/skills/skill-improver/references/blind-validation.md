# Blind Validation — Scorer Agent, A/B Comparator, Model Rule, Formats

The mechanics of the blind scoring pass and the A/B comparator pass
described in `SKILL.md` §"Blind Validation". Load when spawning a baseline
or final blind scorer, or the end-of-run comparator.

## Table of Contents
- [The scorer agent and prompt tail](#the-scorer-agent-and-prompt-tail)
- [Model selection](#model-selection)
- [Parallel scoring (dynamic workflows)](#parallel-scoring-dynamic-workflows)
- [The A/B comparator](#the-ab-comparator)
- [Measured comparator behaviour](#measured-comparator-behaviour-2026-08-22-first-live-run)
- [Comparison Table](#comparison-table)

## The scorer agent and prompt tail

The canonical scoring instructions live in the **`blind-scorer` agent
definition** — `.claude/agents/blind-scorer.md` at the repo root, shipped
with the `agent` plugin as `agent:blind-scorer`. Its body is the subagent's
system prompt, which sits in the prompt-cache prefix every scorer in a run
shares (fan-out cache discipline — improvement-patterns Pattern 7.3), and it
restricts the scorer to read-only tools. The spawn prompt carries only the
two variable paths:

```
Score this skill blind per your instructions.
RUBRIC DIR: <skill-improver-dir>/references
TARGET DIR: <target-skill-dir>
```

Spawn with `subagent_type: "blind-scorer"` (project/user agents dir) or
`"agent:blind-scorer"` (plugin install) — `run_in_background: true` for the
baseline (parallel with the loop), foreground for the final (the comparison
table needs the result).

**Cache note — baseline and final never share a prefix.** Subagents use the
5-minute cache TTL even on a subscription (the 1-hour TTL is main-conversation
only), and a full improvement loop runs far longer than that. Do not try to
"keep the scorers warm"; the baseline pays its own prefix write and so does
the final. Where sharing *is* available is **batch mode**: baseline scorers
for different skills spawned concurrently share one prefix, provided agent
type, model, effort, tools, schema, and cwd match across them.

**Fallback when neither agent name resolves:** Read
`.claude/agents/blind-scorer.md` (relative to the skill dir:
`../../agents/blind-scorer.md` — same layout in the repo and in a plugin
install), paste its body above the two-path tail, and spawn a
`general-purpose` agent with that combined prompt. If no subagent mechanism
is available at all, run the combined prompt manually in a fresh session and
feed back the result.

**Sync rule:** the agent definition is the single canonical copy.
`scripts/batch-workflow.js` `legacyBlindPrompt()` carries a self-contained
fallback of the same instructions — when the agent definition changes, update
it in the same commit; a solo-run blind score and a batch-run blind score are
only comparable while they ask for the same checks.

## Measured scorer behaviour (2026-08-20)

The model rule and the frontier floor below rested on a quote plus reasoning
until this sweep. Four skills spanning 77-988 SKILL.md lines, scored blind,
n=3 per cell, via `claude -p --model M --effort E` with this agent body as the
system prompt. Two axes, run in the order the cost doc prescribes: effort on
the current model first, then models at a fixed effort.

**Effort buys nothing.** Opus at low / high / xhigh returned mean totals within
about 3 points of each other per skill, with no consistent direction, and
identical skill rankings at all three levels. Within-cell spread did not shrink
with effort (median 2.5 / 3.0 / 3.0). A scoring pass is *not* the
complex-reasoning workload the platform effort doc's `high` recommendation is
aimed at — inherit the session effort and do not raise it for the scorer.

**The frontier floor is real, and Haiku fails it for a measurable reason.**
At `high`, Haiku was the ONLY model that reordered the skills, and it produced
a 14-point spread across three runs of one unchanged skill. Sonnet, Opus and
Fable all returned the identical ranking. So the floor holds — but on ranking
instability and variance, not on the "shallow justifications" argument, and it
is a *floor*, not a pin: Sonnet and Fable both qualify. Fable was the steadiest
scorer measured (spread median 2, max 3), Opus the harshest.

**Never compare totals across scorer models.** Haiku, Sonnet and Fable all
scored about +5 to +6 points above Opus on the same skills. The same-run
consistency rule above is what makes a run's trend meaningful; this is the
size of the error when it is broken.

**The scorer's noise floor exceeds the loop's keep threshold.** No model tested
held within-cell spread under +/-2: medians were 2-4, maxima 3-6 (14 for
Haiku). A single iteration kept on a bare +2 is therefore inside the
measurement error, which is why SKILL.md now treats a bare +2 as undecided
rather than as a keep. What survives the noise is the *ranking* between
skills, which was stable across every effort level and every model above the
floor.

**Cost, one metered run each at `high`** (netbox-best-practices, first-party
list rates): Haiku $0.23, Sonnet ~$1.14, Opus $1.96, Fable $2.62. Sonnet
preserves the ranking at roughly half Opus's cost and is the cost-effective
choice where only ranking is needed; the Sonnet figure is a floor, its metered
run finished early and under-reports.

**Not measured:** models below Haiku, efforts other than the three above, and
whether ranking stability holds on skills closer together in quality than these
four (spread 68-86). n=3 per cell is thin — the direction of these findings is
solid, the exact numbers are not.

## Model selection

**Model: pinned to Sonnet 5 in the agent definition** — `model: sonnet` in
`.claude/agents/blind-scorer.md` frontmatter. **Omit `model` in the spawn
call.** The pin lives in one place, which is also what makes the same-run
consistency rule below hold by construction rather than by discipline. The one
exception is `batch-workflow.js`'s `legacyBlindPrompt()` fallback: it runs
without the agent definition, so it states the pin explicitly and must be
changed with it.
Chosen on cost, from what the 2026-08-20 sweep actually established
(§Measured scorer behaviour). The sweep proves ONE thing about model choice:
**Haiku is disqualified** — it was the only model to reorder a fixed set of
skills, and it swung 14 points across three runs of one unchanged skill.
Sonnet, Opus and Fable all returned the identical ranking, and their variance
differences (spread medians 4, 3, 2) are a one-to-two point gap at n=3 on four
skills — inside the noise, not a ranking of scorers. Treating that gap as a
finding would be exactly the mistake this sweep caught the loop making.

Given three models that are indistinguishable on the evidence, take the
cheapest: Sonnet at ~$1.14/run against Opus $1.96 and Fable $2.62. **This is a
trial pin, set 2026-08-20** — if blind scores start disagreeing with judgement
in ways Opus did not, that is the signal to re-measure, not to quietly switch
back.

This reverses the 2026-08-15 dynamic-inheritance decision **for the model
only**; effort still inherits. The churn that decision killed was re-pointing a
pin on every release from a marketing label with nothing measured behind it.
This pin has a measured floor under it and a stated reason above it, and
`evals/scorer-sweep.2026-08-20.json` records the harness to re-run before
moving it.

**Known gap:** the effort sweep ran on Opus. Sonnet's own effort curve is
untested, so "effort is flat, inherit it" is an inference here, not a
measurement.

Two constraints still bind:

- **Same-run consistency.** The baseline and final scorers of one run must use
  the same model — the bias-check table and the run's score trend are only
  comparable within one scorer. If the session model changes mid-run, pass the
  baseline scorer's model explicitly to the final scorer.
- **Frontier floor.** Never score with a Haiku-class or smaller model —
  **measured 2026-08-20** (§Measured scorer behaviour): Haiku was the only
  model to reorder a fixed set of skills, and it swung 14 points across three
  runs of one unchanged skill.
  Validation is the loop's hard task — the dim-by-dim justifications are what
  make subsequent iterations targetable — and Boris Cherny's counterintuitive
  observation holds: cheaper-per-token models often use *more* total tokens on
  hard tasks because of correction loops, and shallow justifications cost more
  wasted iterations than they save in per-token spend. If the session runs a
  small model, pass a frontier-tier model explicitly (`model: "opus"` or
  better) instead of inheriting.

**Effort: inherited from the session** (operator decision,
2026-08-16 — the scorer runs with whatever the calling session runs). Omit
any effort field in the spawn call; record the effective effort in the run
log so scores stay interpretable. One caution to surface — not enforce — in
the run log: per the platform effort doc (verified 2026-08-15), a scoring
pass is complex-reasoning work that maps to `high`; if the session is at
`low`, note that the blind scores were produced at low effort.

**Why dynamic replaced the model pin (2026-08-15).** The pin was re-pointed
on every model release — Opus 4.8 (2026-05-28), Fable 5 (2026-06-09), Opus 5
(2026-07-24), Fable 5 again by operator override (2026-08-15) — a
three-file sync edit plus a benchmark-vs-label adjudication each time.
Inheriting the session model removes that churn and follows the operator's
model choice automatically. Cross-pass score trends were never scorer-stable
anyway (three different scorer models across three months of passes); the
comparability the loop actually uses — baseline vs final within one run —
survives under the same-run consistency rule above.

For the baseline agent, copy the original skill to a temp directory first so
the agent scores the unmodified version even if the loop has already started.

## Parallel scoring (dynamic workflows)

**(Fable 5 / Opus 5, Claude Code v2.1.154+.)** When the runtime exposes the
`Workflow` tool AND the user has opted into it, run blind validation as a
workflow: fan out 3 independent scorers in one phase and take the **median per
dimension** — more robust against a single scorer's bias than one agent.
Otherwise spawn one background `Agent` as above. Do NOT spin up a workflow
without the user's explicit opt-in (the keyword "ultracode" — it replaced
"workflow" as the trigger keyword in v2.1.160 — or a direct request in the
user's own words) — a single `Agent` is the default.

## What blinding actually excludes

"Blind" means the scorer has not seen this skill's improvement history — not
merely that a different agent runs the pass. Two directories inside a target
skill carry that history and must not be read:

- **`references/improvement-backlog.md`** — prior final scores and known-issue
  lists. Excluded in the agent definition since the leak was first found.
- **`evals/`** — the same class, found later and easy to miss because the
  directory looks like input data. `benchmark*.json` carries
  `regression_verdict`, `prior_baseline`, and a `why_run` narrative of what
  recently changed; `case-validation.*.json` records which changes were kept and
  discarded and why; `scorer-sweep.*.json` records prior blind TOTALS — in one
  case for four *other* skills, which anchors a scorer that was told "most
  decent skills score 50–70".

`evals/` cannot simply be excluded, because the Negative-Transfer Gate needs one
number out of it. So the directory is off-limits and
**`scripts/eval-evidence.py`** is the only channel: it prints the case count,
every `delta_*` measurement with the JSON path it came from, and the Dim 10 cap
they imply. No verdicts, no prior scores, no assertions.

**The canonical benchmark format is whatever the official
`aggregate_benchmark.py` writes** — `run_summary.<arm>.pass_rate.{mean, stddev,
min, max}` plus `runs[]`. The rubric already mandates that tool, so its output
is the standard; this repo's two hand-rolled `summary.delta_pass_rate` files are
the deviants, not the other way round.

**But the delta is derived from the arms, never read from the file.** The stored
`run_summary.delta.pass_rate` has three defects, all visible in the aggregator's
source: it is written as `f"{delta:+.2f}"` (a string, rounded — a real +0.1875
is stored as `"+0.19"`); it is `configs[0] - configs[1]` by dict insertion order,
so the sign flips if the arms are recorded the other way round; and both sides
use `.get(..., 0)`, so a missing arm becomes 0 and an absent baseline yields a
maximally *positive* delta. That last one is the same coerce-missing-to-zero
failure the trigger and floor probes were fixed for.

Computing `with_skill − without_skill` from the arms fixes all three: full
precision, order-independent, and a missing arm yields no delta instead of a
flattering one. Every shape in the fleet carries the arms, so it is also the
only route that works across all of them. A stored delta that disagrees with the
derived one is reported as a MISMATCH — the file was hand-edited, or written by
a different aggregator than its own arms.

Same principle as the Dim 1 character count: replace a judgement the scorer
would make by reading with a measurement it runs.

## When a scorer does not return a score

A scorer that dies, times out, returns prose without the table, or omits
dimensions has **not scored**. Treat the gap as absent, never as a value:

- **Do not fill it from the self-score.** That is the exact bias blind
  validation exists to remove, reintroduced at the moment the check failed.
- **Do not coerce a missing dimension to 0**, and do not carry forward its
  previous value. A total summed over fewer than 10 dimensions is not
  comparable to a 10-dimension total — report the dimensions that came back
  and mark the **total** `NO SCORE`.
- **Retry once.** If the second attempt also fails, that end of the run has no
  blind score. Record `NO SCORE` and say which end.

The consequence is a stop condition, not a footnote. A pass is done only with
**both** blind scores on record (SKILL.md §Improvement Loop, improve-loop
Phase 7). With one end unscored the pass is **stopped early** — the keeps may
still be sound, but nothing measured them, so it must not be reported as
finished or its delta quoted.

With median-of-3 parallel scoring, report the count that actually returned:
three is the median as designed, two is an average of two and must be labelled
`n=2`, one is a solo score labelled `n=1`, and none is `NO SCORE`. A run that
scored 3 at baseline and 2 at final is comparable only with both counts stated.

## The A/B comparator

The absolute score answers "how good is this?"; the comparator answers "did
this pass help?". They are different questions and the second one is the
pass verdict. Run the comparator once, after the loop stops.

**Why the absolute delta cannot be the verdict.** Scoring the same skill
twice has a measured 2–4 point spread (§"Measured scorer behaviour"), which
is wider than many real passes. A recorded pass kept six correctness fixes,
lifted the self-score 80 → 85, and the blind scorer returned 85 both times —
the improvement was real and the instrument could not see it. A comparator
never has to resolve a delta against that spread; it reads both texts and
picks one.

**Materialise both sides as plain directories.** The comparator must not be
able to date either side, so do not hand it the live git working tree.

```bash
AB=$(mktemp -d) && mkdir -p "$AB/x" "$AB/y"
git archive <baseline-ref> -- <skill-path> | tar -x -C "$AB/x" --strip-components=<n>
git archive HEAD           -- <skill-path> | tar -x -C "$AB/y" --strip-components=<n>
# Delete what would un-blind rather than trusting the agent not to open it.
rm -rf "$AB"/*/evals "$AB"/*/references/improvement-backlog.md
# git archive stamps every file with ITS OWN commit time, so the two sides
# arrive with different mtimes. Equalise them or `stat` orders the pair.
find "$AB" -exec touch -h -d '2000-01-01T00:00:00Z' {} +
```

`<baseline-ref>` is the commit the loop started from, the same ref Phase 0
recorded. Verified 2026-08-22: `git archive` writes no `.git`, but it does
**not** neutralise time — a baseline and a final taken this way came out 13
hours apart, which is a one-command tell. The `touch` line is what closes it.

**Gate the spawn on the check, per directory:**

```bash
for d in "$AB"/x "$AB"/y; do
  printf '%s %s\n' "$(find "$d" -printf '%T@\n' | sort -u | wc -l)" "$d"
done   # each line must start with 1
```

Check each side on its own, not the parent. Running it over `$AB` counts
anything else that landed there — the A/B mapping note is the obvious one —
and reports a spurious `3` while both trees are in fact uniform. That false
alarm happened on the first real run of this procedure. **Keep the mapping
note outside `$AB`**, and gate on the per-directory numbers, because a
blinding failure here is silent: the verdict still comes back, it is just no
longer blind.

**Randomise the order, per spawn.** Assign baseline and final to `DIR A` /
`DIR B` by coin flip and keep a private note of the mapping. Do not label the
directories: `mktemp -d` names are opaque, so leave them as they are rather
than renaming to anything meaningful.

**Spawn three `skill-comparator` agents, majority vote.** Omit `model` — the
agent definition pins it, so every comparator in a run matches by
construction. The vote is over `winner` after mapping A/B back to
baseline/final:

| Votes for final | Verdict | Action |
|---|---|---|
| 3 of 3, or 2 of 3 | `IMPROVED` | Pass stands. Record the margin. |
| any split with 2+ `TIE` | `NO CHANGE` | Pass kept nothing measurable — record it as such rather than claiming a lift. |
| 2 of 3, or 3 of 3, for baseline | `REGRESSED` | Something in the pass made the skill worse. Read `reasons`, revert the responsible iteration, re-run. |

**Both agree on the winner but split high/low `confidence`** is still a
verdict; only `TIE` counts as no change.

**A `REGRESSED` verdict outranks a positive absolute delta.** If the scores
went up and the comparator says the baseline was better, trust the
comparator and find out which iteration did it — that combination is the
exact failure mode the absolute instrument is blind to.

**Check for order bias across runs.** If the comparator picks whichever side
was presented as `A` in most runs, the blinding is not holding. Track it: the
mapping is recorded, so the A-vs-B win rate is checkable at any time and
should sit near 50%.

**Spawn the comparator from outside the repo.** This is the one step that
cannot be fixed by preparing the directories better. A subagent spawned from
a session whose cwd is the repo inherits an environment block listing the
repo's recent commits — and those subjects *describe the diff being judged*
("decide the pass by blind A/B", "expand X's Show more"). Measured on the
first live run: one of three comparators reported exactly that, having
consulted no git command itself. The prepared copies live in a temp
directory and need no repo cwd, so run the comparison as a bare `claude -p`
with cwd set to `$AB` — the same empty-project trick `knowledge-floor.py`
uses to keep a probe parametric. An in-session subagent is a degraded
fallback whose verdict must be recorded as semi-blind.

**`leakage_external` invalidates the run; `leakage_content` does not.**

| Field | What it means | Action |
|---|---|---|
| `leakage_external` | git metadata, mtimes, directory names, caller session context | Close that channel and re-spawn. A verdict from an agent that knew the order is not evidence. |
| `leakage_content` | a `Verified 2026-..-..` stamp or version line *inside the compared text* | Record it and accept the verdict. |

The split exists because the strict version of this rule was unusable. Every
skill here carries freshness stamps, and `sources.md` is nothing but dated
rows — so "any ordering marker invalidates" fails every run on a signal that
cannot be removed without changing the artifact under comparison. Measured on
the first live run: two of three comparators reported a marker, but only one
was a real channel. Redacting in-text dates is not the fix — a freshness stamp
is Dim 9 evidence, so stripping it would hide part of what is being judged.

## Measured comparator behaviour (2026-08-22)

**Head-to-head against the absolute scorer**, on `netbox-best-practices` —
a skill neither instrument's author had edited. Three versions: `base`,
`improved` (structural only: a routing table replacing three trailing "when
to read X" sections, plus an explicit out-of-scope boundary), and `degraded`
(a negative control — longer and smoother than base, with the concrete error
string, the naming convention, the API endpoint, the Dockerfile lines and the
evidence labels all removed). Comparators: 3 per pair, coin-flipped, run via
`claude -p` from outside the repo. Scorer: 2 runs per version.

| Pair | Absolute scorer | Comparator |
|---|---|---|
| base vs improved | 86.5 vs 86.0 → **−0.5** | **3/3 improved**, medium / slight |
| base vs degraded | 86.5 vs 69.5 → **−17.0** | **3/3 base**, high / decisive |

Within-version scorer spread on identical content: **base 88 / 85**. So the
−0.5 on the real edit sits inside the instrument's own noise — the score
cannot tell that pass from no pass, and its sign is negative for a change
three independent judges called an improvement. The −17 shows the scorer is
fine at catching gross damage. **That is the division of labour: the score
catches large regressions, the comparator resolves the small diffs that make
up most passes.**

Two behaviours worth relying on:

- **The fluency trap held.** The degraded version read *better* and was
  *longer*. All three comparators rejected it decisively. A pass that
  smooths prose while dropping mechanisms is the failure mode this rubric
  warns about most, and comparative judgment caught it.
- **Confidence tracks the size of the difference** — medium/slight on the
  modest edit, high/decisive on the degradation — rather than sounding
  certain either way.

What this does **not** establish: one pair per direction, and the "improved"
version was authored by the same party judging the result useful, so the
small-diff pair has no independent ground truth. It shows the comparator
returns a *directional* answer where the score returns noise; it does not
prove that direction is right on a marginal edit. A comparator also flagged a
real regression inside the version it voted for (the routing table dropped
one reference file's usage note) — read `regressions` even on a win.

**Blinding, measured.** An earlier run of this procedure from *inside* the
repo had one comparator in three report the caller's own environment block
listing recent commit subjects — a description of the diff under judgement,
reached without running any git command. Hence the `claude -p`-from-outside
rule above. That same run had another comparator flag the dated stamps inside
the text, which is why `leakage_content` is recorded rather than
disqualifying. Cost: ~3.5 min wall-clock and ~140k tokens per 3-agent pair,
run in parallel.

## Comparison Table

After each blind agent returns, print a side-by-side comparison:

```
## Bias Check: [baseline|final]

| # | Dimension        | Self | Agent | Gap |
|---|-----------------|------|-------|-----|
| 1 | Trigger Prec.   |  6   |   7   |     |
| 4 | Actionability   |  9   |   7   | +2  |
|   | **Total**       | 81   |  78   |     |

[FLAG] Dimension 4: self-score 2+ higher than blind agent.
Agent says: "Steps 3-4 lack specific commands."
→ Re-evaluate this dimension with the agent's justification in mind.
```

Only flag dimensions where the gap is 2 or more. If no flags, print
"No dimensions with 2+ gap. Scores aligned."

The blind score does not override the self-score. It surfaces potential bias
for the improvement loop to address — a flagged dimension becomes a candidate
for the next iteration.
