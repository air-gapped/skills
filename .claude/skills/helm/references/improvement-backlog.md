# Improvement Backlog — helm skill

Tracks issues attempted during skill-improver passes that could not be applied in
a single atomic iteration, plus what each pass actually resolved.

## Open

- **Add a "Common render errors" troubleshooting table** — Dim 5 — `references/testing-ci.md` (or a new section)
  — Closes the one acknowledged completeness gap (nil-pointer on missing nested
  values, indentation drift from template-vs-include, YAML type-coercion). Deferred:
  the gain is marginal (Dim 5 already 9; +1 cosmetic) and a net addition risks
  Dim 6 (Simplicity); recon ranked it last, below the cap-lifting and freshen fixes.
  Apply as a small table only, after a fresh read.

## Resolved this pass

- Created `references/sources.md` with a dated per-URL table (16 rows, all stamped
  Last verified 2026-05-28) — lifts the Dim 9 absent-sources.md hard cap (ceiling
  was 6; now uncapped since oldest date is within 90 days).
- Updated Helm version line `SKILL.md:39` `v4.1.3` → `v4.2.0 (latest patch line
  v4.1.4 on the 4.1 series)` (Dim 9 freshen).
- Bumped helm-unittest `testing-ci.md:39` `v1.0.3 (October 2025)` → `v1.1.0` (Dim 9 freshen).
- Bumped helmfile `testing-ci.md:594` `v1.3.1 (February 2026)` → `v1.5.2` (Dim 9 freshen).
- Bumped dadav/helm-schema `testing-ci.md:708` and `chart-structure.md:539`
  `v0.23.0` → `v0.23.3` (Dim 9 freshen).
- Re-pinned helm/chart-testing-action `testing-ci.md:358` `v2.7.0`
  (e6669bc…) → `v2.8.0` (SHA 6ec842c01de15ebb84c8627d2744a0c2f2755c9f, verified
  via `git/refs/tags/v2.8.0` → object.type=commit) (Dim 9 freshen).
- Split frontmatter into a what-only `description` (third-person opener "This skill
  should be used when…") plus a `when_to_use` trigger field (Pattern 1.5),
  `SKILL.md` frontmatter (Dim 1, 7 → 8).
- Confirmed CURRENT (no change needed): helm-docs v1.14.2, chart-releaser-action
  v1.7.0, ArgoCD OCI cosign issue #22609 still open.
