# Admin workflows — verified call sequences (v0.10.2)

Contents: [User lifecycle](#user-lifecycle) · [Groups + permissions](#groups--permissions) · [Model catalog GitOps](#model-catalog-gitops-) · [Knowledge pipeline](#knowledge-pipeline-upload--process--attach--shape-verified) · [Backup / migration surface](#backup--migration-surface) · [Reasoning/thinking passthrough](#reasoningthinking-passthrough-)

All payload shapes read from v0.10.2 source; sequences marked ⚡ were additionally executed live against a v0.10.2 instance (2026-07-21). `$B` = base URL, `$T` = admin token (JWT or `sk-` key).

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
- ⚡ `model/update` returned 500 on a live 0.10.2; delete+create is the reliable path.
- Per-model backend extras go in `params.custom_params` with **JSON-string values** (see config-system.md).

Access example — make a model group-visible:

```json
{"id": "litellm.gemma4-31b", "access_grants": [
  {"principal_type": "group", "principal_id": "<group_id>", "permission": "read"}
]}
```

Public = `{"principal_type":"user","principal_id":"*","permission":"read"}`. Empty list = owner/admin-only. Grants are replace-all on write.

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

Batch: `POST /knowledge/{id}/files/batch/add`; reconcile a directory: `POST /knowledge/{id}/sync/diff`. Query it in chat: `POST /api/chat/completions` with `"files":[{"type":"collection","id":"<kb-id>"}]`.

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
