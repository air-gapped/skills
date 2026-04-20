# Agent Runtime Playbook: Prometheus / Mimir / Grafana

Audience: an AI agent with network access to Prometheus/Mimir/Grafana that needs a disciplined runtime workflow. Focus is on *doing*, not theory.

## Contents
- [1. The operational loop](#1-the-operational-loop) — discover → labels → alive → shape → aggregate → correlate → threshold
- [2. Triage scripts](#2-triage-scripts) — 5xx / slow p99 / OOM / disk fill / HPA flap / node not ready
- [3. MCP servers worth knowing](#3-mcp-servers-worth-knowing)
- [4. When NOT to use an MCP server](#4-when-not-to-use-an-mcp-server)
- [5. Query cost awareness](#5-query-cost-awareness)
- [6. Authentication patterns](#6-authentication-patterns) — Cloud / gateway / proxy / in-cluster
- [7. Grafana-side operations](#7-grafana-side-operations)
- [8. Label exploration heuristics](#8-label-exploration-heuristics)
- [9. Error handling](#9-error-handling)
- [10. Practical reference curl snippets](#10-practical-reference-curl-snippets)

## 1. The operational loop

Never start by running `rate(http_requests_total[5m])` on faith. The metric may not exist, its labels may differ, or it may be silent right now.

**Step 1 — Discover metric names.** `GET /api/v1/label/__name__/values`. Returns 10k–200k names on a big cluster. Filter by prefix (`http_`, `kube_`, `node_`, `container_`, `process_`, `go_`, `up`, service name). Cache the result for the session. On Prom ≥ 2.24, narrow with `?match[]={job="api"}`.

**Step 2 — Inspect labels.** `GET /api/v1/series?match[]=http_requests_total` lists every unique label set. For one dimension: `GET /api/v1/label/status_code/values?match[]=http_requests_total` is much cheaper than pulling series.

**Step 3 — Instant aliveness check.** `GET /api/v1/query?query=http_requests_total` confirms samples exist at `time=now`. A metric in `/api/v1/series` (seen in the last 5-minute lookback) may still return empty from `/query` if scraping stopped. Always check `up{job="…"}` at the same time — `up == 0` means the question is "why is the target unreachable", not "where is the metric".

**Step 4 — Range exploration.** `GET /api/v1/query_range` with `step=60s` for exploration, `30s` for dashboards, `300s` for multi-day windows. Points returned ≈ `(end-start)/step`; stay under 11000. Fine steps explode cost and rarely change shape.

**Step 5 — Aggregate and filter.** Raw counters are noise. Apply `rate(metric[5m])`, `increase(metric[1h])`, `sum by (…)`, `histogram_quantile(0.95, sum by (le) (rate(..._bucket[5m])))`. Aggregate *up* to the dimension you care about; drop `instance`/`pod` unless debugging a specific replica.

**Step 6 — Join / correlate.** Attach metadata or compare metrics:
```promql
sum by (version) (
  rate(http_requests_total[5m])
  * on (job, instance) group_left(version) app_build_info
)
```
The `* on(...) group_left(label) meta_info` idiom is the canonical join.

**Step 7 — Threshold / baseline.** Compare live value to a reference: static, historical (`offset 1w`), or existing alert rule (`GET /api/v1/rules`).

## 2. Triage scripts

### 2a. Service returning 5xx
```promql
# Is the error real and current?
sum(rate(http_requests_total{job="api",status_code=~"5.."}[5m]))

# Error ratio
sum(rate(http_requests_total{job="api",status_code=~"5.."}[5m]))
  / sum(rate(http_requests_total{job="api"}[5m]))

# Which endpoints?
topk(5, sum by (handler) (rate(http_requests_total{job="api",status_code=~"5.."}[5m])))

# Which instances?
sum by (instance) (rate(http_requests_total{job="api",status_code=~"5.."}[5m]))

# Correlate to deploy
sum by (version) (
  rate(http_requests_total{status_code=~"5.."}[5m])
  * on (instance) group_left(version) app_build_info
)

# Upstream healthy?
sum by (dependency) (rate(dependency_errors_total{job="api"}[5m]))
```

### 2b. Slow response time
```promql
# p50/p95/p99
histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))

# Slowest handler
topk(5, histogram_quantile(0.95,
  sum by (handler, le) (rate(http_request_duration_seconds_bucket{job="api"}[5m]))))

# CPU saturation
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="prod",pod=~"api-.*"}[5m]))
  / sum by (pod) (kube_pod_container_resource_limits{resource="cpu",pod=~"api-.*"})

# Go GC pressure
rate(go_gc_duration_seconds_sum{job="api"}[5m])
  / rate(go_gc_duration_seconds_count{job="api"}[5m])

# JVM GC pause
rate(jvm_gc_pause_seconds_sum{job="api"}[5m])

# Queue depth
max by (pod) (work_queue_depth{job="api"})

# Dependency latency
histogram_quantile(0.95,
  sum by (dependency, le) (rate(dependency_duration_seconds_bucket{job="api"}[5m])))
```
Bisection order: dependency → queue → CPU → GC → network.

### 2c. Pod OOM-killing
```promql
sum by (namespace, pod) (kube_pod_container_status_last_terminated_reason{reason="OOMKilled"})

max by (pod) (container_memory_working_set_bytes{namespace="prod",pod=~"api-.*"})
  / max by (pod) (kube_pod_container_resource_limits{resource="memory",namespace="prod",pod=~"api-.*"})

deriv(container_memory_working_set_bytes{namespace="prod",pod=~"api-.*"}[1h])

increase(kube_pod_container_status_restarts_total{namespace="prod",pod=~"api-.*"}[1h])
```
Ratio near 1.0 with steady `deriv` = leak. Ratio < 0.5 with spike = burst exceeding limits.

### 2d. Disk filling up
```promql
100 * (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})

predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[1h], 4*3600) < 0

topk(5, deriv(node_filesystem_avail_bytes[1h]) * -1)

100 * (node_filesystem_files_free / node_filesystem_files)
```
`predict_linear` extrapolates linearly; false-positive on bursty disks.

### 2e. HPA flapping
```promql
changes(kube_hpa_status_current_replicas{namespace="prod",hpa="api"}[1h])  # >6 is flapping

kube_hpa_status_current_replicas{namespace="prod",hpa="api"}
kube_hpa_spec_min_replicas{namespace="prod",hpa="api"}
kube_hpa_spec_max_replicas{namespace="prod",hpa="api"}

kube_hpa_status_current_metrics_average_value{namespace="prod",hpa="api"}
kube_hpa_spec_target_metric{namespace="prod",hpa="api"}

# KEDA
keda_scaler_active
keda_scaler_metrics_value
```

### 2f. Node not ready
```promql
kube_node_status_condition{condition="Ready",status="true"} == 0

kube_node_status_condition{status="true",condition=~"MemoryPressure|DiskPressure|PIDPressure"}

up{job=~"kubelet|node-exporter",instance=~"the-node.*"}

node_load5{instance=~"the-node.*"}
  / count by (instance) (node_cpu_seconds_total{mode="idle",instance=~"the-node.*"})
```

## 3. MCP servers worth knowing

### 3a. `grafana/mcp-grafana` — official Grafana MCP server
- Repo: `https://github.com/grafana/mcp-grafana`
- Language: Go. Transport: stdio default; SSE/HTTP via flag.
- Auth: `GRAFANA_URL` + `GRAFANA_SERVICE_ACCOUNT_TOKEN` (or `GRAFANA_API_KEY`). Honors `X-Grafana-Org-Id`.
- Representative tools:
  - `list_datasources`, `get_datasource_by_uid`
  - `query_prometheus` (instant+range), `list_prometheus_metric_names`, `list_prometheus_label_names`, `list_prometheus_label_values`
  - `query_loki_logs`, `query_loki_stats`, `list_loki_label_names`, `list_loki_label_values`
  - `search_dashboards`, `get_dashboard_by_uid`, `update_dashboard`
  - `list_alert_rules`, `get_alert_rule_by_uid`, `list_oncall_schedules`
  - `list_incidents`, `create_incident`, `add_activity_to_incident`
- Config block:
  ```json
  {
    "mcpServers": {
      "grafana": {
        "command": "mcp-grafana",
        "env": {
          "GRAFANA_URL": "https://grafana.example.com",
          "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_..."
        }
      }
    }
  }
  ```
- Install: `go install github.com/grafana/mcp-grafana/cmd/mcp-grafana@latest`, or a release binary.
- Quirks: Prom/Loki tools go via Grafana's datasource proxy, so RBAC = SA's datasource perms. Dashboard update needs correct `version` or `overwrite: true`.

### 3b. `pab1it0/prometheus-mcp-server` — community Prometheus MCP
- Repo: `https://github.com/pab1it0/prometheus-mcp-server`
- Language: Python. Transport: stdio.
- Auth via env: `PROMETHEUS_URL`, optional `PROMETHEUS_USERNAME`/`PROMETHEUS_PASSWORD` (Basic) or `PROMETHEUS_TOKEN` (Bearer). Multi-tenant Mimir: `ORG_ID` → `X-Scope-OrgID`.
- Typical tools: `execute_query`, `execute_range_query`, `list_metrics`, `get_metric_metadata`, `get_targets`.
- Install: `uvx prometheus-mcp-server` or `pipx install prometheus-mcp-server`.

### 3c. Mimir
No widely adopted `mcp-mimir` as of 2026. Mimir speaks the Prometheus HTTP API, so point a Prometheus MCP server at Mimir's query frontend (`/prometheus/api/v1/…`) with `X-Scope-OrgID`. For admin endpoints (runtime config, ingester ring) use curl directly — no MCP server covers that surface.

## 4. When NOT to use an MCP server

Use plain HTTP (curl / `httpx` / `requests`) when:
- **One-off incident triage** — you already have a shell in-cluster; installing an MCP server takes longer than the fix.
- **Exploration at scale** — MCP tool descriptions cost tokens. One `curl .../label/__name__/values | jq` is cheaper than listing 10k metrics through a tool that marshals JSON-RPC.
- **Admin/write paths** — MCP servers rarely expose rule reload, tenant limits, ingester flush, or runtime config. Go direct.
- **Custom headers or edge-case auth** — per-call `X-Scope-OrgID`, custom JWT audiences, or mTLS usually can't be done per-call in stock MCP servers.
- **Deterministic scripting** — shell+curl is reproducible and auditable. MCP tool surfaces drift.

Use an MCP server when:
- A persistent agent session spans Prometheus + Loki + Grafana and you want consistent tool discovery.
- The auth is fiddly and you'd rather externalize it once.
- You want typed tool schemas instead of JSON parsing in the prompt.

## 5. Query cost awareness

- **`step` floors:** ≥30s dashboards, ≥60s exploration, ≥300s multi-day. `step=15s` over 30d pulls 173k points per series × N series = millions of samples.
- **`limit` on instant query** (Prometheus 3.0+): `/api/v1/query?query=...&limit=1000` caps result cardinality. Use it.
- **`match[]` on `/api/v1/series` and `/api/v1/labels`** — avoid full-catalog scans. Bare `/api/v1/series` on large tenants returns hundreds of MB.
- **Avoid `topk(1000, ...)`** — ranks the full vector. `topk(10, ...)` is what you want.
- **Avoid `{__name__=~".+"}`** and similar catch-alls.
- **Know `max_query_length`** before 30d queries. Mimir defaults: 12h instant, 31d range (self-hosted often tighter). Check `/api/v1/status/runtime_config` on Mimir.
- **Prefer recording rules** over repeat ad-hoc queries. If you're re-running `sum by(service)(rate(...)[5m])` every minute, propose a recording rule.
- **Sample math:** points = `(end-start)/step`, capped ~11000 in Prom. Mimir's querier enforces `max_samples` (default 50M).

## 6. Authentication patterns

**Grafana Cloud** — either shape works:
```bash
curl -u "$GRAFANA_INSTANCE_ID:$GRAFANA_CLOUD_API_KEY" \
  "https://prometheus-prod-XX.grafana.net/api/prom/api/v1/query?query=up"
curl -H "Authorization: Bearer $GRAFANA_CLOUD_ACCESS_TOKEN" \
  "https://prometheus-prod-XX.grafana.net/api/prom/api/v1/query?query=up"
```

**Self-hosted Mimir behind a gateway:**
```bash
curl -H "Authorization: Bearer $MIMIR_TOKEN" \
     -H "X-Scope-OrgID: tenant-1" \
     "https://mimir.example.com/prometheus/api/v1/query?query=up"
```

**Prometheus direct:** often no auth. Prom has no RBAC — port access == full query access.

**Grafana datasource proxy** (reach Prometheus through Grafana auth):
```bash
curl -H "Authorization: Bearer $GRAFANA_SA_TOKEN" \
  "https://grafana.example.com/api/datasources/proxy/uid/$DS_UID/api/v1/query?query=up"
```

**Kubernetes in-cluster via apiserver proxy:**
```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
CA=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
curl --cacert "$CA" -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/monitoring/services/prometheus-k8s:web/proxy/api/v1/query?query=up"
```

## 7. Grafana-side operations

**List dashboards** — `GET /api/search?type=dash-db&limit=5000`. Filters: `query=<text>`, `tag=<tag>`, `folderUIDs=<uid>`.

**Fetch dashboard** — `GET /api/dashboards/uid/$UID`. Returns `{dashboard, meta}`. Keep `meta.version` for updates.

**Update dashboard:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     "$GRAFANA/api/dashboards/db" \
     -d '{"dashboard":{...,"version":42},"folderUid":"abc","message":"agent: fixed p95","overwrite":false}'
```

**Annotations:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     "$GRAFANA/api/annotations" \
     -d '{"time":1713561600000,"tags":["deploy","api"],"text":"v2.3.0"}'
```
Time is ms since epoch.

**Multi-org Grafana:** add `X-Grafana-Org-Id: 3` header.

## 8. Label exploration heuristics

Top-down on an unfamiliar cluster:

1. **Metric name scan** — `GET /api/v1/label/__name__/values`. High-signal prefixes:
   - `up` — per-target scrape health (always present)
   - `scrape_*` — per-target scrape stats
   - `http_*` / `grpc_*` — RED inputs
   - `node_*` — node-exporter — host CPU/mem/disk/net
   - `kube_*` — kube-state-metrics — K8s object state
   - `container_*` — cAdvisor — per-container resources
   - `process_*` — per-process RSS/CPU/FD
   - `go_*` / `jvm_*` / `python_*` — runtime
2. **`_info` suffix** carries metadata as labels (`app_build_info{version=...}`, `kube_pod_info{...}`). Value always 1. Use in `group_left` joins.
3. **`_total` suffix = counter** — always wrap in `rate()` or `increase()`. Raw values are meaningless.
4. **`_bucket` suffix = histogram** — pair with `histogram_quantile()`; or `_count`/`_sum` for averages.
5. **HELP text:** `GET /api/v1/metadata?metric=http_requests_total` — returns `help`/`type`/`unit`.

## 9. Error handling

| Code | Meaning | Recovery |
|------|---------|----------|
| `200` + `status:"error"` | Valid HTTP but semantic failure. Body has `errorType` + `error`. | Fix query. No retry. |
| `400` | Malformed request — bad time range, invalid `step`, missing `query`. | Fix. No retry. |
| `401`/`403` | Auth missing/insufficient. Grafana SA lacks datasource perms; Mimir missing `X-Scope-OrgID`. | Fix auth. No retry. |
| `404` | Wrong path — common on Mimir where it's `/prometheus/api/v1/...`. | Fix URL. |
| `422` | Syntactically valid but executionally failed: `too many samples`, `max_samples` exceeded. | Widen `step`, shrink window, tighter matchers. |
| `429` | Rate limited (Mimir per-tenant). | Back off exponentially per `Retry-After`. |
| `502` | Upstream (querier/store-gateway/ingester) down or overloaded. | Retry once after 2–5s. |
| `503` | Service unavailable. | Back off. |
| `504` | Gateway timeout. | Shrink window, raise `step`, or split. |

JSON error shape:
```json
{"status":"error","errorType":"bad_data","error":"1:1: parse error: ..."}
```

`errorType` values: `bad_data`, `execution`, `timeout`, `canceled`, `unavailable`, `not_found`.

## 10. Practical reference curl snippets

```bash
PROM=https://mimir.example.com/prometheus
TOKEN="Bearer glsa_..."
ORG_ID=prod
H_AUTH=(-H "Authorization: $TOKEN" -H "X-Scope-OrgID: $ORG_ID")

# --- Discovery ---
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/label/__name__/values"
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/label/__name__/values" \
  --data-urlencode 'match[]={job="api"}'
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/metadata" \
  --data-urlencode 'metric=http_requests_total'
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/series" \
  --data-urlencode 'match[]=http_requests_total'
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/label/status_code/values" \
  --data-urlencode 'match[]=http_requests_total'

# --- Query ---
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/query" \
  --data-urlencode 'query=sum(rate(http_requests_total{status_code=~"5.."}[5m]))'
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/query" \
  --data-urlencode 'query=http_requests_total' --data-urlencode 'limit=100'

NOW=$(date -u +%s); START=$((NOW - 3600))
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/query_range" \
  --data-urlencode 'query=sum by (handler) (rate(http_requests_total[5m]))' \
  --data-urlencode "start=$START" --data-urlencode "end=$NOW" \
  --data-urlencode 'step=60s'

curl -sG "${H_AUTH[@]}" "$PROM/api/v1/format_query" \
  --data-urlencode 'query=sum by(job)(rate(http_requests_total[5m]))'
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/status/tsdb"
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/targets?state=active"
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/rules"
curl -sG "${H_AUTH[@]}" "$PROM/api/v1/alerts"

# --- Grafana ---
GRAFANA=https://grafana.example.com
GF_TOKEN="Bearer glsa_..."
curl -sG -H "Authorization: $GF_TOKEN" "$GRAFANA/api/search" \
  --data-urlencode 'type=dash-db'
curl -s -H "Authorization: $GF_TOKEN" "$GRAFANA/api/dashboards/uid/$UID"
curl -sX POST -H "Authorization: $GF_TOKEN" -H 'Content-Type: application/json' \
  "$GRAFANA/api/dashboards/db" --data @dashboard.json
curl -sG -H "Authorization: $GF_TOKEN" \
  "$GRAFANA/api/datasources/proxy/uid/$DS_UID/api/v1/query" \
  --data-urlencode 'query=up'
```

## Closing: shape of a good session

1. Discover metric names, cache.
2. Pick candidate, inspect labels.
3. Instant query to confirm live.
4. Small range to see shape.
5. Aggregate up to the answering dimension.
6. Cross-check vs alert rules / baselines.
7. Annotate Grafana with what you did and concluded.
8. Don't loop — if three queries give no signal, the metric is wrong. Go back to step 1.

The failure mode to avoid: confidently running `rate(http_requests_total[5m])` against a cluster where it's `nginx_http_requests_total` or `job="api-server"`. Discovery first, always.
