# Endpoint map with auth levels — v0.11.0

Roles: **[admin]** = `get_admin_user`, **[user]** = `get_verified_user` (role user/admin; resource ACLs apply on top), **[current]** = any authenticated identity incl. `pending`, **[public]** = no auth. API keys pass wherever JWTs do (key inherits owner's role); SCIM uses its own bearer token.

Derived from `backend/open_webui/main.py:785–829` (mounts) and per-router `Depends()` audit. Live-instance surface may differ only by feature flags (SCIM, analytics, channels) — diff the instance's `openapi.json` (needs `ENV=dev`) against this map, never assume version drift first.

## Mount table (main.py)

| Prefix | Router | Notes |
|---|---|---|
| `/api/v1/{pipelines,tasks,images,audio,retrieval,configs,auths,users,channels,chats,notes,models,knowledge,prompts,tools,skills,memories,folders,groups,files,functions,evaluations,utils,terminals,automations,calendars}` | routers/*.py | calendar mounts at plural `/calendars` |
| `/api/v1/notifications` | notifications.py | new in 0.11.0; unconditional mount (`main.py:808`) |
| `/api/v1/analytics` | analytics.py | only if `ENABLE_ADMIN_ANALYTICS` (default true) |
| `/api/v1/scim/v2` | scim.py | only if `ENABLE_SCIM` (default false); toggle needs restart |
| `/ollama`, `/openai` | proxies | not under /api/v1 |
| `/ws` | socket.io | channels + streaming events |
| app-level `/api/*`, `/oauth/*`, `/health*` | main.py | see below |

## Auth character per domain

- **Admin-only routers** (every endpoint): pipelines, analytics.
- **Admin-heavy**: configs (23 admin / 2 user), functions (13 admin / 4 user — arbitrary server-side Python; note `GET /functions/` itself is [user]), auths admin-config block, groups (CRUD admin, listing user), evaluations config/feedback-admin/leaderboard, ollama model lifecycle, retrieval config/reset.
- **User-level routers** (0 admin endpoints): channels, calendars, memories, folders, notes, skills, prompts, automations, notifications, terminals.
- **User with admin escape hatches**: chats (admin: `/list/user/{id}`, `/all/db`, config), files (admin: `DELETE /all`), tools (admin: `/load/url`), models (admin: `/base`, `/sync`, `DELETE /delete/all`), knowledge (admin: `/external/*`, `/metadata/reindex`, `/{id}/export`), tasks (admin: `/config/update`).

## Key admin groups (prefix /api/v1 unless noted)

### users
- `GET /users/?query=&order_by=&direction=&page=` [admin] — 30/page fixed, returns `{users:[...incl group_ids], total}`
- `GET /users/all` [admin]; `GET /users/search` [user]
- `GET|POST /users/default/permissions` [admin] — global permission template (see config-system.md for shape)
- `GET /users/{id}`, `/{id}/groups`, `/{id}/oauth/sessions` [admin]
- ⚠️ `GET /users/{id}/info` and `/{id}/active` are **[user], not [admin]** (`routers/users.py:765,852`) — any verified user can read any other account's name, email, role, group memberships and online status by id. Treat as an info-disclosure surface when reviewing a deployment.
- `GET /users/{id}/preview` [admin] — enumerates every resource that user can reach across all their groups; the per-user twin of `/groups/id/{id}/preview` and the best "what can this account actually see?" audit call.
- `GET /users/default/permissions/defaults` [admin] — the shipped `DEFAULT_USER_PERMISSIONS` baseline (not live config); diff live against it to see what was customised.
- `POST /users/{id}/update` [admin] — partial: `{role?, name?, email?, password?, profile_image_url?}`; role change disconnects user's websockets. No separate role endpoint.
- `DELETE /users/{id}` [admin]. Primary admin (first user) is immutable to other admins.
- Deactivation = role `pending` (no active flag).

### groups
- `GET /groups/` [user, own groups for non-admins]; `POST /groups/create` [admin] `{name, description, permissions?, data?}` — **no members at create**
- `POST /groups/id/{id}/users/add|remove` [admin] `{user_ids:[...]}` — incremental, not replacement; invalid ids silently filtered
- `POST /groups/id/{id}/users` (list members), `GET .../export` (incl. user_ids), `GET .../preview` (audit reachable resources) [admin]
- `POST /groups/id/{id}/update` [admin] (no user_ids field); `DELETE .../delete` [admin]

### auths
- [public]: `POST /auths/signin|signup|signout|ldap` (signin rate-limited 15/3min/email w/ Redis)
- `GET /auths/` [current] — session probe; `POST /auths/add` [admin] — create user, **returns a login token for the new user**
- `GET|POST /auths/admin/config` [admin] — ENABLE_SIGNUP, DEFAULT_USER_ROLE, JWT_EXPIRES_IN, ENABLE_API_KEYS, API_KEYS_ALLOWED_ENDPOINTS, feature toggles; invalid values silently dropped
- `GET|POST /auths/admin/config/ldap` + `/ldap/server`; `GET|POST /auths/admin/config/oauth` [admin]
- `POST|GET|DELETE /auths/api_key` [current] — self-service key (gated: ENABLE_API_KEYS + permission)

### configs
- `GET /configs/export` [admin] — flat dot-keyed dump of ALL config; `POST /configs/import` `{config:{...}}` — partial upsert
- `GET /configs/namespace/{ns}` [admin]
- `GET|POST /configs/connections`, `/configs/tool_servers` (+`/verify`), `/configs/terminal_servers` (+`/verify`), `/configs/code_execution`, `/configs/models`; `POST /configs/suggestions` [admin]. `/configs/banners`: **POST is [admin], GET is [user]** (`configs.py:840,859`).
- `POST /configs/terminal_servers/{policy,lifecycle,refresh}` [admin] — server-side proxies that call an operator-supplied `{url}` with an operator-supplied bearer from inside the cluster (SSRF-shaped outbound surface). `refresh` with `reset: true` destroys running terminal sessions for a user or a whole policy.
- `POST /configs/oauth/clients/register` [admin] — RFC 7591 client registration toward OAuth-protected tool servers

### models (workspace presets)
- `GET /models/list` [user] (NOT bare `/models` — OpenAI-compat alias)
- `POST /models/create`, `GET /model?id=`, `POST /model/update` (**must include `access_grants`** — omitting it 500s; see SKILL.md gotchas), `POST /model/toggle?id=`, `POST /model/delete` [user+ACL]
- `POST /models/model/access/update` `{id, access_grants:[...]}` [user+perm]
- GitOps: `GET /models/export` → `POST /models/import` (additive) → `POST /models/sync` — **only `/sync` is [admin]** (`models.py:488`); export/import are [user] plus an in-body `workspace.models_export` / `models_import` permission check (`models.py:315,347`), so a non-admin service account holding those permissions can dump and load the catalog. `/sync` is **declarative — it deletes models absent from the payload**.
- app-level: `GET /api/models` (effective list) [user], `GET /api/models/base` [admin], `POST /api/models/unload` [admin]

### knowledge + files + retrieval (RAG)
- `POST /knowledge/create` `{name, description, access_grants?}`; `GET /knowledge/{id}` (with files); `/update`, `/delete`, `/reset` [user+ACL]
- `POST /files/` [user] multipart, `?process=true&process_in_background=true` → **poll `GET /files/{id}/process/status` until `completed`** before attaching (else 400)
- `POST /knowledge/{id}/file/add|update|remove` `{file_id}`; batch `/files/batch/add`; diff `/sync/diff`; `GET /{id}/export` [admin]
- `POST /knowledge/reindex` [user-perm], `/metadata/reindex` [admin]
- `GET|POST /retrieval/config(/update)` [admin] — hybrid search, rerankers, extraction engines; `GET|POST /retrieval/embedding(/update)` [admin] — embedding engine switch (unloads old model)
- Danger [admin]: `POST /retrieval/reset/db`, `/reset/uploads`, `DELETE /files/all`

### functions / tools / pipelines
- functions [all admin — arbitrary server-side Python]: `/functions/create` `{id,name,content,meta}`, `/id/{id}/toggle`, `/toggle/global`, `/sync`, valves
- tools [user+ACL]: CRUD + valves; `POST /tools/load/url` [admin]
- pipelines [all admin, proxied to a pipelines server]: `/pipelines/list`, `/add` `{url, urlIdx}`, `/upload`, `/delete`, valves

### observability + ops
- analytics [admin]: `/analytics/{summary,daily,tokens,users,messages,models}`, `/analytics/models/{id}/chats|overview`
- events (app-level, [admin]): `GET /api/events` (catalog), `GET|POST /api/events/webhooks`, `PUT|DELETE /api/events/webhooks/{id}` — outbound event webhooks
- `GET /api/usage` [user]; `GET /api/tasks` [admin], `POST /api/tasks/stop/{id}` [admin]
- `GET /utils/db/download` [admin, `ENABLE_ADMIN_EXPORT`, SQLite only — 400 on Postgres]; `POST /utils/code/execute` [user]
- chats admin: `GET /chats/list/user/{id}?page=` (needs `ENABLE_ADMIN_CHAT_ACCESS`), `GET /chats/all/db` (needs `ENABLE_ADMIN_EXPORT`); own export `GET /chats/all` (NDJSON stream)
- evaluations [admin]: `/evaluations/config`, `/feedbacks/list`, `/feedbacks/all/export`, `DELETE /feedbacks/all`

### Inference surfaces (for completeness)
- `POST /api/chat/completions` (alias `/api/v1/chat/completions`) [user] — OpenAI shape + extras: `files:[{type:'file'|'collection',id}]` (RAG), `tool_ids:["server:mcp:<id>"]`, `params:{...}` per-request
- `POST /api/embeddings` (alias `/api/v1/embeddings`) [user]; `POST /api/message` / `/api/v1/messages` — Anthropic Messages-compatible [user]
- `/ollama/*`: inference [user], model lifecycle `api/pull|create|copy|delete|push|unload|ps` [admin], `GET /ollama/` + `api/version` [public]
- `/openai/*`: `config(/update)`, `verify` [admin]; models/chat/completions/responses/audio [user]; `/{path}` catch-all passthrough gated by `ENABLE_OPENAI_API_PASSTHROUGH`

## New in 0.11.0 (delta from 0.10.2: +21 routes, −1)

Only one addition is admin-gated; the rest are user-level. Route set diffed AST-wise across `v0.10.2..v0.11.0`, auth levels read from each handler's `Depends()`.

- **`GET|POST /configs/subagents` [admin]** — the only new admin surface. `SubagentsConfigForm`: `ENABLE_SUBAGENTS`, `SUBAGENTS_BACKGROUND_ENABLED`, `SUBAGENTS_MAX_CONCURRENT|MAX_ASYNC|MAX_ITERATIONS|MAX_OUTPUT`, `SUBAGENTS_SYSTEM_PROMPT`. POST emits `EVENTS.CONFIG_UPDATED` (`routers/configs.py:778,786`).
- **`/notifications/*` [user]** — per-user outbound webhook targets, stored in `user.settings['notifications']`, not a table. `GET /events` (catalog), `GET|POST /targets`, `PUT|DELETE /targets/{id}`, `PUT /targets/{id}/default`, `POST /targets/{id}/test`. Double-gated: **404** if config `ui.enable_user_webhooks` (env `ENABLE_USER_WEBHOOKS`) is falsy, **403** for non-admins lacking the `features.webhooks` permission. Subscribable events: `chat.finished`, `chat.failed`, `channel.message`, `calendar.alert`. Responses mask the URL (`config.url_masked`) — secrets never round-trip, so a GET cannot be used to back up a target's URL.
- `GET /users/usage` [user] — own token/message stats; query `days` (7–732) or `start_date`/`end_date` epoch-seconds.
- `GET /users/user/variables`, `POST /users/user/variables/update` [user] — chat variables; update **replaces** the whole dict and validates key regex / value length (400 on violation).
- `POST /chats/read`, `POST /chats/{id}/unread`, `POST /folders/{id}/read` [user] — unread tracking; responses carry `folder_unread_counts`.
- `POST /chats/{id}/fork` [user] — needs the `chat.import` permission; 409 if the chat has active tasks or an unfinished assistant message.
- `GET|POST /notes/{id}/chat`, `GET /notes/{id}/chats` [user] — hidden note-attached chats (`internal_meta.type='note'`).
- `POST /ollama/v1/embeddings[/{url_idx}]` [user] — OpenAI-shaped embeddings proxy.
- **Removed**: `POST /api/v1/tasks/active/chats` (present in 0.10.2, gone in 0.11.0).

### Public (no auth) — complete list, v0.11.0 (24 routes)

`/auths/signin|signup|signout|ldap`, `POST /auths/oauth/{provider}/token/exchange`, oauth login/callback/backchannel-logout, SCIM discovery trio (ServiceProviderConfig/ResourceTypes/Schemas), `GET|HEAD /ollama/`, channels inbound webhook `POST /api/v1/channels/webhooks/{webhook_id}/{token}`, `/health`, `/health/db`, `/ready`, `/api/config`, `/api/version`, `/api/changelog`, `/manifest.json`, `/opensearch.xml`.

Two that need calling out:

- **`GET /ollama/api/version` is NO LONGER public** — it gained `get_verified_user` in 0.11.0 (`routers/ollama.py:538`) and 401s anonymously (verified live). Unauthenticated liveness probes pointed at it break on upgrade. `GET /ollama/` itself is still public — use that instead.
- **`GET /chats/share/{share_id}` is now anonymously readable** when the share is "open" — 0.11.0 swapped `get_verified_user` for `get_optional_verified_user` (`routers/chats.py:1188-1193`). In 0.10.2 a share link still required a logged-in account. Security-posture change; audit existing share links after upgrading.

**`ENV=dev` adds an unauthenticated 25th route.** `GET /api/v1/retrieval/ef/{text}` is registered only under `if ENV == 'dev'` (`routers/retrieval.py:2987-2990`) and carries **no auth dependency at all** — anyone who can reach the instance can drive the embedding model with arbitrary text. Since the only supported way to expose `/openapi.json` and `/docs` is `ENV=dev`, that convenience is not free on an internet-reachable deployment.
