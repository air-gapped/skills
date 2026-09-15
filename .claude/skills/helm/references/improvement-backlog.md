# Improvement Backlog — helm skill

Tracks issues attempted during skill-improver passes that could not be applied in
a single atomic iteration, plus what each pass actually resolved.

## Resolved — 2026-09-15 (ranked last by its own recon, closed)

- **"Common render errors" table — CLOSED, decided against.** The entry records
  the gain as "marginal (Dim 5 already 9; +1 cosmetic)", warns it "risks Dim 6
  (Simplicity)", and says recon "ranked it last". An item carrying its own
  negative verdict is not blocked on anything.
- Worth noting the alternative that now exists: `skill-improver`'s
  `check-shell-fences.py` and `check-yaml-fences.py` catch a class of render
  breakage mechanically, which is a better use of the same effort than prose
  about errors a parser can find.

## Open

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

## Resolved — 2026-08-26 (freshen + measured finding)

Probed the 11 release-feed rows and all 8 CI action pins. **All eight SHAs still
resolve** — no repeat of the 2026-07-21 phantom-SHA finding. The defect this pass
is the same class one level down: a pinned **tag**.

- **`rev: v0.23.3` for `dadav/helm-schema` (`testing-ci.md`) does not exist.**
  That repo tags without a `v` prefix (`0.23.5`, `0.23.4`, …); `v0.23.3` returns
  404. A pre-commit block pinned this way fails to resolve, exactly like a bad
  SHA — and version-only checking never catches it, because the *version* was
  real. Fixed to `0.23.5`, and `sources.md` now states tag resolution as a
  standing requirement alongside SHA resolution, with the per-repo format noted
  (helm-docs `v`-prefixed, helm-schema not).
- **Version drift, both released in the 48h before this pass:** dadav/helm-schema
  0.23.4 → **0.23.5** (2026-08-24, also in `chart-structure.md`); release-please
  v17.11.1 → **v17.11.2** (2026-08-24).
- **Confirmed unchanged:** helm v4.2.4 / v3.21.4, helm-unittest v1.1.2, helmfile
  v1.7.4, kubeconform v0.8.0, cosign v3.1.3 (v2.6.5), helm-docs v1.14.2,
  chart-testing-action v2.8.0, chart-releaser-action v1.7.0, ArgoCD issue #22609
  still OPEN (no activity since 2025-04-22).
- **Swept the other three `rev:` pins** after finding the first — all resolve.
  `pre-commit/pre-commit-hooks` was `v5.0.0` (2024-10) against a current v6.0.0
  (2025-08); bumped, the three hooks used still exist in v6. yamllint v1.38.0 and
  helm-docs v1.14.2 are current. `sources.md` now tracks all four in their own
  table so the next pass checks them.
- **Not probed this pass** (doc pages, no release feed, dates left at 2026-05-28):
  helm.sh/docs, Bitnami common, Flux, OpenShift docs, Renovate docs.

**New gotcha — null defaults + `hasKey`** (`SKILL.md` §5). Measured on seven Helm
binaries (v3.17.3, v4.0.5, v4.1.0, v4.1.1, v4.1.4, v4.2.0, v4.2.4) with a minimal
chart. Whether a chart's own `foo: ~` default survives the values merge flipped
twice inside the v4 line — PR #31644 in v4.1.3, PR #31979 in v4.2.0 — and at
v4.2.4 `cleanNilValues` runs only when the user supplies no values at all, so the
same chart renders differently with and without any `-f`. Upstream helm#32093 is
OPEN with fix PR #32097 unmerged. The documented idiom (a user `-f` null deleting
a *non-null* default) is unaffected and works on every version tested, so the
gotcha is scoped to authors writing null defaults, not to consumers.

**`values.schema.json` did not close its objects** (`chart-structure.md`). The
skill's own example schema listed `properties` and stopped, so a chart built from
it accepts any key it does not name — a consumer's typo renders the default and
reports success. Measured on 3.17.3 and 4.2.4: `--set totallyMadeUpKey=42` and
`--set image.repositry=oops` both exit 0 against the old example, and both exit 1
once `additionalProperties: false` is added. `helm lint`/`template` passing is
therefore not evidence a key is valid.

Two corrections found while writing it, both measured rather than assumed:

- The generator this skill recommends, `dadav/helm-schema`, **already** defaults
  `additionalProperties` to `false`. The hole is in hand-written schemas, not
  generated ones — so the text says which is which instead of blaming generators.
- **Closing the root schema breaks any chart with dependencies.** A subchart's
  values sit under its own name at the parent root, so a bare
  `additionalProperties: false` rejects the subchart and the chart stops
  rendering on both Helm 3 and 4. The section now shows declaring each dependency
  as an open property, verified to restore rendering while still catching a
  root-level typo.

Helm 4 emits different wording for the same failure (`at '/image': additional
properties ... not allowed`), noted so nobody matches on the message text.

**Scope widened to cover the values file from the consuming side**, and
`references/values-porting.md` added.

The skill was named `helm` — the bare tool name, the broadest claim in the repo —
while its description said "NOT for installing or consuming third-party charts".
That clause was never a decision: it landed in the skill's first commit
(`8fc591a`) and was only restated by a cross-reference pass (`aef8f18`). No
trigger measurement, no backlog entry, nothing recording why.

It was also already being violated. Gotcha #5's null-coalescing rule is
values-*merge* behaviour — what a consumer hits — and was admitted on the grounds
that an author causes it. Splitting merge semantics from the porting workflow
would have scattered one mechanism across two skills.

Scope is now: authoring, all of it; consuming, the values file only. Everything
else still routes to `argo-cd-apps` / `openshift-app` /
`k8s-components-checker`, which own different domains rather than the other half
of Helm.

Verified in-session on minimal inputs rather than taken on report: `patch -F3`
exits **0** and silently applies a `hostPort:`-scoped edit to `hostFirewall:`
once upstream deletes the anchor block, while `diff3 -m` and
`git merge-file -p --diff3` both exit 1 and raise the conflict with the base
visible.

`mimir-upgrade` ships `scripts/audit-values.sh` for the product-specific half of
this and should point here. **Blocked, not forgotten:** that skill currently
fails the pre-commit `skillevaluator` gate with
`Semgrep error (exit code 2): Failed to obtain target files from semgrep-core`,
on unmodified content, in both the main checkout and a worktree — so no edit to
it can be committed at all. The same skill passes when copied outside the repo,
so it is a semgrep target-collection problem in-repo, not the skill's content
(10 files, no symlinks, nothing unusual). Add the pointer once that is fixed.

**If this over-triggers**, tune the description with `skill-improver`'s `trigger`
mode — do not re-amputate the scope, which is what happened the first time.

## Resolved — 2026-07-21 (freshen)

Probed 20 refs: 10 tool repos, 8 CI action pins, plus the Helm 4.1/3.21 release
lines. The headline finding is not a version — it is that **two SHA pins pointed
at commits that do not exist.**

- **`sigstore/cosign-installer@3454372b…` (labelled v3.8.2) — no such commit.**
  `gh api .../commits/<sha>` returns 422. Replaced with v4.1.2
  (`6f9f17788090df1f26f669e9d70d6ae9567deba6`, verified).
- **`helm/chart-releaser-action@cae68fefc6b5f367a13b05b6d575c93921f3b899`
  (v1.7.0) — no such commit.** The real v1.7.0 SHA shares only its first 17
  hex chars: `cae68fefc6b5f367a0275617c9f83181ba54714f`. The 2026-05-28 pass
  recorded chart-releaser-action as "Confirmed CURRENT" — it checked the
  *version*, which was and is right, and never resolved the SHA. That is the
  hole this pass closes, and why `sources.md` now states the SHA-resolution
  step as a standing requirement rather than a one-off.
- **All six remaining pins resolved**, but every one was 1–3 majors stale:
  checkout v4.2.2→v7.0.1, setup-python v5.6.0→v7.0.0, setup-helm v4.3.0→v5.0.1,
  login-action v3.4.0→v4.4.0, kind-action v1.12.0→v1.14.0. chart-testing-action
  v2.8.0 unchanged and correct.
- **Breaking-change check on the two risky bumps.** setup-helm v5.0.0 is a
  node20→node24 runtime bump, nothing else. cosign-installer v4 is required for
  cosign v3+, and cosign v3 makes `--bundle` mandatory on `sign-blob` — but this
  skill only signs OCI digests with `cosign sign`/`verify` and never calls
  `sign-blob`, so the bump is safe as written. Recorded in `sources.md` with the
  condition that would change the answer.
- **Tool drift:** helm-unittest v1.1.0→v1.1.1, helmfile v1.5.2→**v1.7.1** (two
  minors), dadav/helm-schema v0.23.3→0.23.4. helm-docs still v1.14.2 — no
  release in two years, so the pin is correct, not stale.
- **Helm itself:** v4.2.0→v4.2.3 (2026-07-09). Added the fact that **Helm 3 is
  still maintained in parallel** — v3.21.3 shipped the same day — so the skill
  no longer reads as though Helm 3 users are on an abandoned line.
- **Rows given versions they lacked:** kubeconform v0.8.0, cosign v3.1.2 (v2
  line still patched at v2.6.4), release-please v17.10.3.

## Resolved — 2026-05-28

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
