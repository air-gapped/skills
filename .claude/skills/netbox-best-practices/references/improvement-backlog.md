# Improvement backlog — netbox-best-practices

## Resolved — 2026-07-21 (freshen)

**The skill's own refresh trigger did not fire — and that is the finding.**
NetBox is still **4.6.x** (v4.6.5, 2026-07-14) and the chart is still **8.x**
(8.3.37, 2026-07-15). No new minor, no chart major, so every `version-deltas.md`
claim and the v1-token-removal-at-**v5.0** schedule stand unchanged.

- **Version-lookup trap documented.** `netbox-community/netbox-chart` publishes
  **two products into one release stream** — `netbox-<chart>` and
  `netbox-operator-<chart>`. As of 2026-07-21 `isLatest` is
  **`netbox-operator-1.2.128`**, so `gh release view -R
  netbox-community/netbox-chart` returns an *operator* version, not a chart
  version. Recorded the Helm-index query as the correct lookup, since it
  separates the two entries and carries `appVersion`.
  (Fourth distinct shape of this failure found in one freshen run — after
  date-ranked `latest`, RC tags flagged non-prerelease, and parallel-minor
  patching. "How do I find the newest version" is a per-repo question.)
- **`[live]` labels re-scoped, not re-stamped.** They were verified once on
  chart 8.3.14 / v4.6.2 (2026-06-12) and have **not** been re-run; upstream has
  since moved 23 chart patches and 3 NetBox patches. The header now reads
  "observed on 4.6.2" rather than leaving currency implied. Re-running them
  needs the production install, not a public probe — deliberately not faked.
- **Pinned versions annotated** in `SKILL.md`, `helm-chart-gotchas.md` and
  `sources.md` with the upstream delta plus the explicit "no delta invalidated"
  conclusion, so a future reader can tell *checked-and-unchanged* from
  *not-checked*.


## Open

- **HA/replicas/media-persistence coverage** (Dim 5) — netbox-chart replicas >1
  requires RWX media storage (or S3-style media backend); chart issues track
  upgrade-path and securityContext recurrences. Needs researched, verified
  content (chart issues sweep + a live multi-replica test) — not a
  single-iteration mutation. Source candidates: netbox-community/netbox-chart
  issues; deep-research run 2026-06-12 flagged this as its open question.
- **No eval set → Dim 10 capped at 8** (Negative-Transfer Gate). Both blind
  passes on 2026-08-20 named this as the only route past the cap. Blocked on a
  measurement, not on writing: needs `evals/evals.json` plus a with/without
  `benchmark.json` producing a real `delta_pass_rate`. Note `knowledge-claims.json`
  does NOT qualify — it is claim extraction, not a KNOWS/UNKNOWN/CONFLICTS floor
  probe.

### Unblocked work available to the next pass (NOT blockers)

These are next-iteration hypotheses, recorded because the 2026-08-20 pass
stopped on operator scope rather than on a rubric stop condition. Nothing
external prevents them.

- **Second-person sweep in references** (Dim 3, currently 7 — the lowest
  dimension in the final blind, and its own recommended next fix). ~19
  instances across `sso-hardening.md` (`:57`, `:132`, `:142`) and
  `helm-chart-gotchas.md` (`:186`, `:359`): "you must", "your function",
  "you don't need". SKILL.md itself is clean; only the references slip.
- **PKCE-off-by-default duplicated near-verbatim** (Dim 6) across
  `helm-chart-gotchas.md:359-370` and `sso-hardening.md:132-141`. Deletion
  candidate — merge to one location and cross-reference.
- **`[live]` labels pinned to chart 8.3.14 / NetBox v4.6.2** while upstream is
  chart 8.3.57 / v4.6.8. Inside the 90-day window so no Dim 9 cap fires yet;
  `sources.md` already flags it as the next freshen target.

## Resolved this pass — 2026-08-20

- **`when_to_use` field split** (Dim 1 + Dim 9) — RESOLVED. The June note called
  this "cosmetic today, do it next description edit" at 866 chars. It stopped
  being cosmetic: `description` had drifted to **1,070 chars, past the 1,024
  spec hard max**, hard-capping Dim 9 at 3. Split into `description` 654 +
  `when_to_use` 351 (combined 1,005, inside the 1,536 listing cap). Self Dim 9
  3→9, Dim 1 6→8. Both blind scorers independently named this the single
  highest-impact fix, each having measured the length with
  `skill-improver/scripts/frontmatter-lengths.py` rather than estimating it.
  Lesson worth carrying: a "cosmetic" frontmatter item can silently cross a
  hard cap as the field grows — it is worth re-measuring, not re-reading.
- **Intro said "three areas" and listed four** (Dim 8 8→9). Kept under the
  noise-zone rule: a bare +1 with no simplification, re-checked cold on the
  affected dimension, where it reproduced.

**Pass record (2026-08-20, commit d7da2e5).** 2 iterations, 2 keeps, 0
discards. Self 73 → 83 cold; blind 78 → 86. Anomaly gate fired on iteration 1
(+8 ≥ +5): cold rescore of all ten dims gave 83 against delta-math 82, inside
the 2-point tolerance, so the delta stood. Scorer was Sonnet 5 (pinned in the
`blind-scorer` agent frontmatter as of 2026-08-20). **Stopped on operator
scope, not on a rubric stop condition** — no ceiling was mapped and zero
discards were logged, so this pass has NOT established that the skill is near
its ceiling.

## Resolved this pass — 2026-06-12## Resolved this pass — 2026-06-12

- sources.md created, all rows stamped 2026-06-12 (Dim 9 cap 6 → 9).
- Token section deduplicated against official netbox-labs:netbox-api-integration,
  then made runnable again per final blind feedback (curl + credential assembly).
- Overbroad description catch-all ("any NetBox deployment/bootstrap/CI
  question") narrowed.
- Second-person occurrences → 0; ToC added to helm-chart-gotchas.md.
- Cross-skill deferral given an internal fallback (version-deltas.md §4.5).
- Scores: self baseline 78 → blind baseline 83 → blind final **91/100**
  (no self-vs-blind dimension gap ≥2 at baseline; final issues all addressed
  or backlogged).
