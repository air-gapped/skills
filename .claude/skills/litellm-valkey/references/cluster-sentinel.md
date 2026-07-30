# Sentinel and Cluster — per-topology reality

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29). The shared client factory is `litellm/_redis.py`: `_get_redis_client_logic` (`:317-448`) resolves env + kwargs; branch order is url → `startup_nodes` (cluster) → `sentinel_nodes` (sentinel) → host/port (`:431-445`).

## Sentinel

### Support timeline (the "since what version" answer)

| What | Version | Evidence |
|---|---|---|
| Sentinel for the **response cache** (`cache_params.sentinel_nodes` + `service_name`, or `REDIS_SENTINEL_NODES`/`REDIS_SERVICE_NAME` env) | long-standing | documented in `docs/proxy/caching.md:164-208` |
| Sentinel for **core coordination** (`general_settings.coordination_redis.sentinel_nodes`) | **v1.93.0** | PR #32661 merged 2026-07-11; contained in v1.93.0-rc.1 and v1.93.0 (verified `git merge-base --is-ancestor`) |
| Sentinel via `REDIS_SENTINEL_NODES` env counting as a coordination connection target | v1.93.0 | `_environment_has_redis_connection_target` (`proxy_server.py:3700-3713`), PR #32635 |
| Helm chart renders sentinel coordination block (`redis.sentinel.enabled` + `masterSet`) | v1.93.0 window | PR #32662, 2026-07-11 |
| `router_settings` sentinel | **never** | #22796 closed by stale bot 2026-06-11, unimplemented; superseded by `coordination_redis` |

Fix-version catalog for older images (all closed): #20734 sentinel password passed with wrong kwarg (closed 2026-06-17), #21197 SSL/connection kwargs not forwarded to the resolved master (closed 2026-05-24), #22796 n/a (stale), #10276 DB index with sentinel (older). An image predating mid-2026 likely hits several of these; upgrade rather than patch around.

### Current mechanics

- Selected when `sentinel_nodes` **and** `service_name` are both present (`_redis.py:555` sync, `:629` async). `_init_redis_sentinel`/`_init_async_redis_sentinel` (`:489-536`) build `redis.Sentinel(...).master_for(service_name, **connection_kwargs)`.
- Env fallbacks: `REDIS_SENTINEL_NODES` (JSON, e.g. `'[["host",26379],...]'`), `REDIS_SENTINEL_PASSWORD`, `REDIS_SERVICE_NAME` (`:355-374`).
- `connection_kwargs.setdefault("socket_timeout", REDIS_SOCKET_TIMEOUT)` in both initialisers is effectively a no-op because a 5.0 default already occupies the key (see `config-reference.md`).

### Rough edges (present on main)

- **`sentinel_kwargs["password"] = sentinel_password` unconditionally** (`:496`, `:521`): with authenticated *data* nodes but unauthenticated sentinels this sends `password=None` to the sentinels — fine; the surprising case is sentinels requiring the data password: `sentinel_password` must be set explicitly, it never falls back to `password`.
- **`get_redis_connection_pool()` has no sentinel branch** (`:655-693`): it builds a `BlockingConnectionPool` with sentinel kwargs stuffed into `connection_kwargs` — dead weight the sentinel client path ignores, but it would raise if anything ever used it (e.g. code paths that grab the pool directly).
- **`host`/`port` leak into `master_for`**: `_get_redis_sentinel_connection_kwargs` filters by `_get_redis_kwargs()`, which includes `host` and `port` — setting them alongside `sentinel_nodes` passes them into `sentinel.master_for(service_name, host=…, port=…)`. Don't set both.
- `RedisCache.test_connection` (`redis_cache.py:1279-1314`) constructs `redis_async.Redis(**self.redis_kwargs)` directly, bypassing sentinel resolution — its verdict does not reflect the client the proxy actually uses. Use `POST /coordination_redis/settings/test` instead (it goes through `_build_redis_usage_cache`).

## Cluster

### Selection

A `RedisClusterCache` is built iff `startup_nodes` is present (config `cache_params.redis_startup_nodes` / `coordination_redis.startup_nodes` / `REDIS_CLUSTER_NODES` env): `caching.py:169-197`, `router.py:824-840`, `proxy_server.py:3681-3697` (`_build_redis_usage_cache` — cluster gets `RedisClusterCache`, "everything else (host/url/sentinel) gets a plain `RedisCache`"). `RedisClusterCache` only overrides `init_async_client`, `mget`→`mget_nonatomic`, `test_connection` (`redis_cluster_cache.py`).

### What is cluster-aware (and its cost)

- The v3 limiter mints keys with explicit hash tags — `f"{{{key}:{value}}}:{rate_limit_type}"` (`parallel_request_limiter_v3.py:641`) — and groups Lua invocations by slot via a local CRC16 (`:697-745`), used by the batch rate-limiter script (`:766`) and token-increment script (`:2715`). This is why `redis-cli --scan` shows `{api_key:sk-…}:requests` shapes.
- **Cost**: `atomic_check_and_increment_by_n` degrades from one atomic Lua call to one call per slot-group plus a best-effort `INCRBY` refund loop if a later descriptor is over limit (`:1231-1252`, `:1340-1372`, `_refund_applied_descriptor_groups`). All-or-nothing across api_key/user/team is **not atomic on cluster**; a crash mid-loop leaves counters inflated until window expiry.
- **Latent CROSSSLOT**: the parallel-request gauge scripts (`parallel_count_script` `:1018`, `parallel_acquire_script` `:1047`, `parallel_release_script` `:1171`) pass *all* gauge keys to one EVAL without slot grouping. Works today because only the `api_key` descriptor carries `max_parallel_requests` (`:2010`); breaks silently (→ in-memory fallback, `:1053-1058`) the moment a second scope gains it.

### Broken or degraded on cluster

- `async_scan_iter` returns `[]` when the client lacks `scan_iter` (`redis_cache.py:476-480`) → the `batch_redis_requests` hook and any key-pattern sync are no-ops.
- `mget` is `mget_nonatomic` — multi-key reads not atomic.
- `get_redis_connection_pool()` returns `None` for cluster (`_redis.py:661-662`) → `RedisCache.disconnect()` hits `None.disconnect` `AttributeError` (`redis_cache.py:1272-1273`), reachable from shutdown (`proxy_server.py:805`) and the coordination test endpoint's cleanup.
- **Version probe fails**: `redis_client.info()` raises on a cluster client (per-node), swallowed (`redis_cache.py:249`) → `redis_version="Unknown"` → `DEFAULT_REDIS_MAJOR_VERSION=7` assumed → on Redis ≤6 clusters, `async_lpop(count=…)` uses the native `LPOP key count` form that doesn't exist there. (The parse function's docstring `redis_cache.py:373` name-checks the float `7.0` that **AWS ElastiCache Valkey** returns — Valkey has already bitten this code once, fixed via #16207.)
- `REDIS_CLUSTER_HEALTH_CHECK_INTERVAL` is a hardcoded 25 (`constants.py:347-350`, not env-read); cluster connections get `health_check_interval=25` + `socket_keepalive=True` forced (`_redis.py:603-604`).

### Cluster issue catalog (state at 2026-07-30)

- **#25447 OPEN "Critical"** — response/tool-call cross-talk between users on multi-replica + cluster (Claude Code workloads); independently reproduced on plain single Redis. Workaround: `cache_params.supported_call_types: []` (disables response caching, keeps coordination). Possibly related #35023 (cross-request CJK stream contamination, closed 07-29).
- #30065 OPEN — CROSSSLOT on Azure Redis Enterprise (hash-tag grouping only applied for OSS cluster protocol).
- #28379 OPEN — GCP IAM auth broken with cluster (`redis_connect_func` ignored by cluster bootstrap).
- #31206 OPEN — `REDIS_CLUSTER_NODES` breaks proxy shutdown; #27982 OPEN — usage UI/request logs break with Redis cache enabled.
- Closed lineage (fix versions matter on old images): #25049 EVALSHA slot fallback (2026-07-16), #27919 cluster drops socket-timeout kwargs, #22748 `REDIS_CLUSTER_NODES` ignored in router path, #8878 MOVED errors, #15066 multi-primary rate limiting.

## Valkey specifics

- Standard cache/coordination against Valkey behaves as Redis 7.2-compatible; the ElastiCache-for-Valkey float `redis_version` ("7.0" as float) parse was fixed in #16207.
- `valkey_semantic_cache.py` is a dedicated backend (valkey-search module, direct `FT.*`, builds its own `Redis.from_url` clients bypassing `_redis.py`); it **rejects cluster-mode-enabled endpoints with an explicit error** (`valkey_semantic_cache.py:69-76`) — one of the few well-documented corners (`docs/caching/all_caches.md:334-399`).
- #32324 OPEN at sweep — Valkey semantic cache broken by `**kwargs` vs `metadata` in `_get_async_embedding`; commenters report fixed on main by PR #32295 (2026-07-06), landing ≥v1.92; issue left open.
- #34614 (redis-py 5.3.1 `ssl_check_hostname` TypeError) reproduces against Valkey.
- `grep -ri valkey` across the docs corpus: **zero hits** — the support exists only in code and the dashboard UI.
