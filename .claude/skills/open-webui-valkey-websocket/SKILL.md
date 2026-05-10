---
name: open-webui-valkey-websocket
description: |-
  Deploy Open WebUI multi-pod with WebSockets and Valkey/Redis Sentinel at 1000+ user scale on Kubernetes. Centerpiece is the structural Socket.IO+Redis frame-amplification bug (#23733) that cripples multi-pod streaming, and the maintainer-endorsed mitigation (`CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE`). Covers all multi-pod env vars, the custom-model-icon perf history (base64-in-/api/models, fixed late 2025–Apr 2026), the official helm chart's gaps (bundled Redis is unsuitable for production; no HPA/PDB/probes/sticky sessions), and the catalog of known multi-pod issues with current status.
when_to_use: |-
  Trigger on "open-webui multi-pod", "open-webui replicas", "open-webui scaling", "open-webui websocket", "open-webui valkey", "open-webui redis", "WEBSOCKET_MANAGER", "WEBSOCKET_REDIS_URL", "ENABLE_WEBSOCKET_SUPPORT", "REDIS_KEY_PREFIX", "CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE", "open-webui 1000 users", "open-webui websocket disconnect", "open-webui model icon", "open-webui profile_image_url", "open-webui custom thumbnail", "issue 23733", "openwebui kubernetes", "openwebui helm", "open-webui rolling update", "openwebui sso avatar slow". Also trigger on symptom descriptions: "we had to disable multi-pod", "websocket caused performance problems", "had to drop replicas to 1", "thumbnail/icon caused slowness". NOT for Open WebUI's RAG/embedding/rerank pipeline (use `open-webui-embeddings`), tool/function development, or single-pod home-lab setups.
---

# Open WebUI multi-pod with Valkey Sentinel + WebSockets — operator reference

Target: deploying Open WebUI on Kubernetes with 3+ replicas, WebSocket support enabled, Valkey Sentinel for shared state and Socket.IO pub/sub, at 1000+ user scale. Sentinel is the topology — not a recommendation, just the operating reality.

The single most important thing to internalize before going multi-pod: **issue #23733 (Socket.IO frame amplification) is open and structural**. It is the most likely cause of "we had to turn off multi-pod and websockets" in production. The mitigation is one env var. Read `references/issue-23733.md` first.

## The big bug, in 60 seconds (#23733)

**What it does:** Open WebUI streams assistant responses via Socket.IO. By design, **every single SSE token causes the backend to re-serialize the entire accumulated assistant message and emit it as a new Socket.IO frame**. The frame contains the full message-so-far, not the delta.

**Why it was designed that way (maintainer's words):** *"Every Socket.IO frame carries the complete rendered content of the assistant message. […] If a WebSocket frame is dropped, the connection flaps, the user switches tabs and comes back, or the browser GC causes a missed event, the very next frame self-corrects because it contains the complete truth."* Self-healing client, fully stateless frontend.

**Why it falls apart with `WEBSOCKET_MANAGER=redis` + multi-pod:** Each emit goes through `socketio.AsyncRedisManager`, which serializes the frame and broadcasts it to every pod via Valkey pub/sub. So a 4000-token response generates **4000 frames, each carrying the full accumulated message**. Total bandwidth is O(N²). With a 6-Valkey-node × 4-worker × 100-concurrent-stream setup, the issue author measured **~10,000× infrastructure-traffic amplification**. Reasoning models and tool-calling make it worse because the messages get longer and more structured.

**Status (May 2026):** Open. Maintainer wants a Yjs-based redesign; multiple PRs (#23735, #23736, #24126, #24171) closed without merge. **No merge ETA.**

**Mitigation — set this env var:**

```bash
CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=10
```

Default is `1` (emit on every token). Setting to `10` cuts total bandwidth ~10×; `20` cuts it ~20×. Maintainer-endorsed: *"cuts total bandwidth proportionally with zero code changes and zero change to the reliability model. It is still O(N²) but with a meaningfully smaller constant."*

This is the single highest-leverage knob for multi-pod health. Set it before re-enabling websockets in production. Full deep-dive in `references/issue-23733.md`.

## Triage table

| Symptom | Probable cause | Where |
|---|---|---|
| Multi-pod + WS works at 10 users, melts at 100+ | #23733 amplification — every token re-broadcasts full message via Valkey pub/sub | `references/issue-23733.md` |
| `/api/models` response is multi-MB; reconnect storms during rollouts | Pre-0.6.37 base64 model icons in `model.meta.profile_image_url` | `references/icons-thumbnails.md` |
| `POST /api/tasks/stop/{id}` does nothing across pods | Worker-local task tracking — fixed in dev for Sentinel; broken on RedisCluster (#19840) | `references/known-issues.md` §RedisCluster |
| "Model not found" intermittent under load | `RedisDict.set()` race (DELETE + HSET non-atomic) — fixed in 0.8.x (#22734) | `references/known-issues.md` §RedisDict-race |
| Login loop / 401 on session validation across pods | `WEBUI_SECRET_KEY` differs across replicas | `references/configuration.md` §Secrets |
| Direct-connection chat hangs with `workers > 1` | WS lands on one worker, API request on another (#15162, partial fix #22402) | `references/known-issues.md` §direct-connection |
| Inflated active user count, never goes down | Pre-0.6.41 socket-pool counter; fixed via DB-backed heartbeat (#16074) | `references/known-issues.md` §user-count |
| Sentinel readiness probe fails on 0.9.1 with `'coroutine' object is not callable` | #23987 — `pubsub()` regression; closed 2026-05-08, fix shipped in 0.9.4 | `references/known-issues.md` §sentinel-0.9.1 |
| Admin pages take 30s to load after SSO migration | SSO avatar sync stuffs base64 into user records (#12325) | `references/icons-thumbnails.md` §SSO |
| WS stable for hours, then mass disconnect after firewall idle | No TCP keepalive on Redis pool — set `REDIS_SOCKET_KEEPALIVE=True`, `REDIS_HEALTH_CHECK_INTERVAL=60` (added 0.9.0+) | `references/configuration.md` §Robustness |
| Migration races on rolling restart | Multiple pods running migrations simultaneously — set `ENABLE_DB_MIGRATIONS=false` on all but one | `references/configuration.md` §Migrations |
| Helm chart bundled Redis loses state on restart | Bundled Redis is a no-PVC Deployment; unsuitable for production | `references/helm-chart.md` §Bundled-redis |

## Production env block (read before deploying)

The minimum viable env block for multi-pod with Valkey Sentinel and WebSockets enabled:

```bash
# --- Database (Postgres mandatory; SQLite-on-shared-storage corrupts) ---
DATABASE_URL=postgresql://owui:***@postgres:5432/openwebui
DATABASE_POOL_SIZE=15
DATABASE_POOL_MAX_OVERFLOW=20

# --- Vector DB (default ChromaDB cannot be shared across pods) ---
VECTOR_DB=pgvector
PGVECTOR_DB_URL=postgresql://owui:***@postgres:5432/openwebui

# --- Valkey + Sentinel (general state and Socket.IO pub/sub) ---
REDIS_URL=redis://valkey-master:6379/0
REDIS_SENTINEL_HOSTS=valkey-sentinel-0,valkey-sentinel-1,valkey-sentinel-2
REDIS_SENTINEL_PORT=26379
REDIS_KEY_PREFIX=open-webui                  # same across replicas of THIS deployment
REDIS_HEALTH_CHECK_INTERVAL=60
REDIS_SOCKET_KEEPALIVE=True
REDIS_SOCKET_CONNECT_TIMEOUT=5

# --- WebSocket via Socket.IO + Valkey ---
ENABLE_WEBSOCKET_SUPPORT=true
WEBSOCKET_MANAGER=redis
WEBSOCKET_REDIS_URL=redis://valkey-master:6379/1   # /1 separates WS pub/sub from app state
WEBSOCKET_SENTINEL_HOSTS=valkey-sentinel-0,valkey-sentinel-1,valkey-sentinel-2
WEBSOCKET_SENTINEL_PORT=26379
WEBSOCKET_REDIS_LOCK_TIMEOUT=60

# --- THE #23733 mitigation. Set this. ---
CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=10

# --- Memory-leak guard (default pypdf + SentenceTransformers leak in long-running pods) ---
CONTENT_EXTRACTION_ENGINE=tika
TIKA_SERVER_URL=http://tika:9998
RAG_EMBEDDING_ENGINE=openai

# --- Concurrency model: 1 worker per pod, scale via replicas ---
UVICORN_WORKERS=1

# --- Migrations: exactly one designated pod. Better: separate Job. ---
ENABLE_DB_MIGRATIONS=false      # set to true on the designated migration pod only

# --- SSO avatar bloat killer (only relevant if OIDC/OAuth) ---
OAUTH_PICTURE_CLAIM=""
OAUTH_UPDATE_PICTURE_ON_LOGIN=false

# --- Identical on every pod (otherwise login loops, OAuth-token decryption fails) ---
WEBUI_SECRET_KEY=<32+ bytes, identical across pods>
OAUTH_SESSION_TOKEN_ENCRYPTION_KEY=<same>      # falls back to WEBUI_SECRET_KEY
OAUTH_CLIENT_INFO_ENCRYPTION_KEY=<same>        # falls back to WEBUI_SECRET_KEY
```

Per-variable defaults, semantics, and version-added details live in `references/configuration.md`. Helm chart override block in `references/helm-chart.md`.

## Custom model icons / thumbnails — was this our problem?

For deployments that ran multi-pod + WS in early 2026 and disabled it after performance died, custom model thumbnails are a strong suspect alongside #23733. Pre-0.6.37 (Nov 2025) the entire base64 image lived in `model.meta.profile_image_url` and was returned in `/api/models` for every model on every page load and every WS reconnect. With ~350 models and HD icons, the response payload exceeded 4 MB (issue #18950). On reconnect storms during rollouts: N pods × M users × 4 MB simultaneously, on top of the WS amplification.

The full audit of fixes (PR #19097 Nov 2025, tjbck commit drops `meta.profile_image_url` Nov 21, PR #19519 Dec 2025 strips from "most endpoints", PR #24015 Apr 2026 default-avatar redirect, PR #23796 reuse DB session) lives in `references/icons-thumbnails.md`. **Most of the bloat is gone in ≥0.6.42, fully cleaned up by 0.9.4.** A couple of admin endpoints (`/api/v1/users`, `/api/v1/tools`, etc.) lagged behind the model-list fix — verify on the deployment's target version.

## Reference index

- **`references/issue-23733.md`** — The Socket.IO frame amplification bug. Architecture explanation, full maintainer quote with rationale, the four PRs that didn't merge, the mitigation knob, and what the eventual fix likely looks like (Yjs document streaming).
- **`references/configuration.md`** — Every multi-pod-relevant env var with default, source-file location, and version added. Valkey/Redis configuration (`maxclients`, `timeout`, `maxmemory-policy`). Why `WEBUI_SECRET_KEY` must be shared.
- **`references/helm-chart.md`** — `open-webui/helm-charts` v14.4.0 specifics. The bundled Redis is unsuitable for production — disable it. What the chart doesn't ship (HPA, PDB, probes, sticky sessions). The values.yaml override block. Open chart issues (#383 gateway-API).
- **`references/icons-thumbnails.md`** — Why custom model icons crashed multi-pod pre-0.6.37. The full chronology of fixes. Endpoints to spot-check on the upgrade target. SSO avatar mitigation.
- **`references/known-issues.md`** — #23733, #15162 direct-connection multi-worker routing, #19840 RedisCluster publish broken, #22734 RedisDict race, #23987 Sentinel 0.9.1 regression, #16074 inflated user count, plus the April-2026 batch of merged fixes (#23571 keepalive, #23709 ASGI middleware, #23642 stale Socket.IO sessions, #23896 cross-worker cache invalidation).
- **`references/sources.md`** — Authoritative source files in the open-webui codebase, GitHub issue/PR numbers with dates, and docs.openwebui.com URLs underlying every claim. Load to verify a specific fact or run `freshen` mode.

### Scripts

- **`scripts/check-amplification.sh <valkey-host:port> [duration-seconds]`** — Sample Valkey `MONITOR` for the given duration, count Socket.IO `PUBLISH` ops, and estimate whether `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE` is set to a sane value. Run during an active long-response chat stream to verify the #23733 mitigation is in effect.

## Non-negotiables before re-enabling multi-pod + WS

These are the few things that will sink a deployment if missed. The env block above and the references cover the full configuration; this list is the irreducible minimum to internalize.

- **≥0.9.4.** Earlier versions are missing the April-2026 robustness batch (RedisDict race, ASGI middleware, stale Socket.IO session cleanup, Redis keepalive, profile-image cleanup).
- **`CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=10`.** The single highest-leverage knob until #23733 lands. See `references/issue-23733.md` for why.
- **Identical `WEBUI_SECRET_KEY` on every pod.** Different keys → login loops and OAuth-token decryption failures across pods.
- **One pod runs migrations** (or a separate Job). Other pods set `ENABLE_DB_MIGRATIONS=false`. Concurrent migrations on rolling restart corrupt schema state.
- **No bundled chart Redis in production.** It is a no-PVC single-pod Deployment. Set `websocket.redis.enabled: false` and point at external Valkey Sentinel. See `references/helm-chart.md`.

Validate on staging before production: load-test 100+ concurrent reasoning-model streams to exercise #23733; roll once and watch for session drops; verify Sentinel failover trips the readiness probe; spot-check the admin endpoints in `references/icons-thumbnails.md`.
