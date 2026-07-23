# snmp_exporter best-practices research — 2026-07-23

Mode 2 (Research) synthesis from 5 parallel agents: iDRAC 9/10, Cisco CBS, Mellanox Onyx,
Kubernetes deployment, exporter/generator internals. Grounded in the local checkout
(prometheus/snmp_exporter @ 1d54f35, v0.30.1) and web/gh sources. This file is the
provenance record for the planned `snmp-exporter` best-practices skill.

**Contents:** [Executive summary](#executive-summary) · [Direct answers: what needs adding per vendor](#direct-answers-what-needs-adding-per-vendor) · [Key findings by theme](#key-findings-by-theme) · [Competing perspectives / contradictions](#competing-perspectives--contradictions) · [Gaps / uncertainties](#gaps--uncertainties-hardware-would-settle-these) · [Sources](#sources)

## Executive summary

- **Out of the box**: upstream snmp_exporter covers iDRAC servers via the **`dell`
  module** (iDRAC-MIB-SMIv2, 512 metrics: status, thermal, power, storage). It does
  **not** cover Cisco CBS/small-business switches (CISCOSB tree, `1.3.6.1.4.1.9.6.1`)
  or Mellanox Onyx (`1.3.6.1.4.1.33049`) — those need custom modules + vendor MIBs
  (mirror them into a local `mibs/` tree).
- **The #1 anti-pattern is walking whole enterprise subtrees.** Full `10892.5` walks
  take 2–5 min on real iDRACs (helm-charts#3572); walking all of `9.6.1.101` generated
  5223 metrics and hung the scrape (snmp_exporter#1229); Cisco warns excessive queries
  can crash the CBS SNMP process; Onyx serves everything through one `mgmtd` daemon
  that can be overloaded. Curated per-table walk lists are the core of a good module.
- **Timeouts are the #1 operational trap**: default module `timeout: 5s` ×
  `(retries: 3 + 1)` = 20 s worst case per request, vs Prometheus's default 10 s
  `scrape_timeout`. The exporter does NOT honor the scrape-timeout header; it just
  gets its walk cancelled mid-flight. Align: `scrape_timeout` > walk duration, and
  tune `timeout`/`retries`/`max_repetitions` per module.
- **Kubernetes**: central stateless Deployment behind a Service; Probe CRD (params
  support since prometheus-operator v0.85.0) for static device lists, ScrapeConfig
  CRD for inventory-driven SD; secrets via auths-only file from a Secret + repeated
  `--config.file`, or `--config.expand-environment-variables`.

## Direct answers: what needs adding per vendor

| Vendor | Upstream module? | What's needed |
|---|---|---|
| Dell iDRAC 9 | **Yes — `dell`** (walks `10892.5.2`, `.5.4`, `.5.5`) | Works as-is. Optionally add `10892.5.1.x` identity (racFirmwareVersion) and trim `.5.4` bulk (SEL eventLogTable, FRU). MIB: iDRAC-SMIv2 from the (discontinued, pinned) Dell-OM-MIBS-11010 zip; new MIBs now ship inside iDRAC firmware downloads. |
| Dell iDRAC 10 (17G) | Same `dell` module applies | Same OIDs confirmed working. Caveats: early-firmware SNMP hangs and GETNEXT-skips-OIDs bugs (notably virtualDiskTable), storage health "other", no CMOS battery metric. SNMP included at all license tiers (Core/Enterprise/Datacenter). Consider Redfish (`idrac_exporter`) as the forward path. |
| Cisco CBS250/350 | **No** (upstream `cisco_device` = classic IOS MIBs CBS doesn't implement) | Custom module from CISCOSB MIBs (librenms mirror is best). No memory OID exists at all. CBS220: no CISCOSB private MIBs — IF-MIB + ENTITY-MIB only. Catalyst 1200/1300 successors share the CISCOSB surface. |
| Mellanox Onyx (SN2010 etc.) | **No** | Health data comes from *standard* MIBs (ENTITY-SENSOR, ENTITY-STATE, HOST-RESOURCES, IF-MIB) — the `33049` private tree is mostly traps + legacy IB noise. Onyx LTS until April 2029, MIBs frozen. |

## Key findings by theme

### 1. Exporter/generator fundamentals (v0.30.x)

- Version: repo is v0.30.1; generator and exporter versions **must match** (loader
  error says so). Post-0.30.1 main adds #1653 (reject non-renderable index types —
  previously one bad row, e.g. DateAndTime-indexed table, panicked the whole process),
  #1646 (UTF-8 sanitize index labels), #1648 (PhysAddress48 gating).
- Generator CLI: `generate | parse_errors | dump`; `-m` (repeatable MIB dirs), `-g`,
  `-o`, `--fail-on-parse-errors` (default true), `--snmp.mibopts` (default "eu").
- Recommended layout (generator/README): **one directory per device family** with its
  own `mibs/` + generator.yml to avoid MIB namespace collisions. No need to merge
  outputs: `--config.file` is repeatable and glob-capable since v0.24 (`snmp*.yml`);
  duplicate module/auth names across files are rejected.
- Module schema: `walk` (OID / `MIB::name` / single instance → becomes GET),
  `max_repetitions: 25`, `retries: 3`, `timeout: 5s`, `allow_nonincreasing_oids`,
  `use_unconnected_udp_socket`, `lookups` (chained, order-sensitive,
  `drop_source_indexes`, `display_hint: "@mib"`), `overrides` (ignore/name/type/
  regex_extracts/scale/offset/datetime_pattern), `filters.static` (generation-time →
  GETs of listed indices) and `filters.dynamic` (runtime: walk filter OID, only walk
  matching indices).
- Release deltas that matter: v0.23 auths/modules split (breaking); v0.24 multi-module
  scrapes (`module=a,b`) + repeatable `--config.file`; v0.26
  `--config.expand-environment-variables` (username/password/priv_password only) +
  `snmp_context` param; v0.27 ucd OIDs → `ucd_la_table` (breaking for synology etc.);
  v0.28 sysUpTime moved from `if_mib` to new `system` module (breaking for reboot
  detection); v0.30 `snmp_engineid` param.
- MIB sourcing: `make mibs`; vendor configs+MIBs centralizing in
  **github.com/prometheus-community/snmp**; librenms/librenms `mibs/` as the broadest
  fallback mirror; local `generator/mib-patches/` for unparseable MIBs.

### 2. Performance & timeouts

- SNMP walks are serial PDU chains: scrape time ≈ (PDUs / max_repetitions) × RTT +
  device processing. v1 forces GETNEXT (one row per round trip) — use v2c/v3 for
  GETBULK (and 64-bit HC counters, which v1 can't read at all).
- Worst case per request = `timeout × (retries+1)` = 20 s at defaults. snmp_exporter
  ignores `X-Prometheus-Scrape-Timeout-Seconds` (unlike blackbox_exporter); Prometheus
  hanging up just cancels the walk ("scrape cancelled after Xs"). Rule:
  `scrape_timeout > expected walk duration` and `timeout×(retries+1) < scrape_timeout`.
- `max_repetitions`: raise to reduce round trips on healthy agents; *lower* it for
  buggy agents that choke on large GETBULK.
- if_mib on big switches: full ifTable+ifXTable is every column × every ifIndex
  (VLANs/subifs included). Trim with (a) dynamic filter on ifAdminStatus
  (`1.3.6.1.2.1.2.2.1.7`, values ["1"]), (b) static ifIndex filter (cheapest, GETs),
  (c) Prometheus metric_relabel_configs (saves TSDB only — device still does the walk).
- Per-scrape tuning metrics (returned inline): `snmp_scrape_walk_duration_seconds`,
  `snmp_scrape_duration_seconds`, `snmp_scrape_packets_sent/retried`,
  `snmp_scrape_pdus_returned`. Exporter-level: `snmp_collection_duration_seconds`,
  `snmp_request_errors_total`, `snmp_request_in_flight`. Alert on retried>0 and
  walk_duration → scrape_timeout. Packet-loss proxy: rate(retried)/rate(sent).
- Scaling: one instance ≈ 5000+ targets/core (community claim, MEDIUM confidence);
  `--snmp.module-concurrency` (default 1) only matters for multi-module scrapes; no
  walk dedup across modules.

### 3. Security & config hygiene

- v1/v2c community strings go plaintext on the wire — not secrets; SNMPv3
  authPriv (SHA-256+, AES-128/256) for real security. Config supports
  MD5|SHA|SHA224|SHA256|SHA384|SHA512 / DES|AES|AES192|AES256(+C Cisco variants).
- Keep secrets out of git: (a) auths-only yml from a Secret, loaded as a second
  `--config.file`; (b) `--config.expand-environment-variables` + `${VAR}` (only
  username/password/priv_password). The v0.23 auths/modules split makes (a) clean.
- Anyone who can reach :9116 can walk arbitrary targets with *your configured
  credentials* (SSRF + credential relay). Mitigate: exporter-toolkit
  `--web.config.file` (TLS+basic auth), bind address, NetworkPolicy/firewall to
  Prometheus only, device-side SNMP source ACLs and read-only views.
- Reload: SIGHUP or POST `/-/reload`; `--dry-run` for CI validation; `/-/healthy`
  liveness; `/config` dumps effective config (secrets masked).

### 4. Metric quality

- Canonical lookups: `source_indexes: [ifIndex]` → `IF-MIB::ifName`/`ifAlias`
  (MIB-qualified), then `ignore: true` the lookup columns. `drop_source_indexes`
  reduces clutter but breaks ifIndex joins.
- EnumAsInfo for inventory-ish enums; EnumAsStateSet **only** for low-cardinality
  alertable states (1 series per possible value). Non-numeric types render as
  gauge=1 + value label. Counter64 auto-wraps at 2^53 (rate() handles it).
- regex_extracts to turn status strings into 0/1 gauges; empty `labels: []` in a
  lookup deletes a label.
- Liveness = job `up` (SNMP failure fails the whole scrape; there is no `snmp_up`).
  Reboot detection = sysUpTime via the `system` module (must be added since v0.28).

### 5. Kubernetes deployment

- Topology: central stateless Deployment (chart default replicas:1; N replicas behind
  ClusterIP fine, no affinity needed). Helm chart prometheus-community/
  prometheus-snmp-exporter v9.16.1 (appVersion 0.30.1): `config` → ConfigMap,
  `configmapReload.enabled` (prometheus-config-reloader sidecar → POST /-/reload),
  `extraSecretMounts`, `serviceMonitor.params` (one SM per target — OK for a handful,
  clumsy at scale), `serviceMonitor.selfMonitor` for the exporter's own /metrics.
- Prometheus Operator: **Probe CRD** now first-class — `params` field since v0.85.0
  (2025-08, PR #7755) so `module`+`auth` work without relabeling hacks; use for
  static device lists. **ScrapeConfig CRD** (still v1alpha1) for file_sd/http_sd
  (e.g. NetBox-driven inventory) with classic relabeling:
  `__address__→__param_target`, set `__param_module`/`__param_auth`,
  `__param_target→instance`, `__address__→snmp-exporter.monitoring.svc:9116`.
  VictoriaMetrics: VMProbe / VMScrapeConfig mirror these.
- Network: plain pod-egress UDP/161 through CNI SNAT works; NetworkPolicy egress to
  mgmt CIDR + DNS. hostNetwork not needed (and bypasses NetworkPolicy) — only for
  node-IP source ACLs or node-only routes. Device source-IP allowlists: allowlist
  node CIDR, or use egress gateway (Cilium CiliumEgressGatewayPolicy / Calico) or
  pin to labeled nodes. `use_unconnected_udp_socket: true` for devices replying from
  a different IP.
- Testing: `docker run -p 9116:9116 -v $PWD/snmp.yml:/etc/snmp_exporter/snmp.yml
  quay.io/prometheus/snmp-exporter` then
  `curl 'localhost:9116/snmp?target=IP&auth=NAME&module=NAME'`. Debug:
  `--log.level=debug` (per-subtree walk durations); `snmp_debug_packets=true` param
  (requires debug log level; there is no `debug=` param). Cross-check with
  `snmpbulkwalk -v2c -c COMM -Cr25 IP OID`. CI without hardware: snmpsim replaying
  recorded walks (community string selects the .snmprec file).
- Failure modes: timeout after N retries = wrong community/ACL/unreachable (bad
  community is silently dropped → looks like timeout, not auth error); "OID not
  increasing" → `allow_nonincreasing_oids`; empty result = wrong module for device;
  wrong-source-IP replies → unconnected UDP socket; config load "invalid index type"
  → post-#1653 rejection (override `type: OctetString` to keep the table).

### 6. Dell iDRAC 9/10 specifics

- MIB: IDRAC-MIB-SMIv2 under `1.3.6.1.4.1.674.10892.5`. Structure: `.1` identity
  (racName/racFirmwareVersion/systemInfo), `.2` statusGroup (globalSystemStatus,
  globalStorageStatus, powerState), `.4` systemDetails (`.300` chassis incl. `.300.40`
  SEL eventLogTable — bulky, skip; `.600` power incl. `.600.12` PSUs, `.600.30`
  amperageProbeTable, `.600.50` battery; `.700` thermal incl. `.700.12` fans,
  `.700.20` temp probes; `.1100` devices incl. `.1100.30/.32` CPU, `.1100.50` memory
  DIMMs, `.1100.80/.90` PCI/NIC; `.2000` FRU), `.5` storage (`.5.1.20.130.1`
  controllers, `.130.4` physical disks, `.140.1` virtual disks).
- Upstream `dell` module = `.5.2 + .5.4 + .5.5` (512 metrics) — decent but includes
  eventLog/FRU bulk and misses `.5.1` identity. `dell_rac` = CMC chassis MIB
  (10892.2, M1000e/VRTX/FX2) — not for iDRAC.
- Full `10892.5` walk: 2–5 min scrapes on real hardware (helm-charts#3572). Curated
  community walk list: zorrzoor/grafana-idrac-dashboard (Grafana dashboard 14395).
- iDRAC 9: SNMP agent enabled by default (iDRAC.SNMP.AgentEnable=1), community
  "public", UDP 161; SNMP gets+traps at **every** license tier. v3: per-user
  SNMPv3Enable, SHA+AES recommended; >6 v3 auth failures in 2 min → 10 min lockout;
  KB 000321856 (v3 broken after fw update).
- iDRAC 10: same OIDs, SNMP in all tiers (Core/Enterprise/Datacenter). Security
  guide says "SNMP 2/3" (v1 likely deprecated), recommends v3-only or disable.
  Field report (gushi.medium.com 2026-06): early fw SNMP engine hang, GETNEXT skips
  subtrees (virtualDiskTable), storage health "other", CMOS battery metric removed.
  Sensitive data (lcLogTable) is v3-only by design (in-MIB comment).
- MIB acquisition: consolidated Dell OM MIB package **discontinued** (final 11.1.0,
  KB 000312092); MIBs now inside firmware download packages. Upstream Makefile pins
  the last zip. Redfish alternative: mrlhansen/idrac_exporter.

### 7. Cisco CBS specifics

- Private tree: `switch001 = 1.3.6.1.4.1.9.6.1.101` (CISCOSB MIBs, ex-Linksys/Marvell).
  Key OIDs (MIB-verified + LibreNMS/Centreon cross-confirmed):
  - CPU: `.101.1.6.0` rlCpuUtilEnable, `.101.1.7/.8/.9.0` last-second/minute/5-min
    (INTEGER 0..101, 101="not measured").
  - Env: `.101.83.1.1.1.3` rlEnvMonFanState, `.101.83.1.2.1.3` rlEnvMonSupplyState
    (enum 1 normal…6 notFunctioning), `.101.83.5.1.1.2` rlEnvFanDataTemp (really CPU
    temp; 0 = no sensor), `.101.83.5.1.1.3` fan RPM. Alt: `.101.53.15`
    rlPhdUnitEnvParamTable (PSU status, temp sensor value/status, per stack unit).
  - Inventory: `.101.53.14` rlPhdUnitGenParamTable (.1.2 sw ver, .1.5 serial,
    .1.7 service tag, .1.11 model).
  - Stack: `.101.107` (unit IDs, mode, topology). PoE: `.101.108.1.1.5`
    rlPethPsePortOutputPower (mW, index stackUnit.ifIndex).
- **No memory-utilization OID exists** on CBS250/350 (CISCO-MEMORY-POOL not
  implemented; confirmed by Centreon/Zabbix communities). Plan dashboards without it.
- Standard MIBs: IF-MIB ifXTable works and is the standard traffic path; RMON only
  4 groups; LLDP-MIB yes; ENTITY-MIB enough for inventory fallback; EtherLike
  unverified.
- **CBS220 does not implement the CISCOSB private tree at all** (LibreNMS code
  comment) — IF-MIB + ENTITY-MIB only.
- Generator gotchas (snmp_exporter#1229): CISCOSBsnmp.mib has a parse error (drop it
  or `--no-fail-on-parse-errors`); some rl* tables use InetAddress-without-type
  indexes (now auto-rejected by #1653); full `.101` walk = 5223 metrics + hung scrape.
- SNMP is **disabled by default**; enable via web UI (Advanced → SNMP) or CLI
  (`snmp-server server`, `snmp-server community X ro`); ensure the community's view
  includes the private tree. v3 fully supported (kmgmt3636 lists common OIDs).
  Cisco warns excessive queries can crash the SNMP process; community reports of
  SNMP going deaf until reboot.
- EOL: rolling select-model EOS/EOL notices for CBS250/350 (last-order dates 2024);
  successors Catalyst 1200/1300 share the CISCOSB SNMP surface (joint Cisco OID doc)
  → a CBS module should carry over.
- MIB source: not in cisco/cisco-mibs; official = software.cisco.com per-release
  bundle (login); best mirror = librenms/librenms `mibs/cisco/CISCOSB-*`.
- No published snmp_exporter module or CBS Grafana dashboard exists — building one is
  genuinely novel.

### 8. Mellanox Onyx specifics

- Health via **standard** MIBs (per official Zabbix template): temperature + fans =
  entPhySensorTable `1.3.6.1.2.1.99.1.1.1` (type 8=°C, 10=RPM) + entPhySensorOperStatus;
  PSU = ENTITY-MIB class 6 + ENTITY-STATE entStateOper `1.3.6.1.2.1.131.1.1.1.3`;
  CPU = hrProcessorLoad `1.3.6.1.2.1.25.3.3.1.2`; memory = hrStorageTable; traffic =
  ifXTable (ifName `Eth1/1` style, HC counters reliable).
- `1.3.6.1.4.1.33049` private tree: `.1` product registry (SN2010 sysObjectID =
  `.1.1.1.2010`), `.2` legacy EFM gmVariables (fan/temp/cpu tables — 2012-era IB
  gear; unverified whether Spectrum/Onyx answers them), `.3` IB VPI ports, `.5/.7`
  entity/state extensions, `.10/.11/.12` power-cycle/sw-update/config-db actions.
  Real value = **traps** (asicOverTemp, insufficientFans/Power, procCrash,
  cpuUtilHigh, diskSpaceLow, unexpectedShutdown, PSU insert/extract).
- Product status: Onyx LTS since 2023-11-01, supported to **April 2029**, latest
  train 3.10.47xx; NVIDIA direction = Cumulus/SONiC. MIBs frozen — stable target.
- All management incl. SNMP goes through single `mgmtd` daemon; overload makes the
  whole box unresponsive (NVIDIA KB) → narrow walks, moderate intervals.
- Config: `snmp-server enable`, `snmp-server community X ro`, v3 user with
  sha/aes-128. JSON API exists (x86 models, ≥3.9.0300) but no Prometheus exporter
  uses it; ska-sa/switch_exporter (SSH scraping) is the alternative.
- MIB mirrors: netdisco-mibs `mellanox/`,
  observium CE (adds legacy MELLANOX-MIB), NVIDIA's own Mellanox/ufm_sdk_3.0.
  MELLANOX-WJH-MIB only on the (login-walled) enterprise portal.
- No upstream module, no notable Grafana dashboard — gap confirmed.

### 9. Initial naive modules (historical — superseded by examples/)

These were the first-pass full-tree configs this research replaced; kept as
before/after evidence for the "never walk whole vendor trees" rule. The
curated replacements live in the skill's `examples/` directory.

- `generator-idrac.yml` walks full `10892.5` → 554 metrics; known-slow pattern —
  rebuild on curated tables (status + thermal + power + storage + identity;
  consider amperageProbeTable/powerUsageTable for watts).
- `generator-cisco.yml` walks full `9.6.1` + ifXTable → 4034 metrics; rebuild on
  `.101.1.7-9` CPU + `.101.83` env + `.101.53.14/15` inventory/env + `.101.107`
  stack + (PoE `.101.108.1.1.5` if used) + ifXTable with ifName/ifAlias lookups.
- `generator-mellanox.yml` walks full `33049` + ifXTable → 359 metrics dominated by
  bx*/VPI noise; rebuild on ifXTable + entPhySensorTable + entPhysicalTable/
  entStateTable + hrProcessorLoad + hrStorage (+ selected 33049.7/.11).
- `generator-custom.yml` combines all three (snmp-custom.yml, 4979 metrics).

### 10. Alternatives / complements

- **idrac_exporter** (mrlhansen, Redfish): prefer for modern Dell BMCs; also
  iLO/XClarity. SNMP remains for old iDRACs and trap-only setups.
- **node_exporter**: always prefer when an agent can be installed on the OS.
- **Telegraf snmp plugin**: inline table config, no generator; snmp_exporter wins in
  Prometheus-native shops (central proxy, generator typing, relabel-driven targets).
- **snmp traps**: snmp_exporter does NOT do traps; Onyx/iDRAC trap value needs a
  separate receiver (e.g. Telegraf's snmp_trap input; NOT snmp_notifier —
  that relays Alertmanager alerts out as traps, the reverse direction;
  correction 2026-07-24).

## Competing perspectives / contradictions

- iDRAC 10 + SNMPv1: User's Guide says v1/v2/v3 supported; Security Guide says
  "SNMP 2/3". Treat v1 as gone/deprecated; test on hardware.
- "dell_rac is the iDRAC module" — wrong; `dell` is. dell_rac = CMC chassis.
- ScrapeConfig "replaces" Probe — overstated; still v1alpha1, Probe is v1 and now
  param-complete.
- Older claims that iDRAC SNMP needs Express+ license — license tables show SNMP at
  all tiers.
- "LibreNMS supports Mellanox" — detection + generic pollers only, no vendor sensors.
- Onyx doc's standard-MIB list omitted HOST-RESOURCES, but Zabbix/LibreNMS
  demonstrably poll it (doc extraction truncated).

## Gaps / uncertainties (hardware would settle these)

1. iDRAC 10: default SNMP-agent state out of the box; whether v2c gets still work;
   which firmware fixed the walk bugs.
2. CBS: whether both `.101.83` and `.101.53.15` env tables answer on the exact
   models owned (fanless models return notPresent); EtherLike-MIB presence.
3. Onyx SN2010: whether `33049.2` gmVariables tables answer at all; whether
   entPhySensorTable + hrProcessor answer as the Zabbix template assumes (one
   5-minute snmpwalk settles it); WJH-MIB presence.
4. Exact scrape-time delta full-tree vs curated modules on owned hardware.
5. ScrapeConfig v1beta1 graduation timing; next snmp_exporter release tag carrying
   #1653 (breaking for DateAndTime-indexed hand configs).

## Sources

Per-agent source lists (repo files at v0.30.1/1d54f35; vendor docs; gh issues
#1229/#1240/#1010, helm-charts#3572; LibreNMS/Centreon/Zabbix/netdisco source;
NVIDIA Onyx UM 3.10.4706 + EOL PDFs; Dell KBs 000312092/000321856/000348267,
iDRAC10 UG/SCG; prometheus-operator PR #7755; Grafana dashboards 14395/21107;
mrlhansen/idrac_exporter; zorrzoor/grafana-idrac-dashboard; ska-sa/switch_exporter;
gushi.medium.com iDRAC10 field report 2026-06-21; robustperception.io snmpbulkwalk
article). Full URL lists retained in the session transcript.
