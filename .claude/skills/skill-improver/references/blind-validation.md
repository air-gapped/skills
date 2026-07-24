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
4. Read all files in: <target-skill-dir>/references/
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
Apply the Boris Alignment Check caps and the SkillLens Utility Check caps
where they fire (rubric §§). Do not reward fluency: text that reads well
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

**Default pin: Opus 5** (`claude-opus-5`) at `xhigh` effort — in the `Agent`
call pass `model: "opus"` explicitly rather than inheriting the parent's
default.

Pick the pin from benchmark rows that match the scoring task, not from a
vendor tier label. As of 2026-07-24 the two signals disagree, and the label is
the weaker one:

- **Docs label (weaker signal):** "Claude Fable 5 is Anthropic's most capable
  widely released model… For workloads that need the highest available
  capability, use Claude Fable 5" (platform docs, models overview).
- **Launch benchmarks (stronger signal, Opus 5 launch page):** Opus 5 leads
  Fable 5 on every axis blind scoring actually exercises — knowledge work
  (GDPval-AA 1861 vs 1747), agentic search (BrowseComp 90.8% vs 87.4%),
  multidisciplinary reasoning with tools (HLE 64.7% vs 63.9%), agentic terminal
  coding (43.3% vs 33.7%). Fable 5 leads only on tool-free HLE (56.5% vs 56.3%)
  and two coding benchmarks, all inside 1 point, plus legal; Mythos 5 leads
  health.
- **Knowledge cutoff decides ties for this task:** Opus 5 is May 2026, Fable 5
  Jan 2026. A scorer judging Dim 9 on a freshly freshened skill is exactly the
  case where a later cutoff means fewer false "that version looks wrong" flags.
- Opus 5 is also half the price ($5/$25 vs $10/$50) and supports all five
  effort levels.

Escalate to Fable 5 (`model: "fable"`, `xhigh`) for a long-horizon batch where
the vendor's "highest available capability" positioning is worth the 2× cost,
or when a scoring run must be reproducible against earlier Fable-scored
baselines. Never step below this tier: Boris Cherny's counterintuitive
observation is that cheaper-per-token models often use *more* total tokens on
hard tasks because of correction loops, so the "expensive" model is
paradoxically the cheapest path to a reliable answer. Validation is the loop's
hard task — the dim-by-dim justifications are what make subsequent iterations
targetable, and shallow Sonnet justifications cost more re-runs than they save
in per-token spend.

**Re-pin only on measurements.** A new model being the newest, the default, or
the one labelled "most capable" is not evidence; the benchmark rows that match
the scoring task are. Re-check both signals at each freshen.

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
