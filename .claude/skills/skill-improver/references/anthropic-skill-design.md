# Skill Design Guide — Anthropic Practices & Agent Skills Standard

Sources: Thariq Shihipar (Anthropic), March 2026; official Claude Code docs
(code.claude.com); Anthropic engineering blog; Agent Skills specification
(agentskills.io). See `references/sources.md` for all URLs.

## Table of Contents
- [The Agent Skills Open Standard](#the-agent-skills-open-standard)
- [Core Insight](#core-insight)
- [Complete Frontmatter Reference](#complete-frontmatter-reference) — base fields, CC extensions, substitutions, dynamic context, extended thinking
- [Invocation Control](#invocation-control)
- [Description Field Constraints](#description-field-constraints)
- [Skill Content Lifecycle](#skill-content-lifecycle) — single-message load, compaction (5K/25K budget), debugging
- [Skill Tool and Permissions](#skill-tool-and-permissions)
- [Skill Taxonomy (9 Categories)](#skill-taxonomy-9-categories)
- [Writing Effective Skills](#writing-effective-skills) — gotchas, progressive disclosure, freedom levels, railroading, description for the model, setup, memory, scripts, on-demand hooks
- [Distributing Skills](#distributing-skills)
- [Composing Skills](#composing-skills)
- [Measuring Skills](#measuring-skills)
- [Version Notes & Settings](#version-notes--settings) — changelog table, key settings, Task→Agent rename
- [Related Tools](#related-tools)

## The Agent Skills Open Standard

Claude Code skills follow the Agent Skills open standard (agentskills.io), created
and maintained by Anthropic. The same SKILL.md format works across Claude Code,
VS Code Copilot, Gemini CLI, Codex CLI, and other adopters. Claude Code extends the
base standard with additional frontmatter fields for invocation control, subagent
execution, and dynamic context injection.

A `skills-ref validate ./my-skill` CLI tool validates skills against the spec.

## Core Insight

A skill is a **folder**, not just a markdown file. The entire file system is a form
of context engineering and progressive disclosure. Tell Claude what files are in the
skill and it will read them at appropriate times.

## Complete Frontmatter Reference

### Base Standard Fields (agentskills.io)

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | Yes (recommended) | Max 64 chars, lowercase alphanumeric + hyphens. Must match directory name. Must NOT start/end with a hyphen, contain consecutive hyphens (`--`), contain XML tags, or use the reserved words `anthropic` or `claude`. |
| `description` | Recommended | Spec hard max 1024 chars, non-empty, cannot contain XML tags. Claude Code truncates combined `description` + `when_to_use` at **1,536 chars** in the skill listing (raised from 250 in v2.1.105, 2026-04-13). Front-load key trigger phrases. |
| `when_to_use` | No | Additional trigger context appended to `description` in the skill listing. Counts toward the 1,536-char combined cap. Use for trigger phrases and example requests that don't belong in the core description. |
| `license` | No | License name or reference to bundled file |
| `compatibility` | No | Max 500 chars. Environment requirements (product, packages, network) |
| `metadata` | No | Arbitrary key-value mapping for custom properties |
| `allowed-tools` | No | Space-delimited list or YAML list of pre-approved tools |

### Claude Code Extension Fields

| Field | Description |
|-------|-------------|
| `effort` | Override model effort level: `low`, `medium`, `high`, `xhigh`, or `max`. Available levels depend on the model (`xhigh` is Opus 4.7+, added v2.1.111; `max` originally Opus 4.6). Inherits from session if omitted. |
| `paths` | Glob patterns (comma-separated string or YAML list) limiting when skill activates based on files being worked on. |
| `context` | Set to `fork` to run in an isolated subagent context. Only for task-oriented skills with explicit instructions. |
| `agent` | Subagent type when `context: fork` is set. Built-in: `Explore`, `Plan`, `general-purpose`. Or custom from `.claude/agents/`. Defaults to `general-purpose` if omitted. |
| `model` | Override model: `opus`, `sonnet`, `haiku`, or full model ID. |
| `hooks` | Hooks scoped to skill lifecycle. See hooks docs for format. |
| `shell` | `bash` (default) or `powershell` for `` !`command` `` and ```!``` blocks. `powershell` requires `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`. |
| `argument-hint` | Hint shown during autocomplete, e.g. `[issue-number]`. |
| `disable-model-invocation` | `true` = only user can invoke via `/name`. Removes description from Claude's context entirely. |
| `user-invocable` | `false` = hidden from `/` menu. Only Claude can invoke. Description stays in Claude's context. |

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking. If absent, args appended as `ARGUMENTS: <value>`. |
| `$ARGUMENTS[N]` / `$N` | Access specific argument by 0-based index. |
| `${CLAUDE_SKILL_DIR}` | Path to the skill's own directory. Use for portable script references. |
| `${CLAUDE_SESSION_ID}` | Current session ID for logging or session-specific files. |

### Dynamic Context Injection

The `` !`command` `` syntax runs shell commands **before** the skill content is sent
to Claude. The output replaces the placeholder. Claude sees the result, not the
command. Example:

```yaml
---
name: pr-summary
context: fork
agent: Explore
---
PR diff: !`gh pr diff`
Changed files: !`gh pr diff --name-only`
Summarize this pull request.
```

### Extended Thinking

Include the word `ultrathink` anywhere in skill content to enable extended thinking
(thinking mode) when the skill is active.

## Invocation Control

| Frontmatter | User can invoke | Claude can invoke | Context loading |
|-------------|----------------|-------------------|-----------------|
| (default) | Yes | Yes | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes | No | Description NOT in context |
| `user-invocable: false` | No | Yes | Description always in context |

## Description Field Constraints

**Critical for trigger precision:**
- Agent Skills open-standard spec hard max: **1024 chars** (agentskills.io)
- Claude Code listing truncation: **1,536 chars** for combined `description` + `when_to_use` (raised from 250 in v2.1.105, 2026-04-13). Older installs still use 250 — verify target environment.
- The per-entry budget fits inside a dynamic total budget that scales at **1% of the context window** (fallback: 8,000 chars). Descriptions get shortened further if many skills are installed.
- Override the total budget with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var
- Always write in **third person** — consistent POV avoids discovery problems
- Front-load the key use case within the first 1,536 chars (or 250 if targeting older Claude Code versions)
- Include both what the skill does AND when to use it
- Split into `description` (what + core triggers) and `when_to_use` (extra trigger phrases, example requests). They concatenate in the listing.

## Skill Content Lifecycle

Once invoked, the rendered `SKILL.md` content enters the conversation as **a single
message that stays for the rest of the session**. Claude Code does not re-read the
skill file on later turns.

**Implication for writing skills:** Write guidance that should apply throughout a
task as *standing instructions*, not one-time steps. Instructions framed as "first
do X, then Y" work in the first turn but have no force later. Instructions framed as
"always prefer X over Y" or "when encountering Z, do W" remain effective.

**Compaction behavior:** When auto-compaction summarizes the conversation, Claude
Code re-attaches only the most recent invocation of each skill after the summary,
keeping the first **5,000 tokens per skill** with a combined budget of **25,000
tokens across all skills**. The budget fills from most-recently-invoked backward, so
skills invoked earlier in a long session can be **dropped entirely** after compaction.

**Debugging "skill stopped working":** If a skill seems to stop influencing behavior
after the first response, the content is usually still present — Claude is just
choosing other tools or approaches. Fixes:
- Strengthen the skill's `description` and instructions so Claude prefers it
- Rewrite one-time steps as standing instructions
- Use [hooks](https://code.claude.com/docs/en/hooks) to enforce behavior deterministically
- For large skills or long sessions with many skills: re-invoke after compaction

## Skill Tool and Permissions

Starting in Claude Code v2.1.105+, the model invokes skills via a `Skill` tool.
Deny rules support glob patterns: `Skill(deploy *)`, `Skill(commit)`. Adding `Skill`
to deny rules disables all skill invocations by the model. Built-in commands
(`/compact`, `/init`, `/review`, `/security-review`) are not invokable through the
Skill tool from the model side in older versions but became model-invokable in
v2.1.108 (2026-04-14).

## Skill Taxonomy (9 Categories)

### 1. Library & API Reference
How to correctly use a library, CLI, or SDK. Include reference code snippets and
gotchas. Works for both internal and external libraries that Claude struggles with.

### 2. Product Verification
How to test/verify that code works. Pair with external tools (Playwright, tmux, etc.).
**Worth investing a full week making verification skills excellent.** Techniques:
- Record video of output for review
- Enforce programmatic assertions on state at each step
- Include scripts for driving the verification

### 3. Data Fetching & Analysis
Connect to data/monitoring stacks. Include libraries to fetch data with credentials,
specific dashboard IDs, query patterns. Store helper functions Claude can compose.

### 4. Business Process & Team Automation
Automate repetitive workflows into one command. Save previous results in log files
so the model stays consistent and reflects on previous executions.

### 5. Code Scaffolding & Templates
Generate framework boilerplate. Combine with composable scripts. Especially useful
when scaffolding has natural language requirements beyond pure code templates.

### 6. Code Quality & Review
Enforce code quality. Can include deterministic scripts for maximum robustness.
Run automatically via hooks or GitHub Actions.

### 7. CI/CD & Deployment
Fetch, push, deploy. May reference other skills to collect data.

### 8. Runbooks
Take a symptom (Slack thread, alert, error) → multi-tool investigation → structured
report. Map symptoms → tools → query patterns.

### 9. Infrastructure Operations
Routine maintenance and operational procedures with guardrails for destructive actions.

## Writing Effective Skills

### Don't State the Obvious
Focus on information that pushes Claude out of its normal way of thinking.
Claude already knows standard patterns — document what's DIFFERENT.

### Build a Gotchas Section
Highest-signal content in any skill. Build up from real failure points over time.
Update the skill whenever Claude hits a new edge case.

### Use Progressive Disclosure
- `references/` — detailed docs, API signatures, function specs
- `scripts/` — helper scripts Claude can execute or compose
- `examples/` — reference implementations, templates
- `assets/` — templates for output files, config scaffolds
Tell Claude what files exist and when to use them.

**Keep SKILL.md under 500 lines.** Move detailed reference material to separate
files. Keep file references **one level deep** from SKILL.md — Claude may only
partially read files referenced from other referenced files.

For reference files over 100 lines, include a table of contents at the top so
Claude can see the full scope even when previewing with partial reads.

### Match Freedom to Fragility
- **High freedom** (text instructions): multiple approaches valid, context-dependent
- **Medium freedom** (pseudocode/parameterized scripts): preferred pattern exists
- **Low freedom** (specific scripts, exact commands): fragile operations, consistency critical

### Avoid Railroading
Give Claude information it needs but flexibility to adapt. Don't be overly
prescriptive in instructions — skills are reusable across situations.

### The Description Field Is for the Model
Not a summary — a description of **when to trigger**. Claude scans all descriptions
at session start to decide "is there a skill for this request?" Front-load keywords
within the first 1,536 chars (v2.1.105+; 250 on older Claude Code). Even within that
cap, the dynamic budget can shrink descriptions further if many skills are installed,
so the earlier a keyword appears, the more robust the triggering.

### Think Through Setup
Skills needing user context (Slack channel, API key) should store setup in a
`config.json` in the skill directory. If not configured, prompt the user.

### Memory & Storing Data
Skills can store data within them (log files, JSON, SQLite). Use
`${CLAUDE_PLUGIN_DATA}` for stable storage that survives skill upgrades.
Example: standup-post keeps standups.log for history.

### Store Scripts & Generate Code
Give Claude helper functions and libraries so it spends turns on composition,
not reconstructing boilerplate. Claude generates scripts on the fly composing
the provided functions. Use `${CLAUDE_SKILL_DIR}` in SKILL.md to reference
bundled scripts portably regardless of working directory.

### On-Demand Hooks
Skills can register hooks that activate only when invoked and last for the session.
Use for opinionated hooks that shouldn't run all the time:
- `/careful` — blocks destructive commands via PreToolUse
- `/freeze` — blocks edits outside a specific directory

Hooks can also be embedded directly in skill frontmatter via the `hooks` field.

## Distributing Skills

Three approaches:
1. **Check into repo** (`.claude/skills/`) — works for smaller teams, few repos
2. **Plugin marketplace** — scales better, lets teams choose what to install
3. **Managed settings** — deploy organization-wide for enterprise

Every checked-in skill adds to model context. At scale, use a marketplace to
let users opt in. Skills from `--add-dir` directories load automatically with
live change detection.

Nested `.claude/skills/` directories in subdirectories are auto-discovered,
supporting monorepo setups where packages have their own skills.

## Composing Skills

Reference other skills by name. Claude will invoke them if installed. No native
dependency management — just name references. Skills with `context: fork` can
specify an `agent` type to run in specialized subagent contexts.

## Measuring Skills

Use a PreToolUse hook to log skill usage. Track popularity and undertriggering
to find skills that need better descriptions.

## Version Notes & Settings

Relevant Claude Code changes that affect skill authoring (chronological):

| Version | Date | Change |
|---------|------|--------|
| v2.1.63 | 2026-03 | Task tool renamed to `Agent`. `Task(...)` kept as alias, but new `allowed-tools` rules should use `Agent(...)`. |
| v2.1.91 | 2026-04-02 | Plugin `bin/` auto-added to Bash `PATH` while plugin is enabled — Claude invokes executables there as bare commands. Also introduced `disableSkillShellExecution` setting. |
| v2.1.94 | 2026-04-?? | Plugin skills can declare `"skills": ["./"]` and are invoked by the skill's frontmatter `name` (stable across install methods). |
| v2.1.105 | 2026-04-13 | Description listing cap raised 250→**1,536 chars** for combined `description` + `when_to_use`. Startup warning when descriptions are truncated. `PreCompact` hooks can block compaction with exit code 2 or `{"decision":"block"}`. Plugin `monitors` manifest key auto-arms background monitors. |
| v2.1.108 | 2026-04-14 | Built-in commands `/init`, `/review`, `/security-review` now discoverable and invokable through the Skill tool by the model. |
| v2.1.110 | 2026-04-15 | Fixed skills with `disable-model-invocation: true` failing when invoked via `/<skill>` mid-message. `PreToolUse` hook `additionalContext` no longer dropped when the tool call fails. `PermissionRequest` hook `updatedInput` re-checked against `permissions.deny`. Hardened "Open in editor" against command injection. |
| v2.1.111 | 2026-04-16 | Added `xhigh` effort level for Opus 4.7 (between `high` and `max`). New bundled skills `/less-permission-prompts` and `/ultrareview`. Windows PowerShell tool rolling out (`CLAUDE_CODE_USE_POWERSHELL_TOOL`). `/skills` menu supports sorting by estimated token count (press `t`). Read-only bash commands with glob patterns (e.g. `ls *.ts`) no longer trigger permission prompts. |
| v2.1.113 | 2026-04-17 | Security: Bash deny rules now match commands wrapped in `env`/`sudo`/`watch`/`ionice`/`setsid`. `Bash(find:*)` allow rules no longer auto-approve `find -exec`/`-delete`. macOS `/private/{etc,var,tmp,home}` now treated as dangerous `Bash(rm:*)` targets. Fixed `Bash dangerouslyDisableSandbox` bypassing permission prompts. |
| v2.1.114 | 2026-04-18 | Fixed crash in the permission dialog when an agent teams teammate requested tool permission. |

### Key Settings

| Setting | Where | Purpose |
|---------|-------|---------|
| `disableSkillShellExecution` | `settings.json` | When `true`, blocks `` !`cmd` `` and ```!``` fenced blocks in non-bundled skills. Replacement text: `[shell command execution disabled by policy]`. Bundled and managed skills unaffected. Most useful in managed settings. |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | env var | Override the total budget for skill-description context (default: 1% of context window, 8,000-char fallback). |
| `CLAUDE_CODE_USE_POWERSHELL_TOOL` | env var | Required to be `1` for skills that set `shell: powershell`. |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | env var | Set to `1` to load `CLAUDE.md` from `--add-dir` directories. Skills from `--add-dir` load regardless. |

### Tool Rename: Task → Agent

When writing `allowed-tools` or deny rules for a skill, prefer `Agent(...)` over
`Task(...)`. The alias still works but `Agent` is the canonical name from v2.1.63 onward.

## Related Tools

The official **skill-creator** skill from Anthropic (`anthropics/skills` on GitHub)
provides a complementary workflow: create → evaluate → iterate, with quantitative
assertion-based benchmarks and description optimization loops. It has known bugs but
is actively maintained and useful alongside the skill-improver for new skill creation.
