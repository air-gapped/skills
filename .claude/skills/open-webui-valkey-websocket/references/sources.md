# Sources — files, issues, docs

Freshened: 2026-10-27 — every row probed against v0.12.4 (2026-10-25) and chart 17.0.0; the v0.12.x line moved the security floor, Sentinel behaviour, room-channel delivery and revocation, and six PRs the skill called merged were closed unmerged.

Authoritative source files in the Open WebUI codebase, GitHub issue/PR numbers, and `docs.openwebui.com` URLs underlying every claim in this skill. Load this file to verify a specific fact or run `freshen` mode. Code anchors are file + symbol at tag `v0.12.4`; line numbers drift every release, so resolve by symbol (`git show v0.12.4:<path> | grep -n '<symbol>'`).

## Verification log

| Source | Notes |
|---|---|
| open-webui/open-webui releases (`gh release list`, `isLatest`) | Latest stable **v0.12.4** (2026-10-25). v0.12.0 2026-10-10, v0.12.1 and v0.12.2 2026-10-14, v0.12.3 2026-10-16. Previous line ended at v0.11.4 (2026-09-21). |
| Security floor v0.12.4 — `gh api repos/open-webui/open-webui/security-advisories` (166 published) vs `gh api 'advisories?ecosystem=pip&affects=open-webui'` | Highest published ceiling `< 0.12.2` (advisory published 2026-10-18, patched 0.12.2); 17 advisories published 2026-09-27/28 patched 0.11.4. The global database's newest open-webui entry was 2026-09-10 on 2026-10-27, so it lagged the repo list by 6+ weeks. v0.12.4 notes (CHANGELOG.md at tag `v0.12.4`): security fixes "not listed in this changelog". The 2026-09-15 "all 69 have `first_patched_version` null" no longer held: 73 of 74 in that window had it set on 2026-10-27. |
| v0.12.0–v0.12.4 schema changes and mixed-version delivery — CHANGELOG.md at tag `v0.12.4`, `git diff --diff-filter=A <tag>..<tag> -- backend/open_webui/migrations/versions/` | Migrations added: 6 in v0.12.0 (incl. `a7d3e9f2b641_add_mfa_and_session_stamp`), 2 in v0.12.1, none v0.12.2–v0.12.4. CHANGELOG.md carries the "rolling updates are not supported" warning for v0.12.0 and v0.12.1; the GitHub release body for v0.12.0 does not. v0.12.0 "Update Redis-backed instances together" (#28818): updates from an upgraded instance do not reach an older one unless `WEBSOCKET_REDIS_ROOM_CHANNELS=false`. |
| `WEBSOCKET_REDIS_ROOM_CHANNELS` — `backend/open_webui/env.py` and `backend/open_webui/socket/redis_room_channels.py::AsyncRedisRoomChannelManager` at tag `v0.12.4`; CHANGELOG.md 0.12.0 (#28818) and 0.12.3 (commit `362b01d0`) | Default `True`. Room channel = `f'{self.channel}#{namespace}#{room}'`, base channel is python-socketio's default `socketio` (the skill's earlier `flask-socketio` was Flask-SocketIO's default, never this one). 0.12.3: needs PUBLISH, SUBSCRIBE, UNSUBSCRIBE, PING and `&socketio`, `&socketio#*`; PSUBSCRIBE no longer used (0.12.0 required it). |
| Sentinel fixes v0.12.1 and websocket-reconnect fix v0.12.4 — `git diff v0.11.4 v0.12.1 -- backend/open_webui/utils/redis.py`; CHANGELOG.md 0.12.1 (#32234/#31918, #32241/#32240) and 0.12.4 (#33009/#33008) | `parse_redis_url` used `parts.hostname` (lowercases) for the Sentinel service name until v0.12.1; `build_sentinel_kwargs` (URL credentials + `socket_*` options for the Sentinel connections) added v0.12.1. 0.12.4: "since 0.12.3 every new connection could hang until the instance was restarted" with `retry_on_timeout` in `WEBSOCKET_REDIS_OPTIONS`. |
| Revocation at v0.12.4 — `backend/open_webui/utils/auth.py::is_valid_token` (docstring: "Database failures fail closed. Redis failures retain the existing availability policy."), `models/auths.py` (`session_stamp` rotated with `uuid4`), migration `a7d3e9f2b641_add_mfa_and_session_stamp`; CHANGELOG.md 0.12.0 "Password changes sign out everywhere without Redis" (commit `24e30d1c`) | Per-token `:auth:token:<jti>:revoked` and per-user `:auth:user:<id>:revoked_at` keys still read from Redis inside the fail-open `try`. |
| Valkey key layout at v0.12.4 — `backend/open_webui/tasks.py::save_response_stream` / `append_response_stream`; `git grep` for `PersistentConfig` and `:config` keys over `backend/open_webui` at `v0.12.4`; CHANGELOG.md 0.12.3 "Much lighter streaming with Redis" | Snapshot key `f'{REDIS_RESPONSE_STREAMS_KEY}:{task_id}'`, `redis.set(..., ex=REDIS_RESPONSE_STREAM_TTL)`, append via `redis.eval` with `strlen`/`append`/`expire`. No `PersistentConfig` class and no Redis `config` keys anywhere in the backend at v0.12.4, so the `open-webui:config:*` row was removed. |
| open-webui/helm-charts at `open-webui-17.0.0` (local clone, tags filtered for `dev`) | 17.0.0 2026-10-10 appVersion 0.12.0; only commit 16.6.0..17.0.0 under `charts/open-webui` is `795edda` "upgrade open-webui to v0.12.0". Branches `automation/open-webui-0.12.1`…`0.12.4` unmerged. `service.appProtocol` added by `1b055bb` (2026-05-22), first stable tag containing it `open-webui-14.11.0`; #383 CLOSED 2026-06-28. `websocket-redis.yaml` still `kind: Deployment`, no PVC. Handle `westbrook-ai` now 404s on GitHub, so the maintainer handle was dropped. |
| Issue/PR states re-probed 2026-10-27 (one GraphQL query, open-webui/open-webui) | #15162 CLOSED COMPLETED 2026-09-22, maintainer: "Fixed in v0.11.4" (commit `0180efec`). Closed **unmerged** PRs the skill had called merged: #22402, #24099, #24100, #16693, #23896, #19799. #23650 is a PR, closed unmerged 2026-09-22. #16074 returns NOT_FOUND (dropped; the 0.6.41 fix is cited by commit `70948f880`). Issues, not PRs: #19395, #19519, #24412. #17223 is a merged PR. |
| v0.11.1–v0.11.4 release notes, read item by item | **Biggest find: #23733's amplification is fixed in v0.11.1** (commit `a1579a01f` — `utils/middleware.py::streaming_chat_response_handler` now emits `response.output_text.delta` events, not `{'output': full_output()}`), even though the GitHub issue stayed closed won't-fix. Also confirmed: #27622 and #27651 fixed in v0.11.1 (release notes match the earlier issue-state probe); `REDIS_RESPONSE_STREAM_TTL`, `WEBSOCKET_HEARTBEAT_INTERVAL`, `UVICORN_WS_PER_MESSAGE_DEFLATE` added v0.11.1; `REDIS_TASK_TTL`, `ENABLE_CHAT_RESPONSE_STREAM_INPLACE_APPEND` added v0.11.4; revocation fails open on `RedisError` since v0.11.4 (commit `c1615bec2`, `utils/auth.py::is_valid_token`); sign-in rate limiter (PR #29977) and session-pool reaper (PR #29976) no longer break on a Redis blip, both v0.11.4; per-worker model-registry cache (PR #28176) and Ollama-`expires_at` signature fix (commit `649c012e`), both v0.11.4. |
| GitHub issue #23987 (Sentinel coroutine regression) | CLOSED COMPLETED 2026-05-08; fix shipped in 0.9.4 (2026-05-09). |
| Yjs/streaming PRs #23735, #23736, #24124, #24126, #24171 | All CLOSED, not merged. |
| April–May 2026 batch | Merged PRs: #22507, #22980, #23571, #23572, #23573, #23642, #23649, #23709, #23829, #24015, #24420 (mergedAt 2026-03-15 … 2026-05-08). #22734 and #24412 are issues, CLOSED COMPLETED. #23896 is a PR CLOSED unmerged (dropped from the merged table). |
| Nov–Dec 2025 batch | Merged PRs: #18996, #19097, #19488, #19871, #19959, #20076, #20145. #19395 and #19519 are issues, CLOSED COMPLETED. |
| Earlier closed issues #11934, #12325, #14340, #16157, #16979, #18073, #18223, #18366, #18950, #19401, #20142, #21410, #10278, #10365, #16219, #22734, #27622, #27651, #19840, #23939, #23733 (NOT_PLANNED) | CLOSED. #17223 is a merged PR (2025-09-25). #23796, #27663, #28176, #28177, #29165, #29976, #29977 merged PRs. |
| Helm chart issues #326, #338, #341, #383 | All CLOSED COMPLETED (#383 on 2026-06-28). |
| docs.openwebui.com scaling, redis, multi-replica, env-configuration, hardening | All HTTP 200 on 2026-10-27. Raw source: `open-webui/docs` repo; the Redis tutorial is now `redis.md` (was `.mdx`). |
| GitHub handles tjbck, Classic298, Ithanil, adam-skalicky, luke-wren, HANIHALILI | Resolve. `westbrook-ai` 404s (dropped). |

## Local source files (`open-webui/open-webui`, anchors at tag `v0.12.4`)

### Configuration / env vars

- `backend/open_webui/env.py` — Redis core (`REDIS_URL`, `REDIS_KEY_PREFIX`, `REDIS_SENTINEL_*`, `REDIS_SOCKET_*`, `REDIS_RESPONSE_STREAM_TTL`, `REDIS_TASK_TTL`), websocket (`WEBSOCKET_*` incl. `WEBSOCKET_REDIS_ROOM_CHANNELS`, `WEBSOCKET_HEARTBEAT_INTERVAL`), `UVICORN_WS_PER_MESSAGE_DEFLATE`, `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE`, `ENABLE_DB_MIGRATIONS`, `ENABLE_STAR_SESSIONS_MIDDLEWARE`.
- `backend/open_webui/config.py` — `ENABLE_BASE_MODELS_CACHE`. No `PersistentConfig` and no Redis config cache.

### WebSocket / Socket.IO

- `backend/open_webui/socket/main.py` — manager boot (`manager_class = AsyncRedisRoomChannelManager if WEBSOCKET_REDIS_ROOM_CHANNELS else socketio.AsyncRedisManager`), `periodic_session_pool_cleanup`, `periodic_usage_pool_cleanup`, `disconnect_user_sessions`, `connect` (excludes `profile_image_url`, `profile_banner_image_url` etc. from the session pool), `heartbeat`.
- `backend/open_webui/socket/redis_room_channels.py` — `AsyncRedisRoomChannelManager` (room channel `f'{self.channel}#{namespace}#{room}'`, ACL error messages).
- `backend/open_webui/socket/utils.py` — `RedisLock`, `RedisDict`, `CachedRedisDict`, `YdocManager`.
- `backend/open_webui/utils/redis.py` — `parse_redis_url`, `build_sentinel_url`, `build_sentinel_kwargs` (v0.12.1+), `_build_sentinel`, `SentinelRedisProxy`, `_CONNECTION_POOL`.

### Tasks, streaming snapshot, auth

- `backend/open_webui/tasks.py` — `REDIS_TASKS_KEY`, `REDIS_PUBSUB_CHANNEL` (`{prefix}:tasks:commands`), `save_response_stream` / `append_response_stream` (`{prefix}:tasks:response_streams:<task_id>`).
- `backend/open_webui/utils/auth.py::is_valid_token` — DB `session_stamp` check, then Redis revocation inside `except RedisError` fail-open.
- `backend/open_webui/utils/rate_limit.py::RateLimiter.is_limited` — Redis-backed sign-in limiter.

### Model icons / profile images

- `backend/open_webui/models/models.py` — `profile_image_url: str | None = None` (was `'/static/favicon.png'` at 0.9.x).
- `backend/open_webui/routers/models.py::get_model_profile_image` — `GET /model/profile/image`.
- `backend/open_webui/utils/validate.py::validate_image_url` (was `validate_profile_image_url` in `routers/auths.py`).
- `backend/open_webui/main.py` — `@app.get('/ready')`, `ENABLE_STAR_SESSIONS_MIDDLEWARE` wiring.

### Helm chart (`open-webui/helm-charts`, tag `open-webui-17.0.0`)

- `charts/open-webui/values.yaml` — `websocket:` block (bundled `redis:` sub-block, `existingSecret`), `replicaCount`, `service.appProtocol`, probes default `{}`.
- `charts/open-webui/templates/workload-manager.yaml` — `$kind` selection, env wiring for `ENABLE_WEBSOCKET_SUPPORT` / `WEBSOCKET_MANAGER` / `REDIS_URL` / `WEBSOCKET_REDIS_URL`.
- `charts/open-webui/templates/websocket-redis.yaml` — bundled Redis `kind: Deployment`, no PVC.

### CHANGELOG

- `CHANGELOG.md` — grep by version (`## \[0\.12\.1\]`) or keyword (`redis`, `sentinel`, `websocket`, `Database Migrations`, `Security Advisory`). It carries migration warnings the GitHub release body can omit.

## GitHub issues

```
gh issue view 23733 --repo open-webui/open-webui     # Socket.IO frame amplification (THE BIG ONE)
gh issue view 15162 --repo open-webui/open-webui     # direct-connection multi-worker routing — FIXED v0.11.4
gh issue view 19840 --repo open-webui/open-webui     # RedisCluster publish — FIXED, ships v0.11.2 (PR #29165)
gh issue view 23987 --repo open-webui/open-webui     # Sentinel coroutine regression in 0.9.1
gh issue view 23939 --repo open-webui/open-webui     # 0.9.0/0.9.1 loading and login issues — CLOSED 2026-04-22
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
gh issue view 22734 --repo open-webui/open-webui     # RedisDict race fix (issue)
gh pr view 23571 --repo open-webui/open-webui        # TCP keepalive
gh pr view 23572 --repo open-webui/open-webui        # REDIS_SOCKET_CONNECT_TIMEOUT
gh pr view 23573 --repo open-webui/open-webui        # REDIS_HEALTH_CHECK_INTERVAL
gh pr view 23642 --repo open-webui/open-webui        # invalidate stale Socket.IO sessions
gh pr view 23649 --repo open-webui/open-webui        # REDIS_KEY_PREFIX for tool/terminal caches
gh pr view 23709 --repo open-webui/open-webui        # BaseHTTPMiddleware → pure ASGI
gh pr view 23829 --repo open-webui/open-webui        # chat:outlet stale write-back
gh pr view 24015 --repo open-webui/open-webui        # default avatar 302 redirect
gh issue view 24412 --repo open-webui/open-webui     # arena model profile images (issue)
gh pr view 24420 --repo open-webui/open-webui        # profile_image_url safe-scheme validation
```

## GitHub PRs — Nov–Dec 2025 batch

```
gh pr view 18996 --repo open-webui/open-webui        # user-specific Socket.IO rooms
gh pr view 19097 --repo open-webui/open-webui        # /api/models perf + drop profile_image_url
gh issue view 19395 --repo open-webui/open-webui     # Redis-shared MODELS state (issue)
gh pr view 19488 --repo open-webui/open-webui        # rediss:// TLS via python-socketio 5.15.0
gh issue view 19519 --repo open-webui/open-webui     # base64 stripped from most endpoints (issue)
gh pr view 19871 --repo open-webui/open-webui        # SCAN instead of KEYS
gh pr view 19959 --repo open-webui/open-webui        # model avatar Cache-Control
gh pr view 20076 --repo open-webui/open-webui        # MCP OAuth multi-node
gh pr view 20145 --repo open-webui/open-webui        # SentinelRedisProxy async-generator
```

## Helm chart issues / PRs

```
gh issue view 338 --repo open-webui/helm-charts      # confirms helm chart is supported
gh issue view 341 --repo open-webui/helm-charts      # WEBSOCKET_REDIS_URL from Secret (fixed v13.2.0)
gh issue view 383 --repo open-webui/helm-charts      # gateway-API appProtocol — CLOSED 2026-06-28
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

gh api repos/open-webui/docs/contents/docs/tutorials/integrations/redis.md \
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
- `Ithanil` — operator who reported #23733 with measurements.
- `adam-skalicky` — author of #19097 (group-IDs preload + profile_image_url strip).
- `luke-wren` — auditor of remaining icon-bloated endpoints (#18950 thread).
- `HANIHALILI` — author of the earlier, unmerged RedisCluster `publish()` fixes (#19840); the change that finally landed was PR #29165 (2026-08-29).

## Refresh procedure

To refresh this skill against current upstream state:

1. `git -C <open-webui clone> fetch --tags` and read files at the release tag (`git show <tag>:<path>`)
2. Read CHANGELOG entries since the last skill update for `websocket`, `redis`, `valkey`, `scaling`, `multi-pod`, `replica`, `thumbnail`, `profile_image`.
3. `gh issue view 23733 --repo open-webui/open-webui` — check status.
4. `gh issue list --repo open-webui/open-webui --state open --label scaling` (or `multi-pod`, etc.)
5. `gh pr list --repo open-webui/open-webui --state merged --limit 50 --search "redis OR websocket OR scaling"` — note new fixes.
6. Update `references/known-issues.md` "Fixed" table and `references/configuration.md` if new env vars appeared.
