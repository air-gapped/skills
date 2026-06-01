# Linux bare metal — audit, fwupd-free manual db append, and the reinstall decision

For Dell hardware, prefer the iDRAC path (`dell-poweredge.md`) — it also delivers the 2023 KEK. Use the
OS-side append below for non-Dell bare metal, or when you want to enroll the `db` cert from the OS without an
iDRAC BIOS flash/reboot.

## Audit (read-only)

```bash
sudo mokutil --sb-state                                          # Secure Boot on?
sudo mokutil --kek | grep -i "Microsoft Corporation KEK 2K CA 2023"
sudo mokutil --db  | grep -iE "Microsoft UEFI CA 2023|Windows UEFI CA 2023"
sudo mokutil --db  | grep -i "Microsoft Corporation UEFI CA 2011"     # the old one (expected present)
# efitools alternative (raw EFI var dump; prints each cert's Subject CN):
sudo efi-readvar -v KEK | grep -i 2023
sudo efi-readvar -v db  | grep -i 2023
```
**Verdict:** *NEEDS UPDATE* if `db` has `…UEFI CA 2011` but not `Microsoft UEFI CA 2023`. *GOOD* if `db` shows
`Microsoft UEFI CA 2023` (+ `Windows UEFI CA 2023`) and KEK shows `KEK 2K CA 2023`.

## The fwupd-free manual db append (works everywhere; no Setup Mode)

The 2023 `db` payloads are signed by the **2011 KEK** every machine already has, so they self-authenticate and
append directly. db efivar GUID = `d719b2cb-3d3a-4596-a3bc-dad00e67656f`.

```bash
cd /tmp
# Microsoft UEFI CA 2023 — the Linux shim signer (the one that matters):
curl -fLO https://raw.githubusercontent.com/microsoft/secureboot_objects/main/PostSignedObjects/Optional/DB/amd64/DBUpdate3P2023.bin
# Windows UEFI CA 2023 — only if the box dual-boots / will run Windows:
curl -fLO https://raw.githubusercontent.com/microsoft/secureboot_objects/main/PostSignedObjects/Optional/DB/amd64/DBUpdate2024.bin
# Option ROM 2023 — optional (PCIe option ROMs):
curl -fLO https://raw.githubusercontent.com/microsoft/secureboot_objects/main/PostSignedObjects/Optional/DB/amd64/DBUpdateOROM2023.bin

sudo chattr -i /sys/firmware/efi/efivars/db-d719b2cb-3d3a-4596-a3bc-dad00e67656f
sudo efi-updatevar -a -f DBUpdate3P2023.bin db          # -a = append (never replace)
sudo chattr +i /sys/firmware/efi/efivars/db-d719b2cb-3d3a-4596-a3bc-dad00e67656f
```
*(Alternative: stage under `/etc/secureboot/keys/db/` and `sudo sbkeysync --verbose`.)* Re-audit, then reboot.
The payload filenames are confirmed against `microsoft/secureboot_objects` — note `DBUpdate2024.bin` *contains*
the **Windows UEFI CA 2023** (the file-year is the servicing year, not the cert year).

**KEK 2023:** there's no generic signed payload (see `mechanism.md`). On whitebox you either self-sign the raw
`microsoft corporation kek 2k ca 2023.der` with your own PK (Setup Mode), or accept keeping the 2011 KEK — the
db cert alone still lets you *boot* 2023-signed bootloaders; you just won't get *future* 2023-KEK-signed db/dbx
pushes. On Dell, take the KEK via the BIOS path instead.

## fwupd — only if it's a supported laptop/desktop on LVFS, and only ≥ 2.0.8

The `uefi-db`/`uefi-kek` plugins that perform this rotation exist only in **fwupd ≥ 2.0.8**. Stock Ubuntu is
too old (verify on Launchpad at use time — historically jammy `-updates` = 1.7.9, noble `-updates` = 1.9.34,
and the 2.0.20 backport sat in `-proposed`). 26.04 ships fwupd ≥ 2.1 with the plugins. To get a new-enough
fwupd on 22.04/24.04: `sudo snap install fwupd` (Canonical-maintained; `--channel=2.0.x/stable` for the 2.0
track) — **remove the deb fwupd first; two daemons conflict.** Then:
```bash
sudo fwupdmgr refresh && sudo fwupdmgr get-updates && sudo fwupdmgr update
sudo fwupdmgr security          # the "UEFI db" HSI attribute flips to passing once 2023 is in db
```
fwupd is irrelevant on Dell PowerEdge (not on LVFS) and in VMs (no capsule path).

## The reinstall decision (patch-in-place vs reinstall to 24.04/26.04)

**Reinstalling the OS does NOT touch the firmware `db`/`KEK`** — NVRAM is OS-independent (Red Hat states this
explicitly). A 26.04 install only ships a freshly 2023-aware shim/grub/fwupd stack; you **still** enroll the
cert into firmware. So:

- **22.04 long-uptime boxes:** don't reinstall *for the cert problem* — it won't help. Audit + enroll the 2023
  `db` (or take the Dell iDRAC path). Reinstall only for other reasons (support window, newer fwupd-by-default).
- **24.04** is "better equipped" only in that its fwupd baseline is closer to 2.0 — but it still needs the
  snap/backport, so the manual `db` append is the more reliable path there too.
- **26.04** is the one release where `fwupdmgr` would just work on supported hardware — still irrelevant on
  PowerEdge and in VMs.

**Bottom line:** the firmware-cert fix is orthogonal to OS version. Decouple the two decisions.
