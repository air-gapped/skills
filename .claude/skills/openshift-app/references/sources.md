# Sources

Freshened: 2026-09-22 — every row probed; all URLs 200. OCP 4.20/4.21/4.22 GA dates, the OVN, cgroup-v2, restricted-v2 and OLM v1 claims all reproduce against Red Hat's own lifecycle and docs pages. No 4.23 yet.

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
| OpenShift Container Platform release notes + lifecycle API | https://docs.redhat.com/en/documentation/openshift_container_platform | 2026-10-27 | GA dates from the Product Life Cycles API (`product-life-cycles/api/v1/products?name=OpenShift%20Container%20Platform%204`): **4.22 2026-06-09** (RHEA-2026:0449; K8s 1.35, CRI-O 1.35), **4.21 2026-02-03**, **4.20 2025-10-21** (this row previously said 2025-11-12 — wrong), 4.19 2025-06-17, 4.18 2025-02-25. Stable-channel z-stream ceilings 2026-10-27: 4.20.42, 4.21.37, 4.22.18. **OCP 5.0 not GA**: `candidate-5.0` carries 5.0.0-rc.N, `stable-5.0` graph is empty; no 4.23 stable either. *Exception 2026-10-27: docs.redhat.com returned 503 (site outage page) for the release-notes pages; GA facts taken from the lifecycle API instead.* |
| Red Hat API removals index (KCS 6955985) | https://access.redhat.com/articles/6955985 | 2026-10-27 | Lists removals per OCP minor: 4.17/4.18 none; 4.19 (KCS 7112216: K8s 1.32 drops `flowcontrol.apiserver.k8s.io/v1beta3`, admin-ack gate added in 4.18.13, all clusters need it); 4.20 (KCS 7130599, body subscriber-only: `admissionregistration.k8s.io/v1beta1`, inadvertently served since 4.17); "no Kubernetes API removals in 4.21+ unless added here". Upstream cross-check: kubernetes.io deprecation-guide's newest removal section is v1.32. Replaced the skill's "4.19 list not yet enumerated" absence claim. |
| openshift/oc release tags | https://github.com/openshift/oc/tags | 2026-10-27 | Newest client tags `openshift-clients-4.22.0-202605222050` and `openshift-clients-4.21.0-202601121715`; no 4.23 or 5.x client tags. A client tag appears ~2 weeks before GA (4.22: tag 2026-05-22, GA 2026-06-09), so it proves builds exist, **not** that the minor has shipped. |
| Red Hat OpenShift lifecycle policy | https://access.redhat.com/support/policy/updates/openshift | 2026-10-27 | OVN-Kubernetes mandatory / OpenShift SDN removed in 4.17; cgroup v1 removed in 4.19; restricted-v2 default since 4.11. Policy re-read: **≥4 minor versions supported at any time**; Full Support = 6 months or 90 days past the next minor's GA, whichever is later; Maintenance = 18 months from GA; **EUS = even-numbered minors**. The page has no per-version date table — use the lifecycle API row above. |
| OKD release page | https://github.com/okd-project/okd/releases | 2026-10-27 | OKD 5.0 has GA-style tags: `5.0.0-okd-scos.0` (2026-09-17) through `.3` (2026-10-21, isLatest); `5.1.0-okd-scos.ec.0` open; 4.22 line ended at `4.22.0-okd-scos.10` (2026-09-09). OKD leads OCP, so an OKD tag is a leading indicator, never proof that the matching OCP release has shipped — OCP 5.0 was still RC-only on the same date. |

## Deployments & workloads

| Source | URL | Last verified | Notes |
|---|---|---|---|
| DeploymentConfig deprecation | https://access.redhat.com/articles/7041372 | 2026-05-28 | "As of OpenShift 4.14, DeploymentConfig objects are deprecated ... not recommended for new installations. Instead, use Deployment objects." Exact docs snippet confirmed via `gh search code` in openshift/openshift-docs (snippets/deployment-config-deprecated.adoc). Deprecated, not removed. |
| ImageStream triggers (image.openshift.io/triggers) | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/images/triggering-updates-on-imagestream-changes | 2026-05-28 | Annotation-based trigger pattern for Deployments. |

## Container images (UBI)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Red Hat Universal Base Images (UBI) | https://catalog.redhat.com/software/base-images | 2026-10-27 | ubi9/ubi, ubi-minimal, ubi-micro, ubi-init at registry.access.redhat.com/ubi9/*; microdnf is the ubi-minimal package manager; ubi-micro ships no package manager. **UBI 10**: `registry.access.redhat.com/v2/ubi10/{ubi,ubi-minimal,ubi-micro,ubi-init}/tags/list` all return 10.x tags (10.2 current for minimal/micro/init); catalog page `ubi10/ubi-minimal/66f1504a379b9c2cf23e145c` 200; RHEL 10 GA 2025-05-20 (lifecycle API). |
| UBI documentation | https://www.redhat.com/en/blog/introducing-red-hat-universal-base-image | 2026-05-28 | Background on UBI variants and redistribution terms. |

## Security (SCC / PSA)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Managing SCCs | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/authentication_and_authorization/managing-pod-security-policies | 2026-05-28 | restricted-v2 is the default SCC since 4.11; arbitrary UID + GID 0 group requirement. |
| Red Hat FIPS compliance page | https://access.redhat.com/compliance/fips | 2026-10-27 | Per-RHEL-minor FIPS 140-3 certificate table with the OCP version each minor maps to. OpenSSL #4857 Active for RHEL 9.0-9.8 (9.2→OCP 4.15, 9.4→4.18, 9.6→4.20, 9.8→4.22); libgcrypt #5366, kernel #5034/#5445, GnuTLS #4846, NSS #5022 cover 9.2/9.4 only; 9.6+ lists only OpenSSL validated; RHEL 10.0 OpenSSL pending. |
| NIST FIPS 140-3 transition | https://csrc.nist.gov/projects/fips-140-3-transition-effort | 2026-10-27 | "September 22, 2026 — All FIPS 140-2 certificates are placed on the Historical List." Replaced the skill's expired "140-2 active through 2026-09-21" block. |
| Pod Security Admission in OpenShift | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/authentication_and_authorization/understanding-and-managing-pod-security-admission | 2026-05-28 | PSA enforcement labels and the restricted-v2-vs-PSS-restricted relationship. |

## Packaging (Helm / Operators / OLM v1)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Helm releases | https://github.com/helm/helm/releases | 2026-10-27 | Helm 4.0.0 released November 2025 (SSA default). Both lines ship patches the same day: **v4.3.1 (isLatest) and v3.22.1, both 2026-10-15**; v4.3.0 2026-09-09, v3.22.0 2026-09-10. No v3.23. |
| Helm v3 end of life | https://helm.sh/blog/helm-v3-end-of-life/ | 2026-10-27 | Blog post (2026-06-02): bug fixes up to the final feature release on **2026-09-09** (shipped as v3.22.0, 2026-09-10, limited to Kubernetes client-library updates); security fixes end **2027-02-10** (extended from November 2026); after that no further Helm 3 releases of any kind. The `version_skew` and `release_policy` docs pages carry no Helm 3 sunset — this blog is the source. |
| Operator Lifecycle Manager v1 (ClusterExtension) | https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/extensions/index | 2026-07-21 | **VERIFY resolved: OLM v1 is GA as of OCP 4.18**, with OLM (Classic) as the retronym. Initial GA scope: `registry+v1` bundles, AllNamespaces install mode, no webhooks. The skill's "4.18 timeframe" guess was correct. |
| operator-controller (OLM v1) RBAC template | https://github.com/operator-framework/operator-controller/blob/main/test/e2e/steps/testdata/rbac-template-for-all-extensions.yaml | 2026-10-27 | Installer ClusterRole grants `clusterextensions/finalizers` and `clusterobjectsets[/finalizers]` in **`olm.operatorframework.io`** (CRD `clusterobjectsets.olm.operatorframework.io`; ClusterExtensionRevision renamed to ClusterObjectSet in operator-controller#2589, 2026-03-30; Boxcutter runtime, documented under `docs/draft/`). `package-operator.run` is a different project's API group (package-operator's own ClusterObjectSet) — the skill had it wrong. |
| Operator SDK | https://sdk.operatorframework.io/ | 2026-07-21 | **VERIFY resolved, and it is two gates not one:** the deprecation *notice* landed at OCP 4.16, but **4.18 was the last OpenShift planned to ship the SDK CLI**. On 4.19+ it is not bundled — install from upstream, which continues independently. The skill previously implied 4.16 was the whole story. |

## CI/CD & GitOps

| Source | URL | Last verified | Notes |
|---|---|---|---|
| OpenShift Pipelines (Tekton) | https://docs.redhat.com/en/documentation/red_hat_openshift_pipelines | 2026-05-28 | Tekton-based CI on OpenShift. |
| OpenShift GitOps (Argo CD) | https://docs.redhat.com/en/documentation/red_hat_openshift_gitops | 2026-10-27 | Operator 1.22 current (1.22.0 2026-09-30, 1.22.2 2026-10-15). Compatibility matrix, `openshift/openshift-docs` branch `gitops-docs-1.22`, `modules/go-compatibility-and-support-matrix.adoc`: **1.22.0 = Argo CD 3.5.3 + Helm 4.2.4**, Image Updater 1.3.0 GA, GitOps Promoter 0.35.0 TP; 1.21.0 = Argo CD 3.4.3 + Helm 3.19.4, Image Updater 1.2.1 GA; 1.20.0 = Argo CD 3.3.2 + Helm 3.19.4, Image Updater 1.1.2 TP. Release notes `modules/gitops-release-notes-1-22-0.adoc`. The GitHub operator release feed lags (v1.20.0) — use the docs branch. |
| Argo CD releases + Helm pin | https://github.com/argoproj/argo-cd/releases | 2026-10-27 | Per line: 3.5.6 (2026-10-20, isLatest), 3.4.12 (2026-10-20), 3.3.18 (2026-10-22); 3.6 has RCs only (v3.6.0-rc4, 2026-10-22). `hack/tool-versions.sh`: v3.5.6 `helm4_version=4.2.1`; v3.6.0-rc4 `HELM_VERSION=4.3.1`; v3.4.12 and v3.3.18 `helm3_version=3.19.4`. Helm 4 migration: PR #28076, merged 2026-06-09, first in v3.5.0 (2026-08-04). argoproj/argo-cd#29068 (Helm 4 null-coalescing render change, docs request) still OPEN, no linked fix. |
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
| Red Hat Product Life Cycles API (layered products) | https://access.redhat.com/product-life-cycles/api/v1/products?name=Red%20Hat%20OpenShift%20Service%20Mesh | 2026-10-27 | Machine-readable GA / Full / Maintenance dates and `openshift_compatibility` per layered-product minor; swap `name=` for Pipelines, Trusted Artifact Signer, `builds for Red Hat OpenShift`. Read dates, not the `type` field (it lags: 3.3 still says "Full Support" after its 2026-09-21 full-support end). **Service Mesh:** 3.4 GA 2026-07-09 (OCP 4.20-4.22); 3.3 and 3.2 OCP 4.18-4.22; 3.0 maintenance ends 2026-10-31; 2.6 maintenance ended 2026-06-30. **Trusted Artifact Signer:** 1.5 GA 2026-10-06 (OCP 4.19-4.22); 1.4 GA 2026-04-16 (4.18-4.22); 1.3 (4.16-4.20). **Pipelines:** 1.24 GA 2026-09-17 (OCP 4.14, 4.16, 4.18-4.22, 5.0; maint to 2027-01-31); 1.23 GA 2026-07-17 (to 2026-12-31); 1.22 GA 2026-04-27 (4.16, 4.18-4.22; ended 2026-09-30); 1.21 GA 2026-01-22 (4.14, 4.16-4.20 — not 4.21; ended 2026-07-17); 1.20 GA 2025-09-25; 1.17 GA 2024-12-12 (4.15-4.18). **Builds:** 1.9 GA 2026-08-19 (4.18-4.22); 1.8 GA 2026-05-18 (4.17-4.21); 1.7 GA 2026-02-10 (4.16-4.21); 1.6 GA 2025-10-10 (4.16-4.19); 1.0 GA 2023-12-04 (4.12-4.15). |
| OpenShift Logging | https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.6 | 2026-09-15 | Logging 6.0 removes EFK; LokiStack + Vector replace Elasticsearch/Fluentd/Kibana. **URL corrected — the old `openshift_logging` slug is a bare 404 with no redirect**; current docs are Logging 6.6. |
| Routes | https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/ingress_and_load_balancing/index | 2026-09-15 | OpenShift Route resource (vs Ingress). **URL corrected — Routes moved out of the `networking` guide into `ingress_and_load_balancing` at OCP 4.20**; 4.17–4.19 still resolve at the old path, 4.20+ 404 there. |
