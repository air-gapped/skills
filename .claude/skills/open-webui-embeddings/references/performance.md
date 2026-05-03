# Performance baseline + quality verification

Load this file for sizing decisions and post-deployment health checks.

## Quality verification (cross-engine sanity)

For any TEI-backed model under LiteLLM, run a numerical-identity check before declaring it production-ready: same input through TEI direct, through LiteLLM, and (if available) through a second engine should produce numerically identical embeddings within fp16 noise floor (~1e-5). Mismatches indicate:

- LiteLLM injecting hidden parameters (the `encoding_format: null` trap manifests as a **400**, not a numerical drift, but other params can silently change pooling)
- Different chat-template / pre-tokenization on the embed side (some models normalise inputs differently)
- Different `dtype` (fp16 vs bf16 vs fp32) in the underlying model

For BGE-M3 specifically: a fixed input like `"hello"` should produce the same 1024-dim vector regardless of route. First 5 dims are a fast eyeball check.

## Performance baseline (BGE-M3 + BGE-Reranker-v2-m3 on consumer GPU)

Rough numbers from a single Ada-class consumer GPU at fp16 — for sizing hardware before deploying:

| Workload | Throughput |
|---|---|
| BGE-M3 embed at concurrency=1, single-text | ~65 req/s, 10 ms p50 |
| BGE-M3 embed at saturation (~150 k chars/s) | ~100 req/s |
| BGE-Reranker-v2-m3 at concurrency=1, query+10 docs | ~20 req/s, 40 ms p50 |
| BGE-Reranker-v2-m3 at burst (c=64, query+10 docs) | ~24 req/s |

Both models combined fit easily in 16 GB VRAM at fp16 (~3 GB total). On datacenter GPUs (H100/H200), expect 5–10× higher throughput; ratios remain similar.
