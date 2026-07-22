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

## Recurring upgrade-failure themes (GitHub, for triage matching)

- API keys break after upgrade: #20673 (`ENABLE_API_KEYS=true` "doesn't work" — check permission gate too), #20942 (keys → 500), the 0.6.37 rename+default-flip itself
- Migration failures on upgrade: #19797 (missing user.api_key), #21843/#21851 (0.7→0.8), #24253 (Alembic multiple heads)
- Postgres-specific: #21467 (groups 500 on GROUP BY); `utils/db/download` 400s by design
- SCIM: #17964/#18039 (filter case-sensitivity), #21280 (externalId, fixed 0.8.1), #24501 (deprovisioning, open)
- Streaming behind buffering proxies (IIS/ARR): #24579; `CHAT_STREAM_RESPONSE_BUFFER` exists since 0.6.37
