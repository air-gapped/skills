# Sources — redis-to-valkey

Dated per-URL index backing this skill's factual claims. Freshen Mode probes
each row and stamps `Last verified` (and `Pinned` where applicable). Columns:
Ref, URL, What it grounds, Last verified (YYYY-MM-DD), Pinned.

## Most recent freshen pass: 2026-07-18

Initial creation. Every row below was probed live on 2026-07-18 (research
pass: 6 agents + inline gh reads of source files at release tags), the same
day the skill was authored.

## Primary sources (specs, source code, official docs)

| Ref | URL | Grounds | Last verified | Pinned |
|---|---|---|---|---|
| valkey migration doc | https://valkey.io/topics/migration/ | Redis ≤7.2.x source bound; AOF-masks-RDB caveat; redis_version rationale; Lua namespaces | 2026-07-18 | — |
| valkey rdb.h | https://github.com/valkey-io/valkey/blob/9.0.0/src/rdb.h | RDB_VERSION 11 (8.x) / 80 (9.x); RDB_FOREIGN_VERSION_MIN 12 | 2026-07-18 | tags 8.0.0/8.1.0/9.0.0/9.1.0 |
| valkey version.h | https://github.com/valkey-io/valkey/blob/9.0.0/src/version.h | redis_version frozen at "7.2.4" in 8.x and 9.x | 2026-07-18 | tags 8.1.3/9.0.0 |
| valkey #2588 | https://github.com/valkey-io/valkey/issues/2588 | replica flushes before rejecting foreign RDB | 2026-07-18 | — |
| valkey #2338 / PR #2846 | https://github.com/valkey-io/valkey/issues/2338 | dual-channel + Sentinel phantom replica; fix merged 2026-02-23, contained in 9.1.0 only (verified via tag compare) | 2026-07-18 | fix ∈ 9.1.0 |
| valkey #845 | https://github.com/valkey-io/valkey/issues/845 | "Can't handle RDB format version 12" failure mode | 2026-07-18 | — |
| RedisShake | https://github.com/tair-opensource/RedisShake | v4.6.1 (2026-04-24); Redis 2.8–8.4.x → Valkey 8–9; sync/scan/rdb readers; no-resume + topology-panic caveats; release binaries per platform; image ghcr.io/tair-opensource/redisshake | 2026-07-18 | v4.6.1 |
| librdb / rdb-cli | https://github.com/redis/librdb | rdb-cli replay recipe; source-only releases (build via make) | 2026-07-18 | — |
| groundhog2k valkey chart | https://github.com/groundhog2k/helm-charts/tree/master/charts/valkey | haMode defaults, auth-via-config-fragments, 26379-only HA service, storage/ServiceMonitor defaults, UID 999, chart 2.3.2→Valkey 9.1.0, DNS-failover fix in 2.2.2 | 2026-07-18 | chart 2.3.2 |
| Bitnami redis chart | https://github.com/bitnami/charts/blob/main/bitnami/redis/values.yaml | source-side key names/defaults (auth.*, sentinel.*, replica.*, metrics.*) across 19.x–23.x | 2026-07-18 | 19.6.4–23.1.1 |
| CloudPirates charts | https://github.com/CloudPirates-io/helm-charts | valkey chart 0.24.4, sentinel + externalReplica modes, cosign, common-lib OCI dep | 2026-07-18 | chart 0.24.4 |
| valkey-io/valkey-helm | https://github.com/valkey-io/valkey-helm | official chart 0.10.0, no Sentinel (replication only), Sentinel+HAProxy PR pending | 2026-07-18 | chart 0.10.0 |
| valkey-io/valkey-operator | https://github.com/valkey-io/valkey-operator | cluster-mode only, "not ready for production" | 2026-07-18 | v0.3.x |
| redis_exporter | https://github.com/oliver006/redis_exporter | Valkey 7–9 support statement; v1.87.0; docker.io/ghcr.io/quay.io mirrors | 2026-07-18 | v1.87.0 |
| Bitnami lockdown issue | https://github.com/bitnami/charts/issues/35164 | timeline (2025-08-28 / 2025-09-29), bitnamilegacy semantics, :latest-only free tier | 2026-07-18 | — |
| charts.bitnami.com (live probe) | https://charts.bitnami.com/bitnami/index.yaml | 302 → repo.broadcom.com; still serving; ~13 charts updated, 131 frozen | 2026-07-18 | — |
| Argo CD Helm docs | https://argo-cd.readthedocs.io/en/stable/user-guide/helm/ | OCI repoURL without oci:// prefix; multi-source $values | 2026-07-18 | — |
| ElastiCache Valkey deltas | https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/VersionManagementConsiderations-valkey.html | per-major behavior changes 7.2→8.0→9.x (MULTI, SCAN, BITCOUNT, CLUSTER SHARDS AZ field) | 2026-07-18 | — |

## Consumer-app sources (ground known-consumers.md)

| Ref | URL | Grounds | Last verified | Pinned |
|---|---|---|---|---|
| Harbor valkey decision | https://github.com/goharbor/harbor/issues/22935 | Redis→Valkey replacement decision, target 2.16.0 | 2026-07-18 | — |
| Harbor 2.15.2 notes | https://github.com/goharbor/harbor/releases/tag/v2.15.2 | valkey cache backend cherry-pick #23157 | 2026-07-18 | v2.15.2 |
| harbor-helm values | https://github.com/goharbor/harbor-helm/blob/main/values.yaml | external sentinel keys; valkey-photon on main; 1.19.x still redis-photon | 2026-07-18 | chart 1.19.1 |
| GitLab redis admin doc | https://docs.gitlab.com/administration/redis/ | Valkey beta 18.9 / GA 19.0; admin-area version cosmetic | 2026-07-18 | — |
| GitLab external-redis chart doc | https://docs.gitlab.com/charts/advanced/external-redis/ | global.redis sentinel keys, sentinelAuth ≥17.2 | 2026-07-18 | — |
| GitLab requirements | https://docs.gitlab.com/install/requirements/ | Valkey min/rec 7.2; no Redis Cluster | 2026-07-18 | — |
| oauth2-proxy session docs | https://oauth2-proxy.github.io/oauth2-proxy/configuration/session_storage/ | sentinel flags incl. --redis-sentinel-password | 2026-07-18 | — |
| Open WebUI valkey tutorial | https://docs.openwebui.com/tutorials/integrations/valkey/ | first-party Valkey endorsement | 2026-07-18 | — |
| Open WebUI #19401 | https://github.com/open-webui/open-webui/issues/19401 | sentinel-auth bug, closed 2025-11-25 | 2026-07-18 | — |
| Sidekiq Valkey support | https://github.com/sidekiq/sidekiq/issues/6630 | Sidekiq 8 requires Redis ≥7.2; Valkey supported | 2026-07-18 | — |
| Sentry version-parse crash | https://github.com/getsentry/sentry/issues/107394 | two-part "7.2" redis_version breaking parsers | 2026-07-18 | — |

## Search queries for future freshens

- `valkey-helm sentinel` — has the official chart shipped Sentinel support yet? (flips the chart recommendation)
- `RedisShake release` — new majors past v4.6.x; resume support would remove a documented caveat
- `bitnami charts sunset OR repo.broadcom.com` — an announced end date changes the risk model from "migrate deliberately" to "migrate now"
- `harbor-helm release valkey-photon` — first released chart defaulting to valkey changes the Harbor guidance
- `gitlab charts bundled valkey` — gitlab-org/charts work item on replacing bundled redis
