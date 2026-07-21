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

## Resolved — 2026-07-21 (freshen)

7 probes. vLLM moved four minors; the interesting findings are two silent-skew
traps and a module move.

- **vLLM v0.21.0 → v0.25.1** (2026-07-14). Version framing updated across
  `sources.md` and `output-schema.md`.
- **`--chat-template-kwargs` vs `--extra-body chat_template_kwargs`** (new flag,
  PR #44244, 2026-06-03). Two near-identically-named knobs on **opposite sides of
  the wire**: the new flag forwards kwargs to `apply_chat_template` only for
  **client-rendered** datasets (`custom`, `speed_bench`), while `--extra-body`
  ships them to the server. Picking the wrong one silently benchmarks the wrong
  mode — no error, just numbers for a model that wasn't thinking. Added to
  `commands.md` with the distinction stated explicitly rather than as two
  separate entries.
- **`random`-dataset tokenizer-mismatch auto-correction** (PR #44708,
  2026-06-08). Previously a silent input-length skew. Recorded as a
  **re-baseline trigger**: `random` numbers taken either side of that date are
  not comparable, which matters for any longitudinal SLO tracking.
- **Warmup boundary extended v0.11–v0.21 → v0.11–v0.25**, verified rather than
  extrapolated: `--num-warmups` default re-read as `0` in the current tree.
- **`output-schema.md` line refs had drifted by hundreds of lines**
  (`BenchmarkMetrics` ~L176-215 → ~L321; JSON assembly ~L989-1020 → ~L1198-1219;
  file now 2284 lines). Re-resolved, with a standing instruction to resolve by
  symbol rather than line.
- **Dataset module moved to a package** — `vllm/benchmarks/datasets.py` is now
  `vllm/benchmarks/datasets/datasets.py`. The old flat path 404s.
- **#32841 run through the new stale-close check** (`skill-improver`
  freshen-patterns §3.0, written earlier the same day). It has **zero comments**,
  so it was *not* bot-closed — but there is no linked fix PR either. Neither
  "fixed" nor "stale" is supported, so the existing hedge is **kept deliberately**
  and `sources.md` now records that reasoning so the next pass doesn't re-open it.
- **Honest gap:** the three rendered-`docs.vllm.ai` rows and two blog rows were
  not re-probed and keep their 2026-04-24 stamps rather than borrowing today's.

