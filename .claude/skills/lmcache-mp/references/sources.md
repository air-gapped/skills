# Sources and verification log

Freshened: 2026-10-27 — every row probed. LMCache v0.5.6 sets a security floor for MP mode (CVE-2026-105192) and moves the HTTP admin bind to loopback; the current pair is vLLM v0.32.0, whose `-cu129` images still ship lmcache 0.4.4.

This skill was authored against live source code, image inspection, and live GitHub issue state. Re-run probes when re-verifying.

## Last verified

**2026-10-27** (freshen pass). Prior passes: 2026-09-22, 2026-09-15, 2026-07-21, 2026-05-28, 2026-04-26 (original authoring).

**A default flipped under this skill.** `--separate-object-groups` shipped `True` through v0.5.2 and is `False` from **v0.5.3** onward. Guidance written against v0.5.1 — "default on, no flag needed for hybrids" — is wrong on v0.5.3+: per-window object groups must now be asked for explicitly. Verified by reading the default at each tag, not from release notes, which do not call it out.

### Per-source verification table

| Source | URL | Last verified | Notes |
|---|---|---|---|
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-10-27 | **v0.32.0 (2026-10-18)** isLatest, via v0.30.0 (09-22) and v0.31.0 (10-05). `requirements/kv_connectors.txt`: `lmcache >= 0.3.9` at every tag; `nixl == 1.4.1` at v0.30.0/v0.31.0, `== 1.5.0` at v0.32.0. **#57945** (merged 2026-09-22, first in v0.31.0) adds `requirements/kv_connectors_cu12.txt` with `lmcache == 0.4.4` / `nixl == 1.4.1`, selected by `docker/Dockerfile` when `CUDA_MAJOR` is 12 — i.e. the `-cu129` image tags. Container run of `vllm/vllm-openai:v0.32.0` on 2026-10-27: vllm 0.32.0, lmcache 0.5.6, nixl 1.5.0, mooncake-transfer-engine-cuda13 0.3.13.post1; all four connector classes load. |
| LMCache releases | https://github.com/LMCache/LMCache/releases | 2026-10-27 | **v0.5.6 (2026-10-14)** isLatest, PyPI `lmcache` 0.5.6. v0.5.7rc1/rc2 (10-23/10-26) are prereleases, not on PyPI. Docker Hub `lmcache/standalone` and `lmcache/vllm-openai` carry `v0.5.6` and `latest` (2026-10-16). 0.5.0 renames: `MPCacheEngine`→`MPCacheServer`, `GPUKVFormat`→`EngineKVFormat`, `GPUTransferModule`→`LMCacheDrivenTransferModule`. |
| **LMCache hybrid-model support** | https://docs.lmcache.ai/mp/hybrid_models.html (repo `docs/source/mp/hybrid_models.rst`) | 2026-10-27 | **Inverts the skill's core "hybrids unsupported" claim.** `LMCacheMPConnector` declares `SupportsHMA` at `lmcache/integration/vllm/lmcache_mp_connector.py:535` (tag v0.5.6; :512 at v0.5.1), so vLLM keeps HMA enabled and no flag is needed. Recipes for Gemma 3/4, gpt-oss, Qwen3.5/3.6, DeepSeek-V4-Flash, GLM 5.1/5.2, MiniMax-M3. Mamba/GDN hybrids need the model's unified block size `N` read from vLLM's own startup log. |
| `--separate-object-groups` | `lmcache/v1/multiprocess/config.py:61` (dataclass) and `:505` (argparse) at tag v0.5.6 | 2026-10-27 | **Default `False`**, unchanged at v0.5.6, v0.5.7rc2 and dev. Read at each tag: `True` at v0.5.1 and v0.5.2, `False` from v0.5.3. On v0.5.3+ pass `--separate-object-groups` explicitly to get one object group per attention window. |
| Prompt-only store default (`lmcache.mp.save_decode_cache`) | https://github.com/LMCache/LMCache/pull/5239 ; `lmcache/integration/vllm/lmcache_mp_connector.py:609-613`, `lmcache_mp_metadata.py:231,296` and `docs/source/mp/configuration.rst` at tag v0.5.6 | 2026-10-27 | #5239 (merged 2026-10-05, fixes #5230, first in v0.5.6) caps MP stores at `num_prompt_tokens` unless the key is `true`; default `False` read in code at v0.5.6. At v0.5.5 the store bound is `min(len(all_token_ids), allocated, computed)` with no prompt cap and the key does not exist. Docs: key is separate from the in-process connector's `save_decode_cache`; enable for resumable/streaming sessions. |
| MP server auto-start (`lmcache.mp.autostart`) | https://github.com/LMCache/LMCache/pull/3476 ; `lmcache/integration/vllm/mp_server_launcher.py:134` and `docs/source/mp/configuration.rst` at tag v0.5.6 | 2026-10-27 | #3476 (merged 2026-09-18, fixes #3065, first in v0.5.6; `mp_server_launcher.py` absent at v0.5.5). Opt-in: missing key parses to `False`. Worker 0 spawns `sys.executable -m lmcache.v1.multiprocess.http_server` as a child (`mp_server_launcher.py:312-330`); localhost/127.0.0.1 only, IPv6 and multiple `server_urls` raise `ValueError`; `wait_timeout` default 90 s; endpoint flags in `server_args` rejected. PR validation: vLLM 0.28.0 SIGTERM shutdown killed the child; docs guarantee neither survival nor cleanup and send shared or restart-surviving servers to a separately managed process. |
| ARC eviction policy | https://github.com/LMCache/LMCache/pull/4994 ; https://github.com/LMCache/LMCache/pull/5348 ; `lmcache/v1/distributed/config.py:905-913`, `l2_adapters/config.py:261` at tag v0.5.6 | 2026-10-27 | #4994 (merged 2026-09-22) adds ARC for L1 and per-L2-adapter eviction; #5348 (merged 2026-09-29, fixes #5347) stops new keys skipping T1. Both first in v0.5.6; v0.5.5 choices are `LRU`/`IsolatedLRU`/`noop`. `--eviction-policy` is `required=True` at v0.5.5 and `default=None` with a startup `ValueError` at v0.5.6; watermark 0.8 / ratio 0.2 defaults unchanged. PR scope: global (ignores `cache_salt`), entry-count based; one CPU A/B on a hot-set-plus-scan workload gave hot-probe hit rate 0% (LRU) vs 100% (ARC). |
| LMCache K8s Operator | https://github.com/LMCache/LMCache/releases/tag/operator-v0.5.5 | 2026-10-27 | **operator-v0.5.5 (2026-09-15)** newest operator tag; ships `install.yaml`. operator-v0.5.1–v0.5.5 have empty release notes. 0.5-line features from the core 0.5.1 notes: webhook auto-injecting the `LMCacheEngine` connection into vLLM pods (#3822), `hostNetwork` CRD field (#3849), optional privileged DaemonSet (#3943). |
| **CVE-2026-105192 / GHSA-w5f2-9q9c-ff4h** (MP transport RCE) | https://github.com/LMCache/LMCache/security/advisories/GHSA-w5f2-9q9c-ff4h | 2026-10-27 | Critical, CVSS 9.8, published 2026-10-13. Affected `lmcache >= 0.3.9, < 0.5.6`; patched 0.5.6 (PR #5644, merged 2026-10-12): `DeviceIPCWrapper.Deserialize` called `pickle.loads` while decoding `REGISTER_KV_CACHE` args, before any handler. Socket has no CURVE/ZAP/auth, which 0.5.6 does not change. Wire format changed in 0.5.6 — upgrade all sides together. The `nightly` / `latest-nightly` image tags were last pushed 2026-09-27 (pre-fix) per Docker Hub; versioned `v0.5.6` tags exist for both `lmcache/standalone` and `lmcache/vllm-openai` (2026-10-16). |
| Transport bind rule (DaemonSet) | https://github.com/LMCache/LMCache/pull/5684 ; https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-and-hostnetwork-pods | 2026-10-27 | #5684 (merged 2026-10-13, first in v0.5.7rc1) moves `examples/multi_process/lmcache-daemonset.yaml` to `--host 127.0.0.1` and the vLLM Deployment to `tcp://127.0.0.1`, but `vllm-deployment.yaml` at v0.5.7rc2 still has no `hostNetwork`, so its loopback is the pod's own. Kubernetes docs: NetworkPolicy behaviour for `hostNetwork` pods is undefined, and the most common implementation ignores them. |
| LMCache MP HTTP API | `docs/source/mp/http_api.rst`, `lmcache/v1/multiprocess/http_apis/info_api.py`, `cache_api.py` (tag v0.5.6); https://github.com/LMCache/LMCache/pull/5129 ; https://kubernetes.io/docs/concepts/workloads/pods/probes/ | 2026-10-27 | Routes are `GET /healthcheck` (200 `{"status":"healthy"}`, 503 before engine init), `GET /status`, `POST /cache/clear` (body `{"tier":"l1","force":false}`) — no `/api/` prefix at v0.4.5, v0.5.1 or v0.5.6; 0.4.5 used `/clear-cache`. #5129 (merged 2026-09-23, in v0.5.6): `--http-host` default `127.0.0.1`, `/run_script` off unless `--run-script-api-enabled`. Kubernetes probes page: a container listening on 127.0.0.1 with `hostNetwork: true` takes `httpGet.host: 127.0.0.1`. |
| vLLM #40040 (cache_salt fallback bug) | https://github.com/vllm-project/vllm/issues/40040 | 2026-10-27 | **CLOSED `NOT_PLANNED` 2026-08-17 by the inactivity bot — not fixed.** Its fix PR #40041 ("Fix fallback adapter cache_salt signature mismatch") is still **open and unmerged**, so the signature mismatch is live. Skill guidance holds. |
| LMCache #2845 (hybrid tracker) | https://github.com/LMCache/LMCache/issues/2845 | 2026-10-27 | **CLOSED `NOT_PLANNED` 2026-10-09 by `github-actions[bot]`, label `stale`**; last comment is the inactivity auto-close message. No fix PR, no maintainer reply to the 2026-07-10 "should this close?" comment. Superseded by the hybrid-model docs above. |
| LMCache #2502 (LocalDiskBackend crash) | https://github.com/LMCache/LMCache/issues/2502 | 2026-10-27 | CLOSED `NOT_PLANNED` 2026-05-04 by `github-actions[bot]`, label `stale`, auto-close comment only — no fix; guidance stands. |
| LMCache #3106 (multi-group MemoryObj) | https://github.com/LMCache/LMCache/issues/3106 | 2026-10-27 | OPEN, last updated 2026-10-04. Blocks the **in-process** `LMCacheConnectorV1` on hybrids. A community comment reports `--no-separate-object-groups` as a DeepSeek-V4-Pro workaround (unverified here). |
| vLLM #38261 (HybridOffloadPlanner PR) | https://github.com/vllm-project/vllm/pull/38261 | 2026-10-27 | Still OPEN. No longer on the critical path for MP hybrids. |
| LMCache #2942 (LocalCPUBackend deadlock) | https://github.com/LMCache/LMCache/issues/2942 | 2026-10-27 | **CLOSED / NOT_PLANNED** 2026-07-30 — but closed by `github-actions[bot]` under the `stale` label, with no fix commit. Stale ≠ fixed, and a closed state here is not evidence of one: the deadlock guidance stands. Confirmed via `.closed_by.login` and labels, not `state_reason`. |
| vLLM connector source path | vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py | 2026-10-27 | Present at v0.32.0; registered in `factory.py` (lines 166–174) alongside `LMCacheConnectorV1`. Repo-local fallback class `LMCacheMPConnectorUpstream` (line 461) keeps the HMA guard (`RuntimeError` at lines 79–80). |
| LMCache ParallelStrategy | lmcache/integration/vllm/vllm_multi_process_adapter.py | 2026-10-27 | At tag v0.5.6: `ParallelStrategy` (362), `HeartbeatThread` (509), `LoadStoreOp` (623), `LMCacheMPSchedulerAdapter` (670), `LMCacheMPWorkerAdapter` (1314). 0.4.3-no-class vs 0.4.4-has-class boundary still accurate. |

## Probes used

### Image runtime verification

Run `scripts/verify-bundling.sh <tag>` against any vllm-openai or lmcache image tag. The script:

1. Pulls the image (skipped if cached).
2. Starts a sleep-overridden container.
3. Inside the container: pip metadata check, runtime imports of `lmcache` / `nixl` / `mooncake`, MP adapter class import (including the `ParallelStrategy` version-hazard probe), connector factory registration check, and connector class load via the factory's own thunk-based loader (so it works regardless of the connector's source layout).

Verified tags as of skill creation:
- `vllm/vllm-openai:v0.19.1` — vllm 0.19.1, lmcache 0.4.3, nixl 0.9.0, mooncake-transfer-engine 0.3.10.post1. All connectors load. `ParallelStrategy` not present (correct for v0.19.x).

- `vllm/vllm-openai:v0.32.0` (2026-10-27) — vllm 0.32.0, lmcache 0.5.6, nixl 1.5.0, mooncake-transfer-engine-cuda13 0.3.13.post1. All connectors load.

### LMCache repo probes

Local clone of `LMCache/LMCache`, dev branch.

- `docs/source/mp/` — full MP architecture, deployment, L2 storage, observability, HTTP API documentation.
- `examples/multi_process/lmcache-daemonset.yaml` and `vllm-deployment.yaml` — canonical K8s manifests.
- `lmcache/integration/vllm/vllm_multi_process_adapter.py` — adapter classes including `ParallelStrategy` (v0.4.4+), `LoadStoreOp`, `LMCacheMPSchedulerAdapter`, `LMCacheMPWorkerAdapter`.
- Tag verification: `git show v0.4.3:lmcache/integration/vllm/vllm_multi_process_adapter.py | grep "class ParallelStrategy"` → 0 matches; `git show v0.4.4:...` → 1 match.

### vLLM repo probes

Local clone of `vllm-project/vllm`, main branch.

- `vllm/distributed/kv_transfer/kv_connector/factory.py` — registers `LMCacheConnectorV1` (line 168) and `LMCacheMPConnector` (line 174) side-by-side.
- `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:80` (was :78 at v0.19.1) — `RuntimeError("LMCacheMPConnector only works without hybrid kv cache manager. Please pass --disable-hybrid-kv-cache-manager when starting vllm")`. Still present at v0.25.1, but only on the repo-local **fallback** class `LMCacheMPConnectorUpstream`; the external lmcache 0.5.x connector declares `SupportsHMA` and never raises it.
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
- The bare `nightly` / `latest-nightly` image tags stopped moving on 2026-09-27; daily builds now publish as `nightly-<runid>-amd64|arm64`. Pin a versioned tag (or digest) at or above the security floor.
- The example K8s YAMLs in the LMCache repo can lag behind the current recommended invocation (e.g. they use `python3 -m lmcache.v1.multiprocess.server` rather than the newer `lmcache server` HTTP-frontend variant).
