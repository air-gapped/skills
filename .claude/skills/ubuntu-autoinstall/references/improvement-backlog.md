# Improvement backlog — ubuntu-autoinstall

Carries ceiling findings and run history across skill-improver passes. Read in
Phase 0; update in Phase 6. Append-only history — do not drop prior dated sections.

## Open

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

## Resolved this pass (2026-10-20)

Freshen: all 12 prior rows probed + 9 rows added (21), stamp 2026-10-20; improve blind 82 → 82 (Sonnet scorer,
both ends), A/B comparator IMPROVED 3/3; 10 iterations, 8 kept, 2 discarded (cap).
- Fixed: `geoip: false` does not stop the geoip request; effective `apt.fallback`
  default; `identity.groups` (26.04+, hard failure on 24.04); 26.10 `accepted-errors`
  and `/boot` rule; sub-key strictness; done-condition; wrong-disk blacklist; TOCs;
  sources pointer; second-person slips; public sample hash warning.
- Discard: condensing the SKILL.md precedence list to a rule + pointer — it dropped
  the non-obvious "ISO-baked `cdrom/autoinstall.yaml` loses to a cloud-config seed"
  and the rewording added an unverified claim.
- Discard: rewording the "quote the password hash and `-append`" pitfall to drop the
  `-append` repeat — same shape as the 2026-06-14 declined gotcha consolidation; Δ0,
  no lines saved.

## Resolved — 2026-07-21 (freshen)

**Verified unchanged — mechanically, not by re-stamping.**

The signal worth noting: subiquity's `main` was **pushed 2026-07-20** while
**`26.04` (2026-04-23) is still the latest release** — three months of active
development with no cut. Since this skill documents the schema on `main`, the
release tag is not a proxy for whether the schema moved, so the artifact was
diffed directly.

- **32 top-level keys on `main`; all 32 already documented in `schema.md`** —
  programmatic diff of the live `autoinstall-schema.json` against the backticked
  identifiers in the reference. Zero undocumented keys, none removed.
- Schema `version` still constrained to exactly 1
  (`{minimum: 1, maximum: 1}`); `kernel-crash-dumps` / `zdevs` gating holds.
- `apt.fallback` enum unchanged: `abort`, `continue-anyway`, `offline-install`.
- All three code-behaviour claims re-read at source and unchanged — now carrying
  line anchors so the next pass can jump straight to them:
  `flavor_to_pkgname()` (kernel.py L19-29), the on-media fatal string
  (server.py L741), the `ubuntu-pro`/`ubuntu-advantage` alias pair
  (ubuntu_pro.py L75-76).
- Recorded the reusable diff recipe in `sources.md` so the check is a
  two-command job next time rather than a manual read.


## Decided — do not re-propose

- **Dim 7 (Resource Quality) capped at 8 — no bundled scripts.** Could add a
  `scripts/build-seed.sh` (genisoimage/cloud-localds wrapper) or a validator-fetch
  helper. Deliberately omitted: the authoritative validator ships upstream in
  canonical/subiquity and `references/examples.md` already has copy-paste commands,
  so a bundled script may be over-engineering. Author decides whether the
  convenience justifies the maintenance surface. (dir: `scripts/`, absent by design)

- **SKILL.md stays ~200 lines; Dim 2 sits at 8–9.** Worked 2026-10-20: the key table
  and intro paragraph were cut (219 → 206). What remains above 150 lines (delivery,
  air-gapped YAML, storage quick, validation commands, pitfalls) is INTENTIONAL_DETAIL
  overview of the references, which Pattern 6.1 keeps. Condensing the precedence list
  was tried and discarded (see Resolved this pass, 2026-10-20).

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
