# Improvement Backlog — chat-completions-api

Carried across skill-improver runs.

## Open

(none — the run converged with zero discards; no attempted mutation failed
to apply)

Noted-but-not-attempted blind finding, recorded for a future run's
consideration (NOT an Open item per backlog rules): final blind scorer
docked Dim 4 because "structured outputs / json_schema on local servers"
and "legacy completions / FIM" triggers have facts (matrix rows, gotcha #6)
but no step-by-step procedure. A compact 4th procedure is appliable in one
iteration if a future pass wants the Dim 4 point; weigh against SKILL.md
length (currently ~145 lines).

## Resolved this pass — 2026-07-19 (improve+freshen, baseline 88 self / 89 blind)

- Iter 1 (style): 2 second-person phrasings → imperative (SKILL.md:39, :119;
  blind-flagged). (+1, Dim 3)
- Iter 2 (actionability): expected-output validation added to the sanity
  curl (object type, non-null content, finish_reason `stop` OR `length`,
  error-envelope caveat). (+1, Dim 4)
- Iter 3 (progressive disclosure): Contents ToC added to cloud-compat.md —
  the only >100-line reference lacking one. (+1, Dim 2)
- Freshen: no-op by construction — all sources.md rows probed and stamped
  2026-07-19 (same-day build from live fetches + HEAD clones); nothing
  stale to probe.
- Post-blind sweep (both blind agents converged on these):
  - Frontmatter dedup — removed the NOT-clause duplicated verbatim in
    `when_to_use` (kept in `description`, which lists earlier); combined
    listing text 1459 → ~1390 chars, widening dynamic-budget headroom.
  - Cline freshen probe (gh api, cline/cline@main): the "training
    knowledge" claim was STALE — Cline's modern llms SDK uses
    `@ai-sdk/openai-compatible` (`includeUsage: true`) + a middleware
    splitting images out of tool messages (CC wire can't carry multimodal
    tool messages); official-openai-SDK usage is the classic extension
    path. clients.md §Other clients rewritten as source-verified;
    sources.md row added.
- Scores: baseline 88 self / 89 blind → **final 91 self / 91 blind** (exact
  agreement; no dimension with 2+ gap at either checkpoint). Loop stopped
  on the 90+ criterion after 3 kept iterations, 0 discards, plus the
  post-blind sweep.
