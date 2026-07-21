# improvement-backlog.md

Ceiling findings from skill-improver runs.

## Open

### Ceph patch-level drift in compat/ceph.md (Dim 9) (low-risk, in-minor) (carried 2026-05-28)

- Compat file references Tentacle 20.2.1, Squid 19.2.3, Reef 18.2.8 as the
  illustrative latest patches at sift time. Freshen probe (2026-05-28) found:
  - Tentacle: latest stable is **20.3.0** (compat says 20.2.1)
  - Squid: latest stable is **19.3.0** (compat says 19.2.3)
  - Reef: latest stable is **18.2.8** ✓
- Re-confirmed 2026-05-28 via `gh api repos/ceph/ceph/tags`: v20.3.0 and
  v19.3.0 tags exist (Tentacle / Squid). Tag existence carries **no**
  regression signal, so the bump still cannot be applied this pass.
- Drift is in-minor (Tentacle stays Tentacle, Squid stays Squid). The compat
  file's load-bearing structure — Tentacle/Squid/Reef series characteristics,
  4 known-bad point releases (18.2.5, 18.2.6, 19.2.0, 19.2.1), EOL dates,
  intra-cluster upgrade ordering — remains accurate.
- Could NOT be applied in one iteration: freshen-patterns §3.2 requires
  reading the docs.ceph.com prose release notes for the intervening patches
  (20.2.2..20.3.0, 19.2.4..19.3.0) to extract any NEW known-bad point release
  before bumping the headers. That is a multi-WebFetch sift against a non-`gh`
  doc source, not a single atomic header edit — and stamping the bump on tag
  existence alone would violate "do not apply a bump you cannot stand behind".
- Action: WebFetch https://docs.ceph.com/en/tentacle/releases/ and
  https://docs.ceph.com/en/squid/releases/ for the new patches; add any new
  known-bad to the "Versions skipped" list (Sift notes); bump the
  illustrative patch numbers in the version headers (20.2.1 → 20.3.0,
  19.2.3 → 19.3.0).

### Ceph drift evidence is itself unverified — re-flag (House Rule #8) (2026-05-30)

- The carried Ceph item above cites `v20.3.0` / `v19.3.0` from `gh api .../tags`,
  now known to be **confirmatory/contaminated** (rubber-stamps plausible-but-fake
  tags), and `ceph/ceph` has **no `releases/latest`** scalar to anchor on. So the
  drift is **UNVERIFIED, not merely un-applied** — do NOT bump on the tags
  evidence. Ground via docs.ceph.com release pages first.

### Per-version "fixed-in vX.Y.Z" / CVE-patch claims not release-grounded (Dim 9) (new 2026-05-30)

- Every `compat/*.md` carrying "fixed in" / "patched in" lines (keda
  CVE-2025-68476→2.18.3, cert-manager CVE-2025-617xx, argo CVE-2026-42880, ceph
  data-loss point releases). The release-grounding pass confirmed version
  *existence* via `releases/latest`, but the gh release-**body** endpoint is
  confirmatory/contaminated here, so a patch's *changelog contents* can't be
  trusted from it. Action: author verifies the "fixed-in" patches against real
  changelogs on a trusted network, then stamp `Last release-verified:`.

### GitLab not gh-groundable (new 2026-05-30)

- `compat/gitlab.md`. Chart at `gitlab.com/gitlab-org/charts/gitlab`; `gh` does
  not apply. Ground via the GitLab API / `glab` / `helm search`, else mark
  versions `UNVERIFIED`.

### Grafana Mimir chart-vs-app axis (new 2026-05-30)

- `compat/mimir.md`. `releases/latest` returns the **app** tag (`mimir-3.0.6`);
  the load-bearing axis is the `mimir-distributed` **chart** `Chart.yaml`
  `kubeVersion:`. Ground via
  `gh api repos/grafana/mimir/contents/operations/helm/charts/mimir-distributed/Chart.yaml`
  at chart-release tags, not `releases/latest`.

### NVIDIA GPU Operator v26.3.2 content not sifted (new 2026-05-30)

- `compat/nvidia-gpu-operator.md` (banner added 2026-05-30). Existence grounded
  via `gh`; the 26.3.2 release-note content (breaking changes, driver defaults,
  k8s-floor confirmation) still needs a sift on a trusted network — document
  `§ 26.3.2` then.

### ES 8.8 / 8.14 exact end-of-maintenance dates UNVERIFIED (new 2026-06-02)

- `compat/eck.md` § "Which ECK minors manage Elasticsearch 8.8 / 8.14 / 8.17?".
  ES **8.17 EOL = 2025-08-05** is verified (endoflife.date). **8.8.x and 8.14.x**
  have rolled off endoflife.date's per-minor table (long superseded), so their
  exact end-of-maintenance day is derived from Elastic's "two-newest-8.x-minors"
  policy + successor-minor GA dates, not a fetched per-minor EOL. Only "EOL well
  before 2026" is certain. Both are flagged UNVERIFIED in the table.
- Action: if an exact 8.8/8.14 EOL date is ever needed for a verdict, fetch
  Elastic's archived support-matrix snapshot (web.archive.org of
  elastic.co/support/eol at the relevant date) — not groundable via `gh`.

## Resolved — 2026-07-21 (freshen, operator-requested; driver = a live Mimir 5.7.0/2.16.0 air-gapped fleet)

All 19 compat files re-probed and restamped. Findings applied:

- **mimir** — added **chart 6.1.0 / app 3.1.2** (2026-07-16). k8s floor jumps
  again, `^1.29` → **`^1.32`** — second floor move in two minors, so a fleet
  below k8s 1.32 can reach 6.0.x but not 6.1.0. `kafka.extraEnv` removed →
  `kafka.env`. **Default registry is now `docker.io` and the image tag defaults
  to `Chart.AppVersion`** — air-gap image lists must be regenerated, not diffed.
  Added the 5.7 → 5.8 → 6.0 → 6.1 ladder, the one-minor-at-a-time app policy,
  and a warning about the chart-vs-app version-number collision (Grafana's
  "chart 2.x → 3.0" migration guide is from 2022 and unrelated to app 3.0).
  5.7.0 explicitly retained below the tracked window as a live fleet version.
- **cert-manager** — **1.21.0 GA'd 2026-07-08**, so 1.19 is now EOL and the
  k8s floor moves to **1.33**. Recorded three chart-breaking changes (default
  `tokenrequest` RBAC removed; metrics `servicemonitor`/`podmonitor` values
  removed against an `additionalProperties: false` schema, so leftovers fail
  the upgrade; `cert-manager-edit` RBAC narrowed per GHSA-8rvj-mm4h-c258) plus
  two known issues, including a **controller crash-loop** on
  `renewal.policy: Disabled` (#9031).
- **keda** — registry was two minors behind. Added **2.20.0 / 2.20.1** with the
  `events.k8s.io` RBAC action required *before* upgrading, the four scaler
  metadata removals that 2.19 only warned about, and the new CRD validation
  markers that can reject previously-accepted ScaledObjects.
- **rook** — added **1.20** (new minor, 2026-06-02; latest 1.20.2). Ceph CSI
  operator is now mandatory and CSI settings are gone from the operator
  ConfigMap and `rook-ceph` chart; unused CRUSH rules are deleted by default.
  1.18 marked as fallen out of the current+prior-2 window.
- **openebs** — added **LocalPV-LVM 1.9.0/1.9.1** (umbrella 4.5.0/4.5.1) with
  the thin-pool `GetCapacity` fix that changes scheduling maths.
- **rancher** — edition discriminator re-run: **v2.14.3 is Community** (new
  2.14 ceiling); v2.13.7 / v2.12.11 / v2.11.15 are all Prime-docs redirects, so
  those three ceilings are unchanged. The "older minor's top tag is Prime"
  pattern held exactly.
- **harvester** — community patches **1.8.1** (2026-06-29) and **1.7.2**
  (2026-07-07) recorded; noted that 1.7.2 post-dates 1.8.1, so `sort -V` across
  tags does not yield the newest release. 1.9.0-rc2 flagged as not-released.
- **Patch-level restamps:** cilium 1.19.6/1.18.12/1.17.18; rke2
  1.36.2/1.35.6/1.34.9/1.33.13; argo-cd 3.4.5/3.3.12; kyverno 1.18.2; traefik
  3.7.8; harbor 2.15.2 (security fix + Redis→Valkey cache backend); eck 3.4.1;
  gpu-operator 26.3.3.
- **Re-probed, no change (recorded as such rather than silently restamped):**
  tetragon 1.7.0 still latest; zalando postgres-operator v1.15.1 unchanged for
  7 months; gitlab still chart 10.x / app 19.x; ceph k8s axis unchanged by Rook
  1.20; cilium 1.20 is still pre-release only.

**Not applied (stays Open):** the Ceph patch-level drift above — same reason as
2026-05-28, it needs a multi-fetch prose sift of docs.ceph.com release notes to
extract new known-bad point releases, which is not an atomic header edit.

## Resolved — 2026-05-28 (first pass)

### freshen — 2026-06-02 (floor-override pass, operator-directed migration sources)

Operator-requested floor overrides applied (operator runs / migrates clusters off
versions below the rolling-default floor; registry extended **downward** rather than
abstaining). All version numbers grounded via no-candidate enumeration + per-minor
`sort -V` (House Rule #8). Five compat files backfilled, `components.md` floor cells +
headers + `sources.md` rows updated atomically:

- **Harbor floor 2.13 → 2.11.** §2.12 (chart 1.16.x, app v2.12.4, k8s **1.29–1.31**
  — matrix verified exact at chart tag v1.16.4) + §2.11 (chart 1.15.x, app v2.11.2,
  k8s **1.23–1.25** — verified exact at v1.15.2; bundled **PostgreSQL 14→15** one-way
  DB bump is the load-bearing 2.11 hazard). k8s floors read from harbor-helm
  `.github/workflows/integration.yaml` (README only states generic "1.20+").
- **Rancher floor 2.12 → 2.11.** §2.11 (k8s **1.30–1.32**; community ceiling **v2.11.3**
  = the operator's stated migration source, confirmed community). Forward-migration
  framing: what a 2.11 operator must clear before the 2.12 hop (re-import pre-2.11
  direct-`provisioning.cattle.io` clusters, RKE1 sweep, k8s ≥1.31, OIDC AuthConfig
  backup, aggregation-layer requirement origin).
- **ECK floor 3.2.0 → 2.16.** §3.1.0 (k8s 1.29–1.33), §3.0.0 (k8s 1.28–1.32; the
  **2.x→3.0 operator-major hop** — adds Stack 9.0, removes 6.x, 9.0 staged through
  8.18), §2.16.1 (k8s 1.27–1.32, last line managing Stack 6.x). Added the **ES 8.8 /
  8.14 / 8.17** cross-cutting table: all 8.x → every tracked ECK minor (2.16.1→3.4)
  manages them; constraint is ES-side EOL (all three EOL).
- **OpenEBS → refocused to LocalPV-LVM only** (operator-directed, same session).
  Backfilled the umbrella to 4.0, then **re-scoped the file to the LVM engine alone**,
  re-keyed by LocalPV-LVM version (§1.8.0 → §1.5.1) and dropped Mayastor / LocalPV-ZFS /
  LocalPV-Hostpath / LocalPV-Rawfile / cStor / Jiva entirely. Floor = **LVM 1.5** (engine
  umbrella 4.0.1 pins). LVM versions/dates grounded from `openebs/lvm-localpv`; umbrella→LVM
  pin map from umbrella `Chart.yaml` `dependencies:`. `components.md` row → "OpenEBS
  (LocalPV-LVM only) | 1.5"; `cluster-survey.md` detection narrowed (`local.openebs.io`
  CRDs + `lvm-localpv` chart = tracked; other engines → untracked/abstain); `sources.md`
  row → lvm-localpv. Registry count unchanged (19 — OpenEBS is one component, scoped to LVM).
- **Traefik floor 3.5.0 → 2.11.** §3.4–§3.0 ladder + §2.11. §3.0.0 = the **v2→v3
  migration landing** (`traefik.containo.us`→`traefik.io` CRD-group flip, v3 rule
  syntax); §2.11 (v2.11.46, fully EOL) = migration SOURCE → `✗ blocker`. Gateway API
  version grounded per minor (3.0→v1.0.0 … 3.4→v1.2.1) from each tag's `go.mod`.
  Support-window table extended continuous 3.7→2.11.

### freshen methodology hardening — 2026-06-02 (Rancher edition discriminator, third format)

- **Recurrence fix.** The documented edition discriminator (`version-verification.md`
  § Edition discrimination) tested only the release-notes **first line** for the
  Prime-docs redirect and treated its absence as community. Grounding the 2.11 line
  exposed a **third format the first-line test under-detects**: v2.11.4–v2.11.8
  self-declare `"This is a Prime version release"` in the body while keeping an inline
  `# Release vX.Y.Z` first line — so the first-line test wrongly passes them as
  community (it would have returned v2.11.8; `sort -V | tail -1` returns v2.11.14).
  The robust discriminator greps the body for the `"This is a … version release"`
  **self-declaration line**. Fixed in `version-verification.md` (new "Three Rancher
  release-note formats" table + self-declaration-grep bash + verified 2.11 evidence),
  `compat/rancher.md` (§ Community vs Prime 2.11-line caveat + §2.11 edition note),
  and the `sources.md` Rancher row note. Verified-true via independent body enumeration
  of all 15 v2.11.x tags (2026-06-02).



### improve — 2026-05-30 (field upgrade lessons merged: RKE2 1.32 → 1.33)

Merged a field-validated 1.32 → 1.33 upgrade-gotchas briefing into the compat
data — extracting only durable **compat-registry / survey-verdict** signal (the
skill is methodology, "NOT for executing upgrades"), dropping the per-node runbook
and host/hardware-specific firmware noise. Each lesson landed where the skill
consumes it; provenance tagged inline (`field-validated 2026-05-30`):

- **`compat/rke2.md` § 1.33 — etcd 3.5 → 3.6, the headline 1.32→1.33 risk.**
  Grounded vs RKE2 release notes that the 3.6 bump first ships at **v1.33.11**
  (1.33.10 = etcd `v3.5.26-k3s1`, 1.33.11 = `v3.6.7-k3s1`), not at 1.33.0. Added
  the hard **≥ 3.5.26** all-members prereq (zombie-member fix; 1.33.10 already
  satisfies it), mixed-window discipline + storage-version auto-promote, leader-last
  reboot, post-convergence rollback narrowing. Added the benign rke2-server
  restart-storm / transient-NotReady note (rke2#5614, etcd#16287/#19635) with the
  real readiness signal: **OOM on low-RAM swap-off masters**. Refined the § 1.32 /
  § 1.31 cross-minor etcd lines to the grounded 1.33.11.
- **`compat/nvidia-gpu-operator.md` — host-driver/loaded-`.ko` mismatch** after an
  OS package upgrade (rc 18 / `NVML_ERROR_LIB_RM_VERSION_MISMATCH`), device-plugin
  crashloop until reboot, not flagged by `reboot-required`; rc 18 vs rc 9/12
  distinction; assert on `nvidia-smi == 0`; skip non-NVIDIA hosts.
- **`compat/cilium.md` + `compat/tetragon.md`** — kernel **6.17** BPF verifier
  `WARN_ONCE` (`verifier.c:2752`, `cilium-agent`, tc/`cls_bpf`): cosmetic, dataplane
  fine. Cross-ref pair: **not Tetragon** (kprobe/fentry, no `cls_bpf`); a Tetragon
  trigger of the same path is masked because Cilium loads first — validates the
  Tetragon kernel-axis model.
- **`compat/rook.md` — node drain/reboot during a rolling upgrade** (cross-version):
  OSD/mon/mgr on shared master+worker nodes; gate on CephCluster HEALTH_OK + CSI
  unmount; degraded/backfill recovery window; **trap — never gate on Rook PDBs by
  name** (created/deleted dynamically; per-failure-domain `rook-ceph-osd` PDBs).
- **`cluster-survey.md` Phase 1 — server-version display lag** in a partially-upgraded
  control plane: trust per-node `kubectl get nodes` VERSION, not `kubectl version`.

### improve — 2026-05-30 (Tetragon component added; registry 18 → 19)

- **Operator-directed content gap closed:** the registry was missing **Tetragon**
  (`cilium/tetragon`, Cilium's eBPF runtime-security/observability sibling). Added
  end-to-end per the `components.md` "Adding a component" procedure + cross-file
  wiring:
  - NEW `references/compat/tetragon.md` — multi-axis, `release_notes`. The
    load-bearing **kernel axis** (min 4.19; arm64 ≥ 5.10; BTF required;
    `CONFIG_BPF_KPROBE_OVERRIDE` for enforcement; `CONFIG_BPF_LSM` ≥ 5.7 for the
    LSM sensor; ring-buffer default ≥ 5.11; cgroup v1 ≥ 6.11 extra configs) +
    loose k8s axis (no published matrix, chart sets no `kubeVersion:`, chart ==
    app version). Per-minor breaking signal sifted for 1.7 / 1.6 / 1.5.
  - `components.md` — count 18 → 19; new multi-axis stanza under "No published
    matrix"; Cilium-sibling-not-Cilium note.
  - `cluster-survey.md` — detection wired: shares the `cilium.io` CRD group with
    Cilium, so keyed on the `tracingpolicies.cilium.io` CRD + `tetragon` chart /
    DaemonSet; merge note routes Tetragon's kernel axis to the Phase 1
    `KERNEL-VERSION` column; "18 → 19 registry entries".
  - `sources.md` — Tetragon row (FAQ kernel-floor source + chart source + probe).
  - `version-verification.md` — `cilium/tetragon` added to the repo map (kernel
    floor not `gh`-groundable — from `tetragon.io/docs/installation/faq/`).
  - `SKILL.md` — description count + component list (+"Tetragon"); combined
    description+when_to_use = 1496 chars (under the 1536 Dim 1 cap, 40 margin);
    "19-entry registry". `report-format.md` — three "of 18" → "of 19".
- **All versions release-grounded (House Rule #8):** anchored on
  `gh api repos/cilium/tetragon/releases/latest` → `v1.7.0`; minors enumerated +
  `sort -V` (1.7.0 / 1.6.1 / 1.5.0, none newer than `latest`); Chart.yaml read at
  the `v1.7.0`/`v1.6.0`/`v1.5.0` tags (chart == app, no `kubeVersion:`); CRD
  apiVersion (`cilium.io/v1alpha1`, TracingPolicy/TracingPolicyNamespaced/PodInfo)
  confirmed against `pkg/k8s/apis/cilium.io/client/crds/v1alpha1/`. No CVE-patch
  / "fixed-in" claims authored (the body endpoint is contaminated), so nothing
  added to Open.

### freshen — 2026-05-30 (release-grounding pass, House Rule #8)

- **argo-cd fabrication removed** (this session): struck invented `v3.2.10` /
  `v3.2.12` + "CVE fixed in 3.2.10"; the 3.2 line ended at `v3.2.6` (unpatched);
  grounded latest `v3.4.3`. The 2026-05-28 `gh release view`-based pass did NOT
  catch this (it bumped only the 3.4 / 3.3 headers).
- **harbor fabrication flagged**: `§ 2.15` is not a published release
  (`releases/latest` = `v2.14.4`); banner + UNVERIFIED marker added; line is 2.14.x.
- **nvidia version-drift applied**: real latest `v26.3.2` over documented
  `§ 26.3.1` (existence grounded; content sift in Open).
- **15 gh-backed components release-grounded** via `releases/latest`; 12
  confirmed fresh + nvidia existence. See `sources.md` § 2026-05-30.
- **Methodology hardened (recurrence fix):** House Rule #8 + new
  `references/version-verification.md` (anchor on `releases/latest`,
  enumerate-and-derive, never ask "does vX exist?"); wired into SKILL.md,
  cluster-survey.md (Phase 4b), tooling.md, compat/README.md. Root cause: prior
  runs verified via `gh release list` / `gh release view` / `gh api tags` — the
  confirmatory endpoints that let the fabrications through.

### Improve + freshen run — 2026-05-28 (cap-lift + patch-drift pass)

- **Dim 1 trigger-truncation Open item RESOLVED (Pattern 1.4/6.1).** Trimmed
  the air-gap/freshen maintenance prose from `description` (no trigger phrase
  lost): combined `description` + `when_to_use` 1562 → 1486 chars, now under
  the 1536 listing cap with margin. The late-listed load-bearing triggers
  ("Mimir Chart kubeVersion", "ECK against k8s 1.NN", apiserver
  deprecated-API metric) are no longer at truncation risk. Dim 1 7 → 8.
  Supersedes the prior plan to route this to `trigger` mode — a pure deletion
  fit in one improve iteration.
- **Dim 6 survey-step de-duplication (Pattern 6.1, Boris cap-lift).** Collapsed
  the 5-step Survey workflow's procedural steps 2–5 (which duplicated
  `cluster-survey.md` Phases 2–5 verbatim) into a single goal + tool-pointer
  line, keeping the unique change-set taxonomy (step 1) intact. Fixed the
  dangling `Survey workflow § 1` cross-reference in the Verdict format to
  `§ Survey workflow`. SKILL.md 193 → 181 lines. Dim 6 8 → 9.
- **Four in-minor patch-drift findings bumped (Dim 9 freshen).** Verified each
  new patch's release notes carry no new breaking section before stamping:
  - `compat/argo-cd.md`: 3.4 latest v3.4.2 → **v3.4.3** (2026-05-28); 3.3
    latest v3.3.10 → **v3.3.11** (2026-05-28). Both pure bug-fix + dep bump
    (UI CVE-2026-41240).
  - `compat/rancher.md`: 2.14 latest community v2.14.1 → **v2.14.2**
    (2026-05-28). No new breaking item (2.14.2 restates the 2.14.0/2.14.1
    CAAPF-disable + embedded-CAPI-removed signals; floor 1.33–1.35 unchanged).
  - `compat/kyverno.md`: 1.18.0 header now notes **latest patch 1.18.1**
    (2026-05-18). No breaking/migration heading in 1.18.1.
  - `compat/traefik.md`: 3.7.0 header now notes **latest patch 3.7.1**
    (2026-05-11, **CVE-2026-44774** fix). Additive `CrossProviderNamespaces`
    option; Gateway API stays v1.5.1; no removed feature.

### Freshen run — 2026-05-28 (floor-override pass, operator-driven)

Operator-requested floor overrides applied (running versions in the lab cluster
were below the rolling-default floor; freshen extended the registry to cover
them rather than abstaining):

- **RKE2 floor 1.34 → 1.31.** `compat/rke2.md` backfilled with 1.33 / 1.32 /
  1.31 per-minor sections. Key signal captured: snapshot-controller
  v1beta1→v1beta2 break lands at 1.32; etcd 3.5→3.6 lands at 1.33; Traefik
  v2→v3 chart bump lands at 1.32; Cilium 1.18.x is the ceiling for 1.31;
  upstream k8s 1.31 EOL October 2025. Section headers cite latest community
  `+rke2r1` patches (1.32.13+rke2r1, 1.31.14+rke2r1) per house rule #1;
  Prime-only `+rke2r2` rebuilds noted as installable-if-needed context.
- **Harvester floor 1.6.0 → 1.5.0.** `compat/harvester.md` backfilled with
  1.5.0 section: bundled stack (embedded RKE2 v1.32.3+rke2r1, KubeVirt v1.4.0,
  Longhorn v1.8.1, SLE Micro 5.5), management plane (Rancher v2.11.0,
  harvester-ui-extension v1.5.0), community EOL 2025-10-16 (when 1.6.1 Prime
  shipped) AND past SUSE Prime EOM 2025-12-30 → double-EOL warning. RKE1 EOL
  the headline cross-cutting story; no in-place replatforming path.
- **cert-manager floor 1.18 → 1.17.** `compat/cert-manager.md` backfilled
  with 1.17 section: k8s 1.29–1.33 floor, latest patch 1.17.4, upstream EOL
  2025-10-07, RSA hash + structured-log breaking signals, additive
  `keystores.password` CRD note, `ValidateCAA` deprecation hand-off, 1.16→1.17
  floor jump 1.25 → 1.29.
- **Argo CD floor 3.2 → 3.0.** `compat/argo-cd.md` backfilled with v3.1 +
  v3.0 sections: v3.1 k8s 1.31–1.34 (EOL 2026-05-06 at v3.1.16, CVE-2026-42880
  patched in v3.1.15, OCI Beta, SSA migration opt-in landed here); v3.0 k8s
  1.29–1.32 (EOL 2026-02-02 at v3.0.23, seven default flips with PR cites,
  CVE-2026-42880 patched in v3.0.22, ksonnet removal, default JSON logging).
- All four `components.md` cells + per-compat-file headers updated atomically.

### Freshen run — 2026-05-28 (earlier pass)

- **All 18 sources.md rows stamped `Last verified: 2026-05-28`.** 17 fresh
  (latest upstream tag at or within the compat file's "current + prior 2"
  range), 1 in-minor patch drift (Ceph — see Open above). Dim 9 staleness
  cap should lift on the next score: oldest dated row 0 days, no cap.
- **All 18 `min_tracked_version` cells in `components.md` populated from
  per-compat-file headers.** Replaces the `_set by freshen_` literals with
  semver values: RKE2 1.34, Cilium 1.17, cert-manager 1.18, Kyverno 1.16,
  KEDA 2.17, Argo CD 3.2, Harbor 2.13, Traefik 3.5.0, Rook 1.17, Ceph 18.2,
  OpenEBS 4.2, GitLab 8.11, NVIDIA GPU Operator 25.3, Rancher 2.12,
  Harvester 1.6.0, ECK 3.2.0, Zalando 1.13.0, Mimir 5.7. This **resolves**
  the previous Open item "Format drift between compat/README.md template and
  components.md placeholders" — components.md now carries real semvers, the
  README template still uses `<semver>` (which is correct for a template).
- Updated `sources.md` header — replaced "Stamps are intentionally absent on
  the initial structure pass" claim (no longer true) with a cadence note.

### Improve run — 2026-05-28 (prior pass)

- House rule 7 (air-gap) trimmed — Pattern 6.1.
- Verdict format `✓ ready` example collapsed 2→1 — Pattern 6.3.
- Survey workflow step 5 Harvester example removed — Pattern 6.1.
- Added `allowed-tools` frontmatter — Pattern 9.3.
- Two discards (apiserver caveats, source-disagreement decision tree) — both
  Pattern 6.1 violations.

## Run log

### freshen — 2026-06-02 (floor-override pass, operator-directed)

- Input: operator named five migration-source floors to cover — harbor 2.11.1+,
  rancher 2.11.3, eck 2.16.1+, openebs 4.0.1, traefik 2.11.2+ — plus a research ask:
  "which ECK minors support Elasticsearch 8.8 / 8.14 / 8.17?".
- Grounding (House Rule #8): enumerated all five repos' non-prerelease tags with
  **no candidate named**; derived per-minor-line ceilings via `sort -V`. Traefik
  required `--paginate` (2.11 still gets frequent security patches → older 3.0.x
  patches fell past the first 100 results; 3.0 returned empty until paginated).
  Confirmed ceilings: Harbor app v2.12.4 / v2.11.2 (chart v1.16.4 / v1.15.2),
  ECK v3.1.0 / v3.0.0 / v2.16.1, OpenEBS umbrella v4.1.3 / v4.0.1, Traefik
  v3.4.5 / v3.3.7 / v3.2.5 / v3.1.7 / v3.0.4 / v2.11.46. Rancher 2.11 community
  ceiling **v2.11.3** derived by edition discriminator (independently re-verified).
- Sift: 5 parallel research subagents (opus), one per compat file (distinct files,
  no parallel-edit conflict), each handed the pre-grounded version numbers so they
  sifted **prose only** — no version-fabrication surface. Each grounded content
  against authoritative non-`gh-body` sources (harbor-helm integration matrices +
  Chart.yaml at tags; openebs umbrella Chart.yaml dependencies; ECK versioned
  supported-versions pages + supported_versions.go + client-go inference; Traefik
  migrate/v3.md + deprecation/releases.md + per-tag go.mod; Rancher rendered release
  pages + body edition-discriminator). 13 new sections total.
- Driver verification: independently re-ran the Rancher 2.11 edition enumeration
  (exposed the third release-note format); confirmed the two Harbor k8s matrices
  exact at the chart tags; confirmed ECK 3.1.0 date. Header floors cross-checked
  against components.md (all match). No stale floor references elsewhere.
- Methodology recurrence-fix applied (edition discriminator third format) — see
  Resolved. No blind score (freshen is verification-based, not score-based).
- One new Open item: ES 8.8/8.14 exact EOL dates UNVERIFIED (rolled off
  endoflife.date; 8.17 EOL 2025-08-05 verified).
- **Follow-on operator directive (same session): OpenEBS refocused to LocalPV-LVM
  only.** After the umbrella backfill, the operator scoped OpenEBS to the LVM engine.
  `compat/openebs.md` re-keyed by LocalPV-LVM version (§1.8.0 → §1.5.1, floor LVM 1.5),
  all other engines dropped; LVM versions/dates re-grounded from `openebs/lvm-localpv`
  (two tag schemes — `vX.Y.Z` + `lvm-localpv-X.Y.Z`); umbrella→LVM pin map kept as
  context. Wiring updated: components.md row, cluster-survey.md detection (2 rows),
  sources.md row, version-verification.md repo map. See Resolved this pass.

### improve — 2026-05-30 (field upgrade lessons merge)

- Input: `/tmp/rke2-1.32-to-1.33-upgrade-gotchas.md` (first-hand validated 1.32→1.33
  briefing). Scanned for hostnames/IPs/secrets — none present; kept merged content
  generic and stripped cluster-/hardware-specific framing (node counts, HP ProLiant /
  Matrox firmware-quirk noise list, the per-node runbook).
- Triage: 5 of ~13 gotchas were durable compat/survey signal → merged into rke2 /
  nvidia / cilium / tetragon / rook / cluster-survey. The rest (stage-without-restart
  tactic, crictl-preload retries, apt-timing, worker-reboot ease, per-node procedure,
  host firmware noise) are execution-runbook / host-specific → intentionally NOT
  merged (skill is "NOT for executing upgrades").
- Grounded the one load-bearing patch claim (House Rule #8): enumerated rke2 1.33
  tags, read packaged-etcd in the 1.33.10/.11 bodies → 3.6 transition confirmed at
  1.33.11. No fabricated versions; provenance tagged `field-validated 2026-05-30`.
- 6 files edited, no new files. No blind score (field-content merge, not a rubric
  hill-climb).

### improve — 2026-05-30 (Tetragon addition)

- Research: anchored `cilium/tetragon` on `releases/latest` (`v1.7.0`), enumerated
  non-prerelease tags (clean — no candidate version named in any query), read the
  in-repo FAQ at the `v1.7.0` tag for the kernel floor (ground truth, not memory),
  Chart.yaml at 3 tags, CRD manifests for the apiVersion. `gh release view` 401'd
  on v1.6.0/v1.5.0 (transient); bodies read via the tags endpoint instead (content
  sift of already-enumerated tags, not an existence check).
- Mutations: 1 new compat file + 6 wired files (components, cluster-survey,
  sources, version-verification, SKILL, report-format). One logical change (a new
  component), so not split into rubric iterations — the user gave an explicit
  content directive and the registry's own "Adding a component" procedure spans
  these files. Self-consistency check: every "18"-count surface updated to 19;
  historical run-log "18" entries left intact (they correctly record past passes).
- No blind score (content addition against a real gap, not a rubric hill-climb).
  Skill remains at its prior ~90/100 self-score; Dim 1 margin preserved (1496/1536).

### freshen — 2026-05-30 (release-grounding pass)

- Probe: `releases/latest` scalar for 17 gh repos (clean — no candidate version
  named). 15 returned a version; ceph 404 (no `/latest`); gitlab N/A (not
  GitHub); mimir returned the app tag, not the chart `kubeVersion`.
- Findings: 12 fresh · 2 fabrications (argo-cd, harbor) · 1 drift applied
  (nvidia `v26.3.2`) · 3 not-gh-groundable (ceph / gitlab / mimir → Open) · 1
  claim class (per-version "fixed-in" CVE patches) not body-groundable → Open.
- Key methodology finding: gh release-**body**, **list**, and **tags** endpoints
  are confirmatory/contaminated in this environment (rubber-stamp plausible
  fakes; echo in-context version strings). Only `releases/latest` is
  trustworthy. The prior 2026-05-28 freshen relied on the contaminated
  endpoints — root cause of the surviving fabrications. Fixed via House Rule #8
  + `references/version-verification.md`.
- No blind score (freshen is verification-based, not score-based).

### improve + freshen — 2026-05-28 (cap-lift + patch-drift pass)

- Baseline self: 87/100. Lowest dims: Trigger Precision (7), Simplicity (8).
- 3 keeps, 0 discards. Dim 1 7 → 8 (trim under 1536 cap), Dim 6 8 → 9
  (survey-step de-dup), Dim 9 held at 9 (four patch bumps applied; Ceph
  illustrative-patch drift remains the sole carried drift).
- Freshen: 14 refs probed by recon, 11 current, 4 in-minor patch-drift all
  re-confirmed online this pass via `gh release list` + `gh release view`
  (argo-cd v3.4.3/v3.3.11, rancher v2.14.2, kyverno v1.18.1, traefik v3.7.1)
  and applied as header-marker bumps after verifying no new breaking section.
- Ceph 20.3.0 / 19.3.0 re-confirmed present via tags but NOT bumped — needs a
  docs.ceph.com regression-audit WebFetch (multi-step, non-`gh`); stays Open.
- Final self: 90/100.

### freshen — 2026-05-28 (floor-override pass, operator-driven)

- Floor overrides applied per operator instruction: RKE2 1.31, Harvester
  1.5.0, cert-manager 1.17, Argo CD 3.0.
- Backfill: 7 new per-minor sections written across 4 compat files (RKE2 +3,
  Harvester +1, cert-manager +1, Argo CD +2) via 4 parallel subagents.
- Post-pass fixup: RKE2 1.32 / 1.31 section headers corrected to cite latest
  community `+rke2r1` patch per house rule #1 (subagent had labeled latest
  `+rke2r2` patches as the headline; demoted to contextual note since
  Prime-only labels apply to those rebuilds).
- All probed sources reachable.

### freshen — 2026-05-28 (earlier pass)

- Probe budget: 20 (used 18 + 2 follow-ups for Mimir / GitLab / Ceph
  edge-cases).
- Classifications: 17 fresh, 1 version-drift (Ceph, in-minor, low-risk, not
  auto-applied).
- Mutations applied: stamp 18 dates on sources.md, populate 18
  min_tracked_version cells in components.md, refresh sources.md header.
- All probed sources reachable (no broken / 4xx).
- Rate-limit headroom on completion: 5000/5000 (no gh rate-limit pressure
  this pass).

### improve — 2026-05-28 (prior pass)

- Baseline self: 83/100. Baseline blind: 89/100.
- Final self: 84/100. Final blind: 85/100.
- 6 iterations: 4 keeps + 2 discards.
- Expected score after freshen (Dim 9 cap lift): self → ~86, blind → ~88-89.
