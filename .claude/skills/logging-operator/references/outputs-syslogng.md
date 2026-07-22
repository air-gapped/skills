# syslog-ng mode — outputs, matching, worked chains

The aggregator runs AxoSyslog (`ghcr.io/axoflow/axosyslog`, 4.24.0 at operator
6.5+) with syslog-ng-reloader + axosyslog-metrics-exporter sidecars. Fluent Bit
remains the collector (TCP via its `syslogng_output`). Field names verified from
`syslogng_output_types.go` at 6.7.0 (set unchanged since 6.1.0).

## The 18 SyslogNGOutput plugin fields (exact key spellings)

`loggly` · `syslog` · `file` · `mqtt` · `redis` · `mongodb` · `sumologic-http` ·
`sumologic-syslog` · `http` · `elasticsearch` (renders driver `elasticsearch-http`)
· `elasticsearch-datastream` · `logscale` (CrowdStrike Falcon LogScale/Humio) ·
`splunk_hec_event` · `loki` · `s3` · `openobserve` (driver `openobserve-log`) ·
`opentelemetry` (OTLP gRPC)

Note the inconsistent spellings — `sumologic-http` (dash), `splunk_hec_event`
(underscores), `elasticsearch-datastream`. Copy exactly.

OTLP is syslog-ng-exclusive: fluentd mode has no OTLP output. If the destination
is an OTel collector, syslog-ng mode is the native path.

## Matching — a tree, not a list

`SyslogNGFlow.spec.match` is a single expression tree (unlike fluentd's ordered
list), combinators `regexp` / `and` / `or` / `not`. Field references use the
JSON path prefix with the configured delimiter — set
`Logging.spec.syslogNG.jsonKeyDelim: '#'` (recommended) and reference
`json#kubernetes#labels#...`:

```yaml
apiVersion: logging.banzaicloud.io/v1beta1
kind: SyslogNGFlow
metadata: {name: app, namespace: my-app}
spec:
  match:
    regexp:
      value: "json#kubernetes#labels#app.kubernetes.io/instance"
      pattern: log-generator
      type: string            # pcre (default) | string | glob
  localOutputRefs: [dest]
```

Unlike fluentd Flows, syslog-ng can match on **log content**, not just metadata.
Filters are exactly three families: `match` (drop/keep), `parser`, `rewrite`
(rename/set/subst/unset/group_unset, each with optional `condition`).

## Worked chains (from operator samples/quickstart)

OTLP to an OTel collector:

```yaml
kind: Logging
spec: {controlNamespace: logging, syslogNG: {}, fluentbit: {}}
---
kind: SyslogNGFlow
metadata: {name: all, namespace: logging}
spec:
  match: {}                      # match-all
  localOutputRefs: [otlp]
---
kind: SyslogNGOutput
metadata: {name: otlp, namespace: logging}
spec:
  opentelemetry:
    url: "otel-collector:4317"   # gRPC, port in url
    auth: {insecure: {}}         # empty object = insecure
```

HTTP with reliable disk buffer:

```yaml
kind: SyslogNGOutput
spec:
  http:
    url: http://receiver:8080
    headers: ["Content-Type: application/json"]
    disk_buffer: {dir: /buffers, disk_buf_size: 512000000, reliable: true}
```

OpenObserve:

```yaml
kind: SyslogNGOutput
spec:
  openobserve:
    url: http://openobserve:5080
    port: 5080
    organization: default
    stream: k8s
    user: root@example.com
    password: {valueFrom: {secretKeyRef: {name: oo, key: password}}}
    # embeds HTTPOutput → disk_buffer also available
```

## Operational caveats vs fluentd mode

- **No volume-drainer equivalent** — scaling the syslog-ng StatefulSet DOWN leaves
  disk buffers unprocessed; draining is a manual process.
- Official guidance recommends syslog-ng for high message volume (multithreaded)
  and many-flows/complex-routing — but the ecosystem (drain, HPA docs, most
  community usage, 31 vs 18 outputs) is fluentd-first. Default to fluentd unless
  message rate, content-based matching, or OTLP demands syslog-ng.
- syslog-ng metric names in the built-in PrometheusRules were wrong until 6.2.2.
- Rendered config lands in Secret `<logging>-syslogng-app`, key `syslog-ng.conf`;
  configcheck mechanics identical to fluentd's.
