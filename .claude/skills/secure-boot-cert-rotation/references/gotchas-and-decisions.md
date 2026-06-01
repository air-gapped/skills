# Gotchas, order of operations, and the do-nothing decision

## Order of operations

1. **Ensure PK present → (KEK) → db.** A `db`-2023 enrollment is authorized by the **existing 2011 KEK**, so
   **db-first works without the 2023 KEK** — this is the whole fwupd-free path. The 2023 KEK only matters for
   *future* 2023-KEK-signed db/dbx. A **KEK update from inside a guest fails without a valid PK** (the
   VMware/Broadcom failure mode — payloads that update KEK always fail if the OEM-Devices PK is missing).
2. **Never push a 2023-only-signed bootloader before `db` has the 2023 CA.** The canonical out-of-order trap:
   updating WDS/PXE to serve 2023-signed boot files before clients trust the 2023 CA → every deploy fails.
   Dual-signed shim (2011 + 2023) is what makes the OS side forgiving during the transition.

## Failure modes (recoverable, but real — pilot before fleet)

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

- **Immediate (the deadline):** nothing. No reboot, no error — firmware ignores expiry; machines boot and patch
  normally. The expiry is invisible to running systems.
- **Months later:** the realistic break is *forward-compat* — new install/PXE media and post-cutover bootloader
  updates are signed only with 2023 keys; a `db` lacking the 2023 CA can't validate them. On Linux this stalls
  the boot-stack update chain ("can't install updates"); installers fail rather than producing an unbootable
  machine.
- **Ongoing:** dbx/revocation freeze — a machine on the expired 2011 KEK can't receive new revocations; known
  bootkits stay trusted. On Linux this is softened by SBAT (self-healing).

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
