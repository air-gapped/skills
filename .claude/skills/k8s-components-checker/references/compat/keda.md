# KEDA — compat (sifted from published_matrix)

- **Primary source:** https://keda.sh/docs/latest/operate/cluster/
- **Secondary sources:** https://github.com/kedacore/governance/blob/main/SUPPORT.md ; https://github.com/kedacore/keda/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 2.17
- **Last sifted:** 2026-05-28

Support policy: N-2 against Kubernetes minors — each KEDA release tested against the current k8s minor plus the two prior. No formal time-bound EOL; community supports the latest minor + targeted CVE backports to the prior. CVE-2025-68476 was backported to 2.18.3 and 2.17.3 (Dec 2025) — older 2.17.x / 2.18.x are vulnerable; bump.

## 2.19.0 — 2026-02-02

- **k8s floor:** 1.32 – 1.34
- **Breaking:** NATS Streaming (Stan) scaler **removed** (deprecated in 2.17, gone now). Migrate to NATS JetStream before bumping.
- **CRD migrations:** none — `keda.sh/v1alpha1` unchanged.
- **Upgrade ordering:** apply `keda-2.19.0-crds.yaml` before the core manifest. Standard `kubectl apply` works (no conversion webhook flip).
- **Deprecations:** GCP Pub/Sub `subscriptionSize` (use `mode`/`value`) and Huawei Cloudeye `minMetricValue` (use `activationTargetMetricValue`) — both removed in 2.20. Audit ScaledObjects before the next bump.
- **Notable:** fallback now applied in the polling loop (enables scale-from-zero with fallback — previously broken, #7239). `accurateScalingStrategy` honors `pendingJobCount` in `maxReplicaCount` (#7329). Per-trigger activity surfaced in ScaledObject/ScaledJob status (`status.triggersStatus`) — alerts that scrape `kedaTriggerTotals` keep working; alerts that parse status JSON need updating.

## 2.18.0 — 2025-10-08 (latest patch: 2.18.3, 2025-12-22)

- **k8s floor:** 1.31 – 1.33
- **Breaking:**
  - **Prometheus webhook `prommetrics` deprecations removed** (#6698). Dashboards / alerts on the old metric names go silent on bump — grep Grafana for `keda_webhook_*` legacy names and update.
  - CPU/Memory scaler: `type` field **removed**, use `metricType` (deprecated since 2.13).
  - IBM MQ scaler: `tls` field **removed**, use `unsafeSsl`.
- **CRD migrations:** none.
- **Upgrade ordering:** apply CRDs first; from 2.17 → 2.18 there is no conversion required, but the admission webhook (2.17.1+) rejects ScaledObjects without `metricType` when `fallback` is set — fix manifests before the operator restarts or new applies fail.
- **Deprecations:**
  - GCP Pub/Sub `subscriptionSize` → removal in 2.20.
  - Huawei Cloudeye `minMetricValue` → removal in 2.20.
  - NATS Streaming (Stan) scaler — removed in 2.19; final warning here.
- **Notable:**
  - Fallback support extended to `Value` metric type (#6655) — previously `AverageValue` only.
  - **CVE-2025-68476** fixed in **2.18.3**. Anything below is vulnerable.
  - 2.18.2 fixed HPA behavior not restored when `autoscaling.keda.sh/paused-scale-in/out` annotation is deleted without a corresponding custom HPA behavior — operationally hot for any deploy that uses pause annotations.
  - 2.18.1 added `KEDA_CHECK_UNEXPECTED_SCALERS_PARAMS` feature flag; default off, but turn on in staging to catch silent typos in trigger metadata.

## 2.17.0 — 2025-04-07 (latest patch: 2.17.3, 2025-12-22)

- **k8s floor:** 1.30 – 1.32
- **Breaking:**
  - `InitialCooldownPeriod` type changed from `int32` to `*int32` (#6423) — clients generated from the Go API (custom controllers, kubebuilder reconcilers) need regeneration; raw YAML is unaffected.
  - Prometheus metric deprecations removed (#6339) — recurring drumbeat; check dashboards again.
  - External scaler: deprecated `tlsCertFile` field **removed** — use the cert mount + `tlsCertSecret` pattern.
- **CRD migrations:** none.
- **Upgrade ordering:** apply CRDs first. From 2.16 → 2.17 the admission webhook (2.17.1+) starts **rejecting** ScaledObjects that set `fallback` without `metricType` (#6696). Pre-flight with `kubectl get scaledobjects -A -o json | jq '.items[] | select(.spec.fallback != null and (.spec.triggers[]?.metricType // "") == "")'` before the webhook upgrades, or applies queue up errors.
- **Deprecations:** NATS Streaming (Stan) scaler — first formal deprecation, removed in 2.19.
- **Notable:**
  - **CVE-2025-68476** fixed in **2.17.3**. Anything below is vulnerable.
  - 2.17.2 hot-reloads internal gRPC cert (keda-operator ↔ keda-metrics-apiserver) — eliminates a restart-on-rotation operational footgun, no action needed but pin ≥ 2.17.2 if cert-manager rotates the internal serving cert.
  - 2.17.1 fix to `ScalerCache` locking — sub-2.17.1 can panic the operator under high churn; treat 2.17.0 as effectively superseded.
