# Per-method deep reference

Load when picking a method, debugging config validation errors, or understanding
why a method behaves differently under load. Companion to the selection matrix
in SKILL.md.

## Table of contents

1. `ngram` — CPU n-gram
2. `ngram_gpu` — GPU-vectorised n-gram (v0.18+)
3. `medusa` — removed in v0.33.0
4. `mlp_speculator` — removed in v0.33.0
5. `draft_model` — generic draft LM
6. `eagle` / `eagle3` — EAGLE family
7. `dflash` — block-diffusion parallel drafter
8. `mtp` — native multi-token-prediction heads
9. `suffix` — suffix decoding (GPU; Arctic-backed on ≤ v0.33.x)
10. `extract_hidden_states` — pass-through for live EAGLE training
11. Config reference — every `--speculative-config` field

All code anchors are relative to `vllm/` unless noted. Model Runner V2 is the only
runner from v0.34.0; speculators live in `v1/worker/gpu/spec_decode/<method>/`
(`config.py` holds each method's `SpeculatorConfig`).

## 1. `ngram`

Matches the trailing n-gram of the active sequence against its
own history, returns the tokens that followed the match.

- Proposer (v0.34.0): the GPU speculator `v1/worker/gpu/spec_decode/ngram/` serves both `ngram` and `ngram_gpu`.
- Config fields: `prompt_lookup_min`, `prompt_lookup_max`,
  `num_speculative_tokens`. Defaults: min=5, max=5 (TODO in source —
  "arbitrarily chosen").
- No attention-backend dependency, no draft-model load, no draft-VRAM.
- ≤ v0.32.x turned async scheduling off for `ngram` (explicit
  `--async-scheduling` was a `ValueError`); `ngram_gpu` kept it on.
- Good on repetitive prompts (JSON emission, code with boilerplate, agents
  retrying similar queries). Dies on open-ended chat — expected AL 1.3–2.0.

## 2. `ngram_gpu`

GPU-vectorised n-gram via `unfold + argmax`. PR #29184 (v0.18.0), async-scheduler
compatible. Same result as `ngram` but on-device, so integrates with CUDA graphs
and doesn't bottleneck on single-threaded CPU. From v0.32.0 (#40704) both
methods run on Model Runner V2 (`v1/worker/gpu/spec_decode/ngram/`, variable-length drafts).

- Config fields: same as `ngram`
- v0.34.0: `ngram` and `ngram_gpu` share this GPU speculator; the GPU path
  allocates scratch memory.

## 3. `medusa`

**Removed in v0.33.0** (#61701): `method: "medusa"` or a Medusa draft checkpoint
fails config validation. Retrain as EAGLE-3. On ≤ v0.32.x only:

- Model Runner V1 only; `model` = Medusa checkpoint (auto-detected from
  `hf_config.model_type == "medusa"`); `num_speculative_tokens` inferred from
  head count; draft TP defaults to the target TP.
- Expected AL: 1.6–1.75.

## 4. `mlp_speculator`

**Removed in v0.33.0** (#61701), same failure as `medusa`. On ≤ v0.32.x only:

- Model Runner V1 only; draft TP forced to 1 when `draft_tensor_parallel_size` is
  unset (logs *"cannot currently be run with tp>1"*), so a TP=8 target runs the
  drafter on one GPU.
- `num_speculative_tokens` defaults to the checkpoint's `n_predict`; above it,
  must be divisible by it.
- Known broken for `llama3-70b-accelerator`: `AttributeError: 'MLPSpeculatorConfig'
  object has no attribute 'num_attention_heads'` (issue #34106, closed unfixed).

## 5. `draft_model`

Runs a full tiny LM as the drafter. Most flexible — any HF checkpoint — most
expensive.

- Speculator: `StandaloneARSpeculator`
  (`v1/worker/gpu/spec_decode/standalone_ar/`, #43091). Captures CUDA graphs
  from v0.34.0 (#60989); ≤ v0.33.x captured none.
- Config: `model` (drafter HF path), `num_speculative_tokens`,
  `draft_tensor_parallel_size`. PARD (`parallel_drafting: true` on a draft
  model) is rejected from v0.34.0.
- **Keep `draft_tensor_parallel_size` equal to the target's TP** (leave it
  unset). ≤ v0.33.x raised a `ValueError` on a mismatch (torch.compile cache
  corruption on same-machine multi-rank compile); v0.34.0 accepts 1 or the
  target TP without that check.
- Multimodal target: the draft runs text-only (≤ v0.33.x logged *"Proceeding
  with text-only speculative decoding"*); an M-RoPE drafter raises
  `NotImplementedError`. `disable_padded_drafter_batch` no longer exists
  (v0.34.0: unknown key).
- Embeddings NOT shared with target (different from EAGLE). Drafter loads its
  own weights — VRAM cost for both.
- `quantization` field can be set separately from target (new in v0.11.1 via
  #28435 for EAGLE; draft_model got parallel support via #24322 in v0.15.0).
- Expected AL for a well-aligned tiny model: 2.5–3.5. Alignment means same
  tokenizer, same training distribution, ideally a distilled pair.

### Heterogeneous vocabularies (TLI): v0.25.0–v0.33.x only

v0.34.0 removed Token-Level Intersection (#38174, v0.25.0) with Model Runner V1:
`use_heterogeneous_vocab` is an unknown key and `verify_equal_vocab_size_if_draft_model()`
rejects any draft whose vocabulary size differs from the target's. Pick a drafter
from the target's tokenizer family.

On v0.25.0–v0.33.x TLI is opt-in (`use_heterogeneous_vocab: true` in
`--speculative-config`; without it the equal-vocab check rejects the pair) and
raises `ValueError` unless `method` is `draft_model`, `draft_sample_method` is
`greedy` (default), and (v0.33.0+) `use_local_argmax_reduction` is `false`. The
vocabularies must overlap; acceptance on mismatched pairs is uncharacterised, so
measure it. v0.31.x crashes with a device-side assert (fixed v0.32.0, #59541).

## 6. `eagle` / `eagle3`

EAGLE heads run on target's hidden states; EAGLE-3 additionally consumes
auxiliary hidden states from designated intermediate layers.

- Speculator: `v1/worker/gpu/spec_decode/eagle/` (`EagleSpeculator`)
- Method-enum detection: `"eagle-"` → `eagle`, `"eagle3"` → `eagle3`, substring
  of the lower-cased `model` field (`EagleSpeculatorConfig.matches`)
- Shares embeddings with target (only when PP world size is 1) — drafter VRAM
  much smaller than `draft_model`
- P-EAGLE (`parallel_drafting: true`, v0.16–v0.33.x) is rejected from v0.34.0,
  including `peagle` Speculators checkpoints; see `eagle3.md`
- **EAGLE-3 target support is the `SupportsEagle3` interface**
  (`model_executor/models/interfaces.py`), not a name list — there is no
  allow-list in `config/speculative.py` (none at v0.34.0). See SKILL.md.
- EAGLE-3 auxiliary layers picked via `eagle_aux_hidden_state_layer_ids` in
  HF config (`v1/worker/gpu/spec_decode/eagle/eagle3_utils.py::get_eagle3_aux_layers_from_config`;
  falls back to `dflash_config`/`dspark` `target_layer_ids`)
- Per-target EAGLE-3 head classes exist: `llama_eagle3.py` (first layer is
  `2*hidden_size` to pack embeds + hidden), `deepseek_eagle3.py`, etc.
- No tree speculation: tree attention was removed in v0.21.0 (#42121) and a
  `speculative_token_tree` key is rejected by config validation.

## 7. `dflash`

Block-diffusion parallel drafter, Qwen3-family originated (PR #36847 v0.19+).
Cross-attends non-causally over target hidden states with a mask + next-token
embedding query.

- Speculator: `v1/worker/gpu/spec_decode/dflash/`, plus `dflash2/`, `lilicorr/` and
  (v0.33.0+) `xpress/` selected by checkpoint architecture
- Model: `model_executor/models/qwen3_dflash.py`
- Method-enum detection: `"dflash"` substring in model name, or
  `MuseGlimmerAssistantModel` architecture
- **Always drafts in parallel** (also `dspark`); `parallel_drafting` is a
  deprecated no-op — the architecture requires all k tokens in one forward
- **Requires `--attention-backend flash_attn`**. Non-causal attention is not
  supported by Triton or FlashInfer-TRTLLM paths
- Same target-support rule as EAGLE-3 (`SupportsEagle3` interface)
- Multimodal targets allowed (Qwen3.5 support)
- See `dflash.md` for numbers and the z-lab paper

## 8. `mtp`

Unified entry point for every model family that ships MTP heads in-weights.
Deprecated aliases (`deepseek_mtp`, `glm4_moe_mtp`, `qwen3_next_mtp`, etc.) all
route here via PR #25232. Target model itself is the drafter.

- Speculator: `v1/worker/gpu/spec_decode/mtp/` (`multi_module_mtp/` when the
  head has several modules and `num_speculative_tokens` > 1)
- Auto-detection: a log line "method `%s` is deprecated and replaced with mtp"
  appears when an old alias is seen
- HF-config remapping: `SpeculativeConfig.hf_config_override` rewrites
  `model_type` to the appropriate `*_mtp` variant based on the base
  architecture (see `mtp.md` for the full list)
- `num_speculative_tokens` interaction with model's `n_predict`: see `mtp.md`
  §"num_speculative_tokens rules"
- DeepSeek-V3.2 MTP does **not** force `enforce_eager` (the old FIXME is gone
  by v0.30.0); drop any `--enforce-eager` added for it.
- Expected AL per DeepSeek-V3 tech report §4.5.2: 60–85% on the second token
  (AL ≈ 1.6–1.85).

## 9. `suffix`

Suffix Decoding, upstreamed in PR #25784 (v0.12). No drafter model.

- **v0.34.0+ (#60339):** GPU speculator on Model Runner V2
  (`v1/worker/gpu/spec_decode/suffix/`), builds on `ngram_gpu`; no
  `arctic-inference` package. Each request matches against its own prompt and
  output (longest suffix up to `suffix_decoding_max_tree_depth`) and against a
  GPU corpus of finished responses (last 2 and last 4 tokens as lookup keys).
  The draft **always has `num_speculative_tokens` tokens**; unmatched slots are
  filled with the last sampled token, and every slot is verified unless
  adaptive verification trims it. Default N is `min(8, max_tree_depth)`; keep N
  moderate.
  - Config: `suffix_decoding_max_tree_depth` (24), `suffix_decoding_max_cached_requests`
    (10000; 0 disables the corpus), `suffix_decoding_corpus_tokens` (1048576;
    0 disables the corpus, oldest responses overwritten first).
    `suffix_decoding_max_spec_factor` and `suffix_decoding_min_token_prob` are
    deprecated no-ops.
  - `enable_adaptive_verification: true` (full CUDA graphs and an attention
    backend that replays variable-length decode batches, e.g. `TRITON_ATTN` or
    FlashAttention 3) is the fix for suffix losing to no-spec at high
    concurrency.
  - The corpus is shared across all requests regardless of `cache_salt` or LoRA
    adapter. Where requests must not influence each other, or seeded sampling
    must reproduce, set `suffix_decoding_corpus_tokens: 0` (and leave adaptive
    verification off for reproducibility).
- **≤ v0.33.x:** Model Runner V1 only, proposer a wrapper around Arctic's
  `SuffixDecodingCache`; engine raises `ImportError` at startup without
  `pip install arctic-inference`. Per-request draft length was dynamic
  (`max_spec_factor`, `min_token_prob` active; `num_speculative_tokens` a ceiling).
- Killer workloads: code editing, agent reasoning loops, RL rollouts,
  benchmark harnesses. 1.8–4.5× on SWE-Bench end-to-end (Arctic-era numbers).
- Do not enable for open chat — low repetition means AL ≈ 1.

## 10. `extract_hidden_states`

Runtime pass-through that extracts target hidden states at specified layers
without verification. Used to accumulate training data for EAGLE-3 while serving.

- Speculator: `v1/worker/gpu/spec_decode/extract_hidden_states.py`
- **Requires `num_speculative_tokens = 1`** (`ValueError`) — the "drafting" is
  degenerate; this method's job is to emit states, not tokens
- Requires `eagle_aux_hidden_state_layer_ids` in hf_config (`ValueError`)
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
  must equal target TP for `draft_model` (hard error); unset → target TP
- `draft_decode_context_parallel_size: int | None` (v0.34.0+) — 1 or the target's
  decode context parallel size; defaults to the target's, except `dflash`/`dspark`
  (1 unless full-attention MLA)
- `parallel_drafting` — deprecated no-op from v0.34.0 (v0.16–v0.33.x: P-EAGLE /
  PARD switch); `true` on anything but `dflash`/`dspark` is a `ValueError`

**Batch-size schedule (Dynamic SD, v0.24.0+):**
- `num_speculative_tokens_per_batch_size: [[start_bs, end_bs, K], ...]` —
  inclusive concurrency ranges; `K: 0` disables drafting in that range. This is
  the only batch-size gate: `disable_by_batch_size` is not a key and fails
  config validation.
- Silently dropped (warning, static K used) with `--data-parallel-size > 1`.

**Draft-model tuning:**
- `quantization: QuantizationMethods | str | None` — separate from target
- `draft_lm_head_quantization: "fp8" | "nvfp4" | None` (v0.33.0+, #59973) —
  gives an `eagle` / `eagle3` / `mtp` drafter a quantized private copy of the
  target `lm_head` it shares; the target still verifies with its own head, so
  only acceptance length can move. `ValueError` for any other
  method, for Gemma 4 MTP, or when the head dtype differs from the model
  dtype. Costs extra VRAM for the copy — with `--kv-cache-memory-bytes`, leave
  room for it. Try it when the vocabulary is large and concurrency is low.
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

**Suffix-specific:** see §9.

**Rejection sampling:**
- `rejection_sample_method: "standard" | "synthetic" | "block" | "fly"`
  (default `"standard"`)
- `"block"` — use only on ≥ v0.33.0: earlier builds reuse random draws
  across verification rounds and skew the sampled distribution (#61161)
- `"fly"` (v0.33.0+, #53987) — **lossy**: accepts an isolated target-rejected
  draft token at a high-entropy position when the next `fly_window_size`
  drafts pass. Opt in only when a measured quality drop is acceptable; logs
  *"FLy verification is a lossy speculative decoding method"* once.
  - `fly_window_size: int | None` — default `min(6, num_speculative_tokens - 1)`;
    must be < `num_speculative_tokens`
  - `fly_entropy_threshold: float = 0.3`, `fly_entropy_top_k: int = 3`
  - `ValueError` with `num_speculative_tokens < 2` or
    `method: "extract_hidden_states"`
  - Do not combine `"fly"` or `"synthetic"` with `method: "suffix"` on a
    multi-tenant endpoint — see SKILL.md pitfall 6
- `synthetic_acceptance_rates: list[float] | None` /
  `synthetic_acceptance_length: float | None` — for the synthetic sampler,
  a testing tool not a prod knob (v0.19+, PR #38045)

**Covered elsewhere in this skill:** `kv_cache_dtype`, `attention_backend`,
`enable_adaptive_verification` (`version-gates.md` version gates). Also present
at v0.34.0: `dspark_draft_topk`, `disable_eagle_block_drop`,
`index_share_for_mtp_iteration`, `speculator_options` (custom speculators) —
read their docstrings in `config/speculative.py` before setting.

**Custom speculators (v0.34.0+, experimental, #63205):** `method` may name a
speculator registered by a vLLM plugin through
`vllm.v1.worker.gpu.spec_decode.speculator_config.register_speculative_method`;
`custom_method` then holds the name and `method` the built-in it extends.
Options go in `speculator_options`. Replaces the removed `custom_class` method
(v0.22.0–v0.33.x, callable proposer).

**Runtime:**
- `enforce_eager: bool | None` — overrides target's setting

**Deprecated:**
- `tensor_parallel_size` — triggers validation error; use
  `draft_tensor_parallel_size`

Operator rule: always hand-author `--speculative-config` as a single JSON
object. Splitting into `--speculative-model` + `--num-speculative-tokens`
legacy flags is deprecated per the EAGLE subpage.
