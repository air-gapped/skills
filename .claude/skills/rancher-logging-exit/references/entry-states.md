# Entry states — identify before choosing a runbook

```bash
NS=cattle-logging-system
helm list -n $NS
kubectl get crd | grep banzaicloud
kubectl get pods -n $NS
kubectl get logging-all -A 2>/dev/null || kubectl get loggings,flows,clusterflows,outputs,clusteroutputs -A
```

## State 1 — healthy bundled install (the default case)

`rancher-logging` + `rancher-logging-crd` releases present, operator + fluentd +
fluent-bit pods running, CRs ACTIVE=true. → `runbook.md` Strategy A.

Check the chart version prefix to date it: `10X.y.z+up4.10.0-rancher.N` where
102=Rancher 2.7 … 106=2.11, 107=2.12, 108=2.13, 109=2.14, 110=2.15. ALL of
106–110 carry upstream base 4.10.0. Anything `+up3.x` is Rancher ≤2.8-era and
even more urgent. Full matrix: k8s-components-checker
`references/compat/rancher-logging.md`.

## State 2 — stale debris (operator long gone, CRDs/CRs linger)

Signature: only `rancher-logging-crd` release remains (possibly years old), CRDs
exist (maybe an old subset — 3.17-era ships just 7 of the 16: loggings, flows,
clusterflows, outputs, clusteroutputs, eventtailers, hosttailers — no
fluentbitagents/syslogng*/loggingroutes), orphaned CRs with ACTIVE=false/blank,
no pods.

**Trap**: a naive upstream `helm install` on this cluster silently SKIPS the 7
existing CRDs (crds/-dir semantics) and installs only the missing 9 ⇒ mixed
3.17/6.7 CRD generations, no warning, subtle breakage later.

Path:

```bash
# 1. Salvage config — old ClusterOutputs/Flows often encode still-valid
#    destination details (ES hosts, S3 buckets, creds refs). Back up per
#    runbook step 0 even here.
# 2. Clean slate is safe — nothing is running, cascade deletes nothing live:
helm uninstall rancher-logging-crd -n $NS
kubectl get crd | grep banzaicloud          # hand-delete stragglers
# 3. Fresh upstream install WITH CRDs:
helm install logging-operator oci://<registry>/.../logging-operator \
  --version 6.7.0 -n <ns> --create-namespace -f upstream-values.yaml
# 4. Re-author salvaged config as 6.7-era CRs (decoupled pattern — see the
#    logging-operator skill) rather than re-applying 3.17-era YAML verbatim.
```

Alternative to step 2 (keep the orphaned CRs in place): server-side-apply the
6.7.0 CRDs over the old 7 + delete the orphaned
`sh.helm.release.v1.rancher-logging-crd.*` secret — then the CRs survive and the
new operator reconciles them. Only worth it if the CRs should live unmodified.

## State 3 — legacy Rancher v1 logging remnants (pre-operator era)

`clusterloggings.management.cattle.io` / `projectloggings.management.cattle.io`
CRDs (Rancher ≤2.6 logging v1). Unrelated to the operator — pure debris. After
confirming no CRs exist (`kubectl get clusterloggings,projectloggings -A`),
delete the CRDs. Often coexists with State 2 on long-lived clusters.

## State 4 — Windows nodes with nodeAgents

`kubectl get nodeagents -A` non-empty, or the root Logging has `spec.nodeAgents`.
No 6.x path (NodeAgent removed 6.0; Telemetry Controller immature). Don't
migrate these clusters' Windows collection — see `cr-compat.md` §nodeAgents.

## State 5 — coexistence / gradual adoption

Running upstream operator side-by-side with rancher-logging during transition is
viable (the Sylva project did exactly this): distinct Logging resources with
distinct `loggingRef`s and control namespaces, collectors watching disjoint
namespace sets. Costs a second DaemonSet; buys a no-cliff rollout. End state
should still retire the bundled chart (the CVE lives in ITS operator as long as
it runs and project-owners can author CRs it reconciles).
