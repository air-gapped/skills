# Fluentd outputs — all 31 plugin types, buffers, image variants

Field names verified from `output_types.go` at 6.7.0 (set unchanged since 6.1.0).

## The 31 Output/ClusterOutput plugin fields

Object stores: `s3` · `gcs` · `azurestorage` · `oss` (Alibaba)
Search/analytics: `elasticsearch` · `opensearch` · `awsElasticsearch`⚠ · `logz`
Log platforms: `loki` · `datadog` · `newrelic` · `logdna`⚠ · `splunkHec` ·
`vmwareLogInsight` · `vmwareLogIntelligence` · `lmLogs` (LogicMonitor) · `gelf` (Graylog)
Streams/queues: `kafka` · `kinesisStream` · `kinesisFirehose` · `sqs` · `rabbitmq` · `redis`
Cloud logs: `cloudwatch`
Protocols: `forward` (fluentd→fluentd) · `syslog` (RFC5424) · `http`
Chat: `mattermost`
Plumbing/testing: `file` · `nullout` · `relabel` (re-route to another Flow label)

⚠ **`awsElasticsearch` and `logdna` are dead fields**: their gems are commented out
of the shipped fluentd image (both 6.1 and master). Using them on stock images
fails configcheck with "unknown output plugin". Custom image required. For Amazon
OpenSearch Service use `opensearch` instead.

## Worked Output specs (official-example-verified)

```yaml
# Loki
loki:
  url: http://loki:3100
  configure_kubernetes_labels: true      # or extract_kubernetes_labels / extra_labels
  labels: {app: "$.kubernetes.labels.app"}   # record-accessor per-field labels
  # tenant: <org-id>; drop_single_key, remove_keys also available
  buffer: {timekey: 1m, timekey_wait: 30s, timekey_use_utc: true}
# NOTE: Loki is order-sensitive — multiple fluentd replicas writing needs tuning (#674)

# Elasticsearch (kube-logging ships a FORKED fluent-plugin-elasticsearch)
elasticsearch:
  host: quickstart-es-http
  port: 9200
  scheme: https
  ssl_verify: false
  user: elastic
  password: {valueFrom: {secretKeyRef: {name: es-elastic-user, key: elastic}}}
  # default index "fluentd"; logstash_format: true + logstash_prefix for daily
  # indices; data streams: data_stream_enable + data_stream_name
  buffer: {timekey: 1m, timekey_wait: 30s}

# S3 (MinIO: add s3_endpoint + force_path_style: "true")
s3:
  aws_key_id: {valueFrom: {secretKeyRef: {name: s3, key: id}}}
  aws_sec_key: {valueFrom: {secretKeyRef: {name: s3, key: secret}}}
  s3_bucket: logs
  s3_region: us-east-1
  path: "logs/${tag}/%Y/%m/%d/"
  buffer: {timekey: 10m, timekey_wait: 30s, timekey_use_utc: true}
  # object stores: prefer LONGER timekey to avoid many small objects

# Kafka
kafka:
  brokers: "kafka:29092"
  default_topic: logs
  use_rdkafka: true          # faster client
  format: {type: json}
  buffer: {tags: topic, timekey: 1m}

# Splunk HEC
splunkHec:
  hec_host: splunk
  hec_port: 8088
  hec_token: {valueFrom: {secretKeyRef: {name: splunk, key: token}}}
  insecure_ssl: true
  index: main
  format: {type: json}

# Remote syslog RFC5424 — TRANSPORT DEFAULTS TO "tls"; set explicitly for plaintext
syslog:
  host: 10.0.0.5
  port: 514
  transport: udp             # tls (default) | tcp | udp
  insecure: true
  buffer: {timekey: 10s, timekey_wait: 1s}

# CloudWatch
cloudwatch:
  aws_key_id: {...}
  aws_sec_key: {...}
  region: eu-north-1
  log_group_name: k8s
  log_stream_name: "${tag}"
  auto_create_stream: true
  buffer: {timekey: 30s}
```

Secret-valued fields universally use
`{valueFrom: {secretKeyRef: {name, key}}}` (or `mountFrom` for file-based).

## Buffer — the fields everyone gets wrong

- `timekey` is **required** in the Buffer struct. Delivery latency ≈
  `timekey + timekey_wait`. `flush_mode` defaults to lazy when timekey is set.
- Default buffer `type: file` on the fluentd StatefulSet PVC — **default 20Gi**
  (`disablePvc: true` switches to emptyDir; hostPath also possible).
- Rendered default **`retry_forever true`** — a dead destination grows the buffer
  until the readiness probe fails the pod (>5000 buffer files or >90% full). For
  destinations where drops beat outage-coupling, set `retry_max_times` +
  `overflow_action`.
- `chunk_limit_size` default 8MB (operator stopped overriding it in 4.7 — tiny
  chunks previously caused "too many open files").
- Other knobs: `total_limit_size`, `flush_interval`, `flush_thread_count`,
  `retry_max_interval`, `timekey_use_utc`.
- Collector side (FluentbitAgent): `Mem_Buf_Limit 5MB` default; durability needs
  `inputTail: {storage.type: filesystem}` + `bufferStorageVolume` + `positiondb`
  (no positiondb ⇒ restart re-reads files ⇒ duplicates). See
  production-hardening.md for the backpressure chain.

## Fluentd image variants — three, not two

`ghcr.io/kube-logging/logging-operator/fluentd:<version>-{base|filters|full}`
(operator-versioned since 5.1; default is `-full`).

| Variant | Contains | Works with |
|---|---|---|
| `-base` | fluentd core + label-router only | forward, file, http, null, relabel, stdout — no filter gems |
| `-filters` | + all filter gems (concat, detect-exceptions, prometheus, dedot, geoip, tag-normaliser, record-modifier, throttle, grok, multi-format, ua-parser, …) | filters but no output gems |
| `-full` | + all output gems incl. two kube-logging git forks: `fluent-plugin-elasticsearch`, `fluent-plugin-syslog_rfc5424` | everything above |

`throttle`/`geoip` need `-filters` or `-full` (not `-base`).

Historically fragile third-party gems (why the forks exist): elasticsearch
(Gem::ConflictError with opensearch, #1251 → forked), syslog_rfc5424 (Ruby kwargs
crash, #1716 → forked), aws-elasticsearch-service + logdna (removed from image).
When an upgrade breaks an output with a Ruby stack trace, suspect gem drift first.

## Flow filters (fluentd), one-liners

concat (multiline join) · dedot (dots in keys) · detectExceptions (stack traces;
excl. tag_normaliser, broken multi-worker) · elasticsearch_genid ·
geoip · grep (regexp/exclude/and/or) · kube_events_timestamp · parser (see
recipes.md) · prometheus (metrics from records) · record_modifier ·
record_transformer · stdout (debug tap) · tag_normaliser (retag
`${namespace_name}.${pod_name}.${container_name}`) · throttle (rate-limit per key)
· useragent. Removed in 5.0: sumologic filter, `enhance_k8s`.
