# NetBox 4.2 → 4.7 version-delta cheat sheet

The 4.2–4.6 claims were adversarially verified (3-vote panel) against release
notes / docs / source in June 2026; 4.7 claims carry their own labels. Use this
before upgrading NetBox or writing automation that must span versions.

## 4.2 (2025-01-06) — MAC addresses become objects

- MACs moved from interface attributes to first-class `MACAddress` objects:
  multiple per interface, one designated via `primary_mac_address`.
- New endpoint `/api/dcim/mac-addresses/` (assign with
  `assigned_object_type: dcim.interface` or `virtualization.vminterface`).
- The interface `mac_address` field became **read-only** — seed scripts that
  wrote it directly break on 4.2+.
- Source: release-notes/version-4.2, models/dcim/macaddress.

## 4.3 (2025-05-01) — module profiles + Service API break

- **Module Type Profiles** introduced (netbox-community/netbox#19002) — see
  `modeling-gaps.md#module-type-profiles`.
- **BREAKING REST change**: `Service.device`/`virtual_machine` FKs replaced by
  a generic parent — write `parent_object_type` (e.g. `"dcim.device"`) +
  `parent_object_id`; read-only `parent`. Enables services on FHRP groups
  (netbox-community/netbox#8423). Code posting `{"device": id}` gets a 400 with
  "parent_object_type: This field is required."
- Source: release-notes/version-4.3 (Breaking Changes).

## 4.4 (2025-09-02) — VLAN-to-site deprecated

- Direct VLAN→site assignment deprecated (netbox-community/netbox#19738) in favor of **site-scoped
  VLAN groups**; the FK "will be removed in a future release" (still present
  but warned in 4.6). New IPAM guidance: create a VLAN group scoped to the
  site (or location / rack group), assign VLANs to the group.
- Reinforced in 4.5 (VLAN selector defaults to group, netbox-community/netbox#21165) and 4.6
  (RackGroup became a valid VLANGroup scope).

## 4.5 (2026-01-06) — v2 tokens + port-mapping rework

- **v2 API tokens** (netbox-community/netbox#20210): HMAC + cryptographic pepper, no plaintext stored
  server-side. Wire format `Authorization: Bearer nbt_<KEY>.<TOKEN>`
  (12-char public key, 40-char secret). v1 = `Authorization: Token <hex>`.
  Bootstrap flow: `helm-chart-gotchas.md#api-token-bootstrap`.
- **Advanced Port Mappings** (netbox-community/netbox#20564), breaking for cabling automation:
  `FrontPort.rear_port`/`rear_port_position` REMOVED, replaced by a
  `positions` integer + `rear_ports` list through an intermediary
  `PortMapping` model (supports bidirectional/many-to-many mappings, e.g.
  inline fiber-pair swaps). `RearPort` gained `front_ports`.
  - Nuance (4.6.2): the **template** endpoints
    (`/api/dcim/front-port-templates/`) still accepted the legacy
    `rear_port` + `rear_port_position` shape — the rework hit the
    device-level FrontPort model. Don't assume either way; probe the version.
- `User.is_staff` removed (netbox-community/netbox#16137), and with it `REMOTE_AUTH_STAFF_GROUPS` /
  `REMOTE_AUTH_STAFF_USERS`: `is_superuser` is the only role flag. Drop
  `is_staff` from user-seeding code and SSO pipelines (`sso-hardening.md`).
- `/api/dcim/cable-terminations/` became **read-only** — set terminations on
  cables directly via `/api/dcim/cables/`
  (`a_terminations`/`b_terminations` lists of `{object_type, object_id}`).

## 4.6 (2026-05-05) — RackGroup returns, v1 tokens deprecated

- **Flat RackGroup reintroduced** (netbox-community/netbox#20961): a lightweight SECONDARY axis for
  rack organization (rows/aisles), independent of the Location hierarchy —
  `Rack.group` is an optional FK; it does NOT replace Locations. Also a valid
  VLANGroup scope. ("Reintroduced": the original RackGroup became Location
  in 2.11.)
- v2 token plaintext shown **exactly once** at creation (netbox-community/netbox#22062); 4.6.1
  (netbox-community/netbox#22081) made the REST API return the plaintext on creation. Capture it or
  re-provision — there is no later retrieval.
- **v1 tokens formally deprecated** in 4.6.1 (netbox-community/netbox#22128). Removal timeline
  SHIFTED: 4.5 notes said v4.7; 4.6.1 reschedules removal to **v5.0**.
- **`LOGIN_REQUIRED` deprecated** (4.6.0); 5.0 removes it and anonymous access
  with it — move unauthenticated consumers to tokens before 5.0. Every start
  logs a `FutureWarning` while the setting is present; the helm chart always
  renders it (`loginRequired`, default `false`), so the warning is expected
  there. [source: settings.py @v4.6.0, @v4.7.3]
- **`housekeeping` command deprecated** (netbox-community/netbox#21304); removed in 4.7.

## 4.7 (2026-09-02; 4.7.3 2026-10-13) — ltree hierarchies, target 4.7.2+

Upgrade gates and the chart pin map: `SKILL.md` §"Upgrading to 4.7".

Defects in early 4.7 [docs]:

- **netbox-community/netbox#23112** (4.7.0) — the SSO login button does nothing under a restrictive
  `form-action` CSP. 4.7.1 starts the login with `POST /oauth/begin/<backend>/`,
  which returns the IdP URL as JSON for the page script to navigate to.
- **netbox-community/netbox#23130** (4.7.0) — a `pg_dump` of a 4.7.0 database restores without the
  hierarchy cascade triggers; the restore reports success, then renaming or
  moving a parent leaves descendants stale. 4.7.1 reinstalls the triggers but
  does **not** repair stale values — see the "Repairing Hierarchical Paths"
  admin doc.
- **netbox-community/netbox#23196** (4.7.0–4.7.1) — background bulk API requests that create tokens
  record the plaintext in job results, readable by anyone who can view jobs.
  4.7.2 rejects such requests; replace any token created that way.

### After the roll

The image entrypoint runs `migrate` and its usual cleanup, not the extra steps
NetBox's own `upgrade.sh` adds. Run these in the web pod:

1. `manage.py rebuild_config_context_cache` — fills the new config-context
   cache (one `UPDATE` per device/VM; safe to interrupt and re-run). Until it
   runs, objects render config context on demand.
2. Turn the `housekeeping` CronJob off: the command is gone. Chart ≥8.3.77
   defaults `housekeeping.enabled: false`; a values file that pins `true`
   keeps a CronJob running `manage.py housekeeping`, which fails.
3. `manage.py rebuild_ltree_paths --check` — every hierarchical model must
   report OK.
4. Check the SSO login start with a POST (`helm-chart-gotchas.md` §9.5): a GET
   returns 405 on 4.7.

### Moving or restoring a 4.7 database

A `pg_dump | pg_restore` of a 4.7.1+ database keeps every trigger, verified
copying 4.7.3 between two PostgreSQL operators.

- When trimming extensions with `pg_dump --extension=…`, include
  `--extension=ltree`. It is trusted, so `pg_restore --role=<db owner>` creates
  it without a superuser.
- 4.7 keeps hierarchy paths (`<table>_ltree_compute_path` /
  `<table>_ltree_cascade_path` on 11 tables) and denormalized fields
  (`*_denorm_from_*`) in PostgreSQL triggers, not in Python. A restore that
  loses them still reports success. After every restore:
  - diff `SELECT tgrelid::regclass, tgname, pg_get_triggerdef(oid) FROM
    pg_trigger WHERE NOT tgisinternal ORDER BY 1, 2` between source and
    target — it must be identical;
  - in a transaction you roll back, rename a parent location and confirm the
    child's `sort_path` changed;
  - run `manage.py rebuild_ltree_paths --check`.
- Moving between PostgreSQL operators (e.g. Zalando → CloudNativePG): the
  `postgres-operator-cloudnative-pg-migration` skill.

### API and dependency changes

- `ipam.Service` `protocol`/`ports` → `port_mappings`. REST still accepts the
  legacy pair and still returns it on read; read-only at the
  ORM.
- Config context is pre-rendered into every device/VM REST representation;
  `?exclude=config_context` is silently ignored. Drop it with
  `?omit=config_context` (or `?fields=` / `?brief=1`); from 4.7.3 that also
  skips loading it.
- REST token plaintexts are server-generated only; running custom scripts
  needs a write-enabled token.
- social-auth-core 4.8.7 → 5.1.0 (4.7.0) → **5.2.0** (4.7.3);
  social-auth-app-django 5.9.0 → 6.0.1 → **6.1.0**. app-django 6 makes the
  login start POST-only: `GET /oauth/login/<backend>/` returns **405**. The
  OIDC backend defaults are unchanged (PKCE off, RS256 only,
  `preferred_username`, uid from `sub`), so existing `social_auth` rows stay
  valid [source @5.2.0; live 2026-10-27: login start only].

## Anti-facts (plausible, verified FALSE — do not repeat)

- ~~"4.6 lets VMs be assigned directly to a device without a cluster"~~ —
  refuted 3-0. `VirtualMachine.cluster` semantics unchanged; the
  one-cluster-per-device FK for cluster hosts also still holds (a device
  belongs to at most ONE cluster — plan accordingly when a host is both a
  hypervisor and a member of another logical cluster).
- ~~"4.5 removed ALLOW_TOKEN_PEPPERS and disabled token reassignment"~~ —
  refuted 0-3; the verified v2-token facts are only those listed under 4.5/4.6
  above.
