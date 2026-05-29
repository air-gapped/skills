# Sources

External references underpinning this skill's OpenShift-specific claims. Re-verify the dated rows when running `freshen`. Stamp the row's "Last verified" with the date you re-confirmed the claim against the live source.

## Table of Contents
- [Platform versions & lifecycle](#platform-versions--lifecycle)
- [Deployments & workloads](#deployments--workloads)
- [Container images (UBI)](#container-images-ubi)
- [Security (SCC / PSA)](#security-scc--psa)
- [Packaging (Helm / Operators / OLM v1)](#packaging-helm--operators--olm-v1)
- [CI/CD & GitOps](#cicd--gitops)
- [Supply chain](#supply-chain)
- [Operations & logging](#operations--logging)

## Platform versions & lifecycle

| Source | URL | Last verified | Notes |
|---|---|---|---|
| OpenShift Container Platform release notes | https://docs.redhat.com/en/documentation/openshift_container_platform | 2026-05-28 | OCP 4.20 GA 2025-11-12; 4.21 client tags exist (openshift-clients-4.21.0-202601121715, Jan 2026). Span "4.14-4.21" current. |
| openshift/oc release tags | https://github.com/openshift/oc/tags | 2026-05-28 | Confirms 4.21 client builds via `gh api repos/openshift/oc/tags`. |
| Red Hat OpenShift lifecycle policy | https://access.redhat.com/support/policy/updates/openshift | 2026-05-28 | OVN-Kubernetes mandatory / OpenShift SDN removed in 4.17; cgroup v1 removed in 4.19; restricted-v2 default since 4.11. |
| OKD release page | https://github.com/okd-project/okd/releases | 2026-05-28 | OKD latest 4.22.0-okd-scos.1; confirms 4.21 is the current released OCP line. |

## Deployments & workloads

| Source | URL | Last verified | Notes |
|---|---|---|---|
| DeploymentConfig deprecation | https://access.redhat.com/articles/7041372 | 2026-05-28 | "As of OpenShift 4.14, DeploymentConfig objects are deprecated ... not recommended for new installations. Instead, use Deployment objects." Exact docs snippet confirmed via `gh search code` in openshift/openshift-docs (snippets/deployment-config-deprecated.adoc). Deprecated, not removed. |
| ImageStream triggers (image.openshift.io/triggers) | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/images/triggering-updates-on-imagestream-changes | 2026-05-28 | Annotation-based trigger pattern for Deployments. |

## Container images (UBI)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Red Hat Universal Base Images (UBI) | https://catalog.redhat.com/software/base-images | 2026-05-28 | ubi9/ubi, ubi-minimal, ubi-micro, ubi-init at registry.access.redhat.com/ubi9/*; microdnf is the ubi-minimal package manager; ubi-micro ships no package manager. |
| UBI documentation | https://www.redhat.com/en/blog/introducing-red-hat-universal-base-image | 2026-05-28 | Background on UBI variants and redistribution terms. |

## Security (SCC / PSA)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Managing SCCs | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/authentication_and_authorization/managing-pod-security-policies | 2026-05-28 | restricted-v2 is the default SCC since 4.11; arbitrary UID + GID 0 group requirement. |
| Pod Security Admission in OpenShift | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/authentication_and_authorization/understanding-and-managing-pod-security-admission | 2026-05-28 | PSA enforcement labels and the restricted-v2-vs-PSS-restricted relationship. |

## Packaging (Helm / Operators / OLM v1)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Helm releases | https://github.com/helm/helm/releases | 2026-05-28 | Helm 4.0.0 released November 2025 (SSA default). OCP 4.19-4.21 still ships Helm 3 — VERIFY OCP-bundled Helm version + ArgoCD/GitOps Helm 3-only support during freshen (live docs were blocked in recon). |
| Helm version support / skew | https://helm.sh/docs/topics/version_skew | 2026-05-28 | Helm 3 EOL window (bug fixes ~July 2026, security fixes ~Nov 2026) — VERIFY exact dates during freshen. |
| Operator Lifecycle Manager v1 (ClusterExtension) | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/extensions/index | 2026-05-28 | OLM v1 / ClusterExtension RBAC requirements; ClusterExtension GA in the 4.18 timeframe — VERIFY exact version gate during freshen. |
| Operator SDK | https://sdk.operatorframework.io/ | 2026-05-28 | Operator SDK CLI deprecated in OCP ~4.16 (upstream continues) — VERIFY exact version gate during freshen. |

## CI/CD & GitOps

| Source | URL | Last verified | Notes |
|---|---|---|---|
| OpenShift Pipelines (Tekton) | https://docs.redhat.com/en/documentation/red_hat_openshift_pipelines | 2026-05-28 | Tekton-based CI on OpenShift. |
| OpenShift GitOps (Argo CD) | https://docs.redhat.com/en/documentation/red_hat_openshift_gitops | 2026-05-28 | Argo CD distribution; GitOps version-to-Argo-CD mapping. Verify Helm support skew during freshen. |
| Shipwright | https://shipwright.io/ | 2026-05-28 | Cluster-side container builds (Buildah/Kaniko/BuildKit strategies). |

## Supply chain

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Sigstore / cosign | https://docs.sigstore.dev/ | 2026-05-28 | Image signing/verification. |
| Conforma (formerly Enterprise Contract) | https://conforma.dev/ | 2026-05-28 | Policy-as-code verification of supply-chain attestations. |
| Red Hat container certification (preflight) | https://access.redhat.com/documentation/en-us/red_hat_software_certification | 2026-05-28 | Preflight checks for certified containers/operators. |

## Operations & logging

| Source | URL | Last verified | Notes |
|---|---|---|---|
| OpenShift Logging | https://docs.redhat.com/en/documentation/openshift_logging | 2026-05-28 | Logging 6.0 removes EFK; LokiStack + Vector replace Elasticsearch/Fluentd/Kibana. |
| Routes | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/networking/configuring-routes | 2026-05-28 | OpenShift Route resource (vs Ingress). |
