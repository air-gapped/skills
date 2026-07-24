# Consumer application cutover

Contents: [Services](#services-every-dsn-changes) · [Secrets](#secrets) ·
[Authentication](#authentication) · [Connection pooling](#connection-pooling) ·
[Monitoring and dashboards](#monitoring-and-dashboards) · [Cutover checklist](#cutover-checklist-per-application)

Everything a client app touches changes name or shape. Inventory
consumers per cluster before cutover; the translation is then
mechanical. Verified 2026-07-24.

## Services (every DSN changes)

| Zalando | CNPG | Role |
|---|---|---|
| `<cluster>` | `<cluster>-rw` | primary, read-write |
| `<cluster>-repl` | `<cluster>-ro` | replicas only, read-only |
| — | `<cluster>-r` | any instance (round-robin incl. primary) |
| `<cluster>-pooler` (if enabled) | `<pooler-name>` (Pooler CR name; convention `<cluster>-pooler-rw`) | pgbouncer |

Apps that connected to the bare Zalando cluster-name service must move
to `-rw`. Read-split apps: `-repl` → `-ro`. Keep the cluster name
identical across operators (new namespace if needed) and the churn is
suffix-only. `managed.services.additional` can add LoadBalancer/NodePort
services with `serviceTemplate` where Zalando used
`enableMasterLoadBalancer`/`allowedSourceRanges`
(`loadBalancerSourceRanges`).

## Secrets

| Zalando | CNPG |
|---|---|
| `<user>.<cluster>.credentials.postgresql.acid.zalan.do` (keys: `username`, `password`) | owner: `<cluster>-app`; superuser: `<cluster>-superuser` (keys: `username`, `password`, `host`, `port`, `dbname`, `pgpass`, `uri`, `jdbc-uri`, `fqdn-uri`) |

- CNPG secrets are richer — apps can consume `uri`/`jdbc-uri` directly;
  prefer that over assembling DSNs.
- **Only** the bootstrap owner and superuser get generated secrets.
  Every additional Zalando `users:` entry needs a pre-created
  `kubernetes.io/basic-auth` Secret referenced by
  `managed.roles[].passwordSecret` (see manifest-map.md).
- `enableSuperuserAccess` defaults **false**: no `-superuser` secret
  exists unless enabled. Audit which tools (backup scripts, admin
  jobs) actually used the Zalando `postgres.*` secret.
- External-secrets/ESO templating that watched the Zalando secret name
  pattern must be rewired.

## Authentication

- Both stacks default `scram-sha-256` today. The trap is **old md5
  hashes**: physical copies (path C) and monolith imports carry
  `rolpassword` hashes verbatim; md5-hashed users then fail against
  scram-only pg_hba rules. Pre-flight query (migration-paths.md) finds
  them; fix = reset those passwords (generates scram) before or at
  cutover.
- CNPG **cannot** run `ssl=off` (#5568). Legacy clients that negotiated
  plaintext must tolerate TLS (`sslmode=prefer` clients are fine;
  hardcoded `sslmode=disable` breaks).
- pg_hba: CNPG APPENDS user rules between operator-fixed first/last
  rules; a Zalando cluster that REPLACED defaults (removed pam line,
  tightened the catch-all) cannot be reproduced exactly — verify the
  effective policy with `SELECT * FROM pg_hba_file_rules;`.
- New option worth adopting: `DatabaseRole` (≥1.30) with
  `clientCertificate.enabled` gives operator-issued client certs for
  password-free auth (add the pg_hba `cert` rule yourself).

## Connection pooling

Zalando's pooler service `<cluster>-pooler` → CNPG `Pooler` CR (own
service name). Recompute limits: Zalando divided `maxDBConnections`
across pooler pods; CNPG passes `pgbouncer.parameters` verbatim
**per instance** — copying the Zalando number multiplies effective
connections by the instance count.

## Monitoring and dashboards

- Zalando fleets typically ran postgres_exporter sidecars (`pg_*`
  metric names). CNPG's exporter is built into the instance manager
  (port 9187): built-ins are `cnpg_collector_*`, user queries from
  `monitoring.customQueriesConfigMap/Secret` become `cnpg_<query>_*`.
  **No compatibility shim** — every dashboard, alert, and recording
  rule referencing `pg_*` needs rewriting.
- Official Grafana dashboard: `cloudnative-pg/grafana-dashboards`
  (importable offline).
- Scrape via PodMonitor (create it manually; the Helm chart's
  `monitoring.podMonitorEnabled` exists but per-cluster
  `enablePodMonitor` is deprecated in current docs).
- Backup metrics change again with the barman plugin
  (`barman_cloud_cloudnative_pg_io_*` — backup-chain.md). Alert on
  metric absence, not just failure values.
- Custom exporter queries that lived in the sidecar config move to the
  CNPG custom-queries ConfigMap — syntax is the postgres_exporter
  YAML dialect, mostly copy-paste.

## Cutover checklist (per application)

1. Inventory: DSN source (secret ref? hardcoded? ESO-templated?),
   sslmode, pooling, read-split usage, monitoring dashboards, cron/batch
   jobs with their own credentials.
2. Pre-stage new secret refs / DSNs behind a config flag or a paused
   deployment where possible.
3. At cutover (inside the path-A write pause): swap DSN/secret refs,
   scale up, verify: connect, auth, `SELECT` on hot tables, write path,
   sequence-dependent inserts (path A: only after sync-sequences).
4. Verify TLS mode and password auth for every distinct user, not just
   the owner.
5. Confirm metrics flowing under `cnpg_*` names and backup-freshness
   alerts armed on the plugin metric names.
6. Leave the Zalando-era secrets in place (read-only artifacts) until
   the old cluster is decommissioned — rollback needs them.
