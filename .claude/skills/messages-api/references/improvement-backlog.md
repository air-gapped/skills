# Improvement Backlog — messages-api

Carried across skill-improver runs. Open = attempted this pass but not
applicable in a single iteration.

## Open

- **Divergence facts intentionally double-homed** (Dim 6) — the
  stop_sequence and thinking-signature values appear as matrix cells in
  `backend-implementations.md` AND as tables in `translation-mapping.md`
  (SKILL.md carries only the one-line rule + pointer since 2026-07-19).
  Attempted full single-homing in iter 3; judged net-negative to remove the
  matrix cells — the matrix is the per-backend summary artifact and gutting
  it harms standalone utility. Accepted drift risk; freshen passes must
  update both. Do NOT re-propose removal without a restructure that keeps the
  matrix self-contained.
- **Base-URL convention phrasing differs by design** (Dim 8, blind-flagged
  2026-07-19) — SKILL.md says "origin, no /v1" for Claude Code; clients.md
  says "conventions vary by tool" (Lemonade origin-only, Bifrost /anthropic
  prefix, opencode /v1). Both are correct at their altitude; a unification
  would lose per-tool precision. Left as-is with this rationale.

## Resolved this pass — 2026-07-19 (improve+freshen, baseline 87 self / 89 blind)

- Iter 1 (freshen/probe): resolved 5 unknown matrix cells from local source —
  llama.cpp thinking param (enabled→thinking_budget_tokens, adaptive
  ignored; also forwards metadata.user_id), ping never emitted by
  llama.cpp/SGLang/Ollama, OGX forwards-on-passthrough, Lemonade
  stop_sequence always null. (+1, Dim 5)
- Iter 2: wired the `argument-hint` topic argument into Quick Reference
  (blind finding). (+1, Dim 8)
- Iter 3 (simplification): SKILL.md gotchas reduced to rule + pointer;
  detail single-homed in translation-mapping.md. (+1, Dim 6; Dim 1 corrected
  upward after mechanical length check)
- Iter 4 (freshen): official spec row verified and stamped — docs moved to
  platform.claude.com (docs.anthropic.com 301s); stop_reason value set
  cross-checked against the official reference, skill matches. (+1, Dim 9)
- Post-blind sweep: last "?" cell resolved (Lemonade emits no ping — probed
  source); arg-less load guidance added to Quick Reference.
- Scores: baseline 87 self / 89 blind → **final 91 self / 91 blind** (exact
  agreement, no flagged gaps). Loop stopped on the 90+ criterion after 4
  kept iterations, 0 discards.
