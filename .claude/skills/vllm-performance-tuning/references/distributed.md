# NCCL / DCGM + PD disaggregation

Load when: multi-node deploy, IB/RoCE fabric tuning, DCGM monitoring for perf triage, or deciding whether to split prefill and decode across nodes.

## NCCL baseline

**NVIDIA's explicit guidance:** "In general, users should not need to tune or set NCCL environment variables to achieve peak performance." ([GB200 multi-node tuning](https://docs.nvidia.com/multi-node-nvlink-systems/multi-node-tuning-guide/nccl.html)). NCCL ≥2.28 auto-detects GB200 NVLink domains and picks the algorithm.

### Critical exceptions for vLLM multi-node

- `NCCL_CUMEM_ENABLE` — **do NOT set to 0 on GB200/NVL.** Setting 0 disables multi-node NVLink and forces TCP/IB. vLLM [PR #16992](https://github.com/vllm-project/vllm/pull/16992) tuned the defaults.
- `NCCL_NET_GDR_C2C=1` — recommended on GB200 for GDR-C2C path.
- `NCCL_NVLS_ENABLE=1` — NVLink SHARP; default-on where supported (NVLink v3+).

### InfiniBand / RoCE for H100 / H200

| Var | Purpose |
|---|---|
| `NCCL_IB_HCA` | Comma list with `:port` (e.g. `mlx5_0:1,mlx5_1:1,...,mlx5_7:1`) |
| `NCCL_IB_GID_INDEX` | RoCE GID index; match `show_gids` output |
| `NCCL_NET_GDR_LEVEL` | PIX / PHB / SYS distance for GPUDirect RDMA |
| `NCCL_IB_CUDA_SUPPORT` | GDR on/off; auto-detects |
| `NCCL_P2P_DISABLE=0` | GPU-to-GPU direct transfers |

Debug: `NCCL_DEBUG=INFO vllm serve ... 2>&1 | grep -i "IB\|InfiniBand"`. Missing IB detection = 30-50% throughput loss.

### vLLM-specific env vars

| Var | Default | Purpose |
|---|---|---|
| `VLLM_NCCL_SO_PATH` | None | Explicit path to custom NCCL `.so`; else vLLM searches system paths |
| `VLLM_NCCL_INCLUDE_PATH` | None | Headers for compilation |
| `VLLM_USE_RAY_COMPILED_DAG_CHANNEL_TYPE` | `auto` | `auto` / `nccl` / `shm`. Set `nccl` for IB / GPU-Direct-RDMA |
| `VLLM_USE_RAY_COMPILED_DAG_OVERLAP_COMM` | `false` | Overlap comm with compute in Ray DAG |
| `VLLM_USE_RAY_WRAPPED_PP_COMM` | `true` | Ray wrapper for PP all-reduce |

### Distributed executor backend

| `--distributed-executor-backend` | Use when |
|---|---|
| `mp` (default) | Single-node multiprocessing. Fast, no RPC |
| `ray` | Multi-node; adds RPC latency. Only use when genuinely multi-node |

**Do not use Ray for single-node** — slower than `mp` due to serialization.

### AWS EFA / cloud-specific

EFA installer bundles NCCL-OFI-plugin; works transparently with NCCL ≥2.18. IB / RoCE for on-prem — verify `ibstat` atomic capabilities (32/64/128-bit) before deploying DeepEP.

## DCGM — what to watch

Source: [DCGM field IDs](https://docs.nvidia.com/datacenter/dcgm/latest/dcgm-api/dcgm-api-field-ids.html).

| Field | Meaning | Action |
|---|---|---|
| `DCGM_FI_PROF_SM_OCCUPANCY` | Ratio of resident warps per SM | **The real saturation signal, not `GPU_UTIL`** |
| `DCGM_FI_PROF_SM_ACTIVE` × `DCGM_FI_PROF_GR_ENGINE_ACTIVE` | % SMs in use when GPU active | Low + high GPU_UTIL = lots of idle SMs |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` | TensorCore activity | Low on GEMM-bound workload = memory-bound |
| `DCGM_FI_DEV_POWER_USAGE` | Draw watts | Rack-level health |
| `DCGM_FI_DEV_GPU_TEMP` | °C | Thermal throttling risk |
| `DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL` | NVLink GB/s | Bottleneck check for MoE all-to-all |

**DCGM exporter + vLLM Prometheus + Grafana** = the standard pattern. See `vllm-observability` for dashboard setup.

## PD disaggregation (prefill/decode split)

Source: [disagg prefill docs](https://docs.vllm.ai/en/latest/features/disagg_prefill/).

### Connector catalog

| Connector | Transport | Use |
|---|---|---|
| `SharedStorageConnector` | filesystem | dev-only; slowest |
| `LMCacheConnector` | tiered HBM+CPU+NVMe+GDS | reusable KV (RAG, multi-turn) |
| `NixlConnector` | UCX (RDMA/IB, RoCE, TCP, NVMe-oF, S3) | NVIDIA NIXL, open-sourced GTC 2025 |
| `MooncakeConnector` | RDMA | Kimi Moonshot's transfer layer |
| `MultiConnector` | compose | tiered or fallback chains |

### NIXL flow (from [LMCache blog 2025-04-11](https://blog.lmcache.ai/en/2025/04/11/shaping-nixl-based-pd-disaggregation-in-vllm-v1))

P and D register KV regions; P pushes directly via UCX; D polls readiness. Router decides P-node or D-node. vLLM v1 NIXL role selected via `--kv-transfer-config` with `nixlRole={sender,receiver}`.

**NCCL vars don't apply to NixlConnector** — it uses UCX, not NCCL. Configure UCX: `UCX_TLS=all` OR `rc,ud,sm,^cuda_ipc`.

### When PD disagg is worth it

- **Large models** (≥gpt-oss-120B). Not worth for gpt-oss-20B or 8B-dense.
- **Long inputs / short outputs** (10K ISL / 1K OSL — RAG, batch summarization).
- **P95 ITL SLO too tight** for mixed prefill+decode interference.
- **Separate scaling** — prefill is compute-bound, decode is bandwidth-bound; scale independently.

### When PD disagg is NOT worth it

- Short prompts (200 ISL / 200 OSL) — KV-transfer time > prefill-on-same-GPU time.
- Small models (gpt-oss-20B, 8B-dense) — same.
- Prefill units saturated — disagg becomes queueing bottleneck.
- No RDMA / NVLink fabric between P-nodes and D-nodes.

### Production deployment patterns

- **vLLM production-stack + llm-d** — LeaderWorkerSet K8s orchestration. Configs at tag `2025-05-27-v1`.
- **LMSYS DeepSeek-V3 at 96× H100** — canonical case study ([LMSYS blog](https://www.lmsys.org/blog/2025-05-05-large-scale-ep/)). 4 nodes prefill EP32, 9 nodes decode EP72.
- **Anyscale Ray Serve LLM** — Python builder pattern for wide-EP + disagg ([anyscale.com/blog/ray-serve-llm-anyscale-apis-wide-ep-disaggregated-serving-vllm](https://www.anyscale.com/blog/ray-serve-llm-anyscale-apis-wide-ep-disaggregated-serving-vllm)).

### Benchmark mode

`vllm bench serve --disagg-split …` to measure P and D separately.

## Goodput — the SLO-gated throughput metric

Definition (DistServe paper, [haoailab.com/blogs/distserve](https://haoailab.com/blogs/distserve)):
> "The maximum request rate per second that the system can sustain while meeting a specified SLO."

**Goodput = tok/s/GPU under SLO**, not raw tok/s.

### Translating SLOs to vLLM knobs

| SLO | Knob to watch |
|---|---|
| P95 TTFT ≤ 200ms | `num_requests_waiting` = 0 at peak rate; raise `max_num_batched_tokens` to absorb prefill bursts; enable prefix caching; consider PD disagg |
| P95 TPOT ≤ 50ms | raise `max_num_seqs` only until TPOT hits ceiling; `--async-scheduling` on; shrink `max_num_batched_tokens` (2048 sweet spot) |
| P95 ITL ≤ 30ms | tune `--cuda-graph-sizes` to cover running batch sizes; no eager fallback at peak batch |
| Per-GPU tok/s at SLO | **goodput** — the headline number |

vLLM ships first-class goodput in `vllm bench serve --goodput ttft:200 tpot:50`. Full methodology in `vllm-benchmarking`.

### SemiAnalysis InferenceMAX framing

Pareto-frontier methodology: sweep request rate, plot (tok/s/GPU, latency) pairs, SLO line at e.g. P95 TTFT ≤ 200ms + P95 TPOT ≤ 50ms gates which throughput points count ([newsletter.semianalysis.com/p/inferencemax](https://newsletter.semianalysis.com/p/inferencemax-open-source-inference)). Dashboard: [inferencex.semianalysis.com](https://inferencex.semianalysis.com/).

## Common distributed-tuning mistakes

1. **`NCCL_CUMEM_ENABLE=0` on GB200** — disables NVLink, silent 30-50% drop.
2. **Using Ray backend for single-node** — slower than `mp`.
3. **No IB detection check** — fallback to Ethernet. Always `NCCL_DEBUG=INFO` on first boot.
4. **Disagg prefill for small models** — KV transfer cost exceeds prefill savings.
5. **Watching `DCGM_FI_DEV_GPU_UTIL`** instead of `SM_OCCUPANCY` — misleading for tensor-core-bound workloads.
6. **PD disagg with no RDMA fabric** — TCP fallback serializes. Verify UCX path with `ucx_info -d`.
