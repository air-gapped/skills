# Per-method deep reference

Load when picking a method, debugging config validation errors, or understanding
why a method behaves differently under load. Companion to the selection matrix
in SKILL.md.

## Table of contents

1. `ngram` — CPU n-gram
2. `ngram_gpu` — GPU-vectorised n-gram (v0.18+)
3. `medusa` — Medusa heads
4. `mlp_speculator` — IBM-flavoured MLP drafter
5. `draft_model` — generic draft LM
6. `eagle` / `eagle3` — EAGLE family
7. `dflash` — block-diffusion parallel drafter
8. `mtp` — native multi-token-prediction heads
9. `suffix` — Arctic suffix decoding
10. `extract_hidden_states` — pass-through for live EAGLE training
11. Config reference — every `--speculative-config` field

All code anchors are relative to `vllm/` unless noted. All methods are V1-only;
there is no `vllm/spec_decode/` V0 path in current main.

## 1. `ngram`

CPU, Numba-JIT. Matches the trailing n-gram of the active sequence against its
own history, returns the tokens that followed the match.

- Proposer: `NgramProposer`, `v1/spec_decode/ngram_proposer.py:12-179` (line refs in this file: v0.32.0)
- Config fields: `prompt_lookup_min`, `prompt_lookup_max`,
  `num_speculative_tokens`. Defaults: min=5, max=5 (TODO in source —
  "arbitrarily chosen").
- At most one Numba thread per TP rank (`min(1, cpu_count // 2)`, then
  divided by TP size, L48-51). Pre-triggers JIT with a 1024-length dummy seq
  on engine start (L57).
- No attention-backend dependency, no draft-model load, no draft-VRAM.
- Good on repetitive prompts (JSON emission, code with boilerplate, agents
  retrying similar queries). Dies on open-ended chat — expected AL 1.3–2.0.

## 2. `ngram_gpu`

GPU-vectorised n-gram via `unfold + argmax`. PR #29184 (v0.18.0), async-scheduler
compatible. Same result as `ngram` but on-device, so integrates with CUDA graphs
and doesn't bottleneck on single-threaded CPU. From v0.32.0 (#40704) `ngram` and
`ngram_gpu` run on Model Runner V2 (`v1/worker/gpu/spec_decode/ngram/`, variable-length
drafts) instead of forcing the V1 runner.

- Proposer (V1 runner): `NgramProposerGPU`, `v1/spec_decode/ngram_proposer_gpu.py:215-470`
- Kernel: `NgramGPUKernel` at L27-213, `torch.compile`-compatible
- Config fields: same as `ngram`
- Prefer this over `ngram` on any recent build. Only drop to CPU `ngram` if
  debugging a GPU-memory ceiling — the GPU version allocates scratch.

## 3. `medusa`

Multiple independent heads on top of the target model's hidden states, each
predicting a token at position k.

- Proposer: `MedusaProposer`, `v1/spec_decode/medusa.py:18-79`
- Config: `model` = Medusa checkpoint (auto-detected when
  `hf_config.model_type == "medusa"`, `config/speculative.py:1356-1357`).
  `num_speculative_tokens` inferred from head count.
- Draft TP defaults to the target TP (`_verify_and_get_draft_tp`); an explicit
  `draft_tensor_parallel_size` must be 1 or the target TP. V1 runner only —
  `medusa` forces Model Runner V1.
- No active development in 2025-2026. Superseded by EAGLE-3. Keep only if
  locked into an existing Medusa checkpoint.
- Expected AL: 1.6–1.75. Draft-compute overhead low (small heads).

## 4. `mlp_speculator`

IBM-family MLP drafter (the "accelerator" models on HF like
`ibm-ai-platform/llama3-8b-accelerator`). Takes previous embeddings, projects
through MLP layers, outputs k tokens.

- Model: `model_executor/models/mlp_speculator.py:61-182`
- Config auto-detection: `config/speculative.py:1358-1359`
  (`hf_config.model_type == "mlp_speculator"`)
- `num_speculative_tokens` defaults to the checkpoint's `n_predict`; above
  `n_predict` it must be divisible by it, else `ValueError`
  (`config/speculative.py:1489-1501`)
- **TP=1 forced** when `draft_tensor_parallel_size` is unset — logs
  *"cannot currently be run with tp>1"* (`_verify_and_get_draft_tp`,
  L1723-1730). V1 runner only.
- Known broken for `llama3-70b-accelerator`: `AttributeError: 'MLPSpeculatorConfig'
  object has no attribute 'num_attention_heads'` (issues #34106, #34163)
- Snowflake benchmarks this at 13.7% accept vs 44.5% for their LSTM-Speculator.
  Historical, not a 2026 choice.

## 5. `draft_model`

Runs a full tiny LM as the drafter. Most flexible — any HF checkpoint — most
expensive.

- Proposer: `DraftModelProposer`, `v1/spec_decode/draft_model.py:17-122` (V1);
  on v0.31.0+ the default is the Model Runner V2 `StandaloneARSpeculator`
  (`v1/worker/gpu/spec_decode/standalone_ar/`, #43091), which at v0.32.0
  captures no CUDA graphs. TLI and `parallel_drafting` keep it on V1.
- Config: `model` (drafter HF path), `num_speculative_tokens`,
  `draft_tensor_parallel_size`, `parallel_drafting` (v0.16+ PARD-style
  parallel forward)
- **TP constraint is hard**: `draft_tensor_parallel_size` MUST equal the
  target's TP, or engine raises ValueError
  (`v1/spec_decode/draft_model.py::_raise_if_draft_tp_mismatch`, L63-77).
  Reason: torch.compile cache corruption on same-machine multi-rank compile.
- Multimodal target: the drafter only warns *"Proceeding with text-only
  speculative decoding"* (`llm_base_proposer.py::_warn_if_multimodal`). M-RoPE
  drafter raises `NotImplementedError` (`_raise_if_mrope`). Setting
  `disable_padded_drafter_batch` raises (`_raise_if_padded_drafter_batch_disabled`).
- Embeddings NOT shared with target (different from EAGLE). Drafter loads its
  own weights — VRAM cost for both.
- `quantization` field can be set separately from target (new in v0.11.1 via
  #28435 for EAGLE; draft_model got parallel support via #24322 in v0.15.0).
- Expected AL for a well-aligned tiny model: 2.5–3.5. Alignment means same
  tokenizer, same training distribution, ideally a distilled pair.

### Heterogeneous vocabularies are supported from v0.25.0 — TLI

**"The drafter must share the target's tokenizer" is no longer unconditional.**
PR [#38174](https://github.com/vllm-project/vllm/pull/38174) (merged
2026-07-02, ships in **v0.25.0**) implements **Token-Level Intersection (TLI)**
speculative decoding: target and draft may have **different but overlapping**
vocabularies. It is based on an ICML 2025 method and closes the long-standing
request #38173.

**TLI is opt-in and does not apply itself.** Set `use_heterogeneous_vocab: true`
inside `--speculative-config`. Leave it unset and vLLM still runs
`verify_equal_vocab_size_if_draft_model()` and rejects the pair — the
mismatched-vocab error you were trying to escape.

```bash
vllm serve <target> --speculative-config \
  '{"method":"draft_model","model":"<other-family-tiny-model>",
    "num_speculative_tokens":4,"use_heterogeneous_vocab":true}'
```

Two **hard** constraints, both raised as `ValueError` at config validation
(`vllm/config/speculative.py`, v0.27.0):

- **`method` must be `draft_model`.** *"use_heterogeneous_vocab only works with
  method='draft_model'"*. TLI is not available for `eagle3`, `mtp`, `dflash`,
  `dspark` or any head-based method — those share the target's embedding space
  by construction.
- **`draft_sample_method` must be `greedy`** (the default). *"use_heterogeneous_vocab
  currently only supports greedy draft sampling."* If you had set
  `draft_sample_method: "probabilistic"` to keep the drafter's full logits for
  the ratio test, TLI and that setting are mutually exclusive today.

This widens drafter selection considerably — a small model from a different
family is now a candidate where previously only same-tokenizer pairs were. Two
soft caveats:

- The vocabularies must *overlap*; TLI operates on the intersection. A drafter
  with a disjoint vocabulary still gains nothing.
- Acceptance-rate behaviour on mismatched pairs is not characterised in this
  skill. Measure it (see `references/metrics.md`) rather than assuming the
  same acceptance you would get from a distilled same-tokenizer pair.

On **pre-v0.25.0** engines the original rule stands: same tokenizer, or
expect silent quality loss.

## 6. `eagle` / `eagle3`

EAGLE heads run on target's hidden states; EAGLE-3 additionally consumes
auxiliary hidden states from designated intermediate layers.

- Proposer (V1 runner): `EagleProposer`, `v1/spec_decode/eagle.py:11-22`
  (thin subclass of `SpecDecodeBaseProposer`, `v1/spec_decode/llm_base_proposer.py:72-1820`)
- Method-enum detection: `"eagle-"` → `eagle`, `"eagle3"` → `eagle3`, substring
  of the lower-cased `model` field (`config/speculative.py:1333-1336`)
- Shares embeddings with target (`llm_base_proposer.py::_maybe_share_embeddings`,
  only when PP world size is 1) — drafter VRAM much smaller than `draft_model`
- `parallel_drafting: true` enables P-EAGLE variant (v0.16+, PR #32887); see
  `eagle3.md`
- **EAGLE-3 target support is the `SupportsEagle3` interface**
  (`model_executor/models/interfaces.py`), not a name list — there is no
  allow-list in `config/speculative.py` (none at v0.32.0). See SKILL.md.
- EAGLE-3 auxiliary layers picked via `eagle_aux_hidden_state_layer_ids` in
  HF config (`v1/worker/gpu/spec_decode/eagle/eagle3_utils.py::get_eagle3_aux_layers_from_config`,
  L100-137; falls back to `dflash_config`/`dspark` `target_layer_ids`)
- Per-target EAGLE-3 head classes exist: `llama_eagle3.py` (first layer is
  `2*hidden_size` to pack embeds + hidden), `deepseek_eagle3.py`, etc.
- No tree speculation: tree attention was removed in v0.21.0 (#42121) and a
  `speculative_token_tree` key is rejected by config validation.
- CUDA-graph dispatcher (`llm_base_proposer.py::_determine_batch_execution_and_padding`)
  synchronises graph mode across DP ranks so they compile the same graphs.

## 7. `dflash`

Block-diffusion parallel drafter, Qwen3-family originated (PR #36847 v0.19+).
Cross-attends non-causally over target hidden states with a mask + next-token
embedding query.

- Proposer: `DFlashProposer`, `v1/spec_decode/dflash.py:23-320` (V1); MRV2
  `v1/worker/gpu/spec_decode/dflash/`, plus `dflash2/` and `lilicorr/` selected
  by checkpoint architecture
- Model: `model_executor/models/qwen3_dflash.py`
- Method-enum detection: `"dflash"` substring in model name, or
  `MuseGlimmerAssistantModel` architecture (`config/speculative.py:1338-1343`)
- **Forces `parallel_drafting: true`** regardless of config (L1468-1469, also
  for `dspark`) — the architecture requires all k tokens in one forward
- **Requires `--attention-backend flash_attn`**. Non-causal attention is not
  supported by Triton or FlashInfer-TRTLLM paths
- Same target-support rule as EAGLE-3 (`SupportsEagle3` interface)
- Multimodal targets allowed: `DFlashProposer._warn_if_multimodal` is a no-op
  override (Qwen3.5 support)
- See `dflash.md` for numbers and the z-lab paper

## 8. `mtp`

Unified entry point for every model family that ships MTP heads in-weights.
Deprecated aliases (`deepseek_mtp`, `glm4_moe_mtp`, `qwen3_next_mtp`, etc.) all
route here via PR #25232. Target model itself is the drafter.

- Proposer: `EagleProposer` with `method="mtp"` (shared code path)
- Auto-detection: `config/speculative.py:1141-1145` logs "method `%s` is
  deprecated and replaced with mtp" when an old alias is seen
- HF-config remapping: `SpeculativeConfig.hf_config_override`
  (`config/speculative.py:661-1073`) rewrites
  `model_type` to the appropriate `*_mtp` variant based on the base
  architecture (see `mtp.md` for the full list)
- `num_speculative_tokens` interaction with model's `n_predict`: see `mtp.md`
  §"num_speculative_tokens rules"
- DeepSeek-V3.2 MTP does **not** force `enforce_eager` (the old FIXME is gone
  by v0.30.0); drop any `--enforce-eager` added for it.
- Expected AL per DeepSeek-V3 tech report §4.5.2: 60–85% on the second token
  (AL ≈ 1.6–1.85).

## 9. `suffix`

Arctic Inference's Suffix Decoding, upstreamed in PR #25784 (v0.12). Uses
suffix trees over the current prompt + a global LRU-cached set of past
completions. No drafter model.

- Proposer: `SuffixDecodingProposer`, `v1/spec_decode/suffix_decoding.py:9-102`.
  V1 runner only — `suffix` forces Model Runner V1.
- Requires `pip install arctic-inference` — engine raises `ImportError` at
  startup if missing (`SpeculativeConfig._validate_suffix_decoding`, L1596-1601)
- Config fields (all prefixed `suffix_decoding_`):
  - `max_tree_depth: int = 24`
  - `max_cached_requests: int = 10000` (0 disables global cache, prompt-only)
  - `max_spec_factor: float = 1.0` — cap is `factor × prefix_match_length`
  - `min_token_prob: float = 0.1` — suffix-tree probability floor
- **`num_speculative_tokens` is dynamic per request** — the proposer returns
  variable-length draft lists. Headline `num_speculative_tokens` acts as a
  ceiling.
- Requests ≥ `max_model_len` are skipped (L55-60)
- Killer workloads: code editing, agent reasoning loops, RL rollouts,
  benchmark harnesses. 1.8–4.5× on SWE-Bench end-to-end.
- Do not enable for open chat — low repetition means AL ≈ 1, wasted tree
  maintenance

## 10. `extract_hidden_states`

Runtime pass-through that extracts target hidden states at specified layers
without verification. Used to accumulate training data for EAGLE-3 while serving.

- Proposer: `ExtractHiddenStatesProposer`,
  `v1/spec_decode/extract_hidden_states.py:28-406`
- **Requires `num_speculative_tokens = 1`** (`assert`, L35) — the "drafting" is
  degenerate; this method's job is to emit states, not tokens
- Requires `eagle_aux_hidden_state_layer_ids` in hf_config (`ValueError`, L64-70)
- Incompatible with `disable_padded_drafter_batch` (`ValueError`, L36-40)
- Not for normal production. Only turn on when building an EAGLE-3 training
  pipeline.

## 11. Config reference — every `--speculative-config` key

All fields from `vllm/config/speculative.py`:

**Required or near-required:**
- `method` — `SpeculativeMethod` literal (auto-detected if `model` path
  contains "eagle", "eagle3", "dflash", or matches a *_mtp model_type)
- `model` — HF path or local dir. Omit for `mtp`, `ngram`, `ngram_gpu`,
  `suffix`, `extract_hidden_states`
- `num_speculative_tokens: int` (required, gt=0)

**Parallelism:**
- `draft_tensor_parallel_size: int | None` — must be 1 or the target TP;
  must equal target TP for `draft_model` (hard error); unset → target TP,
  except `mlp_speculator` → 1
- `parallel_drafting: bool = False` — v0.16+; forced True for `dflash`/`dspark`
- `disable_padded_drafter_batch: bool = False`

**Draft-model tuning:**
- `quantization: QuantizationMethods | str | None` — separate from target
- `moe_backend: MoEBackend | None` — per-draft MoE kernel override (v0.19+,
  PR #37880)
- `max_model_len: int | None` — cap drafter context
- `revision` / `code_revision` — HF hub revision pin
- `draft_load_config: LoadConfig | None` — separate from target

## Choosing `num_speculative_tokens`

Sweep it; do not inherit it. The best N moves **within a single model family**
— measured on Qwen3.6-27B peaking at N=4-5 while Qwen3.6-35B-A3B still climbed
at N=6, and on Qwen3.5-27B peaking at N=5 for GSM8K/MATH500 but N=3 for
MT-Bench. A model-card value is a starting point, not an answer.

| Method | Start at | Then |
|---|---|---|
| `mtp` | **N=1** — least added sequential drafting, so correctness and stability are isolated first | sweep 2..7 |
| `eagle3`, Gemma 4 MTP | checkpoint's recommended N | sweep up; throughput typically rises over the first few values, then plateaus |
| `dflash` | the checkpoint's own value — **`block_size` caps N**, so a 16-block checkpoint tops out there | do not sweep past the cap |

**Stop condition, read off a metric the skill already scrapes.** Raise N while
`vllm:spec_decode_num_accepted_tokens_per_pos` stays healthy at the *late*
positions. When acceptance decays there, the extra candidates add drafting and
verification work while committing nothing — throughput flattens, then
regresses. That per-position histogram, not the aggregate acceptance rate, is
what tells you N is too high.

Sweep against representative traffic, not random tokens: acceptance tracks the
predictability of real output, so a reasoning workload and a chat workload
select different N on the same model.

**N-gram tuning:**
- `prompt_lookup_min: int | None` (default 5)
- `prompt_lookup_max: int | None` (default 5) — TODO in source

**Alternative drafting:**
- `use_local_argmax_reduction: bool = False` — vocab-parallel argmax
- `draft_sample_method: "greedy" | "probabilistic"` (default `"greedy"`)
- No tree field: `speculative_token_tree` was removed in v0.21.0 and is now a
  validation error

**Suffix-specific:**
- `suffix_decoding_max_tree_depth: int = 24`
- `suffix_decoding_max_cached_requests: int = 10000`
- `suffix_decoding_max_spec_factor: float = 1.0`
- `suffix_decoding_min_token_prob: float = 0.1`

**Rejection sampling:**
- `rejection_sample_method: "standard" | "synthetic" | "block"`
  (default `"standard"`)
- `synthetic_acceptance_rates: list[float] | None` /
  `synthetic_acceptance_length: float | None` — for the synthetic sampler,
  a testing tool not a prod knob (v0.19+, PR #38045)

**Covered elsewhere in this skill:** `use_heterogeneous_vocab` (TLI),
`kv_cache_dtype`, `attention_backend`, `enable_adaptive_verification` (`version-gates.md`
version gates). Also present at v0.32.0: `dspark_draft_topk`, `num_speculative_tokens_per_batch_size`,
`disable_eagle_block_drop`, `index_share_for_mtp_iteration` — read their
docstrings in `config/speculative.py` before setting.

**Runtime:**
- `enforce_eager: bool | None` — overrides target's setting

**Deprecated:**
- `tensor_parallel_size` — triggers validation error; use
  `draft_tensor_parallel_size`

Operator rule: always hand-author `--speculative-config` as a single JSON
object. Splitting into `--speculative-model` + `--num-speculative-tokens`
legacy flags is deprecated per the EAGLE subpage.
