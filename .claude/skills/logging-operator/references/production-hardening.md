# Production hardening — buffers, scaling, security, monitoring

## Backpressure and durability (the canonical chain)

Collector (fluent-bit) → aggregator (fluentd) → destination. Each hop can drop:

- Per input: `storage.type filesystem` (durability across restarts) + `positiondb`
  volume (no positiondb ⇒ restart re-reads files ⇒ **duplicates** — the #1
  duplicate-log cause).
- `storage.max_chunks_up` (default 128) is a **GLOBAL** memory cap across inputs.
- **`storage.total_limit_size` is NOT backpressure** — when exceeded it silently
  discards the OLDEST chunks (data loss with no error).
- Real bounded backpressure: `storage.pause_on_chunks_overlimit on` per input —
  pauses the tail instead of ballooning. Terminal caveat: while paused, files the
  container runtime rotates away are lost — **log rotation during a long
  destination outage = unavoidable loss at the collector**. Size disk buffers for
  your outage tolerance.
- Memory-buffer symptom: `[warn] ... mem buf overlimit` + pause/resume churn =
  intermittent loss (#2131). Moving to filesystem buffering removes memory
  backpressure and can shift the wall to aggregator overload (connection timeouts
  to :24240, retry storms) — filesystem buffering "needs proper tuning", not a
  set-and-forget.
- Aggregator flow-control knobs: `network.maxWorkerConnections`,
  `syslogng_output.Workers`, `Retry_Limit: "no_limits"`; 4.6+ renders a dedicated
  tail input per tenant so one tenant's backpressure doesn't stall others;
  `forceHotReloadAfterGrace` (5.0) because hot reload blocks while an output is
  down.

## Scaling fluentd

- **Out** is easy (Service load-balances). **In** is the buffer-affinity problem:
  a stopped pod strands its PVC buffers. Enable the volume drainer:
  ```yaml
  spec:
    fluentd:
      scaling: {drain: {enabled: true}}
  ```
  Spawns a drainer Job (same config+volume, drain-watch sidecar) + a placeholder
  pause pod; PVCs labeled `logging.banzaicloud.io/drain-status: drained`; opt-out
  per PVC with label `logging.banzaicloud.io/drain: no`. Drain-watch had real hang
  bugs until fixes across 6.4.0–6.5.0 — another reason for the 6.7.0 floor.
  **syslog-ng has no drain equivalent** (manual).
- **HPA**: `bufferVolumeMetrics.serviceMonitor: true` → Prometheus Adapter →
  recording rule on `buffer_space_usage_ratio`, target ~80%. **Leave
  `scaling.replicas` unset** so HPA owns the count (the operator enforces replicas
  only when explicitly set; older website doc claiming you must delete the operator
  deployment is stale).
- Replicas>1 ⇒ out-of-order chunk delivery: ES tolerates, **Loki needs tuning**
  (#674); forward keepalive skews load across replicas (#661).
- Multi-worker fluentd: dedicate tainted compute-optimized nodes, requests=limits,
  multiply resources by workers. Known broken with workers>1: `detectExceptions`
  (#1490), configcheck (#1023) — both still open.

## Resources (defaults are too low for prod)

| Component | Default req | Default limit |
|---|---|---|
| fluent-bit | 100m / 50Mi | 200m / 100Mi |
| fluentd | 500m / 100Mi | 1000m / 400Mi |
| syslog-ng | 500m / 100Mi | 1000m / 400Mi |

Fluentd buffer PVC default 20Gi. Scale-out trigger heuristic: buffer dir growth
can't stay under the `timekey + timekey_wait` flush window.

## Security

- **Version floor 6.7.0** — CVE-2026-54680 (CVSS 9.9): ≤6.5.2 renders CRD/secret
  string values into fluent.conf unescaped; a newline injects arbitrary directives
  (`<match **> @type exec` ⇒ RCE in the aggregator, which holds every output
  credential and any IRSA/Workload-Identity role on its SA). Fixed 6.6.0; 6.6.0
  broke newline passwords (#2254); use 6.7.0. Critical wherever tenants can author
  Flows/Outputs. When upgrading across 6.6: rendered config changes for values
  containing quotes/backslashes/newlines — diff the `<logging>-fluentd-app` secret
  before/after.
- Fluentd runs non-root since 5.3: UID 100 / GID 101 / fsGroup 101, seccomp
  RuntimeDefault. Pre-5.3 root-owned buffer PVCs break on upgrade
  (`Permission denied @ dir_s_mkdir`) — chown 100:101 (#1908).
  `CreateOpenShiftSCC` option exists.
- TLS collector↔aggregator is **opt-in**: `tls: {enabled: true, secretName: <tls
  secret with tls.crt/tls.key/ca.crt>, sharedKey: ...}` on both fluentd and
  fluentbit specs. No cert-manager automation. Output-side TLS is per-plugin.
- Operator ClusterRole is broad (cluster-wide secrets/pods/workloads CRUD) — treat
  the operator namespace as sensitive.
- Multi-tenant guardrails: `ClusterOutput.spec.protected: true` against Flow spam;
  the isolation ladder + LoggingRoute in cr-model.md.

## Monitoring the pipeline itself

- `metrics.serviceMonitor: true` under fluentd / syslogNG / fluentbit specs
  (15s/5s defaults); buffer-volume metrics via node-exporter sidecar:
  `bufferVolumeMetrics.serviceMonitor: true`.
- Key metrics: `logging_buffer_size_bytes{entity="/buffers"}`,
  `logging_buffer_files`. syslog-ng metrics via axosyslog-metrics-exporter.
- Built-in alerts: `metrics.prometheusRules: true`, per-rule override via
  `prometheusRulesOverride` (4.9+). No published runbooks (#1556). syslog-ng rule
  metric names wrong before 6.2.2.
- Defaults that fire on buffer trouble: readiness fails at >5000 buffer files or
  buffers >90% full (`readinessDefaultCheck`); liveness checks /buffers activity
  (600s initial delay).
- The aggregator's own errors: `Logging.spec.errorOutputRef` → ClusterOutput
  (no filters allowed on that flow). Fluentd/fluent-bit own stdout is excluded from
  collection since 4.4 (`fluentbit.io/exclude: "true"`).
- Watch for: eventrouter memory growth if EventTailer is used pre-6.7.0 (#1993);
  `logging_buffer_files` climbing = destination trouble; retry-rate spikes.
