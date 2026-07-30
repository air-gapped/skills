# Known-issue catalog — Redis/Valkey-relevant, BerriAI/litellm

Issue sweep 2026-07-30. States are as of that date; LiteLLM's tracker moves fast (~1,566 open issues; a stale bot closes real bugs — "closed" ≠ "fixed" without a linked PR). Several threads carry LLM-generated spam comments (notably user IgorGanapolsky) — do not mistake those for maintainer acknowledgment. Maintainers acknowledge the area: #30484 "LiteLLM Stability Sprint Roadmap" (OPEN, 2026-06-15) lists "Spend Tracking and Budgets" and "P0: Virtual key spend limits are not being enforced".

## Rate limiting (v3 parallel_request_limiter) — multi-instance accuracy

| Issue | State | Impact |
|---|---|---|
| #34534 | OPEN (07-24) | Every MCP tool call permanently leaks a `max_parallel_requests` slot; key wedges into 100% 429s; only restart (or 3600s TTL) clears |
| #34140 | OPEN (07-21) | v3 double-counts team per-model descriptors → effective RPM/TPM is **half** configured; confirmed on main |
| #27736 | OPEN (05-12) | Deployment-level TPM per-pod (RPM batch-syncs since #9357, TPM doesn't) → ceiling `tpm × N` |
| #24677 | OPEN (03→07) | TPM fires ~30% below configured, 2–5 min cooldown; recurrence of "fixed" #18953 |
| #32232 | OPEN (07-06) | SCRIPT-blocking proxies (Codis/Twemproxy) → silent per-pod fallback; fix PR #32230 pending |
| #27748 | OPEN | `x-ratelimit-*` headers dropped on streaming responses |
| #27900 | OPEN | `global_max_parallel_requests` not enforced |
| #28991 / #35197 | OPEN | Internal `_litellm_*` reservation fields leak to upstream providers (chat + /v1/responses); recurring (#30544, #28146 closed earlier) |
| #34728 / #32865 | OPEN | /v1/responses token accounting: reserves 1 token / massively over-estimates base64 images |
| #27738 | closed 06-10 | Embedding/TextCompletion/Responses never counted toward TPM — fix version matters |
| #14820 | closed | v3 requests failed outright when Redis down (now: silent fallback instead) |

## Spend / budget counters (§spend-drift)

| Issue | State | Impact |
|---|---|---|
| #30460 | OPEN (06-15) | Redis spend counters inflate over time (multi-pod + ElastiCache timeouts; Redis=50 vs DB=14) → false BudgetExceededError; flush fixes for hours |
| #26233 | OPEN (04-22) | Any key in `cache_params` suppresses `REDIS_*` env for the usage cache → silent in-memory spend tracking |
| #34238 | OPEN (07-23) | End-user budget bypass via stale per-pod fallback after Redis clean miss |
| #26239 | OPEN (04-22) | Team-key spend also increments personal user spend (maintainer: intentional, default changed ~1.94) |
| #26672 | OPEN | Key/user max_budget not enforced on fresh v1.82.3 deploys (regression from v1.81.0) |
| #27735 | OPEN | BudgetExceededError on stale spend while `/key/info` shows under-budget |
| #33321/33323/33325/33330 | OPEN (07-15) | Family: admission at exact limit; `max_budget_limiter` fails open on lookup errors; `model_max_budget` reads pod-local spend; soft budgets use stale spend |
| #32614, #34732, #34733 | OPEN | Races: budget sync overwrites memory with stale Redis; concurrent window resets bypass caps |
| #33872 | OPEN (07-18) | Redis spend buffer loses dequeued transactions on DB commit failure (silent loss) |
| #33923 | closed 07-23 | `fail_closed_budget_enforcement` didn't reject failed atomic reservations — flag is only trustworthy after this fix |

## Connections / TLS / config parsing

| Issue | State | Impact |
|---|---|---|
| #34614 | OPEN (07-25) | v1.93.0 + redis-py 5.3.1: `ssl_check_hostname` TypeError kills cache and budget counters; reproduces on Valkey |
| #16587 | OPEN | Presence-based check makes `ssl: False` force `SSLConnection` — breaks non-TLS Redis |
| #34727 | OPEN [Docs] | Caching docs still warn "don't use REDIS_URL in prod (perf)" — stale since ~v1.95 (measured url 650 vs host/port 690 req/s, both 50 conns); URL mode still silently drops kwargs set outside the URL string |
| #34299 | OPEN | `RedisCache.async_set_cache` swallows exceptions → circuit breaker never learns from writes |
| #20231 / #19724 | closed | Socket-timeout override; init connection-storm race |

## Caching correctness (affects coordination only when client is shared)

#31610 OPEN semantic cache broken; #28778 OPEN tool-return content lost with semantic cache; #32318 OPEN cache debug logs never emitted; #29955 OPEN no per-team cache scoping (cross-tenant reuse); #32068 OPEN reasoning_content lost on streaming cache hit; #27852 OPEN deleted models ghost in other workers (no cross-pod invalidation); #34681 OPEN DualCache evicts fresh Redis batch-throttle entries. Closed with fix versions: #29414 cache key embedded full payload (huge keys/timeouts), #25962 semantic-cache init failure crashed proxy (now degrades, 07-25), #18641 caching persisted despite `cache_responses: false`.

## Cluster / Sentinel

See `cluster-sentinel.md` for the full lists: #25447 (cross-user cross-talk, OPEN, Critical), #30065 (Azure Redis Enterprise CROSSSLOT), #28379 (GCP IAM + cluster), #31206, #27982; sentinel closed set #20734/#21197/#10276; cluster closed set #25049/#27919/#22748/#8878/#15066.

## Valkey

#29121 (feature, closed 06-20) drove valkey-search semantic cache; #32324 (OPEN but reportedly fixed on main via PR #32295, ≥v1.92) `_get_async_embedding` kwargs bug; #16207 (closed) ElastiCache-Valkey float version parse; #11243 (closed 2025-09) Redis/Valkey backend didn't initialize in v1.71.x; #34614 reproduces on Valkey. Docs: zero mentions.

## Reading the tracker

When triaging a symptom against this catalog: check the deployed tag first (`litellm --version` / image tag), then search linked PRs on the issue — stale-bot closures (#22796, #25495-style) have no fix commit. `gh issue view N --repo BerriAI/litellm --json title,state,closedAt,comments` and look for a `fix(...)` PR cross-reference before believing a "closed".
