# mimir — compat (sifted from chart_metadata)

- **Primary source:** https://github.com/grafana/mimir → `operations/helm/charts/mimir-distributed/Chart.yaml` at `mimir-distributed-X.Y.Z` tags
- **Secondary sources:** https://github.com/grafana/mimir/blob/main/operations/helm/charts/mimir-distributed/CHANGELOG.md, https://github.com/grafana/mimir/releases (filter `mimir-distributed-*`)
- **Truth source type:** `chart_metadata`
- **Axis type:** `single`
- **min_tracked_version:** 5.7
- **Last sifted:** 2026-07-21

In-scope set: current stable chart minor **6.1** + prior 2 (6.0, 5.8). Latest patches as of sift: `mimir-distributed-6.1.0` (2026-07-16, appVersion 3.1.2), `6.0.6` (2026-03-19), `5.8.0` (2025-08-20). The chart minors 5.8 and 5.7 carry no patch releases beyond `.0`. **`5.7.0` is retained below the window** (see § 5.7.0) because it is a live fleet version and the origin of the 2.x → 3.x migration — not because it is in scope for a support verdict.

**Chart → Mimir-app mapping (load-bearing):**

| Chart | `kubeVersion:` | `appVersion:` (Mimir) |
|---|---|---|
| 6.1.0 | `^1.32.0-0` | 3.1.2 |
| 6.0.6 | `^1.29.0-0` | 3.0.4 |
| 5.8.0 | `^1.20.0-0` | 2.17.0 |
| 5.7.0 | `^1.20.0-0` | 2.16.0 |

The k8s floor moves only at chart-minor boundaries, and it has moved **twice in two minors** — `^1.20` → `^1.29` (6.0.0) → `^1.32` (6.1.0). A fleet on k8s < 1.32 can reach 6.0.x but not 6.1.0. Mimir-app major bump (2.x → 3.x) lands in chart 6.0.0; Mimir 2.x stays available via chart 5.x.

**Upgrade ladder (app policy: one minor at a time — deprecated features survive two minors).** Chart minors track app minors, so the two ladders are one walk: `5.7 (2.16) → 5.8 (2.17) → 6.0.x (3.0.4) → 6.1.0 (3.1.2)`. The 5.8 hop is cheap and is the last stop on the Mimir 2.x line; **6.0 is the architecture event**, not a `helm upgrade`.

**Naming trap.** Grafana's doc "Migrate the Mimir Helm chart from version 2.x to 3.0" is about **chart** 2.x → 3.0 (2022) and has nothing to do with **app** Mimir 2.x → 3.0. Chart and app version numbers collide across this whole component — always say which one.

**`kubeVersionOverride` gotcha — applies to every minor.** Helm checks the chart's `kubeVersion:` constraint against the **kubectl client** version, not the server. Set `kubeVersionOverride: <server-version>` (e.g. `1.30.0`) in values when the kubectl on the operator's workstation is older than the cluster — otherwise install/upgrade fails with `chart requires kubeVersion: ^1.29.0-0` even on a 1.30 cluster. Restricted PSA via namespace labels (used by the chart's templates) needs **k8s 1.23+** regardless of the constraint.

## 6.1.0

- **k8s floor:** **1.32+** (literal `kubeVersion: ^1.32.0-0`). Second floor jump in two minors; chart CHANGELOG states it plainly — "Update minimum supported Kubernetes version to 1.32. This reflects the fact that Grafana does not test with older versions."
- **Mimir app version:** 3.1.2.
- **Breaking (chart-level, from `6.1.0`):**
  - **`kafka.extraEnv` removed** — use `kafka.env`, which merges by name against the chart's defaults (same pattern as `ingester.env`). A values file still setting `extraEnv` silently loses those vars.
  - **Default registry for the mimir image is now `docker.io`**, and **the image tag now defaults to `Chart.AppVersion`** instead of being carried in values. Both change what an image-list generator emits — **regenerate air-gap image lists from scratch, do not diff them.**
  - rollout-operator subchart moved to **0.38.x** (chart notes "required actions for upgrading the rollout-operator chart" — read the subchart README before rolling).
  - Chart tooling moved to **Helm v4**.
- **Default-value shifts to expect (not breaks, but they resize pods):** querier `max_concurrent` lowered to 8; query-frontend results-cache limit → 25 MB and memory limit → 4 GiB; ruler memory ballast → 1 GiB; memcached StatefulSets get `minReadySeconds` to slow rollouts.
- **Ingest storage:** still the chart default in 6.1 — the config template ships `ingest_storage.enabled: true`. Kafka remains a required dependency of the default topology.
- **CRD migrations:** N/A.
- **Upgrade ordering:** unchanged — rollout-operator drives ingester/store-gateway restarts; never `kubectl rollout restart` those StatefulSets directly.
- **Notable:** the `kubeVersionOverride` gotcha bites harder here — `^1.32.0-0` will trip any operator workstation whose kubectl predates 1.32, even against a 1.32+ server.

## 6.0.6

- **k8s floor:** 1.29+ (literal `kubeVersion: ^1.29.0-0` from Chart.yaml at `mimir-distributed-6.0.6`). Hard jump from 5.8.0's `^1.20.0-0` — a 5.8 → 6.0 chart upgrade on a k8s 1.28 cluster fails the chart precheck.
- **Mimir app version:** 3.0.4.
- **Breaking (chart-level, all from `6.0.0`):**
  - Minimum compatible k8s bumped to **1.29**.
  - **Ingest storage architecture is now the default deployment mode.** Read and write paths decoupled via Kafka. Chart deploys a single-node Kafka for demo only; production must point at an external Kafka-compatible cluster via `kafka.enabled=false` + credentials. 5.x → 6.0 upgrades on classic architecture require an explicit migration; do not roll without reading the upstream migration guide.
  - `nginx` top-level values section **removed** (deprecated in 4.0.0; was scheduled for 7.0.0, pulled forward to 6.0.0). Migrate to the unified `gateway` section before upgrade.
  - **GEM gateway Service port 8080 removed** (deprecated in 3.1.0). Replace with port 80 in dashboards, remote-write configs, rule automation.
  - **`metaMonitoring.grafanaAgent` deprecated** — Grafana Agent reached End-of-Support end-2025. Switch to external collector (Grafana k8s-monitoring / Alloy).
  - Query-scheduler is now a **required component**; always used by queriers and query-frontends. No more "disable query-scheduler" path.
  - Distributor `GOMAXPROCS` calculation lowered to match CPU request more tightly — CPU usage profile shifts; resize requests if pods were leaning on the looser old behaviour.
  - Ingress default routes changed to point to **non-headless** services.
  - Provisioner job default kubectl image replaced with `alpine/kubectl`.
- **Breaking (app-level, Mimir 2.17 → 3.0):**
  - Mimir 3.0 is the cutover to ingest-storage-by-default; chart and app are co-pinned. Treat the chart-minor bump and the Mimir-major bump as one event, not two.
- **CRD migrations:** N/A — Mimir uses stock k8s resources (StatefulSets, Deployments, ConfigMaps). The chart's rollout-operator subchart manages rolling-restart ordering; no Mimir-owned CRDs to convert.
- **Upgrade ordering:**
  - Ingesters and store-gateways: **rolling restart via rollout-operator is mandatory** (chart enforces). Do not bypass with `kubectl rollout restart` on the StatefulSet directly — split-brain on the hash ring.
  - rollout-operator subchart bumped to **0.37.1**. If upgrading from 6.0.0 or 6.0.1, delete the `certificate` secret created by the rollout-operator pod and recreate the pod (TLS DNS-name fix in 6.0.2).
  - PSA: restricted-policy namespaces work fine; chart sets `runAsNonRoot`/`seccompProfile` on all components. Verify the namespace's `pod-security.kubernetes.io/enforce: restricted` label is set **before** the install or admission rejects on first apply.
- **Deprecations:** none new at chart level in 6.0.x. App-side: see Mimir 3.0 CHANGELOG for in-app flag deprecations.
- **Notable:**
  - `kubeVersionOverride` is the single most common upgrade-blocker on this chart minor — operator workstation kubectl < 1.29 trips the constraint even on a 1.30+ server. Set it explicitly in values.yaml during the bump.
  - Rollout-operator subchart pinned 0.37.1 (chart `6.0.6`).
  - Kafka bootstrap fix in `6.0.5` (parallel rollout + not-ready addresses published). If running 6.0.0–6.0.4 with the default ingest-storage Kafka, bootstrap can hang — patch to 6.0.5+.

## 5.8.0

- **k8s floor:** 1.20+ (literal `kubeVersion: ^1.20.0-0`). Effectively any currently-supported k8s minor; the constraint is generous and not the real ceiling. In practice the chart is tested against k8s 1.28–1.32; 1.20–1.22 are constraint-passing but well past upstream k8s EOL.
- **Mimir app version:** 2.17.0.
- **Breaking (chart-level):**
  - KEDA autoscaling: `toPromQLLabelSelector` changed from object to list of strings. Existing KEDA values pinning `toPromQLLabelSelector` as a map fail validation — convert to list.
  - Memcached `ruler-storage` cache default timeout raised `200ms` → `500ms`. If you measure ruler-eval latency against historical baselines, this shifts the floor up; not a break, but a numbers-shift to expect.
  - `JAEGER_REPORTER_MAX_QUEUE_SIZE` env var no longer set by the chart. Components fall back to OTel default 2048. If a previous values override was tuning this, switch to `OTEL_BSP_MAX_QUEUE_SIZE`.
  - Memberlist: `memberlist.abort-if-fast-join-fails` enabled for ingesters — ingester join failures now fail-fast instead of degrading silently.
  - `store_gateway.grpcMaxQueryResponseSizeBytes` defaulted to 200 MB. Operators with custom limits should re-check.
- **Breaking (app-level, Mimir 2.16 → 2.17):** see upstream Mimir 2.17 CHANGELOG; nothing chart-visible beyond image tag.
- **CRD migrations:** N/A.
- **Upgrade ordering:** rolling-restart via rollout-operator (subchart 0.35.x in 5.8 line). Ingester/store-gateway ordering enforced. No coupling with the k8s-minor axis at this chart minor.
- **Deprecations:** Grafana Agent metamonitoring continues to function in 5.8 but the deprecation lands in 6.0.
- **Notable:**
  - `kubeVersionOverride` gotcha applies but rarely surfaces — `^1.20.0-0` passes nearly any kubectl client a 2026 operator would have.
  - Final chart minor on the Mimir 2.x major line. End-of-the-rope for staying on Mimir 2.x via the chart.

## 5.7.0

- **k8s floor:** 1.20+ (`kubeVersion: ^1.20.0-0`). Same constraint as 5.8.
- **Mimir app version:** 2.16.0.
- **Breaking (chart-level):**
  - Tokengen: added k8s Secret storage for the admin token. If automation read the previous in-memory/ConfigMap form, switch to the Secret.
  - Memcached default `clusterDomain` resolution: hostnames now honour `global.clusterDomain` consistently across cache clusters. Air-gapped clusters with non-default cluster DNS suffixes (`cluster.internal.`, etc.) need to ensure `global.clusterDomain` is set explicitly — drifting from `cluster.local.` silently was previously possible.
  - `large.yaml`/`small.yaml` reference values now default to **3 replicas** for all cache types. Apply-time replica counts shift if you derive from these presets.
- **Breaking (app-level, Mimir 2.15 → 2.16):** see upstream Mimir 2.16 CHANGELOG.
- **CRD migrations:** N/A.
- **Upgrade ordering:** rolling-restart via rollout-operator (subchart ~0.20–0.24 in 5.6/5.7). Standard.
- **Deprecations:** none chart-impacting in 5.7.
- **Notable:**
  - `kubeVersionOverride` gotcha applies but rarely matters at this constraint.
  - `5.7.0` is the floor of the tracked window — below this, abstain on Mimir compat verdicts and recommend `skill-improver freshen k8s-components-checker`.
