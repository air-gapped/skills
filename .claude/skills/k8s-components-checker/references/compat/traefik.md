# Traefik — compat (sifted from release_notes)

- **Primary source:** https://github.com/traefik/traefik/releases
- **Secondary sources:** https://github.com/traefik/traefik/blob/master/docs/content/migrate/v3.md (per-minor migration guide), https://github.com/traefik/traefik/blob/master/docs/content/deprecation/releases.md (support window table)
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 2.11
- **Last sifted:** 2026-11-25 — read: v3.8.0 release body, `docs/content/migrate/v3.md` at v3.8.0 and v3.7.20, `docs/content/deprecation/releases.md` at master and v3.8.0, release notes v3.7.17–v3.7.20 and v2.11.61–v2.11.64, `gh api repos/traefik/traefik/security-advisories`, `go.mod` at v3.8.0 / v3.7.20 / v2.11.64.
- **Last release-verified:** 2026-11-25 (`gh release list --repo traefik/traefik`: v3.8.0 `isLatest`, v3.7.20, v2.11.64 — all 2026-11-23; v3.8.0-rc.1..rc.3 are pre-releases)

> ## Verdict shortcut — land on `v3.7.20` or `v3.8.0`; everything older is inside open advisories
>
> **Floor: `v3.7.20` (3.7 line) or `v3.8.0` (3.8 line)**, both 2026-11-23. Any Traefik at or below **v3.7.19** — which
> includes *every* release of 3.0 through 3.6 — is inside published advisories, and on every line except
> 3.7 / 3.8 there is no patch and never will be.
>
> Upstream's own support table (`docs/content/deprecation/releases.md` at master, read 2026-11-25; it has **no 3.8 row yet**):
>
> | Line | Active support | Security support |
> |------|----------------|------------------|
> | **3.7** | **Yes** | **Yes** |
> | 3.6 | ended 2026-05-07 | **ended 2026-08-16** |
> | 3.5 / 3.4 / 3.3 / 3.2 / 3.1 / 3.0 | ended | **No** |
> | 2.11 | ended 2025-04-29 | stated end **2026-09-07** (patches continue, see below) |
>
> **The dates and the advisories interlock — this is not an abstract support argument.**
> GHSA-5w68-77r2-r64c (**critical**, complete authentication bypass in the `digestAuth` middleware)
> was published **2026-08-21**, five days *after* 3.6's security support ended, and its
> affected range is `>= v3.0.0, <= v3.7.10` plus `<= v2.11.54`. The 3.6 line's final release is
> **v3.6.25** (2026-07-31), which sits inside that range. **No 3.6.x will ever be patched for it.**
> CVE-2026-88007 (**critical**, HTTP/3 backend NTLM connection reuse, published 2026-09-07)
> raised the ceiling to `<= v3.7.12`. The floor then kept moving: v3.7.14 (2026-10-06, 8 advisories incl.
> GHSA-qm9f-w54v-q2qh, GHSA-53qr-784g-cj35), v3.7.15 (2026-10-15, GHSA-p8wx-ph99-xgcr, GHSA-ww7c-q3mv-xx22),
> v3.7.16 (2026-10-20, GHSA-hrpp-p4fc-wwf8 — ForwardAuth shares the auth-server connection pool and leaks
> NTLM/Negotiate-bound identity across clients), then three more rounds in November:
>
> | Release (3.7 / 2.11) | Published | Advisories (all high unless noted) |
> |---|---|---|
> | v3.7.17 / v2.11.61 | 2026-11-02 | GHSA-xv5x-242w-7hf7 — per-connection backend transport leak from unauthenticated Negotiate/NTLM headers (`>= v3.7.14, <= v3.7.16`; `>= v2.11.58, <= v2.11.60`) |
> | v3.7.18 / v2.11.62 | 2026-11-12 | GHSA-p956-6gvv-mxqp (incomplete fix for hrpp-p4fc-wwf8: ForwardAuth NTLM bypass via `Proxy-Authorization`); GHSA-x5pf-cqh3-2gv8 (Compress middleware zstd memory exhaustion, `>= v3.1.0`); GHSA-cp28-5662-543f (`sanitizePath` misses `/..;x/` dot-segments, path-based auth bypass); GHSA-rr42-h8r2-f28g (medium, unbounded BasicAuth password length); 3.7 only: GHSA-ccgh-9g52-6vwg (ingress-nginx `auth-tls-secret` client-cert bypass + `Ssl-Client-*` spoofing, `>= v3.7.15`) |
> | v3.7.20 / v2.11.64 (3.8.0) | 2026-11-24 | GHSA-3rh5-223h-cpwr (Compress middleware Brotli memory exhaustion, `>= v3.0.0, <= v3.7.19`); GHSA-9657-c2gv-wjpj (medium, trailing-dot hosts evade TLS-option conflict detection, `>= v2.0.0, <= v2.11.63` and `>= v3.0.0, <= v3.7.19`); GHSA-42x2-976f-ph52 (medium, provider credentials in debug logs, support dumps and anonymous usage statistics) |
>
> 3.6 is inside every one of these ranges, unpatched. v3.7.19 / v2.11.63 (2026-11-13) carry dependency bumps only, no advisory.
>
> **2.11 is not a landing point.** Upstream's table still reads "Ends Sept 07, 2026", yet Traefik
> kept shipping 2.11 security patches after that date through **v2.11.64** (2026-11-23, clears GHSA-9657-c2gv-wjpj;
> v2.11.62 clears the 2026-11-12 items that apply to 2.11). The patches are
> discretionary past the stated end, so plan the v2→v3 move rather than relying on them.
> Ingress-NGINX-provider advisories (3.7+ feature) never apply to 2.11.
>
> **So a survey has exactly one answer: move to `v3.7.20`+ (or `v3.8.0`+)** (stopgap for a 2.11 fleet mid-migration: `v2.11.64`). There is no supported landing point
> on any other line, and "upgrade to the latest patch of the minor you are on" is wrong here for
> every minor but 3.7 and 3.8.
>
> **Re-derive the floor every pass — Traefik publishes faster than it documents.** The advisories endpoint lists 40 for 2026
> (first page, `per_page=40`); nine were published in the 24 days after v3.7.16 alone.
> Per-line sections below record behaviour and migration detail; they do **not** imply a line is choosable.

Traefik does not publish a Kubernetes support matrix. The k8s floor is implicit
in the `client-go` version vendored at release time and is rarely a hard
constraint — Traefik talks to apiserver via watch + standard ingress/CRD/Gateway
API objects. The load-bearing compat signal is **bundled `sigs.k8s.io/gateway-api`
version** (drives required CRDs in-cluster) and the **`traefik.io` CRD-bundle
revisions** (each minor's `kubernetes-crd-definition-v1.yml` is the canonical
shape — apply before bump).

**Applying the `traefik.io` CRD bundle — do it server-side.** The schemas are large
enough that client-side `kubectl apply` trips the 256 KiB `last-applied-configuration`
annotation limit, so use `kubectl apply --server-side --force-conflicts` (e.g.
`helm template traefik-crds <chart>.tgz | kubectl apply --server-side --force-conflicts -f -`).
Installing the `traefik-crds` chart as a Helm *release* can also fail
`"request body too large"` where the release-Secret POST is size-capped — observed
behind a Rancher-proxied API server even though the rendered bundle is only ~25 KiB
gzipped (so it's the request-path cap, not the 1 MiB Secret-data limit). The main
chart's `crds/` dir is installed once and never upgraded by Helm, so a CRD bump is a
manual server-side-apply step regardless of how the controller itself is deployed.

**Helm chart version ≠ proxy version (axis note).** This file tracks the **proxy**
(app) version; the Helm chart moves on its own track and carries its own values-schema
breaking changes not reflected in the per-version sections below. Example: chart 40.x
consolidated the dedicated `service.type` / `loadBalancerSourceRanges` / `externalIPs` /
`ipFamilies` keys into the generic `service.spec` passthrough (which now defaults
`type: LoadBalancer`). Re-diff `helm show values` against your overrides on every
chart-major bump.

Community support window per `deprecation/releases.md` (master, read 2026-11-25; **no 3.8 row yet**):

| Minor | Released   | Active support       | Security support |
|-------|------------|----------------------|------------------|
| 3.8   | 2026-11-23 | not in upstream table | advisories name v3.8.0 as the patched release |
| 3.7   | 2026-05-05 | Yes                  | Yes              |
| 3.6   | 2025-11-07 | Ended 2026-05-07     | Ended 2026-08-16 |
| 3.5   | 2025-07-23 | Ended 2025-11-07     | None             |
| 3.4   | 2025-05-05 | Ended 2025-07-23     | None             |
| 3.3   | 2025-01-06 | Ended 2025-05-05     | None             |
| 3.2   | 2024-10-28 | Ended 2025-01-06     | None             |
| 3.1   | 2024-07-15 | Ended 2024-10-28     | None             |
| 3.0   | 2024-04-29 | Ended 2024-07-15     | None             |
| 2.11  | 2024-02-12 | Ended 2025-04-29     | Stated end 2026-09-07; patches continue (v2.11.64) |

Upstream's stated rule (as of v3.6): every minor is supported 6 months from GA; the last minor before a new major gets 2 years. The table has not been updated for 3.8, so confirm a line's coverage from the advisories endpoint, not the table.

2.11 is past its stated community support end — flag any 2.x sighting as `✗ blocker` and route operators to v2-to-v3 migration. v3 is
backward-compatible with v2 router syntax (`core.defaultRuleSyntax: v2`), so the
upgrade is mostly install-config + CRD-group flip.

## 3.8.0  (2026-11-23 — latest patch **v3.8.0**; `go.mod`: Gateway API **v1.7.0**, `client-go v0.37.1`)

- **k8s floor:** no hard floor stated (no k8s matrix published); vendors `client-go v0.37.1` (3.7.20 vendors v0.36.5). One optional feature is version-gated: **ClusterTrustBundle** references in `BackendTLSPolicy` / Gateway frontend TLS need the `certificates.k8s.io/v1` API, "available since Kubernetes v1.37"; on older clusters those references are reported as unsupported kinds. Source: migration guide `v3.md` § v3.8.0.
- **Breaking:**
  - **Gateway API CRDs must be v1.7.0** (v1.5.x support dropped). `TCPRoute` graduated to Standard and is consumed as `v1`; the Standard channel no longer serves `v1alpha2`, so manifests still authored `gateway.networking.k8s.io/v1alpha2` are rejected by the apiserver — change them to `v1`. `experimentalChannel` now only enables listener filters.
  - **Listener isolation:** each HTTP/HTTPS listener server name gets a parent router with the listener's entry point and TLS config; route routers become children. Anything reading generated routers via the API sees the new structure.
  - **Listener TLS options:** the `default` TLS option no longer applies to Gateway HTTPS listeners; a host served by both a listener and a router from another provider on one entry point is reported as a TLS-option **conflict** (falls back to `default`, or disables the routers with `core.strictTLSOptions`).
  - Listeners declaring `filters` that cannot be applied (no `experimentalChannel`, `ExternalAuth`, unsupported `ExtensionRef`) are now **not accepted** (they were ignored before).
  - Includes the 3.7.18 changes: Ingress-NGINX per-host TLS options (the `default` TLS option's `minVersion`/`cipherSuites` stop applying to Ingress hosts), BasicAuth passwords > 1024 bytes get 401, dot-segments with path parameters (`/foo/..;bar/baz` → `/baz`) are resolved under `sanitizePath`.
- **CRD migrations:** apply `https://raw.githubusercontent.com/traefik/traefik/v3.8/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` (new `peerCertSANs`, `tap` middleware, buffering `disableRequestBuffer`/`disableResponseBuffer`, router `respondingTimeouts`, mirroring `streamBody`). Gateway API: `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.7.0/standard-install.yaml` (use `experimental-install.yaml` only for listener filters).
- **Upgrade ordering:** Gateway API v1.7.0 CRDs **before** Traefik 3.8 (and rewrite any `v1alpha2` TCPRoute manifests); Traefik CRD bundle before; add RBAC `listenersets` (get/list/watch), `listenersets/status` (update) and, for ClusterTrustBundle, `certificates.k8s.io clustertrustbundles` (list/watch) to the Gateway provider ServiceAccount. Optional: the Gateway RBAC `get` verb and `referencegrants/status` can be dropped.
- **Deprecations:** Gateway provider `labelSelector` → `gatewayClass` (error when both set; removal next major). `ServersTransport`/`ServersTransportTCP` `peerCertURI` → `peerCertSANs` (removal next major).
- **Notable:** `urn:k8s:configmap:<name>:<key>` strings in plugin configs are now replaced with the ConfigMap value (a missing ConfigMap/key drops the Middleware). `Host`/`HostSNI` accept a double-wildcard `**.example.com` (nested subdomains; ACME refuses it, so no certificate is issued for such a router). Gateway API ListenerSet (GEP-1713), HTTPRoute retry/CORS/RequestMirror/timeouts, Yaegi v2 experimental plugin runtime, ACME `reusePrivateKey`.

## 3.7.0  (2026-05-05, latest patch **v3.7.20** 2026-11-23 — supported alongside 3.8; 3.7.1 carried the CVE-2026-44774 fix)

- **k8s floor:** no hard floor stated; tested against currently-supported k8s minors (~1.30+ as of release date). `client-go` upstream supports current-3.
- **Breaking:** none for routing config. Ingress NGINX provider RBAC now needs `configmaps: [list, watch]` for the `nginx.ingress.kubernetes.io/custom-headers` annotation — pods will start but the feature silently fails without it. ForwardAuth `trustForwardHeader` deprecation (introduced 3.6.14) escalates — explicit `true`/`false` required to avoid warning logs.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.7/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` to pick up new retry middleware options and `ingressClassName` field on Traefik CRDs. Gateway API bumped to **v1.5.1** — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml`. `TLSRoute` graduated to Standard channel (no longer needs `experimentalChannel`); `TCPRoute` still experimental.
- **Upgrade ordering:** apply Gateway API v1.5.1 CRDs **before** rolling Traefik to 3.7, otherwise Gateway provider rejects routes. Apply updated Traefik CRDs before. Update Ingress NGINX provider RBAC concurrently with the rollout.
- **Deprecations:** none new beyond 3.6.14's `trustForwardHeader`. `experimental.kubernetesIngressNGINX` flag still deprecated (removed-experimental in 3.6.2).
- **Notable:** Wildcard `Host(*.example.com)` / `HostSNI` matchers (v3 rule syntax only — v2-compat mode does not get these). TLSOptions can attach to wildcard hosts now; `HostRegexp` still unsupported for TLSOptions. Knative provider supports v1.20.0.
- **Patch-level behaviour changes (migration guide `v3.md` at v3.7.16):** **v3.7.14** — Ingress-NGINX provider keeps dots in generated router/service/TLS-option names (`default-my.ingress-rule-0-path-0`), and TLSRoute router name hashes change; dashboards/alerts keyed on old names break. Gateway API routes matching equally well: only the precedence route gets a router. OTel duration histograms follow `OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`. Gateway API module bumped to v1.6.2. **v3.7.15** — every `CONNECT` request rejected with 501 regardless of HTTP version (use a TCP router to tunnel); Gateway API HTTPRoute backends with no `appProtocol` now use plain HTTP even on port 443 / `https*` port names — set `appProtocol: https` or a `BackendTLSPolicy` to keep TLS. Gateway API module v1.6.3. **v3.7.16** — middleware routing config holds Secret references (`urn:k8s:secret:<name>:<key>`) instead of the resolved values; behaviour unchanged, but the API/dashboard/support dump now show references. **v3.7.17** — built with **Go 1.27**: the `tlsrsakex`, `tls10server`, `tls3des` `GODEBUG` settings no longer work (set `cipherSuites`/`minVersion` in TLS options or `ServersTransport` instead); a request with more than **500 header values** gets 431 before routing (not access-logged; tune with the new entry-point option `maxHeaderValueCount`); **Ingress-NGINX generated names change again** to length-prefixed form (`default-7-whoami-6-rule-0-path-0`, replacing the 3.7.14 form) — re-key dashboards/alerts. **v3.7.18** — Ingress-NGINX provider generates a per-host TLS option (the `default` TLS option's `minVersion`/`cipherSuites` stop applying to Ingress hosts; host-less `auth-tls-secret` applies to every request matching no other host); BasicAuth rejects passwords > 1024 bytes with 401 (not configurable); under `sanitizePath` (default) `..`/`.`/empty segments with path parameters are resolved (`/foo/..;bar/baz` → `/baz`). v3.7.19 and v3.7.20 add no migration entries. Sources: `migrate/v3.md` at v3.7.20.

## 3.6.0  (2025-11-07 — final release **v3.6.25** 2026-07-31; security support ended **2026-08-16**, so it is permanently inside the 2026-08-21 `digestAuth` critical)

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

## 3.4.0  (2025-05-05, latest patch v3.4.5)

- **k8s floor:** no hard floor stated; targets current-3 k8s minors (~1.31+ as of release date — `client-go v0.31.1`).
- **Breaking:** **3.4.1 changed request-path normalization + router matching** (RFC 3986): unreserved chars like `%2E` are decoded, percent-encodings are uppercased, and reserved chars (e.g. `%2F`) now stay **encoded** during rule matching. Routes can flip between match/no-match across 3.4.0→3.4.1 — e.g. `/foo%2Fbar` no longer matches ```PathPrefix(`/foo/bar`)```. Audit any rules that depend on encoded path segments. **3.4.5 removed the MultiPath TCP support** that 3.4.2 had briefly introduced (MPTCP caused `setsockopt: operation not supported` crashes on some platforms); re-enable only via `GODEBUG=multipathtcp=1` if needed.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.4/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` for the new HTTP load-balancing strategies (`wrr`, `p2c`) and the new `rootCAs` field (ConfigMap+Secret) on `ServersTransport`/`ServersTransportTCP`. Also re-apply `…/v3.4/…/kubernetes-crd-rbac.yml`. Gateway API stays at **v1.2.1** (no GW API bump from 3.3) — `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml`.
- **Upgrade ordering:** apply the updated Traefik CRD bundle + RBAC before rolling pods. No Gateway API CRD change required from 3.3.
- **Deprecations:** `core.defaultRuleSyntax` (static) and `ruleSyntax` (per-router) — the v2-compat helpers — are now formally deprecated and slated for removal in the next major; ensure all rules use v3 syntax before then. HTTP `RoundRobin` strategy deprecated (alias of `wrr`). `ServersTransport.rootCAsSecrets` deprecated in favor of `rootCAs`.
- **Notable:** load-balancing strategy selection on HTTP services.

## 3.3.0  (2025-01-06, latest patch v3.3.7)

- **k8s floor:** no hard floor stated; targets current-3 k8s minors (~1.31+ as of release date — `client-go v0.31.1`).
- **Breaking:** **3.3.6 added automatic request-path sanitization** (`/../`, `/./`, and duplicate `//` segments are collapsed before processing) — can change routing for clients that send unencoded path traversal; opt out with `entryPoints.<name>.http.sanitizePath: false` (not recommended). **3.3.5 reordered default compression** to `gzip, br, zstd`, changing which encoding is chosen for clients that don't express a preference. **3.3.4 changed the OTel request-duration metric unit** from milliseconds to seconds (`traefik_(entrypoint|router|service)_request_duration_seconds`) — update dashboards/alerts.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.3/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` (new optional fields on `TraefikService` `mirrorBody`, RateLimit/InFlightReq `ipv6Subnet`, Compress `encodings` — backward-compatible). Gateway API bumped to **v1.2.x** — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml`. Note: due to breaking changes in Gateway API v1.2.0, **3.3 supports Gateway v1.2.x only when `experimentalChannel` is enabled**.
- **Upgrade ordering:** apply Gateway API v1.2.x CRDs **before** Traefik 3.3 if using the Gateway provider; apply Traefik CRD bundle before pods. New RBAC needed for the Gateway provider: add `backendtlspolicies` + `backendtlspolicies/status` (and `configmaps` get/list/watch) for BackendTLSPolicy support.
- **Deprecations:** ACME DNS-challenge `dnsChallenge.delaybeforecheck` → `dnsChallenge.propagation.delayBeforeChecks`; `dnsChallenge.disablepropagationcheck` → `propagation.disableChecks`. Tracing `globalAttributes` → `resourceAttributes`.
- **Notable:** Gateway provider gains BackendTLSPolicy support (experimental channel).

## 3.2.0  (2024-10-28, latest patch v3.2.5)

- **k8s floor:** no hard floor stated; targets current-3 k8s minors (~1.31+ as of release date — `client-go v0.31.1`).
- **Breaking:** **3.2.1 now strips `X-Forwarded-Prefix`** from untrusted sources (treated like other `X-Forwarded-*` headers) — apps relying on a client-supplied prefix from an untrusted hop will stop receiving it. **3.2.2 deprecated Swarm labels** `traefik.docker.network`/`traefik.docker.lbswarm` → `traefik.swarm.*` (Swarm-only, irrelevant for k8s).
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.2/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml`. Gateway API bumped to **v1.2.0** at the `.0` tag (patch line vendors v1.2.1) — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml`. **GRPCRoute graduated to the Standard channel** in 3.2 — add `grpcroutes` + `grpcroutes/status` RBAC to the Gateway provider ServiceAccount.
- **Upgrade ordering:** apply Gateway API v1.2.0 CRDs **before** Traefik 3.2 if using the Gateway provider; add GRPCRoute RBAC concurrent with rollout; apply Traefik CRD bundle before pods.
- **Notable:** native GRPCRoute support (Standard channel).

## 3.1.0  (2024-07-15, latest patch v3.1.7)

- **k8s floor:** **effective floor rises to k8s ≥ 1.21** — 3.1 switches all Kubernetes providers from the Endpoints API to the **EndpointSlices API** (requires ≥1.21). `client-go v0.30.0` (~1.30 as of release date).
- **Breaking:** EndpointSlices migration requires an **RBAC change for every Kubernetes provider**: remove `endpoints` `[get,list,watch]` and add `discovery.k8s.io/endpointslices` `[list,watch]`; also add `nodes` `[get,list,watch]` for the new NodePort load-balancing. Without the RBAC update, service-endpoint discovery breaks (routes go to no backends).
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.1/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml`. Gateway API stays at **v1.1.0** (no bump from 3.0→3.1) — `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml`.
- **Upgrade ordering:** update provider RBAC (endpoints→endpointslices + nodes) **before or concurrent with** rolling pods, or endpoint discovery silently breaks.
- **Deprecations:** KubernetesGateway provider is **no longer experimental** — remove `experimental.kubernetesgateway: true` from static config. **3.1.1 deprecated `disableIngressClassLookup`** → `disableClusterScopeResources` (broader: covers IngressClass + Nodes).
- **Notable:** NodePort load-balancing for Kubernetes providers (drives the new `nodes` RBAC).

## 3.0.0  (2024-04-29, latest patch v3.0.4)

- **k8s floor:** no hard floor stated; `client-go v0.29.2` (~1.29 as of release date). Removal of the `apiextensions.k8s.io/v1beta1` CRD API version and `networking.k8s.io/v1beta1` Ingress support means **3.0 will not register CRDs or read Ingress on clusters that still serve only the v1beta1 groups** (both gone since k8s 1.22) — irrelevant on any current cluster but a hard floor against pre-1.22.
- **Breaking (the v2→v3 jump — this is the migration landing point):**
  - **CRD API group flip:** `traefik.containo.us/v1alpha1` is **removed**; all CRDs (`IngressRoute`, `Middleware`, `TLSOption`, `ServersTransport`, etc.) move to **`traefik.io/v1alpha1`**. Every CR manifest and the CRD bundle itself must be re-applied under the new group, or all custom resources go dark.
  - **Rule-syntax change:** the default `core.defaultRuleSyntax` is now `v3`. v3 syntax renames `Headers`/`HeadersRegexp` → `Header`/`HeaderRegexp`, drops regexp from `PathPrefix`, drops `{id}`-style path placeholders (use `PathRegexp`), removes `HostHeader` (use `Host`), and switches regexp matchers to Go regexp syntax. **Backward compatibility:** set `core.defaultRuleSyntax: v2` (static) or `ruleSyntax: v2` per router to keep v2 rules working during migration — this is what makes the v2→v3 jump low-risk.
  - **Middleware rename:** `IPWhiteList` → `IPAllowList` (config unchanged). Still accepted with a deprecation warning through at least 3.7; slated for removal in the next major (v4). Migration is a field-only rename — keep the `Middleware` resource name so existing `…@kubernetescrd` references stay valid — so do it before the v4 jump.
  - **CRD API version:** the Traefik CRD definitions move off `apiextensions.k8s.io/v1beta1` to `apiextensions.k8s.io/v1`; Ingress reads move off `networking.k8s.io/v1beta1` to `networking.k8s.io/v1`.
  - **Removed options:** `tls.caOptional` (ForwardAuth + all providers), Headers middleware `sslRedirect`/`sslTemporaryRedirect`/`sslHost`/`sslForceHost`/`featurePolicy`, StripPrefix `forceSlash`, `preferServerCipherSuites`, `tracing.datadog.globaltag`. HTTP/3 is no longer experimental — remove `experimental.http3` (its presence now **prevents Traefik from starting**). TCP LoadBalancer `terminationDelay` deprecated → `TCPServersTransport.terminationDelay`.
- **CRD migrations:** Apply `https://raw.githubusercontent.com/traefik/traefik/v3.0/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml` (the `traefik.io` bundle) and the matching RBAC. Gateway API is **v1.0.0** — apply `https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml`. Gateway experimental-channel resources (`TLSRoute`, `TCPRoute`) are **off by default** — enable with `providers.kubernetesGateway.experimentalChannel: true`.
- **Upgrade ordering (from 2.11):** (1) apply the `traefik.io` CRD bundle + updated RBAC; (2) set `core.defaultRuleSyntax: v2` and remove `experimental.http3`; (3) re-author every CR from `traefik.containo.us` → `traefik.io`; (4) roll Traefik to 3.0 with a rollback plan; (5) progressively migrate routers to v3 syntax, then drop the `defaultRuleSyntax: v2` shim. Gateway API v1.0.0 CRDs before Traefik if using the Gateway provider.
- **Deprecations:** v2 rule syntax (`defaultRuleSyntax`/`ruleSyntax`) deprecated from day one of v3 (removal slated next major); TCP `terminationDelay` at LoadBalancer level.
- **Notable:** this is the only v3 minor where the api-group flip and rule-syntax break land — every higher 3.x section assumes the `traefik.io` group is already in place.

## 2.11  (2024-02-12, latest patch **v2.11.64** 2026-11-23 — active support ended 2025-04-29, security support stated to end 2026-09-07 but patches continued past it)

> **Corrected 2026-09-15.** This section previously read "latest patch v2.11.46 … security ENDED
> 2026-02-01". Both were wrong: the line kept receiving security releases for another seven
> months, through **v2.11.57**, and upstream's table gives the security end as **2026-09-07**.
> The practical consequence of the old text was to tell a 2.11 operator that no patch existed
> when eleven more shipped — including the ones clearing both 2026 criticals.

- **Status:** the **last v2 minor** and the **migration SOURCE** for the v2→v3 jump. Active support ended 2025-04-29. **Flag any 2.x sighting as `✗ blocker`** and route operators to §3.0 (v2→v3 migration). Security patches continue past the stated end (latest v2.11.64); v2.11.59 rejects `CONNECT` on every HTTP version, same as v3.7.15. v2.11.61 adds an entry-point option to limit request header values; v2.11.62 brings the BasicAuth 1024-byte password limit and dot-segment-with-path-parameter resolution (same as v3.7.18). Source: release notes v2.11.61–v2.11.64.
- **k8s floor:** no hard floor stated; the v2.11 patch line was kept building against a current `client-go` (`v0.32.3` at v2.11.46), so it runs on modern k8s — but this does NOT extend its support: EOL is calendar-based, not k8s-based.
- **CRD group / syntax (why migration is mandatory):** 2.11 CRDs are on the legacy **`traefik.containo.us/v1alpha1`** API group and use **v2 rule syntax** (`Headers`/`HeadersRegexp`, regexp `PathPrefix`, `{id}` path placeholders, `HostHeader`, `IPWhiteList`). All of these change at 3.0 — see §3.0 for the exact flips. The v2.11 CRD bundle is `https://raw.githubusercontent.com/traefik/traefik/v2.11/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml`.
- **Gateway API:** v2.11 vendors `sigs.k8s.io/gateway-api v0.4.0` — far behind the v1.x line every v3 minor requires; the Gateway provider was experimental-only in v2.
- **Migration path:** there is no in-place 2.x→2.x escape — the only supported forward path is the **v2→v3 jump to §3.0** (set `core.defaultRuleSyntax: v2` for compatibility, flip the CRD group `traefik.containo.us` → `traefik.io`, re-apply the v3 CRD bundle + RBAC). Treat a 2.11 sighting as a remediation item, not a tracked-and-supported minor.
