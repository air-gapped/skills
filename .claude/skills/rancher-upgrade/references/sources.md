# sources.md — canonical sources + staleness index

Per-source provenance for every version/matrix claim in this skill. `freshen` reads and re-stamps
the **Last verified** column; at use time, treat any row older than ~90 days as suspect and
re-ground per House Rule #8 (`lifecycle.md` § Grounding). All rows below were `gh`/doc-grounded in
one pass when the skill was authored.

Community editions only — Prime-branded sources are tagged and used only to corroborate, never as
the primary for a community claim.

| Source | URL | Last verified | Tier |
|--------|-----|---------------|------|
| Rancher releases + issues (versions, EOL, breaking changes, issue numbers) | https://github.com/rancher/rancher/releases | 2026-05-30 | community |
| Kontainer Driver Metadata — live downstream channel windows | https://releases.rancher.com/kontainer-driver-metadata/release-v2.14/data.json | 2026-05-30 | community |
| KDM repo (branches `release-v2.X`, `data/data.json`) | https://github.com/rancher/kontainer-driver-metadata | 2026-05-30 | community |
| rancher/charts — Fleet / Turtles / provisioning-capi / rancher-backup chart versions per `release-v2.X` | https://github.com/rancher/charts | 2026-05-30 | community |
| Rancher Turtles releases (CAPI contract, v0.25/v0.26 timeline) | https://github.com/rancher/turtles/releases | 2026-05-30 | community |
| Fleet releases (per-minor app version, Helm v4 at 0.15) | https://github.com/rancher/fleet/releases | 2026-05-30 | community |
| backup-restore-operator releases + restore-quirk issues (#844 open, #916 closed) | https://github.com/rancher/backup-restore-operator | 2026-05-30 | community |
| CAPRKE2 `v1alpha1` deprecation (#797) | https://github.com/rancher/cluster-api-provider-rke2 | 2026-05-30 | community |
| Community Helm chart index (current stable minor) | https://releases.rancher.com/server-charts/latest/index.yaml | 2026-05-30 | community |
| Rancher Manager docs — upgrades, air-gapped-upgrades, publish-images, helm-chart-options, tls-settings, rollbacks, update-k8s-without-upgrading-rancher | https://ranchermanager.docs.rancher.com | 2026-05-30 | community |
| RKE2 docs — air-gap, etcd backup/restore, automated SUC upgrades | https://docs.rke2.io | 2026-05-30 | community |
| Rancher EOL dates (cross-check) | https://endoflife.date/rancher | 2026-05-30 | community |
| SUSE lifecycle / support matrix (corroborates EOL + downstream window) | https://www.suse.com/lifecycle | 2026-05-30 | Prime (corroboration only) |
| Companion: mgmt-cluster k8s window (single source of truth — cited, not restated) | k8s-components-checker/references/compat/rancher.md | 2026-05-30 | community/local |
