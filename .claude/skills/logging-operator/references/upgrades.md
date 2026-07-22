# Upgrades — release history, breaking boundaries, CRD mechanics, air-gap

Latest verified: **6.7.0** (2026-06-16). Cadence ~6–10 weeks. Support: previous
minor ≈3 months after a new major; **4.x EOL since Dec 2024** (4.10.4/4.11.4 last).
K8s ≥1.22, Helm ≥3.8.1 (OCI). No documented minor-skip restriction — the operator
regenerates the data plane from CRs; cross the breaking boundaries deliberately.

## Timeline with breaking boundaries

| Version | Date | Breaking / notable |
|---|---|---|
| 4.10.0 | 2024-10-03 | (the version Rancher froze on) |
| 4.11.x | 2024-11→12 | last 4.x line |
| **5.0.0** | 2024-12-17 | **Sumo Logic outputs/filter + `enhance_k8s` REMOVED**; CRD subchart `logging-operator-crds` split out (own OCI artifact); fluentd default = moving tag → pin builds |
| 5.1–5.2 | 2025-02→03 | fluentd + reloader images move in-repo, operator-versioned |
| **5.3.0** | 2025-04-28 | **fluentd non-root: UID 100/GID 101/fsGroup 101** — root-owned buffer PVCs break; chown 100:101 |
| 5.4.0 | 2025-06-06 | NodeAgent + chart-level hostTailer **deprecated**; AxoSyslog CRD lands (5.4, not 6.0) |
| **6.0.0** | 2025-07-14 | **NodeAgent CRD REMOVED** (Windows path gone); chart `hostTailer` removed (→ `hostTailers.instances[]` / HostTailer CRs); fluentd 1.18, fluent-bit 4.0.3 |
| 6.1.0 | 2025-10-08 | additive: `fluentBitAgentNamespace`, rabbitmq output, IPv6 |
| 6.2.x | 2025-11→12 | fluentd 1.19, fluent-bit 4.2; ⚠ 6.2.1-full broke ES 8.x (#2153); nil-pointer when `bufferVolumeMetrics` unset (#2145, fixed 6.2.1/2) |
| 6.3.x–6.4.0 | 2026-01→02 | additive (Kubelet_Host, terminationGracePeriodSeconds, buffermetrics config) |
| 6.5.x | 2026-04→05 | fluent-bit 5.0.x; drain-watch hang fixes land across 6.4–6.5 |
| **6.6.0** | 2026-06-08 | **CVE-2026-54680 hardening** (config-injection RCE, ≤6.5.2 affected); ⚠ escaping broke newline passwords (#2254) |
| **6.7.0** | 2026-06-16 | regression fix (#2255); eventrouter 1.0.0. **← recommended floor** |

Docs site lags GitHub (whats-new stops ~6.5) — release notes on GitHub are the
authoritative current source.

Component images are pinned as Go constants in the operator (not chart values);
override per-CR via `spec.fluentd.image`, `FluentbitAgent.spec.image`,
`spec.syslogNG` image fields.

## CRD upgrade mechanics (the chart quirk that bites everyone)

The chart (`oci://ghcr.io/kube-logging/helm-charts/logging-operator`, chart
version == operator version, OCI-only since 4.3) ships CRDs **twice**:

1. Classic `crds/` dir — installed on `helm install`, **never upgraded** by Helm,
   and **silently skipped if any CRD already exists** (a fresh install on a cluster
   with old CRDs runs the new operator against stale schemas with no error).
2. `logging-operator-crds` subchart — CRDs as real templates, upgradeable.

Supported upgrade invocation:

```bash
helm upgrade logging-operator oci://ghcr.io/kube-logging/helm-charts/logging-operator \
  --version 6.7.0 -n logging \
  --set logging-operator-crds.install=true --skip-crds
```

(`--skip-crds` avoids the crds/-dir vs subchart conflict — the values doc says so
verbatim.) Alternative: apply CRDs manually each upgrade:

```bash
helm show crds oci://ghcr.io/kube-logging/helm-charts/logging-operator --version 6.7.0 \
  | kubectl apply --server-side --force-conflicts -f -
```

**`--server-side` is mandatory**: the CRDs are huge (loggings.yaml 828KB,
outputs.yaml 557KB) — client-side apply dies with `metadata.annotations: Too long`
(256KB last-applied limit). Argo CD users: sync option `ServerSideApply=true`
(the subchart's `annotations` value exists for exactly this).

Order per upgrade: CRDs first, then operator (`helm upgrade`), then let it roll
the aggregator/collector. Legacy `createCustomResource` value: keep false on Helm3.

Chart extras: `logging.enabled` renders a full Logging CR from values
(`logging.fluentd`, `logging.fluentbit`, `logging.controlNamespace`, eventTailer/
hostTailer sub-blocks…); `telemetry-controller.install` conditional subchart.

## Big-jump playbook (e.g. 4.10 → 6.7.0, the Rancher-exit hop)

1. Inventory deprecated usage: `kubectl get nodeagents -A` (must be empty —
   CRD gone in 6.0); chart-level hostTailer config → HostTailer CRs;
   sumologic outputs/filters + enhanceK8s filters (removed 5.0) — **these fields
   are silently pruned on re-apply against 6.x CRDs**, they do not error.
2. Buffer PVC ownership: pre-5.3 root-owned → chown 100:101 or init-fix.
3. CRDs server-side-apply (above), operator upgrade, watch configcheck.
4. Crossing 6.6: diff the rendered `<logging>-fluentd-app` secret before/after —
   escaping changes rendering of values with quotes/backslashes/newlines.
5. ES 8.x users: skip 6.2.1's fluentd image (#2153) — moot at 6.7.0.

For the Rancher-bundled variant of this jump (helm release surgery,
cattle-logging-system specifics, air-gap mirroring), use the
**rancher-logging-exit** skill.

## Air-gap install/upgrade

Chart: `helm pull oci://ghcr.io/kube-logging/helm-charts/logging-operator
--version 6.7.0` → push to the internal OCI registry (or install from the tarball).
No `systemDefaultRegistry`-style global rewrite exists — set every image override
explicitly in values / CR specs.

Image list for 6.7.0 (mirror these):
`ghcr.io/kube-logging/logging-operator:6.7.0` ·
`ghcr.io/kube-logging/logging-operator/fluentd:6.7.0-full` ·
`.../config-reloader:6.7.0` · `.../fluentd-drain-watch:6.7.0` ·
`.../node-exporter:6.7.0` (buffer metrics) · `ghcr.io/fluent/fluent-bit:5.0.5` ·
`registry.k8s.io/pause:3.9` (drain placeholder) · `busybox` (volume init).
Optional: `.../syslog-ng-reloader:6.7.0` · `ghcr.io/kube-logging/eventrouter:1.0.0`
· `ghcr.io/axoflow/axosyslog:4.24.0` + `axosyslog-metrics-exporter:0.0.15`.
