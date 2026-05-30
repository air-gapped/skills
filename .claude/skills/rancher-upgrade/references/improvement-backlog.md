# improvement-backlog — rancher-upgrade

Cross-run memory for `skill-improver`: read at the start of each run, updated at the end.
**Open** = issues the loop *attempted as a hypothesis and could not apply in one iteration*
(ceiling discards, multi-file restructures). Open is NOT a wishlist. **Resolved this pass** =
changes that actually landed.

## Open

- **Dim 6 (Simplicity) ceiling — the cross-cluster ordering rule is stated at three altitudes.**
  Iteration 6 (2026-05-30) attempted to dedup it and **discarded**. "Management Rancher before any
  downstream k8s *minor* bump" appears as a mental-model concept (SKILL.md § two coupled axes), a
  workflow step (SKILL.md §4), standing House Rule #5, and once in `prereqs-and-ordering.md`. Each
  has a distinct function — concept / procedure / compaction-surviving standing rule
  (improvement-pattern 3.2) — so a one-line collapse loses force with no score gain (blind validator
  scored Dim 6 = 8, "non-repetitive"). Breaking past 8 needs an author decision on collapsing to one
  canonical statement + cross-refs across ≥3 locations — a restructure, not a single-iteration mutation.

## Resolved this pass (2026-05-30 · improve + freshen · blind 81 → 92, self 76 → 90)

- Dim 9 hard-cap removed: `description` 1656 → 973 chars, split into `description` + `when_to_use`.
- Dim 9 staleness cap removed: added `references/sources.md` (14 rows, `Last verified: 2026-05-30`).
- Dim 1: combined `description`+`when_to_use` trimmed 1632 → 1514 (under the 1536 listing cap).
- Dim 3: removed the single second-person slip.
- Dim 4 / Dim 5: added a plan-output shape to SKILL.md §5.
- **cert-manager 2.11/2.12/2.13 — resolved (no longer UNVERIFIED).** Probed the SUSE support matrix
  (no cert-manager row) → derived the ranges instead by intersecting the two grounded k8s-window
  files: 2.11→cert-manager 1.17–1.18, 2.12→1.18–1.19, 2.13→1.19–1.20 (`prereqs-and-ordering.md`).
- freshen: no-op confirmed — `releases/latest` unmoved (`v2.14.2`), sources fresh (0 days).

## Companion follow-ups — DONE (in `k8s-components-checker/references/compat/rancher.md`, 2026-05-30)

- Added the air-gap CAPI `capi-controller-manager` 2.13 blocker (#52816) to the § 2.13 Breaking list.
- Clarified the Google OAuth fix: main issue #54387 + v2.14 backport #54416 (both CLOSED, gh-verified).
  (The Fleet "off-by-one" the doc-research flagged was NOT a change — that file was already correct.)
