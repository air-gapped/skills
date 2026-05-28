# ECK (Elastic Cloud on Kubernetes) — compat (sifted from published matrix + release notes)

- **Primary source:** https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-supported.html
- **Secondary sources:** https://www.elastic.co/support/matrix (Stack-side only; does NOT cover ECK — verified empty) ; https://github.com/elastic/cloud-on-k8s/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `multi` (axis 1: k8s / OpenShift; axis 2: managed Elastic Stack range)
- **min_tracked_version:** 3.2.0
- **Last sifted:** 2026-05-28

Notes on sources:

- The current `k8s-supported.html` page collapses 3.3 and 3.4 into one matrix ("3.3 and later"). Per-minor differences are reconstructed from release notes (`v3.X.0` GitHub releases) and from `pkg/controller/elasticsearch/version/supported_versions.go` on the `3.x` branch.
- The Helm `Chart.yaml` `kubeVersion` is permissive (`>=1.21.0-0`) across all 3.x minors — **do not trust it**, it admits k8s minors the docs page excludes. Use the docs page.
- `support/matrix` is Stack-only and does not surface ECK at all — confirmed 2026-05-28.

## 3.4.0 — 2026-05-05

- **k8s floor:** 1.31 – 1.35
- **OpenShift floor:** 4.16 – 4.20
- **Helm floor:** 3.2.0+
- **Elastic Stack range:**
  - Elasticsearch / Kibana / APM Server: 8.x, 9.x
  - Beats: 8.x, 9.x
  - Elastic Agent (Fleet + standalone): 8.x, 9.x
  - Elastic Maps Server: 8.x, 9.x
  - Logstash: 8.12+, 9.x
  - Enterprise Search: 8.x **only** (no 9.x — Enterprise Search EOL'd at 9.0)
- **Breaking:** none operator-side. New Elasticsearch `xpack.security.fips_mode.enabled=true` now triggers operator-managed password-protected keystore (Elasticsearch 9.4.0+ only — earlier 9.x with FIPS still needs manual `podTemplate` override).
- **CRD migrations:** none.
- **Upgrade ordering:** operator (3.3.x → 3.4.0) before any Stack rolling restart; new `eck.k8s.elastic.co/restart` annotation mechanism is operator-managed — old manual pod-deletion recipes still work but the annotation supersedes them.
- **Deprecations:** none new.
- **Cross-component / notable:**
  - Container images now signed with Sigstore cosign — verify in air-gapped mirrors.
  - `controller-runtime` bumped to v0.23.x → k8s client-go v0.35.x baked in (matches the 1.35 ceiling).
  - Default Kibana memory bumped 1Gi → 2Gi (watch for OOM on tight namespaces using prior defaults).
  - Helm chart gains `extraObjects`, `kubeAPIServerPort`, image-digest pinning.
  - Webhooks migrated to controller-runtime `Validator` interface — custom validating webhooks layered on top of ECK should be re-tested.
  - License-gated (Enterprise) features in this release: client-certificate auth for Elasticsearch, mTLS Kibana→Elasticsearch presentation cert. Operator does not require a license; these specific features do.

## 3.3.2 — 2026-04-01

- **k8s floor:** 1.31 – 1.35 (same as 3.3.0)
- **OpenShift floor:** 4.16 – 4.20
- **Elastic Stack range:** same as 3.3.0.
- **Breaking:** none.
- **Notable:** FIPS build fixed (`GOEXPERIMENT=boringcrypto`); preliminary native Go FIPS 140-3 wiring (not active until module is certified). Operators running 3.3.0 / 3.3.1 FIPS images **should bump to 3.3.2**.

## 3.3.1 — 2026-02-25

- **k8s floor:** same as 3.3.0.
- **Notable:** AutoOps no longer requires Enterprise license (`AutoOpsAgentPolicy` usable on Basic). Minimum AutoOps agent bumped to 9.2.4 for Basic-license users. Safe to skip directly to 3.3.2.

## 3.3.0 — 2026-02-03

- **k8s floor:** 1.31 – 1.35 (matrix-expansion release — adds 1.35, drops everything below 1.31)
- **OpenShift floor:** 4.16 – 4.20
- **Helm floor:** 3.2.0+
- **Elastic Stack range:**
  - Elasticsearch / Kibana / APM Server: 8.x, 9.x (**7.17.x dropped from documented support** — release-note line: *"Remove support for Stack 7.17"*)
  - Beats / Elastic Agent / Maps Server: 8.x, 9.x
  - Logstash: 8.12+, 9.x
  - Enterprise Search: 8.x only.
  - **Codebase:** Elasticsearch 6.x support fully removed (`pkg/controller/elasticsearch/version/supported_versions.go` no longer carries the 6.8 wire-compat min for 7.x). 7.x clusters still reconcile but the 6→7 wire-compat fallback is gone — relevant if a long-frozen 7.x cluster historically depended on it.
- **Breaking:**
  - 7.17.x **off the documented support window**. Operator still reconciles 7.x but Elastic-side support stops here. Migrate to 8.x before bumping ECK to 3.3.
  - Stack Config Policies semantics flipped: higher `weight` now takes precedence (PR #9046). If multi-SCP was used on 3.2 with reversed assumption, recompute weights before upgrade.
  - Single-master-at-a-time upscale restriction removed — masters can scale up in parallel. Operationally faster, but watch for transient quorum churn during large scale-ups.
  - Master StatefulSet now upgraded **last** during a Stack version bump (PR #8871, fixes #8429). Old ordering assumed master-first; runbooks that watched master pods first during upgrades need updating.
- **CRD migrations:** none — CRD apiVersions unchanged from 3.2.
- **Upgrade ordering:** operator 3.2.x → 3.3.0 before bumping k8s above 1.34. Bump Stack off 7.17.x **before** upgrading ECK to 3.3.0 or the operator will reconcile clusters that are now out-of-support.
- **Deprecations:** Stack 7.17.x (documented support removed).
- **Cross-component / notable:**
  - New `PackageRegistry` CRD (`packageregistry.k8s.elastic.co`) — first-class air-gapped EPR managed by the operator. Useful for Fleet/Agent + Kibana in air-gapped clusters.
  - New `AutoOpsAgentPolicy` CRD — Enterprise-only in 3.3.0, opened to Basic in 3.3.1.
  - `controller-runtime` v0.22.x; k8s client-go v0.35.0 (drives the 1.35 ceiling).

## 3.2.0 — 2025-10-30

- **k8s floor:** 1.29 – 1.34 *(verify on upgrade — 3.2-era supported.html no longer reachable; floor inferred from controller-runtime v0.21/0.22 and client-go v0.33/0.34 in this release. Mark unreachable if exact range matters.)*
- **OpenShift floor:** 4.14 – 4.19 *(same caveat)*
- **Helm floor:** 3.2.0+
- **Elastic Stack range:**
  - Elasticsearch / Kibana / APM Server / Beats / Agent / Maps: 7.17+, 8.x, 9.x (7.17 still documented here — 3.3.0 is the release that drops it)
  - Logstash: 8.12+, 9.x
  - Enterprise Search: 8.x only.
  - 6.x: codebase still carries 6.8 wire-compat min for 7.x clusters (removed in 3.3.0).
- **Breaking:** none operator-side.
- **CRD migrations:** none.
- **Upgrade ordering:** straightforward — operator first, then Stack-side bumps. No special ordering vs 3.1.
- **Deprecations:** none new (7.17 deprecation lands in 3.3.0).
- **Cross-component / notable:**
  - Default password length raised to 24 chars (configurable up to 72) — clients reading the elastic-user secret should not assume a fixed length.
  - New granular PDB per node-role tier (Enterprise feature) — replaces the prior single-PDB-per-cluster default for Enterprise licensees. CE clusters keep the simpler PDB.
  - `GOMEMLIMIT` now auto-set from cgroups — operator pod memory tuning changes; lifting limits at runtime may need cgroup-level changes, not just env var.
  - Stack monitoring Beats now reload certificates without restart (#8833).

## Cross-cutting notes (apply to all tracked minors)

- **License gating, CE clarity.** ECK operator binary is single-build; "Enterprise" features are runtime-gated by license CR. Operator runs fine without a license (Basic). Features that *require* Enterprise in 3.2–3.4: granular per-role PDBs (3.2+), `AutoOpsAgentPolicy` (Enterprise in 3.3.0, Basic from 3.3.1), Stack Config Policies composition (3.3+), client-certificate auth (3.4+). EE-as-CE pattern is **not applicable** to ECK — these are license-key gated, not binary-gated.
- **OpenShift caveat.** ECK runs as `runAsNonRoot` since long-ago. 3.4 sets `seccompProfile: RuntimeDefault` by default — verify OpenShift `SecurityContextConstraints` permit this (`restricted-v2` does, `restricted` v1 does not).
- **k8s upgrade-ordering rule for ECK clusters.** Always upgrade the **ECK operator** to a release whose k8s support window includes the target k8s minor *before* bumping k8s. Then perform the k8s upgrade. Stack-version bumps are independent and rolling-restart safe; the master-upgrade-last change in 3.3.0 only matters during Stack-version upgrades, not k8s upgrades.
- **CRD apiVersion stability.** No `elasticsearch.k8s.elastic.co` apiVersion bumps across 3.2 → 3.4. CRDs remain `v1` shape. Webhooks moved to controller-runtime `Validator` in 3.4 but the served apiVersion is unchanged.
- **Fleet / Agent lifecycle.** ECK manages Agent CR lifecycle (Fleet-managed and standalone) across the whole 3.2–3.4 window. The Fleet config gating change in 3.2 (#8869) confines advanced Fleet config logic to Agent v8.13+ — running older Agents under a 3.2+ operator silently ignores some Fleet config fields.
