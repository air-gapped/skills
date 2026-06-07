# Improvement backlog — jira-best-practices

Carries findings across skill-improver runs. Read in Phase 0 (improve) / T0 (trigger) / F0 (freshen); update on completion.

## Open

_None._ The skill has been through trigger, improve, and freshen modes and converged cleanly (self 90 / blind 89, no dimension below 8, no Boris caps, no staleness cap). No ceiling hits, no multi-file restructures pending, no cross-skill (T6) conflicts.

Cosmetic-only notes (deliberately NOT Open per the backlog rules — these are future-risk / wishlist, not attempted-and-blocked work):
- `description` sits at 1,532 / 1,536 combined chars — effectively zero headroom; any *future* trigger-phrase addition would truncate. Not a current defect (trigger mode converged 14/14 at this length); if more triggers are ever needed, shorten the `description` half first.
- Some body prose is bold/em-dash dense (e.g. prime-directive, lean-levers). A future cosmetic pass could trim styling for a marginal Dim 6 gain; content is correct.

## Resolved this pass

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
