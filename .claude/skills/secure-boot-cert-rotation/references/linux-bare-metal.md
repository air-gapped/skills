# Linux bare metal — audit, fwupd-free manual db append, and the reinstall decision

- [Audit](#audit-read-only)
- [The fwupd-free manual db append](#the-fwupd-free-manual-db-append-works-everywhere-no-setup-mode)
- [Firmware-menu enrollment + the ESP staging trick](#firmware-menu-enrollment-amiwhitebox-key-management-and-the-esp-staging-trick)
- [fwupd — when it applies](#fwupd-only-if-its-a-supported-laptopdesktop-on-lvfs-and-only-208)
- [The reinstall decision](#the-reinstall-decision-patch-in-place-vs-reinstall-to-24042604)

For Dell hardware, prefer the iDRAC path (`dell-poweredge.md`) — it also delivers the 2023 KEK. Use the
OS-side append below for non-Dell bare metal, or to enroll the `db` cert from the OS without an
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

**KEK 2023:** there's no generic signed payload (see `mechanism.md`). On whitebox, either self-sign the raw
`microsoft corporation kek 2k ca 2023.der` with a local PK (Setup Mode), or accept keeping the 2011 KEK — the
db cert alone is enough to *boot* 2023-signed bootloaders; what it forfeits is *future* 2023-KEK-signed db/dbx
pushes. On Dell, take the KEK via the BIOS path instead.

## Firmware-menu enrollment (AMI/whitebox Key Management) — and the ESP staging trick

The OS-side append above does **db** only. To also enroll the **2023 KEK** (no generic in-band KEK payload
exists), or to use the firmware UI instead, enroll from **UEFI Setup → Key Management**. Field-proven on
whitebox AMI (ASRock Rack, etc.) — enrolls db+KEK in one console pass.

**Files = raw `.der` from `PreSignedObjects/`** — NOT the `.bin` in `PostSignedObjects/` (those are the *signed*
payloads for the in-band `efi-updatevar`/`dbxtool` path above). In `microsoft/secureboot_objects`:
- db: `PreSignedObjects/DB/Certificates/microsoft uefi ca 2023.der` (+ `windows uefi ca 2023.der` only if
  dual-booting Windows; `microsoft option rom uefi ca 2023.der` only for MS-signed option ROMs)
- KEK: `PreSignedObjects/KEK/Certificates/microsoft corporation kek 2k ca 2023.der`
- Do **not** enroll `PreSignedObjects/PK/Certificate/WindowsOEMDevicesPK.der` (that's MS's PK for *their* devices).
- Slim 8.3 names for the picker (AMI filters by extension — `.cer`/`.der`/`.crt` all work; FAT volume):
  `MSUEFI23.CER` (db, Microsoft UEFI CA 2023 — *required for Linux*), `MSKEK23.CER` (KEK 2K CA 2023),
  `MSWIN23.CER` (db, Windows UEFI CA 2023 — only if the host boots Windows), `MSOROM23.CER` (db, Option ROM
  UEFI CA 2023 — only for MS-signed add-in-card option ROMs). Enroll the full set for factory-parity; only
  `MSUEFI23.CER` is load-bearing on a Linux host.

**Staging medium — the firmware file browser reads any FAT volume it enumerates at Setup time:**
1. **FAT32 USB** — `mkfs.vfat -F32 -n SBKEYS2023 /dev/sdXN`; the picker shows the volume by label.
2. **ESP trick (no USB, no iKVM virtual-media):** `sudo cp *.cer /boot/efi/` — Key Management browses the live
   FAT32 **ESP** exactly like fwupd reads it. Pair with **iKVM console-only** for a fully-remote enroll, dodging
   the flaky virtual-media layer entirely. Delete the files afterward to keep the ESP tidy.

**AMI flow:** Secure Boot Mode → **Custom** → **Key Management** → select **Authorized Signatures** (db) or
**Key Exchange Keys** (KEK) → **Append** (*Set New*/*Update* **replace** — don't use them) → pick the file →
**Public Key Certificate** (raw cert; not "Authenticated Variable") → accept the default owner GUID. **Never touch
PK.** Menu enrollment self-authorizes by physical presence (no KEK signature needed), unlike the in-band append.

**Confirm it took (no reboot required):** the variable's `Keys#` increments and `Key Source` flips
**`Default` → `Mixed`** on the Key Management screen. Verify in-OS after reboot with the §Audit `mokutil` greps.
Append keeps the 2011 certs alongside — that's correct.

## fwupd — only if it's a supported laptop/desktop on LVFS, and only ≥ 2.0.8

The `uefi-db`/`uefi-kek` plugins that perform this rotation exist only in **fwupd ≥ 2.0.8**. **Stock Ubuntu is
no longer too old** — the 2.0.20 backport left `-proposed` and landed in both LTS `-updates` pockets on
2026-07-09 (`jammy-updates` / `noble-updates` = `2.0.20-1ubuntu2~22.04.2` / `~24.04.2`), and 26.04 ships
2.1.1. So `sudo apt update && sudo apt upgrade` is now the normal way to clear the floor; re-verify on
Launchpad at use time. The snap (`sudo snap install fwupd`, Canonical-maintained, stable = 2.1.7) remains a
fallback for older pockets — **remove the deb fwupd first; two daemons conflict** — but prefer snap **≥ 2.1.6**
if enrolling a KEK: earlier snap builds installed the wrong blob for KEK updates (fixed in 2.1.6). Then:
```bash
sudo fwupdmgr refresh && sudo fwupdmgr get-updates && sudo fwupdmgr update
sudo fwupdmgr security          # the "UEFI db" HSI attribute flips to passing once 2023 is in db
```
fwupd is irrelevant on Dell PowerEdge (not on LVFS) and in VMs (no capsule path).

## The reinstall decision (patch-in-place vs reinstall to 24.04/26.04)

**Reinstalling the OS does NOT touch the firmware `db`/`KEK`** — NVRAM is OS-independent (Red Hat states this
explicitly). A 26.04 install only ships a freshly 2023-aware shim/grub/fwupd stack; the cert **still** has to
be enrolled into firmware. So:

- **22.04 long-uptime boxes:** don't reinstall *for the cert problem* — it won't help. Audit + enroll the 2023
  `db` (or take the Dell iDRAC path). Reinstall only for other reasons (support window, newer fwupd-by-default).
- **24.04 (and 22.04)** now reach a cert-capable fwupd through `-updates` alone — so OS version no longer
  gates the fwupd path on either LTS. What still gates it is *hardware coverage* (LVFS), not the release.
- **26.04** ships 2.1.1 out of the box — but that only matters on LVFS-covered hardware, so it remains
  irrelevant on PowerEdge and in VMs.

**Bottom line:** the firmware-cert fix is orthogonal to OS version. Decouple the two decisions.
