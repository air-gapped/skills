# Improvement Backlog — argo-cd-apps

Carries open ceiling findings across skill-improver runs. Each entry: title,
affected dim, file:line pointer (or file-set), why it couldn't be applied in
one iteration this run, enough context for a future loop to act on.

## Open

### 1. Inline canonical YAML duplicates content already in references/

- **Dim 2** (Progressive Disclosure)
- `SKILL.md:127-176` (Canonical Application) and `SKILL.md:187-229` (Canonical ApplicationSet)
- Blind reviewer's top recommendation. Both YAML blocks are also covered field-by-field in `references/application.md` and `references/applicationset.md`, but they exist in SKILL.md because they're the highest-traffic surface — every Application/ApplicationSet authoring task starts here.
- Could not apply in one iteration: relocating both is a judgment call between "lean SKILL.md" (drop both, replace with 5-line intent + pointer) vs "fast-reach templates" (keep). The current author chose fast-reach. Future loop could test the lean variant via blind comparison.
- Estimated lift: Dim 2 from 7→8 self / 8→9 blind. SKILL.md drops from 348 → ~250 lines.

### 2. Second-person leakage in reference files

- **Dim 3** (Writing Style)
- `references/version-changes.md:540` ("PRs you'll cite most often"), `references/troubleshooting.md:120, 215, 218`, plus ~50 more across `version-changes.md` and `troubleshooting.md`.
- Loop iter 3 cleared all 10 second-person uses in `SKILL.md` body but did not sweep references/. Sweeping all reference files in one atomic mutation works (same category as iter 3) but blind reviewer's count of "≈1% density across 5326 lines" suggests the cost-benefit is marginal — most are in casual reading-flow contexts ("you deploy a CR") rather than instructional voice.
- Estimated lift: Dim 3 from 9→10 self / 9→10 blind.

### 3. No `paths:` frontmatter despite a tightly file-scoped skill

- **Dim 9** (Domain Accuracy / frontmatter completeness)
- `SKILL.md:1-22`
- Blind reviewer suggested `paths: ["**/argocd/**", "**/Application*.yaml", "**/AppProject*.yaml", "**/ApplicationSet*.yaml"]` — this would tighten triggering on file edits to argo-cd-related YAML and reduce false positives.
- Could not apply in one iteration: the skill is task-flavored ("how do I write an ApplicationSet?") not pure-file-flavored. Adding `paths:` could *miss* triggers on conversational prompts ("set up a multitenant AppProject"). Author judgment needed on whether file-scoped triggering is worth the conversational-trigger cost.
- Estimated lift: Dim 9 from 9→10 if no regression; could regress Dim 1 (trigger recall) on conversational prompts.

### 4. No `scripts/` directory

- **Dim 7** (Resource Quality)
- A useful script: `scripts/check-cve-2026-42880.sh` that runs `kubeconform` or `conftest` against an Application directory and fails on `argocd.argoproj.io/compare-options: IncludeMutationWebhook=true`. The skill recommends this in `SKILL.md` § Critical gotchas #1 but doesn't bundle the implementation.
- Could not apply in one iteration: requires writing and testing real `conftest`/`kubeconform` policies, which is author work.
- Estimated lift: Dim 7 from 8→9.

## Resolved this pass

- **Spec hard-fail: `description` field exceeded 1024-char Agent Skills cap** — split into `description` (938 chars) + `when_to_use` (270 chars), combined 1208 chars under the 1536 listing cap (iter 1).
- **No `references/sources.md` capping Dim 9 at 6** — created with dated index of every cited URL/repo/spec, all `Last verified: 2026-05-06` (iter 2).
- **10 second-person uses in `SKILL.md` body** — converted to imperative/declarative voice (iter 3).
- **9 occurrences of hardcoded absolute author-machine paths breaking portability** — replaced with repo-relative paths (`docs/user-guide/...`) plus a top-level pointer to fetch via `gh api` if the local clone isn't present (iter 4).
- **Verbose paragraph-per-reference "When to load" section** (60 lines) — compressed to dense 8-row table (iter 5). SKILL.md: 391 → 348 lines.

## Final scores (2026-05-06 run)

- Baseline self: 73 / blind: 77
- Final self: 85 / blind: 89
- Delta: +12 self, +12 blind
- 5 iterations, all kept (0 discards), 5 different categories (spec / content / style / portability / simplification)
- No 2+ gap dimensions on final blind check
