# Trigger Patterns — Make Skills Actually Fire

Reference for the `trigger` mode of skill-improver. Covers eval-set
construction, the probe mechanism, mutation patterns for fixing under-trigger
and over-trigger, and the keep/discard rules specific to trigger-rate scoring.

Methodology mirrors Anthropic's official `skill-creator` description-optimization
loop (60/40 train/test, 3 runs/query, blinded test scores, ≤1024-char hard cap)
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
3 runs/query, blinded test scores, ≤1024-char hard cap).

**Use trigger mode when:** a user reports "the skill didn't fire when I asked
X", "Claude isn't using my skill", or you suspect a description is too vague,
too narrow, too keyword-collision-y, or simply written in the wrong vocabulary
for how users actually phrase requests. Score-mode bumps Dim 1 (Trigger
Precision) on subjective rubric judgment; trigger-mode measures it empirically.

The eval-set construction rules, mutation patterns, decision tree, and worked
example are the sections that follow in this file.

### Phase T0: Setup

1. Read the target skill (SKILL.md frontmatter, body, references/).
2. Read `<skill>/references/improvement-backlog.md` if present — open
   "trigger" findings carry forward.
3. Review the mutation patterns and decision rules in the sections below.
4. Snapshot the skill: `cp -a <skill-dir> /tmp/<skill-name>-trigger-baseline`.
5. Initialize a results log: `iter | train | test | desc-chars | status | change`.

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
  --holdout 0.4 --runs-per-query 3 --num-workers 6 --verbose
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
| 1/3 or 2/3 trigger rates dominate | T4 — strengthen redundancy, bump runs-per-query to 5 |
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

### Phase T5: Re-probe and decide

Re-run the probe with the new description (override via
`--description "<text>"` so the file isn't written until accepted).

Decision rule on **train** scores:

- **Train improved by ≥1 query** → KEEP. Write the new frontmatter to
  SKILL.md. New baseline.
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
   identically-described synthetics, and real project skills don't compete).
2. Shell out from that temp dir: `claude -p "<query>" --output-format
   stream-json --verbose --include-partial-messages`.
3. Scan the whole turn for a `Skill`/`Read` `tool_use` referencing the synthetic
   id — do NOT bail on the first other tool (Claude often plans first) or stop at
   `message_stop` (a tool-using turn spans messages). Hit = triggered.
4. Remove the temp project dir.
5. `trigger_rate = triggers / runs`. Pass = `rate ≥ trigger_threshold` for
   should-trigger items, `rate < trigger_threshold` for should-not items.
   Threshold defaults to 0.5; runs default to 3.

Defaults:

| Knob | Default | When to change |
|---|---|---|
| `--runs-per-query` | 3 | Bump to 5 if variance is killing signal (1/3 vs 2/3 keep flipping). |
| `--trigger-threshold` | 0.5 | Lower to 0.34 if you want any trigger to count (more lenient); raise to 0.67 if you want strong consistency. |
| `--num-workers` | 6 | Lower if hitting rate limits; higher if you have headroom. Each worker spawns a `claude -p` subprocess. |
| `--timeout` | 30 (s) | **Bump to 120+ when `claude -p` is slow** (cold start / Opus / heavy tasks can take 60–150s before the model reaches a tool). A timeout that fires before the Skill is invoked reads as a miss — the classic cause of an all-0.0 result. |
| `--holdout` | 0.0 | Set 0.4 to enable train/test split. The loop sets this; standalone probes can leave at 0. |

### Calling the probe

Baseline + train/test split:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path /path/to/target-skill \
  --eval-set /path/to/target-skill/references/trigger-evals.json \
  --holdout 0.4 --runs-per-query 3 --num-workers 6 --verbose
```

Test a candidate description without writing it to SKILL.md yet:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path /path/to/target-skill \
  --eval-set /path/to/target-skill/references/trigger-evals.json \
  --description "Use this skill when..." \
  --holdout 0.4 --runs-per-query 3
```

Output is JSON with `train.summary` and `test.summary`, each carrying
`{total, passed, failed}` plus per-query `pass`/`trigger_rate`/`triggers`/`runs`.

### Cost & time budget

Each query × run = one `claude -p` invocation, ~4–10s typical.
Default 13-query × 3-run × 5-iteration loop ≈ 195 invocations.
With 6 workers and 7s avg, that's ~4 minutes wall-clock per skill. Budget
accordingly — trigger mode is meaningfully more expensive than improve mode
because it actually shells out to a model on every probe.

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
   `Triggers on "X", "Y", "Z"`.
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
1. **Strengthen by adding redundancy.** If the variance is on a should-trigger
   query, add the missing keyword multiple times (in `description` AND in
   `when_to_use`). Anthropic's improver explicitly recommends "be a little
   bit pushy" for borderline cases.
2. **Bump `--runs-per-query` to 5** for the next iteration to get tighter
   estimates before deciding.

### Pattern T5: Description hits the 1024-char hard cap

**Symptom:** mutations keep hitting the cap, the loop keeps shortening, signal
isn't improving. Frontmatter is over-stuffed.

**Fix:** Re-balance. Move the *what* to `description`, the trigger phrases to
`when_to_use`. The combined cap is 1,536 chars on v2.1.105+ but `description`
alone is hard-capped at 1024 by the spec. `when_to_use` has no per-field cap
— use it for the long trigger list.

### Pattern T6: Cross-skill conflict (sibling steals triggers)

**Symptom:** a should-trigger query passes when probed solo, fails in real
sessions. Some other skill's description over-claims the territory.

**Fix:** This is NOT a single-skill mutation. Surface as a backlog finding:
identify the sibling skill stealing the trigger, recommend either tightening
the sibling's `description` or adding a "Do NOT use for X — use `<sibling>`
instead" line to one or both. Cross-skill negotiation requires the author.

## Decision rules

After Phase T5 (re-score), apply this decision tree on the **train** scores:

1. **Train improved by ≥1 query** → KEEP. New baseline.
2. **Train equal but description is shorter or simpler** → KEEP (simplification
   wins ties — same Karpathy rule as the score loop).
3. **Train equal or worse** → DISCARD. Revert the frontmatter via `git
   checkout` or undo edit.
4. **Train improved AND test got worse by 2+ queries** → DISCARD as overfit.
   The mutation taught Claude the train phrasings without generalizing.
5. **Train improved BUT description hit the 1024-char hard cap** → DISCARD,
   apply T5 next iteration.

When picking the **final** description at end of loop: best by **TEST** score,
not train. (Anthropic's loop does the same thing for the same reason.)

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

- **Eval set built only from passing cases.** If you only test phrasings that
  already work, you measure nothing. Always include user-reported failures.
- **Eval set built only from the description.** Then the description trivially
  passes — you've measured itself. At least 1/3 of should-trigger queries must
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
`probe-trigger.py --holdout 0.4 --runs-per-query 3` → train 5/8, test 4/5.

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
