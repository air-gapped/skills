# Per-pod vs shared — the truth table

Which enforcement is actually fleet-wide, how stale each shared view can be, and what breaks it. Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29).

## The table

| Enforcement | Shared via Redis? | Staleness / failure mode |
|---|---|---|
| RPM / TPM (v3 limiter, default) | Yes — Lua per request | Local pre-check can over-reject up to `window_size` after the shared window rolled (`should_rate_limit` local OVER_LIMIT short-circuit, `parallel_request_limiter_v3.py:833-838`); **any** Redis error → per-pod counters |
| `max_parallel_requests` | Yes — ZSET gauge + Lua | Slot leak self-heals only after `PARALLEL_REQUEST_SLOT_TTL_SECONDS=3600` (hardcoded, `:319`); Redis error → per-pod gauge in a 200-entry LRU; only the `api_key` descriptor carries it today (`:2010`) |
| TPM token reservation | Yes — `CHECK_AND_INCREMENT_BY_N` Lua | On cluster: not atomic across descriptors, refunds best-effort (`:1231-1252`, `:1340-1372`) |
| Key/team/user/org budgets | Yes — `spend_counter_cache` + `async_set_max` (Lua CAS-max, `redis_cache.py:918-953`) | 60s in-memory tier (`proxy_server.py:2007-2010`); fails open unless `fail_closed_budget_enforcement` |
| Router cooldowns | Yes — DualCache | Reads throttled to 10s (below); **writes are sync/blocking** on the async path (`cooldown_cache.py:89-93` ← `router.py:7097`, `:7356`); sync-write `str()` serialization can make entries unreadable (see `config-reference.md` §sync-async) |
| usage-based-routing-v2 tpm/rpm | Eventually | Local increment immediate; Redis flush every `DEFAULT_REDIS_SYNC_INTERVAL=1`s (`base_routing_strategy.py:88-101`); reads up to 10s stale → N pods can overshoot by ~N×1s of traffic |
| Provider/tag budget routing | Eventually | Same 1s queue; queue **dropped** on Redis error (`budget_limiter.py:543-545`) |
| Deployment-level TPM | **No** (open #27736) | RPM batch-syncs to Redis (#9357); TPM never did → effective ceiling `tpm × N_pods` |
| Virtual-key auth cache | **No** unless `litellm_settings.enable_redis_auth_cache: true` (`caching.md:26-55`) | 60s per-pod TTL (`proxy_server.py:1396-1397`); key revocation/team deletion lags per pod |
| Spend → DB buffer | Yes — RPUSH/LPOP lists | **At-most-once**: leader LPOPs then commits; "Data already popped from Redis may be lost" (`db_spend_update_writer.py:899`, `:1067`); drain capped at `MAX_REDIS_BUFFER_DEQUEUE_COUNT=100`/cycle → sustained overproduction grows the list unboundedly |
| Cron jobs (budget reset, key rotation, session cleanup, prometheus budget metrics, CloudZero/Vantage/FOCUS export) | Yes — `PodLockManager` (SET NX EX + Lua compare-and-delete, `pod_lock_manager.py:153-186`) | Lock TTL `DEFAULT_CRON_JOB_LOCK_TTL_SECONDS=60`; call sites guard on `pod_lock_manager.redis_cache` — **no Redis = every pod runs the job unlocked**, not "job never runs" |
| Shared health checks | Yes | `release_health_check_lock` is non-atomic GET-then-DEL (`shared_health_check_manager.py:96-98`) — unlike PodLockManager |
| DB config params | Cached per pod | `litellm_config_cache` 60s both tiers (`utils.py:2842-2848`); `invalidate_config_param` deletes local + Redis but **no pub/sub exists in the tree** — other pods serve stale config up to 60s |
| Response cache | Yes (when redis) | **No in-memory tier** — `Cache.cache` is a bare `RedisCache`: every lookup is a Redis GET on the request path |

## The four staleness constants

- **1s** — `DEFAULT_REDIS_SYNC_INTERVAL` (`constants.py:31`): flush cadence for routing/budget increment queues.
- **10s** — `default_redis_batch_cache_expiry` (`dual_cache.py:64,74-76`; settable via `cache_params.default_redis_batch_cache_expiry`, **undocumented**): `DualCache.async_batch_get_cache` serves the in-memory copy and skips Redis for this long per key (`dual_cache.py:250-284`, `301-310`). This is the real staleness bound for `lowest_tpm_rpm_v2.async_get_available_deployments` (`lowest_tpm_rpm_v2.py:466`) and `CooldownCache.async_get_active_cooldowns` (`cooldown_cache.py:114`).
- **60s** — in-memory TTLs: `spend_counter_cache`, `litellm_config_cache`, `user_api_key_cache` (`user_api_key_cache_ttl`), cron lock TTL.
- **3600s** — `PARALLEL_REQUEST_SLOT_TTL_SECONDS` (hardcoded): the only self-heal for leaked parallel slots (relevant to open #34534, MCP slot leak).

## In-memory tier semantics that surprise

- **Every DualCache's local tier is `InMemoryCache(max_size_in_memory=200, default_ttl=600)`** (`in_memory_cache.py:29-43`) — 200 entries, not configurable. >200 hot keys (keys × descriptors across tenants) thrash the local tier; correctness survives while Redis is healthy because Redis is authoritative, but the *fallback* paths and the local parallel-slot registry silently lose state under pressure.
- **TTL is not refreshed on rewrite** (`allow_ttl_override`, `in_memory_cache.py:143-153`): a counter keeps its original expiry regardless of updates — bounds, but does not eliminate, the local over-reject window after the shared window rolls.
- **`DualCache.async_delete_cache` clears this pod + Redis only** (`dual_cache.py:478-485`); cross-pod invalidation does not exist (no pubsub/subscribe anywhere except GCS logging). Deleted models ghost in other workers (open #27852); customer mutations don't invalidate Redis end-user counters (open #31838/#31839).

## Multi-instance correctness checklist

1. `GET /coordination_redis/settings` → `source` non-null on every pod.
2. `enable_redis_auth_cache: true` if key revocation must propagate in less than 60s/pod.
3. `fail_closed_budget_enforcement: true` if budget overruns cost real money.
4. Accept that deployment-level TPM (#27736) and a few budget scopes (`model_max_budget` per-pod reads, #33325/#33330) are per-pod on current versions — size limits with `× N_pods` headroom in mind or enforce at key/team level, which is shared.
5. End-to-end 429 canary after every failover (see `silent-degradation.md`).
