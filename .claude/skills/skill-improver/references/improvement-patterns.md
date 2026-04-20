# Improvement Patterns Catalog

Common improvements organized by scoring dimension. Each pattern includes the problem, the fix, and a before/after example. Use this as a playbook when deciding what to improve in each iteration.

## Table of Contents
- [Dim 1 — Trigger Precision](#dimension-1-trigger-precision): 1.1 Add specific phrases · 1.2 Fix person · 1.3 Reduce false positives · 1.4 Front-load within listing cap · 1.5 Split description vs when-to-use
- [Dim 2 — Progressive Disclosure](#dimension-2-progressive-disclosure): 2.1 Extract to references · 2.2 Add missing pointers · 2.3 Flatten nested references
- [Dim 3 — Writing Style](#dimension-3-writing-style): 3.1 Second-person → imperative · 3.2 One-time steps → standing instructions · 3.3 Remove hedge language
- [Dim 4 — Actionability](#dimension-4-actionability): 4.1 Add concrete commands · 4.2 Add validation steps
- [Dim 5 — Completeness](#dimension-5-completeness): 5.1 Cover missing use cases · 5.2 Add error handling
- [Dim 6 — Simplicity](#dimension-6-simplicity): 6.1 Remove redundant sections · 6.2 Cut defensive boilerplate · 6.3 Collapse trivial examples
- [Dim 7 — Resource Quality](#dimension-7-resource-quality): 7.1 Make examples runnable · 7.2 Add script documentation
- [Dim 8 — Internal Consistency](#dimension-8-internal-consistency): 8.1 Fix dangling references · 8.2 Standardize terminology
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

### Pattern 6.1: Remove Redundant Sections

**Problem:** The same information appears in multiple places.

**Fix:** Keep it in one place. Prefer the more prominent location. Delete the duplicate.

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

---

## Dimension 8: Internal Consistency

### Pattern 8.1: Fix Dangling References

**Problem:** SKILL.md mentions a file that doesn't exist.

**Fix:** Either create the referenced file or remove the reference.

### Pattern 8.2: Standardize Terminology

**Problem:** The same concept has multiple names.

**Fix:** Pick one term and use it consistently. Find-and-replace across all files in the skill directory.

---

## Dimension 9: Domain Accuracy

### Pattern 9.1: Update Deprecated APIs

**Problem:** Instructions reference outdated tool versions or deprecated flags.

**Fix:** Verify commands against current documentation. Update to current syntax.

### Pattern 9.2: Fix Incorrect Defaults

**Problem:** Stated default values don't match actual tool behavior.

**Fix:** Test or verify defaults and correct them.

### Pattern 9.3: Add Missing Frontmatter Fields

**Problem:** Skill could benefit from frontmatter fields it doesn't use.

**Common opportunities:**
- Description stuffed with trigger phrases → split to `description` (what) + `when_to_use` (triggers)
- Skill scoped to file types but missing `paths:` → add `paths: ["*.py", "*.rs"]`
- Task skill with side effects but missing `disable-model-invocation: true`
- Background knowledge skill missing `user-invocable: false`
- Script-heavy skill missing `allowed-tools: Bash(python *)`
- Computationally light skill that could use `effort: low`
- Complex reasoning skill on Opus 4.6 that could use `effort: max`
- Skill that would benefit from isolation missing `context: fork` (pair with `agent: Explore` or `agent: Plan` for specialized subagent behavior)
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
