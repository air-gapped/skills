# Migration paths: recipes and pre-flight

Contents: [Pre-flight triage](#per-cluster-pre-flight-triage-run-before-choosing-a-path) ·
[Path chooser](#path-chooser) · [Path A — logical replication](#path-a--logical-replication-near-zero-downtime-the-default) ·
[Path B — initdb.import](#path-b--initdbimport-offline-pg_dumppg_restore) ·
[Path C — pg_basebackup](#path-c--pg_basebackup-bootstrap--replica-promotion-constrained) ·
[Side-by-side operation](#side-by-side-operation)

Verified 2026-07-24 against CNPG docs/source at v1.30.0+51 and Spilo/
operator source. All `kubectl cnpg` commands need the kubectl-cnpg
plugin at a version matching the operator minor.

## Per-cluster pre-flight triage (run before choosing a path)

On each Spilo cluster (via `kubectl exec` into the `spilo-role=master`
pod, `psql -U postgres`):

```sql
-- PG major (decides A/B/C eligibility; CNPG operand images are PG 14-18)
SHOW server_version;
-- Wall 1: collation exposure (libc datcollate = exposed on physical paths)
SELECT datname, datcollate, datctype, datcollversion FROM pg_database;
-- Large objects present? (blocks path A; forces B)
SELECT count(*) FROM pg_largeobject_metadata;
-- Tables without PK / replica identity (path A: UPDATE/DELETE will fail)
SELECT n.nspname, c.relname FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog','information_schema')
AND NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisprimary)
AND c.relreplident = 'd';
-- Materialized views (path A: not replicated; REFRESH after cutover)
SELECT schemaname, matviewname FROM pg_matviews;
-- Extensions actually installed (drives operand-image choice)
SELECT extname, extversion FROM pg_extension;
-- Password hash format (md5 rows break against scram-only pg_hba after
-- physical/monolith moves — reset those passwords)
SELECT rolname, substr(rolpassword,1,6) FROM pg_authid WHERE rolpassword IS NOT NULL;
```

Pod-level: `kubectl exec <pod> -- env | grep -E 'USE_OLD_LOCALES|SPILO'`
(`USE_OLD_LOCALES=true` = glibc 2.27 collations = Wall 1 at its worst).

Manifest-level: inventory `users:`, `databases:`, `preparedDatabases:`,
`sidecars:`, `enableLogicalBackup`, `standby:`, `streams:` — each maps
(or doesn't) per manifest-map.md.

## Path chooser

| Condition | Path |
|---|---|
| Production, source PG ≥10, no large objects, downtime budget ≈ minutes | **A** (logical replication) |
| PG ≤13 source (no CNPG image at that major — physical impossible) | **A or B** — destination lands on PG ≥14, majors jumped in one hop (import works from ≥9.6, logical from ≥10) |
| Small DB / dev / batch window available | **B** (simplest) |
| Large objects (`pg_largeobject` non-empty) | **B** (A cannot carry them) |
| TB-scale where a logical copy is impractical AND same major AND collation triage clean | **C** — with the full REINDEX discipline |

CNPG maintainer position (issue #5736): "You should not use physical
replication to migrate from Zalando"; docs: the community "does not
endorse" pg_basebackup bootstrap from non-CNPG sources. IBM Instana's
supported runbook is nonetheless path C — it works, but only with the
discipline below.

## Path A — logical replication (near-zero downtime, the default)

Requires: source PG ≥10, CNPG ≥1.25 (Publication/Subscription CRDs,
added explicitly "to facilitate online migrations"; use ≥1.30 anyway).

**1. Prepare the Spilo source.** In the acid.zalan.do manifest:

```yaml
spec:
  postgresql:
    parameters:
      wal_level: "logical"          # Spilo default is hot_standby
      # max_wal_senders / max_replication_slots default 10 — usually fine
      max_slot_wal_keep_size: "50GB" # cap slot retention: aborts the
                                     # migration instead of filling the disk
```

Patroni rolls the pods. Long-running transactions on the source delay
logical-slot snapshot export — schedule the start accordingly.

**2. Create the destination Cluster** with schema-only import + an
external cluster pointing at the Spilo primary service. Reuse the
Zalando-generated credentials secret:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: <app>-cnpg            # NOT the Zalando name if same namespace
spec:
  instances: 3
  imageName: <registry>/cloudnative-pg/postgresql:17.6-standard-trixie
  bootstrap:
    initdb:
      import:
        type: microservice     # or monolith for multi-DB (see path B notes)
        schemaOnly: true       # schema now, data via replication
        databases: ["<db>"]
        source:
          externalCluster: zalando-src
      # match the source! CNPG defaults to C locale otherwise:
      localeCollate: en_US.UTF-8
      localeCType: en_US.UTF-8
  postgresql:
    synchronous: {method: any, number: 1, dataDurability: required, failoverQuorum: true}
  externalClusters:
    - name: zalando-src
      connectionParameters:
        host: <zalando-cluster>.<ns>.svc   # Zalando master service = cluster name
        user: postgres
        dbname: <db>
        sslmode: require                   # CNPG cannot speak ssl=off; Spilo serves TLS
      password:
        name: postgres.<zalando-cluster>.credentials.postgresql.acid.zalan.do
        key: password
```

**3. Wire replication.** The Publication CRD only targets CNPG clusters;
for a Zalando publisher, let the plugin run the SQL on the source:

```bash
kubectl cnpg publication create <app>-cnpg --external-cluster=zalando-src \
  --publication=migration_pub --all-tables
kubectl cnpg subscription create <app>-cnpg --publication=migration_pub \
  --subscription=migration_sub --external-cluster=zalando-src
```

(Declarative alternative: `Subscription` CR with
`spec.externalClusterName: zalando-src`; publication via SQL on Spilo.)

**4. Monitor lag** until initial copy completes and stays converged:
on source `SELECT slot_name, confirmed_flush_lsn, pg_current_wal_lsn()
FROM pg_replication_slots;` — during the window, keep source-side
failovers quiescent or enable `replicationSlots.highAvailability.
synchronizeLogicalDecoding` semantics only where applicable (that
feature protects CNPG *publishers*; the Spilo publisher relies on
Patroni not failing over mid-copy).

**5. Cutover** (minutes): pause/scale-down writers → verify zero lag →
`kubectl cnpg subscription sync-sequences --subscription=migration_sub
<app>-cnpg` (reads source sequences, `setval()` locally — sequences are
NOT replicated) → `REFRESH MATERIALIZED VIEW` each matview → repoint
apps at `<app>-cnpg-rw` (see app-cutover.md) → smoke test → drop
subscription and publication → first CNPG base backup (backup-chain.md).

**6. Rollback:** trivially reversible pre-cutover (drop sub, nothing
changed on source). Post-cutover reverse replication = create a
publication on CNPG + a plain-SQL subscription on the Spilo side
(Zalando has no Subscription CRD).

Not carried by logical replication: DDL (freeze schema changes during
the window), sequences (step 5), large objects, matview contents;
tables without PK need `ALTER TABLE … REPLICA IDENTITY FULL` on the
source first or UPDATE/DELETE breaks the subscription.

## Path B — `initdb.import` (offline pg_dump/pg_restore)

Two types under `spec.bootstrap.initdb.import`:

| | `microservice` | `monolith` |
|---|---|---|
| Databases | exactly one → `initdb.database` | many (`"*"` ok), names/owners preserved |
| Roles | **not imported** | imported (`roles: ["*"]`) minus postgres/streaming_replica/cnpg_pooler_pgbouncer; **SUPERUSER stripped from every role** |
| `postImportApplicationSQL` | yes | **no** |

Mechanics to plan for: the `pg_dump -Fd` staging dir lives **inside the
destination PGDATA volume** — size the PVC for dump + data + indexes.
The operator runs the import with fsync/archiving off and finishes with
`initdb --sync-only` + `ANALYZE`. Parallelize:

```yaml
import:
  pgDumpExtraOptions: ["--jobs=4"]
  pgRestoreDataOptions: ["--jobs=4"]
  pgRestorePostdataOptions: ["--jobs=2"]
```

Works from sources as old as 9.6 — the only path for PG≤13 Spilo
clusters; migrate-and-upgrade in one hop (destination major ≥ source).

**Spilo extension trap** (bit both published migrations): `pg_restore`
recreates extensions only if present in the destination image, and
Spilo's `metric_helpers`/`user_management` schemas plus extensions like
pg_stat_kcache/set_user break a stock-image import. Two fixes:
- Clean at source (or in an intermediate clone cluster): drop the two
  Spilo schemas and unused extensions before dumping (Wilsher pattern:
  clone via import into a custom image with the extensions installed,
  drop them there, import again into the final stock-image cluster).
- Or build/mirror a custom operand image with the needed extensions.

**search_path trap:** after `pg_restore --no-acl --no-owner`, apps that
relied on a non-default search_path see "missing" tables. Fix in the
final cluster: `postInitApplicationSQL: ["ALTER USER <owner> SET
search_path TO \"$user\", <schema>, public"]` (microservice type only —
monolith must apply it manually post-import).

## Path C — `pg_basebackup` bootstrap / replica promotion (constrained)

Requirements: same PG major, same architecture and tablespaces, a
replication role reachable per source pg_hba, ≥2 spare `max_wal_senders`,
TLS (CNPG cannot disable SSL — #5736/#5568). The Instana-verified
sequence:

1. On the Spilo primary: `CREATE ROLE streaming_replica WITH REPLICATION
   LOGIN PASSWORD '…';` (Spilo pg_hba admits replication connections;
   verify `kubectl exec … -- grep replication …/pg_hba.conf`).
2. CNPG Cluster with `bootstrap.pg_basebackup.source: zalando-src` +
   `replica: {enabled: true, source: zalando-src}` + the external
   cluster streaming connection. The cluster runs as a live replica —
   lag is observable, cutover is a promote, downtime is seconds.
3. **Spilo conf fix (required):** the copied PGDATA carries Spilo's
   `postgresql.conf` with wrong paths. Via `kubectl debug` on the CNPG
   pod: rewrite `hba_file`/`ident_file` to
   `/var/lib/postgresql/data/pgdata/…`, append `include 'custom.conf'`
   / `include 'override.conf'` (and `touch` those files if absent on the
   source before the copy).
4. Cutover: stop writers → verify lag 0 → flip `replica.enabled: false`
   (promote; **new timeline** — the Zalando side diverges from here) →
   repoint apps.
5. **Wall 1 discipline (non-negotiable):**
   `ALTER DATABASE template1 REFRESH COLLATION VERSION;` (and each DB)
   only silences the warning — additionally run `amcheck`
   (`bt_index_check` over text-collated indexes) and `REINDEX` every
   collation-dependent index **before accepting writes**. For
   `USE_OLD_LOCALES=true` sources, do not use path C at all.
6. Rollback after promote = discard CNPG-side writes (timeline
   divergence). Keep the Zalando cluster stopped-but-intact until soak
   completes.

## Side-by-side operation

Safe: API groups differ (`acid.zalan.do/v1` vs `postgresql.cnpg.io/v1`),
CNPG webhooks match only its own resources, Zalando registers no
webhooks. Only collision is pod naming — Zalando StatefulSet pods are
`<name>-0,1,…`, CNPG instance pods `<name>-1,2,…`; same name in one
namespace overlaps at `<name>-1`. Use a new cluster name (or namespace)
and keep it: the name prefixes every service and secret consumers use.
