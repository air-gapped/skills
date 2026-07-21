# Improvement backlog — vllm-reasoning-parsers

## Open

_Both items carried from 2026-05-28 were closed by the 2026-07-21 freshen. No
open items at present._

## Resolved — 2026-07-21 (freshen, v0.25.1)

- **Closed both carried Open items.**
  - *Dim 9 staleness cap:* re-probed every row still stamped 2026-04-24 —
    `abs_reasoning_parsers.py` (374 lines), `basic_parsers.py` (201),
    `hy_v3_reasoning_parser.py` (143), and issues #23429 / #20227 — and stamped
    them 2026-07-21. The oldest-row cap should now clear.
  - *Cohere columns:* fetched `cohere_command_reasoning_parser.py` (571 lines).
    Delimiters are the vocab tokens `<|START_THINKING|>` / `<|END_THINKING|>`
    (with `<|CHATBOT_TOKEN|>` also resolved), both classes derive from
    `BaseCohereCommandReasoningParser`, and **the two subclasses differ only by
    a filter profile** — `PyFilterOptions().cmd3()` vs `.cmd4()`. Neither adds a
    thinking-disable switch. "See file" placeholders replaced.
- **The structural finding: a unified reasoning+tool parser has landed.** A new
  top-level **`vllm/parser/`** package implements RFC #32713 —
  `make_adapters(XParser)` derives both `XParserReasoningAdapter` and
  `XParserToolAdapter` from one per-model class, and the
  `vllm/reasoning/*_engine_reasoning_parser.py` files are now three-line
  re-export shims. **8 of 27 registry names are on this path** (`deepseek_v4`,
  `gemma4`, `glm45`, `glm47`, `mimo`, `nemotron_v3`, `qwen3`, `seed_oss`), and
  their matrix rows named both the wrong class and the wrong file. Documented
  the two paths in the matrix intro and warned in SKILL.md against copying an
  adapter-path parser as a template for a custom one.
- **Two behavioural corrections, not just path renames:**
  - `deepseek_v4` **is no longer an alias of `deepseek_v3`** — it has its own
    `DeepSeekV4Parser`.
  - `glm45` and `holo2` **have diverged**. They shared a matrix row as
    `DeepSeekV3ReasoningWithThinkingParser`; `glm45` moved to the adapter path
    with `glm47`, and only `holo2` still uses the DeepSeek-V3 thinking variant.
    Row split, and the SKILL.md pitfall-2 sentence that grouped them corrected.
- **Count 25 → 27**; new names `glm47` and `minimax_m3` added to the matrix and
  to the SKILL.md inline list.
- **RFC #32713 is OPEN and stale-bot-marked while its implementation ships.**
  Recorded in `sources.md` as the counterpart to freshen-patterns §3.0: a
  tracker's state says nothing about whether the work landed, in either
  direction. Read the tree.
- **#20227 re-classified.** It was recorded as "CLOSED (resolved)". It is
  `NOT_PLANNED` — closed without an upstream change. The custom-parser recipe
  this skill teaches comes from a *workaround comment* on that issue, which is
  still the right recipe, but the issue is not evidence of first-class support.

**Caveat on the note below.** The 2026-05-28 "Resolved" entry claiming
`glm45`/`holo2`/`mimo` were "split into their own rows (`Glm45ReasoningParser` /
`Holo2ReasoningParser` / `MiMoReasoningParser`, own files)" records an
**intermediate claim that was retracted within that same session** — see the
`sources.md` sweep log, which notes "an earlier draft of this sweep wrongly
claimed they had been split out; corrected same-session". Those classes never
existed. Left in place as history, flagged here so a future pass doesn't treat
it as a prior observation contradicting today's finding.

## Resolved — 2026-05-28

- Reconciled built-in parser count to **25** across SKILL.md description, SKILL.md matrix intro (inline name list), and `sources.md` — removed the 22-vs-21-vs-25 three-way mismatch (Dim 8 6→9).
- Added the four missing parser rows (`deepseek_v4`, `poolside_v1`, `cohere_command3`, `cohere_command4`) to `parser-matrix.md`; matrix now enumerates all 25 names (Dim 5 8→9).
- Corrected stale class groupings in `parser-matrix.md`: split `glm45`/`holo2` into their own rows (`Glm45ReasoningParser` / `Holo2ReasoningParser`, own files) and split `mimo` from `qwen3` (`MiMoReasoningParser`, own file) — matches `main`.
- Replaced the SKILL.md "Router" block (restated matrix routing, and had begun to drift from the corrected matrix) with a one-line pointer to the matrix `Family` column plus the genuinely non-obvious cases (Dim 6 8→9, single source of truth for routing).
- Fixed the response-message class anchor `ChatCompletionResponseMessage` → `ChatMessage` in the SKILL.md field-name note and pitfall 15 (matches `protocol.py` on `main`).
- Clarified in pitfall 15 that the `reasoning_content` → `reasoning` rename is **response-only**: `reasoning_content` is still accepted request-side via backward-compat normalization (RFC vllm#27755); added the RFC anchor to `sources.md`.
