---
name: autoresearch
argument-hint: "[optimize|research|improve] [topic or target]"
description: >-
  Autonomous experiment loops that hill-climb a measurable metric — apply one
  change, measure, keep it only if the number improved, revert if not, repeat
  unattended. Also deep multi-perspective research producing a saved report, and
  research-then-optimize when no metric exists yet.
when_to_use: >-
  Use whenever work should run as a measured loop rather than a one-shot edit:
  "autoresearch", "experiment loop", "optimize autonomously", "hill climbing",
  "hill-climb", "Karpathy loop", "iterative optimization", "keep trying until it
  improves", "keep trying different approaches", "keep whatever improves", or
  running overnight/unattended while the user is away. Also when any numeric
  target (latency, p99, bundle size, compile time, throughput, loss, pass rate,
  coverage) should be pursued through repeated measure-change-verify cycles
  rather than a single fix; when the request is to research best practices and
  THEN actually improve the thing; or for recursive multi-perspective research
  that saves a report to optimize against later.
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash(git *)
  - WebSearch
  - WebFetch
  - Agent
---

# Autoresearch

An autonomous agent that finds improvements through measured experiments or deep
research. Based on Karpathy's autoresearch pattern: separate what the human controls
(strategy) from what the agent controls (execution), then let the agent iterate
indefinitely with objective verification.

## Choosing a Mode

| Mode | Command | When to use |
|------|---------|-------------|
| **Optimize** | `/autoresearch optimize` | There is code/config/prompt + a way to measure quality. Find improvements autonomously. |
| **Research** | `/autoresearch research` | Deep, multi-source research on a topic with synthesis. |
| **Improve** | `/autoresearch improve` | Improve something without a clear starting point. Research best practices first, then apply via the optimize loop. |

When no mode is specified, infer from context: metric or benchmark mentioned → Optimize.
Question or topic exploration → Research. Wants something "better" without a defined
measure → Improve.

---

## Mode 1: Optimize (Experiment Loop)

The core Karpathy pattern. A hill-climbing ratchet where only measurable improvements
accumulate.

### Step 1: Configure the Experiment

Before looping, establish four components. Ask the user to confirm if anything is
ambiguous — but if the project structure makes the answers obvious, just proceed.

| Component | What it is | Example |
|-----------|-----------|---------|
| **Truth Layer** | Read-only files that define correctness — tests, specs, data, eval harness. The agent never modifies these. | `tests/`, `prepare.py`, `benchmark.sh` |
| **Mutable Surface** | The file(s) the agent modifies each iteration. Keep this as small as possible — a focused surface leads to cleaner experiments. | `train.py`, `config.yaml`, `prompt.md`, `src/hot-path.rs` |
| **Verifier** | A command that produces a numeric metric. Lower or higher is better (establish direction). Must be deterministic enough that noise doesn't dominate signal. | `pytest --tb=short`, `./bench.sh`, `npm run perf` |
| **Metric** | The specific number to extract from verifier output, and the direction of improvement. | `val_bpb (lower is better)`, `throughput_rps (higher)`, `pass_rate (higher)` |

Read `references/experiment-loop.md` for auto-detection heuristics when the user
doesn't specify these explicitly.

**When to suggest classical tools instead:** For pure numeric parameter sweeps
(no code logic — YAML thresholds, hyperparameters), mention that Optuna or BOHB
may converge faster. Autoresearch's edge is mutating arbitrary code and algorithms.
Don't gate on this; just note it so the user can choose.

**Budget the run before entering it.** Multiply the baseline verifier duration by
the iteration cap: a 5-minute verifier over 20 iterations is ~1.7 hours of compute
plus the agent's own token spend, and the loop is designed to run unattended. State
that product when presenting the configuration. If it exceeds what the user has
agreed to, lower `--max` or make the verifier cheaper (smaller input, fewer trials)
*before* starting — mid-loop budget changes invalidate the baseline that every
recorded delta is measured against.

### Step 2: Establish Baseline

1. Create a git branch: `autoresearch/<descriptive-tag>` from current HEAD
2. Read the mutable surface files — those only. The surface is small by
   construction (Step 1), so this is bounded; the truth layer and the wider
   tree are not read here
3. Run the verifier once unmodified to get the **baseline metric**
4. Record in `results.tsv` (see "Results Ledger" below for the canonical schema):
   ```
   commit	metric	delta	status	duration_s	description
   <hash>	<value>	0	baseline	<s>	Initial measurement
   ```

### Step 3: The Loop

Run this loop autonomously without pausing for confirmation. The user may be asleep,
at lunch, or doing other work — they will interrupt when they want it to stop.
`allowed-tools` blocks nothing — it only lists what runs *without asking*.
WebSearch, WebFetch, and Agent are pre-approved because Mode 2 fans out research
agents and would otherwise prompt on every one. Bash is pre-approved for `git *`
only, so the verifier still runs but asks the first time; the Step 2 baseline run
is where that approval lands, while the user is still present rather than mid-loop
while they are away. Pre-approving a *specific* verifier (`Bash(pytest *)`,
`Bash(npm run bench)`) is a reasonable thing to add for a repeat target. Blanket
`Bash` is not — it would let every later iteration run anything unattended, and
the loop's whole premise is that it mutates code while nobody is watching.

```
LOOP:
  1. HYPOTHESIZE: Read results.tsv, recent verifier output (errors, warnings,
     timing breakdowns — not just the scalar), and the mutable surface. Sketch
     2-3 candidate hypotheses, compare them against the results.tsv rows most
     similar to each, then commit to ONE with expected impact and rationale.
     Compare before executing, not after — the ability to predict which change
     will help decays as kept changes accumulate, and this restores it
     (`references/ecosystem.md` §Mechanisms Worth Borrowing).

  2. MUTATE: Apply exactly ONE atomic change. Small reversible edit over large
     rewrite. Never bundle. Don't retry discarded ideas without a meaningfully
     different approach. ANNOTATE non-obvious values inline per "Provenance
     Comments" below.

  3. COMMIT: `git add <mutable files> && git commit -m "experiment: <description>"`

  4. RUN: Execute the verifier. Capture ALL output; retain ~200 lines for the
     next HYPOTHESIZE (warnings, profiling, timing are signal). Never get stuck
     on a failure — extract the signal and move on:
     - Trivial bug (typo, import): fix and retry once, else log "crash".
     - Runtime crash: apply the obvious fix, else log "crash" and move on.
     - Duration over the timeout budget: kill, log "timeout". Budget is 2x
       baseline for 30s-5min runs; shorter runs get 3x, longer runs 1.5x/1.3x
       (`references/experiment-loop.md` §Timeout Policies).
     - Variance >2% between identical runs: run the verifier 3 times and take
       the MEDIAN, not the mean — one outlier run otherwise moves the metric
       more than the change under test. Note the variance in the log.

  5. MEASURE: Extract the metric from the output.

  6. DECIDE:
     - IMPROVED: Keep the commit as new baseline. Log "kept".
       **Anomaly check:** If delta >3x rolling average of kept deltas AND
       follows 3+ consecutive discards, flag: `⚠ ANOMALY: delta=X is Nx rolling
       avg after plateau — inspect for reward hacking.` Pause one iteration to
       reflect. Do NOT auto-discard — could be a breakthrough — but be suspicious.
     - EQUAL: Keep ONLY if simpler (fewer lines, simpler logic) or strictly
       more general (drops an assumption about inputs the verifier doesn't
       exercise). Log "kept-simpler" or "discarded-no-gain".
     - REGRESSED: `git revert HEAD --no-edit` (preserves history). Log "discarded".

  7. LOG: Append to results.tsv (commit, metric, delta, status, duration_s, description).

  8. STATUS: Print `[iteration N] metric=X delta=Y status=Z`

  9. REFLECT (every 5): Re-read results.tsv. Categorize experiments (hyperparameter,
     algorithmic, structural, config). If last 5 are same category, force a
     different category next. Print `[reflect] N kept from <cat>, pivoting to <new>`.

  10. GOTO 1
```

### Stopping Conditions

At 5 consecutive discards (plateau — likely a local maximum), do NOT stop yet:
apply the escape strategies in `references/experiment-loop.md` §"Local Maxima"
and pivot to a different hypothesis category.

Treat the plateau as a signal to widen the *search*, not just to rotate
category. Greedy one-at-a-time is the right default while remaining
improvements are dense; a run of discards is the evidence they have gone
sparse, and that is when to generate and compare candidates in a batch. Switch
back to single-change iteration once a productive region is found.

Stop the loop when ANY of these are true:
- **Ceiling mapped:** 8+ consecutive discards spanning at least 3 different hypothesis
  categories. This is not a failure — it means the optimization space has been explored
  and the system is near its ceiling. Report it as a positive finding:
  `✓ Optimization ceiling mapped at <metric>=<value>. Tried <N> experiments across
  <categories>. The system is near-optimal for the current architecture/approach.
  Further gains likely require a fundamentally different strategy.`
- **Target reached:** The user specified a target metric and the loop reaches it
- **User interrupt:** The user sends any message
- **Iteration cap:** 20 iterations by default (user can override with `--max N`)

When stopping, print a summary table of all experiments and the cumulative improvement.

### The Simplicity Criterion

Prefer deletions. A change that removes code for equal-or-better metric is always
worth keeping; a small gain that adds ugly complexity is not. The git history should
read as a clean sequence of wins, not a pile of hacks.

### The Generality Criterion (weakness)

Simplicity and generality are different axes: hard-coding the benchmark's input
size is one line, and also a maximally specific bet. Among candidates that
measure the same, prefer the one that assumes less about inputs the verifier
doesn't exercise — the probability a change holds beyond the measurement scales
with how little it commits to, not how short it is (Bennett, arXiv:2301.12987:
the weakest hypothesis consistent with the data generalises best; the shortest
is neither necessary nor sufficient). A change keyed to eval-data specifics
(exact sizes, seeds, strings, fixture quirks) is overfitting even when the
number improves — and it is the shape reward hacking usually takes, so this
criterion and the anomaly check reinforce each other.

---

## Mode 2: Research (Deep Multi-Agent Research)

Recursive depth+breadth research with parallel agents. Produces a comprehensive,
source-grounded report.

Break the question into 3-6 independent research angles using the STORM
multi-perspective pattern — split by viewpoint, not by subtopic. What is
borrowed is the *pattern*; the STORM codebase itself has been dormant since
2025 and is not a dependency here (`references/ecosystem.md` §Research
Patterns):

- What would a practitioner want to know?
- What would a skeptic question?
- What does the academic literature say?
- What are the competing approaches?
- What are the failure modes and edge cases?

Spawn one subagent per angle — all in one message, `subagent_type:
"deep-researcher"` (plugin installs: `agent:deep-researcher`). The research
instructions are that agent definition's system prompt, shared and
prompt-cached across the round; each spawn's prompt carries only the
question, the angle, and prior learnings (tail template in
`references/deep-research.md`). Fallback: if neither agent name resolves,
Read `../../agents/deep-researcher.md` (relative to this skill directory)
and spawn `general-purpose` with its body pasted above the tail. Each
returns structured LEARNINGS, CONTRADICTIONS, FOLLOW_UPS, SOURCES, and a
CONFIDENCE rating. Once all agents return:

1. **Merge learnings** — deduplicate, resolve contradictions, note confidence levels
2. **Identify gaps** — what follow-up questions are most important?
3. **Recurse if needed** — for the top 2-3 follow-up questions, dispatch another round
   of agents. Reduce breadth by half each level. Default depth: 2 levels.
   Configurable with `--depth N` and `--breadth N`.
4. **Synthesize** — produce a structured report with: Executive Summary, Key Findings
   (by theme, not by source), Competing Perspectives, Gaps/Uncertainties, and Sources.
   Read `references/deep-research.md` for report templates, agent prompt templates,
   and synthesis patterns.
5. **Audit** — before saving, check the draft against its own sources
   claim-by-claim: does every load-bearing claim trace to a cited source, does
   that source actually say it, and is each contradiction surfaced rather than
   quietly resolved in favour of one side? Dispatch targeted follow-up on claims
   that fail, then re-synthesize. Verification is a separate stage, not something
   folded into writing. Checklist: `references/deep-research.md` §"Audit Pass".
   Skip only at Quick depth.
6. **Save** — write the final report to this skill's own
   `results/<topic>-research-<date>.md`, not the target project's tree. Reports
   accumulate there as a durable cross-project research archive, and the report
   is the provenance record that "Provenance Comments" below points back to.

### Depth Control

| Setting | Queries | Depth | Good for |
|---------|---------|-------|----------|
| Quick | 3-4 | 1 | Factual questions, quick overviews |
| Standard | 5-8 | 2 | Most research tasks (default) |
| Deep | 8-12 | 3 | Complex topics, competitive analysis |
| Exhaustive | 12+ | 4 | Due diligence, literature reviews |

The user can specify: `/autoresearch research --depth deep "topic"`

**Budget the fan-out before dispatching it.** Sum the agents across levels, not
just the first round — Standard is ~6+3+2 ≈ 11 agents, Exhaustive reaches ~23.
Each agent runs several searches, so web searches, not agents, is the binding
constraint: a session allows 200 web searches total
(`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`, Claude Code v2.1.212) and 20
subagents in flight at once (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, v2.1.217).
The per-session cap on *total* subagents was removed in v2.1.224, so agent count
no longer bounds a run — searches and concurrency do. An Exhaustive run at 5
searches per agent consumes over half the session's search budget, and a run
that exhausts it fails mid-synthesis with partial findings and no report.
State the agent count when proposing a depth above Standard.

---

## Mode 3: Improve (Research-then-Optimize)

For when the user wants something better but doesn't yet know what "better" looks
like. This mode runs Research first to discover best practices, then Optimize to
apply them.

### Phase 1: Research

Identify what the user wants to improve (code, config, prompt, workflow), then run
Mode 2 targeting: best practices for this type of artifact, common performance
pitfalls, what the state of the art looks like, and specific techniques that have
worked for others. Present the findings to the user as a brief summary (not the
full report) and propose a metric + verifier grounded in them.

**If the metric is subjective** (quality scores, "is it better?", LLM-as-judge),
recommend converting to 3-5 binary pass/fail assertions instead. Binary evals
(e.g., "Does the output contain X?", "Is the response under N tokens?", "Does it
compile?") resist drift and enable truly autonomous operation. Fuzzy 1-5 rubrics
cause the agent to score itself leniently over time. A test either passes or doesn't.

### Phase 2: Optimize

Present the proposed experiment configuration to the user — truth layer, mutable
surface, verifier command, metric + direction, and the top 5 hypotheses ranked by
expected impact from the research — then let them confirm or override and enter
the Mode 1 loop. Order hypotheses research-informed first, speculative later, and
cite the research report in the provenance comment of every change it informed.

The research phase turns blind exploration into targeted experimentation.

---

## Operational Details

### Git as State Machine

Always work on branch `autoresearch/<tag>`, never on main/master. Never force push.
The branch tip is always the best-known version — commit on keep, `git revert HEAD
--no-edit` on discard. If not in a git repo, keep a copy of the last-known-good
version of the mutable surface and restore it on discard instead.

### Results Ledger

Track all experiments in `results.tsv` (append-only) at the project root:

```
commit	metric	delta	status	duration_s	description
abc1234	0.9979	0.0000	baseline	301	Initial measurement
def5678	0.9952	-0.0027	kept	298	Increased depth from 8 to 12
```

Read this before each hypothesis to avoid repeating failed ideas.

### Provenance Comments

Leave inline comments on non-obvious experimentally-derived values so future readers
don't have to reconstruct the reasoning from git blame or chat history. Include:
the `autoresearch:` prefix, before→after metric, why it works, and a pointer to
`results.tsv` or the research report. Skip obvious defaults and self-explanatory diffs.

```python
# autoresearch: batch_size=384 outperformed 128/256/512 (throughput 1.8x baseline).
# Fits in L2 cache on target hardware. See results.tsv for full sweep.
BATCH_SIZE = 384
```

When Mode 2/3 research informed a choice, reference the report file instead.

### End-of-Session Summary Comment

When the optimize loop stops, add a block comment at the top of the primary mutable
file: session branch/date, metric baseline→final, iteration count (kept/discarded),
key changes that moved the needle, and a pointer to results.tsv. Append below any
previous session comments — don't replace them.

### Resuming an Interrupted Session

Before the first hypothesis of a resumed run, read the prior session comments and
the **full** results.tsv, not just its tail — the files are the durable record and
in-context memory of earlier experiments is not. Then re-run the verifier once on
the branch tip: a metric recorded days ago may not reproduce on today's machine
state, and mutating against a stale baseline silently corrupts every subsequent
delta (see "Baseline Re-establishment" in `references/experiment-loop.md`).
Carrying summaries across sessions this way is measured to unlock further gains,
not just to document them — see PERFOPT-Bench in `references/ecosystem.md`.

### Blind Validation (Subjective Metrics)

Skip for objective metrics (latency, bytes, pass rate) — the number is the number.

For subjective metrics (LLM-as-judge, rubric scores, design ratings), the agent
that proposed a change is biased toward keeping it. Counter by spawning a blind
evaluator subagent — once on a baseline snapshot (background), once on the final
version — and comparing Self / Agent / Gap per component. A gap ≥2 flags that
component for the next hypothesis; the blind score surfaces bias, it never
overrides the self-score.

See `references/experiment-loop.md` (Blind Validation Protocol) for when to spawn,
the agent prompt template, and the comparison-table format.

---

## Additional Resources

### References
- `references/experiment-loop.md` — Auto-detection heuristics, advanced loop
  mechanics, timeout policies, common pitfalls, and the Blind Validation Protocol
  (agent prompt template + comparison-table format for subjective metrics)
- `references/deep-research.md` — Full research agent prompt templates, structured
  extraction schemas, synthesis patterns, source quality assessment, and the
  Audit Pass checklist (Mode 2 step 5)
- `references/domain-templates.md` — Pre-built experiment configurations for web
  perf, ML training, prompt optimization, test coverage, bundle size, API latency
- `references/ecosystem.md` — Prior art: canonical repos, tree search / evolutionary
  / meta-agent alternatives, Claude Code implementations, reward hacking case studies
- `references/sources.md` — Per-URL index backing ecosystem.md; a freshen pass
  probes every row and stamps the `Freshened:` date in the file header
- `references/improvement-backlog.md` — Ceiling findings carried across skill-improver
  passes; not needed at invocation time

### Example Reports

`results/` is a local research archive, not shipped content — it is gitignored,
so these files are present only where the reports were generated. Their absence
in a fresh checkout is expected and is not a broken reference.
- `results/autoresearch-evolution-research-2026-04-06.md` — Mode 2 output: how the
  autoresearch ecosystem has evolved since Karpathy's original release
- `results/autoresearch-landscape-research-2026-08-20.md` — Mode 2 output with an
  Audit pass applied to its own citations; the evidence behind this skill's
  Audit step, plateau rule, and candidate-comparison in HYPOTHESIZE
