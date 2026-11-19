# Config system — dot-keys, PersistentConfig, connections, params (v0.11.0)

## Storage model

Since 0.10.0 config is per-key rows (`config` table: key TEXT PK, value JSON), dot-namespaced: `ui.default_models`, `openai.api_base_urls`, `auth.enable_api_keys`, `ldap.enable`, `rag.template`, … No published key registry — the authoritative list is a live `GET /api/v1/configs/export`, or the `DEFAULT_CONFIG` dict in `config.py` (468 keys at v0.13.4). Every key in `DEFAULT_CONFIG` is seeded from its env var on first start and read from the DB afterwards; an env var that is not in it is read from the environment on every start. The docs env reference (`docs.openwebui.com/reference/env-configuration/`) marks the same set per variable with "Persistence: This environment variable is a `ConfigVar` variable" — `ConfigVar` is a docs label only, no such class exists in the code. There is no schema and no validation on import: an unknown or misspelled key is stored and never read.

```bash
curl $B/api/v1/configs/export -H "Authorization: Bearer $T" > config-backup.json   # ALL keys, flat
curl -X POST $B/api/v1/configs/import -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"config": {"ui.default_models": "litellm.gemma4-31b"}}'                      # PARTIAL upsert — only supplied keys
curl $B/api/v1/configs/namespace/ui -H "Authorization: Bearer $T"                   # one subtree
```

A ≤0.9.x export (nested blob) cannot be imported into 0.10.x — no translation layer.

**Replaying a full export with an API key fails on v0.12.0+.** If the payload contains any of `auth.mfa.enable`, `auth.mfa.allow_oauth_bypass`, `auth.mfa.allow_trusted_header_bypass` — every full export does — `configs/import` requires a human session JWT: an `sk-` key gets `403 A human administrator session is required to change MFA settings` and **no key is imported**. Strip them before importing from CI:

```bash
jq '{config: (.|with_entries(select(.key|startswith("auth.mfa.")|not)))}' config-backup.json \
  | curl -X POST $B/api/v1/configs/import -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d @-
```

Sent with a session JWT, a changed MFA value signs every user out; an invalid combination is a 409.

**v0.13.4+: image backends are one key, `images.connections`** — a list of `{id, name, type, url, key, config}` with `type` in `openai | gemini | comfyui | automatic1111`. It is written once, at the first start on 0.13.4, from the old per-engine keys. After that the old keys (`image_generation.engine`, `.model`, `.size`, `.steps`, `.openai.*`, `.gemini.*`, `.comfyui.*`, `.automatic1111.*` and the `images.edit.*` equivalents) and their env vars (`IMAGE_GENERATION_ENGINE`, `IMAGES_OPENAI_API_BASE_URL`, `COMFYUI_BASE_URL`, …) are not read, so importing them — a ≤0.13.3 export included — returns 200 and changes nothing. Still live: `image_generation.enable`, `image_generation.prompt.enable`, `images.edit.enable`, plus the new `image_generation.default_model` and `images.edit.default_model` (value `<connection id>:<model id>`). Change backends with `POST /api/v1/images/config/update` (validates each connection, 400 on duplicate ids) or import `images.connections` whole; the export carries each connection's `key` in clear.

Removed at v0.13.4: `direct.enable`, `direct.integrations.enable` and the `features.direct_tool_servers` permission (env `ENABLE_DIRECT_CONNECTIONS`, `ENABLE_DIRECT_INTEGRATIONS`, `USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS`). Drop them from stored config files.

## Applying config from CI (Helm rollout, git-owned keys)

Keep a flat JSON file of only the keys git owns; import it after `helm upgrade --wait`. Import is a partial upsert, returns the full config, and does not validate key names, so verify the response.

```bash
jq --arg key "$LITELLM_KEY" '{config: (. + {"openai.api_keys": [$key]})}' config/owui.json \
  | curl -fsS -X POST "$OWUI_URL/api/v1/configs/import" -H "Authorization: Bearer $OWUI_ADMIN_API_KEY" \
      -H "Content-Type: application/json" -d @- > applied.json
jq -e --slurpfile want config/owui.json '. as $got | $want[0] | to_entries | all(.value == $got[.key])' applied.json
```

- A failed verify means a misspelled key or a key that is not read (see the traps above). Inject secrets with `jq --arg` at apply time, never into the committed file.
- Keep out of the file: `auth.mfa.*` (403, nothing applied), `oauth.*` (env-driven; leave in Helm values), env-only settings (DB URL, secret key, audit, logging).
- `ENABLE_PERSISTENT_CONFIG=false` is the alternative (env always wins) but loses UI edits at restart and cannot manage keys that have no env var. Prefer import.
- Credential for the pipeline: `references/admin-workflows.md` section "Credential for a CI pipeline".

## PersistentConfig precedence (the #1 "env var ignored" mystery)

- Env vars only populate defaults; at first boot every key is seeded into the DB. **From then on the DB wins and env changes are silently ignored** (`ENABLE_PERSISTENT_CONFIG=true`, the default).
- `ENABLE_PERSISTENT_CONFIG=false` inverts it: env always wins, API config writes only mutate in-memory state (lost on restart).
- Exception: `oauth.*` keys are env-driven unless `ENABLE_OAUTH_PERSISTENT_CONFIG=true`.
- Not ConfigVars at all (env-only, restart to change): `WEBUI_SECRET_KEY`, `ENABLE_SCIM`/`SCIM_TOKEN`, `ENABLE_PASSWORD_AUTH`, `AUDIT_LOG_*`, `ENABLE_ADMIN_EXPORT`, `ENABLE_ADMIN_CHAT_ACCESS`, `CUSTOM_API_KEY_HEADER`, DB/Redis URLs.
- Known 0.10.0-refactor regressions (rule these out when a config write appears not to apply): open-webui/open-webui#27061 (web-loader reads frozen env; closed "addressed in dev" with no release named — still suspect on 0.11.0), open-webui/open-webui#26761 (boolean DB values ignored), open-webui/open-webui#24743 (connections lost after restart), open-webui/open-webui#24346 (stale Redis overwrites imports).

**Find env vars in a manifest that no longer do anything:** an env var is seed-only when its name is read by a variable on the right-hand side of a `DEFAULT_CONFIG` entry (and the key is not `oauth.*`). `scripts/seeded-env.py` lists them from the image's own `config.py`, without importing the app:

```bash
kubectl exec -i <pod> -- python3 - < scripts/seeded-env.py          # checks the pod's own env
scripts/seeded-env.py <checkout>/backend/open_webui/config.py NAME1 NAME2   # checks named vars against a source tree
```

Each line printed is `ENV_NAME -> config.key`: compare the manifest value with that key in `configs/export`, then either delete the env var or keep it knowingly as the seed for an empty database.

Operational rule: manage runtime config via API (`configs/import` in CI), reserve env for bootstrap + the env-only list.

## Two plugin kill switches that are not interchangeable

Both are env-only. Confusing them costs real state.

- **`SAFE_MODE=true` is a destructive DB mutation, not a runtime flag.** At every startup it runs `Functions.deactivate_all_functions()` (`main.py:354-355`), an unconditional `UPDATE function SET is_active = false` across **every row** (`models/functions.py:417-429`). It gates no router and no endpoint — the whole `/api/v1/functions/*` surface stays callable, and you can even re-activate a function while it is on; the next restart wipes that again. **Turning `SAFE_MODE` back off does not restore anything** — every function stays deactivated and must be re-enabled one by one via `POST /api/v1/functions/id/{id}/toggle`. Pipe models disappear from `/api/models` and filter/action hooks stop firing purely as a data consequence.
- **`ENABLE_PLUGINS=false` (new in 0.11.0, default true) is the non-destructive equivalent** (`env.py:1112` at v0.11.0, `:1182` at v0.13.0). It gates tools *and* functions at request time without touching the DB. Its failure mode is the opposite one: list endpoints return **`200 []` instead of an error** (`functions.py:49,57,74`, `tools.py:75,205`), so an inventory script reads "everything was deleted" rather than "plugins are off". Surfaced as `features.enable_plugins` in `GET /api/config`.

If the intent is "no plugin code executes", `ENABLE_PLUGINS=false` is the correct mechanism in 0.11.0; `SAFE_MODE` additionally destroys activation state.

**v0.12.0+: `ENABLE_PLUGINS` is a master over three finer env switches** — `ENABLE_TOOLS`, `ENABLE_FUNCTIONS`, `ENABLE_TOOL_SERVERS` (each default true, each forced false when `ENABLE_PLUGINS=false`; `env.py:1182-1186` at v0.13.0). The master now also cuts external OpenAPI/MCP/Open Terminal servers and personal direct connections; to stop in-process Python while keeping tool servers, set `ENABLE_TOOLS=false ENABLE_FUNCTIONS=false` instead. All four need a restart.

**`AUDIT_EXCLUDED_PATHS=""` flipped meaning in 0.11.0.** Empty entries are now filtered out (`env.py:1167-1180`). In 0.10.2 an empty value compiled to `^/api(?:/v1)?/()\b`, which matched *every* `/api/...` path — auditing was silently off. In 0.11.0 it compiles to `None` and nothing is excluded, so the same config audits everything. Expect a step change in audit-log volume on upgrade; use a sentinel like `__NONE__` if the intent is "exclude nothing" and you want it to read explicitly.

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

Tool servers (OpenAPI + MCP): `GET|POST /api/v1/configs/tool_servers` — entries `{url, path, type:'openapi'|'mcp', auth_type, headers, key, config, info}`; validate with `/api/v1/configs/tool_servers/verify` before saving (a dead server can hang the UI and crash-loop workers — open-webui/open-webui#22543, open-webui/open-webui#24330).

### Forwarding user identity upstream (per-user attribution)

Open WebUI has **no native per-user rate limiting or quota** (only sign-in is throttled) — to attribute or cap usage per user, forward the authenticated identity to the upstream gateway and enforce there. `ENABLE_FORWARD_USER_INFO_HEADERS=True` (env) makes OWUI add `X-OpenWebUI-User-{Name,Id,Email,Role}` to every upstream call on the proxy paths (`openai`, `ollama`, anthropic, audio, images, tools, retrieval — `routers/openai.py:include_user_info_headers`); the chat path additionally sends `X-OpenWebUI-Chat-Id` when a chat is bound. Header names are overridable (`FORWARD_USER_INFO_HEADER_USER_*` in `env.py`). Note `user.id` is an OWUI-internal uuid4 (**not** the OIDC `sub`), so prefer the `…-Email` header for human-legible downstream records.

**v0.11.4 adds `X-OpenWebUI-Auth-Type`** to the same header set on `openai`/`ollama` connections, carrying `"cookie"` or `"api_key"` depending on how the caller authenticated. Env override is `FORWARD_USER_INFO_HEADER_AUTH_TYPE` (default `X-OpenWebUI-Auth-Type`), and `{{AUTH_TYPE}}` is available in custom headers (`env.py:997`, `utils/headers.py`). Useful for a gateway that wants to rate-limit interactive browser traffic differently from scripted API-key callers.

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

Both paths converge on the same `end_user_id` (`auth_utils.py:get_end_user_id_from_request_body` checks customer mappings first, then falls back to `user_header_name`), so spend logs / Customers look identical after switching. Use `litellm_user_role: customer`, NOT `internal_user` — the latter writes `user_api_key_dict.user_id` (the internal-user column) instead of `end_user`. Historical caveat: LiteLLM BerriAI/litellm#12893 / BerriAI/litellm#14667 reported the mappings path broken with OWUI on older versions (source-verified working on post-v1.92.1 main; see the traefik-hardening skill's ledger) — if `end_user` stays empty on an older running version, fall back to `user_header_name`.

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
- **v0.11.4 fixes two Responses-conversion bugs (both `routers/openai.py`).** Before, a Chat-Completions tool with no explicit `strict` key defaulted to Responses' own `strict: true` instead of Chat-Completions' `false`, so the model filled every optional argument and search/filter tools got values meant to be omitted (open-webui/open-webui#30046, `openai.py:1417-1424` — `converted_tool['strict'] = func.get('strict', False)`). And a forced `tool_choice` in Chat-Completions shape was forwarded unconverted (providers rejected it) and a **non-streaming** reply carrying a function call flattened to empty text with `finish_reason: "stop"`; both now convert (open-webui/open-webui#30095, `openai.py:1428-1466` — forced choice becomes `{"type":"function","name":...}`, `function_call` output items become `tool_calls` with `finish_reason: "tool_calls"`).

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

Effective = defaults OR-merged with every group (True wins; groups only grant). Admins bypass. Non-admin sharing is policy-checked: any grant needs `sharing.<type>` where that key exists (models, knowledge, prompts, tools, skills, notes, folders), public (`user:*`) grants `sharing.public_<type>`, user-targeted `access_grants.allow_users`, group-targeted `access_grants.allow_groups`. On create a disallowed grant is silently stripped; on `…/access/update` (v0.12.4+) the whole request is refused with 403. `BYPASS_ADMIN_ACCESS_CONTROL` (default true) exempts admins from resource ACLs.
