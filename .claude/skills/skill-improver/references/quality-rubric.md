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
- Second person: "Use this skill when..." instead of "This skill should be used when..."
- Vague: "Provides guidance for X" with no trigger phrases
- Over-broad: Triggers on common words that would cause false positives
- Under-specified: Misses the most common ways users phrase the request
- Key triggers buried past character 1,536 (lost to truncation)
- `description` stuffed with trigger phrases that belong in `when_to_use` (separate field, concatenated in the listing)

**Check method:** Mentally test 5 realistic user prompts. Would this description trigger? Then test 3 unrelated prompts. Would it falsely trigger? Also verify the first 1,536 chars of combined `description` + `when_to_use` contain the most important trigger keywords. Use `head -c 1536` to check.

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

**Official limit:** Keep SKILL.md **under 500 lines** (per agentskills.io spec and
official docs). The 3-level loading system: metadata (~100 tokens at startup) →
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
| 9–10 | Every instruction is unambiguous, includes validation steps, handles decision points |

**Common failures:**
- "Configure the settings as needed" — which settings? What values?
- Steps assume knowledge the skill should provide
- Missing validation — no way to confirm a step succeeded

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
best practices. Also check: does the skill use appropriate frontmatter fields? A skill
scoped to specific file types should use `paths:`. A task skill with side effects
should use `disable-model-invocation: true`. Scripts referencing the skill directory
should use `${CLAUDE_SKILL_DIR}`. See `references/anthropic-skill-design.md` for the
complete frontmatter reference.

**Hard-fail validation (spec violations cap Dim 9 at 3):**

Verify the skill would pass `skills-ref validate`. Any of these failures is a
spec violation that makes the skill non-conformant — `skills-ref` would reject it.

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

Quick check:

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
row; if < 80% have dates, treat the file as lacking markers.

Quick check:

```bash
rg '^\|.*\| (\d{4}-\d{2}-\d{2}) \|' references/sources.md -o -r '$1' | sort | head -1
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

Diagnostic patterns drawn from Boris Cherny (creator of Claude Code,
Anthropic; Lenny's podcast 2026). These do NOT add an 11th dimension —
they cap existing dims when triggered, the same way the Dim 9 staleness
cap works. The bitter lesson applied to skills: skills that fight the
model's grain or compensate for current-model limits decay across
releases.

| Pattern | Detection | Cap |
|---|---|---|
| **Strict workflow scaffolding** — skill prescribes "do step 1, then 2, then 3..." procedural steps the model could discover via plan mode | Body contains numbered procedural lists describing the *invocation flow* (not reference content) AND the model could plausibly do the task with a goal + tool pointer. `rg -nE '^\s*\d+\. ' SKILL.md \| wc -l` ≥ 8 in non-reference sections is a strong signal. | **Dim 6 (Simplicity) capped at 6** |
| **Up-front context dumps** — skill front-loads domain context the model could fetch via Read/Grep/WebFetch | Sections >30 lines describing facts (not procedures) without pointing at a tool/file. Boris: "give it a tool so it can get the context it needs." | **Dim 4 (Actionability) capped at 7** |
| **Model-version compensation** — skill contains language like "Claude tends to X, always remind it Y" or version-specific workarounds for behaviour that may be fixed in newer releases | `rg -inE 'claude (tends to\|sometimes\|often)\|always remind\|model (frequently\|tends)\|compensate for'` finds 3+ matches. | **Dim 9 (Domain Accuracy) capped at 7** |
| **Goal + tool pointer** (pro-pattern, no cap) | Skill body is short imperative goal + reference to a tool/file/script. Reward signal — flag in justification, no scoring impact beyond the dim its presence helps. | (none) |

When a Boris cap triggers, record the justification like:
> "Dim 6 capped at 6 — skill prescribes 11-step procedural workflow
> (lines 45-89) the model could discover via plan mode. Boris
> alignment failure: strict workflow scaffolding."

The improvement loop should prefer hypotheses that lift Boris caps over
those that lift uncapped dims of the same magnitude — capped dims are
*structural* problems (rot fast across releases) while uncapped ones
are usually *cosmetic*.

---

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
