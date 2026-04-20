# PromQL Reference (sourced: prometheus.io/docs/prometheus/latest/querying/)

## Contents
- [1. Data types](#1-data-types)
- [2. Selectors and matchers](#2-selectors-and-matchers)
- [3. Modifiers](#3-modifiers) — offset, `@`, subqueries
- [4. Operators](#4-operators) — arithmetic / comparison / logical / vector matching
- [5. Aggregation](#5-aggregation)
- [6. Functions — critical ones](#6-functions--critical-ones) — rate family, histograms, label manipulation, absent, clamps, time, over_time, smoothing, info, math, sorting
- [7. HTTP API](#7-http-api-prometheus-compat-mimir-same-shape-under-prometheus)
- [8. Common query patterns](#8-common-query-patterns) — RED, SLI, multi-burn-rate, info-metric joins, disk fill
- [9. Pitfalls specific to agents](#9-pitfalls-specific-to-agents)
- [10. Engine limits](#10-engine-limits)

## 1. Data types

Four evaluation types:
- **Instant vector** — one sample per series, all sharing one timestamp.
- **Range vector** — series with a window of samples per series.
- **Scalar** — floating-point number.
- **String** — rarely used; present for completeness.

`query_range` only emits scalars and instant vectors → matrix results. `query` emits all four.

Samples are either **floats** or **native histograms** (counter or gauge flavor). Classic histograms are distinct series with `_bucket`, `_count`, `_sum` suffixes.

## 2. Selectors and matchers

Instant vector: `metric_name{label="value", ...}` returns the most recent sample at or before `t`.

Matcher operators:
- `=` exact
- `!=` inequality
- `=~` regex match (RE2, always fully anchored — `env=~"foo"` becomes `^foo$`)
- `!~` regex non-match

Matching empty labels includes series without that label. Must specify a metric name OR at least one matcher that can't match empty string — `{job=~".*"}` is invalid; `{job=~".+"}` is valid.

Match by `__name__`:
```promql
{__name__="http_requests_total"}
{__name__=~"job:.*"}
```
Forbidden metric names: `bool`, `on`, `ignoring`, `group_left`, `group_right`. Quote via `__name__`.

Range vector: `metric[5m]` — left-open, right-closed.

## 3. Modifiers

### offset
`http_requests_total offset 5m` — 5 min in the past.
`offset -1w` — one week in the future (used for `now vs historical` comparison).
Must immediately follow the selector:
```promql
sum(http_requests_total offset 5m)      # OK
sum(http_requests_total) offset 5m      # INVALID
```

### @ modifier
`metric @ 1609746000` — evaluate at unix ts.
`@ start()` / `@ end()` — range-query start/end (instant query: eval time).
Combine with offset either order.

### Subqueries
`<instant_expr>[range:resolution]` → range vector. Default resolution = global eval interval. Cost and cardinality risk scale with range/resolution.
```promql
max_over_time(deriv(rate(distance_covered_total[5s])[30s:5s])[10m:])
```

## 4. Operators

### Arithmetic
`+ - * / % ^`. Scalar, vector-scalar, vector-vector. Histogram + histogram supports only `+` and `-`.

### Comparison
`== != > < >= <=` filter by default. With `bool` modifier → 0/1.
```promql
http_requests_total > bool 50
```

### Logical / set
- `and` intersection
- `or` union
- `unless` complement

### Vector matching
- `on(...)` — match on listed labels only
- `ignoring(...)` — match on everything except listed labels
- `group_left(...)` / `group_right(...)` — many-to-one / one-to-many
- `fill(v)` / `fill_left(v)` / `fill_right(v)` — experimental, fill gaps

Example (join info metric):
```promql
sum by (version) (
  rate(http_requests_total[5m])
  * on(instance) group_left(version) app_build_info
)
```

### Precedence (highest → lowest)
`^` → `* / % atan2` → `+ -` → `== != <= < >= >` → `and unless` → `or`. `^` right-associative.

## 5. Aggregation

`sum`, `avg`, `min`, `max`, `stddev`, `stdvar`, `count`, `group`, `topk`, `bottomk`, `count_values`, `quantile`, `limitk` (experimental), `limit_ratio` (experimental).

Clauses: `by(labels)` preserves listed; `without(labels)` drops listed.

Two forms:
```promql
sum by (job) (metric)
sum(metric) by (job)
```

`topk`/`bottomk` preserve labels. `count_values("version", build_version)` → count series per unique value, adding a label.

## 6. Functions — critical ones

### Rate family
- `rate(v[range])` — per-second, counter-reset aware. Use for alerts and graphs.
- `irate(v[range])` — last two points. Volatile graphs only; do NOT use in alerts.
- `increase(v[range])` — `rate(v) * range_seconds`. Syntactic sugar.
- `delta(v[range])` — gauges only. Extrapolated first-to-last diff.
- `idelta(v[range])` — last two samples, no extrapolation.
- `deriv(v[range])` — per-second derivative (linear regression on gauges).
- `predict_linear(v[range], seconds)` — linear projection. `predict_linear(node_filesystem_avail_bytes[1h], 4*3600) < 0` = will run out in 4h.

**Rule: `rate()` first, then aggregate.** `sum(rate(x[5m]))` is correct; `rate(sum(x)[5m])` loses counter-reset detection on the sum.

### Counter analysis
- `changes(v[range])` — count of value changes
- `resets(v[range])` — count of decreases (treated as counter resets)

### Histograms
Classic histograms — buckets with `le=` label, plus `_count`, `_sum`:
```promql
histogram_quantile(0.95,
  sum by (le, route) (rate(http_request_duration_seconds_bucket[5m])))
```
- `le="+Inf"` bucket must be present
- Always `rate()` the buckets before `sum`, before `histogram_quantile`
- Aggregate by `le` + the grouping dimensions

Native (sparse) histograms (Prometheus 3.x default):
- `histogram_quantile(0.95, rate(latency[5m]))` works directly
- `histogram_count(v)`, `histogram_sum(v)`, `histogram_avg(v)`
- `histogram_fraction(lo, hi, v)` — fraction of observations in bounds
- `histogram_stddev(v)`, `histogram_stdvar(v)`
- `histogram_quantiles(v, "quantile", 0.5, 0.9, 0.99)` experimental — multiple quantiles in one pass

### Label manipulation
- `label_replace(v, "dst", "replacement_with_$1", "src", "regex")`
- `label_join(v, "dst", "sep", "src1", "src2", ...)`

### Absence
- `absent(v)` — 1 if input empty (deadman's switch)
- `absent_over_time(v[range])` — same, range version

### Clamps
- `clamp(v, min, max)`, `clamp_min(v, min)`, `clamp_max(v, max)`

### Time
- `time()` — evaluation time (NOT wall-clock!)
- `timestamp(v)` — sample ts
- `year`, `month`, `day_of_month`, `day_of_week`, `day_of_year`, `hour`, `minute`, `days_in_month`

### _over_time aggregations (range → instant)
`avg_over_time`, `sum_over_time`, `min_over_time`, `max_over_time`, `count_over_time`, `quantile_over_time`, `stddev_over_time`, `stdvar_over_time`, `first_over_time`, `last_over_time`, `present_over_time`, `mad_over_time` (experimental).

`ts_of_min_over_time` / `ts_of_max_over_time` / `ts_of_first_over_time` / `ts_of_last_over_time` (experimental) return timestamps.

### Smoothing
- `double_exponential_smoothing(v, smoothing_factor, trend_factor)` — Holt-Linear. Replaces `holt_winters` (renamed). Requires `--enable-feature=promql-experimental-functions`.

### info() join (experimental)
```promql
info(rate(http_requests_total[5m]), {"version"})
```
Sugar for `group_left(version) target_info`. Limited to `instance`/`job` labels. Requires feature flag.

### Math
`abs`, `ceil`, `floor`, `round(v, to_nearest)`, `sqrt`, `exp`, `ln`, `log2`, `log10`, `sgn`, `deg`, `rad`, `pi`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`.

### Sorting
`sort(v)`, `sort_desc(v)`. `sort_by_label(v, l1, l2)`, `sort_by_label_desc` (experimental, natural sort).

## 7. HTTP API (Prometheus-compat; Mimir same shape under `/prometheus`)

All responses wrap:
```json
{
  "status": "success" | "error",
  "data": <...>,
  "errorType": "...", "error": "...",
  "warnings": [...], "infos": [...]
}
```

### /api/v1/query (instant)
Params: `query`, `time` (RFC3339 or unix), `timeout`, `limit` (cap result cardinality; Prom 3+), `lookback_delta`, `stats=all`.
Result shape: `{resultType: "matrix"|"vector"|"scalar"|"string", result: ...}`.

### /api/v1/query_range (range)
Params: `query`, `start`, `end`, `step` (duration or seconds float), plus above.
Points ≈ `(end - start) / step`, capped ~11000.

### /api/v1/series (series enumeration)
Params: `match[]` (required, repeatable), `start`, `end`, `limit`.
Returns array of label sets.

### /api/v1/labels
Params: `start`, `end`, `match[]`, `limit`.
Returns array of label names (strings).

### /api/v1/label/<name>/values
Params: `start`, `end`, `match[]`, `limit`.
Returns array of values.

### /api/v1/metadata
Params: `metric`, `limit`, `limit_per_metric`.
Returns `{metric: [{type, help, unit}]}`.

### /api/v1/format_query, /api/v1/parse_query
Lint/canonicalize before expensive queries; parse_query returns AST JSON.

### /api/v1/query_exemplars
Params: `query`, `start`, `end`. Returns trace-ID exemplars per series.

### /api/v1/targets, /api/v1/scrape_pools, /api/v1/targets/metadata
Scrape state.

### /api/v1/rules, /api/v1/alerts
Rule groups with active alerts; array of active alerts.

### /api/v1/status/*
- `config` — loaded YAML
- `flags` — flag values
- `runtimeinfo` — uptime, series count, etc.
- `buildinfo` — version, revision, goVersion
- `tsdb` — top label/metric cardinality (paginate via `limit`)
- `tsdb/blocks` — block list (experimental)
- `walreplay` — replay progress

### Admin (`--web.enable-admin-api`)
`snapshot`, `delete_series`, `clean_tombstones`.

### HTTP status codes
- `2xx` success
- `400` bad params
- `422` expression valid but not executable (max samples, query too long)
- `503` timeout/aborted

## 8. Common query patterns

### RED service metrics
```promql
# Rate
sum by (route) (rate(http_requests_total[5m]))

# Error ratio
sum by (route) (rate(http_requests_total{status=~"5.."}[5m]))
 / sum by (route) (rate(http_requests_total[5m]))

# p99 latency
histogram_quantile(0.99,
  sum by (route, le) (rate(http_request_duration_seconds_bucket[5m])))
```

### SLI — "good events / valid events"
```promql
sum(rate(http_request_duration_seconds_bucket{le="0.5",status!~"5.."}[5m]))
 / sum(rate(http_request_duration_seconds_count[5m]))
```

### Multi-window multi-burn-rate (30-day SLO, 99.9% target)
```promql
(
  sum(rate(http_requests_total{status=~"5.."}[1h]))
  / sum(rate(http_requests_total[1h]))
) > (14.4 * (1 - 0.999))
and
(
  sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))
) > (14.4 * (1 - 0.999))
```

### Info-metric join for deployment correlation
```promql
sum by (version) (
  rate(http_requests_total{status=~"5.."}[5m])
  * on(instance) group_left(version) app_build_info
)
```

### Disk fill prediction
```promql
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[1h], 4*3600) < 0
```

### CPU utilization
```promql
1 - avg by (instance)(rate(node_cpu_seconds_total{mode="idle"}[5m]))
```

### CPU throttle ratio
```promql
rate(container_cpu_cfs_throttled_periods_total[5m])
 / rate(container_cpu_cfs_periods_total[5m])
```

### Deadman's switch
```promql
absent(up{job="api"})
```

## 9. Pitfalls specific to agents

1. **Aggregating over counter resets.** Always `rate()` before `sum()`.
2. **Mean latency.** `rate(_sum)/rate(_count)` is meaningless on skewed distributions. Use `histogram_quantile`.
3. **`irate` in alerts.** Non-deterministic within a window. Use `rate`.
4. **`topk` in range queries.** Non-deterministic per step. Works fine for instant queries.
5. **Rate over tiny ranges.** `rate(x[1m])` with 15s scrape = 4 samples; single missed scrape poisons the result. `[5m]` is the safe floor; Grafana's `$__rate_interval` resolves to 4× scrape interval.
6. **`up == 1` ≠ "service healthy".** Says scraping worked. App could 500 on every request.
7. **High-cardinality labels** (user_id, request_id, path) explode TSDB. Keep those in logs/traces.
8. **Staleness marker.** Default `--query.lookback-delta=5m`. Series absent >5m drops from results.
9. **Counter resets on pod restart** already handled by `rate`; don't second-guess.
10. **Instant queries with `@ end()`** for "value at window end" — useful for alerts.

## 10. Engine limits

- `--query.max-samples` (default 50M)
- `--query.timeout` (default 2 min)
- `--query.lookback-delta=5m`
- `query.max-concurrency`
- Mimir adds per-tenant limits (`max_query_length`, `max_query_lookback`, `max_samples_per_query`, `max_fetched_series_per_query`, `max_query_parallelism`).

HTTP 422 from Mimir usually means one of these was exceeded — the remedy is a smaller window, tighter matchers, or a higher `step`, not a retry.
