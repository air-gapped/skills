# Chart selection and Bitnami→Valkey values translation

Chart-health facts dated 2026-07-18 — chart landscapes shift; re-verify
release recency and Sentinel support before committing a new deployment.

## Chart landscape (Sentinel-capable options first)

| Chart | Sentinel | Images | Health signals (2026-07-18) | Air-gap surface |
|---|---|---|---|---|
| **groundhog2k/valkey** | ✅ `haMode` | `docker.io/valkey/valkey` (upstream) | tracks Valkey point releases within days; 5 parallel appVersion lines maintained; issue turnaround in hours; **bus factor 1**; no values.schema.json | 1 image (+ optional exporter); per-image registry override |
| **CloudPirates valkey** | ✅ `architecture: replication` + `sentinel.enabled`; plus `externalReplica` mode (replicate from an external Redis/Valkey — cutover helper, source ≤ 7.2 rule still applies) | `docker.io/valkey/valkey` | multi-maintainer + Renovate; cosign-signed; values.schema + tests + CHANGELOG | extra `common` library chart pulled via OCI — must also be mirrored for offline `helm dependency build` |
| **valkey-io/valkey-helm** (official) | ❌ standalone + replication only, **no automatic failover**; Sentinel(+HAProxy) PR pending — recheck | `docker.io/valkey/valkey`, `global.imageRegistry` | LF umbrella, 3+ named maintainers, very active; values.schema | clean |
| valkey-io/valkey-operator (official) | ❌ "Cluster mode only (no standalone or sentinel)", self-declared not production-ready | — | early development, v1alpha1 | — |
| Bitnami valkey | ✅ | 5 Bitnami-built images, dead-ended for free users | frozen (~Oct 2025, a major behind); maintained continuation is paid BSI | worst case |
| OpsTree redis-operator | ✅ (Redis) | OpsTree images | active, but Valkey support roadmap-only | — |

Selection heuristic: need Sentinel HA today → groundhog2k or CloudPirates
(groundhog2k = fastest tracking, single maintainer; CloudPirates = better
governance, one extra artifact). Watch the official chart — when its
Sentinel support lands, a first-party chart likely outlives both. Never
adopt the frozen Bitnami valkey chart for new work.

## Values translation: Bitnami `redis` chart → groundhog2k `valkey`

Verified against groundhog2k valkey 2.3.x and Bitnami redis 19.x–23.x.

| Bitnami redis | groundhog2k valkey | Trap |
|---|---|---|
| `auth.password` / `auth.existingSecret` (bare value under key `redis-password`) | **no auth block** — `valkeyConfig` (multiline conf string, rendered to a plaintext ConfigMap) or `extraSecretValkeyConfigs` (name of ONE Secret whose file contents are appended to valkey.conf) | the secret must contain **config-file fragments** (`requirepass <pw>`, `masterauth <pw>`), not a bare password. Reshape the secret; don't reuse |
| (sentinel auth implied by `auth.sentinel: true`) | `sentinelConfig` / `extraSecretSentinelConfigs` with `sentinel auth-pass <group> <pw>` (+ `sentinel sentinel-user/-pass` if sentinels themselves require auth) | the chart's init script greps **exactly** `masteruser`/`masterauth` from valkey.conf and `sentinel sentinel-user`/`sentinel sentinel-pass` from sentinel.conf to authenticate its own CLI calls — express auth in precisely those directives |
| `sentinel.enabled: true` | `haMode.enabled: true` | both = init + server + sentinel containers per pod, StatefulSet |
| `sentinel.masterSet` (default `mymaster`) | `haMode.masterGroupName` (default **`valkeyha`**) | client-visible! Set `masterGroupName: mymaster` to keep every client config unchanged, or plan a coordinated client update |
| `sentinel.downAfterMilliseconds` (default 60000) | default **30000** | halved default — align intentionally |
| `sentinel.failoverTimeout: 180000` | `180000` | same |
| `sentinel.quorum: 2` / `replica.replicaCount: 3` | `haMode.quorum: 2` / `haMode.replicas: 3` | same |
| — | `haMode.failoverWait` (**seconds**, default 35) | must exceed `downAfterMilliseconds` (**milliseconds**) — cross-unit comparison; raising downAfter to 60000 requires failoverWait > 60 |
| `master.persistence.enabled/size` | `storage.requestedSize` | **unset ⇒ emptyDir ⇒ data loss on pod delete.** Always set explicitly |
| `networkPolicy.enabled: true` (default on) | `networkPolicy: {}` — renders **nothing** by default | author ingress/egress rules manually or knowingly drop the policy |
| `metrics.enabled` + `metrics.serviceMonitor.enabled: false` | `metrics.enabled: false`, but once on, **`metrics.serviceMonitor.enabled` defaults true** | inverted default — fails install on clusters without prometheus-operator CRDs |
| runAsUser/fsGroup **1001** | **999** | do not reuse Bitnami PVCs (ownership + different on-disk layout; physical reuse is moot for 7.4+ sources anyway — side-by-side instead) |

## Behavioral differences that break clients

- **HA main service `<fullname>` exposes ONLY the sentinel port 26379** —
  no 6379 (Bitnami's sentinel-mode service exposes both `tcp-redis` and
  `tcp-sentinel`). Any client that lazily used the main service's 6379
  breaks; clients must perform real Sentinel discovery
  (`SENTINEL get-master-addr-by-name <group>`) and connect to the announced
  address. The `<fullname>-headless` service carries both ports.
- **Port names** differ: `valkey`/`sentinel` vs Bitnami's
  `tcp-redis`/`tcp-sentinel` — audit NetworkPolicies, ServiceMonitors, and
  probes that reference named ports.
- `haMode.useDnsNames: false` (default) announces **pod IPs**; `true`
  announces `<pod>.<fullname>-headless.<ns>.svc...` with
  `SENTINEL resolve-hostnames yes`. A DNS-resolution-during-failover fix
  landed in chart 2.2.2 — don't run older chart versions in HA.
- No equivalents exist for Bitnami's graceful failover-on-shutdown prestop
  choreography (`redisShutdownWaitFailover`), `auth.acl.*`,
  volumePermissions/sysctl init containers. If any of these carried real
  weight in the old deployment, plan replacements explicitly.

## Prometheus exporter continuity

`oliver006/redis_exporter` is the de-facto Valkey exporter (README now
titled "Prometheus Valkey & Redis Metrics Exporter"; supports Valkey 7–9).
Published on `docker.io/oliver006/redis_exporter`, **`ghcr.io/oliver006/redis_exporter`**,
and **`quay.io/oliver006/redis_exporter`** — pick ghcr/quay to dodge Docker
Hub rate limits; any of the three works as a mirror source. Bitnami's
`redis-exporter` image was just a repackage of it and is dead-ended.

groundhog2k wiring: `metrics.enabled: true` adds the exporter as a per-pod
sidecar + `<fullname>-metrics` service (port 9121) + ServiceMonitor.
Exporter auth is NOT derived from valkeyConfig — pass `REDIS_PASSWORD`
(and `REDIS_USER` if ACLs) via `metrics.exporter.env` or
`metrics.exporter.extraExporterEnvSecrets`. The chart pins its own exporter
tag independent of chart version — set `metrics.exporter.image.*`
explicitly in air-gapped installs so the mirror list stays deterministic.

Dashboards/alerts keyed on exporter metric names carry over unchanged (same
exporter); alerts keyed on `redis_version` labels will report 7.2.4 forever
— key on `valkey_version` or the exporter's build info instead where the
distinction matters.
