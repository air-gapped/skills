# Admin workflows — verified call sequences (v0.11.0)

Contents: [Bootstrapping a token on an SSO-only instance](#bootstrapping-a-token-on-an-sso-only-instance-) · [User lifecycle](#user-lifecycle) · [Groups + permissions](#groups--permissions) · [Model catalog GitOps](#model-catalog-gitops-) · [Knowledge pipeline](#knowledge-pipeline-upload--process--attach--shape-verified) · [Backup / migration surface](#backup--migration-surface) · [Reasoning/thinking passthrough](#reasoningthinking-passthrough-)

Payload shapes read from source; sequences marked ⚡ were additionally executed live (v0.10.2 on 2026-07-21, re-verified plus new ones on v0.11.0 on 2026-07-29). `$B` = base URL, `$T` = admin token (JWT or `sk-` key).

## Bootstrapping a token on an SSO-only instance ⚡

The common hardened deployment — `ENABLE_LOGIN_FORM=False` + OIDC signup, with `ENABLE_API_KEYS` left at its default `false` — has **no API-reachable way to obtain a token**: `/auths/api_key` is gated off, and a password sign-in needs a local password account (see "Credential for a CI pipeline" below; `ENABLE_LOGIN_FORM=False` alone does not block it). Automation has to mint a JWT out-of-band using the instance's own signing key.

`WEBUI_SECRET_KEY` is generated on first boot into `${BACKEND_DIR}/.webui_secret_key` (`start.sh:32-50`) and exported only into the *app* process — a fresh `kubectl exec`/`docker exec` does **not** inherit it, so read the file explicitly or the import aborts with "WEBUI_SECRET_KEY is not set".

```bash
# k8s; for docker swap the exec prefix. Mint a short-lived admin JWT.
kubectl -n <ns> exec <pod> -c open-webui -- sh -c \
  'export WEBUI_SECRET_KEY=$(cat /app/backend/.webui_secret_key) && python -c "
import asyncio
from datetime import timedelta
from open_webui.models.auths import Auths
from open_webui.utils.auth import create_token
a = asyncio.run(Auths.get_auth_by_id(\"<admin-user-id>\"))
print(create_token({\"id\": \"<admin-user-id>\", \"typ\": \"session\", \"session_stamp\": a.session_stamp}, timedelta(hours=8)))
"'
```

Find `<admin-user-id>` the same way (`Users.get_users()` is async — wrap in `asyncio.run`). `create_token` adds `jti`/`iat` itself, and an `expires_delta` sets `exp`. **v0.12.0+ rejects a token whose `session_stamp` differs from the account's current one** — a `{"id"}`-only token fails for any account created on 0.12+ or whose stamp was rotated (password change, sessions/revoke), and a rotation later kills the minted token too. Below 0.12.0 `{"id": ...}` alone is enough. With `ENABLE_MFA` on, add `"mfa_verified": true` — accepted only if the account has an enrolled authenticator. Prefer a short expiry over the `4w` default for a token you are pasting into a shell.

Verify before use — a wrong-role or expired token fails as HTML, not 401:

```bash
curl -s -H "Authorization: Bearer $T" $B/api/v1/users/user/status | jq -e .role   # expect "admin"; /auths/ 403s every sk- key from v0.12.0
```

Cleaner long-term alternative: set `ENABLE_API_KEYS=true` and grant the `features.api_keys` permission to a dedicated non-admin service account, then scope it with `API_KEYS_ALLOWED_ENDPOINTS`. The minted-JWT route is for bootstrap and break-glass, not steady-state automation.

## Credential for a CI pipeline

- **API key path.** An `sk-` key is accepted only when config key `auth.enable_api_keys` is true (env `ENABLE_API_KEYS`, default false, seed-only; with it off every key, an admin's included, gets 403). Non-admins also need `features.api_keys` (env `USER_PERMISSIONS_FEATURES_API_KEYS`, default false); admins skip that check. A group can grant `features.api_keys`, so audit group permissions too. The owning account mints the key: `POST /api/v1/auths/api_key`, read back with `GET`. Enabling `ENABLE_API_KEYS` does not give ordinary users keys. With `API_KEYS_ALLOWED_ENDPOINTS` restrictions on, add `/api/v1/configs` to the allowed list or the import returns 403.
- **Session token path.** `POST /api/v1/auths/signin` (email + password) returns a JWT that expires after `JWT_EXPIRES_IN` (`auth.jwt_expiry`, default `4w`), so a job signs in on every run. Use it to mint the key once, or when API keys must stay off.
- **OIDC sites: a local password account coexists with OIDC users.** `ENABLE_PASSWORD_AUTH` (env only, default true, read every start): when false, `POST /auths/signin` returns 403, so it must stay true for this route. `ENABLE_LOGIN_FORM` (`ui.enable_login_form`): when false it only hides the UI form and blocks signup; the signin endpoint does not check it.
- **Creating the account.** New install: `WEBUI_ADMIN_EMAIL`/`WEBUI_ADMIN_PASSWORD` create an admin at first start only while the user table is empty (`create_admin_user`). Existing install: an admin calls `POST /api/v1/auths/add` with role `admin`.

## User lifecycle

```bash
# Create (admin) — response contains a LOGIN TOKEN for the new user; discard it for service provisioning
curl -X POST $B/api/v1/auths/add -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"name":"Svc Reporter","email":"svc-reporter@example.com","password":"<random>","role":"pending"}'

# Activate / change role / reset password — one endpoint, partial body
curl -X POST $B/api/v1/users/{user_id}/update -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"role":"user"}'

# List (paginated 30/page, fixed) / delete
curl "$B/api/v1/users/?page=1&query=" -H "Authorization: Bearer $T"
curl -X DELETE $B/api/v1/users/{user_id} -H "Authorization: Bearer $T"
```

Deactivate = set role `"pending"`. The first-created user is protected: not modifiable/deletable by other admins, cannot self-demote.

Service-account pattern (recommended over admin keys): create a `user`-role account, grant `features.api_keys` (via group or default permissions), sign in once (`POST /api/v1/auths/signin` → token), then `POST /api/v1/auths/api_key` as that user to mint its key. Scope with `API_KEYS_ALLOWED_ENDPOINTS` if the workload allows.

## Groups + permissions

```bash
# Create (no members possible at create), then add members incrementally
curl -X POST $B/api/v1/groups/create -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"name":"data-team","description":"Data team","permissions":{"features":{"api_keys":true}}}'
curl -X POST $B/api/v1/groups/id/{group_id}/users/add -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"user_ids":["<uid1>","<uid2>"]}'
# Audit what the group can reach:
curl $B/api/v1/groups/id/{group_id}/preview -H "Authorization: Bearer $T"
```

Permission resolution is OR-merge over (global defaults ∪ all groups): groups can only **grant**, never revoke. Global defaults: `GET|POST /api/v1/users/default/permissions`.

## Model catalog GitOps ⚡

```bash
# Export current catalog (JSON array) — commit this to git
curl $B/api/v1/models/export -H "Authorization: Bearer $T" > models.json
# Additive upsert (safe): POST /api/v1/models/import  {"models":[...]}
# Declarative reconcile (DELETES models absent from payload):
curl -X POST $B/api/v1/models/sync -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d "{\"models\": $(cat models.json)}"
```

ModelForm essentials: `{id, base_model_id?, name, meta:{description?, capabilities?, knowledge:[<kb objects>]}, params:{...}, access_grants:[...], is_active}`.
- Customize an upstream/base model: create a row whose `id` equals the upstream id (e.g. `litellm.gemma4-31b`); create a *preset* by using a new id + `base_model_id`.
- Params merge at completion time: `models.default_params` config < per-model params < request params — presets don't lock anything.
- `model/update` grant handling changed twice (500 on omission ≤0.11.1, replace-when-present 0.11.2–0.12.3, ignored 0.12.4+) — set grants with `POST /models/model/access/update` on every version that has it. Details in SKILL.md gotchas.
- Per-model backend extras go in `params.custom_params` with **JSON-string values** (see config-system.md).

Access example — make a model group-visible:

```json
{"id": "litellm.gemma4-31b", "access_grants": [
  {"principal_type": "group", "principal_id": "<group_id>", "permission": "read"}
]}
```

Send it to `POST /api/v1/models/model/access/update`. Public = `{"principal_type":"user","principal_id":"*","permission":"read"}`. Empty list = owner/admin-only. Grants are replace-all on write.

## Knowledge pipeline (upload → process → attach) ⚡ shape-verified

```bash
KB=$(curl -s -X POST $B/api/v1/knowledge/create -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"name":"runbooks","description":"Ops runbooks"}' | jq -r .id)
FID=$(curl -s -X POST "$B/api/v1/files/?process=true&process_in_background=true" \
  -H "Authorization: Bearer $T" -F "file=@runbook.pdf" | jq -r .id)
# MUST wait for processing before attach (else 400):
until curl -s $B/api/v1/files/$FID/process/status -H "Authorization: Bearer $T" | jq -e '.status=="completed"' >/dev/null; do sleep 2; done
curl -X POST $B/api/v1/knowledge/$KB/file/add -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d "{\"file_id\":\"$FID\"}"
```

Batch: `POST /knowledge/{id}/files/batch/add`; reconcile a directory: `POST /knowledge/{id}/sync/diff`.

From v0.12.5 `file/add` returns only the added file (and `file/remove` `files: []`) — read the KB's files from the paginated `GET /knowledge/{id}/files?page=`. From v0.13.0 uploads can hit admin or per-KB limits: 400 "You can only upload a maximum of N file(s) per batch" or "Knowledge base file limit exceeded", 413 for a too-large file; preflight with `POST /knowledge/{id}/files/validate` `{"count":N,"file_size":<bytes>,"removed_file_ids":[]}`. Query it in chat: `POST /api/chat/completions` with `"files":[{"type":"collection","id":"<kb-id>"}]`.

## Backup / migration surface

| What | Endpoint | Gate |
|---|---|---|
| All config (flat dot-keys) | `GET /api/v1/configs/export` | admin |
| Model catalog | `GET /api/v1/models/export` | admin |
| Own chats (NDJSON stream) | `GET /api/v1/chats/all` | user |
| Full chat DB | `GET /api/v1/chats/all/db` | `ENABLE_ADMIN_EXPORT` |
| Per-user chats | `GET /api/v1/chats/list/user/{id}` | `ENABLE_ADMIN_CHAT_ACCESS` |
| Feedbacks | `GET /api/v1/evaluations/feedbacks/all/export` | admin |
| Per-KB | `GET /api/v1/knowledge/{id}/export` | admin |
| Raw SQLite | `GET /api/v1/utils/db/download` | admin + `ENABLE_ADMIN_EXPORT`; 400 on Postgres |

Not exportable via API: vector DB contents, audit log (file-only), file binaries in bulk (only per-file `GET /files/{id}/content`).

## Reasoning/thinking passthrough ⚡

Enable model thinking per-model via `custom_params` (JSON-string values — semantics and the `api_type: "responses"` seam are in `config-system.md`):

```bash
curl -X POST $B/api/v1/models/create -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{
  "id": "litellm.gemma4-31b", "name": "litellm.gemma4-31b",
  "meta": {"description": "thinking on"},
  "params": {"custom_params": {"reasoning": "{\"effort\": \"medium\"}"}},
  "is_active": true}'
```

`reasoning` is the knob for Responses-API connections; `chat_template_kwargs` (as a JSON string) for plain chat-completions connections. Verify with `stream: true`.
