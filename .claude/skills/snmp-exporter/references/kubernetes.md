# Running snmp_exporter on Kubernetes

Verified against helm chart prometheus-snmp-exporter v9.16.1 (appVersion
v0.30.1) and prometheus-operator ≥ v0.85.0, 2026-07.

**Contents:** [Topology](#topology) · [Prometheus Operator wiring](#prometheus-operator-wiring) · [Secrets](#secrets) · [Network](#network) · [Alerting on the pipeline itself](#alerting-on-the-pipeline-itself)

## Topology

One central, stateless **Deployment** behind a ClusterIP Service. Any replica
can serve any target (each scrape is an independent HTTP request), so scale
with plain `replicas` — no affinity, no sharding needed below thousands of
targets (~5000 targets/core is the community reference point). Don't run it as
a sidecar per Prometheus; the multi-target proxy pattern is the design.

Helm: `prometheus-community/prometheus-snmp-exporter`. Values that matter:
`config` (inline snmp.yml → ConfigMap), `extraArgs`, `extraSecretMounts`,
`configmapReload.enabled: true` (prometheus-config-reloader sidecar watching
the config dir and POSTing `/-/reload` — without it the pod must be rolled to pick up changes),
`serviceMonitor.selfMonitor.enabled` (scrape the exporter's own /metrics),
liveness/readiness on `/-/healthy`. The chart's `serviceMonitor.params`
(one ServiceMonitor per device) does not scale — use Probe/ScrapeConfig CRDs.

## Prometheus Operator wiring

**Probe CRD** — best for static device lists. Since operator v0.85.0
(2025-08) Probe has `params`, so `auth` works without relabeling hacks:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Probe
metadata: {name: switches, namespace: monitoring}
spec:
  prober: {url: snmp-exporter.monitoring.svc:9116, path: /snmp}
  module: system,if_mib,cisco_cbs,lldp
  params:
    - {name: auth, values: [switch_v3]}
  interval: 60s
  scrapeTimeout: 50s          # > worst walk duration; NOT the 10s default
  targets:
    staticConfig:
      static: [192.0.2.10, 192.0.2.11]
```

**ScrapeConfig CRD** (still v1alpha1) — use when targets come from service
discovery (http_sd from NetBox, file_sd, consul). Classic relabeling:

```yaml
relabelings:
  - {sourceLabels: [__address__], targetLabel: __param_target}
  - {sourceLabels: [__param_target], targetLabel: instance}
  - {targetLabel: __param_module, replacement: "system,if_mib,cisco_cbs,lldp"}
  - {targetLabel: __param_auth, replacement: switch_v3}
  - {targetLabel: __address__, replacement: snmp-exporter.monitoring.svc:9116}
```

Remember `probeSelector`/`scrapeConfigSelector` on the Prometheus CR.
VictoriaMetrics mirrors both: VMProbe / VMScrapeConfig.

Timeout hierarchy: module `timeout×(retries+1)` < `scrapeTimeout` ≤ `interval`.
The exporter ignores the scrape-timeout header — an undersized scrapeTimeout
cancels walks and yields `up=0`, it does not degrade gracefully.

## Secrets

Three-file pattern (auth names must not collide across files — never reuse
`public_v2` from the stock config):

1. Stock `snmp.yml` from the image (if_mib, system, hr* modules).
2. Your generated modules from a ConfigMap (no credentials in it).
3. Credentials via one of:
   - **SNMPv3 (preferred)**: `${SWITCH_SNMP_USER}`-style placeholders in the
     generated auths + `--config.expand-environment-variables` +
     `envFrom: secretRef` (works only for username/password/priv_password).
   - **v2c fallback**: an auths-only yml from a **Secret** mount, e.g.
     `auths: {switch_v2: {version: 2, community: <real>}}` — communities
     cannot be env-expanded.

All loaded via repeated `--config.file`.

## Network

- Egress **UDP/161** from the exporter pods to the management CIDR (+ DNS).
  Write the NetworkPolicy; also NetworkPolicy-restrict *ingress* to :9116 to
  Prometheus only (anyone reaching /snmp can relay the configured credentials at
  arbitrary targets).
- `hostNetwork` is NOT needed for outbound UDP (CNI SNAT works) and silently
  bypasses NetworkPolicy. Use it only when devices ACL by source IP and you
  need the node IP, or the mgmt net is only routable from nodes.
- Device source-IP allowlists vs ephemeral pod IPs: allowlist the node CIDR
  (pod traffic SNATs to node IP), pin the Deployment to labeled nodes for a
  small stable set, or use an egress gateway (Cilium CiliumEgressGatewayPolicy,
  Calico) for one stable IP.
- Devices replying from a different IP than queried (multi-homed BMCs):
  `use_unconnected_udp_socket: true` in the module.

## Alerting on the pipeline itself

- `up{job="snmp-..."} == 0 for 5m` — device or exporter path down (the
  snmp-mixin ships this as SNMPDown).
- `snmp_scrape_walk_duration_seconds` approaching scrapeTimeout — walk about
  to start failing; trim the module or raise the timeout.
- `rate(snmp_scrape_packets_retried[5m]) / rate(snmp_scrape_packets_sent[5m])
  > 0.02` — packet loss / device SNMP process struggling.
- Exporter self-metrics: `snmp_request_errors_total` (bad module/auth names
  from Prometheus config drift), `snmp_request_in_flight` (saturation).
