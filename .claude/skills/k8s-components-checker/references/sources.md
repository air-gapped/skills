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

## 2026-09-15 — full re-ground pass

Every component re-enumerated with `gh release list --exclude-pre-releases --json
tagName,publishedAt,isLatest`. **Fourteen of seventeen components had moved**; the
per-component rows below carry the measured version. Three notes that change how
to probe, not just what the answer is:

- **Do not sort a release list by date.** Harvester's `isLatest` is `v1.8.2`
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

## RKE2 (anchor)

- URL: https://github.com/rancher/rke2/releases
- Probe: `gh release list --repo rancher/rke2 --limit 50`
- Last verified: 2026-09-15 — v1.36.4+rke2r1 (2026-08-28) is `isLatest`; v1.35.8 and v1.34.11 published the SAME day on lower lines. v1.37 is in rc only.

## Rancher

- URL: https://github.com/rancher/rancher/releases
- Probe: `gh release list --repo rancher/rancher --limit 30`
- Note: filter to community minors (Mar / Jul / Nov). Ignore Prime-flavored release notes. Edition discriminator = body **self-declaration line** (`"This is a … version release"`), NOT the first line alone — the first-line Prime-docs-redirect test under-detects (2.11 line: v2.11.4–.8 are Prime yet keep an inline `# Release` first line). See `version-verification.md` § Edition discrimination.
- Last verified: 2026-09-15 — floor -> 2.11; **community ceiling v2.11.3 re-confirmed** by reading every v2.11.x body up to v2.11.17 — .4 through .17 each self-declare "Prime version release"; only v2.11.3 says "Community and Prime". Overall latest line is v2.15.1, unrelated to this floor.

## Harvester

- URL: https://github.com/harvester/harvester/wiki
- Secondary URL: https://github.com/harvester/harvester/releases
- Probe: WebFetch the per-version compatibility wiki page; filter to community columns.
- Last verified: 2026-09-15 — v1.8.2 (2026-08-06) is `isLatest` — **v1.7.3 (2026-08-07) is one day newer and is NOT the ceiling.** Sorting this list by date picks the wrong answer. v1.9.0 is rc only.

## Cilium

- URL: https://docs.cilium.io/en/stable/network/kubernetes/compatibility/
- Secondary URL: https://github.com/cilium/cilium/releases
- Probe: WebFetch docs page for the matrix; `gh release list --repo cilium/cilium` for per-version notes.
- Last verified: 2026-09-15 — v1.20.1 (2026-08-18); v1.21 in pre-release.

## Tetragon

- URL: https://github.com/cilium/tetragon/releases
- Kernel-floor source: https://tetragon.io/docs/installation/faq/ (also in-repo at `docs/content/en/docs/installation/faq.md`)
- Chart source: `install/kubernetes/tetragon/Chart.yaml` at release tags (chart == app version; no `kubeVersion:`)
- Probe: anchor `gh api repos/cilium/tetragon/releases/latest --jq '.tag_name'`; enumerate minors `gh api 'repos/cilium/tetragon/releases?per_page=100' --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' | sort -V`; sift kernel floor from the FAQ doc, breaking changes from each in-scope release's "Upgrade notes".
- Note: separate component from Cilium core. The k8s axis is loose; the **kernel** axis is load-bearing.
- Last verified: 2026-09-15 — v1.7.1 (2026-08-25).

## cert-manager

- URL: https://cert-manager.io/docs/releases/
- Secondary URL: https://github.com/cert-manager/cert-manager/releases
- Probe: WebFetch releases page; `gh release list --repo cert-manager/cert-manager`.
- Last verified: 2026-09-15 — v1.21.2 (2026-09-11) — new v1.21 minor line since last pass.

## Kyverno

- URL: https://kyverno.io/docs/installation/
- Secondary URL: https://github.com/kyverno/kyverno/releases
- Probe: WebFetch installation page for compatibility table; `gh release list --repo kyverno/kyverno`.
- Last verified: 2026-09-15 — v1.19.1 (2026-09-10) — new v1.19 minor line since last pass.

## KEDA

- URL: https://keda.sh/docs/latest/operate/cluster/
- Governance / support window: https://github.com/kedacore/governance/blob/main/SUPPORT.md
- Secondary URL: https://github.com/kedacore/keda/releases
- Probe: WebFetch docs + governance; `gh release list --repo kedacore/keda`.
- Last verified: 2026-09-15 — v2.20.2 (2026-07-31), which landed 10 days AFTER the previous stamp and was missed by it. Still current — no release since.

## Argo CD

- URL: https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/
- Secondary URL: https://github.com/argoproj/argo-cd/releases
- Probe: WebFetch tested-versions page; `gh release list --repo argoproj/argo-cd`.
- Last verified: 2026-09-15 — v3.5.3 (2026-09-14); two full minors (3.4, 3.5) since the last pass.

## Harbor

- URL: https://goharbor.io/docs/
- Secondary URL: https://github.com/goharbor/harbor/releases
- Probe: WebFetch docs index for release notes pages; `gh release list --repo goharbor/harbor`.
- Note: k8s minimums change with chart versions; cross-reference the harbor-helm chart at https://github.com/goharbor/harbor-helm. Authoritative k8s floor = chart `.github/workflows/integration.yaml` at the chart tag (README only states generic "1.20+").
- Last verified: 2026-09-15 — v2.15.2 (2026-07-02). **Absence claim re-tested and still true:** harbor-helm v1.19.2 `integration.yaml` lists k8s v1.34.0/v1.33.4/v1.32.8 — still no v1.35. Note goharbor.io/docs/ redirects to /docs/2.15.0/, so the cited URL is not the final one.

## Traefik

- URL: https://github.com/traefik/traefik/releases
- Probe: `gh release list --repo traefik/traefik --limit 30` (paginate — 2.11 still gets frequent security patches, pushing older 3.0.x patches past the first 100 results). Per-minor Gateway API version from each tag's `go.mod` (`sigs.k8s.io/gateway-api`).
- Note: extract k8s API minimums from the "Kubernetes" section of release notes. **Traefik publishes no separate k8s support matrix — absence claim re-tested 2026-09-15 against the kubernetes-crd provider page, which carries no explicit "Kubernetes N.N" statement, and it holds.** (Two sibling "upstream publishes no matrix" claims in this registry turned out false the same day, so this one was checked rather than inherited.) v2→v3 migration guide: `docs/content/migrate/v3.md` + `v2-to-v3*.md`; support window: `docs/content/deprecation/releases.md`.
- Last verified: 2026-09-15 — v3.7.13 and v2.11.57 (both 2026-09-04). Same 3.7/2.11 lines — no new v2->v3 breaking hop.

## Rook (operator)

- Primary URL: https://github.com/rook/rook/releases
- Secondary URL: https://rook.io/docs/rook/latest-release/
- Probe: `gh release list --repo rook/rook --limit 30`; for each in-scope release, `gh release view <tag>` and sift k8s floor + supported Ceph versions; WebFetch docs landing page as cross-reference.
- Last verified: 2026-09-15 — v1.20.7 (2026-09-02) — new v1.20 minor line since last pass.

## Ceph (storage)

- Primary source: Rook release notes (each Rook release names the supported Ceph minor range). See `compat/rook.md` first.
- Secondary URL: https://docs.ceph.com/en/latest/releases/ (upstream Ceph EOL line + standalone breaking changes — Reef / Squid / Tentacle).
- Probe: Read `compat/rook.md` for Rook↔Ceph pairings; WebFetch ceph.io releases page for upstream EOL signal + OSD encoding / cluster-wide breaking changes.
- Note: Ceph's k8s axis collapses through Rook — the cluster doesn't see Ceph version against k8s directly; it sees Rook version against k8s, and Rook bounds Ceph.
- Last verified: 2026-09-15 — unchanged. Current named line is still Tentacle (20.2.4); no new named release, so this row's claims are untouched.

## OpenEBS (LocalPV-LVM only)

- URL: https://github.com/openebs/lvm-localpv/releases
- Secondary URL: https://github.com/openebs/openebs (umbrella → LVM pin map only — `charts/Chart.yaml` `dependencies:` at the umbrella tag)
- Probe: `gh api --paginate 'repos/openebs/lvm-localpv/releases?per_page=100'` (two tag schemes — `vX.Y.Z` app tags + `lvm-localpv-X.Y.Z` chart tags; enumerate both, no candidate named). Cross-check the umbrella pin via `gh api repos/openebs/openebs/contents/charts/Chart.yaml?ref=<umbrella-tag>`.
- Scope: **LocalPV-LVM only** (operator runs no other OpenEBS engine). Mayastor / LocalPV-ZFS / LocalPV-Hostpath / LocalPV-Rawfile / cStor / Jiva are out of registry scope — do NOT probe or sift them.
- Last verified: 2026-09-15 — lvm-localpv **v1.10.1** (2026-09-09). The umbrella `openebs/openebs` is now v4.6.1 and pins `lvm-localpv: 1.10.1`, so the "umbrella 4.0.1 pins LVM 1.5" mapping recorded earlier is stale as a *ceiling*. The LVM **floor** claim is unaffected — it describes an older umbrella.

## GitLab

- URL: https://docs.gitlab.com/
- Secondary URL: https://docs.gitlab.com/charts/installation/cloud/ (k8s/Helm chart compat)
- Probe: WebFetch docs sections covering k8s compat and Helm chart minimums.
- Note: operator runs the EE binary as CE; ignore EE-only features in the sift.
- Last verified: 2026-09-15 — both doc URLs 200 direct, no redirect. Correctly not gh-groundable; this row states no version to falsify.

## ECK

- URL: https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s
- Stack-matrix URL: https://www.elastic.co/support/matrix
- ~~Versioned supported-versions pages: `.../cloud-on-k8s/<minor>/k8s-supported.html`, older minors 404 → infer floor~~ — **RETIRED 2026-09-15, the rule no longer discriminates**: 2.14/3.1/3.3/3.5 all 404 while 2.16/3.0 serve.
- **WORKING PROBE:** `curl` https://www.elastic.co/support/matrix, read the `<script id="__NEXT_DATA__">` blob, take the CSV asset `support-matrix-product-and-kubernetes-elastic-cloud-on-kubernetes-and-kubernetes-distro.csv` — it carries **every ECK minor 1.0.x→3.5.x** with release date, k8s range and OpenShift range in one request. Historical note, the old rule inferred a floor from `controller-runtime`/`client-go` baked in the release, with a "verify on upgrade" caveat); in-repo `pkg/controller/elasticsearch/version/supported_versions.go` at the tag for the Stack range.
- Probe: WebFetch supported-versions page; cross-reference stack matrix. For ES Stack EOL: endoflife.date/elasticsearch + elastic.co/support/eol.
- Last verified: 2026-09-15 — v3.5.0 (2026-08-04). **The probe method below is broken, not just the URL** — see the pass note at the top: 2.14/3.1/3.3/3.5 all 404 while 2.16/3.0 serve, so a 404 no longer infers "too old".

## Zalando postgres-operator

- URL: https://github.com/zalando/postgres-operator/releases
- Probe: `gh release list --repo zalando/postgres-operator --limit 30`; sift bundled Spilo + Postgres major + `kubernetes_use_configmaps` semantics.
- Last verified: 2026-09-15 — v2.0.2 (2026-08-20), one patch past the v2.0.1 the last pass sifted.

## Grafana Mimir (chart_metadata)

- URL: https://github.com/grafana/mimir/blob/main/operations/helm/charts/mimir-distributed/Chart.yaml
- Probe: `gh api repos/grafana/mimir/contents/operations/helm/charts/mimir-distributed/Chart.yaml` at each chart-release tag; extract `kubeVersion:` constraint and `appVersion:`.
- Last verified: 2026-09-15 — `Chart.yaml` path still resolves and the probe method still works. Last tagged stable chart is `mimir-distributed-6.2.0` (`kubeVersion: ^1.32.0-0`); HEAD carries a 6.3.0-weekly dev tag.

## NVIDIA GPU Operator

- URL: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html
- Secondary URL: https://github.com/NVIDIA/gpu-operator/releases
- Probe: WebFetch platform-support page; `gh release list --repo NVIDIA/gpu-operator`.
- Note: driver-version-per-release is captured in the compat file, not here.
- Last verified: 2026-09-15 — v26.7.0 (2026-08-21) — a new minor line past v26.3.2.

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes (historical reference the operator wants frozen).
- `Pinned: <semver>` under a row tells freshen not to auto-advance past that version even if upstream ships newer; useful when the operator deliberately stays on an older line.
