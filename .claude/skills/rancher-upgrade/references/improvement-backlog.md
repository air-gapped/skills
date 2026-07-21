# improvement-backlog — rancher-upgrade

Cross-run memory for `skill-improver`: read at the start of each run, updated at the end.
**Open** = issues the loop *attempted as a hypothesis and could not apply in one iteration*
(ceiling discards, multi-file restructures). Open is NOT a wishlist. **Resolved this pass** =
changes that actually landed.

## Resolved — 2026-07-21 (freshen)

- **Version state re-grounded per House Rule #8** (enumerate-and-derive, no
  candidate named in any query). Four active minor lines, all patched
  **2026-06-29**: 2.11.15 / 2.12.11 / 2.13.7 / **2.14.3**. `releases/latest`
  reports v2.14.3, which is genuinely also the highest stable minor — checked
  rather than assumed. v2.15 is in **alpha** (v2.15.0-alpha21), not RC.
- **EOL table re-verified** against endoflife.date: all four dates unchanged.
  Added the consequence the table alone doesn't surface — **2.11 goes EOL
  2026-10-24**, ~3 months out, and 2.11 is this skill's *floor*. An operator
  starting the one-minor-at-a-time ladder from 2.11 is starting from a version
  that leaves support before the ladder plausibly finishes. **2.10 is already
  EOL** (2026-06-19).
- **Two new grounding traps written into `lifecycle.md` § Grounding**, both
  observed this pass:
  1. **`isPrerelease` is not trustworthy in the Rancher org.**
     `rancher/turtles` publishes `v0.25.6-rc.1` and `v0.26.4-rc.2` with
     `isPrerelease=false` — an `isPrerelease==false` filter reports an RC as
     stable. Added a jq filter that matches the tag string as well.
  2. **Component repos currently have no recent stable tag at all.** The top of
     the release list for `rancher/fleet`, `rancher/backup-restore-operator`
     and `rancher/turtles` is entirely RCs. This reinforces the existing
     guidance to read component→minor binding from the `rancher/charts`
     `release-v2.X` branch: the component repo answers "what exists", not
     "what ships with 2.14".
- **Deliberately not added:** a snapshot of per-minor chart/component versions.
  The skill's own House Rule #8 names those as the #1 fabrication risk and
  requires grounding at use time; pinning them here would manufacture the stale
  authority the rule exists to prevent. The *method* is what got pinned.


## Open

- **Dim 6 (Simplicity) ceiling — the cross-cluster ordering rule is stated at three altitudes.**
  Iteration 6 (2026-05-30) attempted to dedup it and **discarded**. "Management Rancher before any
  downstream k8s *minor* bump" appears as a mental-model concept (SKILL.md § two coupled axes), a
  workflow step (SKILL.md §4), standing House Rule #5, and once in `prereqs-and-ordering.md`. Each
  has a distinct function — concept / procedure / compaction-surviving standing rule
  (improvement-pattern 3.2) — so a one-line collapse loses force with no score gain (blind validator
  scored Dim 6 = 8, "non-repetitive"). Breaking past 8 needs an author decision on collapsing to one
  canonical statement + cross-refs across ≥3 locations — a restructure, not a single-iteration mutation.

## Resolved this pass (2026-05-30 · improve + freshen · blind 81 → 92, self 76 → 90)

- Dim 9 hard-cap removed: `description` 1656 → 973 chars, split into `description` + `when_to_use`.
- Dim 9 staleness cap removed: added `references/sources.md` (14 rows, `Last verified: 2026-05-30`).
- Dim 1: combined `description`+`when_to_use` trimmed 1632 → 1514 (under the 1536 listing cap).
- Dim 3: removed the single second-person slip.
- Dim 4 / Dim 5: added a plan-output shape to SKILL.md §5.
- **cert-manager 2.11/2.12/2.13 — resolved (no longer UNVERIFIED).** Probed the SUSE support matrix
  (no cert-manager row) → derived the ranges instead by intersecting the two grounded k8s-window
  files: 2.11→cert-manager 1.17–1.18, 2.12→1.18–1.19, 2.13→1.19–1.20 (`prereqs-and-ordering.md`).
- freshen: no-op confirmed — `releases/latest` unmoved (`v2.14.2`), sources fresh (0 days).

## Companion follow-ups — DONE (in `k8s-components-checker/references/compat/rancher.md`, 2026-05-30)

- Added the air-gap CAPI `capi-controller-manager` 2.13 blocker (#52816) to the § 2.13 Breaking list.
- Clarified the Google OAuth fix: main issue #54387 + v2.14 backport #54416 (both CLOSED, gh-verified).
  (The Fleet "off-by-one" the doc-research flagged was NOT a change — that file was already correct.)
