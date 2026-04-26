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

## Most recent freshen pass: 2026-04-19

### Notable changes since the previous pass (2026-04-15 → 2026-04-19)

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
| Claude Code skills docs | https://code.claude.com/docs/en/skills | Complete skill authoring guide, frontmatter reference, advanced patterns, troubleshooting | 2026-04-19 | — |
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Official best practices: conciseness, freedom levels, progressive disclosure, testing, anti-patterns | 2026-04-19 | — |
| Agent Skills specification | https://agentskills.io/specification | Cross-platform SKILL.md spec: required/optional fields, validation rules, directory structure | 2026-04-19 | — |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | Version history with skill-related feature additions | 2026-04-19 | v2.1.114 |
| Claude Code hooks docs | https://code.claude.com/docs/en/hooks | Hook integration including hooks-in-skills frontmatter | 2026-04-15 | — |
| Claude Code subagents docs | https://code.claude.com/docs/en/sub-agents | Subagent types, skill preloading, context: fork details | 2026-04-15 | — |

## GitHub Repositories

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| anthropics/skills | https://github.com/anthropics/skills | Official skill examples, spec, skill-creator, document skills | 2026-04-19 | main |
| Official skill-creator | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Anthropic's skill for creating/evaluating skills (has known bugs, actively maintained) | 2026-04-19 | main |
| skill-creator: improve_description.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/improve_description.py | Description-improvement prompt — authoritative source for "be a little pushy", overfitting guard, ≤200 word target. Trigger Mode mirrors this approach. | 2026-04-25 | main |
| skill-creator: run_eval.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_eval.py | Trigger-detection mechanism: synthetic slash-command + `claude -p` + stream-json `tool_use` parsing. Source for `scripts/probe-trigger.py`. | 2026-04-25 | main |
| skill-creator: run_loop.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_loop.py | 60/40 train/test split, 3 runs/query, blind test scores, best-by-test selection — Trigger Mode loop semantics. | 2026-04-25 | main |
| Agent Skills spec repo | https://github.com/agentskills/agentskills | Spec source, `skills-ref validate` CLI tool | 2026-04-19 | main |
| Claude Code releases | https://github.com/anthropics/claude-code/releases | Release notes with detailed changelogs | 2026-04-19 | v2.1.114 |

## Blog Posts & Articles

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Anthropic engineering blog | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Agent Skills announcement (2025-10-16), architecture, security considerations | 2026-04-19 | — |
| Thariq Shihipar — Skills lessons | https://x.com/trq212/status/2033949937936085378 | Lessons from building Claude Code: How We Use Skills (March 17, 2026) | 2026-04-15 | — |
| Thariq — Seeing like an Agent | https://x.com/trq212/status/2027463795355095314 | Agent design philosophy | 2026-04-15 | — |

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
