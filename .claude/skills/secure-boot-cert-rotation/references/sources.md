# Sources (primary / high-credibility)

Grounded 2026-06-01. Re-verify volatile leaf numbers (Dell BIOS minimums, Ubuntu fwupd pockets, Harvester
release dates / virt-launcher OVMF) against these at use time — methodology is durable, version numbers are not.

## Freshness ledger

Per-source verification dates (run `freshen secure-boot-cert-rotation` to re-probe and re-stamp).

| Source | Last verified | Note |
|---|---|---|
| Microsoft cert-rotation topic `7ff40d33…` | 2026-06-01 | exact dates + 2011→2023 cert map |
| Dell KB 000402373 (PowerEdge BIOS minimums) | 2026-06-01 | per-generation minimum BIOS — volatile |
| Red Hat 2026-02-04 RHEL guidance | 2026-06-01 | reinstall≠firmware, HP/Fujitsu block, NVRAM |
| fwupd `uefi-db`/`uefi-kek` plugins (rel 2.0.8) | 2026-06-01 | cert plugins need fwupd ≥ 2.0.8 |
| Ubuntu fwupd pockets (Launchpad / Snap) | 2026-06-01 | per-pocket versions — volatile |
| Harvester releases (`gh release list harvester/harvester`) | 2026-06-01 | v1.8.0 latest GA, v1.6.0 guest-OVMF floor |
| `microsoft/secureboot_objects` payloads | 2026-06-01 | `DBUpdate3P2023.bin` etc. |
| SUSE-RU-2026:1157-1 (node-OS OVMF backport) | 2026-06-01 | separate path, NOT the guest fix |

## The mechanism (dates, cert map, firmware-ignores-expiry)
- Microsoft — "Windows Secure Boot certificate expiration and CA updates" (support.microsoft.com topic
  7ff40d33…): authoritative cert names, KEK-vs-db placement, exact expiry dates, "continue to start and operate
  normally."
- Microsoft — "Secure Boot certificate updates: guidance for IT pros and organizations" (e2b43f9f…): the
  documented db→KEK deployment order. Registry-key updates (a7be69c9…); known issues 1795/1796 (5813673d…);
  "when certificates expire" (c83b6afd…).
- Canonical — Ubuntu Discourse "Microsoft UEFI CA rotation: what it means for Ubuntu users and vendors" (82652):
  "UEFI firmware does not check the expiry date of CAs"; per-release readiness; dual-sign plan.
- Red Hat — access.redhat.com/articles/7128933 and developers.redhat.com/articles/2026/02/04/secure-boot-
  certificate-changes-2026-guidance-rhel-environments: keeps-booting-after-2026, reinstall-doesn't-fix-firmware,
  NVRAM independence, HP/Fujitsu block, mokutil audit, edk2-ovmf package versions.
- fwupd/LVFS — fwupd.github.io/libfwupdplugin/uefi-db.html; plugins/uefi-db,uefi-kek,uefi-sbat READMEs; HSI
  `org.fwupd.hsi.Uefi.Db`; release 2.0.8 (added uefi-db/uefi-kek plugins); LVFS com.microsoft.db-uefi-3p.firmware.
- LWN — lwn.net/Articles/1029767/: maintainer commentary (Jones, Hoffmann, Hughes), EDK2 `NO_CHECK_TIME`,
  success rates, FUD-vs-reality framing.

## The signed payloads
- microsoft/secureboot_objects (GitHub) — PostSignedObjects/Optional/DB/amd64/{DBUpdate3P2023, DBUpdate2024,
  DBUpdateOROM2023}.bin (EFI_VARIABLE_AUTHENTICATION_2, signed by the 2011 KEK); PostSignedObjects/KEK/ is
  per-OEM (no generic 2023 KEK payload); PreSignedObjects/KEK/Certificates/microsoft corporation kek 2k ca
  2023.der (raw cert only).

## Dell PowerEdge / iDRAC9
- Dell KB 000402373 (PowerEdge BIOS update guidelines for MS Secure Boot certs — per-generation minimum BIOS
  versions, prerequisites, mandated reboot sequence); KB 000362511 (impact); KB 000390990 (Secure Boot
  Transition FAQ — per-CA dates, EoSL cutoff, Expert-Key-Mode warning).
- Dell iDRAC-Redfish-Scripting `SecureBootResetKeysREDFISH.py` (ResetKeys endpoint, Custom-policy prereq,
  staged-job + reboot semantics, allowable values); RACADM `bioscert` guide; `dellemc.openmanage.idrac_secure_boot`
  Ansible module. (Companion skill: `ansible-idrac-9-10` for the dellemc.openmanage auth lifecycle.)
- Broadcom/VMware KB 423893 (PK-before-KEK dependency). HPE iLO / Lenovo XCC — same firmware-update + Windows-
  Update split (OEM comparison).

## Ubuntu / Linux
- Launchpad `launchpad.net/ubuntu/+source/fwupd` and packages.ubuntu.com (per-series/pocket fwupd versions);
  Snap Store fwupd (api.snapcraft.io/v2/snaps/info/fwupd — channels, Canonical-maintained). Debian wiki
  SecureBoot (mokutil audit). Google Cloud "MS Secure Boot certificates update" (efi-updatevar / sbkeysync /
  immediate-NVRAM-write reference commands).

## Harvester / KubeVirt (guest OVMF floor = v1.6.0)
- `gh release list/view -R harvester/harvester` (GA dates) + per-release `harvester-images-list-amd64.txt`
  (pinned virt-launcher image); `docker run registry.suse.com/suse/sles/15.X/virt-launcher:<ver> rpm -q
  qemu-ovmf-x86_64`; **direct `openssl x509` parse of `ovmf-x86_64-smm-ms-vars.bin`** from each virt-launcher
  (1.6.0/1.7.x/1.8.0 = ovmf-202408, 2023 present; 1.5.2 = ovmf-202308, 2011-only) — the artifact-level proof.
- Harvester wiki Base-Operating-System (Harvester→SL Micro mapping); `github.com/harvester/harvester/issues/7343`
  (host ISO SBAT bug, install SB-off workaround); SUSE support matrix (1.5.x EOM 2025-12-30 / EOL 2026-12-30);
  suse.com/c/uefi-secure-boot-details/ (SUSE shim chain).
- KubeVirt source (pinned tags) — `pkg/storage/backend-storage/backend-storage.go` (`persistent-state-for`
  PVC prefix, `HasPersistentEFI`), `pkg/util/util.go` (`PathForNVram`), `staging/.../v1/schema.go` (EFI
  SecureBoot "defaults true" / Persistent "defaults false"); KubeVirt docs persistent_tpm_and_uefi_state.
  harvester-ui-extension `index.js` (UI defaults secureBoot/efiPersistent = false).
- virt-fw-vars man page (`--microsoft-kek {none,2011,2023,all}`, `--microsoft-db`).
- SUSE node-OS OVMF backport (separate path, NOT the guest fix) — OBS `SUSE:SLE-15-SP5:Update/ovmf/*`;
  advisory SUSE-RU-2026:1157-1 (SLE Micro 5.5, `qemu-ovmf-x86_64-202208-150500.6.15.1`, bsc#1257019).

## Full research provenance
- The deep-research report this skill was distilled from:
  `~/.claude/skills/autoresearch/results/secure-boot-2026-cert-expiry-2026-06-01.md` (autoresearch Research
  mode, 2 levels, with the two operator corrections that pinned the SUSE backport and the Harvester v1.6.0 floor).
