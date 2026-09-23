# NCCL / DCGM + PD disaggregation

Load when: multi-node deploy, IB/RoCE fabric tuning, DCGM monitoring for perf triage, deciding whether to split prefill and decode across nodes, or triaging a throughput change across a v0.29.0 upgrade.

## Before tuning NCCL: v0.29.0 flipped an all-reduce default

**FlashInfer all-reduce is ON by default for TP CUDA groups from v0.29.0**
([#52998](https://github.com/vllm-project/vllm/pull/52998)). It is a behaviour change on an unchanged
config, so a TP deployment can move on throughput or latency across that upgrade
with nothing in the launch command touched. Opt out with
`VLLM_ALLREDUCE_USE_FLASHINFER=0`.

**Check this before attributing a post-upgrade delta to NCCL.** The env vars
below tune the NCCL path; on v0.29.0+ the collective may not be taking it. Bisect
by setting the opt-out and re-running the same benchmark — if the delta closes,
it is the new default, not fabric tuning.

## v0.30.0: opt-in FlashInfer PCIe IPC all-reduce for NVLink-less boxes

**`VLLM_ALLREDUCE_USE_FLASHINFER_PCIE_IPC=1`** (default `0`, opt-in — [#53576](https://github.com/vllm-project/vllm/pull/53576), lazy-imported in kernel warmup by [#54869](https://github.com/vllm-project/vllm/pull/54869)) — single-node, single-stream CUDA-IPC all-reduce over PCIe for TP groups with no NVLink. It is a separate code path from the NVLink `VLLM_ALLREDUCE_USE_FLASHINFER` default above; do not assume one covers the other's fabric. `vllm/envs.py` at v0.30.0.

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
- No RDMA / NVLink fabric between P-nodes and D-nodes. On 25 GbE-only clusters keep P and D on the SAME node (one pod, two vLLM containers) so NIXL uses cuda_ipc/NVLink; see the single-node measurements below.

### Single node, same 8 GPUs: 4P+4D vs 1×TP8 vs 2×TP4 — what has been measured

The one published head-to-head (verified 2026-09-16): [vLLM blog 2026-04-07, AMD MORI-IO connector](https://vllm.ai/blog/2026-04-07-moriio-kv-connector),
Qwen3-235B-A22B-FP8 on one 8× MI300X node, 2000 ISL / 1000 OSL at 8 req/s, SLO = TTFT + P99 ITL:

| Layout | Requests meeting both SLOs |
|---|---|
| 1× TP8 | 26/100 |
| 2× TP4 | 30/100 |
| 1P+1D (TP4+TP4), MORI-IO Read | 70/100 |
| 1P+1D (TP4+TP4), MORI-IO Write | 73/100 |

Collocated layouts fail on ITL spikes; disagg removes them and pays in TTFT. The split's
transport is intra-node (xGMI), so this is the "yes" case for large MoE + long-ish outputs.

Negative reports, same question, smaller models:
- [vllm#23144](https://github.com/vllm-project/vllm/issues/23144) (2025-08): Qwen3-8B on 8× A100, 1024 ISL / 6 OSL, PyNcclConnector 1P1D vs 2× TP2 chunked-prefill — disagg worse on TTFT and ITL at every QPS.
- [kraghavan.ca 2026-04-21](https://kraghavan.ca/llm-infrastructure/inference/2026/04/21/llm-d-pd-disaggregation.html): llm-d + NIXL on a single GH200, Qwen3-0.6B — TTFT 3.7×, ITL 3.5×, E2E 6.5× worse than aggregated.

Model-specific caveat: [vllm#55434](https://github.com/vllm-project/vllm/issues/55434) (open, 2026-09-05) — GLM-5.3
(DeepSeek-V3.2 arch, MLA + DSA indexer; NOT GLM-5.3-Flash) P/D on GB200 issues 91k–120k NIXL descriptors per
TP-rank transfer (~4.9 GB), and `cuda_ipc` spends 57% of transfer time posting them (4.07 µs/descriptor vs
0.20 µs on IB `rc_x`), so the intra-node MNNVL path came out slower end-to-end than RDMA. Descriptor-heavy KV
layouts can make the same-node transport the bottleneck; check the NIXL Prometheus `postDuration` histogram
before assuming NVLink/cuda_ipc is free.

No published single-node numbers exist (as of 2026-09-16) for GLM-5.x-Flash, DeepSeek, Llama-3.3-70B or SGLang.
Recipes (recipes.vllm.ai, NVIDIA Dynamo) document the 4+4 split without benchmarking it. Measure per model:
`vllm bench serve --goodput ttft:… tpot:…` against the split vs 1× TP8 on the same node, cold prefix.

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
| P95 ITL ≤ 30ms | tune `--cudagraph-capture-sizes` to cover running batch sizes; no eager fallback at peak batch |
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
