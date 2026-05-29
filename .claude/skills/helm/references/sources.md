# Sources

External references this skill depends on, with the version/state observed and
the date each was last verified online. Re-run `freshen helm` to refresh.

| Source | URL | Last verified | Notes |
|--------|-----|---------------|-------|
| Helm releases | https://github.com/helm/helm/releases | 2026-05-28 | Latest stable v4.2.0 (2026-05-14); latest 4.1 patch v4.1.4 (2026-04-09). Helm 4.0.0 GA Nov 12 2025 at KubeCon. |
| Helm docs | https://helm.sh/docs/ | 2026-05-28 | Chart API v2 current; v3 format planned, not released. SSA default on new installs in Helm 4. |
| helm-unittest | https://github.com/helm-unittest/helm-unittest/releases | 2026-05-28 | Latest v1.1.0. BDD-style unit testing plugin, no cluster needed. |
| helmfile | https://github.com/helmfile/helmfile/releases | 2026-05-28 | Latest v1.5.2. Declarative multi-release management; supports Helm 3+4. |
| chart-testing (ct) action | https://github.com/helm/chart-testing-action/releases | 2026-05-28 | Latest v2.8.0 (2025-11-05), SHA 6ec842c01de15ebb84c8627d2744a0c2f2755c9f; skill SHA-pins this. |
| chart-releaser action | https://github.com/helm/chart-releaser-action/releases | 2026-05-28 | Latest v1.7.0 (matches skill pin). |
| helm-docs | https://github.com/norwoodj/helm-docs/releases | 2026-05-28 | Latest v1.14.2 (matches skill pin). |
| dadav/helm-schema | https://github.com/dadav/helm-schema/releases | 2026-05-28 | Latest v0.23.3. values.schema.json generator from `@schema` annotations; GPG-signed releases. |
| kubeconform | https://github.com/yannh/kubeconform | 2026-05-28 | Successor to deprecated kubeval; validates rendered manifests against K8s OpenAPI schemas. |
| cosign / sigstore | https://github.com/sigstore/cosign | 2026-05-28 | Keyless + key-based OCI artifact signing; sign Helm charts by digest, not tag. |
| Bitnami common library chart | https://github.com/bitnami/charts/tree/main/bitnami/common | 2026-05-28 | Source of commonLabels/commonAnnotations/adaptSecurityContext patterns; Bitnami moved to OCI-only. |
| ArgoCD OCI cosign verification | https://github.com/argoproj/argo-cd/issues/22609 | 2026-05-28 | Issue still OPEN — ArgoCD has no built-in cosign signature verification for OCI yet. Flux is ahead. |
| Flux Helm OCI verification | https://fluxcd.io/flux/components/source/helmrepositories/ | 2026-05-28 | Flux supports cosign signature verification of OCI Helm charts via `.spec.verify`. |
| OpenShift SCCs / DeploymentConfig | https://docs.openshift.com/ | 2026-05-28 | DeploymentConfig deprecated in OCP 4.14; use apps/v1 Deployment. restricted-v2 SCC assigns arbitrary UIDs. |
| Renovate Helm managers | https://docs.renovatebot.com/modules/manager/helmv3/ | 2026-05-28 | helmv3 + helm-values managers; updates Chart.yaml deps and image tags in values.yaml. |
| release-please | https://github.com/googleapis/release-please | 2026-05-28 | `helm` release-type understands Chart.yaml; config-file vs action-input trap and extra-files object-form trap apply. |
