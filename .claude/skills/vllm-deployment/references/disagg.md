# Disaggregated prefill/decode — cross-pod KV transfer

**Disaggregated serving splits prefill and decode into separate pod pools.** Prefill is compute-bound; decode is bandwidth-bound. On the same GPUs they starve each other. Split them and bandwidth-bound decode pods run at high goodput while compute-bound prefill pods don't hold GPU memory hostage.

The price: KV cache must move from prefill → decode pods. That's what the connectors are for.

## The connector catalogue (in-repo)

Source: ``vllm` repo: vllm/distributed/kv_transfer/`

| Connector | File | Use case |
|---|---|---|
| **NixlConnector** | `nixl/connector.py` | NVIDIA-endorsed; RDMA via NIXL library; paired with NVIDIA Dynamo |
| **MooncakeConnector** | `mooncake/mooncake_connector.py` | Moonshot-originated; KV-store-first; RDMA (RoCE/IB) |
| **LMCacheConnector** | `lmcache_connector.py` | UChicago LMCache; tiered (GPU → CPU → NVMe → remote) |
| **MORI-IOConnector** | `moriio/moriio_connector.py` | AMD + Embedded LLM; network KV transfer |
| **P2PNcclConnector** | `p2p/p2p_nccl_connector.py` | Peer-to-peer via NCCL; simplest, no external dep |
| **OffloadingConnector** | `offloading_connector.py` | CPU/GPU offload scheduler (not cross-pod) |
| **HF3FSConnector** | `hf3fs/hf3fs_connector.py` | HuggingFace 3FS file-backed KV |

See also `vllm-caching` skill for connector tiers (CPU/NVMe offload) vs cross-pod (disagg).

## Example topologies in-repo

- ``vllm` repo: examples/online_serving/disaggregated_serving/` — XpYd, KV events, Mooncake proxy demos
- ``vllm` repo: examples/online_serving/disaggregated_prefill.sh` — one-node 2-engine launcher
- ``vllm` repo: examples/online_serving/disaggregated_serving_p2p_nccl_xpyd/` — P2P NCCL xPyD pattern

## NixlConnector (the current reference)

- **Docs**: https://docs.vllm.ai/en/stable/features/nixl_connector_usage/
- **NIXL lib**: https://github.com/ai-dynamo/nixl
- Pairs with NVIDIA Dynamo: Dynamo drives Nixl; vLLM's `NixlConnector` consumes it.

**Prefill pod spec excerpt**:

```yaml
args:
  - "--model=$(MODEL)"
  - "--kv-transfer-config"
  - '{"kv_connector":"NixlConnector","kv_role":"kv_producer","kv_rank":0,"kv_parallel_size":2}'
```

**Decode pod spec excerpt**:

```yaml
args:
  - "--model=$(MODEL)"
  - "--kv-transfer-config"
  - '{"kv_connector":"NixlConnector","kv_role":"kv_consumer","kv_rank":1,"kv_parallel_size":2}'
```

Prefill and decode pods need network line-of-sight. IB/RoCE recommended for production; cross-pod NCCL over Ethernet works but latency + bandwidth suffer.

## Mooncake

- **Repo**: https://github.com/kvcache-ai/Mooncake
- **Docs**: https://kvcache-ai.github.io/Mooncake/
- Integrated into vLLM v1 as of Dec 2025.
- KV-store-first architecture: KV cache lives in a standalone store; prefill writes, decode reads.
- Best suited for: large fleets where many prefill pods feed many decode pods; KV store acts as the demux.

## LMCache (tiered + disagg)

- **Docs**: https://docs.lmcache.ai/
- **Repo**: https://github.com/LMCache/LMCache
- Dual role: tiered offload within a pod (CPU/NVMe) + cross-pod disagg.
- Integrated into production-stack Helm chart — easiest path to a running disagg setup.
- Tutorial: https://blog.lmcache.ai/en/2025/04/11/shaping-nixl-based-pd-disaggregation-in-vllm-v1/

For KV-cache sizing (tiers, capacity math, offload distinction from disagg), see the `vllm-caching` skill.

## MORI-IO (April 2026)

- **Blog**: https://vllm.ai/blog/moriio-kv-connector (2026-04-07)
- AMD + Embedded LLM. Reports 2.5× goodput for single-node PD-disagg.
- Narrower adoption than NIXL/Mooncake as of Apr 2026; worth watching.

## The llm-d native path

llm-d's inference scheduler is **disagg-native**. Prefill pool, decode pool, EPP routes prefill prompts to prefill pods and decode continuations to decode pods, using KV-aware routing to land decode on the pod that holds the KV.

- llm-d architecture: https://llm-d.ai/docs/architecture
- KV-cache-aware routing: https://developers.redhat.com/articles/2025/10/07/master-kv-cache-aware-routing-llm-d-efficient-ai-inference
- Wide-EP + disagg at scale: https://developers.redhat.com/articles/2025/09/08/scaling-deepseek-style-moes-vllm-and-llm-d-using-wide-ep

For disagg with minimum assembly: use llm-d. Otherwise: pick a connector + deploy two vLLM pools + put production-stack router or a GAIE EPP in front.

## NVIDIA Dynamo's relation to vLLM disagg

Dynamo is the **orchestrator**. vLLM is the **engine**. NIXL is the **data plane**.

- Dynamo launches two vLLM pools (prefill + decode) with `NixlConnector` configured.
- Dynamo's scheduler decides which prefill pod handles a prompt and which decode pod continues.
- NIXL moves the KV between them over RDMA.

vLLM's `NixlConnector` works without Dynamo (production-stack supports it). Dynamo works with other engines (SGLang, TRT-LLM). They're complementary.

- Launch: https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/
- llm-d integration: https://developer.nvidia.com/blog/nvidia-dynamo-accelerates-llm-d-community-initiatives-for-advancing-large-scale-distributed-inference/

## Disagg status in upstream docs

As of April 2026, the disagg-prefill docs are still marked **experimental**:

- https://docs.vllm.ai/en/latest/features/disagg_prefill/

Production-grade path is via NixlConnector + llm-d or production-stack. The in-repo shell scripts are demo-grade.

## When NOT to disagg

Disagg pays off when prefill and decode starve each other. Indicators:

- P99 TTFT high while TPOT is fine → prefill-bound → split helps.
- TPOT high while TTFT fine → decode-bound → split helps.
- Both tolerable → **don't disagg yet**. It's operationally more complex. Single-pool is simpler.

Benchmark first (use `vllm-benchmarking` skill).

## Load-bearing network requirements

- **RDMA (IB or RoCE) strongly recommended** for cross-pod KV at scale. TCP+NCCL works but latency dominates KV transfer budget.
- Enable via NVIDIA Network Operator + Multus secondary network (see `references/multi-node.md` §RDMA).
- KV transfer bandwidth needed ≈ decode token rate × per-layer KV size. For DeepSeek-V3 at 2k tok/s: single-digit GB/s per stream. Tally across concurrency.

## Smoke test — disagg pods actually talking?

```bash
# Both pools up
kubectl get pods -l role=prefill
kubectl get pods -l role=decode

# Prefill logs show kv_producer role, decode shows kv_consumer
kubectl logs <prefill-pod> | grep -i 'kv_role'
kubectl logs <decode-pod>  | grep -i 'kv_role'

# NIXL/Mooncake/LMCache handshake
kubectl logs <prefill-pod> | grep -i 'nixl\|mooncake\|lmcache'

# A real request actually gets routed & continued
curl -fsS $GATEWAY/v1/chat/completions -d '{"model":"...","messages":[...]}'
```

## Next

- KV sizing + tiered offload within a pod: `vllm-caching` skill
- Routing prefill vs decode prompts: `references/routing.md`
- Multi-node TP underlying each pool: `references/multi-node.md`
