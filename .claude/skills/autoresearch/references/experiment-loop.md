# Experiment Loop: Detailed Reference

## Table of Contents
- [Auto-Detection Heuristics](#auto-detection-heuristics): truth layer · mutable surface · verifier · metric
- [Advanced Loop Mechanics](#advanced-loop-mechanics): multi-file mutation · exploration vs exploitation · baseline re-establishment · context exhaustion · parallel experiments
- [Timeout Policies](#timeout-policies)
- [Common Pitfalls](#common-pitfalls): reward hacking · local maxima · nondeterminism
- [Blind Validation Protocol](#blind-validation-protocol): when · spawn · agent prompt · comparison table · decision rule

## Auto-Detection Heuristics

When the user says "optimize this" without specifying the four components, use these
heuristics to configure the experiment automatically.

### Detecting the Truth Layer

Look for these in order:
1. **Test suites:** `tests/`, `__tests__/`, `spec/`, `test_*.py`, `*.test.ts`
2. **Benchmarks:** `bench/`, `benchmark/`, `*.bench.*`, `bench.sh`
3. **CI config:** `.github/workflows/`, `.gitlab-ci.yml` (extract the test/build commands)
4. **Package scripts:** `package.json` scripts with "test", "bench", "lint" in the name
5. **Makefiles:** targets named `test`, `bench`, `check`, `verify`

If none found, ask the user how to verify correctness.

### Detecting the Mutable Surface

The mutable surface should be the smallest set of files that controls the thing being
optimized. Heuristics:

- If the user pointed at a specific file: that file
- If there's a config file (`.yaml`, `.toml`, `.json`, `.env`): often the mutable surface
- If optimizing performance: the hot path (profile or ask the user)
- If optimizing a prompt: the prompt file (`.md`, `.txt`, system message)
- Default: ask the user. A too-broad mutable surface leads to unfocused experiments.

### Detecting the Verifier

Look for commands that produce numeric output:
1. **Test suites with timing:** `pytest --durations=0`, `jest --verbose`
2. **Benchmarks:** `hyperfine`, `wrk`, `ab`, `k6`, `artillery`
3. **Custom scripts:** anything in `scripts/` or `bin/` that outputs numbers
4. **Build metrics:** `du -sb dist/`, `wc -l`, `time make`

### Detecting the Metric

Parse verifier output for numbers. Common patterns:
- `time: 3.45s` → extract seconds (lower is better)
- `score: 0.95` → extract score (higher is better)
- `passed 47/50` → extract pass rate (higher is better)
- `size: 234KB` → extract size (lower is better)
- `val_bpb: 0.9979` → extract metric (ask direction if unclear)

If multiple numbers are present, ask the user which one matters most. Optimizing
multiple metrics simultaneously is hard — pick one primary metric and treat others
as constraints (e.g., "improve speed without increasing error rate").

---

## Advanced Loop Mechanics

### Multi-File Mutation

Sometimes the mutable surface spans multiple files (e.g., a module with 3 source
files). Rules:

- Still make ONE conceptual change per iteration
- The change may touch multiple files if they're part of the same idea
- Commit all changed files together
- On discard, reset all of them

### Exploration vs. Exploitation

The loop naturally exploits (small tweaks to what's working). To encourage exploration:

- After 3 consecutive small improvements (<1% gain each), try a bigger structural change
- Read the results.tsv history to identify patterns: what types of changes tend to work?
- If stuck in a plateau, try changes from a completely different category:
  - If you've been tuning numbers → try architectural changes
  - If you've been changing algorithms → try configuration/parameter changes
  - If you've been optimizing hot paths → try reducing unnecessary work

### Baseline Re-establishment

Every 10 iterations, re-run the baseline (unmodified verifier on current best) to
check for drift. GPU noise, background processes, or system state changes can shift
the baseline over time. If the re-baseline differs significantly (>2%) from the
last measurement, note it in the log.

### Context Exhaustion in Long Loops

After ~10 iterations, in-context memory of previous experiments degrades as the
conversation grows and earlier turns are compacted. Do not rely on remembering what
you tried — **re-read `results.tsv` explicitly** before forming each hypothesis.
The file is the authoritative record of all experiments, not your memory. This is
especially important after autocompaction events.

### Parallel Experiments (Advanced)

When the user has multiple cores/GPUs or the experiments are fast (<30s):

1. Spawn 2-3 subagents, each on a different hypothesis
2. Each works in a git worktree (isolated copy)
3. Collect results from all, keep only the best improvement
4. Merge the winning worktree back to the main branch

This is useful for expensive-to-evaluate experiments where you want to maximize
throughput. The tradeoff is that each agent doesn't see the others' results, so
you may waste effort on redundant experiments.

---

## Timeout Policies

| Experiment duration | Timeout multiplier | Rationale |
|--------------------|-------------------|-----------|
| <30 seconds | 3x baseline | Short runs have high variance, give more slack |
| 30s - 5 min | 2x baseline | Standard multiplier |
| 5 - 30 min | 1.5x baseline | Long runs shouldn't waste too much extra time |
| >30 min | 1.3x baseline | Very long runs — tight timeout to avoid waste |

Kill the process with `timeout <seconds> <command>` or by monitoring wall clock time
and sending SIGTERM.

---

## Common Pitfalls

### Reward Hacking
The agent might find ways to improve the metric without genuinely improving the
artifact. Watch for:
- **Throughput gaming:** Processing more data in the time budget without improving quality
- **Overfitting to eval set:** If the verifier uses a fixed test set, improvements may
  not generalize
- **Metric manipulation:** Changing output format to make parsing extract a "better" number

Mitigation: the truth layer is read-only. The agent cannot modify the verifier or
the eval data. If you suspect reward hacking, add a second metric as a sanity check.

### Local Maxima
Hill climbing can get stuck. Signs:
- 5+ consecutive discards
- All hypotheses in the same category
- Metric has plateaued for 10+ iterations

Escape strategies:
- Try a fundamentally different approach (not a tweak)
- Temporarily accept a small regression to reach a new part of the search space
  (only with user permission — this breaks the ratchet guarantee)
- Ask the user for new ideas to explore

### Nondeterminism
GPU kernels, thread scheduling, and compilation caches can introduce noise. If your
metric variance is >2% between identical runs:
- Run the verifier 3 times and take the median
- Use `torch.use_deterministic_algorithms(True)` for PyTorch
- Set random seeds explicitly
- Note the variance in your results log

---

## Blind Validation Protocol

For subjective metrics (LLM-as-judge, holistic rubric scores, design ratings),
the agent that produced a change is biased toward keeping it — Anthropic's harness
research found agents "confidently praise their own work even when quality is
obviously mediocre." Blind validation runs an independent subagent that has not
seen the changes to score them objectively.

For objective metrics (latency, bytes, throughput, pass rate), skip this — the
number is the number.

### When to spawn

1. **Baseline** — snapshot the mutable surface to a temp directory, then spawn
   a blind agent in the background. It runs in parallel with the loop, so its
   result is ready by the time the loop finishes.
2. **Final** — after the loop stops, spawn another blind agent on the final
   version. Run foreground (the comparison table needs the result before the
   summary is printed).

Snapshot example: `cp -a <surface-dir> /tmp/<tag>-baseline` so the agent scores
the unmodified version even if the loop has already mutated the live files.

### Agent prompt template

Substitute paths and the metric definition. Tell the agent to be honest and
critical and to expect the typical score range up front, so it doesn't grade-
inflate by default:

```
Score the artifact at <path> against this metric: <metric definition>.

Be honest and critical — most decent <artifacts> score in the <typical range>.

<metric-specific scoring guidance — usually a copy of or pointer to the rubric>

For each component, give a 0-N score with a one-sentence justification. Return
the scoring table, the total, and a "Top N issues" list with file:line where
applicable.
```

For component-based metrics (rubric with N dimensions), have the agent score
each component separately so per-component gap detection works.

### Comparison table

After each blind agent returns, print a side-by-side table:

```
## Bias Check: [baseline|final]

| Component | Self | Agent | Gap |
|-----------|------|-------|-----|
| <name>    |  X   |   Y   |     |
| ...       |      |       |     |
| **Total** |  X   |   Y   |     |

[FLAG] <component>: self-score 2+ higher than blind agent.
Agent says: "<the agent's specific justification>"
→ Re-evaluate with this in mind in the next iteration.
```

Only flag components where the gap is **≥2**. If no flags, print "No components
with 2+ gap. Scores aligned." Use the agent's specific justification text — not
just the number — to drive the next hypothesis.

### Decision rule

- The blind score does NOT override the self-score. It surfaces bias for the
  loop to address — a flagged component becomes a candidate for the next
  iteration's hypothesis.
- A flag does not mean the change was wrong. It means the self-score was
  optimistic, and the dimension that drove the flag deserves a fresh look.
- After the loop stops, print both the baseline and final comparison tables so
  the cumulative bias trajectory is visible.

### Why baseline (not just final)

A baseline blind score has two functions:

1. **Detect a wrong starting point.** If the self-baseline is meaningfully above
   the blind-baseline, the optimizer is starting from a wrong number and every
   kept change inherits that error. Recalibrate before continuing.
2. **Provide a control.** The same blind agent rates baseline and final, so the
   blind delta is comparable to the self delta. If the self-loop reports +11 but
   the blind agent only sees +3, the loop has been hill-climbing on noise.
