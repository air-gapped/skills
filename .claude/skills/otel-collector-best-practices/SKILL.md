---
name: otel-collector-best-practices
description: >-
  Current (2026) practice for the OpenTelemetry Collector: writing, reviewing,
  upgrading and debugging collector configs and deployments — component names
  after the snake_case renames, pipeline order, exporter queues and batching,
  data-loss and duplicate traps, Kubernetes (Helm chart presets, operator,
  k8s_attributes, file_log, events), OTTL transform/filter, logs/metrics/traces
  specifics, self-monitoring, security advisories and supply chain. Use it
  whenever the task touches an otelcol config, an opentelemetry-collector Helm
  values file, an OpenTelemetryCollector CR, or asks things like "ship logs
  with OTel", "replace fluentd/Fluent Bit with the collector", "collector
  drops data", "events duplicated", "upgrade the collector", "otelcol validate
  fails", "sending_queue", "tail sampling" — even without the words "best
  practices". Prefer it over memory: the collector ships every two weeks.
---

# OpenTelemetry Collector — current practice

The collector releases every two weeks with no LTS, and in 2026 it renamed
~70 components and changed several defaults. A config that looks right from
memory is often written for a collector that no longer exists. This skill
carries what changed, the defaults that silently lose or duplicate data, and
a working order for writing and verifying a config.

Facts here were checked against collector v0.165.0 (contrib v0.165.1,
2026-11-09) and Helm chart 0.180.0 (2026-11-18). For anything version-bound, check the installed
version first and the release notes of every hop since; see
`references/sources.md` for where each fact came from.

## Workflow: writing or changing a collector config

Work through these in order. Each step names the trap it prevents.

1. **Pin the version and distribution.** Read the image tag or
   `otelcol --version`. Pick the distribution deliberately: `otelcol-k8s`
   is the default for Kubernetes but lacks `prometheus_remote_write`,
   `kafka` and `syslog` exporters; `otelcol-contrib` has ~250 components;
   a custom `ocb` build is the production recommendation. Confirm every
   component you use is in it (`otelcol components`), or the collector
   refuses to start.
2. **Use the component names of that version.** Since v0.144–v0.162 the
   canonical names are snake_case (`file_log`, `otlp_http`, `otlp_grpc`,
   `k8s_attributes`, `k8s_objects`, `host_metrics`, `kubelet_stats`,
   `resource_detection`, `load_balancing`, `span_metrics`…). Old names still
   work as deprecated aliases and log a warning; on an older collector the new
   names fail. Table: `references/components.md`.
3. **Bind receivers explicitly.** Server components default to `localhost`
   since v0.110.0 (v0.104 only added the opt-in gate — models often say
   v0.104). In a container, bind to the pod IP
   (`${env:MY_POD_IP}:4317`), or nothing outside the pod can reach it.
4. **Order processors:** `memory_limiter` first, then enrichment
   (`k8s_attributes` before anything that batches or samples), then
   filtering/sampling, then batching last. Batch either with the `batch`
   processor or with exporter-side `sending_queue.batch` — not both.
5. **Size the exporter queue in bytes and decide what happens when it is
   full.** Defaults: `queue_size: 1000` counted in *requests* (batches),
   `block_on_overflow: false` — when full, new data is **dropped**. A batch
   is 1 to 8192 records, so "1000" means seconds to hours. For durable
   pipelines: `storage: file_storage`, `sizer: bytes`, a byte
   `queue_size`, `block_on_overflow: true`, `retry_on_failure.max_elapsed_time: 0`,
   and `file_storage` compaction. Details and the arithmetic:
   `references/reliability.md`.
6. **Run each cluster-wide receiver exactly once.** `k8s_cluster`,
   `k8s_objects`/`k8sobjects` and `k8s_events` duplicate data per replica
   unless a `k8s_leader_elector` extension is configured. Per-node receivers
   (`file_log`, `host_metrics`, `kubelet_stats`) belong in a DaemonSet.
7. **Expose self-monitoring** (`service.telemetry.metrics.readers`, port
   8888) and alert on queue size near capacity, `otelcol_exporter_send_failed_*`,
   `otelcol_receiver_refused_*`, sent rate dropping to zero, and
   `otelcol_exporter_enqueue_failed_*` — the last one never fires when
   `block_on_overflow: true`, so it cannot be the only alert.
8. **Validate in the real binary.** `otelcol validate --config=…` with the
   same image tag you will deploy, and with the env vars the config expands
   (`MY_POD_IP`, `K8S_NODE_NAME`…) set. Unknown keys, wrong names and
   missing components fail here, not in production.
9. **Verify the data after deploy**, not just pod health: compare per-minute
   row counts against the pipeline it replaces, send one oversized line
   (> 16 KiB, > 32 KiB) and check it arrives whole, read the receiver's
   startup log for the command or settings it actually used.

## Traps that lose or duplicate data silently

| Trap | What happens | Fix |
|---|---|---|
| Exporter `sending_queue` defaults | 1000 *batches*, drop when full: minutes of backend downtime loses data | `sizer: bytes`, byte `queue_size`, `block_on_overflow: true`, persistent storage |
| `transform` / `filter` / `routing` `error_mode` | default is `ignore` (since v0.157): a failing statement is skipped and logged, data passes **unchanged** | check collector logs after any OTTL change; use `propagate` only to drop on error deliberately |
| journald receiver `priority` | defaults to `info`: debug entries never leave the host | `priority: debug` if you need them |
| journald receiver fields | without `convert_to_semantic_conventions: true` (v0.162+) MESSAGE is not the body and PRIORITY is not severity | set it; then check stream/label cardinality (it creates `process.pid` as a resource attribute) |
| Helm `kubernetesEvents` preset in DaemonSet mode | renders **no receiver**: no events at all | Deployment with `replicaCount: 1`, or `kubernetesObjects` events in DaemonSet mode (gets leader election) |
| Helm `kubernetesObjects` in a Deployment with replicas > 1 | no leader elector: every replica sends every object | `mode: daemonset` or one replica |
| Events across a rollout | the new leader starts its watch after taking the Lease; events in the handover seconds are lost (observed) | accept it, or try `storage` on `k8s_objects` (RWX volume with leader election): the README documents it against duplicates on restart; that it also closes the handover gap is untested |
| `file_log` without `storage` | offsets in memory: a restart re-reads or skips (`start_at: end` default) | `storage: file_storage` on a hostPath |
| Same Prometheus scrape config on several replicas | duplicate/out-of-order samples | shard, or Target Allocator |
| Tail sampling / span metrics / service graph behind a plain load balancer | partial traces, wrong aggregates | `load_balancing` exporter tier (traceID / service key) in front |
| `k8s_attributes` after `batch` | `connection` pod association fails | `k8s_attributes` before batching |
| `syslog` receiver body | the body keeps the raw line with the syslog header; the text is in `attributes.message` | `transform`: `set(log.body, log.attributes["message"])`, then delete the attribute (`references/processing.md`) |
| Removing a Helm chart default by deleting the key | the chart default stays | set the key to `null` |
| A component before `memory_limiter` that cannot retry | its data is lost when the limiter refuses | `memory_limiter` first |

## Where to look next

| Task | Read |
|---|---|
| Component names, renames, removed components, stability levels, distributions | `references/components.md` |
| Queues, retry, persistence, batching, memory, deployment tiers, self-monitoring and alerts | `references/reliability.md` |
| Helm chart presets and gotchas, operator, `k8s_attributes`, `file_log` on pods, events, Target Allocator | `references/kubernetes.md` |
| OTTL transform/filter, logs (severity, multiline, journald, dedup), Prometheus naming, delta/cumulative, tail sampling, redaction, resource detection, semconv changes | `references/processing.md` |
| Backend-specific notes (VictoriaLogs/VictoriaMetrics, ClickHouse, Prometheus remote write, Loki) | `references/backends.md` |
| Security advisories and upgrade floors, hardening, signature verification, `ocb`, config tooling, upgrade procedure, air-gap | `references/security-and-upgrades.md` |
| Where each fact came from, when it was verified | `references/sources.md` |
