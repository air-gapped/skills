# Improvement backlog — ubuntu-netplan

Carries ceiling findings and run history across skill-improver passes. Read in
Phase 0; update in Phase 6. Append-only history — do not drop prior dated sections.

## Open

- **Dim 7 (Resource Quality) — no bundled scripts (by design).** netplan is a system
  command; the skill correctly relies on `netplan` invocations + copy-paste examples
  rather than bundling scripts. Reaching a 9/10 "exemplary resources" would mean
  adding helper scripts that don't belong. Accept 8–9; author decides if any helper
  is wanted. (dir: `scripts/`, absent by design)
- **Boris advisory (not a cap): 11 numbered lines** = 6-step authoring workflow +
  5-step validation fast-path. The blind agent judged these genuine netplan *safety
  procedure* (validate-before-apply, `try` over SSH), not invocation scaffolding —
  no Dim 6 cap. Watch on future edits: keep them framed as standing rules ("over SSH
  always prefer `netplan try`") rather than one-time "first do X" steps so they
  survive compaction. (SKILL.md authoring workflow + validation fast-path)

## Resolved — 2026-06-14 (improve mode)

Blind baseline (Opus): 85/100. Top blind findings addressed:

- Dim 3: removed all ~7 second-person slips → imperative voice ("You write declarative
  YAML" → "declarative YAML…"; "drop your SSH session"; "files you'll meet"; "where
  you don't want"; "whenever you set"; "a bridge you deleted").
- Dim 1: split overloaded `description` into `description` (what + scope) +
  `when_to_use` (trigger phrases); folded in the "shared `network:` substrate for
  ubuntu-autoinstall and ubuntu-cloud-init" cross-link. description 472 / combined 936.

**Declined (do NOT re-propose):** consolidating the inline Quick-patterns vs
`examples.md` overlap (Dim 6) — the inline patterns are always-loaded quick-reference;
moving them to references only is net-negative (same rationale as ubuntu-autoinstall).

## Resolved — 2026-06-14 (freshen mode)

Dim 9 cap lifted (6 → 9). Created `references/sources.md`; all claims verified **fresh**
(online releases + local repo); no drift/deprecation/broken:

- netplan live; latest release 1.2.1 (2026-01-27) → "26.04 tracks 1.2.x"; 1.0.1 in the
  24.04 window, 1.1 (ra-overrides/advertised-mss) released *after* 24.04 → version
  gating correct; `parse.c` version-2-only; `netplan try` timeout 120.

## Resolved — 2026-06-14 (trigger mode)

Converged at baseline — **no frontmatter mutation**.

- `references/trigger-evals.json`: 7 should-trigger / 6 should-not (sibling-boundary
  negatives for autoinstall & cloud-init, plus app/firewall/DNS decoys).
- Haiku screen (runs 3): **13/13** — all 7 positives 1.00, all 6 negatives 0.00.
- Opus confirm of the two sibling negatives (autoinstall.yaml, cloud-init): both 0.00
  → no over-trigger across the boundary. Effective Opus: 7/7 pos, 6/6 neg.

`last_run`: 2026-06-14 · baseline = final (0 mutations) · haiku screen + opus confirm.

**Final blind score (Opus, 2026-06-14): 90/100** (baseline blind 85 → 90). Stop
condition met: ≥90 with no dimension below 7 (lowest = Simplicity 8). The blind's
Dim 6 note (udev-MAC warning appears in 3 contexts; validation fast-path overlaps the
playbook) is the intentional inline-gotchas/quick-ref pattern — declined per the
rationale above.
