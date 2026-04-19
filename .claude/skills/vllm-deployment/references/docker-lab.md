# Docker / Podman — single-node lab recipes

For dev boxes, 1-to-2-node labs, and kicking the tyres on a new model before handing it to the k8s operator. For cluster deployment, this is not the right reference — see `references/pod-shape.md`.

## `docker run` canonical template

```bash
docker run --rm -it \
  --name vllm \
  --gpus all \
  --shm-size=10.24g \
  --ipc=host \
  -p 8000:8000 \
  -e HUGGING_FACE_HUB_TOKEN=$HF_TOKEN \
  -e HF_HOME=/models/.cache \
  -e VLLM_NO_USAGE_STATS=1 \
  -e VLLM_DO_NOT_TRACK=1 \
  -v ~/.cache/huggingface:/models/.cache \
  -v /data/models:/models \
  vllm/vllm-openai:<pinned-tag> \
  --model Qwen/Qwen3-8B \
  --tensor-parallel-size 1
```

**Both `--shm-size` and `--ipc=host` are required for TP>1.** `--ipc=host` alone works on most hosts; pair with `--shm-size` for safety. Missing one → silent NCCL segfault on first all-reduce.

Canonical in-repo citation: ``vllm` repo: docs/getting_started/installation/gpu.cuda.inc.md:207,212,251,263,271-272` — *"You can either use the `ipc=host` flag or `--shm-size` flag to allow the container to access the host's shared memory. vLLM uses PyTorch, which uses shared memory to share data between processes."*

Also: ``vllm` repo: docs/deployment/docker.md` · `docs/deployment/nginx.md:95,105` · `docs/serving/parallelism_scaling.md:175,181-182` · `examples/online_serving/run_cluster.sh:120,127`.

## GPU selection: `--gpus` vs `--device` vs MIG

### `--gpus all` (preferred)

Standard NVIDIA Container Toolkit path. Requires `nvidia-container-toolkit` installed on host.

```bash
docker run --gpus all ...                       # all GPUs
docker run --gpus 'device=0,1' ...              # GPU 0 and 1
docker run --gpus '"device=0,1"' ...            # shell quoting for explicit list
```

- **Install docs**: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

### `--device` fallback

Works when `--gpus` doesn't (rootless, old Docker, unusual setups):

```bash
docker run \
  --device /dev/nvidia0 \
  --device /dev/nvidiactl \
  --device /dev/nvidia-uvm \
  --device /dev/nvidia-uvm-tools \
  ...
```

Manually mounting the device nodes. Also loses the toolkit's library injection, so the CUDA libs must be baked into the image. Rarely the right answer.

### MIG

MIG-partitioned GPUs show up as distinct devices:

```bash
# CLI form
docker run --gpus 'device=0:0,0:1' ...

# CDI form (preferred on modern toolkit)
docker run --device nvidia.com/mig=all ...
docker run --device nvidia.com/gpu=MIG-<uuid> ...
```

Check `nvidia-smi -L` for MIG UUIDs.

## Multi-NIC NCCL (`NCCL_SOCKET_IFNAME`)

If the host has multiple NICs (common on dev servers with `eth0` + `wlan0` + `docker0` + VPN), NCCL auto-selection picks the wrong one and hangs on bootstrap. Pin:

```bash
docker run ... \
  -e NCCL_SOCKET_IFNAME=eth0 \
  -e GLOO_SOCKET_IFNAME=eth0 \
  -e VLLM_HOST_IP=<host-ip-on-eth0> \
  ...
```

For IB/RoCE: `-e NCCL_IB_DISABLE=0 -e NCCL_IB_HCA=mlx5_*`

**vLLM debugging guide**: https://docs.vllm.ai/en/stable/getting_started/debugging/

## Rootless Docker + `nvidia-container-toolkit`

Rootless + NVIDIA is fiddly. Two friction points:

1. CDI injection fails in rootless mode ([NVIDIA/nvidia-container-toolkit#434](https://github.com/NVIDIA/nvidia-container-toolkit/issues/434)).
2. Rootful and rootless GPU access on the same host require conflicting configs ([#85](https://github.com/NVIDIA/nvidia-container-toolkit/issues/85)).

Workaround:

```bash
sudo nvidia-ctk config --set nvidia-container-cli.no-cgroups --in-place
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
# Now rootless docker can use --device nvidia.com/gpu=all
```

But this breaks rootful GPU use on the same host. Pick one mode per host.

CDI overview: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html

## Podman

Podman does **not** accept `--gpus all` natively. Use the CDI form:

```bash
podman run --rm -it \
  --device nvidia.com/gpu=all \
  --security-opt=label=disable \
  --shm-size=10.24g \
  --ipc=host \
  -p 8000:8000 \
  vllm/vllm-openai:<pinned-tag> \
  --model Qwen/Qwen3-8B
```

Notes:

- `--security-opt=label=disable` is needed on SELinux hosts (Fedora, RHEL) unless proper SELinux types are configured. Acceptable in a lab; don't carry to production.
- `nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` produces the CDI spec that `nvidia.com/gpu=all` resolves against.
- **Official RHAIIS podman recipe**: https://docs.redhat.com/en/documentation/red_hat_ai_inference_server/3.2/html/getting_started/inference-rhaiis-with-podman-nvidia-cuda_getting-started
- **Community walk (RHEL/Fedora)**: https://thenets.org/how-to-use-nvidia-gpu-on-podman-rhel-fedora/
- **Red Hat — profiling vLLM with podman**: https://developers.redhat.com/articles/2025/10/16/profiling-vllm-inference-server-gpu-acceleration-rhel

### podman-compose

Understands the `deploy.resources.reservations.devices` shape:

```yaml
services:
  vllm:
    image: vllm/vllm-openai:<pinned-tag>
    shm_size: "10.24g"
    ipc: host
    ports: ["8000:8000"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: cdi
              device_ids: ["nvidia.com/gpu=all"]
```

## Docker Compose — 2-node disagg PD lab

The vLLM repo **does not ship** a docker-compose for disagg. Reference shell scripts:

- ``vllm` repo: examples/online_serving/disaggregated_prefill.sh`
- ``vllm` repo: examples/online_serving/disaggregated_serving_p2p_nccl_xpyd/disagg_example_p2p_nccl_xpyd.sh`

Single-host 2-engine PD compose template (lab-grade, NIXL over shared network):

```yaml
# compose-disagg.yaml — 1P1D on one host, two GPUs. Lab only.
services:
  vllm-prefill:
    image: vllm/vllm-openai:<pinned-tag>
    shm_size: "10.24g"
    ipc: host
    command:
      - "--model=Qwen/Qwen3-8B"
      - "--port=8001"
      - "--gpu-memory-utilization=0.5"
      - "--kv-transfer-config"
      - '{"kv_connector":"NixlConnector","kv_role":"kv_producer","kv_rank":0,"kv_parallel_size":2}'
    ports: ["8001:8001"]
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - VLLM_HOST_IP=0.0.0.0
      - VLLM_NO_USAGE_STATS=1
    deploy: {resources: {reservations: {devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]}}}

  vllm-decode:
    image: vllm/vllm-openai:<pinned-tag>
    shm_size: "10.24g"
    ipc: host
    command:
      - "--model=Qwen/Qwen3-8B"
      - "--port=8002"
      - "--gpu-memory-utilization=0.5"
      - "--kv-transfer-config"
      - '{"kv_connector":"NixlConnector","kv_role":"kv_consumer","kv_rank":1,"kv_parallel_size":2}'
    ports: ["8002:8002"]
    environment:
      - CUDA_VISIBLE_DEVICES=1
      - VLLM_HOST_IP=0.0.0.0
      - VLLM_NO_USAGE_STATS=1
    deploy: {resources: {reservations: {devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]}}}

  proxy:
    build: .                     # run disagg_proxy_demo.py from vllm examples
    ports: ["8000:8000"]
    depends_on: [vllm-prefill, vllm-decode]
```

For a maintained, supported path: use **vllm-production-stack** (Helm) even on a single laptop via `minikube`, or follow the LMCache compose quickstart: https://docs.lmcache.ai/getting_started/quickstart/disaggregated_prefill.html

## Observability compose (for dashboard dev)

The repo does ship a compose for Prometheus + Grafana:

- ``vllm` repo: examples/observability/prometheus_grafana/docker-compose.yaml`

Useful for developing Grafana dashboards before handing off to k8s. See `vllm-observability` skill.

## Building a custom image

Dockerfiles in the repo:

| File | Purpose |
|---|---|
| `Dockerfile` | Main CUDA (base `nvidia/cuda:13.0.0-devel-ubuntu22.04`, runtime `nvidia/cuda:13.0.0-base-ubuntu22.04`) |
| `Dockerfile.rocm` / `Dockerfile.rocm_base` | AMD ROCm |
| `Dockerfile.cpu` | CPU-only |
| `Dockerfile.tpu` | Google TPU |
| `Dockerfile.xpu` | Intel XPU |
| `Dockerfile.nightly_torch` | PyTorch nightly |
| `Dockerfile.ppc64le`, `Dockerfile.s390x` | Non-x86 |
| `docker-bake.hcl` | buildx bake |
| `tools/generate_versions_json.py` → `versions.json` | Version source of truth |

Build args worth knowing: `CUDA_VERSION=13.0.0`, `PYTHON_VERSION=3.12`, `UBUNTU_VERSION=22.04`, `PIP_INDEX_URL`, `UV_INDEX_URL` (private mirror support).

## Common single-node pitfalls

1. **Forgot `--shm-size` on TP>1** → segfault. Always include both `--shm-size` and `--ipc=host` for safety.
2. **`:latest` tag** → different behavior on `docker pull` tomorrow. Pin to a version.
3. **Model cache re-downloaded every run** → mount `~/.cache/huggingface:/root/.cache/huggingface` or point `HF_HOME` at a host volume.
4. **Random ports on multi-GPU lab** → default port 8000 conflicts between two containers. Use `-p 8001:8001 --port 8001` on one of them.
5. **GPU visibility across containers** → `CUDA_VISIBLE_DEVICES=0` inside the container **after** `--gpus` exposes devices to the runtime. With `--gpus device=0`, the container sees only that GPU and `CUDA_VISIBLE_DEVICES=0` means "the one it sees".
6. **Telemetry to `stats.vllm.ai`** → set `VLLM_NO_USAGE_STATS=1 VLLM_DO_NOT_TRACK=1` even on a lab; avoids failed POSTs in the log.

## Scaling up to k8s

Once the lab setup works, promoting it:

1. Copy the env vars, not the `docker run` flags. `--shm-size` → `emptyDir {medium: Memory}`; `--ipc=host` → irrelevant on k8s (no equivalent); `--gpus` → `resources.limits.nvidia.com/gpu`.
2. Replace the PVC ReadOnlyMany for `/models` and `/root/.cache`.
3. `nodeSelector` for SKU (see `references/pod-shape.md`).
4. Helm chart from `examples/online_serving/chart-helm/` is experimental — use **vllm-production-stack** Helm for anything beyond demo.
