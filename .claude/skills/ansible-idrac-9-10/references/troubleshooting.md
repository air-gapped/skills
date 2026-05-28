# Troubleshooting — bug patterns from upstream

Cataloged from `dell/dellemc-openmanage-ansible-modules` open + closed
issues and merged PRs through May 2026. Each pattern names the symptom,
the cause, and the workaround the maintainers (or community contributors
that maintainers accepted) recommend.

## Contents

1. TLS/SSL-handshake error on writes (`idrac_network` iDRAC 9-only)
2. `idrac_system_info` 404s on sensors after firmware bump
3. `idrac_user` password change demotes user to ReadOnly
4. `custom_privilege:` bitmap collapses to Operator
5. `idrac_server_config_profile` (SCP) not qualified on iDRAC 10
6. `idrac_os_deployment` rejects `/` inside `iso_image:`
7. iDRAC 8 dropped in collection 10.0.0
8. `idrac_system_info` no longer returns VirtualDisk on iDRAC 10
9. NIC details duplicated across all interfaces (≤ 10.0.1)
10. Ansible-core 2.18+/2.19 + old collection → `TypeError`
11. Generation detection (mixed iDRAC 9 + iDRAC 10 inventory)
12. BIOS workload-profile change-set ordering
13. WS-MAN calls fail wholesale on 17G
14. Session-pool exhaustion on rapid CI
15. `validate_certs: true` requires a CA push first
16. The `gen17` term — don't grep for it

## 1. "Unable to communicate with iDRAC … TLS/SSL handshake" on writes

**Symptom.** Read-only modules with the same credentials succeed (e.g.
`idrac_system_info`), but `idrac_network` or `idrac_user` write tasks
fail with the misleading error:

> Unable to communicate with iDRAC … Incorrect username or password,
> unreachable iDRAC IP or a failure in TLS/SSL handshake.

**Cause.** The module hit a Redfish endpoint that's not present on
iDRAC 10 / 17G. `idrac_network` is iDRAC 9-only. The collection wraps
the underlying 404/405 in the generic auth-error message.

**Fix.**
- For network config: switch to `idrac_network_attributes`, or
  `idrac_attributes` against the Redfish names
  (`Network.1.DNSRacName`, `IPv4.1.StaticDNS1`, …).
- For user config: keep `idrac_user`, but see pattern #3 below for the
  privilege gotcha.

**Refs:** #1054, #1038. Maintainer @Saksham-Nautiyal: *"The previously
used module has been deprecated, and the recommended alternative is
`idrac_network_attributes`."*

## 2. `idrac_system_info` 404s on sensors after firmware bump

**Symptom.** Worked yesterday, 404 today on
`/Sensors/SystemBoardInletTemp` or `/Sensors/SystemBoardCPUUsage` or
`/Sensors/PS1Current1`.

**Cause.** Dell renames sensor URI paths across iDRAC 10 firmware micro-
releases. Notably `SystemBoardInletTemp` was renamed to `InletTemp`
between firmware 1.20.60.50 and 1.20.70.50. The collection hardcodes
these URIs in `plugins/module_utils/idrac_utils/info/system_metrics.py`
and `system_board_metrics.py`. Worse, `invoke_request` in
`module_utils/idrac_redfish.py` (≈ line 217–220) re-raises HTTPError
on 404 rather than returning, bypassing the status-code guards.

**Fix.**
- Upgrade collection to ≥ 10.0.2 + post-10.0.1 fix (PR #1061, PR #1034
  enumerate the SensorCollection first, only fetch sensors present in
  the collection).
- Pin both collection version AND iDRAC firmware in CI so this
  combination is testable in advance of any rolling bump.
- If a 404 still appears: it's a sensor that simply doesn't exist on
  this hardware / this firmware. Enable the iDRAC Performance metrics
  collection (iDRAC GUI → Performance tab) — `SystemBoardCPUUsage`-class
  sensors are only populated when metrics collection is on.

**Refs:** #1053, #1039, #1017, #1088. PRs #1034, #1055, #1061.

## 3. `idrac_user` password change demotes user to ReadOnly

**Symptom.** Calling `idrac_user` with `state: present` to rotate a
password without an explicit `privilege:` — works fine on iDRAC 9; on
iDRAC 10 the user is demoted to `ReadOnly` (locking out root) and a
follow-up 500 Internal Server Error appears because the now-demoted
user can no longer commit.

**Cause.** Omitted-field idempotency changed on iDRAC 10. The module
sends a full user payload; on iDRAC 9 the omitted privilege field was
preserved from current state; on iDRAC 10 it defaults to `ReadOnly`.

**Fix.** Always pass the explicit `privilege:` (or
`custom_privilege:` — but see pattern #4) on every `idrac_user` task
that touches an iDRAC 10:

```yaml
- dellemc.openmanage.idrac_user:
    idrac_ip:      "{{ idrac_ip }}"
    x_auth_token:  "{{ idrac_auth.x_auth_token }}"
    state:         present
    user_name:     root
    user_password: "{{ new_root_password }}"
    privilege:     Administrator   # ← mandatory on iDRAC 10
```

**Refs:** #947.

## 4. `custom_privilege:` bitmap collapses to `Operator`

**Symptom.** `custom_privilege: 33` (Login + Virtual Console) on
iDRAC 10 silently produces a user with role `Operator`, not the custom
bitmap.

**Cause.** The Redfish custom-privilege mapping is broken in collection
≤ 10.0.1. Fixed in PR #1069 (merged 2025-12-19), shipped in collection
**10.0.2**.

**Fix.** On 10.0.2+ `custom_privilege:` is reliable. On ≤ 10.0.1 use the
named `privilege:` enum (`Administrator`, `Operator`, `ReadOnly`,
`NoAccess`).

**Refs:** #1059, PR #1069.

## 5. `idrac_server_config_profile` (SCP) not qualified on iDRAC 10

**Symptom.** `AttributeError: 'NoneType' object has no attribute 'get'`
from the SCP module. Or simply a hard failure on export.

**Cause.** Maintainer @gokul-srivathsan in #959: *"SCP module is yet to
be qualified for iDRAC 10."* The module's allowable-values validator
assumes a static list that isn't exposed on iDRAC 10 yet.

**Fix.** Until SCP qualification ships:
- Use the per-attribute modules (`idrac_attributes`, `idrac_bios`,
  `idrac_storage_volume`, `idrac_network_attributes`).
- Or call Redfish PATCH directly via `ansible.builtin.uri` against
  `/redfish/v1/Managers/iDRAC.Embedded.1/Attributes` etc.

**Refs:** #959.

## 6. `idrac_os_deployment` rejects `/` inside `iso_image:`

**Symptom.** `Unable to run the command because an invalid firmware
image file name is entered.` on `idrac_os_deployment` for any value of
`iso_image:` that contains a `/`.

**Cause.** The 10.0.1 release switched `idrac_os_deployment` from
OMSDK to Redfish. The Redfish backend refuses path components in the
filename argument.

**Fix.** Split the value:

```yaml
- dellemc.openmanage.idrac_os_deployment:
    share_name:    "//nfs.example.com/isos/rhel"   # ← directory here
    iso_image:     "rhel-9.4-x86_64-dvd.iso"        # ← bare filename only
    # ...
```

**Refs:** #1058.

## 7. iDRAC 8 dropped in collection 10.0.0

**Symptom.** Existing iDRAC 8 playbooks crash after upgrading the
collection to 10.x — typically `idrac_server_config_profile` for SCP
export, or `idrac_bios` for BIOS mode config.

**Cause.** Collection 10.0.0 explicitly removed iDRAC 8 from supported
platforms. Companion regression: PR #889 changed the Jobs URI to
`/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/{id}` without
gen-dispatch — iDRAC 8 lacks the `Oem/Dell/Jobs` endpoint and returns
HTTP 405.

**Fix.** Pin `dellemc.openmanage` to **9.12.1** for any inventory that
still contains iDRAC 8 (14G servers and older with old firmware).
Maintainer @anupamaloke confirmed Dell will NOT accept community
contributions to restore iDRAC 8 support.

**Refs:** #1008, #1009.

## 8. `idrac_system_info` no longer returns VirtualDisk on iDRAC 10

**Symptom.** Empty `storage`/`VirtualDisk` section in
`idrac_system_info` output. Looks like a regression — it isn't.

**Cause.** By-design split post-v8.0.0. On iDRAC 10, `idrac_system_info`
is system-only. Storage moved out to dedicated modules.

**Fix.** Use `idrac_storage_volume` or
`idrac_redfish_storage_controller`. For raw inventory: directly call
`/redfish/v1/Systems/System.Embedded.1/Storage`.

**Refs:** #1101. Maintainer @gokul-srivathsan confirmed
not-a-regression in the issue thread.

## 9. NIC details duplicated across all interfaces (≤ 10.0.1)

**Symptom.** `idrac_system_info.NIC[*]` returns the same MAC,
link-speed, permanent MAC, and health for every host NIC.

**Cause.** Bug in the Redfish NIC collector — it hits the iDRAC's own
management NIC endpoint and reuses the result for all members.

**Fix.** Upgrade to ≥ 10.0.2 (fixed in PR #1055 alongside FC inventory
restoration). On older versions, don't trust per-NIC fields from
`idrac_system_info` on iDRAC 10 — query
`/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces` directly.

**Refs:** #1044.

## 10. Ansible-core 2.18+/2.19 + old collection → `TypeError`

**Symptom.** `idrac_attributes` fails with
`TypeError: a bytes-like object is required, not 'str'` from
`urls.py:_configure_auth`.

**Cause.** Ansible-core 2.18 and 2.19 changed the `urls.py` auth
handling in a way the older `dellemc.openmanage` collection's auth
plumbing doesn't tolerate. Triggers in particular on Ubuntu 24.04 with
Python 3.12.3.

**Fix.** Either:
- Upgrade `dellemc.openmanage` to ≥ 10.0.2 (which targets ansible-core
  2.19+).
- Pin ansible-core to ≤ 2.17 for old playbook fleets.

**Refs:** #1046.

## 11. Generation detection (mixed iDRAC 9 + iDRAC 10 inventory)

There's no first-class "give me the iDRAC generation" call yet —
upstream feature request **#1007** is open.

Two viable patterns today:

**A. Use `idrac_system_info`:**

```yaml
- dellemc.openmanage.idrac_system_info:
    idrac_ip:     "{{ idrac_ip }}"
    x_auth_token: "{{ idrac_auth.x_auth_token }}"
  register: sys_info

- set_fact:
    is_idrac10: "{{ (sys_info.system_info.idrac.HWModel | default('')) == 'iDRAC 10' }}"
```

**B. Hit DellAttributes directly:**

```yaml
- ansible.builtin.uri:
    url: "https://{{ idrac_ip }}/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1"
    headers: { X-Auth-Token: "{{ idrac_auth.x_auth_token }}" }
    validate_certs: false
  register: dell_attrs

- set_fact:
    is_idrac10: "{{ (dell_attrs.json.Attributes['Info.1.HWModel'] | default('')) == 'iDRAC 10' }}"
    server_gen: "{{ dell_attrs.json.Attributes['Info.1.ServerGen'] | default(0) | int }}"
    # ServerGen enum: 12G=1, 13G=2, 14G=3, 15G=4, 16G=5, 17G=6, 18G=7
```

Then branch on `is_idrac10`. The two most common things that need to
branch:

| Concern | iDRAC 9 | iDRAC 10 |
|---|---|---|
| `idrac_user.authentication_protocol` | `SHA` | `SHA-512` |
| Network module | `idrac_network` | `idrac_network_attributes` |
| Static IP attr names | `iDRAC.IPv4Static.Address` | `iDRAC.IPv4.StaticAddress` |
| Network DNS attr names | `iDRAC.NIC.DNSRacName` | `iDRAC.Network.DNSRacName` |
| BIOS power recovery | `BIOS.SysSecurity.AcPwrRcvry` | `System.ServerPwr.AcPwrRcvry` |
| Cert enrollment | `iDRAC.ACME.*` / `iDRAC.SCEP.*` | `iDRAC.ACE.*` |

## 12. BIOS workload-profile change-set ordering

**Symptom.** Setting `WorkloadProfile` directly returns
`changed: false` or applies but then snaps back.

**Cause.** On iDRAC 10, `WorkloadProfile` can only be set when
`SysProfile` is `Custom`. The two changes can't be in one PATCH.

**Fix.** Maintainer @gokul-srivathsan in #1072:

```yaml
- name: Step 1 — make SysProfile custom
  dellemc.openmanage.idrac_bios:
    idrac_ip:     "{{ idrac_ip }}"
    x_auth_token: "{{ idrac_auth.x_auth_token }}"
    attributes:
      SysProfile: Custom

- name: Step 2 — apply workload profile (separate PATCH)
  dellemc.openmanage.idrac_bios:
    idrac_ip:     "{{ idrac_ip }}"
    x_auth_token: "{{ idrac_auth.x_auth_token }}"
    attributes:
      WorkloadProfile: VirtualizationMaxPerformanceProfile
      SysProfile:      Custom
```

## 13. `WS-MAN` calls fail wholesale on 17G

If a legacy playbook leans on `wsmancli` shellouts or
`community.windows.win_winrm` against the iDRAC management interface
— it's done. WS-MAN was removed on iDRAC 10. Port to Redfish or
`dellemc.openmanage` modules; there is no compatibility shim.

## 14. Session-pool exhaustion on rapid CI

**Symptom.** First few runs work, subsequent runs fail to mint
sessions: `Could not create the session`. Sometimes the iDRAC UI is
also locked out — *"too many connections"*.

**Cause.** iDRAC's concurrent-session limit (~8) was hit by previous
runs that didn't clean up their sessions (skipped `always:`, killed
mid-run, etc.). Tokens stay valid until the iDRAC's idle timeout
reaps them (default 30 min).

**Fix.**
- Always use `block: … always: <state: absent>` around session work.
- Lower `serial:` and `max_fail_percentage:` on per-host fan-out plays
  so partial failures don't accumulate orphans.
- As a last resort to clear the pool: SSH into the iDRAC and
  `racadm getssninfo` then `racadm closessn -i <session>`. Or wait.

## 15. `validate_certs: true` requires a CA push first

Default iDRAC certs are self-signed. Setting `validate_certs: true`
on day one fails. Workflow:

1. Push the internal CA chain via `idrac_certificates`:

   ```yaml
   - dellemc.openmanage.idrac_certificates:
       idrac_ip:        "{{ idrac_ip }}"
       x_auth_token:    "{{ idrac_auth.x_auth_token }}"
       command:         import
       certificate_type: CA
       certificate_path: /etc/pki/internal-ca.pem
   ```

2. Reset the iDRAC if required (`idrac_reset`).
3. Re-flip to `validate_certs: true` and `ca_path: /etc/pki/internal-ca.pem`
   on subsequent runs.

## 16. The `gen17` term — don't grep for it

The string `gen17` appears exactly **once** in the entire upstream
collection codebase (CHANGELOG entry for v10.0.1 fixing #1017). It's
not a tag, a fact, or a switch. Use `HWModel == 'iDRAC 10'` or
`ServerGen == 6` for any conditional, not `gen17`.
