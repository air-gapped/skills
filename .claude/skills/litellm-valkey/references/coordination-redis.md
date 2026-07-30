# The coordination Redis — resolution, config surface, verification

All line numbers against `BerriAI/litellm` @ `4d543245` (v1.95.0-dev, 2026-07-29) unless stamped otherwise. Re-resolve by symbol name after upgrades.

## What "coordination" covers (and what it doesn't)

The coordination Redis (`redis_usage_cache` internally) backs: v3 rate limiting (Lua scripts), spend counters (`spend_counter_cache`, `RedisCache.async_set_max` Lua CAS-max), the spend→DB transaction buffer (RPUSH/LPOP lists), the pod lock manager / cron leader election (`SET NX EX` + Lua compare-and-delete), shared health checks, config param cache, CLI SSO sessions, MCP OAuth token store + distributed locks, and the scheduler/priority queue. The **response cache** (`litellm.cache`) and the **router cache** (cooldowns, usage-based routing) are separate objects that may or may not share the same client.

Three Redis client sets a "normal" prod config creates:

1. `router_settings.redis_*` → `Router._create_redis_cache()` (`router.py:500-535`, `824-840`) → `Router.cache` (cooldowns, tpm/rpm routing, scheduler).
2. `litellm_settings.cache_params` → `Cache()` → `litellm.cache.cache`, borrowed as `redis_usage_cache` (`proxy_server.py:4126-4133`).
3. Semantic caches build their own `Redis.from_url` pair bypassing `_redis.py` entirely (`valkey_semantic_cache.py:83-92`).

Each `RedisCache` builds a sync client + async client + `BlockingConnectionPool`, so 2 configured backends ≈ 4 clients + 2 pools per pod (see `config-reference.md` §connection-churn for the 600s rebuild issue).

## Resolution order (the 4 sources)

Mirrored by `_coordination_redis_source()` (`management_endpoints/coordination_redis_endpoints.py:208-224`):

1. **`general_settings.coordination_redis`** — `CoordinationRedisParams` (`proxy/_types.py:2192-2217`): `host, port, username, password, url, ssl, startup_nodes, sentinel_nodes, sentinel_password, service_name`. Validated at `proxy_server.py:4070-4102` (`_init_coordination_redis`); runs **before** cache init, so it takes precedence. First-class since **v1.93.0** (PR #32661, merged 2026-07-11). Values support `os.environ/VAR` refs. **No `namespace` field** — see §namespacing.
2. **DB-persisted block** (Admin UI writes it): loaded at `proxy_server.py:984-989`, `7718-7755`; applied after the file config, so the DB copy **silently outranks config.yaml**. Audit-logged (`coordination_redis_endpoints.py:236+`), but nothing warns that the file value is being shadowed.
3. **Borrowed response cache**: `_init_cache` (`proxy_server.py:4104+`) — the cache backend is attached as the usage cache iff it is a `RedisCache`/`RedisClusterCache` (`proxy_server.py:4126-4130`). Semantic/disk/s3 backends are not borrowed.
4. **`REDIS_*` env fallback**: `_build_redis_usage_cache_from_environment()` (`proxy_server.py:3716-3729`), gated by `_environment_has_redis_connection_target()` (`:3700-3713`), which counts `REDIS_HOST`+`REDIS_PORT`, `REDIS_URL`, `REDIS_CLUSTER_NODES`, and `REDIS_SENTINEL_NODES`. Added in the v1.93.0 window (PR #32635: "build redis usage cache from REDIS_* env when cache backend is not Redis").

**The `cache: true` gate.** Sources 3 and 4 execute inside `_init_cache`, which is only called from the config branch `elif key == "cache" and value is True` (`proxy_server.py:4478-4483`). Consequences:

- `REDIS_HOST`/`REDIS_URL` env alone, **no** `litellm_settings.cache: true`, **no** `coordination_redis` block → `redis_usage_cache` stays `None` → rate limits, spend counters, pod locks all per-pod. `docs/proxy/prod.md:161` ("Redis … shares rate limit counters, router state, and the response cache across instances") and `docs/proxy/deploy.md:32` ("Required once you run more than one instance") both omit this precondition.
- The env fallback is otherwise reachable only via `_get_transaction_buffer_redis_cache` when `use_redis_transaction_buffer: true` (`proxy_server.py:7757-7778`).
- Open **#26233**: the guard `len(cache_params.keys()) == 0` (`proxy_server.py` ~L4382 at the time of the report) means *any* key in `cache_params` — even `mode: default_off` — suppresses the env fallback. Symptom: single knob added to cache config, multi-pod spend tracking silently breaks.

**The router gate.** `Router.__init__` creates its Redis cache only when `redis_url` or (`redis_host` **and** `redis_port`) is passed (`router.py:500`); it does not read env vars. `router_settings: {redis_host: x}` without `redis_port` → in-memory router cache, no warning. Mitigation: `proxy_server.py:5041-5042` back-fills `router.cache.redis_cache` from `redis_usage_cache` when one exists — so the visible symptom depends on whether another source produced a coordination Redis.

## Verification endpoints (undocumented, admin-only)

- `GET /coordination_redis/settings` — returns the live (credential-redacted) config **and `source`**: `"coordination_redis"` (explicit block, file or DB), `"cache_backend"` (borrowed), `"environment"`, or null (per-pod mode). `coordination_redis_endpoints.py:288-296`.
- `POST /coordination_redis/settings` — persists a block to the DB (this is how the UI shadows the config file).
- `POST /coordination_redis/settings/test` — builds a throwaway client from submitted params (redacted credential fields fall back to saved values) and pings it. `coordination_redis_endpoints.py:390-433`.
- `GET /cache/ping` — response cache **only**, and only when `litellm.cache.type == "redis"` (`caching_routes.py:80`). Blind to a dedicated coordination Redis. Same for `/cache/flushall` — which, when the client is borrowed, wipes rate-limit counters, spend counters, spend buffer lists, and cron locks along with the cache (`caching_routes.py:235-236` → `redis_client.flushall()`).

`scripts/litellm-redis-preflight.sh` chains these.

## Helm chart wiring (in-repo `helm/litellm-helm`)

Since PR #32662 (v1.93.0 window, 2026-07-11), `values.yaml`:

- `redis.enabled: true` deploys the bundled Redis subchart (bitnamilegacy images), wires `REDIS_HOST/PORT/PASSWORD`, **and renders a `general_settings.coordination_redis` block** into the proxy config.
- `redis.sentinel.enabled: true` renders the coordination block with `sentinel_nodes` + `service_name` (from `redis.sentinel.masterSet`) instead of host/port — "because a plain Redis client cannot talk to the sentinel port" (values.yaml comment).
- `redis.coordination.enabled: false` keeps the bundled Redis for response caching only.
- An explicit `coordination_redis` block in `proxy_config` always wins over the chart-rendered one.
- External Redis: leave `redis.enabled: false`, provide `REDIS_*` via secret — but then the `cache: true` gate applies; prefer an explicit `coordination_redis` block in `proxy_config`.

The chart is marked community-maintained in its README; validate rendered config with `helm template | yq '.data' | grep -A8 coordination_redis` before rollout.

## Namespacing — two deployments, one Valkey

`cache_params.namespace` sets `self.cache.namespace` (`caching.py:281-283`) and `check_and_fix_namespace` prefixes every key on that client (`redis_cache.py:354-363`) — **including** rate-limit and lock keys *when the client is borrowed*. But `CoordinationRedisParams` has no namespace field, so a dedicated coordination Redis writes **unprefixed** keys: `cronjob_lock:*`, `litellm_spend_update_buffer`, `{api_key:…}:requests`. Two LiteLLM deployments pointed at one Valkey DB will interleave locks and counters. Use separate logical DBs (or separate instances) per deployment.

Also: `check_and_fix_namespace` uses `key.startswith(self.namespace)` (`redis_cache.py:360`), so a key that legitimately begins with the namespace string silently escapes prefixing.

## Migrating a pre-v1.93 borrowed-cache deployment to `coordination_redis`

For a fleet where coordination borrows the response-cache client (source `cache_backend`) — the standard pre-v1.93 Sentinel topology:

1. Add a `general_settings.coordination_redis` block mirroring the current `cache_params` connection values (same Redis is fine initially — the win is decoupling the *clients*, which un-shares the circuit breaker; see `silent-degradation.md`).
2. Roll all pods (the block is read at startup), then confirm `GET /coordination_redis/settings` reports `source: "coordination_redis"` on every pod — the explicit block outranks the borrow, no cache config change needed.
3. Optionally repoint the block at a dedicated Redis/Valkey later; keys are unprefixed (§Namespacing), so counters and locks start fresh on the new instance — expect one rate-limit window and one spend-sync cycle of discontinuity, and roll during low traffic.
4. Keep `cache_params` untouched throughout — response caching and coordination are now independent.

Do NOT do this by deleting `cache_params` first: dropping the cache while env vars carry any `cache_params` key leaves the #26233 trap live, and removing `cache: true` without an explicit block lands in per-pod mode (the `cache: true` gate above).

## History: how the Sentinel/Cluster asymmetry arose

- The response cache accepted both Cluster (`redis_startup_nodes`) and Sentinel (`sentinel_nodes`/`service_name`, `REDIS_SENTINEL_NODES`) long before the core path did; `docs/proxy/caching.md` documents both.
- `router_settings` accepted only `redis_host/redis_port/redis_password/redis_url`. Feature request #22796 (Sentinel in `router_settings`, for "cooldown tracking, RPM/TPM limits") was **closed by the stale bot 2026-06-11 — never implemented**. `REDIS_CLUSTER_NODES` was ignored on the router path until #22748.
- Practical pre-v1.93 workaround was configuring the *response cache* with Sentinel and letting coordination borrow the client — which coupled cache health to enforcement health (see `silent-degradation.md` §circuit-breaker) and is what most Sentinel deployments were actually running.
- v1.93.0 (2026-07-11 merge window) shipped the clean split: #32661 (`coordination_redis` block + env fallback + `/coordination_redis/*` endpoints), #32635 (env fallback for non-Redis cache backends), #32662 (chart + terraform surface).
