# Sources and verification log

This skill was authored against live source code, image inspection, and live GitHub issue state. Re-run probes when re-verifying.

## Last verified

**2026-07-21** (freshen pass). Prior passes: 2026-05-28, 2026-04-26 (original authoring).

### Per-source verification table

| Source | URL | Last verified | Notes |
|---|---|---|---|
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-07-21 | **v0.25.1 (2026-07-14)** current stable. Line since last pass: v0.22.0 (05-29), v0.22.1 (06-05), v0.23.0 (06-15), v0.24.0 (06-29), v0.25.0 (07-11). |
| LMCache releases | https://github.com/LMCache/LMCache/releases | 2026-07-21 | **v0.5.1 (2026-07-06)** current stable; v0.5.0 (P2P for MP mode, #3740/#3762); v0.5.2rc1 + nightly (2026-07-20). 0.5.0 renames: `MPCacheEngine`→`MPCacheServer`, `GPUKVFormat`→`EngineKVFormat`, `GPUTransferModule`→`LMCacheDrivenTransferModule`. |
| **LMCache hybrid-model support** | https://docs.lmcache.ai/mp/hybrid_models.html (repo `docs/source/mp/hybrid_models.rst`) | 2026-07-21 | **Inverts the skill's core "hybrids unsupported" claim.** `LMCacheMPConnector` declares `SupportsHMA` at `lmcache/integration/vllm/lmcache_mp_connector.py:512` (tag v0.5.1), so vLLM keeps HMA enabled and no flag is needed. Recipes for Gemma 3/4, gpt-oss, Qwen3.5/3.6, DeepSeek-V4-Flash, GLM 5.1/5.2, MiniMax-M3. Mamba/GDN hybrids need the model's unified block size `N` read from vLLM's own startup log. |
| `--separate-object-groups` | `lmcache/v1/multiprocess/config.py:48`, `lmcache/v1/kv_layer_groups.py:307` (tag v0.5.1) | 2026-07-21 | Default `True`: one object group per distinct cross-chunk attention window. `--no-separate-object-groups` collapses to a single full-attention group (pre-0.5.1 behavior). Documented as transparent to correctness. |
| LMCache K8s Operator | https://github.com/LMCache/LMCache/releases | 2026-07-21 | **operator-v0.5.0 (2026-06-25)** is current stable — the numbering jumped from operator-v0.1.1 (2026-05-18). operator-v0.5.1rc1 (2026-07-20) is an RC. 0.5-line features: webhook auto-injecting the `LMCacheEngine` connection into vLLM pods (#3822), `hostNetwork` CRD field (#3849), optional privileged DaemonSet (#3943). |
| vLLM #40040 (cache_salt fallback bug) | https://github.com/vllm-project/vllm/issues/40040 | 2026-07-21 | Still OPEN, updated 2026-07-17. Skill guidance holds. |
| LMCache #2845 (hybrid tracker) | https://github.com/LMCache/LMCache/issues/2845 | 2026-07-21 | Still OPEN (updated 2026-07-10) but **superseded by the docs above** — a 2026-07-10 comment asks whether it should be closed given the published support. Bookkeeping lag, not a blocker. |
| LMCache #3106 (multi-group MemoryObj) | https://github.com/LMCache/LMCache/issues/3106 | 2026-07-21 | OPEN, active 2026-07-17. Blocks the **in-process** `LMCacheConnectorV1` on hybrids. A community comment reports `--no-separate-object-groups` as a DeepSeek-V4-Pro workaround (unverified here). |
| vLLM #38261 (HybridOffloadPlanner PR) | https://github.com/vllm-project/vllm/pull/38261 | 2026-07-21 | Still OPEN. No longer on the critical path for MP hybrids. |
| LMCache #2942 (LocalCPUBackend deadlock) | https://github.com/LMCache/LMCache/issues/2942 | 2026-07-21 | OPEN; auto-marked **stale** 2026-06-29 with no fix. Stale ≠ fixed. |
| vLLM connector source path | vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py | 2026-07-21 | Present at v0.25.1; still registered in `factory.py` alongside `LMCacheConnectorV1`. The repo-local class is `LMCacheMPConnectorUpstream` and retains the old HMA guard (line 80) — it is the fallback, not the connector you want. |
| LMCache ParallelStrategy | lmcache/integration/vllm/vllm_multi_process_adapter.py | 2026-07-21 | Class still present at tag v0.5.1 alongside `HeartbeatThread`, `LoadStoreOp`, `LMCacheMPSchedulerAdapter`, `LMCacheMPWorkerAdapter`. 0.4.3-no-class vs 0.4.4-has-class boundary still accurate. |

## Probes used

### Image runtime verification

Run `scripts/verify-bundling.sh <tag>` against any vllm-openai or lmcache image tag. The script:

1. Pulls the image (skipped if cached).
2. Starts a sleep-overridden container.
3. Inside the container: pip metadata check, runtime imports of `lmcache` / `nixl` / `mooncake`, MP adapter class import (including the `ParallelStrategy` version-hazard probe), connector factory registration check, and connector class load via the factory's own thunk-based loader (so it works regardless of the connector's source layout).

Verified tags as of skill creation:
- `vllm/vllm-openai:v0.19.1` — vllm 0.19.1, lmcache 0.4.3, nixl 0.9.0, mooncake-transfer-engine 0.3.10.post1. All connectors load. `ParallelStrategy` not present (correct for v0.19.x).

Not yet re-run on the current stable pair: no bundling table exists for `vllm/vllm-openai:v0.25.1` (lmcache 0.5.x) — the v0.19.1 row above is five vLLM minors old and is the only runtime-verified evidence in this skill. Run `scripts/verify-bundling.sh v0.25.1` before relying on bundled versions for a pinned deploy; expect nixl 1.3.0 (vLLM's exact pin) and lmcache ≥ 0.5.x.

### LMCache repo probes

Local clone at `~/projects/github.com/LMCache/LMCache`, dev branch.

- `docs/source/mp/` — full MP architecture, deployment, L2 storage, observability, HTTP API documentation.
- `examples/multi_process/lmcache-daemonset.yaml` and `vllm-deployment.yaml` — canonical K8s manifests.
- `lmcache/integration/vllm/vllm_multi_process_adapter.py` — adapter classes including `ParallelStrategy` (v0.4.4+), `LoadStoreOp`, `LMCacheMPSchedulerAdapter`, `LMCacheMPWorkerAdapter`.
- Tag verification: `git show v0.4.3:lmcache/integration/vllm/vllm_multi_process_adapter.py | grep "class ParallelStrategy"` → 0 matches; `git show v0.4.4:...` → 1 match.

### vLLM repo probes

Local clone at `~/projects/github.com/vllm-project/vllm`, main branch.

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
git -C ~/projects/github.com/vllm-project/vllm log --oneline --all -50 \
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
- After the LMCache #2845 hybrid-model tracker reports new state (community patch landed? official PR merged?).
- After LMCache #2942 (LocalCPUBackend deadlock) is closed.

## Known stale risks

- The MP adapter file evolves quickly on dev branch. Adapter symbol names and signatures (`cache_salt` propagation, `LoadStoreOp` shape) may change without a major version bump.
- The `lmcache/standalone:nightly` and `lmcache/vllm-openai:latest-nightly` images change daily. Pin to a digest if reproducibility matters.
- The example K8s YAMLs in the LMCache repo can lag behind the current recommended invocation (e.g. they use `python3 -m lmcache.v1.multiprocess.server` rather than the newer `lmcache server` HTTP-frontend variant).
