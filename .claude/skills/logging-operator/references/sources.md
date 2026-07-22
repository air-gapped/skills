# Sources — logging-operator

Dated per-URL index backing this skill's factual claims. Freshen Mode probes each
row and stamps `Last verified` (and `Pinned` where applicable).

## Most recent freshen pass: 2026-07-22

Initial creation. Every row probed live 2026-07-22 (research pass: 9 agents over 2
rounds + local clones of kube-logging/logging-operator and kube-logging.github.io
at Oct-2025 snapshots, currency cross-checked via gh at tags/master), same day the
skill was authored.

## Primary sources

| Ref | URL | Grounds | Last verified | Pinned |
|---|---|---|---|---|
| releases | https://github.com/kube-logging/logging-operator/releases | timeline 4.0→6.7.0, breaking changes, component versions | 2026-07-22 | — |
| GHSA-mjqf-28ph-426h | https://github.com/kube-logging/logging-operator/security/advisories/GHSA-mjqf-28ph-426h | CVE-2026-54680: CVSS 9.9, ≤6.5.2 affected, 6.6.0 hardened | 2026-07-22 | — |
| output_types.go | https://github.com/kube-logging/logging-operator/blob/6.7.0/pkg/sdk/logging/api/v1beta1/output_types.go | 31 output fields | 2026-07-22 | tag 6.7.0 |
| syslogng_output_types.go | https://github.com/kube-logging/logging-operator/blob/6.7.0/pkg/sdk/logging/api/v1beta1/syslogng_output_types.go | 18 syslog-ng output fields + driver names | 2026-07-22 | tag 6.7.0 |
| logging_types.go | https://github.com/kube-logging/logging-operator/blob/6.7.0/pkg/sdk/logging/api/v1beta1/logging_types.go | Logging spec keys, configCheck strategies (DryRun/StartWithTimeout, timeout 10), default images | 2026-07-22 | tag 6.7.0 |
| fluentd_types.go / fluentbit_types.go | https://github.com/kube-logging/logging-operator/tree/6.7.0/pkg/sdk/logging/api/v1beta1 | UID 100/101 defaults, 20Gi buffer PVC, Merge_Log default On, resources, no direct fluentbit outputs | 2026-07-22 | tag 6.7.0 |
| fluentd image Dockerfile+Gemfiles | https://github.com/kube-logging/logging-operator/tree/6.7.0/images/fluentd | -base/-filters/-full variant contents; awsElasticsearch/logdna gems commented out; forked es+syslog gems | 2026-07-22 | tag 6.7.0 |
| chart | https://github.com/kube-logging/logging-operator/tree/6.7.0/charts/logging-operator | crds/ + logging-operator-crds subchart duality, `--skip-crds` guidance, kubeVersion ≥1.22, telemetry-controller conditional | 2026-07-22 | tag 6.7.0 |
| config/samples | https://github.com/kube-logging/logging-operator/tree/6.7.0/config/samples | containerd-merge-log CRI workaround, all-to-file, syslog-ng-otlp, configcheck-timeout | 2026-07-22 | tag 6.7.0 |
| design docs | https://github.com/kube-logging/logging-operator/tree/master/docs (multi-tenancy, logging-route, fluentbit-flow-control, volume-drainer, scaling, multi-worker) | isolation ladder, LoggingRoute, backpressure chain, drainer, HPA-replicas rule | 2026-07-22 | — |
| docs site | https://kube-logging.dev/docs/ (quickstarts/single, configuration/log-routing, plugins/filters/parser, operation/troubleshooting, whats-new, image-versions, install) | quickstart chain + record shapes, match semantics, parser flags, rendered-secret debugging, support statements | 2026-07-22 | — |
| telemetry-controller | https://github.com/kube-logging/telemetry-controller | 0.5.6, v1alpha1, 6 outputs, OTel-operator dependency | 2026-07-22 | tag 0.5.6 |

## Community / issue-tracker (gotcha grounding)

| Ref | URL | Grounds | Last verified |
|---|---|---|---|
| #890 | https://github.com/kube-logging/logging-operator/issues/890 | JSON-parsing doc pain (verbatim), Loki label extraction | 2026-07-22 |
| #1784 / #1007 / #1353 | …/issues/1784 etc. | CRI message-vs-log confusion class | 2026-07-22 |
| #2013 | …/issues/2013 | one dead Output stalls all; StartWithTimeout limits | 2026-07-22 |
| #2131 | …/issues/2131 | mem-buf overlimit intermittent loss; filesystem-buffer tuning | 2026-07-22 |
| #1490 / #1023 | …/issues/1490, 1023 | detectExceptions + configcheck broken multi-worker (open) | 2026-07-22 |
| #674 / #661 | …/issues/674, 661 | Loki ordering, uneven forward LB across replicas | 2026-07-22 |
| #2153 / #2145 / #2254 | …/issues/2153 etc. | 6.2.1 ES 8.x break; bufferVolumeMetrics nil; 6.6.0 newline-password regression | 2026-07-22 |
| #1251 / #1716 | …/issues/1251, 1716 | gem-conflict history → forked es + syslog_rfc5424 gems | 2026-07-22 |
| #1908 / #1954 / #1993 / #2191 / #1556 | assorted | non-root PVC ownership; fluentbit disk full; eventrouter leak; protected-for-Flows ask; missing runbooks | 2026-07-22 |
| Axoflow TC blog | https://axoflow.com/blog/kubernetes-logging-telemetry-controller-logging-operator | TC+operator architecture guidance (2024-07, still canonical) | 2026-07-22 |
| CNCF listing | https://www.cncf.io/projects/logging-operator-kube-logging/ | Sandbox since 2023-09 | 2026-07-22 |
