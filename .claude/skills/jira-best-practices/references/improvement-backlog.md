# Improvement backlog — jira-best-practices

Carries findings across skill-improver runs. Read in Phase 0 (improve) / T0 (trigger) / F0 (freshen); update on completion.

## Open

- **Dim 10 unmeasured cap (both 2026-08-18 blind scorers' #1 finding).** No `evals/evals.json`, no `benchmark.json` → Negative-Transfer Gate caps Dim 10 at 8. Blocked in-loop: building an outcome eval set + running the skill-creator with/without benchmark is multi-file work plus external runs. Action: author `evals/evals.json` (task-outcome assertions, not trigger cases — `trigger-evals.json` covers triggering only), then measure `delta_pass_rate`.
- **Frontmatter headroom ~3 chars (1,533/1,536 combined; both scorers' nit).** Any trim/rewrite invalidates the trigger pass's validated 14/14 frontmatter, so the mutation requires a trigger-mode probe run (`probe-trigger.py`), not an improve iteration. If a trigger pass runs anyway, bank ~50–80 chars of headroom while it's measured.

Anti-re-proposal guards (tried 2026-08-18, judged net-negative — do not re-propose the same shape):
- **Condensing SKILL.md summary sections toward pointers** (the blind scorers' recurring Dim 6 flag: hierarchy misconceptions/heuristic, non-software bullets, decomposition anti-patterns). Tried on the non-software section — DISCARDED: each condensed bullet carried unique one-line coverage (Jira Core base, scheduler-app recurrence) for a primary trigger; Dim 5 loss ≥ Dim 6 gain. The genuinely redundant site (the closing Execution paragraph) was removed instead. The remaining SKILL.md/reference overlap is deliberate progressive-disclosure summary, priced in at blind Dim 6 = 7.

Cosmetic-only notes (NOT attempted-and-blocked — future-cosmetic, content is correct):
- Bold/em-dash density in the prime-directive and lean-levers sections (SKILL.md) — a marginal Dim 6 styling trim; flagged by the 2026-06-07 blind scorers as the only stylistic fat (SkillLens: format-only, low EV).
- `hierarchy.md` (exactly 100 lines, at the rubric's >100-line TOC threshold) has no in-file TOC. Add one if it grows past 100 lines.
- `sources.md` and `work-modeling.md` cite `autoresearch/results/...` provenance paths that exist only in the authoring repo (final 2026-08-18 blind docked Dim 8 for it). Harmless pointer on other installs; convert to plain-text provenance notes if it ever bites.

## Resolved this pass — 2026-08-18 (`/skill-improver improve, freshen`)

- **Freshen (F0–F6, ~13 probes, 0 unverifiable):** DC state re-stamped to 2026-08 (11.3.10 latest, 11.3 still the newest line, 10.3→2026-12-05); mcp-atlassian ~72→~98 tools at v0.23.0; in-scope new-feature note for `jira_get_project_epic_hierarchy` + `jira_get_cross_project_dependencies` (#1286). Re-affirmed fresh: JPOSERVER-4430 (still Closed/Not-a-bug via public REST), `jira_batch_create_issues` epic-link silent-drop (schema on main unchanged post-v0.23.0), DC EOL milestones, docs URL. 7 sources.md rows stamped 2026-08-18.
- **Improve (6 iterations: 5 keeps, 1 discard): baseline blind 84 → final blind 85; self 87 → 89; bias aligned both ends (no dim gap ≥2).**
  - Iter 1 KEEP (Dim 3 8→9, confirmed by final blind): purged 16 second-person slips from 5 reference files; residual grep hits are verbatim quotes only.
  - Iter 2 KEEP (simplification): closing Execution paragraph collapsed to a one-line pointer (restated "How the work gets done").
  - Iter 3 KEEP: contents line added to sources.md (146 lines; rubric-prescribed).
  - Iter 4 KEEP (Dim 4 blind 8→9): scaffold sequence step 5 — exhaustive verify bound (exact child count, every epic link, every `blocks` edge; diffs reported, never silently re-created).
  - Iter 5 DISCARD: non-software summary condensation (see anti-re-proposal guard above).
  - Iter 6 KEEP: field audit completion bound (every Create-screen field gets a recorded yes or a remove recommendation).
- Scaffold-probe verdict (11 flagged items) overridden with justification by self and both blind scorers independently: the flags are anti-pattern blacklists / thresholds / named-failure criteria, not invocation-flow scaffolding — no Dim 6 Boris cap.

## Resolved — 2026-06-07

### 2026-06-07 — Improve pass (`/skill-improver improve`) — Dim 3 fix + Dim 2 TOC

- **Baseline blind (Opus): 88/100** (9/9/8/9/9/8/9/9/9/9). Confirmed `work-modeling.md` cleanly **extends** `hierarchy.md` (zero shared 8-grams; defers to it 7×), **no Boris caps** (the 23 numbered lines are reference enumerations — principles/levers/anti-patterns — not invocation flow), **no staleness cap** (all sources `Verified 2026-06-07`).
- **Iter 1 (Dim 3 Writing Style 8→9):** the new content reintroduced **9 second-person slips** ("you'll estimate", "getting your own job done", "you promote", "You can't enumerate", …) against the skill's imperative standard (the prior pass had purged body second-person). Converted all to imperative/objective across `work-modeling.md` + the SKILL.md "Decompose large work" section; grep now **0** (only the deliberately-preserved Excel-aphorism quote remains). KEEP.
- **Final blind (Opus): 87/100** — Dim 3 confirmed **8→9** ("effectively flawless"). The 88↔87 total is **inter-scorer variance** on untouched subjective dims (Dim 4/7/10 each wobbled ±1 between the two independent Opus runs), not a regression. Top finding: the two >100-line references lack an in-file TOC.
- **Iter 2 (Dim 2):** added a one-line **Contents** TOC to `work-modeling.md` (219 lines) — the final blind's #1 recommendation, rubric-prescribed for >100-line references. KEEP. (Not re-blinded: a pure rubric-prescribed TOC-add against ±1 inter-scorer noise.)
- **Converged** in the 87–88 band (excellent; no dimension below 8). Remaining levers are cosmetic (bold/em-dash density) → Open.

### 2026-06-07 — Trigger pass (`/skill-improver trigger`) — no mutation needed

- **Extended the eval set** `references/trigger-evals.json` 14 → **20 queries**: +5 decomposition positives ("break down a big cluster upgrade into issues", "register a multi-week migration", "30-server rollout: one epic or many", "epic with prep + follow-ups", "how many issues to split a big migration into") + 1 jira-cli decoy negative ("batch create issues from the CLI"). Persisted for future runs (kept a pure array — run history lives here, not in the JSON).
- **Baseline Haiku (holdout 0.4): train 12/13, test 6/7.** 4/5 decomposition positives already fired 1.00 (overlap with the existing "epic" / "where should this work go" triggers); the 2 "misses" were the **known Haiku artifact** ("is this an epic" — Opus 1.00) and one borderline ("how many issues split into" 0.33).
- **Candidate** (decomposition triggers added, drafted at 1530/1536): **Haiku train 12/13, test 6/7 — NO lift.** Per the simplicity criterion (equal score, not simpler) → candidate **discarded**; frontmatter left at the validated **1531/1536** (untouched all session).
- **Decisive Opus probe** (focused 8-query decomposition set, `--model opus`): **baseline 8/8.** All 5 decomposition positives **and** "is this an epic or a story?" fire **1.00 on Opus** with the *unchanged* frontmatter; both jira-cli decoys decline 0.00 (no over-trigger). **Finding: the existing frontmatter already reaches decomposition queries on the user's real model** (the epic/story/where-does-work-go triggers overlap the decomposition phrasings) — explicit decomposition triggers are unnecessary. The drafted explicit-trigger version is recorded here as a fallback only if real-session under-triggering is ever observed.

### 2026-06-07 — Added work-modeling.md (the decomposition layer) from deep research

- **Gap:** the skill answered the *vertical* level question (`hierarchy.md` — "what level is THIS one item") but had no *horizontal* decomposition method — how to break one large multi-week initiative into a legible, ordered issue set. Surfaced by a real user need (registering a weeks-long, prerequisite-heavy ops upgrade so progress is trackable).
- **Research:** `/autoresearch research` (STORM, 8 agents, depth 2) → `autoresearch/results/jira-work-decomposition-research-2026-06-07.md`. High confidence; primary-source on DC mechanics + agent scaffolding (read directly from the connected `mcp-atlassian` + `jira-cli` source).
- **Added `references/work-modeling.md`:** WBS spine (100% rule, work package, **rolling-wave / planning package**, milestone=fixVersion, scope-vs-sequence as two views); the **grain rule** (issue→sub-task→checklist→**nothing**, with the ITIL-Standard-Change + SRE-toil floor for "nothing"); the **three axes** (value-slice / phase / wave) + combine; **ordering as a dependency-link overlay** (shared-by-all dep → one gating task); the **assessment→issue-set** table (already-fine→nothing; severity decides 1:1-vs-grouped); a **per-domain generality table** (software / infra / data-eng / business); **DC progress visibility** (epic bar = direct children only; AR has no native critical path; Timeline is Cloud-only); **agent scaffolding** (the `jira_batch_create_issues` can't-link-inline silent gap → multi-pass; deterministic-label idempotency; READ_ONLY_MODE); 8 anti-patterns.
- **SKILL.md wiring:** new "Decompose large work — one initiative into an ordered issue set" body section (after the hierarchy section); read-next table row; dread-playbook row ("a weeks-long effort is impossible to track"); anti-pattern #11.
- **sources.md:** new "Work modeling / decomposition" section (~27 anchors, all `Verified 2026-06-07`).
- **Deliberately NOT done:** frontmatter/triggers (1531/1536 cap) — deferred to the trigger pass logged under Open. Body edits can't affect triggering.

### 2026-06-07 — Improve + Freshen (`/skill-improver improve and freshen`)

- **Result: blind baseline 84 → blind final 89** (self cold 78 → 90). 2 kept improve iterations + 1 freshen pass, 0 discards. Baseline + final blind validation both run (Opus); final bias check aligned (no dimension self ≥ blind+2).
- **Iter 1 (Dim 3 Writing Style 7→9, Pattern 3.1):** converted 11 second-person "you/your" slips in SKILL.md body to imperative/objective voice; the single remaining "your" is inside a verbatim quoted aphorism ("if someone is exporting to Excel, your SSOT is already broken") — correctly preserved.
- **Freshen (Dim 9 Domain Accuracy 6→9):** the staleness cap was a *format* technicality (single header date, no per-row markers), not stale content. Re-probed the 3 most decay-prone claims online — all **`fresh`**:
  - DC latest **11.3.7 (2026-06-03)**, LTS **11.3→Dec 3 2027 / 10.3→Dec 5 2026**, Server EOL 2024-02-15 (endoflife.date) ✓
  - DC EOL milestones **2026-03-30 / 2028-03-30 / 2029-03-28** (atlassian.com/licensing) ✓
  - `mcp-atlassian` repo live (not archived), latest release **v0.21.1** 2026-04-10; skill pins no version → no drift ✓
  - Stamped a per-row `Verified` column (2026-06-07) on all **65** source rows → rubric staleness grep now reads oldest = 2026-06-07 (age 0), cap lifted. Zero `version-drift` / `deprecation` / `broken` findings.
- **Iter 2 (Dim 6 Simplicity →9, simplification keep):** collapsed the redundant role-reinterpretation bullet block in `non-software.md` (duplicated `hierarchy.md`'s per-domain role table) into one tight paragraph + pointer; ~5 lines removed, no information lost.
- **Caps checked clean:** Boris model-version-compensation = 0 matches; the 22 numbered lines are enumerated reference content (principles / levers / anti-patterns), not invocation-flow scaffolding → no Dim 6 Boris cap; name/description pass `skills-ref` spec validation.

### 2026-06-07 — Trigger mode (`/skill-improver trigger`)

- **Result: baseline 12/14 → final 14/14** (Opus). Train 9/9, test 5/5. 1 kept iteration, 0 discards.
- Mutation (Pattern T5 rebalance + T1 front-load): fixed `description` over the 1024 hard cap (1250→668) and combined over the 1536 listing cap (2593→1532); front-loaded the "is this an epic, a story, a task, or a sub-task?" trigger.
- Fixed misses: "too many required fields" (0.33→1.00); "is this an epic or a story?" (Haiku 0.00 → Opus 1.00, Haiku artifact). All 6 negatives clean (no over-trigger; jira-cli + Cloud decoys decline). Eval set saved to `references/trigger-evals.json`.

### Not directly probed (co-installation)

The trigger probe isolates one skill per run, so `jira-best-practices` vs `jira-cli` competing **in the same session** wasn't tested. From this side the boundary is clean (this skill declines all CLI-mechanics queries). If a real session shows `jira-cli` stealing an advisory query, that's a T6 fix on `jira-cli`'s description, not here.

## Resolved this pass — 2026-08-19 (`/skill-improver freshen`)

- **Freshen (full sweep, 65 source cells).** Bulk liveness probe of every
  resolvable URL plus targeted claim checks on each Tier-A hard fact. **Zero
  drift** — DC 11.3.10 (2026-08-07) still latest with no 11.4 line, LTS
  11.3→2027-12-03 and 10.3→2026-12-05, the DC sunset trio (2026-03-30 /
  2028-03-30 / 2029-03-28), the 800/1,200 custom-field guardrail, and
  Automation-for-Jira free-and-native since JSW DC 9.0 all re-confirmed against
  the live pages.
- **Expanded every shorthand citation into a full resolvable URL — 75 source
  cells rewritten.** This was the root cause of the apparent staleness: elided
  paths (`community.atlassian.com/.../Designing Jira Fields in 2026`), brace sets
  (`JRASERVER-{39215,39009}`), and Atlassian slugs missing their trailing numeric
  ID + `.html` could not be probed, so three consecutive passes left ~85 rows on
  the 2026-06-07 research date. The file now holds 126 unique URLs, 120 of which
  return 200 in one bulk sweep; the sweep command is recorded in the header so the
  next pass is a single command.
- Converted `sources.md` from mixed per-row dates to the single header stamp.
- Two dead references replaced rather than merely flagged: `success.atlassian.com`
  is gone at the DNS level (entire domain, not just the page — it read as a
  timeout, not a 404), repointed at the equivalent `atlassian.com/blog` article;
  and a paused Vercel deployment (HTTP 402) dropped from the Linear-vs-Jira row,
  which keeps two live siblings.
- Two `medium.com` rows recorded as permanent bot-block exceptions (403 to any
  non-browser client).
