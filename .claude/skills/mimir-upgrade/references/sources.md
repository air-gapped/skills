# Sources — mimir-upgrade

Dated index of the authoritative URLs and artifacts behind this skill's claims. `skill-improver freshen` reads
this file, probes each row, and stamps `Last verified`.

## Convention

Each row carries `Source`, `URL`, `What it supports`, `Last verified` (YYYY-MM-DD), `Pinned` (optional). Rows
marked `<!-- ignore-freshen -->` are deliberately not refreshed.

## Most recent pass: 2026-07-21

Skill authored 2026-07-21 from a six-agent research pass. **No lab cluster was available** — every claim is
either upstream-grounded (tagged `[UG]`) or reasoned from chart/source reading (tagged `[RFC]`). Static
verification performed: `helm template` renders of charts 5.7.0/5.8.0/6.0.6/6.1.0, a key-by-key diff of one
render against upstream's golden CI fixture, and a Go probe compiled against Mimir's YAML library to settle the
`null`-semantics question. Nothing was run against a live Mimir.

## Chart artifacts (primary — highest credibility)

| Source | Path / URL | What it supports | Last verified | Pinned |
|---|---|---|---|---|
| `mimir-distributed` chart tarballs | https://grafana.github.io/helm-charts (`helm pull grafana/mimir-distributed --version X.Y.Z`) | Every `[RFC]` claim: values keys, template conditionals, defaults, `Chart.yaml` gates, subchart pins. Extract with `tar xzf … -O mimir-distributed/<path>` | 2026-07-21 | 5.7.0, 5.8.0, 6.0.6, 6.1.0 |
| `classic-architecture.yaml` (in-chart) | `mimir-distributed/classic-architecture.yaml` inside the 6.0.6 / 6.1.0 tarballs | The supported classic opt-out; byte-identical across both; absent in 5.x | 2026-07-21 | 6.0.6 = 6.1.0 |
| Upstream golden CI render | https://github.com/grafana/mimir/tree/mimir-distributed-6.1.0/operations/helm/tests/classic-architecture-values-generated | Proves classic mode is regression-tested upstream; our render matched 79/79 config keys | 2026-07-21 | mimir-distributed-6.1.0 |
| chart CHANGELOG | https://github.com/grafana/mimir/blob/main/operations/helm/charts/mimir-distributed/CHANGELOG.md | Per-release chart changes. **Internally inconsistent** — see per-hop-runbook §7 for four claims contradicted by the tarballs | 2026-07-21 | — |

## Mimir app source and config surface

| Source | URL | What it supports | Last verified | Pinned |
|---|---|---|---|---|
| Mimir CHANGELOG | https://github.com/grafana/mimir/blob/main/CHANGELOG.md | App-level removals/renames for 2.17, 3.0, 3.1 | 2026-07-21 | release-3.1 |
| `cmd/mimir/help-all.txt.tmpl` | https://github.com/grafana/mimir/blob/mimir-3.1.2/cmd/mimir/help-all.txt.tmpl | Complete flag surface + defaults. The **negative** results matter: no `-querier.compare-*`, no fallback counter | 2026-07-21 | mimir-3.1.2 |
| `cmd/mimir/config-descriptor.json` | https://github.com/grafana/mimir/blob/mimir-3.1.2/cmd/mimir/config-descriptor.json | `ingest_storage.enabled` binary default is **false**; `distributor.remote_timeout` default 2s | 2026-07-21 | mimir-3.1.2 |
| `pkg/ingester/ingester.go` | https://github.com/grafana/mimir/blob/mimir-3.1.2/pkg/ingester/ingester.go | `-ingester.push-grpc-method-enabled` flag default is `true` (line ~220) — the null-semantics safety | 2026-07-21 | mimir-3.1.2 |
| `pkg/usagestats/reporter.go` | https://github.com/grafana/mimir/blob/mimir-3.1.2/pkg/usagestats/reporter.go | `-usage-stats.enabled` defaults true; endpoint + 4h interval | 2026-07-21 | mimir-3.1.2 |
| `pkg/storage/ingest/util.go` | https://github.com/grafana/mimir/blob/mimir-3.1.2/pkg/storage/ingest/util.go | `CreateTopic` uses broker default RF (-1); partition-from-instance-ID regex | 2026-07-21 | mimir-3.1.2 |
| `pkg/storage/ingest/version.go` | https://github.com/grafana/mimir/blob/mimir-3.1.2/pkg/storage/ingest/version.go | Kafka record V2; **absent at `mimir-2.16.0`** — the rollback edge | 2026-07-21 | mimir-3.1.2 |

## Official documentation

| Source | URL | What it supports | Last verified | Pinned |
|---|---|---|---|---|
| Migrate Helm chart 5.x → 6.0 | https://grafana.com/docs/helm-charts/mimir-distributed/latest/migration-guides/migrate-helm-chart-5.x-to-6.0/ | The 6.0 procedure, CRD prerequisites, and the "Continue using classic architecture" section. **Snippet is incomplete vs the shipped preset**; contains the `rollout-operator:` vs `rollout_operator:` typo | 2026-07-21 | latest |
| Unified-proxy migration (nginx → gateway) | https://grafana.com/docs/helm-charts/mimir-distributed/v5.8.x/migration-guides/migrate-to-unified-proxy-deployment/ | The full nginx→gateway key mapping. **Only the `v5.8.x` path resolves** — `latest` 404s, `v5.6.x` 502s. **Archive this** | 2026-07-21 | v5.8.x |
| Migrate to ingest storage | https://grafana.com/docs/mimir/latest/set-up/migrate/migrate-ingest-storage/ | The two-cluster blue/green procedure and the doubled-cost warning | 2026-07-21 | latest |
| About Mimir architecture | https://grafana.com/docs/mimir/latest/get-started/about-grafana-mimir-architecture/ | The two supported architectures table, "Ingest storage (preferred)" / "Classic" | 2026-07-21 | latest |
| About classic architecture | https://grafana.com/docs/mimir/latest/get-started/about-grafana-mimir-architecture/about-classic-architecture/ | The "set to be deprecated in a future release" statement — **no removal version named** | 2026-07-21 | mimir-3.1.2 |
| Run production environment with Helm | https://grafana.com/docs/helm-charts/mimir-distributed/latest/run-production-environment-with-helm/ | Names `classic-architecture` a supported preset; also the external-Kafka path that shares `kafka.enabled: false` | 2026-07-21 | latest |
| Configure Kafka backend | https://grafana.com/docs/mimir/latest/configure/configure-kafka-backend/ | Supported backends, `message.max.bytes`, partition rule | 2026-07-21 | latest |
| Perform a rolling update | https://grafana.com/docs/mimir/latest/manage/run-production-environment/perform-a-rolling-update/ | "one ingester at a time", or one whole zone with zone-aware replication | 2026-07-21 | latest |
| Mimir runbooks | https://grafana.com/docs/mimir/latest/manage/mimir-runbooks/ | Alert runbooks; the readiness-gated definition of "caught up" | 2026-07-21 | mimir-3.1.2 |
| Mimir Query Engine reference | https://grafana.com/docs/mimir/latest/references/architecture/mimir-query-engine/ | The four documented MQE-vs-Prometheus divergences | 2026-07-21 | latest |
| mimir-continuous-test | https://grafana.com/docs/mimir/latest/manage/tools/mimir-continuous-test/ | Smoke-test semantics, metric names | 2026-07-21 | latest |
| query-tee | https://grafana.com/docs/mimir/latest/manage/tools/query-tee/ | Differencing flags and comparison metrics | 2026-07-21 | latest |
| About versioning | https://grafana.com/docs/mimir/latest/configure/about-versioning/ | Forward-only data guarantee; **no downgrade commitment** | 2026-07-21 | latest |

## Rollout-operator and Helm behaviour

| Source | URL | What it supports | Last verified | Pinned |
|---|---|---|---|---|
| grafana/rollout-operator | https://github.com/grafana/rollout-operator | Sequencing, `rollout-group`/`OnDelete` requirement, webhook behaviour, `rollout-paused` availability (v0.36.0+) | 2026-07-21 | v0.24.0 → v0.38.0 across the ladder |
| rollout-operator runbooks | https://github.com/grafana/rollout-operator/blob/main/docs/runbooks.md | Warning about restarting the operator pod (ZPDB race) | 2026-07-21 | main |
| Helm CRD best practice | https://helm.sh/docs/chart_best_practices/custom_resource_definitions/ | "No support at this time for upgrading or deleting CRDs using Helm" | 2026-07-21 | — |
| Helm `pkg/kube/ready.go` | https://github.com/helm/helm/blob/main/pkg/kube/ready.go | `statefulSetReady()` short-circuits non-RollingUpdate STS — why `--wait` is not a gate | 2026-07-21 | v3.16.3 |
| kubectl `objectrestarter.go` | https://github.com/kubernetes/kubernetes/blob/master/staging/src/k8s.io/kubectl/pkg/polymorphichelpers/objectrestarter.go | No `OnDelete` guard — disproves the "rollout restart errors" folklore | 2026-07-21 | — |

## Issues and discussions — cited as evidence of absence

| Source | URL | What it supports | Last verified | Pinned |
|---|---|---|---|---|
| #13351 in-place migration | https://github.com/grafana/mimir/issues/13351 | In-place classic→ingest-storage is a **request, not a feature**. Open since 2025-11-05, no maintainer response | 2026-07-21 | OPEN |
| #2807 downgrade support | https://github.com/grafana/mimir/issues/2807 | Downgrade support is undocumented; open and unanswered since 2022-08-22 | 2026-07-21 | OPEN |
| #12012 Kafka best practices | https://github.com/grafana/mimir/issues/12012 | Maintainer declines to advise on Apache Kafka ("we use a different Kafka-compatible backend"); community AutoMQ/Redpanda datapoints | 2026-07-21 | OPEN |
| #14008 capacity planning | https://github.com/grafana/mimir/issues/14008 | Confirms the ingest-storage sizing-doc gap | 2026-07-21 | OPEN |
| #5449 global image registry | https://github.com/grafana/mimir/issues/5449 | No global registry override exists in the chart | 2026-07-21 | OPEN |
| #13354 Kafka disk sizing | https://github.com/grafana/mimir/discussions/13354 | The only real-world datapoint (~50k samples/s → 50 GB / ~12 h) + maintainer retention guidance | 2026-07-21 | — |

## Companion skills

| Source | Path | What it supports | Last verified | Pinned |
|---|---|---|---|---|
| k8s-components-checker | `.claude/skills/k8s-components-checker/references/compat/mimir.md` | **The** authority for chart→app mapping, `kubeVersion` floors, in-scope window. This skill cites it and must never restate it | 2026-07-21 | — |
| prometheus-mimir-grafana | `.claude/skills/prometheus-mimir-grafana/` | Querying Mimir, PromQL, dashboards — the non-upgrade half | 2026-07-21 | — |
| airgap-vetting | `.claude/skills/airgap-vetting/` | Vetting a Kafka platform for air-gap readiness, if ingest storage is ever adopted | 2026-07-21 | — |
