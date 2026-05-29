# Improvement Backlog — openshift-app

Tracks improvement hypotheses attempted but not landed in one atomic iteration, plus changes the metric registered this pass. Open is a work-not-done log, not a wishlist.

## Open

- **Per-file tables of contents for the 7 reference files** (Dim 7) — `references/{container-images,packaging-formats,security,cicd-gitops,operations,gotchas,disconnected}.md`. Each file exceeds the 100-line TOC threshold (226-454 lines) but none carries a top-of-file TOC. Not applied in one iteration: adding a TOC to each of 7 files requires reading each file's exact heading structure and is a 7-file change, exceeding the one-atomic-change-per-iteration rule. Do one file per iteration next pass.
- **Merge the two top-of-file routing tables** (Dim 6) — `SKILL.md` Quick Decision Guide (~L18-30) and Additional References (~L223-233). The two tables overlap slightly in intent (task-routing vs file-contents). Merging into one canonical navigation surface is a structural rewrite of two sections that also risks dropping the distinct in-file anchors (#container-image-essentials, #packaging-decision-matrix) the Quick Decision Guide carries; deferred to avoid conflating relocation with prose rewrite in a single step.
- **Inline SCC validation one-liner** (Dim 4) — `SKILL.md` next to the restricted-v2 securityContext block (~L76-85). Add a confirm-it-worked command (e.g. `oc get pod NAME -o jsonpath='{.spec.containers[0].securityContext}'` and the assigned UID via `oc get pod NAME -o jsonpath='{.spec.securityContext.runAsUser}'`). This is an additive content change; deferred this pass to keep the pass deletion-biased and because exact placement needs a fresh read of the surrounding block to avoid duplicating guidance already in references/security.md.

## Verify next freshen (recon flagged 'unverifiable' — live docs were blocked)

These claims in the skill body were NOT altered (cannot stand behind a change without evidence). sources.md carries them with explicit "VERIFY during freshen" notes:
- `SKILL.md` L90-96 — "OCP 4.19-4.21 still ships Helm 3", "ArgoCD through v3.3 / GitOps 1.20 only supports Helm 3", "Helm 3 EOL: bug fixes July 2026, security fixes Nov 2026".
- `SKILL.md` L189-190 + packaging-formats — "OLM v1 ClusterExtension on OCP 4.18+", "Operator SDK CLI deprecated in OCP 4.16".

## Resolved this pass

- Created `references/sources.md` (was absent) with dated, evidence-backed rows stamped 2026-05-28 — lifts the Boris Dim 9 staleness cap from 6 to 8.
- Added "works on Kubernetes but fails on OpenShift" / SCC-denied / arbitrary-UID symptom trigger to the frontmatter `description` (Dim 1).
- Replaced the cryptic "S <Section>" anchor shorthand in the Quick Decision Guide with explicit "(… section)" wording (Dim 8).
