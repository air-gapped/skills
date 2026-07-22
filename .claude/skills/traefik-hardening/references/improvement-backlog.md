# Improvement backlog — traefik-hardening

## Open

- **Dim 1 — full trigger set won't fit the 1,536-char listing cutoff.** Combined `description`+`when_to_use` = ~1,934 chars. After the iter-11 reorder, the core positives + symptoms + the "Do NOT" guard land within 1,536, but the JA3/air-gap trigger *phrases* and the "choose where to cap" clause sit past it (their concepts are covered in `description`, which is fully within cutoff). iter-7 proved a trim-to-fit stays over 1,536 (1,564) while deleting symptom+intent coverage — net negative. Closing fully needs an author decision on which trigger phrases to sacrifice vs. accept tail-truncation. File: `SKILL.md:6`.
- **Dim 6 — single-leader / fan-out topology caveat repeats across 4 files.** Appears in `SKILL.md` (decision-flow step 4 + quick-map), `references/middleware-primitives.md` (InFlightReq), `references/deployment.md` (counting-trap section), and `references/known-products/open-webui-api-abuse.md`. Partly intentional (each file needs the caveat in its own context), but a canonical treatment in `deployment.md` + one-line pointers elsewhere would cut ~15 lines. Multi-file restructure; author call on whether the reinforcement earns its place.
- **Dim 9 — JWT plugin version/config left as `v<latest>` placeholder.** `references/identity-keying.md:27` intentionally does not pin a version (operator picks the plugin and pins at install). Making it concrete would require an online probe of the plugin's Releases (freshen-style), not a score-loop mutation — and hardcoding a number risks staleness. Run `freshen` if a pinned reference example is wanted.

## Resolved this pass — 2026-07-22 (baseline 75/76 → 88)

- Dim 9 hard-fail: `description` was 1,671 chars (> 1,024 spec cap) → rebalanced to 842, triggers moved to `when_to_use` (iter 1).
- Dim 9 staleness: added `references/sources.md` with per-row `Last verified: 2026-07-22` stamps → cap lifted (iter 2).
- Dim 3: eliminated all second-person across SKILL.md + references, including 2 capitalized "You" a case-sensitive grep missed (iters 3, 4, 10).
- Dim 6: de-duplicated the period-default / streaming / per-pod gotchas (already in the quick-map) so Load-bearing = cross-cutting traps only (iter 5).
- Dim 4: added a "Verify the limits actually fire" section (curl concurrency/rate probes, fairness + false-positive checks, the 429-metric alert) — the skill previously had no validation step (iter 9).
- Dim 1: split description/when_to_use and reordered so symptoms + the "Do NOT" negative guard fall within the 1,536 listing cutoff (iters 1, 11).
- Discards (ceiling-mapping): iter 7 (trim when_to_use to fit 1,536 — stays over while losing coverage); iter 8 (remove "How to use" section — carried a unique product-quarantine instruction, wash/loss).
