# Improvement Backlog — argo-cd-apps

Carries open ceiling findings across skill-improver runs. Each entry: title,
affected dim, file:line pointer (or file-set), why it couldn't be applied in
one iteration this run, enough context for a future loop to act on.

## Resolved — 2026-07-21 (freshen)

- **Rebased the version picture.** Latest stable v3.4.3 → **v3.4.5**
  (2026-07-09); maintenance v3.3.11 → **v3.3.12** (2026-06-18); v3.2.12 and
  v3.1.16 also active.
- **Documented v3.5 while it is still in RC** (rc1 2026-06-16, rc2 2026-07-01),
  read from `docs/operator-manual/upgrading/3.4-3.5.md` **at tag v3.5.0-rc2** —
  a release artifact, whereas the 2026-05-06 authoring pass only had the
  in-development version on `main`. Documented ahead of GA deliberately: the
  headline is a **Helm 4.2.0 upgrade that breaks plain-HTTP OCI registries**,
  which is a planning problem, not an upgrade-day problem. Specifically:
  dependency repos on plain-HTTP OCI now need explicit registration where Helm
  v3 handled them transparently, and combining
  `--insecure-skip-server-verification` with `--insecure-oci-force-http` makes
  Helm v4 silently drop `--plain-http` with **no workaround upstream**. Also
  captured React 19 for UI extensions, the `EventList` gRPC type change (CLI
  unaffected, REST unaffected, generated gRPC/OpenAPI clients affected),
  impersonation extending to all server operations with a required-verbs table,
  and SSH `known_hosts` moving to `argocd-ssh-known-hosts-cm` for
  credential-less repos.
- **Closed a recorded ambiguity in "Note on conflicting sources".** It said to
  treat impersonation-on-server-operations as a 3.4 change "unless GA notes say
  otherwise", reasoning from PR merge dates. Resolved by reading the *shipped
  docs* instead: `3.3-3.4.md` at tag **v3.4.5** does not mention impersonation
  at all, while `3.4-3.5.md` at **v3.5.0-rc2** documents it with a full RBAC
  table. It is a **3.5** change. Also corrected the arithmetic in that note —
  PR #26898 (2026-04-02) landed *after* v3.4.0-rc1 (2026-03-16), not four weeks
  before it. Reasoning from merge dates was the error; the release artifact is
  the authority.
- **Security advisories re-probed: genuinely no change.** Nothing newer than the
  two 2026-05-13 entries. Recorded as a verified non-event rather than left
  ambiguous.
- **Added a method note** to the currency section: enumerate
  `gh release list -R argoproj/argo-cd --limit 25` and reason per minor line;
  do not read `releases/latest`, which GitHub marks by recency, so a patch on an
  older line can outrank a newer minor.

**Not attempted:** both structural Open items below (SKILL.md YAML relocation,
second-person leakage) — unchanged reasoning, and this pass's budget went to the
v3.5 material.

## Open

### 1. Inline canonical YAML in SKILL.md — relocate to references (carried 2026-05-29)

- **Dim 2** (Progressive Disclosure) / **Dim 6** (Simplicity)
- `SKILL.md:127-176` (Canonical Application) and `SKILL.md:187-229` (Canonical ApplicationSet)
- Blind reviewer's top recommendation: drop both YAML blocks from SKILL.md (replace with a 5-line intent + pointer) to shed ~98 body lines.
- **Why it is NOT a one-iteration atomic change (corrected 2026-05-29):** `references/application.md` line 5 explicitly says "Canonical full example lives in SKILL.md § Canonical Application — **not repeated here**", so the Application YAML is NOT currently duplicated in the reference. Relocating it means (a) MOVING the block into `application.md`, (b) rewriting that "not repeated here" cross-pointer, and (c) deleting from SKILL.md + adding a back-pointer — a 3-edit multi-file restructure across two files, not a pure relocation. The author also deliberately chose fast-reach (the highest-traffic authoring surface starts at these blocks). A future loop should test the lean variant via blind A/B and, if kept, do the full move+rewrite.
- Estimated lift: Dim 2 from 8→9 / Dim 6 7→8. SKILL.md drops from 350 → ~250 lines.

### 2. Second-person leakage in reference files (carried 2026-05-29)

- **Dim 3** (Writing Style)
- `references/version-changes.md:540` ("PRs you'll cite most often"), `references/troubleshooting.md:120, 215, 218`, plus ~50 more across `version-changes.md` and `troubleshooting.md`.
- Loop iter 3 cleared all 10 second-person uses in `SKILL.md` body but did not sweep references/. Sweeping all reference files in one atomic mutation works (same category as iter 3) but blind reviewer's count of "≈1% density across 5326 lines" suggests the cost-benefit is marginal — most are in casual reading-flow contexts ("you deploy a CR") rather than instructional voice.
- Estimated lift: Dim 3 from 9→10 self / 9→10 blind.

### 3. No `paths:` frontmatter despite a tightly file-scoped skill (carried 2026-05-29)

- **Dim 9** (Domain Accuracy / frontmatter completeness)
- `SKILL.md:1-22`
- Blind reviewer suggested `paths: ["**/argocd/**", "**/Application*.yaml", "**/AppProject*.yaml", "**/ApplicationSet*.yaml"]` — this would tighten triggering on file edits to argo-cd-related YAML and reduce false positives.
- Could not apply in one iteration: the skill is task-flavored ("how do I write an ApplicationSet?") not pure-file-flavored. Adding `paths:` could *miss* triggers on conversational prompts ("set up a multitenant AppProject"). Author judgment needed on whether file-scoped triggering is worth the conversational-trigger cost.
- Estimated lift: Dim 9 from 9→10 if no regression; could regress Dim 1 (trigger recall) on conversational prompts.

### 4. No `scripts/` directory (carried 2026-05-29)

- **Dim 7** (Resource Quality)
- A useful script: `scripts/check-cve-2026-42880.sh` that runs `kubeconform` or `conftest` against an Application directory and fails on `argocd.argoproj.io/compare-options: IncludeMutationWebhook=true`. The skill recommends this in `SKILL.md` § Critical gotchas #1 but doesn't bundle the implementation.
- Could not apply in one iteration: requires writing and testing real `conftest`/`kubeconform` policies, which is author work.
- Estimated lift: Dim 7 from 8→9.

## Resolved this pass (2026-05-29 freshen + improve)

- **CVE-2026-42880 patched-version matrix was WRONG** — claimed patched `v3.3.8 / v3.2.10 / v3.1.15`; actual is `v3.3.9 / v3.2.11` per GHSA-3v3m-wc6v-x4x3 (advisory 2026-05-01), and v3.3.8 predates the advisory. Corrected in `SKILL.md` gotcha #1, `references/projects-rbac.md` §8, `references/version-changes.md` CVE-callouts. Security-critical: the old text would have left an operator on an unpatched build (iter 1).
- **Version-currency stale** — "v3.3.9 (latest stable) / v3.4 (RC)" corrected to "v3.4.x GA, latest stable v3.4.3 (2026-05-28); v3.3 maintenance latest v3.3.11" in `SKILL.md` intro + `references/version-changes.md` currency note + v3.4 section header (iter 2).
- **Two post-authoring CVEs missing** — added CVE-2026-45737 (medium, SSD Secret extraction via sensitive annotations, GHSA-rg3g-4rw9-gqrp, 2026-05-13) and CVE-2026-45738 (high, stored XSS dev→admin via Application link annotations, GHSA-h98r-wv3h-fr38, 2026-05-13) to `references/version-changes.md` CVE-callouts and `references/projects-rbac.md` §8 secrets section (iter 3).
- **Top-of-file ToC missing on the four reference files >100 lines** — added a verified `## Contents` block (anchors generated from `grep -n '^## '` headings) to `references/sync.md` (12 sections), `references/troubleshooting.md` (12 + appendix), `references/repo-layout.md` (12 + citation index), `references/applicationset.md` (7 sections). Satisfies the rubric reference-depth ToC rule for partial reads (iter 4, Dim 2).
- **sources.md restamped 2026-05-29** — freshen-pass header rewritten with the probe findings; Releases + Security-advisories + local-clone rows re-stamped `Last verified: 2026-05-29` with the v3.4.3 pin and the four CVEs (freshen).

## Prior run — Final scores (2026-05-06 run)

- Baseline self: 73 / blind: 77
- Final self: 85 / blind: 89
- Delta: +12 self, +12 blind
- 5 iterations, all kept (0 discards), 5 different categories (spec / content / style / portability / simplification)
- No 2+ gap dimensions on final blind check
