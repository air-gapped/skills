# Sources — redis-to-valkey

Freshened: 2026-09-22 — every row probed; all 32 URLs 200 and every cited issue state reproduces. Valkey 9.2.0-rc1 appeared (2026-09-16, pre-release only, RDB_VERSION 81) and three chart pins moved; `redis_version` is still frozen at 7.2.4 even at the rc.

**Six version pins moved and not one qualitative claim did.** The upstream release lines, three charts, the operator and the exporter are all a release or two on; meanwhile every *behavioural* claim re-verified exactly as written — the official chart still has no Sentinel (both PRs still open), the operator README still says not production-ready, the sync tool's maintainers still decline the feature, and the bundled-chart lockdown thread still has no comment since 2025-09-16. Version pins are the cheap half of this file; the claims they support did not rot.

Dated index of the primary sources backing this skill's factual claims. One
stamp asserts every row below was re-probed on that date, except rows carrying
an inline exception note. `Pinned:` records the version, tag, or commit the
claim was read at.

**Version-containment claims are checked by tag compare, not release notes.**
Both safety-critical fixes here (#2600, #2846) are absent from the 8.x and 9.0
lines despite closing well before those releases shipped — `gh api
repos/valkey-io/valkey/compare/<tag>...<commit>` returning `behind` is what
proves containment, and a release-notes read would have gotten both wrong.

## Primary sources (specs, source code, official docs)

| Ref | URL | Grounds | Pinned |
|---|---|---|---|
| valkey migration doc | https://valkey.io/topics/migration/ | Redis ≤7.2.x source bound; AOF-masks-RDB caveat; redis_version rationale; Lua namespaces | — |
| valkey rdb.h | https://github.com/valkey-io/valkey/blob/9.1.1/src/rdb.h | RDB_VERSION 11 (8.x) / 80 (9.x); RDB_FOREIGN_VERSION_MIN 12 | tags 8.1.9/9.0.5/9.1.1 |
| valkey version.h | https://github.com/valkey-io/valkey/blob/9.1.1/src/version.h | redis_version frozen at "7.2.4" (comment: "should never exceed 7.2.x") | tags 8.1.9/9.1.1 |
| valkey #2588 + **PR #2600** | https://github.com/valkey-io/valkey/pull/2600 | replica flushed before rejecting a foreign RDB; fix "validate before emptyData" merged 2025-11-19, **contained in 9.1.0+ only** — `compare` says `diverged` from 8.1.9 and 9.0.5 | fix ∈ 9.1.0, 9.1.1 |
| valkey #2338 / PR #2846 | https://github.com/valkey-io/valkey/issues/2338 | dual-channel + Sentinel phantom replica; merged 2026-02-23, **9.1 line only** — `diverged` from 9.0 and 8.1 | fix ∈ 9.1.0+ |
| valkey #845 | https://github.com/valkey-io/valkey/issues/845 | "Can't handle RDB format version 12" failure mode; still OPEN, no upstream fix — third-party tools are the only answer | — |
| valkey releases | https://github.com/valkey-io/valkey/releases | current lines **9.1.2 / 9.0.6** (both 2026-09-01), **8.1.10 / 8.0.11** (both 2026-08-31), 7.2.14 (2026-07-21, unchanged); **still no 9.2 or 10.x** | 9.1.2 (2026-09-01) |
| RedisShake | https://github.com/tair-opensource/RedisShake | v4.6.2 (2026-08-17); Redis 2.8–8.4.x → Valkey 8–9; sync/scan/rdb readers; topology-panic caveat | v4.6.2 |
| RedisShake #1016 | https://github.com/tair-opensource/RedisShake/issues/1016 | resume/checkpoint **declined by maintainers** as out of scope for a sync tool — the "restart = full recopy" caveat is permanent, not pending | open |
| librdb / rdb-cli | https://github.com/redis/librdb | rdb-cli replay recipe; git tags only, **no binary releases** (build via make) | tag v2.3.0 |
| groundhog2k valkey chart | https://github.com/groundhog2k/helm-charts/tree/master/charts/valkey | haMode defaults, auth-via-config-fragments, 26379-only HA service, storage/ServiceMonitor defaults, UID 999, DNS-failover fix in 2.2.2 | chart 2.3.3 / app 9.1.1 |
| Bitnami redis chart | https://github.com/bitnami/charts/blob/main/bitnami/redis/values.yaml | source-side key names/defaults (auth.*, sentinel.*, replica.*, metrics.*) across 19.x–23.x; chart still updated, app pinned redis 8.2.1 | 19.6.4–23.1.1 |
| CloudPirates charts | https://github.com/CloudPirates-io/helm-charts | sentinel + externalReplica modes, **new `sentinel.masterProxy` HAProxy front-end**, cosign, common-lib OCI dep | chart 0.25.5 / app 9.1.0 |
| valkey-io/valkey-helm | https://github.com/valkey-io/valkey-helm | official chart, **still no Sentinel**; Sentinel PR #234 and HAProxy PR #235 open/unmerged (earlier attempts #82/#137/#158 closed) | chart 0.11.0 |
| valkey-io/valkey-operator | https://github.com/valkey-io/valkey-operator | cluster-mode only, README still "not ready for production", v1alpha1 | v0.6.0 (2026-09-01) |
| redis_exporter | https://github.com/oliver006/redis_exporter | Valkey 7–9 support statement; docker.io/ghcr.io/quay.io mirrors | v1.91.1 (2026-09-07) |
| Bitnami lockdown issue | https://github.com/bitnami/charts/issues/35164 | timeline (2025-08-28 / 2025-09-29), bitnamilegacy semantics, :latest-only free tier; closed, **no comment since 2025-09-16 and no sunset date announced** | — |
| charts.bitnami.com (live probe) | https://charts.bitnami.com/bitnami/index.yaml | 302 → repo.broadcom.com; still serving 200, index last-modified 2026-08-24, **144 chart entries** | — |
| Argo CD Helm docs | https://argo-cd.readthedocs.io/en/stable/user-guide/helm/ | OCI repoURL **without** `oci://` prefix (page still states this verbatim); multi-source $values | — |
| ElastiCache Valkey deltas | https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/VersionManagementConsiderations-valkey.html | per-major behavior changes 7.2→8.0→8.1→9.0→9.1; 9.1 adds the CLUSTER SHARDS/SLOTS AZ field (cluster-mode only — out of this skill's scope, see pitfall #14) | — |

## Consumer-app sources (ground known-consumers.md)

| Ref | URL | Grounds | Pinned |
|---|---|---|---|
| Harbor valkey decision | https://github.com/goharbor/harbor/issues/22935 | Redis→Valkey replacement; **closed**, shipped in v2.15.2 (no 2.16.0 exists) | closed 2026-04-28 |
| Harbor 2.15.2 notes | https://github.com/goharbor/harbor/releases/tag/v2.15.2 | valkey cache backend cherry-pick #23157 (PR #23261) | v2.15.2 |
| harbor-helm values | https://github.com/goharbor/harbor-helm/blob/v1.19.2/values.yaml | **released chart now defaults `redis.internal.image.repository` to `goharbor/valkey-photon`**; external config keeps legacy `addr`/`sentinelMasterSet` names | chart 1.19.2 (2026-08-03) |
| GitLab redis admin doc | https://docs.gitlab.com/administration/redis/ | Valkey beta 18.9 / GA 19.0; admin-area version display cosmetic (known issue 589642) | — |
| **GitLab bundled-chart removal** | https://docs.gitlab.com/charts/development/external-dependencies/ | "The bundled PostgreSQL, Redis, and MinIO charts have been deprecated and **were removed in GitLab 19.0**" — no replacement; Valkey is the suggested external substitute | 19.0 |
| GitLab external-redis chart doc | https://docs.gitlab.com/charts/advanced/external-redis/ | global.redis sentinel keys. **EXCEPTION (2026-08-26):** the `sentinelAuth ≥17.2` version gate recorded on 2026-07-18 is not present on the current page and `sentinelAuth.*` now documents under charts/globals; the mechanism is confirmed, the version gate is not re-verifiable — treat the floor as unconfirmed rather than deleting it | — |
| GitLab requirements | https://docs.gitlab.com/install/requirements/ | Valkey min/rec 7.2; Redis Cluster not supported | — |
| oauth2-proxy session docs | https://oauth2-proxy.github.io/oauth2-proxy/configuration/session_storage/ | `--redis-use-sentinel`, `--redis-sentinel-master-name`, `--redis-sentinel-connection-urls`. **EXCEPTION (2026-08-26):** `--redis-sentinel-password` is NOT on this page — it is real (19 hits in oauth2-proxy source) but grounded in the repo, not here. Do not drop the flag from the skill on the strength of this page alone | — |
| Open WebUI valkey tutorial | https://docs.openwebui.com/tutorials/integrations/valkey/ | first-party Valkey endorsement; drop-in via REDIS_URL | — |
| Open WebUI #19401 | https://github.com/open-webui/open-webui/issues/19401 | sentinel-auth bug, closed 2025-11-25, no reopen | — |
| Sidekiq Valkey support | https://github.com/sidekiq/sidekiq/issues/6630 | Valkey supported. **8.0.1 relaxed the floor to Redis 7.0**, not 7.2 as recorded on 2026-07-18 | closed |
| Sentry version-parse crash | https://github.com/getsentry/sentry/issues/107394 | two-part "7.2" redis_version breaking parsers — **fixed, closed COMPLETED 2026-02-09** | closed |

## Open questions for the next freshen

Answered this pass, kept because the answer can flip:

- `valkey-helm sentinel` — **still not shipped** (PRs #234/#235 open). Flips the
  chart recommendation to a first-party chart the day it merges.
- `RedisShake resume` — **declined by maintainers**, not pending. Stop watching.
- `bitnami charts sunset` — **no date announced** (issue quiet since 2025-09-16).
  A date changes urgency from "deliberate" to "now".
- `harbor-helm valkey-photon` — **shipped in chart 1.19.2**. Watch instead for
  Harbor switching the *external* config key names off `redis*`.
- `gitlab bundled valkey` — **resolved differently**: 19.0 deleted the bundled
  charts entirely. Watch the Omnibus Valkey epic for the non-Helm path.

Still open:

- Does the #2600 flush fix get backported to 9.0.x or 8.1.x? Today both lines
  carry the live hazard, which is the main argument for landing on 9.1.x.
- `valkey 9.2 / 10.x` — a new RDB version would extend the wall table.
