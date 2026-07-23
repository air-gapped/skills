# Cisco CBS250/CBS350 (and Catalyst 1200/1300 successors)

CBS small-business switches do **not** implement classic Cisco enterprise MIBs
(CISCO-PROCESS-MIB, CISCO-MEMORY-POOL, CISCO-ENVMON) — upstream's
`cisco_device` module is useless here. They use the **CISCOSB** private MIBs
(ex-Linksys/Marvell "RADLAN"), root `switch001 = 1.3.6.1.4.1.9.6.1.101`.
Verified against MIB source + LibreNMS/Centreon pollers, 2026-07.

## Hard facts to not re-learn

- **No memory-utilization OID exists at all** on CBS250/350. Don't look for it;
  plan dashboards without it.
- **CBS220 does not implement the CISCOSB private tree** (LibreNMS ships an
  explicit fallback). CBS220 = IF-MIB + ENTITY-MIB + 4 RMON groups only.
- **SNMP is disabled by default.** Enable: web UI Advanced view → SNMP, or CLI
  `snmp-server server` + `snmp-server community <c> ro`. The community binds to
  a *view* — if the view excludes `1.3.6.1.4.1`, private-tree walks silently
  return nothing.
- **SNMPv3 is fully supported** (users/groups/views model; Cisco publishes
  dedicated CBS SNMPv3 docs incl. kmgmt3636 common-OIDs). Recent 3.x firmware
  offers SHA256 auth + AES-128 privacy (CLI-guide example output shows exactly
  that pair); older firmware may only offer MD5/SHA — match the exporter
  `auth_protocol` to whatever the device user was created with.
- Cisco itself warns that excessive/complex SNMP queries can **crash the CBS
  SNMP process** (community reports: SNMP goes deaf until reboot). Never walk
  the full `9.6.1.101` tree (measured here: 4034 generated metric definitions,
  hung scrapes; the full-walk report in snmp_exporter#1229 counted 5223 — same
  failure, different counting method); scrape at moderate intervals (60 s+).
- EOL: rolling end-of-sale notices through 2024; successors **Catalyst
  1200/1300 share the CISCOSB SNMP surface** (Cisco publishes a joint OID doc,
  kmgmt3636) — a CBS module carries over.

## Health OIDs (all cross-verified LibreNMS + Centreon + MIB source)

| Metric | OID | Notes |
|---|---|---|
| CPU last second/minute/5min | `.101.1.7.0` / `.101.1.8.0` / `.101.1.9.0` | INTEGER 0–101; **101 = "not measured"** — filter it |
| Fan state | `.101.83.1.1.1.3` (rlEnvMonFanState) | enum: 1 normal … 5 notPresent, 6 notFunctioning |
| PSU state | `.101.83.1.2.1.3` (rlEnvMonSupplyState) | same enum |
| Temperature | `.101.83.5.1.1.2` (rlEnvFanDataTemp) | actually the CPU temp; **0 = no sensor** |
| Fan RPM | `.101.83.5.1.1.3` | 0 on fanless models |
| PSU status + temp per stack unit | `.101.53.15` (rlPhdUnitEnvParamTable) | includes warning threshold column |
| Inventory | `.101.53.14` (rlPhdUnitGenParamTable) | .1.2 sw ver, .1.5 serial, .1.7 service tag, .1.11 model |
| Stack | `.101.107` (CISCOSB-STACK-MIB) | unit IDs, mode, chain/ring topology |
| PoE per-port power | `.101.108.1.1.5` (rlPethPsePortOutputPower) | milliwatts, index = stackUnit.ifIndex |
| PoE budget/status | POWER-ETHERNET-MIB `pethMainPseTable` (1.3.6.1.2.1.105.1.3) | total power, consumption, usage threshold — the "budget nearly exhausted" alert; plus per-port `pethPsePortDetectionStatus`/`PowerClassifications` |
| Per-port error taxonomy | RMON `etherStatsTable` columns (CRCAlign, fragments, jabbers, collisions, under/oversize) | distinguishes bad cable/DAC (CRC/fragments) from duplex/congestion (collisions); finer than ifInErrors. etherStatsIndex normally == ifIndex — verify on hardware |

Traffic: plain **IF-MIB ifXTable works fine** — use the stock `if_mib` module.
Recommended scrape: `module=system,if_mib,cisco_cbs,lldp` — `system` carries
sysUpTime (reboot detection; not in if_mib since v0.28), `lldp` is the shared
mis-cabling watchdog module in
[examples/generator-custom.yml](../examples/generator-custom.yml).

**DAC/SFP serials: probably NOT via SNMP on CBS** — its ENTITY-MIB population
is thin (chassis-level only, per LibreNMS) and no CISCOSB transceiver-EEPROM
table is known; the CLI (`show fiber-ports optical-transceiver`) shows DDM for
optics but often nothing for passive DACs. Verify once with
`snmpwalk ... 1.3.6.1.2.1.47.1.1.1.1.11` (entPhysicalSerialNum) on a CBS with
DACs plugged; expect absence.

MIB module names (file → module): CISCOSBmng.mib → `CISCOSB-rndMng`,
CISCOSBenv_mib.mib → `CISCOSB-HWENVIROMENT` (Cisco's typo, keep it),
CISCOSBphysdescription.mib → `CISCOSB-Physicaldescription-MIB`,
CISCOSBstack.mib → `CISCOSB-STACK-MIB`, CISCOSBpoe.mib → `CISCOSB-POE-MIB`.

## Generator gotchas

- **Numeric CISCOSB walks can silently generate nothing**: walking
  `1.3.6.1.4.1.9.6.1.101.83`/`.101.107` numerically produced ZERO metrics in a
  mixed MIB directory (overlapping arc definitions confuse node resolution) —
  generation "succeeded" with env and stack metrics simply absent. The same
  tables by name (`CISCOSB-HWENVIROMENT::rlEnvMonFanStatusTable`,
  `CISCOSB-STACK-MIB::rlStackActiveUnitIdTable`, …) work. Use MIB::name walks
  and always grep the generated file for expected metric names.
- The CISCOSB MIB dump has parse errors in files this module never touches (CISCOSBsnmp,
  VLAN/routing MIBs missing IETF imports). Fetch the missing IETF base MIBs
  (SNMP-FRAMEWORK, INET-ADDRESS, IP-MIB, BRIDGE-MIB — cisco/cisco-mibs `v2/`
  has them all), then `--no-fail-on-parse-errors` for the rest.
- Some rl* tables use InetAddress-without-type indexes; post-v0.30.1 the
  generator rejects them automatically — none are worth walking anyway.
- MIB source: NOT in cisco/cisco-mibs. Official = per-firmware bundle on
  software.cisco.com (login). Best mirror: **librenms/librenms
  `mibs/cisco/CISCOSB-*`** (~60 curated files); netdisco-mibs `ciscosb/` too.

## Worked module

[examples/generator-cisco.yml](../examples/generator-cisco.yml): curated `cisco_cbs` module
(63 metrics vs 4034 full-tree): CPU, env, full inventory (sw/boot/hw versions,
serial, service tag, model), stack, PoE (vendor mW + RFC 3621 budget/status),
RMON error taxonomy; fan/PSU Descr lookups; dry-run validated. Hardware-verify:
whether peth* and etherStats* answer on owned models, and the
etherStatsIndex↔ifIndex mapping.
No published snmp_exporter CBS module or Grafana dashboard existed as of
2026-07 — this is genuinely novel; consider contributing to
prometheus-community/snmp.
