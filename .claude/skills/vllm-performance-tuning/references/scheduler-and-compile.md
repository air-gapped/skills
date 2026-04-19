# Scheduler knobs + CUDA graphs + torch.compile

Load when: tuning TTFT vs TPOT tradeoffs, diagnosing "scheduler stalls", debugging CUDA-graph capture misses, setting up a torch.compile cache for K8s.

## Scheduler knobs

**V1 always-on** (setting either forces V0 fallback): `--enable-chunked-prefill`, `--num-scheduler-steps`. See [V1 Guide](https://docs.vllm.ai/en/latest/usage/v1_guide/).

### Primary knobs

| Flag | Default | Purpose / tuning rule |
|---|---|---|
| `--max-num-batched-tokens` | **2048** (since [PR #10544](https://github.com/vllm-project/vllm/pull/10544); older docs say 512) | Tokens per engine step. Lower (1024) → better ITL for decode-heavy. Higher (4096-16384) → better TTFT for prefill-heavy / long-context |
| `--max-num-seqs` | 256 | Concurrent sequences. Higher → more concurrency but deeper queue; cap by KV-cache size |
| `--long-prefill-token-threshold` | 0 (some docs say 4% of ctx) | Requests with prompt > threshold treated as "long"; works with `--max-num-partial-prefills` so short prompts jump queue |
| `--max-num-partial-prefills` | 1 | Lets N long-prompts prefill in parallel during chunked prefill |
| `--async-scheduling` | auto (default-on recent) | Overlap CPU scheduling with GPU compute. Resolves [v0.10.0 regression](https://discuss.vllm.ai/t/performance-degradation-report-0-9-0-1-vs-0-10-0/1368) |
| `--stream-interval N` | 1 | Token batching for SSE streaming. N=1 smooth, N≥10 less host overhead at high concurrency ([PR #27869](https://github.com/vllm-project/vllm/pull/27869)) |
| `--preemption-mode` | `recompute` | `recompute` vs `swap` (KV → CPU) |
| `VLLM_ENGINE_ITERATION_TIMEOUT_S` | 60 | Per-iter timeout; over this, worker deemed stuck |

### async-scheduling compatibility

Incompatible-or-fragile paths:
- Structured outputs — fixed in [#26866](https://github.com/vllm-project/vllm/issues/26866)
- Spec-dec — fixed in [#24799](https://github.com/vllm-project/vllm/issues/24799), [#29821](https://github.com/vllm-project/vllm/issues/29821)
- Pipeline parallelism — **still broken** ([#27679](https://github.com/vllm-project/vllm/issues/27679))
- Some multimodal paths — [#31679](https://github.com/vllm-project/vllm/issues/31679)
- vllm-ascend v0.11.0rc2 — **precision regression** ([ascend #4649](https://github.com/vllm-project/vllm-ascend/issues/4649))

Disable per-deployment when any above applies.

### Preemption + swap-space tuning

`--preemption-mode` (`recompute` default | `swap`) controls how the scheduler handles overload when KV cache exhausts:

- `recompute` — discard partial KVs, recompute on resume. Cheap on memory, burns compute.
- `swap` — evict KV to CPU RAM via `--swap-space <GB>` (default 4 GB). Cheap on compute, costs CPU RAM + PCIe bandwidth.

Preemption thrashing signal: `num_preemptions_total` climbs monotonically + `num_requests_waiting` flat. Mitigations in order: (1) raise `--swap-space` to absorb bursts, (2) lower `--max-num-seqs` to reduce KV competition, (3) add replicas.

For deeper KV-tier sizing (CPU / NVMe / LMCache / GDS) see companion `vllm-caching` skill.

### Workload-first scheduler profiles

| Scenario | `max_num_batched_tokens` | `max_num_seqs` | Other |
|---|---|---|---|
| Throughput-heavy (batch decode) | 4096-16384 | 256-512 | async-sched on, `chunked_prefill` off if possible |
| Latency-heavy (chat) | 1024-2048 | 64-128 | async-sched on, `--stream-interval 1` |
| Long-context RAG | 8192-16384 | 32-64 | `--enable-prefix-caching`, raise `--long-prefill-token-threshold` |
| Wide-EP DeepSeek | 8192 | 256 | + `--enable-expert-parallel --enable-eplb --enable-dbo`, `FULL_AND_PIECEWISE` |
| CI / smoke test | default | default | shrink `--cuda-graph-sizes` to `[1]` to cut capture time |

### Red Hat 5-step triage ([2026-03-09](https://developers.redhat.com/articles/2026/03/09/5-steps-triage-vllm-performance))

1. Isolate TTFT vs ITL via Prometheus histograms.
2. Read `num_requests_waiting` + `num_requests_running`. Waiting=0 but TTFT high ⇒ **compute-bound**, not queue-bound.
3. KV cache occupancy + `num_preemptions_total` climbing ⇒ **thrashing** (raise `--swap-space` or lower `--max-num-seqs`).
4. Separate ISL (drives TTFT) from OSL (drives total). RAG's vector-DB lookup is NOT in vLLM TTFT.
5. Multi-GPU: `nvidia-smi topo -m`. PCIe ⇒ bottleneck. Rule: **"minimum TP that fits the model, then scale out with replicas."**

## CUDA graph modes

Source: [CUDA graphs design](https://docs.vllm.ai/en/stable/design/cuda_graphs/), [CompilationConfig API](https://docs.vllm.ai/en/latest/api/vllm/config/compilation/).

| Mode | When | Trade-off |
|---|---|---|
| `NONE` | Debugging, `--enforce-eager` | no capture overhead, no graph benefit |
| `PIECEWISE` | Attention kernel not CUDA-graph-safe | capture only safe subgraphs; attention stays eager via dynamo splits |
| `FULL` | Small models / short prompts with uniform batches | whole forward in one graph; reused for uniform-decode batches; high memory |
| **`FULL_AND_PIECEWISE`** (default V1) | Low-latency MoE, mixed prefill/decode | full graph for uniform decode + piecewise for mixed. Best default, longest capture, highest memory |

### Default bucket list

If `--cuda-graph-sizes` unset, vLLM generates:
```
[1, 2, 4] + range(8, 256, 8) + range(256, max_cudagraph_capture_size+1, 16)
max_cudagraph_capture_size = min(max_num_seqs*2, 512)
```

Clamped to `max_num_seqs`. Rule: raising `--max-num-seqs` requires raising `--cuda-graph-sizes` too.

### Capture gotchas

- **FULL_AND_PIECEWISE garbage output** `!!!` on certain configs — [#29539](https://github.com/vllm-project/vllm/issues/29539).
- **ROCm V1 piecewise capture size** much higher than CUDA's — [#19579](https://github.com/vllm-project/vllm/issues/19579).
- **Capture time is dominant cold-start cost.** CI: use `--cuda-graph-sizes 1` or `-O0` ([PR #25951](https://github.com/vllm-project/vllm/pull/25951)).
- **AMD MLPerf v5.1 tuning note:** `max_model_len` and `max_seq_len_to_capture` were "crucial for Hip graph capture to minimize GPU idle time" ([AMD MLPerf v5.1 blog](https://rocm.blogs.amd.com/artificial-intelligence/mlperf-inference-v5.1/README.html)).

## torch.compile in vLLM

Source: [torch.compile blog](https://vllm.ai/blog/torch-compile), [Red Hat deep-dive](https://developers.redhat.com/articles/2025/09/03/vllm-torchcompile-efficient-llm-inference-pytorch), [design docs](https://docs.vllm.ai/en/latest/design/torch_compile/).

### Optimization levels (`-O<n>`)

| Level | What it does |
|---|---|
| `-O0` | No compile, no CUDA graphs. Equivalent to `--enforce-eager` |
| `-O1` | Simple compile + fast fusions + PIECEWISE graphs |
| **`-O2`** | **default** — full compile + `FULL_AND_PIECEWISE` + fusions |
| `-O3` | reserved, currently equals `-O2` |

### Fusion gains at `-O2`

| Fusion | Gain |
|---|---|
| AllReduce + RMSNorm | +15% |
| Sequence-Parallel + Async TP | +10% |
| Attention + Quant (FP8) | +7% |
| FP4 fusions | upcoming |

### Compile cache

Default dir: `$VLLM_CACHE_ROOT/torch_compile_cache` (= `~/.cache/vllm/torch_compile_cache`). Reusable across machines with **identical environment** (torch, CUDA, GPU arch, vLLM version).

| Env var | Purpose |
|---|---|
| `VLLM_DISABLE_COMPILE_CACHE=1` | Disable caching — forces recompile every run. **Required for Llama-4** (stale-cache bug) |
| `VLLM_USE_AOT_COMPILE=1` | Enable AOT compile path (requires torch ≥2.10) |
| `VLLM_USE_MEGA_AOT_ARTIFACT=1` | Single-file artifact (requires torch ≥2.12, vLLM ≥v0.19.0). Needs `VLLM_USE_STANDALONE_COMPILE=1` |
| `VLLM_CACHE_ROOT` | Override cache root (default `~/.cache/vllm`) |

### K8s compile-cache strategy

1. Pre-compile once on a representative pod (same model, same flags, same torch version).
2. Mount `$VLLM_CACHE_ROOT/torch_compile_cache` as a PVC OR bake into an OCI image layer.
3. Replicate — guarantees cold starts < 1 min on large models where full compile takes 5-15 min.

Autoscaling: "generate the cache directory once and share it among instances" — the Meta/vLLM integration blog endorses this as the primary mechanism.

### Common mistakes

- **Stale compile cache after vLLM upgrade** — symptoms range from silent perf regression to crash. Fix: clear `$VLLM_CACHE_ROOT/torch_compile_cache` after version bump.
- **`VLLM_USE_MEGA_AOT_ARTIFACT=1` on torch < 2.12** — silently ignored or crashes. Check: `python -c "import torch; print(torch.__version__)"`.
- **CUDA graphs left enabled during debugging** — shape mismatch → crash/hang. Use `-O0` during iteration.
- **`--max-num-batched-tokens < max_model_len`** — scheduler can't fit even one sequence. Fix: raise batched-tokens OR use chunked prefill (default on V1).
