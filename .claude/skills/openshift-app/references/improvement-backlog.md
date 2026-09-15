# Improvement Backlog — openshift-app

Tracks improvement hypotheses attempted but not landed in one atomic iteration, plus changes the metric registered this pass. Open is a work-not-done log, not a wishlist.

## Resolved — 2026-09-15 (a compliance claim expiring in six days)

- **"FIPS 140-2 validations remain active through September 21, 2026" had no
  expiry marker and no after-state.** It is **6 days** from becoming false, in a
  block an operator reads for a compliance answer.
- **The gap is the point, and it is why this could not be fixed by bumping a
  date.** The 140-2 window closes while the same block still records the 140-3
  submissions as *pending CMVP review* — so the live question after the 21st is
  whether modules are submitted-but-not-validated, and what that does to an
  attestation.
- **Deliberately did not assert what happens next.** Nothing here predicts CMVP
  behaviour; the entry says to check the CMVP validated-modules search and Red
  Hat's compliance page at the time of asking, and demotes the block to a
  starting point for that lookup. Replacing an expiring fact with an invented one
  would be worse than the expiry.

## Open

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

## Unblocked — actionable

## Decided — do not re-propose

- **Do not merge the Quick Decision Guide into Additional References** (was filed
  2026-09-15 as actionable). Inspected: the two tables index different lookups. The
  first maps a *task* to a destination and is the only place two in-file anchors are
  reachable from; the second maps a *file* to its contents, which is what a reader
  scans when they do not yet have a task. A merged table can be keyed on one or the
  other, not both, so the merge loses whichever it is not keyed on — it is a net
  loss, not a deferred win.
- **The real defect underneath it is fixed.** Two Quick Decision Guide rows pointed
  only at in-file sections while a deeper reference file existed, so a reader
  following them stopped at the summary and never learned the reference was there.
  Both rows now name the in-file anchor *and* the reference.

## Resolved — 2026-09-15 (a compliance claim expiring in six days)

- **"FIPS 140-2 validations remain active through September 21, 2026" had no
  expiry marker and no after-state.** It is **6 days** from becoming false, in a
  block an operator reads for a compliance answer.
- **The gap is the point, and it is why this could not be fixed by bumping a
  date.** The 140-2 window closes while the same block still records the 140-3
  submissions as *pending CMVP review* — so the live question after the 21st is
  whether modules are submitted-but-not-validated, and what that does to an
  attestation.
- **Deliberately did not assert what happens next.** Nothing here predicts CMVP
  behaviour; the entry says to check the CMVP validated-modules search and Red
  Hat's compliance page at the time of asking, and demotes the block to a
  starting point for that lookup. Replacing an expiring fact with an invented one
  would be worse than the expiry.

## Open

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

## Unblocked — actionable

- **Merge the two top-of-file routing tables** (Dim 6) — `SKILL.md` Quick Decision Guide (~L18-30) and Additional References (~L223-233). The two tables overlap slightly in intent (task-routing vs file-contents). Merging into one canonical navigation surface is a structural rewrite of two sections that also risks dropping the distinct in-file anchors (#container-image-essentials, #packaging-decision-matrix) the Quick Decision Guide carries; deferred to avoid conflating relocation with prose rewrite in a single step. Nothing external blocks it — it needs two iterations, a move and then a rewrite.

## Resolved — 2026-09-15

- **Per-file tables of contents** (Dim 7) — found already present in all seven reference files. The item was stale: the work had been done and never retired from Open. Verified every anchor resolves to a real heading.
- **Inline SCC validation commands added** (Dim 4) — `SKILL.md`, immediately after the minimum-compliant securityContext block. Three `oc get pod -o jsonpath` one-liners: the admitting SCC from the `openshift.io/scc` annotation, the container securityContext, and the assigned UID. Notes that an empty `runAsUser` alongside a populated SCC annotation is the expected result, since the range assignment lands at admission rather than in the manifest.

## Resolved — 2026-09-15 (both carried verify-next-freshen items)

- **Argo CD moved to Helm 4 — the skill's headline claim was inverted.** The
  gotcha was titled "Helm 4 Is NOT Usable with ArgoCD on OpenShift" and said
  "ArgoCD through v3.3 / GitOps 1.20 only supports Helm 3". PR #28076 ("feat:
  Migrate from Helm 3 to Helm 4") merged **2026-06-09** and shipped in
  **v3.5.0** (2026-08-04). Read from `hack/tool-versions.sh` at each tag:
  v3.5.3 pins `helm4_version=4.2.1`, v3.4.9 pins `helm3_version=3.19.4`. The
  old "through v3.3" framing also understated it — 3.4.x stayed on Helm 3 too,
  and only 3.5.x jumped. Section retitled and rewritten, with the upgrade
  hazard added: Helm 4's null-coalescing change can alter rendered manifests
  across 3.4 → 3.5 with no chart or values edit (argo-cd#29068, still OPEN).
- **OCP 4.22's bundled Helm version established: v3.20.2.** The previous pass
  could not read it because `docs.redhat.com` 403s. It is not a 403 problem —
  the page is a client-rendered shell with **no version text in its HTML for
  any OCP version**, so that source can never answer this. The answer lives in
  the `redhat-developer/web-terminal-operator` CHANGELOG, which maps each Web
  Terminal Operator release to the tool versions it ships: WTO 1.17
  (2026-06-24) bumped `oc` v4.21.4 → v4.22.1 and helm v3.17.1 → v3.20.2.
  Recorded in `SKILL.md` and `packaging-formats.md` along with where it came
  from, so the next pass does not retry the docs page.

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
