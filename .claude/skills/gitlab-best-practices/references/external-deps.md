# External dependencies — PostgreSQL, Redis, object storage, pooling

From chart 10.0 these are **mandatory**, not optional. Everything here is the
part of a GitLab install that GitLab does not run for you.

**Tag convention.** Untagged claims were verified against a primary source or a
live install on 2026-08-29. **[A]** = reported but not independently
re-verified — re-check before acting.

## Table of contents
- [PostgreSQL](#postgresql)
- [Redis](#redis)
- [Object storage, and non-AWS S3](#object-storage-and-non-aws-s3)
- [Connection pooling](#connection-pooling)

## PostgreSQL

### The version window is the whole upgrade plan

| GitLab | Chart | PG minimum | PG maximum |
|---|---|---|---|
| 19.x | 10.x | **17.x** | **17.x** |
| 18.x | 9.x | 16.5 | 17.x |
| 17.x | 8.x | 14.14 | 16.x |

Read the 19.x row carefully: minimum *and* maximum are 17.x. There is no
running ahead to PG 18 to get it out of the way — PG 18 is opt-in from 19.3,
default from 19.10, minimum at 20.0. **[A]**

**18.x already tolerates PG 17, and that overlap is the entire safe path:
upgrade PostgreSQL to 17 while still on 18.x, then upgrade GitLab.** Doing the
database first is not a preference; it is the only ordering with a supported
resting point on both sides.

The 19.0 requirement is marked **"Affects: All installation methods"** — not
Linux-package-only, despite reading that way.

### Extensions — GitLab will not install them for you

| Extension | Minimum GitLab version | Type |
|---|---|---|
| `amcheck` | **18.4** | Required |
| `btree_gist` | 13.1 | Required |
| `pg_trgm` | 8.6 | Required |
| `plpgsql` | 11.7 | Required |
| `pg_stat_statements` | — | Recommended |

Two traps:

1. **`amcheck` became required at 18.4** and nothing fails loudly without it.
2. **Migrations do not install extensions.** Installing them needs superuser,
   which the GitLab DB role usually is not: *"you must install extensions
   manually before upgrading GitLab."*

```sql
SELECT extname FROM pg_extension ORDER BY 1;
-- then, as superuser, per missing extension:
CREATE EXTENSION IF NOT EXISTS amcheck;
```

**The extensions docs page does not carry this table** — it defers to
`doc/install/requirements.md`. Fetching the extensions page and grepping for
`amcheck` returns nothing, which reads as "not required" if you stop there.

### Major-version upgrades of the database itself

`pg_upgrade` in place is the documented route. Two non-negotiables: **every
GitLab component must be restarted afterwards** (the upgrade invalidates
existing connections), and **`ANALYZE` is mandatory** — `pg_upgrade` does not
carry optimizer statistics across, and skipping it is a named cause of
post-upgrade CPU burn. **[A]**

Operator-managed databases: the mechanics are the operator's, not GitLab's.
For the Zalando postgres-operator — in-place major upgrades, the
`last-major-upgrade-success/failure` annotations that latch and block retries,
the Spilo image pin that must move in the same change, and sizing — use
**`postgres-operator-best-practices`**. Do not re-derive them here.

### Scaling GitLab down for a database cutover

**Four deployments hold PostgreSQL credentials, not two:** webservice,
sidekiq, **gitlab-exporter** and **toolbox**. The exporter is the routine miss
— it polls the database continuously for metrics and will hammer a database
mid-upgrade. KAS and registry carry no PG credentials.

Derive the list rather than naming the obvious two: grep the workloads for the
DB secret or host.

Three things that behave differently than expected:

- **`desired=0` is not quiesced, and pod count is not the real gate.** The
  check that proves an app let go of a database runs on the database:
  ```sql
  SELECT usename, count(*) FROM pg_stat_activity
  WHERE datname='<db>' GROUP BY usename;
  ```
  Replica count proves scheduling; connections prove quiescence.
- **An HPA does not fight a scale-to-zero.** At 0 replicas the webservice HPA
  reports `ScalingActive=False (ScalingDisabled)` and stands down despite
  `minReplicas: 2`. No need to suspend or delete it. (Scaling *up* from zero is
  the direction that needs an alpha feature gate.)
- **A configured grace period is a budget, not a duration.** Sidekiq with
  `terminationGracePeriodSeconds: 120` drained in ~22s with no long jobs in
  flight. Gate a runbook on *pods gone*, never on a fixed wait.

**Skip the ritual restart afterwards.** Pods recreated from 0 cannot be holding
a pre-upgrade connection; a `rollout restart` verifies nothing.

**Do not validate with `Project.first`.** On most instances that is the
auto-created self-monitoring project, which legitimately has no repository — it
reads as a Gitaly failure when nothing is wrong. Walk the projects and count
repos with commits instead.

## Redis

- Minimum **7.0**, recommended **7.2**. Valkey 7.2 is a first-class supported
  alternative. Redis 6 support was removed in 19.0.
- **Sentinel is fully supported** and is the documented HA pattern.
  `global.redis.host` must be the sentinel **master group name** (e.g.
  `mymaster`), *not* a host, with `global.redis.sentinels[N].host/.port`
  listing the sentinels. **[A]**
- The chart can split Redis by workload class (cache, queues, shared_state,
  actioncable). Cache-like classes may use LRU eviction; **queues and
  shared_state must never be LRU** — they hold data, not cache. **[A]**
- **`gitlab-exporter` ignoring Sentinel is a *fixed* bug — do not plan around
  it.** The exporter connected directly to `<host>:6379` and threw
  `SocketError`; charts issue #3813, and its companion #5376 (Sentinel config
  for Sidekiq probes), are both **closed at milestone 17.1**. Any 18.x/19.x
  install already carries the fix. Smoke-test metrics against the real Sentinel
  topology rather than treating this as a live limitation — several secondary
  sources still describe it as open.

Migrating a Bitnami Redis Sentinel deployment to Valkey: **`redis-to-valkey`**.

## Object storage, and non-AWS S3

- The **consolidated form** (one connection shared across object types) is the
  current recommended shape. The legacy per-type form remains **mandatory for
  backups and the container registry**, which do not support consolidated.
  **[A]** A values file legitimately carrying both styles at once is correct,
  not drift.
- Knobs that exist for non-AWS S3 implementations: **[A]**
  - `path_style: true` — path-style rather than virtual-hosted bucket
    addressing.
  - `aws_signature_version: 2` — where v4 is not fully implemented.
  - `enable_signature_v4_streaming: false` — where chunked signature streaming
    is rejected.
- Known non-AWS failure modes: **[A]** a missing "Upload Part Copy" API → 404s
  on multipart (mitigate by disabling the `s3_multithreaded_uploads` feature
  flag); ETag ≠ MD5 mismatches, worse with encryption; and missing bucket
  **CORS** causing browser-side file loads to fail.
- The container registry uses **Docker Distribution's own S3 driver**, not
  GitLab's object-storage layer. Registry S3 config is tuned separately.

### The `s3_v2` scare — check driver registration, not release-note prose

19.0's notes read as though an `s3:` registry storage stanza must be migrated
to `s3_v2`. **It must not.** In registry `v4.40.2-gitlab` the legacy driver
package registers all three names onto the same v2 factory:

```go
factory.Register(common.V1DriverName, new(v2.S3DriverFactory))
// upstream comment: "legacy aliases — they now resolve to the v2 implementation"
```

An `s3:` stanza keeps working, transparently served by the SDK-v2 code path.
Verified against `registry/storage/driver/s3-aws/s3.go` at tag `v4.40.2-gitlab`.

**Generalise it:** when release notes say a driver was replaced, read the
driver's registration table before planning a migration.

## Connection pooling

- Prepared statements collide with transaction-mode pooling →
  `PG::DuplicatePstatement` on webservice startup. Charts issue #1444, which
  requested a chart flag to disable prepared statements, is **closed** — so
  handle it via `database.yml` overrides or session-mode pooling rather than
  waiting for a values key. **[A]** for the collision itself.
- **"Do not back up or restore GitLab through a PgBouncer connection. These
  tasks must bypass PgBouncer and connect directly to the PostgreSQL primary
  database node, or they cause a GitLab outage."** **[A]**
