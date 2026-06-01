# Improvement backlog — secure-boot-cert-rotation

Carries ceiling findings across `skill-improver` runs. Read in Phase 0; updated in Phase 6.

## Open

- **Dim 6 (Simplicity, 8/10) — House Rules ↔ routing/references overlap.** SKILL.md "House rules" (the 7-item
  standing-rules block) restates points also in the routing table and references (db-first, right-tool-per-
  surface, audit→sample→fleet). Considered trimming as a simplification iteration but did **not** apply: both
  the baseline and final blind agents judged these "standing instructions, not waste," and they carry the
  hard-won lessons (don't-fearmonger, verify-real-artifact-not-tags) that drive Dim 10=10. Lifting Dim 6 to 9
  needs author judgment on which rules are genuinely redundant vs load-bearing — not a mechanical dedup.
- **Dim 2 (minor) — no TOC on the one >100-line reference.** `references/harvester-vms.md` is 115 lines; the
  rubric's reference-depth rule suggests a table-of-contents for files >100 lines. Marginal (only 15 lines
  over); skipped to avoid bloating a file that reads top-to-bottom as one runbook. Add a 4-line TOC if it grows.

## Resolved this pass (2026-06-01)

- **Dim 9 spec hard-fail** — `description` was 1554 chars (> 1024 Agent Skills cap, `skills-ref validate`
  reject). Rewrote frontmatter → `description` 876 chars. Cap lifted (3 → 9).
- **Dim 1 listing truncation** — combined `description` + `when_to_use` was 2420 chars (> 1,536 listing cap),
  burying every symptom trigger. Split + front-loaded → combined 1486 (50-char headroom). (4 → 9)
- **Dim 9 staleness cap** — `sources.md` had no per-row `Last verified:` markers (capped Dim 9 at 6). Added a
  "Freshness ledger" table (8 rows, all `2026-06-01`); freshen probe confirmed Harvester v1.8.0 latest /
  v1.6.0 guest-OVMF floor still current. Cap lifted.
- **Dim 3 second-person** — two `you`/`your` slips in the SKILL.md body converted to imperative.

Self-score 75 → 89; blind 78 → 91 (no bias flags). Stop condition met (≥90, no dim < 7).
