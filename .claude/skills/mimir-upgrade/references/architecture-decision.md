# The architecture decision — classic vs ingest storage

The decision that dominates the whole ladder. It lands at chart **6.0**, it is made in your values file, and
getting it wrong produces an ingestion outage that pod status does not reveal.

## Contents
1. [What changed](#1-what-changed)
2. [Classic is supported, shipped, and CI-tested](#2-classic-is-supported-shipped-and-ci-tested)
3. [The two-switch trap](#3-the-two-switch-trap)
4. [The shipped preset, annotated](#4-the-shipped-preset-annotated)
5. [Migrating to ingest storage is a separate project](#5-migrating-to-ingest-storage-is-a-separate-project)
6. [If you adopt Kafka anyway](#6-if-you-adopt-kafka-anyway)
7. [Direction of travel](#7-direction-of-travel)

## 1. What changed

Classic write path: `client → distributor --gRPC push--> ingester → object storage`. The distributor fans each
sample to N ingesters synchronously.

Ingest storage (Mimir 3.0+): `client → distributor --produce--> KAFKA --consume--> ingester → object storage`.
Reads and writes scale independently, ingester restarts resume from an offset, and query load cannot
back-pressure ingestion. [UG]

Chart 6.x makes ingest storage the **default deployment mode**. [UG] The chart's default Mimir config hardcodes
`ingest_storage.enabled: true` **and** `ingester.push_grpc_method_enabled: false`. [RFC]

## 2. Classic is supported, shipped, and CI-tested

Staying classic is not a hack or an undocumented workaround. Four independent upstream signals:

- **The chart ships the preset.** `mimir-distributed/classic-architecture.yaml` sits at the chart root in 6.0.6
  and 6.1.0 (byte-identical between them; absent in 5.x). [UG]
- **The 5.x→6.0 migration guide has a "Continue using classic architecture (disable ingest storage)"
  section.** [UG]
- **The production-deployment doc names it a supported preset.** [UG]
- **Upstream CI regression-tests it** with a golden-manifest tree at
  `operations/helm/tests/classic-architecture-values-generated/`. [UG]

And the engine agrees: **Mimir's own binary default is `ingest_storage.enabled: false`** (`config-descriptor.json`
gives `fieldDefaultValue: false`). Only the chart flips it on. [UG]

Independent static verification performed when this skill was written: rendering the preset on 6.0.6 and 6.1.0
produced clean output with no Kafka objects, and the 6.1.0 render matched upstream's golden CI fixture on
**79/79 config keys**, differing only in release-name/namespace substitution. [RFC]

## 3. The two-switch trap

There are two switches and they are easy to confuse, because the docs use one of them for two opposite intents.

| Key | What it actually does |
|---|---|
| `kafka.enabled` | Only gates whether the chart **deploys** a Kafka StatefulSet/Service/PDB and injects its address. [RFC] |
| `mimir.structuredConfig.ingest_storage.enabled` | **The architecture switch.** [RFC] |

`kafka.enabled: false` **alone** gives you Mimir configured for ingest storage, with the classic push path
disabled (`push_grpc_method_enabled: false`), pointing at no broker. That is a **total ingestion outage**.

The overload is upstream's, not yours: the production doc uses `kafka.enabled: false` to mean *"I bring my own
external Kafka"*, and the migration guide uses it inside the classic snippet to mean *"no Kafka at all"*. Same
key, opposite architectures. Say which one you mean in every plan.

## 4. The shipped preset, annotated

Prefer `-f classic-architecture.yaml` from the chart over pasting keys — you re-read it on every hop and pick up
any upstream change for free. Extract it with
`tar xzf mimir-distributed-<ver>.tgz -O mimir-distributed/classic-architecture.yaml`.

```yaml
kafka:
  enabled: false                 # don't deploy the bundled demo Kafka. NOT the architecture switch.
mimir:
  structuredConfig:
    ingest_storage:
      enabled: false             # THE switch. Restores Mimir's own binary default.
      kafka:
        address: null            # null, not omitted — see the null-semantics note below
        topic: null
        auto_create_topic_default_partitions: null
    distributor:
      remote_timeout: null       # reverts the chart's Kafka-tuned 5s to Mimir's 2s flag default
    ingester:
      push_grpc_method_enabled: null   # chart hardcodes false; null restores the `true` flag default
```

**Why `null` and not omission.** [RFC] The chart deliberately emits literal `key: null` into the rendered config
(chart 5.8.0 CHANGELOG: *"Work around Helm PR 12879 not clearing fields with null, instead setting them to
null"*). Mimir loads config with `go.yaml.in/yaml/v3` + `KnownFields(true)`, where `null` leaves a non-pointer
scalar at its **flag default**. So `push_grpc_method_enabled: null` yields `true`
(`pkg/ingester/ingester.go:220`), not `false`. This was verified by compiling a probe against Mimir's exact YAML
library — **but not against a running Mimir**, so the residual risk is whether a live 3.x rejects
`ingest_storage.kafka.address: null` during `Validate()`. Upstream CI ships this exact config, which makes that
unlikely.

**The docs and the preset disagree — the preset is better.** [UG] The migration guide's snippet writes
`push_grpc_method_enabled: true` (functionally identical to `null`, and arguably more legible) but **omits**
`distributor.remote_timeout: null` and the three `ingest_storage.kafka.*` nulls. Following the doc literally
leaves the distributor on the chart's Kafka-tuned **5s** instead of the **2s** that 5.7.0/5.8.0 effectively ran —
a silent write-path timeout change on an architecture you believe is unchanged.

**Pre-flight assertion for every hop:**

```bash
helm template <rel> <chart.tgz> -f classic-architecture.yaml -f your-values.yaml \
  | yq '.data."mimir.yaml"' \
  | grep -E 'ingest_storage:|enabled:|push_grpc_method_enabled:'
# must show ingest_storage.enabled: false AND push_grpc_method_enabled: null|true
```

**One forward trap:** if anyone trims ingesters to **2 zones** (legal only *with* ingest storage, and only from
chart 6.1.0), flipping back to classic **hard-fails the template** — the zone guard requires ≥3 without ingest
storage. [RFC]

## 5. Migrating to ingest storage is a separate project

The official procedure is **two-cluster blue/green**, not an upgrade step: [UG]

1. Scale out compactors on the existing cluster.
2. Stand up a **second** Mimir on the **same object-storage bucket**, with `compactor.replicas: 0`.
3. Duplicate writes from every client to both clusters.
4. **Wait 12–13 h** — ingesters hold that much in memory/disk and cut blocks every 2 h.
5. Switch read clients; confirm the old query-frontend stops logging `msg="query stats"`.
6. Scale old compactors to 0, then new compactors up **within ~15 minutes** (if the bucket index isn't
   refreshed within ~1 h, reads can fail).
7. Move ruler evaluation, stop writing to the old cluster, `helm uninstall` it.

Upstream opens with: *"This procedure temporarily doubles your ingestion and storage costs, because both
clusters run in parallel and receive duplicated writes."* [UG]

**There is no supported in-place path.** grafana/mimir#13351 requests one — open since 2025-11-05 with no
maintainer response. The operator who filed it said the cost made them *"retain the classic architecture in
mimir v3 too."* [UG]

Mimir does carry three `-ingest-storage.migration.*` flags (dual-write to Kafka *and* ingesters;
ignore-ingest-storage-errors; ingest-storage-max-wait-time), present and **not marked experimental** in 3.0.4 and
3.1.2. [UG] They plainly describe an in-place ramp and are almost certainly how Grafana migrated internally, but
**no doc, changelog, or issue describes their sequence or the ingester-side cutover.** [RFC] Unsupported
territory; do not build a plan on them.

## 6. If you adopt Kafka anyway

What the bundled Kafka actually gives you — worse than "demo only" implies: [RFC]

- **RF=1.** Auto-created topics use the broker's `default.replication.factor`, which the chart never sets → 1 on
  a single broker. A single-replica, single-PVC choke point on the entire write path.
- **`message.max.bytes` never set.** Mimir's producer max record is 15,983,616 B (~15.2 MB); `apache/kafka-native`
  defaults to ~1 MB. Docs tell you to raise the broker to `16000000`; the chart's own Kafka doesn't.
- **5 Gi PVC, 24 h retention, 1 CPU / 1 Gi with no limits, PLAINTEXT only.**
- `kafka.replicas` and `kafka.clusterId` exist in the template but appear in **neither `values.yaml` nor the
  README** — multi-broker is reachable but untested surface.

Requirements if you run a real broker: [UG]

- **Partitions ≥ ingesters in one zone.** Partition assignment derives from the instance-ID regex `-([0-9]+)$`
  (`ingester-zone-a-13` → partition 13); a non-matching ID **fails ingester startup**. Mimir will not expand an
  existing topic, so scaling ingesters past the partition count silently under-delivers capacity. [RFC]
- Pre-create the topic with explicit RF and set `auto_create_topic_enabled: false`, so a misconfigured broker
  can't hand you RF=1.
- **Sizing: no upstream guidance exists** (issues #12012, #14008 open). The only real datapoint is ~50k
  samples/s filling 50 GB in ~12 h ⇒ roughly **2 GB/day per 1k samples/s** at 24 h retention. A maintainer notes
  seconds of retention are theoretically sufficient and 24 h is "very high" — cutting to 2–4 h cuts disk 6–12×.
  Retention is only configurable from chart 6.1.0 (`kafka.logRetentionHours`). [UG]
- **Broker support is narrow.** Documented: Apache Kafka, Confluent, Warpstream, MSK, Azure Event Hub (needs
  `producer-compression=none`). **Redpanda has no upstream statement either way** — Grafana's dev-compose runs
  the Redpanda *console UI* against Apache Kafka brokers, which is easy to misread as an endorsement. A
  maintainer: *"we're not super confident to give advice on running Apache Kafka, since we use a different
  Kafka-compatible backend."* [UG] Vet any candidate with the `airgap-vetting` skill.

Failure semantics: **Kafka down = all writes fail** (no buffering, no fallback). Reads degrade gracefully to
stale data — **except** strong-consistency queries, which the ruler adds automatically for dependent rules
within a group. So a Kafka outage breaks ingestion and chained recording/alerting rules while ad-hoc dashboards
keep serving stale data. [UG]

## 7. Direction of travel

Mimir 3.1.2's docs say classic *"is set to be deprecated in a future release"* and label ingest storage
"(preferred)". [UG] But: **no removal version is announced**, classic is absent from the chart's
deprecated-features list, and by the chart's own policy (removal in the third major release after deprecation)
that clock has not started. [UG]

Reasonable posture for an air-gapped community fleet: walk the chart ladder on classic now, and treat ingest
storage as a separately-scoped project with its own Kafka platform decision — one you may reasonably never take.
Re-check the deprecation status on each `skill-improver freshen` pass.
