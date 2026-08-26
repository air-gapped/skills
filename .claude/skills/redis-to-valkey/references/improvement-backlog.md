# Improvement backlog — redis-to-valkey

Carries ceiling findings across skill-improver runs. Append-only history;
keep prior passes' sections dated below the current one.

## Open

None. The two items carried since 2026-07-18 were decisions, not blocked work,
and both are decided below.

## Resolved this pass — 2026-08-26

Run: freshen + improve. Baseline blind 89. Freshen: 27 rows re-probed, stamp
2026-07-18 → 2026-08-26. Improve: 3 iterations, 3 keeps, 0 discards —
**stopped early, no ceiling mapped** (see "Status of the ceiling" below).

### The two July items were decisions, not blockers — both now decided

**1. SKILL.md <150-line restructure — CLOSED, will not do.** Settled by
measuring the file rather than re-attempting the July edit. Body is 169 lines
across 9 sections (frontmatter + title + intro account for the remaining 39,
and the frontmatter is the trigger surface, not compressible content):

| lines | section |
|---|---|
| 36 | Choosing a transfer method |
| 35 | The RDB-version wall |
| 24 | Cutover runbook |
| 18 | Chart selection and values translation |
| 14 | Air-gap and GitOps rewiring |
| 13 | Reconnecting consumer applications |
| 11 | Reference files · 9 Pitfalls quick index · 9 Why this migration exists |

Reaching <150 requires removing 59+ body lines — i.e. the RDB wall, or *both*
the transfer decision tree and the cutover runbook. Those are the three the
frontmatter explicitly promises ("the RDB-version wall", "the two transfer
layers", "a side-by-side cutover runbook") and the two the July entry itself
called non-negotiable in-body. The target is unreachable without breaking the
skill's stated scope, so it is not a deferred task.

Two further reasons not to carry it: a blind scorer independently rated Dim 2
**9/10 at 207 lines**, weighting one-level-deep pointers and per-file
read-when guidance rather than the band boundary; and the 500-line
platform ceiling — the figure that is actually stated as an imperative — is
not remotely in play.

**2. pitfalls.md cross-file dedup — CLOSED, correct as written.** The July
entry had already reached the right analysis ("each file serves a different
read mode: scan-before-execute vs translate-values") and then filed it as open
work anyway. That overlap is `RELATED_BUT_DISTINCT`, which fleet-wide
measurement puts in the 83% of similar-looking content that is correct as
written. Deduplicating it would be the deletion-bias failure, not a fix. The
only thing that would reopen this is a changed role for pitfalls.md.

### Freshen — the finding that mattered

**A safety claim became version-gated.** valkey#2588, the skill's #1
data-destroying pitfall ("a replica FLUSHES its own dataset before discovering
the incoming RDB is foreign"), was fixed by PR #2600, merged 2025-11-19.
Containment proven by tag compare — `diverged` from 8.1.9 and 9.0.5, `behind`
(ancestor) for 9.1.0/9.1.1 — so the hazard is live on 8.x/9.0.x and fixed only
in 9.1.0+.

Two traps in confirming it, both worth repeating on the next pass:

- A probe reported it "fixed" by quoting the issue title, which is a feature
  *request* (`[NEW] Do not flushall during RDBLoad…`), not evidence of a merge.
  Closed-with-a-title is not closed-with-a-fix.
- Release notes would have gotten containment wrong: both #2600 and #2846
  closed well before the 8.x/9.0.x releases shipped and are still absent from
  them. `sources.md` now states tag compare as the required method.

This converges with #2846 (dual-channel/Sentinel, also 9.1.0-only): **9.1.x is
the floor for both known hazards**, which now argues against pitfall #3's
"land on 8.1.x for a rollback window". Both entries say so.

Advice-changing, each verified first-hand before being written:

- **harbor-helm v1.19.2 defaults to `valkey-photon`** — a released chart, not
  just `main`. Harbor #22935 closed, shipped in v2.15.2; no 2.16.0 exists.
- **GitLab 19.0 removed the bundled Bitnami Redis/PostgreSQL/MinIO outright,
  no replacement.** Inverts the GitLab path for a bitnami-exit skill: nothing
  bundled left to migrate, only external Redis/Valkey before upgrading. Two
  probes disagreed on the spike's state; gitlab-org/charts#6227 is closed,
  checked directly.
- Sentry #107394 fixed; Sidekiq's floor is 7.0, not the 7.2 recorded.

Two probe findings **rejected** rather than applied — both would have weakened
a correct claim, and both are now inline exceptions in `sources.md`:
`--redis-sentinel-password` is absent from the oauth2-proxy docs page but real
(19 hits in the repo), and GitLab's `sentinelAuth >= 17.2` gate is no longer
stated in current docs but was not disproven.

### Improve — 3 iterations, all kept

- **iter 1 — keep (simplification).** "Why this migration exists" 212 → 209:
  dropped the hedge ("don't assume the status quo is stable") and the
  adoption-evidence sentence. Neither changed what an agent does; the risk
  model was already one pointer away.
- **iter 2 — keep (simplification).** Chart prose → verdict table, 209 → 206.
  All four charts stay in-body, so this does not repeat July's iter-9 failure
  (which *extracted* frontmatter-promised content and lost Dim 5). "Do not
  adopt" now reads as an instruction rather than a description.
- **iter 3 — keep (correctness; Δ0 on the metric).** Runbook step 6 said
  `DBSIZE` comparison with no per-index bound, while pitfalls #19 *and*
  app-cutover.md both require per-DB verification. An agent executing the
  always-loaded runbook would verify db0, match, and declare success with
  other indexes empty. Step 6 now bounds on "every DB index in use". This is
  the rubric's Dim 8 scattering defect and its Dim 4 "checks existence, not
  coverage" failure in one line, and the metric did not register the fix —
  expected, and why the A/B comparator decides the pass.

### Status of the ceiling

**Stopped early, not ceiling-mapped.** Three iterations, three keeps, zero
discards. A run with no discards has mapped nothing, and this one deliberately
did not spend a discard re-attempting the extraction shape July already
discarded — item 1 was closed by measuring the file instead. The next pass
inherits an open field, not a finished skill.

Dim 10 remains capped at 8 (unmeasured `delta_pass_rate`; 8 eval cases exist
but no with/without benchmark). That cap is a resting state and lifting it
costs a benchmark run — a spend decision, not a defect.

## Resolved — 2026-07-18

Run: improve+freshen, 10 iterations + 1 bonus, self 77→87, blind 81→88.

- iter 1 (freshen F6): created references/sources.md, 27 rows all
  `Last verified: 2026-07-18` with pins; Dim 9 cap 6→9. Freshen probe
  outcome: 0 stale findings (skill authored same day as its research);
  future-probe queries recorded in sources.md.
- iter 2: combined frontmatter 1716→1524 chars — all triggers and both
  NOT-scope clauses now inside the 1536 listing cap (Dim 1 7→8; blind 9).
- iter 3: zero second-person in SKILL.md (Dim 3 7→9).
- iter 4: TOC added to data-transfer.md (Dim 7 8→9).
- iter 5: prose standardized on "master-set name" (SKILL.md,
  app-cutover.md, pitfalls.md #11); literal chart keys untouched (Dim 8 8→9).
- iter 6: SKILL.md pitfalls quick-index deduplicated against in-body traps
  (Dim 6 7→8).
- iter 7: lockdown detail consolidated behind airgap-gitops pointer
  (keep-simplification).
- iter 8: `SENTINEL ckquorum` validation added to runbook step 2 —
  probe-verified against valkey 9.1.0 sentinel.c before mutation (Dim 4 8→9).
- iter 9: DISCARD — extracted the chart-selection/values-translation summary
  to references/chart-migration.md; SKILL.md only reached ~190 lines (Dim 2
  band unchanged) while dropping Dim 5, because the frontmatter promises
  "chart selection tradeoffs" and the extraction moved them out of the
  always-loaded layer. Superseded 2026-08-26: see Resolved item 1.
- iter 10: DISCARD — shortened pitfalls #10/#11 to pointers at
  chart-migration.md; broke the file's standalone pre-execution scan-list
  role and introduced reference→reference chains. Superseded 2026-08-26:
  see Resolved item 2.
- bonus: 3 second-person slips in reference files fixed (final blind
  finding #3).
