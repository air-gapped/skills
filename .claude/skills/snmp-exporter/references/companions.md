# Companion components — adopt, don't author

The snmp_exporter modules in this skill cover polling. These free components
cover the layers above and below it. Be opinionated about the wiring, not
about rebuilding them.

## Alert rules

Start from [examples/alerts.yml](../examples/alerts.yml) (opinionated pack for
these modules, enum values cited inline). Cross-check against
**samber/awesome-prometheus-alerts** (hardware/SNMP sections) and, for the
Redfish layer, **mrlhansen/idrac_exporter's `grafana/alerts.yaml`**. Keep the
one-alert-one-system rule: hardware-failure alerts fire from the SNMP layer;
Redfish alerts only on its unique data (drive wear, SEL).

## SNMP traps → Alertmanager (inbound)

snmp_exporter cannot receive traps, and some events are trap-only (Onyx
asicOverTemp/insufficientPower/procCrash, iDRAC alert traps, CBS traps).

**Direction trap (verified 2026-07-24): everything named "snmp notifier" or
"webhook-snmp" in the Prometheus ecosystem goes the OPPOSITE way** —
maxwo/snmp_notifier, SUSE/prometheus-webhook-snmp, and the
webhook-snmptrapper forks all relay *Alertmanager alerts out as traps* for a
legacy NMS. Do NOT deploy them as trap receivers; they cannot ingest device
traps.

Working inbound options:

- **Telegraf `snmp_trap` input plugin** (in influxdata/telegraf since v1.13,
  actively maintained) listening on UDP/162, paired with its
  `outputs.prometheus_client` — traps become scrapeable metrics to alert on.
  Point Telegraf's MIB path at the vendor trap MIBs (MELLANOX-EFM-MIB,
  IDRAC-SMIv2 trap definitions) for readable field names.
- **snmptrapd + `traphandle` script** POSTing to Alertmanager's
  `/api/v2/alerts` — no extra component, but the script and its alert
  lifecycle (resolve/expiry via `endsAt`) are yours to own.

Kubernetes note either way: traps are unsolicited inbound — unlike polling
this DOES need a stable reachable entry point (LoadBalancer IP, hostPort on
pinned nodes, or an ingress node) for UDP/162. Configure device trap targets:
Onyx `snmp-server host <ip> traps`, iDRAC SNMPAlert destinations, CBS trap
receivers.

Keep maxwo/snmp_notifier in mind only for the reverse need: forwarding
Prometheus alerts *to* a legacy SNMP-based NMS.

## Reachability discrimination: blackbox_exporter ICMP

Probe every SNMP target with a blackbox ICMP module under a `blackbox-icmp`
job whose `instance` labels match the SNMP job's. This turns "SNMP down" into
two distinct alerts (see examples/alerts.yml): device down (ping+SNMP both
dead) vs **SNMP agent wedged** (ping OK, SNMP dead) — the latter is a
documented CBS failure mode requiring an agent bounce, not an RMA.

## Targets from NetBox (source of truth)

Don't hand-list targets in Probe CRDs beyond the first handful. NetBox can
feed Prometheus via HTTP service discovery (several maintained integrations
exist — e.g. netbox-prometheus-sd style file_sd/http_sd exporters, or a small
export template on the NetBox side) → ScrapeConfig CRD with `httpSDConfigs`
and the standard `__param_target` relabeling. Drive `module` and `auth`
selection from NetBox custom fields (device role/platform → module list).

Second-order win: export **intended topology** from NetBox cable records as a
static metric (`expected_neighbor{instance,port,sysname} 1` via file), then
upgrade the LLDP watchdog from "new neighbor appeared" to "neighbor differs
from intended": `lldpRemSysName unless on(instance, port...) expected_neighbor`.

## Dell fleet firmware: OpenManage Enterprise (free)

PSU firmware and fleet-wide firmware compliance are invisible to SNMP and to
idrac_exporter. **Dell OpenManage Enterprise** (free virtual appliance) does
firmware baselines/compliance and rollouts for PowerEdge natively, and can be
the Dell trap receiver. Use it for the firmware-inventory problem; keep
Prometheus for metrics. (Per-server ad hoc: `racadm swinventory` or Redfish
UpdateService firmware inventory.)

## Dashboards

Grafana 14395 (iDRAC SNMP; companion repo zorrzoor/grafana-idrac-dashboard),
idrac_exporter's `grafana/*.json` for the Redfish layer, generic
interface dashboards for if_mib. No CBS or Onyx dashboards existed publicly
as of 2026-07 — building on top of these modules is greenfield.

## CI regression fixtures: snmpsim

When doing the hardware-verification snmpwalks, capture full walks
(`snmpwalk -ObentU -v2c -c <comm> <ip> .1 > <model>.snmpwalk`) and keep them
next to the skill as fixtures. Replay with snmpsim in CI: every module change
is then regression-tested against real device behavior without hardware.
This also permanently settles the "does device X answer OID Y" questions.

## Keeping this skill fresh

This skill embeds dated claims (versions, open issues, CRD maturity). Run a
freshen pass periodically (or on the Backlog triggers in SKILL.md): check
snmp_exporter and idrac_exporter releases, idrac_exporter#202, and
prometheus-operator CHANGELOG, then update the affected reference files.
