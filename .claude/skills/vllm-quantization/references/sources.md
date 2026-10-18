# External sources — rows pinned to vLLM v0.32.0 (current release)

Freshened: 2026-10-18 — every row probed at v0.32.0 (310 URLs; GitHub 502s re-read via `gh`, the deepwiki 429 via browser) and every count re-derived from the tree: CacheDType 19, MoEBackend 23, LinearBackend 21, QuantizationMethods 30. Moved: `fp8` online path removed (v0.31.0), Humming-over-Marlin on SM90, CUTLASS FP4 MoE EP corruption fixed, NVFP4 KV beyond SM100, llm-compressor 0.14.0, ModelOpt 0.47.0 CLI/preset names (the skill's `hf_ptq.py` flags were wrong), AWQ/GPTQ flag trios now one config each.

**2026-09-22 pass:** every row re-probed at v0.30.0 and every v0.27.0-pinned claim reproduced exactly — no false rows. Counts re-derived from the tree rather than carried forward, which corrected two the previous pass had guessed: `QuantizationMethods` 31 → 30 (`bitsandbytes` left in v0.28.0); `CacheDType` **16 → 18**, gaining `nvfp4_4over6` *and* `nvfp4_ds_mla` (#51724), not 17; LinearBackend/MoEBackend **20/17 → 21/22**, not 21/20. Two behaviour changes at v0.30.0 are now recorded in the body: FlashInfer CuTeDSL NVFP4 W4A16 became the SM100/103 default over Marlin (#53014), and GPTQ `g_idx` activation ordering was removed (#54809). External projects: llm-compressor v0.13.0 (2026-08-11), ModelOpt 0.46.1, repo canonically `NVIDIA/Model-Optimizer`.

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
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-10-18 | **drift** | **v0.32.0 (2026-10-18)** is current (`isLatest`); v0.31.0 shipped 2026-10-05, v0.30.0 2026-09-22. Every quantization/KV/kernel item in both release notes walked; applied ones have their own rows below. |
| vLLM source — `QuantizationMethods` | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/model_executor/layers/quantization/__init__.py | 2026-10-18 | fresh (count) / **drift (dispatch)** | **30 values at v0.32.0**, identical list to v0.30.0 (no `__init__.py` diff v0.30.0→v0.32.0). `DEPRECATED_QUANTIZATION_METHODS` still exactly `["fbgemm_fp8", "fp_quant"]`. `get_quantization_config()` maps `awq`/`awq_marlin`/`auto_awq` → `AutoAWQConfig` and `gptq`/`gptq_marlin`/`auto_gptq` → `AutoGPTQConfig` (already so at v0.27.0) — the skill's "`awq` is unfused Triton, use `awq_marlin`" and the per-file `awq.py`/`gptq.py`/`*_marlin.py`/`mxfp8.py`/`bitsandbytes.py` sections were stale; corrected in SKILL.md, formats.md, version-gates.md. |
| vLLM source — `vllm/config/cache.py` `CacheDType` | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/cache.py | 2026-10-18 | **drift** | **19 entries at v0.32.0** — 18 at v0.30.0/v0.31.0 plus `ultraquant_4bit` (#57057, v0.32.0, ROCm `UltraQuantAttentionBackend`). SKILL.md still said "all 16 at v0.27.0" and kv-cache.md lacked `nvfp4_ds_mla` / `nvfp4_4over6` (both since v0.30.0); all three added. FlashInfer `supports_kv_cache_dtype()`: `nvfp4*` on SM100 via TRTLLM; plain `nvfp4` on SM80/90/120 via `_nvfp4_kv_on_fa2()`; `supports_combination()` rejects head size 64 and sinks. |
| vLLM source — `vllm/config/quantization.py` (online schema) | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/quantization.py | 2026-10-18 | drift (additive) | `QuantizationConfigArgs` = `linear`, `moe`, `ignore`, `targets`. `QUANT_KEY_NAMES` at v0.32.0 adds `nvfp4_per_token` and `int4_per_group_32` (gfx942 load-time MXFP4→int4) to the list formats.md had. `_ONLINE_SHORTHANDS` unchanged. |
| vLLM source — `vllm/config/kernel.py` `LinearBackend` / `MoEBackend` | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/kernel.py | 2026-10-18 | **drift** | **21 linear / 23 MoE at v0.32.0** (21/22 at v0.30.0 and v0.31.0). v0.32.0: `flashinfer_moe_ep_mega_cutedsl` → `flashinfer_moe_ep_cutedsl`, `aiter_mega_moe` added (#59685). kernels.md lists were missing `b12x`, `flashinfer_moe_ep_mega_deep_gemm`, `aiter_triton_mxfp4_bf16`, `rdna3` — rewritten from the tree. |
| vLLM PR #50273 — `--linear-backend` for ModelOpt W4A16 | https://github.com/vllm-project/vllm/pull/50273 | 2026-10-18 | fresh | MERGED 2026-07-30, v0.27.0. Default for `auto` has since moved twice: CuTeDSL on SM100/103 (#53014, v0.30.0), Humming on SM90 (#56997, v0.32.0). |
| vLLM docs — GGUF | https://github.com/vllm-project/vllm/blob/v0.32.0/docs/features/quantization/gguf.md | 2026-10-18 | fresh | Still *"GGUF support has migrated to OOT [vllm-gguf-plugin]"* at v0.32.0; `gguf.py` absent. Plugin latest v0.0.5 (2026-08-10). |
| vLLM PR #43841 — cpu_awq removal | https://github.com/vllm-project/vllm/pull/43841 | 2026-10-18 | fresh | MERGED 2026-05-28. SKILL.md format table still offered `cpu_awq` for CPU — replaced with `awq_marlin`. |
| vLLM issue #32220 — NVFP4 KV cache support | https://github.com/vllm-project/vllm/issues/32220 | 2026-10-18 | fresh | CLOSED `COMPLETED` 2026-05-04. Hardware widened in v0.32.0: SM8x/SM12x (#46963), SM90 FA2 (#60620), XQA decode SM12x (#60452). |
| vLLM issue #39407 — Gemma 4 FP8-block logit saturation | https://github.com/vllm-project/vllm/issues/39407 | 2026-10-18 | **stale-closed — no fix** | #39407 and #39049 CLOSED `NOT_PLANNED` by the inactivity bot 2026-09-02. PR #40391 (Gemma4 KV page-size alignment) was **auto-closed unmerged 2026-09-28** (github-actions inactivity comment). Warning stands. |
| vLLM issue #39663 — online FP8 drops bias weights | https://github.com/vllm-project/vllm/issues/39663 | 2026-10-18 | fresh | CLOSED `COMPLETED`, fix PR #41424, earliest stable v0.21.0. |
| vLLM issue #38652 — FP8 KV on MLA garbage at multi-turn | https://github.com/vllm-project/vllm/issues/38652 | 2026-10-18 | fresh | CLOSED `COMPLETED` 2026-05-15 ("Fixed by #37054"). Fix commit 577df69b26 (PR #37054) is in no stable tag before v0.19.0. Skill guidance reversed from avoid-on-MLA on 2026-07-21. |
| vLLM issue #34129 — online FP8 doesn't split MoE across EP | https://github.com/vllm-project/vllm/issues/34129 | 2026-10-18 | fresh | CLOSED `NOT_PLANNED` 2026-06-13 — won't-fix. |
| vLLM PR #44941 — `FusedMoE` → `FusedMoEFactory` | https://github.com/vllm-project/vllm/pull/44941 | 2026-10-18 | fresh | `FusedMoEFactory` is a function (`def FusedMoEFactory(` in `fused_moe/layer.py:88` at v0.32.0), exported from `fused_moe/__init__.py`. |
| vLLM PR #48538 — `nvfp4_per_token` online MoE quant | https://github.com/vllm-project/vllm/pull/48538 | 2026-10-18 | fresh | Shorthand present at v0.32.0; v0.32.0 added a per-token NVFP4 CuTe-DSL MoE backend (#50030) with ReLU2 (#56740). |
| llm-compressor releases | https://github.com/vllm-project/llm-compressor/releases | 2026-10-18 | **drift** | Latest (`isLatest`) **0.14.0 (2026-09-22)**; newest by date are 0.10.0.4 / 0.9.0.5 (2026-10-10) backports. 0.14.0 breaking: Hessian offloading removed (`offload_hessians` absent from `GPTQModifier` at tag 0.14.0), GPTQ group/dynamic actorder removed (#3038), `ModelFreePtqConverter`. `model_free_ptq(model_stub, save_directory, scheme, ...)` signature unchanged. 0.13.0: #2860, `calibration_start/end` rename. |
| NVIDIA ModelOpt releases | https://github.com/NVIDIA/Model-Optimizer/releases | 2026-10-18 | **drift + broken (skill was wrong)** | Repo canonically `NVIDIA/Model-Optimizer`; old docs URL `nvidia.github.io/TensorRT-Model-Optimizer/` **404**, `nvidia.github.io/Model-Optimizer/` 200. Latest **0.47.0 (2026-09-23)**, 0.48.0rc1 2026-10-17. `examples/hf_ptq/hf_ptq.py` @0.47.0 takes `--pyt_ckpt_path`/`--model`, `--qformat`, `--kv_cache_qformat` (default `fp8_cast`), `--recipe`, `--export_path` — the skill's `--model_name_or_path`/`--quant_cfg`/`--export_dir` never matched. 0.47.0 removed `examples/llm_ptq` symlink and short qformat aliases. `config.py` @0.47.0 has `NVFP4_KV_CFG` and `FP8_2D_BLOCKWISE_WEIGHT_ONLY_CFG`, not `NVFP4_KV_CACHE_CFG` / `FP8_PB_WO_CFG` / `MIXED_PRECISION_CFG`; `modelopt_recipes/general/auto_quantize/` @0.47.0 holds `nvfp4_fp8_at_5p4bits` (the `--recipe` help text's `nvfp4_fp8_at_4p8bits` example does not exist). |
| vLLM PR #52890 — AutoRound 2/3/5/6/7-bit on CUDA | https://github.com/vllm-project/vllm/pull/52890 | 2026-10-18 | fresh | `inc/schemes/inc_wna16_scheme.py` present at v0.32.0. |
| vLLM PR #55353 — deprecations scheduled for 0.29 removed | https://github.com/vllm-project/vllm/pull/55353 | 2026-10-18 | fresh | `IndexerKVDType = Literal["auto", "bf16", "fp8", "mxfp4", "nvfp4"]` unchanged at v0.32.0. |
| vLLM PR #51204 — `linear_backend_per_quant` | https://github.com/vllm-project/vllm/pull/51204 | 2026-10-18 | fresh | Field present in `vllm/config/kernel.py` at v0.32.0. |
| vLLM PR #51285 — targeted online quantization (`targets`) | https://github.com/vllm-project/vllm/pull/51285 | 2026-10-18 | fresh | `targets: dict[str, str] \| None` present at v0.32.0. |
| vLLM PR #51392 — online quant on partially pre-quantized checkpoints | https://github.com/vllm-project/vllm/pull/51392 | 2026-10-18 | fresh | MERGED 2026-09-04 (`gh pr view`; the HTML page 502s to curl on size). Doc section present at v0.32.0. |
| vLLM PR #55170 — W4A4 NVFP4 preferred over weight-only on SM120/121 | https://github.com/vllm-project/vllm/pull/55170 | 2026-10-18 | fresh | `_POSSIBLE_NVFP4_KERNELS[CUDA]` at v0.32.0 still lists `FlashInferCuteDslNvFp4W4A16LinearKernel` under the "Weight-only: a fallback" comment after the W4A4 kernels. |
| vLLM PR #53585 — `fp8` online quantization removed | https://github.com/vllm-project/vllm/pull/53585 | 2026-10-18 | **breaking (new)** | v0.31.0. `Fp8Config.__init__` raises on `is_checkpoint_fp8_serialized=False` (`fp8.py:108` at v0.32.0); `weight_utils.get_quant_config` warns and returns `OnlineQuantizationConfig(fp8_per_tensor)` when no checkpoint quant config exists (`weight_utils.py:353`). |
| vLLM PR #51800 / #58001 / #57055 — v0.31.0 removals and restore | https://github.com/vllm-project/vllm/releases/tag/v0.31.0 | 2026-10-18 | **breaking (new)** | Quark silent online quant removed; AllSpark W8A16 removed; `VLLM_ROCM_USE_AITER_FP4_ASM_GEMM` back in `envs.py` (default `False`) — SKILL.md had it as removed. All three commits are in `v0.30.0..v0.31.0`. |
| vLLM PR #56997 — Humming before Marlin on SM90 | https://github.com/vllm-project/vllm/pull/56997 | 2026-10-18 | **default change (new)** | v0.32.0. `utils/humming/priority.py`: `_HUMMING_PREFERRED_CAPABILITIES = frozenset({90})`; `prioritize_humming()` applied in `kernels/linear/__init__.py:_resolve_backend_kernels` and the fp8/nvfp4/mxfp4/mxfp8/int_wna16 MoE oracles. |
| vLLM PR #59042 — CUTLASS FP4 MoE ignored EP `expert_map` | https://github.com/vllm-project/vllm/pull/59042 | 2026-10-18 | **known failure (new)** | v0.32.0 (commit in `v0.31.0..v0.32.0`). Release notes: *"silent CUTLASS NVFP4/MXFP4 MoE corruption under EP"*. Introduction version not established — skill says "before v0.32.0". |
| vLLM PR #60079 — MXFP4 MoE CUTLASS W4A4 + BF16 fallback | https://github.com/vllm-project/vllm/pull/60079 | 2026-10-18 | default change (new) | v0.32.0. `_warn_on_bf16_fallback` logs *"No Mxfp4 MoE backend supports activation=%s ... Falling back to '%s' with BF16 activations."* |
| vLLM PR #55684 — online re-quantization of linear layers | https://github.com/vllm-project/vllm/pull/55684 | 2026-10-18 | new-feature | v0.32.0. `docs/features/quantization/online.md` @v0.32.0: supported source is serialized ModelOpt MXFP8 linear only; checkpoint exclusions not enforced. |
| vLLM PRs #46963 / #60620 / #60452 / #57057 — KV dtype hardware | https://github.com/vllm-project/vllm/pull/46963 | 2026-10-18 | new-feature | v0.32.0. See the `CacheDType` row for the gating code. |
| vLLM PRs #60140 / #60281 — GLM-5.x FP8 KV default | https://github.com/vllm-project/vllm/pull/60281 | 2026-10-18 | default change (new) | v0.32.0. `models/config.py`: `GlmMoeDsaForCausalLM` sets `cache_dtype = "fp8_e4m3"` when `auto`, CUDA, SM100 family. |
| vLLM PR #57163 — `sleep(level=2)` zeroed CT KV scales | https://github.com/vllm-project/vllm/pull/57163 | 2026-10-18 | known failure (new) | v0.32.0. PR body: NaN logprobs + wrong first token after a weights-only reload; other KV quant methods unaffected. |
| vLLM issue #39137 — `_init_kv_cache_quant` fp8_e5m2 gate | https://github.com/vllm-project/vllm/issues/39137 | 2026-10-18 | **fixed (skill said open)** | CLOSED `COMPLETED` 2026-06-18 by PR #45040 (closer per GraphQL timeline), first stable v0.24.0. kv-cache.md landmine 3 said "patch in discussion". |
| vllm-bnb-plugin | https://github.com/vllm-project/vllm-bnb-plugin | 2026-10-18 | new | Named by `docs/features/quantization/bnb.md` @v0.32.0; repo latest v0.0.3. |
| vLLM b12x backend (SM120/121) | https://github.com/vllm-project/vllm/blob/v0.32.0/docs/features/quantization/b12x.md | 2026-10-18 | new | b12x FP4 MoE backend commit (#52018) first in v0.29.0; MoE has no EP / expert maps. IQ2_XS/IQ2_XXS/Q8_0 block codecs #59604 (v0.32.0). |

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
