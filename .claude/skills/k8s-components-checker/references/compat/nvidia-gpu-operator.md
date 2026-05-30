# NVIDIA GPU Operator — compat (sifted from published_matrix)

- **Primary source:** https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html
- **Secondary sources:**
  - https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/release-notes.html
  - https://github.com/NVIDIA/gpu-operator/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 25.3
- **Last sifted:** 2026-05-31
- **2026-05-31 matrix-grounded (platform-support page):** the 26.3 k8s window is **1.32 – 1.36** —
  **26.3.2 added k8s 1.36** (earlier entries said 1.32–1.35; the prior "presumed unchanged" caveat is
  now lifted and § 26.3.2 is sifted below). The floor is **1.32** across the whole 26.3 line — **not
  1.29** (1.29 is the *25.10* line's floor; don't conflate the two). `releases/latest` = **v26.3.2**
  (gh, 2026-05-30). (House Rule #8 · `references/version-verification.md`)

Lifecycle (per upstream): 26.3.x **current**; 25.10.x **deprecated** (critical fixes only); 25.3.x and lower **end of support**. Upgrades supported only within a major or to the next major — don't jump 25.3 → 26.3 in one step.

GPU architecture floor (cross-version, set by silicon, not by operator minor):

- **Blackwell HGX B200 / GB200 NVL:** driver ≥ R570.133.20.
- **Blackwell HGX B300 / GB300 NVL72:** first explicitly listed in 25.10; needs R580 family in practice (operator default 580.95.05+ at 25.10, 580.126.20 at 26.3).
- **Blackwell RTX PRO 6000 Server Edition:** driver ≥ 575.57.08. MIG unsupported on 575.57.08 — bump to a later patch for MIG.
- **Hopper H100/H200/H800/H20:** R535+ works; R570+ recommended for newer features.
- **Grace Hopper GH200:** open kernel modules **mandatory** (same module-type rule as Blackwell).
- **Ada / Ampere / Turing / Volta / Pascal:** all branches in the tracked window work.

Cross-version known issue: drivers 570.124.06, 570.133.20, 570.148.08, 570.158.01 can't schedule mixed MIG-sliced + full-GPU on the same node — workaround is upgrade to ≥ 580.65.06 (or 570.172.08 for the 570 branch). Bites any operator minor whose default lands on those drivers.

**Upgrade hazard — host-driver / loaded-module mismatch after an OS package upgrade**
(cross-version; applies whenever a node-OS bump rides along with a k8s upgrade and
the driver is **host-managed**, e.g. Ubuntu `unattended-upgrades`, not the operator's
own driver DaemonSet). The package upgrade replaces the userspace libs **and** the
on-disk `.ko`, but the **old kernel module stays loaded** until reboot →
`nvidia-smi` exits **18** (`NVML_ERROR_LIB_RM_VERSION_MISMATCH`) → the GPU
device-plugin / operand pods `RunContainerError`-crashloop indefinitely (observed for
weeks). **Not** flagged by `/var/run/reboot-required` (it's a DKMS change, not a
kernel/libc bump), so a reboot-required gate misses it. A reboot loads the new module
and clears it (rc 18 → 0).
- **Detect:** `nvidia-smi; echo $?` → `18`; or loaded vs on-disk version differ —
  `sed -n 's/.*Kernel Module *\([0-9.]*\).*/\1/p' /proc/driver/nvidia/version` (loaded)
  vs `modinfo -F version nvidia` (on-disk).
- **Don't conflate with a broken install:** rc **9** (driver not loaded) / **12**
  (lib missing) is a broken/absent driver — a reboot won't fix it and may strand the
  node driverless. The mismatch trigger is specifically rc 18 (or loaded ≠ on-disk).
- **Health assert is `nvidia-smi` rc == 0**, never an enumerated failure-code list —
  the man-page return-code table is incomplete (omits 18). Skip nodes with no
  `nvidia-smi` binary (`command -v nvidia-smi`) so non-NVIDIA hosts don't false-fail.
- Field-validated 2026-05-30 (community RKE2 1.32 → 1.33 on Ubuntu GPU nodes).

## 26.3.2

- **k8s floor:** 1.32 – **1.36** (1.36 added on the 26.3 line; NVIDIA platform-support matrix grounded 2026-05-31).
- **Driver branches:** 26.3 line (default 580.126.20) — see § 26.3.0.
- **Notable:** DCGM Exporter adds `enablePodLabels` / `enablePodUID` / `podLabelAllowlistRegex` (additive). On RKE2/K3s, prefer the **NRI Plugin** (see § 26.3.0) — set `cdi.nriPluginEnabled: true` rather than the toolkit `CONTAINERD_SOCKET` env; needs containerd ≥ 1.7.30 / 2.1.x / 2.2.x, not supported with CRI-O. NRI host prereq field-verified on RKE2 (containerd 2.2.x, NRI live) 2026-05-31.

## 26.3.1

- **k8s floor:** 1.32 – 1.36
- **Driver branches:** default 580.126.20, recommended 580.159.03; also 595.71.05, 595.58.03, 590.48.01, 570.211.01, 535.309.01, 535.288.01
- **Breaking:** pods with `spec.hostUsers: false` (k8s user namespaces) **not supported** — container creation fails with "No such process". Audit any policy that enables user namespaces before bumping.
- **Notable:** all operands gain `hostNetwork` toggle; precompiled drivers now mount `/lib/modules` from host (required for SLES 15 SP7 / SLES 16); OLM bundle KubeVirt GPU Device Plugin multi-arch fix.

## 26.3.0

- **k8s floor:** 1.32 – 1.36
- **Container runtime:** containerd 1.7 – 2.2, CRI-O. NRI Plugin requires containerd ≥ 1.7.30 / 2.1.x / 2.2.x.
- **Driver branches:** default 580.126.20; same set as 26.3.1.
- **Breaking:**
  - NRI Plugin (when enabled) creates no `nvidia` runtime class and makes no container-runtime config changes — **incompatible with CRI-O**.
  - `defaultRuntime` field in ClusterPolicy now optional (was required).
- **CRD migrations:**
  - **New `NVIDIADriver` CRD** — manages multiple driver types/versions across nodes. **Greenfield only**: not supported as an upgrade path from earlier minors. Existing ClusterPolicy installs stay on the ClusterPolicy driver spec.
  - Dynamic MIG config now uses per-node ConfigMaps (replaces single static ConfigMap). MIG Manager v0.14.0+ auto-generates them.
- **Upgrade ordering:** driver pods reuse kernel modules across container restarts instead of recompiling — restart recovery drops from minutes to seconds. No NFD ordering change.
- **Deprecations:**
  - NVIDIA Kata Manager deprecated → use `kata-deploy`.
  - `useOpenKernelModules` deprecated → `kernelModuleType` (`auto`/`open`/`proprietary`); `auto` requires driver ≥ 570.86.15 or 570.124.06+.
- **Notable:**
  - NRI Plugin added (alternative to runtime-class injection).
  - Driver validation now waits for GDS / GDRCopy additional drivers before proceeding.
  - DCGM + DCGM Exporter gain liveness/readiness probes.
  - PodSecurityContext support on DaemonSets.
  - New OS adds: Rocky Linux 9.7 / 10.0 / 10.1, RHEL 10.0 / 10.1 / 9.7, K3s, containerd 2.2.
- **Known issues:** GPUDirect RDMA — `nvidia-peermem` container may fail to restart after driver pod restart without node reboot; workaround `FORCE_REINSTALL=true`. RHEL 8 + pre-installed driver + MIG Manager ≥ v0.13.1 fails on GLIBC mismatch — pin MIG Manager v0.12.3. Deleting the default NVIDIADriver CR can strand custom CRs in pending — restart controller pod.

## 25.10.1

- **k8s floor:** 1.29 – (matrix ceiling per 25.10 line; 1.33 era)
- **Driver branches:** default 580.105.08
- **Notable:** DCGM Exporter gains HPC job-mapping metrics; cluster-policy reconciler hardened against node-update races; fixed driver daemonset not applying user-supplied kernel module params; fixed driver image misassignment in multi-nodepool clusters.
- **Known issues:** SELinux enforcing — MIG Manager fails to schedule on GPU nodes due to GFD permissions; workaround: switch GFD to Node Feature API.

## 25.10.0

- **k8s floor:** 1.29 (raised from earlier)
- **Driver branches:** default 580.95.05; also 570.195.03, 535.274.02
- **Breaking:**
  - **CDI enabled by default** (`cdi.enabled: true`); `cdi.default` field deprecated. Standard workloads unaffected; **GPU management containers that bypass the device plugin must set `runtimeClassName: nvidia`**. OpenShift users: OLM doesn't mutate CRs on upgrade — flip CDI in ClusterPolicy by hand post-upgrade.
- **CRD migrations:** ClusterPolicy CDI default flipped; vGPU licensing migrated from configMap to secret-based tokens (configMap path still works; secret recommended).
- **Notable:**
  - First explicit support for **HGX B300 / HGX GB300 NVL72** with new MIG profiles.
  - MIG-backed vGPU on capable GPUs (select via node label).
  - **NVIDIA Network Operator v25.7.0** integration (DOCA / RDMA path).
  - Driver pod containers gain configurable resource requests/limits.
  - New platforms: Mirantis k0s, OpenShift 4.20.
- **Known issues:**
  - CRI-O: pods stuck in `Init:RunContainerError` / `Init:CreateContainerError` during install/upgrade.
  - NVIDIA Container Toolkit 1.18.0 **overwrites containerd imports field** — non-obvious config loss.
  - MIG-backed vGPU on RTX Pro 6000 Blackwell: vgpu-device-manager fails with default config; needs custom ConfigMap with GFX suffix.
  - GKE 1.33+: set `RUNTIME_CONFIG_SOURCE=file` to prevent containerd misconfig.

## 25.3.4 / 25.3.3 / 25.3.2 / 25.3.1

Patch releases — no breaking, no CRD migrations, no k8s-floor change beyond 25.3.0. Bug fixes only. Per upstream: 25.3.x is end-of-support — no new patches expected.

## 25.3.0

- **k8s floor:** 1.25 – 1.33 (matrix ceiling on the 25.3 line)
- **Container runtime:** containerd 1.6 – 2.0, CRI-O. Containerd 2.0 newly supported.
- **Driver branches:** R535, R550, R570, R580. Default 570.172.08, recommended 580.65.06, minimum 535.247.01.
- **Breaking:** none at the CRD shape; default driver module type **flipped to open** starting R570 (matches NVIDIA's open-modules transition — Blackwell + Grace Hopper are open-only anyway).
- **CRD migrations:** new `kernelModuleType` field on ClusterPolicy + NVIDIADriver APIs (`auto` / `open` / `proprietary`); `auto` requires driver ≥ 570.86.15 or 570.124.06+.
- **Deprecations:** `useOpenKernelModules` deprecated → use `kernelModuleType`.
- **Notable:**
  - First operator minor with explicit **HGX B200 / HGX GB200 NVL** support (B200 needs driver ≥ 570.133.20).
  - **NFD minimum bumped to k8s 1.29** at the dependency level (matrix floor remained 1.25 for the operator itself).
  - CDI alongside operator install (supported on k8s 1.32; not yet default — that flips in 25.10).
  - OpenShift 4.18 support added.
- **Known issues:**
  - **CDI mode incompatible with RKE2** on this line — RKE2 operators should leave CDI off until 25.10 or verify the upstream fix landed.
  - Driver 580.65.06: MIG unsupported on GB200 when CDMM enabled.
  - Mixed MIG/full-GPU scheduling broken on drivers 570.124.06 / 570.133.20 / 570.148.08 / 570.158.01 — pin 570.172.08+ on the 570 branch.
