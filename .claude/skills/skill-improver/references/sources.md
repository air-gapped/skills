# Sources — Skill Design & Agent Skills Ecosystem

URLs for keeping the skill-improver's references current. Freshen Mode reads
this file, probes each row, and stamps `Last verified` (and `Pinned` where
applicable). Standalone Evaluation uses the oldest `Last verified` to cap
Dim 9 (see `references/quality-rubric.md` §Dim 9).

## Table of Contents
- [Convention](#convention)
- [Most recent freshen pass](#most-recent-freshen-pass-2026-07-24) (and prior passes)
- [Official Documentation](#official-documentation)
- [GitHub Repositories](#github-repositories)
- [Blog Posts & Articles](#blog-posts--articles)
- [Search Queries for Future Research](#search-queries-for-future-research)

## Convention

Each row below has these columns: `Source`, `URL`, `What it contains`,
`Last verified` (YYYY-MM-DD), `Pinned` (version or git ref, optional).
Mark rows you want Freshen Mode to skip with `<!-- ignore-freshen -->`
at the end of the row.

## Most recent freshen pass: 2026-07-24

### Notable changes since the previous pass (2026-07-18 → 2026-07-24)

- **Claude Opus 5 shipped 2026-07-24** (Claude Code v2.1.219), `claude-opus-5` — new *default* Opus, 1M context, $5/$25 per Mtok, knowledge cutoff May 2026. **Blind-validation pin moved Fable 5 → Opus 5** after the two available signals were compared directly:
  - *Vendor label:* platform models-overview still reads "Claude Fable 5 is Anthropic's most capable widely released model… for the highest available capability, use Claude Fable 5", and the launch page's prose ("comes close to the frontier intelligence of Claude Fable 5 at half the price") reads as second place.
  - *Measurements:* the launch benchmark table has Opus 5 ahead of Fable 5 on GDPval-AA knowledge work (1861 vs 1747), BrowseComp agentic search (90.8 vs 87.4), HLE-with-tools (64.7 vs 63.9), Frontier-Bench agentic terminal coding (43.3 vs 33.7), OSWorld (70.6 vs 66.1) and AutomationBench (26.0 vs 17.4); Fable 5 leads only tool-free HLE (56.5 vs 56.3), DeepSWE (69.7 vs 68.8), FrontierCode (53.5 vs 53.4) and legal, with Mythos 5 taking health.
  - *Tiebreaker for this skill's use:* Opus 5's May-2026 cutoff (vs Fable 5's Jan 2026) is worth real accuracy on Dim 9, where a scorer with a stale prior flags freshened claims as wrong.
  - **Lesson recorded in `blind-validation.md`:** pick the pin from benchmark rows matching the scoring task; a "most capable" label, a release date, or default-model status is not evidence. The first pass of this freshen got it wrong by trusting the label.
- **Claude Code v2.1.214 → v2.1.219** (v2.1.219 published today). Skill-relevant: **v2.1.218** adds the frontmatter field **`background`** (`context: fork` skills now background by default, `background: false` to block the turn and keep the full tool set) and accepts `yes/no/on/off/1/0` for frontmatter booleans; **v2.1.217** caps concurrent subagents at 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) and bounds `paths` brace expansion; **v2.1.219** sets a default dynamic-workflow size guideline of <15 agents (`workflowSizeGuideline`) and raises nested-subagent depth to 3; **v2.1.215/218** stop Claude self-invoking `/verify`, `/code-review`, `/deep-research`. All folded into `anthropic-skill-design.md` (frontmatter table + version rows); the three fan-out caps are now stated in SKILL.md §Batch Mode.
- **Official skills doc gained an "Evaluate and iterate on a skill" section**, and **skill-creator is installed as a plugin** (`/plugin install skill-creator@claude-plugins-official`, source `anthropics/claude-plugins-official/plugins/skill-creator`) rather than copied from `anthropics/skills`. Its documented loop — `evals/evals.json` assertions, per-case subagent isolation, `grading.json` / `benchmark.json`, blind A/B version comparison, description tuning — measures **output quality**, the axis this skill's rubric and trigger metrics do not cover. New sources.md rows for both the agentskills.io methodology page and the plugin repo; SKILL.md §Standalone Evaluation now points there for output-quality work.
- **Repos**: anthropics/skills @ 1f630fdf (2026-07-22, claude-api Managed Agents update) — **skill-creator path unchanged since 2026-04-20** (verified by commit history on `skills/skill-creator`), so Trigger Mode mirroring of `run_eval.py` / `run_loop.py` / `improve_description.py` stays accurate; the plugin copy last synced 2026-04-23. agentskills/agentskills @ 38a2ff82 (2026-07-10) — no spec drift.
- **Not re-probed this pass** (2026-07-18 stamps, 6 days old, far inside the 90-day cap): hooks and subagents docs, engineering blog, loops blog, SkillOpt/SkillLens papers, X/Twitter rows.

### Second pass, same day — Claude Code team blog pair

Triggered by two posts, not by a staleness stamp. Recency filter applied: only
the changelog was re-probed; doc/spec/paper rows left unprobed **and**
unrestamped.

- **Boris Alignment Check now has a first-party written source.** Thariq
  Shihipar, *"The new rules of context engineering for Claude 5 generation
  models"* (2026-07-24) — 80% of Claude Code's system prompt removed for Opus 5 /
  Fable 5 with no eval loss; names all three capped patterns as superseded
  practice. The check was previously sourced only to an X post about a podcast,
  marked `ignore-freshen` because X is unfetchable. Rubric §Boris Alignment Check
  re-attributed; the X row stays as origin but is no longer the citation.
- **Delba de Oliveira, *"Building verification loops in Claude Code with
  skills"*** (2026-07-22) — supplied the criterion side of the new scaffolding
  discriminator. Its invocation-mode taxonomy (standalone / embedded / chained /
  on-every-PR) is **not yet reflected anywhere in this skill** — Dim 1 and all of
  Trigger Mode assume every skill is standalone and model-invoked. Not filed
  under Open (no mutation was attempted, so it fails the backlog admission bar);
  recorded here as the strongest candidate for the next `improve` pass.
- **`/doctor` positioned as first-party skill rightsizing.** Bundled skill since
  v2.1.205 (already in the version table) but never referenced in SKILL.md.
  §Standalone Evaluation now names it as a pre-pass and states the boundary: no
  metric, no keep/discard, no blind check.
- **`/verify` chaining — resolved, no conflict existed.** Changelog v2.1.215
  (2026-07-19): *"Claude no longer runs the `/verify` and `/code-review` skills
  **on its own**."* Confirmed mechanically by the **sibling test**: `/verify`
  shipped in v2.1.145 with `/run` and `/run-skill-generator`; in a live v2.1.219
  session `run` and `simplify` are in the Skill-tool listing and `verify` is not.
  The apparent conflict with the verification-loops post was a misread on my
  part — its chaining code example uses `/simplify` → a *custom*
  `/verify-no-public-api-changes`, never the bundled pair; the "/code-review,
  /simplify, /verify" passage describes a **human** habit, which is the post's
  setup for "habit becomes contract". Rule recorded in the v2.1.215 row: chain to
  custom verification skills, never to `/verify` or `/code-review`.
  **Method note:** this was first classified `unverifiable` after reading two
  documents and finding them in tension, with no probe run. That is *unverified*,
  and the two are not the same — F3's `unverifiable` class requires probes that
  came back ambiguous. The sibling test cost one command.
- **Watch:** `quality-rubric.md` crossed 500 lines (501) with the discriminator
  section. Reference files have no hard cap — only SKILL.md does — but this is
  the largest reference after `trigger-patterns.md` and `improvement-patterns.md`.

### Previous freshen pass: 2026-07-18

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
| Claude Code skills docs | https://code.claude.com/docs/en/skills | Complete skill authoring guide, frontmatter reference (incl. `background`, `arguments`), bundled skills, "Evaluate and iterate on a skill" section | 2026-07-24 | — |
| Evaluating skill output quality | https://agentskills.io/skill-creation/evaluating-skills | Output-quality eval methodology: `evals/evals.json` schema, assertions, clean-context runs, `grading.json` / `benchmark.json`, blind A/B comparison, iterate-until-flat loop | 2026-07-24 | — |
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Official best practices: conciseness, freedom levels, progressive disclosure, evaluation-first testing, anti-patterns | 2026-07-18 | — |
| Agent Skills specification | https://agentskills.io/specification | Cross-platform SKILL.md spec: required/optional fields (incl. license/compatibility/metadata/allowed-tools), validation rules | 2026-07-18 | — |
| Claude models overview | https://platform.claude.com/docs/en/about-claude/models/overview | Per-model IDs, pricing, context windows, knowledge cutoffs, and the vendor capability positioning — the label side of the blind-validation model pin | 2026-07-24 | — |
| Effort levels | https://platform.claude.com/docs/en/build-with-claude/effort | Which models support `xhigh`/`max`, per-model defaults and recommended levels; ultracode = `xhigh` + standing multiagent-workflow permission | 2026-07-24 | — |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | Version history with skill-related feature additions | 2026-07-24 | v2.1.219 |
| Claude Code hooks docs | https://code.claude.com/docs/en/hooks | Hook integration including hooks-in-skills frontmatter | 2026-07-18 | — |
| Claude Code subagents docs | https://code.claude.com/docs/en/sub-agents | Subagent types, skill preloading, context: fork, agent teams, background agents | 2026-07-18 | — |
| Claude Code prompt-caching docs | https://code.claude.com/docs/en/prompt-caching | Prefix layers (system prompt / project context / conversation); model and effort are cache keys; system prompt embeds cwd, platform, shell, OS, auto-memory paths — so each worktree is its own prefix; **subagents use the 5-min TTL even on a subscription** (1-hour is main-conversation only); fork inherits the parent prefix; workflow fan-out hold-and-release; grounds Pattern 7.3 | 2026-08-19 | — |
| Claude Code workflows docs | https://code.claude.com/docs/en/workflows | Workflow agent() cache mechanics (same prefix rules as Agent tool), fan-out cache warm-up | 2026-08-16 | — |
| Optimizing for cost and intelligence | https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence | Measured cost levers: caching 2.5-3.7x; prompt audit — Opus 4.8-era prompts cost 36% more per ticket on Opus 5 at equal accuracy, audit returns 14% and +5pts accuracy (14% again on Sonnet 4.6→5); "verify twice" removal cut cost by a third; retired thinking setting / contradictory rules / hand-rolled scratchpad each restored 7-11 accuracy points; page states the patterns apply to skills. Cited in quality-rubric.md §Boris Alignment Check. Also: effort curves flat on knowledge work, re-run-failures policy | 2026-08-19 | — |
| Model pricing | https://platform.claude.com/docs/en/about-claude/pricing | Per-MTok list rates for every live model plus the cache multipliers (read 0.1x, 5m write 1.25x, 1h write 2x), `inference_geo: us` 1.1x, fast-mode premium, web search $10/1k. **Backs `scripts/model-rates.json`** — when this row is re-probed, update that file's `verified` stamp in the same pass | 2026-08-19 | — |
| Loop engineering blog post | https://claude.com/blog/getting-started-with-loops | Official loops guide (2026-06-30): /loop, /goal, /schedule taxonomy by trigger + stop condition; best practices (deterministic criteria, turn caps, verify via skills) | 2026-07-18 | — |
| Context engineering for Claude 5 models | https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models | Thariq Shihipar, 2026-07-24. **First-party written source for the Boris Alignment Check** — 80% of Claude Code's system prompt removed with no eval loss; six then/now shifts (rules→judgment, examples→interface design, upfront→progressive disclosure, repetition→simple tool descriptions, CLAUDE.md memory→auto-memory, simple specs→rich references); `/doctor` rightsizes skills + CLAUDE.md; rubrics-as-references + verifier agents | 2026-07-24 | — |
| Building verification loops with skills | https://claude.com/blog/building-verification-loops-in-claude-code-with-skills | Delba de Oliveira, 2026-07-22. Invocation-mode taxonomy (standalone / embedded / chained / on-every-PR) with outgrow signals and skip conditions; encode manual checks as skills; "a deterministic rule no generic linter will catch but a project-specific one will" — the criterion side of the scaffolding discriminator; plugin-managed skills off-limits for embedding (overwritten on update) | 2026-07-24 | — |

## GitHub Repositories

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| anthropics/skills | https://github.com/anthropics/skills | Official skill examples, spec, skill-creator, document skills | 2026-07-24 | main @ 1f630fdf (2026-07-22) |
| Official skill-creator | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Anthropic's skill for creating/evaluating skills (has known bugs, actively maintained) | 2026-07-24 | main |
| skill-creator plugin (install path) | https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator | The copy the official docs tell users to install (`/plugin install skill-creator@claude-plugins-official`); last synced from anthropics/skills 2026-04-23 | 2026-07-24 | main @ 2a40fd2e |
| skill-creator: improve_description.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/improve_description.py | Description-improvement prompt — authoritative source for "be a little pushy", overfitting guard, ≤200 word target. Trigger Mode mirrors this approach. | 2026-07-24 | main (unchanged since 2026-04-20) |
| skill-creator: run_eval.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_eval.py | Trigger-detection mechanism: synthetic slash-command + `claude -p` + stream-json `tool_use` parsing. Source for `scripts/probe-trigger.py`. | 2026-07-24 | main (unchanged since 2026-04-20) |
| skill-creator: run_loop.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_loop.py | 60/40 train/test split, 3 runs/query, blind test scores, best-by-test selection — Trigger Mode loop semantics. | 2026-07-24 | main (unchanged since 2026-04-20) |
| Agent Skills spec repo | https://github.com/agentskills/agentskills | Spec source, `skills-ref validate` CLI tool | 2026-07-24 | main @ 38a2ff82 (2026-07-10) |
| Claude Code releases | https://github.com/anthropics/claude-code/releases | Release notes with detailed changelogs | 2026-07-24 | v2.1.219 |

## Blog Posts & Articles

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Anthropic engineering blog | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Agent Skills announcement (2025-10-16), architecture, security considerations; standard open-sourced 2025-12-18 | 2026-07-18 | — |
| Anthropic news — Opus 4.8 | https://www.anthropic.com/news/claude-opus-4-8 | Opus 4.8 launch (2026-05-28): `claude-opus-4-8`, effort tiers, dynamic workflows, fast mode pricing | 2026-05-28 | — | <!-- ignore-freshen (historical launch page) -->
| Anthropic news — Opus 5 | https://www.anthropic.com/news/claude-opus-5 | Opus 5 launch (2026-07-24): `claude-opus-5`, $5/$25 per Mtok, near-frontier at half Fable 5's price but below it; new default Opus | 2026-07-24 | — | <!-- ignore-freshen (historical launch page) -->
| Anthropic news — Fable 5 | https://www.anthropic.com/news/claude-fable-5-mythos-5 | Fable 5 launch (2026-06-09): `claude-fable-5`, Mythos-class tier above Opus, pricing ($10/$50 per Mtok), availability windows | 2026-06-09 | — | <!-- ignore-freshen (historical launch page) -->
| Thariq Shihipar — Skills lessons | https://x.com/trq212/status/2033949937936085378 | Lessons from building Claude Code: How We Use Skills (March 17, 2026) | 2026-05-01 | — | <!-- ignore-freshen (X unfetchable, content quoted in skill) -->
| Thariq — Seeing like an Agent | https://x.com/trq212/status/2027463795355095314 | Agent design philosophy | 2026-05-01 | — | <!-- ignore-freshen (X unfetchable, content quoted in skill) -->
| Boris Cherny on Lenny's podcast | https://x.com/Mnilax/status/2050321700802408552 | Creator of Claude Code interviewed 2026; "don't box the model in", bitter lesson applied to skills, "give it a tool, not context up front", build for the model 6 months out, plan-mode default. Source for Boris Alignment Check (rubric §), Scaffolding Decay Probes (freshen §4b), Minimalism Test (trigger §), and Philosophy Mode (SKILL.md §). | 2026-05-03 | — | <!-- ignore-freshen (X unfetchable, content quoted in skill) -->
| Boris Cherny — Steps of AI Adoption | https://x.com/bcherny/status/2077929379661844559 | Loop-era adoption ladder (2026-07-16): Gated (0) → Assisted (~1) → Parallel (~10) → Supervised autonomy (~100) → AI-native (1,000+ agents); "I don't prompt Claude anymore … my job is to write loops"; Anthropic self-reports step 3. Verified 2026-07-18 via LinkedIn mirror + press syndication (X direct fetch 402). | 2026-07-18 | — | <!-- ignore-freshen (X unfetchable, verified via syndication) -->
| Armin Ronacher — The Coming Loop | https://lucumr.pocoo.org/2026/6/23/the-coming-loop/ | Independent practitioner take (2026-06-23) on the loop shift — third-party corroboration of the loop-engineering discourse | 2026-07-18 | — |
| SkillOpt paper | https://arxiv.org/abs/2605.23904 | Microsoft text-space optimizer for agent skills (v2, 2026-05-25): bounded add/delete/replace edits, held-out validation gate, textual learning rate, rejected-edit buffer, slow/meta update. Source of this skill's rejected-edit buffer + noise floor (adopted 2026-07-18). Read from local PDF. | 2026-07-18 | v2 |
| SkillLens paper | https://arxiv.org/abs/2605.23899 | Companion lifecycle study (2026-05-22): 25% negative transfer; LLM plausibility judging = 46.4% accuracy, inverts to 15.8% on high-gap pairs; format non-significant; validated 3-dim rubric (failure mechanism encoding, actionable specificity, high-risk blacklist) lifts judging to 73.8%. Source of rubric §SkillLens Utility Check + Pattern 10.1b. Read from local PDF. | 2026-07-18 | v1 |
| Bennett — Weakest Not Shortest | https://arxiv.org/abs/2301.12987 | v4 2024: weakest (largest-extension) hypothesis maximises P(generalisation) under uniform task prior; MDL neither necessary nor sufficient; weak ≠ short. Source of the weakness criterion (SKILL.md Phase 2) and the failure-class rule in trigger Pattern T1. Read from local PDF. | 2026-08-09 | v4 |

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
