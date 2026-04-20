# Grafana Dashboards (2026) — JSON model + Variables + Transformations + API

Sources: grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/, /variables/, /panels-visualizations/query-transform-data/transform-data/, /developer-resources/api-reference/http-api/dashboard/.

## Contents
- [1. Two API surfaces exist in 2026](#1-two-api-surfaces-exist-in-2026) — legacy vs Grafana-12 Kubernetes-style
- [2. Dashboard JSON model (classic)](#2-dashboard-json-model-classic)
- [3. Panel schema](#3-panel-schema) — targets, fieldConfig, options
- [4. Variables / templating](#4-variables--templating) — 8 types + interpolation format specifiers + built-in `$__*`
- [5. Transformations](#5-transformations)
- [6. Provisioning](#6-provisioning) — file / ConfigMap sidecar / operator
- [7. Legacy dashboard API](#7-legacy-dashboard-api-still-canonical-in-2026-tooling) — `POST /api/dashboards/db`
- [8. Kubernetes-style API (Grafana 12+)](#8-kubernetes-style-api-grafana-12)
- [9. Common dashboard bugs + fixes](#9-common-dashboard-bugs--fixes)
- [10. Dashboards-as-code](#10-dashboards-as-code-brief)
- [11. Annotations](#11-annotations)
- [12. Deep-linking](#12-deep-linking)

## 1. Two API surfaces exist in 2026

Grafana ≥ 12 introduced a **Kubernetes-style dashboard API** alongside the long-standing legacy REST endpoints.

- **Legacy (still the default for most tools in 2026):**
  - `POST /api/dashboards/db` (create/update)
  - `GET /api/dashboards/uid/{uid}`
  - `DELETE /api/dashboards/uid/{uid}`
  - `GET /api/search`
- **Kubernetes-style (Grafana 12+):**
  - `POST /apis/dashboard.grafana.app/v1beta1/namespaces/{ns}/dashboards`
  - `PUT/GET/DELETE /apis/dashboard.grafana.app/v1beta1/namespaces/{ns}/dashboards/{uid}`
  - `resourceVersion`-based optimistic concurrency

Per the Grafana 13 deprecation notice: `/api/` endpoints are being phased out *but remain fully accessible and operative*. **Default to the legacy API unless the environment explicitly uses the new one** — most Helm charts, operator CRDs, dashboards-as-code tools still speak legacy.

## 2. Dashboard JSON model (classic)

```json
{
  "id": null,
  "uid": "cLV5GDCkz",
  "title": "API service — RED",
  "tags": ["service:api", "red"],
  "timezone": "browser",
  "editable": true,
  "graphTooltip": 1,
  "panels": [ ... ],
  "templating": { "list": [ ... ] },
  "annotations": { "list": [ ... ] },
  "time": { "from": "now-6h", "to": "now" },
  "timepicker": { "refresh_intervals": ["5s", "10s", "30s", "1m"] },
  "refresh": "30s",
  "schemaVersion": 41,
  "version": 17,
  "links": [],
  "fiscalYearStartMonth": 0
}
```

Top-level fields:
- `uid` — 8-40 char public identifier; stable across rename.
- `schemaVersion` — bumped per Grafana release when the schema changes. Newer Grafana auto-migrates older `schemaVersion` values on load.
- `version` — bumped on each save. Used for optimistic concurrency on legacy API.
- `graphTooltip` — 0 none, 1 shared crosshair, 2 shared crosshair+tooltip.
- `timezone` — `"browser"` / `"utc"` / IANA name.
- `refresh` — auto-refresh interval like `"30s"`.

## 3. Panel schema

```json
{
  "id": 4,
  "type": "timeseries",
  "title": "Request rate per route",
  "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
  "datasource": { "type": "prometheus", "uid": "$DS_PROMETHEUS" },
  "targets": [
    {
      "refId": "A",
      "expr": "sum by (route) (rate(http_requests_total{job=\"$service\"}[$__rate_interval]))",
      "legendFormat": "{{route}}",
      "interval": "",
      "exemplar": true,
      "range": true,
      "instant": false,
      "editorMode": "code"
    }
  ],
  "fieldConfig": {
    "defaults": { "unit": "reqps", "min": 0 },
    "overrides": []
  },
  "options": {
    "legend": { "displayMode": "table", "placement": "right" },
    "tooltip": { "mode": "multi" }
  },
  "transformations": []
}
```

### gridPos
24-column grid, `w`/`h` in grid units (≈ 30 px each). `x` 0-23, `y` grows downward.

### targets[] — Prometheus datasource
- `expr` — PromQL.
- `refId` — one char per target (A, B, ...).
- `legendFormat` — `{{label}}` template, replaces noisy `{instance="...", pod="..."}` auto-legend.
- `interval` — override for `$__interval`. Leave empty to inherit.
- `range` / `instant` — booleans; both can be true (Prometheus datasource will emit both series and single-sample overlay).
- `format` — `time_series` | `table` | `heatmap`.
- `editorMode` — `"code"` (raw PromQL) or `"builder"` (UI form).
- `exemplar` — set `true` to request trace exemplars for histogram queries.

### fieldConfig
- `defaults` — unit, decimals, min, max, displayName, thresholds, color, mappings, links.
- `overrides` — per-series/per-field tweaks. Matchers: `byName`, `byRegexp`, `byType`, `byFrameRefId`.
- Common units: `reqps`, `percentunit` (0-1), `percent` (0-100), `s`, `ms`, `bytes`, `decbytes`, `Bps`, `short`.

### options
Panel-type-specific. `timeseries` has `legend`, `tooltip`, `lineWidth`, `fillOpacity`, `stacking`, `thresholdsStyle`.

### Panel types worth knowing
`timeseries`, `stat`, `gauge`, `bargauge`, `table`, `heatmap`, `histogram`, `piechart`, `state-timeline`, `status-history`, `trend`, `text`, `alertlist`, `annolist`, `dashboardlist`, `logs`, `traces`, `nodegraph`, `canvas`, `xy-chart`, `barchart`, `geomap`.

## 4. Variables / templating

### Eight variable types
1. `query` — datasource-backed
2. `custom` — comma-separated list
3. `textbox` — free text
4. `constant` — hidden constant (for provisioned dashboards)
5. `datasource` — switches datasource for the whole dashboard
6. `interval` — time-span chooser
7. `adhoc` — key/value filters injected into every query as extra label matchers
8. `switch` — two-value toggle (newer)

### Prometheus query-variable forms
- `label_values(metric_name, label)` — distinct values of `label` on `metric_name`
- `label_values(label)` — distinct values globally
- `label_names(metric_name)` — label names on a metric
- `metrics(<regex>)` — metric names matching regex
- `query_result(<promql>)` — full PromQL result (used with Regex field to parse out IDs)

### Refresh
- **Never** — value cached indefinitely
- **On dashboard load** — when the dashboard opens
- **On time range change** — also re-runs when user scrolls / zooms

### Selection behavior
- `Multi-value` — tick box to pick several
- `Include All option` — adds an `All` entry
- `Custom all value` — custom regex under the hood, e.g. `.*` or `api-.*`
- `Regex` — post-filter or rewrite (with capture groups)
- `Sort` — alpha, numeric, ascending/descending, case-insensitive
- `Allow custom values` — user can type in values that weren't in the query

### Variable dependencies ("chained")
A variable's query can reference another variable: `label_values(http_requests_total{namespace="$namespace"}, pod)`. Parent changes re-trigger children.

### Ad-hoc filters
Injected as extra `{label="value"}` matchers into **every** query on the dashboard, per datasource. Magic for letting users slice without editing panels.

### Interpolation formats
```
$var, ${var}                    # default
${var:raw}                      # unescaped
${var:regex}                    # regex-safe (pipe-separated)
${var:glob}                     # glob
${var:json}                     # JSON array
${var:csv}                      # comma-joined
${var:pipe}                     # pipe-joined
${var:distributed}              # for repeated panel queries (InfluxDB-style)
${var:singlequote}              # single-quoted each item
${var:doublequote}              # double-quoted
${var:sqlstring}                # SQL-safe
${var:text}                     # display text, not value
${var:queryparam}               # URL-query-param form: var=a&var=b
${var:percentencode}            # percent-encoded
${var:lucene}                   # Elasticsearch Lucene
```

### Built-in global variables
```
$__interval                     # auto step based on panel width
$__rate_interval                # safe rate window: max($__interval, 4 × scrape)
$__range                        # current time range as duration (e.g. "6h")
$__from, $__to                  # ms unix
$__from:date, $__to:date        # ISO8601
$__dashboard                    # dashboard title
$__org, $__user                 # org/user id
$__name                         # series name (in overrides)
$__field.name                   # field/series name in data links
$__field.labels.<label>         # a specific label in data links
$__value.raw / .text / .time    # clicked value in data links
$__url_time_range               # current time range as URL params
```

**When to use which time-window variable:**
- `$__rate_interval` — inside `rate()/increase()/irate()`. Safe floor of 4× scrape.
- `$__interval` — for `avg_over_time()` / `max_over_time()` — matches panel resolution.
- `$__range` — for whole-window aggregations (`count_over_time(...[$__range])`).

## 5. Transformations

Applied post-query, client-side. Order matters — each transformation reads the previous one's output.

Core set agents should know:
- **Reduce** — collapse to single value per series (mean/last/first/min/max/sum/count/range/diff/delta).
- **Merge** — fuse multiple query results into one frame on matching rows.
- **Join by field** — inner/outer join two frames on a shared field (SQL-ish).
- **Join by labels** — join time series on specific label values into a wide frame.
- **Organize fields** — rename, reorder, hide columns from one query.
- **Filter fields by name** — drop columns by regex/manual/variable.
- **Filter data by values** — per-row filter (null, equals, regex, range).
- **Filter data by query refId** — drop an entire query.
- **Rename by regex** — regex-rename fields.
- **Add field from calculation** — math on fields (reduce row, binary/unary, cumulative, window, row index).
- **Labels to fields** — turn series labels into columns (useful for table view of PromQL instant vector).
- **Group by** — group rows and aggregate each group.
- **Sort by** — reorder rows.
- **Limit** — cap row count.
- **Prepare time series** — wide / multi / long format conversion.
- **Config from query** — pull thresholds/min/max/unit from one query and apply to another.
- **Row to columns** / **Rows to fields** — pivot rows up to columns.
- **Extract fields** — parse JSON/kv/regex out of one field into many.
- **Convert field type** — numeric/string/time/bool/enum.
- **Time series to table** — emit Trend fields compatible with sparkline.
- **Transpose** — swap rows↔columns.
- **Concatenate fields** — merge all fields across frames into one.
- **Partition by values** — split one frame into N by distinct column value.
- **Trendline** / **Smoothing** — regression fit / ASAP noise reduction.
- **Create heatmap** / **Histogram** / **Grouping to matrix** — shape-changing aggregations.

## 6. Provisioning

Three common shapes:

1. **File provisioning** — `/etc/grafana/provisioning/dashboards/<provider>.yaml` points to a folder of JSON files.
   ```yaml
   apiVersion: 1
   providers:
     - name: 'default'
       folder: 'Infrastructure'
       foldersFromFilesStructure: true
       options: { path: /var/lib/grafana/dashboards }
   ```

2. **ConfigMap + Grafana sidecar** (Kubernetes) — `kube-prometheus-stack` / `grafana` Helm chart deploys a sidecar that watches ConfigMaps with label `grafana_dashboard: "1"` and mounts their JSON into the provisioning dir at runtime.
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: api-red
     labels: { grafana_dashboard: "1" }
   data:
     api-red.json: |-  { "uid": "api-red", ... }
   ```

3. **Grafana Operator CRDs** — `GrafanaDashboard`, `GrafanaDatasource`, `GrafanaFolder`.

When a dashboard is provisioned, `POST /api/dashboards/db` returns an error for manual edits unless `allowUiUpdates: true` is set in the provider YAML.

## 7. Legacy dashboard API (still canonical in 2026 tooling)

### Create / update — `POST /api/dashboards/db`
```json
{
  "dashboard": {
    "id": null,
    "uid": "api-red",
    "title": "API — RED",
    "tags": ["api", "red"],
    "timezone": "browser",
    "schemaVersion": 41,
    "version": 0,
    "panels": [ ... ],
    "templating": { "list": [ ... ] },
    "time": { "from": "now-6h", "to": "now" },
    "refresh": "30s"
  },
  "folderUid": "production",
  "message": "agent: added SLO burn-rate panel",
  "overwrite": false
}
```
- `dashboard.id: null` + `dashboard.uid` unset → create new.
- `dashboard.version` mismatch → HTTP 412 (another writer changed it).
- `overwrite: true` bypasses the version check — use sparingly; it's how provisioned dashboards get clobbered by mistake.
- `folderUid` puts it in a folder (not `folderId`; that was removed in Grafana 11).
- `message` feeds dashboard version history.

### Fetch — `GET /api/dashboards/uid/{uid}`
Returns `{dashboard: {...}, meta: {version, url, folderUid, provisioned, provisionedExternalId, canSave, ...}}`. Always carry `meta.version` back into the next save to avoid clobbers.

### Search — `GET /api/search`
Query params:
- `query=<text>` — full-text
- `tag=<tag>` (repeatable) — tag filter
- `type=dash-db` — dashboards; `dash-folder` — folders
- `folderUIDs=<uid>` (repeatable)
- `starred=true`
- `limit=` (default 1000, max 5000)
- `page=`

### Delete — `DELETE /api/dashboards/uid/{uid}`
Requires Editor on the folder.

### Auth
`Authorization: Bearer <service_account_token>`. Multi-org: `X-Grafana-Org-Id: 3`.

## 8. Kubernetes-style API (Grafana 12+)

```bash
curl -X POST "$GRAFANA/apis/dashboard.grafana.app/v1beta1/namespaces/default/dashboards" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "metadata": { "name": "api-red", "annotations": { "grafana.app/folder": "production" } },
    "spec": {
      "title": "API — RED",
      "schemaVersion": 41,
      "panels": [ ... ]
    }
  }'
```
`resourceVersion` = optimistic concurrency (like k8s). Legacy `schemaVersion` still present inside `spec`.

## 9. Common dashboard bugs + fixes

- **"No data"** — panel datasource `uid` doesn't resolve (templated `$DS_PROMETHEUS` is empty), or `$service` variable empty, or time range has no samples. Fix: hardcode datasource uid while debugging; `format_query` the `expr`; query `/api/v1/query` directly.
- **Legend shows full label sets** — add `legendFormat: "{{route}}"`.
- **Wrong unit** — `bytes` vs `decbytes`, `s` vs `ms`, `percent` (0-100) vs `percentunit` (0-1). Fix `fieldConfig.defaults.unit`.
- **`rate()` too short** — use `$__rate_interval`, not `$__interval`, for counters.
- **Stacked area with gaps** — `connectNullValues: "always"` (timeseries panel) or transformation "Fill null values".
- **Panel repeats on empty variable** — set `Include All: true` or add `repeat_direction: "h"` + proper default.
- **`schemaVersion` mismatch after import** — Grafana auto-migrates; set to current if regenerating.
- **Table sorted on wrong field** — use `Sort by` transformation or `fieldConfig.override` on the column.
- **Stat panel wrong reducer** — set `options.reduceOptions.calcs: ["lastNotNull"]` (not `"mean"`).
- **Heatmap built from `histogram_quantile(...)`** — wrong. Use raw `_bucket` series with `format: "heatmap"`.
- **Threshold color not applied** — check override matcher; defaults don't propagate if an override on `unit` also exists for the same field.
- **All variable picks "All"** — generated regex `(a|b|c)` may hit too much. Constrain with `Custom all value: api-.*`.
- **Provisioned dashboard keeps reverting** — set `allowUiUpdates: true` in provider YAML, OR edit the source and reapply.
- **Multi-value variable used without `=~`** — PromQL needs regex matcher. Write `{route=~"$route"}`, not `{route="$route"}`.

## 10. Dashboards-as-code (brief)

- **Grafonnet** (Jsonnet library) — long-standing, powerful, steep.
- **Foundation SDK** (grafana-foundation-sdk) — official, multi-lang (TS/Go/Python/Java). The 2026 direction.
- **Grizzly** (`grr`) — Jsonnet + git apply/diff workflow.
- **grafanalib** — Python DSL.
- **Kubernetes-native** — `GrafanaDashboard` CR via grafana-operator.

For agents editing one-off dashboards: pull JSON via legacy API, mutate, push back. For repo-scale changes: go through the dashboards-as-code repo.

## 11. Annotations

```bash
curl -X POST "$GRAFANA/api/annotations" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "time": 1713561600000,
    "timeEnd": 1713562200000,
    "tags": ["deploy", "api", "agent-action"],
    "text": "auto-remediation: scaled api deployment from 3→6 after 5xx spike"
  }'
```
`time` in ms. Deployment markers, incidents, agent actions — annotate them. Makes post-hoc incident review tractable.

## 12. Deep-linking

Data links in a panel let you click a point and jump to another dashboard / Loki / Tempo / external URL:
```json
"links": [
  {
    "title": "Logs for ${__field.labels.pod}",
    "url": "/explore?left={\"datasource\":\"loki\",\"queries\":[{\"expr\":\"{pod=\\\"${__field.labels.pod}\\\"}\"}]}",
    "targetBlank": true
  }
]
```
Supported substitutions: `${__field.labels.<label>}`, `${__value.raw}`, `${__value.text}`, `${__value.time}`, `${__url_time_range}`.
