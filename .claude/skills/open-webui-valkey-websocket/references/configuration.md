# Configuration reference — multi-pod env vars and Valkey config

Defaults and source locations are based on `backend/open_webui/env.py` and `backend/open_webui/config.py` at v0.9.4 (2026-05-09). Versions noted are when each variable was added or its semantics last changed.

## Streaming (#23733 mitigation)

| Var | Default | Notes |
|---|---|---|
| `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE` | `1` | **The most important multi-pod knob.** Tokens to buffer per Socket.IO emit. Set to `10` for production multi-pod, `20` for reasoning-heavy traffic. See `issue-23733.md`. |
| `ENABLE_WEBSOCKET_SUPPORT` | `True` | When `False`, Socket.IO falls back to polling only — `transports=['polling']`, no upgrades. Polling fallback requires sticky sessions even with `WEBSOCKET_MANAGER=redis`. |

## Core Valkey/Redis (`env.py` lines 442–500)

| Var | Default | Notes |
|---|---|---|
| `REDIS_URL` | `''` (off) | E.g. `redis://valkey-master:6379/0`. Empty disables Valkey/Redis entirely. |
| `REDIS_KEY_PREFIX` | `open-webui` | Prefix all keys. Use the **same** prefix across replicas of one deployment, **different** prefixes when multiple deployments share one Valkey instance. Operators get this backwards. |
| `REDIS_CLUSTER` | `False` | Use `redis.cluster.RedisCluster.from_url(...)`. **Avoid** — `RedisCluster.publish()` doesn't exist (#19840), breaks `tasks/stop` and other pub/sub paths. |
| `REDIS_SENTINEL_HOSTS` | `''` | Comma-separated hostnames of Sentinels. |
| `REDIS_SENTINEL_PORT` | `26379` | |
| `REDIS_SENTINEL_MAX_RETRY_COUNT` | `2` | Retries on `ConnectionError` / `ReadOnlyError` during failover. |
| `REDIS_RECONNECT_DELAY` | unset | Float ms between Sentinel failover retries. |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | unset | Float seconds. Without this, Sentinel failover can hang the app indefinitely. **Set to `5`.** Added 0.6.42 (#19799), broadened to non-sentinel in 0.9.0 (#23572). |
| `REDIS_SOCKET_KEEPALIVE` | `False` | TCP `SO_KEEPALIVE`. Detects half-closed sockets after silent firewall/LB resets or NIC flaps. **Set to `True`.** Added 2026-04-12 (#23571). |
| `REDIS_HEALTH_CHECK_INTERVAL` | unset | Seconds between idle-conn pings. Must be shorter than the Valkey `timeout` setting and any firewall/LB idle timeout on the path. **Set to `60`.** Added 2026-04-12 (#23573). |

## WebSocket-specific Valkey (`env.py` lines 744–809)

These default to the `REDIS_*` versions if unset, but separating them is documented best practice (different DB number, easier to size, easier to monitor).

| Var | Default | Notes |
|---|---|---|
| `WEBSOCKET_MANAGER` | `''` | Set to `redis` to use `socketio.AsyncRedisManager`. **Required for multi-pod.** |
| `WEBSOCKET_REDIS_URL` | falls back to `REDIS_URL` | Recommended: same Valkey, different DB number (`/1`). Isolates Socket.IO pub/sub from app state. |
| `WEBSOCKET_REDIS_CLUSTER` | falls back to `REDIS_CLUSTER` | |
| `WEBSOCKET_REDIS_OPTIONS` | unset | Arbitrary JSON of `redis-py` kwargs. Auto-includes `socket_connect_timeout` if set. |
| `WEBSOCKET_REDIS_LOCK_TIMEOUT` | `60` | Seconds. Used for SET-NX cleanup locks (`socket/utils.py:31`). |
| `WEBSOCKET_SENTINEL_HOSTS` | `''` | Independent Sentinel set for WS Valkey. Reuse `REDIS_SENTINEL_HOSTS` unless explicit isolation is desired. |
| `WEBSOCKET_SENTINEL_PORT` | `26379` | |
| `WEBSOCKET_SERVER_LOGGING` | `False` | Socket.IO server logger. Useful for diagnosing #23733 emit rate. |
| `WEBSOCKET_SERVER_ENGINEIO_LOGGING` | inherits `WEBSOCKET_SERVER_LOGGING` | EngineIO logger. |
| `WEBSOCKET_SERVER_PING_TIMEOUT` | `20` | Seconds before Socket.IO considers a client dead. |
| `WEBSOCKET_SERVER_PING_INTERVAL` | `25` | Heartbeat interval. |
| `WEBSOCKET_EVENT_CALLER_TIMEOUT` | `None` (no timeout) | Server-to-client `sio.call(...)` timeout. Falls back to 300s on invalid string. |

## Database

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | SQLite | **Postgres mandatory for multi-pod.** SQLite-on-shared-storage corrupts under concurrent writes. |
| `DATABASE_POOL_SIZE` | `0` (no pool) | Set to `15` per replica. With 6 replicas → 90 conns base. |
| `DATABASE_POOL_MAX_OVERFLOW` | `0` | Set to `20` per replica. With 6 replicas → 120 conns max overflow. Bump Postgres `max_connections` to ≥ `(replicas × 35) + 50` to leave headroom for migrations and ad-hoc tools. |
| `ENABLE_DB_MIGRATIONS` | `True` | **Set `False` on every pod except one designated migration pod.** Or run migrations as a separate Job before rolling update. Without this, simultaneous migrations on rolling restart will race and corrupt schema state. Added 0.6.34 (`9824f0e33`). |

## Vector DB

| Var | Default | Notes |
|---|---|---|
| `VECTOR_DB` | `chroma` | **Cannot share ChromaDB across pods** — SQLite + fork = instant worker death during document uploads. Set to `pgvector` (recommended), `milvus`, or `qdrant`. |
| `PGVECTOR_DB_URL` | unset | If `VECTOR_DB=pgvector`. Can share connection with `DATABASE_URL`. |
| `ENABLE_MILVUS_MULTITENANCY_MODE` / `ENABLE_QDRANT_MULTITENANCY_MODE` | `False` | Per-user collections for higher throughput on Milvus/Qdrant. |

Maintainers consistently maintain pgvector and ChromaDB; others are community-supported.

## Concurrency

| Var | Default | Notes |
|---|---|---|
| `UVICORN_WORKERS` | `1` | **Keep at 1.** Scaling via replicas is the supported path. Multiple workers per pod re-creates the cross-worker routing class of bug (#15162) within a single pod — same root cause as the multi-pod version, no in-memory state shared. |

## Memory-leak guard (RAG pipeline)

Default `pypdf` and `SentenceTransformers` are documented (in the official scaling guide) as the two most common causes of memory leaks in long-running pods. For multi-pod they will eventually OOM.

| Var | Default | Notes |
|---|---|---|
| `CONTENT_EXTRACTION_ENGINE` | `pypdf` | Set to `tika` and run an Apache Tika sidecar/service. |
| `TIKA_SERVER_URL` | unset | Required if `tika`. |
| `RAG_EMBEDDING_ENGINE` | `sentencetransformers` | Set to `openai` (works for any OpenAI-compat) or `ollama`. Saves ~500 MB per worker. |

## Secrets — must be identical across all pods

| Var | Default | Notes |
|---|---|---|
| `WEBUI_SECRET_KEY` | random per-pod | **MUST be identical across all replicas.** Without it, login loops, 401s, OAuth tokens written by one pod fail decryption on another. |
| `OAUTH_SESSION_TOKEN_ENCRYPTION_KEY` | falls back to `WEBUI_SECRET_KEY` | Same — keep identical. |
| `OAUTH_CLIENT_INFO_ENCRYPTION_KEY` | falls back to `WEBUI_SECRET_KEY` | Same. |

Mount via a Kubernetes Secret referenced by every pod's `envFrom` — never let the chart auto-generate per-pod, never use the `existingSecret`-less paths in random pods.

## OAuth/SSO avatar bloat killers

When the IdP returns large profile pictures (Microsoft/Entra is notorious — 1024×1024 base64 PNGs), every login round-trips the avatar through Postgres and the bytes appear in `/api/v1/users` payloads (issue #12325 — 30s admin loads).

| Var | Default | Notes |
|---|---|---|
| `OAUTH_PICTURE_CLAIM` | `picture` | Set to `""` to skip avatar pickup entirely. |
| `OAUTH_UPDATE_PICTURE_ON_LOGIN` | `True` | Set to `False` to keep existing avatars but stop re-syncing on every login. |
| `ENABLE_PROFILE_IMAGE_URL_FORWARDING` | `True` | Added 0.9.3. Set `False` to suppress 302→external profile-image URLs (privacy/perf). |

## OAuth multi-pod session state

| Var | Default | Notes |
|---|---|---|
| `ENABLE_STAR_SESSIONS_MIDDLEWARE` | `False` | Experimental: backs OAuth session state with Valkey via `starsessions.RedisStore`. Fixes CSRF errors during multi-pod OAuth (#17223, 0.6.31). Marked "may be removed in future" in env.py. Validate per upgrade. |

## Instance identification (operational hygiene)

| Var | Default | Notes |
|---|---|---|
| `DEPLOYMENT_ID` | `''` | Useful for log correlation across replicas. Set to deployment name. |
| `INSTANCE_ID` | random uuid4 | Per-pod ID. Logged on startup. |

## Observability

| Var | Default | Notes |
|---|---|---|
| `ENABLE_OTEL` | `False` | OpenTelemetry export (traces/metrics/logs). |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | E.g. `http://otel-collector:4317`. |
| `OTEL_SERVICE_NAME` | `open-webui` | Override per environment. |

---

## Valkey configuration (`valkey.conf`)

Required for production at 1000-user scale. None of these are env-vars on Open WebUI's side — they're Valkey server config.

```conf
# Sufficient headroom for replicas × pool_size × concurrent connections
maxclients 10000

# Drop idle connections after 30 min — half-dead client cleanup
timeout 1800

# Cap RAM. Size based on observed working set; <500 MB is typical for OWUI.
maxmemory 1gb
maxmemory-policy allkeys-lru

# AOF for durability on the small amount of state OWUI cares about
appendonly yes
appendfsync everysec
```

Without `maxclients 10000` the deployment hits `max number of clients reached` after days of uptime — every login burst, every Socket.IO reconnect storm, every connection-pool growth event eats slots. The default of 10000 in newer Valkey versions is fine; older Redis versions defaulted to 4096 or even 256.

`timeout 1800` only works if `REDIS_HEALTH_CHECK_INTERVAL` is set on the client side to less than that — otherwise long-idle pooled connections get killed by Valkey and the app sees them only when it tries to use them. The pair must be set together.

`allkeys-lru` is safe for OWUI because everything it stores has an upstream of truth (Postgres or in-memory regenerable state). Connection-pool exhaustion is a worse failure mode than a cold cache.

## What's actually in Valkey at runtime

When `WEBSOCKET_MANAGER=redis`, the keys present (with prefix `open-webui:`):

| Key pattern | What it is | Sizing |
|---|---|---|
| `open-webui:models` | Distributed `MODELS` dict (model registry) | ~1 KB per model. |
| `open-webui:session_pool:<sid>` | Authenticated user data per Socket.IO session, **excluding** profile images | ~1 KB per active session. Reaped at 120s without heartbeat. |
| `open-webui:usage_pool` | Per-model active session counts | Reaped at 3s. Cheap. |
| Socket.IO pub/sub channels (`flask-socketio`-prefixed) | Cross-pod event fan-out | **The high-traffic path.** Where #23733 hurts. |
| `open-webui:tasks:*` | Task tracking. `:commands` is a pubsub channel. | Small. RedisCluster `publish()` broken (#19840) — use Sentinel. |
| `open-webui:ydoc:documents:<id>:updates` | Yjs CRDT state for collaborative notes | Only when notes are open. Compaction at 500 entries. |
| `open-webui:config:*` | PersistentConfig cache | Read-heavy. 0.9.3 fix made imports sync immediately. |
| `open-webui:ratelimit:*` | Sign-in rate limit buckets | Falls back to in-memory if Valkey unreachable. |

Profile images are explicitly excluded from `SESSION_POOL` since 0.6.37 (`socket/main.py:357-365` excludes `profile_image_url`, `profile_banner_image_url`, `date_of_birth`, `bio`, `gender`). Session state is small.

Total working-set estimate for 1000 users: <500 MB even at peak. Sizing constraint is usually CPU under #23733 fan-out, not memory.

## See also

- `references/issue-23733.md` for `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE` deep-dive.
- `references/known-issues.md` for what each fix corresponds to in version history.
- `references/sources.md` for the file paths and PR numbers behind these defaults.
