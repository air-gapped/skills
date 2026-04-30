# HBM-bandwidth saturation on H100 vs H200 — vLLM source investigation

Background: when serving Gemma 4 31B AWQ (or similar dense models) on
H100, throughput plateaus around batch=64 — adding more concurrent
sequences just inflates TPOT and TTFT without moving aggregate
throughput. On H200, the operator's empirical data shows the same
plateau but at batch=128. This doc explains why.

## Direct answer

**The 64↔128 plateau difference is NOT baked into vLLM source as a
hardware switch.** It's an emergent compute/memory-bandwidth
saturation knee — a property of where GEMV/GEMM kernels stop
amortizing weight reads across the batch. Different hardware = different
HBM bandwidth = different saturation point.

## Evidence from vLLM source

The only hardware-aware default-batch logic is in
`vllm/engine/arg_utils.py:2207-2288` (`get_batch_defaults`). It
branches on `device_memory >= 70 GiB AND device_name != "a100"` —
H100 80GB **and** H200 141GB take the *same* code path:
- `default_max_num_batched_tokens[OPENAI_API_SERVER] = 8192`
- `default_max_num_seqs[OPENAI_API_SERVER] = 1024`

Other key files checked, no H100/H200 switch found:

- `vllm/config/scheduler.py:42-44` — flat constants
  `DEFAULT_MAX_NUM_BATCHED_TOKENS=2048`, `DEFAULT_MAX_NUM_SEQS=128`.
- `vllm/config/compilation.py:666-680` —
  `max_cudagraph_capture_size = min(max_num_seqs*2, 512)`; capture
  pattern `[1, 2, 4] + range(8, 256, 8) + range(256, max+1, 16)`.
  Identical for H100 and H200.
- `vllm/platforms/cuda.py` — zero hits on `max_num_seqs`, `H100`,
  `H200`, `sm_90`, or `sm_100`.
- `vllm/v1/spec_decode/{eagle,llm_base_proposer,extract_hidden_states,dflash}.py`
  — `max_batch_size` is just `scheduler_config.max_num_seqs`
  propagated; no EAGLE3-side cap.
- `vllm/config/{model,parallel,kv_cache,vllm}.py` —
  `device_capability` is read for kernel selection (e.g. mamba
  family-100 gating at `vllm.py:129-130`), never for batch sizing.

## Evidence from upstream issues

- **PR #17885** *"[Perf] Use small max_num_batched_tokens for A100"*:
  documents the `device_memory >= 70 GiB AND not a100` heuristic — the
  only hardware split in the engine. Llama-70B TP=2 +36% on A100 with
  smaller token budget. Confirms vLLM's own model: per-SKU defaults
  are tuned **manually**, not derived from device_capability.
- **#22780** *"Performance Drop with Concurrent Requests Using
  BnB-4bit"*: AWQ scales 30→56 t/s at 2 concurrent, BnB 20→9 t/s —
  confirms quant-kernel-specific scaling but no H100/H200 split.
- **#35467** *"non-optimal performance of `linear` for medium batches"*
  (B200): explicit numerical proof that on Blackwell, **a
  memory-bandwidth-bound GEMM (AI=251 < ridge=584) caps at ~49% of peak
  HBM** even with the best kernel. Same physics on H100/H200 with
  different ridge points. This is the textbook explanation for the
  knee.
- **#6801** *"[RFC]: Performance Roadmap"* — open, references batch-size
  sweeps as a tuning knob, never as a fixed cap.

## Upstream docs

`docs/benchmarking/sweeps.md` ships a default sweep with `max_num_seqs ∈
{32, 64, 64, 128, 128, 256}` and explicitly frames concurrency as a
Pareto knob. `docs/configuration/optimization.md:54-58` recommends
`max_num_batched_tokens > 8192` for "smaller models on large GPUs" —
generic, no per-SKU number. **No upstream doc states a per-hardware
concurrency knee.**

## Likely root cause — the physics

You are **HBM-bandwidth-bound on decode**. Decode time per layer ≈
`weight_bytes / HBM_bw`. Once batch is large enough that the compute
(Tensor Core flops) hides the weight read, throughput plateaus. Higher
HBM bandwidth = the knee shifts to a larger batch.

| GPU | HBM | Bandwidth | Approx batch knee (Gemma 4 31B AWQ) |
|---|---|---|---|
| H100 SXM5 80GB | HBM3 | ~3.35 TB/s | ~64 |
| H200 SXM 141GB | HBM3e | ~4.8 TB/s | ~128 |
| B200 SXM 192GB | HBM3e | ~8 TB/s | (~256 expected, see #35467) |
| Ada (RTX 4060 Ti / sm_89) | GDDR6 | ~448 GB/s | ~16-32 (much lower) |

Bandwidth ratio H200/H100 = 1.43; observed batch ratio 128/64 = 2.0.
Not exact but same direction — kernel mix and arithmetic intensity per
layer also play in.

The AWQ-INT4 weights + EAGLE3 k=3 (which accepts ~2-3× more tokens per
forward, magnifying decode pressure) + `kv-cache-fp8` (halves KV
bandwidth) all anchor you in the bandwidth-bound regime where this
scales linearly with HBM bandwidth.

## Operator action

This is a hardware-saturation reality, not a knob. Three useful
actions:

1. **Confirm bandwidth-bound** with `nsys`/`ncu` on a decode-only trace;
   expect HBM utilization >70%. If yes, no software fix moves the knee.
2. **To extract more throughput on H100 specifically**: increase TP
   (split weight bytes across HBM), drop EAGLE3 k=3 → k=2 (lowers
   per-step accept-cost), or run AWQ-Marlin instead of vanilla AWQ
   (better kernel utilization at mid-batch).
3. **Don't tune `max_num_seqs` above the knee** — it just inflates TPOT
   (data: 74 ms → 169 ms, throughput flat) and queue depth (TTFT
   2.9 s → 181.8 s).

## Source paths cited

- `vllm/engine/arg_utils.py:2207-2288` (the only hardware-aware default in vLLM)
- `vllm/config/scheduler.py:42-44` (flat batch defaults)
- `vllm/config/compilation.py:666-680` (cudagraph capture pattern)
- `vllm/v1/spec_decode/llm_base_proposer.py:116`
- `docs/configuration/optimization.md:54-58`
- `docs/benchmarking/sweeps.md`
