# Traefik middleware primitives for abuse mitigation

Exact config for each middleware, in both the **file/dynamic** provider form and the **Kubernetes CRD** (`Middleware`, `traefik.io/v1alpha1`) form, with the 2.x→3.x deltas and the gotcha that actually bites. All CRD snippets use `apiVersion: traefik.io/v1alpha1` (v3; the deprecated `traefik.containo.us/v1alpha1` group is v2-era and removed in v3.0).

## Contents
- InFlightReq — concurrency cap (the primary lever)
- RateLimit — request-rate cap (+ Redis in v3)
- IPAllowList — perimeter CIDR gate
- Buffering — request-body cap
- ForwardAuth — delegated allow/deny
- CircuitBreaker / Retry — resilience (2.x↔3.x deltas)
- Chain — composition and order
- 2.x → 3.x delta summary

---

## InFlightReq — per-identity concurrency cap

The single most effective lever against resource starvation: a streaming/long response counts as **one in-flight request for its entire duration**, so `amount` bounds how many concurrent generations one identity can hold open.

```yaml
# Kubernetes CRD
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: chat-inflight, namespace: apps }
spec:
  inFlightReq:
    amount: 8                         # max concurrent requests per key
    sourceCriterion:
      requestHeaderName: Authorization   # one bucket per token; use a decoded claim header for per-user
```
```yaml
# File provider
http:
  middlewares:
    chat-inflight:
      inFlightReq:
        amount: 8
        sourceCriterion: { requestHeaderName: Authorization }
```

- `sourceCriterion` is one of `ipStrategy` (default), `requestHeaderName`, or `requestHost` — same shape as RateLimit.
- **No Redis / distributed backend in any version.** Counters are per-Traefik-pod. Accurate only when one pod receives all traffic (single-leader LB); on a fan-out topology set `amount ≈ target ÷ receiving_pods`, or move the concurrency cap into the app/backend.
- **Fan-out caveat:** one user action often fires several concurrent backend calls (a chat turn = main stream + title + tags + follow-up + autocomplete). Start generous (`amount: 8`+), watch for false 429s, then tighten. Reducing the fan-out itself is an app-side change.
- 2.x→3.x: config unchanged. v3 adds `sourceCriterion.ipStrategy.ipv6Subnet` (group IPv6 clients by subnet so one /64 isn't unlimited).

## RateLimit — per-identity request rate

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: chat-ratelimit, namespace: apps }
spec:
  rateLimit:
    average: 30                       # 30 requests…
    period: 1m                        # …per MINUTE — see gotcha
    burst: 15                         # token-bucket depth
    sourceCriterion:
      requestHeaderName: Authorization
```

- **THE gotcha: `period` defaults to `1s`.** Omit it and `average: 30` means 30 requests/**second**. Always set `period` explicitly.
- `average` + `period` = sustained rate; `burst` = bucket depth (short spikes allowed).
- **Distributed (v3.4+, "the prod answer for fan-out"):** a native `redis` block gives consistent counts across all Traefik replicas. Use instead of relying on single-leader counting when traffic fans out.
  ```yaml
  spec:
    rateLimit:
      average: 30
      period: 1m
      burst: 15
      sourceCriterion: { requestHeaderName: Authorization }
      redis:
        endpoints: ["redis-master.redis:6379"]
        # secret / db / tls.caSecret / tls.certSecret as needed
  ```
- Real client IP for `ipStrategy` depends on the entrypoint's `forwardedHeaders.trustedIPs` — without it, XFF is stripped (secure default) and depth-based IP detection degrades to `RemoteAddr`.

## IPAllowList — perimeter CIDR gate (v3 name; `IPWhiteList` in v2)

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: intranet-only, namespace: apps }
spec:
  ipAllowList:
    sourceRange: ["10.0.0.0/8", "192.168.0.0/16"]
    rejectStatusCode: 403             # v3 only; v2 IPWhiteList always returned 403
    # ipStrategy: { depth: 1, excludedIPs: [] }   # set depth if behind another proxy/XFF
```

- **v2→v3 rename:** `IPWhiteList` → `IPAllowList` (field shape otherwise identical). v3 adds `rejectStatusCode`. Keep the `Middleware` resource *name* stable across the rename so existing `@kubernetescrd` references don't break.
- If `ipStrategy.depth` is set, `excludedIPs` is ignored; if depth exceeds the XFF entry count the derived IP is empty and the request fails closed.
- Blunt for many users behind one NAT/egress IP — a perimeter, not a per-user control.

## Buffering — request-body size cap

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: body-cap, namespace: apps }
spec:
  buffering:
    maxRequestBodyBytes: 2000000      # ~2 MB → 413 if exceeded
    memRequestBodyBytes: 1048576
    maxResponseBodyBytes: 0           # 0 = unlimited — MUST stay 0 on streaming paths
```

- Stops giant-body amplification. `maxRequestBodyBytes` exceeded → 413.
- **Never set `maxResponseBodyBytes` on a streaming/SSE route** — buffering the response breaks streaming. Apply Buffering to the request side only.

## ForwardAuth — delegate an allow/deny to a sidecar

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: gate, namespace: apps }
spec:
  forwardAuth:
    address: http://authz.apps.svc/verify
    authResponseHeaders: ["X-User-Id"]      # copy headers from the auth response onto the upstream request
    # maxBodySize: 1000000   # v3: default is -1 (UNBOUNDED) — a DoS footgun, set it
```

- 2xx from `address` → allowed; anything else → the auth service's response is returned to the client.
- **No caching, in any version** — every proxied request makes a fresh round-trip to `address`. Real per-request latency; keep the authorizer local and fast.
- v3 adds `maxBodySize`/`maxResponseBodySize` (both **unbounded `-1` by default** — set them), `forwardBody`, `preserveRequestMethod`, `addAuthCookiesToResponse`.
- Best used for a check the app *can't* express (mTLS identity, an SSO/OIDC gate, a coarse pre-app allow/deny) — not to re-validate a session the app already validates (that just doubles the check and couples the proxy to app internals).

## CircuitBreaker / Retry — 2.x↔3.x deltas

- **CircuitBreaker:** expression (`NetworkErrorRatio()`, `ResponseCodeRatio(...)`, `LatencyAtQuantileMS(...)`), `checkPeriod`, `fallbackDuration`, `recoveryDuration`. v3 adds a configurable open-state `responseCode` (v2 hard-coded 503). Not an abuse control itself, but pairs with rate limiting to shed load once the upstream degrades under attack.
- **Retry — biggest 2.x→3.x change:** v2 retries only on network failure (`attempts` + `initialInterval`). v3 (through 3.7) adds `status` (retry on specific HTTP codes), `retryNonIdempotentMethod` (opt-in POST retry — an *amplification risk* if misused), `maxRequestBodyBytes`. Be deliberate: retrying POSTs against a scarce backend can worsen a flood.

## Chain — composition and order

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: chat-defense, namespace: apps }
spec:
  chain:
    middlewares:
      - name: intranet-only     # cheapest reject first
      - name: chat-inflight
      - name: chat-ratelimit
      - name: body-cap
```

- Executes in declared order, and a later middleware **sees header mutations made by earlier ones** — so a claim→header decode (identity-keying.md) must come *before* the `InFlightReq`/`RateLimit` that key on that header.
- Order principle: reject the cheapest way first (IP allowlist → concurrency → rate → body), so a blocked request spends the least work.

## 2.x → 3.x delta summary

| Concern | v2 | v3 |
|---|---|---|
| IP gate | `IPWhiteList`, always 403 | `IPAllowList`, `rejectStatusCode` |
| Distributed rate limit | none (in-memory only) | `RateLimit.redis` (v3.4+) |
| Retry triggers | network failure only | + HTTP `status`, non-idempotent opt-in (v3.7) |
| CircuitBreaker open code | 503 fixed | configurable `responseCode` |
| CRD API group | `traefik.containo.us/v1alpha1` | `traefik.io/v1alpha1` (old group removed at 3.0) |
| Rule syntax (routers) | v2 (`Headers`, regexp `PathPrefix`) | v3 (`Header`, `!`-negation, wildcard `Host`); `core.defaultRuleSyntax: v2` shim for migration |

For migration/compat tracking of Traefik versions themselves (support windows, CRD-bundle apply, Gateway API pairing), that is a *different* concern — see the `k8s-components-checker` skill's Traefik compat file, not this hardening skill.
