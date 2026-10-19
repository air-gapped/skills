---
name: ansible-idrac-9-10
description: >-
  Run and debug `dellemc.openmanage` Ansible playbooks against Dell
  PowerEdge **iDRAC 9** (14G–16G) and **iDRAC 10** (17G — R670, R770,
  R870, R970, XE9780, XE9785). Covers the iDRAC 10 / iDRAC 9 ≥
  7.30.10.50 `BasicAuthState: Unadvertised` default that silently 401s
  `ansible.builtin.uri` (Dell KB 000437501), the `idrac_session` +
  `x_auth_token` lifecycle with `block:/always:`, `force_basic_auth:
  true` fallback for raw Redfish, modules that reject tokens
  (`idrac_bios`, `idrac_firmware`, `idrac_system_info`), iDRAC 10
  attribute deltas (`iDRAC.IPv4Static.*` → `iDRAC.IPv4.Static*`,
  `iDRAC.NIC.*` → `iDRAC.Network.*`, ACME+SCEP → `iDRAC.ACE`,
  `BIOS.SysSecurity.AcPwrRcvry*` → `System.ServerPwr.*`), modules
  removed in 11.0.0 (`idrac_network` → `idrac_network_attributes`,
  `idrac_syslog`, `idrac_timezone_ntp`), iDRAC 10 Redfish Jobs URI under
  `/Oem/Dell/Jobs/`, WS-MAN removed on 17G, and version pins
  (collection ≥9.12.3 broad / ≥10.0.2 full; 9.12.1 for iDRAC 8).
when_to_use: >-
  Trigger on iDRAC, iDRAC9, iDRAC10, 17G, PowerEdge 17G, Dell BMC,
  `dellemc.openmanage`, `idrac_session`, `idrac_attributes`,
  `idrac_bios`, `idrac_firmware`, `idrac_user`, `idrac_network`,
  `racadm`, `BasicAuthState`, `X-Auth-Token`, `force_basic_auth`, SCP,
  LC. Also symptoms: 401 with no `WWW-Authenticate`,
  "TLS/SSL handshake" on writes only, sensor 404 after firmware bump,
  attributes silently no-op'ing, "Dell ansible playbook stopped after
  firmware upgrade". Also mixed iDRAC 9+10 inventories needing per-gen
  branching.
---

# Ansible against iDRAC 9 and iDRAC 10

Operator skill for the `dellemc.openmanage` Ansible collection across both
generations of Dell's BMC. Targets collection **≥ 9.12.3** (broad iDRAC 10
support) and **10.0.2** (full coverage incl. SCP / storage / OS deployment,
Ansible Core 2.19+). Information current as of **October 2026** (collection
11.0.0, iDRAC 10 firmware 1.30.x, iDRAC 9 firmware 7.30.10.50).

## Reference routing

Load only the file the question needs:

| Question | File |
|---|---|
| 401s, BasicAuthState, session/token lifecycle, which modules reject `x_auth_token`, `force_basic_auth`, raw-Redfish token minting, secret hygiene | `references/auth-and-session.md` |
| Attribute renamed / deprecated / changed default on iDRAC 10, module support matrix, Jobs URI, WS-MAN, 17G platform list | `references/idrac-10-deltas.md` |
| A specific error or misbehaviour (17 catalogued upstream bugs with symptom → cause → fix) | `references/troubleshooting.md` |
| Where a claim comes from, when it was verified | `references/sources.md` |
| Static check of a playbook/role against everything below | `scripts/lint-playbook.py` (`--selfcheck` verifies it) |

## Decision tree (start here)

```
   Is the target an iDRAC 10 / 17G box?  ──┐
   (R670/R770/R870/R970, R6715/R7715,      │ yes → token-only mindset:
    C6715/C7715, M7725, XE9780/XE9785,     │       always use idrac_session +
    XE7740 — also any server identifying   │       x_auth_token where the module
    as ServerGen=6 or HWModel="iDRAC 10")  │       accepts it (list below)
                                           │
   no → iDRAC 9 (14G-16G)?                 │
   ┌───────────────────────────────────────┘
   │ Firmware ≥ 7.30.10.50?
   │   yes → BasicAuthState default is now Unadvertised — same
   │         broken-clients story as iDRAC 10; use idrac_session
   │         or force_basic_auth on ansible.builtin.uri
   │   no  → either auth pattern still works; recommend session anyway
   │         for forward-compat
   │
   iDRAC 8?  → STOP. Collection ≥ 10.0.0 dropped iDRAC 8. Pin
               dellemc.openmanage 9.12.1.
```

## Canonical session pattern (lift verbatim into playbooks)

The whole skill is built around this 30-line shape. Block + always so the
session is always cleaned up even when middle tasks fail — iDRAC's
concurrent-session table is small and orphaned sessions lock fleets out.

```yaml
- name: Configure iDRAC over a session
  hosts: idracs
  gather_facts: false
  connection: local       # collection has no httpapi plugin; modules run
                          # locally and POST Redfish to the BMC

  tasks:
    - block:
        - name: Open iDRAC session
          dellemc.openmanage.idrac_session:
            hostname:       "{{ idrac_ip }}"
            username:       "{{ idrac_user }}"
            password:       "{{ idrac_password }}"
            validate_certs: false
            state:          present
          register: idrac_auth
          no_log: true

        # Subsequent tasks use x_auth_token, NOT idrac_user/idrac_password.
        # The collection's arg-spec makes them mutually exclusive
        # (idrac_redfish.py:_init_), so passing both is a hard error.

        - name: Set iDRAC attributes
          dellemc.openmanage.idrac_attributes:
            idrac_ip:       "{{ idrac_ip }}"
            x_auth_token:   "{{ idrac_auth.x_auth_token }}"
            validate_certs: false
            idrac_attributes:
              SNMP.1.AgentCommunity: public
              SNMP.1.AgentEnable:    Enabled

      always:
        - name: Close iDRAC session
          dellemc.openmanage.idrac_session:
            hostname:       "{{ idrac_ip }}"
            validate_certs: false
            state:          absent
            x_auth_token:   "{{ idrac_auth.x_auth_token }}"
            session_id:     "{{ idrac_auth.session_data.Id }}"
          when: idrac_auth.x_auth_token is defined
          no_log: true
```

The `when:` guard on cleanup is so the always-block doesn't crash when the
session-open task itself was the thing that failed. The
`IDRAC_X_AUTH_TOKEN` env var is also accepted as a fallback for
`x_auth_token` on every module that takes `x_auth_token` — useful when
chaining outside-ansible session minting into a play.

On collection ≥ 11.0.0 the cleanup task warns `Self-session protection
not available when using x_auth_token` and still deletes the session.
Expected — keep the token-based cleanup; do not "fix" the warning.

See `references/auth-and-session.md` for the BasicAuthState backstory,
diagnostic curl/racadm commands, the `ansible.builtin.uri` fallback when
the collection isn't available, and the modules that reject tokens.

## The three things that break iDRAC 9 playbooks on first 17G contact

1. **401 on Redfish with no `WWW-Authenticate` header.** Dell flipped the
   default `iDRAC.Redfish.BasicAuthState` to `Unadvertised` on iDRAC 10 ≥
   1.30.10.50 (and iDRAC 9 ≥ 7.30.10.50). Basic auth still works, but
   stock `ansible.builtin.uri` waits for the (now absent) challenge and
   401s. Fix: switch to the session pattern above, or add
   `force_basic_auth: true` to the `uri` call. Dell KB 000437501.

2. **`idrac_network` fails with "Unable to communicate with iDRAC … TLS/SSL
   handshake".** Misleading error. `idrac_network` is iDRAC 9-only, and
   collection 11.0.0 removed it outright. Use `idrac_network_attributes`
   (preferred) or `idrac_attributes` with the Redfish attribute names
   (`Network.1.DNSRacName`, `IPv4.1.StaticDNS1`, etc.). See [#1054], [#1038] in
   `references/troubleshooting.md`.

3. **Attribute names silently no-op.** Many iDRAC 9 attributes moved to new
   groups on iDRAC 10 — entire categories of network, certificate
   enrollment, and BIOS-AC-power settings now live at different paths.
   Examples:
   - `iDRAC.IPv4Static.Address` → `iDRAC.IPv4.StaticAddress`
   - `iDRAC.NIC.DNSRacName` → `iDRAC.Network.DNSRacName`
   - `iDRAC.ACME.CA-URL` → `iDRAC.ACE.CA-URL`
   - `iDRAC.SCEP.*` → `iDRAC.ACE.*`
   - `BIOS.SysSecurity.AcPwrRcvry` → `System.ServerPwr.AcPwrRcvry`

   See `references/idrac-10-deltas.md` for the full verbatim table from the
   iDRAC 10 Attribute Registry (Chapters 2-4).

## Anti-patterns that look fine but aren't

- **Sending both `idrac_user`/`idrac_password` AND `x_auth_token` in the
  same task.** Hard error from the collection arg-spec
  (`mutually_exclusive`). Pick one; let `idrac_session` mint the token.
- **Forgetting to delete sessions on play failure.** iDRAC sessions count
  against a small pool (~8). A skipped cleanup orphans tokens until idle
  timeout; rapid CI runs will lock the iDRAC out. Always wrap in
  `block: … always: <state: absent>`.
- **Passing `x_auth_token` to a username/password-only module.** These
  build their arg-spec from `idrac_auth_params`, which has no
  `x_auth_token`, so the task fails with `Unsupported parameters`:
  `idrac_bios`, `idrac_firmware`, `idrac_firmware_info`,
  `idrac_system_info`, the four `idrac_lifecycle_controller_*` modules,
  and (11.0.0+) `idrac_bios_registry_info`, `idrac_network_info`,
  `idrac_network_attributes_info`, `idrac_session_info`. Give them
  `idrac_user`+`idrac_password` (no_log). They send Basic pre-emptively:
  fine on `Unadvertised`, broken on `Disabled`. For firmware on a
  `Disabled` iDRAC use `redfish_firmware`. Any other module: confirm
  `ansible-doc dellemc.openmanage.<module> | grep x_auth_token` first.
- **Calling `idrac_user` to rotate a password without `privilege:`.** On
  iDRAC 10, omitted privilege silently defaults to `ReadOnly` — a
  password rotate can demote root. Always pass the explicit privilege.
- **Putting `/path/in/iso_image:` for `idrac_os_deployment`.** Post-10.0.1
  Redfish backend rejects path components. Directory goes in `share_name:`,
  bare filename in `iso_image:`.
- **Flipping `iDRAC.Redfish.BasicAuthState` back to `Enabled` as a
  permanent fix.** Drifts on every factory reset / reimage / new shipment;
  re-creates the exposure Dell intended to close. Fix the playbook once,
  the right way.

## Generation handling in mixed inventories

The Dell collection doesn't expose iDRAC generation as a first-class
fact (open feature request: dell/dellemc-openmanage-ansible-modules#1007),
and `idrac_system_info` returns no `HWModel`. Read `Info.1.HWModel` from
the Redfish DellAttributes (the collection's own `get_idrac_hw_model()`
reads the same key):

```yaml
- ansible.builtin.uri:
    url: "https://{{ idrac_ip }}/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1"
    headers: { X-Auth-Token: "{{ idrac_auth.x_auth_token }}" }
    validate_certs: false
  register: dell_attrs
- set_fact:
    is_idrac10: "{{ (dell_attrs.json.Attributes['Info.1.HWModel'] | default('')) == 'iDRAC 10' }}"
```

Then branch:
- `idrac_user.authentication_protocol`: `SHA` on iDRAC 9, `SHA-512` on iDRAC 10
- `idrac_network` vs `idrac_network_attributes` — collection ≤ 10.0.3 only; on 11.0.0+ `idrac_network` is gone, use `idrac_network_attributes` on both
- attribute names per the rename table in `references/idrac-10-deltas.md`

## Done when (porting or reviewing a play)

Every item holds, for every task in the play. Run the static checks first:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/lint-playbook.py" <playbook-or-role-dir> --idrac10   # omit --idrac10 for iDRAC 9-only plays
```

It exits 1 on removed modules, tokens passed to rejecting modules,
token + password together, credentialed Redfish `uri` without
`force_basic_auth`, `/` in `iso_image`, and (with `--idrac10`) password
changes without `privilege` and attribute keys renamed or deprecated on
iDRAC 10. A clean run covers the first three items below; the last two
need the live iDRAC.

- Each `dellemc.openmanage` task passes `x_auth_token` only to a module
  that accepts it; the rejecting modules (anti-patterns above) get
  `idrac_user`/`idrac_password` with `no_log: true`.
- Each `ansible.builtin.uri` call to the BMC sends `X-Auth-Token` or
  `force_basic_auth: true`.
- No call to a module removed in 11.0.0 remains.
- Each attribute key is valid for the target generation
  (`references/idrac-10-deltas.md` §3–§4). Verify by reading the value back
  (GET the DellAttributes URI above, compare to the desired value):
  a renamed key reports `changed: false` without applying, so task
  status proves nothing.
- `Members@odata.count` of `GET /redfish/v1/SessionService/Sessions` is
  the same after the run as before it.

## Minimum versions cheat-sheet

| Component | Minimum | Notes |
|---|---|---|
| `dellemc.openmanage` | **9.12.3** broad, **10.0.2** full | 10.0.0 dropped iDRAC 8 — pin 9.12.1 for iDRAC 8 fleets. 11.0.0 removed `idrac_network`, `idrac_syslog`, `idrac_timezone_ntp` and every `dellemc_*` module — port those calls before upgrading |
| iDRAC 10 firmware | **1.20.50.50** | 1.30.10.50 (Mar 2026) is the BasicAuthState cutover. Newer 1.30.x builds are per-platform (e.g. 1.30.30.50, 1.30.31.10, Jun 2026) — read KB 000305325 for the Recommended build for *your* model, don't assume one number fleet-wide |
| iDRAC 9 firmware | 7.10.90.00 | BasicAuthState=Unadvertised default starts at **7.30.10.50** |
| Ansible Core | 2.18.8 or ≥ 2.19 (iDRAC modules); 2.19 / 2.20 (OME modules) | Collection README's tested set. 2.18.6 + older collection triggers `TypeError: bytes-like object` in `urls.py:_configure_auth` (#1046) |
| Python | 3.11+ | |

## Connection mode

All `dellemc.openmanage` modules run over HTTPS to the BMC from the
Ansible controller. Use `connection: local` (or `delegate_to: localhost`
on a per-task basis). There is **no `httpapi` connection plugin in this
collection** — `connection: httpapi` will fail. The canonical reference
playbook is at `playbooks/idrac/idrac_session.yml` in the upstream repo.
