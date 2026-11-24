# Sources and verification log

Parked: 2026-11-24 — kept and published, not freshened on schedule: no known user, and vLLM's native KV offload covers the single-node case. Freshen only when someone reports using it, or a new LMCache advisory moves the security floor the skill states. Review: 2027-02-24 — retire (`git mv` to `removed/`, pointer left in `vllm-caching`) unless a user has appeared.

Freshened: 2026-11-24 — every row probed against vLLM v0.34.0 (2026-11-16) and LMCache v0.5.8 (2026-11-22). LMCache 0.5.8 is the security floor for MP mode (GHSA-hhqh-8jpj-27rf, GHSA-jg4p-wprm-8hph, GHSA-qr43-hv93-6x7p); the vLLM v0.34.0 image bundles lmcache 0.5.7.post1, below it.

Freshened: 2026-10-27 — every row probed. LMCache v0.5.6 sets a security floor for MP mode (CVE-2026-105192) and moves the HTTP admin bind to loopback; the current pair was vLLM v0.32.0, whose `-cu129` images still shipped lmcache 0.4.4.

This skill was authored against live source code, image inspection, and live GitHub issue state. Re-run probes when re-verifying.

## Last verified

**2026-11-24** (freshen pass). Prior passes: 2026-10-27, 2026-09-22, 2026-09-15, 2026-07-21, 2026-05-28, 2026-04-26 (original authoring).

**A default flipped twice under this skill.** `--separate-object-groups` shipped `True` through v0.5.2, `False` in v0.5.3–v0.5.7 and `True` again from **v0.5.8** (#6041). Read at tags v0.5.6, v0.5.7, v0.5.7.post1 and v0.5.8 in `lmcache/v1/multiprocess/config.py`; the v0.5.8 release notes word it as "shared-object grouping by default" and `docs/source/mp/configuration.rst` agrees with the code.

### Per-source verification table

| Source | URL | Last verified | Notes |
|---|---|---|---|
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-11-24 | **v0.34.0 (2026-11-16)** isLatest. `requirements/kv_connectors.txt` at v0.34.0: `lmcache >= 0.5.6`, `nixl == 1.5.2`, `mooncake-transfer-engine >= 0.3.14` (`>= 0.3.9` lmcache floor at every tag through v0.32.0). `requirements/kv_connectors_cu12.txt` (CUDA 12 / `-cu129` builds): `lmcache == 0.4.4` at v0.32.0, `lmcache == 0.5.6` at v0.33.0 and v0.34.0, `--find-links` to the LMCache v0.5.6-cu129 release assets. Container run of `vllm/vllm-openai:v0.34.0` through `scripts/verify-bundling.sh`: vllm 0.34.0, lmcache **0.5.7.post1**, nixl 1.5.2, mooncake-transfer-engine-cuda13 0.3.14; MP adapter classes and `ParallelStrategy` OK, 18 connectors registered, exit 0. **#56492** (extensible KV cache on by default, merged 2026-11-02, ancestor of v0.34.0): `VllmConfig._resolve_extensible_kv_cache` turns it off when `KVConnector` reports `KVCacheAccess.LEGACY_IPC`; `KVConnectorFactory.kv_cache_access` forces LEGACY_IPC for the stock `LMCacheMPConnector` when the lmcache package's connector does not override the classmethod (**#66605**, in v0.34.0); unset `gpu_memory_utilization` resolves to 0.92, or 1.0 with extensible KV cache on (`vllm/config/cache.py`). **vLLM#69358** (OPEN): lmcache >= 0.5.7 lacks `lmcache.integration.vllm.vllm_v1_adapter`, so the in-process `LMCacheConnectorV1` fails; the MP connector path does not import it. |
| LMCache releases | https://github.com/LMCache/LMCache/releases | 2026-11-24 | **v0.5.8 (2026-11-22)** isLatest (tag commit 651617ef), via v0.5.7 (2026-11-05) and v0.5.7.post1 (2026-11-12; PyTorch 2.14 ABI rebuild, CUDA 12.9 wheels and images removed). Docker Hub: `lmcache/standalone` carries `v0.5.8`, `v0.5.8-cu130`, `latest` (2026-11-22); `lmcache/vllm-openai` carries `v0.5.8`, `v0.5.8-lightweight`, `latest`; no `-cu129` tag after v0.5.7. v0.5.7: `vllm_v1_adapter` removed (in-process connector gone), chunk size negotiated from KV geometry (#5222), HTTP API-key auth (#5756, #5779), pickle tensor codec replaced (#5699, #5903), non-root images (uid 1000, #5685). v0.5.8: API-key auth on ZMQ/gRPC request transports (`docs/source/mp/request_transport.rst`), per-LoRA cache identity (#5713 via the `lmcache.tag.lora` tag), `--separate-object-groups` default True (#6041), `lmcache-nixl` package (#5400), loopback-only coordinator bind, UDS-proxy restriction (#6497), GLM-5.3-Flash recipe, `lmcache.mp.save_unfull_chunk` (#5886), `lmcache.mp.use_vmm_api` auto-detect (#6499) and `kv_cache_access` (#6487). 0.5.0 renames: `MPCacheEngine`→`MPCacheServer`, `GPUKVFormat`→`EngineKVFormat`, `GPUTransferModule`→`LMCacheDrivenTransferModule`. Not applied: the native `hf3fs` L2 adapter (#5131) compiles only with `BUILD_HF3FS=1`, which nothing under `docker/`, `.github/` or `setup.py` sets at v0.5.8; WQS is a docs page for a vendor-built `wqs_store` adapter that is not a registered adapter type in the tree. |
| **LMCache hybrid-model support** | https://docs.lmcache.ai/mp/hybrid_models.html (repo `docs/source/mp/hybrid_models.rst`) | 2026-11-24 | **Inverts the skill's original "hybrids unsupported" claim.** `LMCacheMPConnector(KVConnectorBase_V1, SupportsHMA)` in `lmcache/integration/vllm/lmcache_mp_connector.py` at v0.5.1, v0.5.6, v0.5.7 and v0.5.8, so vLLM keeps HMA enabled and no flag is needed. Recipe table at v0.5.8: Gemma 3/4, gpt-oss, Qwen3.5/3.6/3.8 series, Qwen3.8-Flash-Next, Kimi-Linear, Kimi K3, DeepSeek-V4-Flash, DeepSeek-V4.1-Flash, GLM 5.1/5.2, GLM-5.3, GLM-5.3-Flash (new in 0.5.8, N = 1152), MiniMax-M3. v0.5.8 docs: `--chunk-size` is a minimum and the connector negotiates the smallest multiple of the unified block size `N` (`chunk_size_negotiation`, #5222, first in v0.5.7; `N` = 784 for Qwen3.6-27B and Qwen3.8-27B, 544 for Qwen3.5-0.8B, 944 for Kimi-Linear, 768 for Kimi K3); the Qwen3.5 recipe launches with `--chunk-size 784`; "Do not pass `--no-separate-object-groups`" for Mamba/GDN models. |
| `--separate-object-groups` | `lmcache/v1/multiprocess/config.py` (dataclass and argparse) at tags v0.5.6, v0.5.7, v0.5.7.post1, v0.5.8; https://github.com/LMCache/LMCache/pull/6041 | 2026-11-24 | **Default `True` at v0.5.8** (`BooleanOptionalAction`, `default=True`; #6041, "Enable --separate-object-groups as default"). `False` at v0.5.6, v0.5.7 and v0.5.7.post1; `True` at v0.5.1 and v0.5.2, `False` from v0.5.3. `docs/source/mp/configuration.rst` at v0.5.8: on by default, keep it enabled for Mamba/linear-attention hybrids, no difference for non-hybrids. |
| Prompt-only store default (`lmcache.mp.save_decode_cache`) | https://github.com/LMCache/LMCache/pull/5239 ; `lmcache/integration/vllm/lmcache_mp_connector.py` and `docs/source/mp/configuration.rst` at tags v0.5.6 and v0.5.8 | 2026-11-24 | #5239 (merged 2026-10-05, fixes #5230, first in v0.5.6) caps MP stores at `num_prompt_tokens` unless the key is `true`; `get_from_extra_config("lmcache.mp.save_decode_cache", False)` and a boolean check at v0.5.8. v0.5.8 adds `lmcache.mp.save_unfull_chunk` (default `False`, #5886): stores the prompt's trailing partial chunk; the constructor raises `ValueError` with speculative decoding or per-request ring-state groups. At v0.5.5 the store bound has no prompt cap and the key does not exist. |
| MP server auto-start (`lmcache.mp.autostart`) | https://github.com/LMCache/LMCache/pull/3476 ; `lmcache/integration/vllm/mp_server_launcher.py` and `docs/source/mp/configuration.rst` at tag v0.5.8 | 2026-11-24 | #3476 (merged 2026-09-18, fixes #3065, first in v0.5.6). Unchanged at v0.5.8: opt-in, localhost/127.0.0.1 only (`_LOCAL_HOSTS`), IPv6 raises `ValueError`, `lmcache.mp.autostart.wait_timeout` key present, multiple servers disable it. PR validation (vLLM 0.28.0 SIGTERM shutdown killed the child) not re-run; docs guarantee neither survival nor cleanup. |
| ARC eviction policy | https://github.com/LMCache/LMCache/pull/4994 ; https://github.com/LMCache/LMCache/pull/5348 ; `lmcache/v1/distributed/config.py` at tag v0.5.8 | 2026-11-24 | #4994 (merged 2026-09-22) adds ARC for L1 and per-L2-adapter eviction; #5348 (merged 2026-09-29, fixes #5347) stops new keys skipping T1. Both first in v0.5.6. At v0.5.8 `--eviction-policy` has choices `LRU`, `ARC`, `IsolatedLRU`, `noop` and no default (`ValueError: An eviction policy is required for each L1`); watermark 0.8 / ratio 0.2 defaults unchanged. `IsolatedLRU` keeps one LRU list per `cache_salt`. |
| LMCache K8s Operator | https://github.com/LMCache/LMCache/releases/tag/operator-v0.5.5 | 2026-11-24 | **operator-v0.5.5 (2026-09-15)** is still the newest `operator-v*` release and tag (15 operator tags; none after 09-15); ships `install.yaml`; empty release notes. 0.5-line features from the core 0.5.1 notes: webhook auto-injecting the `LMCacheEngine` connection into vLLM pods (#3822), `hostNetwork` CRD field (#3849), optional privileged DaemonSet (#3943). The v0.5.8 operator doc marks it deprecated: see the next row. |
| LMCache operator doc | `docs/source/mp/operator.rst`, `git diff v0.5.6 v0.5.8` | 2026-11-24 | v0.5.8 retitles the page "Kubernetes Operator (Deprecated)": "deprecated and no longer maintained … expected to be removed from this repository in 2027Q1. Existing release artifacts (e.g. `operator-v*` `install.yaml`) will not receive fixes or updates. Do not build new deployments on it." Points new deployments at the manual DaemonSet setup in `deployment.rst`. Other changes: `l2Backend.prefetchPolicy: skip_l1` for buffer-only mode; blending doc renamed `cacheblend`. |
| **LMCache security advisories** (CVE-2026-105192 / GHSA-w5f2-9q9c-ff4h and later) | https://github.com/LMCache/LMCache/security/advisories ; `gh api repos/LMCache/LMCache/security-advisories` | 2026-11-24 | Eight published. **GHSA-hhqh-8jpj-27rf** critical, `>= 0.4.7, < 0.5.8`, patched 0.5.8 (2026-11-23): unauthenticated proxy reaches any local UNIX socket (frontend; #6497, #6534). **GHSA-qr43-hv93-6x7p** critical, `>= 0.4.6, < 0.5.7`, patched 0.5.7 (2026-11-18): pickle deserialization in MP `commit_store`. **GHSA-jg4p-wprm-8hph** medium, `>= 0.4.5, < 0.5.8`, patched 0.5.8 (2026-11-23): KV cache shared across LoRA adapters and the base model in MP mode; fix #5713 (merged 2026-11-05) puts a `lmcache.tag.lora` digest in the cache identity, advisory says to clear L2 tiers written before the fix. **GHSA-xv3r-8wjc-26q5** high (unauthenticated KV overwrite), **GHSA-59pj-5774-xp3f** high (legacy `LMCacheServer` unvalidated TCP message length), **GHSA-799h-gjjf-wfm7** medium (RESP client memory exhaustion), all `< 0.5.7`. **GHSA-7p86-8g3v-vgv9** critical, `< 0.5.6`: unauthenticated `/run_script`. **GHSA-w5f2-9q9c-ff4h** critical (CVSS 9.8), `>= 0.3.9, < 0.5.6`, patched 0.5.6 (PR #5644): `pickle.loads` in `DeviceIPCWrapper.Deserialize`. Docs at v0.5.7 and v0.5.8: legacy pickle descriptors rejected, upgrade workers and servers together. Versioned image tags `v0.5.8` exist for `lmcache/standalone` and `lmcache/vllm-openai`; the `nightly` / `latest-nightly` tags move daily again (2026-11-24) and `nightly-<runid>-amd64|arm64` tags also exist. |
| Transport bind rule (DaemonSet) and API keys | https://github.com/LMCache/LMCache/pull/5684 ; `examples/multi_process/lmcache-daemonset.yaml`, `vllm-deployment.yaml`, `docs/source/mp/request_transport.rst` at tag v0.5.8 ; https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-and-hostnetwork-pods | 2026-11-24 | At v0.5.8 the DaemonSet example has `hostNetwork: true` and `--host 127.0.0.1`; `vllm-deployment.yaml` connects to `tcp://127.0.0.1` with no `hostNetwork`, so its loopback is the pod's own. Optional API keys (`--api-key-file`, `LMCACHE_API_KEY_FILE`, `LMCACHE_API_KEY`) cover ZMQ and gRPC request transports and HTTP; ZMQ sends the token in a versioned frame in clear; clients that predate it cannot talk to an authenticating server; `/` and `/healthcheck` stay public. Kubernetes docs: NetworkPolicy behaviour for `hostNetwork` pods is undefined. |
| LMCache MP HTTP API | `docs/source/mp/http_api.rst`, `lmcache/v1/multiprocess/http_apis/info_api.py`, `cache_api.py` (tag v0.5.8); https://github.com/LMCache/LMCache/pull/5129 ; https://kubernetes.io/docs/concepts/workloads/pods/probes/ | 2026-11-24 | Routes at v0.5.8: `GET /`, `GET /healthcheck`, `GET /status`, `GET /lmc_version`, `/commit_id`, `/version`, `POST /cache/clear`, plus `/cache/objects`, `/cache/prefetches`, `/cache/checksums` — no `/api/` prefix. `--http-host` default `127.0.0.1`, `--http-port` 8080; `/run_script` off unless `--run-script-api-enabled` (default `False`). Kubernetes probes page: a container listening on 127.0.0.1 with `hostNetwork: true` takes `httpGet.host: 127.0.0.1`. |
| vLLM #40040 (cache_salt fallback bug) | https://github.com/vllm-project/vllm/issues/40040 | 2026-11-24 | **CLOSED `not_planned` 2026-08-17 by `github-actions[bot]` — not fixed.** Fix PR #40041 is still **open and unmerged**. Skill guidance holds. |
| LMCache #2845 (hybrid tracker) | https://github.com/LMCache/LMCache/issues/2845 | 2026-11-24 | **CLOSED `NOT_PLANNED` 2026-10-09 by `github-actions[bot]`, label `stale`**; last comment is the inactivity auto-close message. No fix PR, no maintainer reply to the 2026-07-10 "should this close?" comment. Superseded by the hybrid-model docs above. |
| LMCache #2502 (LocalDiskBackend crash) | https://github.com/LMCache/LMCache/issues/2502 | 2026-11-24 | CLOSED `NOT_PLANNED` 2026-05-04 by `github-actions[bot]`, label `stale`, auto-close comment only — no fix; guidance stands. |
| LMCache #3106 (multi-group MemoryObj) | https://github.com/LMCache/LMCache/issues/3106 | 2026-11-24 | OPEN, last updated 2026-10-04. Blocks the **in-process** `LMCacheConnectorV1` on hybrids. A community comment reports `--no-separate-object-groups` as a DeepSeek-V4-Pro workaround (unverified here). |
| vLLM #38261 (HybridOffloadPlanner PR) | https://github.com/vllm-project/vllm/pull/38261 | 2026-11-24 | Still OPEN. No longer on the critical path for MP hybrids. |
| LMCache #2942 (LocalCPUBackend deadlock) | https://github.com/LMCache/LMCache/issues/2942 | 2026-11-24 | **CLOSED / NOT_PLANNED** 2026-07-30 — but closed by `github-actions[bot]` under the `stale` label, with no fix commit. Stale ≠ fixed, and a closed state here is not evidence of one: the deadlock guidance stands. Confirmed via `.closed_by.login` and labels, not `state_reason`. |
| vLLM connector source path | vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py | 2026-11-24 | Present at v0.34.0; registered in `factory.py` next to `LMCacheConnectorV1`. Repo-local fallback class `LMCacheMPConnectorUpstream` keeps the HMA guard (`RuntimeError` still present). `lmcache_integration/vllm_v1_adapter.py` still exists in vLLM v0.34.0 while lmcache 0.5.7+ dropped its own (#69358). |
| LMCache ParallelStrategy | lmcache/integration/vllm/vllm_multi_process_adapter.py | 2026-11-24 | `ParallelStrategy`, `LoadStoreOp`, `LMCacheMPSchedulerAdapter`, `LMCacheMPWorkerAdapter` present at tags v0.5.6, v0.5.7 and v0.5.8 (`HeartbeatThread` moved out of this file in 0.5.8, #6270). 0.4.3-no-class vs 0.4.4-has-class boundary: not re-run, unchanged. |

## Probes used

### Image runtime verification

Run `scripts/verify-bundling.sh <tag>` against any vllm-openai or lmcache image tag. The script:

1. Pulls the image (skipped if cached).
2. Starts a sleep-overridden container.
3. Inside the container: pip metadata check, runtime imports of `lmcache` / `nixl` / `mooncake`, MP adapter class import (including the `ParallelStrategy` version-hazard probe), connector factory registration check, and connector class load via the factory's own thunk-based loader (so it works regardless of the connector's source layout).

Verified tags as of skill creation:
- `vllm/vllm-openai:v0.19.1` — vllm 0.19.1, lmcache 0.4.3, nixl 0.9.0, mooncake-transfer-engine 0.3.10.post1. All connectors load. `ParallelStrategy` not present (correct for v0.19.x).

- `vllm/vllm-openai:v0.32.0` (2026-10-27) — vllm 0.32.0, lmcache 0.5.6, nixl 1.5.0, mooncake-transfer-engine-cuda13 0.3.13.post1. All connectors load.

- `vllm/vllm-openai:v0.34.0` (2026-11-24) — vllm 0.34.0, lmcache 0.5.7.post1, nixl 1.5.2, mooncake-transfer-engine-cuda13 0.3.14. All connectors load; 18 connectors registered.

### LMCache repo probes

Local clone of `LMCache/LMCache`, dev branch.

- `docs/source/mp/` — full MP architecture, deployment, L2 storage, observability, HTTP API documentation.
- `examples/multi_process/lmcache-daemonset.yaml` and `vllm-deployment.yaml` — canonical K8s manifests.
- `lmcache/integration/vllm/vllm_multi_process_adapter.py` — adapter classes including `ParallelStrategy` (v0.4.4+), `LoadStoreOp`, `LMCacheMPSchedulerAdapter`, `LMCacheMPWorkerAdapter`.
- Tag verification: `git show v0.4.3:lmcache/integration/vllm/vllm_multi_process_adapter.py | grep "class ParallelStrategy"` → 0 matches; `git show v0.4.4:...` → 1 match.

### vLLM repo probes

Local clone of `vllm-project/vllm`, main branch.

- `vllm/distributed/kv_transfer/kv_connector/factory.py` — registers `LMCacheConnectorV1` and `LMCacheMPConnector` side-by-side; `kv_cache_access` forces `LEGACY_IPC` for the stock MP connector when the lmcache connector lacks the classmethod.
- `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:79` at v0.34.0 (was :78 at v0.19.1) — `RuntimeError("LMCacheMPConnector only works without hybrid kv cache manager. Please pass --disable-hybrid-kv-cache-manager when starting vllm")`. Still present at v0.34.0, but only on the repo-local **fallback** class `LMCacheMPConnectorUpstream`; the external lmcache 0.5.x connector declares `SupportsHMA` and never raises it.
- v0.19.1 source vs main: v0.19.1 imports only `LMCacheMPSchedulerAdapter, LMCacheMPWorkerAdapter, LoadStoreOp`; main also imports `ParallelStrategy`. This drives the version-compat matrix.

### GitHub issue / PR probes

```bash
# vLLM kv_offload+HMA series (most parts merged through 2026-04-25)
gh api "search/issues?q=repo:vllm-project/vllm+is:pr+label:kv-connector+kv_offload+hma" \
  --jq '.items[] | {number, state, title, updated_at, pull_request_merged_at: .pull_request.merged_at}'

# Hybrid model + offload bugs
gh search issues --repo vllm-project/vllm "disable-hybrid-kv-cache-manager"
gh search issues --repo LMCache/LMCache "hybrid model"

# LMCache MP fallback adapter cache_salt mismatch (vLLM #40040)
gh issue view 40040 --repo vllm-project/vllm --json title,body,state

# Hybrid models tracker (LMCache #2845)
gh issue view 2845 --repo LMCache/LMCache --json title,body,state,comments

# Hybrid model PRs still open as of 2026-04-26
gh pr view 38261 --repo vllm-project/vllm --json title,state,mergedAt,updatedAt,labels
gh pr view 2879 --repo LMCache/LMCache --json title,state,mergedAt,updatedAt
```

### Recent history of native KV offload

```bash
git -C <vllm clone> log --oneline --all -50 \
  -- vllm/v1/kv_offload/ vllm/distributed/kv_transfer/kv_connector/v1/offloading/
```

### Image build-flag (NOT runtime — see bundling caveat in skill)

```bash
~/.claude/skills/vllm-caching/scripts/inspect-vllm-image.sh <tag>
```

This only checks the build flag `INSTALL_KV_CONNECTORS=true`. For runtime proof, use the verify-bundling.sh script in this skill.

## Re-verification triggers

Re-run the probes above when:

- A new vLLM release is tagged (verify the new image tag, check `kv_offload+HMA` series progress).
- A new LMCache release is tagged (verify `ParallelStrategy` and other adapter symbols).
- The user reports a connector failure that may be a new pin mismatch.
- After LMCache #2942 (LocalCPUBackend deadlock) is closed.

## Known stale risks

- The MP adapter file evolves quickly on dev branch. Adapter symbol names and signatures (`cache_salt` propagation, `LoadStoreOp` shape) may change without a major version bump.
- The bare `nightly` / `latest-nightly` image tags moved again (pushed 2026-11-24) after a pause from 2026-09-27; they are unpinned, so pin a versioned tag (or digest) at or above the security floor.
- The example K8s YAMLs in the LMCache repo can lag behind the current recommended invocation (e.g. they use `python3 -m lmcache.v1.multiprocess.server` rather than the newer `lmcache server` HTTP-frontend variant).
