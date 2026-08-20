---
name: skill-improver
description: >-
  Autoresearch loop for Claude Code skills — greedy keep/discard hill climbing
  on a 10-dimension quality rubric, with blind subagent validation for
  self-scoring bias, plus a `freshen` mode that probes external references
  (release notes, docs, deprecation signals) and applies verified updates,
  plus a `trigger` mode that measures and tunes the skill's frontmatter
  description until it reliably fires when it should and stays silent when
  it shouldn't (60/40 train/test split, 7 runs/query, blinded test scores),
  plus an `ages` mode that prints a fleet-wide table of every skill's
  verification age vs last content change, no probes.
when_to_use: >-
  Triggers on "improve a skill", "optimize a SKILL.md", "make my skill better",
  "run skill autoresearch", "self-improve skills", "evaluate skill quality",
  "score my skill", "audit a skill", "rate my skill", "refine skill
  description", "iterate on a skill", "freshen skill", "freshen skills",
  "update skill references", "check skill staleness", "is my skill out of
  date", "refresh skill sources", "skill ages", "how old are my skills",
  "list skills by date", "skill not triggering", "skill didn't
  fire", "skill won't trigger", "skill not invoked", "tune skill
  description", "fix skill triggers", "skill under-triggers",
  "skill over-triggers", "false-positive skill", "make skill trigger",
  "Claude isn't using my skill", or mentions autonomous skill improvement,
  skill quality scoring, skill optimization loops, stale skill content,
  or skill activation problems.
argument-hint: '[improve|score|freshen|trigger|philosophy|ages|batch] [<skill-name>|--all|<glob>]'
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

- `<mode>` — `improve` (default) | `score` | `freshen` | `trigger` | `philosophy` | `ages` | `batch`
- `<target>` — skill name (e.g. `gh-cli`), absolute SKILL.md path, `--all`, or glob (e.g. `vllm-*`)
- `[--opts]` — mode-specific flags (e.g. `--iterations 15`, `--probe-budget 30`, `--runs-per-query 5`)

Examples:

```
/skill-improver ages
/skill-improver ages 'vllm-*'
/skill-improver freshen autoresearch
/skill-improver score gh-cli
/skill-improver improve ~/.claude/skills/helm
/skill-improver trigger vllm-caching
/skill-improver trigger gh-cli --missed "find issue with label X"
/skill-improver batch freshen --all
/skill-improver freshen --group 'vllm-*'
```

If `<mode>` is omitted, default to `improve`. If `<target>` is omitted and mode is not `batch`, prompt the user. For `batch`, the target after `batch` selects the sub-mode (`freshen`, `improve`, `trigger`, or `philosophy`, default `improve`); the target list comes from `scripts/scan-skills.sh`. The `--missed "<phrase>"` flag (trigger mode only, repeatable) seeds the eval set with user-reported failures as gold should-trigger queries.

## The Improvement Loop (default mode)

Greedy hill climbing on the 10-dimension rubric: score the skill, apply ONE
change, re-score cold, keep only what moves the metric (+2, or +1 with net
simplification), revert everything else; stop at 90+ with no dim below 7, a
mapped ceiling (5+ discards across 2+ categories), or the 10-iteration cap.

**A +2 movement is inside the scorer's own noise** (measured 2026-08-20:
re-scoring an unchanged skill moves the total by a median of 2-3 points and up
to 6 on frontier models — `references/blind-validation.md` §Measured scorer
behaviour). Treat a bare +2 as *undecided*, not as a keep: confirm it with a
second cold score, or keep it only when the change also simplifies. Rankings
between skills are stable under that noise; single-iteration totals are not.

The full phase workflow — **Phase 0 Setup → Phase 7 Land it**,
including the cold-score discipline, the hypothesis criteria (simplicity,
weakness, format-only), the keep/discard decision rules with the anomaly
gate and noise zone, and the stop conditions — lives in
**`references/improve-loop.md`**. Read it before starting a run; every rule
that decides keeps and discards is there.

Three rules that bind without reading it:

- **One change per iteration, diff minimal.** Bundling attributes the score
  lift to the wrong cause, so the next loop pivots to the wrong category.
- **The backlog records blockers, not leftovers.** Persist ceiling findings to
  `<skill>/references/improvement-backlog.md` (`references/backlog-format.md`)
  — but every Open entry must **name the absent thing** that prevents the work:
  a ruling, a credential, an unreleased version, a measurement nobody can run
  now. Effort is not a blocker. If the honest answer is "nothing, it is just
  work", do it before the pass ends; a pass may not end having added an
  unblocked item under any heading.
- **A pass ends with work, not a report of work.** Done = every keep applied +
  **both** blind scores on record (baseline at setup on a snapshot, final on
  stop — one alone is self-scored) + committed with the backlog in the same
  commit + resolved items deleted from Open. Zero discards means no ceiling was
  mapped: record that as stopped early, never as finished (Phase 7).

---

## Operating Rules

### Never Stop (Unless Asked)

Run the loop continuously. Do not ask permission between iterations. The user may be away. Print status lines so they can review when they return.

### State the Spend Before a Fan-out

Any wave of subagents or `claude -p` probes — a batch pass, a freshen wave, a
floor fleet, a trigger eval — gets a one-line estimate before it starts: how
many calls, on which model, and the rough dollar size from
`scripts/model-rates.json`. `scripts/run-cost.py` prices a run afterwards, which
is too late to decide against it.

Two things this catches, both observed: probes inheriting the session model when
a cheap one would do (a grader that only checks text against assertions does not
need the strongest model), and optional work being started because a rubric cap
*could* be cleared rather than because clearing it was worth the spend. **A cap
is a resting state, not a task** — the unmeasured Dim 10 cap in particular is
documented as deliberate. Reaching for it is a choice that costs money, so
price it first and say the number.

### Git as State Machine

When improving skills in a git-tracked directory:
- Commit each kept improvement individually.
- Use `git diff` to show what changed on discard before reverting.
- The branch tip always represents the best-known version.

### Prioritize Deletion Over Addition

In practice, removing redundant content produces the largest per-iteration score gains. When choosing between an additive improvement (+1 from adding content) and a subtractive one (+1 from deleting content), prefer deletion — it improves simplicity as a side effect.

**But similar is not redundant, and this bias is exactly what gets that wrong.**
Before deleting on the grounds that two passages overlap, classify the overlap:
only `DUPLICATE` is actionable, while `INTENTIONAL_DETAIL` (an overview in
SKILL.md developed in `references/`) and `RELATED_BUT_DISTINCT` (same topic,
different purpose) must be kept — the first of those *is* progressive
disclosure, the structure a good skill is meant to have. Measured across the
whole fleet — 62 skills, 520 clusters — **83% of similar-looking content was
correct as written** (292 INTENTIONAL_DETAIL + 138 RELATED_BUT_DISTINCT vs 90
real duplicates). Those 430 clusters are what a deletion bias would have cut.
`scripts/dedup-fleet.py` produces that table; `references/improvement-patterns.md`
§Pattern 6.1 explains how to read it.

### One File at a Time

Each iteration targets one file. If the improvement requires touching multiple files (e.g., moving content from SKILL.md to references/), that counts as one atomic change.

**The split test for atomicity.** "Atomic" is not a word — it is a constraint. State the change in 10 words, present-tense, single verb. "Move gotchas section to references/gotchas.md." If the honest sentence needs an "and" — "move content to references/ AND fix second-person AND tighten terminology" — it is three iterations, not one. Pure relocation is allowed; relocation that quietly rewrites prose is not. If a structural move starts editing a sentence's wording, stop, finish the move with the prose unchanged, score, then propose the prose edit as the next iteration. The reason: bundled iterations attribute the score lift to the wrong cause, which means future loops will pick the wrong category to pivot to.

### Preserve the Author's Intent

The skill reflects the author's domain expertise. Improve structure, clarity, and adherence to best practices. Do NOT rewrite the author's domain knowledge or change what the skill teaches — only how it teaches it.

### A Measurement That Failed Is Not a Low Score

Every mode here turns evidence into a number, and every one of them can fail to
collect a piece of it — a `claude -p` probe that times out, a blind scorer that
dies, an eval case that errors, a source row that cannot be reached. **Never let
the gap become a value.** Report it as `NO SCORE`, exclude it from the
denominator, and say what is missing.

Coercing to zero is not the conservative choice; it is a fabricated
measurement, and it biases in whichever direction the metric happens to run:

- A timed-out trigger probe scored as "did not fire" deflates should-trigger
  queries *and* inflates should-NOT-trigger ones, so a completely broken probe
  reports a plausible mid-range number built out of nothing.
- A floor run whose probes all failed reads as 0% known — the "every claim is
  real transfer" row — so the failure *raises* the Dim 10 cap.
- A missing blind score filled in from the self-score reinstates exactly the
  bias the blind check exists to remove.

The rule is the same in each case: an incomplete run must not be compared
against a complete one, and a pass that could not measure its own mode's
evidence is **stopped early**, never finished. `freshen` has always worked this
way — "the stamp never lies", a partial pass keeps the old date. This is that
rule everywhere else.

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
- **A new citation is a claim too — verify it before writing it down.** The rule
  above covers *altering* an existing claim; the recurring failure has been
  *adding* one. Before a paper, post, issue, or doc URL enters any file, open it
  and confirm the title, the author, the date, and that the specific number or
  finding being attributed is actually there. A plausible-looking arXiv ID is not
  a source. Where a research agent supplied the citation, the check is a separate
  step from the research — an agent asked only "is this real?" catches what the
  agent that found it will not. Both known instances were caught this way, and
  the ones that slipped through (`e379abd`) were not checked at all. If a detail
  cannot be confirmed on the page, cite the paper without it rather than
  repeating the unverified figure.

---

## Blind Validation

Self-evaluation bias is real — the agent that wrote improvements tends to score
them generously. Blind validation uses independent subagents that have never seen
the skill to score it objectively. Run it twice: at baseline (improve-loop
Phase 0 step 6, in the background, parallel with the loop) and after the
loop stops (improve-loop §"On stop") — the spawn points the loop itself
already marks.

### Scorer Agent, Model Rule, and Comparison Table

The scorer is the **`blind-scorer` agent definition** (canonical instruction
text; spawn it with a two-line path tail so every scorer in a run shares the
cached prefix). The spawn mechanics, fallback chain, model rule, parallel-
scoring variant, and bias-check table format live in
**`references/blind-validation.md`**. Read it when spawning either agent.
Two rules that bind without reading it: **omit `model` in the spawn call** —
the agent definition pins it (`model: sonnet`), so baseline and final match by
construction — and inherit the session effort (omit it too; it was measured
flat) — and print the
bias-check table after each agent returns, flagging every dimension where self
and blind differ by 2 or more.

---

## Batch Mode

To improve multiple skills:

1. Run `scripts/scan-skills.sh` to find all SKILL.md files in scope.
2. Score each skill (baseline only) and print a ranked table.
3. Sort by score ascending (worst first).
4. Run the improvement loop on each, starting from the worst. Cap at 5 iterations per skill in batch mode.
5. Print a final summary table: skill name, baseline score, final score, delta, number of kept changes. The batch is done when **every skill from step 1 has a row** — including skills whose loop was skipped, crashed, or hit the cap (mark the status). A missing row is silent truncation, not a smaller batch.

**Dynamic workflows (Fable 5 / Opus 5, Claude Code v2.1.154+).** Batch mode is multi-agent orchestration — when the user has opted into the `Workflow` tool, reuse the saved driver `scripts/batch-workflow.js` (a recon→apply→blind pipeline, median-of-3 final blind): `Workflow({scriptPath: "${CLAUDE_SKILL_DIR}/scripts/batch-workflow.js", args: ["keda", "helm", ...]})`. `args` takes bare names, absolute dirs, or `{dir, hints}` objects. Per-skill loops keep one change per iteration so cause stays attributable; recon and apply agents inherit the session model and effort; blind scorers are pinned to Sonnet 5, same as a solo run, and no agent does git ops — commit per-skill after review. Without opt-in, run skills sequentially as above.

**Native loops (Claude Code `/loop` v2.1.71+, `/goal` v2.1.139+).** For recurring or goal-driven runs, drive this skill with the harness's loop primitives: `/loop <interval> /skill-improver batch freshen --all` for scheduled passes, or `/goal` with a checkable stop ("every skill scores ≥85, stop after N tries") — `/goal`'s evaluator-checked stop condition maps directly onto this skill's scalar metric. Size batch fan-outs against two live caps: **20 concurrent subagents** (v2.1.217 default, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) and the **medium workflow size guideline of <15 agents** (v2.1.219 default, `workflowSizeGuideline`) — a batch wider than these queues silently or trips a guideline warning mid-run. The per-session subagent cap is gone: **v2.1.224 removed it**, so total agent count no longer bounds a `--all` pass; concurrency does. Official guidance: https://claude.com/blog/getting-started-with-loops (2026-06-30).

---

## Standalone Evaluation (No Loop)

When the user only wants a quality score without iterating:

1. Read the target skill and `references/quality-rubric.md` from the skill-improver directory.
2. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/eval-evidence.py <skill-dir>` and take Dim 10's cap from it — never judge the delta's sign by eye. It also prints the case count and noise floor.
3. Score all 10 dimensions using the scoring template from the rubric.
4. Print the results table. Highlight the lowest dimension and recommend the single highest-impact improvement.
5. If Dim 9 is capped by sources.md staleness (see rubric §Dim 9), recommend running `freshen <skill>` as the single highest-impact next step.
6. If step 2 reported fewer than 8 cases, recommend `scripts/grow-evals.py` — a corpus that small cannot resolve a delta and quietly defends the skill it tests. No eval set at all is a different finding: the cap is correct and needs no fix.
7. Stop. Do not enter the improvement loop unless asked.

**`/doctor` is the first-party sibling, not a substitute.** Anthropic ships
`claude doctor` / `/doctor` to "rightsize your skills, and CLAUDE.md files"
([context-engineering blog](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models),
2026-07-24; bundled skill since v2.1.205). It is a one-shot simplification pass
with no metric, no keep/discard, and no blind check — run it first for free
hypotheses, then use this skill when the question is *did the change measurably
help*. Do NOT report `/doctor` output as a score.

**Dim 10 is capped until net value is measured** — apply the rubric's
§"Negative-Transfer Gate" (8 unmeasured, 2 when the skill loses to no-skill;
measuring means `delta_pass_rate`, not a judgement about the text).

**Scope boundary — every metric here scores the skill's *text*, never its
outputs.** SkillLens measured text-only judging at 46.4% accuracy against real
utility, so a rising rubric score is not evidence the skill's results improved.
To measure that, run the official skill-creator plugin's eval loop (`/plugin
install skill-creator@claude-plugins-official`): assertions in `evals/evals.json`,
one clean-context subagent per case, with-skill vs without-skill `benchmark.json`,
blind A/B between versions. Methodology:
https://agentskills.io/skill-creation/evaluating-skills

---

## Freshen Mode

Probe a skill's external references for staleness and apply verified updates in
place — same keep/discard loop as `improve`, but hypotheses come from online
evidence (release notes, doc commits, deprecation signals), not rubric scores.
A pass verifies **every** sources.md row (delegated to cheap subagents —
`web-searcher` for web/gh rows, `Explore` for local-clone rows — in one
background wave) and ends by writing the single `Freshened: <date>` header
stamp; unverifiable rows get inline exception notes. No per-row dates.

**Invocation:** `freshen <skill-path>` · `--all` · `--group <glob>`. Defaults to
**apply**. For a read-only staleness readout — "how old are my skills?", which
to freshen first — use `ages` mode instead (fleet-wide table in one command,
no probes); Standalone Evaluation covers the single-skill case (Dim 9 tracks
`sources.md`).

Full phase workflow (F0→F6), batch mode, and anti-patterns live in
**`references/freshen-patterns.md` §"Freshen Mode Workflow"** with the extraction
heuristics, probe templates, and classification rules. Read it when running `freshen`.

---

## Trigger Mode

Measure and tune a skill's frontmatter `description` (and `when_to_use`) so it
fires when it should and stays silent when it shouldn't. Same keep/discard
hill-climbing as `improve`, but the metric is **trigger rate against an eval
set** — the methodology Anthropic's `skill-creator` uses (60/40 train/test,
7 runs/query for decisions, blinded test scores, ≤1024-char cap).

**Use trigger mode when:** a user reports "the skill didn't fire" / "Claude isn't
using my skill", or a description is too vague, narrow, or keyword-collision-y.
Trigger-mode measures Dim 1 empirically via `claude -p` (`scripts/probe-trigger.py`).

Full phase workflow (T0 Setup → T7 Apply/persist), batch mode, and anti-patterns
live in **`references/trigger-patterns.md` §"Trigger Mode Workflow"** with the
eval-set construction rules, probe mechanism, and mutation patterns. Read it when
running `trigger`.

---

## Ages Mode

Read-only fleet readout — no probes, no scoring, no mutation. Run
`scripts/staleness-report.py` and print its table verbatim, then one
sentence naming the stalest bucket and the suggested next `freshen` target.
That is the whole mode; do not start scoring or freshening from it.

**Invocation:** `ages` (whole fleet) · `ages <glob>` (e.g. `ages 'vllm-*'`) ·
`ages <root-dir>`. Two date tracks per skill: `oldest`/`age` = when the
skill's external claims were last verified — the sources.md `Freshened:`
header stamp (rows shows `full`), or for legacy files the oldest per-row
date — vs `changed` = last content change on disk (newest file mtime). A
skill can be freshly edited yet stale on verification — and vice versa; the
`cap` column shows the Dim 9 staleness cap the verification age implies.

The `cases` column counts outcome eval cases and marks `!` below 8. **A skill
with an eval set is not the same as a skill that can be measured**: one case
flipping moves the pass rate by `1/n`, so a 3-case corpus resolves nothing under
0.33 and quietly defends the skill it exists to test. This is the only place the
fleet reports that gap — `eval-evidence.py` computes the same floor per skill,
but nothing would ever run it on a corpus nobody had flagged. Act on `!` rows
with `scripts/grow-evals.py`, then re-run the benchmark.

The `open` column counts items under `## Open` in each
`improvement-backlog.md`, with a fleet total in the footer. Read it as a
deferral signal, not a workload: an entry earns its place there only when
something external blocks the work, so a count that only ever rises is
recording work that was parked rather than blocked. Report it in the `ages`
summary sentence whenever the fleet total moved since the last run.

---

## Floor Mode

Measure what a **bare** model already knows about the skill's subject — no
skills loaded, no tools, no web. Whatever the model knows unaided does not need
to be in the skill; as the bleeding edge is absorbed into training, the skill
should shrink to the delta. Read-only: surfaces candidates, never edits.

**Invocation:** one skill — `python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge-floor.py --skill <name> [--extract]`
· whole fleet — `python3 ${CLAUDE_SKILL_DIR}/scripts/floor-fleet.py --root <dir>`, which
writes each result as it lands so a multi-hour pass is resumable, and ranks by the
share of claims the strongest probed model already knows.

The skill is its own answer key. Claims are extracted once to
`<skill>/references/knowledge-claims.json` (cached, hash-stamped against
SKILL.md) and each is put to the bare model across a model × effort matrix.
Three buckets:

| Bucket | Meaning | Action |
|---|---|---|
| **KNOWS** | model states the claim correctly | deletion **candidate** |
| **UNKNOWN** | does not know, or hedges | keep — real knowledge transfer |
| **CONFLICTS** | confidently states something else | keep, and make it louder |

`CONFLICTS` is the valuable bucket: filling a blank is worth something,
overriding a confident wrong prior is worth more, because unaided the model
does not hesitate — it proceeds, wrong.

Two limits bind. **Recall is not application** — a model can state a flag and
still not think to use it mid-task, so `KNOWS` is a candidate to confirm with
an eval delta, never a licence to cut. And **a conflict never means the skill
is wrong**: skills here are freshened past the model cutoff, so the skill is
presumed correct and the model presumed stale (§"The Skill Outranks Training
Data"). The grader prompt encodes this; without it the probe becomes a
downgrade machine.

Re-run on each model release — the movement in `KNOWS` is the delete list.

Floor results are also a **rubric input**: they move the unmeasured Dim 10 cap
off its flat `8`, and they classify the skill into one of three profiles —
deletion candidate, pure transfer, or correction skill. A high floor with
durable conflicts means *louder*, not leaner. See
`references/quality-rubric.md` § Negative-Transfer Gate.

---

## Philosophy Mode

Cheap weekly check that runs the three Boris-derived signals as one
pass without spinning up the full 10-dim rubric or the trigger eval set.
Sibling to `freshen` and `trigger`. All three signals are grounded in
the first-party context-engineering blog (2026-07-24); the podcast
origin the name comes from is **unverified** — the X row that carried it
was browser-read 2026-08-20 and does not contain the claims (`sources.md`).
Output is a Boris score (0-3 anti-patterns flagged) plus the existing dim
caps that fire as a side-effect.

**Invocation:** `philosophy <skill-name>` · `batch philosophy --all`.
Surfaces findings only — never auto-applies mutations; the operator decides.

Full phase workflow (P0 Setup → P4 Persist), Boris score interpretation,
batch leaderboard, and anti-patterns live in
**`references/philosophy-patterns.md`**. Read it when running `philosophy`,
along with the three check sections P0 uses: `quality-rubric.md` §"Boris
Alignment Check", `freshen-patterns.md` §"4b. Scaffolding Decay Probes",
`trigger-patterns.md` §"Minimalism test (Boris alignment)".

---

## Additional Resources

### Reference Files

- **`references/improve-loop.md`** — The full **Improvement Loop workflow** (Phases 0–6): setup, cold scoring, hypothesis criteria, keep/discard decision rules, stop conditions, backlog persistence. Load when running `improve` (the default mode).
- **`references/quality-rubric.md`** — Full scoring rubric with sub-criteria, examples of each score level, and common failure patterns. Load this before scoring.
- **`references/improvement-patterns.md`** — Catalog of common improvements organized by dimension, with before/after examples.
- **`references/freshen-patterns.md`** — The full **Freshen Mode workflow** (F0–F6) plus reference-extraction heuristics, probe templates (gh CLI / WebFetch / WebSearch), and classification rules. Load when running `freshen`.
- **`references/trigger-patterns.md`** — The full **Trigger Mode workflow** (T0–T7) plus eval-set construction, mutation patterns by failure type, decision rules, and worked example. Load when running `trigger`.
- **`references/philosophy-patterns.md`** — The full **Philosophy Mode workflow** (P0–P4) plus Boris score interpretation, batch leaderboard, and anti-patterns. Load when running `philosophy`.
- **`references/blind-validation.md`** — The blind-scorer agent, model rule, fallback chain, parallel-scoring variant, and bias-check table format. Load when spawning a baseline or final blind agent.
- **`references/backlog-format.md`** — The `Open` / `Resolved this pass` section shapes, admission rules, and append-only history rule. Load when writing a target skill's `improvement-backlog.md` in Phase 6.
- **`references/anthropic-skill-design.md`** — Anthropic's skill design practices, complete frontmatter reference, Agent Skills standard, and platform constraints. Consult when scoring Dimensions 1, 2, 8, and 9.
- **`references/sources.md`** — Index of official docs, specs, changelogs, and blog posts, one row per URL with an optional `Pinned:` version or git ref. Freshen Mode probes every row and writes the single `Freshened: <date>` header stamp; per-row dates are legacy.
- **`<skill>/references/improvement-backlog.md`** (per-target, not in skill-improver's own dir) — Carries ceiling findings across skill-improver runs. Read in Phase 0 step 3; updated in Phase 6. Each target skill that has ever been through skill-improver should have one.
- **`<skill>/references/trigger-evals.json`** (per-target) — Persistent eval set for Trigger Mode. Built on first `trigger` run; reused and extended on subsequent runs. Schema: `[{"query": str, "should_trigger": bool, "source": str, "bucket": "explicit"|"implicit"|"contextual"|"negative"}, ...]`. The bucket splits positives by how the user phrases the request — see `trigger-patterns.md` §Phase T1 for the target mix and why `contextual` is the one that goes missing.

### Scripts

Every script, what it measures, and the failure it prevents:
**`references/scripts.md`**. Load it when choosing a tool for a phase.
