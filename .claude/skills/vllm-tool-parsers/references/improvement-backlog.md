# Improvement backlog — vllm-tool-parsers

Work-not-done log from skill-improver APPLY passes. "Open" = attempted as a
hypothesis but not applied in a single atomic iteration. Not a wishlist.

## Open

- **Relocate framework-contract + reasoning-pairing tables out of SKILL.md** (Dim 2 Progressive Disclosure) — `SKILL.md` "Framework contract (mental model)" (~lines 89-106) and "Reasoning-parser pairing" (~lines 108-123). Both are reference content already cross-linked from the diagnostic playbook. Moving them to a reference file would trim the 222-line body toward the <150 lean band, but the diagnostic playbook's steps reference the four state fields and the reasoning pairing inline, so a pure relocation risks dangling those pointers — needs a coordinated multi-file edit (extract + repoint + add reference bullet) that exceeds one atomic iteration. Deferred: Dim 2 already at 9 and SKILL.md is comfortably under the 500-line limit, so this is low-ROI relative to its breakage risk.

## Resolved — 2026-07-21 (freshen, v0.21.0 -> v0.25.1)

- **Registry count unchanged at 43, composition changed — the case for diffing
  names rather than counting them.** `minimax` was **removed** (and
  `minimax_tool_parser.py` deleted), `minimax_m3` **added**. Net zero. A
  count-only check reports "no change" while `--tool-call-parser minimax`
  silently stops resolving on upgrade.
- **The unified parser engine reached the tool side too.** Seven registry names
  now resolve through `vllm/parser/` via `make_adapters()`: `qwen3_coder`,
  `qwen3_xml`, `mimo`, `gemma4`, `deepseek_v4`, `deepseek_v32`, `seed_oss`.
  Their `vllm/tool_parsers/*_engine_tool_parser.py` files are a few lines that
  subclass the adapter and attach `structural_tag_model`. Added both the
  package and the name→implementation map to the "Where things live" table,
  because this skill's core instruction — *"read
  `vllm/tool_parsers/X_tool_parser.py`"* — now lands on a stub for those seven.
- **Two guidance claims invalidated, not merely relocated:**
  - `qwen3_coder` vs `qwen3_xml` were documented as materially different
    implementations (hand-rolled state machine vs an expat
    `StreamingXMLToolCallParser` called "cleanest streaming in the tree"),
    which read as a recommendation to prefer `qwen3_xml`. **Both names now
    resolve to the same class**; the separate files are deleted. The choice is
    a naming detail, and issue #30439 (`qwen3_coder` not streaming args) is
    moot on the unified path.
  - `step3p5` was documented as reusing "the `qwen3_xml` expat engine". That
    file is gone; `step3p5_tool_parser.py` imports
    `xml.parsers.expat.ParserCreate` directly.
- **Cross-skill consistency:** the same refactor was found in
  `vllm-reasoning-parsers` this pass. Recorded in both skills that for these
  models tool and reasoning behaviour now share one parser class, so they are
  no longer independent surfaces — and that RFC #32713 is OPEN and
  stale-bot-marked while its implementation ships.

**Carried forward:** the single Open item above (relocating the
framework-contract and reasoning-pairing tables) was not attempted — unchanged
reasoning, and this pass's budget went to the factual drift.

## Resolved — 2026-05-28

- Added 6 new parser families + hy_v3 to the SKILL.md family table (Dim 5, Dim 8, Dim 9): apertus, cohere_command3/cohere_command4, deepseek_v4, lfm2, minicpm5, poolside_v1, hy_v3.
- Added all 7 new parsers to `references/parser-index.md` with verified one-line non-obvious facts read from live source (Dim 5, Dim 9).
- Bumped "36+ built-in parsers" → "40+" in the description and corrected `sources.md` counts to 40 source files / 43 CLI names (Dim 9).
- Re-stamped `sources.md` `Last verified` to 2026-05-28 on all re-confirmed rows; added a latest-release row (v0.21.0); refreshed the registry row with the 7 new CLI names (Dim 9 staleness window).
- Deleted the near-duplicate 9-step diagnostic flow from `references/streaming-pitfalls.md`, leaving a one-line pointer to the canonical SKILL.md playbook (Dim 6, Dim 8).
- Trimmed `description` + `when_to_use` from a combined ~1795 chars to 1495 chars, fitting under the 1536 listing cap that was previously overflowing and truncating the implicit-phrasing triggers (Dim 1).
