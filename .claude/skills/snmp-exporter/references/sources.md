# Sources — dated provenance index

External sources backing this skill's factual claims. Freshen passes update
`Last verified:` dates after re-probing. Claims in the skill covered by a
recent date here outrank an AI model's training-data memory.

| Claim area | Source | Last verified: |
|---|---|---|
| snmp_exporter v0.30.x behavior, flags, #1653 index rejection, #1066 sensor scaling, #1229 CBS hang | https://github.com/prometheus/snmp_exporter (code + issues) | 2026-07-23 |
| Ready-made vendor modules | https://github.com/prometheus-community/snmp | 2026-07-23 |
| Helm chart v9.16.1 values (configmapReload, extraSecretMounts) | https://github.com/prometheus-community/helm-charts (charts/prometheus-snmp-exporter) | 2026-07-23 |
| iDRAC full-walk 2–5 min reports | https://github.com/prometheus-community/helm-charts/issues/3572 | 2026-07-23 |
| Probe CRD `params` since v0.85.0; ScrapeConfig still v1alpha1 | https://github.com/prometheus-operator/prometheus-operator (releases + docs) | 2026-07-23 |
| iDRAC MIB versions 4.3/4.7, Mib_A00.zip per-firmware downloads (driverids fmd40, kywdc, fwmwv) | https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=fmd40 (and kywdc, fwmwv) | 2026-07-23 |
| iDRAC9 firmware version index | Dell KB 000178115 | 2026-07-23 |
| OpenManage MIB bundle discontinued | Dell KB 000312092 | 2026-07-23 |
| iDRAC v3 breaks after firmware update | Dell KB 000321856 | 2026-07-23 |
| iDRAC10 SNMP defaults (AgentEnable=0, SHA-384/512 + AES-256 only, ProtocolEnable=0, 40-char passphrases) | iDRAC10 Attribute Registry 1.10.05.00 (dell.com support downloads) | 2026-07-23 |
| idrac_exporter metric list, config groups, Helm chart, no-PSU-firmware/no-Connection-View | https://github.com/mrlhansen/idrac_exporter (source, code-verified) | 2026-07-23 |
| idrac_exporter iDRAC10 breakage / 401s | https://github.com/mrlhansen/idrac_exporter/issues/202 and /issues/191 (v2.6.1 current) | 2026-07-23 |
| CBS health OIDs, no-memory-OID, CBS220 fallback | https://github.com/librenms/librenms (mibs/cisco CISCOSB-*, poller includes) + Centreon plugin source | 2026-07-23 |
| CBS SNMPv3 support, common-OID doc, SNMP-crash warning | Cisco CBS 250/350 admin + CLI guides, cisco.com kmgmt3636 | 2026-07-23 |
| Onyx SNMP surface: EFM trap-only, entity-state PSU-only, 60 s cache, engineID reset, v3 protocol set, LTS to April 2029 | NVIDIA Onyx v3.10.4606 LTS User Manual (PDF; login-walled) <!-- ignore-freshen --> | 2026-07-23 |
| Onyx standard-MIB polling pattern | Official Zabbix "Mellanox by SNMP" template | 2026-07-23 |
| IETF/vendor base MIBs (ENTITY*, HOST-RESOURCES, EtherLike, RMON, POWER-ETHERNET) | https://github.com/cisco/cisco-mibs `v2/` @ commit f55dc443 | 2026-07-23 |
| Mellanox MIB mirrors | https://github.com/netdisco/netdisco-mibs (mellanox/, ciscosb/) | 2026-07-23 |
| Trap pipeline: telegraf snmp_trap input (inbound); maxwo/snmp_notifier is outbound-only (Alertmanager→traps) | https://github.com/influxdata/telegraf (plugins/inputs/snmp_trap) + https://github.com/maxwo/snmp_notifier | 2026-07-24 |
| iDRAC SNMP Grafana dashboard 14395 | https://grafana.com/grafana/dashboards/14395 + https://github.com/zorrzoor/grafana-idrac-dashboard | 2026-07-23 |
| UniFi SNMP surface (no LLDP-MIB/RMON/POWER-ETHERNET; ubiquiti_unifi module works) | Live hardware test against USW Pro HD 24 / USW-16-PoE / UAP-nanoHD <!-- ignore-freshen --> | 2026-07-23 |
