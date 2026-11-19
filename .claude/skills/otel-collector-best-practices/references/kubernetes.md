# Collector on Kubernetes

Checked against Helm chart `opentelemetry-collector` 0.180.0 (default image
v0.163.2), operator v0.163.0, contrib v0.165.1, 2026-11.

## Contents
- Helm chart or operator
- Chart presets
- Chart gotchas
- Chart upgrade notes (0.157 → 0.180)
- k8s_attributes
- file_log for pod logs
- Cluster-wide receivers and leader election
- Target Allocator
- Field-tested checks

## Helm chart or operator

| | Helm chart | Operator |
|---|---|---|
| Gives | one workload per release (`mode`: daemonset / deployment / statefulset), ConfigMap, presets, RBAC | CRDs `OpenTelemetryCollector` (incl. sidecar mode), `Instrumentation`, `TargetAllocator`, `OpAMPBridge`, `ClusterObservability` |
| Pick when | you need collectors only (agent + gateway) and plain Helm/GitOps | you need auto-instrumentation (Java, .NET, Node, Python, Go, httpd, nginx), Target Allocator with ServiceMonitor/PodMonitor, or OpAMP |
| Costs | — | admission webhook (cert-manager or the chart's `autoGenerateCert`), another controller to upgrade; v0.160 turned network policies off by default |

Related charts: `opentelemetry-kube-stack` (alpha: operator + agent pool),
`opentelemetry-target-allocator` (standalone TA).

## Chart presets

| Preset | Adds | Instances |
|---|---|---|
| `logsCollection` | `file_log` on `/var/log/pods/*/*/*.log`, excludes the collector's own logs, `start_at: end`, `include_file_path: true`, `container` operator (`maxRecombineLogSize` 100 KiB). `storeCheckpoints: true` adds `file_storage` at hostPath `/var/lib/otelcol` and runs as root | per node — DaemonSet |
| `hostMetrics` | `host_metrics` with `root_path: /hostfs` (cpu, load, memory, disk, filesystem, network) | per node |
| `kubeletMetrics` | `kubelet_stats` at `${K8S_NODE_IP}:10250` | per node |
| `kubernetesAttributes` | `k8s_attributes` prepended to all pipelines; node filter in DaemonSet mode | any |
| `kubernetesEvents` | `k8s_objects` events (watch) — or `k8s_events` with `useK8sEventsReceiver: true` | **one replica, no leader election. In DaemonSet mode it renders no receiver at all.** |
| `kubernetesObjects` | `k8s_objects` pull (1h) of core/rbac/storage/networking/… groups; optional `watch` and `events` | leader election **only in `mode: daemonset`**; a multi-replica Deployment duplicates |
| `clusterMetrics` | `k8s_cluster` + Lease RBAC | leader election when daemonset or `replicaCount` > 1 |
| `annotationDiscovery.*`, `resourceDetection`, `profiling` | discovery via `receiver_creator`; `resource_detection` (`k8s_api` default since 0.160); eBPF profiling | — |

Enabling both `kubernetesEvents` and `kubernetesObjects.events` fails the render.

For events in a DaemonSet, use `kubernetesObjects` with only the events
group enabled — one pod holds the Lease `k8s.objects.receiver.opentelemetry.io`.
Values tested on chart 0.173.1 (renders `k8s_objects` with an events watch
and a `k8s_leader_elector` extension; every other group off):

```yaml
mode: daemonset
presets:
  kubernetesEvents:
    enabled: false        # renders nothing in daemonset mode anyway
  kubernetesObjects:
    enabled: true
    watch: false
    core: {enabled: false}
    rbac: {enabled: false}
    storage: {enabled: false}
    networking: {enabled: false}
    autoscaling: {enabled: false, vpa: {enabled: false}}
    policy: {enabled: false}
    apiExtensions: {enabled: false}
    events: {enabled: true}
```

The alternative is a second release with `mode: deployment`,
`replicaCount: 1` and `kubernetesEvents.enabled: true` (no leader election;
fine while it stays one replica). Do not also define your own `k8s_objects`
receiver next to a preset — the preset already renders it.

## Chart gotchas

- `image.repository` has **no default** — the render fails until set. Use
  `ghcr.io/open-telemetry/opentelemetry-collector-releases/opentelemetry-collector-k8s`
  (or `-contrib`), and `command.name: otelcol-k8s` / `otelcol-contrib` to
  match.
- Removing a default: set the key to `null`. Lists are replaced, not merged.
  Presets add to `config`; they cannot remove from it. As a **subchart**,
  `null` does not work (helm#12879) — use `alternateConfig`.
- The stock config enables otlp, jaeger, zipkin and a prometheus self-scrape
  receiver, bound to `${env:MY_POD_IP}`. In DaemonSet mode every default port
  gets a **hostPort**. Null the receivers and pipelines you do not use.
- `health_check` must stay or the probes fail.
- Default `memory_limiter` is 80 % / 25 % of the memory limit; set
  `useGOMEMLIMIT: true`.
- The chart runs as root only when `storeCheckpoints` is on and
  `securityContext` is empty.
- Below chart 0.178.0 a node whose name is all digits fails
  (`host.name must be string`, helm#2250); upgrade, or null `host.name` and
  `k8s.node.name` in the resource config.
- `rewriteDeprecatedComponentNames: true` (default) rewrites old component
  names; set `false` with images older than the renames.
- `extraEnvs`/`extraEnvsFrom` are templated since 0.171.1 — escape literal
  `{{ }}`.

## Chart upgrade notes (0.157 → 0.180)

| Chart | Change |
|---|---|
| 0.160.0 | `k8s_attributes` name (needs collector ≥ 0.146); `resourceDetection` defaults to `k8s_api` (≥ 0.154) |
| 0.161.0 | `service.telemetry.metrics.address` removed — use `readers` |
| 0.162.0 | `rewriteDeprecatedProcessorNames` → `rewriteDeprecatedComponentNames`; the old key is rejected |
| 0.168.0 | `filelog` → `file_log` |
| 0.170.0 | `kubernetesEvents.useK8sEventsReceiver` added (default false, will flip) |
| 0.171.0 | exporters `otlp_grpc` / `otlp_http` (collector ≥ 0.144) |
| 0.174.0 | appVersion 0.161.0 |
| 0.178.0 | resource attributes move to `telemetry.resourceAttributes.{default,extra}`; a map under `config.service.telemetry.resource` still works but is deprecated. Turn a default off with `enabled: false` |
| 0.179.0 | `kubernetesAttributes` preset extracts `container.image.tags` (a list) instead of `container.image.tag`: needs collector ≥ 0.152 with `EmitV1K8sConventions` (default from 0.161); update queries |
| 0.180.0 | `rewriteDeprecatedComponentNames` also renames `hostmetrics` → `host_metrics`: set it `false` on images older than v0.151.0. `presets.hostMetrics.hardenedMode` mounts only /proc and /sys and disables the filesystem scraper |

## k8s_attributes

- Stable since v0.161. RBAC: get/list/watch `pods`, `namespaces`; plus
  `replicasets` for deployment fields, `nodes` for node uid/labels,
  `jobs`/`cronjobs` for those.
- In a DaemonSet set `filter.node_from_env_var` (downward API), or every
  agent caches every pod in the cluster.
- `pod_association` rules run in order, first match wins; the `connection`
  source only works **before** batching or tail sampling.
- Agent/gateway split: agents `passthrough: true` (add pod IP only), gateway
  enriches by `k8s.pod.ip`.
- Large clusters: `watch_sync_period: 0s`; extracting
  deployment/replicaset/job metadata costs memory.
- **Attribute renames (collector ≥ v0.161, gates on by default):**
  `k8s.pod.labels.<k>` → `k8s.pod.label.<k>` (same for node/namespace and
  `annotations` → `annotation`), `container.image.tag` →
  `container.image.tags`. Queries and dashboards using the old names break on
  upgrade; dual-emit with
  `--feature-gates=-processor.k8sattributes.DontEmitV0K8sConventions,processor.k8sattributes.EmitV1K8sConventions`
  during a migration.

## file_log for pod logs

- The `container` operator parses docker, cri-o and containerd formats
  (auto-detect) and **recombines CRI partial lines** (16 KiB pieces) itself —
  no separate concat step. With `include_file_path: true` it derives
  namespace, pod, uid, container and restart count from the path.
- Receiver `max_log_size` 1 MiB, `max_log_size_behavior: split` (or
  `truncate`); the chart sets the recombine limit to 100 KiB.
- `start_at: end` by default — existing content is skipped on first start.
- `storage: file_storage` keeps offsets across restarts; without it a restart
  re-reads or skips.
- Rotation by inode + fingerprint (first 1000 bytes); handles move/create and
  copy/truncate.
- Exclude the collector's own logs, and never read logs that a `debug`
  exporter writes — exponential log explosion.
- Mirror the excludes of the pipeline you replace (noisy containers,
  the logging stack itself) by path glob:
  `/var/log/pods/<namespace>_*/*/*.log`, `/var/log/pods/*/<container>/*.log`.

## Cluster-wide receivers and leader election

| Receiver | Run |
|---|---|
| `k8s_cluster` | once, or with `k8s_leader_elector` |
| `k8s_objects` | once ("must be deployed as one replica") or with `k8s_leader_elector`; `storage` keeps the watch resourceVersion (RWX volume with leader election); watch needs `list`; `kube_api_qps` 5 |
| `k8s_events` (alpha) | once, or leader elector |
| `kubelet_stats`, `host_metrics` | per node; in a Deployment they see one node only |

`k8s_leader_elector` (alpha, in the k8s distro): lease 15s, renew 10s, retry
2s; needs Lease RBAC. Events emitted while the Lease changes hands (rollouts)
are lost.

Kubernetes events carry no body text; the human message is `object.note`
(events.k8s.io/v1) — map it to the backend's message field (see
`backends.md`).

## Target Allocator

- Modes: `consistent-hashing` (default), `least-weighted`, `per-node`
  (DaemonSet only; skips targets without a node).
- ServiceMonitor/PodMonitor/Probe/ScrapeConfig via `prometheusCR`; only the
  CRDs are needed, not Prometheus.
- Security: the default namespace selector is all namespaces and
  `bearerTokenFile` reads are allowed — set `denyFSAccessThroughSMs: true`
  and narrow selectors. Operator < 0.152.0 has an arbitrary-file-read
  advisory (GHSA-cxh2-4639-vmc5).
- Only one `prometheus/*` receiver per collector is supported with the TA.

## Field-tested checks (replacing fluentd/Fluent Bit with the chart)

Run with both pipelines writing for ~15 minutes before cutting over:

1. per-namespace, per-minute row counts equal (allow for the old pipeline's
   buffer flush lag — re-count the same window a few minutes later);
2. `_time`/timestamp is the log's own time, not receive time;
3. a 40 KiB single line from a test pod arrives as one row
   (`head -c 40960 /dev/zero | tr '\0' x`);
4. events arrive with a message, and only once.

Then remove the old flow and confirm its ingest falls to zero.
