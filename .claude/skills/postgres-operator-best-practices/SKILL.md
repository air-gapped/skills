---
name: postgres-operator-best-practices
description: >-
  Run, configure, upgrade and troubleshoot the Zalando postgres-operator
  (acid.zalan.do `postgresql` CRs, Spilo, Patroni, WAL-G) on Kubernetes.
  Core knowledge: the v1.x -> v2.x major upgrade and its three changed
  defaults that bite silently (`kubernetes_use_configmaps` true,
  spilo-17 -> spilo-18, scram-sha-256 password encryption); the Patroni
  DCS living in deprecated v1 Endpoints and the split-brain hazard in
  switching to ConfigMaps; Helm never updating the CRDs; exactly which
  spec changes trigger a rolling update of Spilo pods; in-place major
  version upgrades and their success/failure annotations; PDBs, delete
  protection, password rotation, logical backups, maintenance windows.
when_to_use: >-
  Use for any task touching the Zalando postgres-operator: "upgrade the
  postgres operator", "postgres-operator 2.0", "zalando postgres helm
  values", "OperatorConfiguration", "acid.zalan.do", "spilo image bump",
  "patroni leader election", "kubernetes_use_configmaps", "v1 Endpoints
  is deprecated warning", "postgres major version upgrade in place",
  "why did my postgres pods roll", "postgresql CR stuck", "logical
  backup cronjob", "connection pooler / pgbouncer". Symptoms: unknown
  field errors after a chart bump, config options silently ignored,
  unexpected switchovers, `last-major-upgrade-failure` annotation,
  clusters not syncing, PDB blocking a node drain.
  NOT for migrating off Zalando onto CloudNativePG - that is the sibling
  skill postgres-operator-cloudnative-pg-migration.
argument-hint: "[upgrade|dcs|ops] (optional focus area)"
---

# postgres-operator-best-practices

Operate the Zalando postgres-operator without surprise downtime. Facts
below were verified **2026-08-25** against the upstream repo at tag
`v2.0.2` (`docs/administrator.md`, `docs/migrate.md`, chart defaults),
with the release list enumerated unfiltered, the issue tracker swept, and
deployment-level claims checked against a live RKE2 cluster on v1.14.0.
Re-verify anything version-gated before relying on it later.

**Version anchor (2026-08-25):** v1.14.0 (2024-12-23) · **v1.15.0**
(2025-10-21, ships without UI and logical-backup images — never use it,
go to v1.15.1) · **v1.15.1** (2025-12-18) · v2.0.0 (2026-07-27) ·
v2.0.1 (2026-07-29) · **v2.0.2** (2026-08-20, current). Default Spilo:
`spilo-17:4.0-p2` in v1.14.0, `spilo-17:4.0-p3` in v1.15.1,
`spilo-18:4.1-p2` in v2.0.x.

**v1.15.1 is the staging point for anyone on v1.14.x.** It is the last
release with `kubernetes_use_configmaps` disabled by default, and it is
where the code that the ConfigMap switch *needs* landed — service-selector
comparison in `compareServices` (#2955, explicitly "required when switching
to `kubernetes_use_configmaps`") and the extended RBAC for configmap-based
cluster management (#2961). Going v1.14 -> v1.15.1 crosses no changed
default at all. See "Choosing a path" below.

For migrating away to CloudNativePG, and for the "is this project still
alive" evidence, use `postgres-operator-cloudnative-pg-migration`. This
skill assumes you are staying.

## The four things that cause unplanned downtime

**1. Helm does not update the CRDs.** Upstream says so explicitly: "installing
the new chart will not update the `Postgresql` and `OperatorConfiguration`
CRD. Make sure to update them before with the provided manifests in the
`crds` folder." Skip this and new config options are silently **pruned** by
the apiserver against the old schema — the operator then runs on its own Go
defaults for those fields, which on a major upgrade are exactly the ones that
changed. Apply CRDs first, server-side:

```bash
tar xzf postgres-operator-<ver>.tgz -C /tmp postgres-operator/crds
kubectl apply --server-side --force-conflicts -f /tmp/postgres-operator/crds/
```

Pruning is near-total: only `sidecars` carries
`x-kubernetes-preserve-unknown-fields`. Check whether a specific option is
already in the *installed* CRD before assuming a pin will survive —
`kubectl get crd operatorconfigurations.acid.zalan.do -o yaml | grep <option>`.
Note `enable_crd_registration: true` (the default) makes the operator update
CRDs itself at runtime, but that happens *after* Helm has already applied the
CR, so it does not save you.

**2. A changed default is a config change you did not make.** Every major
upgrade, diff the upstream default values file against the previous one and
pin anything whose new value you are not ready to adopt. Rebuild your values
file *from the new upstream defaults* rather than patching your old copy —
that way removed keys drop out and new keys arrive with their comments,
instead of accumulating orphans that get silently pruned.

**3. Changing the operator's `docker_image` rolls every cluster that does not
pin its own.** A cluster manifest's `spec.dockerImage` wins; clusters without
one ride the operator default. Count the blast radius before touching it:

```bash
kubectl get pods -A -l application=spilo \
  -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}' | sort | uniq -c
```

`enable_lazy_spilo_upgrade: true` updates the StatefulSet without a rolling
update (deferring the switchover to whenever the pod next restarts). Default
is `false` — image change means immediate roll.

**4. The Patroni DCS is in deprecated v1 Endpoints, and switching is not a
flag flip.** With the Kubernetes DCS the leader lease and cluster config are
annotations on `Endpoints` objects. `kubernetes_use_configmaps: true` moves
them to ConfigMaps — and **defaults to true from v2.0**. Flipping it while a
cluster has replicas can leave a leader Endpoint and a leader ConfigMap alive
at the same time during the pod roll: **split brain**. Details, the upstream
procedure, and two lower-downtime paths: `references/dcs-endpoints.md`.

## Upgrading v1.x -> v2.x

Three breaking defaults, all of which change *runtime behaviour* on an
upgrade that is supposed to change *code*:

| Option | v1.14.0 | v2.0.x | Consequence if unpinned |
|---|---|---|---|
| `kubernetes_use_configmaps` | `false` | `true` | DCS switch mid-upgrade; split-brain risk |
| `docker_image` | `spilo-17:4.0-p2` | `spilo-18:4.1-p2` | rolls every cluster on the default image |
| password encryption | md5 | `scram-sha-256` | rewrites secrets, alters DB passwords, rolls pods |

The scram change is the widest blast radius and the easiest to miss: unless a
cluster sets `password_encryption: md5` under `spec.postgresql.parameters`,
v2 re-encrypts existing passwords and alters them. Every client driver must
speak scram before the first cluster rolls. Spilo's `pg_hba.conf` still
permits md5 for now, but the next tagged Spilo drops md5 entirely.

Also dropped in v2: Postgres 13 support; config options
`enable_ebs_gp3_migration(_max_size)`, `enable_spilo_wal_path_compat`,
`enable_crd_validation`; manifest fields `init_containers`,
`pod_priority_class_name`, `replicaLoadBalancer`, `useLoadBalancer` (use
`initContainers`, `podPriorityClassName`, `enableReplicaLoadBalancer`,
`enableMasterLoadBalancer`); the `kubectl-pg` plugin; and every reference to
`registry.opensource.zalan.do` — including the old `connection_pooler_image`
default, which is now `ghcr.io/zalando/postgres-operator/pgbouncer:<ver>`.

### v2.0.2 is the only viable v2 — v2.0.0 and v2.0.1 are both defective

Do not read "2.0.1 has the real release notes" as "2.0.1 is the release".
v2.0.0's notes are a single line redirecting to v2.0.1's, which is where the
full v2 changelog lives — but the *artifact* to deploy is v2.0.2.

- **v2.0.0** — generated CRD rejected by the apiserver; the operator fatals
  on startup (#3143).
- **v2.0.1** — three defects, all fixed only in v2.0.2: the scram
  `ALTER ROLE`-every-sync loop (#3170), global `sidecars` rejected by the
  apiserver (#3159), and the missing chart `strategy.type: Recreate` that
  lets two operators run at once (#3164).

**#3170 reproduces on v1.15.1 too — it is a scram bug, not a v2 bug.** On
v1.15.1 the default is still md5, so it bites only on opt-in. When staging
through v1.15.1, do **not** enable scram there.

Mechanisms, blast radius and fix PRs: `references/upgrade-v1-v2.md`.

### Two v2-upgrade traps that are only in the issue tracker

Neither is in the release notes or `migrate.md`. Both from **#3163 (still
open)**, with a detailed field report from an operator who hit the cascade:

**The v2 operator does not serve `/readyz` until every cluster has been
reconciled.** On v1.15.1 the API server came up first. Now the pod can sit
un-Ready for ~20-30 minutes on a fleet of any size. Do not interpret this as
a failed upgrade and do not roll back into it.

**If the old operator keeps running during that window, the two fight.**
Before v2.0.2 the Helm chart had no `Recreate` strategy, so both ran. The
v1 operator resets `scram-sha-256` back to `md5` while the v2 operator sets
it forward — one reporter saw 16 pods roll two or three times each, with a
switchover per cluster, plus `pod_deletion_wait_timeout` (10m) sync failures
and another 30m `resync_period` wait before recovery. **v2.0.2's `Recreate`
strategy fixes the fight**; confirm it is actually in your rendered
Deployment before upgrading.

**Set `workers` >= number of Postgres clusters first.** With fewer workers
than clusters, a cluster can wait on a pod informer that never starts,
burn `pod_deletion_wait_timeout`, fail the sync, and wait a full
`resync_period` to retry — rolling pods again each time. This is the
mitigation the reporter landed on, and it is not documented anywhere else.

### Choosing a path from v1.14.x

| Path | Crosses | When to prefer |
|---|---|---|
| **A. straight to v2.0.2**, pin `kubernetes_use_configmaps: false`, migrate DCS later | scram + PG13 drop + spilo default + regenerated CRDs, all at once | small fleets, tolerant of a pod roll, want one upgrade |
| **B. v1.14 -> v1.15.1, migrate DCS there, then v2.0.2** | nothing on the first hop; DCS alone on the second; scram alone on the third | production fleets; splits the two biggest risks apart |

Path B's first hop crosses **no changed default** and lands on a release
soaked since 2025-12-18, versus v2.0.2's few weeks. Its third hop needs no
DCS pin at all, because reality already matches the v2 default.

Full release history, the upgrade method, the layered diff, the
issue-tracker-only traps and two wrong expectations worth not repeating:
`references/upgrade-v1-v2.md`.

## Day-2 operations

Rolling updates, in-place major version upgrades and their annotations, PDB
behaviour, delete protection, maintenance windows, configuration hygiene and
the open-issue list: `references/operations.md`.

The two highest-value knobs most deployments leave off:

- **Delete protection** (`delete_annotation_name_key` /
  `delete_annotation_date_key`) is unset by default, so any `kubectl delete
  postgresql` takes the cluster. Turn it on before you need it.
- **`enable_patroni_failsafe_mode`** defaults to `false`. With it off, a DCS
  outage can demote a healthy primary. Worth enabling *before* a DCS
  migration, not after.

## Working method

- Verify against the cluster, not the release notes. Release notes say what
  changed; only the live CRD and a rendered template say what will happen to
  *this* deployment. Every claim in this skill that concerns a specific
  deployment was checked with `kubectl`, and several release-note-derived
  fears turned out not to apply.
- Render and diff before upgrading: `helm template ... --validate` both
  versions and diff the rendered manifests. A five-line rendered diff is a
  safe upgrade; a fifty-line one needs reading.
- Verify on settled state. The operator syncs on `resync_period` (default
  30m) and repairs on `repair_period` (5m). A snapshot taken mid-reconcile
  proves nothing.
- **Enumerate releases unfiltered before choosing a target version.** A
  pattern built from the versions expected to be there can only confirm that
  expectation — one such filter hid the entire v1.15.x line, and with it the
  designed staging point. List everything, then narrow by reading.
- Citations, per-claim, with issue states: `references/sources.md`.
