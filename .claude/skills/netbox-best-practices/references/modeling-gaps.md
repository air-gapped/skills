# Modeling gaps not covered by the official netboxlabs/skills (as of 2026-06)

Two features the official skill library doesn't document yet, plus one
seeding gotcha. For general hierarchy/tenancy/IPAM modeling, use the official
`netbox-data-modeling` skill instead.

## Module Type Profiles {#module-type-profiles}

Introduced 4.3.0 (#19002). Lets module types carry **typed, schema-validated
attributes by functional classification** — the supported way to inventory
server internals (CPU, RAM, PSU, disks, GPU) without custom fields.

- A module type may optionally be assigned ONE profile. Built-in example
  profiles ship by default (CPU, Fan, GPU, Hard disk, Memory, Power supply,
  Expansion card) — they are editable/removable examples, not fixtures.
- Each profile holds a JSON Schema (json-schema.org) defining the attributes;
  `null` schema = classification-only profile, which is allowed. Types:
  string, integer, decimal, boolean, choice (enum), with defaults/required/
  descriptions.
- Attribute values are set on the module type via the `attributes` field and
  are validated against the profile's schema at write time — enum case
  matters (e.g. a schema with `"enum": ["AC", "DC"]` rejects `"ac"`). [live]
- Discover instance profiles + schemas: `GET /api/dcim/module-type-profiles/`.
- **API gotcha** [live on 4.6.2]: module types have NO slug field — idempotent
  lookups must filter on `manufacturer_id` + `model`, not a slug. A wrong
  filter param can be silently ignored and match everything; verify the
  get-or-create actually discriminates.

Worked example (server inventory):

```
module bays on device "server-01":  psu1, cpu1, dimm-1..8, gpu-1, disk-1
module types:
  "750W Platinum PSU"  profile=Power supply  attributes={"input_current":"AC","input_voltage":230,"wattage":750}
  "EPYC 7551"          profile=CPU           attributes={"architecture":"x86-64","cores":32,"speed":2.0}
  "32GB DDR4-3200"     profile=Memory        attributes={"class":"DDR4","data_rate":3200,"ecc":true,"size":32}
modules: instantiate each type into its bay (serial per module if known)
```

Related placement rules (documented, here for convenience):

- **Device bay vs module bay**: independent management plane → device bay
  (child device, e.g. blade); depends on parent's control plane → module bay
  (line card, PSU, disk). Docs state line cards must NOT be device bays.
- `{module}` placeholder: module-type component templates named e.g.
  `Gi{module}/0/1-48` are renamed with the bay's position on install
  (bay 7 → `Gi7/0/1-48`). Works for interfaces, console/power ports, and
  front/rear port templates.

## 4.5 Port-mapping rework (patch panels)

See `version-deltas.md` §4.5 — `FrontPort.rear_port` is gone in favor of
`PortMapping` (many-to-many, bidirectional). When modeling patch panels on
4.5+, think in terms of front/rear port *pairs via mappings* rather than the
old 1:1 FK. Template endpoints still accepted the legacy shape on 4.6.2;
device-level FrontPort did not.

## Device types are creation-time templates (seeding gotcha)

Component templates (interfaces, ports, bays) instantiate **only at device
creation**. Editing a device type later does NOT retroactively update existing
devices — so in any seed/import pipeline, finalize device types (including
module bay templates and port templates) BEFORE mass-creating devices, or
the fix is hand-patching every existing device afterwards. (Docs: "changes made to a
device type will not apply to instances of that device type retroactively.")
