# Grafana Mimir (2026) — API + Architecture Reference

Sources: grafana.com/docs/mimir/latest/references/http-api/, /manage/secure/authentication-and-authorization/, /references/configuration-parameters/.

## Contents
- [1. What it is](#1-what-it-is)
- [2. Multi-tenancy](#2-multi-tenancy) — `X-Scope-OrgID`, federation, tenant-ID rules
- [3. Read path — Prometheus-compatible HTTP API](#3-read-path--prometheus-compatible-http-api)
- [4. Write path](#4-write-path) — remote_write, OTLP, Influx
- [5. Ruler — recording & alerting rules](#5-ruler--recording--alerting-rules)
- [6. Alertmanager (multi-tenant)](#6-alertmanager-multi-tenant)
- [7. Component admin endpoints](#7-component-admin-endpoints)
- [8. Per-tenant limits (operator-facing)](#8-per-tenant-limits-operator-facing)
- [9. Response / error shapes](#9-response--error-shapes)
- [10. curl patterns for agents](#10-curl-patterns-for-agents)
- [11. Telling Prometheus from Mimir at runtime](#11-telling-prometheus-from-mimir-at-runtime)
- [12. Grafana Cloud Mimir auth patterns](#12-grafana-cloud-mimir-auth-patterns)
- [13. Tooling](#13-tooling)

## 1. What it is

Horizontally-scalable, multi-tenant, long-term storage for Prometheus metrics with object-storage backend. Wire-compatible with Prometheus remote_write (1.0 + 2.0 proto+snappy), OTLP, and Prometheus HTTP query API. Born from Cortex. Services: distributor, ingester, querier, query-frontend, query-scheduler, compactor, store-gateway, ruler, alertmanager, overrides-exporter. Runs monolithic / microservices / read-write-backend modes.

## 2. Multi-tenancy

**Default: multi-tenancy ON.** Every request must carry `X-Scope-OrgID: <tenant-id>` header or it is rejected.

Disable: `-auth.multitenancy-enabled=false` → internally sets tenant to `anonymous`. Custom: `-auth.no-auth-tenant=<name>`.

Federated queries: `X-Scope-OrgID: tenant-a|tenant-b|tenant-c` — reads across tenants in one call.

Mimir does **not** ship authentication. Always front with a reverse proxy (nginx/envoy), oauth2-proxy, mTLS gateway, or Grafana Enterprise Metrics Gateway. Typical `cortex-tenant` sidecar maps Prometheus labels → `X-Scope-OrgID`.

Tenant ID character rules: 150-char max, alphanumeric plus `! # $ % & ' ( ) * + - . / : ; = ? @ [ \ ] ^ _ \` { | } ~`. Reserved: empty, `.`, `..`, `__mimir_cluster`.

## 3. Read path — Prometheus-compatible HTTP API

All read endpoints sit under `/<prometheus-http-prefix>/api/v1/...` (default prefix `/prometheus`, configurable via `-http.prometheus-http-prefix`).

### Query
```
GET|POST /prometheus/api/v1/query
GET|POST /prometheus/api/v1/query_range
```
Same shape as Prometheus: `query`, `time|start|end|step`, `timeout`, `limit`, `lookback_delta`, `stats=all`. Response envelope identical: `{status, data: {resultType, result}, warnings, infos}`.

### Discovery
```
GET|POST /prometheus/api/v1/series
GET|POST /prometheus/api/v1/labels
GET      /prometheus/api/v1/label/<name>/values
GET      /prometheus/api/v1/metadata
GET|POST /prometheus/api/v1/format_query
GET|POST /prometheus/api/v1/query_exemplars
POST     /prometheus/api/v1/read            # remote_read (protobuf)
```

### Cardinality analysis (requires `-querier.cardinality-analysis-enabled=true`)
```
GET|POST /prometheus/api/v1/cardinality/active_series
GET|POST /prometheus/api/v1/cardinality/label_names
GET|POST /prometheus/api/v1/cardinality/label_values
```
`count_method=inmemory|active`. Active = samples within `-ingester.active-series-metrics-idle-timeout`.

### Status (Prometheus-compat shims)
`/api/v1/status/config` and `/api/v1/status/flags` exist but return empty on Mimir (use `/config` and `/runtime_config` instead). `/api/v1/status/buildinfo` works normally.

### Query stats headers
Request `X-Mimir-Response-Query-Stats: true` → response includes `Server-Timing` header with `encode_time`, `estimated_series_count`, `fetched_chunks`, `query_wall_time`, `queue_time`, etc.

## 4. Write path

```
POST /api/v1/push                         # Prometheus remote_write (proto+snappy)
POST /otlp/v1/metrics                     # OTLP HTTP
POST /api/v1/push/influx/write            # InfluxDB line protocol
```
Single-tenant: `X-Scope-OrgID: anonymous` if multitenancy disabled. Multi-tenant: tenant header required; per-tenant `ingestion_rate` / `ingestion_burst_size` enforced → 429 on overflow.

## 5. Ruler — recording & alerting rules

Prometheus-compat read:
```
GET /prometheus/api/v1/rules
GET /prometheus/api/v1/alerts
```

Config API (per-tenant rule CRUD):
```
GET    /prometheus/config/v1/rules
GET    /prometheus/config/v1/rules/{namespace}
GET    /prometheus/config/v1/rules/{namespace}/{group}
POST   /prometheus/config/v1/rules/{namespace}     # body: YAML rule group
DELETE /prometheus/config/v1/rules/{namespace}/{group}
DELETE /prometheus/config/v1/rules/{namespace}
```
POST accepts `Content-Type: application/yaml`, returns `202 Accepted`. Ruler admin: `/ruler/ring`, `/ruler/rule_groups`, `POST /ruler/delete_tenant_config`.

## 6. Alertmanager (multi-tenant)

```
GET    /api/v1/alerts                             # tenant's AM config (YAML)
POST   /api/v1/alerts                             # set config
DELETE /api/v1/alerts                             # remove config
GET    /alertmanager                              # UI
GET    /multitenant_alertmanager/{status,configs,ring}
POST   /multitenant_alertmanager/delete_tenant_config
```

## 7. Component admin endpoints

### Distributor
`/distributor/ring`, `/distributor/all_user_stats`, `/distributor/ha_tracker`.

### Ingester
`/ingester/ring`, `/ingester/tenants`, `/ingester/tsdb/{tenant}`, `/ingester/flush`, `/ingester/prepare-shutdown`, `/ingester/prepare-partition-downscale`, `/ingester/prepare-instance-ring-downscale`.

### Store-gateway
`/store-gateway/ring`, `/store-gateway/tenants`, `/store-gateway/tenant/{tenant}/blocks`, `/store-gateway/prepare-shutdown`.

### Compactor
`/compactor/ring`, `/compactor/tenants`, `/compactor/tenant/{tenant}/planned_jobs`, `POST /compactor/delete_tenant`, `GET /compactor/delete_tenant_status`.

Block upload (manual import):
```
POST /api/v1/upload/block/{block}/start          # meta.json body
POST /api/v1/upload/block/{block}/files?path=... # index / chunks
POST /api/v1/upload/block/{block}/finish
GET  /api/v1/upload/block/{block}/check          # uploading|validating|complete|failed
```

### Universal (all services)
- `GET /` — index/links
- `GET /config?mode=diff|defaults` — loaded config (secrets masked)
- `GET /runtime_config` — live runtime overrides
- `GET /services` — internal service state
- `GET /ready` — 200 when ready
- `GET /metrics` — Prometheus exposition
- `GET /memberlist` — cluster gossip state
- `GET /api/v1/user_limits` — live per-tenant limits (current tenant)
- `GET /debug/pprof/{heap,block,profile,trace,goroutine,mutex}` + `/debug/fgprof`

## 8. Per-tenant limits (operator-facing)

Configured in `limits:` block, overridable via runtime config YAML reloaded on interval (`-runtime-config.reload-period=10s`). Check live values at `GET /api/v1/user_limits`.

| Limit | Purpose | Error surface |
|---|---|---|
| `max_query_length` | longest range window | HTTP 422 `query length ... exceeds limit` |
| `max_query_lookback` | how far back `@`/`offset`/start can reach | HTTP 422 |
| `max_samples_per_query` | in-memory sample cap | HTTP 422 `query processing would load too many samples` |
| `max_fetched_series_per_query` | series fetched from store/ingester | HTTP 422 |
| `max_query_parallelism` | concurrent sub-queries | enforced by query-frontend |
| `max_label_names_per_series` | write-path cardinality guard | HTTP 400 on push (bypass: `X-Mimir-SkipLabelCountValidation`) |
| `max_global_series_per_user` | tenant active-series ceiling | HTTP 400 `per-user series limit exceeded` |
| `ingestion_rate`, `ingestion_burst_size` | write-path rps | HTTP 429 |
| `ruler_max_rules_per_rule_group`, `ruler_max_rule_groups_per_tenant` | rule config | 400/422 on rule POST |

Remedy hierarchy when hitting 422: tighter matchers → shorter window → higher `step` → split into multiple queries client-side → ask operator to raise the limit. **Never retry unchanged** — the limit is deterministic.

## 9. Response / error shapes

Success envelope same as Prometheus. Error envelope:
```json
{"status":"error","errorType":"...","error":"..."}
```

Mimir-specific status codes layered over Prom contract:
- `201` Alertmanager config POST
- `202` Ruler rule POST / config change (async)
- `409` block upload conflict (already exists)
- `422` expensive query rejected by limits (NOT just query parse error — interpret `errorType` field)
- `429` ingestion rate limit

## 10. curl patterns for agents

Discovery/query under a gateway with Bearer + org:
```bash
PROM="https://mimir.example.com/prometheus"
HDR=(-H "Authorization: Bearer $TOKEN" -H "X-Scope-OrgID: prod")

curl -sG "${HDR[@]}" "$PROM/api/v1/label/__name__/values"
curl -sG "${HDR[@]}" "$PROM/api/v1/label/__name__/values" \
     --data-urlencode 'match[]={job="api"}'
curl -sG "${HDR[@]}" "$PROM/api/v1/series" \
     --data-urlencode 'match[]={job="api"}'
curl -sG "${HDR[@]}" "$PROM/api/v1/metadata" \
     --data-urlencode 'metric=http_requests_total'
curl -sG "${HDR[@]}" "$PROM/api/v1/query" \
     --data-urlencode 'query=sum(rate(http_requests_total[5m]))'
curl -sG "${HDR[@]}" "$PROM/api/v1/query_range" \
     --data-urlencode 'query=sum by(route)(rate(http_requests_total[5m]))' \
     --data-urlencode "start=$(date -u -d '1 hour ago' +%s)" \
     --data-urlencode "end=$(date -u +%s)" \
     --data-urlencode 'step=60s'

# Federated tenants
curl -sG -H "X-Scope-OrgID: us-east|us-west" "$PROM/api/v1/query" \
     --data-urlencode 'query=sum(up)'

# Limits check
curl -sG "${HDR[@]}" "https://mimir.example.com/api/v1/user_limits"

# Ruler — list all rule groups for tenant
curl -sG "${HDR[@]}" "https://mimir.example.com/prometheus/config/v1/rules"

# Ruler — upload YAML rule group
curl -X POST "${HDR[@]}" -H 'Content-Type: application/yaml' \
     --data-binary @group.yaml \
     "https://mimir.example.com/prometheus/config/v1/rules/my_namespace"
```

## 11. Telling Prometheus from Mimir at runtime

- `GET /api/v1/status/buildinfo` — field `version` + product (Prometheus vs Mimir).
- Mimir's API is under `/prometheus/api/v1/…` by default; Prometheus is `/api/v1/…`.
- 401/403 missing `X-Scope-OrgID` is a Mimir signature.
- `GET /ready` works on both (200 when ready).
- `GET /api/v1/status/config` on Mimir returns empty — on Prometheus it returns loaded YAML.

## 12. Grafana Cloud Mimir auth patterns

```bash
# Basic auth with instance ID + access policy token
curl -u "$INSTANCE_ID:$CLOUD_TOKEN" \
     "https://prometheus-prod-XX.grafana.net/api/prom/api/v1/query?query=up"

# Bearer token
curl -H "Authorization: Bearer $CLOUD_TOKEN" \
     "https://prometheus-prod-XX.grafana.net/api/prom/api/v1/query?query=up"
```
Path prefix for Grafana Cloud is `/api/prom` (not `/prometheus`). Tenant is implied by the URL/token.

## 13. Tooling

- `mimirtool` — `rules`, `analyze dashboards`, `analyze prometheus` (metric usage audit), `remote-read export`, `rules diff`.
- `promtool` — query instant/range, unit tests for rules, check rules/config.
- `cortex-tenant` — proxy that promotes a Prometheus label into `X-Scope-OrgID`.
- Grafana Alloy's `mimir.rules.kubernetes` component — syncs PrometheusRule CRs into Mimir ruler.
