# Improvement Backlog — keycloak-iam

Skill-improver carries open ceiling findings forward across runs. Items here either could not be fixed in a single iteration (multi-file restructure, requires author judgment) or were proposed and discarded.

## Open

| # | Title | Dim | Files | Why deferred |
|---|-------|-----|-------|--------------|
| 1 | Reference-file second-person sweep (carried 2026-05-28) | Dim 3 (9→10) | `references/security-hardening.md` (~15 remaining hits), `k8s-deployment.md` (17), `upgrade-and-backup.md` (14), `integration.md` (11), `observability.md` (~9), `server-config.md` (~8) | Volume (~70 remaining occurrences across 6 files) makes single-iteration completion impractical under the one-atomic-change-per-iteration rule. Each occurrence is a minor reader-addressing slip ("if you have", "your hostname", "you can", "if you must") — convertible mechanically to imperative/third-person. Not advanced on 2026-05-28: the iteration budget was spent on the higher-value Dim 9 fabricated-CVE removal and the Dim 8 version propagation, which are correctness fixes that outrank a cosmetic Dim-3 polish. Best tackled one file per iteration in a future `improve` pass. Estimated +1 to Dim 3 if completed. |

## Resolved this pass

Run date: 2026-05-28 — modes: `improve` + `freshen`.

| # | Iteration | What changed | Score impact |
|---|-----------|--------------|--------------|
| 1 | iter (Dim 9) | **Removed fabricated CVE content.** Deleted the invented `CVE-2026-4366` / `CVE-2026-4633` detailed subsections (§9), the `CVE-2026-4633` reference in §4 flows, the unverifiable `#47776` claim in §3, and the whole §12 CVE table (which mixed fabricated 2026 IDs with un-re-verified older IDs). Verified via `gh api .../security-advisories` (recon, 84KB parsed 3 ways) that none of `CVE-2026-4366/4633/3429` exist in the feed. | Dim 9 5→8 (removes actively-misleading invented security identifiers) |
| 2 | iter (Dim 9) | **Replaced §12 with a live-feed procedure** — `gh api repos/keycloak/keycloak/security-advisories` + `gh release view` commands, severity/patched-version cross-check, and section-mapping guidance, instead of asserting any specific CVE IDs. The live 26.6.2 release body (CVE-2026-7504 redirect-URI bypass, CVE-2026-7507 OIDC session fixation, CVE-2026-7571, CVE-2026-37982, CVE-2026-7307, CVE-2026-6856, CVE-2026-37978/79/80/81, CVE-2026-4628/4630, CVE-2026-5588/0636/3505/5598 BouncyCastle, CVE-2026-33870/33871) was confirmed this pass, but encoding a static table re-introduces the staleness/fabrication risk just removed — so the skill points at the feed instead. Preserves Dim 10 differentiation without restating drift-prone IDs. | Dim 9 (supports 5→8), Dim 10 preserved |
| 3 | iter (Dim 9) | **Version bump 26.6.1 → 26.6.2.** Independently confirmed this pass via `gh release list` + `gh api releases/latest` (tag 26.6.2, isLatest:true, published 2026-05-19T12:41:03Z; 26.6.1 published 2026-04-15). Updated SKILL.md L9 intro, L54 latest-stable callout, and version-table 26.6.x row (noting 26.6.2 is a security-fix batch). | Dim 9 (currency) |
| 4 | iter (Dim 8) | **Propagated 26.6.2 across install/image references:** SKILL.md (guardrail #5 image tag, #10 operator pin, Quickstart image + 3 raw-manifest URLs, tag-example L81; softened 2 operator-pitfall lines to "fixed in 26.6.1 … use latest 26.6.x"); k8s-deployment.md (official image tag, 2 Dockerfile FROMs, custom-image-tag suffix, `KC_VERSION`, operator-pin prose, "spec fields in 26.6.x"); assets keycloak-cr.yaml, realm-import-cr.yaml, Dockerfile.optimized (all FROM/tag lines). All Edits returned success. Deliberately LEFT unchanged: accurate "fixed in 26.6.1" history (observability.md, integration.md), generic "26.6.0 → 26.6.1" patch-upgrade examples and feature-version labels in upgrade-and-backup.md/server-config.md, and the historical 26.6.1 release row in sources.md — bumping accurate history would introduce errors. | Dim 8 8→9 (no install-reference drift) |
| 5 | iter (Dim 1) | **Tightened the trailing trigger clause** — replaced the broad "Triggers on IAM/SSO/realm questions … even when Keycloak isn't repeated" with a Keycloak-context-anchored version plus an explicit negative ("do NOT trigger on generic IAM/SSO/OIDC with no Keycloak context — Auth0, Okta, Entra ID, Cognito, from-scratch OAuth"). Frontmatter re-validated: name=keycloak-iam matches dir, description unchanged and <1024 chars, no XML tags. | Dim 1 9→10 |
| 6 | freshen | Re-stamped `sources.md` rows for upstream repo, releases (added 26.6.2 row, demoted 26.6.1 to historical), advisory feed, and k8s-resources to `Last verified: 2026-05-28`. | Dim 9 staleness window reset |

## Resolved 2026-05-06

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
