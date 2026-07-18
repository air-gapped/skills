# Improvement backlog — redis-to-valkey

Carries ceiling findings across skill-improver runs. Append-only history;
keep prior passes' sections dated below the current one.

## Open

1. **SKILL.md <150-line restructure** (Dim 2: 8 → 9+). Attempted 2026-07-18
   (iter 9): extracting the chart-selection/values-translation summary to
   `references/chart-migration.md` left SKILL.md at ~190 lines (Dim 2 band
   unchanged) while dropping Dim 5 — the frontmatter description promises
   "chart selection tradeoffs" and the extraction moved them out of the
   always-loaded layer. Discarded as net-negative. Breaking through needs a
   deliberate redesign of which summaries must survive a no-references read
   (RDB wall and transfer decision tree are non-negotiable in-body; chart
   tradeoffs and lockdown history are the candidates) — an author-judgment
   tradeoff between Dim 2 and Dim 5, not a one-iteration edit.
   Files: SKILL.md §"Chart selection and values translation",
   §"Why this migration exists", references/chart-migration.md,
   references/airgap-gitops.md.

2. **pitfalls.md cross-file dedup** (Dim 6: 8 → 9). Attempted 2026-07-18
   (iter 10): shortening pitfalls #10/#11 to pointers at
   chart-migration.md broke the file's standalone pre-execution scan-list
   role and introduced reference→reference chains (rubric Dim 2 warns
   against A→B→C). Discarded. The remaining duplication (26379-only
   service, master-set mismatch, failoverWait trap appearing in both
   pitfalls.md and chart-migration.md) is load-bearing: each file serves a
   different read mode (scan-before-execute vs translate-values). Only a
   changed role for pitfalls.md would unlock this.

## Resolved this pass — 2026-07-18

Run: improve+freshen, 10 iterations + 1 bonus, self 77→87, blind 81→88.

- iter 1 (freshen F6): created references/sources.md, 27 rows all
  `Last verified: 2026-07-18` with pins; Dim 9 cap 6→9. Freshen probe
  outcome: 0 stale findings (skill authored same day as its research);
  future-probe queries recorded in sources.md.
- iter 2: combined frontmatter 1716→1524 chars — all triggers and both
  NOT-scope clauses now inside the 1536 listing cap (Dim 1 7→8; blind 9).
- iter 3: zero second-person in SKILL.md (Dim 3 7→9).
- iter 4: TOC added to data-transfer.md (Dim 7 8→9).
- iter 5: prose standardized on "master-set name" (SKILL.md,
  app-cutover.md, pitfalls.md #11); literal chart keys untouched (Dim 8 8→9).
- iter 6: SKILL.md pitfalls quick-index deduplicated against in-body traps
  (Dim 6 7→8).
- iter 7: lockdown detail consolidated behind airgap-gitops pointer
  (keep-simplification).
- iter 8: `SENTINEL ckquorum` validation added to runbook step 2 —
  probe-verified against valkey 9.1.0 sentinel.c before mutation (Dim 4 8→9).
- iter 9: DISCARD (see Open #1).
- iter 10: DISCARD (see Open #2).
- bonus: 3 second-person slips in reference files fixed (final blind
  finding #3).
