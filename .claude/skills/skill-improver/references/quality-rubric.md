# Skill Quality Rubric — Detailed Scoring Guide

This rubric defines how to score a Claude Code skill on 10 dimensions (0–10 each, 100 total). Use it consistently across all evaluations to ensure comparability.

## Table of Contents
- [Scoring Philosophy](#scoring-philosophy)
- [Dim 1 — Trigger Precision](#dimension-1-trigger-precision-010)
- [Dim 2 — Progressive Disclosure](#dimension-2-progressive-disclosure-010)
- [Dim 3 — Writing Style](#dimension-3-writing-style-010)
- [Dim 4 — Actionability](#dimension-4-actionability-010)
- [Dim 5 — Completeness](#dimension-5-completeness-010)
- [Dim 6 — Simplicity](#dimension-6-simplicity-010)
- [Dim 7 — Resource Quality](#dimension-7-resource-quality-010)
- [Dim 8 — Internal Consistency](#dimension-8-internal-consistency-010)
- [Dim 9 — Domain Accuracy](#dimension-9-domain-accuracy-010)
- [Dim 10 — Differentiation](#dimension-10-differentiation-010)
- [Scoring Template](#scoring-template)
- [Results Log Format](#results-log-format)

## Scoring Philosophy

Score honestly. Most decent skills land at 50–70. A score of 80+ is excellent. 90+ is rare and means the skill is nearly flawless across all dimensions. Do not grade inflate — a 7 is genuinely good.

When scoring, consider:
- **Evidence over impression.** Point to specific lines/sections.
- **Penalize proportionally.** A minor flaw in an otherwise strong dimension costs 1 point, not 3.
- **Context matters.** A minimal skill for a narrow task can score 10 on simplicity where a complex skill cannot.

---

## Dimension 1: Trigger Precision (0–10)

**What:** How well the frontmatter `description` field ensures the skill activates when needed and stays silent when not.

| Score | Criteria |
|---|---|
| 0–2 | Missing description, or so vague it would match nearly anything or nothing |
| 3–4 | Has a description but uses wrong person, lacks specific trigger phrases |
| 5–6 | Third-person, some trigger phrases, but misses important use cases or is overly broad |
| 7–8 | Third-person, specific trigger phrases covering core use cases, few gaps |
| 9–10 | Comprehensive trigger phrases, correct person, covers edge triggers, no false positives likely |

**Platform constraint:** Claude Code truncates combined `description` + `when_to_use` at **1,536 characters** in the skill listing (250 for Claude Code < v2.1.105). The Agent Skills spec hard-caps `description` at 1024 chars. Many installed skills shrink it further (budget: 1% of context window, 8,000-char fallback; override `SLASH_COMMAND_TOOL_CHAR_BUDGET`). Key trigger phrases MUST appear within the first 1,536 chars.

**Common failures:**
- Second person ("You can use this when...") instead of "This skill should be used when..." (imperative "Use this skill when..." is acceptable; see trigger-patterns.md)
- Vague: "Provides guidance for X" with no trigger phrases
- Over-broad: triggers on common words (false positives)
- Under-specified: misses the common ways users phrase the request
- Key triggers buried past character 1,536
- `description` stuffed with trigger phrases that belong in `when_to_use` (separate field, concatenated in the listing)

**Check method:** Mentally test 5 realistic user prompts (would it trigger?), then 3 unrelated prompts (would it falsely trigger?). Verify the first 1,536 chars of combined `description` + `when_to_use` hold the most important trigger keywords. Use `head -c 1536`.

**Invocation-fit check (run before scoring the wording):** Every installed skill's description loads into context on every turn. First ask whether the skill should model-trigger at all. A skill the user only fires by hand (`/name` — task skills, personal pipelines, anything whose backlog or git history shows exclusively slash invocations) should carry `disable-model-invocation: true`: its description leaves the always-loaded listing and the trigger wording becomes moot. When that fits, recommend it as the single highest-impact Dim 1 improvement and score Dim 1 on the human-facing one-liner instead of trigger coverage. Applies at creation time too.

---

## Dimension 2: Progressive Disclosure (0–10)

**What:** Whether the skill manages context window budget well through layered loading.

| Score | Criteria |
|---|---|
| 0–2 | Everything in SKILL.md with no structure, or SKILL.md is empty |
| 3–4 | All content in SKILL.md (>500 lines), no references/ or examples/ |
| 5–6 | SKILL.md is moderate (300–500 lines), some content in references/ but unevenly split |
| 7–8 | SKILL.md is lean (150–300 lines), detailed content in references/, clear pointers |
| 9–10 | SKILL.md is focused (<150 lines), excellent separation, every resource explicitly referenced with clear guidance on when to load |

The 500-line figure is a recommendation (agentskills.io, Anthropic best-practices), not validated by `skills-ref validate`. Loading levels: metadata (~100 tokens at startup) → SKILL.md body (when triggered) → bundled files (on demand).

**Reference depth rule:** Keep file references **one level deep** from SKILL.md (Claude may only partially read files referenced from other references). Reference files over 100 lines need a table of contents at the top.

**Common failures:**
- Entire API reference dumped into SKILL.md body
- References exist but SKILL.md never mentions them
- References too granular (10 tiny files) or too monolithic (one 10k-word file)
- Nested reference chains (SKILL.md → A.md → B.md)

---

## Dimension 3: Writing Style (0–10)

**What:** Adherence to imperative/infinitive form, no second-person, objective instructional tone.

| Score | Criteria |
|---|---|
| 0–2 | Entirely conversational, second-person throughout |
| 3–4 | Mixed — some imperative, frequent "you should" or "you can" |
| 5–6 | Mostly imperative, occasional second-person slips |
| 7–8 | Consistently imperative, rare or no second-person |
| 9–10 | Flawless imperative form throughout, reads like a technical manual |

**Check method:** Search for "you ", "you'll", "you're", "your " in the SKILL.md body. Each occurrence costs points.

**The target voice:**
- YES: "Configure the server. Validate input. Start by reading the file."
- NO: "You should configure the server. You need to validate input."

---

## Dimension 4: Actionability (0–10)

**What:** Whether instructions are concrete enough that Claude can execute them without ambiguity.

| Score | Criteria |
|---|---|
| 0–2 | Abstract descriptions with no concrete steps |
| 3–4 | Some steps but vague ("set up the environment appropriately") |
| 5–6 | Steps are present but some lack specificity (missing commands, file paths, parameter values) |
| 7–8 | Clear step-by-step with specific commands, paths, and expected outcomes |
| 9–10 | Every instruction is unambiguous, includes validation steps, handles decision points, and ends on completion criteria that are both checkable AND exhaustive |

**Completion-criterion demand:** a done-condition needs *clarity* (agent can tell done from not-done) and *demand* (how much the bound requires). "Produce a change list" is checkable but undemanding and invites premature completion; "every modified flag accounted for" forces the agent to keep going. The 9–10 band requires exhaustive bounds ("every X handled", "all Y verified") wherever the work has an enumerable scope.

**Common failures:**
- "Configure the settings as needed" — which settings? What values?
- Steps assume knowledge the skill should provide
- Missing validation — no way to confirm a step succeeded
- Completion criteria that check existence, not coverage ("write the report" vs "every finding from the scan appears in the report")

---

## Dimension 5: Completeness (0–10)

**What:** Whether the skill covers the full scope its description promises.

| Score | Criteria |
|---|---|
| 0–2 | Covers less than half of what the description promises |
| 3–4 | Covers basics but significant gaps in common use cases |
| 5–6 | Core use cases covered, some secondary cases missing |
| 7–8 | Core and secondary cases covered, edge cases acknowledged |
| 9–10 | Comprehensive coverage including edge cases, error handling, and troubleshooting |

**Check method:** List 5 scenarios from the trigger description. Is each one addressed?

---

## Dimension 6: Simplicity (0–10)

**What:** Whether the skill achieves its goals with minimal complexity. Deleting text for equal results is a win.

| Score | Criteria |
|---|---|
| 0–2 | Massively over-engineered, unnecessary abstraction layers, confusing structure |
| 3–4 | Noticeable bloat — sections that repeat, unnecessary complexity |
| 5–6 | Reasonable but could be trimmed — some redundancy or over-explanation |
| 7–8 | Lean and focused, no obvious waste |
| 9–10 | Maximally concise — every sentence earns its place, nothing to remove |

**The test:** Read each paragraph and ask "would the skill be worse without this?" If no, it should go.

**Common failures:**
- Saying the same thing three different ways
- Examples that add nothing beyond the instructions
- Defensive caveats and disclaimers Claude doesn't need
- Metadata/boilerplate that serves no function

---

## Dimension 7: Resource Quality (0–10)

**What:** Quality of bundled scripts, examples, and reference files.

| Score | Criteria |
|---|---|
| 0–2 | Resources are broken, incomplete, or missing despite being referenced |
| 3–4 | Resources exist but are stubs, untested, or poorly documented |
| 5–6 | Resources work but lack polish — incomplete examples, no error handling |
| 7–8 | Resources are solid, working, well-documented |
| 9–10 | Resources are exemplary — complete examples, robust scripts, comprehensive references |
| N/A | Skill has no bundled resources and doesn't need them → score 7 (neutral) |

**Check method:** Could Claude actually execute the scripts? Are examples copy-paste ready?

---

## Dimension 8: Internal Consistency (0–10)

**What:** Whether the skill is internally coherent — no contradictions, dangling references, or naming mismatches.

| Score | Criteria |
|---|---|
| 0–2 | Major contradictions, referenced files don't exist, fundamentally incoherent |
| 3–4 | Some broken references or contradictory instructions |
| 5–6 | Mostly consistent but some naming mismatches or outdated references |
| 7–8 | Consistent throughout, all references valid |
| 9–10 | Perfectly coherent — naming, terminology, file references, and instructions all align |

**Check method:**
- Every file mentioned in SKILL.md exists
- Terminology is consistent ("config" vs "settings")
- Instructions don't contradict each other
- File references from SKILL.md are one level deep (no A→B→C chains)
- All frontmatter fields are valid per the Agent Skills spec
- Each concept's material is co-located: definition, rules, and caveats under one heading. Scattering (one meaning fragmented across many places, so an agent reading one fragment acts on a partial picture — e.g. a flag defined in §Flags, version-gated in §Compatibility, warned-about in §Troubleshooting) is distinct from duplication (one meaning repeated).

---

## Dimension 9: Domain Accuracy (0–10)

**What:** Whether the technical content is correct and current.

| Score | Criteria |
|---|---|
| 0–2 | Major technical errors, deprecated APIs, incorrect instructions |
| 3–4 | Several inaccuracies or outdated information |
| 5–6 | Mostly accurate, minor errors or slightly outdated details |
| 7–8 | Accurate and current, reflects real APIs/tools/workflows |
| 9–10 | Authoritative — could serve as reference documentation |

**Check method:** Verify key claims against actual tool behavior, API docs, or current best practices. **Verification means online probes, local execution, or `sources.md` stamps — never the scorer's training-data memory.** Factual claims (versions, dates, model names, flags) often postdate the model's cutoff; a claim covered by a recent `Last verified:` stamp outranks the prior. Never score a claim down, and never recommend reverting it to an older value, from memory alone; flag it for an online probe (freshen mode). A version that "looks too new" is usually correct.

Also check frontmatter fields: a skill scoped to specific file types should use `paths:`; a task skill with side effects should use `disable-model-invocation: true`; scripts referencing the skill directory should use `${CLAUDE_SKILL_DIR}`. See `references/anthropic-skill-design.md` for the frontmatter reference.

**Hard-fail validation (spec violations cap Dim 9 at 3):**

Verify the skill would pass `skills-ref validate`. Any failure below is a spec violation.

**The frontmatter block must first PARSE as YAML.** Check this before scoring any field. A block that does not parse makes Claude Code load the skill with **every field dropped** (`name` falls back to the directory name, `description` to the first line of the body, `allowed-tools`, `model`, `disable-model-invocation` stop applying) with no warning, and the file still *reads* correctly. Regex extraction cannot see this (`rg '^description:'` matches a broken block as well as a valid one). Run the script, which parse-gates first, rather than grepping. Usual cause: an unquoted value containing `': '`; fix: a block scalar (`description: >-` with the value indented beneath).

`name:` must:
- Be 1–64 characters, only `[a-z0-9-]`
- NOT start or end with a hyphen
- NOT contain consecutive hyphens (`--`)
- NOT contain XML tags
- NOT equal reserved words `anthropic` or `claude`
- Match the parent directory name

`description:` must:
- Be non-empty
- Be ≤ 1024 characters
- NOT contain XML tags

Quick check — `frontmatter-lengths.py` covers the parse gate and both length caps, and exits non-zero on a violation:

```bash
python3 <skill-improver>/scripts/frontmatter-lengths.py <skill>/SKILL.md
```

Name-rule check (regex is adequate here ONLY because the parse gate has already passed):

```bash
# Extract name
name=$(rg '^name:\s*(.+)$' SKILL.md -o -r '$1' | tr -d '"' | tr -d "'" | xargs)
# Verify: length ≤64, only [a-z0-9-], no leading/trailing -, no --,
# not "anthropic" or "claude", matches dirname
[[ ${#name} -le 64 ]] && [[ "$name" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] \
  && [[ "$name" != *--* ]] && [[ "$name" != "anthropic" ]] \
  && [[ "$name" != "claude" ]] && [[ "$name" == "$(basename "$(dirname "$PWD/SKILL.md")")" ]] \
  && echo OK || echo FAIL
```

Any hard fail → cap Dim 9 at 3 and surface the specific violation in the justification. `freshen` mode will not fix these — the author must rename or edit the frontmatter.

**Staleness cap (sources.md dates):**

When `references/sources.md` exists, cap Dim 9 on the date it was last verified. Read that date in this order:

1. **`Freshened: YYYY-MM-DD` header stamp** — the current contract (`freshen-patterns.md` §1.1b). One stamp asserts every row was verified on that date, except rows with an inline exception note. Age it as a per-row date.
2. **Per-row `Last verified:` dates** — legacy. Use the **oldest**.

| Age of that date | Max Dim 9 |
|------------------|-----------|
| ≤ 90 days | no cap |
| 91–180 days | 7 |
| > 180 days | 5 |
| Neither a header stamp nor `Last verified:` markers | 6 |
| `references/sources.md` absent | 6 |

**A header stamp with no per-row column is on the current contract, not unmarked.** Do not read it as "no markers" (that caps a freshly freshened skill at 6). `staleness-report.py` resolves the stamp first and prints `full` in its `rows` column for these files.

Tolerance (legacy files only): if ≥ 80% of rows have `Last verified:` dates, use the oldest dated row; if < 80% have dates, treat the file as lacking markers. Rows marked `<!-- ignore-freshen -->` (historical/pinned sources the author keeps as-is) are excluded from the cap computation entirely.

Quick check:

```bash
# current contract first — the header stamp; only fall back to legacy per-row dates
rg -m1 '^\*{0,2}Freshened:?\*{0,2}\s*(\d{4}-\d{2}-\d{2})' -o -r '$1' references/sources.md \
  || rg -v 'ignore-freshen' references/sources.md \
     | rg '^\|.*\| (\d{4}-\d{2}-\d{2}) \|' -o -r '$1' | sort | head -1
```

Running only the second command on a header-stamped file prints nothing, which reads as "no markers" and wrongly fires the 6-cap.

When the cap triggers, record a justification like "Dim 9 capped at 7 — oldest sources.md date is 2025-12-02 (139 days old)" and recommend `freshen <skill>` as the improvement path; score-loop mutations cannot resolve staleness without online probes.

---

## Dimension 10: Differentiation (0–10)

**What:** Whether the skill provides genuine value beyond Claude's base knowledge.

| Score | Criteria |
|---|---|
| 0–2 | Skill restates what Claude already knows — no procedural or domain value |
| 3–4 | Mostly general knowledge with a few specific details |
| 5–6 | Contains useful specifics (company conventions, project-specific patterns, tool configs) |
| 7–8 | Strong procedural value — workflows, scripts, and patterns Claude couldn't derive |
| 9–10 | Essential — contains proprietary knowledge, tested workflows, or non-obvious patterns that fundamentally change Claude's capability in this domain |

**The test:** If this skill were deleted, would Claude produce noticeably worse results for the use cases it covers?

---

## Boris Alignment Check (cross-cutting caps)

Diagnostic patterns from Boris Cherny, confirmed first-party by Thariq Shihipar, *"The new rules of context engineering for Claude 5 generation models"* (2026-07-24), which names all three patterns below as superseded practice. **Cite the blog, never the podcast** (podcast origin unverified; no rule may be justified by it alone).

Cost of *not* lifting these caps (from *Optimizing for cost and intelligence*, Anthropic; applies to skills too):

- Prompts written for an older model cost **36% more per ticket** on the newer one with no accuracy change; auditing them made it **14% cheaper and more accurate**.
- Over-obeyed instructions cost money ("verify twice", "be maximally thorough"); broken or conflicting scaffolding (retired thinking setting, contradictory rules, hand-rolled scratchpad) costs accuracy.
- "Verify twice" is Dim 6 scaffolding; a prompt carrying an older model's workarounds is the compensation cap below.

These do NOT add an 11th dimension — they cap existing dims when triggered, like the Dim 9 staleness cap. Skills that fight the model's grain or compensate for current-model limits decay across releases.

| Pattern | Detection | Cap |
|---|---|---|
| **Up-front context dumps** — skill front-loads domain context the model could fetch via Read/Grep/WebFetch | Sections >30 lines describing facts (not procedures) without pointing at a tool/file. Boris: "give it a tool so it can get the context it needs." | **Dim 4 (Actionability) capped at 7** |
| **Model-version compensation** — skill contains language like "Claude tends to X, always remind it Y" or version-specific workarounds for behaviour that may be fixed in newer releases | Compensation-language probe below finds 3+ matches. | **Dim 9 (Domain Accuracy) capped at 7** |
| **Goal + tool pointer** (pro-pattern, no cap) | Skill body is short imperative goal + reference to a tool/file/script. Reward signal — flag in justification, no scoring impact beyond the dim its presence helps. | (none) |

Compensation-language probe (kept outside the table — a `\|` pasted from a table cell is a valid regex that matches nothing):

```bash
rg -in 'claude (tends to|sometimes|often)|always remind|model (frequently|tends)|compensate for' SKILL.md references/
```

Also run the `prompt-audit` subcommand of the bundled `claude-api` skill (Claude Code v2.1.221+); it audits prompts and tool descriptions for patterns written for older models and supplies hypotheses for this cap.

### Procedural steps — advisory signal, NO cap

**There is no step-count cap. Do not re-introduce a count-based cap without a source that states one.** No source gives a numeric step threshold; Anthropic guidance recommends explicit sequential steps when operations are fragile, consistency matters, or order is load-bearing; SkillLens found surface format non-predictive.

Judge procedure by fit, not count. A long sequence is correct where the operation is fragile, consistency matters, or order is load-bearing; it is waste where the model would reach the same steps unaided. Record that judgement in the Dim 6 justification, never as an automatic cap.

`scripts/scaffold-probe.py` classifies items (scaffold / criterion / branch) to *find* candidate bloat. Read its list, then decide; it sets no score. Criteria and branches encode judgment the model cannot infer; never penalise a skill for writing them down.

When a Boris cap triggers, record the justification like:
> "Dim 4 capped at 7 — §Background front-loads 60 lines of protocol facts
> (lines 45-105) with no pointer to a tool or file that would fetch them.
> Boris alignment failure: up-front context dump."

### Induced cost — what the skill costs to OBEY

The caps above measure the skill's **text**. A 90-line skill can still be expensive to run. `scripts/induced-cost-probe.py [SKILL.md] [--refs]` reports four **structural** triggers (never judge whether prose "feels wasteful"):

| Trigger | Detection | Why it costs |
|---|---|---|
| `effort-pin` | frontmatter `effort:` at high/xhigh/max on a skill with 2+ modes | Overrides the session on *every* invocation, including the cheap modes the skill itself defines. |
| `eager-read` | "read all/every/each reference" with no conditional scoping it | Pays for the whole reference set on a run that needed one file. Point-of-use phrasing ("read each reference at its question") is the fix, and the probe stays quiet on it. |
| `uncapped-fanout` | a spawn imperative with no agent-count cap **anywhere in the skill** | An unbounded fan-out is unbounded spend. The cap is looked for skill-wide, so stating it once in SKILL.md covers the reference files carrying the spawn tails. |
| `over-obedience` | "verify twice", "be maximally thorough", "investigate fully even when it looks simple" | Removing "verify twice" cut cost per ticket by a third with no accuracy change. |

**Cap: Dim 6 (Simplicity) capped at 6** when any trigger fires. A triggered skill may still be right: record the dismissal reason rather than silently ignoring it.

**The cap is two-sided.** A skill trimmed until vague makes the agent flail, which costs more than the lines saved. **Dim 5 (Completeness) is the brake**: an induced-cost hit never justifies a cut that drops scope the description promises. Fix the trigger (scope the read, state the cap, delete the over-obedience clause), not the length. The probe has no "too short" trigger by design. Run `--selftest` after any change to the probe's patterns.

---

Prefer hypotheses that lift Boris caps over those that lift uncapped dims of the same magnitude: capped dims are *structural* problems, uncapped ones usually *cosmetic*.

---

## SkillLens Utility Check (cross-cutting, evidence-based)

An LLM judge scoring skill *text* picks the higher-utility skill only 46.4% of the time (random); **the skill that reads better is often the one that performs worse**. Clarity, conciseness, structure, formatting, tone and format (list vs prose vs checklist) carry no predictive signal. Only three text properties predict downstream utility:

1. **Failure Mechanism Encoding** — names concrete failure mechanisms with executable remedies, not generic advice.
2. **Actionable Specificity** — commands, values, decision points (≈ Dim 4).
3. **High-Risk Action Blacklist** — names what NOT to do and when.

| Pattern | Detection | Effect |
|---|---|---|
| **Generic-advice body** — guidance is mostly "do X well" platitudes with no mechanism/remedy pairs | Read the skill's core teaching sections: can each major claim be traced to a concrete failure mode, command, threshold, or counter-example? | **Dim 10 capped at 6** |
| **No high-risk blacklist where risk exists** — skill covers an operation with known destructive/irreversible failure modes but never says what NOT to do | Check whether "do NOT", "never", or an anti-patterns section exists for the risky operations in scope | **Dim 5 capped at 8** |
| **Mechanism + remedy density** (pro-pattern) | Failure modes named with executable fixes throughout | Reward signal — note in justification |

Do not reward fluency: a skill scoring high on Dims 3/6/8 with a generic-advice body is the inversion case these caps catch. Never justify a score delta on format alone.

---

## Negative-Transfer Gate (Dim 10 cap, evidence-based)

Skills help in only 75% of extractor-target pairs; 25% are net-harmful. Dim 10's test ("if deleted, would Claude produce noticeably worse results?") is this measurement, so Dim 10 is capped by what has been measured, not intuition.

Every row is against a **noise floor of `1/n_cases`** (the delta from one eval case flipping). Take the floor and verdict from `scripts/eval-evidence.py`; do not eyeball the sign.

| Evidence | Max Dim 10 |
|---|---|
| `delta_pass_rate ≤ −2 × floor` — skill loses to no-skill | **2**, and surface it as the headline finding |
| inside the band (`−2 × floor` … `+floor`) **and** `delta_tokens > 0` — unresolved, and it costs | **3**, and surface it: it costs and has not been shown to pay |
| inside the band, `delta_tokens ≤ 0` — unresolved, but free | **8** — unresolved is not "neutral"; the unmeasured cap stands |
| `delta_pass_rate ≥ +floor` | no cap — score on the evidence |
| Never measured | **8** — "essential" (9–10) is a claim about outcomes, not text |

The band is asymmetric because calling a skill harmful is the expensive error; clearing the cap takes `+floor`, the harmful verdict takes twice that.

**"Inside the band" means the corpus cannot answer the question**, not "roughly neutral". At the fleet median of 3 cases the floor is 0.33. Fix: more cases (`scripts/grow-evals.py`, floor of 8), never a more generous reading.

**Several measurements: the worst governs.** Per-model and per-case-subset runs are not replicates; do not average them.

**How to measure it.** Do NOT build a harness — the official `skill-creator` plugin runs each eval case with and without the skill:

```bash
# after skill-creator has produced with_skill/ and without_skill/ runs
cd ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator
python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
# -> benchmark.json carries delta_pass_rate, delta_time, delta_tokens
```

Requires the target to have `evals/evals.json`. A skill with no eval set cannot clear the unmeasured cap: log an Open backlog item with action "build an eval set, then measure delta_pass_rate".

**An errored case is not a failed case.** Before reading any delta, check every case in `benchmark.json` ran. A crashed, timed-out or ungraded case measured nothing: counting it as a failure manufactures a negative delta; dropping it changes the denominator between arms. Re-run errored cases. If they cannot be made to run, the delta is **unmeasured** and the 8 cap applies.

**A negative delta is not automatically a delete.** Check the analyst pass (a skill can lose on `pass_rate` while winning on tokens or time; a flaky eval can invert a small delta) and confirm the sign is stable across runs. Do not round a negative delta up to "roughly neutral".

### The cost side of the same benchmark

`benchmark.json` carries `delta_tokens` next to `delta_pass_rate`. A skill that changes no outcome while adding context is a **pure tax** (the 3 row above).

`≈ 0` means **inside run-to-run variance**: compare the delta against the per-config `pass_rate.stddev` in `benchmark.json`; a delta smaller than the baseline's spread is noise.

Check before using the number:

- **Sign convention.** The delta is `configs[0] - configs[1]` over config directories in **alphabetical** order. `with_skill` sorts before `without_skill`, so positive means *the skill costs more*. Confirm the two directory names before reading a sign.
- **It may not be tokens.** `tokens` comes from `timing.json` only when `grading.json` carries no timing; otherwise it falls back to `execution_metrics.output_chars`. Both configs are measured the same way, so the sign is sound; the magnitude is not tokens unless the source is confirmed.
- **The deltas are strings** (`"+0.12"`, `"+1840"`). Parse them.

A **positive** `delta_pass_rate` with a large positive `delta_tokens` is not a cap: report the cost alongside the win. Only the `≈ 0` case converts cost into a ceiling.

**No cost dimension, ever.** No 11th dimension scoring cheapness (the scalar sum would trade quality for cost at an arbitrary rate; an empty skill scores 10). Cost enters as caps and gates only.

### Floor evidence moves the unmeasured cap

Floor mode (`scripts/knowledge-floor.py`) asks a bare model (no skills, no tools) what it already knows about the skill's subject and buckets each claim KNOWS / UNKNOWN / CONFLICTS. When floor data exists for the skill, it replaces the flat `8`:

| Floor evidence (strongest probed tier) | Max Dim 10 |
|---|---|
| Any **durable** CONFLICT (see below) | **9** — the skill overrides a confident wrong prior |
| Floor ~0% — no claim is known on any probed tier | **9** — every claim is real transfer |
| Mixed (some KNOWS, no durable conflict) | 8 — unchanged |
| Floor ≥80% KNOWS **and** zero CONFLICTS | **5** — the model already carries it; report as a deletion candidate |

- **`delta_pass_rate` still wins.** Floor only moves the *unmeasured* cap; a measured delta of any sign overrides every row.
- **A partial floor run moves nothing.** Read `scored` / `unmeasured` before the share: a claim whose probe failed or came back `UNGRADED` was not measured. Compute the share over graded claims only. `NO SCORE` (nothing graded) leaves the flat `8`. Failure must never score better than success.
- **10 is unreachable from floor alone.** Only a positive measured delta clears 9.
- **Durable conflict beats high floor** when both apply (profile 3 below).
- **No floor data → the flat `8` stands.** Do not infer a floor from reading the text.

**Durable means it survives on a peer tier, not a weaker one.** Check durability against a frontier-class sibling; a downgrade tier cannot falsify a conflict (it returns UNKNOWN where it has no confident prior).

### Three profiles — a floor number alone mis-ranks one of them

| Floor | Conflicts | Profile | What to do |
|---|---|---|---|
| high | none | **deletion candidate** | confirm with an eval delta, then cut to the delta |
| low | any | **pure transfer** | nothing to trim; the skill is the only source |
| high | durable | **correction skill** | make it **louder**, not leaner |

Leanness cannot be scored from the floor percentage: a correction skill (model mostly knows the subject, gets a few things confidently wrong) needs its corrections front-loaded and stated as a contradiction of the common belief, not buried among the parts the model already had right.

## Scoring Template

Use this format when reporting scores:

```
## Skill Evaluation: [skill-name]
Path: [path/to/SKILL.md]

| # | Dimension | Score | Justification |
|---|---|---|---|
| 1 | Trigger Precision | X/10 | [one sentence] |
| 2 | Progressive Disclosure | X/10 | [one sentence] |
| 3 | Writing Style | X/10 | [one sentence] |
| 4 | Actionability | X/10 | [one sentence] |
| 5 | Completeness | X/10 | [one sentence] |
| 6 | Simplicity | X/10 | [one sentence] |
| 7 | Resource Quality | X/10 | [one sentence] |
| 8 | Internal Consistency | X/10 | [one sentence] |
| 9 | Domain Accuracy | X/10 | [one sentence] |
| 10 | Differentiation | X/10 | [one sentence] |
| **Total** | | **XX/100** | |

Lowest dimension: [name] ([score])
Recommended first improvement: [one sentence]
```

---

## Results Log Format

Track the improvement loop with this TSV-style log:

```
iteration | score | delta | status | description
0         | 58    | —     | baseline | initial evaluation
1         | 62    | +4    | keep     | rewrote description with specific trigger phrases
2         | 62    | 0     | discard  | added examples/ directory (no score gain, added complexity)
3         | 65    | +3    | keep     | moved API reference from SKILL.md to references/api.md
4         | 67    | +2    | keep     | converted 12 second-person sentences to imperative form
```
