# Improvement Backlog — vllm-caching

> **Local-only file. NOT committed yet** — captures live-lab findings staged
> for SKILL.md / sources.md. Reapply when ready to publish.

## Open — pending publish

### Hybrid-attention KV caching is unsolved on v0.19.1 + LMCache 0.4.4 (2026-04-25 Verda 2× H100 SXM5 session)

**Goal**: add Step 0 gate to backend decision tree + new "Backlog: hybrid-attention KV caching is unsolved" section to SKILL.md + 3 new bug rows + Verda evidence row in sources.md.

#### Proposed `SKILL.md` — Decision-tree Step 0 gate (insert before existing "Ask these in order:")

```markdown
**Step 0 — gate on attention shape.** If the model is hybrid (Gemma-4, Qwen3.5/3.6, gpt-oss, Llama-4 — has `layer_types: [sliding_attention, full_attention, ...]` OR `mtp.*`/`gdn.*` weights in `config.json`'s `text_config`), **STOP**. As of v0.19.1 + LMCache 0.4.4, NO connector reliably extends HBM with a DRAM/NVMe tier on hybrid attention. See "Backlog: hybrid-attention KV caching is unsolved" below for the full evidence map. Either run a non-hybrid model OR use NixlConnector 1P1D with a proxy (different topology). The questions below assume the model is NOT hybrid.

For non-hybrid models, ask in order:
```

#### Proposed `SKILL.md` — new section after "Open bugs to know before recommending offload"

```markdown
## Backlog: hybrid-attention KV caching is unsolved (2026-04-25)

**The most consequential finding for 2026 deploys:** every modern dense LLM ships with hybrid attention — alternating sliding-window + full-attention layers (Gemma-4, gpt-oss, Llama-4) OR gated delta-net + attention (Qwen3.5/3.6). vLLM groups these as "hybrid KV cache" and a connector must subclass `SupportsHMA` (Hybrid Memory Allocator) to coexist. **Most KV connectors don't.** Result: tier-extension caching (HBM → DRAM/NVMe) is broken for the entire 2026 model lineup.

Verified 2026-04-25 against vLLM v0.19.1 + LMCache 0.4.4 on Verda 2× H100 SXM5 80GB serving `Qwen/Qwen3.6-27B-FP8`:

| Connector | `SupportsHMA`? | Outcome on hybrid model | Evidence |
|---|---|---|---|
| **LMCacheConnectorV1** | ✗ | startup `ValueError: Hybrid KV cache manager is disabled but failed to convert KV cache specs to one unified type` | LMCache [#3106](https://github.com/LMCache/LMCache/issues/3106) (open 2026-04-22): "LMCache is currently unusable on any model that mixes attention types — every storage backend and connector reaches for `MemoryObj.tensor` which materializes a single-shape view and fails on the mismatched group." Reproduced live on Qwen3.6-27B-FP8 H100 SXM5. PR [#2926](https://github.com/LMCache/LMCache/pull/2926) (merged 2026-04-07) only fixed the MP server side. Connector layer still single-shape. |
| **LMCacheMPConnector** | ✗ | same `ValueError` | source `lmcache_mp_connector.py` v0.19.1: `class LMCacheMPConnector(KVConnectorBase_V1):` (no SupportsHMA) |
| **OffloadingConnector** | ✗ | requires `--disable-hybrid-kv-cache-manager`, then crashes if model needs HMA | source `offloading_connector.py` v0.19.1 |
| **MooncakeConnector** | ✗ | same hybrid-disable issue | source v0.19.1 |
| **MoRIIOConnector** | ✗ | same | source v0.19.1 |
| **FlexKVConnector** | ✗ | same | source v0.19.1 |
| **P2pNcclConnector** | ✗ | same | source v0.19.1 |
| **SimpleCPUOffloadConnector** | ✓ | starts on hybrid; runtime `AssertionError: External KV connector is not verified yet` (or per #39702 `Expected N hit tokens, got 0` TOCTOU race) on first KV transfer | vLLM [#39702](https://github.com/vllm-project/vllm/issues/39702) open 2026-04-13. Reproduced on Qwen3.6-27B-FP8 with `cpu_bytes_to_use: 100GiB` config — engine dies after CUDA-graph capture, on first long-context request. |
| **NixlConnector** (`kv_role=kv_both`) | ✓ | starts on hybrid; serves chat correctly. BUT `vllm:nixl_xfer_time_seconds_count = 0` after a same-prefix request to peer — **no auto peer discovery in symmetric kv_both mode** | designed for proxy-orchestrated 1P1D. Live verification: twin-pod, prime pod-a + same-prefix request to pod-b → both pods served from their own HBM, no cross-pod KV transfer happened |
| **NixlConnector** 1P1D (kv_producer + kv_consumer + toy_proxy) | ✓ | works on hybrid + cross-pod | proven on lab Qwen3-4B (which is non-hybrid), pattern is proxy-driven; should generalize to hybrid since SupportsHMA is declared |
| **Native** `--kv-offloading-size` | implicit ✗ | fail-to-start | vLLM [#36463](https://github.com/vllm-project/vllm/issues/36463) open: Qwen3.5 fails with native CPU offload while Qwen3 (non-hybrid) works |

**Operational verdict for hybrid models on v0.19.1:** there is no production-ready single-pod tier-extension (HBM→DRAM/NVMe). Three options:

1. **Run a non-hybrid model.** Pure-attention 2025 models still serve fine: Llama-3.3-70B-FP8, DeepSeek-V2-Lite-FP8 (MLA), Qwen2.5-72B-FP8.
2. **Use NixlConnector 1P1D with a proxy** — doesn't extend HBM but gives separate prefill and decode pools, so a pod can specialize its KV layout to its phase. Different scaling story.
3. **Wait for upstream fix.** Track LMCache #3106 (multi-shape connector path), vLLM #39702 (SimpleCPUOffloadConnector TOCTOU race), and any LMCacheConnectorV1 commit that adds `, SupportsHMA` to its class declaration.

**What worked (2026-04-25 measurements, baseline values, no caching tier):**
- `Qwen/Qwen3.6-27B-FP8` on TP=1 single H100 SXM5 80GB:
  - GPU KV cache: 174,048 tokens; max concurrency at 262K full context: 2.6×
  - With CUDA graphs (no `--enforce-eager`), c=10 ISL=4k OSL=200: ITL avg **17.9 ms p50 / 22.5 ms p99**, output throughput **393 tok/s** aggregate, **56 tok/s/user**
- TP=2 across both H100 SXM5 80GB:
  - GPU KV cache: 447,664 tokens; max concurrency at 262K full context: 6.7×
  - With CUDA graphs c=10 ISL=4k: ITL avg **14.3 ms**, request throughput **2.42 req/s**
- Eager mode collapses ITL ~20× (358 ms vs 17.9 ms) — never use `--enforce-eager` on datacenter HW
```

#### Proposed `SKILL.md` — three new rows in "Open bugs" table (after #40259 row)

```markdown
| [#3106](https://github.com/LMCache/LMCache/issues/3106) | LMCache/LMCache | open | LMCache unusable on any hybrid-attention model (Gemma-4, Qwen3.5/3.6, gpt-oss, Llama-4). `MemoryObj.tensor` materializes single-shape view, fails on multi-group buffer. Filed 2026-04-22, no fix yet on main | Use a non-hybrid model OR switch to NixlConnector 1P1D (different topology, cross-pod KV transfer instead of in-pod tier extension) |
| [#2845](https://github.com/LMCache/LMCache/issues/2845) | LMCache/LMCache | open | "Hybrid models like qwen3.5 9B are not supported" | same as #3106 |
| [#2927](https://github.com/LMCache/LMCache/issues/2927) | LMCache/LMCache | open | vLLM fails to start with LMCache + Qwen3-Coder-Next-FP8 (nightly image) | same as #3106 |
```

#### Proposed `references/sources.md` — append new section

```markdown
## 2026-04-25 update — Verda 2× H100 SXM5 hybrid-attention sweep

| Source | URL | Last verified | Notes |
|---|---|---|---|
| LMCache #3106 multi-shape KV layout feature | https://github.com/LMCache/LMCache/issues/3106 | 2026-04-25 | Open. Filed 2026-04-22. "LMCache currently unusable on any model that mixes attention types" — `MemoryObj.tensor` materializes single-shape view, fails on multi-group buffers (Gemma-4 50 sliding + 10 full layers exact case). PR #2926 (merged 2026-04-07) only fixed MP server; connector layer still broken. Cited in SKILL.md "Backlog: hybrid-attention KV caching is unsolved". |
| LMCache #2845 hybrid models qwen3.5 9B not supported | https://github.com/LMCache/LMCache/issues/2845 | 2026-04-25 | Open. Same root issue as #3106. Cited in SKILL.md backlog. |
| LMCache #2927 Qwen3-Coder-Next-FP8 fails to start | https://github.com/LMCache/LMCache/issues/2927 | 2026-04-25 | Open. Cited in SKILL.md backlog. |
| Live verification — Verda 2× H100 SXM5 80GB on-demand + Qwen/Qwen3.6-27B-FP8 + vLLM v0.19.1 + LMCache 0.4.4 | n/a (Verda on-demand) | 2026-04-25 | **LMCacheConnectorV1 + Qwen3.6 hybrid:** `ValueError: Hybrid KV cache manager is disabled but failed to convert KV cache specs to one unified type` at engine init. Reproduced after pip-upgrading lmcache 0.4.3 → 0.4.4 in container — PR #2926 doesn't reach connector code path. Confirms #3106. **SimpleCPUOffloadConnector (has SupportsHMA):** boots clean on hybrid; `AssertionError: External KV connector is not verified yet` raised from `EngineCore` on first long-context request — same class as #39702. **NixlConnector kv_role=kv_both:** boots and serves chat correctly on hybrid; `vllm:nixl_xfer_time_seconds_count = 0` after a same-prefix request to peer pod confirms no auto peer discovery in symmetric mode (designed for proxy-orchestrated 1P1D). **Plain TP=2 baseline (no kv_transfer_config):** 174k tokens KV per H100 single-pod; 447k tokens combined TP=2; ITL avg 14-18 ms, output throughput 393 tok/s aggregate at c=10 ISL=4k. `--enforce-eager` collapses ITL ~20× — never use on datacenter HW. |
| vLLM v0.19.1 source — connector SupportsHMA audit | https://github.com/vllm-project/vllm/tree/v0.19.1/vllm/distributed/kv_transfer/kv_connector/v1 | 2026-04-25 | Audit of `class XConnector(...)` declarations: `SimpleCPUOffloadConnector(KVConnectorBase_V1, SupportsHMA)` ✓; `NixlConnector(KVConnectorBase_V1, SupportsHMA)` ✓; `LMCacheConnectorV1(KVConnectorBase_V1)` ✗; `LMCacheMPConnector(KVConnectorBase_V1)` ✗; `MooncakeConnector` ✗; `MoRIIOConnector(KVConnectorBase_V1)` ✗; `OffloadingConnector(KVConnectorBase_V1)` ✗; `FlexKVConnectorV1(KVConnectorBase_V1)` ✗; `P2pNcclConnector(KVConnectorBase_V1)` ✗. Only Simple + Nixl declare hybrid support. |
| vLLM image-tag freshness rule | n/a (operator pushback 2026-04-25) | 2026-04-25 | `vllm/vllm-openai:v0.19.0` (Apr 3) bundles lmcache 0.4.2; `:v0.19.1` (Apr 18) bundles lmcache 0.4.3; v0.20.0 GitHub release Apr 23, Docker image not yet pushed at session time. Always run `gh release list --repo vllm-project/vllm` AND `skopeo list-tags docker://vllm/vllm-openai` before picking; don't default to memorized known-good tag. |
| Docker `-v /root/cache:/root/.cache` mount as default | n/a (operator pushback 2026-04-25) | 2026-04-25 | Cold restart on H100 + Qwen3.6-27B-FP8 + TP=2 = ~5 min, mostly DeepGEMM SM_90A FP8 GEMM JIT (cicc nvcc) + torch.compile inductor + CUDA graph capture. With persistent `/root/.cache` mount the same restart is ~50 s. Mount the WHOLE cache, not just `/root/.cache/huggingface`. |
```

## Resolved this pass (2026-04-25)

- 5e628ba `docs(vllm-caching): cross-reference nvidia-nixl skill for transport-level details` — 4 cross-references from vllm-caching → nvidia-nixl skill. Scoped vllm-caching to vLLM-side wiring; transport-level details delegated to nvidia-nixl.
