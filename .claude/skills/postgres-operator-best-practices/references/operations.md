# Day-2 operations

Verified **2026-08-25** against upstream at tag `v2.0.2`
(`docs/administrator.md`) plus an issue-tracker sweep the same day.

- [What triggers a rolling update of Spilo pods](#what-triggers-a-rolling-update-of-spilo-pods)
- [In-place major version upgrades](#in-place-major-version-upgrades)
- [Maintenance windows](#maintenance-windows)
- [Pod Disruption Budgets](#pod-disruption-budgets)
- [Delete protection](#delete-protection)
- [Password rotation in K8s secrets](#password-rotation-in-k8s-secrets)
- [Logical backups](#logical-backups)
- [Connection pooler](#connection-pooler)
- [Configuration hygiene worth auditing](#configuration-hygiene-worth-auditing)
- [Open issues worth knowing](#open-issues-worth-knowing)

## What triggers a rolling update of Spilo pods

The StatefulSet is **replaced** when annotations, `volumeClaimTemplates`, or
template volumes change. It is replaced **and rolled** when any of these
differ:

- container: name, ports, image, resources, env, envFrom, securityContext, volumeMounts
- pod template: labels, annotations, service account, securityContext, affinity, priority class, termination grace period

Changes to `SPILO_CONFIGURATION` under `bootstrap.dcs` are **excluded** from
the diff — they go through Patroni's REST API after a restart of all
instances.

The operator logs the *reason* for a rolling update at `info` and the full
StatefulSet spec diff at `debug` (view with `echo -e`; expect noise, since the
operator's PodTemplate is not defaulted the way Kubernetes will default it).

**Changing the operator's `docker_image` rolls every cluster that does not pin
its own.** A cluster manifest's `spec.dockerImage` wins; clusters without one
ride the operator default. Count the blast radius before touching it:

```bash
kubectl get pods -A -l application=spilo \
  -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}' | sort | uniq -c
```

`enable_lazy_spilo_upgrade: true` updates the StatefulSet without a rolling
update, deferring the switchover to whenever the pod next restarts — useful
when nodes rotate anyway, since it saves a switchover. Default is `false`,
which means an image change rolls immediately.

## In-place major version upgrades

- Requires `PGVERSION` in the pod env — `enable_pgversion_env_var`, default on
  since v1.6.0.
- `major_version_upgrade_mode`: `manual` (default — editing `version` in the
  manifest triggers it), `full` (the operator auto-upgrades anything below
  `minimal_major_version` up to `target_major_version`), `off`.
- **`full` creates drift**: the operator does not patch the version back into
  the manifest, so desired and actual state diverge.
- With `off`, upgrade by hand from inside the primary pod:
  `python3 /scripts/inplace_upgrade.py N`, where N is `numberOfInstances`.
  Usually well under a minute. **Irreversible once `pg_upgrade` is called.**
- The outcome is recorded as an annotation on the PostgreSQL resource:
  `last-major-upgrade-success` or `last-major-upgrade-failure`, valued with a
  timestamp. **A failure annotation blocks all retries on subsequent syncs** —
  clear it by reverting the manifest `version` back to the current version.
- Minor version upgrades mean a new Spilo image, hence a rolling update with a
  switchover (planned failover) — normally under 5s, but clients must
  reconnect.

## Maintenance windows

If `maintenanceWindows` are set (per-manifest, or globally from v2),
major-version-related pod rotation is deferred to those windows. They must be
**at least twice `resync_period`** (default 30m, so a 60m minimum window) or
the operator may never get a chance to act.

Note that `enable_maintenance_windows` becoming `true` constrains nothing on
its own — without defined `maintenance_windows` it is an empty switch.

## Pod Disruption Budgets

Two PDBs by default:

- **Primary PDB** — `MinAvailable: 1`, selector includes `spilo-role=master`
  when `pdb_master_label_selector` is on. Stops the last running instance
  being evicted.
- **Critical-operations PDB** — `MaxUnavailable: 0`, selector
  `critical-operation=true`. The operator labels all Spilo pods with this
  during a major version upgrade. Because the labelled set is usually empty,
  `MaxUnavailable: 0` expresses "freeze" without leaving an unsatisfiable
  budget — which used to keep `KubePdbNotEnoughHealthyPods` firing forever.
  Added in v1.15.0.

Both relax only when a cluster is scaled to 0 instances, or when
`enable_pod_disruption_budget` is off. Disabling avoids blocking managed-K8s
node upgrades, at the cost of longer database downtime.

## Delete protection

`delete_annotation_name_key` and `delete_annotation_date_key` (date in
`YYYY-MM-DD` form). **Unset by default, which means no delete protection at
all** — any `kubectl delete postgresql` takes the cluster. Either or both keys
can be used. Turn this on before it is needed, not after.

## Password rotation in K8s secrets

Off by default. `enable_password_rotation: true` makes the operator refresh
credentials in the K8s secrets of `LOGIN` roles that have one — manifest roles
and the default users from `preparedDatabases`. Interval:
`password_rotation_interval`, default `90` days, minimum 1.

**Rotation creates a new role, it does not change the old one's password.** On
each rotation the secret's username *and* password are replaced, pointing at a
freshly created user named after the original role plus the rotation date in
`YYMMDD` form. Privileges are inherited, which is the trap: **migration scripts
must still grant and revoke against the original role**, never the dated one.
The next rotation timestamp (RFC 3339, UTC) is written into the secret too.

Four categories are deliberately excluded — infrastructure role secrets
(rotation belongs to the infrastructure), Team API roles using OAuth2/JWT (no
secret exists), database owners (object ownership cannot be inherited), and the
system users `postgres`, `standby` and `pooler`.

Shortening the interval does not take effect immediately: it only applies once
the already-scheduled next rotation date is further away than the new interval.

## Logical backups

Per-cluster, off by default — set `enableLogicalBackup: true` in the cluster
manifest. The operator manages a K8s CronJob that spawns a batch job running a
single pod; it updates the CronJob during Sync when the schedule changes, using
the job name as the identifier.

**These are not a substitute for basebackups and WAL archiving.** The operator
cannot restore them automatically and they give no point-in-time recovery —
treat them as SQL snapshots for reloading into an empty test cluster. The
stock image runs `pg_dumpall` (which needs superuser, and runs on a replica
where possible) and uploads compressed, encrypted output to S3.

Four operational consequences worth planning for:

- **The operator never removes old backups.** Retention is somebody else's job.
- **Monitor the CronJob separately.** K8s cron jobs can miss runs, and upstream
  states explicitly that such monitoring is outside operator responsibility.
- **RBAC must allow `cronjobs` in the `batch` API group** for the operator
  service account, or the feature silently does nothing.
- A custom image must tolerate pod restarts and simultaneous invocations of the
  cron job. Pod-template resources default to the Spilo pod values when unset.

## Connection pooler

Off by default. Two independent flags, either usable alone:

```yaml
spec:
  enableConnectionPooler: true          # pooler in front of the master
  enableReplicaConnectionPooler: true   # pooler in front of the replicas
```

The master pooler is reachable on its own service, `{cluster-name}-pooler`.
Per-cluster tuning goes under `spec.connectionPooler` (`numberOfInstances`,
`mode: session|transaction`, `schema`, `user`, `resources`); the default
configuration is adequate for most deployments.

Two behaviours that surprise: the `connectionPooler` section alone is enough —
`enableConnectionPooler` is not required when it is present — but the flag
still works as an on/off switch that **removes the pooler while keeping its
configuration**. And in v2 the pooler image moved off
`registry.opensource.zalan.do` to
`ghcr.io/zalando/postgres-operator/pgbouncer:<ver>`, so any pinned pooler image
from a v1 values file must be re-pointed.

Note the pooler interacts with the scram bug in `upgrade-v1-v2.md` (#3170):
pgbouncer doing SCRAM pass-through with `auth_query` breaks when the operator
rewrites role passwords every sync cycle.

## Configuration hygiene worth auditing

Four defaults that commonly sit wrong in long-lived deployments:

- **No delete protection.** See above. The single highest-value flag most
  deployments leave off.
- **`enable_patroni_failsafe_mode: false`.** With it off, a DCS outage can
  demote a healthy primary. Enable it *before* a DCS migration, not after.
- **Plaintext S3 credentials in values files.** `logical_backup_s3_access_key_id`
  and `logical_backup_s3_secret_access_key` are frequently pasted into values
  files (and again as env in the UI chart's values). Upstream supports
  `logical_backup_cronjob_environment_secret` instead. Related: **#3161 (open)**
  — credentials are exposed as env vars rather than read-only mounts.
- **`workers` below the cluster count.** See `upgrade-v1-v2.md` — this turns a
  routine upgrade into a repeated-rolling cascade.

## Open issues worth knowing

State verified 2026-08-25.

- **#3163 (open)** — the v2 upgrade cascade: slow `/readyz`, concurrent
  operators, worker starvation. Covered in `upgrade-v1-v2.md`.
- **#3161 (open)** — credentials exposed as env vars rather than read-only
  mounts.
- **#3151 (open)** — the operator skips a cluster update when the controller
  ID changes. Matters for the per-cluster DCS migration path.
- **#3157 (open)** — the UI cannot select a namespace for new clusters and
  does not display clusters from other namespaces.
- **#3168 (open)** — proposal to protect operator CRDs with a finalizer.
- **#3162 (closed)** — secrets were still deleted with
  `enable_secrets_deletion: false` combined with `enable_owner_references:
  true`. Worth knowing if that combination is ever adopted.

The most-discussed open issues are all long-standing feature requests
(monitoring #264 from 2018, Vault integration #847, custom collation #375);
none bear on upgrades or day-2 operations.

## Working method

- **Verify against the cluster, not the release notes.** Release notes say
  what changed; only the live CRD and a rendered template say what will happen
  to a given deployment. Several release-note-derived fears turn out not to
  apply — see the wrong expectations in `upgrade-v1-v2.md`.
- **Render and diff before upgrading.** `helm template ... --validate` both
  versions and diff. A five-line rendered diff is a safe upgrade; a fifty-line
  one needs reading.
- **Verify on settled state.** The operator syncs on `resync_period` (default
  30m) and repairs on `repair_period` (5m). A snapshot taken mid-reconcile
  proves nothing.
