# KEDA — compat (sifted from published_matrix)

- **Primary source:** https://keda.sh/docs/latest/operate/cluster/
- **Secondary sources:** https://github.com/kedacore/governance/blob/main/SUPPORT.md ; https://github.com/kedacore/keda/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 2.17
- **Last sifted:** 2026-09-24 — 2.21.0 added (new line, k8s 1.34–1.36); 2.17–2.20 line ceilings and windows re-checked, **unchanged**.
- **Last release-verified:** 2026-09-24 — all patch/version numbers below confirmed against `generated.json` (compat.py sync 2026-09-24) and `gh release view`.
- **A third CVE, critical, hits every line below 2.21.** **CVE-2026-77524 / GHSA-637c-6jxx-4rwm (critical)**: `TriggerAuthentication`/`ClusterTriggerAuthentication` using Vault Kubernetes auth or any `boundServiceAccountToken` (Metrics API, Prometheus, Loki, Datadog Cluster Agent, etc.) accepted service-account tokens without an explicit audience, letting a namespace-scoped attacker escalate to cluster-admin. **Vulnerable ≤2.20.2 — every 2.17.x/2.18.x/2.19.x/2.20.x patch this file tracks, with no backport.** Fixed only in **2.21.0**.

Support policy: N-2 against Kubernetes minors — each KEDA release tested against the current k8s minor plus the two prior. No formal time-bound EOL; community supports the latest minor + targeted CVE backports to the prior. CVE-2025-68476 was backported to 2.18.3 and 2.17.3 (Dec 2025) — older 2.17.x / 2.18.x are vulnerable; bump. CVE-2026-53572 fixed only in 2.20 (no backport). CVE-2026-77524 fixed only in 2.21 (no backport) — this is the higher-priority driver for any cluster on 2.17–2.20 using Vault or bound-token scaler auth.

## 2.21.0 — 2026-09-23 (latest patch: **2.21.0** — release-verified 2026-09-24)

- **k8s floor:** **1.34 – 1.36** (keda.sh/docs/2.21/operate/cluster/, N-2 window).
- **⚠️ CRITICAL — CVE-2026-77524 / GHSA-637c-6jxx-4rwm fixed here, no backport.** See header. KEDA 2.21 defaults `operator.serviceAccountTokens.mode` to `enforce-audience`: Vault Kubernetes auth and all `boundServiceAccountToken` auth now require an explicit, receiver-accepted audience — missing audience mappings make the affected scaler/auth fail (the operator itself stays up). **Audit every `TriggerAuthentication`/`ClusterTriggerAuthentication` with `spec.hashiCorpVault.authentication: kubernetes` or `spec.boundServiceAccountToken` and configure audiences on both KEDA and the receiver before upgrading**, or use the insecure `operator.serviceAccountTokens.mode: legacy` escape hatch as a temporary bridge (KEDA logs warnings while it's set). See keda.sh/docs/2.21/migration/#service-account-token-audiences.
- **Breaking (2 more, non-security):**
  - **Azure Pipelines scaler:** `scaleOnInFlight` now defaults `true` — queue length includes jobs already assigned to an agent, not just unassigned ones. Set `scaleOnInFlight: false` to keep KEDA 2.20 behavior (pair with the accurate scaling strategy for ScaledJobs).
  - **Temporal scaler:** deprecated `buildId`, `selectAllActive`, `selectUnversioned` settings **removed** — ScaledObjects/ScaledJobs still setting them fail scaler metadata parsing. Migrate to `workerDeploymentName` + `workerDeploymentBuildId`, or drop the settings for unversioned workers.
- **CRD migrations:** none — `keda.sh/v1alpha1` unchanged.
- **Upgrade ordering:** CRDs before core manifest, as usual. Do the Vault/BSAT audience audit above **before** rolling the operator — this is a default-on behavior change, not opt-in.
- **Deprecations:** Liiklus scaler deprecated (upstream unmaintained); removal planned for a later release — migrate off it before then (#7929).
- **Notable:** HPA-owned scaling decisions skip redundant scaler-backend polls; new Azure Cosmos DB Change Feed, ClickHouse, and GCP Cloud Spanner scalers; external scalers can push HPA target updates via `StreamMetricSpec`. Next release estimated 2nd week of January 2027.

## 2.20.0 — 2026-06-01 (latest patch: **2.20.2**, 2026-07-31 — release-verified 2026-09-24; unchanged since last sift)

- **k8s floor:** **1.33 – 1.35** (N-2 window moves with the release).
- **⚠️ Upgrade action REQUIRED before bumping — events moved to `events.k8s.io`.** With the k8s 0.35 dependency bump, KEDA records events via the `events.k8s.io` API group instead of core `events`. **Custom or restricted RBAC must grant the operator `create`/`patch` on `events.k8s.io/events` BEFORE the upgrade**, or event recording silently fails. Bundled manifests and the Helm chart already carry the permission — this only bites hand-rolled RBAC (PR #7781).
- **Breaking (scaler metadata removals — audit ScaledObjects first):**
  - GCP Pub/Sub `subscriptionSize` **removed** → use `mode` + `value`.
  - Huawei Cloudeye `minMetricValue` **removed** → use `activationTargetMetricValue`.
  - IBM MQ `tls` setting code **removed**.
  - InfluxDB `authToken` in `triggerMetadata` **removed** → use `resolvedEnv` or `authParams`.
  (The first two were the deprecations 2.19 warned about; they have now landed.)
- **CRD migrations:** none — `keda.sh/v1alpha1` unchanged. But 2.20 adds **CRD-level validation markers** (Minimum, MinLength, MinItems, Enum) and rejects ScaledObject names over 63 chars, so an object that was accepted pre-2.20 can fail admission after the upgrade. Dry-run apply your ScaledObjects against the new CRDs before rolling.
- **Upgrade ordering:** unchanged — CRDs before core manifest.
- **Notable:** `scalingModifiers` finally supports fallback (`fallback.behavior: scalingModifiers` + `??` chaining in the formula, PR #7790); new OpenSearch and Elastic Forecast scalers; AWS External ID in `TriggerAuthentication` podIdentity for all AWS scalers; new scaler HTTP metrics (`keda_scaler_http_requests_total`, `keda_scaler_http_request_duration_seconds`); webhook OOM fix under heavy admission load (~60k ScaledObjects, PR #7670). Next release estimated 2nd week of September 2026.

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
