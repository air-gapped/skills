# NIXL Python API Reference

Source: `src/api/python/_api.py` (1099 lines, fully docstring'd). Bindings via pybind11 wrap `src/api/cpp`. Install: `pip install nixl` (auto-selects nixl-cu12 / nixl-cu13 based on PyTorch CUDA at runtime in v1.0.1+).

## Table of Contents
- [Imports + agent creation](#imports--agent-creation)
- [Plugin discovery](#plugin-discovery)
- [Memory registration](#memory-registration)
- [Querying memory metadata](#querying-memory-metadata)
- [Metadata exchange](#metadata-exchange)
- [Transfer creation — two paths](#transfer-creation--two-paths)
- [Posting + checking transfers](#posting--checking-transfers)
- [Per-transfer telemetry](#per-transfer-telemetry)
- [Notifications (decoupled from transfers)](#notifications-decoupled-from-transfers)
- [Teardown](#teardown)
- [Handle classes](#handle-classes)
- [Full worked example — basic_two_peers](#full-worked-example--basic_two_peers)

## Imports + agent creation

```python
from nixl import nixl_agent, nixl_agent_config
from nixl.logging import get_logger
import nixl._utils as nixl_utils         # malloc_passthru helper
import torch
```

`nixl_agent_config` parameters:

| Param | Type | Default | Notes |
|---|---|---|---|
| `enable_prog_thread` | bool | `True` | Internal completion processing thread |
| `enable_listen_thread` | bool | `False` | Side-channel TCP listener (forces strict thread sync) |
| `listen_port` | int | `0` | TCP port for listener; `0` = ephemeral |
| `capture_telemetry` | bool | `False` | Per-transfer telemetry data collection |
| `num_threads` | int | `0` | Forwarded to UCX/OBJ as `num_threads`, GDS_MT as `thread_count`, UCCL as `num_cpus` |
| `backends` | list[str] | `["UCX"]` | Plugins to instantiate at agent creation |

`nixl_agent` ctor:

```python
agent = nixl_agent("agent-name", config, instantiate_all=False)
# instantiate_all=True: ignore config.backends, instantiate every discovered plugin.
# Mutually exclusive with passing a config — config wins.
```

Throws `RuntimeError("No plugins available for NIXL")` if `getAvailPlugins()` is empty. Common cause: bad `NIXL_PLUGIN_DIR` or wrong wheel for CUDA version.

## Plugin discovery

```python
agent.get_plugin_list()                      # ['UCX', 'GDS', 'POSIX', ...]
agent.get_plugin_mem_types("UCX")            # ['DRAM', 'VRAM']
agent.get_plugin_params("UCX")               # {'num_threads': '1', ...}
agent.create_backend("UCX", {"num_threads": "4"})  # explicit init
agent.get_backend_mem_types("UCX")           # may differ post-init
agent.get_backend_params("UCX")              # may differ post-init
```

## Memory registration

`register_memory` accepts:
- A torch tensor → auto-detects DRAM (cpu) or VRAM (cuda).
- A `list[tuple[int, int, int, str]]` of `(addr, len, devID, str)` plus `mem_type=` arg.
- An existing `nixlRegDList`.

```python
# Tensor — most common
tensor = torch.zeros((10, 16), dtype=torch.float32, device="cuda:0")
reg = agent.register_memory(tensor)

# Raw addresses (use nixl_utils.malloc_passthru for testing)
addr = nixl_utils.malloc_passthru(buf_size=1024)
strs = [(addr, 1024, 0, "test")]
reg_descs = agent.get_reg_descs(strs, "DRAM")
agent.register_memory(reg_descs)

# Limit to specific backends
reg = agent.register_memory(tensor, backends=["UCX"])

# Deregister
agent.deregister_memory(reg)
```

`reg_descs.trim()` returns a `nixlXferDList` — a "transfer view" without the registration-only metadata, suitable for `initialize_xfer`.

## Querying memory metadata

`query_memory(reg_list, backend, mem_type=None)` returns per-region info dictionaries (or `None` if not found). Useful for storage backends to discover the actual size on disk, S3 object existence, etc.

```python
results = agent.query_memory(reg_descs, "OBJ")
for r in results:
    if r is None:
        print("missing")
    else:
        print(r)  # backend-specific keys
```

## Metadata exchange

Side-channel:

```python
# On target — listener thread is on
config_t = nixl_agent_config(enable_prog_thread=True, enable_listen_thread=True, listen_port=5555)
target = nixl_agent("target", config_t)

# On initiator — pulls then optionally pushes
initiator = nixl_agent("initiator", nixl_agent_config(enable_listen_thread=True))
initiator.fetch_remote_metadata("target", "10.0.0.5", 5555)
initiator.send_local_metadata("10.0.0.5", 5555)
```

ETCD (set `NIXL_ETCD_ENDPOINTS` first):

```python
agent.send_local_metadata()                  # to ETCD
agent.fetch_remote_metadata("target")        # from ETCD
```

Partial metadata:

```python
agent.send_partial_agent_metadata(
    descs=reg_descs,            # only this region's metadata
    inc_conn_info=True,
    backends=["UCX"],
    label="run-42",             # ETCD label for fetcher to match
    # ip_addr / port: socket mode only
)
agent.invalidate_local_metadata()           # ETCD: invalidates whole agent
agent.invalidate_local_metadata(ip, port)   # socket: tell specific peer
```

Direct metadata blob handling:

```python
md = agent.get_agent_metadata()                 # full blob
partial = agent.get_partial_agent_metadata(reg_descs, True, ["UCX"])
peer_name = agent.add_remote_agent(md_bytes)    # consume peer's blob
agent.remove_remote_agent("target")             # purge cache + disconnect
```

Remote metadata readiness check:

```python
while not agent.check_remote_metadata("target"):
    time.sleep(0.01)   # ETCD pull may be in flight
```

## Transfer creation — two paths

### Combined: `initialize_xfer`

Best when each transfer has a unique descriptor list.

```python
local_rows  = [tensor[i, :] for i in range(tensor.shape[0])]
local_descs = agent.get_xfer_descs(local_rows)

# target_descs come from the remote peer (sent via notif or out-of-band)
target_desc_str = agent.get_serialized_descs(local_descs)   # for sending over wire
target_descs    = agent.deserialize_descs(notif_bytes)       # on receive

xfer = agent.initialize_xfer(
    operation="READ",                # or "WRITE"
    local_descs=local_descs,
    remote_descs=target_descs,
    remote_agent="target",
    notif_msg=b"done_reading",
    backends=[]                      # let agent pick
)
```

### Split: `prep_xfer_dlist` + `make_prepped_xfer`

Best when many transfers share a descriptor list.

```python
local_dlist  = agent.prep_xfer_dlist("NIXL_INIT_AGENT", local_descs)   # local side
remote_dlist = agent.prep_xfer_dlist("target", target_descs)            # remote side
# (or local agent's name for loopback)

xfer = agent.make_prepped_xfer(
    operation="READ",
    local_xfer_side=local_dlist,
    local_indices=[0, 2, 4],         # which entries in local_descs to use
    remote_xfer_side=remote_dlist,
    remote_indices=[0, 2, 4],
    notif_msg=b"done",
    backends=[],
    skip_desc_merge=False,           # deprecated optimization flag
)
```

## Posting + checking transfers

```python
state = agent.transfer(xfer, notif_msg=b"override")   # post; status returned immediately
# state ∈ {"DONE", "PROC", "ERR"}

while True:
    state = agent.check_xfer_state(xfer)
    if state == "DONE":
        break
    if state == "ERR":
        raise RuntimeError("transfer failed")
    # do other work or short sleep
```

`agent.estimate_xfer_cost(xfer)` returns `(duration_µs, error_margin_µs, method)` — backend's cost model. Method is currently `"ANALYTICAL_BACKEND"` or `"UNKNOWN"`. Optional API; many backends return UNKNOWN.

`agent.query_xfer_backend(xfer)` returns the backend name the agent picked for this handle. Useful to verify the backend selector chose what you expect.

## Per-transfer telemetry

```python
tel = agent.get_xfer_telemetry(xfer)
print(tel.startTime, tel.postDuration, tel.xferDuration, tel.totalBytes, tel.descCount)
```

Fields:
- `startTime` µs (since some monotonic origin)
- `postDuration` µs (start → backend-post)
- `xferDuration` µs (full transfer)
- `totalBytes` int
- `descCount` int (post-merge, may differ from input list length)

This is per-transfer, separate from the global telemetry exporters in `references/architecture.md`.

## Notifications (decoupled from transfers)

```python
# Send standalone notification (control message)
agent.send_notif("target", b"go", backend=None)         # default backend picks

# Pull new notifications since last call
notifs = agent.get_new_notifs()                          # {agent_name: [bytes, ...]}

# Accumulate all unhandled notifications
notifs = agent.update_notifs()                           # appends to agent.notifs

# Match a specific tag (consumes the notif)
done = agent.check_remote_xfer_done("target", b"done_reading", tag_is_prefix=True)
```

A notification attached to a transfer (`notif_msg=` in `initialize_xfer` / `make_prepped_xfer` / `transfer`) is delivered to the remote agent when the transfer completes. Notifications via `send_notif` / `genNotif` are out-of-band (no transfer ordering guarantee).

## Teardown

```python
agent.release_xfer_handle(xfer)              # or xfer.release()
agent.release_dlist_handle(local_dlist)
agent.deregister_memory(reg)
agent.remove_remote_agent("target")
# Agent destructor cleans up remaining state
```

Handle classes (`nixl_xfer_handle`, `nixl_prepped_dlist_handle`) have `__del__` finalizers that best-effort release. If a finalizer fails for an in-flight transfer, the handle is queued in `agent._leaked_xfer_handles` and re-released during agent destruction. **Don't rely on finalizers** — explicitly release.

## Handle classes

### `nixl_prepped_dlist_handle`
- Wraps an opaque integer handle to a prepped descriptor list.
- `release()` — explicit free.
- `__repr__()` shows the handle as hex + released flag.

### `nixl_xfer_handle`
- Wraps an opaque integer handle to a transfer request.
- `release()` — if active, attempts abort; raises if abort fails.
- `__del__` defers to `release()`; on failure, queues handle for agent destruction cleanup.

## Full worked example — basic_two_peers

From `examples/python/basic_two_peers.py`:

```python
import torch
from nixl import nixl_agent, nixl_agent_config
from nixl.logging import get_logger
logger = get_logger(__name__)

# Run as: python basic_two_peers.py --mode {target,initiator} --ip 127.0.0.1 --port 5555

mode = ...; ip = ...; port = ...
listen_port = port if mode == "target" else 0
config = nixl_agent_config(True, True, listen_port)
agent = nixl_agent(mode, config)

tensor = torch.ones((10, 16)) if mode == "target" else torch.zeros((10, 16))
reg = agent.register_memory(tensor)

if mode == "target":
    rows = [tensor[i, :] for i in range(10)]
    descs = agent.get_xfer_descs(rows)
    while not agent.check_remote_metadata("initiator"):
        pass
    agent.send_notif("initiator", agent.get_serialized_descs(descs))
    while True:
        n = agent.get_new_notifs()
        if "initiator" in n and b"Done_reading" in n["initiator"]:
            break
else:
    agent.fetch_remote_metadata("target", ip, port)
    agent.send_local_metadata(ip, port)
    n = {}
    while not n:
        n = agent.get_new_notifs()
    target_descs = agent.deserialize_descs(n["target"][0])
    rows = [tensor[i, :] for i in range(10)]
    local_descs = agent.get_xfer_descs(rows)
    while not agent.check_remote_metadata("target"):
        pass
    xfer = agent.initialize_xfer("READ", local_descs, target_descs, "target", "Done_reading")
    agent.transfer(xfer)
    while agent.check_xfer_state(xfer) != "DONE":
        pass
    assert torch.allclose(tensor, torch.ones((10, 16)))
    agent.remove_remote_agent("target")
    agent.release_xfer_handle(xfer)
    agent.invalidate_local_metadata(ip, port)

agent.deregister_memory(reg)
```

For the parallel-READ + parallel-WRITE pattern (common for KV-cache transfer), see `examples/python/expanded_two_peers.py`. It shows `prep_xfer_dlist` + `make_prepped_xfer` with `--backend UCX` selection.
