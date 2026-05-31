# improvement-backlog — vuln-scan

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

## Open

- **Inline review briefs could move to `references/` (Dim 2).** The two
  subagent briefs (the per-focus-area review brief, SKILL.md ~83-165, and the
  Step-3b confidence-scoring brief, ~187-214) are inlined. Extracting them to
  `references/prompts.md` (as `triage`/`patch` now do) would tighten
  progressive disclosure. NOT applied this pass: SKILL.md is only 294 lines
  (already under the 300-line lean threshold, Dim 2 ≈ 7-8), so the ROI is low
  and the briefs read well next to the step that uses them. Revisit only if
  the body grows past ~350 lines.
- **`allowed-tools: Task` vs canonical `Agent` (Dim 8/9).** SKILL.md:17 lists
  `Task`; body uses `Task`/`subagent_type`. Cross-cutting rename shared with
  the other three defending-code skills — see threat-model backlog for the
  rationale and the one-pass plan. Deferred (regression risk + multi-location).

## Resolved this pass (2026-05-31)

- **Dim 9 staleness cap lifted.** Created `references/sources.md`
  (defending-code reference harness, claude-code-security-review, the
  "Using LLMs to secure source code" write-up) — all probed live,
  `Last verified: 2026-05-31`. Was capped at 6 by the absent-sources.md rule.
