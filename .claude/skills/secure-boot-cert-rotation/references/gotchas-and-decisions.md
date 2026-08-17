# Gotchas, order of operations, and the do-nothing decision

## Order of operations

1. **Ensure PK present → (KEK) → db.** A `db`-2023 enrollment is authorized by the **existing 2011 KEK**, so
   **db-first works without the 2023 KEK** — this is the whole fwupd-free path. The 2023 KEK only matters for
   *future* 2023-KEK-signed db/dbx. A **KEK update from inside a guest fails without a valid PK** (the
   VMware/Broadcom failure mode — payloads that update KEK always fail if the OEM-Devices PK is missing).
2. **Never push a 2023-only-signed bootloader before `db` has the 2023 CA.** The canonical out-of-order trap:
   updating WDS/PXE to serve 2023-signed boot files before clients trust the 2023 CA → every deploy fails.
   Dual-signed shim (2011 + 2023) is what makes the OS side forgiving during the transition.

## Failure modes (usually recoverable — but not always; pilot before fleet)

- **Forced updates are not safe on all hardware — the one non-recoverable case.** Post-expiry retrospective
  (LWN 2026-07-01, by a Microsoft author): *"Forced updates have left some machines unbootable. On certain
  hardware, recovery requires physical access, and in some cases we have observed that systems were
  permanently damaged."* Microsoft now publishes **"High Confidence Buckets"** in `microsoft/secureboot_objects`
  — telemetry-derived device configurations where the 2023 db update is confirmed to apply safely. Check fleet
  hardware against it before any force-push, and prefer the vendor firmware path over forcing a db write.

- **HP & Fujitsu block standalone db updates** (observed post-update boot failures) → use a **full firmware
  update** on those, not a standalone db push. Red Hat: *"Do not force install db updates. Always follow vendor
  guidance."*
- **NVRAM exhaustion** → `failed to write efivarfs`. Fix: reboot + BIOS "restore Secure Boot keys to factory
  defaults" to defragment EFI variable space. Pre-check free space before any write on old firmware.
- **Real 2026 incidents:** a wave of *update-application* failures (Event IDs **1795** "media is write
  protected" / **1796**) hit Jan–Mar 2026, prominently on **Hyper-V VMs during the KEK step** and on buggy
  firmware. Microsoft shipped fixes 2026-03-10 (Server 2025: 2026-04-14). These were **failed enrollments, not
  mass bricking** — devices kept running. fwupd's measured rates: ~98% KEK / ~99% db success — small but
  non-zero absolute failures at fleet scale.
- **Dual-boot / FDE:** a db change can re-seal TPM PCR7 → BitLocker recovery prompt / Linux FDE re-enroll.
  Suspend BitLocker before the write.
- **"Long uptime" is a red herring for staleness on Linux** (db/KEK live in NVRAM, written live, independent of
  OS reboot) — **except on Dell**, where a BIOS-staged key set genuinely needs a reboot to apply.

## The do-nothing risk timeline (what to tell a worried operator)

- **The deadline: settled, not predicted.** Two of the three 2011 CAs have now expired — KEK CA 2011 on
  **2026-06-24**, UEFI CA 2011 on **2026-06-27** — and **nothing happened**. No fleet incident, no boot
  failures attributable to expiry; the post-expiry retrospective (LWN 2026-07-01) confirms it outright. Use
  this as observed fact when reassuring an operator, not as a forecast. **Windows Production PCA 2011 expires
  2026-10-19** and there is no reason to expect it to behave differently. What *has* hurt people is the
  remediation (see Failure modes above), not the expiry.
- **The real trigger to watch is not a date.** Per the same retrospective, the event that actually bites is
  **the next CVE-driven shim respin** — the first security update that forces a distro to ship a 2023-only
  signed shim. That is unscheduled and could land any month, which is exactly why this is worth doing on a
  calm calendar rather than under an advisory. It has already happened on **aarch64** (`mechanism.md`).
- **Forward-compat, when it comes:** new install/PXE media and post-cutover bootloader updates signed only
  with 2023 keys; a `db` lacking the 2023 CA can't validate them. On Linux this stalls the boot-stack update
  chain ("can't install updates"); installers fail rather than producing an unbootable machine.
- **Revocation freeze: not yet in effect.** Microsoft is still signing `dbx` with the **2011** KEK (verified by
  parsing the June 2026 payload — `mechanism.md`), so machines lacking the 2023 KEK are not currently missing
  revocations. The freeze starts at the un-announced dbx signing cutover. On Linux it is softened anyway by
  SBAT (self-healing).

So: **low immediate risk, real *compounding* risk.** It's a scheduled hygiene task, not a fire drill. The
dominant practitioner framing: "real but probably won't hurt you — do it before the forward-compat and
revocation costs compound."

## The disable-Secure-Boot stopgap

Every vendor says don't disable it as a workaround (removes anti-bootkit protection, can break
BitLocker/compliance). But the calculus is bimodal:
- **Laptops/endpoints = regression.** Secure Boot gates BitLocker/device hardening; disabling exposes a
  lost/stolen disk. Don't.
- **Datacenter servers behind physical security = much weaker case for keeping it.** The bootkit threat model
  assumes physical/pre-OS access, which a locked rack largely removes. "Disable and revisit" is a defensible,
  time-boxed decision *for servers* in a way it isn't for fleet laptops.
- **Dell caveat:** on "Expert Key Mode" devices, toggling Secure Boot off can wipe active UEFI variables and
  revert a completed 2023 migration back to 2011 defaults. So "just disable it" can itself undo the fix.

## OEM-abandonment (the one no patch fixes)

The whole chain needs an OEM firmware update to seat a new PK/KEK. Devices past EoSL, never-updated appliances,
and pre-14G Dell may have **no path to the 2023 db at all** — for these, manual db enrollment (physical access)
or accepting the frozen-posture risk are the only options.
