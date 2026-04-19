# KEDA Operations — deploy, authenticate, observe, harden

## Contents
- [Deploy and upgrade](#deploy-and-upgrade)
- [Components and their jobs](#components-and-their-jobs)
- [Authentication deep dive](#authentication-deep-dive)
- [Observability](#observability)
- [Operator configuration](#operator-configuration)
- [Production hardening checklist](#production-hardening-checklist)

---

## Deploy and upgrade

### Helm (recommended)

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda kedacore/keda \
  --namespace keda --create-namespace \
  --values values.yaml
```

Common values.yaml knobs:

```yaml
operator:
  replicaCount: 2            # 2 for HA with leader election
  name: keda-operator
  revisionHistoryLimit: 5

metricsServer:
  replicaCount: 2            # only 1 is "active" at a time (external.metrics API)
  useHostNetwork: false

webhooks:
  enabled: true
  failurePolicy: Ignore      # set to Fail for strict validation in prod

podIdentity:
  azureWorkload:
    enabled: false
    clientId: ""
    tenantId: ""
  aws:
    irsa:
      enabled: false
      roleArn: ""
  gcp:
    gcpWorkloadIdentity:
      enabled: false
      clientName: ""

env:
  - name: KEDA_RESTRICT_SECRET_ACCESS
    value: "true"
  - name: WATCH_NAMESPACE
    value: ""                # "" = all namespaces; or "team-a,team-b"
  - name: KEDA_SCALEDOBJECT_CTRL_MAX_RECONCILES
    value: "10"

resources:
  operator:
    requests: {cpu: 100m, memory: 100Mi}
    limits:   {cpu: 1, memory: 1Gi}
  metricsServer:
    requests: {cpu: 100m, memory: 100Mi}
    limits:   {cpu: 1, memory: 1Gi}
  webhooks:
    requests: {cpu: 100m, memory: 100Mi}
    limits:   {cpu: 1, memory: 1Gi}

# Leader-election tuning for stable clusters
additionalEnvVars:
  - {name: KEDA_OPERATOR_LEADER_ELECTION_LEASE_DURATION, value: "15s"}
  - {name: KEDA_OPERATOR_LEADER_ELECTION_RENEW_DEADLINE, value: "10s"}
  - {name: KEDA_OPERATOR_LEADER_ELECTION_RETRY_PERIOD, value: "2s"}
```

### YAML manifest install

```bash
kubectl apply --server-side -f \
  https://github.com/kedacore/keda/releases/download/v2.20.0/keda-2.20.0.yaml
```

For environments that don't want the admission webhook:

```bash
kubectl apply --server-side -f \
  https://github.com/kedacore/keda/releases/download/v2.20.0/keda-2.20.0-core.yaml
```

### Upgrades

- **Minor (2.x → 2.y)**: Helm upgrade or `kubectl apply` the new manifest. CRDs
  are part of the chart; `--server-side` avoids CRD conflicts.
- **CRD changes**: check the release notes for new fields. No CRD-breaking
  changes in 2.x so far.
- **CVE patches**: stay within 2 minor versions of latest. CVE-2025-68476 was
  fixed in 2.17.3 / 2.18.3 / 2.19.0+.

### Kubernetes version support

KEDA follows an N-2 support window (e.g., 2.19 supports k8s 1.32–1.34). Check
`keda-docs/content/docs/<version>/deploy.md` for the exact matrix.

---

## Components and their jobs

| Component | Deployment | Job |
|---|---|---|
| `keda-operator` | `deploy/keda-operator` in `keda` ns | Reconciles CRDs, polls triggers for `0↔1` decisions, creates/maintains HPAs and Jobs. |
| `keda-operator-metrics-apiserver` | `deploy/keda-operator-metrics-apiserver` | Serves the `external.metrics.k8s.io/v1beta1` API. HPA reads from it for `1↔N` scaling. |
| `keda-admission-webhooks` | `deploy/keda-admission-webhooks` | Validates ScaledObjects on create/update (dup target, HPA conflict, broken config). |

Only **one** component per cluster can own the `external.metrics.k8s.io`
APIService. If Datadog Cluster Agent or Prometheus Adapter has already claimed
it, KEDA's metrics-apiserver silently fails to serve metrics.

---

## Authentication deep dive

Five common auth patterns. Most real deployments combine two (e.g., a
`TriggerAuthentication` that uses pod identity plus reads one secret).

### 1. Static secret

Simplest. Store creds in a k8s Secret, reference with `secretTargetRef`.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rabbitmq-credentials
  namespace: apps
stringData:
  amqp-host: amqp://user:pw@rabbit:5672/
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: rabbitmq-auth
  namespace: apps
spec:
  secretTargetRef:
    - parameter: host
      name: rabbitmq-credentials
      key: amqp-host
```

### 2. AWS IRSA

Preferred for EKS. Annotate the KEDA operator SA (or the target workload SA
when `identityOwner: workload`) with a role ARN; AWS STS handles the rest.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: sqs-irsa
spec:
  podIdentity:
    provider: aws
    roleArn: arn:aws:iam::123456789:role/keda-sqs-reader
    identityOwner: keda      # use the keda-operator SA's IRSA
```

KEDA operator SA needs:

```yaml
metadata:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/keda-sqs-reader
    eks.amazonaws.com/sts-regional-endpoints: "true"
```

### 3. Azure Workload Identity

Replaces the deprecated `azure` pod identity v1.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: servicebus-wi
spec:
  podIdentity:
    provider: azure-workload
    identityId: <user-assigned-managed-identity-client-id>
```

Helm: `--set podIdentity.azureWorkload.enabled=true
--set podIdentity.azureWorkload.clientId=<client-id>
--set podIdentity.azureWorkload.tenantId=<tenant-id>`.

### 4. GCP Workload Identity

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: pubsub-wi
spec:
  podIdentity:
    provider: gcp
```

KSA annotation: `iam.gke.io/gcp-service-account=sa-name@project.iam.gserviceaccount.com`.
Grant the GSA the minimum roles (e.g., `roles/pubsub.subscriber` for a Pub/Sub
scaler).

### 5. HashiCorp Vault

Pull per-scaler secrets from Vault. Kubernetes auth mode is preferred over
static tokens.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: vault-prom
spec:
  hashiCorpVault:
    address: https://vault.example.com
    authentication: kubernetes
    role: keda-reader
    mount: kubernetes
    credential:
      serviceAccount: /var/run/secrets/kubernetes.io/serviceaccount/token
    secrets:
      - parameter: bearer_token
        path: secret/data/prometheus
        key: token
        type: secretV2
```

KEDA needs `create serviceaccounts/token` permission for the kubernetes auth
mode. In Helm:
`permissions.operator.restrict.allowAllServiceAccountTokenCreation=true`.

### TriggerAuthentication vs ClusterTriggerAuthentication

- Namespace: TriggerAuthentication lives in and only serves ScaledObjects in
  the same namespace. Secrets referenced in `secretTargetRef` must be in that
  namespace.
- Cluster: ClusterTriggerAuthentication can be referenced from any namespace
  via `authenticationRef.kind: ClusterTriggerAuthentication`. Secrets
  referenced in `secretTargetRef` must live in the KEDA operator's namespace
  (usually `keda`), unless `KEDA_CLUSTER_OBJECT_NAMESPACE` is set.
- `KEDA_RESTRICT_SECRET_ACCESS=true` forces ClusterTriggerAuthentication for
  any cross-namespace secret use.

### TLS for scalers

For mTLS (Kafka, private Prometheus, etc.), pass cert material through
`secretTargetRef`:

```yaml
secretTargetRef:
  - parameter: ca              # scaler-specific parameter name; see scaler doc
    name: kafka-tls
    key: ca.crt
  - parameter: cert
    name: kafka-tls
    key: tls.crt
  - parameter: key
    name: kafka-tls
    key: tls.key
```

The actual parameter names vary by scaler — check the scaler's `metadata`
struct for tls-related fields.

---

## Observability

### Prometheus metrics

KEDA operator exposes on `:8080/metrics`, metrics-apiserver on `:9022/metrics`
(or the port configured in Helm).

Key metrics:

- `keda_scaler_errors_total{scaler, scaledobject, namespace, scaler_id}` —
  cumulative scaler failures. Alert on sustained non-zero rate.
- `keda_scaler_metrics_value{scaler, scaledobject, namespace, metric}` —
  last-reported metric value per scaler.
- `keda_scaled_object_errors_total{scaledobject, namespace}` — reconciliation
  errors.
- `keda_resource_total{type, namespace}` — count of ScaledObjects/ScaledJobs.
- `keda_internal_scale_loop_latency_seconds` — how long the polling loop takes.

Example alert rules:

```yaml
- alert: KEDAScalerErrors
  expr: rate(keda_scaler_errors_total[5m]) > 0.01
  for: 10m
  annotations:
    summary: "KEDA scaler {{ $labels.scaler }} for {{ $labels.scaledobject }} is erroring"

- alert: KEDAMetricsAPIUnavailable
  expr: up{job="keda-operator-metrics-apiserver"} == 0
  for: 2m
```

### OpenTelemetry

KEDA 2.12+ emits OTel traces/metrics. Enable with Helm
`operator.otelScraping.enabled=true` (check chart version). Useful for tying
KEDA decisions to downstream scaling latency.

### Probing the external metrics API

```bash
# Is the APIService registered?
kubectl get apiservice v1beta1.external.metrics.k8s.io

# List all available external metrics
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1" | jq

# Get the value KEDA is currently serving for a specific ScaledObject
kubectl get --raw \
  "/apis/external.metrics.k8s.io/v1beta1/namespaces/apps/s0-prometheus-rps?labelSelector=scaledobject.keda.sh%2Fname%3Dorder-api" | jq
```

The metric name on the external API follows the pattern
`s<index>-<type>-<hash>` where `<index>` is the position of the trigger in
`spec.triggers`. Use the label selector
`scaledobject.keda.sh/name=<name>` to narrow it.

---

## Operator configuration

Key environment variables / flags (set via Helm `additionalEnvVars` or
manifest patches):

| Variable / flag | Default | Purpose |
|---|---|---|
| `WATCH_NAMESPACE` | "" | Empty = all namespaces. Comma-separated list restricts scope. |
| `KEDA_OPERATOR_LOG_LEVEL` | `info` | `debug` \| `info` \| `error`. Debug is noisy. |
| `KEDA_HTTP_DEFAULT_TIMEOUT` | `3000` ms | HTTP timeout for HTTP-based scalers (Prometheus, metrics-api). |
| `KEDA_HTTP_MIN_TLS_VERSION` | `TLS12` | `TLS10` \| `TLS11` \| `TLS12` \| `TLS13`. |
| `KEDA_RESTRICT_SECRET_ACCESS` | `false` | `true` limits secret reads to the keda namespace. Forces ClusterTriggerAuthentication for cross-ns secrets. |
| `KEDA_SCALEDOBJECT_CTRL_MAX_RECONCILES` | `5` | Max concurrent ScaledObject reconciles. Raise at scale (100+ ScaledObjects). |
| `KEDA_SCALEDJOB_CTRL_MAX_RECONCILES` | `1` | Same for ScaledJob. |
| `KEDA_CLUSTER_OBJECT_NAMESPACE` | (operator ns) | Override where ClusterTriggerAuthentication's secrets live. |
| `--kube-api-qps` (flag) | `20` | Kubernetes client QPS. Raise for large clusters. |
| `--kube-api-burst` (flag) | `30` | Kubernetes client burst. Raise alongside QPS. |
| `KEDA_HTTP_DISABLE_KEEP_ALIVE` | `false` | Disable HTTP keep-alive to event sources (troubleshooting). |
| `--enable-cert-rotation` (flag) | `true` | Auto-rotate webhook/metrics-server self-signed certs. |
| `--ca-dir` (flag, repeatable) | "" | Additional CA directories trusted by operator. Use for private CAs. |

### HTTP proxy

Set `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` as env vars on **both** the
operator and the metrics-apiserver deployments. Applies to all HTTP-based
scaler calls.

### Multiple KEDA instances in one cluster

Not recommended. When strictly required (regulated-workload isolation), use
`WATCH_NAMESPACE` to scope each operator and deploy into distinct namespaces.
But only **one** instance can own `external.metrics.k8s.io` — the others'
external-metric scalers will fail. Consider using the `metrics-api` scaler
pointing at internal APIs as a workaround, or split clusters.

---

## Production hardening checklist

- [ ] Run 2+ `keda-operator` replicas with leader election (1 active, 1 warm).
- [ ] Run 2+ `keda-operator-metrics-apiserver` replicas (only 1 active, but
      shortens failover).
- [ ] `KEDA_RESTRICT_SECRET_ACCESS=true` enforced.
- [ ] Admission webhook `failurePolicy: Fail` (catch invalid CRs at submit).
- [ ] `securityContext`: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`,
      `capabilities.drop: [ALL]`, `allowPrivilegeEscalation: false`.
- [ ] PodDisruptionBudget `minAvailable: 1` on operator and metrics-server.
- [ ] NetworkPolicy in `keda` namespace: allow apiserver→metrics-server:443;
      allow egress only to event sources; deny east-west.
- [ ] RBAC minimization — avoid `cluster-admin`. Review any chart overrides.
- [ ] ResourceQuota on each tenant namespace:
      `count/scaledobjects.keda.sh: "50"` to cap runaway CR creation.
- [ ] Audit policy rule matching `keda.sh` `create|update|delete` verbs.
- [ ] Alerts on `keda_scaler_errors_total` and
      `keda_scaled_object_errors_total` sustained > 0.
- [ ] Upgrade cadence — stay ≤ 2 minor versions behind latest.
- [ ] Limit who can create/modify `TriggerAuthentication` and
      `ClusterTriggerAuthentication` — these are capable of reading secrets
      and vault paths.
- [ ] Grafana dashboard on keda metrics (community dashboards exist; search
      "KEDA dashboard" on grafana.com).
