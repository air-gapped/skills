# Sources

Freshened: 2026-10-27 — every row probed. Helm v4.3.1 / v3.22.1; the null-default leak re-measured on five binaries is subchart-scoped, and two of the three CRD exemplars never templated their CRDs.

**Methodology note for the null-coalescing rows:** their release attributions are confirmable only from each release's own notes, **not** from git ancestry. This project backports, so a fix reaches an older patch release as a *different commit*; comparing the pull request's main-branch merge commit against that tag reports "diverged" even though the fix is in it. Measured here: #31644's merge commit is not an ancestor of v4.1.3, yet v4.1.3's notes credit #31644 — while v4.2.0, which does contain that commit, never mentions it.

External references this skill depends on, with the version/state observed and
the date each was last verified online. Re-run `freshen helm` to refresh.

**Every `uses:` SHA in this skill is resolved against the GitHub API before it
ships.** Two of the eight pins present before 2026-07-21 pointed at commits that
do not exist — a SHA-pinned action with a wrong SHA is a hard workflow failure,
and neither a version bump nor a read-through catches it. Re-verify with
`gh api repos/<owner>/<repo>/commits/<sha>` on every pass; a `422 No commit
found` is the finding.

**Resolve pinned *tags* too, not just SHAs.** A `rev:` or `@tag` naming a tag
upstream never cut fails exactly like a bad SHA, and tag *format* is per-repo,
not guessable: `norwoodj/helm-docs` tags `v1.14.2`, `dadav/helm-schema` tags
`0.24.0` with **no** `v`. The 2026-08-26 pass found `rev: v0.23.3` in
`testing-ci.md` — a 404. Check with `gh api repos/<o>/<r>/git/refs/tags/<tag>`.

| Source | URL | Last verified | Notes |
|--------|-----|---------------|-------|
| Helm releases | https://github.com/helm/helm/releases · https://helm.sh/blog/helm-v3-end-of-life | 2026-10-27 | Latest stable **v4.3.1 (2026-10-15)** (notes: CRD establishment wait under HookOnlyStrategy #32672, golangci-lint bump; nothing on values merging). 4.2 ends at v4.2.4, 4.1 at v4.1.4. **Helm 3 still patched**: **v3.22.1 (2026-10-15)**, Go-vulnerability dependency bumps + k8s.io updates. v4.3.1 notes: "no further Helm 3 minor releases"; Helm 3 patches ship alongside Helm 4 patches. Helm 3 EOL blog (2026-06-02): bug fixes and the final feature release on September 9th, 2026 (v3.22.0, published 2026-09-10 00:08 UTC); security fixes end February 10th, 2027. Helm 4.0.0 GA Nov 12 2025 at KubeCon. |
| Helm docs | https://helm.sh/docs/overview/ | 2026-10-27 | Chart API v2 current. "Charts v3 is in early development and available for experimentation": `HELM_EXPERIMENTAL_CHART_V3=1` + `helm create --chart-api-version=v3`; "Use for testing and feedback only." Helm 4 defaults to server-side apply on new installs. |
| helm-unittest | https://github.com/helm-unittest/helm-unittest/releases | 2026-10-27 | Latest **v1.2.1** (2026-10-03): v1.2.0 (2026-10-01) "Full helm 4 support"; v1.2.1 fixes the install script on Helm >= 4.3.0 with OCI plugin installation. README: Helm 4 git install needs `--verify=false`; OCI install supported from plugin 1.1.0. |
| helmfile | https://github.com/helmfile/helmfile/releases | 2026-10-27 | Latest **v1.8.2 (2026-10-16)**; v1.8.0 2026-09-13. Declarative multi-release management; supports Helm 3+4. |
| chart-testing (ct) action | https://github.com/helm/chart-testing-action/releases | 2026-10-27 | Latest **v2.9.0** (2026-10-09). Skill pins v2.8.0 (2025-11-05), SHA `6ec842c01de15ebb84c8627d2744a0c2f2755c9f` — resolves and equals the tag commit; bump deliberately. |
| chart-releaser action | https://github.com/helm/chart-releaser-action/releases | 2026-10-27 | Latest **v1.8.0** (2026-10-27). Skill pins v1.7.0 (2025-01-20), SHA `cae68fefc6b5f367a0275617c9f83181ba54714f` (corrected 2026-07-21) — resolves; the annotated tag dereferences to it. Bump deliberately. |
| helm-docs | https://github.com/norwoodj/helm-docs/releases | 2026-10-27 | Still v1.14.2 (2024-07-08) — no release since; matches skill pin. Tags here **are** `v`-prefixed. |
| dadav/helm-schema | https://github.com/dadav/helm-schema/releases | 2026-10-27 | Latest **0.24.0** (2026-10-18), was 0.23.5: bug fixes (subchart schema references, import-values), no breaking changes; `additionalProperties` still defaults to `false` for non-empty maps; hook id `helm-schema` unchanged. values.schema.json generator from `@schema` annotations; GPG-signed releases. Tags carry **no** `v` prefix — `v0.23.x` 404s. |
| kubeconform | https://github.com/yannh/kubeconform | 2026-10-27 | Latest v0.8.0 (2026-06-04). Successor to deprecated kubeval; validates rendered manifests against K8s OpenAPI schemas. |
| cosign / sigstore | https://github.com/sigstore/cosign | 2026-10-27 | Latest v3.1.4 (2026-10-20); v2 line still patched (v2.6.5, 2026-08-06). Keyless + key-based OCI artifact signing; sign Helm charts by digest, not tag. |
| Bitnami common library chart | https://github.com/bitnami/charts/tree/main/bitnami/common | 2026-10-27 | Source of commonLabels/commonAnnotations/adaptSecurityContext patterns. Newest `common` is 2.41.0 (2026-06-29), served from `oci://registry-1.docker.io/bitnamicharts/common`. The legacy `https://charts.bitnami.com/bitnami/index.yaml` is still regenerated (generated 2026-10-27, entries dated 2026-10-26) and every entry points at an `oci://` URL; the bare repo URL returns 403, the index 200. |
| ArgoCD OCI cosign verification | https://github.com/argoproj/argo-cd/issues/22609 | 2026-10-27 | Issue OPEN; last comment 2026-10-27 is a user asking for updates, no maintainer fix. Related PR #27741 (open) extends Source Integrity to Helm/OCI Helm sources via `.prov` files, not cosign. At argoproj/argo-cd `main` (2026-10-27) `docs/user-guide/source-integrity.md` lists Git GnuPG as the only method (Source Integrity replaced GnuPG verification in 3.5). OCI sources first shipped in v3.1.0 (PR #18646, Beta). Latest v3.5.6; v3.6.0-rc4. Flux is ahead. |
| Flux Helm OCI verification | https://fluxcd.io/flux/components/source/ocirepositories/ · https://fluxcd.io/flux/components/source/helmcharts/ · https://fluxcd.io/flux/components/source/helmrepositories/ | 2026-10-27 | `.spec.verify` (cosign or notation; `matchOIDCIdentity` for keyless cosign) is documented on OCIRepository and on HelmChart ("available only for Helm charts fetched from an OCI Registry"); the HelmRepository page has no verify field and says "The oci type is in maintenance mode … please use the OCIRepository API". HelmRelease `spec.chartRef` accepts OCIRepository, HelmChart, ExternalArtifact. |
| OpenShift SCCs / DeploymentConfig | https://docs.openshift.com/ | 2026-10-27 | Redirects to docs.redhat.com. OCP 4.14 release notes: "DeploymentConfig resources are now deprecated"; use apps/v1 Deployment. restricted-v2 SCC assigns arbitrary UIDs. |
| Renovate Helm managers | https://docs.renovatebot.com/modules/manager/helmv3/ | 2026-10-27 | helmv3 + helm-values managers (both doc pages 200); updates Chart.yaml deps and image tags in values.yaml. |
| Dependabot Helm | https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories · https://github.blog/changelog/2025-04-09-dependabot-version-updates-now-support-helm/ | 2026-10-27 | GA changelog April 9, 2025. Docs: "it will also automatically update the Docker images referenced within those charts". Code: dependabot/dependabot-core PR #11890 (merged 2025-03-26) added values-file image tags and Chart.lock regeneration; `helm/lib/dependabot/helm/file_parser.rb` `parse_values_yaml_files` handles `image: "repo:tag"` and `repository` + `tag` maps. Drives SKILL.md Gotcha #14. |
| release-please | https://github.com/googleapis/release-please | 2026-10-27 | Latest **v17.11.2** (2026-08-24), was v17.11.1. `helm` release-type understands Chart.yaml; config-file vs action-input trap and extra-files object-form trap apply. |
| Trivy action compromise | https://github.com/advisories/GHSA-69fq-xp46-6x23 | 2026-10-27 | GHSA-69fq-xp46-6x23, published 2026-03-24: "Trivy ecosystem supply chain was briefly compromised". Backs `testing-ci.md` "pin Trivy action to SHA". |
| helm-diff plugin | https://github.com/databus23/helm-diff/releases | 2026-10-27 | Latest **v3.15.15** (2026-09-26). `.prov` assets on every release from v3.15.8 (2026-06-06); none on v3.15.7 and earlier. README "For Helm 4 users": import `https://github.com/databus23.gpg`, install from the release tarball URL; git repo URLs do not support provenance verification. |
| CRD approaches in major charts | https://github.com/cert-manager/cert-manager/tree/v1.21.3/deploy/charts/cert-manager · https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack · https://github.com/cilium/cilium/blob/v1.18.16/pkg/k8s/apis/cell.go | 2026-10-27 | cert-manager v1.21.3: `crd-*.yaml` in `templates/`, `crds.enabled: false` / `crds.keep: true` (`installCRDs` deprecated). kube-prometheus-stack 92.14.1: local `crds` subchart with CRDs in its native `crds/` dir, `condition: crds.enabled`; README says CRDs are not updated on upgrade; `crds.upgradeJob.enabled` (preview, default false); UPGRADE.md uses `kubectl apply --server-side`. Cilium v1.18.16: no CRD manifests in `install/kubernetes/cilium/`; operator's `RegisterCRDsCell` creates them, `--skip-crd-creation` disables. Drives SKILL.md Gotcha #6 and `chart-structure.md` § CRD Management. |
| Helm null coalescing | https://github.com/helm/helm/issues/32093 | 2026-10-27 | **Measured** with minimal charts on v3.17.3 / v4.0.5 / v4.1.0 / v4.1.1 / v4.1.4 / v4.2.0 / v4.2.4. Whether a chart's own `foo: ~` default survives the merge (`hasKey`) flipped twice — PR #31644 in **v4.1.3**, PR #31979 in **v4.2.0**. helm#32093 ("Subchart-default nil values still leak through coalescing when parent sets any user value") OPEN, last comment 2026-10-20; fix PR #32097 unmerged; related open PRs #32531, #32538. **Re-measured 2026-10-27** with `helm template` on v3.17.3 / v3.22.1 / v4.2.4 / v4.3.0 / v4.3.1: top-level chart `keyMapping.password: ~` → `hasKey` true on both 3.x, false on all 4.x, with or without any `-f` (no `-f` dependence at top level). Same default in a subchart → false with no values or an unrelated top-level key, **true when the parent passes `child.someOtherKey`**, on v4.2.4–v4.3.1; true in every case on v3.22.1, false in every case on v3.17.3. Deleting a **non-null** default via a user `-f` null works on 3.17.3, 4.3.0, 4.3.1. Drives SKILL.md Gotcha #5. |

## CI action pins — verified 2026-10-27

Every SHA below was re-confirmed to resolve via `gh api repos/<r>/commits/<sha>`
on 2026-10-27 — all eight pass, and each equals its tag's commit. Newer releases exist for several; bump those
deliberately, not via freshen.

| Action | Version | SHA | Note |
|---|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | was v4.2.2 |
| actions/setup-python | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` | was v5.6.0; latest v7.1.0 (2026-10-22) — bump deliberately |
| azure/setup-helm | v5.0.1 | `9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310` | was v4.3.0; v5.0.0 was node20→node24 only |
| docker/login-action | v4.4.0 | `af1e73f918a031802d376d3c8bbc3fe56130a9b0` | was v3.4.0; latest is v4.7.0 (2026-10-23), pin still resolves — bump deliberately, not via freshen |
| helm/kind-action | v1.14.0 | `ef37e7f390d99f746eb8b610417061a60e82a6cc` | was v1.12.0; latest v1.15.1 (2026-10-06; v1.15.0 bumped default kind/kubectl) — bump deliberately |
| sigstore/cosign-installer | v4.1.2 | `6f9f17788090df1f26f669e9d70d6ae9567deba6` | was v3.8.2 — **and that SHA did not exist**. v4 is required to install cosign v3+ |
| helm/chart-testing-action | v2.8.0 | `6ec842c01de15ebb84c8627d2744a0c2f2755c9f` | latest v2.9.0 (2026-10-09) — bump deliberately |
| helm/chart-releaser-action | v1.7.0 | `cae68fefc6b5f367a0275617c9f83181ba54714f` | **SHA corrected** 2026-07-21; latest v1.8.0 (2026-10-27) — bump deliberately |

## pre-commit `rev:` pins — verified 2026-10-27

Every tag below was confirmed via `gh api repos/<o>/<r>/git/refs/tags/<tag>`.
Note the inconsistent prefixing — copy the tag, do not construct it.

| Repo | Pinned rev | Resolves | Latest | Where |
|---|---|---|---|---|
| pre-commit/pre-commit-hooks | `v6.0.0` | yes | v6.0.0 (2025-08-09) | `testing-ci.md` — was v5.0.0, a year stale |
| adrienverge/yamllint | `v1.38.0` | yes | v1.38.0 (2026-01-13) | `testing-ci.md` |
| norwoodj/helm-docs | `v1.14.2` | yes | v1.14.2 (2024-07-08) | `testing-ci.md`, `chart-structure.md` |
| dadav/helm-schema | `0.24.0` | yes | 0.24.0 (2026-10-18) | `testing-ci.md` — **was `v0.23.3`, a 404** |

**cosign-installer v4 breaking change does not bite this skill.** v4 is required
for cosign v3+, and cosign v3 makes `--bundle` mandatory on `cosign sign-blob`.
This skill only ever runs `cosign sign` / `cosign verify` against OCI digests
(`security.md`, `testing-ci.md`) and never `sign-blob`, so the bump is safe as
written. If chart-provenance signing is ever added, revisit this.
