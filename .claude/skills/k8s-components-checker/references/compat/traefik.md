# Traefik — compat (sifted from release_notes)

- **Primary source:** https://github.com/traefik/traefik/releases
- **Secondary sources:** https://github.com/traefik/traefik/blob/master/docs/content/migrate/v3.md (per-minor migration guide), https://github.com/traefik/traefik/blob/master/docs/content/deprecation/releases.md (support window table)
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 3.5.0
- **Last sifted:** 2026-05-28

Traefik does not publish a Kubernetes support matrix. The k8s floor is implicit
in the `client-go` version vendored at release time and is rarely a hard
constraint — Traefik talks to apiserver via watch + standard ingress/CRD/Gateway
API objects. The load-bearing compat signal is **bundled `sigs.k8s.io/gateway-api`
version** (drives required CRDs in-cluster) and the **`traefik.io` CRD-bundle
revisions** (each minor's `kubernetes-crd-definition-v1.yml` is the canonical
shape — apply before bump).

Active community support window per `deprecation/releases.md`:

| Minor | Released   | Active support       | Security support |
|-------|------------|----------------------|------------------|
| 3.7   | 2026-05-05 | Yes (current)        | Yes              |
| 3.6   | 2025-11-07 | Ended 2026-05-05     | Yes (until 3.8)  |
| 3.5   | 2025-07-23 | Ended 2025-11-07     | None             |
| 2.11  | 2024-02-12 | Ended 2025-04-29     | Ended 2026-02-01 |

2.11 is out of community support entirely as of 2026-02-01 — flag any 2.x
sighting as `✗ blocker` and route operators to v2-to-v3 migration. v3 is
backward-compatible with v2 router syntax (`core.defaultRuleSyntax: v2`), so the
upgrade is mostly install-config + CRD-group flip.

## 3.7.0  (2026-05-05)

- **k8s floor:** no hard floor stated; tested against currently-supported k8s minors (~1.30+ as of release date). `client-go` upstream supports current-3.
- **Breaking:** none for routing config. Ingress NGINX provider RBAC now needs `configmaps: [list, watch]` for the `nginx.ingress.kubernetes.io/custom-headers` annotation — pods will start but the feature silently fails without it. ForwardAuth `trustForwardHeader` deprecation (introduced 3.6.14) escalates — explicit `true`/`false` required to avoid warning logs.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.7/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` to pick up new retry middleware options and `ingressClassName` field on Traefik CRDs. Gateway API bumped to **v1.5.1** — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml`. `TLSRoute` graduated to Standard channel (no longer needs `experimentalChannel`); `TCPRoute` still experimental.
- **Upgrade ordering:** apply Gateway API v1.5.1 CRDs **before** rolling Traefik to 3.7, otherwise Gateway provider rejects routes. Apply updated Traefik CRDs before. Update Ingress NGINX provider RBAC concurrently with the rollout.
- **Deprecations:** none new beyond 3.6.14's `trustForwardHeader`. `experimental.kubernetesIngressNGINX` flag still deprecated (removed-experimental in 3.6.2).
- **Notable:** Wildcard `Host(*.example.com)` / `HostSNI` matchers (v3 rule syntax only — v2-compat mode does not get these). TLSOptions can attach to wildcard hosts now; `HostRegexp` still unsupported for TLSOptions. Knative provider supports v1.20.0.

## 3.6.0  (2025-11-07)

- **k8s floor:** no hard floor stated; targets current-3 k8s minors (~1.29+ as of release date).
- **Breaking:** none for routing config. `traefik.containo.us` CRD group is still gone (removed in v3.0) — operators arriving from 2.11 must flip every CRD manifest from `apiVersion: traefik.containo.us/v1alpha1` to `apiVersion: traefik.io/v1alpha1`. The v3.6 CRD bundle does not ship the legacy group.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.6/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` for the new `leasttime` load-balancing strategy and the new healthcheck options. Gateway API bumped to **v1.4.0** — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/standard-install.yaml`.
- **Upgrade ordering:** Gateway API v1.4.0 CRDs **before** Traefik. Traefik CRD bundle before. From 2.11: complete `traefik.containo.us → traefik.io` flip on all CRDs and manifests before rolling pods, or routers/services in the old group go dark.
- **Deprecations:** `3.6.2` made Ingress NGINX provider non-experimental — remove `experimental.kubernetesIngressNGINX: true` from static config (warning-only, but cleanup). `3.6.14` deprecates ForwardAuth `trustForwardHeader` (removal in next major); explicit setting silences the warning. `3.6.16` raises Docker provider floor to API v1.40 (Docker Engine 19.03) — irrelevant for k8s deployments.
- **Notable:** Knative provider added. Passive health checks + TCP health checks. `HighestRandomWeight` load-balancing algorithm. HTTP/2 HPACK table size now tunable. ECS IPv6. **3.6.4 hardened encoded-character rejection by default (rejects `%2F`, `%5C`, `%00`, `%3B`, `%25`, `%3F`, `%23` in paths) — caused widespread 400s, then 3.6.7 flipped defaults back to permissive.** If running 3.6.4..3.6.6, expect 400s on `%2F`-containing paths until the rollback in 3.6.7 or explicit `entryPoints.<name>.http.encodedCharacters.allowEncoded*: true` config.

## 3.5.0  (2025-07-23)

- **k8s floor:** no hard floor stated; targets current-3 k8s minors (~1.28+ as of release date).
- **Breaking:** RBAC now needs `pods: [get]` for auto-injection of `k8s.pod.name` / `k8s.pod.uid` into OTel resource attributes — pods start, but OTel signal regresses on missing RBAC. **Tracing default verbosity changed:** if no explicit `traceVerbosity` is set, existing configs default to `minimal` → fewer spans than 3.4. Set `traceVerbosity: detailed` to restore prior behavior.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.5/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml`. Gateway API bumped to **v1.3.0** — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml`.
- **Upgrade ordering:** Gateway API v1.3.0 CRDs **before** Traefik. Traefik CRD bundle before. Update RBAC ServiceAccount with `pods: [get]` concurrent with rollout if OTel is wired.
- **Deprecations:** `3.5.2` deprecates `proxyProtocol` on TCP LoadBalancer — move to `TCPServersTransport.proxyProtocol`. `3.5.4` renames OTel metric `traefik_tls_certs_not_after_milliseconds` → `traefik_tls_certs_not_after_seconds` (dashboard/alert update).
- **Notable:** NGINX Ingress provider added (still experimental in 3.5; non-experimental in 3.6.2). OCSP stapling. X25519MLKEM768 post-quantum TLS. Dashboard rewritten in React. Ingress prefix-match behavior now matches Kubernetes spec (could change which routes win for ambiguous prefixes — audit `pathType: Prefix` after upgrade).
