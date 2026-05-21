# Secure Boot + MOK + DKMS

The full Ubuntu 24.04 LTS Secure Boot story for B300, where both NVIDIA modules and DOCA-OFED modules need signing. Key insight: **one DKMS MOK signs both stacks**.

## Why MOK is unavoidable on B300

DOCA-OFED builds its ConnectX kernel modules via DKMS — there is no Canonical-signed precompiled ConnectX path. On a Blackwell host with Secure Boot enabled, a MOK MUST be enrolled to sign the DOCA modules. Once enrolled, the same MOK signs NVIDIA's DKMS modules too — no second key, no second enrollment.

The Canonical-signed precompiled NVIDIA path (`linux-modules-nvidia-XXX-open-generic-hwe-24.04`) saves signing NVIDIA modules but does NOT save MOK enrollment because DOCA still needs it. Net: still must enroll one MOK. The single-source-CUDA-repo path (this skill's recommendation) is therefore not worse than the mixed path on the SB axis.

## Boot chain on Ubuntu 24.04 under SB

```
UEFI firmware
  └─ Microsoft-signed shim (shim-signed 1.58+15.8-0ubuntu1 in noble)
      └─ Canonical-signed GRUB
          └─ Canonical-signed kernel
              └─ Module signature check (kernel keyring)
                  ├─ Canonical Master CA (embedded in shim)
                  └─ MOK list (enrolled via mokutil)
```

The Canonical Master CA is embedded in shim, NOT pre-enrolled in firmware — that's why Canonical-signed modules work without user action. Third-party DKMS modules need their own MOK on the MOK list.

## First-time MOK setup

```bash
# Check SB state
sudo mokutil --sb-state
# Output: SecureBoot enabled    (or "disabled" — skip this whole file if so)

# Generate the DKMS key pair (creates /var/lib/dkms/mok.key and mok.pub)
sudo update-secureboot-policy --new-key

# Import the public half into the MOK list
sudo mokutil --import /var/lib/dkms/mok.pub
# Set a one-shot password — required at next boot to confirm enrollment

# Reboot — MokManager runs and prompts for the password
sudo reboot
# In MokManager: "Enroll MOK" → "Continue" → "Yes" → enter password → reboot

# After reboot, verify
sudo mokutil --list-enrolled | grep -i dkms
# Should show the DKMS MOK with CN containing "DKMS" or "Secure Boot Module Signature key"
```

MOK keys carry the Code-Signing OID `1.3.6.1.4.1.2312.16.1.2`, restricting them to module signing — they cannot be used to sign kernel images or shim itself.

## DKMS auto-sign mechanics

Ubuntu's DKMS includes `dkms_sign_tool`. On every `dkms install`:
1. DKMS builds the module
2. DKMS signs it with `/var/lib/dkms/mok.key`
3. The signature is embedded in the `.ko` file

You enroll the public half once via MOK; subsequent DKMS rebuilds (on kernel upgrade, NVIDIA driver upgrade, DOCA upgrade) sign automatically with the same key. **No re-enrollment needed.**

This applies to both NVIDIA modules (`nvidia-dkms-open`) and DOCA-OFED modules (`mlnx-ofed-kernel-dkms`, `iser-dkms`, `knem-dkms`, etc.) — same `/var/lib/dkms/mok.pub` covers everything.

## Failure signatures when SB is on but the key isn't enrolled

```
# dmesg
PKCS#7 signature not signed with a trusted key
Loading of unsigned module is rejected

# modprobe
modprobe: ERROR: could not insert 'nvidia': Operation not permitted

# lsmod
(nvidia module absent despite package being installed)

# nvidia-smi
No devices were found
```

These all mean: the .ko on disk is signed, but the signing key isn't on the MOK list. Fix: `sudo mokutil --import /var/lib/dkms/mok.pub`, reboot through MokManager.

## Verify a built module is signed

```bash
# Check sig info embedded in the module file
modinfo nvidia | grep -i ^sig
# Look for:
#   sig_id:         PKCS#7
#   signer:         DKMS module signing key
#   sig_key:        <hex fingerprint>
#   sig_hashalgo:   sha256

# List keys the kernel trusts at runtime
sudo keyctl list %:.platform     # firmware/OEM keys
sudo keyctl list %:.machine      # MOK list — the DKMS CN should appear here

# See shim handing keys to the kernel keyring at boot
dmesg | grep -iE 'mok|integrity|Loading.*key'
```

## Manual signing (when DKMS auto-sign isn't enough)

To sign an out-of-tree module manually:

```bash
sudo /usr/src/linux-headers-$(uname -r)/scripts/sign-file sha256 \
  /var/lib/dkms/mok.key /var/lib/dkms/mok.pub <module.ko>
```

For Mellanox/DOCA out-of-tree builds, env vars to invoke signing during build:

```bash
WITH_MOD_SIGN=1 \
MODULE_SIGN_PUB_KEY=/var/lib/dkms/mok.pub \
MODULE_SIGN_PRIV_KEY=/var/lib/dkms/mok.key \
/opt/mellanox/doca/tools/doca-kernel-support
```

## kernel.lockdown=integrity under SB

Setting `kernel.lockdown=integrity` is automatic when SB is on. Restrictions:
- Blocks `/dev/mem`, custom ACPI tables, unsigned kexec, hibernation
- Blocks MSR writes via `/dev/cpu/*/msr`
- Blocks unsigned module load

Does NOT restrict: normal userspace, GPU compute, RDMA, signed-module load. `nvidia-peermem` / GDR-Copy / `nv_peer_mem` work fine because they touch only PCI BARs from signed kernel modules.

## Air-gap non-interactive MOK seeding

Most air-gap sites lack interactive KVM access for the MokManager password prompt. Two options:

### Option A: Pre-bake the MOK into the golden image

```bash
# On the golden-image builder
sudo openssl req -new -x509 \
  -newkey rsa:2048 -nodes -days 3650 \
  -outform DER -keyout /var/lib/dkms/mok.key \
  -out /var/lib/dkms/mok.pub \
  -subj "/CN=Site DKMS Module Signing Key (B300 fleet)/"

# Bake the keys into the image at /var/lib/dkms/mok.{key,pub}
# Boot image, run mokutil --import once, password supervised over IPMI/KVM
sudo mokutil --import /var/lib/dkms/mok.pub
```

After enrollment, every B300 in the fleet uses the same MOK. Threat model: a stolen private key compromises module signing for the whole fleet. Acceptable for many sites; not for high-security ones.

### Option B: Unique MOK per host

Each host generates its own key on first boot, requires one supervised reboot via iDRAC virtual KVM to confirm MokManager. More secure, more operational overhead. See [[improvement-backlog]] for the open per-host-vs-site-wide question.

## Disabling Secure Boot entirely

If the threat model allows it, the simplest path is to disable Secure Boot in BIOS/UEFI. Skip this whole file. Verify with:

```bash
sudo mokutil --sb-state
# SecureBoot disabled
```

DKMS still works; modules are unsigned but the kernel doesn't enforce signatures when SB is off. This is what many GPU sites do in production — the tradeoff is no firmware-level attestation — supply-chain trust comes from mirror + GPG.

## What goes wrong with kernel upgrades

DKMS rebuilds NVIDIA + DOCA modules automatically when a new kernel is installed via `linux-image-*` apt upgrade. Modules are re-signed with the same MOK. No manual intervention needed.

If a kernel upgrade lands but DKMS rebuild fails (e.g. headers missing for the new kernel):

```bash
# Find what DKMS thinks is broken
sudo dkms status

# Force a rebuild
sudo dkms autoinstall

# Logs
sudo journalctl --no-pager -u nvidia-fabricmanager
ls -la /var/lib/dkms/nvidia/*/build/make.log
```

Usually fixed by installing `linux-headers-$(uname -r)` and re-running `dkms autoinstall`.

## References

- Ubuntu Wiki — UEFI/SecureBoot: https://wiki.ubuntu.com/UEFI/SecureBoot
- Ubuntu Wiki — UEFI/SecureBoot/DKMS: https://wiki.ubuntu.com/UEFI/SecureBoot/DKMS
- Ubuntu Security docs — Secure Boot: https://documentation.ubuntu.com/security/security-features/platform-protections/secure-boot/
- Debian Wiki — SecureBoot (lockdown=integrity behaviour): https://wiki.debian.org/SecureBoot
- NVIDIA DOCA Host Install + DKMS Management: https://docs.nvidia.com/doca/sdk/doca-host-installation-and-dkms-management-guide/
