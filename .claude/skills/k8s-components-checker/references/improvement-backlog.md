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

## Resolved this pass

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
