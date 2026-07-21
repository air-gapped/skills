# Improvement Backlog — openshift-app

Tracks improvement hypotheses attempted but not landed in one atomic iteration, plus changes the metric registered this pass. Open is a work-not-done log, not a wishlist.

## Open

- **Per-file tables of contents for the 7 reference files** (Dim 7) — `references/{container-images,packaging-formats,security,cicd-gitops,operations,gotchas,disconnected}.md`. Each file exceeds the 100-line TOC threshold (226-454 lines) but none carries a top-of-file TOC. Not applied in one iteration: adding a TOC to each of 7 files requires reading each file's exact heading structure and is a 7-file change, exceeding the one-atomic-change-per-iteration rule. Do one file per iteration next pass.
- **Merge the two top-of-file routing tables** (Dim 6) — `SKILL.md` Quick Decision Guide (~L18-30) and Additional References (~L223-233). The two tables overlap slightly in intent (task-routing vs file-contents). Merging into one canonical navigation surface is a structural rewrite of two sections that also risks dropping the distinct in-file anchors (#container-image-essentials, #packaging-decision-matrix) the Quick Decision Guide carries; deferred to avoid conflating relocation with prose rewrite in a single step.
- **Inline SCC validation one-liner** (Dim 4) — `SKILL.md` next to the restricted-v2 securityContext block (~L76-85). Add a confirm-it-worked command (e.g. `oc get pod NAME -o jsonpath='{.spec.containers[0].securityContext}'` and the assigned UID via `oc get pod NAME -o jsonpath='{.spec.securityContext.runAsUser}'`). This is an additive content change; deferred this pass to keep the pass deletion-biased and because exact placement needs a fresh read of the surrounding block to avoid duplicating guidance already in references/security.md.

## Verify next freshen (recon flagged 'unverifiable' — live docs were blocked)

**Three of the four original items were resolved on 2026-07-21** — see the
Resolved section below. What remains:

- **OCP 4.22's bundled Helm version** — `SKILL.md` §"Helm 4 Is NOT Usable with
  ArgoCD on OpenShift", `references/packaging-formats.md`. The 4.19-4.21
  "ships Helm 3 / web terminal v3.17.1" claim was carried forward unchanged;
  4.22 is now GA but `docs.redhat.com/.../4.22/...` returns **403** to direct
  fetch, so the bundled version could not be read. Both files now say 4.22 is
  unverified rather than silently extending the range.
- **"ArgoCD through v3.3 / GitOps 1.20 only supports Helm 3"** — not re-probed
  this pass; the pass budget went to the version-span and EOL findings. Argo CD
  is on GitHub, so this one is cheaply checkable next time via
  `gh release list -R argoproj/argo-cd` plus its Helm-version dependency.

## Resolved — 2026-07-21 (freshen)

The file's own "VERIFY during freshen" flags drove this pass. Three of four
closed; one of them by *deleting* a claim rather than updating it.

- **OCP 4.22 went GA 2026-07-14** (RHEA-2026:0449, Kubernetes 1.35, CRI-O 1.35)
  — one week before this pass. Span moved 4.14-4.21 → **4.14-4.22** in the
  frontmatter, body, and `gotchas.md`, and a 4.22 timeline row added (JobSet
  controller GA, lazy image pulling via plug-in CRI-O). That row is marked
  **incomplete**: the 4.22 release notes 403 to direct fetch, so it holds only
  what search summaries surfaced.
- **Helm 3 EOL dates removed, not re-dated.** The skill stated "bug fixes
  July 8 2026, security fixes November 11 2026" with a precision no source
  supports. `helm.sh/docs/topics/version_skew` and
  `helm.sh/docs/community/release_policy` both describe only "the most recent
  minor release" receiving cherry-picked fixes and name no Helm 3 sunset.
  Observed behaviour contradicts the claim outright: **v3.21.3 shipped
  2026-07-09**, one day after the stated bug-fix cutoff and alongside v4.2.3.
  Replaced with what is verifiable — both lines are live, so plan a migration on
  ArgoCD support rather than on a calendar.
- **OLM v1 / ClusterExtension GA confirmed at OCP 4.18** — the previous pass's
  "4.18 timeframe" hedge was correct. Initial GA scope recorded: `registry+v1`
  bundles, AllNamespaces install mode, no webhooks.
- **Operator SDK is two gates, not one.** The deprecation *notice* landed at
  4.16, but **4.18 was the last OpenShift planned to ship the CLI** — on 4.19+
  it is not bundled at all. The skill said only "deprecated in 4.16", which
  understates the impact for anyone on a current cluster.
- **Two leading-indicator traps recorded in `sources.md`.** (1) The
  `openshift-clients-4.22.0-*` tag was cut ~2 months before 4.22 GA, so a client
  tag proves builds exist, not that the minor shipped. (2) OKD leads OCP and is
  now at `4.22.0-okd-scos.7` with a `5.0.0-okd-scos.ec` line open — the previous
  pass inferred "4.21 is the current OCP line" from an OKD 4.22 tag, which was
  right by luck, not by reasoning.
- **Lifecycle policy re-read:** ≥4 minors supported concurrently; Full Support =
  6 months or 90 days past the next minor's GA, whichever is longer; Maintenance
  = 18 months from GA; **EUS = even-numbered minors**, so 4.20 and 4.22 are EUS
  and 4.21 is not.

## Resolved — 2026-05-28

- Created `references/sources.md` (was absent) with dated, evidence-backed rows stamped 2026-05-28 — lifts the Boris Dim 9 staleness cap from 6 to 8.
- Added "works on Kubernetes but fails on OpenShift" / SCC-denied / arbitrary-UID symptom trigger to the frontmatter `description` (Dim 1).
- Replaced the cryptic "S <Section>" anchor shorthand in the Quick Decision Guide with explicit "(… section)" wording (Dim 8).
