---
name: skill-improver
description: >-
  Autoresearch loop for Claude Code skills — greedy keep/discard hill climbing
  on a 10-dimension quality rubric, with blind subagent validation for
  self-scoring bias, plus a `freshen` mode that probes external references
  (release notes, docs, deprecation signals) and applies verified updates.
when_to_use: >-
  Triggers on "improve a skill", "optimize a SKILL.md", "make my skill better",
  "run skill autoresearch", "self-improve skills", "evaluate skill quality",
  "score my skill", "audit a skill", "rate my skill", "refine skill
  description", "iterate on a skill", "freshen skill", "freshen skills",
  "update skill references", "check skill staleness", "is my skill out of
  date", "refresh skill sources", or mentions autonomous skill improvement,
  skill quality scoring, skill optimization loops, or stale skill content.
argument-hint: '[improve|score|freshen|batch] [<skill-name>|--all|<glob>]'
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

- `<mode>` — `improve` (default) | `score` | `freshen` | `batch`
- `<target>` — skill name (e.g. `gh-cli`), absolute SKILL.md path, `--all`, or glob (e.g. `vllm-*`)
- `[--opts]` — mode-specific flags (e.g. `--iterations 15`, `--probe-budget 30`)

Examples:

```
/skill-improver freshen autoresearch
/skill-improver score gh-cli
/skill-improver improve ~/.claude/skills/helm
/skill-improver batch freshen --all
/skill-improver freshen --group 'vllm-*'
```

If `<mode>` is omitted, default to `improve`. If `<target>` is omitted and mode is not `batch`, prompt the user. For `batch`, the target after `batch` selects the sub-mode (`freshen` or `improve`, default `improve`); the target list comes from `scripts/scan-skills.sh`.

## The Improvement Loop

### Phase 0: Setup

1. Identify the target skill. Accept a path, or run `scripts/scan-skills.sh` (or Glob pattern `**/SKILL.md` under `~/.claude/skills/` and `.claude/skills/`) to list candidates. Do NOT search `~/.claude/plugins/` — those are managed externally.
2. Read the target skill's entire directory: SKILL.md and any references/, examples/, scripts/, assets/ present.
3. Read `references/quality-rubric.md` from the skill-improver directory for the full scoring rubric.
4. Establish a baseline score by evaluating the skill against the rubric.
5. Spawn a blind scoring agent on the baseline (see "Blind Validation" section). First snapshot the skill: `cp -a <skill-dir> /tmp/<skill-name>-baseline`. Then run the agent in the background while the loop proceeds.
6. Initialize a results log (in-memory or scratch file) with header: `iteration | score | delta | status | description`.
7. Log iteration 0 as `baseline`.

### Phase 1: Evaluate (Score the Skill)

Score the skill on 10 dimensions (each 0–10, summed to 0–100) using the detailed criteria and scoring template in `references/quality-rubric.md` (loaded in Phase 0).

### Phase 2: Hypothesize (Pick One Improvement)

Identify the **single lowest-scoring dimension** (or highest-impact if tied). If the
baseline blind agent has returned with flagged dimensions (2+ gap), use the agent's
specific justification text — not just the number — to inform the hypothesis.
Formulate one specific change:

- What to change and why
- Expected score impact
- Complexity cost (lines added/removed, new files)

Consult `references/improvement-patterns.md` for concrete before/after patterns organized by dimension.

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
  **Anomaly check:** If a single change improves the total by +5 or more, be
  suspicious — re-read the change and verify each dimension's delta is justified.
  Self-scoring inflates most on Simplicity and Completeness.
- **Score equal, but simpler** → KEEP. Log as `keep (simplification)`.
- **Score equal or worse** → DISCARD. Revert via `git checkout -- <file>` (or undo the edit if not git-tracked). Log as `discard`.
- **Change broke something** → REVERT. Log as `crash`. Fix and continue.

### Phase 5: Log and Loop

1. Append result to the log: `iteration | score | delta | status | description`.
2. Print a one-line status, e.g.: `[iter 3] score: 74 (+2) — keep — moved API docs to references/api.md`.
3. Go to Phase 2 and pick the next improvement.

**Reflect (every 5 iterations):** Categorize all iterations by type (simplification,
style fix, restructuring, content addition, trigger tuning). If the last 5 were all
the same category, force the next hypothesis to be a different category. Print:
`[reflect] N kept from <category>, pivoting to <new category>`

**Stop conditions:**
- Score reaches 90+ and no dimension is below 7.
- **Ceiling mapped:** 5+ consecutive discards spanning at least 2 different
  improvement categories. This is not failure — it means the skill is near its
  quality ceiling. Report as a positive finding: which categories were tried,
  what the ceiling is, and what would require the author's input to break through.
- Remaining low dimensions require new domain content only the author can provide
  (structural ceiling). Print what's needed and stop.
- User interrupts.
- 10 iterations completed (default cap; user can override).

**On stop:** Spawn a final blind scoring agent (see "Blind Validation"). Print
both comparison tables (baseline + final) and the overall results summary.

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

### Preserve the Author's Intent

The skill reflects the author's domain expertise. Improve structure, clarity, and adherence to best practices. Do NOT rewrite the author's domain knowledge or change what the skill teaches — only how it teaches it.

---

## Blind Validation

Self-evaluation bias is real — the agent that wrote improvements tends to score
them generously. Blind validation uses independent subagents that have never seen
the skill to score it objectively. Run it twice: at baseline and after the loop.

### When to Run

1. **Baseline** — after the self-score in Phase 0 step 4, spawn a blind scoring
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
For Dimension 9: check if appropriate frontmatter fields are used.

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

For the baseline agent, copy the original skill to a temp directory first so
the agent scores the unmodified version even if the loop has already started.

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

Probe a skill's external references for staleness and apply verified updates
in place. Shares the keep/discard loop with the improvement mode but sources
hypotheses from online evidence (release notes, doc commits, deprecation
signals) rather than rubric scores.

### Invocation

- `freshen <skill-path>` — single skill
- `freshen --all` — every skill returned by `scripts/scan-skills.sh`
- `freshen --group <glob>` — subset, e.g., `vllm-*`

Freshen defaults to **apply** — the loop commits verified updates. For a
read-only staleness readout, use Standalone Evaluation (Dim 9 reflects
`references/sources.md` freshness automatically).

### Phase F0: Setup

1. Read the target skill directory (SKILL.md + `references/`).
2. Read `references/freshen-patterns.md` from the skill-improver directory for ref-extraction heuristics and probe templates.
3. Snapshot: `cp -a <skill-dir> /tmp/<skill-name>-freshen-baseline`.
4. Open a findings log: `id | ref | skill-says | current | classification | action`.

### Phase F1: Extract References

Precedence (extractors defined in `freshen-patterns.md` §1):

1. `references/sources.md` rows — authoritative refs with prior `Last verified` / `Pinned` markers.
2. SKILL.md + other reference-file scan — URLs, `owner/repo` patterns, CLI names with versions, semver strings, API paths, dated claims.
3. Deduplicate (normalize URLs, collapse owner/repo variants).

If the target skill has no `sources.md`, create one in Phase F6 from the extracted set so future freshens have a baseline.

Mark rows with `<!-- ignore-freshen -->` to exclude refs the author deliberately keeps as-is (e.g., historical references).

### Phase F2: Probe

For each ref, run the cheapest applicable probe first (templates in `freshen-patterns.md` §2). Stop probing a ref as soon as it produces a finding.

Default probe budget: **20 per skill, 100 per batch run**. On budget exhaustion, stop probing and summarize; flag the skill `partial-freshen` in the log.

### Phase F3: Classify

| Class | Action |
|-------|--------|
| `fresh` | Stamp `Last verified: <today>` on the sources.md row; no content change |
| `version-drift` | Hypothesis: bump pinned version + version-specific guidance |
| `deprecation` | Hypothesis: replace deprecated API / flag with current equivalent |
| `new-feature` | Hypothesis: add a ≤3-line note IFF feature maps to an existing trigger phrase in the skill's `description` / `when_to_use` |
| `broken` | Hypothesis: update or remove the ref |
| `unverifiable` | Leave unchanged; note the ambiguity in the log |

Only drift, deprecation, new-feature, and broken produce mutation hypotheses.

### Phase F4: Mutate (One Finding at a Time)

Same atomicity rule as the improvement loop — one finding per iteration, diff minimal, cause attributable. Always cite the verifying source URL.

### Phase F5: Accept / Revert

Decision rule (different from score-based loop — verification-based):

- **Verified source + ≤ equal complexity** → KEEP. Update sources.md with new `Last verified:` (and `Pinned:` if relevant). Commit per `freshen-patterns.md` §4.
- **Unverified** (single unofficial source, probes ambiguous) → DISCARD. Do not guess.
- **>20 added lines for one finding** → DISCARD and flag for human review in the summary.
- **Breaks self-consistency** (orphans a section, contradicts another part) → REVERT.

### Phase F6: Stamp and Summarize

1. Any ref that probed successfully — fresh or updated — gets `Last verified: <today>` in sources.md.
2. If sources.md was absent at Phase F1, create it now from the successfully-probed refs.
3. Print summary: total findings, kept, discarded, unverifiable, flagged-for-review.
4. Stop. Do not re-probe the same skill in the same session.

### Batch Mode

`freshen --all` iterates skills sequentially:

1. Scan scope via `scripts/scan-skills.sh`.
2. Rank by sources.md staleness (oldest `Last verified:` first; missing dates sort last).
3. Cap findings-per-skill at 5 in batch mode.
4. Share the 100-probe global budget across the batch; stop early on exhaustion.
5. Print ranked summary: skill, findings, kept, new stamp date.

### Anti-Patterns

- Do NOT replace concrete guidance with "see release notes" — extract the specific change.
- Do NOT bump a pinned version without checking the breaking-change section — pins often exist for reasons a diff can't see.
- Do NOT trust a single social-media post — require an authoritative source (official docs, release notes, merged PR, maintainer issue response).
- Do NOT rewrite content unrelated to a finding — each mutation is scoped to its finding.

---

## Additional Resources

### Reference Files

- **`references/quality-rubric.md`** — Full scoring rubric with sub-criteria, examples of each score level, and common failure patterns. Load this before scoring.
- **`references/improvement-patterns.md`** — Catalog of common improvements organized by dimension, with before/after examples.
- **`references/freshen-patterns.md`** — Reference-extraction heuristics, probe templates (gh CLI / WebFetch / WebSearch), and classification rules for Freshen Mode.
- **`references/anthropic-skill-design.md`** — Anthropic's skill design practices, complete frontmatter reference, Agent Skills standard, and platform constraints. Consult when scoring Dimensions 1, 2, 8, and 9.
- **`references/sources.md`** — Dated per-URL index of official docs, specs, changelogs, and blog posts. Freshen Mode reads and stamps `Last verified:` / `Pinned:` fields here.

### Scripts

- **`scripts/scan-skills.sh`** — Find all SKILL.md files in profile and project scopes. Outputs paths sorted by modification time.
