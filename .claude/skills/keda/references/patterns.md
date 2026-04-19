# KEDA Patterns — advanced scaling, HTTP, GitOps, cost

## Contents
- [HPA behavior tuning](#hpa-behavior-tuning)
- [Multi-trigger semantics and scalingModifiers](#multi-trigger-semantics-and-scalingmodifiers)
- [Cron patterns](#cron-patterns)
- [ScaledObject vs ScaledJob decision](#scaledobject-vs-scaledjob-decision)
- [KEDA HTTP Add-on](#keda-http-add-on)
- [GitOps with Argo CD and Flux](#gitops-with-argo-cd-and-flux)
- [KEDA with Karpenter and Cluster Autoscaler](#keda-with-karpenter-and-cluster-autoscaler)
- [Multi-tenancy and multi-cluster](#multi-tenancy-and-multi-cluster)

---

## HPA behavior tuning

`advanced.horizontalPodAutoscalerConfig.behavior` is a passthrough to the
Kubernetes HPA v2 behavior spec. Understand the semantics before copying
templates.

**The knobs:**

- `stabilizationWindowSeconds` — HPA considers the highest (for scaleDown) or
  lowest (for scaleUp) metric values from this window before deciding. Damps
  oscillation.
- `policies[]` — rate limits. Each policy says "in the last `periodSeconds`,
  allow at most this many pods of change". The HPA picks the policy that
  allows the most change (selectPolicy: Max, default) or least (Min) or
  disables the direction (Disabled).
- `policies[].type: Percent` / `Pods` — percentage of current replicas or
  absolute pod count.

**Defaults (without explicit `behavior`):**

```yaml
scaleUp:
  stabilizationWindowSeconds: 0            # react instantly
  policies:
    - type: Percent
      value: 100
      periodSeconds: 15
    - type: Pods
      value: 4
      periodSeconds: 15
  selectPolicy: Max

scaleDown:
  stabilizationWindowSeconds: 300          # damp 5 min
  policies:
    - type: Percent
      value: 100
      periodSeconds: 15
  selectPolicy: Max
```

**Production web service** — fast up, tapered down:

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 0
    policies:
      - {type: Percent, value: 100, periodSeconds: 30}
      - {type: Pods,    value: 5,   periodSeconds: 30}
    selectPolicy: Max
  scaleDown:
    stabilizationWindowSeconds: 300
    policies:
      - {type: Percent, value: 10, periodSeconds: 60}
      - {type: Pods,    value: 2,  periodSeconds: 60}
    selectPolicy: Min
```

**Slow-warmup service** (JVM, ML model load) — keep scaleDown conservative:

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 60         # accept a little delay to avoid thrash
    policies:
      - {type: Pods, value: 2, periodSeconds: 60}
  scaleDown:
    stabilizationWindowSeconds: 900        # 15 min — outlast warmup
    policies:
      - {type: Pods, value: 1, periodSeconds: 120}
```

**Tight rules:**

1. Align `stabilizationWindowSeconds` to multiples of the HPA sync period
   (`15s`). Use `15, 30, 60, 120, 300, 900`. Non-aligned windows are
   non-deterministic.
2. `scaleDown.stabilizationWindowSeconds` ≥ container warmup time. Otherwise
   HPA terminates pods before they contribute, leaving the queue/load on
   other pods and oscillating.
3. `cooldownPeriod` (KEDA) and `scaleDown.stabilizationWindowSeconds` (HPA)
   both apply to the `1→0` transition. Pods only terminate after the longer
   of the two elapses. Tune them together.

---

## Multi-trigger semantics and scalingModifiers

### Default: max of triggers

ScaledObject with multiple triggers emits each as a separate external metric
to the HPA. HPA calculates a desired replica count for each and picks the
**max**. If Kafka lag demands 10 pods and CPU demands 5, the result is 10.

That fits any-signal-high-means-scale-up. It is wrong for weighted or
conditional combinations.

### scalingModifiers — composite metric via formula (KEDA 2.13+)

Combine named triggers into a single composite metric.

```yaml
triggers:
  - type: prometheus
    name: rps
    metadata:
      serverAddress: http://prom:9090
      query: sum(rate(http_requests_total[1m]))
      threshold: "1"                    # threshold is ignored when using scalingModifiers
  - type: kubernetes-workload
    name: cpu_pressure
    metadata:
      podSelector: app=api
      value: "1"
advanced:
  scalingModifiers:
    formula: "(rps * 0.7) + (cpu_pressure * 0.3)"
    target: "100"                       # single target for the composite
    activationTarget: "20"              # gates 0→1
    metricType: AverageValue
```

Rules:

- Every trigger referenced in `formula` must have `name`.
- Formula grammar is [expr-lang](https://expr-lang.org/) — supports `+ - * /`,
  ternary `a > b ? a : b`, functions `min`, `max`, `ceil`, `floor`, `abs`.
- The formula replaces all individual trigger metrics — HPA sees one
  composite external metric.
- Fallback does not fire correctly while `scalingModifiers` is active in
  older KEDA versions (tracked issue). Validate against the KEDA version in use.
- For an **OR** of triggers (e.g., scale if queue > 50 OR CPU > 80%), the
  default max-of semantics does exactly that. Use `scalingModifiers` only for
  non-max combinations.

### Examples

**Weighted average:** `(rps * 0.6) + (queue_depth * 0.4)`.

**Conditional scaling (only when both metrics high):**
`rps > 100 and queue_depth > 10 ? rps : 0`.

**Ceiling at 3x a base metric:** `min(rps, base_rps * 3)`.

**Ratio-based:** `requests / workers` — scale when request/worker ratio
exceeds target.

---

## Cron patterns

### Overlap behavior

Cron triggers combine as max. Two overlapping windows of 10 replicas each
produce **10**, not 20. This is the right behavior for follow-the-sun
("10 pods during US hours OR 10 pods during IN hours; during overlap, still
just 10"). For summed replicas, use `scalingModifiers`.

### Business hours with off-hours batch handoff

One ScaledObject on the inference deployment, one on the batch deployment:

```yaml
# inference
triggers:
  - type: cron
    metadata:
      timezone: Europe/Stockholm
      start: "0 7 * * 1-5"
      end:   "0 18 * * 1-5"
      desiredReplicas: "10"

# batch (on a separate ScaledObject/ScaledJob)
triggers:
  - type: cron
    metadata:
      timezone: Europe/Stockholm
      start: "0 18 * * 1-5"
      end:   "0 7 * * 2-6"         # next-day 07:00 Tue–Sat
      desiredReplicas: "20"
```

### Overnight windows

Cron triggers with `start` in the evening and `end` in the next morning
(e.g., `start: "0 22 * * *"`, `end: "0 6 * * *"`) are buggy for multi-day
spans. Split into two triggers — `22:00–23:59 *` and `00:00–06:00 *` — or
always cross the day explicitly (`0 6 * * 2-6` for "until 6 AM next day").

### `desiredReplicas` is a floor, not a ceiling

During an active cron window, the cron trigger suggests `desiredReplicas`.
Any other trigger on the same ScaledObject can still push higher. To cap
scaling, use `maxReplicaCount` (which caps the whole ScaledObject).

---

## ScaledObject vs ScaledJob decision

Use this flow:

```
Is each event's work >30 seconds AND interrupting it costs significant state/redelivery?
│
├─ Yes → ScaledJob
│        ├─ one Job per event (or per event batch)
│        ├─ jobs are never killed for scale-down
│        └─ use scalingStrategy: accurate for queue scalers
│
└─ No  → ScaledObject
         ├─ long-running service
         ├─ HPA may terminate pods
         └─ message redelivery must be tolerated by app logic (idempotent workers, acks-after-processing)
```

See the canonical ScaledJob template in SKILL.md (long-running job section).
The key knob for queue-driven jobs is `scalingStrategy.strategy: accurate` —
KEDA computes `new = min(queueLength - runningJobs, maxReplicaCount - runningJobs)`,
so if the queue has 10 messages and 8 jobs are already running, only 2 more are
spawned (not 10).

Other `scalingStrategy` options:

- `default` — `new = max_scale - running_jobs`. Assumes queue items may get
  processed by running jobs.
- `eager` — use all remaining slots up to `maxReplicaCount` to drain a backlog
  fast.
- `custom` — plug in `customScalingQueueLengthDeduction` and
  `customScalingRunningJobPercentage` for bespoke math.

Multi-trigger combining for ScaledJob differs from ScaledObject: set
`scalingStrategy.multipleScalersCalculation` to `max` (default), `min`, `avg`,
or `sum` to choose how multiple triggers' queue lengths combine.

---

## KEDA HTTP Add-on

Separate project, separate CRD (`HTTPScaledObject`, `http.keda.sh/v1alpha1`).
As of 2026 it is **beta** — project README explicitly says not recommended
for critical production.

```yaml
apiVersion: http.keda.sh/v1alpha1
kind: HTTPScaledObject
metadata:
  name: xkcd
  namespace: apps
spec:
  hosts:
    - xkcd.example.com
  pathPrefixes:
    - "/"
  scaleTargetRef:
    name: xkcd
    kind: Deployment
    service: xkcd
    port: 8080
  replicas:
    min: 0
    max: 10
  scalingMetric:
    requestRate:
      granularity: 1s
      targetValue: 100
      window: 1m
    # or (mutually exclusive):
    # concurrency:
    #   targetValue: 100
```

Components:

- `interceptor` — traffic-facing, forwards to target, buffers while scaling
  from zero.
- `scaler` — external metrics provider KEDA queries.
- `operator` — watches `HTTPScaledObject`.

**Install:**

```bash
helm install http-add-on kedacore/keda-add-ons-http \
  --namespace keda
```

**When to use:**
- KEDA is already deployed, HTTP scale-to-zero is needed, and beta status is acceptable.
- Alternative: scale from Prometheus RPS query via the `prometheus` trigger
  (no scale-to-zero for cold starts though, because a running pod is needed to
  emit the metric — pair with a low-min scaler).
- Knative is a heavier alternative with revision/traffic-splitting features.

---

## GitOps with Argo CD and Flux

### Argo CD

Store ScaledObjects alongside the workloads in the same Application.
Problem: ArgoCD compares the Deployment's `.spec.replicas` against Git, but
KEDA/HPA mutates it — infinite sync drift.

Fix: annotate or add `ignoreDifferences` to the Application:

```yaml
spec:
  syncPolicy:
    syncOptions:
      - RespectIgnoreDifferences=true
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

Or on the Deployment itself:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/compare-options: IgnoreExtraneous
```

ApplicationSet with `cluster` generator fans ScaledObjects out to many
clusters with per-cluster parameter overrides.

### Flux

Same pattern — `ignoreDifferences` in the `Kustomization`:

```yaml
spec:
  patches:
    - target:
        kind: Deployment
        name: order-api
      patch: |
        - op: remove
          path: /spec/replicas
```

Flux multi-tenancy lockdown (`--no-cross-namespace-refs=true`) pairs naturally
with KEDA's `WATCH_NAMESPACE=team-a`.

---

## KEDA with Karpenter and Cluster Autoscaler

KEDA scales **pods**, not nodes. To convert "need more pods" into "need more
nodes" cheaply, pair with:

- **Karpenter** (AWS/Azure, fastest provisioning, best node diversity).
- **Cluster Autoscaler** (GKE-friendly, legacy EKS, on-prem with node groups).

### Key principles

1. **Pod requests are the input**, not actual usage. Under-request = Karpenter
   packs tightly and nodes never shrink; over-request = giant idle nodes.
   Profile with VPA in recommender mode and roll requests into the spec.
2. **Match KEDA `maxReplicaCount` to what the node pool can provide** within
   the workload's SLO. Scaling to 100 pods is useless if Karpenter takes 5 min
   to provision and the SLO is 30s.
3. **Karpenter consolidation** (`consolidationPolicy: WhenEmptyOrUnderutilized`)
   shrinks nodes when KEDA scales pods down. Keep KEDA `cooldownPeriod` and
   HPA `scaleDown.stabilizationWindowSeconds` together longer than Karpenter
   `consolidateAfter` to avoid reshuffling in-flight work.
4. **PDBs on scaled workloads** so Karpenter/CA don't evict mid-work.
5. **Multiple NodePools**: `on-demand` for latency-critical, `spot` for
   ScaledJobs. Use tolerations/nodeSelectors in the target spec.
6. **Provisioning latency caveats**: an aggressive `scaleUp` policy
   targeting 100 pods in 30s is useless if the node pool takes 90s to
   scale. Either raise `scaleUp.stabilizationWindowSeconds` or pre-warm
   a node.

### Karpenter NodePool snippet for KEDA batch

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: keda-spot-batch
spec:
  template:
    metadata:
      labels:
        workload: keda-batch
    spec:
      taints:
        - {key: workload, value: keda-batch, effect: NoSchedule}
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      requirements:
        - {key: karpenter.sh/capacity-type, operator: In, values: [spot]}
        - {key: kubernetes.io/arch, operator: In, values: [amd64]}
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 60s
  limits:
    cpu: 1000
```

ScaledJob jobTargetRef then uses a matching toleration and nodeSelector.

---

## Multi-tenancy and multi-cluster

### Central shared KEDA

- `WATCH_NAMESPACE=""` (all namespaces).
- `KEDA_RESTRICT_SECRET_ACCESS=true` limits secrets to the keda namespace.
  Cross-ns secret use requires `ClusterTriggerAuthentication`.
- RBAC per tenant limits who can create ScaledObjects.
- Simplest ops; one KEDA serves everyone.

### Per-namespace KEDA instances

- Stronger isolation (regulated workloads, noisy-neighbor isolation).
- One operator per team namespace with `WATCH_NAMESPACE` scoped to that
  namespace.
- **Only one instance can own `external.metrics.k8s.io`**. Others'
  external-metric scalers fail. Work around by using the `metrics-api`
  scaler pointed at an internal metrics service, or accept that only one
  namespace can use external-metric triggers.

### Multi-cluster GitOps

- Hub-and-spoke: Argo CD or Flux hub manages ScaledObjects across spokes.
- Per-cluster overrides via Kustomize/Helm for event-source endpoints.
- Use `ApplicationSet` (Argo) or `cluster` generator (Flux) to fan out.

### ResourceQuota for tenant caps

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: keda-limits
  namespace: team-a
spec:
  hard:
    count/scaledobjects.keda.sh: "50"
    count/scaledjobs.keda.sh: "20"
    count/triggerauthentications.keda.sh: "20"
```

Prevents runaway CR creation from tanking the operator.
