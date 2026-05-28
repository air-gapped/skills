# Improvement backlog — ansible-idrac-9-10

Work-not-done log from the skill-improver APPLY pass on 2026-05-28
(baseline self-score 89/100 → 93/100). Only items actually attempted as
hypotheses but not fully resolvable in one atomic iteration, plus items
deliberately left for evidence reasons, are listed under Open.

## Open

- **WS-MAN-removed-on-17G claim is single-sourced / unverifiable** — Dim 9
  — `SKILL.md` (description + decision tree), `references/idrac-10-deltas.md`
  §2 table + §13-equivalent, `references/troubleshooting.md` #13. The
  claim is sourced only from the iDRAC 10 Attribute Registry; a 2026-05-28
  web probe returned ambiguous signal (one low-quality snippet listed
  WSMan as still available for 17G) and no authoritative Dell page either
  confirmed or contradicted removal. Left unchanged per freshen discipline
  (do not guess on a single ambiguous source). Re-probe on next freshen
  against the iDRAC 10 Security Configuration Guide / a definitive Dell KB;
  if removal is confirmed, add a dated sources.md row; if contradicted,
  soften to "WS-MAN deprecated / not a default protocol on 17G."

- **`troubleshooting.md` #2 still uses soft "post-10.0.1" phrasing for the
  sensor-URI fix** — Dim 9 — `references/troubleshooting.md` #2 ("Upgrade
  collection to ≥ 10.0.2 + post-10.0.1 fix (PR #1061, PR #1034)"). PRs
  #1061 (merged 2025-11-12) and #1034 (merged 2025-09-23) both predate
  v10.0.2 (published 2026-04-01), so the recommended pin already contains
  them — same soft-claim shape that Iter 4 fixed for #4. Not applied this
  pass: it was outside the five ranked hypotheses and needs its own
  verified-by-gh edit confirming both PRs shipped in 10.0.2 (and whether
  #1088/#1039/#1017 add later follow-ups). Low effort next pass.

## Resolved this pass

- Dim 6: deleted the ~36-line duplicate canonical-session YAML from
  `auth-and-session.md`, replaced with a pointer to SKILL.md's canonical
  block (7→8).
- Dim 8: added dated source row for issue #1038 (was cross-referenced from
  SKILL.md and troubleshooting.md #1 but absent from sources.md) (9→10).
- Dim 1: trimmed redundant trigger phrases from `when_to_use` (dropped
  lowercase `idrac10` duplicate and `XE9780/R770/R670 BMC` models already
  in the description), restoring headroom from 15 to 49 chars under the
  1536 listing cap (9→10).
- Dim 9 (freshen): sharpened `troubleshooting.md` #4 — `custom_privilege`
  fix now stated as shipped in collection 10.0.2 (PR #1069 merged
  2025-12-19, v10.0.2 published 2026-04-01), replacing the soft
  "lands post-10.0.1" phrasing (held 9, no regression).
- Dim 2: added top-of-file numbered Contents TOC to `troubleshooting.md`
  (16 patterns) and `idrac-10-deltas.md` (9 sections) so a `head -100`
  partial read surfaces the full section map (9→10).
- Freshen: restamped `Last verified: 2026-05-28` on the re-confirmed rows
  (KB 000437501 — last modified 2026-05-24; Galaxy + Releases — v10.0.2
  still latest), folded the 14G 7.00.00.184 cutover note into the KB row,
  and added a dated row for PR #1069.
