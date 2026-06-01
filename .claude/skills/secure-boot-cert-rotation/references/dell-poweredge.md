# Dell PowerEdge / iDRAC9 — the fix is a controlled reboot

Dell delivers the Microsoft 2023 KEK + db certs **inside the regular BIOS DUP** at/above a per-generation
minimum (Dell KB 000402373). PowerEdge firmware is managed through **iDRAC / Lifecycle Controller / DSU /
OpenManage** — **not LVFS**, which is why `fwupd` has nothing to offer these nodes.

> Ground the per-generation BIOS minimum against **Dell KB 000402373** at use time (numbers below are a
> starting reference, not gospel — Dell revises them). 17G ships with the 2023 certs pre-installed.

| Gen | Example models | Min BIOS carrying 2023 certs (verify in KB 000402373) |
|---|---|---|
| 14G | R740/R640/R840/R940/T640/R540/R440 | `2.25.0` |
| 14G | R750/R650/R550/R450 | `1.19.2` · R350/R250 → `1.13.0` · R340/R240 → `2.21.0` |
| 15G | R6515/R7515/R6525/R7525 | `2.22.0` |
| 16G | R660/R760/R860 family | `2.8.2` · R260/R360/T160/T360 → `2.4.0` |
| 17G | all | ships with 2023 certs pre-installed |

## The staged-until-reboot mechanism (this is the whole point)

A BIOS DUP applied via iDRAC/Lifecycle Controller is **staged ("Scheduled")** and only writes the new KEK/db
into firmware at the **next host reboot / Lifecycle Controller pass**. So a server that *"pulled a BIOS update
months ago but hasn't rebooted in a long time"* almost certainly has the **2023 keys staged but not applied** —
**a single controlled reboot applies them.** Expect a benign `UEFI0074` POST warning ("The Secure Boot policy
has been modified since the last time the system was started"). KB 000402373 mandates: update → reboot (applies
during POST/LC) → a second reboot completes it.

## Runbook

1. **Audit** — confirm whether the staged/installed BIOS already carries the 2023 certs:
   ```bash
   racadm -r <iDRAC_IP> -u <user> -p <pw> bioscert view --all      # inspect each PK/KEK/DB cert CN for "...2023"
   racadm -r <iDRAC_IP> -u <user> -p <pw> get BIOS.SysSecurity.SecureBoot
   ```
   Redfish equivalent:
   ```
   GET /redfish/v1/Systems/System.Embedded.1/SecureBoot
   GET /redfish/v1/Systems/System.Embedded.1/SecureBoot/SecureBootDatabases/KEK/Certificates
   GET /redfish/v1/Systems/System.Embedded.1/SecureBoot/SecureBootDatabases/db/Certificates
   ```
   Look for `Microsoft Corporation KEK 2K CA 2023` (KEK) and `Windows UEFI CA 2023` / `Microsoft UEFI CA 2023`
   / `Microsoft Option ROM UEFI CA 2023` (db).
2. **If BIOS < minimum:** stage the BIOS update (iDRAC firmware update / DSU / OME).
3. **Reboot in a maintenance window.** BIOS applies during POST/LC; a second reboot completes it.
4. **Or enroll without a flash on a new-enough BIOS** — set `SecureBootPolicy=Custom`, then:
   ```
   POST /redfish/v1/Systems/System.Embedded.1/SecureBoot/Actions/SecureBoot.ResetKeys
   { "ResetKeysType": "ResetAllKeysToDefault" }
   ```
   `ResetAllKeysToDefault` re-installs the **firmware-embedded default key set** — 2023-inclusive *only if the
   BIOS is new enough* (otherwise it restores the old 2011 set). Completes at next reboot. **Back up keys
   first — this is destructive to any custom Secure Boot config.** Allowable `ResetKeysType`:
   `ResetAllKeysToDefault`, `DeleteAllKeys`, `DeletePK`, `ResetPK`, `ResetKEK`, `ResetDB`, `ResetDBX`.
5. **Manual enroll on an out-of-scope / old BIOS** (no 2023 DUP available): import the 2023 certs in Custom
   mode — `racadm ... bioscert import -t <type> -k <keycat> -f <path>\db.der`, or Redfish POST to the specific
   `SecureBootDatabases/<db|KEK>/Certificates` collection.
6. **Fleet automation** — the `dellemc.openmanage.idrac_secure_boot` Ansible module wraps all of this
   (`import_certificates`, `reset_keys` with the same 7 enum values, `restart`/`restart_type`). Note: "Secure
   boot certificate import operation requires a server restart." See the `ansible-idrac-9-10` skill for the
   `dellemc.openmanage` auth lifecycle (the iDRAC 9 ≥ 7.30.10.50 / iDRAC 10 `BasicAuthState` 401 trap).

## Gotchas specific to Dell

- **"Expert Key Mode" trap:** toggling Secure Boot **off** can wipe active UEFI variables and revert
  2023→2011 defaults (and trip BitLocker recovery). Don't "just disable it" as a workaround on Dell after
  migrating.
- **EoSL cutoff:** Dell ships BIOS updates only to platforms with End-of-Service-Life *after* 2025-12-31.
  Pre-14G / EoSL servers may have no 2023-bearing DUP → manual `bioscert import` or accept the frozen posture.
- These Dell hosts are also where the Ubuntu/Linux servers live — so for **bare-metal Linux on Dell, this
  iDRAC path is the primary fix** (it also delivers the 2023 *KEK*, which the OS-side manual `db` append in
  `linux-bare-metal.md` cannot). Use the OS-side append only when you want db enrollment without a BIOS
  flash/reboot.
