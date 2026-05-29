# Improvement backlog — vllm-benchmarking

Work-not-done log from skill-improver passes. "Open" = issues attempted or identified but not applied this pass (with the reason). "Resolved this pass" = changes the metric actually registered.

## Open

- **Trim triple-stated warmup/tokenizer/random content** — Dim 6 (Simplicity). `SKILL.md` "Why this matters" (L14-22) restates the warmup / tokenizer / random-as-prod pitfalls that "Critical pitfalls" (L73-82) also enumerates. Not applied this pass: the keep/discard budget went to higher-magnitude wins (release framing, version-boundary unification, listing-cap trim, dataset/trace-replay coverage). Deletion-favoured candidate for next pass — collapse "Why this matters" to the three failure-mode *consequences* and let "Critical pitfalls" own the flag-level detail.

## Resolved this pass (2026-05-28)

- Release framing bumped v0.19.1 → v0.21.0 (current stable, `gh release list` isLatest) — `sources.md`, `output-schema.md`. Dim 9 8→9.
- Warmup version-boundary unified to v0.11–v0.21 across `SKILL.md`, `troubleshooting.md`, `output-schema.md`, `methodology.md` (was v0.19 / v0.11–v0.19, mutually inconsistent + stale). Dim 8 8→10.
- `when_to_use` trimmed so combined description+when_to_use = 1199 chars (≤ 1536 listing cap); only redundant/deprecated phrases dropped (`sonnet dataset`, `does this deploy get faster`, `can {model} hit TTFT Y`). Dim 1 9→10.
- Added timed trace-replay feature (v0.21+, verified serve.py commit `bfb9ebc211` / PR #39795) to `commands.md`. Dim 9 supported.
- Added datasets `spec_bench`, `speed_bench`, `custom_audio`, `custom_image` to `datasets.md` — all four confirmed in the rendered `docs.vllm.ai` dataset table this cycle. Dim 5 supported.
