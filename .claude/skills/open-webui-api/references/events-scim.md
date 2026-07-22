# Event webhooks + SCIM provisioning (v0.10.2)

## Outbound event webhooks (new in 0.10.x)

Nearly every admin-relevant action publishes a typed event; webhooks push them to a configured endpoint — the closest thing to a *domain-event* feed the API offers. For per-HTTP-request forensics (who/what/where/which client) use the audit log instead — see **Audit log** below; it has no read API but can stream to stdout.

```bash
curl $B/api/events -H "Authorization: Bearer $T"          # event catalog for this version
curl -X POST $B/api/events/webhooks -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"name":"audit-sink","url":"https://collector.example.com/owui","enabled":true,
       "events":["auth.login","auth.signup","auth.api_key.created","chat.deleted_all"],"targets":[]}'
# PUT /api/events/webhooks/{id} to edit, DELETE to remove
```

Event names are dot-namespaced strings (registry: `backend/open_webui/events.py`). Families as of 0.10.2: `auth.*` (login, logout, signup, password_changed, api_key.created/deleted, oauth_session.deleted), `chat.*` (created, deleted, deleted_all, imported, shared, archived, pinned, cloned, compacted, tag_added/removed, folder_updated), `channel.*` (+member/webhook subevents), `automation.*` (created/updated/deleted, run_started/completed/failed, enabled/disabled), `calendar.*` (+event subevents), plus model/config/user families. Pull the live catalog from `GET /api/events` rather than hardcoding — the registry grows per release.

Inbound (different feature): channels accept unauthenticated posts at `POST /api/v1/channels/webhooks/{webhook_id}/{token}` (token-in-URL).

## Audit log (per-request metadata)

Per-HTTP-request trail with the OWUI **user identity attached** — the one thing a front proxy's access log (Traefik) can't give you, since it can't decode the session cookie. No read API; it's a log stream. `AUDIT_LOG_LEVEL` (env, default `NONE`): `METADATA` = metadata only, `REQUEST`/`REQUEST_RESPONSE` add bodies. Entry JSON:

```
id, timestamp, user{id,email,role,name}, audit_level, verb,
request_uri, response_status_code, source_ip, user_agent, request_object, response_object, extra
```

Default sink is **file-only** (`AUDIT_LOGS_FILE_PATH`, default `DATA_DIR/audit.log`) — lost on a stateless pod with no PVC, and OWUI's chart has no sidecar to tail it. Stream it out instead (verified in `utils/logger.py` `audit_filter`):

```
ENABLE_AUDIT_STDOUT=True      # default False — audit records → container stdout (cluster log pipeline collects them)
LOG_FORMAT=json               # structured lines
ENABLE_AUDIT_LOGS_FILE=False  # optional: skip the ephemeral file
```

All audit vars are env-only (not PersistentConfig).

## SCIM 2.0 (experimental, 0.6.19+)

The clean path for IdP-driven user/group lifecycle (Entra, Okta, Keycloak). Community edition — env-gated, not license-gated.

Enable (env-only, restart required — the router is mounted at startup):

```
ENABLE_SCIM=true          # legacy alias SCIM_ENABLED still read
SCIM_TOKEN=<long-random>  # static shared bearer; compared with hmac.compare_digest
SCIM_AUTH_PROVIDER=<oauth-provider-name>   # e.g. "oidc" — where externalId is stored; warning logged if unset
```

Base URL `/api/v1/scim/v2`, auth `Authorization: Bearer $SCIM_TOKEN` — **outside** the JWT/API-key system entirely (user tokens don't work here, SCIM token works nowhere else). 403 = SCIM disabled; 401 = bad token.

| Endpoint | Notes |
|---|---|
| `GET /ServiceProviderConfig`, `/ResourceTypes`, `/Schemas` | discovery, unauthenticated |
| `GET /Users?filter=...` | eq/ne/co/sw/ew/pr operators, incl. externalId; case-sensitivity is non-compliant (#17964/#18039) |
| `POST|GET|PUT|PATCH /Users(/{id})` | create/read/replace/patch |
| `DELETE /Users/{id}` | **deactivates** (role → pending), does not delete |
| same set for `/Groups` | group membership sync |

Semantics that surprise IdP admins:
- `active: true` ⇄ role `user`; `active: false` ⇄ role `pending`. SCIM **never demotes an existing admin** (guard in scim.py) — admin role changes stay manual.
- Since 0.6.37, API-key endpoint restrictions also cover SCIM paths (#19168) — irrelevant for the SCIM token itself, but a restricted `sk-` key cannot probe SCIM endpoints.
- Deprovisioning gap tracked in #24501 (open as of 2026-07-21).

Alternative without SCIM: trusted-header auth (`WEBUI_AUTH_TRUSTED_EMAIL_HEADER`, `..._GROUPS_HEADER` for group sync) auto-provisions at signin — pick one mechanism, not both.
