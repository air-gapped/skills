# Sources

External references this skill depends on, with the version/state observed and
the date each was last verified online. Re-run `freshen helm` to refresh.

**Every `uses:` SHA in this skill is resolved against the GitHub API before it
ships.** Two of the eight pins present before 2026-07-21 pointed at commits that
do not exist — a SHA-pinned action with a wrong SHA is a hard workflow failure,
and neither a version bump nor a read-through catches it. Re-verify with
`gh api repos/<owner>/<repo>/commits/<sha>` on every pass; a `422 No commit
found` is the finding.

| Source | URL | Last verified | Notes |
|--------|-----|---------------|-------|
| Helm releases | https://github.com/helm/helm/releases | 2026-07-21 | Latest stable v4.2.3 (2026-07-09); latest 4.1 patch v4.1.4 (2026-04-09), line quiet since. **Helm 3 is still maintained in parallel** — v3.21.3 shipped the same day as v4.2.3. Helm 4.0.0 GA Nov 12 2025 at KubeCon. |
| Helm docs | https://helm.sh/docs/ | 2026-05-28 | Chart API v2 current; v3 format planned, not released. SSA default on new installs in Helm 4. |
| helm-unittest | https://github.com/helm-unittest/helm-unittest/releases | 2026-07-21 | Latest v1.1.1 (2026-06-05). BDD-style unit testing plugin, no cluster needed. |
| helmfile | https://github.com/helmfile/helmfile/releases | 2026-07-21 | Latest v1.7.1 (2026-07-17) — two minors on from the previous pass. Declarative multi-release management; supports Helm 3+4. |
| chart-testing (ct) action | https://github.com/helm/chart-testing-action/releases | 2026-07-21 | Still v2.8.0 (2025-11-05), SHA `6ec842c01de15ebb84c8627d2744a0c2f2755c9f` — resolves, matches the skill pin. |
| chart-releaser action | https://github.com/helm/chart-releaser-action/releases | 2026-07-21 | Still v1.7.0 (2025-01-20). **Skill SHA was wrong** and now reads `cae68fefc6b5f367a0275617c9f83181ba54714f`. |
| helm-docs | https://github.com/norwoodj/helm-docs/releases | 2026-07-21 | Still v1.14.2 (2024-07-08) — no release in two years; matches skill pin. |
| dadav/helm-schema | https://github.com/dadav/helm-schema/releases | 2026-07-21 | Latest 0.23.4 (2026-06-03). values.schema.json generator from `@schema` annotations; GPG-signed releases. |
| kubeconform | https://github.com/yannh/kubeconform | 2026-07-21 | Latest v0.8.0 (2026-06-04). Successor to deprecated kubeval; validates rendered manifests against K8s OpenAPI schemas. |
| cosign / sigstore | https://github.com/sigstore/cosign | 2026-07-21 | Latest v3.1.2 (2026-07-17); v2 line still patched (v2.6.4, same day). Keyless + key-based OCI artifact signing; sign Helm charts by digest, not tag. |
| Bitnami common library chart | https://github.com/bitnami/charts/tree/main/bitnami/common | 2026-05-28 | Source of commonLabels/commonAnnotations/adaptSecurityContext patterns; Bitnami moved to OCI-only. |
| ArgoCD OCI cosign verification | https://github.com/argoproj/argo-cd/issues/22609 | 2026-05-28 | Issue still OPEN — ArgoCD has no built-in cosign signature verification for OCI yet. Flux is ahead. |
| Flux Helm OCI verification | https://fluxcd.io/flux/components/source/helmrepositories/ | 2026-05-28 | Flux supports cosign signature verification of OCI Helm charts via `.spec.verify`. |
| OpenShift SCCs / DeploymentConfig | https://docs.openshift.com/ | 2026-05-28 | DeploymentConfig deprecated in OCP 4.14; use apps/v1 Deployment. restricted-v2 SCC assigns arbitrary UIDs. |
| Renovate Helm managers | https://docs.renovatebot.com/modules/manager/helmv3/ | 2026-05-28 | helmv3 + helm-values managers; updates Chart.yaml deps and image tags in values.yaml. |
| release-please | https://github.com/googleapis/release-please | 2026-07-21 | Latest v17.10.3 (2026-07-09). `helm` release-type understands Chart.yaml; config-file vs action-input trap and extra-files object-form trap apply. |

## CI action pins — verified 2026-07-21

Every SHA below was confirmed to resolve via `gh api repos/<r>/commits/<sha>`.

| Action | Version | SHA | Note |
|---|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | was v4.2.2 |
| actions/setup-python | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` | was v5.6.0 |
| azure/setup-helm | v5.0.1 | `9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310` | was v4.3.0; v5.0.0 was node20→node24 only |
| docker/login-action | v4.4.0 | `af1e73f918a031802d376d3c8bbc3fe56130a9b0` | was v3.4.0 |
| helm/kind-action | v1.14.0 | `ef37e7f390d99f746eb8b610417061a60e82a6cc` | was v1.12.0 |
| sigstore/cosign-installer | v4.1.2 | `6f9f17788090df1f26f669e9d70d6ae9567deba6` | was v3.8.2 — **and that SHA did not exist**. v4 is required to install cosign v3+ |
| helm/chart-testing-action | v2.8.0 | `6ec842c01de15ebb84c8627d2744a0c2f2755c9f` | unchanged, verified |
| helm/chart-releaser-action | v1.7.0 | `cae68fefc6b5f367a0275617c9f83181ba54714f` | version unchanged, **SHA corrected** |

**cosign-installer v4 breaking change does not bite this skill.** v4 is required
for cosign v3+, and cosign v3 makes `--bundle` mandatory on `cosign sign-blob`.
This skill only ever runs `cosign sign` / `cosign verify` against OCI digests
(`security.md`, `testing-ci.md`) and never `sign-blob`, so the bump is safe as
written. If chart-provenance signing is ever added, revisit this.
