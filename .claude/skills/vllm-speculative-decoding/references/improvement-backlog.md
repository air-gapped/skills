# Improvement backlog — vllm-speculative-decoding

Work-not-done log from skill-improver passes. `## Open

- **Relax or restate the suffix + lossy-verification rule** (Dim 9). SKILL.md
  pitfall 6 and `methods.md` §9 and §11 `"fly"` bullet. Blocker: issue #66629
  is open (checked 2026-11-24 at v0.34.0, which ships the GPU suffix speculator
  with no config guard and no per-tenant corpus isolation). When a guard or
  isolation merges into a release, state what that version rejects or isolates.

## Resolved this pass (2026-11-10, trigger)

`claude-sonnet-5-5`, 7 runs per query, new 36-query `trigger-evals.json`:
baseline train 21/22, test 14/14; all 15 negatives 0/7, the sibling-territory
ones and the "without restarting" pair included — no cross-skill over-trigger.
- Kept: `when_to_use` terms the `description` already states removed, and the
  version-gate list cut from `description`. Listing 1521 → 1265 chars; train
  21/22 and test 14/14 unchanged.

## Resolved — 2026-10-18 (improve)

Blind baseline 75 (snapshot of the v0.32.0 freshen); self cold 75 -> 81 over
5 iterations, 4 kept; final blind score and A/B comparator run by the operator.
- Kept: 38-row version-gate table moved to `version-gates.md`; SKILL.md keeps a
  five-row "Version floors" table of the gates that still change a deploy.
- Kept: aux-hidden-state allowlist history cut to the `SupportsEagle3` rule;
  layer hook corrected to `get_eagle3_default_aux_hidden_state_layers()`.
- Kept: Composability rewritten as a current-state table; per-PR history moved
  to `version-gates.md` §"Composability history".
- Kept: TLI pitfall 7 states the rule and points at the v0.31.x floors row.
- Kept (after the cap, outside scoring): last second-person slip in §Method selection.
- Discard: moving the user-phrased implicit triggers to the front of
  `when_to_use` — Dim 1 unchanged on a cold re-score (the flag-heavy
  `description` dominates), and it took the listing to 1512/1536 chars for no
  measured gain. Do not re-propose without a `trigger`-mode measurement.

## Resolved — 2026-09-15 (the generic caveat now lives in one place)

- **Collapsed to SKILL.md, method-specific deltas kept.** `eagle3.md` and
  `dflash.md` were restating the general BS >= 32 and domain-mismatch effects,
  numbers included, beside their own method-specific parts. Each now states only
  its delta and points at SKILL.md: EAGLE-3 keeps the domain-adaptation remedy and
  the `disable_by_batch_size` knob, DFlash keeps that it falls off faster than
  vanilla EAGLE-3.
- **The blocker had already gone.** The entry recorded that the tool channel
  returned empty on every read of `troubleshooting.md`, so the file could not be
  confirmed and a blind edit was refused — correctly. It reads fine now, which is
  the whole reason this could be finished.
- **`troubleshooting.md` deliberately keeps its one-line bullet.** It sits in a
  "when to disable" checklist that is read as a list; replacing one line with a
  cross-reference would cost more tokens than it saves and break the scan.

## Resolved — 2026-05-29

- Fixed aux_hidden_states allowlist line-anchor drift 818-833 → 895-909 in
  references/eagle3.md L27 and references/dflash.md L41 (Dim 8 — matches
  SKILL.md/methods.md; sources.md row 15 had already claimed this fixed).
- Added EAGLE 3.1 note (vLLM blog 2026-05-26) to references/eagle3.md after the
  P-EAGLE section (Dim 9 / Dim 5 — captures newest in-scope EAGLE feature).
- Re-stamped sources.md "vLLM releases" row from stale "v0.20.0 one day ago" to
  v0.21.0 stable / v0.22.0rc as of 2026-05-29; added an EAGLE 3.1 blog row; both
  stamped Last verified 2026-05-29 (Dim 9).
- Trimmed two near-duplicate implicit triggers ("faster inference", "higher
  tok/s") from SKILL.md when_to_use — subsumed by retained "speed up decode" /
  "can we get more tokens/sec"; widens listing-cap headroom (Dim 1 / Dim 6).
