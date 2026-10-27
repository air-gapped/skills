# Sources — postgres-operator-best-practices

Freshened: 2026-09-22 — every row probed; all 26 URLs 200. v2.0.2 is still the unfiltered latest — no v2.0.3 or v2.1.x — and the readyz regression, the scram password-rewrite loop and the `workers >= cluster count` mitigation are all freshly reconfirmed in #3163's live thread, which remains open and undocumented upstream.

Per-URL index backing this skill's factual claims. Freshen Mode probes every
row and rewrites the stamp below; rows it could not reach carry an inline
exception note instead.

**Freshened: 2026-09-15**

Re-probed end to end with no drift: every URL, every cited issue and PR state, and each of the volatile facts below. `v2.0.2` is still the newest release (list enumerated unfiltered), the `/readyz` regression is still open and still undocumented upstream, and Spilo still has no tag past the one this release pins — so the claim that the md5 drop is still ahead of us remains forward-looking rather than wrong. Release containment for each fix was re-established with `git tag --contains`, never from a merge date.

Upstream read at tag **v2.0.3** (v2.0.2 -> v2.0.3 diffed file by file); release list enumerated unfiltered via
`gh api`; issue tracker swept the same day; claims about a running deployment
checked with `kubectl` against a live RKE2 cluster on v1.14.0. Nothing here is
inferred from release notes alone.

## Primary sources (repos, official docs, release artifacts)

| Ref | URL | Grounds |
|---|---|---|
| `docs/administrator.md` | https://github.com/zalando/postgres-operator/blob/v2.0.3/docs/administrator.md | CRD registration, rolling-update triggers, in-place major upgrades and annotations, PDBs, delete protection, maintenance windows, password rotation (`enable_password_rotation`, dated-role mechanics, the four exclusions), logical backups (`enableLogicalBackup`, no-retention, RBAC), `CONTROLLER_ID` ownership |
| `docs/user.md` | https://github.com/zalando/postgres-operator/blob/v2.0.3/docs/user.md | connection pooler: `enableConnectionPooler` / `enableReplicaConnectionPooler` independence, `{cluster-name}-pooler` service, `spec.connectionPooler` fields, flag-vs-section semantics |
| `docs/migrate.md` | https://github.com/zalando/postgres-operator/blob/v2.0.3/docs/migrate.md | v1 -> v2 migration: scram change, the Endpoints/ConfigMap procedure, the dropped-manifest-fields table |
| `docs/reference/operator_parameters.md` | https://github.com/zalando/postgres-operator/blob/master/docs/reference/operator_parameters.md | `kubernetes_use_configmaps`, `resync_period`, `repair_period`, `pod_deletion_wait_timeout`, `workers` |
| Chart defaults | https://github.com/zalando/postgres-operator/tree/v2.0.3/charts/postgres-operator | v1.14.0 -> v2.0.2 default flips (v2.0.3 changes only image tags); `strategy.type: Recreate`; `docker_image` `spilo-18:4.1-p2` at v2.0.3 |
| Release list (unfiltered) | https://github.com/zalando/postgres-operator/releases | full release history incl. the v1.15.x line. **Pinned:** v2.0.3 latest (2026-10-02) |
| v2.0.0 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.0 | one-line redirect to v2.0.1 — the version-selection trap (2026-07-27) |
| v2.0.1 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.1 | the full v2 changelog (2026-07-29) |
| v2.0.2 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.2 | fixes for #3170, #3159, #3164 (2026-08-20) |
| v2.0.3 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.3 | bugfix patch (2026-10-02); its "Default Spilo image" line prints `spilo-17:4.1-p2`, contradicted by the chart and `config.go` (`spilo-18:4.1-p2`) |
| v1.15.0 notes | https://github.com/zalando/postgres-operator/releases/tag/v1.15.0 | the fuller DCS migration guide (CONTROLLER_ID + standby paths); missing-images defect (2025-10-21) |
| K8s Endpoints deprecation | https://kubernetes.io/blog/2025/04/24/endpoints-deprecation/ | "will probably never completely go away"; deprecated in v1.33 |
| KEP-4974 | https://github.com/kubernetes/enhancements/issues/4974 | deprecates the Endpoints *controller* and conformance requirement, not the API type |
| Patroni Kubernetes DCS | https://github.com/patroni/patroni/blob/master/patroni/dcs/kubernetes.py | state written to object `metadata.annotations` (`_patch_or_create`, a `V1ConfigMap` with no `data`); `leader_path` is `<scope>-leader` under ConfigMaps, `<scope>` under Endpoints; `-failover` is written only by `set_failover_value`, `-sync` only by the sync-state write |
| Operator master Service selector | https://github.com/zalando/postgres-operator/blob/v2.0.3/pkg/cluster/k8sres.go | `generateService`: the master Service gets a selector when `kubernetes_use_configmaps` is on, so the `<cluster>` Endpoints is controller-managed after the switch |

## Issues / PRs (state-sensitive — re-check on freshen)

| Ref | URL | Grounds | State |
|---|---|---|---|
| #3170 | https://github.com/zalando/postgres-operator/issues/3170 | scram `ALTER ROLE` every sync cycle; reproduces on v1.15.1 and master (scram bug, not v2 bug) | closed — fixed by #3171 in v2.0.2 |
| #3163 | https://github.com/zalando/postgres-operator/issues/3163 | v2 upgrade cascade: `/readyz` after full reconcile, concurrent operators, `workers` >= cluster count | **open** |
| #3159 | https://github.com/zalando/postgres-operator/issues/3159 | `configuration.sidecars` typed `object` vs Go `[]v1.Container` | closed — fixed by #3160 |
| #3143 | https://github.com/zalando/postgres-operator/issues/3143 | v2.0.0 CRD rejected by apiserver; operator fatals on startup (also #3152, #3153) | closed |
| #3164 | https://github.com/zalando/postgres-operator/pull/3164 | adds `strategy.type: Recreate` to the chart | merged |
| #3161 | https://github.com/zalando/postgres-operator/issues/3161 | credentials exposed as env vars rather than read-only mounts | **open** |
| #3151 | https://github.com/zalando/postgres-operator/issues/3151 | operator skips cluster update when controller ID changes | **open** |
| #3157 | https://github.com/zalando/postgres-operator/issues/3157 | UI namespace selection limitations | **open** |
| #3168 | https://github.com/zalando/postgres-operator/issues/3168 | proposal to protect operator CRDs with a finalizer | **open** |
| #3162 | https://github.com/zalando/postgres-operator/issues/3162 | secrets deleted despite `enable_secrets_deletion: false` + owner references | closed |
| #2946 | https://github.com/zalando/postgres-operator/issues/2946 | the Endpoints deprecation warning, filed against v1.14.0; @FxKu on EndpointSlice not being usable | — |
| #2955 / #2961 | https://github.com/zalando/postgres-operator/pull/2955 | ConfigMap-switch prerequisites landing in v1.15.x (`compareServices`; configmap RBAC) | merged |
| #2893 | https://github.com/zalando/postgres-operator/pull/2893 | operator CPU limit removed | merged |
| #3177 / #3193 | https://github.com/zalando/postgres-operator/pull/3193 | v2.0.3: pgbouncer `auth_type` from `md5` to `$CONNECTION_POOLER_AUTH_TYPE` = `password_encryption` (`passwordEncryptionFromSpec`, scram fallback); md5-only pooler clients must pin `password_encryption: md5`. Operator restart needed for a manifest `password_encryption` change: `docs/migrate.md` + `docs/user.md` at v2.0.3; code reads it once in `cluster.New` | merged (2026-09-01 / 2026-09-30), both in v2.0.3 |
| #3179 / #3187 | https://github.com/zalando/postgres-operator/pull/3179 | primary move off an unschedulable node: before v2.0.3 `retryutil.Retry` aborted on the first error (fixes #3176); #3187 (https://github.com/zalando/postgres-operator/pull/3187) makes single-pod clusters recreate without a switchover request. Trigger condition (`nodeUpdate`: ready -> unschedulable without readiness label) and `master_pod_move_timeout` 20m read in `pkg/controller/node.go` / `config.go` at v2.0.3 | merged, both in v2.0.3 |
| #3200 | https://github.com/zalando/postgres-operator/issues/3200 | post-switch confusion on v2.0.3: `<cluster>` Endpoints still present with the primary IP, ConfigMaps "not populated" — both expected (see the two rows above) | **open**, unanswered |
| #3004 / #3102 / #3117 | https://github.com/zalando/postgres-operator/pull/3102 | CRDs generated from Go structs (cause of the ~7× CRD size growth and #3159) | merged |

## Volatile facts to re-verify on every freshen

- Latest release and whether a newer patch supersedes v2.0.3 as the deployable
  v2 artifact. Enumerate releases **unfiltered**; never pattern-match on
  expected versions.
- #3163 state — the `/readyz` regression and the `workers` mitigation are
  undocumented upstream and may become documented or fixed.
- Whether Spilo has dropped md5 from `pg_hba.conf` (stated upstream as coming
  in the next tagged Spilo).
- Default Spilo image per release line (`spilo-17:4.0-p2` in v1.14.0,
  `spilo-17:4.0-p3` in v1.15.1, `spilo-18:4.1-p2` in v2.0.x).

## Related

- Sibling skill `postgres-operator-cloudnative-pg-migration` — for leaving
  Zalando rather than operating it, and for the stay-vs-migrate evidence base.
