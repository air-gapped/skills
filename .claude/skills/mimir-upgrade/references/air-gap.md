# Air gap — staging, egress, CRDs

What must cross the gap, what phones home, and the two things that fail at install time and look like network
faults.

## Contents
1. [Egress audit](#1-egress-audit)
2. [Image plumbing](#2-image-plumbing)
3. [Per-hop image sets](#3-per-hop-image-sets)
4. [CRDs — Helm will not do this for you](#4-crds--helm-will-not-do-this-for-you)
5. [The RKE2 DNS gotcha](#5-the-rke2-dns-gotcha)
6. [What else to stage](#6-what-else-to-stage)

## 1. Egress audit

**Mimir phones home by default.** [UG] `-usage-stats.enabled` defaults to **true**, POSTing to
`https://stats.grafana.org/mimir-usage-report` every 4 h (5 s client timeout). The chart sets only
`usage_stats: {installation_mode: helm}` and never sets `enabled`, so the Go default stands in every version in
scope. [RFC] The reporter runs on targets that touch blocks storage — ingester, querier, store-gateway,
compactor — and also writes a cluster-seed object into **your own** bucket (`__mimir_cluster/mimir_cluster_seed.json`,
internal and harmless).

Air-gapped symptom if left on: a per-4h connection timeout in four components' logs plus a rising
`cortex_usage_stats_report_sends_failed_total`. Non-fatal, but noisy and it is the only unsolicited outbound
connection in the stack.

```yaml
mimir:
  structuredConfig:
    usage_stats:
      enabled: false
```

**Everything else is clean.** [RFC] minio's `mc` job targets the in-cluster minio Service; nginx's resolver
points at in-cluster DNS; Kafka is KRaft-only with in-cluster headless-service quorum voters (no ZooKeeper
image, no schema registry, no bootstrap discovery); the rollout-operator self-signs its webhook TLS (no
cert-manager, no ACME); the smoke-test Job is `helm.sh/hook: test` so it never runs on install/upgrade and
targets the in-cluster gateway; `continuous_test` defaults off and its write/read URLs default in-cluster.

## 2. Image plumbing

**There is no global registry override.** [RFC] `global:` carries no `image*` key — the upstream request
(grafana/mimir#5449) is still open. Every image family must be repointed independently, and they do not share a
shape:

| Family | Shape | Note |
|---|---|---|
| Mimir (all 15 components) | `repository:tag` | **No `registry` key at all** — fold the mirror host into `repository` |
| memcached, memcached-exporter | `repository:tag` | Same; and the four cache sections have **no per-cache image key** — one global block each |
| gateway nginx, kafka, rollout-operator, grafana-agent-operator | `registry` + `repository` + `tag` | Separate registry key |
| meta-monitoring Grafana Agent workloads | `repo` + `image` + `tag` | **Invisible to `helm template`** — the operator creates them |

Pull secrets differ too: top-level `image.pullSecrets` is a list of **strings** and covers Mimir components,
gateway, smoke/continuous test, memcached and exporter — but **not** kafka, minio, rollout-operator or
grafana-agent-operator, whose `imagePullSecrets` are lists of **maps**. `kafka.image.pullSecrets` is honoured by
the template yet **absent from `values.yaml`**. [RFC]

**Pin `image.tag` explicitly from 6.1.0.** [UG] The chart stopped shipping a default and now falls back to
`Chart.AppVersion`, so a chart patch bump silently changes the image tag to a value written nowhere in your
values file — the opposite of what an air-gapped staging process needs.

**There is no `image.digest` key.** [RFC] The only digest form the chart can express is the composite tag:

```yaml
image:
  repository: registry.internal/mirror/grafana/mimir
  tag: "3.1.2@sha256:<digest>"     # renders repo:3.1.2@sha256:<digest>
```

The alternative (`repository: …@sha256:…` with an empty tag) does **not** work — `default` treats `""` as empty
and appends AppVersion, producing `…@sha256:…:3.1.2`.

**Your mirror must serve quay.io as well as docker.io** — minio and `mc` come from quay.io. [RFC]

## 3. Per-hop image sets

Generated with `helm template` (chart sizing preset + chart defaults, `sort -u`). Regenerate rather than
hand-editing; the 6.1.0 prefix change makes a naive diff read as "4 removed, 4 added".

| Hop | Images |
|---|---|
| **5.8.0** | `grafana/mimir:2.17.0` · `grafana/rollout-operator:v0.28.0` · `nginxinc/nginx-unprivileged:1.28-alpine` · `memcached:1.6.38-alpine` · `prom/memcached-exporter:v0.15.3` · minio + mc unchanged |
| **6.0.6** | **+ `apache/kafka-native:4.1.0`** (only if adopting ingest storage) · `grafana/mimir:3.0.4` · `rollout-operator:v0.32.0` · nginx `1.29-alpine` · `memcached:1.6.39-alpine` |
| **6.1.0** | `docker.io/`-prefixed: `grafana/mimir:3.1.2` · `rollout-operator:v0.38.0` · `apache/kafka-native:4.1.0` · `nginx-unprivileged:1.29-alpine`; **memcached and memcached-exporter stay unprefixed** |

Not needed, explicitly: no `grafana/mimir-continuous-test` (a module of the main image), no `alpine/kubectl`
(the provisioner is GEM-only and removed), no ZooKeeper. [RFC]

**Regenerate the list per hop** with the chart's own preset extracted from the tarball — sizing presets drift
between minors, so carrying an older `large.yaml` forward silently keeps stale resource shapes.

## 4. CRDs — Helm will not do this for you

**Helm never installs or upgrades `crds/` content on `helm upgrade`** — only on `helm install`. [UG] That makes
CRDs a manual, hop-blocking step twice on this ladder:

- **At 6.0.6:** chart 5.8's rollout-operator shipped **no** CRDs, so `replicatemplates.rollout-operator.grafana.com`
  and `zoneawarepoddisruptionbudgets.rollout-operator.grafana.com` will not exist — yet the webhooks register
  anyway with `failurePolicy: Fail`. Apply both from `charts/rollout-operator/crds/` **inside the tarball**.
- **At 6.1.0:** they moved to a bundled subchart at `charts/rollout-operator/charts/crds/crds/` and their content
  changed for the new partition-aware PDB eviction. Apply again.

Air-gap note: the upstream migration guide installs them via `kubectl apply` from `raw.githubusercontent.com`.
Take them from the tarball instead — the URLs are unreachable, and they track `main` rather than the pinned
subchart version.

If you do not use the operator, set `rollout_operator.enabled: false` — **underscore**. The migration guide's
hyphenated `rollout-operator:` is a silent no-op that leaves it enabled. [UG]

Also: `charts/grafana-agent-operator/crds/` ships Prometheus-Operator CRDs (`servicemonitors`, `podmonitors`,
`probes`). If you already run prometheus-operator, installing with
`metaMonitoring.grafanaAgent.installOperator: true` risks CRD ownership conflict. It is off by default and the
Grafana Agent path is deprecated as of 6.0 — leave it off. [RFC]

## 5. The RKE2 DNS gotcha

`global.dnsService` defaults to `kube-dns` and `global.dnsNamespace` to `kube-system`; together they render
nginx's `resolver` directive. **On RKE2 the CoreDNS Service is `rke2-coredns-rke2-coredns`**, so the gateway pod
crash-loops on an unresolvable resolver — and in an air-gapped cluster this looks exactly like a network or
registry problem, which is where the debugging time goes. [RFC]

```yaml
global:
  dnsService: rke2-coredns-rke2-coredns
  dnsNamespace: kube-system
```

Confirm the actual Service name per cluster (Step 0 fact #5): `kubectl get svc -n kube-system | grep -i dns`.

## 6. What else to stage

- **Chart tarballs** for every hop. **Subcharts and mixins are vendored inside the `.tgz`** — `charts/{minio,
  rollout-operator,grafana-agent-operator}` and `mixins/` are all present, so **never run `helm dep update`
  inside the air gap**. (Rebuilding the chart from git *would* require `charts.min.io` and
  `grafana.github.io/helm-charts`.) [RFC]
- **One Helm binary version, used for every hop.** Helm 3 is sufficient — the CHANGELOG's "Upgrade to Helm v4"
  is a CI-only change and `Chart.yaml` is still `apiVersion: v2`. But Helm 3 and 4 render PDB apiVersions,
  `internalTrafficPolicy`, and PSP objects differently, so mixing versions across hops fills your diffs with
  phantom changes. [UG]
- **`mimirtool`** matching each app version, if you manage ruler rules or Alertmanager configs with it — there
  is no in-cluster path to fetch it.
- **The v5.8.x unified-proxy migration guide**, archived to disk. It is the only surviving copy of the
  nginx→gateway mapping table and it will disappear. [UG]
- **If adopting ingest storage:** your chosen Kafka platform's images and operator, which are *not* in the chart
  and are a separate lifecycle. Vet the candidate with the `airgap-vetting` skill.
