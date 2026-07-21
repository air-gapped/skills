# Sources (primary / high-credibility)

Grounded 2026-06-01; release/edition rows re-grounded **2026-07-21**. The ladder/pairing/ordering *mechanics* are durable methodology; the volatile leaf
numbers — latest patch per minor, GA dates, "fixed in vX" claims, Node-Driver ranges — must be re-grounded via
`gh` at use time (House Rule #2). Distilled from the deep-research report (see Provenance).

## Freshness ledger

Per-source verification dates (run `freshen harvester-upgrade` to re-probe and re-stamp).

| Source | Last verified | Note |
|---|---|---|
| Harvester docs `upgrade/automatic.md` (lifecycle, paths, component table) | 2026-06-01 | no-skip ladder + per-minor stack + Rancher-first |
| Harvester docs `upgrade/{v1-5-x-to-v1-6-x,v1-6-x-to-v1-7-x,v1-7-x-to-v1-8-x}.md` | 2026-06-01 | per-hop breaking changes — volatile fix versions |
| Harvester docs `upgrade/troubleshooting.md` + `advanced/addons/upgrade-manager.md` | 2026-06-01 | 5-phase flow, Phase-4 "do not restart", experimental/no-air-gap manager |
| Harvester docs `rancher/{virtualization-management,harvester-ui-extension}.md` + `airgap.md` | 2026-06-01 | 3-step order, UI-ext support matrix, ui-plugin-catalog image map |
| Harvester docs `rancher/{cloud-provider,csi-driver}.md` + `vm/{live-migration,create-vm,backup-restore}.md` | 2026-06-01 | CCM/CSI standalone install, migratability, backup primitives |
| Harvester source `pkg/controller/master/upgrade/*` | 2026-06-01 | node order delegated, serial interlock, restoreVM, pause-map |
| `gh release list/api -R harvester/harvester` + `curl -I releases.rancher.com/harvester/<tag>/…iso` | 2026-07-21 | Edition reality re-confirmed (v1.8.1 and v1.7.2 ISOs both HTTP 200 → patches remain community). Latest GA per line: **v1.8.1** (2026-06-29), **v1.7.2** (2026-07-07). **Still no 1.9.0 GA** — v1.9.0-rc1/rc2 only (2026-07-08 / 07-15). ⚠ **`releases/latest` currently resolves to v1.7.2, a *lower* minor than v1.8.1**, because Harvester patches several minors in parallel and GitHub ranks by date. |
| harvester/upgrade-helpers `pre-check/v1.x/check.sh` | 2026-06-01 | the enforced pre-flight gate thresholds |
| KubeVirt live-migration (user-guide + `types.go`/`virt-config.go` v1.4.0) + harvester#9144/#10482/#10698/#4375 | 2026-06-01 | busy-etcd non-convergence; real v1.4 migration defaults; bandwidth-0 self-throttle; no-circuit-breaker |
| Harvester upgrade drain + gating (`upgrade_controller.go`, `job_controller.go`, `virtualmachineinstance.go`, `upgrade_node.sh` @ v1.5.0/1.6.0/1.7.0) | 2026-06-02 | drain is eviction-based + honors PDBs; detector force-stops NodeSelector-pinned VMs pre-eviction; `restoreVM` is 1.6+ (auto-restart job, not a gate); pause-map is 1.7.0+; no guest-etcd gate; PDB+VMI-readinessProbe native gate |
| `compat/harvester.md` + `compat/rancher.md` (k8s-components-checker) | 2026-06-01 | pairing, Node-Driver ranges, Rancher mgmt-k8s windows (NB: edition claim there is wrong — §Editions) |

## The ladder, editions, lifecycle
- Harvester docs `upgrade/automatic.md` — lifecycle (4-month minor / 2-month patch cadence), the supported
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
  per-node state machine; pause-map annotation; `upgrade_controller.go:601-608` = drain `Enabled/Force/
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
  `vm/live-migration.md` (migratability rules, timeouts), `vm/create-vm.md` (VM Scheduling / anti-affinity, VLAN
  auto-affinity), `vm/backup-restore.md` (VM Backup vs Snapshot; virt-freezer fsfreeze), `host/host.md`
  (maintenance-mode strategy), `advanced/addons/virtual-machine-auto-balance.md`.
- harvester-csi-driver repo (`README`, `deploy/generate_addon_csi.sh`, `deploy/manifests/deployment.yaml`);
  cloud-provider-harvester `deploy/generate_addon.sh`; harvester/upgrade-helpers `pre-check/v1.x/check.sh`.

### Live migration of busy etcd / control-plane VMs (the §5 correction)
- KubeVirt user-guide Live Migration (kubevirt.io/user-guide/compute/live_migration/) + Migration Policies +
  Node maintenance/eviction; KubeVirt `staging/.../v1/types.go` + `pkg/virt-config/virt-config.go` @ v1.4.0 (real
  defaults: auto-converge off, post-copy off, `bandwidthPerMigration: 0`, completion/progress timeout 150;
  evictionStrategy semantics).
- kubevirt#3504 (busy-VM dirty-rate non-convergence, canonical repro), kubevirt#15924 (post-copy crashes VM, no
  recovery — OPEN), kubevirt#15373 (1.6.0 upgrade left RKE2 control-plane VMs double-running/corrupt).
- Harvester: chart `dependency_charts/kubevirt/values.yaml` (migrations block commented out in v1.5/v1.6),
  `pkg/settings/settings.go` + `pkg/controller/master/setting/kubevirt_migration.go` (the `kubevirt-migration`
  Setting, 1.7.0+ only, reconciles/overwrites direct CR edits), `package/upgrade/upgrade_node.sh`
  (`wait_vms_out_or_shutdown` — infinite wait on 1.5.x), `docs/advanced/{vm-migration-network,settings}.md`,
  `docs/networking/clusternetwork.md` (mgmt bond active-backup), `docs/host/host.md` (`maintain-mode-strategy`).
- harvester#9144 (real v1.5.x migration-config support-bundle dump), #10482 (bandwidth-0 self-throttle analysis),
  #4375 (auto-converge motivation), #5756/#8731/#10349 (pre-drain stuck "Waiting for VM live-migration"),
  #10698 (evacuation loop has no retry limit — maintainer-confirmed 2026-06-01), #10425 (concurrent live
  migration — open). OpenShift Virtualization "Live migration" docs + etcd.io tuning/maintenance (quorum,
  heartbeat/election, defrag).

## Landmines / pre-flight / rollback
- Harvester docs `upgrade/{automatic,troubleshooting,v1-5-x-to-v1-6-x,v1-6-x-to-v1-7-x,v1-7-x-to-v1-8-x}.md` +
  `release-notes/v1.5.0–v1.8.0.md` (per-hop known issues), `upgrade-helpers/pre-check/v1.x/check.sh` (enforced
  gates), `vm/backup-restore.md` (DR primitives).
- GitHub issues (re-check status via `gh`): #10099, #10188, #10425, #10447, #10471, #10513, #10532, #2316,
  #2323, #6418, #6849, #7366, #7650, #8949, #8950, #9033, #9260, #9367, #9644, #9738, #9815, #9845, #10349.

## Full research provenance
- The deep-research report this skill was distilled from:
  `~/.claude/skills/autoresearch/results/harvester-upgrade-eol-1.5-to-latest-2026-06-01.md` (autoresearch
  Research mode, 6 parallel agents + a verification recurse that pinned the edition correction and the
  controlled-flow source-level facts).
</content>
