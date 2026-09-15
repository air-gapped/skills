# Improvement Backlog — responses-api

Carried across skill-improver runs. Open = attempted this pass but not
applicable in a single iteration. Do not re-propose without new evidence.

## Open

- **GPT-5.6 Programmatic Tool Calling / multi-agent orchestration depth**
  (Dim 5, narrowed 2026-07-31) — the tool type (`programmatic_tool_calling`)
  and beta status are now in spec.md, but the API reference documents only
  the type discriminator; invocation semantics, output item shapes, and the
  orchestration beta's params are still undocumented upstream. **Absent
  thing:** the upstream schema itself. Re-probe the API reference next
  freshen; expand only from official schema, not blogs.

## Decided — do not re-propose

- **Dim 6 near ceiling** (carried 2026-07-19) — two simplification
  iterations (iters 8-9, 2026-07-19) removed duplicate stats with no score
  gain; remaining duplication (Critical Gotchas summary layer, per-file stat
  repetition) is deliberate progressive-disclosure layering — further cuts
  judged net-negative for standalone file utility. Do not re-attempt without
  a restructure plan spanning SKILL.md + spec.md + translation-mapping.md.

## Resolved — 2026-09-15

- **vLLM PR #48098 release inclusion established** (Dim 9) — merged
  2026-07-15 as `c0302d94`; **first shipped in v0.26.0** (2026-07-27). Settled
  by commit-ancestry comparison rather than release-note reading: the merge
  commit is not an ancestor of v0.25.1 and is an ancestor of v0.26.0, and no
  tag exists between them. `sources.md` row updated.
- **vLLM #36435 stock-parser question answered — and the answer widens the
  warning** (Dim 9). The upstream reproduction runs a stock parser
  (`--tool-call-parser qwen3_coder`), not a custom one, and maintainers place
  the cause in a parser-agnostic `if reasoning_parser: ... elif tool_parser:`
  branch in `_process_simple_streaming_events`. So the leak is not
  custom-parser-specific: any model configured with both a reasoning parser
  and a tool parser is exposed. The skill previously implied the opposite by
  noting only that its own 2026-07-19 local run had used a custom Rust parser.
  Corrected in `backend-implementations.md`, `streaming-events.md` and
  `sources.md`. Issue remains OPEN (reopened); no comment confirms or denies
  it on v0.25+, so the warning stands rather than being narrowed to a version.

## Resolved this pass — 2026-07-31 (freshen)

- **"Llama Stack is the only non-OpenAI backend with /v1/responses/compact"
  claim refined** (was Open) — LiteLLM gateway has exposed the route since
  PR #18697 (merged 2026-01-06, code-verified at v1.92.0 and v1.94.0), but
  as pure passthrough (operator-confirmed): works only when the upstream
  provider supports compaction. Llama Stack remains the only non-OpenAI
  *implementation*. SKILL.md, backend matrix, Llama Stack + LiteLLM
  sections updated.
- **Bifrost version line ambiguity resolved** (was Open) — repo tags per
  component; HTTP-transport line is `transports/vX` (transports/v1.6.7,
  2026-07-30); `ent-v2.0.0-pre*` is the enterprise line. Pin updated.
- **GPT-5.6 Responses surface expanded** (was Open) — changelog + API
  reference probed: `reasoning.effort: "max"` (+ Pro mode),
  `programmatic_tool_calling` tool type, `prompt_cache_breakpoint
  {mode: "explicit"}`, image `detail: "original"`, multi-agent orchestration
  beta, 2026-07-30 Fast mode/pricing. spec.md + SKILL.md + adoption.md
  updated. Residual depth item re-opened (narrowed) above.
- ARC-AGI-3 evidence folded in (OpenAI publication 2026-07-29): retained
  reasoning + compaction = ~3× score / 6× fewer output tokens vs
  discard-and-truncate harness (13.3%→38.3% RHAE) — added to the
  reasoning-persistence gotcha (SKILL.md, translation-mapping.md gotcha 2,
  adoption.md) and as compaction-vs-rolling-truncation rationale in spec.md.
- OpenAI's first-party "legacy Chat Completions" positioning (2026-07-29)
  recorded in SKILL.md intro + adoption.md timeline/section.
- `phase` gotcha wording updated to gpt-5.3-codex and later (5.4/5.5/5.6)
  with Codex-protocol treat-absent-as-unknown semantics (models.rs probed).
- Version-pin refresh across 11 backends/clients; all tracked issues
  re-probed (no flips; #36435 reopened); sources.md fully restamped
  2026-07-31 with probe-access notes (openai.com 403s non-browser fetchers;
  developers.openai.com is WebFetch-reachable).

## Resolved — 2026-07-19

- Live verification against vLLM v0.25.1 (local deployment, custom Rust
  parsers): sequence_number fixed, `[DONE]` still
  omitted, event ordering correct, parallel tool calls work, `truncation:
  "auto"` no longer 400s, DELETE still absent, stream-vs-final item-id
  mismatch observed, and `store` gating traced to
  `VLLM_ENABLE_RESPONSES_API_STORE=1` in `responses/serving.py`.

- Freshen: 11 verified findings applied (10-backend version refresh; issue
  flips for vLLM #39584/#23218, LiteLLM #22102, SGLang #16806/#20771/#25881,
  mistral.rs #1944; `prompt_cache_retention` default flip 2026-05-29;
  `usage.input_tokens_details` field fix + `cache_write_tokens`; OpenResponses
  2026-04-24 release; Apr–Jul platform timeline incl. GPT-5.5/5.6; Codex CLI
  rust-v0.144.6; stamps → 2026-07-19). Created `references/sources.md`
  (lifts the Dim 9 staleness cap).
- Improve iters 1–10: event count standardized to 53 (SDK-verified); TOC added
  to backend-implementations.md; OpenResponses ecosystem section deduped
  (removed stale v2.3.0 claim); person-slips removed; sources.md wired into
  Quick Reference; runnable curl SSE-capture step added; trigger phrases added
  (OpenResponses, prompt_cache_key, Assistants migration); 2 stat dedupes;
  6 remaining sources rows re-probed (opencode v1.18.3, Pydantic AI v2.13.0,
  TensorRT-LLM v1.2.1, Agent Framework python-1.11.0).
- Post-blind sweep: 5 leftover "as of 2026-04-1x" status strings fixed
  (flagged by final blind validation, Dim 8 gap).
- Scores: baseline 78 (blind 82) → final 90 self / 85 blind (blind ran before
  the date-string sweep that resolved its top finding).
