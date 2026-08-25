# Upgrading the Zalando postgres-operator v1.x -> v2.x

Verified **2026-08-25** against upstream `zalando/postgres-operator` at tag
`v2.0.2` (`docs/migrate.md`, `docs/administrator.md`, chart defaults), the
release list enumerated unfiltered, and the issue tracker swept. Re-verify
version-gated claims before relying on them later.

- [Release history — and which releases are deployable](#release-history)
- [Choosing a path](#choosing-a-path)
- [The upgrade method that works](#the-upgrade-method-that-works)
- [The three pins](#the-three-pins)
- [What the layered diff finds](#what-the-layered-diff-finds)
- [Traps that live only in the issue tracker](#traps-that-live-only-in-the-issue-tracker)
- [Expectations that turned out wrong](#expectations-that-turned-out-wrong)

## Release history

Enumerate the release list **unfiltered** before planning any upgrade:

```bash
gh api repos/zalando/postgres-operator/releases \
  --jq '.[] | "\(.tag_name)  \(.published_at[0:10])"'
```

| release | date | state |
|---|---|---|
| v1.14.0 | 2024-12-23 | last of the long-soaked v1 line |
| v1.15.0 | 2025-10-21 | **broken** — published without UI and logical-backup images; upstream says go straight to v1.15.1 |
| v1.15.1 | 2025-12-18 | sound; default Spilo `spilo-17:4.0-p3` |
| v2.0.0 | 2026-07-27 | **fatals on startup**, see below |
| v2.0.1 | 2026-07-29 | carries the full v2 changelog; **three defects**, not deployable |
| v2.0.2 | 2026-08-20 | the only viable v2 |

**Never filter a release list by a pattern built from what you expect to
find.** A `test("v2|v1.14")` filter on the API call above hides the entire
`v1.15.*` line — which is exactly where the designed staging point lives. The
filter can only ever confirm the assumption that built it. List everything,
then narrow by reading.

### v2.0.2 is the only viable v2

Do not read "v2.0.1 has the real release notes" as "v2.0.1 is the release".
v2.0.0's notes are a single line redirecting to v2.0.1's, so v2.0.1 is where
the full v2 changelog lives — but the *artifact* to deploy is v2.0.2.

**v2.0.0** — the generated `operatorconfigurations` CRD is rejected by the
apiserver (invalid string default on the object-typed
`oauth_token_secret_name`); the operator fatals on startup. #3143 (closed),
#3152, #3153.

**v2.0.1** — three defects, all fixed only in v2.0.2:

- **#3170 (closed) — a default that activates its own bug.** `syncUsers`
  compares the stored `rolpassword` against a freshly generated hash using
  plain string equality. That is fine for md5 (deterministic), but a
  SCRAM-SHA-256 verifier embeds a **random salt**, so the comparison never
  matches: the role is marked `PGsyncUserAlter`, the `ALTER ROLE ...
  PASSWORD` re-hashes with yet another random salt, and the next cycle
  mismatches again — forever, every `resync_period` (30 min default).
  Effects: `pg_authid.rolpassword` of every managed role rewritten each
  cycle (WAL and audit noise); and pgbouncer doing SCRAM pass-through with
  `auth_query` holds client keys bound to the previous salt, so server
  logins fail twice an hour (around :04 and :34) with `server_login_retry`
  throttling catching unrelated clients. **v2 flips the default to
  scram-sha-256, so v2.0.1 ships a default that triggers this.** Fixed by
  #3171.
- **#3159 (closed)** — because v2 generates CRDs from Go structs
  (#3004/#3102/#3117), `configuration.sidecars` renders as `type: object`
  while the Go field is `[]v1.Container`. Any OperatorConfiguration defining
  global sidecars is rejected by the apiserver; the feature is unusable on
  v2.0.0, v2.0.1 and master. It worked on v1.14.0, where the field was
  correctly `type: array`. Fixed by #3160.
- **#3164 (merged)** — the chart had no `strategy.type: Recreate`, so the old
  and new operators run concurrently and fight over scram vs md5.

**Scope note on #3170: it reproduces on v1.15.1 and master too — it is a
*scram* bug, not a *v2* bug.** v1.15.1 still defaults to md5, so it only
bites on opt-in. When staging through v1.15.1, do **not** enable scram there.

Generalise: when a release's notes are thin or redirect elsewhere, that is a
signal to check what the *next* patch release fixed before choosing a target.
"Latest stable" and "the release with the changelog" are often not the same
artifact.

**Nothing was reported against v2.0.2 in its first five days. That is
"untested in public", not "clean".**

## Choosing a path

| Path | Crosses | When to prefer |
|---|---|---|
| **A. straight to v2.0.2**, pin `kubernetes_use_configmaps: false`, migrate DCS later | scram + PG13 drop + spilo default + regenerated CRDs, all at once | small fleets, tolerant of a pod roll, want one upgrade |
| **B. v1.14 -> v1.15.1, migrate DCS there, then v2.0.2** | nothing on the first hop; DCS alone on the second; scram alone on the third | production fleets; splits the two biggest risks apart |

**v1.15.1 is the designed staging point for anyone on v1.14.x.** It is the
last release with `kubernetes_use_configmaps` disabled by default, and it is
where the code the ConfigMap switch *needs* landed — service-selector
comparison in `compareServices` (#2955, explicitly "required when switching to
`kubernetes_use_configmaps`") and the extended RBAC for configmap-based
cluster management (#2961). v1.15.0 also added the second
(critical-operations) PDB.

Path B's first hop crosses **no changed default at all** and lands on a
release soaked since 2025-12-18, versus v2.0.2's few weeks. Its third hop
needs no DCS pin, because reality already matches the v2 default.

## The upgrade method that works

Rebuild the values file **from the upstream defaults of the target version**,
then re-apply the deployment's own deltas. Do not patch the old values file
forward.

Removed keys drop out on their own, new keys arrive with their upstream
comments, and the diff against upstream defaults is exactly the
customisation surface — nothing else. Patching forward instead silently
carries dead keys (`enable_ebs_gp3_migration`, `enable_spilo_wal_path_compat`)
into a schema that no longer has them, where the apiserver prunes them
without a word.

## The three pins

The three v2 defaults worth pinning to v1 behaviour on the first hop, so the
code upgrade does not double as a behaviour change:

| Pin to v1 behaviour | v2 default | Reason |
|---|---|---|
| `kubernetes_use_configmaps: false` | `true` | split-brain hazard; see `dcs-endpoints.md` |
| `docker_image: ghcr.io/zalando/spilo-17:4.0-p2` | `spilo-18:4.1-p2` | rolls every cluster riding the default image |
| `target_major_version: "17"` | `"18"` | must match the pinned image |

`minimal_major_version` can usually be allowed to move `13` -> `14`, provided
nothing runs PG13.

### The three breaking defaults, restated

| Option | v1.14.0 | v2.0.x | Consequence if unpinned |
|---|---|---|---|
| `kubernetes_use_configmaps` | `false` | `true` | DCS switch mid-upgrade; split-brain risk |
| `docker_image` | `spilo-17:4.0-p2` | `spilo-18:4.1-p2` | rolls every cluster on the default image |
| password encryption | md5 | `scram-sha-256` | rewrites secrets, alters DB passwords, rolls pods |

The scram change has the widest blast radius and is the easiest to miss:
unless a cluster sets `password_encryption: md5` under
`spec.postgresql.parameters`, v2 re-encrypts existing passwords and alters
them. Every client driver must speak scram before the first cluster rolls.
Spilo's `pg_hba.conf` still permits md5 for now, but the next tagged Spilo
drops md5 entirely.

Also dropped in v2: Postgres 13 support; config options
`enable_ebs_gp3_migration(_max_size)`, `enable_spilo_wal_path_compat`,
`enable_crd_validation`; manifest fields `init_containers`,
`pod_priority_class_name`, `replicaLoadBalancer`, `useLoadBalancer` (use
`initContainers`, `podPriorityClassName`, `enableReplicaLoadBalancer`,
`enableMasterLoadBalancer`); the `kubectl-pg` plugin; and every reference to
`registry.opensource.zalan.do` — including the old `connection_pooler_image`
default, now `ghcr.io/zalando/postgres-operator/pgbouncer:<ver>`.

## What the layered diff finds

Four diffs, cheapest first. A small rendered diff is the actual green light;
the release notes' "breaking changes" list is far scarier than what a given
deployment will experience.

1. **Upstream default diff**, old chart vs new. Between 1.14.0 and 2.0.2 there
   are 8 material flips: the three pins above, plus `minimal_major_version`
   13->14, `connection_pooler_image` moving off `registry.opensource.zalan.do`
   onto ghcr, the operator CPU **limit** removed (#2893), new
   `enable_maintenance_windows: true`, and new logical-backup job history
   limits with `logical_backup_ttl_seconds_after_finished: 86400`. Removed:
   `enable_ebs_gp3_migration(_max_size)`, `enable_spilo_wal_path_compat`.
   Added: `extraArgs`, `irsa_role_arn`, `liveness_probe`, global
   `maintenance_windows`.
2. **Key-presence diff** — for every key the deployment sets, check it still
   exists in the new chart. Anything absent is about to be pruned silently.
3. **Rendered template diff** — `helm template ... --validate` on both
   versions, then diff. For 1.14.0 -> 2.0.2 expect ~20 lines: images bumped,
   `strategy.type: Recreate` added, the `update` verb added to one RBAC rule,
   the CPU limit gone, and the pins landing in the `OperatorConfiguration`.
4. **UI chart** — 1.14.0 -> 2.0.2 is a tag bump plus two removed commented
   examples. Copy the old values file and bump the tag.

## Traps that live only in the issue tracker

Neither of the first two appears in the release notes or `migrate.md`. Both
come from **#3163 (still open)**, with a detailed field report from an
operator who hit the full cascade.

**The v2 operator does not serve `/readyz` until every cluster has been
reconciled.** On v1.15.1 the API server came up before the sync. On v2 the pod
can sit un-Ready for ~20-30 minutes on a fleet of any size, with the readiness
probe refusing connections meanwhile. Do not read this as a failed upgrade and
do not roll back into it.

**If the old operator keeps running during that window, the two fight.**
Before v2.0.2 the chart had no `Recreate` strategy, so both ran. The v1
operator resets `scram-sha-256` back to `md5` while the v2 operator sets it
forward. One reported cascade (8 workers, 9 clusters): 8 clusters roll to
scram -> the old operator reverts them to md5 -> all 16 pods roll again with a
switchover each -> the 9th cluster's worker collision leaves clusters waiting
on a pod informer that never starts -> `pod_deletion_wait_timeout` (10m)
expires -> the sync fails -> a full `resync_period` (30m) passes before retry
-> a third roll. **v2.0.2's `Recreate` strategy fixes the fight** — confirm it
is actually in the rendered Deployment before upgrading.

**Set `workers` >= number of Postgres clusters first.** With fewer workers
than clusters, a cluster can wait on a pod informer that never starts, burn
`pod_deletion_wait_timeout`, fail the sync, and wait a full `resync_period` to
retry — rolling pods again each time. This is the mitigation the reporter
landed on, and it is documented nowhere upstream.

## Expectations that turned out wrong

Both of these were plausible, both cost time, and both were settled by
checking the live cluster rather than reasoning from the release notes.

- **"The v2 CRDs are too big for `kubectl apply`."** They did grow ~7×
  (`postgresqls` 25 KB -> 189 KB, `operatorconfigurations` 25 KB -> 132 KB,
  because v2 generates CRDs from Go structs with full descriptions). But a
  client-side `kubectl apply --dry-run=server` **succeeds** — the compacted
  JSON in `last-applied-configuration` stays under the 256 KB annotation
  limit. Server-side apply is still preferred (no giant annotation) and needs
  `--force-conflicts` when the existing CRD was applied client-side; the
  resulting "failed to migrate last-applied-configuration" warning is
  non-fatal and self-resolving.
- **"CRD pruning will defeat the `kubernetes_use_configmaps` pin."** It does
  not. That option is **already present in the v1.14.0 CRD schema, with
  `default: false`** — verified by dumping the live CRD, not assumed. Pruning
  only affects options genuinely new in v2, and where the operator's Go
  default equals the chart default the pruning is harmless. Applying CRDs
  first is still right, for determinism.

The transferable lesson: check whether a specific option is already in the
*installed* CRD before assuming a pin will survive.

```bash
kubectl get crd operatorconfigurations.acid.zalan.do -o yaml | grep <option>
```
