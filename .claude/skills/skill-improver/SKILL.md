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
2. Score all 10 dimensions using the scoring template from the rubric.
3. Print the results table. Highlight the lowest dimension and recommend the single highest-impact improvement.
4. If Dim 9 is capped by sources.md staleness (see rubric §Dim 9), recommend running `freshen <skill>` as the single highest-impact next step.
5. Stop. Do not enter the improvement loop unless asked.

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

**Invocation:** `python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge-floor.py --skill <name> [--extract]`

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
- **`<skill>/references/trigger-evals.json`** (per-target) — Persistent eval set for Trigger Mode. Built on first `trigger` run; reused and extended on subsequent runs. Schema: `[{"query": str, "should_trigger": bool, "source": str}, ...]`.

### Scripts

- **`scripts/scan-skills.sh`** — Find all SKILL.md files in profile and project scopes. Outputs paths sorted by modification time.
- **`scripts/eval-evidence.py`** — The blind scorer's only channel into a
  target's `evals/`. That directory is not neutral input: it accumulates prior
  blind totals, kept/discarded records, and regression verdicts, so reading it
  un-blinds the pass exactly as `improvement-backlog.md` does. But it cannot be
  excluded outright — the Negative-Transfer Gate needs `delta_pass_rate` out of
  it. This prints the case count, every `delta_*` measurement with its source
  path, and the Dim 10 cap they imply, and nothing else. Handles all three
  benchmark shapes in the fleet (flat `delta_pass_rate`, a `delta` object, and
  either encoded as a string); an unrecognized one yields the unmeasured cap of
  8 rather than a guess.
- **`scripts/overlap-scan.py`** — Fleet-wide overlap measurement, and the
  empirical input Dim 10 has been missing. Embeds every skill twice via
  SkillEvaluator Tier 2 — `name: description` alone, then the whole SKILL.md —
  because the two answer different questions: description similarity means the
  skills compete for the same **queries** (a trigger problem), body similarity
  means they may duplicate **material** (a Dim 10 problem). The cross-tab of the
  two is the output. **Rank, do not threshold**: upstream's 0.95/0.90/0.75 bands
  come from another model and corpus, and measured here on 68 skills with bge-m3
  the *median* body pair scored 0.789 — above `SIMILAR` — so a
  `--full-body --threshold 0.75` run aborts on the 1000-match cap. It saves
  vectors once and scores locally as z-scores against the fleet's own
  distribution. A lexical-overlap column guards the known artifact: pooling a
  long document measures *register* as much as subject (measured
  `corr(body, lexical) = 0.515`), so two unrelated 400-line operator guides
  score high for both being 400-line operator guides. Endpoint config is env-only
  (`--env-file`); no host is hardcoded and none should be added. `--from-catalogs`
  re-scores offline with no API calls.
- **`scripts/tier1-sweep.py`** — Deterministic pre-scoring gate over a whole
  fleet: invisible Unicode (tag-block smuggling, BiDi overrides), leaked home
  paths, credentials, and Agent-Skills schema violations. No model, no key, no
  network — it wraps NVIDIA SkillEvaluator's keyless Tier 1
  (`validate --checks schema,pii,unicode,lint --no-dedup`). Scores what a skill
  *is*, not what it says, so it catches what no rubric dimension can reach: a
  `U+E0000..E007F` payload renders as nothing in the editor a scorer reads.
  Sorts findings into **actionable** / **review** / **suppressed** because the
  raw gate is unusable here — a measured pass over 105 skills produced 529
  findings (368 excluding two pure-policy checks), 28 actionable, with
  `hardcoded_secrets` 17/17 false (Jinja refs,
  `<placeholder>`, redacted values) and `ip_addresses` matching four-part
  firmware versions. The suppression list names its reason per check; `--all`
  shows everything, `--json` for machine output. Never suppresses credential
  classes — one real key outranks the whole false-positive tail.
- **`scripts/frontmatter-lengths.py`** — Exact `name` / `description` /
  `when_to_use` character counts for one SKILL.md, the combined total against
  the 1,536-char listing cap, and any `description` breach of the 1,024-char
  hard max. The blind scorer calls this for Dim 1 and Dim 9 instead of
  estimating: a scorer was measured reporting 1,120 chars for an 847-char field
  and hard-failing Dim 9 to 3 on the invented number (2026-08-20).
- **`scripts/staleness-report.py`** — Fleet-wide staleness readout, no probes/network: per skill, the `sources.md` `Freshened:` header stamp (or, on legacy files, the oldest per-row `Last verified:` date), its age, dated-row coverage, the Dim 9 staleness cap it implies, last improvement-pass date (from `improvement-backlog.md`), whether trigger/outcome evals exist, and the count of items still under that backlog's `## Open` heading (fleet total in the footer). Stalest first — this is the ranking `freshen --all` uses. `--json` for machine output.
- **`scripts/batch-workflow.js`** — Reusable `Workflow`-tool driver for batch improve + freshen (recon → apply → blind pipeline, median-of-3 final blind). Skill list comes from `args`. Invoke with `Workflow({scriptPath: "${CLAUDE_SKILL_DIR}/scripts/batch-workflow.js", args: [...]})`. See Batch Mode § Dynamic workflows.
- **`scripts/scaffold-probe.py`** — classifies each numbered item as scaffold, criterion, or branch. **Advisory only — it sets no score.** The step-count cap it once fed was withdrawn 2026-08-20: no source states a numeric threshold, Anthropic's degrees-of-freedom guidance recommends explicit steps for fragile or order-dependent work, and SkillLens measured surface format as non-predictive (p > 0.34). Use it to find candidate bloat, then judge fit (quality-rubric §"Procedural steps").
- **`scripts/induced-cost-probe.py`** — what the skill costs to *obey*, which no text dimension measures: pinned effort over cheap modes, unconditional read-everything, uncapped fan-out, over-obedience phrasing. `--refs` to include references, `--selftest` to check the patterns still separate mention from use. Caps Dim 6 at 6 (quality-rubric §"Induced cost").
- **`scripts/floor-fleet.py`** — Fleet driver for Floor Mode. Walks every SKILL.md under a root, runs `knowledge-floor.py` per skill, and writes each result the moment it lands so a multi-hour pass is resumable (`--redo` to force). `--report` re-prints the leaderboard without probing; `--merge <dir,...>` folds a later pass over the same claim sets (e.g. adding a cheaper tier) into one table, columns ordered weakest-to-strongest. Ranks by the share of claims the strongest probed model already knows.
- **`scripts/knowledge-floor.py`** — Floor-mode probe. Extracts checkable factual claims from a skill (cached to `<skill>/references/knowledge-claims.json`), then asks a **bare** `claude -p` — empty project so no skills resolve, every tool denied so the answer is parametric recall — and buckets each answer KNOWS / UNKNOWN / CONFLICTS against the skill's own claim. `--models`/`--efforts` sweep the matrix; each invocation reports its own `total_cost_usd`. See Floor Mode.
- **`scripts/run-cost.py`** — Token and cost accounting for a session, read from its transcript. The agent cannot see its own spend at runtime; the harness records every call's `usage`, so cost is recoverable after the fact. Deduplicates on `requestId` (one request writes one record per content block — summing records overcounts 2x+) and reads `<session>/subagents/agent-*.jsonl` so blind scorers and probe fleets are costed by `agentType` and task. `--json` for machine output, `--list` to enumerate sessions, `--since` to scope to one phase. Also derives **timing** from transcript timestamps — per-model p50 latency and output tokens/sec, plus in-model time against wall time, whose ratio is the effective concurrency a fan-out actually achieved. Throughput runs inverse to capability (haiku 70.7 tok/s → fable 30.2), so this is the column that prices a stronger model in seconds rather than dollars. Rates live in **`scripts/model-rates.json`** (dated; refreshed from the `Model pricing` row in `sources.md`). List API rates — read the dollars as relative sizing between runs, not as an invoice.
#### Eval-corpus maintenance (fleet-wide, not per-run)

These four operate on the *fleet's* `evals/` and floor results rather than on
one skill in one pass. Reach for them when the corpus itself is the problem —
a `delta_pass_rate` that cannot resolve a change, or graded output that is not
trustworthy — not during a normal `improve` or `freshen` run.

- **`scripts/normalize-evals.py`** — Collapses every skill's `evals.json` onto one schema and stamps provenance. An audit found 26 eval files carrying 11 distinct shapes and no record of what wrote them or when; 15 predated the current model by four generations. A stale eval set **defends the stale skill** — a case expecting a reminder an older model needed fails when that reminder is correctly deleted.
- **`scripts/backfill-assertions.py`** — Writes discrete outcome assertions for cases graded only against a prose `expected_output`, which is the subjective text comparison SkillLens measured at 46.4% (worse than chance). Enforces outcome assertions over text-recall ones ("expert parallelism is set correctly for a 2-node MoE deployment", not "mentions `--enable-expert-parallel`").
- **`scripts/grow-evals.py`** — Adds cases until a skill has enough to resolve a change. At the corpus median of 3 cases, one flip moves pass rate 33 points, so `delta_pass_rate` cannot separate "this edit hurt" from "one case is flaky". Floor of 8 (one flip = 12.5 points). New cases are generated to complement the existing prompts, not repeat them.
- **`scripts/regrade.py`** — Re-buckets stored floor-mode answers with a stricter grader, no re-probing. The first fleet pass inflated `CONFLICTS` by dumping agree-with-different-detail and hedged answers into it — the one bucket that can least afford noise, since overriding a confident wrong prior is the whole point of Floor Mode.

- **`scripts/probe-trigger.py`** — Trigger-mode measurement tool. Adapted from anthropics/skills `skill-creator/scripts/run_eval.py`. Spawns `claude -p` subprocesses against a synthetic slash-command and parses stream-json for `Skill`/`Read` `tool_use` events to compute per-query trigger rate. Supports stratified train/test split, configurable runs-per-query, threshold, and parallelism.
