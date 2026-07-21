# sources.md — canonical sources + staleness index

Per-source provenance for every version/matrix claim in this skill. `freshen` reads and re-stamps
the **Last verified** column; at use time, treat any row older than ~90 days as suspect and
re-ground per House Rule #8 (`lifecycle.md` § Grounding). All rows below were `gh`/doc-grounded in
one pass when the skill was authored.

Community editions only — Prime-branded sources are tagged and used only to corroborate, never as
the primary for a community claim.

| Source | URL | Last verified | Tier |
|--------|-----|---------------|------|
| Rancher releases + issues (versions, EOL, breaking changes, issue numbers) | https://github.com/rancher/rancher/releases | 2026-07-21 | community |
| Kontainer Driver Metadata — live downstream channel windows | https://releases.rancher.com/kontainer-driver-metadata/release-v2.14/data.json | 2026-07-21 | community |
| KDM repo (branches `release-v2.X`, `data/data.json`) | https://github.com/rancher/kontainer-driver-metadata | 2026-07-21 | community |
| rancher/charts — Fleet / Turtles / provisioning-capi / rancher-backup chart versions per `release-v2.X` | https://github.com/rancher/charts | 2026-07-21 | community |
| Rancher Turtles releases (CAPI contract, v0.25/v0.26 timeline) | https://github.com/rancher/turtles/releases | 2026-07-21 | community |
| Fleet releases (per-minor app version, Helm v4 at 0.15) | https://github.com/rancher/fleet/releases | 2026-07-21 | community |
| backup-restore-operator releases + restore-quirk issues (#844 open, #916 closed) | https://github.com/rancher/backup-restore-operator | 2026-07-21 | community |
| CAPRKE2 `v1alpha1` deprecation (#797) | https://github.com/rancher/cluster-api-provider-rke2 | 2026-07-21 | community |
| Community Helm chart index (current stable minor) | https://releases.rancher.com/server-charts/latest/index.yaml | 2026-07-21 | community |
| Rancher Manager docs — upgrades, air-gapped-upgrades, publish-images, helm-chart-options, tls-settings, rollbacks, update-k8s-without-upgrading-rancher | https://ranchermanager.docs.rancher.com | 2026-07-21 | community |
| RKE2 docs — air-gap, etcd backup/restore, automated SUC upgrades | https://docs.rke2.io | 2026-07-21 | community |
| Rancher EOL dates (cross-check) | https://endoflife.date/rancher | 2026-07-21 | community |
| SUSE lifecycle / support matrix (corroborates EOL + downstream window) | https://www.suse.com/lifecycle | 2026-07-21 | Prime (corroboration only) |
| Companion: mgmt-cluster k8s window (single source of truth — cited, not restated) | k8s-components-checker/references/compat/rancher.md | 2026-07-21 | community/local |

## 2026-07-21 freshen — observed state

Grounded per the § Grounding protocol (enumerate-and-derive, no candidate named
in any query).

**Rancher server — four active minor lines, all patched the same day
(2026-06-29):**

| Line | Latest stable | EOL (endoflife.date cross-check) |
|---|---|---|
| **2.14** | **v2.14.3** | 2027-10-10 |
| 2.13 | v2.13.7 | 2027-06-17 |
| 2.12 | v2.12.11 | 2027-02-28 |
| **2.11** | v2.11.15 | **2026-10-24 — ~3 months out** |
| 2.10 | v2.10.12 | 2026-06-19 — **already EOL** |

`releases/latest` reports **v2.14.3**, which is genuinely also the highest
stable minor here — no recency-vs-rank conflict this pass, but it was checked
rather than assumed.

**In flight (all `isPrerelease=true`):** alphas for v2.14.4, v2.13.8, v2.12.11→12,
v2.11.16, and **v2.15.0-alpha21** — v2.15 is in *alpha*, not RC. Do not plan
against it.

**Two grounding traps observed and written into `lifecycle.md` § Grounding:**

1. **`isPrerelease` lies on `rancher/turtles`** — `v0.25.6-rc.1` and
   `v0.26.4-rc.2` are both flagged `isPrerelease=false`. Filtering on the flag
   alone reports an RC as stable. Match the tag string as well.
2. **Component repos have no recent stable tag to find.** The top of the
   release list for `rancher/fleet`, `rancher/backup-restore-operator` and
   `rancher/turtles` is entirely RCs. Component→minor binding must come from
   the `rancher/charts` `release-v2.X` branch, not the component repo.

**Also probed:** `rancher/cluster-api-provider-rke2` latest stable **v0.25.0**
(2026-05-28).

**Deliberately not restated:** specific per-minor chart/component versions. The
skill's own House Rule #8 names these as the #1 fabrication risk and requires
grounding at use time; recording a snapshot here would create exactly the stale
authority it warns against. The *method* is what this file pins.
