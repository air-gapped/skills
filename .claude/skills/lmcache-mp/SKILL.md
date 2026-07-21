---
name: lmcache-mp
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  LMCache multiprocess (MP) mode — standalone LMCache server in its own pod/process that vLLM connects to over ZMQ. Gives process isolation, no GIL contention on the inference path, one cache shared by multiple vLLM pods per node, and CPU-memory scaling independent of GPU memory. Covers the `LMCacheMPConnector` path (vs the in-process `LMCacheConnectorV1`), the DaemonSet+Deployment K8s pattern and LMCache Operator, the L1 (CPU DRAM) + L2 (NIXL, fs, mooncake_store, s3, Redis) cascade, the `lmcache/standalone` + `lmcache/vllm-openai` image pair, hybrid-attention model support (Gemma 3/4, Qwen3.5/3.6 GDN, DeepSeek-V4-Flash, GLM 5.x, MiniMax-M3) via `SupportsHMA`, and the production gotchas (`--no-enable-prefix-caching`, vLLM/lmcache version pins, object-group separation, cache_salt fallback bug).
when_to_use: |-
  Trigger on "LMCache MP", "LMCacheMPConnector", "LMCache standalone", "lmcache server", "lmcache daemon", "lmcache pod", "lmcache daemonset", "ZMQ kv connector", "lmcache shared across pods", "separate cache process", "lmcache nixl_store", "lmcache mooncake adapter", "L1+L2 cache", "lmcache GIL contention", "LMCacheConnectorV1 vs LMCacheMPConnector", "lmcache:standalone image", or any troubleshooting of LMCacheMP deployments — whenever LMCache runs as its own pod/process rather than in-process. For native vLLM CPU offload without a separate pod (`--kv-offloading-size` / OffloadingConnector), defer to `vllm-caching`. For NIXL transport-layer details under the `nixl_store` backend, defer to `nvidia-nixl`. For SGLang's equivalent (HiCache), see `sglang-hicache`.
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
   → Native offload (`--kv-offloading-size N --kv-offloading-backend native`; no HMA flag on vLLM v0.23.0+). Zero extra pods. Use the `vllm-caching` skill, not this one.

2. **Single vLLM pod, need NVMe as a third tier, but no other pod will share the cache?**
   → In-process `LMCacheConnectorV1` (`--kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'` + `LMCACHE_LOCAL_DISK` env vars). Still in vllm-caching skill.

3. **Multiple vLLM pods on the same node should share a KV cache, OR you want to isolate cache CPU work from inference (no GIL contention), OR you want to scale cache CPU memory independently of GPU pods?**
   → **MP mode. This skill.**

4. **Disaggregated prefill across nodes (separate prefill and decode pods, KV transferred between them)?**
   → NixlConnector or MooncakeConnector. See `vllm-caching` (and `nvidia-nixl` for transport-level tuning). MP can layer on top of these via MultiConnector.

Don't reach for MP mode just because it's newest — it adds operational surface (extra DaemonSet, ZMQ network path, two images to keep in sync, version-pin dance). The in-process LMCacheConnectorV1 still works fine for single-pod deployments.

## Version gates — check these FIRST

Current stable pair (2026-07): **vLLM v0.25.1** (2026-07-14) + **LMCache v0.5.1** (2026-07-06). v0.19.1 remains the verified-floor bundling example below.

| Component | What you need | Notes |
|---|---|---|
| vLLM | **v0.19.0 or newer** for `LMCacheMPConnector` registered in `factory.py` | Pre-0.19 had only `LMCacheConnectorV1`. Both connectors coexist in 0.19+. Connector source path stable through v0.25.1. |
| vLLM | **v0.20.0+** for `cache_salt` propagation through MP | PR #39837 added per-user/per-tenant cache isolation. Repo-local fallback adapter has a known bug — see Pitfalls below. |
| vLLM | **v0.23.0+** for HMA-by-default | #41847 made `disable_hybrid_kv_cache_manager` tri-state; combined with LMCache 0.5.x's `SupportsHMA` declaration this is what unlocks hybrid models in MP mode. |
| LMCache | **0.4.0+** for the MP adapter file (`lmcache.integration.vllm.vllm_multi_process_adapter`) | Moved into LMCache repo on 2026-01-07 (PR #2360). Earlier versions had it in vLLM. |
| LMCache | **0.4.4+** for vLLM v0.20+/main | vLLM main imports `ParallelStrategy` symbol that doesn't exist in 0.4.3. Verified against tags v0.4.3 (no class) vs v0.4.4 (has class); still present at v0.5.1. |
| LMCache | **0.5.1 recommended** as current stable | 0.5.0 brought P2P KV transfer to MP mode (#3740/#3762), Device-DAX L1 overflow, asymmetric serde (FP16 key / FP8 value), and a wave of renames. 0.5.1 added L2→L1 warm-prefetch (#3827), `HiddenStateStore` (#3221), an AMD `hipFile` GDS-L1 backend (#3843), TurboQuant serde for L2, and configurable `disk_io_threads`. |
| LMCache | **0.5.x required** for hybrid-attention models | The `SupportsHMA`-declaring connector lives in `lmcache/integration/vllm/lmcache_mp_connector.py`. See the hybrid-model section. |

**Renames in 0.5.0 that break old greps and docs:** `MPCacheEngine` → `MPCacheServer`, `GPUKVFormat` → `EngineKVFormat` (`gpu_kv_*` → `engine_kv_*`), `GPUTransferModule` → `LMCacheDrivenTransferModule`, `NonGPUTransferModule` → `EngineDrivenTransferModule`. The CLI was also refactored into multi-subcommand form (#3678).

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
- No HMA flag. On lmcache 0.5.x, `--disable-hybrid-kv-cache-manager` is neither required nor wanted (see Pitfall 1); on lmcache ≤ 0.4.x it is required.

## Kubernetes (the production shape)

The canonical pattern is **DaemonSet (LMCache) + Deployment (vLLM)**: one LMCache server per node serves multiple vLLM pods on that node.

An LMCache Kubernetes Operator reconciles an `LMCacheEngine` custom resource into the DaemonSet + Service + ConfigMap. **Current release is `operator-v0.5.0` (2026-06-25)** — the version numbering jumped from the old `operator-v0.1.1` (2026-05-18) line, so pin deliberately; `operator-v0.5.1rc1` (2026-07-20) is a release candidate, not stable. Install via the `install.yaml` from the release. Prefer it over hand-rolled manifests for new clusters; the hand-written YAML in `references/deployment.md` remains the manual alternative and shows what the operator generates.

Operator capabilities added in the 0.5 line (LMCache 0.5.1 notes): a **mutating webhook that auto-injects the `LMCacheEngine` connection into vLLM pods** (#3822), so vLLM Deployments no longer hand-write the `status.hostIP` plumbing; a configurable `hostNetwork` field on the CRD (#3849); and optional privileged mode on the engine DaemonSet (#3943).

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

## Hybrid model status — supported as of LMCache 0.5.x

**This inverted in the 0.5 line. MP mode now supports hybrid-attention models officially**, and the old "don't recommend MP for hybrids" guidance is obsolete. `LMCacheMPConnector` declares vLLM's `SupportsHMA` interface (`lmcache/integration/vllm/lmcache_mp_connector.py:512`, verified at tag v0.5.1), so vLLM keeps its hybrid KV cache manager **enabled** and exposes multiple KV cache groups — you do not pass `--disable-hybrid-kv-cache-manager`, and you do not need any HMA-related flag.

Upstream ships per-model recipes (`docs/source/mp/hybrid_models.rst`, published at https://docs.lmcache.ai/mp/hybrid_models.html) for:

| Model | Attention layout |
|---|---|
| Gemma 2 / 3 / 4, gpt-oss | Interleaved sliding-window + full |
| Qwen3.5 / Qwen3.6, Qwen3-Next and other GDN hybrids | Mamba / Gated-DeltaNet + full |
| DeepSeek-V4-Flash | Sparse-MLA, multiple KV groups |
| GLM 5.1 / 5.2 | Dynamic Sparse Attention, multiple KV groups |
| MiniMax-M3 | Sparse attention + lightning indexer (mixed KV formats in one group) |

Sliding-window + full-attention hybrids need no special configuration — LMCache detects the model's KV cache groups at registration time.

**Mamba / GDN hybrids need one model-specific number.** vLLM forces a single unified block size `N` across all KV cache groups so an attention page is at least as large as a Mamba state page; the LMCache server's `--chunk-size` and vLLM's `--max-num-batched-tokens` both derive from it, and getting it wrong raises at engine startup. `N` is model-specific — **never assume a value**. vLLM prints it once during startup:

```
INFO ... interface.py:670] Setting attention block size to 784 tokens to
ensure that attention page size is >= mamba page size.
```

Launch vLLM far enough to emit that line (cheap settings, `--mamba-cache-mode align --enable-prefix-caching`), read `N`, then stop. The per-model recipe pages carry the rest.

**Object-group separation (`--separate-object-groups`, default on).** At registration LMCache buckets a hybrid model's layers into object groups — the unit it stores and retrieves as one object — one per distinct cross-chunk attention window. `--no-separate-object-groups` collapses every layer into a single full-attention object group (pre-0.5.1 behavior). Upstream documents the flag as transparent to correctness. A community report on [LMCache#3106](https://github.com/LMCache/LMCache/issues/3106) (2026-07-17, DeepSeek-V4-Pro on vLLM 0.25.1 + LMCache 0.5.1) uses `--no-separate-object-groups` to work around a `ValueError: Size mismatch` in the multi-group retrieve path; that report is unverified by this skill, but the flag and its default are confirmed in `lmcache/v1/multiprocess/config.py:48`.

Still open upstream: [LMCache#2845](https://github.com/LMCache/LMCache/issues/2845) (the original hybrid tracker) has not been closed even though the docs now claim support — a 2026-07-10 comment asks exactly that. [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261) (HybridOffloadPlanner) is also still open. Neither blocks the documented path; treat #2845 as a bookkeeping lag, and verify the specific model against its recipe page before production.

Note the in-process `LMCacheConnectorV1` did **not** get this — it does not declare `SupportsHMA` at vLLM v0.25.1, so hybrids remain broken there (#3106). That distinction is the main reason to choose MP mode for a hybrid model.

## Critical pitfalls

### 1. `--disable-hybrid-kv-cache-manager` is a symptom of the *fallback* connector, not a requirement

On lmcache 0.5.x this flag is **not** needed — the external package's `LMCacheMPConnector` declares `SupportsHMA`, so vLLM keeps the hybrid manager on.

You only see this error when vLLM falls back to its own repo-local copy of the connector (`LMCacheMPConnectorUpstream`), which still carries the old guard:

```
RuntimeError: LMCacheMPConnector only works without hybrid kv cache manager.
Please pass --disable-hybrid-kv-cache-manager when starting vllm
```

Source: `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:80` (verified at vLLM tag v0.25.1). **The fix is to make the external `lmcache` import succeed, not to add the flag** — run `scripts/verify-bundling.sh <tag>`. Adding the flag masks a broken install and costs hybrid-model support. On lmcache ≤ 0.4.x the flag genuinely is required.

### 2. vLLM's own prefix cache must be OFF

Always set `--no-enable-prefix-caching` on the vLLM side when using LMCacheMPConnector. LMCache handles prefix caching externally. Leaving vLLM's own prefix cache on creates double-counting and inconsistent hit reporting.

### 3. lmcache `ParallelStrategy` version hazard

vLLM `main` (post-2026-03) imports `ParallelStrategy` from `lmcache.integration.vllm.vllm_multi_process_adapter`. This class does **not** exist in lmcache 0.4.3 (verified against the v0.4.3 tag on 2026-04-26). It was added in 0.4.4.

| vLLM version | Required lmcache |
|---|---|
| v0.19.0, v0.19.1 | 0.4.0+ (works with bundled 0.4.3) |
| v0.20.0 – v0.22.x | **0.4.4+** — verify on the released image |
| v0.23.0 – v0.25.1 (current stable) | **0.5.x** (0.5.1 recommended) — 0.4.x works but forfeits hybrid-model support |
| main / nightly | **0.5.1+** |

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
- LMCache K8s Operator: [operator-v0.1.1 release](https://github.com/LMCache/LMCache/releases/tag/operator-v0.1.1) (CRD-based DaemonSet+Service+ConfigMap reconciler)
- Hybrid model tracker: [LMCache#2845](https://github.com/LMCache/LMCache/issues/2845) (open), [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261) (open), [LMCache#2879](https://github.com/LMCache/LMCache/pull/2879) (closed-unmerged)
- cache_salt fallback bug: [vLLM#40040](https://github.com/vllm-project/vllm/issues/40040) (open)

See `references/sources.md` for verification dates and the inspection ritual.

Last verified: 2026-07-21 (freshen pass — hybrid-model support inverted, LMCache 0.5.x + operator-v0.5.0 versions, HMA pitfall reframed. Runtime bundling table still only captured for `vllm/vllm-openai:v0.19.1`; run `scripts/verify-bundling.sh v0.25.1` before pinning the current pair).
