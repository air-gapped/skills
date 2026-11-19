# Processing: OTTL, logs, metrics, traces, sensitive data

Checked against contrib v0.162.0 component READMEs and pkg/ottl docs,
2026-10.

## Contents
- OTTL: transform and filter
- Logs
- Metrics and Prometheus
- Traces and sampling
- Sensitive data
- Resource detection
- Semantic-convention changes that rename attributes

## OTTL: transform and filter

- Contexts: resource, scope, span, spanevent, metric, datapoint, exemplar,
  log, profile (development), profilesample, otelcol.
- Shape: `log_statements:` / `trace_statements:` / `metric_statements:` is a
  list of plain statements or of groups with `context`, `error_mode`,
  `conditions` (ORed), `statements`, `shared_cache`. Paths carry the context
  prefix: `log.attributes["x"]`, `resource.attributes["y"]`.
- The context is inferred from the paths. A group that mixes incompatible
  levels (e.g. `convert_sum_to_gauge()` with `datapoint.*` paths) fails to
  parse — split it.
- **`error_mode` defaults to `ignore`** (transform, filter, routing connector
  since v0.157; feature gates removed in v0.159/v0.162). A statement that
  errors is logged and skipped; the data passes through *unmodified*. After
  any OTTL change, read the collector log. `propagate` drops the payload on
  error; `silent` hides the log line.
- A missing map key evaluates to `nil` — guard with `where … != nil`. `set`
  now writes `nil` through instead of doing nothing (stable v0.162).
- Useful log functions: `ParseJSON`, `merge_maps(target, src, "upsert")`,
  `flatten`, `ParseSeverity`, `ParseKeyValue`, `ParseCSV`,
  `ExtractGrokPatterns`; transform also has `ParseCEF`, `ParseCLF`,
  `ParseELF`, `ParseLEEF`. JSON body pattern:
  `merge_maps(log.cache, ParseJSON(log.body), "upsert") where IsMatch(log.body, "^\\{")`.
- Performance: transform is stateless and scales horizontally; use `where`
  and `conditions`; `flatten_data` copies resource and scope per record and is
  costly.
- `filter` (alpha): conditions are ORed; a match **drops**. A `metric.*`
  condition drops the whole metric; a `datapoint.*` condition drops matching
  points (the metric goes when none remain). Dropping all span events keeps
  the span.

## Logs

- Severity: the stanza `severity` parser maps to the 24 OTLP levels; in OTTL
  use `ParseSeverity` or `set(log.severity_number, SEVERITY_NUMBER_WARN)`.
- Multiline: `file_log.multiline` with exactly one of `line_start_pattern` /
  `line_end_pattern`; or the `recombine` operator (exactly one of
  `is_first_entry` / `is_last_entry`; `max_log_size` defaults to unlimited —
  set a cap to bound memory).
- `journald` receiver (alpha): needs the `journalctl` binary and journal read
  access (root, or `DAC_READ_SEARCH` in a container).
  - `priority` defaults to `info` → **debug lines are dropped**; set
    `priority: debug` to match a full shipper such as
    systemd-journal-upload.
  - Without `convert_to_semantic_conventions: true` (new in v0.162), the
    whole journal record is a body map: MESSAGE is not the message and
    PRIORITY is not severity, so backends show no message and "Unspecified"
    severity. With it: MESSAGE → body, PRIORITY → severity,
    `_HOSTNAME` → `host.name`, `_PID` → `process.pid`, `_EXE` →
    `process.executable.path`, CODE_* → `code.*`, the rest → `journald.*`.
  - With semantic conventions on, `process.pid` is a **resource** attribute —
    backends that index resource attributes (e.g. VictoriaLogs streams) get
    one stream per process; restrict stream fields.
  - Field names then differ from a native journal shipper
    (`journald._SYSTEMD_UNIT` vs `_SYSTEMD_UNIT`), so queries do not carry
    over between the two paths.
  - `storage` persists the journal cursor; `start_at: end` default.
- Dedup: `log_dedup` (alpha), `interval` 10s, adds `log_count` and first/last
  timestamps.
- Logs with an empty body (some programs print blank lines, e.g. Ceph
  daemons) arrive with no message; drop them with `filter`
  (e.g. `log.body == ""`, untested) if unwanted.

## Metrics and Prometheus

- `prometheus` receiver: keeps Prometheus names, strips
  `_total`/`_count`/`_sum`/`_bucket` into type info, turns `target_info` into
  resource attributes, no longer adjusts start time (v0.140), drops malformed
  classic histograms (v0.162). Native histograms become exponential only with
  `scrape_native_histograms: true` and `PrometheusProto` in
  `scrape_protocols`.
- Exporters `prometheus` / `prometheus_remote_write`: `translation_strategy`
  (`UnderscoreEscapingWithSuffixes` default for remote write,
  `UnderscoreEscapingWithoutSuffixes`, `NoUTF8EscapingWithSuffixes`,
  `NoTranslation`) replaces the deprecated `add_metric_suffixes`; the
  `prometheus` exporter ignores `add_metric_suffixes` since v0.154.
  `resource_to_telemetry_conversion` is deprecated (v0.160) for
  `resource_constant_labels`. `PermissiveLabelSanitization` is on by default
  since v0.162 (opt out: `--feature-gates=-pkg.translator.prometheus.PermissiveLabelSanitization`).
  The remote-write exporter/receiver need Prometheus ≥ 3.8.0 (RW 2.0 rc.4).
- Naming: unit `By` → `_bytes`, `{packets}` dropped, gauge with unit `1` →
  `_ratio`, monotonic sums get `_total`.
- `host_metrics` / `k8s_cluster` are **not drop-in replacements** for
  node_exporter / kube-state-metrics: different names and labels
  (`system_cpu_time_seconds_total` vs `node_cpu_seconds_total{mode}`,
  `k8s.pod.phase` gauge vs `kube_pod_status_phase`). Existing dashboards and
  alerts do not carry over. v0.157 also removed the `cpu` attribute from
  `system.cpu.time` by default.
- Scraping Prometheus targets with the collector instead of Prometheus: no
  storage, no rule evaluation, `ServiceMonitor` discovery needs the operator's
  Target Allocator.
- Temporality: `delta_to_cumulative` (alpha, stateful, `max_stale` 5m) for
  Prometheus-style backends; `cumulative_to_delta` (beta, `max_staleness`
  defaults to 1h since v0.142) for delta backends.
- Cardinality: `filter`, transform `aggregate_on_attributes`,
  `span_metrics` `aggregation_cardinality_limit` / `exclude_dimensions`.

## Traces and sampling

- `tail_sampling` (beta, stateful): `decision_wait` 30s, `num_traces` 50000,
  `num_shards` 1; set `decision_cache` well above `num_traces`. Traces evicted
  before the decision are dropped. Place after `k8s_attributes`. Multi-replica
  needs a `load_balancing` exporter tier (traceID) in front.
- `probabilistic_sampler` when not tail sampling; inside tail sampling use the
  probabilistic policy.
- `span_metrics` (alpha): default unit is still ms (gate to switch to s);
  route by `service` through the load balancer.
- `service_graph` (alpha): both sides of an edge must reach one instance.

## Sensitive data

- `redaction` (beta traces, alpha logs/metrics) fails closed: empty
  `allowed_keys` removes all attributes — set `allow_all_keys: true` plus
  `blocked_key_patterns`/`blocked_values` to redact selectively. Prefer
  `hmac-sha256`/`hmac-sha512` (with `hmac_key`) over plain hashes for
  low-entropy values.
- `attributes` `action: hash` uses SHA1; transform has `replace_pattern`,
  `delete_key`, `truncate_all` and SHA256/Murmur3 converters.
- Official guidance: collect only what you need; hashing small input spaces
  is reversible; truncate where possible.

## Resource detection

- `resource_detection` (beta): a failing detector stops startup; the first
  detector to set an attribute wins (order matters); `k8snode` → `k8s_api`.
- `system` detector `hostname_sources` default is dns.

## Semantic-convention changes that rename attributes

| Component | Since | Change |
|---|---|---|
| `k8s_attributes` | v0.161 | `k8s.*.labels.<k>` → `k8s.*.label.<k>`, `annotations` → `annotation`, `container.image.tag` → `container.image.tags` (gates on by default) |
| `host_metrics` | v0.157 / v0.160 | `cpu` attribute off by default on `system.cpu.time`/`utilization`; v1 system-conventions gates (alpha) |
| `kubelet_stats` | v0.161 / v0.162 | `cpuUsageScrapeBased` on by default; `*.node.utilization` deprecated |
| collector internal metrics | v0.148 / v0.149 | singular units (`{request}`); `service_*` labels removed |

Check dashboards and saved queries on every upgrade that crosses these.
