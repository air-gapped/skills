---
name: skill-improver
description: >-
  Autoresearch loop for Claude Code skills — greedy keep/discard hill climbing
  on a 10-dimension quality rubric, with blind subagent validation for
  self-scoring bias, plus a `freshen` mode that probes external references
  (release notes, docs, deprecation signals) and applies verified updates,
  plus a `trigger` mode that measures and tunes the skill's frontmatter
  description until it reliably fires when it should and stays silent when
  it shouldn't (60/40 train/test split, 3 runs/query, blinded test scores).
when_to_use: >-
  Triggers on "improve a skill", "optimize a SKILL.md", "make my skill better",
  "run skill autoresearch", "self-improve skills", "evaluate skill quality",
  "score my skill", "audit a skill", "rate my skill", "refine skill
  description", "iterate on a skill", "freshen skill", "freshen skills",
  "update skill references", "check skill staleness", "is my skill out of
  date", "refresh skill sources", "skill not triggering", "skill didn't
  fire", "skill won't trigger", "skill not invoked", "tune skill
  description", "fix skill triggers", "skill under-triggers",
  "skill over-triggers", "false-positive skill", "make skill trigger",
  "Claude isn't using my skill", or mentions autonomous skill improvement,
  skill quality scoring, skill optimization loops, stale skill content,
  or skill activation problems.
argument-hint: '[improve|score|freshen|trigger|philosophy|batch] [<skill-name>|--all|<glob>]'
---

# Skill Improver — Autoresearch for SKILL.md

> **Core Philosophy:** The human programs the researcher, not the research.
> Apply Karpathy's autoresearch methodology — greedy hill climbing with
> keep/discard against a scalar metric — to autonomously improve Claude Code
> skills.

## Invocation

Argument grammar:

```
/skill-improver <mode> <target> [--opts]
```

- `<mode>` — `improve` (default) | `score` | `freshen` | `trigger` | `philosophy` | `batch`
- `<target>` — skill name (e.g. `gh-cli`), absolute SKILL.md path, `--all`, or glob (e.g. `vllm-*`)
- `[--opts]` — mode-specific flags (e.g. `--iterations 15`, `--probe-budget 30`, `--runs-per-query 5`)

Examples:

```
/skill-improver freshen autoresearch
/skill-improver score gh-cli
/skill-improver improve ~/.claude/skills/helm
/skill-improver trigger vllm-caching
/skill-improver trigger gh-cli --missed "find issue with label X"
/skill-improver batch freshen --all
/skill-improver freshen --group 'vllm-*'
```

If `<mode>` is omitted, default to `improve`. If `<target>` is omitted and mode is not `batch`, prompt the user. For `batch`, the target after `batch` selects the sub-mode (`freshen`, `improve`, `trigger`, or `philosophy`, default `improve`); the target list comes from `scripts/scan-skills.sh`. The `--missed "<phrase>"` flag (trigger mode only, repeatable) seeds the eval set with user-reported failures as gold should-trigger queries.

## The Improvement Loop

### Phase 0: Setup

1. Identify the target skill. Accept a path, or run `scripts/scan-skills.sh` (or Glob pattern `**/SKILL.md` under `~/.claude/skills/` and `.claude/skills/`) to list candidates. Do NOT search `~/.claude/plugins/` — those are managed externally.
2. Read the target skill's entire directory: SKILL.md and any references/, examples/, scripts/, assets/ present.
3. **Read `<skill>/references/improvement-backlog.md` if it exists.** This file carries open issues from prior skill-improver runs — ceiling-hit items that require multi-file restructure or author judgment. Do NOT re-propose items already listed there unless new evidence (e.g. the ceiling is now breakable in one iteration due to earlier structural changes). Items resolved mid-loop get moved to the backlog's "Resolved this pass" section in Phase 6.
4. Read **both** `references/quality-rubric.md` (scoring criteria) **and** `references/improvement-patterns.md` (concrete before/after patterns by dimension) from the skill-improver directory. Both are non-optional — skipping the patterns file means later iterations propose changes that miss documented techniques (Pattern 8.2 terminology standardisation, Pattern 6.1 redundancy removal, Pattern 9.3 frontmatter fields). Feeling unsure what to try next at any phase is a symptom of skipping this read. **Apply the Boris Alignment Check** (rubric §"Boris Alignment Check") on the baseline — three diagnostic patterns (strict workflow scaffolding, up-front context dumps, model-version compensation) cap Dims 6, 4, and 9 respectively. Caps surface as cross-cutting structural issues that should be lifted ahead of cosmetic dim improvements of the same magnitude.
5. Establish a baseline score by evaluating the skill against the rubric.
6. Spawn a blind scoring agent on the baseline (see "Blind Validation" section). First snapshot the skill: `cp -a <skill-dir> /tmp/<skill-name>-baseline`. Then run the agent in the background while the loop proceeds. **This is non-optional.** The baseline blind agent is the only check on Phase 1's self-score — without it the entire run rests on whatever bias the loop's self-scoring carries. If the runtime cannot spawn agents, run the same prompt manually in a fresh session and paste back the result before entering Phase 2. Do NOT proceed to Phase 6 without both a baseline AND a final blind score on record.
7. Initialize a results log (in-memory or scratch file) with header: `iteration | score | delta | status | description`.
8. Log iteration 0 as `baseline`.

### Phase 1: Evaluate (Score the Skill)

Score the skill on 10 dimensions (each 0–10, summed to 0–100) using the detailed criteria and scoring template in `references/quality-rubric.md` (loaded in Phase 0).

**Cold-score discipline.** When scoring at any phase, read the current file fresh and assign each dimension against the rubric criteria with no reference to prior iteration scores. Do NOT compute the new score by adding deltas to the old. Delta math hides regressions in dimensions not being watched.

### Phase 2: Hypothesize (Pick One Improvement)

Identify the **single lowest-scoring dimension** (or highest-impact if tied). If the
baseline blind agent has returned with flagged dimensions (2+ gap), use the agent's
specific justification text — not just the number — to inform the hypothesis.
Formulate one specific change:

- What to change and why
- Expected score impact
- Complexity cost (lines added/removed, new files)

Consult `references/improvement-patterns.md` for concrete before/after patterns organized by dimension.

**Check the rejected-edit buffer first.** The run log's discard rows (Phase 5
requires them to carry shape + reason) are this run's rejected-edit buffer.
Do NOT re-propose an edit of the same shape against the same section that a
prior iteration discarded — change the dimension, the section, or the
mechanism. The only exemption: a change kept since the discard has plausibly
removed the reason it failed; if claiming that, name the kept iteration and
the removed reason in the hypothesis.

**Factual-claim hypotheses require a probe.** If the change would alter a
version, date, model name, API, flag, or any other external-world claim, run an
online verification BEFORE mutating (see Operating Rules §"The Skill Outranks
Training Data") — the claim is likely newer than the model's knowledge cutoff,
and "fixing" it from memory regresses the skill.

**The simplicity criterion (from autoresearch):** A small improvement that adds ugly complexity is not worth it. Removing something and getting equal or better results is a great outcome. A +1 score that adds 20 lines of noise? Skip. A +1 from deleting redundant content? Keep.

### Phase 3: Mutate (Make the Change)

1. Apply exactly one change to the skill.
2. Keep the diff minimal and focused.
3. Do NOT bundle multiple improvements — one change per iteration so cause is attributable.

### Phase 4: Re-evaluate (Score Again)

1. Re-score the skill using the same rubric.
2. Compare to previous best score.

**Decision rule:**
- **Score improved** → KEEP. Log as `keep`. This is the new baseline.
  **Noise floor (+1):** a bare +1 total is inside self-scoring noise — cold
  rescores routinely move a total by ±1–2, so a +1 may be the scorer, not the
  change. If the change also simplifies (net lines removed), keep it as
  `keep (simplification)` — the simplification justifies it even at Δ0.
  Otherwise cold-score the affected dimension(s) fresh; keep only if the +1
  reproduces, else revert and log as `discard (noise)`. Noise discards count
  toward the ceiling-mapped stop condition like any other discard.
  **Anomaly gate (+5 or more):** A single change that lifts the total by +5
  or more is presumed inflated until proven otherwise. Do NOT rationalize the
  deltas. Instead: open the rubric fresh, read the current file as if it were
  new, and score each dimension cold. If the cold total differs from the
  delta-math total by 2 or more in either direction, the cold score wins.
  Most +5 jumps shrink to +3 under cold rescore — that is the finding, not a
  failure of the change. Log both totals in the iteration row.
- **Score equal, but simpler** → KEEP. Log as `keep (simplification)`.
- **Score equal or worse** → DISCARD. Revert via `git checkout -- <file>` (or undo the edit if not git-tracked). Log as `discard`. The discard row must name WHAT was tried (change shape + target section) and WHY it failed — discard rows are the rejected-edit buffer Phase 2 consults, and a bare `discard` with no rationale invites the same edit back two iterations later.
- **Change broke something** → REVERT. Log as `crash`. Fix and continue.

### Phase 5: Log and Loop

1. Append result to the log: `iteration | score | delta | status | description`. Use a single declared score column for trend math — pick `self` OR `blind` and stay with it across iterations. Do NOT mix self-scores and blind-scores in the same delta column to make iterations look bigger; if both are tracked, log them as separate columns side by side and compute deltas within each column.
2. Print a one-line status, e.g.: `[iter 3] score: 74 (+2) — keep — moved API docs to references/api.md`.
3. Go to Phase 2 and pick the next improvement.

**Reflect (every 5 iterations):** Categorize all iterations by type (simplification,
style fix, restructuring, content addition, trigger tuning). If the last 5 were all
the same category, force the next hypothesis to be a different category. Print:
`[reflect] N kept from <category>, pivoting to <new category>`

**Stop conditions:**
- Score reaches 90+ AND no dimension is below 7.
- **Ceiling mapped:** 5+ consecutive discards spanning at least 2 different
  improvement categories. This is not failure — it means the skill is near its
  quality ceiling. Report as a positive finding: which categories were tried,
  what the ceiling is, and what would require the author's input to break through.
- **Structural ceiling claim requires evidence.** "Structural ceiling" stops
  require at least 2 logged discards naming the patterns that were attempted
  and why each failed. A run with zero discards has not mapped any ceiling —
  it has stopped early. Reasoning "the next iteration would just be a
  discard" without actually trying it is the
  cheat. Try it.
- User interrupts.
- 10 iterations completed (default cap; user can override).

**What a stop is NOT:**
- Not "+N feels like enough". The metric drives the loop; subjective comfort
  with the gain does not.
- Not "the score is good and I am tired". Read on.
- Not "Dim X is capped, so further improvement is impossible". Other dims
  may still be liftable. Stop only when the rubric criteria for stopping match.

**On stop:** Spawn a final blind scoring agent (see "Blind Validation"). Print
both comparison tables (baseline + final) and the overall results summary.

### Phase 6: Persist the backlog

Before declaring the run done, update `<skill>/references/improvement-backlog.md`
(create the file if absent). This is non-optional — ceiling findings that exist
only in chat disappear when the session ends.

Write two sections:

1. **Open** — every issue the loop **actually attempted** as a hypothesis and
   could NOT apply in a single iteration (multi-file restructure, author-only
   domain content, flagged-for-review findings from freshen, or rule-ceiling
   discards). For each entry:
   - one-line title
   - dimension number it affects (e.g. "Dim 2" or "Dim 6/8")
   - specific file:line pointer OR the exact file-set that would need to change
   - why skill-improver couldn't apply it in one iteration (e.g. "9-file split",
     "requires author-authored error-handling content", "breaks
     self-consistency without restructure")
   - enough context to act on without re-running the baseline scoring

   **Open is NOT a wishlist.** Hypothetical-future-risk items ("description is
   8 chars from cap, might overflow someday"; "this trigger keyword could
   become ambiguous if X happens") do NOT belong in Open. The bar is: the loop
   proposed this iteration, attempted or planned the mutation, and the
   mutation could not be applied. If it was never tried, leave it out. If
   tomorrow's edits would naturally surface it, leave it out. Open is a
   work-not-done log, not a worry list.

2. **Resolved this pass** — one-line audit of what was fixed. Move items from
   "Open" to "Resolved" if a prior backlog listed them and this run closed them.

   **What "Resolved" means:** the iteration applied a real mutation that the
   metric registered. Creating a placeholder file (e.g., empty `sources.md`
   with no `Last verified:` dates) does NOT resolve a Dim 9 staleness cap —
   the cap stays. Log such cases as Open with action "run freshen mode", not
   Resolved. Hand-waving that "the structure now exists" is theater.

Format: plain markdown, `## Open` and `## Resolved this pass` as top-level
sections, in the target skill's own `references/improvement-backlog.md` (not
skill-improver's). Keep the shape uniform across runs so future loops can diff.

If the backlog already exists with items skill-improver chose not to fix this
run, carry them forward into the new "Open" section with a `(carried YYYY-MM-DD)`
marker so staleness is visible.

**The backlog is append-only history, not a status page.** When rewriting it,
never drop prior passes' "Resolved" sections or discard rationales — keep them
as dated `## Resolved — YYYY-MM-DD` sections below the current pass. Discard
rationales are anti-re-proposal guards: a future loop that can't see "tried X,
judged net-negative" will re-propose X. Git keeps the bytes, but loops read the
live file, not git history.

If the run produced zero ceiling findings (converged cleanly at ≥90/100),
still update the file — strip "Open" to empty and record the final score under
"Resolved this pass" so the file remains a truthful record.

---

## Operating Rules

### Never Stop (Unless Asked)

Run the loop continuously. Do not ask permission between iterations. The user may be away. Print status lines so they can review when they return.

### Git as State Machine

When improving skills in a git-tracked directory:
- Commit each kept improvement individually.
- Use `git diff` to show what changed on discard before reverting.
- The branch tip always represents the best-known version.

### Prioritize Deletion Over Addition

In practice, removing redundant content produces the largest per-iteration score gains. When choosing between an additive improvement (+1 from adding content) and a subtractive one (+1 from deleting content), prefer deletion — it improves simplicity as a side effect.

### One File at a Time

Each iteration targets one file. If the improvement requires touching multiple files (e.g., moving content from SKILL.md to references/), that counts as one atomic change.

**The split test for atomicity.** "Atomic" is not a word — it is a constraint. State the change in 10 words, present-tense, single verb. "Move gotchas section to references/gotchas.md." If the honest sentence needs an "and" — "move content to references/ AND fix second-person AND tighten terminology" — it is three iterations, not one. Pure relocation is allowed; relocation that quietly rewrites prose is not. If a structural move starts editing a sentence's wording, stop, finish the move with the prose unchanged, score, then propose the prose edit as the next iteration. The reason: bundled iterations attribute the score lift to the wrong cause, which means future loops will pick the wrong category to pivot to.

### Preserve the Author's Intent

The skill reflects the author's domain expertise. Improve structure, clarity, and adherence to best practices. Do NOT rewrite the author's domain knowledge or change what the skill teaches — only how it teaches it.

### The Skill Outranks Training Data

Target skills are freshened continuously — their factual claims (versions,
release dates, model names, APIs, flags, pinned SHAs) are often NEWER than the
model's knowledge cutoff. Treat the skill's existing text as more current than
the model's prior, never the reverse. This rule applies in EVERY mode, not just
`freshen`:

- Never mutate an external-world claim from memory. If a hypothesis requires
  changing one, verify online first (gh / WebFetch / WebSearch, freshen-style
  probe) and cite the source in the iteration log — or drop the hypothesis.
  "I know this is wrong" is not evidence; the probe is.
- **Downgrade alarm:** wanting to lower a version, move a date backward, or
  revert a claim to an older state is the signature of training-data staleness
  — the skill was probably freshened past the cutoff. Mandatory online check
  before touching it; expect to find the skill is right.
- This binds blind scorers too — the validation prompt instructs them to check
  `sources.md` stamps instead of scoring Dim 9 down from memory, and the loop
  must not act on a blind agent's "wrong version" finding without its own probe.

---

## Blind Validation

Self-evaluation bias is real — the agent that wrote improvements tends to score
them generously. Blind validation uses independent subagents that have never seen
the skill to score it objectively. Run it twice: at baseline and after the loop.

### When to Run

1. **Baseline** — after the self-score in Phase 0 step 5, spawn a blind scoring
   agent in the background. It runs in parallel with the improvement loop.
2. **Final** — after the loop stops, spawn another blind scoring agent on the
   final version.

### Agent Prompt

Spawn a subagent with this task (substitute paths):

```
Score this Claude Code skill for quality. Be honest and critical — most decent
skills score 50-70, 80+ is excellent.

1. Read the rubric: <skill-improver-dir>/references/quality-rubric.md
2. Read the design guide: <skill-improver-dir>/references/anthropic-skill-design.md
3. Read the skill: <target-skill-dir>/SKILL.md
4. Read all files in: <target-skill-dir>/references/
5. Read all scripts in: <target-skill-dir>/scripts/ (if the directory exists)

For Dimension 1: check what falls within the first 1,536 chars of combined
`description` + `when_to_use`, and penalize if key trigger phrases are past the
cutoff. Note whether the skill splits the two fields or stuffs everything into
`description`.
For Dimension 9: check if appropriate frontmatter fields are used. Do NOT mark
a version, date, or other external-world claim wrong from internal knowledge —
the skill is freshened continuously and its claims may postdate the knowledge
cutoff. A claim covered by a recent `Last verified:` stamp in sources.md
outranks the prior. If a claim looks wrong, say "verify online" — never
recommend reverting it to an older value from memory.

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

**Model selection:** pin the validation subagent to the most capable
model available (Fable 5, `claude-fable-5`, as of 2026-06-09 — the
Mythos-class tier above Opus, shipped in Claude Code v2.1.170). Boris Cherny's
counterintuitive observation: cheaper-per-token models often use *more*
total tokens on hard tasks because of correction loops, so the
"expensive" model is paradoxically the cheapest path to a reliable
answer. Validation is the loop's hard task — the dim-by-dim
justifications are what make subsequent iterations targetable, and
shallow Sonnet justifications cost more re-runs than they save in
per-token spend. In the `Agent` call: pass `model: "fable"` (or the
current most-capable identifier) explicitly rather than inheriting the
parent's default.

For the baseline agent, copy the original skill to a temp directory first so
the agent scores the unmodified version even if the loop has already started.

**Parallel scoring (dynamic workflows, Fable 5 / Opus 4.8, Claude Code v2.1.154+).**
When the runtime exposes the `Workflow` tool AND the user has opted into it,
run blind validation as a workflow: fan out 3 independent scorers in one phase
and take the **median per dimension** — more robust against a single scorer's
bias than one agent. Otherwise spawn one background `Agent` as above. Do NOT
spin up a workflow without the user's explicit opt-in (the keyword "ultracode"
— it replaced "workflow" as the trigger keyword in v2.1.160 — or a direct
request in the user's own words) — a single `Agent` is the default.

### Comparison Table

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

---

## Batch Mode

To improve multiple skills:

1. Run `scripts/scan-skills.sh` to find all SKILL.md files in scope.
2. Score each skill (baseline only) and print a ranked table.
3. Sort by score ascending (worst first).
4. Run the improvement loop on each, starting from the worst. Cap at 5 iterations per skill in batch mode.
5. Print a final summary table: skill name, baseline score, final score, delta, number of kept changes.

**Dynamic workflows (Fable 5 / Opus 4.8, Claude Code v2.1.154+).** Batch mode is multi-agent orchestration — when the user has opted into the `Workflow` tool, reuse the saved driver `scripts/batch-workflow.js` (a recon→apply→blind pipeline, median-of-3 final blind): `Workflow({scriptPath: "${CLAUDE_SKILL_DIR}/scripts/batch-workflow.js", args: ["keda", "helm", ...]})`. `args` takes bare names, absolute dirs, or `{dir, hints}` objects. Per-skill loops keep one change per iteration so cause stays attributable; agents inherit the session model and do no git ops — commit per-skill after review. Without opt-in, run skills sequentially as above.

---

## Standalone Evaluation (No Loop)

When the user only wants a quality score without iterating:

1. Read the target skill and `references/quality-rubric.md` from the skill-improver directory.
2. Score all 10 dimensions using the scoring template from the rubric.
3. Print the results table. Highlight the lowest dimension and recommend the single highest-impact improvement.
4. If Dim 9 is capped by sources.md staleness (see rubric §Dim 9), recommend running `freshen <skill>` as the single highest-impact next step.
5. Stop. Do not enter the improvement loop unless asked.

---

## Freshen Mode

Probe a skill's external references for staleness and apply verified updates in
place — same keep/discard loop as `improve`, but hypotheses come from online
evidence (release notes, doc commits, deprecation signals), not rubric scores.

**Invocation:** `freshen <skill-path>` · `--all` · `--group <glob>`. Defaults to
**apply**; for a read-only readout use Standalone Evaluation (Dim 9 tracks `sources.md`).

Full phase workflow (F0→F6), batch mode, and anti-patterns live in
**`references/freshen-patterns.md` §"Freshen Mode Workflow"** with the extraction
heuristics, probe templates, and classification rules. Read it when running `freshen`.

---

## Trigger Mode

Measure and tune a skill's frontmatter `description` (and `when_to_use`) so it
fires when it should and stays silent when it shouldn't. Same keep/discard
hill-climbing as `improve`, but the metric is **trigger rate against an eval
set** — the methodology Anthropic's `skill-creator` uses (60/40 train/test,
3 runs/query, blinded test scores, ≤1024-char cap).

**Use trigger mode when:** a user reports "the skill didn't fire" / "Claude isn't
using my skill", or a description is too vague, narrow, or keyword-collision-y.
Trigger-mode measures Dim 1 empirically via `claude -p` (`scripts/probe-trigger.py`).

Full phase workflow (T0 Setup → T7 Apply/persist), batch mode, and anti-patterns
live in **`references/trigger-patterns.md` §"Trigger Mode Workflow"** with the
eval-set construction rules, probe mechanism, and mutation patterns. Read it when
running `trigger`.

---

## Philosophy Mode

Cheap weekly check that runs the three Boris-derived signals as one
pass without spinning up the full 10-dim rubric or the trigger eval set.
Sibling to `freshen` and `trigger`. Sourced from Boris Cherny (creator
of Claude Code, Anthropic; Lenny's podcast 2026). Output is a Boris
score (0-3 anti-patterns flagged) plus the existing dim caps that fire
as a side-effect.

**Invocation:** `philosophy <skill-name>` · `batch philosophy --all`.
Surfaces findings only — never auto-applies mutations; the operator decides.

Full phase workflow (P0 Setup → P4 Persist), Boris score interpretation,
batch leaderboard, and anti-patterns live in
**`references/philosophy-patterns.md`**. Read it when running `philosophy`.

---

## Additional Resources

### Reference Files

- **`references/quality-rubric.md`** — Full scoring rubric with sub-criteria, examples of each score level, and common failure patterns. Load this before scoring.
- **`references/improvement-patterns.md`** — Catalog of common improvements organized by dimension, with before/after examples.
- **`references/freshen-patterns.md`** — The full **Freshen Mode workflow** (F0–F6) plus reference-extraction heuristics, probe templates (gh CLI / WebFetch / WebSearch), and classification rules. Load when running `freshen`.
- **`references/trigger-patterns.md`** — The full **Trigger Mode workflow** (T0–T7) plus eval-set construction, mutation patterns by failure type, decision rules, and worked example. Load when running `trigger`.
- **`references/philosophy-patterns.md`** — The full **Philosophy Mode workflow** (P0–P4) plus Boris score interpretation, batch leaderboard, and anti-patterns. Load when running `philosophy`.
- **`references/anthropic-skill-design.md`** — Anthropic's skill design practices, complete frontmatter reference, Agent Skills standard, and platform constraints. Consult when scoring Dimensions 1, 2, 8, and 9.
- **`references/sources.md`** — Dated per-URL index of official docs, specs, changelogs, and blog posts. Freshen Mode reads and stamps `Last verified:` / `Pinned:` fields here.
- **`<skill>/references/improvement-backlog.md`** (per-target, not in skill-improver's own dir) — Carries ceiling findings across skill-improver runs. Read in Phase 0 step 3; updated in Phase 6. Each target skill that has ever been through skill-improver should have one.
- **`<skill>/references/trigger-evals.json`** (per-target) — Persistent eval set for Trigger Mode. Built on first `trigger` run; reused and extended on subsequent runs. Schema: `[{"query": str, "should_trigger": bool, "source": str}, ...]`.

### Scripts

- **`scripts/scan-skills.sh`** — Find all SKILL.md files in profile and project scopes. Outputs paths sorted by modification time.
- **`scripts/batch-workflow.js`** — Reusable `Workflow`-tool driver for batch improve + freshen (recon → apply → blind pipeline, median-of-3 final blind). Skill list comes from `args`. Invoke with `Workflow({scriptPath: "${CLAUDE_SKILL_DIR}/scripts/batch-workflow.js", args: [...]})`. See Batch Mode § Dynamic workflows.
- **`scripts/probe-trigger.py`** — Trigger-mode measurement tool. Adapted from anthropics/skills `skill-creator/scripts/run_eval.py`. Spawns `claude -p` subprocesses against a synthetic slash-command and parses stream-json for `Skill`/`Read` `tool_use` events to compute per-query trigger rate. Supports stratified train/test split, configurable runs-per-query, threshold, and parallelism.
