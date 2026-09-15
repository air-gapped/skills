# Improvement backlog — postgres-operator-cloudnative-pg-migration

Carries ceiling findings across skill-improver runs. Append-only history.

## Open

## Decided — do not re-propose

- **Dim 10 capped at 8 by design** (Dim 10). No `delta_pass_rate`: `evals/`
  has 8 cases but no with_skill/without_skill benchmark pair. This is the
  documented resting state, not a defect — clearing it costs a measured
  benchmark run and should be a deliberate decision, not a reflex to a cap.

## Unblocked — actionable

- **SKILL.md <150 lines for Dim 2 = 10** (Dim 2). SKILL.md is 192 lines after
  the 2026-08-25 pass trimmed the why-migrate summary. The remaining 42 lines
  cannot come from the same place: what is left in SKILL.md is scan-layer —
  the two walls, the path table, the pitfalls quick index, the reference
  table — and the sibling skill measured this exact trade going negative
  (compressing a SKILL.md block that answered an advertised symptom cost a
  completeness point for four lines). Blocked on an eval benchmark that can
  show completeness held; the corpus has 8 cases but no with/without pair, so
  no `delta_pass_rate` is derivable today.
- **Trigger mode not yet run** (Dim 1, empirical). Frontmatter measures 1,521
  chars against the 1,536 listing cap — verified with a fixed measurement
  script, see below — but fit is not fire rate. Run
  `/skill-improver trigger postgres-operator-cloudnative-pg-migration`. Now
  shares a trigger space with the sibling `postgres-operator-best-practices`,
  so the run must test both directions of confusion, not just this skill's
  recall.

## Resolved this pass — 2026-08-25 (freshen + improve)

Freshen: full sweep, every row probed, 4 drifts found and fixed, 1 exception.
Improve: 3 hypotheses, 1 kept, 1 discarded, 1 reclassified. Self 88 → 89;
blind baseline 87.

Freshen findings:

- Zalando release state bumped to v2.0.2, **and a factual error corrected**:
  the anchor claimed Spilo-17 on the v2 line. `charts/postgres-operator/values.yaml`
  pins `spilo-18:4.1-p2` at both v2.0.1 and v2.0.2, so that claim was wrong
  when written on 2026-07-29, not merely stale.
- **Crunchy #3601 is open, not closed** — filed 2023-03-08, never closed. The
  file had recorded it closed since creation. Changes what the row means:
  decision.md sets Crunchy aside partly on this image-revocation incident, and
  an issue open for three and a half years is an unresolved posture rather
  than a handled event.
- Instana runbook deep link retired — the pinned `1.0.314` path 302s to the
  docs root; row repointed at the version-agnostic `saas` path and marked as
  the pass's one exception, because IBM client-side-routes `?topic=` and no
  fetcher resolves the page itself.
- Operand-image repo now also builds a PG19 beta ("for testing purposes
  only"), restated in the builds-vs-supports form a prior pass established.
- New pitfall §7b from the Zalando tracker: a scram source below v2.0.2
  re-salts every managed role's verifier every sync cycle (zalando#3170). The
  password is untouched, so direct libpq is fine; verifier-caching
  intermediaries — pgbouncer with `auth_query`, including Zalando's own
  `enableConnectionPooler` — fail twice an hour. Hence: point
  `externalClusters` at the primary, never at `<cluster>-pooler`.

Improve iterations:

- **Discard (pre-mutation)** — deduplicate the pg_hba APPENDS/REPLACES fact.
  The blind scorer named `manifest-map.md` and `backup-chain.md`; the fact is
  actually in `manifest-map.md`, `app-cutover.md` and `pitfalls.md`, and the
  pooler fact it paired with appears in one file only. The real three-way
  overlap serves three purposes — field translation, client impact at cutover,
  severity catalog — which is RELATED_BUT_DISTINCT, the category the dedup
  guidance says to keep. Do not re-propose.
- **Keep** — why-migrate summary compressed 17 lines → 8, every dropped
  specific verified still present in `decision.md` (Dim 6, 201 → 192).

### Correction to the 2026-07-24 record

That pass logged "iter 1: frontmatter 1,834 → 1,521 chars". The file has
measured **1,521 since creation and the frontmatter has never been edited** —
`git log` shows no commit touching it between creation and 2026-08-25. The
1,834 figure was a raw-block measurement, not the folded value the loader
sees. The number it landed on was right; the delta it claimed to have produced
was not.

This surfaced because `frontmatter-lengths.py` reported a 39-char overrun that
did not exist: it parse-gated with YAML and then measured with a regex over the
raw block, counting each continuation line's indent. Fixed in the same session
(skill-improver commit). Fleet impact at the time: 15 skills falsely reported
as over the cap. The baseline blind scorer for this pass made "trim ~39 chars"
its top recommendation — acting on it would have deleted a real NOT clause.

## Resolved — 2026-07-24

Run: 8 iterations, self-score 83 → 91; blind baseline 87, blind final 87
(final blind ran before iters 7–8, whose fixes implement its own top
findings — its Dim 3: 8 and Dim 8: 8 predate those fixes).

- iter 1: frontmatter trimmed — symptom triggers + NOT clause inside the
  1,536 listing cap (Dim 1). See the correction above for what this actually
  measured.
- iter 2: SKILL.md second-person → imperative, 2 spots (Dim 3).
- iter 3: sources.md operand-majors row disambiguated (image repo *builds*
  13–18, CNPG *supports* 14–18) — blind-flagged mismatch (Dim 8/9).
- iter 4: TOCs added to all five >100-line references (Dim 2/7).
- iter 5: backup-chain wall-recap deduplicated, −2 lines (Dim 6).
- iter 6: duplicate rolling-restart entry removed from quick index (Dim 6).
- iter 7: path-chooser PG-floor contradiction fixed — Path A valid from
  source PG ≥10; PG≤13 routes to A or B, not B only (final-blind flag, Dim 8).
- iter 8: 4 second-person slips in references fixed (final-blind flag, Dim 3).

Discards: none — every hypothesis derived from a rubric criterion or a
blind-agent finding and landed. Ceiling not mapped by discard evidence;
the run stopped on the 90+/no-dim-below-7 condition (self 91).
