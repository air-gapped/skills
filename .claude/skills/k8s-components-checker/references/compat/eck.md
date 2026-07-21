# ECK (Elastic Cloud on Kubernetes) — compat (sifted from published matrix + release notes)

- **Primary source:** https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-supported.html
- **Secondary sources:** https://www.elastic.co/support/matrix (Stack-side only; does NOT cover ECK — verified empty) ; https://github.com/elastic/cloud-on-k8s/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `multi` (axis 1: k8s / OpenShift; axis 2: managed Elastic Stack range)
- **min_tracked_version:** 2.16
- **Last sifted:** 2026-07-21
- **Last release-verified:** 2026-07-21

Notes on sources:

- The current `k8s-supported.html` page collapses 3.3 and 3.4 into one matrix ("3.3 and later"). Per-minor differences are reconstructed from release notes (`v3.X.0` GitHub releases) and from `pkg/controller/elasticsearch/version/supported_versions.go` on the `3.x` branch.
- The k8s/OpenShift/Helm floors for **3.1, 3.0, and 2.16 are matrix-grounded** off the still-reachable per-version pages: 2.16 / 3.0 versioned `…/cloud-on-k8s/<ver>/k8s-supported.html` resolve directly, and the *current* page still tabulates a per-minor row for 3.1/3.2 (3.1's Stack column is collapsed there, so 3.1's Stack range is carried from the 3.2 row — same pre-3.3 shape). Only the 3.2.0 floors remain inferred (its versioned page 404s). The 3.1 versioned URL also 404s but its row survives on the current page.
- The Helm `Chart.yaml` `kubeVersion` is permissive (`>=1.21.0-0`) across all 3.x minors — **do not trust it**, it admits k8s minors the docs page excludes. Use the docs page.
- `support/matrix` is Stack-only and does not surface ECK at all — confirmed 2026-05-28.

## 3.4.0 — 2026-05-05  (latest patch **3.4.1**, 2026-06-22 — version-verified 2026-07-21, patch contents not sifted)

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

## 3.1.0 — 2025-07-30

- **k8s floor:** 1.29 – 1.33
- **OpenShift floor:** 4.15 – 4.19
- **Helm floor:** 3.2.0+
- **Elastic Stack range:** same as 3.2.0 (current `k8s-supported.html` collapses 3.1 to k8s/OpenShift only; Stack window is the pre-3.3 shape — 7.17 still documented, dropped only at 3.3.0):
  - Elasticsearch / Kibana / APM Server / Beats / Maps: 7.17+, 8.x, 9.x
  - Elastic Agent: 7.10+ (standalone), 7.17+ (Fleet), 8.x, 9.x
  - Logstash: 8.12+, 9.x
  - Enterprise Search: 7.7+, 8.x (no 9.x — Enterprise Search EOL'd at 9.0)
- **Breaking:** none operator-side.
- **CRD migrations:** none — CRD apiVersions unchanged from 3.0.
- **Upgrade ordering:** straightforward — operator first, then Stack-side bumps.
- **Deprecations:** none new.
- **Cross-component / notable:**
  - `go.mod` bumped to `/v3` (#8609) — only matters to forks/importers, not operators.
  - UBI images switched from `ubi-minimal` to `ubi-micro` (#8704) — smaller attack surface; re-validate any air-gapped image-scan baseline that pinned the old base layer.
  - Metadata propagation: labels/annotations on Elasticsearch/Kibana/Agent CRs now propagate to child Pods/Services (#8673) — admission webhooks or policies keying on child-object labels may see new labels appear.
  - `controller-runtime` v0.20.x; k8s client-go v0.33.2 (#8699) — drives the 1.33 ceiling.

## 3.0.0 — 2025-04-22

- **k8s floor:** 1.28 – 1.32
- **OpenShift floor:** 4.14 – 4.18
- **Helm floor:** 3.2.0+
- **Elastic Stack range:**
  - Elasticsearch / Kibana / APM Server / Beats / Maps: 7.17+, 8.x, **9.x (new — 9.0.0 support added here)**
  - Elastic Agent: 7.10+ (standalone), 7.17+ (Fleet), 8.x, 9.x
  - Logstash: 8.12+, 9.x
  - Enterprise Search: 7.7+, 8.x only.
  - **6.x Stack support removed** (#8507) — 2.16 was the last operator to manage 6.x; a 6.x cluster cannot be reconciled by 3.0+.
- **Breaking:**
  - **MAJOR operator version (2.x → 3.0).** This is the headline. Treat 2.16 → 3.0 as a deliberate operator-major hop, not a routine minor bump — read the upgrade notes before applying the new operator manifest.
  - 6.x Stack reconciliation removed (#8507). Any 6.8/6.x Elasticsearch still under management must be migrated to 7.17+ **before** the operator is bumped to 3.0, or it will go unreconciled.
  - 9.0 adoption is gated to the operator: "Elastic Stack 9.0.0 is not supported on ECK operators earlier than 3.0.0" (release note) — and 9.0 upgrades are validated to route **through 8.18** (#8559). You cannot jump a Stack straight from <8.18 to 9.0 under ECK; land on 8.18 first.
  - APM Server reworked for 9.0.0 (#8448) — APM users moving to 9.x should re-test their APM Server spec.
- **CRD migrations:** none — CRD apiVersions stay `v1`; no conversion step despite the operator-major bump.
- **Upgrade ordering:**
  - From 2.16.1: bump operator 2.16.1 → 3.0.0 (operator-major hop) **before** bumping k8s above 1.32. The 3.0 operator's k8s window is 1.28–1.32, so an in-place k8s already at 1.31/1.32 is fine; do not bump k8s to 1.33 until the operator is at 3.1+.
  - Stack 9.0 adoption comes **after** the operator is at 3.0+ and any cluster is staged at 8.18 (see Breaking).
- **Deprecations:** 6.x Stack support removed (was already legacy).
- **Cross-component / notable:**
  - `controller-runtime` v0.19.3; k8s client-go v0.32.0 (#8330) — drives the 1.32 ceiling.
  - UBI images dropped the `ubi` suffix for 9.x image paths (#8509) and adopted the new agent image path for 9.0 (#8518) — air-gapped mirrors must seed the new 9.x image coordinates before upgrading managed Stacks to 9.x.

## 2.16.1 — 2025-01-13

- **k8s floor:** 1.27 – 1.32 *(2.16.1 raised the supported window to 1.27–1.32 via #8403; 2.16.0 shipped a lower ceiling — operator runs 2.16.1+, so 1.27–1.32 is the floor to assume)*
- **OpenShift floor:** 4.12 – 4.17
- **Helm floor:** 3.2.0+
- **Elastic Stack range (last 2.x shape — widest backward window, narrowest forward):**
  - Elasticsearch / Kibana / APM Server: 6.8+, 7.1+, 8.x  *(**no 9.x** — 9.0 support arrives only at ECK 3.0.0)*
  - Beats: 7.0+, 8.x
  - Elastic Agent: 7.10+ (standalone), 7.14+ (Fleet), 8.x
  - Elastic Maps Server: 7.11+, 8.x
  - Logstash: 8.7+
  - Enterprise Search: 7.7+, 8.x
  - **6.x still managed here** — `supported_versions.go` on the 2.16 tag still carries the 6.8 minimum; this is the last operator line that reconciles 6.x clusters (removed at 3.0.0).
- **Breaking:** none operator-side within 2.16.
- **CRD migrations:** none.
- **Upgrade ordering (forward-migration story — 2.16 as a migration SOURCE):**
  - **2.16 → 3.0 is a MAJOR operator jump.** The operator-side path is 2.16.1 → 3.0.0 → 3.1.0 → … (operators upgrade one minor/major at a time; do not skip 3.0). CRDs stay `v1` across the boundary, so there is no CRD conversion — but the Stack-support window shifts: 9.x is unavailable until 3.0, and 6.x stops being managed at 3.0.
  - **Stage Stacks before the operator-major hop.** Any managed 6.x cluster must reach 7.17+ before bumping to 3.0 (3.0 removed 6.x). Any cluster you intend to take to 9.0 must first reach 8.18 (3.0 validates 9.0 upgrades only through 8.18).
  - **k8s window widens forward, not backward.** 2.16.1 tops out at k8s 1.32; 3.0 also tops at 1.32 (window 1.28–1.32), 3.1 reaches 1.33. Bump the operator to a release whose window includes the target k8s minor *before* the k8s upgrade — the standard ECK ordering rule (see Cross-cutting notes).
- **Deprecations:** none new in 2.16 itself; 6.x management is implicitly end-of-the-line here (removed next major).
- **Cross-component / notable:**
  - 2.16.1's only substantive change over 2.16.0 is the k8s window bump to 1.27–1.32 (#8403); functionally a compat/patch release. Run 2.16.1, not 2.16.0, on any cluster at k8s 1.31/1.32.
  - `controller-runtime` ~v0.19.x; k8s client-go ~v0.31/0.32 baked in (consistent with the 1.32 ceiling).

## Cross-cutting notes (apply to all tracked minors)

- **License gating, CE clarity.** ECK operator binary is single-build; "Enterprise" features are runtime-gated by license CR. Operator runs fine without a license (Basic). Features that *require* Enterprise in 3.2–3.4: granular per-role PDBs (3.2+), `AutoOpsAgentPolicy` (Enterprise in 3.3.0, Basic from 3.3.1), Stack Config Policies composition (3.3+), client-certificate auth (3.4+). EE-as-CE pattern is **not applicable** to ECK — these are license-key gated, not binary-gated.
- **OpenShift caveat.** ECK runs as `runAsNonRoot` since long-ago. 3.4 sets `seccompProfile: RuntimeDefault` by default — verify OpenShift `SecurityContextConstraints` permit this (`restricted-v2` does, `restricted` v1 does not).
- **k8s upgrade-ordering rule for ECK clusters.** Always upgrade the **ECK operator** to a release whose k8s support window includes the target k8s minor *before* bumping k8s. Then perform the k8s upgrade. Stack-version bumps are independent and rolling-restart safe; the master-upgrade-last change in 3.3.0 only matters during Stack-version upgrades, not k8s upgrades.
- **CRD apiVersion stability — including across the 2.x → 3.x major.** No `elasticsearch.k8s.elastic.co` apiVersion bumps across 2.16 → 3.0 → 3.4. CRDs remain `v1` shape; the 2.x → 3.0 operator-major hop carries **no CRD conversion step**. Webhooks moved to controller-runtime `Validator` in 3.4 but the served apiVersion is unchanged.
- **Fleet / Agent lifecycle.** ECK manages Agent CR lifecycle (Fleet-managed and standalone) across the whole 2.16–3.4 window. The Fleet config gating change in 3.2 (#8869) confines advanced Fleet config logic to Agent v8.13+ — running older Agents under a 3.2+ operator silently ignores some Fleet config fields.

### Which ECK minors manage Elasticsearch 8.8 / 8.14 / 8.17? (operator's question)

All three are **8.x**, so the 7.17-drop at ECK 3.3.0 does **not** affect any of them — every tracked ECK minor documents `8.x` (i.e. `8+`) in its Elasticsearch/Kibana/APM Stack column. So the *full* tracked window manages all three:

| Elasticsearch | GA | ECK minors that document support | ES EOL status (Elastic policy: only the 2 newest 8.x minors get maintenance) |
|---|---|---|---|
| **8.8.x** | 2023-05-23 | ECK 2.16.1 → 3.4 (every tracked minor; 8.x is in-window throughout) | **EOL** — superseded by 8.9 (mid-2023); out of maintenance since ~late 2023. Long past support. |
| **8.14.x** | 2024-06 (8.14.0) | ECK 2.16.1 → 3.4 (every tracked minor) | **EOL** — superseded by 8.15 (Aug 2024); out of maintenance since late 2024. |
| **8.17.x** | 2024-12-11 | ECK 2.16.1 → 3.4 (every tracked minor) | **EOL 2025-08-05** (endoflife.date) — was the final 8.x before 8.18; maintenance ran to 8.19 GA. |

Practical reading for an upgrade verdict:

- **The ECK side is never the constraint for 8.8/8.14/8.17.** Any operator from 2.16.1 through 3.4 will reconcile them — ECK is forward-compatible down to its documented Stack floor, and that floor is well below 8.8 in every tracked minor (2.16 floors at 6.8/7.1; 3.0–3.2 at 7.17; 3.3+ at 8.x). The **8.x floor at 3.3+** is the only place to watch, and 8.8/8.14/8.17 all clear it.
- **The constraint is Stack-side EOL, not ECK.** All three ES minors are out of Elastic maintenance/support today (2026-06). Running them under a current operator works, but they receive no security patches — treat them as migration *sources*, not targets. ECK does not block reconciling an EOL Stack; it just manages whatever you declare.
- **9.0 interplay (only if these are migration sources toward 9.x):** moving any of them to 9.0 requires the operator at **3.0+** and the cluster staged at **8.18** first (3.0 validates 9.0 upgrades only through 8.18, #8559). 8.8/8.14/8.17 cannot jump straight to 9.0 — land on 8.18 under a 3.0+ operator, then go to 9.x.

Sources: ECK supported-versions pages 2.16 / 3.0 / 3.1 / current (`elastic.co/guide/en/cloud-on-k8s/<ver>/k8s-supported.html`); ECK 3.0.0 release notes (#8507 6.x removal, #8559 9.0-through-8.18); endoflife.date/elasticsearch (8.17 EOL 2025-08-05); Elastic EOL policy `elastic.co/support/eol` (two-newest-minors maintenance rule). 8.8/8.14 per-minor EOL dates are no longer enumerated by endoflife.date (rolled off as long-superseded) — status derived from the published maintenance policy + successor-minor GA dates; mark the exact 8.8/8.14 end-of-maintenance day **UNVERIFIED** (only the policy-derived "EOL well before 2026" is certain).
