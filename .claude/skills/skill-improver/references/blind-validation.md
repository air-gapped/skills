# Blind Validation — Scorer Prompt, Model Pin, Comparison Format

The mechanics of the blind scoring pass described in `SKILL.md` §"Blind
Validation". Load when spawning a baseline or final blind scorer.

## Table of Contents
- [Agent Prompt](#agent-prompt)
- [Model selection](#model-selection)
- [Parallel scoring (dynamic workflows)](#parallel-scoring-dynamic-workflows)
- [Comparison Table](#comparison-table)

## Agent Prompt

This block is the canonical scorer prompt; `scripts/batch-workflow.js`
`blindPrompt()` carries the same instructions in JS-array form. Change both
together — a solo-run blind score and a batch-run blind score are only
comparable while they ask for the same checks.

Spawn a subagent with this task (substitute paths):

```
Score this Claude Code skill for quality. Be honest and critical — most decent
skills score 50-70, 80+ is excellent, 90+ is rare. You have never seen this
skill before; score it blind.

1. Read the rubric: <skill-improver-dir>/references/quality-rubric.md
2. Read the design guide: <skill-improver-dir>/references/anthropic-skill-design.md
3. Read the skill: <target-skill-dir>/SKILL.md
4. Read all files in: <target-skill-dir>/references/ — EXCEPT
   improvement-backlog.md. Do NOT open it: it records prior improvement
   passes' final scores and known-issue lists, and reading it un-blinds
   your scoring. Do not penalize the skill for its presence either.
5. Read any scripts/evals: <target-skill-dir>/scripts/ and <target-skill-dir>/evals/ (if present)

For Dimension 1: check what falls within the first 1,536 chars of combined
`description` + `when_to_use`, and penalize if key trigger phrases are past the
cutoff. Note whether the skill splits the two fields or stuffs everything into
`description`.
For Dimension 9: check the `sources.md` `Last verified:` dates (staleness cap),
the spec validity of `name` / `description` (hard-fail cap at 3), and whether
appropriate frontmatter fields are used. Do NOT mark
a version, date, or other external-world claim wrong from internal knowledge —
the skill is freshened continuously and its claims may postdate the knowledge
cutoff. A claim covered by a recent `Last verified:` stamp in sources.md
outranks the prior. If a claim looks wrong, say "verify online" — never
recommend reverting it to an older value from memory.
Apply the Boris Alignment Check caps, the SkillLens Utility Check caps, and
the Negative-Transfer Gate where they fire (rubric §§). For the
Negative-Transfer Gate: unless a `benchmark.json` with a positive
`delta_pass_rate` is present in the skill directory, Dim 10 is capped at 8 —
"essential" is a claim about measured outcomes, not about how the text reads. Do not reward fluency: text that reads well
does not predict utility (SkillLens inversion) — check for failure
mechanisms with executable remedies, actionable specificity, and high-risk
blacklists, and never justify a score delta on format alone.

Score each dimension (0-10) with one-sentence justification. Return the
scoring table, the total, and a "Top 3 issues" list (one line each, with
file:line if applicable).
```

Spawn via whatever subagent mechanism the runtime exposes — in Claude Code,
the `Agent` tool with `subagent_type: general-purpose` and
`run_in_background: true` for the baseline (parallel with the loop), foreground
for the final (comparison table needs the result). If no subagent mechanism is
available, run the same prompt manually in a fresh session and feed back the
result.

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

**Effort: `high`, pinned — never inherit the session effort.** Per the
platform effort doc (verified 2026-08-15), `high` is the level for complex
reasoning and nuanced analysis where quality outranks speed (and equals the
API default), while `xhigh` is scoped to long-horizon agentic runs — 30+
minutes, million-token budgets — which a scoring pass is not. Inheriting
would let a low-effort session silently degrade the justifications the loop
steers by; pinning above `high` buys agentic-exploration depth a read-and-
judge task does not use. Where the runtime's agent-spawn call exposes an
effort field (e.g. the `Workflow` tool's `agent()`), set it; where it does
not (the solo-run `Agent` tool), the session effort applies — record the
effective effort in the run log so scores stay interpretable.

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
