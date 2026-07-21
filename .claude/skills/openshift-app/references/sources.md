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
| OpenShift Container Platform release notes | https://docs.redhat.com/en/documentation/openshift_container_platform | 2026-07-21 | **OCP 4.22 GA 2026-07-14** (RHEA-2026:0449, Kubernetes 1.35, CRI-O 1.35); 4.21 GA ~Feb 2026; 4.20 GA 2025-11-12. Span updated to "4.14-4.22". Direct fetch of the 4.22 release-notes page returns **403** — reachable via search summaries only, so the 4.22 timeline row is explicitly incomplete. |
| openshift/oc release tags | https://github.com/openshift/oc/tags | 2026-07-21 | `openshift-clients-4.22.0-202605222050` present. Useful as an early GA tell: the client tag appeared ~2 months before 4.22 GA, so a client tag alone proves builds exist, **not** that the minor has shipped. |
| Red Hat OpenShift lifecycle policy | https://access.redhat.com/support/policy/updates/openshift | 2026-07-21 | OVN-Kubernetes mandatory / OpenShift SDN removed in 4.17; cgroup v1 removed in 4.19; restricted-v2 default since 4.11. Policy re-read: **≥4 minor versions supported at any time**; Full Support = 6 months or 90 days past the next minor's GA, whichever is longer; Maintenance = 18 months from GA; **EUS = even-numbered minors** (so 4.20 and 4.22 are EUS, 4.21 is not). The page carries no per-version date table — that lives on the Product Life Cycles page. |
| OKD release page | https://github.com/okd-project/okd/releases | 2026-07-21 | OKD at `4.22.0-okd-scos.7` (2026-07-13), and a **`5.0.0-okd-scos.ec.5`** early-candidate line now exists alongside it. OKD leads OCP, so an OKD tag is a leading indicator, never proof that the matching OCP minor has shipped — the previous pass inferred "4.21 is current" from `4.22.0-okd-scos.1`, which was right by luck. |

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
| Helm releases | https://github.com/helm/helm/releases | 2026-07-21 | Helm 4.0.0 released November 2025 (SSA default); **both lines are live — v4.2.3 and v3.21.3 shipped the same day, 2026-07-09.** OCP-bundled Helm version for 4.22 still NOT verified (docs 403). |
| Helm version support / skew | https://helm.sh/docs/topics/version_skew | 2026-07-21 | **VERIFY resolved: the Helm 3 EOL dates are not published.** This page and `helm.sh/docs/community/release_policy` both say only that the most recent minor gets cherry-picked fixes; neither names a Helm 3 sunset. The skill's "bug fixes July 8 2026 / security fixes November 11 2026" had no citable source and is contradicted by v3.21.3 shipping 2026-07-09. Claim removed rather than re-dated. |
| Operator Lifecycle Manager v1 (ClusterExtension) | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/extensions/index | 2026-07-21 | **VERIFY resolved: OLM v1 is GA as of OCP 4.18**, with OLM (Classic) as the retronym. Initial GA scope: `registry+v1` bundles, AllNamespaces install mode, no webhooks. The skill's "4.18 timeframe" guess was correct. |
| Operator SDK | https://sdk.operatorframework.io/ | 2026-07-21 | **VERIFY resolved, and it is two gates not one:** the deprecation *notice* landed at OCP 4.16, but **4.18 was the last OpenShift planned to ship the SDK CLI**. On 4.19+ it is not bundled — install from upstream, which continues independently. The skill previously implied 4.16 was the whole story. |

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
