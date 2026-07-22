# CR compatibility 4.10 → 6.7 — pruning, deltas, rollback

## API compatibility baseline

Both rancher-logging 4.10-era and upstream 6.7.0 serve
`logging.banzaicloud.io/v1beta1` (storage) + non-storage `v1alpha1` on the big
five kinds. Even the 3.17.10-era CRDs use the same group/version. No conversion
webhooks, no storedVersions surgery — schema replacement in both directions.

## Silent pruning — the real restore risk

The 4.10→6.7 CRD schema diff removes these fields. They do **not** cause
validation errors: structural-schema pruning means `kubectl apply` **succeeds and
silently drops them**.

| Removed field | Where | Removed in | Migration action |
|---|---|---|---|
| `spec.filters[].sumologic` | Flow/ClusterFlow (+ Logging defaultFlow/globalFilters) | 5.0 | replace or accept loss |
| `spec.filters[].enhanceK8s` | Flow/ClusterFlow (+ same) | 5.0 | metadata now via fluent-bit k8s filter |
| `spec.sumologic` (output plugin) | Output/ClusterOutput | 5.0 | switch to `http`/`syslog` to Sumo, or custom image |
| `spec.enabledNamespaces` | ClusterOutput | ≤6.x | use `protected` + Flow-side control |
| `spec.nodeAgents` | Logging | 6.0 | see §nodeAgents |

### Pruning pre-flight (run before any cutover)

After the 6.7.0 CRDs are applied (or against a scratch cluster with them):

```bash
for f in flows clusterflows outputs clusteroutputs loggings; do
  kubectl apply --dry-run=server -o yaml -f $f.yaml > $f.dryrun.yaml 2>$f.errors
  diff <(yq -P 'sort_keys(..)' $f.yaml) <(yq -P 'sort_keys(..)' $f.dryrun.yaml) \
    > $f.pruned.diff || echo "REVIEW $f.pruned.diff"
done
```

Any diff line that isn't server-side bookkeeping (managedFields, generation,
resourceVersion) is a field the new schema will eat. Grep the backups directly
too — faster signal:

```bash
grep -l 'sumologic\|enhanceK8s\|enabledNamespaces\|nodeAgents' *.yaml
```

## §nodeAgents — the Windows dead-end

Rancher's root Logging templates `spec.nodeAgents` only when Windows support is
enabled (`windowsEnabled` chart helper). Linux-only clusters: nothing to lose —
confirm with `kubectl get nodeagents -A` (empty) and grep the Logging backup.
Windows clusters: NodeAgent is **removed** in 6.0 with no equivalent (Telemetry
Controller is the nominal successor and not production-ready). Options: keep a
separate legacy collector for Windows nodes, or defer the migration for those
clusters. Do not proceed expecting Windows logs to survive.

## §journald — the rke2/k3s host-log delta

`additionalLoggingSources.rke2` (and k3s/rke/aks/eks/gke, kubeAudit) deploys a
**plain fluent-bit DaemonSet outside operator control**
(`<release>-rke2-journald-aggregator` + ConfigMap) tailing
`_SYSTEMD_UNIT=rke2-server/rke2-agent` and
`/var/lib/rancher/rke2/agent/logs/kubelet.log`, honoring the `systemdLogPath`
value (default `/run/log/journal`). The upstream chart has no equivalent value.
Choose per cluster:

1. **Port it**: keep the DaemonSet+ConfigMap as your own manifests (it's
   self-contained; strip the Rancher labels), or
2. **Replace with HostTailer** (operator-native):
   ```yaml
   kind: HostTailer
   spec:
     systemdTailers:
       - {name: rke2-server, systemdFilter: rke2-server.service}
       - {name: rke2-agent, systemdFilter: rke2-agent.service}
     fileTailers:
       - {name: kubelet, path: /var/lib/rancher/rke2/agent/logs/kubelet.log}
   ```
   plus a Flow selecting the host-tailer pod (see logging-operator skill,
   recipes.md §events-and-host-logs).

Either way, decide BEFORE deleting the old DaemonSet in runbook step 4.

## Other chart-level deltas (rancher-logging adds vs upstream)

- Values-driven default CRs (`logging.enabled` root Logging named
  `<release>-root`, FluentbitAgent, ClusterFlows/Outputs from values) — after
  migration these are plain CRs you own directly; nothing regenerates them.
- `global.cattle.systemDefaultRegistry` image rewriting — upstream has **no**
  global registry rewrite; every image override is explicit (airgap-prep.md).
- `disablePvc: true` is Rancher's DEFAULT (fluentd buffers on emptyDir!). Check
  `helm get values` — many Rancher installs never had durable buffers to
  preserve; the upstream default is a 20Gi PVC. Decide deliberately.
- SELinux option (`rke_logreader_t`), Windows path prefixes, `logging-admin`/
  `logging-view` aggregated ClusterRoles (recreate if user-facing RBAC on
  flows/outputs is still wanted — see security-urgency.md before granting).
- Chart annotation `catalog.cattle.io/auto-install: rancher-logging-crd=match` —
  why the CRD chart appeared automatically in Rancher Apps.

## §escaping — rendered-config diff across 6.6

4.10 renders CRD/secret values into fluent.conf **unescaped**; 6.6.0+ escapes
(the CVE fix; corrected in 6.7.0). For any Output/Flow value containing quotes,
backslashes, `#` or newlines the rendered config text changes. Procedure: capture
`fluentd.conf.pre` (runbook step 0), diff post-migration; investigate any change
that is not an image/version line or a known-escaped value. Exact per-character
table is unverified (improvement-backlog) — trust the diff, not assumptions.

## §rollback

Going back 6.7 → 4.10:

1. Old CRDs back: `helm show crds` from the rancher-logging-crd chart (or the
   backed-up chart assets) → `kubectl apply --server-side --force-conflicts -f -`
   (same size limits apply). 6.x-only spec fields on CRs prune on next write —
   acceptable.
2. Strategy A path: re-create the two backed-up `sh.helm.release.v1.*` Secrets
   (`kubectl apply -f helm-release-secrets.yaml`) — Helm/Rancher sees the old
   releases again; or fresh `helm install` of the rancher charts with the saved
   values. Because the kubectl-apply CRD path never changed Helm ownership
   metadata (`meta.helm.sh/release-name: rancher-logging-crd` still on the CRDs),
   Rancher-chart reinstall/upgrade just works.
3. If CRDs WERE Helm-adopted into the upstream release (the subchart path),
   flip `app.kubernetes.io/managed-by` + `meta.helm.sh/release-*` back first.
4. Uninstall the upstream operator release; the recreated/reinstalled Rancher
   operator reconciles the data plane back to 4.10 images.

Storage-version note: both directions keep v1beta1 storage + status subresource —
no `.status.storedVersions` editing needed.
