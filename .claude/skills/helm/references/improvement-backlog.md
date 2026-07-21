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
