---
name: open-webui-api
description: |-
  Administer Open WebUI entirely via its REST API (v0.10.x): user/group lifecycle, permissions, model catalog GitOps (export/import/sync), knowledge/RAG pipelines, config-as-code, SCIM provisioning, event webhooks, and backup surfaces. Grounded in the v0.10.2 source — covers the 458-path surface the official docs leave ~96% undocumented, the auth bootstrapping traps (ENABLE_API_KEYS default-off, JWT 4-week expiry, one unscoped key per user), and the 0.10.0 breaking changes (access_control→access_grants with inverted public/private defaults, flat dot-keyed config) that silently break every pre-0.10 script and most LLM training-data knowledge.
when_to_use: |-
  Trigger on "open-webui api", "openwebui rest", "open-webui automation", "provision open-webui users", "open-webui api key", "access_grants", "access_control open-webui", "models/sync", "open-webui config export", "configs/import", "PersistentConfig", "open-webui scim", "custom_params", "chat_template_kwargs open-webui", "open-webui webhook events", "/api/v1/", "api_type responses", or any task scripting/automating an Open WebUI instance (create users, manage groups, sync model catalog, upload knowledge, read analytics) rather than clicking the UI. Also trigger on symptoms: "API returns HTML", "403 with valid API key", "env var change ignored", "custom parameter shows [object Object]", "reasoning missing from API response". NOT for Open WebUI RAG/embedding wiring (open-webui-embeddings), multi-pod scaling (open-webui-valkey-websocket), or generic OpenAI-API client questions.
---

# Open WebUI REST API administration — operator reference

Target: operators who script Open WebUI (create users, reconcile model catalogs, drive RAG pipelines, export configs) instead of clicking the admin UI. Grounded in v0.10.2 source (2026-07-01); the API is officially "experimental" with no versioning policy, so every claim here is version-stamped. **First step on any instance: `GET /api/version`** — never trust `openapi.json`'s `info.version` (always says "0.1.0").

## The API in 30 seconds

Four surfaces, one Bearer header (`Authorization: Bearer <jwt-or-api-key>`):

| Surface | What lives there | Examples |
|---|---|---|
| `/api/v1/*` | Resource CRUD — 26 routers (+2 feature-gated) | users, groups, auths, configs, models, knowledge, files, retrieval, tools, functions, prompts, chats, evaluations |
| `/api/*` | Runtime endpoints in main.py | `chat/completions`, `models`, `config`, `version`, `events` (webhooks), `tasks`, `usage` |
| `/ollama/*`, `/openai/*` | Authenticated proxies to backends | inference = user-level; model lifecycle + config = admin |
| `/ws` | socket.io | invisible to openapi.json |

Conditional mounts (404 when off): `/api/v1/scim/v2` needs `ENABLE_SCIM=true` (+restart), `/api/v1/analytics` needs `ENABLE_ADMIN_ANALYTICS` (default on).

Preflight before any scripted work (`$B` = base URL, `$T` = token):

```bash
curl -s $B/api/version | jq -e .version          # real version; jq failing = HTML came back (SPA trap — check the path)
curl -s -H "Authorization: Bearer $T" $B/api/v1/auths/ | jq -e .role   # expect "admin" for admin endpoints; 401 = key disabled/expired
```

For multi-call scripts, source `scripts/owui-curl.sh` (live-tested): `owui <METHOD> <path> [json]` wraps every call with the HTTP-2xx and JSON-content-type checks (the HTML-200 trap detector), and `owui_preflight [role]` runs the probes above.

Full endpoint inventory with per-route auth levels: `references/endpoint-map.md`.

## Auth — the trap zone (read before first request)

1. **API keys are off by default** since 0.6.37: `ENABLE_API_KEYS=true` required (the old `ENABLE_API_KEY` name is **silently ignored** — no fallback), plus admin role or `features.api_keys` permission (also default false). One unnamed, non-expiring `sk-` key per user; regenerate replaces it. Keys inherit the owner's full power — an admin's key can do everything, no scoping. Best practice: dedicated non-admin service accounts + `API_KEYS_ALLOWED_ENDPOINTS` allowlist (warning: restrictions on + empty list = keys can reach *nothing*).
2. **JWTs expire after 4 weeks** by default since 0.6.34 (was: never). Long-lived automation on a captured session token dies silently mid-quarter. Signout only revokes JWTs when Redis is present.
3. **Headless bootstrap**: `WEBUI_ADMIN_EMAIL` + `WEBUI_ADMIN_PASSWORD` create the first admin at startup; or the first signup auto-promotes to admin and disables signup.
4. SCIM is a separate universe: static `SCIM_TOKEN` bearer, not a JWT/API key.
5. Behind proxies that eat `Authorization`: send the key in `x-api-key` (`CUSTOM_API_KEY_HEADER`).

## The 0.10.0 break — unlearn the old shapes

Everything the community (and LLM training data) teaches about two core shapes died in 0.10.0 (2026-06-29). Old payloads are **silently ignored** (pydantic `extra='ignore'`) — scripts appear to succeed while doing nothing:

| Concept | Dead (≤0.9.x) | Current (0.10.x) |
|---|---|---|
| Resource ACLs | `access_control: {read:{group_ids,user_ids},...}`, `null`=public, `{}`=private | `access_grants: [{principal_type:"user"\|"group", principal_id:"<id>"\|"*", permission:"read"\|"write"}]` — **absent = private; public needs explicit `user:*` read grant** |
| Config export | one nested JSON blob | flat dot-keyed dict (`{"ui.default_models": ...}`); import = partial upsert |

Full ledger 0.6.19→0.10.2 with dates and issue numbers: `references/breaking-changes.md`.

## Task → reference routing

| Task | Read |
|---|---|
| Find an endpoint, check required role | `references/endpoint-map.md` |
| User/group lifecycle, model GitOps (`models/sync`), knowledge upload pipeline, backups | `references/admin-workflows.md` (verified curl sequences) |
| Config-as-code, PersistentConfig precedence, connections, per-model request params | `references/config-system.md` |
| "Worked before upgrade, broken now" | `references/breaking-changes.md` |
| IdP provisioning (SCIM), audit/event webhooks | `references/events-scim.md` |
| Verify a claim / freshen | `references/sources.md` |

## Gotchas that cost hours (all verified in v0.10.2 source or live)

- **HTML-200 trap**: the SPA catch-all serves `index.html` with HTTP 200 for any unknown path. A typo'd endpoint "succeeds" with HTML. Always check `Content-Type: application/json`.
- **`/docs` and `/openapi.json` need `ENV=dev`** — the Docker image ships `ENV=prod`, so production instances return the SPA for both. Flipping to `dev` also skips the prod-only default `OLLAMA_BASE_URL` Docker rewrite — safe on external-connection setups, breaking on default-Ollama containers.
- **PersistentConfig**: env vars seed the DB on first boot only; thereafter the DB value wins and env changes are silently ignored (`ENABLE_PERSISTENT_CONFIG=true` default). Exception: `oauth.*` stays env-driven unless `ENABLE_OAUTH_PERSISTENT_CONFIG=true`. Change runtime config via the API, not the deployment env.
- **Connection `api_type: "responses"` changes the whole wire contract**: Open WebUI converts requests to the Responses API. vLLM-recipe knobs like `chat_template_kwargs` get dropped by the upstream (LiteLLM `/v1/responses` drops them); use the Responses-native `reasoning: {"effort": ...}` param instead. Also: `convert_responses_result()` discards reasoning items for **non-streaming** API callers — test reasoning with `stream: true`.
- **`custom_params` values must be JSON strings**, not nested objects: `{"custom_params": {"reasoning": "{\"effort\": \"medium\"}"}}`. The backend `json.loads`es strings; raw dicts work on the wire but render as `[object Object]` in the UI editor and get corrupted on UI save.
- **`POST /api/v1/models/model/update` can 500** (observed live on 0.10.2); workaround: `model/delete` + `create`.
- **Pagination is inconsistent**: `/api/v1/users/` is hard-capped 30/page (no limit param); `GET /api/v1/chats/` **without `page` returns everything unbounded**.
- **Workspace-model list**: use `GET /api/v1/models/list` — bare `/api/v1/models` is the OpenAI-compat alias (collision, renamed 0.6.35).
- No general rate limiting (only signin: 15/3min/email). `CORS_ALLOW_ORIGIN` defaults `*`.
- Filter `outlet()` hooks run on direct API calls (streaming included) **since 0.10.0, on by default** — API response bodies can be rewritten by installed filter functions.

## Debugging pattern that works

When a parameter "doesn't arrive" at the backend, bisect the chain with an error probe: send the parameter with an **invalid type** (e.g. a string where a dict belongs) at each hop — direct to the upstream, then through Open WebUI. A hop that errors is forwarding; a hop that succeeds silently is dropping. This located a LiteLLM Responses-path drop in two requests that log-reading could not have found.
