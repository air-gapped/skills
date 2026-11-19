# Components: names, removals, stability, distributions

Checked against core and contrib v0.162.0. A component's name, stability and
presence in a distribution change between releases — re-check on the version
you run (`otelcol components` lists what a binary contains).

## snake_case renames

The convention is `lower_snake_case`. The old name keeps working as a
deprecated alias and logs `Using deprecated alias X; use Y instead`. No
removal date is announced. On a collector **older** than the rename, the new
name fails to start the collector — so match names to the version.

| Since | Old → new |
|---|---|
| core v0.144 | exporters `otlp` → `otlp_grpc`, `otlphttp` → `otlp_http` |
| v0.145 | `azureeventhub` → `azure_event_hub`, `mongodbatlas` → `mongodb_atlas` |
| v0.146 | `k8sattributes` → `k8s_attributes`, `signaltometrics` → `signal_to_metrics` |
| v0.148 | `azure_blob`, `azure_monitor`, `cisco_os`, `google_cloud_storage`, `prometheus_remote_write` (receiver), `yang_grpc` |
| v0.149 | `filelog` → `file_log` |
| v0.150 | `httpcheck`, `namedpipe`, `tcplog`, `tlscheck`, `udplog`, `windowseventlog` get snake_case names |
| v0.151 | `hostmetrics` → `host_metrics`, `k8sobjects` → `k8s_objects`, `servicegraph` → `service_graph`, `spanmetrics` → `span_metrics`, `filestats`, `sshcheck` |
| v0.152 | `kubeletstats` → `kubelet_stats`, `kafkametrics`, `tcpcheck`, `otlpjson`, `roundrobin`, `slowsql`, `awslambda` |
| v0.153 | `loadbalancing` → `load_balancing`, `resourcedetection` → `resource_detection`, `metricsaslogs` |
| v0.154 | `prometheusremotewrite` (exporter) → `prometheus_remote_write`, `apachespark`, `envoyals`, `otlpjsonfile`, `webhookevent` |
| v0.155–v0.162 | `cumulativetodelta` → `cumulative_to_delta`, `deltatocumulative` → `delta_to_cumulative`, `deltatorate`, `sqlquery`, `azuremonitor`, `windowsperfcounters`, `icmpcheckreceiver` → `icmp_check`, `awss3`, `grafanacloud` |
| version not recorded | `logdedup` → `log_dedup` |
| core v0.162 | processor `queuebatch` → `queue_batch` (**breaking**, no alias noted) |

- Unchanged names: `otlp` (receiver), `transform`, `filter`, `attributes`,
  `prometheus`, `kafka`, `syslog`, `zipkin`, `journald`, `tail_sampling`,
  `redaction`, `batch`, `memory_limiter`.
- Not every rename kept an alias: `dynamic_sampling` → `adaptive_tail_sampling`
  (v0.160) has none.
- The Helm chart rewrites old names to new ones itself
  (`rewriteDeprecatedComponentNames`, default true). With an image older than
  the rename (roughly < 0.144–0.154 depending on the component), set it to
  `false`.

## Removed or deprecated

| Component | Status | Since | Use instead |
|---|---|---|---|
| `routing` processor | removed | **v0.133** (not v0.116, as models often claim) | `routing` connector |
| `loki` exporter | removed | **v0.131** (not v0.126) | `otlp_http` to Loki's native OTLP endpoint |
| `opencensus` receiver/exporter | removed | v0.134 | OTLP |
| `sapm` receiver / exporter | removed | v0.135 / v0.148 | OTLP |
| JMX receiver | removed | v0.157 | — |
| `kafkatopics_observer` | removed | v0.159 | `kafka` receiver |
| `mezmo` exporter, `wavefront` receiver | removed | v0.161, v0.162 | — |
| `signalfx` receiver | deprecated | v0.146 | OTLP receiver |
| `resource_detection` detector `k8snode` | deprecated | v0.154 | `k8s_api` |
| Jaeger exporter | removed (earlier) | — | Jaeger accepts OTLP |

## Stability levels (v0.162.0)

Alpha and development components may change config or behaviour in any minor
release; prefer stable/beta in production paths.

| Component | Stability |
|---|---|
| `otlp_http` / `otlp_grpc` exporters | stable (traces, metrics, logs) |
| `k8s_attributes` processor | stable (v0.161) — the only v1 contrib module |
| `prometheus` receiver, `prometheus` and `prometheus_remote_write` exporters | beta |
| `file_log`, `k8s_objects`, `file_storage` | beta |
| `batch`, `memory_limiter` processors | beta (not deprecated) |
| `transform` | beta; `filter` alpha (traces/metrics/logs) |
| `clickhouse` exporter | beta traces/logs, alpha metrics |
| `elasticsearch` exporter | beta traces/logs, development metrics |
| `tail_sampling`, `probabilistic_sampler` (traces), `cumulative_to_delta`, `resource_detection`, `redaction` (traces) | beta |
| `routing` connector, `span_metrics`, `service_graph`, `delta_to_cumulative`, `log_dedup`, `journald`, `syslog`/`awss3` exporters, `k8s_events`, `k8s_leader_elector`, `tlscheck`, `systemd`, OpAMP supervisor/extension | alpha |
| `chrony` receiver | beta |
| `icmp_check` | development |

## Receivers that do not exist

- No SMART disk-health receiver and no IPMI receiver (only `redfish`). Keep a
  host agent such as Telegraf for those.
- No `sysctl fs` / `file-nr` source.

## Distributions

Six in `opentelemetry-collector-releases`: `otelcol` (core), `otelcol-contrib`
(~250 components), `otelcol-k8s`, `otelcol-otlp`, `otelcol-ebpf-profiler`,
`otelcol-prometheus` (new in v0.162, experimental — not for production).

- `otelcol-k8s` contains otlp, `file_log`, `host_metrics`, `kubelet_stats`,
  `k8s_cluster`, `k8s_events`, `k8s_objects`, `receiver_creator`,
  `prometheus`, `journald`, `fluentforward`, … ; processors incl.
  `k8s_attributes`, `resource_detection`, `transform`, `filter`,
  `tail_sampling`; exporters `otlp_grpc`, `otlp_http`, `debug`, `file`,
  `load_balancing`, `otelarrow`; extensions `health_check`,
  `k8s_leader_elector`, `k8s_observer`, `file_storage`, `opamp`, `pprof`,
  `zpages`. It does **not** contain `prometheus_remote_write`, `kafka`,
  `syslog` or vendor exporters.
- The Helm chart's UPGRADING.md says Docker Hub images stopped at 0.123.1; use
  `ghcr.io/open-telemetry/opentelemetry-collector-releases/<distro>`.
- Build your own with `ocb` when you need components from several
  distributions or want a smaller attack surface — see
  `security-and-upgrades.md`.
