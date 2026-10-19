# Sources

Freshened: 2026-09-22 — every row probed (exception: the Dell driver page 403s to every fetcher, as already noted). snmp_exporter v0.30.1 is unchanged, but idrac_exporter#202 closed 2026-08-04 with a real fix in v2.6.2 — the body still described it as open and unreleased, contradicting this file's own v2.6.3 pin.

**Exception — 1 row:** the iDRAC10 SNMP defaults (AgentEnable, SHA/AES ciphers, passphrase length) come from a login-walled Dell Attribute Registry PDF and were not re-opened this pass. No contradicting source surfaced. — dated provenance index

External sources backing this skill's factual claims. Freshen passes update
`Last verified:` dates after re-probing. Claims in the skill covered by a
recent date here outrank an AI model's training-data memory.

| Claim area | Source | Last verified: |
|---|---|---|
| snmp_exporter v0.30.x behavior, flags, #1653 index rejection, #1066 sensor scaling, #1229 (full `9.6.1.101` generator config = 5223 metrics; a generator-error report, not a hang report) | https://github.com/prometheus/snmp_exporter (code + issues) | 2026-09-15 |
| `--config.expand-environment-variables` expands username/password/priv_password of every auth in every loaded file via `os.Expand(value, os.Getenv)`, erroring only when the whole result is empty (embedded unset `$var` → silently ""); main errors on that too (PR #1500, merged 2026-03-22, unreleased) | https://github.com/prometheus/snmp_exporter/blob/v0.30.1/config/config.go (substituteEnvVariables) + https://github.com/prometheus/snmp_exporter/pull/1500 | 2026-10-20 |
| Stock modules at v0.30.1: `dell`, `ubiquiti_unifi`, `hrDevice`, `hrStorage`, `system` (holds sysUpTime), auth `public_v2`; `dell_rac` (DELL-RAC-MIB) added on main 2026-02-23 (commit 11c48d3), in no release yet | https://github.com/prometheus/snmp_exporter/blob/v0.30.1/snmp.yml + commit 11c48d3 | 2026-10-20 |
| Ready-made vendor modules | https://github.com/prometheus-community/snmp | 2026-09-15 |
| Helm chart 9.18.1 (2026-09-24, appVersion v0.30.1) values: config, extraArgs, extraSecretMounts, configmapReload.enabled, serviceMonitor.selfMonitor.enabled, serviceMonitor.params — all present on main | https://github.com/prometheus-community/helm-charts (charts/prometheus-snmp-exporter) | 2026-09-15 |
| iDRAC full-walk 2–5 min reports | https://github.com/prometheus-community/helm-charts/issues/3572 | 2026-09-15 |
| Probe CRD `params` since v0.85.0; ScrapeConfig still v1alpha1 | https://github.com/prometheus-operator/prometheus-operator (releases + docs) | 2026-09-15 |
| iDRAC MIB versions: iDRAC10 1.30.31.10 zip = 4.7 / 15 May 2026, no SD/IDSDM objects; iDRAC9 7.30.30.54 zip (P3PPC, 21 Aug 2026, R650/R660/R750/R760) = 4.7 / 06 Aug 2026, a strict superset by object name (+8 SD/IDSDM systemState objects, +9 alert traps) — both zips opened 2026-10-20; 7.20.80.50 (kywdc) and 7.00.00.184 (fwmwv) driver pages list their Mib zips; dl.dell.com 403s bare curl (Akamai), browser download works | https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=fmd40 (and P3PPC, kywdc, fwmwv) | 2026-09-15 |
| iDRAC9 firmware version index (7.30.30.51 Jun 2026 newest listed; R760 driver page already serves 7.30.30.54) | Dell KB 000178115 | 2026-09-15 |
| OpenManage MIB bundle discontinued | Dell KB 000312092 | 2026-09-15 |
| iDRAC v3 breaks after firmware update | Dell KB 000321856 | 2026-09-15 |
| iDRAC10 SNMP defaults (AgentEnable=0, SHA-384/512 + AES-256 only, ProtocolEnable=0, 40-char passphrases) | iDRAC10 Attribute Registry 1.10.05.00 (dell.com support downloads) | 2026-09-15 |
| idrac_exporter metric list (drive life_left_percent, PSU input_watts/efficiency_percent, power_control min/avg/max, events log_entry, airflow CFM; PSU metrics carry no make/serial/firmware labels; firmware labels on storage controller, network_adapter_info (v2.6.3 #209), manager, PDU), config groups, Helm chart, no Connection View — internal/collector/collector.go @ v2.6.3 | https://github.com/mrlhansen/idrac_exporter (source, code-verified) | 2026-09-15 |
| idrac_exporter iDRAC10 empty power/fan/network fixed in v2.6.2 (#202 closed 2026-08-04, release note "Select the correct primary chassis"); 401s on `$` in passwords fixed in v2.6.3 (#191 closed 2026-10-14; env expansion now opt-in via `--config-expand-env`, `encoded: true` base64 credentials per sample-config.yml) | https://github.com/mrlhansen/idrac_exporter/issues/202 , https://github.com/mrlhansen/idrac_exporter/releases/tag/v2.6.2 , /issues/191 , https://github.com/mrlhansen/idrac_exporter/releases/tag/v2.6.3 (**v2.6.3 current**, 2026-09-05) | 2026-10-20 |
| CBS health OIDs, no-memory-OID, CBS220 fallback | https://github.com/librenms/librenms (mibs/cisco CISCOSB-*, poller includes) + Centreon plugin source | 2026-09-15 |
| CBS SNMPv3 support; joint CBS250/350 + Catalyst 1200/1300 OID doc (kmgmt3636, updated 2023-10-30 — carries no polling warning); excessive-polling high-CPU warning | Cisco CBS 250/350 admin + CLI guides; https://www.cisco.com/c/en/us/support/docs/smb/switches/Cisco-Business-Switching/kmgmt3636-snmpv3-common-oids-cbs350.html ; Cisco Tech Talk "High CPU Utilization on CBS Switches Due to Excessive SNMP Polling" https://video.cisco.com/detail/video/6333825352112 (kmgmt2884, formerly cited for this, is "Configure SNMP Views on CBS220" and carries no such warning) | 2026-09-15 |
| Onyx SNMP surface: EFM trap-only, entity-state PSU-only, 60 s cache, engineID reset, v3 protocol set, LTS to April 2029 | NVIDIA Onyx v3.10.4606 LTS User Manual (PDF; login-walled) <!-- ignore-freshen --> | 2026-09-15 |
| Onyx standard-MIB polling pattern | Official Zabbix "Mellanox by SNMP" template | 2026-09-15 |
| IETF/vendor base MIBs (ENTITY*, HOST-RESOURCES, EtherLike, RMON, POWER-ETHERNET) | https://github.com/cisco/cisco-mibs `v2/` @ commit f55dc443 | 2026-09-15 |
| Mellanox MIB mirrors | https://github.com/netdisco/netdisco-mibs (mellanox/, ciscosb/) | 2026-09-15 |
| Trap pipeline: telegraf snmp_trap input (inbound); maxwo/snmp_notifier is outbound-only (Alertmanager→traps) | https://github.com/influxdata/telegraf (plugins/inputs/snmp_trap) + https://github.com/maxwo/snmp_notifier | 2026-07-24 |
| iDRAC SNMP Grafana dashboard 14395 | https://grafana.com/grafana/dashboards/14395 + https://github.com/zorrzoor/grafana-idrac-dashboard | 2026-09-15 |
| UniFi SNMP surface (no LLDP-MIB/RMON/POWER-ETHERNET; ubiquiti_unifi module works) | Live hardware test against USW Pro HD 24 / USW-16-PoE / UAP-nanoHD <!-- ignore-freshen --> | 2026-09-15 |
