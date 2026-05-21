# Hopper recipe — H100 / H200 / GH200

Companion to [[recipe]] (which is Blackwell-centric). Hopper install is **strictly simpler** because most B300-specific complexity is absent: no CX bridge, no NVLSM, no DOCA-OFED.

This file covers the three Hopper-class chassis variants in deployment:

- **HGX 4-GPU SXM (XE8640)** — direct NVLink, **no NVSwitch**, no Fabric Manager
- **HGX 8-GPU SXM (XE9680)** — NVSwitch fabric, Fabric Manager required
- **Grace Hopper GH200** — open kernel modules *mandatory*; otherwise like 8-GPU SXM

## Topology → install matrix

| Chassis | Topology | NVSwitch | FM | NVLSM | DOCA-OFED | nvidia-imex | open modules |
|---|---|---|---|---|---|---|---|
| XE8640 (4× H100 SXM5) | direct NVLink4 mesh | ❌ | ❌ | ❌ | ❌ | optional | recommended |
| XE9680 (8× H100 SXM5) | 3rd-gen NVSwitch | ✅ | ❌ | ❌ | ❌ | optional | recommended |
| XE9680 (8× H200 SXM5) | 3rd-gen NVSwitch | ✅ | ❌ | ❌ | ❌ | optional | recommended |
| GH200 / NVL2 | direct NVLink4 over chip-to-chip | ❌ | ❌ | ❌ | ❌ | optional | **mandatory** |
| HGX H200 NVL (2× PCIe + NVLink bridge) | direct NVLink bridge | ❌ | ❌ | ❌ | ❌ | optional | recommended |
| L40S/L4 (PCIe inference cards) | none | ❌ | ❌ | ❌ | ❌ | ❌ | recommended |

Source: NVIDIA FM User Guide explicitly states *"The HGX A100 4-GPU system does not include NVSwitch, so FM is not a required component on this system configuration"* — same rule applies to HGX H100 4-GPU SXM baseboard. The 8-GPU HGX H100 baseboard contains **4× third-generation NVSwitch** ASICs in a fully-meshed topology.

## XE8640 — H100 4-GPU minimal install

The simplest install in this skill. Three apt packages.

```bash
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

sudo apt install nvidia-driver-pinning-580
sudo apt install nvidia-open-580                  # driver + persistenced + utils + open kernel modules
sudo apt install nvidia-container-toolkit

# Optional but recommended for NVLink GPU-to-GPU memory mapping workloads:
sudo apt install nvidia-imex-580
```

Skip everything else from the B300 recipe — no DOCA, no MOK-for-OFED, no fabricmanager service, no NVLSM.

**Validation on XE8640:**

```bash
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
# Expect: 4 H100 lines, matching driver

systemctl is-active nvidia-persistenced
# active

lsmod | grep ^nvidia
# nvidia, nvidia_uvm, nvidia_drm, nvidia_modeset, nvidia_peermem (optional)

# NO fabric registration check — there's no fabric
# (nvidia-smi -q -i 0 won't emit a "Fabric" section on a 4-GPU baseboard)

nvidia-smi nvlink --status -i 0
# Expect: 18 NVLink4 links per GPU, all "Up"
```

`scripts/health-check.sh` handles XE8640 automatically — it detects the missing fabric section (`has_fabric=0`) and returns SKIPPED for FM/NVLSM/ib_umad rather than FAIL.

## XE9680 — H100/H200 8-GPU install

H200 needs minimum driver 535+; the user's 580 branch is well past that. Hopper VBIOS gate applies — see [[troubleshooting]] §"R580 fails to init on Hopper subrev 3".

```bash
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

sudo apt install nvidia-driver-pinning-580
sudo apt install nvidia-open-580                  # Hopper supports both; open is recommended
sudo apt install cuda-drivers-fabricmanager-580   # meta → nvidia-fabricmanager-580 + libnvidia-nscq-580
sudo apt install nvidia-container-toolkit

# Optional:
sudo apt install nvidia-imex-580

# Enable + start FM
sudo systemctl enable --now nvidia-fabricmanager
```

`cuda-drivers-fabricmanager-580` Depends (apt-cache-verified): just `nvidia-fabricmanager-580`. That in turn depends on `nvidia-kernel-common-580-server`. Total install: ~8 packages incl. transitive.

**Validation on XE9680:**

```bash
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
# Expect: 8 H100/H200 lines

systemctl is-active nvidia-persistenced nvidia-fabricmanager
# active active

# NVLSM is NOT used on 3rd-gen NVSwitch — there's no nvidia-nvlsm.service
systemctl is-active nvidia-nvlsm 2>/dev/null || echo "(correctly absent on Hopper)"

# Fabric registration (3rd-gen NVSwitch uses ALI — trained at hardware)
nvidia-smi -q -i 0 | grep -A 2 Fabric
# Expect: State: Completed, Status: Success

nvidia-smi nvlink --status -i 0
# Expect: 18 NVLink4 links per H100, ~13 per H200 — all "Up" at NVLink4 speed
```

## Open vs proprietary on Hopper

Per NVIDIA's open-modules transition blog (R560+):

| Architecture | Open modules required? |
|---|---|
| Maxwell, Pascal, Volta | ❌ proprietary only |
| Turing, Ampere, Ada Lovelace | open or proprietary (open recommended) |
| **Hopper** | open or proprietary (open recommended) |
| **Grace Hopper (GH200)** | **open MANDATORY — proprietary unsupported** |
| Blackwell (B100/B200/B300) | open MANDATORY |

Regular Hopper (H100/H200 SXM5, H200 NVL, H100 PCIe) accepts both. Grace Hopper (GH200) follows the Blackwell rule — open is the only option. The skill's recommendation is open across the board for forward consistency; if a workload regresses on open, fall back to `cuda-drivers-580` (proprietary).

## H200 NVL — 2-GPU PCIe with NVLink bridge

XE9680 supports SXM5 H200; H200 NVL is a different SKU (PCIe form factor, 2× cards in an NVLink-bridge pair). The install is the same as a PCIe inference card — no Fabric Manager, no NVSwitch.

```bash
sudo apt install nvidia-driver-pinning-580 nvidia-open-580 nvidia-container-toolkit
# Optional: nvidia-imex-580 for cross-bridge mem mapping
```

`nvidia-smi nvlink --status` shows the bridge link, but there's no fabric to register.

## Dell XE8640 firmware notes

The XE8640 has its own HGX H100 4-GPU baseboard firmware bundle (different from XE9680's 8-GPU bundle, different from XE9780's B300 bundle). Find at Dell support → service tag → System Update → "HGX H100 4-GPU Baseboard Assembly".

The **iDRAC Direct USB Port BIOS gotcha (KB 000308105) applies to XE8640 too** — same family as XE9680/XE9640 for GPU baseboard firmware updates over iDRAC. See [[dell-firmware]] §"XE9680/XE9640/XE8640 iDRAC Direct USB Port gotcha".

The DellOemChassis.ExtendedReset Redfish recipe in [[dell-firmware]] applies identically to XE8640's GPU baseboard firmware activation.

## What the skill's other references say about Hopper

- [[recipe]] — primary recipe is B300-centric; treat Hopper as the "skip steps 4 (DOCA), 7 (fabric-stack), 2 (MOK)" simplification
- [[packages]] — `cuda-drivers-fabricmanager-XXX` is the Hopper FM meta; `nvlink5-XXX` is Blackwell-only
- [[troubleshooting]] — `cudaErrorSystemNotReady` still applies on XE9680 (FM not running); not relevant on XE8640 (no FM)
- [[gpu-operator]] — pre-installed-driver-mode helm values are the same across Hopper and Blackwell
- [[secure-boot]] — MOK enrollment same; on Hopper only the NVIDIA driver DKMS modules need signing (no DOCA modules)
