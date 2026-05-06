# Keycloak: upgrade strategy, backup, and disaster recovery

For Keycloak 26.6.x. The official upgrade guide is at `https://www.keycloak.org/docs/latest/upgrading/index.html` — that's the source of truth for breaking changes per version.

## TOC
1. [Upgrade matrix](#matrix)
2. [Zero-downtime patch updates](#zdt)
3. [Pre-upgrade checklist](#prechecks)
4. [Realm export/import](#export-import)
5. [Database backup (the actual backup)](#db-backup)
6. [Disaster recovery](#dr)
7. [Rollback](#rollback)

---

## <a id="matrix"></a>1. Upgrade matrix

Keycloak's stated support: each minor release supersedes the previous within ~3 months. **Skip-version upgrades are not supported** for normal upgrades — go one minor at a time (26.4 → 26.5 → 26.6, not 26.4 → 26.6 directly). The DB migrations assume sequential application.

For RHBK (Red Hat build of Keycloak): LTS lines have multi-year support; 26.0 LTS gets backports of security fixes from upstream. If you can't track upstream's quarterly cadence, run RHBK LTS.

| From      | To        | Path                                                               |
|-----------|-----------|--------------------------------------------------------------------|
| 26.6.0    | 26.6.1    | Patch — Auto strategy, zero-downtime.                              |
| 26.5.x    | 26.6.x    | Minor — Auto strategy possible, but read the upgrade guide first.  |
| 26.x      | 26.6.x    | One minor at a time. Confirm each interim version comes up clean.   |
| 25.x      | 26.x      | Cross-major — `Recreate` strategy. Brief downtime. Read the migration guide carefully — the major has retired flags (e.g. `--proxy edge`, `KEYCLOAK_ADMIN`). |
| 24.x      | 25.x → 26.x | Don't try to leap. Step through 25.x first.                       |
| < 24.x    | 26.x       | These ran the legacy WildFly distribution. Migration is non-trivial: re-architect, don't migrate in place. |

The release-notes body for each version (`gh release view <tag> --repo keycloak/keycloak --json body --jq '.body'`) lists "Migration Changes" inline — read those before you upgrade, not after.

---

## <a id="zdt"></a>2. Zero-downtime patch updates

Promoted to supported in 26.6 (`spec.update.strategy: Auto`). The mechanism:

- The operator probes the new image's protocol version against the running pods.
- If wire-compatible, it does a rolling update (pods leave the JGroups cluster gracefully, new pods join, sessions migrate).
- If not, falls back to `Recreate` (downtime). You'll see this in the operator logs.

**Patch upgrades within a minor stream** (26.6.0 → 26.6.1): always wire-compatible, always rolling. Use Auto.

**Minor upgrades** (26.5.x → 26.6.x): usually wire-compatible. Test in staging with `Auto`; the operator will fall back if not.

**Major upgrades** (25.x → 26.x): generally not wire-compatible. Plan for downtime.

Set `spec.update.strategy: Explicit` and bump `spec.update.revision` if you want to manually gate updates: the operator only acts when the revision changes.

---

## <a id="prechecks"></a>3. Pre-upgrade checklist

1. **Read the migration guide for every minor version you're crossing.** Not optional. Things like option renames, default-value changes, and feature-flag promotions live there.
2. **Back up the Postgres database** with WAL archiving, not just a `pg_dump`. CloudNativePG handles this; if you're on RDS, snapshot + enable PITR.
3. **Realm export for portability**, NOT as a backup (see §4). `kc.sh export --dir /tmp/export --users different_files` per realm.
4. **Run a dry-run upgrade in staging** with realistic data. Specifically check:
   - Liquibase migration completes
   - Existing client policies still apply
   - Users can log in
   - Refresh tokens issued before the upgrade still work
   - Federated IdPs still work (sync hash signatures, etc.)
5. **Take note of cache topology** — if you have external Infinispan, the Infinispan version must be compatible with the new Keycloak version. The HA guide documents the matrix.
6. **Plan the rollback story** before starting (see §7). It's harder than the upgrade.
7. **For 26.5 → 26.6 specifically**: review usage of `KEYCLOAK_ADMIN` (gone since 26.0 but re-confirmable) and any `--proxy edge|reencrypt|passthrough` (gone since 26.4). If you've been on 26.x for a while, this should already be clean.

---

## <a id="export-import"></a>4. Realm export/import

`kc.sh export` writes realm config to JSON. Useful for:
- Migrating between deployments (dev → staging → prod)
- Versioning realm config in git
- Pre-upgrade snapshot for portability

Modes:

```bash
# Single realm to a single file
kc.sh export --realm myrealm --file /tmp/myrealm.json

# All realms to a directory, with users in separate per-chunk files
kc.sh export --dir /tmp/export --users different_files

# Skip users entirely
kc.sh export --dir /tmp/export --users skip
```

`--users` modes:
- `skip` — no users
- `realm_file` — users in the realm JSON file (only OK for tiny realms)
- `same_file` — users in same files as realm but separated
- `different_files` — separate user-chunk files (`realm-users-N.json`). **Use this for production realms.**
- `same_files_per_user` — one file per user (rarely useful)

### What's NOT in a realm export

- **Federated users** (LDAP, custom UserStorageProvider). Those live in the upstream system.
- **Event history** (login events, admin events).
- **Sessions** (active sessions are runtime state, not realm config).
- **Realm signing keys' private material** — the JWKS public keys are exported, but the operator needs to set up keys after import.
- **Database-resident secrets in plain form** — exported in encrypted form using the realm master encryption key. If you import to a different deployment with a different master key, secrets become un-decryptable. Plan key migration if moving across deployments.

### Importing

```bash
kc.sh import --dir /tmp/export
```

Or via the operator's `KeycloakRealmImport` CR. Either way, **import is destructive** for the target realm: existing config is replaced. There's no merge mode.

For operational changes after deployment, use `kcadm.sh` or terraform-provider-keycloak — both edit incrementally without blowing away existing state.

---

## <a id="db-backup"></a>5. Database backup (the actual backup)

The Postgres database is the source of truth. This is what you back up.

Tools by environment:

| Environment              | Tool                                       | Notes                                                                  |
|--------------------------|--------------------------------------------|-------------------------------------------------------------------------|
| Kubernetes / CloudNativePG | `cnpg backup` + S3 WAL archive             | Recommended K8s pattern. PITR within retention window.                 |
| Kubernetes / Crunchy Postgres | pgBackRest (built-in)                      | Continuous WAL + scheduled full backups.                               |
| RDS / Aurora             | Automated backups + manual snapshots       | PITR window configurable; 35 days max for automated.                   |
| Self-managed Postgres    | pgBackRest, WAL-G, or Barman               | All do continuous WAL archiving + PITR.                                |
| Last resort              | `pg_dump` cron                             | Restore-only; loses anything since last dump. **Not real backup.**     |

**Minimum**: daily full backup + continuous WAL archiving. Retention: 30+ days for compliance. Test restoration quarterly — a backup that has never been restored is not a backup.

### Database data-at-rest encryption (26.6.1)

The new application-layer encryption (`--db-data-encryption-*`) encrypts a subset of stored secrets. This complicates restore: the master encryption key must be available to the restored instance, otherwise stored secrets become un-decryptable. Treat the master encryption key as critical material — back it up separately, store in a HSM/KMS, rotate per your compliance schedule.

---

## <a id="dr"></a>6. Disaster recovery

Failure scenarios and what handles each:

| Failure                           | Handled by                                                |
|-----------------------------------|-----------------------------------------------------------|
| Single pod crash                  | K8s restart + JGroups peer re-sync; bounded session loss for users on that pod. |
| Node failure                      | PodDisruptionBudget + podAntiAffinity ensure other pods on other nodes survive. |
| AZ failure                        | Multi-AZ Postgres + multi-AZ K8s (3 replicas across 3 AZs); session loss bounded to AZ. |
| Region failure                    | Multi-region active-passive (DB cross-region replication; warm Keycloak in the second region) or active-active (external Infinispan + cross-site replication). |
| Database corruption / accidental DROP | PITR to a point before the corruption; replay events from there. |
| Cluster compromise                | Restore DB to a clean point + rotate all signing keys + force re-login. |

**Test your DR runbook.** A common pattern: quarterly game-day exercise — restore a snapshot of prod into an isolated staging cluster, validate users can log in, validate clients still work. If you can't do this, your DR plan isn't real.

---

## <a id="rollback"></a>7. Rollback

Rolling back across DB schema migrations is the hard part. Liquibase doesn't generate down-migrations automatically.

For patch upgrades (26.6.0 → 26.6.1 → rollback to 26.6.0): usually safe; patches don't change schema. Roll back the image.

For minor/major upgrades that ran a schema migration: **forward-only** is the default operational stance. To roll back you'd need to:
1. Restore the DB from a pre-upgrade backup.
2. Roll back the image.
3. Lose all changes (user creations, login events, …) made since the upgrade.

Plan accordingly: always have a pre-upgrade snapshot, decide upfront how much data loss is acceptable for a rollback, and do the upgrade during a maintenance window so the loss window is small.

If forward-only is mandatory (e.g. for compliance reasons you can't lose audit events): test the upgrade *exhaustively* in staging with prod-shaped data, and have a "fix-forward" plan (apply patches, work around bugs in production, communicate downtime if needed) instead of a rollback plan.
