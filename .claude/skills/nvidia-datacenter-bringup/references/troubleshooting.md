# Troubleshooting playbook

Symptom → most likely cause → fix. Ordered by observed frequency on B300 + Ubuntu 24.04 bring-ups.

## `nvidia-smi` reports "No devices were found" on a B300

**Most likely causes, ordered by likelihood:**

1. **Baseboard firmware below v1.4.30** — CX-8 MCTP enumeration bug. The host can't see the GPUs at the PCIe layer because the chassis firmware doesn't enumerate them properly. Symptoms: `lspci -nn | grep -i nvidia` shows fewer GPUs than expected, or none. Cure: update Dell firmware to v1.4.30+ and AC-cycle properly. See [[dell-firmware]].
2. **Proprietary kernel modules on Blackwell** — `nvidia-driver-580` (no `-open`) installs but the module doesn't bind to B300 silicon. Check with `lsmod | grep nvidia` (modules loaded but no GPUs) plus `dpkg -l | grep nvidia-driver` (proprietary packages visible). Cure: `apt install --autoremove --purge nvidia-open nvidia-driver-open`.
3. **MOK not enrolled on Secure Boot host** — modules built but kernel refuses to load them. Check `dmesg | grep -iE 'PKCS#7|signature'` (signature-rejection messages appear). Cure: enroll MOK per [[secure-boot]].
4. **DKMS build failed** — modules don't exist on disk. Check `sudo dkms status` (expect `installed` for nvidia/580.x). Cure: `sudo dkms autoinstall`; check `make.log` under `/var/lib/dkms/nvidia/`.

**Triage**:
```bash
lspci -nn | grep -iE 'nvidia|3d controller|mellanox'   # GPUs visible at PCIe?
sudo mokutil --sb-state                                # SB enabled?
sudo dpkg -l | grep -E 'nvidia-driver|nvidia-open|cuda-drivers'  # which variant installed?
sudo dkms status                                       # DKMS modules built?
lsmod | grep ^nvidia                                   # modules loaded into kernel?
sudo dmesg | grep -iE 'nvidia|nvrm|signature' | tail -50
```

## R580 driver fails to init on a Hopper (H100/H200) host

If `nvidia-smi` errors with "driver/library version mismatch" or "driver failed to initialize" specifically after upgrading to a R580 patch level, the **VBIOS may be too old**. Per NVIDIA's R580 release notes:

> *"This version of the GPU driver will fail to initialize on systems with Hopper GPUs subrevision = 3 and VBIOS versions older than 96.00.68.00.xx."*

Check the GPU VBIOS:

```bash
nvidia-smi -q -i 0 | grep -i 'VBIOS\|Subdevice ID'
```

If the VBIOS string is below `96.00.68.00.xx` and you have Hopper subrev 3 silicon, update the chassis baseboard firmware via iDRAC ([[dell-firmware]]) — VBIOS ships as part of the baseboard firmware bundle. After flash + AC-cycle, re-test.

This is Hopper-only — Blackwell B300 and H100/H200 subrev <3 aren't affected.

## `nvidia-fabricmanager.service` fails to start

```bash
sudo systemctl status nvidia-fabricmanager
sudo journalctl --no-pager -u nvidia-fabricmanager -b | tail -50
```

**Most likely causes:**

1. **`ib_umad` kernel module not loaded** — DOCA was installed AFTER the driver (the famous install-order pitfall). NVIDIA forum 353369. Check with `lsmod | grep ib_umad`. Cure:
   ```bash
   echo ib_umad | sudo tee /etc/modules-load.d/ib_umad.conf
   sudo modprobe ib_umad
   sudo systemctl restart nvidia-fabricmanager
   ```
   Long-term, reinstall DOCA so its postinst regenerates the modules-load configuration: `sudo apt install --reinstall doca-ofed`.

2. **FM version doesn't match driver version** — FM aborts with "kernel driver stack version not compatible". Check:
   ```bash
   cat /proc/driver/nvidia/version | head -1     # driver version
   nv-fabricmanager --version                    # FM version
   ```
   They must match major.minor.patch. Cure: use `nvlink5-<branch>` meta which keeps them coherent, or install matching versions explicitly.

3. **NVLSM not running on B200/B300** — FM journal shows "Failed to connect to NVLSM" or "subnet manager unavailable". Check:
   ```bash
   systemctl status nvidia-nvlsm
   ls -la /var/run/nvidia-fabricmanager/fm_sm_ipc.socket
   ```
   On B200/B300, NVLSM is mandatory (4th-gen NVSwitch). Cure: `apt install nvlsm` (or reinstall `nvlink5-<branch>` to pull it).

4. **CX bridge device not identified** — FM can't find the SMDL=SW_MNG VPD signature. Usually means OFED isn't fully loaded or PCIe enumeration failed.
   ```bash
   # Find CX bridge devices
   for bdf in $(lspci -nn | grep -i mellanox | awk '{print $1}'); do
     echo "=== $bdf ==="
     sudo lspci -vvs $bdf 2>/dev/null | grep -A 1 SMDL
   done
   ```
   At least one should show `SW_MNG`. If none do, baseboard firmware may be old (back to [[dell-firmware]]) or DOCA stack isn't loaded.

## `cudaErrorSystemNotReady` / "failed to allocate device vector A"

Textbook FM-not-running signature on any NVSwitch system. **This is almost never a driver bug.**

Triage:
```bash
# Is FM running?
systemctl is-active nvidia-fabricmanager
# Is fabric registered?
nvidia-smi -q -i 0 | grep -A 2 Fabric
# Expected: State: Completed, Status: Success
```

If `is-active` returns `inactive` or `failed`, go to the "fabricmanager.service fails to start" section above.

If `nvidia-smi` shows `State: In Progress`, FM is still registering — wait 30-90 seconds and check again.

If `State: NotInitialized`, FM started but didn't successfully register. Check `journalctl -u nvidia-fabricmanager` for errors; usually pointing back at `ib_umad`, NVLSM, or CX bridge.

References: gpu-operator issues #286, #1043, #1146, #545.

## gpu-operator `cuda-validator` pod in CrashLoopBackOff

```bash
kubectl logs -n gpu-operator nvidia-cuda-validator-XXX -c cuda-validation
```

On `failed to allocate device vector A, error code system not yet initialized` → FM not running on the host. See section above.

On `unable to get device name: failed to find device with id '3182'` → known cosmetic bug gpu-operator #2231. Symptom is benign — `/dev/nvidia*` symlinks are still created. Real workloads work; only the validator's name-table check is unhappy. See [[gpu-operator]].

If the pod CrashLoopBackoffs for less than 3 minutes on first boot → normal; FM is still initializing. Wait.

If the pod fails with a CUDA mismatch error → driver branch on host doesn't match what the operator image expects. Check `nvidia-smi --query-gpu=driver_version --format=csv` vs gpu-operator's platform-support matrix.

## `ib_umad` not loaded at boot

You followed the install order but `ib_umad` still isn't loading at boot.

```bash
# Confirm DOCA's modules-load file exists
ls -la /etc/modules-load.d/
sudo cat /etc/modules-load.d/*doca* 2>/dev/null
sudo cat /etc/modules-load.d/*mlnx* 2>/dev/null
```

If no DOCA-provided modules-load config exists, write one yourself:
```bash
echo ib_umad | sudo tee /etc/modules-load.d/ib_umad.conf
```

Then `sudo modprobe ib_umad` to load it now, and confirm next reboot autoloads:
```bash
sudo reboot
# After reboot
lsmod | grep ib_umad
```

## DKMS build fails after a kernel upgrade

```bash
sudo dkms status
# Look for nvidia/580.xxx, status should be "installed"
# If "added" but not "installed", the build failed
```

Check the build log:
```bash
ls /var/lib/dkms/nvidia/*/build/make.log
sudo less /var/lib/dkms/nvidia/580.xxx/build/make.log
```

Common fixes:
- Missing kernel headers: `sudo apt install linux-headers-$(uname -r)`
- gcc mismatch: install the gcc version the kernel was built with (`/proc/version` shows it)
- Force rebuild: `sudo dkms autoinstall`

After successful rebuild, modules are auto-signed with the DKMS MOK. Verify `modinfo nvidia | grep ^sig`.

## NVLink links down or partial

```bash
nvidia-smi nvlink --status
# Expect all 18 (B300) links per GPU, all "Up"
nvidia-smi nvlink --status -i 0     # just GPU 0
```

If some links are down:
- Check `nvidia-smi -q -i 0 | grep -A 5 NVLink` — error counts indicate bad cables / link errors
- Check `dmesg | grep -i nvswitch` — SXid errors point at NVSwitch issues
- Reset GPUs: `sudo nvidia-smi -r` (requires FM to be running; will pause running workloads briefly)
- If reset doesn't recover: AC-cycle the chassis (back to [[dell-firmware]] procedure)

## Mixed Ubuntu archive + NVIDIA CUDA repo packages

You suspect both repos are providing different versions of the same packages, causing apt to refuse to upgrade or pulling in inconsistent versions.

```bash
# What's installed and where did it come from?
for pkg in $(dpkg -l | awk '/nvidia|cuda|nvlsm|libnv|fabricmanager|nvlink|ib_umad/{print $2}'); do
  origin=$(apt-cache policy "$pkg" 2>/dev/null | awk '/^[ ]*[0-9]+/{print $3; exit}')
  echo "$pkg <- $origin"
done | sort -k2

# Common values:
#   http://archive.ubuntu.com/...     ← Ubuntu archive
#   https://developer.download.nvidia.com/...  ← NVIDIA CUDA repo
#   https://linux.mellanox.com/...     ← DOCA repo
```

For B300, single-source on NVIDIA CUDA repo is strictly better. To rip out Ubuntu archive NVIDIA packages and re-install from CUDA repo:

```bash
sudo apt purge '~i^nvidia-' '~i^cuda-' '~i^libnvidia-'
sudo apt autoremove --purge
sudo apt update
# Now install fresh per [[recipe]]
```

Be careful: `apt purge ~i^nvidia-` is a regex purge of all installed packages matching `^nvidia-`. Inspect first with `apt-get -s purge '~i^nvidia-'`.

## Test FM with no workload

```bash
# Trigger FM init manually and watch
sudo systemctl restart nvidia-fabricmanager
sleep 30
nvidia-smi -q -i 0 | grep -A 2 Fabric
```

On a healthy B300 this should produce `State: Completed, Status: Success` within 30-90s.

Verbose FM logs (raise log level temporarily):
```bash
sudo sed -i 's/^LOG_LEVEL=.*/LOG_LEVEL=5/' /usr/share/nvidia/nvswitch/fabricmanager.cfg
sudo systemctl restart nvidia-fabricmanager
sudo journalctl -u nvidia-fabricmanager -f
# Restore
sudo sed -i 's/^LOG_LEVEL=.*/LOG_LEVEL=4/' /usr/share/nvidia/nvswitch/fabricmanager.cfg
sudo systemctl restart nvidia-fabricmanager
```

## Quick "is this host healthy?" one-liner

```bash
echo "=== sb-state: $(sudo mokutil --sb-state 2>&1) ==="
echo "=== gpus: $(nvidia-smi --query-gpu=count --format=csv,noheader -i 0 2>&1) ==="
echo "=== fm: $(systemctl is-active nvidia-fabricmanager) ==="
echo "=== nvlsm: $(systemctl is-active nvidia-nvlsm) ==="
echo "=== persistenced: $(systemctl is-active nvidia-persistenced) ==="
echo "=== ib_umad: $(lsmod | awk '/^ib_umad/{print "loaded"; found=1} END{if (!found) print "MISSING"}') ==="
echo "=== fabric: $(nvidia-smi -q -i 0 2>/dev/null | awk '/Fabric/{f=1; next} f && /State/{print $3; exit}') ==="
echo "=== nvidia-smi gpus: $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l) ==="
```

Healthy output looks like:
```
=== sb-state: SecureBoot enabled ===
=== gpus: 8 ===
=== fm: active ===
=== nvlsm: active ===
=== persistenced: active ===
=== ib_umad: loaded ===
=== fabric: Completed ===
=== nvidia-smi gpus: 8 ===
```
