# What To Actually Measure — KPIs & Metric Frameworks For Production Systems (2026)

Audience: an AI agent that must exercise judgment about *what* to measure when a user says "help me see if this is healthy" or "build me a dashboard". Reach for a framework before reaching for specific metrics.

Primary sources (canonical, stable):
- Google SRE Book, *Monitoring Distributed Systems* (Ch. 6) — Four Golden Signals.
- Google SRE Workbook, *Alerting on SLOs* (Ch. 5) — multi-window multi-burn-rate.
- Brendan Gregg, `brendangregg.com/usemethod.html` — USE method.
- Tom Wilkie, Grafana blog 2018-08-02, "The RED Method".
- Prometheus exporter docs.
- OpenTelemetry Semantic Conventions v1.30+ (2026) for metrics.

## Contents
- [0. One-paragraph rubric](#0-one-paragraph-rubric-memorize-this)
- [1. The three foundational frameworks](#1-the-three-foundational-frameworks) — RED / USE / Golden Signals, when to use which
- [2. SLI / SLO / SLA / Error budgets / Burn-rate alerting](#2-sli--slo--sla--error-budgets--burn-rate-alerting) — multi-window multi-burn-rate recipe + PromQL
- [3. The "what to look at" hierarchy](#3-the-what-to-look-at-hierarchy)
- [4. Standard exporter metric catalogs](#4-standard-exporter-metric-catalogs) — node_exporter, kube-state-metrics, cAdvisor, blackbox, postgres, kafka, nginx/envoy/istio, DCGM
- [5. OpenTelemetry semantic conventions (2026)](#5-opentelemetry-semantic-conventions-2026) — canonical names + OTel→Prometheus translation
- [6. Red flags / anti-patterns](#6-red-flags--anti-patterns) — 16 things to push back on
- [7. Dashboard recipes](#7-dashboard-recipes) — 8 ready-made layouts (HTTP / Kafka / Postgres / k8s ns / node / GPU / ingress / cron)
- [8. Business KPI tie-in](#8-business-kpi-tie-in)
- [9. Agent decision tree](#9-agent-decision-tree)

## 0. One-paragraph rubric (memorize this)

- **RED** → *services*. What's happening at the request boundary.
- **USE** → *resources*. What's happening to a thing that has a capacity.
- **Golden Signals** → *user-facing SLIs*. The distilled four that map onto RED+U and feed SLOs.
- **SLO / burn-rate** → *alerting*. Alert on running out of error budget, not on instantaneous threshold crossings.
- If the agent is asked "is X healthy?" and X is a **service**, start with RED. If X is a **host, disk, GPU, queue, connection pool**, start with USE. If X is **customer-facing**, wrap it in an SLO and alert on burn rate.

## 1. The three foundational frameworks

### 1.1 RED — Rate, Errors, Duration (Tom Wilkie)

Applies to: request-driven services (HTTP, gRPC, RPC, GraphQL, any client/server boundary).

- **Rate** — requests per second.
- **Errors** — rate of failing requests.
- **Duration** — distribution of response time (p50, p95, p99, p999 — **NOT** mean).

Cardinality axes: per endpoint × per method × per status class. At minimum split `5xx` — those are *your* failures; `4xx` are often the client's fault and can pollute SLIs.

```promql
sum by (route) (rate(http_requests_total[5m]))

sum by (route) (rate(http_requests_total{status=~"5.."}[5m]))
  / sum by (route) (rate(http_requests_total[5m]))

histogram_quantile(0.99,
  sum by (route, le) (rate(http_request_duration_seconds_bucket[5m])))
```

### 1.2 USE — Utilization, Saturation, Errors (Brendan Gregg)

Applies to: any *resource* with finite capacity — CPU, memory, disk IO, filesystem space, network link, file descriptors, DB connection pool, thread pool, Kafka partition, GPU SM, GPU VRAM, NVLink.

- **Utilization** — % time busy (or % capacity used). Bounded 0–100%.
- **Saturation** — extra work the resource *couldn't yet do*. Queue depth, run-queue, swap activity, iowait, TCP backlog, CFS throttling. The early warning *once utilization ≈ 100%*.
- **Errors** — error events on the resource: disk errors, NIC errors, ECC, XID, TCP retransmits.

**The bit people miss:** a 100%-utilized-but-unsaturated resource is fine; a 50%-utilized-but-saturated one is broken. Saturation is independent.

| Resource | Utilization | Saturation | Errors |
|---|---|---|---|
| CPU | `1 - rate(node_cpu_seconds_total{mode="idle"}[5m])` | `node_load1 / CPU count`, runqueue, CFS throttle | mcheck events |
| Memory | `1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes` | `rate(node_vmstat_pgmajfault[5m])`, swap-in, OOM | OOM kills, ECC |
| Disk IO | `rate(node_disk_io_time_seconds_total[5m])` | `node_disk_io_time_weighted_seconds_total`, iowait | `node_disk_read_errors_total` |
| Filesystem | `1 - node_filesystem_avail_bytes / node_filesystem_size_bytes` | inode exhaustion | FS errors, ro remounts |
| Network | `rx/tx bytes / link_speed` | `node_netstat_Tcp_RetransSegs`, NIC drops | `node_network_receive_errs_total` |
| GPU | `DCGM_FI_DEV_GPU_UTIL` | `SM_OCCUPANCY` << util, memcopy util | `DCGM_FI_DEV_XID_ERRORS` |

### 1.3 Four Golden Signals (Google SRE book)

- **Latency** — distribution, not mean. Separately track successful vs failed (fast 500 shouldn't pollute latency SLI).
- **Traffic** — demand in the unit native to the system (HTTP RPS, msg/s, concurrent sessions, IOPS).
- **Errors** — explicit (5xx), implicit (wrong content), policy (latency > 1s counts as fail).
- **Saturation** — "fullest" resource. Often shows up as latency rising before utilization.

Mapping: Latency+Errors ≈ RED{Duration,Errors}; Traffic ≈ RED.Rate; Saturation ≈ USE.Saturation. Golden Signals = RED + USE.Saturation distilled for user experience.

### 1.4 When to use which

| Situation | Framework |
|---|---|
| "Is my HTTP API healthy?" | RED per route + SLO |
| "Is my consumer keeping up?" | RED on handler + saturation (consumer lag) |
| "Is my node overloaded?" | USE across CPU/mem/disk/net |
| "Did my deploy regress users?" | Golden Signals + SLO burn rate |
| "Why is latency spiking?" | RED at edge → USE on each hop |
| "Is my GPU fleet healthy?" | USE (util, VRAM, thermals, XID) + RED on inference service |

## 2. SLI / SLO / SLA / Error budgets / Burn-rate alerting

### 2.1 Definitions
- **SLI** — measured number, usually `good_events / valid_events` over a window.
- **SLO** — target for the SLI over a compliance window (e.g. 99.9% over 30d).
- **SLA** — contract with customer, SLA < SLO for margin.
- **Error budget** — `1 − SLO`. 99.9% over 30d ≈ 43.2 min allowance.
- **Burn rate** — how fast budget is being spent; 1 = on-target, 10 = would exhaust 30-day budget in 3 days.

### 2.2 Good SLIs
Be proxies for user experience, not infrastructure:
- **Availability / success rate** — fraction of requests without server error.
- **Latency distribution** — p50 / p95 / p99 / p999. Pick percentile by user pain.
- **Freshness** — age of the youngest record a read can see (pipelines, caches, search).
- **Correctness** — synthetic probes / shadow traffic that verifies answers are right.
- **Coverage** — fraction of inputs actually processed (batch/streaming).
- **Durability** — for storage.

Availability SLI shape:
```promql
sum(rate(http_requests_total{status!~"5..",route="/api"}[5m]))
  / sum(rate(http_requests_total{route="/api"}[5m]))
```

Latency-in-scope SLI — use **buckets directly**, not `histogram_quantile`:
```promql
sum(rate(http_request_duration_seconds_bucket{le="0.5",status!~"5.."}[5m]))
  / sum(rate(http_request_duration_seconds_count[5m]))
```

### 2.3 Why single-threshold alerts are broken
1. Fire on noise.
2. Miss slow burns.
3. Disconnected from the promise.

### 2.4 Multi-window multi-burn-rate recipe (SRE Workbook, Ch. 5)

Canonical tiers for a 30-day SLO:

| Severity | Burn rate | Long window | Short window | Budget burned if sustained |
|---|---|---|---|---|
| Page (fast) | 14.4× | 1 h | 5 m | 2% in 1 h |
| Page (medium) | 6× | 6 h | 30 m | 5% in 6 h |
| Ticket (slow) | 3× | 1 d | 2 h | 10% in 1 d |
| Ticket (very slow) | 1× | 3 d | 6 h | 10% in 3 d |

Both the long and the short window must breach — long = significance, short = auto-resolve.

```promql
(
  sum(rate(http_requests_total{status=~"5.."}[1h]))
  / sum(rate(http_requests_total[1h]))
) > (14.4 * (1 - 0.999))
AND
(
  sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))
) > (14.4 * (1 - 0.999))
```

For 99.9%, `1−SLO=0.001`, threshold `0.0144` (1.44% errors).

### 2.5 Tooling
- **sloth** (`github.com/slok/sloth`) — generates Prometheus rules from a small SLO YAML.
- **pyrra** (`github.com/pyrra-dev/pyrra`) — Kubernetes-native SLO controller.
- **OpenSLO** — vendor-neutral SLO spec.

## 3. The "what to look at" hierarchy

Walk the stack from user inward:
1. **User-facing SLIs** — RED + Golden Signals at the edge. Alert on burn rate.
2. **Service internals** — RED per internal boundary. Dependency latency. Queue saturation. Circuit breaker. Retry rate (retries hide errors).
3. **Hosts / nodes** — USE.
4. **Platform** — Kubernetes pod / deploy / PVC / node conditions, HPA, scheduler.
5. **Business KPIs** — sign-ups, conversions, DAU, MAU, GMV, ARR, revenue/sec, failed-transaction $ rate.

## 4. Standard exporter metric catalogs

### 4.1 node_exporter
- `node_cpu_seconds_total{mode}`
- `node_memory_MemAvailable_bytes`, `node_memory_MemTotal_bytes`
- `node_memory_SwapFree_bytes`, `node_memory_SwapTotal_bytes`
- `node_vmstat_pgmajfault`
- `node_filesystem_avail_bytes`, `node_filesystem_size_bytes`, `node_filesystem_files_free`, `node_filesystem_files`
- `node_disk_io_time_seconds_total`, `node_disk_io_time_weighted_seconds_total`
- `node_disk_read_bytes_total`, `node_disk_written_bytes_total`
- `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`
- `node_network_receive_errs_total`, `node_network_transmit_errs_total`
- `node_netstat_Tcp_RetransSegs`
- `node_load1`, `node_load5`, `node_load15`
- `node_filefd_allocated`, `node_filefd_maximum`
- `node_pressure_cpu_waiting_seconds_total`, `node_pressure_memory_waiting_seconds_total`, `node_pressure_io_waiting_seconds_total` — PSI, modern saturation signal

```promql
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))

1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes

predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[1h], 4*3600) < 0

rate(node_pressure_memory_waiting_seconds_total[5m])
```

### 4.2 kube-state-metrics
- `kube_pod_status_phase{phase=Pending|Running|Succeeded|Failed|Unknown}`
- `kube_pod_status_ready`, `kube_pod_container_status_ready`
- `kube_pod_container_status_waiting_reason` — ImagePullBackOff, CrashLoopBackOff
- `kube_pod_container_status_restarts_total`
- `kube_pod_container_status_terminated_reason` — OOMKilled, Error
- `kube_deployment_spec_replicas`, `kube_deployment_status_replicas_available`
- `kube_statefulset_status_replicas_ready`
- `kube_daemonset_status_number_unavailable`
- `kube_job_status_failed`, `kube_job_status_succeeded`
- `kube_cronjob_status_last_schedule_time`
- `kube_node_status_condition{condition,status}`
- `kube_persistentvolumeclaim_resource_requests_storage_bytes`
- `kube_hpa_status_current_replicas`, `kube_hpa_spec_max_replicas`

### 4.3 cAdvisor
- `container_cpu_usage_seconds_total{container,pod,namespace}`
- `container_cpu_cfs_throttled_periods_total`, `container_cpu_cfs_periods_total`
- `container_memory_working_set_bytes` — what OOM killer watches
- `container_memory_rss`, `container_memory_cache`
- `container_fs_usage_bytes`, `container_fs_limit_bytes`
- `container_network_receive_bytes_total`, `container_network_transmit_bytes_total`
- `container_oom_events_total`

```promql
# CPU throttle ratio (>0 = throttled)
rate(container_cpu_cfs_throttled_periods_total[5m])
  / rate(container_cpu_cfs_periods_total[5m])

# Working set vs limit (OOM risk)
container_memory_working_set_bytes
 / on(namespace,pod,container) group_left
 kube_pod_container_resource_limits{resource="memory"}
```

### 4.4 blackbox_exporter
- `probe_success`, `probe_duration_seconds`
- `probe_http_status_code`, `probe_http_duration_seconds{phase="resolve|connect|tls|processing|transfer"}`
- `probe_ssl_earliest_cert_expiry`
- `probe_dns_lookup_time_seconds`

### 4.5 postgres_exporter
- `pg_up`
- `pg_stat_database_xact_commit`, `pg_stat_database_xact_rollback`
- `pg_stat_database_blks_hit`, `pg_stat_database_blks_read`
- `pg_stat_database_numbackends` vs `pg_settings_max_connections`
- `pg_stat_database_deadlocks`, `pg_stat_database_temp_files`
- `pg_stat_replication_lag_bytes`
- `pg_stat_activity_count{state}`
- `pg_locks_count{mode}`
- `pg_stat_user_tables_n_dead_tup` (bloat)

### 4.6 kafka_exporter
- `kafka_consumergroup_lag{consumergroup,topic,partition}` — THE metric
- `kafka_consumergroup_lag_sum`
- `kafka_topic_partition_current_offset` vs `kafka_consumergroup_current_offset`
- `kafka_topic_partition_in_sync_replica`
- `kafka_topic_partition_under_replicated_partition`

```promql
# Time-to-drain
sum by (consumergroup)(kafka_consumergroup_lag)
 / sum by (consumergroup)(rate(kafka_consumergroup_current_offset[5m]))
```

### 4.7 nginx / envoy / istio
- `nginx_http_requests_total`, `nginx_connections_active`
- `envoy_http_downstream_rq_total{response_code_class}`
- `envoy_cluster_upstream_rq_time`, `_retry`, `_timeout`
- `envoy_cluster_outlier_detection_ejections_active` — circuit-broken hosts
- `istio_requests_total{response_code, source_workload, destination_workload}`
- `istio_request_duration_milliseconds`

### 4.8 DCGM / NVIDIA GPU
- `DCGM_FI_DEV_GPU_UTIL` — coarse (% time any kernel running)
- `DCGM_FI_DEV_SM_OCCUPANCY` — **real** util
- `DCGM_FI_DEV_MEM_COPY_UTIL`
- `DCGM_FI_DEV_FB_USED`, `DCGM_FI_DEV_FB_FREE`
- `DCGM_FI_DEV_POWER_USAGE`, `DCGM_FI_DEV_POWER_MGMT_LIMIT`
- `DCGM_FI_DEV_GPU_TEMP`, `DCGM_FI_DEV_MEMORY_TEMP`
- `DCGM_FI_DEV_XID_ERRORS` — HW-health signal (XID 48/63/79/94 serious)
- `DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL`, `DCGM_FI_DEV_NVLINK_CRC_FLIT_ERROR_COUNT_TOTAL`
- `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE`, `DCGM_FI_PROF_DRAM_ACTIVE`

## 5. OpenTelemetry semantic conventions (2026)

### Canonical names
- `http.server.request.duration` (histogram, s)
- `http.server.active_requests` (updown counter)
- `http.client.request.duration`
- `rpc.server.duration`, `rpc.client.duration`
- `db.client.operation.duration`
- `db.client.connections.usage{state=idle|used}`
- `messaging.client.published.messages`, `messaging.client.consumed.messages`
- `container.cpu.time`, `container.memory.usage`
- `system.cpu.utilization`, `system.memory.usage`
- `k8s.pod.phase`, `k8s.pod.ready`

### OTel → Prometheus name translation
- `.` → `_` (e.g. `http.server.request.duration` → `http_server_request_duration`)
- `-` → `_`
- Unit suffix appended: seconds → `_seconds`, bytes → `_bytes`
- Counters get `_total`

Thus `http.server.request.duration` (seconds, histogram) → `http_server_request_duration_seconds_bucket` / `_sum` / `_count`.

## 6. Red flags / anti-patterns

1. **CPU% as the only saturation signal** — misses memory PSI, iowait, NIC drops, FD exhaustion.
2. **Averaging latency** — `avg(latency)` hides the tail. Always p99/p999.
3. **Single-threshold alerts** — replace with multi-window multi-burn-rate.
4. **Absolute error counts in alerts** — "5xx > 100/min" doesn't scale. Use rate or ratio.
5. **`up == 1` mistaken for healthy** — only says scrape worked; app can 500 on everything.
6. **Aggregating across tenants/regions/routes** — one bad cohort hides in the mean.
7. **Monitoring infrastructure without SLIs**.
8. **Over-alerting → alert fatigue**.
9. **No error-budget policy**.
10. **Histograms with default buckets** — `[0.005..10]s` is wrong for 100ms-tail services or 60s batch.
11. **Counters without `rate()`, gauges without `avg_over_time()`**.
12. **High-cardinality labels** (user id, request id, full URL) — blows up TSDB.
13. **Ignoring retries** — retry storms look like traffic but are outages.
14. **Missing saturation on work queues** — latency spikes are usually queue buildups, not CPU.
15. **No synthetic probe from outside the VPC**.
16. **Clock skew** — breaks trace timelines. Track `node_timex_offset_seconds`.

## 7. Dashboard recipes

### 7.1 HTTP service — RED per route
1. RPS per route
2. Error rate per route (5xx/total)
3. Latency p50/p95/p99 per route
4. In-flight: `sum by (route)(http_server_active_requests)`
5. SLO burn-rate panel
6. Top-5 slowest routes (table)
7. Top-5 erroring routes (table)

### 7.2 Kafka consumer
1. Lag per group
2. Processing rate
3. Time-to-drain
4. Handler error rate
5. Handler p99
6. Rebalance count
7. ISR shrink
8. DLQ depth

### 7.3 Postgres
1. Connection saturation
2. Commit vs rollback rate
3. Cache hit ratio
4. Replication lag (bytes + seconds)
5. Top-10 slow queries (pg_stat_statements)
6. Deadlock rate
7. Temp files rate
8. Top-10 bloated tables
9. Checkpoint buffer rate
10. Active vs idle-in-txn count

### 7.4 Kubernetes namespace
1. Pod phases
2. Restart rate per deploy (1h)
3. Deployment replica health
4. CPU per deploy
5. Memory working set per deploy
6. CFS throttle ratio per deploy
7. HPA current vs min/max
8. PVC fill %
9. Currently-waiting pods + reason
10. OOMKilled count

### 7.5 Node / host (USE)
1. CPU % by mode stacked
2. Load1/5/15 vs CPU count
3. PSI CPU/mem/io waiting
4. Memory breakdown
5. Disk IO util per device
6. Disk latency per device
7. Filesystem fill % per mount
8. Net throughput rx/tx
9. TCP retransmit rate
10. FD usage

### 7.6 GPU fleet (DCGM)
1. GPU util per device (heatmap)
2. SM occupancy
3. VRAM used %
4. Tensor-core active %
5. Power vs limit
6. Temp (core + HBM)
7. XID count (24h)
8. ECC SBE/DBE
9. NVLink CRC errors
10. PCIe replay delta
11. Overlay: inference RED

### 7.7 Ingress / gateway
1. Total RPS
2. 5xx rate per upstream
3. p99 latency per upstream
4. Upstream error breakdown
5. Active connections
6. Cert expiry
7. Rate-limited count
8. Circuit-breaker open count

### 7.8 Cron / batch job
1. Time since last success
2. Last run duration
3. Success rate over N runs
4. Running-job count
5. Failure count
6. Records processed per run
7. Input-queue depth before run

## 8. Business KPI tie-in

- **Successful transaction rate** — catches "requests OK, transactions failed" silent bugs
- **Revenue per second**
- **Conversion funnel** — funnel_step_total + ratios
- **Cost per request** — opencost/kubecost ÷ requests
- **Time-to-value** — signup → first meaningful action SLO
- **DAU/MAU/WAU** from auth events
- **Availability SLO** — 30-day rolling; "budget remaining (minutes)" is the exec summary
- **Error budget burn by team**

Exec dashboard:
1. Availability SLO (R/A/G)
2. Error budget remaining + 30d line
3. Transactions/sec
4. Revenue/sec + DoD delta
5. Active users now
6. Cost / request trend
7. Incident timeline (annotations)

## 9. Agent decision tree

```
User asks "what should I measure for X?"
├── X is user-facing (HTTP/gRPC/GraphQL/API):
│     ├── RED per route
│     ├── SLO (availability + latency)
│     └── Multi-window multi-burn-rate alerts
├── X is an internal service / worker / consumer:
│     ├── RED on handler
│     ├── Saturation: in-flight, queue depth, lag
│     └── Dependency RED
├── X is a resource (host, disk, GPU, pool, NIC):
│     └── USE
├── X is a database:
│     ├── Connection saturation
│     ├── Cache hit / miss
│     ├── Slow queries
│     ├── Replication lag
│     └── Commit/rollback rates
├── X is a broker / queue:
│     ├── Consumer lag per group
│     ├── Processing rate
│     ├── ISR / partition health
│     └── DLQ depth
├── X is a batch / cron:
│     ├── Last success time
│     ├── Duration p50/p99
│     ├── Success rate
│     └── Records processed
└── X is "the business":
      ├── Transaction success rate
      ├── Revenue/sec
      ├── Conversion funnel
      ├── Availability SLO + error budget
      └── Cost / request
```

Before picking metrics:
1. Identify which bucket X falls into.
2. Name the framework (RED / USE / GS).
3. List the 5–10 default metrics from §4 for whichever exporter applies.
4. Propose SLIs + an SLO + a burn-rate alert if X is user-facing.
5. Flag anti-patterns from §6 in the user's existing setup.
