# Sources and verification log

This skill was authored against live source code, image inspection, and live GitHub issue state. Re-run probes when re-verifying.

## Last verified

**2026-04-26** (skill creation).

## Probes used

### Image runtime verification

Run `scripts/verify-bundling.sh <tag>` against any vllm-openai or lmcache image tag. The script:

1. Pulls the image (skipped if cached).
2. Starts a sleep-overridden container.
3. Inside the container: pip metadata check, runtime imports of `lmcache` / `nixl` / `mooncake`, MP adapter class import (including the `ParallelStrategy` version-hazard probe), connector factory registration check, and connector class load via the factory's own thunk-based loader (so it works regardless of the connector's source layout).

Verified tags as of skill creation:
- `vllm/vllm-openai:v0.19.1` — vllm 0.19.1, lmcache 0.4.3, nixl 0.9.0, mooncake-transfer-engine 0.3.10.post1. All connectors load. `ParallelStrategy` not present (correct for v0.19.x).

### LMCache repo probes

Local clone at `~/projects/github.com/LMCache/LMCache`, dev branch.

- `docs/source/mp/` — full MP architecture, deployment, L2 storage, observability, HTTP API documentation.
- `examples/multi_process/lmcache-daemonset.yaml` and `vllm-deployment.yaml` — canonical K8s manifests.
- `lmcache/integration/vllm/vllm_multi_process_adapter.py` — adapter classes including `ParallelStrategy` (v0.4.4+), `LoadStoreOp`, `LMCacheMPSchedulerAdapter`, `LMCacheMPWorkerAdapter`.
- Tag verification: `git show v0.4.3:lmcache/integration/vllm/vllm_multi_process_adapter.py | grep "class ParallelStrategy"` → 0 matches; `git show v0.4.4:...` → 1 match.

### vLLM repo probes

Local clone at `~/projects/github.com/vllm-project/vllm`, main branch.

- `vllm/distributed/kv_transfer/kv_connector/factory.py` — registers `LMCacheConnectorV1` (line 168) and `LMCacheMPConnector` (line 174) side-by-side.
- `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:78` — `RuntimeError("LMCacheMPConnector only works without hybrid kv cache manager. Please pass --disable-hybrid-kv-cache-manager when starting vllm")`.
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
