# Runbooks — Strategy A (release-secret surgery) and B (clean reinstall)

Target 6.7.0+. Air-gapped clusters: complete `airgap-prep.md` FIRST (images +
chart in the internal registry, values overrides drafted).

## Shared step 0 — inventory & backup (both strategies)

```bash
NS=cattle-logging-system
helm list -n $NS                                   # note exact chart versions
mkdir -p logging-exit-backup-$(date +%Y%m%d) && cd logging-exit-backup-$(date +%Y%m%d)

# All CR kinds that exist at 4.10 (syslogng* usually absent on Rancher installs)
for k in loggings flows clusterflows outputs clusteroutputs fluentbitagents \
         eventtailers hosttailers; do
  kubectl get $k -A -o yaml > $k.yaml 2>/dev/null || true
done
kubectl get nodeagents -A -o yaml > nodeagents.yaml 2>/dev/null || true  # Windows check

helm get values rancher-logging -n $NS > rancher-logging-values.yaml
kubectl get pvc -n $NS -o yaml > pvcs.yaml

# Rendered config snapshot — needed for the post-migration escaping diff
kubectl get secret -n $NS -o name | grep fluentd-app
kubectl get secret <logging>-fluentd-app -n $NS \
  -o jsonpath="{.data['fluentd\.conf']}" | base64 -d > fluentd.conf.pre

# Helm release secrets (the rollback lifeline for Strategy A)
kubectl get secret -n $NS -o name | grep sh.helm.release.v1.rancher-logging
kubectl get secret -n $NS -o yaml \
  -l 'owner=helm,name in (rancher-logging, rancher-logging-crd)' > helm-release-secrets.yaml

tar czf ../logging-exit-backup-$(date +%Y%m%d-%H%M).tar.gz . && cd ..
```

Gate checks before proceeding:
- `nodeagents.yaml` non-empty ⇒ Windows logging in use ⇒ **stop**, see
  `cr-compat.md` §nodeAgents.
- Run the **pruning pre-flight** (`cr-compat.md`) — know which fields will be
  silently dropped before you commit.

## Strategy A — release-secret surgery (primary; near-zero gap)

Maintainer-endorsed (Axoflow/Wilcsinszky). The insight: deleting a Helm *release
Secret* makes the release vanish from Helm/Rancher without touching any deployed
resource. CRDs, CRs, and the running pipeline stay up throughout.

```bash
# 1. Stop the old operator (data plane keeps running — fluentd/fluent-bit are
#    operator-CREATED but not operator-DEPENDENT)
kubectl scale deploy rancher-logging -n $NS --replicas=0
# (deployment name = helm release name; verify: kubectl get deploy -n $NS)

# 2. Delete the Helm release secrets (backed up in step 0)
kubectl delete secret -n $NS -l 'owner=helm,name=rancher-logging'
kubectl delete secret -n $NS -l 'owner=helm,name=rancher-logging-crd'
helm list -n $NS      # both gone; Rancher Apps UI no longer shows them

# 3. Upgrade CRDs in place — server-side is MANDATORY (828KB CRDs)
helm show crds oci://<registry>/kube-logging/helm-charts/logging-operator \
  --version 6.7.0 | kubectl apply --server-side --force-conflicts -f -
# verify: kubectl get crd flows.logging.banzaicloud.io -o yaml | grep controller-gen
#         (expect a recent controller-gen version, and 16 CRDs total present)

# 4. Delete the old operator deployment + rancher-only leftovers the release
#    secrets no longer own (operator deployment, its SA/RBAC — enumerate first):
kubectl delete deploy rancher-logging -n $NS
# journald aggregator DaemonSets (rancher-only, no upstream equivalent — decide
# per cr-compat.md §journald whether to port before deleting):
kubectl get ds -n $NS | grep journald

# 5. Install upstream operator — CRDs already applied, so skip them
helm install logging-operator oci://<registry>/kube-logging/helm-charts/logging-operator \
  --version 6.7.0 -n $NS \
  --set logging-operator-crds.install=false \
  -f upstream-values.yaml        # air-gap image overrides from airgap-prep.md

# 6. The operator adopts the existing Logging (name rancher-logging-root) and
#    reconciles fluentd/fluent-bit to 6.7.0 images. Watch:
kubectl get pods -n $NS -w
kubectl get logging rancher-logging-root -o yaml   # status.problems, configCheckResults
```

Why keep namespace + Logging name: StatefulSet `rancher-logging-root-fluentd` and
its `fluentd-buffer` PVCs keep their names ⇒ **disk buffers survive** the operator
swap. (Rename later, as a separate planned change, if cattle-* naming offends.)

Collection gap: only the aggregator pod restarts on the image bump — fluent-bit
buffers during it. Typically <1 min.

## Strategy B — clean reinstall (corrected from the common draft)

For when a config redesign is wanted anyway. Corrections vs the typical guide:
do NOT delete the namespace (kills buffer PVCs); expect silent pruning, not
validation errors; CRD deletes cascade.

```bash
# 1. Backup (step 0) — this strategy DEPENDS on it
# 2. Uninstall operator, then CRDs — THIS CASCADES: all CRs + the operator-owned
#    fluentd/fluent-bit are deleted. Accept the outage window.
helm uninstall rancher-logging -n $NS
helm uninstall rancher-logging-crd -n $NS
kubectl get crd | grep banzaicloud   # should be empty; hand-delete stragglers
# 3. DO NOT delete the namespace if you want the buffer PVCs.
# 4. Install upstream WITH CRDs (none exist now, crds/ dir applies cleanly)
helm install logging-operator oci://<registry>/.../logging-operator \
  --version 6.7.0 -n $NS -f upstream-values.yaml
# 5. Restore CRs: outputs → clusteroutputs → loggings → fluentbitagents →
#    flows → clusterflows (refs before referrers). Pruning diff first (cr-compat.md).
kubectl apply -f outputs.yaml ... etc
```

## Validation (both strategies)

```bash
kubectl get logging-all -A                    # every Flow/Output ACTIVE=true?
kubectl logs -n $NS -l app.kubernetes.io/name=logging-operator --tail=100
kubectl get pods -n $NS | grep -E 'fluentd|fluent-bit'   # new 6.7.0 images?
# Escaping diff (fact #5): rendered config pre vs post
kubectl get secret <logging>-fluentd-app -n $NS \
  -o jsonpath="{.data['fluentd\.conf']}" | base64 -d > fluentd.conf.post
diff fluentd.conf.pre fluentd.conf.post   # expect image/version lines + escaping
                                          # changes ONLY where values had special chars
# End-to-end: run a test pod, confirm arrival at one real destination
```

Post-migration: update team docs (no Rancher Apps UI anymore — helm/kubectl only),
monitoring selectors if labels changed, and consult the **logging-operator** skill
for day-2 (the 4.10→6.x behavior deltas: non-root fluentd UID 100, removed
NodeAgent, new FluentbitAgent decoupled pattern).

## Rollback

See `cr-compat.md` §rollback. Short version: with Strategy A, re-create the two
backed-up release secrets + server-side-apply the old CRDs back; CRD ownership
metadata still points at rancher-logging-crd (you never Helm-adopted them), so
`helm upgrade`/reinstall of the Rancher charts just works. 6.x-only spec fields get
pruned on the way back.
