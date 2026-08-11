# Improvement backlog — vllm-quantization

Tracks improvement attempts that could not be applied in a single atomic
iteration, plus changes the metric registered this pass.

## Resolved — 2026-08-11 (freshen, v0.25.1 -> v0.27.1)

Two minors of drift. **The three highest-value findings were not release-note
items at all — they were wrong config keys that had been wrong for longer than
this window.** Prior passes audited issue states and release notes; none diffed
the config dataclasses.

- **The online-quantization schema in this skill never existed upstream.**
  SKILL.md taught `--quantization-config-file online.yaml` and `formats.md`
  taught `global_scheme` / `linear_scheme_override` / `moe_scheme_override` /
  an `OnlineQuantScheme` enum. The real surface is **`--quantization-config`**
  carrying `{linear: {weight, activation}, moe: {...}, ignore: [...]}` with
  names from `QUANT_KEY_NAMES` (`vllm/config/quantization.py`). Verified
  identical at v0.25.1 and v0.27.0 plus `docs/features/quantization/online.md`
  — so this was never right for the documented window. A user copying it got a
  flag error.
- **Two `--quantization` values had been removed and were still advertised.**
  `gguf` migrated out-of-tree to `vllm-gguf-plugin`; `cpu_awq` was folded into
  `awq_marlin` (#43841, 2026-05-28). Both had full sections in `formats.md`.
  Catalog corrected 29 -> **31 verified values**, and
  `DEPRECATED_QUANTIZATION_METHODS` recorded as exactly
  `["fbgemm_fp8", "fp_quant"]` rather than the skill's editorial list.
- **A half-finished reversal from the previous pass.** The 2026-07-21 pass
  established `nvfp4` KV had shipped and updated `kv-cache.md` — but SKILL.md
  still said "roadmap" in **two** places, and `kv-cache.md` still listed it
  under "Roadmap items". *A partial reversal is worse than none: the stale
  copies license each other.* Grep the whole skill for the old wording after
  any reversal.
- SKILL.md's KV-dtype section claimed "all 11", listed 13, and omitted
  `float16`, `bfloat16`, `int4_per_token_head`. Actual: **16 at v0.27.0**.
- Added the missing operator lever: **`--linear-backend` / `--moe-backend`**
  with authoritative value lists from `vllm/config/kernel.py`, plus the trap
  that ModelOpt W4A16 **silently ignored `--linear-backend`** until #50273
  (v0.27.0). The skill mapped kernel dispatch but never the override flag.
- Version window v0.14 -> v0.27; `version-gates.md` gained v0.26.0, v0.27.0
  and v0.27.1 sections. **v0.27.1 (2026-08-11)** ships one change — quantized
  DSpark Markov heads (#50424), a new W4A16 surface on a spec-dec drafter.
  Recorded that the **v0.27.1 container images shipped before the GitHub release**; PyPI lag does not
  install yet.
- **Warnings deliberately kept:** #39407 (Gemma 4 FP8-block) still OPEN,
  #39663 (online FP8 drops bias) still OPEN and survived its stale-bot window.
  #34129 (online FP8 + MoE/EP) closed **`NOT_PLANNED`** — won't-fix, which
  makes the prefer-a-pre-quantized-checkpoint rule *more* load-bearing.

**Process hazard hit this run:** a concurrent git operation in the parent
session reverted the working tree mid-pass and silently discarded ~30 applied
edits. They were re-applied from a script with per-edit exact-match assertions
(fails loudly rather than double-applying). If a freshen pass runs alongside
anything that commits, verify edits are on disk before reporting.

**Not re-probed, declared rather than assumed:** llm-compressor releases and
NVIDIA ModelOpt releases. Budget went to the config-key defects.

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

- **Populate v0.21.0 / v0.20.x PR-level quantization deltas** (Dim 5/9) —
  `references/version-gates.md` new `## v0.21.0` and `## v0.20.x` sections.
  Added as stubs this pass (window + ship-date facts only). Itemising the
  per-release quantization PRs requires a `gh` release-body sweep that the
  APPLY stage could not run (Bash output channel degraded). Fill on next freshen.

## Resolved — 2026-07-21 (freshen, v0.21.0 -> v0.25.1)

- **The predicted inversion happened: #38652 is fixed, and the guidance is
  reversed.** The prior pass filed this exactly right — *"the 'avoid FP8 KV on
  MLA multi-turn' guidance inverts if a fix lands"* — and named all three call
  sites. #38652 closed **2026-05-15** with *"Fixed by #37054"*.

  **The skill already contained the answer and had not joined it up.**
  `troubleshooting.md` line 12 said "avoid FP8 KV on MLA multi-turn — open"
  while line 16, *two rows down the same table*, said "Fixed PR #37054, v0.19".
  `kv-cache.md` items 1 and 5 had the identical split. Upstream has now
  confirmed both rows describe one defect. Updated all five locations
  (`SKILL.md` pitfall 1 and the `kv_cache_scheme` note, `kv-cache.md` items 1
  and 5, `troubleshooting.md` rows 12/16 and triage step 3) and recorded the
  mechanism from the PR body: FlashInfer applied `layer._[qkv]_scale`
  unconditionally even on unscaled BF16 QKV, and MLA needs K/V to share one
  scale so only one of `_k_scale`/`_v_scale` was handled.

  **The lag is the transferable lesson.** PR #37054 merged **2026-03-18**; the
  issue stayed OPEN until 2026-05-15; this skill carried the warning until
  today. §3.0 says a closed issue is not a fixed issue — this is the mirror:
  **an open issue is not a live bug.** Check for a merged fix, not just a state
  field. Where a skill states both "X is broken" and "PR Y fixed X", that
  internal contradiction is itself the signal.
- **`config/cache.py:18-34` had drifted, as predicted.** The `CacheDType`
  `Literal` has grown to 16 entries at v0.25.1 and the skill's table was missing
  two: **`int4_per_token_head`** and **`nvfp4`**. The `nvfp4` row also said
  "Roadmap" — the feature request (#32220) closed `COMPLETED` **2026-05-04**
  (maintainer closing on a contributor's work, not a bot), and v0.25.0 shipped
  NVFP4 KV cache with skip-layers sliding window (#42890). Replaced the
  line-range citation with "grep the `CacheDType = Literal[...]` block".
  `quantization/__init__.py:107-184` is still in-bounds (191-line file) but now
  sits within 7 lines of EOF — flagged to switch to a symbol reference.
- **llm-compressor drift, plus a release-reading trap.** Recorded latest was
  `v0.10.0.1`; it is now **0.12.0** (2026-06-15). But the newest release *by
  publish date* is **0.7.1.3 (2026-06-26)**, a backport on an older branch —
  sorting the release list by date picks the wrong version. Documented the
  parallel maintenance lines (0.7.1.x / 0.9.0.x / 0.10.0.x / 0.11.0 / 0.12.0)
  and added the 0.11.0 (DDP AWQ + SmoothQuant, up to 3.2x) and 0.12.0
  (Transformers v5, MoE linearization refactor, multi-GPU model-free PTQ)
  feature rows. Flagged that 0.12.0's dataset-split API change removes legacy
  multi-stage logic, so pre-0.12 recipes may need updating.
- **Version-gate window extended v0.21 -> v0.25.1**, including the pin that
  matters: **serve NVFP4 multi-GPU on >= v0.25.1**, since v0.25.0 corrupts
  output through the fused allreduce+RMSNorm+quant path (PR #48330). Frontmatter
  description range corrected v0.14->v0.21 => v0.14->v0.25.
- **Other issue states re-probed:** #39407 (Gemma 4 FP8_BLOCK) still OPEN with a
  fix in flight (PR #40391 reworked against main) — avoid-FP8-block stands;
  #39663 (online FP8 drops bias) OPEN but **stale-bot-marked**, so a future
  CLOSED will mean abandonment; #40252's fix is scoped narrowly to Qwen3-Next
  fused `in_proj_qkvz`/`in_proj_ba`, which is why the general "audit the
  `ignore` list" rule is kept. ModelOpt 0.43.0 -> 0.45.0 (skill pins no version,
  no body change needed).

**Still open from prior passes:** the per-file TOC additions (Dim 2) and the
cross-skill eval-harness pointer (Dim 4) were not attempted — this pass's budget
went to the factual inversion, which was the higher-value item.

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
