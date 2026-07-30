# Endpoint map — families, files, quirks

Measured @ `4d543245` (v1.95.0-dev, 2026-07-29): 746 route decorators, 624 unique paths, 447 non-inference, 91 with `include_in_schema=False`, ~315 admin-ish of which `DISABLE_ADMIN_ENDPOINTS` covers 51. `GET /routes` (unauthenticated — in `public_routes`, auth dependency short-circuits at `user_api_key_auth.py:1162-1167`) is the only complete live inventory.

## Family → file table

| Family | Primary file | Quirks |
|---|---|---|
| `/key/*` (14) | `management_endpoints/key_management_endpoints.py` (6600+ lines) | also hosts `/credentials/migrate-encryption*` (`:4357`, `:4397`) and `/team/key/bulk_update` (`:2954`) |
| `/team/*` (24) | `management_endpoints/team_endpoints.py` | `PATCH /team/{id}` is RFC 7386 (metadata deep-merge, `key: null` deletes, `:1970-1978`); `/team/{team_id}/members/me`, `/team/{team_id:path}/callback` mix path styles |
| `/user/*` (11) | `management_endpoints/internal_user_endpoints.py` | `/user/available_users` is enterprise-package-only |
| `/customer/*` + `/end_user/*` (16) | `management_endpoints/customer_endpoints.py` | two full aliased sets of the same 8 handlers |
| `/organization/*` (9) + `/v2/organization/{organization_id}` | `management_endpoints/organization_endpoints.py` | `/organization/update` is PATCH over raw `request.json()` (untyped, `:609-641`); `/v2` PATCH is the only `extra="forbid"` model (typos 422 instead of silent no-op, `_types.py:2820-2830`); delete is DELETE-with-body |
| `/model/*`, `/model_group/*`, `/model_hub/*` | `management_endpoints/model_management_endpoints.py` + `proxy_server.py:12095-13281` | `/model/info`, `/v2/model/info`, `/model/metrics*`, `/model/settings` live in proxy_server.py |
| `/budget/*` (6) | `management_endpoints/budget_management_endpoints.py` | undocumented as a family |
| `/spend/*` (9), `/global/*` (18) | `spend_tracking/spend_management_endpoints.py` (3300+ lines) | ALL `/global/*` hidden from schema; `/spend/logs` deprecated for `/spend/logs/v2` (`:2264-2265`) but docs still show v1 |
| `/config/*` (13) | `proxy_server.py:14540-15668` + pass_through + cost_tracking_settings | ALL hidden from schema; `GET /config/yaml` is a mock returning `{"hello":"world"}` (`proxy_server.py:15690`) **and** a public route |
| `/credentials/*` (6) | `credential_endpoints/endpoints.py` | |
| `/guardrails/*` (18) | `guardrails/guardrail_endpoints.py` | `GET /guardrails/list` reads config-file only; `GET /v2/guardrails/list` merges config+DB (`:125-137`); `/guardrails/{id}` registers PUT and PATCH and GET and DELETE |
| `/policies/*` (15) vs `/policy/*` (9) | **two different subsystems** (`policy_engine/` vs `management_endpoints/policy_endpoints/`) | lazy-load prefixes disambiguated by trailing slash (`_lazy_features.py:68-69`) |
| MCP mgmt (~25) | `management_endpoints/mcp_management_endpoints.py` | router prefix `/v1/mcp` (`:71`); whole prefix **bypasses central RBAC** (`route_checks.py:308-309`) — per-handler self-policing |
| `/access_group/*` (5) | `model_access_group_management_endpoints.py` | undocumented family |
| `/tag/*` (12) | `tag_management_endpoints.py` + user_agent_analytics | |
| `/scim/v2/*` (19) | `management_endpoints/scim/scim_v2.py` | lazy-loaded |
| `/sso/*`, `/login`, `/v2/login`, `/v3/login(+/exchange)` | `ui_sso.py` (4400 lines), proxy_server.py | all `/sso/*` hidden from schema |
| `/audit`, `/project/*`, `/email/event_settings*` | enterprise package only | **404** (not 402) when `litellm_enterprise` isn't importable (`proxy_server.py:671-679`) |
| `/get/*`, `/update/*`, `/delete/allowed_ip` | `ui_crud_endpoints/proxy_setting_endpoints.py` | `GET /get/ui_settings`, `/get/ui_theme_settings` are **unauthenticated** |
| `/cloudzero/*`, `/vantage/*` | `spend_tracking/{cloudzero,vantage}_endpoints.py` | lazy-loaded |
| `/health*` (13) | `health_endpoints/_health_endpoints.py` | `/health/readiness`, `/health/drain` unauthenticated |
| `/management/v1/spend_logs/end_users` | `management_v1/spend_logs.py` | the ONLY route on the new `/management/v1` prefix; RFC 7807 problem+json errors, 400 on validation (vs 422 `{"detail":[...]}` everywhere else, `proxy_server.py:1458-1476`) |
| `/coordination_redis/settings*` | `coordination_redis_endpoints.py` | see litellm-valkey skill |

## Hidden from `/openapi.json` (91 total, `include_in_schema=False`)

Every `/global/spend/*` + `/global/activity/*`, every `/config/*`, every `/invitation/*`, every `/sso/*`, `/customer/{info,list,update,delete,daily/activity}`, `/end_user/{new,block,unblock}`, `/v2/key/info`, `PATCH /v2/organization/{id}`, `/model/metrics*`, `/model/settings`, `/model/cost_map/source`, `/schedule/*`, `/reload/*`, `/spend/{keys,users,logs/v2,logs/ui,logs/session/ui}`, `/team/filter/ui`, `/user/{filter/ui,available_roles}`, `/alerting/settings`, `/get/config/callbacks`, `/onboarding/*`, `/debug/memory/*`, `/lazy/warm/{name}`.

Additional spec distortions: `DOCS_FILTERED=True` + premium license reduces the whole spec to inference routes (`proxy_server.py:1357-1393`); lazy features get fake `GET <prefix>` placeholders unless a snapshot file exists (`_lazy_features.py:409-430`); `operationId`s are machine-rewritten and unstable across versions; Swagger UI can be off entirely (`NO_DOCS`).

## Lazy loading (34 families)

`litellm/proxy/_lazy_features.py` (`LAZY_FEATURES`, `:54-256`): guardrails, policies, policy_engine, vector_store_management (implemented **twice** — OSS + enterprise dirs), tools, search_tools, mcp_management, config_overrides, scim, cloudzero, vantage, prompts, jwt_mappings, compliance, access_groups, tag, …

- Routes register on the **first request matching a string prefix**; prefix matching is `SERVER_ROOT_PATH`-sensitive (`:301-302`) — a root-path mismatch means the whole family 404s forever.
- **Import failure = permanent 404 until restart**, logged as a warning only (`:336-344`).
- `POST /lazy/warm/{name}` force-loads (`:366`). Recon tip: after warming, re-fetch `/routes` — the inventory grows.

## Per-endpoint identifier + pagination quirks

| Endpoint | Identifier | Pagination |
|---|---|---|
| `GET /key/info?key=` | plaintext **or** hash; omitted = caller's own key (`key_management_endpoints.py:3500-3502`) | — |
| `POST /key/delete` | `keys: []` (plaintext or hash) **or** `key_aliases: []`, never both; partial failure = one 400 with a count mismatch, no per-key results (`:3255-3295`) | — |
| `POST /key/{key:path}/regenerate`, `/key/{key:path}/reset_spend` | key **in path** (`:4602`, `:4945`); RBAC enum records them as `{key_id}` — naming mismatch (`_types.py:242,247`) | — |
| `GET /key/list` | `key_hash=` (hash only) / `key_alias=` | `page` + `size`, **max 100** (`:5241-5242`) — bites the UI itself (#30984); team-visibility filters are OR'd not AND'd (#32062) |
| `/v2/team/list`, `/user/list`, `/audit` | | `page` + `page_size` |
| `/spend/logs/v2`, `/spend/logs/session/ui` | | `page` + `page_size` (default 50, max **1000**) |
| `/team/list`, `/organization/list`, `/budget/list`, `/customer/list`, `/tag/list` | | **unpaginated** |
| `GET /key/aliases` | | undocumented (`:5454`) |

## Update semantics per family

| Op | Verb | Semantics |
|---|---|---|
| `/key/update`, `/team/update` | POST | `exclude_unset=True` merge — omitted fields untouched (`key_management_endpoints.py:1887`) |
| `PATCH /team/{team_id}` | PATCH | RFC 7386: `metadata` deep-merged, `key: null` deletes |
| `/organization/update` | PATCH | raw `request.json()`, no typed body |
| `PATCH /v2/organization/{id}` | PATCH | typed, `extra="forbid"`, per-field clear tokens (`null` budgets/metadata, `[]` models) |
| `/model/update` | POST | requires `STORE_MODEL_IN_DB`; 500 (not 400) when off |
| `PATCH /model/{model_id}/update` | PATCH | rejects config-YAML models |
| `/user/delete`, `/team/delete`, `/key/delete` | POST | |
| `/organization/delete` | DELETE with body | |
| `/key/health` | **POST** | |

## Usage-read recipe (`/spend/logs/v2`, verified params @ `spend_management_endpoints.py:1595+`)

Accepted filters: `api_key`, `user_id`, `request_id`, `session_id`, `team_id`, `min_spend`, `max_spend`, `start_date`, `end_date`, `status_filter`, `model`, `model_id`, `model_group`, `key_alias`, `end_user`, `error_code`, `error_message`, `sort_by`, `sort_order`, plus `page`/`page_size`.

```bash
curl -sG -H "Authorization: Bearer $K" "$B/spend/logs/v2" \
  --data-urlencode "team_id=my-team" --data-urlencode "start_date=2026-07-01" \
  --data-urlencode "end_date=2026-07-30" --data-urlencode "page_size=1000" \
  | jq '{total: .total_count, spend: [.data[]?.spend] | add}'
```

Reconcile spend against this + the DB, never against enforcement counters (see `budgets-spend.md` — counters disagree in both directions).

Deprecated-but-accepted params that still 200: `config`/`team_id` on `/user/new`, `admins`/`users` on `/team/new`, `duration: "-1"` on `/key/update`. Documented-as-ignored (`[Not Implemented Yet]`, stored, never enforced): `blocked`/`guardrails`/`permissions` on `/user/*`; `tpm_limit`/`rpm_limit`/`model_max_budget`/`max_parallel_requests`/`soft_budget` on `/customer/new`; `max_parallel_requests`/`soft_budget` on `/organization/new`; `mcp_rpm_limit`/`tag_rpm_limit` per user.
