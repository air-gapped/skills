# Improvement Backlog — responses-api

Carried across skill-improver runs. Open = attempted this pass but not
applicable in a single iteration. Do not re-propose without new evidence.

## Open

- **GPT-5.6 Responses surface undetailed** (Dim 5) — spec.md has only a
  timeline line for the 2026-07-09 GPT-5.6 launch (Programmatic Tool Calling,
  explicit prompt-caching controls, persisted reasoning, multi-agent
  orchestration beta). Hypothesis deferred 2026-07-19 on probe-budget
  exhaustion (~26 probes used). Action: next `freshen`, probe OpenAI docs for
  the concrete new tool types / request params / stream events and expand
  `references/spec.md` + the SKILL.md "2026 additions" list.
- **SGLang custom function tools: current behavior unverified** (Dim 9) —
  competing PRs #16806/#20771 closed unmerged 2026-06-12; #25881 merged same
  day but its description doesn't confirm custom function-tool support.
  Both `backend-implementations.md` and `streaming-events.md` carry a
  "re-verify on ≥ v0.5.15" marker. Needs a live-backend test or a targeted
  issue probe; not resolvable from PR metadata alone.
- **vLLM #36435 (tool-XML leakage) unverified on stock parsers** (Dim 9) —
  the 2026-07-19 live run showed no leakage but used a custom Rust
  tool parser; stock-parser behavior on ≥ v0.25 remains
  unverified. Everything else from the post-refactor re-verification item was
  resolved live 2026-07-19 (see Resolved).
- **Bifrost version line ambiguous** (Dim 9) — repo's latest release tag is
  `ent-v2.0.0-prerelease2-base` (enterprise line); the HTTP-transport line
  version could not be verified 2026-07-19. Probe the repo's release/tag
  scheme or docs next freshen.
- **"Llama Stack is the only non-OpenAI backend with /v1/responses/compact"**
  (SKILL.md line 14, Dim 9) — not re-probed this pass; at Llama Stack v1.2.1
  and 3 months of ecosystem movement the uniqueness claim may have decayed.
  Verify next freshen.
- **Dim 6 near ceiling** — two simplification iterations (iters 8-9,
  2026-07-19) removed duplicate stats with no score gain; remaining
  duplication (Critical Gotchas summary layer, per-file stat repetition) is
  deliberate progressive-disclosure layering — further cuts judged
  net-negative for standalone file utility. Do not re-attempt without a
  restructure plan spanning SKILL.md + spec.md + translation-mapping.md.

## Resolved this pass — 2026-07-19

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
