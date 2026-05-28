# Sources

External references this skill's content is grounded in. Each row was verified
on the date shown. When re-freshening, re-check the oldest row first and bump
the date after confirming the cited fact still holds.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| KEDA core repo | https://github.com/kedacore/keda | 2026-05-28 | Operator, metrics-apiserver, admission-webhooks; CRDs under `config/crd/bases/`. |
| KEDA latest release | https://github.com/kedacore/keda/releases/latest | 2026-05-28 | Latest is **v2.19.0** (published 2026-02-02). Install assets: `keda-2.19.0.yaml`, `keda-2.19.0-core.yaml`, `keda-2.19.0-crds.yaml`. No v2.20.0 exists. |
| ScaledObject CRD (v2.19.0) | https://github.com/kedacore/keda/blob/v2.19.0/config/crd/bases/keda.sh_scaledobjects.yaml | 2026-05-28 | Single served version `v1alpha1`; no v1beta1/v1 graduation. `scalingModifiers` present (origin KEDA 2.13+). |
| k8s compatibility matrix | https://github.com/kedacore/keda-docs/blob/main/content/docs/2.19/operate/cluster.md | 2026-05-28 | N-2 tested window: **v2.19 → k8s v1.32–v1.34**. |
| CVE-2025-68476 advisory | https://github.com/kedacore/keda/security/advisories/GHSA-c4p6-qg4m-9jmr | 2026-05-28 | Arbitrary File Read via HashiCorp Vault `TriggerAuthentication`; published 2025-12-22. Fixed in **2.17.3 / 2.18.3 / 2.19.0+**. |
| KEDA HTTP Add-on repo | https://github.com/kedacore/http-add-on | 2026-05-28 | API group `http.keda.sh/v1alpha1`, CRD `HTTPScaledObject`. README still carries the **beta** banner ("not recommended for production"). Latest release v0.14.0 (2026-04-24). |
| Helm charts | https://github.com/kedacore/charts (repo: https://kedacore.github.io/charts) | 2026-05-28 | `kedacore/keda` and `kedacore/keda-add-ons-http` charts; source of the `values.yaml` knobs in `operations.md`. |
| Scalers documentation | https://keda.sh/docs/latest/scalers/ | 2026-05-28 | 70+ scaler catalog; authoritative field names. Cross-check Go source under `keda/pkg/scalers/<name>_scaler.go` when docs lag. |
| expr-lang (scalingModifiers grammar) | https://expr-lang.org/ | 2026-05-28 | Formula grammar for `advanced.scalingModifiers.formula`: `+ - * /`, ternary, `min`/`max`/`ceil`/`floor`/`abs`. |
| HPA v2 behavior spec | https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior | 2026-05-28 | Upstream semantics for `advanced.horizontalPodAutoscalerConfig.behavior`; 15s sync period drives the stabilization-window alignment rule. |
