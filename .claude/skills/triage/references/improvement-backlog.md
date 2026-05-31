# improvement-backlog — triage

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

## Open

- **SKILL.md still 823 lines (>500 guideline) — Dim 2 ceiling.** This pass
  extracted the two ~1,200-word subagent prompts to `references/prompts.md`
  (1021 → 823). Reaching <500 would require also extracting the per-phase JSON
  checkpoint schemas and the Phase-6 incremental-write mechanics (SKILL.md
  ~679-733) to `references/`. NOT applied this pass: those schemas are
  interleaved with the checkpoint instructions that use them, so moving them
  fragments the resumable-runbook coherence the skill depends on — a
  multi-section restructure that needs author judgment on how far to split a
  deliberately single-file pipeline. The residual length is load-bearing phase
  methodology, not padding.
- **Add a `when_to_use` field (Dim 1).** The 447-char `description` carries the
  four primary triggers; secondary phrasings ("false positive review",
  "scanner noise", "dedupe vulns", "rank by exploitability") would lift Dim 1
  recall. NOT applied: additive change, low ROI against the current score; do
  it on a trigger-mode pass (`/skill-improver trigger triage`) which measures
  trigger rate empirically rather than guessing phrasings.
- **Prose tool-list at SKILL.md:57 omits `Grep` + scoped `Bash` (Dim 8).** The
  inline "Tools:" sentence lists fewer tools than the frontmatter
  `allowed-tools` grants; reconcile the two. Minor; one-line edit deferred to
  avoid mid-run churn.
- **`allowed-tools: Task` vs canonical `Agent` (Dim 8/9).** Shared across all
  four defending-code skills — see `threat-model/references/improvement-backlog.md`
  for the rationale and the one-pass cross-skill rename plan. Deferred
  (regression risk + multi-location).

## Resolved this pass (2026-05-31)

- **Dim 9 staleness cap lifted (6 → 9).** Created `references/sources.md`
  (defending-code reference harness, CVSS first.org, OWASP Risk Rating) —
  probed live, `Last verified: 2026-05-31`.
- **Dim 2 lift (4 → 7).** Extracted the Phase-3a verifier prompt and Phase-4a
  ranking prompt (verbatim) to `references/prompts.md` with read-at-phase
  pointers; SKILL.md 1021 → 823 lines. The compact 3b verifier form stays
  inline (short, used where described). Blind final 78 → 84.
