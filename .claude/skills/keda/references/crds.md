# KEDA CRDs — Complete field reference

KEDA's API group is `keda.sh/v1alpha1`. The three CRDs are `ScaledObject`,
`ScaledJob`, and `TriggerAuthentication` / `ClusterTriggerAuthentication`.
This file documents every field with defaults and semantics.

## Contents

- [ScaledObject](#scaledobject)
- [ScaledJob](#scaledjob)
- [TriggerAuthentication / ClusterTriggerAuthentication](#triggerauthentication--clustertriggerauthentication)
- [Annotations](#annotations)

---

## ScaledObject

Links a Deployment, StatefulSet, or any resource with a `/scale` subresource to
one or more event triggers. KEDA creates and manages an HPA behind it.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1          # default: apps/v1
    kind: Deployment             # default: Deployment
    name: my-deployment          # required
    envSourceContainerName: app  # optional; which container env to read for env-based auth
  pollingInterval: 30            # default 30; seconds between trigger polls
  initialCooldownPeriod: 0       # default 0; delay before cooldown logic starts
  cooldownPeriod: 300            # default 300; seconds of inactivity before N→0
  idleReplicaCount: 0            # optional; only "0" supported reliably. Must be < minReplicaCount
  minReplicaCount: 0             # default 0; set >=1 to always keep pods
  maxReplicaCount: 100           # default 100; passed to HPA
  fallback:                      # optional; kicks in when trigger errors
    failureThreshold: 3          # consecutive failures before fallback
    replicas: 6                  # replica count during fallback
    behavior: static             # static | currentReplicas | currentReplicasIfHigher | currentReplicasIfLower
  advanced:
    restoreToOriginalReplicaCount: false  # on delete: keep current (false) or restore original
    horizontalPodAutoscalerConfig:
      name: my-custom-hpa        # default keda-hpa-<scaledobject-name>
      behavior:                  # standard HPA v2 behavior
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
            - type: Percent
              value: 100
              periodSeconds: 30
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
            - type: Percent
              value: 10
              periodSeconds: 60
    scalingModifiers:            # KEDA 2.13+
      formula: "(rps + cpu) / 2"
      target: "100"
      activationTarget: "10"
      metricType: AverageValue
  triggers:                      # required; one or more
    - type: prometheus
      name: rps                  # optional; required when referenced in scalingModifiers.formula
      metricType: AverageValue   # default AverageValue. AverageValue | Value | Utilization (cpu/memory only)
      useCachedMetrics: false    # default false; cache within pollingInterval. Not for cpu/memory/cron.
      metadata:                  # scaler-specific; see references/scalers.md
        serverAddress: http://prom:9090
        query: sum(rate(...))
        threshold: "200"
      authenticationRef:
        name: prom-auth
        kind: TriggerAuthentication  # default; also ClusterTriggerAuthentication
```

### Semantics by field

- **`pollingInterval`** — how often the KEDA operator polls each trigger during
  `0→1` evaluation. HPA polls external metrics on its own 15s cycle, so between
  1 and N the effective polling is MAX(pollingInterval, 15s). Use
  `useCachedMetrics` to align.
- **`cooldownPeriod`** — inactivity-required seconds before scaling `1→0`. Has
  **no effect** on `N→1` scale-down; that's HPA's
  `scaleDown.stabilizationWindowSeconds`.
- **`initialCooldownPeriod`** — after ScaledObject creation, delay before the
  cooldown timer starts. Useful to warm up deployments after
  creating the ScaledObject without them immediately scaling to zero.
- **`idleReplicaCount`** — defines a "running floor" separate from
  the "idle replicas". E.g., `idleReplicaCount: 0` + `minReplicaCount: 2`
  means "0 pods when idle, jump to 2 when a trigger activates". Only `0`
  is well-supported; HPA cannot natively idle at non-zero values.
- **`minReplicaCount`** — the HPA floor. `0` enables scale-to-zero for
  external-metric triggers.
- **`maxReplicaCount`** — the HPA ceiling. Keep this ≤ what the node pool can
  actually provide within the workload's SLO.
- **`fallback`** — when a trigger errors `failureThreshold` times consecutively,
  KEDA substitutes a synthesized metric that drives replicas to
  `fallback.replicas`. Requires the trigger's `metricType` to be
  `AverageValue` — **does not work with cpu/memory triggers**. Behavior modes:
  - `static`: always use `replicas`.
  - `currentReplicas`: freeze at the current count.
  - `currentReplicasIfHigher` / `currentReplicasIfLower`: clamp.
- **`advanced.restoreToOriginalReplicaCount`** — on ScaledObject deletion,
  `false` (default) leaves the deployment at current count; `true` restores
  the original replica count recorded at ScaledObject creation.
- **`advanced.horizontalPodAutoscalerConfig.name`** — rename the managed HPA;
  otherwise `keda-hpa-<scaledobject>`.
- **`advanced.horizontalPodAutoscalerConfig.behavior`** — standard
  [HPAv2 behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior).
  Align stabilization windows to multiples of the 15s HPA sync period.
- **`advanced.scalingModifiers`** (KEDA 2.13+) — combine multiple triggers into
  a single composite metric via an expr-lang formula. Requires `name` on
  each trigger used in the formula. Fallback does not fire correctly while
  scalingModifiers is active.
- **`triggers[*].name`** — trigger identifier. Required when referenced in
  `scalingModifiers.formula`. Shows in metrics and logs.
- **`triggers[*].metricType`** — for external metrics, typically
  `AverageValue` (metric per pod). `Value` gives a raw per-HPA metric. For
  cpu/memory, use `Utilization` (% of request) or `AverageValue` (absolute).
- **`triggers[*].useCachedMetrics`** — cache scaler result within
  `pollingInterval`; HPA reads cache rather than forcing a fresh call per
  15s sync. Not available for cpu/memory/cron.

### Multi-trigger semantics (ScaledObject)

Each trigger emits a desired replica count to the HPA as a separate external
metric. The HPA takes **max** across them. To combine differently (sum,
weighted average, conditional), use `advanced.scalingModifiers.formula`.

---

## ScaledJob

Scales by spawning new `Job` resources instead of adjusting a Deployment's
replicas. Use when events must be processed to completion — pods are never
terminated for scale-down.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: example-job
spec:
  jobTargetRef:                  # required; full Job spec
    parallelism: 1               # pods per job
    completions: 1               # successful pod count
    backoffLimit: 4              # retries before job failure
    template:
      spec:
        restartPolicy: Never
        containers:
          - name: worker
            image: worker:v1
  pollingInterval: 30            # default 30
  successfulJobsHistoryLimit: 100  # default 100; retain N completed jobs
  failedJobsHistoryLimit: 100    # default 100; retain N failed jobs
  envSourceContainerName: worker # optional; container whose env feeds env-based auth
  minReplicaCount: 0             # default 0
  maxReplicaCount: 100           # default 100; max jobs created per poll
  rollout:
    strategy: default            # default | gradual (gradual = don't delete running jobs on update)
    propagationPolicy: background # background | foreground (for job deletion on ScaledJob update)
  scalingStrategy:
    strategy: default            # default | custom | accurate | eager
    customScalingQueueLengthDeduction: 1       # custom only
    customScalingRunningJobPercentage: "0.5"   # custom only
    pendingPodConditions: ["Ready"]            # optional; pod conditions marking job as pending
    multipleScalersCalculation: max  # max | min | avg | sum across triggers
  triggers:
    - type: rabbitmq
      metadata: {queueName: jobs, host: ..., mode: QueueLength, value: "1"}
```

### Scaling strategies

- **default** — `new = max_scale - running_jobs`. Assumes queue items may get
  processed by running jobs.
- **accurate** — `new = min(queue_length - running_jobs, max_scale - running)`.
  Best when the queue represents exactly what's outstanding (e.g., most queue
  scalers). Prevents over-provisioning.
- **eager** — use all remaining slots up to `maxReplicaCount` to drain the
  queue fast.
- **custom** — plug in `customScalingQueueLengthDeduction` and
  `customScalingRunningJobPercentage` for bespoke math.

### Multi-trigger semantics (ScaledJob)

Unlike ScaledObject, ScaledJob combines multiple triggers via
`scalingStrategy.multipleScalersCalculation` (default `max`): `max`, `min`,
`avg`, or `sum` across all triggers' reported queue lengths.

### When to use ScaledJob

- Long-running work that must not be killed mid-execution.
- One event = one job with its own lifecycle.
- Batch workloads where job completion matters.

When NOT to use ScaledJob: long-running services with many short requests per
pod. Use ScaledObject.

---

## TriggerAuthentication / ClusterTriggerAuthentication

Both have the same spec. TriggerAuthentication is namespace-scoped;
ClusterTriggerAuthentication is cluster-scoped and referenced from any
namespace via `authenticationRef.kind: ClusterTriggerAuthentication`.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: example-auth
spec:
  # Each block is independent and optional. Pick what the scaler requires.

  podIdentity:
    provider: aws | azure-workload | gcp | none
    identityId: <client-id>           # azure | gcp
    identityTenantId: <tenant-id>     # azure
    identityAuthorityHost: <host>     # azure (cross-cloud)
    roleArn: arn:aws:iam::...         # aws; optional
    identityOwner: keda | workload    # aws; keda = operator SA; workload = target pod SA

  secretTargetRef:                    # mount k8s secret keys as params
    - parameter: host                 # scaler parameter name
      name: rabbitmq-credentials      # secret name (same namespace as ScaledObject)
      key: amqp-host                  # key in secret

  configMapTargetRef:                 # same shape, but from a ConfigMap
    - parameter: ca_cert
      name: prom-config
      key: ca.crt

  env:                                # from target pod's container env
    - parameter: prometheus_url
      name: PROM_URL
      containerName: app              # default: from scaleTargetRef.envSourceContainerName

  hashiCorpVault:
    address: https://vault.example.com
    authentication: token | kubernetes
    namespace: ""                     # Vault Enterprise namespace
    role: keda-role                   # kubernetes auth
    mount: kubernetes                 # kubernetes auth mount
    credential:
      token: <vault-token>            # token auth
      serviceAccount: /var/run/secrets/kubernetes.io/serviceaccount/token
      serviceAccountName: my-sa       # kubernetes auth: request token from SA
    secrets:
      - parameter: api_key
        path: secret/data/myapp
        key: api_key_field
        type: secretV2                # "" | secretV2 | secret | pki

  azureKeyVault:
    vaultUri: https://vault.vault.azure.net/
    credentials:
      clientId: <app-id>
      tenantId: <tenant-id>
      clientSecret:
        valueFrom:
          secretKeyRef:
            name: azure-app-secret
            key: client-secret
    podIdentity:
      provider: azure-workload
      identityId: <managed-identity>
    cloud:
      type: AzurePublicCloud          # AzurePublicCloud | AzureUSGovernmentCloud | AzureChinaCloud | AzureGermanCloud
    secrets:
      - parameter: connection-string
        name: MySecretName
        version: <version>            # optional

  awsSecretManager:
    credentials:
      accessKey:
        valueFrom:
          secretKeyRef: {name: aws-creds, key: AWS_ACCESS_KEY_ID}
      accessSecretKey:
        valueFrom:
          secretKeyRef: {name: aws-creds, key: AWS_SECRET_ACCESS_KEY}
    podIdentity:
      provider: aws
      roleArn: arn:aws:iam::...
    region: us-east-1
    secrets:
      - parameter: db_password
        name: MySecretName
        versionId: <id>
        versionStage: AWSCURRENT
        secretKey: password           # optional; key within JSON secret

  gcpSecretManager:
    credentials:
      clientSecret:
        valueFrom:
          secretKeyRef: {name: gcp-sa, key: key.json}
    podIdentity:
      provider: gcp
    secrets:
      - parameter: db-password
        id: my-secret
        version: latest

  boundServiceAccountToken:           # bound SA token
    - parameter: bearer_token
      serviceAccountName: keda-reader
```

### Referencing from a trigger

```yaml
triggers:
  - type: prometheus
    metadata: { serverAddress: http://prom:9090, query: '...', threshold: '200' }
    authenticationRef:
      name: prom-auth
      kind: TriggerAuthentication     # default; ClusterTriggerAuthentication otherwise
```

### Secret namespace rules

- `TriggerAuthentication.spec.secretTargetRef` looks in the ScaledObject's
  namespace.
- `ClusterTriggerAuthentication.spec.secretTargetRef` looks in the KEDA
  operator's namespace (usually `keda`) — unless the operator is launched with
  `KEDA_CLUSTER_OBJECT_NAMESPACE` set to override.
- `KEDA_RESTRICT_SECRET_ACCESS=true` limits the operator to reading secrets
  only in the keda namespace, forcing ClusterTriggerAuthentication for
  cross-namespace secret use.

### podIdentity provider details

- `none` — disable pod identity; use secrets/env/Vault instead.
- `aws` — IRSA (serviceAccountName annotated with `eks.amazonaws.com/role-arn`).
  `identityOwner: keda` uses the operator's SA; `workload` uses the target
  pod's SA (useful when the app already has IRSA configured).
- `azure-workload` — Azure AD Workload Identity. SA annotated with
  `azure.workload.identity/client-id`. Replaces the deprecated `azure`
  provider (which used pod identity v1).
- `gcp` — GCP Workload Identity. SA annotated with
  `iam.gke.io/gcp-service-account=...`.

---

## Annotations

### On ScaledObject/ScaledJob

| Annotation | Value | Purpose |
|---|---|---|
| `autoscaling.keda.sh/paused` | `"true"` / `"false"` | Freeze replica count; metrics still collected but HPA not reconciled. |
| `autoscaling.keda.sh/paused-replicas` | `"N"` | Pin to exactly N replicas until annotation removed. Overrides `paused`. |
| `autoscaling.keda.sh/paused-scale-in` | `"true"` | Block scale-down (HPA scaleDown policy → Disabled). |
| `autoscaling.keda.sh/paused-scale-out` | `"true"` | Block scale-up. |
| `autoscaling.keda.sh/force-activation` | `"true"` | Force all scalers active immediately. Break-glass. |
| `scaledobject.keda.sh/transfer-hpa-ownership` | `"true"` | Adopt an existing HPA on the target rather than conflict. |
| `validations.keda.sh/hpa-ownership` | `"false"` | Disable the HPA-conflict validation (use cautiously). |

### What "paused" does not do

- It does NOT stop the operator from polling triggers.
- It does NOT stop the metrics-apiserver from serving the metric.
- It only stops the HPA from reconciling replica changes based on metrics.

To fully stop metric collection, delete the ScaledObject (or set
`minReplicaCount` high enough that scaling has no target).

---

## Status fields (read-only)

`kubectl get scaledobject <name> -o yaml` exposes a `status` block worth
knowing:

```yaml
status:
  scaleTargetKind: Deployment
  scaleTargetGVKR: apps/v1.deployments
  originalReplicaCount: 1
  lastActiveTime: "2026-04-15T12:34:56Z"
  conditions:
    - type: Ready       # True = ScaledObject is functional
      status: "True"
      reason: ScaledObjectReady
    - type: Active      # True = at least one trigger active (workload awake)
      status: "True"
      reason: ScalerActive
    - type: Fallback    # True = fallback replicas in effect
      status: "False"
    - type: Paused      # True = paused annotation applied
      status: "False"
  hpaName: keda-hpa-my-scaledobject
```

Debug rule of thumb: if `Ready=False`, inspect `reason` — it's usually
`HPAConflict`, `ScaledObjectDoesntExist`, or a scaler connection error.
