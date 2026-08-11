# Improvement backlog — vllm-chat-templates

Tracks work attempted-but-not-completed and changes the metric registered.
Append-only; carry open items forward with a `(carried <date>)` marker.

## Open

- **DeepSeek-V3.1 #28804 won't-fix mitigation phrasing could be tightened** (Dim 4/6) —
  SKILL.md pattern #10 + model-families.md DeepSeek bugs row. The whitespace-accumulation
  workaround ("strip leading whitespace on each turn") is stated as guidance but lacks an
  exact client-side snippet. Not applied this pass: adding a snippet is additive content,
  not a one-line atomic edit, and risks Dim 6 regression — defer to an author-driven
  decision on whether the snippet earns its place.

## Resolved — 2026-08-11 (freshen, v0.25.1 -> v0.27.0)

- **Pattern 15 was inverted and contradicted the sibling skill.** It read "vLLM
  settled on `reasoning_content` (#28472)". The response field is `reasoning`
  (`ChatMessage.reasoning`, `protocol.py:71` at v0.27.0); `reasoning_content` is
  the *deprecated request-side* alias. `vllm-reasoning-parsers` has had this
  right since 2026-05-28, so the two skills were telling operators opposite
  things about the field a client must read. Rewritten with the probe and the
  `jq '.choices[0].message | keys'` check.
- **`--reasoning-parser gpt_oss` in `flags-matrix.md` is not a registered
  name** — it is `openai_gptoss`, at v0.25.1, v0.26.0 and v0.27.0 alike. The
  GPT-OSS copy-paste recipe would have failed at server startup. This is a
  pre-existing error, not drift, and the highest-severity one found: the file's
  entire purpose is copy-pasteable serve commands.
- **Code-locations section re-anchored at v0.27.0.** `serving_chat.py` no
  longer exists (→ `chat_completion/serving.py`); all four `hf.py` ranges were
  stale, with the `ChatTemplateResolutionError` anchor at `477` now pointing at
  unrelated code (real line: 718).
- **Two counts corrected, both wrong before this window:** shipped tool
  templates are **26**, not 27 (identical at v0.25.1 and v0.27.0); the bundled
  fallback registry has **13 model types over 7 jinja files**, has lost `fuyu`
  (model removed in v0.26.0, #48096) and never had a `qwen` entry.
- **`continue_final_message` (#47844, v0.26.0)** — three lines noting that the
  kwarg is a near-no-op on the Python renderer (few HF templates read it) while
  the Rust frontend implements Transformers-v5 sentinel semantics, and that the
  Rust Harmony renderer rejects it outright.
- **Deliberately NOT changed: the "As of transformers v4.44" quote.** vLLM
  raises that string verbatim on v0.27.0; it names the transformers release that
  removed default templates, not a requirement. Added a guard note plus the real
  runtime floor (`transformers >= 5.5.3`, unchanged since v0.25.1) in
  `debugging.md`, so the next pass does not "fix" a correct quotation.

## Resolved this pass

- (2026-05-28) GLM #39614 reclassified OPEN → CLOSED/COMPLETED 2026-04-25 in SKILL.md
  pattern #13, sources.md, and model-families.md GLM bugs table — Dim 9 freshen.
- (2026-05-28) GLM #39611 reclassified to CLOSED/COMPLETED 2026-04-12, mislabel GLM-4.7
  → GLM-5.1 corrected, in SKILL.md patterns #14 + triage table L61 and model-families.md;
  added a dedicated sources.md row and removed it from the not-re-probed bucket — Dim 8 + Dim 9.
- (2026-05-28) Standardized GLM section in model-families.md to note both documented bugs
  are GLM-5.1-FP8 — Dim 8 naming consistency.
- (2026-05-28) Collapsed the redundant per-layer re-definition block under the Triage table
  (5 lines → 1 line) while preserving the "diagnose one at a time" discipline and all three
  layer names — Dim 6 simplification.
- (2026-05-28) Re-stamped re-confirmed sources.md rows (PR #27622, #39392, #38855) and the
  SKILL.md footer to Last verified 2026-05-28; updated sweep header — Dim 9 staleness clock reset.
