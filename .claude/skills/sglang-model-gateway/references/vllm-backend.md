# vLLM behind sgl-model-gateway — deep dive

This is the operator-side companion to the SKILL.md "Decision tree — vLLM behind the gateway" section. Read it when you're standing up vLLM workers fronted by `sgl-model-gateway` and need to know what each route does, what flags surface what data, and which DP-LB mode collides with the gateway.

## What vLLM exposes that the gateway can use

vLLM mounts FastAPI sub-routers from `vllm/entrypoints/openai/api_server.py:182` via `register_vllm_serve_api_routers(app)` and `register_models_api_router(app)`. The full surface, with what the gateway uses each route for:

| Route | Method | What the gateway uses it for | Notes |
|---|---|---|---|
| `/v1/models` | GET | List served model IDs; gateway can filter by `id` for selector matching | `ModelCard{id, root, max_model_len, permission}`. `id` defaults to `--served-model-name`, falls back to `--model`. |
| `/v1/chat/completions` | POST | Forward request to selected worker | OpenAI-compat. |
| `/v1/completions` | POST | Forward request | OpenAI-compat. |
| `/v1/embeddings`, `/v1/audio/transcriptions`, `/rerank`, `/score`, `/classify`, `/pooling`, `/v1/responses`, `/v1/messages` | varies | Forward (where applicable) | Conditional on vLLM `supported_tasks`. |
| `/health` | GET | Liveness/readiness probe | **Single endpoint.** No `/health/ready` or `/health/live` — vLLM does not separate them. Body is empty. |
| `/load` | GET | Workload signal | Returns `{"server_load": ...}` only when `--enable-server-load-tracking` was passed at boot. Off by default. |
| `/version` | GET | Sanity check | `{"version": "<vllm version>"}`. |
| `/metrics` | GET | Prometheus scrape (vLLM-side metrics, not gateway-side) | See `vllm-observability` skill. |
| `/server_info` | GET | **Gateway HTTP discovery probe** | **Gated behind `VLLM_SERVER_DEV_MODE=1`** (`instrumentator/__init__.py:26`). Production deployments will 404 this — meaning the gateway's HTTP service-discovery code path **fails** for vLLM. |
| `/reset_prefix_cache` | POST | Cache-bust on model-version rollout | Useful from the gateway via a webhook. |
| `/start_profile`, `/stop_profile`, `/sleep`, `/wake_up`, `/is_sleeping` | POST | — | Gateway doesn't use these. |

### Routes vLLM does **not** expose

If the gateway is configured to probe SGLang-style metadata routes, expect 404s for:

- `/get_server_info` and `/get_model_info` — SGLang-only.
- `/flush_cache` — vLLM equivalent is `POST /reset_prefix_cache`.
- `/start_expert_distribution_record`, `/stop_expert_distribution_record` — SGLang-only.

## `/health` exact behaviour

From `vllm/entrypoints/serve/instrumentator/health.py:22-33`:

```python
@router.get("/health", response_class=Response)
async def health(raw_request: Request) -> Response:
    client = engine_client(raw_request)
    if client is None:
        return Response(status_code=200)  # render-only, no engine
    try:
        await client.check_health()
        return Response(status_code=200)
    except EngineDeadError:
        return Response(status_code=503)
```

Empty body. `503` only on `EngineDeadError`. Importantly there is **no "warming" code path** — during weight load and CUDA-graph capture, the FastAPI app is not yet up at all (server starts after engine init). So:

- **Connection refused** → still booting.
- **`200` OK** → live AND ready, no separate probe needed.
- **`503`** → engine crashed.

This means `httpGet /health` on both readiness and liveness probes is fine, with sufficient `failureThreshold` to absorb the cold-load window.

## `--enable-prompt-tokens-details` — the missing flag for cache feedback

vLLM's `RequestOutput.num_cached_tokens` carries the prefix-cache hit count, but it's only surfaced in the OpenAI response when this flag is set. From `vllm/entrypoints/openai/cli_args.py:135`:

```python
enable_prompt_tokens_details: bool = False
"""If set to True, enable prompt_tokens_details in usage."""
```

When enabled, responses carry `usage.prompt_tokens_details.cached_tokens` per OpenAI naming. Without it, every response has `prompt_tokens_details: null` and the gateway has to fall back to scraping `vllm:prefix_cache_hits` / `vllm:prefix_cache_queries` from `/metrics`.

**Recommendation: always set `--enable-prompt-tokens-details` on vLLM workers fronted by a gateway.** It costs nothing, gives per-request cache feedback that smarter routing decisions can use later, and lets you compute "cache hit rate by route" in Grafana directly.

## vLLM data-parallel modes — pick one or the other, never both

From `vllm/entrypoints/cli/serve.py:64-104`:

```python
is_external_lb = (
    args.data_parallel_external_lb or args.data_parallel_rank is not None)
is_hybrid_lb = (
    args.data_parallel_hybrid_lb or args.data_parallel_start_rank is not None)
...
if args.api_server_count is None:
    if is_external_lb:
        args.api_server_count = 1
    elif is_hybrid_lb:
        args.api_server_count = args.data_parallel_size_local or 1
    else:
        args.api_server_count = args.data_parallel_size  # internal LB
```

| Mode | How to enable | Pod topology | Gateway compatibility |
|---|---|---|---|
| **Internal LB** (default) | `vllm serve --data-parallel-size N` | One Pod, N GPUs, one external port, ZMQ-fans-out internally | **Don't put a gateway in front.** Gateway sees one upstream → DP is invisible → loses per-replica routing intelligence. Use vLLM internal-LB *alone*. |
| **External LB** | `vllm serve --data-parallel-external-lb --data-parallel-rank=<i>` per Pod | One Pod per rank, each exposing its own port | **Recommended for gateway-fronted setups.** `api_server_count=1` per Pod. Gateway makes routing decisions per replica. |
| **Hybrid LB** | `vllm serve --data-parallel-hybrid-lb --data-parallel-start-rank=<i>` | One Pod per node, internal-LB local ranks, external-LB across nodes | For multi-node-per-replica wide-EP setups. Gateway sees per-node, vLLM handles per-rank within node. |

The docstring at `vllm/config/parallel.py:136-139` for external LB:

> "Whether to use 'external' DP LB mode... useful for a 'one-pod-per-rank' wide-EP setup in Kubernetes."

That's the configuration sgl-model-gateway expects.

## Multiple replicas of the same model — what changes

Inter-replica state inside vLLM: **none.** The KV/prefix cache lives entirely inside `KVCacheManager` (`vllm/v1/core/kv_cache_manager.py:106`) which is constructed per engine process. Block hashes, the LRU `block_pool`, and `prefix_cache_stats` are all in-process Python data structures. A second vLLM Pod cannot read the first Pod's prefix cache. (If you want shared prefix cache across replicas, see the `vllm-caching` and `lmcache-mp` skills — `LMCacheMPConnector` is the supported "external prefix store" path.)

Routing implication for the gateway:

- With N replicas behind round-robin and no sticky-on-prefix routing, the same prefix lands on a different replica each time → each replica builds its own copy → effective hit rate divides by ~N.
- Gateway's `cache_aware` policy claws this back by hashing the prompt prefix on the gateway side and steering same-prefix requests to the same worker. The radix tree is router-side-only — it doesn't query vLLM internals. So vLLM workers just need to keep their prefix caches enabled (default) and the gateway does the steering.
- The win is workload-dependent. With abundant KV memory per replica, vLLM's own prefix cache absorbs most of the win regardless. With tight KV memory, cache-aware routing matters a lot. See `sgl-project/sglang#17623` for an operator's reproduction where `cache_aware` ≈ k8s-RR with comfortable memory and started winning only after constraining `--gpu-memory-utilization`.

## Gateway worker-registration — three ways for vLLM HTTP workers

Service discovery (`--service-discovery --selector ...`) **does not work** for vanilla vLLM HTTP workers because the gateway probes `/server_info` + `/model_info` and gets 404. Three workarounds:

### 1. Static `--worker-urls`

```bash
sgl-model-gateway \
  --worker-urls http://vllm-0:8000 http://vllm-1:8000 http://vllm-2:8000 \
  --policy cache_aware \
  --tokenizer-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/ \
  --host 0.0.0.0 --port 8080
```

Simple, but requires a gateway restart on membership changes. Fine for static N-replica deployments.

### 2. Dynamic registration via `/workers` REST

```bash
# Add a worker
curl -X POST http://gateway:8080/workers \
  -H "Content-Type: application/json" \
  -d '{"url":"http://vllm-3:8000","model_id":"llama-3-8b","api_key":"<gateway-api-key>"}'

# List
curl http://gateway:8080/workers

# Get one
curl http://gateway:8080/workers/<worker_id>

# Remove
curl -X DELETE http://gateway:8080/workers/<worker_id>
```

A small operator (sidecar, DaemonSet, or Argo workflow) watching `Endpoints` for the vLLM Service and reconciling this list is the practical answer for autoscaling. Crude but works today.

### 3. Wait for vLLM-gRPC native (when available)

If the vLLM gRPC server (`CatherineSue/vllm#2`, referenced in `sgl-project/sglang#13120`) is available in your build, register over gRPC. The gateway auto-detects via `GrpcClient::connect(grpc_url, runtime_type)` — tries `sglang` first, falls back to `vllm`. Pin explicitly with `--runtime vllm` to skip the probe. Limitations until upstream catches up: no `n>1`, no logprobs, no multimodal, no LoRA, no PD-disagg.

## Cache-aware policy with vLLM workers — what actually happens

From `sgl-model-gateway/src/policies/cache_aware.rs:351-424` (paraphrased):

```rust
let result = tree.prefix_match_with_counts(text);
let match_rate = result.matched_char_count as f32 / result.input_char_count as f32;

let selected_idx = if match_rate > self.config.cache_threshold {
    // Cache hit path: find worker by URL
    workers.iter().position(|w| w.url() == &result.tenant)
} else {
    // Low cache match: use worker with minimum load
    healthy_indices.iter().min_by_key(|&&idx| workers[idx].load()).copied()
};
```

Key facts:

- **Character-level prefix matching, not token-level.** No tokenization on the routing decision (though the gateway tokenizes for `/v1/tokenize` if you call it).
- **In-memory radix tree per gateway process.** Multi-replica gateways have independent trees → the "10-20% reduction" the docs cite.
- **The router's mental model is what *it* thinks each worker has cached, not what vLLM actually has.** vLLM may evict under memory pressure faster than the router's tree decays.
- Below `--cache-threshold` (default 0.3 — 30% of prompt prefix matched), falls through to load-based selection.

Tune `--cache-threshold` per workload: lower (0.1) for short prompts where small prefix overlaps still matter, higher (0.5+) for long-context where you want more aggressive locality.

## Putting it together — a working vLLM-fronted-by-gateway recipe

```bash
# vLLM worker (one per Pod, N Pods)
vllm serve /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/ \
  --served-model-name llama-3-8b-instruct \
  --tensor-parallel-size 1 \
  --port 8000 \
  --enable-prompt-tokens-details \
  --disable-log-requests

# Gateway (one Deployment, in front of N vLLM Pods)
sgl-model-gateway \
  --worker-urls http://vllm-0.vllm-headless.sglang.svc:8000 \
                http://vllm-1.vllm-headless.sglang.svc:8000 \
                http://vllm-2.vllm-headless.sglang.svc:8000 \
  --policy cache_aware \
  --cache-threshold 0.3 \
  --tokenizer-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/ \
  --host 0.0.0.0 --port 8080 \
  --prometheus-host 0.0.0.0 --prometheus-port 29000 \
  --max-concurrent-requests 256 \
  --retry-max-retries 3 \
  --cb-failure-threshold 10
```

For full K8s manifests, see `assets/vllm-behind-gateway.yaml`.

## Useful issue refs

- `sgl-project/sglang#13120` — vLLM gRPC backend support. Limitation matrix lives here.
- `sgl-project/sglang#17623` — cache_aware-vs-k8s-RR reproduction; explains when cache_aware doesn't help.
- `sgl-project/sglang#13070` — multi-replica gateway HA confirmation.
- `sgl-project/sglang#13606` — `/v1/models` shape fix in gRPC mode (closed Dec 2025).

## Things to verify with your specific build

The exact JSON shape of streaming `prompt_tokens_details.cached_tokens` chunks should be smoke-tested against your vLLM version. The code path is at `vllm/entrypoints/openai/completion/serving.py:558-563` (non-streaming) — streaming wraps differently.
