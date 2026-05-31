# improvement-backlog — patch

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

## Open

- **SKILL.md 528 lines (28 over the 500 soft cap) — Dim 2.** This pass
  extracted the patch-author and reviewer prompts to `references/prompts.md`
  (653 → 528). The cleanest remaining trim is folding the "Design notes"
  section into "Guard rails" — both restate the reviewer-isolation property
  (also stated in Phase 3). NOT applied: each restatement is a load-bearing
  safety reminder (the reviewer must never see finding prose), and collapsing
  them risks dropping a standing safety instruction. Author judgment on
  whether the ~28-line overage is worth the consolidation.
- **4 second-person slips in body prose (Dim 3).** SKILL.md:201, 224, 226, 408
  ("you need", "your conversation", "end your turn", "you find yourself") — in
  operational/async-recovery notes, not quoted prompts. Convertible to
  imperative on a style pass; minor (Dim 3 already 8).
- **Add a `when_to_use` field (Dim 1).** 665/1536 chars of budget unused;
  symptom triggers ("draft a fix for", "remediate") would lift recall. Defer
  to a `trigger`-mode pass.
- **`allowed-tools: Task` vs canonical `Agent` (Dim 8/9).** Shared across all
  four defending-code skills — see `threat-model/references/improvement-backlog.md`.
  Deferred (regression risk + multi-location).

## Resolved this pass (2026-05-31)

- **Dim 9 staleness cap lifted (6 → 9).** Created `references/sources.md`
  (defending-code reference harness, execution-verified delegate) — probed
  live, `Last verified: 2026-05-31`.
- **Dim 2 lift (5 → 7).** Extracted the Phase-2B patch-author prompt and the
  Phase-3 reviewer prompt (verbatim) to `references/prompts.md` with
  read-at-phase pointers; SKILL.md 653 → 528 lines. Blind final 79 → 84.
