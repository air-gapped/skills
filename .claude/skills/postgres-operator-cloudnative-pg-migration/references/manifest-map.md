# Manifest translation: acid.zalan.do `postgresql` → postgresql.cnpg.io `Cluster`

Field-by-field, verified 2026-07-24 against the CNPG generated API
reference (`cloudnative-pg.v1.md` @ v1.30.0+51) and the Zalando CRD Go
source (`postgresql_type.go`). **No conversion tool exists anywhere** —
this table is the substitute. Version gates note the minimum CNPG minor.

Contents: [Core](#core) · [Users and databases](#users-and-databases) ·
[postgresql block](#postgresql-block) · [Patroni block → CNPG HA](#patroni-block--cnpg-ha) ·
[Storage, resources, pods](#storage-resources-pods) · [Pooler/backups/standby/TLS/clone](#pooler-backups-standby-tls-clone) ·
[New decisions](#new-decisions-with-no-zalando-input) · [Operator-level config](#operator-level-configuration) · [streams](#zalando-streams-cdcfes)

Legend: — = no equivalent (decision required).

## Core

| Zalando | CNPG | Notes |
|---|---|---|
| `numberOfInstances` | `.spec.instances` | no operator-side min/max clamps in CNPG |
| `teamId` | — | drop the concept; keep the full cluster name to minimize secret/service churn |
| `dockerImage` (Spilo) | `.spec.imageName` or `.spec.imageCatalogRef` | mutually exclusive; Spilo images unusable by CNPG |
| `spiloRunAsUser/Group`, `spiloFSGroup` | `.spec.postgresUID/.postgresGID` (default 26) + securityContext | CNPG is non-root by design |
| `env` / `envFrom` (undocumented but in CRD) | `.spec.env` / `.spec.envFrom` | 1:1 |
| `initContainers` | — | CNPG-I plugins only |
| `livenessProbe` | `.spec.probes` (+ `startDelay` default 3600s, covers slow WAL replay) | setting `probes.startup.failureThreshold` manually disables startDelay math |

## Users and databases

| Zalando | CNPG | Notes |
|---|---|---|
| `users: {name: [flags]}` | `.spec.managed.roles` (≥1.20) or `DatabaseRole` CRD (≥1.30) | fields: ensure, passwordSecret (kubernetes.io/basic-auth), disablePassword, connectionLimit, validUntil, inRoles (GRANT/REVOKE reconciled), inherit, superuser, createdb, createrole, `login` (**default false** — Zalando default is LOGIN), replication, bypassrls. `DatabaseRole` adds reclaim policy + `clientCertificate.enabled` (operator-issued TLS client cert in `<name>-client-cert`; the pg_hba `cert` rule must be added manually) |
| (auto-generated credential secrets) | — | **CNPG generates passwords only for the bootstrap owner (`-app`) and superuser.** Extra managed roles need pre-created basic-auth Secrets (#3788 open). Workarounds: external-secrets, scripted Secret creation, or `postInitSQL`/`postInitApplicationSQLRefs` (Secret-backed SQL keeps passwords out of manifests) |
| `usersWithSecretRotation` / `usersWithInPlaceSecretRotation` | — | no rotation machinery; `validUntil` + cert auth are the primitives |
| `databases: {name: owner}` | one `Database` CR each (≥1.25) | owner (required, ALTER-able), ensure, encoding/locale* (immutable), reclaim policy; `schemas` + `extensions` declarative (≥1.26), `fdws`/foreign servers (≥1.28). Owner role must exist first — same ordering as Zalando |
| `preparedDatabases` (owner/reader/writer trios, defaultUsers, schemas, extensions, secretNamespace) | — | reconstruct: Database CR (db+schemas+extensions) + managed.roles trio with `inRoles` chains + `postInitApplicationSQLRefs` for GRANTs/ALTER DEFAULT PRIVILEGES. Default-privilege upkeep on later schema additions becomes manual. `secretNamespace` (cross-ns secrets): no equivalent |

## postgresql block

| Zalando | CNPG | Notes |
|---|---|---|
| `postgresql.version` | implied by image tag / `imageCatalogRef.major` | |
| `postgresql.parameters` | `.spec.postgresql.parameters` | reload applied live; restart-requiring params trigger automatic rolling restart per `primaryUpdateMethod`. **Strip the ~60 operator-owned params**: archive_*, restore_command, recovery_*, hot_standby, listen_addresses, port, primary_conninfo, primary_slot_name, ssl_*, synchronous_standby_names, logging_collector, log_directory/filename/rotation*, cluster_name, allow_alter_system; `shared_preload_libraries` → dedicated `.spec.postgresql.shared_preload_libraries` array |
| (`wal_level` via parameters) | defaults to **`logical`** in CNPG (Spilo default hot_standby) | drop to `replica` to cut WAL volume if no logical consumers |
| (ALTER SYSTEM allowed) | disabled by default (`.spec.postgresql.enableAlterSystem`) | behavior change for DBAs |
| `patroni.pg_hba` | `.spec.postgresql.pg_hba` | **semantic flip: Zalando REPLACES the default hba; CNPG APPENDS between operator-fixed first/last rules.** Clusters that tightened/removed defaults can't reproduce that exactly. `${podselector:…}` expansion ≥1.29 |
| (no pg_ident) | `.spec.postgresql.pg_ident` | new capability |

## Patroni block → CNPG HA

| Zalando | CNPG | Notes |
|---|---|---|
| `patroni.ttl/loop_wait/retry_timeout` | `.spec.primaryLease` (≥1.30: leaseDuration 15s / renewDeadline 10s / retryPeriod 2s) + `failoverDelay` (0) / `switchoverDelay` (3600 — lower it for RTO-biased fleets) | lease is a promotion **gate, not a fence** (see pitfalls §HA) |
| `synchronous_mode` / `synchronous_mode_strict` / `synchronous_node_count` | `.spec.postgresql.synchronous {method: any\|first, number, dataDurability (≥1.25): required≈strict / preferred≈non-strict, failoverQuorum (≥1.28)}` | legacy `minSyncReplicas`/`maxSyncReplicas` top-level pair still exists — don't mix APIs |
| `patroni.slots` (permanent slots) | `.spec.replicationSlots` (HA slots default on, `slotPrefix _cnpg_`; `synchronizeReplicas` for user slots; `synchronizeLogicalDecoding` ≥1.27, needs PG17+ or pg_failover_slots) | |
| `failsafe_mode` | — | architectural difference; compensate with sync replication + failoverQuorum (pitfalls §HA) |
| `maximum_lag_on_failover` | — | closest: sync replication + failoverQuorum |
| `patroni.initdb` options | `bootstrap.initdb` explicit fields (dataChecksums, encoding, localeCollate/localeCType — **default C, set explicitly**, localeProvider/icuLocale ≥PG15, builtinLocale ≥PG17, walSegmentSize) | raw `options` array deprecated |

## Storage, resources, pods

| Zalando | CNPG | Notes |
|---|---|---|
| `volume.size/storageClass` | `.spec.storage.size/storageClass` (+ `resizeInUseVolumes`, no shrink) | |
| `volume.selector/iops/throughput` | via `storage.pvcTemplate` + StorageClass params | |
| `volume.subPath` | — | |
| `additionalVolumes` | — (only `projectedVolumeTemplate` → `/projected`, `ephemeralVolumeSource`, `ephemeralVolumesSizeLimit {shm, temporaryData}`) | arbitrary mounts not supported |
| (WAL on same volume) | `.spec.walStorage` | first-class WAL volume — an upgrade |
| `enableShmVolume` | always mounted; cap via `ephemeralVolumesSizeLimit.shm` | |
| `resources` | `.spec.resources` (hugepages included) | set requests=limits → Guaranteed QoS → operator sets PG_OOM_ADJUST_VALUE=0 (postmaster survives OOM, children die first) |
| `sidecars` | — | CNPG-I plugin sidecars only; exporter sidecars → built-in metrics + `monitoring.customQueriesConfigMap/Secret` |
| `nodeAffinity` / `tolerations` | `.spec.affinity.nodeAffinity` / `.spec.affinity.tolerations` | tolerations nest under affinity, not top-level |
| (operator-level anti-affinity) | `.spec.affinity.enablePodAntiAffinity` (default on, preferred; `podAntiAffinityType: required` for hard), `topologyKey` | |
| `topologySpreadConstraints` | `.spec.topologySpreadConstraints` | any supported CNPG version |
| `podPriorityClassName` / `schedulerName` | `.spec.priorityClassName` / `.spec.schedulerName` | |
| `podAnnotations` + inherited labels | `.spec.inheritedMetadata` (labels+annotations on all generated objects) | |
| `serviceAnnotations`, `enableMasterLoadBalancer` etc., `allowedSourceRanges` | `.spec.managed.services` (≥1.24): `disabledDefaultServices`, per-selectorType `serviceTemplate` (type LoadBalancer/NodePort, loadBalancerSourceRanges, annotations) | |

## Pooler, backups, standby, TLS, clone

| Zalando | CNPG | Notes |
|---|---|---|
| `enableConnectionPooler` / `enableReplicaConnectionPooler` / `connectionPooler.*` | separate `Pooler` CR per service type (`type: rw` / `ro`) | `mode`→`pgbouncer.poolMode`; `numberOfInstances`→`instances`; **Zalando divides `maxDBConnections` across pods, CNPG passes parameters verbatim per instance — recompute**; auth auto-managed (`cnpg_pooler_pgbouncer` + user_search authQuery); image via `pgbouncer.imageCatalogRef` ≥1.30 |
| `enableLogicalBackup` / `logicalBackupSchedule` | — | CNPG Backup/ScheduledBackup are physical-only; hand-build a pg_dump CronJob if dumps are a requirement |
| (WAL-G env config in Spilo) | `ObjectStore` CRD + `spec.plugins` (barman-cloud) | see backup-chain.md; never point CNPG at the WAL-G bucket |
| `standby.{s3_wal_path,gs_wal_path}` | — | CNPG cannot consume WAL-G-layout archives; use streaming instead |
| `standby.{standby_host,standby_port}` | `.spec.replica {enabled, source}` + `externalClusters[].connectionParameters` | distributed topology (`primary`/`self`, promotionToken) is the DR upgrade path |
| `tls.{secretName,caFile,…}` | `.spec.certificates {serverTLSSecret, serverCASecret, clientCASecret, replicationTLSSecret, serverAltDNSNames}` | fixed key names tls.crt/tls.key (no filename knobs); CNPG adds client-cert replication auth; self-signs by default |
| `clone.{cluster,timestamp,s3_wal_path}` | `bootstrap.recovery` (from CNPG backup/snapshot only) or `bootstrap.pg_basebackup` (live streaming clone) | PITR inclusivity differs: Zalando target non-inclusive; CNPG `exclusive` defaults false (inclusive). WAL-G S3 paths unusable |
| `maintenanceWindows` | — | **`nodeMaintenanceWindow` is a false friend** (controls PVC reuse during node maintenance, not upgrade timing). Substitute: `primaryUpdateStrategy: supervised` + GitOps-timed rollouts |
| (`major_version_upgrade_mode` operator config) | bump image major → declarative **offline** in-place `pg_upgrade` (≥1.26); whole cluster down; same image OS generation required; PITR doesn't cross the boundary | |

## New decisions with no Zalando input

- `primaryUpdateStrategy`: `unsupervised` (default) vs `supervised` (manual promote step per rollout).
- `primaryUpdateMethod`: `restart` (default) vs `switchover`.
- `enableSuperuserAccess`: default **false** (no `-superuser` secret, no
  network superuser) — opposite of Zalando's always-present postgres
  secret. Enable only where genuinely needed.
- `enablePDB` (default true; Zalando managed PDBs via operator config).
- Probe strategy (`pg_isready` vs `query` vs `streaming` with lag threshold).
- `.spec.tablespaces` (declarative, per-tablespace PVCs — no Zalando equivalent).

## Operator-level configuration

| Zalando OperatorConfiguration | CNPG (`cnpg-controller-manager-config` ConfigMap/Secret, Helm `config.data`) |
|---|---|
| `watched_namespace` | `WATCH_NAMESPACE` (comma-separated) |
| `inherited_labels/annotations` | `INHERITED_LABELS` / `INHERITED_ANNOTATIONS` (wildcards ok) |
| `docker_image` default | `POSTGRES_IMAGE_NAME` (+ `PGBOUNCER_IMAGE_NAME`) |
| registry pull secret | `PULL_SECRET_NAME` (copied into each cluster ns as `<cluster>-pull`) |
| `default_cpu/memory_request/limit` | — (per-Cluster only) |
| teams API, secret rotation intervals, `pod_environment_configmap` | — (`pod_environment_configmap` ≈ per-cluster `env`/`envFrom`) |
| (multi-operator `CONTROLLER_ID`) | `ENABLE_WEBHOOK_NAMESPACE_SUFFIX` (≥1.30) for coexisting CNPG operators |

## Zalando `streams` (CDC/FES)

No CNPG equivalent for the Nakadi/FES machinery. CNPG's
Publication/Subscription CRDs cover the PUBLICATION half declaratively;
event-stream infrastructure must be re-homed separately.
