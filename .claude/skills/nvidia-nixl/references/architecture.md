# NIXL Architecture — Agent, SB API, Plugin Manager, NIXL-EP

Canonical source: `docs/nixl.md`, `docs/BackendGuide.md`, `docs/telemetry.md` in the NIXL repo.

## Table of Contents
- [Core abstractions](#core-abstractions)
- [Memory Section + descriptor lists](#memory-section--descriptor-lists)
- [South Bound API (SB API) — what plugins implement](#south-bound-api-sb-api--what-plugins-implement)
- [Plugin Manager](#plugin-manager)
- [Metadata exchange — side channel vs ETCD](#metadata-exchange--side-channel-vs-etcd)
- [Transfer lifecycle](#transfer-lifecycle)
- [NIXL-EP — elastic Expert Parallel](#nixl-ep--elastic-expert-parallel)
- [Telemetry event catalog](#telemetry-event-catalog)
- [Threading model](#threading-model)

## Core abstractions

The `nixlAgent` (C++) / `nixl_agent` (Python) is the entry point. One agent per inference conductor process. Each agent manages:

1. **Memory Section** — registered memory regions across heterogeneous types (DRAM/VRAM/FILE/BLOCK/OBJ).
2. **Transfer Backend Interface (SB API)** — set of loaded backend plugins. The agent picks the optimal one per transfer.
3. **Metadata Handler** — caches remote agent metadata so transfers can use a remote handle without per-transfer round-trips.

A transfer = (operation ∈ {READ, WRITE}, local descriptor list, remote descriptor list, remote agent name, optional notification message). Both sides' descriptors must be inside their respective registered regions. The initiator alone holds the handle; the target sees nothing until either a local memory change (write) or a notification arrives.

There is **no SEND/RECV in NIXL** — only one-sided RDMA-style READ and WRITE. A "send" is the initiator pushing a WRITE to remote; a "recv" is the initiator pulling a READ from remote. Two-sided semantics are layered on top via `genNotif` / `getNotifs`.

## Memory Section + descriptor lists

A descriptor list = `(memory space ∈ {DRAM, VRAM, FILE, BLOCK, OBJ}, [descriptors...])`.

Two descriptor flavors:
- **Registration descriptor**: `(addr, len, devID, str)` — `str` is an optional byte array carrying e.g. file path + access mode for FILE, or extended-key + bucket for OBJ.
- **Transfer descriptor**: `(addr, len, devID, metadata*)` — `metadata*` is a backend-internal pointer that the agent attaches; the user never sees it.

`devID` semantics by memory type:

| mem type | addr | len | devID | str |
|---|---|---|---|---|
| DRAM | host pointer | bytes | 0 (or NUMA region) | — |
| VRAM | device pointer | bytes | GPU ID (CUDA ordinal) | — |
| BLOCK | block offset | bytes | volume ID | — |
| FILE | offset | bytes (or 0 for whole-file) | file descriptor | path + access mode |
| OBJ | offset | bytes (or 0) | key | extended key + bucket ID |

Registration:

```python
agent.register_memory(tensor)               # auto-detects DRAM vs VRAM, registers with all backends supporting that type
agent.register_memory(tensor, backends=["UCX"])  # restricted to UCX
agent.register_memory(buf_tuples, mem_type="DRAM")  # explicit list of (addr,len,dev,str) tuples via nixl_utils.malloc_passthru
```

The returned `nixlRegDList` is what's passed to `deregister_memory` and to `get_partial_agent_metadata`. Re-registering the same region is an error in some backends — track lifecycle carefully.

## South Bound API (SB API) — what plugins implement

Plugins declare 4 capability flags via getter methods:
- `supportsLocal()` — within-node transfers (incl. loopback)
- `supportsRemote()` — cross-node transfers
- `supportsNotif()` — async notifications
- `getSupportedMems()` — set of memory types the plugin handles

A network plugin sets `supportsRemote=true` AND `supportsNotif=true`, ideally also `supportsLocal=true`. A storage plugin typically sets only `supportsLocal=true` (the storage server is "remote" but NIXL sees the local client as the only peer).

Required SB API methods (subset depends on capabilities):

| Group | Methods | Required when |
|---|---|---|
| Lifecycle | constructor, destructor | always |
| Capability | `supportsLocal`, `supportsRemote`, `supportsNotif`, `getSupportedMems` | always |
| Connection | `connect`, `disconnect` | always |
| Connection (remote) | `getConnInfo`, `loadRemoteConnInfo` | `supportsRemote` |
| Memory | `registerMem`, `deregisterMem` | always |
| Metadata | `getPublicData`, `loadRemoteMD` | `supportsRemote` |
| Metadata | `loadLocalMD` | `supportsLocal` |
| Metadata | `unloadMD` | always |
| Transfer | `prepXfer`, `postXfer`, `checkXfer`, `releaseReqH` | always |
| Transfer (optional) | `estimateXferCost` | optional |
| Notif | `getNotifs`, `genNotif` | `supportsNotif` |

Plugin manager methods (different from SB API; required for dynamic loading):

- `get_plugin_name`, `get_plugin_version`
- `create_engine`, `destroy_engine`
- `get_backend_mems`, `get_backend_options`

`get_backend_options` returns the param schema (key → default-value strings) — use this from `agent.getPluginParams("X")` to discover what `createBackend` accepts before the user has to grep source.

## Plugin Manager

- Searches `NIXL_PLUGIN_DIR` for `.so` files matching `libplugin_*.so` (Linux).
- **Defers loading until first use** (v1.0.0 PR #1546) — agents creation is fast even with many plugins on disk; only the requested ones load.
- Static plugins are compiled into the NIXL library and don't need the env var.
- Currently the cyclic-buffer telemetry exporter is static-only; the Prometheus exporter is dynamic-only.
- API versioning of plugin manager methods enables backward/forward compat across plugin and NIXL versions.

To check what's loaded:

```python
plugins = agent.get_plugin_list()              # what was discovered
mems = agent.get_plugin_mem_types("UCX")       # memory types UCX advertises
params = agent.get_plugin_params("UCX")        # init param schema
agent.create_backend("UCX", {"num_threads": "4"})
backend_mems = agent.get_backend_mem_types("UCX")  # post-init may differ
```

## Metadata exchange — side channel vs ETCD

After backends are created and memory is registered, peer agents must learn each other's metadata before transfers work. Metadata = serialized blob containing per-backend connection info + per-region remote identifiers + agent name.

**Two transports for the metadata blob itself:**

### Side-channel (TCP listener, default port 5555)

```python
config = nixl_agent_config(enable_listen_thread=True, listen_port=5555)
target = nixl_agent("target", config)
# … register memory …
# Initiator side:
initiator.fetch_remote_metadata("target", "10.0.0.5", 5555)
initiator.send_local_metadata("10.0.0.5", 5555)
```

The listener thread reuses the agent's progress-thread infrastructure. `enable_listen=True` sets thread sync to `NIXL_THREAD_SYNC_STRICT` (otherwise `NIXL_THREAD_SYNC_NONE`). One TCP port per agent.

### ETCD (central metadata service)

```bash
export NIXL_ETCD_ENDPOINTS=http://etcd:2379
# multiple endpoints: http://e1:2379,http://e2:2379,http://e3:2379
```

```python
config = nixl_agent_config(enable_listen_thread=False)  # ETCD doesn't need listener
agent = nixl_agent("agent-1", config)
# … register …
agent.send_local_metadata()                    # no IP/port — goes to ETCD
agent.fetch_remote_metadata("agent-2")         # pulls from ETCD
```

ETCD is **mandatory for elastic clusters** where peers aren't known upfront, and is what `nixlbench` uses by default. Production Dynamo deploys also use ETCD.

### Partial metadata

Send only the metadata for specific descriptor lists — useful for dynamic registration or to avoid leaking unrelated regions:

```python
agent.send_partial_agent_metadata(
    descs=reg_descs,
    inc_conn_info=True,
    backends=["UCX"],
    label="run-42",         # ETCD only
)
```

Working example: `examples/python/partial_md_example.py`.

### Invalidation

`agent.remove_remote_agent("name")` — disconnects all backends, purges cached metadata. Call this when a peer is removed from the deploy or fails. Also use `invalidate_local_metadata(...)` on the leaving agent so peers see the disappearance. Heartbeat / failure detection is the **caller's responsibility** — NIXL does not implement a heartbeat protocol.

## Transfer lifecycle

```
register_memory  →  exchange metadata  →  prep_xfer_dlist (or initialize_xfer)  →
post (transfer)  →  check_xfer_state until DONE  →  release_xfer_handle
```

Two API surfaces for creating transfers:

**`initialize_xfer` — combined prep+post-prep.** Best when each transfer's descriptor list is unique:

```python
xfer = agent.initialize_xfer("READ", local_descs, target_descs, "target", b"done_reading")
agent.transfer(xfer)
```

**`prep_xfer_dlist` + `make_prepped_xfer` — split.** Best when many transfers share the same descriptor list (e.g., reading from the same set of KV blocks repeatedly). The list is prepped once; per-transfer is a `make_prepped_xfer` with index lists. Cheaper hot path.

```python
local_dlist = agent.prep_xfer_dlist("NIXL_INIT_AGENT", local_descs)
remote_dlist = agent.prep_xfer_dlist("target", target_descs)
xfer = agent.make_prepped_xfer("READ", local_dlist, [0,2,4], remote_dlist, [0,2,4], b"done")
```

**Reposting.** A handle from either path can be `transfer()`-ed multiple times as long as it reaches `DONE` between posts. Posting while `PROC` is an error and may abort the in-flight transfer.

**Per-transfer telemetry.** `agent.get_xfer_telemetry(handle)` returns a `nixlXferTelemetry` with `startTime`, `postDuration`, `xferDuration` (all µs), `totalBytes`, `descCount`. Useful for adaptive scheduling, e.g., feed back into a local "is this peer slow today" metric.

**Aborting.** `release_xfer_handle(handle)` while `PROC`: if the backend supports cancel, it does; if not, the call returns error and `check_xfer_state` keeps returning ERR until the transfer naturally completes, then a subsequent release succeeds. `release` is **non-blocking** by contract — backends that need a blocking abort run it on a separate thread internally.

## NIXL-EP — elastic Expert Parallel

`examples/device/ep/` is the device-side Expert Parallel layer for MoE all-to-all. Two modes:
- **LL (low-latency)**: `nixl_ep_ll.cu` — for small all-to-all bursts (decode-time MoE routing).
- **HT (high-throughput)**: `nixl_ep_ht.cu` — for large dispatch (prefill-time, batched).

**Mode is sticky per agent.** PR #1538 (v1.0.1) added guards to fail fast if LL and HT calls mix. Pick one at agent-init time.

**Elastic scale-up.** New nodes can join a running deploy; signaling-buffer corruption fix landed in v1.0.1 (#1453). Pre-1.0.1 elastic scale-up was unsafe with concurrent transfers.

**GPU timeouts.** `nixl_ep` exposes per-agent GPU timeout config (v1.0.1, #1520); useful for slow scale-up where the new node hasn't wired its NICs yet.

**Planned SIGTERM.** v1.0.1 (#1500) made the EP elastic test handle planned shutdowns cleanly — relevant if running in K8s with `terminationGracePeriodSeconds`.

NIXL-EP is the data-plane substrate for Dynamo's MoE pipeline. For plain disagg-prefill (single tensor transfer per request), use the regular `nixl_agent` API; NIXL-EP would be over-engineering.

## Telemetry event catalog

Built-in events (from `docs/telemetry.md`):

| Category | Event | Type | Description |
|---|---|---|---|
| MEMORY | `agent_memory_registered` | bytes | per `registerMem` call |
| MEMORY | `agent_memory_deregistered` | bytes | per `deregisterMem` call |
| TRANSFER | `agent_tx_bytes` | counter | bytes transmitted per TX |
| TRANSFER | `agent_rx_bytes` | counter | bytes received per RX |
| TRANSFER | `agent_tx_requests_num` | counter | TX request count |
| TRANSFER | `agent_rx_requests_num` | counter | RX request count |
| PERFORMANCE | `agent_xfer_time` | µs | full transfer time |
| PERFORMANCE | `agent_xfer_post_time` | µs | start → backend-post time |
| BACKEND | dynamic | varies | per-plugin events |
| ERROR | error-status string | counter | error occurrences by type |

**Notes from recent commits:**
- v1.0.0 PR #1531: switched event names from raw strings to enum types — dynamic backend events still string-typed.
- v1.0.0 PR #1522: removed timestamp field — readers must use ring-insertion order. If a downstream consumer expects timestamps, **derive them at read time** in the reader.
- v1.0.0 PR #1516: fixed unbounded growth of in-memory event buffer — older NIXL had a memory leak under high event throughput.
- v1.0.0 PR #1470: Prometheus exposer is shared across all agents in the same process — multi-agent processes (rare but possible) export to one `/metrics` endpoint.

Full Prometheus exporter doc: `src/plugins/telemetry/prometheus/README.md`. Custom exporter dev: `src/plugins/telemetry/README.md`.

## Threading model

- **Progress thread**: per-agent, optional (`enable_prog_thread=True`, default). Drives backend internal completion processing. Disable only if the agent's process never lets the main thread go idle (rare).
- **Listener thread**: per-agent, optional (`enable_listen_thread=False`, default). For socket side-channel metadata exchange. Default delay 100 µs. ETCD doesn't need it.
- **Plugin internal threads**: e.g., libfabric uses background progress threads with lock-free completion queues; UCX runs its own progress (the agent's progress thread calls into UCX); GDS_MT spins up `thread_count` worker threads (configurable).
- **Sync mode**: enabling listener forces `NIXL_THREAD_SYNC_STRICT`; otherwise `NIXL_THREAD_SYNC_NONE` is used. Strict mode adds locks around shared state; non-strict assumes the user only calls the agent from one thread.

**Per-plugin threading caveats:**
- Mooncake: progress thread NOT supported — set `enable_prog_thread=False` if Mooncake is the only backend.
- libfabric: thread-safe in v1.0.1+ (PR #1483 added mutex around endpoint access; FI_THREAD_COMPLETION). Pre-1.0.1 had race conditions.
- UCX: thread-safe by design; v1.0.1 PR #1565 improved progress + notif handling.
