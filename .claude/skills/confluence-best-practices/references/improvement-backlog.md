# Improvement backlog — confluence-best-practices

Carries findings across skill-improver runs. Read in Phase 0 (improve) / T0 (trigger) / F0 (freshen); update on completion.

## Resolved — 2026-07-21 (freshen)

- **Two cited bugs were already fixed when the research was done.**
  CONFSERVER-60057 (Closed/**Fixed** 2023-11-14) and CONFSERVER-59747
  (Closed/**Fixed** 2024-10-08) were cited as evidence that large/macro-heavy
  pages "break Synchrony". Both predate the 2026-06-07 research pass, which
  picked up the symptom description without checking resolution.
  `lean-content-and-lifecycle.md` now separates the two things that were
  conflated: the **12-concurrent-editor cap** is a documented product limit and
  stands; "split large pages" is **authoring guidance** (readability, review
  effort, transclusion reuse), not a defect workaround. Added the operational
  consequence — a Synchrony timeout on a current version is a *new* bug, so
  don't hand someone a known-issue link closed years ago.
- **CONFSERVER-31010 re-confirmed** — still `Gathering Interest`, unresolved,
  100 votes, and updated **2026-07-21** itself. "No native page-level archiving
  on DC" holds, 13 years on.
- **DC lifecycle re-checked; all dates unchanged**, but the *consequence* was
  missing: **9.2 LTS has under five months of support left** (EOL 2026-12-10),
  and the 10.2 hop carries a **Java 17 → 21** requirement, so the JVM move is
  part of that upgrade rather than a later task.
- **Latest patch deliberately left unresolved.** The skill recorded 10.2.13
  (2026-06-02) and Atlassian's docs indicate a further 10.2.x around
  2026-07-09, but the release-summary page enumerates only minor lines and the
  exact patch didn't surface. Marked "re-derive from the instance or the 10.2
  release-notes page" in both files instead of substituting a plausible-looking
  number — an invented patch version is worse than an explicit gap.

**Not re-probed:** the Atlassian doc-page URLs and tier-B/C practitioner
sources — they back durable principles rather than dated facts.


## Open

_None._ The skill has been through trigger, improve, and freshen modes and converged cleanly (final blind **90/100**, self/blind aligned, no dimension below 8, no Boris caps). The 24 enumerated lines in the SKILL.md body are reference content (5 prime-directive principles, 6 lean levers, 11 anti-patterns) — not invocation-flow scaffolding — so no Dim 6 Boris cap; `name`/`description` pass spec validation; `sources.md` is fully per-row dated (no Dim 9 staleness cap).

Cosmetic-only note (deliberately NOT Open per the backlog rules — future-risk, not attempted-and-blocked work):
- Combined `description` + `when_to_use` = **1,523 / 1,536** chars — ~13 chars of headroom against the listing cap. Not a current defect (trigger converged Opus 20/20 at this length); any *future* trigger-phrase addition must shorten the `description` half first.

## Resolved this pass

### 2026-06-07 — Improve + Freshen (`/skill-improver improve and freshen`)

- **Result: blind baseline 86 → blind final 90** (self/blind aligned at both ends; no dimension with a 2+ self-vs-blind gap). 2 kept improve iterations + 1 freshen pass + the Phase-6 Dim-8 fix; 0 discards.
- **Iter 1 (Dim 3 Writing Style 8→10, Pattern 3.1):** converted the 2 second-person slips in the SKILL.md body to objective voice — "If unsure which you're on… tells you" → "To tell which applies, check…" (Cloud-vs-DC guard) and "note you cannot move pages…" → "note that pages cannot be moved…" (lean-content lever 5). Body now has zero second-person; blind scored Dim 3 = 10. (Reference-file `you/your` occurrences left as-is: they are verbatim Atlassian quotes — e.g. info-architecture "folders into which you can put your work" — URLs, or imperative-adjacent agent prose.)
- **Iter 2 (Dim 6 Simplicity, simplification keep):** merged the redundant third sentence of prime-directive principle #3 ("The same moves serve the human reader and the RAG/agent retriever") into the prior sentence with an em-dash — equal information, one fewer sentence.
- **Freshen (Dim 9 Domain Accuracy 8→9):** independently re-probed the 4 most decay-prone, load-bearing facts (the rest were web-verified the same session during creation) — all **`fresh`**, zero content mutations:
  - DC latest **10.2.13 (2026-06-02)**, LTS **10.2→2027-12-02 / 9.2→2026-12-10**, 8.5 EOL'd 2025-12-15, Server EOL 2024-02-15, 8.6+ DC-only (endoflife.date) ✓
  - DC sunset milestones **2026-03-30 / 2028-03-30 / 2029-03-28**, Bitbucket exception (atlassian.com/licensing) ✓
  - **CONFSERVER-31010** "Add ability to Archive individual Pages" still **Gathering Interest / Unresolved** (100 votes) → DC has no native page archiving ✓
  - DC-EOL announcement date **2025-09-08** confirmed (izymes.com 2025-09-09 + corroborating coverage) — a WebFetch fast-model "2024" hedge was a misread ✓
  - `sources.md` rows already carry per-row `Verified: 2026-06-07` (age 0) → no staleness cap; no re-stamp needed.
- **Phase 6 (Dim 8 Internal Consistency 8→9):** the final blind agent flagged that this backlog file previously carried stale self-descriptions ("body 183 lines"; "sources.md carries a single header date rather than per-row Verified stamps") that contradicted the skill's actual state. Rewriting this file to the accurate current state resolves that Dim-8 deduction.
- **Caps checked clean:** model-version-compensation grep = 0 matches; numbered lines are enumerated reference content (no Dim 6 Boris cap); name + description pass `skills-ref`-equivalent validation. (Note: `when_to_use` is a Claude Code runtime field, NOT in the portable Agent Skills base spec — see [[feedback_skill_trigger_tooling]]; the skill is consumed in-repo, so this is correct, and skill-creator's packager rejecting it is a known stale-validator bug, anthropics/claude-code#33724.)

### 2026-06-07 — Trigger mode (`/skill-improver trigger`)

- **Result: Opus 20/20 (10/10 positives fire · 10/10 negatives decline). Converged at baseline; 0 mutations.** Haiku screen 19/20 — the lone miss (readability positive "restructure this giant runbook" at 0.33) was confirmed a Haiku artifact (Opus runs×5 → 1.0). Eval set saved to `references/trigger-evals.json` (20 queries, `source`-tagged). All sibling/Cloud-only/adjacent decoys declined — boundary with the jira siblings clean from this side.

### Not directly probed (co-installation)

The trigger probe isolates one skill per run (`--setting-sources project`), so `confluence-best-practices` vs the live `jira-*` siblings competing **in the same session** wasn't tested. From this side the boundary is clean (all jira/mcp/Cloud-only decoys declined). If a real session shows a sibling stealing a Confluence advisory query, that's a T6 cross-skill fix on the relevant description, not here.
