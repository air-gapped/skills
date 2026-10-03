# Sources — Skill Design & Agent Skills Ecosystem

Freshened: 2026-09-22 — every row probed; all 41 URLs 200. One version attribution corrected — `/skill-doctor` landed in v2.1.261, not v2.1.271 — and SkillEvaluator now has a real v0.3.0 release shipping what this file still listed as unreleased.

**Freshened: 2026-09-15** — every row probed. All ~45 URLs resolve; every arXiv citation re-opened and its title, version pin and attributed finding confirmed on the page (SkillOpt still v2, SkillLens still v1, Bennett still v4 — no newer versions); all four X posts re-fetched unexpanded and their quoted text re-confirmed, including the two the file deliberately records as *misattributed* and *unverified-but-not-refuted*, both of which still hold.

**Claude Code moved 15 releases (v2.1.257 → v2.1.272) and three changes land on this skill**, now folded into `SKILL.md`: **v2.1.271 lowered the medium workflow size guideline from 15 to 10 agents** and made **small** the default on Pro plans — the figure this file had published as `<15` since v2.1.219; **v2.1.269** added `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` (1–256), a per-run Workflow limit distinct from the unchanged 20-subagent cap; and **v2.1.271** added `/skill-doctor`. Re-checked as unaffected across that range: the 20-subagent cap, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, `prompt-audit`, `disable-model-invocation`.

One URL moved: the models overview dropped its `about-claude/` path segment. The `anthropics/skills` pin is 9 days stale (HEAD `34040c9c`), but `skills/skill-creator/**` is untouched since 2026-04-20, so the Trigger Mode mirroring claim is unaffected. SkillEvaluator re-checked: still no `v0.2.0` **tag** — the changelog has a 0.2.0 heading that was never released, which is the correction this file already records.

Prior pass: 2026-09-01.

URLs for keeping the skill-improver's references current. Freshen Mode probes
every row and writes the single header stamp above; the per-row `Last verified`
column is legacy and no longer authoritative. Standalone Evaluation reads the
stamp to cap Dim 9 (see `references/quality-rubric.md` §Dim 9).

## Table of Contents
- [Convention](#convention)
- [Most recent freshen pass](#most-recent-freshen-pass-2026-09-01) (and prior passes)
- [Official Documentation](#official-documentation)
- [GitHub Repositories](#github-repositories)
- [Blog Posts & Articles](#blog-posts--articles)
- [Search Queries for Future Research](#search-queries-for-future-research)
- [Evidence behind the rules](#evidence-behind-the-rules)

## Convention

Each row below has these columns: `Source`, `URL`, `What it contains`,
`Last verified` (YYYY-MM-DD), `Pinned` (version or git ref, optional).
Mark rows you want Freshen Mode to skip with `<!-- ignore-freshen -->`
at the end of the row.

## Most recent freshen pass: 2026-09-01

All 29 rows probed (three parallel `web-searcher` agents: docs/blogs, GitHub,
papers/X), and every drifted claim re-read on its primary page from the main
context before it entered a file. Trigger: the Fable 5.1 release.

### Notable changes since the previous pass (2026-08-20 → 2026-09-01)

- **Claude Fable 5.1 and Mythos 5.1 shipped 2026-09-01** (Claude Code
  v2.1.257), model id `claude-fable-5-1` — now the default Fable model: 1M
  context, 128K max output, $10/$50 per Mtok, reliable knowledge cutoff June
  2026, default effort `high`. The models-overview page moves Fable 5 to the
  legacy list and now reads *"start with Claude Opus 5 for most workloads. Use
  Claude Fable 5.1 for demanding reasoning and long-horizon agentic work, or
  when your evals on Claude Opus 5 at higher effort still fall short."* The
  launch page (new row) attributes a ~25% lower cost than Fable 5 on typical
  workloads, up to ~45% on highly agentic ones, to cache-read pricing alone,
  and its benchmark table has Fable 5.1 ahead of Opus 5 on every listed row.
  **The blind-scorer pin is unaffected** — it is cost-chosen among models that
  tied on ranking (`blind-validation.md` §Model selection), Sonnet 5 is
  unchanged, and no Sonnet 5.1 / Opus 5.1 / Haiku 5 shipped.
- **Cache reads on Fable 5.1 / Mythos 5.1 cost 0.025× base input ($0.25/MTok);
  every other model stays at 0.1×** — the first per-model exception to the
  multiplier table. `scripts/model-rates.json` gained a per-model `cache_read`
  override, honoured by `run-cost.py` and by `probe-trigger.py` (which had 0.1
  hardcoded); `verified` restamped 2026-09-01. Same page: **Sonnet 5's $2/$10
  is now the standard price** — the increase to $3/$15 scheduled for
  2026-09-01 was cancelled.
- **Effort availability moved.** `xhigh` adds Fable 5.1 / Mythos 5.1; `max`
  now lists Mythos Preview, Opus 4.6 and Sonnet 4.6 alongside — and **Opus 4.5
  is gone from both lists**. Fable 5.1, Mythos 5.1 and Opus 5 accept a
  per-message effort change (beta) that keeps the prompt cache.
  `anthropic-skill-design.md` effort row and improvement-patterns Pattern 9.3
  corrected.
- **Claude Code v2.1.237 → v2.1.257** (superseded — see the header for v2.1.257 → v2.1.272), seven new version-table rows. Beyond
  the release itself: **v2.1.251** demotes `CLAUDE_CODE_SUBAGENT_MODEL` to a
  default that an agent definition's `model:` outranks, and **v2.1.257** adds
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, which overrides agent definitions — the
  one setting that silently moves the blind-scorer pin, now stated in
  `blind-validation.md`; **v2.1.243 / v2.1.248** make the subagent cache TTL
  configurable (`subagentPromptCacheTtl`, agent frontmatter
  `experimental.cacheTtl`), so Pattern 7.3's "5-minute TTL even on a
  subscription" became "by default"; **v2.1.246** subagents stopping at
  `maxTurns` return output marked partial; **v2.1.239** BOM-prefixed skill
  files were silently ignored; **v2.1.247** `/claude-api cost-optimize`;
  **v2.1.248** Workflow prompt cut to ~1k tokens with a bundled
  `workflow-authoring` skill. Nothing in the range touches the 20-concurrent
  cap, nesting depth, `workflowSizeGuideline`, `plugin validate`,
  `disable-model-invocation` or `prompt-audit`.
- **The `fable` alias now names two releases.** Claude Code resolves `fable`
  to Fable 5.1, while Claude-apps gateway sessions keep resolving it to Fable 5
  (v2.1.257). Floor-mode results are keyed by that alias and
  `knowledge-floor.py` recorded no resolved model id, so a `fable` column
  could not be attributed to a release — a Dim 7 defect handed to the improve
  pass that followed.
- **A pinned SkillEvaluator release never existed.** The row pinned "v0.2.0
  (2026-08-18)"; GitHub carries only the `v0.1.0` tag and release
  (2026-08-05). The number came from `pyproject.toml` / `CHANGELOG.md`, which
  now read **0.2.1 (2026-08-24)** with further fixes under Unreleased: license
  detection no longer trusts a frontmatter `license` over a conflicting
  LICENSE file (a blocking conflict no longer reports `allowed`), PII scanning
  catches emails in Markdown headings, and `tools/` is scanned like
  `scripts/`. Tier 1 check names, Tier 2 classes and bands, and the profiles
  are unchanged. The host running this repo's pre-commit gate has **0.2.0**
  installed, so that tightening is not yet what the gate enforces.
- **anthropics/skills @ 0a64e398 → `53048666`** (2026-09-01, claude-api skill
  updated for Fable 5.1 / Mythos 5.1); **`skills/skill-creator/**` has zero
  commits since 2026-07-22**, so every Trigger-Mode invariant (holdout 0.4,
  3 runs/query, test scores stripped, best-by-test, the "pushy" guidance in
  SKILL.md, the overfitting guard and ≤200-word / 1024-char targets in
  `improve_description.py`) stands by inheritance. Plugin copy @ `2a40fd2e`
  and agentskills/agentskills @ `69ef37e9` both unchanged.
- **Papers stable:** SkillOpt v2, SkillLens v1, Bennett v4 — no new versions.
- **One date was wrong.** The Fable field-guide row said 2026-07-03; the
  page's own `datePublished` is **2026-07-06** and its title is "A field guide
  to Claude Fable 5: Finding your unknowns". Corrected.
- **X rows all read by `scripts/read-x-post.py`**, `unexpanded: 0` on every
  one. The `bcherny` thread's fourth post re-confirmed verbatim; the `Mnilax`
  row still contains none of the claims it was once cited for and stays as a
  record of the bad citation.
- **Cost figures re-confirmed verbatim** on the optimizing-for-cost page
  (36%, 14%, +5 points, a third, 7–11 points, and the sentence extending them
  to skills).

### Previous freshen pass: 2026-08-20

All 29 rows probed (three parallel `web-searcher` agents: docs/blogs, GitHub,
papers/announcements). First pass on this file to use the one-stamp contract —
it had been running the legacy per-row format that Freshen Mode replaced, the
only file in the fleet still doing so.

### Notable changes since the previous pass (2026-07-24 → 2026-08-20)

- **A cap this skill told the loop to size against no longer exists.**
  Claude Code **v2.1.224 removed the 200-subagent-per-session spawn cap**
  (*"long-running sessions no longer refuse new agents (concurrency and depth
  limits still apply)"*). SKILL.md §Batch Mode named it as one of three live
  caps; corrected to two, with the removal stated. Verified against the primary
  `CHANGELOG.md`, not the summary.
- **A quote was attributed to the wrong file.** The `"be a little bit pushy"`
  guidance is in `skills/skill-creator/SKILL.md` (with its rationale — Claude
  *"has a tendency to 'undertrigger' skills"*), **not** in
  `scripts/improve_description.py`, where sources.md had claimed it. That file
  is the source of the overfitting guard and the ≤200-word / 1024-char targets.
  Both rows corrected; `trigger-patterns.md` Pattern T4 re-attributed.
- **Claude Code v2.1.219 → v2.1.237.** Seven new rows in
  `anthropic-skill-design.md`. Skill-relevant beyond v2.1.224: **v2.1.221**
  added a `prompt-audit` subcommand to the bundled `claude-api` skill that
  audits prompts *and tool descriptions* for "patterns written for older
  models" — first-party tooling aimed at the same target as the
  model-version-compensation cap, now cited in the rubric as a hypothesis
  source; **v2.1.222** makes Claude ask the user to run a
  `disable-model-invocation` skill rather than replicate it inline (strengthens
  the Dim 1 invocation-fit check); **v2.1.232** turns subagent forking on by
  default; **v2.1.233** extends `claude plugin validate` to bare
  `.claude/skills` frontmatter parse errors, and removes todo/task tools by
  default on Opus 4.8 / Sonnet 5 / Fable 5 / Mythos 5 and newer.
- **One probe finding was wrong and the skill was right.** An agent reported
  nesting-depth default moving 1→3 in v2.1.232; the primary changelog shows
  v2.1.232 says nothing about depth and v2.1.219 already carried it. Existing
  text kept. This is §"The Skill Outranks Training Data" applied to a subagent
  report rather than to a model prior.
- **Repos:** anthropics/skills @ 1f630fdf → `0a64e398` (2026-08-18), but
  `skills/skill-creator/**` is **unchanged** — Trigger Mode's mirroring of
  `run_eval.py` / `run_loop.py` / `improve_description.py` stays accurate, and
  all four of `run_loop.py`'s semantics re-confirmed in source (holdout 0.4,
  runs-per-query 3, test scores stripped before the improver sees them,
  best-by-test). agentskills/agentskills @ 38a2ff82 → `69ef37e9` (2026-08-09),
  one spec clarification: `metadata` values are strings, not arbitrary YAML.
  skill-creator plugin @ `2a40fd2e` unchanged.
- **Papers all stable:** SkillOpt v2, SkillLens v1, Bennett v4 — no new
  versions, and every load-bearing SkillLens figure re-confirmed verbatim
  (25% negative transfer, 46.4% / 15.8% judging, p > 0.34 on format, 73.8%
  rubric-guided, 64–66% better-rates).
- **Models:** no launch after Opus 5 (2026-07-24). The models-overview page
  again leads with **Fable 5** as most capable widely released, with Opus 5 the
  recommended default for complex agentic coding — the blind-scorer pin is
  Sonnet 5 and is unaffected.
- **The X rows were never unfetchable — only bot-blocked.** All four were read
  this pass through the operator's logged-in browser. Result: two Thariq essays
  confirmed as described; the `bcherny` ladder confirmed for steps 0–3 from the
  linked claude.ai artifact (step 4 and two quotes unreachable behind a
  non-scrolling iframe); and the `Mnilax` row **misattributed** — it contains
  none of the five claims it was sourced for. That row had been marked
  `ignore-freshen (X unfetchable)`, which is precisely why nothing caught it for
  months. `freshen-patterns.md` §2.4 now requires escalating a `402`/`403` to
  the browser before writing an exception note.
- **Cost figures re-confirmed verbatim** on the optimizing-for-cost page (36%,
  14%, +5 accuracy points, a third off for "verify twice", 7–11 points each for
  the three scaffolding defects, and the sentence extending all of it to
  skills).


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
| Claude Code skills docs | https://code.claude.com/docs/en/skills | Complete skill authoring guide, frontmatter reference (incl. `background`, `arguments`), bundled skills, "Evaluate and iterate on a skill" section | 2026-09-15 | — |
| Evaluating skill output quality | https://agentskills.io/skill-creation/evaluating-skills | Output-quality eval methodology: `evals/evals.json` schema, assertions, clean-context runs, `grading.json` / `benchmark.json`, blind A/B comparison, iterate-until-flat loop | 2026-09-15 | — |
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Official best practices: conciseness, freedom levels, progressive disclosure, evaluation-first testing, anti-patterns. **Re-read 2026-08-20** to settle the step-count question: the page gives degrees-of-freedom guidance (low freedom = explicit steps when operations are fragile / consistency critical / sequence matters) and "use workflows for complex tasks" with NO step ceiling — the basis for withdrawing the unsourced scaffold cap. | 2026-09-15 | — |
| Agent Skills specification | https://agentskills.io/specification | Cross-platform SKILL.md spec: required/optional fields (incl. license/compatibility/metadata/allowed-tools), validation rules; `description` hard cap 1024 chars and the `name` rules are unchanged; `metadata` clarified 2026-08-09 to a map of string keys to **string** values. **Size guidance, read verbatim 2026-08-21** (previously omitted from this row while quality-rubric.md leaned on it as an "Official limit"): "Keep your main SKILL.md **under 500 lines**. Move detailed reference material to separate files." plus the three-level loading model — metadata ~100 tokens at startup, "Instructions (**< 5000 tokens recommended**)" for the body, resources on demand. Note the asymmetry: the line figure is a bare imperative, the token figure is hedged. **Neither is enforced** — `skills-ref validate` checks frontmatter, not body length — so these are directives, not schema constraints. Anthropic's best-practices page and the Claude Code skills docs both state the same 500 lines, no conflicting number. **Do not conflate** the spec's "< 5000 tokens" *authoring* guidance with Claude Code's separate *runtime* cap: after auto-compaction it re-attaches "the first 5,000 tokens of each" skill, with re-attached skills sharing "a combined budget of 25,000 tokens". Same number, different mechanism. Verified by independent agent 2026-08-21 | 2026-09-15 | — |
| Claude models overview | https://platform.claude.com/docs/en/models/overview | Per-model IDs, pricing, context windows, knowledge cutoffs, and the vendor capability positioning — the label side of the blind-validation model pin. As of 2026-09-01 the table leads with **Fable 5.1** (`claude-fable-5-1`, June 2026 cutoff, $10/$50) "for demanding reasoning and long-horizon agentic work", with Opus 5 the recommended start "for most workloads"; Fable 5 is on the legacy list | 2026-09-15 | — |
| Effort levels | https://platform.claude.com/docs/en/build-with-claude/effort | Which models support `xhigh`/`max`, per-model defaults and recommended levels; per-message effort change (beta) on Fable 5.1 / Mythos 5.1 / Opus 5 keeps the cache, other models restart it; ultracode = `xhigh` + standing multiagent-workflow permission | 2026-09-15 | — |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | Version history with skill-related feature additions | 2026-09-15 | v2.1.257 |
| Claude Code hooks docs | https://code.claude.com/docs/en/hooks | Hook integration including hooks-in-skills frontmatter | 2026-09-15 | — |
| Claude Code subagents docs | https://code.claude.com/docs/en/sub-agents | Subagent types, skill preloading, context: fork, agent teams, background agents. **The 200-subagent-per-session cap was removed in v2.1.224** — concurrency (20, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) is now the only live subagent bound; nesting-depth default is 3 | 2026-09-15 | — |
| Claude Code prompt-caching docs | https://code.claude.com/docs/en/prompt-caching | Prefix layers (system prompt / project context / conversation); model and effort are cache keys; system prompt embeds cwd, platform, shell, OS, auto-memory paths — so each worktree is its own prefix; **subagents use the 5-min TTL even on a subscription** (1-hour is main-conversation only); fork inherits the parent prefix; workflow fan-out hold-and-release; `promptCacheTtl` / `subagentPromptCacheTtl` (v2.1.242+) and agent frontmatter `experimental.cacheTtl` (v2.1.248+) set the TTL per bucket / per agent; automatic model fallback on Fable 5.1 / Fable 5 / Opus 5 is a cache-invalidating model switch; grounds Pattern 7.3 | 2026-09-15 | — |
| Claude Code workflows docs | https://code.claude.com/docs/en/workflows | Workflow agent() cache mechanics (same prefix rules as Agent tool), fan-out cache warm-up | 2026-09-15 | — |
| Optimizing for cost and intelligence | https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence | Measured cost levers: caching 2.5-3.7x; prompt audit — Opus 4.8-era prompts cost 36% more per ticket on Opus 5 at equal accuracy, audit returns 14% and +5pts accuracy (14% again on Sonnet 4.6→5); "verify twice" removal cut cost by a third; retired thinking setting / contradictory rules / hand-rolled scratchpad each restored 7-11 accuracy points; page states the patterns apply to skills. Cited in quality-rubric.md §Boris Alignment Check and §The cost side of the same benchmark. Also: effort curves flat on knowledge work, re-run-failures policy | 2026-09-15 | — |
| Model pricing | https://platform.claude.com/docs/en/about-claude/pricing | Per-MTok list rates for every live model plus the cache multipliers (read 0.1x — **0.025x on Fable 5.1 and Mythos 5.1**, 5m write 1.25x, 1h write 2x), `inference_geo: us` 1.1x, fast-mode premium (Opus 5 / Opus 4.8 only), web search $10/1k; Sonnet 5's $2/$10 is the standard price since 2026-09-01 (scheduled $3/$15 increase cancelled). **Backs `scripts/model-rates.json`** — when this row is re-probed, update that file's `verified` stamp in the same pass | 2026-09-15 | — |
| Loop engineering blog post | https://claude.com/blog/getting-started-with-loops | Official loops guide (2026-06-30): /loop, /goal, /schedule taxonomy by trigger + stop condition; best practices (deterministic criteria, turn caps, verify via skills) | 2026-09-15 | — |
| Context engineering for Claude 5 models | https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models | Thariq Shihipar, 2026-07-24. **First-party written source for the Boris Alignment Check** — 80% of Claude Code's system prompt removed with no eval loss; six then/now shifts (rules→judgment, examples→interface design, upfront→progressive disclosure, repetition→simple tool descriptions, CLAUDE.md memory→auto-memory, simple specs→rich references); `/doctor` rightsizes skills + CLAUDE.md; rubrics-as-references + verifier agents | 2026-09-15 | — |
| Building verification loops with skills | https://claude.com/blog/building-verification-loops-in-claude-code-with-skills | Delba de Oliveira, 2026-07-22. Invocation-mode taxonomy (standalone / embedded / chained / on-every-PR) with outgrow signals and skip conditions; encode manual checks as skills; "a deterministic rule no generic linter will catch but a project-specific one will" — the criterion side of the scaffolding discriminator; plugin-managed skills off-limits for embedding (overwritten on update) | 2026-09-15 | — |

## GitHub Repositories

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| anthropics/skills | https://github.com/anthropics/skills | Official skill examples, spec, skill-creator, document skills | 2026-09-15 | main @ 53048666 (2026-09-01, claude-api skill updated for Fable 5.1) — **`skills/skill-creator/**` unchanged since 1f630fdf** (zero commits since 2026-07-22), so Trigger Mode's mirroring of `run_eval.py` / `run_loop.py` / `improve_description.py` stays accurate |
| Official skill-creator | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Anthropic's skill for creating/evaluating skills (has known bugs, actively maintained). **Source of the "a little bit 'pushy'" guidance** and the undertrigger rationale behind it (body, §description) — cited by trigger-patterns Pattern T4 | 2026-09-15 | main |
| skill-creator plugin (install path) | https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator | The copy the official docs tell users to install (`/plugin install skill-creator@claude-plugins-official`); last synced from anthropics/skills 2026-04-23 | 2026-09-15 | main @ 2a40fd2e |
| skill-creator: improve_description.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/improve_description.py | Description-improvement prompt — authoritative source for the overfitting guard ("do NOT produce an ever-expanding list of specific queries"; generalize to broader categories of user intent) and the ≤200-word / 1024-char targets. Trigger Mode mirrors this approach. The "pushy" guidance is NOT here — it lives in skill-creator's SKILL.md (row above); this row misattributed it until 2026-08-20. | 2026-09-15 | main (unchanged since 2026-04-20) |
| skill-creator: run_eval.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_eval.py | Trigger-detection mechanism: synthetic slash-command + `claude -p` + stream-json `tool_use` parsing. Source for `scripts/probe-trigger.py`. | 2026-09-15 | main (unchanged since 2026-04-20) |
| skill-creator: run_loop.py | https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_loop.py | 60/40 train/test split, 3 runs/query, blind test scores, best-by-test selection — Trigger Mode loop semantics. | 2026-09-15 | main (unchanged since 2026-04-20) |
| NVIDIA SkillEvaluator | https://github.com/NVIDIA/SkillEvaluator | Three-tier skill evaluation framework: keyless deterministic Tier 1 (schema / PII / unicode-smuggling / license / code-integrity / lint), embedding Tier 2 dedup (intra-skill DUPLICATE vs INTENTIONAL_DETAIL vs RELATED_BUT_DISTINCT; inter-skill similarity bands), Harbor-sandboxed Tier 3 A/B Skill Lift. Backs the pre-commit gate (`scripts/skillevaluator-gate.sh` + `.claude/skillevaluator-policy.yaml`, base+security install) and `scripts/overlap-scan.py` / `scripts/dedup-fleet.py` (tier2 extra, only — no LLM or Harbor deps, nothing leaves the machine). Its `external` profile is a public-marketplace policy, not this fleet's; the sweep script documents which checks it suppresses and why | 2026-09-15 | CHANGELOG 0.2.1 (2026-08-24) — the only GitHub release is v0.1.0 (2026-08-05); the earlier "v0.2.0" pin named a release that does not exist. Unreleased since 0.2.1: license conflicts no longer report `allowed`, PII in Markdown headings, `tools/` scanned like `scripts/`. The gate host runs 0.2.0 |
| Agent Skills spec repo | https://github.com/agentskills/agentskills | Spec source, `skills-ref validate` CLI tool | 2026-09-15 | main @ 69ef37e9 (2026-08-09) — one spec clarification since: `metadata` is now stated to be a map from string keys to **string values**. No `skills-ref validate` behaviour change |
| Claude Code releases | https://github.com/anthropics/claude-code/releases | Release notes with detailed changelogs | 2026-09-15 | v2.1.257 (2026-09-01) |

## Blog Posts & Articles

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Anthropic engineering blog | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Agent Skills announcement (2025-10-16), architecture, security considerations; standard open-sourced 2025-12-18 | 2026-09-15 | — |
| Anthropic news — Opus 4.8 | https://www.anthropic.com/news/claude-opus-4-8 | Opus 4.8 launch (2026-05-28): `claude-opus-4-8`, effort tiers, dynamic workflows, fast mode pricing | 2026-05-28 | — <!-- ignore-freshen (historical launch page) --> |
| Anthropic news — Opus 5 | https://www.anthropic.com/news/claude-opus-5 | Opus 5 launch (2026-07-24): `claude-opus-5`, $5/$25 per Mtok, near-frontier at half Fable 5's price but below it; new default Opus | 2026-09-15 | — <!-- ignore-freshen (historical launch page) --> |
| Anthropic — Fable 5.1 / Mythos 5.1 | https://www.anthropic.com/claude-fable-and-mythos-5-1 | "Introducing Claude Fable 5.1 and Claude Mythos 5.1" (2026-09-01): `claude-fable-5-1`, same $10/$50 base as Fable 5 with cache reads cut to $0.25/MTok — an estimated 25% cheaper on typical workloads, up to ~45% on highly agentic ones; benchmark table vs Opus 5 (Terminal-Bench 4.0 55.8 vs 42.0, Terminal-Bench-Science 52.6 vs 29.0, GDPval-AA v2 1853 vs 1824); Mythos 5.1 is the same model with looser safeguards for vetted cyber / life-science programs | 2026-09-01 | — |
| Anthropic news — Fable 5 | https://www.anthropic.com/news/claude-fable-5-mythos-5 | Fable 5 launch (2026-06-09): `claude-fable-5`, Mythos-class tier above Opus, pricing ($10/$50 per Mtok), availability windows | 2026-09-15 | — <!-- ignore-freshen (historical launch page) --> |
| Thariq Shihipar — Skills lessons | https://x.com/trq212/status/2033949937936085378 | "Lessons from Building Claude Code: How We Use Skills", 2026-03-17. Skill categories, "don't state the obvious", gotchas sections, progressive disclosure, distribution/marketplace, measuring skills. Browser-read 2026-08-20 — the row's prior `X unfetchable` note was wrong, the block is fetcher-side | 2026-09-15 | — |
| Thariq — Seeing like an Agent | https://x.com/trq212/status/2027463795355095314 | "Lessons from Building Claude Code: Seeing like an Agent", 2026-02-27. Tool-space design philosophy, AskUserQuestion history, TodoWrite → Task tool evolution, progressive disclosure via Grep/skills, Claude Code Guide subagent. Browser-read 2026-08-20 | 2026-09-15 | — |
| Anthropic — Improving skill-creator | https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills | First-party post on testing/measuring/refining skills (2026-03-03) — the closest published analogue to this skill, and previously uncited. **Comparator agents**: blind A/B of two skill versions, or skill vs. no-skill, judged without knowing which is which. **Two skill kinds**: *capability uplift* (decays as models improve — the case Floor Mode exists for) vs *encoded preference* (durable; evals verify workflow fidelity). Benchmark mode tracks pass rate + elapsed time + token usage. Description tuning improved triggering on 5 of 6 public skills. Floor Mode's premise stated first-party: base model passing evals with the skill unloaded means the skill is unnecessary, not broken. | 2026-09-15 | — |
| Thariq — Dynamic workflows | https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code | 2026-06-02. Names three single-context failure modes this skill's fan-outs already work around: **agentic laziness** (declaring done after partial progress), **self-preferential bias** (preferring one's own output when judging against a rubric — the stated reason blind validation exists), and **goal drift** (lossy compaction dropping constraints). Six composable patterns: classify-and-act, fan-out-and-synthesize, adversarial verification, generate-and-filter, tournament, loop-until-done. States that **comparative judgment is more reliable than absolute scoring** for qualitative ranking, and names skill refinement against a rubric as an eval use case. | 2026-09-15 | — |
| Thariq — A field guide to Claude Fable 5: finding your unknowns | https://claude.com/blog/a-field-guide-to-claude-fable-finding-your-unknowns | 2026-07-06 (the page's `datePublished`; an earlier row said 07-03). Known/unknown quadrants over prompts-skills-context as "the map"; the blindspot pass (literal phrasing "blindspot pass", "unknown unknowns"); implementation-notes.md with a Deviations log; quiz-before-merge as a comprehension gate. Techniques for finding what a skill fails to cover. | 2026-09-15 | — |
| ~~Boris Cherny on Lenny's podcast~~ **MISATTRIBUTED** | https://x.com/Mnilax/status/2050321700802408552 | **Read via browser 2026-08-20 (the `402` was the fetcher, not the page) and it does NOT say what this row claimed.** It is a third-party post by @Mnilax (2026-05-01) summarising a podcast as *nine patterns that waste 73% of your tokens* — CLAUDE.md overhead, re-read chat history, forgotten hooks. **None** of the five claims this row sourced — "don't box the model in", the bitter lesson applied to skills, "give it a tool, not context up front", build for the model 6 months out, plan-mode default — appears in it or its quoted tweet. Kept as a record of the bad citation, not as a source. The Boris Alignment Check does not depend on it (re-attributed 2026-07-24 to the first-party context-engineering blog, which carries all three capped patterns plus the measured cost evidence). Freshen §4b and the trigger Minimalism Test still describe their origin as this podcast — that origin is **unverified**, not refuted: the podcast may well say these things; this post is simply not evidence that it does. | 2026-09-15 | — |
| Boris Cherny — Steps of AI Adoption | https://x.com/bcherny/status/2077929379661844559 | Loop-era adoption ladder. **Browser-read 2026-08-20:** tweet is Boris Cherny, 2026-07-17, linking a claude.ai artifact "Steps of AI Adoption" dated 2026-07-16 — the artifact is the primary source, the tweet is a pointer. Ladder steps **0–3 confirmed verbatim** in the artifact table (0 Gated / 0 agents · 1 Assisted, a pair / ~1 · 2 Parallel, orchestrator / ~10 · 3 Supervised autonomy, manager of managers / ~100). **Confirmed 2026-08-22 by `curl` on the tweet itself** (not the artifact): the thread's fourth post reads "Anthropic is on step 3 and pushing toward 4. Personally, I just hit level 4." — so "Anthropic self-reports step 3" is first-party sourced, and a step 4 exists. The **whole four-post thread** has since been read via `scripts/read-x-post.py` (which expands X's `Show more` truncation), and it does **not** contain the step-4 "AI-native (1,000+)" label or the "I don't prompt Claude anymore … my job is to write loops" quote — so neither is sourced *to this tweet*. Both would have to come from the linked claude.ai artifact (whose iframe the browser could not scroll past step 3) or the @Scale talk. Unverified rather than refuted; do not quote them as sourced. | 2026-09-15 | — |
| Armin Ronacher — The Coming Loop | https://lucumr.pocoo.org/2026/6/23/the-coming-loop/ | Independent practitioner take (2026-06-23) on the loop shift — third-party corroboration of the loop-engineering discourse | 2026-09-15 | — |
| SkillOpt paper | https://arxiv.org/abs/2605.23904 | Microsoft text-space optimizer for agent skills (v2, 2026-05-25): bounded add/delete/replace edits, held-out validation gate, textual learning rate, rejected-edit buffer, slow/meta update. Source of this skill's rejected-edit buffer + noise floor (adopted 2026-07-18). Read from local PDF. | 2026-09-15 | v2 |
| SkillLens paper | https://arxiv.org/abs/2605.23899 | Companion lifecycle study (2026-05-22): 25% negative transfer; LLM plausibility judging = 46.4% accuracy, inverts to 15.8% on high-gap pairs; format non-significant; validated 3-dim rubric (failure mechanism encoding, actionable specificity, high-risk blacklist) lifts judging to 73.8%. Source of rubric §SkillLens Utility Check + Pattern 10.1b. Read from local PDF. | 2026-09-15 | v1 |
| Bennett — Weakest Not Shortest | https://arxiv.org/abs/2301.12987 | v4 2024: weakest (largest-extension) hypothesis maximises P(generalisation) under uniform task prior; MDL neither necessary nor sufficient; weak ≠ short. Source of the weakness criterion (SKILL.md Phase 2) and the failure-class rule in trigger Pattern T1. Read from local PDF. | 2026-09-15 | v4 |

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

## Evidence behind the rules
Measurements, dates, citations and history removed from the reference files when they were rewritten for the agent (2026-10-03). Grouped by the file and section they came from. Maintainer reading only — agents doing a task do not need it.

### anthropic-skill-design.md

#### Header
Sources: Thariq Shihipar (Anthropic), March 2026; official Claude Code docs (code.claude.com); Anthropic engineering blog; Agent Skills specification (agentskills.io). Created and maintained by Anthropic (agentskills.io).

#### Complete Frontmatter Reference
- description cap raised from 250 in v2.1.105, 2026-04-13. Spec clarified 2026-08-09: metadata keys AND values are strings.
- effort availability per platform effort docs 2026-09-01 (Opus 4.5 no longer listed).
- `background` default true since v2.1.218; `fable` alias -> Fable 5.1 since v2.1.257; `disallowed-tools` v2.1.152; scheduled-task block v2.1.196+.

#### Skill Tool and Permissions
Skill tool since v2.1.105+. Built-in commands (/compact, /init, /review, /security-review) were not model-invokable in older versions; /init, /review, /security-review became so in v2.1.108 (2026-04-14).

#### Version Notes & Settings (dropped rows, verbatim)
| v2.1.71 | 2026-03 | `/loop` command: run a prompt or slash command on a recurring interval (e.g. `/loop 5m <task>`). Ships as a bundled prompt-based skill. |
| v2.1.139 | 2026-05 | `/goal` command: completion condition, evaluator model judges; agent view (`claude agents`) research preview. |
| v2.1.105 | 2026-04-13 | Startup warning when descriptions are truncated. Plugin `monitors` manifest key auto-arms background monitors. |
| v2.1.108 | 2026-04-14 | Built-in commands `/init`, `/review`, `/security-review` invokable through the Skill tool by the model. |
| v2.1.110 | 2026-04-15 | Fixed `disable-model-invocation: true` skills failing when invoked via `/<skill>` mid-message. PreToolUse `additionalContext` no longer dropped on failure. PermissionRequest `updatedInput` re-checked against deny. |
| v2.1.111 | 2026-04-16 | `xhigh` effort for Opus 4.7. Bundled skills `/less-permission-prompts`, `/ultrareview`. PowerShell tool rolling out. `/skills` sort by token count (`t`). Read-only bash globs no longer prompt. |
| v2.1.113 | 2026-04-17 | Security: Bash deny rules match commands wrapped in env/sudo/watch/ionice/setsid; `Bash(find:*)` no longer auto-approves `-exec`/`-delete`; macOS /private paths dangerous for `rm`; dangerouslyDisableSandbox bypass fixed. |
| v2.1.114 | 2026-04-18 | Fixed permission-dialog crash for agent-team teammates. |
| v2.1.154 | 2026-05-28 | Opus 4.8 (`claude-opus-4-8`) ships; default `high`, `/effort xhigh`. Dynamic workflows research preview (`/workflows`; Enterprise/Team/Max). Lean system prompt default for all but Haiku/Sonnet/Opus <=4.7. Fast mode on 4.8 2x rate for 2.5x speed. |
| v2.1.157 | 2026-06 | Plugins in `.claude/skills` load automatically; `claude plugin init`. |
| v2.1.160 | 2026-06 | Dynamic-workflow trigger keyword renamed `workflow` -> `ultracode`. |
| v2.1.163 | 2026-06 | `\$` escape in command bodies. |
| v2.1.169 | 2026-06 | `--safe-mode` / `CLAUDE_CODE_SAFE_MODE`; `disableBundledSkills`. |
| v2.1.170 | 2026-06-09 | Claude Fable 5 (`claude-fable-5`) ships, Mythos-class tier above Opus; `xhigh`; $10/$50 per Mtok; included on Pro/Max/Team/seat-Enterprise Jun 9-22 2026. |
| v2.1.205 | 2026-07 | Custom commands merged into skills; nested dir-qualified names. |
| v2.1.212 | 2026-07 | WebSearch cap 200 (`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`), subagent spawn cap 200 (`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`, `/clear` resets) - batch/blind fan-outs counted against these. (Spawn cap removed v2.1.224.) |
| v2.1.214 | 2026-07-17 | EndConversation tool; permission hardening (fail-closed Bash redirects, >10k-char commands prompt). No skill-frontmatter or Skill-tool changes v2.1.171->214 beyond listed rows. |
| v2.1.215 | 2026-07-19 | Claude no longer self-invokes /verify and /code-review. Exact wording: "Claude no longer runs the `/verify` and `/code-review` skills **on its own**; invoke them with `/verify` or `/code-review` when you want them." Confirmed 2026-07-24 by sibling test: in a live v2.1.219 session `run` and `simplify` appear in the Skill-tool listing and `verify` does not. The verification-loops blog example chains `/simplify` -> custom `/verify-no-public-api-changes`. |
| v2.1.217 | 2026-07-21 | `paths` brace expansion budget-bounded (many brace groups OOM-killed startup). |
| v2.1.218 | 2026-07-22 | `/deep-research` and `/code-review` no longer self-launch. |
| v2.1.219 | 2026-07-24 | Opus 5 ships: 1M context, $5/$25 per Mtok, cutoff May 2026. Platform docs still label Fable 5 "most capable widely released model", but launch benchmarks put Opus 5 ahead on knowledge work, agentic search, tool-using reasoning, agentic terminal coding; Fable 5 ahead only on sub-1-point coding/tool-free-reasoning margins and legal. Nested subagent depth raised to 3. Workflow medium guideline then <15 agents. |
| v2.1.222 | 2026-08 | Refusal for disable-model-invocation strengthens the Dim 1 invocation-fit check. |
| v2.1.224 | 2026-08 | Quote: "long-running sessions no longer refuse new agents (concurrency and depth limits still apply)". |
| v2.1.232 | 2026-08 | Nesting depth 3 dates from v2.1.219, not this release. |
| v2.1.236 | 2026-08-19 | Fixed skills hot-reload erroring in SDK/VS Code sessions with deleted cwd (regression from 2.1.229). |
| v2.1.243 | 2026-08-24 | docs say v2.1.242+; API-key and cloud-provider users keep 1-hour cache on main conversation. `/tasks` shows model and effort per subagent. |
| v2.1.246 | 2026-08-25 | Dynamic workflow asks before restarting finished subagents on `/background` or interrupt. |
| v2.1.248 | 2026-08-27 | Workflow tool description cut ~5.7k -> ~1k tokens; script reference moved to bundled `workflow-authoring` skill. |
| v2.1.257 | 2026-09-01 | Platform models page moves Fable 5 to legacy, positions Fable 5.1 "for demanding reasoning and long-horizon agentic work"; cutoff June 2026; `fable`/`best` aliases keep resolving to Fable 5 in gateway sessions until gateway supports 5.1. Latest at 2026-09-01 freshen. |
| v2.1.261 | 2026-09-04 | `/skill-doctor` introduced. |

#### Related Tools
skill-creator "has known bugs but is actively maintained".

#### Dropped prose
- Skill Content Lifecycle debugging etc. kept; "Worth investing a full week making verification skills excellent" (Product Verification).
- Taxonomy: library skills "work for both internal and external libraries that Claude struggles with".
- Distributing: "Skills from --add-dir load automatically with live change detection" kept.
- Backfilled 2026-07-18 notes on v2.1.71/139.

### backlog-format.md

#### Drain duty
**Why this is enforced rather than advised.** Open counts across the fleet do not fall — they sit flat or rise across successive passes, and "Resolved this pass" becomes a changelog of whatever that session happened to do rather than the Open list being worked off. This skill's own target proved the cost: `netbox-best-practices` carried a `when_to_use` split from 2026-06-12 described as "spec-preferred but cosmetic today; do it next description edit". Nothing was absent — it was a two-minute frontmatter edit. It sat for 69 days while `description` grew from 866 to 1,070 chars, crossed the 1,024-char spec hard max, and hard-capped Dim 9 at 3. A deferred cosmetic item became the skill's single worst dimension by doing nothing at all.

#### Resolved this pass
Removed: "Hand-waving that 'the structure now exists' is theater."

### blind-validation.md

#### The scorer agent and prompt tail
Cache note: Subagents default to the 5-minute cache TTL even on a subscription (the 1-hour TTL is main-conversation only; `subagentPromptCacheTtl: 1h`, v2.1.242+, raises it), and a full improvement loop runs far longer than an hour anyway.

#### Measured scorer behaviour (2026-08-20)
Four skills spanning 77-988 SKILL.md lines, scored blind, n=3 per cell, via `claude -p --model M --effort E` with the agent body as system prompt. Effort on the current model first, then models at a fixed effort.

Effort: Opus at low / high / xhigh returned mean totals within about 3 points of each other per skill, no consistent direction, identical skill rankings at all three levels. Within-cell spread did not shrink with effort (median 2.5 / 3.0 / 3.0). A scoring pass is not the complex-reasoning workload the platform effort doc's `high` recommendation targets.

Floor: At `high`, Haiku was the ONLY model that reordered the skills, 14-point spread across three runs of one unchanged skill. Sonnet, Opus and Fable returned identical ranking. The floor holds on ranking instability and variance, not on the "shallow justifications" argument. Fable was the steadiest scorer (spread median 2, max 3), Opus the harshest.

Cross-model: Haiku, Sonnet and Fable all scored about +5 to +6 above Opus on the same skills.

Noise: No model held within-cell spread under +/-2: medians 2-4, maxima 3-6 (14 for Haiku). Why SKILL.md treats a bare +2 as undecided.

Cost (netbox-best-practices, first-party list rates): Haiku $0.23, Sonnet ~$1.14, Opus $1.96, Fable $2.62. Sonnet metered run finished early and under-reports.

Not measured: models below Haiku, efforts other than the three above, whether ranking stability holds on skills closer than these four (spread 68-86).

#### Model selection
Fable 5.1, 2026-09-01: Sonnet 5 unchanged, its $2/$10 rate made permanent. `CLAUDE_CODE_SUBAGENT_MODEL` default since v2.1.251; `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` v2.1.257.
Chosen on cost from the 2026-08-20 sweep. Variance differences (spread medians Sonnet 4, Opus 3, Fable 2) are a one-to-two point gap at n=3 on four skills, inside the noise; "treating that gap as a finding would be exactly the mistake this sweep caught the loop making."
Trial pin, set 2026-08-20. Reverses the 2026-08-15 dynamic-inheritance decision for the model only; effort still inherits. The churn that decision killed was re-pointing a pin on every release from a marketing label with nothing measured behind it. This pin has a measured floor and a stated reason.
Known gap: the effort sweep ran on Opus; "effort is flat, inherit it" is an inference for Sonnet.
Frontier floor: "measured 2026-08-20"; Boris Cherny's observation: cheaper-per-token models often use more total tokens on hard tasks because of correction loops.
Effort: operator decision 2026-08-16; platform effort doc (verified 2026-08-15) maps a scoring pass to `high`.

#### Parallel scoring (dynamic workflows)
Fable 5 / Opus 5, Claude Code v2.1.154+. "ultracode" replaced "workflow" as the trigger keyword in v2.1.160.

#### What blinding actually excludes
`improvement-backlog.md` exclusion in the agent definition dated from when the leak was first found. `evals/` leak found later, easy to miss because the directory looks like input data; `scorer-sweep.*.json` in one case held prior blind TOTALS for four other skills, anchoring a scorer told "most decent skills score 50-70". `evals/` cannot simply be excluded because the Negative-Transfer Gate needs a number from it.
Benchmark format: the rubric already mandates `aggregate_benchmark.py`, so its output is the standard; this repo's two hand-rolled `summary.delta_pass_rate` files are the deviants. Aggregator defects: written as `f"{delta:+.2f}"` (real +0.1875 stored as "+0.19"); `configs[0] - configs[1]` by dict insertion order; both sides `.get(..., 0)`. Same coerce-missing-to-zero failure the trigger and floor probes were fixed for. Every shape in the fleet carries the arms, so deriving is the only route working across all. Same principle as the Dim 1 character count: replace a judgement with a measurement.

#### When a scorer does not return a score
Filling from the self-score is "the exact bias blind validation exists to remove, reintroduced at the moment the check failed." Unscored end: "the keeps may still be sound, but nothing measured them." A run that scored 3 at baseline and 2 at final is comparable only with both counts stated.

#### The A/B comparator
A recorded pass kept six correctness fixes, lifted the self-score 80 → 85, and the blind scorer returned 85 both times; the improvement was real and the instrument could not see it. A comparator never has to resolve a delta against that spread; it reads both texts and picks one.
Verified 2026-08-22: `git archive` writes no `.git` but does not neutralise time; a baseline and a final came out 13 hours apart, a one-command tell. The `touch` line closes it.
Per-directory gate: running over `$AB` counted the A/B mapping note and reported a spurious `3` on the first real run.
Outside-repo: measured on the first live run, one of three comparators reported the commit subjects ("decide the pass by blind A/B", "expand X's Show more") having consulted no git command.
leakage split: the strict version was unusable. Every skill carries freshness stamps and `sources.md` is dated rows. First live run: two of three comparators reported a marker, only one was a real channel. Redacting in-text dates would hide Dim 9 evidence.

#### Measured comparator behaviour (2026-08-22)
Head-to-head against the absolute scorer on `netbox-best-practices` (neither instrument's author had edited it). Versions: `base`; `improved` (structural only: routing table replacing three trailing "when to read X" sections, plus explicit out-of-scope boundary); `degraded` (negative control: longer and smoother, with concrete error string, naming convention, API endpoint, Dockerfile lines and evidence labels removed). 3 comparators per pair, coin-flipped, `claude -p` from outside the repo. Scorer: 2 runs per version.

| Pair | Absolute scorer | Comparator |
|---|---|---|
| base vs improved | 86.5 vs 86.0 → -0.5 | 3/3 improved, medium / slight |
| base vs degraded | 86.5 vs 69.5 → -17.0 | 3/3 base, high / decisive |

Within-version scorer spread on identical content: base 88 / 85. The -0.5 sits inside noise and its sign is negative for a change three judges called an improvement. The -17 shows the scorer catches gross damage.
- Fluency trap held: the degraded version read better and was longer; all three comparators rejected it decisively.
- Confidence tracks difference size (medium/slight on modest edit, high/decisive on degradation).
Not established: one pair per direction; the "improved" version was authored by the party judging it useful, so no independent ground truth for the small-diff pair. A comparator flagged a real regression inside the version it voted for (routing table dropped one reference file's usage note).
Blinding, measured: an earlier in-repo run had one comparator in three report the caller's environment block listing recent commit subjects. Another flagged dated stamps inside the text. Cost: ~3.5 min wall-clock and ~140k tokens per 3-agent pair, in parallel.

### fleet-checks.md

#### (intro)
Every one of them found defects in skills nobody was touching. A checker whose false positives get treated as findings costs more than the defects it catches.

#### A Fence Is Code, and Nothing Else Checks It
Skill markdown is copy-paste material; a broken command fails on the reader's machine rather than here. `shellcheck` runs on `.sh` files only.
Measured 2026-09-15: 753 fences, 7 occurrences across 4 skills, none visible to `bash -n` — one had been quietly dropping two of three `--config.file` flags.
check-yaml-fences.py: 576 fences, one real bug (fieldPath with `[` `]` unquoted in a flow mapping; legal in block style, which is why it read as correct). Its value is the next edit, not the current run.

#### Content Scheduled to Become False
`freshen` catches sources that drifted, not content correct today and wrong on a date already written into it. "2.11 goes EOL 2026-10-24 — roughly three months out" had a correct date and a wrong description of it 5½ weeks later, in a warning whose job was conveying how short the runway was. Measured 2026-09-15: 37 future-dated claims, 2 worth acting on, both `[rel]` hits real.

#### Two Classes of Link Rot, and the Rest Is Noise
Measured 2026-09-15 over 2573 unique URLs: documentation hosts 322 checked, 7 dead; GitHub blob/tree paths 189 checked, 4 dead. All four GitHub findings were relocations; when a project migrates its docs to a generated site every deep link into the old tree dies at once. The fleet's last standing 403 turned out to be a sibling-path fix.

#### A Remediation Floor Is the Number an Operator Acts On
`freshen` re-probes sources; `advisory-lag.py` finds advisories a skill has not absorbed; neither checks a floor already written. Measured 2026-09-15: 104 advisory ids, one skill crediting a critical Argo CD advisory to two minors it never affected, one of them in a release that shipped three months before the fix existed; the file stated the correct range four sections above the error. Checker checks 7 of 104 ids; guessing at the rest manufactures findings.

#### A Cited Issue's State Drifts, and the Skill Keeps Its Old Verdict
Measured 2026-09-15 on an inference-server repo: three issues closed by `github-actions[bot]` with an `inactive` label all report `COMPLETED`. Across 694 citations: 6 real findings, split three-to-three; deciding by state alone would have been wrong half the time. One finding merged five days before a release and is not in it. One issue stayed open for four releases after its fix merged; a previous pass had recorded it as "confirmed still true"; a third party re-ran the reproduction and the author closed it naming the fix. One warning carried two independent reasons, one fixed and one closed won't-fix. A checker condemning the stale-bot phrasing would train its reader to ignore the report. AMBIGUOUS example: a dense correct line naming a fixed issue, its merged fix, an abandoned earlier attempt and a still-open sibling lands there by construction.

#### A Release Note Saying "Bumped X to N" May Be a CI Pin
Measured 2026-09-15, two lines in the same release notes: "Transformers bumped to 5.15.0" touched `requirements/test/*` only (CI pin); "Upgrade huggingface-hub to 1.28.0" touched `requirements/common.txt` (real floor). Two skills had recorded the first as the engine's floor. A third skill tracks three tokenizer CVEs fixed at three versions; the CI pin clears all three, the real floor clears none at that release. Correcting both package claims in one sentence on the strength of checking one would have been right by luck.

#### A Ragged Table Loses Its Last Column Silently
Measured 2026-09-15: 34 ragged rows across 7 files. Worst: header `| Symptom | Issue | Fix |` over rows with an extra model/scenario column, so Fix was discarded on exactly the rows carrying a model-specific workaround. An earlier draft of the checker produced 13 findings, all escaped pipes.

#### Which Fleet Sweeps Pay, and Four That Do Not
Syntactic sweeps found real defects on a fleet that looked healthy, including a troubleshooting table dropping its Fix column and a critical advisory credited to two release lines it never affected. The four semantic sweeps were tried 2026-09-15 and produced only false positives. Hit counts: unreferenced reference files 21 -> 9 -> 1 hits over three drafts (last one was reachable too); "latest" conflicts 53 hits, none real; cross-skill pointers 79 hits, none real; JSON in shell fences 152 candidates, 77 "invalid", all false positives. One real defect came out of reading the hits (a compatibility registry carrying a component its index never listed).

### floor-patterns.md

#### Classify the skill before probing it
Removed rationale: as the bleeding edge is absorbed into training, the skill should shrink to the delta. Capability-uplift content "decays as models improve, which is exactly what a floor probe detects." For encoded-preference skills "the model knowing what a Helm upgrade is says nothing about whether it knows to do it this way here"; probing spends tokens to produce a number that must be ignored, and the standing risk is that some pass eventually acts on it.

#### The three buckets
Removed: "The skill is its own answer key." "filling a blank is worth something, overriding a confident wrong prior is worth more, because unaided the model does not hesitate — it proceeds, wrong."

#### Two limits
Removed: "skills here are freshened past the model cutoff"; "without it the probe becomes a downgrade machine."

### freshen-patterns.md

#### Phase F1: Extract References
(2026-09-15: a fleet sweep of 70 descriptions found five carrying bare counts. Two were wrong — both correct when written, superseded by upstream removals/additions the skill's own `sources.md` already recorded that same day. Bodies were right; only descriptions were stale.)

#### Phase F3: Classify
- Absence claims: Measured 2026-09-15: a row recorded two doc-absence greps over a pinned docs snapshot. Re-grepping that snapshot (not current `main`), one term matched two files, and the introducing commit was an ancestor of the pin. The claim was false the day it was written and survived because no pass spent the thirty seconds.
- Tag ancestry vs backports: Measured 2026-09-15 on a chart tool maintaining two major lines: a PR's merge commit was not an ancestor of the patch release whose own notes credit that PR by number, while the release that did contain the commit never mentioned it. The two methods disagreed in both directions at once.
- Sibling test: (2026-07-24: settled a `/verify` chaining question in one command after it had been logged `unverifiable`.)
- Release-note default change: Measured 2026-09-15: a note read "raised `max_num_batched_tokens` from 8192 to 16384". The code added a new device tier above the existing branch — the largest GPUs default to 16384, the previously-documented class still defaults to 8192. An operator on the unchanged class re-plans a batch size that never moved; one on the new tier misses that their default doubled.
- "Current HEAD" refs: Measured 2026-09-15, twice in one pass, on numbers the reporting agent had labelled correctly and the writer mislabelled: one file gained anchors 60+ lines past their true position at the named tag, another 23 lines past.
- Absence-licensed inference: Measured 2026-09-15 on two registry files that each said upstream published no Kubernetes support matrix. Both false. One guessed a floor and happened to be right, so every pass re-derived it. The other inferred version windows from which doc pages 404; four windows were wrong (a floor, a ceiling, two OpenShift ranges). The 404 rule had stopped discriminating: recent minors 404 alongside old ones. "A stale number eventually contradicts something; a wrong inference never does."
- Lifecycle dates: Measured 2026-09-15: a tag-derived table ran about a month early on every one of five minors; on the oldest it turned a version with 39 days of support left into one that read as expired, retiring a live migration source.
- Inherited unverifiable: (2026-09-15: a row carrying "not re-verified — vendor blocks automated reads; read manually" opened first try in the browser, and every per-generation figure in the companion reference read back identically off the live page. The flag had made the row unfalsifiable rather than unverified.) The same pass found six documentation URLs returning `429` to curl even one at a time, all loading normally in a browser.

#### Recency filter (F2)
Rationale: a full sweep of a file freshened three days ago mostly re-reads specs that change on a scale of quarters. Restamping an unprobed row silently disarms the Dim 9 staleness cap so the skill scores as fresh forever; "a filtered pass that reads as a full one is worse than no pass at all."

#### Phase F6: Stamp and Summarize
Blanket-restamp incident: hit in three files in a single pass on 2026-09-15 before being caught and reverted; it backdates this pass's work onto an older record and erases when the skill was authored.

#### 2.1 GitHub release tags
(2026-09-15: a hypervisor's `isLatest` was `v1.8.2` while `v1.7.3`, one day newer, sat on the 1.7 line; a Kubernetes distro published three lines — `v1.34.11`, `v1.35.8`, `v1.36.4` — on a single day.)
(2026-09-15: a row read "No git tags/releases — the version lives in a header file"; `gh release list` was indeed empty, and the repo had tags for every version including one newer than the header the row quoted.)

#### 2.4 Live URL check
Measured 2026-08-22: `x.com` posts, theatlantic.com and newyorker.com all return `200` to bare `curl` and `402`/`403` when the same `curl` sends `-A "Claude-User/1.0"`.
X/Twitter: Verified 2026-08-22 against all six `x.com` rows in this repo's sources plus a `twitter.com` host: `unexpanded: 0` on every one. `og:description` meta tag is hard-capped at 278 chars; long posts render only first 278 chars plus `Show more`.

#### 3.0 A closed issue is not a fixed issue
Observed 2026-07-21 in two unrelated repos on the same day:
- `sgl-project/sglang` #20184 and #17623 — both CLOSED/COMPLETED, both closed by "This issue has been automatically closed due to inactivity."
- `huggingface/transformers` #45205 — CLOSED/COMPLETED 2026-06-10, closed by "automatically marked as stale because it has not had recent activity."

#### 3.0b A tag is not a release
Observed 2026-09-22 — a `messages-api` row recording opencode v2.0.3 was "corrected" to "has never existed" because `gh release list` topped out at v1.18.32. The operator's machine was running v2.0.8. Tags `v2.0.0` through `v2.0.13`, a `2.0` branch, npm `@opencode/cli` at 2.0.13, a `/v2/` docs tree and a `/v2/install` script all existed; only a Release object did not. Cross-reference: [[the-skill-outranks-training-data]].

#### 4b. Scaffolding Decay Probes
Boris Cherny (creator of Claude Code) on the bitter lesson: scaffolding gains "get wiped out by the next model. So it's almost better to just wait for the next one." Quote in mutations: "Removing something and getting equal results is a great outcome."

### improve-loop.md

#### Header
Extracted verbatim from `SKILL.md` §"The Improvement Loop"; the stub there carries the three rules that bind without reading this file.

#### Phase 0
- Reading the whole tree up front costs the loop its own induced-cost cap on a large skill.
- Boris Alignment Check: the procedural-scaffolding step-count cap was withdrawn 2026-08-20.
- Phase 0 step 6: "without it the entire run rests on whatever bias the loop's self-scoring carries."

#### Phase 2
- Simplicity criterion origin: autoresearch.
- Weakness criterion: generalisation probability scales with what a rule permits, not its brevity (arXiv:2301.12987); held-out test splits exist to punish encoding the literal failing case.
- Format-only: SkillLens (arXiv:2605.23899) measured skill format as statistically non-significant on every tested target, while content changes were significant on 5/6. The 2026-07-18 self-run confirmed: all three format/naming iterations discarded at delta 0.

#### Phase 4
- Line-ceiling gate: the rubric cannot see this. Real miss: freshen additions took a SKILL.md 493 -> 506, past the spec ceiling (agentskills.io / platform best-practices cap), with every dimension band-internal; only a manual count caught it. Cost measurements (`quality-rubric.md` §Boris Alignment Check): stale bulk cost 36% more per ticket at unchanged accuracy; scaffolding that fights the model cost 7-11 accuracy points.
- Anomaly gate: most +5 jumps shrink to +3 under cold rescore.
- +1 zone: cold rescores routinely move a total by +-1-2.

#### Phase 5
- Widen before declaring the ceiling: a discard run means improvements went sparse, not absent. One-at-a-time holds up against costlier strategies while improvements are dense (arXiv:2603.27415); an agent that switches strategy on detecting stagnation beat every fixed-strategy agent tested (arXiv:2605.17373). Widening is a response to stagnation, not a permanent upgrade.

#### Phase 7
- "A backlog that lands a commit later describes a state that never existed."
- "Both blind scores: a run reporting one has no bias check and its trend is self-scored."
- "Findings named only in the run summary are gone with the session."

### improvement-patterns.md

#### Pattern 3.4
SkillLens found High-Risk Action Blacklists predictive of skill utility.

#### Pattern 6.1
Measured across the whole fleet: 62 skills analysed (6 exceeded the tool's chunk ceiling), 520 clusters: INTENTIONAL_DETAIL 292, RELATED_BUT_DISTINCT 138, DUPLICATE 90. 83% of similar-looking content was correct as written (430 clusters); 23 skills had no duplication. Worst DUPLICATE offenders: autoresearch (7), jinja-expert (6), keda (6), sglang-hicache (5). Verified by hand: keda carries the same six-step triage block in SKILL.md:295-313 and references/troubleshooting.md:12-27, differing only in placeholder style (<name> vs "$NAME"); two independent models agreed on keda's count via different gateways. skill-improver itself is 444 chunks (over the ~221 limit). Pure relocation is one atomic change; relocation that rewrites prose is two (SKILL.md §"The split test for atomicity").

#### Pattern 7.3
Subagent 5-minute TTL claim verified 2026-09-01 against Claude Code prompt-caching docs. Guidance derived from Claude Code prompt-caching and workflows docs.

#### Pattern 10.1b
SkillLens (arXiv:2605.23899): generic-advice-without-mechanism is the single strongest text-level predictor of skill utility; such skills read well but underperform.

#### Dropped examples
2.1 full API-reference before/after; 2.3 nested-chain diagram; 3.1/3.3 prose before/after (compressed inline); 6.2 boilerplate text; 6.3 code-fence example (compressed inline); 1.4 verbose-preamble note.
Original file: /tmp/si-shrink.qPkC/ip.orig

### quality-rubric.md

#### Dimension 1 (platform constraint)
Claude Code truncates combined description + when_to_use at 1,536 chars (raised from 250 in v2.1.105, 2026-04-13).

#### Dimension 1 (common failures)
Imperative "Use this skill when..." form is what Anthropic's own skill-creator description optimizer emits.

#### Dimension 2
"Keep your main SKILL.md under 500 lines" — agentskills.io/specification, echoed by Anthropic's best-practices page ("under 500 lines for optimal performance") and Claude Code skills docs. No validator checks it: skills-ref validate covers frontmatter only. The same page hedges the companion figure: "Instructions (< 5000 tokens *recommended*)". Reference depth: Claude may partially read files referenced from other referenced files (using head -100 previews).

#### Dimension 6
Inspired by autoresearch: deleting code for equal results is a win.

#### Dimension 9 (hard-fail frontmatter parse)
That is not hypothetical: this rubric's own quick-check snippet and frontmatter-lengths.py were both regex-only until 2026-08-20, and printed clean, confident numbers for two skills whose frontmatter had not parsed for months. (frontmatter-lengths.py now parse-gates first.) A scorer eyeballing a non-parsing block sees a healthy description and scores Dim 1 on text the loader already threw away.

#### Dimension 9 (staleness cap)
Two blind scorers split on exactly the header-stamp-without-row-column case on 2026-08-22: one declined the cap and scored Dim 9 8, the other applied it and scored 6, on byte-identical input. staleness-report.py already resolved the stamp first; the rubric was aligned to it.

#### Boris Alignment Check
Original: Diagnostic patterns originally drawn from Boris Cherny (creator of Claude Code, Anthropic; Lenny's podcast 2026) and since confirmed in first-party writing by Thariq Shihipar, "The new rules of context engineering for Claude 5 generation models" (2026-07-24) — which reports over 80% of Claude Code's system prompt removed for Opus 5 / Fable 5 with no measurable loss on coding evals, and names all three patterns as superseded practice. The X row that once carried the podcast attribution was read through a browser on 2026-08-20 — the 402 had been the fetcher, not the page — and it turned out to be a third-party post about token-waste patterns containing none of the claims attributed to it (sources.md, row marked MISATTRIBUTED). The blog is first-party and carries all three patterns plus the cost evidence, so nothing here rests on the bad citation; the podcast origin is unverified.

Cost evidence, from "Optimizing for cost and intelligence" (Anthropic, re-read 2026-08-19), support-desk evaluation:
- Prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no change in accuracy.
- Auditing the same prompts against the current model made Opus 5 14% cheaper than unaudited and more accurate (97% of tickets, up from 92%). Sonnet 4.6 -> Sonnet 5 migration: 14% off at equal accuracy.
- Removing "verify twice" cut cost per ticket by a third; "be maximally thorough" nearly as much. A retired thinking setting, contradictory rules, and a hand-rolled scratchpad each restored 7-11 accuracy points on Opus 5 when removed.
- The page says the patterns "appear in tool descriptions and skills, and are worth removing there too".
The caps are not a style preference — an uncapped skill of this shape is measurably slower, dearer, and less accurate on the model it runs on today. The bitter lesson applied to skills.
First-party tooling: Claude Code v2.1.221 added a prompt-audit subcommand to the bundled claude-api skill.

#### Procedural steps — advisory signal, NO cap (withdrawn 2026-08-20)
A "≥ 8 scaffold items → Dim 6 capped at 6" rule was withdrawn: it had no source and contradicted the evidence it cited. Checked 2026-08-20:
- No first-party or peer-reviewed source gives a numeric threshold for numbered/procedural steps (not the platform best-practices doc, the two claude.com blog posts, SkillLens, or agentskills.io). The 8 was inherited from a naive `rg -c '^\s*\d+\. '` detector.
- Anthropic: "Set appropriate degrees of freedom. Match the level of specificity to the task's fragility and variability." Low freedom (explicit sequential steps) is recommended when "operations are fragile and error-prone / consistency is critical / a specific sequence must be followed." Also "Use workflows for complex tasks. Break complex operations into clear, sequential steps", no ceiling; its worked examples run 4–6 steps. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- SkillLens: rewriting one skill into different surface formats yielded statistically indistinguishable gains (p > 0.34). Its three validated predictors (Failure Mechanism Encoding, Actionable Specificity, High-Risk Action Blacklist) are content properties, none a count. A step-count cap contradicted the rubric's own §"Format-only hypotheses are low expected value".
- Delba de Oliveira's verification-loops post: "Reject any migration that drops a column without a backfill step" is a deterministic rule no generic linter will catch but a project-specific one will.

#### Induced cost
Dim 2 counts lines; a 90-line skill saying "read every reference before starting", fanning out unbounded subagents and pinning effort: xhigh is cheap to load and expensive to run. The "feels wasteful" judgment was clocked by SkillLens at 46.4%, worse than chance. Measured on this fleet (68 skills, --refs): 3 fire. An earlier, looser version fired on 4 of 6 skills tested, mostly on prose that quoted the patterns; it was narrowed until it separated mention from use. The effort: xhigh ruling is dismissed in the backlog.

#### SkillLens Utility Check
Source: Microsoft's SkillLens study (arXiv:2605.23899, 2026-05). LLM judge picked the higher-utility skill 46.4% of the time (random); on the largest-gap pairs only 15.8%. Skill format (list vs prose vs checklist) statistically non-significant on every tested target. The three predictive properties had better-rates of 64–66%.

#### Negative-Transfer Gate
SkillLens (arXiv:2605.23899) vs a no-skill baseline: skills help in only 75% of extractor-target pairs, 25% net-harmful, worst domain 47% negative ("ALFWorld is the most fragile"). Roughly one in four makes the agent worse at its own task. Scorer intuition on Dim 10's test is the judgment SkillLens clocked at 46.4%.
Band asymmetry: NVIDIA's published Skill Lift band (+0.05 pass, −0.10 fail) is asymmetric in the same direction; the floor here is measured from the corpus because a constant is too tight at 8 cases and far too loose at 3. A false "unresolved" only withholds a 9 or 10; a false "harmful" gets a skill rewritten or deleted.
The unmeasured cap binds most often, deliberately: 9–10 asserts the skill "fundamentally changes Claude's capability", which reading text cannot establish.
Errored-case rule bites hardest at small corpus sizes: at the fleet median of 3 cases one errored case is a third of the evidence.

#### Negative-Transfer Gate (floor evidence)
A totally failed floor run used to produce a 0% floor, which is the "every claim is real transfer" row, so the probe breaking raised the cap to 9.
Durability measured on this fleet: of 17 opus CONFLICTS on the 8 skills also probed on fable, 12 conflicted on fable too. Of 31 opus CONFLICTS across all 68 skills probed on haiku, only 3 conflicted there, because 26 came back UNKNOWN.
Profile 3 measured examples: ubuntu-netplan (13/15 known, 2 conflicts) and keda (10/12 known, 1 conflict), at the top of the floor leaderboard next to makefile-best-practices (10/10, zero conflicts, profile 1, opposite recommendation).

### scripts.md

#### Header / intro
Catalogue lives here rather than in SKILL.md: progressive disclosure (Pattern 2.1) applied to itself after the pre-commit gate flagged SKILL.md at 10,051 tokens against the 5,000 guidance.

#### scripts/advisory-lag.py
- Rationale: a skill verified eight weeks ago whose upstream shipped a critical auth bypass in week six is a worse liability than one verified six months ago against a project that shipped nothing; date ordering is blind to this.
- Found `traefik-hardening` sixteen advisories behind with two criticals, one a complete authentication bypass in a middleware the skill configures.
- Corrected 2026-09-15, same day it shipped: first version silently skipped an empty repo feed. Endpoint returns `[]` both for no advisories and for a token lacking `repository_advisories=read`. 27 skills were dropped that way, including `huggingface/transformers` (`[]` from repo endpoint, ecosystem database lists four 2026 advisories, two high, in tokenizer-loading path). Docstring's earlier claim that `first_patched_version` is reliably null withdrawn: true on repo feed, false on ecosystem database.

#### scripts/dedup-fleet.py
- 1 duplicate among 22 clusters is noise, 4 among 7 structural. 1-of-2 is two clusters, not "50%".
- Measured `vllm-*` at 13 skills and 29 duplicate clusters, a third of all fleet duplication.
- 68-skill re-report 0.07s vs 7m19s cold. Same `bge-m3` scores differently across gateways.

#### scripts/eval-evidence.py
- Official aggregator writes `delta.pass_rate` as a 2-decimal string, orders by dict insertion, defaults a missing arm to 0, turning an absent baseline into a maximally positive result.

#### scripts/overlap-scan.py
- Measured on 68 skills with bge-m3: median body pair 0.789, above `SIMILAR`. Measured `corr(body, lexical) = 0.515`; two unrelated 400-line operator guides score high for both being 400-line operator guides.

#### Deterministic safety gate
- An earlier `tier1-sweep.py` reimplemented severity filtering in Python; the policy file replaced it.

#### scripts/frontmatter-lengths.py
- A scorer reported 1,120 chars for an 847-char field and hard-failed Dim 9 to 3 on the invented number (2026-08-20).

#### scripts/read-x-post.py
- `WebFetch` identifies as `Claude-User`, hence 402.

#### scripts/scaffold-probe.py
- Step-count cap it once fed was withdrawn 2026-08-20: no source states a numeric threshold; Anthropic's degrees-of-freedom guidance recommends explicit steps for fragile or order-dependent work; SkillLens measured surface format as non-predictive (p > 0.34).

#### scripts/knowledge-floor.py
- `fable` alias was Fable 5 until 2026-09-01, Fable 5.1 after.

#### scripts/run-cost.py
- One request writes one record per content block; summing records overcounts 2x+. Agent cannot see its own spend at runtime.
- Throughput inverse to capability (haiku 70.7 tok/s -> fable 30.2).

#### Eval-corpus maintenance
- normalize-evals: audit found 26 eval files with 11 distinct shapes and no provenance; 15 predated the current model by four generations; a case expecting a reminder an older model needed fails when that reminder is correctly deleted.
- backfill-assertions: prose `expected_output` comparison measured by SkillLens at 46.4% (worse than chance).
- grow-evals: at corpus median of 3 cases one flip moves pass rate 33 points.
- regrade: first fleet pass inflated `CONFLICTS` by dumping agree-with-different-detail and hedged answers into it.
- bucket-evals: measured on 14 corpora / 220 queries: `contextual` 9% against 20% target, four corpora at zero, negatives 45%.

#### scripts/probe-trigger.py
- Adapted from anthropics/skills `skill-creator/scripts/run_eval.py`.

#### scripts/check-* (not in the original file; added from docstrings)
- check-expiring-claims: measured 2026-09-15: 37 future-dated claims, 2 worth acting on; example "2.11 goes EOL 2026-10-24 — roughly three months out" when the date was 5½ weeks away.
- check-links: measured 2026-09-15, 2573 unique URLs; documentation hosts 322 checked / 7 dead; GitHub blob/tree 189 checked / 4 dead (repo renames redirect, moved files do not).
- check-tables: measured 2026-09-15: 34 ragged rows across 7 files.
- check-yaml-fences: 576 yaml fences, one real bug (LeaderWorkerSet `fieldPath` with `[` `]` unquoted inside a flow mapping).

### trigger-patterns.md

#### Header / Trigger Mode Workflow
- Methodology mirrors Anthropic's official `skill-creator` description-optimization loop (60/40 train/test, blinded test scores, <=1024-char hard cap); skill-creator uses 3 runs/query, this skill uses 7. Sources documented at `references/sources.md` (Skill authoring best practices, anthropics/skills `improve_description.py`, `run_eval.py`, `run_loop.py`).
- Score-mode bumps Dim 1 (Trigger Precision) on subjective rubric judgment; trigger-mode measures it empirically.

#### Phase T1
- Measured across this fleet's 14 corpora and 220 queries: `contextual` sat at 9% against the 20% target, with four corpora at zero, while negatives ran 45%.

#### Phase T4
- Measured instance: skill-improver sat at exactly 1536/1536 on 2026-08-20 while its own backlog planned an addition on the belief that ~230 chars were free.

#### Phase T5
- Observed 2026-07-24 on `autoresearch`: at N=3 the canonical "set up an autoresearch loop" query read 0.67 -> 0.00 and drove a whole iteration built on a fabricated mechanism about proper-noun placement; at N=7 the same pair was 6/7 vs 5/7 -- nothing. The same low-N artifact simultaneously hid a real Mode-3 fix behind a tied pass count.
- A candidate can tie 4/7 on pass count while differing by 8 fires out of 49.
- Fisher exact p~0.03 for 1/7 -> 6/7.

#### Why skills under-trigger
- Quote from official skill-creator: "Claude has a tendency to undertrigger skills -- to not use them when they'd be useful." Causes mapped from the official best-practices doc.
- Cause 6 (easy queries Claude answers alone): Anthropic notes skills only fire for tasks Claude can't easily handle on its own; e.g. "read this PDF".

#### The probe mechanism
- `--setting-sources project` rationale: without it `claude` also loads `~/.claude/skills/` (often symlinks of the skills under test), the synthetic competes with its real twin, the model invokes the real one, probe sees the synthetic id missing -> false 0.0.
- `--disallowedTools` rationale: a query like "deploy my app to openshift" makes the nested agent try to provision a local environment (`crc`/libvirt -> host sudo/pkexec prompts) or run arbitrary Bash.
- `--timeout` rationale: sized for `claude -p` latency (60-150s/call incl. cold start / Opus); a fast call returns on its `result` event so a high value has no downside; timed-out runs are tracked per query and surfaced as a `warn:` line, and an all-positives-0.0 result emits a "probe isn't measuring" warning.
- Probe is a stripped-down adaptation of `anthropics/skills/skill-creator/scripts/run_eval.py`.

#### Which model to probe with
- Haiku ~20-40x faster and ~5x cheaper than Opus; Anthropic builds it for routing/classification.
- Measured on this repo (2026-06): of 6 skills Haiku flagged as under-triggering, 5 fired 1.00 on Opus (the 6th was correct deferral to a sibling).
- Sonnet matched Opus on a 5-query subset, but only at n=3 (provisional).
- Cache-prefix identity: a fresh model/--effort/--settings value writes ~35k tokens, then runs warm at ~0.

#### Cost & time budget
- ~$0.03/call on Sonnet. 40 queries x 7 runs ~ 280 calls ~ $8 and tens of minutes.
- Measured: a setting that dropped two queries from 1.00 (7/7) to 0.71 (5/7) read as identical across four n=3 arms, because 0.71 and 1.00 both land on 1.00 on that grid.
- Prompt cache expires at 60 min: https://claude.com/blog/maximizing-the-value-of-your-claude-code-sessions
- `MAX_THINKING_TOKENS=0` is ~6% cheaper and cuts output 29-50%, but at n=7 both firing queries fell 1.00 -> 0.71.
- Timing: Haiku ~2-5s per call, Opus ~60-150s. Default 13-query x 7-run x 5-iteration loop ~ 455 invocations if every query re-probes every iteration.
- A 13-query corpus with 6 negatives moves 14 points when one query flips.

#### Pattern T2
- Measured on `skill-improver`, 2026-08-20: three should-NOT queries about creating skills fired at 1.00/1.00/0.71. Adding "Does NOT apply to writing a new skill from scratch, scaffolding a SKILL.md for a workflow that has none, or packaging and publishing plugins" moved the mean negative rate 0.452 -> 0.476; `write me a SKILL.md for my terraform workflow` went 0.71 -> 0.86. The clause introduced "new skill from scratch" and "SKILL.md" as matching text.

#### Pattern T4
- Anthropic's skill-creator tells authors to make descriptions "a little bit 'pushy'" (`skills/skill-creator/SKILL.md`, not the description optimizer -- verified 2026-08-20).

#### Pattern T5
- Tension with T4's "add redundancy" is intended: T4 strengthens a borderline query, T5 trims a cap-bound description; both answer to the same eval.

#### Minimalism test (Boris alignment)
- Boris Cherny: "underfund things at the start... if you have a good idea, you just really want to get it out there."
- Rationale: a high-trigger-rate / low-value skill inflates its 10-dim score (Dim 5 Completeness sees coverage; Dim 7 Resource Quality sees existence) while per-invocation impact is poor.

#### Worked example (removed; vllm-caching trigger run)
User: "/skill-improver trigger vllm-caching -- it didn't fire when I asked about prefix caching memory tuning".
- T1: 13 queries (6 should-trigger incl. user-reported "how do I tune prefix cache memory in vllm", "should I enable prefix caching"; 7 negatives incl. siblings vllm-deployment, vllm-performance-tuning, vllm-quantization, vllm-chat-templates, decoy, "hello").
- T2: baseline train 5/8, test 4/5. Failures: "how do I tune prefix cache memory in vllm" 1/3 (under), "should I enable prefix caching" 0/3 (under), "fix my vllm CUDA OOM" 3/3 (over).
- T3: mixed, 2 unders 1 over -> T1 first. T4: added to `when_to_use` `"should I enable prefix caching", "tune cache memory", "vllm OOM on long context", "kv cache memory budget"`; combined 712 chars.
- T5: train 7/8, test 4/5 -> KEEP. Next: T2 on the CUDA OOM over-trigger, added `Do NOT use for general CUDA OOM debugging -- use vllm-deployment for pod sizing or vllm-performance-tuning for batch-size tuning.` -> train 8/8, test 5/5, STOP. Baseline 9/13 -> 13/13 in 2 iterations.
(Decisions taught: mixed failures -> fix larger class first; negative boundary names the sibling.)
