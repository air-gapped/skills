# Backend notes

What the backend does with OTLP decides how collector data looks there.
Checked 2026-11 against VictoriaMetrics v1.156, VictoriaLogs v1.54,
VictoriaTraces v0.13, contrib v0.165.1.

## VictoriaLogs

- Endpoint `/insert/opentelemetry/v1/logs`, **OTLP/HTTP protobuf only** —
  JSON is rejected ("json encoding isn't supported"); gRPC is not documented. Use
  `otlp_http` with `logs_endpoint`.
- **Every OTLP resource attribute becomes a stream field** unless
  `VL-Stream-Fields` is set. Set it on the exporter, e.g.
  `VL-Stream-Fields: k8s.namespace.name,k8s.pod.name,k8s.container.name`;
  otherwise per-pod/per-process resource attributes (`k8s.pod.uid`,
  `process.pid`) explode the stream count.
- Message field: `VL-Msg-Field` takes a **comma-separated list; the first
  non-empty field wins**. Records with no message get the placeholder text
  `missing _msg field; see …`. Where the OTLP body goes changed in v1.54.0,
  and the right header depends on the version — **check it before upgrading
  VictoriaLogs**:

  | VictoriaLogs | Body stored as | Pod logs + Kubernetes events (`object.note`) | Attribute over a non-empty body |
  |---|---|---|---|
  | < v1.54.0 | `_msg` | `VL-Msg-Field: _msg,object.note` | not possible: `VL-Msg-Field: message` gives two `_msg` fields and either may win; move the text into the body (`transform`) |
  | ≥ v1.54.0 | `body` (`_msg` only via the header, default `body`) | `VL-Msg-Field: body,object.note` | `VL-Msg-Field: message,body` |

  A `_msg,object.note` header kept across the upgrade to v1.54 leaves every
  pod log without a message: `_msg` no longer exists at ingest.
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
  `-otlpGRPCListenAddr=:4317`, plaintext from v0.13 unless `-otlpGRPC.tls` is
  set (the `otlp_grpc` exporter then needs `tls.insecure: true`). Jaeger query API; 7-day default retention.

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
