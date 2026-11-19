# Sources

Freshened: 2026-11-19 — every row probed at collector v0.165.0 / contrib v0.165.1, chart 0.180.0, operator v0.163.0, VictoriaLogs v1.54.0, VictoriaMetrics v1.156.0, VictoriaTraces v0.13.0.

External, versioned claims this skill relies on. The collector ships every two
weeks; re-verify with the skill-improver `freshen` mode at least monthly and
on every collector minor you deploy.

| Source | Ref / URL | Read at | Used for |
|---|---|---|---|
| Collector core CHANGELOG, VERSIONING.md, versions.yaml, docs/release.md | github.com/open-telemetry/opentelemetry-collector | v0.165.0 (2026-11-06) | renames (otlp_grpc/otlp_http, queue_batch), queue_batch beta, double-batching startup warning, memory_limiter `garbage_collector`, breaking changes, module stability, cadence, no LTS |
| Collector contrib CHANGELOG | github.com/open-telemetry/opentelemetry-collector-contrib | v0.165.1 (2026-11-09) | rename timeline (sql_server, google_client_auth), removals (signalfx receiver, transform `flatten_data`, removed OTTL/filter gates), error_mode default, Prometheus translation changes (PermissiveLabelSanitization locked on v0.164, `__scheme__`/`__metrics_path__` kept v0.165), semconv gates |
| Contrib rename tracker | https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/45339 | 2026-11-19 (open) | full rename list, no alias removal date |
| exporterhelper README | core `exporter/exporterhelper/README.md` | v0.165.0 (defaults unchanged) | sending_queue/retry defaults, sizer, block_on_overflow, wait_for_result vs storage, sending_queue.batch |
| batch / memory_limiter processor READMEs | core `processor/*` | v0.165.0 | batch defaults (8192 / 200ms), ordering, GOMEMLIMIT 80 % |
| Batching direction | https://github.com/open-telemetry/opentelemetry-collector/issues/13766, /15047 | 2026-11-19 (#13766 open; #15047 closed 2026-07-27: "batching processor and/or connector still needed") | batch processor not deprecated; exporter-side batching preferred; no double batching |
| queue_batch deadlock | https://github.com/open-telemetry/opentelemetry-collector/issues/16076 | 2026-11-19 (open) | num_consumers 1 + metadata_keys |
| filestorage README | contrib `extension/storage/filestorage/README.md` | v0.165.1 (defaults unchanged) | compaction defaults, fsync, max_size |
| opentelemetry.io collector docs (resiliency, scaling, internal-telemetry, configuration, security) | github.com/open-telemetry/opentelemetry.io `content/en/docs/collector`, `docs/security` | `7b5cb9f` (2026-11-19) | tiers, LB, alerts, telemetry readers/levels, validate/print-config, hardening |
| Component metadata.yaml stability | contrib component dirs + core CHANGELOG | v0.165.1 | stability table (queue_batch beta, elasticsearch metrics beta, adaptive_tail_sampling alpha) |
| Helm chart README, values.yaml, _config.tpl, UPGRADING.md (+ `helm template` render tests) | github.com/open-telemetry/opentelemetry-helm-charts | `cea4f45a` (chart 0.180.0; `helm template` re-run) | presets, 0.178–0.180 upgrade notes, kubernetesEvents renders nothing in daemonset, leader election per mode, gotchas, upgrade notes |
| Operator docs | github.com/open-telemetry/opentelemetry-operator `docs/` | v0.163.0 (CHANGELOG v0.161–v0.163) | operator CRDs, Target Allocator modes and security, `cgroup_runtime` skips GOMEMLIMIT injection (v0.161) |
| k8sattributes / filelog / k8sobjects / k8scluster / journald READMEs | contrib component dirs | v0.165.1 | RBAC, pod_association, node filter, v1 conventions renames, container operator, journald priority and convert_to_semantic_conventions |
| Releases repo manifests, goreleaser, workflows | github.com/open-telemetry/opentelemetry-collector-releases | v0.165.0 | distributions and their contents, cosign v3 bundles, SBOMs |
| Security advisories | `gh api repos/open-telemetry/<repo>/security-advisories` (collector, contrib, releases, operator, helm-charts) | 2026-11-19 (6 new since 2026-10-04) | advisory table and floors |
| Core README "Verifying the images signatures" | core `README.md` | v0.165.0 | cosign verify command |
| ocb docs | opentelemetry.io `docs/collector/extend/ocb.md`, core `cmd/builder/README.md` | `7b5cb9f` / v0.165.0 | manifest format, strict versioning |
| VictoriaLogs data-ingestion docs | github.com/VictoriaMetrics/VictoriaLogs `docs/victorialogs/data-ingestion/` | v1.54.0 | OTLP endpoint, VL-Stream-Fields, VL-Msg-Field list, body stored as `body` from v1.54.0 (CHANGELOG, PR #1884), protobuf only |
| VictoriaMetrics OpenTelemetry/Prometheus integration docs | github.com/VictoriaMetrics/VictoriaMetrics `docs/victoriametrics/integrations/` | v1.156.0 | OTLP no gRPC (#10345, open 2026-11-19), native histograms → vmrange, no RW 2.0 |
| Grafana Mimir HTTP API / out-of-order docs | https://grafana.com/docs/mimir/latest/references/http-api/ | 2026-11-19 | X-Scope-OrgID, out-of-order rejection |
| syslog receiver README + metadata.yaml | contrib `receiver/syslogreceiver/` | v0.165.1 | beta, contrib only, protocols, `on_error` default `send`, `add_attributes` |
| VictoriaLogs OTLP ingest source | github.com/VictoriaMetrics/VictoriaLogs `app/vlinsert/opentelemetry/opentelemetry.go`, `lib/logstorage/rows.go` (`RenameField`) | v1.52.0 and v1.54.0 | before v1.54 the body is `_msg` and the rename leaves it, giving two `_msg` fields; v1.54.0 stores the body as `body` with `defaultMsgFields = ["body"]`; not in v1.52.2 or v1.53.0 |
| VictoriaTraces CHANGELOG | github.com/VictoriaMetrics/VictoriaTraces | v0.13.0 | OTLP gRPC plaintext unless `-otlpGRPC.tls` |
| ClickHouse exporter README | contrib `exporter/clickhouseexporter/README.md` | v0.165.1 | what an otlp_http lab cannot test |

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
