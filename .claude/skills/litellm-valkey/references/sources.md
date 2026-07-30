# Sources — code, docs, issues, verification log

Every claim traces to one of these groups. Load to verify a specific fact or run `freshen` mode.

## Verification log

| Source group | Last verified | Notes |
|---|---|---|
| BerriAI/litellm local clone @ `4d543245` (v1.95.0-dev, 2026-07-29; latest stable tag v1.94.0) | 2026-07-30 | Primary source for every file:line. Full history clone (41k+ commits, 1486 tags) — version claims use `git merge-base --is-ancestor <sha> <tag>`. |
| `coordination_redis` provenance | 2026-07-30 | PR #32661 (block + endpoints), #32635 (env fallback), #32662 (chart/terraform), all merged 2026-07-11; first release tag containing #32661: **v1.93.0-rc.1**, stable **v1.93.0** (merge-base verified). |
| BerriAI/litellm-docs local clone @ `803ee53` (2026-07-30) | 2026-07-30 | Doc-absence claims (`coordination_redis`: zero hits; `valkey`: zero hits) are greps over this corpus; re-grep on freshen. |
| Helm chart `helm/litellm-helm` values.yaml (chart 1.1.1, in-repo) | 2026-07-30 | `redis.sentinel.enabled` / `redis.coordination.enabled` / masterSet rendering read directly from values.yaml comments + structure. |
| GitHub issues (gh CLI sweep) — rate limiting: #34534 #34140 #27736 #24677 #32232 #27748 #27900 #28991 #35197 #34728 #32865 #27738 #14820 | 2026-07-30 | Open/closed states as of sweep. |
| Issues — spend/budget: #30460 #26233 #34238 #26239 #26672 #27735 #33321 #33323 #33325 #33330 #32614 #34732 #34733 #33872 #33923 #30484 | 2026-07-30 | #30484 is the maintainer stability-sprint roadmap. |
| Issues — cluster/sentinel: #25447 #30065 #28379 #31206 #27982 #25049 #27919 #22748 #8878 #15066 #20734 #21197 #22796 #10276 | 2026-07-30 | **#22796 verified stale-closed** (only comment is the stale bot; `gh search prs "22796"` → empty). Do not cite it as "fixed". |
| Issues — connections/valkey: #34614 #16587 #34727 #34299 #20231 #19724 #29121 #32324 #16207 #11243 #3188 | 2026-07-30 | |
| Key source files | 2026-07-30 | `litellm/_redis.py` (client factory, sentinel `:489-536`, logic `:317-448`), `litellm/caching/{redis_cache,redis_cluster_cache,dual_cache,in_memory_cache,caching}.py`, `litellm/proxy/hooks/parallel_request_limiter_v3.py`, `litellm/proxy/management_endpoints/coordination_redis_endpoints.py` (routes `:288`, `:319`, `:390`; source fn `:208-224`), `litellm/proxy/proxy_server.py` (`_init_coordination_redis` `:4070`, `_build_redis_usage_cache` `:3681`, env target `:3700`), `litellm/router.py` (`:500`, `:824-840`), `litellm/router_utils/cooldown_cache.py`, `litellm/router_strategy/{base_routing_strategy,budget_limiter,lowest_tpm_rpm_v2}.py`, `litellm/proxy/db/db_transaction_queue/{pod_lock_manager,redis_update_buffer,db_spend_update_writer}.py`, `litellm/caching/valkey_semantic_cache.py`, `litellm/constants.py`. |

Research provenance: 4-agent pass 2026-07-30 (source map, management-API audit, two issue sweeps) in session litellm-skills; findings cross-checked inline for the coordination/sentinel timeline (issue #22796 stale-closure and v1.93.0 tag containment were verified by hand, not taken from agent output).

## Freshen protocol

1. `git -C <litellm-clone> pull && git log --oneline -5` — restamp the SHA in every reference header if moved.
2. Re-resolve headline line numbers **by symbol name** (`_coordination_redis_source`, `_build_redis_usage_cache`, `CoordinationRedisParams`, `PARALLEL_REQUEST_SLOT_TTL_SECONDS`, `_init_redis_sentinel`) — LiteLLM files shift constantly.
3. Re-check open-issue states: the OPEN list above via one `gh issue list`/`gh issue view` sweep; promote fixed ones into fix-version rows.
4. Re-grep the docs corpus for `coordination_redis` and `valkey` — the "undocumented" claims expire the day docs land.
5. Check whether a `fail_closed` for rate limits appeared (`grep -rn fail_closed litellm/proxy/hooks/`).
6. Re-verify the redis-py pin (`grep redis uv.lock`) — #34614 class regressions ride on it.
