# Troubleshooting — the debug sequence

Work top-down; most "no logs" cases resolve at steps 1–3.

## 1. Status fields first

```bash
kubectl get logging -o yaml            # .status.problems / problemsCount /
                                       # configCheckResults / fluentdConfigName
kubectl get logging-all -n <ns>        # every kind, ACTIVE + PROBLEMS columns
```

`ACTIVE=false` on a Flow/Output = not compiled into the pipeline — check its
`status.problems` (dangling outputRef, invalid filter, protected ClusterOutput,
loggingRef mismatch).

## 2. Configcheck gate

Every change spawns `<logging>-fluentd-configcheck-<hash>` which must Complete.
**A failed check silently blocks ALL further config rollouts.** Look for the pod,
read its logs (`error_class=Fluent::ConfigError` pinpoints the resource), fix or
delete the offender; `skipInvalidResources: true` skips broken Flows instead of
blocking everything. `configCheck.strategy: StartWithTimeout` also catches
connection-level errors — but only at apply time.

## 3. Read the rendered config (ground truth)

```bash
kubectl get secret <logging>-fluentd-app -o jsonpath="{.data['fluentd\.conf']}" | base64 -d
kubectl get secret <logging>-fluentbit  -o jsonpath="{.data['fluent-bit\.conf']}" | base64 -d
# syslog-ng: secret <logging>-syslogng-app, key syslog-ng.conf
```

In fluentd.conf, find the `label_router` `<route>` blocks — one per Flow with its
namespace+label criteria. Match mistakes are visible right there (wrong label,
wrong namespace, Flow missing entirely = not compiled in, see step 1).

## 4. Tap the stream

- Drop `- stdout: {}` anywhere in a Flow's filter list → records dump to fluentd
  pod logs at that stage. Remove after.
- Route parse failures: parser filter `emit_invalid_record_to_error: true` +
  `Logging.spec.errorOutputRef: <ClusterOutput>`.
- Fluentd verbosity: `spec.fluentd.logLevel: debug`. Fluent-bit images have
  `-debug` tag variants for exec-ing in.

## 5. Error signature table

| Signature | Meaning / fix |
|---|---|
| JSON arrives as one string field `log`/`message` | CRI trap — `enableDockerParserCompatibilityForCRI: true` (recipes.md) |
| `kubernetes.*` fields vanished after parsing | parser missing `reserve_data: true` |
| `pattern not matched` flood in fluentd | parser pointed at a field that's already merged/absent (double-parse) or wrong key_name |
| `error="can't create buffer file"` | /buffers full, read-only, or (post-5.3) root-owned PVC → chown 100:101 |
| `no space left on device` (fluent-bit) | node buffer dir full (#1954) — storage.total_limit_size / disk pressure |
| `[error] [upstream] connection ... timed out` + `failed to flush chunk` + `no upstream connections available` | aggregator down or stalled — check the SPOF case below |
| `unknown output plugin` at configcheck | plugin gem not in image: `awsElasticsearch`/`logdna` (dead fields), or `-base`/`-filters` image variant lacking output gems |
| Ruby stack trace from an output after upgrade | gem drift (elasticsearch/opensearch/syslog_rfc5424 history) — check release notes, pin image |
| Fluentd pod NotReady, buffers climbing | readiness fails at >5000 buffer files / >90% full — destination down + `retry_forever` |
| Logs "missing" for ~1–2 min then arrive | not a bug: latency ≈ timekey + timekey_wait |
| Duplicate logs after collector restart | positiondb not configured |
| Flow silently ignored, multiple Loggings exist | loggingRef missing/mismatched |
| ClusterFlow/ClusterOutput ignored | created outside controlNamespace (they're namespaced!) |

## 6. The shared-aggregator SPOF (#2013)

One Output with an unreachable endpoint can stall the ENTIRE fluentd — all other
destinations stop receiving. Known fluent-plugin-elasticsearch behavior class.
StartWithTimeout does not protect a running aggregator from a destination that
dies later. Real mitigations: per-tenant aggregators (LoggingRoute), bounded
retries on non-critical outputs, alerting on `logging_buffer_files` growth.

## 7. Buffer forensics

```bash
kubectl exec <logging>-fluentd-0 -- ls -la /buffers   # .buffer / .buffer.meta files
```

Growing file count = destination trouble (see retry_forever note in
outputs-fluentd.md). Enable `metrics: {}` + `bufferVolumeMetrics: {}` and alert
before the readiness probe kills the pod.
