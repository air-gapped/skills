# Skill Design Guide — Anthropic Practices & Agent Skills Standard

URLs: `references/sources.md`.

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
- [Version Notes & Settings](#version-notes--settings) — current facts, key settings, Task→Agent rename
- [Related Tools](#related-tools)

## The Agent Skills Open Standard

Claude Code skills follow the Agent Skills open standard (agentskills.io). The same SKILL.md format works across Claude Code, VS Code Copilot, Gemini CLI, Codex CLI and others. Claude Code adds frontmatter fields for invocation control, subagent execution and dynamic context injection.

`skills-ref validate ./my-skill` validates a skill against the spec.

## Core Insight

A skill is a **folder**, not a markdown file. The file system is context engineering and progressive disclosure. Tell Claude what files the skill holds; it reads them when needed.

## Complete Frontmatter Reference

### Base Standard Fields (agentskills.io)

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | Yes (recommended) | Max 64 chars, lowercase alphanumeric + hyphens. Must match directory name. Must NOT start/end with a hyphen, contain `--`, contain XML tags, or use the reserved words `anthropic` or `claude`. |
| `description` | Recommended | Spec hard max 1024 chars, non-empty, no XML tags. Claude Code truncates combined `description` + `when_to_use` at **1,536 chars** in the skill listing (older installs: 250). Front-load key trigger phrases. |
| `when_to_use` | No | Extra trigger context appended to `description` in the listing. Counts toward the 1,536-char cap. Put trigger phrases and example requests here. |
| `license` | No | License name or reference to bundled file |
| `compatibility` | No | Max 500 chars. Environment requirements (product, packages, network) |
| `metadata` | No | Key-value mapping; keys AND values are strings, not arbitrary YAML |
| `allowed-tools` | No | Space-delimited or YAML list of pre-approved tools |

### Claude Code Extension Fields

| Field | Description |
|-------|-------------|
| `effort` | `low`, `medium`, `high`, `xhigh`, or `max`. `xhigh` on Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5, Opus 4.8/4.7, Sonnet 5; `max` on those plus Mythos Preview, Opus 4.6, Sonnet 4.6. **Fable 5.1, Opus 5, Opus 4.8, and Sonnet 5 default to `high`** — start at `xhigh` for coding and agentic work, `max` only where evals show headroom. Fable 5.1, Mythos 5.1 and Opus 5 accept a per-message effort change (beta) that keeps the prompt cache; on every other model a changed effort restarts the cache. On Opus 5, `xhigh`/`max` reject `thinking: disabled` with a 400. Inherits from session if omitted. |
| `paths` | Glob patterns (comma-separated string or YAML list) limiting activation to matching files being worked on. |
| `context` | `fork` runs in an isolated subagent context. Only for task-oriented skills with explicit instructions. |
| `agent` | Subagent type when `context: fork`. Built-in: `Explore`, `Plan`, `general-purpose`, or custom from `.claude/agents/`. Default `general-purpose`. |
| `background` | Only with `context: fork`. Default `true`: the fork runs in the background, result arrives later, under the **narrower background-subagent tool set**. `false` blocks the invoking turn and keeps the full tool set. |
| `arguments` | Named positional arguments for `$name` substitution. Space-separated string or YAML list, mapped to positions in order. |
| `model` | `opus`, `sonnet`, `haiku`, `fable`, or full model ID. An alias resolves to the current release of that family (`fable` → Fable 5.1, except in Claude-apps gateway sessions); record the full id where a measurement must be reproducible. |
| `hooks` | Hooks scoped to skill lifecycle. |
| `shell` | `bash` (default) or `powershell` for `` !`command` `` and ```!``` blocks. `powershell` requires `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`. |
| `argument-hint` | Autocomplete hint, e.g. `[issue-number]`. |
| `disable-model-invocation` | `true` = only the user can invoke via `/name`. Removes description from Claude's context. Also blocks preloading into subagents and blocks the skill running when a scheduled task fires with it as the prompt. |
| `user-invocable` | `false` = hidden from `/` menu; only Claude can invoke. Description stays in context. |
| `disallowed-tools` | Space-delimited or YAML list of tools removed while the skill is active. Inverse of `allowed-tools`. |

Frontmatter booleans also accept `yes`/`no`/`on`/`off`/`1`/`0`.

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments. If absent from the body, args are appended as `ARGUMENTS: <value>`. |
| `$ARGUMENTS[N]` / `$N` | Argument by 0-based index. |
| `${CLAUDE_SKILL_DIR}` | The skill's own directory. Use for portable script references. |
| `${CLAUDE_SESSION_ID}` | Current session ID. |

`\$` writes a literal `$` before a digit in command bodies (prevents `$1` substitution).

### Dynamic Context Injection

`` !`command` `` runs the shell command **before** the skill content is sent; output replaces the placeholder. Claude sees the result, not the command.

```markdown
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

The word `ultrathink` anywhere in skill content enables extended thinking while the skill is active.

## Invocation Control

| Frontmatter | User can invoke | Claude can invoke | Context loading |
|-------------|----------------|-------------------|-----------------|
| (default) | Yes | Yes | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes | No | Description NOT in context |
| `user-invocable: false` | No | Yes | Description always in context |

When Claude tries to invoke a `disable-model-invocation` skill it is refused and told to ask the user to run it, so it does not re-derive the workflow inline.

## Description Field Constraints

**Critical for trigger precision:**
- Spec hard max: **1024 chars**.
- Claude Code listing cap: **1,536 chars** for combined `description` + `when_to_use`; older installs use 250 — verify the target environment.
- The per-entry cap sits inside a dynamic total budget of **1% of the context window** (fallback 8,000 chars); descriptions shrink further when many skills are installed. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET`.
- Write in **third person**.
- Front-load the key use case within the first 1,536 chars (250 for older versions); the earlier a keyword appears, the more robust the triggering.
- State what the skill does AND when to use it.
- Split into `description` (what + core triggers) and `when_to_use` (extra trigger phrases, example requests); they concatenate in the listing.

## Skill Content Lifecycle

Once invoked, the rendered `SKILL.md` enters the conversation as **a single message that stays for the session**. Claude Code does not re-read the file on later turns.

**Writing consequence:** write guidance that applies throughout a task as *standing instructions* ("always prefer X over Y", "when encountering Z, do W"), not one-time steps ("first do X, then Y"), which have no force after the first turn.

**Compaction:** auto-compaction re-attaches only the most recent invocation of each skill, keeping the first **5,000 tokens per skill** within a combined **25,000-token** budget. The budget fills from most-recently-invoked backward; earlier-invoked skills can be **dropped entirely**. The post-compaction reminder does not re-run a skill's original arguments.

**Debugging "skill stopped working":** the content is usually still present; Claude is choosing other tools. Fixes:
- Strengthen the `description` and instructions so Claude prefers it
- Rewrite one-time steps as standing instructions
- Use [hooks](https://code.claude.com/docs/en/hooks) to enforce behavior deterministically
- For large skills or long sessions with many skills: re-invoke after compaction

## Skill Tool and Permissions

The model invokes skills via a `Skill` tool. Deny rules take globs: `Skill(deploy *)`, `Skill(commit)`. Denying `Skill` disables all model skill invocations. `/init`, `/review`, `/security-review` are model-invokable through the Skill tool.

## Skill Taxonomy (9 Categories)

### 1. Library & API Reference
How to use a library, CLI or SDK correctly. Include reference code snippets and gotchas.

### 2. Product Verification
How to test/verify that code works. Pair with external tools (Playwright, tmux). Techniques:
- Record video of output for review
- Enforce programmatic assertions on state at each step
- Include scripts that drive the verification

### 3. Data Fetching & Analysis
Connect to data/monitoring stacks. Include fetch libraries with credentials, dashboard IDs, query patterns, composable helper functions.

### 4. Business Process & Team Automation
Automate repetitive workflows into one command. Save previous results in log files so the model stays consistent across runs.

### 5. Code Scaffolding & Templates
Framework boilerplate, combined with composable scripts; useful when scaffolding has natural-language requirements beyond code templates.

### 6. Code Quality & Review
Enforce quality; include deterministic scripts. Run via hooks or GitHub Actions.

### 7. CI/CD & Deployment
Fetch, push, deploy. May reference other skills to collect data.

### 8. Runbooks
Symptom (Slack thread, alert, error) → multi-tool investigation → structured report. Map symptoms → tools → query patterns.

### 9. Infrastructure Operations
Routine maintenance and operational procedures with guardrails for destructive actions.

## Writing Effective Skills

### Don't State the Obvious
Document what pushes Claude out of its normal way of thinking; Claude already knows standard patterns.

### Build a Gotchas Section
Highest-signal content in any skill. Build it from real failure points; update it whenever Claude hits a new edge case.

### Use Progressive Disclosure
- `references/` — detailed docs, API signatures, function specs
- `scripts/` — helper scripts Claude can execute or compose
- `examples/` — reference implementations, templates
- `assets/` — templates for output files, config scaffolds
Tell Claude what files exist and when to use them.

**Keep SKILL.md under 500 lines.** Move reference material to separate files. Keep file references **one level deep** from SKILL.md — Claude may only partially read files referenced from other referenced files.

Reference files over 100 lines get a table of contents at the top.

### Match Freedom to Fragility
- **High freedom** (text instructions): multiple valid approaches, context-dependent
- **Medium freedom** (pseudocode/parameterized scripts): a preferred pattern exists
- **Low freedom** (specific scripts, exact commands): fragile operations, consistency critical

### Avoid Railroading
Give the information needed plus room to adapt; skills are reused across situations.

### The Description Field Is for the Model
Describe **when to trigger**, not a summary. Claude scans all descriptions at session start to decide "is there a skill for this request?". Front-load keywords (see Description Field Constraints).

### Think Through Setup
Skills needing user context (Slack channel, API key) store setup in a `config.json` in the skill directory; prompt the user if unconfigured.

### Memory & Storing Data
Skills can store data (log files, JSON, SQLite). Use `${CLAUDE_PLUGIN_DATA}` for storage that survives skill upgrades.

### Store Scripts & Generate Code
Give Claude helper functions and libraries so turns go to composition, not rebuilding boilerplate. Reference bundled scripts via `${CLAUDE_SKILL_DIR}`.

### On-Demand Hooks
Skills can register hooks that activate only when invoked and last for the session — for opinionated hooks that should not always run:
- `/careful` — blocks destructive commands via PreToolUse
- `/freeze` — blocks edits outside a specific directory

Hooks can also be embedded in skill frontmatter via `hooks`.

## Distributing Skills

1. **Check into repo** (`.claude/skills/`) — small teams, few repos
2. **Plugin marketplace** — scales; teams choose what to install
3. **Managed settings** — organization-wide

Every checked-in skill adds to model context; at scale use a marketplace. Skills from `--add-dir` directories load automatically with live change detection. Nested `.claude/skills/` directories are auto-discovered (monorepos); nested dirs give directory-qualified names (`apps/web:deploy`). Plugins in `.claude/skills` load without a marketplace; `claude plugin init <name>` scaffolds one. Custom commands are merged into skills (`.claude/commands/deploy.md` ≡ `.claude/skills/deploy/SKILL.md`).

## Composing Skills

Reference other skills by name; Claude invokes them if installed. No native dependency management. `context: fork` skills can set an `agent` type.

**Chaining:** a SKILL.md body cannot chain to `/verify` or `/code-review` — Claude no longer self-invokes them, and they are absent from the model's Skill-tool listing. Chain only to model-invocable skills (e.g. `/simplify`, a custom verification skill).

## Measuring Skills

Use a PreToolUse hook to log skill usage; track popularity and undertriggering to find skills needing better descriptions. `/skill-doctor` shows which loaded skills go unused and their context cost — a pruning signal, not a quality measurement.

## Version Notes & Settings

Current Claude Code facts that affect skill authoring and runs:

| Since | Fact |
|-------|------|
| v2.1.63 | Task tool renamed `Agent`; `Task(...)` still works as alias. |
| v2.1.91 | Plugin `bin/` auto-added to Bash `PATH` while the plugin is enabled. |
| v2.1.94 | Plugin skills can declare `"skills": ["./"]` and are invoked by frontmatter `name`. |
| v2.1.105 | Listing cap 1,536 chars. `PreCompact` hooks can block compaction (exit 2 or `{"decision":"block"}`). |
| v2.1.145 | Bundled skills `/run`, `/verify`, `/run-skill-generator` (launch and verify the real app). |
| v2.1.152 | `disallowed-tools` frontmatter; `/reload-skills` and `SessionStart` hook `reloadSkills: true` re-scan skill dirs without restart. |
| v2.1.205 | `/doctor` is a bundled skill, typable even with `disableBundledSkills` on. |
| v2.1.212 | `/fork` copies the conversation to a background session; the old in-session fork is `/subtask`. |
| v2.1.217 | Default **20** concurrent subagents (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); nested spawning off by default (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; nested depth 3 since v2.1.219). `--max-budget-usd` halts running background subagents. |
| v2.1.218 | `background` frontmatter field. |
| v2.1.219 | Opus 5 (`claude-opus-5`) is the default Opus; blind-validation pin is Opus 5 (see `blind-validation.md` §Model selection). Dynamic workflows default to a medium size guideline, settable via `workflowSizeGuideline`. |
| v2.1.221 | `claude-api` skill `prompt-audit` subcommand audits prompts and tool descriptions for "patterns written for older models" — same target as the model-version-compensation cap (§Boris Alignment Check); run it as a free hypothesis source before a compensation-cap iteration. `claude plugin validate` warns on names Claude Desktop would reject. |
| v2.1.224 | No per-session subagent spawn cap (the 200 cap was removed). Live bounds: the 20-concurrent cap and the workflow size guideline. |
| v2.1.228 | Skills synced from claude.ai cannot shadow local commands or MCP prompts; their bodies do not run `!` commands or expand `@` files locally. |
| v2.1.232 | `subagent_type: "fork"` inherits the full conversation and prompt cache; non-teammate agent spawns in interactive sessions run in the background by default. |
| v2.1.233 | `claude plugin validate` checks a bare `.claude/skills` directory and reports SKILL.md files whose frontmatter fails to parse — a cheap pre-check before the Dim 9 hard-fail rules. Todo/task tools (TaskCreate/Get/Update/List, TodoWrite) are unavailable on Opus 4.8, Sonnet 5, Fable 5, Mythos 5 and newer (`CLAUDE_CODE_ENABLE_TODO_TOOLS=1` restores them). |
| v2.1.239 | `.md` agents/skills/commands that start with a UTF-8 BOM are loaded (previously ignored). |
| v2.1.243 | `promptCacheTtl` / `subagentPromptCacheTtl` settings (`5m` or `1h`; env `CLAUDE_CODE_PROMPT_CACHE_TTL` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`). Subagents stay at 5 minutes unless the subagent bucket is set. |
| v2.1.246 | A subagent that stops at `maxTurns` returns its output marked **partial** with a `SendMessage` continuation hint. |
| v2.1.247 | `/claude-api cost-optimize` profiles API spend and walks the cost levers one measured change at a time. |
| v2.1.248 | Agent frontmatter `experimental.cacheTtl` (`"5m"`/`"1h"`) sets per-agent cache TTL when no subagent TTL setting exists; `1h` is ignored while a subscription is on usage credits. |
| v2.1.251 | `CLAUDE_CODE_SUBAGENT_MODEL` is a **default**: an agent definition's `model:` and an explicit per-spawn model override it. |
| v2.1.257 | Fable 5.1 (`claude-fable-5-1`) is the default Fable: 1M context, $10/$50 per Mtok, **$0.25/Mtok cache reads**, default effort `high`, all five effort levels; Opus 5 is the default for most workloads. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` applies one model to **every** subagent, ignoring agent-definition and per-spawn overrides (see `blind-validation.md` §Model selection). |
| v2.1.269 | `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` (1–256) raises the Workflow tool's per-run concurrent-agent limit; the 20-subagent cap is unchanged. |
| v2.1.271 | Medium dynamic-workflow size guideline is 10 agents (`workflowSizeGuideline`); Pro plans default to **small**. |

### Key Settings

| Setting | Where | Purpose |
|---------|-------|---------|
| `disableSkillShellExecution` | `settings.json` | `true` blocks `` !`cmd` `` and ```!``` blocks in non-bundled skills (replacement text `[shell command execution disabled by policy]`). Bundled and managed skills unaffected. |
| `disableBundledSkills` | `settings.json` / `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` | Hide bundled skills, workflows and built-in slash commands from the model. |
| `CLAUDE_CODE_SAFE_MODE` | env var / `--safe-mode` | Start with ALL customizations disabled (CLAUDE.md, plugins, skills, hooks, MCP) to isolate whether a skill causes a problem. |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | env var | Override the total skill-description budget (default 1% of context window, 8,000-char fallback). |
| `CLAUDE_CODE_USE_POWERSHELL_TOOL` | env var | Must be `1` for skills with `shell: powershell`. |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | env var | `1` loads `CLAUDE.md` from `--add-dir` directories. Skills from `--add-dir` load regardless. |

### Tool Rename: Task → Agent

In `allowed-tools` and deny rules write `Agent(...)`, not `Task(...)`.

## Related Tools

Anthropic's **skill-creator** skill (`anthropics/skills`) offers create → evaluate → iterate with assertion-based benchmarks and description optimization loops; useful alongside skill-improver for new skills.
