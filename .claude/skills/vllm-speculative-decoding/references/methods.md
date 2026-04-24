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

- Proposer: `NgramProposer`, `v1/spec_decode/ngram_proposer.py:12-161`
- Config fields: `prompt_lookup_min`, `prompt_lookup_max`,
  `num_speculative_tokens`. Defaults: min=5, max=5 (TODO in source —
  "arbitrarily chosen").
- Runs in a single Numba thread per TP rank (line 48). Pre-triggers JIT with a
  1024-length dummy seq on engine start (line 57).
- No attention-backend dependency, no draft-model load, no draft-VRAM.
- Good on repetitive prompts (JSON emission, code with boilerplate, agents
  retrying similar queries). Dies on open-ended chat — expected AL 1.3–2.0.

## 2. `ngram_gpu`

GPU-vectorised n-gram via `unfold + argmax`. PR #29184 (v0.18.0), async-scheduler
compatible. Same result as `ngram` but on-device, so integrates with CUDA graphs
and doesn't bottleneck on single-threaded CPU.

- Proposer: `NgramProposerGPU`, `v1/spec_decode/ngram_proposer_gpu.py:215-380`
- Kernel: `NgramGPUKernel` at lines 26-212, `torch.compile`-compatible
- Config fields: same as `ngram`
- Prefer this over `ngram` on any recent build. Only drop to CPU `ngram` if
  debugging a GPU-memory ceiling — the GPU version allocates scratch.

## 3. `medusa`

Multiple independent heads on top of the target model's hidden states, each
predicting a token at position k.

- Proposer: `MedusaProposer`, `v1/spec_decode/medusa.py:18-79`
- Config: `model` = Medusa checkpoint (auto-detected when
  `hf_config.model_type == "medusa"`, `config/speculative.py:523`).
  `num_speculative_tokens` inferred from head count.
- **TP=1 forced on the drafter** (`config/speculative.py:731-738`). Operator
  with TP=8 target sees their Medusa drafter silently pinned to TP=1. Not in
  any doc.
- No active development in 2025-2026. Superseded by EAGLE-3. Keep only if
  locked into an existing Medusa checkpoint.
- Expected AL: 1.6–1.75. Draft-compute overhead low (small heads).

## 4. `mlp_speculator`

IBM-family MLP drafter (the "accelerator" models on HF like
`ibm-ai-platform/llama3-8b-accelerator`). Takes previous embeddings, projects
through MLP layers, outputs k tokens.

- Model: `model_executor/models/mlp_speculator.py:60-110`
- Config auto-detection: `config/speculative.py:525-526`
  (`hf_config.model_type == "mlp_speculator"`)
- `num_speculative_tokens` defaults to `config.num_lookahead_tokens`; if set
  manually, must be a multiple of `n_predict` (`config/speculative.py:591-600`)
- **TP=1 forced** (same as Medusa)
- Known broken for `llama3-70b-accelerator`: `AttributeError: 'MLPSpeculatorConfig'
  object has no attribute 'num_attention_heads'` (issues #34106, #34163)
- Snowflake benchmarks this at 13.7% accept vs 44.5% for their LSTM-Speculator.
  Historical, not a 2026 choice.

## 5. `draft_model`

Runs a full tiny LM as the drafter. Most flexible — any HF checkpoint — most
expensive.

- Proposer: `DraftModelProposer`, `v1/spec_decode/draft_model.py:17-89`
- Config: `model` (drafter HF path), `num_speculative_tokens`,
  `draft_tensor_parallel_size`, `parallel_drafting` (v0.16+ PARD-style
  parallel forward)
- **TP constraint is hard**: `draft_tensor_parallel_size` MUST equal the
  target's TP, or engine raises ValueError (`config/speculative.py:46-51`).
  Reason: torch.compile cache corruption on same-machine multi-rank compile.
- Multimodal not supported on the drafter (`config/speculative.py:305`). M-RoPE
  not supported (line 312). Padded drafter batch disabled (line 297).
- Embeddings NOT shared with target (different from EAGLE). Drafter loads its
  own weights — VRAM cost for both.
- `quantization` field can be set separately from target (new in v0.11.1 via
  #28435 for EAGLE; draft_model got parallel support via #24322 in v0.15.0).
- Expected AL for a well-aligned tiny model: 2.5–3.5. Alignment means same
  tokenizer, same training distribution, ideally a distilled pair.

## 6. `eagle` / `eagle3`

EAGLE heads run on target's hidden states; EAGLE-3 additionally consumes
auxiliary hidden states from designated intermediate layers.

- Proposer: `EagleProposer`, `v1/spec_decode/eagle.py:1735-1748`
  (inherits `SpecDecodeBaseProposer` at lines 60-1732)
- Method-enum detection: `"eagle"` / `"eagle3"` substring in the model field
  name (`config/speculative.py:517-519`)
- Shares embeddings with target (lines 1376-1405) — drafter VRAM much smaller
  than `draft_model`
- `parallel_drafting: true` enables P-EAGLE variant (v0.16+, PR #32887); see
  `eagle3.md`
- **EAGLE-3 target-model allow-list** (config/speculative.py:895-909 as of
  2026-04-24 — grep `aux_hidden_states_supported` on upgrade; line numbers
  drift): llama, qwen, minicpm, gpt_oss, hunyuan_vl, hunyuan_v1_dense, afmoe,
  nemotron_h, deepseek_v2, deepseek_v3, kimi_k2, kimi_k25, minimax_m2, gemma4
- EAGLE-3 auxiliary layers picked via `eagle_aux_hidden_state_layer_ids` in
  HF config (`v1/worker/gpu/spec_decode/eagle/eagle3_utils.py:35-46`)
- Per-target EAGLE-3 head classes exist: `llama_eagle3.py` (first layer is
  `2*hidden_size` to pack embeds + hidden), `deepseek_eagle3.py`, etc.
- Tree speculation supported via `speculative_token_tree`. Red Hat reports
  tree decoding typically underperforms greedy in deployment — prefer chain.
- CUDA-graph dispatcher (lines 1681-1732) synchronises graph mode across DP
  ranks so they compile the same graphs.

## 7. `dflash`

Block-diffusion parallel drafter, Qwen3-family originated (PR #36847 v0.19+).
Cross-attends non-causally over target hidden states with a mask + next-token
embedding query.

- Proposer: `DFlashProposer`, `v1/spec_decode/dflash.py:20-250+`
- Model: `model_executor/models/qwen3_dflash.py`
- Method-enum detection: `"dflash"` substring in model name
  (`config/speculative.py:521`)
- **Forces `parallel_drafting: true`** regardless of config (line 576) — the
  architecture requires all k tokens in one forward
- **Requires `--attention-backend flash_attn`**. Non-causal attention is not
  supported by Triton or FlashInfer-TRTLLM paths
- Same target-model allow-list as EAGLE-3
- Multimodal untested (line 71 override raises if MM)
- See `dflash.md` for numbers and the z-lab paper

## 8. `mtp`

Unified entry point for every model family that ships MTP heads in-weights.
Deprecated aliases (`deepseek_mtp`, `glm4_moe_mtp`, `qwen3_next_mtp`, etc.) all
route here via PR #25232. Target model itself is the drafter.

- Proposer: `EagleProposer` with `method="mtp"` (shared code path)
- Auto-detection: `config/speculative.py:385-389` logs "method `%s` is
  deprecated and replaced with mtp" when an old alias is seen
- HF-config remapping: `config/speculative.py:235-367` rewrites
  `model_type` to the appropriate `*_mtp` variant based on the base
  architecture (see `mtp.md` for the full list)
- `num_speculative_tokens` interaction with model's `n_predict`: see `mtp.md`
  §"num_speculative_tokens rules"
- **DeepSeek-V3.2 MTP forces `enforce_eager=True`** — no CUDA graphs. Line
  397-398, FIXME'd. Recheck on every upgrade.
- Expected AL per DeepSeek-V3 tech report §4.5.2: 60–85% on the second token
  (AL ≈ 1.6–1.85).

## 9. `suffix`

Arctic Inference's Suffix Decoding, upstreamed in PR #25784 (v0.12). Uses
suffix trees over the current prompt + a global LRU-cached set of past
completions. No drafter model.

- Proposer: `SuffixDecodingProposer`, `v1/spec_decode/suffix_decoding.py:9-85`
- Requires `pip install arctic-inference` — engine throws at startup if
  missing (`config/speculative.py:644-649`)
- Config fields (all prefixed `suffix_decoding_`):
  - `max_tree_depth: int = 24`
  - `max_cached_requests: int = 10000` (0 disables global cache, prompt-only)
  - `max_spec_factor: float = 1.0` — cap is `factor × prefix_match_length`
  - `min_token_prob: float = 0.1` — suffix-tree probability floor
- **`num_speculative_tokens` is dynamic per request** — the proposer returns
  variable-length draft lists. Headline `num_speculative_tokens` acts as a
  ceiling.
- Requests ≥ `max_model_len` are skipped (line 56-59)
- Killer workloads: code editing, agent reasoning loops, RL rollouts,
  benchmark harnesses. 1.8–4.5× on SWE-Bench end-to-end.
- Do not enable for open chat — low repetition means AL ≈ 1, wasted tree
  maintenance

## 10. `extract_hidden_states`

Runtime pass-through that extracts target hidden states at specified layers
without verification. Used to accumulate training data for EAGLE-3 while serving.

- Proposer: `ExtractHiddenStatesProposer`,
  `v1/spec_decode/extract_hidden_states.py:26-280`
- **Forces `num_speculative_tokens = 1`** (line 30) — the "drafting" is
  degenerate; this method's job is to emit states, not tokens
- Requires `eagle_aux_hidden_state_layer_ids` in hf_config (lines 53-58)
- Incompatible with `disable_padded_drafter_batch` (lines 31-35)
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
- `draft_tensor_parallel_size: int | None` — must equal target TP for
  `draft_model` (hard error); TP=1 forced for `medusa`, `mlp_speculator`
- `parallel_drafting: bool = False` — v0.16+; forced True for `dflash`
- `disable_padded_drafter_batch: bool = False`

**Draft-model tuning:**
- `quantization: QuantizationMethods | str | None` — separate from target
- `moe_backend: MoEBackend | None` — per-draft MoE kernel override (v0.19+,
  PR #37880)
- `max_model_len: int | None` — cap drafter context
- `revision` / `code_revision` — HF hub revision pin
- `draft_load_config: LoadConfig | None` — separate from target

**N-gram tuning:**
- `prompt_lookup_min: int | None` (default 5)
- `prompt_lookup_max: int | None` (default 5) — TODO in source

**Alternative drafting:**
- `speculative_token_tree: str | None` — tree literal; chain if None
- `use_local_argmax_reduction: bool = False` — vocab-parallel argmax

**Suffix-specific:**
- `suffix_decoding_max_tree_depth: int = 24`
- `suffix_decoding_max_cached_requests: int = 10000`
- `suffix_decoding_max_spec_factor: float = 1.0`
- `suffix_decoding_min_token_prob: float = 0.1`

**Rejection sampling:**
- `rejection_sample_method: "strict" | "probabilistic" | "synthetic"`
  (default `"strict"`)
- `synthetic_acceptance_rate: float | None` — for the synthetic sampler,
  a testing tool not a prod knob (v0.19+, PR #38045)

**Runtime:**
- `enforce_eager: bool | None` — overrides target's setting

**Deprecated:**
- `tensor_parallel_size` — triggers validation error; use
  `draft_tensor_parallel_size`

Operator rule: always hand-author `--speculative-config` as a single JSON
object. Splitting into `--speculative-model` + `--num-speculative-tokens`
legacy flags is deprecated per the EAGLE subpage.
