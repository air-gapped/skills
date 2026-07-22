# Modes, project landscape, and what NOT to adopt yet (July 2026)

## The two real modes

| | fluentd mode | syslog-ng mode |
|---|---|---|
| Node collector | Fluent Bit DaemonSet | Fluent Bit DaemonSet (same) |
| Collector→aggregator | fluentd `forward` protocol | TCP (fluentbit `syslogng_output`) |
| Aggregator | fluentd StatefulSet (`ghcr.io/kube-logging/logging-operator/fluentd:<ver>-full`) | AxoSyslog StatefulSet (`ghcr.io/axoflow/axosyslog`) |
| Routing CRs | Flow/ClusterFlow/Output/ClusterOutput | SyslogNGFlow/…/SyslogNGOutput |
| Outputs | 31 | 18 (incl. OTLP — fluentd has none) |
| Scale-in | volume drainer (automated) | manual buffer drain |
| Maturity | ecosystem default | performant but operationally thinner |

Official decision rule: **pick by output support first**; then syslog-ng if message
volume is high (multithreaded) or routing needs content matching / many flows;
fluentd otherwise. Both selected per Logging CR (`spec.fluentd: {}` vs
`spec.syslogNG: {}`).

**There is no fluentbit-only / direct-to-output mode.** FluentbitSpec's only egress
paths are forward-to-fluentd, TCP-to-syslog-ng, `targetHost/targetPort` (redirect to
an external forward-protocol receiver), and a `customConfigSecret` escape hatch.
Flows/Outputs render exclusively into aggregator config — no aggregator, no routing.
A Logging CAN be collector-less (aggregator-only, fed by another Logging's collector
via LoggingRoute) — that's the multi-tenant pattern, not a lighter mode.

## Telemetry Controller — watch, don't adopt (as of 2026-07)

The separate kube-logging project (OTel-Collector-based DaemonSet) positioned as
NodeAgent's successor and the collector-only story:

- 0.5.6 (2026-05-19), **v1alpha1**, pre-1.0. CRDs: Collector (cluster),
  Tenant (cluster), Subscription (ns), Output (ns), Bridge.
- **Only 6 output types**: otlp, otlphttp, fluentforward, file, elasticsearch,
  awss3 — everything else needs an aggregator behind it or a custom otelcol image.
- Hard-depends on the OpenTelemetry Operator; runs Axoflow's otelcol distribution.
- The operator integration (`Logging.spec.routeConfig.enableTelemetryControllerRoute`
  + operator flag `-enable-telemetry-controller-route`) is **still experimental** in
  6.7.0 and hardwired: it creates one Tenant+Subscription+Output per Logging,
  Output fixed to fluentforward → that Logging's fluentd. TC replaces fluent-bit as
  collector; fluentd stays. Admin must deploy the Collector CR and install TC
  (`telemetry-controller.install` chart conditional) separately.
- Roadmap gaps (one-collector-per-tenant, hot reload, backpressure verification)
  open with no GA date; Axoflow's public attention has pivoted to SIEM pipelines.

**Recommendation: LoggingRoute for multi-tenancy today; re-evaluate TC at 1.0/v1beta1.**

## AxoSyslog CRD — frozen thin wrapper

`AxoSyslog` (since 5.4) = `logPaths` (filterx + destination) + raw `destinations`
config strings. One deprecation chore since it landed; not a full aggregator
replacement in the operator. AxoSyslog-the-engine is heavily developed, but the
invested delivery paths are axoflow/axosyslog-charts and the commercial platform.
Inside the operator, treat syslog-ng mode (SyslogNGConfig + SyslogNG* CRs) as the
supported syslog-ng path, the AxoSyslog CRD as an expert escape hatch.

## Project health (verified 2026-07-22)

CNCF Sandbox since 2023-09; maintainers employed by Axoflow (commercial support
vendor); ~6–10-week release cadence through 6.7.0 (2026-06-16); repo active daily.
Support precedent: previous minor supported ~3 months after a new major (5.4 until
2026-10-06). **4.x is de facto EOL** — last patches Dec 2024. Axoflow states
logging-operator "is not being replaced" by TC.

## When something else fits better (honest comparison)

- **Grafana Alloy**: Loki-centric LGTM stack, no aggregator tier wanted.
- **Vector**: single-binary high-perf collector-direct-to-destination with VRL;
  no CRD-per-flow model.
- **fluent-operator (fluent.io)**: CRD-managed Fluent Bit WITH direct fluent-bit
  outputs, lighter footprint, no mandatory aggregator — the closest "fluentbit-only"
  alternative. Different project; don't mix docs.
- **OTel Collector**: logs as one signal among traces/metrics, OTLP end-to-end.

logging-operator's unique value: the Flow/Output CRD abstraction with
namespace-enforced soft multi-tenancy, LoggingRoute hard multi-tenancy,
buffer-aware scaling/draining, and fluentd's 100+ battle-tested outputs — i.e. a
**managed aggregator tier as CRDs**, which none of the above offer.
