# Scheduler knobs + CUDA graphs + torch.compile

Load when: tuning TTFT vs TPOT tradeoffs, diagnosing "scheduler stalls", debugging CUDA-graph capture misses, setting up a torch.compile cache for K8s.

## Scheduler knobs

Chunked prefill is on by default wherever the model supports it. `--num-scheduler-steps` no longer exists — V1 has no multi-step scheduling; `--async-scheduling` is the overlap mechanism. See [V1 Guide](https://docs.vllm.ai/en/latest/usage/v1_guide/).

### Primary knobs

| Flag | Default | Purpose / tuning rule |
|---|---|---|
| `--max-num-batched-tokens` | **device-gated, see below** | Tokens per engine step. Lower (1024) → better ITL for decode-heavy. Higher (4096-16384) → better TTFT for prefill-heavy / long-context |
| `--max-num-seqs` | **device-gated, see below** | Concurrent sequences. Higher → more concurrency but deeper queue; cap by KV-cache size |
| `--long-prefill-token-threshold` | 0 (= no cap) | Requests with prompt > threshold are treated as "long" by the chunked-prefill scheduler |
| `--async-scheduling` | auto (default-on recent) | Overlap CPU scheduling with GPU compute. Resolves [v0.10.0 regression](https://discuss.vllm.ai/t/performance-degradation-report-0-9-0-1-vs-0-10-0/1368) |
| `--stream-interval N` | 1 | Token batching for SSE streaming. N=1 smooth, N≥10 less host overhead at high concurrency ([PR #27869](https://github.com/vllm-project/vllm/pull/27869)). Also settable **per request** as a sampling param ([#49754](https://github.com/vllm-project/vllm/pull/49754)) — one interactive client no longer forces N=1 server-wide |
| `--watermark` | 0.0 | Fraction of KV blocks held free when admitting waiting/preempted requests. Raise to buy anti-thrash headroom |
| `--scheduler-reserve-full-isl` | `true` | Admit only if the **whole** input length fits in KV, not just the first chunk. The default that prevents over-admission |
| `--performance-mode` | `balanced` | `balanced` \| `interactivity` \| `throughput`. One flag for the whole latency-vs-throughput posture; `throughput` doubles the *defaulted* `max_num_batched_tokens` / `max_num_seqs` (explicit values are left alone) and picks larger graphs + throughput kernels; `interactivity` picks fine-grained graphs + latency kernels. Try this **before** hand-tuning the table below |
| `VLLM_ENGINE_ITERATION_TIMEOUT_S` | 60 | Per-iter timeout; over this, worker deemed stuck |

**Neither batching default is a constant — both are device-gated, and this is the
single most common source of "my numbers don't match the docs".** `EngineArgs`
picks from the usage context and the device: on a GPU with ≥70 GiB that is *not*
an A100 (H100/H200/B200/GB200/MI300X), `vllm serve` defaults to
**`max_num_batched_tokens=8192`, `max_num_seqs=1024`**. Below 70 GiB, or on any
A100, **2048 / 256**. (`vllm bench throughput` and other `LLM`-class entry points
get 16384 / 1024 and 8192 / 256 respectively.) The flat "2048 / 256" figure from
PR #10544 is the *small-GPU* branch only, so a tuning plan built on it starts 4×
below where an H200 actually is.

**Removed knobs — do not reach for these.** `--max-num-partial-prefills` and
`--max-long-partial-prefills` were removed in **v0.27.0**
([PR #49244](https://github.com/vllm-project/vllm/pull/49244)); per the PR they
were V0 fields the V1 oracle already rejected, so they could only ever raise
`UnsupportedFeatureError` — nothing was lost by their deletion, and any older
recipe that sets them will now fail to start.
`--preemption-mode` and `--scheduler-delay-factor` went in
[PR #25334](https://github.com/vllm-project/vllm/pull/25334) (2025-09-21), and
`--swap-space` in [PR #36216](https://github.com/vllm-project/vllm/pull/36216)
(2026-03-07) — V1 hardcodes `num_cpu_blocks = 0`, so swap space was never
allocated even when the flag was accepted.

### async-scheduling compatibility

Incompatible-or-fragile paths:
- Structured outputs — fixed in [#26866](https://github.com/vllm-project/vllm/issues/26866)
- Spec-dec — fixed in [#24799](https://github.com/vllm-project/vllm/issues/24799), [#29821](https://github.com/vllm-project/vllm/issues/29821)
- Pipeline parallelism — umbrella tracker [#27679](https://github.com/vllm-project/vllm/issues/27679) closed 2025-12-29, sub-PRs merged; verify on the running version
- Some multimodal paths — [#31679](https://github.com/vllm-project/vllm/issues/31679) closed 2026-01-07
- vllm-ascend v0.11.0rc2 — precision regression **fixed**, [ascend #4649](https://github.com/vllm-project/vllm-ascend/issues/4649) closed 2026-03-13; upgrade rather than disabling

Disable per-deployment only when reproduced on the running version.

### Preemption tuning

**There is no swap tier to tune.** V1 always preempts by recompute — it discards
partial KVs and recomputes on resume. `--preemption-mode` and `--swap-space` are
both gone (see removed-knobs note above), and `--swap-space` never allocated
anything in V1 even while it was still accepted. Advice to "raise `--swap-space`
to absorb bursts" is a V0 reflex and does nothing.

Preemption thrashing signal: `num_preemptions_total` climbs monotonically +
`num_requests_waiting` flat. Mitigations, in order:

1. **`--watermark 0.02`–`0.05`** — hold a fraction of KV blocks free at admission.
   Headroom is what stops the admit→preempt→re-admit cycle; this is the direct
   replacement for the swap knob.
2. **Leave `--scheduler-reserve-full-isl` on** (it is the default). It admits a
   request only when the *whole* input length fits, instead of only checking the
   first chunk — the over-admission that produced most thrash reports.
3. **Lower `--max-num-seqs`** to reduce KV competition. Remember the default on a
   ≥70 GiB GPU is 1024, not 256, so there is usually far more headroom to cut
   than the old figure suggested.
4. **Add replicas.**

For deeper KV-tier sizing (CPU / NVMe / LMCache / GDS) see companion `vllm-caching` skill.

### Workload-first scheduler profiles

| Scenario | `max_num_batched_tokens` | `max_num_seqs` | Other |
|---|---|---|---|
| Throughput-heavy (batch decode) | 4096-16384 | 256-512 | async-sched on, `chunked_prefill` off if possible |
| Latency-heavy (chat) | 1024-2048 | 64-128 | async-sched on, `--stream-interval 1` |
| Long-context RAG | 8192-16384 | 32-64 | `--enable-prefix-caching`, raise `--long-prefill-token-threshold` |
| Wide-EP DeepSeek | 8192 | 256 | + `--enable-expert-parallel --enable-eplb --enable-dbo`, `FULL_AND_PIECEWISE` |
| CI / smoke test | default | default | shrink `--cudagraph-capture-sizes` to `[1]` to cut capture time |

### Red Hat 5-step triage ([2026-03-09](https://developers.redhat.com/articles/2026/03/09/5-steps-triage-vllm-performance))

1. Isolate TTFT vs ITL via Prometheus histograms.
2. Read `num_requests_waiting` + `num_requests_running`. Waiting=0 but TTFT high ⇒ **compute-bound**, not queue-bound.
3. KV cache occupancy + `num_preemptions_total` climbing ⇒ **thrashing** (raise `--watermark` or lower `--max-num-seqs`; the article's `--swap-space` advice predates its removal).
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

The flag is **`--cudagraph-capture-sizes`** (plus `--max-cudagraph-capture-size`).
`--cuda-graph-sizes` no longer exists anywhere in the tree — verified absent from
`vllm/config/compilation.py` and `vllm/engine/arg_utils.py` at both `v0.25.1` and
`v0.27.0`, and a repo-wide code search for the old symbol returns nothing. Older
recipes and blog posts still use the old spelling; they will fail to parse.

If `--cudagraph-capture-sizes` is unset, vLLM generates:
```
[1, 2, 4] + range(8, 256, 8) + range(256, max_cudagraph_capture_size+1, 16)
max_cudagraph_capture_size = min(max_num_seqs*2, 512)
```

Setting `--cudagraph-capture-sizes` explicitly pins `max_cudagraph_capture_size`
to the largest entry in the list. Rule: raising `--max-num-seqs` raises the
generated cap with it, so only override when you want to *shrink* capture time or
pin exact buckets.

### Capture gotchas

- **FULL_AND_PIECEWISE garbage output** `!!!` on certain configs — [#29539](https://github.com/vllm-project/vllm/issues/29539).
- **ROCm V1 piecewise capture size** much higher than CUDA's — [#19579](https://github.com/vllm-project/vllm/issues/19579).
- **Capture time is dominant cold-start cost.** CI: use `--cudagraph-capture-sizes 1` or `-O0` ([PR #25951](https://github.com/vllm-project/vllm/pull/25951)).
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
| `VLLM_DISABLE_COMPILE_CACHE=1` | Disable caching — forces recompile every run. **Required for Llama-4** (stale-cache bug). Note the coupling below |
| `VLLM_USE_AOT_COMPILE` | AOT compile path. **Default resolves to ON** — see below |
| `VLLM_USE_MEGA_AOT_ARTIFACT` | Single-file artifact. **Default resolves to ON** — see below |
| `VLLM_CACHE_ROOT` | Override cache root (default `~/.cache/vllm`) |

**Both AOT vars are opt-*out* on any current image, and one of them is coupled to
the cache flag.** Their defaults are computed, not constant: AOT compile is on
when torch ≥ 2.10 **and** the compile cache is enabled; the mega-artifact is on
when torch ≥ 2.12 **and** AOT compile is on. `requirements/cuda.txt` at v0.27.0
pins **`torch==2.13.0`** / **`torchvision==0.28.0`**
([PR #48155](https://github.com/vllm-project/vllm/pull/48155), which pulled Triton
to 3.7.1 transitively — no direct `triton` pin exists — and was flagged upstream
as a breaking environment change), so both gates are satisfied out of the box.

The consequence worth internalising: setting `VLLM_DISABLE_COMPILE_CACHE=1` — the
documented Llama-4 workaround one row above — **also silently turns off AOT
compile, and that turns off the mega-artifact with it.** A Llama-4 deployment
carrying that flag is not comparable on startup time to anything else, and the
gap is not the cache alone.

### K8s compile-cache strategy

1. Pre-compile once on a representative pod (same model, same flags, same torch version).
2. Mount `$VLLM_CACHE_ROOT/torch_compile_cache` as a PVC OR bake into an OCI image layer.
3. Replicate — guarantees cold starts < 1 min on large models where full compile takes 5-15 min.

Autoscaling: "generate the cache directory once and share it among instances" — the Meta/vLLM integration blog endorses this as the primary mechanism.

### Common mistakes

- **Stale compile cache after vLLM upgrade** — symptoms range from silent perf regression to crash. Fix: clear `$VLLM_CACHE_ROOT/torch_compile_cache` after version bump.
- **Attributing the first request's latency to the model.** v0.27.0 warms JIT'd kernels *before* serving: FA4 gained JIT warmup infrastructure ([#47451](https://github.com/vllm-project/vllm/pull/47451)) and the model runner now warms its own Triton kernels ahead of the first request ([#49903](https://github.com/vllm-project/vllm/pull/49903)). A first-request stall that used to be normal is now a signal — and a pre-v0.27.0 TTFT baseline that included it is not comparable.
- **CUDA graphs left enabled during debugging** — shape mismatch → crash/hang. Use `-O0` during iteration.
- **`--max-num-batched-tokens < max_model_len`** — scheduler can't fit even one sequence. Fix: raise batched-tokens OR use chunked prefill (default on V1).
