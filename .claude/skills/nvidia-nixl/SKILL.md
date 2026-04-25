---
name: nvidia-nixl
description: |-
  NVIDIA Inference Xfer Library (NIXL) operator + developer reference. Point-to-point KV-cache and tensor transport for distributed inference (Dynamo, vLLM, SGLang). Covers the C++/Python/Rust agent API, all 13 backend plugins (UCX, GDS, GDS_MT, libfabric, mooncake, posix, hf3fs, obj/S3, azure_blob, gusli, uccl, gpunetio/DOCA, telemetry), build paths (pip nixl-cu12/cu13, meson+ninja from source), ETCD vs side-channel metadata, telemetry (Prometheus + cyclic shared-memory), NIXL-EP elastic MoE device kernels, and Dynamo / vLLM NixlConnector / SGLang integration patterns.
when_to_use: |-
  Trigger on "NIXL", "ai-dynamo/nixl", "NVIDIA Inference Xfer Library", "nixl_agent", "nixl-cu12", "nixl-cu13", "nixlbench", "kvbench", "NIXL_PLUGIN_DIR", "NIXL_ETCD_ENDPOINTS", "NIXL_TELEMETRY_ENABLE", "VLLM_NIXL_SIDE_CHANNEL_HOST", "NIXL UCX/GDS/Mooncake/libfabric/HF3FS/S3/GUSLI/DOCA GPUNetIO/UCCL/Azure Blob backend", "NIXL telemetry", "NIXL ETCD", "side-channel metadata", "NIXL-EP", "elastic MoE", "nixlBackendH", "registerMem", "prepXfer", "createXferReq", "getNotifs", "loadRemoteMD", "fetchRemoteMD", "sendLocalMD", "South Bound API", "GPUDirect Storage cuFile", "RDMA write KV cache", "disaggregated prefill transport", "KV cache transfer engine", "NixlConnector", "Dynamo backend transfer", "nixlUcxSharedThread", "NIXL_ERR_REMOTE_DISCONNECT", "AWS EFA NIXL", "writing a NIXL plugin". For vLLM connector wiring (`--kv-transfer-config`, K8s pod shape, UCX_TLS) consult `vllm-caching` first.
---

# NVIDIA Inference Xfer Library (NIXL)

Target audience: operators wiring NIXL into Dynamo/vLLM/SGLang clusters, plugin authors writing new backends, developers using the agent API directly from Python/C++/Rust. Assumes datacenter-class GPUs (H100/H200/B200/B300) with NVIDIA driver, CUDA 12.8+, RDMA NIC (Mellanox/EFA) for cross-node, and Linux (Ubuntu 22.04/24.04 or Fedora). macOS and Windows are not supported.

## What NIXL is — one paragraph

NIXL is a thin abstraction over heterogeneous transport backends. A `nixlAgent` registers memory regions (DRAM, VRAM, FILE, BLOCK, OBJ), exchanges metadata with peer agents via either ETCD or socket side-channel, then issues asynchronous one-sided `READ`/`WRITE` transfers between local and remote registered memory. The agent picks the best backend (UCX for network, GDS for storage, etc.) based on memory types and what both sides have loaded. Same-process loopback, intra-node GPU-to-GPU, and cross-node RDMA are all the same API. Two operations only — read and write — and both are non-blocking with optional notifications.

## Version snapshot — verify before recommending

| Item | Value | Source |
|---|---|---|
| Latest release | **v1.0.1** (2026-04-14) — maintenance: NIXL-EP destruction/elastic-scale fixes, libfabric thread-safety + notif-on-repost, build/packaging | `gh release list --repo ai-dynamo/nixl` |
| Previous milestone | **v1.0.0** (2026-03-13) — first stable | release notes |
| HEAD pyproject version | **1.1.0** | `pyproject.toml` |
| PyPI wheels | `nixl-cu12`, `nixl-cu13` (auto-selects at runtime via PyTorch CUDA version since 1.0.1) | `pip install nixl` |
| Torch dep pin | `torch==2.11.*` | `pyproject.toml` (1.0.1+) |
| UCX version | `1.20.x` tested | repo `README.md` |
| Plugins | 13: ucx, libfabric, mooncake, uccl, gpunetio, cuda_gds, gds_mt, posix, hf3fs, obj (S3), azure_blob, gusli, telemetry | `src/plugins/` |
| Memory types | `DRAM`, `VRAM`, `FILE`, `BLOCK`, `OBJ` | `src/api/python/_api.py` |
| Operations | `READ`, `WRITE` | (no SEND/RECV — one-sided) |

For staleness — see `references/sources.md` for verified URLs. Run `freshen` mode of `skill-improver` to refresh.

## Decision tree — picking a backend

```
Is the transfer across nodes?
├─ Yes → Network backend
│   ├─ Standard RDMA (RoCE / IB) on Mellanox NICs?      → UCX
│   ├─ AWS EFA?                                          → libfabric (validated) or UCX
│   ├─ Heterogeneous GPU/NIC, software transport (no RDMA)? → UCCL [Preview]
│   ├─ KVCache-centric workload, multi-protocol (TCP/RDMA/CXL/NVMe-oF)? → mooncake [Preview]
│   └─ GPU-driven RDMA (GDAKI, kernel-launched)?        → gpunetio (DOCA)
└─ No → Local / storage backend
    ├─ NVMe / parallel FS via GPUDirect Storage?         → cuda_gds (single-thread) or gds_mt (multi-thread)
    ├─ Plain POSIX file (libaio default, liburing opt)?  → posix
    ├─ DeepSeek 3FS distributed FS?                      → hf3fs
    ├─ Block storage via GUSLI shared-mem client?        → gusli
    ├─ S3 (or S3-compatible) object store?               → obj (with optional cuobjclient accelerated engine)
    └─ Azure Blob?                                       → azure_blob
```

A single agent can instantiate multiple backends; per-transfer the agent chooses one based on the memory types involved and what the remote side advertises. Pass `backends=["UCX","GDS"]` to `nixl_agent_config` (Python) or `createBackend` calls (C++) to constrain candidates.

## Quick start (Python)

```python
import torch
from nixl import nixl_agent, nixl_agent_config

# Agent on each side
config = nixl_agent_config(
    enable_prog_thread=True,
    enable_listen_thread=True,        # socket side-channel
    listen_port=5555,
    capture_telemetry=False,
    backends=["UCX"],                  # default; use ["UCX","GDS"] etc. to add more
)
agent = nixl_agent("agent-1", config)

# Register a tensor (auto-detects DRAM vs VRAM)
tensor = torch.zeros((10, 16), dtype=torch.float32)
reg = agent.register_memory(tensor)

# After exchanging metadata (see references/python-api.md):
local_descs = agent.get_xfer_descs([tensor[i, :] for i in range(10)])
xfer = agent.initialize_xfer("READ", local_descs, target_descs, "agent-2", b"done")
agent.transfer(xfer)
while agent.check_xfer_state(xfer) == "PROC":
    pass  # spin or do other work
```

End-to-end working programs in `examples/python/basic_two_peers.py`, `expanded_two_peers.py`, `partial_md_example.py`. Full surface in `references/python-api.md`.

## Metadata exchange — choose ONE of two modes

**Side-channel (default).** Each agent runs a TCP listener (`enable_listen_thread=True`, `listen_port=N`). One agent calls `fetch_remote_metadata(remote_name, ip, port)` to pull, or `send_local_metadata(ip, port)` to push. Good for fixed-pair setups, lab environments. Defaults to port 5555.

**ETCD.** Set `NIXL_ETCD_ENDPOINTS=http://etcd:2379` (comma-separated for HA). Each agent calls `sendLocalMD()` / `fetchRemoteMD(remote_name)` (no IP/port args). Required for elastic / dynamic-scaling clusters where peers are not known upfront. ETCD is also how `nixlbench` discovers workers.

Both modes support `send_partial_agent_metadata(descs, inc_conn_info, backends, label=...)` — only register-then-send the metadata for specific descriptor lists, useful when memory regions are dynamic or to avoid advertising everything. Example: `examples/python/partial_md_example.py`.

## Plugin Manager + plugin search path

The plugin manager defers loading until first use (#1546, in v1.0.0+) and reads `NIXL_PLUGIN_DIR` to find dynamic plugins on disk. Static plugins are compiled in. Set this env var explicitly when running from non-system paths:

```bash
export NIXL_PLUGIN_DIR=/path/to/nixl/lib/x86_64-linux-gnu/plugins
```

`agent.getAvailPlugins()` lists what was discovered. `agent.getPluginParams("UCX")` returns the param schema + supported memory types for that plugin (use this to discover what to pass to `createBackend`).

## NIXL-EP — elastic Expert Parallel device kernels

`examples/device/ep/csrc/` ships device-side CUDA kernels for MoE all-to-all dispatch — `nixl_ep_ll.cu` (low-latency) and `nixl_ep_ht.cu` (high-throughput). Two API surfaces, one mode per agent: mixing LL and HT calls on the same agent is a hard error (mode guards added in v1.0.1, #1538). NIXL-EP also supports elastic scale-up (new nodes joining a running deploy), with signaling-buffer fixes in v1.0.1 (#1453). GPU timeouts are configurable (#1520). NIXL-EP is the layer Dynamo's MoE plane will land on; for plain disaggregated prefill (single tensor transfer), use the regular agent API.

## Telemetry — two exporters, environment-driven

| Env var | Purpose | Default |
|---|---|---|
| `NIXL_TELEMETRY_ENABLE` | Master switch (`y/yes/1` to enable) | `false` |
| `NIXL_TELEMETRY_EXPORTER` | Plugin name; empty falls back to cyclic buffer if `NIXL_TELEMETRY_DIR` set | unset |
| `NIXL_TELEMETRY_DIR` | Output dir for cyclic buffer files (one file per agent) | unset |
| `NIXL_TELEMETRY_BUFFER_SIZE` | Events in cyclic buffer | `4096` |
| `NIXL_TELEMETRY_RUN_INTERVAL` | Flush interval ms | `100` |

Cyclic buffer = static plugin, shared-memory ring; readers in `examples/python/telemetry_reader.py` and `examples/cpp/telemetry_reader.cpp`. **Prometheus exporter is dynamic + experimental (beta)** as of v1.0.x — see `src/plugins/telemetry/prometheus/README.md`. The Prometheus Exposer is shared across agents in the same process (v1.0.0 PR #1470). Built-in metrics: `agent_tx_bytes`, `agent_rx_bytes`, `agent_xfer_time` (µs), `agent_xfer_post_time` (µs), `agent_memory_registered`, etc. — full table in `references/architecture.md` and per-transfer telemetry via `agent.get_xfer_telemetry(handle)`.

## Common gotchas — read before deploying

1. **`UCX_TLS` is the #1 source of segfaults in vLLM+NIXL deploys.** `UCX_TLS=tcp` alone segfaults `nixlUcxSharedThread::run()` after prefill on CUDA-capable images that haven't been told the GPU is reachable. Use `UCX_TLS=cuda_copy,sm,tcp` (or full `cuda_copy,cuda_ipc,sm,tcp,rc` for cross-node). Symptom: `W ucx_utils.cpp:581: memory is detected as host`. (Verified in `vllm-caching` skill 2026-04-25.)
2. **First transfer after pod-ready may fail with `NIXL_ERR_REMOTE_DISCONNECT`** — handshake race. Retry the second request. Side-channel listener takes a few seconds to bind.
3. **Side-channel host MUST be a real interface, not a service VIP.** In Kubernetes, set `VLLM_NIXL_SIDE_CHANNEL_HOST=$(POD_IP)` via downward API and use a **headless** Service (`clusterIP: None`, `publishNotReadyAddresses: true`). Same applies to ETCD-mode if pods advertise their own addr.
4. **`NIXL_PLUGIN_DIR` defaults aren't reliable in non-pip installs.** If `agent.getAvailPlugins()` returns `[]` and an exception fires (`No plugins available for NIXL`), the env var is wrong. Verify with `ls $NIXL_PLUGIN_DIR/libplugin_*.so`.
5. **Mooncake plugin disables progress thread**, has its own metadata system that bypasses NIXL's, and caps transfer requests per handle at 1024 (`kMaxRequestCount`). It's `[Preview]`. Don't compose with strict NIXL-only metadata flows.
6. **GDS requires `cufile.json` with `allow_compat_mode: true`** unless full GDS is wired (kernel module + supported FS). The plugin README has the canonical config and `CUFILE_ENV_PATH_JSON` export.
7. **HF3FS needs page-aligned, page-size-multiple memory** for the zero-copy `mmap()` shared-memory path; otherwise it copies. Pass `mem_config=dram_zc` to fail loud if alignment is wrong.
8. **gpunetio (DOCA) is single-NIC + single-GPU per backend**. To use 2 NICs, instantiate 2 backends with different `network_devices`. `nvshmem`-aware bench mode supports VRAM-only transfers.
9. **EFA-only configs in UCX** were gated to not poison non-EFA setups in v1.0.1 (#1527). Below that, UCX with EFA-tuned defaults could degrade other systems.
10. **Telemetry timestamps were removed** from events in v1.0.0 (#1522) — readers must derive ordering from ring-insertion order, not event timestamp fields.

Full debugging cookbook in `references/gotchas.md`.

## What this skill does NOT cover (and where to go)

- **vLLM `NixlConnector` configuration (`--kv-transfer-config`, `kv_role`, K8s pod shape, the proxy server)** — covered in `vllm-caching` skill, especially `references/connectors.md` "NixlConnector" section. The vllm-caching skill has live-lab-verified recipes for 1P1D Qwen3-4B on consumer hardware including the six non-obvious env vars.
- **Dynamo deployment and disaggregation orchestration** — Dynamo docs at `https://docs.nvidia.com/dynamo/`. NIXL is the data plane; Dynamo handles request routing, scheduling, and the rest of the control plane.
- **vLLM-stack production deploy (LMCache, MooncakeConnector etc.)** — `vllm-deployment` and `vllm-caching` skills.
- **SGLang KV transport** — SGLang has its own connector; NIXL is one of the available backends. Consult SGLang docs.

## When the user is stuck — diagnostic flow

**Quick first pass**: run `python ${CLAUDE_SKILL_DIR}/scripts/check_install.py --backends UCX,LIBFABRIC,GDS` (substitute backends used). Validates wheel/CUDA match, plugin discovery, UCX_TLS, ETCD reachability, cufile.json — covers gotchas #1, #2, #4, #5, #7 in `references/gotchas.md`.

1. **`nixl_agent` raises `RuntimeError("No plugins available")`** → `NIXL_PLUGIN_DIR` is wrong, OR pip wheel mismatch (`nixl-cu13` on CUDA 12 host etc.). Confirm `pip show nixl-cu12 nixl-cu13` and which one PyTorch CUDA matches.
2. **Hangs on `fetch_remote_metadata`** → side-channel listener didn't start. Check `enable_listen_thread=True` on the **target**, port not collided, firewall open. Add a 5 s sleep before fetching.
3. **`NIXL_ERR_REMOTE_DISCONNECT`** → handshake race or network ACL. Retry. Check `UCX_TLS`. Confirm peer is listening with `ss -tlnp | grep <port>`.
4. **`Posting transfer failed.` (`state == "ERR"`)** → the agent rejected the request. Common causes: descriptor not within registered region, remote agent metadata not loaded yet (call `check_remote_metadata(name)` first), or backend not available on both sides. Check `agent.query_xfer_backend(handle)` if it's prepped.
5. **Throughput nowhere near line rate** → run `nixlbench --backend UCX --etcd-endpoints ... --initiator_seg_type=VRAM --target_seg_type=VRAM` to isolate. Compare against AWS/Mellanox-published numbers. Check `UCX_TLS`, `UCX_NET_DEVICES`, `cudaDeviceCanAccessPeer`, GDS path with `gdscheck`.
6. **Correctness bug after upgrade** → `git log v1.0.0..v1.0.1` and search for the relevant subsystem; the libfabric / NIXL-EP subsystems had several correctness fixes in 1.0.1.

`references/gotchas.md` has the full diagnostic flow with commands.

## References

- `references/architecture.md` — Agent + Memory Section + South Bound API (SB API) + Plugin Manager + descriptor lists + NIXL-EP device kernels + telemetry event catalog.
- `references/plugins.md` — All 13 plugins with deps, parameters, capabilities, when-to-pick.
- `references/python-api.md` — `nixl_agent` Python surface with worked examples for every common operation.
- `references/deployment.md` — pip install, source build (meson+ninja), Docker, K8s, ETCD setup, env vars, `nixlbench`, `kvbench`.
- `references/integrations.md` — Dynamo, vLLM `NixlConnector`, SGLang, observability stack pointers.
- `references/gotchas.md` — Debugging cookbook, error catalog, threading/sync model, build pitfalls.
- `references/sources.md` — Verified URLs with `Last verified` dates.
- `scripts/check_install.py` — Sanity-check script: wheel/CUDA match, plugin discovery, UCX_TLS, ETCD reach, cufile.json. Run before debugging deeper.

## Authoritative upstream sources

Primary: `https://github.com/ai-dynamo/nixl` (releases via `gh release list --repo ai-dynamo/nixl`). Canonical docs live in-tree under `docs/` (`nixl.md`, `BackendGuide.md`, `telemetry.md`, `python_api.md`); Python API source `src/api/python/_api.py`; per-plugin docs `src/plugins/<name>/README.md`; examples `examples/{python,cpp,rust,device/ep}/`; benchmarks `benchmark/{nixlbench,kvbench}/`. Full URL list with verification dates in `references/sources.md`.

When asked about a specific backend, **read the plugin's `README.md` under `src/plugins/<name>/` first** — every plugin documents its own deps, params, and gotchas there. Then map to `references/plugins.md` for the cross-cutting matrix.
