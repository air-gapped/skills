# improvement-backlog.md

Ceiling findings from skill-improver runs.

## Open

### Dim 1 trigger truncation risk past 1536 chars (Dim 1) (carried 2026-05-28)

- `SKILL.md:3-26`: combined `description` + `when_to_use` measures somewhere
  between 1486 and 1732 chars across blind runs. Even at the lower bound, the
  Claude Code listing dynamic-budget can shrink further when many skills are
  installed, putting late-listed triggers ("Mimir Chart kubeVersion", "ECK
  against k8s 1.NN", apiserver deprecated-API metric) at risk of truncation.
- Improve-mode tried trim-then-add-content patterns; trigger-mode is the
  correct tool.
- Action: run `/skill-improver trigger k8s-components-checker` with the
  listed late phrases as `--missed` flags so they appear as should-trigger
  eval entries. Re-balance `description` vs `when_to_use`, prioritise
  front-loading rare-but-load-bearing phrases.

### Ceph patch-level drift in compat/ceph.md (low-risk, in-minor)

- Compat file references Tentacle 20.2.1, Squid 19.2.3, Reef 18.2.8 as the
  illustrative latest patches at sift time. Freshen probe (2026-05-28) found:
  - Tentacle: latest stable is **20.3.0** (compat says 20.2.1)
  - Squid: latest stable is **19.3.0** (compat says 19.2.3)
  - Reef: latest stable is **18.2.8** ✓
- Drift is in-minor (Tentacle stays Tentacle, Squid stays Squid). The compat
  file's load-bearing structure — Tentacle/Squid/Reef series characteristics,
  4 known-bad point releases (18.2.5, 18.2.6, 19.2.0, 19.2.1), EOL dates,
  intra-cluster upgrade ordering — remains accurate.
- Not auto-bumped because freshen-patterns §3.2 requires checking the
  breaking-change section of each new patch before bumping. Two new patches
  to verify (20.2.2..20.3.0, 19.2.4..19.3.0). Each needs a release-notes
  read.
- Action: read https://docs.ceph.com/en/tentacle/releases/ and
  https://docs.ceph.com/en/squid/releases/ for the new patches; add any new
  known-bad to the compat file's "patches to avoid" list; bump the
  illustrative patch numbers in the version headers.

## Resolved this pass

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
