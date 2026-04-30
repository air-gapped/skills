---
name: sglang-model-gateway
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  SGLang Model Gateway (`sgl-model-gateway`, formerly `sgl-router`) — Rust router fronting vLLM/SGLang inference workers on Kubernetes. Trigger on "sgl-model-gateway", "sgl-router", "sglang router", "smg", "amg", "model gateway", "inference gateway", "load balance vllm replicas", "fan out same model", "kubernetes vllm router", "cache-aware routing", "prefix_hash policy", "PD disaggregation router", "--worker-urls", "--service-discovery", "--enable-mesh", "smg_* metrics". Covers: first-class vLLM gRPC backend (`RuntimeType::Vllm`) plus HTTP transparent-proxy for vanilla vLLM; eight policies; air-gapped recipe (gateway ignores `HF_ENDPOINT`, mount tokenizer on PVC); K8s manifests with `model_id` labels + per-model RBAC; three HA mitigations (single+PDB / `sessionAffinity` / `--enable-mesh` CRDT sync); pitfalls (vLLM HTTP discovery registers empty labels, gRPC probes need numeric ports, `sgl_router_*` → `smg_*` rename Dec 2025).
---

# SGLang Model Gateway — sgl-model-gateway

Target audience: operators running **vLLM and/or SGLang inference on Kubernetes**, fronting workers with a router that does cache-aware load-balancing, optional prefill-decode disaggregation, and dynamic worker registration. Especially: hosting **multiple replicas of the same model** behind one address, in **air-gapped clusters with local model mirrors** (no live `huggingface.co`).

## Why this matters

A single vLLM or SGLang process serves one Pod. To scale beyond one GPU, you either fan-out replicas (N Pods, one Service) or run engine-internal data-parallelism (`vllm serve --data-parallel-size N`). Plain Kubernetes `Service` round-robins requests, which **fragments per-replica prefix caches** — every replica builds its own copy of the same prefix and hit rate divides by ~N. The Model Gateway is a Rust router that recovers most of that with a **cache-aware policy** (steers same-prefix requests to the same replica), adds health checks / circuit breakers / retries, exposes a unified OpenAI-compatible endpoint regardless of backend, and integrates with Kubernetes service discovery via label selectors. It also handles prefill-decode disaggregation when you split phases across worker pools.

## Sibling skills — what NOT to duplicate here

This skill stays inside the router's territory. Defer to:

- **`vllm-deployment`** — vLLM pod shape: `/dev/shm` emptyDir, `initialDelaySeconds: 600` (matches `VLLM_ENGINE_READY_TIMEOUT_S`), RHAIIS root-UID gotcha, LWS multi-node, container image selection.
- **`vllm-configuration`** — `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `HF_ENDPOINT` (no-trailing-slash gotcha), `VLLM_USE_MODELSCOPE`, `HF_TOKEN` for gated-offline, telemetry triple-opt-out.
- **`vllm-observability`** — vLLM-side `vllm:*` metric semantics (the gateway only adds `smg_*`).
- **`sglang-hicache`** — SGLang's three-tier prefix cache (orthogonal to the gateway).
- **`keda`** — autoscaling on `smg_router_request_queue_length` or `smg_inference_requests_running`.
- **`helm`** — chart authoring (no upstream gateway Helm chart exists; you build your own).

## Versions and canonical name (this is a footgun)

The project was **renamed in Dec 2025**:

| Field | Old (pre Dec 2025) | Current (April 2026) |
|---|---|---|
| Source directory | `sgl-router/` | `sgl-model-gateway/` |
| Rust crate | `sglang-router` | `sgl-model-gateway` |
| Binary names | `sglang-router` | `sgl-model-gateway`, `smg`, `amg` (3 aliases) |
| Docker image | `lmsysorg/sglang-router:*` | `lmsysorg/sgl-model-gateway:*` (current `:v0.3.x`) |
| Prometheus metric prefix | `sgl_router_*` | `smg_*` |
| Release tag prefix | `router-vX.Y.Z` | `gateway-vX.Y.Z` |
| Python launcher module | `sglang_router` | `sglang_router` (**not renamed**) |

The Python entry point `python3 -m sglang_router.launch_router` still works. CLI flags are unchanged across the rename. **Dashboards on `sgl_router_*` go silently empty after upgrading** — fix the metric prefix in your Grafana dashboards and Prometheus alerts.

PR refs: `sgl-project/sglang#14283` (crate rename), `sgl-project/sglang#14312` (directory rename).

## Architecture in one paragraph

The gateway is a stateless Rust process that accepts OpenAI-compatible HTTP and native gRPC traffic on a front port, maintains a registry of healthy backend workers, and forwards each request to one worker chosen by a **policy**. The full set: `cache_aware` (default — radix-tree prefix matching), `random`, `round_robin`, `power_of_two`, `prefix_hash` (lightweight deterministic prefix → worker), `consistent_hashing` (deterministic hash-ring), `bucket`, and `manual`. Workers are added either statically (`--worker-urls`), dynamically (`POST /workers`), or via Kubernetes service discovery (`--service-discovery --selector key=value --service-discovery-namespace ns`). The internal `WorkerType` enum has three variants — `Regular`, `Prefill`, `Decode` (PD-disagg) — and the `RuntimeType` enum has three — `Sglang`, `Vllm`, `External` (OpenAI-compatible non-local). Connection mode is `Http` or `Grpc`. A separate Prometheus exporter on `--prometheus-port` (default 29000) emits 40+ `smg_*` metrics. Source: `sgl-model-gateway/src/core/worker.rs`, `src/core/steps/worker/local/discover_metadata.rs`, `src/policies/`, `src/server.rs`, `src/service_discovery.rs`.

## Decision tree — vLLM behind the gateway

The single most-asked question is "how do I put N vLLM replicas behind one sgl-model-gateway?" There are **three viable paths**, and choosing the wrong one wastes a day:

```
Are you already on a vLLM gRPC fork (CatherineSue/vllm or upstream once it lands)?
├── Yes → Path A: vLLM-gRPC native (best, but currently requires the fork build)
└── No → Are you using HTTP-only vanilla vLLM?
        ├── Yes, and you only need basic load-balancing → Path B: HTTP transparent proxy via --worker-urls
        └── Yes, but you want vLLM to handle DP internally with one Pod → Path C: vLLM internal DP-LB (no gateway needed for fan-out)
```

### Path A — vLLM-gRPC native (first-class)

Requires a vLLM build with the gRPC server (PR `sgl-project/sglang#13120` references upstream `CatherineSue/vllm#2`). When available, the gateway treats vLLM workers as a typed `RuntimeType::Vllm` over `Connection::Grpc`. Auto-detect probes SGLang first, falls back to vLLM. Pin explicitly with `--runtime vllm` when registering. **Limitations from #13120:** no `n>1`, no logprobs, no multimodal, no LoRA, **no PD-disaggregation with vLLM workers**. If those features are required, stay on SGLang workers for now.

### Path B — HTTP via `--worker-urls` or service discovery (the realistic vanilla-vLLM path)

Vanilla vLLM speaks OpenAI-compatible HTTP and exposes `/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/health`, `/metrics`. It **does not** expose `/server_info` or `/model_info` — the metadata-enrichment endpoints SGLang workers use. The gateway's HTTP service-discovery probe **falls through gracefully**: when both `/server_info` and `/model_info` return 404, the discovery loop returns `Ok((labels=empty, None))` and **the worker is still registered** (source: `discover_metadata.rs:237-298` — `unwrap_or_else(|e| { warn!(...); (HashMap::new(), None) })`).

So **both** `--worker-urls` and `--service-discovery --selector model_id=...` work for vLLM HTTP workers — service discovery just registers them with empty discovered labels (no model name, no max-context auto-pulled from the worker). For Kubernetes, prefer service discovery so worker autoscaling adds/removes Pods without gateway restarts:

```bash
sgl-model-gateway \
  --worker-urls http://vllm-pool-0:8000 http://vllm-pool-1:8000 http://vllm-pool-2:8000 \
  --policy cache_aware \
  --tokenizer-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/ \
  --host 0.0.0.0 --port 8080
```

Cache-aware policy still works: it's a **pure prefix-hash on the router side** (radix tree over text, not tokens, in `src/policies/cache_aware.rs`). It does not query vLLM's internal cache state — it just steers same-prefix requests to the same replica so vLLM's *own* prefix cache hits. Set `--enable-prompt-tokens-details` on vLLM if you want OpenAI-standard `usage.prompt_tokens_details.cached_tokens` in responses (off by default).

For dynamic worker membership without K8s service discovery, use the runtime endpoints:

```bash
curl -X POST http://gateway:8080/workers -d '{"url":"http://vllm-3:8000","model_id":"llama-3-8b"}'
curl -X DELETE http://gateway:8080/workers/<worker_id>
curl     http://gateway:8080/workers
```

A K8s sidecar can `kubectl get endpoints -w` and reconcile this list. Crude but works today.

### Path C — vLLM internal DP-LB (`--data-parallel-size N` in one Pod)

vLLM has its own DP load-balancer modes (`vllm/entrypoints/cli/serve.py:64-104`):

- **Internal LB** (default): one `vllm serve --data-parallel-size N` process exposes a single `--port` and ZMQ-fans-out to N engines. From the gateway's perspective this is one upstream — DP is invisible. Use this when fitting N engines on one Pod is operationally simpler than N Pods, and you don't need cross-replica routing visibility.
- **External LB** (`--data-parallel-external-lb` + `--data-parallel-rank` per Pod): each Pod runs one DP rank, exposes its own port, and the *external* LB (= sgl-model-gateway) makes routing decisions per replica. This is what the gateway expects when you want true per-replica visibility. Per `vllm/config/parallel.py:135-146`: *"useful for a 'one-pod-per-rank' wide-EP setup in Kubernetes."*
- **Hybrid LB**: per-node API server, internal LB local DP ranks, external LB across nodes.

Rule: **don't put a gateway in front of vLLM internal-DP-LB Pods** — you lose per-replica visibility and double-hop. Either use vLLM internal-LB alone, or external-LB + gateway, never both.

## Decision tree — where the tokenizer must live

The gateway needs a tokenizer in three situations:

1. **gRPC mode (always)** — the gateway tokenizes locally before sending token IDs to the worker.
2. **HTTP mode + cache_aware policy with prefix-hash variant** — needs to hash prompt text → tokens for the radix tree.
3. **`/v1/tokenize`, `/v1/detokenize` endpoints** — gateway-side tokenization for clients.

Pass via `--tokenizer-path /local/dir` or `--model-path /local/dir` (latter derives the tokenizer). Both accept either an HF repo ID or a local directory. **Critical:** the Rust gateway's HF resolver **does not honour `HF_ENDPOINT`**. The Python `transformers` library does; the Rust `hf-hub` crate the gateway uses does not. In an air-gapped cluster with only an internal mirror, **passing an HF repo ID will fail** even with `HF_ENDPOINT` set. Always pass a local path. See `references/air-gapped.md`.

## Hosting multiple replicas of the same model — the "10-20%" claim explained

The doc line `Cache hits may decrease by 10-20%` is widely misquoted. It applies to running **multiple gateway replicas in front of the same workers**, not to multiple worker replicas behind one gateway. Each gateway replica builds its own radix tree, the trees are not shared by default, so when a request lands on Gateway-A and the next same-prefix request lands on Gateway-B, B doesn't know A made the previous routing decision and may pick a different worker → cache miss. The 10-20% is the empirical penalty of HA-pairing the gateway itself.

**Three mitigations**, in increasing operational complexity:

1. **Single gateway replica + PDB**. Best cache locality. Brief unavailability during restarts (Rust binary, sub-second cold start). Default recommendation.
2. **`sessionAffinity: ClientIP` on the gateway Service**. Clients pin to one gateway replica; same-prefix requests stay on the same gateway → same routing decision. Simple, no gateway-side config. Hot-spot risk if a single client IP dominates traffic.
3. **`--enable-mesh` (gateway mesh sync, shipped in v0.3.x).** Each gateway replica syncs its **worker registry + policy registry state** (including the radix tree) to peers via gRPC + CRDTs. Eventual consistency. Default mesh port `39527`. Enable with `--enable-mesh --mesh-peer-urls grpc://gateway-0:39527 grpc://gateway-1:39527`, or with K8s pod-annotation discovery via `--router-mesh-port-annotation sglang.ai/mesh-port`. `MeshSyncManager` lives in `src/server.rs:744-981`. The doc warning predates this feature and is essentially stale once mesh is on.

For **N worker replicas behind 1 gateway** (the common case), cache_aware routing is *the recovery mechanism*, not a penalty. But it's only beneficial when:

- Prefix sharing across requests is high (chat with system prompts, RAG with same retrieved chunks, code-review of same repo).
- Per-replica KV memory is **constrained** — abundant memory means vLLM's own prefix cache absorbs the win regardless of routing. See `sgl-project/sglang#17623` for an operator's reproduction where cache_aware ≈ k8s-RR with comfortable KV memory.
- Workers are CPU-pinned to keep tokenizer / scheduler latency from drowning the routing benefit.

If your workload is single-turn unique prompts, cache_aware ≈ random — that's fine, just don't expect a TTFT win.

## Air-gapped + local mirror — the recipe that works

Both gateway and worker pods need:

- A read-mostly model store (PVC or hostPath) that already contains the HF snapshot — `tokenizer.json`, `tokenizer_config.json`, `chat_template.jinja` (or embedded in tokenizer_config), `config.json`, weights.
- `HF_HOME` and `HF_HUB_CACHE` env vars pointing into that store.
- A **writable** `HF_HOME` location for any side-files vLLM/transformers caches at runtime — never point `HF_HOME` at a read-only PVC mount or initialization writes will fail.
- `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` on the *worker* (the gateway doesn't read these — it just doesn't try the network when given a local path).

Gateway args reference the local path:

```bash
--model-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/
```

For the full flag list, snapshot directory layout, ModelScope alternative, and gated-model-offline trap, see `references/air-gapped.md`.

## Kubernetes — minimal working pattern

The pattern in production (matches the user's `k8s-homelab/` reference) is **one Deployment+Service+RBAC per model**, keyed by a `model_id` label:

- Worker Deployment: `model_id=<name>`, port 30000 (SGLang) or 8000 (vLLM), `httpGet /health` probes, hostPath/PVC for `/models`.
- Worker Service: `clusterIP: ClusterIP` (or headless), selects on `model_id`.
- Gateway Deployment: 1 replica (or N for HA, accepting the 10-20% cache-hit penalty), `lmsysorg/sgl-model-gateway:v0.3.x`, args include `--service-discovery --selector model_id=<name> --service-discovery-namespace <ns> --service-discovery-port 30000` for SGLang workers (HTTP discovery works) **OR** `--worker-urls http://worker-svc:30000` for vLLM HTTP workers (discovery does not work).
- Gateway ServiceAccount + Role + RoleBinding: `pods, endpoints, services` with verbs `get, list, watch`.
- Gateway Service: routes 8080 (HTTP) and 29000 (Prometheus).
- ServiceMonitor with relabelings to surface `model_id`, `pod`, `node` labels.

Full manifests in `assets/sglang-gateway-deployment.yaml` (SGLang worker) and `assets/vllm-behind-gateway.yaml` (vLLM worker). For RBAC details, multi-port-per-pod limitation (`#20184`), gRPC probes-need-numeric-ports, and HA gateway pattern, see `references/kubernetes.md`.

## Critical pitfalls

1. **HTTP service discovery registers vLLM workers with empty metadata, not rich metadata.** Discovery probes `/server_info` + `/model_info`, which vLLM 404s. The gateway falls through gracefully (`discover_metadata.rs:237-298` returns `Ok((empty_labels, None))`) and **the worker is still registered** — routing works, cache_aware works (it's router-side prefix-hashing), but you don't get worker-side label enrichment. Pass `--tokenizer-path` explicitly since the gateway can't fetch it from the worker. Static `--worker-urls` is also fine — pick whichever fits your autoscaling story.

2. **PD-disaggregation does not support vLLM workers.** Per PR #13120 limitation matrix. Don't mix vLLM into prefill/decode pools.

3. **The Rust gateway ignores `HF_ENDPOINT` entirely.** It uses raw `reqwest` for its few HTTP calls (no `hf-hub` Rust crate), so neither Python `transformers`-style nor Rust `hf-hub`-style endpoint rewriting applies. Verified by grep: zero hits for `HF_ENDPOINT` in the gateway source. Always pass a local directory to `--model-path` / `--tokenizer-path` in air-gapped clusters.

4. **gRPC liveness/readiness probes need numeric ports**, not named (Kubernetes API constraint, not gateway-specific). For HTTP gateways probing `/health`, named ports work fine.

5. **Service discovery only watches one port per pod** (`#20184`). For nodes hosting two decode workers on different ports, split into two Pods, one port each.

6. **Multi-replica gateway → 10-20% cache hit reduction.** Each gateway replica owns its radix tree; the trees are not shared. Either accept the penalty for HA, or use a single gateway with PodDisruptionBudget + fast restarts.

7. **Dynamic worker registration does not inherit the gateway API key.** When POSTing to `/workers`, pass `api_key=...` explicitly.

8. **Metric prefix renamed Dec 2025**: `sgl_router_*` → `smg_*`. Update Grafana dashboards and Prometheus alerts. The `lmsysorg/sgl-model-gateway:v0.3.x` images all use the new prefix.

9. **vLLM's `prompt_tokens_details.cached_tokens` is gated behind `--enable-prompt-tokens-details`.** Off by default. Without it, every response carries `prompt_tokens_details: null` and your gateway loses per-request cache feedback (you'd have to scrape `vllm:prefix_cache_hits` from `/metrics` instead).

10. **Don't put a gateway in front of vLLM `--data-parallel-size N` internal-LB Pods.** You lose per-replica visibility and double-hop. Use vLLM external-LB mode (`--data-parallel-external-lb` + per-Pod `--data-parallel-rank`) when you want gateway-level routing intelligence.

11. **Workers behind cache_aware need similar GPU memory budgets.** The policy assumes uniform replicas; mixing a 24 GB and an 80 GB GPU in the same pool produces uneven evictions and the cache score becomes meaningless.

For the extended troubleshooting list, see `references/pitfalls.md`.

## Where to go next

- **vLLM-specific deep-dive** (gRPC vs HTTP path matrix, `--enable-prompt-tokens-details`, DP modes, what vLLM endpoints the gateway sees) → `references/vllm-backend.md`
- **Air-gapped / mirror recipes** (what files the snapshot dir needs, env vars, ModelScope, gated-model HF_TOKEN trap) → `references/air-gapped.md`
- **Kubernetes deep-dive** (RBAC, label selectors, multi-port-per-pod, gRPC probes, ServiceMonitor relabelings, PDB, multi-gateway HA) → `references/kubernetes.md`
- **Full CLI flag reference** (all 80+ flags grouped by category, defaults, env-var equivalents) → `references/cli-flags.md`
- **`smg_*` Prometheus surface** (40+ metrics, alert recipes, PromQL for cache hit rate / queue depth / circuit breaker state) → `references/metrics.md`
- **Extended pitfalls** (the long list with reproductions and fixes) → `references/pitfalls.md`
- **Reference manifests** (drop-in YAML for SGLang and vLLM workers behind a gateway) → `assets/sglang-gateway-deployment.yaml`, `assets/vllm-behind-gateway.yaml`

## Source of truth

- Upstream docs: https://docs.sglang.io/docs/advanced_features/sgl_model_gateway.md
- Source: https://github.com/sgl-project/sglang/tree/main/sgl-model-gateway
- Local clone: `~/projects/github.com/sgl-project/sglang/sgl-model-gateway/`
- Reference homelab manifests (untracked, repo-local): `~/projects/github.com/sgl-project/sglang/k8s-homelab/`
- Verify a flag with `--help`: `docker run --rm lmsysorg/sgl-model-gateway:v0.3.1 --help`. If this skill disagrees with `--help`, trust `--help` and freshen the skill.
