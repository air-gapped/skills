# sources.md — URL index for freshen

One row per component. Each row carries the canonical source URL freshen
probes, optional pin notes, and the `Last verified:` stamp.

`skill-improver freshen` reads this file, probes each URL, sifts the upstream
content into `references/compat/<comp>.md`, and updates the
`Last verified:` date. Surveys at use time read this only to surface
staleness — a row past 90 days appears in the verdict as a soft warning.

First freshen run: 2026-05-28. Re-run `/skill-improver freshen
k8s-components-checker` at quarterly cadence or before any upgrade plan that
relies on a row older than 90 days.

## RKE2 (anchor)

- URL: https://github.com/rancher/rke2/releases
- Probe: `gh release list --repo rancher/rke2 --limit 50`
- Last verified: 2026-05-28

## Rancher

- URL: https://github.com/rancher/rancher/releases
- Probe: `gh release list --repo rancher/rancher --limit 30`
- Note: filter to community minors (Mar / Jul / Nov). Ignore Prime-flavored release notes.
- Last verified: 2026-05-28

## Harvester

- URL: https://github.com/harvester/harvester/wiki
- Secondary URL: https://github.com/harvester/harvester/releases
- Probe: WebFetch the per-version compatibility wiki page; filter to community columns.
- Last verified: 2026-05-28

## Cilium

- URL: https://docs.cilium.io/en/stable/network/kubernetes/compatibility/
- Secondary URL: https://github.com/cilium/cilium/releases
- Probe: WebFetch docs page for the matrix; `gh release list --repo cilium/cilium` for per-version notes.
- Last verified: 2026-05-28

## cert-manager

- URL: https://cert-manager.io/docs/releases/
- Secondary URL: https://github.com/cert-manager/cert-manager/releases
- Probe: WebFetch releases page; `gh release list --repo cert-manager/cert-manager`.
- Last verified: 2026-05-28

## Kyverno

- URL: https://kyverno.io/docs/installation/
- Secondary URL: https://github.com/kyverno/kyverno/releases
- Probe: WebFetch installation page for compatibility table; `gh release list --repo kyverno/kyverno`.
- Last verified: 2026-05-28

## KEDA

- URL: https://keda.sh/docs/latest/operate/cluster/
- Governance / support window: https://github.com/kedacore/governance/blob/main/SUPPORT.md
- Secondary URL: https://github.com/kedacore/keda/releases
- Probe: WebFetch docs + governance; `gh release list --repo kedacore/keda`.
- Last verified: 2026-05-28

## Argo CD

- URL: https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/
- Secondary URL: https://github.com/argoproj/argo-cd/releases
- Probe: WebFetch tested-versions page; `gh release list --repo argoproj/argo-cd`.
- Last verified: 2026-05-28

## Harbor

- URL: https://goharbor.io/docs/
- Secondary URL: https://github.com/goharbor/harbor/releases
- Probe: WebFetch docs index for release notes pages; `gh release list --repo goharbor/harbor`.
- Note: k8s minimums change with chart versions; cross-reference the harbor-helm chart at https://github.com/goharbor/harbor-helm.
- Last verified: 2026-05-28

## Traefik

- URL: https://github.com/traefik/traefik/releases
- Probe: `gh release list --repo traefik/traefik --limit 30`
- Note: extract k8s API minimums from "Kubernetes" section of release notes; Traefik does not publish a separate matrix.
- Last verified: 2026-05-28

## Rook (operator)

- Primary URL: https://github.com/rook/rook/releases
- Secondary URL: https://rook.io/docs/rook/latest-release/
- Probe: `gh release list --repo rook/rook --limit 30`; for each in-scope release, `gh release view <tag>` and sift k8s floor + supported Ceph versions; WebFetch docs landing page as cross-reference.
- Last verified: 2026-05-28

## Ceph (storage)

- Primary source: Rook release notes (each Rook release names the supported Ceph minor range). See `compat/rook.md` first.
- Secondary URL: https://docs.ceph.com/en/latest/releases/ (upstream Ceph EOL line + standalone breaking changes — Reef / Squid / Tentacle).
- Probe: Read `compat/rook.md` for Rook↔Ceph pairings; WebFetch ceph.io releases page for upstream EOL signal + OSD encoding / cluster-wide breaking changes.
- Note: Ceph's k8s axis collapses through Rook — the cluster doesn't see Ceph version against k8s directly; it sees Rook version against k8s, and Rook bounds Ceph.
- Last verified: 2026-05-28

## OpenEBS

- URL: https://openebs.io/docs/releases
- Secondary URL: https://github.com/openebs/openebs/releases
- Probe: WebFetch releases page (engine-specific — Mayastor, cStor, LocalPV); `gh release list --repo openebs/openebs`.
- Last verified: 2026-05-28

## GitLab

- URL: https://docs.gitlab.com/
- Secondary URL: https://docs.gitlab.com/charts/installation/cloud/ (k8s/Helm chart compat)
- Probe: WebFetch docs sections covering k8s compat and Helm chart minimums.
- Note: operator runs the EE binary as CE; ignore EE-only features in the sift.
- Last verified: 2026-05-28

## ECK

- URL: https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-supported.html
- Stack-matrix URL: https://www.elastic.co/support/matrix
- Probe: WebFetch supported-versions page; cross-reference stack matrix.
- Last verified: 2026-05-28

## Zalando postgres-operator

- URL: https://github.com/zalando/postgres-operator/releases
- Probe: `gh release list --repo zalando/postgres-operator --limit 30`; sift bundled Spilo + Postgres major + `kubernetes_use_configmaps` semantics.
- Last verified: 2026-05-28

## Grafana Mimir (chart_metadata)

- URL: https://github.com/grafana/mimir/blob/main/operations/helm/charts/mimir-distributed/Chart.yaml
- Probe: `gh api repos/grafana/mimir/contents/operations/helm/charts/mimir-distributed/Chart.yaml` at each chart-release tag; extract `kubeVersion:` constraint and `appVersion:`.
- Last verified: 2026-05-28

## NVIDIA GPU Operator

- URL: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html
- Secondary URL: https://github.com/NVIDIA/gpu-operator/releases
- Probe: WebFetch platform-support page; `gh release list --repo NVIDIA/gpu-operator`.
- Note: driver-version-per-release is captured in the compat file, not here.
- Last verified: 2026-05-28

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes (historical reference the operator wants frozen).
- `Pinned: <semver>` under a row tells freshen not to auto-advance past that version even if upstream ships newer; useful when the operator deliberately stays on an older line.
