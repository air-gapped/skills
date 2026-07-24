---
name: postgres-operator-cloudnative-pg-migration
description: >-
  Migrate PostgreSQL clusters from the Zalando postgres-operator
  (acid.zalan.do `postgresql` CRs, Spilo/Patroni, WAL-G) to CloudNativePG
  (CNPG) on Kubernetes, incl. fully air-gapped clusters. Core knowledge:
  the two walls (Spilo↔CNPG glibc/collation divergence that corrupts
  physically-copied indexes; WAL-G↔Barman archive incompatibility that
  strands old backups), three migration paths (logical replication
  default; initdb.import for small DBs/PG≤13; pg_basebackup as the
  discouraged same-major exception), the acid.zalan.do→Cluster manifest
  field map with no-equivalent gaps (preparedDatabases, sidecars,
  logical-backup cron), backup re-plumbing onto the barman-cloud CNPG-I
  plugin, HA parity (synchronous + failoverQuorum vs Patroni failsafe),
  consumer cutover (service/secret renames, scram, cnpg_ metrics),
  air-gap mirroring, stay-vs-migrate evidence.
when_to_use: >-
  Use whenever the task involves moving off the Zalando postgres-operator
  or onto CloudNativePG: "migrate zalando to cnpg", "postgres-operator to
  cloudnative-pg", "replace spilo", "convert acid.zalan.do manifest",
  "is zalando postgres-operator dead", "which postgres operator".
  Symptoms: CNPG replica won't bootstrap from
  a Spilo primary (SSL/scram), pg_restore failing on Spilo extensions
  (metric_helpers, user_management), search_path "data loss" after
  import, collation version mismatch after basebackup, barman-cloud
  can't read a WAL-G bucket, apps failing after <cluster>-rw rename.
  NOT for tuning a healthy CNPG fleet or for Crunchy/StackGres/Percona
  migrations.
argument-hint: "[decide|paths|manifest|backup|cutover|airgap] (optional focus area)"
---

# postgres-operator-cloudnative-pg-migration

Migrate PostgreSQL clusters from the Zalando postgres-operator (Spilo +
Patroni) to CloudNativePG with data intact, indexes trustworthy, backups
restorable at every phase, and no dependency left on maintenance-mode
artifacts. Facts below were verified 2026-07-24 against primary sources
(both operator repos at HEAD, release manifests, maintainer statements);
re-verify anything version-gated before relying on it in a later year.
Version anchor at authoring time: Zalando 1.15.1 (Spilo-17 4.0-p3, PG
13–17), CNPG 1.30.0 / 1.29.2 (PG 14–18), plugin-barman-cloud v0.13.0.

## Why this migration exists

Zalando's operator is in maintainer-confirmed maintenance mode ("a little
idle state… not encouraged by management", issue #2921, June 2025): ~1
release/year, one sustained maintainer, no release in 2026 despite a
commit rebound. CNPG runs ~7× the human commit volume, releases
quarterly across three maintained lines, entered CNCF Sandbox (Jan 2025,
incubation pending), and has a documented migration wave (IBM Instana
ships official Zalando→CNPG docs). **This is strategic, not an
emergency**: Zalando is safe to run through ~2027 (v1.15.x covers PG13–17
and the K8s-1.33 Endpoints deprecation), Patroni itself is thriving, and
CNPG brings its own churn costs (quarterly operator upgrades that
rolling-restart every cluster; a backup-plugin transition in flight).
Full evidence, the skeptic's case, and alternatives:
`references/decision.md`. Migrate deliberately, cluster by cluster.

## The two walls that shape every plan

**Wall 1 — glibc/collation (physical data paths).** Spilo images are
Ubuntu (glibc 2.35; or a bundled Ubuntu 18.04 archive at glibc **2.27**
when `USE_OLD_LOCALES=true` — common on long-lived fleets). CNPG operand
images are Debian bookworm/trixie (glibc 2.36/2.41). Zalando's initdb
default is `en_US.UTF-8` (libc), so collation-sensitive btree indexes are
the norm. Any physical copy (`pg_basebackup`, replica promotion) crosses
at least one glibc boundary — for `USE_OLD_LOCALES` clusters it crosses
the catastrophic glibc-2.28 ISO-14651 break — and text indexes, unique
constraints, and partition bounds become **silently** corrupt. `REFRESH
COLLATION VERSION` only silences the warning. Logical paths (replication,
import) rebuild indexes on the destination and dodge this entirely.
Triage per cluster before choosing a path:
`SELECT datname, datcollate, datcollversion FROM pg_database;` plus
checking `USE_OLD_LOCALES` in the pod env.

**Wall 2 — WAL-G ↔ Barman (backup archives).** Current Spilo backs up
with WAL-G; CNPG restores only Barman-Cloud-layout object stores. The
formats are disjoint (`basebackups_005/wal_005` vs `base/wals`) with no
interop or conversion tool in either project. Consequences: a CNPG
cluster cannot bootstrap or PITR from the Zalando S3 archive, and after
cutover the old bucket is restorable **only by a Spilo/WAL-G stack** —
freeze it read-only and keep the retired cluster (or a documented
resurrection path) until the retention window expires. Take a fresh
CNPG base backup immediately at cutover.

## Choosing a migration path

Three paths; pick by PG major, size, downtime budget, and Wall 1 status.
Full recipes with YAML and cutover sequences: `references/migration-paths.md`.

| Path | When | Downtime | Wall 1 |
|---|---|---|---|
| **A. Logical replication** (Publication/Subscription CRDs, CNPG ≥1.25) | default for production; source PG ≥10; no large objects | near-zero (write pause at cutover) | immune |
| **B. `initdb.import`** (pg_dump/pg_restore) | small DBs; PG ≤13 sources (CNPG images are 14–18 — jump majors in one hop); large objects | full copy window | immune |
| **C. `pg_basebackup` / replica promote** | same major only; TB-scale where logical copy is impractical | short (promote) | **exposed** — amcheck + full REINDEX of text indexes mandatory |

The CNPG maintainer explicitly discourages C from Zalando sources ("You
should not use physical replication to migrate from Zalando", #5736) —
yet IBM Instana's supported runbook is exactly C, with Spilo conf-path
fixes. Both are real; default to A, and treat C as the constrained
exception it is.

Path A skeleton: set `wal_level: logical` on the Spilo manifest (rolling
restart) → CNPG Cluster with `bootstrap.initdb.import` + `schemaOnly:
true` + `externalClusters` pointing at the Spilo primary (reuse the
Zalando credentials secret) → `kubectl cnpg publication create
--external-cluster` (runs SQL on the source) → `subscription create` →
watch lag → pause writes → `kubectl cnpg subscription sync-sequences` →
repoint apps → drop pub/sub. Not carried: DDL, sequence values (the
sync-sequences step), large objects, matviews (REFRESH after).

## Translating the manifest

No conversion tool exists anywhere — translation is manual against the
field map in `references/manifest-map.md` (every acid.zalan.do field →
CNPG equivalent or explicit gap, with minimum CNPG versions). The gaps
that most often force design decisions: `preparedDatabases` role trios
(reconstruct via `managed.roles` + `inRoles` + `postInitApplicationSQLRefs`),
password auto-generation for extra users (CNPG requires pre-created
basic-auth Secrets — #3788), arbitrary `sidecars`/`initContainers` (CNPG-I
plugins only), `enableLogicalBackup` pg_dump cron (hand-build), and
`maintenanceWindows` (`nodeMaintenanceWindow` is a false friend — it
controls PVC reuse, not upgrade timing). Strip CNPG's ~60 operator-owned
parameters from any copied `postgresql.parameters` map.

Extensions: Spilo bundles timescaledb/postgis/pg_cron/pg_stat_kcache/
set_user/…; CNPG `standard` images add only PGAudit, pgvector,
pg_failover_slots, locales, JIT. `pg_restore` fails on missing
extensions. Drop unused Spilo extensions pre-dump, use the official
postgis image, or build a custom operand image (TimescaleDB has **no**
official CNPG image; `timescale/timescaledb-ha` is incompatible).

## HA parity

CNPG closed most of the Patroni gap: default-on primary isolation
self-fencing (1.27), quorum-gated failover (1.28), primary lease (1.30).
The honest residual: under *partial* partition (primary loses the API
server but reaches ≥1 peer) CNPG never fences where Patroni's failsafe
demotes — with async replication that is a real acknowledged-write
split-brain window. For Patroni-equivalent durability, migrated
production clusters get 3 instances +
`postgresql.synchronous: {method: any, number: 1, dataDurability:
required, failoverQuorum: true}`. Details, defaults, and open HA bugs to
watch: `references/pitfalls.md` §HA.

## Backups, cutover, air-gap

- **Backups**: go plugin-first (in-tree `barmanObjectStore` removal is
  scheduled for CNPG 1.31 after slipping four times — never hard-code
  that). ObjectStore CRD wiring, the sidecar image hidden in the release
  manifest, cert-manager avoidance, dashboards for renamed
  `barman_cloud_*` metrics, and the frozen-WAL-G-bucket plan:
  `references/backup-chain.md`.
- **Consumer cutover**: services `<cluster>`/`<cluster>-repl` →
  `<cluster>-rw/-ro/-r`; secrets `<user>.<cluster>.credentials…` →
  `<cluster>-app`/`-superuser` (richer keys); md5 password hashes
  surviving physical/monolith moves fail against scram-only pg_hba;
  `pg_*` exporter metrics → `cnpg_*` with no shim. Checklists:
  `references/app-cutover.md`.
- **Air-gap**: the mirror list is operator + operand (`-standard-`
  flavor keeps en_US.UTF-8 available) + pgbouncer + plugin + sidecar
  images, two Helm charts; no telemetry to disable; cosign-verify at the
  mirror boundary. Registry knobs (`PULL_SECRET_NAME`,
  `POSTGRES_IMAGE_NAME`): `references/airgap.md`.

Side-by-side operation of both operators in one cluster is safe
(different API groups; Zalando registers no webhooks) — but never reuse
a Zalando cluster name in the same namespace: Zalando pods `<name>-0,1…`
and CNPG pods `<name>-1,2…` collide at `<name>-1`.

## Pitfalls quick index

Before executing any plan, scan `references/pitfalls.md` (severity-
ordered). Headliners beyond the walls: CNPG initdb defaults to `C`
locale (silent ORDER BY change vs Spilo's en_US.UTF-8 — set locale
explicitly, or move to ICU/builtin to escape glibc); `enableSuperuserAccess`
defaults false; CNPG pg_hba APPENDS where Zalando REPLACES; monolith
import strips SUPERUSER; first plugin backup on an idle cluster is
unrestorable until a WAL switch; SSL cannot be fully disabled in CNPG.

## Reference files

| File | Read when |
|---|---|
| `references/decision.md` | deciding stay-vs-migrate; trend evidence, skeptic's case, alternatives |
| `references/migration-paths.md` | executing a migration: full recipes for paths A/B/C, per-cluster pre-flight triage |
| `references/manifest-map.md` | translating an acid.zalan.do manifest; field map + gaps + operator-config knobs |
| `references/backup-chain.md` | re-plumbing backups onto the barman-cloud plugin; WAL-G retention plan; snapshot-only option |
| `references/app-cutover.md` | repointing applications; secret/service/auth/monitoring checklists |
| `references/airgap.md` | air-gapped mirroring: exact images, charts, registry configuration |
| `references/pitfalls.md` | always, before executing a migration plan |
| `references/sources.md` | verifying or freshening any dated claim |
