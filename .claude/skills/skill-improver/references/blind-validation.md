# Blind Validation — Scorer Agent, A/B Comparator, Model Rule, Formats

Mechanics of the blind scoring pass and A/B comparator pass from `SKILL.md`
§"Blind Validation". Load when spawning a baseline or final blind scorer, or
the end-of-run comparator.

## Table of Contents
- [The scorer agent and prompt tail](#the-scorer-agent-and-prompt-tail)
- [Measured scorer behaviour](#measured-scorer-behaviour-2026-08-20)
- [Model selection](#model-selection)
- [Parallel scoring (dynamic workflows)](#parallel-scoring-dynamic-workflows)
- [What blinding actually excludes](#what-blinding-actually-excludes)
- [When a scorer does not return a score](#when-a-scorer-does-not-return-a-score)
- [The A/B comparator](#the-ab-comparator)
- [Comparison Table](#comparison-table)

## The scorer agent and prompt tail

Canonical scoring instructions live in the **`blind-scorer` agent definition**
(`.claude/agents/blind-scorer.md`; plugin name `agent:blind-scorer`). Its body
is the system prompt (shared cache prefix, read-only tools). The spawn prompt
carries only:

```
Score this skill blind per your instructions.
RUBRIC DIR: <skill-improver-dir>/references
TARGET DIR: <target-skill-dir>
```

Spawn with `subagent_type: "blind-scorer"` (project/user agents dir) or
`"agent:blind-scorer"` (plugin install). `run_in_background: true` for the
baseline (parallel with the loop); foreground for the final (the comparison
table needs it).

Baseline and final never share a cache prefix (5-minute subagent TTL; loops run
longer). Do not try to keep scorers warm. Sharing exists only in batch mode:
baseline scorers for different skills spawned concurrently share a prefix when
agent type, model, effort, tools, schema, and cwd match.

**Fallback when neither agent name resolves:** Read
`../../agents/blind-scorer.md` (relative to the skill dir), paste its body above
the two-path tail, spawn a `general-purpose` agent with that prompt. With no
subagent mechanism, run the combined prompt in a fresh session and feed back the
result.

**Sync rule:** the agent definition is the single canonical copy.
`scripts/batch-workflow.js` `legacyBlindPrompt()` carries a self-contained
fallback; update it in the same commit as any agent-definition change.

## Measured scorer behaviour (2026-08-20)

- **Effort buys nothing.** Inherit the session effort; do not raise it for the scorer.
- **Frontier floor.** Haiku reordered skills and swung 14 points across three runs of one unchanged skill. Sonnet, Opus and Fable returned identical rankings. The floor is not a pin: Sonnet and Fable both qualify.
- **Never compare totals across scorer models.** Haiku, Sonnet and Fable scored about +5 to +6 above Opus on the same skills.
- **Noise floor exceeds the keep threshold.** Within-cell spread was medians 2-4, maxima 3-6 (14 for Haiku), so a bare +2 is undecided, not a keep. Rankings between skills are stable above the floor.
- **Cost per run at `high`:** Haiku $0.23, Sonnet ~$1.14 (a floor, under-reported), Opus $1.96, Fable $2.62. Sonnet preserves ranking at about half Opus's cost.
- **Not measured:** models below Haiku, other efforts, skills closer together than spread 68-86. n=3 per cell: direction solid, exact numbers not.

## Model selection

**Model: pinned to Sonnet 5 in the agent definition** (`model: sonnet` in
`.claude/agents/blind-scorer.md` frontmatter). **Omit `model` in the spawn
call.** The pin lives in one place, so same-run consistency holds by
construction. Exception: `batch-workflow.js` `legacyBlindPrompt()` runs without
the agent definition, states the pin explicitly, and must change with it.

- The pin outranks `CLAUDE_CODE_SUBAGENT_MODEL` but **not**
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, which overrides agent-definition and
  per-spawn models. With it set, both scorers land on the forced model:
  same-run consistency survives, the Sonnet pin does not, and totals are not
  comparable with any other run. Check `scripts/run-cost.py` (reports the model
  each scorer ran on) before quoting a score.
- A new frontier release does not move the pin. Only the re-measurement signal
  does: if blind scores start disagreeing with judgement in ways Opus did not,
  re-measure with the harness in `evals/scorer-sweep.2026-08-20.json`; do not
  quietly switch back.
- Sonnet, Opus and Fable are indistinguishable on the evidence; take the cheapest. Do not read their variance differences as a ranking of scorers.

Constraints:

- **Same-run consistency.** Baseline and final scorers of one run use the same
  model. If the session model changes mid-run, pass the baseline scorer's model
  explicitly to the final scorer.
- **Frontier floor.** Never score with a Haiku-class or smaller model: shallow
  justifications cost more wasted iterations than they save. If the session runs a
  small model, pass a frontier-tier model explicitly (`model: "opus"` or
  better).

**Effort: inherited from the session.** Omit any effort field in the spawn
call; record the effective effort in the run log. If the session is at `low`,
note in the run log that the blind scores were produced at low effort.
Sonnet's own effort curve is untested.

For the baseline agent, copy the original skill to a temp directory first so
it scores the unmodified version even if the loop has started.

## Parallel scoring (dynamic workflows)

When the runtime exposes the `Workflow` tool AND the user has opted in, run
blind validation as a workflow: fan out 3 independent scorers in one phase and
take the **median per dimension**. Otherwise spawn one background `Agent` as
above. Do NOT start a workflow without explicit opt-in (keyword "ultracode" or
a direct request in the user's own words); a single `Agent` is the default.

## What blinding actually excludes

"Blind" means the scorer has not seen the skill's improvement history. Two
paths inside a target skill carry it and must not be read:

- **`references/improvement-backlog.md`** — prior scores and known-issue lists.
- **`evals/`** — `benchmark*.json` (`regression_verdict`, `prior_baseline`, `why_run`), `case-validation.*.json` (kept/discarded changes), `scorer-sweep.*.json` (prior blind totals that anchor the scorer).

The Negative-Transfer Gate needs one number from `evals/`, so the only channel
is **`scripts/eval-evidence.py`**: it prints the case count, every `delta_*`
measurement with its JSON path, and the Dim 10 cap they imply. No verdicts, no
prior scores, no assertions.

**Benchmark format:** whatever the official `aggregate_benchmark.py` writes
(`run_summary.<arm>.pass_rate.{mean, stddev, min, max}` plus `runs[]`).

**Derive the delta from the arms; never read the stored
`run_summary.delta.pass_rate`.** It is a rounded string (`"+0.19"`), its sign
follows dict insertion order, and a missing arm becomes 0 (absent baseline gives
a maximally positive delta). Compute `with_skill − without_skill` from the
arms: full precision, order-independent, a missing arm yields no delta. A stored
delta that disagrees with the derived one is reported as a MISMATCH (hand-edited
file or different aggregator).

## When a scorer does not return a score

A scorer that dies, times out, returns prose without the table, or omits
dimensions has **not scored**. Treat the gap as absent:

- **Do not fill it from the self-score.**
- **Do not coerce a missing dimension to 0** or carry forward its previous
  value. Report the dimensions that came back and mark the **total** `NO SCORE`
  (a total over fewer than 10 dimensions is not comparable).
- **Retry once.** If the second attempt fails, record `NO SCORE` and say which end.

A pass is done only with **both** blind scores on record (SKILL.md §"Improve",
improve-loop Phase 7). With one end unscored the pass is **stopped
early**: do not report it as finished or quote its delta.

With median-of-3 scoring, report the count that returned: three is the median,
two is an average labelled `n=2`, one is a solo score labelled `n=1`, none is
`NO SCORE`. State both ends' counts when they differ.

## The A/B comparator

The absolute score answers "how good is this?"; the comparator answers "did
this pass help?" and is the pass verdict. Run it once, after the loop stops.
The absolute delta cannot be the verdict: scorer spread (2-4 points) exceeds
many real passes. The score catches large regressions; the comparator resolves
small diffs.

**Materialise both sides as plain directories.** Do not hand it the live git
working tree. Run:

```bash
scripts/ab-setup.py <baseline-ref> <skill-dir>
```

It extracts the baseline to `x/` and `HEAD` to `y/` with `git archive`, leaves
out `evals/` and `improvement-backlog.md`, sets every mtime to one value, and
writes the comparator agent as an `--agents` JSON file outside the pair. It
prints `AB=<dir>` and `AGENTS=<file>`; use those literal paths below.

`<baseline-ref>` is the commit the loop started from, the same ref Phase 0
recorded.

**Gate the spawn on the check, per directory:**

```bash
for d in "$AB"/x "$AB"/y; do
  printf '%s %s\n' "$(find "$d" -printf '%T@\n' | sort -u | wc -l)" "$d"
done   # each line must start with 1
```

Check each side, not the parent: other files in `$AB` give a spurious `3`.
**Keep the mapping note outside `$AB`.** A blinding failure is silent, so gate
on the per-directory numbers.

**Randomise the order, per spawn.** Assign baseline and final to `DIR A` /
`DIR B` by coin flip and keep a private mapping note. Leave the opaque
`mktemp -d` names; do not rename them.

**Spawn three `skill-comparator` agents, majority vote.** Omit `model` (the
agent definition pins it). Vote over `winner` after mapping A/B back to
baseline/final:

| Votes for final | Verdict | Action |
|---|---|---|
| 3 of 3, or 2 of 3 | `IMPROVED` | Pass stands. Record the margin. |
| any split with 2+ `TIE` | `NO CHANGE` | Pass kept nothing measurable — record it as such rather than claiming a lift. |
| 2 of 3, or 3 of 3, for baseline | `REGRESSED` | Something in the pass made the skill worse. Read `reasons`, revert the responsible iteration, re-run. |

- Agreement on the winner with split high/low `confidence` is still a verdict; only `TIE` counts as no change.
- **`REGRESSED` outranks a positive absolute delta.** Trust the comparator and find the responsible iteration.
- **Read `regressions` even on a win.**
- **Check order bias across runs.** The A-vs-B win rate from the recorded mappings should sit near 50%; otherwise blinding is not holding.

**Spawn the comparator from outside the repo.** A subagent spawned from a repo
cwd inherits an environment block listing recent commit subjects, which
describe the diff being judged. Run each comparator as a bare `claude -p` with
cwd `<AB>`, the agent from the `<AGENTS>` file (a project agent does not resolve from
`/tmp`):

```bash
# The prompt goes before --add-dir: --add-dir takes every following argument.
(cd <AB> && claude -p "Rubric: <skill-improver-dir>/references/quality-rubric.md. DIR A: <AB>/x. DIR B: <AB>/y." \
  --agents <AGENTS> --agent skill-comparator --add-dir <skill-improver-dir>/references)
```

An in-session subagent is a degraded fallback; record its verdict as semi-blind.

| Field | What it means | Action |
|---|---|---|
| `leakage_external` | git metadata, mtimes, directory names, caller session context | Invalidates the run. Close that channel and re-spawn. Exception: today's date is always in a `claude -p` environment and cannot be closed — record it, accept the verdict. |
| `leakage_content` | a `Verified 2026-..-..` stamp or version line *inside the compared text* | Record it and accept the verdict. Do not redact in-text dates (freshness stamps are Dim 9 evidence). |

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

The blind score does not override the self-score. A flagged dimension becomes a
candidate for the next iteration.
