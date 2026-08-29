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

Rehearse before relying on the artifact. Row counts matching production across
projects, users, namespaces, members, merge_requests, personal_access_tokens and
issues is achievable — after clearing two failures that appear in no
documentation.

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

## Performance and scale — the toolbox path does not scale

**Do not tune the toolbox backup. Split the backup by data class instead.** The
chart's default path pulls every blob through the toolbox pod on every run, and
the three optimizations a reader reaches for first are all unavailable on that
path.

### The data path

`backup-utility`'s `backup()`: `gitlab:backup:db:create` → `gitlab:backup:repo:create`
(repos stream **through** the pod) → **eleven** object-storage backends
(registry, uploads, artifacts, lfs, packages, external_diffs, terraform_state,
pages, ci_secure_files, agent_plan_content, ci_catalog_bundles) → `pack_backup`
(one `tar` over all of it) → upload.

Per bucket, from `object_storage_backup.rb`:

```
s3cmd --stop-on-error --delete-removed --exclude 'tmp/builds/*' sync s3://<bucket>/ /srv/gitlab/tmp/<name>/
tar -cf <name>.tar.gz -I gzip -C /srv/gitlab/tmp/<name> .
```

Consequences: every blob makes a full round trip object storage → pod disk →
gzip → tar.gz → tarred again into the archive → uploaded back. Nothing is
incremental, nothing is server-side, and local scratch must hold roughly **2x
total data size**.

### Three optimizations that do not apply here

| Technique | Why it fails on the chart's blob path |
|---|---|
| `COMPRESS_CMD` (pigz/zstd) | reaches the **Rake** tasks only. `object_storage_backup.rb` hardcodes `gzip_cmd = 'gzip' + (ENV['GZIP_RSYNCABLE'] == 'yes' ? ' --rsyncable' : '')`. No hook — the blob half is single-threaded gzip |
| `SKIP=tar` | docs, verbatim: *"It is not possible to skip the tar creation when using object storage for backups."* |
| Incremental | `backup-utility` has no `--incremental` and no `PREVIOUS_BACKUP`. Incremental exists in the Rake layer; the chart wrapper cannot reach it. Upstream docs confirm: *"Incremental repository backup is not supported by `backup-utility` with server-side repository backup"* (charts#3421, **closed unimplemented**) |

### The supported answer: split by data class

| Data | Back it up with |
|---|---|
| PostgreSQL | the database's own tooling, **not** `pg_dump` via toolbox — `pg_dump` is documented as *"not appropriate for databases over 100 GB"* |
| Blobs + registry | bucket-to-bucket replication at the storage layer |
| Git repositories | **Gitaly server-side backups** (chart support since GitLab 17.0) |

Upstream's Helm recipe for `gitlab.toolbox.backups.cron.extraArgs`, verbatim:

```
--repositories-server-side --skip db --skip repositories --skip uploads --skip builds
--skip artifacts --skip pages --skip lfs --skip terraform_state --skip registry
--skip packages --skip ci_secure_files
```

### DANGER: that documented cron recipe backs up no repositories

**Delete `--skip repositories` from it.** As written, the recipe silently
produces scheduled backups containing **no Git repository data**, and the
failure is only discovered at restore time.

The two flags are mutually exclusive and skip wins. From `backup-utility`:

```bash
--repositories-server-side)
  export REPOSITORIES_SERVER_SIDE="true"      # sets a variable, nothing else
```

```bash
if ! [[ ${skipped_via_flag[@]} =~ "repositories" ]]; then
  gitlab-rake gitlab:backup:repo:create        # the only consumer of that variable
fi
```

With both flags the rake task is **never invoked**, so
`REPOSITORIES_SERVER_SIDE=true` is exported into a process that never runs. No
repository backup is produced — server-side or otherwise.

The one-off full-backup example on the same upstream page omits
`--skip repositories` and is correct. **Use the flag set from that example for
cron as well**, and verify a scheduled run actually lands data in the Gitaly
backup bucket before trusting the schedule.

**Omnibus asymmetry — the reason copied commands do not help.** On Omnibus,
`SKIP=db` alone suffices because the Rake task does not back up object storage
at all. **The chart adds blob backup on top**, so every blob component must be
skipped individually.

### Gitaly server-side backups — three parts, docs cover one

**1. Destination** — `gitlab.gitaly.backup.goCloudUrl`, rendered by the chart
helper into a `[backup] go_cloud_url` entry in Gitaly's config. **Quote the
value**; an unquoted `&` is ambiguous in YAML.

```yaml
gitlab:
  gitaly:
    backup:
      goCloudUrl: "s3://<bucket>?region=us-east-1&endpoint=https://s3.example.com"
```

**2. Credentials** — the URL carries none. Gitaly reads standard AWS env vars:

```yaml
gitlab:
  gitaly:
    extraEnvFrom:
      AWS_ACCESS_KEY_ID:
        secretKeyRef: { name: <secret>, key: <key> }
      AWS_SECRET_ACCESS_KEY:
        secretKeyRef: { name: <secret>, key: <key> }
```

`secretKeyRef` takes secret name **and** key name as free-form fields, so any
existing secret works — **the key does not need a particular name**, and a
differently-shaped secret is not a blocker.

**3. Invocation** — `--repositories-server-side`, on the command or in
`cron.extraArgs`. **Gitaly does not back itself up.**

**Name trap:** `gitlab.gitaly.bundleUri.goCloudUrl` is a *different* feature
(serving repo bundles to clients on clone). Do not confuse the two keys.

### Non-AWS S3 works — and silently defeats Object Lock

Gitaly's `internal/backup/sink.go` (gocloud.dev s3blob) treats third-party S3 as
a deliberate target, so `endpoint` is a supported query parameter. But:

> "// This maintains compatibility with third-party S3 providers that don't support AWS SDK checksums.
> // When no custom endpoint is configured (i.e., using AWS S3 directly), checksums are left enabled
> // as they work correctly and are required for features like Object Lock."

`withS3DefaultChecksumCalculation` sets
`request_checksum_calculation=when_required` **whenever a custom `endpoint` is
present** and the parameter is not already specified.

**That is exactly the setting that breaks S3 Object Lock (WORM), which needs
`when_supported`.** Hardening a backup bucket with Object Lock on
S3-compatible storage requires overriding it explicitly in the URL — the
compatibility default silently defeats the immutability control.

**[?] Unverified:** some S3-compatible backends may additionally need path-style
addressing (`use_path_style`). Reading the sink proves `endpoint` is honoured;
it does not prove any given provider round-trips. Test before relying on it.

### Give Gitaly its own object-storage credential

Gitaly stores repositories on a PersistentVolume and ships with **no S3
credentials at all**. Server-side backups are the only reason it ever touches
object storage.

- Issue it a **dedicated** object-storage identity, shared with nothing else —
  not Rails (LFS/artifacts/uploads/packages), the registry, or the runner cache,
  each of which has its own.
- Scope it **read+write but not delete**, so a compromised GitLab cannot destroy
  its own backups. Run retention from a bucket lifecycle rule or a separate
  admin credential.
- Combine with versioning and Object Lock — subject to the checksum trap above.

### Quick wins, by payoff

1. **`--skip` the large blob components** and replicate those buckets at the
   storage layer. Removes the round trip entirely. Biggest lever.
2. **`--s3tool awscli`** — the default is `s3cmd`, which is single-threaded;
   awscli parallelises, and avoids a known 404 `NoSuchKey` crash on artifacts
   buckets (charts#3338). `--s3tool-backup` and `--s3tool-data` set it
   separately for the two paths. On non-AWS S3 this may need
   `AWS_REQUEST_CHECKSUM_CALCULATION: WHEN_REQUIRED` in toolbox `extraEnv`.
3. **`--repositories-server-side`** once the Gitaly bucket exists.
4. **`GITLAB_BACKUP_MAX_CONCURRENCY`** in toolbox `extraEnv` — defaults to
   logical CPU count, so it only helps with a real CPU request on the pod.
5. **Size the toolbox**: ~2x data in local scratch, CPU-bound in gzip
   (charts#5151).

### Do not plan around `gitlab-backup-cli`

The strategic replacement ("Unified Backup") is real and actively worked, but
**undocumented and not GA**. `gitlab#477791` — an issue that merely restores the
documentation link — carries `missed:` labels for **every release from 17.7
through 19.3**.

**Generalisable maturity signal: read the `missed:` label chain, not the
milestone.** A milestone says where something is aimed; twenty consecutive
`missed:` labels say what actually happens.

## Open question worth settling empirically

Whether `backup-utility`'s `db` component behaves safely — succeeds, fails, or
silently skips — when PostgreSQL is external and operator-managed. **The chart
docs are simply silent.** Determine it on a rehearsal before relying on it, and
do not assume `--skip db` is either required or harmless.
