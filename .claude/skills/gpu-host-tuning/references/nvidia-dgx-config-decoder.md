# NVIDIA DGX configuration package decoder

What NVIDIA actually flips on a DGX, package by package, and how to apply
the same settings on non-DGX hosts (Dell XE9680/XE9780, Supermicro,
Lenovo, HPE, cloud VMs) where `apt install nvidia-tuned-profiles` does
nothing.

The DGX EL10 / DGX OS 7 user guides reference `nvidia-tuned-profiles` as
the one-line shortcut. That package's actual `dgx-<platform>-performance/
tuned.conf` files are **not** distributed in the public BaseOS repos.
What IS public are ~30 small focused packages that each install a single
config file (kernel cmdline fragment, sysctl drop-in, modprobe option,
systemd unit) — and a JSON file with the per-platform flag matrix
(`nvidia-platform-configs.json`). Together they reconstruct what
`nvidia-tuned-profiles` would have done.

This file is exhaustive on purpose: every grub fragment, every sysctl
key, every systemd unit override, every helper script's actual flag.

## Table of contents

- [Public repo URLs](#public-repo-urls)
- [Per-platform configuration matrix](#per-platform-configuration-matrix)
- [Per-platform divergences worth flagging](#per-platform-divergences-worth-flagging)
- [GRUB cmdline drop-ins](#grub-cmdline-drop-ins)
- [sysctl drop-ins](#sysctl-drop-ins)
- [Modprobe options](#modprobe-options)
- [Modules autoloaded at boot](#modules-autoloaded-at-boot)
- [Limits](#limits)
- [Systemd unit overrides](#systemd-unit-overrides)
- [Standalone systemd units](#standalone-systemd-units)
- [udev — character device symlinks](#udev--character-device-symlinks)
- [Helper scripts (runtime logic)](#helper-scripts-runtime-logic)
- [Platform detection regex strings](#platform-detection-regex-strings)
- [What's NOT in the public repo (gated)](#whats-not-in-the-public-repo-gated)
- [Extraction recipe for non-DGX users](#extraction-recipe-for-non-dgx-users)

---

## Public repo URLs

All probed live on 2026-05-05. The host blocks directory listings (404)
but specific metadata files (Release / repomd.xml / Packages.gz /
primary.xml.zst) and individual `.deb` / `.rpm` files return 200.

| Repo | URL | Component | Notable contents |
|------|-----|-----------|------------------|
| Ubuntu jammy (22.04) | `https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/` | `common`, `dgx`, `dcs`, `egx`, `preview`, `c2` | 106 settings packages in `common`; 35 metapackages in `dgx` (a100/a800/dgx1/dgx2/station only — no h100+) |
| Ubuntu noble (24.04) | `https://repo.download.nvidia.com/baseos/ubuntu/noble/x86_64/` | `dgx` | 8 metapackages, no detail-level packages yet (May 2026) |
| EL10 (RHEL 10) | `https://repo.download.nvidia.com/baseos/el/10/x86_64/dgx/` | (single channel) | 19 RPMs including `nv-common-apis-25.10-1.el.noarch.rpm` (carries `nvidia-platform-configs.json` and `plat_funcs.bash`) |

Index files used:

```bash
# Ubuntu metadata
curl -s https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/Release
curl -s https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/common/binary-amd64/Packages.gz | gunzip
curl -s https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/dgx/binary-amd64/Packages.gz | gunzip

# EL10 metadata
curl -s https://repo.download.nvidia.com/baseos/el/10/x86_64/dgx/repodata/repomd.xml
# then fetch the primary.xml.zst hash referenced inside
```

---

## Per-platform configuration matrix

Source: `nv-common-apis-25.10-1.el.noarch.rpm` ships
`/etc/nvidia-platform.d/nvidia-platform-configs.json` with 22 platform
entries. Detection grepstr is matched against `dmidecode --string
system-product-name` (or `system-family` when
`UsesDmiSystemFamilyForDetection=True`).

| Platform | DMI grepstr | Serial TTY | `pci=realloc` | `iommu=pt` | `init_on_alloc=0` | NVMe RO | GPU RO | ACS disable | Crashdump |
|---|---|---|---|---|---|---|---|---|---|
| `dgx_a100` | `920-23687-`, `675-23287-`, `920-23287-` | ttyS1 | — | yes | yes | yes | **yes** | yes | `1G-:2048M` |
| `dgx_a800` | `920-23687-2535-` | ttyS1 | — | yes | yes | yes | **yes** | yes | `1G-:2048M` |
| `dgx_h100` | `DGXH100`, `DGX H100` | ttyS0 | **off** | yes | yes | yes | no | yes | `1G-:2048M` |
| `dgx_h200` | `DGXH200`, `DGX H200` | ttyS0 | **off** | yes | yes | yes | no | yes | `1G-:2048M` |
| `dgx_h800` | `DGXH800`, `DGX H800` | ttyS0 | **off** | yes | yes | yes | no | yes | `1G-:2048M` |
| `dgx_b200` | `DGXB200`, `DGX B200` | ttyS0 | **off** | yes | yes | yes | no | yes | `2048M,high` |
| `dgx_b300` | `DGXB300`, `DGX B300` | ttyS0 | **off** | yes | yes | yes | no | yes | `2048M,high` |
| `dgx_gb200` | `DGXGB200`, `DGX GB200`, `GB200 NVL` | ttyS0 | **on** | **no** | yes | yes | no | yes | `2048M,high` |
| `dgx_gb300` | `DGXGB300`, `DGX GB300`, `GB300.*NVL` | ttyS0 | **on** | **no** | yes | yes | no | yes | `2048M,high` |
| `dgx_spark` | `DGX Spark` | ttyS1 | — | no | yes | no | no | yes | `1G-:1024M` |
| `dgx_gb300ws` | `GALAXY-GB300` | ttyS1 | — | no | yes | no | no | yes | `1G-:1024M` |
| `dgxstation_a100` | `920-23487-`, `675-23487-`, `DGX Station A100` | ttyS1 | — | yes | yes | yes | yes | yes | `1G-:2048M` |
| `dgxstation_a800` | `920-23487-2535`, `675-23487-0200` | ttyS1 | — | yes | yes | yes | yes | yes | `1G-:2048M` |
| `dgxstation` | `DGX Station`, `DiGiTS Dev Box2` | ttyS1 | — | no | yes | no | no | yes | `1G-:2048M` |
| `l4t_ut2_1` | `UT2.1 DP Chassis` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `l4t_c2` | `Grace CPU P.*` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `l4t_cg1` | `GH200 P.*` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `l4t_cg4` | `Grace Hopper x4 P.*` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `l4t_keystone` | `P4261` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `l4t_oberon` | `P4486` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `l4t_smcmgx` | `ARS-`, `MBD-G1SMH`, `Super Server` | ttyS1 | — | no | yes | no | no | yes | `2048M,high` |
| `kvm` | `QEMU` | ttyS1 | — | no | no | no | no | yes | `1G-:2048M` |

---

## Per-platform divergences worth flagging

The skill's `recommended-tunings.md` §B.1 currently gives universal
advice. Four cases where that's wrong:

1. **GPU Relaxed Ordering** is enabled (`NVreg_EnablePCIERelaxedOrderingMode=1`)
   only on **A100/A800 and DGX Stations**. Explicitly disabled on
   H100/H200/H800/B200/B300/GB200/GB300. Do NOT blanket-recommend it on
   Hopper+ or Blackwell — NVIDIA's own platform table opts out.

2. **`pci=realloc`** flips per-platform: `off` on H100–B300, but **`on`** on
   Grace-Blackwell GB200/GB300. Reason: NVLink-C2C and the larger BAR
   layout on Grace need PCIe BAR reallocation. The skill's universal
   `pci=realloc=off` recommendation is wrong for GB200/GB300.

3. **`iommu=pt`** is **disabled** on Grace-Blackwell (GB200/GB300),
   `dgx_spark`, `dgxstation`, all L4T platforms, and KVM guests. The
   skill's universal `iommu=pt` recommendation is wrong for those —
   Grace SoC handles addressing differently and IOMMU passthrough mode
   conflicts with its memory model.

4. **Crashdump reservation** changes from `crashkernel=1G-:2048M` (legacy
   syntax: 2048 MB reserved when RAM ≥ 1 GB) on Hopper to
   `crashkernel=2048M,high` (use high memory area, requires
   `crashkernel=,low` companion) on Blackwell+. Relevant for
   `crashkernel=` cmdline and host-side OOM accounting.

---

## GRUB cmdline drop-ins

Each package installs ONE file in `/etc/default/grub.d/` that appends to
`GRUB_CMDLINE_LINUX`. Drop-ins are concatenated by Ubuntu's
`update-grub` and Debian's `grub-mkconfig`.

| Package | File | Content |
|---------|------|---------|
| `nv-iommu-pt` | `iommu.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX iommu=pt"` |
| `nv-mitigations-off` | `mitigations-off.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX mitigations=off"` |
| `nv-hugepage` | `hugepage.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX transparent_hugepage=madvise"` |
| `nv-ast-modeset` | `ast-modeset.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX ast.modeset=0"` and `GRUB_GFXPAYLOAD_LINUX=auto` |
| `nvidia-pci-no-realloc` | `no-pci-realloc.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX pci=realloc=off"` |
| `nvidia-deadline-scheduler` | `deadline-scheduler.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX elevator=deadline"` |
| `nv-disk-encrypt` | `allow_tpm.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX libata.allow_tpm=1"` |
| `nv-pci-dbg` | `pci-dbg.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX dyndbg=\"file pciehp* +p\""` |
| `nvidia-acs-disable` (RHEL ≥10.99) | `acs-disable.cfg` (written by script) | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX pci=disable_acs_redir=pci:0:0"` |
| `nv-enable-nvme-hot-plug` (runtime, plat-conditional) | `enable-nvme-hot-plug.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX pci=realloc=on pcie_ports=native"` |
| `nvidia-ipmisol` (runtime) | `ipmisol.cfg` | `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX console=tty0 console=ttyS0,115200n8"` plus `GRUB_TERMINAL="$GRUB_TERMINAL console serial"` and `GRUB_SERIAL_COMMAND="$GRUB_SERIAL_COMMAND serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1"` |

After dropping these in, run `update-grub` (Debian/Ubuntu) or
`grub2-mkconfig -o $(readlink /etc/grub2-efi.cfg)` (RHEL/SUSE) and
reboot.

---

## sysctl drop-ins

`nvidia-kernel-defaults` → **`/etc/sysctl.d/20-nvidia-defaults.conf`**:

```
net.ipv4.conf.all.arp_announce = 2
net.ipv4.conf.default.arp_announce = 2
net.ipv4.conf.all.arp_ignore = 1
net.ipv4.conf.default.arp_ignore = 1
```

Why: prevents ARP cross-interface answers on multi-NIC GPUDirect hosts,
where each rank has a near-NIC and answering an ARP for an unrelated NIC
causes traffic to land on the wrong path. Same setting is in NVIDIA's
`nvidia-base` TuneD profile.

---

## Modprobe options

| File | Setting | Purpose |
|------|---------|---------|
| `/etc/modprobe.d/nvidia-drm.conf` | `options nvidia-drm modeset=1` | Required for KMS / Wayland on DGX Stations |
| `/etc/modprobe.d/nvidia-relaxed-ordering.conf` | `options nvidia NVreg_EnablePCIERelaxedOrderingMode=1` | GPU-side PCIe Relaxed Ordering (A100/A800 only — see platform matrix) |

---

## Modules autoloaded at boot

| File | Module | Purpose |
|------|--------|---------|
| `/etc/modules-load.d/nvidia-fs-loader.conf` | `nvidia-fs` | GPUDirect Storage |
| `/etc/modules-load.d/nvidia-peermem.conf` | `nvidia-peermem` | GPUDirect RDMA — required for Mellanox + NVIDIA P2P |

---

## Limits

`nv-limits` → **`/etc/security/limits.d/99-nv-limits.conf`**:

```
* hard nofile 500000
* soft nofile 500000
```

NVIDIA's stock limits package only sets `nofile=500000`. **No
`memlock=unlimited`** is shipped by NVIDIA. The skill's separate
recommendation in §D.1 to add `memlock unlimited` is operator-tier
guidance; NVIDIA's stock package leaves memlock at the kernel default.

---

## Systemd unit overrides

`/etc/systemd/system/<unit>.d/*.conf` drop-ins that modify package units:

### `nvidia-persistenced.service` (`nv-persistence-mode`)
```ini
[Service]
ExecStartPre=/usr/bin/nvidia-smi
ExecStart=
ExecStart=/usr/bin/nvidia-persistenced --user nvidia-persistenced --persistence-mode --verbose

[Install]
WantedBy=
WantedBy=basic.target
```
The `ExecStartPre=/usr/bin/nvidia-smi` warms the driver before
persistenced takes over (avoids first-call latency).

### `docker.service` (`nv-docker-options`)
```ini
[Unit]
After=nvidia-fabricmanager.service

[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -s overlay2 --default-shm-size=1G --bip=172.17.0.1/16 --fixed-cidr=172.17.0.0/16
LimitMEMLOCK=infinity
LimitSTACK=67108864
```
**`LimitMEMLOCK=infinity`** is the docker-side memlock that LMCache and
pinned-buffer paths need. The skill's §D.2 mentions this; this is the
canonical NVIDIA override.

### `cachefilesd.service` (`nvidia-conf-cachefilesd`)
```ini
[Unit]
After=raid.mount

[Service]
Restart=on-failure
StartLimitBurst=5
ExecStartPre=/bin/mountpoint /raid
```
Starts cachefilesd only after `/raid` is mounted (DGX A100/H100 RAID
config); restart-on-failure with 5-burst limit.

---

## Standalone systemd units

### `nv-cpu-governor.service`
```ini
[Unit]
Description=Set the CPU Frequency Scaling governor
ConditionVirtualization=no
ConditionPathExists=/sys/devices/system/cpu/online
ConditionPathExists=!/etc/init/lxc-android-config.conf

[Service]
Type=idle
ExecStart=/usr/bin/cpupower frequency-set -g performance
```
The `ConditionVirtualization=no` is why this unit is no-op inside QEMU
guests — confirms the skill's virt-and-cloud-quirks claim.

### `nvidia-acs-disable.service` and `disable_acs_redir.service`
Two-method ACS disable. On RHEL ≥ 10.99 (kernel supports
`pci=disable_acs_redir`), the cmdline method is used:
```ini
[Unit]
Description=Configure grub pci=disable_acs_redir=pci:0:0
ConditionPathExists=/var/tmp/first_boot_disable_acs_redir

[Service]
Type=oneshot
ExecStartPre=/bin/rm /var/tmp/first_boot_disable_acs_redir
ExecStart=/bin/bash -c '/usr/bin/nvidia-acs-disable.sh run'
```
On older kernels, the `setpci` per-bridge method fires at `basic.target`:
```ini
[Service]
Type=oneshot
ExecStart=/bin/bash -c '/usr/bin/nvidia-acs-disable.sh run'
```
The script picks based on the running kernel version
(`OS_VER_HAS_DISABLE_ACS_REDIR`).

### `nvidia-pci-bridge-power.service`
```ini
[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/bin/nvidia-pci-bridge-power.sh'
```
Walks every NVIDIA-3D-controller's parent PCIe bridge and forces
**`/sys/bus/pci/drivers/pcieport/<BDF>/power/control = on`**. Prevents
bridges from entering ASPM low-power states that add link-exit latency.
Pairs with `pcie_aspm=off` in cmdline.

The script logic (extracted):
```bash
BRIDGE_BDF=( `lspci -D -d ::0604 | awk '{print $1}'` )
BRIDGE_SEC_BDF=( `lspci -vv -d ::0604 | grep "Bus: " | awk '{print $3}' | sed 's/secondary=//' | sed 's/,//'` )
BRIDGE_SUB_BDF=( `lspci -vv -d ::0604 | grep "Bus: " | awk '{print $4}' | sed 's/subordinate=//' | sed 's/,//'` )

for GPU_BUS in `lspci | grep "3D controller: NVIDIA" | awk '{print $1}' | sed 's/^....://' | sed 's/:..\..$//'`; do
  for i in "${!BRIDGE_BDF[@]}"; do
    if [ $((16#${BRIDGE_SEC_BDF[i]})) -le $((16#$GPU_BUS)) ] && \
       [ $((16#$GPU_BUS)) -le $((16#${BRIDGE_SUB_BDF[i]})) ]; then
      filename=$(echo "/sys/bus/pci/drivers/pcieport/BDF/power/control" | sed "s/BDF/${BRIDGE_BDF[i]}/")
      echo on > "$filename"
    fi
  done
done
```
The 16#-arithmetic finds the parent bridge by checking which bridge's
`secondary..subordinate` bus range covers the GPU's bus.

### `nvidia-mlnx-config.service`
```ini
[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/bin/nvidia-mlnx-config.sh'
```
The script (`/usr/bin/nvidia-mlnx-config.sh`) flips Mellanox firmware
settings:
- **`mlxconfig set ADVANCED_PCI_SETTINGS=1`** on every IB device
- **`mlxconfig set MAX_ACC_OUT_READ=44`** — sets max outstanding read
  requests to 44 (NVIDIA-tuned for ConnectX-6/7 + GPU traffic)
- Falls back to `mstconfig` (older Mellanox firmware tool) if `mlxconfig`
  isn't available
- Operates per-platform: only runs `mlxconfig_set_acc_bytes` on platforms
  where `NeedsAccBytesTuning=True` in the JSON (A100/A800 + DGX Stations)

### `nv-docker-gpus.service`
```ini
[Unit]
After=network.target
Before=containerd.service

[Service]
ExecStart=/usr/sbin/nv-docker-gpus
```
Generates a containerd override pinning to compute-class GPUs. The
script:
1. Filters `lspci` for "3D controller" + NVIDIA → list of compute GPUs.
2. Greps minor numbers from `nvidia-smi -q -i $BDF | grep "Minor Number"`.
3. Writes `/etc/containerd/conf.d/nv-docker-gpus.toml` referencing only
   the compute-class minors (excludes display GPUs on stations).

### `nvidia-ipmisol.service`
```ini
[Unit]
ConditionPathExists=/var/tmp/first-boot-nvidia-ipmisol

[Service]
Type=oneshot
ExecStartPre=/bin/rm /var/tmp/first-boot-nvidia-ipmisol
ExecStart=/usr/sbin/configure-ipmisol.bash enable
```
First-boot only. The script enables IPMI SOL on 10 channels:
```bash
i=1; MAX=10; CHANNEL=1
while [ ${i} -le ${MAX} ]; do
    ipmitool sol payload enable ${CHANNEL} ${i} >/dev/null 2>&1 || true
    i=$((i+1))
done
```
Plus writes the GRUB cmdline IPMI SOL drop-in (see §A.10 above).

### `cfg-nvme-hot-plug.service`
```ini
[Unit]
ConditionPathExists=/var/tmp/first-boot-nv-cfg-nvme-hot-plug

[Service]
Type=oneshot
ExecStart=/usr/sbin/configure-nvme-hot-plug.bash
```
First-boot only. Conditional on
`plat_supports_nvme_hot_plug` — adds `pci=realloc=on pcie_ports=native`
to GRUB only if the platform JSON says so.

### `icmp_disable.service`
```ini
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'iptables -A INPUT -p icmp --icmp-type timestamp-request -j DROP; iptables -A OUTPUT -p icmp --icmp-type timestamp-reply -j DROP'
```
Drops ICMP timestamp requests/replies (security hardening — historic
tooling fingerprint).

### `sed-unlock.service`
```ini
[Unit]
Wants=tcsd.service
Requires=local-fs.target
After=local-fs.target tcsd.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nv-disk-encrypt unlock
ExecStartPost=-/sbin/mdadm --assemble --scan
```
Unlocks self-encrypting drives (SED) using TPM-stored keys, then
re-assembles software RAID across the unlocked drives.

---

## udev — character device symlinks

`nvidia-chardev-links` → **`/lib/udev/rules.d/71-nvidia-ctk.rules`**:
```
ACTION=="add", DEVPATH=="/bus/pci/drivers/nvidia",
  RUN+="/usr/bin/nvidia-ctk system create-dev-char-symlinks --create-all"
```
Creates `/dev/char/<major>:<minor>` symlinks for every NVIDIA device
node. Required for CDI device specs to work — CDI references devices by
character-device symlink, not by `/dev/nvidia*` path.

---

## Helper scripts (runtime logic)

### `configure-tuned-profiles.bash` (in `nvidia-dgx-setup`)
```bash
PROCESS="$1"

configure-tuned-profiles_setup() {
    # Enable tuned and mask tuned-ppd (which fights the governor=performance setting)
    if ! systemctl is-active --quiet tuned; then
        systemctl enable --now tuned || true
    fi
    systemctl list-unit-files --type=service | grep -q "tuned-ppd"
    if [ $? -eq 0 ]; then
        systemctl disable --now tuned-ppd.service || true
        systemctl mask tuned-ppd.service || true
    fi

    # Source platform helpers
    . /usr/local/sbin/nv_scripts/general_funcs.bash
    . /usr/local/sbin/nv_scripts/plat_funcs.bash

    # Detect platform → activate matching profile
    PRODUCT_NAME=$(get_system_product_name 2>/dev/null || echo "")
    PLATFORM_SHORT=$(get_platform_short "${PRODUCT_NAME}" 2>/dev/null || echo "")

    if [ -n "${PLATFORM_SHORT}" ] ; then
        PROFILE="${PLATFORM_SHORT//_/-}-performance"   # e.g. dgx-h200-performance
        if [[ -d /usr/lib/tuned/profiles/${PROFILE} ]]; then
            tuned-adm profile "${PROFILE}" || true
        else
            echo "Warning: Profile not found, no profile activated"   # ← non-DGX outcome
        fi
    fi
}

configure-tuned-profiles_teardown() {
    # NOTE: deliberately does NOT unmask tuned-ppd
    tuned-adm profile throughput-performance
}
```
**Observation:** the script ACTIVATES profiles, it does not install
them. The `.conf` files for `dgx-<platform>-performance` profiles must
exist in `/usr/lib/tuned/profiles/` already — and they do not ship in
any of the public BaseOS repos.

### `nvidia-mlnx-config.sh` (Mellanox firmware tuning)
Two paths depending on tooling:
- **mlxconfig path** (newer): operates on interface names from `/sys/class/infiniband/`
- **mstconfig path** (older): operates on PCI BDFs from `/sys/bus/pci/devices/<bdf>/infiniband`

Both apply the same two settings:
```
ADVANCED_PCI_SETTINGS = 1
MAX_ACC_OUT_READ = 44
```

### `nvidia-relaxed-ordering-nvme.sh` (Samsung-only NVMe RO)
```bash
# Only allow on platforms where JSON sets NeedsRelaxedOrderingConfig=True
plat_needs_relaxed_ordering_config || exit 2

# Enumerate data drives (excludes boot drives) via get_data_drives.bash
DATA_DISKS=$(.../get_data_drives.bash | awk -F':' '{print $NF}' | sed 's/n1//g' | sed 's,/dev/,,g' | sed 's/,/ /g')

# Refuse on mixed vendors
PREVIOUS_VID="0xFFFF"
for x in ${DATA_DISKS}; do
    VID=$(cat /sys/class/nvme/${x}/device/vendor)
    if [ ${VID} != ${PREVIOUS_VID} ]; then
        if [ ${PREVIOUS_VID} = "0xFFFF" ]; then
            PREVIOUS_VID=${VID}
        else
            echo "Relaxed Ordering with mixed vendor NVMe disks is not supported"
            exit 2
        fi
    fi
done

# Samsung VID 0x144d → toggle feature 198
case "${VID}" in
    "0x144d")
        for x in ${DATA_DISKS}; do
            nvme set-feature ${x} -f 198 -v 1 -s   # enable
            # nvme set-feature ${x} -f 198 -v 0 -s   # disable
        done ;;
    *)
        echo "Relaxed Ordering is only supported on Samsung NVMe disks"
        exit 3
esac
```
Only Samsung VID `0x144d` is supported. Other-vendor NVMe drives are
left alone, and mixed-vendor configs hard-error out.

### `configure-nvme-hot-plug.bash`
```bash
plat_funcs="/usr/local/sbin/nv_scripts/plat_funcs.bash"
. ${plat_funcs}

if plat_supports_nvme_hot_plug; then
    paramstr="pci=realloc=on pcie_ports=native"
fi

if [ -n "${paramstr}" ]; then
    cat > /etc/default/grub.d/enable-nvme-hot-plug.cfg <<EOF
GRUB_CMDLINE_LINUX="\$GRUB_CMDLINE_LINUX ${paramstr}"
EOF
    /usr/sbin/update-grub
fi
```

### `configure-ipmisol.bash`
```bash
setup_ipmisol() {
    TTY=$(plat_get_default_serial_tty)   # ttyS0 or ttyS1 from JSON
    cat > /etc/default/grub.d/ipmisol.cfg <<EOF
GRUB_CMDLINE_LINUX="\$GRUB_CMDLINE_LINUX console=tty0 console=${TTY},115200n8"
GRUB_TERMINAL="\$GRUB_TERMINAL console serial"
GRUB_SERIAL_COMMAND="\$GRUB_SERIAL_COMMAND serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1"
EOF
    update-grub-cfg

    # Enable SOL on 10 channels for all users
    for i in $(seq 1 10); do
        ipmitool sol payload enable 1 ${i} >/dev/null 2>&1 || true
    done
}
```
Uses the per-platform `IPMIDefaultSerialTTY` field from the JSON
(ttyS0 for H100/H200/B200/B300/GB200/GB300, ttyS1 for everything else).

---

## Platform detection regex strings

The complete set of `dmidecode --string system-product-name` patterns
NVIDIA matches, with the platform name they map to:

```
DGX-1                                              → dgx1
DGX-2                                              → dgx2
DRIVE CONSTELLATION                                → dcs
X11DPG-OT, SYS-4029GP-TRT                          → dcs_legacy
SYS-420GP-TNR                                      → c2_ovx
PIO-420GP-TNR-01-NC24B, X12DPG-OA6                 → c2_io
920-23687-2535-                                    → dgx_a800
920-23687-, 675-23287-, 920-23287-                 → dgx_a100
DGXH100, DGX H100                                  → dgx_h100
DGXH200, DGX H200                                  → dgx_h200
DGXH800, DGX H800                                  → dgx_h800
DGXB200, DGX B200                                  → dgx_b200
DGXB300, DGX B300                                  → dgx_b300
DGXGB200, DGX GB200, GB200 NVL                     → dgx_gb200
DGXGB300, DGX GB300, GB300.*NVL                    → dgx_gb300
DGX Spark                                          → dgx_spark
GALAXY-GB300                                       → dgx_gb300ws
^DGX Station$, DiGiTS Dev Box2                     → dgxstation
920-23487-2535, 675-23487-0200                     → dgxstation_a800
920-23487-, 675-23487-, DGX Station A100           → dgxstation_a100
QEMU                                               → kvm
VirtualBox                                         → virtualbox (DGX-1/2/2H sub-types via /proc/cmdline)
UT2.1 DP Chassis                                   → l4t_ut2_1
Grace CPU P.*                                      → l4t_c2
GH200 P.*                                          → l4t_cg1
Grace Hopper x4 P.*                                → l4t_cg4
P4261                                              → l4t_keystone
P4486                                              → l4t_oberon
ARS-, MBD-G1SMH, Super Server                      → l4t_smcmgx
```

To force a platform identity for testing (overrides DMI detection):
```
echo "<platform_name>" > /usr/share/nvidia/force_platform
```
Only `c2_io c2_ovx dcs dcs_legacy dgx1 dgx2 dgx_a800 dgx_a100
dgxstation_a100 dgxstation_a800 dgxstation` are valid forced values;
anything else maps to `other`.

---

## What's NOT in the public repo (gated)

After dumping the full package list across Ubuntu jammy (106 packages in
`common`, 35 in `dgx`), Ubuntu noble (8), and EL10 (19), these items
referenced in the DGX docs are **absent**:

| Missing artifact | Where docs say it lives | Reality |
|------------------|------------------------|---------|
| `dgx-<platform>-performance/tuned.conf` (the actual TuneD profile bundles) | `nvidia-tuned-profiles` package | Not in any public repo. DGX BaseOS ISO or NVAIE-gated only. |
| `nvidia-base/tuned.conf` | `nvidia-tuned-profiles` | Same. |
| `dgx-base/tuned.conf` | `nvidia-tuned-profiles` | Same. |
| Per-platform performance variants (`nvidia-x86-64-performance`, `nvidia-no-mitigations`, `nvidia-acs-disable`, `nvidia-crashdump-core`) | DGX EL10 user guide | TuneD profile of these names is gated. The acs-disable RPM is the binary-action equivalent (not a TuneD profile). |
| `dgx-h200-system-configurations` etc. (the metapackages that pull in per-platform settings) for Hopper/Blackwell | Should mirror `dgx-a100-system-configurations` | Only A100/A800/dgx1/dgx2/station versions exist publicly (jammy). Hopper+ metapackages are DGX-internal only. |

For non-DGX hosts: the right path is to install the individual settings
packages from the public `common` component (jammy) — they cover most of
what `nvidia-tuned-profiles` would do — and skip the TuneD-profile shortcut
entirely. Use the custom `inference-h200/tuned.conf` template in
`tuned-profiles.md` to bundle the equivalent settings into a single
profile.

---

## Extraction recipe for non-DGX users

The NVIDIA repos are a public package source — operators on Dell XE9680,
Supermicro AS-8125GS, HPE Apollo, custom whitebox, or cloud VMs can pull
the `.deb` files directly and copy the config files in. No NVIDIA repo
registration required.

### One-line per package (Ubuntu jammy, x86_64):
```bash
PKG=nv-iommu-pt   # or nv-mitigations-off, nv-hugepage, nvidia-kernel-defaults, etc.
URL_BASE="https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64"
curl -s "$URL_BASE/dists/jammy/common/binary-amd64/Packages.gz" \
  | gunzip \
  | awk -v pkg="$PKG" '/^Package: /{p=($2==pkg)} p && /^Filename: /{print $2}' \
  | head -1 \
  | xargs -I{} curl -sLO "$URL_BASE/{}"
```

### Bulk-download all settings packages (jammy `common`):
```bash
URL_BASE="https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64"
mkdir -p /tmp/nv-settings && cd /tmp/nv-settings

# Pull every package whose name starts with nv- or nvidia-
curl -s "$URL_BASE/dists/jammy/common/binary-amd64/Packages.gz" | gunzip > Packages

for pkg in nv-iommu-pt nv-mitigations-off nv-hugepage nv-cpu-governor \
           nv-limits nv-persistence-mode nv-ast-modeset nv-pci-dbg \
           nv-update-disable nv-smartd-disable nv-enable-nvme-hot-plug \
           nvidia-acs-disable nvidia-pci-bridge-power nvidia-pci-no-realloc \
           nvidia-deadline-scheduler nvidia-kernel-defaults \
           nvidia-relaxed-ordering-gpu nvidia-relaxed-ordering-nvme \
           nvidia-fs-loader nvidia-peermem-loader nvidia-drm-options \
           nvidia-mlnx-config nvidia-ipmisol nvidia-icmp \
           nvidia-conf-cachefilesd nvidia-chardev-links \
           nv-docker-options nv-docker-gpus nvidia-esm-hook-epilogue \
           nv-common-apis ; do
    fn=$(awk -v p="$pkg" '/^Package: /{cp=$2} cp==p && /^Filename: /{print $2; exit}' Packages)
    [ -n "$fn" ] && curl -sLO "$URL_BASE/$fn"
done
```

### Extract a `.deb` without `dpkg-deb` (Fedora/Arch/macOS):
```bash
deb=nv-iommu-pt.deb
mkdir -p extract && cd extract
ar x "../$deb"
# Try both compression formats (jammy: data.tar.xz; future: data.tar.zst)
[ -f data.tar.xz ] && tar xf data.tar.xz
[ -f data.tar.zst ] && tar --use-compress-program=zstd -xf data.tar.zst
[ -f data.tar.gz ] && tar xf data.tar.gz
# Files are now in ./etc/, ./usr/, ./lib/ etc.
```

### Extract an EL10 `.rpm`:
```bash
mkdir -p extract && cd extract
rpm2cpio ../nvidia-acs-disable-25.08-1.el.noarch.rpm | cpio -idm
```

### Apply (manually, on a non-DGX host):
After extracting, copy the relevant files into place:
```bash
# Per-extracted package, copy its config files to the live system:
cp -r etc/default/grub.d/*.cfg /etc/default/grub.d/
cp -r etc/sysctl.d/*.conf /etc/sysctl.d/
cp -r etc/modprobe.d/*.conf /etc/modprobe.d/
cp -r etc/modules-load.d/*.conf /etc/modules-load.d/
cp -r etc/security/limits.d/*.conf /etc/security/limits.d/
cp -r lib/systemd/system/*.service /etc/systemd/system/

# Apply
update-grub      # for any grub.d/ changes — then reboot
sysctl --system  # for sysctl.d/
systemctl daemon-reload
systemctl enable --now nv-cpu-governor   # plus any other services wanted
```
Skip the units that won't apply (e.g. `nvidia-mlnx-config.service`
expects `nv_scripts/plat_funcs.bash` from `nv-common-apis` — install
that package first if its detection logic is needed).

---

## Sources verified 2026-05-05

- `https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/Release` (HTTP 200, 5 components: common dcs dgx egx preview c2)
- `https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/common/binary-amd64/Packages.gz` (HTTP 200, 106 packages)
- `https://repo.download.nvidia.com/baseos/ubuntu/jammy/x86_64/dists/jammy/dgx/binary-amd64/Packages.gz` (HTTP 200, 35 packages)
- `https://repo.download.nvidia.com/baseos/ubuntu/noble/x86_64/dists/noble/dgx/binary-amd64/Packages.gz` (HTTP 200, 8 packages)
- `https://repo.download.nvidia.com/baseos/el/10/x86_64/dgx/repodata/repomd.xml` (HTTP 200, 19 RPMs)
- `nv-common-apis-25.10-1.el.noarch.rpm` extracted; ships
  `/etc/nvidia-platform.d/nvidia-platform-configs.json` with 22 platform entries.
