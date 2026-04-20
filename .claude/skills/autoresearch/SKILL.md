---
name: autoresearch
argument-hint: "[optimize|research|improve] [topic or target]"
description: >-
  Karpathy-pattern autoresearch — autonomous hill-climbing over a measurable
  metric, deep multi-agent research, or research-then-optimize. Three modes:
  Optimize (keep/discard ratchet), Research (STORM multi-perspective), Improve.
when_to_use: >-
  This skill should be used when the user asks for "autoresearch", "experiment
  loop", "optimize autonomously", "deep research", "hill climbing", "Karpathy
  loop", "iterative optimization", or "keep trying until it improves". Also
  triggers when hitting a numeric target (latency, bundle size, compile time,
  throughput, loss, pass rate) autonomously, running multi-source competitive
  analysis, or improving prompt quality without a defined starting point.
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

### Step 2: Establish Baseline

1. Create a git branch: `autoresearch/<descriptive-tag>` from current HEAD
2. Read all mutable surface files to build full context
3. Run the verifier once unmodified to get the **baseline metric**
4. Record in `results.tsv` (see "Results Ledger" below for the canonical schema):
   ```
   commit	metric	delta	status	duration_s	description
   <hash>	<value>	0	baseline	<s>	Initial measurement
   ```

### Step 3: The Loop

Run this loop autonomously without pausing for confirmation. The user may be asleep,
at lunch, or doing other work — they will interrupt when they want it to stop.

```
LOOP:
  1. HYPOTHESIZE: Read results.tsv, recent verifier output (errors, warnings,
     timing breakdowns — not just the scalar), and the mutable surface. Form
     one specific hypothesis with expected impact and rationale.

  2. MUTATE: Apply exactly ONE atomic change. Small reversible edit over large
     rewrite. Never bundle. Don't retry discarded ideas without a meaningfully
     different approach. ANNOTATE non-obvious values inline per "Provenance
     Comments" below.

  3. COMMIT: `git add <mutable files> && git commit -m "experiment: <description>"`

  4. RUN: Execute the verifier. Capture ALL output; retain ~200 lines for the
     next HYPOTHESIZE (warnings, profiling, timing are signal).
     - Trivial bug (typo, import): fix and retry once, else log "crash".
     - Duration >2x baseline: kill, log "timeout".

  5. MEASURE: Extract the metric from the output.

  6. DECIDE:
     - IMPROVED: Keep the commit as new baseline. Log "kept".
       **Anomaly check:** If delta >3x rolling average of kept deltas AND
       follows 3+ consecutive discards, flag: `⚠ ANOMALY: delta=X is Nx rolling
       avg after plateau — inspect for reward hacking.` Pause one iteration to
       reflect. Do NOT auto-discard — could be a breakthrough — but be suspicious.
     - EQUAL: Keep ONLY if simpler (fewer lines, simpler logic). Log
       "kept-simpler" or "discarded-no-gain".
     - REGRESSED: `git revert HEAD --no-edit` (preserves history). Log "discarded".

  7. LOG: Append to results.tsv (commit, metric, delta, status, duration_s, description).

  8. STATUS: Print `[iteration N] metric=X delta=Y status=Z`

  9. REFLECT (every 5): Re-read results.tsv. Categorize experiments (hyperparameter,
     algorithmic, structural, config). If last 5 are same category, force a
     different category next. Print `[reflect] N kept from <cat>, pivoting to <new>`.

  10. GOTO 1
```

### Stopping Conditions

Stop the loop when ANY of these are true:
- **Plateau:** 5 consecutive discards (likely a local maximum)
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

---

## Mode 2: Research (Deep Multi-Agent Research)

Recursive depth+breadth research with parallel agents. Produces a comprehensive,
source-grounded report.

### Step 1: Decompose the Question

Break the user's question into 3-6 independent research angles. Use the STORM
multi-perspective pattern — don't just split by subtopic, split by viewpoint:

- What would a practitioner want to know?
- What would a skeptic question?
- What does the academic literature say?
- What are the competing approaches?
- What are the failure modes and edge cases?

### Step 2: Dispatch Parallel Research Agents

For each angle, spawn a subagent using the Research Agent Prompt Template in
`references/deep-research.md`. Each agent returns structured LEARNINGS,
CONTRADICTIONS, FOLLOW_UPS, SOURCES, and a CONFIDENCE rating.

### Step 3: Synthesize and Recurse

After all agents return:

1. **Merge learnings** — deduplicate, resolve contradictions, note confidence levels
2. **Identify gaps** — what follow-up questions are most important?
3. **Recurse if needed** — for the top 2-3 follow-up questions, dispatch another round
   of agents. Reduce breadth by half each level. Default depth: 2 levels.
   Configurable with `--depth N` and `--breadth N`.
4. **Synthesize** — produce a structured report with: Executive Summary, Key Findings
   (by theme, not by source), Competing Perspectives, Gaps/Uncertainties, and Sources.
   Read `references/deep-research.md` for report templates, agent prompt templates,
   and synthesis patterns.
5. **Save** — write the final report to `results/<topic>-research-<date>.md`. This
   file serves as the provenance record. Code changes informed by this research
   should reference it in comments (see "Provenance Comments" in Mode 1).

### Depth Control

| Setting | Queries | Depth | Good for |
|---------|---------|-------|----------|
| Quick | 3-4 | 1 | Factual questions, quick overviews |
| Standard | 5-8 | 2 | Most research tasks (default) |
| Deep | 8-12 | 3 | Complex topics, competitive analysis |
| Exhaustive | 12+ | 4 | Due diligence, literature reviews |

The user can specify: `/autoresearch research --depth deep "topic"`

---

## Mode 3: Improve (Research-then-Optimize)

For when the user wants something better but doesn't yet know what "better" looks
like. This mode runs Research first to discover best practices, then Optimize to
apply them.

### Phase 1: Research

1. Identify what the user wants to improve (code, config, prompt, workflow)
2. Run Mode 2 (Research) targeting:
   - Best practices for this type of artifact
   - Common performance pitfalls
   - What the state of the art looks like
   - Specific techniques that have worked for others
3. Present findings to the user as a brief summary (not the full report)
4. Propose a metric and verifier based on the research findings
5. **If the metric is subjective** (quality scores, "is it better?", LLM-as-judge),
   recommend converting to 3-5 binary pass/fail assertions instead. Binary evals
   (e.g., "Does the output contain X?", "Is the response under N tokens?", "Does it
   compile?") resist drift and enable truly autonomous operation. Fuzzy 1-5 rubrics
   cause the agent to score itself leniently over time. A test either passes or doesn't.

### Phase 2: Optimize

1. Present the proposed experiment configuration to the user:
   - Truth layer, mutable surface, verifier command, metric + direction
   - Top 5 hypotheses ranked by expected impact (from research findings)
2. Let the user confirm or override, then enter the Mode 1 loop
3. Order hypotheses research-informed first, speculative later
4. When keeping changes informed by the research phase, include provenance
   comments that reference the research file (e.g., `See results/<topic>-research-<date>.md`)

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

### Crash Handling

Don't get stuck — if an experiment fails, extract signal and move on:
- **Trivial bug** (typo, import): fix and retry once, then discard
- **Runtime crash**: apply obvious fix or log as "crash" and move on
- **Timeout** (>2x baseline): kill, discard, log as "timeout"
- **Flaky results**: run verifier twice and average; note variance >5%

### Blind Validation (Subjective Metrics)

Skip for objective metrics (latency, bytes, pass rate) — the number is the number.

For subjective metrics (LLM-as-judge, rubric scores, design ratings), the agent
that proposed a change is biased toward keeping it. Counter with blind agents:

1. **Baseline:** snapshot the mutable surface (`cp -a <surface> /tmp/<tag>-baseline`)
   and spawn a blind evaluator subagent on the snapshot. Run it in the background
   so the loop continues in parallel.
2. **Final:** spawn another blind evaluator on the final version after the loop
   stops. Print baseline and final comparison tables side by side.
3. **Compare:** for each metric component, print Self / Agent / Gap. Flag any
   gap ≥2 — that component becomes a candidate for the next iteration's
   hypothesis. The blind score does NOT override the self-score; it surfaces bias.

See `references/experiment-loop.md` (Blind Validation Protocol) for the agent
prompt template and comparison-table format.

---

## Additional Resources

### References
- `references/experiment-loop.md` — Auto-detection heuristics, advanced loop
  mechanics, timeout policies, common pitfalls, and the Blind Validation Protocol
  (agent prompt template + comparison-table format for subjective metrics)
- `references/deep-research.md` — Full research agent prompt templates, structured
  extraction schemas, synthesis patterns, and source quality assessment
- `references/domain-templates.md` — Pre-built experiment configurations for web
  perf, ML training, prompt optimization, test coverage, bundle size, API latency
- `references/ecosystem.md` — Prior art: canonical repos, tree search / evolutionary
  / meta-agent alternatives, Claude Code implementations, reward hacking case studies

### Example Reports
- `results/autoresearch-evolution-research-2026-04-06.md` — Mode 2 output: how the
  autoresearch ecosystem has evolved since Karpathy's original release
