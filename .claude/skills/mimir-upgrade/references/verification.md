# Verification — proving a hop worked

"Pods are Running" proves nothing. Everything below is passive except §5, which is the only active gate.

Verify from a **separate meta-monitoring Prometheus** where possible — verifying Mimir with Mimir means a
read-path failure blinds you to itself.

## Contents
1. [Phase 0 — baselines before you touch anything](#1-phase-0--baselines-before-you-touch-anything)
2. [Phase 1 — immediately after the upgrade](#2-phase-1--immediately-after-the-upgrade)
3. [Phase 2 — read path](#3-phase-2--read-path)
4. [Phase 3 — write path and sample loss](#4-phase-3--write-path-and-sample-loss)
5. [Phase 4 — the active gate](#5-phase-4--the-active-gate)
6. [Phase 5 — alert-name reconciliation](#6-phase-5--alert-name-reconciliation)
7. [MQE differencing](#7-mqe-differencing)
8. [Ingest storage only](#8-ingest-storage-only)

## 1. Phase 0 — baselines before you touch anything

```promql
# record the value at T-0; §4 compares against it
sum(rate(cortex_distributor_received_samples_total{namespace="$NS"}[5m]))
```

```bash
helm get manifest <rel> -n $NS | grep -oP '(?<=- alert: )\S+' | sort -u > alerts-before.txt
```

Confirm **nothing is already firing**. A pre-existing firing alert makes post-upgrade attribution impossible.

## 2. Phase 1 — immediately after the upgrade

Ring health is the fastest true signal — this is `MimirIngesterUnhealthy` verbatim (`for: 15m`, critical): [RFC]

```promql
min by (cluster, namespace) (cortex_ring_members{state="Unhealthy", name="ingester", namespace="$NS"}) > 0
```

Cross-check interactively at `/ingester/ring`, plus `/distributor/ring`, `/store-gateway/ring`,
`/compactor/ring`, `/ruler/ring`.

Error ratio — `MimirRequestErrors`, threshold 1 %. Note 529 and 598 are excluded upstream as non-errors: [RFC]

```promql
(
  sum by (cluster, namespace, job, route) (rate(cortex_request_duration_seconds_count{namespace="$NS", status_code=~"5..", status_code!~"529|598", route!~"ready|debug_pprof"}[1m]))
  /
  sum by (cluster, namespace, job, route) (rate(cortex_request_duration_seconds_count{namespace="$NS", route!~"ready|debug_pprof"}[1m]))
) * 100 > 1
```

Latency — `MimirRequestLatency`, threshold 2.5 s, on the
`cluster_namespace_job_route:cortex_request_duration_seconds:99quantile` recording rule. [RFC]

Open the **Mimir / Rollout progress** and **Mimir / Overview** dashboards — the two the upstream migration guide
names. [UG]

## 3. Phase 2 — read path

- `MimirSchedulerQueriesStuck`. **Note `MimirFrontendQueriesStuck` was removed at 6.0.6** — don't route on it
  past that hop. [RFC]
- `MimirRulerTooManyFailedQueries` (`for: 5m`, critical, 1 %). [RFC]
- Store-gateway: `MimirStoreGatewayHasNotSyncTheBucket`, `MimirStoreGatewayNoSyncedTenants`,
  `MimirStoreGatewayTooManyFailedOperations`. [RFC]
- **`MimirQueriesFailing` does not exist** in the 6.1.0 mixin. Don't write a runbook against it. [RFC]

**Smoke query set.** There is no upstream-defined set; this one is constructed to cross every MQE code path the
docs name as divergent. Run each as instant *and* range, pre- and post-hop, and diff: [RFC]

| Query | Exercises |
|---|---|
| `up` | selector only |
| `sum by (job) (rate(cortex_request_duration_seconds_count[5m]))` | streaming aggregation |
| `topk(5, sum by (pod) (rate(cortex_ingester_ingested_samples_total[5m])))` | **documented non-determinism** on value ties |
| `cortex_ingester_memory_series * on (pod) group_left() up` | binary-op early-abort optimisation |
| `up unless on (pod) cortex_ingester_memory_series` | narrow-selector handling (changed at 3.1) |
| `histogram_quantile(0.99, sum by (le) (rate(cortex_request_duration_seconds_bucket[5m])))` | histogram path |
| `max_over_time(sum(rate(cortex_distributor_received_samples_total[5m]))[24h:5m])` | memory-limit path |
| `up @ end() offset 1h` | `@`/offset/timestamp optimisation |
| `rate(cortex_ingester_memory_series[5m])` | annotation emission (MQE omits some) |

**6.1.0 hop only — the four query-plan-version alerts.** They **are expected to fire during the rollout**; the
gate is that they clear within 15 min of the last querier going Ready. [RFC]

```promql
cortex_querier_maximum_supported_query_plan_version{namespace="$NS"}                                   # all queriers must converge
cortex_query_frontend_querier_ring_calculated_maximum_supported_query_plan_version{namespace="$NS"} == -1   # must not persist
```

If `-1` persists past 5 min, check `/querier/ring` (new at 3.1) on the query-frontends and grep their logs for
`could not compute maximum supported query plan version`.

## 4. Phase 3 — write path and sample loss

**No shipped mixin alert covers sample loss.** There is no alert on `cortex_discarded_samples_total` and none on
distributor-vs-ingester divergence, so this PromQL is yours to author: [RFC]

```promql
# discards rising vs an hour ago, by reason
sum by (reason) (rate(cortex_discarded_samples_total{namespace="$NS"}[5m]))
  > 1.2 * sum by (reason) (rate(cortex_discarded_samples_total{namespace="$NS"}[5m] offset 1h))
```

```promql
# ingestion continuity vs the Phase-0 baseline; expect ~1.0, alert <0.95 or >1.05 sustained 15m
sum(rate(cortex_distributor_received_samples_total{namespace="$NS"}[5m]))
  / sum(rate(cortex_distributor_received_samples_total{namespace="$NS"}[5m] offset 1h))
```

```promql
# fan-out ratio: ~RF (3.0 by default) and FLAT across the upgrade
sum(rate(cortex_ingester_ingested_samples_total{namespace="$NS"}[5m]))
  / sum(rate(cortex_distributor_received_samples_total{namespace="$NS"}[5m]))
```

Confirm the fleet's actual `replication_factor` first (Step 0 fact #2). **Under ingest storage this ratio changes
meaning** — each partition is consumed by one ingester, not RF copies — so re-baseline it after a cutover rather
than reading the shift as a regression.

Also watch `cortex_discarded_requests_total`, `cortex_discarded_exemplars_total`,
`cortex_distributor_instance_rejected_requests_total`, `cortex_ingester_instance_rejected_requests_total`, and
the block-shipping alerts (`MimirIngesterNotShippingBlocks` at 6.1.0; **`MimirIngesterHasNotShippedBlocks`** at
≤6.0.6 — the rename is in §6).

## 5. Phase 4 — the active gate

Everything above is passive. This is the only check that *proves* write→read→correct-result works.

**`helm test <release> -n $NS`** runs the chart's smoke-test Job (annotated `helm.sh/hook: test`, so it never
runs on install/upgrade). It writes, queries back, and compares results through the gateway, exiting non-zero on
failure. [RFC] It uses the regular Mimir image with `-target=continuous-test`, so there is nothing extra to
stage.

**Better: enable `continuous_test` *before* the hop** and leave it running across, so you get a time series
rather than a point sample:

```yaml
continuous_test:
  enabled: true
  runInterval: 1m      # tighten from the 5m default for the upgrade window
  numSeries: 1000
  maxQueryAge: 48h
```

Gate on all three staying flat at zero across the window — watch the raw expressions, not the alerts, since two
of them carry `for: 1h`: [UG]

```promql
sum by(cluster, namespace, test) (rate(mimir_continuous_test_writes_failed_total[5m])) > 0
sum by(cluster, namespace, test) (rate(mimir_continuous_test_queries_failed_total[5m])) > 0
sum by(cluster, namespace, test) (rate(mimir_continuous_test_query_result_checks_failed_total[10m])) > 0
```

The third is the **correctness** signal — it is what catches an MQE result regression.

On ingest storage from 6.0.x, add `-tests.ingest-storage-record.enabled` (validates the V2 record format against
live write requests). [UG]

Note: `grafana/mimir-continuous-test` is **no longer a separate image** — it has been a module of the main image
since at least 5.7.0, so a mirrored copy is probably unused. Confirm nobody overrode `continuous_test.image`
before dropping it from your mirror. [RFC]

## 6. Phase 5 — alert-name reconciliation

Alert counts per chart: 5.7.0=97, 5.8.0=103, 6.0.6=100, **6.1.0=121**. [RFC]

```bash
helm get manifest <rel> -n $NS | grep -oP '(?<=- alert: )\S+' | sort -u > alerts-after.txt
comm -23 alerts-before.txt alerts-after.txt   # gone: dead Alertmanager routes / silences
comm -13 alerts-before.txt alerts-after.txt   # new: unrouted, pages nobody
```

**Chart 6.1.0 renames ~22 alerts.** Every Alertmanager route, silence, inhibition, and runbook anchor keyed on
an old name goes dead. Only relevant if you vendor the mixin (Step 0 fact #4). [RFC]

| Old (≤6.0.6) | New (6.1.0) |
|---|---|
| `MimirIngesterHasNotShippedBlocks` | `MimirIngesterNotShippingBlocks` |
| `MimirIngesterHasNotShippedBlocksSinceStart` | `MimirIngesterNotShippingBlocksSinceStart` |
| `MimirIngesterTSDBCheckpointCreationFailed` | `MimirIngesterTSDBCheckpointCreateFailed` |
| `MimirIngesterTSDBCheckpointDeletionFailed` | `MimirIngesterTSDBCheckpointDeleteFailed` |
| `MimirIngesterLastConsumedOffsetCommitFailed` | `MimirIngesterOffsetCommitFailed` |
| `MimirIngesterFailedToReadRecordsFromKafka` | `MimirIngesterKafkaReadFailed` |
| `MimirIngesterFailsToProcessRecordsFromKafka` | `MimirIngesterKafkaProcessingFailed` |
| `MimirIngesterStuckProcessingRecordsFromKafka` | `MimirIngesterKafkaProcessingStuck` |
| `MimirStartingIngesterKafkaReceiveDelayIncreasing` | `MimirStartingIngesterKafkaDelayGrowing` |
| `MimirStrongConsistencyOffsetNotPropagatedToIngesters` | `MimirStrongConsistencyOffsetMissing` |
| `MimirKafkaClientBufferedProduceBytesTooHigh` | `MimirKafkaClientProduceBufferHigh` |
| `MimirCompactorHasNotSuccessfullyRunCompaction` | `MimirCompactorNotRunningCompaction` |
| `MimirCompactorHasNotSuccessfullyCleanedUpBlocks` | `MimirCompactorNotCleaningUpBlocks` |
| `MimirCompactorFailingToBuildSparseIndexHeaders` | `MimirCompactorBuildingSparseIndexFailed` |
| `MimirCompactorSkippedUnhealthyBlocks` | `MimirCompactorSkippedBlocks` |
| `MimirDistributorReachingInflightPushRequestLimit` | `MimirDistributorInflightRequestsHigh` |
| `MimirAlertmanagerPartialStateMergeFailing` | `MimirAlertmanagerStateMergeFailing` |
| `MimirServerInvalidClusterValidationLabelRequests` | `MimirServerInvalidClusterLabelRequests` |
| `MimirClientInvalidClusterValidationLabelRequests` | `MimirClientInvalidClusterLabelRequests` |
| `MimirHighGRPCConcurrentStreamsPerConnection` | `MimirHighGRPCStreamsPerConnection` |

Also: `MimirFrontendQueriesStuck` and `MimirBlockBuilderLagging` were **removed** at 6.0.6; 5.8.0 added
`MimirGoThreadsTooHigh`, `MimirHighVolumeLevel1BlocksQueried`, and the block-builder family. [RFC]

**Expect `MimirRingMembersMismatch` to flap through every ingester zone roll** — pods drop out of `up` before
their ring entries expire (`heartbeat_timeout: 10m`, `unregister_on_shutdown: false`). Silence it for the
maintenance window rather than treating it as a gate. [RFC]

## 7. MQE differencing

**No in-process differencing exists.** There is no `-querier.compare-*` flag, no query-mirroring mode, and — the
part that bites — **no counter for engine fallback**, so you cannot alert on "MQE silently deferred to the
Prometheus engine". [RFC] Both tiers carry `-enable-query-engine-fallback` defaulting to `true`.

The supported method is **`query-tee`**, which the chart does **not** ship. Rig it yourself: [RFC]

1. Mirror `grafana/query-tee`, tag pinned to the Mimir app version of the hop.
2. Stand up **two query paths against the same backing storage** — a second query-frontend + querier pair with
   `-querier.query-engine=prometheus` and `-querier.enable-query-engine-fallback=false` (fallback off, or your
   control path silently becomes MQE for exactly the queries you most want to compare).
3. Run query-tee in front with `-proxy.compare-responses=true` and
   `-proxy.value-comparison-tolerance=0.000001`. Leave `-proxy.compare-exact-error-matching` **off** — MQE's
   documented annotation and duplicate-series divergences would otherwise be pure noise. The tolerance is
   essential: streaming vs non-streaming aggregation reorders float accumulation, so bit-exact equality is the
   wrong test.
4. Gate on `sum by (secondary_backend, route) (rate(cortex_querytee_responses_compared_total{result="fail"}[5m]))`.

**Whitelist the four documented divergences:** [UG] `topk`/`bottomk` tie-breaking (Prometheus itself is
non-deterministic here); missing metric-validation annotations; absent "found duplicate series for the match
group" errors in some edge cases; early abort of binary-op evaluation when MQE can prove no series result.

**Timing:** since MQE is querier-default from **2.17 (chart 5.8.0)**, this exercise belongs at hop 1. If you want
a true Prometheus-engine control, either build the rig before 5.8.0 or pin `-querier.query-engine=prometheus`
through the hop and flip it as a separate change.

## 8. Ingest storage only

Skip this section entirely on classic.

- **`MimirFewerIngestersConsumingThanActivePartitions`** (`for: 15m`, critical). Unconsumed partitions mean
  *"data missing from the short-term read path and potential data loss."* Inspect at `/ingester/partition-ring`.
  [UG]
- **"Caught up" has an exact definition, and it is enforced by the readiness probe.** An ingester does not become
  ACTIVE or pass readiness until measured lag is below `-ingest-storage.kafka.max-consumer-lag-at-startup`. [UG]
  This is the one place where "the pod is Ready" genuinely proves something.
- Steady-state lag — `MimirRunningIngesterReceiveDelayTooHigh` (>120 s for 3m, and >30 s for 15m, both
  critical), on `cortex_ingest_storage_reader_receive_delay_seconds` split by `phase="starting"|"running"`.
  **"Caught up" = this steady and < 30 s.** [RFC]
- **Strongest no-loss signal in the stack:** `MimirIngesterMissedRecordsFromKafka`, critical, **no `for:` clause
  — it fires instantly.** [RFC]
  ```promql
  increase(cortex_ingest_storage_reader_missed_records_total{namespace="$NS"}[10m]) > 0
  ```
  The ingester logs the gap as `there is a gap in consumed offsets`.
- `MimirIngesterKafkaProcessingStuck` carries a backwards-compat `or` between
  `cortex_ingest_storage_reader_records_total` (old) and `..._requests_total` (new). **Mid-upgrade both names may
  exist in your TSDB** — any hand-written lag query must handle both or it silently returns no data on one side
  of the rollout. [RFC]
- Best single end-to-end gauge, though no shipped alert uses it:
  `cortex_ingest_storage_reader_receive_and_consume_delay_seconds` (distributor receipt → ingester ingestion).
  [UG]
- **Kafka-side consumer lag is not covered by any Mimir metric.** With a real broker you need broker-side lag
  exported separately — and that exporter is its own air-gap item. [RFC]
