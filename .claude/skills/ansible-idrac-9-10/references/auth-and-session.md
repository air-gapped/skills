# Auth and session — the iDRAC BasicAuth story and how to use tokens

The whole reason this skill exists. Two things stack on top of each other:

1. **Firmware-level change.** Starting iDRAC 9 ≥ **7.30.10.50** and iDRAC
   10 ≥ **1.30.10.50** the Redfish `AccountService` no longer **advertises**
   HTTP Basic in the 401 `WWW-Authenticate` header. Basic auth still
   works, but clients that wait for the challenge before sending
   credentials (`ansible.builtin.uri`, browsers, generic scanners) hang on
   401 with no recovery path.

2. **Collection-level recommendation.** Dell's official guidance is to
   stop relying on Basic and switch to session-token auth via
   `dellemc.openmanage.idrac_session`. Most `dellemc.openmanage` modules
   accept `x_auth_token:` in place of `idrac_user`/`idrac_password` —
   not all; see "Modules that reject `x_auth_token`" below.

## The BasicAuth tri-state

The Redfish OEM attribute is `iDRAC.Redfish.BasicAuthState` (also
surfaced on the standard Redfish `AccountService.HTTPBasicAuth` property):

| Value          | Behavior |
|----------------|----------|
| `Enabled`      | Legacy. 401 responses include `WWW-Authenticate: Basic realm="RedfishService"`. |
| `Unadvertised` | **New default** on iDRAC 9 ≥ 7.30.10.50 / iDRAC 10 ≥ 1.30.10.50. Basic still works, but no challenge is announced. Generic clients can't probe. |
| `Disabled`     | Basic auth rejected entirely. Only X-Auth-Token (session-based) auth accepted. |

GUI path on **iDRAC 10**: `iDRAC Settings → Connectivity → Services →
Redfish → HTTP Basic Authentication`. Dell KB 000437501 still documents
the iDRAC 9 path (`iDRAC Settings → Services → Redfish`) — wrong for 17G.
On 14G (iDRAC 9 7.00.00.184) the Web UI cannot change it at all — use
`racadm set iDRAC.Redfish.BasicAuthState` or a Redfish PATCH.

XE-platform-specific firmware branches (1.20.55.x for XE9780, 1.20.95.x
for XE9785) appear to have flipped the default ahead of the mainline
1.30.10.50. Factory-shipped 17G servers ordered after Mar 2026 will
arrive with `Unadvertised` regardless.

## How to spot it

A playbook that has worked for years suddenly fails with HTTP 401 and no
useful detail. Quick check from any Linux host that can reach the iDRAC:

```sh
curl -v -k https://<idrac>/redfish/v1/Managers/iDRAC.Embedded.1 2>&1 \
  | grep -i 'WWW-Authenticate\|401'
```

- **Old behavior (`Enabled`):** both `401 Unauthorized` and
  `WWW-Authenticate: Basic realm="RedfishService"` appear.
- **New behavior (`Unadvertised`):** only `401 Unauthorized`. No
  challenge.

Read the current state via racadm (over SSH to the iDRAC):

```sh
racadm get iDRAC.Redfish.BasicAuthState
```

Or via Redfish PATCH on the `AccountService`:

```sh
curl -sk -u root:<pw> https://<idrac>/redfish/v1/AccountService | \
  jq '.HTTPBasicAuth'
```

## Why not flip it back to Enabled?

Technically possible:

```sh
racadm set iDRAC.Redfish.BasicAuthState Enabled
```

Not recommended:

1. Undoes the deliberate hardening that closes an unintended-exposure
   path.
2. Drifts on every new server, every firmware reflash, every factory
   reset — chasing the drift becomes ongoing work.
3. Papers over the deeper issue: the playbooks use a weaker auth
   pattern than the iDRAC spec recommends. Sessions have been the
   documented preferred pattern for years.

Fix the playbooks once; don't fight the firmware.

## Canonical session lifecycle

The full `block:`/`always:` session play lives in SKILL.md under "Canonical
session pattern" — lift it from there. The shape: `idrac_session state:
present` (registers `idrac_auth`) → middle tasks pass `x_auth_token:` and
NOT username/password (the arg-spec marks them mutually exclusive) →
`always:` closes with `state: absent` guarded by `when: idrac_auth.x_auth_token
is defined` so the cleanup doesn't itself crash when the open task failed.

### Return shape of `idrac_session`

```yaml
idrac_auth:
  x_auth_token: "<32-char-hex-token-from-iDRAC>"
  session_data:
    Id: "2"
    SessionType: "Redfish"
    UserName: "root"
    CreatedTime: "2026-05-17T10:23:11+00:00"
```

`x_auth_token` becomes the value of the `X-Auth-Token` HTTP header on
every subsequent Redfish request. `session_data.Id` is the SessionService
identifier used by the DELETE.

### Aliases worth knowing

- `idrac_session.username` ↔ `idrac_user`
- `idrac_session.password` ↔ `idrac_password`
- `x_auth_token` ↔ `auth_token` (older docs use the alias)

### Env-var fallbacks

Modules check these env vars when the matching parameter is omitted
(`IdracAnsibleModule` in `module_utils/idrac_redfish.py`; `RedfishAnsibleModule`
in `module_utils/redfish.py`). `IDRAC_X_AUTH_TOKEN` applies only to modules
that accept `x_auth_token`:

| Param           | Env var             |
|-----------------|---------------------|
| `idrac_user`    | `IDRAC_USERNAME`    |
| `idrac_password`| `IDRAC_PASSWORD`    |
| `x_auth_token`  | `IDRAC_X_AUTH_TOKEN`|

Useful when chaining outside-Ansible session minting (e.g. a wrapper
script) into a play.

## Session-pool exhaustion (the silent killer)

iDRAC's concurrent-session table is small (~8). Every play that opens a
session without cleaning up consumes a slot until the iDRAC's idle-session
timeout (default 30 min) reaps it. CI loops without `always:` cleanup
exhaust the pool within minutes — subsequent runs return `Could not
create the session` and the iDRAC's UI locks out too.

Always wrap real plays in `block: … always:`. For parallel per-host
plays, keep `max_fail_percentage` and `serial:` low to avoid hitting
the cap.

## Modules that reject `x_auth_token`

Token support depends on how the module builds its arg-spec, not on
the generation:

| Arg-spec base | `x_auth_token` | Modules |
|---|---|---|
| `IdracAnsibleModule` / `RedfishAnsibleModule` | accepted (mutually exclusive with user/password) | `idrac_attributes`, `idrac_boot`, `idrac_certificates`, `idrac_diagnostics`, `idrac_license`, `idrac_network_attributes`, `idrac_os_deployment`, `idrac_reset`, `idrac_secure_boot`, `idrac_server_config_profile`, `idrac_storage_volume`, `idrac_support_assist`, `idrac_system_erase`, `idrac_user`, `idrac_user_info`, `idrac_virtual_media`, `idrac_redfish_storage_controller`, all `redfish_*` |
| `AnsibleModule` + `idrac_auth_params` | **rejected** — `Unsupported parameters`; `idrac_user` + `idrac_password` required | `idrac_bios`, `idrac_firmware`, `idrac_firmware_info`, `idrac_system_info`, `idrac_lifecycle_controller_jobs`, `idrac_lifecycle_controller_job_status_info`, `idrac_lifecycle_controller_logs`, `idrac_lifecycle_controller_status_info`; 11.0.0+: `idrac_bios_registry_info`, `idrac_network_info`, `idrac_network_attributes_info`, `idrac_session_info` |

- The rejecting modules send Basic pre-emptively (`force_basic_auth`), so
  they work on `Unadvertised` and fail on `Disabled`. On a `Disabled`
  iDRAC, replace `idrac_firmware` with `redfish_firmware` and read
  inventory via `ansible.builtin.uri` + `X-Auth-Token`.
- In a session play, pass these modules `idrac_user`/`idrac_password`
  (with `no_log: true`) while the rest use the token.
- For a module not in the table, check
  `ansible-doc dellemc.openmanage.<module> | grep x_auth_token` first.

## Fallback for `ansible.builtin.uri` / raw Redfish

If a playbook uses `ansible.builtin.uri` directly (not the
`dellemc.openmanage` modules) and the `BasicAuthState` is `Unadvertised`,
the minimum fix is `force_basic_auth: true`:

```yaml
- ansible.builtin.uri:
    url:              "https://{{ idrac_ip }}/redfish/v1/Managers/iDRAC.Embedded.1"
    method:           GET
    url_username:     "{{ idrac_user }}"
    url_password:     "{{ idrac_password }}"
    force_basic_auth: true     # ← sends Authorization on first request
    validate_certs:   false
```

This works on `Unadvertised` but **not** on `Disabled`. For more than a
couple of one-off calls, mint a token once (POST `/redfish/v1/SessionService/Sessions`),
register, reuse via `X-Auth-Token`, DELETE at the end — same shape as
`idrac_session` does internally, just hand-rolled.

```yaml
- name: Mint a token directly
  ansible.builtin.uri:
    url:              "https://{{ idrac_ip }}/redfish/v1/SessionService/Sessions"
    method:           POST
    body_format:      json
    body:             { UserName: "{{ idrac_user }}", Password: "{{ idrac_password }}" }
    url_username:     "{{ idrac_user }}"
    url_password:     "{{ idrac_password }}"
    force_basic_auth: true
    validate_certs:   false
    status_code:      [200, 201]
  register: sess
  no_log: true

- name: Use it
  ansible.builtin.uri:
    url:            "https://{{ idrac_ip }}/redfish/v1/Managers/iDRAC.Embedded.1"
    headers:        { X-Auth-Token: "{{ sess.x_auth_token }}" }
    validate_certs: false

- name: Drop it
  ansible.builtin.uri:
    url:            "https://{{ idrac_ip }}{{ sess.location }}"
    method:         DELETE
    headers:        { X-Auth-Token: "{{ sess.x_auth_token }}" }
    validate_certs: false
    status_code:    [200, 204]
  when: sess.x_auth_token is defined
  no_log: true
```

(`sess.x_auth_token` and `sess.location` come from the `uri` module's
auto-extraction of response headers.)

## Secret hygiene

- `no_log: true` on every task that touches `username`/`password`/
  `x_auth_token`. iDRAC tokens are credential-equivalent for the
  session's lifetime and **will** appear in `-vvvv` output otherwise.
- Prefer Ansible Vault for `idrac_user` / `idrac_password`. The
  `IDRAC_*` env-var fallback is intended for ephemeral CI contexts, not
  long-lived inventory storage.
- `validate_certs: false` is endemic in Dell examples because shipping
  iDRACs have self-signed certs. In production fleets, push internal CA
  certs to the iDRAC (via `idrac_certificates`) and switch
  `validate_certs: true` + `ca_path:`.

## Connection mode

All `dellemc.openmanage` modules run over HTTPS from the Ansible
controller to the iDRAC. There is **no `httpapi` connection plugin in
this collection** — `connection: httpapi` will fail. Use
`connection: local` at the play level, or `delegate_to: localhost` on
each task (the upstream `playbooks/idrac/idrac_session.yml` uses the
latter).

`gather_facts: false` is also conventional — the collection's modules
don't need controller facts to run, and `setup` against a BMC inventory
adds latency for nothing.
