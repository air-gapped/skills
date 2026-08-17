# Mechanism: what expires, the 2011→2023 map, and the trust chain

## Exact expiry dates (staggered — not one cliff)

Three Microsoft 2011 CAs expire; the 2023 replacements are valid to **2038**.

| 2011 cert (expiring) | UEFI store | Signs | Expiry | → 2023 replacement(s) |
|---|---|---|---|---|
| **Microsoft Corporation KEK CA 2011** | **KEK** | Updates to `db`/`dbx` | **2026-06-24** | **Microsoft Corporation KEK 2K CA 2023** (KEK) |
| **Microsoft Corporation UEFI CA 2011** (the "third-party CA") | **db** | Linux **shim**, 3rd-party bootloaders **and** option ROMs | **2026-06-27** | split into **Microsoft UEFI CA 2023** (bootloaders/shim) **+ Microsoft Option ROM UEFI CA 2023** (db) |
| **Microsoft Windows Production PCA 2011** | **db** | Windows boot manager | **2026-10-19** | **Windows UEFI CA 2023** (db) |

For **Linux**, the cert that matters most is the shim signer: **Microsoft UEFI CA 2011 → Microsoft UEFI CA
2023**. The single 2011 third-party CA is deliberately **split into two** 2023 certs so that trusting option
ROMs no longer forces trusting third-party OS bootloaders.

## The one load-bearing fact: firmware ignores expiry

UEFI firmware does **not** check a certificate's `notAfter` date when validating Secure Boot signatures. EDK2
sets `NO_CHECK_TIME` on PKCS#7 verification because there is no trustworthy clock at boot (the RTC drifts and
is attacker-controllable; enforcing expiry would be a self-inflicted brick/DoS vector and would break option
ROMs). Stated independently by Canonical ("UEFI firmware does not check the expiry date of CAs when validating
signatures"), Red Hat ("expiration only impacts the ability to sign new binaries, not booting from existing
ones"), fwupd ("will not stop booting"), and LWN.

**Therefore: expiry ≠ revocation.** An already-signed, already-trusted binary keeps validating forever. Only
*signing new binaries* moves to the 2023 certs. The "machines won't boot in June 2026" headline is FUD for
running systems.

## What actually breaks (slow fuse, two failure modes)

1. **Forward-compat.** When a distro cuts over to shipping shim/bootloaders signed *only* by the Microsoft UEFI
   CA 2023, a firmware `db` lacking that 2023 cert can't validate the new binary. On Linux: "package-management
   failures / inability to install updates" once the boot-stack update chain stalls. New installs/PXE on such
   firmware also fail. Distros mitigate by shipping **dual-signed** shim (2011 **and** 2023) until cutover.

   **Where the cutover actually stands (verified 2026-08-18):**

   | Distro | Shim status | Evidence |
   |---|---|---|
   | **RHEL 8 / 9 / 10, x86_64** | **dual-signed, shipped 2026-06-10** — `shim-x64` 16.1-2 / 16.1-7 / 16.1-4 | access.redhat.com/articles/7128933 (upd. 2026-07-10) |
   | **RHEL 9.7 / 10.0, aarch64** | ⚠️ **2023-ONLY signed** — the cliff, already here | AlmaLinux wiki (states same holds for RHEL) |
   | **SUSE SLES 15 SP6** | shim **16.1** shipped 2026-06-16 (same upstream release RHEL dual-signs; advisory does not say "dual-signed" verbatim) | SUSE-SU-2026:0741 |
   | **Ubuntu (all LTS)** | **no new shim at all** — archive `shim-signed` is still `1.59+15.8-0ubuntu2` (2024-10-02) | archive.ubuntu.com pool listing |

   Two consequences. **(a) The cliff is real and has already landed on aarch64** — an ARM RHEL/AlmaLinux host
   whose `db` lacks the 2023 CA cannot validate its current shim. On **x86_64 no distro has dropped the 2011
   signature yet**, and none has published a date. **(b) Canonical took a different route**: rather than a new
   shim, it pushed the **2023 certs themselves via fwupd** in June 2026 (rollout 06-08, paused 06-11 for MTD
   LP#2156479 and BitLocker/TPM-FDE dual-boot LP#2156480, completed 06-23), pre-staging firmware trust so a
   future shim update won't strand systems. Ubuntu 26.04 point releases and new cloud images are stated to
   require the 2023 CA *later* — planned, not shipped.
2. **Revocation freeze — real, but *not yet started* (verified 2026-08-18).** The eventual risk: no valid 2023
   KEK → the machine can never enroll new `dbx` entries, so known-vulnerable bootloaders stay trusted. But
   Microsoft is **still signing dbx with the 2011 KEK**, so machines that never got the 2023 KEK are *not*
   currently missing revocations. Proof (House Rule #4 — parse the artifact, don't infer): the June 2026 dbx
   push — `PostSignedObjects/DBX/amd64/DBXUpdate.bin`, commit `a728996` (2026-06-09), 12 new x64 hashes,
   bootmgfw SVN → v9, **CVE-2026-45654** — parses as a PKCS#7 `EFI_VARIABLE_AUTHENTICATION_2` blob whose
   SignerInfo is `CN=Microsoft Windows UEFI Key Exchange Key`, **issuer `CN=Microsoft Corporation KEK CA 2011`**.
   No cert chaining to `KEK 2K CA 2023` appears in it. The freeze begins only when Microsoft cuts dbx signing
   over to the 2023 KEK — **no cutover date is published**, so treat this as the trigger to watch, not a
   present-day gap. On **Linux** the risk is lower regardless: revocation rides **SBAT** (generation-number,
   self-healing in shim), not `dbx`. The 2023 cert transition does **not** change dbx/SBAT handling — it's an
   orthogonal axis (trust/expiry of signing CAs, not revocation).

## The PK → KEK → db trust chain (why the fix needs no fwupd and no new KEK)

- A **db** (or dbx) update must be signed by something already in the **KEK**.
- A **KEK** update must be signed by the **PK** (the OEM platform key).

**The key enabler (verified by byte-parsing the actual payloads):** Microsoft's pre-signed 2023 **db** updates
are signed by the **old 2011 KEK**, not the 2023 KEK. They are `EFI_VARIABLE_AUTHENTICATION_2` (time-based
authenticated PKCS#7) blobs. So they **self-authenticate against the 2011 KEK every machine already has**,
append with a plain `efi-updatevar -a` / `sbkeysync`, and need **no Setup Mode and no 2023 KEK first**. fwupd
maintainer, confirming: "it's actually signed by the old KEK… now it can apply on many more systems."

**The catch — no generic Microsoft 2023 KEK payload.** In `microsoft/secureboot_objects`, `PostSignedObjects/
KEK/` is organized **per-OEM**: each `KEKUpdate_<OEM>_PK*.bin` is signed by *that vendor's PK* and only enrolls
on that vendor's firmware. The 2023 KEK ships only as a **raw cert**. So the 2023 KEK arrives via: (a) OEM BIOS
update (Dell), (b) Windows Update servicing, (c) fwupd's per-hardware LVFS KEK update, or (d) self-sign with
your own PK in Setup Mode. For VMs, `virt-fw-vars` injects it offline (acting as the platform owner).

**Practical consequence:** the **db cert** (what you need to *boot* future 2023-signed bootloaders) is trivially
enrollable everywhere, fwupd-free. The **2023 KEK** (what you need to keep *receiving* future db/dbx updates) is
the OEM/firmware-dependent part — prioritize db first; do KEK where the platform gives you a path.

## Deployment ordering (Microsoft's documented sequence)

Microsoft applies, in order: Windows UEFI CA 2023 → db; Microsoft UEFI CA 2023 + Option ROM 2023 → db; then
the KEK 2K CA 2023 → KEK **last**. This confirms the existing 2011 KEK authorizes the first round of 2023 db
certs; the 2023 KEK is only needed to authorize *future* db/dbx payloads signed by the 2023 KEK after the 2011
KEK is retired. Never push a 2023-only-signed bootloader before `db` has the 2023 CA (the canonical out-of-order
trap — see `gotchas-and-decisions.md`).
