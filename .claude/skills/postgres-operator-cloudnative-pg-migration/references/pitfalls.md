# Pitfalls catalog

Contents: [Data-corrupting / data-losing](#data-corrupting--data-losing) (1–7) ·
[Outage-causing](#outage-causing) (8–14) · [Operational surprises](#operational-surprises-cnpg-side-post-migration) (15–21) ·
[HA semantics](#ha-semantics-decision-grade-detail) · [Zalando-side traps](#zalando-side-pre-migration-traps) (22–24)

Scan before executing any migration plan. Ordered by severity. Version
gates verified 2026-07-24.

## Data-corrupting / data-losing

1. **Collation wall on physical paths** (Wall 1): any
   pg_basebackup/replica copy from Spilo (Ubuntu glibc 2.35, or 2.27
   with `USE_OLD_LOCALES=true`) onto CNPG images (Debian glibc
   2.36/2.41) silently corrupts text-collated btree indexes, unique
   constraints, and partition bounds. `REFRESH COLLATION VERSION`
   silences the warning without fixing anything. Mandatory on path C:
   amcheck (`bt_index_check`) + REINDEX of all text-collated indexes
   before accepting writes. For `USE_OLD_LOCALES` sources: don't use
   path C at all. Logical paths are immune.
2. **CNPG initdb locale default is `C`** — not Spilo's `en_US.UTF-8`.
   An untranslated Cluster silently changes ORDER BY/comparison
   semantics for every text column. Set `localeCollate`/`localeCType`
   explicitly to match the source; consider `localeProvider: icu`
   (PG15+) or builtin `C.UTF-8` (PG17+) to escape glibc permanently.
3. **WAL-G archive is unreadable by CNPG** (Wall 2): never wire
   `externalClusters`/`recovery` at the Zalando bucket; keep the retired
   Spilo stack resurrectable until retention expires. Fresh CNPG base
   backup immediately at cutover.
4. **First plugin backup on an idle cluster is unrestorable** until the
   final WAL segment archives (plugin-barman-cloud #652, open). Force
   `SELECT pg_switch_wal();` after the first backup before declaring
   the cluster protected.
5. **Sequences are not replicated** by logical replication — apps insert
   duplicate keys after cutover unless `kubectl cnpg subscription
   sync-sequences` ran during the write pause. Matviews are also not
   carried (REFRESH after); large objects not at all (forces path B).
6. **monolith import strips SUPERUSER from every role; microservice
   import imports no roles at all.** Either re-grant deliberately
   post-import or (better) inventory which roles truly need superuser
   and stop granting it.
7. **md5 password hashes** survive physical/monolith moves and then fail
   against scram-only pg_hba — looks like an outage at first app
   connect. Pre-flight finds them (`substr(rolpassword,1,6)='md5…'`);
   reset those passwords.

## Outage-causing

8. **Spilo extension dependencies break pg_restore** (CNPG discussion
   #3723; both published migrations hit it): `metric_helpers`,
   `user_management` schemas and extensions like pg_stat_kcache,
   set_user aren't in stock CNPG images. Drop them pre-dump or build a
   custom operand image.
9. **search_path after import** (`pg_restore --no-acl --no-owner`): apps
   using a non-default schema see "missing tables" — looks like total
   data loss. `ALTER USER <owner> SET search_path TO "$user", <schema>,
   public` via postInitApplicationSQL (microservice) or manually
   (monolith).
10. **SSL cannot be disabled in CNPG** (#5568, #5736): clients with
    `sslmode=disable` hardcoded fail. Also the reason physical
    replication from a no-TLS source setup fails.
11. **Pooler limits multiply**: Zalando divided `maxDBConnections`
    across pooler pods; CNPG passes pgbouncer parameters verbatim per
    instance. Copying the old number over N instances = N× the intended
    connections — can exhaust `max_connections` at cutover.
12. **Pod-name collision in side-by-side operation**: Zalando pods
    `<name>-0,1…` vs CNPG pods `<name>-1,2…` overlap at `<name>-1` if
    the same cluster name is used in one namespace.
13. **Slot WAL retention during long initial copy** (path A): an
    unattended lagging subscription retains WAL on the Spilo source
    until the disk fills. Set `max_slot_wal_keep_size` — the slot
    invalidates (migration restarts) instead of the source dying.
14. **Long-running source transactions** delay logical-slot creation
    (snapshot export waits) — a stuck vacuum or idle-in-transaction
    session can stall path A's start invisibly.

## Operational surprises (CNPG-side, post-migration)

15. **Operator upgrades rolling-restart every cluster** by default
    (instance-manager binary swap). Plan windows; or accept
    `ENABLE_INSTANCE_MANAGER_INPLACE_UPDATES` (off by default,
    "breaks immutability"). Minors live ~6 months; skipping minors on
    upgrade is discouraged.
16. **In-tree barmanObjectStore removal at 1.31** (slipped 4×, don't
    hard-code) + backup metrics rename with the plugin (#8902): old
    `cnpg_collector_last_*_backup_timestamp` go silently stale. Alert
    on new-metric absence.
17. **`nodeMaintenanceWindow` is a false friend** — PVC-reuse control
    for node maintenance, not an upgrade-timing window. Zalando
    `maintenanceWindows` has no equivalent; use
    `primaryUpdateStrategy: supervised` + GitOps timing.
18. **`enableSuperuserAccess` defaults false** — admin tooling expecting
    a postgres secret finds none.
19. **pg_hba APPENDS in CNPG** (between operator-fixed rules) where
    Zalando REPLACED — tightened-default policies can't be reproduced
    exactly; verify with `pg_hba_file_rules`.
20. **ALTER SYSTEM disabled by default** in CNPG — DBA muscle memory
    breaks; config changes go through the manifest (which is the point).
21. **pg_upgrade constraints**: offline (whole cluster down), same image
    OS generation only (bookworm→trixie refused), PITR doesn't cross
    the boundary, statistics not carried (plan post-upgrade ANALYZE).
    PG 17.0–17.5 pg_upgrade fails if `max_slot_wal_keep_size` ≠ -1
    (fixed 17.6/18).

## HA semantics (decision-grade detail)

CNPG's split-brain story, post-2025 (history: #7407 → discussion #7462,
closed 2025-12-31):

- **Primary isolation check** (default ON since 1.27): primary's
  liveness probe fails iff it reaches neither the K8s API **nor any
  other instance**; kubelet kills it in ~30 s. This is the fence — but
  only for *total* isolation.
- **Failover quorum** (stable 1.28, `synchronous.failoverQuorum`):
  R+W>N check before promotion; refuses to promote a possibly-stale
  replica (waits; `kubectl cnpg promote` is the manual override).
  Guarantee covers synchronously-committed data only —
  `synchronous_commit=local` sessions are explicitly excluded.
- **Primary lease** (1.30, always on): promotion mutex; candidate waits
  a full leaseDuration (15 s) before takeover. Code-verified: an
  API-partitioned primary retries forever (relies on the isolation
  check); it self-stops only when it *observes* preemption.

Residual vs Patroni: under **partial partition** (primary loses the API
but reaches ≥1 peer — the freshly promoted primary counts!) CNPG never
fences, where Patroni failsafe demotes unless ALL members are
reachable. With `dataDurability: required` divergence is limited to
unacknowledged writes; **async clusters have a real acknowledged-write
split-brain window**, plus a ~15 s promote-before-fence overlap (lease
15 s < fence 30 s). Patroni is conversely *less* available during plain
API-server outages (non-failsafe demotes; CNPG keeps serving).

Prescription: production clusters = 3 instances +
`synchronous: {method: any, number: 1, dataDurability: required,
failoverQuorum: true}` → durability-equivalent to Spilo
`synchronous_mode` + `failsafe_mode`. (The multi-instance-without-sync
warning webhook is 1.31 material, PR #11148 — not in 1.30.)

Open HA-adjacent bugs to re-check at execution time: #10430 (failover
skipped on instance-manager HTTP false-negative), #10287
(false-positive fencing when a sync replica is slow during API blips),
#11202 (no switchover on drain when primary isn't lowest-index pod),
#10547 (`dataDurability: preferred` + failoverQuorum never-ready),
#11110 (restart proceeds with unpromotable lagged replica).

## Zalando-side pre-migration traps

22. **PG ≤13 sources have no CNPG landing image** (operand images PG
    14–18; PG13 support ended 2025-11-13) — import/logical must jump
    majors in one hop; pg_basebackup is impossible.
23. **`wal_level: logical` needs a Patroni rolling restart** — schedule
    it; don't bundle with other parameter changes.
24. **Zalando images are ghcr.io-only since 1.15.x** — resurrection
    plans still pointing at `registry.opensource.zalan.do` will fail.
