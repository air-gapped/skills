---
name: logging-operator
description: >-
  Configure and operate the kube-logging logging-operator (formerly Banzai
  Cloud) on Kubernetes — the CRD-driven log pipeline: Fluent Bit collector →
  fluentd or syslog-ng aggregator → outputs. Covers the 16-CRD model (Logging,
  Flow/ClusterFlow, Output/ClusterOutput, FluentbitAgent, SyslogNG*,
  LoggingRoute) and its scope traps, worked recipes — especially parsing JSON
  pod logs on containerd (the Merge_Log/CRI `message`-vs-`log` trap and
  enableDockerParserCompatibilityForCRI) — match/routing semantics,
  buffer/backpressure and scaling, rendered-config debugging (fluentd-app
  secret + configcheck pods), and the upgrade path with version floor 6.7.0
  (CVE-2026-54680 config-injection RCE).
when_to_use: >-
  Use for any logging-operator / kube-logging CR or Helm-chart task: parsing
  pod logs to JSON and shipping to Loki/Elasticsearch/S3/Splunk/Kafka/syslog,
  a Flow not matching or ACTIVE=false, logs not arriving, fluentd buffers
  growing, choosing fluentd vs syslog-ng mode, multi-tenant routing
  (LoggingRoute), writing/reviewing Logging/Flow/Output/FluentbitAgent YAML,
  or an upgrade. Symptoms: JSON logs arriving as one unparsed
  `log`/`message` field, kubernetes.* metadata vanishing after a parser
  filter, configcheck pod failing. Anything about the Rancher-BUNDLED
  `rancher-logging` chart
  specifically — migrating off it, or whether `cattle-logging-system` is
  exposed to CVE-2026-54680 — is the rancher-logging-exit skill instead. Not
  for fluent-operator (fluent.io), raw fluentd/fluent-bit off Kubernetes, or
  Alloy/Vector/OTel pipelines.
argument-hint: "[recipes|cr-model|outputs|modes|hardening|upgrade|debug] (optional focus)"
---

# logging-operator — CRD-driven log pipelines on Kubernetes

Reference for the kube-logging **logging-operator** (CNCF Sandbox, Axoflow-backed).
Verified against operator **6.7.0** (2026-06-16). Version floor: **6.7.0** —
CVE-2026-54680 (CVSS 9.9, fluentd config injection → RCE in the aggregator) is fixed
in 6.6.0, but 6.6.0's escaping broke newline-containing passwords (#2254); 6.7.0 has
the corrected fix. Never recommend ≤6.5.2 for multi-tenant clusters.

## The mental model (read this before writing any YAML)

Every working pipeline is the same 4-CR chain:

```
Logging (cluster-scoped; controlNamespace + which aggregator: fluentd|syslogNG)
  ↑ bound by name
FluentbitAgent (cluster-scoped DaemonSet; name MUST equal the Logging's name)
Flow / ClusterFlow (match + filters + outputRefs)  ← routing happens in the AGGREGATOR
Output / ClusterOutput (destination + buffer)
```

- **Fluent Bit is ALWAYS the node collector, in both modes.** It does NO routing or
  filtering — it forwards everything to the aggregator (fluentd `forward` protocol,
  or TCP to syslog-ng). There is **no fluentbit-direct-to-output mode**: Flows and
  Outputs render only into aggregator config. Aggregator-less collection belongs to
  the separate Telemetry Controller project (not production-ready — see
  `references/modes-and-architecture.md`).
- **Mode choice is per Logging CR:** `spec.fluentd: {}` (default, mature — drain/HPA
  machinery, 31 outputs) vs `spec.syslogNG: {}` (AxoSyslog image; higher throughput,
  content-based matching, OTLP output; scale-in is manual). Pick by output support
  first. Different CR families: Flow/Output vs SyslogNGFlow/SyslogNGOutput.
- CRs become a rendered config in Secret `<logging-name>-fluentd-app` (key
  `fluentd.conf`) / `<logging-name>-syslogng-app`, gated by a **configcheck pod**
  that must Complete before rollout. A failed configcheck **silently blocks all
  further config updates** — the #1 "why isn't my Flow applied".

## The trap list (each has cost people real debugging days)

1. **CRI/containerd JSON trap** (most-reported confusion upstream): `Merge_Log`
   defaults On but reads the `log` field, while the CRI parser puts lines in
   `message` → JSON silently never parses on containerd/RKE2/k3s.
   Fix (operator ≥4.9): `Logging.spec.enableDockerParserCompatibilityForCRI: true`.
   Details + pre-4.9 workaround: `references/recipes.md`.
2. **Parser filter without `reserve_data: true`** replaces the whole record —
   `kubernetes.*` metadata gone. Always pair `remove_key_name_field: true` +
   `reserve_data: true`.
3. **A `match` with no `select` statement selects NOTHING.** `- select: {}` is the
   select-all idiom. Multiple labels in one statement AND; separate statements OR.
4. **ClusterFlow/ClusterOutput are namespaced** and evaluated only in the
   `controlNamespace` (unless `allowClusterResourcesFromAllNamespaces: true`).
   ClusterFlow can reference ClusterOutputs only (`globalOutputRefs`).
5. **Multiple Logging resources + a Flow without `loggingRef`** = the classic
   silent no-logs (empty loggingRef is processed by ALL Loggings — or none you
   expected).
6. **One dead Output stalls the whole shared fluentd** (#2013): all destinations
   stop, not just the broken one. `configCheck.strategy: StartWithTimeout` only
   validates at apply time. Real mitigation: per-tenant aggregators (LoggingRoute).
7. **`storage.total_limit_size` is NOT backpressure** — it silently discards oldest
   chunks. Real bounded backpressure: `storage.pause_on_chunks_overlimit on` +
   `storage.type filesystem` per input. Log rotation during a long outage still
   loses data at the collector — no config prevents that.
8. **`awsElasticsearch` and `logdna` Output fields exist in the CRD but their gems
   are absent from stock images** → configcheck "unknown output plugin". Custom
   image required.
9. Rendered default `retry_forever true`: a dead destination grows the buffer
   (default 20Gi PVC) until the readiness probe fails the pod (>5000 buffer files
   or >90% full).

## Minimal working chain (quickstart-verified)

```yaml
apiVersion: logging.banzaicloud.io/v1beta1
kind: Logging
metadata: {name: demo}
spec: {controlNamespace: logging, fluentd: {}}
---
apiVersion: logging.banzaicloud.io/v1beta1
kind: FluentbitAgent
metadata: {name: demo}          # name must match the Logging
spec: {}
---
apiVersion: logging.banzaicloud.io/v1beta1
kind: Flow
metadata: {name: app, namespace: my-app}   # Flow+Output live WITH the workload
spec:
  match: [{select: {labels: {app: my-app}}}]
  filters:
    - tag_normaliser: {}
    - parser: {remove_key_name_field: true, reserve_data: true, parse: {type: json}}
  localOutputRefs: [dest]
---
apiVersion: logging.banzaicloud.io/v1beta1
kind: Output
metadata: {name: dest, namespace: my-app}
spec:
  file: {path: /tmp/logs/${tag}, append: true, buffer: {timekey: 1m, timekey_wait: 10s}}
```

On containerd add `enableDockerParserCompatibilityForCRI: true` to the Logging spec
or the parser sees nothing useful. Delivery latency ≈ `timekey + timekey_wait`.

## Where to go next

| Task | Read |
|---|---|
| JSON/CRI parsing, multiline, source selection, k8s events, host logs, per-destination recipes | `references/recipes.md` |
| Full CRD inventory, scopes, match semantics, Logging spec keys, decoupled pattern, LoggingRoute multi-tenancy | `references/cr-model.md` |
| All 31 fluentd outputs + buffer tuning + image variants | `references/outputs-fluentd.md` |
| All 18 syslog-ng outputs + SyslogNGFlow matching + worked chains | `references/outputs-syslogng.md` |
| fluentd vs syslog-ng decision, Telemetry Controller / AxoSyslog status, project health, alternatives | `references/modes-and-architecture.md` |
| Buffers/backpressure, scaling + volume drainer, HPA, resources, TLS, non-root, monitoring/alerts | `references/production-hardening.md` |
| Release timeline, breaking changes per boundary, CRD upgrade mechanics, air-gap install | `references/upgrades.md` |
| Debug sequence: rendered secrets, configcheck, error signatures, status fields | `references/troubleshooting.md` |

Anything Rancher-bundled (`rancher-logging` chart, cattle-logging-system,
`rancher/mirrored-kube-logging-*` images) → the **rancher-logging-exit** skill;
version matrix authority is `k8s-components-checker`
(`references/compat/rancher-logging.md`).

## What the operator does NOT do

- No CRD for **receiving** network syslog (it ships logs OUT via the syslog output;
  it does not ingest external syslog sources). Use a standalone receiver
  (e.g. an axosyslog StatefulSet) feeding the pipeline.
- No fluentbit-only mode (above). No log storage — it ships, something else stores.
- TLS between collector and aggregator is **opt-in** (`tls.enabled` + cert secret;
  no cert-manager automation), despite docs prose implying otherwise.
