# Breaking-change ledger + pre-0.10 translation

The API is officially "experimental" (docs, verbatim: "this is an experimental setup and may undergo future updates for enhancement"). `/api/v1` is a namespace, not a stability contract — endpoints under it have been renamed and removed without notice. Historical rate: ~2 API-affecting breaks per quarter. **Triage step one on any instance: `GET /api/version`.**

## Ledger (verified against CHANGELOG.md + git history, v0.10.2 clone)

| Version | Date | API-affecting change |
|---|---|---|
| 0.5.0 | 2024-12-25 | folders, channels, evaluations routers added |
| 0.6.6 | 2025-05 | notes router; LICENSE gains branding clause |
| 0.6.19 | 2025-08-09 | SCIM 2.0 router (experimental); Docling moved to `/v1` (declared breaking) |
| 0.6.26 | 2025-09 | file upload gains `process_in_background` (async processing → poll status) |
| 0.6.34 | 2025-10-16 | **JWT default expiry: never → 4 weeks** — long-lived JWT automation dies silently |
| 0.6.35 | 2025-11-06 | `GET /api/v1/models/` → `/api/v1/models/list` (collision with OpenAI-compat alias) |
| 0.6.37 | 2025-11-24 | **`ENABLE_API_KEY` → `ENABLE_API_KEYS`, default flipped to OFF, no fallback for the old name**; key creation permission-gated; restriction vars renamed (those DO fall back); SCIM covered by key restrictions |
| 0.6.39 | 2025-11-25 | Docling envs consolidated into `DOCLING_PARAMS` (declared breaking) |
| 0.6.41 | 2025-12-02 | API keys → dedicated table (migration failures #19797); signin rate limiter added |
| 0.6.42 | 2025-12-21 | legacy pre-KB document/tag collections removed |
| 0.8.0 | 2026-02-12 | analytics + skills routers |
| 0.8.6 | 2026-03-01 | terminals router |
| 0.9.0 | 2026-04-20 | automations + calendars routers; key endpoint-restrictions enforced on cookie + `x-api-key` transports (bypasses start 403ing); LICENSE contributor exemption dropped |
| 0.9.2 | 2026-04-24 | `CUSTOM_API_KEY_HEADER` added |
| 0.9.5 | 2026-05-09 | unauthenticated `GET /api/v1/retrieval/` removed |
| 0.9.6 | 2026-06-01 | key allowlist matched against routed path (another tightening) |
| 0.10.0 | 2026-06-29 | **`access_control` → `access_grants` (inverted defaults); config storage → flat dot-keys; filter `outlet()` runs on direct API calls by default (#25650)** — API response bodies change; new 403s from permission enforcement on api-key view/delete, speech, image-edit; `ENABLE_RAG_LOCAL_WEB_FETCH`→`ENABLE_LOCAL_WEB_FETCH` (alias kept) |
| 0.11.0 | 2026-07-27 | **two new permission keys (`sharing.open_chats`, `access_grants.allow_groups`) that a hard-coded permissions POST silently revokes** (below); `X-Process-Time` header format changed; LDAP server-config gained 3 fields that an old-shaped PUT resets; `notifications` router added; `POST /api/v1/tasks/active/chats` removed; new `ENABLE_PLUGINS` kill switch makes function/tool lists return `200 []` |

## Translating a ≤0.9.x script to 0.10.x

**ACLs.** Old: `"access_control": null` (public-read) / `{}` (private) / `{read:{group_ids:[...],user_ids:[...]}, write:{...}}`. New:

```json
"access_grants": [
  {"principal_type": "group", "principal_id": "<gid>", "permission": "read"},
  {"principal_type": "user",  "principal_id": "*",     "permission": "read"}   ← this IS "public"
]
```

Mapping: `null` → `[{user, *, read}]`; `{}` → `[]`; each `read.group_ids[i]` → `{group, gid, read}`, etc. **Defaults inverted**: omitted grants now mean *private*, where omitted `access_control` meant *public*. Files migrate to private regardless. Old-shape payloads are silently ignored (`extra='ignore'`) — the request 200s and does nothing to ACLs; that's the failure signature.

**Config.** Old export: nested blob. New: flat `{"ui.default_models": ...}` dict; import is a partial upsert. No API-level translation — re-derive keys from a fresh `configs/export`.

**Group membership.** Old habit: update group with replacement `user_ids`. New: `GroupUpdateForm` has no `user_ids`; use incremental `POST /groups/id/{id}/users/add` / `/users/remove`.

**Community content warning.** Blogs/scripts (and LLM prior knowledge) overwhelmingly teach the ≤0.6.x shapes, and some community accounts are outright backwards (e.g. claims that `/api/v1/chat/completions` was renamed to `/api/chat/completions` — in reality `/api/chat/completions` is primary and the `/api/v1` form is a later alias). When in doubt, the router source for the running version is the only authority.

## Translating a 0.10.x script to 0.11.0

**Permissions — read-modify-write, never POST a literal.** 0.11.0 adds `sharing.open_chats` (default false) and `access_grants.allow_groups` (default true) to the default-permissions dict (`config.py:1950,1955`). `has_permission` **denies on any missing path segment** (`utils/access_control/__init__.py:87-89`), so a script that POSTs a hard-coded 0.10-shaped body to `/api/v1/users/default/permissions` silently revokes group-based access grants for every non-admin. Always `GET`, mutate the returned dict, then `POST` it back.

**`sharing.open_chats` cannot survive an API save (upstream bug, verified live on 0.11.0).** `config.py:1950` defines the key and `routers/chats.py:2041` enforces it, but the server-side `SharingPermissions` model has no `open_chats` field (`routers/users.py:191-205`). Every `POST /api/v1/users/default/permissions` — including saves from the admin UI — drops the key, after which open chat sharing reads as denied. A live `GET` returns a `sharing` block with no `open_chats` at all. There is no API-side workaround; the value has to be restored in config storage directly.

**`X-Process-Time` is now fractional seconds** — was `str(int(elapsed))` (nearly always `"0"`), now `f'{elapsed:.6f}'` (`utils/asgi_middleware.py:174-177`). `int(resp.headers['X-Process-Time'])` raises `ValueError`.

**LDAP server config gained fields.** `LdapServerConfig` added `enable_group_management`, `enable_group_creation`, `attribute_for_groups` (`routers/auths.py:1256-1261`) and the handler upserts the full `model_dump()`. A 0.10-shaped PUT silently resets group management/creation to false. Same read-modify-write rule. Likewise `POST /auths/admin/config` gained `CHANNEL_MODEL_RESPONSE_MODE` (defaults back to `thread` when omitted).

**Read endpoints now redact by access level — back up with an admin token or lose data.** Three responses silently drop fields for callers without *write* access:

| Endpoint | Dropped | Condition |
|---|---|---|
| `GET /models/list` | `params` → `{}` (incl. the system prompt) | `not write_access`, i.e. not owner, no `write` grant, and not (admin ∧ `BYPASS_ADMIN_ACCESS_CONTROL`) — `models.py:197-200` |
| `GET /tools/id/{id}` | `content` (the tool source) | no write access — `tools.py:463` |
| `/api/models`, `/models/list`, `/models/id/{id}` | `meta.knowledge[].data.content` | always; a `field_validator` strips it **and `Models.get_*` rewrites `model.meta` in the DB** — not reversible by downgrading (#27287) |

This is the dangerous shape for GitOps: a read-only service account exports, gets `params: {}`, and a later `import`/`sync` writes the emptied catalog back. Export with an admin token, and diff before syncing. `GET /models/export` is *not* stripped (`models.py:333`) — prefer it over `/models/list` for backups.

**Token accounting inverted.** `usage.prompt_tokens` / `completion_tokens` were cumulative across all model calls in a turn; they now report the **last call only**, while `input_tokens`/`output_tokens`/`total_tokens` stay cumulative (`utils/response.py`, #27031). A 6-round tool loop bills as round 6 — silent undercount for any metering script.

**`updated_at` no longer moves on background writes.** `Chats.update_chat_by_id` gained `touch: bool = True`, and ~14 call sites pass `touch=False` (title generation, tags, sources, status, compaction, variables, note-chats). A chat can change materially without its timestamp moving — breaks `updated_at`-based incremental sync.

**Chat queries hide "internal" chats.** ~25 query sites add `WHERE meta->>'internal' IS NOT TRUE`; note-chats and sub-agent chats are stored as chats with `meta.internal=true`. List/search/export/count endpoints won't show them, so API counts will disagree with `SELECT count(*)` against the DB.

**Admins lost access to other users' automations.** The `user.role != 'admin'` exemption was removed — non-owners now get **404, not 403** (`routers/automations.py`), so fleet-wide automation management via an admin token reads as "deleted" rather than "forbidden".

**Upgrade-blocking, not API:** 0.11.0 adds a case-insensitive unique index on user email (`uq_user_email_lower`); the migration **raises `RuntimeError` and aborts startup** if `A@x.com` and `a@x.com` both exist — dedupe before upgrading, and stop provisioning scripts from creating case-variant duplicates. The release also declares **rolling upgrades unsupported** (schema changes; all instances must move at once), which breaks blue/green and rolling k8s deploys.

**Sockets/terminals accept JWTs only.** The new `get_verified_user_by_token` (`utils/auth.py:503-513`) calls `decode_token`, so `sk-` API keys do **not** authenticate socket.io or terminal handshakes — only JWTs do.

## Recurring upgrade-failure themes (GitHub, for triage matching)

- API keys break after upgrade: #20673 (`ENABLE_API_KEYS=true` "doesn't work" — check permission gate too), #20942 (keys → 500), the 0.6.37 rename+default-flip itself
- Migration failures on upgrade: #19797 (missing user.api_key), #21843/#21851 (0.7→0.8), #24253 (Alembic multiple heads)
- Postgres-specific: #21467 (groups 500 on GROUP BY); `utils/db/download` 400s by design
- SCIM: #17964/#18039 (filter case-sensitivity), #21280 (externalId, fixed 0.8.1), #24501 (deprovisioning, open)
- Streaming behind buffering proxies (IIS/ARR): #24579; `CHAT_STREAM_RESPONSE_BUFFER` exists since 0.6.37
