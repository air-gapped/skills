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

**Platform constraint:** Claude Code truncates combined `description` + `when_to_use` at **1,536 characters** in the skill listing (raised from 250 in v2.1.105, 2026-04-13). The Agent Skills spec hard-caps `description` at 1024 chars. Descriptions shorten further when many skills are installed, via a dynamic budget (1% of context window, 8,000-char fallback; override with `SLASH_COMMAND_TOOL_CHAR_BUDGET`). Key trigger phrases MUST appear within the first 1,536 chars. For skills targeting older Claude Code (< v2.1.105), treat 250 as the cap.

**Common failures:**
- Second person: "You can use this when..." instead of "This skill should be used
  when..." (imperative "Use this skill when..." is acceptable — it is the form
  Anthropic's own skill-creator description optimizer emits; see trigger-patterns.md)
- Vague: "Provides guidance for X" with no trigger phrases
- Over-broad: Triggers on common words that would cause false positives
- Under-specified: Misses the most common ways users phrase the request
- Key triggers buried past character 1,536 (lost to truncation)
- `description` stuffed with trigger phrases that belong in `when_to_use` (separate field, concatenated in the listing)

**Check method:** Mentally test 5 realistic user prompts. Would this description trigger? Then test 3 unrelated prompts. Would it falsely trigger? Also verify the first 1,536 chars of combined `description` + `when_to_use` contain the most important trigger keywords. Use `head -c 1536` to check.

**Invocation-fit check (run before scoring the wording):** A description is
permanent context load — every installed skill's description sits in the
context on every turn, fired or not. So the first question is not "is the
description good?" but "should this skill model-trigger at all?" A skill the
user only ever fires by hand (`/name` — task skills, personal pipelines,
anything whose backlog or git history shows exclusively slash invocations)
should carry `disable-model-invocation: true`: its description leaves the
always-loaded listing entirely, and the trigger wording becomes moot. When
that fits, recommend it as the single highest-impact Dim 1 improvement and
score Dim 1 on the human-facing one-liner instead of trigger coverage. This
check applies at creation time too, not only when retrofitting — the cheapest
description is the one that never loads.

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

**Stated as an imperative, not enforced:** "Keep your main `SKILL.md` under 500
lines" — agentskills.io/specification, echoed by Anthropic's best-practices page
("under 500 lines for optimal performance") and the Claude Code skills docs. No
validator checks it: `skills-ref validate` covers frontmatter only. The same page
hedges the companion figure — "Instructions (< 5000 tokens *recommended*)". The 3-level loading system: metadata (~100 tokens at startup) →
SKILL.md body (when triggered) → bundled files (on demand).

**Reference depth rule:** Keep file references **one level deep** from SKILL.md.
Claude may partially read files referenced from other referenced files (using
`head -100` previews). For reference files over 100 lines, include a table of
contents at the top.

**Common failures:**
- Entire API reference dumped into SKILL.md body
- References exist but SKILL.md never mentions them
- References are too granular (10 tiny files) or too monolithic (one 10k-word file)
- Nested reference chains (SKILL.md → A.md → B.md) where Claude only partially reads B.md

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

**Completion-criterion demand:** a step's done-condition has two properties —
*clarity* (can the agent tell done from not-done?) and *demand* (how much the
bound requires). "Produce a change list" is checkable but undemanding; "every
modified flag accounted for" forces the agent to keep digging until the bound
is met. Undemanding criteria invite premature completion — the agent ends the
step as soon as any output exists. The 9–10 band requires exhaustive bounds
("every X handled", "all Y verified") wherever the work has an enumerable scope.

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

**What:** Whether the skill achieves its goals with minimal complexity. Inspired by autoresearch: deleting code for equal results is a win.

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
- Examples that don't add value beyond what the instructions already convey
- Defensive caveats and disclaimers that Claude doesn't need
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
- Terminology is consistent (don't call it "config" in one place and "settings" in another)
- Instructions don't contradict each other
- File references from SKILL.md are one level deep (no A→B→C chains)
- All frontmatter fields are valid per the Agent Skills spec
- Each concept's material is co-located: definition, rules, and caveats under
  one heading. Scattering is distinct from duplication — duplication repeats
  one meaning in two places; scattering fragments one meaning across many, so
  an agent reading one fragment acts on a partial picture (e.g. a flag defined
  in §Flags, version-gated in §Compatibility, and warned-about in
  §Troubleshooting — an agent landing on §Flags recommends it blind)

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

**Check method:** Verify key claims against actual tool behavior, API docs, or current
best practices. **Verification means online probes, local execution, or `sources.md`
stamps — never the scorer's training-data memory.** Skills here are freshened
continuously, so factual claims (versions, dates, model names, flags) often postdate
the model's knowledge cutoff; a claim covered by a recent `Last verified:` stamp
outranks the prior. Never score a claim down — and never recommend reverting it to
an older value — from memory alone; flag it for an online probe (freshen mode)
instead. A version that "looks too new" is usually correct; the urge to lower it is
the canonical training-data-staleness failure.
Also check: does the skill use appropriate frontmatter fields? A skill
scoped to specific file types should use `paths:`. A task skill with side effects
should use `disable-model-invocation: true`. Scripts referencing the skill directory
should use `${CLAUDE_SKILL_DIR}`. See `references/anthropic-skill-design.md` for the
complete frontmatter reference.

**Hard-fail validation (spec violations cap Dim 9 at 3):**

Verify the skill would pass `skills-ref validate`. Any of these failures is a
spec violation that makes the skill non-conformant — `skills-ref` would reject it.

**The frontmatter block must first PARSE as YAML.** Check this before scoring
any field, because a block that does not parse makes every other check
meaningless: Claude Code loads the skill with **every field dropped** — `name`
falls back to the directory name, `description` to the first line of the body,
and `allowed-tools`, `model`, and `disable-model-invocation` silently stop
applying. Nothing warns at normal verbosity, and the file still *reads*
correctly, so a scorer eyeballing it sees a healthy description and scores Dim 1
on text the loader already threw away.

Regex extraction cannot see this — `rg '^description:'` matches a broken block
exactly as well as a valid one. That is not hypothetical: this rubric's own
quick-check snippet and `frontmatter-lengths.py` were both regex-only until
2026-08-20, and printed clean, confident numbers for two skills whose
frontmatter had not parsed for months. Run the script (it now parse-gates first)
rather than grepping. The usual cause is an unquoted value containing `': '`;
the fix is a block scalar (`description: >-` with the value indented beneath).

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

Quick check — `frontmatter-lengths.py` covers the parse gate and both length
caps in one call, and exits non-zero on a violation:

```bash
python3 <skill-improver>/scripts/frontmatter-lengths.py <skill>/SKILL.md
```

Name-rule check (regex is adequate here ONLY because the parse gate above has
already passed):

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

Any hard fail → cap Dim 9 at 3 and surface the specific violation in the
justification. `freshen` mode will not fix these — author must rename or
edit the frontmatter.

**Staleness cap (sources.md dates):**

When `references/sources.md` exists with per-row `Last verified:` dates, cap
Dim 9 based on the **oldest** `Last verified:` date:

| Oldest entry age | Max Dim 9 |
|------------------|-----------|
| ≤ 90 days | no cap |
| 91–180 days | 7 |
| > 180 days | 5 |
| No `Last verified:` markers | 6 |
| `references/sources.md` absent | 6 |

Tolerance: if ≥ 80% of rows have `Last verified:` dates, use the oldest dated
row; if < 80% have dates, treat the file as lacking markers. Rows marked
`<!-- ignore-freshen -->` (historical/pinned sources the author keeps as-is,
e.g. unfetchable social posts already quoted in the skill) are excluded from
the cap computation entirely.

Quick check:

```bash
rg -v 'ignore-freshen' references/sources.md \
  | rg '^\|.*\| (\d{4}-\d{2}-\d{2}) \|' -o -r '$1' | sort | head -1
```

When the cap triggers, record a justification like "Dim 9 capped at 7 —
oldest sources.md date is 2025-12-02 (139 days old)" and recommend running
`freshen <skill>` as the improvement path, since score-loop mutations cannot
resolve staleness without online probes.

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

Diagnostic patterns originally drawn from Boris Cherny (creator of Claude Code,
Anthropic; Lenny's podcast 2026) and since confirmed in first-party writing by
Thariq Shihipar, *"The new rules of context engineering for Claude 5 generation
models"* (2026-07-24) — which reports **over 80% of Claude Code's system prompt
removed for Opus 5 / Fable 5 with no measurable loss on coding evals**, and names
all three patterns below as superseded practice. **Cite the blog, never the
podcast.** The X row that once carried the podcast attribution was read through
a browser on 2026-08-20 — the `402` had been the fetcher, not the page — and it
turned out to be a third-party post about token-waste patterns containing none
of the claims attributed to it (`sources.md`, row marked MISATTRIBUTED). The
blog is first-party and carries all three patterns plus the measured cost
evidence below, so nothing here rests on the bad citation; but the podcast
origin itself is now **unverified**, and no rule may be justified by it alone.

The cost of *not* lifting these caps is measured, first-party, and stated to
apply to skills. From *Optimizing for cost and intelligence* (Anthropic,
re-read 2026-08-19), on a support-desk evaluation:

- Prompts written for Opus 4.8 cost **36% more per ticket** on Opus 5 **for no
  change in accuracy** — text that compensated for an older model is pure
  overhead on a newer one, which is the decay these caps predict, priced.
- Auditing the same prompts against the current model made Opus 5 both
  **14% cheaper than unaudited and more accurate** (97% of tickets, up from
  92%). The Sonnet 4.6 → Sonnet 5 migration: **14% off at equal accuracy**.
- The two kinds of stale text fail differently. Over-obeyed instructions cost
  **money**: removing "verify twice" cut cost per ticket **by a third**, and
  "be maximally thorough" nearly as much. Broken or conflicting scaffolding
  costs **accuracy**: a retired thinking setting, contradictory rules, and a
  hand-rolled scratchpad that fights the model's own thinking each restored
  **7-11 accuracy points** on Opus 5 when removed.
- The page says the patterns "appear in tool descriptions and skills, and are
  worth removing there too" — so this is evidence about this rubric's subject
  matter, not an analogy borrowed from prompt engineering.

Read that against the cap table: "verify twice" is Dim 6 scaffolding, the
hand-rolled scratchpad is scaffolding that fights the grain, and a prompt
carrying an older model's workarounds is the compensation cap exactly. The
caps are not a style preference — an uncapped skill of this shape is
measurably slower, dearer, and less accurate on the model it runs on today.

These do NOT add an 11th dimension — they cap existing dims when triggered, the
same way the Dim 9 staleness cap works. The bitter lesson applied to skills:
skills that fight the model's grain or compensate for current-model limits decay
across releases.

| Pattern | Detection | Cap |
|---|---|---|
| **Up-front context dumps** — skill front-loads domain context the model could fetch via Read/Grep/WebFetch | Sections >30 lines describing facts (not procedures) without pointing at a tool/file. Boris: "give it a tool so it can get the context it needs." | **Dim 4 (Actionability) capped at 7** |
| **Model-version compensation** — skill contains language like "Claude tends to X, always remind it Y" or version-specific workarounds for behaviour that may be fixed in newer releases | Compensation-language probe below finds 3+ matches. | **Dim 9 (Domain Accuracy) capped at 7** |
| **Goal + tool pointer** (pro-pattern, no cap) | Skill body is short imperative goal + reference to a tool/file/script. Reward signal — flag in justification, no scoring impact beyond the dim its presence helps. | (none) |

Compensation-language probe (kept outside the table — `|` inside a table cell
must be written `\|`, and that escaped form is a valid regex that silently
matches nothing, so a pasted-from-table command reports a clean skill):

```bash
rg -in 'claude (tends to|sometimes|often)|always remind|model (frequently|tends)|compensate for' SKILL.md references/
```

First-party tooling now targets the same pattern: Claude Code v2.1.221 added a
`prompt-audit` subcommand to the bundled `claude-api` skill, which audits
prompts **and tool descriptions** for "patterns written for older models".
Run it alongside the regex — it is free hypothesis supply for this cap, and it
reads the same text the cap scores.

### Procedural steps — advisory signal, NO cap (withdrawn 2026-08-20)

**There is no step-count cap.** A "≥ 8 scaffold items → Dim 6 capped at 6" rule
was carried here and is withdrawn: it had no source, and it contradicted the
evidence it cited.

What the sources actually say, checked 2026-08-20:

- **No first-party or peer-reviewed source gives a numeric threshold** for
  numbered or procedural steps in a skill. Not the platform best-practices doc,
  not the two claude.com blog posts, not SkillLens, not agentskills.io. The 8
  was inherited from a naive `rg -c '^\s*\d+\. '` detector and never
  revisited when that detector was replaced.
- **Anthropic's guidance points the other way.** *"Set appropriate degrees of
  freedom. Match the level of specificity to the task's fragility and
  variability."* Low freedom — explicit sequential steps — is the RECOMMENDED
  shape when *"operations are fragile and error-prone / consistency is critical
  / a specific sequence must be followed."* The same doc says *"Use workflows
  for complex tasks. Break complex operations into clear, sequential steps"*,
  with no ceiling, and its own worked examples run 4–6 steps.
  [best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- **SkillLens measured this property as non-predictive.** Rewriting one skill
  into different surface formats yielded *statistically indistinguishable*
  downstream gains (p > 0.34). Its three validated predictors —
  Failure Mechanism Encoding, Actionable Specificity, High-Risk Action
  Blacklist — are content properties. **None is a count.**
- Capping on a step count therefore contradicted this rubric's own
  §"Format-only hypotheses are low expected value", which cites the same paper.

**What replaces it.** Judge procedure by fit, not by count. A long sequence is
correct where the operation is fragile, consistency matters, or order is
load-bearing; it is waste where the model would reach the same steps unaided.
That is a judgement, and the rubric records it as one — in the Dim 6
justification, never as an automatic cap.

`scripts/scaffold-probe.py` still classifies items (scaffold / criterion /
branch) and remains useful for *finding* candidate bloat — read its list, then
decide. It no longer sets a score. Its classification insight stands on its own:
criteria and branches encode judgment the model cannot infer, and Delba de
Oliveira's verification-loops post makes the case directly — *"Reject any
migration that drops a column without a backfill step" is a deterministic rule
no generic linter will catch but a project-specific one will.* Penalising a
skill for writing those down was always the inversion; the fix is to stop
penalising steps at all, not to count them more cleverly.

**Do not re-introduce a count-based cap without a source that states one.**

When a Boris cap triggers, record the justification like:
> "Dim 4 capped at 7 — §Background front-loads 60 lines of protocol facts
> (lines 45-105) with no pointer to a tool or file that would fetch them.
> Boris alignment failure: up-front context dump."

### Induced cost — what the skill costs to OBEY

Every cap above measures the skill's **text**. Dim 2 counts lines, and a lean
line count is satisfied by a 90-line skill that says "read every
reference before starting", fans out subagents with no ceiling, and pins
`effort: xhigh`. That skill is cheap to load and expensive to run, and nothing
in this rubric currently sees the difference.

`scripts/induced-cost-probe.py [SKILL.md] [--refs]` reports four triggers.
All four are **structural** — none asks whether prose "feels wasteful," which
is the judgment SkillLens clocked at 46.4%, worse than chance:

| Trigger | Detection | Why it costs |
|---|---|---|
| `effort-pin` | frontmatter `effort:` at high/xhigh/max on a skill with 2+ modes | Overrides the session on *every* invocation, including the cheap modes the skill itself defines. |
| `eager-read` | "read all/every/each reference" with no conditional scoping it | Pays for the whole reference set on a run that needed one file. Point-of-use phrasing ("read each reference at its question") is the fix, and the probe stays quiet on it. |
| `uncapped-fanout` | a spawn imperative with no agent-count cap **anywhere in the skill** | An unbounded fan-out is unbounded spend. The cap is looked for skill-wide, so stating it once in SKILL.md covers the reference files carrying the spawn tails. |
| `over-obedience` | "verify twice", "be maximally thorough", "investigate fully even when it looks simple" | The priced one: removing "verify twice" cut cost per ticket **by a third** with no accuracy change, and the source says these patterns apply to skills. |

**Cap: Dim 6 (Simplicity) capped at 6** when any trigger fires. As with the
other caps, a triggered skill may still be right — record the dismissal reason
rather than silently ignoring it, the way the `effort: xhigh` ruling is
dismissed in the backlog.

**The cap is two-sided, and this half is not optional.** Leaner is not
automatically cheaper. A skill trimmed until it is vague makes the agent flail,
re-deriving from scratch what the text used to state, and that costs more than
the lines saved. **Dim 5 (Completeness) is the brake**: an induced-cost hit
never justifies a cut that drops scope the description promises. Fix the
trigger — scope the read, state the cap, delete the over-obedience clause —
not the length. The probe has no "too short" trigger by design.

Measured on this fleet (68 skills, `--refs`): **3 fire**. An earlier, looser
version fired on 4 of 6 skills it was tested against, mostly on prose that
*quoted* these patterns while discussing them; it was narrowed until it
separated mention from use. `--selftest` asserts each trigger fires on its own
shape and stays quiet on the near-miss that shares its vocabulary — run it
after any change to the patterns.

---

The improvement loop should prefer hypotheses that lift Boris caps over
those that lift uncapped dims of the same magnitude — capped dims are
*structural* problems (rot fast across releases) while uncapped ones
are usually *cosmetic*.

---

## SkillLens Utility Check (cross-cutting, evidence-based)

From Microsoft's SkillLens study (arXiv:2605.23899, 2026-05): an LLM judge
scoring skill *text* picked the higher-utility skill only 46.4% of the time
(random), and on the largest-gap pairs only 15.8% — **the skill that reads
better is often the one that performs worse**. Plausibility dimensions
(clarity, conciseness, structure, formatting, tone) carried no predictive
signal; skill *format* (list vs prose vs checklist) was statistically
non-significant on every tested target. Only three text properties predicted
downstream utility (better-rates 64–66%):

1. **Failure Mechanism Encoding** — names concrete failure mechanisms with
   executable remedies, not generic advice.
2. **Actionable Specificity** — commands, values, decision points (≈ Dim 4).
3. **High-Risk Action Blacklist** — names what NOT to do and when.

Scoring consequences (same mechanism as the Boris caps):

| Pattern | Detection | Effect |
|---|---|---|
| **Generic-advice body** — guidance is mostly "do X well" platitudes with no mechanism/remedy pairs | Read the skill's core teaching sections: can each major claim be traced to a concrete failure mode, command, threshold, or counter-example? | **Dim 10 capped at 6** |
| **No high-risk blacklist where risk exists** — skill covers an operation with known destructive/irreversible failure modes but never says what NOT to do | Check whether "do NOT", "never", or an anti-patterns section exists for the risky operations in scope | **Dim 5 capped at 8** |
| **Mechanism + remedy density** (pro-pattern) | Failure modes named with executable fixes throughout | Reward signal — note in justification |

Guard for scorers: do not reward fluency. A skill scoring high on Dims 3/6/8
with a generic-advice body is the SkillLens inversion case — the caps above
exist to catch it. Format-only differences (list vs prose) are noise;
never justify a score delta on format alone.

---

## Negative-Transfer Gate (Dim 10 cap, evidence-based)

SkillLens (arXiv:2605.23899) measured skills against a no-skill baseline and
found they help in only **75% of extractor-target pairs — 25% are net-harmful**,
with the worst domain at **47% negative** ("ALFWorld is the most fragile").
A skill is not neutral-to-positive by default. Roughly one in four makes the
agent *worse* at the task it was written for.

Dim 10's own test — "if this skill were deleted, would Claude produce noticeably
worse results?" — is precisely this measurement. Scorers currently answer it from
intuition, which is the judgment SkillLens clocked at 46.4% (worse than chance).
So Dim 10 is capped by what has actually been measured:

Every row below is against a **noise floor of `1/n_cases`** — the delta produced
by a single eval case flipping. Take the floor and the verdict from
`scripts/eval-evidence.py`; do not eyeball the sign.

| Evidence | Max Dim 10 |
|---|---|
| `delta_pass_rate ≤ −2 × floor` — skill loses to no-skill | **2**, and surface it as the headline finding |
| inside the band (`−2 × floor` … `+floor`) **and** `delta_tokens > 0` — unresolved, and it costs | **3**, and surface it: it costs and has not been shown to pay |
| inside the band, `delta_tokens ≤ 0` — unresolved, but free | **8** — unresolved is not "neutral"; the unmeasured cap stands |
| `delta_pass_rate ≥ +floor` | no cap — score on the evidence |
| Never measured | **8** — "essential" (9–10) is a claim about outcomes, not text |

**Why the band is asymmetric.** Clearing the cap takes `+floor`; firing the
harmful verdict takes twice that. Calling a skill harmful is the expensive
error — it gets rewritten or deleted on the strength of that number — while a
false "unresolved" only withholds a 9 or 10. NVIDIA's published Skill Lift band
(+0.05 pass, −0.10 fail) is asymmetric in the same direction, for the same
reason; the floor here is measured from the corpus instead of fixed, because a
constant is too tight at 8 cases and far too loose at 3.

**"Inside the band" is not "roughly neutral."** It means the corpus cannot
answer the question. At the fleet median of 3 cases the floor is 0.33 — almost
nothing resolves. The fix is more cases (`scripts/grow-evals.py`, floor of 8),
never a more generous reading of the same number.

**Several measurements: the worst governs.** Per-model and per-case-subset runs
are not replicates and cannot be averaged. The gate asks whether the skill is
*shown* to be essential, so a measurement that fails to show it counts against
the claim.

The unmeasured cap is the one that binds most often, and it is deliberate: a
9–10 on Dim 10 asserts the skill "fundamentally changes Claude's capability",
which no amount of reading the text can establish.

**How to measure it.** Do NOT build a harness — the official `skill-creator`
plugin already runs each eval case with and without the skill and computes the
delta:

```bash
# after skill-creator has produced with_skill/ and without_skill/ runs
cd ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator
python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
# -> benchmark.json carries delta_pass_rate, delta_time, delta_tokens
```

Requires the target to have `evals/evals.json`. A skill with no eval set cannot
clear the unmeasured cap — that is a finding, not an obstacle: log it as an Open
backlog item with action "build an eval set, then measure delta_pass_rate".

**An errored case is not a failed case.** Before reading any delta, check that
every case in `benchmark.json` actually ran. A case that crashed, timed out, or
came back ungraded measured nothing — counting it as a failure manufactures a
negative delta, and silently dropping it changes the denominator between the
with-skill and without-skill arms so the two are no longer comparable. Re-run
the errored cases. If they cannot be made to run, the delta is **unmeasured**
and the 8 cap applies: partial evidence does not clear a gate that exists
precisely because unmeasured skills look fine. This bites hardest at small
corpus sizes — at the fleet median of 3 cases, one errored case is a third of
the evidence (`scripts/grow-evals.py`, floor of 8).

**A negative delta is not automatically a delete.** Check the analyst pass first
— a skill can lose on `pass_rate` while winning on tokens or time, and a single
flaky eval can invert a small delta. Confirm the sign is stable across runs
before acting on it. But do not round a negative delta up to "roughly neutral":
the whole point of the gate is that this failure mode is common and invisible to
text scoring.

### The cost side of the same benchmark

`benchmark.json` carries `delta_tokens` next to `delta_pass_rate`. It is what
splits the old flat `≈ 0` row: a skill that changes no outcome while adding
context is not merely non-discriminating, it is a **pure tax** — a harder
finding than the gate used to produce, and one grounded in measurement rather
than a line count.

`≈ 0` means **inside run-to-run variance**, not literally zero: compare the
delta against the per-config `pass_rate.stddev` that `benchmark.json` already
reports. A delta smaller than the baseline's own spread is noise.

Three things about that number have to be checked before it is used, because
all three are quiet:

- **Sign convention.** The delta is `configs[0] - configs[1]` over the config
  directories in **alphabetical** order. `with_skill` sorts before
  `without_skill` (`_` < `o`), so positive means *the skill costs more*. That
  is an accident of naming, not a guarantee — confirm the two config
  directory names before reading a sign.
- **It may not be tokens.** `tokens` is read from `timing.json`, but only when
  `grading.json` carries no timing of its own; otherwise it silently falls back
  to `execution_metrics.output_chars`. In the common case the field is
  characters. Both configs are measured the same way, so the **sign is sound**
  — the magnitude is not tokens unless you have confirmed the source.
- **The deltas are strings.** `"+0.12"`, `"+1840"` — formatted, not numeric.
  Parse them; do not compare them as they come.

A **positive** `delta_pass_rate` with a large positive `delta_tokens` is not a
cap. The skill earned its cost; report the cost alongside the win and let the
reader decide. Only the `≈ 0` case converts cost into a ceiling.

**No cost dimension, ever.** The obvious move — an 11th dimension scoring
cheapness — is wrong twice: the rubric total is a scalar sum, so a cost term
makes the loop trade quality for cost at an exchange rate nobody chose, and an
empty skill scores 10 on it. Cost enters as caps and gates only. Dim 5 remains
the brake on length; this is the brake on length that bought nothing.

### Floor evidence moves the unmeasured cap

`delta_pass_rate` is scarce — it needs an eval set, and most skills have none.
Floor mode (`scripts/knowledge-floor.py`) supplies a cheaper measurement that
needs no eval set: it asks a bare model, with no skills and no tools, what it
already knows about the skill's subject, and buckets each claim KNOWS /
UNKNOWN / CONFLICTS. That is still not an outcome measurement, but it is a
measurement, and it beats the intuition the unmeasured cap exists to distrust.

So when floor data exists for the skill, it replaces the flat `8`:

| Floor evidence (strongest probed tier) | Max Dim 10 |
|---|---|
| Any **durable** CONFLICT (see below) | **9** — the skill overrides a confident wrong prior |
| Floor ~0% — no claim is known on any probed tier | **9** — every claim is real transfer |
| Mixed (some KNOWS, no durable conflict) | 8 — unchanged |
| Floor ≥80% KNOWS **and** zero CONFLICTS | **5** — the model already carries it; report as a deletion candidate |

Rules for reading that table:

- **`delta_pass_rate` still wins.** Floor only moves the *unmeasured* cap. A
  measured delta of any sign overrides every row here.
- **A partial floor run moves nothing.** Read `scored` / `unmeasured` before
  the share: a claim whose probe failed or came back `UNGRADED` was not
  measured, and a share computed over the full claim set instead of the graded
  one understates the floor. `NO SCORE` — nothing graded — leaves the flat `8`
  in place. Note which row this protects: a totally failed run used to produce
  a 0% floor, and 0% is the "every claim is real transfer" row, so the probe
  breaking *raised* the cap to 9. Failure must never score better than success.
- **10 is still unreachable from floor alone.** Recall is not application: a
  model can state a flag correctly and never think to use it mid-task. Only a
  positive measured delta clears 9.
- **Durable conflict beats high floor** when both apply — that is profile 3
  below, and it is the case a leanness number gets backwards.
- **No floor data → the flat `8` stands.** Do not infer a floor from reading
  the text; run the probe or take the cap.

**Durable means it survives on a peer tier, not a weaker one.** Measured on
this fleet: of 17 opus CONFLICTS on the 8 skills also probed on fable, 12
conflicted on fable too. Of 31 opus CONFLICTS across all 68 skills probed on
haiku, only 3 conflicted there — because 26 of them came back UNKNOWN. The
weak tier has no confident wrong prior to override, so its silence is not
evidence the conflict was transient. Check durability against a frontier-class
sibling; a downgrade tier cannot falsify a conflict.

### Three profiles — a floor number alone mis-ranks one of them

| Floor | Conflicts | Profile | What to do |
|---|---|---|---|
| high | none | **deletion candidate** | confirm with an eval delta, then cut to the delta |
| low | any | **pure transfer** | nothing to trim; the skill is the only source |
| high | durable | **correction skill** | make it **louder**, not leaner |

Profile 3 is why leanness cannot be scored from the floor percentage. A skill
whose subject the model mostly knows, but gets confidently wrong in a few
places, looks like the leanest thing on the leaderboard and is the one whose
corrections most need emphasis — front-loaded, stated as a contradiction of the
common belief, not buried as one bullet among the parts the model already had
right. Measured examples of profile 3 on this fleet: `ubuntu-netplan` (13/15
known, 2 conflicts) and `keda` (10/12 known, 1 conflict). Both sit at the top
of the floor leaderboard next to `makefile-best-practices` (10/10, zero
conflicts) — which is profile 1 and the opposite recommendation.

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
