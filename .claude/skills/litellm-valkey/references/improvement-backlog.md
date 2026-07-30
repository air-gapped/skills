# Improvement backlog — litellm-valkey

Carries ceiling findings across skill-improver runs. See skill-improver `references/backlog-format.md` for admission rules.

## Open

- **Run `scripts/litellm-redis-preflight.sh` against a real LiteLLM ≥v1.93.0 proxy** — Dim 7. Now execution-tested against a faithful mock server (happy path exit 0, `source: null` exit 2, response shapes mirrored from `coordination_redis_endpoints.py:269-283`), but never against a live proxy. Requires a running deployment with an admin key — author environment.
- **Measure `delta_pass_rate`** — Dim 10 (capped at 8 unmeasured). Requires building `evals/evals.json` and running skill-creator's `aggregate_benchmark` with/without the skill — multi-file, author-decision scope. Flagged by both blind scorers.
- **Frontmatter headroom is 10 chars** (1,526/1,536 combined) — any future trigger addition must trade an existing phrase out or the NOT-for scope guard silently truncates. Not actionable now; guard for future edits (blind-final finding).

## Resolved this pass — 2026-07-30

Initial improve run on the day the skill was authored. Self-score 77 → 87 (cold rescore), 7 kept / 2 discarded iterations:

- Dim 3: 7 second-person sentences converted to imperative (remaining "you" only inside verbatim doc quotes).
- Dim 8: dangling `§spend-drift` anchor fixed (known-issues.md heading now carries the marker).
- Dim 1: combined description+when_to_use trimmed 1834 → 1530 chars (under the 1536 listing cap; NOT-for exclusions no longer truncated).
- Dim 6: SKILL.md Helm paragraph collapsed to a pointer at `coordination-redis.md` §Helm (was near-verbatim duplication).
- Dim 7: preflight script bug — `GET /coordination_redis/settings` returns `values`, not `settings`; jq path fixed after source probe.
- Dim 4: verification step now states the exact response shape incl. `source: null` = per-pod mode.
- Dim 5: added "Migrating a pre-v1.93 borrowed-cache deployment" procedure with the do-NOT-delete-cache_params-first blacklist.

Post-final fixes driven by blind-scorer findings (baseline blind 80, final blind 83, both from independent agents):
- **Crash bug**: `parse()` assigned `STATUS`/`CTYPE` inside a command-substitution subshell → `set -u` killed the script on first use (both blind agents reproduced it by execution; self-review missed it twice). Rewritten as a globals-setting `do_fetch()`; verified live against a mock proxy on both exit paths.
- Script path now uses `${CLAUDE_SKILL_DIR}` (portability, blind-final issue 3).

Discard rationales (anti-re-proposal guards):
- Deleting the "commonly-remembered version" sentence in SKILL.md §Sentinel — no score gain; the sentence is a prior-correction hook matching how operators actually misremember the Sentinel/Cluster split. Do not re-propose as a Simplicity edit.
- Hedge-language sweep — zero instances found; style category exhausted at imperative-flawless-minus-quotes.
