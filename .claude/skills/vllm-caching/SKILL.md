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

Verify any image's CUDA version + bundled backends without pulling it:

```bash
${CLAUDE_SKILL_DIR}/scripts/inspect-vllm-image.sh <tag>
```

For other diagnostics (LMCache logs, `gdscheck`, Prometheus metrics), see `references/diagnostics.md`.

## Decision tree — which backend

Ask these in order:

1. **Single node, CPU DRAM tier only, no disk?** → `--kv-offloading-backend native`. Zero extra deps, included since v0.11.1. Start here unless there is a concrete reason to add complexity.
2. **Single node, want NVMe as a third tier?** → LMCache. `--kv-offloading-backend lmcache` + `LMCACHE_LOCAL_DISK` env vars.
3. **Disaggregated prefill across nodes (separate prefill and decode pods)?** → NixlConnector via `--kv-transfer-config`. Tunes TTFT and ITL independently.
4. **RDMA-backed KV transfer between nodes, high-throughput datacenter fabric?** → MooncakeConnector.
5. **NIXL between prefill/decode pods AND local CPU overflow on each?** → MultiConnector, composing NixlConnector + OffloadingConnector.

Do not reach for LMCache or NIXL or Mooncake just because they exist. Native offload handles the 80% case with zero operational surface area.

**For concrete config recipes for any of the above, see `references/connectors.md`.** Load that reference once a backend has been selected — it contains copy-paste-ready invocations with all required env vars, GDS host prerequisites (cuda-keyring, open kernel modules, Secure Boot), and the MultiConnector JSON format.

## Sizing math — READ BEFORE RECOMMENDING A NUMBER

**`--kv-offloading-size` is TOTAL across all TP ranks, in GiB.** This is the OPPOSITE of SGLang's equivalent flag (which is per-rank). Teams migrating from SGLang routinely under-allocate by a factor of TP.

If an SGLang config was 200 GB per GPU × 8 GPUs = 1600 GB, then on vLLM use `--kv-offloading-size 1600`. Not 200.

**For per-token KV formulas, worked slot-math examples, Dell XE9680 hardware reference numbers, and NVMe-vs-DRAM-vs-prefill load-time comparisons, see `references/hardware-sizing.md`.**

When using LMCache as the backend, keep `LMCACHE_MAX_LOCAL_CPU_SIZE` and `--kv-offloading-size` consistent. LMCache env vars win on the backend side; inconsistency leads to scheduler miscounting available slots and either over-subscribing or under-using the cache.

## Critical pitfalls

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

## Other long-context knobs worth tuning alongside offload

Offload is necessary but not sufficient for stable long-context serving. Two flags compound the effect:

- **`--block-size 32`** (default 16) — larger KV blocks reduce internal fragmentation at very long contexts. Meaningful win past ~128k; usually neutral or slight loss below 32k.
- **`--max-num-batched-tokens <N>`** — caps how many prefill tokens vLLM will batch in one step. Without it, a burst of long-prompt arrivals can starve decode and spike tail TTFT. Good starting value: 4096–8192 on H200-class.

Do not enable `--enforce-eager` as a fragmentation workaround — it disables CUDA graphs and hurts steady-state throughput by more than fragmentation costs.

## Validating that offload is actually helping

After enabling offload, measure with `vllm bench serve` against a realistic request mix:

```bash
vllm bench serve --model <model> --host <endpoint> --num-prompts 1000 --request-rate 10
```

Compare two runs on identical traffic with and without `--kv-offloading-size` set. Look at P50/P99 TTFT and `prefix_cache_hits_total` / `prefix_cache_queries_total` ratios. On agentic workloads with 100k+ contexts, expect TTFT P50 to drop several seconds on returning sessions.

## External references

- vLLM source: `vllm/v1/kv_offload/` (native), `vllm/distributed/kv_transfer/kv_connector/v1/` (all connectors), `requirements/kv_connectors.txt` (bundled backend pins)
- `docs/features/disagg_prefill.md` — overview of all 7 connector types in the vLLM repo
- LMCache config reference: https://docs.lmcache.ai/api_reference/configurations.html
- NVIDIA GPU Operator GDS: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-operator-rdma.html

See `references/sources.md` for verification dates and probe notes.

Last verified: 2026-04-24
