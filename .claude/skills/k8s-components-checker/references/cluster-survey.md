# cluster-survey.md — canonical survey commands

The operator runs these from their workstation with `KUBECONFIG` pointed at one
target cluster. All commands are read-only. Output is parsed in-memory; nothing
is written to disk.

Each phase below runs in order; later phases depend on earlier output. Phases
are independent enough that a partial survey is still useful — if pluto isn't
installed, skip Phase 3b and note `pluto: unavailable` in the verdict.

## Phase 1: cluster identity

```bash
# Server k8s version + RKE2 build string
kubectl version --output=json | jq -r '.serverVersion.gitVersion'
# example output: v1.32.12+rke2r1

# Nodes — count, roles, OS, container runtime, kernel
kubectl get nodes -o wide
```

**Parsing rules:**

- The k8s minor is `serverVersion.major + "." + serverVersion.minor` (e.g. `1.32`).
  The patch and `+rke2rN` suffix do not affect compat decisions — compat is
  driven by the k8s minor. Record the patch + suffix in the verdict header for
  audit, but verdict against the minor.
- If `kubectl version` emits the "version difference exceeds the supported
  minor version skew" warning, that's about the operator's local kubectl, not
  about the cluster's component skew. Do not surface it in the verdict.

## Phase 2: component detection

Three complementary approaches. Run all three and merge — each catches what the
others miss.

### 2a. CRD api-group fingerprint

CRDs are the cheapest, most reliable signal that a component is installed. Map
api-group → registry component:

```bash
kubectl get crd --no-headers \
  | awk '{split($1,a,"."); g=""; for(i=2;i<=length(a);i++){g=g a[i] (i<length(a)?".":"") }; print g}' \
  | sort | uniq -c | sort -rn
```

| CRD api-group | Registry component |
|---|---|
| `cilium.io` | Cilium |
| `cert-manager.io` | cert-manager |
| `kyverno.io` | Kyverno |
| `keda.sh` | KEDA |
| `argoproj.io` | Argo CD |
| `goharbor.io` (when via operator) | Harbor (note: most Harbor installs are Helm-only, no CRDs) |
| `traefik.io` (+ legacy `containo.us`) | Traefik |
| `ceph.rook.io`, `objectbucket.io` | Rook (operator) |
| `ceph.rook.io/v1` `CephCluster` etc. | Ceph (storage; version lives inside the CR) |
| `openebs.io` | OpenEBS |
| `cattle.io`, `management.cattle.io` | Rancher |
| `harvesterhci.io` | Harvester |
| `kubevirt.io` (when running on Harvester) | Harvester (bundled KubeVirt) |
| `elasticsearch.k8s.elastic.co` | ECK |
| `acid.zalan.do` | Zalando postgres-operator |
| `monitoring.grafana.com` (Mimir-specific CRs are uncommon) | Grafana Mimir (mostly via Helm — see 2b) |
| `nvidia.com` (`ClusterPolicy`, etc.) | NVIDIA GPU Operator |

A component without CRDs (e.g. Grafana Mimir, vanilla Harbor) is invisible to
this scan and shows up in 2b instead.

### 2b. Helm releases

```bash
helm list -A -o json
```

Returns an array of objects with keys: `name`, `namespace`, `revision`,
`updated`, `status`, `chart`, `app_version`.

**Parsing:**

- `chart` is `<chart-name>-<chart-version>`, e.g. `cilium-1.19.4`, `cert-manager-v1.17.1`, `argo-cd-8.0.17`. Strip the trailing semver to get the chart name; record the chart version.
- `app_version` is the upstream app version (sometimes prefixed `v`, sometimes not — normalize).
- For chart_metadata components (Grafana Mimir), `chart` carries the chart version that maps to a `Chart.yaml` `kubeVersion:` constraint; this is the load-bearing axis for that component.

Map chart-name → registry component:

| Chart name | Registry component |
|---|---|
| `cilium` | Cilium |
| `cert-manager` | cert-manager |
| `kyverno` (and `kyverno-policies`) | Kyverno |
| `keda` | KEDA |
| `argo-cd` | Argo CD |
| `harbor` | Harbor |
| `traefik` | Traefik |
| `rook-ceph`, `rook-ceph-cluster` | Rook (operator chart) / Ceph (cluster chart) |
| `openebs`, `mayastor`, `cstor-operator`, `localpv-provisioner` | OpenEBS (engine-specific) |
| `rancher` | Rancher |
| `harvester` | Harvester |
| `eck-operator`, `eck-stack`, `elasticsearch`, `kibana` | ECK |
| `postgres-operator` | Zalando postgres-operator |
| `mimir-distributed` | Grafana Mimir |
| `gpu-operator` | NVIDIA GPU Operator |
| `gitlab` | GitLab |

### 2c. Pod-label fallback

For components installed without Helm and without registered CRDs:

```bash
kubectl get pods -A -o json \
  | jq -r '.items[] | {ns: .metadata.namespace, name: .metadata.name,
                       labels: .metadata.labels, images: [.spec.containers[].image]}'
```

Component images are the last-resort identifier. The image tag is usually the
version (e.g. `quay.io/cilium/cilium:v1.19.4`). Lower confidence than 2a/2b
because tags can lie; cross-reference with a `kubectl exec ... -- <binary>
--version` if it matters.

### Component-version merge

After 2a + 2b + 2c, produce a deduplicated list of `(component, version)`
tuples covering the 18 registry entries that are present. Prefer Helm chart
version when available (most authoritative for what the operator deployed);
fall back to CRD-bearing pod's image tag; last fall back to label inspection.

For multi-axis components (Harvester, ECK, Rancher), capture all axis values
the survey can see (e.g. Rancher chart version + downstream cluster k8s
versions if managed clusters are visible via `kubectl get clusters.cluster.x-k8s.io`).

## Phase 3: deprecated-API liability

Two paths. Run both; reconcile.

### 3a. Apiserver counter — canonical but operationally tricky

```bash
# DOES NOT WORK on most clusters — RBAC limits the cluster-root /metrics scrape:
kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis{'

# Real path: query a kube-apiserver pod via the apiserver-itself proxy:
APISERVER_POD=$(kubectl get pods -n kube-system -l component=kube-apiserver -o name | head -1)
kubectl get --raw "/api/v1/namespaces/kube-system/${APISERVER_POD#pod/}/proxy/metrics" \
  | grep '^apiserver_requested_deprecated_apis{'
```

**Gotchas:**

- The metric is a **counter**, not a gauge. It increments per request. It
  **resets when the apiserver process restarts**. A zero reading does not
  prove the cluster has never served a deprecated API — only that this
  apiserver pod hasn't served one since its last restart. Cross-check
  apiserver pod ages via `kubectl get pods -n kube-system | grep apiserver`
  and treat a clean reading from a recently-restarted apiserver as
  inconclusive.
- RBAC: the pod-proxy approach requires the operator's bound role to allow
  `get pods/proxy` on `kube-system`. Cluster-admin trivially has this.
  Restricted operators may need to read the metric from a sidecar (e.g.
  prometheus scraping the apiserver's mTLS endpoint with a configured token).
- On HA control planes (multiple apiservers), poll each pod; counters are
  per-process.

**Interpreting hits:** each line includes labels naming the deprecated
`group/version/resource` and the `removed_release` minor:

```
apiserver_requested_deprecated_apis{group="autoscaling",version="v2beta2",
  resource="horizontalpodautoscalers",subresource="",removed_release="1.26"} 1432
```

If `removed_release` ≤ the upgrade target minor, the API will be gone after
the upgrade — that's a `✗ blocker` row in the verdict. Trace the source via
audit logs or by querying the resource directly to identify the workload
emitting the deprecated call.

### 3b. Pluto static scan — primary fallback

Pluto bundles a deprecated-API rule set in the binary. Two scan modes:

```bash
# Live cluster: scan currently-served API resources
pluto detect-api-resources --target-versions k8s=v1.32

# Static: scan all Helm release manifests for deprecated apiVersions
pluto detect-helm --target-versions k8s=v1.32
```

**Gotcha — pluto's default target is stale.** Without `--target-versions`,
pluto uses baselines like `k8s=v1.25.0`, `cert-manager=v1.5.3`,
`istio=v1.11.0` — frozen years ago. Always pass `--target-versions
k8s=v<current-minor>` (and the relevant component minors) explicitly. Verify
with `pluto list-versions` if uncertain about the bundled rule set's age.

For upgrade-readiness, run twice:
- Once against current k8s minor → catches APIs that are deprecated now.
- Once against target k8s minor → catches APIs that will be **removed** at the upgrade.

### 3c. Why both 3a and 3b

| Source | Strength | Weakness |
|---|---|---|
| apiserver counter (3a) | Reports what was **actually served** — proves real liability | Counter resets; restricted by RBAC; tedious to scrape |
| pluto (3b) | Works offline against manifests; covers things not yet served but staged | Bundled rule set ages; only knows about APIs the pluto version recognizes |

Conflict resolution: if 3a shows hits and 3b doesn't, trust 3a (the cluster
saw it). If 3b shows hits and 3a doesn't, the API may be staged but unused —
verdict row says `⚠ staged deprecated API` (not `✗ blocker`) until something
actually invokes it.

## Phase 4: kubent is dead

Do not run `kubent` (`doitintl/kube-no-trouble`). Last stable 0.7.3; last
commit early 2025; deprecation rulesets stop at k8s 1.32. Will under-report on
any current cluster. If a runbook somewhere mentions kubent, replace with the
3a / 3b pair above. See `references/tooling.md`.

## Phase 4b: ground version specifics (online only)

Before assembling the verdict, if the workstation has internet + `gh`: **ground
every specific version the verdict will cite** — the recommended target patch,
any "CVE fixed in vX.Y.Z", any "latest"/"newest minor" claim — per
`references/version-verification.md` (House Rule #8). The k8s support *windows*
come from the registry; the version *numbers* must be confirmed against real
releases.

Method (anti-confirmation — existence/list queries get rubber-stamped, so never
name a candidate version in the query):

```bash
# anchor: the real ceiling (no candidate version in the command)
gh api repos/<org>/<repo>/releases/latest --jq '.tag_name'
# derive the real latest patch of a minor — enumerate, then take the max yourself
gh api 'repos/<org>/<repo>/releases?per_page=100' \
  --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' | grep -E '^v?1\.20\.' | sort -V | tail -1
```

Reject any cited version newer than `releases/latest`. If a "fixed-in" / "latest"
claim from the compat file contradicts what `gh` returns, **the compat file is
wrong** — verdict on the grounded value and flag the registry for a `freshen`.
If **offline**, mark those specifics `UNVERIFIED` and verdict on the minor-level
window. Component→repo map is in `references/version-verification.md`.

## Phase 5: assemble the verdict

Inputs:
- k8s current minor (Phase 1)
- k8s target minor (operator-provided)
- detected (component, version) tuples (Phase 2)
- deprecated-API hits (Phase 3, both sources, reconciled)

For each detected component:
1. Read its row in `references/components.md`.
2. Read `references/compat/<component>.md` § <detected-version>.
3. Cross-reference against current minor and target minor.
4. Classify into the verdict row: `✓ ready`, `⚠ needs bump`, `⚠ ordering`,
   `✗ blocker`, or `✗ out of registry scope`.
5. Cite the exact `references/compat/<component>.md § <version>` block.

For deprecated-API hits, classify by `removed_release`:
- `removed_release` ≤ current minor → already broken; flag as `✗ blocker`
  regardless of upgrade scope.
- current minor < `removed_release` ≤ target minor → will break at upgrade;
  `✗ blocker`.
- `removed_release` > target minor → not blocking this upgrade; `⚠ staged
  deprecated API` for the next planning cycle.

Order the `action plan` to respect known upgrade-ordering rules from the
compat files (e.g. Harvester before RKE2; Rancher before downstream-cluster
RKE2 bumps when relevant). Emit the verdict per the format in SKILL.md.

## Air-gap discipline

Every command in Phases 1–5 runs against the cluster's own apiserver — no
internet calls. Pluto runs locally with a bundled rule set. The skill's own
`references/` is read locally. Confirm zero outbound by running the survey
under a network policy that blocks egress; results should be identical.

**One sanctioned exception:** Phase 4b version grounding deliberately calls
`gh` / endoflife.date when the workstation is online. That traffic targets
*release metadata*, never the cluster, and is required by House Rule #8 — it
does not weaken the cluster survey's zero-outbound property. A genuinely
air-gapped run skips Phase 4b and marks version specifics `UNVERIFIED`.
