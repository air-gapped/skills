# sources.md — URL index for freshen

Freshened: 2026-11-25 — every row probed across all 20 components; the registry sync check reports no drift after regeneration (195 items cleared).

One row per component. Each row carries the canonical source URL freshen
probes, optional pin notes, and the `Last verified:` stamp.

`skill-improver freshen` reads this file, probes each URL, sifts the upstream
content into `references/compat/<comp>.md`, and updates the
`Last verified:` date. Surveys at use time read this only to surface
staleness — a row past 90 days appears in the verdict as a soft warning.

First freshen run: 2026-05-28. Re-run `/skill-improver freshen
k8s-components-checker` at quarterly cadence or before any upgrade plan that
relies on a row older than 90 days.

## 2026-06-02 — floor-override pass (operator-directed, migration sources)

Operator-requested floor overrides — the operator runs (or migrates clusters off)
versions below the rolling-default floor, so the registry was extended **downward**
to cover them rather than abstaining. All version numbers grounded via no-candidate
enumeration (`gh api .../releases?per_page=100`, per-minor-line `sort -V`); House
Rule #8. Five compat files backfilled + their `components.md` floor cells + headers:

- **Harbor floor 2.13 → 2.11.** `compat/harbor.md` §2.12 (chart 1.16.x, app v2.12.4,
  k8s 1.29–1.31) + §2.11 (chart 1.15.x, app v2.11.2, k8s 1.23–1.25; bundled
  **PostgreSQL 14→15** one-way DB bump is the load-bearing 2.11 hazard). k8s floors
  read from harbor-helm `.github/workflows/integration.yaml` at chart tags v1.16.4 /
  v1.15.2 (authoritative — README only states generic "1.20+").
- **Rancher floor 2.12 → 2.11.** `compat/rancher.md` §2.11 (k8s 1.30–1.32; community
  ceiling **v2.11.3**, the operator's migration source — confirmed community).
  **Methodology finding:** the documented first-line Prime-docs-redirect discriminator
  **under-detects** the 2.11 line — v2.11.4–.8 self-declare `"Prime version release"`
  in the body while keeping an inline `# Release` first line. Fix propagated to
  `version-verification.md` § Edition discrimination (third release-note format +
  self-declaration-grep discriminator).
- **ECK floor 3.2.0 → 2.16.** `compat/eck.md` §3.1.0 (k8s 1.29–1.33), §3.0.0 (k8s
  1.28–1.32; **2.x→3.0 operator-major hop**, adds Stack 9.0, removes 6.x), §2.16.1
  (k8s 1.27–1.32, last line that manages Stack 6.x). Added the **ES 8.8 / 8.14 / 8.17**
  cross-cutting table answering the operator's Stack-version question: all three are
  8.x → every tracked ECK minor (2.16.1→3.4) manages them; the constraint is ES-side
  EOL (all three EOL; 8.17 EOL 2025-08-05 verified, 8.8/8.14 EOL-by-policy UNVERIFIED).
- **OpenEBS — refocused to LocalPV-LVM only** (operator-directed, same session). The
  floor-override first backfilled the umbrella down to 4.0; the file was then **re-scoped
  to the LVM engine alone** and re-keyed by LocalPV-LVM version (1.8.0 → 1.5.1), dropping
  Mayastor / LocalPV-ZFS / LocalPV-Hostpath / LocalPV-Rawfile / cStor / Jiva entirely.
  Floor = **LVM 1.5** (the engine umbrella 4.0.1 pins). LVM versions + dates grounded
  from `openebs/lvm-localpv` (no-candidate enumeration); umbrella→LVM pin map from
  umbrella `charts/Chart.yaml` `dependencies:`. Survey detection (`cluster-survey.md`)
  narrowed: `local.openebs.io` CRDs + `lvm-localpv` chart → tracked; any other OpenEBS
  engine → untracked/abstain.
- **Traefik floor 3.5.0 → 2.11.** `compat/traefik.md` §3.4–§3.0 ladder + §2.11.
  §3.0.0 is the **v2→v3 migration landing point** (`traefik.containo.us` →
  `traefik.io` CRD-group flip, `defaultRuleSyntax` v3 default); §2.11 (v2.11.46, fully
  EOL) is the migration SOURCE → `✗ blocker`. Gateway API version grounded per minor
  (3.0→v1.0.0, 3.1→v1.1.0, 3.2→v1.2.0, 3.3→v1.2.x, 3.4→v1.2.1) from each tag's `go.mod`.
  Support-window table extended continuous 3.7→2.11.

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
  fixed in 3.2.10" (real latest `v3.4.3`) **[RETRACTED 2026-09-15 in `compat/argo-cd.md`; the SKILL.md / version-verification.md / tooling.md examples followed on 2026-10-04 — v3.2.7–v3.2.12 are real, `gh api repos/argoproj/argo-cd/releases`]**; Harbor — flagged `§ 2.15`
  **[CORRECTED 2026-05-31 — this was wrong: 2.15.x is real; see correction below]**.
- **Version-drift applied:** NVIDIA GPU Operator — latest `v26.3.2`, one patch
  ahead of documented `§ 26.3.1` (existence grounded; content sift deferred).
- **NOT gh-groundable (see `references/improvement-backlog.md`):** GitLab (not on GitHub), Grafana Mimir (`releases/latest`
  returns the app tag, not the chart `kubeVersion`). Ceph has no `releases/latest`, but its release table is groundable (2026-11-25): `gh api` on `ceph/ceph` `doc/releases/{umbrella,tentacle,squid}.rst` and `releases.yml` on main. Ground the rest via docs / GitLab
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

## 2026-09-15 — full re-ground pass

Every component re-enumerated with `gh release list --exclude-pre-releases --json
tagName,publishedAt,isLatest`. **Fourteen of seventeen components had moved**; the
per-component rows below carry the measured version. Three notes that change how
to probe, not just what the answer is:

- **Do not sort a release list by date.** Harvester's `isLatest` was `v1.8.2` on 2026-09-15 (now `v1.9.1`, 2026-11-25; `v1.8.2` and `v1.7.3` remain the newest of their lines)
  (2026-08-06) while `v1.7.3` (2026-08-07) is one day newer on a maintenance line;
  RKE2 published `v1.34.11`, `v1.35.8` and `v1.36.4` on one day. Date-ordering picks
  the wrong ceiling for both. This is the 2026-05-31 correction below seen from the
  other side: recency is not rank in *either* direction.
- **ECK's probe method is broken, not just its URL.** The row's "older minors 404,
  so a 404 infers the floor" rule no longer holds: `2.14`, `3.1`, `3.3` and `3.5`
  all 404, while `2.16` and `3.0` still serve. It is not an old-vs-new split any
  more, so a 404 carries no information. The canonical page has also moved to
  `elastic.co/docs/deploy-manage/deploy/cloud-on-k8s`.
- **A row can be stale on the day it is written.** KEDA v2.20.2 shipped ten days
  before the previous pass stamped v2.20.1.

## 2026-09-24 — `scripts/compat.py` sources + release-note sifts

Machine-read by `compat.py sync` (drift = `sync --check`; no per-row stamp — the committed
`generated.json` is the record):

- GitHub releases (every stable tag, bodies for SUSE edition): all `gh` rows in `compat.py` `COMPONENTS`
- `git ls-remote --tags` — ceph/ceph, grafana/mimir (`mimir-distributed-*`)
- https://gitlab.com/api/v4/projects/gitlab-org%2Fcharts%2Fgitlab/repository/tags — GitLab chart tags (`v*` only)
- `rancher/rancher` `chart/Chart.yaml@<tag>` — Rancher management-cluster `kubeVersion`
- https://raw.githubusercontent.com/rancher/kontainer-driver-metadata/release-v2.X/data/data.json — RKE2 lines each Rancher line provisions
- https://raw.githubusercontent.com/rancher/charts/release-v2.X/index.yaml — rancher-logging gates
- https://www.suse.com/suse-harvester/support-matrix/all-supported-versions/harvester-vX-Y-x/ — Harvester ↔ Rancher + Node Driver RKE2 (per-line pages; the index page lags)
- cilium/cilium `Documentation/network/kubernetes/compatibility.rst@<tag>` · argoproj/argo-cd `docs/operator-manual/tested-kubernetes-versions.md@<tag>` · rook/rook `Documentation/Getting-Started/Prerequisites/prerequisites.md@<tag>`
- kedacore/keda-docs `content/docs/<line>/operate/cluster.md@main` · cert-manager/website `content/docs/releases/README.md@master` · kyverno/website `src/constants/version.ts@main` (no longer holds a support matrix as of 2026-11-25; use https://kyverno.io/docs/installation/releases/) · https://www.elastic.co/support/matrix (ECK × Kubernetes CSV, found in the page's `__NEXT_DATA__`)
- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/<line>/platform-support.html — version-pinned GPU Operator window
- GitLab chart `doc/installation/cloud/_index.md` + `doc/installation/version_mappings.md` at the newest chart tag

Grounding for the 2026-09-24 compat/*.md sifts:

**mimir**
- https://github.com/grafana/mimir/pull/17231 — chart 5.8.1 (2026-11-09): appVersion 2.17.11, `kubeVersion ^1.20.0-0`, zone-downscale leader fix #16899 (§ 5.8.0, mapping table)
- https://github.com/grafana/mimir/blob/mimir-3.2.0/CHANGELOG.md — #15358: 3.2 needs every querier on 3.1 first (upgrade paths)
- https://github.com/ceph/ceph/blob/main/doc/releases/tentacle.rst — 20.2.5 (2026-11-02) carries the SigV4 fix pr#71364 (object storage table); Squid 19.2.7 per `ceph-s3` sources
- Lab rehearsal 2026-11-24/25 (k8s 1.35, Ceph RGW 20.2.4) — 5.7.0 → 6.1.1 → 6.2.2 path rows and the RGW 20.2.4 row; details in `mimir-upgrade` sources
- https://github.com/grafana/mimir/releases/tag/mimir-3.2.1 — Go-CVE patch for Mimir 3.2.x; packaged by chart 6.2.1, superseded by 3.2.3 in chart 6.2.2 (§ 6.2.0)
- https://github.com/grafana/mimir/releases/tag/mimir-3.1.6 — Go/x-crypto/grpc CVE patch for Mimir 3.1.x; superseded by 3.1.8 in chart 6.1.1 (§ 6.1.0)
- https://github.com/grafana/mimir/issues/17112 — mimir-distributed chart deprecated and moving to grafana-community; 6.3.0 (Q4 2026) announced as last release. Last verified 2026-11-25
- https://github.com/grafana/mimir/releases/tag/mimir-3.2.5 — Alertmanager SNS and tenant-config validation changes (also 3.1.10, 2.17.12). Last verified 2026-11-25
**gitlab**
- https://gitlab.com/gitlab-org/charts/gitlab/-/raw/v10.6.1/doc/installation/cloud/_index.md — k8s support table with minimum GitLab per k8s minor, plus the 1.30 hard install floor from chart 10.6.0 (path moved from cloud/index.md, which 404s)
- https://gitlab.com/gitlab-org/charts/gitlab/-/raw/master/CHANGELOG.md — chart patch contents
- https://gitlab.com/gitlab-org/charts/gitlab/-/raw/v10.6.1/doc/releases/10_0.md — chart 10.x upgrade notes per minor (10.3, 10.4, 10.6)
- https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/update/versions/gitlab_19_changes.md — GitLab 19.x upgrade notes (fixed patch levels, required stops)
**keda**
- https://keda.sh/docs/2.21/operate/cluster/ — KEDA 2.21 k8s window 1.34–1.36
- https://keda.sh/docs/2.21/migration/#upgrading-from-keda-220-to-221 — 2.21 breaking-change migration
- https://github.com/kedacore/keda/security/advisories/GHSA-637c-6jxx-4rwm — CVE-2026-77524 CRITICAL, <= 2.20.2, fixed only in 2.21
**openebs**
- https://github.com/openebs/lvm-localpv/releases/tag/v1.10.0 — LVM 1.10.0
- https://github.com/openebs/lvm-localpv/releases/tag/v1.10.1 — LVM 1.10.1 + formatOptions hazard
- https://github.com/openebs/openebs/releases/tag/v4.6.0 — umbrella 4.6.0 pins LVM 1.10.0
- https://github.com/openebs/openebs/releases/tag/v4.6.1 — umbrella 4.6.1 pins LVM 1.10.1
- https://github.com/openebs/openebs/releases/tag/v4.6.2 — umbrella 4.6.2 pins LVM 1.10.1
- https://github.com/openebs/lvm-localpv/blob/v1.9.0/deploy/helm/charts/values.yaml — LVM 1.9.0 ships csi-provisioner v6.1.0 + csi-resizer v2.0.0 (v1.8.1: v5.2.0 / v1.11.2)
- https://github.com/kubernetes-csi/external-provisioner/releases/tag/v6.0.0 — csi-provisioner v6 minimum Kubernetes 1.34 (v6.1.0 same)
- https://github.com/kubernetes-csi/external-resizer/releases/tag/v2.0.0 — csi-resizer v2 needs 1.34 for VolumeAttributesClass modification
- https://github.com/openebs/lvm-localpv/issues/492 — maintainer: CI tests against k8s v1.34.3
**eck**
- https://github.com/elastic/cloud-on-k8s/releases/tag/v3.5.0 — ECK 3.5.0 release notes (deprecations, mTLS scope, Fleet token fix)
- https://github.com/elastic/cloud-on-k8s/pull/9346 — 3.5.0 spec.resources shorthand is additive, no CRD migration
- https://github.com/elastic/cloud-on-k8s/issues/9786 — 3.5.0 leaked `watched` label rolls all ES and Kibana pods; fixed in 3.6.0. Last verified 2026-11-25
**kyverno**
- https://github.com/kyverno/kyverno/releases/tag/v1.19.0 — 1.19.0 changelog
- https://github.com/kyverno/kyverno/releases/tag/v1.19.1 — 1.19.1 security cherry-picks (the only line with the 2026-09-10 GHSA fixes)
- https://github.com/kyverno/kyverno/pull/16868 — kyverno-policies policyType default flip + legacy policy deprecation warning
- https://github.com/kyverno/kyverno/issues/15435 — kyverno-json removal (alpha-only) — stale-bot closed; the removal itself is in merged PRs shipped in the v1.19.0 and v1.20.0 notes
- https://kyverno.io/docs/installation/releases/ — 1.20 support block (k8s 1.34–1.37), 1.19 EOL at 1.20 GA. Last verified 2026-11-25
- https://kyverno.io/docs/installation/upgrading/ — 1.20 legacy-policy engine removal, `upgrade.acknowledgeLegacyPoliciesNotEnforced`. Last verified 2026-11-25
**nvidia-gpu-operator**
- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html — 26.7.x k8s 1.33–1.37, containerd 2.0–2.4 (version-pinned). Last verified 2026-11-25
- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/release-notes.html — 26.7.3 (2026-11-17): 26.3→26.7 driver-DaemonSet-deletion fix (issue #3155, PR #3157), DCGM Exporter 4.9.0 metric renames. Last verified 2026-11-25
- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.3/platform-support.html — 26.3.x k8s 1.32–1.36, containerd 1.7–2.3 (version-pinned)
**rke2**
- https://github.com/rancher/rke2/releases/tag/v1.37.0+rke2r1 — RKE2 1.37 GA notes (ingress-nginx correction, etcd 3.6→3.7, new charts)
- https://github.com/rancher/rke2/releases/tag/v1.36.3+rke2r1 — first Traefik v40.x provider-key rename warning
- https://github.com/traefik/traefik-helm-chart/releases/tag/v41.0.0 — rke2-traefik chart 41.x log-key rename and file-provider object change (1.37 line). Last verified 2026-11-25
- https://endoflife.date/api/v1/products/kubernetes/ — k8s minor EOL dates
**harvester**
- https://github.com/harvester/harvester/releases/tag/v1.9.1 — 1.9.1 Component Versions, `shutdownVMOnMigrationFailure`, fixes for #11356 / #11615
- https://github.com/harvester/harvester/releases/tag/v1.9.0 — 1.9.0 Component Versions + the upgrade warnings (#11356, #11615), superseded by 1.9.1
- https://docs.harvesterhci.io/v1.9/rancher/rancher-integration — points at the SUSE matrix
**rancher / rancher-logging**
- https://github.com/rancher/rancher/releases/tag/v2.15.3 — 2.15 community ceiling (Community declaration), CVE batch 3, #57506/#58028/#58075 fixes, #57078 known issue. Last verified 2026-11-25
- https://github.com/rancher/rancher/releases/tag/v2.16.0-rc4 — 2.16 prerelease only (rc2 2026-11-24, rc4 2026-11-25); chart kubeVersion < 1.38.0-0. Last verified 2026-11-25
- https://github.com/rancher/rancher/releases/tag/v2.15.2 — superseded by v2.15.3; keep for #57050 fix. Last verified 2026-11-25
- https://github.com/kube-logging/logging-operator/releases — upstream base (6.9.0), rancher-logging freeze gap
- https://github.com/rancher/ob-team-charts/pull/337 — rancher-logging 4.10.0-rancher.25 BCI image rebuild (new repository names). Last verified 2026-11-25
**cert-manager**
- https://cert-manager.io/docs/releases/ — k8s/OpenShift windows, EOL triggers, support policy
**cilium**
- https://docs.cilium.io/en/v1.20/network/kubernetes/compatibility/ — Cilium 1.20 k8s window 1.33–1.36
- https://docs.cilium.io/en/v1.20/operations/upgrade/ — Cilium 1.20 action-required notes
**harbor**
- https://github.com/goharbor/harbor/releases/tag/v2.16.0 — Harbor 2.16.0 GA 2026-11-10, no harbor-helm chart yet (PR #2449 open). Last verified 2026-11-25
- https://github.com/goharbor/harbor/releases/tag/v2.15.5 — 2.15.5 (2026-11-12): replication `image` filter fix (#24180). Last verified 2026-11-25

## RKE2 (anchor)

- URL: https://github.com/rancher/rke2/releases
- Probe: `gh release list --repo rancher/rke2 --limit 50`
- Last verified: 2026-11-25 — community per line **v1.37.2 (2026-11-05, isLatest) / v1.36.6+rke2r2 (2026-11-20) / v1.35.10 / v1.34.13 (2026-11-05)**; v1.33.13+rke2r2 unchanged. Prime-only bodies ("is a Prime-only release"): v1.33.13+rke2r3 (2026-10-02), v1.32.13+rke2r3 (2026-11-16); community ceilings per line in `compat/generated.json`.

## Rancher

- URL: https://github.com/rancher/rancher/releases
- Probe: `gh release list --repo rancher/rancher --limit 30`
- EOL source: https://endoflife.date/api/v1/products/rancher/ — per-minor `eolFrom`; read 2026-11-25: 2.11 → 2026-10-24 (`isEol: true`), 2.12 → 2027-02-28, 2.13 → 2027-06-17, 2.14 → 2027-10-10, 2.15 → 2028-02-27 (unchanged).
- Note: filter to community minors (Mar / Jul / Nov). Ignore Prime-flavored release notes. Edition discriminator = body **self-declaration line** (`"This is a … version release"`), NOT the first line alone — the first-line Prime-docs-redirect test under-detects (2.11 line: v2.11.4–.8 are Prime yet keep an inline `# Release` first line). See `version-verification.md` § Edition discrimination.
- Last verified: 2026-11-25 — community ceilings v2.11.3 / v2.12.3 / v2.13.3 / v2.14.3 / **v2.15.3** (2026-10-29, body self-declares "Community version release"). Prime-only redirect bodies: v2.11.18/19, v2.12.14/15, v2.13.10/11, v2.14.6/7 (the 2026-09-23 four were empty at the last sift and are now backfilled). 2.16 not GA: only v2.16.0-rc2 (2026-11-24) and rc4 (2026-11-25); rc4 chart `kubeVersion < 1.38.0-0`, no floor recorded. KDM RKE2 pairings per release branch `data.json`: 2.13 → 1.34.13; 2.14 → 1.34.13, 1.35.10; 2.15 → 1.34.13, 1.35.10, 1.36.6. Hazards: #57506 / #58028 / #58075 fixed in v2.15.3; #57078 OPEN (milestone v2.17.0), #57196 / #57240 OPEN.

## Harvester

- URL: https://github.com/harvester/harvester/wiki
- Secondary URL: https://github.com/harvester/harvester/releases
- Probe: WebFetch the per-version compatibility wiki page; filter to community columns.
- Last verified: 2026-11-25 — **v1.9.1 GA 2026-11-10** (`v1.9.0` 2026-09-16); #11356 / #11615 CLOSED and listed as fixed in the 1.9.1 notes. `v1.10.0-rc3` and `v1.8.3-rc1` are pre-releases only. SUSE per-line pages `harvester-v1-5-x` through `-v1-9-x` re-read: Node Driver RKE2 1.31–1.33 (1.6) / 1.32–1.34 (1.7) / 1.33–1.35 (1.8) / 1.34–1.36 (1.9); the 1.9 page still lists only v1.9.0 (CSI ≥ v0.1.31). Per line: v1.9.1 (2026-11-10), v1.8.2 (2026-08-06), v1.7.3 (2026-08-07, one day newer than 1.8.2 but a lower line; sorting by date picks the wrong answer).

## Cilium

- URL: https://docs.cilium.io/en/stable/network/kubernetes/compatibility/
- Secondary URL: https://github.com/cilium/cilium/releases
- Probe: WebFetch docs page for the matrix; `gh release list --repo cilium/cilium` for per-version notes.
- Last verified: 2026-11-25 — v1.20.5 / v1.19.11 / v1.18.17 (2026-11-17, v1.20.5 `isLatest`; bugfix + dependency `[security]` bumps, `toServices`+`toPorts` egress deny change in the upgrade notes); v1.17.18 unchanged; v1.21 still pre-release (v1.21.0-pre.4). `compatibility.rst` windows unchanged at the four line tags; all Cilium URLs above HTTP 200.

## Tetragon

- URL: https://github.com/cilium/tetragon/releases
- Kernel-floor source: https://tetragon.io/docs/installation/faq/ (also in-repo at `docs/content/en/docs/installation/faq.md`)
- Chart source: `install/kubernetes/tetragon/Chart.yaml` at release tags (chart == app version; no `kubeVersion:`)
- Probe: anchor `gh api repos/cilium/tetragon/releases/latest --jq '.tag_name'`; enumerate minors `gh api 'repos/cilium/tetragon/releases?per_page=100' --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' | sort -V`; sift kernel floor from the FAQ doc, breaking changes from each in-scope release's "Upgrade notes" (the v1.8.0 release body has none: read `contrib/upgrade-notes/v<minor>.md` at the tag).
- Note: separate component from Cilium core. The k8s axis is loose; the **kernel** axis is load-bearing.
- Last verified: 2026-11-25 — v1.8.0 (2026-10-30, `isLatest`), v1.7.1 (2026-08-25), v1.6.1, v1.5.0 newest of their lines; `Chart.yaml@v1.8.0` version == appVersion == 1.8.0, no `kubeVersion:`; FAQ and hooks docs unchanged v1.7.0→v1.8.0; upgrade notes at `contrib/upgrade-notes/v1.8.0.md`; https://tetragon.io/docs/installation/faq/ HTTP 200.

## cert-manager

- URL: https://cert-manager.io/docs/releases/
- Secondary URL: https://github.com/cert-manager/cert-manager/releases
- Probe: WebFetch releases page; `gh release list --repo cert-manager/cert-manager`.
- Last verified: 2026-11-25 — v1.21.3 (2026-10-23) and v1.20.5 (2026-10-28, eMudhra root removed, Go 1.26.10, x/net v0.60.0+, x/crypto v0.57.0) newest of their lines; v1.22.0-alpha.0 (2026-11-24) is the only 1.22 tag. Support table (website `content/docs/releases/README.md@master`, live page identical): 1.21 → k8s 1.33–1.36 / OpenShift 4.20–4.22, 1.20 → 1.32–1.35 / 4.19–4.21, 1.22 listed `~Nov 2026`, window TBD; 1.17 LTS vendor-only to 2027-02-03. `gh api repos/cert-manager/cert-manager/security-advisories`: still only GHSA-8rvj-mm4h-c258 (2026-06-25), GHSA-gx3x-vq4p-mhhv, GHSA-r4pg-vg54-wxx4.

## Kyverno

- URL: https://kyverno.io/docs/installation/releases/
- Secondary URL: https://github.com/kyverno/kyverno/releases
- Probe: WebFetch the releases page for the support block; `gh release list --repo kyverno/kyverno`; upgrade guide https://kyverno.io/docs/installation/upgrading/.
- Last verified: 2026-11-25 — v1.20.0 (2026-11-12, k8s v1.34–v1.37, EOL est. 1.21 release ~Feb 2027); v1.19.2, v1.18.2, v1.17.2 newest of their lines. `kyverno/website` `src/constants/version.ts` no longer holds a support matrix (selector links only). `gh api repos/kyverno/kyverno/security-advisories`: newest published 2026-10-23, all patched in 1.19.2; none names 1.20. `/docs/installation/` redirects to `/docs/installation/installation/`. Issue #15435 shows closed by a stale-bot recap; the kyverno-json removal itself is in merged PRs shipped in the v1.19.0 and v1.20.0 notes.

## KEDA

- URL: https://keda.sh/docs/latest/operate/cluster/
- Governance / support window: https://github.com/kedacore/governance/blob/main/SUPPORT.md
- Secondary URL: https://github.com/kedacore/keda/releases
- Probe: WebFetch docs + governance; `gh release list --repo kedacore/keda`.
- Last verified: 2026-11-25 — v2.21.1 (2026-11-15) newest; v2.20.2 newest 2.20. `docs/latest` redirects to 2.21 (matrix 2.21 v1.34–v1.36 … 2.17 v1.30–v1.32). `docs/2.22/` still serves with no 2.22 release (pre-release docs, do not cite). Next release estimated 2nd week of January 2027 (v2.21.0 notes).

## Argo CD

- URL: https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/
- Secondary URL: https://github.com/argoproj/argo-cd/releases
- Probe: WebFetch tested-versions page; `gh release list --repo argoproj/argo-cd`.
- Last verified: 2026-11-25 — `stable` page now lists 3.6 (1.34–1.37), 3.5 (1.33–1.36), 3.4 (1.32–1.35). Latest v3.6.3 / v3.5.9 / v3.4.15 (2026-11-24); v3.3.19 final (2026-11-02, EOL banner 2026-11-03); v3.6.0 GA 2026-11-03. 2026-11-24 advisories fixed in 3.6.3 / 3.5.9 / 3.4.15, none in 3.3.

## Harbor

- URL: https://goharbor.io/docs/
- Secondary URL: https://github.com/goharbor/harbor/releases
- Probe: WebFetch docs index for release notes pages; `gh release list --repo goharbor/harbor`.
- Note: k8s minimums change with chart versions; cross-reference the harbor-helm chart at https://github.com/goharbor/harbor-helm. Authoritative k8s floor = chart `.github/workflows/integration.yaml` at the chart tag (README only states generic "1.20+").
- Probe (2026-11-25): harbor-helm tags (`gh release list --repo goharbor/harbor-helm`; newest v1.19.4) and `RELEASES.md` on main for the support window.
- Last verified: 2026-11-25 — v2.16.0 (GA 2026-11-10), v2.15.5 (2026-11-12, `isLatest`), v2.14.6 (2026-10-23), v2.13.6 (2026-10-06). harbor-helm newest tag v1.19.4 (app v2.15.4); no 2.16 chart (PR #2449 open, 1.20.0 branch is a `1.4.0-dev` placeholder). `integration.yaml` at v1.19.4 still lists k8s v1.34.0 / v1.33.4 / v1.32.8 (no v1.35). `RELEASES.md` on main lists 2.15, 2.14, 2.13 as supported. v2.15.4 / v2.14.6 carry the same-origin replication fix (#24114).

## Traefik

- URL: https://github.com/traefik/traefik/releases
- Probe: `gh release list --repo traefik/traefik --limit 30` (paginate — 2.11 still gets frequent security patches, pushing older 3.0.x patches past the first 100 results). Per-minor Gateway API version from each tag's `go.mod` (`sigs.k8s.io/gateway-api`).
- Note: extract k8s API minimums from the "Kubernetes" section of release notes. **Traefik publishes no separate k8s support matrix — absence claim re-tested 2026-09-15 against the kubernetes-crd provider page, which carries no explicit "Kubernetes N.N" statement, and it holds.** (Two sibling "upstream publishes no matrix" claims in this registry turned out false the same day, so this one was checked rather than inherited.) v2→v3 migration guide: `docs/content/migrate/v3.md` + `v2-to-v3*.md`; support window: `docs/content/deprecation/releases.md`.
- Last verified: 2026-11-25 — v3.8.0 (GA 2026-11-23, `isLatest`; Gateway API v1.7.0, client-go v0.37.1), v3.7.20 and v2.11.64 (both 2026-11-23); floor re-derived from `gh api repos/traefik/traefik/security-advisories` (GHSA-3rh5-223h-cpwr, GHSA-9657-c2gv-wjpj, GHSA-42x2-976f-ph52 patched in v3.7.20 / v3.8.0, GHSA-9657 also v2.11.64). `deprecation/releases.md` at master has no 3.8 row and still says 2.11 security "Ends Sept 07, 2026" while 2.11 patches continued.

## Rook (operator)

- Primary URL: https://github.com/rook/rook/releases
- Secondary URL: https://rook.io/docs/rook/latest-release/
- Probe: `gh release list --repo rook/rook --limit 30`; for each in-scope release, `gh release view <tag>` and sift k8s floor + supported Ceph versions; WebFetch docs landing page as cross-reference.
- Last verified: 2026-11-25 — v1.21.3 (2026-11-24, `isLatest`; 1.21.2 2026-11-05); `prerequisites.md@v1.21.3` reads "v1.32 through v1.37"; `ceph-upgrade.md@v1.21.3` Squid v19.2.0+ / Tentacle v20.2.1+ (Umbrella in `version.go@v1.21.3` `supportedVersions` only). v1.20.10 (2026-11-05, `prerequisites.md` "v1.31 through v1.37") and v1.19.12 (2026-10-14) newest of their lines. Primary and secondary URLs return 200.

## Ceph (storage)

- Primary source: Rook release notes (each Rook release names the supported Ceph minor range). See `compat/rook.md` first.
- Secondary URL: https://docs.ceph.com/en/latest/releases/ (upstream Ceph EOL line + standalone breaking changes — Reef / Squid / Tentacle).
- Probe: Read `compat/rook.md` for Rook↔Ceph pairings; WebFetch ceph.io releases page for upstream EOL signal + OSD encoding / cluster-wide breaking changes.
- Note: Ceph's k8s axis collapses through Rook — the cluster doesn't see Ceph version against k8s directly; it sees Rook version against k8s, and Rook bounds Ceph.
- Last verified: 2026-11-25 — Umbrella **21.2.0** (2026-10-28), Tentacle **20.2.5** (2026-11-02), Squid **19.2.7** (2026-10-12, EOL est. 2026-12-02), Reef 18.2.8 final (`ceph/ceph` `doc/releases/{umbrella,tentacle,squid}.rst` and `releases.yml` on main; same table on https://docs.ceph.com/en/latest/releases/). `docs.ceph.com/en/tentacle/releases/` now redirects to `/en/latest/releases/`.

## OpenEBS (LocalPV-LVM only)

- URL: https://github.com/openebs/lvm-localpv/releases
- Secondary URL: https://github.com/openebs/openebs (umbrella → LVM pin map only — `charts/Chart.yaml` `dependencies:` at the umbrella tag)
- Probe: `gh api --paginate 'repos/openebs/lvm-localpv/releases?per_page=100'` (two tag schemes — `vX.Y.Z` app tags + `lvm-localpv-X.Y.Z` chart tags; enumerate both, no candidate named). Cross-check the umbrella pin via `gh api repos/openebs/openebs/contents/charts/Chart.yaml?ref=<umbrella-tag>`.
- Scope: **LocalPV-LVM only** (operator runs no other OpenEBS engine). Mayastor / LocalPV-ZFS / LocalPV-Hostpath / LocalPV-Rawfile / cStor / Jiva are out of registry scope — do NOT probe or sift them.
- Last verified: 2026-11-25 — lvm-localpv **v1.10.1** (2026-09-09) still newest; umbrella v4.6.2 (2026-10-07) still pins `lvm-localpv: 1.10.1`. Unreleased on main (no tag yet): #530 scheduler fix when VG free space equals the request, #532 snapshot-ready wait, #520 update-strategy values ignored. The LVM **floor** claim is unaffected — it describes an older umbrella.

## GitLab

- URL: https://docs.gitlab.com/
- Secondary URL: https://docs.gitlab.com/charts/installation/cloud/ (k8s/Helm chart compat)
- Probe: WebFetch docs sections covering k8s compat and Helm chart minimums.
- Note: operator runs the EE binary as CE; ignore EE-only features in the sift.
- Last verified: 2026-11-25 — newest chart v10.6.1 = GitLab 19.6.1 (tag message; `version_mappings.md` at v10.6.1 lists up to 10.5.7 / 10.4.9 only); chart `doc/installation/cloud/_index.md` at v10.6.1: 1.35–1.37 (1.37 needs GitLab ≥ 19.5), chart ≥ 10.6.0 does not install below k8s 1.30; CHANGELOG 10.5.3–10.6.1 and `doc/releases/10_0.md` (10.3 / 10.4 / 10.6 notes) read; bundled cert-manager per newest tag from `Chart.yaml`: 9.11.16 / 10.0.11 / 10.1.10 v1.20.5, 10.2.10 / 10.3.11+ v1.21.3; `doc/install/requirements.md` at master: 19.x PostgreSQL 17.x–18.x, Redis 7.0 / Valkey 7.2 minimum; `upgrade_paths.md`: 19.x stops 19.2 / 19.5 / 19.8 / 19.11; 19.6.0–19.6.1 `DropAiEventsCounts` migration failure fixed in 19.6.2. Not gh-groundable; read via gitlab.com raw/API.

## ECK

- URL: https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s
- Stack-matrix URL: https://www.elastic.co/support/matrix
- ~~Versioned supported-versions pages: `.../cloud-on-k8s/<minor>/k8s-supported.html`, older minors 404 → infer floor~~ — **RETIRED 2026-09-15, the rule no longer discriminates**: 2.14/3.1/3.3/3.5 all 404 while 2.16/3.0 serve.
- **WORKING PROBE:** `curl` https://www.elastic.co/support/matrix, read the `<script id="__NEXT_DATA__">` blob, take the CSV asset `support-matrix-product-and-kubernetes-elastic-cloud-on-kubernetes-and-kubernetes-distro.csv` — it carries **every ECK minor 1.0.x→3.5.x** with release date, k8s range and OpenShift range in one request. Historical note, the old rule inferred a floor from `controller-runtime`/`client-go` baked in the release, with a "verify on upgrade" caveat); in-repo `pkg/controller/elasticsearch/version/supported_versions.go` at the tag for the Stack range.
- Probe: WebFetch supported-versions page; cross-reference stack matrix. For ES Stack EOL: endoflife.date/elasticsearch + elastic.co/support/eol.
- Last verified: 2026-11-25 — v3.5.0 (2026-08-04, `isLatest`) still newest; matrix CSV unchanged (3.5.x k8s 1.32–1.36, OpenShift 4.16–4.22; 3.4.x k8s 1.31–1.36, OpenShift 4.16–4.22; 3.2.x k8s 1.30–1.34, OpenShift 4.15–4.20). v3.4.1 is dependency bumps only. Known issue #9786: 3.5.0 leaks the `eck.k8s.elastic.co/watched` label and rolls all Elasticsearch and Kibana pods on upgrade; fixed in 3.6.0 (unreleased). Elastic Package Registry, Stack-compatibility tabs and 8.x/9.x EOL dates not re-probed.

## Zalando postgres-operator

- URL: https://github.com/zalando/postgres-operator/releases
- Probe: `gh release list --repo zalando/postgres-operator --limit 30`; sift bundled Spilo + Postgres major + `kubernetes_use_configmaps` semantics.
- Last verified: 2026-11-25 — v2.0.3 (2026-10-02, `isLatest`) still newest; README support table at v2.0.3: K8s `1.27+`, PG 14→18. Open issues affecting 2.0.3: #3248 operator panic after a successful in-place major upgrade, #3210 rolling-update loop when a mutating webhook injects `runAsNonRoot`, #3201 / #3229 / #3230 grant failures not retried; master (unreleased): lazy rolling updates wait for the maintenance window (#3204).

## Grafana Mimir (chart_metadata)

- URL: https://github.com/grafana/mimir/blob/main/operations/helm/charts/mimir-distributed/Chart.yaml
- Probe: `gh api repos/grafana/mimir/contents/operations/helm/charts/mimir-distributed/Chart.yaml` at each chart-release tag; extract `kubeVersion:` constraint and `appVersion:`.
- Last verified: 2026-11-25 — newest stable charts `mimir-distributed-6.2.2` (appVersion 3.2.3) and `6.1.1` (appVersion 3.1.8), both 2026-10-26; no chart tag newer than 6.2.2. Newest app releases: mimir-3.2.6, 3.1.11, 2.17.12 (and 3.0.9), all ahead of every chart (need an `image.tag` pin); 3.2.5 / 3.1.10 / 2.17.12 carry Alertmanager breaking changes (SNS receivers need explicit credentials, `use_aws_http_client` rejected, tenant-config restrictions enforced on storage load). Chart deprecation: `mimir-distributed` is moving to `grafana-community/helm-charts` (issue #17112); 6.3.0 (Q4 2026) announced as the last release from the Grafana repo, not yet tagged.

## NVIDIA GPU Operator

- URL: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html
- Secondary URL: https://github.com/NVIDIA/gpu-operator/releases
- Probe: WebFetch platform-support page; `gh release list --repo NVIDIA/gpu-operator`.
- Note: driver-version-per-release is captured in the compat file, not here.
- Last verified: 2026-11-25 — v26.7.3 (2026-11-17, `isLatest`; notes at `/26.7/release-notes.html`): fixes the 26.3.x → 26.7.0/.1/.2 driver-DaemonSet deletion (issue #3155, PR #3157); DCGM Exporter 4.9.0 renames default metrics. v26.3.3 newest 26.3 (no 26.3.x after it). 26.7 platform-support: k8s 1.33–1.37, containerd 2.0–2.4. No platform-support page for any later line.

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes (historical reference the operator wants frozen).
- `Pinned: <semver>` under a row tells freshen not to auto-advance past that version even if upstream ships newer; useful when the operator deliberately stays on an older line.
