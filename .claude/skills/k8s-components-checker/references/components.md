# components.md — the registry

19 components. Community editions only. Lookup table the survey reads.

Each entry carries:

- **axis_type** — `single` (single k8s axis) or `multi` (two or more dimensions the operator picks independently)
- **truth_source_type** — `published_matrix` | `release_notes` | `chart_metadata` (branches the lookup; see SKILL.md)
- **source** — canonical URL the freshen probe reads. Also indexed in `references/sources.md`.
- **min_tracked_version** — registry floor. Default = current minor + prior 2 (~18 months). Operator overrides win; freshen leaves overridden rows alone.
- **compat file** — `references/compat/<name>.md` carries per-version compatibility signal (sifted from matrix, docs, release notes, FAQ — whatever the truth_source_type dictates).

Detection patterns (how a survey identifies a component as installed) live in `references/cluster-survey.md`.

---

## Single-axis components

k8s-version is the only independent axis. The compat file refines with
breaking-change / CRD / ordering signal per minor.

| Component | truth_source_type | min_tracked_version | primary source | compat file |
|---|---|---|---|---|
| RKE2 (anchor) | release_notes | 1.31 | https://github.com/rancher/rke2/releases | `compat/rke2.md` |
| Cilium | published_matrix | 1.17 | https://docs.cilium.io/en/stable/network/kubernetes/compatibility/ | `compat/cilium.md` |
| cert-manager | published_matrix | 1.17 | https://cert-manager.io/docs/releases/ | `compat/cert-manager.md` |
| Kyverno | published_matrix | 1.16 | https://kyverno.io/docs/installation/ | `compat/kyverno.md` |
| KEDA | published_matrix | 2.17 | https://keda.sh/docs/latest/operate/cluster/ | `compat/keda.md` |
| Argo CD | published_matrix | 3.0 | https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/ | `compat/argo-cd.md` |
| Harbor | release_notes | 2.13 | https://goharbor.io/docs/ (per-release k8s + Helm minimums) | `compat/harbor.md` |
| Traefik | release_notes | 3.5.0 | https://github.com/traefik/traefik/releases | `compat/traefik.md` |
| Rook (operator) | release_notes | 1.17 | https://github.com/rook/rook/releases | `compat/rook.md` |
| Ceph (storage) | release_notes | 18.2 | Rook release notes (authoritative Rook↔Ceph matrix) + https://docs.ceph.com/en/latest/releases/ | `compat/ceph.md` |
| OpenEBS | release_notes | 4.2 | https://openebs.io/docs/releases (engine-specific) | `compat/openebs.md` |
| GitLab | published_matrix | 8.11 | https://docs.gitlab.com/charts/installation/cloud/ (k8s/Helm chart compat) | `compat/gitlab.md` |
| NVIDIA GPU Operator | published_matrix | 25.3 | https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html | `compat/nvidia-gpu-operator.md` |

Every row's `axis_type` is `single`. Multi-axis rows live as stanzas below.

### Override pattern

When the operator runs a version older than the default floor, set
`min_tracked_version` explicitly. Example row (replace the
`_set by freshen_` placeholder):

```
| Cilium | single | 1.14 | https://docs.cilium.io/... | compat/cilium.md |
```

Freshen sees the explicit semver and stops trimming the row.

### Cross-component relationships

Some single-axis components carry their compat data via another component's
release notes:

- **Ceph ← Rook.** The Rook operator's release notes are the authoritative
  source for "Rook N supports Ceph X.Y..Z" pairings. Ceph's
  `compat/ceph.md` sifts from Rook releases first, then ceph.io for the
  upstream Ceph EOL line and standalone breaking changes. When verdicting a
  Ceph row, cite Rook's compat-file block as the primary source for the
  k8s/Rook compat path, and ceph.io for Ceph-only signal (e.g. OSD encoding
  changes between Reef/Squid/Tentacle).

If another component picks up a similar dependency in the future, add it here
so the survey knows where the truth actually lives.

---

## Multi-axis — stanzas

### Rancher (community) — `axis_type: single`, `truth_source_type: release_notes`

- **Axis:** Kubernetes version that the Rancher management cluster runs on.
- **Cadence:** community minors land Mar / Jul / Nov (Prime: Apr / Aug / Dec).
  Community misses end-of-line Prime patches. 18-month community support from 2.9 onward.
- **Source:** https://github.com/rancher/rancher/releases
- **compat file:** `compat/rancher.md`
- **min_tracked_version:** 2.12

Operator manages downstream-cluster k8s versions outside Rancher; the
downstream-provisioning axis is not in scope here.

### Harvester (community) — `axis_type: multi`, `truth_source_type: release_notes`

- **Axis 1 (bundled stack):** locked to the Harvester version — embedded RKE2, KubeVirt, Longhorn, SLE Micro all move together.
- **Axis 2 (management):** which Rancher version can manage this Harvester; `harvester-ui-extension` is pinned per Harvester↔Rancher pair.
- **Community EOL rule:** from Harvester 1.5+, `x.y.0` = community, `x.y.[1-z]` = Prime. Community support for `x.y` ends when `x.(y+1).1` ships (~4-month tail; minors Apr/Aug/Dec).
- **Ordering rule:** check `compat/harvester.md` for Harvester↔RKE2 pairing before any RKE2 minor bump. Missing this turns the upgrade into a rebuild.
- **Source:** https://github.com/harvester/harvester/wiki (per-version compatibility pages — filter to community columns).
- **compat file:** `compat/harvester.md`
- **min_tracked_version:** 1.5.0

### ECK (Elastic Cloud on Kubernetes) — `axis_type: multi`, `truth_source_type: published_matrix`

- **Axis 1:** Supported Kubernetes / OpenShift versions.
- **Axis 2:** Supported Elastic Stack (Elasticsearch / Kibana / Beats / APM) versions managed by the operator.
- **Source:** ECK docs "supported versions" page + https://www.elastic.co/support/matrix
- **compat file:** `compat/eck.md`
- **min_tracked_version:** 3.2.0

---

## No published matrix

### Zalando postgres-operator — `axis_type: multi`, `truth_source_type: release_notes`

- **Axes:** operator version → bundled Spilo image → bundled PostgreSQL majors.
- **k8s floor:** loose; operator generally works on currently-supported minors.
- **Watch:** the axis that matters is what Postgres major a given operator version's Spilo bundles, and whether `kubernetes_use_configmaps` semantics have shifted.
- **Source:** https://github.com/zalando/postgres-operator/releases + the Spilo image tag matrix referenced from each release.
- **compat file:** `compat/zalando-postgres-operator.md`
- **min_tracked_version:** 1.13.0

### Grafana Mimir — `axis_type: single`, `truth_source_type: chart_metadata`

- **Truth lives in:** `mimir-distributed` chart `Chart.yaml` — `kubeVersion:` constraint + chart-version → Mimir-app-version mapping per tagged release.
- **Helm gotcha:** chart exposes `kubeVersionOverride` because Helm otherwise uses the kubectl *client* version for resource compatibility, which may not match the cluster server version. The compat file calls this out per chart minor.
- **Source:** https://github.com/grafana/mimir → `operations/helm/charts/mimir-distributed/Chart.yaml` at chart-release tags.
- **compat file:** `compat/mimir.md`
- **min_tracked_version:** 5.7

### Tetragon (Cilium runtime security) — `axis_type: multi`, `truth_source_type: release_notes`

- **Axis 1 (k8s):** loose — Tetragon publishes no k8s support matrix and the
  `tetragon` chart sets no `kubeVersion:`. Runs on any currently supported minor.
- **Axis 2 (node kernel) — the load-bearing one:** eBPF/BTF kernel floor.
  Minimum Linux **4.19** (CI: 4.19/5.4/5.10/5.15/bpf-next); **arm64 needs ≥ 5.10**;
  **BTF required**; enforcement needs `CONFIG_BPF_KPROBE_OVERRIDE`, the LSM sensor
  needs `CONFIG_BPF_LSM` (≥ 5.7). The k8s minor rarely blocks Tetragon; the node
  OS/kernel does.
- **Sibling-not-Cilium:** separate component from Cilium core — own release train
  (`cilium/tetragon`), own chart, runs standalone (no Cilium CNI required). Shares
  the `cilium.io` CRD api-group, so detect via the `tracingpolicies.cilium.io` CRD
  + `tetragon` DaemonSet, not the api-group alone.
- **Source:** https://github.com/cilium/tetragon/releases + https://tetragon.io/docs/installation/faq/ (kernel floor).
- **compat file:** `compat/tetragon.md`
- **min_tracked_version:** 1.5

---

## Adding a component

New component arrives in scope:

1. Decide `axis_type` (single only if the operator picks one k8s dimension; multi if two or more independent picks).
2. Decide `truth_source_type` (vendor matrix → `published_matrix`; GitHub releases → `release_notes`; Helm chart → `chart_metadata`).
3. Add a row (single-axis) or a stanza (multi-axis) above.
4. Add the source URL to `references/sources.md` so freshen picks it up.
5. Create the stub `references/compat/<name>.md` per the README shape.
6. Run `skill-improver freshen k8s-components-checker` from an internet-accessible client to populate.

## Removing a component

If the operator stops running a component entirely:

1. Delete its row / stanza here.
2. Delete its `references/compat/<name>.md`.
3. Delete its row in `references/sources.md`.

No "deprecated" or "retired" sections — gone is gone.
