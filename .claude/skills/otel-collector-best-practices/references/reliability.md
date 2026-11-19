# Reliability: queues, batching, memory, tiers, self-monitoring

Checked against core v0.160.0–v0.162.0 (exporterhelper, memory_limiter,
batch READMEs) and opentelemetry.io docs (resiliency, scaling, internal
telemetry), 2026-10.

## Contents
- Exporter queue and retry
- Sizing the queue in bytes (worked example)
- Persistence: file_storage
- What receivers do when the queue is full
- Batching: processor vs exporter-side
- Memory
- Deployment tiers and scaling
- Self-monitoring and alerts

## Exporter queue and retry

Every exporter built on exporterhelper (`otlp_grpc`, `otlp_http`,
`prometheus_remote_write`, `clickhouse`, …) has a `sending_queue` and
`retry_on_failure`.

| Setting | Default | Meaning |
|---|---|---|
| `sending_queue.enabled` | true | |
| `queue_size` | 1000 | in units of `sizer` |
| `sizer` | `requests` | batches; `items` = log records/spans/points; `bytes` = serialized size (slowest, most predictable) |
| `num_consumers` | 10 | parallel senders |
| `block_on_overflow` | false | false: reject new data when full (`ErrQueueIsFull`, counted in `otelcol_exporter_enqueue_failed_*`); true: block the caller |
| `wait_for_result` | false | **not allowed together with `storage`** (config validation fails) |
| `storage` | none | name of a storage extension → persistent queue, no in-memory queue |
| `retry_on_failure.initial_interval` / `max_interval` / `multiplier` | 5s / 30s / 1.5 | backoff |
| `retry_on_failure.max_elapsed_time` | 300s | give up after 5 min; `0` = retry forever |
| per-attempt `timeout` | 5s | |

Data that cannot be enqueued never reaches retry. With the defaults, a backend
outage longer than the queue lasts loses data, and so does an outage longer
than 5 minutes for any single batch.

## Sizing the queue in bytes (worked example)

A "request" is one batch. Batches close at 8192 records or after 200 ms
(batch processor defaults; exporter-side batching uses the same
`min_size`/`flush_timeout`). So:

- a quiet node (~12 log lines/s) sends ~5 batches/s of 2–3 lines: 1000
  requests ≈ **3 minutes** of backend downtime;
- a burst fills 8192-line batches: 1000 requests ≈ 8 million lines.

Because "1000" swings by three orders of magnitude, size by bytes:

1. measure records/hour on the busiest node and the average serialized record
   size (message + attributes; ~1 KB for Kubernetes pod logs with
   `k8s_attributes`);
2. `queue_size` bytes ≥ bytes/hour × hours of backend downtime to survive;
3. check it against free disk on the node.

Example: 44k records/h × ~1 KB ≈ 45–65 MB/h → 1 GiB covers ~16–24 h.

```yaml
exporters:
  otlp_http/backend:
    sending_queue:
      enabled: true
      storage: file_storage
      sizer: bytes
      queue_size: 1073741824   # 1 GiB
      block_on_overflow: true  # pause the receiver instead of dropping
    retry_on_failure:
      enabled: true
      max_elapsed_time: 0      # never give up
extensions:
  file_storage:
    directory: /var/lib/otelcol
    compaction:
      on_start: true
      on_rebound: true          # give space back after a backlog drains
      directory: /var/lib/otelcol
```

## Persistence: file_storage

- Default directory `/var/lib/otelcol/file_storage`; it must exist unless
  `create_directory: true`. On Kubernetes use a hostPath so the queue survives
  pod restarts.
- `compaction.on_start` and `on_rebound` are **off** by default: after a long
  backlog the bbolt file keeps its peak size. Rebound thresholds:
  `rebound_needed_threshold_mib` 100, `rebound_trigger_threshold_mib` 10,
  `check_interval` 5s.
- `fsync` off by default (faster; less safe on power loss).
- `max_size` caps the file; writes beyond it fail with storage-full → data
  dropped.
- Auth-extension context is not persisted through the queue.
- The same extension stores `file_log` offsets and `k8s_objects`
  resourceVersions.

## What receivers do when the queue is full

- `otlp` receiver: returns retryable errors (gRPC `Unavailable` /
  `ResourceExhausted`, HTTP 503/429); the SDK or upstream collector retries.
- `file_log`: its own `retry_on_failure.enabled` defaults to **false**. With
  `block_on_overflow: true` on the exporter the pipeline blocks, so the
  receiver stops reading and resumes from its checkpoint; the log files on
  disk become the buffer — until kubelet/logrotate deletes them (kubelet keeps
  ~5 × 10 MiB per container by default).
- Queues on the app → local-agent hop can back-pressure the application;
  docs recommend resilience on the agent → gateway and gateway → backend hops.

## Batching: processor vs exporter-side

- The `batch` processor (beta) is **not deprecated**: defaults
  `send_batch_size` 8192, `timeout` 200ms.
- Upstream now steers new configs to exporter-side batching:
  `sending_queue.batch: {}` (off by default; `flush_timeout` 200ms,
  `min_size` 8192, `sizer` items/bytes, `partition.metadata_keys`). Several
  contrib exporters dropped their own `batcher` field for it.
- Use one or the other, **never both** on a pipeline (double batching).
- `queue_batch` (renamed from `queuebatch` in v0.162) can deadlock on
  partition eviction with `num_consumers: 1` and `metadata_keys` set (open
  core issue #16076).
- Batch after `memory_limiter` and after sampling/filtering — batching should
  happen after any drops.

## Memory

- `memory_limiter` first in every pipeline. Above the soft limit
  (`limit_mib − spike_limit_mib`) it refuses data with retryable errors;
  above the hard limit it also forces GC. Data is lost if the component
  before it cannot retry.
- In containers use `limit_percentage` (e.g. 80) and `spike_limit_percentage`
  (e.g. 20–25), `check_interval: 1s`. RSS runs ~50 MiB above `limit_mib`.
- Set `GOMEMLIMIT` to ~80 % of the container memory limit (Helm chart:
  `useGOMEMLIMIT: true`). The alpha `cgroup_runtime` extension sets it from
  cgroups with a 0.9 default ratio — that conflicts with the 80 % advice;
  choose one.
- A `memory_limiter` *extension* (beta, usable as HTTP/gRPC middleware)
  exists and may eventually replace the processor.
- No official CPU/memory-per-throughput table exists; measure.

## Deployment tiers and scaling

- **Agent** (DaemonSet / host service): local collection, small config.
  **Gateway** (Deployment): central processing, sampling, egress. The
  combination is the documented pattern.
- Stateless components scale behind a load balancer; for OTLP/gRPC use an L7
  (gRPC-aware) balancer — L4 pins each client to one collector.
- Scrapers: shard targets or use the Target Allocator; the same scrape config
  on N replicas gives duplicates.
- Stateful components (`tail_sampling`, `span_metrics`, `service_graph`)
  need all related data on one instance: put a `load_balancing` exporter tier
  in front (routing key `traceID` for traces, `service` for span metrics).
  Resolvers: static, dns (lower `interval` in elastic environments), k8s
  (needs EndpointSlice RBAC), aws_cloud_map.
- Kafka between tiers is the documented maximum-durability option.
- Keep ≥ 3 gateway replicas; more queue consumers do not help a saturated
  backend.

## Self-monitoring and alerts

- Exposed by default as Prometheus on `:8888`. Configure with
  `service.telemetry.metrics.readers` (`- pull: exporter: prometheus: {host, port}`
  or `- periodic: exporter: otlp: …`). `service.telemetry.metrics.address` has
  been ignored since v0.123 and the Helm chart removed it in 0.161.
- Levels: `none`, `basic`, `normal` (default), `detailed`.
- Internal metrics lost the `service_name`/`service_instance_id`/`service_version`
  labels in v0.149 (use `target_info`); `memory_limiter` metrics are
  `otelcol_processor_memory_limiter_*` since v0.155.

| Alert on | Meaning |
|---|---|
| `otelcol_exporter_queue_size / otelcol_exporter_queue_capacity` > 0.6–0.7 sustained | backend slow or down; queue filling |
| `otelcol_exporter_enqueue_failed_*` > 0 | **data dropped** — queue full |
| `otelcol_receiver_refused_*` sustained | clients may be losing data |
| `otelcol_exporter_send_failed_*` sustained | backend rejecting; not loss by itself (retries) |
| log line `Dropping data because sending_queue is full` | data dropped |
| `otelcol_processor_refused_*` | memory pressure — scale |
| `receiver_accepted_*` vs `exporter_sent_*` diverging | data lost or filtered in between |
| `rate(otelcol_exporter_sent_*[10m]) == 0` sustained | pipeline stuck or collector broken |
| collector pods ready < desired | a node has no collector |

**With `block_on_overflow: true`, `enqueue_failed_*` never fires** — the
queue blocks instead of rejecting, and loss happens upstream (a `file_log`
receiver stops reading until the source files rotate away). Alert on queue
fill ratio and on `send_failed_*` instead, early enough that the queue's
byte budget outlasts the response time. Failure counters only appear after
the first failure, so write expressions that tolerate absent series.
The collector's own logs are usually excluded from its log pipeline (to
avoid loops), so its "Dropping data…" lines are visible only in
`kubectl logs` — metrics are the alerting path.

- Extensions: `health_check` (required by the Helm chart's probes; default
  `localhost:13133`), `pprof` (`localhost:1777`), `zpages`
  (`localhost:55679`). Treat pprof and zpages as debug-only.
