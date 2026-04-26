# LMCache MP — troubleshooting and known bugs

## Symptom → diagnosis matrix

| Symptom | Most likely cause |
|---|---|
| `RuntimeError: LMCacheMPConnector only works without hybrid kv cache manager` at startup | Missing `--disable-hybrid-kv-cache-manager` on vLLM |
| `ImportError: cannot import name 'ParallelStrategy'` from lmcache adapter | vLLM main paired with bundled lmcache 0.4.3 — upgrade to 0.4.4+ |
| `TypeError: ... got an unexpected keyword argument 'cache_salt'` | Falling through to repo-local fallback adapter (vLLM #40040). Make sure `import lmcache.integration.vllm.vllm_multi_process_adapter` succeeds. |
| `LMCache INFO: Registering kv caches!` never logs on vLLM side | vLLM can't reach the LMCache server — wrong host/port, or hostNetwork misconfig, or DaemonSet not on this node |
| `CPU_to_GPU_total_bytes=0` consistently in vLLM logs | LMCache is reachable but never serving hits — wrong prefix-cache settings, low hit rate workload, or L1 too small |
| Eviction stutter every few seconds in LMCache logs | L1 sized too small relative to working set — increase `--l1-size-gb`, lower `--eviction-trigger-watermark`, or raise `--eviction-ratio` |
| Cryptic CUDA errors at startup | `/dev/shm` not host-mounted on both pods, or `--ipc host` missing in Docker |
| Hybrid model garbled output / 0% prefix hit rate | Hybrid models not yet supported in MP mode (LMCache#2845). Use native offload instead. |
| Multiple vLLM pods on the same node, only one sees the cache | DaemonSet not on the same node, or `hostNetwork` missing, or vLLM pods using `Pod IP` instead of `status.hostIP` |

## Open bugs and version hazards (2026-04-26)

### vLLM #40040 — fallback adapter rejects cache_salt

**State**: open. **Affects**: vLLM main with `--kv-transfer-config` selecting `LMCacheMPConnector`.

`lmcache_mp_connector.py` falls back to a **repo-local** adapter (`vllm/distributed/kv_transfer/kv_connector/v1/lmcache_integration/multi_process_adapter.py`) when the external `lmcache.integration.vllm.vllm_multi_process_adapter` import fails. PR #39837 added `cache_salt`/`cache_salts` keyword args at the call sites but the fallback still has the old signature → `TypeError` at load.

**Avoidance**: Make sure the external `lmcache` package import succeeds (run `scripts/verify-bundling.sh` against your image). Don't deploy a pinned vLLM that needs args the bundled lmcache doesn't have.

### LMCache #2845 — hybrid models not supported

**State**: open, "WIP". **Affects**: any model with sliding window + full attention (Gemma4) or attention + Mamba (Qwen3.5).

Open PRs trying to fix:
- vLLM #38261 — HybridOffloadPlanner + MultiConnector hybrid awareness + mamba alignment
- LMCache #2879 — garbled output fix on hybrid models

Both still open as of 2026-04-26. A community patch in #2845 works for Qwen3.5-27B specifically and is not production-ready.

**Avoidance**: For hybrid-model production today, use vLLM's native CPU offload (`vllm-caching` skill) — also broken on hybrid models, but with the same known workaround (`--disable-hybrid-kv-cache-manager` + lower `--max-model-len`). Or wait for the vLLM `[kv_offload+HMA][N/N]` series to complete.

### LMCache #2942 — LocalCPUBackend deadlock with `use_hot=False`

**State**: open. Affects: in-process `LMCacheConnectorV1` (not strictly MP), but documented here because operators often switch back and forth.

`LocalCPUBackend.allocate()` deadlocks when `use_hot=False` and the staging buffer fills. Reproduced 2026-04-23 even with `use_hot=True` on Llama-3.2-1B + ShareGPT.

**Avoidance**: Always set `LMCACHE_LOCAL_CPU=True` (default). Skip `LMCACHE_LOCAL_DISK` for now.

### LMCache #2502 — LocalDiskBackend benchmark crashes vLLM

**State**: open. Affects: in-process V1 with disk tier.

**Avoidance**: Skip the disk tier on production paths. In MP mode, use `nixl_store_dynamic` or `fs` adapter instead.

## Version compatibility matrix

Verified 2026-04-26 against tags v0.4.3 / v0.4.4 of LMCache and v0.19.1 / v0.20.0 / main of vLLM.

| vLLM version | Required lmcache | Notes |
|---|---|---|
| v0.19.0 | 0.4.0+ | Bundled image ships compatible version |
| v0.19.1 | 0.4.0+ | Image ships 0.4.3, all imports clean |
| v0.20.0 | Verify on the released image | `cache_salt` propagation added |
| main / nightly | **0.4.4+** | `ParallelStrategy` import requirement |

To verify a specific image, use `scripts/verify-bundling.sh <tag>`.

## Prometheus metrics for triage

LMCache server exposes Prometheus on port 9090 (override with `--prometheus-port`). Useful counters:

- `lmcache_l1_cache_hits_total` / `lmcache_l1_cache_misses_total` — overall L1 hit rate
- `lmcache_l2_store_total_bytes` / `lmcache_l2_load_total_bytes` — L2 throughput by adapter
- `lmcache_l1_evictions_total` — eviction frequency
- `lmcache_registered_gpus` — current registered vLLM workers (should match TP × num-pods)

vLLM-side counters (port `--port` /metrics):

- `vllm:external_prefix_cache_hits_total` / `vllm:external_prefix_cache_queries_total` — vLLM's view of LMCache hit rate
- `vllm:cache_config_info` — total bytes vLLM allocated; useful sanity check

If `vllm:external_prefix_cache_hits_total` increments but `lmcache_l1_cache_hits_total` doesn't, you've got a metric-naming or scrape-target mismatch.

## Diagnostics commands

```bash
# Status of the LMCache HTTP server (if using `lmcache server` not `python3 -m`)
curl http://<lmcache-host>:8080/api/healthcheck
curl http://<lmcache-host>:8080/api/status   # detailed internals

# Force-clear all KV cache in L1 (CPU)
curl -X POST http://<lmcache-host>:8080/api/clear-cache

# Verify vLLM-side connector registration
docker exec <vllm-pod> python3 -c "
from vllm.distributed.kv_transfer.kv_connector.factory import KVConnectorFactory
print(sorted(KVConnectorFactory._registry.keys()))"

# Verify lmcache and adapter classes import cleanly
docker exec <vllm-pod> python3 -c "
import lmcache; print('lmcache', lmcache.__version__)
from lmcache.integration.vllm.vllm_multi_process_adapter import (
    LMCacheMPSchedulerAdapter, LMCacheMPWorkerAdapter, LoadStoreOp)
print('MP adapter classes OK')"
```

## Logs to grep for

LMCache server side (search the DaemonSet pod's logs):

```
LMCache INFO: LMCache cache server is running...           # successful startup
LMCache INFO: Registered KV cache for GPU ID <pid>         # vLLM successfully registered
LMCache DEBUG: Submitted store task ...                    # L2 activity (with DEBUG level)
LMCache DEBUG: L2 store task N completed ...
LMCache ERROR: ...                                         # any error during cache ops
```

vLLM side:

```
LMCache INFO: Registering kv caches!                       # successful connection
KV Transfer metrics: GPU_to_CPU_total_bytes=N ...          # bidirectional transfer summary
```
