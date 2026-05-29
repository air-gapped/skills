# Sources — files, issues, docs

Authoritative source files in the Open WebUI codebase, GitHub issue/PR numbers with dates, and `docs.openwebui.com` URLs underlying every claim in this skill. Load this file to verify a specific fact or run `freshen` mode.

Versions referenced span 0.5.x (Dec 2024) through 0.9.5 (current stable, May 2026). Multi-pod story starts maturing around 0.6.18 (July 2025) and is still actively patched.

## Verification log

Per-source-group last-verified dates. `freshen` mode probes each row and stamps the date on success. The skill's `Last verified:` cap (Dim 9 rubric) reads from the oldest row.

| Source group | Last verified | Notes |
|---|---|---|
| open-webui/open-webui latest stable v0.9.5 (released 2026-05-10) | 2026-05-28 | Latest release confirmed via `gh api /repos/open-webui/open-webui/releases/latest` → tag v0.9.5. File paths/line numbers below verified against the v0.9.4 clone HEAD `f51d2b026` (2026-05-10); v0.9.5 release body empty, no redis/websocket/sentinel signal. |
| docs.openwebui.com (scaling, redis tutorial, multi-replica troubleshooting, env-config, hardening) | 2026-05-10 | Pulled raw from `open-webui/docs` repo on this date. |
| open-webui/helm-charts at v14.6.0 | 2026-05-28 | Latest `open-webui-14.6.0` (2026-05-20), appVersion 0.9.5; also 14.5.0 (2026-05-11, appVersion 0.9.5). Confirmed via `gh release list --repo open-webui/helm-charts`. |
| GitHub issues #23733, #15162, #19840, #23939, #23650 (open) | 2026-05-28 | #23733 confirmed OPEN, updated 2026-05-27 via `gh issue view`. Others confirmed open 2026-05-10. |
| GitHub issue #23987 (Sentinel coroutine regression) | 2026-05-28 | Confirmed CLOSED 2026-05-08 by tjbck via `gh issue view`; fix shipped in 0.9.4 (released 2026-05-09). |
| GitHub PRs #23735, #23736, #24124, #24126, #24171 (Yjs/streaming attempts) | 2026-05-28 | All confirmed CLOSED, not merged, via `gh pr view`: #23735 delta emission, #23736 resumable replay, #24124/#24126/#24171 Ydoc streaming. |
| GitHub PRs in April–May 2026 batch (#22507, #22980, #22734, #23571–3, #23642, #23649, #23709, #23829, #23896, #24015, #24412, #24420) | 2026-05-10 | Verified merged. |
| GitHub PRs in Nov–Dec 2025 batch (#18996, #19097, #19395, #19488, #19519, #19871, #19959, #20076, #20145) | 2026-05-10 | Verified merged. |
| Earlier closed issues (#11934, #12325, #14340, #16074, #16157, #16693, #16979, #17223, #18073, #18223, #18366, #18950, #19401, #20142, #21410, #22734) | 2026-05-10 | Verified closed; resolutions referenced in `known-issues.md`. |
| Helm chart issues #338, #341, #383 | 2026-05-10 | #338 closed (maintainer confirms support), #341 closed (fixed v13.2.0), #383 open. |

## Local source files (`~/projects/github.com/open-webui/open-webui` at v0.9.4)

These paths are stable across recent versions. Line numbers may drift in clones past 0.9.4, but structure should hold.

### Configuration / env vars

- `backend/open_webui/env.py` — primary env-var registry.
  - Lines 442–500: Redis / Valkey core (`REDIS_URL`, `REDIS_KEY_PREFIX`, `REDIS_CLUSTER`, `REDIS_SENTINEL_*`, `REDIS_SOCKET_*`, `REDIS_HEALTH_CHECK_INTERVAL`).
  - Lines 744–809: WebSocket-specific (`ENABLE_WEBSOCKET_SUPPORT`, `WEBSOCKET_MANAGER`, `WEBSOCKET_REDIS_*`, `WEBSOCKET_SENTINEL_*`, `WEBSOCKET_SERVER_*`).
  - Lines 247–261: `ENABLE_PROFILE_IMAGE_URL_FORWARDING`.
  - Line 160: `ENABLE_DB_MIGRATIONS`.
- `backend/open_webui/config.py`:
  - Lines 279–361: `PersistentConfig` cache through Redis.
  - Lines 1187–1191: `ENABLE_BASE_MODELS_CACHE`.
  - Line 74: `ENABLE_DB_MIGRATIONS` consumer.

### WebSocket / Socket.IO

- `backend/open_webui/socket/main.py`:
  - Lines 65–164: Socket.IO + Redis manager boot.
  - Lines 173–193: `periodic_session_pool_cleanup`.
  - Lines 196–237: `periodic_usage_pool_cleanup`.
  - Lines 294–312: User-specific rooms (`enter_room(sid, f'user:{user.id}')`).
  - Lines 315–330: `disconnect_user_sessions(user_id)`.
  - Lines 347–369: `connect` handler — JWT auth, `SESSION_POOL` populate.
  - Lines 357–365: **profile-image fields excluded from SESSION_POOL** (`profile_image_url`, `profile_banner_image_url`, `date_of_birth`, `bio`, `gender`).
  - Lines 411–416: `heartbeat` handler.
- `backend/open_webui/socket/utils.py`:
  - Lines 9–42: `RedisLock` (SET-NX + UUID lock_id pattern).
  - Lines 84–100: `RedisDict` (post-#22734 race-fix HSET-then-HDEL).
  - Lines 124–263: `YdocManager` (CRDT state for collaborative notes).
  - Line 232: `scan_iter` for Redis Cluster compat (#19871 fix).
- `backend/open_webui/utils/redis.py`:
  - Lines 30, 193–194: `_CONNECTION_CACHE` shared connection pool.
  - Lines 33–149: `SentinelRedisProxy` (async-aware retry wrapper).

### Tasks (cross-pod cancellation)

- `backend/open_webui/tasks.py`:
  - Lines 25–86: distributed task tracking.
  - Lines 49–86: `{prefix}:tasks` hash, `{prefix}:tasks:item:{id}` sets, `{prefix}:tasks:commands` pubsub channel. Uses `execute_command('PUBLISH', ...)` for RedisCluster paths (which still fails — see #19840).

### Model icons / profile images

- `backend/open_webui/models/models.py:38` — `profile_image_url: Optional[str] = '/static/favicon.png'` default.
- `backend/open_webui/routers/models.py`:
  - Lines 142–148: Model list filter.
  - Lines 458–525: `/api/v1/models/model/profile/image` endpoint (the new dedicated path).
- `backend/open_webui/main.py`:
  - Lines 1497–1499: strip `profile_image_url` from `/api/models` response.
  - Line 1384: `MODELS` state initialization.
  - Lines 2585–2600: `ENABLE_STAR_SESSIONS_MIDDLEWARE` (OAuth Redis sessions).
  - Lines 2853–2890: `/ready` endpoint (#22507).

### Rate limit / auth

- `backend/open_webui/utils/rate_limit.py` — Redis-backed sign-in rate limiter, in-memory fallback.
- `backend/open_webui/routers/auths.py:97` — `validate_profile_image_url` (#24420 safe-scheme validation).
- `backend/open_webui/models/auths.py:9` — `validate_profile_image_url` import.

### Helm chart (in-tree copy at this point in history)

- `helm-charts-temp/charts/open-webui/values.yaml`:
  - Lines 51–140: WebSocket + Redis subchart.
  - Line 184: `replicaCount: 1`.
  - Lines 296–331: Ingress.
- `helm-charts-temp/charts/open-webui/templates/workload-manager.yaml`:
  - Lines 248–255 / 301–323: env wiring for `ENABLE_WEBSOCKET_SUPPORT` / `WEBSOCKET_MANAGER` / `REDIS_URL` / `WEBSOCKET_REDIS_URL`.

### CHANGELOG

- `CHANGELOG.md` — release-by-release history. Approximately 800 KB; grep by version (`#### \[0\.9\.0\]`) or by keyword (`websocket`, `redis`, `valkey`, `scaling`, `multi-pod`, `replica`, `thumbnail`, `profile_image`).
  - Line ~41: 0.9.3 arena model profile images.
  - Line ~87: 0.9.3 forwarding control.
  - Line ~122: 0.9.2 model list performance.
  - Line ~475: 0.9.0 RedisDict race fix.
  - Line ~1295: 0.6.42 model avatar Cache-Control.
  - Line ~1384: 0.6.41 Redis MODELS state.
  - Line ~1392: base64 strip.
  - Line ~1463: 0.6.37 user-specific rooms.
  - Line ~1480: 0.6.37 WS env vars.
  - Line ~2152: 0.7.x Redis connection pool cache.

## GitHub issues — open as of 2026-05-10

```
gh issue view 23733 --repo open-webui/open-webui     # Socket.IO frame amplification (THE BIG ONE)
gh issue view 15162 --repo open-webui/open-webui     # direct-connection multi-worker routing
gh issue view 19840 --repo open-webui/open-webui     # RedisCluster publish broken
gh issue view 23987 --repo open-webui/open-webui     # Sentinel coroutine regression in 0.9.1
gh issue view 23939 --repo open-webui/open-webui     # 0.9.0/0.9.1 loading and login issues
```

## GitHub PRs — closed, not merged (the Yjs / streaming attempts)

```
gh pr view 23735 --repo open-webui/open-webui        # delta emission
gh pr view 23736 --repo open-webui/open-webui        # resumable WS streaming with seq replay
gh pr view 24124 --repo open-webui/open-webui        # Yjs streaming attempt 1
gh pr view 24126 --repo open-webui/open-webui        # Yjs streaming attempt 2
gh pr view 24171 --repo open-webui/open-webui        # Yjs streaming attempt 3
```

## GitHub PRs — merged April–May 2026 batch

```
gh pr view 22507 --repo open-webui/open-webui        # /ready endpoint
gh pr view 22980 --repo open-webui/open-webui        # WS heartbeat non-blocking
gh pr view 22734 --repo open-webui/open-webui        # RedisDict race fix
gh pr view 23571 --repo open-webui/open-webui        # TCP keepalive
gh pr view 23572 --repo open-webui/open-webui        # REDIS_SOCKET_CONNECT_TIMEOUT
gh pr view 23573 --repo open-webui/open-webui        # REDIS_HEALTH_CHECK_INTERVAL
gh pr view 23642 --repo open-webui/open-webui        # invalidate stale Socket.IO sessions
gh pr view 23649 --repo open-webui/open-webui        # REDIS_KEY_PREFIX for tool/terminal caches
gh pr view 23709 --repo open-webui/open-webui        # BaseHTTPMiddleware → pure ASGI
gh pr view 23829 --repo open-webui/open-webui        # chat:outlet stale write-back
gh pr view 23896 --repo open-webui/open-webui        # cross-worker tool/function cache invalidation
gh pr view 24015 --repo open-webui/open-webui        # default avatar 302 redirect
gh pr view 24412 --repo open-webui/open-webui        # arena model profile images
gh pr view 24420 --repo open-webui/open-webui        # profile_image_url safe-scheme validation
```

## GitHub PRs — Nov–Dec 2025 batch

```
gh pr view 18996 --repo open-webui/open-webui        # user-specific Socket.IO rooms
gh pr view 19097 --repo open-webui/open-webui        # /api/models perf + drop profile_image_url
gh pr view 19395 --repo open-webui/open-webui        # Redis-shared MODELS state
gh pr view 19488 --repo open-webui/open-webui        # rediss:// TLS via python-socketio 5.15.0
gh pr view 19519 --repo open-webui/open-webui        # base64 stripped from most endpoints
gh pr view 19871 --repo open-webui/open-webui        # SCAN instead of KEYS
gh pr view 19959 --repo open-webui/open-webui        # model avatar Cache-Control
gh pr view 20076 --repo open-webui/open-webui        # MCP OAuth multi-node
gh pr view 20145 --repo open-webui/open-webui        # SentinelRedisProxy async-generator
```

## Helm chart issues / PRs

```
gh issue view 338 --repo open-webui/helm-charts      # confirms helm chart is supported
gh issue view 341 --repo open-webui/helm-charts      # WEBSOCKET_REDIS_URL from Secret (fixed v13.2.0)
gh issue view 383 --repo open-webui/helm-charts      # gateway-API appProtocol (open)
```

## Documentation pages (docs.openwebui.com)

```
https://docs.openwebui.com/getting-started/advanced-topics/scaling
https://docs.openwebui.com/tutorials/integrations/redis
https://docs.openwebui.com/troubleshooting/multi-replica
https://docs.openwebui.com/reference/env-configuration
https://docs.openwebui.com/getting-started/advanced-topics/hardening
```

Source repo for the docs (markdown lives here, useful for `gh api`):

```
https://github.com/open-webui/docs
```

Pull pages directly via `gh`:

```
gh api repos/open-webui/docs/contents/docs/getting-started/advanced-topics/scaling.md \
  --header "Accept: application/vnd.github.raw"

gh api repos/open-webui/docs/contents/docs/tutorials/integrations/redis.mdx \
  --header "Accept: application/vnd.github.raw"

gh api repos/open-webui/docs/contents/docs/troubleshooting/multi-replica.mdx \
  --header "Accept: application/vnd.github.raw"

gh api repos/open-webui/docs/contents/docs/reference/env-configuration.mdx \
  --header "Accept: application/vnd.github.raw"
```

## Repos

```
https://github.com/open-webui/open-webui                # the app
https://github.com/open-webui/helm-charts               # helm chart
https://github.com/open-webui/docs                      # documentation source
https://helm.openwebui.com/                             # helm repository URL
```

## Maintainer + key contributor handles

- `tjbck` — primary maintainer. Authoritative on architecture decisions (#23733).
- `Classic298` — collaborator. Authoritative on Postgres-vs-SQLite at scale.
- `westbrook-ai` — helm chart maintainer.
- `Ithanil` — operator who reported #23733 with measurements.
- `adam-skalicky` — author of #19097 (group-IDs preload + profile_image_url strip).
- `luke-wren` — auditor of remaining icon-bloated endpoints (#18950 thread).
- `HANIHALILI` — author of unmerged RedisCluster `publish()` fixes (#19840).

## Refresh procedure

To refresh this skill against current upstream state:

1. `cd ~/projects/github.com/open-webui/open-webui && git pull origin main`
2. Read CHANGELOG entries since the last skill update for `websocket`, `redis`, `valkey`, `scaling`, `multi-pod`, `replica`, `thumbnail`, `profile_image`.
3. `gh issue view 23733 --repo open-webui/open-webui` — check status.
4. `gh issue list --repo open-webui/open-webui --state open --label scaling` (or `multi-pod`, etc.)
5. `gh pr list --repo open-webui/open-webui --state merged --limit 50 --search "redis OR websocket OR scaling"` — note new fixes.
6. Update `references/known-issues.md` "Fixed" table and `references/configuration.md` if new env vars appeared.
