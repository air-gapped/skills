# Blind Validation — Scorer Agent, Model Rule, Comparison Format

The mechanics of the blind scoring pass described in `SKILL.md` §"Blind
Validation". Load when spawning a baseline or final blind scorer.

## Table of Contents
- [The scorer agent and prompt tail](#the-scorer-agent-and-prompt-tail)
- [Model selection](#model-selection)
- [Parallel scoring (dynamic workflows)](#parallel-scoring-dynamic-workflows)
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

It reads all three benchmark shapes in the fleet — a flat `delta_pass_rate`, a
`delta` object whose children are the deltas, and either encoded as a string
(`"+0.19"`). A benchmark whose delta it cannot find yields the unmeasured cap of
8 rather than a guess, so a schema it does not know fails toward "not measured".

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
