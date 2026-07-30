# Config knob inventory, connection behavior, and doc corrections

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29).

## How env vars actually work

`_get_redis_kwargs()` builds the supported `REDIS_<KWARG>` set by **introspecting `redis.Redis.__init__` of the installed redis-py at import time** (`_redis.py:38-61`, `116-130`). So `REDIS_DB`, `REDIS_MAX_CONNECTIONS`, `REDIS_RETRY_ON_TIMEOUT`, `REDIS_SOCKET_KEEPALIVE`, `REDIS_HEALTH_CHECK_INTERVAL`, … exist because redis-py has those kwargs — and the set silently shifts when a transitive dependency bumps redis-py. All env values arrive as **strings**; redis-py tolerates some, not others (see `REDIS_SOCKET_TIMEOUT` below).

`redis` itself is **not a declared dependency**: `pyproject.toml` has only `redisvl`, `types-redis`, `fakeredis`; redis-py comes transitively via `rq>=2.7.0` (proxy extra) and `redisvl` (extra_proxy); `uv.lock` resolves **redis 5.3.1** (the #34614 pin). `pip install litellm` + `litellm.Cache(type="redis")` fails at `import redis` (`_redis.py:17`).

Kwarg precedence: explicit kwargs (including `RedisCache.__init__` defaults!) beat env (`_get_redis_client_logic`, `_redis.py:339-342`). An explicitly configured target (host/startup_nodes/sentinel_nodes) outranks `REDIS_URL` from the environment (`:330-337`).

## Documented knobs

`docs/proxy/config_settings.md` + `docs/proxy/caching.md` cover: `REDIS_HOST/PORT/PASSWORD/USERNAME/URL/SSL/SSL_CERT_REQS`, `REDIS_CLUSTER_NODES`, `REDIS_SENTINEL_NODES/SENTINEL_PASSWORD/SERVICE_NAME`, `REDIS_GCP_SERVICE_ACCOUNT/GCP_SSL_CA_CERTS`, `REDIS_SOCKET_TIMEOUT`, `REDIS_CONNECTION_POOL_TIMEOUT`, `REDIS_CIRCUIT_BREAKER_{ENABLED,FAILURE_THRESHOLD,RECOVERY_TIMEOUT}`, `DEFAULT_REDIS_SYNC_INTERVAL`, `DEFAULT_REDIS_MAJOR_VERSION`, `DEFAULT_MAX_REDIS_BATCH_CACHE_SIZE`, `MAX_REDIS_BUFFER_DEQUEUE_COUNT`, `LITELLM_RATE_LIMIT_WINDOW_SIZE`, `LITELLM_TPM_TOKEN_RESERVATION_ENABLED`, `LEGACY_MULTI_INSTANCE_RATE_LIMITING`, `DEFAULT_CRON_JOB_LOCK_TTL_SECONDS`, `DEFAULT_SHARED_HEALTH_CHECK_{TTL,LOCK_TTL}`, `LITELLM_KEY_ROTATION_LOCK_TTL_SECONDS`, `DEFAULT_IN_MEMORY_TTL`, `VALKEY_HOST/PORT/PASSWORD`.

## Exists in code, not in docs (zero grep hits in the docs corpus)

| Knob | Location | Why it matters |
|---|---|---|
| `general_settings.coordination_redis` (full block) | `_types.py:2192-2217`, `proxy_server.py:4070-4102` | see `coordination-redis.md` — the headline undocumented surface, incl. UI/DB persistence |
| `cache_params.default_redis_batch_cache_expiry` | `dual_cache.py:64,74-76`; default **10s** | the routing/cooldown staleness bound |
| `REDIS_AZURE_AD_TOKEN` + `AZURE_CLIENT_ID/TENANT_ID/CLIENT_SECRET` for Redis | `_redis.py:397-429` | Entra ID auth for Azure Managed Redis, fully implemented, undocumented |
| `REDIS_CLUSTER_HEALTH_CHECK_INTERVAL` | `constants.py:347-350` — **hardcoded 25, not env-read** | cluster conns get `health_check_interval=25` + forced keepalive (`_redis.py:603-604`); not tunable |
| `PARALLEL_REQUEST_SLOT_TTL_SECONDS = 3600` | `parallel_request_limiter_v3.py:319` — hardcoded | longest request `max_parallel_requests` tracks; also the leak self-heal bound |
| `InMemoryCache.max_size_in_memory = 200` | `in_memory_cache.py:29-43` | hard cap on the local tier of every DualCache; not configurable |
| `spend_counter_cache` / `litellm_config_cache` / `cli_sso_session_cache` TTLs (60s) | `proxy_server.py:2007-2010`, `utils.py:2842-2848` | per-pod staleness on budgets and DB config |

## Documented knobs that are no-ops or wrong

- **`REDIS_CONNECTION_POOL_KWARGS`** (`docs/proxy/caching.md:334`, example `'{"max_connections": 20}'`): `connection_pool_kwargs` is not a `redis.Redis.__init__` argument → never in the introspected mapping → silently discarded. Working alternative: `cache_params.max_connections` (handled `_redis.py:669-677` for the URL path, passed to `BlockingConnectionPool` otherwise) — which `docs/proxy/prod.md:190` correctly recommends.
- **`REDIS_SOCKET_TIMEOUT`** (`config_settings.md:1146`, "default 0.1"): (a) `RedisCache.__init__` default `socket_timeout=5.0` (`redis_cache.py:204`) lands in overrides and beats the env var on the main client; (b) the sentinel initialisers' `setdefault` is likewise pre-empted; (c) in the one path where it applies (`_build_redis_usage_cache_from_environment`) it arrives as the string `"0.1"` handed to `socket.settimeout()`. The docs contradict themselves two lines apart (`caching.md:320` "suggested mechanism" vs `:338` "avoid using REDIS_* env for non-string params").
- **`docs/proxy/users.md:1116-1127` "Multi-instance rate limiting"** describes the **v1** limiter ("in-memory cache synced with redis every 0.01s", drift ≤10 requests). The default is v3 (`PROXY_HOOKS["parallel_request_limiter"] = _PROXY_MaxParallelRequestsHandler_v3`, `proxy/hooks/__init__.py:21`), Lua-per-request; no 0.01s sync exists; `DEFAULT_REDIS_SYNC_INTERVAL` is 1s (`constants.py:31`). `LEGACY_MULTI_INSTANCE_RATE_LIMITING=true` restores v1 (`hooks/__init__.py:31-32`).
- **`docs/proxy/prod.md:161` "Redis (7.0 or newer)"**: the code carries `<7` compat branches for `LPOP count` (`redis_cache.py:1587-1593`, `1644-1670`) via `DEFAULT_REDIS_MAJOR_VERSION`; the real floor is lower — but the version probe fails on cluster (see `cluster-sentinel.md`), so on cluster the assumed version is always 7.
- **#34727 (open docs issue)**: caching docs still warn against `REDIS_URL` in prod for perf; the underlying ~2-connections-per-request bug (#3188, 2024) is fixed by ~v1.95 (measured 650 vs 690 req/s). Still true: URL mode drops kwargs not encoded in the URL string.

## Connection churn (§connection-churn)

The mechanism behind growing `connected_clients` and `Got exception from REDIS No connection available`:

1. Every `RedisCache.__init__` builds a **sync client** (`redis_cache.py:232`) + a connection pool (`:235`) — the sync client is barely used (startup `info()`/`ping()`, plus the sync cooldown-write path) but holds connections.
2. The **async** client is cached in `litellm.in_memory_llm_clients_cache` — an `InMemoryCache` with `max_size_in_memory=200, default_ttl=600` (`_lazy_imports.py:396-398`). After **600s** the entry expires and `init_async_client` (`redis_cache.py:334-352`) builds a **new `BlockingConnectionPool` + client without disconnecting the old one** — the class docstring admits it (`llm_caching_handler.py:13-19`, which also claims "1 hour" TTL; the code says 600s).
3. The same 200-entry cache holds every OpenAI/Azure/httpx client, so size pressure can evict the Redis client **early** (`in_memory_cache.py:102-137` evicts by earliest expiration).
4. The pool built in `__init__` is orphaned on the first `init_async_client` miss.

Mitigations: cap `maxclients` sanely on the Valkey side and watch churn rather than absolute count; set `cache_params.max_connections`; treat step-function growth every ~10 min as this bug, not load.

## Sync/async seams (§sync-async)

- **Sync writes on the async path**: `CooldownCache.add_deployment_to_cooldown` → sync `DualCache.set_cache` → blocking `redis_client.set()` (`cooldown_cache.py:89-93`), called from async router code (`router.py:7097`, `:7356`) and `proxy_server.py:3275`. `CooldownCache.get_min_cooldown` (sync) → `DualCache.batch_get_cache`, which **spawns a ThreadPoolExecutor + fresh event loop per call** and blocks on `future.result()` (`dual_cache.py:184-215`) — invoked from async error paths (`handle_error.py:79`, `router.py:11282+`): every "no healthy deployment" error blocks the loop on a threaded MGET.
- **Serialization asymmetry**: sync `set_cache` writes `str(value)` (`redis_cache.py:400`); `async_set_cache` writes `json.dumps` (`:636`). Reads try `json.loads` then bare `ast.literal_eval` (`:960-972`) — a sync-written value `literal_eval` rejects raises, is swallowed, and reads as `None` — i.e. a cooldown that silently doesn't exist. Error handling is asymmetric too: `set_cache` swallows (`:410-412`), `increment_cache` re-raises (`:459-468`).
- Startup does blocking `info()` (`:248`) and `ping()` (`:283`) on the event loop.
- `_pretty_print_redis_config` renders a rich panel to stdout when DEBUG (`_redis.py:696-781`) — surprising in JSON log pipelines.
- `DualCache.batch_get_cache` passes `locals()` including `kwargs` → callee receives `kwargs={'kwargs': {}}` (`dual_cache.py:191-199`). Harmless, fragile.

## Well-documented corners — cite, don't restate

`valkey-semantic`/ElastiCache constraints (`docs/caching/all_caches.md:334-399`, `caching.md:413-457`), `enable_redis_auth_cache` (`caching.md:26-55`), `use_redis_transaction_buffer` (`prod.md:181-190`), `fail_closed_budget_enforcement` (`users.md:737-746`), shared health checks page.
