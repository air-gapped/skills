# Budgets and spend — semantics, traps, drift

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29). Issue states @ 2026-07-30. Maintainer context: #30484 "Stability Sprint Roadmap" (open) lists "P0: Virtual key spend limits are not being enforced" — this whole area is acknowledged unstable.

## Two budget mechanisms, not one

1. **`max_budget` + `budget_duration`** — classic columns. Setting `budget_duration` computes `budget_reset_at`; clearing nulls both (`key_management_endpoints.py:1925-1935`). The ResetBudgetJob resets on schedule — for *some* entity types (below).
2. **`budget_limits`** — plural concurrent windows, a separate JSON column (`:1937-1951`). Its OpenAPI schema documents **wrong field names** (`budget_limit`/`time_period` vs actual `max_budget`/`budget_duration`, #32695 open).

## The unset problem

- `budget_limits: []` → 200, **silently ignored**; `null` → 400; omission → ignored (open #28021). No removal path short of a new key (or absurd max_budget).
- `budget_duration: null` doesn't clear it either (#27734 closed variant).
- On `/team/member_update`, `max_budget_in_team: null` leaves a **null budget row → every subsequent request from that team's members fails 401/Pydantic** (#29066/#30437 open; #25508's orphaned-row variant closed). Never send it.

## Update ≠ reset

Applying `budget_duration` to an existing key/user/team via update does **not** reset carried spend — the entity starts its "fresh" window already over budget → instant 429 (#34492 open, #34270 dup). The update path is inconsistent with both the create path and ResetBudgetJob. Workaround: `POST /key/{key}/reset_spend` first (in-path key; note `/key/regenerate` is premium-gated), or recreate.

## Per-entity-type inconsistencies

| Aspect | Inconsistency |
|---|---|
| Limit boundary | team check uses `>` while key/org use `>=` (`_team_max_budget_check`, #28020 open) — teams admit at exact limit (#33321 open family: team/end-user/tag/model all admit at limit) |
| Resets | organizations were simply omitted from ResetBudgetJob (#25495 — **closed as stale, not fixed-confirmed**); tag budgets never reset (#27481 open); `max_end_user_budget_id` ignores resets (#24675 open); auto-created end-users never get their budget_id persisted (#25386 open) |
| Reset timing | `model_max_budget` shares one window start across models/durations (#33326 open); `litellm_settings.timezone` skews window resets (#34896 open); large s/m/h durations compute wrong reset times (#17993 open) |
| Enforcement | `model_max_budget` for customers not enforced at all (#31842 open); project spend never tracked → project budgets never enforce (#33871 open); `max_budget_in_team` not enforced (#19105, open since Jan 2026) |
| `soft_budget` | alerts only, never blocks (`utils.py:5773-5820`); on `/team/new` must be strictly `<` max_budget or 400 (`team_endpoints.py:1043-1050`) |

## Team spend vs personal budgets (behavior change ~v1.94)

Team-key spend **also increments the member's personal user spend by default** — maintainer-confirmed intentional after #26239 ("we changed the default in 1.94 rc"). Consequence: users with personal budgets get `BudgetExceededError` on personal keys because of team usage. The opt-out `skip_user_budget_on_team_key: true` **does not work** (#35076, open, reported 2026-07-30). Plan budgets assuming personal spend includes team-key spend on ≥1.94.

## Member budgets: clone-on-write + auto-disconnect

- Team-member budget rows pointing at the team's shared default **fork on first edit** (`management_helpers/common_utils.py:490-499`) — later changes to the team default no longer reach that member.
- A member budget row is **auto-disconnected when no meaningful limit remains** (`:412-423`, `:476-478`, `:506-509`), silently reverting the member to team default; `_is_set_budget_value` treats `[]` as unset (`:415-416`). Only fields in `_TEAM_MEMBER_BUDGET_LIMIT_FIELDS` (`:400-409`) count as "meaningful".

## Scope composition: AND, not precedence

`parallel_request_limiter_v3.py` builds an independent `RateLimitDescriptor` per scope — key, team, team-member, user, org, end-user/customer, `model_per_key`, `model_per_organization`, `tag_per_key`, `mcp` (`:790-830`, `:1580-1700`) — and enforces **all of them**. Effective limit = minimum across scopes; a 429 or BudgetExceededError does not name the tripping scope (read `x-ratelimit-*` headers — though they're dropped on streaming, #27748 open). Budgets likewise: key, team, member, user, org, customer, tag budgets are independent rows all checked.

## Spend numbers: eventually consistent, lossy, both directions

- Enforcement uses cached counters that can exceed DB truth → false 429 while `/key/info` shows under-budget (#27735 open); or lag it → admission despite over-budget (#26672 open, fresh v1.82.3 deploys). Redis counter inflation on multi-pod: #30460 open (see litellm-valkey skill).
- **Silent spend-log loss** (all open): batches dropped on DB write failure (#33873), Redis buffer loses dequeued transactions on commit failure (#33872), rows lost on cancelled flush (#34820), in-memory buffers dropped on shutdown (#34805), GC race loses streaming Responses-API logs (#31059), success-logger crash → request uncharged (#32487), rows dropped on non-unique provider response IDs (#28376).
- Attribution gaps: Azure Model Router logs the router model not the selected one (#27942), Vertex passthrough batch cost unattributed (#33316), **org-level `spend_logs_metadata` silently ignored** — only key/team merge (#33663), failed requests lose call_type/router metadata (#35068).
- Privacy mismatches: `store_prompts_in_spend_logs: true` may still persist `messages` as `{}` (#34747) and UI viewers can't see request/response data anyway (#23636/#32564/#34099/#28859); `false` still stores full embedding **vectors** (#24928).
- `fail_closed_budget_enforcement: true` (documented, `users.md:737-746`) only became trustworthy after #33923 (closed 2026-07-23) — before that it failed open despite the flag.

## Operator rules of thumb

1. Set budgets at **create** time; treat post-hoc `budget_duration` addition as "reset spend first, then update".
2. To *raise* a budget: update `max_budget` only, minimal body. To *remove* one: recreate the entity — don't fight the unset bugs.
3. Reconcile spend against `/spend/logs/v2` + the DB, not the enforcement counters; expect the counters to disagree.
4. Alert on `BudgetExceededError` rates, not just occurrences — a step change fleet-wide usually means counter drift, not user behavior.
5. On ≥1.94, model personal budgets as (personal + team) spend until #35076 is fixed.
