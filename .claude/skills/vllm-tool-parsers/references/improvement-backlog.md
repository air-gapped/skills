# Improvement backlog — vllm-tool-parsers

Work-not-done log from skill-improver APPLY passes. "Open" = attempted as a
hypothesis but not applied in a single atomic iteration. Not a wishlist.

## Open

- **Relocate framework-contract + reasoning-pairing tables out of SKILL.md** (Dim 2 Progressive Disclosure) — `SKILL.md` "Framework contract (mental model)" (~lines 89-106) and "Reasoning-parser pairing" (~lines 108-123). Both are reference content already cross-linked from the diagnostic playbook. Moving them to a reference file would trim the 222-line body toward the <150 lean band, but the diagnostic playbook's steps reference the four state fields and the reasoning pairing inline, so a pure relocation risks dangling those pointers — needs a coordinated multi-file edit (extract + repoint + add reference bullet) that exceeds one atomic iteration. Deferred: Dim 2 already at 9 and SKILL.md is comfortably under the 500-line limit, so this is low-ROI relative to its breakage risk.

## Resolved this pass (2026-05-28)

- Added 6 new parser families + hy_v3 to the SKILL.md family table (Dim 5, Dim 8, Dim 9): apertus, cohere_command3/cohere_command4, deepseek_v4, lfm2, minicpm5, poolside_v1, hy_v3.
- Added all 7 new parsers to `references/parser-index.md` with verified one-line non-obvious facts read from live source (Dim 5, Dim 9).
- Bumped "36+ built-in parsers" → "40+" in the description and corrected `sources.md` counts to 40 source files / 43 CLI names (Dim 9).
- Re-stamped `sources.md` `Last verified` to 2026-05-28 on all re-confirmed rows; added a latest-release row (v0.21.0); refreshed the registry row with the 7 new CLI names (Dim 9 staleness window).
- Deleted the near-duplicate 9-step diagnostic flow from `references/streaming-pitfalls.md`, leaving a one-line pointer to the canonical SKILL.md playbook (Dim 6, Dim 8).
- Trimmed `description` + `when_to_use` from a combined ~1795 chars to 1495 chars, fitting under the 1536 listing cap that was previously overflowing and truncating the implicit-phrasing triggers (Dim 1).
