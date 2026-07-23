# Ubiquiti UniFi (live-tested 2026-07-23)

Tested against real gear (USW Pro HD 24, USW-16-PoE, UAP-nanoHD, fw 6.x/7.x)
with the stock exporter modules — the only vendor in this skill verified on
hardware so far.

## What works

- SNMP is a **site-wide setting** in the UniFi controller (Settings → System →
  SNMP; v1/v2c community, or v3) — one toggle covers every adopted device.
- **`module=system,if_mib`** works perfectly: 28-port switch = 1121 PDUs in
  0.44 s, full ifXTable HC counters, sysUpTime accurate (cross-checked against
  controller uptime).
- **Upstream's `ubiquiti_unifi` module** (UBNT-UniFi-MIB) works on APs:
  model/version/uptime plus per-VAP wireless tables (194 PDUs, 0.17 s on a
  nanoHD). It's AP-oriented; on switches it adds little.
- Recommended scrape: APs `module=system,if_mib,ubiquiti_unifi`; switches
  `module=system,if_mib`.

## What does NOT work (verified empty, not assumed)

UniFi's SNMP surface is narrow — MIB-2 + UBNT private MIBs only:

- **No LLDP-MIB** (0 PDUs) — devices run LLDP (the controller shows
  neighbors) but don't expose the standard MIB. The `lldp` watchdog module
  does not apply; get topology from the controller API instead
  (`lldp_neighbor` in device port tables).
- **No RMON etherStats, no POWER-ETHERNET-MIB** (0 PDUs on a PoE switch) —
  PoE budget/per-port power and error taxonomy exist only in the controller
  API.
- Practical consequence: for UniFi fleets, SNMP gives traffic + uptime; the
  richer data (PoE, LLDP, client/RF stats) needs a controller-API exporter
  (e.g. unpoller) — same "SNMP for the base, API exporter for the rest"
  pattern as the iDRAC/Redfish split.

## Validation notes for this skill (why this file exists)

The live test confirmed several skill claims: multi-module scrapes work in one
request; absent subtrees are cheap (5 empty LLDP walks = 92 ms, 23 empty
CISCOSB/RMON walks = 0.49 s); and the failure-mode table's "empty result =
device doesn't implement those OIDs" diagnosis path is exactly what
distinguishes UniFi's missing MIBs from an auth failure (which looks like a
timeout instead).
