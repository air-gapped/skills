# Backup chain: WAL-G off, barman-cloud plugin on

Contents: [The WAL-G wall](#the-wal-g-wall-recap--plan) · [Plugin install](#plugin-install-air-gap-ready) ·
[Wiring a Cluster](#wiring-a-cluster) · [In-tree→plugin migration](#if-migrating-an-existing-cnpg-in-tree-cluster-not-the-zalando-case) ·
[Monitoring](#monitoring-the-new-chain) · [Snapshot-only alternative](#snapshot-only-alternative-no-object-store)

Verified 2026-07-24. Version anchor: plugin-barman-cloud v0.13.0
(2026-06-10, pre-1.0, ~monthly cadence), CNPG 1.30.0. In-tree
`barmanObjectStore` is deprecated since 1.26; removal is scheduled for
**1.31.0** after slipping four times (1.28→1.29→1.30→1.31) — treat the
removal version as volatile, but build new clusters plugin-first
regardless.

## The WAL-G wall (recap + plan)

Wall 2 (see SKILL.md): the layouts are disjoint, with no interop or
conversion in either project (verified: zero requests in both issue
trackers). Therefore:

1. **Never** point CNPG `externalClusters[].barmanObjectStore` /
   `bootstrap.recovery` at the Zalando bucket — it cannot work.
2. At cutover, take the first CNPG base backup **immediately**. On idle
   clusters force `SELECT pg_switch_wal();` afterwards — until the final
   WAL segment archives, the first backup is unrestorable (plugin
   issue #652, open).
3. Freeze the WAL-G bucket read-only. It remains restorable **only by a
   Spilo/WAL-G stack**: keep the retired Zalando cluster
   stopped-but-resurrectable (manifest + operator version + Spilo image
   pinned in git, PVCs or a final basebackup retained) until the
   organization's PITR retention window has fully passed. Only then
   decommission and delete.
4. There is a PITR seam at cutover: pre-cutover targets restore via the
   Spilo stack, post-cutover targets via CNPG. Document the timestamp.

## Plugin install (air-gap-ready)

Images (both required):
- `ghcr.io/cloudnative-pg/plugin-barman-cloud:v0.13.0` (Deployment)
- `ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar:v0.13.0` — the
  sidecar reference is **hidden base64-encoded in a Secret**
  (`SIDECAR_IMAGE`) inside the release-asset `manifest.yaml`. Mirror it
  too or every instance pod fails to start the sidecar.
- Use the **release asset** manifest, never the repo-root manifest.yaml
  (that one points at `-testing:main`).

The sidecar (distroless, embeds barman 3.19.1) runs in **every**
Postgres pod; sidecar upgrades require pod restarts.

Install constraints: same namespace as the CNPG operator (typically
`cnpg-system`); the Service must keep the name `barman-cloud`
(certificate SAN — chart values warn "DO NOT CHANGE").

Helm chart exists despite stale docs claiming manifest/Kustomize-only:
`cloudnative-pg/charts` → `plugin-barman-cloud` (chart 0.7.0, appVersion
v0.13.0, kubeVersion ≥1.29).

**cert-manager**: the kubectl manifest hardcodes a selfsigned Issuer +
two Certificates for the CNPG-I mTLS. It is avoidable — CNPG-I only
needs TLS Secrets referenced via Service annotations
(`cnpg.io/pluginClientSecret` / `cnpg.io/pluginServerSecret` /
`cnpg.io/pluginPort`); the chart exposes
`certificate.createClientCertificate/createServerCertificate/
createIssuer: false` + `issuerName` for BYO certs. The BYO path is
documented but not verified end-to-end — lab-test before fleet rollout.

Compatibility: documented floor CNPG ≥1.26, "strongly recommend
≥1.27"; v0.13.0 is built against CNPG 1.29.1 modules. No formal
per-minor matrix — at execution time check for a plugin release built
against the running CNPG minor.

## Wiring a Cluster

```yaml
apiVersion: barmancloud.cnpg.io/v1
kind: ObjectStore
metadata:
  name: <app>-store
spec:
  configuration:            # = the old spec.backup.barmanObjectStore keys
    destinationPath: s3://backups/<app>
    endpointURL: https://<s3>
    s3Credentials:
      accessKeyId: {name: <secret>, key: ACCESS_KEY_ID}
      secretAccessKey: {name: <secret>, key: SECRET_ACCESS_KEY}
    wal: {compression: gzip}
    # serverName: ALWAYS leave empty here (API-compat relic) —
    # use the plugin parameter serverName instead
  retentionPolicy: "30d"    # TOP LEVEL — concepts.md showing it under
                            # configuration is wrong; the CRD is authoritative
---
# In the Cluster:
spec:
  plugins:
    - name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters:
        barmanObjectName: <app>-store
---
apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
spec:
  schedule: "0 0 2 * * *"
  cluster: {name: <app>-cnpg}
  method: plugin
  pluginConfiguration: {name: barman-cloud.cloudnative-pg.io}
```

Imperative: `kubectl cnpg backup <cluster> --method=plugin
--plugin-name=barman-cloud.cloudnative-pg.io`.

Restore/replica from a plugin store: `externalClusters[].plugin:
{name: barman-cloud.cloudnative-pg.io, parameters: {barmanObjectName:
…, serverName: <source-cluster>}}`.

Retention mechanics: recovery-window policy; obsolete backups are
deleted only **after the next backup completes** (sidecar runs
`barman-cloud-backup-delete` every `retentionPolicyIntervalSeconds`,
default 1800).

## If migrating an existing CNPG in-tree cluster (not the Zalando case)

The official procedure (plugin docs `migration.md`): install plugin →
create ObjectStore by copying the `barmanObjectStore` stanza (move
retentionPolicy to the ObjectStore) → **single atomic Cluster edit**
removing `spec.backup.barmanObjectStore` and adding the `plugins` entry
(triggers one rolling update) → flip ScheduledBackups to `method:
plugin` → update externalClusters. Backups made in-tree are fully
readable by the plugin (same layout, same bucket — officially stated).
This does NOT extend to WAL-G buckets.

## Monitoring the new chain

The plugin renames the backup metrics; the old ones silently go stale
(issue #8902 — an EDB engineer hit this in production monitoring):

| In-tree (goes stale) | Plugin |
|---|---|
| `cnpg_collector_last_available_backup_timestamp` | `barman_cloud_cloudnative_pg_io_last_available_backup_timestamp` |
| `cnpg_collector_last_failed_backup_timestamp` | `barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp` |
| `cnpg_collector_first_recoverability_point` | `barman_cloud_cloudnative_pg_io_first_recoverability_point` |

Rewrite backup-freshness alerts at cutover, and alert on **absence** of
the new metrics (the failure mode is silence, not a firing alert).

## Snapshot-only alternative (no object store)

For air-gapped clusters without S3: `spec.backup.volumeSnapshot:
{className, walClassName}` is viable. This loses PITR (WAL archiving
requires an object store — no snapshot-based WAL archive exists) and
retention automation (manual/external cleanup). Cold snapshots
(`online: false`) of a **primary** fence it (cluster read-only for the
duration) — snapshot a standby instead. Snapshot recovery without a WAL
archive is emulated via `recoveryTarget.targetImmediate`. Longhorn/
Rook-Ceph VolumeSnapshotClass behavior on RKE2 is not CNPG-certified —
lab-validate cross-node restore before relying on it.
