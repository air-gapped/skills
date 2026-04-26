---
name: lmcache-mp
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  LMCache multiprocess (MP) mode — standalone LMCache server in its own pod/process that vLLM connects to over ZMQ. Provides process isolation, no GIL contention on the inference path, one cache shared by multiple vLLM pods on the same node, and CPU-memory scaling independent of GPU memory. Covers the `LMCacheMPConnector` path (the new direction; `LMCacheConnectorV1` in-process path still works but is being upstaged), DaemonSet+Deployment K8s pattern, L1 (CPU DRAM) + L2 (NIXL POSIX / GDS / HF3FS, plain fs, mooncake_store, s3) cascade, the `lmcache/standalone:nightly` + `lmcache/vllm-openai:latest-nightly` image pair vs stock `vllm/vllm-openai`, and the production gotchas (--no-enable-prefix-caching on vLLM side, --disable-hybrid-kv-cache-manager required, vLLM/lmcache version compatibility, hybrid-model NOT supported yet, cache_salt fallback adapter bug).
when_to_use: |-
  Trigger on "LMCache MP", "LMCacheMPConnector", "LMCache standalone", "lmcache server", "lmcache daemon", "lmcache pod", "lmcache daemonset", "ZMQ kv connector", "lmcache shared across pods", "separate cache process", "lmcache nixl_store", "lmcache mooncake adapter", "L1+L2 cache", "lmcache GIL contention", or whenever the user mentions running LMCache as its own pod/process rather than in-process. Also trigger on "LMCacheConnectorV1 vs LMCacheMPConnector", "lmcache:standalone image", "vllm-openai:latest-nightly", or any troubleshooting of LMCacheMP deployments. For native vLLM CPU offload without a separate pod (`--kv-offloading-size` / OffloadingConnector), defer to `vllm-caching`. For NIXL transport-layer details under the `nixl_store` L2 backend, defer to `nvidia-nixl`. For SGLang's equivalent (HiCache), see `sglang-hicache`.
---

# LMCache multiprocess (MP) mode

Target audience: operators running vLLM on H100/H200/B200-class GPUs in production who need KV-cache extension beyond HBM and have outgrown the in-process LMCache path. Assumes Kubernetes or bare container deployment.

## Why this exists separately from `vllm-caching`

`vllm-caching` covers vLLM's **native** CPU-offload (`--kv-offloading-size`, `OffloadingConnector`) and the **in-process** `LMCacheConnectorV1` (LMCache linked into the vLLM worker). MP mode is structurally different:

- LMCache runs in its **own process / container / pod** with its own CPU and memory budget.
- vLLM talks to it over **ZMQ** (DEALER/ROUTER pattern, default port 5555).
- One LMCache server can serve **multiple vLLM pods on the same node** — they share the L1 cache.
- L2 cascade (NVMe, S3, Mooncake, HF3FS) is configured on the LMCache side, not vLLM side.

Different image pair, different deployment shape, different troubleshooting surface. Hence its own skill.

## Decision tree — pick a path

Ask in order:

1. **Single vLLM pod, only need CPU DRAM tier, no node-shared cache?**
   → Native offload (`--kv-offloading-size N --kv-offloading-backend native --disable-hybrid-kv-cache-manager`). Zero extra pods. Use the `vllm-caching` skill, not this one.

2. **Single vLLM pod, need NVMe as a third tier, but no other pod will share the cache?**
   → In-process `LMCacheConnectorV1` (`--kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'` + `LMCACHE_LOCAL_DISK` env vars). Still in vllm-caching skill.

3. **Multiple vLLM pods on the same node should share a KV cache, OR you want to isolate cache CPU work from inference (no GIL contention), OR you want to scale cache CPU memory independently of GPU pods?**
   → **MP mode. This skill.**

4. **Disaggregated prefill across nodes (separate prefill and decode pods, KV transferred between them)?**
   → NixlConnector or MooncakeConnector. See `vllm-caching` (and `nvidia-nixl` for transport-level tuning). MP can layer on top of these via MultiConnector.

Don't reach for MP mode just because it's newest — it adds operational surface (extra DaemonSet, ZMQ network path, two images to keep in sync, version-pin dance). The in-process LMCacheConnectorV1 still works fine for single-pod deployments.

## Version gates — check these FIRST

| Component | What you need | Notes |
|---|---|---|
| vLLM | **v0.19.0 or newer** for `LMCacheMPConnector` registered in `factory.py` | Pre-0.19 had only `LMCacheConnectorV1`. Both connectors coexist in 0.19+. |
| vLLM | **v0.20.0 or main** for `cache_salt` propagation through MP | PR #39837 added per-user/per-tenant cache isolation. Repo-local fallback adapter has a known bug — see Pitfalls below. |
| LMCache | **0.4.0+** for the MP adapter file (`lmcache.integration.vllm.vllm_multi_process_adapter`) | Moved into LMCache repo on 2026-01-07 (PR #2360). Earlier versions had it in vLLM. |
| LMCache | **0.4.4+** if running vLLM main | vLLM main imports `ParallelStrategy` symbol that doesn't exist in 0.4.3. Verified 2026-04-26 against tags v0.4.3 (no class) vs v0.4.4 (has class). |
| LMCache | **dev branch** for actively-evolving MP features (HTTP API, runtime plugins, L2 throughput metrics) | The MP-mode docs at `docs/source/mp/` explicitly say "latest dev branch recommended." |

### Image bundling (what's actually in the container)

Verified 2026-04-26 inside `vllm/vllm-openai:v0.19.1` (sleep-overridden, exec'd in):

| Package | Version in v0.19.1 image | Import works? | Notes |
|---|---|---|---|
| `vllm` | 0.19.1 | OK | — |
| `lmcache` | 0.4.3 | OK | `ParallelStrategy` class **NOT** present yet (added 0.4.4) |
| `nixl` | 0.9.0 | OK | — |
| `mooncake-transfer-engine` | 0.3.10.post1 | OK as `import mooncake` | Pip name vs import name differ |
| `lmcache` CLI | — | `/usr/local/bin/lmcache` | Server entrypoint ready out of the box |

All three KV connector classes (`OffloadingConnector`, `LMCacheConnectorV1`, `LMCacheMPConnector`) import cleanly in v0.19.1. **Bundling is real this time** — no pip install at container start needed for v0.19.x. The torch-conflict era of mid-2025 is over.

But: **always verify the tag you actually deploy** with `scripts/verify-bundling.sh <tag>`. It builds a sleep-overridden container, runs the import test, prints the version table. ~30 seconds (after pull).

## Quick start (Docker, single node)

Two containers. The LMCache server is a separate process; vLLM connects over ZMQ to localhost:6555.

```bash
# Terminal 1 — LMCache server
docker run --runtime nvidia --gpus all \
    --network host --ipc host \
    lmcache/standalone:nightly \
    /opt/venv/bin/lmcache server \
    --l1-size-gb 60 --eviction-policy LRU --max-workers 4 --port 6555

# Terminal 2 — vLLM (connects to LMCache via ZMQ)
docker run --runtime nvidia --gpus all \
    --network host --ipc host \
    lmcache/vllm-openai:latest-nightly \
    Qwen/Qwen3-14B \
    --no-enable-prefix-caching \
    --disable-hybrid-kv-cache-manager \
    --kv-transfer-config '{"kv_connector":"LMCacheMPConnector",
                           "kv_role":"kv_both",
                           "kv_connector_extra_config":{"lmcache.mp.port":6555}}'
```

Required Docker flags:

- `--network host` — vLLM container needs to reach LMCache on localhost:6555.
- `--ipc host` — CUDA IPC shared-memory transfers require shared `/dev/shm`.
- `--runtime nvidia --gpus all` — both containers see GPUs (the LMCache server uses GPU-side IPC even though it doesn't run inference).

Flags on the **vLLM side** that operators forget:

- `--no-enable-prefix-caching` — vLLM's own prefix cache is **OFF**. LMCache MP handles prefix caching externally.
- `--disable-hybrid-kv-cache-manager` — required by `LMCacheMPConnector` (raises a clear `RuntimeError` at startup if missing). Same restriction as `OffloadingConnector`.

## Kubernetes (the production shape)

The canonical pattern is **DaemonSet (LMCache) + Deployment (vLLM)**: one LMCache server per node serves multiple vLLM pods on that node.

Example manifests live in the LMCache repo at `examples/multi_process/`:
- `lmcache-daemonset.yaml` — LMCache server, one per node
- `vllm-deployment.yaml` — vLLM pods that connect to the node-local LMCache via `status.hostIP`

Architecture details that bite if missed:

- **`hostNetwork: true` on the DaemonSet** — vLLM pods discover the LMCache server via the node's `status.hostIP`. Without `hostNetwork`, the server's listening port isn't reachable from sibling pods.
- **Both containers mount `/dev/shm` from the host** — required for CUDA IPC.
- **GPUs are NOT requested in the DaemonSet** — the LMCache server doesn't run inference. The NVIDIA container runtime gives it just enough GPU access for IPC-based transfers. Requesting GPUs there would steal them from vLLM pods.
- **Multiple vLLM pods on the same node automatically share** the same LMCache DaemonSet instance — that's the whole point.
- **LMCache pods on non-GPU nodes will crash with CUDA init errors.** Constrain the DaemonSet to GPU nodes via nodeSelector.

For the full deployment recipe (sample YAMLs, prereqs, monitoring integration, cleanup), see `references/deployment.md`.

For the L1+L2 storage architecture (NIXL adapters, fs, mooncake_store, s3, eviction policies), see `references/l2-storage.md`.

## Hybrid model status — read before recommending MP for Qwen3.5/Gemma4/Mamba

**LMCache MP does NOT yet support hybrid models** (sliding-window + full attention, or attention + Mamba). Tracker: [LMCache#2845](https://github.com/LMCache/LMCache/issues/2845).

Open community work: [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261) (HybridOffloadPlanner + MultiConnector hybrid awareness + mamba alignment) and [LMCache#2879](https://github.com/LMCache/LMCache/pull/2879) (garbled output fix). Both still open as of 2026-04-26. A community-contributed patch in #2845 works for Qwen3.5-27B specifically and is explicitly NOT production-ready.

**Don't recommend MP for hybrid-model production today.** Either:

1. Use stock `vllm/vllm-openai:v0.19.1+` with native `--kv-offloading-size` (also requires `--disable-hybrid-kv-cache-manager` — see vllm-caching for the prefix-cache trade-off and the EAGLE/MTP spec-decode interaction).
2. Wait for the `[kv_offload+HMA][N/N]` series to complete in vLLM (parts 0–11 merged through 2026-04-25, the final hybrid-aware planner PR still pending). When done, native OffloadingConnector becomes the sanctioned hybrid-model path. See `vllm-caching` for the timeline.
3. For pure-transformer models (Qwen3-14B, Llama-3, Mistral-7B, etc.), MP mode is fine today.

## Critical pitfalls

### 1. `LMCacheMPConnector` requires `--disable-hybrid-kv-cache-manager`

Same restriction as `OffloadingConnector`. Without it the engine fails at startup:

```
RuntimeError: LMCacheMPConnector only works without hybrid kv cache manager.
Please pass --disable-hybrid-kv-cache-manager when starting vllm
```

Source: `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:78` (verified 2026-04-26).

### 2. vLLM's own prefix cache must be OFF

Always set `--no-enable-prefix-caching` on the vLLM side when using LMCacheMPConnector. LMCache handles prefix caching externally. Leaving vLLM's own prefix cache on creates double-counting and inconsistent hit reporting.

### 3. lmcache `ParallelStrategy` version hazard

vLLM `main` (post-2026-03) imports `ParallelStrategy` from `lmcache.integration.vllm.vllm_multi_process_adapter`. This class does **not** exist in lmcache 0.4.3 (verified against the v0.4.3 tag on 2026-04-26). It was added in 0.4.4.

| vLLM version | Required lmcache |
|---|---|
| v0.19.0, v0.19.1 | 0.4.0+ (works with bundled 0.4.3) |
| v0.20.0 | 0.4.x (verify on the released image) |
| main / nightly | **0.4.4+** required |

If you mix vLLM main with the v0.19.1 image's bundled 0.4.3, expect:

```
ImportError: cannot import name 'ParallelStrategy' from
  'lmcache.integration.vllm.vllm_multi_process_adapter'
```

Either pin to a matching pair or pip-upgrade lmcache inside the container.

### 4. cache_salt fallback adapter mismatch (vLLM main, [vLLM#40040](https://github.com/vllm-project/vllm/issues/40040))

PR #39837 added `cache_salt`/`cache_salts` keyword args at the LMCache MP connector call sites, but the **repo-local fallback adapter** (`vllm/distributed/kv_transfer/kv_connector/v1/lmcache_integration/multi_process_adapter.py`) still has the old method signatures. The external `lmcache` package is fine — only the fallback path used when `import lmcache.integration.vllm.vllm_multi_process_adapter` fails will trip:

```
TypeError: LMCacheMPSchedulerAdapter.maybe_submit_lookup_request()
  got an unexpected keyword argument 'cache_salt'
```

Don't rely on the fallback adapter. Make sure the external lmcache imports successfully (`scripts/verify-bundling.sh`).

### 5. SGLang-style per-rank sizing is wrong here

LMCache `--l1-size-gb` is the **total** L1 size for that LMCache server, not per-GPU. The LMCache server is a single process. Don't multiply by TP size.

(This is the same direction as vLLM's `--kv-offloading-size` — total. Opposite of SGLang.)

### 6. Eviction tuning matters under steady load

Defaults (`--eviction-policy LRU --eviction-trigger-watermark 0.8 --eviction-ratio 0.2`) are fine for bursty traffic. Under sustained pressure, frequent eviction cycles can stutter cache hits. Lower the watermark (0.7) or raise the ratio (0.3) if logs show eviction every few seconds.

### 7. CUDA IPC requirements

`--ipc host` (Docker) or mounting `/dev/shm` from the host (K8s) is mandatory. Without it, CUDA IPC shared-memory transfers between vLLM and LMCache pods fail silently or at startup with cryptic errors. The DaemonSet + Deployment example YAMLs show the right `volumes`/`volumeMounts` pattern.

## Validating that MP is helping

The validation method is the same as for native CPU offload — `vllm bench serve --dataset-name prefix_repetition`, then diff `vllm:external_prefix_cache_*` Prometheus counters before and after. See `vllm-caching` for the methodology and right-sizing math (`unique_prefix_budget_tokens ≈ l1_size_gib × 1024 × 1024 / kv_bytes_per_token`).

Additional MP-specific signals:

- **LMCache server `/api/healthcheck`** (HTTP server variant, port 8080 default) returns `{"status":"healthy"}` when the engine is initialized. Wire this into K8s liveness/readiness probes.
- **LMCache `/api/status`** dumps detailed internal state (L1 cache, L2 adapters, controllers, registered GPUs, sessions). Use during incident triage.
- **Prometheus on LMCache port 9090** — set `--prometheus-port` to override. The MP server publishes its own metrics independent of vLLM's.
- **Bidirectional KV transfer log line** in vLLM pod log:
  ```
  KV Transfer metrics: GPU_to_CPU_total_bytes=N  GPU_to_CPU_total_time=Ts
                       CPU_to_GPU_total_bytes=M  CPU_to_GPU_total_time=Us
  ```
  Non-zero `CPU_to_GPU_total_bytes` proves the offload path is serving hits back.

## When the user says "it's slower with LMCache MP"

Ranked by likelihood:

1. **vLLM's own prefix cache is still on** (`--no-enable-prefix-caching` missing). Both caches racing → worse than either alone.
2. **Hit rate is low** — the workload doesn't have prefix locality. MP can't help random traffic.
3. **DaemonSet not on the same node as the vLLM pod** — `hostNetwork` misconfigured, or the vLLM pod scheduled to a node without an LMCache instance, falling through to no-cache or RPC failures.
4. **L1 sized smaller than working set** → constant eviction, hit rate collapses. Right-size with the formula in vllm-caching.
5. **`/dev/shm` not host-mounted** → CUDA IPC degraded to a slower fallback. Verify both pods reference the host `/dev/shm`.
6. **lmcache version mismatch** → falling through to the broken repo-local fallback adapter. Run `verify-bundling.sh`.

## External references

- LMCache repo: https://github.com/LMCache/LMCache (clone at `~/projects/github.com/LMCache/LMCache`)
- LMCache MP docs: `docs/source/mp/` in the repo (`index.rst`, `quickstart.rst`, `deployment.rst`, `l2_storage.rst`, `architecture.rst`, `http_api.rst`, `observability.rst`, `tracing_and_debugging.rst`)
- vLLM connector source: `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py` (clone at `~/projects/github.com/vllm-project/vllm`)
- Example K8s manifests: `LMCache/LMCache/examples/multi_process/`
- Hybrid model tracker: [LMCache#2845](https://github.com/LMCache/LMCache/issues/2845), [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261)
- cache_salt fallback bug: [vLLM#40040](https://github.com/vllm-project/vllm/issues/40040)

See `references/sources.md` for verification dates and the inspection ritual.

Last verified: 2026-04-26.
