# NVIDIA/Mellanox Onyx (Spectrum switches: SN2010, SN2100, SN2700…)

Enterprise OID `1.3.6.1.4.1.33049`. Verified against the Onyx v3.10.4606 LTS
User Manual (full PDF), MIB source, and the official Zabbix template, 2026-07.

**Contents:** [The key insight](#the-key-insight) · [Module design decisions & known limitations](#module-design-decisions--known-limitations) · [Operational notes](#operational-notes) · [MIB sources](#mib-sources) · [Alternatives](#alternatives)

## The key insight

**Onyx health lives in STANDARD MIBs, not the private tree.** The `33049` tree
is product identity (sysObjectID: SN2010 = `.33049.1.1.1.2010`), SNMP-SET
actions (power-cycle, sw-update), legacy InfiniBand/EFM objects, and — its real
value — **traps** (asicOverTemp, asicChipDown, insufficientFans,
insufficientPower, procCrash, procUnexpectedExit, internalBusError,
cpuUtilHigh, diskSpaceLow, systemHealthStatus, PSU insert/extract).
A full `33049` walk yields mostly dead BridgeX/VPI noise (measured: 359 junk
metrics). The user manual settles the legacy-table question **officially**:
MELLANOX-EFM-MIB is "partially deprecated — trap definitions and the test-trap
scalar are supported", and MELLANOX-ENTITY-STATE-MIB is "currently supported
for power supply insertion and extraction only". Do not poll `33049.2`
gmVariables tables; they are not served.

Poll instead (= official Zabbix "Mellanox by SNMP" pattern):

| Data | MIB / OID |
|---|---|
| Temperatures | ENTITY-SENSOR-MIB `entPhySensorTable` (1.3.6.1.2.1.99.1.1), type 8 = °C |
| Fan RPM | same table, type 10 = rpm; check `entPhySensorOperStatus` |
| PSU / module state | ENTITY-STATE-MIB `entStateTable` (1.3.6.1.2.1.131.1.1), join ENTITY-MIB `entPhysicalClass` = 6 (powerSupply) |
| CPU load | HOST-RESOURCES `hrProcessorLoad` — use stock `hrDevice` module |
| Memory / disk | HOST-RESOURCES `hrStorageTable` — use stock `hrStorage` module |
| Traffic | IF-MIB ifXTable (`Eth1/1`-style ifName, HC counters reliable) — stock `if_mib` |
| Names for all sensor indexes | lookup `ENTITY-MIB::entPhysicalName` on `entPhysicalIndex` |

Scrape: `module=system,if_mib,hrDevice,hrStorage,mellanox,lldp` (`system` = sysUpTime/reboot detection) where `mellanox` covers
sensors, entity state, component make/model/serial/firmware, and installed
Onyx images (see [examples/generator-mellanox.yml](../examples/generator-mellanox.yml) —
30 metrics, validated).

**Sensor value math**: `entPhySensorValue` must be scaled by
`entPhySensorScale`/`entPhySensorPrecision` — Onyx temps typically precision 1,
i.e. divide by 10 in PromQL or a dashboard, the exporter exports the raw value.
(Auto-scaling is a long-open upstream feature request, snmp_exporter#1066 —
don't wait for it.)

## Module design decisions & known limitations

The `mellanox` module ([examples/generator-mellanox.yml](../examples/generator-mellanox.yml), 30 metrics as of 2026-07-23) is
deliberately thin because CPU/memory/traffic come from stock modules at scrape
time (`module=system,if_mib,hrDevice,hrStorage,mellanox,lldp`). What it covers beyond
sensors/state: per-component **make, model, serial, software/firmware revision**
(entPhysicalMfgName/ModelName/SoftwareRev/FirmwareRev — the chassis row's
SoftwareRev is the Onyx version) and **installed-image inventory**
(mellanoxSWTable: image per partition, active + next-boot partition) — i.e.
switch firmware IS trackable via SNMP here, unlike Dell PSU firmware.

Excluded, and why:

- **BRIDGE-MIB / Q-BRIDGE (MAC table, VLANs)** — cardinality bomb (one row per
  learned MAC); an NMS/topology concern, not metrics.
- **LLDP-MIB** — not in this module, but a shared vendor-neutral `lldp` module
  exists ([examples/generator-custom.yml](../examples/generator-custom.yml)): lldpRemSysName/ChassisId/PortId/PortDesc with
  local-port-name lookup. Add `,lldp` to the scrape's module list as a
  mis-cabling watchdog — a wrong system patched into a port appears as a new
  (port, remote-sysname) series; alert idiom:
  `lldpRemSysName unless (lldpRemSysName offset 1h)`. Full topology mapping
  still belongs in NetBox/LibreNMS.
- **EtherLike-MIB — now walked speculatively** (dot3StatsFCSErrors/
  AlignmentErrors/SymbolErrors + dot3In/OutPauseFrames, ifName-labeled):
  FCS/symbol errors = degrading DAC/optic, pause frames = flow-control
  storms (the classic RoCE congestion signal on Spectrum). Onyx support is
  unverified — an absent subtree costs one empty PDU, so it's walked anyway;
  if the hardware snmpwalk (`1.3.6.1.2.1.10.7.2`) shows it's not served,
  either drop the walks or fall back to mellanoxIfVPITable's FCS counters.
- **mellanoxIfVPITable (33049.3)** — InfiniBand-era port extensions +
  packet-size histograms; ifXTable covers Ethernet needs. Revisit only for IB.
- **33049.2 EFM gmVariables** — officially trap-only on Onyx (manual-verified);
  never poll.
- **33049.10/.12/.13/.15 (power-cycle, config-db, XSTP, QoS)** — SET actions
  and config, not telemetry. The SW-UPDATE *Cmd* objects are likewise actions —
  only the read-only image tables are walked.
- **Traps (EFM/WJH/entity-state)** — snmp_exporter cannot receive them; the
  asicOverTemp/insufficientPower class of events needs a trap receiver, or you
  approximate via the polled sensor/state tables.
- **Full entPhysicalTable** — only 6 columns walked; Descr/VendorType/etc.
  add string bulk without alerting value.
- Remember the polling-side limits from Operational notes: 60 s on-box SNMP
  cache (faster scrapes read stale data) and unverified HOST-RESOURCES support.

## Operational notes

- **SNMP data is cached on-box.** `snmp-server auto-refresh` is enabled by
  default with a **60 s interval** (range 20–500 s; <60 s warns about CPU
  cost), and even with auto-refresh disabled, cached tables refresh at most
  once per 60 s (disable `snmp-server cache` to force live reads). Consequence:
  scraping faster than the refresh interval reads the same cached values —
  set Prometheus `interval` ≥ the auto-refresh interval (60 s), and expect
  counters to advance in refresh-interval steps (use rate() windows ≥ 5×).
- All management (CLI, API, SNMP) runs through one **mgmtd** daemon; NVIDIA KB
  documents overloaded mgmtd making the whole switch unresponsive. Narrow
  walks, moderate intervals (small boxes like SN2010 with 22 ports are cheap).
- Config: `snmp-server enable`, `snmp-server community <c> ro`; v3:
  `snmp-server user admin v3 prompt auth <md5|sha|sha224|sha256|sha384|sha512>
  priv <des|3des|aes-128|aes-192|aes-256|aes-192-cfb|aes-256-cfb>` — the full
  modern protocol set is available; prefer sha256 + aes-128 for exporter
  interop. For aes-192/256, Onyx offers plain and `-cfb` variants — these map
  to the two key-expansion schemes (exporter: AES192/AES256 vs the Cisco/Reeder
  AES192C/AES256C); test which pairing decrypts before rollout.
- **SNMPv3 engine-ID trap**: all units shipped with OS older than 3.6.6102
  share ONE identical engine ID, and upgrading does NOT change it. Duplicate
  engine IDs across switches break v3 USM. Check `show snmp engineID` and fix
  with `snmp-server engineID reset` (SNMP must be disabled during reset).
- **Never configure an `rw` community**: SNMP SET is enabled by default for
  MELLANOX-CONFIG-DB / EFM / POWER-CYCLE — a read-write community means remote
  reboot and config upload via SNMP (`show snmp set-permission`).
- `entPhysicalIndex` values are structured 9/10-digit encodings
  (module-type | module | device | sensor layers; module type 1=chassis,
  5=fan, 6=PSU, 8=x86 CPU, 9=port module) — indexes like `401191311` are
  meaningful, not random; rely on the entPhysicalName lookup for labels.
- **DAC/transceiver serials**: the manual's entity-index scheme explicitly
  includes *cables* as modules, so plugged DACs/optics appear as
  entPhysicalTable rows — meaning `entPhysicalSerialNum` / `MfgName` /
  `ModelName` (all walked by the `mellanox` module) give per-cable serial,
  vendor, and part number, labeled by port-module entity name. This detects
  a swapped/replaced DAC by serial change. Verify row presence on the SN2010
  during the hardware snmpwalk (unverified which fields passive DACs populate).
- The manual documents IF-MIB (ifTable/ifXTable) and ENTITY-MIB explicitly.
  It does NOT mention HOST-RESOURCES-MIB anywhere — the hrProcessor/hrStorage
  recommendation rests on the Zabbix template and LibreNMS behavior; verify
  with one snmpwalk before depending on it.
- JSON API (`json-gw`) is **enabled by default** on supported platforms.
- Quirk: `sysServices=72` makes some NMS auto-classification treat Onyx as an
  application-layer host — irrelevant for snmp_exporter, confusing in LibreNMS.
- **Product status**: Onyx is LTS since Nov 2023, supported to **April 2029**,
  train 3.10.47xx; NVIDIA's direction is Cumulus/SONiC. The MIB surface is
  frozen — a module built now stays valid, but SNMP bugs won't be fixed.
  Same hardware re-imaged with Cumulus/SONiC needs a completely different
  approach (node_exporter-ish / gNMI), not this module.
- Traps are where the private MIBs shine — for asicOverTemp etc.,
  deploy a trap receiver; snmp_exporter won't see them.

## MIB sources

netdisco/netdisco-mibs `mellanox/` (12 files, matches the
`mibs/mellanox/`), observium CE (adds legacy MELLANOX-MIB), NVIDIA's own
Mellanox/ufm_sdk_3.0 repo. MELLANOX-WJH-MIB (What-Just-Happened drop
telemetry) exists only on the login-walled NVIDIA enterprise portal.
ENTITY/ENTITY-SENSOR/ENTITY-STATE/HOST-RESOURCES come from cisco-mibs `v2/`
or net-snmp — remember ENTITY-MIB needs SNMP-FRAMEWORK-MIB to parse.

## Alternatives

ska-sa/switch_exporter (SSH screen-scraping, actively maintained) for per-port
data SNMP can't reach; the Onyx JSON API (x86 models, ≥3.9.0300) has no
published Prometheus exporter.
