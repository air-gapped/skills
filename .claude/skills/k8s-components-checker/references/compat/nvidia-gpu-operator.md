# NVIDIA GPU Operator — compat (sifted from published_matrix)

- **Primary source:** https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html
- **Secondary sources:**
  - https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/release-notes.html
  - https://github.com/NVIDIA/gpu-operator/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 25.3
- **Last sifted:** 2026-09-24 (added § 26.7.1, § 26.7.0, § 26.3.3; k8s window 1.33–1.37 and containerd floor 2.0 confirmed for the 26.7 line; support-status table updated)
- **Last release-verified:** 2026-09-24 (`gh` release listing + NVIDIA platform-support/release-notes pages, `NVIDIA/gpu-operator`)
- **2026-05-31 matrix-grounded (platform-support page):** the 26.3 k8s window is **1.32 – 1.36** —
  **26.3.2 added k8s 1.36** (earlier entries said 1.32–1.35; the prior "presumed unchanged" caveat is
  now lifted and § 26.3.2 is sifted below). The floor is **1.32** across the whole 26.3 line — **not
  1.29** (1.29 is the *25.10* line's floor; don't conflate the two). `releases/latest` = **v26.3.3** (2026-06-25; 26.3.2 was the prior)
  (gh, 2026-05-30). (House Rule #8 · `references/version-verification.md`)

26.7.x is current (26.7.0 2026-08-21, 26.7.1 2026-09-23) — see § 26.7.0 for the containerd-floor raise and CRD migration change, § 26.7.1 for the latest patch.

26.3.3 (2026-06-25) fixed the RDMA/NCCL device-node-leak regression — see § 26.3.3.

Lifecycle (per upstream support-status table, NVIDIA platform-support page, verified 2026-09-24): 26.7.x **Supported** (current); 26.3.x **Deprecated**; 25.10.x and lower **End of Support** (25.10.x moved straight from deprecated to end-of-support as of 26.7.0 — it no longer gets critical fixes). Upgrades supported only within a major or to the next major — don't jump 25.3 → 26.7 or 25.10 → 26.7 in one step; hop through 26.3 first.

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

**Operand-roll behavior (cross-version, field-observed 2026-05-31).** A device-plugin DaemonSet bounce
during an operator upgrade does **not** revoke an already-allocated GPU from a running container —
only *new* allocations + health reporting pause briefly; a live inference pod rides straight through
(don't drain healthy GPU pods purely for the operator bump). Separately, high device-plugin restart
*counts* are usually historical, not a live storm: the toolkit SIGHUPs containerd on its own restart →
a runc-init mount race (`open /run/nvidia-persistenced/socket: no such file`, `exit 128`) fans out many
device-plugin restarts per toolkit cycle, accrued over pod age. Triage the restart *rate*, not the count.

## 26.7.1

- **k8s floor:** 1.33 – 1.37 (unchanged from 26.7.0; NVIDIA platform-support matrix, `/26.7/platform-support.html`, verified 2026-09-24).
- **Container runtime:** containerd 2.0 – 2.3, CRI-O (unchanged from 26.7.0).
- **Driver branches:** default/recommended still 595.91.07; adds 615.71.09 (needs driver ≥ R615 for the new per-GPU CUDA memory-limit feature); also 610.57.04, 580.173.02.
- **Notable:**
  - New `NVIDIA_GPU_MEMORY_REQUEST` / `NVIDIA_GPU_MEMORY_LIMIT` env vars enforce soft/hard per-GPU CUDA memory limits (driver ≥ R615).
  - Helm `operator.leaderElection.renewDeadline` now configurable (parity with OLM installs).
  - `ComputeDomain.spec.numNodes` no longer required (defaults to `0`).
  - Component bumps: Container Toolkit v1.20.1, Driver Manager v0.12.1, Device Plugin v0.20.1, DCGM Exporter v4.6.1-4.8.4, DCGM 4.6.1-1, MIG Manager v0.15.1, GFD v0.20.1, vGPU Device Manager v0.5.1, Confidential Computing Manager v0.4.4.
- **Known issues:** upgrading the driver 595.91.07 → 615.71.09 on H100 nodes **without a reboot** can strand MIG reconfiguration (`nvidia-smi -r` fails, Xid 119). Reboot after the driver bump and before changing MIG config, or use the documented per-node pause/reset/resume workaround.

## 26.7.0

- **k8s floor:** 1.33 – 1.37 — **raised from 26.3's 1.32 – 1.36** (NVIDIA platform-support matrix, `/26.7/platform-support.html`, verified 2026-09-24); adds explicit Kubernetes 1.37, and 1.36 for Canonical MicroK8s.
- **Container runtime:** **minimum containerd raised from 1.8 to 2.0.** Release notes, verbatim: *"The minimum supported containerd version changed from 1.8 to 2.0."* Validated range containerd 2.0 – 2.3, CRI-O. This is a node prerequisite the operator cannot fix from inside the cluster — check every GPU node's containerd before planning the hop.
  - **Cross-component (RKE2):** RKE2 1.34 and 1.35 bundle containerd **v2.2.7**; 1.36 and 1.37 bundle **v2.3.4** (generated.json `edges.rke2_bundles`, compat.py sync 2026-09-24) — all four clear the 26.7.0 floor. RKE2 1.33 and earlier are not in `rke2_bundles`; confirm their bundled containerd before pairing with GPU Operator ≥ 26.7.0 (pre-2.0 bundles fail the floor).
- **Driver branches:** default/recommended 595.91.07; also 610.57.04, 580.173.02.
- **CRD migrations:** **`NVIDIADriver` CRD now supports migrating from a ClusterPolicy-managed driver** (PR #2353) — lifts the "greenfield only" restriction noted in § 26.3.0; existing ClusterPolicy installs can move to NVIDIADriver in place. New `GPUCluster` CRD (DRA Driver for NVIDIA GPUs) requires k8s ≥ 1.34.2, driver ≥ 580, a CDI-compatible runtime, and cannot coexist with ClusterPolicy on the same cluster.
- **Breaking:** driver container image tags for RHEL/Rocky now key off the OS **major** version only (matches existing Rocky behavior), for both ClusterPolicy- and NVIDIADriver-managed drivers — a custom driver-image mirror pinned to a minor-version tag breaks.
- **Notable:**
  - Helm chart now published as an OCI artifact (`oci://nvcr.io/nvidia/cloud-native-charts/gpu-operator`) alongside the classic repo.
  - DRA Driver for NVIDIA GPUs v0.5.0 — full-GPU KubeVirt VM passthrough via DRA claims (optional capabilities remain alpha, off by default).
  - AKS restored to the cloud-provider support table (previously dropped).
  - Support-status table: **26.7.x Supported (current), 26.3.x Deprecated, 25.10.x and lower End of Support** — 25.10.x moved straight from deprecated to end-of-support.
  - "Government-ready" designation added for all operands except GDS Driver, Confidential Computing Manager, and GDRCopy Driver.
  - Fixed: NRI-enabled driver containers no longer set up containerd config mounts, unblocking NRI pods on immutable hosts with read-only containerd paths.
- **Known issues:** with DRA passthrough enabled, a container-GPU claim and a VFIO-passthrough claim for the same physical GPU, allocated before either is prepared, can both win the scheduler race — the second fails. Submit serially or dedicate separate nodes to container vs. VFIO workloads.

## 26.3.3

- **k8s floor:** 1.32 – 1.36 (unchanged from 26.3.0).
- **Fixed:** the `MOFED_ENABLED` / `GDS_ENABLED` device-plugin regression that defaulted both flags on and injected every host `ibverbs` device node into GPU workload containers, breaking RDMA/NCCL network isolation on 26.3.0–26.3.2. The operator now infers both flags per node from loaded kernel modules (PR #2525, k8s-device-plugin PR #1837). Upgrade reason for any 26.3.0–26.3.2 fleet running multi-node NCCL.
- **Notable:** component matrix gains driver versions 580.178.04, 595.91.97, 610.57.04.

## 26.3.2

- **k8s floor:** 1.32 – **1.36** (1.36 added on the 26.3 line; NVIDIA platform-support matrix grounded 2026-05-31).
- **Driver branches:** 26.3 line (default 580.126.20) — see § 26.3.0.
- **Notable:** DCGM Exporter adds `enablePodLabels` / `enablePodUID` / `podLabelAllowlistRegex` (additive). On RKE2/K3s, prefer the **NRI Plugin** (see § 26.3.0) — set `cdi.nriPluginEnabled: true` rather than the toolkit `CONTAINERD_SOCKET` env; needs containerd ≥ 1.7.30 / 2.1.x / 2.2.x, not supported with CRI-O. NRI host prereq field-verified on RKE2 (containerd 2.2.x, NRI live) 2026-05-31. **25.10.1 → 26.3.2 upgrade field-validated 2026-05-31** (RKE2, NRI path, host-managed driver): ClusterPolicy reached `ready`; the `RuntimeClass "nvidia" not found` + `toolkit-validation` BackOff warnings during the roll were transient (~90 s) operand choreography, validators green — **but** any workload pinning `runtimeClassName: nvidia` then failed to recreate (see § 26.3.0 Breaking).

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
  - **NRI Plugin (`cdi.nriPluginEnabled: true`, the recommended RKE2/K3s path) creates NO `nvidia` RuntimeClass and makes no containerd `config.toml` change** — devices inject from the `nvidia.com/gpu` request alone. **This BREAKS any workload that pins `runtimeClassName: nvidia`:** already-running pods keep running (admission already passed), but the next pod (re)creation / scale-up / rollout fails admission with `RuntimeClass "nvidia" not found` — a **latent trap** that surfaces only on restart, not at upgrade time. Recreating the RuntimeClass does not help (no `nvidia` handler exists under NRI). Fix = **remove `runtimeClassName: nvidia` from GPU workloads** (CDI+NRI needs none). Treat the operator flip + a fleet-wide `grep -r 'runtimeClassName: nvidia'` sweep of manifests, generators, and docs as **ONE migration window, not two**. The key is flat `cdi.nriPluginEnabled` under top-level `cdi:` — NOT a nested `cdi.nriPlugin.enabled` block — and the chart fails the render if NRI is on while `cdi.enabled` is false. **NRI is incompatible with CRI-O.** (Field-validated 2026-05-31, RKE2 containerd 2.2.x.)
  - `defaultRuntime` field in ClusterPolicy now optional (was required).
- **CRD migrations:**
  - **New `NVIDIADriver` CRD** — manages multiple driver types/versions across nodes. **Greenfield only** on this minor: not supported as an upgrade path from earlier minors; existing ClusterPolicy installs stay on the ClusterPolicy driver spec. **Restriction lifted in 26.7.0** — see § 26.7.0 for the ClusterPolicy → NVIDIADriver migration path.
  - Dynamic MIG config now uses per-node ConfigMaps (replaces single static ConfigMap). MIG Manager v0.14.0+ auto-generates them.
- **Upgrade ordering:** driver pods reuse kernel modules across container restarts instead of recompiling — restart recovery drops from minutes to seconds. No NFD ordering change.
  - **Preview with a rendered-manifest text diff, NOT `kubectl diff`.** Adding ClusterPolicy fields (e.g. `cdi.nriPluginEnabled`) makes `kubectl diff` warn `unknown field …` and silently strip them — the *live* CRD is still the old schema during the server dry-run. The chart updates the CRD first (`upgradeCRD: true` hook) so the real upgrade applies cleanly; `helm upgrade` needs `--disable-openapi-validation` for the same reason.
- **Deprecations:**
  - NVIDIA Kata Manager deprecated → use `kata-deploy`.
  - `useOpenKernelModules` deprecated → `kernelModuleType` (`auto`/`open`/`proprietary`); `auto` requires driver ≥ 570.86.15 or 570.124.06+.
- **Notable:**
  - NRI Plugin added (alternative to runtime-class injection) — see **Breaking** for the `runtimeClassName: nvidia` consequence.
  - **`ccManager` default flipped `enabled: false→true` / `defaultMode: off→on`** in chart defaults. Inert unless a node carries `nvidia.com/cc.capable=true` (Hopper in a TDX/SEV-SNP confidential VM), but a sparse values overlay silently inherits the flip — diff prev-vs-new *chart defaults* (not just your values delta) to catch flips like this.
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
