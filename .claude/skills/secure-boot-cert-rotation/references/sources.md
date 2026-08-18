# Sources (primary / high-credibility)

Freshened: 2026-08-18

Grounded 2026-06-01; re-probed 2026-08-18 (first freshen, ~8 weeks after the June expiries). Re-verify volatile
leaf numbers (Dell BIOS minimums, Ubuntu fwupd pockets, Harvester release dates / virt-launcher OVMF) against
these at use time — methodology is durable, version numbers are not.

- [Freshness ledger](#freshness-ledger)
- [The mechanism](#the-mechanism-dates-cert-map-firmware-ignores-expiry)
- [Post-expiry distro status](#post-expiry-distro-status-checked-2026-08-18)
- [The signed payloads](#the-signed-payloads)
- [Dell PowerEdge / iDRAC9](#dell-poweredge-idrac9)
- [Ubuntu / Linux](#ubuntu-linux)
- [Harvester / KubeVirt](#harvester-kubevirt-guest-ovmf-floor-v160)
- [Recovery / rollback](#recovery-rollback-the-backup-and-back-out-path)
- [Full research provenance](#full-research-provenance)

## Freshness ledger

Per-source verification dates (run `freshen secure-boot-cert-rotation` to re-probe and re-stamp).

| Source | Last verified | Note |
|---|---|---|
| Microsoft cert-rotation topic `7ff40d33…` | 2026-08-18 | all three expiry dates unchanged; page last edited 2026-05-18 |
| Microsoft IT-pro guidance `e2b43f9f…` | 2026-08-18 | db→KEK deployment order unchanged |
| Microsoft known issues `5813673d…` | 2026-08-18 | Hyper-V 1795 resolved; Azure Trusted Launch 1795 still open |
| Microsoft DB/DBX update events `37e47cf8…` | 2026-08-18 | **the** source for event IDs 1795/1796 (not the known-issues page) |
| Microsoft registry-key article `a7be69c9…` | 2026-08-18 | still opt-in (`MicrosoftUpdateManagedOptIn`); not mandatory |
| LWN 1079808 — post-expiry retrospective | 2026-08-18 | expiry passed cleanly; forced updates damaged some machines |
| Dell KB 000402373 (PowerEdge BIOS minimums) | ⚠️ 2026-06-01 | **not re-verified** — Dell blocks automated reads; page modified 2026-06-23. Read manually |
| Dell KB 000390990 (Transition FAQ) | 2026-08-18 | EoSL cutoff confirmed: EoSL before 2026-01-01 = no BIOS remediation |
| Red Hat 2026-02-04 RHEL guidance + article 7128933 | 2026-08-18 | dual-signed shim shipped 2026-06-10 (8/9/10, x86_64) |
| AlmaLinux Secure Boot 2023 wiki | 2026-08-18 | aarch64 shim is **2023-only** signed (states same for RHEL) |
| Ubuntu Discourse 82652 + archive `shim-signed` pool | 2026-08-18 | no new shim; certs delivered via fwupd instead |
| fwupd releases (`uefi-db`/`uefi-kek`) | 2026-08-18 | floor still ≥ 2.0.8; latest 2.1.7; snap ≥ 2.1.6 for KEK |
| Ubuntu fwupd pockets (Launchpad / Snap) | 2026-08-18 | **2.0.20 now in jammy/noble `-updates`** — floor cleared by apt |
| Harvester releases (`gh release list harvester/harvester`) | 2026-08-18 | v1.8.2 latest GA (2026-08-06); v1.6.0 guest-OVMF floor unchanged |
| harvester#7343 (installer SBAT) | 2026-08-18 | fixed in v1.8.0 GA; close is a real QA verification, not stale-bot |
| `microsoft/secureboot_objects` payloads | 2026-08-18 | three DB payloads unchanged; KEK still per-OEM; rel v1.6.5 |
| `secureboot_objects` DBX payload signer | 2026-08-18 | June 2026 dbx signed under **2011** KEK — freeze not yet started |
| SUSE-RU-2026:1157-1 (node-OS OVMF backport) | 2026-08-18 | still current; separate path, NOT the guest fix |
| SUSE-SU-2026:0741 (shim 16.1) | 2026-08-18 | 2026-06-16, SLES 15 SP6; advisory does not say "dual-signed" |
| KubeVirt persistent TPM/UEFI state docs | 2026-08-18 | no documented varstore reset-to-template path exists |
| `virt-firmware` (virt-fw-vars) | 2026-08-18 | PyPI 26.8.1 (2026-08-17); `--microsoft-kek/-db` flags unchanged |

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
- LWN — lwn.net/Articles/1079808/ **"Secure Boot certificate expiration is here"** (2026-07-01, Brian
  Exelbierd/Microsoft): the post-expiry retrospective. Confirms nothing stopped booting, *and* is the source
  for the forced-update damage warning ("recovery requires physical access… systems were permanently
  damaged") and the reframing of the real trigger as the next CVE-driven shim respin.
- Microsoft — "Secure Boot DB and DBX variable update events" (`37e47cf8…`): verbatim definitions of event IDs
  **1795** and **1796**. These are *not* on the known-issues page — cite this article for them.

## Post-expiry distro status (checked 2026-08-18)
- Red Hat — access.redhat.com/articles/7128933 (upd. 2026-07-10): dual-signed shim shipped **2026-06-10** for
  RHEL 8/9/10 **x86_64** (`shim-x64` 16.1-2 / 16.1-7 / 16.1-4).
- AlmaLinux — wiki.almalinux.org/documentation/secure-boot-2023-certificates: **aarch64 shim is 2023-only
  signed** on 9.7/10.0, and states the same holds for RHEL. The one architecture where the cliff has landed.
- SUSE — SUSE-SU-2026:0741 (2026-06-16): shim 16.1 for SLES 15 SP6 LTSS. Same upstream release RHEL
  dual-signs, but the advisory text does not use the word "dual-signed" — do not assert it.
- Canonical — discourse.ubuntu.com topic 82652 + archive.ubuntu.com `pool/main/s/shim-signed/`: **no new shim
  build** (still `1.59+15.8-0ubuntu2`, 2024-10-02). Canonical shipped the **2023 certs via fwupd** instead
  (06-08 rollout, 06-11 pause for LP#2156479 MTD / LP#2156480 BitLocker-TPM-FDE, 06-23 complete).
- Microsoft — **"High Confidence Buckets"** in `microsoft/secureboot_objects`: telemetry-derived device
  configurations where the 2023 db update is confirmed safe. Check hardware against it before any force-push.

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

## Recovery / rollback (the backup-and-back-out path)
- `dellemc.openmanage.idrac_secure_boot` module docs — `export_certificates` (PK/KEK/db/dbx dump to a
  directory) and `import_certificates`; the citable PowerEdge backup path. `reset_keys` is the only action
  supported on iDRAC8; export/import needs iDRAC9+.
- `efi-updatevar(1)` / `efi-readvar(1)` man pages — the `.esl` dump, and the rule that a write must be signed
  by the next-higher key (db needs KEK, KEK needs PK), which is why an OEM-keyed dump is not replayable.
- KubeVirt — kubevirt.io/user-guide/compute/persistent_tpm_and_uefi_state/: persistence is opt-in, and
  snapshot-restore-into-the-same-VM is the **only** documented restore. No reset-to-template path is
  documented — do not invent one (PVC deletion is not supported guidance).
- Dell — Lifecycle Controller firmware-rollback docs, and KB 000115696 (corrupt/interrupted BIOS flash
  recovery — a *different* path from key rollback). Whether a BIOS rollback reverts key databases is
  **undocumented**; the skill says so rather than guessing.

## Full research provenance
- The deep-research report this skill was distilled from:
  `~/.claude/skills/autoresearch/results/secure-boot-2026-cert-expiry-2026-06-01.md` (autoresearch Research
  mode, 2 levels, with the two operator corrections that pinned the SUSE backport and the Harvester v1.6.0 floor).
