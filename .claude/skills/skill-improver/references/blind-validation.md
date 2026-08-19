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

## Model selection

**Model: dynamic — the scorer inherits the session model.** Omit the `model`
field in the `Agent` call. Two constraints bind:

- **Same-run consistency.** The baseline and final scorers of one run must use
  the same model — the bias-check table and the run's score trend are only
  comparable within one scorer. If the session model changes mid-run, pass the
  baseline scorer's model explicitly to the final scorer.
- **Frontier floor.** Never score with a Haiku-class or smaller model.
  Validation is the loop's hard task — the dim-by-dim justifications are what
  make subsequent iterations targetable — and Boris Cherny's counterintuitive
  observation holds: cheaper-per-token models often use *more* total tokens on
  hard tasks because of correction loops, and shallow justifications cost more
  wasted iterations than they save in per-token spend. If the session runs a
  small model, pass a frontier-tier model explicitly (`model: "opus"` or
  better) instead of inheriting.

**Effort: inherited from the session, like the model** (operator decision,
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
