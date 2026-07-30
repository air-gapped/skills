# Known-issue catalog — management API, BerriAI/litellm

Sweep 2026-07-30. ~1,566 open issues total; ~192 open mention "budget", ~267 "spend", ~38 "access group". Management-plane issues sit open for months with no maintainer comment (e.g. #28021 since May, #25951 since April, #15230 since Oct 2025/38 comments); the stale bot closes real bugs (#25495). "Closed" ≠ "fixed" without a linked PR. Maintainer roadmap: #30484 (open) acknowledges spend/budget as P0.

Budget/spend issues are catalogued in `budgets-spend.md`; access-model issues in `access-model.md`; config-DB in `config-db.md`. This file holds the rest + the cross-reference index.

## Enterprise-gating false positives (the #15230 class)

| Issue | State | Note |
|---|---|---|
| #15230 | **OPEN since 2025-10**, 38 comments | UI key-edit → "Enterprise users" error; UI round-trips `guardrails`/empty arrays into `/key/update`. Workaround: API update omitting those fields |
| #11552 #14934 #20304 #20476 #20534 #21037 #21570 #22201 #30285 | closed dupes | same class across ≥8 versions — it keeps coming back; assume any full-object round-trip can trigger it |
| #34241 | OPEN | "Clear license boundaries between MIT and Enterprise" — the boundary is undocumented |

## /key/update and non-admin permission regressions

| Issue | State | Impact |
|---|---|---|
| #33277 | OPEN (v1.92.0 regression) | non-admin `/key/update` 403s when body *includes* `allowed_routes`/`permissions` (presence-checked) — breaks team moves + UI round-trips |
| #33246 | closed | dashboard always sent `budget_limits: []` → every non-admin self-service key edit 403'd |
| #27005, #26555 | OPEN | related non-admin update failures |
| #33194 / #33212 | OPEN | non-admins can't set max_budget on personal keys |
| #29305 | OPEN | `/key/update` 403 when a previously-assigned MCP server was deleted |
| #20962 | OPEN | UI requires team for non-admin key creation while API blocks team assignment — deadlock |
| #29073 | closed | v1.86.0: UI session's $0.25 budget became the ceiling for keys generated via UI |

## Team/org/user lifecycle integrity

| Issue | State | Impact |
|---|---|---|
| #25951 | OPEN since April | `/team/member_add` read-modify-write race silently loses members under concurrency — serialize calls |
| #34217 | OPEN (community fix PR #34218 pending) | `/team/delete` leaves the team's keys **auth-valid in cache** until TTL (+ cache-key mismatch `team_id` vs `team_id:{id}` in invalidation) |
| #30798 | OPEN | `/team/info` leaks internal `model_name_{team_id}_{uuid}` keys; `/team/update` round-trips them → persistent `team.models` corruption |
| #31447 | OPEN | setting `team_member_budget` replaces the team's entire `metadata` object |
| #27294 / #30843 | OPEN | org_admin 401 on `/team/update`; org admin can't add internal user |
| #33941 | OPEN | `/customer/update` silently drops `budget_duration` |
| #32062 / #30984 | OPEN | `/key/list` filters OR'd instead of AND'd for team-visibility callers; `size` cap 100 bites the UI |
| #31838 / #31839 | OPEN | `/customer/*` mutations don't invalidate Redis end-user caches/counters |

## API-doc / OpenAPI accuracy

| Issue | State | Impact |
|---|---|---|
| #32695 | OPEN | OpenAPI documents `budget_limits` with wrong field names (`budget_limit`/`time_period` vs actual `max_budget`/`budget_duration`) |
| #16623 | OPEN | config.yaml schema no longer in the OpenAPI spec |
| #33690 | OPEN | SSO role value docs≠code (`internal_user_view_only` vs `internal_user_viewer`) |
| #21066 | closed | Swagger auth used wrong header |
| #23850 | closed | "Access Groups not working as described" — doc-vs-behavior acknowledged |

## Pass-through endpoints

#30932 (model=unknown in SpendLogs), #33210 (vLLM passthrough logs nothing), #30667 (mid-stream failures log no cost), #30725 (zeroed cost_breakdown), #29921 (no RPM/concurrency limits on custom pass-throughs), #26081 (registry grows unbounded → 100% CPU), #24500 (subpath + no-auth still 401s), #33000 (SSRF, CVSS 7.5, **open**).

## Cross-reference index (issues detailed in sibling files)

- Budgets/spend: #34492 #34270 #28021 #27734 #26239 #35076 #25495 #27481 #24675 #25386 #33321 #28020 #31842 #33871 #33326 #34896 #17993 #19105 #29066 #30437 #25508 #27735 #26672 #30484 #33923 #33873 #33872 #34820 #34805 #31059 #32487 #28376 #27942 #33316 #33663 #35068 #34747 #23636 #32564 #34099 #28859 #24928 #34238 → `budgets-spend.md`
- Access model: #34296 #31966 #31438 #34998 #25222 #21102 #26420 #25550 #28464 #23850 #33030 #33080 #27536 #21935 #33636 → `access-model.md`
- Config/DB: #30771 #31968 #27852 #33168 #31836 #32106 #28168 → `config-db.md`

## Triage procedure

1. Pin the deployed version (`GET /health/readiness` → `litellm_version`).
2. Match symptom against the tables; for "closed" issues, confirm a fix PR is linked and `git merge-base --is-ancestor` the fix into the deployed tag before ruling it out.
3. For anything budget/spend: reproduce against `/spend/logs/v2` + DB truth before trusting counters.
4. Ignore LLM-spam comments in threads (recurring poster: IgorGanapolsky) when assessing maintainer acknowledgment.
