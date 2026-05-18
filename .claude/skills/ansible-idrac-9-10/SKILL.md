---
name: ansible-idrac-9-10
description: >-
  Run and debug `dellemc.openmanage` Ansible playbooks against Dell
  PowerEdge **iDRAC 9** (14G–16G) and **iDRAC 10** (17G — R670, R770,
  R870, R970, XE9780, XE9785). Covers the iDRAC 10 / iDRAC 9 ≥
  7.30.10.50 `BasicAuthState: Unadvertised` default that silently 401s
  `ansible.builtin.uri` (Dell KB 000437501), the `idrac_session` +
  `x_auth_token` lifecycle with `block:/always:`, `force_basic_auth:
  true` fallback for raw Redfish, OMSDK modules (`idrac_firmware`,
  `idrac_server_config_profile`) that cannot use tokens, iDRAC 10
  attribute deltas (`iDRAC.IPv4Static.*` → `iDRAC.IPv4.Static*`,
  `iDRAC.NIC.*` → `iDRAC.Network.*`, ACME+SCEP → `iDRAC.ACE`,
  `BIOS.SysSecurity.AcPwrRcvry*` → `System.ServerPwr.*`), iDRAC 9-only
  modules (`idrac_network` → `idrac_network_attributes`, `idrac_syslog`,
  `idrac_timezone_ntp`), iDRAC 10 Redfish Jobs URI under
  `/Oem/Dell/Jobs/`, WS-MAN removed on 17G, and version pins
  (collection ≥9.12.3 broad / ≥10.0.2 full; 9.12.1 for iDRAC 8).
when_to_use: >-
  Trigger on iDRAC, iDRAC9, iDRAC10, idrac10, 17G, PowerEdge 17G, Dell
  BMC, `dellemc.openmanage`, `idrac_session`, `idrac_attributes`,
  `idrac_bios`, `idrac_firmware`, `idrac_user`, `idrac_network`,
  `racadm`, `BasicAuthState`, `X-Auth-Token`, `force_basic_auth`, SCP,
  LC. Also symptoms: 401 with no `WWW-Authenticate`,
  "TLS/SSL handshake" on writes only, sensor 404 after firmware bump,
  attributes silently no-op'ing, "Dell ansible playbook stopped after
  firmware upgrade". Also XE9780/R770/R670 BMC and mixed iDRAC 9+10
  inventories needing per-gen branching.
---

# Ansible against iDRAC 9 and iDRAC 10

Operator skill for the `dellemc.openmanage` Ansible collection across both
generations of Dell's BMC. Targets collection **≥ 9.12.3** (broad iDRAC 10
support) and **10.0.2** (full coverage incl. SCP / storage / OS deployment,
Ansible Core 2.19+). Information current as of **May 2026** (iDRAC 10
firmware 1.30.10.50, iDRAC 9 firmware 7.30.10.50).

The skill exists because most iDRAC 9 playbooks **silently break on first
contact with a 17G server** for two reasons that look unrelated but stack on
top of each other: a firmware-level Basic-auth default change, and a
collection-level module rename. Knowing both stops the bleed in one
playbook edit instead of three days of firefighting.

## How to use this skill

Route to one or two reference files based on the question. Don't try to
load everything.

```
references/
├── auth-and-session.md    → BasicAuthState=Unadvertised, idrac_session +
│                            x_auth_token lifecycle (block/always), env
│                            fallback IDRAC_X_AUTH_TOKEN, OMSDK modules
│                            that CAN'T use tokens, force_basic_auth
│                            fallback for ansible.builtin.uri / raw
│                            Redfish, racadm BasicAuthState toggle,
│                            session-pool exhaustion, no_log/no-secret
│                            hygiene
├── idrac-10-deltas.md     → Verbatim attribute registry tables from the
│                            iDRAC 10 1.30.xx Attribute Registry —
│                            deprecated groups & attributes (Table 1),
│                            reorganized renames (Table 2), changed values
│                            and defaults (Table 3); module support
│                            matrix iDRAC 9 vs iDRAC 10; iDRAC 10 Redfish
│                            Jobs URI; WS-MAN removal; iDRAC 8 dropped in
│                            10.0.0
├── troubleshooting.md     → 10-pattern bug catalog from upstream GitHub
│                            issues — sensor URI rename, misleading
│                            "TLS/credentials" error on writes, idrac_user
│                            privilege regression, custom_privilege
│                            collapse, SCP not qualified, iso_image path
│                            rejection, NIC-info duplication, Ansible
│                            Core 2.18+ TypeError, generation-detection
│                            (`authentication_protocol` SHA vs SHA-512)
└── sources.md             → Dated index of Dell KBs, Ansible module
                             docs, GitHub PRs, attribute-registry PDF
                             for freshen mode
```

## Decision tree (start here)

```
   Is the target an iDRAC 10 / 17G box?  ──┐
   (R670/R770/R870/R970, R6715/R7715,      │ yes → token-only mindset:
    C6715/C7715, M7725, XE9780/XE9785,     │       always use idrac_session +
    XE7740 — also any server identifying   │       x_auth_token; avoid the
    as ServerGen=6 or HWModel="iDRAC 10")  │       OMSDK modules below
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
`x_auth_token` on every module — useful when chaining outside-ansible
session minting into a play.

See `references/auth-and-session.md` for the BasicAuthState backstory,
diagnostic curl/racadm commands, the `ansible.builtin.uri` fallback when
the collection isn't available, and the OMSDK-token gotcha.

## The three things that break iDRAC 9 playbooks on first 17G contact

1. **401 on Redfish with no `WWW-Authenticate` header.** Dell flipped the
   default `iDRAC.Redfish.BasicAuthState` to `Unadvertised` on iDRAC 10 ≥
   1.30.10.50 (and iDRAC 9 ≥ 7.30.10.50). Basic auth still works, but
   stock `ansible.builtin.uri` waits for the (now absent) challenge and
   401s. Fix: switch to the session pattern above, or add
   `force_basic_auth: true` to the `uri` call. Dell KB 000437501.

2. **`idrac_network` fails with "Unable to communicate with iDRAC … TLS/SSL
   handshake".** Misleading error. `idrac_network` is iDRAC 9-only. On
   iDRAC 10 use `idrac_network_attributes` (preferred) or `idrac_attributes`
   with the Redfish attribute names (`Network.1.DNSRacName`,
   `IPv4.1.StaticDNS1`, etc.). See [#1054], [#1038] in
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
- **Calling `idrac_firmware` or `idrac_server_config_profile` with
  `x_auth_token`.** These modules go through OMSDK
  (`module_utils/dellemc_idrac.py`), which strictly requires
  `idrac_user`+`idrac_password`. On a `Disabled`-BasicAuth iDRAC they may
  simply not work. Use Redfish-native modules
  (`idrac_attributes`, `redfish_firmware`, `redfish_firmware_rollback`)
  where possible.
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
fact (open feature request: dell/dellemc-openmanage-ansible-modules#1007).
Two options today:

```yaml
# Option A: detect from System info (works on both)
- dellemc.openmanage.idrac_system_info:
    idrac_ip: "{{ idrac_ip }}"
    x_auth_token: "{{ idrac_auth.x_auth_token }}"
  register: sys_info

- set_fact:
    is_idrac10: "{{ sys_info.system_info.idrac.HWModel | default('') == 'iDRAC 10' }}"

# Option B: get from Redfish DellAttributes directly via uri
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
- `idrac_network` vs `idrac_network_attributes`
- attribute names per the rename table in `references/idrac-10-deltas.md`

## Minimum versions cheat-sheet

| Component | Minimum | Notes |
|---|---|---|
| `dellemc.openmanage` | **9.12.3** broad, **10.0.2** full | 10.0.0 dropped iDRAC 8 — pin 9.12.1 for iDRAC 8 fleets |
| iDRAC 10 firmware | **1.20.50.50** | Current Recommended: 1.30.10.50 (Mar 2026) |
| iDRAC 9 firmware | 7.10.90.00 | BasicAuthState=Unadvertised default starts at **7.30.10.50** |
| Ansible Core | 2.18.8 (iDRAC modules), 2.19+ (also OME modules), 2.20 (latest) | 2.18.6 + older collection triggers `TypeError: bytes-like object` in `urls.py:_configure_auth` (#1046) |
| Python | 3.11+ | |

## Connection mode

All `dellemc.openmanage` modules run over HTTPS to the BMC from the
Ansible controller. Use `connection: local` (or `delegate_to: localhost`
on a per-task basis). There is **no `httpapi` connection plugin in this
collection** — `connection: httpapi` will fail. The canonical reference
playbook is at `playbooks/idrac/idrac_session.yml` in the upstream repo.

## Source files in the upstream collection (for cross-reference)

- `plugins/modules/idrac_session.py` — token mint module (`version_added: 9.2.0`)
- `plugins/module_utils/idrac_redfish.py` — auth layer, `IdracAnsibleModule.__init__` arg-spec, `_args_without_session` sets `force_basic_auth=True` for no-token path, `get_server_generation()`, `validate_idrac10_and_above()`
- `plugins/module_utils/session_utils.py` — lower-level `SessionAPI`, `create_session`, `delete_session`
- `plugins/module_utils/dellemc_idrac.py` — OMSDK path (no token support)
- `playbooks/idrac/idrac_session.yml` — canonical session-lifecycle example
- `tests/integration/targets/idrac_session_auth/tests/idrac_redfish_auth_valid-11786.yaml` — canonical token-handoff test
- `docs/README.md` — definitive iDRAC 9 / iDRAC 10 per-module support matrix
