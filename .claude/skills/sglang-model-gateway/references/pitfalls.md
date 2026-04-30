# Extended pitfalls — sgl-model-gateway

Beyond the top-10 in SKILL.md. Each entry: symptom → diagnosis → fix.

## 1. HTTP service discovery silently registers vLLM workers without metadata

**Symptom:** `--service-discovery --selector app=vllm` enabled. Gateway logs show "discovered 3 workers" but `/v1/models` returns empty or stale, and routing fails with "no healthy workers".

**Diagnosis:** Service discovery probes `/server_info` + `/model_info` to enrich worker metadata (model name, max-context, tokenizer info). vLLM 404s both. Gateway either marks the workers unhealthy outright, or registers them with empty metadata that causes routing to fail.

**Fix:** Use `--worker-urls http://vllm-svc:8000` instead, optionally with a sidecar reconciler watching Endpoints. Or wait for vLLM gRPC fork support (PR #13120).

## 2. Service discovery picks up workers from other models

**Symptom:** Gateway routes requests for model A to a worker actually serving model B; clients get the wrong responses or 4xx errors about unknown models.

**Diagnosis:** Selector too loose, e.g. `--selector app.kubernetes.io/name=sglang-worker` matches all SGLang workers in the namespace, regardless of model.

**Fix:** Always include the `model_id` discriminator: `--selector model_id=<the-one-model>`. Per the user's homelab pattern, `model_id` is the only label that uniquely identifies a worker pool.

## 3. Cache-aware policy gives worse hit rate than round-robin

**Symptom:** TTFT P99 is higher with `--policy cache_aware` than `--policy round_robin`.

**Diagnosis:** Three sub-causes:
- (a) Workload has no prefix sharing (uniform random prompts). Cache-aware degrades to load-based selection below `--cache-threshold`, but the radix-tree maintenance cost adds overhead with no benefit.
- (b) `--cache-threshold` set too high → falls through to load-based for most requests, so the radix tree is just dead weight.
- (c) Workers have abundant KV memory; vLLM's own prefix cache absorbs the win, and any routing imbalance hurts more than the cache win.

**Fix:**
- For uniform-random workloads, use `--policy round_robin` or `--policy power_of_two`.
- For prefix-sharing workloads with comfortable memory, lower `--cache-threshold` to 0.1 to make cache-aware kick in earlier.
- For prefix-sharing workloads with tight memory, `cache_aware` should win — verify `vllm:gpu_cache_usage_perc > 0.8` on workers.

See `sgl-project/sglang#17623` for an operator's reproduction.

## 4. Gateway ignores `HF_ENDPOINT`, breaks in air-gapped clusters

**Symptom:** Gateway pod fails to start with DNS resolution errors for `huggingface.co`, despite `HF_ENDPOINT=https://internal-mirror.example.com` set.

**Diagnosis:** The Rust gateway uses the `hf-hub` crate, which (as of v0.3.x) does not honour `HF_ENDPOINT`. Only Python `huggingface_hub` does.

**Fix:** Pass a local snapshot directory to `--model-path` / `--tokenizer-path`. Mount the snapshot via PVC. `HF_ENDPOINT` is irrelevant — the resolver should never need to touch the network.

## 5. gRPC liveness probe fails with "named ports not supported"

**Symptom:** Pod stuck in CrashLoopBackOff, kubelet event: `gRPC probe with named port "grpc" not supported`.

**Diagnosis:** Kubernetes `kubelet` requires numeric port numbers for gRPC probes — a constraint of the gRPC probe API.

**Fix:** Use the numeric port:

```yaml
readinessProbe:
  grpc:
    port: 8080      # numeric
```

Not:

```yaml
readinessProbe:
  grpc:
    port: grpc      # named — kubelet rejects
```

Named ports work fine for `httpGet` probes.

## 6. Multi-replica gateway HA → cache hit rate drops 10-20%

**Symptom:** After scaling gateway from 1 → 2 replicas, TTFT regresses ~10-20%.

**Diagnosis:** Each gateway replica owns an independent radix tree. Two same-prefix requests landing on different gateway replicas are routed independently, so worker selection diverges → split prefix cache → lower hit rate.

**Fix:** Two options:
- Run **single-replica with PDB** — accept brief unavailability during restarts. Best cache hit rate.
- Run **N replicas with `sessionAffinity: ClientIP`** on the gateway Service — clients pin to one gateway, so same-prefix requests stay on the same gateway. Trades hot-spot risk for cache hit rate.

The "10-20%" doc claim refers to multi-replica *gateway* — not multi-replica *worker*. Don't conflate.

## 7. `POST /workers` rejected with 401

**Symptom:** Dynamic worker registration via `/workers` REST returns 401 Unauthorized.

**Diagnosis:** When `--api-key` is set on the gateway, dynamic registration requests must include the key. The CLI `--worker-urls` flag bypasses auth (initial registration), but the REST endpoint is auth'd like any client request.

**Fix:** Pass `api_key` in the body or `Authorization: Bearer <key>` header:

```bash
curl -X POST http://gateway:8080/workers \
  -H "Authorization: Bearer <gateway-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://vllm-3:8000","model_id":"llama-3-8b"}'
```

## 8. Grafana dashboard goes silent after Dec 2025 upgrade

**Symptom:** Upgraded to `lmsysorg/sgl-model-gateway:v0.3.x`. Old Grafana dashboards show "no data".

**Diagnosis:** Metric prefix renamed from `sgl_router_*` to `smg_*`. Dashboards targeting old prefix see nothing.

**Fix:** Search-and-replace `sgl_router_` → `smg_` in dashboard JSON and alert rules. Some metric names also changed slightly (e.g. `_ttft_` was previously `_time_to_first_token_`). Dump current metric list:

```bash
kubectl exec -n sglang gateway-pod -- curl -s http://localhost:29000/metrics | grep '^# TYPE smg_'
```

## 9. PD-disagg worker pools mix vLLM and SGLang

**Symptom:** Gateway in PD mode with `--prefill-selector app=vllm-prefill --decode-selector app=sglang-decode`. Requests fail with cryptic gRPC errors.

**Diagnosis:** PD-disaggregation requires SGLang's bootstrap-port mechanism (`sglang.ai/bootstrap-port` annotation) and SGLang-specific RPCs between prefill and decode. vLLM does not implement this. PR #13120 explicitly calls out **no PD with vLLM**.

**Fix:** Both prefill and decode pools must be SGLang workers. Or run a non-PD gateway and let workers handle full pipeline.

## 10. Gateway eats memory because tokenizer cache is unbounded

**Symptom:** Gateway pod OOMs after a few hours. Memory grows steadily.

**Diagnosis:** `--tokenizer-cache-enable-l1` was enabled with default `--tokenizer-cache-l1-max-memory 52428800` (50 MiB), but actual memory usage exceeds this — likely a leak or accounting bug — or you mistakenly set L1 to a huge value.

**Fix:** Either disable L1 (it's `false` by default; only enable for very high tokenization throughput), or cap aggressively:

```bash
--tokenizer-cache-enable-l0 \
--tokenizer-cache-l0-max-entries 5000 \
--tokenizer-cache-enable-l1 \
--tokenizer-cache-l1-max-memory 104857600   # 100 MiB
```

Watch `container_memory_working_set_bytes` for the gateway pod and confirm it plateaus.

## 11. Service discovery with cluster-wide selector hits API server rate limits

**Symptom:** Gateway logs show repeated "kube watch closed by server" with 429 status. Discovery flaps.

**Diagnosis:** Using `ClusterRole` for cluster-wide pod watching, in a large cluster (10k+ pods), can hit kube-apiserver rate limits on the watch.

**Fix:** Scope to a single namespace via `Role` + `RoleBinding` + `--service-discovery-namespace <ns>`. If you genuinely need cross-namespace, scope the `ClusterRole` to a label selector via `resourceSelector` (Kubernetes 1.31+).

## 12. Request body too large

**Symptom:** Long-context requests (~100k token prompts) get 413 Request Entity Too Large from the gateway.

**Diagnosis:** Default body size limit. Each layer in the path (gateway, optional Ingress, vLLM) has a body cap.

**Fix:** Bump on all hops. Gateway typically inherits a sensible default but check `--max-request-body-bytes` if present. For Nginx Ingress: `nginx.ingress.kubernetes.io/proxy-body-size: "100m"`. For vLLM: `--max-model-len` must accommodate the request, no separate body limit.

## 13. Streaming response stalls when worker is slow

**Symptom:** SSE stream from `/v1/chat/completions?stream=true` hangs, then disconnects after 60-180s.

**Diagnosis:** Idle-timeout on a long-thinking model. The gateway forwards SSE chunks as they arrive; if the worker is slow on first token (cold cache, long prompt processing), the gateway's idle timeout may fire before the first chunk.

**Fix:**
- Bump `--retry-max-backoff-ms` and check streaming-specific timeouts (vary by version).
- Set `--cb-failure-threshold` higher (15-20) so a single slow request doesn't open the breaker.
- If using K8s Ingress in front, bump `proxy-read-timeout` to 600s.
- For very long prompts, prefer chunked input or non-streaming endpoints.

## 14. Worker registration race during gateway startup

**Symptom:** Gateway starts faster than workers; first requests return 503 "no healthy workers" before workers register.

**Diagnosis:** With service discovery, gateway has to wait for kube-apiserver `watch` to deliver Pod events and complete probing.

**Fix:**
- Set `readinessProbe` on the gateway with `--health-success-threshold 2` plus a custom check that requires at least 1 healthy worker. The default `/health` returns 200 even with no workers — clients can hit the gateway too early.
- Or accept the brief startup window and rely on client retries.

## 15. Mixing different `--served-model-name` values across replicas

**Symptom:** `/v1/models` flickers between two model IDs every few seconds.

**Diagnosis:** vLLM workers behind the gateway have different `--served-model-name` values. The gateway reports whichever it last queried. From `vllm/config/model.py:1841-1851`, `get_served_model_name` falls back to `--model` value when `--served-model-name` is absent.

**Fix:** Ensure all replicas pass the same `--served-model-name`. Even in dev: pin it explicitly.

## 16. Reasoning parser silently swallows the entire response

**Symptom:** Some chat completion responses come back with empty content; only the chain-of-thought is visible (or vice versa).

**Diagnosis:** `--reasoning-parser deepseek-r1` (etc.) splits the response into `reasoning` and `content` fields. If the model didn't emit the expected delimiter (e.g., `</think>`), the parser fails open or shut depending on the model and may keep the entire response in one field.

**Fix:** Either match the parser to the exact model variant (DeepSeek-R1 vs distilled vs non-reasoning fine-tunes), or omit `--reasoning-parser` and pass the raw text to the client.

For the parser × model matrix, see the `vllm-reasoning-parsers` skill.

## 17. Tool-call parser corrupts JSON tool calls

**Symptom:** Tool calls return malformed JSON or string-escaped output.

**Diagnosis:** `--tool-call-parser json` (etc.) tries to extract structured tool calls. If the model emits a slightly different format than the parser expects (e.g., trailing commas, different escape conventions), parsing degrades.

**Fix:** Match parser to model exactly. For Qwen-Coder, use `pythonic`. For DeepSeek-R1, omit (no native tool calling). See `vllm-tool-parsers` skill for the matrix.

## 18. mTLS handshake fails with "unknown CA"

**Symptom:** Gateway logs `tls handshake error: unknown CA` when connecting to upstream workers.

**Diagnosis:** `--ca-cert-path` not set, or set to a CA that doesn't sign the worker certs.

**Fix:** Mount the CA bundle and pass `--ca-cert-path /etc/tls/ca.crt`. For Istio mesh, use SPIRE/cert-manager-issued certs and align the trust roots between gateway and workers.
