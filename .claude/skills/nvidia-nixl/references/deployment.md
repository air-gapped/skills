# NIXL Deployment — Build, Install, Containerize, Run

Covers: pip install, source build with meson+ninja, ETCD setup, env-var catalog, Docker, Kubernetes pod shape, NIXLBench + KVBench harnesses.

## Table of Contents
- [Installation paths](#installation-paths)
- [Source build](#source-build)
- [Docker images](#docker-images)
- [Kubernetes pod shape](#kubernetes-pod-shape)
- [ETCD setup](#etcd-setup)
- [NIXL environment variables](#nixl-environment-variables)
- [NIXLBench](#nixlbench)
- [KVBench](#kvbench)

## Installation paths

### PyPI wheels (recommended for most)

```bash
pip install nixl
```

The `nixl` meta-wheel installs both `nixl-cu12` and `nixl-cu13` (since 1.0.1). At runtime, the right one is selected based on the CUDA reported by PyTorch. UCX is bundled inside the wheel.

To pin: `pip install nixl-cu12==1.0.1` or `pip install nixl-cu13==1.0.1`.

`pip show nixl-cu12` confirms install path; the wheel includes `_bindings.so`, `libnixl.so`, and the bundled plugin `.so`s under the package directory. **`NIXL_PLUGIN_DIR` is auto-set by the wheel's `__init__`** — only override if installing additional out-of-tree plugins.

### Source — when wheel doesn't fit

Reasons to build from source:
- Want a custom UCX build with GDRCopy linked.
- Need plugins not in the wheel: `mooncake`, `uccl`, `gpunetio` (DOCA), `gusli`, `hf3fs` — these have third-party deps that PyPI policy forbids bundling.
- Bisecting a NIXL or UCX commit.
- Air-gapped builds.

## Source build

Prereqs (Ubuntu 22.04 / 24.04):

```bash
sudo apt install build-essential cmake pkg-config
pip3 install meson ninja pybind11 tomlkit
```

Fedora:

```bash
sudo dnf install gcc-c++ cmake pkg-config
pip3 install meson ninja pybind11 tomlkit
```

UCX 1.20.x:

```bash
git clone https://github.com/openucx/ucx.git
cd ucx && git checkout v1.20.x
./autogen.sh
./contrib/configure-release-mt \
    --enable-shared --disable-static \
    --disable-doxygen-doc --enable-optimizations \
    --enable-cma --enable-devel-headers \
    --with-cuda=<cuda install> \
    --with-verbs --with-dm \
    --with-gdrcopy=<gdrcopy install>
make -j && sudo make -j install-strip && sudo ldconfig
```

ETCD (optional but recommended):

```bash
sudo apt install etcd etcd-server etcd-client
# or:
docker run -d -p 2379:2379 quay.io/coreos/etcd:v3.5.1
```

ETCD CPP API: `https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3` — install from source.

NIXL build (meson + ninja):

```bash
cd nixl
meson setup builddir [-Dlibfabric_path=...] [-Ddisable_mooncake_backend=false]
cd builddir
ninja
sudo ninja install
```

Python bindings:

```bash
cd nixl
pip install .
```

The pyproject specifies `mesonpy` as the build backend. `meson_options.txt` exposes per-plugin enable/disable flags — read it before passing `-D...` flags.

### Plugin-specific source build notes

- **Mooncake** (`disable_mooncake_backend=false`): Build Mooncake first with `cmake .. -DBUILD_SHARED_LIBS=ON`, install. Then NIXL.
- **HF3FS**: Install 3FS, ensure `hf3fs_usrbio.so` and `libhf3fs_api_shared.so` in `/usr/lib/`, headers in `/usr/include/hf3fs`.
- **GUSLI**: Build with `make all BUILD_RELEASE=1 BUILD_FOR_UNITEST=0 ALLOW_USE_URING=0`. Install `libgusli_clnt.so` to `/usr/lib/`.
- **OBJ (S3)**: aws-sdk-cpp 1.11.581 with `-DBUILD_ONLY="s3;s3-crt"`. Optional `cuobjclient-13.1` for accel.
- **Azure Blob**: azure-sdk-for-cpp at `azure-storage-blobs_12.15.0` tag.
- **DOCA GPUNetIO**: Install DOCA SDK + GDRCopy.
- **UCCL**: Build P2P engine via `make -j && sudo make install` in `uccl/p2p`.

## Docker images

The repo's `Dockerfile`s under `contrib/` and `benchmark/nixlbench/contrib/` build the manylinux + benchmark images.

For inference workloads, NIXL is **bundled into vLLM images** since v0.14.0:
- `vllm/vllm-openai:v0.14.0+` with `INSTALL_KV_CONNECTORS=true` ships `nixl-cu12` / `nixl-cu13` along with LMCache and Mooncake-transfer-engine.
- `cu130-nightly` and per-model tags like `glm51-cu130` ship both `nixl-cu12` AND `nixl-cu13` — the meta `nixl` wheel `Requires: nixl-cu12`, but `nixl_cu13._bindings` is what gets loaded on CUDA 13 hosts. Both coexist.

Verify a vLLM image's CUDA + bundled NIXL:

```bash
docker run --rm <image> python -c "
import nixl, nixl._bindings as b
print('nixl', nixl.__version__)
print('plugins', b.nixlAgent('test', b.nixlAgentConfig()).getAvailPlugins())
"
```

## Kubernetes pod shape

For NIXL-using pods (Dynamo workers, vLLM disagg-prefill prefiller/decoder), the load-bearing requirements:

1. **Headless Service** — `clusterIP: None`, `publishNotReadyAddresses: true`. Pods advertise pod IPs to peers via the side-channel handshake; binding/advertising via Service VIP breaks because a kube-proxy VIP is not a local interface.

2. **Pod IP via downward API:**
   ```yaml
   env:
   - name: VLLM_NIXL_SIDE_CHANNEL_HOST
     valueFrom:
       fieldRef:
         fieldPath: status.podIP
   - name: VLLM_NIXL_SIDE_CHANNEL_PORT
     value: "5557"
   ```
   For ETCD mode, set `NIXL_ETCD_ENDPOINTS` instead.

3. **`UCX_TLS=cuda_copy,sm,tcp`** — without `cuda_copy`, prefiller segfaults in `nixlUcxSharedThread::run()` after prefill with `W ucx_utils.cpp:581: memory is detected as host`. Image's UCX IS CUDA-capable; defaults aren't enabled. For cross-node, add `rc` for IB-RC: `cuda_copy,cuda_ipc,sm,tcp,rc`.

4. **Generous probe timeouts** — pod-ready handshake takes 5–15 s after model load. First request after pod-ready may fail with `NIXL_ERR_REMOTE_DISCONNECT`; second works. Apply `initialDelaySeconds: 60+` on liveness for prefiller pods.

5. **`hostNetwork: true`** for InfiniBand RDMA — required for verbs / RoCE since the pod-network namespace doesn't share IB devices. Use a SriovNetworkNodePolicy + RDMA shared device plugin if you can't use hostNetwork.

6. **`nvidia.com/gpu: 1` resource** + `runtimeClassName: nvidia` (NVIDIA Container Runtime). For GDS, additionally:
   - `volumeMounts`: `/dev/nvidia-fs0`, `/dev/nvidia-fs[1-15]`, `/run/cufile-rdma`.
   - `securityContext.privileged: true` or specific device cgroups.
   - GPU Operator with `gds.enabled=true` + `driver.kernelModuleType=open` (current name) installed cluster-wide.

## ETCD setup

For elastic / multi-node clusters NIXL needs ETCD. Production patterns:

- **3-node ETCD** for HA. Comma-separate endpoints: `NIXL_ETCD_ENDPOINTS=http://e1:2379,http://e2:2379,http://e3:2379`.
- **Bitnami ETCD Helm chart** for K8s. Mount its Service into NIXL pods.
- **Single-node** for lab: `docker run -d --name etcd -p 2379:2379 quay.io/coreos/etcd:v3.5.1 etcd --listen-client-urls http://0.0.0.0:2379 --advertise-client-urls http://localhost:2379`.

NIXL agents auto-detect ETCD via the env var. The metadata namespace inside ETCD is per-agent — use unique agent names.

When a peer leaves, call `agent.invalidate_local_metadata()` (no IP/port) to evict from ETCD; otherwise the metadata stays and other agents will keep retrying connections.

## NIXL environment variables

| Variable | Purpose | Default | Notes |
|---|---|---|---|
| `NIXL_PLUGIN_DIR` | Search path for dynamic plugins | wheel-managed | `ls $NIXL_PLUGIN_DIR/libplugin_*.so` to verify |
| `NIXL_ETCD_ENDPOINTS` | ETCD client endpoints (comma-sep) | unset | Required for ETCD-mode metadata exchange |
| `NIXL_TELEMETRY_ENABLE` | Master telemetry switch | `false` | `y/yes/on/true/enable/1` (case-insensitive) |
| `NIXL_TELEMETRY_EXPORTER` | Exporter plugin name | unset | `prometheus` for beta exporter; empty + `NIXL_TELEMETRY_DIR` set → cyclic buffer |
| `NIXL_TELEMETRY_DIR` | Cyclic-buffer output directory | unset | Required for cyclic-buffer mode |
| `NIXL_TELEMETRY_BUFFER_SIZE` | Events in cyclic buffer | `4096` | Bump if events drop |
| `NIXL_TELEMETRY_RUN_INTERVAL` | Flush interval ms | `100` | Cyclic buffer only |
| `CUFILE_ENV_PATH_JSON` | cuFile config path | unset | For GDS plugin; see `references/plugins.md` cuda_gds section |
| `UCX_TLS` | UCX transports allowed | UCX-default | `cuda_copy,sm,tcp` minimum for vLLM+CUDA |
| `UCX_NET_DEVICES` | UCX NIC restriction | UCX-default | e.g. `mlx5_0:1` |
| `UCX_LOG_LEVEL` | UCX log verbosity | `warn` | `info`/`debug`/`trace` for diagnosis |

Plus per-plugin env vars (e.g., libfabric `FI_*`, UCCL `UCCL_*`) — see each plugin's README.

## NIXLBench

Comprehensive benchmark for NIXL. ETCD-coordinated.

```bash
cd nixl/benchmark/nixlbench/contrib
docker build -t nixlbench .
# Or build from source via meson + ninja (see contrib/README)
```

Two workers (initiator + target), one ETCD. Example UCX VRAM↔VRAM:

```bash
# Worker 1 (target) — first started becomes target after a sleep race; use --runtime_type
NIXL_PLUGIN_DIR=/path/to/plugins \
  ./nixlbench --etcd-endpoints http://etcd:2379 \
    --backend=UCX --runtime_type=ETCD \
    --initiator_seg_type=VRAM --target_seg_type=VRAM \
    --start_batch_size=1 --max_batch_size=512 \
    --total_buffer_size=$((32*1024*1024*1024))

# Worker 2 (initiator) — same command, different host
```

Communication patterns:
- `pairwise` (default): point-to-point.
- `many-to-one`: multiple initiators → one target. Stress test for the target.
- `one-to-many`: one → multiple targets.
- `tp`: tensor-parallel layout.

Worker types:
- `nixl` (default): full backend support.
- `nvshmem`: GPU-focused, VRAM-only.

Key flags:
- `--device_list mlx5_0` — restrict NICs.
- `--gpunetio_device_list 0` — for GPUNETIO backend.
- `--num_threads N` — concurrency.
- `--check_consistency` — data validation, slower but catches corruption.

**v1.0.1 PRs to know:**
- #1502: NIXLBench can run without ETCD (sleeps to prevent both processes becoming clients, #1560).
- #1495: pairwise SG stats scaling fixed for multi-rank.
- #1454: Neuron support added.
- #1421: poll-shutdown fix (hangs on Ctrl-C resolved).

Output includes latency percentiles (p50/p95/p99) plus throughput. Parse the JSON output for downstream dashboards.

## KVBench

`benchmark/kvbench/` — higher-level KV-cache-shaped workload generator. Python; reads model configs and generates realistic KV transfer patterns.

```bash
cd benchmark/kvbench
pip install -e .
python -m kvbench --help
```

Subcommand layout: `commands/` directory has individual benchmark drivers; `models/` has tokenizer/model configs; `runtime/` has the harness. `docs/` has tutorials.

Use this when "wire-speed nixlbench number" isn't enough and you need "what does Llama-70B prefill→decode KV transfer look like in practice."
