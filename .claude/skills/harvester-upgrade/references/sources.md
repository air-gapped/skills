# Sources (primary / high-credibility)

Freshened: 2026-09-22 — every row probed. v1.9.0 GA'd 2026-09-16, ending the RC-only state this file recorded — but its own release notes warn against upgrading (QEMU-10/libvirt regression force-shuts-down VMs, harvester#11356 and #11615 both still open, fix planned for v1.9.1), so the ladder still tops out at 1.8.2 in practice.

Grounded 2026-06-01; release/edition rows re-grounded **2026-07-21**. The ladder/pairing/ordering *mechanics* are durable methodology; the volatile leaf
numbers — latest patch per minor, GA dates, "fixed in vX" claims, Node-Driver ranges — must be re-grounded via
`gh` at use time (House Rule #2). Distilled from a deep-research pass (see Provenance).

## Freshness ledger

Per-source verification dates (run `freshen harvester-upgrade` to re-probe and re-stamp).

| Source | Last verified | Note |
|---|---|---|
| Harvester docs `upgrade/index.md` (lifecycle, paths, component table) | 2026-09-15 — **five doc pages were merged into their section index pages and the old slugs now 404**: `upgrade/automatic`, `vm/create-vm`, `host/host`, `networking/clusternetwork`, `advanced/settings`. Each is repointed here. `host/` resolves only as the bare path — `host/index/` 404s too. | no-skip ladder + per-minor stack + Rancher-first |
| Harvester docs `upgrade/{v1-5-x-to-v1-6-x,v1-6-x-to-v1-7-x,v1-7-x-to-v1-8-x}.md` | 2026-09-15 | per-hop breaking changes — volatile fix versions |
| Harvester docs `upgrade/troubleshooting.md` + `advanced/addons/upgrade-manager.md` | 2026-09-15 | 5-phase flow, Phase-4 "do not restart", experimental/no-air-gap manager |
| Harvester docs `rancher/{virtualization-management,harvester-ui-extension}.md` + `airgap.md` | 2026-10-27 — `airgap.md` image map moved upstream: 1.8.x → 4.30.0 (bae9b9e08c, 2026-07-06), 1.7.x → 4.32.0 (9db0105a09, 2026-07-16); the 1.9.x rows (Rancher 2.15.0+, image 4.45.0) exist only in the v1.10 dev docs (07866ddfb3) | 3-step order, UI-ext support matrix, ui-plugin-catalog image map |
| Harvester docs `rancher/{cloud-provider,csi-driver}.md` + `vm/{live-migration,create-vm,backup-restore}.md` | 2026-09-15 | CCM/CSI standalone install, migratability, backup primitives |
| Harvester source `pkg/controller/master/upgrade/*` | 2026-09-15 | node order delegated, serial interlock, restoreVM, pause-map |
| `gh release list/api -R harvester/harvester` + `curl -I releases.rancher.com/harvester/<tag>/…iso` + v1.9.0 release notes (Upgrade warning, Component Versions, Known Issues) + docs `upgrade/v1-8-x-to-v1-9-x` | 2026-10-27 | Latest GA per line: **v1.9.0** (2026-09-16, `isLatest`; notes say do not upgrade — #11356/#11615 open, fixes slated for v1.9.1, which is at rc4 2026-10-21), **v1.8.2** (2026-08-06), **v1.7.3** (2026-08-07), v1.6.1 (2025-10-16). ISOs for all four → HTTP 200 (patches stay community). A `prime-v1.9.1-rc4` tag appeared beside `v1.9.1-rc4` — first `prime-` tag in the repo. `releases/latest` resolved to v1.7.3 from 2026-08-07 until v1.9.0 shipped. 1.9.0 stack: RKE2 v1.36.3, KubeVirt v1.8.4, Longhorn v1.12.1, SL Micro 6.2, embedded Rancher v2.15.0. #11543 (stuck Images preloaded) open, milestone v1.11.0. |
| Security advisories — `gh api repos/harvester/harvester/security-advisories` + `gh api advisories/<GHSA>` | 2026-10-27 — two published, none new since 2026-09-15. GHSA-pgh9-mpwc-8jjf (CVE-2025-71261): repo entry `< 1.8` patched **1.8.0** plus `<= 1.7.1`/`<= 1.6.1`/`<= 1.5.2` with no patch; global DB `< 1.8.0` → 1.8.0; text "Patched versions … include releases v1.8.0 or newer", workaround restrict `cluster-registration-url`. The 2026-09-15 reading "first_patched_version null on both" was wrong for this one. GHSA-6g8q-hp2j-gvwv (CVE-2025-62877, harvester-installer): no patched version. | patch floors on the ladder |
| SUSE per-line support matrix `suse.com/suse-harvester/support-matrix/all-supported-versions/harvester-v1-{6,7,8,9}-x/` | 2026-10-27 (bare curl, HTTP 200) — Node Driver RKE2: 1.6 = 1.31–1.33, 1.7 = 1.32–1.34, 1.8 = 1.33–1.35 (≤1.35.3 known issue #10188), 1.9 = 1.34–1.36; 1.9 CCM v0.2.15 / CSI ≥ v0.1.31 with RKE2 ≥ v1.36.4/v1.35.8/v1.34.11; UI-ext → ui-plugin-catalog: 1.7.0–1.7.3 and 1.8.0–1.8.2 → 4.34.0, 1.9.0 → 4.45.0 (Rancher 2.15.0+). `compat/harvester.md` still lists 1.6 = 1.30–1.33 and 1.7 = 1.31–1.34. | guest Node-Driver ranges, ui-plugin-catalog image map |
| harvester/upgrade-helpers `pre-check/v1.x/check.sh` + `pkg/webhook/resources/upgrade/validator.go` @ v1.8.2/v1.9.0 | 2026-10-27 — webhook: `defaultNewImageSize` 13 GiB, `defaultImageGCHighThresholdPercent` 85, `defaultMinCertsExpirationInDay` 7; no 30 GiB check anywhere in source (the figure is docs `upgrade/automatic.md` only). check.sh: projected-usage 85% test, cert warning at 10 days (`-checkend 864000`); new `check_vmi_cpu_topology` (485e51fd, 2026-09-17) | the enforced pre-flight gate thresholds |
| KubeVirt live-migration (user-guide + `types.go`/`virt-config.go` v1.4.0) + harvester#9144/#10482/#10698/#4375 | 2026-09-15 | busy-etcd non-convergence; real v1.4 migration defaults; bandwidth-0 self-throttle; no-circuit-breaker |
| Harvester upgrade drain + gating (`upgrade_controller.go`, `job_controller.go`, `virtualmachineinstance.go`, `upgrade_node.sh` @ v1.5.0/1.6.0/1.7.0) | 2026-09-15 | drain is eviction-based + honors PDBs; detector force-stops NodeSelector-pinned VMs pre-eviction; `restoreVM` is 1.6+ (auto-restart job, not a gate); pause-map is 1.7.0+; no guest-etcd gate; PDB+VMI-readinessProbe native gate |
| `compat/harvester.md` + `compat/rancher.md` (k8s-components-checker) | 2026-09-15 | pairing, Node-Driver ranges, Rancher mgmt-k8s windows (**the edition caveat that used to sit here is retired** — `compat/harvester.md` has since corrected its own edition claim and now agrees with this skill; historical note: it previously said the edition claim there is wrong — §Editions) |

## The ladder, editions, lifecycle
- Harvester docs `upgrade/index.md` — lifecycle (4-month minor / 2-month patch cadence), the supported
  upgrade-paths table (1.5.x→1.6.x→1.7.x→1.8.x, no skip), the per-minor component table, the k8s version-skew
  note, "Harvester does not support downgrades", free-space/cert gates, VM-handling + restoreVM, customize/pause
  node upgrade (v1.7.0+), air-gapped `version.yaml` registration.
- `gh release list/api -R harvester/harvester` (tag enumeration, GA dates, prerelease flags) +
  `curl -I releases.rancher.com/harvester/<tag>/harvester-<tag>-amd64.iso` (public patch ISOs, HTTP 200) +
  local `release-notes/v1.5.0–v1.8.0.md` — the edition correction (patches are community; "Prime" = paid
  support on the same bits; the lone Community↔Prime cross-upgrade bug v1.5.0).

## External Rancher coupling
- Harvester docs `rancher/virtualization-management.md` (the Rancher→UI-ext→Harvester upgrade order),
  `rancher/harvester-ui-extension.md` (the UI-ext↔Harvester↔Rancher support matrix), `airgap.md` (air-gapped
  ui-plugin-catalog image map + secret in `cattle-ui-plugin-system`).
- Companion: `rancher-upgrade` skill (the external Rancher's own 2.11→2.14 chain — KDM, cert-manager/Helm
  floors, CAPI→Turtles, the 2.14 one-way boundary) and `k8s-components-checker/references/compat/rancher.md`
  (mgmt-cluster k8s windows per Rancher minor).

## Controlled flow / upgrade controller
- Harvester source `pkg/controller/master/upgrade/{upgrade_controller,secret_controller,job_controller,
  node_controller,common}.go` (node order delegated to RKE2 with concurrency=1; one-at-a-time interlock;
  per-node state machine; pause-map annotation; `upgrade_controller.go` `*DrainOptions` block (`rke2DrainNodes = true`; lines 619-624 @ v1.5.2, 580-585 @ v1.6.1, 742-749 @ v1.8.2/v1.9.0 — find by symbol) = drain `Enabled/Force/
  IgnoreDaemonSets/DeleteEmptyDirData`, **no `disableEviction` → eviction-based, PDBs honored**;
  `job_controller.go sendRestoreVMJob`+`util.IsRestoreVM` = `restoreVM` is a post-host restart job, **not** a
  gate), `pkg/util/virtualmachineinstance/virtualmachineinstance.go GetAllNonLiveMigratableVMINames` (NodeSelector
  / HostDevices / node-affinity / CD-ROM → force-stopped pre-eviction, bypassing PDB),
  `pkg/upgradehelper/vmlivemigratedetector/detector.go` (only stops non-migratable; leaves migratable for the
  drain), `package/upgrade/upgrade_node.sh` (`command_pre_drain`→`wait_longhorn_engines`+`wait_vms_out_or_shutdown`;
  `--upgrade`/`restoreVM` absent on v1.5, present v1.6+; `wait_evacuation_pdb_gone`; no guest/etcd reference at all),
  `pkg/settings/settings_helper.go` (UpgradeConfig / nodeUpgradeOption — pause-map present v1.7.0+ only, 0 in
  v1.5/v1.6), `pkg/webhook/resources/upgrade/{mutator,validator}.go` (manual-mode→pause-map; degraded-volume gate).
- KubeVirt VMI `readinessProbe` (sets virt-launcher pod readiness via readiness gate → counted by PodDisruptionBudget);
  KubeVirt eviction / `kubevirt.io/drain` taint evacuation + per-VMI evacuation PDBs.
- Harvester docs `upgrade/troubleshooting.md` (5-phase flow + Phase-4 "do not restart"),
  `advanced/addons/upgrade-manager.md` (experimental, air-gap-unsupported, mutually exclusive).

## Guest RKE2 survivability
- Harvester docs `rancher/cloud-provider.md`, `rancher/csi-driver.md` (standalone CCM/CSI install + cloud-config
  token via `generate_addon.sh` / `generate_addon_csi.sh`; macvlan requirement; Node-Driver ranges),
  `vm/live-migration.md` (migratability rules, timeouts), `vm/index.md` (VM Scheduling / anti-affinity, VLAN
  auto-affinity), `vm/backup-restore.md` (VM Backup vs Snapshot; virt-freezer fsfreeze), `host/ (bare path)`
  (maintenance-mode strategy), `advanced/addons/virtual-machine-auto-balance.md`.
- harvester-csi-driver repo (`README`, `deploy/generate_addon_csi.sh`, `deploy/manifests/deployment.yaml`);
  cloud-provider-harvester `deploy/generate_addon.sh`; harvester/upgrade-helpers `pre-check/v1.x/check.sh`.

### Live migration of busy etcd / control-plane VMs (the §5 correction)
- KubeVirt user-guide Live Migration (kubevirt.io/user-guide/compute/live_migration/) + Migration Policies +
  Node maintenance/eviction; KubeVirt `staging/.../v1/types.go` + `pkg/virt-config/virt-config.go` @ v1.4.0 (real
  defaults: auto-converge off, post-copy off, `bandwidthPerMigration: 0`, completion/progress timeout 150;
  evictionStrategy semantics).
- kubevirt#3504 (busy-VM dirty-rate non-convergence, canonical repro), kubevirt#15924 (post-copy crashes VM, no — shows closed 2026-07-19, but kubevirt-bot rotted it closed with no fix, so the constraint stands;
  recovery — OPEN), kubevirt#15373 (1.6.0 upgrade left RKE2 control-plane VMs double-running/corrupt).
- Harvester: chart `deploy/charts/harvester/dependency_charts/kubevirt/values.yaml` (migrations block commented out in v1.5/v1.6; the root-level `dependency_charts/…` path cited before 2026-08-18 never existed),
  `pkg/settings/settings.go` + `pkg/controller/master/setting/kubevirt_migration.go` (the `kubevirt-migration`
  Setting, 1.7.0+ only, reconciles/overwrites direct CR edits), `package/upgrade/upgrade_node.sh`
  (`wait_vms_out_or_shutdown` — infinite wait on 1.5.x), `docs/advanced/{vm-migration-network,settings}.md`,
  `docs/networking/index.md` (mgmt bond active-backup), `docs/host/ (bare path)` (`maintain-mode-strategy`).
- harvester#9144 (real v1.5.x migration-config support-bundle dump), #10482 (bandwidth-0 self-throttle analysis),
  #4375 (auto-converge motivation), #5756/#8731/#10349 (pre-drain stuck "Waiting for VM live-migration"),
  #10698 (evacuation loop has no retry limit — maintainer-confirmed 2026-06-01), #10425 (**FIXED** — closed COMPLETED 2026-07-20 by `albinsun`, QA signed off against v1.9.0-rc2 via harvester-ui-extension PR #863. **The trailing "concurrent live migration — open" clause was removed 2026-09-15: it contradicted the same row's own FIXED verdict, and no second open issue exists — a search for "concurrent live migration" returns exactly one hit, #10425 itself.** Historically the row also said; concurrent live
  migration — open). OpenShift Virtualization "Live migration" docs + etcd.io tuning/maintenance (quorum,
  heartbeat/election, defrag).

## Landmines / pre-flight / rollback
- Harvester docs `upgrade/{automatic,troubleshooting,v1-5-x-to-v1-6-x,v1-6-x-to-v1-7-x,v1-7-x-to-v1-8-x}.md` +
  `release-notes/v1.5.0–v1.8.0.md` (per-hop known issues), `upgrade-helpers/pre-check/v1.x/check.sh` (enforced
  gates), `vm/backup-restore.md` (DR primitives).
- GitHub issues (re-check status via `gh`): #10099, #10188, #10425, #10447, #10471, #10513, #10532 (fixed by PR #10543, backported to v1.8.1 via #10537 — QA verified v1.7.1 → v1.8.1-dev), #2316,
  #2323, #6418, #6849, #7366, #7650, #8949, #8950, #9033, #9260, #9367, #9644, #9738, #9815, #9845, #10349.

## Full research provenance
- Distilled from a 2026-06-01 multi-agent deep-research pass (6 parallel agents + a verification recurse that
  pinned the edition correction and the controlled-flow source-level facts). The report itself is not shipped
  (autoresearch `results/` is untracked); every claim it fed is cited to a primary source in the rows above.
</content>
