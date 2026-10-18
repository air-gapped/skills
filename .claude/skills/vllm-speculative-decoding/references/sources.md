# External-reference provenance

Freshened: 2026-10-18 — every row probed at v0.32.0 (41 URLs 200, 75 vLLM PR/issue states batched, ArcticInference/PyPI/Docker Hub/HF versions); `MTPModelTypes` (27) and the 13-method enum are unchanged since v0.30.0, but `draft_model` (v0.31.0) and n-gram (v0.32.0) moved to Model Runner V2, TLI broke on v0.31.x MRV2 (#59541), and ~60 line anchors were re-measured at the tag, which exposed four wrong claims (Medusa TP=1, MTP warning text, DFlash multimodal raise, eagle3 auto-detect by aux-layer IDs) plus the removed `speculative_token_tree`.

**ArcticInference v0.3.0 (2026-08-28) rebased onto vLLM v0.26.0**, superseding the v0.2.0 note that pinned it to vLLM 0.14.1. The repo is active, not dormant. Still the latest release on 2026-10-18 (PyPI `arctic-inference` 0.3.0). The version-lag caution still applies — v0.26.0 trails the current v0.32.0 — but the gap it warns about is much narrower than the rows below describe.

**Added 2026-09-22** — [Exploring Speculative Decoding in vLLM on AMD GPUs](https://vllm.ai/blog/2026-08-23-speculative-decoding-amd-gpus) (vLLM Blog, 2026-08-23, AMD + Embedded LLM). Source for `methods.md` §"Choosing `num_speculative_tokens`" and the DeepSpec publisher row in `eagle3.md`. **Despite the title it is not AMD-specific** — the drafting methods, memory overhead and N-tuning loop are hardware-neutral; AMD is only what the sweeps ran on. The per-model throughput ratios in its appendix are deliberately NOT imported: they are workload-specific and the post says so itself. (The site labels it "242 min read"; it is ~15.7k words, roughly 60-70 min — the estimator is counting 90 tables / 522 rows.)

Cited upstream sources for this skill, probed on the `Last verified` date. Used
by skill-improver Dim 9 (staleness) and by anyone auditing whether a claim is
still current.

Method: `gh pr view` / `gh api repos/.../contents/...?ref=<tag>` / `gh api
repos/.../releases` / HF `/api/models/<id>`. URLs are the canonical upstream;
for pinned line numbers in vLLM source, the skill cites the current file path
(line numbers drift across refactors — re-verify on upgrade).

**Version discipline for this pass:** claims are probed against **v0.27.0**
(2026-08-10) except the DSpark Markov head, probed against **v0.27.1**
(2026-08-11, current stable). v0.27.1 is a single-change patch, so v0.27.0
probes remain valid for everything else and were deliberately **not**
re-stamped. The v0.27.1 **container images** shipped 10:24-10:42Z, before the release; PyPI lag is not a gate here. (`pip install
vllm==0.27.1` does not resolve.

**Headline of the 2026-08-11 pass (v0.25.1 → v0.27.1):** the 2026-07-21 pass
documented **TLI as a capability but never as a configuration**. It told the
reader the same-tokenizer rule was relaxed, and stopped there. TLI is opt-in
(`use_heterogeneous_vocab: true`) and carries two hard `ValueError` constraints
that existed *at v0.25.1 already* — `method` must be `draft_model`, and
`draft_sample_method` must be `greedy`. Anyone acting on the old text would have
hit the exact vocab-size rejection the feature exists to avoid.
**Lesson: when a release note announces a capability, read the config
dataclass, not just the PR title. A feature you cannot spell is not documented.**

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM PR #48915 — per-request spec-dec acceptance | https://github.com/vllm-project/vllm/pull/48915 | 2026-10-18 | **MERGED 2026-08-20**, commit `7cfb97e3`. Ancestry in-clone: not in v0.28.0, **is** in v0.29.0. Server-start flag `--per-request-spec-decode-metrics summary|detailed`, off by default, response unchanged when off; stats land in the top-level `metrics` object under `speculative_decoding` with `mean_acceptance_length`. |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-10-18 | **v0.32.0 (2026-10-18T06:50:48Z)** latest; v0.31.0 2026-10-05; v0.30.0 2026-09-22; v0.29.0 2026-09-09. PyPI `vllm` 0.32.0. Version-gate table extended to v0.32.0. |
| PR #50424 — quantized DSpark Markov heads | https://github.com/vllm-project/vllm/pull/50424 | 2026-10-18 (**ref=v0.32.0**) | @ v0.32.0: `class DSparkMarkovHead` L48 still takes `quant_config` (L67) into `ParallelLMHead` `markov_w2` (L72-77). MERGED 2026-08-03, **the sole change in v0.27.1**. Verified in `vllm/model_executor/models/qwen3_dspark.py` @ v0.27.1: `class DSparkMarkovHead` (L36) takes `quant_config` (L55) and forwards it to its `ParallelLMHead`-based `markov_w2` (L59-64); `Qwen3DSparkModel` passes `self.quant_config` (L103). W4A16 `markov_w2` weights incl. `weight_scale_2` now load through normal quantization dispatch; unquantized behaviour preserved. **The skill made no claim that the head must be unquantized, so nothing was retracted** — this is a pure addition. Implication recorded in pitfall 8: on ≤ v0.27.0 the head loads unquantized regardless of the checkpoint. |
| vllm/config/speculative.py — `SpeculativeMethod` enum | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/speculative.py | 2026-10-18 | **@ v0.32.0 (2004 lines):** 13 base methods, `MTPModelTypes` 27 entries incl. `mtp` — identical set to v0.30.0; `RejectionSampleMethod` and `DraftSampleMethod` unchanged; `SpeculativeConfig` field set identical to v0.30.0 (diffed). New since v0.30.0: `_DRAFT_VLLM_CONFIG_OVERRIDES` + `apply_draft_overrides()` (draft `moe_backend`/`attention_backend`/`kv_cache_dtype`), `build_draft_parallel_config(draft_model_config=)` drops inherited EP for dense drafts (#56930). The five entries added 22 → 27 between v0.27.0 and v0.30.0 (`dots3_note_mtp`, `qwen4_exp_mtp`, `bailing_hybrid_v3_mtp`, `hy_v4_mtp`, `glm5_next_mtp`) are now in `mtp.md`. **Prior @ v0.27.0:** Base-method count unchanged at 13 — frontmatter still correct. Structure unchanged: `EagleModelTypes = ["eagle", "eagle3", "extract_hidden_states", MTPModelTypes, DFlashModelTypes]`, plus `NgramGPUTypes` and `DSparkModelTypes`. **`MTPModelTypes` grew 20 → 22**: new `kimi_k3_mtp`, `inkling_mtp`. `RejectionSampleMethod` unchanged (`standard`/`synthetic`/`block`). File is 1435 lines (was 1276 at v0.25.1). |
| vllm/config/speculative.py — TLI config surface | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/config/speculative.py | 2026-10-18 | @ v0.32.0: field L463, both `ValueError`s L1854-1864, equal-vocab check otherwise L1866-1867 — unchanged. New: TLI is V1-runner-only (see #59541 row). **Prior @ v0.27.0: broken (skill under-specified).** `use_heterogeneous_vocab: bool = False` (line 151). Validation at lines 1324-1334 raises on two conditions: *"use_heterogeneous_vocab only works with method='draft_model'"* and *"use_heterogeneous_vocab currently only supports greedy draft sampling."* When the flag is `False`, `verify_equal_vocab_size_if_draft_model()` still runs. **Both constraints were present at v0.25.1** — this is a documentation miss, not new drift. Fixed in SKILL.md pitfall 7, the version-gate row, and `methods.md`. |
| PR #48787 — `kv_cache_dtype` in `speculative_config` | https://github.com/vllm-project/vllm/pull/48787 | 2026-10-18 | MERGED 2026-07-16, ships **v0.26.0**. New `SpeculativeConfig` field — the only field added between v0.25.1 and v0.27.0 (verified by diffing the dataclass field set). Docstring: *"KV cache dtype for the draft model. When `None`, the draft inherits the target model's `--kv-cache-dtype`."* |
| PR #48639 — `sample_from_anchor` from speculators config | https://github.com/vllm-project/vllm/pull/48639 | 2026-10-18 | MERGED 2026-07-20, ships **v0.27.0**. Lives in `vllm/transformers_utils/configs/speculators/algos.py` — it is a **checkpoint** field, not a CLI flag, for both DFlash and DSpark. Docstring: *"Default False (anchor is a bonus token, only mask tokens predict, yielding block_size - 1 speculative tokens)."* Captured in `references/dflash.md`. |
| PR #48892 — multi-layer MTP speculator on MRV2 | https://github.com/vllm-project/vllm/pull/48892 | 2026-10-18 | MERGED 2026-07-30, **v0.27.0**. Added as a version-gate row. |
| aux_hidden_states model support | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/model_executor/models/interfaces.py | 2026-10-18 | **@ v0.32.0:** `class SupportsEagle3` L1675, `supports_eagle3()` L1737-1744, `eagle3_utils.py` raises `RuntimeError("Model does not support EAGLE3 interface")` L19-20; no allowlist in `config/speculative.py` (`aux_hidden_states_supported` 0 hits); aux-consuming method tuple L626-631. `eagle3.md`/`dflash.md`/`methods.md` still printed the old 14-name list as live — rewritten. **Prior:** fresh — re-verified, no regression. `class SupportsEagle3(SupportsEagleBase, Protocol)` at line 1449, `supports_eagle3()` at 1510, `set_aux_hidden_state_layers()` at 1463. `config/speculative.py` still contains **no** allowlist — only the method tuple that consumes aux states (line 307). The 2026-07-21 finding holds two minors later; version markers bumped v0.25.1 → v0.27.0. |
| PR #38174 — TLI universal spec-dec | https://github.com/vllm-project/vllm/pull/38174 | 2026-10-18 | MERGED 2026-07-02, ships v0.25.0. Not re-probed this pass (merged PR, state cannot regress); its *config surface* was probed instead — see the TLI row above. |
| PR #44744 — spec-dec DoS fix | https://github.com/vllm-project/vllm/pull/44744 | 2026-10-18 | Security / DoS in the v0.24.0 notes: remote DoS via invalid recovered-token reinjection. Gate ≥ v0.24.0 stands. Not re-probed (merged). |
| PR #25916 — EAGLE-3 preamble fix (+32% MTBench) | https://github.com/vllm-project/vllm/pull/25916 | 2026-10-18 | MERGED 2025-10-02. v0.11.1 gate still correct. Re-probed 2026-08-18: still MERGED. |
| PR #36847 — DFlash method | https://github.com/vllm-project/vllm/pull/36847 | 2026-10-18 | MERGED 2026-03-30. v0.19 gate still correct. Re-probed 2026-08-18: still MERGED. |
| PR #32887 — Unified Parallel Drafting (P-EAGLE enabler) | https://github.com/vllm-project/vllm/pull/32887 | 2026-10-18 | MERGED 2026-02-05. v0.16 gate still correct. Re-probed 2026-08-18: still MERGED. |
| PR #29184 — ngram_gpu + async scheduler | https://github.com/vllm-project/vllm/pull/29184 | 2026-10-18 | MERGED 2026-03-07. v0.18 gate still correct. Re-probed 2026-08-18: still MERGED. |
| ArcticInference repo (suffix + LSTM speculators) | https://github.com/snowflakedb/ArcticInference | 2026-10-18 | Latest release **v0.3.0 (2026-08-28)**, unchanged; PyPI 0.3.0. vLLM v0.32.0 `_validate_suffix_decoding` (L1596-1601) only checks `arctic_inference` imports (`vllm/utils/import_utils.py::has_arctic_inference`), while its error text says `pip install arctic-inference==0.1.1`. **Prior:** **Not dormant** — v0.2.0 released 2026-06-26, repo pushed 2026-07-14. The new risk is version lag, not abandonment: v0.2.0's release notes say "Rebase to vLLM 0.14.1" (#242) while current vLLM is 0.27.x — verify ArcticInference-vs-vLLM compat before relying on the `suffix` method on a modern stack. |
| yuhuili/EAGLE3-LLaMA3.1-Instruct-8B HF checkpoint | https://huggingface.co/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B | 2026-10-18 | Present (HF API 2026-10-18: 9,776 downloads/30d, lastModified 2025-09-19). Earlier: 245k downloads, Apache-2.0, last modified 2025-09-19. Re-probed 2026-08-18: page live, ~244k monthly downloads. |
| EAGLE 3.1 announcement (vLLM blog) | https://vllm.ai/blog/2026-05-26-eagle-3-1 | 2026-10-18 | Config-driven extension of eagle3 (same `method` enum). Captured in `references/eagle3.md`. Page 200 on 2026-10-18; `eagle3` still in the v0.32.0 enum. |
| HF EAGLE-3 + DFlash recipe survey | `hf models list --search {eagle3,dflash} --limit 500` | 2026-10-18 | **HF API 2026-10-18: 757 eagle3 repos, ≥1000 dflash repos (API page cap)** — the April families table is a snapshot of a corpus now ~2× larger; still not re-derived. Snapshot of 2026-04-30: 369 EAGLE-3 + 97 DFlash repos, five recurring recipe families. Tabulated in `references/training-data-recipes.md`. Not re-probed. **Re-probed 2026-08-18 via HF API search: ~523 eagle3 / ~679 dflash repos — the tabulated recipe families in `training-data-recipes.md` are an April snapshot of a corpus that has since roughly doubled; re-derive on next deep pass.** |
| `vllm/vllm-openai` image tags | https://hub.docker.com/v2/repositories/vllm/vllm-openai/tags/ | 2026-10-18 | **v0.32.0:** `v0.32.0` pushed 2026-10-18T10:54Z, `-cu129*`/`-aarch64*`/`-x86_64-zstd` 10:53-10:58Z — about 4h *after* the 06:50Z GitHub release; PyPI already 0.32.0. **Prior (v0.27.1):** **`v0.27.1` images exist and predate the GitHub release** — `v0.27.1` (10.53 GB) pushed 10:34:40Z, `-x86_64` 10:24:20Z, `-cu129` 10:41:15Z, `-cu129-ubuntu2404` 10:42:47Z; release published 10:47:49Z. This stack runs the image, so image availability — not the PyPI wheel — is the gate. (PyPI `info.version` was still 0.27.0 when checked.) |
| PR #50514, #46994 — EAGLE3/MTP spec-dec under pipeline parallel (MRV2) | https://github.com/vllm-project/vllm/pull/50514 | 2026-10-18 (**ref=v0.32.0**) | MERGED. @ v0.32.0: still no EAGLE3+PP entry in the MRV2-unsupported list; `build_draft_parallel_config` keeps `pipeline_parallel_size=1` (L1778). Verified in `vllm/config/vllm.py` @ v0.30.0: the `"EAGLE3 with pipeline parallelism"` entry in `_get_v2_model_runner_unsupported_features()` present at v0.29.0 is gone at v0.30.0. `vllm/config/speculative.py` `build_draft_parallel_config()` now hardcodes the draft's `pipeline_parallel_size=1` instead of copying the target's. |
| PR #54788, #54826 — draft `moe_backend`/`attention_backend` honored on MRV2 | https://github.com/vllm-project/vllm/pull/54788 | 2026-10-18 (**ref=v0.32.0**) | MERGED. @ v0.32.0 the override moved into `SpeculativeConfig.apply_draft_overrides()`, which `load_eagle_model()` calls (`eagle/utils.py` L83) and which also applies the draft `kv_cache_dtype`. `vllm/v1/worker/gpu/spec_decode/eagle/utils.py::load_eagle_model()` at v0.30.0 now overrides `vllm_config.kernel_config.moe_backend` / `vllm_config.attention_config.backend` from `speculative_config.moe_backend` / `.attention_backend` when set; absent at v0.29.0, where the draft silently inherited the target's backend under MRV2 (the v0.19.0/v0.21.0 gates only ever applied to the legacy `vllm/v1/spec_decode/` path). |
| PR #52228 — adaptive verification via online acceptance estimator | https://github.com/vllm-project/vllm/pull/52228 | 2026-10-18 (**ref=v0.32.0**) | MERGED. @ v0.32.0 (and already @ v0.30.0) `VllmConfig._validate_adaptive_verification` also rejects LoRA, PP > 1 and cudagraph modes without full graphs; V1 runner rejects it outright. `OnlineAcceptanceEstimator` at `acceptance_estimator.py:313`. `draft_model` reaches it only from v0.31.0 (MRV2). `vllm/config/speculative.py` validation at v0.30.0 only rejects `enable_adaptive_verification` when `method != "dspark"` **and** `use_local_argmax_reduction` is set — the prior "only supported with DSpark" hard rule is gone. New `vllm/v1/worker/gpu/spec_decode/acceptance_estimator.py::OnlineAcceptanceEstimator` wired into the shared `DraftModelSpeculator` base class; DSpark falls back to it automatically when its checkpoint has no trained confidence head. |
| PR #56122 — dual-key Gumbel-max watermarking + spec-dec | https://github.com/vllm-project/vllm/pull/56122 | 2026-10-18 (**ref=v0.32.0**) | MERGED. @ v0.32.0 the doc's "Speculative decoding" section is unchanged; #56801 (v0.32.0) changed request semantics only (omitted = watermark on, unsupported request modes warn and fall back) and context dedup now covers drafter watermarking. `docs/features/watermarking.md` @ v0.30.0 adds a "Speculative decoding" section: requires probabilistic draft sampling + standard rejection sampling + `dspark`/`eagle`/`eagle3`/`mtp`; non-native algorithms need `allow_target_only_watermarking: true` in `--watermark-config`. `dual_key_gumbel` is natively compatible — draft tokens use key A, rejection-recovery/bonus tokens use key B. |
| PR #43091 — `draft_model` on Model Runner V2 | https://github.com/vllm-project/vllm/pull/43091 | 2026-10-18 (**ref=v0.31.0/v0.32.0**) | MERGED 2026-09-28, v0.31.0. `draft_model` is in the MRV2-unsupported list at v0.30.0, absent at v0.31.0. MRV2 class at v0.32.0: `v1/worker/gpu/spec_decode/standalone_ar/speculator.py::StandaloneARSpeculator`, whose `init_cudagraph_manager`/`capture` are `pass` ("CUDA graph not yet supported"). |
| PR #59541 — TLI kept on Model Runner V1 | https://github.com/vllm-project/vllm/pull/59541 | 2026-10-18 | MERGED 2026-10-06; commit `ad0f67a7ec` is in v0.32.0, not v0.31.0 (`git log v0.31.0..v0.32.0 -S`). PR body: on v0.31.x `use_heterogeneous_vocab=True` runs on MRV2, which has no `VocabMapping` → device-side assert; `VLLM_USE_V2_MODEL_RUNNER=0` avoids it. Fix adds "heterogeneous-vocabulary draft models" to `_get_v2_model_runner_unsupported_features`. Not in the v0.32.0 release notes. |
| PR #40704 — n-gram GPU speculator on MRV2 | https://github.com/vllm-project/vllm/pull/40704 | 2026-10-18 (**ref=v0.32.0**) | MERGED 2026-10-06. `ngram`/`ngram_gpu` in the MRV2-unsupported list at v0.31.0, gone at v0.32.0; class `v1/worker/gpu/spec_decode/ngram/speculator.py::NgramGPUSpeculator`. |
| PR #56930 — dense draft + EP-enabled MoE target | https://github.com/vllm-project/vllm/pull/56930 | 2026-10-18 | MERGED 2026-09-17, v0.31.0 (not in v0.30.0). Regression from #55914 (in v0.30.0, not v0.29.0): *"Number of experts in the model must be greater than 0 when expert parallelism is enabled"*. |
| PR #57934 — LiLiCorr drafter | https://github.com/vllm-project/vllm/pull/57934 | 2026-10-18 (**ref=v0.32.0**) | MERGED 2026-09-25, v0.31.0. `docs/features/speculative_decoding/lilicorr.md` @ v0.32.0: `method: "dflash"`, `LiLiCorrDraftModel` architecture, MRV2 auto-selected, `num_speculative_tokens` = `block_size - 1` recommended, larger unsupported. Dispatch in `v1/worker/gpu/spec_decode/__init__.py`. |
| PR #57633 — Llama 4 / Mistral Large 3 EAGLE drafters + multimodal | https://github.com/vllm-project/vllm/pull/57633 | 2026-10-18 | MERGED 2026-10-09; in v0.32.0, not v0.31.0. Regression from #50417 (in v0.28.0). Fixes #57630. |
| PR #59655 — DeepSeek V4/V4.1 NVFP4 MTP/DSpark experts | https://github.com/vllm-project/vllm/pull/59655 | 2026-10-18 | MERGED 2026-10-08; not in v0.31.0, listed in v0.32.0 notes. PR body: AL 1.00 (0 of 604,200 drafts) on `DeepSeek-V4.1-Flash-NVFP4` with DSpark, only hint `w1_weight_scale_2 must match w3_weight_scale_2`. |
| PR #57104 — KV connector + MTP deadlock | https://github.com/vllm-project/vllm/pull/57104 | 2026-10-18 | MERGED 2026-09-16, v0.31.0 notes (Scheduler). |
| PR #43310 — per-request spec-dec metrics on `/inference/v1/generate` | https://github.com/vllm-project/vllm/pull/43310 | 2026-10-18 | MERGED 2026-09-20, v0.31.0 notes. Same `metrics.speculative_decoding` shape; streaming returns it in the final usage chunk with `stream_options.include_usage`; still needs `--per-request-spec-decode-metrics` (`ObservabilityConfig`, default `"none"`, @ v0.32.0). |
| PR #42121 — tree attention removed | https://github.com/vllm-project/vllm/pull/42121 | 2026-10-18 | Commit `b1728c1e66`, first in v0.21.0. `speculative_token_tree` absent from `vllm/` at v0.30.0 and v0.32.0; config dataclasses use `extra="forbid"` (`vllm/config/utils.py`), so the key is a validation error. Skill text that still recommended removing/using it was rewritten. |
| v0.32.0 line anchors (spec-dec source) | https://github.com/vllm-project/vllm/tree/v0.32.0/vllm/v1/spec_decode | 2026-10-18 (**ref=v0.32.0**) | Re-measured with `git show v0.32.0:<path>`. Line counts: `config/speculative.py` 2004, `v1/spec_decode/metrics.py` 281 (byte-identical to v0.30.0), `draft_model.py` 122, `llm_base_proposer.py` 1860, `dflash.py` 320, `suffix_decoding.py` 102, `extract_hidden_states.py` 406, `eagle.py` 22. Draft TP equality lives in `draft_model.py::_raise_if_draft_tp_mismatch` (L63-77), not `speculative.py`; `_verify_and_get_draft_tp` (L1712-1743) forces TP=1 only for `mlp_speculator`. MTP divisibility `ValueError` L1493-1501; re-run warning L1377-1385. Metric counters L229-259, PromQL docstring L177-196. The canonical repro script moved to `examples/features/speculative_decoding/spec_decode_offline.py` (already there at v0.30.0). |

## Classifications summary (2026-08-11 pass)

- **broken: 1** — the TLI documentation gap. Highest-value finding of the pass:
  the capability was named without its flag or its two hard constraints.
- **new-feature: 4** — `kv_cache_dtype` in `--speculative-config` (#48787,
  v0.26.0); `sample_from_anchor` loaded from the speculators config (#48639,
  v0.27.0); multi-layer MTP on MRV2 (#48892, v0.27.0); quantized DSpark Markov
  heads (#50424, v0.27.1).
- **version-drift: 1** — `MTPModelTypes` 20 → 22 (Kimi K3, Inkling now ship
  native MTP heads); method-selection table row 1 updated.
- **fresh: 1** — the `SupportsEagle3` capability interface, re-verified at
  v0.27.0 with no regression. Base method count still 13.
- **not re-probed: 7** — the four original PRs (merged; state cannot regress),
  ArcticInference, the yuhuili checkpoint, the EAGLE 3.1 blog, and the
  training-data recipe survey. Declared, not assumed fresh.

## Re-verification recipe

```bash
# Method enum + MTP alias list + config surface, all from one fetch
gh api "repos/vllm-project/vllm/contents/vllm/config/speculative.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" > /tmp/spec.py
sed -n '/^MTPModelTypes = Literal\[/,/^\]/p;/^SpeculativeMethod = Literal\[/,/^\]/p' /tmp/spec.py
grep -n "use_heterogeneous_vocab\|draft_sample_method\|kv_cache_dtype\|rejection_sample_method" /tmp/spec.py

# Diff the whole SpeculativeConfig field set against the previous tag — this is
# what catches a new knob that no release note headlines
for t in vA.B.C vX.Y.Z; do
  gh api "repos/vllm-project/vllm/contents/vllm/config/speculative.py?ref=$t" \
    --header "Accept: application/vnd.github.raw" | grep -oP '^    \w+:' | sort -u > "/tmp/f_$t.txt"
done
diff /tmp/f_vA.B.C.txt /tmp/f_vX.Y.Z.txt

# EAGLE-3 support is an interface, not a list — confirm it still is
gh api "repos/vllm-project/vllm/contents/vllm/model_executor/models/interfaces.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" | grep -n "class SupportsEagle3\|def supports_eagle3"

# DSpark / DFlash drafter internals (quant plumbing, sample_from_anchor)
gh api "repos/vllm-project/vllm/contents/vllm/model_executor/models/qwen3_dspark.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" | grep -n "markov_w2\|quant_config"
gh api "repos/vllm-project/vllm/contents/vllm/transformers_utils/configs/speculators/algos.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" | grep -n "sample_from_anchor" -B4 -A2

# Arctic Inference freshness
gh api repos/snowflakedb/ArcticInference/releases/latest --jq '{tag:.tag_name, published:.published_at}'

# Is the release actually installable yet?
curl -s https://pypi.org/pypi/vllm/json | python3 -c \
  'import json,sys;d=json.load(sys.stdin);print(d["info"]["version"])'

# HF checkpoint existence
curl -s "https://huggingface.co/api/models/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B" | head -c 400
```
