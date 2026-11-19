# Sources

Freshened: 2026-10-04 — first version. Every row read at the stated version.

External, versioned claims this skill relies on. The collector ships every two
weeks; re-verify with the skill-improver `freshen` mode at least monthly and
on every collector minor you deploy.

| Source | Ref / URL | Read at | Used for |
|---|---|---|---|
| Collector core CHANGELOG, VERSIONING.md, versions.yaml, docs/release.md | github.com/open-telemetry/opentelemetry-collector | v0.162.0 (2026-09-28) | renames (otlp_grpc/otlp_http, queue_batch), breaking changes, module stability, cadence, no LTS |
| Collector contrib CHANGELOG | github.com/open-telemetry/opentelemetry-collector-contrib | main `7872583` (v0.162.0) | rename timeline, removals, error_mode default, Prometheus translation changes, semconv gates |
| Contrib rename tracker | https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/45339 | 2026-10-04 | full rename list, no alias removal date |
| exporterhelper README | core `exporter/exporterhelper/README.md` | v0.160.0 | sending_queue/retry defaults, sizer, block_on_overflow, wait_for_result vs storage, sending_queue.batch |
| batch / memory_limiter processor READMEs | core `processor/*` | v0.160.0 / v0.162.0 | batch defaults (8192 / 200ms), ordering, GOMEMLIMIT 80 % |
| Batching direction | https://github.com/open-telemetry/opentelemetry-collector/issues/13766, /15047 | 2026-10-04 | batch processor not deprecated; exporter-side batching preferred; no double batching |
| queue_batch deadlock | https://github.com/open-telemetry/opentelemetry-collector/issues/16076 | 2026-10-04 (open) | num_consumers 1 + metadata_keys |
| filestorage README | contrib `extension/storage/filestorage/README.md` | main `7872583` | compaction defaults, fsync, max_size |
| opentelemetry.io collector docs (resiliency, scaling, internal-telemetry, configuration, security) | github.com/open-telemetry/opentelemetry.io `content/en/docs/collector`, `docs/security` | `c7156a1` (2026-10-03) | tiers, LB, alerts, telemetry readers/levels, validate/print-config, hardening |
| Component metadata.yaml stability | contrib component dirs | v0.162.0 | stability table |
| Helm chart README, values.yaml, _config.tpl, UPGRADING.md (+ `helm template` render tests) | github.com/open-telemetry/opentelemetry-helm-charts | `83b0bff6` (chart 0.175.0) | presets, kubernetesEvents renders nothing in daemonset, leader election per mode, gotchas, upgrade notes |
| Operator docs | github.com/open-telemetry/opentelemetry-operator `docs/` | `7a8ddcad` (v0.160.0+) | operator CRDs, Target Allocator modes and security |
| k8sattributes / filelog / k8sobjects / k8scluster / journald READMEs | contrib component dirs | main `7872583` | RBAC, pod_association, node filter, v1 conventions renames, container operator, journald priority and convert_to_semantic_conventions |
| Releases repo manifests, goreleaser, workflows | github.com/open-telemetry/opentelemetry-collector-releases | `3d037de` (2026-10-01) | distributions and their contents, cosign v3 bundles, SBOMs |
| Security advisories | `gh api repos/open-telemetry/<repo>/security-advisories` (collector, contrib, releases, operator, helm-charts) | 2026-10-04 | advisory table and floors |
| Core README "Verifying the images signatures" | core `README.md` | v0.162.0 | cosign verify command |
| ocb docs | opentelemetry.io `docs/collector/extend/ocb.md`, core `cmd/builder/README.md` | `c7156a1` / v0.162.0 | manifest format, strict versioning |
| VictoriaLogs data-ingestion docs | github.com/VictoriaMetrics/VictoriaLogs `docs/victorialogs/data-ingestion/` | v1.53.0-8 | OTLP endpoint, VL-Stream-Fields, VL-Msg-Field list, protobuf only |
| VictoriaMetrics OpenTelemetry/Prometheus integration docs | github.com/VictoriaMetrics/VictoriaMetrics `docs/victoriametrics/integrations/` | v1.153.0 | OTLP no gRPC (#10345), native histograms → vmrange, no RW 2.0 |
| Grafana Mimir HTTP API / out-of-order docs | https://grafana.com/docs/mimir/latest/references/http-api/ | 2026-10-03 | X-Scope-OrgID, out-of-order rejection |
| syslog receiver README + metadata.yaml | contrib `receiver/syslogreceiver/` | main `117c830` (2026-10-17) | beta, contrib only, protocols, `on_error` default `send`, `add_attributes` |
| VictoriaLogs OTLP ingest source | github.com/VictoriaMetrics/VictoriaLogs `app/vlinsert/opentelemetry/opentelemetry.go`, `lib/logstorage/rows.go` (`RenameField`) | `94be0e7` (2026-10-02) | `VL-Msg-Field` renames the first non-empty listed field without removing the body's `_msg` |
| ClickHouse exporter README | contrib `exporter/clickhouseexporter/README.md` | v0.162.0 | what an otlp_http lab cannot test |

## Field observations (RKE2 test cluster, 2026-10-03)

Measured, not documented upstream:

| Observation | How |
|---|---|
| journald receiver defaults to `journalctl --priority info` | receiver startup log, otelcol-contrib v0.162.0 binary on a node |
| With `convert_to_semantic_conventions: true`, VictoriaLogs streams per `process.pid` | side-by-side probe against systemd-journal-upload |
| Kubernetes events have no body; VictoriaLogs stores its placeholder until `VL-Msg-Field: _msg,object.note` | otelcol-k8s 0.160.0 → VictoriaLogs 1.52 |
| Events during a DaemonSet rollout (Lease handover) never arrived | k8s events vs VictoriaLogs, 2026-10-03 21:33 UTC |
| `file_log` + container operator delivers a 40 KiB line as one row; Fluent Bit (`Skip_Long_Lines On`) dropped it | test pod |
| `syslog` receiver: raw line stays in the body; `VL-Msg-Field: message` gave the raw body as `_msg` on 2 of 10 records; `transform` into the body fixed it (21 of 21) | `logger --rfc3164` over UDP, otelcol-contrib 0.160.0 → VictoriaLogs 1.52, 2026-10-11 |
| `externalTrafficPolicy: Cluster` on the syslog LoadBalancer: `net.peer.ip` was a node IP on 4 of 10 lines; `Local`: 20 of 20 real | same test, Cilium BGP LoadBalancer |
| 1000-request queue ≈ 3 min of downtime at ~12 lines/s per node | arithmetic from batch defaults and measured volume |
