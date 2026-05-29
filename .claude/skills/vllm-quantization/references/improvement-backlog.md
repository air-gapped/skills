# Improvement backlog — vllm-quantization

Tracks improvement attempts that could not be applied in a single atomic
iteration, plus changes the metric registered this pass.

## Open

- **Add a 1-line TOC to each reference file over 100 lines** (Dim 2) —
  `references/{formats.md (352L), modelopt.md (303L), llm-compressor.md (288L),
  version-gates.md (192L), kv-cache.md (122L)}`. Not applied this pass: the
  APPLY-stage tool-output channel intermittently returned empty for Read/Bash
  on these four reference files (formats/modelopt/llm-compressor/kv-cache), so
  no verified anchor text was available to insert a TOC without risking a
  blind, possibly-corrupting edit. version-gates.md was editable (full content
  verified) but its TOC was deferred to keep this a single coherent batch.
  Re-run once tool output is stable; insert a `## Contents` block listing the
  `##` headings at the top of each file.

- **Add a cross-skill eval-harness pointer** (Dim 4) — `SKILL.md` near
  "Always eval on actual traffic" (L44-46). Recon hypothesis 5 (+1). Deferred:
  the parent skill set has both `vllm-benchmarking` and `aiperf`; choosing the
  right pointer and phrasing is a judgment call better made with the body fully
  re-readable. One-line addition, no structural risk — pick up next pass.

- **Re-probe load-bearing freshness items** (Dim 9) — next freshen run:
  (1) vLLM issue #38652 OPEN state — the "avoid FP8 KV on MLA multi-turn"
  guidance inverts if a fix lands (`SKILL.md` L172, `troubleshooting.md` L12,
  `kv-cache.md` L98); (2) source line ranges `quantization/__init__.py:107-184`
  (`SKILL.md` L68) and `config/cache.py:18-34` (`SKILL.md` L91) — fragile across
  the v0.20/v0.21 shipments. Left unverified 2026-05-28 (probe budget spent on
  the higher-value release-tag drift); recorded in `sources.md`.

- **Populate v0.21.0 / v0.20.x PR-level quantization deltas** (Dim 5/9) —
  `references/version-gates.md` new `## v0.21.0` and `## v0.20.x` sections.
  Added as stubs this pass (window + ship-date facts only). Itemising the
  per-release quantization PRs requires a `gh` release-body sweep that the
  APPLY stage could not run (Bash output channel degraded). Fill on next freshen.

## Resolved this pass

- Bumped production-pin / version-window from "pin v0.19.1 / v0.20.0 pre-release"
  to "v0.21.0 stable (2026-05-15), run v0.21.0+" (Dim 9) — `SKILL.md` L191.
- Changed the stated window `v0.14 → v0.19.1` → `v0.14 → v0.21` in three places
  (Dim 8) — `SKILL.md` description-block (L5) and "What to read next" (L207),
  plus `version-gates.md` title (L1).
- Added `## v0.21.0` and `## v0.20.x` sections to `version-gates.md` recording
  v0.20.0 shipped stable 2026-04-27 (correcting the "pre-release" label) and
  v0.21.0 stable 2026-05-15 (Dim 8/9).
- Trimmed the operator-pain-point shortlist from 12 items to the 6
  highest-frequency ones, deferring the hardware-/version-gated tail to
  `references/troubleshooting.md` via a one-line pointer (Dim 6) — `SKILL.md`
  L168-185.
- Re-stamped the vLLM-releases row in `sources.md` to 2026-05-28 with the
  corrected classification, and added a "next freshen should re-probe" note for
  #38652 + the two source line-ranges (Dim 9).
