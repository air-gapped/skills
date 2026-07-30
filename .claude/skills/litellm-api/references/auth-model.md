# Auth model — credentials, roles, gating

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29). Authoritative sources: `litellm/proxy/_types.py:270-867` (`LiteLLMRoutes` enum), `litellm/proxy/auth/route_checks.py`, `litellm/proxy/auth/user_api_key_auth.py`.

## Credential types

| Credential | Recognized by | Effective role |
|---|---|---|
| Master key | `secrets.compare_digest` (`user_api_key_auth.py:1591`) | `PROXY_ADMIN`; logged as `LITELLM_PROXY_MASTER_KEY_ALIAS` |
| **No master key configured** | `user_api_key_auth.py:1406-1417` | **any request → `INTERNAL_USER`, `common_checks` skipped entirely (`:2160-2165`) — the whole management API is open.** Undocumented. |
| Virtual key (`sk-…`) | DB lookup | role from linked user row |
| UI session token | `is_session_token=True`, team `litellm-dashboard` (`constants.py:1412`) | delegation ceiling on `/key/generate` (`key_management_endpoints.py:2810-2822`); v1.86.0 once used the $0.25 UI-session budget as the generated key's ceiling (#29073, fixed) |
| JWT / OAuth2 / oauth2-proxy | `general_settings.enable_jwt_auth` etc. (`auth/handle_jwt.py`) | mapped roles; JWT `role_permissions.models` doesn't honor wildcards (#27536 open) |
| `"ui-token"` | `SPECIAL_LITELLM_AUTH_TOKEN` (`constants.py:1537`) | special-cased |

## Role → route access

| Role | Gate | Surprises |
|---|---|---|
| `PROXY_ADMIN` | bypasses non-admin route checks | except 3 **master-key-only** routes: `/global/spend/reset`, `/memory-usage-in-mem-cache`, `/memory-usage-in-mem-cache-items` (`_types.py:554-558`) — an admin virtual key gets "only for MASTER KEY" (`user_api_key_auth.py:1637`) |
| `PROXY_ADMIN_VIEW_ONLY` | `route_checks.py:752-859` | **default-allow on ANY GET/HEAD/OPTIONS on any non-inference route** (`:811-812`); writes are blocklist-based. Every newly added GET endpoint is automatically viewer-readable. |
| `INTERNAL_USER` | `internal_user_routes` (`_types.py:711-734`) | includes all key-management routes → an internal user can mint keys |
| `INTERNAL_USER_VIEW_ONLY` | `_types.py:736-745` | spend + compliance + 2 tag routes |
| Org admin | `org_admin_allowed_routes` (`_types.py:867`) | very broad (management + self-managed + viewer unions); yet org admins hit 401 on `/team/update` (#27294 open) and can't add internal users (#30843 open) |
| Team member | `team_member_permissions` (`management_helpers/team_member_permission_checks.py:19-47`) | baseline = `/key/info` + `/key/health` **only**; `[]` still gets baseline unioned in (`:41-45`) |
| Any authenticated key | `self_managed_routes` (`_types.py:747-777`) | includes `/model/new`, `/model/update`, `/model/delete`, `/invitation/new`, `/health/test_connection` — endpoints self-police internally |
| Unauthenticated | `public_routes` (`_types.py:654-671`) + `general_settings.public_routes` | `/routes`, `/config/yaml` (mock), `/`, `/health/{liveness,readiness,drain}`, `/public/*`, `/get/ui_settings`, `/get/ui_theme_settings`, `/onboarding/*` |

**`/v1/mcp/*` and `/mcp-rest/*` bypass central RBAC entirely** (`route_checks.py:308-309`: `pass  # authN/authZ handled by api itself`) — ~25 MCP management handlers each self-police by convention, not enforcement.

## `allowed_routes` on keys — semantics

- `None`, non-list, **and `[]`** all mean unrestricted (`route_checks.py:99-104`). No deny-all value exists.
- **Prefix matching** (`:537-560`): `["/key"]` grants everything under `/key/`.
- Route-**group names** are accepted: any `LiteLLMRoutes` member name resolves (`:114-119`), e.g. `allowed_routes: ["management_routes"]` grants the whole set at `_types.py:581-620`.
- `key_type: "management"` **overwrites** caller-supplied `allowed_routes` with `["management_routes"]` (`key_management_endpoints.py:470-485`).
- `allowed_routes` and `allowed_passthrough_routes` are mutually exclusive — the former silently wins (`:1528`, `:2600`).

## `team_member_permissions` accepted values

The enum is `KeyManagementRoutes` (`_types.py:231-261`) — **18 values**; `docs/proxy/access_control.md:227-240` lists 10. Undocumented-but-valid: `/key/bulk_update`, `/team/key/bulk_update`, `/key/{key_id}/reset_spend`, `/key/aliases`, `/team/daily/activity`, `/spend/logs`, `/spend/logs/v2`, and the pseudo-route `"/key/access_group_assignment"` — not an HTTP route but a field-level opt-in letting non-admin members set `access_group_ids` on keys (`_types.py:249-252`, default-deny).

## Enterprise vs OSS gating — three different failure shapes

1. **Enterprise routers not installed → 404** (`proxy_server.py:671-679` leaves an empty router on ImportError): `/audit`, `/project/*`, `/user/available_users`, `/email/event_settings*`. Note: audit-log *writing* is gated only on `litellm.store_audit_logs` with no premium check (`hooks/key_management_event_hooks.py:57+`) — rows accumulate on OSS with no endpoint to read them.
2. **Premium-gated features inside OSS endpoints → `CommonProxyErrors.not_premium_user` error**: `tags` on a key (`key_management_endpoints.py:957-958`), `/key/regenerate` at all (`:4725-4728`), `permissions: {"get_spend_routes": …}` (`:3801`), access-group-on-wildcard-model (`:3565-3579`), `model_info.team_id` on `/model/new`, `/global/spend/report`, SSO beyond 5 users (`ui_sso.py:861-880`), airgapped `max_users` enforced on `/user/new`. The premium metadata-field list (`_types.py:4075-4085`): `disable_global_guardrails`, `guardrails`, `policies`, `tags`, `team_member_key_duration`, `prompts`, `logging`, `secret_manager_settings`, `allowed_passthrough_routes`. **This is the #15230 trap**: UIs and naive clients round-tripping objects with empty enterprise arrays hit these checks.
3. **Silent no-ops on OSS**: `general_settings.admin_only_routes` logs an error and returns — the route stays open (`route_checks.py:333-338`); `general_settings.public_routes` same pattern (`auth_utils.py:566`). Configuring these on OSS gives the opposite of the intended security posture, silently.
4. `DISABLE_ADMIN_ENDPOINTS` / `DISABLE_LLM_API_ENDPOINTS` (enterprise `route_checks.py:26-42`) raise **HTTP 500** with an emoji-prefixed body, and cover only `LiteLLMRoutes.management_routes` (51 paths: `/key/*`, `/user/*`, `/team/*` core, `/model/*` core). Still reachable with the flag on: `/organization/*`, `/customer/*`, `/end_user/*`, `/budget/*`, `/credentials*`, `/config/*` (incl. `POST /config/update`), `/guardrails/*`, `/policies/*`, `/policy/*`, `/tag/*`, `/access_group/*`, `/invitation/*`, `/router/settings`, `/team/member_*`, `/model/block|unblock`, `PATCH /model/{id}/update`, `/reload/*`, `/spend/*`, `/global/spend/*`. `docs/proxy/multi_region.md:169` overstates it as management isolation.

## #34241 (open): the MIT/Enterprise boundary itself is undocumented — when an operation fails with an enterprise error on OSS, check group 2 above before assuming misconfiguration.
