# Philosophy Patterns — Boris-Derived Structural Checks

The full Philosophy Mode workflow for `SKILL.md` §"Philosophy Mode". Runs the
three Boris-derived signals as one pass without spinning up the full 10-dim
rubric or the trigger eval set. Sourced from Boris Cherny (creator of Claude
Code, Anthropic; Lenny's podcast 2026).

## Table of Contents
- [Phase P0: Setup](#phase-p0-setup)
- [Phase P1: Run the three checks](#phase-p1-run-the-three-checks)
- [Phase P2: Score](#phase-p2-score)
- [Phase P3: Apply (optional)](#phase-p3-apply-optional)
- [Phase P4: Persist](#phase-p4-persist)
- [Batch Mode](#batch-mode)
- [Anti-patterns](#anti-patterns)

## Phase P0: Setup

1. Resolve the skill (same as Phase 0 of `improve` mode).
2. Read `references/quality-rubric.md` §"Boris Alignment Check",
   `references/freshen-patterns.md` §"4b. Scaffolding Decay Probes",
   and `references/trigger-patterns.md` §"Minimalism test (Boris
   alignment)".

## Phase P1: Run the three checks

| Check | Source | What it flags |
|---|---|---|
| Boris Alignment | quality-rubric §"Boris Alignment Check" | Strict workflow, context dump, model-version compensation |
| Scaffolding Decay | freshen-patterns §4b | Old Claude-version language, prescriptive procedural lists, monolithic context sections |
| Minimalism | trigger-patterns §"Minimalism test" | High-trigger-rate / low-body-content collapse candidates |

Run all three. Each check returns 0 or more findings.

## Phase P2: Score

```
philosophy_score = 3 - count(distinct anti-patterns flagged)
```

Boris score interpretation:

| Score | Meaning |
|---|---|
| 3 | Skill is Boris-aligned. No structural debt. |
| 2 | One anti-pattern. Note in justification, defer if minor. |
| 1 | Two anti-patterns. Flag as ceiling — recommend `improve` mode pass with the flagged dims as targets. |
| 0 | All three anti-patterns. Skill is fighting the model's grain — high probability of decay across the next 1-2 model releases. Recommend a structural rewrite, not iterative improvement. |

## Phase P3: Apply (optional)

Philosophy mode does NOT auto-apply mutations. It surfaces the
findings; the operator decides whether to:

1. Run `improve` mode with the flagged dims as the optimization target,
2. Run `freshen` mode (which now includes scaffolding-decay probes), or
3. Manually rewrite — Boris-score-0 skills typically need that, not
   loop-driven hill climbing.

## Phase P4: Persist

Append a Philosophy entry to `references/improvement-backlog.md` (create
the file if absent) with the score, flagged patterns, and a one-line
recommendation per finding. Same format as the existing backlog
pattern (e.g. `instructions-triage`'s backlog).

## Batch Mode

`/skill-improver batch philosophy --all` runs P1-P4 across every skill
under `~/.claude/skills/`. Output is a leaderboard of Boris scores so
the operator can target the worst offenders first. ~10 seconds per
skill — fast because no probes hit external services and no rubric
re-scoring runs.

## Anti-patterns

- Running `philosophy` mode right before a major Claude release. The
  bitter-lesson signal is most useful 1-2 weeks AFTER a release lands —
  when scaffolding-decay flags are confirmed by behaviour, not predicted.
- Treating Boris score 3 as a permanent green light. Philosophy is a
  point-in-time check; re-run at least quarterly or after each Claude
  major release.
- Auto-applying philosophy findings. The "right" response to model-
  version compensation is usually deletion, but the deletion needs
  author judgment — the loop should not delete operator-curated rules
  unilaterally.
