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

## 2026-05-30 — release-grounding pass (House Rule #8)

Ran `freshen` focused on **version grounding**: confirmed each gh-backed
component's newest version against the **`gh api .../releases/latest`** scalar —
the only signal that survives the tool's confirmation bias (existence/list/per-tag
queries rubber-stamp plausible fakes; see `references/version-verification.md`).
This was a release-grounding overlay, **not** a full docs-matrix re-sift; per-row
`Last verified:` dates below remain the 2026-05-28 sift date.

- **Confirmed fresh (latest scalar matches compat newest):** RKE2
  v1.36.1+rke2r1 · Rancher v2.14.2 · Harvester v1.8.0 · Cilium v1.19.4 ·
  cert-manager v1.20.2 · Kyverno v1.18.1 · KEDA v2.19.0 · Traefik v3.7.1 ·
  Rook v1.19.6 · OpenEBS v4.4.0 · Zalando v1.15.1 · ECK v3.4.0.
- **Fixed fabrications:** Argo CD — removed invented `v3.2.10`/`v3.2.12` + "CVE
  fixed in 3.2.10" (real latest `v3.4.3`); Harbor — flagged `§ 2.15`
  **[CORRECTED 2026-05-31 — this was wrong: 2.15.x is real; see correction below]**.
- **Version-drift applied:** NVIDIA GPU Operator — latest `v26.3.2`, one patch
  ahead of documented `§ 26.3.1` (existence grounded; content sift deferred).
- **NOT gh-groundable (see `references/improvement-backlog.md`):** Ceph (no
  `releases/latest`), GitLab (not on GitHub), Grafana Mimir (`releases/latest`
  returns the app tag, not the chart `kubeVersion`). Ground via docs / GitLab
  API / `Chart.yaml`.

## 2026-05-31 — correction: `releases/latest` is recency, not rank

The 2026-05-30 pass above anchored "newest version" on `gh api .../releases/latest`
and called it "the only signal that survives confirmation bias." **That method was
wrong.** `releases/latest` is the most-recently-*published* (or maintainer-pinned)
release — **not** the highest semantic version. Projects maintaining multiple lines
in parallel publish out of order (a back-ported patch to an old line, or a fix not
needed in the higher line), so `releases/latest` can sit *below* a real higher minor.

- **Harbor:** `§ 2.15` is **real** (gh-enumerated `v2.15.1` / `v2.15.0`, no version
  named in the query). `releases/latest` = `v2.14.4` is the maintained 2.14 line, not
  the ceiling. The 2026-05-30 "invented `§ 2.15`" finding is **reversed**;
  `compat/harbor.md` banner + `§ 2.15` header corrected. (2.15 is still tested only
  to k8s 1.34 — no 1.35.)
- **Method fix applied to** `version-verification.md` (§ Three orthogonal failure
  modes), `tooling.md`, `cluster-survey.md`, `compat/README.md`, `SKILL.md` #8:
  enumerate the real tag list (no candidate named) and reason **per minor line**;
  never reject a higher enumerated minor because it exceeds `releases/latest`;
  confirm a surprising tag with `gh release view <tag>`, not against the scalar.
- **Re-ground recommended:** any other compat row whose "newest line" was decided by
  the 2026-05-30 `releases/latest`-anchored pass should be re-checked per-minor-line
  on the next `freshen`.

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

## Tetragon

- URL: https://github.com/cilium/tetragon/releases
- Kernel-floor source: https://tetragon.io/docs/installation/faq/ (also in-repo at `docs/content/en/docs/installation/faq.md`)
- Chart source: `install/kubernetes/tetragon/Chart.yaml` at release tags (chart == app version; no `kubeVersion:`)
- Probe: anchor `gh api repos/cilium/tetragon/releases/latest --jq '.tag_name'`; enumerate minors `gh api 'repos/cilium/tetragon/releases?per_page=100' --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' | sort -V`; sift kernel floor from the FAQ doc, breaking changes from each in-scope release's "Upgrade notes".
- Note: separate component from Cilium core. The k8s axis is loose; the **kernel** axis is load-bearing.
- Last verified: 2026-05-30  (release-grounded: `releases/latest` = `v1.7.0`; minors 1.7/1.6/1.5 enumerated)

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
