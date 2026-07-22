# Sources — rancher-logging-exit

Dated per-URL index backing this skill's factual claims. Freshen Mode probes each
row and stamps `Last verified`.

## Most recent freshen pass: 2026-07-22

Initial creation. Every row probed live 2026-07-22 (research pass: 9 agents over
2 rounds; rancher/charts chart internals read from local clone + release branches
via gh), same day the skill was authored.

**Freshen watch-list (things that would change this skill):** a SUSE advisory or
backport for CVE-2026-54680 · a rancher-logging rebase off 4.10.0 (check newest
`+upX.Y.Z` on release-v2.1{4,5,6} branches) · a formal deprecation/replacement of
rancher-logging · upstream releases past 6.7.0 (floor bump) · NVD publishing the
CVE.

## Primary sources

| Ref | URL | Grounds | Last verified | Pinned |
|---|---|---|---|---|
| GHSA-mjqf-28ph-426h | https://github.com/kube-logging/logging-operator/security/advisories/GHSA-mjqf-28ph-426h | CVE mechanics, CVSS 9.9, ≤6.5.2 affected / 6.6.0 patched, IMDS-theft example | 2026-07-22 | — |
| rancher/charts branches | https://github.com/rancher/charts (release-v2.11…release-v2.15, dev-v2.1x; assets/rancher-logging) | chart-line enumeration per Rancher minor; all `+up4.10.0`; kube-gate annotations | 2026-07-22 | branch heads 2026-07-22 |
| rancher-logging chart internals | rancher/charts `charts/rancher-logging{,-crd}/107.0.2+up4.10.0-rancher.15/` (+109.0.0 via gh) | values (images, disablePvc default, systemDefaultRegistry, loggingServiceAccountAnnotations), userroles.yaml RBAC aggregation, journald DaemonSet templates, windowsEnabled-gated nodeAgents, NO resource-policy keep in CRD chart | 2026-07-22 | chart 107.0.2 / 109.0.0 |
| rancher/ob-team-charts | https://github.com/rancher/ob-team-charts | -rancher.N fork anatomy (chart-level only), version policy README, no post-CVE logging commits, issue #218 | 2026-07-22 | — |
| upstream releases | https://github.com/kube-logging/logging-operator/releases | 4.10.0 date, 5.0/5.3/6.0 breaking boundaries, 6.6.0/6.7.0 fix pair, air-gap image tables | 2026-07-22 | — |
| upstream chart @6.7.0 | https://github.com/kube-logging/logging-operator/tree/6.7.0/charts | crds/-dir skip semantics, logging-operator-crds subchart + `--skip-crds` guidance, CRD file sizes (828KB/557KB) | 2026-07-22 | tag 6.7.0 |
| CRD schema diff | rancher chart CRDs vs upstream 6.7.0 CRDs (local diff, research pass) | silent-pruning field list (sumologic, enhanceK8s, enabledNamespaces, nodeAgents); v1beta1 storage both sides | 2026-07-22 | 4.10-era vs 6.7.0 |
| StatefulSet/PVC naming | kube-logging/logging-operator pkg/resources/fluentd (4.10.0 vs 6.7.0) | `<logging>-fluentd` + `fluentd-buffer` stable ⇒ PVC preservation rule | 2026-07-22 | tags 4.10.0/6.7.0 |
| Axoflow Rancher-migration blog | https://axoflow.com/blog/get-the-latest-logging-operator-in-rancher | maintainer-endorsed release-secret strategy; historical 3.17 freeze precedent | 2026-07-22 (content 2023-09) | — |
| Rancher advisories page | https://ranchermanager.docs.rancher.com/reference-guides/rancher-security/security-advisories-and-cves | no logging CVE listed (negative evidence) | 2026-07-22 | — |
| SUSE CVE page | https://www.suse.com/security/cve/CVE-2026-54680.html | 404 = unpublished (negative evidence) | 2026-07-22 | — |
| rancher/rancher releases | https://github.com/rancher/rancher/releases (v2.12.0–v2.14.0) | no rancher-logging deprecation in release notes | 2026-07-22 | — |

## Community / secondary

| Ref | URL | Grounds | Last verified |
|---|---|---|---|
| eumel.de migration blog | https://k8sblog.eumel.de/2023/08/08/migrate-rancher-logging-en.html | annotation-size failure on client-side CRD apply (independent confirmation) | 2026-07-22 |
| Sylva MR 3577 | https://gitlab.com/sylva-projects/sylva-core/-/merge_requests/3577 | production coexistence/gradual-adoption pattern (2025) | 2026-07-22 |
| janeczku/rancher-v2-logging | https://github.com/janeczku/rancher-v2-logging | legacy management.cattle.io CRD cleanup | 2026-07-22 |
| fluent-bit CVE set | https://kb.cert.org/vuls/id/761751 + New Relic NR25-02 + Oligo writeup | five-CVE plugin mapping → default-config non-exploitability analysis | 2026-07-22 |
| CVE-2019-12303 | historical Rancher advisory record | same-class precedent (project-owner fluentd config injection) | 2026-07-22 |
| upstream #2254/#2255, #1522 | github.com/kube-logging/logging-operator issues/PRs | 6.6.0 newline-password regression + fix; ghcr OCI 403s | 2026-07-22 |

Related local artifact: the user's pre-skill draft
`~/projects/github.com/kube-logging/LOGGING_OPERATOR_MIGRATION.md` (2025-10-23) —
superseded by this skill (six corrections applied; see research report §T9).
