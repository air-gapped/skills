---
name: nvidia-datacenter-bringup
description: Bring up NVIDIA HGX/DGX datacenter GPU hosts on Ubuntu 24.04 LTS — air-gapped or connected, Secure Boot enabled. Covers B300/B200/H100/A100/L40S/L4 driver+fabricmanager+NVLSM+DOCA-OFED install order and exact package set from NVIDIA CUDA repo + DOCA repo. Triggers on B300/B200/HGX/DGX install, "fabricmanager won't start", "system not yet initialized" / cudaErrorSystemNotReady, NVLSM missing, ib_umad not loading, DOCA-OFED before NVIDIA driver, nvidia-driver-pinning-XXX, nvlink5-XXX, nvidia-open vs cuda-drivers, "Blackwell requires open kernel modules", ConnectX-7/8 bridge device, FM exact-version-match, gpu-operator cuda-validator CrashLoopBackOff, B300 PCI ID 0x3182, air-gap CUDA + DOCA mirror, three-tier DOCA GPG key, MOK enrollment, DKMS sign, Dell PowerEdge XE9780/XE9785 baseboard firmware v1.4.30, iDRAC Redfish virtual AC cycle DellOemChassis.ExtendedReset, generic "install nvidia driver ubuntu 24.04 datacenter".
when_to_use: Use for bringing up an NVIDIA datacenter GPU host (HGX, DGX, or inference-card servers) on Ubuntu 24.04 LTS. Covers the full air-gapped path from clean OS install to the gpu-operator cuda-validator pod passing. Trigger when fabricmanager fails to start, nvidia-smi sees no GPUs on B200/B300, the cuda-validator loops with "system not yet initialized", a host needs coherent DOCA-OFED + NVLSM + NVIDIA driver install, MOK enrollment for Secure Boot is needed, or a Dell XE9780/XE9785 chassis needs baseboard firmware updated.
---

# nvidia-datacenter-bringup

Opinionated greenfield recipe for **NVIDIA datacenter GPUs on Ubuntu 24.04 LTS** — get from a clean OS install to a healthy host where `nvidia-smi` reports all GPUs, `nvidia-fabricmanager` is `active (running)`, and the gpu-operator `cuda-validator` pod passes. Air-gap is the primary case; connected sites use the same packages from the same upstream URLs.

## Decision tree

| Question | Answer | Read |
|---|---|---|
| Has Blackwell silicon (B300/B200/B100)? | Yes | Open kernel modules **mandatory** — proprietary is unsupported [[open-modules-transition]] |
| HGX H100/H200/H800 (3rd-gen NVSwitch)? | Yes | Open recommended (not mandatory). Use `cuda-drivers-fabricmanager-<branch>` meta; **skip** `nvlink5-<branch>` and NVLSM (NVLSM is B200/B300-only). DOCA-OFED also skipped — no CX bridge on H100. Min driver 525.xx |
| HGX/DGX A100 (2nd-gen NVSwitch)? | Yes | Same as H100 path. Min driver 450.xx. ALI not available — FM trains NVLinks at boot |
| L40S, L40, or L4 (no NVSwitch)? | Yes | Driver + container-toolkit only. **Skip** DOCA-OFED, fabricmanager, NVLSM entirely. Validation reduces to `nvidia-smi` clean — no fabric registration to check |
| 4th-gen NVSwitch (B200/B300/B100)? | Yes | Must install `nvlink5-<branch>` meta (or `nvlsm + libnvsdm + libibumad3 + infiniband-diags` separately). FM talks to switches via CX7 bridge — DOCA-OFED is non-optional [[fabric-manager-guide]] §"Additional Steps for B200/B300" |
| Dell XE9780 or XE9785 chassis? | Yes | **Step 0 is firmware ≥ v1.4.30**. Use Redfish `DellOemChassis.ExtendedReset`, NOT BIOS Full Power Cycle [[dell-firmware]] |
| Secure Boot enabled? | Yes | Enroll one DKMS MOK — signs both NVIDIA and DOCA-OFED modules [[secure-boot]] |
| Air-gapped? | Yes | Mirror three repos. Total budget ~3 GB. Three-tier GPG keys for DOCA [[airgap-mirror]] |
| gpu-operator on top? | Yes | Pre-installed driver mode: `driver.enabled=false`, `toolkit.enabled=false`. Know about B300 issue #2231 [[gpu-operator]] |

## The 10-step install order

Order matters: DOCA before driver, MOK before any DKMS build, firmware before everything.

```
0. Dell baseboard firmware ≥ v1.4.30 + Redfish virtual AC cycle      [[dell-firmware]]
1. OS prep: kernel headers, blacklist nouveau                         [[recipe]]
2. Secure Boot: generate + import MOK (once, signs both stacks)       [[secure-boot]]
3. Add repos: NVIDIA CUDA + DOCA (+ Ubuntu archive subset)            [[airgap-mirror]]
4. Install DOCA — modules-load.d generated, ib_umad autoloads         [[recipe]]
5. Pin NVIDIA driver branch: apt install nvidia-driver-pinning-580    [[packages]]
6. Install driver: apt install nvidia-open-580 (open is mandatory)    [[packages]]
7. Install fabric stack: apt install nvlink5-580                      [[packages]]
8. Install nvidia-container-toolkit (lives in same CUDA repo)         [[packages]]
9. Validate: nvidia-smi clean, FM active, ib_umad loaded, Fabric Completed/Success
```

`nvlink5-580` is the **compute-only** fabric meta — pulls `nvidia-fabricmanager + nvlsm + libnvsdm + libnvidia-nscq + nvidia-imex + collectx-bringup + mft{,-oem,-autocomplete} + nvidia-dkms-580-open + libnvidia-compute-580` (and transitively `libibumad3` + `infiniband-diags`). It does NOT pull `nvidia-utils-580` / `nvidia-smi` — that's why step 6 installs `nvidia-open-580` (full userland) AS WELL. Dependency tree verified live from the NVIDIA CUDA repo for Ubuntu 24.04 amd64 — see [[packages]].

## Pitfalls catalogue

The mistakes that cost hours, ordered by frequency in the wild:

1. **Proprietary modules on Blackwell.** `nvidia-driver-580-server` (no `-open`) installs cleanly but the kernel module silently doesn't bind to B300 silicon. `nvidia-smi` reports no GPUs. NVIDIA's open-modules transition blog: proprietary is **unsupported** on Blackwell and Grace Hopper. Cure: use `nvidia-open-<branch>` from the CUDA repo. See [[open-modules-transition]].

2. **DOCA installed AFTER the driver.** `ib_umad` does not autoload at boot; `nvidia-fabricmanager.service` fails. NVIDIA forum 353369. Cure: install DOCA first. If already broken, reinstall DOCA OR `echo ib_umad | sudo tee /etc/modules-load.d/ib_umad.conf && sudo modprobe ib_umad && sudo systemctl restart nvidia-fabricmanager`. See [[troubleshooting]].

3. **Dell BIOS Full Power Cycle.** The iDRAC web-UI "Full Power Cycle" and the standard Redfish `Chassis.Reset` `FullPowerCycle` do **not** reliably activate the GPU baseboard subcomponents (HMC, NVSwitch, CX bridge firmware). Symptom: firmware update "succeeded" but old version still reports. Cure: Dell-specific `DellOemChassis.ExtendedReset`. See [[dell-firmware]].

4. **Mixing Ubuntu archive `nvidia-driver-XXX-server` with CUDA-repo `nvlsm`.** Ubuntu archive's FM version lags NVIDIA's by patches; NVLSM is only in CUDA repo. Rip out Ubuntu archive NVIDIA packages and go single-source CUDA repo. See [[packages]].

5. **MOK enrolled for NVIDIA but not for DOCA-OFED (or vice versa).** Both stacks are DKMS-built. One `/var/lib/dkms/mok.pub` signs both — enroll once, covers everything. There is no Canonical-signed precompiled HWE module for ConnectX, so MOK is unavoidable on B300 + Secure Boot. See [[secure-boot]].

6. **`cudaErrorSystemNotReady` blamed on driver.** This is the textbook FM-not-running signature on any NVSwitch system. The fix is always: confirm `nvidia-fabricmanager.service` is `active (running)` and its version matches the loaded driver. See [[troubleshooting]] and [[gpu-operator]].

7. **gpu-operator B300 PCI ID warning loop (#2231).** Cosmetic, not fatal. `nvidia-operator-validator` logs `unable to get device name: failed to find device with id '3182'`. Open in upstream since 2026-03-18; NVIDIA acknowledged "B300 should be supported" but waiting on must-gather. Symptom is benign — pods still work. See [[gpu-operator]].

8. **Driver 570.158.01 + operator-managed driver mode.** FM start script broken (gpu-operator #1595). Cure: pin ≥570.172.08 OR move to 580+. Or just use pre-installed-driver mode and let the host's systemd unit own FM. See [[gpu-operator]].

## Validation

After step 9 these should all be true. Expected output on a healthy 8-GPU B300:

```bash
$ nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
NVIDIA B300 SXM6 270GB, 580.126.20
NVIDIA B300 SXM6 270GB, 580.126.20
# ... 8 identical lines

$ systemctl is-active nvidia-persistenced nvidia-fabricmanager nvidia-nvlsm
active
active
active

$ lsmod | grep -E '^nvidia|^nvidia_uvm|^nvidia_peermem|^ib_umad' | awk '{print $1}'
nvidia_peermem
nvidia_uvm
nvidia
ib_umad

$ nvidia-smi -q -i 0 | grep -A 2 Fabric
        Fabric
            State                  : Completed
            Status                 : Success

$ nvidia-smi nvlink --status -i 0 | head -3
GPU 0: NVIDIA B300 SXM6 270GB (UUID: ...)
         Link 0: 200 GB/s
         Link 1: 200 GB/s
```

If any value is missing or wrong (e.g. `State: Not Initialized`, `lsmod` missing `ib_umad`, `systemctl is-active` reports `inactive`), see [[troubleshooting]] keyed by the symptom.

On a fresh 8-GPU B300, FM takes ~30–90 s to finish fabric registration on first boot. The gpu-operator validator pod may CrashLoopBackoff transiently during this window — only sustained crashes >3 min are real failures.

## Hard out-of-scope

- Windows, workstation/Optimus, non-Ubuntu (RHEL/SLES handled by NVIDIA's own guides)
- vGPU / MIG runtime config (separate concern from bring-up)
- DGX OS (NVIDIA's preinstalled bundle — different workflow, see DGX OS docs)
- gpu-operator helm-values for full cluster config (host-side stops at validator passing)
- Multi-node NVLink Switch (NVL72-style); single-chassis NVL8 only
- Data-plane CX-8 NIC config (bridge role only — those are the management PFs)
- Vendor firmware for non-Dell chassis (Supermicro/HPE/Lenovo — defer to vendor docs)

## References

| Topic | File |
|---|---|
| Full install recipe with commands | [[recipe]] |
| Exact apt package matrix (verified live) | [[packages]] |
| Air-gap mirror setup + GPG keys + sizing | [[airgap-mirror]] |
| Secure Boot + MOK + DKMS pipeline | [[secure-boot]] |
| Dell baseboard firmware + Redfish AC cycle | [[dell-firmware]] |
| gpu-operator host-contract + cuda-validator triage | [[gpu-operator]] |
| Symptom → cause → fix playbook | [[troubleshooting]] |
| Dated URL index | [[sources]] |
| Open follow-ups / ceiling findings | [[improvement-backlog]] |
| NVIDIA Fabric Manager User Guide (offline copy) | [[fabric-manager-guide]] |
| NVIDIA Driver Install Guide — Ubuntu chapter | [[driver-install-ubuntu]] |
| NVIDIA Driver Install Guide — Kernel modules | [[driver-install-kernel-modules]] |
| NVIDIA Driver Install Guide — Advanced Options | [[driver-install-advanced-options]] |
| DOCA Host Installation Guide — Ubuntu 24.04 | [[doca-install-ubuntu]] |
| NVIDIA blog: open kernel modules transition | [[open-modules-transition]] |
| Dell HGX B300 SXM6 firmware release notes (v1.4.30) | [[b300-firmware-release-notes]] |
| One-shot host health check (`bash`) | `scripts/health-check.sh` |
