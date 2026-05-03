# Sources — Skill Design & Agent Skills Ecosystem

URLs for keeping the skill-improver's references current. Freshen Mode reads
this file, probes each row, and stamps `Last verified` (and `Pinned` where
applicable). Standalone Evaluation uses the oldest `Last verified` to cap
Dim 9 (see `references/quality-rubric.md` §Dim 9).

## Convention

Each row below has these columns: `Source`, `URL`, `What it contains`,
`Last verified` (YYYY-MM-DD), `Pinned` (version or git ref, optional).
Mark rows you want Freshen Mode to skip with `<!-- ignore-freshen -->`
at the end of the row.

## Most recent freshen pass: 2026-05-01

### Notable changes since the previous pass (2026-04-19 → 2026-05-01)

- **Claude Code v2.1.114 → v2.1.126:** Twelve minor releases. None alter skill-improver's body content (the skill describes methodology, not version-specific APIs). Most skill-relevant:
  - **v2.1.116:** Agent frontmatter `hooks:` now fire when running as a main-thread agent via `--agent`.
  - **v2.1.117 (2026-04-22):** Agent frontmatter `mcpServers` loaded for main-thread agent sessions via `--agent`. `CLAUDE_CODE_FORK_SUBAGENT=1` enables forked subagents on external builds. Default effort for Pro/Max subscribers on Opus 4.6 / Sonnet 4.6 raised from `medium` → `high`. OpenTelemetry: `cost.usage`/`token.usage`/`api_request`/`api_error` now include an `effort` attribute. Opus 4.7 sessions now correctly compute `/context` against 1M-token native window (was incorrectly 200K).
  - **v2.1.118:** Hooks can now invoke MCP tools directly via `type: "mcp_tool"`.
  - **v2.1.119 (2026-04-23):** `--print` mode honors agent's `tools:`/`disallowedTools:` frontmatter. `--agent <name>` honors `permissionMode` for built-in agents. `PostToolUse`/`PostToolUseFailure` hook inputs now include `duration_ms`. Slash command picker wraps long descriptions instead of truncating.
  - **v2.1.121 (2026-04-28):** Type-to-filter search box added to `/skills`. `PostToolUse` hooks can replace tool output for all tools via `hookSpecificOutput.updatedToolOutput`. `--dangerously-skip-permissions` no longer prompts for writes to `.claude/skills/`, `.claude/agents/`, `.claude/commands/`.
  - **v2.1.126 (2026-05-01):** New `claude_code.skill_activated` OpenTelemetry event with `invocation_trigger` attribute (`"user-slash"`, `"claude-proactive"`, or `"nested-skill"`). Fixed deferred tools (WebSearch, WebFetch, etc.) not being available to skills with `context: fork` and other subagents on their first turn.
- **anthropics/skills repo:** Latest commit 2026-04-23 (`Add Managed Agents memory stores page to claude-api skill #1014`). skill-creator scripts (`improve_description.py`, `run_eval.py`, `run_loop.py`) and `SKILL.md` unchanged since 2026-04-25 — Trigger Mode mirroring stays accurate.
- **Anthropic engineering blog post** (Agent Skills announcement): URL still 200 OK, original publication 2025-10-16, content unchanged.
- **Platform best-practices page**: still authoritative — confirmed core guidance (third-person descriptions, ≤500-line SKILL.md, one-level-deep references, ≥100-line files need TOC) matches what skill-improver enforces.

### Previous freshen pass: 2026-04-19

- **Claude Code v2.1.109 → v2.1.114:** Six minor releases. Most skill-relevant:
  - **v2.1.111 (2026-04-16):** New `xhigh` effort level for Opus 4.7 (between
    `high` and `max`). New bundled skills `/less-permission-prompts` and
    `/ultrareview`. Windows PowerShell tool rolling out. `/skills` menu
    sort-by-token-count. Read-only bash commands with glob no longer prompt.
  - **v2.1.110 (2026-04-15):** Fixed skills with `disable-model-invocation:
    true` failing when invoked via `/<skill>` mid-message. `PreToolUse`
    `additionalContext` preserved on failure. `PermissionRequest`
    `updatedInput` re-checked against deny rules.
  - **v2.1.113 (2026-04-17):** Security tightening — Bash deny rules now
    match `env`/`sudo`/`watch`/`ionice`/`setsid` wrappers. `Bash(find:*)`
    allow rules no longer auto-approve `find -exec`/`-delete`.
- **Blog URL moved (301):** Anthropic blog post "Equipping agents for the real
  world with Agent Skills" moved from `claude.com/blog/...` to
  `www.anthropic.com/engineering/...`. Original publication still 2025-10-16.
- **Platform best-practices page** adds validation rules for `name` and
  `description` fields: no XML tags; `name` cannot start/end with hyphen, no
  consecutive hyphens, no reserved words `anthropic` or `claude`.

### Previous freshen pass: 2026-04-15

- **Claude Code v2.1.105 (2026-04-13):** Skill description listing cap raised from
  **250 → 1,536 chars** for combined `description` + `when_to_use`. `PreCompact`
  hooks can now block compaction. Plugin `monitors` manifest key added.
- **v2.1.108 (2026-04-14):** Built-in `/init`, `/review`, `/security-review` are
  now Skill-tool invokable by the model.
- **v2.1.91 (2026-04-02):** Plugin `bin/` auto-added to PATH; `disableSkillShellExecution`
  setting added.
- **New frontmatter fields documented** in code.claude.com/docs/en/skills:
  `when_to_use`, `shell: bash|powershell`, `effort: max` (Opus 4.6 only).
- **New "Skill content lifecycle" section** in the official skills doc — SKILL.md
  loads once, not re-read; 5K/25K token compaction budget for re-attached skills.
- **Task tool renamed to Agent** (v2.1.63). `Task(...)` still aliased.

## Official Documentation

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Claude Code skills docs | https://code.claude.com/docs/en/skills | Complete skill authoring guide, frontmatter reference, advanced patterns, troubleshooting | 2026-05-01 | — |
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Official best practices: conciseness, freedom levels, progressive disclosure, testing, anti-patterns | 2026-05-01 | — |
| Agent Skills specification | https://agentskills.io/specification | Cross-platform SKILL.md spec: required/optional fields, validation rules, directory structure | 2026-05-01 | — |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | Version history with skill-related feature additions | 2026-05-01 | v2.1.126 |
| Claude Code hooks docs | https://code.claude.com/docs/en/hooks | Hook integration including hooks-in-skills frontmatter | 2026-05-01 | — |
| Claude Code subagents docs | https://code.claude.com/docs/en/sub-agents | Subagent types, skill preloading, context: fork details | 2026-05-01 | — |

## GitHub Repositories

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| anthropics/skills | https://github.com/anthropics/skills | Official skill examples, spec, skill-creator, document skills | 2026-05-01 | main @ 5128e186 (2026-04-23) |
| Official skill-creator | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Anthropic's skill for creating/evaluating skills (has known bugs, actively maintained) | 2026-05-01 | main |
| skill-creator: improve_description.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/improve_description.py | Description-improvement prompt — authoritative source for "be a little pushy", overfitting guard, ≤200 word target. Trigger Mode mirrors this approach. | 2026-05-01 | main (unchanged since 2026-04-25) |
| skill-creator: run_eval.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_eval.py | Trigger-detection mechanism: synthetic slash-command + `claude -p` + stream-json `tool_use` parsing. Source for `scripts/probe-trigger.py`. | 2026-05-01 | main (unchanged since 2026-04-25) |
| skill-creator: run_loop.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_loop.py | 60/40 train/test split, 3 runs/query, blind test scores, best-by-test selection — Trigger Mode loop semantics. | 2026-05-01 | main (unchanged since 2026-04-25) |
| Agent Skills spec repo | https://github.com/agentskills/agentskills | Spec source, `skills-ref validate` CLI tool | 2026-05-01 | main @ 2d3e01f5 (2026-04-22) |
| Claude Code releases | https://github.com/anthropics/claude-code/releases | Release notes with detailed changelogs | 2026-05-01 | v2.1.126 |

## Blog Posts & Articles

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Anthropic engineering blog | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Agent Skills announcement (2025-10-16), architecture, security considerations | 2026-05-01 | — |
| Thariq Shihipar — Skills lessons | https://x.com/trq212/status/2033949937936085378 | Lessons from building Claude Code: How We Use Skills (March 17, 2026) | 2026-05-01 | — |
| Thariq — Seeing like an Agent | https://x.com/trq212/status/2027463795355095314 | Agent design philosophy | 2026-05-01 | — |
| Boris Cherny on Lenny's podcast | https://x.com/Mnilax/status/2050321700802408552 | Creator of Claude Code interviewed 2026; "don't box the model in", bitter lesson applied to skills, "give it a tool, not context up front", build for the model 6 months out, plan-mode default. Source for Boris Alignment Check (rubric §), Scaffolding Decay Probes (freshen §4b), Minimalism Test (trigger §), and Philosophy Mode (SKILL.md §). | 2026-05-03 | — |

## Search Queries for Future Research

When checking for updates, these queries have been productive:

```
"claude code" skills SKILL.md frontmatter 2026
claude code changelog new features skills
agentskills.io specification updates
Thariq Shihipar claude code skills
site:code.claude.com/docs skills
site:platform.claude.com agent-skills
```
