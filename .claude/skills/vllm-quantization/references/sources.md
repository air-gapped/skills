# External sources — last verified 2026-09-15 (rows pinned to vLLM v0.27.0; current release v0.29.0)

**2026-09-15 pass:** every row re-probed and every v0.27.0-pinned claim reproduced exactly — no false rows found. Four counts have since moved upstream and are flagged at their rows: `bitsandbytes` left `QuantizationMethods` in v0.28.0 (31 → 30 values), `CacheDType` gained `nvfp4_4over6` (16 → 17), and LinearBackend/MoEBackend went 20/17 → 21/20. Two external projects also moved: ModelOpt shipped 0.46.0 and 0.46.1, and its repo is now canonically `NVIDIA/Model-Optimizer`.

Freshness audit for externally-referenced material in SKILL.md. Probes were
issued via the `gh` CLI and GitHub API. Re-run the freshen loop when the
rolling delta exceeds two minor vLLM releases.

**Headline of the 2026-08-11 pass (v0.25.1 → v0.27.0, two minors):** three
*wrong-config-key* defects, all pre-dating this window and all missed by
earlier passes that only chased issue states:

- The **online-quantization advanced schema** in SKILL.md and `formats.md` named
  a flag (`--quantization-config-file`) and keys (`global_scheme`,
  `linear_scheme_override`, `moe_scheme_override`) that do not exist. The real
  surface is `--quantization-config` with `{linear, moe, ignore}`.
- **`gguf` left the tree** for an out-of-tree plugin, and **`cpu_awq` was folded
  into `awq_marlin`** (#43841). Both were still listed as `--quantization` values.
- SKILL.md still called **`nvfp4` KV "roadmap"** in two places, while this
  skill's own `kv-cache.md` and this file had recorded it shipped since the
  2026-07-21 pass. *Lesson: after reversing a claim, grep the whole skill for
  the old wording — a partial reversal is worse than none, because the two
  statements license each other.*

## Probe results

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-09-15 | re-stamped | **v0.27.0 (2026-08-10)** is current; v0.26.0 shipped 2026-07-27. Window advanced two minors from v0.25.1. |
| vLLM source — `QuantizationMethods` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/model_executor/layers/quantization/__init__.py | 2026-09-15 | **drift** | **31 values at v0.27.0**, not 29. Delta vs v0.25.1 is exactly one addition: `nvfp4_per_token` (#48538, v0.26.0). Values the skill had never listed: `auto_awq`, `auto_gptq`, `humming`, `deepseek_v4_fp8`, `fp8_per_channel`. Values the skill listed that **no longer exist**: `gguf`, `cpu_awq`. `DEPRECATED_QUANTIZATION_METHODS` is exactly `["fbgemm_fp8", "fp_quant"]`. File is 192 lines; the old `107-184` citation was replaced with a symbol grep, as the previous pass recommended. |
| vLLM source — `vllm/config/cache.py` `CacheDType` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/config/cache.py | 2026-09-15 | **drift (SKILL.md only)** | 16 entries at v0.27.0 — unchanged in count since v0.25.1. `kv-cache.md` was already correct; **SKILL.md was not**: it claimed "all 11", listed 13, and omitted `float16`, `bfloat16`, `int4_per_token_head`. Fixed. |
| vLLM source — `vllm/config/quantization.py` (online schema) | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/config/quantization.py | 2026-09-15 | **broken (skill was wrong)** | `QuantizationConfigArgs` has fields `linear`, `moe` (each a `QuantSpec` of `weight`/`activation`) and `ignore`; names resolve through `QUANT_KEY_NAMES`. Identical at v0.25.1 — the skill's `global_scheme` / `linear_scheme_override` / `moe_scheme_override` / `OnlineQuantScheme` description and its `--quantization-config-file` flag were **never** correct for this window. Corroborated by `docs/features/quantization/online.md` @ v0.27.0. |
| vLLM source — `vllm/config/kernel.py` `LinearBackend` / `MoEBackend` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/config/kernel.py | 2026-09-15 | new (added to `kernels.md`) | 20 `--linear-backend` values, 17 `--moe-backend` values. The skill documented kernel *dispatch* but never the operator's override flag. |
| vLLM PR #50273 — `--linear-backend` for ModelOpt W4A16 | https://github.com/vllm-project/vllm/pull/50273 | 2026-09-15 | fresh (MERGED 2026-07-30, v0.27.0) | Body: *"`ModelOptNvFp4W4A16LinearMethod` currently hardcodes usage of the Marlin kernel, ignoring `--linear-backend`."* Post-fix `auto` still selects Marlin. **On ≤ v0.26.0 the flag is a silent no-op for ModelOpt W4A16.** |
| vLLM docs — GGUF | https://github.com/vllm-project/vllm/blob/v0.27.0/docs/features/quantization/gguf.md | 2026-09-15 | **deprecation (removal)** | *"GGUF support has migrated to OOT [vllm-gguf-plugin]."* `quantization/gguf.py` is absent from the v0.27.0 tree; only `docs/` and `tests/plugins_tests/gguf/` remain. Install `vllm-gguf-plugin`, serve `repo_id:QUANT` with the base model's tokenizer. |
| vLLM PR #43841 — cpu_awq removal | https://github.com/vllm-project/vllm/pull/43841 | 2026-09-15 | **deprecation (removal)** | *"[CPU] Migrate cpu_awq into awq_marlin"*, merged 2026-05-28. `quantization/cpu_wna16.py` gone at v0.27.0. |
| vLLM issue #32220 — NVFP4 KV cache support | https://github.com/vllm-project/vllm/issues/32220 | 2026-09-15 | fixed (CLOSED `COMPLETED` 2026-05-04) | Re-confirmed. `nvfp4` is an accepted `CacheDType` at v0.27.0. SKILL.md's two remaining "roadmap" mentions were removed this pass. |
| vLLM issue #39407 — Gemma 4 FP8-block logit saturation | https://github.com/vllm-project/vllm/issues/39407 | 2026-09-15 | **CLOSED `NOT_PLANNED` 2026-09-02 by the inactivity bot — no fix** | Sibling #39049 closed the same way the same day. PR #40391 (Gemma4 KV-cache page-size alignment) is still **open**. **"Avoid FP8-block on Gemma 4" still stands**; the closure is an autoclose, not a resolution. |
| vLLM issue #39663 — online FP8 drops bias weights | https://github.com/vllm-project/vllm/issues/39663 | 2026-09-15 | **CLOSED `COMPLETED` 2026-09-02 — genuinely fixed** | Not an autoclose: a third party re-ran the issue's own reproduction on v0.26.0 and got output matching bf16, and the author closed it with "#41424 is the fix". PR #41424 ("Fix FP8 Bias Loading") merged 2026-05-03, merge `db9a84e0`, earliest stable tag **v0.21.0** (in-clone ancestry). Warning retired above v0.21.0. The MoE half of the prefer-pre-quantized rule is unaffected — #34129 is still won't-fix. |
| vLLM issue #34129 — online FP8 doesn't split MoE across EP | https://github.com/vllm-project/vllm/issues/34129 | 2026-09-15 | **CLOSED `NOT_PLANNED` 2026-06-13** | **Closed as won't-fix, not fixed.** The skill's "for any MoE model prefer a pre-quantized checkpoint" guidance is now *more* load-bearing, not less. Kept and re-cited. |
| vLLM PR #44941 — `FusedMoE` → `FusedMoEFactory` | https://github.com/vllm-project/vllm/pull/44941 | 2026-09-15 | new (recorded in `version-gates.md`) | MERGED 2026-07-31, v0.27.0. This skill never named the class, so no body text changed. **`vllm-performance-tuning` does name it — out-of-scope finding, reported to the parent.** |
| vLLM PR #48538 — `nvfp4_per_token` online MoE quant | https://github.com/vllm-project/vllm/pull/48538 | 2026-09-15 | new-feature | MERGED 2026-07-16, ships v0.26.0. New `--quantization` shorthand; added to the catalog and the frontmatter. |
| llm-compressor releases | https://github.com/vllm-project/llm-compressor/releases | 2026-09-15 | **drift** | Latest **0.13.0 (2026-08-11)**. Breaking there: sparsity-preserving logic removed from GPTQ (#2860), `calibration_epoch_start/end` → `calibration_start/end`; NVFP4/FP8 scheme names intact, REAP pruning composes with quantization. Parallel maintenance lines persist — **sort by version, not by publish date**. SKILL.md mention bumped 0.12.0 → 0.13.0. |
| NVIDIA ModelOpt releases | https://github.com/NVIDIA/TensorRT-Model-Optimizer/releases | 2026-09-15 | fresh | Still **0.45.0 (2026-07-06)** — no release since. The skill pins no ModelOpt version, so drift here cannot make the body wrong. |

## Classification summary

- **broken (skill stated something false): 3** — online-quant config schema
  (flag + keys); `gguf` / `cpu_awq` listed as live flag values; `nvfp4` KV
  called "roadmap" in SKILL.md.
- **drift: 2** — `--quantization` catalog 29 → 31; SKILL.md KV-dtype list
  (count and three missing entries).
- **new-feature: 2** — `--linear-backend` / `--moe-backend` override axis
  (#50273); `nvfp4_per_token` (#48538).
- **fresh (warning confirmed still true): 2** — #39407, #39663. Both re-probed
  precisely *because* deleting a still-true warning is the highest-damage
  outcome of this mode.
- **deprecation (won't-fix): 1** — #34129 closed `NOT_PLANNED`.
- **not re-probed: 2** — llm-compressor, ModelOpt. Declared, not assumed fresh.

## Re-probe cadence

- Quantization layer churns at ~one format per vLLM minor. Re-run this
  freshen pass on each new minor release or every ~6 weeks, whichever is
  shorter.
- **Next pass must start with `vllm/config/quantization.py` and
  `vllm/config/kernel.py`.** Three passes audited issue states and release
  notes while the config schema documented in the skill was wrong the whole
  time. Diff the config dataclasses first, issue states second.

## Re-verification recipe

```bash
# Flag catalog + deprecations (authoritative)
gh api "repos/vllm-project/vllm/contents/vllm/model_executor/layers/quantization/__init__.py?ref=vX.Y.Z" \
  --header 'Accept: application/vnd.github.raw' \
  | sed -n '/^QuantizationMethods = Literal\[/,/^\]/p;/^DEPRECATED_QUANTIZATION_METHODS/,/^\]/p'

# KV-cache dtypes
gh api "repos/vllm-project/vllm/contents/vllm/config/cache.py?ref=vX.Y.Z" \
  --header 'Accept: application/vnd.github.raw' \
  | sed -n '/^CacheDType = Literal\[/,/^\]/p'

# Online-quant schema + kernel-backend values
gh api "repos/vllm-project/vllm/contents/vllm/config/quantization.py?ref=vX.Y.Z" \
  --header 'Accept: application/vnd.github.raw' | grep -n "QUANT_KEY_NAMES" -A 15
gh api "repos/vllm-project/vllm/contents/vllm/config/kernel.py?ref=vX.Y.Z" \
  --header 'Accept: application/vnd.github.raw' \
  | sed -n '/^MoEBackend = Literal\[/,/^\]/p;/^LinearBackend = Literal\[/,/^\]/p'

# A format that vanished — confirm removal rather than assuming a rename
gh api "repos/vllm-project/vllm/git/trees/vX.Y.Z?recursive=1" --jq '.tree[].path' | grep -i gguf

# Issue states — read the CLOSING COMMENT, not just the state field
for i in 39407 39663 34129 32220; do
  gh issue view "$i" -R vllm-project/vllm --json number,state,stateReason,updatedAt
done
```
