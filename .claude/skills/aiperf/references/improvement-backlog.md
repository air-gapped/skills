# Improvement Backlog — aiperf

Prior skill-improver runs and ceiling findings.

## Open

### Bundle helper scripts to lift Dim 7 (Resource Quality)
- **Dim:** 7
- **Where:** new `scripts/` directory; would also require pointer table additions in `SKILL.md` "What to read next" and `references/output-artifacts.md`.
- **Why ceiling-bound:** plugin authoring (rerank shim, custom dataset loader) and `profile_export.jsonl` percentile/correlation analysis are scriptable. But: (a) which scripts are most valuable depends on author intent — operator-side (analysis helpers) vs developer-side (plugin scaffolds); (b) the official aiperf repo already provides Pydantic models for output parsing, so a script would be duplicative without a focused use case the author wants to standardize on. Skip until the author signals the workflow.
- **Score impact if resolved:** Dim 7 7→9 (~+2 total).

### Quick-recipe / timing-modes overlap (intentional design)
- **Dim:** 6
- **Where:** `SKILL.md:144-209` "Quick recipes" overlaps with `references/timing-modes.md:122-169` "Worked examples".
- **Why not fixed:** different audiences. SKILL.md recipes are entry-points (smoke test, ShareGPT, Mooncake+goodput, NIM, multi-turn KV-cache, multi-run CI, accuracy) — pattern-by-task. timing-modes.md examples are scheduling-mode-by-scheduling-mode, intentionally illustrating compatibility-matrix rules. Removing either degrades the corresponding navigation path. Carrying as a known-non-issue rather than open work.

## Resolved this pass (2026-04-25)

- **Trigger Precision (Dim 1) char-cap fix.** Combined `description` + `when_to_use` reduced from 2188 chars (truncated at 1536) to 1455 chars (81-char margin). Tail-truncated triggers no longer lost. (iter 1, iter 4)
- **Writing Style (Dim 3).** Six second-person slips removed: 2 in SKILL.md (lines 40, 79), 4 in references (migration:62, endpoints:43, plugins:3, plugins:155). Zero "you/your" remaining in the skill. (iter 2, iter 4)
- **Stale instruction in cli.md.** `--isl-block-size` description previously said "Match server's block size" — contradicted SKILL.md pitfall 5 (Mooncake encodes at 512 by design). Rewritten to point at SKILL.md pitfall 5 with the correct divisibility rule. (iter 2)
- **Pitfall redundancy (Dim 6).** Pitfall 12 (server-side reasoning-parser config) folded into pitfall 2 (TTFT/TTFO/OSL semantics) since the former is a prerequisite of the latter. Net -2 SKILL.md lines, no content lost. (iter 3)

### Score trajectory

| iter | self | blind | delta | status | description |
|------|------|-------|-------|--------|-------------|
| 0    | 85   | 82    | —     | baseline |  |
| 1    | 86   |       | +1    | keep   | trim desc+when_to_use to 1532/1536 |
| 2    | 87   |       | +1    | keep   | 2 SKILL.md you/your → imperative + 1 cli.md stale instruction |
| 3    | 88   |       | +1    | keep   | merge pitfall 12 → pitfall 2 |
| 4    | 90   | 90    | +2    | keep   | 4 reference you/your fixes + tighten margin to 81 chars |

Final blind agreed with self. No bias flags ≥2. Run converged at 90/100 with no dimension below 8.
