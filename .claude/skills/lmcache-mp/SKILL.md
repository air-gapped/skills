---
name: lmcache-mp
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: >-
  LMCache multiprocess (MP) mode: LMCache as its own pod or process that vLLM
  reaches over ZMQ (`LMCacheMPConnector`), one cache shared by several vLLM pods
  per node. Covers the DaemonSet+Deployment pattern (the LMCache Operator is deprecated), the L1
  CPU + L2 (NIXL, fs, mooncake, s3, Redis) cascade, the `lmcache/standalone`
  image, hybrid-attention models, and production gotchas. Use when LMCache runs
  as a separate server, daemon or daemonset, or for LMCacheMPConnector vs
  LMCacheConnectorV1. In-process vLLM CPU offload: `vllm-caching`; NIXL
  transport: `nvidia-nixl`; SGLang: `sglang-hicache`.
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
   → In-process `LMCacheConnectorV1` (`--kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'` + `LMCACHE_LOCAL_DISK` env vars). Still in vllm-caching skill. It fails on lmcache 0.5.7+ (`No module named 'lmcache.integration.vllm.vllm_v1_adapter'`, [vLLM#69358](https://github.com/vllm-project/vllm/issues/69358), open); MP mode is unaffected.

3. **Multiple vLLM pods on the same node should share a KV cache, OR you want to isolate cache CPU work from inference (no GIL contention), OR you want to scale cache CPU memory independently of GPU pods?**
   → **MP mode. This skill.**

   One node, one vLLM instance, and MP wanted only for isolation or hybrid-model support (lmcache 0.5.6+)? Skip the second container: `"lmcache.mp.autostart": true` plus `"lmcache.mp.autostart.server_args": "--l1-size-gb N --eviction-policy LRU"` in `kv_connector_extra_config` makes vLLM worker 0 start a localhost server as its child. Its lifetime is tied to vLLM: never count on a warm cache across vLLM restarts, and stop a leftover server yourself. Keep autostart off (the default) for the DaemonSet pattern, several vLLM instances, or multi-node TP/PP. `server_args` must not set `--host`, `--port` or `--http-host`; give each auto-started server on one host its own `--http-port`.

4. **Disaggregated prefill across nodes (separate prefill and decode pods, KV transferred between them)?**
   → NixlConnector or MooncakeConnector. See `vllm-caching` (and `nvidia-nixl` for transport-level tuning). MP can layer on top of these via MultiConnector.

Don't reach for MP mode just because it's newest — it adds operational surface (extra DaemonSet, ZMQ network path, two images to keep in sync, version-pin dance). The in-process LMCacheConnectorV1 still works fine for single-pod deployments.

## Version gates — check these FIRST

Current stable pair: **vLLM v0.34.0** (2026-11-16) + **LMCache v0.5.8** (2026-11-22). v0.34.0 pins `nixl == 1.5.2` and `lmcache >= 0.5.6`; `LMCacheMPConnector`/`SupportsHMA` are unchanged. **The default `vllm/vllm-openai:v0.34.0` image bundles lmcache 0.5.7.post1, below the 0.5.8 security floor: for `LMCacheMPConnector`, run `pip install lmcache==0.5.8` in the vLLM image (or build `FROM` it), or use `lmcache/vllm-openai:v0.5.8`.** Install into the image's own Python environment and re-run `scripts/verify-bundling.sh` on the result; keep the server image on the same version. **`-cu129` vLLM tags bundle `lmcache == 0.5.6` (v0.33.0 and v0.34.0; `0.4.4` on v0.31.0 and v0.32.0) and LMCache publishes no CUDA 12.9 build from 0.5.8**: use the default CUDA 13 tag. Do not install lmcache 0.5.7+ for the in-process `LMCacheConnectorV1` ([vLLM#69358](https://github.com/vllm-project/vllm/issues/69358)).

**vLLM v0.34.0 extensible KV cache and LMCache.** vLLM v0.34.0 turns extensible KV cache on by default. With lmcache **< 0.5.8** and `LMCacheMPConnector` it is switched off (the connector reports legacy CUDA IPC) and an unset `gpu_memory_utilization` resolves to 0.92; otherwise an unset value resolves to 1.0. With lmcache 0.5.8 on both sides the connector detects the extensible KV cache and exports it as file descriptors over `/dev/shm/lmcache_fd_<port>.sock`: keep `--ipc host` / the shared host `/dev/shm`, use a TCP server URL, and leave `lmcache.mp.use_vmm_api` unset unless you must override the detection. Set `--no-enable-extensible-kv-cache` or an explicit `--gpu-memory-utilization` to keep the pre-v0.34 sizing.

| Component | What you need | Notes |
|---|---|---|
| vLLM | **v0.19.0 or newer** for `LMCacheMPConnector` registered in `factory.py` | Pre-0.19 had only `LMCacheConnectorV1`. Both connectors coexist in 0.19+. Connector source path stable through v0.25.1. |
| vLLM | **v0.20.0+** for `cache_salt` propagation through MP | PR #39837 added per-user/per-tenant cache isolation. Repo-local fallback adapter has a known bug — see Pitfalls below. |
| vLLM | **v0.23.0+** for HMA-by-default | #41847 made `disable_hybrid_kv_cache_manager` tri-state; combined with LMCache 0.5.x's `SupportsHMA` declaration this is what unlocks hybrid models in MP mode. |
| LMCache | **0.4.0+** for the MP adapter file (`lmcache.integration.vllm.vllm_multi_process_adapter`) | Moved into LMCache repo on 2026-01-07 (PR #2360). Earlier versions had it in vLLM. |
| LMCache | **0.4.4+** for vLLM v0.20+/main | vLLM main imports `ParallelStrategy` symbol that doesn't exist in 0.4.3. Verified against tags v0.4.3 (no class) vs v0.4.4 (has class); still present at v0.5.1. |
| LMCache | **0.5.8** is the newest release; the default v0.34.0 image ships 0.5.7.post1 | 0.5.0 brought P2P KV transfer to MP mode (#3740/#3762), Device-DAX L1 overflow, asymmetric serde (FP16 key / FP8 value), and a wave of renames. 0.5.1 added L2→L1 warm-prefetch (#3827), `HiddenStateStore` (#3221), an AMD `hipFile` GDS-L1 backend (#3843), TurboQuant serde for L2, and configurable `disk_io_threads`. 0.5.7 dropped the in-process `vllm_v1_adapter`, negotiates the chunk size from the model's KV geometry and added HTTP API-key auth; 0.5.8 added request-transport API-key auth, per-LoRA cache identity, `--separate-object-groups` on by default, and shipped the NIXL L2 connector as the separate `lmcache-nixl` package. |
| LMCache | **0.5.x required** for hybrid-attention models | The `SupportsHMA`-declaring connector lives in `lmcache/integration/vllm/lmcache_mp_connector.py`. See the hybrid-model section. |
| LMCache | **0.5.8+ on both sides** — the server image AND the lmcache inside the vLLM image | Security floor. 0.3.9–0.5.5 unpickle data from the MP transport: one unauthenticated message to the ZMQ port runs code as the LMCache user (critical, CVE-2026-105192, fixed 0.5.6). 0.4.6–0.5.6 also unpickle in the MP `commit_store` path (critical, GHSA-qr43-hv93-6x7p, fixed 0.5.7). 0.4.7–0.5.7 let an unauthenticated frontend proxy reach any local UNIX socket (critical, GHSA-hhqh-8jpj-27rf, fixed 0.5.8). 0.4.5–0.5.7 share KV cache across LoRA adapters and the base model (medium, GHSA-jg4p-wprm-8hph, fixed 0.5.8: clear L2 tiers written by a multi-adapter deployment before upgrading). Three more high/medium advisories (legacy `LMCacheServer`, unauthenticated KV overwrite, RESP client) are fixed in 0.5.7. The wire format changed in 0.5.6 and 0.5.7 (legacy pickle descriptors rejected): upgrade the server and every vLLM-side lmcache together, never one side alone. |

**Renames in 0.5.0 that break old greps and docs:** `MPCacheEngine` → `MPCacheServer`, `GPUKVFormat` → `EngineKVFormat` (`gpu_kv_*` → `engine_kv_*`), `GPUTransferModule` → `LMCacheDrivenTransferModule`, `NonGPUTransferModule` → `EngineDrivenTransferModule`. The CLI was also refactored into multi-subcommand form (#3678).

### Image bundling (what's actually in the container)

Contents of `vllm/vllm-openai:v0.34.0` (sleep-overridden, exec'd in):

| Package | Version in v0.34.0 image | Import works? | Notes |
|---|---|---|---|
| `vllm` | 0.34.0 | OK | — |
| `lmcache` | 0.5.7.post1 | OK | **Below the 0.5.8 security floor**; `ParallelStrategy` present; upgrade it for MP mode |
| `nixl` | 1.5.2 | OK | — |
| `mooncake-transfer-engine-cuda13` | 0.3.14 | OK as `import mooncake` | **Distribution carries a CUDA suffix; the module does not.** Querying `mooncake-transfer-engine` reports NOT INSTALLED for a package that is present |
| `lmcache` CLI | — | `/usr/local/bin/lmcache` | Server entrypoint ready out of the box |

All four KV-offload connector classes (`OffloadingConnector`, `LMCacheConnectorV1`, `LMCacheMPConnector`, `NixlConnector`) load through the factory's own thunk (18 connectors are registered); vLLM logs `Using external LMCacheMPConnector from lmcache.integration.vllm.lmcache_mp_connector`. `LMCacheConnectorV1` loads here but breaks at runtime on lmcache 0.5.7+ (see above).

Earlier floor: `v0.19.1` shipped vllm 0.19.1 / lmcache 0.4.3 / nixl 0.9.0 / mooncake 0.3.10.post1 — below the security floor, and its lmcache predates `ParallelStrategy`.

But: **always verify the tag you actually deploy** with `scripts/verify-bundling.sh <tag>`. It builds a sleep-overridden container, runs the import test, prints the version table. ~30 seconds (after pull).

## Quick start (Docker, single node)

Two containers. The LMCache server is a separate process; vLLM connects over ZMQ to localhost:6555.

```bash
# Terminal 1 — LMCache server
docker run --runtime nvidia --gpus all \
    --network host --ipc host \
    lmcache/standalone:v0.5.8 \
    /opt/venv/bin/lmcache server \
    --l1-size-gb 60 --eviction-policy LRU --max-workers 4 --port 6555

# Terminal 2 — vLLM (connects to LMCache via ZMQ)
docker run --runtime nvidia --gpus all \
    --network host --ipc host \
    lmcache/vllm-openai:v0.5.8 \
    Qwen/Qwen3-14B \
    --no-enable-prefix-caching \
    --kv-transfer-config '{"kv_connector":"LMCacheMPConnector",
                           "kv_role":"kv_both",
                           "kv_connector_extra_config":{"lmcache.mp.port":6555}}'
```

Docker Hub carries `v0.5.8` and `latest` for both images (`lmcache/standalone` also `v0.5.8-cu130`, `lmcache/vllm-openai` also `v0.5.8-lightweight`). Both run as uid 1000 (`lmcache`) since 0.5.7: a host path mounted for an L2 adapter must be writable by that uid.

Required Docker flags:

- `--network host` — vLLM container needs to reach LMCache on localhost:6555.
- `--ipc host` — CUDA IPC shared-memory transfers require shared `/dev/shm`.
- `--runtime nvidia --gpus all` — both containers see GPUs (the LMCache server uses GPU-side IPC even though it doesn't run inference).

Flags on the **vLLM side** that operators forget:

- `--no-enable-prefix-caching` — vLLM's own prefix cache is **OFF**. LMCache MP handles prefix caching externally.
- No HMA flag. On lmcache 0.5.x, `--disable-hybrid-kv-cache-manager` is neither required nor wanted (see Pitfall 1); on lmcache ≤ 0.4.x it is required.

## Kubernetes (the production shape)

The canonical pattern is **DaemonSet (LMCache) + Deployment (vLLM)**: one LMCache server per node serves multiple vLLM pods on that node.

**Do not build new deployments on the LMCache Kubernetes Operator.** From LMCache v0.5.8 the docs mark it deprecated and unmaintained, with removal from the repo expected in 2027Q1; `operator-v*` releases (newest `operator-v0.5.5`, 2026-09-15) get no fixes. Use the hand-written DaemonSet + Deployment in `references/deployment.md`. An existing operator install keeps working at its pinned release: plan the move to manual manifests. What it generated (reference when migrating off it): an `LMCacheEngine` custom resource reconciled into DaemonSet + Service + ConfigMap, a mutating webhook that injects the `LMCacheEngine` connection into vLLM pods (#3822), a `hostNetwork` CRD field (#3849) and optional privileged mode on the engine DaemonSet (#3943).

Example manifests live in the LMCache repo at `examples/multi_process/`:
- `lmcache-daemonset.yaml` — LMCache server, one per node
- `vllm-deployment.yaml` — vLLM pods that connect to the node-local LMCache via `status.hostIP`

Architecture details that bite if missed:

- **`hostNetwork: true` on the DaemonSet** — vLLM pods discover the LMCache server via the node's `status.hostIP`. Without `hostNetwork`, the server's listening port isn't reachable from sibling pods.
- **The request transport is unauthenticated unless you enable API keys — never bind `--host 0.0.0.0` without them.** Bind the node IP (`--host $(HOST_IP)` from `status.hostIP`) and block the port from off-node sources at the host firewall; NetworkPolicy usually ignores `hostNetwork` pods. Binding `--host 127.0.0.1` works only if the vLLM pods also run `hostNetwork: true` — a pod's own loopback is not the node's, and upstream's localhost example (v0.5.8) omits this, so its vLLM pods cannot connect.
- **API keys (0.5.8+, opt-in).** Start the server with `--api-key-file <path>` (repeat the flag to overlap old and new keys) and give each vLLM process `LMCACHE_API_KEY_FILE` (or `LMCACHE_API_KEY`). It covers the ZMQ and gRPC request transports and the HTTP API; `/` and `/healthcheck` stay public. ZMQ servers and clients that predate 0.5.8 cannot talk to an authenticating server, so upgrade everything before enabling keys. The key travels in clear text: it is access control on a trusted network, not encryption. Do not run the optional frontend dashboard (its reverse proxy) below 0.5.8; on 0.5.8 restrict socket targets with `--uds-allowlist` and set a frontend API key.
- **Both containers mount `/dev/shm` from the host** — required for CUDA IPC.
- **GPUs are NOT requested in the DaemonSet** — the LMCache server doesn't run inference. The NVIDIA container runtime gives it just enough GPU access for IPC-based transfers. Requesting GPUs there would steal them from vLLM pods.
- **Multiple vLLM pods on the same node automatically share** the same LMCache DaemonSet instance — that's the whole point.
- **LMCache pods on non-GPU nodes will crash with CUDA init errors.** Constrain the DaemonSet to GPU nodes via nodeSelector.

For the full deployment recipe (sample YAMLs, prereqs, monitoring integration, cleanup), see `references/deployment.md`.

For the L1+L2 storage architecture (NIXL adapters, fs, mooncake_store, s3, eviction policies), see `references/l2-storage.md`.

## Hybrid model status — supported as of LMCache 0.5.x

**This inverted in the 0.5 line. MP mode now supports hybrid-attention models officially**, and the old "don't recommend MP for hybrids" guidance is obsolete. `LMCacheMPConnector` declares vLLM's `SupportsHMA` interface (`lmcache/integration/vllm/lmcache_mp_connector.py`), so vLLM keeps its hybrid KV cache manager **enabled** and exposes multiple KV cache groups — you do not pass `--disable-hybrid-kv-cache-manager`, and you do not need any HMA-related flag.

Upstream ships per-model recipes (`docs/source/mp/hybrid_models.rst`, published at https://docs.lmcache.ai/mp/hybrid_models.html) for:

| Model | Attention layout |
|---|---|
| Gemma 2 / 3 / 4, gpt-oss | Interleaved sliding-window + full |
| Qwen3.5 / 3.6 / 3.8 series, Qwen3-Next and other GDN hybrids | Mamba / Gated-DeltaNet + full |
| Qwen3.8-Flash-Next (0.5.6+) | GDN + QSA sparse full; per-request scratch ring is recomputed, not cached |
| Kimi-Linear, Kimi K3 | KDA linear attention + MLA full |
| DeepSeek-V4-Flash | Sparse-MLA, multiple KV groups |
| DeepSeek-V4.1-Flash (0.5.6+) | Sparse-MLA + per-layer sliding window, 9 KV groups; scratch ring recomputed |
| GLM 5.1 / 5.2 | Dynamic Sparse Attention, multiple KV groups |
| GLM-5.3 (0.5.6+) | Dynamic Sparse Attention, single KV group; `--chunk-size` a multiple of 64, well below typical prompt length |
| GLM-5.3-Flash (0.5.8) | KDA linear attention + NoPE sparse MLA; unified block size 1152 |
| MiniMax-M3 | Sparse attention + lightning indexer (mixed KV formats in one group) |

Sliding-window + full-attention hybrids need no special configuration — LMCache detects the model's KV cache groups at registration time.

**Mamba / GDN hybrids depend on one model-specific number.** vLLM forces a single unified block size `N` across all KV cache groups so an attention page is at least as large as a Mamba state page. `N` is model-specific — **never assume a value**. On lmcache **0.5.7+** nothing has to be derived by hand: `--chunk-size` is a minimum and the connector negotiates the smallest multiple of `N` at least that large (default 256 with `N = 784` resolves to 784). On lmcache ≤ 0.5.6 the server's `--chunk-size` and vLLM's `--max-num-batched-tokens` both derive from `N`, and a wrong value raises at engine startup. vLLM prints `N` once during startup:

```
INFO ... interface.py:670] Setting attention block size to 784 tokens to
ensure that attention page size is >= mamba page size.
```

Launch vLLM far enough to emit that line (cheap settings, `--mamba-cache-mode align --enable-prefix-caching`), read `N`, then stop. On lmcache 0.5.3–0.5.7 start the LMCache server with `--separate-object-groups` as well (see below). The per-model recipe pages carry the rest.

**Object-group separation (`--separate-object-groups`, default ON through v0.5.2, OFF in v0.5.3–v0.5.7, ON again from v0.5.8).** At registration LMCache buckets a hybrid model's layers into object groups — the unit it stores and retrieves as one object — one per distinct cross-chunk attention window. `--no-separate-object-groups` collapses every layer into a single full-attention object group (pre-0.5.1 behavior). `--separate-object-groups` is **required for Mamba / linear-attention hybrids** (GDN, KDA) and a no-op for non-hybrid models; the recipes for those models, DeepSeek-V4.1-Flash and GLM-5.3 all pass it. **The default flipped twice**: on v0.5.3–v0.5.7 the single full-attention group is what you get unless you pass `--separate-object-groups`; from v0.5.8 separation is on and `--no-separate-object-groups` is the opt-out (never pass it for Mamba / linear-attention models). A config or cache carried across those versions silently changes grouping, so set the flag explicitly on every upgrade across v0.5.3 and v0.5.8. A community report on [LMCache#3106](https://github.com/LMCache/LMCache/issues/3106) (2026-07-17, DeepSeek-V4-Pro on vLLM 0.25.1 + LMCache 0.5.1) uses `--no-separate-object-groups` to work around a `ValueError: Size mismatch` in the multi-group retrieve path; on v0.5.8 the flag's default is `True`, so pass `--no-separate-object-groups` only if that `ValueError` appears.

[LMCache#2845](https://github.com/LMCache/LMCache/issues/2845) (the original hybrid tracker) was closed by the stale bot with no fix or maintainer answer, so its state says nothing either way; [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261) (HybridOffloadPlanner) is still open. Neither blocks the documented path: the recipe pages are the authority, and verify the specific model against its recipe before production.

Note the in-process `LMCacheConnectorV1` did **not** get this — it does not declare `SupportsHMA` at vLLM v0.25.1, so hybrids remain broken there (#3106). That distinction is the main reason to choose MP mode for a hybrid model.

## Critical pitfalls

### 1. `--disable-hybrid-kv-cache-manager` is a symptom of the *fallback* connector, not a requirement

On lmcache 0.5.x this flag is **not** needed — the external package's `LMCacheMPConnector` declares `SupportsHMA`, so vLLM keeps the hybrid manager on.

You only see this error when vLLM falls back to its own repo-local copy of the connector (`LMCacheMPConnectorUpstream`), which still carries the old guard:

```
RuntimeError: LMCacheMPConnector only works without hybrid kv cache manager.
Please pass --disable-hybrid-kv-cache-manager when starting vllm
```

Source: `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py` in vLLM. **The fix is to make the external `lmcache` import succeed, not to add the flag** — run `scripts/verify-bundling.sh <tag>`. Adding the flag masks a broken install and costs hybrid-model support. On lmcache ≤ 0.4.x the flag genuinely is required.

### 2. vLLM's own prefix cache must be OFF

Always set `--no-enable-prefix-caching` on the vLLM side when using LMCacheMPConnector. LMCache handles prefix caching externally. Leaving vLLM's own prefix cache on creates double-counting and inconsistent hit reporting.

### 3. lmcache `ParallelStrategy` version hazard

vLLM `main` (post-2026-03) imports `ParallelStrategy` from `lmcache.integration.vllm.vllm_multi_process_adapter`. This class does **not** exist in lmcache 0.4.3 (verified against the v0.4.3 tag on 2026-04-26). It was added in 0.4.4.

| vLLM version | Required lmcache |
|---|---|
| v0.19.0, v0.19.1 | 0.4.0+ (works with bundled 0.4.3) |
| v0.20.0 – v0.22.x | **0.4.4+** — verify on the released image |
| v0.23.0 – v0.25.1 | **0.5.x** (0.5.1+) — 0.4.x works but forfeits hybrid-model support |
| v0.29.0 | ships **0.5.4**, `ParallelStrategy` present — below the security floor |
| v0.32.0 | ships **0.5.6** (default CUDA 13 tag); `-cu129` tags ship **0.4.4** |
| v0.34.0 | ships **0.5.7.post1** (default CUDA 13 tag), below the 0.5.8 floor; `-cu129` tags ship **0.5.6**; requires `lmcache >= 0.5.6` |
| main / nightly | **0.5.8+** |

Tags not listed (v0.26.x – v0.28.x, v0.30.x, v0.31.x, v0.33.x) are unknown, not known-bad: run the check on the exact tag first.

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

`--eviction-policy` has no default; the server refuses to start without it. The pressure defaults (`--eviction-trigger-watermark 0.8 --eviction-ratio 0.2`) are fine for bursty traffic. Under sustained pressure, frequent eviction cycles can stutter cache hits. Lower the watermark (0.7) or raise the ratio (0.3) if logs show eviction every few seconds.

On lmcache 0.5.6+, choose `--eviction-policy ARC` when reused prefixes (system prompts, shared RAG documents, agent/tool prefixes) share L1 with a stream of one-time prefixes or batch scans: LRU flushes the hot set, while ARC keeps it. ARC ignores `cache_salt`, so use `IsolatedLRU` where per-tenant quotas are needed. Each L2 adapter can choose it separately (`"eviction":{"eviction_policy":"ARC"}`).

### 7. CUDA IPC requirements

`--ipc host` (Docker) or mounting `/dev/shm` from the host (K8s) is mandatory. Without it, CUDA IPC shared-memory transfers between vLLM and LMCache pods fail silently or at startup with cryptic errors. The DaemonSet + Deployment example YAMLs show the right `volumes`/`volumeMounts` pattern.

### 8. Only prompt chunks are stored (lmcache 0.5.6+)

On 0.5.6+ the connector stores chunks only up to the request's prompt length: `lmcache.mp.save_decode_cache` (vLLM-side `kv_connector_extra_config`) defaults to `false`. Size L1 on unique prompt-prefix tokens; output length does not consume it. On 0.5.8, `lmcache.mp.save_unfull_chunk` (default `false`) also stores the prompt's trailing partial chunk; the connector refuses it with speculative decoding or with models that keep per-request ring state. Set `"lmcache.mp.save_decode_cache": true` only when a resumable or streaming request feeds its own generated tokens back as a growing prompt. The in-process connector's `save_decode_cache` YAML/env setting does not apply to MP. On ≤ 0.5.5 every complete chunk of generated tokens was stored too, so a fixed-prompt workload keeps writing new chunks after warm-up: size L1 for prompt + output there.

## Validating that MP is helping

The validation method is the same as for native CPU offload — `vllm bench serve --dataset-name prefix_repetition`, then diff `vllm:external_prefix_cache_*` Prometheus counters before and after. See `vllm-caching` for the methodology and right-sizing math (`unique_prefix_budget_tokens ≈ l1_size_gib × 1024 × 1024 / kv_bytes_per_token`).

Additional MP-specific signals:

- **LMCache server `GET /healthcheck`** (HTTP server variant, port 8080 default; no `/api/` prefix; stays unauthenticated when API keys are on) returns `{"status":"healthy"}` when the engine is initialized, 503 before. Wire this into K8s liveness/readiness probes. On 0.5.6+ the HTTP server binds `127.0.0.1` by default (`--http-host`; the admin API is unauthenticated), so on the `hostNetwork` DaemonSet set `httpGet.host: 127.0.0.1` in the probe rather than opening `--http-host`.
- **LMCache `GET /status`** dumps detailed internal state (L1 cache, L2 adapters, controllers, registered GPUs, sessions). Use during incident triage.
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

- LMCache repo: https://github.com/LMCache/LMCache
- LMCache MP docs: `docs/source/mp/` in the repo (`index.rst`, `deployment.rst`, `configuration.rst`, `http_api.rst`, `hybrid_models.rst`, `operator.rst`, `request_transport.rst`, `tracing_and_debugging.rst`, and the `l2_storage/` and `observability/` directories)
- vLLM connector source: `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py`
- Example K8s manifests: `LMCache/LMCache/examples/multi_process/`
- LMCache K8s Operator (deprecated from v0.5.8): [operator-v0.5.5 release](https://github.com/LMCache/LMCache/releases/tag/operator-v0.5.5)
- Hybrid model tracker: [LMCache#2845](https://github.com/LMCache/LMCache/issues/2845) (stale-closed, no fix), [vLLM#38261](https://github.com/vllm-project/vllm/pull/38261) (open), [LMCache#2879](https://github.com/LMCache/LMCache/pull/2879) (closed-unmerged)
- cache_salt fallback bug: [vLLM#40040](https://github.com/vllm-project/vllm/issues/40040) (autoclosed 2026-08-17 for inactivity, **not fixed** — fix PR #40041 still open)

See `references/sources.md` for verification dates and the inspection ritual.
