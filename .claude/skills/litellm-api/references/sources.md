# Sources — code, docs, issues, verification log

Every claim traces to one of these groups. Load to verify a specific fact or run `freshen` mode.

## Verification log

| Source group | Last verified | Notes |
|---|---|---|
| BerriAI/litellm local clone @ `4d543245` (v1.95.0-dev, 2026-07-29; latest stable v1.94.0) | 2026-07-30 | Primary source for every file:line. Surface counts (746 decorators, 624 paths, 91 hidden, 34 lazy features, 51/315 DISABLE_ADMIN coverage) measured by scripted scan over `litellm/proxy/` + `enterprise/`. |
| BerriAI/litellm-docs local clone @ `803ee53` (2026-07-30) | 2026-07-30 | Doc-coverage claim (225 of 359 management paths undocumented) = path-grep over the 767-file corpus. Good pages worth citing instead of restating: `key_auth_arch.md:24-36` (sentinels), `configs.md:126-128` (DB overlay), `access_control.md:215-275` (team permissions concept), `model_management.md:39-49`, `customers.md:419`, `mcp_control.md:100`. |
| BerriAI/litellm-skills clone (21 task skills; last meaningful commit 2026-05-07) | 2026-07-30 | The `"models": []` template hazard read directly from `add-key/SKILL.md:47`, `update-key/SKILL.md:49`. |
| Key source files | 2026-07-30 | `litellm/proxy/_types.py` (`LiteLLMRoutes` `:270-867`, sentinels `:3110-3113`, premium fields `:4075-4085`, `KeyManagementRoutes` `:231-261`), `auth/route_checks.py` (allowed_routes `:99-119`, `:537-560`; MCP bypass `:308-309`; viewer default-allow `:752-859`; admin_only_routes no-op `:333-338`), `auth/user_api_key_auth.py` (no-master-key `:1406-1417`, `:2160-2165`), `auth/auth_checks.py` (empty-models `:2948-2951`, sentinels `:3045-3060`, `:3366`), `management_endpoints/key_management_endpoints.py` (key_type `:470-485`, defaults `:790-805`, update merge `:1887`, budget writes `:1925-1951`, premium gates `:957`, `:3565`, `:3801`, `:4725`), `team_endpoints.py`, `internal_user_endpoints.py`, `organization_endpoints.py`, `management_helpers/common_utils.py` (member-budget clone/disconnect `:400-509`), `management_helpers/team_member_permission_checks.py:19-47`, `_lazy_features.py` (`:54-256`, `:301-344`, `:366`, `:409-430`), `proxy_server.py` (DB overlay `:6005-6135`, config mock `:15690`, openapi filter `:1357-1393`, error-shape split `:1458-1476`, enterprise import `:671-679`), `hooks/parallel_request_limiter_v3.py` (descriptor AND-composition `:790-830`, `:1580-1700`), `constants.py` (`LITELLM_SETTINGS_SAFE_DB_OVERRIDES` `:1519-1536`). |
| GitHub issues (gh CLI sweep) — full list | 2026-07-30 | Every issue number cited across the references; states as of the sweep. Notable verifications: #25495 closed **as stale** (not fixed); #15230 still open with 38 comments; #35076 opened 2026-07-30. |

Research provenance: 4-agent pass 2026-07-30 in session litellm-skills (management-API surface audit with measured counts + issue sweep); the surface counts and file:line cites originate from the audit agent's scripted scans over the same pinned clone.

## Freshen protocol

1. `git -C <litellm-clone> pull`; restamp SHA; re-resolve headline line numbers **by symbol** (`LiteLLMRoutes`, `KeyManagementRoutes`, `_lazy_features.LAZY_FEATURES`, `LITELLM_SETTINGS_SAFE_DB_OVERRIDES`, the empty-models check in `auth_checks.py`).
2. Re-measure the surface: count route decorators + `include_in_schema=False` under `litellm/proxy/` + `enterprise/`; diff against 746/91 — a big delta means the endpoint map needs a re-audit.
3. Re-check the OPEN issue list (one `gh issue list` sweep on the numbers in `known-issues.md` + cross-reference index); promote fixes into fix-version rows. Priority watches: #34296 (access-group grants), #35076 (skip_user_budget), #34217 (deleted-team keys), #15230 (enterprise 403), #33277 (presence-check 403), #32695 (OpenAPI budget_limits).
4. Re-grep the docs corpus for previously-undocumented families (`/access_group/`, `/budget/`, `/config/`, `coordination_redis`) — "undocumented" claims expire when docs land.
5. Check whether `models: []` semantics changed (`auth_checks.py` empty-list branch) — it is the single highest-impact claim in the skill.
6. Re-read `litellm-skills` templates — if BerriAI fixes the `"models": []` emission, soften that warning.
