---
name: snmp-exporter
description: >-
  Best practices for Prometheus snmp_exporter (v0.30.x): writing generator.yml
  modules, curating MIB walks, SNMPv2c/v3 auth, timeout tuning, Kubernetes
  deployment (Probe/ScrapeConfig CRDs, secrets, UDP egress), local docker
  testing, and debugging failed scrapes. Includes worked device references for
  Dell iDRAC 9/10, Cisco CBS250/350 (+ Catalyst 1200/1300), and NVIDIA/Mellanox
  Onyx switches.
when_to_use: >-
  Use whenever the task touches snmp_exporter, snmp.yml, generator.yml, MIBs,
  SNMP monitoring of servers/switches/BMCs/PDUs, scraping hardware with
  Prometheus, snmpwalk output, SNMP traps, Probe/ScrapeConfig CRDs, or
  slow/failing SNMP scrapes — even if the user only says "monitor this switch"
  or "iDRAC metrics" without naming the exporter.
---

# snmp_exporter best practices

snmp_exporter is a **multi-target proxy**: one central instance walks SNMP on
many devices; Prometheus tells it what to scrape per request via URL params
(`/snmp?target=<ip>&module=<m1,m2>&auth=<name>`). Everything below assumes
v0.30.x. The generator and exporter versions **must match** — a config generated
by a different version can fail to load. Pin both in CI.

## Golden rules

1. **Never walk a whole vendor enterprise subtree.** Full-tree walks are the #1
   cause of multi-minute scrapes, device-CPU exhaustion, and even crashed SNMP
   agents (Cisco documents this for CBS; iDRAC full walks take 2–5 min;
   Onyx serves all management through one easily-overloaded daemon). Walk the
   specific tables worth alerting on — a curated module is typically 10–100×
   smaller. Measured here: Cisco CBS full-tree = 4034 metrics vs curated = 63.
2. **Compose modules per scrape instead of duplicating walks.** Since v0.24 one
   scrape can request `module=if_mib,vendor_health`. Keep vendor modules
   health-only and reuse the stock `if_mib`, `system`, `hrDevice`, `hrStorage`
   modules for interfaces/uptime/CPU/memory. `sysUpTime` lives in `system`
   (moved out of `if_mib` in v0.28) — include it when alerting on reboots.
3. **Do the timeout math.** Per-request worst case = `timeout × (retries+1)` =
   20 s at defaults (5s × 4), which silently exceeds Prometheus's default 10 s
   `scrape_timeout`. The exporter does NOT honor the scrape-timeout header —
   Prometheus just hangs up and the walk is cancelled, yielding `up=0` with no
   partial data. Set `scrape_timeout` above the observed
   `snmp_scrape_walk_duration_seconds`, and keep `timeout×(retries+1)` below it.
4. **Prefer v3 authPriv everywhere; v2c only as fallback.** SNMP v1 forces
   GETNEXT (one row per round trip) and can't read 64-bit counters — never use
   it. v2c community strings are plaintext on the wire: acceptable only on an
   access-controlled management network. Modern gear (iDRAC 9/10, Cisco CBS,
   Onyx) all support v3 with SHA-2 + AES — use SHA256 + AES-128 as the default
   pair, and match `auth_protocol` exactly to how the device user was created.
   BMCs also gate some data (e.g. iDRAC lifecycle logs) behind v3.
5. **Keep credentials out of git.** Generated snmp.yml embeds secrets in
   cleartext. Either use `${ENV_VAR}` in v3 `username`/`password`/`priv_password`
   with `--config.expand-environment-variables` (only those three fields), or
   split an auths-only yml into a Secret and load it as an extra `--config.file`
   (repeatable + glob since v0.24; duplicate auth/module names across files are
   rejected — never reuse the stock names like `public_v2`).
6. **Protect port 9116.** Anyone who can reach `/snmp` can walk arbitrary
   targets *with the configured credentials* (SSRF + credential relay).
   Firewall/NetworkPolicy it to Prometheus, optionally add exporter-toolkit TLS
   + basic auth (`--web.config.file`), and set device-side SNMP source ACLs.

## Writing modules (generator workflow)

Layout: one directory per device family with its own `mibs/` + generator.yml to
avoid MIB name collisions; generate one snmp.yml per family and load them all
at runtime (no merge needed). MIB sources: `make mibs` for the curated upstream
set; **github.com/prometheus-community/snmp** for ready-made vendor configs;
**librenms/librenms `mibs/`** as the broadest mirror when the vendor hides MIBs
behind a login. Patch unparseable MIBs in a `mib-patches/` dir rather than
hand-editing generated output.

```yaml
modules:
  my_device:
    walk:
      - MY-MIB::usefulTable          # ALWAYS prefer MIB::name over bare OIDs
      - 1.3.6.1.4.1.X.Y.Z            # numeric: last resort, see pitfall below
    lookups:                         # turn numeric indexes into readable labels
      - source_indexes: [ifIndex]
        lookup: IF-MIB::ifName
    overrides:
      ifName: {ignore: true}         # don't also emit lookup columns as metrics
    timeout: 5s                      # per-PDU; worst case ×(retries+1)
    retries: 2
    max_repetitions: 25              # raise for fast agents, LOWER for buggy ones
```

- **Numeric-OID pitfall**: numeric subtree walks can silently resolve to
  nothing when the MIB directory contains overlapping arc definitions —
  generation "succeeds" with the metrics simply absent. Always diff the
  generated file for the expected metric names before shipping it.
- A walk entry that is a single instance (e.g. `...1.8.0`) becomes a cheap GET.
- `filters.static` (generation-time, fixed indices → GETs) and `filters.dynamic`
  (runtime, e.g. only ifAdminStatus=up interfaces) trim big tables at the
  device, unlike Prometheus `metric_relabel_configs` which only saves TSDB.
- `EnumAsInfo` for inventory-ish enums; `EnumAsStateSet` only for
  low-cardinality alertable states (it emits one series per possible value).
- Strings render as `gauge=1` with the value in a label; use `regex_extracts`
  to turn status strings into real 0/1 gauges.
- Tables indexed by non-renderable types (DateAndTime, Bits) are rejected after
  v0.30.1 (#1653) — override the index `type: OctetString` to keep such a table.
- Generate with `--fail-on-parse-errors` first; inspect `generator parse_errors`.
  Using `--no-fail-on-parse-errors` is fine when the remaining errors are all in
  MIB files the walks never touch (common with large vendor MIB dumps).
- No net-snmp headers locally? Use the container:
  `docker run --rm -v "$PWD:/opt/" quay.io/prometheus/snmp-generator:v0.30.1
  generate -m /opt/mibs -g /opt/generator.yml -o /opt/snmp.yml`

## Running it

```
snmp_exporter \
  --config.file=/etc/snmp_exporter/snmp.yml \   # stock modules (if_mib, system, hr*)
  --config.file=/config/snmp-custom.yml \        # generated custom modules
  --config.file=/secrets/auths.yml \             # credentials, from a Secret
  --config.expand-environment-variables
```

- Validate in CI with `--dry-run`; reload via SIGHUP or `POST /-/reload`;
  liveness on `/-/healthy`; inspect effective config at `/config`.
- Watch the exporter's own `/metrics` plus the per-scrape series every target
  returns: `snmp_scrape_walk_duration_seconds` (tune scrape_timeout against
  this), `snmp_scrape_packets_retried` (alert if ratio to packets_sent exceeds
  a few percent — it's the packet-loss signal), `snmp_scrape_pdus_returned`.
  Liveness of the *device* is the job's `up`; there is no `snmp_up` metric.
- One instance comfortably handles thousands of targets; scale with plain
  replicas behind one Service (stateless). `--snmp.module-concurrency` only
  parallelizes modules within one scrape — raise cautiously, devices rate-limit.

## Kubernetes

Read [references/kubernetes.md](references/kubernetes.md) before deploying:
Helm chart values, Probe CRD (params support needs prometheus-operator
≥ v0.85.0) vs ScrapeConfig relabeling, Secret-based auth wiring, UDP/161
NetworkPolicy, and stable-source-IP options for device ACLs.

## Local testing & debugging

```bash
docker run --rm -p 9116:9116 -v "$PWD/snmp.yml:/etc/snmp_exporter/snmp.yml" \
  quay.io/prometheus/snmp-exporter
curl 'localhost:9116/snmp?target=192.0.2.10&auth=public_v2&module=if_mib'
```

Failure-mode table — check these before blaming the exporter:

| Symptom | Likely cause / fix |
|---|---|
| "request timeout (after N retries)" | Wrong community/ACL/unreachable — SNMP silently drops bad-community requests, so auth errors LOOK like timeouts. Verify with `snmpbulkwalk -v2c -c <comm> <ip> system` from the same host/pod. |
| Scrape works but empty/few metrics | Wrong module for the device (it doesn't implement those OIDs), or the community's SNMP view excludes the private tree. |
| "OID not increasing" | Buggy agent — set `allow_nonincreasing_oids: true`. |
| Replies ignored on multi-homed device | Device answers from a different source IP — `use_unconnected_udp_socket: true`. |
| `up=0` only under Prometheus, curl works | scrape_timeout too low — walk cancelled mid-flight; check `snmp_scrape_walk_duration_seconds` via curl timing. |
| Config load: "invalid index type" | Post-v0.30.1 rejection of non-renderable index types — override to OctetString or drop the table. |
| Auths/modules parse error on upgrade | v0.23 auth split / version mismatch — regenerate with the matching generator. |

Debug tracing: `--log.level=debug` logs per-subtree walk durations (find the
slow subtree); add `&snmp_debug_packets=true` to a scrape URL for full packet
traces (requires debug log level; there is no `debug=` param). For CI without
hardware, replay a recorded `snmpwalk` with snmpsim.

## Device references

Read the matching file before writing or modifying a module for these families
— they carry verified OIDs, quirks, and the rationale for what NOT to walk:

| Device | Reference |
|---|---|
| Dell iDRAC 9/10 (PowerEdge BMC) | [references/idrac.md](references/idrac.md) |
| Cisco CBS250/350, Catalyst 1200/1300 | [references/cisco-cbs.md](references/cisco-cbs.md) |
| NVIDIA/Mellanox Onyx (Spectrum, SN2010…) | [references/mellanox-onyx.md](references/mellanox-onyx.md) |
| Ubiquiti UniFi (switches, APs) | [references/ubiquiti-unifi.md](references/ubiquiti-unifi.md) — live-tested; stock modules suffice |

Working generator configs for all of the above (curated walks, lookups, v3
auth blocks with `${ENV}` placeholders, plus a vendor-neutral `lldp`
mis-cabling watchdog module) are in [examples/](examples/) —
`generator-custom.yml` is the combined production config; the per-vendor files
are for iterating on one family. An opinionated alert pack for these modules
is [examples/alerts.yml](examples/alerts.yml). The stack around the exporter —
traps (Telegraf snmp_trap → Prometheus), ICMP discrimination (blackbox), NetBox-driven service
discovery, Dell OME for firmware, CI fixtures — is
[references/companions.md](references/companions.md): adopt those, don't
rebuild them.

## Backlog — open items to re-check

Time-sensitive or hardware-gated items; resolve and update the relevant
reference file when done. Dated provenance for every external claim lives in
[references/sources.md](references/sources.md) — bump its `Last verified:`
dates when re-checking; the full research narrative behind these modules is
[references/research-report.md](references/research-report.md) (background
only — never needed to apply the skill):

1. **idrac_exporter iDRAC 10 fix** — watch mrlhansen/idrac_exporter#202
   (power/fan/network metrics empty on 17G; fix committed but unreleased as of
   v2.6.1). Until a release ships, don't deploy the Redfish layer against
   iDRAC 10. Re-check: `gh release list -R mrlhansen/idrac_exporter`.
2. **Hardware snmpwalks** (one session with real gear settles all):
   Onyx SN2010 — hrProcessorLoad/hrStorageTable answer? EtherLike dot3Stats?
   DAC rows in entPhysicalSerialNum? CBS — which env table answers
   (.101.83 vs .101.53.15) on owned models; confirm DAC serial absence; do
   pethMainPseTable + etherStats* answer, and does etherStatsIndex == ifIndex;
   EtherLike dot3Stats? iDRAC 10 — v2c gets work once enabled? AES256 vs
   AES256C pairing? Walk bugs (virtualDiskTable skip) on current firmware?
3. **Next snmp_exporter release** (>0.30.1) ships the non-renderable-index
   rejection (#1653) — re-validate hand-written configs on upgrade; regenerate
   with the matching generator.
4. **prometheus-operator ScrapeConfig v1beta1 graduation** — update
   references/kubernetes.md examples when it ships.
5. **Contribute the cisco_cbs module** to prometheus-community/snmp — no
   public CBS module existed as of 2026-07; ours is novel.

## When NOT to use snmp_exporter

- OS that permits installing software → **node_exporter**.
- Modern Dell/HPE/Lenovo BMCs → **idrac_exporter** (Redfish, mrlhansen) is
  richer and avoids MIB curation; keep SNMP for old BMCs or trap-only needs.
- SNMP **traps** → snmp_exporter doesn't receive them; that needs a separate
  receiver (e.g. Telegraf's snmp_trap input; note maxwo/snmp_notifier is the
  REVERSE direction — Alertmanager alerts out as traps — see
  [references/companions.md](references/companions.md)). Don't promise trap-based alerting
  from this exporter.
