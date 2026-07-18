# Sources — Skill Design & Agent Skills Ecosystem

URLs for keeping the skill-improver's references current. Freshen Mode reads
this file, probes each row, and stamps `Last verified` (and `Pinned` where
applicable). Standalone Evaluation uses the oldest `Last verified` to cap
Dim 9 (see `references/quality-rubric.md` §Dim 9).

## Table of Contents
- [Convention](#convention)
- [Most recent freshen pass](#most-recent-freshen-pass-2026-07-18) (and prior passes)
- [Official Documentation](#official-documentation)
- [GitHub Repositories](#github-repositories)
- [Blog Posts & Articles](#blog-posts--articles)
- [Search Queries for Future Research](#search-queries-for-future-research)

## Convention

Each row below has these columns: `Source`, `URL`, `What it contains`,
`Last verified` (YYYY-MM-DD), `Pinned` (version or git ref, optional).
Mark rows you want Freshen Mode to skip with `<!-- ignore-freshen -->`
at the end of the row.

## Most recent freshen pass: 2026-07-18

### Notable changes since the previous pass (2026-06-09 → 2026-07-18)

- **Loops became the platform story.** The features are older than the discourse: `/loop` shipped in **v2.1.71** (recurring interval, bundled prompt-based skill), `/goal` in **v2.1.139** (evaluator-checked completion condition, live turns/tokens overlay), `/schedule` is in research preview (cloud-run proactive loops). What changed recently: Anthropic's official **"Loop engineering: Getting started with loops"** blog post (2026-06-30, Delba de Oliveira & Michael Segner) canonized the taxonomy — turn-based / goal-based / time-based / proactive loops, each defined by trigger + stop condition — and **Boris Cherny's "Steps of AI Adoption"** (2026-07-16, X + LinkedIn, 251K+ views; "I don't prompt Claude anymore … my job is to write loops", @Scale talk) made loop engineering the adoption narrative. Blog best practices map 1:1 onto this skill's existing design: deterministic success criteria (the scalar rubric metric), explicit turn caps (10-iteration cap), skills encoding verification (blind validation), match interval to change frequency (freshen cadence). SKILL.md §Batch Mode gained a native-loops note; version table backfilled v2.1.71/139.
- **Claude Code v2.1.170 → v2.1.214** (changelog fetched raw via `gh api`). Skill-relevant: **v2.1.205** `/doctor` becomes a bundled skill, custom commands fully merged into skills, nested `.claude/skills/` directory-qualified names; **v2.1.212** session loop-guards — 200-subagent and 200-WebSearch caps (batch/blind fan-outs count against them), `/fork` background sessions; **v2.1.214** EndConversation tool, permission hardening. No frontmatter/Skill-tool behavior drift affecting this skill's guidance.
- **Docs all healthy, re-stamped 2026-07-18**: skills docs (new: bundled-skills section listing `/loop`; `/run`+`/verify`+`/run-skill-generator` v2.1.145), best-practices (all enforced practices confirmed — third-person, 500-line cap, one-level refs, 100-line TOC; "build evaluations first" section validates trigger mode's empirical approach), agentskills.io spec (optional `license`/`compatibility`/`metadata`/`allowed-tools` fields — already in `anthropic-skill-design.md`), hooks, subagents, engineering blog (adds note: standard open-sourced 2025-12-18).
- **Repos**: anthropics/skills @ fa0fa64b (2026-07-17, docx/pptx/xlsx update) — **skill-creator unchanged since 2026-04-20**, Trigger Mode mirroring stays accurate; agentskills/agentskills @ 38a2ff82 (2026-07-10, pulumi-neo example — no spec drift).
- **X/Twitter rows unfetchable (HTTP 402)** — historical post rows marked `<!-- ignore-freshen -->` (content already quoted in the skill; corroborated via syndication where needed). Rubric §Dim 9 staleness cap now explicitly excludes ignore-freshen rows.

### Previous freshen pass: 2026-06-09

### Notable changes since the previous pass (2026-05-28 → 2026-06-09)

- **Claude Fable 5 shipped 2026-06-09** (Claude Code v2.1.170), model ID `claude-fable-5` — the first generally-available **Mythos-class** model, a tier *above* Opus. Verified via the Claude Code changelog (`gh api repos/anthropics/claude-code/contents/CHANGELOG.md`) and the official news page. Skill-relevant effects:
  - **Blind-validation model pin** updated: most capable model is now Fable 5 (`model: "fable"` in `Agent` calls). API $10/$50 per Mtok; included on Pro/Max/Team/seat-Enterprise Jun 9–22 2026, usage credits afterward.
  - **Effort:** `xhigh` is supported on Fable 5 and Opus 4.8/4.7 (per the `/effort` dialog). Fast mode remains Opus-only (4.6/4.7/4.8).
  - **Dynamic workflows** run on Fable 5 (verified in-session: the `Workflow` tool is exposed on `claude-fable-5`).
- **Claude Code v2.1.155 → v2.1.170:** Most skill-relevant intermediate changes, all folded into `anthropic-skill-design.md` (version table + Key Settings):
  - **v2.1.160:** dynamic-workflow trigger keyword renamed `workflow` → `ultracode` (the word "workflow" alone no longer triggers a run). SKILL.md opt-in language updated.
  - **v2.1.157:** plugins in `.claude/skills` auto-load, no marketplace; `claude plugin init`.
  - **v2.1.163:** skills `\$` escape for a literal `$` before a digit in command bodies.
  - **v2.1.169:** `--safe-mode`/`CLAUDE_CODE_SAFE_MODE` (start with all customizations disabled); `disableBundledSkills` setting.
- **agentskills spec repo:** docs commit `5d4c1fda` (2026-05-20) clarifies the `name` field charset as `a-z, 0-9` + hyphens — matches what `quality-rubric.md` already enforces; no drift.
- **anthropics/skills repo:** latest commit `c30d329f` (2026-06-07, claude-api skill update). skill-creator path unchanged since 2026-04-20 — Trigger Mode mirroring stays accurate.
- **Not re-probed this pass** (kept 2026-05-01 stamps, all within 90 days → no Dim 9 cap): skills docs, best-practices, agentskills.io spec page, hooks/subagents docs, blog, x.com posts.

### Previous freshen pass: 2026-05-28

### Notable changes since the previous pass (2026-05-01 → 2026-05-28)

- **Claude Opus 4.8 shipped 2026-05-28** (Claude Code v2.1.154), model ID `claude-opus-4-8`. Verified via the Claude Code changelog (`gh api repos/anthropics/claude-code/contents/CHANGELOG.md`) and the official news page. Skill-relevant effects:
  - **Effort:** Opus 4.8 defaults to `high`; `xhigh` for hard tasks, `max` for the hardest. The news page surfaces three operator-facing tiers (High / Extra=`xhigh` / Max). On coding tasks, high uses ≈ Opus 4.7's default token count with better performance.
  - **Dynamic workflows** (research preview, Enterprise/Team/Max): "ask Claude to create a workflow and it orchestrates work across tens to hundreds of agents in the background" — the official news page cites "codebase-scale migrations across hundreds of thousands of lines from kickoff to merge." `/workflows` views runs. **Directly relevant to skill-improver's blind-validation, batch, and trigger loops** — these are multi-agent orchestration that the Workflow tool is purpose-built for. Reflected in SKILL.md (Blind Validation §"Parallel scoring" and Batch Mode) and `quality-rubric.md`.
  - **Lean system prompt** now default for all models except Haiku/Sonnet/Opus ≤4.7.
  - **Multiple-choice prompts reserved** for decisions Claude genuinely can't make itself (reinforces the loop's "never stop unless asked" rule).
  - Fast mode on 4.8: 2× standard rate for 2.5× speed.
- **Claude Code v2.1.126 → v2.1.154:** Most skill-relevant intermediate change is **v2.1.152**: `disallowed-tools` frontmatter field for skills/slash-commands; `/reload-skills` command; `SessionStart` hook `reloadSkills: true`; new `MessageDisplay` hook event. All folded into `anthropic-skill-design.md` (frontmatter table + version table).
- **Not re-probed this pass** (kept 2026-05-01 stamps, all within 90 days → no Dim 9 cap): skills docs, best-practices, agentskills spec, anthropics/skills repo, hooks/subagents docs, blog, x.com posts.

### Previous freshen pass: 2026-05-01

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
| Claude Code skills docs | https://code.claude.com/docs/en/skills | Complete skill authoring guide, frontmatter reference, bundled skills (incl. `/loop`), advanced patterns | 2026-07-18 | — |
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Official best practices: conciseness, freedom levels, progressive disclosure, evaluation-first testing, anti-patterns | 2026-07-18 | — |
| Agent Skills specification | https://agentskills.io/specification | Cross-platform SKILL.md spec: required/optional fields (incl. license/compatibility/metadata/allowed-tools), validation rules | 2026-07-18 | — |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | Version history with skill-related feature additions | 2026-07-18 | v2.1.214 |
| Claude Code hooks docs | https://code.claude.com/docs/en/hooks | Hook integration including hooks-in-skills frontmatter | 2026-07-18 | — |
| Claude Code subagents docs | https://code.claude.com/docs/en/sub-agents | Subagent types, skill preloading, context: fork, agent teams, background agents | 2026-07-18 | — |
| Loop engineering blog post | https://claude.com/blog/getting-started-with-loops | Official loops guide (2026-06-30): /loop, /goal, /schedule taxonomy by trigger + stop condition; best practices (deterministic criteria, turn caps, verify via skills) | 2026-07-18 | — |

## GitHub Repositories

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| anthropics/skills | https://github.com/anthropics/skills | Official skill examples, spec, skill-creator, document skills | 2026-07-18 | main @ fa0fa64b (2026-07-17) |
| Official skill-creator | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Anthropic's skill for creating/evaluating skills (has known bugs, actively maintained) | 2026-07-18 | main |
| skill-creator: improve_description.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/improve_description.py | Description-improvement prompt — authoritative source for "be a little pushy", overfitting guard, ≤200 word target. Trigger Mode mirrors this approach. | 2026-07-18 | main (unchanged since 2026-04-20) |
| skill-creator: run_eval.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_eval.py | Trigger-detection mechanism: synthetic slash-command + `claude -p` + stream-json `tool_use` parsing. Source for `scripts/probe-trigger.py`. | 2026-07-18 | main (unchanged since 2026-04-20) |
| skill-creator: run_loop.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_loop.py | 60/40 train/test split, 3 runs/query, blind test scores, best-by-test selection — Trigger Mode loop semantics. | 2026-07-18 | main (unchanged since 2026-04-20) |
| Agent Skills spec repo | https://github.com/agentskills/agentskills | Spec source, `skills-ref validate` CLI tool | 2026-07-18 | main @ 38a2ff82 (2026-07-10) |
| Claude Code releases | https://github.com/anthropics/claude-code/releases | Release notes with detailed changelogs | 2026-07-18 | v2.1.214 |

## Blog Posts & Articles

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Anthropic engineering blog | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Agent Skills announcement (2025-10-16), architecture, security considerations; standard open-sourced 2025-12-18 | 2026-07-18 | — |
| Anthropic news — Opus 4.8 | https://www.anthropic.com/news/claude-opus-4-8 | Opus 4.8 launch (2026-05-28): `claude-opus-4-8`, effort tiers, dynamic workflows, fast mode pricing | 2026-05-28 | — | <!-- ignore-freshen (historical launch page) -->
| Anthropic news — Fable 5 | https://www.anthropic.com/news/claude-fable-5-mythos-5 | Fable 5 launch (2026-06-09): `claude-fable-5`, Mythos-class tier above Opus, pricing ($10/$50 per Mtok), availability windows | 2026-06-09 | — | <!-- ignore-freshen (historical launch page) -->
| Thariq Shihipar — Skills lessons | https://x.com/trq212/status/2033949937936085378 | Lessons from building Claude Code: How We Use Skills (March 17, 2026) | 2026-05-01 | — | <!-- ignore-freshen (X unfetchable, content quoted in skill) -->
| Thariq — Seeing like an Agent | https://x.com/trq212/status/2027463795355095314 | Agent design philosophy | 2026-05-01 | — | <!-- ignore-freshen (X unfetchable, content quoted in skill) -->
| Boris Cherny on Lenny's podcast | https://x.com/Mnilax/status/2050321700802408552 | Creator of Claude Code interviewed 2026; "don't box the model in", bitter lesson applied to skills, "give it a tool, not context up front", build for the model 6 months out, plan-mode default. Source for Boris Alignment Check (rubric §), Scaffolding Decay Probes (freshen §4b), Minimalism Test (trigger §), and Philosophy Mode (SKILL.md §). | 2026-05-03 | — | <!-- ignore-freshen (X unfetchable, content quoted in skill) -->
| Boris Cherny — Steps of AI Adoption | https://x.com/bcherny/status/2077929379661844559 | Loop-era adoption ladder (2026-07-16): Gated (0) → Assisted (~1) → Parallel (~10) → Supervised autonomy (~100) → AI-native (1,000+ agents); "I don't prompt Claude anymore … my job is to write loops"; Anthropic self-reports step 3. Verified 2026-07-18 via LinkedIn mirror + press syndication (X direct fetch 402). | 2026-07-18 | — | <!-- ignore-freshen (X unfetchable, verified via syndication) -->
| Armin Ronacher — The Coming Loop | https://lucumr.pocoo.org/2026/6/23/the-coming-loop/ | Independent practitioner take (2026-06-23) on the loop shift — third-party corroboration of the loop-engineering discourse | 2026-07-18 | — |

## Search Queries for Future Research

When checking for updates, these queries have been productive:

```
"claude code" skills SKILL.md frontmatter 2026
claude code changelog new features skills
agentskills.io specification updates
Thariq Shihipar claude code skills
site:code.claude.com/docs skills
site:platform.claude.com agent-skills
claude code /loop /goal loop engineering
Boris Cherny loops adoption
```
