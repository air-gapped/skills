# Version gates — minimum vLLM release per spec-dec fix or feature

Load when pinning or upgrading a vLLM image for a spec-dec deployment, when a
feature or flag below is missing on the running build, or when benchmark numbers
look wrong on an older build. Many rows affect *correctness*, not just perf: on a
build older than a row that applies, upgrade before benchmarking or debugging.

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
| Spec-dec respects reasoning/**thinking budgets** (PR #34668) | **v0.21.0** | Correct spec-dec on reasoning models — before this, budgets were not honoured |
| Independent **drafter attention-backend** selection (PR #39930) | **v0.21.0** | Draft and target no longer forced onto one backend |
| **`custom_class`** method — callable proposer backend (PR #39487) | **v0.22.0** | New base method; bring your own proposer |
| **peagle** speculators (#41826) and **post-norm EAGLE-3** speculators (#42764) | **v0.22.0** | Wider checkpoint compatibility |
| **Dynamic SD** (PR #32374) | **v0.24.0** | Adapts speculation depth at runtime; made full-CUDA-graph compatible in v0.25.0 (#45953) |
| ⚠ **DoS fix: invalid recovered-token reinjection in spec-dec** (PR #44744) | **v0.24.0** | **Remote denial of service.** Listed under Security in the v0.24.0 notes. Anyone running spec-dec on an internet-reachable endpoint should be ≥ v0.24.0 |
| **TLI — universal spec-dec for heterogeneous vocabularies** (PR #38174) | **v0.25.0** | Target and drafter may have different but *overlapping* vocabularies. **Opt-in:** `"use_heterogeneous_vocab": true`, `method: "draft_model"` only, `draft_sample_method: "greedy"` only |
| **`kv_cache_dtype` inside `--speculative-config`** (PR #48787) | **v0.26.0** | Drafter KV dtype set independently of the target's `--kv-cache-dtype`. Unset = inherit. Lets a small drafter keep BF16 KV while the target runs FP8 |
| **Multi-layer MTP speculator on Model Runner V2** (PR #48892) | **v0.27.0** | MTP heads with more than one layer now run under MRV2 |
| **Quantized DSpark Markov heads** (PR #50424) | **v0.27.1** | `DSparkMarkovHead.markov_w2` accepts `quant_config`; W4A16 (incl. `weight_scale_2`) now loads through normal quantization dispatch. Before this, the Markov head stayed unquantized whatever the checkpoint declared |
| Native-MTP target list gains **Kimi K3** (`kimi_k3_mtp`) and **Inkling** (`inkling_mtp`) | **v0.26–v0.27** | `MTPModelTypes` 20 → 22 entries |
| **`dspark`** drafter (#46995, #47093) | **v0.25.0** | New base method + speculators checkpoint support |
| **Block verification** for rejection sampling (#46781) | **v0.25.0** | `RejectionSampleMethod` gains `"block"` alongside `standard` / `synthetic` |
| DFlash: **CPU support** (#44029), backend selection (#46770), FlashInfer (#43081), per-layer RMSNorm fusion (#46761) | **v0.24–v0.25** | DFlash matured well past its v0.19 debut |
| EAGLE-3 for Qwen3 (#43132); reduced TP comms for large-vocab drafts (#39419) | **v0.24.0** | |
| **EAGLE3 + pipeline parallelism** on MRV2 (#50514); MTP under PP for sparse-MLA targets (#46994) | **v0.30.0** | Before this, `eagle3` + `pipeline_parallel_size > 1` was a hard-rejected combination (`vllm/config/vllm.py`). The draft's own parallel config is now always `pipeline_parallel_size=1` regardless of the target's PP degree — the drafter itself is never split across pipeline stages |
| Draft's own `moe_backend` (#54788) and `attention_backend` (#54826) **actually honored on MRV2** | **v0.30.0** | The v0.19.0/v0.21.0 rows above only ever took effect on the legacy V1 speculator (`vllm/v1/spec_decode/`); Model Runner V2 (`vllm/v1/worker/gpu/spec_decode/eagle/utils.py`) silently forced the draft to inherit the target's backend until this fix |
| **Adaptive verification** opened to every draft-model speculator via an online acceptance estimator (#52228) | **v0.30.0** | `enable_adaptive_verification: true` in `--speculative-config` previously required a DSpark checkpoint with a trained confidence head; now any MRV2 draft-model-based method (eagle3, dflash, dspark without a head; `draft_model` only from v0.31.0, when it moved to MRV2) gets per-position acceptance predicted online from the draft logits. Hard `ValueError` with `use_local_argmax_reduction: true`, LoRA, `pipeline_parallel_size > 1`, or a cudagraph mode without full graphs |
| Dual-key Gumbel-max watermarking compatible with spec-dec (#56122) | **v0.30.0** | `--watermark-config '{"algorithm":"dual_key_gumbel",...}'` works with probabilistic-sampling, standard-rejection `eagle`/`eagle3`/`mtp`/`dspark`. Other algorithms need `"allow_target_only_watermarking": true` (dilutes the signal) |
| **`draft_model` on Model Runner V2** (#43091) | **v0.31.0** | Default runner for `draft_model` now; at v0.32.0 the MRV2 standalone drafter still captures no CUDA graphs. ⚠ On v0.31.x, `use_heterogeneous_vocab: true` (TLI) also lands on MRV2, which has no vocab mapping → device-side assert at startup. Fix: v0.32.0 (#59541) falls back to V1; on v0.31.x set `VLLM_USE_V2_MODEL_RUNNER=0` |
| Dense drafter (EAGLE/EAGLE3/`draft_model`) with an EP-enabled MoE target (#56930) | **v0.31.0** | On v0.30.x startup fails with *"Number of experts in the model must be greater than 0 when expert parallelism is enabled"*; the dense draft no longer inherits target EP |
| **LiLiCorr** drafter (#57934) | **v0.31.0** | Not a new method: a `LiLiCorrDraftModel` checkpoint under `method: "dflash"`, MRV2 only. See `references/dflash.md` |
| **`ngram` / `ngram_gpu` on Model Runner V2** (#40704) | **v0.32.0** | GPU n-gram speculator with variable-length drafts; before this, n-gram forced the V1 runner |

## Composability history

| Combination | Min version | PRs |
|---|---|---|
| Chunked prefill + spec-dec | v0.11.1 | #26263 |
| LoRA: EAGLE + LoRA CUDA graph specialisation; Nemotron-H MTP LoRA | v0.11.1; v0.16.0 | #28318; #32265 |
| Sparse MLA + MTP full CUDA graphs; FP8 MLA KV fix | v0.17.0; — | #34457; #37054 |
| Disaggregated serving KV-transfer fix; KV connector + MTP deadlock under KV pressure | v0.18.0; v0.31.0 | #35158; #57104 |
| Multimodal: EAGLE/EAGLE3 on Qwen2.5-VL; text-only drafter auto-disable; MM embeddings for spec decode | v0.11.1; —; v0.19.0 | #22872; #25667; #36097 |
