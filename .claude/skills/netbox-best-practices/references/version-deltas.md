# NetBox 4.2 → 4.6 version-delta cheat sheet

Every claim below was adversarially verified (3-vote panel) against release
notes / docs / source in June 2026. Use this before upgrading NetBox or
writing automation that must span versions.

## 4.2 (2025-01-06) — MAC addresses become objects

- MACs moved from interface attributes to first-class `MACAddress` objects:
  multiple per interface, one designated via `primary_mac_address`.
- New endpoint `/api/dcim/mac-addresses/` (assign with
  `assigned_object_type: dcim.interface` or `virtualization.vminterface`).
- The interface `mac_address` field became **read-only** — seed scripts that
  wrote it directly break on 4.2+.
- Source: release-notes/version-4.2, models/dcim/macaddress.

## 4.3 (2025-05-01) — module profiles + Service API break

- **Module Type Profiles** introduced (#19002) — see
  `modeling-gaps.md#module-type-profiles`.
- **BREAKING REST change**: `Service.device`/`virtual_machine` FKs replaced by
  a generic parent — write `parent_object_type` (e.g. `"dcim.device"`) +
  `parent_object_id`; read-only `parent`. Enables services on FHRP groups
  (#8423). Code posting `{"device": id}` gets a 400 with
  "parent_object_type: This field is required."
- Source: release-notes/version-4.3 (Breaking Changes).

## 4.4 (2025-09-02) — VLAN-to-site deprecated

- Direct VLAN→site assignment deprecated (#19738) in favor of **site-scoped
  VLAN groups**; the FK "will be removed in a future release" (still present
  but warned in 4.6). New IPAM guidance: create a VLAN group scoped to the
  site (or location / rack group), assign VLANs to the group.
- Reinforced in 4.5 (VLAN selector defaults to group, #21165) and 4.6
  (RackGroup became a valid VLANGroup scope).

## 4.5 (2026-01-06) — v2 tokens + port-mapping rework

- **v2 API tokens** (#20210): HMAC + cryptographic pepper, no plaintext stored
  server-side. Wire format `Authorization: Bearer nbt_<KEY>.<TOKEN>`
  (12-char public key, 40-char secret). v1 = `Authorization: Token <hex>`.
  Bootstrap flow: `helm-chart-gotchas.md#api-token-bootstrap`.
- **Advanced Port Mappings** (#20564), breaking for cabling automation:
  `FrontPort.rear_port`/`rear_port_position` REMOVED, replaced by a
  `positions` integer + `rear_ports` list through an intermediary
  `PortMapping` model (supports bidirectional/many-to-many mappings, e.g.
  inline fiber-pair swaps). `RearPort` gained `front_ports`.
  - Nuance [live on 4.6.2]: the **template** endpoints
    (`/api/dcim/front-port-templates/`) still accepted the legacy
    `rear_port` + `rear_port_position` shape — the rework hit the
    device-level FrontPort model. Don't assume either way; probe the version.
- `/api/dcim/cable-terminations/` became **read-only** — set terminations on
  cables directly via `/api/dcim/cables/`
  (`a_terminations`/`b_terminations` lists of `{object_type, object_id}`).

## 4.6 (2026-05-05) — RackGroup returns, v1 tokens deprecated

- **Flat RackGroup reintroduced** (#20961): a lightweight SECONDARY axis for
  rack organization (rows/aisles), independent of the Location hierarchy —
  `Rack.group` is an optional FK; it does NOT replace Locations. Also a valid
  VLANGroup scope. ("Reintroduced": the original RackGroup became Location
  in 2.11.)
- v2 token plaintext shown **exactly once** at creation (#22062); 4.6.1
  (#22081) made the REST API return the plaintext on creation. Capture it or
  re-provision — there is no later retrieval.
- **v1 tokens formally deprecated** in 4.6.1 (#22128). Removal timeline
  SHIFTED: 4.5 notes said v4.7; 4.6.1 reschedules removal to **v5.0**.

## Anti-facts (plausible, verified FALSE — do not repeat)

- ~~"4.6 lets VMs be assigned directly to a device without a cluster"~~ —
  refuted 3-0. `VirtualMachine.cluster` semantics unchanged; the
  one-cluster-per-device FK for cluster hosts also still holds (a device
  belongs to at most ONE cluster — plan accordingly when a host is both a
  hypervisor and a member of another logical cluster).
- ~~"4.5 removed ALLOW_TOKEN_PEPPERS and disabled token reassignment"~~ —
  refuted 0-3; the verified v2-token facts are only those listed under 4.5/4.6
  above.
