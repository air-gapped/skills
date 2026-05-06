# Improvement Backlog — keycloak-iam

Skill-improver carries open ceiling findings forward across runs. Items here either could not be fixed in a single iteration (multi-file restructure, requires author judgment) or were proposed and discarded.

## Open

| # | Title | Dim | Files | Why deferred |
|---|-------|-----|-------|--------------|
| 1 | Reference-file second-person sweep | Dim 3 (9→10) | `references/security-hardening.md` (~17 remaining hits), `k8s-deployment.md` (17), `upgrade-and-backup.md` (14), `integration.md` (11), `observability.md` (~9), `server-config.md` (~8) | Volume (~76 remaining occurrences across 6 files) makes single-iteration completion impractical. The loop applied 2 conversions in `security-hardening.md` (Password History row, Digits/Lowercase/etc row) before stopping; the rest remain. Each occurrence is a minor reader-addressing slip ("if you have", "your hostname", "you can", "if you must") — convertible mechanically to imperative or third-person. Estimated +1 to Dim 3 if completed. |

## Resolved this pass

Run date: 2026-05-06 — modes: `improve` + `freshen`.

| # | Iteration | What changed | Score impact |
|---|-----------|--------------|--------------|
| 1 | iter 1 | **Pattern 1.5** — split frontmatter into `description` (250 chars, was 1466) + `when_to_use` (819 chars). Resolved the Dim 9 hard-fail spec violation (description > 1024 char cap). | Dim 1 6→8, Dim 9 3→6 |
| 2 | iter 2 | Created `references/sources.md` with `Last verified: 2026-05-06` on all major URLs. Resolved Dim 9 staleness cap. | Dim 9 6→9 |
| 3 | iter 3 | **Pattern 3.1** — removed 4 second-person slips in `SKILL.md` (lines 115, 139, 167, 168). | Dim 3 7→9 |
| 4 | iter 4 | Pattern 3.1 partial — converted 2 reader-addressing rows in `security-hardening.md`. Full sweep deferred (see Open #1). | (none on the metric, but progress toward Dim 3 ceiling) |
| 5 | freshen | Probed critical refs: 26.6.1 still latest stable (`gh release list`), `/operator/rolling-updates` alive (HTTP 200), `keycloak-k8s-resources` tag 26.6.1 contains expected manifests (`kubernetes.yml`, both CRDs). Classified all probed refs as `fresh`; no mutations. | (none — sources.md `Last verified:` already 2026-05-06) |

## Final scores

- Self-final: **90/100** (stop condition: ≥90 total, all dims ≥7)
- Blind agent final (Opus): **93/100** — no dimensions with 2+ gap → scores aligned, self conservative

| # | Dim                    | Self | Blind |
|---|------------------------|------|-------|
| 1 | Trigger Precision      |  8   |   9   |
| 2 | Progressive Disclosure |  9   |  10   |
| 3 | Writing Style          |  9   |   9   |
| 4 | Actionability          |  9   |   9   |
| 5 | Completeness           |  9   |   9   |
| 6 | Simplicity             |  9   |   9   |
| 7 | Resource Quality       |  9   |   9   |
| 8 | Internal Consistency   |  9   |   9   |
| 9 | Domain Accuracy        |  9   |  10   |
|10 | Differentiation        | 10   |  10   |

Boris Alignment Check: NO caps trigger. Pro-pattern flagged: routing cheatsheet + "source of truth" pointer (goal+tool-pointer shape).

## Notes for future runs

- Re-run `freshen` quarterly or after Keycloak minor releases (current 26.6.1 → next is 26.7.x sometime in summer 2026). The Dim 9 staleness cap kicks in after 90 days from `Last verified:` (2026-05-06).
- The trigger-mode loop (`/skill-improver trigger keycloak-iam`) was attempted via the `skill-creator`'s description optimizer in a prior session and blocked by (a) no `ANTHROPIC_API_KEY` and (b) the eval mechanism not detecting triggers when the skill is already installed under its real name. Manual `claude -p` testing confirmed the skill triggers correctly on representative queries. If trigger drift is suspected after this run, run `philosophy` mode first to spot scaffolding decay before reaching for the full trigger probe.
