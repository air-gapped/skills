# Improvement Patterns Catalog

Common improvements organized by scoring dimension. Each pattern includes the problem, the fix, and a before/after example. Use this as a playbook when deciding what to improve in each iteration.

## Table of Contents
- [Dim 1 — Trigger Precision](#dimension-1-trigger-precision): 1.1 Add specific phrases · 1.2 Fix person · 1.3 Reduce false positives · 1.4 Front-load within listing cap · 1.5 Split description vs when-to-use
- [Dim 2 — Progressive Disclosure](#dimension-2-progressive-disclosure): 2.1 Extract to references · 2.2 Add missing pointers · 2.3 Flatten nested references
- [Dim 3 — Writing Style](#dimension-3-writing-style): 3.1 Second-person → imperative · 3.2 One-time steps → standing instructions · 3.3 Remove hedge language · 3.4 Prohibitions → positive statements
- [Dim 4 — Actionability](#dimension-4-actionability): 4.1 Add concrete commands · 4.2 Add validation steps · 4.3 Raise completion-criterion demand
- [Dim 5 — Completeness](#dimension-5-completeness): 5.1 Cover missing use cases · 5.2 Add error handling
- [Dim 6 — Simplicity](#dimension-6-simplicity): 6.1 Remove redundant sections · 6.2 Cut defensive boilerplate · 6.3 Collapse trivial examples
- [Dim 7 — Resource Quality](#dimension-7-resource-quality): 7.1 Make examples runnable · 7.2 Add script documentation · 7.3 Fan-out cache discipline
- [Dim 8 — Internal Consistency](#dimension-8-internal-consistency): 8.1 Fix dangling references · 8.2 Standardize terminology · 8.3 Co-locate scattered concept material
- [Dim 9 — Domain Accuracy](#dimension-9-domain-accuracy): 9.1 Update deprecated APIs · 9.2 Fix incorrect defaults · 9.3 Add missing frontmatter fields · 9.4 Use ${CLAUDE_SKILL_DIR} · 9.5 Use dynamic context injection
- [Dim 10 — Differentiation](#dimension-10-differentiation): 10.1 Add procedural knowledge · 10.2 Add decision trees
- [Meta-Patterns](#meta-patterns-cross-dimensional): Simplification Pass · Trigger Audit · Reference Rebalance

---

## Dimension 1: Trigger Precision

### Pattern 1.1: Add Specific Trigger Phrases

**Problem:** Description is vague or abstract.

**Before:**
```yaml
description: Helps with database operations and queries.
```

**After:**
```yaml
description: This skill should be used when the user asks to "write a SQL query", "optimize a database query", "create a migration", "add an index", "debug slow queries", or mentions database performance, schema design, or ORM configuration.
```

### Pattern 1.2: Fix Person

**Problem:** Description uses second person or imperative.

**Before:**
```yaml
description: Use this skill when you need to work with Docker containers.
```

**After:**
```yaml
description: This skill should be used when the user asks to "create a Dockerfile", "set up docker-compose", "debug container issues", "optimize Docker builds", or mentions container orchestration, image layers, or multi-stage builds.
```

### Pattern 1.3: Reduce False Positives

**Problem:** Description triggers on overly common words.

**Before:**
```yaml
description: This skill should be used when the user mentions "code", "file", or "error".
```

**After:**
```yaml
description: This skill should be used when the user asks to "lint Python code", "run flake8", "configure ruff", "fix linting errors", or mentions Python code style, PEP 8 compliance, or auto-formatting.
```

### Pattern 1.4: Front-Load Description Within the Listing Cap

**Problem:** Key trigger phrases are buried past the truncation point. The skill listing
truncates the combined `description` + `when_to_use` at **1,536 chars** on Claude Code
v2.1.105+ (was 250 prior). If targeting older Claude Code, treat 250 as the cap.

**Before:**
```yaml
description: >-
  This comprehensive skill provides detailed guidance and step-by-step workflows
  for managing, configuring, and troubleshooting Docker containers, images,
  Dockerfiles, multi-stage builds, docker-compose setups, and container orchestration.
```
(Preamble delays the real keywords — scan-readability suffers even if characters fit.)

**After:**
```yaml
description: >-
  Manage Docker containers, Dockerfiles, docker-compose, and multi-stage builds.
when_to_use: >-
  Use when the user asks to "create a Dockerfile", "debug container issues",
  "optimize Docker builds", or mentions container orchestration or image layers.
```

**Check:** Count characters of combined `description` + `when_to_use`. Verify all critical
keywords appear early — front-load even within the 1,536 cap, since the dynamic budget
shrinks descriptions when many skills are installed.

### Pattern 1.5: Split Description vs. When-to-Use

**Problem:** The `description` field is stuffed with trigger phrases, example requests,
and a summary — making the core purpose hard to scan.

**Fix:** Put the *what* in `description`, put trigger phrases and example requests in
`when_to_use`. They concatenate in the listing, but separating them improves both
scannability and reusability across skill catalogs.

**Before:**
```yaml
description: Lint Python code, run flake8, configure ruff, fix linting errors, handle PEP 8 compliance, set up pre-commit hooks for Python, check auto-formatting with black, resolve style violations, or work with Python code style tools.
```

**After:**
```yaml
description: Lint and auto-format Python code with ruff, flake8, and black.
when_to_use: Triggers on "lint Python", "run flake8", "configure ruff", "fix linting errors", "set up pre-commit for Python", or mentions PEP 8 compliance or Python style violations.
```

---

## Dimension 2: Progressive Disclosure

### Pattern 2.1: Extract to References

**Problem:** SKILL.md exceeds 500 lines with detailed reference material inline.

**Fix:** Move detailed sections to `references/` and replace with a pointer.

**Before (in SKILL.md):**
```markdown
## Complete API Reference

### Method: createUser(name, email, role)
Parameters:
- name (string, required): ...
- email (string, required): ...
[... 2,000 more words of API docs ...]
```

**After (in SKILL.md):**
```markdown
## API Reference

For full API documentation including parameters, return types, and error codes, consult **`references/api-reference.md`**.

Quick reference for the most common methods:

| Method | Purpose |
|---|---|
| `createUser(name, email, role)` | Create a new user |
| `deleteUser(id)` | Remove a user |
```

### Pattern 2.2: Add Missing Pointers

**Problem:** Reference files exist but SKILL.md never mentions them.

**Fix:** Add an "Additional Resources" section at the end of SKILL.md.

```markdown
## Additional Resources

### Reference Files
- **`references/patterns.md`** — Detailed patterns for common scenarios
- **`references/troubleshooting.md`** — Error resolution guide

### Scripts
- **`scripts/validate.sh`** — Validate configuration before deployment
```

### Pattern 2.3: Flatten Nested References

**Problem:** Reference files link to other reference files, creating chains that
Claude may only partially read.

**Before:**
```
SKILL.md → references/overview.md → references/details.md → references/api.md
```
Claude may only `head -100` on `details.md` and never reach `api.md`.

**After:**
```
SKILL.md → references/overview.md
SKILL.md → references/details.md
SKILL.md → references/api.md
```
All references linked directly from SKILL.md, one level deep.

**Fix:** Audit reference chains. Move all deep links up to SKILL.md as direct
references. For files over 100 lines, add a table of contents at the top.

---

## Dimension 3: Writing Style

### Pattern 3.1: Convert Second-Person to Imperative

**Problem:** Body uses "you should", "you need to", "you can".

**Before:**
```markdown
You should first read the configuration file. Then you need to validate
the settings. You can use the grep tool to search for errors.
```

**After:**
```markdown
First, read the configuration file. Validate the settings against the
schema. Use the grep tool to search for errors.
```

### Pattern 3.2: Rewrite One-Time Steps as Standing Instructions

**Problem:** Skill content is structured as a sequence of first-turn steps ("first do
X, then Y") that have no force on later turns. SKILL.md loads once and is not re-read
— compaction may also drop older invocations.

**Fix:** Rewrite guidance that must apply throughout the session as *standing* rules.
Keep true first-turn setup steps (initialization, fetch) separate from standing
conventions.

**Before:**
```markdown
1. Read the config file at ~/.myapp/config.yml
2. Apply the coding conventions below
3. When writing tests, use pytest parametrize
```

**After:**
```markdown
## First-turn setup
1. Read the config file at ~/.myapp/config.yml

## Standing conventions (apply throughout the session)
- Use pytest parametrize for all test matrices
- Prefer pathlib over os.path
- Return type hints on all public functions
```

**Why this matters:** After auto-compaction, re-attached skills keep only the first
5,000 tokens with a combined 25K budget across all skills; older invocations can be
dropped entirely. Standing-rule phrasing survives context shuffling; numbered-step
phrasing reads as if the steps are already done.

### Pattern 3.3: Remove Hedge Language

**Problem:** Unnecessary qualifiers weaken instructions.

**Before:**
```markdown
It might be a good idea to perhaps consider checking the logs before
you try to make any changes to the configuration.
```

**After:**
```markdown
Check the logs before modifying the configuration.
```

### Pattern 3.4: Convert Steering-by-Prohibition to Positive Statements

**Problem:** Guidance steers by naming the unwanted behavior ("don't write
long comments", "avoid nested callbacks"). Negation drags the forbidden
behavior into context and makes it MORE available, not less — the "don't"
is a weak modifier on a strongly-activated concept, so the ban half-reads
as an instruction to do the thing.

**Fix:** State the target behavior so the banned one is never named.

**Before:**
```markdown
Don't write multi-paragraph comments. Avoid explaining what the next line
does. Never narrate why your change is correct.
```

**After:**
```markdown
Write one-line comments that state only what the code cannot show — a
constraint, an invariant, a non-obvious reason.
```

**Guardrail exception:** hard prohibitions for destructive or irreversible
actions stay — SkillLens found High-Risk Action Blacklists predictive of
skill utility (rubric §SkillLens Utility Check), and rubric Dim 5 caps
skills that omit them where risk exists. The two rules compose: keep "do
NOT" for the blacklist (what must never run and when), and pair each entry
with the positive alternative ("do NOT `git checkout -- <file>` with
uncommitted keeps — restore the last kept snapshot instead"). What this
pattern removes is prohibition as *style steering*, not as a safety rail.

---

## Dimension 4: Actionability

### Pattern 4.1: Add Concrete Commands

**Problem:** Instructions are abstract.

**Before:**
```markdown
Set up the testing environment appropriately.
```

**After:**
```markdown
Set up the testing environment:
1. Run `npm install --save-dev jest @testing-library/react`
2. Create `jest.config.js` in the project root
3. Add `"test": "jest"` to `package.json` scripts
4. Verify with `npm test -- --version`
```

### Pattern 4.2: Add Validation Steps

**Problem:** No way to confirm a step succeeded.

**Before:**
```markdown
Deploy the application to staging.
```

**After:**
```markdown
Deploy the application to staging:
1. Run `deploy.sh staging`
2. Verify: `curl -s https://staging.example.com/health` should return `{"status":"ok"}`
3. If health check fails, check `deploy.log` for errors.
```

### Pattern 4.3: Raise Completion-Criterion Demand

**Problem:** A step's done-condition checks that output exists, not that the
work is covered. The agent ends the step as soon as anything is produced —
premature completion — because nothing in the bound forces it to keep digging.

**Fix:** Where the work has an enumerable scope, bind the step to exhaustive
coverage: "every X accounted for", not "produce an X list". Demand is a
separate axis from clarity — both criteria below are checkable; only the
second forces legwork.

**Before:**
```markdown
Review the migration and list the affected tables.
```

**After:**
```markdown
Review the migration. The step is done when every table the migration
touches appears in the list with its change type (added / dropped /
altered) — cross-check the list against `grep -c 'TABLE' migration.sql`.
```

---

## Dimension 5: Completeness

### Pattern 5.1: Cover Missing Use Cases

**Problem:** Description promises coverage the body doesn't deliver.

**Fix:** Audit trigger phrases against body content. For each trigger phrase, ensure there's a corresponding section or instruction.

### Pattern 5.2: Add Error Handling

**Problem:** Only the happy path is covered.

**Fix:** Add a "Troubleshooting" section or inline error handling at failure-prone steps.

---

## Dimension 6: Simplicity

### Pattern 6.1: Remove Redundant Sections — after classifying the overlap

**Problem:** The same information appears in multiple places.

**Two of the three kinds of overlap must NOT be deleted.** Similar text is not
evidence of redundancy, and this skill's standing bias toward deletion is what
makes the distinction load-bearing. Classify before cutting:

| Verdict | What it looks like | Action |
|---|---|---|
| `DUPLICATE` | Repeats the same information with nothing added | Consolidate into one place. The only actionable verdict. |
| `INTENTIONAL_DETAIL` | A short overview in `SKILL.md`, the development in `references/` | **Keep.** This is progressive disclosure — the structure the skill is supposed to have. |
| `RELATED_BUT_DISTINCT` | Same topic, different purpose or angle | **Keep.** Both earn their place. |

**This is not a hypothetical guard.** Measured across the whole fleet —
62 skills analysed (6 exceeded the tool's chunk ceiling), 520 clusters of
similar content classified:

| verdict | clusters | action |
|---|---|---|
| `INTENTIONAL_DETAIL` | 292 | keep |
| `RELATED_BUT_DISTINCT` | 138 | keep |
| `DUPLICATE` | **90** | consolidate |

**83% of similar-looking content was correct as written.** Those 430 clusters
are what a bare similarity score would flag and a deletion bias would cut —
and cutting them destroys the progressive disclosure that makes a skill
readable. 23 skills had no duplication at all.

The 90 that are real are why this is a classifier and not a rubber stamp. Worst
offenders: `autoresearch` (7), `jinja-expert` (6), `keda` (6), `sglang-hicache`
(5). One was verified by hand: `keda` carries the same six-step triage block in
`SKILL.md:295-313` and `references/troubleshooting.md:12-27`, differing only in
placeholder style (`<name>` vs `"$NAME"`). Two independent models agreed on
keda's count, through different gateways.

**Fix (for `DUPLICATE` only):** keep it in one place, prefer the more prominent
location, delete the other. Pure relocation is one atomic change; relocation
that rewrites prose is two (SKILL.md §"The split test for atomicity").

**To find candidates** rather than eyeballing them, SkillEvaluator's intra-skill
pass does the clustering and the classification:

```bash
skillevaluator context-optimization-check <skill-dir>
```

It needs both an embeddings provider and a chat model. Two limits worth knowing:
it bounds pairwise work at `n*(n-1)/2 * vector_dimension <= 25M`, which at
bge-m3's 1024 dims refuses above ~221 chunks (`skill-improver` is 444), and the classification is one LLM's judgement —
treat a `DUPLICATE` verdict as a candidate to read, not a mandate to cut.

### Pattern 6.2: Cut Defensive Boilerplate

**Problem:** Sections like "Important Notes", "Please Remember", "Disclaimer" that add no instructional value.

**Before:**
```markdown
## Important Notes

Please note that this skill is provided as-is. Results may vary depending
on your specific configuration. Always test in a non-production environment
first. The authors are not responsible for any issues that may arise.
```

**After:** Delete the entire section.

### Pattern 6.3: Collapse Trivial Examples

**Problem:** Examples that don't add value beyond the instruction.

**Before:**
```markdown
Use the `--verbose` flag for detailed output.

Example:
```bash
command --verbose
```

**After:**
```markdown
Use `--verbose` for detailed output.
```

---

## Dimension 7: Resource Quality

### Pattern 7.1: Make Examples Runnable

**Problem:** Examples are pseudocode or snippets that can't be executed.

**Fix:** Provide complete, copy-paste-ready examples with all imports, setup, and expected output.

### Pattern 7.2: Add Script Documentation

**Problem:** Scripts exist but have no usage instructions.

**Fix:** Add a comment header to each script:
```bash
#!/bin/bash
# Usage: ./validate.sh <config-path>
# Validates the configuration file against the schema.
# Exit code 0 on success, 1 on validation failure.
```

### Pattern 7.3: Fan-out Cache Discipline

**Problem:** A skill that spawns many same-shape subagents (reviewers,
scorers, scanners — sometimes hundreds) repeats its invariant instructions in
every spawn's prompt string. Cross-subagent prompt-cache sharing covers only
the prefix *before* the prompt string (tools + agent system prompt + project
context) — there is no cache breakpoint inside the first user message — so
every agent bills the full instruction block at full input price, when a
shared prefix would bill it at ~10%.

**Fix:** Restructure the fleet around the cached prefix
(per the Claude Code prompt-caching and workflows docs):

- Move the invariant instructions into a **custom agent definition**
  (`.claude/agents/<name>.md`, or the plugin's `agents/` dir) — its body
  becomes the system prompt, which sits inside the shared cached prefix.
  Each spawn's prompt carries only the variable tail (target path, finding,
  query).
- Keep the fleet uniform on the **six prefix-identity dimensions**: agent
  type, model, effort, tools, output schema (one schema constant, stable key
  order), and working directory. Any mismatch forks the cache.
- `isolation: "worktree"` gives every agent a unique working directory —
  zero sharing. Reserve it for agents that mutate files; read-only fleets
  run in the repo.
- No per-agent decoration early in the prompt ("reviewer 7 of 100",
  timestamps, run IDs).
- Spawn same-type agents in one wave (in a **workflow** fan-out Claude Code
  holds all-but-the-first until the first response begins, then releases the
  rest onto the warm cache) and keep waves within the subagent cache TTL.
- **Subagents get the 5-minute TTL even on a subscription** — the automatic
  1-hour TTL applies only to the main conversation (Claude Code prompt-caching
  docs, verified 2026-08-19). This is the constraint that decides fan-out
  shape: agents spawned minutes apart share nothing, however identical their
  prefixes. Two scorers separated by a full improvement loop can never share a
  cache; the sharing opportunity is *across skills within one wave*, never
  across phases of one skill.
- The system prompt embeds **working directory, platform, shell, OS version,
  and auto-memory paths**, so cwd is part of the prefix by construction — and
  each git worktree is its own working directory.
- A **fork** (`context: fork`) is the exception to all of this: it inherits the
  parent's system prompt, tools, and history exactly, so its first request
  reads the *parent's* cache rather than warming its own.
- Background vs foreground does **not** fork the prefix. `run_in_background`
  changes when the result returns, not the system prompt or tool set.

**Before (in a workflow script or skill body):**
```js
agent(`${TWO_KB_OF_REVIEW_RULES}\nNow review ${file}`)   // ×200 agents, full price each
```

**After:**
```js
agent(`Review target: ${file}`, {agentType: 'reviewer'}) // rules live in agents/reviewer.md, cached once
```

---

## Dimension 8: Internal Consistency

### Pattern 8.1: Fix Dangling References

**Problem:** SKILL.md mentions a file that doesn't exist.

**Fix:** Either create the referenced file or remove the reference.

### Pattern 8.2: Standardize Terminology

**Problem:** The same concept has multiple names.

**Fix:** Pick one term and use it consistently. Find-and-replace across all files in the skill directory.

### Pattern 8.3: Co-locate Scattered Concept Material

**Problem:** One concept's definition, rules, and caveats are fragmented
across sections. Distinct from duplication (Pattern 6.1): duplication repeats
one meaning in two places; scattering splits one meaning across many, so an
agent that jumps to one fragment acts on a partial picture.

**Before:**
```markdown
## Flags
`--foo` — enables foo mode.
...
## Compatibility
`--foo` requires v2.3+.
...
## Troubleshooting
`--foo` with TP>1 corrupts state.
```
(An agent grepping to §Flags recommends `--foo` and never sees the caveats.)

**After:**
```markdown
## Flags
`--foo` — enables foo mode. Requires v2.3+. Do NOT combine with TP>1
(corrupts state) — use `--bar` there instead.
```

**Fix:** For each load-bearing concept (flag, command, config key), gather
its definition, version gates, and caveats under one heading. Grep the
concept's name across the skill directory; more than one hit outside its
home section is the smell.

---

## Dimension 9: Domain Accuracy

> **Guard:** every Dim 9 mutation needs an online or local-execution source —
> training-data memory is NOT a source. The skill's claims may postdate the
> model's knowledge cutoff: a version that "looks too new" is usually correct,
> and lowering it from memory is the canonical staleness failure. See SKILL.md
> §"The Skill Outranks Training Data".

### Pattern 9.1: Update Deprecated APIs

**Problem:** Instructions reference outdated tool versions or deprecated flags.

**Fix:** Verify commands against current documentation — via an online probe
(`gh`, WebFetch, WebSearch), never from memory — and cite the source. If the
"current syntax" remembered from training is OLDER than what the skill says,
the skill is right; do not touch it.

### Pattern 9.2: Fix Incorrect Defaults

**Problem:** Stated default values don't match actual tool behavior.

**Fix:** Test locally or verify online, then correct them. Never "correct" a
value from memory.

### Pattern 9.3: Add Missing Frontmatter Fields

**Problem:** Skill could benefit from frontmatter fields it doesn't use.

**Common opportunities:**
- Description stuffed with trigger phrases → split to `description` (what) + `when_to_use` (triggers)
- Skill scoped to file types but missing `paths:` → add `paths: ["*.py", "*.rs"]`
- Task skill with side effects — or any skill the user only ever fires by
  hand (`/name`) — missing `disable-model-invocation: true`. The second case
  is the bigger win: a hand-only skill's description is pure context load on
  every turn, and the flag removes it from the always-loaded listing entirely
  (see rubric §Dim 1 "Invocation-fit check")
- Background knowledge skill missing `user-invocable: false`
- Script-heavy skill missing `allowed-tools: Bash(python *)`
- Computationally light skill that could use `effort: low`
- Complex reasoning skill that could use `effort: xhigh` (Fable 5, Mythos 5, Opus 5, Opus 4.8/4.7, Sonnet 5) or `effort: max` (those plus Opus 4.6/4.5) — but frontmatter `effort` applies to EVERY invocation of the skill, cheap modes included, so prefer pinning effort on the specific subagent call when only one stage is expensive
- Skill that would benefit from isolation missing `context: fork` (pair with `agent: Explore` or `agent: Plan` for specialized subagent behavior; since v2.1.218 a forked skill runs in the background under the narrower background-subagent tool set — set `background: false` to block the turn and keep the full set)
- Windows-targeted skill using `` !`command` `` blocks but missing `shell: powershell`

**Check:** Read `references/anthropic-skill-design.md` for the complete field reference.
For each field, ask: would this skill work better with this field set?

### Pattern 9.4: Use ${CLAUDE_SKILL_DIR} for Portable Script References

**Problem:** Scripts referenced with hardcoded absolute paths.

**Before:**
```markdown
Run: `python ~/.claude/skills/my-skill/scripts/validate.py`
```

**After:**
```markdown
Run: `python ${CLAUDE_SKILL_DIR}/scripts/validate.py`
```

This works regardless of where the skill is installed (personal, project, plugin).

### Pattern 9.5: Use Dynamic Context Injection

**Problem:** Skill instructions reference data that should be fetched live.

**Before:**
```markdown
1. Run `git log --oneline -5` and read the output
2. Based on the recent commits, summarize changes
```

**After (using !`command` preprocessing):**
```markdown
Recent commits: !`git log --oneline -5`

Summarize the changes shown above.
```

The `` !`command` `` syntax runs before Claude sees the content, injecting live data
directly into the prompt. Claude receives the result, not the command.

---

## Dimension 10: Differentiation

### Pattern 10.1: Add Procedural Knowledge

**Problem:** Skill only restates what Claude already knows.

**Fix:** Add company-specific workflows, tested configurations, non-obvious patterns, or hard-won knowledge that can't be derived from public documentation alone.

### Pattern 10.1b: Convert Generic Advice into Mechanism + Remedy

**Problem:** Guidance states a goal without the failure mechanism or an
executable fix. SkillLens (arXiv:2605.23899) found this is the single
strongest text-level predictor of skill utility — generic-advice skills
*read* well but underperform (see rubric §SkillLens Utility Check).

**Before:**
```markdown
Resolve the contract before coding. Make sure formulas are handled correctly.
```

**After:**
```markdown
Host engines do not evaluate formula strings written into cells — the value
reads back as literal text. Precompute static values in code and write the
result; only write `=FORMULA(...)` strings when the target app will reopen
the file.
```

Each converted claim should name: the failure mechanism (what breaks and
why), the remedy (what to do instead, executable as written), and — where
the operation is risky — the blacklisted action ("do NOT ...").

### Pattern 10.2: Add Decision Trees

**Problem:** Skill lists options but doesn't help choose between them.

**Before:**
```markdown
Available options: A, B, or C.
```

**After:**
```markdown
Choose based on context:
- **A** when latency < 100ms is required (adds 200MB memory overhead)
- **B** for batch processing (10x throughput, but 2s cold start)
- **C** as default — balanced performance, simplest to maintain
```

---

## Meta-Patterns (Cross-Dimensional)

### The Simplification Pass

After several additive improvements, run a dedicated simplification iteration:
1. Read the entire skill fresh
2. For each paragraph, ask: "Would the skill be worse without this?"
3. Delete anything that fails the test
4. Re-score — simplicity should improve, nothing else should drop

### The Trigger Audit

1. List all trigger phrases from the description
2. For each, trace to the corresponding body section
3. Any trigger without a body section? → Add coverage or remove the trigger
4. Any body section without a trigger? → Add a trigger phrase for it

### The Reference Rebalance

1. Count lines in SKILL.md body
2. If > 500: identify sections that are reference material vs. procedural
3. Move reference material to `references/`
4. Add pointer in SKILL.md (keep all references one level deep)
5. Re-score progressive disclosure
