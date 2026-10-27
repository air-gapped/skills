# Per-hop runbook

Concrete pre-flight and execution for the 5.7.0 → 5.8.0 → 6.0.6 → 6.1.0 ladder. The method generalises; the
version numbers do not — get those from `k8s-components-checker` → `references/compat/mimir.md`.

## Contents
1. [The silent-vs-loud asymmetry](#1-the-silent-vs-loud-asymmetry)
2. [Hop 1 — 5.7.0 → 5.8.0](#2-hop-1--570--580)
3. [Interlude — the proxy migration](#3-interlude--the-proxy-migration-on-580)
4. [Hop 2 — 5.8.0 → 6.0.6](#4-hop-2--580--606)
5. [Hop 3 — 6.0.6 → 6.1.0](#5-hop-3--606--610)
6. [Removed-key quick table](#6-removed-key-quick-table)
7. [CHANGELOG claims that are wrong](#7-changelog-claims-that-are-wrong)
8. [Hop 4 — 6.1.x → 6.2.x](#8-hop-4--61x--62x)

## 1. The silent-vs-loud asymmetry

Audit the values file **twice, expecting different symptoms**: [RFC]

- **Chart keys fail silently.** No `values.schema.json` ships in 5.7.0, 5.8.0, 6.0.6, or 6.1.0. Unknown and
  stale keys are never rejected. The only fail-fast is `templates/validate.yaml`, whose guards cover **none** of
  the 6.0 removals. A removed chart key is a no-op — the setting simply stops applying.
- **App config fails loudly.** Mimir rejects removed config keys at startup, so a stale
  `mimir.structuredConfig` key is a **crashloop**, not a silent regression.

Practical consequence: a clean `helm upgrade` plus Running pods proves nothing about the chart half of the
audit. Diff the *rendered* manifest, not the command's exit code.

`${CLAUDE_SKILL_DIR}/scripts/audit-values.sh <values.yaml> <target-chart-version>` mechanises the grep-able half of both lists
below, splitting its output into SILENT and LOUD findings. It is deliberately advisory — grep cannot parse YAML
structure, so treat every hit as "inspect this", not "this is broken".

## 2. Hop 1 — 5.7.0 → 5.8.0

App 2.16.0 → 2.17.0. Structurally the smallest hop; it carries the read-path risk.

**Pre-flight**

1. **Decide the MQE question.** [UG] 2.17 makes MQE the querier default (`[CHANGE] Querier: Use Mimir Query
   Engine (MQE) by default`, #11501) — *not* 3.0, which only extends the default to query-frontends. To keep the
   chart bump bisectable from an engine change, pin `mimir.structuredConfig.querier.query_engine: prometheus`
   through this hop and flip it later as its own change.
2. Grep `current.yaml` for `jaegerReporterMaxQueueSize` — removed from **19 components**. Replacement is
   `OTEL_BSP_MAX_QUEUE_SIZE` via `<component>.env`. [UG]
3. Grep for `kedaAutoscaling.toPromQLLabelSelector` — **type change**, object → list of PromQL matcher strings.
   A carried map renders a malformed/empty selector. Verify by rendering the ScaledObject. [UG]
4. Budget `memcachedExporter.resources` (new 50m/50Mi requests on **every** memcached pod) × the cache replica
   counts against namespace quota. [RFC]
5. New `store_gateway.grpcMaxQueryResponseSizeBytes: 209715200` — align querier/query-frontend gRPC limits if
   they were tuned lower. [RFC]
6. With a **full custom `mimir.config` string** pinned rather than `structuredConfig`, re-merge from the 5.8.0
   chart to pick up `dnssrvnoa+` memcached addressing and `ruler_storage.cache.memcached.timeout: 500ms`. [UG]
7. Purge 2.17 app removals from `structuredConfig`: `ooo_native_histograms_ingestion_enabled`,
   `-ruler-storage.cache.rule-group-enabled`, `max_cost_attribution_cardinality_per_user`, the
   instant-queries-with-subquery-spin-off rename, top-level HA-tracker timeouts (moved into `limits`), and
   **`log_level: fatal`** — no longer a valid level after the logrus → go-kit change. [UG]

**Watch during/after:** ingesters gain `memberlist.abort-if-fast-join-fails` (refuse to start if fast join
fails) and 2.17 tightens memberlist KV timeouts, which upstream warns "might cause long-running packets to be
dropped in high-latency networks". [UG] Confirm the gossip-ring headless Service resolves cleanly before rolling
ingesters, and watch ring-health alerts through this hop.

## 3. Interlude — the proxy migration, on 5.8.0

**Do this as its own `helm upgrade`, while still on chart 5.8.0.** It is the mitigation for the worst break in
the ladder, and it is far safer to land it before the chart bump than during it.

**Why it matters.** [RFC] In 5.x the gateway was gated by
`gateway.enabled AND (gateway.enabledNonEnterprise OR enterprise.enabled)` with `enabledNonEnterprise: false` —
so **community fleets ran `<release>-nginx`**. Chart 6.0 collapses the helper to just `gateway.enabled`
(default `true`). A naive upgrade therefore deletes the `<release>-nginx` Deployment/Service/Ingress and creates
`<release>-gateway` **at a different DNS name**. Every remote_write client, Grafana datasource, and ingress
backend pointing at the old name breaks simultaneously.

**Procedure**

1. Confirm which proxy is running: `kubectl get deploy -n <ns> | grep -E 'nginx|gateway'`, and record the exact
   Service and Ingress names.
2. On 5.8.0, set `gateway.enabledNonEnterprise: true` and `gateway.replicas` to match nginx. Upgrade. Both
   proxies now run; verify gateway pods pass readiness.
3. Translate every `nginx.*` key:

   | 5.8 key | 6.0 key | note |
   |---|---|---|
   | `nginx.enabled` | `gateway.enabled` | direct |
   | `nginx.deploymentStrategy` | `gateway.strategy` | **renamed** |
   | `nginx.extraEnv` | `gateway.env` | **renamed** |
   | `nginx.podSecurityContext` | `gateway.securityContext` | **renamed** |
   | `nginx.nginxConfig.*` | `gateway.nginx.config.*` | **renamed + nested** |
   | `nginx.image.*` | `gateway.nginx.image.*` | nested |
   | `nginx.basicAuth.*` | `gateway.nginx.basicAuth.*` | nested — **silently disables proxy auth if missed** |
   | `nginx.verboseLogging` | `gateway.nginx.verboseLogging` | nested |
   | `nginx.affinity` (string) | `gateway.affinity` (**object**) | **type change** — verbatim copy is a render error |
   | `nginx.image.pullPolicy` | *(none)* | inherits the **Mimir** image's `image.pullPolicy` |
   | everything else (`ingress`, `route`, `service`, `resources`, `tolerations`, `podDisruptionBudget`, …) | `gateway.<same>` | direct |

4. **Preserve the names:** `gateway.service.nameOverride: <existing-nginx-service-name>` and
   `gateway.ingress.nameOverride: <existing-nginx-ingress-name>`. Both keys exist in 6.0.6. [UG]
5. Set `nginx.enabled: false`, upgrade, and verify writes and reads through the **preserved** Service name.
   Only then delete the `nginx` block.

**Archive the mapping guide now.** It resolves only at the **`v5.8.x`** docs path — `latest` 404s and `v5.6.x`
redirect-loops between grafana.com and archive.grafana.com, because the guide was removed when `nginx` was. [UG]

## 4. Hop 2 — 5.8.0 → 6.0.6

App 2.17.0 → 3.0.4. The big one. Three separate concerns: architecture, admission webhooks, and values surface.

**Pre-flight — cluster**

1. **Decide the architecture** → `references/architecture-decision.md`. For an air-gapped community fleet,
   `-f classic-architecture.yaml`.
2. **Apply the rollout-operator CRDs by hand, before the upgrade:** `replicatemplates.rollout-operator.grafana.com`
   and `zoneawarepoddisruptionbudgets.rollout-operator.grafana.com`. Helm **never** installs `crds/` on upgrade,
   5.8's operator shipped none, and 6.0's webhooks register anyway with `failurePolicy: Fail`. Skipping this
   wedges pod evictions and StatefulSet downscales in the namespace. Take the YAML from **inside the tarball**,
   not the doc's `raw.githubusercontent.com` URLs. [UG] If the operator is not in use, set
   `rollout_operator.enabled: false` — note the alias uses an **underscore**; the migration guide's hyphenated
   `rollout-operator:` is a silent no-op that leaves it enabled. [UG]
3. Confirm the CD identity has **cluster-scoped** create rights for CRDs, Validating/MutatingWebhookConfiguration,
   ClusterRole, ClusterRoleBinding. [RFC]
4. Stage the break-glass commands (see `references/rollout-and-rollback.md`) *before* starting.

**Pre-flight — values**

5. Delete the whole GEM surface (silent no-ops, but they mislead the next operator): `enterprise.*`,
   `admin_api.*`, `admin-cache.*`, `graphite.*`, `gr-*-cache.*`, `tokengenJob.*`, `license.*`, `provisioner.*`,
   `kubectlImage.*`, `federation_frontend.*`, `gateway.image`, `gateway.enabledNonEnterprise`. [RFC]
6. Rename `ingress.paths.distributor-headless` → `distributor` and `alertmanager-headless` → `alertmanager`.
   `ingress.paths` is map-merged, so a leftover adds a rule pointing at a **headless (no-ClusterIP) Service** —
   a dead route with no error. [UG]
7. Remove `mimir.structuredConfig.frontend_worker.frontend_address` — the `<release>-query-frontend-headless`
   Service is deleted and the query-scheduler is now mandatory. [RFC]
8. Purge 3.0 app removals (each a **startup crashloop**): `-query-frontend.downstream-url`,
   `-querier.frontend-address`, `-querier.max-outstanding-requests-per-tenant`,
   `-query-frontend.querier-forget-delay`, `ingester_stream_chunks_when_using_blocks`,
   `-query-frontend.prune-queries`, `<prefix>.memcached.addresses-provider`, **the Redis cache backend
   entirely**, memcached mTLS, `service_overload_status_code_on_rate_limit_enabled`, instant-query splitting,
   read-write deployment mode. Ensure `-querier.streaming-chunks-per-*-buffer-size` are non-zero if set. [UG]
9. Review `-store-gateway.dynamic-replication.multiple` default **3 → 5** against store-gateway memory. [UG]
10. Expect distributor CPU to shift — `GOMAXPROCS` is recalculated closer to the CPU request. Re-baseline
    distributor HPA/KEDA thresholds after the hop. [UG]

**Land on 6.0.6 directly.** 6.0.0/6.0.1 ship a rollout-operator self-signed cert with the wrong DNS name;
recovery means deleting the `certificate` secret and recreating the pod. [UG]

**Assert in the rendered diff:** proxy Service name unchanged · `ingest_storage.enabled: false` (if classic) ·
no Kafka StatefulSet · query-scheduler present · ingress backends resolve to non-headless Services.

## 5. Hop 3 — 6.0.6 → 6.1.0

App 3.0.4 → 3.1.2. Mostly a defaults-and-resources hop, with one hard gate.

1. **The k8s minor gate is hard, and it moved again at this hop.** [UG] Helm enforces `Chart.yaml`'s
   `kubeVersion` against the API-server version; there is **no bypass flag**, and `kubeVersionOverride` does
   **not** bypass it (it only feeds the chart's internal capability helper for `internalTrafficPolicy` / PVC
   retention / PSP decisions). Complete the k8s upgrade first. **Read the floor from `compat/mimir.md`** — it
   has moved twice in two chart minors and this skill deliberately holds no copy of it.
2. **Apply the rollout-operator CRDs again** — they moved into a bundled `crds` subchart
   (`charts/rollout-operator/charts/crds/crds/`) and changed content for the new partition-aware PDB eviction.
   Still `crds/` semantics, so still skipped by `helm upgrade`. [UG]
3. **Raise `ruler.resources.limits.memory` by ≥1 GiB *first*.** The ruler Deployment hardcodes
   `-mem-ballast-size-bytes=1073741824` with **no values escape hatch**; a limit near the old working set
   OOMKills. [RFC]
4. `kafka.extraEnv` → `kafka.env` (name-keyed merge). Silent no-op otherwise — and it bites the day Kafka is
   enabled, even from a classic deployment. [UG]
5. **Pin `image.tag` explicitly.** It's gone from chart defaults and now falls back to `Chart.AppVersion`, so a
   chart patch bump silently changes the image tag. [UG] See `references/air-gap.md`.
6. `image.repository` default gains a `docker.io/` prefix — check any containerd registry-mirror rule that
   string-matched bare `grafana/mimir`. [RFC]
7. Budget slower rollouts: `minReadySeconds: 60` on all four memcached StatefulSets; zone-downscale guards
   `ingester 12h` / `store_gateway 30m` block rapid successive zone operations. [RFC]
8. Audit `env` / `extraEnvFrom` overrides — `containerEnv.tpl` merge semantics were rewritten (in-place,
   order-preserving) and `extraEnvFrom` indentation was fixed from 12 to 2 spaces. Values that compensated for
   the old bug now render malformed. [RFC]
9. `gateway-servmon.yaml` is deleted — reroute gateway metric scraping. [RFC]
10. **Memcached DNS is now fail-hard at startup** (`dns-ignore-startup-failures` removed) — relevant to
    air-gapped cold starts with slow CoreDNS. Verify memcached Services resolve before rolling. [UG]
11. Purge 3.1 app renames (crashloops): `blocked_queries.minimum_step_size` → `step_size_shorter_than` (and
    `blocked_queries` is now **validated at load** — empty patterns and invalid regexes are hard errors);
    `cost_attribution_labels` → `cost_attribution_labels_structured`; `-querier.prefer-availability-zone` →
    `-querier.prefer-availability-zones` (now a list); `-alertmanager.grafana-alertmanager-idle-grace-period` →
    `-alertmanager.strict-initialization-idle-grace-period`; and `*.ring.heartbeat-{period,timeout}: 0` is now
    invalid. Also removed: `-distributor.metric-relabeling-enabled`, `-compactor.no-blocks-file-cleanup-enabled`,
    `-compactor.in-memory-tenant-meta-cache-size`,
    `-blocks-storage.bucket-store.index-header.eager-loading-startup-enabled`,
    `-query-frontend.shard-active-series-queries`, `-query-frontend.use-active-series-decoder`,
    `-querier.response-streaming-enabled`, `-target=flusher` (use `/ingester/flush`). [UG]
12. With remote rule evaluation in use, `ruler-query-frontend` splits into ClusterIP + headless and the ruler
    dials the headless one — check any NetworkPolicy. [UG]

## 6. Removed-key quick table

| Hop | Key | Replacement | Failure mode |
|---|---|---|---|
| 5.7→5.8 | `<19 components>.jaegerReporterMaxQueueSize` | `<component>.env` + `OTEL_BSP_MAX_QUEUE_SIZE` | silent |
| 5.7→5.8 | `kedaAutoscaling.toPromQLLabelSelector` (object) | same key, **list of strings** | silent, malformed selector |
| 5.8→6.0 | `nginx.*` (whole section) | `gateway.*` (see mapping) | **silent — proxy DNS name changes** |
| 5.8→6.0 | `nginx.basicAuth.*` | `gateway.nginx.basicAuth.*` | silent — **proxy auth disabled** |
| 5.8→6.0 | `ingress.paths.{distributor,alertmanager}-headless` | drop `-headless` | silent — dead Ingress route |
| 5.8→6.0 | whole GEM surface | none | silent |
| 5.8→6.0 | app: 3.0 removals (§4.8) | see §4.8 | **crashloop** |
| 6.0→6.1 | `kafka.extraEnv` | `kafka.env` | silent |
| 6.0→6.1 | `image.tag` (from defaults) | falls back to `Chart.AppVersion` | silent tag drift |
| 6.0→6.1 | app: 3.1 renames (§5.11) | see §5.11 | **crashloop** |

## 7. CHANGELOG claims that are wrong

Verified against the tarballs; trust the artifact over the changelog. [RFC]

| Upstream CHANGELOG says | Actually |
|---|---|
| GEM gateway Service port 8080 removed at 6.0.0 | `gateway.service.legacyPort: 8080` still present in both |
| "Upgrade to Helm v4" | **CI-only** — `Chart.yaml` is `apiVersion: v2`; Helm 3 installs 6.1.0 fine |
| rollout-operator "0.38.x" at 6.1.0 | dependency is chart **0.50.0** (appVersion v0.38.0); the CHANGELOG cites four versions for one release |
| "rollout-operator chart 0.38.1" at 6.2.0 | chart **0.50.1** = appVersion **v0.38.1**; only the appVersion moved — no CRD step |

Corollary: use **one Helm binary version across all hops**. Helm 3 and 4 render PDB apiVersions,
`internalTrafficPolicy`, and PSP objects differently, so mixing them fills `helm template` diffs with
phantom changes. [RFC]

## 8. Hop 4 — 6.1.x → 6.2.x

Past the worked ladder: app 3.1 → 3.2. `kubeVersion` unchanged and no rollout-operator CRD change (bundled
v0.38.0 → v0.38.1). Come from 3.1 — the 3.2 querier↔store-gateway gRPC change requires it. [UG]

1. **Read-path defaults move.** [UG] `querier.max_concurrent` 16 → 8 (chart and app; pin it if query capacity
   was sized on 16); ingester request hedging is off (`-querier.minimize-ingester-requests-hedging-delay=3s`
   restores it); MQE remote execution and subset-selector elimination are on. Re-baseline query latency.
2. **Purge 3.2 removals (crashloop):** `-querier.mimir-query-engine.enable-projection-pushdown`,
   `-querier.mimir-query-engine.enable-prune-toggles`,
   `-query-frontend.enable-multiple-node-remote-execution-requests`. A `-query-frontend.log-query-request-headers`
   list naming `Authorization`, `Cookie` or `X-Api-Key` also fails startup. [UG]
3. **Alertmanager** no longer serves its per-tenant UI or `/-/healthy`, `/-/ready`, `/-/reload` under the
   alertmanager prefix — repoint any external probe or reload hook that used them. [UG]
4. **`ruler.memBallastSizeBytes`** (new; `0` disables) is the escape hatch §5 item 3 lacked. Keep it below any
   `GOMEMLIMIT` set on the ruler, or GC thrashes permanently. [UG]
5. **KEDA-autoscaled installs:** the `kedaAutoscaling.fallback` ScaledObject template bug is fixed (#15793) —
   re-render the ScaledObjects and diff. [UG]
