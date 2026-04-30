---
name: vllm-speculative-decoding
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Pick, configure, tune, monitor vLLM speculative decoding in production. Eleven SpeculativeMethod options (ngram, ngram_gpu, medusa, mlp_speculator, draft_model, suffix, eagle, eagle3, dflash, mtp, extract_hidden_states), `--speculative-config` JSON schema, which methods pair with which target model family, Prometheus acceptance metric surface, version gates (v0.11.1 EAGLE-3 preamble fix, v0.16 parallel drafting, v0.18 ngram_gpu, v0.19 dflash and zero-bubble), composability with chunked prefill / PP / LoRA / FP8 / structured outputs, Arctic Inference plugin, where spec-dec stops paying at high batch.
when_to_use: |-
  Trigger on speculative decoding, draft model, EAGLE/EAGLE-2/EAGLE-3, MTP/multi-token prediction, deepseek_mtp, glm4_moe_mtp, qwen3_next_mtp, Medusa, MLPSpeculator, DFlash, suffix decoding, ngram speculation, ngram_gpu, acceptance rate / AL, --speculative-config, -sc, --num-speculative-tokens, prompt_lookup_min/max, draft_tensor_parallel_size, parallel_drafting, vllm:spec_decode_num_drafts, vllm:spec_decode_num_accepted_tokens, Arctic Inference, SuffixDecodingCache, SpeculativeMethod, P-EAGLE, PARD, dynamic-K, rejection_sample_method. Low-acceptance troubleshooting, BS>=32 regressions, method-selection decisions, air-gapped draft-checkpoint sourcing, integration with chunked prefill/disagg serving/PP/LoRA/FP8 KV/structured outputs. Also implicit — "speed up decode", "faster inference", "higher tok/s", "draft model for X", "audit spec dec", "deploy-memo speculative", "can we get more tokens/sec".
---

# vLLM speculative decoding — operator skill

For production vLLM operators deciding which speculative method fits a given
model + workload, configuring it correctly, wiring the acceptance metrics into
their dashboards, and diagnosing why a deployment isn't seeing the expected
speedup.

## When spec-dec wins, when it loses

Spec-dec amortises memory-bandwidth-bound decode by letting a cheap proposer
guess k tokens that a single target-model forward can verify in parallel.

- **Wins at low concurrency (BS 1–8)**: decode is bandwidth-bound, k verified
  tokens per target step → 1.5–3× throughput on a well-matched target+drafter.
  EAGLE-3 on Llama-3.1-8B: +32% TPOT over EAGLE-1 at BS=4 (vLLM v0.11.1+, PR
  #25916). DFlash on Qwen3-8B: 3.5× at BS=1, 1.6× at BS=32 (PR #36847).
- **Hurts at high concurrency (BS ≥ 32)**: target becomes compute-bound, draft
  latency is no longer hidden, rejections waste GPU time. Red Hat, Snowflake
  and the P-EAGLE author all report this. Gate spec-dec to the low-concurrency
  tier of a disagg or multi-tenant deployment, or disable above a threshold.
- **Domain mismatch sinks acceptance**: stock EAGLE-3 checkpoints are chat-tuned.
  Code / agentic / RL-rollout workloads see AL drop from ~3 to ~2. Measure on
  actual traffic before trusting vendor numbers.

## Method selection

Pick once by target-model family and workload shape. Full per-method detail in
`references/methods.md`; MTP in `references/mtp.md`; EAGLE-3 specifics including
P-EAGLE in `references/eagle3.md`; DFlash in `references/dflash.md`; Arctic
plugin and suffix in `references/arctic-inference.md`. **If training your own
EAGLE-3 / DFlash drafter (vs. picking a published one), see
`references/training-data-recipes.md` for the five recipe families surveyed
across 466 published checkpoints.**

| Situation | Pick | Why |
|---|---|---|
| Target ships MTP heads (DeepSeek V3/R1/V3.2, GLM-4.5/4.6 MoE, Qwen3-Next, Qwen3.5, Nemotron-H, MiMo, ERNIE 4.5, EXAONE-MoE, LongCat-Flash, Pangu-Ultra-MoE, Step-3.5) | `mtp` | Heads trained during pretraining, no second checkpoint, best AL |
| Qwen3 / Llama / DeepSeek / gpt-oss / Kimi K2 / Minimax M2 / Gemma 4 / Nemotron-H target on B200 class | `dflash` | Block-diffusion parallel drafter, 2.5–4.6× at BS=1, v0.19+ |
| Same list above, want mature / pre-trained head | `eagle3` | Current SOTA model-based method for listed families (v0.11.1+) |
| Agentic / code-editing / RL-rollout workload with repetition | `suffix` | Model-free suffix trees, 1.8–4.5× on SWE-Bench. Requires `pip install arctic-inference` |
| No pre-trained head, have a good tiny model (≤2B) in same family | `draft_model` | Runs full LM as drafter; TP must match target |
| Quick win, no drafter of any kind | `ngram_gpu` (v0.18+) or `ngram` | Prefix-matching only; fine for repetitive prompts, skip for open chat |
| Locked into vendor checkpoint | `medusa` / `mlp_speculator` | Legacy; still works, do not adopt for new deployments |

**EAGLE-3/DFlash aux-hidden-state list (from `vllm/config/speculative.py:895-909`
as of 2026-04-24; search `aux_hidden_states_supported` on future upgrades —
line numbers drift)**: llama, qwen, minicpm, gpt_oss, hunyuan_vl,
hunyuan_v1_dense, afmoe, nemotron_h, deepseek_v2, deepseek_v3, kimi_k2,
kimi_k25, minimax_m2, gemma4.

## Canonical `--speculative-config` shapes

Single source of truth: **`--speculative-config` JSON** (or `-sc` alias, v0.19+).
Legacy `--speculative-model` / `--num-speculative-tokens` CLI is deprecated.

```bash
# EAGLE-3 (the default "give me more tokens" choice in 2026)
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --speculative-config '{"method":"eagle3","model":"yuhuili/EAGLE3-LLaMA3.1-Instruct-8B","num_speculative_tokens":3}'

# MTP (target model has native heads — model field not set)
vllm serve deepseek-ai/DeepSeek-V3 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}'

# DFlash (Qwen3 on B200)
vllm serve Qwen/Qwen3-8B \
  --attention-backend flash_attn \
  --speculative-config '{"method":"dflash","model":"<dflash-checkpoint>","num_speculative_tokens":15,"parallel_drafting":true}'

# Suffix decoding (agentic / code workloads)
# Requires: pip install arctic-inference
vllm serve <target> \
  --speculative-config '{"method":"suffix","num_speculative_tokens":32}'

# N-gram GPU (v0.18+, model-free, repetitive prompts)
vllm serve <target> \
  --speculative-config '{"method":"ngram_gpu","num_speculative_tokens":5,"prompt_lookup_min":2,"prompt_lookup_max":5}'

# Draft model (own tiny same-family LM, TP must match target)
vllm serve <target> \
  --speculative-config '{"method":"draft_model","model":"<tiny-model>","num_speculative_tokens":4,"parallel_drafting":true}'
```

`num_speculative_tokens` tuning guidance in `references/methods.md`. `n_predict`
interaction for MTP (multiples-of-N rule) in `references/mtp.md`.

## Acceptance-rate metric surface

vLLM V1 emits four spec-dec metrics on `/metrics`
(`vllm/v1/spec_decode/metrics.py:154-198`). Every production spec-dec deployment
should scrape and dashboard all four:

| Metric | Type | Purpose |
|---|---|---|
| `vllm:spec_decode_num_drafts` | Counter | Spec-dec invocations |
| `vllm:spec_decode_num_draft_tokens` | Counter | Tokens proposed by drafter |
| `vllm:spec_decode_num_accepted_tokens` | Counter | Tokens accepted after verification |
| `vllm:spec_decode_num_accepted_tokens_per_pos` | Counter (label: position) | Per-position acceptance (position 0 to num_speculative_tokens-1) |

Counters export with `_total` suffix (prometheus_client convention).

**PromQL recipes (from source comments in `metrics.py:122-139`):**

```promql
# Acceptance rate
rate(vllm:spec_decode_num_accepted_tokens_total[5m]) /
rate(vllm:spec_decode_num_draft_tokens_total[5m])

# Mean acceptance length (+1 for the bonus target token)
1 + (
  rate(vllm:spec_decode_num_accepted_tokens_total[5m]) /
  rate(vllm:spec_decode_num_drafts_total[5m])
)

# Per-position acceptance — watch the tail falloff
rate(vllm:spec_decode_num_accepted_tokens_per_pos_total[5m]) /
rate(vllm:spec_decode_num_drafts_total[5m])
```

**Expected steady-state acceptance** (rough bands — measure actuals):
- EAGLE-3 / MTP: 0.75–0.92
- DFlash: 0.80–0.90
- Draft model (well-matched): 0.70–0.85
- ngram / ngram_gpu: 0.30–0.60 (higher on repetitive prompts)
- Medusa: 0.60–0.75
- **Alert if below 0.50** — drafter divergence, tokenizer mismatch, or temperature drift.

Alertmanager templates, Grafana-panel layout, and cross-metric diagnostics
(AL-falling-while-KV-growing, acceptance-stable-but-throughput-flat, etc.) in
`references/metrics.md`.

Smoke-check a live endpoint with `${CLAUDE_SKILL_DIR}/scripts/check-spec-decode.sh <base-url>`.

## Critical version gates

Spec-dec shipped many fixes in 2025-2026 that affect *correctness*, not just
perf. If operating off a build older than these, upgrade before benchmarking.

| Fix / feature | Min version | Impact |
|---|---|---|
| EAGLE-3 MTBench +32% (preamble dedup fix, PR #25916) | **v0.11.1** | Older builds show only +5% — benchmark numbers are wrong |
| Unsupported sampling params now **hard-fail** (PR #31982) | **v0.14.0** | Prior versions silently ignored them |
| Async scheduling default ON with spec-dec (PR #27614, #31998) | **v0.14.0** | Big throughput win; assume on |
| Spec-dec + structured outputs (PR #33374) | **v0.16.0** | Prior versions: mutually exclusive |
| Unified parallel drafting (PR #32887) — enables P-EAGLE | **v0.16.0** | Required for `parallel_drafting: true` on EAGLE/draft_model/dflash |
| Pipeline parallel + spec-dec on MRV2 (PR #33960) | **v0.17.0** | Docs still say PP-incompatible as of the public page |
| Spec-dec + disaggregated serving (PR #34529) | **v0.17.0** | Required for NixlConnector + EAGLE-3 |
| ngram on GPU + async-scheduler compatible (PR #29184) | **v0.18.0** | `ngram_gpu` method enum |
| Zero-bubble async scheduling + spec-dec (PR #32951) | **v0.19.0** | ~small % throughput recovery |
| `dflash` method + Qwen3.5 / Kimi K2.5 / Mistral Large 3 EAGLE3 | **v0.19.0** | New method, new targets |
| `--speculative-config` / `-sc` alias (PR #38380) | **v0.19.0** | Short form; flag names stabilised |
| Per-draft-model MoE backend (PR #37880) | **v0.19.0** | `moe_backend` field inside `--speculative-config` |
| Configurable acceptance rate for synthetic rejection (PR #38045) | **v0.19.0** | Testing only; not for prod |

## Critical pitfalls

The "wins/loses" section above covers BS regime and domain mismatch. The
method-selection matrix covers TP constraints and the Arctic plugin
requirement. The items below are the silent-behaviour and version-specific
traps not captured by those.

1. **Draft-model TP must equal target TP** — hard error at
   `vllm/config/speculative.py:46-51`, root cause is torch.compile cache
   corruption. Medusa and `mlp_speculator` instead silently force TP=1
   (validation at line 731), so a TP=8 target with a Medusa drafter runs the
   drafter serially. Undocumented.
2. **MTP `num_speculative_tokens` > model's native `n_predict`** must be a
   *multiple* of `n_predict`; vLLM re-runs the MTP layer. Logged warning at
   speculative.py:531-536 ("may result in lower acceptance rate"). DeepSeek-V3
   ships `n_predict=1` so asking for 5 runs the layer 5× sequentially.
3. **DeepSeek-V3.2 MTP forces `enforce_eager=True`** (speculative.py:397-398).
   No CUDA graphs → ~10-20% throughput hit. Marked FIXME; recheck on upgrade.
4. **DFlash requires `--attention-backend flash_attn`** — Triton and
   FlashInfer-TRTLLM don't support the non-causal cross-attention path.
5. **MTP model-specific method names are deprecated.** `deepseek_mtp`,
   `glm4_moe_mtp`, `qwen3_next_mtp`, etc. all unified under `method: "mtp"`
   (PR #25232). Old names still work but log deprecation.
6. **Logprob stability is not guaranteed** with spec-dec. If downstream eval
   requires reproducible logprobs, disable spec-dec. Lossless *token*
   guarantee holds "up to hardware numerics."
7. **Tokenizer mismatch between draft and target destroys acceptance.** The
   `draft_model` validator does a vocab-size check, but not token-id
   alignment. Verify with a shared-tokenizer family.
8. **Quantization mismatch**: drafter in FP16 + target in FP8 is fine;
   drafter in INT4 + target in FP8 causes AL collapse. Align where possible,
   or measure before adopting.

## Composability (current, verified)

`chunked_prefill + spec-dec` → supported since v0.11.1 (PR #26263 fix). No mutual
exclusivity in code.
`async_scheduling + spec-dec` → default since v0.14.0. Zero-bubble variant in
v0.19.0 (#32951).
`LoRA + spec-dec` → EAGLE + LoRA CUDA graph specialisation in v0.11.1 (#28318).
Nemotron-H MTP LoRA in v0.16.0 (#32265).
`Pipeline parallel + spec-dec` → MRV2 only, v0.17.0+ (#33960). **Not V1 on
current engine runner**; if pinning PP on non-MRV2, spec-dec is off.
`FP8 KV + spec-dec` → supported. Sparse MLA + MTP full CUDA graphs v0.17.0
(#34457). FP8 MLA KV specific fix #37054.
`Structured outputs + spec-dec` → v0.16.0+ (#33374). Prior: incompatible.
`Disaggregated serving + spec-dec` → v0.17.0+ (#34529). KV-transfer fix #35158
in v0.18.0.
`Multimodal + spec-dec` → v0.11.1 EAGLE/EAGLE3 on Qwen2.5-VL (#22872); text-only
drafters auto-disabled for MM when mismatch (#25667); v0.19 multimodal
embeddings for spec decode (#36097). Broad but spotty; check target family.

## Air-gapped operation

Spec-dec checkpoints (EAGLE-3 heads, MLP speculators, LSTM speculators, DFlash
adapters) live on Hugging Face. Treat them like any other HF model per the
`vllm-configuration` skill's air-gap patterns (`HF_ENDPOINT` mirror,
`HF_HUB_OFFLINE=1`, or `VLLM_USE_MODELSCOPE=True`). Specific gotchas:

- EAGLE-3 auto-detection fires on `"eagle3"` substring in `model` field —
  renaming a locally-cached dir can break detection; keep the upstream name.
- Arctic Inference speculator checkpoints (Llama-3.1-8B/70B, Llama-3.3-70B,
  Qwen2.5-32B) also live on HF — mirror before cutover.
- MTP heads ship *inside* the target model checkpoint — no separate artefact.
  Air-gap story is the same as the base model.

## When spec-dec is the wrong lever

- Workload is embedding / classification / reward-model scoring — no autoregressive
  decode, spec-dec does nothing.
- Single-token generation (tool-call decision, yes/no classification) — overhead
  without benefit.
- Prefill-dominated traffic (TTFT SLO, long prompts, short outputs) — spec-dec
  helps decode only. Chunked prefill and prefix cache matter more.
- Already-fast model (small <1B, or quantised to where decode is compute-bound)
  — headroom for spec-dec is minimal.

See `references/troubleshooting.md` for diagnostic flow on low acceptance,
silent regressions after upgrade, and metric-interpretation pitfalls.

## External references

Last verified: 2026-04-24. All vLLM PR / HF-checkpoint / Arctic-Inference URLs
probed via `gh` + HF API. Provenance table, classifications, and
re-verification recipe in `references/sources.md`.

- Main docs: <https://docs.vllm.ai/en/latest/features/speculative_decoding/>
- Per-method docs: `/features/speculative_decoding/{eagle,mtp,draft_model,mlp,n_gram,suffix}/`
- P-EAGLE blog (2026-03-13): <https://vllm.ai/blog/p-eagle>
- Speculators v0.3 (2025-12-13): <https://vllm.ai/blog/speculators-v030>
- Red Hat EAGLE-3 (Jul 2025): <https://developers.redhat.com/articles/2025/07/01/fly-eagle3-fly-faster-inference-vllm-speculative-decoding>
- Snowflake Arctic Inference: <https://www.snowflake.com/en/engineering-blog/fast-speculative-decoding-vllm-arctic/>
- SuffixDecoding (NeurIPS 2025): <https://arxiv.org/abs/2411.04975>
- EAGLE-3 paper: <https://arxiv.org/abs/2503.01840>
- DeepSeek V3 (MTP §2.2): <https://arxiv.org/abs/2412.19437>
- Spec-Bench: <https://github.com/hemingkx/Spec-Bench>
- SPEED-Bench (NVIDIA): <https://huggingface.co/blog/nvidia/speed-bench>
