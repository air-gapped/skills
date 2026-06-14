# Improvement backlog — ubuntu-autoinstall

Carries ceiling findings and run history across skill-improver passes. Read in
Phase 0; update in Phase 6. Append-only history — do not drop prior dated sections.

## Open

- **Dim 2 (Progressive Disclosure) capped at 8 by SKILL.md length.** SKILL.md is
  215 lines; reaching 9 needs <150 lines. The over-length comes from inline
  quick-reference blocks (the schema table ~110-133, the Air-gapped essentials YAML
  ~140-161, and storage-quick ~163-174). These carry high always-loaded
  actionability value, so cutting them to references/ is net-negative without a
  restructure that keeps the body equally useful. Needs author judgment, not a
  one-iteration mechanical move. (file: `SKILL.md`)
- **Dim 7 (Resource Quality) capped at 8 — no bundled scripts.** Could add a
  `scripts/build-seed.sh` (genisoimage/cloud-localds wrapper) or a validator-fetch
  helper. Deliberately omitted: the authoritative validator ships upstream in
  canonical/subiquity and `references/examples.md` already has copy-paste commands,
  so a bundled script may be over-engineering. Author decides whether the
  convenience justifies the maintenance surface. (dir: `scripts/`, absent by design)

## Resolved — 2026-06-14 (improve mode)

Self-score 78 → 84 (blind baseline, Opus: 82 — aligned). 5 keeps, 2 discards.

- Dim 3: removed lone second-person slip in the intro ("You provide" → imperative).
- Dim 8: disambiguated `validate-autoinstall-user-data.py` as a subiquity-SOURCE-repo
  script, not a bundled skill resource (flagged by the blind baseline agent — I had
  over-scored Dim 8 at 9; corrected to 7 then fixed to 9). (SKILL.md authoring step 5
  + Validation block)
- Dim 1: split the overloaded `description` into `description` (what) + `when_to_use`
  (triggers); recovered the "local mirror" / "PXE-USB" trigger keywords within the
  1,536 combined cap (description 590, combined 1003).
- Dim 6: removed the air-gapped key enumeration in workflow step 3 (dedup vs the
  Air-gapped essentials section).
- Dim 5: added explicit PXE/netboot delivery to `references/delivery-and-seeding.md`
  (closes the `when_to_use` PXE trigger → body-coverage trace).

**Discard rationales (do NOT re-propose):**
- *Validator exit-code note in SKILL.md* (Dim 4 attempt): duplicates
  `references/validation-and-debugging.md` (exit 0/1, `-vvv`); net-neutral and not
  simpler. The detail is one ref-hop away.
- *Cutting the intro delegation-map bullets* (Dim 6/2 attempt): the three bullets
  (network→netplan, user-data→cloud-init, delivered via NoCloud) are load-bearing
  orientation — the differentiator of this three-skill design. Removing them makes
  the intro vague. Net-negative.
- *Consolidating the geoip/fallback/late-commands gotchas* (Dim 6, raised by the
  final blind agent): these appear in the SKILL.md "Common pitfalls" gotchas section
  AND in the reference pitfalls list. This overlap is **intentional** progressive
  disclosure — Anthropic's design guide endorses a curated, always-loaded inline
  gotchas section with fuller detail in references. Consolidating to one location
  would either drop the always-loaded gotchas or the comprehensive list. Declined.

**Final blind score (Opus, 2026-06-14): 91/100** (self 87 — aligned, no 2+ bias
gaps; blind scored higher). Stop condition met: ≥90 with no dimension below 7
(lowest = Simplicity 8). Self trajectory across modes: 78 → 84 (improve) → 87
(freshen) → trigger converged at baseline.

## Resolved — 2026-06-14 (freshen mode)

Self-score 84 → 87 (Dim 9 cap lifted 6 → 9).

- Created `references/sources.md`. Every factual claim probed and verified **fresh**
  against canonical/subiquity (online tags/releases + local repo execution); no
  version-drift, deprecation, or broken refs. Verified: subiquity live; 26.04 is the
  latest release (2026-04-23 → 26.04 LTS shipped); tags 24.04.x/24.10.1/25.04/25.10/
  26.04 exist; `kernel-crash-dumps`+`zdevs` are exactly the 24.04→main top-level
  additions; 26.04 top-level keys identical to main; `apt.fallback` enum =
  abort|continue-anyway|offline-install; `ubuntu-advantage` = autoinstall_key_alias
  for ubuntu-pro (ubuntu_pro.py); on-media "no other keys" rule (server.py).
- No content mutations needed (skill authored same day against the repo).

## Resolved — 2026-06-14 (trigger mode)

Converged at baseline — **no frontmatter mutation**.

- Eval set built: `references/trigger-evals.json` (7 should-trigger / 6 should-not,
  incl. sibling-boundary negatives for netplan & cloud-init and keyword collisions).
- Haiku screen (runs-per-query 3): train 12/13 — all 6 negatives clean (0.00, no
  over-trigger), 6/7 positives pass; lone miss "validate my autoinstall user-data"
  (0.00) is Haiku's known answer-directly false-negative.
- Opus confirmation (4 flagged queries): "validate…" 1.00, "PXE netboot…" 1.00,
  netplan-negative 0.00, cloud-init-negative 0.00 → **4/4**. Effective Opus: 7/7
  positives fire, 6/6 negatives quiet.
- Side finding: empirically confirmed `when_to_use` IS consumed by Claude Code
  v2.1.177 (when_to_use-only phrasings trigger reliably) — validates the improve-mode
  split. (skill-creator's `quick_validate.py` flags `when_to_use` as "unexpected" —
  that linter's allow-list is stale; ignore it.)

`last_run`: 2026-06-14 · baseline = final (0 mutations) · model: haiku screen + opus
confirm · eval set saved for next run.
