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

**`kubeVersion` enforcement — corrected 2026-07-21.** Helm checks the chart's `kubeVersion:` constraint against `.Capabilities.KubeVersion`, which is the **API-server** version for `install`/`upgrade` and **helm's own compiled-in default** for `helm template`. **kubectl is not involved.** Verified: `helm template` of `mimir-distributed-6.1.0` (`^1.32.0-0`) passes under helm 3.17.3 with no flag, and fails only with an explicit `--kube-version 1.31.0`. Practical consequences: (a) a real `helm upgrade` against a too-old **cluster** fails and there is no bypass flag; (b) an *old helm binary* can fail a `helm template` dry-run that would succeed against the live cluster — pass `--kube-version <server-version>` for the render. **`kubeVersionOverride` does NOT bypass the constraint** — it only feeds the chart's internal `mimir.kubeVersion` helper for `internalTrafficPolicy` / PVC-retention / PSP decisions. The earlier "checks the kubectl client version" claim here was wrong. Restricted PSA via namespace labels (used by the chart's templates) needs **k8s 1.23+** regardless of the constraint.

## 6.1.0

- **k8s floor:** **1.32+** (literal `kubeVersion: ^1.32.0-0`). Second floor jump in two minors; chart CHANGELOG states it plainly — "Update minimum supported Kubernetes version to 1.32. This reflects the fact that Grafana does not test with older versions."
- **Mimir app version:** 3.1.2.
- **Breaking (chart-level, from `6.1.0`):**
  - **`kafka.extraEnv` removed** — use `kafka.env`, which merges by name against the chart's defaults (same pattern as `ingester.env`). A values file still setting `extraEnv` silently loses those vars.
  - **Default registry for the mimir image is now `docker.io`**, and **the image tag now defaults to `Chart.AppVersion`** instead of being carried in values. Both change what an image-list generator emits — **regenerate air-gap image lists from scratch, do not diff them.** Air-gapped fleets should **add an explicit `image.tag` pin**: from 6.1.0 on, a chart patch bump silently bumps the image tag to a value written nowhere in your values file. There is **no `image.digest` key** — the only digest form the chart can express is `tag: "3.1.2@sha256:<digest>"`.
  - **No global registry override exists** (`global:` has no `image*` key; upstream request grafana/mimir#5449 still open). Every image family needs its own key, and the shapes differ: Mimir/memcached/memcached-exporter fold the registry into `repository` (no `registry` key at all), while gateway-nginx / kafka / rollout-operator / grafana-agent-operator take a separate `registry`. `image.pullSecrets` is a list of **strings** but the subcharts' `imagePullSecrets` are lists of **maps**, and `kafka.image.pullSecrets` is honoured by the template yet absent from `values.yaml`.
  - Mirror must serve **quay.io as well as docker.io** — minio and `mc` come from quay.io.
  - rollout-operator subchart **0.37.1 → 0.50.0 (appVersion v0.38.0)** — read the tarball's `Chart.yaml`, not the CHANGELOG, which cites 0.37.1/0.38.0/0.38.1/0.48.0 inconsistently for this one release. **Required action:** v0.38.0's fixed-delay partition-aware PDB eviction needs an **updated CRD** plus a role letting the operator patch pods. From chart 0.48.0 the CRDs live in a bundled `crds` subchart (`charts/rollout-operator/charts/crds/crds/`) — still Helm `crds/` semantics, so **`helm upgrade` will NOT apply them**. `kubectl apply` both from the tarball first.
  - ~~Chart tooling moved to Helm v4~~ — **not a consumer requirement.** The CHANGELOG's "Upgrade to Helm v4" (#13661) touches only `.github/workflows/*`, the build image, `Makefile` and `operations/helm/scripts/build.sh`. `Chart.yaml` is still `apiVersion: v2` and **Helm 3 installs 6.1.0 fine.** Caveat: Helm 3 vs 4 *do* render differently (PDB apiVersion, `internalTrafficPolicy`, PSP objects), so use the **same Helm binary across all hops** or `helm template` diffs will show phantom changes.
- **Default-value shifts to expect (not breaks, but they resize pods):**
  - `results-cache.maxItemMemory` 5 → **25 MB** (base values).
  - query-frontend memory limit 2.8Gi → **4Gi** — but **only in `small.yaml`/`large.yaml`**, not base values. A fleet that does not apply a sizing plan gets the cache bump *without* the memory bump and is under-provisioned.
  - **Ruler gains a hardcoded 1 GiB memory ballast** — `ruler-dep.yaml` sets `-mem-ballast-size-bytes=1073741824` with **no values escape hatch**. Raise `ruler.resources.limits.memory` by ≥1 GiB *before* the hop or the ruler OOMKills.
  - All four memcached StatefulSets get `minReadySeconds: 60` — memcached rollouts become substantially slower; budget the maintenance window.
  - Zone-downscale guards: `ingester.zoneAwareReplication.minTimeBetweenZonesDownscale: 12h`, `store_gateway…: 30m`. These block rapid successive zone operations.
  - **NOT in 6.1.0:** querier `max_concurrent` stays **16** (verified byte-identical in the 6.0.6 and 6.1.0 embedded config). The lowering to 8 is in the chart CHANGELOG's `main / unreleased` section — do not budget for it on this ladder.
- **Ingest storage:** still the chart default in 6.1 — the config template ships `ingest_storage.enabled: true`. Kafka remains a required dependency of the default topology.
- **CRD migrations:** N/A.
- **Upgrade ordering:** rollout-operator drives ingester/store-gateway restarts. See § Rollout mechanics.
- **Notable:** the `kubeVersionOverride` gotcha bites harder here — `^1.32.0-0` will trip any operator workstation whose kubectl predates 1.32, even against a 1.32+ server.

## 6.0.6

- **k8s floor:** 1.29+ (literal `kubeVersion: ^1.29.0-0` from Chart.yaml at `mimir-distributed-6.0.6`). Hard jump from 5.8.0's `^1.20.0-0` — a 5.8 → 6.0 chart upgrade on a k8s 1.28 cluster fails the chart precheck.
- **Mimir app version:** 3.0.4.
- **Breaking (chart-level, all from `6.0.0`):**
  - Minimum compatible k8s bumped to **1.29**.
  - **Ingest storage architecture is now the default deployment mode** (Kafka between write and read paths). **But staying on classic is a first-class supported option and is the low-risk path for an existing 5.x fleet** — the chart ships `classic-architecture.yaml` at its root (6.0.6 and 6.1.0, byte-identical), the 5.x→6.0 migration guide has a "Continue using classic architecture" section, and upstream CI regression-tests it with golden manifests. Mimir's own binary default is `ingest_storage.enabled: false`; only the chart flips it on.
  - **`kafka.enabled: false` is NOT the architecture switch** — it only stops the chart *deploying* Kafka. Alone it yields ingest-storage-configured Mimir with the classic push path disabled and no broker = ingestion outage. The switch is `mimir.structuredConfig.ingest_storage.enabled: false` **plus** `ingester.push_grpc_method_enabled: true` (the chart hardcodes it to `false`). Prefer the shipped preset file over the migration guide's snippet — the snippet omits `distributor.remote_timeout: null`, silently leaving the Kafka-tuned 5s instead of reverting to 2s.
  - **Migrating classic → ingest storage is a two-cluster blue/green project, not an upgrade step:** second cluster on the same bucket, dual-write, 12–13 h overlap, read cutover, compactor handover inside ~15 min. Upstream states it "temporarily doubles your ingestion and storage costs". In-place migration is an open feature request (grafana/mimir#13351), not a feature. Decouple the chart ladder from the architecture change.
  - **`nginx` section removed — this is the highest-severity silent break on the whole ladder, and it specifically hits COMMUNITY fleets.** In 5.x the gateway was gated by `gateway.enabled AND (gateway.enabledNonEnterprise OR enterprise.enabled)` with `enabledNonEnterprise: false` — so **community clusters ran `<release>-nginx`, not `<release>-gateway`**. In 6.0 the helper collapses to just `gateway.enabled` (default `true`). A naive upgrade therefore **deletes the `<release>-nginx` Deployment/Service/Ingress and creates `<release>-gateway` at a different DNS name** — every remote_write client, Grafana datasource, and ingress backend pointing at the old name breaks at once.
    - **Fix:** `gateway.service.nameOverride: <existing-nginx-service-name>` and `gateway.ingress.nameOverride: <existing-nginx-ingress-name>` (both keys exist in 6.0.6). Migrate the proxy **on 5.8.0 first**, in a separate `helm upgrade`, then bump the chart — do not combine the two.
    - Non-obvious key renames: `deploymentStrategy`→`strategy`, `extraEnv`→`env`, `podSecurityContext`→`securityContext`, `nginxConfig.*`→`nginx.config.*`, `image.*`→`nginx.image.*`, `basicAuth.*`→`nginx.basicAuth.*`. **`affinity` changes type** — templated string → YAML object; copying it verbatim is a render error. **`nginx.image.pullPolicy` has no equivalent** — the nginx container now inherits `image.pullPolicy` from the Mimir image.
    - `nginx.basicAuth.*` silently no-op'ing means **proxy auth silently disappears**. Check this one explicitly.
    - The nginx→gateway mapping guide only resolves at the **`v5.8.x`** docs path (`latest` 404s, `v5.6.x` 502s). Archive it — it will disappear.
  - **`ingress.paths` keys renamed** `distributor-headless`→`distributor`, `alertmanager-headless`→`alertmanager`. `ingress.paths` is map-merged, so a carried-forward old key **adds a rule pointing at a headless (no-ClusterIP) Service** — a dead route with no error.
  - **No `values.schema.json` ships in any of 5.7/5.8/6.0/6.1.** Unknown and stale keys are never rejected — every removed chart key above is a **silent no-op**, not an error. Only `templates/validate.yaml` hard-fails, and its guards do NOT cover any of the 6.0 removals. Contrast with app-level config: Mimir *does* reject removed config keys at startup, so `structuredConfig` leftovers crashloop instead of being ignored.
  - The whole GEM surface is removed with no guard: `enterprise.*`, `admin_api.*`, `admin-cache.*`, `graphite.*`, `gr-*-cache.*`, `tokengenJob.*`, `license.*`, `provisioner.*`, `kubectlImage.*`, `federation_frontend.*`. Silent no-ops; delete them so the next operator is not misled.
  - `<release>-query-frontend-headless` Service is **deleted** (query-scheduler now mandatory). Any `frontend_worker.frontend_address` override dangles.
  - **Land on 6.0.6 directly — never stop at 6.0.0/6.0.1** (rollout-operator self-signed cert has the wrong DNS name; recovery needs deleting the `certificate` secret and recreating the pod).
  - ~~GEM gateway Service port 8080 removed~~ — **the CHANGELOG is wrong.** `gateway.service.legacyPort` still defaults to `8080` in both 6.0.6 and 6.1.0 and `gateway-svc.yaml` still renders the `legacy-http-metrics` port (verified in both tarballs). No action needed.
  - **`metaMonitoring.grafanaAgent` deprecated** — Grafana Agent reached End-of-Support end-2025. Switch to external collector (Grafana k8s-monitoring / Alloy).
  - Query-scheduler is now a **required component**; always used by queriers and query-frontends. No more "disable query-scheduler" path.
  - Distributor `GOMAXPROCS` calculation lowered to match CPU request more tightly — CPU usage profile shifts; resize requests if pods were leaning on the looser old behaviour.
  - Ingress default routes changed to point to **non-headless** services.
  - Provisioner job default kubectl image replaced with `alpine/kubectl`.
- **Breaking (app-level, Mimir 2.17 → 3.0):**
  - Mimir 3.0 is the cutover to ingest-storage-by-default; chart and app are co-pinned. Treat the chart-minor bump and the Mimir-major bump as one event, not two.
  - **CRDs must be pre-installed.** 6.0.0's rollout-operator needs the `replica-templates` and `zone-aware-pod-disruption-budget` CRDs applied *before* the upgrade, or set `rollout_operator.enabled: false`. Skipping this wedges the upgrade (the migration guide has a webhook-recovery troubleshooting block for exactly this). Air-gapped: the docs install them by `kubectl apply` from `raw.githubusercontent.com` — mirror them.
  - MQE default straddles hops — see § 5.8.0.
- **CRD migrations:** N/A — Mimir uses stock k8s resources (StatefulSets, Deployments, ConfigMaps). The chart's rollout-operator subchart manages rolling-restart ordering; no Mimir-owned CRDs to convert.
- **Upgrade ordering:**
  - Ingesters and store-gateways roll via the rollout-operator, one zone at a time. See § Rollout mechanics for the corrected `kubectl rollout restart` story.
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
- **Breaking (app-level, Mimir 2.16 → 2.17):**
  - **MQE becomes the default query engine in queriers** (`[CHANGE] Querier: Use Mimir Query Engine (MQE) by default`, #11501). This is the read-path risk hop for a fleet coming from 2.16 — *not* the 6.0 hop, where 3.0 merely extends the default to query-frontends (#12361). Opt out per tier: `-querier.query-engine=prometheus` / `-query-frontend.query-engine=prometheus`. Both tiers carry `-enable-query-engine-fallback` (default `true`) and there is **no fallback counter**, so silent engine divergence is not alertable. To keep a chart upgrade bisectable from an engine swap, pin `prometheus` through the 5.8.0 hop and flip the engine as a separate change.
  - Memberlist KV defaults tightened (`packet-dial-timeout` 500ms, `packet-write-timeout` 500ms, `max-concurrent-writes` 5, `acquire-writer-timeout` 1s) — upstream warns this "might cause long-running packets to be dropped in high-latency networks". Watch ring-health alerts on this hop.
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


## Rollout mechanics (cross-version) — corrected 2026-07-21

**The `kubectl rollout restart` prohibition is folklore, and the usual justification is wrong.** Researched against rollout-operator source, kubectl source, and the Mimir docs; **no upstream document prohibits it** anywhere in `docs/sources/mimir/**`, the runbooks, or the rollout-operator README.

- On zone-aware StatefulSets (the chart default) `updateStrategy` is `OnDelete`. `kubectl rollout restart` does **not** error and does **not** delete a pod — kubectl's `objectrestarter.go` only stamps `kubectl.kubernetes.io/restartedAt` on the pod template. The operator then rolls that zone through its normal gated path. Real cost: **manifest drift** from the Helm-rendered state, and only the named zone rolls.
- The hash-ring resharding mechanism is real but **defused by the chart**: it pins `unregister_on_shutdown: false` + `tokens_file_path: /data/tokens` for ingester *and* store-gateway in all four versions. Upstream says why: *"Rolling restarts of ingesters are now less likely to cause spikes in resource usage."* If anyone overrides `unregister_on_shutdown: true`, the folklore becomes true.
- **The genuinely dangerous config is single-zone** (`zoneAwareReplication.enabled: false`): the chart emits `RollingUpdate`, the operator refuses the group, `podManagementPolicy: Parallel` removes ordering, and PDBs don't gate controller-driven deletion.
- The real simultaneity limit is capacity: with RF=3, roll **one ingester at a time**, or **one whole zone at a time** if zone-aware replication is on (upstream `perform-a-rolling-update.md`).

**Do NOT POST `/ingester/prepare-shutdown` before a version bump.** It is wired as an STS annotation consumed by the `prepare-downscale` webhook, which fires only on a **replica decrease**. A version bump leaves replicas unchanged, so pods keep their PVC, tokens file, and ring entry and replay the WAL. Forcing `prepare-shutdown` triggers unregister + full flush — the expensive scale-down path, not the restart path.

**Abort levers, in order of safety:**

| Lever | Verdict |
|---|---|
| `grafana.com/rollout-paused: "true"` on the STS | The correct pause. **But it needs rollout-operator ≥ v0.36.0** — bundled appVersions are 5.7.0→v0.24.0, 5.8.0→v0.28.0, 6.0.6→v0.32.0, 6.1.0→**v0.38.0**. So it is only available on the final hop. |
| Scale the rollout-operator to 0 | **Deadlocks the namespace on 6.x.** The `prepare-downscale` MutatingWebhookConfiguration matches UPDATE on `statefulsets` + `statefulsets/scale` with `failurePolicy: Fail`. No ready endpoint ⇒ the apiserver rejects every matching request — including `helm upgrade`, `helm rollback`, and `kubectl scale`. Correct only on 5.7.0/5.8.0, which ship no webhooks. |
| `helm rollback` | Works at the workload layer; the operator explicitly handles reverted revisions. Not a data rollback. |

**`helm upgrade --wait` is not a gate here.** Helm's `statefulSetReady()` short-circuits for any non-`RollingUpdate` StatefulSet, so Helm reports success the moment the STS object is patched — before a single ingester pod is replaced. Also: `--dry-run` auto-allows the prepare-downscale webhook, so a replica reduction that will be denied on real apply looks clean in `helm diff`.

**Downgrade is an unmade upstream claim.** `CHANGELOG.md` and the chart CHANGELOG contain zero occurrences of "downgrade"/"rollback". `about-versioning.md` guarantees only that *future* versions read old data; grafana/mimir#2807 asking for the converse has been open and unanswered since 2022. Treat every hop as forward-only at the **data** layer.
- TSDB blocks are *not* the barrier in this window — 2.16.0 and 3.1.2 both write index `FormatV2`, `meta.json` `TSDBVersion1`.
- The sharp edge is the **Kafka record version** (ingest storage only): 3.1 defaults `-ingest-storage.kafka.producer-record-version=2`. 3.0.4 can read V2; **2.16 cannot** (`pkg/storage/ingest/version.go` does not exist at that tag).
- Config-shape asymmetry makes a binary downgrade fail loudly anyway: 3.0 removed **159** flags that 2.17 knew, and 3.1.2 has **225** flags 2.17 does not.