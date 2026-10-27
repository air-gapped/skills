# ECK (Elastic Cloud on Kubernetes) — compat (sifted from published matrix + release notes)

- **Primary source:** https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-supported.html
- **PRIMARY source (corrected 2026-09-15):** https://www.elastic.co/support/matrix — **it DOES cover ECK, in full.** Fetch the page with plain `curl` (no JS needed), read the server-rendered `<script id="__NEXT_DATA__">` blob, and take the CSV asset named `support-matrix-product-and-kubernetes-elastic-cloud-on-kubernetes-and-kubernetes-distro.csv`. It carries **every ECK minor from 1.0.x to 3.5.x** with release date, Kubernetes range and OpenShift range — one round trip for the whole history.
- **Secondary:** https://github.com/elastic/cloud-on-k8s/releases ; https://elastic.co/docs/deploy-manage/deploy/cloud-on-k8s#k8s-supported (the current guide page — a tabbed widget covering only the ~5 newest minors, but it carries the Elastic Stack compatibility axis the CSV does not)
- **Truth source type:** `published_matrix`
- **Axis type:** `multi` (axis 1: k8s / OpenShift; axis 2: managed Elastic Stack range)
- **min_tracked_version:** 2.16
- **Last sifted:** 2026-10-12 (breaking changes 3.4/3.5, upgrade path from 2.x, restart pacing)
- **CORRECTION — the probe method was broken and the inferences it produced were wrong.** This file recorded that `support/matrix` "does NOT cover ECK — verified empty", and so fell back to probing per-minor guide pages and *inferring* windows from which ones 404. Both halves failed. The matrix does cover ECK (above). And the 404 rule no longer discriminates: probed today, **2.14, 3.1, 3.3, 3.4 and 3.5 all 404 while 2.16 and 3.0 still serve** — it is not an old-vs-new split, so a 404 carries no information at all.
- **Four inferred values were wrong**, now replaced with published ones: 3.2.x k8s **1.30–1.34** (was inferred 1.29–1.34) and OpenShift **4.15–4.20** (was 4.14–4.19); 3.4.x k8s **1.31–1.36** (was 1.31–1.35) and OpenShift **4.16–4.22** (was 4.16–4.20). The 3.0.0 release date was also wrong: **2025-04-15**, not 2025-04-22. Unlike a stale number, a wrong inference never ages into correctness — it had to be read off the source to be caught.
- **Published matrix, CSV read 2026-10-27** (release ceiling **v3.5.0**, 2026-08-04, `isLatest`):

  | ECK line | Released | Kubernetes | OpenShift |
  |---|---|---|---|
  | 2.16.x | 2024-12-19 | 1.27–1.32 | 4.12–4.17 |
  | 3.0.x | 2025-04-15 | 1.28–1.32 | 4.14–4.18 |
  | 3.1.x | 2025-07-29 | 1.29–1.33 | 4.15–4.19 |
  | 3.2.x | 2025-10-23 | **1.30–1.34** | **4.15–4.20** |
  | 3.3.x | 2026-02-03 | 1.31–1.35 | 4.16–4.20 |
  | 3.4.x | 2026-05-05 | **1.31–1.36** | **4.16–4.22** |
  | 3.5.x | 2026-07-28 | **1.32–1.36** | 4.16–4.22 |
- **Last release-verified:** 2026-09-24 — 3.5.0 confirmed via `gh api repos/elastic/cloud-on-k8s/releases/tags/v3.5.0` (published 2026-08-04, matches `generated.json`); ranges and breaking-change signal now sifted into `## 3.5.0` below.

Notes on sources:

- The current `k8s-supported.html` page collapses 3.3 and 3.4 into one matrix ("3.3 and later"). Per-minor differences are reconstructed from release notes (`v3.X.0` GitHub releases) and from `pkg/controller/elasticsearch/version/supported_versions.go` on the `3.x` branch.
- The k8s/OpenShift/Helm floors for **3.1, 3.0, and 2.16 are matrix-grounded** off the still-reachable per-version pages: 2.16 / 3.0 versioned `…/cloud-on-k8s/<ver>/k8s-supported.html` resolve directly, and the *current* page still tabulates a per-minor row for 3.1/3.2 (3.1's Stack column is collapsed there, so 3.1's Stack range is carried from the 3.2 row — same pre-3.3 shape). Only the 3.2.0 floors remain inferred (its versioned page 404s). The 3.1 versioned URL also 404s but its row survives on the current page.
- The Helm `Chart.yaml` `kubeVersion` is permissive (`>=1.21.0-0`) across all 3.x minors — **do not trust it**, it admits k8s minors the docs page excludes. Use the docs page.
- ~~`support/matrix` is Stack-only and does not surface ECK at all~~ — **false, retracted 2026-09-15.** See the corrected primary-source note above; it has carried the full ECK history throughout.

## 3.5.0 — 2026-08-04

- **k8s floor:** 1.32 – 1.36 — 3.5 drops k8s 1.31 (matrix CSV; the v3.5.0 e2e kind matrix tests 1.32–1.36). The docs page's "3.4+" tab still reads 1.31–1.36 and `compat.py` reads that tab, so `check --with eck=3.5` passes k8s 1.31: override it — ECK 3.5 on 1.31 is `⚠ needs bump` (k8s first).
- **OpenShift floor:** 4.16 – 4.22 (same as 3.4.x)
- **Helm floor:** 3.2.0+
- **Elastic Stack range:** same as 3.3.0+ (current docs page's "3.3+" Stack tab covers 3.3/3.4/3.5 identically):
  - Elasticsearch / Kibana / APM Server: 8.x, 9.x
  - Beats / Elastic Agent (Fleet + standalone) / Elastic Maps Server: 8.x, 9.x
  - Logstash: 8.12+, 9.x
  - Enterprise Search: 8.x only (no 9.x — EOL'd at 9.0)
- **Breaking:** the operator upgrade restarts **every Fleet Server pod** (pod-spec change; breaking-changes.md § 3.5.0 — no action, plan for it). Otherwise none. `eck.k8s.elastic.co/managed: "false"` annotation is **deprecated** (still functional) in favor of the new `eck.k8s.elastic.co/pause-orchestration` annotation, which — unlike `managed: false` — keeps cert rotation, secret/user management and health monitoring running during the pause instead of stopping all reconciliation.
- **CRD migrations:** none required. New optional `spec.resources` shorthand (top-level; `spec.nodeSets[].resources` for Elasticsearch) added to all 8 pod-owning CRDs (#9346) as a flattened alternative to `podTemplate.spec.containers[name=<main>].resources`. Additive and opt-in — existing manifests are unaffected, and an older (pre-3.5) operator silently ignores the field on rollback.
- **Upgrade ordering:** standard rule applies (operator before k8s bump, see Cross-cutting notes below); no new ordering constraint introduced.
- **Deprecations:** `eck.k8s.elastic.co/managed: "false"` annotation (superseded by `pause-orchestration`, not yet removed).
- **Cross-component / notable:**
  - Mutual TLS now covers every Stack component talking to Elasticsearch — APM Server, Beats, Enterprise Search, Elastic Maps Server, Logstash, Elastic Agent (standalone), Fleet Server — all auto-receive ECK-managed client certs. Fleet Server can additionally require client certs from connecting Agents (**Enterprise** feature); this path is version-gated to Fleet Server/Agent **≥ 8.13.0** (#9598) — older Agents fail mTLS enrollment when it's enabled.
  - Dynamic namespaces: label-selector-based (`namespaceSelector`) namespace scoping as an alternative to the static managed-namespace list, applied live with no operator restart. **Enterprise feature.**
  - Hot-reload of `spec.secureSettings` without pod restarts — opt-in via `eck.k8s.elastic.co/file-based-secure-settings: "true"` annotation, requires **Elasticsearch 9.5+**; older Elasticsearch still needs the rolling-restart path.
  - Security-relevant fix: `FLEET_SERVER_SERVICE_TOKEN` moved from a plaintext pod env var to a Secret (#9626) — clusters running Fleet Server should bump to pick this up.
  - Operator switched to Go native FIPS with a static binary (#9538), building on the FIPS wiring started in 3.3.2.
  - Reduced operator memory footprint: controller-runtime cache auto-scoped to ECK-labelled core workload resources; new opt-in `--restrict-watched-resources` flag further narrows Secrets/Services/ConfigMaps caching to `eck.k8s.elastic.co/watched=true`-labelled objects.
  - `controller-runtime` v0.24.1; k8s client-go v0.36.2 — consistent with the unchanged 1.36 ceiling.

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
- **Breaking (corrected 2026-10-12 — this row said "none operator-side"; Elastic's breaking-changes.md § 3.4.0 lists four):**
  - **Rolling restart of every Elasticsearch pod** during the operator upgrade (`seccompProfile: RuntimeDefault`, new pre-stop hook and readiness-probe scripts).
  - **Rolling restart of Kibana**, and its default memory limit rises **1Gi → 2Gi**. Pods with no explicit limit grow; an explicit limit below 2Gi risks OOM on Kibana 9.4.0+.
  - **Rolling restart of APM Server, Logstash, Elastic Maps Server and Package Registry** wherever the security context is injected (`--set-default-security-context` `true`, or `auto-detect` on non-OpenShift). OpenShift `auto-detect` is unaffected.
  - **Default PVC handling:** a custom PVC in `podTemplate.spec.volumes` named like a default volume (e.g. `elasticsearch-data`) is now *used* instead of ignored, which can make Kubernetes reject the StatefulSet update. Fix: remove the overlapping entry.
  - New Elasticsearch `xpack.security.fips_mode.enabled=true` now triggers operator-managed password-protected keystore (Elasticsearch 9.4.0+ only — earlier 9.x with FIPS still needs manual `podTemplate` override).
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
  - New `PackageRegistry` CRD (`packageregistry.k8s.elastic.co`) — first-class air-gapped EPR managed by the operator. Useful for Fleet/Agent + Kibana in air-gapped clusters. Details: § "Elastic Package Registry (EPR) in air-gapped clusters" below.
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
  - From 2.16.1: the operator may go **directly** to any 3.x (see § 2.16.1 Upgrade ordering); pick one whose k8s window covers the cluster *before* bumping k8s above 1.32. The 3.0 operator's k8s window is 1.28–1.32, so an in-place k8s already at 1.31/1.32 is fine; do not bump k8s to 1.33 until the operator is at 3.1+.
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
  - **2.16 → 3.0 is a MAJOR operator jump.** A **direct hop to the newest 3.x is supported** — Elastic's upgrade page: *"There are no special instructions to follow if you upgrade from any 2.x version"* (corrected 2026-10-12; this row previously said "do not skip 3.0", which the source never said). Skipping is allowed, but read the release notes **and breaking changes of every skipped release** — they only list changes since the previous one. CRDs stay `v1` across the boundary, so there is no CRD conversion — but the Stack-support window shifts: 9.x is unavailable until 3.0, and 6.x stops being managed at 3.0.
  - **Stage Stacks before the operator-major hop.** Any managed 6.x cluster must reach 7.17+ before bumping to 3.0 (3.0 removed 6.x). Any cluster you intend to take to 9.0 must first reach 8.18 (3.0 validates 9.0 upgrades only through 8.18).
  - **k8s window widens forward, not backward.** 2.16.1 tops out at k8s 1.32; 3.0 also tops at 1.32 (window 1.28–1.32), 3.1 reaches 1.33. Bump the operator to a release whose window includes the target k8s minor *before* the k8s upgrade — the standard ECK ordering rule (see Cross-cutting notes).
- **Deprecations:** none new in 2.16 itself; 6.x management is implicitly end-of-the-line here (removed next major).
- **Cross-component / notable:**
  - 2.16.1's only substantive change over 2.16.0 is the k8s window bump to 1.27–1.32 (#8403); functionally a compat/patch release. Run 2.16.1, not 2.16.0, on any cluster at k8s 1.31/1.32.
  - `controller-runtime` ~v0.19.x; k8s client-go ~v0.31/0.32 baked in (consistent with the 1.32 ceiling).

## Operator-upgrade impact ledger (sifted 2026-10-13, through 3.5.0)

**How to use.** For an operator hop *from* → *to*, take every row whose **Ver** satisfies *from* < Ver ≤ *to*. A skipped release still applies: its restarts, behaviour changes and known issues all land in the one hop (Elastic: "Stepping over one of these versions … still triggers a rolling restart"). Rows describe what the **operator upgrade** does to already-running workloads, plus behaviour that changes afterwards. Version support windows and new opt-in features live in the per-version sections above.

**Kinds:** `restart` — pods roll when the new operator starts · `break` — may fail or need action · `behaviour` — changes silently, check your assumptions · `perms` — operator RBAC / CRD surface grows · `deprecation` · `known-issue` — note the fixed-in version · `rollback` — hazard when going back down · `removed`.

| Ver | Kind | Change | What to do | Source |
|---|---|---|---|---|
| 3.0.0 | removed | Stack 6.x no longer reconciled | Move any 6.x to 7.17+ before the hop | breaking/index #8507 |
| 3.0.0 | behaviour | 9.0 upgrades validated to go through 8.18 | 9.x only after the cluster reaches 8.18 (9.0) / 8.19 (9.1+) | index #8559 |
| 3.0.0 | behaviour | 9.x images drop the `ubi` suffix; new Agent image path from 9.0 | Mirror the new 9.x image paths before any 9.x Stack | index #8509 #8518 |
| 3.0.0 | break | Enterprise Search has no 9.x | Migrate off before any Stack 9.x | breaking 3.0.0 |
| 3.1.0 | restart | Stack-monitoring sidecars roll (only when stack monitoring is used) | Plan the roll | upgrade page restart list |
| 3.1.0 | behaviour | Labels/annotations on ES/Kibana/Agent CRs propagate to child Pods/Services | Re-check admission policies and selectors that key on child labels | index #8673 |
| 3.1.0 | behaviour | Stack-monitoring Filebeat moves from the `container` input to `filestream` | Watch for changed monitoring-log ingestion | index #8679 |
| 3.2.0 | restart | Stack-monitoring sidecars roll again (only when stack monitoring is used) | Plan the roll | upgrade page restart list |
| 3.2.0 | behaviour | Advanced Fleet config gated to Agent ≥ 8.13; older Agents silently ignore those fields | Check Agent versions on older Stacks | index #8869 |
| 3.2.0 | behaviour | Fleet-mode Agent CONFIG_PATH aligned to STATE_PATH | See the 3.2.0 rollback row | index #8856 |
| 3.2.0 | behaviour | `GOMEMLIMIT` set automatically from the operator's cgroup memory limit | Revisit operator memory tuning | index #8814 |
| 3.2.0 | rollback | Going below 3.2 and back up: Fleet-mode Agents fail with "cipher: message authentication failed" | Re-enroll with env `FLEET_FORCE=true` on the Agent podTemplate, remove afterwards | known-issues 3.2.0 |
| 3.3.0 | behaviour | Elasticsearch version upgrades roll **master StatefulSets last** (previously first) | Update runbooks that watch masters first | index #8871 |
| 3.3.0 | behaviour | Single-master-at-a-time upscale restriction removed | Expect parallel master scale-up | index #8940 |
| 3.3.0 | behaviour | Operator pod uses standard Kubernetes/Helm labels | Re-check selectors on the operator pod (monitoring, NetworkPolicy) | index #8840 |
| 3.3.0 | behaviour | Kibana `server.name` no longer set by the operator | Check anything relying on it | index #8930 |
| 3.3.0 | perms | New CRDs `AutoOpsAgentPolicy`, `PackageRegistry` (+ RBAC; cluster-wide namespaces read) | Expect the RBAC diff | index #8941 #8800 |
| 3.3.0 | deprecation | Stack 7.17 deprecated | Move off 7.17 | deprecations 3.3.0 |
| 3.3.0 | known-issue | HTTP/transport cert AKI/SKI mismatch → ES nodes cannot join, Kibana/Fleet cannot connect. **Fixed in 3.4.0** | Skip 3.3.x as a target; if hit, delete `<cluster>-es-<nodeset>-es-transport-certs` and `<cluster>-es-http-certs-internal` | known-issues 3.3.0–3.3.2, #9197 |
| 3.3.2 | known-issue | FIPS images 2.9.0–3.3.1 used standard Go crypto, not BoringCrypto. **Fixed in 3.3.2** | FIPS sites target ≥ 3.3.2 | known-issues, #9263 |
| 3.4.0 | restart | **All Elasticsearch pods** roll (`seccompProfile: RuntimeDefault`, new pre-stop/readiness scripts) | Pace with the pause annotation (§ Cross-cutting) | breaking 3.4.0 |
| 3.4.0 | restart | **Kibana** rolls; default memory limit **1Gi → 2Gi** | Check node headroom; explicit limits < 2Gi risk OOM on Kibana 9.4+ | breaking 3.4.0 |
| 3.4.0 | restart | APM Server, Logstash, Maps, Package Registry roll where the security context is injected | Plan the roll | breaking 3.4.0 |
| 3.4.0 | break | A custom PVC in `podTemplate.spec.volumes` named like a default volume is now *used*; Kubernetes may reject the StatefulSet update | Remove the overlapping volume entry | breaking 3.4.0 |
| 3.4.0 | behaviour | Webhooks moved to controller-runtime `Validator`; warnings surfaced | Re-test custom webhooks layered on ECK | index #9235 |
| 3.4.0 | known-issue | Logstash ignores `set-default-security-context` → rejected under an OpenShift `anyuid` SCC. **Fixed in 3.5.0** | Skip 3.4.x on OpenShift with Logstash | known-issues 3.4.x, #9550 |
| 3.5.0 | restart | **Fleet Server** pods roll | Plan the roll | breaking 3.5.0 |
| 3.5.0 | behaviour | Kibana readiness probe uses the status API | Pods may take longer to report Ready | index #9468 |
| 3.5.0 | behaviour | `FLEET_SERVER_SERVICE_TOKEN` moves from a pod env var to a Secret | Nothing; security fix | index #9626 |
| 3.5.0 | behaviour | Operator cache scoped to ECK-labelled workload resources; opt-in `--restrict-watched-resources` | Lower operator memory | index #9339 #9359 |
| 3.5.0 | deprecation | `eck.k8s.elastic.co/managed` annotation → use `pause-orchestration` | Replace in runbooks/scripts | deprecations 3.5.0 |

**Restart-trigger list** (Elastic's upgrade page, read 2026-10-12): 1.6, 1.9, 2.0, 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8, 2.14, 3.1¹, 3.2¹, 3.4², plus 3.5 (Fleet Server, from breaking-changes). ¹ stack monitoring only · ² nearly every workload.

**Adding a release (freshen procedure).** For each new ECK version, read these four pages and append rows; never edit an old row except to fill in a **fixed-in** version:

1. `elastic/cloud-on-k8s` `docs/release-notes/breaking-changes.md` → `restart` / `break` rows.
2. `docs/release-notes/known-issues.md` → `known-issue` rows; when a later release fixes one, add **Fixed in X** to the existing row.
3. `docs/release-notes/deprecations.md` → `deprecation` rows.
4. `docs/release-notes/index.md` (features + fixes) → only items that change behaviour for **existing** workloads (`behaviour`, `perms`). Skip opt-in features and dependency bumps.

Also re-read the restart-trigger list on `elastic/docs-content` `deploy-manage/upgrade/orchestrator/upgrade-cloud-on-k8s.md`; it is maintained separately from the release notes. Bump the date in this section's heading.

## Cross-cutting notes (apply to all tracked minors)

- **License gating, CE clarity.** ECK operator binary is single-build; "Enterprise" features are runtime-gated by license CR. Operator runs fine without a license (Basic). Features that *require* Enterprise in 3.2–3.5: granular per-role PDBs (3.2+), `AutoOpsAgentPolicy` (Enterprise in 3.3.0, Basic from 3.3.1), Stack Config Policies composition (3.3+), client-certificate auth (3.4+), dynamic namespaces and Fleet Server client-cert enforcement (3.5+). EE-as-CE pattern is **not applicable** to ECK — these are license-key gated, not binary-gated.
- **OpenShift caveat.** ECK runs as `runAsNonRoot` since long-ago. 3.4 sets `seccompProfile: RuntimeDefault` by default — verify OpenShift `SecurityContextConstraints` permit this (`restricted-v2` does, `restricted` v1 does not).
- **k8s upgrade-ordering rule for ECK clusters.** Always upgrade the **ECK operator** to a release whose k8s support window includes the target k8s minor *before* bumping k8s. Then perform the k8s upgrade. Stack-version bumps are independent and rolling-restart safe; the master-upgrade-last change in 3.3.0 only matters during Stack-version upgrades, not k8s upgrades.
- **Operator upgrades restart managed pods — and the restarts can be paced.** (Per-release detail: § Operator-upgrade impact ledger.) Source: Elastic's [Upgrade ECK](https://www.elastic.co/docs/deploy-manage/upgrade/orchestrator/upgrade-cloud-on-k8s) § "Control rolling restarts during the upgrade" (read 2026-10-12). Operator versions that trigger a one-time rolling restart when installed: **1.6, 1.9, 2.0, 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8, 2.14, 3.1¹, 3.2¹, 3.4²** (¹ stack-monitoring users only; ² nearly every managed workload — see § 3.4.0). 3.5 adds a Fleet Server restart (§ 3.5.0). **Stepping over one of these versions still triggers its restart** — a 2.16 → 3.5 hop inherits 3.1, 3.2 and 3.4.
  - **To pace the restarts** on a large cluster, annotate the resources *before* the operator upgrade, then remove the annotation per resource when convenient; each restart runs on removal.
  - **Target 3.5+:** `eck.k8s.elastic.co/pause-orchestration=true` — pauses spec-driven changes (StatefulSet/Deployment updates, rolling upgrades, scaling, volume expansion) while cert rotation, services, users/roles, keystore, PDBs and health monitoring keep running. Sets an `OrchestrationPaused` status condition. Only the exact strings `"true"`/`"false"` pass the webhook. Doc: [Pause orchestration](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/k8s-pause-orchestration).
  - **Target 3.0–3.4:** `eck.k8s.elastic.co/managed=false` — stops **all** reconciliation, cert rotation included; remove it promptly. Deprecated in 3.5, still functional.
  - Bulk form: `kubectl annotate --overwrite elastic --all <annotation>` per namespace; resume with the trailing-dash form (`eck.k8s.elastic.co/pause-orchestration-`). Upstream ships a helper at `hack/annotator` in `elastic/cloud-on-k8s`.
- **CRD apiVersion stability — including across the 2.x → 3.x major.** No `elasticsearch.k8s.elastic.co` apiVersion bumps across 2.16 → 3.0 → 3.5. CRDs remain `v1` shape; the 2.x → 3.0 operator-major hop carries **no CRD conversion step**. Webhooks moved to controller-runtime `Validator` in 3.4 but the served apiVersion is unchanged; 3.5's new `resources` shorthand field (all 8 pod-owning CRDs) is likewise additive, not an apiVersion bump.
- **Fleet / Agent lifecycle.** ECK manages Agent CR lifecycle (Fleet-managed and standalone) across the whole 2.16–3.5 window. The Fleet config gating change in 3.2 (#8869) confines advanced Fleet config logic to Agent v8.13+ — running older Agents under a 3.2+ operator silently ignores some Fleet config fields. 3.5's Fleet Server→Agent mTLS enrollment (when enabled) is gated to the same floor (Fleet Server/Agent ≥ 8.13.0, #9598).

### Elastic Package Registry (EPR) in air-gapped clusters (sifted 2026-10-12)

Fleet in Kibana downloads integration packages from EPR (`epr.elastic.co`). An air-gapped cluster must run its own copy from a mirrored `docker.elastic.co/package-registry/distribution` image.

**Hosting — ECK 3.3+ (recommended):** a `PackageRegistry` resource (`packageregistry.k8s.elastic.co/v1alpha1`, still alpha), referenced from Kibana. ECK creates the Deployment, Service and TLS certs and wires Kibana's registry URL itself.

```yaml
apiVersion: packageregistry.k8s.elastic.co/v1alpha1
kind: PackageRegistry
metadata: { name: epr }
spec:
  version: 8.19.23            # Stack version; selects the default image tag
  count: 1
  # image: <mirror>/package-registry/distribution:<tag>   # override the default
---
apiVersion: kibana.k8s.elastic.co/v1
kind: Kibana
spec:
  packageRegistryRef: { name: epr }
```

- **Default image** (ECK v3.5.0 `pkg/controller/common/container/container.go`, `getPackageRegistryImage`): `<container-registry>/package-registry/distribution:lite-<spec.version>`. It goes through the operator's `--container-registry` setting, so a mirror configured there is used without `spec.image`.
- For `spec.version` below **8.15.1** the default tag falls back to `lite-8.15.1` (no older lite builds exist).
- With UBI images the suffix goes **in the tag** (`lite-X.Y.Z-ubi`), unlike other Stack images. That is a separate image to mirror.

**Hosting — ECK below 3.3, or self-managed:** run the image yourself as a Deployment and Service on port 8080, and set the Kibana config key `xpack.fleet.registryUrl` (Kibana CR `spec.config`), e.g. `"http://<svc>.<ns>.svc:8080"`. Elastic's air-gapped Fleet docs, `reference/fleet/air-gapped.md` § "Connect Kibana to your hosted Package Registry". It is a config key, not an environment variable.

**Choosing a tag — what crosses the air gap.** Measured 2026-10-12 on amd64 by pulling each image and counting the files inside every package zip:

| Tag | Compressed | Package zips | Files inside zips | Changes |
|---|---|---|---|---|
| `production` | 22.8 GiB | not counted | not counted (size within 1 % of `8.19.23`) | on every package publish |
| `8.19.23` (Elastic's "recommended", pinned to the Stack release) | 22.7 GiB | 15,398 | 3,932,057 | never |
| `lite-8.19.23` (ECK's default) | 4.39 GiB | 1,988 | 3,068,088 | never |
| `lite` | 4.39 GiB | — | — | on every package publish |

- **No deep nesting:** layer tar.gz → package `.zip` → plain files. No zip holds another archive, detected by magic bytes. The load on a security scanner is file **count**, not depth.
- **Why lite stays at 3 million files:** every tag ships **every version** of each package, betas included. `security_detection_engine` (Elastic's prebuilt detection rules) has **801 versions × up to ~12,600 rule files = 2.93 M files** — 95 % of lite and 75 % of the full image. A Stack-pinned tag (`8.19.23`) still includes packages built for later Stacks (9.5.x), which is why it is almost as large as `production`.
- **Lite trades coverage for size:** it holds only the most commonly used integrations; anything outside that subset is missing, and the next step up is the full ~23 GiB image.
- **To cut the file count, trim versions, not packages.** Keeping only the newest GA version of each package is roughly 8 k files (lite's package set) or 27 k files / 1 GiB unpacked (all 508 packages). Elastic's **distribution tool** (`elastic/package-registry`, `cmd/distribution`, technical preview) collects a chosen package set from EPR, filtered by Kibana version, with signatures verified; build a custom registry image from its output. Pick the newest version **compatible with the target Kibana**, not the newest overall.

Sources: Elastic docs-content `deploy-manage/deploy/cloud-on-k8s/package-registry.md` (CRD, `packageRegistryRef`, lite default, `spec.image`); `reference/fleet/air-gapped.md` (tag meanings, `xpack.fleet.registryUrl`); ECK v3.5.0 `container.go`; `elastic/package-registry` `cmd/distribution/README.md`. Sizes and counts measured 2026-10-12 with `skopeo` plus a magic-byte nested-archive walk. They grow with every package release; re-measure before quoting.

### Which ECK minors manage Elasticsearch 8.8 / 8.14 / 8.17? (operator's question)

All three are **8.x**, so the 7.17-drop at ECK 3.3.0 does **not** affect any of them — every tracked ECK minor documents `8.x` (i.e. `8+`) in its Elasticsearch/Kibana/APM Stack column. So the *full* tracked window manages all three:

| Elasticsearch | GA | ECK minors that document support | ES EOL status (Elastic policy, below) |
|---|---|---|---|
| **8.8.x** | 2023-05-23 | ECK 2.16.1 → 3.5 (every tracked minor; 8.x is in-window throughout) | **EOL** — superseded by 8.9 (mid-2023); out of maintenance since ~late 2023. Long past support. |
| **8.14.x** | 2024-06 (8.14.0) | ECK 2.16.1 → 3.5 (every tracked minor) | **EOL** — superseded by 8.15 (Aug 2024); out of maintenance since late 2024. |
| **8.17.x** | 2024-12-11 | ECK 2.16.1 → 3.5 (every tracked minor) | **EOL 2025-08-05** (endoflife.date as read 2026-09-15; its API reads **2025-08-12** on 2026-10-12, while the policy date — 8.19 GA — is 2025-07-29) — was the final 8.x before 8.18; maintenance ran to 8.19 GA. |

**The policy, in Elastic's own words** ([elastic.co/support/eol](https://www.elastic.co/support/eol),
read 2026-09-15): *"Elastic Stack version 8.17 will be maintained until the release date of
version 8.19, Elastic Stack version 8.18 will be maintained until the release date of version
9.2."* That is an **N+2 rule** — a minor is maintained until its successor's successor ships —
which is what makes the two newest minors the maintained ones at any moment. Derive a date from
the successor-minor GA, not from a fixed interval. It corroborates the 8.17 figure above:
maintenance to 8.19 GA, which endoflife.date dates 2025-08-05.

**8.8 and 8.14 are not on that page at all**, and not on endoflife.date's per-minor table either.
Both are long superseded, so no publisher still lists a per-minor day for them. Their rows above
are derived from the N+2 rule, not fetched — treat "EOL well before 2026" as the certain part and
do not quote an exact day. Re-fetching the live page will not produce one; an archived snapshot
from the relevant period is the only route.

Practical reading for an upgrade verdict:

- **The ECK side is never the constraint for 8.8/8.14/8.17.** Any operator from 2.16.1 through 3.5 will reconcile them — ECK is forward-compatible down to its documented Stack floor, and that floor is well below 8.8 in every tracked minor (2.16 floors at 6.8/7.1; 3.0–3.2 at 7.17; 3.3+ at 8.x). The **8.x floor at 3.3+** is the only place to watch, and 8.8/8.14/8.17 all clear it.
- **The constraint is Stack-side EOL, not ECK.** All three ES minors are out of Elastic maintenance/support today (2026-06). Running them under a current operator works, but they receive no security patches — treat them as migration *sources*, not targets. ECK does not block reconciling an EOL Stack; it just manages whatever you declare.
- **9.x interplay (only if these are migration sources toward 9.x):** the operator must be at **3.0+**. Elastic's path rule (corrected 2026-10-12 — this row said "stage at 8.18", which only reaches **9.0**): to reach **9.0.x** start from **8.18.x**; to reach **9.1 or later** start from **8.19.x**. 9.0 is past EOL, so in practice the staging minor is **8.19**. 8.8/8.14/8.17 cannot jump straight to 9.x.

### Where to take them — supported targets and upgrade paths (sifted 2026-10-12)

ECK 3.3+ manages Elasticsearch/Kibana **8.x and 9.x**, so the operator never limits the choice; Elastic's support window and upgrade-path rules do. Lines still in maintenance on 2026-10-12 (endoflife.date API, cross-checked with the 8.19 date on `elastic.co/support/eol`):

| Line | Latest patch (2026-10-12) | End of maintenance |
|---|---|---|
| **8.19** (final 8.x) | 8.19.23 | **2027-07-15** — longer than the N+2 rule gives; it is the 8.x long-support line |
| **9.4** | 9.4.8 | N+2 — when 9.6 GAs |
| **9.5** (current) | 9.5.5 | N+2 — when 9.7 GAs |

Every other minor is EOL (9.0–9.3, 8.18 and older). Re-derive the patch numbers before citing them (House Rule #8); they move monthly.

Upgrade-path rules (Elastic `deploy-manage/upgrade.md` § Upgrade paths, `upgrade/prepare-to-upgrade.md`):

- **Within 8.x, one rolling upgrade from any 8.x to a later one is allowed.** 8.8, 8.14 and 8.17 can each go straight to the latest 8.19 patch. The general rule is release *date*, not number: the target must have been released **after** the current version (e.g. 9.0.5 → 9.1.0 was not allowed because 9.1.0 shipped first).
- **To 9.x:** 9.0.x from 8.18.x only; **9.1+ from 8.19.x only**. Elastic recommends the latest 8.19 patch before the major, so the newest Upgrade Assistant runs.
- **Upgrade Assistant on 8.19 is the gate.** Indices created in **7.x or earlier** must be reindexed, deleted, or marked read-only (archived) before 9.x. The oldest cluster is the likeliest to carry them. Snapshot before reindexing.
- **Clients decouple at 8.19:** 8.19 Elastic Agent, Beats and Logstash work with every 9.x Elasticsearch, so client fleets need not move in lockstep with the major.
- **Enterprise Search has no 9.x.** Migrate App Search / Workplace Search / the web crawler off it before the major (ECK breaking-changes.md § 3.0.0).

Default recommendation for 8.8 / 8.14 / 8.17: **one rolling upgrade each to the latest 8.19 patch** — supported into mid-2027 without a major. Treat 9.x as a separate later project; it needs new image coordinates (§ 3.0.0, `ubi` suffix and agent path changes), Upgrade Assistant cleanup, and no Enterprise Search.

Sources: ECK supported-versions pages 2.16 / 3.0 / 3.1 / current (`elastic.co/guide/en/cloud-on-k8s/<ver>/k8s-supported.html`); ECK 3.0.0 release notes (#8507 6.x removal, #8559 9.0-through-8.18); endoflife.date/elasticsearch (8.17 EOL 2025-08-05, now 2025-08-12; 8.19 EOL 2027-07-15); Elastic `deploy-manage/upgrade.md` + `upgrade/prepare-to-upgrade.md` (upgrade paths, 8.19 staging, 7.x-index rule); Elastic EOL policy `elastic.co/support/eol` (two-newest-minors maintenance rule). 8.8/8.14 per-minor EOL dates are no longer enumerated by endoflife.date (rolled off as long-superseded) — status derived from the published maintenance policy + successor-minor GA dates; mark the exact 8.8/8.14 end-of-maintenance day **UNVERIFIED** (only the policy-derived "EOL well before 2026" is certain).
