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

- **Dim 10 hard cap at 8 — the skill has never been measured against a no-skill baseline.**
  (new 2026-07-25) The Negative-Transfer Gate caps Dim 10 at 8 while `delta_pass_rate` is
  unmeasured, and it is currently the single binding constraint on the total. Not applicable in one
  iteration: needs an author-written `evals/evals.json` (realistic upgrade-planning prompts with
  assertions), then `python -m scripts.aggregate_benchmark` from the official skill-creator plugin.
  Worth ~+2 if the delta is positive — and a genuine finding either way, given SkillLens measured
  25% of skills as net-harmful.

- **Dim 5 (Completeness) — failure remedies are named-but-unresolved for two watch items.**
  (new 2026-07-25) `per-minor-runbook.md` post-flight steps 10 and 12 tell the operator to *watch*
  for CrashLoop @2.14 and DiskPressure @2.12, but neither carries a remedy — unlike the RKE1 gate
  (#50286) and the BRO rollback path, which both now name executable fixes. Not applied this pass
  because the remedies are **author domain knowledge, not groundable via `gh`**: the field reports
  in this file record both as non-events on the operator's own clusters, so there is no observed
  failure to write up. Needs either a field occurrence or the author's own procedure.

- **Dim 6 (Simplicity) ceiling — the cross-cluster ordering rule is stated at three altitudes.**
  Iteration 6 (2026-05-30) attempted to dedup it and **discarded**. "Management Rancher before any
  downstream k8s *minor* bump" appears as a mental-model concept (SKILL.md § two coupled axes), a
  workflow step (SKILL.md §4), standing House Rule #5, and once in `prereqs-and-ordering.md`. Each
  has a distinct function — concept / procedure / compaction-surviving standing rule
  (improvement-pattern 3.2) — so a one-line collapse loses force with no score gain (blind validator
  scored Dim 6 = 8, "non-repetitive"). Breaking past 8 needs an author decision on collapsing to one
  canonical statement + cross-refs across ≥3 locations — a restructure, not a single-iteration mutation.

## Resolved — 2026-07-25 (improve + freshen · blind 76 → 84 → re-scored after 2 further fixes · 14 iterations, 0 discards)

**Improve (defects the blind baseline caught that the self-score missed):**

- **Dim 8 — `House Rule #8` was dangling in 7 places across 4 files.** The House Rules block ends at
  **#6**; grounding is #3. Repointed all 7; the two legitimate cross-skill refs (#8/#9) are now
  explicitly attributed to `k8s-components-checker`. This was the largest single defect in the skill
  and the self-score had scored Dim 8 an 8 against the blind agent's 5.
- **Dim 8 — `harvester-upgrade` was described as "planned".** It exists. The companion row is now a
  real handoff naming the coupling direction (each Harvester hop gates on the external Rancher
  upgrade this skill plans); the pairing table itself is deliberately *not* restated here.
- **Dim 9 — five reference files stamped their content 2026-05-30 while `sources.md` claimed
  2026-07-21.** Each header now states what this pass re-verified **and, explicitly, what it did
  not** (cert-manager windows, Helm floor, per-minor breaking-change lists, CAPI-contract rows).
- **Dim 2/7 — TOCs added** to the four reference files over 100 lines, per the rubric's
  reference-depth rule. All 15 anchors validated against GitHub slug rules.
- **Dim 6 — a redundancy this run introduced, then removed.** The final blind scorer caught that
  iterations 7/10 told the same "a prior pass's claim reversed in four days" story in three files.
  The caution is now canonical in `lifecycle.md` § Grounding; `sources.md` and
  `capi-turtles-fleet.md` carry one-line cross-refs. Net deletion. **Lesson: a freshen finding that
  changes guidance belongs in exactly one place — the file that owns the guidance — with the probe
  record in `sources.md` reduced to a pointer.**
- **Dim 3 — all 13 second-person occurrences converted to imperative** (SKILL.md + 6 references,
  including one section heading and its TOC anchor, updated together). Verified zero remaining —
  note the 13th (`take the max yourself`) was missed by a `you|your|you're` regex; **match
  `yourself`/`yours` too.**
- **Dim 8 — a self-inflicted contradiction, caught and fixed.** Adding the honest
  "what was NOT re-derived" headers made SKILL.md's closing line ("All version specifics… were
  grounded via `gh` on the date stamped in each file") false. Rewritten to send the reader to each
  file's header first, and to state that a claim under a "not re-derived" disclaimer must be
  re-grounded regardless of the file's headline date.
- **Dim 5/8 — the install-type scope boundary was never stated.** The skill assumes the
  Helm-on-Kubernetes install on every page but never said so, while its triggers ("upgrade Rancher")
  match a **single-node Docker install** just as well — which upgrades by swapping the container
  against its data volume and shares nothing with this runbook. The failure mode was not a missing
  chapter but a *silently wrong confident answer*. Fixed with a scope line in `description`, the
  `NOT for` clause, and a stop-gate in workflow §1 (empty `helm list` = likely Docker install → say
  so and stop). Docker single-node confirmed still a live documented method 2026-07-25. Budget:
  `description`+`when_to_use` re-trimmed to **1529/1536** — every trigger keyword retained.
- **Dim 6 — `sources.md` cut 120 → 57 lines.** It had grown into a second copy of this backlog plus
  ~46 lines of superseded 2026-07-21 state, in an operator-facing reference. It is now a provenance
  index (the dated per-source table) plus a short digest; the narrative lives here, and the prior
  text lives in `git log -p`. **Standing rule for future passes: `sources.md` is the table plus a
  digest — findings prose belongs in this backlog.**

**Freshen (four findings, all evidence-backed; full probe record in `sources.md`):**

- **The community-vs-Prime discriminator command was broken** — the documented
  `--jq '.body' | head -1` matched **0 of 4** probed releases. Community bodies open with a
  `# Release vX.Y.Z` heading and carry the classifier sentence at body line 3 / line 12; only the
  Prime stub is line 1. Replaced with a body-wide grep, verified 4/4. This is House Rule #1's only
  mechanism, so it was silently mis-classifying every community patch.
- **v2.15 moved alpha → RC** (rc1 2026-07-21, rc3 2026-07-24) with `release-v2.15` branches live in
  both KDM and charts. Recorded with the look-ahead consequence and an explicit "do not plan onto it".
- **KDM 2.15 window derived live: 1.34/1.35/1.36**, with k8s **1.33 dropping out** — plus the
  observation that 1.34's max moved `v2.14.99`→`v2.15.99` *between branches*, which demonstrates the
  file's own "windows extend per branch" rule instead of asserting it.
- **BRO #916 is closed with a workaround, not a fix.** Read the closing comment per the
  closed-≠-fixed rule: rollback needs the docs' `cleanup.sh` and then "behaves like a cluster
  migration instead of an in-place rollback". Added verbatim, with the planning consequence.

**Version drift applied:** Rancher 2.14.2→**2.14.3**; Turtles 0.26.2→**0.26.4** (+ v0.27.0 exists,
tracking 2.15); BRO 10.0.4→**10.0.7**; Prime-stub examples 2.11.14/2.12.10/2.13.6→2.11.15/2.12.11/2.13.7.

**New capability found and documented:** two release assets the skill had never listed —
`rancher-data.json` (the KDM bundle, version-locked to that exact release; the cleanest air-gap KDM
source) and `rancher-mirror-to-rancher-org.sh` (a flat `docker pull` list = the exact component
image tags a patch ships). The latter is now a grounding shortcut in `lifecycle.md` § Grounding, and
its output is the cleanest available proof of "the component repo answers what exists, not what
ships": on v2.14.3 **every** shipped tag sits below its repo's newest stable.

**A prior-pass claim reversed in four days.** The 2026-07-21 note that Fleet/Turtles/BRO had *no
recent stable tag* is no longer true — Fleet and Turtles both cut stable tags 2026-07-21–22. The
conclusion it supported (bind via `rancher/charts`) stands and is better-founded; the observation was
a snapshot, not a property. Both superseded claims are marked in place in `sources.md` rather than
deleted. **Lesson for future passes: do not encode a "repo currently has no X" observation as
guidance.** The `isPrerelease` trap from that same pass is still live and was left untouched.

**Deliberately not done:** no 2.15 rung was added to `per-minor-runbook.md`. 2.15 is a prerelease
with no community classifier sentence and no grounded breaking-change list; writing one would
manufacture exactly the fabrication House Rule #3 exists to prevent. Only the *pre-GA state* and the
*live-derived KDM window* were recorded.


## Resolved — 2026-05-30 (improve + freshen · blind 81 → 92, self 76 → 90)

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
