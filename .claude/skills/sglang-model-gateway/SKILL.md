---
name: sglang-model-gateway
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  SGLang Model Gateway (`sgl-model-gateway`, formerly `sgl-router`) — Rust router fronting vLLM/SGLang inference workers on Kubernetes. Trigger on "sgl-model-gateway", "sgl-router", "sglang router", "smg", "amg", "model gateway", "inference gateway", "load balance vllm replicas", "fan out same model", "kubernetes vllm router", "cache-aware routing", "prefix_hash policy", "PD disaggregation router", "--worker-urls", "--service-discovery", "--enable-mesh", "smg_* metrics", "--tokenizer-path", "tokenizer.json vs tiktoken.model", "Kimi K2", "K2.6", "DeepSeek tiktoken". Covers: first-class vLLM gRPC backend (`RuntimeType::Vllm`) plus HTTP transparent-proxy for vanilla vLLM; eight policies; tokenizer format dispatch (`tokenizer.json` HF-fast vs `tiktoken.model` BPE — when each is required, when neither is required because cache_aware is text-based); air-gapped recipe (gateway ignores `HF_ENDPOINT`, mount tokenizer on PVC only when actually needed); K8s manifests with `model_id` labels + per-model RBAC; three HA mitigations (single+PDB / `sessionAffinity` / `--enable-mesh` CRDT sync); pitfalls (vLLM HTTP discovery registers empty labels, gRPC requires HF tokenizer (no tiktoken), gRPC probes need numeric ports, `sgl_router_*` → `smg_*` rename Dec 2025, over-engineered tokenizer init containers for cache_aware-only deployments).
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

The gateway is a stateless Rust process that accepts OpenAI-compatible HTTP and native gRPC traffic on a front port, maintains a registry of healthy backend workers, and forwards each request to one worker chosen by a **policy**. The full set: `cache_aware` (default — radix-tree prefix matching on **raw text**, no tokenizer needed), `random`, `round_robin`, `power_of_two`, `prefix_hash` (xxh3 over the first 256 token IDs against a consistent-hash ring — needs a working tokenizer), `consistent_hashing` (deterministic hash-ring), `bucket`, and `manual`. Workers are added either statically (`--worker-urls`), dynamically (`POST /workers`), or via Kubernetes service discovery (`--service-discovery --selector key=value --service-discovery-namespace ns`). The internal `WorkerType` enum has three variants — `Regular`, `Prefill`, `Decode` (PD-disagg) — and the `RuntimeType` enum has three — `Sglang`, `Vllm`, `External` (OpenAI-compatible non-local). Connection mode is `Http` or `Grpc`. The gRPC path hard-requires a HuggingFace tokenizer (so tiktoken-only models like Kimi K2/K2.6 must use HTTP). A separate Prometheus exporter on `--prometheus-port` (default 29000) emits 40+ `smg_*` metrics. Source: `sgl-model-gateway/src/core/worker.rs`, `src/core/steps/worker/local/discover_metadata.rs`, `src/policies/`, `src/server.rs`, `src/service_discovery.rs`.

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
  --host 0.0.0.0 --port 8080
```

**Note no `--tokenizer-path`.** With `cache_aware`, the gateway does not need a tokenizer — the radix tree stores raw text characters (`src/policies/cache_aware.rs:22`). If you only run cache_aware (or any non-`prefix_hash` policy in HTTP mode), you can skip `--tokenizer-path`, skip the model-files PVC on the gateway pod, and skip any init container that pulls tokenizer files from S3. A tokenizer is only needed for `prefix_hash`, `/v1/tokenize` / `/v1/detokenize`, or gRPC mode — and the last one is HF-tokenizer-only anyway. See `references/tokenizers.md` for the full matrix.

Cache-aware policy is a **text radix tree on the router side**, not a token-based hash. It does not query vLLM's internal cache state — it just steers same-prefix requests to the same replica so vLLM's *own* prefix cache hits. Set `--enable-prompt-tokens-details` on vLLM if you want OpenAI-standard `usage.prompt_tokens_details.cached_tokens` in responses (off by default).

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

The gateway only invokes a tokenizer in three situations:

1. **gRPC mode (always)** — gateway applies the chat template and sends token IDs to the worker. **gRPC hard-requires a HuggingFace tokenizer** (explicit downcast in `src/routers/grpc/utils.rs`); tiktoken-only models — Kimi K2/K2.6, DeepSeek-V3-style, GPT-OSS-style — **cannot use gRPC mode at all today**.
2. **HTTP mode + `prefix_hash` policy** — hashes the first 256 token IDs (xxh3) against a consistent-hash ring. Needs a working tokenizer.
3. **`/v1/tokenize`, `/v1/detokenize`** — gateway-side tokenization exposed to clients.

**`cache_aware` does NOT need a tokenizer.** The radix tree stores raw text characters (`src/policies/cache_aware.rs:22` comment, `tree.insert(text, …)`); routing is pure text-prefix matching. This is why operators successfully run Kimi K2.6 (tiktoken-only) behind cache_aware in production — no tokenizer ever runs on the gateway side. The tokenizer choice only matters when you're explicitly using one of the three paths above.

Pass via `--tokenizer-path /local/dir` or `--model-path /local/dir`. Both accept either an HF repo ID or a local directory. **Critical:** the Rust gateway's HF resolver does not honour `HF_ENDPOINT` (verified — zero hits in the source). In an air-gapped cluster with only an internal mirror, passing an HF repo ID will fail even with `HF_ENDPOINT` set — always pass a local path.

For the full format-dispatch matrix (what the loader does with `tokenizer.json` vs `tiktoken.model` vs SentencePiece vs GGUF vs custom Python tokenizers), the cl100k_base regex caveat for Kimi K2 / DeepSeek, and the K2.6 multimodal-file inventory, see `references/tokenizers.md`. For air-gapped specifics, see `references/air-gapped.md`.

## Hosting multiple replicas of the same model — the "10-20%" claim explained

The doc line `Cache hits may decrease by 10-20%` is widely misquoted. It applies to running **multiple gateway replicas in front of the same workers**, not to multiple worker replicas behind one gateway. Each gateway replica builds its own radix tree, the trees are not shared by default, so when a request lands on Gateway-A and the next same-prefix request lands on Gateway-B, B doesn't know A made the previous routing decision and may pick a different worker → cache miss. The 10-20% is the empirical penalty of HA-pairing the gateway itself.

**Three mitigations**, in increasing operational complexity:

1. **Single gateway replica + PDB**. Best cache locality. Brief unavailability during restarts (Rust binary, sub-second cold start). Default recommendation.
2. **`sessionAffinity: ClientIP` on the gateway Service**. Clients pin to one gateway replica; same-prefix requests stay on the same gateway → same routing decision. Simple, no gateway-side config. Hot-spot risk if a single client IP dominates traffic.
3. **`--enable-mesh` (gateway mesh sync, shipped in v0.3.x).** Gateway replicas form a gossip mesh and sync state via CRDTs (`crdts = "7.3"` Rust crate; the actual mesh implementation is the external `smg-mesh` crate). What gets synced across replicas: **worker registry, `cache_aware` radix tree, rate-limit window counters** (`src/policies/cache_aware.rs:67,324,428,453` for tree ops, `src/server.rs:753-759` for rate-limit window). What does **not** sync: **circuit-breaker state**, which stays per-replica by design. Eventual consistency. Default mesh port `39527`, default peer-discovery annotation `sglang.ai/ha-port` (`main.rs:903` — note: not `sglang.ai/mesh-port`, that name was a doc error). Two ways to wire peers on K8s: static `--mesh-peer-urls` (parsed as `IP:port` SocketAddr — hostnames and `grpc://` URLs **fail to parse**, and only `first()` is used as the gossip bootstrap peer per `main.rs:1099-1102`), or the K8s-native `--router-selector role=gateway` with the `sglang.ai/ha-port` annotation, which gets real pod IPs from the kube API. The K8s-native path is the practical one — see `references/kubernetes.md` "HA: multiple gateway replicas with mesh" for both recipes. The upstream doc warning about "10-20% cache hit reduction" predates this feature and is stale once mesh is on.

For **N worker replicas behind 1 gateway** (the common case), cache_aware routing is *the recovery mechanism*, not a penalty. But it's only beneficial when:

- Prefix sharing across requests is high (chat with system prompts, RAG with same retrieved chunks, code-review of same repo).
- Per-replica KV memory is **constrained** — abundant memory means vLLM's own prefix cache absorbs the win regardless of routing. See `sgl-project/sglang#17623` for an operator's reproduction where cache_aware ≈ k8s-RR with comfortable KV memory.
- Workers are CPU-pinned to keep tokenizer / scheduler latency from drowning the routing benefit.

If your workload is single-turn unique prompts, cache_aware ≈ random — that's fine, just don't expect a TTFT win.

## Air-gapped + local mirror — the recipe that works

**Worker pods always need the model snapshot mounted.** That part is non-negotiable — the worker loads weights, tokenizer, and chat template from disk. Specifically:

- A read-mostly model store (PVC or hostPath) that already contains the HF snapshot — `tokenizer.json` (or `tiktoken.model`), `tokenizer_config.json`, `chat_template.jinja` (or embedded in `tokenizer_config.chat_template`), `config.json`, weights.
- `HF_HOME` and `HF_HUB_CACHE` env vars pointing into that store.
- A **writable** `HF_HOME` location for any side-files vLLM/transformers caches at runtime — never point `HF_HOME` at a read-only PVC mount or initialization writes will fail.
- `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` on the **worker** (the gateway doesn't read these — it just doesn't try the network when given a local path).

**Gateway pods only need the snapshot if they actually use a tokenizer.** That means: if you run `prefix_hash`, expose `/v1/tokenize`, or use gRPC mode against an HF-tokenized model. For the most common case (HTTP + cache_aware), the gateway pod needs **no model files at all** — no PVC mount, no init container, no S3 pull. Cache_aware works on raw text from the request body.

If you do need a tokenizer on the gateway, gateway args reference the local path (no repo IDs — the Rust gateway does not honor `HF_ENDPOINT`):

```bash
--tokenizer-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/
```

For tiktoken-only models (Kimi K2/K2.6, DeepSeek-V3 family) the same flag works — point at the dir containing `tiktoken.model` + `tokenizer_config.json` + `chat_template.jinja`. The loader's directory scan picks the right format automatically.

For the full flag list, snapshot directory layout, ModelScope alternative, and gated-model-offline trap, see `references/air-gapped.md`. For tokenizer format dispatch, see `references/tokenizers.md`.

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

1. **HTTP service discovery registers vLLM workers with empty metadata, not rich metadata.** Discovery probes `/server_info` + `/model_info`, which vLLM 404s. The gateway falls through gracefully (`discover_metadata.rs:237-298` returns `Ok((empty_labels, None))`) and **the worker is still registered** — routing works, cache_aware works (text-based, no tokenizer needed), but you don't get worker-side label enrichment. If you specifically need `prefix_hash`, `/v1/tokenize`, or gRPC mode, pass `--tokenizer-path` explicitly since the gateway can't fetch it from the worker. For HTTP + cache_aware deployments, no tokenizer is needed at all. Static `--worker-urls` is also fine — pick whichever fits your autoscaling story.

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

12. **Over-engineered tokenizer init pipeline for cache_aware-only deployments.** Common shape: an init container pulls tokenizer files from S3 onto an emptyDir, the gateway mounts it, `--tokenizer-path` points at it. This is dead weight for HTTP + cache_aware — the radix tree never reads the loaded tokenizer. The pipeline adds boot latency, S3-credential plumbing, IRSA, and another failure mode. Drop the init container, drop the mount, drop the flag. Keep only if you actually call `/v1/tokenize`, run `prefix_hash`, or run gRPC mode. See pitfall #19 in `references/pitfalls.md`.

13. **gRPC mode silently rejects tiktoken-only models** — Kimi K2/K2.6, DeepSeek-V3-style, GPT-OSS-style. `src/routers/grpc/utils.rs:407` does `downcast_ref::<HuggingFaceTokenizer>()`; for tiktoken the downcast returns None and the request fails with *"gRPC router requires HuggingFace tokenizer with chat template support"*. Use HTTP mode for these models. Cache_aware works fine over HTTP regardless of tokenizer format.

For the extended troubleshooting list, see `references/pitfalls.md`. For tokenizer format dispatch, see `references/tokenizers.md`.

## Where to go next

- **Tokenizer formats** (`tokenizer.json` vs `tiktoken.model`, what the Rust loader accepts, why gRPC is HF-only, the cl100k_base regex caveat for Kimi K2 / DeepSeek, K2.6 multimodal-file inventory) → `references/tokenizers.md`
- **vLLM-specific deep-dive** (gRPC vs HTTP path matrix, `--enable-prompt-tokens-details`, DP modes, what vLLM endpoints the gateway sees) → `references/vllm-backend.md`
- **Air-gapped / mirror recipes** (what files the snapshot dir needs, env vars, ModelScope, gated-model HF_TOKEN trap) → `references/air-gapped.md`
- **Kubernetes deep-dive** (RBAC, label selectors, multi-port-per-pod, gRPC probes, ServiceMonitor relabelings, PDB, multi-gateway HA) → `references/kubernetes.md`
- **Full CLI flag reference** (all 80+ flags grouped by category, defaults, env-var equivalents) → `references/cli-flags.md`
- **`smg_*` Prometheus surface** (40+ metrics, alert recipes, PromQL for cache hit rate / queue depth / circuit breaker state) → `references/metrics.md`
- **Extended pitfalls** (the long list with reproductions and fixes) → `references/pitfalls.md`
- **Chat history backends** (`/v1/responses` and `/v1/conversations` — what they're for, when you actually need a non-`memory` backend, the privacy/proxy angle) → `references/history.md`
- **Reference manifests** (drop-in YAML for SGLang and vLLM workers behind a gateway) → `assets/sglang-gateway-deployment.yaml`, `assets/vllm-behind-gateway.yaml`

## Source of truth

- Upstream docs: https://docs.sglang.io/docs/advanced_features/sgl_model_gateway.md
- Source: https://github.com/sgl-project/sglang/tree/main/sgl-model-gateway
- Local clone: `~/projects/github.com/sgl-project/sglang/sgl-model-gateway/`
- Reference homelab manifests (untracked, repo-local): `~/projects/github.com/sgl-project/sglang/k8s-homelab/`
- Verify a flag with `--help`: `docker run --rm lmsysorg/sgl-model-gateway:v0.3.1 --help`. If this skill disagrees with `--help`, trust `--help` and freshen the skill.
