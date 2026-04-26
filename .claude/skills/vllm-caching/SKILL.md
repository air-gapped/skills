---
name: vllm-caching
description: |-
  vLLM tiered KV cache configuration for production H100/H200 clusters. Native CPU offload, LMCache (CPU+NVMe+GDS), NixlConnector (disaggregated prefill), MooncakeConnector (RDMA), MultiConnector composition. Version gates, sizing math (flag total across TP, not per-GPU — opposite of SGLang), KV-vs-weights offload distinction operators most often get wrong.
when_to_use: |-
  Trigger on "vllm kv cache", "kv offload", "prefix caching", "LMCache", "NixlConnector", "MooncakeConnector", "kv_offloading_size", "kv-offloading-backend", "disaggregated prefill", "tiered kv", "CPU offload kv", "long context concurrency", "TTFT too slow", "prefill bottleneck", "GDS cuFile", "gpu_memory_utilization full", "how many concurrent requests", "KV won't fit", "long prompts too slow", "extending vLLM KV beyond HBM". SGLang-to-vLLM migration on CPU KV sizing, whether to add LMCache to existing deploy. Also implicit contexts — "audit KV config", "deploy-memo cache", "serve_args kv", "cache strategy for {model}", "long-context serve recipe" — any time authoring/reviewing a KV-cache deploy recipe.
---

# vLLM tiered KV caching

Target audience: operators running vLLM on H100/H200-class datacenter GPUs in production. Assumes CUDA 12/13, Kubernetes or bare container deployment, multi-GPU tensor parallel.

## Why this matters

Long-context workloads (coding agents, RAG, research agents averaging 50k–200k tokens) are almost always **KV-cache bound**, not compute bound. The GPU sits idle waiting for free KV slots. Tiered caching — HBM → CPU DRAM → local NVMe → remote — extends effective capacity without adding GPUs and converts repeated sessions from "re-prefill every turn" to "reload in milliseconds."

The single biggest throughput lever for long-context serving, once the model fits, is a well-sized DRAM tier. It routinely delivers 50–100× speedups on cache hits vs re-prefill, and coding-agent traffic has strong prefix locality that makes hits nearly universal after the first turn.

## Version gates — check these FIRST

Operators constantly ask "is this available?" when it either isn't in their version, or has been for a while and they missed it. Always confirm the vLLM version before recommending a config.

| Feature | First release | Notes |
|---|---|---|
| Native CPU KV offload (`vllm/v1/kv_offload/`) | **v0.11.0** (2025-10-02) | Infrastructure + scheduler integration |
| CLI flags `--kv-offloading-size` / `--kv-offloading-backend` | **v0.11.1** (2025-11-18) | Before this, required editing config objects |
| LMCache bundled in official x86 `vllm/vllm-openai` image | **v0.14.0** (2026-01-20) | arm64 had it from v0.10.2; x86 was intentionally stripped July 2025–Jan 2026 due to torch version conflict — many ops teams had to pip install LMCache at container start during that window, which is now unnecessary |
| `--calculate-kv-scales` deprecated | pre-v0.19 (still present in v0.19.1) | Flag emits a deprecation warning but still accepted as of v0.19.1. FP8 KV without shipped scales falls back to scale=1.0 (see pitfalls). Verified 2026-04-24 against `vllm/config/cache.py` on main. |

Known-good tags: `v0.14.0`+, `v0.19.0`, `v0.19.0-cu130`, and model-specific tags like `glm51-cu130` all ship with `INSTALL_KV_CONNECTORS=true` baked in — LMCache, NIXL, and Mooncake pre-installed.

### Two-step bundling verification (build flag + runtime import)

Build flag = "we tried to install it." Runtime import = "the package actually loads." Different things — the torch-conflict era of mid-2025 had cases where the build flag said yes but `import lmcache` failed at runtime.

**Step 1 — build-flag check (no pull, ~1s):**

```bash
${CLAUDE_SKILL_DIR}/scripts/inspect-vllm-image.sh <tag>
```

Prints `LMCache/NIXL/Mooncake: YES (built with INSTALL_KV_CONNECTORS=true)` if the build layer ran the kv_connectors install.

**Step 2 — runtime-import check (pull if needed, ~30s after pull):**

```bash
~/.claude/skills/lmcache-mp/scripts/verify-bundling.sh <tag>
```

Starts a sleep-overridden container, exec's a Python probe that confirms `lmcache`, `nixl`, `mooncake` import cleanly; checks the LMCache MP adapter classes and the `ParallelStrategy` version-hazard symbol; lists all registered KV connectors; loads each connector class through the factory's own thunk. Run this against any tag before trusting it in production. Verified `vllm/vllm-openai:v0.19.1` 2026-04-26: vllm 0.19.1, lmcache 0.4.3, nixl 0.9.0, mooncake-transfer-engine 0.3.10.post1, all imports clean, all four KV-offload connectors load.

**lmcache version compatibility:** vLLM main imports `ParallelStrategy` from the lmcache MP adapter. That symbol does NOT exist in lmcache 0.4.3 (verified against the v0.4.3 tag); it was added in 0.4.4. v0.19.1 image ships 0.4.3 — fine for v0.19.x vLLM source which doesn't need the symbol, but if you mix vLLM main with the bundled lmcache, expect `ImportError: cannot import name 'ParallelStrategy'`. Pin the pair or `pip install -U lmcache>=0.4.4` inside the container.

For other diagnostics (LMCache logs, `gdscheck`, Prometheus metrics), see `references/diagnostics.md`.

## Decision tree — which backend

Ask these in order:

1. **Single node, CPU DRAM tier only, no disk?** → `--kv-offloading-backend native`. Zero extra deps, included since v0.11.1. Start here unless there is a concrete reason to add complexity.
2. **Single node, want NVMe as a third tier?** → LMCache in-process via `LMCacheConnectorV1` (`--kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'` + `LMCACHE_LOCAL_DISK` env vars).
3. **Multiple vLLM pods on the same node want a SHARED KV cache, OR cache CPU work should not contend with the inference GIL, OR cache memory needs to scale independently of GPU pods?** → **LMCache MP mode** (separate-pod LMCache server, vLLM connects via ZMQ using `LMCacheMPConnector`). Defer to the **`lmcache-mp` skill** for the DaemonSet+Deployment pattern, image pair, ZMQ protocol, L2 adapter cascade.
4. **Disaggregated prefill across nodes (separate prefill and decode pods)?** → NixlConnector via `--kv-transfer-config`. Tunes TTFT and ITL independently.
5. **RDMA-backed KV transfer between nodes, high-throughput datacenter fabric?** → MooncakeConnector.
6. **NIXL between prefill/decode pods AND local CPU overflow on each?** → MultiConnector, composing NixlConnector + OffloadingConnector.

Do not reach for LMCache or NIXL or Mooncake just because they exist. Native offload handles the 80% case with zero operational surface area. LMCache MP adds an extra pod and another image — only justified by the multi-pod-shared-cache or GIL-isolation cases above.

**For concrete config recipes for any of the above, see `references/connectors.md`.** Load that reference once a backend has been selected — it contains copy-paste-ready invocations with all required env vars, GDS host prerequisites (cuda-keyring, open kernel modules, Secure Boot), and the MultiConnector JSON format.

> **NIXL deep-dive** — NIXL itself (transfer library, 13 backend plugins, agent API, telemetry, ETCD/side-channel metadata, plugin authoring) lives in the dedicated **`nvidia-nixl`** skill. This skill covers vLLM-side wiring of NixlConnector / LMCache-P2P-over-NIXL only. Reach for `nvidia-nixl` when picking transports (`UCX_TLS`, GDS, Mooncake, libfabric…), tuning UCX, debugging `nixl_agent` directly, or writing custom plugins.

> **LMCache MP deep-dive** — the standalone-server multiprocess mode (`LMCacheMPConnector`, `lmcache server`, `lmcache/standalone:nightly`, DaemonSet+Deployment, L2 adapters: nixl_store / fs / mooncake_store / s3) is its own operational shape. The dedicated **`lmcache-mp`** skill covers it.

## Sizing math — READ BEFORE RECOMMENDING A NUMBER

**`--kv-offloading-size` is TOTAL across all TP ranks, in GiB.** This is the OPPOSITE of SGLang's equivalent flag (which is per-rank). Teams migrating from SGLang routinely under-allocate by a factor of TP.

If an SGLang config was 200 GB per GPU × 8 GPUs = 1600 GB, then on vLLM use `--kv-offloading-size 1600`. Not 200.

**For per-token KV formulas, worked slot-math examples, Dell XE9680 hardware reference numbers, and NVMe-vs-DRAM-vs-prefill load-time comparisons, see `references/hardware-sizing.md`.**

When using LMCache as the backend, keep `LMCACHE_MAX_LOCAL_CPU_SIZE` and `--kv-offloading-size` consistent. LMCache env vars win on the backend side; inconsistency leads to scheduler miscounting available slots and either over-subscribing or under-using the cache.

## Critical pitfalls

### OffloadingConnector requires `--disable-hybrid-kv-cache-manager`

Add this flag whenever `--kv-offloading-size` is set. Without it the engine fails at startup with:

```
ValueError: Connector OffloadingConnector does not support HMA but HMA is enabled.
Please set `--disable-hybrid-kv-cache-manager`.
```

The Hybrid Memory Allocator (HMA) is the default scheduler in vLLM v0.18+ and is mutually exclusive with `OffloadingConnector`. This is the **single most common silent blocker** for first-time KV-offload deploys — the error message names the fix but it appears on no cookbook page or release note (verified 2026-04-25 against release notes for v0.18.0 → v0.20.0). Verified live on RTX 4060 Ti 16 GB + cu130-nightly + Qwen3-4B; pod boots clean once the flag lands.

The same flag is required by `LMCacheConnectorV1`, `LMCacheMPConnector`, and the new hybrid-aware path being built — see the next section.

### Hybrid models (Qwen3.5, Gemma4, Mamba+attention) are a moving target

vLLM's Hybrid Memory Allocator (HMA) is mutually exclusive with all current KV-offload connectors. Disabling HMA fixes startup, but introduces secondary problems on hybrid-attention models:

- **0% prefix cache hit rate** on Gemma4 + speculative decoding (EAGLE/DFlash/MTP) — reported as [vLLM#40624](https://github.com/vllm-project/vllm/issues/40624) (open as of 2026-04-26, last update 2026-04-23). Caused by a per-manager EAGLE-drop spiral when the hybrid coordinator sees ≥3 attention groups (Gemma4 full + sliding + DFlash draft = 3 specs). Workaround: `--disable-hybrid-kv-cache-manager` + lower `--max-model-len` to fit non-HMA allocation.
- **LMCache MP doesn't support hybrid models at all** ([LMCache#2845](https://github.com/LMCache/LMCache/issues/2845)). Community patch exists for Qwen3.5-27B, marked NOT production-ready.
- **Native offload + hybrid is being actively built** in the `[kv_offload+HMA][N/N]` PR series. Parts 0-3, 5-7 shipped in **v0.20.0** (2026-04-23); parts 4, 8, 9, 10, 11 merged to `main` between 2026-04-22 and 2026-04-25 — **not yet in any tagged release**. Final piece (HybridOffloadPlanner + MultiConnector hybrid awareness + mamba alignment, [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261)) still open.

**Today's recommendation for hybrid-model + offload:**

1. Use stock `vllm/vllm-openai:v0.19.1+` with native `--kv-offloading-size` + `--disable-hybrid-kv-cache-manager` + reduced `--max-model-len`. Accept the prefix-cache hit rate bug on hybrid + spec-decode combos.
2. Or wait for v0.21.x with the full kv_offload+HMA series merged.
3. Pure-transformer models (Qwen3-14B, Llama-3, Mistral-7B) are unaffected by this section — the standard offload recipes work today.

When recheckchecking, the canonical probe is:

```bash
gh pr list --repo vllm-project/vllm --search "kv_offload+HMA in:title is:open"
gh issue view 40624 --repo vllm-project/vllm --json state,updatedAt
gh issue view 2845 --repo LMCache/LMCache --json state,updatedAt
```

### `--cpu-offload-gb` is NOT the same as `--kv-offloading-size`

| Flag | What it offloads | Unit | Effect |
|---|---|---|---|
| `--cpu-offload-gb` | **Model weights** | Per-GPU | Hurts prefill throughput; lets larger-than-HBM models fit |
| `--kv-offloading-size` | **KV cache** | Total across TP | Helps TTFT on cache hits; no effect on compute throughput |

Recommending `--cpu-offload-gb` when the user asked about KV tiering is a serious error. They are different subsystems with opposite throughput implications.

### FP8 KV cache without shipped scales

`--calculate-kv-scales` is deprecated (still accepted as of v0.19.1, emits a warning, scheduled for removal). Setting it has no effect — vLLM now always loads scales from the checkpoint. If `--kv-cache-dtype fp8` is set on a model whose checkpoint doesn't ship calibrated `k_scale`/`v_scale`, vLLM defaults to scale=1.0, which can clip pathological activations — especially on long code contexts where specific tokens produce large activations in specific layers.

Symptoms: subtle quality degradation, often only past 128k context. "Usually works fine" is the common operator experience because most activations fit, but the risk is real.

Recommend: stay on BF16 KV and use offload to claw back the memory. The prefill savings from offload hits dwarf whatever would be saved by moving KV from BF16 to FP8.

### NVSwitch doesn't accelerate host-to-GPU offload

Operators new to tiered caching sometimes assume NVSwitch/NVLink helps. It doesn't — those interconnects are GPU↔GPU only. KV offload traffic is **CPU DRAM → PCIe Gen5 x16 → GPU HBM**, one link per GPU. See `references/hardware-sizing.md` for the bandwidth numbers on XE9680-class hardware.

### NVMe tier is NOT a hot path

Loading a 100k-token BF16 context from NVMe takes ~5–7 seconds (Gen4 U.2, buffered) — still beats a ~10 second re-prefill, but DRAM beats NVMe by 20×. Size the DRAM tier to hold the hot working set; treat NVMe as overflow for sessions from "earlier today" that might come back.

## When the user says "it doesn't help"

Most common root causes, in order:

1. **Concurrency is already at the memory wall, not the cache.** On an 8× H200 with a 300–500 GB weight footprint serving 200k+ contexts, 1–2 live slots is physics — compute jumped ~6× over the previous generation but memory bandwidth only ~1.6×. Adding offload doesn't raise live concurrency; it raises the *warm-set* size (sessions that skip re-prefill on return). Confirm the expectation is "more warm sessions," not "more simultaneous running."
2. **Hit rate is low.** No prefix reuse in the workload → offload gains nothing. Check `prefix_cache_hits_total` / `prefix_cache_queries_total`. Non-agentic, non-RAG traffic often has low prefix locality.
3. **`--enable-prefix-caching` is missing.** Without it, vLLM doesn't try to reuse prefixes in the first place; offload has nothing to hit against.
4. **Flag sized as per-GPU (SGLang habit).** Check `vllm:cache_config_info` — the number reported is what vLLM actually allocated. If it's 1/TP of what was expected, this is the cause.
5. **Cold cache.** First N requests pay full prefill cost while filling the cache. Measure steady-state, not ramp-up.
6. **Max context set higher than needed.** If `--max-model-len` is 200k but typical requests are 8k, the scheduler reserves capacity for 200k; effective concurrency is starved. Tune `--max-model-len` to the 95th or 99th percentile of real traffic, not the theoretical maximum.
7. **Actually compute-bound.** Short prompts + many tokens out = decode-dominated. Offload can't help; more GPUs or a smaller model is the fix.

## Open bugs to know before recommending offload

Active issues at the time of last verification (2026-04-25). All checked when authoring a new offload deploy.

| Issue | Repo | State | Affects | Avoidance |
|---|---|---|---|---|
| [#36463](https://github.com/vllm-project/vllm/issues/36463) | vllm-project/vllm | open | **Qwen3.5 family** fail-to-start with `--kv-offloading-backend native` while Qwen3 (non-hybrid) works fine | Try a non-hybrid model first to isolate; if Qwen3.5/3.6 must run with offload, monitor the issue for fix |
| [#39702](https://github.com/vllm-project/vllm/issues/39702) | vllm-project/vllm | open | `SimpleCPUOffloadScheduler` AssertionError TOCTOU race once CPU LRU starts evicting (10–30 min after warm-start). Repro on 2× RTX 4090 + Gemma4-31B AWQ-4bit + TP=2 + v0.19.1rc1 | Run short benches first to prove plumbing; long-soak only after fix lands. PR proposed in issue body, not yet merged |
| [#40259](https://github.com/vllm-project/vllm/issues/40259) | vllm-project/vllm | open | KV offload + EAGLE3 + Expert Parallel cuMemcpyDtoHAsync segfault on 8× H20-3e | Don't combine offload with EP+EAGLE3 until fix lands |
| [#2942](https://github.com/LMCache/LMCache/issues/2942) | LMCache/LMCache | open | `LocalCPUBackend.allocate()` deadlocks when `use_hot=False` and staging buffer fills. Repro confirmed 2026-04-23 even with `use_hot=True` on Llama-3.2-1B + ShareGPT | Always set `LMCACHE_LOCAL_CPU=True` (default) — never `use_hot=False`. Skip `LMCACHE_LOCAL_DISK` until fix lands. PR proposed by `ianliuy`, not yet in v0.4.4 |
| [#2502](https://github.com/LMCache/LMCache/issues/2502) | LMCache/LMCache | open | LocalDiskBackend benchmark crashes vLLM | Skip the disk tier on production paths; DRAM-only is the safer default |

When auditing a new offload deploy, recheck these — `gh issue view <N>` confirms current state cheaply.

## Other long-context knobs worth tuning alongside offload

Offload is necessary but not sufficient for stable long-context serving. Two flags compound the effect:

- **`--block-size 32`** (default 16) — larger KV blocks reduce internal fragmentation at very long contexts. Meaningful win past ~128k; usually neutral or slight loss below 32k.
- **`--max-num-batched-tokens <N>`** — caps how many prefill tokens vLLM will batch in one step. Without it, a burst of long-prompt arrivals can starve decode and spike tail TTFT. Good starting value: 4096–8192 on H200-class.
- **`--load-format fastsafetensors`** — direct-mapped safetensors loader. Bundled in NVIDIA Dockerfile from v0.20.0 (#38950); also present in cu130-nightly. **`fastsafetensors` is a CLI flag, not an env var** — `VLLM_USE_FASTSAFETENSOR=1` does NOT exist. On consumer GPUs (no GDS) it auto-falls back to non-GDS mode with a `GDS is not supported in this platform` warning; loader still ~3× faster than default safetensors path (3.7 s for Qwen3-4B BF16 on RTX 4060 Ti). Pair with `HF_HUB_ENABLE_HF_TRANSFER=1` for first-pull download speed.

Do not enable `--enforce-eager` as a fragmentation workaround — it disables CUDA graphs and hurts steady-state throughput by more than fragmentation costs. Verified live: dropping `--enforce-eager` on Qwen3-4B (pure transformer, RTX 4060 Ti) cut prefix-cache-hit turn from 2.4 s → 0.64 s (-73 %). Only keep it when the architecture genuinely needs it (hybrid DeltaNet+Attention models like Qwen3.5).

## Validating that offload is actually helping

After enabling offload, the canonical workload for stressing the CPU tier is **`vllm bench serve --dataset-name prefix_repetition`** — it generates N distinct shared prefixes and cycles requests through them, forcing KV eviction once aggregate prefix footprint exceeds GPU capacity. Knobs:

```bash
vllm bench serve \
  --backend openai-chat \
  --base-url http://<endpoint> \
  --endpoint /v1/chat/completions \
  --model <served-name> \
  --tokenizer <hf-repo> \
  --dataset-name prefix_repetition \
  --prefix-repetition-prefix-len 8000 \
  --prefix-repetition-suffix-len 200 \
  --prefix-repetition-num-prefixes 16 \
  --prefix-repetition-output-len 64 \
  --num-prompts 128 --max-concurrency 4 --seed 42 \
  --save-result --result-filename /tmp/bench-prefix-repetition.json
```

Size `prefix_len × num_prefixes` so aggregate exceeds **2×** `num_gpu_blocks × block_size`. That guarantees evictions during the run. If `num_gpu_blocks=1458` and `block_size=32` (46.6 K KV slots), `8000 × 16 = 128 K` overshoots by ~2.7× — CPU hits start landing within seconds.

But do NOT overshoot the CPU tier — aggregate > CPU capacity thrashes LRU and the **hit rate collapses**. Verified on RTX 4060 Ti: 8 prefixes × 6 K (48 K aggregate, fits in 6 GB CPU tier) → 9.4 % CPU hit rate; 16 prefixes × 10 K (160 K aggregate, 4× CPU capacity) → 2.1 % CPU hit rate even though absolute bytes transferred 2.5× higher. The right-sizing rule:

```
unique_prefix_budget_tokens ≈ offload_gib × 1024 × 1024 / kv_bytes_per_token
kv_bytes_per_token          = layers × kv_heads × head_dim × 2 (K+V) × dtype_bytes
                            (e.g. Qwen3-4B BF16: 36 × 8 × 128 × 2 × 2 ≈ 144 KiB/token)
```

For Qwen3-4B + 6 GB CPU offload that caps the CPU tier at ~41 K unique prefix tokens. Benchmark around that, not above.

After the run, diff metrics:

```bash
diff <(curl -s .../metrics-pre.txt | grep vllm:external_prefix_cache) \
     <(curl -s .../metrics-post.txt | grep vllm:external_prefix_cache)
```

Must see `external_prefix_cache_hits_total` increase. Also scan the pod log for the bidirectional transfer line:

```
KV Transfer metrics: GPU_to_CPU_total_bytes=N  GPU_to_CPU_total_time=Ts
                     CPU_to_GPU_total_bytes=M  CPU_to_GPU_total_time=Us
```

A non-zero `CPU_to_GPU_total_bytes` = offload tier served a cache hit back to GPU. That's the physical proof the offload path works end-to-end.

Compare two runs on identical traffic with and without `--kv-offloading-size` set. Look at P50/P99 TTFT and GPU prefix cache hit rate. On agentic workloads with 100k+ contexts, expect TTFT P50 to drop several seconds on returning sessions.

**Other built-in workloads relevant to cache:**
- `--dataset-name random` with `--random-prefix-len N` — simpler baseline
- LMCache repo `benchmarks/multi_round_qa/multi-round-qa.py` — stateful multi-turn chat, closer to agentic pattern
- LMCache CLI `lmcache bench engine --workload long-doc-permutator` — 5-axis stress (blended context boundaries, eviction, vocab, prefix domination, concurrency). Requires `lmcache` CLI on PATH (bundled in v0.14.0+ images but check — on CUDA 13 images the CLI may fail to import c_ops if built against CUDA 12, see LMCache #2843).

## External references

- vLLM source: `vllm/v1/kv_offload/` (native), `vllm/distributed/kv_transfer/kv_connector/v1/` (all connectors), `requirements/kv_connectors.txt` (bundled backend pins)
- `docs/features/disagg_prefill.md` — overview of all 7 connector types in the vLLM repo
- LMCache config reference: https://docs.lmcache.ai/api_reference/configurations.html
- NVIDIA GPU Operator GDS: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-operator-rdma.html

See `references/sources.md` for verification dates and probe notes.

Last verified: 2026-04-25
