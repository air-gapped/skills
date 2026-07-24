# Sources — postgres-operator-cloudnative-pg-migration

Dated per-URL index backing this skill's factual claims. Freshen Mode
probes each row and stamps `Last verified` (and `Pinned` where
applicable). Columns: Ref, URL, What it grounds, Last verified
(YYYY-MM-DD), Pinned.

## Most recent freshen pass: 2026-07-24

Initial creation. Every row was probed live on 2026-07-24 (research
pass: 9 agents over 2 rounds; both operator repos read from full local
clones at HEAD 2026-07-23). Research report:
`.claude/skills/autoresearch/results/zalando-postgres-operator-vs-cloudnative-pg-research-2026-07-24.md`.

## Primary sources (repos, official docs, release artifacts)

| Ref | URL | Grounds | Last verified | Pinned |
|---|---|---|---|---|
| CNPG repo/docs | https://github.com/cloudnative-pg/cloudnative-pg | all CNPG field/version claims (API ref, bootstrap, database_import, logical_replication, failover, instance_manager, replication, backup, postgres_upgrades, supported_releases, operator_conf, cnpg_i) | 2026-07-24 | clone @ 0552b9caa (v1.30.0+51) |
| CNPG lease source | internal/cmd/manager/instance/run/lease/runnable.go | isolated-primary lease behavior (retry vs self-stop) | 2026-07-24 | same clone |
| Zalando repo/docs | https://github.com/zalando/postgres-operator | manifest reference, CRD Go types, admin docs, service/secret naming, scram default | 2026-07-24 | clone @ 86d3027e |
| Spilo repo | https://github.com/zalando/spilo | USE_OLD_LOCALES / Ubuntu 18.04 locale archive (Dockerfile, launch.sh), WAL-G-only (ENVIRONMENT.rst), wal_level default (configure_spilo.py) | 2026-07-24 | — |
| CNPG supported releases | https://cloudnative-pg.io/docs/devel/supported_releases | 3-month cadence, ~6-month minor life, K8s/PG windows | 2026-07-24 | 1.30.x: K8s 1.34–1.36, PG 14–18 |
| CNPG installation_upgrade | https://cloudnative-pg.io/docs/devel/installation_upgrade | operator upgrade → fleet rolling restart; in-place update flag | 2026-07-24 | — |
| plugin-barman-cloud | https://github.com/cloudnative-pg/plugin-barman-cloud | v0.13.0 images (sidecar in base64 Secret), ObjectStore CRD shape, migration.md, cert-manager avoidance, CNPG ≥1.26 floor | 2026-07-24 | v0.13.0 (2026-06-10) |
| plugin Helm chart | https://github.com/cloudnative-pg/charts/tree/main/charts/plugin-barman-cloud | chart 0.7.0 / appVersion v0.13.0; certificate.create* toggles | 2026-07-24 | chart 0.7.0 |
| CNPG postgres-containers | https://github.com/cloudnative-pg/postgres-containers | operand image repo builds majors 13–18 (13 deprecated; CNPG 1.29/1.30 *support* only PG 14–18 per supported_releases), minimal/standard flavors, Debian bases, system deprecated | 2026-07-24 | — |
| Instana runbook | https://www.ibm.com/docs/en/instana-observability/1.0.314?topic=postgres-migrating-data-from-zalando-cnpg | path C sequence: streaming_replica role, replica mode, Spilo conf-path fix, REFRESH COLLATION VERSION | 2026-07-24 | — |
| Bartolini Recipe #5 | https://www.gabrielebartolini.it/articles/2024/03/cloudnativepg-recipe-5-how-to-migrate-your-postgresql-database-in-kubernetes-with-~0-downtime-from-anywhere/ | canonical path A recipe (schemaOnly import + pub/sub + sync-sequences) | 2026-07-24 | — |
| Patroni failsafe docs | https://github.com/patroni/patroni/blob/master/docs/dcs_failsafe_mode.rst | Patroni demote-on-lock-failure; failsafe ALL-members rule | 2026-07-24 | — |
| glibc collation break | https://wiki.postgresql.org/wiki/Locale_data_changes | glibc 2.28 ISO-14651 corruption background | 2026-07-24 | — |

## Issues / discussions (state-sensitive — re-check on freshen)

| Ref | URL | Grounds | Last verified | State |
|---|---|---|---|---|
| Zalando #2921 | https://github.com/zalando/postgres-operator/issues/2921 | maintainer "idle state" statement, internal scale, "will keep maintaining" | 2026-07-24 | open |
| Spilo #1131 | https://github.com/zalando/spilo/issues/1131 | Spilo aliveness, internal fork, migration testimonials both directions | 2026-07-24 | open |
| CNPG #5736 (+#5568) | https://github.com/cloudnative-pg/cloudnative-pg/issues/5736 | "should not use physical replication from Zalando"; SSL required | 2026-07-24 | closed |
| CNPG #7407 / disc #7462 | https://github.com/cloudnative-pg/cloudnative-pg/discussions/7462 | split-brain history; closed 2025-12-31 citing 1.27 isolation + 1.28 quorum | 2026-07-24 | closed |
| CNPG #10807 / PR #10627 | https://github.com/cloudnative-pg/cloudnative-pg/issues/10807 | primary lease design intent (gate not fence) | 2026-07-24 | merged 1.30 |
| CNPG #8902 | https://github.com/cloudnative-pg/cloudnative-pg/issues/8902 | backup-metrics rename regression after plugin migration | 2026-07-24 | open |
| plugin #652 | https://github.com/cloudnative-pg/plugin-barman-cloud/issues/652 | first backup unrestorable on idle DBs | 2026-07-24 | open |
| CNPG #3788 | https://github.com/cloudnative-pg/cloudnative-pg/issues/3788 | managed.roles no password generation | 2026-07-24 | open |
| CNPG disc #3723 | https://github.com/cloudnative-pg/cloudnative-pg/discussions/3723 | import fails on Spilo extension deps | 2026-07-24 | — |
| HA bugs #10430 #10287 #11202 #10547 #11110 | github.com/cloudnative-pg/cloudnative-pg/issues/… | open HA-adjacent bugs listed in pitfalls | 2026-07-24 | all open |
| PR #11148 | https://github.com/cloudnative-pg/cloudnative-pg/pull/11148 | multi-instance-no-sync warning is 1.31 material ("do not backport") | 2026-07-24 | merged, unreleased |
| CNCF incubation | https://github.com/cncf/toc/issues/1961 | CNPG incubation application (2025-11-12) | 2026-07-24 | open |
| Crunchy #3601 | https://github.com/CrunchyData/postgres-operator/issues/3601 | Developer Program image revocation incident (alternatives assessment) | 2026-07-24 | closed |

## Secondary (practitioner / vendor — bias noted)

| Ref | URL | Grounds | Last verified |
|---|---|---|---|
| Wilsher migration writeup | https://shawnwilsher.com/2026/01/migrating-from-zalados-postgres-operator-to-cloudnativepg/ | clone-cluster import pattern, extension + search_path traps, 1.15.0 trigger | 2026-07-24 |
| Bartolini 2025 year-in-review | https://www.gabrielebartolini.it/articles/2025/12/cloudnativepg-in-2025-cncf-sandbox-postgresql-18-and-a-new-era-for-extensions/ | CNPG metrics, extension_control_path (insider, factual) | 2026-07-24 |
| EDB survey blog | https://www.enterprisedb.com/blog/cloudnativepg-the-most-popular-postgres-operator-in-2023 | 2023 share numbers (vendor-published; no neutral 2025/26 survey exists) | 2026-07-24 |
| Crunchy glibc blog | https://www.crunchydata.com/blog/glibc-collations-and-data-corruption | collation-corruption mechanics | 2026-07-24 |

## Volatile facts to re-verify on every freshen

- In-tree barmanObjectStore removal version (currently 1.31.0 — slipped 4×).
- Latest plugin-barman-cloud release and its CNPG module target.
- Zalando release state (v1.15.1 latest since 2025-12-18; PG18 release pending).
- CNPG latest minors + K8s window; PG major support floor.
- CNCF incubation outcome (cncf/toc#1961).
- Open-bug states listed above (esp. #3788, #8902, #652, HA set).
