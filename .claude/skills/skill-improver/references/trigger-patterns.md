# Trigger Patterns — Make Skills Actually Fire

Reference for the `trigger` mode of skill-improver. Covers eval-set
construction, the probe mechanism, mutation patterns for fixing under-trigger
and over-trigger, and the keep/discard rules specific to trigger-rate scoring.

Methodology mirrors Anthropic's official `skill-creator` description-optimization
loop (60/40 train/test, blinded test scores, ≤1024-char hard cap), except on
runs-per-query: skill-creator uses 3, this skill decides at 7 — see the noise
floor in §"Phase T5"
documented at `references/sources.md` (Skill authoring best practices,
anthropics/skills `improve_description.py`, `run_eval.py`, `run_loop.py`).

## Table of Contents
- [Trigger Mode Workflow](#trigger-mode-workflow)
- [Why skills under-trigger](#why-skills-under-trigger)
- [Eval-set construction](#eval-set-construction)
- [The probe mechanism](#the-probe-mechanism)
- [Mutation patterns by failure type](#mutation-patterns-by-failure-type)
- [Decision rules](#decision-rules)
- [Anti-patterns](#anti-patterns)
- [Worked example](#worked-example)

## Trigger Mode Workflow

Measure and tune a skill's frontmatter `description` (and `when_to_use`) so it
reliably fires when it should and stays silent when it shouldn't. Same
keep/discard hill-climbing structure as `improve`, but the metric is **trigger
rate against an eval set** — exactly the methodology Anthropic's own
`skill-creator` uses for description optimization (60/40 train/test split,
blinded test scores, ≤1024-char hard cap) — but at 7 runs/query, not
skill-creator's 3, for the reason in Phase T5.

**Use trigger mode when:** a user reports "the skill didn't fire when I asked
X", "Claude isn't using my skill", or a description looks too vague,
too narrow, too keyword-collision-y, or simply written in the wrong vocabulary
for how users actually phrase requests. Score-mode bumps Dim 1 (Trigger
Precision) on subjective rubric judgment; trigger-mode measures it empirically.

The eval-set construction rules, mutation patterns, decision tree, and worked
example are the sections that follow in this file.

### Phase T0: Setup

1. Read the target skill (SKILL.md frontmatter, body, references/).
2. **Invocation gate — should this skill model-trigger at all?** A
   description is permanent context load on every turn. If the evidence
   says the user only ever fires the skill by hand — the request that
   started this run was "make `/name` work", the backlog and git history
   show exclusively slash invocations, or the user confirms it — the
   correct mutation is `disable-model-invocation: true`, which removes
   the description from the always-loaded listing entirely. Apply it,
   rewrite `description` as a human-facing one-liner (trigger phrases
   stripped), and stop: the rest of trigger mode measures a gate this
   skill no longer has. Only proceed to T1 when model-triggering is
   actually wanted.
3. Read `<skill>/references/improvement-backlog.md` if present — open
   "trigger" findings carry forward.
4. Review the mutation patterns and decision rules in the sections below.
5. Snapshot the skill: `cp -a <skill-dir> /tmp/<skill-name>-trigger-baseline`.
6. Initialize a results log: `iter | train | test | desc-chars | status | change`.

### Phase T1: Build (or load) the eval set

Look for `<skill>/references/trigger-evals.json`. If present, use it as the
starting eval set and append any new user-reported failures from `--missed
"<phrase>"` flags as new should-trigger entries.

If absent, construct a fresh eval set per §"Eval-set construction" below:

- 6–8 should-trigger queries: prioritise user-reported failures verbatim;
  fill the rest with description paraphrases, body-mined examples, and
  everyday user vocabulary.
- 5–7 should-NOT-trigger queries: keyword-collision distractors,
  sibling-skill territory, generic conversation, adjacent-domain decoys.

Save to `<skill>/references/trigger-evals.json`. The file persists so future
trigger-mode runs build on the same eval baseline.

### Phase T2: Probe baseline

Run the probe with a stratified train/test split:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path <skill-dir> \
  --eval-set <skill-dir>/references/trigger-evals.json \
  --holdout 0.4 --runs-per-query 7 --num-workers 7 --verbose
```

The probe installs the candidate description as a real **skill** in a fresh
isolated temp project (`<tmp>/.claude/skills/<id>/SKILL.md` — Claude auto-invokes
skills, NOT `.claude/commands/` entries), runs `claude -p "<query>"` with
`--output-format stream-json --verbose --include-partial-messages`, and scans
the whole turn for a `Skill`/`Read` `tool_use` whose input references the
synthetic id. Each query runs N times to measure trigger rate; rate >=
threshold counts as triggered.

Read the JSON output: `train.summary` and `test.summary` carry pass/fail
counts; per-query records carry `trigger_rate` for diagnosing the failure
type.

If the `claude` CLI is missing or unauthenticated, the probe fails fast.
Fall back to manual A/B testing per §"Fallback when `claude -p` is not
available" below — print the candidate description and the eval
set, ask the user to spot-check from a fresh session. Do NOT use a subagent
to "guess" trigger behavior; the agent will roleplay, not measure.

### Phase T3: Hypothesize

Categorise the train-set failures and pick ONE mutation type per
§"Mutation patterns by failure type" below:

| Failure profile | Pattern |
|---|---|
| All failures are should-trigger misses (under-trigger) | T1 — add explicit phrases, be pushier, front-load |
| All failures are should-NOT false-positives (over-trigger) | T2 — add negative boundary, tighten scope |
| Mixed under + over | T3 — fix whichever class has more failures first |
| Fractional trigger rates dominate (not 0.00/1.00) | T4 — the measurement is underpowered before it is a mutation problem: re-measure the disputed queries at N=7+ (§T5 noise floor) before proposing any edit |
| Cap-bound: description hits 1024 chars | T5 — re-balance into description vs when_to_use |
| Sibling skill steals the trigger | T6 — backlog finding, NOT single-skill mutation |

### Phase T4: Mutate

Apply ONE change to the frontmatter (description and/or when_to_use). Hard
constraints:

- `description` ≤ 1024 chars (Agent Skills spec hard cap; descriptions over
  that are rejected by `skills-ref validate`).
- Combined `description` + `when_to_use` ≤ 1,536 chars (Claude Code listing
  truncation in v2.1.105+; targets older Claude Code use 250).
- Third person, imperative voice ("Use this skill for…", not "You can use…").
- Do NOT touch SKILL.md body — it loads after triggering and cannot influence
  trigger decisions. Trigger mode is frontmatter-only.

**Measure both caps before and after every mutation** —
`python3 ${CLAUDE_SKILL_DIR}/scripts/frontmatter-lengths.py <target>/SKILL.md`.
Stating the bound is not enforcing it: the overrun is silent. Claude Code
truncates the combined field at 1,536 and says nothing, so the phrases that
disappear are simply the last ones written, whether or not they were the
load-bearing ones — and the probe still runs, scoring a description the model
never saw in full.

**At the cap, an addition must be funded by a deletion.** When the combined
count is already at (or within ~50 chars of) 1,536, do NOT append: pick the
weakest existing phrase and swap it out, then re-probe. A mutation that assumes
headroom it does not have is not a mutation — it is a silent truncation with a
trigger score attached. Measured instance: this skill sat at exactly 1536/1536
on 2026-08-20 while its own backlog planned an addition on the belief that ~230
chars were free.

### Phase T5: Re-probe and decide

Re-run the probe with the new description (override via
`--description "<text>"` so the file isn't written until accepted).

**Noise floor first — a thresholded pass count at low N is not a measurement.**
With `--runs-per-query 3` a query can only score 0, 0.33, 0.67 or 1.0, so any
query whose true rate is near the 0.5 threshold is a coin flip, and train
moves ±1–2 queries on resampling alone. Before treating any train delta as
real:

- Use **`--runs-per-query 7`** for decisions. Reserve 3 for a first
  reconnaissance probe that tells you *where* the disputed queries are, never
  for keep/discard.
- Compare on **mean trigger rate across queries**, not the thresholded pass
  count. Thresholding discards most of what the probe paid for: a candidate can
  tie 4/7 on pass count while differing by 8 fires out of 49.
- Re-measure only the disputed queries at high N rather than the whole set.
  Queries sitting at 0.00 or 1.00 across every run so far are settled and need
  no further compute.
- A single query moving 1/7 → 6/7 (Fisher exact p≈0.03) is a result. A query
  moving 6/7 → 5/7 is not, no matter how canonical the query looks.

Observed 2026-07-24 on `autoresearch`: at N=3 the canonical "set up an
autoresearch loop" query read 0.67 → 0.00 and drove a whole iteration built on
a fabricated mechanism about proper-noun placement; at N=7 the same pair was
6/7 vs 5/7 — nothing. The same low-N artifact simultaneously *hid* a real
Mode-3 fix behind a tied pass count.

Decision rule on **train** scores:

- **Train improved by ≥1 query at N≥7** → KEEP. Write the new frontmatter to
  SKILL.md. New baseline.
- **Pass count tied but mean trigger rate up ≥0.10 with no should-NOT
  regression** → KEEP. The binary metric is the lossy one.
- **Train equal but description shorter/simpler** → KEEP (simplification ties
  per the Karpathy rule).
- **Train equal or worse** → DISCARD. Revert the proposal (file unchanged
  since override was used).
- **Train improved AND test got worse by 2+ queries** → DISCARD as overfit.
  The mutation taught Claude the train phrasings without generalising.
- **Train improved BUT description hit the 1024 hard cap** → DISCARD, plan
  T5 next iteration.

### Phase T6: Loop

Up to **5 iterations** (default; trigger probes are 5–10x more expensive
than rubric scoring because each probe shells out to a model). Stop when:

- Train pass-rate ≥ 95% AND test pass-rate ≥ 80% — converged.
- 3 consecutive discards across at least 2 mutation patterns — ceiling
  mapped. Surface what was tried.
- A T6 (cross-skill conflict) finding emerges — single-skill loop can't fix
  it; surface as backlog.
- User interrupts.

### Phase T7: Apply and persist

1. Pick the winner by **TEST** score (NOT train — overfit guard, same as
   Anthropic's loop).
2. Write the winning frontmatter to `<skill>/SKILL.md`. Do NOT edit body.
3. Update `<skill>/references/trigger-evals.json` — append a `last_run`
   metadata block with date, baseline score, final score, iteration count.
4. Update `<skill>/references/improvement-backlog.md`:
   - Move resolved trigger items to "Resolved this pass".
   - Add any T6 cross-skill conflicts as new "Open" items.
5. Print summary table:
   ```
   skill: <name>
   baseline: train X/N, test Y/M
   final:    train X'/N, test Y'/M
   delta:    +A train, +B test
   iterations: I (K kept, D discarded)
   eval set: <skill>/references/trigger-evals.json (saved for next run)
   ```

### Batch Mode

`/skill-improver batch trigger --all` (or `--group <glob>`) iterates skills
sequentially:

1. Scan via `scripts/scan-skills.sh`.
2. Probe baseline on each — rank by `(train_pass_rate * 0.6 + test_pass_rate
   * 0.4)` ascending (worst first).
3. Run trigger loop per skill, capped at 3 iterations in batch mode (probes
   are expensive).
4. Print ranked summary: skill, baseline, final, delta, iterations.

### Anti-Patterns

- Do NOT mutate the SKILL.md body — body cannot influence trigger.
- Do NOT pick the final by train score — always test, to guard overfit.
- Do NOT eval against only passing phrasings — include user-reported
  failures and adversarial negatives.
- Do NOT skip negatives — pure-recall tuning makes the skill grab everything.
- Do NOT run on plugin or managed skills (`~/.claude/plugins/`) — trigger
  mode mutates frontmatter; only personal/project skills are in scope.
- The probe self-isolates: each query installs its synthetic skill in its own
  fresh temp project (auto-removed), so it does NOT write into the cwd or the
  user's active project. Running it from any directory is safe.

## Why skills under-trigger

Anthropic's own guidance (in the official skill-creator): *"Claude has a tendency
to **undertrigger** skills — to not use them when they'd be useful."* Concrete
causes mapped from the official best-practices doc:

1. **Description tells what skill *does*, not when to *use* it.** "Processes Excel
   files" is a what; "Use when analyzing Excel files, spreadsheets, tabular data,
   or .xlsx files" is a when. Front-load the when.
2. **Wrong person.** "You can use this to..." gets ignored more than "Use this for..."
   The description is injected into a system prompt — second person is jarring.
3. **Buried trigger keywords.** Combined `description` + `when_to_use` truncates at
   1,536 chars in v2.1.105+ (250 chars on older Claude Code). Even within that cap,
   the dynamic budget can shrink further when many skills compete for context. Keywords
   in the first ~200 chars are the most robust.
4. **Vague intent.** "Helps with documents" matches everything and nothing — Claude
   can't disambiguate from the other 100+ skills competing for attention.
5. **Missing the user's actual phrasing.** The skill author writes in domain
   vocabulary; the user types in everyday vocabulary. Skill says "configure
   PostgreSQL"; user says "my db is slow". No overlap → no trigger.
6. **Easy queries that Claude can answer alone.** Anthropic notes skills only fire
   for tasks Claude *can't easily handle on its own*. A trivial one-step query like
   "read this PDF" may skip the skill even with a perfect description.
7. **Negative-boundary collision.** A *different* skill's description claims
   territory ("Use whenever the user mentions X") that overlaps with this skill,
   and Claude picks the wrong one.

The trigger-mode loop addresses 1–5 directly, surfaces 6 as unverifiable, and
flags 7 as a cross-skill conflict (manual fix).

## Eval-set construction

Build 12–15 queries, stratified roughly half should-trigger / half should-not.
Aim for ≥6 in each class so the train/test split has at least 3+3 in test.
Save to `<skill>/references/trigger-evals.json` for re-use across runs.

Schema:

```json
[
  {"query": "exact user-style phrasing", "should_trigger": true,
   "source": "user-reported|description-mined|sibling-skill|generic"},
  ...
]
```

The `source` field is metadata for the loop (helps weight failures); the probe
ignores it.

### Should-trigger queries (≈ 7 of 13)

| Source | How many | Where to mine |
|---|---|---|
| User-reported failures | 0–3 | If the user mentioned specific phrasings the skill missed in their `/skill-improver trigger` invocation, USE THOSE VERBATIM as gold should-triggers. |
| Description paraphrases | 2–3 | Pick 2–3 phrases from the existing `description` + `when_to_use`, paraphrase as a real user would. "Lint Python code" → "my python file has style errors" |
| Body-mined examples | 2–3 | Skim SKILL.md for example commands or section titles; convert each into a realistic user query. |
| Common everyday phrasings | 1–2 | "how do I X", "X is broken", "fix the X", "my X isn't working" — using the skill's domain vocabulary. |

### Should-NOT-trigger queries (≈ 6 of 13)

These are the ones that catch over-triggering. They share keywords with the
skill but need something else.

| Source | How many | Construction |
|---|---|---|
| Keyword-collision distractors | 2–3 | Use the skill's main keyword in a query that should go elsewhere. Skill is for "PDF form filling" → "what's the page count of this PDF?" (that's a read task, not a fill task). |
| Sibling-skill territory | 1–2 | If a related skill exists (e.g. `vllm-caching` vs `vllm-deployment`), write a query that belongs to the sibling. The probe sees only this skill's description, but the eval is "would this description over-claim the sibling's work?" |
| Generic conversation | 1–2 | "hi", "what does this code do?", "explain async/await" — should never invoke any specialised skill. |
| Adjacent-domain decoy | 1 | Same broad domain, different sub-area. Skill is for Helm charts → "deploy with kubectl apply". |

### Stratification check

Before saving, count: must have ≥3 in each class. If user-reported failures
are all should-trigger, deliberately add more should-not queries to keep the
split honest — otherwise the loop optimizes only for recall and over-triggers
become invisible.

## The probe mechanism

`scripts/probe-trigger.py` is the measurement tool. It is a stripped-down
adaptation of `anthropics/skills/skill-creator/scripts/run_eval.py`.

How it works (per query, repeated `runs_per_query` times):

1. Generate a unique synthetic skill name `<skill>-probe-<uuid>` and install it
   as a **skill** at `<tmp>/.claude/skills/<id>/SKILL.md` in a fresh, isolated
   per-query temp project (so concurrent workers never see each other's
   identically-described synthetics).
2. Shell out from that temp dir: `claude -p "<query>" --output-format
   stream-json --verbose --include-partial-messages --setting-sources project
   --disallowedTools Bash Edit Write NotebookEdit Task WebFetch WebSearch`. The
   `--setting-sources project` flag is load-bearing: without it, `claude` ALSO
   loads the user's `~/.claude/skills/` (often symlinks of the very skills under
   test), so the synthetic competes with its real twin + every sibling, the
   model invokes the real one, and the probe sees its synthetic id missing →
   false 0.0 on a skill that triggers perfectly. `--setting-sources project`
   loads ONLY the temp project's lone synthetic, which is the isolation the
   probe assumes. The probe only measures *whether*
   the model would invoke the Skill — the `--disallowedTools` deny-list makes the
   spawned agent hermetic so it can NEVER execute the task itself. Without it, a
   query like "deploy my app to openshift" makes the nested agent try to provision
   a real local environment (e.g. `crc`/libvirt → host sudo/pkexec password
   prompts) or run arbitrary Bash. Deny rules override any allow-list in the host
   settings; `Skill`/`Read` (what we detect) stay enabled.
3. Scan the whole turn for a `Skill`/`Read` `tool_use` referencing the synthetic
   id — do NOT bail on the first other tool (Claude often plans first) or stop at
   `message_stop` (a tool-using turn spans messages). Hit = triggered.
4. Remove the temp project dir.
5. `trigger_rate = triggers / runs`. Pass = `rate ≥ trigger_threshold` for
   should-trigger items, `rate < trigger_threshold` for should-not items.
   Threshold defaults to 0.5; runs default to 7.

Defaults:

| Knob | Default | When to change |
|---|---|---|
| `--runs-per-query` | 7 | 7 is the decision floor (§Pattern T4 noise rule). A lower N is acceptable only for a throwaway first sighting-pass, never for a keep/discard decision. |
| `--trigger-threshold` | 0.5 | Lower to 0.34 to count any single trigger (more lenient); raise to 0.67 to require strong consistency. |
| `--num-workers` | 6 | Lower if hitting rate limits; higher when rate-limit headroom allows. Each worker spawns a `claude -p` subprocess. |
| `--timeout` | 180 (s) | Sized for `claude -p` latency here (60–150s/call incl. cold start / Opus). It only caps a *hung* call — a fast call returns as soon as it emits its `result` event — so a high value has no downside. Timed-out runs are now tracked per query and surfaced as a `warn:` line, and an all-positives-0.0 result emits an explicit "probe isn't measuring" warning instead of looking like genuine under-triggering. Lower only if calls are reliably fast. |
| `--holdout` | 0.0 | Set 0.4 to enable train/test split. The loop sets this; standalone probes can leave at 0. |

### Calling the probe

Baseline + train/test split:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path /path/to/target-skill \
  --eval-set /path/to/target-skill/references/trigger-evals.json \
  --holdout 0.4 --runs-per-query 7 --num-workers 7 --verbose
```

Test a candidate description without writing it to SKILL.md yet:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path /path/to/target-skill \
  --eval-set /path/to/target-skill/references/trigger-evals.json \
  --description "Use this skill when..." \
  --holdout 0.4 --runs-per-query 7
```

Output is JSON with `train.summary` and `test.summary`, each carrying
`{total, passed, failed}` plus per-query `pass`/`trigger_rate`/`triggers`/`runs`.

### Which model to probe with (`--model`)

Trigger behavior is model-dependent, and the difference is large enough to
change conclusions — so choose deliberately:

- **Haiku is the cheap broad-screen model.** It is ~20–40× faster and ~5× cheaper
  than Opus, and Anthropic builds it for routing/classification — exactly a
  trigger decision. A skill that fires on Haiku will fire on the stronger models
  too, so **Haiku-CLEAN results are trustworthy** (use it to clear the bulk of a
  `--all` audit fast).
- **But Haiku OVER-reports under-triggering.** It tends to answer an actionable
  query directly instead of invoking the skill, so it produces false 0.0s even on
  near-verbatim description matches. Measured on this repo (2026-06): of 6 skills
  Haiku flagged as under-triggering, **5 fired 1.00 on Opus** (the 6th was correct
  deferral to a sibling). **Never change a description off a Haiku under-trigger
  flag alone — confirm the missed positives on the user's real model (Opus)
  first.** The workflow is: screen on Haiku → re-probe only the flagged misses on
  Opus → fix only what Opus also misses.
- **Probe with the model the user actually runs** when measuring "does it trigger
  for *them*". Default (no `--model`) inherits the session model.
- High variance on a borderline query (e.g. 0/3 then 3/3 across runs) is real —
  re-probe a lone Opus 0.00 before trusting it; one run that times out also reads
  as 0.0 (the `timeouts` field tells them apart).

### Cost & time budget

Each query × run = one `claude -p` invocation. On **Haiku** ~2–5s typical; on
**Opus** ~60–150s (set `--timeout` ≥ 180). Default 13-query × 7-run × 5-iteration
loop ≈ 455 invocations if every query re-probes every iteration — minutes on
Haiku, far longer on Opus; re-measuring only the disputed queries (§Phase T5)
is what keeps the real cost well below that ceiling. Keep total
concurrent `claude -p` modest (≈6 for Opus; Haiku tolerates more): the global
cap is `(parallel probes × --num-workers)`, and oversubscribing it triggers
rate-limit storms that read as mass timeouts/false-0.0. Trigger mode is
meaningfully more expensive than improve mode because it shells out to a model on
every probe.

### Fallback when `claude -p` is not available

If the `claude` CLI is missing or unauthenticated in the environment (rare in
Claude Code sessions, common on remote tools), the probe script will fail
fast. The loop should fall back to a *manual A/B*: print the candidate
description and the eval set, ask the user to test in a fresh session, and
record their reported outcomes by hand. This is degraded but honest — do
NOT use a subagent to "guess" trigger behavior; the agent will roleplay,
not measure.

## Mutation patterns by failure type

Once the probe returns, classify the train-failures and pick the matching
mutation. One change per iteration (keep the autoresearch attribution rule).

### Pattern T1: All failures are should-trigger misses (under-trigger)

**Symptom:** train passes negatives, fails 2+ positives. Skill is too quiet.

**Fix priority:**
1. **Add explicit trigger phrases for the missed phrasings.** Take the failed
   queries verbatim, extract their key noun + verb, add to `when_to_use` as
   `Triggers on "X", "Y", "Z"`. Generalise to the failure *class* while
   extracting: the phrase that covers "why does my python look wrong" is
   stronger eval-bait than the literal query, and the weakest phrasing that
   captures the class is what survives the held-out test split (the weakness
   criterion, SKILL.md Phase 2) — pasting whole queries verbatim overfits
   train and buys nothing on test.
2. **Be pushier.** Anthropic's own guidance: convert "How to do X" into "Use
   this skill whenever the user mentions X, Y, Z, or asks about W — even if
   they don't explicitly say 'X.'"
3. **Front-load.** If keywords appear after char ~400, move them to the start
   of the description.

**Before** (under-triggers on "my python file has style errors"):
```yaml
description: Lint and auto-format Python code with ruff, flake8, and black.
```

**After:**
```yaml
description: >-
  Lint, auto-format, and fix style errors in Python code (ruff, flake8, black).
when_to_use: >-
  Use whenever the user mentions "lint python", "fix style", "format code",
  "PEP 8", "ruff", "flake8", "black", "pre-commit for python", style errors
  in .py files, or asks why python code "looks wrong" / "won't pass linting".
```

### Pattern T2: All failures are should-not false-positives (over-trigger)

**Symptom:** train passes positives, fails 2+ negatives. Skill grabs everything
in its domain.

**Fix priority:**
1. **Add negative boundary** — explicit "Do NOT use for..." clause.
2. **Tighten scope** — replace broad words ("documents") with narrow ones
   ("Word .docx files specifically").
3. **Cite the right sibling skill** by name so Claude routes there instead.

**Before** (over-triggers on "what's the page count of this PDF?"):
```yaml
description: PDF processing — extract text, fill forms, merge documents. Use whenever the user mentions PDFs.
```

**After:**
```yaml
description: >-
  Fill PDF forms, merge or split PDF documents, redact sensitive content.
when_to_use: >-
  Use when the user wants to write or modify a PDF (fill a form, merge,
  split, redact, watermark, sign). Do NOT use for read-only PDF inspection
  (page count, metadata, text extraction) — Claude's built-in Read tool
  handles those without this skill.
```

**A negative boundary can raise the very rate it targets.** Measured on
`skill-improver`, 2026-08-20: three should-NOT queries about *creating* skills
fired at 1.00/1.00/0.71. Adding "Does NOT apply to writing a new skill from
scratch, scaffolding a SKILL.md for a workflow that has none, or packaging and
publishing plugins" moved the mean negative rate the wrong way, 0.452 → 0.476;
`write me a SKILL.md for my terraform workflow` went 0.71 → 0.86. The clause
introduced "new skill from scratch" and "SKILL.md" as *matching* text. Fix 2
(narrow the positive wording) and fix 3 (name the sibling) do not have this
failure mode; prefer them, and treat fix 1 as the one that must be re-probed
before it is believed.

**Over-trigger measured solo is not attributable.** The probe installs the
synthetic as the *only* skill in a fresh temp project, so there is no sibling
for the query to route to and the synthetic wins by default. A negative that
belongs to a sibling's territory therefore reads as a T2 failure of this
skill's description when it is really T6 in the other direction. Before
mutating on a failed negative, ask whether the correct handler exists in the
real environment; if it does, the finding is cross-skill and the fix is the
sibling's description, not this one. Only negatives that no installed skill
should handle — generic conversation, adjacent-domain decoys — are cleanly
this skill's problem.

### Pattern T3: Mixed failures (under and over together)

**Symptom:** failures on both should-trigger and should-not queries.

**Fix:** Don't try to fix both in one iteration — that's two changes.
Pick whichever class has more failures and apply T1 or T2. Next iteration
addresses the other.

If they're tied, fix under-trigger first (T1) — over-trigger is recoverable
("wrong skill fired" is annoying but visible), under-trigger is silent
("skill never fired, user gave up").

### Pattern T4: High-variance queries (the 1/3 or 2/3 trap)

**Symptom:** several queries trigger 1/3 or 2/3 times. Description is on
the borderline of triggering — small wording shifts could flip it either way.

**Fix:**
1. **Re-measure before mutating.** Fractional rates mean the measurement is
   underpowered, not that the description needs another edit — re-run the
   disputed queries at `--runs-per-query` 7 or higher (the decision floor;
   see the T4 row in Phase T3) and only treat a rate that survives as real.
2. **Then strengthen by adding redundancy.** If the confirmed variance is on
   a should-trigger query, add the missing keyword multiple times (in
   `description` AND in `when_to_use`). Anthropic's own skill-creator says
   Claude "has a tendency to 'undertrigger' skills" and tells authors to make
   descriptions "a little bit 'pushy'" to counter it (`skills/skill-creator/SKILL.md`,
   not the description optimizer — verified 2026-08-20).

### Pattern T5: Description hits the 1024-char hard cap

**Symptom:** mutations keep hitting the cap, the loop keeps shortening, signal
isn't improving. Frontmatter is over-stuffed.

**Fix:** Two mutations, try in order (one per iteration):

1. **Re-balance.** Move the *what* to `description`, the trigger phrases to
   `when_to_use`. The combined cap is 1,536 chars on v2.1.105+ but `description`
   alone is hard-capped at 1024 by the spec. `when_to_use` has no per-field cap
   — use it for the long trigger list.
2. **Collapse near-synonyms.** Trigger phrases that rename the same use case
   ("improve a skill", "make my skill better", "optimize a SKILL.md") are one
   trigger written three times; keep one phrase per genuinely distinct use
   case and spend the freed characters on uncovered cases. The re-probe
   decides: if the test rate holds, the synonyms were dead weight; if it
   drops, they were doing matching work — discard per the decision rules.
   (Tension with Pattern T4's "add redundancy" is real and intended: T4
   strengthens a borderline query, this trims a cap-bound description; both
   answer to the same eval.)

### Pattern T6: Cross-skill conflict (sibling steals triggers)

**Symptom:** a should-trigger query passes when probed solo, fails in real
sessions. Some other skill's description over-claims the territory.

**Fix:** This is NOT a single-skill mutation. Surface as a backlog finding:
identify the sibling skill stealing the trigger, recommend either tightening
the sibling's `description` or adding a "Do NOT use for X — use `<sibling>`
instead" line to one or both. Cross-skill negotiation requires the author.

The inverse case — a should-NOT query the probe shows firing at 1.00 because
the real handler was not installed in the temp project — is also T6, not T2.
See the attribution note under Pattern T2.

## Decision rules

The keep/discard decision tree lives in **Phase T5** above (§"Phase T5:
Re-probe and decide" — the authoritative copy, including the
mean-trigger-rate tie-break the noise floor requires). Final-description
selection is in **Phase T7**: best by **TEST** score, never train.

## Minimalism test (Boris alignment)

A skill that triggers reliably but produces little value per invocation
is shaped wrong. Boris Cherny: "underfund things at the start... if you
have a good idea, you just really want to get it out there." Same logic
applied to skills — over-tuned triggers on a thin skill outscore a
3-line CLAUDE.md rule pointing at a tool, but only on the rubric, not
in actual user value.

### Run after Phase T7

When trigger mode lands a stable description, before persisting, run:

```bash
# 1. Body content delivered per invocation (post-frontmatter)
body_lines=$(awk '/^---$/{f++; next} f==2' SKILL.md | wc -l)

# 2. Reference content the body actually invokes
ref_invocations=$(rg -cE 'references/[\w-]+\.md|scripts/[\w-]+\.(sh|py)' SKILL.md)
```

| Signal | Action |
|---|---|
| `body_lines < 40` AND `ref_invocations < 2` | **Collapse candidate** — flag for review. The skill could plausibly be a `.claude/rules/` entry or CLAUDE.md line pointing at the tool. Recommend running `instructions-triage` to confirm. |
| `body_lines < 40` AND `ref_invocations ≥ 2` | Skill is correctly minimal — pointer-shaped. Pass. |
| `body_lines ≥ 40` AND `ref_invocations < 2` | Skill is monolithic — flag for Dim 2 (Progressive Disclosure) work, separate from trigger tuning. |

### Why this matters at trigger-tune time, not score-time

The 10-dim rubric scores intrinsic skill quality. Trigger mode tunes the
*invocation gate*. A high-trigger-rate / low-value skill quietly inflates
its 10-dim score (Dim 5 Completeness sees coverage; Dim 7 Resource
Quality sees existence) while its real per-invocation impact is poor.
The minimalism test catches this — Boris's "is the model adding more
value than the scaffolding costs?" applied at trigger-tune time.

## Anti-patterns

- **Eval set built only from passing cases.** Testing only phrasings that
  already work measures nothing. Always include user-reported failures.
- **Eval set built only from the description.** Then the description trivially
  passes — the eval has measured the description against itself. At least 1/3 of should-trigger queries must
  be everyday phrasings the skill author *didn't* write down.
- **No should-not queries.** Without negatives, the loop optimizes pure recall
  → description becomes a 1024-char trigger-word soup → over-triggers everywhere
  → other skills suffer. Always include ≥3 negatives.
- **Mutating SKILL.md body to fix triggering.** The body is loaded *after*
  triggering. It can't influence whether the skill triggers. Only the
  frontmatter (`description`, `when_to_use`, `paths`) affects triggering.
- **Picking the final by train score.** Train score → overfit. Always pick by
  test.
- **Assuming an all-0.0 result means the skill under-triggers.** If *every*
  query (positives included) reads 0.0, the probe isn't measuring — check
  `claude -p` works and bump `--timeout` (a call killed before the model reaches
  the Skill reads as a miss). A real result discriminates: clear positives fire,
  clear negatives don't.
- **Running on managed/plugin skills.** Plugins (`~/.claude/plugins/`) and
  managed skills are owned by their authors. Don't mutate them — the
  skill-improver only operates on personal/project skills.

## Worked example

User: "/skill-improver trigger vllm-caching — it didn't fire when I asked
about prefix caching memory tuning"

### T0: setup
Snapshot `vllm-caching` to `/tmp/vllm-caching-trigger-baseline`. Read its
frontmatter: `description` mentions "tiered KV cache", "CPU offload", "LMCache",
"NixlConnector". `when_to_use` lists "vllm kv cache", "kv offload", "prefix cache".

### T1: build eval set
13 queries, saved to `references/trigger-evals.json`:

```json
[
  {"query": "how do I tune prefix cache memory in vllm", "should_trigger": true, "source": "user-reported"},
  {"query": "vllm kv cache offload to cpu", "should_trigger": true, "source": "description-mined"},
  {"query": "set up LMCache for my vllm cluster", "should_trigger": true, "source": "description-mined"},
  {"query": "disaggregated prefill with NixlConnector", "should_trigger": true, "source": "body-mined"},
  {"query": "my vllm is OOMing on long contexts what cache options", "should_trigger": true, "source": "everyday"},
  {"query": "should I enable prefix caching", "should_trigger": true, "source": "everyday"},
  {"query": "vllm tensor parallelism settings for h100", "should_trigger": false, "source": "sibling (vllm-deployment)"},
  {"query": "how does vllm chunked prefill work", "should_trigger": false, "source": "sibling (vllm-performance-tuning)"},
  {"query": "explain mistral attention", "should_trigger": false, "source": "decoy"},
  {"query": "what's the difference between awq and gptq", "should_trigger": false, "source": "sibling (vllm-quantization)"},
  {"query": "hello", "should_trigger": false, "source": "generic"},
  {"query": "vllm chat template debugging", "should_trigger": false, "source": "sibling (vllm-chat-templates)"},
  {"query": "fix my vllm CUDA OOM", "should_trigger": false, "source": "sibling (vllm-deployment)"}
]
```

### T2: baseline probe
`probe-trigger.py --holdout 0.4 --runs-per-query 7` → train 5/8, test 4/5.

Failures (train):
- "how do I tune prefix cache memory in vllm" — 1/3 trigger (under)
- "should I enable prefix caching" — 0/3 trigger (under)
- "fix my vllm CUDA OOM" — 3/3 trigger, expected false (over)

### T3: hypothesize
Mixed: 2 unders, 1 over. Pick T1 (under) first — more failures and silent.
Hypothesis: skill misses *user-vocabulary* phrasings of "memory tuning" and
"should I enable". Add explicit phrases.

### T4: mutate
Add to `when_to_use`: `..., "should I enable prefix caching", "tune cache
memory", "vllm OOM on long context", "kv cache memory budget"`.
Frontmatter combined char count: 712 (well under 1,536 cap).

### T5: re-probe
Train 7/8 (+2), test 4/5 (unchanged). KEEP — improvement on train, no
test regression.

### T3': next iteration
Remaining failure: "fix my vllm CUDA OOM" still over-triggers. Apply T2.
Add to `when_to_use`: `Do NOT use for general CUDA OOM debugging — use
vllm-deployment for pod sizing or vllm-performance-tuning for batch-size
tuning.`

### T5': re-probe
Train 8/8, test 5/5. STOP — perfect.

### T7: persist
Write final frontmatter to `vllm-caching/SKILL.md`. Update
`vllm-caching/references/trigger-evals.json` with timestamp. Print summary:
baseline 9/13 → final 13/13, +4 queries fixed in 2 iterations.
