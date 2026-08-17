---
name: secure-boot-cert-rotation
description: >-
  Triage and fix the Microsoft Secure Boot 2011→2023 UEFI certificate rotation across Dell PowerEdge / iDRAC9
  bare metal, Ubuntu/Linux servers, and Harvester HCI / KubeVirt guest VMs. Two 2011 CAs expired June 2026 and
  Windows Production PCA 2011 expires 2026-10-19 — but UEFI firmware ignores certificate expiry, so nothing
  stopped booting; the real risks are forward-compat once a 2023-only-signed shim arrives (already true on
  aarch64) plus a dbx/revocation freeze. Routes to the per-platform fix: iDRAC BIOS-staged keys applied on
  reboot (Dell), fwupd-free manual `db` append self-authenticating via the existing 2011 KEK (Linux), and the
  Harvester virt-launcher OVMF floor (v1.6.0) with ephemeral-vs-persistent NVRAM triage (VMs). Covers the
  PK→KEK→db trust chain, the missing generic 2023 KEK payload, backup/rollback, and audit via mokutil /
  efi-readvar / racadm bioscert / Redfish.
when_to_use: >-
  Use whenever secure boot certificate expiry, KEK/db/dbx updates, KEK CA 2011, Microsoft UEFI CA 2011/2023,
  "did the June 2026 expiry break anything", or "will our servers still boot" come up. Also on symptom-only
  prompts that don't name the rotation: a kernel/shim update that won't boot, "Secure
  Boot Violation" / "Invalid signature" at boot, "fwupdmgr does nothing on our servers", mokutil / efi-updatevar,
  Dell PowerEdge secure boot BIOS, Harvester VM secure boot, OVMF varstore, virt-fw-vars, or "should we
  reinstall to fix secure boot". NOT for MOK enrollment of self-signed kernel modules or generic GRUB/UEFI repair.
---

# secure-boot-cert-rotation

Triage and fix the **Microsoft Secure Boot 2011→2023 certificate rotation** on a real, mixed fleet.
Microsoft's original 2011 Secure Boot CAs expire in 2026; their 2023 replacements take over. This skill
exists to stop the two failure modes operators actually hit: (1) **panic** — believing servers will stop
booting on the expiry date (they won't), and (2) **applying the wrong tool** — reaching for `fwupd`/LVFS on
hardware and VMs it cannot serve, instead of the firmware-native path.

The work is almost never the cert write itself — it's **knowing which of three firmware surfaces a given
machine has** (Dell host firmware, generic Linux host firmware, or a VM's virtual OVMF varstore), because each
is updated by a different mechanism and `fwupd` only covers one of them.

## The one load-bearing fact — read this before anything else

**UEFI firmware does not check a certificate's expiry date when validating Secure Boot signatures.** EDK2 sets
`NO_CHECK_TIME` on PKCS#7 verification on purpose (there is no trustworthy clock at boot; enforcing `notAfter`
would be a self-inflicted brick vector). Canonical, Red Hat, fwupd, and LWN all state this independently.

Consequences, and the entire reason this is a *hygiene* task and not a *fire*:

- **Every machine that boots today keeps booting after the expiry dates.** Nothing breaks on the deadline —
  and this is now **observed, not predicted**: the **2011 KEK CA expired 2026-06-24 and the 2011 UEFI CA on
  2026-06-27**, with no resulting fleet incident (LWN retrospective, 2026-07-01). **Windows Production PCA
  2011 expires 2026-10-19** and is expected to pass the same way. Say this plainly to a worried operator.
- The **real** risks are forward-looking:
  1. **Forward-compat** — once a distro ships a shim/bootloader signed *only* by the **Microsoft UEFI CA 2023**,
     a machine whose firmware `db` lacks that 2023 cert can't validate the new binary. On Linux this surfaces
     as "package-management failures / can't install updates"; on new installs/PXE as a failed deploy.
  2. **Revocation freeze** — a machine stuck on the expired **2011 KEK** can't receive new `dbx` revocations, so
     known-vulnerable bootloaders stay trusted. (Lower on Linux, which revokes via **SBAT**, not `dbx`.)
- **So the fix everywhere is: get the Microsoft 2023 `db` cert into the firmware/varstore** (and the 2023 KEK
  where the platform offers a path). Mechanism + dates + the 2011→2023 map: `references/mechanism.md`.

## Routing — pick the surface, then the reference

A machine has exactly one of three firmware surfaces. Identify it first; everything else follows.

| Surface | Who has it | Cleanest fix | Reference |
|---|---|---|---|
| **Dell PowerEdge host firmware** | Any Dell bare-metal node (incl. Linux servers and Harvester *hosts* on Dell) | Recent BIOS already carries 2023 keys, **staged → applied on a controlled reboot** (Lifecycle Controller pass). Audit + reboot; `ResetAllKeysToDefault` via Redfish on a new-enough BIOS; Ansible for the fleet. | `references/dell-poweredge.md` |
| **Generic Linux host firmware** | Non-Dell bare metal, or OS-side enrollment on any host | Manual `db` append of Microsoft's signed 2023 payload — **no fwupd, no Setup Mode** (it self-auths via the 2011 KEK). | `references/linux-bare-metal.md` |
| **VM virtual OVMF varstore** | Harvester / KubeVirt (and any QEMU/OVMF) guest VMs | iDRAC does **not** touch this. Governed by the **Harvester version → virt-launcher → OVMF** (floor **v1.6.0**); then ephemeral-vs-persistent-NVRAM triage. | `references/harvester-vms.md` |

`fwupd`/LVFS is the desktop/laptop path. It is the **wrong tool** for Dell PowerEdge (firmware ships via
iDRAC/DSU, not LVFS) and for VMs (no capsule path) — a **coverage** limit, not a version one. The old "stock
Ubuntu fwupd is too old" caveat has **expired**: jammy and noble `-updates` both carry **fwupd 2.0.20** as of
2026-07-09, past the **≥ 2.0.8** floor the `uefi-db`/`uefi-kek` cert plugins need, so a plain `apt upgrade` now
clears it. If `fwupdmgr` still "does nothing" on a server, that is expected — it means no LVFS/capsule path for
that hardware, so use the firmware-native path. Details in each platform reference.

## Workflow

### 1. Audit before you touch anything (read-only)

Always start by reading what's actually enrolled — the fix and its urgency depend on it. Verdict: *NEEDS
UPDATE* if `db` has the 2011 Microsoft UEFI CA but not `Microsoft UEFI CA 2023`; *GOOD* if the 2023 certs are
present.

```bash
# Linux host or in-guest:
sudo mokutil --sb-state                                              # Secure Boot on?
sudo mokutil --kek | grep -i "KEK 2K CA 2023"                       # 2023 KEK present?
sudo mokutil --db  | grep -iE "Microsoft UEFI CA 2023|Windows UEFI CA 2023"
sudo efi-readvar -v db | grep -i 2023                               # efitools alternative
```
Dell out-of-band: `racadm ... bioscert view --all` or Redfish `GET /redfish/v1/Systems/System.Embedded.1/SecureBoot/SecureBootDatabases`.
Harvester VMs: first find which VMs even *use* Secure Boot (`kubectl ... efi.secureBoot`) — many don't, and
those are moot. Exact commands per reference.

**Capture a rollback point before the first write** — on Dell an `export_certificates` dump, on a persistent-
NVRAM VM a backend-storage snapshot. On an OEM-keyed Linux host an `efi-readvar` dump is evidence but *not* a
replayable restore; the real undo there is the firmware's factory-keys option. `gotchas-and-decisions.md` § Recovery.

### 2. Establish the surface and route (table above), then apply that reference's runbook

Each reference is self-contained: audit → cleanest fix → fallback → verify.

### 3. Verify after, on a sample, before fleet rollout

Re-run the §1 audit. **Test one host per model+firmware (or one VM per template) before the fleet** — failure
modes cluster by firmware version (HP/Fujitsu block standalone db updates; old BIOSes exhaust NVRAM). Cross-
cutting gotchas, ordering, and the do-nothing risk timeline: `references/gotchas-and-decisions.md`.

## House rules (the hard-won ones — encode these into every answer)

1. **Don't fearmonger.** Lead with "nothing stops booting on the deadline." Expiry ≠ revocation; firmware
   ignores `notAfter`. The honest framing is forward-compat + revocation-freeze on a slow fuse, not a brick
   event. Getting this wrong sends operators into needless emergency reinstalls.
2. **`db`-first works without the 2023 KEK.** The Microsoft 2023 `db` payloads are signed by the *old 2011 KEK*
   that every machine already has, so they self-authenticate and append with `efi-updatevar -a`/`sbkeysync` —
   no fwupd, no Setup Mode. There is **no generic Microsoft-signed 2023 KEK payload** (KEK updates are per-OEM,
   PK-signed); the 2023 KEK arrives via OEM BIOS (Dell), Windows servicing, fwupd's per-hardware LVFS KEK, or
   `virt-fw-vars` for VMs. Prioritize the db cert — it is what boots future 2023-signed bootloaders.
3. **Reinstalling the OS does NOT fix firmware.** `db`/`KEK` live in firmware NVRAM (or a VM's varstore),
   independent of the OS. A 26.04 reinstall only ships a 2023-aware shim/grub — the cert still needs enrolling.
   Decouple "patch in place vs reinstall" from "fix the certs". `references/linux-bare-metal.md` § Reinstall.
4. **Verify version claims against the REAL artifact, never upstream commit dates.** "Does package/image X carry
   the 2023 certs?" is answered by reading the *published* artifact — distro changelog/advisory, or the bytes of
   the actual varstore/ISO/RPM — because distros **backport** certs onto old bases (Red Hat and SUSE both did).
   Inferring from an upstream edk2 tag date gives a confidently-wrong answer. (This is exactly how the Harvester
   floor was pinned to **v1.6.0** by `openssl`-parsing the varstore in each release's `virt-launcher`, not by
   the Oct-2025 upstream commit.) `references/harvester-vms.md` shows the proof method.
5. **Ground volatile numbers; don't assert from memory.** Dell per-generation BIOS minimums, Ubuntu fwupd
   pocket versions, and Harvester release dates change. State a specific version only if it's machine-reported,
   freshly grounded (Dell KB / Launchpad / `gh release`), or marked UNVERIFIED. The methodology (mechanism,
   trust chain, surfaces) is what this skill asserts; the leaf numbers are grounded per use.
6. **Right tool per surface.** Don't recommend `fwupd` for Dell PowerEdge or VMs, and don't recommend `rpm -q`
   on a Harvester *node* to check guest OVMF (it isn't there — guest OVMF ships in the `virt-launcher`
   container). Match the mechanism to the firmware surface (routing table).
7. **Audit → sample → fleet.** Read what's enrolled before acting; pilot one host/VM per model+firmware before
   rolling out. The usual worst case is transient, recoverable unbootability — but *forced* trust-DB updates
   are not safe on all firmware: some machines have needed physical recovery and a few were **permanently
   damaged** (LWN, 2026-07-01, authored from Microsoft). That is what makes the pilot non-optional, and why
   "force it fleet-wide" is never the answer. Note this is a risk of the *update*, not of the expiry.

## References

- `references/mechanism.md` — what expires + exact dates, the 2011→2023 cert map (KEK vs db), why firmware
  ignores expiry, the PK→KEK→db trust chain, the no-generic-2023-KEK fact, SBAT-vs-dbx on Linux.
- `references/dell-poweredge.md` — iDRAC9 path: per-generation BIOS minimums, staged-until-reboot mechanism,
  `ResetAllKeysToDefault` via Redfish/racadm, `bioscert` audit, the `dellemc.openmanage` Ansible module.
- `references/linux-bare-metal.md` — audit commands, the fwupd-free manual `db` append (Microsoft signed-payload
  filenames + URLs), firmware-menu (Key Management) enrollment from raw `PreSignedObjects/*.der` + the ESP
  staging trick (`/boot/efi`, no USB/virtual-media), the fwupd-snap fallback + Ubuntu pocket reality, the
  patch-vs-reinstall decision.
- `references/harvester-vms.md` — the two layers (Dell host vs guest OVMF), guest OVMF ships in `virt-launcher`
  (floor **v1.6.0**, per-line table, the artifact-proof method), host Secure Boot + bug #7343, the
  ephemeral-vs-persistent NVRAM triage with exact `kubectl` commands, `virt-fw-vars` injection.
- `references/gotchas-and-decisions.md` — order of operations (PK→KEK→db), HP/Fujitsu standalone-db block,
  NVRAM exhaustion, BitLocker/PCR7 reseal, **the backup + recovery ladder for an enrollment that went wrong**,
  the do-nothing risk timeline, the disable-Secure-Boot tradeoff.
- `references/sources.md` — primary sources (Microsoft, Dell, Red Hat, Canonical, fwupd/LVFS, SUSE/Harvester,
  KubeVirt) with one-line credibility notes.
