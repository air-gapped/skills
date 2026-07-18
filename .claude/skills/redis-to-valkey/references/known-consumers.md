# Known consumers — dated compatibility log

Append-only product findings (research pass 2026-07-18, primary sources).
Config-surface classes refer to `app-cutover.md`. Re-verify anything
version-gated at use time.

## 2026-07-18 — Harbor (classes A + C)

- Harbor is **itself replacing Redis with Valkey**: decision goharbor#22935
  (target 2.16.0); valkey cache backend cherry-picked into **v2.15.2**
  (#23157). harbor-helm main branch defaults the internal redis image to
  `goharbor/valkey-photon`; released 1.19.x charts still ship redis-photon.
  Strong first-party evidence of client compatibility.
- External sentinel config (chart): `redis.type: external`,
  `redis.external.addr: "s1:26379,s2:26379,s3:26379"` (comma list ⇒
  sentinel mode), `redis.external.sentinelMasterSet`, password via
  `existingSecret` (key `REDIS_PASSWORD`). Sentinel support since chart 1.9.0.
- DB indexes: `coreDatabaseIndex` **must be 0**; jobservice=1, registry=2,
  trivy=5 by default (+optional 6/7). Class C: transfer/verify all of them.
- No mTLS to redis; TLS server-auth only (`tlsOptions` + CA bundle secret).
- Clients: go-redis v9 + redigo. Data classes: jobservice **queues**
  (transfer or accept losing pending GC/replication/scan jobs and re-verify
  schedules after), registry cache + sessions (disposable).

## 2026-07-18 — GitLab (classes A + D, self-hosted chart/omnibus)

- Official support: Valkey **beta in 18.9, GA in 19.0**; requirements list
  Valkey min/recommended 7.2. GitLab 19.0 removed Redis 6 support and names
  Valkey an approved migration target. Earlier 18.x: protocol-compatible
  (frozen 7.2.4 passes the ≥7.0 gate) but formally unsupported — prefer
  sequencing the Valkey cutover with an upgrade to ≥18.9.
- Chart keys: `global.redis.host` = **master-set name** under Sentinel,
  `global.redis.sentinels[].host/port`, `global.redis.auth.*`, separate
  `global.redis.sentinelAuth.*` (chart ≥17.2) for authed sentinels.
- Data classes: Sidekiq **queues live in Redis — never flush**; drain to
  empty in maintenance mode or transfer logically. Cache instance is
  disposable. Admin Area shows "7.2.4" post-migration (documented cosmetic).
- Container-registry's own Redis cache had no Valkey statement yet
  (gitlab-org/container-registry#1648) — check if that feature is enabled.

## 2026-07-18 — oauth2-proxy (class A)

- Sentinel flags: `--redis-use-sentinel`, `--redis-sentinel-master-name`,
  `--redis-sentinel-connection-urls`, `--redis-sentinel-password`
  (sentinel-only; data nodes use `--redis-password`). go-redis v9.
- Sessions only (encrypted SETEX payloads): fresh start = one forced
  re-auth for users. No Valkey statement in docs; compatibility is
  protocol-level and unremarkable. Good first-mover app for proving a
  migration pattern.

## 2026-07-18 — Open WebUI (classes A + B)

- **First-party Valkey endorsement**: official tutorial states the Redis
  websocket guidance "applies as-is" to Valkey.
- Env surface: `REDIS_URL` (+`WEBSOCKET_REDIS_URL`) where host = master-set
  name when `REDIS_SENTINEL_HOSTS` (+`WEBSOCKET_SENTINEL_HOSTS`,
  `*_SENTINEL_PORT`) are set.
- Redis **Cluster** mode broken (#16157) — Sentinel is the HA path.
- Sentinel-auth bug #19401 (password not passed to sentinel client) was
  fixed shortly after report (closed 2025-11-25) — still, unauthenticated
  sentinels remain the safe posture. Multi-pod Sentinel floor: ≥0.9.5
  (readiness-probe regression fixed there).

## 2026-07-18 — cross-ecosystem client notes

- **Sidekiq** v8 requires Redis ≥7.2 and officially supports Valkey
  ("Redis 7.2.4 is the canonical implementation").
- **Sentry** crashed parsing Valkey's two-part `redis_version:7.2`
  (getsentry#107394) — the class-D poster child; test version parsers.
- **redis-py**: sentinel auth must go via `sentinel_kwargs={"password":…}`,
  not the top-level `password=` (recurring foot-gun).
- **go-redis**: old versions rejected Valkey 9.1's extra AZ field in
  `CLUSTER SHARDS` — fixed upstream; only affects cluster-mode clients.
