# Improvement backlog — vllm-reasoning-parsers

## Open

_No open items._

## Resolved — 2026-08-11 (freshen, v0.25.1 -> v0.27.0)

- **The prior pass's method was the bug.** 2026-07-21 detected unified-engine
  membership by matching `*_engine_reasoning_parser.py` filenames and concluded
  "8 of 27", explicitly noting that `kimi_k2`/`minimax_m2`/`mistral` reasoning
  entries "still point at the legacy files". Diffing by *import* shows
  `kimi_k2` and `minimax_m2` were already adapter shims **at v0.25.1** — the
  claim was wrong when written, and the matrix sent readers to 8-line files for
  behavioural detail. Replaced with an import test
  (`grep -l "registered_adapters import" vllm/reasoning/*.py`) stated in both
  the matrix and SKILL.md, so the next pass cannot repeat the filename
  inference. Real v0.27.0 additions to the path: `mistral` (#48947),
  `inkling`. Now **12 of 29**.
- **`openai_gptoss` gutted by #45560** (merged 2026-08-01). `is_reasoning_end`
  returns `True` unconditionally; `extract_reasoning`,
  `extract_reasoning_streaming`, `extract_content_ids` raise
  `NotImplementedError` → `HarmonyParser`. `reasoning_end_token_ids_prefix`,
  `reasoning_max_num_between_tokens = 20` and `eom_token_id` are deleted
  (`git grep` empty at v0.27.0, 4 hits at v0.25.1). Rewrote the matrix Harmony
  section, the `openai_gptoss` row and pitfalls.md §10, and repointed pitfall
  8's multi-token worked example at `kimi_k3_reasoning_parser.py`.
- **`mistral` unified with the tool parser** (#48947, merged 2026-07-30). CLI
  name unchanged. Pitfall 11 documented a hard
  `ValueError: The tokenizer must be an instance of MistralTokenizer.` — that
  raise no longer exists at v0.27.0. Rewritten rather than deleted: the
  `--tokenizer-mode mistral` recommendation stands, because the mistral-common
  grammar path is what enforces `tool_choice`; the failure mode changed from
  loud to silent-degradation.
- **`include_reasoning` reached the parser layer** (#44301, v0.26.0) — matrix
  line "Irrelevant for parser logic" corrected; engine-path `parse_delta` sees
  the flag, legacy `ReasoningParser` still does not.
- **29 names** (27 → 29): `kimi_k3` (legacy shape, 3-token XTML markers) and
  `inkling` (adapter path, typed content blocks) added to the matrix, the
  SKILL.md inline list and the description.
- **Not changed, deliberately:** the response field is still `reasoning` (not
  `reasoning_content`) — re-verified at `chat_completion/protocol.py:71` on
  v0.27.0. The sibling `vllm-chat-templates` skill claimed the reverse; fixed
  there, not here.

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
