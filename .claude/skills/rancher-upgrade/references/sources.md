# sources.md — canonical sources + staleness index

Freshened: 2026-09-22 — every row probed; all 15 URLs 200 and every advisory floor and community-ceiling figure matches live release tags. Two moved: Rancher 2.15's EOL is now published (2028-02-27), and Turtles is at v0.26.6 / v0.27.2 with v0.27 no longer tracking an unreleased 2.15.

Per-source provenance for every version/matrix claim in this skill. `freshen` reads and re-stamps
the **Last verified** column; at use time, treat any row older than ~90 days as suspect and
re-ground per House Rule #3 (`lifecycle.md` § Grounding). All rows below were `gh`/doc-grounded in
one pass when the skill was authored.

Community editions only — Prime-branded sources are tagged and used only to corroborate, never as
the primary for a community claim.

| Source | URL | Last verified | Tier |
|--------|-----|---------------|------|
| Rancher releases + issues (versions, EOL, breaking changes, issue numbers) | https://github.com/rancher/rancher/releases | 2026-09-15 | community |
| Rancher per-release assets — `rancher-data.json` (KDM bundle), `rancher-mirror-to-rancher-org.sh` (exact shipped image tags) | https://github.com/rancher/rancher/releases/tag/v2.14.3 | 2026-09-15 | community |
| Kontainer Driver Metadata — live downstream channel windows (`release-v2.14` **and** `release-v2.15`) | https://releases.rancher.com/kontainer-driver-metadata/release-v2.14/data.json | 2026-09-15 | community |
| KDM repo (branches `release-v2.X`, `data/data.json`) | https://github.com/rancher/kontainer-driver-metadata | 2026-09-15 | community |
| rancher/charts — Fleet / Turtles / provisioning-capi / rancher-backup chart versions per `release-v2.X` | https://github.com/rancher/charts | 2026-07-25 *(branch list only; `assets/` not re-read)* | community |
| Rancher Turtles releases (CAPI contract, v0.25/v0.26/v0.27 timeline) | https://github.com/rancher/turtles/releases | 2026-09-15 | community |
| Fleet releases (per-minor app version, Helm v4 at 0.15) | https://github.com/rancher/fleet/releases | 2026-09-15 | community |
| backup-restore-operator releases + restore-quirk issues (#844 open, #916 closed-with-workaround) | https://github.com/rancher/backup-restore-operator | 2026-09-15 | community |
| CAPRKE2 `v1alpha1` deprecation (#797) | https://github.com/rancher/cluster-api-provider-rke2 | 2026-09-15 | community |
| Community Helm chart index — **decisive test for the per-minor community ceiling** (`latest` + `stable`) | https://releases.rancher.com/server-charts/latest/index.yaml | 2026-09-15 | community |
| Rancher Manager docs — upgrades, air-gapped-upgrades, publish-images, helm-chart-options, tls-settings, rollbacks, update-k8s-without-upgrading-rancher | https://ranchermanager.docs.rancher.com | 2026-07-25 *(rollbacks page only)* | community |
| RKE2 docs — air-gap, etcd backup/restore, automated SUC upgrades | https://docs.rke2.io | 2026-09-15 | community |
| Rancher EOL dates (cross-check) | https://endoflife.date/rancher | 2026-09-15 | community |
| SUSE lifecycle / support matrix (corroborates EOL + downstream window) | https://www.suse.com/lifecycle | 2026-09-15 | Prime (corroboration only) |
| Companion: mgmt-cluster k8s window (single source of truth — cited, not restated) | k8s-components-checker/references/compat/rancher.md | 2026-09-15 | community/local |

## Freshen history — observed state

**Where the narrative lives:** the per-pass findings write-up (what was probed, what changed, what
was deliberately not changed, and the lessons) is in `improvement-backlog.md`. This file stays a
provenance index: the table above is the authoritative per-source staleness record, and the digest
below is the minimum an operator needs before citing anything.

### 2026-07-25 (latest)

Grounded per the § Grounding protocol (enumerate-and-derive, no candidate named in any query).

- **2026-09-15: v2.15 HAS SHIPPED — this file said "still RC, do NOT plan onto it" while `SKILL.md` already carried the correct v2.15.1 ceiling.** An internal contradiction inside one skill, and the sources file was the wrong half. v2.15.0 (2026-07-30) and **v2.15.1 (2026-08-28)** both self-declare "This is a Community version release", and v2.15.1 is `isLatest`. Nuance that matters for the ceiling: the community chart index at `releases.rancher.com/server-charts/latest` carries **2.15.1 but not 2.15.0** — 2.15.0 appears there only as rc1–rc5. So the reachable community ceiling is **2.15.1**, and the chart index, not the GitHub release list, is what settles it.
- Three further monthly patch cycles landed (07-30, 08-26, 08-28) across every active minor; `releases/latest` is **v2.15.1**, not v2.14.3. Historically, stable patch state was 2.11.15 / 2.12.11 / 2.13.7 / **2.14.3**, all 2026-06-29.
- **EOL moved:** endoflife.date now reports 2.10 as **actually EOL** (passed 2026-06-19), and 2.11's EOL falls **2026-10-24 — next month**. Re-check any EOL claim dated to the 2026-07-25 pass.
- `release-v2.16` branches now exist in rancher/charts while KDM has none yet — charts runs ahead of KDM, so a branch in one is not evidence of a release in the other.
- **KDM 2.15 window: 1.34 / 1.35 / 1.36**, k8s **1.33 drops out** — `kdm-downstream-matrix.md`.
- **The community-vs-Prime `head -1` classifier was broken** (matched 0 of 4 probed releases) and has
  been replaced — `lifecycle.md` § Community vs Prime.
- **BRO #916 closed with a workaround, not a fix** — `prereqs-and-ordering.md` § Backup & rollback.
- **Not re-probed** (still stamped 2026-07-21): docs.rke2.io, SUSE lifecycle, companion
  `compat/rancher.md`, per-minor breaking-change lists.

**Correction applied later the same day — community ceilings, not top tags.** An agent using the
skill hit the trap the edition rule exists to prevent: `sort -V | tail -1` returns a **Prime-only**
patch for every non-current minor, so the ladder targets recorded above as "latest patch per minor"
(2.11.15 / 2.12.11 / 2.13.7) were not installable by this skill's own audience. Real community
ceilings, confirmed by **two independent sources** — the release-notes edition markers (Prime uses
*two* forms: a self-declaration line and a docs-redirect stub) and the community Helm chart index at
`releases.rancher.com/server-charts/{latest,stable}/index.yaml`, which is decisive because it is what
`helm upgrade` pulls:

| Minor | Newest tag | Community ceiling | Released |
|---|---|---|---|
| 2.11 | v2.11.15 | **v2.11.3** | 2025-06-25 |
| 2.12 | v2.12.11 | **v2.12.3** | 2025-10-22 |
| 2.13 | v2.13.7 | **v2.13.3** | 2026-02-25 |
| 2.14 | v2.14.3 | **v2.14.3** | 2026-09-15 |

Corroborated by the skill's own field reports (validated hops 2.12.3→2.13.3 and 2.13.3→2.14.2).
`k8s-components-checker` § Edition discrimination owns the protocol and is now cited from
`lifecycle.md` § Grounding. **2.15 re-checked 2026-09-15: no longer RC — v2.15.1 is the current community release and `releases/latest`.**

### 2026-07-21

Superseded by the above on two points and retained only as a caution, both written up in
`lifecycle.md` § Grounding: v2.15 was recorded as *alpha* (it reached RC the same day), and
Fleet/Turtles/BRO were recorded as having *no recent stable tag* (Fleet and Turtles both cut stable
tags 2026-07-21–22). **The `isPrerelease`-lies-on-`rancher/turtles` trap from that pass is still
live and re-confirmed 2026-07-25.** Full prior text: `git log -p references/sources.md`.
