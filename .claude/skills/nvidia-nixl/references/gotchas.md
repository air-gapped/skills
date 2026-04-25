# NIXL Gotchas + Debugging Cookbook

Real failure modes, ranked by frequency. Reference numbers in parens are PRs in `ai-dynamo/nixl`.

## Table of Contents
- [Top 10 production gotchas](#top-10-production-gotchas)
- [Error catalog](#error-catalog)
- [Diagnostic flow — symptom → tool](#diagnostic-flow--symptom--tool)
- [Threading + lifecycle traps](#threading--lifecycle-traps)
- [Build pitfalls](#build-pitfalls)
- [Performance debugging](#performance-debugging)
- [Plugin-specific traps](#plugin-specific-traps)

## Top 10 production gotchas

### 1. `UCX_TLS=tcp` segfaults `nixlUcxSharedThread::run()` on CUDA hosts
Symptom: prefill completes, then segv during the KV transfer with `W ucx_utils.cpp:581: memory is detected as host`.
Fix: `UCX_TLS=cuda_copy,sm,tcp` (single-node) or `cuda_copy,cuda_ipc,sm,tcp,rc` (cross-node IB). Image's UCX is CUDA-capable; default TLS doesn't enable cuda_copy.

### 2. `NIXL_ERR_REMOTE_DISCONNECT` on first request after pod-ready
Side-channel handshake hasn't fully bound when the first request arrives. Symptom: first transfer fails, second works.
Fix: retry the first request, OR add 5-second sleep between pod-ready and accepting traffic, OR set generous `initialDelaySeconds` on liveness probe.

### 3. Pod IP via downward API is mandatory in Kubernetes
Setting `VLLM_NIXL_SIDE_CHANNEL_HOST` to a Service VIP, FQDN, or `0.0.0.0` breaks the side-channel handshake — kube-proxy VIP is not a local interface, agents can't bind to it, and FQDN can resolve to wrong replicas.
Fix:
```yaml
- name: VLLM_NIXL_SIDE_CHANNEL_HOST
  valueFrom: { fieldRef: { fieldPath: status.podIP } }
```
Plus headless Service (`clusterIP: None`, `publishNotReadyAddresses: true`).

### 4. `NIXL_PLUGIN_DIR` mismatch
Symptom: `RuntimeError: No plugins available for NIXL, cannot start transfers!`. Or `agent.getAvailPlugins()` returns `[]`.
Fix:
```bash
ls $NIXL_PLUGIN_DIR/libplugin_*.so          # confirm files exist
echo $NIXL_PLUGIN_DIR                        # confirm var is set in NIXL's process env
strace -f -e openat python my_program.py 2>&1 | grep libplugin_  # see what NIXL is trying to open
```
For pip wheels the var is auto-set; for source builds set it to `<install-prefix>/lib/x86_64-linux-gnu/plugins`.

### 5. CUDA wheel mismatch: nixl-cu12 on CUDA 13 host (or vice versa)
Symptom: `ImportError: libcudart.so.12: cannot open shared object file` or similar.
Fix: `pip install nixl` (the meta-wheel auto-selects). If pinning, match the host CUDA — `nvidia-smi` and `python -c "import torch; print(torch.version.cuda)"`.

### 6. Mooncake's metadata system bypasses NIXL's
If you use Mooncake plugin, do NOT also rely on NIXL's ETCD/side-channel for the same agent — Mooncake handles peering itself. Mixing them produces silent connection failures.
Plus: Mooncake's `kMaxRequestCount = 1024` per `prepXfer` handle.

### 7. GDS without `cufile.json` fails on most filesystems
Without `allow_compat_mode: true` in cufile.json, cuFile errors out on filesystems that don't natively support GDS (most ext4, xfs without GDS-aware mount, etc.).
Fix: Set `CUFILE_ENV_PATH_JSON=/path/to/cufile.json` with NVIDIA's recommended NIXL config (see `references/plugins.md` cuda_gds section).

### 8. HF3FS zero-copy needs page-aligned memory
Symptom: HF3FS slow, copy path used unexpectedly.
Fix: Allocate user memory with `mmap()` directly or use `posix_memalign` to page boundary; size must be multiple of `getpagesize()`. Pass `mem_config=dram_zc` to fail loud on bad alignment.

### 9. Telemetry events silently dropped under load
The cyclic-buffer is fixed-size (default 4096); under sustained high event throughput, oldest events are overwritten.
Fix: Bump `NIXL_TELEMETRY_BUFFER_SIZE` (e.g. 65536). Or use the Prometheus exporter, which aggregates rather than buffering.

### 10. `progthread=False` with backends that need it
If your backend is UCX or libfabric and you disable the progress thread, completion processing only runs when you call into the agent. Symptom: transfers stuck in PROC despite the network having delivered the bytes.
Fix: Keep `enable_prog_thread=True` (default) unless you're using Mooncake-only or you're driving progress from your application loop manually.

## Error catalog

| Error / message | Likely cause |
|---|---|
| `RuntimeError: No plugins available for NIXL` | `NIXL_PLUGIN_DIR` wrong / wheel mismatch |
| `NIXL_ERR_REMOTE_DISCONNECT` | First-request handshake race; or peer crashed; or `UCX_TLS` misconfig; or kube ACL |
| `Posting transfer failed.` (state == "ERR" from `agent.transfer`) | Descriptor not in registered region, peer metadata not loaded, no common backend, or backend internal error |
| `W ucx_utils.cpp:581: memory is detected as host` | `UCX_TLS` doesn't include `cuda_copy` on a CUDA tensor |
| `Failed to register memory.` | Memory not aligned (storage backends), region overlap, backend not supporting that mem type |
| `Failed to fetch metadata of remote agent <name>` | Peer hasn't `sendLocalMD()`'d yet (ETCD), or socket listener not up, or IP/port wrong |
| `nixl_status_t = NIXL_ERR_BACKEND_NOT_SUPPORTED` | Asked for a backend that isn't loaded; check `agent.get_plugin_list()` |
| `nixl_status_t = NIXL_ERR_NO_BACKEND_FOR_REQUEST` | No common backend between local and remote agent for the requested mem types |
| Mooncake: silent connection failure | Mixing NIXL ETCD/side-channel with Mooncake's own metadata |
| Crash on `_bindings.so` import | `LD_LIBRARY_PATH` doesn't include UCX or CUDA; `ldd $(python -c 'import nixl._bindings as b; print(b.__file__)')` to diagnose |

## Diagnostic flow — symptom → tool

### Symptom: "It hangs"

```
agent.fetch_remote_metadata stuck?
├─ ETCD mode  → curl http://etcd:2379/v2/keys/  to confirm ETCD reachable
│              → curl http://etcd:2379/v2/keys/?recursive=true | jq  to see what's there
└─ Side-channel → ss -tlnp | grep <port>  on the target — listener up?
                → nc -zv <ip> <port>  from initiator — port reachable?
                → Add agent_config.enable_listen_thread=True on target

agent.transfer stuck in PROC?
├─ Backend progress thread ON?  agent.create_backend logged it?
├─ check_xfer_state in tight loop without yielding the GIL?
└─ Other side never received the request?  Check NIC counters, UCX_LOG_LEVEL=info
```

### Symptom: "It crashes"

```
Segfault in nixlUcxSharedThread::run?     UCX_TLS — see #1 above.
ImportError on libcudart.so.X?            wheel/CUDA mismatch — see #5.
Hang then OOM during register_memory?     allocator pressure — bump cgroup limit, or
                                           verify shared-mem device cgroup (`/dev/shm`).
gdb backtrace shows ucp_*?                UCX-internal — UCX_LOG_LEVEL=trace, file UCX issue.
```

### Symptom: "Transfer succeeds but data is wrong"

```
1. Verify with simple loopback (basic_two_peers.py) — does the same code path work locally?
2. Check src/dst memory types — did the agent pick a backend that does the actual copy?
   → agent.query_xfer_backend(handle)
3. Check UCX_TLS — `tcp` fallback can do silent CPU-staging where you expected RDMA.
4. Run nixlbench with --check_consistency — known good harness will catch backend bugs.
5. Re-test against latest NIXL release — libfabric had per-repost notif overrides fixed in 1.0.1.
```

### Symptom: "Throughput nowhere near line rate"

```
1. nixlbench with the same backend + same memory types
   → if nixlbench hits line rate, the bottleneck is in your code (descriptor splitting,
     transfer ordering, prep thrashing).
   → if nixlbench is also slow, the bottleneck is config / hardware.

2. UCX side:
   - UCX_TLS includes cuda_copy / rc?
   - UCX_NET_DEVICES restricting NICs?
   - GDR enabled for VRAM-VRAM? Check ucx_info -d for GPUDirect RDMA support.

3. GDS side:
   - gdscheck.sh shows your filesystem as compat_mode? Need full GDS for max BW.
   - cufile.json max_direct_io_size_kb sized to your transfer chunk?

4. Network:
   - ibv_devinfo / efa-info shows expected link speed?
   - ip -s link show <iface>  shows errors / drops?

5. Rule out fragmentation:
   - Big single descriptor = one RDMA write. Many small descriptors = many writes; per-op overhead dominates.
   - Use prep_xfer_dlist + index lists for batch transfers.
```

## Threading + lifecycle traps

- **Don't share an agent across processes.** `nixl_agent` holds backend handles + plugin state; `fork()` corrupts them. Use one agent per process.
- **One in-flight transfer per handle.** Posting to a `PROC` handle aborts the in-flight transfer. Tracking: per-transfer `nixl_xfer_handle`.
- **`__del__` is best-effort.** Explicit `release()` always; finalizer queues leaked handles for agent destruction but you'll lose telemetry on the leak.
- **`agent.notifs` is a member, not a fresh dict.** `update_notifs` accumulates into it; `get_new_notifs` returns only what's new. Don't mutate `agent.notifs` directly between calls.
- **Mooncake disables progthread internally.** Don't rely on background completion processing if Mooncake is in the mix.

## Build pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `meson setup` fails on UCX detect | UCX 1.20.x not installed / not in pkg-config path | `pkg-config --modversion ucx` should print 1.20.x |
| `ninja` fails with abseil errors | abseil version conflict (NIXL ≤1.0.0 issue, fixed v1.0.1 #1432) | Bump NIXL or pin abseil |
| Mooncake build OOM | Default ninja parallelism too high | NIXL v1.0.1 PR #1485 added memory-aware build; or set `NINJA_FLAGS="-j2"` |
| Plugin not built despite source present | meson option `disable_<name>_backend=true` | Read `meson_options.txt`, override `-Ddisable_<name>_backend=false` |
| Test build fails when UCX disabled | Test code assumed UCX (fixed v1.0.1 #1491) | Bump NIXL |

## Performance debugging

Start with `nixlbench` to isolate NIXL from your application:

```bash
NIXL_TELEMETRY_ENABLE=1 NIXL_TELEMETRY_DIR=/tmp/nixl-tel \
NIXL_PLUGIN_DIR=/path \
./nixlbench --etcd-endpoints http://etcd:2379 \
  --backend=UCX --runtime_type=ETCD \
  --initiator_seg_type=VRAM --target_seg_type=VRAM \
  --start_batch_size=1 --max_batch_size=512 \
  --total_buffer_size=$((32*1024*1024*1024))
```

Then read the telemetry:

```bash
python3 examples/python/telemetry_reader.py --telemetry_path /tmp/nixl-tel/<agent>
```

Look at `agent_xfer_time` distribution. If p99 ≫ p50, suspect contention (multi-tenant NIC, GDS bounce buffers exhausted, cuFile compat mode).

For per-request profiling: `agent.capture_telemetry=True` then `agent.get_xfer_telemetry(handle)` per transfer.

## Plugin-specific traps

### UCX
- `UCX_RNDV_THRESH` — rendezvous threshold; if KV blocks are smaller, eager protocol; larger, rendezvous (extra round-trip but zero-copy). Tune to your block size.
- `UCX_MAX_RNDV_RAILS` for multi-rail.
- v1.0.1 PR #1527: EFA-tuned config now gated to EFA only; pre-1.0.1 broke non-EFA setups silently.

### libfabric
- Multi-rail discovery is automatic; verify with `fi_info` that all NICs show up.
- NUMA-to-NIC mapping requires libnuma installed AND `numactl --hardware` showing the CPU/PCIe topology.
- Pre-v1.0.1: notification-on-repost bug — first prep's notif "wins" forever. Bump NIXL.

### Mooncake
- Preview status. Don't deploy in production without testing the specific Mooncake commit.
- Refactoring active — Mooncake team is reworking the transfer engine; expect API changes.

### gpunetio (DOCA)
- Single NIC + single GPU per backend instance. For multi-GPU, instantiate multiple backends.
- DOCA SDK + GDRCopy required; `LD_LIBRARY_PATH` must include `/opt/mellanox/doca` and `gdrcopy/src`.
- `CUDA_MODULE_LOADING=EAGER` — DOCA kernels load faster.

### POSIX
- liburing requires Docker seccomp tweak (`io_uring` syscalls are blocked by default).
- `params["use_uring"]="true"` to opt in.

### OBJ (S3)
- `crtMinLimit` controls when the CRT client kicks in for large objects. Tune to your object size distribution.
- Optional `cuobjclient-13.1` enables GPU-direct accelerated S3; if not installed, transparent fallback (no error, just slower).

### Azure Blob
- Backend params override env vars. Don't set both for the same key.
- AMQP and OpenTelemetry must be DISABLED at azure-sdk-for-cpp build time (`-DDISABLE_AMQP=ON`, `-DDISABLE_AZURE_CORE_OPENTELEMETRY=ON`); otherwise ABI conflicts.

### GUSLI
- Server is required for high-perf modes; "direct" mode is a fallback, not for production.
- Config file built from C++ API, not JSON. Stash the `params["config_file"]` blob somewhere if you want to inspect it.
