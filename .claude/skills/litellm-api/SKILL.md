---
name: litellm-api
description: |-
  Administer a LiteLLM proxy via its management REST API (keys, teams, users, orgs, models, budgets, spend) — a 447-path control plane where ~63% of paths are undocumented, 91 are hidden from /openapi.json, and the OpenAPI schema documents wrong field names. Centerpiece: four "empty means UNLIMITED" footguns (`models: []`, `allowed_routes: []`, additive access groups, team-member `[]`) where the natural reading is the opposite. Covers the real auth model (no-master-key = fully open, admin-viewer default-allow on GETs, /v1/mcp/* RBAC bypass), budget semantics (can't unset, update≠reset, team spend hits personal budgets since ~v1.94), presence-sensitive updates that trigger spurious enterprise 403s, config-vs-DB precedence, and lazy-loaded families that 404 until warmed.
when_to_use: |-
  Trigger on "litellm api", "litellm management api", "/key/generate", "/team/new", "/user/new", "litellm virtual key", "litellm budget", "max_budget", "budget_duration", "litellm spend", "model access group", "no-default-models", "team_member_permissions", "STORE_MODEL_IN_DB", "litellm openapi", "litellm enterprise 403", "allowed_routes", or any task scripting a LiteLLM proxy (provision keys/teams/users, reconcile models, read usage) rather than clicking the Admin UI. Also on symptoms: "key can access everything", "budget never resets", "update returns 200 but nothing changed", "deleted team's keys still work". NOT for the inference endpoints (chat-completions-api / messages-api / responses-api) or Redis/multi-pod coordination (litellm-valkey).
---

# LiteLLM proxy management API — operator reference

Target: operators scripting a LiteLLM proxy's control plane — key/team/user/org lifecycle, model management, budgets, spend — instead of clicking the Admin UI. Grounded in source @ `4d543245` (v1.95.0-dev, 2026-07-29; latest stable v1.94.0) + docs corpus + issue-tracker sweep of 2026-07-30. LiteLLM releases weekly; treat claims as version-stamped and re-verify on the deployed tag.

Siblings: multi-pod Redis/Valkey coordination is **`litellm-valkey`**; the inference protocols are `chat-completions-api` / `messages-api` / `responses-api`. BerriAI's official `litellm-skills` repo (add-key, add-team, …) is a set of thin curl templates — several of which emit exactly the dangerous values documented here (`"models": []`); treat them as UI sugar, not as a semantics reference.

**Neither the docs nor `/openapi.json` is ground truth.** Measured: 746 route decorators, 624 unique paths, 447 non-inference; **225 of 359 management paths appear nowhere in the docs**; **91 endpoints set `include_in_schema=False`** (all of `/config/*`, `/global/spend/*`, `/invitation/*`, `/sso/*`, most `/customer/*` …); the OpenAPI schema for `budget_limits` documents field names the API rejects (#32695). The only complete live inventory is **`GET /routes`** — which is unauthenticated (it's in `public_routes`, so its auth dependency short-circuits).

## Recon-first protocol (before scripting anything)

```bash
B=https://proxy.example.com; K=sk-...
curl -s $B/routes | jq '.routes | length'            # full inventory, no auth needed
curl -s -H "Authorization: Bearer $K" $B/key/info | jq '.info | {key_alias, user_id, team_id, models}'  # own key (omitted ?key= = self); response is {"key", "info"}
curl -s -H "Authorization: Bearer $K" $B/health/readiness | jq '{status, litellm_version, db}'
```

Then remember three structural facts about the surface:

1. **Lazy loading**: 34 feature families (`guardrails`, `policies`, `vector_store*`, `mcp_management`, `scim`, `tag`, `access_groups`, …) register routes on first matching request. Import failure = **permanent 404 until restart** (logged as a warning only). `POST /lazy/warm/{name}` force-loads (undocumented, hidden from schema).
2. **Enterprise gating is inconsistent**: enterprise-only routers that aren't installed **404** (not 402): `/audit`, `/project/*`, `/user/available_users`, `/email/event_settings*`. Premium-gated *features* inside OSS endpoints raise the "LiteLLM Enterprise" error — see the 403 trap below. `DISABLE_ADMIN_ENDPOINTS` blocks only 51 of ~315 admin paths (`/organization/*`, `/customer/*`, `/budget/*`, `/config/*`, `/guardrails/*` etc. all stay reachable) and returns **500**, not 403.
3. **No master key set = the entire management API is open**: any request is treated as `INTERNAL_USER` and `common_checks` is skipped entirely (`user_api_key_auth.py:1406-1417`, `:2160-2165`). No doc page states this.

## The dangerous-defaults table (memorize)

| Field | Empty/omitted means | The safe deny value |
|---|---|---|
| `models` on key/team/user | **ALL models** (`auth_checks.py:2948-2951`; default is `[]`) | `["no-default-models"]` — hard deny (but see its sharp edges in `references/access-model.md`) |
| `allowed_routes` on a key | **ALL routes** — `None`, non-list, and `[]` all pass (`route_checks.py:99-104`); no deny-all exists | scope to named route groups (any `LiteLLMRoutes` enum name is accepted, e.g. `["management_routes"]`) — and it's **prefix-matched**: `"/key"` grants `/key/delete` |
| `access_group_ids` + empty `models` | access groups are **additive grants, not allow-lists** → key can call **everything** (open #34296) | set `models: ["no-default-models"]` alongside the groups |
| `team_member_permissions: []` | baseline permissions still union in (`/key/info`, `/key/health`) — `[]` ≠ deny | there is no full-deny; baseline is the floor |
| `mcp_servers` empty | all servers | `["no-mcp-servers"]` (documented, `docs/mcp_control.md:100`) |

Also: `litellm.default_key_generate_params` silently replaces `None`/`[]`/`{}` request values on `/key/generate` — on a proxy with defaults configured, `"models": []` yields the default list, not all-models. Same request, different proxy, different meaning.

## Budget semantics — the minefield

Full detail in `references/budgets-spend.md`. The load-bearing rules:

- **Budgets can't be cleanly unset**: `budget_limits: []` is silently ignored (200, no-op), `null` → 400, omission ignored (open #28021; `null`-clear family #27734). `max_budget`+`budget_duration` and `budget_limits` (concurrent windows) are two separate mechanisms.
- **Adding `budget_duration` to an existing entity via update does NOT reset carried spend** — the entity 429s instantly on its "fresh" window (open #34492). Pre-zero spend explicitly (`/key/{key}/reset_spend`, enterprise-gated regenerate not required) or create anew.
- **Team-key spend counts against members' personal budgets by default since ~v1.94** (maintainer-confirmed intentional, #26239) — and the opt-out `skip_user_budget_on_team_key` is broken (open #35076).
- **Boundary inconsistency**: team check uses `>`, key/org use `>=` (`_team_max_budget_check`, open #28020) — budgets admit at exact limit for some entity types (#33321).
- **Resets historically skip entity types**: org budgets never reset (#25495, stale-closed unfixed), tag budgets (#27481 open), auto-created end-users (#24675/#25386 open). `soft_budget` only alerts, never blocks; on `/team/new` it must be strictly < `max_budget` or 400.
- **Never send `max_budget_in_team: null` on `/team/member_update`** — it leaves a null budget row that 401s every subsequent request from the whole team's members (open #29066/#30437). Member-budget edits are clone-on-write from the team default; per-member budget rows auto-disconnect when no meaningful limit remains.
- **Spend numbers are eventually consistent in both directions**: enforcement can 429 on stale-high spend while `/key/info` shows under-budget (#27735), or admit despite over-budget (#26672). Spend-log writes are silently lost on DB failure/shutdown/GC races (#33873/#34820/#34805/#31059). Rate limits and budgets across scopes are **AND-composition** — every applicable scope (key, team, member, user, org, customer, tag, model-within-key) enforces independently; effective limit = the minimum; a 429/BudgetExceeded doesn't say which scope tripped.

## Update calls: minimal-diff PATCH bodies only

The single most recurrent bug class (≥8 versions of duplicates): update endpoints are **presence-sensitive, not diff-sensitive**. Round-tripping a full object — as the Admin UI does — breaks:

- Including enterprise-only fields (`guardrails`, `policies`, `tags`, …) **even as empty arrays** triggers "This feature is only available for LiteLLM Enterprise users" 403s (#15230 open since 2025-10 with 38 comments; closed dupes #11552 #14934 #20304 #20476 #20534 #21037 #21570 #22201 #30285). Workaround: **omit every field not being deliberately changed**.
- Non-admin `/key/update` 403s if the body merely *includes* `allowed_routes` or `permissions` — presence-checked, not change-checked (v1.92.0 regression, open #33277; dashboard's `budget_limits: []` variant #33246).
- `key_type: "management"` silently **overwrites** any caller-supplied `allowed_routes` (`key_management_endpoints.py:470-485`).
- Unknown fields are **silently dropped** (`extra="ignore"`) on every management model except `PATCH /v2/organization/{id}` (`extra="forbid"` → 422) — a typo'd field name is a 200 that did nothing. Verify with a follow-up GET, not the status code.
- Verb/semantics are inconsistent per family (POST-merge vs RFC-7386 PATCH where `null` deletes vs raw-json PATCH; `page`+`size` vs `page`+`page_size` vs unpaginated) — per-family cheatsheet in `references/endpoint-map.md`.

## Config-vs-DB duality (`STORE_MODEL_IN_DB`)

With it on, DB rows deep-merge **over** YAML for `general_settings`/`router_settings`/`litellm_settings` (DB wins; DB `None`/`[]` treated as no-value) — editing YAML and restarting won't change a UI-written key. `POST /model/new` can return 200 with `db_model: false` meaning **the write was skipped** (open #30771); a stale DB row `store_model_in_db: false` overrides the env var (open #31968); config-YAML models can't be edited via API at all ("Cannot edit config-based model"); with the flag off, model-management endpoints return **500** (not 400). There is no export of UI/DB state back to declarative config (#28168). `GET /config/yaml` is a **mock** returning `{"hello": "world"}` — and it's a public route. Details: `references/config-db.md`.

## Destructive ops don't propagate

`/team/delete` leaves the team's virtual keys **auth-valid in cache** until TTL (open #34217); customer mutations don't invalidate Redis end-user counters (#31838/#31839). After any destructive op, verify with a live auth attempt, not the 200. `/team/member_add` is a read-modify-write race — serialize concurrent membership calls (open #25951).

## Task → reference routing

| Task | Read |
|---|---|
| Find an endpoint, verb/pagination/identifier quirks, hidden + lazy families | `references/endpoint-map.md` |
| Roles, route groups, who-can-what, no-master-key mode, enterprise/OSS gating | `references/auth-model.md` |
| Key/model access semantics: sentinels, access groups, wildcards, `/v1/models` lies | `references/access-model.md` |
| Budgets, spend tracking, rate-limit scope composition | `references/budgets-spend.md` |
| STORE_MODEL_IN_DB, config precedence, `/config/*` surface | `references/config-db.md` |
| "Is this a known bug on my version?" | `references/known-issues.md` |
| Verify a claim / freshen | `references/sources.md` |

### Scripts

- **`${CLAUDE_SKILL_DIR}/scripts/litellm-key-audit.sh <base-url> <admin-key>`** — lists keys whose effective model access is "everything" (empty `models` without team inheritance, or access-groups-with-empty-models — the pattern #34296 makes dangerous). Fields verified against `LiteLLM_VerificationToken` in schema.prisma; execution-tested against a mock `/key/list`.

## Gotchas that cost hours

- `/v1/models` **is not an access-policy oracle**: it never resolves `access_group_ids` (#31966 cluster), ignores user-level restrictions (#26420), and can show the literal string `no-default-models` as a model. Don't verify access policy by listing models; verify with a live completion attempt.
- Key identifiers differ per endpoint: `/key/info?key=` takes plaintext or hash (omitted = the caller's own key); `/key/delete` takes `keys` or `key_aliases` (never both); regenerate/reset_spend take the key **in the path**; `/key/list` filter `key_hash=` is hash-only, and its `size` caps at 100.
- `/user/new` **auto-creates and returns a live key** unless `auto_create_key: false`; a keyless request with a `models`-bearing user record makes later empty-`models` keys inherit the user's list.
- The three master-key-only routes (`/global/spend/reset`, 2 memory-usage routes) reject even proxy-admin virtual keys with a confusing error.
- `metadata.service_account_id` is immutable once set and requires `team_id`. `allowed_routes` and `allowed_passthrough_routes` are mutually exclusive (the former wins silently).
- `/spend/logs` is deprecated in favor of `/spend/logs/v2` — but it's the one the docs still show. `spend_logs_metadata` on an **organization** is silently ignored (only key/team merge, #33663). `store_prompts_in_spend_logs: true` can still persist `messages` as `{}` (#34747) while `false` still stores full embedding vectors (#24928). When docs and behavior disagree, behavior wins — test against the live proxy (tracker-health caveats: `references/known-issues.md`).
