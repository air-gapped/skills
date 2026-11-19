# Backend notes

What the backend does with OTLP decides how collector data looks there.
Checked 2026-10 against VictoriaMetrics v1.153, VictoriaLogs v1.53,
VictoriaTraces v0.12, contrib v0.162.0.

## VictoriaLogs

- Endpoint `/insert/opentelemetry/v1/logs`, **OTLP/HTTP protobuf only** —
  JSON is rejected ("json encoding isn't supported"); gRPC is not documented. Use
  `otlp_http` with `logs_endpoint`.
- **Every OTLP resource attribute becomes a stream field** unless
  `VL-Stream-Fields` is set. Set it on the exporter, e.g.
  `VL-Stream-Fields: k8s.namespace.name,k8s.pod.name,k8s.container.name`;
  otherwise per-pod/per-process resource attributes (`k8s.pod.uid`,
  `process.pid`) explode the stream count.
- Message field: the OTLP body becomes `_msg`. Records with no body get
  VictoriaLogs' placeholder text `missing _msg field; see …`.
  `VL-Msg-Field` takes a **comma-separated list; the first non-empty field
  wins** — `VL-Msg-Field: _msg,object.note` keeps pod-log bodies and gives
  Kubernetes events (whose text is `object.note`) a message.
- **List `_msg` first in `VL-Msg-Field`.** The rename does not remove the
  body: with `VL-Msg-Field: message` and a non-empty body, the record holds
  two `_msg` fields, and VictoriaLogs showed the raw body on 2 of 10 records
  (v1.52, `syslog` receiver). To promote an attribute over a non-empty body,
  move it into the body in the collector (`transform`) instead.
- `VL-Ignore-Fields` drops noisy fields (e.g. `log.file.path`).
- Multi-tenancy by `AccountID`/`ProjectID` headers; default tenant `0:0`.
  Queries without the headers see only `0:0`.
- Delete API (`/delete/run_task`) is disabled unless VictoriaLogs runs with
  `-delete.enable` — test data written to a real tenant stays until retention
  removes it.
- Queries: `_time` is UTC; a LogsQL word search does not match a substring of
  a long unbroken token — filter by stream fields instead.

## VictoriaMetrics

- OTLP: `/opentelemetry/v1/metrics`, HTTP protobuf only (no gRPC; issue
  #10345). Names stored as-is unless `-opentelemetry.usePrometheusNaming`.
- Remote write: `/api/v1/write`; no Remote Write 2.0. Native histograms are
  converted to classic `vmrange` buckets at ingest; out-of-order samples are
  accepted within retention (Mimir rejects them).
- Single-node has no tenancy (`X-Scope-OrgID` only via vmauth/cluster).

## VictoriaTraces

- `/insert/opentelemetry/v1/traces` on :10428 (HTTP); OTLP gRPC only with
  `-otlpGRPCListenAddr=:4317`. Jaeger query API; 7-day default retention.

## Grafana Mimir (remote write / OTLP)

- Requires `X-Scope-OrgID` on every push (set `headers` on the exporter).
- Rejects out-of-order samples unless `out_of_order_time_window` is set.
- Stores native histograms natively — a VictoriaMetrics lab does not
  reproduce Mimir's histogram or out-of-order behaviour.

## ClickHouse (`clickhouse` exporter)

Beta for traces/logs, alpha for metrics. Things an OTLP-to-something-else
test environment cannot exercise:

- native TCP (9000), TLS, ClickHouse auth;
- DDL: `create_schema` (default true — the README recommends managing the
  schema yourself in production), `cluster_name`/`ON CLUSTER`,
  `table_engine`, `ttl`, partitioning;
- per-type metric tables, optional JSON column type;
- `async_insert`, `sending_queue.batch` + `storage`.

## Loki

- The `loki` exporter was removed in v0.131. Send `otlp_http` to Loki's
  native OTLP endpoint.

## Elasticsearch

- `elasticsearch` exporter beta for traces/logs; exporters are moving their
  batching into `sending_queue.batch` (the exporter's own `batcher` was
  removed or deprecated).
