# Improvement backlog — vllm-reasoning-parsers

## Open

- **Re-verify the 2026-04-24-stamped sources rows to clear the Dim 9 staleness cap** (Dim 9; `references/sources.md` in-tree rows: `abs_reasoning_parsers.py`, `basic_parsers.py`, `hy_v3_reasoning_parser.py`, and issue-state rows #23429 / #20227). These were NOT re-probed in the 2026-05-28 sweep because the shell output channel degraded mid-run, so they remain stamped 2026-04-24 (>90 days old). The oldest dated row therefore still drives the Dim 9 cap at 7. A clean follow-up freshen that re-fetches each path/issue and stamps them today is the only thing that clears the cap — score-loop edits cannot. (created 2026-05-28)

- **Fill delimiter / thinking-disable / truncation columns for the Cohere Command rows** (Dim 5/9; `references/parser-matrix.md` rows `cohere_command3`, `cohere_command4`). Registry name + shared file (`cohere_command_reasoning_parser.py`) + ClassName are verified against `main`, and `deepseek_v4` (alias of `deepseek_v3`), `poolside_v1` (subclass of `DeepSeekV3ReasoningParser`, source read line-by-line) are fully characterized. The Cohere file body was not fetched this run (404 on the guessed `cohere_command{3,4}_reasoning_parser.py` paths before the shared-file name was known), so the Cohere `Family` / `Thinking-disable switch` / `Truncation policy` cells carry a "See file" pointer. A follow-up should read `cohere_command_reasoning_parser.py` and fill exact delimiter style and truncation policy. (created 2026-05-28)

## Resolved this pass

- Reconciled built-in parser count to **25** across SKILL.md description, SKILL.md matrix intro (inline name list), and `sources.md` — removed the 22-vs-21-vs-25 three-way mismatch (Dim 8 6→9).
- Added the four missing parser rows (`deepseek_v4`, `poolside_v1`, `cohere_command3`, `cohere_command4`) to `parser-matrix.md`; matrix now enumerates all 25 names (Dim 5 8→9).
- Corrected stale class groupings in `parser-matrix.md`: split `glm45`/`holo2` into their own rows (`Glm45ReasoningParser` / `Holo2ReasoningParser`, own files) and split `mimo` from `qwen3` (`MiMoReasoningParser`, own file) — matches `main`.
- Replaced the SKILL.md "Router" block (restated matrix routing, and had begun to drift from the corrected matrix) with a one-line pointer to the matrix `Family` column plus the genuinely non-obvious cases (Dim 6 8→9, single source of truth for routing).
- Fixed the response-message class anchor `ChatCompletionResponseMessage` → `ChatMessage` in the SKILL.md field-name note and pitfall 15 (matches `protocol.py` on `main`).
- Clarified in pitfall 15 that the `reasoning_content` → `reasoning` rename is **response-only**: `reasoning_content` is still accepted request-side via backward-compat normalization (RFC vllm#27755); added the RFC anchor to `sources.md`.
