# Improvement Backlog — chat-completions-api

Carried across skill-improver runs.

## Resolved — 2026-09-15 (the completions shutdown, named and dated precisely)

- **Date re-verified against the live deprecations page: 2026-09-28, unchanged**,
  and now **13 days out**. The claim was correct; what it lacked was specificity.
- **Named the four shutdowns**, all replaced by `gpt-5.6-terra`:
  `gpt-3.5-turbo-instruct`, `babbage-002`, `davinci-002` — the three
  `/v1/completions` models — plus `gpt-3.5-turbo-1106` (a chat model sharing the
  date).
- **The fine-tuned variants are on a later date**: `ft-babbage-002` and
  `ft-davinci-002` shut down **2026-10-23**, roughly four weeks after. A fleet
  running a fine-tune does not lose it on the 28th, and migrating on that
  assumption would be premature — precisely what the general phrasing hid.
- **The paragraph now declares its own expiry**, per half, so the next pass gets
  an instruction rather than a judgement: after 2026-09-28 the first-party
  completions surface is gone and the tense must change; after 2026-10-23 so must
  the fine-tune line.
- Recorded for whoever re-probes: the deprecations page is **JS-rendered**, so a
  plain fetch returns markup — strip tags and search the text. Two attempts were
  wasted on that here.

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
