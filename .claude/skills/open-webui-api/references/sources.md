# Sources — code, docs, issues, live verification

Every claim in this skill traces to one of these groups. Load to verify a specific fact or run `freshen` mode. Research provenance: `.claude/skills/autoresearch/results/open-webui-api-research-2026-07-21.md` (5-agent STORM pass, code-grounded).

## Verification log

| Source group | Last verified | Notes |
|---|---|---|
| open-webui/open-webui local clone at **v0.10.2** (ecd48e2f7, released 2026-07-01) | 2026-07-21 | Primary source for every endpoint, payload shape, auth rule. Key files below. |
| Live instance on v0.10.2 (458 paths / 503 operations) | 2026-07-21 | openapi.json diffed against code — all differences explained by feature flags (SCIM off, analytics on), zero drift. Live-executed: models create/delete/toggle-shape, `model/update` 500, custom_params JSON-string requirement, api_type=responses reasoning path incl. `reasoning_tokens` usage evidence, `GET /openai/config` key readback, error-probe bisection. |
| open-webui/docs clone (HEAD d412c345) | 2026-07-21 | reference/api-endpoints.md (~18 documented paths vs 458 real; "experimental setup" statement; ENV=dev Swagger gate; outlet retraction), features/authentication-access/api-keys.md, auth/scim.mdx, reference/env-configuration.mdx |
| CHANGELOG.md + git history sweep 0.5.0 → 0.10.2 | 2026-07-21 | Ledger dates/versions in breaking-changes.md; router introduction versions via `git log --diff-filter=A` + `git describe` |
| GitHub issues (gh CLI): #17964 #18039 #19168 #19797 #20184 #20359 #20673 #20901 #20942 #21280 #21467 #21843 #21851 #22543 #24253 #24330 #24346 #24501 #24579 #24631 #24743 #24906 #25650 #26761 #27061 | 2026-07-21 | Open at last check: #24501, #24906, #27061. Re-probe on freshen. |
| vllm-project/recipes gemma-4-31B-it.yaml | 2026-07-21 | `chat_template_kwargs` enable_thinking contract + `--default-chat-template-kwargs` server default |

## Key code files (clone: `~/projects/github.com/open-webui/open-webui`, v0.10.2)

Line numbers resolved against v0.10.2 — expect drift in later clones; re-resolve by symbol name.

- `backend/open_webui/main.py` — router mounts (728–775), app-level endpoints (799–2570), model-params merge order (1043–1053), SPA catch-all HTML-200 trap (261–273), ENV-gated docs/openapi (431–432)
- `backend/open_webui/utils/auth.py` — get_current_user/get_verified_user/get_admin_user chain (315–493), API-key branch `sk-` (341), key gating (440–448), endpoint-restriction matching (450–461), JWT create/validate + Redis revocation (218–293)
- `backend/open_webui/utils/access_control/__init__.py` — permission OR-merge (30–103), grant checks + public `user:*` semantics (119–123), sharing filters (212–256), base-model-chain walk (259–297)
- `backend/open_webui/models/access_grants.py` — grant table (20–41), old-shape migration semantics (79–115)
- `backend/open_webui/utils/payload.py` — custom_params json.loads + deep-merge (99–160), unmapped-key passthrough (60–68)
- `backend/open_webui/utils/middleware.py` — apply_params_to_form_data (1872–1915), applied at 2201
- `backend/open_webui/routers/openai.py` — payload={**form_data} (1126), prefix strip (1171), convert_to_responses_payload (928, keeps unknown keys), **convert_responses_result drops reasoning for non-stream (1070)**, per-connection model_ids/prefix_id/connection_type (453–508)
- `backend/open_webui/routers/{auths,users,groups,configs,models,knowledge,files,retrieval,chats,scim,evaluations,functions,tools,pipelines,analytics,utils}.py` — endpoint signatures + payload forms
- `backend/open_webui/config.py` — ConfigVar registry, DEFAULT_USER_PERMISSIONS, ENABLE_API_KEYS no-fallback (≈2379), PersistentConfig seeding (≈3129)
- `backend/open_webui/env.py` — env-only settings: SCIM (799–812), WEBUI_ADMIN_* (715–717), audit (1071–1105)
- `backend/open_webui/events.py` — webhook event-name registry

## Ecosystem (tier B/C, for context only)

- sysinit-at/openwebui-cli (`owui`) — closest prior-art admin CLI (active 2026-07)
- Fu-Jie/openwebui-chat-client — best-maintained Python client (PyPI)
- npm `@kingsland/open-webui-client` — claims "Official"; is not. No official SDK exists in any language.
- taylorwilsdon/open-webui-postgres-migration — SQLite→Postgres tooling
- docs.openwebui.com/reference/api-endpoints — the ~4%-coverage official reference

## Freshen guidance

1. `gh release view --repo open-webui/open-webui` — new minor ⇒ sweep CHANGELOG for: auth/key changes, router adds/renames, access_grants/config shape changes, outlet/filter behavior. Extend the ledger; never rewrite verified history.
2. Re-probe the open issues row; move closed ones into breaking-changes triage notes if resolution matters.
3. The `api_key` table has unused `expires_at`/`data` columns (v0.10.2) — named/expiring multi-keys are likely coming; when they land, rewrite the "one unscoped key" guidance in SKILL.md.
4. Watch for `access_control` compat shims appearing in import endpoints (none exist as of 0.10.2).
