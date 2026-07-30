---
name: litellm-valkey
description: |-
  Run LiteLLM proxy multi-pod with Redis/Valkey (standalone, Sentinel, or Cluster) so rate limits, budgets, and router state are actually shared across pods. Centerpiece: LiteLLM's dominant failure mode is SILENT fallback from Redis to per-pod in-memory enforcement (≥6 independent code paths, log-level warning, no metric) — a fleet quietly enforces N× its configured limits. Covers the 4-way coordination-Redis resolution order (incl. the undocumented `general_settings.coordination_redis` block, first-class since v1.93.0, and the DB-persisted UI value that silently outranks the config file), Sentinel/Cluster support per subsystem with fix versions, the per-pod-vs-shared truth table with real staleness bounds, documented knobs that are no-ops, and the open-issue catalog (counter drift, connection churn, ssl_check_hostname).
when_to_use: |-
  Trigger on "litellm redis", "litellm valkey", "litellm sentinel", "litellm redis cluster", "litellm multi-pod", "litellm rate limit not enforced", "litellm budget not enforced", "BudgetExceededError", "litellm spend wrong", "coordination_redis", "redis_usage_cache", "router_settings redis", "REDIS_SENTINEL_NODES", "REDIS_CLUSTER_NODES", "litellm helm redis", "parallel_request_limiter", "max_parallel_requests stuck", "fail_closed_budget_enforcement", "No connection available". Also on symptoms: "limits only work sometimes", "each pod has its own counter", "flushed redis and it fixed itself". NOT for response-cache tuning, the management REST API (litellm-api), or generic Redis/Valkey ops.
---

# LiteLLM proxy + Redis/Valkey multi-pod — operator reference

Target: operating LiteLLM proxy with 2+ replicas (typically the in-repo Helm chart) where Redis or Valkey is supposed to make rate limits, spend/budget enforcement, cooldowns, and locks fleet-wide. Grounded in source at `4d543245` (v1.95.0-dev, 2026-07-29; latest stable v1.94.0) plus a GitHub-issue sweep of the same date. LiteLLM releases weekly and fixes land fast — treat every claim as version-stamped, and re-verify on the deployed tag.

Sibling skill: the proxy's management REST API (keys, teams, budgets semantics) is **`litellm-api`**. Migrating the Redis itself to Valkey is **`redis-to-valkey`**.

The single most important thing to internalize: **when Redis fails — or is never wired in — LiteLLM does not fail. It silently enforces everything per-pod.** No 5xx, no metric, log-level `warning` at best. A fleet of N pods enforces N× every rate limit and lets budgets drift. Verifying that coordination is *actually* shared is the operator's job; nothing in the product surfaces the loss. Read `references/silent-degradation.md` first.

## Which Redis am I actually coordinating through?

The coordination Redis (rate limits, spend counters, pod locks — NOT the response cache) is resolved in this precedence order (`proxy_server.py` `_init_coordination_redis` → `_init_cache`):

1. **`general_settings.coordination_redis`** in config.yaml — the only clean way to point coordination at its own Redis. First-class since **v1.93.0** (PR #32661, 2026-07-11). **Documented nowhere** as of 2026-07-30.
2. **A `coordination_redis` block persisted in the DB by the Admin UI** — applied after the config file, so it **silently outranks** it. GitOps drift hazard.
3. **Borrowing the response-cache client** — iff `litellm_settings.cache: true` and the cache backend is plain Redis (`RedisCache`/`RedisClusterCache`). A semantic/disk/s3 cache is not borrowable.
4. **`REDIS_*` env fallback** — but steps 3 and 4 live inside `_init_cache`, which only runs on the `cache: true` config branch. **`REDIS_HOST` alone, with no `cache: true` and no `coordination_redis` block, coordinates nothing** — every limit is per-pod while `docs/proxy/prod.md` claims env Redis "shares rate limit counters across instances".

Two more traps in the same area:

- Open issue **#26233**: putting *any* key in `cache_params` (even `mode: default_off`) makes the proxy ignore `REDIS_*` env vars for the usage cache — silent in-memory fallback.
- `Router` only creates its own Redis cache when `redis_url` or `redis_host` **and** `redis_port` are set (`router.py:500`); `redis_host` without `redis_port` silently yields an in-memory router cache, and the router does not read env vars itself. (The proxy back-fills `router.cache.redis_cache` from the coordination Redis when one exists.)

**Verify, don't assume:** `GET /coordination_redis/settings` (admin) returns `{"values": {...redacted config...}, "fields": [...], "source": "coordination_redis"|"cache_backend"|"environment"|null}` — `source` names which of the four sources won; **null means per-pod mode**. `POST /coordination_redis/settings/test` pings with candidate params (`{"settings": {}}` tests the saved config). Both undocumented. `GET /cache/ping` tests **only the response cache** — it is blind to a separate coordination Redis. `scripts/litellm-redis-preflight.sh` runs the whole check.

## Sentinel and Cluster — support matrix that moved late

A commonly-remembered version of this is "one function supported Sentinel, the other Cluster". The real historical split: the **response cache** (`cache_params`) supported both Sentinel and Cluster for years; the **core/coordination path had no direct Sentinel config at all until v1.93.0** (and its Cluster wiring had gaps, #22748). The feature request for Sentinel in `router_settings` (#22796) was never implemented — the stale bot closed it 2026-06-11; `coordination_redis` landed by another route a month later.

| Capability | Since | Notes |
|---|---|---|
| Sentinel for coordination (`coordination_redis.sentinel_nodes` + `service_name`) | **v1.93.0** | PR #32661. Helm chart renders it from `redis.sentinel.enabled` + `redis.sentinel.masterSet` (PR #32662, same release) |
| Sentinel via `REDIS_SENTINEL_NODES` env for the usage cache | v1.93.0 | `_environment_has_redis_connection_target` counts it — but only reachable per the resolution rules above |
| Cluster for coordination (`startup_nodes` / `REDIS_CLUSTER_NODES`) | earlier, gaps until ~v1.9x | router-path `REDIS_CLUSTER_NODES` was ignored (#22748); EVALSHA slot fallback fixed 2026-07 (#25049) |
| Sentinel fixes an older image is missing | ≤ mid-2026 | wrong password kwarg (#20734), SSL/kwargs not forwarded to master (#21197), DB index (#10276) |

Cluster mode changes semantics, not just topology: the v3 rate limiter's all-or-nothing check across key/user/team descriptors degrades to per-slot Lua calls with best-effort refunds (a crash mid-loop inflates counters until window expiry), `SCAN`-based paths silently return `[]`, and the version probe fails (per-node `INFO`) so Redis ≤6 clusters get sent Redis-7 command forms. Details + Sentinel rough edges: `references/cluster-sentinel.md`.

## Triage table

| Symptom | Probable cause | Where |
|---|---|---|
| Limits enforce ~N× configured across N pods | Coordination never wired (resolution order above) or silent fallback after Redis errors | `references/coordination-redis.md`, `references/silent-degradation.md` |
| Rate limiting AND budgets break together for ~60s bursts | Shared `RedisCircuitBreaker` on the borrowed cache client: 5 failed response-cache ops fast-fail coordination for `REDIS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60s` | `references/silent-degradation.md` |
| False `BudgetExceededError`, `/key/info` shows spend under budget; Redis flush "fixes" it | Redis spend counters inflate/drift (open #30460, #27735); no invalidation pub/sub exists | `references/known-issues.md` §spend-drift |
| Effective RPM/TPM is half of configured | v3 limiter double-counts team per-model descriptors (open #34140) | `references/known-issues.md` |
| Deployment TPM ceiling = `tpm × N_pods`, zero 429s | Deployment-level TPM is per-pod — RPM batch-syncs to Redis, TPM never did (open #27736) | `references/known-issues.md` |
| Key wedges into 100% 429s until proxy restart | MCP tool calls leak `max_parallel_requests` slots (open #34534); slot TTL self-heal is 3600s | `references/known-issues.md` |
| `TypeError: ... 'ssl_check_hostname'` kills cache + budget counters | redis-py 5.3.1 pin regression on v1.93.0 (open #34614) — reproduces with Valkey | `references/known-issues.md` |
| Rate limits become per-pod behind Codis/Twemproxy/SCRIPT-blocking proxies | Lua/EVALSHA blocked → silent in-memory fallback (open #32232) | `references/silent-degradation.md` |
| Redis `connected_clients` grows; `No connection available` | Async client + pool rebuilt every 600s (LLM-client cache TTL), old pool never disconnected; sync client per RedisCache mostly unused | `references/config-reference.md` §connection-churn |
| Response/tool-call cross-talk between users | Open #25447 (multi-replica + cluster, also seen on single Redis). Workaround: `cache_params.supported_call_types: []` | `references/known-issues.md` |
| Cooldowns randomly "don't exist"; event loop stalls on errors | Sync blocking writes on the cooldown path + `str()` vs `json.dumps` serialization asymmetry | `references/config-reference.md` §sync-async |
| Two proxies on one Valkey DB corrupt each other | `coordination_redis` has **no namespace field** — `cronjob_lock:*`, spend buffer, `{api_key:…}:requests` collide | `references/coordination-redis.md` §namespacing |
| Config/key changes take a minute to apply on other pods | No cross-pod invalidation (no pub/sub in the tree); 60s in-memory TTLs | `references/shared-vs-perpod.md` |

## Per-pod vs shared — the numbers that matter

Full table in `references/shared-vs-perpod.md`. The staleness bounds to memorize: **1s** (usage-based-routing/budget-router increments flush to Redis on `DEFAULT_REDIS_SYNC_INTERVAL`), **10s** (`DualCache` batch reads throttled per key by undocumented `default_redis_batch_cache_expiry` — this is why routing and cooldown reads lag), **60s** (in-memory tiers for budgets/auth/config; `user_api_key_cache` is per-pod-only unless `enable_redis_auth_cache: true`), **3600s** (leaked parallel-request slots self-heal). The spend→DB pipeline is **at-most-once**: the code's own log admits "Data already popped from Redis may be lost".

## Production config that actually coordinates

```yaml
general_settings:
  coordination_redis:          # v1.93.0+; undocumented; wins over cache-borrow + env
    sentinel_nodes: [["valkey-sentinel-0", 26379], ["valkey-sentinel-1", 26379], ["valkey-sentinel-2", 26379]]
    service_name: "mymaster"
    password: os.environ/REDIS_PASSWORD          # data-node auth
    # sentinel_password: os.environ/SENTINEL_PW  # only if sentinels themselves require auth
  fail_closed_budget_enforcement: true   # budgets reject on Redis failure — no rate-limit equivalent exists
litellm_settings:
  cache: true                  # optional response cache; independent of coordination since v1.93.0
  cache_params: {type: redis, host: ..., port: ...}
  enable_redis_auth_cache: true  # else key revocation lags 60s per pod
```

Helm chart wiring (`redis.sentinel.enabled` renders the coordination block from `masterSet`; precedence rules; the Admin-UI DB copy that beats all of it): `references/coordination-redis.md` §Helm. After any Admin-UI use, re-check `GET /coordination_redis/settings`.

## Gotchas that cost hours

- **`REDIS_CONNECTION_POOL_KWARGS` (documented) is a no-op** — `connection_pool_kwargs` is not a `redis.Redis.__init__` arg so the env mapping drops it. The working knob is `cache_params.max_connections`.
- **`REDIS_SOCKET_TIMEOUT` (documented, "default 0.1") is a no-op on the main client** — the `RedisCache.__init__` default of 5.0 always wins; in the one env path where it applies it arrives as the string `"0.1"`.
- **`docs/proxy/users.md` "Multi-instance rate limiting" describes the legacy v1 limiter** (0.01s sync loop). The default is the v3 Lua-per-request limiter (`LEGACY_MULTI_INSTANCE_RATE_LIMITING=true` restores v1); no 0.01s sync exists in the tree.
- **`redis` is not a declared dependency** of the `litellm` package — it arrives transitively (`rq`, `redisvl`; lockfile resolves redis-py 5.3.1). SDK-only installs fail at `import redis`; the supported `REDIS_*` env-var set is *introspected from the installed redis-py at import time* and can shift on a transitive bump.
- **`POST /cache/flushall` wipes coordination too** when the cache client is borrowed (the common case): rate-limit counters, spend counters, spend buffer, cron locks — and any co-tenant of the instance.
- **Valkey works but is invisible**: Valkey-specific code exists (`valkey_semantic_cache.py`, ElastiCache-Valkey float-version parse fix #16207) yet `grep -ri valkey docs/` finds nothing. Standard `cache_params`/`coordination_redis` against Valkey behaves as Redis 7.2; `valkey-semantic` explicitly rejects cluster-mode endpoints (good error, and one of the few documented bits).
- The **v3 limiter's odd key shapes are load-bearing**: `{api_key:sk-…}:requests` — the braces are cluster hash tags, not a bug. Don't "clean them up".

## Task → reference routing

| Task | Read |
|---|---|
| Wire/verify coordination Redis; namespacing; the 4 sources; endpoints | `references/coordination-redis.md` |
| Alert on silent degradation; log strings to watch; circuit-breaker coupling | `references/silent-degradation.md` |
| What's shared vs per-pod, exact staleness, which knob controls each | `references/shared-vs-perpod.md` |
| Sentinel/Cluster wiring, history, per-topology sharp edges, fix versions | `references/cluster-sentinel.md` |
| "Is this a known bug on my version?" — the issue catalog | `references/known-issues.md` |
| Full knob inventory (documented vs not), connection churn, sync/async seams | `references/config-reference.md` |
| Verify a claim / freshen | `references/sources.md` |

### Scripts

- **`${CLAUDE_SKILL_DIR}/scripts/litellm-redis-preflight.sh <base-url> <admin-key>`** — asks the proxy which coordination source won (`/coordination_redis/settings`), pings it (`/settings/test`), pings the response cache (`/cache/ping`), and prints the per-pod-enforcement warning if no source is active. Execution-tested against a mock proxy (source-present → exit 0, `source: null` → exit 2).

## Non-negotiables before trusting multi-pod enforcement

- **Prove coordination is wired**: `GET /coordination_redis/settings` must name a source. Env vars alone without `cache: true` or a `coordination_redis` block = per-pod everything.
- **≥ v1.93.0** for Sentinel on the core path and for independent coordination config at all. On v1.93.0 specifically, check #34614 (redis-py 5.3.1 `ssl_check_hostname`) before rolling out.
- **`fail_closed_budget_enforcement: true`** if budget overrun costs real money — the default fails open, and rate limits *always* fail open (no closed mode exists).
- **Alert on the degradation log strings** (`references/silent-degradation.md` has the exact list) — they are the only signal that the fleet has stopped coordinating.
- **One Redis logical DB per LiteLLM deployment** — coordination keys are unprefixed; sharing a DB across deployments collides locks and counters.
- Load-test the actual limit: run > limit RPM across all pods and confirm 429s at ~1× (not ~N×) the configured value. This is the only end-to-end proof.
