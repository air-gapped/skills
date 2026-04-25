# NIXL Integrations — Dynamo, vLLM, SGLang, Observability

NIXL is a transport library, not a serving framework. The frameworks below consume NIXL as their data plane.

## Table of Contents
- [NVIDIA Dynamo](#nvidia-dynamo)
- [vLLM NixlConnector](#vllm-nixlconnector)
- [SGLang](#sglang)
- [TensorRT-LLM (TRT-LLM)](#tensorrt-llm-trt-llm)
- [Observability stack](#observability-stack)
- [Choosing between connectors](#choosing-between-connectors)

## NVIDIA Dynamo

`https://github.com/ai-dynamo/dynamo` — high-throughput, low-latency open-source inference serving framework. Announced GTC 2025. NIXL is its data plane for KV-cache and tensor transfers in disaggregated serving.

**Where NIXL plugs in:**
- Dynamo's planner separates prefill and decode pools onto different GPU/node populations.
- KV cache produced by prefill workers is transferred to decode workers via a NIXL agent on each side.
- For MoE models, NIXL-EP handles the expert-parallel all-to-all dispatch.

**Backends Dynamo's TRT-LLM connector supports** (from `docs.nvidia.com/dynamo/.../kv-cache-transfer.html`):
- UCX (default) — RDMA/IB/RoCE.
- Libfabric — AWS EFA.
- Mooncake — multi-protocol KVCache-centric.
- (Object/storage backends for KV-extender / spillover patterns.)

**Operational pattern:**
- Both prefill and decode pods run with `NIXL_ETCD_ENDPOINTS` set to a shared ETCD.
- Side-channel mode also supported but adds Service plumbing complexity.
- Dynamo planner + Kubernetes operator handle pod scheduling; NIXL handles the transfer.
- For elastic scale-up/down (mid-day prefill capacity changes), use NIXL-EP for MoE; for non-MoE the regular agent API + ETCD invalidation suffices.

**WEKA, VAST, and other tiered-storage vendors** integrate via NIXL's storage plugins (GDS, OBJ) to extend KV cache to remote tiered storage. The Dynamo blog/docs cover the patterns.

## vLLM NixlConnector

vLLM's `NixlConnector` sits in `vllm.distributed.kv_transfer.kv_connector.v1.nixl_connector`. It's a v1 KVConnector implementation that uses NIXL for asynchronous send/receive of KV blocks.

**Configuration via `--kv-transfer-config`:**

```bash
vllm serve <model> \
  --kv-transfer-config '{
    "kv_connector":"NixlConnector",
    "kv_role":"kv_both",
    "kv_buffer_device":"cuda",
    "kv_connector_extra_config":{"backends":["UCX"]}
  }'
```

| Field | Purpose |
|---|---|
| `kv_connector` | `NixlConnector` |
| `kv_role` | `kv_both` / `kv_producer` (prefill) / `kv_consumer` (decode). NIXL connector itself does NOT distinguish — proxy server (`toy_proxy_server.py --prefiller-hosts ... --decoder-hosts ...`) decides. So `kv_role` is effectively a placeholder. |
| `kv_buffer_device` | `cuda` (default) or `cpu`. CPU buffer support added in PR #18293 (juncgu). |
| `kv_connector_extra_config.backends` | List of NIXL backend names to use. Default `["UCX"]`. |
| `kv_load_failure_policy` | `fail` (default — abort request on KV-load fail) or `recompute` (recompute the failed blocks locally). |

**Critical env vars (set per pod):**

```yaml
env:
- name: VLLM_NIXL_SIDE_CHANNEL_HOST
  valueFrom: { fieldRef: { fieldPath: status.podIP } }
- name: VLLM_NIXL_SIDE_CHANNEL_PORT
  value: "5557"
- name: UCX_TLS
  value: "cuda_copy,sm,tcp"          # mandatory; tcp alone segfaults
```

**For full operator-grade recipes** (live-lab verified) including the toy proxy server, headless Service spec, and gotchas list: consult the `vllm-caching` skill, especially `references/connectors.md` "NixlConnector — disaggregated prefill" section. Verified 2026-04-25 on consumer 2× RTX 4060 Ti + Qwen3-4B + vLLM v0.19.2rc1.

**Observed gotchas in vLLM+NIXL deploys** (from `vllm-caching`):
1. `UCX_TLS=tcp` alone segfaults. Use `cuda_copy,sm,tcp`.
2. First request after pod-ready may `NIXL_ERR_REMOTE_DISCONNECT`; second works.
3. Proxy httpx client pool caches pod IPs — restart proxy if you restart vLLM pods.
4. Headless Service required.

**Disaggregation does not always win.** From the vllm-caching live-lab measurement: 1P1D vs single-pod baseline on consumer hardware with short prompts: −34% throughput, 9× worse TTFT. Disaggregation pays off when input ≫ output (16k+ prefill), prefill latency dominates TTFT, 1P:N-D ratio, AND multi-node where prefill pool scales independently. Don't deploy 1P1D for short-prompt chat workloads.

**Open issue to track:** vllm-project/vllm#27055 — "Prefill disaggregation failed kv transfer with NiXL connector using LIBFABRIC backend with vllm 0.11 and nixl 0.6.1." Likely fixed by libfabric thread-safety work in NIXL v1.0.1, but verify against current vLLM nightly.

**vLLM image bundled NIXL versions** (from `requirements/kv_connectors.txt` on main as of 2026-04-24):
- `nixl-cu12 / cu13 >= 0.7.1, <= 0.10.1`. **vLLM does NOT yet pin NIXL ≥ 1.0.0** as of 2026-04-24 — there's a window where NIXL is shipping fixes (NIXL-EP, libfabric) faster than vLLM is bumping its pin. If the user is debugging against `nixl 0.10.1` that's expected for current vLLM.

## SGLang

SGLang has its own KV-cache transport layer with NIXL as one of the backends. The connector lives in `sglang/srt/disaggregation/`. Configuration is via SGLang launch flags (`--disaggregation-mode prefill|decode`, `--disaggregation-bootstrap-port`, `--disaggregation-transfer-backend nixl`). 

NIXL plugin selection is implicit (UCX-default); per-deploy tuning via `UCX_TLS` and the SGLang transfer config. Refer to SGLang docs for the canonical flag set; NIXL itself is the same library as in vLLM.

## TensorRT-LLM (TRT-LLM)

The Dynamo TRT-LLM backend uses NIXL for KV-cache transfer between prefill and decode engines. Documented at `https://docs.nvidia.com/dynamo/latest/backends/trtllm/kv-cache-transfer.html` (verify URL — pages occasionally move).

Config patterns are framed inside Dynamo's deploy spec (Helm values for TRT-LLM workers), not directly inside TRT-LLM. NIXL agent comes up with the worker container, ETCD endpoints come from the Dynamo control plane.

## Observability stack

NIXL emits Prometheus metrics via the (beta) Prometheus exporter. Wire that into a standard inference-stack observability:

| Layer | Tool | What to look at |
|---|---|---|
| Per-transfer NIXL telemetry | `agent.get_xfer_telemetry(handle)` | Per-request latency, bytes, descCount |
| Agent-level NIXL telemetry | NIXL Prometheus / cyclic buffer | Aggregate TX/RX bytes, request counts, error counts, transfer time histogram |
| vLLM | vLLM `/metrics` | TTFT, TPOT, queue depth, KV cache utilization |
| Dynamo | Dynamo planner + worker metrics | Pod-pool occupancy, prefill/decode imbalance |
| Underlying NIC | Mellanox NIC counters / EFA telemetry | bytes_in / bytes_out / errors / RDMA-recv-CQE |
| K8s | kubelet + cAdvisor | CPU / memory / GPU / network |

For dashboards: ship NIXL `agent_xfer_time` histogram alongside vLLM TTFT — TTFT = prefill_compute + xfer_time + decode_first_token. If TTFT degrades but vLLM prefill stays flat, NIXL transfer time is the suspect.

The `vllm-observability` skill covers the vLLM side. The `prometheus-mimir-grafana` skill covers querying the resulting metrics.

## Choosing between connectors

vLLM ships several KV-transfer connectors. NIXL is one. Quick selector:

| Goal | Connector | Why |
|---|---|---|
| Single-node, CPU DRAM tier only | Native `OffloadingConnector` | No network plane needed, zero deps |
| Single-node, NVMe spillover | `LMCacheConnectorV1` | LMCache native NVMe + GDS path |
| Cross-node KV transfer (prefill→decode) | `NixlConnector` | NIXL is the wire-speed transport for this |
| Multi-protocol KV with KVCache-centric design | `MooncakeConnector` | Mooncake has its own engine |
| LMCache-style P2P between vLLM pods | `LMCacheConnectorV1` + `transfer_channel: nixl` | LMCache uses NIXL under the hood |
| Compose: Nixl across nodes + CPU offload locally | `MultiConnector(NixlConnector + OffloadingConnector)` | The vllm-caching skill has this recipe |

The `vllm-caching` skill is the operator reference for this decision tree. NIXL itself is just the transport — choosing the right vLLM connector is a separate decision.
