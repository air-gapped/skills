# Silent degradation to per-pod enforcement — the headline failure mode

LiteLLM's coordination paths are written fail-open: catch any Redis/Lua exception, log at `warning`/`debug`, fall back to in-memory per-pod state, return 200. There is **no metric, no health-endpoint signal, and no fail-closed option for rate limits** (`grep fail_closed parallel_request_limiter_v3.py` → empty; budgets have `fail_closed_budget_enforcement`, `proxy_server.py:2138-2139`, documented at `config_settings.md:149`).

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29).

## The fallback catalogue

| Location | What falls back | In-memory substitute |
|---|---|---|
| `parallel_request_limiter_v3.py:775-782` | whole key-group rate check | `in_memory_cache_sliding_window` |
| `parallel_request_limiter_v3.py:1053-1059` | `max_parallel_requests` gauge acquire | local gauge |
| `parallel_request_limiter_v3.py:1022-1025` | gauge count read | local mirror |
| `parallel_request_limiter_v3.py:1183-1191` | slot release | local release (Redis slot leaks until 3600s TTL) |
| `parallel_request_limiter_v3.py:1352-1372` | the atomic check-and-increment | refund attempt + in-memory |
| `dual_cache.py:406-411`, `:435-440` | `async_increment` | returns the in-memory increment result |
| `base_routing_strategy.py:142-146` | usage-based-routing increment flush | **queue dropped entirely** (`self.redis_increment_operation_queue = []`) |
| `budget_limiter.py:543-545` | provider/tag budget flush | **queue dropped entirely** |

Two structural amplifiers:

1. **The shared circuit breaker.** `RedisCircuitBreaker` (`redis_cache.py:99-190`): after `REDIS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5` consecutive failures it raises *without a network call* for `REDIS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60`s, and that raise is caught by every fallback above. When the coordination client is the borrowed response-cache client (the common pre-v1.93 topology and the default whenever `cache: true` supplies the client), **five failing cache writes fast-fail rate limiting and spend tracking for a minute** — cache health is coupled to enforcement health. Knobs: `REDIS_CIRCUIT_BREAKER_{ENABLED,FAILURE_THRESHOLD,RECOVERY_TIMEOUT}`. A dedicated `coordination_redis` block decouples the clients (v1.93.0+).
2. **Swallowed errors starve the breaker where it would help.** Open #34299: `RedisCache.async_set_cache` swallows exceptions itself, so its failures never count toward the breaker — the breaker trips on read paths while write paths degrade invisibly.

## Environment-shaped triggers

- **SCRIPT-blocking Redis proxies** (Codis, Twemproxy, some managed proxies): the v3 limiter is Lua/EVALSHA-based; blocked scripts → every check takes the `:775-782` fallback → fleet limit becomes `limit × pods`. Open #32232 (fix PR #32230 pending at sweep time).
- **Redis restarts / failovers**: EVALSHA `NOSCRIPT` after script-cache flush was mishandled on cluster until #25049 (closed 2026-07-16).
- **redis-py 5.3.1 pin regression** (open #34614, v1.93.0): `TypeError: ... unexpected keyword argument 'ssl_check_hostname'` on client construction kills cache *and* budget counters at startup; reproduces against Valkey.
- **Clean-miss fallback**: a Redis read that returns nothing falls back to stale per-pod spend → end-user budget bypass (open #34238).

## What to alert on

There is no metric; alert on logs. Watch for (exact substrings, `verbose_proxy_logger.warning`/`verbose_router_logger` emitters near the lines above — re-grep on the deployed tag since strings drift):

- `In-memory fallback` / `falling back to in-memory` near `parallel_request_limiter_v3`
- `Redis increment failed` / the queue-drop paths in `base_routing_strategy.py:142-146`, `budget_limiter.py:543-545`
- `Circuit breaker` open/half-open transitions (`redis_cache.py:99-190`)
- `Got exception from REDIS` (connection pool exhaustion — see `config-reference.md` §connection-churn)
- `Data already popped from Redis may be lost` (`db_spend_update_writer.py:899`, `:1067`) — spend rows silently dropped

Cheap black-box canary: from outside, drive one virtual key past its RPM limit across all pods simultaneously; if observed throughput at 429-onset ≈ `limit × N_pods`, the fleet is per-pod. Repeat after any Redis failover.

## Budget-specific posture

`fail_closed_budget_enforcement: true` makes budget checks reject when the atomic reservation fails (fixed to actually do so in #33923, closed 2026-07-23 — earlier versions failed open despite the flag). The budget family of open issues (admission at exact limit #33321, `max_budget_limiter` failing open on lookup errors #33323-family, pod-local `model_max_budget` reads #33325/#33330) is catalogued in `known-issues.md`; the flag closes the Redis-failure hole, not the semantics bugs.
