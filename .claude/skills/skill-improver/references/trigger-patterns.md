# Trigger Patterns — Make Skills Actually Fire

Reference for the `trigger` mode of skill-improver: eval-set construction, the probe, mutation patterns for under-trigger and over-trigger, keep/discard rules for trigger-rate scoring. Method: 60/40 train/test, blinded test scores, <=1024-char description cap, 7 runs/query (see §"Phase T5"). Sources: `references/sources.md`.

## Table of Contents
- [Trigger Mode Workflow](#trigger-mode-workflow)
- [Why skills under-trigger](#why-skills-under-trigger)
- [Eval-set construction](#eval-set-construction)
- [The probe mechanism](#the-probe-mechanism)
- [Mutation patterns by failure type](#mutation-patterns-by-failure-type)
- [Minimalism test (Boris alignment)](#minimalism-test-boris-alignment)
- [Anti-patterns](#anti-patterns)

## Trigger Mode Workflow

Measure and tune a skill's frontmatter `description` (and `when_to_use`) so it fires when it should and stays silent when it shouldn't. Same keep/discard hill-climbing as `improve`; the metric is **trigger rate against an eval set**.

**Use when:** a user reports "the skill didn't fire when I asked X" / "Claude isn't using my skill", or a description is too vague, too narrow, keyword-colliding, or in the wrong vocabulary for how users phrase requests.

### Phase T0: Setup

1. Read the target skill (SKILL.md frontmatter, body, references/).
2. **Invocation gate — should this skill model-trigger at all?** A description is permanent context load on every turn. If the evidence says the user only fires the skill by hand (the request that started this run was "make `/name` work", the backlog and git history show only slash invocations, or the user confirms), apply `disable-model-invocation: true`, rewrite `description` as a human-facing one-liner (trigger phrases stripped), and stop. Proceed to T1 only when model-triggering is wanted.
3. Read `<skill>/references/improvement-backlog.md` if present — open "trigger" findings carry forward.
4. Review the mutation patterns below.
5. Snapshot the skill: `SNAP=$(mktemp -d -t <skill-name>-trigger-baseline.XXXX) && cp -a <skill-dir>/. "$SNAP"`.
6. Initialize a results log: `iter | train | test | desc-chars | status | change`.

### Phase T1: Build (or load) the eval set

If `<skill>/references/trigger-evals.json` exists, use it as the starting set and append each `--missed "<phrase>"` flag as a new should-trigger entry. Otherwise construct one per §"Eval-set construction".

Each entry carries a `bucket` (they fail differently; an aggregate rate hides which broke):

| bucket | what it is | target share |
|---|---|---|
| `explicit` | names the skill, its command, or a distinctive token | 20% |
| `implicit` | describes the task in the user's own words, never naming it | 30% |
| `contextual` | arrives inside a real scenario — a file, an error, mid-task | 20% |
| `negative` | should NOT fire | 30% |

- 6–8 should-trigger queries across `explicit` / `implicit` / `contextual`: user-reported failures verbatim first; fill with description paraphrases, body-mined examples, everyday user vocabulary.
- 5–7 `negative` queries: keyword-collision distractors, sibling-skill territory, generic conversation, adjacent-domain decoys.

`contextual` is the bucket that goes missing: a description tuned on explicit/implicit phrasings passes by keyword match and still misses requests that arrive mid-task. Fill it deliberately.

`scripts/bucket-evals.py` labels an existing corpus (negatives definitional, positives classified by the configured chat model) and prints the fleet balance; `scripts/probe-trigger.py` reports `summary.by_bucket` so a run says which bucket failed.

Save to `<skill>/references/trigger-evals.json`; it persists across runs.

### Phase T2: Probe baseline

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path <skill-dir> \
  --eval-set <skill-dir>/references/trigger-evals.json \
  --holdout 0.4 --runs-per-query 7 --num-workers 7 --verbose
```

The probe installs the candidate description as a real **skill** in a fresh isolated temp project (`<tmp>/.claude/skills/<id>/SKILL.md` — Claude auto-invokes skills, NOT `.claude/commands/` entries), runs `claude -p "<query>"` with `--output-format stream-json --verbose --include-partial-messages`, and scans the whole turn for a `Skill`/`Read` `tool_use` referencing the synthetic id. Each query runs N times; rate >= threshold = triggered.

Read `train.summary` and `test.summary` (pass/fail counts); per-query `trigger_rate` diagnoses the failure type.

If the `claude` CLI is missing or unauthenticated the probe fails fast. Fall back to manual A/B (§"Fallback when `claude -p` is not available"). Do NOT use a subagent to "guess" trigger behavior; it roleplays, not measures.

### Phase T3: Hypothesize

Categorise train failures and pick ONE mutation type:

| Failure profile | Pattern |
|---|---|
| All failures are should-trigger misses (under-trigger) | T1 — add explicit phrases, be pushier, front-load |
| All failures are should-NOT false-positives (over-trigger) | T2 — add negative boundary, tighten scope |
| Mixed under + over | T3 — fix whichever class has more failures first |
| Fractional trigger rates dominate (not 0.00/1.00) | T4 — the measurement is underpowered before it is a mutation problem: re-measure the disputed queries at N=7+ (§T5 noise floor) before proposing any edit |
| Cap-bound: description hits 1024 chars | T5 — re-balance into description vs when_to_use |
| Sibling skill steals the trigger | T6 — backlog finding, NOT single-skill mutation |

### Phase T4: Mutate

Apply ONE change to the frontmatter (description and/or when_to_use). Constraints:

- `description` <= 1024 chars (spec hard cap; `skills-ref validate` rejects more).
- Combined `description` + `when_to_use` <= 1,536 chars (Claude Code listing truncation in v2.1.105+; older Claude Code uses 250).
- Third person, imperative voice ("Use this skill for…", not "You can use…").
- Do NOT touch the SKILL.md body — it loads after triggering. Trigger mode is frontmatter-only.

**Measure both caps before and after every mutation:** `python3 ${CLAUDE_SKILL_DIR}/scripts/frontmatter-lengths.py <target>/SKILL.md`. Overrun is silent: Claude Code truncates the combined field at 1,536, dropping the last-written phrases, and the probe still scores a description the model never saw in full.

**At the cap, fund an addition with a deletion.** When the combined count is at or within ~50 chars of 1,536, do NOT append: swap out the weakest existing phrase, then re-probe.

### Phase T5: Re-probe and decide

Re-run the probe with the new description via `--description "<text>"` (the file is not written until accepted).

**Noise floor first.** At `--runs-per-query 3` a query scores only 0, 0.33, 0.67 or 1.0, so a query near the 0.5 threshold is a coin flip and train moves ±1–2 queries on resampling alone. Before treating any train delta as real:

- Use **`--runs-per-query 7`** for decisions. Use 3 only for a first reconnaissance probe locating the disputed queries, never for keep/discard.
- Compare on **mean trigger rate across queries**, not the thresholded pass count.
- Re-measure only the disputed queries at high N. Queries at 0.00 or 1.00 across every run so far are settled.
- A single query moving 1/7 → 6/7 is a result. 6/7 → 5/7 is not, however canonical the query looks.

Decision rule on **train** scores:

- **Train improved by ≥1 query at N≥7** → KEEP. Write the new frontmatter to SKILL.md. New baseline.
- **Pass count tied but mean trigger rate up ≥0.10 with no should-NOT regression** → KEEP.
- **Train equal but description shorter/simpler** → KEEP.
- **Train equal or worse** → DISCARD. Revert the proposal (file unchanged since override was used).
- **Train improved AND test got worse by 2+ queries** → DISCARD as overfit.
- **Train improved BUT description hit the 1024 hard cap** → DISCARD, plan T5 next iteration.

### Phase T6: Loop

Up to **5 iterations** (default; probes cost 5–10x rubric scoring). Stop when:

- Train pass-rate ≥ 95% AND test pass-rate ≥ 80% — converged.
- 3 consecutive discards across at least 2 mutation patterns — ceiling mapped. Surface what was tried.
- A T6 (cross-skill conflict) finding emerges — surface as backlog.
- User interrupts.

### Phase T7: Apply and persist

1. Pick the winner by **TEST** score, NOT train (overfit guard).
2. Write the winning frontmatter to `<skill>/SKILL.md`. Do NOT edit the body.
3. Save queries added this run to `<skill>/references/trigger-evals.json`. Keep it a bare list of query objects — `probe-trigger.py` treats every element as a query, so a metadata block breaks the next run. Date, baseline, final, and iteration count go in the backlog entry.
4. Update `<skill>/references/improvement-backlog.md`: move resolved trigger items to "Resolved this pass"; add T6 cross-skill conflicts as new "Open" items.
5. Print:
   ```
   skill: <name>
   baseline: train X/N, test Y/M
   final:    train X'/N, test Y'/M
   delta:    +A train, +B test
   iterations: I (K kept, D discarded)
   eval set: <skill>/references/trigger-evals.json (saved for next run)
   ```

### Batch Mode

`/skill-improver batch trigger --all` (or `--group <glob>`) iterates skills sequentially:

1. Scan via `scripts/scan-skills.sh`.
2. Probe baseline on each — rank by `(train_pass_rate * 0.6 + test_pass_rate * 0.4)` ascending (worst first).
3. Run the trigger loop per skill, capped at 3 iterations.
4. Print ranked summary: skill, baseline, final, delta, iterations.

### Anti-Patterns

- Do NOT compare an incomplete probe run. `probe-trigger.py` exits 1 and sets `summary.complete: false` when any query produced no measured run (`"trigger_rate": null`). Re-run; do not rank, keep or discard on a partial set. An unmeasured query is not a low score: should-trigger queries deflate while should-NOT queries inflate, producing a plausible number from nothing.
- Do NOT mutate the SKILL.md body.
- Do NOT pick the final by train score — always test.
- Do NOT eval against only passing phrasings — include user-reported failures and adversarial negatives.
- Do NOT skip negatives — pure-recall tuning makes the skill grab everything.
- Do NOT run on plugin or managed skills (`~/.claude/plugins/`) — only personal/project skills are in scope.
- The probe self-isolates (fresh temp project per query, auto-removed); running it from any directory is safe.

## Why skills under-trigger

Claude undertriggers skills. Causes:

1. **Description tells what, not when.** "Processes Excel files" → "Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files". Front-load the when.
2. **Wrong person.** "You can use this to..." is ignored more than "Use this for...".
3. **Buried trigger keywords.** Combined `description` + `when_to_use` truncates at 1,536 chars (v2.1.105+; 250 on older), and the dynamic budget can shrink further when many skills compete. Keywords in the first ~200 chars are most robust.
4. **Vague intent.** "Helps with documents" matches nothing in particular.
5. **Missing the user's phrasing.** Skill says "configure PostgreSQL"; user says "my db is slow". No overlap → no trigger.
6. **Easy queries Claude answers alone.** Skills fire only for tasks Claude can't easily handle itself; a trivial query may skip the skill even with a perfect description.
7. **Negative-boundary collision.** Another skill's description claims overlapping territory ("Use whenever the user mentions X").

The loop addresses 1–5, surfaces 6 as unverifiable, flags 7 as a cross-skill conflict (manual fix).

## Eval-set construction

Build 12–15 queries, roughly half should-trigger / half should-not, ≥6 per class (≥3+3 in test). Save to `<skill>/references/trigger-evals.json`.

```json
[
  {"query": "exact user-style phrasing", "should_trigger": true,
   "source": "user-reported|description-mined|sibling-skill|generic"},
  ...
]
```

`source` is loop metadata; the probe ignores it.

### Should-trigger queries (≈ 7 of 13)

| Source | How many | Where to mine |
|---|---|---|
| User-reported failures | 0–3 | Phrasings the user said the skill missed in their `/skill-improver trigger` invocation — USE VERBATIM. |
| Description paraphrases | 2–3 | Phrases from `description` + `when_to_use`, paraphrased as a real user would: "Lint Python code" → "my python file has style errors". |
| Body-mined examples | 2–3 | Example commands or section titles in SKILL.md, converted to realistic user queries. |
| Common everyday phrasings | 1–2 | "how do I X", "X is broken", "fix the X", "my X isn't working" with the skill's domain vocabulary. |

### Should-NOT-trigger queries (≈ 6 of 13)

They share keywords with the skill but need something else.

| Source | How many | Construction |
|---|---|---|
| Keyword-collision distractors | 2–3 | Main keyword in a query that belongs elsewhere. "PDF form filling" skill → "what's the page count of this PDF?". |
| Sibling-skill territory | 1–2 | A query belonging to a related skill (e.g. `vllm-caching` vs `vllm-deployment`); tests whether this description over-claims. |
| Generic conversation | 1–2 | "hi", "what does this code do?", "explain async/await". |
| Adjacent-domain decoy | 1 | Same domain, different sub-area. Helm charts skill → "deploy with kubectl apply". |

### Stratification check

Before saving, each class must have ≥3. If user-reported failures are all should-trigger, add should-not queries to compensate. At least 1/3 of should-trigger queries must be everyday phrasings the skill author didn't write down (an eval built only from the description measures the description against itself).

## The probe mechanism

`scripts/probe-trigger.py` measures trigger rate. Per query, repeated `runs_per_query` times:

1. Generate a unique synthetic skill name `<skill>-probe-<uuid>` and install it as a **skill** at `<tmp>/.claude/skills/<id>/SKILL.md` in a fresh per-query temp project.
2. Shell out from that dir: `claude -p "<query>" --output-format stream-json --verbose --include-partial-messages --setting-sources project --disallowedTools Bash Edit Write NotebookEdit Task WebFetch WebSearch`.
   - `--setting-sources project` is load-bearing: without it `claude` also loads `~/.claude/skills/`, the synthetic competes with its real twin, and the probe reports a false 0.0.
   - `--disallowedTools` keeps the spawned agent hermetic so it never executes the task; `Skill`/`Read` (what is detected) stay enabled.
3. Scan the whole turn for a `Skill`/`Read` `tool_use` referencing the synthetic id — do NOT bail on the first other tool or stop at `message_stop`. Hit = triggered.
4. The temp project lives under `mktemp -d`; leave it.
5. `trigger_rate = triggers / runs`. Pass = `rate ≥ trigger_threshold` for should-trigger, `rate < trigger_threshold` for should-not.

| Knob | Default | When to change |
|---|---|---|
| `--runs-per-query` | 7 | 7 is the decision floor (§Pattern T4 noise rule). Lower only for a throwaway first sighting-pass. |
| `--trigger-threshold` | 0.5 | 0.34 counts any single trigger (lenient); 0.67 requires strong consistency. |
| `--num-workers` | 6 | Lower on rate limits; each worker spawns a `claude -p` subprocess. |
| `--timeout` | 180 (s) | Only caps a hung call; a high value has no downside. Timed-out runs surface as a `warn:` line; an all-positives-0.0 result emits a "probe isn't measuring" warning. Lower only if calls are reliably fast. |
| `--holdout` | 0.0 | Set 0.4 for train/test split. |
| `--model` | `claude-sonnet-5` | Pinned, not inherited (§Which model to probe with). Override only to answer "does it fire on the model *I* run", never mid-sweep. |

### Calling the probe

Baseline + train/test split:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path /path/to/target-skill \
  --eval-set /path/to/target-skill/references/trigger-evals.json \
  --holdout 0.4 --runs-per-query 7 --num-workers 7 --verbose
```

Candidate description without writing it to SKILL.md:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/probe-trigger.py \
  --skill-path /path/to/target-skill \
  --eval-set /path/to/target-skill/references/trigger-evals.json \
  --description "Use this skill when..." \
  --holdout 0.4 --runs-per-query 7
```

Output is JSON: `train.summary` and `test.summary` each carry `{total, passed, failed}` plus per-query `pass`/`trigger_rate`/`triggers`/`runs`.

### Which model to probe with (`--model`)

- **Haiku is the cheap broad-screen model.** A skill that fires on Haiku fires on stronger models, so **Haiku-CLEAN results are trustworthy** (use it to clear the bulk of an `--all` audit).
- **Haiku OVER-reports under-triggering** (answers actionable queries directly, giving false 0.0s). **Never change a description off a Haiku under-trigger flag alone.** Workflow: screen on Haiku → re-probe only the flagged misses on Opus → fix only what Opus also misses.
- **Default is `claude-sonnet-5`, pinned.** An inherited model makes a run unreproducible. Sonnet-vs-Opus agreement was measured only at n=3; treat as provisional.
- **Pass `--model` explicitly** when the question is "does it fire on the model *I* run".
- **Never vary model, `--effort`, or `--settings` inside one sweep** (each is a cache-prefix identity). Batch all calls of one identity together.
- High variance on a borderline query is real — re-probe a lone Opus 0.00 before trusting it; a timed-out run also reads 0.0 (the `timeouts` field tells them apart).

### Cost & time budget

- **Read `summary.usage`, don't estimate.** Each run reports `requests`, `calls`, four token counts, `est_cost_usd`, `est_cost_per_call_usd`, `model_reported`. `run-cost.py` cannot see a probe sweep (killed runs write no transcript); this block is the only record.
- **`model_reported` gates comparability.** A mismatch, or more than one value, prints a `warn:`; the arm must not be ranked against another.
- **Size corpora for power, not budget.** 40 queries × 7 runs ≈ 280 calls ≈ $8 — affordable.
- **n=3 cannot support a keep/discard decision.** "Identical at n=3" is not evidence of equivalence (0.71 and 1.00 both land on 1.00 on that grid).
- **Keep a sweep under an hour** — the prompt cache expires at 60 min; split long sweeps.
- **Do not set `MAX_THINKING_TOKENS=0`** — at n=7 both firing queries fell 1.00 → 0.71 (margin vanishes while still passing 0.5).
- Opus calls take ~60–150s (set `--timeout` ≥ 180); Haiku ~2–5s. Re-measure only disputed queries (§Phase T5). Keep concurrent `claude -p` modest (≈6 for Opus): the global cap is `(parallel probes × --num-workers)`; oversubscribing causes rate-limit storms that read as mass timeouts/false-0.0.

### Fallback when `claude -p` is not available

If the `claude` CLI is missing or unauthenticated, fall back to a *manual A/B*: print the candidate description and eval set, ask the user to test in a fresh session, record their outcomes by hand. Do NOT use a subagent to guess trigger behavior; it roleplays, not measures.

## Mutation patterns by failure type

Classify train failures and pick the matching mutation. One change per iteration.

### Pattern T1: All failures are should-trigger misses (under-trigger)

**Symptom:** train passes negatives, fails 2+ positives.

**Fix priority:**
1. **Add explicit trigger phrases for the missed phrasings.** Extract key noun + verb from failed queries, add to `when_to_use` as `Triggers on "X", "Y", "Z"`. Generalise to the failure *class*: the weakest phrasing that captures the class survives the held-out test split (the weakness criterion, SKILL.md Phase 2); pasting whole queries verbatim overfits train.
2. **Be pushier.** Convert "How to do X" into "Use this skill whenever the user mentions X, Y, Z, or asks about W — even if they don't explicitly say 'X.'"
3. **Front-load.** If keywords appear after char ~400, move them to the start of the description.

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

**Symptom:** train passes positives, fails 2+ negatives.

**Fix priority:**
1. **Add negative boundary** — explicit "Do NOT use for..." clause.
2. **Tighten scope** — replace broad words ("documents") with narrow ones ("Word .docx files specifically").
3. **Cite the right sibling skill** by name.

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

**A negative boundary can raise the rate it targets:** the clause's wording ("new skill from scratch", "SKILL.md") becomes *matching* text. Prefer fix 2 and fix 3; re-probe fix 1 before believing it.

**Over-trigger measured solo is not attributable.** The probe installs the synthetic as the only skill, so a negative belonging to a sibling's territory reads as a T2 failure when it is really T6. Before mutating on a failed negative, ask whether the correct handler exists in the real environment; if so, the finding is cross-skill and the fix is the sibling's description. Only negatives no installed skill should handle (generic conversation, adjacent-domain decoys) are this skill's problem.

### Pattern T3: Mixed failures (under and over together)

Do not fix both in one iteration. Apply T1 or T2 for whichever class has more failures; the next iteration addresses the other. If tied, fix under-trigger first (T1) — under-trigger is silent, over-trigger is visible.

### Pattern T4: High-variance queries (the 1/3 or 2/3 trap)

**Symptom:** several queries trigger 1/3 or 2/3 times; the description is borderline.

**Fix:**
1. **Re-measure before mutating.** Re-run the disputed queries at `--runs-per-query` 7 or higher (see the T4 row in Phase T3); treat only a rate that survives as real.
2. **Then add redundancy.** If confirmed variance is on a should-trigger query, add the missing keyword multiple times (in `description` AND `when_to_use`) — make descriptions "a little bit 'pushy'".

### Pattern T5: Description hits the 1024-char hard cap

**Symptom:** mutations keep hitting the cap; the frontmatter is over-stuffed.

**Fix:** two mutations, in order, one per iteration:

1. **Re-balance.** Move the *what* to `description`, trigger phrases to `when_to_use` (no per-field cap; combined cap 1,536 on v2.1.105+; `description` alone is capped at 1024).
2. **Collapse near-synonyms.** Phrases renaming the same use case ("improve a skill", "make my skill better", "optimize a SKILL.md") are one trigger written three times; keep one per distinct use case and spend the freed characters on uncovered cases. The re-probe decides: test rate holds → dead weight; drops → discard per the decision rules.

### Pattern T6: Cross-skill conflict (sibling steals triggers)

**Symptom:** a should-trigger query passes solo, fails in real sessions; another skill's description over-claims the territory.

**Fix:** NOT a single-skill mutation. Surface as a backlog finding: name the sibling, recommend tightening its `description` or adding "Do NOT use for X — use `<sibling>` instead" to one or both. Cross-skill negotiation requires the author.

The inverse — a should-NOT query firing at 1.00 because the real handler was not installed in the temp project — is also T6, not T2.

Keep/discard decisions: §"Phase T5". Final-description selection: §"Phase T7" (TEST score, never train).

## Minimalism test (Boris alignment)

A skill that triggers reliably but delivers little per invocation is shaped wrong. Run after Phase T7, before persisting:

```bash
# 1. Body content delivered per invocation (post-frontmatter)
body_lines=$(awk '/^---$/{f++; next} f==2' SKILL.md | wc -l)

# 2. Reference content the body actually invokes
ref_invocations=$(rg -cE 'references/[\w-]+\.md|scripts/[\w-]+\.(sh|py)' SKILL.md)
```

| Signal | Action |
|---|---|
| `body_lines < 40` AND `ref_invocations < 2` | **Collapse candidate** — flag for review. Could be a `.claude/rules/` entry or CLAUDE.md line pointing at the tool. Confirm by checking whether the body does anything a one-line pointer would not. |
| `body_lines < 40` AND `ref_invocations ≥ 2` | Correctly minimal — pointer-shaped. Pass. |
| `body_lines ≥ 40` AND `ref_invocations < 2` | Monolithic — flag for Dim 2 (Progressive Disclosure) work, separate from trigger tuning. |

## Anti-patterns

- **Eval set built only from passing cases or only from the description.** Include user-reported failures; ≥1/3 of should-trigger queries must be everyday phrasings.
- **No should-not queries.** Always include ≥3 negatives; pure recall tuning yields a 1024-char trigger-word soup that over-triggers.
- **Mutating the SKILL.md body to fix triggering.** Only frontmatter (`description`, `when_to_use`, `paths`) affects triggering.
- **Picking the final by train score.** Pick by test.
- **Reading an all-0.0 result as under-triggering.** If *every* query (positives included) reads 0.0, the probe isn't measuring — check `claude -p` works and bump `--timeout`. A real result discriminates: clear positives fire, clear negatives don't.
- **Running on managed/plugin skills** (`~/.claude/plugins/`).
