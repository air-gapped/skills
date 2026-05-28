# Ceph (storage) — compat (sifted from release_notes)

- **Primary source:** https://docs.ceph.com/en/latest/releases/
- **Secondary sources:** per-release notes pages (https://docs.ceph.com/en/latest/releases/{tentacle,squid,reef}/); cross-reference `compat/rook.md` for the Rook↔Ceph pairing matrix (authoritative for k8s axis).
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 18.2
- **Last sifted:** 2026-05-28

**k8s axis collapses through Rook.** Ceph itself has no k8s version dependency
— it is daemon software. The operator-axis is `Rook minor → Ceph minor` and
lives in `compat/rook.md`. This file captures Ceph-cluster-internal signal:
upgrade-ordering between daemon types, OSD encoding gates, RGW/RBD/CephFS
protocol changes, removed modules, and EOL. For "can I run Ceph X on k8s Y",
read `compat/rook.md`.

Three lines active as of 2026-05-28: Tentacle (20.x — current), Squid (19.2.x
— stable), Reef (18.2.x — final point release shipped, EOL'd at 18.2.8).

## 20.2.1 / Tentacle (GA 2025-11-18, latest 20.2.1 2026-04-06)

- **k8s floor:** N/A — see `compat/rook.md`. Tentacle requires Rook ≥ the
  minor that lists Tentacle in its supported-Ceph table.
- **Breaking:**
  - Upgrade is gated: must run `ceph osd require-osd-release tentacle` to
    finalize. **One-way** — pre-Tentacle OSDs are rejected after the flag is
    set. No downgrade path past this point.
  - `mgr/restful` and `mgr/zabbix` modules deleted (deprecated since 2020).
    Any dashboard / alerting wired through `/restful` breaks; move to the
    built-in dashboard or Prometheus exporter.
  - Default EC plugin for *new* pools flipped Jerasure → ISA-L. Existing
    pools unchanged.
  - CephFS subvolume pool namespace format changed
    `fsvolumens__<name>` → `fsvolumens__<group>_<name>`. Tooling that grepped
    the old form (backup scripts, audit) breaks.
  - RBD `rbd device map` now defaults to **msgr2**. Legacy clients still on
    msgr1 must pass `-o ms_mode=legacy` or fail to map.
  - RGW `LastModified` timestamps now truncated to whole seconds — observable
    timestamp can move *backwards* during/after the upgrade. S3 API still
    compatible but consumers that diff `LastModified` may flap.
  - Systemd unit names include cluster FSID (already true on Reef-onward
    clusters; matters for non-Rook deployments only — Rook talks to daemons
    by Pod, not by unit).
- **CRD migrations:** N/A — Ceph CRs are Rook's surface area, not Ceph's.
- **Upgrade ordering (intra-cluster):** strict — **mon → mgr → osd → mds (if
  CephFS) → rgw**, then `ceph osd require-osd-release tentacle`. Mons must be
  on Tentacle (verify `min_mon_release == 20`) **before** OSDs upgrade. Rook
  reconciles in this order automatically; the operator only needs to avoid
  parallel CephCluster patches mid-upgrade. Pre-upgrade requires zero
  `down`/`recovering`/`undersized` PGs — disable the autoscaler temporarily
  if it's churning.
- **Deprecations:**
  - Tenant-level IAM (`CreateRole`, `PutRolePolicy`, `PutUserPolicy`)
    deprecated, scheduled for removal in the "V" release (next).
  - S3 cross-tenant syntax `tenant:bucketname` deprecated.
  - `osd_repair_during_recovery` config key **removed** (not deprecated —
    gone). Configs referencing it will warn but not fail.
  - `bluefs_check_volume_selector_on_umount` **renamed**
    → `bluefs_check_volume_selector_on_mount` and semantics widened. Custom
    tuning that set the old key silently no-ops.
  - `mon_nvmeofgw_beacon_grace` default 10s → 7s;
    `nvmeof_mon_client_tick_period` default 2s → 1s (NVMe-oF gateway only).
- **Cross-component:** Rook pairing — see `compat/rook.md` for which Rook
  minor first added Tentacle support. Do not infer; the Rook compat table is
  the contract.
- **Notable:**
  - FastEC opt-in: per-pool `allow_ec_optimizations` flag. Requires 4K-
    aligned chunk sizes; monitor rejects non-aligned attempts.
  - BlueStore OMAP iteration rewritten — faster RGW listing and scrubs. No
    on-disk format bump; transparent to operators.
  - Faster BlueFS WAL; volume-selector recovery bug fixes for envelope-mode
    WAL. No format incompatibility, but worth pinning to ≥20.2.1 to pick up
    the recovery fixes.
  - New `ceph osd pool availability-status` (tech preview, gated by
    `enable_availability_tracking`).
  - `cephadm` is the upstream tool for non-Rook deployments. Operator runs
    Rook; informational only — `cephadm` workflow does not apply.
- **EOL:** ~2027-11 (estimated 2-year stable line). No formal upstream EOL
  calendar; estimate from prior cadence.

## 19.2.3 / Squid (GA 2024-09-26, latest 19.2.3 2025-07-28)

- **k8s floor:** N/A — see `compat/rook.md`.
- **Breaking:** none cluster-wide that block in-place upgrade from Reef.
  **However:**
  - **Critical data-loss bug in 19.2.1:** RGW `CopyObject` of an object onto
    itself erased the tail data. Fixed in **19.2.2**. **Skip 19.2.0 and
    19.2.1.** Pin Rook's Ceph image to ≥19.2.2.
- **CRD migrations:** N/A.
- **Upgrade ordering (intra-cluster):** standard — mon → mgr → osd → mds →
  rgw. No `require-osd-release` gate documented for Squid that operators
  trip on (Reef→Squid is mostly smooth via Rook reconcile). Always-on MGR
  modules can now be force-disabled if a module pins the upgrade.
- **Deprecations:**
  - **Cache tiering** deprecated. Tests removed. Any CephCluster relying on
    cache-tier pools should plan migration before Tentacle, which is likely
    to remove it outright.
  - **btrfs OSD code path removed.** Squid OSDs require BlueStore.
    (Filestore was already deprecated; this is the cleanup.) Rook hasn't
    supported Filestore for years — informational only.
  - mClock scheduler defaults flipped: `osd_op_num_shards_hdd` 5 → 1,
    `osd_op_num_threads_per_shard_hdd` 1 → 5. Operators with hand-tuned
    HDD shards should re-baseline performance.
- **Cross-component:** Rook pairing — see `compat/rook.md`.
- **Notable:** Hybrid btree2 allocator backported; BlueFS multi-label
  handling refined. No encoding-format incompatibility for Reef→Squid
  rolling upgrade.
- **EOL:** ~2026-09 (estimated). Will be the prior-stable line once
  Tentacle is broadly adopted.

## 18.2.8 / Reef (GA 2023-08-07, final point release 18.2.8 2026-03-20)

- **k8s floor:** N/A — see `compat/rook.md`.
- **Breaking:**
  - **Pacific → Reef direct upgrade is unsafe.** A deprecated connection-
    feature-bit interaction can fire `OSD_UPGRADE_FINISHED` *before* all
    OSDs are actually on Reef. Path: Pacific → Quincy → Reef. Anyone still
    on Pacific in 2026 is already past EOL by years — flag as a separate
    risk.
  - Critical BlueFS regression in 18.2.5 / 18.2.6 (`_extend_log seq
    advance`). Fixed in **18.2.7**. **Skip 18.2.5 and 18.2.6.** Pin
    Rook-managed Reef clusters to ≥18.2.7, preferably 18.2.8.
- **CRD migrations:** N/A.
- **Upgrade ordering (intra-cluster):** standard. No notable one-way gate
  unique to Reef itself.
- **Deprecations:**
  - Cache tiering deprecated (tests removed in 18.2.5 — same deprecation
    Squid carries forward).
  - RBD-NBD `try-netlink` mapping is now default; legacy ioctl fallback
    still works but is deprecated.
  - `cloud-restore` removed from RGW (PR #65638).
- **Cross-component:** Rook pairing — see `compat/rook.md`. Reef is the
  oldest Ceph line that mainstream Rook minors still ship.
- **Notable:** No on-disk format flip from Quincy to Reef. 18.2.8 is the
  final point release of the Reef line.
- **EOL:** **2026-03-20** (effective — final point release shipped; no
  further patches planned). Operators still on Reef past 2026-Q2 are on
  unsupported software and should plan Squid or Tentacle migration via
  Rook's pairing table.

## Sift notes

- Ceph's k8s compatibility is entirely transitive through Rook — there is
  no `k8s X requires Ceph Y` constraint anywhere in upstream Ceph. The
  Rook compat file owns that axis. This file owns the *Ceph-side* axis:
  protocol breaks, removed modules, encoding gates, intra-cluster ordering.
- Three releases (Reef / Squid / Tentacle) overlap as of 2026-05-28; floor
  set to **18.2** because Reef just EOL'd and operators with Reef in
  production still need verdict coverage during their migration window.
  Move floor to 19.2 once the Reef migration tail clears (expected Q4
  2026).
- Versions skipped due to known data-loss / BlueFS regressions: **18.2.5,
  18.2.6, 19.2.0, 19.2.1**. Verdicts touching any of these four point
  releases must flag the issue regardless of Rook's compat answer.
