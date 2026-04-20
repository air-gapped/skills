---
name: prometheus-mimir-grafana
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch, WebSearch
description: Query Prometheus and Grafana Mimir, write and debug PromQL, and build or fix Grafana dashboards — for agents solving problems from metrics. Covers the Prometheus HTTP API (`/api/v1/query`, `query_range`, `series`, `labels`, `metadata`), Mimir multi-tenancy (`X-Scope-OrgID`, federation `a|b|c`, per-tenant 422/429 limits), the PromQL surface (selectors, rate family, classic + native histograms, `histogram_quantile`, vector matching `on()`/`group_left`, recording rules), Grafana dashboard JSON (panels, targets, variables + interpolation specifiers, legacy `/api/dashboards/db` vs Grafana-12 `/apis/dashboard.grafana.app/v1beta1/…`), KPI frameworks (RED, USE, Golden Signals, SLO burn-rate), connection recipes, MCP servers vs curl, and the PromQL trap list.
when_to_use: Triggers on "prometheus", "mimir", "grafana", "promql", "metrics", "dashboard", "observability", "SLO", "SLI", "burn rate", "golden signals", "RED", "USE method", "histogram_quantile", "X-Scope-OrgID", "remote_write", "node_exporter", "kube-state-metrics", "cadvisor", "DCGM", "kafka lag", "5xx rate", "p99 latency", "alert rule", "recording rule", "label_values", "$__rate_interval", "grafana variable", "grafana-mcp", "pyrra", "sloth". Also on operational phrases without a stack name — "why is my service slow", "what should I alert on", "help me build a dashboard", "my PromQL isn't matching", "my HPA is flapping". Fixing a dashboard, deciding what to measure, or reasoning from a /metrics surface → this skill.
---

# Prometheus, Mimir, and Grafana — for agents

Target audience: an AI agent (or a human working through one) that has to *do things with metrics* — query, triage, alert, build and fix dashboards, and pick the right KPIs — against a stack that runs Prometheus, Grafana Mimir, and/or Grafana. Works whether the agent is given curl access to a Mimir gateway, an MCP server wrapper, or just a Grafana URL and a service-account token.

## Why this matters

Metrics lie in three directions: (1) the agent queries the wrong metric or wrong label, (2) the query is syntactically fine but semantically broken (`rate` after aggregation, `histogram_quantile` of the mean, default histogram buckets sized for the wrong service), (3) the dashboard *looks* correct but the datasource variable is empty or the unit is off by 1000×. Each failure mode has an easy check. This skill is those checks, organized so the agent reaches for them before issuing the first query.

## The one-paragraph rubric

Prometheus stores samples identified by `metric_name{label=value, ...}`. Mimir is a horizontally-scalable multi-tenant store that speaks Prometheus's wire protocol and API under a `/prometheus/api/v1/…` prefix, gated by `X-Scope-OrgID`. Grafana is the UI and the dashboards-as-JSON store. PromQL returns instant vectors, range vectors, scalars, or strings; `rate()` always wraps a counter before any `sum`; `histogram_quantile()` always consumes aggregated `_bucket` rates; and `$__rate_interval` is the only interval variable safe for counter rates. RED answers *is my service OK*, USE answers *is my resource OK*, and Golden Signals + SLO burn-rate answer *are my users OK*. Everything else is detail in the references.

## Connect first — figure out what endpoint is in front of the agent

Before the first query, identify the endpoint and auth shape. One of these five patterns will match:

| Shape | Base URL | Auth | Tenant |
|---|---|---|---|
| Prometheus direct | `http://prometheus:9090` | usually none / optional Basic | n/a |
| Self-hosted Mimir via gateway | `https://mimir.example.com/prometheus` | `Authorization: Bearer …` | `X-Scope-OrgID: <tenant>` |
| Grafana Cloud Mimir | `https://prometheus-prod-XX.grafana.net/api/prom` | Basic `instance_id:access_token` **or** `Bearer access_token` | encoded in token |
| Grafana datasource proxy | `${GRAFANA}/api/datasources/proxy/uid/<ds-uid>` | Grafana SA token | datasource-configured |
| In-cluster via k8s apiserver | `https://kubernetes.default.svc/…/services/prometheus-k8s:web/proxy` | mounted ServiceAccount token + CA | n/a |

Probe which one:
```bash
curl -sG "$URL/api/v1/status/buildinfo"          # Prom: full payload; Mimir: also full, product field distinguishes
curl -s  "$URL/ready"                            # Mimir health
curl -sG "$URL/api/v1/status/config"             # Mimir returns empty; Prom returns loaded YAML
```
Missing `X-Scope-OrgID` on Mimir → 401/403 with a message mentioning "org id" — the tell.

Full connection and auth recipes in [references/mimir-api.md](references/mimir-api.md). MCP-server options, Grafana-side SA tokens, and the when-to-skip-MCP rule are in [references/agent-workflow.md](references/agent-workflow.md).

## The discovery → query loop

Do not start from `rate(http_requests_total[5m])` on faith. A metric *thought* to exist may actually be called `nginx_http_requests_total`, `istio_requests_total`, or `app_requests_total{job="api-server"}`. Always walk this ladder:

1. **Catalog.** `GET /api/v1/label/__name__/values` — filter by prefix (`http_`, `kube_`, `node_`, `container_`, `grpc_`, `process_`, service name). Cache the result in the session.
2. **Metadata.** `GET /api/v1/metadata?metric=<name>` — type, help, unit. Confirms what the metric *means* on this cluster.
3. **Labels.** `GET /api/v1/series?match[]=<metric>` — enumerate label sets. For one dimension, `GET /api/v1/label/<label>/values?match[]=<metric>` is cheaper.
4. **Aliveness.** `GET /api/v1/query?query=<metric>` — samples *right now*? A series present in `/series` can still be silent. Always pair with `up{job="…"}`.
5. **Shape.** `GET /api/v1/query_range` at `step=60s` for an hour — eyeball the trajectory.
6. **Aggregate.** `sum by(dim)(rate(<metric>[5m]))` — drop noise, keep the dimension that answers the question.
7. **Correlate.** Join metadata via `* on(instance) group_left(version) app_build_info` — the canonical PromQL join.
8. **Threshold.** Compare to a baseline: `offset 1w`, recording rule, alert rule (`/api/v1/rules`).

Budget: `step` ≥ 30s for dashboards, ≥ 60s for exploration, ≥ 300s for multi-day windows. `limit=…` (Prom 3+) caps `/query` result cardinality. Don't scan with `{__name__=~".+"}`. Mimir 422 means the limit kicked in — **never retry unchanged**, change the query. Full cost and error-handling table in [references/agent-workflow.md](references/agent-workflow.md) §5, §9.

## Triage scripts by symptom

Full PromQL for each in [references/agent-workflow.md](references/agent-workflow.md) §2. The one-liner reminders:

| Symptom | Start with |
|---|---|
| Service 5xx | rate of 5xx ÷ total, topk by handler, correlate by version via `group_left(version) app_build_info` |
| Slow p99 | histogram_quantile on `_bucket` rates, top handler, then CPU saturation + GC + dependency latency |
| OOM | `container_memory_working_set_bytes` / limits ratio, `deriv(...[1h])` for leak |
| Disk fill | `predict_linear(node_filesystem_avail_bytes[1h], 4*3600) < 0` |
| HPA flap | `changes(kube_hpa_status_current_replicas[1h]) > 6` |
| Node not ready | `kube_node_status_condition{condition="Ready",status="true"} == 0`, `up{job=~"kubelet|node-exporter"}` |

## PromQL — the things agents get wrong

Full reference in [references/promql.md](references/promql.md). The trap list:

- **`rate` before aggregation.** `sum(rate(x[5m]))` is correct; `rate(sum(x)[5m])` loses counter-reset detection. Agents invert this regularly.
- **Histogram quantile of averages.** `histogram_quantile` must consume **rates of `_bucket` series**, aggregated **by `le`** plus any other dimensions needed. `avg(_bucket)` is wrong.
- **`rate()` window too small.** `rate(x[1m])` with 15s scrape = 4 samples; a single missed scrape poisons it. Use `[5m]` as the floor, or `$__rate_interval` in Grafana.
- **`irate` in alerts.** Non-deterministic over a window; use `rate`.
- **`topk` in range queries.** Non-deterministic per step — `topk` ranks per evaluation point, so the *identity* of the top-K series flips. Fine for instant queries and tables; wrong for graphs.
- **`up == 1` ≠ healthy.** Says scrape worked. The service can 500 every request.
- **Mean latency.** `rate(_sum)/rate(_count)` hides the tail. Always `histogram_quantile`.
- **Regex not anchored.** It is. `=~"foo"` means `^foo$` — write `=~"foo.*"` for prefix match.
- **Counter on gauge.** `rate()` on a gauge produces garbage. `delta`/`deriv` are the gauge equivalents.
- **`absent()` with matchers that don't really exist.** `absent(up{job="api", pod="abc"})` fires even if `pod="abc"` never existed. Keep deadman-switch queries minimal.
- **Staleness marker.** Default `--query.lookback-delta=5m`. Series absent >5m disappear from `/query` results even if in `/series` list.
- **Mimir limits.** 422 after a tight query means `max_samples_per_query` or `max_query_length` tripped. Raise `step`, shrink window, tighten matchers.

Canonical join (agents underuse this — write it down):
```promql
sum by (version) (
  rate(http_requests_total{status=~"5.."}[5m])
  * on(instance) group_left(version) app_build_info
)
```

## Grafana — what the agent is actually doing

Three workflows matter:

### A. Query metrics *through* Grafana (agent has Grafana token but not Prom URL)
```bash
curl -sG -H "Authorization: Bearer $GF_TOKEN" \
  "$GRAFANA/api/datasources/proxy/uid/$DS_UID/api/v1/query" \
  --data-urlencode 'query=up'
```
Grafana enforces datasource RBAC. `/api/datasources` lists available datasources — find the Prometheus/Mimir one by `type`.

### B. Build or fix a dashboard
1. Fetch: `GET /api/dashboards/uid/<uid>` → `{dashboard, meta}`.
2. Mutate the `panels[].targets[].expr`, `fieldConfig.defaults.unit`, `legendFormat`, `templating.list[]`, etc.
3. Push back: `POST /api/dashboards/db` with the whole `dashboard` object (keep `version` from `meta.version`), `folderUid`, `overwrite: false`, `message` describing the agent's change.

The legacy `/api/dashboards/db` endpoint is still the default in 2026 tooling (Helm charts, grafana-operator, most MCP servers). Grafana 12 added a Kubernetes-style `/apis/dashboard.grafana.app/v1beta1/namespaces/<ns>/dashboards/<uid>` API with `resourceVersion` concurrency — use it only when the environment does.

Full JSON schema, panel anatomy, transformation catalog, variable interpolation specifiers, and the full bug-fix list in [references/grafana-dashboards.md](references/grafana-dashboards.md).

### C. Annotate what the agent did
Every automated intervention should leave a trail:
```bash
curl -X POST -H "Authorization: Bearer $GF_TOKEN" \
  -H 'Content-Type: application/json' \
  "$GRAFANA/api/annotations" \
  -d "{\"time\": $(date +%s%3N), \"tags\":[\"agent\",\"api\"], \"text\":\"scaled api 3→6 after 5xx spike\"}"
```
This is how post-mortems stay tractable when agents start acting on metrics.

## KPIs — what to actually measure

The judgment call the agent must make *before* picking metrics:

| Target | Framework | What to graph |
|---|---|---|
| A service (HTTP / gRPC / queue handler) | **RED** | Rate, Errors, Duration (p50/p95/p99) |
| A resource (CPU, mem, disk, GPU, pool) | **USE** | Utilization, Saturation, Errors |
| User experience | **Golden Signals + SLO** | Latency, Traffic, Errors, Saturation — wrapped in an availability/latency SLI |
| Alert trigger | **Multi-window multi-burn-rate** | 14.4× over 1h + 5m, 6× over 6h + 30m, 3× over 1d + 2h, 1× over 3d + 6h |

Never alert on single thresholds, never average latency, never aggregate errors across every route — always decompose. `up == 1` is not a health signal; a synthetic probe from outside the cluster is. Framework reference, exporter catalogs, anti-patterns, and the "what should I measure for X?" decision tree in [references/kpis-frameworks.md](references/kpis-frameworks.md).

## The top 10 diagnostic PromQL queries

When dropped into an unfamiliar cluster, start with these:

```promql
# 1. Scrape health across all jobs
sum by (job) (up)

# 2. Which scrape jobs have failing targets
sum by (job) (up == 0)

# 3. Top-10 metrics by cardinality (Mimir status)
#    -> GET /api/v1/status/tsdb

# 4. RPS per service (auto-discovers whatever exists)
sum by (job) (rate({__name__=~".+_requests_total"}[5m]))

# 5. Error rate per service
sum by (job) (rate({__name__=~".+_requests_total", status=~"5.."}[5m]))
  / sum by (job) (rate({__name__=~".+_requests_total"}[5m]))

# 6. p99 latency per service (classic histograms)
histogram_quantile(0.99,
  sum by (job, le) (rate({__name__=~".+_duration_seconds_bucket"}[5m])))

# 7. Pods crashlooping
kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} == 1

# 8. OOM-killed recently
sum by (namespace, pod) (
  kube_pod_container_status_last_terminated_reason{reason="OOMKilled"})

# 9. Nodes with pressure
kube_node_status_condition{status="true",
  condition=~"MemoryPressure|DiskPressure|PIDPressure"}

# 10. Anything going to fill its disk in 4 hours
predict_linear(node_filesystem_avail_bytes{
  fstype!~"tmpfs|overlay|squashfs"}[1h], 4*3600) < 0
```

Queries 4-6 use `__name__` wildcard — that's the "agent dropped into an unfamiliar cluster" shape. On production dashboards, prefer the actual metric name.

## Reference map

- [references/promql.md](references/promql.md) — full PromQL surface and the Prometheus HTTP API.
- [references/mimir-api.md](references/mimir-api.md) — Mimir architecture, endpoints, auth, per-tenant limits, curl recipes.
- [references/grafana-dashboards.md](references/grafana-dashboards.md) — dashboard JSON, variables, transformations, both dashboard APIs, provisioning, bug-fix catalog.
- [references/kpis-frameworks.md](references/kpis-frameworks.md) — RED / USE / Golden Signals, SLO burn-rate, exporter metric catalogs, anti-patterns, dashboard recipes, decision tree.
- [references/agent-workflow.md](references/agent-workflow.md) — runtime playbook, triage scripts, MCP servers, auth patterns, error-handling table, curl snippets.
- [references/sources.md](references/sources.md) — dated upstream sources for freshen mode.
