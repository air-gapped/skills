# Improvement backlog — ansible-idrac-9-10

Work-not-done log from the skill-improver APPLY pass on 2026-05-28
(baseline self-score 89/100 → 93/100). Only items actually attempted as
hypotheses but not fully resolvable in one atomic iteration, plus items
deliberately left for evidence reasons, are listed under Open.

## Open

*(none — both carried items closed on the 2026-07-21 freshen; see below.)*

## Resolved — 2026-07-21 (freshen)

- **WS-MAN-removed-on-17G was single-sourced** — closed. Re-probed and found a
  second on-the-record Dell source (community roadmap thread, Dell employee
  ajay_shenoy 2023-02-28: "WSMAN will be 'removed' in iDRAC10/17th Generation…
  DCIM view classes will not be supported"). Claim text in `troubleshooting.md`
  #13 held unchanged; a dated `sources.md` row now carries the corroboration
  *and* the caveat that it is a roadmap statement, not a shipped-product one.
  The Redfish-enhancements whitepaper (dl.dell.com) 403s to unauthenticated
  fetch — if a future pass gets at it, that would be the definitive source.
- **`troubleshooting.md` #2 soft "post-10.0.1" phrasing** — closed. Now states
  ≥ 10.0.2 already contains the fix, with both merge dates (PR #1061
  2025-11-12, PR #1034 2025-09-23) against v10.0.2's 2026-04-01 publish date.
- **New upstream bug → `troubleshooting.md` #17**: `redfish_powerstate`
  `oem_reset_type` gates on an iDRAC 9 firmware string (`7.00.60`), so iDRAC 10
  (`1.xx`) boxes are *skipped* rather than power-cycled. Upstream #1103, filed
  2026-06-09, no maintainer response. Includes the `uri`-module workaround and
  a warning that skip-not-fail means playbooks march on against a live host.
- **Collection v10.0.2 → v10.0.3** (2026-06-23) — maintenance only (galaxy.yml
  build excludes, pytest bump, README); recorded in `sources.md`, minimum-version
  pins deliberately left at 10.0.2 since no module behavior changed.
- **iDRAC 10 firmware line moved** — the cheat-sheet's "Current Recommended:
  1.30.10.50 (Mar 2026)" is now per-platform (1.30.30.50 / 1.30.31.10 etc.,
  Jun 2026); reworded to keep 1.30.10.50 as the BasicAuthState cutover and
  point at KB 000305325 for the per-model Recommended build.
- KB 000437501 restamped (last modified 2026-05-24 → 2026-07-17); the
  BasicAuthState cutovers (iDRAC 9 ≥ 7.30.10.50 / 14G 7.00.00.184 /
  iDRAC 10 ≥ 1.30.10.50) re-verified unchanged.
- Logged (no mutation): issue #1102, OIDC workload-identity feature request —
  out of scope until it ships.

## Resolved — 2026-05-28

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

### Prior-pass items (context for the two closed above)

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
