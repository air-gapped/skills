# Sources

External references this skill's content is grounded in. Each row was verified
on the date shown. When re-freshening, re-check the oldest row first and bump
the date after confirming the cited fact still holds.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| KEDA core repo | https://github.com/kedacore/keda | 2026-07-21 | Operator, metrics-apiserver, admission-webhooks; CRDs under `config/crd/bases/`. |
| KEDA latest release | https://github.com/kedacore/keda/releases/latest | 2026-07-21 | Latest is **v2.20.1** (2026-06-08; patch over v2.20.0, 2026-06-01). Install assets: `keda-2.20.1.yaml`, `-core.yaml`, `-crds.yaml`. 2.20 upgrade note: events moved to `events.k8s.io` (RBAC). Next release estimated 2nd week of September 2026. |
| ScaledObject CRD (v2.20.1) | https://github.com/kedacore/keda/blob/v2.20.1/config/crd/bases/keda.sh_scaledobjects.yaml | 2026-07-21 | Single served version `v1alpha1`; no v1beta1/v1 graduation. `scalingModifiers` present (origin KEDA 2.13+); 2.20 adds CRD-level validation markers. |
| k8s compatibility matrix | https://github.com/kedacore/keda-docs/blob/main/content/docs/2.20/operate/cluster.md | 2026-07-21 | N-2 tested window: **v2.20 → k8s v1.33–v1.35**; v2.19 → v1.32–v1.34. |
| KEDA 2.20.0 release notes | https://github.com/kedacore/keda/releases/tag/v2.20.0 | 2026-07-21 | OpenSearch + Elastic Forecast scalers, `scalingModifiers` fallback behavior, AWS External ID, scaler HTTP metrics. Breaking: GCP Pub/Sub `subscriptionSize`, Huawei `minMetricValue`, IBM MQ `tls`, InfluxDB `authToken`-in-metadata all removed. |
| CVE-2025-68476 advisory | https://github.com/kedacore/keda/security/advisories/GHSA-c4p6-qg4m-9jmr | 2026-07-21 | Arbitrary File Read via HashiCorp Vault `TriggerAuthentication`; published 2025-12-22. Fixed in **2.17.3 / 2.18.3 / 2.19.0+**. |
| KEDA HTTP Add-on repo | https://github.com/kedacore/http-add-on | 2026-07-21 | API group `http.keda.sh/v1alpha1`, CRD `HTTPScaledObject`. Latest v0.15.0 (2026-06-15): HTTP/2 + gRPC, `coldStart.placeholder`, graceful drain. README status is **beta** but now worded "stable, actively maintained, v1.0 planned" — no longer "not recommended for production". |
| Helm charts | https://github.com/kedacore/charts (repo: https://kedacore.github.io/charts) | 2026-07-21 | `kedacore/keda` and `kedacore/keda-add-ons-http` charts; source of the `values.yaml` knobs in `operations.md`. OTel keys are `opentelemetry.operator.enabled` + `opentelemetry.collector.uri`. |
| Scalers documentation | https://keda.sh/docs/latest/scalers/ | 2026-07-21 | 70+ scaler catalog; authoritative field names. Cross-check Go source under `keda/pkg/scalers/<name>_scaler.go` when docs lag. |
| expr-lang (scalingModifiers grammar) | https://expr-lang.org/ | 2026-07-21 | Formula grammar for `advanced.scalingModifiers.formula`: `+ - * /`, ternary, `min`/`max`/`ceil`/`floor`/`abs`. |
| HPA v2 behavior spec | https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior | 2026-07-21 | Upstream semantics for `advanced.horizontalPodAutoscalerConfig.behavior`; 15s sync period drives the stabilization-window alignment rule. |
