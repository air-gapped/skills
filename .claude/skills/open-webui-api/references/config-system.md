# Config system — dot-keys, PersistentConfig, connections, params (v0.10.2)

## Storage model

Since 0.10.0 config is per-key rows (`config` table: key TEXT PK, value JSON), dot-namespaced: `ui.default_models`, `openai.api_base_urls`, `auth.enable_api_keys`, `ldap.enable`, `rag.template`, … No published key registry — the authoritative list is a live `GET /api/v1/configs/export`, or `config.py`'s `ConfigVar(...)` declarations in source.

```bash
curl $B/api/v1/configs/export -H "Authorization: Bearer $T" > config-backup.json   # ALL keys, flat
curl -X POST $B/api/v1/configs/import -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"config": {"ui.default_models": "litellm.gemma4-31b"}}'                      # PARTIAL upsert — only supplied keys
curl $B/api/v1/configs/namespace/ui -H "Authorization: Bearer $T"                   # one subtree
```

A ≤0.9.x export (nested blob) cannot be imported into 0.10.x — no translation layer.

## PersistentConfig precedence (the #1 "env var ignored" mystery)

- Env vars only populate defaults; at first boot every key is seeded into the DB. **From then on the DB wins and env changes are silently ignored** (`ENABLE_PERSISTENT_CONFIG=true`, the default).
- `ENABLE_PERSISTENT_CONFIG=false` inverts it: env always wins, API config writes only mutate in-memory state (lost on restart).
- Exception: `oauth.*` keys are env-driven unless `ENABLE_OAUTH_PERSISTENT_CONFIG=true`.
- Not ConfigVars at all (env-only, restart to change): `WEBUI_SECRET_KEY`, `ENABLE_SCIM`/`SCIM_TOKEN`, `ENABLE_PASSWORD_AUTH`, `AUDIT_LOG_*`, `ENABLE_ADMIN_EXPORT`, `ENABLE_ADMIN_CHAT_ACCESS`, `CUSTOM_API_KEY_HEADER`, DB/Redis URLs.
- Known 0.10.0-refactor regressions (rule these out when a config write appears not to apply): #27061 (web-loader reads frozen env, OPEN), #26761 (boolean DB values ignored), #24743 (connections lost after restart), #24346 (stale Redis overwrites imports).

Operational rule: manage runtime config via API (`configs/import` in CI), reserve env for bootstrap + the env-only list.

## Provider connections

```bash
# OpenAI-type connections (arrays are index-aligned; configs keyed by STRINGIFIED index)
curl -X POST $B/openai/config/update -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{
  "ENABLE_OPENAI_API": true,
  "OPENAI_API_BASE_URLS": ["http://litellm.litellm.svc.cluster.local:4000/v1"],
  "OPENAI_API_KEYS": ["sk-..."],
  "OPENAI_API_CONFIGS": {"0": {"enable": true, "prefix_id": "litellm", "model_ids": [], "connection_type": "external", "api_type": "responses"}}}'
# Ollama variant: POST /ollama/config/update  {ENABLE_OLLAMA_API, OLLAMA_BASE_URLS, OLLAMA_API_CONFIGS}  (no keys array)
```

Per-connection config fields: `model_ids` (allowlist; empty = all), `prefix_id` (namespaces ids as `<prefix>.<model>`; stripped before proxying upstream), `connection_type`, `api_type` (`"responses"` switches the whole upstream leg to the Responses API — see below), `tags`, `auth_type`, `azure`+`api_version`.

Admin can read keys back via `GET /openai/config` — useful for debugging the upstream directly.

Tool servers (OpenAPI + MCP): `GET|POST /api/v1/configs/tool_servers` — entries `{url, path, type:'openapi'|'mcp', auth_type, headers, key, config, info}`; validate with `/api/v1/configs/tool_servers/verify` before saving (a dead server can hang the UI and crash-loop workers — #22543, #24330).

### Forwarding user identity upstream (per-user attribution)

Open WebUI has **no native per-user rate limiting or quota** (only sign-in is throttled) — to attribute or cap usage per user, forward the authenticated identity to the upstream gateway and enforce there. `ENABLE_FORWARD_USER_INFO_HEADERS=True` (env) makes OWUI add `X-OpenWebUI-User-{Name,Id,Email,Role}` to every upstream call on the proxy paths (`openai`, `ollama`, anthropic, audio, images, tools, retrieval — `routers/openai.py:include_user_info_headers`); the chat path additionally sends `X-OpenWebUI-Chat-Id` when a chat is bound. Header names are overridable (`FORWARD_USER_INFO_HEADER_USER_*` in `env.py`). Note `user.id` is an OWUI-internal uuid4 (**not** the OIDC `sub`), so prefer the `…-Email` header for human-legible downstream records.

The upstream then reads that header as the request's end-user. Example — LiteLLM picks it up with one setting:

```yaml
# litellm proxy config.yaml — general_settings
general_settings:
  user_header_name: "X-OpenWebUI-User-Email"   # header value becomes end_user in spend logs + Customers
```

**`user_header_name` is deprecated** (marked so in `litellm/proxy/_types.py` as of 2026-07, still functional). The replacement is `user_header_mappings`, which also supports multiple headers:

```yaml
general_settings:
  user_header_mappings:
    - header_name: "X-OpenWebUI-User-Email"
      litellm_user_role: customer   # customer = same end_user field as user_header_name; first present header wins
```

Both paths converge on the same `end_user_id` (`auth_utils.py:get_end_user_id_from_request_body` checks customer mappings first, then falls back to `user_header_name`), so spend logs / Customers look identical after switching. Use `litellm_user_role: customer`, NOT `internal_user` — the latter writes `user_api_key_dict.user_id` (the internal-user column) instead of `end_user`. Historical caveat: LiteLLM #12893/#14667 reported the mappings path broken with OWUI on older versions (source-verified working on post-v1.92.1 main; see the traefik-hardening skill's ledger) — if `end_user` stays empty on an older running version, fall back to `user_header_name`.

Spend tracking and per-end-user budgets are then a property of the **gateway** (LiteLLM), not OWUI — OWUI's only job is emitting the header.

## Per-model request params (`custom_params`)

Model `params` beyond the standard mapped set (temperature, top_p, max_tokens, reasoning_effort, seed, stop, logit_bias, response_format, …) go in `params.custom_params`. Two hard rules:

1. **Values must be JSON strings** — the backend `json.loads`es string values (`utils/payload.py`); the UI's custom-parameter editor stores strings and renders raw objects as `[object Object]` (corrupted on next UI save).
2. Keys are deep-merged and sent **top-level** in the upstream request body (non-Ollama connections copy every param key into the payload; Ollama connections nest under `options`).

```json
{"params": {"custom_params": {
  "chat_template_kwargs": "{\"enable_thinking\": true}",
  "top_k": "40"
}}}
```

### The api_type "responses" seam

With `api_type: "responses"` on the connection, Open WebUI converts chat requests via `convert_to_responses_payload()` (keeps unknown keys) and calls the upstream's `/responses`. Consequences, all verified live:

- vLLM/engine-level knobs (`chat_template_kwargs`, …) survive Open WebUI but are typically **dropped by the upstream's Responses route** (verified: LiteLLM `/v1/responses`). Use the OpenAI-standard Responses params instead — `reasoning: {"effort": ...}` reaches the engine and enables thinking.
- `convert_responses_result()` rebuilds non-streaming answers from `message`/`output_text` items only — **reasoning items are silently discarded for non-streaming API callers**. Streaming callers (and the UI) receive the raw event stream (`response.reasoning_text.delta`, …). Always test reasoning with `stream: true`.
- Usage accounting still proves thinking server-side: `output_tokens_details.reasoning_tokens > 0`.

## Defaults, ordering, task models

- `POST /api/v1/configs/models` — `{DEFAULT_MODELS: "<csv>", DEFAULT_PINNED_MODELS, MODEL_ORDER_LIST, DEFAULT_MODEL_METADATA, DEFAULT_MODEL_PARAMS}`
- Task models (title/tags/query generation): `GET /api/v1/tasks/config` [user], `POST /api/v1/tasks/config/update` [admin]
- Banners: `GET|POST /api/v1/configs/banners`; prompt suggestions: `POST /api/v1/configs/suggestions`

## Permissions object shape (used by groups + default permissions)

Six sections, boolean leaves; each leaf seeded by `USER_PERMISSIONS_<SECTION>_<KEY>` env var:

```json
{"workspace": {"models": false, "knowledge": false, "prompts": false, "tools": false, "skills": false,
               "models_import": false, "models_export": false, "...": "…import/export per type"},
 "sharing":  {"models": false, "public_models": false, "knowledge": false, "public_knowledge": false,
              "...": "…per type", "public_chats": false},
 "access_grants": {"allow_users": true},
 "chat":     {"controls": true, "system_prompt": true, "params": true, "file_upload": true, "delete": true,
              "edit": true, "share": true, "export": true, "temporary": true, "temporary_enforced": false, "...": "…"},
 "features": {"api_keys": false, "channels": true, "web_search": true, "image_generation": true,
              "code_interpreter": true, "memories": true, "automations": false, "webhooks": false, "...": "…"},
 "settings": {"interface": true}}
```

Effective = defaults OR-merged with every group (True wins; groups only grant). Admins bypass. Non-admin sharing is server-filtered: public (`user:*`) grants stripped without `sharing.public_<type>`; user-targeted grants stripped without `access_grants.allow_users`. `BYPASS_ADMIN_ACCESS_CONTROL` (default true) exempts admins from resource ACLs.
