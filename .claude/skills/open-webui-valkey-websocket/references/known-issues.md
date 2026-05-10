# Known issues, fixes shipped, and what to watch

Status as of 2026-05-10. Cross-reference for the triage table in `SKILL.md` and the timeline in `references/icons-thumbnails.md`.

## Open issues that affect multi-pod

### #23733 — Socket.IO frame amplification (THE BIG ONE)

Opened 2026-04-14, status open. The structural bug. Full deep-dive in `references/issue-23733.md`. Mitigation: `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=10`.

### #15162 — direct-connection chat with `workers > 1`

Opened 2025-06-20. With either `UVICORN_WORKERS > 1` or multi-pod and `WEBSOCKET_MANAGER=redis`, the WebSocket connection and the `/api/v1/completions` request can land on different worker instances. The receiving worker has no in-memory state for the WS session, so the request hangs forever waiting for a response that goes to the other worker.

PR #22402 (merged Mar 2026) added Redis pub/sub fan-out for direct-connection channel events. PR #24099/#24100 (Apr/May 2026) fixed task generation for direct-connection chats. **Issue still open** — pattern keeps appearing in new endpoints.

Mitigation: keep `UVICORN_WORKERS=1` and stay on ≥0.9.3 to pick up #22402.

### #19840 — RedisCluster `publish()` AttributeError on `/api/tasks/stop/{id}`

Opened 2025-12-09, still open as of May 2026. The redis-py `RedisCluster` client doesn't expose `publish()` (cluster mode requires `spublish` to a specific node). The `tasks.py` stop-cancellation path calls `redis.publish(...)`, raises `AttributeError`, stop-button is broken on RedisCluster setups.

Multiple proposed fixes (`spublish`, `execute_command`, PR #20803) but none merged.

**Mitigation: don't use Redis Cluster.** Use Sentinel. (Note: this is **not** a recommendation — Sentinel is the operating reality for this environment; this is a warning *against* RedisCluster.)

### #23987 — Sentinel coroutine-not-awaited regression in 0.9.1 (FIXED in 0.9.4)

Opened 2026-04-22, **closed 2026-05-08** by tjbck. `SentinelRedisProxy.__getattr__` regression introduced via the `/ready` endpoint PR (#22507) caused readiness probe and login to fail with `'coroutine' object is not callable`. Fix shipped in 0.9.4 (released 2026-05-09). On any 0.9.0–0.9.3 deployment with Sentinel: upgrade to 0.9.4 immediately, or pin to 0.9.0 if upgrade is blocked. **Validate the readiness probe + login flow on a staging cluster after upgrade.**

### #23939 — Loading and login issues on 0.9.0/0.9.1

Opened 2026-04. 39 comments. Includes a `KeyError` in socketio's `enter_room` (bidict) on connect — Socket.IO state corruption on connect path. `Classic298`'s diagnosis pivoted the thread to NFS-backed SQLite I/O ("MUST use Postgres for multi-replica"), but the underlying Socket.IO breakage on 0.9.0/0.9.1 is real and a separate concern.

### #23650 — PR open: evict Socket.IO room subscriptions when access revoked

Opened 2026-04-12. Stale Socket.IO rooms persist across pod restarts and access revocations. Not yet merged.

## Fixed issues — what shipped, when

### #22734 — RedisDict.set() race condition

Closed (fix in 0.8.x dev, then 0.9.0). `RedisDict.set()` did pipelined `DELETE + HSET` (non-atomic). Concurrent reader saw empty hash → "Model not found" intermittents at scale. Fix: HSET first, HDEL only stale keys (no DELETE-then-HSET window). `socket/utils.py:84-100`.

Comment in fixed code: *"We never DELETE the whole hash — this eliminates the race window where concurrent readers would see an empty models dict."*

### #21410 — Memory leak in SESSION_POOL, USAGE_POOL, YdocManager

Closed. `RedisDict` had no TTL/eviction; `USAGE_POOL` not cleaned on disconnect; `YdocManager._updates` grew unboundedly. Both Redis RAM and Python RAM grew without bound until restart. Addressed by PR #16693 ("Session TTL management, periodic cleanup", 2026-02-16) and the v0.9 socket refactor.

### #18073 — Redis ReadOnlyError after upgrade to 0.6.32 (Oct 2025)

Closed. PR #17223 introduced `starsessions` Redis backend without a Sentinel-aware client → writes went to read-only replica. Fixed in `861953fd2d`.

### #19401 — Redis Sentinel auth bug (password not passed to Sentinel client)

Closed Nov 2025.

### #16979 — RedisLock REDIS_KEY_PREFIX bug

Closed Aug 2025. Lock keys ignored prefix → collisions across deployments sharing one Redis. Fixed.

### #16157 — Backend cannot connect to Redis Cluster

Closed Aug 2025. Foundational cluster-mode work. (Note: even with this fixed, Cluster has the unfixed #19840 `publish()` bug; Sentinel is the way.)

### #20142 — `YDocManager.remove_user_from_all_documents` throws on WebSocket disconnect with Sentinel

Closed Dec 2025.

### #18223 — Redis exception in ydoc manager when working with AWS ElastiCache

Closed Oct 2025.

### #18950 — `/api/models` slow and very heavy with larger instances

Closed Nov 2025. 4.3 MB payload for 350 models because `meta.profile_image_url` returned for every model, plus `get_filtered_models` calling `has_access` per-model with no preloaded group IDs (~4.7s → ~0.2s after fix). PR #19097 + tjbck strip commit. Full chronology in `references/icons-thumbnails.md`.

### #11934 — Large Base64-Encoded Images in `model.meta` cause performance problems

Closed. Mar 2025 — this is the originally-flagged version of the issue eventually fixed in 0.6.37.

### #12325 — Microsoft SSO profile pictures cause severe degradation

Closed. 30s admin loads with 5 users — admin panel fetched full base64 SSO avatars (1–10 MB each) on every page. Fixed by allowing `OAUTH_PICTURE_CLAIM=""` / `OAUTH_UPDATE_PICTURE_ON_LOGIN=false`.

### #14340 — Multi-pod task cancellation broken

Closed (Jun 2025). `tasks.stop` only knew about its local pod's in-memory task dict. Fixed via Redis pub/sub broadcast in commits `db3c26ab` / `ea8dc333`.

### #18366 — Multiple uvicorn workers do not refresh config from DB

Closed Oct 2025.

### #10278 / #10365 — Replicas don't update certain settings until pod restart (split-brain)

Closed Feb 2025. Original split-brain config-refresh bug.

### #16074 — Active user count inflated, never goes down

Closed (in 0.6.41). Counter moved from socket-based USER_POOL to DB-backed heartbeat. *"Resolving long-standing issues where Redis deployments displayed inflated user counts due to stale sessions never being cleaned up on disconnect."* Commit `70948f880`.

## The April 2026 batch — what came in 0.9.0–0.9.4

This is the burst of multi-pod robustness work that, combined with the icon fixes from Nov 2025, makes today's situation materially better than early 2026.

| PR | Date | What it does |
|---|---|---|
| #22507 | 2026-03-15 | Added `/ready` endpoint that returns 200 only after startup + DB ping + Redis ping. Use as readiness probe. (Caused #23987 Sentinel regression.) |
| #22980 | 2026-03 | WebSocket heartbeat handler no longer blocks the event loop. |
| #22734 | 2026-03 | RedisDict.set race condition fix. |
| #23571 | 2026-04-11 | Enable TCP `SO_KEEPALIVE` on all Redis client connections. Lets the kernel detect dead peers on idle pooled connections. |
| #23572 | 2026-04-11 | Honor `REDIS_SOCKET_CONNECT_TIMEOUT` on non-Sentinel clients. |
| #23573 | 2026-04-11 | Add `REDIS_HEALTH_CHECK_INTERVAL` for stale-pooled-connection detection. |
| #23642 | 2026-04-12 | Invalidate stale Socket.IO sessions on role change and user deletion. |
| #23649 | 2026-04-12 | Apply `REDIS_KEY_PREFIX` to `tool_servers` and `terminal_servers` cache keys. |
| #23709 | 2026-04-14 | **Replace BaseHTTPMiddleware with pure ASGI implementations.** Major perf fix — removes serialization bottleneck under concurrency. |
| #23829 | 2026-04-17 | Fix `chat:outlet` update overwritten by stale write-back (race in event ordering). |
| #23896 | 2026-05-07 | Cross-worker tool + function cache invalidation via Redis. Plugins now invalidate consistently across pods. |
| #24015 | 2026-04-24 | `perf: redirect default model profile image to canonical static URL`. Browser caches one asset. |
| #24412 | 2026-05-09 | Arena model profile images. |
| #24420 | 2026-05-09 | `profile_image_url` validation — replace brittle allowlist with safe-scheme validation. |

Plus the Nov–Dec 2025 work:

| PR | Date | What it does |
|---|---|---|
| #18996 | 2025-11 | User-specific Socket.IO rooms — eliminates O(N) user fan-out on each event. |
| #19097 | 2025-11-07 | Preload group IDs, drop `profile_image_url` from list responses. |
| #19395 | 2025-12-02 | Redis-shared `MODELS` state (commit `b5e5617a4`). |
| #19488 | 2025-12 | `rediss://` (TLS) restored via python-socketio 5.15.0. |
| #19519 | 2025-12-21 | Base64 stripped from "most endpoints". |
| #19871 | 2025-12-11 | Use `SCAN` instead of `KEYS` for Redis Cluster compatibility. |
| #19959 | 2025-12 | Model avatar Cache-Control headers. |
| #20076 | 2025-12 | MCP OAuth tool servers work in multi-node via lazy-load from Redis. |
| #20145 | 2025-12-31 | `SentinelRedisProxy` async-generator handling for `YDocManager.remove_user_from_all_documents`. |

## Summary table — what to know at a glance

| Concern | Status |
|---|---|
| Custom model icons crash multi-pod | Fixed in 0.6.37–0.9.4. Spot-check non-model endpoints. |
| Inflated active user count | Fixed in 0.6.41. |
| `/api/tasks/stop` doesn't reach all pods | Fixed for Sentinel; broken on RedisCluster (#19840). Use Sentinel. |
| RedisDict.set race ("Model not found") | Fixed in 0.8.x dev / 0.9.0. |
| Memory leak in SESSION_POOL etc. | Fixed in 0.9.x. |
| WS heartbeat blocking event loop | Fixed in 0.8.x. |
| Sentinel ReadOnlyError | Fixed Oct 2025. |
| Sentinel auth password | Fixed Nov 2025. |
| Sentinel coroutine-not-awaited (0.9.1) | Fixed in 0.9.4 (#23987 closed 2026-05-08). Upgrade required for Sentinel users on 0.9.1–0.9.3. |
| Direct-connection chat with `workers > 1` | Partial fix Mar 2026; **don't use multiple workers per pod**. |
| Socket.IO frame amplification (#23733) | **Open. No ETA. Mitigate with `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=10`.** |
| Helm chart bundled Redis is no-PVC | Disable, use external Valkey. |
| Helm chart no HPA/PDB/probes | Add yourself. |
| Helm gateway-API WS appProtocol | Open #383, manual workaround. |

## See also

- `references/issue-23733.md` for the deep dive on the open structural bug.
- `references/configuration.md` for the env vars introduced by these fixes.
- `references/sources.md` for direct GitHub issue/PR links.
