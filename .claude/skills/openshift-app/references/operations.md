# Operations Reference

## Table of Contents
- [Routes and TLS](#routes-and-tls)
- [Health Probes](#health-probes)
- [Autoscaling (HPA, KEDA, VPA)](#autoscaling-hpa-keda-vpa)
- [Monitoring](#monitoring)
- [Logging](#logging)
- [Persistent Storage](#persistent-storage)
- [Disruption Budgets and Graceful Shutdown](#disruption-budgets-and-graceful-shutdown)
- [Sidecars and Init Containers](#sidecars-and-init-containers)
- [Serverless (Knative)](#serverless-knative)
- [Multi-Architecture Images](#multi-architecture-images)
- [Resource Management](#resource-management)

---

## Routes and TLS

### TLS Termination Types

| Type | Behavior | Use Case |
|------|----------|----------|
| Edge | TLS terminates at router; traffic to pod is unencrypted | Most common; simplest |
| Passthrough | Encrypted traffic goes straight to pod | Mutual TLS, client certs |
| Re-encrypt | TLS terminated at router; new TLS connection to backend | End-to-end encryption with cert inspection |

**Gotcha**: path-based routing is NOT available with passthrough TLS (router cannot
read request contents).

Re-encrypt requires specifying a `destinationCA` certificate. Missing this causes
silent failures.

### Route Example (Edge TLS)

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: myapp
spec:
  to:
    kind: Service
    name: myapp
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

### Rolling Update Zero-Downtime

A preStop hook with sleep 15-30s eliminates the race condition between pod
termination and HAProxy route deregistration:

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sleep", "15"]
```

Without this, rolling updates cause brief downtime as HAProxy may still route
to terminating pods.

### Gateway API (OCP 4.19+)

- Gateway API CRDs ship by default in OCP 4.19+ (v1.2.1)
- Requires OpenShift Service Mesh (OSSM) 3.x with Envoy underneath
- TCPRoute, TLSRoute, UDPRoute are alpha and NOT supported
- Routes and Gateway API coexist

### Service Mesh 3.2

- Uses Istio 1.27, Kiali 2.17, requires OCP 4.18+
- **OSSM 2.6 EOL: June 30, 2026** -- migration to 3.x is urgent
- **Ambient mode** (OSSM 3.2+): eliminates sidecar proxies, uses node-level ztunnel
  for L4 mTLS and optional Waypoint proxies for L7. Recommended for new installations.

---

## Health Probes

### Startup Probes (Use for Slow-Starting Apps)

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
  # Gives 5 minutes for startup (30 * 10s)
```

After the startup probe succeeds, liveness/readiness probes take over.

### Best Practices

- **Always define readiness probes** in production
- **Liveness probes must be lightweight** -- expensive checks cause false restarts
- **Never depend on external services in liveness probes** (database, cache) -- only
  check if the process itself is alive
- Use the same low-cost HTTP endpoint for both, but set higher `failureThreshold`
  on liveness (pod marked not-ready well before it gets killed)

### OpenShift-Specific Gotchas

- `timeoutSeconds` has **no effect on exec probes** -- OpenShift cannot time out on
  an exec call. Implement timeouts inside the probe script.
- Default values are aggressive: `timeoutSeconds: 1`, `failureThreshold: 3`,
  `initialDelaySeconds: 0` -- JVM apps will be killed before startup without a
  startup probe.

---

## Autoscaling (HPA, KEDA, VPA)

### KEDA (Preferred for Prometheus-Based Scaling)

The Custom Metrics Autoscaler Operator (KEDA) is recommended over HPA for
Prometheus-based scaling because HPA's Prometheus adapter is hard to install on OCP.

Supported triggers: Prometheus, CPU, memory, Apache Kafka, cron.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: myapp-scaler
spec:
  scaleTargetRef:
    name: myapp
  minReplicaCount: 2
  maxReplicaCount: 10
  cooldownPeriod: 300
  triggers:
  - type: prometheus
    metadata:
      serverAddress: https://thanos-querier.openshift-monitoring.svc:9091
      query: sum(rate(http_requests_total{namespace="myns"}[2m]))
      threshold: "100"
    authenticationRef:
      name: keda-prometheus-auth
```

KEDA TriggerAuthentication requires:
1. ServiceAccount with cluster-monitoring-view role
2. Bearer token secret for Prometheus access

### HPA

Requires resource requests to be defined on pods. Without them, HPA cannot compute
utilization percentages.

### VPA (Vertical Pod Autoscaler)

- In-place pod vertical scaling: GA in Kubernetes 1.35 (Dec 2025)
- VPA 1.2+ `InPlaceOrRecreate` mode: attempts resize without restart, falls back
  to eviction
- Use **Recommendation mode first** (not Auto) to observe before acting
- **Never use VPA on its own components** with Auto mode -- causes continuous restarts
- Formula for QPS: `QPS = number_of_VPAs / 30`, burst = 2x QPS

---

## Monitoring

### Enable User Workload Monitoring

Must be explicitly enabled:

```yaml
# ConfigMap in openshift-monitoring namespace
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
```

Creates a separate Prometheus stack in `openshift-user-workload-monitoring`.

### ServiceMonitor

Must be in the same namespace as the application:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
  - port: metrics
    interval: 30s
```

### PrometheusRule

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: myapp-alerts
spec:
  groups:
  - name: myapp
    rules:
    - alert: HighErrorRate
      expr: rate(http_errors_total{namespace="myns"}[5m]) > 0.1
      for: 5m
```

### RBAC

- `monitoring-rules-view`: read PrometheusRules
- `monitoring-rules-edit`: CRUD PrometheusRules
- `monitoring-edit`: all above plus create scrape targets

### Best Practices

- Configure sample limits on ServiceMonitors to prevent cardinality explosions
- Default retention is 15-30 days; integrate with remote storage for longer term
  (VictoriaMetrics, Thanos ObjectStore)

---

## Logging

### Logging 6.x Architecture

Vector replaces Fluentd. LokiStack replaces Elasticsearch. Kibana removed.

Use `ClusterLogForwarder` (observability.openshift.io API group) and LokiStack CRDs.
The `ClusterLogging` CRD is effectively deprecated.

### Migration from 5.x

NOT in-place. Deploy Loki/Vector in parallel, adjust ClusterLogForwarder, run both
stacks during retention window, then retire Elasticsearch.

### Log Input Types

- `application` -- user container logs
- `infrastructure` -- platform components + node journal
- `audit` -- auditd from `/var/log/audit/audit.log`

### RBAC (Logging 6.x)

Explicit cluster roles required for log collection:
- Separate roles for audit, application, and infrastructure logs

### Structured JSON Logging

Use `structuredTypeKey` / `structuredTypeName` in ClusterLogForwarder to route
parsed JSON logs to distinct indices. Use distinct types per log FORMAT, not per
application.

---

## Persistent Storage

### Access Modes

| Mode | Description | Gotcha |
|------|-------------|--------|
| RWO | Single node read-write | If node fails, volume stays assigned -- blocks rescheduling |
| RWX | Multi-node read-write | CephFS supports this; needed for shared data |
| ROX | Multi-node read-only | For shared config/data |

### OpenShift Data Foundation (ODF)

- **Block** (Ceph RBD, RWO): databases, high IOPS
- **File** (CephFS, RWX): shared workloads, logging, monitoring
- **Object** (S3-compatible): backups, data pipelines

CephFS supports online expansion for both RWO and RWX.

### Best Practices

- Always set a default StorageClass (PVCs without explicit storageClassName hang)
- Reserve CPU/memory for ODF storage daemons or use dedicated storage nodes
- Isolate storage traffic with dedicated NICs/VLANs
- Test during recovery scenarios, not just steady state
- Use StatefulSets with anti-affinity for RWO database volumes (HA consideration)

---

## Disruption Budgets and Graceful Shutdown

### PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

### Graceful Shutdown Pattern

```yaml
spec:
  terminationGracePeriodSeconds: 60  # Must >= preStop + app drain time
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["sleep", "15"]  # Wait for HAProxy deregistration
```

**terminationGracePeriodSeconds** must be >= preStop sleep + app drain time.
Default is 30s; increase for apps needing longer cleanup. If exceeded, SIGKILL
disrupts orderly shutdown.

### Istio Sidecar Shutdown

Use `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` annotation and configure
`terminationDrainDuration` (default 5s).

### QoS Classes

Guaranteed QoS (requests == limits) pods have lower eviction priority. Consider
this for critical workloads.

---

## Sidecars and Init Containers

### Native Sidecar Containers (Kubernetes 1.33+ / OCP 4.16+ Beta)

Init containers with `restartPolicy: Always` are native sidecars:
- Start before main containers
- Run alongside them
- Terminate in reverse order AFTER main containers exit

```yaml
initContainers:
- name: proxy
  image: envoy:latest
  restartPolicy: Always  # Makes it a sidecar
  ports:
  - containerPort: 15001
```

Solves the classic Istio sidecar race condition.

**Note**: `terminationGracePeriodSeconds` must account for full reverse-order
shutdown of all sidecars.

---

## Serverless (Knative)

### When to Use

- Bursty/unpredictable traffic
- Event-driven workloads
- Scale-to-zero cost savings

### When NOT to Use

- Long-running services
- Latency-sensitive workloads (cold starts)
- Workloads needing persistent connections

### Scaling Configuration

```yaml
metadata:
  annotations:
    autoscaling.knative.dev/minScale: "1"    # Prevent cold starts
    autoscaling.knative.dev/maxScale: "10"   # Cap costs
```

Defaults: minScale=0 (with scale-to-zero), no maxScale limit.

---

## Multi-Architecture Images

### Builds for OpenShift (OCP 4.17+)

The `multiarch-native-buildah` ClusterBuildStrategy dispatches build jobs to nodes
of each architecture, then consolidates into a manifest list.

### Manual Multi-Arch Build

```bash
podman build --platform linux/amd64,linux/arm64 --manifest myapp:1.0.0 .
podman manifest push myapp:1.0.0 docker://registry.example.com/myapp:1.0.0
```

Tag architecture-specific images explicitly during builds for traceability.

---

## Resource Management

### Best Practices

- Always set resource requests and limits (required if namespace has quotas)
- Guaranteed QoS (requests == limits) for critical workloads
- Always set ephemeral storage requests (prevents surprise evictions)
- emptyDir volumes count against pod ephemeral storage limits

### Gotchas

- If CPU/memory quotas are enabled on namespace, pods without resource requests
  **fail to schedule** unless a LimitRange with `defaultRequest` exists
- Pods can be evicted with 0 ephemeral storage request even at minimal usage
- BestEffort pods (no requests/limits) are evicted first under memory pressure

### Topology Spread

Prefer `topologySpreadConstraints` over pod affinity/anti-affinity:

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: myapp
```

Combine with `podAntiAffinity` for hard requirements.
