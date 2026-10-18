---
name: vllm-caching
description: |-
  vLLM tiered KV cache configuration for production H100/H200 clusters. Native CPU offload, LMCache (CPU+NVMe+GDS), NixlConnector (disaggregated prefill), MooncakeConnector (RDMA), MultiConnector composition. Version gates, sizing math (flag total across TP, not per-GPU — opposite of SGLang), KV-vs-weights offload distinction operators most often get wrong.
when_to_use: |-
  Trigger on "vllm kv cache", "kv offload", "prefix caching", "LMCache", "NixlConnector", "MooncakeConnector", "kv_offloading_size", "kv-offloading-backend", "disaggregated prefill", "tiered kv", "CPU offload kv", "long context concurrency", "TTFT too slow", "prefill bottleneck", "GDS cuFile", "gpu_memory_utilization full", "how many concurrent requests", "KV won't fit", "long prompts too slow", "extending vLLM KV beyond HBM". SGLang-to-vLLM migration on CPU KV sizing, whether to add LMCache to existing deploy. Also implicit contexts — "audit KV config", "deploy-memo cache", "serve_args kv", "cache strategy for {model}", "long-context serve recipe" — any time authoring/reviewing a KV-cache deploy recipe.
---

# vLLM tiered KV caching

Target audience: operators running vLLM on H100/H200-class datacenter GPUs in production. Assumes CUDA 12/13, Kubernetes or bare container deployment, multi-GPU tensor parallel.

**Where this sits.** Cache flags are one slice of a serving config: the manifest
that carries them (cache mounts, probes, image tags) is **`vllm-deployment`**,
the non-cache throughput knobs are **`vllm-performance-tuning`**, and the numbers
that justify either are **`vllm-benchmarking`** — all in the `vllm` plugin. For
the same problem on other stacks, see **`sglang-hicache`** (SGLang's tiering) and
**`lmcache-mp`** (LMCache as a standalone server rather than in-process).

## Version gates — check these FIRST

Confirm the vLLM version before recommending any config.

| Feature | First release | Notes |
|---|---|---|
| Native CPU KV offload (`vllm/v1/kv_offload/`) | **v0.11.0** (2025-10-02) | Infrastructure + scheduler integration |
| CLI flags `--kv-offloading-size` / `--kv-offloading-backend` | **v0.11.1** (2025-11-18) | Before this, required editing config objects |
| LMCache bundled in official x86 `vllm/vllm-openai` image | **v0.14.0** (2026-01-20) | arm64 had it from v0.10.2; x86 was intentionally stripped July 2025–Jan 2026 due to torch version conflict — many ops teams had to pip install LMCache at container start during that window, which is now unnecessary |
| `--calculate-kv-scales` deprecated, then removed | deprecated pre-v0.19; **removed in v0.28.0** (#49389) | Accepted with a deprecation warning through v0.27.1; on v0.28.0+ the flag no longer exists — delete it from serve args before upgrading. FP8 KV without shipped scales falls back to scale=1.0 (see pitfalls). |
| KV Offload + Hybrid Memory Allocator (HMA) | **v0.21.0** (2026-05-15) | Native offload integrates with HMA — full enablement (#41445) + sliding-window groups (#41228) + multi-connector HMA (#39571), plus Qwen3.5/Mamba hybrid support (#35520). |
| **Native multi-tier offloading** (`TieringOffloadingSpec`, fs / obj / p2p secondary tiers) | **v0.22.0** (2026-05-29) | Framework #40020 + Python filesystem tier #41735; object-store tier #41968 and per-request policy hooks landed in v0.23.0. Native offload is no longer CPU-DRAM-only — an NVMe or S3 tier no longer requires LMCache. See the decision tree. |
| **HMA on by default for capable connectors** | **v0.23.0** (2026-06-15) | #41847. `disable_hybrid_kv_cache_manager` became tri-state (`None` = auto): vLLM disables HMA only for connectors that don't subclass `SupportsHMA`. This retires the manual-flag pitfall for native offload — see "Critical pitfalls". |
| `P2pNcclConnector` removed | **v0.24.0** (2026-06-29) | #44854. Migrate to NixlConnector or the `p2p` secondary tier. |
| `p2p` secondary tier gets env-var defaults + hard `PYTHONHASHSEED` check | **v0.26.0** (2026-07-27) | #47636. `host`/`port` now default to `VLLM_P2P_SIDE_CHANNEL_HOST` (`localhost`) / `VLLM_P2P_SIDE_CHANNEL_PORT` (`5710`), not the old literal `7777`, and the tier raised at startup if `PYTHONHASHSEED` was unset — **lifted in v0.29.0** (#51875), which gives `NONE_HASH` a fixed default seed so cross-instance prefix sharing works unpinned. See `references/connectors.md`. |

Latest stable: **v0.32.0** (2026-10-18). Confirm the deployed tag before recommending a config; per-tag evidence lives in `references/sources.md`.

| Question | Answer at v0.32.0 | Action |
|---|---|---|
| Does the image bundle LMCache / NIXL / Mooncake? | Build flag `INSTALL_KV_CONNECTORS=true` confirmed on `v0.14.0`+, `v0.19.0`, `v0.19.0-cu130`, `v0.20.x`–`v0.27.x`, `v0.29.0`, `v0.32.0`, `v0.32.0-cu129`, model tags like `glm51-cu130`. Runtime imports: full pass on `v0.29.0`; on `v0.32.0` every package imports and all four KV-offload connectors load, MP adapter step unverified (see step 2). | Run the two-step check below on the exact tag before production. `v0.28.x`–`v0.31.x` are unverified, not known-bad. |
| Is the tag safe to run? | Bundled ≠ safe. Floor **v0.22.0** (CVE-2026-48746, `--api-key` bypass via `Host:` header). **v0.14.1** (CVE-2026-22778, pre-auth RCE, video models only). | Run ≥ v0.22.0. `v0.14.0`, `v0.19.0`, `v0.19.0-cu130` bundle correctly but sit below the floor. Detail: `vllm-configuration` § Server auth. |
| CUDA 12 (`-cu129`) tag? | From v0.31.0, `requirements/kv_connectors_cu12.txt` pins `lmcache == 0.4.4`, `nixl == 1.4.1`. | LMCache MP on a hybrid model needs lmcache ≥ 0.5.0 — use the CUDA 13 tag. |
| Installing a NIXL wheel by hand? | `requirements/kv_connectors.txt` pins `nixl == 1.5.0` exactly (CUDA 13; `1.4.1` on CUDA 12), `lmcache >= 0.3.9`, `mooncake-transfer-engine >= 0.3.12`, `cupy-cuda13x != 14.1.0`. | Match the pin of the tag and CUDA major in use: read `requirements/kv_connectors*.txt` at that tag. `ImportError: libcudart.so.12` importing `nixl_ep` on a CUDA 13 image = dual-wheel build bug, fixed in v0.22.1. |
| Is the tag out yet? | Container images can appear before the GitHub release. | Gate on image availability (Docker Hub tag list), not on PyPI. |

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

Starts a sleep-overridden container, exec's a Python probe that confirms `lmcache`, `nixl`, `mooncake` import cleanly; checks the LMCache MP adapter classes and the `ParallelStrategy` version-hazard symbol; lists all registered KV connectors; loads each connector class through the factory's own thunk. Exit 0 = the connectors are usable on that tag (bundling only; the security floor is separate). The four connectors it loads are the KV-offload set; the factory registers more (16 at v0.29.0), and its list is the only place the rest appear.

**lmcache version compatibility:** vLLM main imports `ParallelStrategy` from the lmcache MP adapter. The symbol was added in lmcache 0.4.4 and is absent in 0.4.3 (verified against the v0.4.3 tag), so images built around that era raise `ImportError: cannot import name 'ParallelStrategy'` when their bundled lmcache is mixed with vLLM main. The v0.29.0 image ships 0.5.4 and the symbol is present — the hazard is now confined to pinning an older image, not to the current one. Fix by pinning the pair or `pip install -U lmcache>=0.4.4` inside the container.

**Run step 2 on a GPU node.** With lmcache 0.5.6 (the `v0.32.0` image) the MP adapter classes load `libcuda.so.1` at import, so on a host or container without the NVIDIA driver the script prints `MP adapter classes FAIL  ImportError: libcuda.so.1` and exits 1 although every package imports. Treat that line alone as a probe-environment failure, not a bundling failure.

For other diagnostics (LMCache logs, `gdscheck`, Prometheus metrics), see `references/diagnostics.md`.

## Decision tree — which backend

Ask these in order:

1. **Single node, CPU DRAM tier only, no disk?** → `--kv-offloading-backend native`. Zero extra deps, included since v0.11.1. Start here unless there is a concrete reason to add complexity.
2. **Single node, want NVMe (or S3, or a peer's DRAM) as a third tier?** → **on v0.22.0+, prefer the native multi-tier framework** — `OffloadingConnector` with `spec_name: TieringOffloadingSpec` and a `secondary_tiers` list. Registered tier types are `fs` (local filesystem/NVMe), `obj` (object store), `p2p` (peer vLLM instances over NIXL), `kvcr` (v0.30.0+, see `references/connectors.md`), and `example`. Zero extra pods, no second cache implementation to keep in version-sync. LMCache in-process via `LMCacheConnectorV1` + `LMCACHE_LOCAL_DISK` remains the pre-v0.22 answer and is still the right call when a deploy needs LMCache-specific features (CacheBlend, its own controller, cross-engine sharing with SGLang).
3. **Multiple vLLM pods on the same node want a SHARED KV cache, OR cache CPU work should not contend with the inference GIL, OR cache memory needs to scale independently of GPU pods?** → **LMCache MP mode** (separate-pod LMCache server, vLLM connects via ZMQ using `LMCacheMPConnector`). Defer to the **`lmcache-mp` skill** for the DaemonSet+Deployment pattern, image pair, ZMQ protocol, L2 adapter cascade.
4. **Disaggregated prefill across nodes (separate prefill and decode pods)?** → NixlConnector via `--kv-transfer-config`. Tunes TTFT and ITL independently.
5. **RDMA-backed KV transfer between nodes, high-throughput datacenter fabric?** → MooncakeConnector.
6. **NIXL between prefill/decode pods AND local CPU overflow on each?** → MultiConnector, composing NixlConnector + OffloadingConnector.
7. **Sparse-MLA decode model (e.g. DeepSeek-style), want a host-resident tier for cold KV pages?** → **`HiSparseConnector`, v0.30.0+, experimental.** See `references/connectors.md` § HiSparseConnector.

Do not reach for LMCache or NIXL or Mooncake just because they exist. Native offload handles the 80% case with zero operational surface area. LMCache MP adds an extra pod and another image — only justified by the multi-pod-shared-cache or GIL-isolation cases above.

**For concrete config recipes for any of the above, see `references/connectors.md`.** Load that reference once a backend has been selected — it contains copy-paste-ready invocations with all required env vars, GDS host prerequisites (cuda-keyring, open kernel modules, Secure Boot), and the MultiConnector JSON format.

> **NIXL deep-dive** — NIXL itself (transfer library, 13 backend plugins, agent API, telemetry, ETCD/side-channel metadata, plugin authoring) lives in the dedicated **`nvidia-nixl`** skill. This skill covers vLLM-side wiring of NixlConnector / LMCache-P2P-over-NIXL only. Reach for `nvidia-nixl` when picking transports (`UCX_TLS`, GDS, Mooncake, libfabric…), tuning UCX, debugging `nixl_agent` directly, or writing custom plugins.

> **LMCache MP deep-dive** — the standalone-server multiprocess mode (`LMCacheMPConnector`, `lmcache server`, `lmcache/standalone:nightly`, DaemonSet+Deployment, L2 adapters: nixl_store / fs / mooncake_store / s3) is its own operational shape. The dedicated **`lmcache-mp`** skill covers it.

## Sizing math — READ BEFORE RECOMMENDING A NUMBER

**`--kv-offloading-size` is TOTAL across all TP ranks, in GiB.** This is the OPPOSITE of SGLang's equivalent flag (which is per-rank). Teams migrating from SGLang routinely under-allocate by a factor of TP.

If an SGLang config was 200 GB per GPU × 8 GPUs = 1600 GB, then on vLLM use `--kv-offloading-size 1600`. Not 200.

**For per-token KV formulas, worked slot-math examples, Dell XE9680 hardware reference numbers, and NVMe-vs-DRAM-vs-prefill load-time comparisons, see `references/hardware-sizing.md`.**

**If Model Runner V2 was opted into before v0.29.0, KV auto-sizing did not reserve CUDA graph memory.** MRV1 always did; MRV2 gained it in **v0.29.0** ([#53306](https://github.com/vllm-project/vllm/pull/53306)), explicitly to unblock making MRV2 the default. Since the default flip ships in that same release, a deployment that never set `VLLM_USE_V2_MODEL_RUNNER=1` is unaffected. An **early opt-in on v0.27.x or v0.28.0** is the exposed case: auto-sizing over-allocated KV against memory the graphs then needed. Suspect it before re-deriving a sizing formula on a box that OOMs only after capture.

**`--mamba-cache-mode all` is removed in v0.32.0** ([#58997](https://github.com/vllm-project/vllm/pull/58997)) — it now fails config validation at startup (accepted values: `align`, `none`). On v0.30.0–v0.31.x it was deprecated ([#55041](https://github.com/vllm-project/vllm/pull/55041)): it warned and forced MRV1. vLLM sets `align` itself when prefix caching is on (`vllm/model_executor/models/config.py`), so only a deployment that explicitly passes `all` is affected — delete the flag before upgrading to v0.32.0.

When using LMCache as the backend, keep `LMCACHE_MAX_LOCAL_CPU_SIZE` and `--kv-offloading-size` consistent. LMCache env vars win on the backend side; inconsistency leads to scheduler miscounting available slots and either over-subscribing or under-using the cache.

## Critical pitfalls

### `--disable-hybrid-kv-cache-manager` — required only for connectors that lack HMA support

**This changed in v0.23.0 (#41847) and the old advice is now actively harmful.** `disable_hybrid_kv_cache_manager` is tri-state, defaulting to `None` (auto): vLLM turns HMA off by itself, with a warning, only when the selected connector does not subclass `SupportsHMA`. Passing the flag by reflex on a modern build costs hybrid-model support and sliding-window performance for nothing.

Which connectors declare `SupportsHMA` at v0.32.0 (re-verified 2026-10-18 against `kv_connector/v1/base.py` and the connector classes; `HiSparseConnector`, `MoRIIOConnector` and `SimpleCPUOffloadConnector` also declare it):

| Connector | `SupportsHMA`? | Consequence |
|---|---|---|
| `OffloadingConnector` (native, `--kv-offloading-size`) | **yes** | Do NOT pass the flag. HMA stays on. |
| `NixlConnector` / `NixlPullConnector` / `NixlPushConnector` | **yes** | Do NOT pass the flag. |
| `MooncakeConnector`, `MooncakeStoreConnector` | **yes** | Do NOT pass the flag. |
| `MultiConnector` | **yes**, but only if *every* child supports HMA | One non-HMA child disables HMA for the whole composition. |
| `LMCacheMPConnector` | **yes** with lmcache ≥ 0.5.0 (the external package's class); the vLLM-repo fallback class does not | Keep the external `lmcache` import healthy and omit the flag. See the `lmcache-mp` skill. |
| `LMCacheConnectorV1` (in-process) | **no** | HMA auto-disables. This is why LMCache in-process is still blocked on hybrid models (LMCache #3106). |

On vLLM ≤ v0.22.x the flag was mandatory with `OffloadingConnector`, and the startup error named it:

```
ValueError: Connector OffloadingConnector does not support HMA but HMA is enabled.
Please set `--disable-hybrid-kv-cache-manager`.
```

If a deploy still hits that error on v0.23.0+, the cause is a connector genuinely lacking HMA support, not a missing flag — read the warning line vLLM emits, which names the connector.

### Hybrid models (Qwen3.5, Gemma-4, Mamba+attention)

Pick in this order: native offload → native multi-tier (disk/object tier) → LMCache MP → never the in-process `LMCacheConnectorV1`.

| Path | Status at v0.32.0 | Action |
|---|---|---|
| Native offload (`OffloadingConnector`) | Works from v0.21.0; HMA on by default from v0.23.0 | Serve with `--kv-offloading-size` and no HMA flag. Do NOT apply the old Gemma-4 + spec-decode workaround (disable HMA + shrink `--max-model-len`): the 0% hit-rate bug (vLLM#40624) is fixed and the workaround now costs performance. |
| LMCache MP (`LMCacheMPConnector`, lmcache ≥ 0.5.0) | Supported; upstream recipes for Gemma 3/4, gpt-oss, Qwen3.5/3.6, DeepSeek-V4-Flash, GLM 5.1/5.2, MiniMax-M3 | Use when a hybrid needs an LMCache tier. Needs a CUDA 13 image (`-cu129` bundles lmcache 0.4.4). Detail: `lmcache-mp`. |
| LMCache in-process (`LMCacheConnectorV1`) | **Blocked**, LMCache#3106 open: no `SupportsHMA`, so HMA auto-disables and the single-shape `MemoryObj.tensor` fails on mixed attention groups | Never use on a hybrid. The object-group-collapsing workaround posted on #3106 is unverified; see `lmcache-mp`. |
| `MoRIIOConnector` (ROCm), SWA hybrids | READ mode works from v0.30.0. WRITE raises `NotImplementedError: MoRIIO WRITE mode does not support hybrid KV cache groups` | Use READ mode, or pass `--disable-hybrid-kv-cache-manager` with WRITE. |
| `MoRIIOConnector`, Mamba/KDA hybrids | READ mode from v0.31.0, startup-checked: one transferable attention group, two Mamba states (conv + SSM), DSpark the only spec-decode method. WRITE fails with `set kv_connector_extra_config.read_mode=true` | Set `kv_connector_extra_config.read_mode=true` and stay inside the checked limits. |

**`--prefix-cache-retention-interval` (SWA and SSM models only).** From v0.29.0 the default is `0`: only the latest replayable prompt boundary is retained (the system prompt is still kept); a positive `N` retains every `N` tokens.

- Set it as the CLI flag. `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` is removed from v0.30.0 and does nothing.
- Hybrids running EAGLE or MTP get dense retention automatically; they need no flag.
- Agentic multi-turn traffic without spec-decode is where `0` bites. If prefix hit rate drops after an upgrade to v0.29.0+, set a positive interval and re-measure before changing anything else.
- From v0.30.0 the interval also gates which SWA/SSM chunks `OffloadingConnector` offloads (native and multi-tier). It must be a multiple of the SWA group's `tokens_per_chunk`, or startup raises `ValueError`.

v0.29.0+ also cuts Mamba prefix-caching TTFT by 9–25% with no flag; count it when weighing an upgrade for a Mamba or hybrid deploy.

Pure-transformer models (Qwen3-14B, Llama-3, Mistral-7B) are unaffected; the standard offload recipes work on any v0.14.0+ tag.

Recheck the hybrid state at a new tag:

```bash
gh issue view 3106 --repo LMCache/LMCache --json state,updatedAt   # LMCacheConnectorV1 hybrid block
# which connectors declare HMA support at a given tag:
git -C <vllm-clone> grep -n "SupportsHMA)" v0.32.0 -- vllm/distributed/kv_transfer/kv_connector/v1/
```

### `--cpu-offload-gb` is NOT the same as `--kv-offloading-size`

| Flag | What it offloads | Unit | Effect |
|---|---|---|---|
| `--cpu-offload-gb` | **Model weights** | Per-GPU | Hurts prefill throughput; lets larger-than-HBM models fit |
| `--kv-offloading-size` | **KV cache** | Total across TP | Helps TTFT on cache hits; no effect on compute throughput |

Never recommend `--cpu-offload-gb` for a KV-tiering question. They are different subsystems with opposite throughput implications.

### FP8 KV cache without shipped scales

`--calculate-kv-scales` is gone from v0.28.0 (#49389); through v0.27.1 it only warned and had no effect. vLLM always loads scales from the checkpoint. **On v0.32.0, `--kv-cache-dtype auto` selects `fp8_e4m3` for GLM-5.x (`GlmMoeDsaForCausalLM`) on SM100** (#60140, #60281) — pass `--kv-cache-dtype bfloat16` to keep BF16 KV there. If `--kv-cache-dtype fp8` is set on a model whose checkpoint doesn't ship calibrated `k_scale`/`v_scale`, vLLM defaults to scale=1.0, which can clip pathological activations — especially on long code contexts where specific tokens produce large activations in specific layers.

Symptoms: subtle quality degradation, often only past 128k context. "Usually works fine" is the common operator experience because most activations fit, but the risk is real.

Recommend: stay on BF16 KV and use offload to claw back the memory. The prefill savings from offload hits dwarf whatever would be saved by moving KV from BF16 to FP8.

### NVSwitch doesn't accelerate host-to-GPU offload

Operators new to tiered caching sometimes assume NVSwitch/NVLink helps. It doesn't — those interconnects are GPU↔GPU only. KV offload traffic is **CPU DRAM → PCIe Gen5 x16 → GPU HBM**, one link per GPU. See `references/hardware-sizing.md` for the bandwidth numbers on XE9680-class hardware.

### NVMe tier is NOT a hot path

Loading a 100k-token BF16 context from NVMe takes ~5–7 seconds (Gen4 U.2, buffered) — still beats a ~10 second re-prefill, but DRAM beats NVMe by 20×. Size the DRAM tier to hold the hot working set; treat NVMe as overflow for sessions from "earlier today" that might come back.

## Offload "doesn't help" — root causes

Check in order, most common first:

1. **Concurrency is already at the memory wall, not the cache.** On an 8× H200 with a 300–500 GB weight footprint serving 200k+ contexts, 1–2 live slots is physics — compute jumped ~6× over the previous generation but memory bandwidth only ~1.6×. Adding offload doesn't raise live concurrency; it raises the *warm-set* size (sessions that skip re-prefill on return). Confirm the expectation is "more warm sessions," not "more simultaneous running."
2. **Hit rate is low.** No prefix reuse in the workload → offload gains nothing. Check `prefix_cache_hits_total` / `prefix_cache_queries_total`. Non-agentic, non-RAG traffic often has low prefix locality.
3. **Prefix caching is off.** It is on by default (`enable_prefix_caching: bool = True` in `vllm/config/cache.py` at v0.32.0); check the serve args for `--no-enable-prefix-caching`. With it off, offload has nothing to hit against.
4. **Flag sized as per-GPU (SGLang habit).** Check `vllm:cache_config_info` — the number reported is what vLLM actually allocated. If it's 1/TP of what was expected, this is the cause.
5. **Cold cache.** First N requests pay full prefill cost while filling the cache. Measure steady-state, not ramp-up.
6. **Max context set higher than needed.** If `--max-model-len` is 200k but typical requests are 8k, the scheduler reserves capacity for 200k; effective concurrency is starved. Tune `--max-model-len` to the 95th or 99th percentile of real traffic, not the theoretical maximum.
7. **Actually compute-bound.** Short prompts + many tokens out = decode-dominated. Offload can't help; more GPUs or a smaller model is the fix.

## Known bugs to check before recommending offload

States verified 2026-10-18. Before authoring an offload deploy, recheck each row with `gh issue view <N> --repo <repo> --json state,stateReason`.

| Issue | State | Affects | Avoidance |
|---|---|---|---|
| [LMCache#2942](https://github.com/LMCache/LMCache/issues/2942) | closed by the stale bot — **NOT fixed** (fix PR #3006 closed unmerged) | `LocalCPUBackend.allocate()` deadlocks when the staging buffer fills; reproduced with `use_hot=False` and with `use_hot=True` | Keep `LMCACHE_LOCAL_CPU=True` (default); never `use_hot=False`. Treat the closure as live in 0.5.x |
| [LMCache#3106](https://github.com/LMCache/LMCache/issues/3106) | **open** | `LMCacheConnectorV1` unusable on hybrid-attention models (Gemma-4, Qwen3.5/3.6, DeepSeek-V4): single-shape `MemoryObj.tensor` fails on a multi-group buffer | Use native offload or LMCache **MP** mode; never the in-process connector |
| [LMCache#2502](https://github.com/LMCache/LMCache/issues/2502) | closed not_planned — not being fixed | `LocalDiskBackend` crashes vLLM under burst allocation pressure | Keep `LMCACHE_ENABLE_ASYNC_LOADING=False` on a disk tier; DRAM-only stays the simpler default |

Fixed at or below the v0.22.0 security floor: segfault with `--decode-context-parallel-size` + offload (#40259, v0.21.0), Qwen3.5 native-offload start failure (#36463, v0.21.0), `SimpleCPUOffloadScheduler` TOCTOU `AssertionError: Expected N hit tokens` (#39702, v0.22.0). On an older tag, upgrade rather than work around them.

## Other long-context knobs worth tuning alongside offload

Offload is necessary but not sufficient for stable long-context serving. Tune these alongside it:

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

But do NOT overshoot the CPU tier — aggregate > CPU capacity thrashes LRU and the **hit rate collapses** (verified on RTX 4060 Ti: 48 K aggregate fitting a 6 GB tier hit 9.4 %, while 160 K aggregate at 4× capacity dropped to 2.1 % despite moving 2.5× the bytes). Size the bench to the CPU tier's unique-prefix-token budget — the `kv_bytes_per_token` formula and the worked Qwen3-4B cap (~41 K tokens for 6 GB) are in `references/hardware-sizing.md`.

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

## Done when — authoring or auditing a KV-cache config

The recipe is finished only when every item holds for the exact tag deployed:

1. Every cache-related flag and env var in the serve args is accounted for: available at that tag (version gates), not removed (`--calculate-kv-scales`, `--mamba-cache-mode all`, `VLLM_PREFIX_CACHE_RETENTION_INTERVAL`), and not the weights flag `--cpu-offload-gb` standing in for KV offload.
2. `--kv-offloading-size` is the TP-wide total in GiB; with LMCache, `LMCACHE_MAX_LOCAL_CPU_SIZE` agrees with it.
3. `--disable-hybrid-kv-cache-manager` appears only for a connector without `SupportsHMA` or MoRI-IO WRITE mode on a hybrid.
4. The image tag passed both bundling steps and is ≥ v0.22.0.
5. Every row of "Known bugs" was rechecked and its avoidance applied.
6. A validation run shows `external_prefix_cache_hits_total` rising and a non-zero `CPU_to_GPU_total_bytes`.

## External references

- vLLM source: `vllm/v1/kv_offload/` (native), `vllm/distributed/kv_transfer/kv_connector/v1/` (all connectors), `requirements/kv_connectors.txt` (bundled backend pins)
- `docs/features/disagg_prefill.md` — overview of the disaggregation connector types (the doc says 9 at v0.32.0)
- LMCache config reference: https://docs.lmcache.ai/api_reference/configurations.html
- NVIDIA GPU Operator GDS: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-operator-rdma.html

See `references/sources.md` for verification dates and probe notes.
