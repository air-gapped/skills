# KEDA Scalers — Catalog

KEDA ships 70+ scalers. This catalog groups them by signal source with the
minimal trigger block, essential fields with defaults, and gotchas per scaler.
All snippets show only the `triggers:` list item — wrap in a `ScaledObject` or
`ScaledJob`.

## Contents

- [Compute / resource](#compute--resource)
- [Time-based](#time-based)
- [Cloud queues](#cloud-queues)
- [Self-hosted queues and brokers](#self-hosted-queues-and-brokers)
- [Streaming](#streaming)
- [Databases and caches](#databases-and-caches)
- [Metrics systems](#metrics-systems)
- [HTTP / generic](#http--generic)
- [CI/CD runners](#cicd-runners)
- [Cloud compute and storage](#cloud-compute-and-storage)
- [Predictive](#predictive)
- [Selection decision tree](#selection-decision-tree)

---

## Compute / resource

Resource-metric scalers use the Kubernetes metrics-server, not KEDA's external
metrics server. They **cannot drive scale-to-zero on their own** (HPA requires
`minReplicas ≥ 1` for resource metrics).

### cpu / memory

```yaml
- type: cpu
  metricType: Utilization   # or AverageValue
  metadata:
    value: "70"             # % utilization or absolute (e.g., "500m")
    containerName: app      # optional; defaults to all
```

Memory identical, `type: memory`, `value: "1Gi"` for AverageValue.

### kubernetes-workload

Scale based on pod count matching a selector — a cheap internal signal.

```yaml
- type: kubernetes-workload
  metadata:
    podSelector: app=queue-processor
    value: "5"              # target pods per replica metric
    activationValue: "1"
```

---

## Time-based

### cron

Scale to a fixed replica count during a time window. Non-active windows yield
no opinion — other triggers may still scale up. Overlapping cron triggers
combine as max (not sum).

```yaml
- type: cron
  metadata:
    timezone: Europe/Stockholm    # IANA name; required
    start: "0 7 * * 1-5"          # cron expr — activate
    end: "0 18 * * 1-5"           # cron expr — deactivate
    desiredReplicas: "10"         # string in YAML, parsed as int
```

Gotchas:
- `start` and `end` must differ.
- Overnight spans (22:00→06:00) can behave oddly; split into two triggers
  (22:00→23:59 and 00:00→06:00).
- `desiredReplicas` is a floor when active, not a ceiling.

---

## Cloud queues

### aws-sqs-queue

```yaml
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
    queueLength: "30"             # target messages per replica (default 5)
    awsRegion: us-east-1
    scaleOnInFlight: "true"       # count in-flight (default true)
    scaleOnDelayed: "false"       # count delayed (default false)
  authenticationRef:
    name: aws-irsa
```

Gotcha: the field is `queueURL`, not `queueUrl`.

### aws-kinesis-stream

```yaml
- type: aws-kinesis-stream
  metadata:
    streamName: my-stream
    shardCount: "4"               # target open shards per replica (default 2)
    awsRegion: us-west-2
```

### azure-servicebus

```yaml
- type: azure-servicebus
  metadata:
    queueName: orders             # OR topicName+subscriptionName, not both
    messageCount: "20"            # default 5
    connection: my-connection     # from TriggerAuthentication secret
    operation: sum                # sum|avg|max across multiple matches
```

### azure-queue

```yaml
- type: azure-queue
  metadata:
    queueName: tasks
    queueLength: "10"             # default 5
    queueLengthStrategy: all      # all | visibleonly
    connection: DefaultEndpointProtocol=https;...
```

### azure-eventhub

```yaml
- type: azure-eventhub
  metadata:
    unprocessedEventThreshold: "100"  # default 64
    consumerGroup: my-group
    connection: Endpoint=sb://...
```

### gcp-pubsub

```yaml
- type: gcp-pubsub
  metadata:
    subscriptionName: my-subscription
    value: "30"                   # target backlog per replica (default 10)
    mode: SubscriptionSize
```

---

## Self-hosted queues and brokers

### rabbitmq

```yaml
- type: rabbitmq
  metadata:
    protocol: amqp                # amqp | http | auto
    host: amqp://user:pw@rabbit:5672
    queueName: tasks
    mode: QueueLength             # QueueLength | MessageRate | DeliverGetRate
    value: "20"
  authenticationRef:
    name: rabbitmq-auth
```

Gotcha: `mode: Unknown` (the implicit default in some examples) does not scale.
Always set `mode`.

### apache-kafka (kafka-go, current)

```yaml
- type: apache-kafka
  metadata:
    bootstrapServers: kafka-0:9092,kafka-1:9092
    consumerGroup: my-group
    topic: events                 # optional; omit for all topics in group
    lagThreshold: "50"            # target lag per partition (default 10)
    activationLagThreshold: "1"
    offsetResetPolicy: latest
    sasl: scram_sha512            # none | plaintext | scram_sha256 | scram_sha512 | aws_msk_iam
    tls: enable                   # enable | disable
```

Gotchas:
- `lagThreshold` is per-partition; high values give less aggressive scaling.
- `allowIdleConsumers` and `limitToPartitionsWithLag` are mutually exclusive.
- MSK IAM needs `sasl: aws_msk_iam` plus AWS credentials via TriggerAuthentication.

### kafka (legacy native scaler)

Use `apache-kafka` for new deployments; `kafka` is the older scaler retained for
compatibility.

### solace-event-queue, pulsar, nats-jetstream, nats-streaming, beanstalkd, activemq, artemis, ibmmq

Similar shape — connection URL plus `queueName`/`stream`/`tube` plus a
`*Threshold`/`*Length` field. See upstream docs for the exact fields.

---

## Streaming

Kafka is covered above. Azure Event Hub is covered under cloud queues.

### redis-streams

```yaml
- type: redis-streams
  metadata:
    addresses: redis-0:6379,redis-1:6379
    stream: events
    consumerGroup: workers
    lagThreshold: "20"
```

---

## Databases and caches

### redis (lists)

```yaml
- type: redis
  metadata:
    address: redis.apps:6379
    listName: task_queue
    listLength: "30"
    databaseIndex: "0"
    enableTLS: "false"
    unsafeSsl: "false"            # true only for testing
```

Variants: `redis-cluster-lists` (cluster), `redis-sentinel-lists` (sentinel).

### postgresql / mysql / mssql

```yaml
- type: postgresql
  metadata:
    host: postgres
    port: "5432"
    userName: app
    passwordFromEnv: DB_PASS      # from pod env
    dbName: appdb
    sslmode: disable
    query: SELECT COUNT(*) FROM jobs WHERE status='pending'
    targetQueryValue: "100"
```

Query must return a single numeric value. Same shape for MySQL and MSSQL with
their respective field variants (e.g., `database` for MSSQL).

### mongodb

```yaml
- type: mongodb
  metadata:
    connectionStringFromEnv: MONGO_URI
    dbName: mydb
    collection: orders
    query: '{"status":"pending"}'
    queryValue: "50"
```

### elasticsearch, cassandra, couchdb, arangodb, etcd, influxdb

All query-shaped: connection + query + target. Exact field names vary.

---

## Metrics systems

### prometheus

The swiss army knife — any numeric PromQL expression becomes a scaling metric.

```yaml
- type: prometheus
  metadata:
    serverAddress: http://prometheus.monitoring:9090
    query: sum(rate(http_requests_total{service="api"}[1m]))
    threshold: "200"
    activationThreshold: "10"
    ignoreNullValues: "true"      # default true → null treated as 0
    unsafeSsl: "false"
    customHeaders: "X-Scope-OrgID=tenant-a"   # Cortex/Mimir
```

Gotchas:
- Return value must be a single scalar. Wrap in `sum(...)` if the query would
  return a vector.
- `ignoreNullValues: false` scales down (or rather, makes the trigger inactive)
  when the query returns null — use this if missing data means "no load".
- For Mimir/Cortex multitenancy, pass the tenant header via `customHeaders`.

### datadog

```yaml
- type: datadog
  metadata:
    query: sum:trace.web.request{env:prod}.as_rate()
    queryValue: "1000"
    activationQueryValue: "100"
    age: "120"                    # max age of metric in seconds
```

### new-relic, dynatrace, azure-monitor, aws-cloudwatch, gcp-stackdriver, splunk, graphite, loki

All follow the "query + threshold" pattern. See the upstream scaler doc for the
exact field names. Azure Monitor example:

```yaml
- type: azure-monitor
  metadata:
    subscriptionId: abc123
    resourceGroupName: my-rg
    resourceName: my-app
    resourceType: Microsoft.Web/sites
    metricName: RequestCount
    targetValue: "1000"
```

---

## HTTP / generic

### metrics-api

Scale off any HTTP endpoint returning JSON. A JSON path tells KEDA where to
find the numeric value.

```yaml
- type: metrics-api
  metadata:
    targetValue: "100"
    url: http://my-api:8080/metrics/queue-depth
    valueLocation: data.queue.depth
    method: GET
```

Use this for in-house metrics not exposed to Prometheus.

### external / external-push

Delegate scaling logic entirely to a custom gRPC service.

```yaml
- type: external
  metadata:
    scalerAddress: custom-scaler.apps:6000
    enableTLS: "false"
```

Reach for this when none of the built-in scalers fit. Implement the
`externalscaler.proto` gRPC service and return custom metric values.

---

## CI/CD runners

### github-runner

```yaml
- type: github-runner
  metadata:
    owner: myorg
    runnerScope: org               # org | repo | enterprise
    labels: self-hosted,linux
    targetWorkflowQueueLength: "1"
  authenticationRef:
    name: github-token-auth
```

### gitlab-runner, forgejo-runner, azure-pipelines

Same shape — project/pool identifier plus target queue length.

---

## Cloud compute and storage

### aws-dynamodb

Scale based on consumed read/write capacity or item count.

```yaml
- type: aws-dynamodb
  metadata:
    tableName: my-table
    awsRegion: us-east-1
    keyConditionExpression: "id = :id"
    expressionAttributeNames: '{"#k":"id"}'
    expressionAttributeValues: '{":id":{"S":"abc"}}'
    targetValue: "100"
```

### aws-dynamodb-streams

```yaml
- type: aws-dynamodb-streams
  metadata:
    tableName: my-table
    awsRegion: us-west-2
    shardCount: "2"
```

### azure-blob

Scale by object count in a container.

```yaml
- type: azure-blob
  metadata:
    blobContainerName: uploads
    blobCount: "100"
    accountName: mystorage
    connection: DefaultEndpointProtocol=https;...
```

### gcp-storage, gcp-cloudtasks, azure-pipelines, azure-log-analytics, azure-application-insights, azure-data-explorer

Follow same patterns — connection/resource identifier plus target.

---

## Predictive

### predictkube

ML-based; requires historical data and a PredictKube deployment.

```yaml
- type: predictkube
  metadata:
    predictHorizon: 2m
    historyTimeWindow: 7d
    prometheusAddress: http://prometheus:9090
    query: sum(rate(http_requests_total[1m]))
    threshold: "200"
```

Useful for workloads with a regular pattern (diurnal traffic, weekday batch)
where reactive scaling is too slow.

---

## Selection decision tree

```
Signal source?
├─ HTTP request rate/concurrency      → KEDA HTTP Add-on (HTTPScaledObject)
│                                        or prometheus on RPS query
├─ Time-of-day                        → cron
├─ Cloud queue
│   ├─ AWS SQS                        → aws-sqs-queue
│   ├─ AWS Kinesis                    → aws-kinesis-stream
│   ├─ Azure Service Bus              → azure-servicebus
│   ├─ Azure Storage Queue            → azure-queue
│   ├─ Azure Event Hub                → azure-eventhub
│   └─ GCP Pub/Sub                    → gcp-pubsub
├─ Self-hosted broker
│   ├─ RabbitMQ                       → rabbitmq
│   ├─ Kafka                          → apache-kafka
│   ├─ Pulsar                         → pulsar
│   ├─ NATS JetStream                 → nats-jetstream
│   ├─ Redis list                     → redis
│   ├─ Redis stream                   → redis-streams
│   ├─ ActiveMQ / Artemis / IBM MQ    → corresponding scaler
│   └─ Solace                         → solace-event-queue
├─ Database
│   ├─ Postgres/MySQL/MSSQL query     → postgresql / mysql / mssql
│   ├─ MongoDB count                  → mongodb
│   ├─ Elasticsearch count            → elasticsearch
│   └─ InfluxDB series                → influxdb
├─ Metric store
│   ├─ Prometheus (most flexible)     → prometheus
│   ├─ Datadog / New Relic / Dynatrace→ corresponding scaler
│   ├─ CloudWatch / Stackdriver       → aws-cloudwatch / gcp-stackdriver
│   └─ Azure Monitor / Log Analytics  → azure-monitor / azure-log-analytics
├─ Internal REST metric               → metrics-api (with valueLocation JSONPath)
├─ CI/CD runner backlog               → github-runner / gitlab-runner / forgejo-runner
├─ Pod count signal                   → kubernetes-workload
├─ Predictive pattern                 → predictkube
└─ None of the above                  → external (implement a custom gRPC scaler)

Plus: CPU/memory refinement           → cpu / memory (pair with an event trigger)
```

## Cross-cutting gotchas

- Always check the scaler's Go source under
  `keda/pkg/scalers/<name>_scaler.go` for the authoritative field names — some
  docs lag behind. The `metadata` struct tags show validators.
- Scalers that support `activationValue`/`activationThreshold` use it only for
  the `0→1` transition. It does nothing when `minReplicaCount ≥ 1`.
- Cloud scalers (AWS/Azure/GCP) prefer pod identity (IRSA, Workload Identity)
  over static secrets — see `references/operations.md`.
- `unsafeSsl: "true"` is for testing only. Use a `TriggerAuthentication` with
  a proper CA bundle in production.
