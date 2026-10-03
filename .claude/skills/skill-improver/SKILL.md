---
name: skill-improver
description: >-
  Autoresearch loop for Claude Code skills — greedy keep/discard hill climbing
  on a 10-dimension quality rubric, with blind subagent validation for
  self-scoring bias. Given only a skill name, it reads that skill's history
  and picks which modes to run. Modes: `score`
  rates a skill out of 100 without editing it; `freshen` probes external
  references (release notes, docs, deprecation signals) and applies verified
  updates; `trigger` measures and tunes the frontmatter description until it
  fires when it should and stays silent when it shouldn't (60/40 train/test,
  7 runs/query); `outcome` runs the skill's eval cases with and without the
  skill through `claude plugin eval`; `ages` prints every skill's verification
  age vs last content change; `floor` measures what a bare model already knows
  about a skill's subject.
when_to_use: >-
  Triggers on "improve a skill", "optimize a SKILL.md", "make my skill better",
  "run skill autoresearch", "self-improve skills", "evaluate skill quality",
  "score my skill", "audit a skill", "rate my skill", "refine skill
  description", "iterate on a skill", "freshen skills",
  "update skill references", "check skill staleness", "is my skill out of
  date", "refresh skill sources", "skill ages", "how old are my skills",
  "list skills by date", "skill not triggering", "skill didn't
  fire", "skill not invoked", "tune skill
  description", "fix skill triggers", "skill under-triggers",
  "skill over-triggers", "false-positive skill",
  "Claude isn't using my skill", "does my skill help", "skill eval",
  or mentions autonomous skill improvement,
  skill quality scoring, skill optimization loops, stale skill content,
  or skill activation problems.
argument-hint: '[improve|score|freshen|trigger|outcome|floor|ages|batch] [<skill-name>|--all|<glob>]'
---

# Skill Improver

`/skill-improver <mode> <target> [--opts]`. `<target>` is a skill name, a
SKILL.md path, `--all`, or a glob (`'vllm-*'`). No mode → **Auto**. No target
(except `ages`, `batch`) → ask.

| Mode | Does | Read first |
|---|---|---|
| Auto | Decides which modes the skill needs, runs them | §Auto |
| `improve` | Keep/discard loop on the 10-dimension rubric | `references/improve-loop.md`, `references/quality-rubric.md` |
| `score` | Rubric score, no edits | §Score |
| `freshen` | Verifies every `sources.md` row online, applies verified updates | `references/freshen-patterns.md` |
| `trigger` | Measures and tunes the description's trigger rate | `references/trigger-patterns.md` |
| `outcome` | Runs the skill's eval cases with vs without it (`claude plugin eval`) | §Outcome |
| `floor` | Measures what a bare model already knows about the subject | `references/floor-patterns.md` |
| `ages` | Fleet table of verification age vs last change | §Ages |
| `batch` | Runs `improve`, `freshen` or `trigger` over many skills | §Batch |

Flags are mode-specific: `--iterations N`, `--probe-budget N`,
`--runs-per-query N`, `--missed "<query>"` (trigger; repeatable — seeds a
user-reported miss as a should-trigger query), `--against <git-ref>` (outcome).

## Auto

1. **Read the evidence, no edits:** the `Freshened:` line in
   `references/sources.md`; one `gh release list --repo <o>/<r> --limit 5` per
   upstream whose version the skill states, compared against the version in the
   skill's text (never assume "no new release"); `git log --format='%ad %s'
   --date=short -- <skill-dir> | head -20`; `references/improvement-backlog.md`
   §Open (has a named blocker arrived?); `disable-model-invocation` and
   `references/trigger-evals.json`; how fast the subject moves.
2. **Decide each step:**

   | Step | Run when |
   |---|---|
   | `freshen` | an upstream is newer than the skill states; or the last pass is old for this subject's pace; or a model or Claude Code release it depends on shipped |
   | `floor` | fact-heavy skill, no floor run since the last model release |
   | `improve` | content changed since the last improve pass, a backlog blocker arrived, or no improve pass on record |
   | `trigger` | description changed or trigger evals fail; never for `disable-model-invocation` |
   | `outcome` | the skill has `evals/evals.json` and its content changed since the last outcome run |

3. **Print the plan** — one line per step: run or skip, with the evidence. Run in
   table order. Nothing due is a valid result: say so and stop.
4. **Report** what ran, what changed, the commits, what was skipped and why.

## Improve

Score, apply ONE change, re-score cold, keep +3 or more; keep +1/+2 only when a
second cold score confirms it or the change also simplifies; keep Δ0 only when
it fixes a verifiable defect; revert the rest. Stop at 90+ with no dimension
below 7, at 5+ discards across 2+ categories, or after 10 iterations.
Re-scoring an unchanged skill moves the total 2–3 points (up to 6), so +2 is
noise. Phases, decision rules and stop conditions: `references/improve-loop.md`.

- **One change per iteration.** State it in 10 words with one verb; an "and"
  means two iterations. A move that starts rewording prose is two changes.
- **The backlog records blockers only.** Every Open entry in
  `<skill>/references/improvement-backlog.md` names the absent thing (a ruling,
  a credential, an unreleased version, a measurement nobody can run now). Effort
  is not a blocker: do it before the pass ends. Format:
  `references/backlog-format.md`.
- **A pass ends with work, not a report.** Done = every keep applied, blind
  score at baseline (on a snapshot) and at stop, the A/B comparator verdict, an
  `outcome` run when the skill has eval cases, committed with the backlog in the
  same commit, resolved items deleted from Open. Zero discards = stopped early.

## Rules for every mode

- **Run without pausing** between iterations; print status lines.
- **State the spend before any fan-out** of subagents or `claude -p` probes:
  calls, model, rough dollars from `scripts/model-rates.json`. Pin a cheap model
  on mechanical work (graders, row probes).
- **Git is the state.** Commit each kept change; `git diff` before reverting.
  Never `rm`: revert with git, put temp dirs and snapshots under a fresh
  `mktemp -d` and leave them.
- **Classify overlap before deleting.** Only `DUPLICATE` is deletable;
  `INTENTIONAL_DETAIL` (summary in SKILL.md, detail in `references/`) and
  `RELATED_BUT_DISTINCT` stay. `scripts/dedup-fleet.py` produces the table;
  `references/improvement-patterns.md` §Pattern 6.1 reads it.
- **Preserve the author's domain knowledge.** Change how the skill teaches, not
  what it teaches.
- **Write for the agent; history goes to `sources.md`.** `SKILL.md` and task
  references state the current rule and the action. Where a fact came from, why
  it changed and when it was checked go in `references/sources.md`; `SKILL.md`
  carries one pointer to it. Keep a version or issue number in agent text only
  where the agent acts on it ("on 0.7.0 every command fails — upgrade").
  Existing history is not a defect by itself; move it when it is in the diff.
- **A failed measurement is NO SCORE, never 0.** A timed-out probe, a dead
  scorer, an errored eval run: exclude it from the denominator and say what is
  missing. An incomplete run is never compared with a complete one; a pass that
  could not measure its mode's evidence is stopped early.
- **The skill outranks training data.** Never change an external claim
  (version, date, flag, model name, SHA) from memory — verify online and cite,
  or drop the change. Wanting to lower a version or move a date back is the
  stale-prior alarm: check first, expect the skill to be right. A subagent's
  "wrong version" finding is applied only after the primary source confirms
  it. Open a new citation and confirm its title, date and the attributed figure
  before writing it down.

## Fleet checks

Run each over the whole tree, not only the skill being edited. Each exits
non-zero on findings and has `--selfcheck`. Read the non-findings column before
acting; detail in `references/fleet-checks.md`.

| Script | Catches | Expected non-findings |
|---|---|---|
| `check-shell-fences.py` | bash fences that do not parse; backslash-then-comment continuations | prompt transcriptions, placeholders |
| `check-yaml-fences.py` | YAML fences that do not parse | Go/Jinja templates, placeholders |
| `check-tables.py` | rows whose cell count disagrees with the header | none |
| `check-links.py` | dead doc-host URLs, moved GitHub file paths | 403, 429 |
| `check-advisory-floors.py` | a CVE floor still vulnerable or outside the advisory range (`--verify`) | per-minor backports, unbounded ranges, negative claims |
| `check-expiring-claims.py` | content dated to become false, relative phrases beside a date | lifecycle tables of future EOL dates |
| `check-issue-states.py` | closed issue called open, PR merge state misdescribed | deliberate "stale bot closed it, still live" wording |

## Blind validation

**Scorer** — the `blind-scorer` agent, spawned with a two-line path tail. Omit
`model` and effort (the definition pins them). Run at baseline (on a snapshot,
in the background) and at stop. Print the bias table: every dimension where
self and blind differ by 2+.

**A/B comparator — decides the pass.** Absolute scores cannot show whether a
pass helped. Extract baseline and final with `git archive` into a `mktemp -d`,
leaving out `evals/` and `improvement-backlog.md`; set every file to one
timestamp; label them `DIR A` / `DIR B` by coin flip; spawn three
`skill-comparator` agents **from outside the repo** (inside, they see recent
commit subjects). Majority gives `IMPROVED` / `NO CHANGE` / `REGRESSED`; a tie
is `NO CHANGE`; `REGRESSED` outranks any score gain — revert the responsible
iteration. Commands and leakage classes: `references/blind-validation.md`.

## Outcome

Rubric and comparator judge the skill's text. `outcome` measures whether the
skill makes the model's answers better:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/outcome-eval.py <skill-dir> [--against <git-ref>] [--write-benchmark]
```

It converts `<skill>/evals/evals.json` into `claude plugin eval` cases (one
grader per assertion), runs each with and without the skill, and with
`--against` the other version too. Prompts force invocation, so the number is
about content; trigger mode measures triggering. Defaults: 3 runs, Sonnet,
Sonnet judge, $20 cap.

- **Price it first:** about $0.15 per with-skill run and $0.05 per without, times
  cases × runs.
- **Read failures before concluding.** Three runs and a 2-of-3 judge vote are
  noisy: a per-case difference of one run, or a total gap under ~0.15, is noise
  until the failed answers are read and found worse.
- **A skill that does not beat the without arm on a case** carries nothing the
  model lacks there — a deletion candidate, confirmed with `floor`.
- `--write-benchmark` writes `evals/benchmark.plugin-eval.json`, which
  `eval-evidence.py` reads for the Dim 10 gate.
- Fewer than 8 cases cannot resolve a delta: grow them with
  `scripts/grow-evals.py` first.

## Score

1. Read the target and `references/quality-rubric.md`.
2. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/eval-evidence.py <skill-dir>`; take
   Dim 10's cap from it, never judge the delta by eye.
3. Score all 10 dimensions with the rubric's template; print the table; name the
   lowest dimension and the single highest-impact fix.
4. Dim 9 capped by `sources.md` staleness → recommend `freshen`. Fewer than 8
   eval cases → recommend `scripts/grow-evals.py`.
5. Stop. Do not start the loop unless asked.

## Freshen

Verify **every** `sources.md` row — delegate rows to cheap subagents in one
background wave (`web-searcher` for web/gh rows, `Explore` for local clones).
Apply one verified finding at a time. End by writing the single
`Freshened: <date>` header stamp; an unreachable row gets an inline exception
note. A partial pass keeps the old stamp. Workflow F0–F6, probe templates and
classification: `references/freshen-patterns.md`.

## Trigger

Metric: trigger rate on an eval set of should- and should-not-trigger queries,
60/40 train/test, 7 runs per query, test scores blinded, description ≤1024
characters. Probe: `scripts/probe-trigger.py`. Eval set:
`<skill>/references/trigger-evals.json`, `[{"query", "should_trigger",
"source", "bucket"}]`, buckets `explicit` / `implicit` / `contextual` /
`negative`. Workflow T0–T7: `references/trigger-patterns.md`.

## Floor

`python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge-floor.py --skill <name> [--extract]`;
fleet: `scripts/floor-fleet.py --root <dir>`. Read-only. Classify the skill
first: on an encoded-preference skill a high floor is expected, not a delete
list. `KNOWS` is a candidate, never a licence to cut; `CONFLICTS` never means
the skill is wrong. `references/floor-patterns.md`.

## Ages

Run `scripts/staleness-report.py [<glob>|<root>]`, print its table verbatim,
then one sentence naming the stalest bucket and the next `freshen` target. No
probes, scoring or edits. `cases` marked `!` = fewer than 8 eval cases; `open`
= backlog Open items — report it when the fleet total moved.

## Batch

`scripts/scan-skills.sh` lists targets. Baseline-score each, run worst first,
cap 5 iterations per skill. The batch is done when every listed skill has a
summary row (skipped, crashed and capped included). With the `Workflow` tool
opted in, use `scripts/batch-workflow.js`
(`args: ["keda", "helm", ...]`); no agent there does git — commit per skill
after review. Size fan-outs to 20 concurrent subagents and the workflow size
guideline.

## Files

| File | Load when |
|---|---|
| `references/improve-loop.md` | running `improve` |
| `references/quality-rubric.md` | scoring |
| `references/improvement-patterns.md` | choosing an improvement |
| `references/freshen-patterns.md` | running `freshen` |
| `references/trigger-patterns.md` | running `trigger` |
| `references/floor-patterns.md` | running or reading `floor` |
| `references/blind-validation.md` | spawning a scorer or comparator |
| `references/fleet-checks.md` | running or proposing a sweep |
| `references/backlog-format.md` | writing a target's `improvement-backlog.md` |
| `references/anthropic-skill-design.md` | scoring Dims 1, 2, 8, 9; frontmatter questions |
| `references/scripts.md` | choosing a script |

Why a rule exists and when it changed: `references/sources.md`.
