# gpu-operator host-side contract

The skill's scope ends at the host being healthy. This file documents what gpu-operator expects FROM the host so a Kubernetes admin can wire the operator on top correctly, plus failure-mode triage where the cuda-validator pod's symptom points back to a host gap.

## Versions in scope

- **v25.10.1** (Dec 2025) — first version with HGX B300 + GB300 NVL72 support. Default driver 580.95.05. (User's currently-deployed version.)
- **v26.3.0** (Mar 2026) — adds NRI plugin, dynamic MIG configmaps, NVIDIADriver CRD. Default driver 580.126.20.
- **v26.3.1** (Apr 2026) — adds `hostNetwork` for ClusterPolicy/NVIDIADriver operands. Same default driver.
- **v26.3.2** (2026-05-29) — Kubernetes 1.36 support, NRI plugin on CRI-O v1.34+, DCGM-exporter pod metadata (`enablePodLabels`, `enablePodUID`) + custom DaemonSet annotations, driver-upgrade label staleness fix. Same default driver.
- **v26.3.3** (2026-06-25) — **latest.** Device Plugin + GFD to v0.19.3, and a fix for a **v26.3.2 regression** that unconditionally enabled `MOFED_ENABLED` / `GDS_ENABLED`, injecting unintended network interfaces and disrupting RDMA workloads. On an RDMA chassis, skip 26.3.2 and go straight to 26.3.3. Default driver still 580.126.20.

## Pre-installed driver mode

For B300, the recommended path is **pre-installed driver mode** — the host owns driver + fabricmanager + nvlsm; the operator skips its driver DaemonSet and uses what's already there.

Helm install command:

```bash
helm install --wait gpu-operator \
  -n gpu-operator --create-namespace \
  nvidia/gpu-operator \
  --version=v26.3.3 \
  --set driver.enabled=false \
  --set toolkit.enabled=false
```

`driver.enabled=false` skips the `nvidia-driver-daemonset`. `toolkit.enabled=false` skips the `nvidia-container-toolkit-daemonset` (since [[recipe]] step 8 installed it on the host already).

**Important**: there is NO `validator.driver.enabled` field in the upstream `values.yaml`. The validator's driver-validation init container always runs and uses the operator image. It cannot be disabled via helm. Setting `validator.driver.enabled` is a no-op.

## What runs on each node

After install, the following DaemonSets are visible:

```
kubectl get ds -n gpu-operator
```

| DaemonSet | Pre-installed driver mode | Notes |
|---|---|---|
| `nvidia-driver-daemonset` | NOT scheduled | because `driver.enabled=false` |
| `nvidia-container-toolkit-daemonset` | NOT scheduled | because `toolkit.enabled=false` |
| `nvidia-operator-validator` | YES | runs `driver-validation`, `toolkit-validation`, `cuda-validation` init containers |
| `nvidia-device-plugin-daemonset` | YES | exposes `nvidia.com/gpu` resources |
| `nvidia-dcgm` + `nvidia-dcgm-exporter` | YES | DCGM v4 |
| `gpu-feature-discovery` | YES | NFD labels |
| `nvidia-mig-manager` | YES if MIG configured | skip on B300 unless using MIG |
| `nvidia-cuda-validator-*` | ephemeral pods, on demand | not a DaemonSet |

## The validator chain (where things actually break)

The `nvidia-operator-validator` pod runs init containers in order:

1. `driver-validation` — checks driver loaded + version
2. `toolkit-validation` — checks container toolkit configured
3. `cuda-validation` — runs the actual vectorAdd CUDA kernel
4. `plugin-validation` — verifies device plugin registered

The `nvidia-cuda-validator-*` ephemeral pod has `args: ["vectorAdd"]` and is privileged with `NVIDIA_VISIBLE_DEVICES=all`. Its job is to run a tiny CUDA kernel that allocates a device vector and adds two vectors. **If FM isn't running, this is exactly where the failure surfaces.**

## NodeFeatureDiscovery labels the operator cares about

```
feature.node.kubernetes.io/pci-10de.present=true    # NVIDIA vendor present
nvidia.com/gpu.deploy.driver=pre-installed          # tells controller to skip driver DS
nvidia.com/gpu.deploy.container-toolkit=pre-installed
nvidia.com/gpu.deploy.device-plugin=true
nvidia.com/gpu.deploy.dcgm-exporter=true
nvidia.com/gpu.deploy.gpu-feature-discovery=true
nvidia.com/gpu.deploy.mig-manager=true            # only with MIG
nvidia.com/gpu.deploy.operator-validator=true
```

If a node has `nvidia.com/gpu.deploy.driver=true` but helm sets `driver.enabled=false`, the DaemonSet still gets skipped for THIS node — but mislabeled nodes can silently confuse troubleshooting. Check labels with:

```bash
kubectl get nodes -l feature.node.kubernetes.io/pci-10de.present=true -o jsonpath='{range .items[*]}{.metadata.name}{"\n  "}{.metadata.labels}{"\n"}{end}' | grep nvidia.com
```

## What the operator does NOT manage in pre-installed mode

In pre-installed-driver mode the operator does NOT manage:
- `nvidia-fabricmanager.service` lifecycle
- `nvidia-nvlsm.service` lifecycle
- Driver kernel modules (host owns them via DKMS or precompiled)
- DOCA-OFED modules
- Container toolkit configuration of `/etc/containerd/config.toml`

You own all of those on the host. The operator just verifies they're working and then schedules pods.

## The five host-side prerequisites the operator silently depends on

Before scheduling any pods on a node, the operator checks:

1. `nvidia-smi` returns valid output (all GPUs visible, driver loaded)
2. Fabric registration succeeded for each GPU (`nvidia-smi -q -i 0 | grep -A 2 Fabric` shows `State: Completed`, `Status: Success`)
3. Container runtime is configured for nvidia (`/etc/containerd/config.toml` or `/etc/docker/daemon.json`)
4. `nvidia.com/gpu` resources advertised by the device plugin
5. NodeFeatureDiscovery has labeled the node with PCI vendor

If (2) fails — which is what FM-not-running causes — the cuda-validator pod fails. The trail looks like:

```
FM not running on host
  ↓
nvidia-smi shows Fabric "Not Initialized"
  ↓
cuda-validator runs vectorAdd
  ↓
cudaMalloc fails with cudaErrorSystemNotReady
  ↓
log: "failed to allocate device vector A, error code system not yet initialized"
  ↓
cuda-validator pod CrashLoopBackOff
  ↓
nvidia-operator-validator stuck Init
  ↓
nvidia-device-plugin-daemonset not scheduled
  ↓
nvidia.com/gpu resources not advertised
  ↓
no GPU workloads can run
```

The fix is always: confirm FM running on host, version matching driver. See [[troubleshooting]] for the symptom drill-down.

## Symptom → cause map

| Validator-pod symptom | Most likely host cause |
|---|---|
| cuda-validator: "failed to allocate device vector A, error code system not yet initialized" | `nvidia-fabricmanager.service` not running OR not version-matched to loaded driver |
| driver-validator: "unable to get device name: failed to find device with id '3182'" | gpu-operator issue #2231 — B300 PCI ID missing from validator name table. Benign warning, not fatal. |
| nvidia-device-plugin-daemonset: "no NVIDIA devices found" | Driver not loaded on host, or wrong kernel module variant (proprietary on Blackwell) |
| toolkit-validation: "could not find runtime binary" | `nvidia-container-toolkit` not installed on host |
| All validators looking healthy but workloads fail at runtime | NVLSM not running OR fabric registration incomplete |
| First boot only: validator CrashLoopBackoff that self-heals after 1-2 minutes | Normal — FM takes 30-90s to register 8 B300 GPUs on first start. Only sustained >3 min is real |

## Known issue #2231 — B300 PCI 0x3182 (benign)

Repro:
- gpu-operator 25.10.1 (also reported on 26.3.x)
- Pre-installed driver on B300 SXM6
- Ubuntu 24.04.1 LTS
- K8s 1.33

Symptom:

```
time="2026-03-18T15:43:34Z" level=warning msg="unable to get device name: failed to find device with id '3182'"
time="2026-03-18T15:43:37Z" level=info msg="Creating link /host-dev-char/195:0 => /dev/nvidia0"
```

Status: OPEN as of 2026-05-21 with `more-information-needed` label. NVIDIA response: "B300 should be supported. Can you please share the must_gather logs."

**Impact**: cosmetic. The `nvidia-operator-validator` init container loops on the warning but the device symlinks ARE created and real workloads function. Operator-validator may stay in Init state cosmetically.

**Workaround**: none confirmed. To nudge upstream, run `./hack/must-gather.sh` from https://github.com/NVIDIA/gpu-operator and attach to the issue.

Track: https://github.com/NVIDIA/gpu-operator/issues/2231

## Known issue #1595 — FM start broken in driver 570.158.01

Affects **operator-managed driver mode** (`driver.enabled=true`) only. Pre-installed-driver mode (the recommended B300 path) is unaffected.

On operator-managed driver mode with driver 570.158.01:
- Symptom: FM start script in the driver container errors with "Unknown option: /usr/share/nvidia/nvswitch/fabricmanager.cfg"
- Fix: pin driver to ≥ 570.172.08, OR move to 580+

Closed 2025-11-17. Most B300 fleets are on 580+ now anyway.

Track: https://github.com/NVIDIA/gpu-operator/issues/1595

## Known issue: nvidia-peermem post-driver-restart

Carried in 26.3.x release notes:

> nvidia-peermem container fails to restart after driver pod restart without recompilation. Workaround: Set `FORCE_REINSTALL=true` (forces full recompilation, node drain, GPU disruption) or reboot node.

Affects only operator-managed driver mode. Pre-installing the driver and putting `nvidia-peermem` on the host avoids this entirely.

## Air-gap operator install

Mirror these images for v26.3.3 pre-installed mode:

```
nvcr.io/nvidia/gpu-operator:v26.3.3
nvcr.io/nvidia/k8s-device-plugin:v0.19.0
nvcr.io/nvidia/cloud-native/k8s-driver-manager:v0.10.0    # only needed for operator-managed driver mode
nvcr.io/nvidia/cloud-native/gpu-feature-discovery:v0.19.0
nvcr.io/nvidia/cloud-native/dcgm-exporter:4.5.2-1
nvcr.io/nvidia/cloud-native/k8s-mig-manager:v0.14.0       # only if using MIG
nvcr.io/nvidia/cloud-native/nvidia-fs:<tag>               # only if using GDS
nvcr.io/nvidia/cloud-native/k8s-cc-manager:v0.4.0         # only if using Confidential Containers
```

Plus an NFD image. Use `skopeo sync` or a Harbor pull-through cache. Then in helm values:

```yaml
operator:
  repository: registry.internal.lan/nvcr.io/nvidia
imagePullSecrets:
- name: internal-registry-creds

driver:
  enabled: false
toolkit:
  enabled: false

# Each component needs repository override
devicePlugin:
  repository: registry.internal.lan/nvcr.io/nvidia
gfd:
  repository: registry.internal.lan/nvcr.io/nvidia/cloud-native
dcgm:
  repository: registry.internal.lan/nvcr.io/nvidia/cloud-native
dcgmExporter:
  repository: registry.internal.lan/nvcr.io/nvidia/cloud-native
validator:
  repository: registry.internal.lan/nvcr.io/nvidia
```

## References

- gpu-operator release notes: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/release-notes.html
- Platform support matrix: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html
- Install guide: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/install-gpu-operator.html
- Upstream source: https://github.com/NVIDIA/gpu-operator
- Issue #2231 (B300 PCI 0x3182): https://github.com/NVIDIA/gpu-operator/issues/2231
- Issue #1595 (FM 570.158.01): https://github.com/NVIDIA/gpu-operator/issues/1595
- Issue #2463 (CONFIG_MEMORY_HOTPLUG hostPath): https://github.com/NVIDIA/gpu-operator/issues/2463 — CLOSED 2026-07-07
