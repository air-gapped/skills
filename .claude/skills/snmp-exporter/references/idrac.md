# Dell iDRAC 9 / iDRAC 10 (PowerEdge 14G–17G)

MIB: **IDRAC-MIB-SMIv2**, enterprise root `1.3.6.1.4.1.674.10892.5`
("outOfBandGroup"). Verified against MIB 11.0.1.0 and community practice,
2026-07.

**Contents:** [Out-of-the-box status](#out-of-the-box-status) · [Subtree map](#subtree-map-what-to-walk) · [Per-PSU monitoring](#per-psu-monitoring-multi-psu-chassis-eg-xe9780-with-up-to-12) · [Module design decisions & known limitations](#module-design-decisions--known-limitations) · [Enablement, auth, licensing](#enablement-auth-licensing) · [iDRAC 10 gotchas](#idrac-10-gotchas-early-firmware-field-verified-2026-06) · [MIB acquisition](#mib-acquisition) · [Alternatives / complement: idrac_exporter](#alternatives--complement-idrac_exporter)

## Out-of-the-box status

Upstream snmp_exporter ships a **`dell`** module (walks `10892.5.2` status,
`.5.4` system details, `.5.5` storage — 512 metrics). It works for iDRAC 9 but
walks bulky subtrees (SEL event log, FRU) and misses identity. The upstream
**`dell_rac` module is NOT for iDRAC** — it's DELL-RAC-MIB (`10892.2`), the old
CMC chassis controller (M1000e/VRTX/FX2).

## Subtree map (what to walk)

| OID under 10892.5 | Content | Walk? |
|---|---|---|
| `.1.1` | racInfo: name, firmware version, URL | yes (tiny) |
| `.1.3` | systemInfo: service tag, model, OS | yes (tiny) |
| `.2` | globalSystemStatus, globalStorageStatus, powerState | yes — primary alert source |
| `.4.200` | systemStateTable: per-subsystem rollups incl. SD/IDSDM (iDRAC9) | yes |
| `.4.300.40` | SEL eventLogTable | **no** — log-as-metrics anti-pattern; use Redfish/traps |
| `.4.300.50/.60/.70` | BIOS / firmware / intrusion | yes |
| `.4.600.10/.12/.20/.30/.50/.60` | powerUnit redundancy / PSUs / voltage probes / amperage probes / CMOS battery / powerUsage | yes |
| `.4.700.10/.12/.20` | coolingUnit (fan redundancy) / fans / temperature probes | yes |
| `.4.1100.30/.32/.50/.90` | CPU inventory / CPU status / memory DIMMs / NICs (status, MAC, product) | yes |
| `.4.2000.10` | fruTable: per-FRU manufacturer, part no, serial, revision (covers PSUs, DIMMs) | yes — PSU make/serial tracking |
| `.4.1100.80`, `.4.1200`, `.4.300.10` | PCI inventory, slots, chassisInformation | **no** — static inventory, fru/systemInfo cover the useful parts |
| lcLogTable | Lifecycle log (SNMPv3-only) | **no** — unbounded log data |
| `.5.1.20.130.1/.15/.130.4/.140.1` | RAID controller / controller battery (BBU) / physical disks / virtual disks | yes |
| `.5.x` enclosure tables (5) | external SAS enclosure, fans, PSUs, temps, EMMs | yes — empty rows on servers without JBODs |

A **full `10892.5` walk takes 2–5 minutes** on real iDRACs and blows any sane
scrape_timeout (prometheus-community/helm-charts#3572). The curated module in
[examples/generator-idrac.yml](../examples/generator-idrac.yml) implements the table above
with LocationName/diskName lookups; 449 metrics, dry-run validated.

Index naming quirk: chassis indexes are lowercase-c `<table>chassisIndex`
(e.g. `temperatureProbechassisIndex`) — EXCEPT `fruChassisIndex` (capital C);
storage tables use `controllerNumber`, `physicalDiskNumber`,
`virtualDiskNumber`. Lookup columns: `*LocationName`, `powerUnitName`,
`fruFQDD`, `controllerName`, `physicalDiskName`, `virtualDiskDisplayName`.

## Per-PSU monitoring (multi-PSU chassis, e.g. XE9780 with up to 12)

Every PSU is its own row, labeled via `powerSupplyLocationName` ("PS1 Status"…):

- `powerSupplyTable`: status enum, sensor state, IsOK/IsON flags, output watts
  (tenths), rated input wattage, current input voltage,
  `powerSupplyConfigurationErrorType` (catches mismatched/wrong-revision PSUs
  when mixing vendors), FQDD, redundancy linkage.
- `powerUnitTable.powerUnitRedundancyStatus`: the single full/degraded/lost
  redundancy rollup — the primary PSU alert on multi-PSU boxes.
- `amperageProbeTable` / `voltageProbeTable`: per-PSU current ("PS1 Current 1",
  tenths of amps) and voltage probes with thresholds — shows load balance.
- `fruTable`: per-PSU **manufacturer, part number, serial, revision**
  (LiteOn vs Delta etc.), labeled by `fruFQDD` (e.g. `PSU.Slot.7`).
- **PSU firmware version is NOT exposed via SNMP** — firmwareTable's type enum
  only covers iDRAC/Lifecycle Controller. PSU firmware needs Redfish
  (idrac_exporter) or `racadm get`. Plan PSU-firmware compliance tracking
  outside snmp_exporter.

## Module design decisions & known limitations

The curated `idrac` module ([examples/generator-idrac.yml](../examples/generator-idrac.yml), 449 metrics as of 2026-07-23)
walks 28 of the MIB's 33 tables. Decisions a future editor should know:

- **Not available via SNMP at all**: PSU firmware versions (firmwareTable only
  covers iDRAC/LC — and note idrac_exporter does NOT export PSU firmware
  either; it only exists in the Redfish firmware inventory, via
  `racadm swinventory` or Redfish UpdateService);
  NIC transceiver/DAC EEPROM data (serials, DDM) — networkDeviceTable stops at
  NIC-level status/MAC/product; transceiver inventory needs Redfish
  (NetworkAdapter/Port schemas on recent firmware) or the switch-side entity
  table; **iDRAC Connection View** (the per-NIC "which switch + port am I
  cabled to" shown in the iDRAC UI, learned from switch LLDP) — verified
  absent from the MIB (no SwitchConnectionID/LLDP objects); it IS available
  via `racadm hwinventory` (NICView SwitchConnectionID/SwitchPortConnectionID),
  WSMAN DCIM_NICView, and Redfish Dell OEM network-port resources; anything in
  lcLogTable without v3.
- **Cabling-verification direction matters**: Connection View works because
  *switches* transmit LLDP. The reverse — our switch-side `lldp` watchdog
  module seeing *servers* — only works if the server transmits LLDP too
  (OS lldpd/NIC firmware agent; not on by default). For server-facing ports,
  either run lldpd on hosts to make the switch-side watchdog complete, or pull
  Connection View via Redfish per server.
- **Excluded on purpose**: eventLogTable + lcLogTable (unbounded log rows as
  metrics — use Redfish/syslog/traps for SEL), pCIDeviceTable, systemSlotTable,
  chassisInformationTable (static inventory; fruTable + systemInfo already
  carry serials/part numbers/model).
- **Enums export as raw numbers** (3=ok, 4=nonCritical, 5=critical for
  ObjectStatus-style enums) — no EnumAsStateSet overrides, deliberately: on a
  module this wide it would multiply series count. Map values in
  dashboards/alert rules; flip individual metrics to EnumAsStateSet only if a
  specific alert needs label-based states.
- **Walk cost**: at ~449 metrics the walk is substantial for a BMC. Watch
  `snmp_scrape_walk_duration_seconds` on first deployment; keep Prometheus
  scrape_timeout ≥ 30-60s (module timeout 5s × retries 2 = 15s worst-case per
  PDU). If a slow iDRAC needs trimming, drop in this order: enclosure tables
  (empty anyway without JBODs), processorDeviceTable, networkDeviceTable,
  fruTable — never the status/thermal/power/storage-health tables.

## Enablement, auth, licensing

- iDRAC 9: SNMP agent **enabled by default** (`iDRAC.SNMP.AgentEnable=1`),
  community `public`, UDP 161. SNMP gets+traps are included at **every**
  license tier (Basic → Datacenter) — no Enterprise license needed.
- iDRAC 10: same OIDs, all three tiers (Core/Enterprise/Datacenter) include
  SNMP, **but the agent ships DISABLED** — `iDRAC.SNMP.AgentEnable` default is
  0 (verified in the iDRAC10 Attribute Registry 1.10.05.00). Enable with
  `racadm set iDRAC.SNMP.AgentEnable 1`. `iDRAC.SNMP.SNMPProtocol` defaults to
  "All" (v1/v2c/v3), so v2c gets DO still work once enabled; set it to
  "SNMPv3" (1) to lock down. Agent community default "public", port 161.
- SNMPv3 crypto differs by generation — configs must match exactly:
  - **iDRAC 9**: auth MD5/SHA(-1), priv DES/AES-128 → exporter
    `auth_protocol: SHA, priv_protocol: AES`.
  - **iDRAC 10**: auth **None/SHA-384/SHA-512 only** (default SHA-384), priv
    **None/AES-256 only** (default AES-256) — no MD5, SHA-1, SHA-256 or
    AES-128 at all → exporter `auth_protocol: SHA384` (or SHA512),
    `priv_protocol: AES256` (try `AES256C` if decryption fails — the registry
    doesn't say which key-expansion variant Dell uses). Per-user
    `iDRAC.Users.ProtocolEnable` (SNMPv3) also defaults to 0 — enable it, and
    note passphrases max 40 chars.
  Sensitive tables (lcLogTable) are v3-only by design. Lockout: >6 v3 auth
  failures in 2 min blocks all v3 for 10 min — don't hammer retries. Known
  Dell KB 000321856: v3 breaks after some firmware updates (re-save the user
  config). iDRAC10's read-only `iDRAC.SNMP.EngineID` for v3 traps shows a
  constant-looking default (`0x800002A2040102...09`) — if ever doing v3
  traps, set `CustomEngineID` per host.
- Set Prometheus `scrape_timeout: 30s`+ for iDRAC jobs; module
  `timeout: 5s, retries: 2` keeps worst-case per-PDU cost at 15 s.

## iDRAC 10 gotchas (early firmware, field-verified 2026-06)

- SNMP engine hang under fast walks (fixed in later firmware — keep current).
- GETNEXT illegally skips some subtrees (virtualDiskTable) — if virtual-disk
  metrics vanish on iDRAC 10 but answer to direct GETs, it's this bug.
- Storage global health may report "other" instead of "ok" — don't alert on
  `!= ok`, alert on explicit bad states.
- CMOS battery metrics (systemBatteryTable) were **removed** on iDRAC 10.
- iSM (iDRAC Service Module) can make the SNMP agent slow/deaf — if scrapes
  degrade after OS provisioning, try stopping the in-OS iSM service.

## MIB acquisition

The consolidated "Dell OpenManage MIBs" package is **discontinued** (final
v11.1.0, Dell KB 000312092). Current MIBs are a separate small download on each
iDRAC firmware's driver-details page: look for `iDRAC_<ver>_Mib_A00.zip`
(~113 KB; contains iDRAC-SMIv2.mib, iDRAC-SMIv1.mib, dellrac.mib,
DcAsfSrv.mib). Worked path (2026-07): any 17G product page →
Drivers & Downloads → "iDRAC <ver>" row → details
(`dell.com/support/home/en-us/drivers/driversdetails?driverid=<dup-id>`, e.g.
`fmd40` for iDRAC10 1.30.31.10, `kywdc` for iDRAC9 7.20.80.50, `fwmwv` for
7.00.00.184) → the Mib zip's dl.dell.com URL downloads without the Akamai
wall. Note dell.com support pages 403 curl/headless browsers — use a headed
browser or WebFetch; dl.dell.com itself is open. Dell KB 000178115 is the
canonical iDRAC9 firmware version index (with per-version driverids).

MIB version map (verified 2026-07):

| Source | MIB version | Notes |
|---|---|---|
| iDRAC9 14G branch (7.00.00.184, Apr 2026) | 4.3 (12 Dec 2024) | identical file to the 15/16G branch |
| iDRAC9 15/16G branch (7.20.80.50, Dec 2025) | 4.3 (12 Dec 2024) | **superset**: includes SD-card/IDSDM status objects |
| iDRAC10 (1.30.31.10, Jun 2026) | 4.7 (15 May 2026) | drops SD/IDSDM objects, fixes enum-0 definitions; no new tables |
| Discontinued OM bundle / upstream pinned zip | 4.3 (21 May 2024) | stale build of 4.3 |

For one module serving both generations, **generate from iDRAC9's 4.3
(Dec 2024)** — it's the superset; iDRAC10 targets simply return nothing for
the SD/IDSDM OIDs. The firmware release-notes files bundled on download pages
are pointer stubs; real per-version fix lists live at dell.com/idracmanuals
under each series' Manuals section. iDRAC9 firmware branches: 14G stays on
7.00.00.x maintenance; 15/16G track 7.20.x.

## Alternatives / complement: idrac_exporter

**mrlhansen/idrac_exporter** (Redfish/HTTPS, port 9348) is the same
multi-target `?target=&auth=` pattern as snmp_exporter — same Probe/
ScrapeConfig wiring applies. Also covers iLO/XClarity/Supermicro. Run it
ALONGSIDE the SNMP module for what SNMP can't see (verified against its
metric list 2026-07): `idrac_storage_drive_life_left_percent` (SSD wear),
storage-controller firmware label + cache health, PSU input watts/efficiency,
min/max/avg power stats, SEL entries as metrics, memory serials, airflow CFM.
It does NOT export Connection View or PSU firmware (code-verified against https://github.com/mrlhansen/idrac_exporter source, 2026-07: no
LLDP/SwitchConnection code; FirmwareVersion only for storage controllers,
manager, PDUs) — and it lacks PSU make/serial labels, redundancy rollups,
intrusion, and enclosure health, so it cannot replace the SNMP module.
Caveats: on-demand Redfish collection can take minutes with all metric groups
on — enable only needed groups and raise scrape_timeout; needs a dedicated
read-only iDRAC user.

**Known idrac_exporter issues (checked 2026-07-23, v2.6.1):**
- **iDRAC 10 / 17G largely broken** (issue #202, open): on R470-R7725-class
  boxes `/redfish/v1/Chassis/` returns two members (an internal RAID enclosure
  + System.Embedded.1) and the exporter picks the first — power supply, power
  control, fan, and network metrics come back empty on iDRAC 10. Dell also
  moved PSU metrics to the modern Sensors collection
  (`.../Sensors/PSU.Slot.1_OutputPower`) and deprecated old chassis endpoints.
  A fix is in progress (commit "potential fix for #202", unreleased) — until a
  release ships, the Redfish enrichment layer is effectively
  **iDRAC 9-only for power/fan/network**; the SNMP module is unaffected on
  iDRAC 10 and remains the source of truth there.
- Sporadic **401 Unauthorized on iDRAC 9** since v2.3.2 (issue #191, open,
  cause unknown, maintainer can't reproduce) — if hit, set
  `use_basic_auth: true` for the affected hosts as a workaround.

Deployment conveniences (from the repo): every config option has a
CONFIG_* env var — in k8s, set CONFIG_DEFAULT_USERNAME/PASSWORD from a Secret
and skip config-file mounting entirely; config group keys are exactly
`processors system sensors power events storage memory network manager extra`
(never `all: true` in production); the `events` group has severity/maxage
filters (`severity: warning, maxage: 7d`) — use them for the SEL layer;
in-repo Helm chart (charts/idrac-exporter) plus ready-made Grafana dashboards
AND alert rules (grafana/idrac.json, idrac_overview.json, alerts.yaml) —
start from those instead of writing alerts from scratch.

**Recommended split (decision 2026-07-23)** — run both with distinct jobs:
- SNMP `idrac` module: primary/fast layer (~60 s) — everything alerted on
  (health, thermal, PSU status + redundancy + mismatch, storage health,
  intrusion, FRU identity).
- idrac_exporter: slow enrichment layer (5-15 min) with ONLY the groups SNMP
  can't provide (`storage` for drive wear/cache, `power` for efficiency +
  min/max/avg, `events` for SEL) — not `all: true`.
- Each alert condition lives in exactly one system: hardware-failure alerts
  from SNMP only; Redfish alerts only on its unique data (drive wear, SEL
  severity). Prevents double paging.
Grafana dashboards for the SNMP path: 14395 (companion repo
zorrzoor/grafana-idrac-dashboard has a proven curated generator.yml).
