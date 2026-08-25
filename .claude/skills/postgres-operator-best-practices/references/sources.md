# Sources — postgres-operator-best-practices

Dated per-URL index backing this skill's factual claims. Freshen Mode probes
each row and stamps `Last verified` (and `Pinned` where applicable). Columns:
Ref, URL, What it grounds, Last verified (YYYY-MM-DD), Pinned.

## Most recent freshen pass: 2026-08-25

Initial creation. Upstream read at tag **v2.0.2**; release list enumerated
unfiltered via `gh api`; issue tracker swept the same day; claims about a
running deployment checked with `kubectl` against a live RKE2 cluster on
v1.14.0. Nothing here is inferred from release notes alone.

## Primary sources (repos, official docs, release artifacts)

| Ref | URL | Grounds | Last verified | Pinned |
|---|---|---|---|---|
| `docs/migrate.md` | https://github.com/zalando/postgres-operator/blob/v2.0.2/docs/migrate.md | v1 -> v2 migration: scram change, the Endpoints/ConfigMap procedure, the dropped-manifest-fields table | 2026-08-25 | tag v2.0.2 |
| `docs/administrator.md` | https://github.com/zalando/postgres-operator/blob/v2.0.2/docs/administrator.md | CRD registration, rolling-update triggers, in-place major upgrades and annotations, PDBs, delete protection, maintenance windows, password rotation (`enable_password_rotation`, dated-role mechanics, the four exclusions), logical backups (`enableLogicalBackup`, no-retention, RBAC), `CONTROLLER_ID` ownership | 2026-08-25 | tag v2.0.2 |
| `docs/user.md` | https://github.com/zalando/postgres-operator/blob/v2.0.2/docs/user.md | connection pooler: `enableConnectionPooler` / `enableReplicaConnectionPooler` independence, `{cluster-name}-pooler` service, `spec.connectionPooler` fields, flag-vs-section semantics | 2026-08-25 | tag v2.0.2 |
| `docs/reference/operator_parameters.md` | https://github.com/zalando/postgres-operator/blob/master/docs/reference/operator_parameters.md | `kubernetes_use_configmaps`, `resync_period`, `repair_period`, `pod_deletion_wait_timeout`, `workers` | 2026-08-25 | master |
| Chart defaults | https://github.com/zalando/postgres-operator/tree/v2.0.2/charts/postgres-operator | v1.14.0 -> v2.0.2 default flips; `strategy.type: Recreate` | 2026-08-25 | tag v2.0.2 |
| Release list (unfiltered) | https://github.com/zalando/postgres-operator/releases | full release history incl. the v1.15.x line | 2026-08-25 | v2.0.2 latest (2026-08-20) |
| v2.0.0 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.0 | one-line redirect to v2.0.1 — the version-selection trap | 2026-08-25 | 2026-07-27 |
| v2.0.1 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.1 | the full v2 changelog | 2026-08-25 | 2026-07-29 |
| v2.0.2 notes | https://github.com/zalando/postgres-operator/releases/tag/v2.0.2 | fixes for #3170, #3159, #3164 | 2026-08-25 | 2026-08-20 |
| v1.15.0 notes | https://github.com/zalando/postgres-operator/releases/tag/v1.15.0 | the fuller DCS migration guide (CONTROLLER_ID + standby paths); missing-images defect | 2026-08-25 | 2025-10-21 |
| K8s Endpoints deprecation | https://kubernetes.io/blog/2025/04/24/endpoints-deprecation/ | "will probably never completely go away"; deprecated in v1.33 | 2026-08-25 | 2025-04-24 |
| KEP-4974 | https://github.com/kubernetes/enhancements/issues/4974 | deprecates the Endpoints *controller* and conformance requirement, not the API type | 2026-08-25 | — |

## Issues / PRs (state-sensitive — re-check on freshen)

| Ref | URL | Grounds | Last verified | State |
|---|---|---|---|---|
| #3170 | https://github.com/zalando/postgres-operator/issues/3170 | scram `ALTER ROLE` every sync cycle; reproduces on v1.15.1 and master (scram bug, not v2 bug) | 2026-08-25 | closed — fixed by #3171 in v2.0.2 |
| #3163 | https://github.com/zalando/postgres-operator/issues/3163 | v2 upgrade cascade: `/readyz` after full reconcile, concurrent operators, `workers` >= cluster count | 2026-08-25 | **open** |
| #3159 | https://github.com/zalando/postgres-operator/issues/3159 | `configuration.sidecars` typed `object` vs Go `[]v1.Container` | 2026-08-25 | closed — fixed by #3160 |
| #3143 | https://github.com/zalando/postgres-operator/issues/3143 | v2.0.0 CRD rejected by apiserver; operator fatals on startup (also #3152, #3153) | 2026-08-25 | closed |
| #3164 | https://github.com/zalando/postgres-operator/pull/3164 | adds `strategy.type: Recreate` to the chart | 2026-08-25 | merged |
| #3161 | https://github.com/zalando/postgres-operator/issues/3161 | credentials exposed as env vars rather than read-only mounts | 2026-08-25 | **open** |
| #3151 | https://github.com/zalando/postgres-operator/issues/3151 | operator skips cluster update when controller ID changes | 2026-08-25 | **open** |
| #3157 | https://github.com/zalando/postgres-operator/issues/3157 | UI namespace selection limitations | 2026-08-25 | **open** |
| #3168 | https://github.com/zalando/postgres-operator/issues/3168 | proposal to protect operator CRDs with a finalizer | 2026-08-25 | **open** |
| #3162 | https://github.com/zalando/postgres-operator/issues/3162 | secrets deleted despite `enable_secrets_deletion: false` + owner references | 2026-08-25 | closed |
| #2946 | https://github.com/zalando/postgres-operator/issues/2946 | the Endpoints deprecation warning, filed against v1.14.0; @FxKu on EndpointSlice not being usable | 2026-08-25 | — |
| #2955 / #2961 | https://github.com/zalando/postgres-operator/pull/2955 | ConfigMap-switch prerequisites landing in v1.15.x (`compareServices`; configmap RBAC) | 2026-08-25 | merged |
| #2893 | https://github.com/zalando/postgres-operator/pull/2893 | operator CPU limit removed | 2026-08-25 | merged |
| #3004 / #3102 / #3117 | https://github.com/zalando/postgres-operator/pull/3102 | CRDs generated from Go structs (cause of the ~7× CRD size growth and #3159) | 2026-08-25 | merged |

## Volatile facts to re-verify on every freshen

- Latest release and whether a newer patch supersedes v2.0.2 as the deployable
  v2 artifact. Enumerate releases **unfiltered**; never pattern-match on
  expected versions.
- #3163 state — still open as of 2026-08-25; the `/readyz` regression and the
  `workers` mitigation are undocumented upstream and may become documented or
  fixed.
- Whether Spilo has dropped md5 from `pg_hba.conf` (stated upstream as coming
  in the next tagged Spilo).
- Default Spilo image per release line (`spilo-17:4.0-p2` in v1.14.0,
  `spilo-17:4.0-p3` in v1.15.1, `spilo-18:4.1-p2` in v2.0.x).
- Whether the v1.15.0-notes vs v2-`migrate.md` discrepancy on ConfigMap count
  (two vs three) has been reconciled upstream.

## Related

- Sibling skill `postgres-operator-cloudnative-pg-migration` — for leaving
  Zalando rather than operating it, and for the stay-vs-migrate evidence base.
