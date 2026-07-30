# Config-vs-DB duality — STORE_MODEL_IN_DB and the /config surface

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29).

## The flag and its three spellings

`store_model_in_db` is read from `general_settings.store_model_in_db` **or** the `STORE_MODEL_IN_DB` env var, and is runtime-mutable via `POST /config/update` (`proxy_server.py:4817-4820`, `:5952-5962`). Trap: a stale `LiteLLM_Config.general_settings.store_model_in_db=false` **row in the DB overrides the env var** (#31968 open) — the env spelling is the weakest of the three.

## Precedence when ON

- DB rows for `general_settings`, `router_settings`, `litellm_settings`, `environment_variables` are **deep-merged over** the YAML; **DB wins**, except DB `None` and DB `[]` are treated as "no value" (`proxy_server.py:6005-6018`, `:6055-6062`). Editing YAML + restart does not change a UI-written key. (`docs/proxy/configs.md:126-128` documents this correctly as of 2026-07-30 — one of the few good pages.)
- Only the 14 keys in `LITELLM_SETTINGS_SAFE_DB_OVERRIDES` (`constants.py:1519-1536`) are pushed onto the live `litellm` module; other DB `litellm_settings` land in the config dict but not the runtime attribute (`proxy_server.py:6045-6048`) — a DB write can "succeed" and change nothing observable.
- `general_settings.supported_db_objects` filters which object types load from DB at all (`proxy_server.py:6108-6135`) — an easy way to make `/model/new` writes appear to vanish on restart.
- DB-sourced remote module loads (`s3://…`) are scrubbed from the overlay (`proxy_server.py:6027-6031`) — a value that works in YAML silently doesn't from DB.
- DB-backed `router_settings` JSON strings are skipped on reload (#31836 open); DB router rebuild drops `cache_responses` (#32106 open).

## Model management failure shapes

| Situation | Behavior |
|---|---|
| Flag ON, `POST /model/new` | can return **200 with `db_model: false`** = write skipped, model vanishes on restart (#30771 open). Always check `db_model` in the response. |
| Flag OFF, any of `/model/new`, `/model/update`, `/model/delete`, `/model_group/make_public` | **HTTP 500** (not 400/409) with "Set `STORE_MODEL_IN_DB='True'`" (`model_management_endpoints.py:1216`, `:1388`, `:1642`) |
| Editing a config-YAML model | `PATCH /model/{model_id}/update` → "Cannot edit config-based model. Store model in DB via /model/new first." (`:270-276`) |
| Multi-worker delete | deleted models ghost in other workers' caches (#27852 open); DB auto-router models vanish from `/v1/models` after update/delete (#33168 open) |
| Export DB state back to YAML | **doesn't exist** (#28168 open feature) — UI-managed config is a one-way door. Mitigate: manage via API/GitOps scripts only, treat the UI as read-only. |

## The /config/* surface (13 paths, all hidden from openapi)

- `POST /config/update` — admin-only, per-section merge (`proxy_server.py:14540-14562`). This is what the UI uses; it's how DB shadowing (incl. `coordination_redis`) gets written.
- `GET /config/yaml` — **a mock returning `{"hello": "world"}`** (`proxy_server.py:15690`), and it's in `public_routes`. Never treat it as config export.
- Guardrails duality mirror: `GET /guardrails/list` = config-file only; `GET /v2/guardrails/list` = config + DB merged (`guardrail_endpoints.py:125-137`).
- Pass-through endpoint config lives under `/config/pass_through_endpoint*` (`pass_through_endpoints/pass_through_endpoints.py:3034-3319`); pass-through spend/limit gaps are real: no RPM/concurrency limits on custom pass-throughs (#29921), unbounded registry growth → 100% CPU (#26081), SSRF report open (#33000, CVSS 7.5), spend logs with `model=unknown` (#30932), vLLM passthrough logs nothing (#33210).

## GitOps recipe that survives the duality

1. Set `STORE_MODEL_IN_DB` **in general_settings (YAML)**, not env, so the DB row can't shadow it ambiguously.
2. Treat DB as authoritative for models; reconcile declaratively: `GET /v2/model/info` → diff against desired → `/model/new` / `/model/update` / `/model/delete`; assert `db_model: true` on every write response.
3. Treat YAML as authoritative for settings; after any UI usage, diff `GET /get/config/callbacks` + relevant `/config` reads against the repo and delete stray DB rows (or at minimum alert on them).
4. Verify with restart-shaped tests: a model that survives `kubectl rollout restart` is in the DB; one that doesn't was config-YAML or a skipped write.
