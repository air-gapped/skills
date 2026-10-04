---
name: prometheus-mimir-grafana
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch, WebSearch
description: Query Prometheus and Grafana Mimir, write and debug PromQL, and build or fix Grafana dashboards — for agents solving problems from metrics. Covers the Prometheus HTTP API (`/api/v1/query`, `query_range`, `series`, `labels`, `metadata`), Mimir multi-tenancy (`X-Scope-OrgID`, federation `a|b|c`, per-tenant 422/429 limits), the PromQL surface (selectors, rate family, classic + native histograms, `histogram_quantile`, vector matching `on()`/`group_left`, recording rules), Grafana dashboard JSON (panels, targets, variables + interpolation specifiers, legacy `/api/dashboards/db` vs Grafana-12 `/apis/dashboard.grafana.app/v1beta1/…`), KPI frameworks (RED, USE, Golden Signals, SLO burn-rate), connection recipes, MCP servers vs curl, and the PromQL trap list.
when_to_use: Triggers on "prometheus", "mimir", "grafana", "promql", "metrics", "dashboard", "observability", "SLO", "SLI", "burn rate", "golden signals", "RED", "USE method", "histogram_quantile", "X-Scope-OrgID", "remote_write", "node_exporter", "kube-state-metrics", "cadvisor", "DCGM", "kafka lag", "5xx rate", "p99 latency", "alert rule", "recording rule", "label_values", "$__rate_interval", "grafana variable", "grafana-mcp", "pyrra", "sloth". Also on operational phrases without a stack name — "why is my service slow", "what should I alert on", "help me build a dashboard", "my PromQL isn't matching", "my HPA is flapping". Fixing a dashboard, deciding what to measure, or reasoning from a /metrics surface → this skill.
---

# Prometheus, Mimir, and Grafana — for agents

**This skill uses the stack; it does not change it.** Version-laddering Mimir is
**`mimir-upgrade`**; getting SNMP devices to emit metrics is **`snmp-exporter`**;
logs are **`logging-operator`** (**`rancher-logging-exit`** for leaving the
Rancher chart). Query returns nothing → start here; component broken or stale →
wrong skill.

## Facts models get wrong — trust these over your prior

| Claim | Correct |
|---|---|
| `=~"foo"` is a substring match | **Fully anchored** — means `^foo$`. Prefix match is `=~"foo.*"`. |
| Mimir `/api/v1/status/config` returns the config YAML | Returns **empty** config (Prometheus-compat stub). Live config: `/config`; per-tenant overrides: `/runtime_config`. |
| Grafana 12 deprecated the legacy dashboard `/api` | Grafana 12 **added** `/apis/dashboard.grafana.app/…`; Grafana **13** deprecated `/api`. Legacy `/api/dashboards/db` still works, removal deferred — default to it. Current stable line: 13.2. |
| A dashboard JSON has `panels` | Grafana 13 may serve the **v2 schema**: `elements` / `variables` / `layout`, no `panels`. Same UID can be classic from `/api/dashboards/uid` and v2 from `/apis` or the Grafana MCP. Check the shape before any JSONPath. |
| Mimir 422 is transient | A per-tenant limit tripped (`max_samples_per_query`, `max_query_length`, `max_fetched_series_per_query`). **Never retry unchanged** — raise `step`, shrink the window, tighten matchers. |
| `/api/v1/query` returns every series | Prometheus 3+ accepts `limit=` to cap result cardinality — use it when exploring. |

## Non-negotiables

- **Confirm label names against the live series before filtering** (`/api/v1/series?match[]=<metric>` or `label_values()`). The 5xx label is exporter-dependent (`status`, `status_code`, `code`); a wrong name matches nothing and the panel reads zero errors.
- **Catalog ≠ alive.** A name in `/label/__name__/values` or `/series` can have no samples now; confirm with an instant query and `up{job=…}`.
- **Leave a trail.** Every automated intervention gets a Grafana annotation (`POST /api/annotations`, tags `["agent", …]`) and every dashboard save a `message`.

## Connect first

| Shape | Base URL | Auth | Tenant |
|---|---|---|---|
| Prometheus direct | `http://prometheus:9090` | none / Basic | n/a |
| Self-hosted Mimir gateway | `https://mimir.example.com/prometheus` | `Bearer` | `X-Scope-OrgID: <tenant>`; federate `a\|b\|c` |
| Grafana Cloud Mimir | `https://prometheus-prod-XX.grafana.net/api/prom` | Basic `instance_id:access_token` **or** `Bearer access_token` | in token |
| Grafana datasource proxy | `${GRAFANA}/api/datasources/proxy/uid/<ds-uid>` | Grafana SA token | datasource-configured |
| In-cluster via apiserver | `https://kubernetes.default.svc/…/services/prometheus-k8s:web/proxy` | SA token + CA | n/a |

Missing `X-Scope-OrgID` on Mimir → 401/403 mentioning "org id". Recipes: [references/mimir-api.md](references/mimir-api.md).

## Grafana MCP

Its tools describe themselves. What they don't say — dead metrics without a time window, the histogram helper collapsing dimensions, `run_panel_query` failing on v2 dashboards, v2 JSONPaths and bracket quoting — is in [references/agent-workflow.md §3a](references/agent-workflow.md#3a-grafanamcp-grafana--official-grafana-mcp-server). Read it before the first MCP call.

## Reference map

| Need | File |
|---|---|
| Discovery loop, triage PromQL by symptom, first 10 queries on an unfamiliar cluster, MCP gotchas, query cost, auth | [references/agent-workflow.md](references/agent-workflow.md) |
| PromQL surface, HTTP API, canonical `group_left` join, agent pitfall list | [references/promql.md](references/promql.md) |
| Mimir architecture, endpoints, per-tenant limits, curl recipes | [references/mimir-api.md](references/mimir-api.md) |
| Dashboard JSON (classic + v2), variables, transformations, both dashboard APIs, bug-fix catalog | [references/grafana-dashboards.md](references/grafana-dashboards.md) |
| What to measure: RED / USE / Golden Signals, SLO burn-rate tiers, exporter catalogs, dashboard recipes | [references/kpis-frameworks.md](references/kpis-frameworks.md) |
| Upstream sources and verification dates | [references/sources.md](references/sources.md) |
