# KEDA Troubleshooting

Symptom → likely cause → fix. Start from the top. If the first three checks
pass, the problem is not KEDA itself — it's the trigger's event source.

## The canonical 6-step probe

```bash
NAME=order-worker
NS=apps

# 1. Is the ScaledObject Ready? What reason?
kubectl describe scaledobject -n "$NS" "$NAME"

# 2. Was the HPA created?
kubectl get hpa -n "$NS" "keda-hpa-$NAME" -o yaml

# 3. Operator saying anything?
kubectl logs -n keda deploy/keda-operator --tail=300 | grep -i "$NAME"

# 4. Is the external metrics API itself alive?
kubectl get apiservice v1beta1.external.metrics.k8s.io

# 5. Can KEDA serve the metric?
kubectl get --raw \
  "/apis/external.metrics.k8s.io/v1beta1/namespaces/$NS/s0-...?labelSelector=scaledobject.keda.sh%2Fname%3D$NAME"

# 6. Metrics server logs (scaler-side errors)
kubectl logs -n keda deploy/keda-operator-metrics-apiserver --tail=200
```

Use `${CLAUDE_SKILL_DIR}/scripts/debug-scaledobject.sh <name> [namespace]` to
run all of these in one shot.

## Symptom catalogue

### ScaledObject stuck at 0 replicas, HPA exists

- **Cause A**: trigger is evaluating inactive. Check
  `status.conditions[type=Active]` — if False, the scaler is saying "no work
  to do". Verify against the event source directly (queue is empty, cron
  window is closed, query returns 0).
- **Cause B**: activation threshold not met. `activationValue` /
  `activationThreshold` must be crossed to wake from 0. E.g., if
  `queueLength: 20` and `activationValue: 5`, queue must be ≥ 5 to wake.
- **Cause C**: scaler auth failure. Scaler returns error, deployment stays
  at minReplicaCount (0). Look for error logs: `kubectl logs -n keda
  deploy/keda-operator | grep -i "error.*<trigger-type>"`.

### ScaledObject shows Ready=False

Check `kubectl describe scaledobject` `.status.conditions[].reason`:

| Reason | Meaning | Fix |
|---|---|---|
| `ScaledObjectReady` | Working | (Expected when Ready=True) |
| `HPAConflict` | Manual HPA exists on same target | Delete the HPA, or set annotation `scaledobject.keda.sh/transfer-hpa-ownership: "true"`. |
| `ScaledObjectCheckFailed` | ScaledObject has an invalid config | Inspect `.status.conditions[].message`. |
| `ScalerBuildError` | Couldn't instantiate a scaler | Check trigger metadata is well-formed, auth ref resolves. |

### HPA not created at all

1. `kubectl get hpa -n <ns>` — look for `keda-hpa-<name>`.
2. If absent, admission webhook may have rejected the ScaledObject. Check:
   `kubectl get scaledobject <name> -o yaml` for status messages.
3. Check webhook logs:
   `kubectl logs -n keda deploy/keda-admission-webhooks --tail=100`.
4. If webhook is unhealthy and `failurePolicy: Fail` is set, ScaledObject
   submission is blocked. Temporarily set `Ignore`, fix, then set back.

### HPA exists, but "unable to get external metric"

This is the most common case — the metric pipeline is broken between HPA and
KEDA's metrics apiserver.

1. **APIService registered?**
   ```bash
   kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml
   ```
   `Available=False` means another component owns the APIService (Datadog,
   Prometheus Adapter). Only one can serve it.

2. **Metrics apiserver healthy?**
   ```bash
   kubectl get pods -n keda -l app=keda-operator-metrics-apiserver
   kubectl logs -n keda deploy/keda-operator-metrics-apiserver --tail=100
   ```

3. **Metric exposed?**
   ```bash
   kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1" | jq '.resources[].name' | grep -i <scaledobject-name>
   ```
   Nothing? The operator hasn't registered it — likely scaler error.

4. **Can KEDA resolve the value?**
   ```bash
   kubectl get --raw \
     "/apis/external.metrics.k8s.io/v1beta1/namespaces/<ns>/<metric>?labelSelector=scaledobject.keda.sh%2Fname%3D<name>"
   ```
   A 404 usually means the trigger index is wrong or the ScaledObject has not
   produced a metric yet (first poll pending).

### Scaling happens but to wrong replica count

- **Trigger emits wrong metric**. Probe the raw metric value (step 5 above)
  and compare to what the event source really has. If the queue has 100
  messages but KEDA reports 50, the scaler is double-counting or mis-parsing.
- **Wrong `metricType`**. `AverageValue` = metric-per-pod; `Value` = raw
  per-HPA. Most scalers want `AverageValue`. If using `Value`, HPA divides
  differently.
- **`queueLength`/`threshold` misunderstood**. `queueLength: 20` on 100 messages
  → 100 / 20 = 5 desired replicas. Set the target to the per-replica workload
  desired, not the total.

### Scale-to-zero never happens

- **`minReplicaCount: 0` set?** — check.
- **Only cpu/memory triggers?** — can't scale to 0. Add a queue/cron/prometheus
  trigger.
- **`cooldownPeriod` not elapsed?** — default 300s of trigger inactivity.
- **Trigger permanently active?** — e.g., `activationValue: 0` means "always
  active". Raise it.
- **Minimum HPA compat?** — some very old cluster autoscaler or HPA
  configurations do not support `minReplicas: 0` even with external metrics;
  confirm k8s version.

### Scaling oscillates (flapping)

- **`scaleDown.stabilizationWindowSeconds` too short**. Default 300s; raise
  to 600–900s for slow-warmup services.
- **Metric itself is noisy** (short-window rate, spiky queue). Smooth in the
  source: `rate(x[5m])` instead of `rate(x[10s])`.
- **scaleUp too aggressive on a slow-provisioning cluster**. Raise
  `scaleUp.stabilizationWindowSeconds` or lower policy values.

### Pods get killed mid-work

Wrong shape. For long-running discrete units of work, use
ScaledJob, not ScaledObject. HPA will terminate pods on scale-down; there is
no API to pin a specific pod as "in use".

### Fallback doesn't fire when trigger source is down

- **`fallback` not set?** — add `failureThreshold: 3, replicas: N`.
- **cpu/memory trigger?** — fallback doesn't work for resource metrics.
- **`scalingModifiers` in use?** — fallback interaction is broken in some
  versions. Test by chaos (block the metric source) and verify behavior.

### Operator CrashLoopBackOff or constant restarts

- **Slow-query scaler** can cause the polling loop to timeout. Set timeouts
  on the event source and check operator logs for long poll durations.
- **Too many ScaledObjects, not enough reconciles**. Raise
  `KEDA_SCALEDOBJECT_CTRL_MAX_RECONCILES` (default 5) and Kubernetes client
  QPS (`--kube-api-qps=50 --kube-api-burst=75`).
- **OOM**. Operator default limits are 1GiB; raise to 2-4Gi for large
  clusters (100+ ScaledObjects).

### Metrics apiserver intermittently unresponsive

- **Single replica going through rolling update**. Run 2+ replicas.
- **Keep-alive issues** with some proxies. Set
  `KEDA_METRICS_LEVERAGE_KEEPALIVE=false` and retest.

### Authentication fails for pod identity

- **AWS IRSA**: verify `eks.amazonaws.com/role-arn` annotation on the KEDA
  operator SA (or target SA if `identityOwner: workload`). Trust policy on
  the IAM role must allow the KEDA OIDC provider and the SA's audience.
- **Azure Workload Identity**: KSA needs label
  `azure.workload.identity/use: "true"` and annotation
  `azure.workload.identity/client-id: <client-id>`. Federated credential on
  the Azure managed identity must trust the SA's issuer URL.
- **GCP Workload Identity**: KSA annotation
  `iam.gke.io/gcp-service-account=sa@project.iam.gserviceaccount.com`, and
  the GSA must have `roles/iam.workloadIdentityUser` binding for the KSA.

### RBAC / "forbidden" errors in operator logs

KEDA operator's cluster role needs access to:

- `deployments`, `statefulsets` (`apps/*`): `get, list, watch, patch`
- `horizontalpodautoscalers` (`autoscaling/*`): `get, list, watch, create, update, delete`
- `scaledobjects`, `scaledjobs`, `triggerauthentications`,
  `clustertriggerauthentications` (`keda.sh/*`): full
- `secrets` (if reading secrets for TriggerAuthentication): `get, list, watch`
- `events`: `create, patch`
- `serviceaccounts/token` (if using Vault kubernetes auth): `create`

If the chart's RBAC has been customized, confirm these.

### Admission webhook blocking all changes

- **Cert expired**. Check `kubectl get secret -n keda kedaorg-certs -o yaml`
  for expiry. Auto-rotation should handle this — verify
  `--enable-cert-rotation=true` on operator.
- **Webhook pod crashed**. `kubectl get pods -n keda -l
  app=keda-admission-webhooks`. Restart if needed.
- **Emergency**: patch webhook failurePolicy to `Ignore`:
  ```bash
  kubectl patch validatingwebhookconfiguration keda-admission \
    --type=json \
    -p='[{"op":"replace","path":"/webhooks/0/failurePolicy","value":"Ignore"}]'
  ```
  Then fix the root cause and set back to `Fail`.

## Known CVEs / advisories

- **CVE-2025-68476** (Arbitrary File Read via HashiCorp Vault
  `TriggerAuthentication`). Fixed in v2.17.3 / v2.18.3 / v2.19.0+. Upgrade
  and restrict who can create/modify TriggerAuthentication.
- Keep an eye on https://github.com/kedacore/keda/security/advisories for
  newer issues.

## Known scaler-specific footguns

- **Prometheus** `ignoreNullValues: true` (default) means a null query result
  is treated as 0, which triggers scale-down. If "missing data" means
  "keep current", set to `false` and handle the error path.
- **apache-kafka** `allowIdleConsumers` and `limitToPartitionsWithLag` are
  mutually exclusive — the admission webhook rejects if both are set.
- **aws-sqs-queue** field is `queueURL`, not `queueUrl` (camelCase is common
  Kubernetes but SQS uses this spelling).
- **cron** `start` and `end` must differ; overnight spans can surprise.
- **rabbitmq** `mode: Unknown` (implicit default) does not scale.
- **Redis** `unsafeSsl: "true"` should only be for testing. In prod, mount a
  CA bundle via TriggerAuthentication.

## When to escalate upstream

- Operator CrashLoopBackOff with no informative log and `--verbosity=debug`
  shows nothing → file an issue at github.com/kedacore/keda with the CRD,
  operator version, and logs.
- Scaler behavior contradicts the docs/source → file an issue with a reproduction.
- CVE or suspected security issue → file per the Security Policy in the repo
  (private advisory, not public issue).
