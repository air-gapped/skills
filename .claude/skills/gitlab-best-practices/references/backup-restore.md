# Backup and restore with external dependencies

The half of an upgrade plan that `helm rollback` cannot cover.

**Tag convention.** Untagged claims were verified against a primary source or a
live install on 2026-08-29. **[A]** = reported but not independently
re-verified — re-check before acting.

## Mechanics

- Backup and restore run from the **toolbox pod**: `backup-utility`, restore via
  `backup-utility --restore -t <backup_ID>`. It shells out to **`s3cmd` by
  default** for bucket copy (`--s3tool awscli` to switch). **[A]**
- Components skip individually, one flag each:
  `backup-utility --skip db --skip lfs`. **[A]**
- **Restore requires the same GitLab version as the backup.** **[A]**
- **Never back up or restore through PgBouncer** → `references/external-deps.md`.

## Secrets are not in the backup, and without them the backup is useless

The rationale is explicit: *"Storing encrypted information in the same location
as its key defeats the purpose of using encryption."* **[A]**

For the chart this is the `gitlab-rails-secret` Secret:

```bash
kubectl get secret <release>-rails-secret \
  -o jsonpath="{.data['secrets\.yml']}" | base64 -d
```

Store it outside the cluster and outside any repo, mode 600. Without it, CI/CD
variables, runner tokens and 2FA data are undecryptable after restore — and the
documented recovery for broken 2FA is *"disable 2FA for everyone"*. **[A]**

Confirm the captured secret parses and carries the four that matter —
`secret_key_base`, `db_key_base`, `otp_key_base`,
`encrypted_settings_key_base` — plus the `active_record_encryption_*` keys on
modern versions.

**`gitlab-rake gitlab:doctor:secrets` detects undecryptable values but does not
repair them.** Run it *before* an upgrade: it walks every encrypted model and
proves the secrets you are about to back up actually decrypt what is in the
database — the half of a restore that a database dump cannot tell you about. A
healthy instance ends `Total: 0 row(s) affected`.

## Rehearsing the restore — three things that only appear when you try

Measured on a real restore of an operator-taken `pg_dumpall` artifact into a
throwaway PostgreSQL. Row counts matched production exactly across projects,
users, namespaces, members, merge_requests, personal_access_tokens and issues —
but only after two failures that are in no documentation.

**1. A `pg_dumpall` stream rewrites the superuser password partway through, and
then `psql` cannot reconnect.** The dump contains `ALTER ROLE ... PASSWORD` for
every role, including the one authenticating. Restoring into a target whose
`postgres` password differs from production dies at the first `\connect`:

```
ERROR:  role "postgres" already exists                                <- benign
\connect: FATAL: password authentication failed for user "postgres"   <- fatal
```

Everything after that point silently does not load, and `psql` exits non-zero
with two stderr lines to show for it. Fixes: restore into a target created with
the *same* credentials (an operator-recreated cluster — which is the real
rollback path), stand the rehearsal target up with trust auth, or dump with
`--no-role-passwords`. **A rehearsal that skips this does not resemble the real
restore, and a real restore into a freshly-provisioned cluster will hit it.**

**2. The rehearsal target must be the same image as production.** Restoring a
Spilo dump into a vanilla `postgres:17` produced 87 errors — `extension "X" is
not available` (pg_stat_kcache, set_user, pg_cron, plpython3u, pg_auth_mon),
`schema "X" does not exist`, plus cascading failures from those. The GitLab
database itself restored fine, so this reads as success or failure depending on
which line you happen to read.

**3. A table-count match does not prove the instance boots.** It proves the dump
loads and the data is there. Booting additionally requires the secrets to line
up with the restored rows. Prove the halves separately — restore for the data,
`doctor:secrets` for the keys — unless you are willing to wire a full GitLab at
the restored database.

## Consistency is the real problem with external state

GitLab's own dump coordinates a PostgreSQL snapshot across databases. **Nothing
coordinates GitLab's backup with an operator's database backup.** If the
database is dumped by a Postgres operator at 02:00 and repositories are backed
up at 03:00, there is no consistent restore point.

Either drive both from one orchestration, or accept the window and document it.

## Gitaly

- Server-side repository backups let the Gitaly node stream directly to object
  storage. **[A]**
- Gitaly **Cluster** does not support snapshot backups (Praefect DB desyncs).
  A **single-replica non-Cluster** Gitaly is not covered by that restriction —
  but a restored snapshot still needs `git fsck` verification, and repositories
  must not be copied during concurrent writes. **[A]**

## Open question worth settling empirically

Whether `backup-utility`'s `db` component behaves safely — succeeds, fails, or
silently skips — when PostgreSQL is external and operator-managed. **The chart
docs are simply silent.** Determine it on a rehearsal before relying on it, and
do not assume `--skip db` is either required or harmless.
